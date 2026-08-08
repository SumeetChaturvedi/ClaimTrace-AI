"""Verbatim structured data for Scenario 2's 8 approved documents.
Same transcription discipline as scenario_01_data.py: only inline
header-line -> metadata-box lifting and hand-wrapped-line -> paragraph
rejoining are applied; no wording is added, removed, or changed.
"""

from pdf_template import DocumentSpec

SCENARIO = 2

DOCUMENTS: list[DocumentSpec] = [

    # Document 1 -- CTR-NRB4-0052
    DocumentSpec(
        doc_id="CTR-NRB4-0052",
        title="Contractor's Supplementary Claim — Dispute of EOT-01 Assessment",
        doc_type="CLAIM",
        doc_type_tag="CONTRACTOR CLAIM",
        letterhead="CONTRACTOR",
        date="08-Oct-2021",
        from_="Contractor, Project Manager, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Supplementary Claim — Extension of Time — Pier P3 Utility Conflict — "
                "Dispute of Determination ENG-NRB4-0019",
        body=[
            ("para", "We refer to the Engineer's determination ENG-NRB4-0019 dated "
                     "25-Sep-2021, granting an extension of the Time for Completion of 10 "
                     "weeks in respect of the Pier P3 utility conflict addressed in our Notice "
                     "CTR-NRB4-0021 and detailed particulars CTR-NRB4-0028."),
            ("para", "We accept the Engineer's finding of entitlement under Sub-Clause 8.4(c). "
                     "However, we do not accept that 10 weeks reflects the true net critical "
                     "path impact of this event, for the following reason."),
            ("para", "ENG-NRB4-0019 credits the resequencing carried out under Site Instruction "
                     "SI-NRB4-014 with substantially mitigating the delay, on the basis that "
                     "works continued at Piers P1, P2, P4 and P5 while Pier P3 was suspended. "
                     "We submit that this mitigation was materially less effective than "
                     "assumed, because the resequenced works themselves fell substantially "
                     "within the Monsoon Period defined at Particular Conditions Part D.1 (1 "
                     "June to 30 September), during which our productivity at Piers P1, P2, P4 "
                     "and P5 was significantly reduced by sustained heavy rainfall, as recorded "
                     "in our Daily Progress Reports for the period and set out in the rainfall "
                     "data we are compiling separately for the Engineer's review."),
            ("para", "Had the mitigating works at Piers P1, P2, P4 and P5 proceeded at "
                     "dry-season productivity, a materially greater portion of the Pier P3 "
                     "suspension period would have been absorbed without programme impact. "
                     "Since that mitigation was itself constrained by monsoon conditions, we "
                     "submit that the net critical path delay attributable to the Pier P3 "
                     "utility conflict is understated in ENG-NRB4-0019, and we claim a further "
                     "extension of 6 weeks, in addition to the 10 weeks already granted, making "
                     "16 weeks in total."),
            ("para", "We will submit rainfall records and an updated programme analysis in "
                     "support of this claim within the coming weeks, and reserve our right to "
                     "supplement these particulars further."),
        ],
        closing_lines=["Regards,", "Project Manager", "Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 2 -- DPR-0614-2021
    DocumentSpec(
        doc_id="DPR-0614-2021",
        title="Daily Progress Report — Piers P1/P2, 14-Jun-2021",
        doc_type="PROGRESS_REPORT",
        doc_type_tag="DAILY PROGRESS REPORT",
        letterhead="CONTRACTOR",
        date="14-Jun-2021",
        from_="Site Engineer, Sagara Constructions Pvt. Ltd.",
        to="Engineer's Site Office (Meridian Engineering Consultants)",
        extra_meta=[("Location", "Piers P1, P2, P4, P5 — Nandira River Bridge Project — "
                                  "Package NRB-4")],
        body=[
            ("heading", "WORK CARRIED OUT TODAY:"),
            ("bullet", "Reinforcement fixing at Pier P2 pile cap halted at approximately 10:30 "
                       "due to heavy rainfall; resumed briefly in the afternoon before being "
                       "stopped again at 15:00. Approximately 4.5 hours lost."),
            ("bullet", "Formwork erection at Pier P4 continued in the morning session only; "
                       "afternoon session cancelled due to site access becoming unsafe "
                       "following rainfall."),
            ("bullet", "Routine inspection of the Pier P1 pile cap reinforcement carried out by "
                       "the Engineer's Representative ahead of the scheduled concrete pour, "
                       "Hold Point (b) per Employer's Requirements Section 11, cleared and "
                       "recorded in the Hold Point register."),
            ("bullet", "Delivery of precast parapet moulding samples received from approved "
                       "supplier for Engineer's review; stored at site compound."),
            ("bullet", "Rainfall recorded at site gauge: 58mm in the 24 hours to 08:00."),
            ("bullet", "Labour deployed: 22 general labourers, 3 supervisors (reduced from "
                       "planned 34 due to weather stoppage)."),
            ("heading", "REMARKS:"),
            ("para", "Works at Pier P3 remain suspended pending utility relocation (ref. "
                     "SI-NRB4-014, VPGC-NRB4-0012). Continuing to monitor productivity impact "
                     "of monsoon conditions on resequenced works at Piers P1, P2, P4 and P5."),
        ],
        closing_lines=["Reported by: Site Engineer, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 3 -- DPR-0722-2021
    DocumentSpec(
        doc_id="DPR-0722-2021",
        title="Daily Progress Report — Piers P2/P5, 22-Jul-2021",
        doc_type="PROGRESS_REPORT",
        doc_type_tag="DAILY PROGRESS REPORT",
        letterhead="CONTRACTOR",
        date="22-Jul-2021",
        from_="Site Engineer, Sagara Constructions Pvt. Ltd.",
        to="Engineer's Site Office (Meridian Engineering Consultants)",
        extra_meta=[("Location", "Piers P2, P5 — Nandira River Bridge Project — Package NRB-4")],
        body=[
            ("heading", "WORK CARRIED OUT TODAY:"),
            ("bullet", "Concrete pour for Pier P5 pile cap (approximately 42 cubic metres, "
                       "Grade M40) completed in the morning session ahead of the day's "
                       "rainfall, witnessed by the Engineer's Representative, Hold Point (d) "
                       "cleared. Pour record to follow under Employer's Requirements Section "
                       "14."),
            ("bullet", "Reinforcement fixing at Pier P2 pier shaft suspended from 13:00 due to "
                       "heavy rainfall; approximately 3 hours lost."),
            ("bullet", "Rainfall recorded at site gauge: 71mm in the 24 hours to 08:00, the "
                       "highest single-day total recorded at site to date this season."),
            ("bullet", "Site compound access road required regrading following surface water "
                       "accumulation; carried out by site plant, no impact on critical "
                       "activities."),
            ("bullet", "Procurement note: purchase order raised for the second batch of "
                       "precast deck girder segments, delivery scheduled for Q1 2022, unrelated "
                       "to current substructure activities."),
            ("bullet", "Labour deployed: 26 general labourers, 3 supervisors."),
            ("heading", "REMARKS:"),
            ("para", "Works at Pier P3 remain suspended pending utility relocation. Rainfall "
                     "this month continues to run above the seasonal average recorded in prior "
                     "years at this location, though no single day has approached the 100mm/24 "
                     "hour threshold referred to in Particular Conditions Part D.2."),
        ],
        closing_lines=["Reported by: Site Engineer, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 4 -- DPR-0830-2021
    DocumentSpec(
        doc_id="DPR-0830-2021",
        title="Daily Progress Report — Piers P1/P4, 30-Aug-2021",
        doc_type="PROGRESS_REPORT",
        doc_type_tag="DAILY PROGRESS REPORT",
        letterhead="CONTRACTOR",
        date="30-Aug-2021",
        from_="Site Engineer, Sagara Constructions Pvt. Ltd.",
        to="Engineer's Site Office (Meridian Engineering Consultants)",
        extra_meta=[("Location", "Piers P1, P4 — Nandira River Bridge Project — Package NRB-4")],
        body=[
            ("heading", "WORK CARRIED OUT TODAY:"),
            ("bullet", "Formwork and falsework erection at Pier P4 pier shaft continued through "
                       "the day; productivity reduced by intermittent rainfall through the "
                       "afternoon, approximately 2 hours lost."),
            ("bullet", "Pier P1 approach drainage works progressed as planned, no weather "
                       "impact."),
            ("bullet", "Site safety induction conducted for two new equipment operators "
                       "joining the Contractor's team, unrelated to current claim matters."),
            ("bullet", "Rainfall recorded at site gauge: 64mm in the 24 hours to 08:00."),
            ("bullet", "Labour deployed: 30 general labourers, 4 supervisors."),
            ("heading", "REMARKS:"),
            ("para", "Works at Pier P3 remain suspended pending utility relocation, now "
                     "approaching its estimated completion per VPGC-NRB4-0012. Cumulative "
                     "monsoon-season productivity impact at Piers P1, P2, P4 and P5 being "
                     "compiled for submission to the Engineer."),
        ],
        closing_lines=["Reported by: Site Engineer, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 5 -- MET-NRB4-2021-03
    DocumentSpec(
        doc_id="MET-NRB4-2021-03",
        title="Site Rainfall Report — Monsoon Season 2021 (June–September)",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="TECHNICAL REPORT — RAINFALL DATA",
        letterhead="CONTRACTOR",
        date="05-Oct-2021",
        from_="Site Engineer, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Site Rainfall Record — Monsoon Period 2021, in Support of Claim CTR-NRB4-0052",
        body=[
            ("para", "In support of our supplementary claim CTR-NRB4-0052 dated 08-Oct-2021, "
                     "we submit the following consolidated rainfall data recorded at the site "
                     "rain gauge, cross-checked against the Suvarna District Meteorological "
                     "Station's published records for the Monsoon Period defined at Particular "
                     "Conditions Part D.1 (1 June to 30 September 2021)."),
            ("subheading", "MONTHLY SUMMARY:"),
            ("table", {
                "headers": ["Month", "Total Rainfall", "Rain-Days (>10mm)", "Peak 24hr Rainfall"],
                "rows": [
                    ["June 2021", "412mm", "14", "58mm (14-Jun-2021)"],
                    ["July 2021", "486mm", "17", "71mm (22-Jul-2021)"],
                    ["August 2021", "398mm", "13", "64mm (30-Aug-2021)"],
                    ["September 2021", "301mm", "10", "52mm (03-Sep-2021)"],
                    ["TOTAL", "1,597mm", "54", "71mm"],
                ],
                "right_align_cols": [1, 2, 3],
                "bold_last_row": True,
            }),
            ("para", "For comparison, the five-year average total rainfall for the same period "
                     "at this location, per the Suvarna District Meteorological Station's "
                     "published records, is approximately 1,180mm. The 2021 monsoon season "
                     "therefore recorded approximately 35 per cent above the five-year seasonal "
                     "average, with a materially higher number of rain-days than typical."),
            ("para", "We note for completeness that no single 24-hour period during the season "
                     "reached the 100mm threshold referred to in Particular Conditions Part "
                     "D.2; the highest recorded 24-hour total was 71mm, on 22-Jul-2021 "
                     "(DPR-0722-2021). This report accordingly does not assert an Adverse "
                     "Weather Event under Part D.2, and is submitted solely in support of the "
                     "productivity-impact argument made in Claim CTR-NRB4-0052."),
        ],
        closing_lines=["Compiled by: Site Engineer, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 6 -- PGM-NRB4-Rev04
    DocumentSpec(
        doc_id="PGM-NRB4-Rev04",
        title="Programme Update Rev. 04 — Critical Path Analysis, Pier P3 Delay Period",
        doc_type="PROGRAMME",
        doc_type_tag="PROGRAMME UPDATE",
        letterhead="CONTRACTOR",
        date="15-Oct-2021",
        from_="Planning Engineer, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Programme Update Revision 04 — Critical Path Analysis in Support of Claim "
                "CTR-NRB4-0052",
        body=[
            ("para", "This programme update revises the critical path analysis previously "
                     "reflected in the Contractor's programme as at determination "
                     "ENG-NRB4-0019, in support of our supplementary claim CTR-NRB4-0052."),
            ("para", "1. PERIOD ANALYSED: 28-Jan-2021 (suspension of Pier P3 works, per "
                     "DPR-0128-2021) to 10-Sep-2021 (utility relocation complete, per "
                     "VPGC-NRB4-0045)."),
            ("para", "2. MITIGATION ASSUMED IN ENG-NRB4-0019: That substructure works at Piers "
                     "P1, P2, P4 and P5, resequenced under SI-NRB4-014, would absorb the "
                     "majority of the Pier P3 suspension without residual critical path "
                     "impact, netting to a 10-week extension."),
            ("para", "3. REVISED ANALYSIS: Cross-referencing productivity records in "
                     "DPR-0614-2021, DPR-0722-2021 and DPR-0830-2021 against planned output "
                     "rates for Piers P1, P2, P4 and P5, we assess that monsoon-season "
                     "productivity on the mitigating works averaged approximately 74 per cent "
                     "of planned output across June to September 2021, against the rainfall "
                     "data set out in report MET-NRB4-2021-03. On this basis, the mitigating "
                     "works absorbed less of the Pier P3 suspension than assumed in "
                     "ENG-NRB4-0019, and our revised critical path analysis indicates a net "
                     "delay to Substantial Completion of 16 weeks attributable to the Pier P3 "
                     "event, rather than the 10 weeks previously determined."),
            ("para", "4. BASIS OF ENTITLEMENT: We maintain that the additional 6 weeks arises "
                     "from the same Sub-Clause 8.4(c) event as EOT-01 and is not an "
                     "independent claim for monsoon delay under Particular Conditions Part "
                     "D.1, which we accept is not independently compensable."),
            ("para", "This programme update is submitted for the Engineer's review in "
                     "accordance with Sub-Clause 8.4 and does not itself constitute a fresh "
                     "notice under Sub-Clause 20.1."),
        ],
        closing_lines=["Prepared by: Planning Engineer, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 7 -- MOM-NRB4-021
    DocumentSpec(
        doc_id="MOM-NRB4-021",
        title="Minutes of Monthly Progress Meeting No. 21",
        doc_type="MEETING_MINUTES",
        doc_type_tag="PROGRESS MEETING MINUTES",
        letterhead="ENGINEER",
        date="20-Oct-2021",
        from_="Resident Engineer, Meridian Engineering Consultants",
        to="Distribution list — Employer, Engineer, Contractor",
        extra_meta=[
            ("Meeting", "Monthly Progress Meeting No. 21"),
            ("Venue", "NRB-4 Site Office, Left Bank Approach"),
            ("Present", "Er. Anand Vasker (Resident Engineer, Meridian Engineering "
                        "Consultants); Project Manager and Planning Engineer (Sagara "
                        "Constructions Pvt. Ltd.); Project Representative (National Highways "
                        "Infrastructure Authority)"),
        ],
        body=[
            ("para", "Issued in accordance with Particular Conditions Part B.2, within 5 "
                     "working days of the meeting."),
            ("heading", "1. PREVIOUS MINUTES:"),
            ("para", "Minutes of Meeting No. 20 confirmed without amendment."),
            ("heading", "2. PROGRESS SUMMARY:"),
            ("para", "Superstructure works at Piers P1 and P2 approximately 82 per cent "
                     "complete. Girder erection at Pier P4 scheduled to commence November "
                     "2021, subject to receipt of the second precast girder segment batch "
                     "(procurement note, DPR-0722-2021). Pier P3 substructure works resumed "
                     "13-Sep-2021 following handback of the area by Vantara Power Grid "
                     "Corporation (VPGC-NRB4-0045); excavation re-commenced 15-Sep-2021."),
            ("heading", "3. CONTRACTOR'S SUPPLEMENTARY CLAIM (CTR-NRB4-0052):"),
            ("para", "The Contractor summarised its supplementary claim disputing "
                     "determination ENG-NRB4-0019, referring to rainfall report "
                     "MET-NRB4-2021-03 and programme update PGM-NRB4-Rev04. The Engineer noted "
                     "receipt and confirmed the claim would be assessed and responded to "
                     "formally in accordance with Sub-Clause 20.1, separately from these "
                     "minutes. The Employer's representative reserved the Employer's position "
                     "pending the Engineer's determination."),
            ("heading", "4. PERFORMANCE SECURITY AND RETENTION:"),
            ("para", "No matters arising."),
            ("heading", "5. HEALTH AND SAFETY:"),
            ("para", "No lost-time incidents reported for the period."),
            ("heading", "6. OTHER BUSINESS:"),
            ("para", "Contractor confirmed submission of updated Inspection and Test Plan for "
                     "superstructure concrete works, per Employer's Requirements Section 10, "
                     "for the Engineer's review."),
            ("heading", "7. NEXT MEETING:"),
            ("para", "Scheduled for 20-Nov-2021."),
        ],
        closing_lines=["Minutes recorded by: Resident Engineer, Meridian Engineering "
                       "Consultants"],
        scenario=SCENARIO,
    ),

    # Document 8 -- ENG-NRB4-0024
    DocumentSpec(
        doc_id="ENG-NRB4-0024",
        title="Engineer's Determination — Supplementary Claim CTR-NRB4-0052",
        doc_type="APPROVAL",
        doc_type_tag="ENGINEER'S DETERMINATION",
        letterhead="ENGINEER",
        date="05-Nov-2021",
        from_="Engineer, Meridian Engineering Consultants",
        to="Contractor, Sagara Constructions Pvt. Ltd.",
        subject="Determination — Supplementary Claim CTR-NRB4-0052 — Pier P3 Utility Conflict",
        body=[
            ("para", "We refer to your supplementary claim CTR-NRB4-0052 dated 08-Oct-2021, "
                     "rainfall report MET-NRB4-2021-03 dated 05-Oct-2021, and programme update "
                     "PGM-NRB4-Rev04 dated 15-Oct-2021, seeking an additional extension of 6 "
                     "weeks beyond the 10 weeks granted under our determination ENG-NRB4-0019 "
                     "dated 25-Sep-2021, on the basis that monsoon conditions reduced the "
                     "effectiveness of the mitigating works at Piers P1, P2, P4 and P5."),
            ("para", "Having reviewed the particulars submitted, we make the following "
                     "determination:"),
            ("para", "1. RAINFALL DATA: We accept that the 2021 monsoon season, as recorded in "
                     "MET-NRB4-2021-03, was heavier than the five-year average for this "
                     "location. We note, and the Contractor's own report confirms, that no "
                     "24-hour period during the season met the 100mm threshold for an Adverse "
                     "Weather Event under Particular Conditions Part D.2. The season "
                     "accordingly falls within the ordinary Monsoon Period defined at "
                     "Particular Conditions Part D.1, which is expressly not independently "
                     "compensable."),
            ("para", "2. CONCURRENT DELAY: The reduced productivity at Piers P1, P2, P4 and P5 "
                     "during June to September 2021 arose from ordinary seasonal conditions "
                     "that would have affected those works, and the Contractor's programme "
                     "generally, regardless of whether the Pier P3 event had occurred. A risk "
                     "allocated to the Contractor under Part D.1 does not become compensable "
                     "merely because it coincides in time with, or reduces the effectiveness "
                     "of mitigation for, a separate compensable event. The two causes are "
                     "concurrent but distinct, and only the delay genuinely attributable to "
                     "the Sub-Clause 8.4(c) event — the Pier P3 utility conflict — falls to be "
                     "assessed under that Sub-Clause."),
            ("para", "3. REASSESSMENT: We have reviewed the critical path analysis in "
                     "PGM-NRB4-Rev04 against our own analysis underlying ENG-NRB4-0019 and "
                     "find no basis to revise the net delay attributable to the Pier P3 event. "
                     "The 10-week extension determined in ENG-NRB4-0019 remains our assessment "
                     "of the Contractor's entitlement under Sub-Clause 8.4(c) and is not "
                     "increased by this determination."),
            ("para", "4. DETERMINATION: The supplementary claim for a further 6-week extension "
                     "is rejected. The extension of the Time for Completion of 10 weeks "
                     "granted under ENG-NRB4-0019 stands, and the revised Time for Completion "
                     "notified in that determination is unchanged."),
            ("para", "This determination is issued under Sub-Clause 20.1 and relates solely to "
                     "the matters raised in CTR-NRB4-0052."),
        ],
        closing_lines=["Signed: Engineer's Representative", "Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),
]
