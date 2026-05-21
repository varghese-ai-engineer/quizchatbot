-- ============================================================
-- Migration 003: Link quiz_topics → knowledge_files
-- Adds knowledge_file_id FK with ON DELETE CASCADE so that
-- deleting a knowledge file automatically removes its quiz topic
-- which then cascades to quiz_questions → quiz_answers.
-- Safe to run on existing databases.
-- ============================================================
USE quizchatbot;

-- Step 1: Add column only if it doesn't already exist (via procedure)
SET @col_exists = (
    SELECT COUNT(*) FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = 'quizchatbot'
      AND TABLE_NAME   = 'quiz_topics'
      AND COLUMN_NAME  = 'knowledge_file_id'
);
SET @sql = IF(@col_exists = 0,
    'ALTER TABLE quiz_topics ADD COLUMN knowledge_file_id INT UNSIGNED NULL AFTER id',
    'SELECT 1 -- column already exists'
);
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Step 2: Back-fill existing rows by matching slug to filename stem
-- slug "ipl-cricket"   → looks for filename "ipl_cricket.md"
-- slug "ipl_knowledge" → looks for filename "ipl_knowledge_base.md" etc.
UPDATE quiz_topics qt
JOIN knowledge_files kf
  ON REPLACE(REPLACE(kf.filename, '.md', ''), '-', '_')
   = REPLACE(qt.slug, '-', '_')
SET qt.knowledge_file_id = kf.id
WHERE qt.knowledge_file_id IS NULL;

-- Step 3: Add index on new column (skip if exists)
SET @idx_exists = (
    SELECT COUNT(*) FROM information_schema.STATISTICS
    WHERE TABLE_SCHEMA = 'quizchatbot'
      AND TABLE_NAME   = 'quiz_topics'
      AND INDEX_NAME   = 'idx_knowledge_file_id'
);
SET @sql2 = IF(@idx_exists = 0,
    'ALTER TABLE quiz_topics ADD INDEX idx_knowledge_file_id (knowledge_file_id)',
    'SELECT 2 -- index already exists'
);
PREPARE stmt FROM @sql2; EXECUTE stmt; DEALLOCATE PREPARE stmt;

-- Step 4: Add FK constraint (skip if exists)
SET @fk_exists = (
    SELECT COUNT(*) FROM information_schema.REFERENTIAL_CONSTRAINTS
    WHERE CONSTRAINT_SCHEMA = 'quizchatbot'
      AND CONSTRAINT_NAME   = 'fk_quiz_topics_knowledge_file'
);
SET @sql3 = IF(@fk_exists = 0,
    'ALTER TABLE quiz_topics ADD CONSTRAINT fk_quiz_topics_knowledge_file FOREIGN KEY (knowledge_file_id) REFERENCES knowledge_files(id) ON DELETE CASCADE',
    'SELECT 3 -- FK already exists'
);
PREPARE stmt FROM @sql3; EXECUTE stmt; DEALLOCATE PREPARE stmt;
