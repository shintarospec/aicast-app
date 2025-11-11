#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
投稿案自動生成バッチ処理
作成日: 2025-11-10
機能: 設定に基づいてキャスト別に投稿案を自動生成
"""

import datetime
import sys
import traceback
import random
import time
from typing import List, Dict, Any
import os
import fcntl

# app.pyから必要な関数をインポート
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import execute_query

# ロックファイルのパス
LOCK_FILE = os.path.join(os.path.dirname(__file__), '.auto_generation.lock')

# Vertex AI のインポート
try:
    from vertexai.generative_models import GenerativeModel
    import vertexai
except ImportError:
    from vertexai.preview.generative_models import GenerativeModel
    import vertexai

# Vertex AI初期化（グローバルで1回のみ）
_vertex_ai_initialized = False
_gemini_model = None

def init_vertex_ai():
    """Vertex AIを初期化（初回のみ実行）"""
    global _vertex_ai_initialized, _gemini_model
    
    if _vertex_ai_initialized:
        return _gemini_model
    
    try:
        project_id = os.getenv("GCP_PROJECT", "aicast-472807")
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        
        if credentials_path and os.path.exists(credentials_path):
            from google.oauth2 import service_account
            credentials = service_account.Credentials.from_service_account_file(credentials_path)
            vertexai.init(project=project_id, location="us-central1", credentials=credentials)
        else:
            vertexai.init(project=project_id, location="us-central1")
        
        _gemini_model = GenerativeModel("gemini-2.5-flash")
        _vertex_ai_initialized = True
        return _gemini_model
    except Exception as e:
        print(f"❌ Vertex AI初期化エラー: {e}")
        return None
    import vertexai



def get_active_auto_generation_settings() -> List[Dict[str, Any]]:
    """
    現在実行すべき自動生成設定を取得（日本時間JSTベース）
    
    Returns:
        実行対象の設定リスト
    """
    # 日本時間（JST）で現在時刻を取得
    JST = datetime.timezone(datetime.timedelta(hours=9))
    now = datetime.datetime.now(JST)
    current_time_str = now.strftime('%H:%M')
    today = now.strftime('%Y-%m-%d')
    
    print(f"🕐 現在時刻（JST）: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔍 検索する生成時刻: {current_time_str} 以前（今日未実行）")
    
    # 実行対象の設定を取得
    # 条件: 今日まだ生成していない && generation_time <= 現在時刻
    settings = execute_query("""
        SELECT 
            ags.id AS setting_id,
            ags.cast_id,
            ags.posts_per_day,
            ags.last_generated_at,
            c.name AS cast_name,
            c.nickname AS cast_nickname,
            ags.generation_time
        FROM auto_generation_settings ags
        JOIN casts c ON ags.cast_id = c.id
        WHERE ags.enabled = 1 
        AND ags.generation_time <= ?
        AND (
            ags.last_generated_at IS NULL 
            OR DATE(ags.last_generated_at) < DATE('now', 'localtime')
        )
    """, (current_time_str,), fetch="all")
    
    if settings:
        print(f"✅ 実行対象: {len(settings)}件")
        for s in settings:
            print(f"   - {s['cast_name']} ({s['cast_nickname']}) - 設定時刻: {s['generation_time']}")
    else:
        print(f"⏭️ 実行対象なし（generation_time <= {current_time_str} で今日未実行の設定なし）")
    
    return settings if settings else []


def generate_posts_for_cast(setting: Dict[str, Any]) -> Dict[str, Any]:
    """
    指定されたキャストの投稿案を生成
    
    Args:
        setting: 自動生成設定（cast_id, cast_name, cast_nickname, posts_per_day, setting_idを含む辞書）
        
    Returns:
        実行結果（posts_generated, posts_failed, status, error_messageを含む辞書）
    """
    cast_id = setting['cast_id']
    cast_name = setting['cast_name']
    cast_nickname = setting['cast_nickname']
    posts_per_day = setting['posts_per_day']
    setting_id = setting['setting_id']
    
    print(f"\n{'='*60}")
    print(f"🤖 自動生成開始: {cast_name}（{cast_nickname}）")
    print(f"   生成件数: {posts_per_day}件")
    print(f"{'='*60}")
    
    success_count = 0
    failed_count = 0
    error_messages = []
    
    # サンプル投稿を取得
    sample_posts = execute_query("""
        SELECT post_content, category FROM sample_posts 
        WHERE cast_id = ? 
        ORDER BY sort_order
    """, (cast_id,), fetch="all")
    
    if not sample_posts:
        error_msg = f"サンプル投稿が見つかりません（キャストID: {cast_id}）"
        print(f"❌ {error_msg}")
        return {
            'posts_generated': 0,
            'posts_failed': posts_per_day,
            'status': 'failed',
            'error_message': error_msg
        }
    
    # Vertex AIモデルを取得
    model = init_vertex_ai()
    if model is None:
        error_msg = "Vertex AI初期化に失敗しました"
        print(f"❌ {error_msg}")
        return {
            'posts_generated': 0,
            'posts_failed': posts_per_day,
            'status': 'failed',
            'error_message': error_msg
        }
    
    # 投稿案を生成
    for i in range(posts_per_day):
        try:
            print(f"\n📝 投稿案 {i+1}/{posts_per_day} を生成中...")
            
            # ランダムにサンプル投稿を選択
            selected_sample = random.choice(sample_posts)
            instruction_text = selected_sample['post_content']
            category_text = selected_sample['category'] or "一般"
            
            # プロンプトを構築（app.pyのbuild_full_prompt相当）
            prompt = f"""あなたは{cast_name}({cast_nickname})としてSNS投稿を作成します。

