"""AI/developer-authored textual controls, not independent clinical gold.

Each entry records corpus ID, source sentence IDs, shared context, two scoped
statements, target group/quantity anchors, and extra required literal qualifiers.
The full abstract remains the supplied evidence. No candidate output informed these.
"""

# (document, sentence IDs, scope, statements, groups, values, qualifier terms)
DEFINITIONS = [
    (
        "20422174",
        [2, 4],
        "The ALTS report describes patients monitored for 2 years.",
        ["The ASCUS group included 3488 patients.", "The LSIL group included 1572 patients."],
        ["ASCUS", "LSIL"],
        ["3488", "1572"],
        ["2 years"],
    ),
    (
        "43220289",
        [5, 6],
        "The bariatric surgery study reports average losses of initial weight after surgery.",
        ["At 1 year, average weight loss was 24.6%.", "At 4 years, average weight loss was 22.3%."],
        ["1 year", "4 years"],
        ["24.6", "22.3"],
        ["average", "initial weight"],
    ),
    (
        "26611834",
        [4, 5],
        "The review of antenatal depression and adverse birth outcomes screened published studies.",
        [
            "The reviewed set contained 862 studies.",
            "The set meeting the selection criteria contained 29 studies.",
        ],
        ["reviewed", "selection criteria"],
        ["862", "29"],
        [],
    ),
    (
        "36558211",
        [1, 2, 5],
        "In the British dietary reanalysis, the FATg high-fat thresholds were daily amounts.",
        [
            "For men, the high-fat threshold was > 138 g/day.",
            "For women, the high-fat threshold was > 102 g/day.",
        ],
        ["men", "women"],
        ["138", "102"],
        ["g/day", ">"],
    ),
    (
        "15678772",
        [1, 3, 5],
        "The Swedish cohort reports high school attendance among men treated for haemangioma in infancy.",
        [
            "Among those not exposed, about 32% attended high school.",
            "Among those who received > 250 mGy, around 17% attended high school.",
        ],
        ["not exposed", "> 250 mGy"],
        ["32", "17"],
        ["about", "around"],
    ),
    (
        "1358909",
        [0, 3],
        "The Rotterdam population study assessed PAD in people aged 55 years and over.",
        ["In men, PAD prevalence was 16.9%.", "In women, PAD prevalence was 20.5%."],
        ["men", "women"],
        ["16.9", "20.5"],
        ["55 years and over"],
    ),
    (
        "6491532",
        [2, 4, 5, 6],
        "The Bangladesh prospective observational study reports treatment of multidrug-resistant TB.",
        [
            "Among the 515 enrolled patients, 84.4% had a bacteriologically favorable outcome.",
            "Treatment completion within 12 months was possible for 95% of patients.",
        ],
        ["bacteriologically favorable", "12 months"],
        ["84.4", "95"],
        ["observational"],
    ),
    (
        "35495268",
        [2, 5],
        "The trial studied overweight or obese patients with type 2 diabetes; these weight-loss percentages are at 1 year.",
        [
            "The intervention group had weight loss of 8.6%.",
            "The control group had weight loss of 0.7%.",
        ],
        ["intervention group", "control group"],
        ["8.6", "0.7"],
        ["1 year"],
    ),
    (
        "5597586",
        [4, 5, 9],
        "The case-control study concerns AL amyloidosis patients undergoing ASCT, with or without autonomic neuropathy (AN).",
        [
            "Median overall survival for patients with AN was 29 months.",
            "Median overall survival for controls was >60 months.",
        ],
        ["patients with AN", "controls"],
        ["29", "60"],
        ["Median", "months"],
    ),
    (
        "3222187",
        [1],
        "The study examined circulating 25(OH)D levels in women.",
        [
            "The Hispanic group comprised 1,605 women.",
            "The non-Hispanic White group comprised 354 women.",
        ],
        ["Hispanic", "non-Hispanic White"],
        ["1,605", "354"],
        [],
    ),
    (
        "24704139",
        [0, 3, 11],
        "At baseline in the randomized DPP cohort, these percentages concern history of hypertension.",
        ["Among men, the frequency was 29%.", "Among women, the frequency was 26%."],
        ["men", "women"],
        ["29", "26"],
        ["hypertension"],
    ),
    (
        "42150015",
        [3, 7],
        "In the cross-sectional study, age-specific AMH percentiles were compared with women with a regular menstrual cycle.",
        [
            "For current oral contraceptive users, AMH was 11 percentiles lower.",
            "For pregnant women, AMH was 17 percentiles lower.",
        ],
        ["oral contraceptive", "pregnant"],
        ["11", "17"],
        ["lower"],
    ),
    (
        "25589047",
        [6, 7, 11],
        "In the bevacizumab meta-analysis, the following percentages describe causes among fatal adverse events.",
        ["Hemorrhage accounted for 23.5%.", "Neutropenia accounted for 12.2%."],
        ["hemorrhage", "neutropenia"],
        ["23.5", "12.2"],
        [],
    ),
    (
        "23983289",
        [1, 6, 7],
        "In Medicare beneficiaries with atrial fibrillation, ICD-9-CM codes were compared against chart abstraction.",
        [
            "For valvular heart disease, positive predictive value was 0.93.",
            "Across all 6 common risk factors, negative predictive values ranged from 0.52 to 0.91.",
        ],
        ["valvular heart disease", "negative predictive values"],
        ["0.93", "0.52"],
        ["0.91"],
    ),
    (
        "26199970",
        [6, 8, 9, 11],
        "The meta-analysis compared angiotensin-system drugs with placebo or other antihypertensive medications in adults without major physical symptoms; quality of life was a secondary outcome.",
        [
            "For overall quality of life, the standard mean difference was 0.11.",
            "For the mental domain, the standard mean difference was 0.15.",
        ],
        ["overall quality of life", "mental"],
        ["0.11", "0.15"],
        ["standard mean difference"],
    ),
    (
        "29955650",
        [2, 3, 7, 8],
        "The English infectious intestinal disease study reports incidence per 100 person years.",
        [
            "In the community cohort, incidence was 19.4/100 person years.",
            "For cases presenting to general practice, incidence was 3.3/100 person years.",
        ],
        ["community", "general practice"],
        ["19.4", "3.3"],
        ["100 person years"],
    ),
    (
        "1781626",
        [0, 3, 4],
        "In the cross-sectional survey, poor self-rated health means worse than average.",
        ["Prevalence among Czechs was 8%.", "Prevalence among Hungarians was 19%."],
        ["Czechs", "Hungarians"],
        ["8", "19"],
        ["worse than average"],
    ),
    (
        "16204011",
        [3, 7, 8, 9, 10],
        "The systematic review concerns care seeking for ill or suspected ill neonates in LMICs; estimates varied across studies.",
        [
            "The median for some type of care seeking was 59%.",
            "The median for care seeking at a health care facility was 20%.",
        ],
        ["Care seeking", "health care facility"],
        ["59", "20"],
        ["median"],
    ),
    (
        "5132358",
        [2, 8, 9],
        "The report describes two children with relapsed and refractory pre-B-cell ALL treated with CTL019 cells.",
        [
            "In one patient, complete remission was ongoing at 11 months after treatment.",
            "The other patient had a relapse approximately 2 months after treatment.",
        ],
        ["one patient", "other patient"],
        ["11", "2"],
        ["after treatment"],
    ),
    (
        "20083834",
        [0, 2, 3],
        "The randomized crossover study involved 34 postmenopausal women; soy and milk diets lasted 6 weeks each.",
        [
            "Soy protein supplied 26±5 g protein per day.",
            "Soy isoflavones supplied 44±8 mg isoflavones per day.",
        ],
        ["protein", "isoflavones"],
        ["26", "44"],
        ["per day"],
    ),
    (
        "17914395",
        [5, 10, 11],
        "The convenience sample consisted of young African American adults aged 18-26 years; the measures below are adjusted R2.",
        [
            "For the summary CVD knowledge score, adjusted R2 was 0.158.",
            "For self-efficacy in changing CVD risk, adjusted R2 was 0.064.",
        ],
        ["summary CVD knowledge score", "self-efficacy in changing CVD risk"],
        ["0.158", "0.064"],
        ["adjusted R2"],
    ),
    (
        "14726759",
        [1, 5, 8],
        "The retrospective Finnish cervicocerebral artery dissection study reports the following follow-up outcomes.",
        [
            "At 3 months, 247 patients reached a favorable outcome.",
            "During follow-up with mean duration 4.0 years, 7 patients died.",
        ],
        ["favorable outcome", "died"],
        ["247", "7"],
        [],
    ),
    (
        "3524352",
        [2, 5],
        "The geographic analysis examined breast cancer mortality in northeastern US women during 1988-1992.",
        [
            "The demographic data covered 244 counties.",
            "The New York City-Philadelphia cluster had a 7.4% higher mortality rate than the rest of the Northeast.",
        ],
        ["counties", "higher mortality rate"],
        ["244", "7.4"],
        [],
    ),
    (
        "45336190",
        [3, 9, 10, 11],
        "In the phase 2 Alzheimer trial, these percentages describe reductions in plasma Abeta(40), not cerebrospinal fluid or cognitive benefit.",
        [
            "The 100-mg group had a reduction of 58.2%.",
            "The 140-mg group had a reduction of 64.6%.",
        ],
        ["100-mg group", "140-mg group"],
        ["58.2", "64.6"],
        ["plasma"],
    ),
]

