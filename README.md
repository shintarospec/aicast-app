# 📚 AIcast Room - 総合ドキュメント

## 🎯 クイックアクセス

### 📖 **[→ 完全なドキュメント目次はこちら](./docs/README.md)**

プロジェクトの全ドキュメントが体系的に整理されています。

---

## ⚡ **緊急時対応**

| 問題 | 解決ドキュメント |
|------|------------------|
| 🚨 予約投稿が動かない | [開発履歴 → トラブルシューティング](./docs/SCHEDULE_POSTING_DEVELOPMENT_HISTORY.md#-重要なトラブルシューティング) |
| 🔧 cronサービス停止 | [開発履歴 → cronサービス停止](./docs/SCHEDULE_POSTING_DEVELOPMENT_HISTORY.md#2-cronサービス停止) |
| 🔑 X API認証エラー | [X API実装ガイド](./docs/X_API_IMPLEMENTATION_GUIDE.md) |
| 🖥️ サーバー障害 | [Sakura VPS運用手順](./docs/README_SAKURA_VPS.md) |

---

## 🚀 **新規開発者向け**

1. **📋 [開発履歴](./docs/SCHEDULE_POSTING_DEVELOPMENT_HISTORY.md)** - システム全体の理解
2. **🔑 [X API実装ガイド](./docs/X_API_IMPLEMENTATION_GUIDE.md)** - 核心技術の習得
3. **☁️ [GCP実装ガイド](./docs/MINIMAL_GCP_IMPLEMENTATION.md)** - 環境構築

---

## 👥 **キャスト管理担当者向け**

1. **👤 [キャスト別X API設定](./docs/CAST_SPECIFIC_X_API_GUIDE.md)** - アカウント管理
2. **🛡️ [セキュリティ対策](./docs/SCHEDULE_POSTING_DEVELOPMENT_HISTORY.md#-セキュリティとエラーハンドリング)** - 安全な運用
3. **📊 [現在の稼働状況](./docs/SCHEDULE_POSTING_DEVELOPMENT_HISTORY.md#-現在の稼働状況)** - システム状態確認

---

## 🖥️ **サーバー管理者向け**

1. **🖥️ [Sakura VPS運用手順](./docs/README_SAKURA_VPS.md)** - 本番環境管理
2. **⚡ [デプロイ最適化](./docs/deployment_optimization.md)** - 効率的な運用
3. **💰 [コスト最適化](./docs/gemini_cost_optimization.md)** - 費用管理

---

## 📁 **ドキュメント構成**

```
📂 docs/
├── 📖 README.md                              # 総合目次（このファイル）
├── 📋 SCHEDULE_POSTING_DEVELOPMENT_HISTORY.md # 🌟 開発履歴（最重要）
├── 🔑 X_API_IMPLEMENTATION_GUIDE.md          # X API実装ガイド
├── 👥 CAST_SPECIFIC_X_API_GUIDE.md           # キャスト別設定
├── ☁️ MINIMAL_GCP_IMPLEMENTATION.md          # GCP実装ガイド
├── 📚 MINIMAL_GCP_GUIDE.md                   # GCP基本ガイド
├── 🖥️ README_SAKURA_VPS.md                  # Sakura VPS運用
├── ⚡ deployment_optimization.md             # デプロイ最適化
├── 💰 gemini_cost_optimization.md           # コスト最適化
└── 🎯 STRATEGY_COMPLETE.md                   # 戦略ドキュメント
```

---

## 📊 **システム状態**

### 現在稼働中のキャスト
- ✅ **shinrepoto** - 完全稼働
- ✅ **4te_123** - 完全稼働  
- ✅ **kawa_saki_style** - 完全稼働
- ⚠️ **kurumibutterfly** - 権限調整中
- ✅ **Hiranonorico** - 完全稼働

### システム稼働状況
- ✅ Cloud Functions: 正常稼働
- ✅ cronジョブ: 5分間隔実行
- ✅ Secret Manager: 自動設定対応
- ✅ セキュリティ: 誤投稿防止完了

---

*詳細な情報は [📖 docs/README.md](./docs/README.md) をご覧ください。*