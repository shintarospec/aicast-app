# AI画像生成モジュール - Vertex AI Imagen 2
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
import time
import os
import tempfile
from datetime import datetime
import streamlit as st
from ai_image_db import log_generation_history, get_daily_generation_count, get_img_setting

class AIImageGenerator:
    """Vertex AI Imagen 2を使用した画像生成クラス"""
    
    def __init__(self, project_id="aicast-472807", location="us-central1"):
        self.project_id = project_id
        self.location = location
        self.model = None
        self.initialized = False
    
    def initialize(self, retry_count=3):
        """Vertex AI接続を初期化（リトライ機能付き）"""
        for attempt in range(retry_count):
            try:
                # 認証状況をチェック
                import os
                adc_file = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
                if not os.path.exists(adc_file):
                    st.error("❌ Google Cloud認証が設定されていません")
                    st.info("💡 システム設定で認証を行ってください")
                    return False
                
                # プロジェクトIDとロケーションを明示的に設定
                print(f"🔧 Vertex AI初期化中... (試行 {attempt + 1}/{retry_count}) Project: {self.project_id}, Location: {self.location}")
                
                # タイムアウトを短く設定してテスト
                import time
                start_time = time.time()
                
                vertexai.init(project=self.project_id, location=self.location)
                print(f"✅ Vertex AI初期化完了 ({time.time() - start_time:.2f}秒)")
                
                # モデル読み込み
                start_time = time.time()
                self.model = ImageGenerationModel.from_pretrained("imagegeneration@006")
                print(f"✅ Imagen 2モデル読み込み完了 ({time.time() - start_time:.2f}秒)")
                
                self.initialized = True
                if attempt > 0:
                    st.success(f"✅ 初期化成功 (試行 {attempt + 1}回目)")
                return True
                
            except Exception as e:
                error_msg = str(e)
                print(f"❌ 初期化エラー (試行 {attempt + 1}/{retry_count}): {error_msg}")
                
                # 最後の試行でない場合は短時間待機
                if attempt < retry_count - 1:
                    print(f"⏳ {2}秒後に再試行...")
                    time.sleep(2)
                    continue
                
                # 最後の試行でもエラーの場合、ユーザー向けメッセージを表示
                # エラー分類とユーザー向けメッセージ
                if "authentication" in error_msg.lower() or "login" in error_msg.lower():
                    st.error("❌ Google Cloud認証エラー")
                    st.info("💡 システム設定 > Google Cloud認証 で再認証してください")
                elif "timeout" in error_msg.lower():
                    st.error("❌ 接続タイムアウト")
                    st.info("💡 ネットワーク接続を確認して再試行してください")
                elif "503" in error_msg:
                    st.error("❌ Google Cloud サービス一時利用不可")
                    st.info("💡 しばらく時間をおいてから再試行してください")
                elif "quota" in error_msg.lower():
                    st.error("❌ API使用量制限に達しました")
                    st.info("💡 プロジェクトのAPI制限を確認してください")
                else:
                    st.error(f"❌ Vertex AI初期化エラー: {error_msg}")
                    st.info("💡 エラーが続く場合は、認証を再設定してください")
                
                return False
        
        return False
    
    def check_generation_limits(self, cast_id=None):
        """画像生成制限をチェック"""
        max_daily = int(get_img_setting("max_daily_generations", "10"))
        current_count = get_daily_generation_count(cast_id)
        
        return {
            "can_generate": current_count < max_daily,
            "current_count": current_count,
            "max_daily": max_daily,
            "remaining": max_daily - current_count
        }
    
    def validate_prompt(self, prompt):
        """プロンプトの検証とフィルタリング"""
        if not prompt or len(prompt.strip()) < 3:
            return False, "プロンプトは3文字以上で入力してください"
        
        if len(prompt) > 500:
            return False, "プロンプトは500文字以内で入力してください"
        
        # 不適切なキーワードのチェック（基本的なもの）
        inappropriate_keywords = [
            "violent", "weapon", "blood", "nude", "sexual", "adult",
            "暴力", "武器", "血", "裸", "性的", "アダルト", "暴力的"
        ]
        
        prompt_lower = prompt.lower()
        for keyword in inappropriate_keywords:
            if keyword in prompt_lower:
                return False, f"不適切なキーワードが含まれています: {keyword}"
        
        return True, "OK"
    
    def enhance_prompt(self, prompt):
        """プロンプトを強化（翻訳・詳細化）"""
        try:
            from vertexai.generative_models import GenerativeModel
            
            model = GenerativeModel("gemini-pro")
            
            enhancement_prompt = f"""
以下の画像生成プロンプトを、より詳細で効果的な英語のプロンプトに変換してください。

元のプロンプト: "{prompt}"

要件:
1. 日本語の場合は英語に翻訳
2. 画像生成AIに適した詳細な描写を追加
3. アート・写真の品質を向上させるキーワードを含める
4. 不適切な内容は排除
5. 1つの改良されたプロンプトのみを出力（説明不要）

強化されたプロンプト:
"""
            
            response = model.generate_content(enhancement_prompt)
            enhanced_prompt = response.text.strip()
            
            # 不適切なキーワードを再チェック
            if self.validate_prompt(enhanced_prompt)[0]:
                print(f"プロンプト強化: '{prompt}' → '{enhanced_prompt}'")
                return enhanced_prompt
            else:
                print(f"強化されたプロンプトに問題があるため、元のプロンプトを使用: '{prompt}'")
                return prompt
                
        except Exception as e:
            print(f"プロンプト強化エラー: {e}")
            return prompt

    def generate_image(self, prompt, cast_id=None, cast_name=None, 
                      aspect_ratio="1:1", image_size="1024x1024"):
        """画像を生成"""
        
        # 初期化チェック（遅延初期化）
        if not self.initialized:
            st.info("🔧 Vertex AI Imagen 2を初期化中...")
            if not self.initialize():
                return None, "Vertex AI初期化に失敗しました"
        
        # プロンプト検証
        is_valid, validation_message = self.validate_prompt(prompt)
        if not is_valid:
            return None, validation_message
        
        # プロンプト強化（エラー時は元のプロンプトを使用）
        try:
            enhanced_prompt = self.enhance_prompt(prompt)
            if enhanced_prompt == prompt:  # 強化されていない場合
                print(f"プロンプト強化をスキップ、元のプロンプトを使用: '{prompt}'")
        except Exception as e:
            print(f"プロンプト強化エラー、元のプロンプトを使用: {e}")
            enhanced_prompt = prompt
        
        # 生成制限チェック
        limits = self.check_generation_limits(cast_id)
        if not limits["can_generate"]:
            return None, f"日次生成制限に達しました（{limits['current_count']}/{limits['max_daily']}）"
        
        start_time = time.time()
        
        try:
            st.info("🎨 AI画像を生成中...")
            progress_bar = st.progress(0)
            
            # Imagen 2で画像生成
            progress_bar.progress(25)
            
            print(f"🎨 画像生成開始: '{enhanced_prompt}' (アスペクト比: {aspect_ratio})")
            
            images = self.model.generate_images(
                prompt=enhanced_prompt,
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                safety_filter_level="allow_most",
                person_generation="allow_adult"
            )
            
            progress_bar.progress(75)
            
            # ImageGenerationResponseからimagesリストを正しく取得
            if hasattr(images, 'images'):
                image_list = images.images
            else:
                image_list = images
            
            print(f"生成結果: {len(image_list) if image_list else 0}個の画像")
            
            if not image_list or len(image_list) == 0:
                raise Exception("画像が生成されませんでした（空のレスポンス）")
            
            # 画像を一時ファイルに保存
            generated_image = image_list[0]
            temp_dir = "temp_images"
            os.makedirs(temp_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"ai_image_{timestamp}.png"
            image_path = os.path.join(temp_dir, filename)
            
            # 画像を保存
            generated_image.save(image_path)
            print(f"✅ 画像保存完了: {image_path}")
            
            progress_bar.progress(100)
            generation_time = time.time() - start_time
            
            # 生成履歴を記録
            log_generation_history(
                prompt=prompt,
                model_used="imagen-2",
                generation_time=generation_time,
                success=True,
                cast_id=cast_id,
                cast_name=cast_name
            )
            
            st.success(f"✅ 画像生成完了！（{generation_time:.2f}秒）")
            progress_bar.empty()
            
            return image_path, "画像生成成功"
            
        except Exception as e:
            generation_time = time.time() - start_time
            error_message = str(e)
            
            # エラー履歴を記録
            log_generation_history(
                prompt=prompt,
                model_used="imagen-2",
                generation_time=generation_time,
                success=False,
                error_message=error_message,
                cast_id=cast_id,
                cast_name=cast_name
            )
            
            st.error(f"❌ 画像生成エラー: {error_message}")
            return None, error_message
    
    def generate_auto_caption(self, prompt, cast_name=None, cast_id=None, user_instruction=None):
        """投稿管理の直接指示と同じシステムを使用してAIキャプションを生成"""
        import streamlit as st
        
        print(f"🔍 [DEBUG] コメント生成開始:")
        print(f"  - prompt: '{prompt}'")
        print(f"  - cast_name: '{cast_name}'")
        print(f"  - cast_id: {cast_id}")
        print(f"  - user_instruction: '{user_instruction}'")
        print(f"  - gemini_model 存在: {bool(st.session_state.get('gemini_model'))}")
        
        try:
            # 投稿管理と同じGeminiモデルを使用
            if not st.session_state.get('gemini_model'):
                print("❌ Geminiモデルが利用できません。フォールバック処理を実行します。")
                return self.generate_fallback_caption(prompt, cast_name, user_instruction)
            
            print("✅ Geminiモデルが利用可能です。AI生成を実行します。")
            
            # キャスト情報を取得（投稿管理と同じformat_persona関数を使用）
            persona_sheet = f"キャスト名: {cast_name or 'AIキャスト'}"
            
            if cast_id:
                try:
                    # app.pyのformat_persona関数をインポート
                    import sys
                    sys.path.append('.')
                    from app import format_persona, execute_query
                    
                    # cast_detailsを取得（MCF DBから）
                    cast_details = execute_query("SELECT * FROM casts WHERE id = ?", (cast_id,))
                    
                    if cast_details:
                        persona_sheet = format_persona(cast_id, cast_details[0])
                        print(f"✅ キャスト情報取得成功")
                    else:
                        print(f"⚠️ キャスト情報が見つかりません (ID: {cast_id})")
                    
                except Exception as e:
                    print(f"❌ キャスト情報取得エラー: {e}")
            
            # 投稿管理の直接指示と同じプロンプト形式を使用
            # プロンプトまたはユーザー指示を投稿指示として使用
            post_instruction = user_instruction if user_instruction and user_instruction.strip() else prompt
            
            print(f"📝 投稿指示: '{post_instruction}'")
            
            # 投稿管理と同じスタイルのプロンプト（直接指示形式）
            caption_prompt = f"""# ペルソナ
{persona_sheet}

# 投稿指示
{post_instruction.strip()}に関する画像投稿のキャプションを作成してください。

# ルール
上記の指示に従って、このキャラクターらしいSNS投稿を**50〜70文字以内**で生成してください。キャラクターの個性、口調、趣味嗜好を反映させてください。"""
            
            print(f"🔍 投稿管理互換プロンプト送信中...")
            
            # 投稿管理と同じsafe_generate_content関数を使用
            from app import safe_generate_content, clean_generated_content
            response = safe_generate_content(st.session_state.gemini_model, caption_prompt)
            caption = clean_generated_content(response.text)
            
            print(f"✅ AI生成成功: '{caption}'")
            
            # 文字数制限チェック
            if len(caption) > 70:
                caption = caption[:67] + "..."
            elif len(caption) < 50:
                # 短すぎる場合は適切な絵文字やハッシュタグを追加
                if any(word in post_instruction for word in ["花", "お花"]):
                    caption += " 🌸 #花"
                elif any(word in post_instruction for word in ["猫", "ねこ"]):
                    caption += " 🐱 #猫"
                else:
                    caption += " ✨"
            
            print(f"✨ 最終結果: '{caption}' ({len(caption)}文字)")
            
            return caption
            
        except Exception as e:
            print(f"❌ AI キャプション生成エラー: {e}")
            print("🔄 フォールバック処理に切り替えます")
            return self.generate_fallback_caption(prompt, cast_name, user_instruction)
            
            # キャスト詳細情報を取得（MCF DBから）
            cast_info = None
            if cast_id:
                # MCF DBのexecute_query関数を使用
                import sqlite3
                try:
                    conn = sqlite3.connect("casting_office.db", check_same_thread=False)
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    # キャスト基本情報とペルソナ情報を結合して取得
                    # まずキャスト基本情報を取得
                    cursor.execute("""
                        SELECT name, nickname, age, gender, region, language
                        FROM casts WHERE id = ?
                    """, (cast_id,))
                    
                    cast_basic = cursor.fetchone()
                    
                    if cast_basic:
                        # ペルソナ情報も取得を試行
                        try:
                            cursor.execute("""
                                SELECT personality, tone, hobby, background, goal,
                                       strength, weakness, speaking_style
                                FROM personas WHERE cast_id = ?
                            """, (cast_id,))
                            persona_info = cursor.fetchone()
                            
                            # 基本情報とペルソナ情報を結合
                            if persona_info:
                                cast_info = dict(cast_basic)
                                cast_info.update(dict(persona_info))
                            else:
                                cast_info = dict(cast_basic)
                        except sqlite3.Error:
                            # personasテーブルが存在しない場合は基本情報のみ
                            cast_info = dict(cast_basic)
                    else:
                        cast_info = None
                    conn.close()
                    
                except Exception as e:
                    print(f"キャスト情報取得エラー: {e}")
                    cast_info = None
            
            # 投稿管理の直接指示と同じプロンプト形式を使用
            # キャラクター設定をformat_persona関数と同じ形式で構築
            from app import format_persona
            
            # キャスト情報を統合してペルソナシートを生成
            try:
                # cast_infoを統合データ形式に変換
                integrated_cast_data = {}
                if cast_info:
                    # 基本情報とペルソナ情報を統合
                    integrated_cast_data.update(cast_info)
                else:
                    integrated_cast_data = {"name": cast_name or "AIキャスト"}
                
                # 投稿管理と同じformat_persona関数を使用
                persona_sheet = format_persona(cast_id, integrated_cast_data)
            except Exception as e:
                print(f"ペルソナシート生成エラー: {e}")
                persona_sheet = f"# キャラクター設定シート：{cast_name or 'AIキャスト'}\n基本的な設定情報が利用できません。"
            
            # 投稿管理と完全に同じプロンプト形式
            caption_prompt = f"""# ペルソナ
{persona_sheet}

# 投稿指示
画像：{prompt}についてのSNS投稿を作成してください。
{user_instruction.strip() if user_instruction and user_instruction.strip() else "画像の内容に関連した自然な投稿をしてください。"}

# ルール
上記の指示に従って、このキャラクターらしいSNS投稿を**280文字以内**で生成してください。キャラクターの個性、口調、趣味嗜好を反映させてください。"""
            
            # 投稿管理と同じsafe_generate_content関数を使用
            from app import safe_generate_content
            response = safe_generate_content(model, caption_prompt)
            raw_caption = response.text.strip()
            
            # 投稿管理と同じコンテンツクリーニングを適用
            from app import clean_generated_content
            caption = clean_generated_content(raw_caption)
            
            # 文字数制限チェック
            if len(caption) > 280:
                caption = caption[:277] + "..."
            
            print(f"✅ 投稿管理形式でのコメント生成完了: '{caption}' ({len(caption)}文字)")
            return caption
            
        except Exception as e:
            print(f"AI キャプション生成エラー: {e}")
            # 改善されたフォールバック：プロンプト内容を詳細に反映
            fallback_parts = []
            
            # キャラクター名がある場合
            if cast_name:
                fallback_parts.append(f"こんにちは、{cast_name}です！")
            
            # プロンプト内容に基づいた具体的なコメント生成
            prompt_lower = prompt.lower()
            
            # 自然・風景関連
            if any(word in prompt for word in ["夜の海", "海", "夜", "月", "星"]):
                fallback_parts.append("美しい夜の海をお届けします🌙✨")
            elif any(word in prompt for word in ["夕日", "夕焼け", "サンセット"]):
                fallback_parts.append("綺麗な夕日の風景をお楽しみください🌅")
            elif any(word in prompt for word in ["山", "自然", "森"]):
                fallback_parts.append("自然の美しさを感じてください🏔️")
            elif any(word in prompt for word in ["花", "桜", "バラ"]):
                fallback_parts.append("美しいお花の画像です🌸")
            elif any(word in prompt for word in ["空", "雲", "青空"]):
                fallback_parts.append("爽やかな空の風景をどうぞ☁️")
            
            # 動物関連
            elif any(word in prompt for word in ["猫", "ねこ", "cat"]):
                fallback_parts.append("可愛い猫ちゃんの画像です🐱")
            elif any(word in prompt for word in ["犬", "いぬ", "dog"]):
                fallback_parts.append("可愛いワンちゃんです🐶")
            elif any(word in prompt for word in ["鳥", "とり", "bird"]):
                fallback_parts.append("美しい鳥の姿をご覧ください🐦")
            
            # 建物・都市関連
            elif any(word in prompt for word in ["街", "都市", "ビル", "建物"]):
                fallback_parts.append("都市の風景をお届けします🏙️")
            elif any(word in prompt for word in ["家", "建築", "architecture"]):
                fallback_parts.append("素敵な建築の画像です�")
            
            # 人物・ポートレート関連
            elif any(word in prompt for word in ["人", "女性", "男性", "portrait"]):
                fallback_parts.append("素敵なポートレート画像です📷")
            
            # 抽象・アート関連
            elif any(word in prompt for word in ["アート", "抽象", "art", "abstract"]):
                fallback_parts.append("アーティスティックな作品をどうぞ🎨")
            
            # その他・一般的
            else:
                # プロンプトの最初の部分を使用
                prompt_part = prompt[:20] + ("..." if len(prompt) > 20 else "")
                fallback_parts.append(f"「{prompt_part}」をテーマにした画像です✨")
            
            # ユーザー指示がある場合は内容を反映
            if user_instruction and user_instruction.strip():
                instruction_keywords = user_instruction.strip()
                if "可愛い" in instruction_keywords:
                    fallback_parts.append("可愛らしさを込めて💕")
                elif "綺麗" in instruction_keywords or "美しい" in instruction_keywords:
                    fallback_parts.append("美しさをお楽しみください✨")
                elif "楽しい" in instruction_keywords:
                    fallback_parts.append("楽しい気持ちでお届け🎉")
                else:
                    fallback_parts.append(f"({instruction_keywords})")
            
            # 適切なハッシュタグを追加
            if any(word in prompt for word in ["夜", "海", "月", "星"]):
                fallback_parts.append("#夜景 #海 #美しい風景")
            elif any(word in prompt for word in ["猫", "動物"]):
                fallback_parts.append("#猫 #可愛い #動物")
            elif any(word in prompt for word in ["花", "自然"]):
                fallback_parts.append("#花 #自然 #美しい")
            else:
                fallback_parts.append("#AI生成 #画像投稿")
            
            fallback = "\n".join(fallback_parts)
            
            # 文字数制限チェック
            if len(fallback) > 280:
                fallback = fallback[:277] + "..."
            
            return fallback
    
    
    def generate_fallback_caption(self, prompt, cast_name=None, user_instruction=None):
        """改善されたフォールバック：プロンプト内容を詳細に反映"""
        fallback_parts = []
        
        # キャラクター名がある場合
        if cast_name:
            fallback_parts.append(f"こんにちは、{cast_name}です！")
        
        # プロンプト内容に基づいた具体的なコメント生成
        prompt_lower = prompt.lower()
        
        # 自然・風景関連
        if any(word in prompt for word in ["夜の海", "海", "夜", "月", "星"]):
            fallback_parts.append("美しい夜の海をお届けします🌙✨")
        elif any(word in prompt for word in ["夕日", "夕焼け", "サンセット"]):
            fallback_parts.append("綺麗な夕日の風景をお楽しみください🌅")
        elif any(word in prompt for word in ["山", "自然", "森"]):
            fallback_parts.append("自然の美しさを感じてください🏔️")
        elif any(word in prompt for word in ["花", "桜", "バラ"]):
            fallback_parts.append("美しいお花の画像です🌸")
        elif any(word in prompt for word in ["空", "雲", "青空"]):
            fallback_parts.append("爽やかな空の風景をどうぞ☁️")
        
        # 動物関連
        elif any(word in prompt for word in ["猫", "ねこ", "cat"]):
            fallback_parts.append("可愛い猫ちゃんの画像です🐱")
        elif any(word in prompt for word in ["犬", "いぬ", "dog"]):
            fallback_parts.append("可愛いワンちゃんです🐶")
        elif any(word in prompt for word in ["鳥", "とり", "bird"]):
            fallback_parts.append("美しい鳥の姿をご覧ください🐦")
        
        # 建物・都市関連
        elif any(word in prompt for word in ["街", "都市", "ビル", "建物"]):
            fallback_parts.append("都市の風景をお届けします🏙️")
        elif any(word in prompt for word in ["家", "建築", "architecture"]):
            fallback_parts.append("素敵な建築の画像です🏠")
        
        # 人物・ポートレート関連
        elif any(word in prompt for word in ["人", "女性", "男性", "portrait"]):
            fallback_parts.append("素敵なポートレート画像です📷")
        
        # 抽象・アート関連
        elif any(word in prompt for word in ["アート", "抽象", "art", "abstract"]):
            fallback_parts.append("アーティスティックな作品をどうぞ🎨")
        
        # ビジネス・ショッピング関連
        elif any(word in prompt for word in ["お買い得", "セール", "安い", "コメント", "おすすめ", "商品", "ショッピング"]):
            fallback_parts.append("お得な情報をお届けします💰")
        
        # 食べ物関連
        elif any(word in prompt for word in ["料理", "食べ物", "グルメ", "美味しい", "レシピ"]):
            fallback_parts.append("美味しそうな画像です🍽️")
        
        # その他・一般的
        else:
            # プロンプトの最初の部分を使用（改善版）
            if len(prompt) > 10:
                prompt_part = prompt[:15] + "..."
            else:
                prompt_part = prompt
            fallback_parts.append(f"{prompt_part}に関する投稿です✨")
        
        # ユーザー指示がある場合は内容を反映
        if user_instruction and user_instruction.strip():
            instruction_keywords = user_instruction.strip()
            if "可愛い" in instruction_keywords:
                fallback_parts.append("可愛らしさを込めて💕")
            elif "綺麗" in instruction_keywords or "美しい" in instruction_keywords:
                fallback_parts.append("美しさをお楽しみください✨")
            elif "楽しい" in instruction_keywords:
                fallback_parts.append("楽しい気持ちでお届け🎉")
            else:
                fallback_parts.append(f"({instruction_keywords})")
        
        # 適切なハッシュタグを追加
        if any(word in prompt for word in ["夜", "海", "月", "星"]):
            fallback_parts.append("#夜景 #海 #美しい風景")
        elif any(word in prompt for word in ["猫", "動物"]):
            fallback_parts.append("#猫 #可愛い #動物")
        elif any(word in prompt for word in ["花", "自然"]):
            fallback_parts.append("#花 #自然 #美しい")
        elif any(word in prompt for word in ["お買い得", "セール", "コメント", "おすすめ"]):
            fallback_parts.append("#お買い得 #おすすめ")
        elif any(word in prompt for word in ["料理", "食べ物", "グルメ"]):
            fallback_parts.append("#グルメ #美味しい")
        else:
            fallback_parts.append("#AI生成 #画像投稿")
        
        fallback = " ".join(fallback_parts)
        
        # 文字数制限チェック（50-70文字範囲で調整）
        if len(fallback) > 70:
            fallback = fallback[:67] + "..."
        elif len(fallback) < 50:
            fallback += " ✨"
        
        return fallback

    def get_generation_stats(self, cast_id=None, days=7):
        """画像生成統計を取得"""
        from ai_image_db import execute_image_query
        
        # 期間内の生成統計
        stats_query = """
        SELECT 
            COUNT(*) as total_generations,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_generations,
            AVG(CASE WHEN success = 1 THEN generation_time ELSE NULL END) as avg_generation_time,
            DATE(created_at) as generation_date
        FROM img_generation_history 
        WHERE created_at >= DATE('now', '-{} days')
        """.format(days)
        
        if cast_id:
            stats_query += " AND cast_id = ?"
            params = (cast_id,)
        else:
            params = ()
        
        stats_query += " GROUP BY DATE(created_at) ORDER BY generation_date DESC"
        
        return execute_image_query(stats_query, params, fetch="all")

# グローバルインスタンス
ai_image_generator = AIImageGenerator()

# 便利関数
def generate_ai_image(prompt, cast_id=None, cast_name=None):
    """画像生成の便利関数"""
    return ai_image_generator.generate_image(prompt, cast_id, cast_name)

def get_auto_caption(prompt, cast_name=None, cast_id=None, user_instruction=None):
    """自動キャプション生成の便利関数"""
    return ai_image_generator.generate_auto_caption(prompt, cast_name, cast_id, user_instruction)

def check_daily_limits(cast_id=None):
    """日次制限チェックの便利関数"""
    return ai_image_generator.check_generation_limits(cast_id)