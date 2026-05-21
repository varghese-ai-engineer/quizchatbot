-- ============================================================
-- Migration 001: Answer Aliases + Fuzzy Thresholds
-- Safe to run on existing databases (IF NOT EXISTS / IF NOT COLUMN)
-- ============================================================
USE quizchatbot;

-- ─── answer_aliases table ────────────────────────────────────
CREATE TABLE IF NOT EXISTS answer_aliases (
    id                INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    knowledge_file_id INT UNSIGNED NOT NULL,
    canonical         VARCHAR(500) NOT NULL COLLATE utf8mb4_unicode_ci,
    alias             VARCHAR(500) NOT NULL COLLATE utf8mb4_unicode_ci,
    created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (knowledge_file_id)
        REFERENCES knowledge_files(id) ON DELETE CASCADE,
    INDEX idx_canonical (canonical(100))
) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- ─── quiz_config threshold columns ──────────────────────────
-- Add only if they don't already exist (safe re-run)
SET @db = DATABASE();

SET @col_accept = (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = @db
      AND TABLE_NAME   = 'quiz_config'
      AND COLUMN_NAME  = 'fuzzy_accept_threshold'
);
SET @col_reject = (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = @db
      AND TABLE_NAME   = 'quiz_config'
      AND COLUMN_NAME  = 'fuzzy_reject_threshold'
);

-- Only ALTER if columns are missing
SET @sql_accept = IF(@col_accept = 0,
    'ALTER TABLE quiz_config ADD COLUMN fuzzy_accept_threshold INT UNSIGNED NOT NULL DEFAULT 85',
    'SELECT 1'
);
SET @sql_reject = IF(@col_reject = 0,
    'ALTER TABLE quiz_config ADD COLUMN fuzzy_reject_threshold INT UNSIGNED NOT NULL DEFAULT 55',
    'SELECT 1'
);

PREPARE stmt FROM @sql_accept; EXECUTE stmt; DEALLOCATE PREPARE stmt;
PREPARE stmt FROM @sql_reject; EXECUTE stmt; DEALLOCATE PREPARE stmt;
