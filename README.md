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
4. **🆕 [新プロンプト構造仕様](./directories/docs/NEW_PROMPT_STRUCTURE.md)** - 2025年10月の大規模リファクタリング ★NEW
5. **🎨 [スタイル仕様書](./STYLE_SPECIFICATION.md)** - サイバーパンク調UIデザインガイド ★NEW

---

## 👥 **キャスト管理担当者向け**

1. **👤 [キャスト別X API設定](./docs/CAST_SPECIFIC_X_API_GUIDE.md)** - アカウント管理
2. **🆕 [新プロンプト構造 & CSV一括管理](./directories/docs/NEW_PROMPT_STRUCTURE.md)** - キャスト登録の新方式 ★NEW
3. **🛡️ [セキュリティ対策](./docs/SCHEDULE_POSTING_DEVELOPMENT_HISTORY.md#-セキュリティとエラーハンドリング)** - 安全な運用
4. **📊 [現在の稼働状況](./docs/SCHEDULE_POSTING_DEVELOPMENT_HISTORY.md#-現在の稼働状況)** - システム状態確認

---

## 🖥️ **サーバー管理者向け**

1. **🖥️ [Sakura VPS運用手順](./docs/README_SAKURA_VPS.md)** - 本番環境管理
2. **⚡ [デプロイ最適化](./docs/deployment_optimization.md)** - 効率的な運用
3. **💰 [コスト最適化](./docs/gemini_cost_optimization.md)** - 費用管理
4. **📊 [DBマイグレーションプロジェクト](./DB_MIGRATION_PROJECT.md)** - データベース更新管理 ★NEW

---

## 📁 **ドキュメント構成**

```
📂 プロジェクトルート/
├── 📊 DB_MIGRATION_PROJECT.md                # DBマイグレーション状態記録 ★NEW
└── 📂 docs/
    ├── 📖 README.md                              # 総合目次
    ├── 📋 SCHEDULE_POSTING_DEVELOPMENT_HISTORY.md # 🌟 開発履歴（最重要）
    ├── 🔑 X_API_IMPLEMENTATION_GUIDE.md          # X API実装ガイド
    ├── 👥 CAST_SPECIFIC_X_API_GUIDE.md           # キャスト別設定
    ├── ☁️ MINIMAL_GCP_IMPLEMENTATION.md          # GCP実装ガイド
    ├── 📚 MINIMAL_GCP_GUIDE.md                   # GCP基本ガイド
    ├── 🖥️ README_SAKURA_VPS.md                  # Sakura VPS運用
    ├── ⚡ deployment_optimization.md             # デプロイ最適化
    ├── 💰 gemini_cost_optimization.md           # コスト最適化
    └── 🎯 STRATEGY_COMPLETE.md                   # 戦略ドキュメント

📂 directories/docs/
└── 🆕 NEW_PROMPT_STRUCTURE.md                # 新プロンプト構造仕様 ★NEW

📂 migrations/
├── 📋 README.md                              # マイグレーション手順書 ★NEW
└── 🗃️ 20251026_add_prompt_tables.sql        # プロンプトテーブル追加SQL ★NEW
```

---

## 📊 **システム状態**

### 🗄️ データベース
- ✅ **ローカルDB**: 新プロンプト構造対応完了（2025-10-27）
- ⏸️ **本番DB**: マイグレーション適用保留中
- 📋 **詳細**: [DB_MIGRATION_PROJECT.md](./DB_MIGRATION_PROJECT.md) 参照

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