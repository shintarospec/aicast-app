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
        from vertexai.preview.generative_models import GenerativeModel
        
        vertexai.init(project=project_id, location="asia-northeast1")
        print("   ✅ Vertex AI 初期化成功")
        
        # Geminiモデルのロードテスト
        print("\n3. Gemini モデル接続テスト:")
        model = GenerativeModel("gemini-1.5-pro")
        print("   ✅ Gemini モデルロード成功")
        
        # 簡単なテスト生成
        print("\n4. 簡単なテスト生成:")
        response = model.generate_content("こんにちは！元気ですか？")
        print(f"   ✅ テスト生成成功: {response.text[:50]}...")
        
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