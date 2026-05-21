-- ============================================================
-- Migration: Add Tamil/Hindi pre-translated columns to quiz_questions
-- Run: docker exec -i quizchatbot_mysql mysql -uquizuser -pquizpass quizchatbot < database/migration_add_translations.sql
-- ============================================================
-- CRITICAL: must be first statement — ensures Tamil/Hindi text is not double-encoded
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
USE quizchatbot;

-- ─── Add translation columns ─────────────────────────────────
-- MySQL 8.0 doesn't support IF NOT EXISTS for ADD COLUMN.
-- Using a procedure to safely add columns.

DROP PROCEDURE IF EXISTS add_translation_columns;
DELIMITER //
CREATE PROCEDURE add_translation_columns()
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='quizchatbot' AND TABLE_NAME='quiz_questions' AND COLUMN_NAME='question_ta') THEN
        ALTER TABLE quiz_questions ADD COLUMN question_ta TEXT NULL AFTER question;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='quizchatbot' AND TABLE_NAME='quiz_questions' AND COLUMN_NAME='question_hi') THEN
        ALTER TABLE quiz_questions ADD COLUMN question_hi TEXT NULL AFTER question_ta;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='quizchatbot' AND TABLE_NAME='quiz_questions' AND COLUMN_NAME='options_ta') THEN
        ALTER TABLE quiz_questions ADD COLUMN options_ta JSON NULL AFTER options;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='quizchatbot' AND TABLE_NAME='quiz_questions' AND COLUMN_NAME='options_hi') THEN
        ALTER TABLE quiz_questions ADD COLUMN options_hi JSON NULL AFTER options_ta;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='quizchatbot' AND TABLE_NAME='quiz_questions' AND COLUMN_NAME='answer_ta') THEN
        ALTER TABLE quiz_questions ADD COLUMN answer_ta TEXT NULL AFTER answer;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='quizchatbot' AND TABLE_NAME='quiz_questions' AND COLUMN_NAME='answer_hi') THEN
        ALTER TABLE quiz_questions ADD COLUMN answer_hi TEXT NULL AFTER answer_ta;
    END IF;
END //
DELIMITER ;
CALL add_translation_columns();
DROP PROCEDURE IF EXISTS add_translation_columns;

-- ─── Populate Open-Ended Questions ───────────────────────────

-- Q1: Who won the first IPL?
UPDATE quiz_questions SET
    question_ta = 'முதல் IPL-ஐ யார் win பண்ணாங்க?',
    question_hi = 'पहला IPL किसने win किया?',
    answer_ta   = 'Rajasthan Royals',
    answer_hi   = 'Rajasthan Royals'
WHERE question = 'Who won the first IPL?' AND type = 'open';

-- Q2: Who is called Captain Cool in IPL?
UPDATE quiz_questions SET
    question_ta = 'IPL-ல் யாரை Captain Cool-ன்னு சொல்வாங்க?',
    question_hi = 'IPL में किसे Captain Cool बोलते हैं?',
    answer_ta   = 'MS Dhoni',
    answer_hi   = 'MS Dhoni'
WHERE question = 'Who is called Captain Cool in IPL?' AND type = 'open';

-- Q3: Who scored 175* in IPL?
UPDATE quiz_questions SET
    question_ta = 'IPL-ல் 175* runs யார் அடிச்சாங்க — highest individual score?',
    question_hi = 'IPL में 175* runs किसने बनाए — highest individual score?',
    answer_ta   = 'Chris Gayle',
    answer_hi   = 'Chris Gayle'
WHERE question = 'Who scored 175* in IPL — the highest individual score?' AND type = 'open';

-- Q4: Which team has won the most IPL trophies?
UPDATE quiz_questions SET
    question_ta = 'எந்த team அதிகமா IPL trophies win பண்ணிருக்கு?',
    question_hi = 'किस team ने सबसे ज्यादा IPL trophies जीते हैं?',
    answer_ta   = 'Chennai Super Kings மற்றும் Mumbai Indians',
    answer_hi   = 'Chennai Super Kings और Mumbai Indians'
WHERE question = 'Which team has won the most IPL trophies?' AND type = 'open';

-- Q5: Who hit the fastest fifty in IPL history?
UPDATE quiz_questions SET
    question_ta = 'IPL history-ல் fastest fifty யார் அடிச்சாங்க?',
    question_hi = 'IPL history में fastest fifty किसने मारा?',
    answer_ta   = 'Yashasvi Jaiswal',
    answer_hi   = 'Yashasvi Jaiswal'
WHERE question = 'Who hit the fastest fifty in IPL history?' AND type = 'open';

-- Q6: Who has scored the most runs in IPL history?
UPDATE quiz_questions SET
    question_ta = 'IPL history-ல் அதிக runs யார் அடிச்சாங்க?',
    question_hi = 'IPL history में सबसे ज्यादा runs किसने बनाए?',
    answer_ta   = 'Virat Kohli',
    answer_hi   = 'Virat Kohli'
WHERE question = 'Who has scored the most runs in IPL history?' AND type = 'open';

