import pytest

from medrag.verification.parent_binding import bind_parent_fragments


def test_repeated_number_is_unique_inside_the_selected_parent_and_uses_unicode_offsets():
    answer = "😀 First arm: 12 people. Second arm: 12 people."
    row = bind_parent_fragments(answer, "Second arm: 12 people.", ["12 people"])
    assert row["position_valid"]
    span = row["answer_bindings"][0]["span"]
    assert span["start"] == answer.rindex("12 people")
    assert answer[span["start"] : span["end"]] == "12 people"
    assert span["offset_unit"] == "unicode_codepoint"


@pytest.mark.parametrize("parent", ["Same.", "Missing.", ""])
def test_unresolved_parent_does_not_fall_back_to_a_unique_global_fragment(parent):
    row = bind_parent_fragments("Same. Same. Unique.", parent, ["Unique"])
    assert not row["position_valid"]
    assert row["answer_bindings"][0]["status"] == "unresolved_parent"
    assert row["answer_bindings"][0]["span"] is None


def test_unique_text_outside_parent_is_rejected():
    row = bind_parent_fragments("Arm A: 12. Arm B: 19.", "Arm B: 19.", ["12"])
    assert row["answer_bindings"][0]["status"] == "not_found"
    assert not row["position_valid"]


def test_repetition_within_parent_and_overlapping_matches_remain_ambiguous():
    row = bind_parent_fragments("Intro. aaaa. End.", "aaaa.", ["aa"])
    b = row["answer_bindings"][0]
    assert b["status"] == "ambiguous" and b["match_count"] == 3
    assert [s["start"] for s in b["candidates"]] == [7, 8, 9]
    assert b["span"] is None


def test_discontiguous_fragments_are_not_silently_joined_or_rewritten():
    text = "At 12 months, arm A had 19 events per 100 participants."
    row = bind_parent_fragments(text, text, ["At 12 months", "19 events per 100 participants"])
    assert row["position_valid"]
    assert [b["span"]["text"] for b in row["answer_bindings"]] == [
        "At 12 months",
        "19 events per 100 participants",
    ]
    assert (
        bind_parent_fragments(text, text, ["19 events per 100 patients"])["position_valid"] is False
    )


def test_many_candidates_are_capped_without_claiming_uniqueness():
    parent = "a " * 20
    b = bind_parent_fragments("Prefix " + parent, parent, ["a"])["answer_bindings"][0]
    assert b["match_count"] == 20 and len(b["candidates"]) == 8
    assert b["candidates_truncated"] and b["span"] is None
