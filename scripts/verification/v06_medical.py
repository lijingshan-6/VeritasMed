"""Source-anchored constructed diagnostics, authored before candidate outputs.

Each tuple: selection index, relevant sentence IDs, unrelated retained ID, two facts,
two faithful paraphrases, a single first-fact mutation. No independent expert labels.
"""

import json

from medrag.verification.atomic_schema import AtomicAuditRequest
from medrag.verification.scifact import object_hash, read_jsonl
from v06_prepare import CACHE, OUT

DEFINITIONS = [
    (
        0,
        [5, 6],
        3,
        [
            "The daily active capsule contained 40 mg of folic acid",
            "the primary outcome was all-cause mortality",
        ],
        [
            "Folic acid was given at 0.04 g in the daily active capsule",
            "all-cause mortality served as the primary endpoint",
        ],
        ["40 mg", "100 mg"],
    ),
    (
        1,
        [6, 7],
        2,
        [
            "The ocular inflammation cohort included 7957 US residents",
            "2340 participants received immunosuppressive drugs during follow-up",
        ],
        [
            "There were 7,957 US residents in the ocular inflammation cohort",
            "immunosuppressive treatment was received by 2,340 of them during follow-up",
        ],
        ["7957", "2340"],
    ),
    (
        2,
        [3, 6],
        0,
        [
            "Sympathetic activation was greater in pregnant women than nonpregnant controls across all 3 minutes of cold pressor stimulation",
            "mean arterial pressure during peak sympathoexcitation was not different between these groups",
        ],
        [
            "Throughout the three-minute cold pressor stimulation, pregnant women showed greater sympathetic activation than nonpregnant controls",
            "the groups did not differ in mean arterial pressure at peak sympathoexcitation",
        ],
        ["3 minutes", "5 minutes"],
    ),
    (
        3,
        [10],
        2,
        [
            "Anterior resection for rectal cancer was received by 67.4% of patients in the most deprived fifth",
            "75.5% of patients in the least deprived fifth received that procedure",
        ],
        [
            "In the most deprived fifth, the proportion receiving anterior resection for rectal cancer was 67.4%",
            "in the least deprived fifth, the corresponding proportion was 75.5%",
        ],
        ["67.4%", "75.5%"],
    ),
    (
        4,
        [4],
        3,
        [
            "The epigenome-wide methylation analysis included 64 endometrial cancer tissue samples",
            "it included 23 control samples",
        ],
        [
            "Endometrial cancer tissues numbered sixty-four in the epigenome-wide methylation analysis",
            "the control sample count was twenty-three",
        ],
        ["64", "23"],
    ),
    (
        5,
        [5, 7],
        3,
        [
            "Average colonoscopy use was 285 per 100,000 per quarter in period 1",
            "it was 1919 per 100,000 per quarter in period 3",
        ],
        [
            "In period 1 the quarterly average colonoscopy rate was 285 per 100,000",
            "the corresponding period 3 rate was 1,919 per 100,000",
        ],
        ["285", "1919"],
    ),
    (
        6,
        [3, 4, 7],
        2,
        [
            "By age 2 years, 858 infants had received multidisciplinary neurodevelopmental assessment",
            "122 of those 858 survivors had cerebral palsy at age 2",
        ],
        [
            "Multidisciplinary neurodevelopmental assessment by age two covered 858 infants",
            "at that age cerebral palsy was present in 122 of the 858 survivors",
        ],
        ["858 infants", "2318 infants"],
    ),
    (
        7,
        [5, 6, 7],
        0,
        [
            "Nine randomised studies of psychiatric instruments were identified",
            "four studies with 2457 participants could be pooled for the effect of feedback on recognition of depressive disorders",
        ],
        [
            "The review identified 9 randomised psychiatric-instrument studies",
            "pooling of the feedback effect on depressive-disorder recognition covered 4 studies and 2,457 participants",
        ],
        ["Nine", "Four"],
    ),
    (
        8,
        [4, 8],
        2,
        [
            "Compared with placebo, orlistat reduced weight by 2.9 kg in the included adult trials",
            "sibutramine reduced weight by 4.2 kg compared with placebo",
        ],
        [
            "The included adult trials reported 2,900 g less weight with orlistat than placebo",
            "the corresponding reduction for sibutramine versus placebo was 4,200 g",
        ],
        ["2.9 kg", "4.2 kg"],
    ),
    (
        9,
        [11],
        4,
        [
            "The rate of preventable ordering adverse drug events was 10.4 per 1000 patient-days before the intervention",
            "it was 3.5 per 1000 patient-days after the intervention",
        ],
        [
            "Before the intervention, preventable prescribing adverse events occurred at 10.4 per 1,000 patient-days",
            "afterwards the rate was 3.5 per 1,000 patient-days",
        ],
        ["10.4", "3.5"],
    ),
    (
        10,
        [5, 6],
        0,
        [
            "The residual lifetime risk of hypertension was 90% in both 55- and 65-year-old participants",
            "the lifetime probability of receiving antihypertensive medication was 60%",
        ],
        [
            "For participants aged 55 or 65, residual lifetime hypertension risk was ninety percent",
            "lifetime receipt of antihypertensive medication had a probability of sixty percent",
        ],
        ["90%", "60%"],
    ),
    # Selection 11 is excluded: internally inconsistent 1988-9/1998-9 and truncated source.
    (
        12,
        [1, 2, 4],
        0,
        [
            "The authors reported integrin alpha-v-beta-3 as a marker of breast, lung and pancreatic carcinomas with stem-like properties resistant to erlotinib",
            "pharmacological pathway targeting with bortezomib reversed both tumour stemness and erlotinib resistance",
        ],
        [
            "According to the authors, erlotinib-resistant stem-like breast, lung and pancreatic carcinomas were marked by integrin alpha-v-beta-3",
            "bortezomib targeting of the pathway reversed erlotinib resistance as well as tumour stemness",
        ],
        ["resistant to erlotinib", "sensitive to erlotinib"],
    ),
    (
        13,
        [1, 2, 6],
        4,
        [
            "Treatment response was reported in 30.3% of the amitriptylinoxide group",
            "it was reported in 22.4% of the amitriptyline group",
        ],
        [
            "The reported response proportion for amitriptylinoxide was 30.3%",
            "for amitriptyline the response proportion was 22.4%",
        ],
        ["30.3%", "22.4%"],
    ),
    (
        14,
        [7, 8],
        4,
        [
            "4828 eligible Natsal-3 participants agreed to provide a urine sample",
            "4550 participants remained with STI test results after 278 samples were excluded",
        ],
        [
            "A urine sample was agreed to by 4,828 eligible Natsal-3 participants",
            "excluding 278 samples left STI results for 4,550 participants",
        ],
        ["4828", "8047"],
    ),
    (
        15,
        [7, 13],
        2,
        [
            "Severe hepatotoxicity was observed in 31 of 298 patients",
            "no irreversible outcomes were seen among patients with severe hepatotoxicity",
        ],
        [
            "Of the 298 patients, 31 had severe hepatotoxicity",
            "the severe-hepatotoxicity patients had no observed irreversible outcomes",
        ],
        ["31 of 298", "298 of 298"],
    ),
    (
        16,
        [3, 5],
        1,
        [
            "37 studies met the inclusion criteria in the tricyclic antidepressant headache review",
            "eligible trials used tricyclics as the only treatment for at least four weeks",
        ],
        [
            "The headache review included thirty-seven qualifying studies",
            "the trials required tricyclic-only treatment lasting a minimum of 28 days",
        ],
        ["37 studies", "73 studies"],
    ),
    (
        17,
        [3, 4],
        1,
        [
            "731 of the original 824 DESMOND trial participants were eligible for follow-up",
            "biomedical data were collected on 604 participants",
        ],
        [
            "Follow-up eligibility in DESMOND covered 731 participants out of the original 824",
            "604 participants contributed biomedical data",
        ],
        ["731 of the original 824", "824 of the original 824"],
    ),
    (
        18,
        [3, 4, 8],
        2,
        [
            "Within the first treatment hour, 70% of the NIV group improved their PaO2-to-FIO2 ratio",
            "25% of the standard-treatment group improved that ratio in the same hour",
        ],
        [
            "Improvement in the PaO2/FIO2 ratio within hour one occurred in 70 percent of NIV patients",
            "the same first-hour improvement occurred in 25 percent of standard-treatment patients",
        ],
        ["70%", "25%"],
    ),
    (
        19,
        [4, 8],
        2,
        [
            "The dialysis antihypertensive meta-analysis identified 1202 patients in five studies",
            "publication bias was indicated by Egger's test and the funnel plot",
        ],
        [
            "Five studies contributed 1,202 patients to the dialysis antihypertensive meta-analysis",
            "the funnel plot and Egger's test provided evidence of publication bias",
        ],
        ["1202", "2102"],
    ),
    (
        20,
        [6, 7, 8],
        2,
        [
            "Participants received five doses of 150 mg alirocumab two weeks apart after placebo",
            "postprandial triglycerides and apoB48 were measured in 10 participants",
        ],
        [
            "After placebo, alirocumab was administered on five occasions at 0.15 g per dose with fourteen-day spacing",
            "10 participants had measurements of postprandial triglycerides and apoB48",
        ],
        ["150 mg", "250 mg"],
    ),
    (
        21,
        [2, 3, 11],
        1,
        [
            "The qualitative prescribing study included 20 general practitioners and 35 consulting patients",
            "the authors were developing an educational intervention based on the findings",
        ],
        [
            "There were twenty general practitioners and thirty-five consulting patients in the prescribing study",
            "an educational intervention building on these findings was under development by the authors",
        ],
        [
            "20 general practitioners and 35 consulting patients",
            "35 general practitioners and 20 consulting patients",
        ],
    ),
    (
        22,
        [4],
        3,
        [
            "Prior-year WMH-CIDI/DSM-IV disorder prevalence was 4.3% in Shanghai",
            "it was 26.4% in the United States",
        ],
        [
            "Shanghai's prevalence of a WMH-CIDI/DSM-IV disorder over the preceding year was 4.3%",
            "the corresponding United States prevalence was 26.4%",
        ],
        ["4.3%", "26.4%"],
    ),
    (
        23,
        [2, 5],
        4,
        [
            "The CALIBER cohort included patients aged 30 years or older who were initially free of cardiovascular disease",
            "83,098 initial cardiovascular presentations were recorded over a median 5.2 years of follow-up",
        ],
        [
            "At entry, CALIBER patients were at least thirty years old and had no cardiovascular disease",
            "median follow-up of 5.2 years yielded 83,098 initial cardiovascular presentations",
        ],
        [
            "initially free of cardiovascular disease",
            "initially diagnosed with cardiovascular disease",
        ],
    ),
]


