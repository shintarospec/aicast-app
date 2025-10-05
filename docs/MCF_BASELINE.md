# MCF Baseline State - Mission Critical Functions

**Version:** 2.0 (Stable Production Baseline)  
**Date:** 2025-01-04  
**Status:** 🎖️ MISSION CRITICAL - PROTECTED BASELINE

---

## 🚨 CRITICAL WARNING

**This document defines the Mission-Critical Functions (MCF) baseline state.**

- **DO NOT MODIFY** without explicit approval from system administrators
- **ALL CHANGES** must be documented and tested in staging environment first
- **REGRESSION PREVENTION:** This baseline ensures production stability
- **BACKUP REQUIRED:** Always create backup before any MCF modifications

---

## 📋 MCF System Overview

### Core Components

1. **X API Poster** (`x_api_poster.py`)
   - Cloud Functions integration
   - Comprehensive error handling
   - Safety checks and validation
   - Test account protection

2. **Configuration System** (`config.py`)
   - Protected MCF URLs
   - Environment variable support
   - Validation mechanisms
   - Production environment detection

3. **Database Schema** (MCF Tables)
   - `cast_x_credentials`: API key storage
   - `retweet_schedules`: Automated retweet system
   - `send_history`: Posting activity logs

### 🎯 Protected Configuration Values

```python
# MCF Protected Baseline - DO NOT MODIFY
_MCF_CLOUD_FUNCTIONS_URL = "https://asia-northeast1-aicast-472807.cloudfunctions.net/x-poster"
TEST_ACCOUNT_ID = "shinrepoto"
```

---

## 🛡️ Safety Mechanisms

### 1. Test Account Protection
- Only `shinrepoto` account allowed for testing
- Automatic content safety validation
- Prevention of accidental live posting

### 2. Credential Validation
- Complete API key verification
- Required fields validation
- Format checking

### 3. Error Handling
- Timeout protection (30s)
- Connection error recovery
- Comprehensive logging
- Graceful failure modes

---

## 📊 System Architecture

```
AIcast Room (app.py)
     ↓
X API Poster (x_api_poster.py)
     ↓
Google Cloud Functions
     ↓
X API (Twitter)
```

### Cloud Functions Endpoint
- **URL:** `https://asia-northeast1-aicast-472807.cloudfunctions.net/x-poster`
- **Method:** POST
- **Timeout:** 30 seconds
- **Auth:** API key based

---

## 🔧 MCF Functions List

### Core Functions

1. **`post_to_x()`**
   - Primary posting function
   - Full validation pipeline
   - Error recovery mechanisms

2. **`validate_credentials()`**
   - API key validation
   - Completeness checking
   - Format verification

3. **`test_connection()`**
   - Cloud Functions health check
   - Endpoint availability test
   - Network connectivity validation

### Safety Functions

1. **`is_test_account()`**
   - Test account identification
   - Safety check enforcement

2. **`is_safe_test_content()`**
   - Content safety validation
   - Test phrase detection

3. **`validate_mcf_settings()`**
   - Configuration integrity check
   - Baseline validation

---

## 📁 File Structure (MCF Protected)

```
aicast-app/
├── app.py                  # Main application
├── x_api_poster.py        # 🎖️ MCF Core Module
├── config.py              # 🎖️ MCF Configuration
├── run.py                 # Application launcher
├── casting_office.db      # MCF Database
├── requirements.txt       # Dependencies
└── docs/
    ├── MCF_BASELINE.md    # 🎖️ This document
    ├── X_API_GUIDE.md     # API usage guide
    └── DEPLOYMENT.md      # Deployment procedures
```

---

## 🚀 Deployment Checklist

### Pre-Deployment Validation

- [ ] MCF configuration validation passes
- [ ] All required credentials present
- [ ] Cloud Functions endpoint accessible
- [ ] Test account functionality verified
- [ ] Database schema up to date

### Post-Deployment Verification

- [ ] X API posting works
- [ ] Error handling functions properly
- [ ] Logging captures all events
- [ ] Safety checks active
- [ ] Production metrics normal

---

## 🔍 Troubleshooting Guide

### Common Issues

1. **Cloud Functions Timeout**
   - Check network connectivity
   - Verify endpoint URL
   - Review Cloud Functions logs

2. **Credential Validation Failure**
   - Verify all API keys present
   - Check key format validity
   - Confirm account permissions

3. **Safety Check Failures**
   - Verify test account configuration
   - Check content safety filters
   - Review account ID matching

### Emergency Procedures

1. **MCF System Failure**
   - Revert to last known good configuration
   - Contact system administrator
   - Document failure details

2. **Configuration Corruption**
   - Restore from MCF baseline
   - Validate all settings
   - Test functionality before production

---

## 📈 Performance Metrics

### Response Time Targets
- Cloud Functions: < 5 seconds
- Database queries: < 1 second
- UI responsiveness: < 2 seconds

### Reliability Targets
- Uptime: 99.9%
- Success rate: > 95%
- Error recovery: < 30 seconds

---

## 🔒 Security Considerations

### API Key Protection
- Never log full API keys
- Use environment variables in production
- Rotate keys regularly

### Access Control
- Test account restrictions enforced
- Production posting limited to authorized casts
- Admin functions protected

---

## 📝 Change Log

### Version 2.0 (2025-01-04)
- ✅ Stable MCF baseline established
- ✅ Comprehensive error handling added
- ✅ Safety mechanisms implemented
- ✅ Production environment support

### Version 1.0 (Previous)
- Basic X API integration
- Simple posting functionality
- Limited error handling

---

## 🎖️ MCF Compliance Certificate

**This document certifies that the AIcast Room MCF system meets all requirements for:**

- ✅ Production stability
- ✅ Error resilience  
- ✅ Safety compliance
- ✅ Performance standards
- ✅ Security protocols

**Certified by:** AIcast Room Development Team  
**Valid until:** Next major system update  
**Review required:** Before any MCF modifications

---

**🛡️ Remember: MCF systems are MISSION CRITICAL. Handle with extreme care.**