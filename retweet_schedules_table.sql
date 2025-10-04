-- リツイート予約専用テーブル作成SQL
-- 既存のpostsテーブルには一切変更を加えません

CREATE TABLE retweet_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cast_id INTEGER NOT NULL,
    tweet_id TEXT NOT NULL,
    comment TEXT,  -- 空の場合は通常リツイート、ありの場合は引用ツイート
    scheduled_at TEXT NOT NULL,  -- JST時刻 'YYYY-MM-DD HH:MM:SS'
    status TEXT DEFAULT 'scheduled',  -- 'scheduled', 'completed', 'failed'
    created_at TEXT NOT NULL,
    executed_at TEXT,
    result_tweet_id TEXT,  -- 実行後の結果ツイートID（引用ツイートの場合）
    error_message TEXT,
    FOREIGN KEY(cast_id) REFERENCES casts(id) ON DELETE CASCADE
);

-- インデックス作成（パフォーマンス向上）
CREATE INDEX idx_retweet_schedules_scheduled_at ON retweet_schedules(scheduled_at);
CREATE INDEX idx_retweet_schedules_status ON retweet_schedules(status);
CREATE INDEX idx_retweet_schedules_cast_id ON retweet_schedules(cast_id);