EXCLUDED = {
    "42298280": "Most digits describe staining markers rather than two comparable numeric findings.",
    "23284774": "Numeric screen mainly matched an enumerated list, not two quantitative findings.",
    "195680777": "Multiple nested regimen comparisons need more extensive construction annotation; excluded before inference.",
    "13514898": "Multiple nested treatment/generation/end-point comparisons need more extensive annotation; excluded before inference.",
}

# Additional explicit negation targets, fixed before inference. Sentence IDs are
# added to the supplied original-answer view; all methods see the same text.
NEGATIONS = {
    "43220289": (
        11,
        "The decline in psychological improvements over time was not significant.",
        ["not significant", "decline"],
    ),
    "15678772": (
        7,
        "A negative dose-response relation was not evident for the test of spatial recognition.",
        ["not", "spatial recognition"],
    ),
    "35495268": (
        8,
        "An intensive lifestyle intervention focusing on weight loss did not reduce the rate of cardiovascular events in overweight or obese adults with type 2 diabetes.",
        ["did not reduce", "cardiovascular"],
    ),
    "3222187": (
        5,
        "No significant associations were found for polymorphisms in CYP24A1.",
        ["no significant", "CYP24A1"],
    ),
    "20083834": (
        3,
        "Results did not differ by equol production status or by baseline lipid concentration.",
        ["did not differ", "equol"],
    ),
    "45336190": (
        10,
        "No significant reduction was seen in cerebrospinal fluid Abeta levels.",
        ["no significant reduction", "cerebrospinal fluid"],
    ),
}
