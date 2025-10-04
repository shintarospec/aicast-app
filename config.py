# AIcast Room 設定ファイル
# 新機能追加時は既存設定を変更しないこと！

import os

class Config:
    """
    Centralized Configuration Management System
    ⚠️ MCF: Mission-Critical Functions configuration is protected!
    🌐 Production: Streamlit Cloud environment support
    """
    
    # 🎖️ Mission-Critical Functions (MCF) Configuration - Protected!
    # Production stable baseline - 2025-10-04
    _MCF_CLOUD_FUNCTIONS_URL = "https://asia-northeast1-aicast-472807.cloudfunctions.net/x-poster"
    
    # Cloud Functions configuration (MCF Protected + Production Support)
    CLOUD_FUNCTIONS_URL = os.environ.get('MCF_CLOUD_FUNCTIONS_URL', _MCF_CLOUD_FUNCTIONS_URL)
    
    # Google Cloud設定 (Production Environment Support)
    GCP_PROJECT = os.environ.get('GCP_PROJECT', 'aicast-472807')
    
    # データベース設定 (Streamlit Cloud Compatible)
    DATABASE_PATH = os.environ.get('DATABASE_PATH', "casting_office.db")
    
    # Vertex AI設定 (Production Environment)
    VERTEX_AI_LOCATION = os.environ.get('VERTEX_AI_LOCATION', "asia-northeast1")
    
    # ログ設定 (Production Environment)
    SCHEDULE_LOG_PATH = os.environ.get('SCHEDULE_LOG_PATH', "schedule.log")
    RETWEET_LOG_PATH = os.environ.get('RETWEET_LOG_PATH', "retweet.log")
    
    # テスト投稿設定
    TEST_POSTS = [
        "🔧",  # メンテナンス
        "⚡",  # 動作確認
        "🚀",  # システムテスト
        "✅",  # 正常動作確認
        "🔍",  # 接続テスト
        "🛠️",  # システム調整
        "📡",  # 通信テスト
        "🎯",  # 機能テスト
    ]
    
    # テストアカウント設定（安全性確保）
    TEST_ACCOUNT_ID = "shinrepoto"  # テスト専用アカウント
    
    @classmethod
    def get_test_account_id(cls):
        """
        テスト専用アカウントIDを取得
        安全性のため、テストは指定されたアカウントのみで実行
        """
        return cls.TEST_ACCOUNT_ID
    
    @classmethod
    def is_test_account(cls, account_id):
        """
        指定されたアカウントがテスト用アカウントかチェック
        """
        return account_id == cls.TEST_ACCOUNT_ID
    
    @classmethod
    def get_test_post(cls):
        """
        安全なテスト投稿用絵文字を取得
        「テストです」などの明示的なテスト文言は使用しない
        """
        import random
        return random.choice(cls.TEST_POSTS)
    
    @classmethod
    def is_safe_test_content(cls, text):
        """
        テスト投稿として安全かチェック
        「テスト」「test」などの文言が含まれていないか確認
        """
        unsafe_words = ['テスト', 'test', 'Test', 'TEST', 'てすと']
        text_lower = text.lower()
        return not any(word.lower() in text_lower for word in unsafe_words)
    
    @classmethod
    def get_cloud_functions_url(cls):
        """
        Get Mission-Critical Functions (MCF) Cloud Functions URL
        🎖️ MCF: This value is used by mission-critical production systems!
        🌐 Production: Environment variable support for Streamlit Cloud
        Refer to MCF_BASELINE.md before making any changes!
        """
        return os.environ.get('MCF_CLOUD_FUNCTIONS_URL', cls._MCF_CLOUD_FUNCTIONS_URL)
    
    @classmethod
    def validate_mcf_settings(cls):
        """
        Validate Mission-Critical Functions (MCF) configuration integrity
        🌐 Production: Enhanced validation for Streamlit Cloud environment
        This check prevents MCF regression and ensures production stability
        """
        errors = []
        
        # MCF URL validation (with environment variable support)
        current_url = cls.get_cloud_functions_url()
        if current_url != cls._MCF_CLOUD_FUNCTIONS_URL:
            # Allow environment variable override but validate format
            if not current_url.startswith("https://"):
                errors.append("🚨 MCF ALERT: Cloud Functions URL must start with https")
            elif "asia-northeast1-aicast-472807.cloudfunctions.net" not in current_url:
                errors.append("🚨 MCF ALERT: Cloud Functions URL project mismatch")
        
        if not current_url:
            errors.append("🚨 MCF ALERT: Cloud Functions URL not configured")
        
        # MCF Test account validation
        if not cls.TEST_ACCOUNT_ID:
            errors.append("🚨 MCF ALERT: Test account ID is not configured")
        
        if cls.TEST_ACCOUNT_ID != "shinrepoto":
            errors.append("🚨 MCF ALERT: Test account has been modified!")
            
        return errors
    
    @classmethod
    def is_production_environment(cls):
        """
        Check if running in Streamlit Cloud production environment
        """
        return 'STREAMLIT_CLOUD' in os.environ or 'STREAMLIT_SHARING' in os.environ
    
    @classmethod
    def get_production_config_summary(cls):
        """
        Get production configuration summary for monitoring
        """
        return {
            "mcf_url": cls.get_cloud_functions_url(),
            "gcp_project": cls.GCP_PROJECT,
            "database_path": cls.DATABASE_PATH,
            "is_production": cls.is_production_environment(),
            "test_account": cls.TEST_ACCOUNT_ID
        }
    
    @classmethod
    def validate_config(cls):
        """設定の妥当性をチェック"""
        errors = []
        
        if not cls.CLOUD_FUNCTIONS_URL:
            errors.append("CLOUD_FUNCTIONS_URL が設定されていません")
            
        if not cls.CLOUD_FUNCTIONS_URL.startswith("https://"):
            errors.append("CLOUD_FUNCTIONS_URL は https で始まる必要があります")
            
        return errors

# 設定の妥当性チェック
_config_errors = Config.validate_config()
if _config_errors:
    print("⚠️ 設定エラー:")
    for error in _config_errors:
        print(f"  - {error}")