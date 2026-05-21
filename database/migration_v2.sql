-- ============================================================
-- QuizChatbot v2 Migration
-- Run: docker-compose exec mysql mysql -uroot -proot quizchatbot < database/migration_v2.sql
-- ============================================================
USE quizchatbot;

-- ─── Knowledge Files Metadata ────────────────────────────────
CREATE TABLE IF NOT EXISTS knowledge_files (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    filename            VARCHAR(255) NOT NULL UNIQUE,
    domain_name         VARCHAR(100) NOT NULL DEFAULT 'general',
    topics_json         JSON         NULL,
    keywords_json       JSON         NULL,
    ai_language_rules   TEXT         NULL,    -- per-file custom LLM instructions
    chunk_count         INT UNSIGNED NOT NULL DEFAULT 0,
    indexed_at          DATETIME     NULL,
    status              ENUM('indexed','pending','error') NOT NULL DEFAULT 'pending',
    created_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ─── Global AI Settings ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS global_ai_settings (
    id                          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    global_special_instruction  TEXT         NOT NULL,
    is_active                   TINYINT(1)   NOT NULL DEFAULT 1,
    created_at                  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ─── Seed: default global instruction ────────────────────────
INSERT IGNORE INTO global_ai_settings (id, global_special_instruction) VALUES
(1, 'If a user asks a question unrelated to the current knowledge base, politely inform them you can only help with topics in the available knowledge base. Do not hallucinate or make up answers. Keep all responses conversational, natural, and concise. Never use religious phrases or emotional filler.');

-- ─── Add admin role to users (if not exists) ─────────────────
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS role ENUM('user','admin') NOT NULL DEFAULT 'user',
    ADD COLUMN IF NOT EXISTS phone VARCHAR(20) NULL,
    ADD COLUMN IF NOT EXISTS total_credits INT UNSIGNED NOT NULL DEFAULT 100;

-- Sync total_credits for existing users
UPDATE users SET total_credits = 100 WHERE total_credits = 0;

-- Make first user admin
UPDATE users SET role = 'admin' WHERE id = 1;
