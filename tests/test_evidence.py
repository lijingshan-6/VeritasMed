"""Source provenance and bounded repair behaviors, using fictional study data."""
import json
from unittest.mock import MagicMock, patch

from medrag.agent.evidence import (
    bind_claims, bind_components, missing_numeric_details, outline_status, repair_gaps,
)
from medrag.retrieval.retriever import RetrievedChunk


def chunk(doc_id="1", text="Sensitivity was 92% vs. 84% in 30 participants; P < .001."):
    return RetrievedChunk(f"pubmed:{doc_id}:0", text, 0.9,
                          {"source": "pubmed", "doc_id": doc_id, "pmid": doc_id})


def outline():
    source = chunk()
    return bind_components([{
        "requirement": "Diagnostic performance and comparator",
        "status": "supported",
        "evidence": [{"chunk_id": source.chunk_id, "quote": source.text}],
        "required_details": ["92% vs. 84%", "30 participants", "P < .001"],
    }, {
        "requirement": "Prospective patient benefit", "status": "missing",
        "gap": "The retrieved study does not establish prospective patient benefit.",
    }], [], [source])


def test_complete_comparison_and_inequality_survive_binding():
    component = outline()[0]
    assert component["required_details"] == ["92% vs. 84%", "30 participants", "P < .001"]
    assert component["evidence"][0]["citation"] == "PMID:1"


def test_selected_sentence_ids_recover_exact_quotes_without_model_transcription():
    source = chunk()
    result = bind_components([{
        "requirement": "Performance", "status": "supported", "evidence_ids": ["E1"],
    }], [], [source])
    assert result[0]["evidence"][0]["quote"] == source.text


def test_comparative_sentence_keeps_its_preceding_reference_values():
    source = chunk(text="Readers achieved sensitivity of 84%. Assistance achieved comparable sensitivity of 85%.")
    result = bind_components([{
        "requirement": "Diagnostic change", "status": "supported", "evidence_ids": ["E2"],
    }], [], [source])
    assert "Readers achieved sensitivity of 84%." in result[0]["required_details"]
    assert len(result[0]["evidence"]) == 2


def test_a_preceding_numeric_method_detail_is_not_an_answer_requirement():
    source = chunk(text="The probe had purity of 99%. Uptake was higher in positive tumors than negative tumors.")
    result = bind_components([{
        "requirement": "Tumor localization", "status": "supported", "evidence_ids": ["E2"],
    }], [], [source])
    assert not result[0]["required_details"]
    assert len(result[0]["evidence"]) == 1






def test_model_population_field_cannot_add_unrelated_method_sentences():
    source = chunk(text="The probe uses isotope 64. Uptake was 4.2%.")
    result = bind_components([{
        "requirement": "Uptake", "status": "supported", "evidence_ids": ["E2"],
    }], [], [source], [{"chunk_id": source.chunk_id, "quote": "The probe uses isotope 64.",
                       "required_details": ["isotope 64"]}])
    assert len(result[0]["evidence"]) == 1
    assert not result[0]["required_details"]


def test_omitted_answer_does_not_mean_source_evidence_is_missing():
    from medrag.agent.nodes import check_faithfulness
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=json.dumps({
        "supported": True, "complete": False, "boundary_correct": True,
        "component_checks": [{"id": "C1", "passed": False, "evidence_status": "missing",
                              "unsupported_source_inference": False,
                              "gap": "Answer omitted performance", "correction": "Include the result"}],
    }))
    with patch("medrag.agent.nodes.checking.make_llm_think", return_value=llm):
        result = check_faithfulness({"query": "Performance?", "answer": "No evidence",
                                    "answer_components": outline()[:1], "retrieved_chunks": [chunk()]})
    assert result["answer_components"][0]["status"] == "supported"
    assert result["repair_component_ids"] == ["C1"]


def test_last_check_removes_an_outcome_not_established_by_the_source():
    from medrag.agent.nodes import check_faithfulness
    component = dict(outline()[0], requirement="Fewer hospital admissions")
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=json.dumps({
        "supported": False, "complete": False, "boundary_correct": False,
        "component_checks": [{"id": "C1", "passed": False, "evidence_status": "missing",
                              "unsupported_source_inference": True,
                              "gap": "The answer incorrectly infers admissions from sensitivity.",
                              "correction": "Remove the admission claim"}],
    }))
    with patch("medrag.agent.nodes.checking.make_llm_think", return_value=llm):
        result = check_faithfulness({
            "query": "Did it reduce admissions?", "answer": "Hospital admissions decreased.",
            "answer_claims": [{"component_id": "C1", "text": "Hospital admissions decreased.", "cite": ["PMID:1"]}],
            "answer_components": [component], "retrieved_chunks": [chunk()], "regen_count": 2,
        })
    assert result["answer"] == "The retrieved evidence does not establish: Fewer hospital admissions."
    assert result["answer_claims"] == []
    assert result["evidence_status"] == "insufficient"


