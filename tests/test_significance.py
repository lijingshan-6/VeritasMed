"""The non-significance advisory: flags "no difference" claims resting on non-significant results."""
from medrag.verification.significance import nonsignificance_diagnostic as check


def test_flags_no_difference_from_nonsignificant_source():
    out = check("HFNC were not noisier than bubble CPAP in preterm infants",
                ["There was no evidence of a difference in average noise levels measured at the EAM."])
    assert out["status"] == "flagged" and out["claim_phrase"] == "not noisier"
    assert out["overrides_relation"] is False


def test_flags_p_value_above_threshold():
    assert check("Survival did not differ between groups", ["68.6 vs. 58.8 %, P = 0.085"])["status"] == "flagged"
    assert check("Cost was equivalent between the arms", ["$16,789 vs $16,815; P = 0.9557"])["status"] == "flagged"


def test_correctly_hedged_claims_are_not_flagged():
    src = ["No statistically significant difference was found (p = 0.33)."]
    for claim in ["Sensitivity did not differ significantly between the views",
                  "There was no significant difference in sensitivity",
                  "Oblique views were not shown to improve sensitivity",
                  "The study found no evidence of a difference"]:
        assert check(claim, src)["status"] == "not_applicable", claim


def test_significant_sources_and_missing_evidence_are_not_flagged():
    assert check("Noise did not differ", ["Noise increased with gas flow (p=0.007)."])["status"] == "not_applicable"
    assert check("Noise did not differ", [])["status"] == "not_applicable"
    assert check("Noise increased with flow", ["not significant"])["status"] == "not_applicable"
