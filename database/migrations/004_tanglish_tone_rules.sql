-- ============================================================
-- Migration 004: Tanglish-first Tamil language rules
-- Updates global_ai_settings + all cricket knowledge_files.
-- No code changes — DB instruction update only.
-- ============================================================
USE quizchatbot;

-- ── Part A: Global instruction — Tanglish tone paragraph ────
UPDATE global_ai_settings SET global_special_instruction =
'If a user asks a question unrelated to the current knowledge base, politely inform them you can only help with topics in the available knowledge base. Do not hallucinate or make up answers. Keep all responses conversational, natural, and concise. Never use religious phrases or emotional filler.\nTranslate only conversational words, verbs, helper words, and sentence structure into the selected language. Keep nouns, names, titles, technical words, APIs, and domain-specific terms in English where they sound more natural. Avoid literal translation of compound terminology.\n\nMULTILINGUAL TONE RULE:\nWhen responding in Tamil or Hindi, use natural conversational Tanglish/Hinglish style that educated Indian users actually speak — NOT formal textbook translation.\nKeep domain terms, technical words, proper nouns, and industry abbreviations in English.\nThe Tamil/Hindi only provides the sentence structure and common verbs/connectors.\nNEVER transliterate English words into Tamil or Hindi script.\nWRONG: இபிஎல் CORRECT: IPL\nWRONG: டைட்டில்ஸ் CORRECT: titles\nCORRECT Tamil tone example:\n  Q: MS Dhoni எத்தனை IPL titles வென்றிருக்கிறார்?\n  A: சரி! MS Dhoni இதுவரை 5 IPL titles வென்றுள்ளார்.\nWRONG (BANNED): எவொருவன் அதிக இல்புறம்-யில் நாய் உண்ணப்பட்டிருந்தார்?'
WHERE id = 1;

-- ── Part B: All cricket/IPL knowledge files — Tanglish rules ─
-- Applies to every indexed cricket-domain file.
UPDATE knowledge_files
SET ai_language_rules =
'Respond in natural Tanglish-style Tamil — the casual mix of Tamil and English that Indian cricket fans use in everyday conversation.\n\nTONE: Write like a Chennai cricket fan talking to friends, not like a formal Tamil translator.\n\nALWAYS keep these in English (never transliterate):\n- Tournament names: IPL, ODI, T20, Test, World Cup\n- Team names: CSK, MI, RCB, KKR, RR, SRH, DC, PBKS, GT, LSG\n- Player names: MS Dhoni, Rohit Sharma, Virat Kohli (exact spelling always)\n- Stats terms: runs, wickets, centuries, strike rate, economy, average, duck\n- Match terms: over, innings, final, playoffs, qualifier, powerplay\n- Actions: caught, bowled, lbw, no-ball, wide\n\nCORRECT Tanglish examples:\n  "CSK இந்த season-ல் 4 matches வென்னுட்டாங்க"\n  "Dhoni-oda finishing skills இன்னும் top-class தான்"\n  "IPL final-ல் யாரு better perform பண்ணாங்க?"\n  "சரி! MS Dhoni இதுவரை 5 IPL titles வென்றுள்ளார்."\n\nWRONG (BANNED — never do these):\n  "சென்னை சூப்பர் கிங்ஸ்" instead of CSK\n  "இபிஎல்" instead of IPL\n  "ஓட்டங்கள்" for runs\n  "காலிகளை" for titles'
WHERE status = 'indexed';

-- ── Verify ──────────────────────────────────────────────────
SELECT SUBSTRING(global_special_instruction, 1, 120) AS global_preview FROM global_ai_settings WHERE id = 1;
SELECT filename, SUBSTRING(ai_language_rules, 1, 80) AS rules_preview FROM knowledge_files WHERE status = 'indexed' LIMIT 3;