def test_named_study_is_selected_by_identity_instead_of_leading_rank():
    from medrag.agent.nodes import grade_relevance
    wrong = chunk("2", "Unrelated study: survival was 96%.")
    target = chunk()
    llm = MagicMock()
    llm.invoke.side_effect = [
        MagicMock(content=json.dumps({"source_ids": ["PMID:1"]})),
        MagicMock(content=json.dumps({"relevant": True, "score": 1, "components": [{
            "requirement": "Diagnostic performance", "status": "supported", "evidence_ids": ["E1"],
        }]})),
    ]
    with patch("medrag.agent.nodes.grading.make_llm_think", return_value=llm), patch("medrag.agent.nodes.grading.make_llm_fast", return_value=llm):
        result = grade_relevance({"query": "What did the diagnostic study find?",
                                 "source_scope": "single_study", "retrieved_chunks": [wrong, target]})
    assert result["selected_sources"] == ["PMID:1"]
    assert result["retrieved_chunks"] == [target]
    assert result["answer_components"][0]["evidence"][0]["quote"] == target.text


def test_invented_quote_and_misassigned_source_cannot_become_supported():
    for span in [
        {"chunk_id": "pubmed:1:0", "quote": "Patient survival improved."},
        {"chunk_id": "pubmed:1:0", "citation": "PMID:2", "quote": chunk().text},
    ]:
        result = bind_components([{"requirement": "Patient benefit", "status": "supported",
                                   "evidence": [span]}], [], [chunk()])
        assert result[0]["status"] == "missing"
        assert result[0]["evidence"] == []
        assert result[0]["gap"]


def test_adjacent_source_cannot_fill_a_component_or_hide_missing_comparator():
    accepted, issues = bind_claims([
        {"component_id": "C1", "text": "An unrelated review says 96%.", "cite": ["PMID:2"]},
    ], outline())
    assert not accepted
    assert any("omitted" in issue for issue in issues)


def test_missing_clinical_outcome_is_preserved_alongside_supported_diagnostics():
    status, gap = outline_status(outline())
    assert status == "partial"
    assert "prospective patient benefit" in gap.casefold()


def test_gap_rewrite_cannot_replace_the_requested_outcome():
    before = outline()
    result = repair_gaps(before, [
        {"component_id": "C1", "gap": "Wrongly overwrite the supported result"},
        {"component_id": "C2", "gap": "The study does not establish fewer hospital admissions."},
    ], ["C2"])
    assert result[0] == before[0]
    assert result[1]["gap"] == before[1]["gap"]
    assert result[1]["status"] == "missing"


def test_comparator_number_missing_from_answer_requests_component_repair():
    missing = missing_numeric_details(outline(), [{
        "component_id": "C1", "text": "Sensitivity was 92% in 30 participants; P < .001",
    }])
    assert missing == {"C1": ["92% vs. 84%"]}




def test_targeted_repair_retains_the_other_component():
    from medrag.agent.nodes import generate_answer_node
    components = outline()[:1]
    other = dict(components[0], id="C2", requirement="Study population")
    preserved = {"component_id": "C2", "text": "There were 30 participants", "cite": ["PMID:1"]}
    response = {"claims": [
        {"component_id": "C1", "text": "Sensitivity was 92% vs. 84%; P < .001", "cite": ["PMID:1"]},
    ], "evidence_status": "complete", "confidence": 0.5}
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=json.dumps(response))
    with patch("medrag.agent.nodes.generation.make_llm_fast", return_value=llm):
        result = generate_answer_node({
            "query": "Compare performance and report the population",
            "retrieved_chunks": [chunk()], "answer_components": [*components, other],
            "answer_claims": [preserved], "repair_component_ids": ["C1"],
            "regen_count": 1, "faithfulness_issues": "C1 missing the comparator",
        })
    assert preserved in result["answer_claims"]
    assert "92% vs. 84%" in result["answer"]
    assert "30 participants" in result["answer"]




