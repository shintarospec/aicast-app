-- ================================================
-- auto_generation_settingsテーブルのUNIQUE制約追加
-- 作成日: 2025-11-10
-- 目的: cast_idにUNIQUE制約を追加してON CONFLICT句を機能させる
-- ================================================

-- 既存テーブルをバックアップ
CREATE TABLE IF NOT EXISTS auto_generation_settings_backup AS 
SELECT * FROM auto_generation_settings;

-- 既存テーブルを削除
DROP TABLE IF EXISTS auto_generation_settings;

-- UNIQUE制約付きで再作成
CREATE TABLE auto_generation_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cast_id INTEGER NOT NULL UNIQUE,  -- UNIQUE制約を追加
    
    -- 自動生成の基本設定
    enabled INTEGER DEFAULT 0,
    frequency TEXT DEFAULT 'daily',
    generation_time TEXT,
    posts_per_day INTEGER DEFAULT 10,
    
    -- 実行履歴
    last_generated_at DATETIME,
    total_generated INTEGER DEFAULT 0,
    
    -- メタデータ
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- 外部キー制約
    FOREIGN KEY (cast_id) REFERENCES casts(id) ON DELETE CASCADE
);

-- バックアップからデータを復元（重複を除外）
INSERT INTO auto_generation_settings (cast_id, enabled, frequency, generation_time, posts_per_day, last_generated_at, total_generated, created_at, updated_at)
SELECT cast_id, enabled, frequency, generation_time, posts_per_day, last_generated_at, total_generated, created_at, updated_at
FROM auto_generation_settings_backup
GROUP BY cast_id;  -- 重複を除外

-- バックアップテーブルを削除
DROP TABLE auto_generation_settings_backup;

-- インデックス再作成
CREATE INDEX IF NOT EXISTS idx_auto_gen_cast_id ON auto_generation_settings(cast_id);
CREATE INDEX IF NOT EXISTS idx_auto_gen_enabled ON auto_generation_settings(enabled);
CREATE INDEX IF NOT EXISTS idx_auto_gen_time ON auto_generation_settings(generation_time);
