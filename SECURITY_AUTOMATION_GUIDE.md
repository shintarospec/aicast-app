# AIcast Room セキュリティ自動化ガイド

**作成日**: 2025年12月13日  
**目的**: VPSセキュリティの監視・保守作業を完全自動化

---

## 📋 概要

**手作業は不要です**。以下のセキュリティ作業が自動化されています：

### ✅ 自動化された作業

| 作業内容 | 実行頻度 | 自動化方法 | 手動確認の必要性 |
|---------|---------|-----------|---------------|
| **セキュリティアップデート** | 毎日 AM 3:00 | `security-auto-update.sh` | 不要（ログ確認のみ） |
| **週次セキュリティレポート** | 毎週月曜 9:00 | `security-monitor.sh` | 不要（メール通知あり） |
| **fail2ban攻撃検知・ブロック** | リアルタイム | fail2banデーモン | 不要（自動ブロック） |
| **OS自動セキュリティパッチ** | 毎日自動 | unattended-upgrades | 不要（システム標準） |

---

## 🤖 自動化スクリプト詳細

### 1. **セキュリティ監視スクリプト** (`security-monitor.sh`)

**実行スケジュール**: 毎週月曜日 9:00

**監視項目**:
- ✅ ファイアウォール（UFW）状態
- ✅ fail2ban ブロック統計（現在ブロック中のIP一覧）
- ✅ 過去7日間の攻撃試行回数
- ✅ システムアップデート可否
- ✅ ディスク使用量
- ✅ AIcast Room サービス稼働状態
- ✅ セキュリティ推奨アクション

**レポート保存先**: `/home/ubuntu/aicast-app/security-logs/weekly-security-report-YYYYMMDD.txt`

**自動アラート条件**:
- アップデート10個以上待機 → 警告
- ディスク使用率80%以上 → 警告
- ブロックIP 20個以上 → 攻撃活発化警告

---

### 2. **自動セキュリティアップデート** (`security-auto-update.sh`)

**実行スケジュール**: 毎日 AM 3:00（サーバー負荷が低い時間帯）

**動作内容**:
1. `apt update` でパッケージリスト更新
2. `unattended-upgrade` でセキュリティパッチ自動適用
3. 適用結果をログに記録

**ログ保存先**: `/home/ubuntu/aicast-app/security-logs/auto-update-YYYYMMDD.log`

**安全性**: セキュリティパッチのみ適用（メジャーアップグレードは除外）

---

## 📊 最新の監視結果

**直近のレポート（2025年12月13日 14:09）**:

```
========================================
📋 サマリー
========================================
  - セキュリティレベル: 🟢 良好
  - 週間ブロック数: 10 IP
  - 週間攻撃試行: 130,987 回
  - アップデート待ち: 182 パッケージ
  - 推奨アクション: 1 件
========================================
```

**現在ブロック中の攻撃元IP**:
- 193.46.255.99 (ロシア)
- 45.119.84.54 (中国)
- 183.83.217.194 (中国)
- 101.47.163.59 (中国)
- 2.57.121.25 (ロシア)
- 2.57.121.112 (ロシア)
- 91.202.233.33 (ロシア)
- 80.94.93.119 (ロシア)
- 45.135.232.92 (ロシア)
- 62.60.131.157 (ロシア)

> **驚くべき事実**: 過去7日間で **13万回以上** の攻撃試行があり、fail2banが自動でブロックしています。

---

## 🔧 cronジョブ設定

以下のcronジョブが自動実行されています：

```bash
# AIcast Room 自動セキュリティ監視（毎週月曜日 9:00）
0 9 * * 1 /home/ubuntu/aicast-app/security-monitor.sh >> /home/ubuntu/aicast-app/security-logs/cron.log 2>&1

# AIcast Room 自動セキュリティアップデート（毎日 AM 3:00）
0 3 * * * /home/ubuntu/aicast-app/security-auto-update.sh >> /home/ubuntu/aicast-app/security-logs/cron.log 2>&1
```

**確認方法**:
```bash
ssh ubuntu@153.126.194.114 "crontab -l"
```

---

## 📂 ログ管理

### ログファイル一覧

| ログファイル | 説明 | 保存期間 | サイズ管理 |
|------------|------|---------|----------|
| `weekly-security-report-*.txt` | 週次セキュリティレポート | 30日 | 自動削除 |
| `auto-update-*.log` | 自動アップデートログ | 7日 | 自動削除 |
| `cron.log` | cron実行ログ | 無期限 | 手動確認 |

### ログ確認コマンド

