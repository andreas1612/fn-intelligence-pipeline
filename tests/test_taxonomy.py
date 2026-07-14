"""The taxonomy parser.

taxonomy-v1.0.md is the single source of truth for the controlled vocabulary
(D-016): the triage prompt, the client profile validator, and the Notion board
schema are all generated from it at runtime, so nothing holds a second copy.

That makes the parser load-bearing in a way that is easy to miss. If it silently
returned a partial tag set, triage would reject valid tags, client seeding would
reject valid profiles, and the Notion board would be built with options missing.
The count assertion inside load_taxonomy is the guard; these tests prove it works.
"""

import pytest

from src import triage

TEXT = triage.TAXONOMY_PATH.read_text(encoding="utf-8")


def test_the_parser_finds_every_tag_the_document_declares():
    taxonomy = triage.load_taxonomy(TEXT)
    # The counts the document states in its own section totals.
    assert len(taxonomy.themes) == 15
    assert len(taxonomy.sectors) == 5
    assert len(taxonomy.jurisdictions) == 3
    assert len(taxonomy.types) == 7


def test_tags_are_parsed_into_the_right_group():
    taxonomy = triage.load_taxonomy(TEXT)
    assert "DORA" in taxonomy.themes
    assert "Investment firms" in taxonomy.sectors
    assert "Cyprus" in taxonomy.jurisdictions
    assert "Threat advisory" in taxonomy.types

    # Groups do not bleed into each other. "Insurance" is a sector, never a theme.
    assert "Insurance" not in taxonomy.themes
    assert "DORA" not in taxonomy.sectors


def test_the_escape_valve_is_a_real_tag():
    # Taxonomy section 3.5: Other exists so the model never invents a tag when
    # nothing fits. If the parser dropped it, uncertainty would have nowhere to go.
    assert "Other" in triage.load_taxonomy(TEXT).themes


def test_a_tag_added_without_updating_the_count_fails_loudly():
    # This is the real protection: a tag edited into the document without
    # updating its section total is a half-finished change. Fail, do not guess.
    tampered = TEXT.replace(
        "- **Insurance**",
        "- **Insurance**\n- **Pension funds**",
    )
    with pytest.raises(ValueError, match="taxonomy parse mismatch"):
        triage.load_taxonomy(tampered)


def test_a_renamed_section_heading_fails_loudly():
    # The parser locates tags by section heading. A renamed heading must not
    # silently yield an empty group.
    tampered = TEXT.replace("## 4. Sector tags", "## 4. Sectors")
    with pytest.raises((ValueError, Exception)):
        triage.load_taxonomy(tampered)