以下の指示に従って、投稿案を1つだけ作成してください：
{instruction_text}

要件：
- 140文字以内
- {cast_name}のキャラクターに合った口調・表現
- カテゴリ: {category_text}
- 投稿文のみを出力（説明や例示は不要）
"""
            
            # Geminiで投稿文を生成
            response = model.generate_content(prompt)
            generated_text = response.text.strip()
            
            # 不要なパターンを除去
            import re
            # 「」や『』で囲まれている場合は除去
            generated_text = re.sub(r'^[「『"]([^」』"]+)[」』"]$', r'\1', generated_text)
            
            if generated_text:
                # ランダムな投稿時刻を生成（7:00-23:00）
                random_hour = random.randint(7, 23)
                random_minute = random.randint(0, 59)
                created_at = datetime.datetime.now().replace(
                    hour=random_hour, minute=random_minute, second=0, microsecond=0
                ).strftime('%Y-%m-%d %H:%M:%S')
                
                # データベースに保存
                execute_query("""
                    INSERT INTO posts (cast_id, created_at, content, theme, generated_at)
                    VALUES (?, ?, ?, ?, datetime('now', 'localtime'))
                """, (cast_id, created_at, generated_text, category_text))
                
                success_count += 1
                print(f"✅ 投稿案 {i+1} 生成成功")
                print(f"   内容: {generated_text[:50]}...")
            else:
                failed_count += 1
                error_messages.append(f"投稿案 {i+1}: 生成結果が空")
                print(f"⚠️ 投稿案 {i+1} 生成失敗（空の結果）")
            
            # API制限回避のため待機
            time.sleep(1.0)
                
        except Exception as e:
            failed_count += 1
            error_msg = f"投稿案 {i+1}: {str(e)}"
            error_messages.append(error_msg)
            print(f"❌ 投稿案 {i+1} 生成エラー: {e}")
            traceback.print_exc()
    
    # 最終生成日時を更新
    execute_query("""
        UPDATE auto_generation_settings 
        SET last_generated_at = datetime('now', 'localtime'),
            total_generated = total_generated + ?,
            updated_at = datetime('now', 'localtime')
        WHERE id = ?
    """, (success_count, setting_id))
    
    # ログを記録
    status = 'success' if failed_count == 0 else ('partial' if success_count > 0 else 'failed')
    error_message = '\n'.join(error_messages) if error_messages else None
    
    execute_query("""
        INSERT INTO auto_generation_logs 
        (cast_id, posts_generated, posts_failed, status, error_message)
        VALUES (?, ?, ?, ?, ?)
    """, (cast_id, success_count, failed_count, status, error_message))
    
    print(f"\n{'='*60}")
    print(f"📊 生成結果: {cast_name}（{cast_nickname}）")
    print(f"   成功: {success_count}件")
    print(f"   失敗: {failed_count}件")
    print(f"   ステータス: {status}")
    print(f"{'='*60}\n")
    
    return {
        'posts_generated': success_count,
        'posts_failed': failed_count,
        'status': status,
        'error_message': error_message
    }


def run_auto_generation():
    """
    自動生成バッチのメイン処理（日本時間JSTベース）
    """
    JST = datetime.timezone(datetime.timedelta(hours=9))
    
    print("\n" + "="*60)
    print("🚀 投稿案自動生成バッチ実行開始")
    print(f"   実行時刻（JST）: {datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # 実行対象の設定を取得
    settings = get_active_auto_generation_settings()
    
    if not settings:
        print("\n⏭️ 実行対象の設定がありません")
        print("="*60 + "\n")
        return
    
    print(f"\n✅ 実行対象: {len(settings)}件")
    
    total_success = 0
    total_failed = 0
    
    # 各設定について投稿案を生成
    for setting in settings:
        result = generate_posts_for_cast(setting)
        total_success += result['posts_generated']
        total_failed += result['posts_failed']
    
    print("\n" + "="*60)
    print("🎉 投稿案自動生成バッチ実行完了")
    print(f"   総成功: {total_success}件")
    print(f"   総失敗: {total_failed}件")
    print("="*60 + "\n")


if __name__ == "__main__":
    lock_file = None
    try:
        # ロックファイルを取得（重複実行を防止）
        lock_file = open(LOCK_FILE, 'w')
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            print("⏭️ 別のバッチ処理が実行中です。スキップします。")
            sys.exit(0)
        
        # バッチ処理実行
        run_auto_generation()
        
    except Exception as e:
        print(f"\n❌ 致命的エラー: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        # ロックを解放
        if lock_file:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                lock_file.close()
            except:
                pass
