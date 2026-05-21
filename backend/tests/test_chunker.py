"""
Regression Tests — MarkdownChunker (RAG Chunking Strategy v3)
Tests the heading-aware, paragraph-splitting, overlap-chunking logic.
Run: pytest backend/tests/test_chunker.py -v
"""
import sys
import os
import importlib
import types
import pytest

# ── Import MarkdownChunker without triggering httpx/chromadb/pymysql ─────────
# We stub out the heavy third-party modules so the pure-Python chunker class
# can be loaded and tested without a running Docker stack.
_stub_names = ["httpx", "chromadb", "pymysql"]
for _name in _stub_names:
    if _name not in sys.modules:
        sys.modules[_name] = types.ModuleType(_name)

# Provide a minimal pymysql stub so the import doesn't fail
_pymysql_stub = sys.modules.get("pymysql", types.ModuleType("pymysql"))
_pymysql_stub.cursors = types.SimpleNamespace(DictCursor=object)  # type: ignore
_pymysql_stub.connect = lambda **kw: None  # type: ignore
sys.modules["pymysql"] = _pymysql_stub

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.ingest_knowledge_base import MarkdownChunker, Chunk  # noqa: E402



# ── Fixtures ──────────────────────────────────────────────────

SIMPLE_TWO_SECTION = """\
# IPL Records

## Batting Records
Virat Kohli is the highest run scorer.
Chris Gayle holds the highest individual score: 175*.

## Bowling Records
Yuzvendra Chahal is the highest wicket taker.
Alzarri Joseph took 6/12 on debut.
"""

SINGLE_SECTION_SHORT = """\
# IPL Overview
The Indian Premier League (IPL) started in 2008.
It is a T20 cricket league in India.
"""

MULTI_LEVEL_HEADINGS = """\
# IPL Records

## Batting Records

### Most Sixes
Chris Gayle has hit the most sixes in IPL history with 358+ sixes.
He hit 17 sixes in a single innings of 175*.

### Most Runs
Virat Kohli has scored the most runs in IPL history with 8000+ runs.

## Bowling Records
Yuzvendra Chahal holds the most wickets in IPL history.
"""

LONG_SECTION = """\
# Long Document

## Very Long Section
""" + ("This is a long line of content. " * 20)  # ~640 chars

NO_HEADING_DOCUMENT = """\
The Indian Premier League started in 2008.
It is a T20 cricket league founded by BCCI.
Teams play 20 overs each.
"""

PREAMBLE_PLUS_SECTIONS = """\
This document covers IPL records.

## Batting Records
Chris Gayle scored 175* in IPL.
Most runs: Virat Kohli.
"""


# ── Test: basic section splitting ─────────────────────────────

class TestSectionSplitting:

    def test_two_sections_produce_at_least_two_chunks(self):
        chunker = MarkdownChunker()
        chunks = chunker.chunk(SIMPLE_TWO_SECTION, "records.md")
        # Should have at least one chunk per ## section
        assert len(chunks) >= 2

    def test_chunk_sections_are_distinct(self):
        chunker = MarkdownChunker()
        chunks = chunker.chunk(SIMPLE_TWO_SECTION, "records.md")
        sections = [c.section for c in chunks]
        # Both sections should appear
        assert "Batting Records" in sections
        assert "Bowling Records" in sections

    def test_chunks_do_not_mix_section_content(self):
        """Batting chunk should not contain bowling content and vice versa."""
        chunker = MarkdownChunker()
        chunks = chunker.chunk(SIMPLE_TWO_SECTION, "records.md")
        batting_chunks = [c for c in chunks if c.section == "Batting Records"]
        bowling_chunks = [c for c in chunks if c.section == "Bowling Records"]
        assert batting_chunks, "Should have at least one batting chunk"
        assert bowling_chunks, "Should have at least one bowling chunk"
        for bc in batting_chunks:
            assert "Chahal" not in bc.raw_text, "Batting chunk must not contain bowling content"
        for wc in bowling_chunks:
            assert "175*" not in wc.raw_text, "Bowling chunk must not contain batting content"


# ── Test: heading breadcrumb ──────────────────────────────────

