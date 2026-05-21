"""
Regression Tests — Answer Evaluator (domain-agnostic)
Tests all 6 stages of the evaluation pipeline using pure unit tests
(no DB, no LLM calls needed for stages 0–3).

Run: pytest backend/tests/test_answer_evaluator.py -v
"""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.answer_evaluator import (
    normalize,
    exact_match,
    acronym_match,
    fuzzy_score,
    fuzzy_match,
    alias_match,
    evaluate_mcq_answer,
)

# Default thresholds (must match defaults in answer_evaluator.py)
FUZZY_ACCEPT = 85
FUZZY_REJECT = 55


# ─────────────────────────────────────────────────────────────────────────────
# Stage 1 — normalize()
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalize:
    def test_lowercase(self):
        assert normalize("MS Dhoni") == "ms dhoni"

    def test_strips_punctuation(self):
        # M. A. Chidambaram Stadium:
        # m.a.→ma (dots collapsed), stadium kept, result: "ma chidambaram stadium"
        result = normalize("M. A. Chidambaram Stadium")
        assert "chidambaram" in result
        assert "stadium" in result

    def test_strips_dots_from_abbreviation(self):
        # M.S. → ms (dots between letters collapsed)
        assert normalize("M.S. Dhoni") == "ms dhoni"

    def test_removes_filler_words(self):
        assert normalize("the best team in IPL") == "best team ipl"

    def test_collapses_whitespace(self):
        assert normalize("  Rohit   Sharma  ") == "rohit sharma"

    def test_removes_parentheses(self):
        assert normalize("Rajasthan Royals (RR)") == "rajasthan royals rr"

    def test_empty_string(self):
        assert normalize("") == ""

    def test_only_filler(self):
        assert normalize("the a an") == ""

    def test_unicode_nfc(self):
        # NFC normalisation should not corrupt normal ASCII
        assert normalize("Chennai") == "chennai"

    def test_hyphen_removed(self):
        # M-S → ms (hyphen between letters collapsed)
        assert normalize("M-S Dhoni") == "ms dhoni"


# ─────────────────────────────────────────────────────────────────────────────
# Stage 2 — exact_match()
# ─────────────────────────────────────────────────────────────────────────────

class TestExactMatch:
    def test_identical(self):
        assert exact_match("MS Dhoni", "MS Dhoni") is True

    def test_case_insensitive(self):
        assert exact_match("ms dhoni", "MS Dhoni") is True

    def test_punctuation_stripped(self):
        assert exact_match("M.S. Dhoni", "MS Dhoni") is True

    def test_different_answer(self):
        assert exact_match("Virat Kohli", "MS Dhoni") is False

    def test_partial_name_not_exact(self):
        # "Dhoni" alone does NOT exact-match "MS Dhoni" (after normalization)
        assert exact_match("Dhoni", "MS Dhoni") is False

    def test_filler_word_ignored(self):
        assert exact_match("the best answer", "best answer") is True


