#!/usr/bin/env python3
"""
AIcast room アプリケーション起動スクリプト（Python版）
"""
import os
import sys
import subprocess

def main():
    print("🚀 AIcast room アプリケーションを起動中...")
    
    # Google Cloud認証設定
    os.environ["GCP_PROJECT"] = "aicast-472807"
    
    # Application Default Credentials (ADC) の確認
    adc_file = os.path.expanduser("~/.config/gcloud/application_default_credentials.json")
    google_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    
    if os.path.exists(adc_file):
        print("✅ Google Cloud Application Default Credentials 確認完了")
        print(f"📍 認証ファイル: {adc_file}")
    elif google_creds and os.path.exists(google_creds):
        print("✅ Google Cloud Service Account Key 確認完了")
        print(f"📍 認証ファイル: {google_creds}")
    else:
        print("❌ Error: Google Cloud認証が設定されていません")
        print("💡 以下のいずれかの方法で認証を設定してください:")
        print("   1. gcloud auth application-default login")
        print("   2. export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json")
        sys.exit(1)
    
    # Streamlitアプリケーションを起動
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.address=0.0.0.0",
            "--server.port=8501",
            "--server.headless=true"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ アプリケーションの起動に失敗しました: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 アプリケーションを停止します...")
        sys.exit(0)

if __name__ == "__main__":
    main()