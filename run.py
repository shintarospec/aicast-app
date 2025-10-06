#!/usr/bin/env python3
"""
AIcast room アプリケーション起動スクリプト（Python版）
"""
import os
import sys
import subprocess
import socket
import time
import psutil

def check_port_in_use(port):
    """指定されたポートが使用中かチェック"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            return result == 0
    except:
        return False

def find_streamlit_process():
    """Streamlitプロセスを検索"""
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['cmdline']:
                cmdline = ' '.join(proc.info['cmdline'])
                if 'streamlit' in cmdline and 'app.py' in cmdline:
                    return proc.info['pid']
    except:
        pass
    return None

def main():
    print("🚀 AIcast room アプリケーションを起動中...")
    
    # ポート8503の使用状況をチェック（新しいポート）
    port = 8503
    if check_port_in_use(port):
        print(f"⚠️ ポート {port} は既に使用中です")
        
        # Streamlitプロセスを検索
        streamlit_pid = find_streamlit_process()
        if streamlit_pid:
            print(f"✅ AIcast Room は既に起動中です (PID: {streamlit_pid})")
            print(f"🌐 アクセスURL: http://localhost:{port}")
            print("💡 既存のアプリを使用するか、停止してから再起動してください")
            
            # 選択肢を提供
            response = input("\n選択してください:\n1. 既存のアプリを使用 (推奨)\n2. 既存のアプリを停止して再起動\n3. 終了\n選択 (1-3): ").strip()
            
            if response == "1":
                print("✅ 既存のアプリを使用します")
                print(f"🌐 ブラウザで http://localhost:{port} にアクセスしてください")
                return
            elif response == "2":
                print("🛑 既存のアプリを停止中...")
                try:
                    proc = psutil.Process(streamlit_pid)
                    proc.terminate()
                    print(f"✅ プロセス {streamlit_pid} を停止しました")
                    time.sleep(2)  # プロセス停止を待機
                except:
                    print("❌ プロセス停止に失敗しました")
                    return
            else:
                print("👋 終了します")
                return
        else:
            print(f"❌ ポート {port} は他のプロセスで使用中です")
            print("💡 別のポートを使用するか、他のプロセスを停止してください")
            return
    
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
        print("⚠️  Warning: Google Cloud認証が設定されていません")
        print("💡 アプリは起動しますが、AI機能は認証後に利用可能になります")
        print("   認証方法: アプリの「システム設定」→「Google Cloud認証」で設定可能")
    
    # Streamlitアプリケーションを起動
    print(f"🚀 ポート {port} でアプリケーションを起動します...")
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            f"--server.address=0.0.0.0",
            f"--server.port={port}",
            "--server.headless=true"
        ], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ アプリケーションの起動に失敗しました: {e}")
        print("💡 ポートが使用中の可能性があります。再度実行してください。")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n🛑 アプリケーションを停止します...")
        sys.exit(0)

if __name__ == "__main__":
    main()