class TestBreadcrumb:

    def test_breadcrumb_included_in_chunk_text(self):
        chunker = MarkdownChunker()
        chunks = chunker.chunk(SIMPLE_TWO_SECTION, "records.md")
        for chunk in chunks:
            # Each chunk's full text should contain its section as a breadcrumb prefix
            assert "[" in chunk.text, "Breadcrumb must be present in chunk.text"

    def test_breadcrumb_contains_section_name(self):
        chunker = MarkdownChunker()
        chunks = chunker.chunk(SIMPLE_TWO_SECTION, "records.md")
        batting_chunks = [c for c in chunks if c.section == "Batting Records"]
        assert batting_chunks
        assert "Batting Records" in batting_chunks[0].text

    def test_multi_level_breadcrumb_chains_headings(self):
        """H3 under H2 should produce a breadcrumb like "IPL Records > Batting Records > Most Sixes"."""
        chunker = MarkdownChunker()
        chunks = chunker.chunk(MULTI_LEVEL_HEADINGS, "records.md")
        sixes_chunks = [c for c in chunks if "Most Sixes" in c.section]
        assert sixes_chunks, "Should have a chunk for the ### Most Sixes subsection"
        assert "Batting Records" in sixes_chunks[0].heading, \
            "Breadcrumb should include parent heading"
        assert "Most Sixes" in sixes_chunks[0].heading


# ── Test: chunk bounds ────────────────────────────────────────

class TestChunkBounds:

    def test_no_chunk_exceeds_max_chars_significantly(self):
        """Chunks should not exceed max_chars by more than one overlap amount."""
        chunker = MarkdownChunker(max_chars=400, overlap=75)
        chunks = chunker.chunk(LONG_SECTION, "test.md")
        for chunk in chunks:
            # Allow some leeway for the breadcrumb prefix
            assert len(chunk.text) <= 600, f"Chunk too long: {len(chunk.text)} chars"

    def test_no_chunk_below_min_len(self):
        """All returned chunks should meet the minimum length requirement."""
        chunker = MarkdownChunker(min_len=40)
        chunks = chunker.chunk(SIMPLE_TWO_SECTION, "records.md")
        for chunk in chunks:
            assert len(chunk.raw_text) >= 40, \
                f"Chunk below min_len: {repr(chunk.raw_text)}"

    def test_long_section_split_into_multiple_chunks(self):
        """A section with 640+ chars must be split into >=2 chunks."""
        chunker = MarkdownChunker(max_chars=400, overlap=75)
        chunks = chunker.chunk(LONG_SECTION, "test.md")
        long_section_chunks = [c for c in chunks if c.section == "Very Long Section"]
        assert len(long_section_chunks) >= 2, \
            "Long section should produce multiple chunks"

    def test_short_document_produces_minimal_chunks(self):
        """A small single-section doc should produce exactly 1 chunk."""
        chunker = MarkdownChunker(max_chars=400)
        chunks = chunker.chunk(SINGLE_SECTION_SHORT, "overview.md")
        assert len(chunks) == 1

    def test_chunk_indices_are_sequential(self):
        """chunk_index should be 0, 1, 2, ... across all chunks."""
        chunker = MarkdownChunker()
        chunks = chunker.chunk(MULTI_LEVEL_HEADINGS, "records.md")
        for expected_idx, chunk in enumerate(chunks):
            assert chunk.chunk_index == expected_idx, \
                f"Expected chunk_index={expected_idx}, got {chunk.chunk_index}"


# ── Test: no-heading documents ────────────────────────────────

class TestNoHeadingDocument:

    def test_no_heading_document_produces_at_least_one_chunk(self):
        chunker = MarkdownChunker()
        chunks = chunker.chunk(NO_HEADING_DOCUMENT, "plain.md")
        assert len(chunks) >= 1

    def test_no_heading_chunk_has_empty_section(self):
        chunker = MarkdownChunker()
        chunks = chunker.chunk(NO_HEADING_DOCUMENT, "plain.md")
        assert all(c.section == "" for c in chunks)


# ── Test: preamble ────────────────────────────────────────────

class TestPreamble:

    def test_preamble_before_first_heading_is_captured(self):
        """Content before the first heading should still be included."""
        chunker = MarkdownChunker(min_len=10)
        chunks = chunker.chunk(PREAMBLE_PLUS_SECTIONS, "test.md")
        all_text = " ".join(c.raw_text for c in chunks)
        assert "IPL records" in all_text, "Preamble content should be indexed"


# ── Test: metadata fields ─────────────────────────────────────

