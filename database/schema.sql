-- ============================================================
-- QuizChatbot Database Schema
-- ============================================================
-- CRITICAL: ensures Tamil/Hindi text is stored correctly (not double-encoded)
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS quizchatbot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE quizchatbot;

-- ─── Users ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    email         VARCHAR(120) NOT NULL UNIQUE,
    password      VARCHAR(255) NOT NULL,          -- bcrypt hash
    full_name     VARCHAR(100) NOT NULL,
    role          ENUM('user','admin') NOT NULL DEFAULT 'user',
    credits       INT UNSIGNED NOT NULL DEFAULT 100,
    total_credits INT UNSIGNED NOT NULL DEFAULT 100,
    language      ENUM('en','ta','hi') NOT NULL DEFAULT 'en',
    phone         VARCHAR(20)  NULL,
    is_active     TINYINT(1)   NOT NULL DEFAULT 1,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ─── Sessions ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id     INT UNSIGNED NOT NULL,
    token       VARCHAR(512) NOT NULL UNIQUE,
    expires_at  DATETIME     NOT NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ─── Chat History ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chat_history (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id     INT UNSIGNED NOT NULL,
    role        ENUM('user','assistant') NOT NULL,
    message     TEXT         NOT NULL,
    intent      VARCHAR(30)  NULL,              -- rag | sql | quiz
    source_file VARCHAR(255) NULL,
    language    VARCHAR(5)   NOT NULL DEFAULT 'en',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ─── Credit Transactions ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS credit_transactions (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id     INT UNSIGNED NOT NULL,
    delta       INT          NOT NULL,          -- negative = deduct
    reason      VARCHAR(100) NOT NULL,
    balance     INT UNSIGNED NOT NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ─── Quiz Topics ─────────────────────────────────────────────
-- knowledge_file_id links each topic to the .md file it was generated from.
-- ON DELETE CASCADE: deleting a knowledge file removes its topic automatically,
-- which then cascades to quiz_questions → quiz_answers.
CREATE TABLE IF NOT EXISTS quiz_topics (
    id                INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    knowledge_file_id INT UNSIGNED  NULL,               -- FK to knowledge_files
    name              VARCHAR(100)  NOT NULL,
    slug              VARCHAR(100)  NOT NULL UNIQUE,
    description       TEXT          NULL,
    is_active         TINYINT(1)    NOT NULL DEFAULT 1,
    created_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (knowledge_file_id)
        REFERENCES knowledge_files(id) ON DELETE CASCADE,
    INDEX idx_knowledge_file_id (knowledge_file_id)
) ENGINE=InnoDB;

-- ─── Quiz Questions ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quiz_questions (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    topic_id    INT UNSIGNED NOT NULL,
    question    TEXT         NOT NULL,
    type        ENUM('mcq','open') NOT NULL DEFAULT 'mcq',
    options     JSON         NULL,              -- for MCQ
    answer      TEXT         NOT NULL,
    difficulty  ENUM('easy','medium','hard') NOT NULL DEFAULT 'medium',
    is_active   TINYINT(1)   NOT NULL DEFAULT 1,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES quiz_topics(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ─── Quiz Sessions ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quiz_sessions (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id         INT UNSIGNED NOT NULL,
    topic_id        INT UNSIGNED     NULL,
    score           INT UNSIGNED NOT NULL DEFAULT 0,
    total_questions INT UNSIGNED NOT NULL DEFAULT 0,
    marks_per_q     INT UNSIGNED NOT NULL DEFAULT 1,
    pass_mark_pct   INT UNSIGNED NOT NULL DEFAULT 60,
    completed       TINYINT(1)   NOT NULL DEFAULT 0,
    ai_feedback     TEXT         NULL,
    started_at      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at        DATETIME     NULL,
    FOREIGN KEY (user_id)  REFERENCES users(id)        ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES quiz_topics(id)  ON DELETE CASCADE
) ENGINE=InnoDB;

-- ─── Quiz Config (global) ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS quiz_config (
    id                      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    num_questions           INT UNSIGNED NOT NULL DEFAULT 10,
    marks_per_q             INT UNSIGNED NOT NULL DEFAULT 1,
    pass_mark_pct           INT UNSIGNED NOT NULL DEFAULT 60,
    question_type           ENUM('mcq','open','both') NOT NULL DEFAULT 'both',
    intro_text              TEXT NULL,
    fuzzy_accept_threshold  INT UNSIGNED NOT NULL DEFAULT 85,   -- score >= this → CORRECT without LLM
    fuzzy_reject_threshold  INT UNSIGNED NOT NULL DEFAULT 55,   -- score <  this → WRONG  without LLM
    updated_at              DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ─── Quiz Answers ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quiz_answers (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    quiz_session_id INT UNSIGNED NOT NULL,
    question_id     INT UNSIGNED NOT NULL,
    user_answer     TEXT         NOT NULL,
    is_correct      TINYINT(1)   NOT NULL DEFAULT 0,
    answered_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (quiz_session_id) REFERENCES quiz_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id)     REFERENCES quiz_questions(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- ─── Knowledge Files Metadata ────────────────────────────────
CREATE TABLE IF NOT EXISTS knowledge_files (
    id                INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    filename          VARCHAR(255) NOT NULL UNIQUE,
    domain_name       VARCHAR(100) NOT NULL DEFAULT 'general',
    topics_json       JSON         NULL,
    keywords_json     JSON         NULL,
    ai_language_rules TEXT         NULL,
    chunk_count       INT UNSIGNED NOT NULL DEFAULT 0,
    indexed_at        DATETIME     NULL,
    status            ENUM('indexed','pending','error') NOT NULL DEFAULT 'pending',
    created_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ─── Global AI Settings ──────────────────────────────────────
CREATE TABLE IF NOT EXISTS global_ai_settings (
    id                         INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    global_special_instruction TEXT         NOT NULL,
    show_prompt_debug          TINYINT(1)   NOT NULL DEFAULT 0,
    is_active                  TINYINT(1)   NOT NULL DEFAULT 1,
    created_at                 DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                 DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ─── Answer Aliases ──────────────────────────────────────────
-- Links canonical answers to their common aliases per knowledge file.
-- Aliases are deleted automatically (ON DELETE CASCADE) when the
-- knowledge file is removed from admin — zero manual cleanup.
CREATE TABLE IF NOT EXISTS answer_aliases (
    id                INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    knowledge_file_id INT UNSIGNED  NOT NULL,
    canonical         VARCHAR(500)  NOT NULL COLLATE utf8mb4_unicode_ci,  -- e.g. "Chennai Super Kings"
    alias             VARCHAR(500)  NOT NULL COLLATE utf8mb4_unicode_ci,  -- e.g. "CSK"
    created_at        DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (knowledge_file_id)
        REFERENCES knowledge_files(id) ON DELETE CASCADE,
    INDEX idx_canonical (canonical(100))
) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
