"""Structured data for the 14 Scenario 11 documents — Concrete Defects
During the Defects Notification Period, Pier P2 Pier Cap, Nandira River
Bridge Project (Package NRB-4).

Continues the existing Dataset V2 corpus (Scenarios 1-10, project_id=2).
This scenario occurs after Practical Completion: the Taking-Over
Certificate (TOC-NRB4-001, Scenario 9) was issued 22-Sep-2023, establishing
a Defects Notification Period of 365 days per Contract Data Section 3,
running 22-Sep-2023 to 21-Sep-2024. Every document in this scenario is
dated within that window (14-Feb-2024 to 05-Aug-2024), so it does not
interact with, and cannot contradict, any Scenario 1-10 document, all of
which are dated on or before 22-Sep-2023 (Scenario 10's own events, though
numbered after Scenario 9, occur chronologically earlier, 07-Feb-2023 to
24-Mar-2023, inside the existing corpus's documented "quiet" period).

Location: the top surface of the Pier P2 pier cap (beneath the bearing
plinths), cast 11-Aug-2021 during the period of resequenced substructure
works at Piers P1, P2, P4 and P5 instructed under Site Instruction
SI-NRB4-014 (Scenario 1) following the Pier P3 utility conflict suspension
-- reusing an already-established fact rather than re-deriving it. Pier P2
was inspected without adverse comment during the Taking-Over inspection
(Engineer's Inspection Notes EIN-NRB4-001 and Joint Inspection Report
JIR-NRB4-001, Scenario 9, both dated Sep-2023, record "no structural
cracking, spalling, or other defect observed at any pier or span"); this
scenario's cracking is deliberately written as a defect that manifests
later, from progressive early-age shrinkage, consistent with (not
contradicting) that earlier clean inspection.

Two facts already established by existing documents are reused rather than
re-derived: (1) SI-NRB4-014 places Pier P2 substructure work in mid-to-late
2021, before Pier P3 resumed following EOT-01 (Engineer's Determination
ENG-NRB4-0019, 25-Sep-2021, Scenario 1); (2) Contract Data Section 3
already states the Defects Notification Period is 365 days from the
Taking-Over Certificate date, and TOC-NRB4-001 already states it expires
21-Sep-2024 -- this scenario's rectification and close-out (05-Aug-2024)
completes with time to spare before that expiry, so it does not affect, and
is not affected by, the Performance Certificate that will fall due at DNP
expiry.

This scenario also relies on Sub-Clauses 11.1 and 11.2, added by a new
addendum, NRB4-GC-2020-ADD02.txt (see that file's own docstring context for
why: the existing General Conditions extract has no Clause 11 at all, only
a gap in the numbering, and the Engineer's liability/cost determination in
this scenario requires quoted contractual text to be contractually
grounded, exactly as Sub-Clause 4.12 was added by ADD01 for Scenario 10).
"""

from pdf_template import DocumentSpec

SCENARIO = 11

