-- ============================================================
-- Seed Data  — auto-loaded on fresh Docker install
-- ============================================================
-- CRITICAL: ensures Tamil/Hindi text is stored correctly (not double-encoded)
SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
USE quizchatbot;


-- ─── Default Admin User ───────────────────────────────────────
-- email: varghesedott@gmail.com  |  password: varghese@123
INSERT IGNORE INTO users (username, email, password, full_name, role, credits, total_credits, is_active)
VALUES (
    'vargheset',
    'varghesedott@gmail.com',
    '$2y$10$RanU4CSqVowJ70BnJl7F2.caXd3FYlzV7uRqYqr7AWhWxc5UGIeai',
    'Varghese',
    'admin',
    1000,
    1000,
    1
);

-- ─── Default Regular User ────────────────────────────────────
-- email: user@quizchatbot.com  |  password: User@123
INSERT IGNORE INTO users (username, email, password, full_name, role, credits, total_credits, is_active)
VALUES (
    'testuser',
    'user@quizchatbot.com',
    '$2y$10$Qd86EpdqinRUgwBIyjft1O4yotYWcKIlX3EzpCGmlxszeumcfFSa6',
    'Test User',
    'user',
    100,
    100,
    1
);

-- ─── Global AI Instructions ──────────────────────────────────
INSERT IGNORE INTO global_ai_settings (id, global_special_instruction) VALUES (
    1,
    'If a user asks a question unrelated to the current knowledge base, politely inform them you can only help with topics in the available knowledge base. Do not hallucinate or make up answers. Keep all responses conversational, natural, and concise. Never use religious phrases or emotional filler.'
);

-- ─── Default Quiz Config ─────────────────────────────────────
INSERT IGNORE INTO quiz_config (id, num_questions, marks_per_q, pass_mark_pct, question_type, intro_text)
VALUES (1, 10, 1, 60, 'both', 'Welcome to the IPL Quiz! Test your cricket knowledge with our AI-powered quiz. Each question is evaluated by AI — so you can answer in your own words. Good luck! 🏏');

-- ─── Knowledge Base Files ─────────────────────────────────────
-- These are auto-indexed on startup via entrypoint.sh ingestion script.
-- INSERT IGNORE prevents duplicates on re-deploy.
SET @cricket_rules = 'Keep all player names in English exactly as written — do NOT transliterate.\nKeep all team names/abbreviations in English (CSK, MI, RCB, KKR etc.).\nCricket terms may be used in the selected UI language where natural.\nKeep numbers, dates, and statistics in their original form.';
SET @general_rules = 'Respond naturally in the selected UI language.\nKeep proper nouns and acronyms in their original form.';

INSERT IGNORE INTO knowledge_files (filename, domain_name, topics_json, keywords_json, ai_language_rules, chunk_count, status) VALUES
('captains.md',           'cricket', '["IPL Captains","MS Dhoni","Rohit Sharma","Virat Kohli","Gautam Gambhir","Hardik Pandya","David Warner"]',              '["ipl","Captains","Dhoni","Rohit","Sharma","Virat","Kohli","Gambhir","Pandya","Warner"]',                                                @cricket_rules, 1, 'indexed'),
('famous_matches.md',     'cricket', '["Famous IPL Matches","IPL 2019 Final","IPL 2023 Final","IPL 2016 Final","IPL 2020 Final"]',                             '["ipl","Famous","Matches","Final","Mumbai","Indians","Chennai","Super","Kings","Gujarat","Titans"]',                                      @cricket_rules, 1, 'indexed'),
('ipl_knowledge_base.md', 'cricket', '["IPL Knowledge Base","IPL Overview","IPL Teams","IPL Trophy Winners","Famous Captains","Orange Cap Winners","Purple Cap Winners","Important IPL Records","Famous IPL Players","IPL Basics"]', '["ipl","cricket","wicket","batting","odi","t20","century","run","over","Knowledge","Base","Overview"]', @cricket_rules, 6, 'indexed'),
('history.md',            'cricket', '["IPL History","IPL Winners"]',                                                                                         '["ipl","History","Rajasthan","Royals","Deccan","Chargers","Chennai","Mumbai","Indians","Sunrisers","Hyderabad","Gujarat","Titans"]',       @cricket_rules, 2, 'indexed'),
('orange_purple_caps.md', 'general', '["Orange Cap Winners","Purple Cap Winners"]',                                                                            '["Orange","Cap","Winners","Virat","Kohli","Chris","Gayle","David","Warner","Rahul","Shubman","Gill","Purple","Malinga","Bravo"]',          @general_rules, 1, 'indexed'),
('quiz_questions.md',     'cricket', '["IPL Quiz Questions"]',                                                                                                '["ipl","Quiz","Questions","Rajasthan","Royals","Captain","Cool","Dhoni","Chris","Gayle","Chennai","Mumbai","Jaiswal","Kohli"]',            @cricket_rules, 1, 'indexed'),
('records.md',            'cricket', '["IPL Records","Batting Records","Bowling Records","Team Records","Fastest Fifties"]',                                   '["ipl","wicket","batting","bowling","century","run","Records","Chris","Gayle","Virat","Kohli","Yuzvendra","Chahal","Jaiswal"]',            @cricket_rules, 1, 'indexed'),
('stadiums.md',           'cricket', '["IPL Stadiums","Wankhede Stadium","M. A. Chidambaram Stadium","Eden Gardens","Narendra Modi Stadium","M. Chinnaswamy Stadium"]', '["ipl","Stadiums","Wankhede","Mumbai","Chidambaram","Chennai","Eden","Gardens","Kolkata","Narendra","Modi","Ahmedabad","Chinnaswamy"]', @cricket_rules, 1, 'indexed'),
('teams.md',              'cricket', '["IPL Teams","Chennai Super Kings","Mumbai Indians","Royal Challengers Bengaluru","Kolkata Knight Riders","Rajasthan Royals","Sunrisers Hyderabad","Delhi Capitals","Punjab Kings","Lucknow Super Giants","Gujarat Titans"]', '["ipl","Teams","Chennai","Mumbai","Royal","Challengers","Kolkata","Knight","Riders","Rajasthan","Royals","Sunrisers","Delhi","Punjab","Lucknow","Gujarat"]', @cricket_rules, 1, 'indexed'),
('players.md',            'cricket', '["Famous IPL Players","MS Dhoni","Virat Kohli","Rohit Sharma","Chris Gayle","AB de Villiers","Jasprit Bumrah","Suresh Raina","Yuzvendra Chahal"]', '["ipl","wicket","batting","run","Dhoni","Virat","Kohli","Rohit","Sharma","Gayle","Villiers","Bumrah","Raina","Chahal"]', @cricket_rules, 1, 'indexed'),
('csk_records.md',        'cricket', '["Chennai Super Kings (CSK)","IPL Titles","Captains","Home Ground","Famous Players","Team Records","Suresh Raina IPL Records","MS Dhoni IPL Records"]', '["ipl","run","Chennai","Super","Kings","Titles","Dhoni","Jadeja","Chidambaram","Stadium","Raina","Bravo","Gaikwad"]', @cricket_rules, 2, 'indexed');

