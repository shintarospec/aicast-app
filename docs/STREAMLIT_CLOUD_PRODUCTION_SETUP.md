# 🎖️ Streamlit Cloud Production Environment Setup Guide

## 🚀 MCF保護を維持したStreamlit Cloud本番環境構築

**Date**: October 4, 2025  
**Target**: Production-ready deployment with MCF protection

---

## 📋 Phase 1: Pre-Deployment Analysis

### 🎖️ Current MCF Configuration Status
```python
# config.py - MCF Protected Settings
_MCF_CLOUD_FUNCTIONS_URL = "https://asia-northeast1-aicast-472807.cloudfunctions.net/x-poster"
GCP_PROJECT = "aicast-472807"
TEST_ACCOUNT_ID = "shinrepoto"
```

### 📊 Environment Requirements Analysis

#### ✅ Current Dependencies (requirements.txt)
```
streamlit          # ✅ Core framework
pandas            # ✅ Data processing
google-cloud-aiplatform  # ✅ Vertex AI
gspread           # ✅ Google Sheets
google-auth       # ✅ Authentication
tweepy            # ❌ Not used - can remove
psutil            # ❌ Not used - can remove
```

#### 🔧 Additional Dependencies Needed
```
requests          # ✅ Cloud Functions calls
sqlite3           # ✅ Built-in Python
```

---

## 📋 Phase 2: Production Code Optimization

### 🎖️ MCF Environment Variables Strategy
```python
# Production-ready config.py modifications needed:

class Config:
    # 🎖️ MCF Production Configuration
    _MCF_CLOUD_FUNCTIONS_URL = os.environ.get(
        'MCF_CLOUD_FUNCTIONS_URL', 
        "https://asia-northeast1-aicast-472807.cloudfunctions.net/x-poster"
    )
    
    GCP_PROJECT = os.environ.get('GCP_PROJECT', 'aicast-472807')
    
    # Database path for Streamlit Cloud
    DATABASE_PATH = os.environ.get('DATABASE_PATH', "casting_office.db")
```

### 📱 Streamlit Cloud Adaptations
```python
# app.py modifications for production:

# 1. Database initialization for cloud environment
def initialize_database_for_cloud():
    """Initialize database for Streamlit Cloud environment"""
    if not os.path.exists(Config.DATABASE_PATH):
        # Create database with required tables
        create_initial_database()

# 2. Google Cloud authentication handling
def setup_gcp_auth_for_streamlit_cloud():
    """Setup GCP authentication for Streamlit Cloud"""
    # Use Streamlit secrets for service account
    if "gcp_service_account" in st.secrets:
        credentials_info = st.secrets["gcp_service_account"]
        # Initialize Vertex AI with credentials
```

---

## 📋 Phase 3: Secrets Management

### 🔐 Streamlit Cloud Secrets Configuration

#### Required Secrets in `.streamlit/secrets.toml`:
```toml
# GCP Configuration
[gcp_service_account]
type = "service_account"
project_id = "aicast-472807"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@aicast-472807.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"

# MCF Configuration
[mcf_config]
MCF_CLOUD_FUNCTIONS_URL = "https://asia-northeast1-aicast-472807.cloudfunctions.net/x-poster"
GCP_PROJECT = "aicast-472807"

# Google Sheets Configuration (if needed)
[google_sheets]
type = "service_account"
# ... (same structure as gcp_service_account)
```

### 🛡️ MCF Protection in Production
```python
# Enhanced MCF validation for production
@classmethod
def validate_mcf_settings_production(cls):
    """Production MCF validation with Streamlit Cloud support"""
    errors = []
    
    # MCF URL validation
    mcf_url = os.environ.get('MCF_CLOUD_FUNCTIONS_URL') or cls._MCF_CLOUD_FUNCTIONS_URL
    if not mcf_url or not mcf_url.startswith("https://"):
        errors.append("🚨 MCF ALERT: Cloud Functions URL validation failed")
    
    # Production environment check
    if "MCF_CLOUD_FUNCTIONS_URL" in st.secrets.get("mcf_config", {}):
        production_url = st.secrets["mcf_config"]["MCF_CLOUD_FUNCTIONS_URL"]
        if production_url != cls._MCF_CLOUD_FUNCTIONS_URL:
            errors.append("🚨 MCF ALERT: Production URL mismatch detected")
    
    return errors
```

