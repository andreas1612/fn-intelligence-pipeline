"""Triage output validation.

The validator is the only thing standing between model output and the system of
record. If it accepts a malformed result, an invented tag or an unjustified level
is written to the database and carried through review, matching, and distribution
as if a person had approved it.
"""

import pytest

from src import triage

TAXONOMY = triage.load_taxonomy(triage.TAXONOMY_PATH.read_text(encoding="utf-8"))

VALID = {
    "auto_discard": None,
    "theme_tags": ["DORA", "ICT incident reporting"],
    "sector_tags": ["Investment firms"],
    "jurisdiction": "EU",
    "type": "Consultation",
    "level": "High",
    "rules_applied": ["H-2", "W-1"],
    "summary": "ESMA opened a consultation on incident reporting.",
    "flagged": False,
    "flag_rules": [],
    "flag_reason": "",
    "confidence": "high",
}


def errors_for(**overrides):
    return triage.validate({**VALID, **overrides}, TAXONOMY)


def test_a_well_formed_result_passes():
    assert errors_for() == []


# --- Controlled vocabulary ------------------------------------------------


def test_an_invented_theme_tag_is_rejected():
    # Hard rule 3: tag only from the taxonomy. A plausible-sounding tag that is
    # not in the locked document is exactly the failure this must catch.
    assert errors_for(theme_tags=["Cyber resilience"])


def test_a_real_tag_from_the_wrong_group_is_rejected():
    # "Insurance" is a valid sector tag, but not a valid theme.
    assert errors_for(theme_tags=["Insurance"])


@pytest.mark.parametrize("themes", [[], ["DORA", "AI security", "Other", "AI regulation"]])
def test_theme_count_outside_one_to_three_is_rejected(themes):
    assert errors_for(theme_tags=themes)


def test_zero_sector_tags_is_allowed():
    # Taxonomy section 4: absence of a sector tag means cross-sector.
    assert errors_for(sector_tags=[]) == []


def test_jurisdiction_must_be_exactly_one_taxonomy_tag():
    assert errors_for(jurisdiction="Global")
    assert errors_for(jurisdiction=["EU"])


# --- Levels and rules -----------------------------------------------------


def test_an_invented_level_is_rejected():
    assert errors_for(level="Critical")


def test_a_level_must_be_justified_by_a_named_rule():
    # D-016: every level must be justified by named rules in rules_applied.
    assert errors_for(rules_applied=[])


def test_free_text_in_rules_applied_is_rejected():
    assert errors_for(rules_applied=["High because it affects many firms"])


def test_a_discarded_item_carries_no_level():
    assert errors_for(auto_discard="AD-2", level="High")
    assert errors_for(auto_discard="AD-2", level=None, rules_applied=["AD-2"]) == []


def test_a_kept_item_must_carry_a_level():
    assert errors_for(auto_discard=None, level=None)


def test_the_model_may_not_apply_ad_1():
    # AD-1 is deduplication, handled upstream by content hash. The model applying
    # it would mean an item is dropped for a reason the pipeline never checked.
    assert errors_for(auto_discard="AD-1")


# --- The D-021 defect 2 split: F rules belong in flag_rules ----------------


def test_a_flag_rule_in_rules_applied_is_rejected():
    # The old validator accepted F- in rules_applied, so prompt and validator
    # disagreed and 12 of 13 flagged items put F-2 in the wrong field.
    assert errors_for(rules_applied=["H-4", "F-2"])


def test_a_level_rule_in_flag_rules_is_rejected():
    assert errors_for(flagged=True, flag_rules=["H-4"], flag_reason="unclear")


def test_a_flagged_item_must_name_the_flag_rule():
    assert errors_for(flagged=True, flag_rules=[], flag_reason="unclear")


def test_an_unflagged_item_carries_no_flag_rules():
    assert errors_for(flagged=False, flag_rules=["F-2"])


def test_a_correctly_flagged_item_passes():
    assert errors_for(
        flagged=True,
        flag_rules=["F-2"],
        flag_reason="Client-base relevance is not evidenced in the supplied text.",
        rules_applied=["H-4"],
    ) == []


# --- Shape ----------------------------------------------------------------


def test_a_missing_summary_is_rejected():
    assert errors_for(summary="   ")


def test_a_non_object_response_is_rejected():
    assert triage.validate(["not", "an", "object"], TAXONOMY)


def test_confidence_must_come_from_the_fixed_set():
    assert errors_for(confidence="very high")


# --- JSON extraction ------------------------------------------------------


def test_a_fenced_response_is_still_parsed():
    # The prompt forbids markdown fences, but tolerating them is cheaper than
    # burning a retry when the model adds one anyway.
    assert triage.extract_json('```json\n{"level": "High"}\n```') == {"level": "High"}