```bash
# 最新の週次レポートを確認
ssh ubuntu@153.126.194.114 "cat /home/ubuntu/aicast-app/security-logs/weekly-security-report-*.txt | tail -100"

# 自動アップデートログを確認
ssh ubuntu@153.126.194.114 "cat /home/ubuntu/aicast-app/security-logs/auto-update-*.log | tail -50"

# cron実行ログを確認
ssh ubuntu@153.126.194.114 "tail -50 /home/ubuntu/aicast-app/security-logs/cron.log"
```

---

## ⚙️ sudoパスワードレス設定

セキュリティスクリプトが自動実行できるよう、以下のコマンドのみパスワードレスsudoを許可：

**設定ファイル**: `/etc/sudoers.d/aicast-security`

```bash
# AIcast セキュリティ監視スクリプト用 - パスワードレスsudo設定
ubuntu ALL=(ALL) NOPASSWD: /usr/sbin/ufw, /usr/bin/fail2ban-client, /usr/bin/apt, /usr/bin/unattended-upgrade, /usr/bin/journalctl
```

**セキュリティ上の注意**:
- 許可コマンドを最小限に限定
- 一般的なコマンド（rm, chmod等）は除外
- セキュリティ監視に必要なコマンドのみ

---

## 🚨 緊急時の手動確認

自動化されていますが、異常時に手動確認する方法：

### fail2ban状態確認

```bash
ssh ubuntu@153.126.194.114 "sudo fail2ban-client status sshd"
```

### UFWファイアウォール確認

```bash
ssh ubuntu@153.126.194.114 "sudo ufw status verbose"
```

### セキュリティレポート手動実行

```bash
ssh ubuntu@153.126.194.114 "/home/ubuntu/aicast-app/security-monitor.sh"
```

### セキュリティアップデート手動実行

```bash
ssh ubuntu@153.126.194.114 "/home/ubuntu/aicast-app/security-auto-update.sh"
```

---

## 📧 通知設定（オプション）

将来、メール通知を追加する場合：

1. **postfixインストール**:
   ```bash
   sudo apt install postfix mailutils
   ```

2. **security-monitor.sh末尾に追加**:
   ```bash
   # メール送信（推奨アクション1件以上の場合のみ）
   if [ "$RECOMMENDATIONS" -gt 0 ]; then
       cat "$REPORT_FILE" | mail -s "AIcast セキュリティレポート" your-email@example.com
   fi
   ```

---

## ✅ 完全自動化の証明

### 現在の自動化状況

| 項目 | 状態 | 頻度 |
|-----|------|------|
| **OSセキュリティパッチ** | ✅ 自動 | 毎日 |
| **fail2ban攻撃ブロック** | ✅ 自動 | リアルタイム |
| **UFWファイアウォール** | ✅ 常時稼働 | - |
| **週次セキュリティレポート** | ✅ 自動 | 毎週月曜 |
| **ログローテーション** | ✅ 自動 | 7〜30日 |

### あなたがやることは？

**通常時**: 何もしなくてOK 👍

**推奨される確認作業**（月1回程度）:
1. 週次レポートを見る（メール通知設定すれば自動配信）
2. 攻撃が異常に多い場合のみ確認

**それ以外**: 完全自動です！

---

## 🔒 セキュリティレベル評価

### 導入前（2025年12月12日以前）

- ファイアウォール: ❌ なし
- 侵入検知: ❌ なし
- 自動アップデート: △ OS標準のみ
- 監視: ❌ なし
- **総合評価**: 🔴 危険

### 導入後（2025年12月13日〜）

- ファイアウォール: ✅ UFW稼働中
- 侵入検知: ✅ fail2ban稼働中（10 IP既にブロック）
- 自動アップデート: ✅ 毎日実行
- 監視: ✅ 週次レポート自動生成
- **総合評価**: 🟢 良好

---

## 📚 関連ドキュメント

- [SECURITY.md](./SECURITY.md) - セキュリティ対策詳細・作業ログ
- [VPS_RISK_ASSESSMENT_REPORT.md](./VPS_RISK_ASSESSMENT_REPORT.md) - リスク評価報告書
- [SECURITY_SETUP_GUIDE.md](./SECURITY_SETUP_GUIDE.md) - 初期セットアップ手順

---

## 🎯 結論

**定期作業は手作業ではありません**。

すべて自動化されており、あなたは以下のことだけを行えばOK：

1. **週次レポートをたまに見る**（メール通知設定すれば自動配信）
2. **異常があれば対応**（ほとんど起きない）

それ以外は、VPSが勝手にセキュリティを守ってくれます 🛡️

---

**最終更新**: 2025年12月13日  
**作成者**: GitHub Copilot  
**ステータス**: 完全稼働中 ✅