class TestChunkMetadata:

    def test_chunk_has_required_fields(self):
        chunker = MarkdownChunker()
        chunks = chunker.chunk(SIMPLE_TWO_SECTION, "records.md")
        for chunk in chunks:
            assert isinstance(chunk.text, str)
            assert isinstance(chunk.raw_text, str)
            assert isinstance(chunk.section, str)
            assert isinstance(chunk.heading, str)
            assert isinstance(chunk.chunk_index, int)

    def test_raw_text_is_subset_of_text(self):
        """chunk.text should contain chunk.raw_text."""
        chunker = MarkdownChunker()
        chunks = chunker.chunk(SIMPLE_TWO_SECTION, "records.md")
        for chunk in chunks:
            assert chunk.raw_text in chunk.text, \
                "raw_text should appear verbatim inside full chunk text"


# ── Test: six-hitting query scenario ─────────────────────────

class TestSixHittingScenario:
    """
    Verifies that after the knowledge base is enriched, the relevant section
    content (Chris Gayle / sixes) will appear as its own chunk and NOT be
    mixed with unrelated team-roster content.
    """

    SIX_HITTING_SECTION = """\
# IPL Records

## Six-Hitting Records
Most sixes in IPL history: Chris Gayle has hit the most sixes in IPL history with 358+ sixes.
Second most sixes: AB de Villiers is among the top six-hitters in IPL history.
Most sixes in a single innings: Chris Gayle hit 17 sixes in his 175* knock against PWI in 2013.
Chris Gayle is known as the Universe Boss for his explosive six-hitting ability in IPL.

## Batting Records
Most runs in IPL history: Virat Kohli with 8000+ runs.
Highest individual score: Chris Gayle scored 175* for RCB.
"""

    TEAM_SECTION = """\
# IPL Teams

## Chennai Super Kings
Chennai Super Kings (CSK) is captained by MS Dhoni, known as Captain Cool.
CSK has won the IPL title 5 times: 2010, 2011, 2018, 2021, 2023.
Home ground: M. A. Chidambaram Stadium, Chennai.

## Mumbai Indians
Mumbai Indians (MI) is captained by Rohit Sharma, a five-time IPL winner.
MI has won the IPL title 5 times: 2013, 2015, 2017, 2019, 2020.
Home ground: Wankhede Stadium, Mumbai.
"""


    def test_sixes_section_is_isolated_chunk(self):
        """The Six-Hitting Records section should produce its own dedicated chunk."""
        chunker = MarkdownChunker()
        chunks = chunker.chunk(self.SIX_HITTING_SECTION, "records.md")
        sixes_chunks = [c for c in chunks if c.section == "Six-Hitting Records"]
        assert sixes_chunks, "Must have a dedicated Six-Hitting Records chunk"

    def test_sixes_chunk_contains_gayle(self):
        """The sixes chunk must mention Chris Gayle explicitly."""
        chunker = MarkdownChunker()
        chunks = chunker.chunk(self.SIX_HITTING_SECTION, "records.md")
        sixes_chunks = [c for c in chunks if c.section == "Six-Hitting Records"]
        assert any("Chris Gayle" in c.raw_text for c in sixes_chunks)

    def test_sixes_chunk_does_not_contain_team_roster(self):
        """The sixes chunk must not contain team roster data (e.g. CSK, MI captain info)."""
        chunker = MarkdownChunker()
        chunks = chunker.chunk(self.SIX_HITTING_SECTION, "records.md")
        sixes_chunks = [c for c in chunks if c.section == "Six-Hitting Records"]
        for chunk in sixes_chunks:
            assert "MS Dhoni" not in chunk.raw_text, \
                "Sixes chunk must not contain team captain data"

    def test_team_section_stays_in_its_own_chunks(self):
        """Team data must not bleed into records chunks."""
        chunker = MarkdownChunker()
        record_chunks = chunker.chunk(self.SIX_HITTING_SECTION, "records.md")
        team_chunks   = chunker.chunk(self.TEAM_SECTION, "teams.md")

        record_text = " ".join(c.raw_text for c in record_chunks)
        team_text   = " ".join(c.raw_text for c in team_chunks)

        # Records should talk about sixes; teams should talk about captains
        assert "358" in record_text
        assert "MS Dhoni" in team_text
        # Cross-contamination check
        assert "358" not in team_text
        assert "Universe Boss" not in team_text