---

## 📋 Phase 4: Production Deployment Steps

### 🚀 Step-by-Step Deployment Process

#### Step 1: Repository Preparation
```bash
# 1. Ensure clean repository state
git status
git add .
git commit -m "🎖️ Production deployment preparation with MCF protection"
git push origin main
```

#### Step 2: Streamlit Cloud App Creation
```markdown
1. 📱 Visit: https://share.streamlit.io/
2. 🔐 Connect GitHub account
3. 📂 Select repository: shintarospec/aicast-app
4. 📄 Main file path: app.py
5. 🌿 Branch: main
```

#### Step 3: Environment Configuration
```markdown
1. 🔧 Advanced settings
2. 📚 Python version: 3.10
3. 📦 Requirements file: requirements.txt
4. 🔐 Secrets management setup
```

#### Step 4: Secrets Deployment
```markdown
1. 📋 Copy secrets.toml content
2. 🔐 Paste into Streamlit Cloud secrets manager
3. ✅ Validate all secrets are properly set
4. 🎖️ Confirm MCF configuration
```

---

## 📋 Phase 5: Post-Deployment Validation

### 🎖️ MCF Production Testing Protocol

#### MCF Functionality Tests
```python
# Production MCF test checklist:
✅ Cloud Functions connectivity test
✅ MCF configuration validation
✅ Database initialization
✅ Vertex AI authentication
✅ Google Sheets integration (optional)
✅ Test account posting (shinrepoto)
✅ Production account posting (156_syoy)
✅ Scheduling system integration
```

#### Production Environment Monitoring
```python
# Real-time MCF monitoring for production:
def production_mcf_health_check():
    """Production environment MCF health monitoring"""
    checks = {
        "mcf_url": test_mcf_cloud_functions(),
        "database": test_database_connectivity(),
        "auth": test_gcp_authentication(),
        "scheduling": test_scheduling_integration()
    }
    return all(checks.values())
```

---

## 🔄 Phase 6: CI/CD Integration

### 🚀 Automated Deployment Pipeline
```yaml
# .github/workflows/streamlit-deploy.yml (future enhancement)
name: MCF Protected Streamlit Deployment
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: MCF Protection Validation
        run: python test_existing_functions.py
      - name: Deploy to Streamlit Cloud
        # Automatic deployment trigger
```

---

## ⚡ Quick Deployment Checklist

### 🎯 Pre-Deployment (5 minutes)
- [ ] Update requirements.txt (remove unused dependencies)
- [ ] Add environment variable support to config.py
- [ ] Test MCF protection functions
- [ ] Prepare secrets.toml

### 🚀 Deployment (10 minutes)
- [ ] Create Streamlit Cloud app
- [ ] Configure secrets management
- [ ] Deploy application
- [ ] Initial functionality test

### ✅ Post-Deployment (5 minutes)
- [ ] MCF connectivity verification
- [ ] Test account posting test
- [ ] Production environment validation
- [ ] Monitoring setup

---

## 🎖️ Expected Production Benefits

### 🌟 Production Advantages
- **🚀 Instant Global Access**: Worldwide availability
- **⚡ Zero Server Management**: Fully managed infrastructure
- **🛡️ MCF Protection Maintained**: All critical functions preserved
- **📊 Built-in Analytics**: Usage monitoring included
- **🔐 Enterprise Security**: Streamlit Cloud security standards

### 📈 Performance Expectations
- **🌍 Global CDN**: Fast loading worldwide
- **⚡ Auto-scaling**: Handle traffic spikes
- **🔄 Auto-updates**: Automatic deployment on git push
- **📱 Mobile Optimized**: Responsive design

---

## 🎯 Ready for Production!

With this comprehensive plan, **AIcast Room** will maintain complete **MCF (Mission-Critical Functions)** protection while gaining all the benefits of professional cloud deployment.

**Next Action**: Begin Phase 2 - Production Code Optimization

Let's make AIcast Room production-ready! 🚀🎖️