def prepare():
    import re

    manifest = json.loads((OUT / "splits.json").read_text(encoding="utf8"))
    docs = {str(d["doc_id"]): d for d in read_jsonl(CACHE / "corpus.jsonl")}
    selection = []
    seen = set()
    for entry in manifest["entries"]:
        if not entry["split"].startswith("medical_") or entry["group_id"] in seen:
            continue
        members = [e for e in manifest["entries"] if e["group_id"] == entry["group_id"]]
        eligible = [
            docs[e["document_id"]]
            for e in members
            if re.search(
                r"\b(patient|trial|participants|women|men|adults|children|cohort|randomized)\b",
                " ".join(docs[e["document_id"]]["abstract"]),
                re.I,
            )
            and sum(bool(re.search(r"\d", s)) for s in docs[e["document_id"]]["abstract"]) >= 2
        ]
        doc = sorted(eligible, key=lambda d: object_hash(str(d["doc_id"])))[0]
        seen.add(entry["group_id"])
        selection.append(
            {
                "group_id": entry["group_id"],
                "split": entry["split"],
                "document_id": str(doc["doc_id"]),
            }
        )
    entries = []
    for index, ids, unrelated, facts, paraphrases, mutation in DEFINITIONS:
        chosen = selection[index]
        d = docs[chosen["document_id"]]
        for variant in ("original_meaning", "paraphrase", "single_error", "evidence_removed"):
            fs = paraphrases if variant == "paraphrase" else list(facts)
            if variant == "single_error":
                assert mutation[0] in fs[0]
                fs[0] = fs[0].replace(*mutation, 1)
            answer = fs[0] + ", while " + fs[1] + "."
            sentence_ids = [unrelated] if variant == "evidence_removed" else ids
            source = "\n".join(d["abstract"][i] for i in sentence_ids)
            item = AtomicAuditRequest(
                answer=answer,
                sources=[{"id": str(d["doc_id"]), "title": d["title"], "text": source}],
                strategy="direct",
            )
            relations = (
                ["insufficient"] * 2
                if variant == "evidence_removed"
                else ["contradicted" if variant == "single_error" else "supported", "supported"]
            )
            entries.append(
                {
                    "case_id": f"medical-{index + 1:02d}-{variant}",
                    **chosen,
                    "variant": variant,
                    "source_sentence_ids": sentence_ids,
                    "input_sha256": object_hash(item.model_dump()),
                    "answer": answer,
                    "facts": [
                        {
                            "quote": fact,
                            "relation": r,
                            "start": answer.index(fact),
                            "end": answer.index(fact) + len(fact),
                        }
                        for fact, r in zip(fs, relations)
                    ],
                    "transformation": mutation if variant == "single_error" else variant,
                }
            )
    result = {
        "label_provenance": "source-anchored developer/AI construction; not independent clinical gold",
        "source_view": "Only listed verbatim sentences are supplied; not full abstract. Unrelated retained sentences cannot establish the two facts.",
        "excluded": [
            {
                "selection_index": 11,
                "document_id": "42291761",
                "reason": "Internal year inconsistency and truncated text; no certain labels authored",
            }
        ],
        "groups": 23,
        "cases": entries,
        "scoring": "Per authored fact: all nonspace gold characters covered by one checked claim or the union of same-relation atomic spans; partial coverage separate. This is location-linked diagnostic scoring, not independent semantic scoring of parsed text.",
    }
    path = OUT / "medical.json"
    if path.exists() and json.loads(path.read_text(encoding="utf8")) != result:
        raise ValueError("Medical labels already frozen")
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(f"Frozen {len(entries)} cases in 23 groups (15 development, 8 transfer)")


def cases(split):
    docs = {str(d["doc_id"]): d for d in read_jsonl(CACHE / "corpus.jsonl")}
    result = []
    for e in json.loads((OUT / "medical.json").read_text(encoding="utf8"))["cases"]:
        if split and e["split"] != split:
            continue
        d = docs[e["document_id"]]
        item = AtomicAuditRequest(
            answer=e["answer"],
            sources=[
                {
                    "id": e["document_id"],
                    "title": d["title"],
                    "text": "\n".join(d["abstract"][i] for i in e["source_sentence_ids"]),
                }
            ],
        )
        if object_hash(item.model_dump()) != e["input_sha256"]:
            raise ValueError("Medical source/input changed")
        result.append({**e, "input": item, "id": e["case_id"], "source_id": e["document_id"]})
    return result


if __name__ == "__main__":
    prepare()