DOCUMENTS: list[DocumentSpec] = [

    # ------------------------------------------------------------------
    # Document 1 -- DIR-NRB4-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="DIR-NRB4-001",
        title="Defect Inspection Report — Routine Defects Notification Period Inspection, "
              "Pier P2 Pier Cap",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="DEFECT INSPECTION REPORT",
        letterhead="ENGINEER",
        date="14-Feb-2024",
        from_="QA Engineer, Meridian Engineering Consultants",
        to="Resident Engineer (Er. Anand Vasker), copied to project file",
        extra_meta=[("Location", "Pier P2, Nandira River Bridge Project — Package NRB-4")],
        subject="Routine Defects Notification Period Inspection — Pier P2 Pier Cap",
        body=[
            ("para", "This report records the findings of a routine Defects Notification "
                     "Period inspection carried out 13-Feb-2024, forming part of the "
                     "programme of periodic inspections during the Defects Notification "
                     "Period established by Contract Data Section 3 (365 days from the "
                     "Taking-Over Certificate, 22-Sep-2023 to 21-Sep-2024)."),
            ("heading", "FINDINGS:"),
            ("bullet", "Map (crazing) cracking observed across approximately 60 per cent of "
                       "the exposed top surface of the Pier P2 pier cap, beneath and around "
                       "the bearing plinths. Crack widths estimated by visual inspection at "
                       "between 0.1mm and 0.5mm, in an irregular, interconnected pattern "
                       "typical of surface shrinkage cracking, not of a single dominant crack "
                       "or a pattern radiating from a point load."),
            ("bullet", "No cracking of comparable extent observed on the vertical faces of "
                       "the Pier P2 pier shaft below the cap, or on the pier cap soffit."),
            ("bullet", "No spalling, exposed reinforcement, rust staining, or efflorescence "
                       "observed at any crack. No cracking observed at the bearing plinths "
                       "themselves or at the bearing seating surfaces."),
            ("bullet", "This condition was not present, or not of this extent, when Pier P2 "
                       "was last formally inspected during the Taking-Over inspection "
                       "(Engineer's Inspection Notes EIN-NRB4-001, 09-Sep-2023), which recorded "
                       "no structural cracking at any pier."),
            ("heading", "PRELIMINARY ASSESSMENT:"),
            ("para", "The pattern, distribution, and shallow appearance of the cracking are "
                     "consistent with surface (plastic or early-age drying shrinkage) "
                     "cracking rather than a structural or load-related defect. No immediate "
                     "safety concern is identified. Given the extent of the cracking, this "
                     "should be formally notified to the Contractor under the Defects "
                     "Liability provisions of the Contract for investigation and, if "
                     "confirmed, remedial action within the Defects Notification Period."),
            ("heading", "OTHER SITE OBSERVATIONS TODAY:"),
            ("bullet", "Piers P1, P3, P4, P5, P6, P7 and both abutments visually inspected; no "
                       "comparable cracking or other new defect observed at any other "
                       "location."),
            ("bullet", "Outstanding Works Register OWR-NRB4-001 items 1-4 (Scenario 9 punch "
                       "list) confirmed closed out during previous inspections; not revisited "
                       "today."),
        ],
        closing_lines=["Reported by: QA Engineer, Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 2 -- ENG-NRB4-0078
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="ENG-NRB4-0078",
        title="Engineer's Defect Notice — Cracking, Pier P2 Pier Cap",
        doc_type="NOTICE",
        doc_type_tag="DEFECT NOTICE",
        letterhead="ENGINEER",
        date="20-Feb-2024",
        from_="Engineer, Meridian Engineering Consultants",
        to="Contractor, Sagara Constructions Pvt. Ltd.",
        subject="Defect Notice — Map Cracking, Pier P2 Pier Cap",
        body=[
            ("para", "Pursuant to Sub-Clause 11.1, we give notice of a defect identified "
                     "during a routine Defects Notification Period inspection on 13-Feb-2024, "
                     "recorded in Defect Inspection Report DIR-NRB4-001: map (crazing) "
                     "cracking, crack widths estimated between 0.1mm and 0.5mm, across "
                     "approximately 60 per cent of the exposed top surface of the Pier P2 "
                     "pier cap."),
            ("para", "This condition was not recorded during the Taking-Over inspection "
                     "(Engineer's Inspection Notes EIN-NRB4-001, 09-Sep-2023), which found no "
                     "structural cracking at any pier. We consider this defect has become "
                     "apparent within the Defects Notification Period established by Contract "
                     "Data Section 3, which expires 21-Sep-2024."),
            ("para", "In accordance with Sub-Clause 11.1, the Contractor is instructed to: "
                     "(a) investigate and report the root cause of the cracking within 21 "
                     "days of this notice; (b) carry out such further investigation, mapping "
                     "and testing as may be necessary to establish the extent, depth, and "
                     "cause of the cracking, engaging an independent testing laboratory for "
                     "this purpose; and (c) not undertake any remedial work at Pier P2 pending "
                     "the Engineer's instruction under Sub-Clause 11.1."),
            ("para", "We reserve our position under Sub-Clause 11.2 as to the cause of, and "
                     "liability for the cost of remedying, this defect, pending the outcome of "
                     "the investigation."),
        ],
        closing_lines=["Regards,", "Engineer", "Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 3 -- CTR-NRB4-0162
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="CTR-NRB4-0162",
        title="Contractor's Initial Response — Defect Notice ENG-NRB4-0078",
        doc_type="CORRESPONDENCE",
        doc_type_tag="CORRESPONDENCE",
        letterhead="CONTRACTOR",
        date="04-Mar-2024",
        from_="Contractor, Quality Manager, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Initial Response — Defect Notice ENG-NRB4-0078, Pier P2 Pier Cap",
        body=[
            ("para", "We acknowledge Defect Notice ENG-NRB4-0078 dated 20-Feb-2024 and confirm "
                     "we will investigate the cracking reported at the Pier P2 pier cap in "
                     "accordance with Sub-Clause 11.1, and will not undertake remedial work "
                     "pending the Engineer's instruction."),
            ("para", "Our preliminary, without-prejudice view, based on a site walk carried "
                     "out 01-Mar-2024, is that the cracking is consistent with plastic or "
                     "early-age drying shrinkage arising from the ambient conditions "
                     "prevailing at the time of the pour on 11-Aug-2021, a period of elevated "
                     "daytime temperatures on Site, and is not attributable to any deficiency "
                     "in materials or workmanship. We note the concrete mix used for this pour "
                     "was the same approved Grade M40 mix design used successfully across all "
                     "other substructure elements on the Works."),
            ("para", "We propose to engage Suvarna Materials Testing Laboratory, the "
                     "independent testing laboratory already nominated by the Engineer for "
                     "the Works, to carry out crack mapping, core testing, and non-destructive "
                     "testing to establish the extent and cause of the cracking, and will "
                     "report our root cause analysis in accordance with the timetable in "
                     "ENG-NRB4-0078."),
            ("para", "We reserve our position as to liability for the cost of any remedial "
                     "work pending that investigation."),
        ],
        closing_lines=["Regards,", "Quality Manager", "Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 4 -- SIR-NRB4-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="SIR-NRB4-001",
        title="Joint Site Inspection Record — Pier P2 Pier Cap Cracking",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="JOINT SITE INSPECTION RECORD",
        letterhead="JOINT",
        date="08-Mar-2024",
        from_="Meridian Engineering Consultants, jointly with Sagara Constructions Pvt. Ltd.",
        to="Project file",
        extra_meta=[
            ("Participants", "Er. Anand Vasker (Resident Engineer, Meridian Engineering "
                             "Consultants); Quality Manager (Sagara Constructions Pvt. Ltd.); "
                             "Field Technician (Suvarna Materials Testing Laboratory)"),
        ],
        subject="Joint Site Inspection Record — Pier P2 Pier Cap",
        body=[
            ("para", "Joint site inspection carried out 07-Mar-2024 to establish a common "
                     "record of the cracking reported in Defect Inspection Report "
                     "DIR-NRB4-001 before further testing, and to agree the scope of the "
                     "investigation proposed in CTR-NRB4-0162."),
            ("heading", "AGREED OBSERVATIONS:"),
            ("bullet", "Cracking confirmed present across the top surface of the pier cap as "
                       "described in DIR-NRB4-001, with the densest concentration in the "
                       "central portion of the cap, tapering toward the cap edges."),
            ("bullet", "No cracking observed on the pier shaft, pier cap soffit, or at the "
                       "bearing seating surfaces, confirmed by both Parties."),
            ("bullet", "A reference grid (1m x 1m) was marked on the pier cap top surface to "
                       "allow the testing laboratory to record crack locations, widths and "
                       "orientations systematically for the Crack Mapping Report."),
            ("bullet", "Both Parties agreed the scope of further testing: full crack mapping "
                       "survey; three cores for compressive strength and petrographic "
                       "examination; ultrasonic pulse velocity (UPV) survey; and review of "
                       "the pour record and Site diary for the 11-Aug-2021 pour, to be carried "
                       "out by Suvarna Materials Testing Laboratory."),
            ("bullet", "The Contractor's Quality Manager confirmed the original pour record "
                       "and Site diary entries for 11-Aug-2021 to 18-Aug-2021 would be located "
                       "and provided to the Engineer and the testing laboratory within 5 "
                       "working days."),
            ("para", "This record is agreed as an accurate account of the joint inspection by "
                     "both Parties present."),
        ],
        closing_lines=["Signed jointly by: Meridian Engineering Consultants and Sagara "
                       "Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 5 -- CMR-NRB4-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="CMR-NRB4-001",
        title="Crack Mapping Report — Pier P2 Pier Cap",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="CRACK MAPPING REPORT",
        letterhead="THIRD_PARTY",
        letterhead_org_override="Suvarna Materials Testing Laboratory",
        date="15-Mar-2024",
        from_="Suvarna Materials Testing Laboratory",
        to="Meridian Engineering Consultants",
        cc="Sagara Constructions Pvt. Ltd.",
        subject="Crack Mapping Survey — Pier P2 Pier Cap Top Surface",
        body=[
            ("para", "Crack mapping survey carried out 11-Mar-2024, against the 1m x 1m "
                     "reference grid established in Joint Site Inspection Record "
                     "SIR-NRB4-001."),
            ("heading", "SURVEY RESULTS:"),
            ("table", {
                "headers": ["Zone", "Crack Density", "Width Range", "Pattern"],
                "rows": [
                    ["Central (grid C3-D5)", "High — interconnected", "0.2mm – 0.5mm", "Map/crazing"],
                    ["Intermediate (grid B2-B6, E2-E6)", "Moderate", "0.1mm – 0.3mm", "Map/crazing"],
                    ["Edge (grid A1-A7, F1-F7)", "Low, isolated cracks only", "0.1mm – 0.15mm", "Isolated fine"],
                ],
            }),
            ("para", "1. PATTERN: The cracking forms an irregular, interconnected map (or "
                     "'crazing') pattern, with no dominant single crack, no radial pattern "
                     "consistent with a point load, and no orientation aligned with the "
                     "reinforcement layout drawings reviewed for this survey. Crack density "
                     "decreases from the centre of the pour toward its edges."),
            ("para", "2. EXTENT: Cracking is confined to the top surface of the pier cap. No "
                     "crack was traced to the pier cap soffit or the vertical faces of the "
                     "pier shaft during this survey."),
            ("para", "3. ASSESSMENT: This pattern, density gradient, and confinement to the "
                     "top (exposed) surface are characteristic of surface shrinkage cracking "
                     "(plastic or early-age drying shrinkage), rather than structural or "
                     "load-induced cracking, which would typically show a different "
                     "orientation and would not be confined to a single exposed surface. Depth "
                     "of cracking to be confirmed by core testing and petrographic examination, "
                     "reported separately."),
        ],
        closing_lines=["Issued by: Suvarna Materials Testing Laboratory"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 6 -- LAB-NRB4-058
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="LAB-NRB4-058",
        title="Laboratory Test Report — Core Tests, UPV Survey and Petrographic Analysis, "
              "Pier P2 Pier Cap",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="LABORATORY TEST REPORT",
        letterhead="THIRD_PARTY",
        letterhead_org_override="Suvarna Materials Testing Laboratory",
        date="29-Mar-2024",
        from_="Suvarna Materials Testing Laboratory",
        to="Meridian Engineering Consultants",
        cc="Sagara Constructions Pvt. Ltd.",
        subject="Core Tests, UPV Survey and Petrographic Analysis — Pier P2 Pier Cap",
        body=[
            ("para", "Testing carried out 18-Mar-2024 to 26-Mar-2024, per the scope agreed in "
                     "Joint Site Inspection Record SIR-NRB4-001 and following the Crack "
                     "Mapping Report CMR-NRB4-001."),
            ("heading", "1. CORE TESTS (COMPRESSIVE STRENGTH):"),
            ("para", "Three cores extracted from the central (highest crack density) zone of "
                     "the pier cap, length-to-diameter ratio 2.0 (no correction factor "
                     "required). Specified characteristic strength: 40 N/mm2 at 28 days "
                     "(Grade M40, per Employer's Requirements Section 5)."),
            ("table", {
                "headers": ["Core", "Raw Strength (N/mm2)", "Corrected Strength (N/mm2)"],
                "rows": [
                    ["C-1", "44.6", "44.6"],
                    ["C-2", "43.1", "43.1"],
                    ["C-3", "45.0", "45.0"],
                    ["Average corrected core strength:", "", "44.2 N/mm2"],
                ],
                "right_align_cols": [1, 2],
                "bold_last_row": True,
            }),
            ("para", "ASSESSMENT: All three results exceed the specified characteristic "
                     "strength; the concrete's bulk compressive strength is not implicated in "
                     "the cracking."),
            ("heading", "2. ULTRASONIC PULSE VELOCITY (UPV) SURVEY:"),
            ("table", {
                "headers": ["Zone", "UPV Range (km/s)", "Average (km/s)", "Classification"],
                "rows": [
                    ["Central (cracked)", "4.2 – 4.5", "4.3", "Good to Excellent"],
                    ["Edge (uncracked)", "4.2 – 4.6", "4.4", "Good to Excellent"],
                ],
                "right_align_cols": [1, 2],
            }),
            ("para", "ASSESSMENT: UPV readings in the cracked central zone are consistent "
                     "with the uncracked edge zone, indicating dense, homogeneous concrete "
                     "below the surface, with no significant internal voiding or "
                     "discontinuity attributable to the cracking."),
            ("heading", "3. PETROGRAPHIC EXAMINATION:"),
            ("para", "Thin sections prepared from Core C-1 (through a representative surface "
                     "crack) examined under polarising microscope."),
            ("bullet", "Crack depth measured at 12mm to 19mm from the top surface across the "
                       "three sections examined; no crack observed to extend below "
                       "approximately 20mm depth in any section."),
            ("bullet", "No evidence of alkali-silica reaction (ASR) gel, sulfate attack "
                       "products, or delayed ettringite formation at or adjacent to any crack "
                       "examined."),
            ("bullet", "Aggregate distribution, paste microstructure, and air content of the "
                       "bulk concrete below the cracked zone are consistent with a properly "
                       "proportioned and compacted Grade M40 mix; no evidence of segregation, "
                       "excess water content, or abnormal aggregate reaction."),
            ("bullet", "Carbonation depth measured at 2mm to 3mm, consistent with normal "
                       "carbonation for concrete of this age and exposure; no evidence of "
                       "reinforcement corrosion or corrosion-induced cracking (cracks do not "
                       "align with, or extend to, the cover to reinforcement, measured at "
                       "45mm to 50mm at the locations examined, in accordance with the "
                       "Specification)."),
            ("heading", "4. OVERALL CONCLUSION:"),
            ("para", "The cracking is shallow (confined to approximately the top 20mm of the "
                     "pier cap), is not associated with any deficiency in the bulk concrete's "
                     "strength, density, or composition, and is not associated with "
                     "alkali-silica reaction, sulfate attack, or reinforcement corrosion. "
                     "These findings are consistent with surface (plastic or early-age "
                     "drying shrinkage) cracking, most commonly associated with insufficient "
                     "curing of the exposed surface in the days immediately following "
                     "placement, rather than with a deficiency in the concrete mix, the "
                     "in-place placement or compaction of the concrete, or the structural "
                     "design. We were not instructed to, and have not, reviewed curing "
                     "records for this pour, which fall outside the scope of this laboratory "
                     "testing."),
        ],
        closing_lines=["Issued by: Suvarna Materials Testing Laboratory"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 7 -- RCA-NRB4-004
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="RCA-NRB4-004",
        title="Contractor's Root Cause Analysis — Pier P2 Pier Cap Cracking",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="ROOT CAUSE ANALYSIS",
        letterhead="CONTRACTOR",
        date="12-Apr-2024",
        from_="Contractor, Quality Manager, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Root Cause Analysis — Pier P2 Pier Cap Cracking",
        body=[
            ("para", "Further to Defect Notice ENG-NRB4-0078, and having reviewed Crack "
                     "Mapping Report CMR-NRB4-001, Laboratory Test Report LAB-NRB4-058, and "
                     "our own pour record and Site diary for the pour of 11-Aug-2021, we "
                     "report the following root cause analysis."),
            ("para", "1. WEATHER RECORDS: Site weather records for 11-Aug-2021 show a maximum "
                     "ambient temperature of 33.5 degrees C, within the range recorded at "
                     "other substructure pours completed successfully during the same "
                     "period, including the Pier P4 and Pier P5 pier caps (32-35 degrees C "
                     "range, per pour records reviewed). We do not consider ambient "
                     "temperature on the day of the pour to have been exceptional or a "
                     "material contributing cause."),
            ("para", "2. MIX DESIGN AND MATERIALS: The pour used the same approved Grade M40 "
                     "mix design, from the same approved concrete source, as used across all "
                     "other substructure elements on the Works, including Piers P1, P4 and "
                     "P5, none of which exhibits comparable cracking. Petrographic "
                     "examination in LAB-NRB4-058 found no abnormality in the mix. We do not "
                     "consider the mix design or materials to be a contributing cause."),
            ("para", "3. CURING RECORDS: Review of the Site diary for this pour identifies "
                     "that the curing membrane and wet hessian cover specified for the "
                     "exposed top surface were removed on 14-Aug-2021, approximately 3 days "
                     "after the pour, to allow formwork for the bearing plinths to proceed "
                     "ahead of programme, against a 7-day minimum curing period for exposed "
                     "surfaces under the Specification. We have not identified a corresponding "
                     "curing record for any other substructure pour on the Works showing an "
                     "equivalent shortfall."),
            ("para", "4. CONCLUSION: Having reviewed the alternative causes, we consider it "
                     "more likely than not that the early removal of curing protection "
                     "identified in paragraph 3 above is the principal contributing cause of "
                     "the cracking, resulting in accelerated early-age drying shrinkage of the "
                     "exposed top surface before the concrete had gained sufficient tensile "
                     "strength to resist the resulting stresses. We accept this is a departure "
                     "from the curing period required by the Specification."),
        ],
        closing_lines=["Submitted by: Quality Manager, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 8 -- MOM-NRB4-031
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="MOM-NRB4-031",
        title="Minutes of Meeting — Defects Notification Period Review, Pier P2 Pier Cap",
        doc_type="MEETING_MINUTES",
        doc_type_tag="DNP REVIEW MEETING MINUTES",
        letterhead="ENGINEER",
        date="18-Apr-2024",
        from_="Resident Engineer, Meridian Engineering Consultants",
        to="Distribution list — Employer, Engineer, Contractor",
        extra_meta=[
            ("Meeting", "Defects Notification Period Review Meeting No. 1 — Pier P2 Pier Cap"),
            ("Venue", "NRB-4 Site Office, Left Bank Approach"),
            ("Present", "Er. Anand Vasker (Resident Engineer, Meridian Engineering "
                        "Consultants); Quality Manager (Sagara Constructions Pvt. Ltd.); "
                        "Project Representative (National Highways Infrastructure "
                        "Authority)"),
        ],
        body=[
            ("para", "This meeting was convened to review the investigation into the Pier P2 "
                     "pier cap cracking notified under ENG-NRB4-0078, in accordance with "
                     "Sub-Clause 11.1."),
            ("heading", "ITEM 1 — REVIEW OF INVESTIGATION FINDINGS"),
            ("para", "The Engineer summarised Crack Mapping Report CMR-NRB4-001 and "
                     "Laboratory Test Report LAB-NRB4-058, confirming the cracking is "
                     "shallow, confined to the top 20mm of the pier cap, not associated with "
                     "the bulk concrete strength or composition, and not associated with "
                     "alkali-silica reaction, sulfate attack, or reinforcement corrosion."),
            ("para", "The Contractor presented Root Cause Analysis RCA-NRB4-004, confirming "
                     "ambient conditions and mix design/materials are not considered "
                     "contributing causes, and identifying early removal of curing "
                     "protection (removed after approximately 3 days against a 7-day "
                     "Specification requirement) as the principal contributing cause."),
            ("heading", "ITEM 2 — LIABILITY"),
            ("para", "The Resident Engineer noted that, on the basis of RCA-NRB4-004's own "
                     "findings, the cracking appears attributable to workmanship not in "
                     "accordance with the Specification's curing requirements, which would "
                     "engage Sub-Clause 11.2, and that the Engineer would issue a formal "
                     "determination under that Sub-Clause. The Contractor did not dispute the "
                     "curing record finding itself, but reserved its position as to whether "
                     "that finding is sufficient, on its own, to establish liability under "
                     "Sub-Clause 11.2."),
            ("heading", "ITEM 3 — NEXT STEPS"),
            ("para", "The Engineer to issue a determination under Sub-Clause 11.2 addressing "
                     "root cause and liability, following which, if the cracking is "
                     "determined to require remedial work, an instruction for rectification "
                     "will be issued under Sub-Clause 11.1."),
        ],
        closing_lines=["Minutes issued by: Resident Engineer, Meridian Engineering "
                       "Consultants"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 9 -- ENG-NRB4-0083
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="ENG-NRB4-0083",
        title="Engineer's Determination — Root Cause and Liability, Pier P2 Pier Cap "
              "Cracking",
        doc_type="APPROVAL",
        doc_type_tag="ENGINEER'S DETERMINATION",
        letterhead="ENGINEER",
        date="06-May-2024",
        from_="Engineer, Meridian Engineering Consultants",
        to="Contractor, Sagara Constructions Pvt. Ltd.",
        subject="Determination Under Sub-Clause 11.2 — Pier P2 Pier Cap Cracking",
        body=[
            ("para", "We refer to Defect Notice ENG-NRB4-0078 dated 20-Feb-2024, Crack "
                     "Mapping Report CMR-NRB4-001, Laboratory Test Report LAB-NRB4-058, "
                     "Contractor's Root Cause Analysis RCA-NRB4-004, and Minutes of Meeting "
                     "MOM-NRB4-031, concerning the map cracking identified at the Pier P2 "
                     "pier cap."),
            ("para", "Having reviewed the particulars submitted, we make the following "
                     "determination under Sub-Clause 11.2:"),
            ("para", "1. NATURE OF DEFECT: The cracking is confirmed, by Laboratory Test "
                     "Report LAB-NRB4-058, to be shallow surface (plastic or early-age drying "
                     "shrinkage) cracking, confined to approximately the top 20mm of the pier "
                     "cap. The bulk concrete meets the specified characteristic strength "
                     "(average corrected core strength 44.2 N/mm2 against 40 N/mm2 "
                     "specified), and no alkali-silica reaction, sulfate attack, or "
                     "reinforcement corrosion is present."),
            ("para", "2. CAUSES EXCLUDED: We accept, on the evidence in LAB-NRB4-058 and "
                     "RCA-NRB4-004, that this defect is not attributable to design, to the "
                     "concrete mix or materials used, or to the ambient conditions prevailing "
                     "at the time of the pour, each of which is excluded as a material "
                     "contributing cause for the reasons set out in those reports."),
            ("para", "3. CAUSE ACCEPTED: RCA-NRB4-004 records, and the Contractor did not "
                     "dispute at the meeting recorded in MOM-NRB4-031, that the curing "
                     "membrane and wet hessian cover for the exposed top surface of this pour "
                     "were removed on 14-Aug-2021, approximately 3 days after placement, "
                     "against the 7-day minimum curing period required by the Specification "
                     "for exposed surfaces. We accept this finding, and consider it, on the "
                     "balance of the evidence, the cause of the cracking: the shallow depth "
                     "of the cracking (confined to the top 20mm) and its confinement to the "
                     "exposed top surface only, with no equivalent cracking on the pier shaft "
                     "or pier cap soffit, are each consistent with a curing-related cause and "
                     "not with any of the causes excluded in paragraph 2."),
            ("para", "4. LIABILITY: The failure to maintain curing protection for the period "
                     "required by the Specification is workmanship not in accordance with the "
                     "Contract within the meaning of Sub-Clause 11.2(b), and is not fair wear "
                     "and tear. The Contractor is accordingly liable under Sub-Clause 11.2 for "
                     "the cost of remedying this defect, and is not entitled to any additional "
                     "payment or extension of time in respect of it."),
            ("para", "5. NEXT STEPS: We will separately issue an instruction under Sub-Clause "
                     "11.1 for the rectification of the cracking, having regard to the "
                     "Contractor's proposed method."),
        ],
        closing_lines=["Signed: Engineer's Representative", "Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 10 -- CTR-NRB4-0169
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="CTR-NRB4-0169",
        title="Contractor's Objection — Determination ENG-NRB4-0083",
        doc_type="CORRESPONDENCE",
        doc_type_tag="CORRESPONDENCE",
        letterhead="CONTRACTOR",
        date="20-May-2024",
        from_="Contractor, Project Manager, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Objection — Determination ENG-NRB4-0083, Pier P2 Pier Cap Cracking",
        body=[
            ("para", "We refer to the Engineer's determination ENG-NRB4-0083 dated "
                     "06-May-2024, finding the Contractor liable under Sub-Clause 11.2 for "
                     "the cost of remedying the Pier P2 pier cap cracking."),
            ("para", "We do not dispute the curing record identified in our own Root Cause "
                     "Analysis RCA-NRB4-004, nor the exclusion of design, materials and "
                     "ambient conditions as contributing causes. We submit, however, that a "
                     "shortfall in curing duration measured in days, on a single pour among "
                     "many completed successfully across the Works, is not, without further "
                     "direct evidence linking that specific shortfall to this specific "
                     "cracking (as opposed to a general association between curing shortfalls "
                     "and shrinkage cracking of this type), sufficient to discharge the "
                     "Engineer's burden of establishing the cause of the defect to the "
                     "standard required by Sub-Clause 11.2."),
            ("para", "We do not consider it commercially proportionate to escalate this "
                     "matter further given the modest scope of the remedial work involved, "
                     "and will proceed to rectify the cracking in accordance with any "
                     "instruction issued under Sub-Clause 11.1, without prejudice to, and "
                     "expressly reserving, our position that liability for the cost of that "
                     "work has not been established to the standard required by Sub-Clause "
                     "11.2."),
        ],
        closing_lines=["Regards,", "Project Manager", "Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 11 -- SI-NRB4-031
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="SI-NRB4-031",
        title="Site Instruction SI-NRB4-031 — Rectification of Cracking, Pier P2 Pier Cap",
        doc_type="SITE_INSTRUCTION",
        doc_type_tag="SITE INSTRUCTION",
        letterhead="ENGINEER",
        date="27-May-2024",
        from_="Engineer (on behalf of Employer), per Er. Anand Vasker, Resident Engineer, "
              "acting within the delegation recorded under Particular Conditions Part B.1",
        to="Contractor, Sagara Constructions Pvt. Ltd.",
        extra_meta=[("Project", "Nandira River Bridge Project — Package NRB-4")],
        body=[
            ("heading", "INSTRUCTION:"),
            ("para", "Further to Determination ENG-NRB4-0083 dated 06-May-2024 and noting "
                     "the Contractor's objection CTR-NRB4-0169, the Contractor is instructed, "
                     "pursuant to Sub-Clause 11.1, to rectify the map cracking at the Pier P2 "
                     "pier cap as follows:"),
            ("para", "1. All cracks mapped in Crack Mapping Report CMR-NRB4-001 with a width "
                     "of 0.2mm or greater shall be sealed by low-viscosity epoxy resin "
                     "injection, in accordance with a method statement to be submitted for "
                     "the Engineer's review under Employer's Requirements Section 16 before "
                     "work commences."),
            ("para", "2. Cracks of width less than 0.2mm, being within the range generally "
                     "considered self-sealing for concrete of this exposure class, shall be "
                     "treated by application of a penetrating, breathable surface sealer "
                     "across the full extent of the affected top surface, following "
                     "completion of the injection works in paragraph 1."),
            ("para", "3. On completion, the Contractor shall submit a Rectification "
                     "Completion Report, including a re-survey of the treated area against "
                     "the reference grid established in SIR-NRB4-001, for the Engineer's "
                     "review and acceptance."),
            ("para", "This instruction is issued without prejudice to Determination "
                     "ENG-NRB4-0083 and to the Contractor's reservation of position recorded "
                     "in CTR-NRB4-0169; the cost of the work instructed above is for the "
                     "Contractor's own account in accordance with that Determination, subject "
                     "to any right the Contractor may have to pursue that reservation further "
                     "under the Contract."),
        ],
        closing_lines=["Signed: Er. Anand Vasker, Resident Engineer"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 12 -- MST-NRB4-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="MST-NRB4-001",
        title="Method Statement — Crack Injection Repair, Pier P2 Pier Cap",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="METHOD STATEMENT",
        letterhead="CONTRACTOR",
        date="10-Jun-2024",
        from_="Contractor, Quality Manager, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Method Statement Submitted Under SI-NRB4-031 — Pier P2 Pier Cap",
        body=[
            ("heading", "SCOPE:"),
            ("para", "Low-viscosity epoxy resin injection of all cracks 0.2mm and greater "
                     "identified in Crack Mapping Report CMR-NRB4-001 (approximately 45 "
                     "linear metres of crack, concentrated in grid zones B2-E6), followed by "
                     "application of a penetrating, breathable surface sealer across the full "
                     "top surface of the pier cap, in accordance with Site Instruction "
                     "SI-NRB4-031."),
            ("heading", "SEQUENCE OF WORK:"),
            ("bullet", "1. Surface preparation: cleaning and degreasing of all crack lines "
                       "and surrounding surface by low-pressure water wash and air drying."),
            ("bullet", "2. Injection port installation at 150mm centres along each crack line "
                       "0.2mm or greater, surface-sealed with epoxy paste pending injection."),
            ("bullet", "3. Low-viscosity epoxy resin injection under controlled pressure, "
                       "working from the lowest port upward along each crack line, until "
                       "resin return is observed at the adjacent port."),
            ("bullet", "4. Minimum 48-hour cure before port removal and surface grinding "
                       "flush."),
            ("bullet", "5. Application of penetrating, breathable surface sealer across the "
                       "full top surface, in two coats, following manufacturer's recoat "
                       "interval."),
            ("bullet", "6. Re-survey of the treated area against the SIR-NRB4-001 reference "
                       "grid, and preparation of the Rectification Completion Report."),
            ("heading", "MATERIALS:"),
            ("para", "Structural epoxy injection resin and surface sealer, both proprietary "
                     "products with manufacturer's technical data sheets and third-party "
                     "test certification confirming suitability for structural crack "
                     "injection and exposed concrete surfaces respectively, to be submitted "
                     "with product samples for the Engineer's review before procurement."),
            ("heading", "QUALITY CONTROL:"),
            ("para", "Injection pressure and resin consumption per linear metre to be logged "
                     "for each crack line. A minimum of 3 no. injected sections will be "
                     "selected at random by the Engineer for verification coring after cure, "
                     "to confirm full resin penetration through the crack depth."),
        ],
        closing_lines=["Submitted by: Quality Manager, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 13 -- RCR-NRB4-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="RCR-NRB4-001",
        title="Rectification Completion Report — Pier P2 Pier Cap",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="RECTIFICATION COMPLETION REPORT",
        letterhead="CONTRACTOR",
        date="22-Jul-2024",
        from_="Contractor, Quality Manager, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Rectification Completion Report — Pier P2 Pier Cap, Under SI-NRB4-031",
        body=[
            ("para", "This report confirms completion of the rectification works instructed "
                     "under Site Instruction SI-NRB4-031, carried out 17-Jun-2024 to "
                     "12-Jul-2024 in accordance with Method Statement MST-NRB4-001."),
            ("heading", "WORK COMPLETED:"),
            ("bullet", "48 linear metres of crack (0.2mm and greater) injected with "
                       "low-viscosity epoxy resin, across grid zones B2-E6, in accordance "
                       "with MST-NRB4-001."),
            ("bullet", "Penetrating, breathable surface sealer applied in two coats across "
                       "the full top surface of the pier cap."),
            ("bullet", "3 verification cores taken at randomly selected injected sections "
                       "(grid C3, D4, C5) on 15-Jul-2024, witnessed by the Resident Engineer; "
                       "all 3 confirmed full resin penetration through the crack depth, with "
                       "no voiding observed within the injected crack in any core."),
            ("bullet", "Re-survey against the SIR-NRB4-001 reference grid carried out "
                       "18-Jul-2024: no crack of width 0.2mm or greater remains visible on "
                       "the treated surface; isolated fine cracking below 0.15mm remains "
                       "visible beneath the surface sealer at a small number of locations in "
                       "the former edge zone (grid A1-A7, F1-F7), consistent with the "
                       "self-sealing cracks excluded from injection under SI-NRB4-031 and not "
                       "affecting the sealer's continuity."),
            ("heading", "RECORDS:"),
            ("para", "Injection pressure and resin consumption logs, verification core "
                     "photographs and test results, and the post-treatment survey record are "
                     "enclosed for the Engineer's review."),
            ("para", "We request the Engineer's inspection and acceptance of the completed "
                     "rectification works."),
        ],
        closing_lines=["Submitted by: Quality Manager, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 14 -- EAC-NRB4-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="EAC-NRB4-001",
        title="Engineer's Acceptance Certificate — Rectification of Cracking, Pier P2 Pier "
              "Cap",
        doc_type="APPROVAL",
        doc_type_tag="CERTIFICATE",
        letterhead="ENGINEER",
        date="05-Aug-2024",
        from_="Engineer, Meridian Engineering Consultants",
        to="Sagara Constructions Pvt. Ltd.",
        cc="National Highways Infrastructure Authority",
        subject="Acceptance Certificate — Rectification of Cracking, Pier P2 Pier Cap",
        body=[
            ("para", "We refer to Rectification Completion Report RCR-NRB4-001 dated "
                     "22-Jul-2024, reporting completion of the rectification works "
                     "instructed under Site Instruction SI-NRB4-031."),
            ("para", "1. INSPECTION: The Resident Engineer inspected the treated surface on "
                     "25-Jul-2024, witnessed the verification coring results reported in "
                     "RCR-NRB4-001, and reviewed the post-treatment survey record."),
            ("bullet", "No crack of width 0.2mm or greater remains visible on the treated "
                       "surface. The isolated fine cracking below 0.15mm noted in RCR-NRB4-001 "
                       "at the former edge zone is accepted as within the self-sealing range "
                       "excluded from injection under SI-NRB4-031 and does not affect this "
                       "acceptance."),
            ("bullet", "Verification coring confirms full resin penetration through the crack "
                       "depth at all 3 sections tested, with no voiding."),
            ("para", "2. ACCEPTANCE: The rectification works instructed under SI-NRB4-031 are "
                     "accepted as complete and in accordance with the instruction and Method "
                     "Statement MST-NRB4-001."),
            ("para", "3. COST AND LIABILITY: In accordance with Determination ENG-NRB4-0083, "
                     "the cost of this rectification work is for the Contractor's own account. "
                     "This acceptance does not itself resolve the reservation of position "
                     "recorded in the Contractor's correspondence CTR-NRB4-0169, which remains "
                     "a matter between the Parties should the Contractor elect to pursue it "
                     "further under the Contract."),
            ("para", "4. DEFECTS NOTIFICATION PERIOD: This matter is closed for the purposes "
                     "of Sub-Clause 11.1. The Defects Notification Period, expiring "
                     "21-Sep-2024 per Contract Data Section 3, is otherwise unaffected by this "
                     "matter, and this acceptance does not itself constitute or affect the "
                     "Performance Certificate to be considered separately at expiry of that "
                     "Period."),
            ("total_box", "Rectification of the Pier P2 pier cap cracking is hereby ACCEPTED."),
        ],
        closing_lines=["Signed: Engineer's Representative", "Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),
]
