#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""既存の承認済み投稿を一括予約実行するスクリプト"""

import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# app.pyから必要な関数をインポート
from app import batch_schedule_all_approved_posts, init_db

def main():
    print("=== 承認済み投稿の一括予約実行 ===")
    
    # データベース初期化
    init_db()
    
    # 一括予約実行
    count, message = batch_schedule_all_approved_posts()
    
    print(f"結果: {message}")
    print(f"予約件数: {count}件")
    
    return 0 if count > 0 else 1

if __name__ == "__main__":
    sys.exit(main())