-- ─── Quiz Topics (IPL only) ───────────────────────────────────
INSERT IGNORE INTO quiz_topics (name, slug, description, is_active) VALUES
('IPL Cricket', 'ipl-cricket', 'Indian Premier League quiz questions', 1);

-- ─── IPL Cricket Questions (Open-Ended) ──────────────────────
-- topic_id=4 = IPL Cricket (inserted 4th above)
INSERT IGNORE INTO quiz_questions (topic_id, question, type, options, answer, difficulty) VALUES
(4, 'Who won the first IPL?', 'open', NULL, 'Rajasthan Royals', 'easy'),
(4, 'Who is called Captain Cool in IPL?', 'open', NULL, 'MS Dhoni', 'easy'),
(4, 'Who scored 175* in IPL — the highest individual score?', 'open', NULL, 'Chris Gayle', 'medium'),
(4, 'Which team has won the most IPL trophies?', 'open', NULL, 'Chennai Super Kings and Mumbai Indians', 'medium'),
(4, 'Who hit the fastest fifty in IPL history?', 'open', NULL, 'Yashasvi Jaiswal', 'hard'),
(4, 'Who has scored the most runs in IPL history?', 'open', NULL, 'Virat Kohli', 'medium'),
(4, 'Which stadium is the home ground of CSK?', 'open', NULL, 'M. A. Chidambaram Stadium', 'easy'),
(4, 'Which bowler has the most wickets in IPL history?', 'open', NULL, 'Yuzvendra Chahal', 'medium'),
(4, 'Which year did Mumbai Indians win their 5th IPL title?', 'open', NULL, '2020', 'hard'),
(4, 'Who was the Orange Cap winner in IPL 2023?', 'open', NULL, 'Shubman Gill', 'hard');

-- ─── IPL Cricket Questions (MCQ) ─────────────────────────────
INSERT IGNORE INTO quiz_questions (topic_id, question, type, options, answer, difficulty) VALUES
(4, 'Who won IPL 2023?', 'mcq',
 '["Chennai Super Kings","Mumbai Indians","Gujarat Titans","Kolkata Knight Riders"]',
 'Chennai Super Kings', 'easy'),
(4, 'How many teams play in IPL?', 'mcq',
 '["8","10","12","6"]',
 '10', 'easy'),
(4, 'Which player is known as the Universe Boss?', 'mcq',
 '["Rohit Sharma","Virat Kohli","Chris Gayle","MS Dhoni"]',
 'Chris Gayle', 'medium'),
(4, 'Which team won IPL 2022?', 'mcq',
 '["Rajasthan Royals","Gujarat Titans","Mumbai Indians","Lucknow Super Giants"]',
 'Gujarat Titans', 'medium'),
(4, 'Who is the highest run-scorer in IPL?', 'mcq',
 '["Rohit Sharma","David Warner","Virat Kohli","Suresh Raina"]',
 'Virat Kohli', 'easy');
