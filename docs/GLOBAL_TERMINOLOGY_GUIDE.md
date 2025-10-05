# �️ Global Terminology Guide - Mission-Critical Functions (MCF)

## Overview
This document establishes the global terminology standards for the AIcast Room system, with **Mission-Critical Functions (MCF)** as the highest-tier designation for essential system operations.

## 🎖️ MCF (Mission-Critical Functions) Tier
**Definition**: Core system operations that are absolutely essential for system functionality. Any failure in MCF components results in system-wide impact and requires immediate attention.

### MCF Components:
- **MCF Post Scheduling**: Core post scheduling functionality (`local_schedule_checker.py`)
- **MCF Retweet Scheduling**: Independent retweet scheduling system (`local_retweet_scheduler.py`)  
- **MCF Cloud Functions**: X API posting infrastructure (x-poster Cloud Functions)
- **MCF Configuration**: Centralized config management with protected settings (`config.py`)
- **MCF Database**: Critical data storage (`casting_office.db`)
- **MCF Cron Scheduling**: System scheduling infrastructure

### MCF Protection Systems:
- **MCF Protection Test System** (`test_existing_functions.py`)
- **MCF Real-time Monitoring** (`monitor_critical_functions.py`)
- **MCF Configuration Validation** (`Config.validate_mcf_settings()`)
- **MCF Regression Prevention** (Development rules and testing)
## 🔧 Configuration Management Terminology

### MCF Configuration Hierarchy:
1. **`_MCF_CLOUD_FUNCTIONS_URL`**: Protected URL configuration
2. **`validate_mcf_settings()`**: MCF validation function
3. **MCF Test Account**: Centralized test account management
4. **MCF Protection**: Regression prevention protocols

## 🚨 Alert and Monitoring Terminology

### MCF Alert Levels:
- **🚨 MCF ALERT**: Critical issues requiring immediate attention
- **⚠️ MCF Warning**: Non-critical issues requiring monitoring
- **✅ MCF Verified**: Successful validation/operation
- **🛡️ MCF Protected**: Successfully protected operations

### MCF Status Messages:
- **"MCF Status: All Mission-Critical Functions operational"**
- **"MCF ALERT: Mission-Critical Functions require attention"**
- **"MCF Protection Test System"**
- **"MCF Real-time Monitoring System"**

## 📋 Development Standards

### MCF Code Standards:
- All MCF components must use consistent terminology
- MCF protection must be implemented for any changes
- MCF validation required before deployment
- MCF monitoring integration mandatory

### MCF Documentation Standards:
- Use 🎖️ emoji for MCF-tier documentation
- Include "Mission-Critical Functions (MCF)" in headers
- Maintain MCF terminology consistency across all files
- Document MCF protection measures

## 🔄 Implementation Status

### ✅ Completed MCF Upgrades:
- [x] `config.py` - MCF configuration management
- [x] `test_existing_functions.py` - MCF Protection Test System
- [x] `monitor_critical_functions.py` - MCF Real-time Monitoring
- [x] `CRITICAL_FUNCTIONS_BASELINE.md` - MCF baseline documentation
- [x] `DEVELOPMENT_RULES.md` - MCF development rules
- [x] `GLOBAL_TERMINOLOGY_GUIDE.md` - This comprehensive guide

### 🔮 Future MCF Enhancements:
- Extended MCF monitoring capabilities
- Advanced MCF protection mechanisms  
- MCF performance optimization
- MCF scalability improvements

## 🎯 Key Principles

1. **MCF Consistency**: All system references to critical functions use MCF terminology
2. **MCF Protection**: Every MCF component has protection and monitoring
3. **MCF Validation**: All MCF operations include validation mechanisms
4. **MCF Documentation**: Comprehensive MCF documentation maintained
5. **MCF Evolution**: Continuous improvement of MCF standards and practices

---

**Last Updated**: December 2024  
**Version**: MCF 1.0  
**Status**: 🎖️ Mission-Critical Functions (MCF) Standard Established
```

## 🎯 Recommended Global Terms

### System Architecture
- **Configuration Management**: 設定管理
- **Critical Functions**: 重要機能
- **Core Functionality**: コア機能
- **Mission-Critical Features**: ミッション重要機能
- **System Regression**: システム退行
- **Rollback Prevention**: 回帰防止
- **Baseline Protection**: ベースライン保護

### Development Process
- **Centralized Configuration**: 集中設定管理
- **Parameter Management**: パラメーター管理
- **Environment Variables**: 環境変数
- **Configuration Validation**: 設定検証
- **Safety Checks**: 安全性チェック

### Quality Assurance
- **Regression Testing**: 回帰テスト
- **Baseline Monitoring**: ベースライン監視
- **Critical Path Protection**: 重要パス保護
- **System Integrity**: システム整合性
- **Continuous Monitoring**: 継続監視

## 📚 Usage Examples

### Documentation Titles
```
❌ Before: 生命線機能の永続的保護
✅ After: Critical Functions - Persistent Protection System

❌ Before: 先祖返り防止
✅ After: Regression Prevention Framework
```

### Code Comments
```python
# ❌ Before
# 生命線機能設定（変更禁止）
CRITICAL_URL = "..."

# ✅ After  
# Critical Functions Configuration (Protected)
CRITICAL_URL = "..."
```

### Function Names
```python
# ❌ Before
def validate_critical_settings():
    """生命線機能の設定が正しいかチェック"""

# ✅ After
def validate_critical_settings():
    """Validate critical functions configuration"""
```

## 🌍 International Standards Alignment

- **ISO/IEC 25010**: Software Quality Model
- **ITIL 4**: IT Service Management
- **DevOps**: Continuous Integration/Deployment
- **SRE**: Site Reliability Engineering

These terms align with global software engineering standards and are widely understood in international development teams.