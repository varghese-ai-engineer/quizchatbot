-- ============================================================
-- Migration 005: Add leniency_score to quiz_config
-- Single slider (0=strict, 100=easy) that drives fuzzy thresholds.
-- Default 50 preserves current behavior (accept=85, reject=55).
-- ============================================================
USE quizchatbot;

ALTER TABLE quiz_config
    ADD COLUMN leniency_score TINYINT UNSIGNED NOT NULL DEFAULT 50
    COMMENT '0=strict (accept>=100), 50=balanced (accept>=85,reject<55), 100=easy (accept>=55)';

UPDATE quiz_config SET leniency_score = 50 WHERE id = 1;

SELECT id, leniency_score FROM quiz_config;
