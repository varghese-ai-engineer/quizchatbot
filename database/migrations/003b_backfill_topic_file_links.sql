-- ============================================================
-- Migration 003b: Back-fill knowledge_file_id for existing topics
-- Manual mapping for topics whose slug doesn't auto-match filename
-- ============================================================
USE quizchatbot;

-- "IPL Cricket" topic → most questions came from ipl_knowledge_base.md (id=3)
UPDATE quiz_topics SET knowledge_file_id = 3
WHERE slug = 'ipl-cricket' AND knowledge_file_id IS NULL;

-- Stale topics from old/deleted knowledge bases (python, ML, data structures)
-- No matching knowledge file exists → mark them inactive so they don't show in quiz
-- They will be cleaned up when the file-linked delete system is fully in use.
UPDATE quiz_topics SET is_active = 0
WHERE knowledge_file_id IS NULL AND slug IN ('python-basics', 'data-structures', 'machine-learning');

-- Confirm state
SELECT id, name, slug, knowledge_file_id, is_active FROM quiz_topics;
