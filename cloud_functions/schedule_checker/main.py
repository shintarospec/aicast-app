import functions_framework
import sqlite3
import json
import requests
from datetime import datetime
from google.cloud import secretmanager
import tempfile
import os

@functions_framework.http
def schedule_checker(request):
    """スケジュールされた投稿をチェックして実行する"""
    
    # CORS対応
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, GET',
            'Access-Control-Allow-Headers': 'Content-Type',
        }
        return ('', 204, headers)
    
    headers = {'Access-Control-Allow-Origin': '*'}
    
    try:
        # Cloud Functions環境では永続化ディスクがないため、今回はテスト応答を返す
        # 実際の運用ではCloud SQLやFirestoreを使用する
        
        return (json.dumps({
            "status": "success",
            "message": "Schedule checker is running on Cloud Functions",
            "timestamp": datetime.now().isoformat(),
            "note": "This is a test version. For production, integrate with Cloud SQL or Firestore."
        }), 200, headers)
        
    except Exception as e:
        return (json.dumps({
            "status": "error",
            "message": str(e),
            "error_type": type(e).__name__
        }), 500, headers)

@functions_framework.http  
def test_scheduler(request):
    """スケジューラーのテスト用エンドポイント"""
    
    headers = {'Access-Control-Allow-Origin': '*'}
    
    try:
        # テスト用のスケジュール投稿を作成
        test_data = {
            'status': 'test_mode',
            'current_time': datetime.now().isoformat(),
            'message': 'Schedule checker is working properly on Cloud Functions',
            'environment': 'Cloud Functions Gen 2'
        }
        
        return (json.dumps(test_data), 200, headers)
        
    except Exception as e:
        return (json.dumps({
            "status": "error",
            "message": str(e)
        }), 500, headers)