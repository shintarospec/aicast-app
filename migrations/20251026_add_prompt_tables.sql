-- Migration: add new prompt-related tables (account_mission, persona_detailed, sample_profiles, sample_posts)
-- Generated: 2025-10-26

PRAGMA foreign_keys = OFF;
BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS account_mission (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cast_id INTEGER UNIQUE,
  mission TEXT,
  persona_design TEXT,
  content_strategy TEXT,
  final_goal TEXT,
  additional_notes TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS persona_detailed (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cast_id INTEGER UNIQUE,
  archetype TEXT,
  occupation TEXT,
  residence TEXT,
  family_structure TEXT,
  symbolic_quote TEXT,
  x_usage_purpose TEXT,
  behavior_pattern TEXT,
  interested_topics TEXT,
  platform_pain_points TEXT,
  brand_relationship TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS sample_profiles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cast_id INTEGER UNIQUE,
  profile_text TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT
);

CREATE TABLE IF NOT EXISTS sample_posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cast_id INTEGER,
  category TEXT,
  post_content TEXT,
  sort_order INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
PRAGMA foreign_keys = ON;
