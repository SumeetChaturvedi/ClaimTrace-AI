"""Verbatim structured data for Scenario 7's 8 approved documents."""

from pdf_template import DocumentSpec

SCENARIO = 7

DOCUMENTS: list[DocumentSpec] = [

    # Document 1 -- INSP-NRB4-014
    DocumentSpec(
        doc_id="INSP-NRB4-014",
        title="Quality Inspection Report — Review of Cube Test Results, Pier P5 Pier Shaft",
        doc_type="PROGRESS_REPORT",
        doc_type_tag="QUALITY INSPECTION REPORT",
        letterhead="ENGINEER",
        date="16-Mar-2022",
        from_="QA Engineer, Meridian Engineering Consultants",
        to="Resident Engineer (Er. Anand Vasker), copied to project file",
        extra_meta=[("Location", "Pier P5, Nandira River Bridge Project — Package NRB-4")],
        body=[
            ("heading", "FINDINGS:"),
            ("bullet", "Routine review of Cube Test Report LAB-NRB4-034, issued 15-Mar-2022 "
                       "by Suvarna Materials Testing Laboratory, covering the Pier P5 pier "
                       "shaft pour of 14-Feb-2022 (Grade M40)."),
            ("bullet", "28-day results for Test Set B (representing the middle portion of the "
                       "pour, approximately 30m3, cast between 11:40 and 13:10) show an "
                       "average compressive strength of 35.0 N/mm2, below the specified "
                       "characteristic strength of 40 N/mm2 for Grade M40, and below the "
                       "minimum individual result threshold applicable under the "
                       "Specification."),
            ("bullet", "Test Sets A and C, representing the remainder of the same pour, both "
                       "exceed the specified characteristic strength with no cause for "
                       "concern."),
            ("bullet", "Recommend the Engineer raise a Non-Conformance Report in respect of "
                       "the Set B result and that the Contractor be instructed accordingly."),
            ("heading", "OTHER SITE OBSERVATIONS TODAY:"),
            ("bullet", "Reinforcement inspection carried out at Pier P6 pile cap ahead of "
                       "scheduled concrete pour, Hold Point (b) cleared."),
            ("bullet", "Routine servicing of the site's remaining tower crane carried out by "
                       "the equipment supplier; crane returned to service same day."),
            ("bullet", "Note: the concrete curing tank heater at the site laboratory compound "
                       "was found faulty during routine equipment checks in late February 2022 "
                       "and was logged for repair; repair completed 04-Mar-2022. Logged for "
                       "reference only, no immediate action required."),
            ("bullet", "Approach road pavement works on the right bank progressing to "
                       "programme."),
        ],
        closing_lines=["Reported by: QA Engineer, Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # Document 2 -- LAB-NRB4-034
    DocumentSpec(
        doc_id="LAB-NRB4-034",
        title="Cube Test Report — Pier P5 Pier Shaft Pour, 14-Feb-2022",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="LABORATORY TEST REPORT",
        letterhead="THIRD_PARTY",
        letterhead_org_override="Suvarna Materials Testing Laboratory",
        date="15-Mar-2022",
        from_="Suvarna Materials Testing Laboratory",
        to="Meridian Engineering Consultants",
        cc="Sagara Constructions Pvt. Ltd.",
        subject="Compressive Strength Test Results — Pier P5 Pier Shaft, Pour Date "
                "14-Feb-2022, Grade M40",
        body=[
            ("para", "Specified characteristic strength: 40 N/mm2 at 28 days (Grade M40, per "
                     "Employer's Requirements Section 5 and the Specification)."),
            ("subheading", "TEST SET A (first ~30m3, cast 09:15–10:50):"),
            ("para", "7-day results (individual): 26.8, 28.1, 27.6 N/mm2 — Average: 27.5 "
                     "N/mm2"),
            ("para", "28-day results (individual): 42.1, 43.5, 41.8 N/mm2 — Average: 42.5 "
                     "N/mm2"),
            ("para", "ASSESSMENT: Satisfactory. Exceeds specified characteristic strength."),
            ("subheading", "TEST SET B (middle ~30m3, cast 11:40–13:10):"),
            ("para", "7-day results (individual): 24.2, 25.6, 24.6 N/mm2 — Average: 24.8 "
                     "N/mm2"),
            ("para", "28-day results (individual): 35.2, 33.8, 36.1 N/mm2 — Average: 35.0 "
                     "N/mm2"),
            ("para", "ASSESSMENT: Does not meet specified characteristic strength. Both the "
                     "average and each individual result fall below the acceptance criteria "
                     "in the Specification."),
            ("subheading", "TEST SET C (final ~2m3, cast 13:10–13:25):"),
            ("para", "7-day results (individual): 27.4, 28.9, 28.0 N/mm2 — Average: 28.1 "
                     "N/mm2"),
            ("para", "28-day results (individual): 44.0, 42.7, 43.1 N/mm2 — Average: 43.3 "
                     "N/mm2"),
            ("para", "ASSESSMENT: Satisfactory. Exceeds specified characteristic strength."),
            ("para", "Cubes cured in the site laboratory curing tank in accordance with the "
                     "Specification, save that a fault in the curing tank heater was logged "
                     "by the Engineer between approximately 18-Feb-2022 and 04-Mar-2022 "
                     "(repaired 04-Mar-2022); this period overlaps the early curing age of "
                     "the 28-day cubes for this pour."),
        ],
        closing_lines=["Issued by: Suvarna Materials Testing Laboratory"],
        scenario=SCENARIO,
    ),

    # Document 3 -- NCR-NRB4-001
    DocumentSpec(
        doc_id="NCR-NRB4-001",
        title="Non-Conformance Report NCR-NRB4-001 — Pier P5 Pier Shaft, Concrete Strength "
              "(Set B)",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="NON-CONFORMANCE REPORT",
        letterhead="ENGINEER",
        date="18-Mar-2022",
        from_="Engineer, Meridian Engineering Consultants",
        to="Sagara Constructions Pvt. Ltd.",
        subject="Non-Conformance Report — Cube Test Results Below Specified Strength, Pier "
                "P5 Pier Shaft",
        body=[
            ("para", "1. NON-CONFORMANCE: Cube Test Report LAB-NRB4-034 dated 15-Mar-2022 "
                     "records that Test Set B, from the Pier P5 pier shaft pour of "
                     "14-Feb-2022, achieved a 28-day average compressive strength of 35.0 "
                     "N/mm2, against the specified characteristic strength of 40 N/mm2 for "
                     "Grade M40, with each individual result also below the acceptance "
                     "criteria in the Specification. This is recorded per Employer's "
                     "Requirements Section 12 and Inspection Report INSP-NRB4-014."),
            ("para", "2. AFFECTED AREA: The portion of the Pier P5 pier shaft represented by "
                     "Test Set B, approximately the middle third of the shaft cross-section "
                     "by pour sequence, cast between 11:40 and 13:10 on 14-Feb-2022. Test "
                     "Sets A and C, covering the remainder of the same pour, are satisfactory "
                     "and are not affected by this NCR."),
            ("para", "3. INSTRUCTION: The Contractor shall, within 14 days: (a) investigate "
                     "and report the root cause of the non-conforming result; (b) propose and "
                     "carry out such additional testing as may be necessary to establish the "
                     "actual in-place strength of the affected concrete; and (c) not proceed "
                     "with further concrete pours directly bearing on the affected area of "
                     "the Pier P5 pier shaft until this NCR is closed."),
            ("para", "4. STATUS: OPEN."),
        ],
        closing_lines=["Signed: Engineer's Representative", "Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # Document 4 -- RCA-NRB4-003
    DocumentSpec(
        doc_id="RCA-NRB4-003",
        title="Contractor's Root Cause Analysis — NCR-NRB4-001",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="ROOT CAUSE ANALYSIS",
        letterhead="CONTRACTOR",
        date="01-Apr-2022",
        from_="Contractor, Quality Manager, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Root Cause Analysis — NCR-NRB4-001, Pier P5 Pier Shaft",
        body=[
            ("para", "In response to NCR-NRB4-001, we have investigated pour records, "
                     "batching records, curing records, and site photographs for the Pier P5 "
                     "pier shaft pour of 14-Feb-2022, and identify the following contributing "
                     "factors."),
            ("para", "1. CUBE CURING: The curing tank heater fault logged by the Engineer "
                     "between approximately 18-Feb-2022 and 04-Mar-2022 overlaps the first "
                     "9–14 days of curing for the 28-day cubes of this pour, including Test "
                     "Set B. Reduced curing temperature during this early period is capable "
                     "of measurably suppressing cube strength gain, particularly for "
                     "specimens cast later in a working day when ambient temperatures were "
                     "already falling, which applies to Test Set B (cast 11:40–13:10, the "
                     "warmest part of the day, with curing tank conditions affected shortly "
                     "after casting)."),
            ("para", "2. CUBE COMPACTION: Review of site photographs taken during "
                     "cube-making for this pour indicates the Set B cubes were compacted by a "
                     "relief technician standing in for the usual laboratory technician, who "
                     "was on approved leave that day. Compaction of these specific cubes "
                     "appears less thorough than the standard practice observed for Sets A "
                     "and C, consistent with minor entrapped air voids visible in the "
                     "photographs of the Set B specimens after de-moulding."),
            ("para", "3. IN-PLACE CONCRETE PLACEMENT: We have reviewed the pour record and "
                     "placement method statement for this pour. The affected portion of the "
                     "pour was placed and compacted by the standard placing crew using "
                     "immersion vibrators in accordance with the approved method statement, "
                     "in the same manner as the remainder of the pour. We have no record or "
                     "observation indicating that placement or compaction of the in-place "
                     "concrete itself differed for this portion of the pour."),
            ("para", "4. CONCLUSION: We consider it likely that the low Test Set B results "
                     "reflect deficiencies in the cube specimens themselves — curing and "
                     "compaction — rather than a deficiency in the in-place concrete. We "
                     "propose additional testing of the in-place concrete (core testing and "
                     "non-destructive testing) to verify this conclusion, as instructed under "
                     "NCR-NRB4-001."),
        ],
        closing_lines=["Submitted by: Quality Manager, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 5 -- LAB-NRB4-041
    DocumentSpec(
        doc_id="LAB-NRB4-041",
        title="Additional Test Report — Core Tests and Non-Destructive Testing, Pier P5 "
              "Pier Shaft",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="LABORATORY TEST REPORT",
        letterhead="THIRD_PARTY",
        letterhead_org_override="Suvarna Materials Testing Laboratory",
        date="12-Apr-2022",
        from_="Suvarna Materials Testing Laboratory",
        to="Meridian Engineering Consultants",
        cc="Sagara Constructions Pvt. Ltd.",
        subject="Core Test and Ultrasonic Pulse Velocity (UPV) Results — Pier P5 Pier Shaft, "
                "Affected Zone (Test Set B)",
        body=[
            ("para", "Testing carried out 05-Apr-2022 to 08-Apr-2022, in response to "
                     "NCR-NRB4-001 and Root Cause Analysis RCA-NRB4-003."),
            ("para", "1. CORE TESTS: Three cores extracted from the affected zone of the Pier "
                     "P5 pier shaft, length-to-diameter ratio 1.9 (correction factor 0.98 "
                     "applied per the Specification's referenced core testing standard)."),
            ("table", {
                "headers": ["Core", "Raw Strength (N/mm2)", "Corrected Strength (N/mm2)"],
                "rows": [
                    ["C-1", "39.0", "38.2"],
                    ["C-2", "38.7", "37.9"],
                    ["C-3", "40.2", "39.4"],
                    ["Average corrected core strength:", "", "38.5 N/mm2"],
                ],
                "right_align_cols": [1, 2],
                "bold_last_row": True,
            }),
            ("para", "ASSESSMENT: All three corrected core results exceed 85 per cent of the "
                     "specified characteristic strength (34.0 N/mm2), the criterion commonly "
                     "applied for assessing in-place concrete strength from core results, and "
                     "the average corrected strength approaches the specified characteristic "
                     "strength itself."),
            ("para", "2. ULTRASONIC PULSE VELOCITY (UPV) TESTING: UPV readings taken at 12 "
                     "points across the affected zone and adjacent unaffected areas for "
                     "comparison."),
            ("table", {
                "headers": ["Zone", "UPV Range (km/s)", "Average (km/s)", "Classification"],
                "rows": [
                    ["Affected (Set B)", "4.0 – 4.4", "4.2", "Good to Excellent"],
                    ["Adjacent (Set A/C)", "4.1 – 4.5", "4.3", "Good to Excellent"],
                ],
                "right_align_cols": [1, 2],
            }),
            ("para", "ASSESSMENT: UPV readings across the affected zone are consistent with "
                     "those in the unaffected zones and indicate dense, homogeneous concrete "
                     "with no significant voiding, honeycombing, or discontinuity."),
            ("para", "3. OVERALL CONCLUSION: Both the core test results and the UPV survey "
                     "indicate the in-place concrete in the affected zone is sound and meets "
                     "or closely approaches the specified characteristic strength, supporting "
                     "the Root Cause Analysis conclusion that the low Test Set B cube results "
                     "arose from deficiencies in the test specimens rather than the in-place "
                     "concrete."),
        ],
        closing_lines=["Issued by: Suvarna Materials Testing Laboratory"],
        scenario=SCENARIO,
    ),

    # Document 6 -- CTR-NRB4-0112
    DocumentSpec(
        doc_id="CTR-NRB4-0112",
        title="Corrective Action Proposal — NCR-NRB4-001",
        doc_type="CORRESPONDENCE",
        doc_type_tag="CORRECTIVE ACTION PROPOSAL",
        letterhead="CONTRACTOR",
        date="18-Apr-2022",
        from_="Contractor, Quality Manager, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Corrective Action Proposal — NCR-NRB4-001, Pier P5 Pier Shaft",
        body=[
            ("para", "Further to Root Cause Analysis RCA-NRB4-003 and Additional Test Report "
                     "LAB-NRB4-041, we propose the following corrective actions in respect of "
                     "NCR-NRB4-001:"),
            ("para", "1. STRUCTURAL ACCEPTANCE: We propose no demolition or reconstruction of "
                     "the affected portion of the Pier P5 pier shaft, on the basis that core "
                     "test results (average corrected strength 38.5 N/mm2, all individual "
                     "results exceeding 85 per cent of the specified characteristic strength) "
                     "and UPV survey results (consistent with adjacent unaffected zones) both "
                     "confirm the in-place concrete is sound and structurally adequate."),
            ("para", "2. PROCESS CORRECTIVE ACTIONS: (a) Cube curing tank temperature will be "
                     "logged continuously with an automated data logger, with an alarm for "
                     "any deviation, rather than relying on periodic manual checks; (b) Cube "
                     "compaction will be carried out only by laboratory technicians who have "
                     "completed the site's compaction competency assessment, with no "
                     "substitution by non-assessed personnel; a second, assessed technician "
                     "has been added to the laboratory team to provide cover for planned "
                     "absences; (c) A review of cube results for all pours since 01-Jan-2022 "
                     "has been carried out; no other test set shows a comparable shortfall."),
            ("para", "We request the Engineer's acceptance of these proposals and closure of "
                     "NCR-NRB4-001."),
        ],
        closing_lines=["Regards,", "Quality Manager", "Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 7 -- ENG-NRB4-0045
    DocumentSpec(
        doc_id="ENG-NRB4-0045",
        title="Engineer's Technical Assessment — NCR-NRB4-001",
        doc_type="APPROVAL",
        doc_type_tag="ENGINEER'S TECHNICAL ASSESSMENT",
        letterhead="ENGINEER",
        date="29-Apr-2022",
        from_="Engineer, Meridian Engineering Consultants",
        to="Contractor, Sagara Constructions Pvt. Ltd.",
        subject="Technical Assessment — NCR-NRB4-001, Pier P5 Pier Shaft",
        body=[
            ("para", "We have reviewed Root Cause Analysis RCA-NRB4-003, Additional Test "
                     "Report LAB-NRB4-041, and Corrective Action Proposal CTR-NRB4-0112 in "
                     "respect of NCR-NRB4-001."),
            ("para", "1. STRUCTURAL ADEQUACY: We accept the conclusion that the low Test Set "
                     "B cube results are attributable to deficiencies in the test specimens — "
                     "curing tank conditions during the logged heater fault period and "
                     "below-standard compaction of the specimens by a relief technician — "
                     "rather than to the in-place concrete. The core test results (average "
                     "corrected strength 38.5 N/mm2, individual results 37.9–39.4 N/mm2, all "
                     "exceeding the 34.0 N/mm2 threshold applied for in-place assessment) and "
                     "the UPV survey results (consistent with adjacent, unaffected concrete, "
                     "no indication of voiding or discontinuity) provide adequate direct "
                     "evidence of the in-place concrete's condition. We accept that the "
                     "affected portion of the Pier P5 pier shaft is structurally adequate and "
                     "that no demolition or reconstruction is required."),
            ("para", "2. CORRECTIVE ACTIONS: We accept the process corrective actions "
                     "proposed in CTR-NRB4-0112, subject to written confirmation from the "
                     "Contractor, within 14 days, that the automated curing tank temperature "
                     "logger referred to in item 2(a) has been installed and is operational."),
            ("para", "3. DETERMINATION: Subject to the confirmation in paragraph 2 above, we "
                     "are satisfied that NCR-NRB4-001 may be closed upon receipt of that "
                     "confirmation. This determination relates solely to the structural and "
                     "quality matters addressed in NCR-NRB4-001 and does not concern any "
                     "other matter, including the retention interpretation dispute addressed "
                     "separately under CTR-NRB4-0098."),
        ],
        closing_lines=["Signed: Engineer's Representative", "Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # Document 8 -- ENG-NRB4-0049
    DocumentSpec(
        doc_id="ENG-NRB4-0049",
        title="NCR Close-Out Notice — NCR-NRB4-001",
        doc_type="APPROVAL",
        doc_type_tag="NCR CLOSE-OUT NOTICE",
        letterhead="ENGINEER",
        date="06-May-2022",
        from_="Engineer, Meridian Engineering Consultants",
        to="Sagara Constructions Pvt. Ltd.",
        cc="National Highways Infrastructure Authority",
        subject="Close-Out — NCR-NRB4-001, Pier P5 Pier Shaft",
        body=[
            ("para", "We confirm receipt of the Contractor's written confirmation, dated "
                     "04-May-2022, that the automated curing tank temperature logger referred "
                     "to in our Technical Assessment ENG-NRB4-0045 has been installed and is "
                     "operational, and that the additional laboratory technician has "
                     "completed the compaction competency assessment referred to in "
                     "Corrective Action Proposal CTR-NRB4-0112."),
            ("para", "Having reviewed the full record — Cube Test Report LAB-NRB4-034, "
                     "Inspection Report INSP-NRB4-014, Root Cause Analysis RCA-NRB4-003, "
                     "Additional Test Report LAB-NRB4-041, Corrective Action Proposal "
                     "CTR-NRB4-0112, and Technical Assessment ENG-NRB4-0045 — we confirm:"),
            ("bullet", "The affected portion of the Pier P5 pier shaft is structurally "
                       "adequate; no demolition or reconstruction has been required."),
            ("bullet", "The accepted process corrective actions have been implemented."),
            ("total_box", "NCR-NRB4-001 is hereby CLOSED."),
        ],
        closing_lines=["Signed: Engineer's Representative", "Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),
]