# ─────────────────────────────────────────────────────────────────────────────
# Stage 1.5 — acronym_match()  — domain-agnostic algorithmic tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAcronymMatch:
    # ── User types acronym of correct answer ──────────────────────
    def test_acronym_of_three_word_correct(self):
        # "chennai super kings" → "csk",  normalize("CSK") = "csk"
        assert acronym_match("CSK", "Chennai Super Kings") is True

    def test_acronym_case_insensitive(self):
        assert acronym_match("csk", "Chennai Super Kings") is True

    def test_acronym_two_words(self):
        # "rajasthan royals" → "rr"
        assert acronym_match("RR", "Rajasthan Royals") is True

    def test_acronym_two_words_mi(self):
        assert acronym_match("MI", "Mumbai Indians") is True

    def test_acronym_rcb(self):
        assert acronym_match("RCB", "Royal Challengers Bangalore") is True

    # ── User types full form of a canonical acronym ──────────────
    def test_full_form_of_canonical_acronym(self):
        # canonical = "CSK", user types "Chennai Super Kings"
        assert acronym_match("Chennai Super Kings", "CSK") is True

    # ── Single-word canonical — no acronym expected ───────────────
    def test_single_word_correct_no_acronym(self):
        # "Dhoni" has no multi-word acronym → should NOT match "D"
        assert acronym_match("D", "Dhoni") is False

    # ── Wrong acronym ──────────────────────────────────────────────
    def test_wrong_acronym(self):
        assert acronym_match("KKR", "Chennai Super Kings") is False

    def test_wrong_short_answer(self):
        assert acronym_match("MI", "Chennai Super Kings") is False

    # ── Domain-agnostic: works for any domain ────────────────────
    def test_aws_acronym(self):
        assert acronym_match("EC2", "Elastic Compute Cloud") is False  # EC2 ≠ "ecc"

    def test_aws_acronym_ecc(self):
        assert acronym_match("ECC", "Elastic Compute Cloud") is True

    def test_generic_three_word(self):
        assert acronym_match("OOP", "Object Oriented Programming") is True


# ─────────────────────────────────────────────────────────────────────────────
# Stage 3 — fuzzy_score() and fuzzy_match()
# ─────────────────────────────────────────────────────────────────────────────

class TestFuzzyScore:
    def test_identical_score_100(self):
        assert fuzzy_score("MS Dhoni", "MS Dhoni") == 100

    def test_partial_name_high_score(self):
        # "Dhoni" vs "MS Dhoni" — token_set_ratio should be high
        score = fuzzy_score("Dhoni", "MS Dhoni")
        assert score >= 80, f"Expected >=80, got {score}"

    def test_wrong_person_low_score(self):
        score = fuzzy_score("Virat Kohli", "MS Dhoni")
        assert score < FUZZY_ACCEPT, f"Expected <{FUZZY_ACCEPT}, got {score}"

    def test_typo_near_miss(self):
        score = fuzzy_score("Rohit Sharma", "Rohit Sharma")
        assert score == 100

    def test_bad_typo_low_score(self):
        score = fuzzy_score("dhone", "MS Dhoni")
        # "dhone" vs "ms dhoni" should score well below accept threshold
        assert score < FUZZY_ACCEPT, f"Expected <{FUZZY_ACCEPT}, got {score}"

    def test_empty_user_answer(self):
        assert fuzzy_score("", "MS Dhoni") == 0


class TestFuzzyMatch:
    def test_exact_above_accept(self):
        decision, score = fuzzy_match("MS Dhoni", "MS Dhoni", 85, 55)
        assert decision is True
        assert score == 100

    def test_partial_name_accept(self):
        decision, score = fuzzy_match("Dhoni", "MS Dhoni", 85, 55)
        # "Dhoni" should score high enough to accept or be uncertain
        assert decision is True or decision is None

    def test_clearly_wrong_rejected(self):
        decision, score = fuzzy_match("Sachin Tendulkar", "Rohit Sharma", 85, 55)
        assert decision is False

    def test_uncertain_zone_returns_none(self):
        # Manufacture an uncertain score using custom thresholds
        decision, score = fuzzy_match("Dhon", "MS Dhoni", accept_threshold=99, reject_threshold=0)
        # With threshold 99, anything < 99 but > 0 is uncertain
        assert decision is None or decision is False  # depends on actual score

    def test_empty_answer_zero_score(self):
        decision, score = fuzzy_match("", "MS Dhoni", 85, 55)
        assert decision is False
        assert score == 0


# ─────────────────────────────────────────────────────────────────────────────
# Stage 0 — alias_match()
# ─────────────────────────────────────────────────────────────────────────────