def test_validation_cannot_claim_same_cohort_without_a_bound_basis():
    from medrag.agent.evidence import population_scope_issue
    component = {"evidence": [{"quote": "Multicenter validation improved reader accuracy."}]}
    assert population_scope_issue("Validation used the same four-hospital dataset.", component)
    assert population_scope_issue("The model was then validated in a separate multicenter validation set.", component)
    assert not population_scope_issue("Multicenter validation improved reader accuracy.", component)
    explicit = {"evidence": [{"quote": "Validation used the same dataset in cross-validation."}]}
    assert not population_scope_issue("Validation used the same dataset.", explicit)
    independent = {"evidence": [{"quote": "An independent cohort was used for validation."}]}
    assert not population_scope_issue("Validation used an independent cohort.", independent)


def test_quote_recovery_does_not_hide_rejected_explanation():
    from medrag.agent.nodes import generate_answer_node
    # No explicit cross-sectional design: the narrow design repair cannot apply.
    source = chunk(text="The 2020 study was observational.")
    components = bind_components([{"requirement": "Explain causal limits", "status": "supported",
        "evidence_ids": ["E1"], "required_details": [source.text]}], [], [source])
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=json.dumps({"claims": [{"component_id": "C1",
        "text": "Measurements were simultaneous at a single time point, so causality is unproven.",
        "cite": ["PMID:1"]}], "evidence_status": "complete"}))
    with patch("medrag.agent.nodes.generation.make_llm_fast", return_value=llm):
        result = generate_answer_node({"query": "Explain the design's causal limit",
            "retrieved_chunks": [source], "answer_components": components})
    # The rejected timing claim is removed and flagged for repair; no quotation is pasted in its place.
    assert 'simultaneous' not in result['answer']
    assert any('unreported timing' in issue for issue in result['binding_issues'])


def test_synthesized_answer_keeps_its_source_sentence_as_attached_evidence():
    from medrag.agent.nodes import generate_answer_node
    source = chunk(text="The area increased by 0.4 units at 6 months, P = .02.")
    components = bind_components([{"requirement": "Measured area change", "status": "supported",
        "evidence_ids": ["E1"], "required_details": [source.text]}], [], [source])
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=json.dumps({"claims": [{"component_id": "C1",
        "text": "Area increased by 0.4 units because the implant dissolved.", "cite": ["PMID:1"]}],
        "evidence_status": "complete"}))
    with patch("medrag.agent.nodes.generation.make_llm_fast", return_value=llm):
        result = generate_answer_node({"query": "What was the measured change?",
            "retrieved_chunks": [source], "answer_components": components})
    # Answers stay in the model's words. An unsupported addition such as this mechanism is
    # left for the check node and the claim audit to catch; the exact source sentence stays
    # attached to the component so the reader can compare.
    assert "0.4 units" in result['answer']
    assert result['answer_components'][0]['evidence'][0]['quote'] == source.text
    assert result['repair_history'] == []






def test_missing_outcome_does_not_invent_absent_patient_data():
    source = chunk(text="A simulated workflow used archived examinations with histopathology as the reference.")
    components = bind_components([{
        "requirement": "Reduced invasive procedures versus usual care", "status": "missing",
        "evidence_ids": ["E1"], "gap": "There were no real patients or biopsies.",
    }], [], [source])
    assert "no real" not in components[0]["gap"]
    assert "Reduced invasive procedures versus usual care" in components[0]["gap"]
    assert repair_gaps(components, [{"component_id": "C1", "gap": "The study does not establish benefit because no patients existed."}], ["C1"]) == components


def test_method_purpose_alone_recovers_same_source_steps_not_neighboring_study():
    source = chunk(text="The method addresses slow acquisition. The technique combined rotated sampling and Hadamard encoding.")
    neighbor = chunk("2", "The technique used a different filter.")
    components = bind_components([{"requirement": "Problem addressed by the reconstruction method", "status": "supported", "evidence_ids": ["E1"]}], [], [source, neighbor])
    quotes = [s["quote"] for s in components[0]["evidence"]]
    assert "The technique combined rotated sampling and Hadamard encoding." in quotes
    assert neighbor.text not in quotes


def test_boundary_distinguishes_measured_outcome_from_requested_comparison():
    from medrag.agent.nodes import grade_relevance
    for comparison_supported in (False, True):
        source = chunk(text=("Mortality was 5% with treatment versus 10% with control among 80 randomized participants."
                             if comparison_supported else "Mortality was 5% among 80 participants in one treatment cohort."))
        llm = MagicMock()
        llm.invoke.return_value = MagicMock(content=json.dumps({"assessments": [{
            "id": "C1", "outcome_measured": True, "requested_comparison_supported": comparison_supported,
            "outcome_evidence_ids": ["E1"], "comparison_evidence_ids": ["E1"] if comparison_supported else [],
            "design_evidence_ids": [],
        }]}))
        with patch("medrag.agent.nodes.grading.make_llm_think", return_value=llm):
            result = grade_relevance({"query": "Does the study establish comparative mortality benefit?",
                                     "source_scope": "single_study", "selected_sources": ["PMID:1"],
                                     "answer_mode": "evidence_boundary", "answer_requirements": ["Comparative mortality benefit"],
                                     "retrieved_chunks": [source]})
        assert result["relevant"] is True  # A valid missing comparator needs no new study.
        assert result["answer_components"][0]["requirement"] == "Comparative mortality benefit"
        assert result["answer_components"][0]["status"] == ("supported" if comparison_supported else "missing")




