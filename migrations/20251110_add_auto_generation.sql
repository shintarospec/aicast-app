-- ================================================
-- 投稿案自動生成機能のためのマイグレーション
-- 作成日: 2025-11-10
-- 機能: キャスト別の自動生成スケジュール設定
-- ================================================

-- 自動生成設定テーブル
CREATE TABLE IF NOT EXISTS auto_generation_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cast_id INTEGER NOT NULL,
    
    -- 自動生成の基本設定
    enabled INTEGER DEFAULT 0,              -- 自動生成ON/OFF (0=OFF, 1=ON)
    frequency TEXT DEFAULT 'daily',         -- 生成頻度 ('daily', 'weekly', 'custom')
    generation_time TEXT,                   -- 生成時刻 ('09:00', '14:00' など HH:MM形式)
    posts_per_day INTEGER DEFAULT 10,       -- 1日の生成件数
    
    -- 実行履歴
    last_generated_at DATETIME,             -- 最終生成日時
    total_generated INTEGER DEFAULT 0,      -- 累計生成数
    
    -- メタデータ
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- 外部キー制約
    FOREIGN KEY (cast_id) REFERENCES casts(id) ON DELETE CASCADE
);

-- インデックス作成（パフォーマンス最適化）
CREATE INDEX IF NOT EXISTS idx_auto_gen_cast_id ON auto_generation_settings(cast_id);
CREATE INDEX IF NOT EXISTS idx_auto_gen_enabled ON auto_generation_settings(enabled);
CREATE INDEX IF NOT EXISTS idx_auto_gen_time ON auto_generation_settings(generation_time);

-- 自動生成実行ログテーブル（オプション：将来の監視・デバッグ用）
CREATE TABLE IF NOT EXISTS auto_generation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cast_id INTEGER NOT NULL,
    execution_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    posts_generated INTEGER DEFAULT 0,      -- 生成成功数
    posts_failed INTEGER DEFAULT 0,         -- 生成失敗数
    status TEXT DEFAULT 'success',          -- 'success', 'partial', 'failed'
    error_message TEXT,                     -- エラーメッセージ
    
    FOREIGN KEY (cast_id) REFERENCES casts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_auto_gen_logs_cast_id ON auto_generation_logs(cast_id);
CREATE INDEX IF NOT EXISTS idx_auto_gen_logs_time ON auto_generation_logs(execution_time);

-- ================================================
-- 初期データ（サンプル）
-- ================================================
-- 既存キャストに対してデフォルト設定を追加（全てOFF状態）
INSERT INTO auto_generation_settings (cast_id, enabled, generation_time, posts_per_day)
SELECT id, 0, '09:00', 10
FROM casts
WHERE id NOT IN (SELECT cast_id FROM auto_generation_settings);

-- ================================================
-- マイグレーション完了確認用クエリ
-- ================================================
-- SELECT 'Migration 20251110_add_auto_generation.sql completed successfully' AS status;