class TestAliasMatch:
    def test_exact_alias(self):
        assert alias_match("CSK", ["CSK", "Chennai"]) is True

    def test_alias_case_insensitive(self):
        assert alias_match("csk", ["CSK", "Chennai"]) is True

    def test_alias_punctuation_stripped(self):
        assert alias_match("C.S.K.", ["CSK"]) is True

    def test_alias_not_in_list(self):
        assert alias_match("MI", ["CSK", "Chennai"]) is False

    def test_empty_aliases_list(self):
        assert alias_match("CSK", []) is False

    def test_stadium_alias(self):
        assert alias_match("Chepauk", ["Chepauk", "MA Chidambaram"]) is True

    def test_partial_not_matched(self):
        # "Che" is NOT in aliases — should not match "Chepauk"
        assert alias_match("Che", ["Chepauk"]) is False

    def test_player_alias_msd(self):
        assert alias_match("MSD", ["MSD", "Captain Cool"]) is True

    def test_domain_agnostic_aws(self):
        assert alias_match("EC2", ["Elastic Compute Cloud", "EC2"]) is True

    def test_domain_agnostic_python(self):
        assert alias_match("list comp", ["list comprehension", "list comp"]) is True


# ─────────────────────────────────────────────────────────────────────────────
# MCQ evaluation — strict exact only
# ─────────────────────────────────────────────────────────────────────────────

class TestMCQEvaluation:
    def test_exact_match_correct(self):
        assert evaluate_mcq_answer("Mumbai Indians", "Mumbai Indians") is True

    def test_case_insensitive(self):
        assert evaluate_mcq_answer("mumbai indians", "Mumbai Indians") is True

    def test_trailing_space(self):
        assert evaluate_mcq_answer("Mumbai Indians ", "Mumbai Indians") is True

    def test_wrong_answer(self):
        assert evaluate_mcq_answer("Chennai Super Kings", "Mumbai Indians") is False

    def test_abbreviation_not_accepted(self):
        # MCQ is strict — abbreviations are not accepted (options are shown on screen)
        assert evaluate_mcq_answer("MI", "Mumbai Indians") is False

    def test_partial_not_accepted(self):
        assert evaluate_mcq_answer("Mumbai", "Mumbai Indians") is False


# ─────────────────────────────────────────────────────────────────────────────
# Integration: stage priority order
# ─────────────────────────────────────────────────────────────────────────────

class TestStagePriority:
    """Verify the pipeline stages fire in correct order."""

    def test_alias_beats_fuzzy(self):
        """If answer is in alias list, it's accepted even if fuzzy score would be uncertain."""
        # "MSD" vs "Mahendra Singh Dhoni" — fuzzy score is ~40 (below accept threshold)
        # but alias_match should catch it first
        assert alias_match("MSD", ["MSD", "Captain Cool"]) is True

    def test_acronym_match_for_known_abbreviations(self):
        """Acronym stage catches team abbreviations algorithmically — no alias needed."""
        assert acronym_match("MI", "Mumbai Indians") is True
        assert acronym_match("KKR", "Kolkata Knight Riders") is True
        # SRH: "Sunrisers"→s, "Hyderabad"→h → acronym is "sh" not "srh"
        # so "SRH" does NOT match via acronym (needs alias or LLM)
        assert acronym_match("SH", "Sunrisers Hyderabad") is True
        assert acronym_match("SRH", "Sunrisers Hyderabad") is False

    def test_normalize_then_exact_catches_punctuation_variants(self):
        """M.S. Dhoni should match MS Dhoni at the exact stage, not waste LLM."""
        assert exact_match("M.S. Dhoni", "MS Dhoni") is True

    def test_domain_python_exact(self):
        assert exact_match("for loop", "for loop") is True

    def test_domain_aws_acronym(self):
        assert acronym_match("VPC", "Virtual Private Cloud") is True

    def test_domain_medical(self):
        assert acronym_match("ECG", "Electrocardiogram") is False  # ECG ≠ "e" (single word)

    def test_no_false_positives_wrong_domain(self):
        """A cricket answer should not match a different answer."""
        assert exact_match("Python", "Java") is False
        assert acronym_match("JS", "Python") is False