def test_joint_study_plan_keeps_both_sources_and_original_question():
    from medrag.agent.nodes import grade_relevance
    first = chunk(text="Method A reduced scan time.")
    second = chunk("2", "Method B reduced noise.")
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=json.dumps({"relevant": True, "score": .9,
        "components": [{"requirement": requirement, "status": "supported", "evidence_ids": [evidence]}
                       for requirement, evidence in [("Method A result", "E1"), ("Method B result", "E2")]]}))
    with patch("medrag.agent.nodes.grading.make_llm_think", return_value=llm):
        result = grade_relevance({"query": "Compare method A and method B", "source_scope": "multi_source",
                                 "selected_sources": ["PMID:1", "PMID:2"], "retrieved_chunks": [first, second]})
    assert [c["evidence"][0]["citation"] for c in result["answer_components"]] == ["PMID:1", "PMID:2"]
    prompt = llm.invoke.call_args.args[0][1].content
    assert "Method B reduced noise" in prompt and "Method A reduced scan time" in prompt
    assert "Query: Compare method A and method B" in prompt
    assert "[E1]" in prompt and "[E2]" in prompt


def test_check_schema_requires_each_gap_decision():
    from medrag.agent.nodes.checking import _check_schema
    schema = _check_schema([{"id": "C1"}, {"id": "C2"}])
    assert schema["properties"]["component_checks"]["required"] == ["C1", "C2"]


def test_source_cards_keep_descriptive_suffix_candidates_and_disclose_mismatches():
    from medrag.agent.nodes.retrieval import _source_cards
    source = chunk(text="RX2 uptake was measured in tumor models.")
    assert list(_source_cards("RX2-targeted imaging results?", [source])) == ["PMID:1"]
    assert list(_source_cards("RX2-expressing models?", [source])) == ["PMID:1"]
    assert _source_cards("RX3-targeted imaging results?", [source])["PMID:1"]["unmatched_identifiers"] == ["RX3"]
    assert _source_cards("RX2-A imaging results?", [source])["PMID:1"]["unmatched_identifiers"] == ["RX2-A"]


def test_partial_gap_does_not_deny_the_supported_result():
    component = bind_components([{"requirement": "Accuracy and admissions", "status": "partial",
        "evidence_ids": ["E1"], "missing_outcome": "effects on hospital admissions"}], [], [chunk()])[0]
    assert component["gap"] == "The retrieved evidence does not establish: effects on hospital admissions."
    assert "Accuracy" not in component["gap"]


def test_string_details_remain_whole_and_paraphrased_contract_keeps_source():
    source = chunk(text="We included 3455 births. Validation used simulated and experimental images.")
    result = bind_components([{"requirement": "Validation", "status": "supported",
        "evidence_ids": ["E2"], "required_details": ["Validation with both data types"]}], [], [source],
        [{"evidence_id": "E1", "required_details": "3455 births"}])
    assert "3455 births" in result[0]["required_details"]
    assert "3" not in result[0]["required_details"]
    assert "Validation used simulated and experimental images." in result[0]["required_details"]


def test_design_label_cannot_become_unreported_measurement_timing():
    source = chunk(text="This was a cross-sectional study of flow and ventricular mass.")
    components = bind_components([{"requirement": "Causal limitation", "status": "supported",
        "evidence_ids": ["E1"]}], [], [source])
    claims, issues = bind_claims([{"component_id": "C1", "text": "The study measured flow and mass simultaneously.",
        "cite": ["PMID:1"]}], components)
    assert not claims and any("unreported timing" in issue for issue in issues)
    safe = {"component_id": "C1", "text": "The cross-sectional association does not establish an intervention benefit.", "cite": ["PMID:1"]}
    assert bind_claims([safe], components)[0] == [safe]


