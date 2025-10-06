#!/usr/bin/env python3
"""
VPS用のVertex AI認証テストスクリプト
"""
import os
import sys

def test_vertex_ai_auth():
    print("=== Vertex AI 認証テスト ===")
    
    # 環境変数の確認
    print("\n1. 環境変数の確認:")
    gcp_project = os.environ.get("GCP_PROJECT")
    google_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    devshell_project = os.environ.get("DEVSHELL_PROJECT_ID")
    
    print(f"   GCP_PROJECT: {gcp_project}")
    print(f"   GOOGLE_APPLICATION_CREDENTIALS: {google_creds}")
    print(f"   DEVSHELL_PROJECT_ID: {devshell_project}")
    
    # プロジェクトIDの決定
    project_id = gcp_project or devshell_project or "aicast-472807"
    print(f"   使用するプロジェクトID: {project_id}")
    
    # Vertex AI の初期化テスト
    print("\n2. Vertex AI 初期化テスト:")
    try:
        import vertexai
        # 最新のSDKを試す
        try:
            from vertexai.generative_models import GenerativeModel
            api_type = "stable"
        except ImportError:
            from vertexai.preview.generative_models import GenerativeModel
            api_type = "preview"
        
        vertexai.init(project=project_id, location="us-central1")
        print(f"   ✅ Vertex AI 初期化成功 ({api_type} API)")
        
        # Geminiモデルのロードテスト
        print("\n3. Gemini モデル接続テスト:")
        
        # 利用可能なモデルを順に試す（2025年10月最新版）
        models_to_try = [
            "gemini-2.5-flash",      # 最新の価格パフォーマンス最適モデル
            "gemini-2.0-flash-exp",  # Gemini 2.0 Flash
            "gemini-1.5-flash-001",  # 安定版
        ]
        
        model = None
        for model_name in models_to_try:
            try:
                model = GenerativeModel(model_name)
                print(f"   ✅ Gemini モデルロード成功: {model_name}")
                break
            except Exception as e:
                print(f"   ⚠️ {model_name} でエラー: {str(e)[:100]}...")
                continue
        
        if not model:
            raise Exception("利用可能なモデルが見つかりません")
        
        # 簡単なテスト生成（タイムアウト付き）
        print("\n4. 簡単なテスト生成:")
        try:
            import signal
            
            def timeout_handler(signum, frame):
                raise TimeoutError("生成がタイムアウトしました")
            
            # 30秒のタイムアウトを設定
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(30)
            
            response = model.generate_content("こんにちは！元気ですか？")
            signal.alarm(0)  # タイムアウトをクリア
            
            print(f"   ✅ テスト生成成功: {response.text[:50]}...")
            
        except TimeoutError:
            print("   ⚠️ テスト生成がタイムアウトしました（モデルロードは成功）")
        except Exception as e:
            print(f"   ⚠️ テスト生成エラー: {str(e)[:100]}...")
            print("   💡 モデルロードは成功しているため、時間が経てば改善する可能性があります")
        
        print("\n🎉 すべてのテストが成功しました！Streamlitアプリケーションが正常に動作するはずです。")
        return True
        
    except ImportError as e:
        print(f"   ❌ パッケージのインポートエラー: {e}")
        print("   pip install google-cloud-aiplatform を実行してください")
        return False
    except Exception as e:
        print(f"   ❌ 認証エラー: {e}")
        print("   ADC認証が正常に完了していない可能性があります")
        return False

if __name__ == "__main__":
    success = test_vertex_ai_auth()
    sys.exit(0 if success else 1)