-- Q7: Which stadium is the home ground of CSK?
UPDATE quiz_questions SET
    question_ta = 'CSK-ன் home ground எந்த stadium?',
    question_hi = 'CSK का home ground कौन सा stadium है?',
    answer_ta   = 'M. A. Chidambaram Stadium',
    answer_hi   = 'M. A. Chidambaram Stadium'
WHERE question = 'Which stadium is the home ground of CSK?' AND type = 'open';

-- Q8: Which bowler has the most wickets in IPL history?
UPDATE quiz_questions SET
    question_ta = 'IPL history-ல் அதிக wickets யார் எடுத்திருக்காங்க?',
    question_hi = 'IPL history में सबसे ज्यादा wickets किसने लिए?',
    answer_ta   = 'Yuzvendra Chahal',
    answer_hi   = 'Yuzvendra Chahal'
WHERE question = 'Which bowler has the most wickets in IPL history?' AND type = 'open';

-- Q9: Which year did Mumbai Indians win their 5th IPL title?
UPDATE quiz_questions SET
    question_ta = 'Mumbai Indians எந்த year-ல் 5th IPL title win பண்ணாங்க?',
    question_hi = 'Mumbai Indians ने किस year में अपना 5th IPL title जीता?',
    answer_ta   = '2020',
    answer_hi   = '2020'
WHERE question = 'Which year did Mumbai Indians win their 5th IPL title?' AND type = 'open';

-- Q10: Who was the Orange Cap winner in IPL 2023?
UPDATE quiz_questions SET
    question_ta = 'IPL 2023-ல் Orange Cap winner யாரு?',
    question_hi = 'IPL 2023 में Orange Cap winner कौन था?',
    answer_ta   = 'Shubman Gill',
    answer_hi   = 'Shubman Gill'
WHERE question = 'Who was the Orange Cap winner in IPL 2023?' AND type = 'open';

-- ─── Populate MCQ Questions ──────────────────────────────────

-- MCQ1: Who won IPL 2023?
UPDATE quiz_questions SET
    question_ta = 'IPL 2023 யார் win பண்ணாங்க?',
    question_hi = 'IPL 2023 किसने win किया?',
    options_ta  = '["Chennai Super Kings","Mumbai Indians","Gujarat Titans","Kolkata Knight Riders"]',
    options_hi  = '["Chennai Super Kings","Mumbai Indians","Gujarat Titans","Kolkata Knight Riders"]',
    answer_ta   = 'Chennai Super Kings',
    answer_hi   = 'Chennai Super Kings'
WHERE question = 'Who won IPL 2023?' AND type = 'mcq';

-- MCQ2: How many teams play in IPL?
UPDATE quiz_questions SET
    question_ta = 'IPL-ல் எத்தனை teams விளையாடுது?',
    question_hi = 'IPL में कितने teams खेलते हैं?',
    options_ta  = '["8","10","12","6"]',
    options_hi  = '["8","10","12","6"]',
    answer_ta   = '10',
    answer_hi   = '10'
WHERE question = 'How many teams play in IPL?' AND type = 'mcq';

-- MCQ3: Which player is known as the Universe Boss?
UPDATE quiz_questions SET
    question_ta = 'யாரை Universe Boss-ன்னு சொல்வாங்க?',
    question_hi = 'किस player को Universe Boss बोलते हैं?',
    options_ta  = '["Rohit Sharma","Virat Kohli","Chris Gayle","MS Dhoni"]',
    options_hi  = '["Rohit Sharma","Virat Kohli","Chris Gayle","MS Dhoni"]',
    answer_ta   = 'Chris Gayle',
    answer_hi   = 'Chris Gayle'
WHERE question = 'Which player is known as the Universe Boss?' AND type = 'mcq';

-- MCQ4: Which team won IPL 2022?
UPDATE quiz_questions SET
    question_ta = 'IPL 2022-ஐ எந்த team win பண்ணுச்சு?',
    question_hi = 'IPL 2022 किस team ने जीता?',
    options_ta  = '["Rajasthan Royals","Gujarat Titans","Mumbai Indians","Lucknow Super Giants"]',
    options_hi  = '["Rajasthan Royals","Gujarat Titans","Mumbai Indians","Lucknow Super Giants"]',
    answer_ta   = 'Gujarat Titans',
    answer_hi   = 'Gujarat Titans'
WHERE question = 'Which team won IPL 2022?' AND type = 'mcq';

-- MCQ5: Who is the highest run-scorer in IPL?
UPDATE quiz_questions SET
    question_ta = 'IPL-ல் highest run-scorer யாரு?',
    question_hi = 'IPL में highest run-scorer कौन है?',
    options_ta  = '["Rohit Sharma","David Warner","Virat Kohli","Suresh Raina"]',
    options_hi  = '["Rohit Sharma","David Warner","Virat Kohli","Suresh Raina"]',
    answer_ta   = 'Virat Kohli',
    answer_hi   = 'Virat Kohli'
WHERE question = 'Who is the highest run-scorer in IPL?' AND type = 'mcq';