def test_timing_repair_keeps_causal_explanation_without_inventing_a_protocol():
    from medrag.agent.evidence import repair_design_scope
    source = chunk(text="This was a cross-sectional study of exposure and outcome.")
    components = bind_components([{"requirement": "Why causal benefit cannot be established",
                                  "status": "supported", "evidence_ids": ["E1"]}], [], [source])
    unsafe = {"component_id": "C1", "text": "Concurrently measured variables cannot establish benefit.",
              "cite": ["PMID:1"]}
    repaired = repair_design_scope(components, [unsafe])
    assert source.text in repaired[0]["text"]
    assert "changing the exposure" in repaired[0]["text"]
    assert "concurrent" not in repaired[0]["text"].lower()
    assert bind_claims(repaired, components)[0] == repaired
    assert repair_design_scope(components, repaired) == repaired
    longitudinal = bind_components([{"requirement": "Causal limitation", "status": "supported",
                                     "evidence_ids": ["E1"]}], [],
                                   [chunk(text="This was a longitudinal observational study.")])
    assert repair_design_scope(longitudinal, [unsafe]) == [unsafe]
    assert not bind_claims([unsafe], longitudinal)[0]


def test_review_reads_and_repairs_the_displayed_gap_with_the_answer():
    from medrag.agent.nodes import check_faithfulness
    source = chunk(text="Method A improved images in phantom and patient tests.")
    component = bind_components([{"requirement": "Validation findings", "status": "partial",
        "evidence_ids": ["E1"], "missing_outcome": "quantitative validation metrics"}], [], [source])[0]
    component.update(answer=source.text, source_hint="PMID:1")
    llm = MagicMock()
    llm.invoke.return_value = MagicMock(content=json.dumps({
        "supported": True, "complete": False, "boundary_correct": False,
        "component_checks": {"C1": {"passed": False, "evidence_status": "supported",
            "requirement_requested": True, "unsupported_source_inference": False,
            "gap": "", "missing_outcome": "", "correction": "Remove the unrequested quantitative gap"}},
    }))
    with patch("medrag.agent.nodes.checking.make_llm_think", return_value=llm):
        result = check_faithfulness({"query": "What validation findings did methods A and B report?",
            "source_scope": "multi_source", "selected_sources": ["PMID:1", "PMID:2"],
            "retrieved_chunks": [source], "answer_components": [component],
            "answer_claims": [{"component_id": "C1", "text": source.text, "cite": ["PMID:1"]}],
            "answer": source.text + ' ' + component["gap"], "evidence_status": "partial"})
    prompt = llm.invoke.call_args.args[0][1].content
    assert source.text in prompt and component["gap"] in prompt
    assert result["answer_components"][0]["status"] == "supported"
    assert result["evidence_gap"] == ""
    assert "quantitative" not in result["answer"]






def test_named_identifier_is_not_crowded_out_or_matched_in_references():
    from medrag.agent.nodes.retrieval import _source_cards
    wrong = [chunk(str(i), "A receptor imaging study targeting RX20.") for i in range(2, 7)]
    reference = chunk("7", "References: RX2 tumor imaging study.")
    reference.payload['section'] = 'REF'
    target = chunk(text="Preclinical RX-2 targeted imaging found specific uptake.")
    cards = _source_cards("What did the RX2 imaging study find?", [*wrong, reference, target])
    assert next(iter(cards)) == 'PMID:1'
    assert 'PMID:7' not in cards
    assert cards['PMID:1']['matched_identifiers'] == ['RX2']
    assert all(c['unmatched_identifiers'] == ['RX3'] for c in
               _source_cards("What did the RX3 imaging study find?", [*wrong, reference, target]).values())


def test_open_boundary_names_missing_effect_without_invented_explanation():
    source = chunk(text="The workflow was simulated using patient records and biopsy results.")
    raw = {"requirement": "Identify the real-world clinical effect that remains untested",
           "status": "missing", "evidence_ids": ["E1"],
           "missing_outcome": "prospective deployment effects on patient care"}
    components = bind_components([raw], [], [source])
    assert components[0]["gap"] == "The retrieved evidence does not establish: prospective deployment effects on patient care."
    raw['missing_outcome'] = 'patient benefit because there were no patients'
    assert 'no patients' not in bind_components([raw], [], [source])[0]['gap']


def test_exact_population_quote_does_not_inherit_another_sentences_role():
    source = chunk(text="The workflow was simulated on 40 examinations. The 40 examinations were used for testing.")
    components = bind_components([{"requirement": "Study workflow", "status": "supported",
                                  "evidence_ids": ["E1", "E2"]}], [], [source])
    claim = {'component_id': 'C1', 'cite': ['PMID:1'],
             'text': 'The study reports: "The workflow was simulated on 40 examinations."'}
    accepted, issues = bind_claims([claim], components)
    assert accepted == [claim] and not issues
