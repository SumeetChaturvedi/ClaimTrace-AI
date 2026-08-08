"""Structured data for the 14 Scenario 10 documents — Concurrent Delay,
Pier P4 supplementary piling, Nandira River Bridge Project (Package NRB-4).

Continues the existing Dataset V2 corpus (Scenarios 1-9, project_id=2).
Events are placed in the documented "quiet" period of the existing corpus
timeline (after ENG-NRB4-0052 / WPR-NRB4-023, 08-Aug-2022 / 29-Jul-2022,
and before CTR-NRB4-0198, 05-Sep-2023 -- see ingestion_report.json), so
this scenario's own events do not need to interact with, and cannot
contradict, any Scenario 1-9 document. All party names, addresses, and
contract references (NHIA/NRB4/CW/2020-01, Sub-Clause numbers, Particular
Conditions Parts) match those already established in
backend/storage/contracts/*.txt and scenario_01-09_data.py verbatim.

Two facts already established by existing documents are deliberately reused
here rather than re-derived: (1) SI-NRB4-014 (Scenario 1) instructed the
Contractor to resequence and prioritise substructure works at Piers P1, P2,
P4 and P5 during the 2021 Pier P3 suspension, establishing that Pier P4
substructure work was well under way by that year -- this scenario's
supplementary piling at Pier P4 in November 2022 is realistically a later
stage of that same pier's construction, not a contradiction of it. (2) The
Employer's Requirements (NRB4-ER-2020), Section 6, already states: "Where
ground conditions encountered during piling differ from those indicated in
the geotechnical information provided with the tender documents, the
Contractor shall notify the Engineer promptly and shall not proceed with
the affected foundation until the Engineer has reviewed the matter." This
scenario's ground-condition documents are written to trigger, and comply
with, that existing obligation directly.
"""

from pdf_template import DocumentSpec

SCENARIO = 10

DOCUMENTS: list[DocumentSpec] = [

    # ------------------------------------------------------------------
    # Document 1 -- DPR-1103-2022
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="DPR-1103-2022",
        title="Daily Progress Report — Pier P4 Supplementary Piling, 03-Nov-2022",
        doc_type="PROGRESS_REPORT",
        doc_type_tag="DAILY PROGRESS REPORT",
        letterhead="CONTRACTOR",
        date="03-Nov-2022",
        from_="Site Engineer, Sagara Constructions Pvt. Ltd.",
        to="Engineer's Site Office (Meridian Engineering Consultants)",
        extra_meta=[("Location", "Pier P4, Nandira River Bridge Project — Package NRB-4")],
        body=[
            ("heading", "WORK CARRIED OUT TODAY:"),
            ("bullet", "Continued rotary boring for the supplementary pile group at Pier P4 "
                       "(pile positions P4-N3 to P4-N6), instructed following the Engineer's "
                       "foundation capacity review of September 2022."),
            ("bullet", "Boring at pile position P4-N4 reached a depth of approximately 18.2m "
                       "when a marked change in drilling response was noted, together with "
                       "arisings consistent with a soft, compressible clay stratum, not "
                       "consistent with the founding stratum indicated in the geotechnical "
                       "information provided with the tender documents at this location."),
            ("bullet", "Boring at pile position P4-N4 suspended as a precaution pending further "
                       "investigation. Boring continued at pile positions P4-N3, P4-N5 and "
                       "P4-N6."),
            ("bullet", "Labour deployed: 11 general labourers, 1 piling rig operator (Rig PR-2), "
                       "1 supervisor."),
            ("bullet", "Weather: Clear."),
            ("heading", "REMARKS:"),
            ("para", "Arisings retained for inspection and sampling. Site Engineer to notify "
                     "the Engineer formally in accordance with Section 6 of the Employer's "
                     "Requirements and Sub-Clause 4.12 of the Conditions of Contract, and to "
                     "arrange a geotechnical investigation of pile position P4-N4 and the "
                     "surrounding pile group."),
        ],
        closing_lines=["Reported by: Site Engineer, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 2 -- EQR-NRB4-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="EQR-NRB4-001",
        title="Plant Breakdown Report — Piling Rig PR-2, Pier P4",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="PLANT BREAKDOWN REPORT",
        letterhead="CONTRACTOR",
        date="07-Nov-2022",
        from_="Plant Engineer, Sagara Constructions Pvt. Ltd.",
        to="Project Manager, Sagara Constructions Pvt. Ltd.",
        cc="Engineer, Meridian Engineering Consultants (for information)",
        subject="Breakdown of Piling Rig PR-2 During Boring at Pier P4, Pile Position P4-N5",
        body=[
            ("para", "This report records the breakdown of Piling Rig PR-2 (rotary bored "
                     "piling rig, fleet no. PR-2) during continued boring operations for the "
                     "Pier P4 supplementary pile group."),
            ("heading", "EVENT:"),
            ("para", "At approximately 09:40 on 07-Nov-2022, while boring pile position P4-N5, "
                     "Rig PR-2's hydraulic power pack experienced a sudden loss of drive "
                     "pressure. Boring was stopped immediately and the rig withdrawn from the "
                     "pile position."),
            ("heading", "FINDINGS:"),
            ("para", "Inspection by the rig manufacturer's authorised service technician on "
                     "08-Nov-2022 identified a failed main hydraulic pump drive coupling. The "
                     "failure is assessed as a mechanical fatigue failure of the coupling "
                     "itself, unrelated to ground conditions encountered at either pile "
                     "position P4-N4 or P4-N5."),
            ("heading", "REMEDIAL ACTION:"),
            ("para", "A replacement coupling assembly is not held in Site stores and must be "
                     "sourced from the manufacturer's regional depot. On the basis of the "
                     "manufacturer's advice, we estimate the rig will be out of service for "
                     "approximately 3 weeks from the date of failure, pending delivery and "
                     "fitting of the replacement assembly."),
            ("para", "No other piling rig on Site is configured for the socket diameter "
                     "required at Pier P4, and mobilising a substitute rig of the required "
                     "specification from outside the Site is not considered practicable within "
                     "the anticipated repair period."),
        ],
        closing_lines=["Prepared by: Plant Engineer, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 3 -- CTR-NRB4-0125
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="CTR-NRB4-0125",
        title="Notice of Delay — Unforeseen Ground Condition at Pier P4",
        doc_type="NOTICE",
        doc_type_tag="NOTICE",
        letterhead="CONTRACTOR",
        date="09-Nov-2022",
        from_="Contractor, Project Manager, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Notice of Delay — Unforeseen Ground Condition, Pier P4 Supplementary Pile "
                "Group",
        body=[
            ("para", "We write further to Daily Progress Report DPR-1103-2022, recording that "
                     "boring at pile position P4-N4, within the Pier P4 supplementary pile "
                     "group, encountered a soft, compressible clay stratum at approximately "
                     "18.2m depth, inconsistent with the founding stratum indicated in the "
                     "geotechnical information provided with the tender documents at this "
                     "location."),
            ("para", "Pursuant to Sub-Clause 20.1 and Sub-Clause 4.12 of the Conditions of "
                     "Contract, we hereby give notice that this event constitutes a cause of "
                     "delay for which we consider the Contractor entitled to an extension of "
                     "the Time for Completion under Sub-Clause 8.4(b), the condition "
                     "encountered being a physical condition which we consider could not "
                     "reasonably have been foreseen having regard to the geotechnical "
                     "information provided with the tender documents."),
            ("para", "In accordance with Sub-Clause 4.12, boring has continued at the "
                     "unaffected pile positions within the group; pile position P4-N4 remains "
                     "suspended pending the Engineer's review. We are keeping contemporaneous "
                     "records of the resulting impact on our programme and will submit fully "
                     "detailed particulars within 42 days of this notice, in accordance with "
                     "Sub-Clause 20.1."),
            ("para", "We reserve our rights to claim an extension of time and any associated "
                     "cost consequences arising from this event."),
        ],
        closing_lines=["Regards,", "Project Manager", "Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 4 -- CTR-NRB4-0131
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="CTR-NRB4-0131",
        title="Notice of Delay — Plant Breakdown, Piling Rig PR-2",
        doc_type="CORRESPONDENCE",
        doc_type_tag="CORRESPONDENCE",
        letterhead="CONTRACTOR",
        date="10-Nov-2022",
        from_="Contractor, Project Manager, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Notification of Plant Breakdown — Piling Rig PR-2, Pier P4",
        body=[
            ("para", "For the Engineer's information and for the purposes of the Contract "
                     "record, we confirm that Piling Rig PR-2 suffered a hydraulic drive "
                     "coupling failure on 07-Nov-2022 while boring pile position P4-N5 within "
                     "the Pier P4 supplementary pile group, as more fully described in our "
                     "Plant Breakdown Report EQR-NRB4-001."),
            ("para", "The rig is expected to be out of service for approximately 3 weeks. We "
                     "do not consider this event to fall within any of the causes described at "
                     "Sub-Clause 8.4, and no extension of time or additional payment is claimed "
                     "in respect of it. We record it here solely so that its effect on progress "
                     "at Pier P4 is not conflated with the separate ground condition addressed "
                     "in our Notice CTR-NRB4-0125 of 09-Nov-2022."),
            ("para", "We will keep the Engineer informed of the rig's return to service."),
        ],
        closing_lines=["Regards,", "Project Manager", "Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 5 -- GEO-NRB4-004
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="GEO-NRB4-004",
        title="Geotechnical Investigation Report — Pier P4 Supplementary Pile Group",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="GEOTECHNICAL INVESTIGATION REPORT",
        letterhead="ENGINEER",
        date="16-Nov-2022",
        from_="Geotechnical Section, Meridian Engineering Consultants",
        to="Contractor, Sagara Constructions Pvt. Ltd.",
        cc="Employer, National Highways Infrastructure Authority (for information)",
        subject="Geotechnical Investigation — Pile Position P4-N4 and Surrounding Pile Group, "
                "Pier P4",
        body=[
            ("para", "Further to Notice CTR-NRB4-0125 dated 09-Nov-2022, we report the findings "
                     "of a supplementary geotechnical investigation carried out at pile "
                     "position P4-N4 and the surrounding pile group between 10-Nov-2022 and "
                     "15-Nov-2022, comprising one rotary core borehole adjacent to P4-N4 and "
                     "review of arisings retained from pile positions P4-N3, P4-N5 and P4-N6."),
            ("heading", "FINDINGS:"),
            ("para", "The borehole confirms a lens of soft, compressible clay between "
                     "approximately 17.6m and 21.4m depth beneath pile position P4-N4, "
                     "underlain by the dense sandy gravel stratum shown as the founding stratum "
                     "in the geotechnical information provided with the tender documents. No "
                     "equivalent lens was encountered in the arisings from pile positions "
                     "P4-N3, P4-N5 or P4-N6, indicating the condition is localised to the "
                     "immediate vicinity of P4-N4."),
            ("para", "The geotechnical information provided with the tender documents does not "
                     "show, or reasonably indicate the presence of, a compressible stratum in "
                     "this vicinity. In our assessment, the condition encountered at pile "
                     "position P4-N4 could not reasonably have been anticipated by an "
                     "experienced contractor from that information."),
            ("heading", "RECOMMENDATION:"),
            ("para", "Pile position P4-N4 cannot achieve the design founding criteria at its "
                     "originally specified socket depth. We recommend the pile socket at this "
                     "position be extended by approximately 3.5m, founding within the "
                     "underlying dense sandy gravel stratum, together with a corresponding "
                     "increase in reinforcement cage length. A revised pile schedule for "
                     "position P4-N4 is enclosed for the Engineer's instruction."),
        ],
        closing_lines=["Prepared by: Geotechnical Section, Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 6 -- SI-NRB4-027
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="SI-NRB4-027",
        title="Site Instruction SI-NRB4-027 — Redesign of Pile Position P4-N4",
        doc_type="SITE_INSTRUCTION",
        doc_type_tag="SITE INSTRUCTION",
        letterhead="ENGINEER",
        date="22-Nov-2022",
        from_="Engineer (on behalf of Employer), per Er. Anand Vasker, Resident Engineer, "
              "acting within the delegation recorded under Particular Conditions Part B.1",
        to="Contractor, Sagara Constructions Pvt. Ltd.",
        extra_meta=[("Project", "Nandira River Bridge Project — Package NRB-4")],
        body=[
            ("heading", "INSTRUCTION:"),
            ("para", "Further to Geotechnical Investigation Report GEO-NRB4-004 dated "
                     "16-Nov-2022, concerning the soft clay lens encountered at pile position "
                     "P4-N4, the Contractor is instructed as follows:"),
            ("para", "1. Pile position P4-N4 shall be bored to a revised socket depth extending "
                     "approximately 3.5m beyond that shown on the original pile schedule, "
                     "founding within the dense sandy gravel stratum identified in "
                     "GEO-NRB4-004, in accordance with the revised pile schedule enclosed with "
                     "that report."),
            ("para", "2. The reinforcement cage for pile position P4-N4 shall be extended to "
                     "match the revised socket depth, in accordance with the enclosed revised "
                     "schedule."),
            ("para", "3. Boring and construction of pile positions P4-N3, P4-N5 and P4-N6 may "
                     "proceed to the original pile schedule, no equivalent condition having "
                     "been found at those positions."),
            ("para", "This instruction is issued without prejudice to any entitlement to "
                     "extension of time or additional cost the Contractor may have under "
                     "Sub-Clause 8.4, Sub-Clause 4.12 or Sub-Clause 20.1 in respect of the "
                     "ground condition encountered at pile position P4-N4, which remains under "
                     "the Engineer's consideration."),
        ],
        closing_lines=["Signed: Er. Anand Vasker, Resident Engineer"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 7 -- DPR-1130-2022
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="DPR-1130-2022",
        title="Daily Progress Report — Pier P4 Supplementary Piling, 30-Nov-2022",
        doc_type="PROGRESS_REPORT",
        doc_type_tag="DAILY PROGRESS REPORT",
        letterhead="CONTRACTOR",
        date="30-Nov-2022",
        from_="Site Engineer, Sagara Constructions Pvt. Ltd.",
        to="Engineer's Site Office (Meridian Engineering Consultants)",
        extra_meta=[("Location", "Pier P4, Nandira River Bridge Project — Package NRB-4")],
        body=[
            ("heading", "WORK CARRIED OUT TODAY:"),
            ("bullet", "Piling Rig PR-2 returned to service today following completion of "
                       "repairs recorded in Plant Breakdown Report EQR-NRB4-001; rig "
                       "recommissioned and function-tested with no issues noted."),
            ("bullet", "Boring resumed at pile position P4-N4 to the revised socket depth "
                       "instructed under Site Instruction SI-NRB4-027."),
            ("bullet", "Pile positions P4-N3, P4-N5 and P4-N6 completed to the original pile "
                       "schedule during the period Rig PR-2 was out of service, using the "
                       "Contractor's second piling rig (Rig PR-1), redeployed from approach "
                       "works for this purpose."),
            ("bullet", "Labour deployed: 12 general labourers, 2 piling rig operators, 1 "
                       "supervisor."),
            ("bullet", "Weather: Clear."),
            ("heading", "REMARKS:"),
            ("para", "With Rig PR-2 back in service and the revised design instructed, boring "
                     "at pile position P4-N4 is expected to be completed within "
                     "approximately two weeks, subject to no further ground anomalies."),
        ],
        closing_lines=["Reported by: Site Engineer, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 8 -- PGM-NRB4-Rev09
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="PGM-NRB4-Rev09",
        title="Programme Update Rev. 09 — Pier P4 Supplementary Piling Delay Period",
        doc_type="PROGRAMME",
        doc_type_tag="PROGRAMME UPDATE",
        letterhead="CONTRACTOR",
        date="05-Dec-2022",
        from_="Planning Engineer, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Programme Update Revision 09 — Pier P4 Supplementary Pile Group",
        body=[
            ("para", "This programme update reflects progress on the Pier P4 supplementary "
                     "pile group following the ground condition addressed in Notice "
                     "CTR-NRB4-0125 and the plant breakdown addressed in Notice CTR-NRB4-0131."),
            ("heading", "SUMMARY OF PERIOD:"),
            ("table", {
                "headers": ["Event", "Affected Position(s)", "Start", "End", "Duration"],
                "rows": [
                    ["Ground condition (ongoing)", "P4-N4", "03-Nov-2022", "15-Dec-2022 (est.)", "6 weeks"],
                    ["Plant breakdown (Rig PR-2)", "P4-N5 (then P4-N4)", "07-Nov-2022", "28-Nov-2022", "3 weeks"],
                ],
            }),
            ("para", "Pile positions P4-N3, P4-N5 and P4-N6 were completed by 30-Nov-2022 using "
                     "Rig PR-1, redeployed from approach works. Pile position P4-N4, the "
                     "critical-path item for completion of the Pier P4 supplementary pile "
                     "group and pile cap works following it, remains in progress to the "
                     "revised design under SI-NRB4-027, with completion of boring anticipated "
                     "by approximately 15-Dec-2022."),
            ("para", "This update is submitted for the Engineer's information in accordance "
                     "with Sub-Clause 8.4 and does not itself constitute a claim submission."),
        ],
        closing_lines=["Prepared by: Planning Engineer, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 9 -- MOM-NRB4-030
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="MOM-NRB4-030",
        title="Minutes of Monthly Progress Meeting No. 30",
        doc_type="MEETING_MINUTES",
        doc_type_tag="PROGRESS MEETING MINUTES",
        letterhead="ENGINEER",
        date="08-Dec-2022",
        from_="Resident Engineer, Meridian Engineering Consultants",
        to="Distribution list — Employer, Engineer, Contractor",
        extra_meta=[
            ("Meeting", "Monthly Progress Meeting No. 30"),
            ("Venue", "NRB-4 Site Office, Left Bank Approach"),
            ("Present", "Er. Anand Vasker (Resident Engineer, Meridian Engineering "
                        "Consultants); Project Manager and Planning Engineer (Sagara "
                        "Constructions Pvt. Ltd.); Project Representative (National Highways "
                        "Infrastructure Authority)"),
        ],
        body=[
            ("para", "Issued in accordance with Particular Conditions Part B.2, within 5 "
                     "working days of the meeting."),
            ("heading", "ITEM 4 — PIER P4 SUPPLEMENTARY PILE GROUP"),
            ("para", "The Contractor updated the meeting on the status of pile position P4-N4, "
                     "referring to Notice CTR-NRB4-0125 (ground condition), Notice "
                     "CTR-NRB4-0131 (plant breakdown, Rig PR-2), Geotechnical Investigation "
                     "Report GEO-NRB4-004, Site Instruction SI-NRB4-027, and Programme Update "
                     "PGM-NRB4-Rev09. The Contractor noted that the two events overlapped in "
                     "time and both affected progress at pile position P4-N4 and the "
                     "surrounding pile group, and indicated it intended to submit a claim for "
                     "extension of time once the affected pile is complete and the full effect "
                     "on the critical path can be assessed."),
            ("para", "The Resident Engineer noted that the ground condition and the plant "
                     "breakdown are distinct events with different contractual treatment under "
                     "Sub-Clause 8.4, and that any claim would need to address the effect of "
                     "each separately, including the period during which both were concurrently "
                     "affecting progress at Pier P4. The Contractor confirmed it would address "
                     "this in its detailed particulars."),
            ("para", "Pile positions P4-N3, P4-N5 and P4-N6 were confirmed complete to the "
                     "original pile schedule. No other matter affecting Pier P4 was raised."),
            ("heading", "ITEM 5 — GENERAL PROGRESS"),
            ("para", "No other matter of note was raised in respect of general progress "
                     "elsewhere on the Works."),
        ],
        closing_lines=["Minutes issued by: Resident Engineer, Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 10 -- CTR-NRB4-0142
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="CTR-NRB4-0142",
        title="Contractor's Detailed Particulars — Pier P4 Ground Condition Delay",
        doc_type="CLAIM",
        doc_type_tag="CONTRACTOR CLAIM",
        letterhead="CONTRACTOR",
        date="20-Dec-2022",
        from_="Contractor, Project Manager, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Detailed Particulars in Support of Notice CTR-NRB4-0125 — Pier P4 Ground "
                "Condition",
        body=[
            ("para", "In accordance with Sub-Clause 20.1 and further to our Notice "
                     "CTR-NRB4-0125 dated 09-Nov-2022, we submit the following particulars in "
                     "support of our claim for an extension of the Time for Completion."),
            ("para", "1. EVENT: Discovery on 03-Nov-2022 of a soft, compressible clay lens at "
                     "pile position P4-N4 (DPR-1103-2022), confirmed by Geotechnical "
                     "Investigation Report GEO-NRB4-004 dated 16-Nov-2022 as a condition not "
                     "reasonably foreseeable from the geotechnical information provided with "
                     "the tender documents, requiring a redesigned pile socket instructed under "
                     "Site Instruction SI-NRB4-027."),
            ("para", "2. CONTRACTUAL BASIS: Sub-Clause 8.4(b) and Sub-Clause 4.12, the "
                     "condition being an Unforeseeable physical condition within the meaning of "
                     "Sub-Clause 4.12 and not a risk allocated to the Contractor under the "
                     "Contract."),
            ("para", "3. PROGRAMME IMPACT: Pile position P4-N4 was affected by the ground "
                     "condition from 03-Nov-2022 until completion of boring to the revised "
                     "design, anticipated by 15-Dec-2022, a total period of approximately 6 "
                     "weeks. Pile position P4-N4 is the critical-path item for completion of "
                     "the Pier P4 supplementary pile group and the pile cap works following it. "
                     "We therefore claim an extension of the Time for Completion of 6 weeks."),
            ("para", "4. RECORDS MAINTAINED: Site diary entries, Daily Progress Reports, "
                     "Geotechnical Investigation Report GEO-NRB4-004, and Programme Update "
                     "PGM-NRB4-Rev09, all available for the Engineer's inspection."),
            ("para", "We confirm this submission relates solely to the ground condition "
                     "addressed in Notice CTR-NRB4-0125. As recorded in Notice CTR-NRB4-0131, "
                     "we do not claim any extension of time or additional payment in respect of "
                     "the separate breakdown of Piling Rig PR-2, which is a matter for the "
                     "Contractor's own account."),
        ],
        closing_lines=["Regards,", "Project Manager", "Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 11 -- ENG-NRB4-0065
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="ENG-NRB4-0065",
        title="Engineer's Request for Further Particulars — Claim CTR-NRB4-0142",
        doc_type="CORRESPONDENCE",
        doc_type_tag="CORRESPONDENCE",
        letterhead="ENGINEER",
        date="10-Jan-2023",
        from_="Engineer, Meridian Engineering Consultants",
        to="Contractor, Sagara Constructions Pvt. Ltd.",
        subject="Request for Further Particulars — Claim CTR-NRB4-0142, Pier P4 Ground "
                "Condition",
        body=[
            ("para", "We refer to your claim CTR-NRB4-0142 dated 20-Dec-2022, claiming an "
                     "extension of the Time for Completion of 6 weeks in respect of the ground "
                     "condition encountered at pile position P4-N4."),
            ("para", "We note that your own Notice CTR-NRB4-0131 dated 10-Nov-2022, and the "
                     "record of Monthly Progress Meeting No. 30 (MOM-NRB4-030), confirm that "
                     "Piling Rig PR-2 was out of service between 07-Nov-2022 and 28-Nov-2022, a "
                     "period which falls wholly within the 6-week period now claimed in respect "
                     "of the ground condition, and that the rig was engaged on work at Pier P4 "
                     "throughout that period."),
            ("para", "Before we are able to make a determination under Sub-Clause 8.4, "
                     "including the apportionment provided for at Sub-Clause 8.4 where a delay "
                     "results partly from a cause described in that Sub-Clause and partly from "
                     "a cause for which the Contractor is responsible, we require a critical "
                     "path analysis isolating, to the extent reasonably practicable, the "
                     "independent effect on the completion date of (a) the ground condition at "
                     "pile position P4-N4, and (b) the unavailability of Rig PR-2, for the "
                     "period during which both were concurrently capable of affecting progress "
                     "at Pier P4."),
            ("para", "Please submit this analysis within 21 days of this letter, in accordance "
                     "with Sub-Clause 8.4."),
        ],
        closing_lines=["Regards,", "Engineer", "Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 12 -- CPA-NRB4-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="CPA-NRB4-001",
        title="Critical Path Analysis — Pier P4 Ground Condition and Plant Breakdown",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="CRITICAL PATH ANALYSIS",
        letterhead="CONTRACTOR",
        date="07-Feb-2023",
        from_="Planning Engineer, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Critical Path Analysis Submitted in Response to ENG-NRB4-0065 — Pier P4 Pile "
                "Position P4-N4",
        body=[
            ("para", "In response to your letter ENG-NRB4-0065 dated 10-Jan-2023, we submit "
                     "the following critical path analysis isolating the independent effect of "
                     "the ground condition and the plant breakdown on progress at pile position "
                     "P4-N4."),
            ("heading", "PERIODS ANALYSED:"),
            ("table", {
                "headers": ["Cause", "Start", "End", "Independent Duration"],
                "rows": [
                    ["Ground condition (P4-N4)", "03-Nov-2022", "15-Dec-2022", "6 weeks"],
                    ["Plant breakdown (Rig PR-2)", "07-Nov-2022", "28-Nov-2022", "3 weeks"],
                    ["Overlap (both causes operative)", "07-Nov-2022", "28-Nov-2022", "3 weeks"],
                ],
            }),
            ("para", "1. GROUND CONDITION IN ISOLATION: Had Rig PR-2 remained available "
                     "throughout, boring at pile position P4-N4 could not have proceeded to "
                     "the revised design before completion of Geotechnical Investigation Report "
                     "GEO-NRB4-004 (16-Nov-2022) and Site Instruction SI-NRB4-027 (22-Nov-2022), "
                     "and, allowing for the additional 3.5m socket depth instructed, would still "
                     "have required a total period of 6 weeks from 03-Nov-2022 to 15-Dec-2022 "
                     "to complete."),
            ("para", "2. PLANT BREAKDOWN IN ISOLATION: Had the ground condition not been "
                     "encountered, boring at pile position P4-N4 to the original design would "
                     "have continued using Rig PR-2 until its breakdown on 07-Nov-2022, and "
                     "would have resumed on the rig's return to service on 28-Nov-2022, a "
                     "standalone impact of 3 weeks."),
            ("para", "3. COMBINED EFFECT: The 3-week period during which Rig PR-2 was out of "
                     "service (07-Nov-2022 to 28-Nov-2022) falls entirely within the 6-week "
                     "ground condition period. The critical path to completion of pile position "
                     "P4-N4 was, throughout this 6-week period, controlled by the ground "
                     "condition and the redesign process it necessitated: the geotechnical "
                     "investigation and Site Instruction SI-NRB4-027 were still outstanding for "
                     "the greater part of the period Rig PR-2 was unavailable, such that the "
                     "unavailability of the rig did not, in our assessment, independently "
                     "extend the date pile position P4-N4 was actually completed."),
            ("para", "We maintain, on this basis, that the ground condition is the controlling "
                     "cause of the full 6-week delay to pile position P4-N4, and that our claim "
                     "for a 6-week extension under CTR-NRB4-0142 stands. We confirm the dates "
                     "and durations in this analysis are drawn from the contemporaneous records "
                     "already provided, including EQR-NRB4-001, GEO-NRB4-004 and SI-NRB4-027."),
        ],
        closing_lines=["Prepared by: Planning Engineer, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 13 -- ENG-NRB4-0072
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="ENG-NRB4-0072",
        title="Engineer's Determination — Extension of Time, Pier P4 Ground Condition and "
              "Plant Breakdown",
        doc_type="APPROVAL",
        doc_type_tag="ENGINEER'S DETERMINATION",
        letterhead="ENGINEER",
        date="10-Mar-2023",
        from_="Engineer, Meridian Engineering Consultants",
        to="Contractor, Sagara Constructions Pvt. Ltd.",
        subject="Determination — Claim CTR-NRB4-0142 — Extension of Time, Pier P4 Pile "
                "Position P4-N4",
        body=[
            ("para", "We refer to your Notice CTR-NRB4-0125 dated 09-Nov-2022, detailed "
                     "particulars CTR-NRB4-0142 dated 20-Dec-2022, and Critical Path Analysis "
                     "CPA-NRB4-001 dated 07-Feb-2023, claiming an extension of the Time for "
                     "Completion of 6 weeks arising from the ground condition encountered at "
                     "pile position P4-N4."),
            ("para", "Having reviewed the particulars submitted, Geotechnical Investigation "
                     "Report GEO-NRB4-004, Site Instruction SI-NRB4-027, and Critical Path "
                     "Analysis CPA-NRB4-001, together with your Notice CTR-NRB4-0131 and Plant "
                     "Breakdown Report EQR-NRB4-001 concerning Piling Rig PR-2, we make the "
                     "following determination under Sub-Clause 8.4:"),
            ("para", "1. ENTITLEMENT: The ground condition encountered at pile position P4-N4 "
                     "is accepted as an Unforeseeable physical condition within the meaning of "
                     "Sub-Clause 4.12, and as falling within Sub-Clause 8.4(b). The condition "
                     "was not shown, and could not reasonably have been inferred, from the "
                     "geotechnical information provided with the tender documents."),
            ("para", "2. CONCURRENCY: Your own Critical Path Analysis CPA-NRB4-001 confirms "
                     "that the unavailability of Piling Rig PR-2, a cause for which the "
                     "Contractor is responsible, was operative between 07-Nov-2022 and "
                     "28-Nov-2022, a period falling entirely within the 6-week ground condition "
                     "period. We do not accept CPA-NRB4-001's conclusion that the plant "
                     "breakdown had no independent effect on the critical path: on a plain "
                     "reading of the dates in CPA-NRB4-001 itself, had Rig PR-2 remained "
                     "available throughout, boring at pile position P4-N4 could have continued, "
                     "in parallel with the geotechnical investigation and redesign process, up "
                     "to the point the revised design was actually issued under SI-NRB4-027, "
                     "such that the rig's unavailability was, for the 3-week period it "
                     "persisted, an equally operative cause of the Contractor's inability to "
                     "progress that pile position."),
            ("para", "3. APPORTIONMENT: In accordance with Sub-Clause 8.4's provision for "
                     "apportionment where a delay results partly from a cause described in that "
                     "Sub-Clause and partly from a cause for which the Contractor is "
                     "responsible, we apportion the 6-week period as follows: the 3-week period "
                     "from 03-Nov-2022 to 07-Nov-2022 and from 28-Nov-2022 to 15-Dec-2022, "
                     "during which the ground condition alone affected progress at pile "
                     "position P4-N4, is attributable solely to the ground condition. The "
                     "3-week concurrent period from 07-Nov-2022 to 28-Nov-2022, during which "
                     "both the ground condition and the unavailability of Rig PR-2 were "
                     "operative, is not attributed solely to the ground condition, a "
                     "Contractor-risk cause having been equally operative throughout."),
            ("para", "4. DETERMINATION: An extension of the Time for Completion of 3 weeks is "
                     "hereby granted under Sub-Clause 8.4, revising the Time for Completion "
                     "accordingly. No extension of time is granted in respect of the 3-week "
                     "concurrent period. No additional payment is due in respect of the "
                     "concurrent period; a revision to the Time for Completion under this "
                     "Sub-Clause does not, of itself, entitle the Contractor to additional "
                     "payment in any event."),
            ("para", "This determination does not address, and is without prejudice to, any "
                     "other notice or claim the Contractor may have submitted or may submit in "
                     "respect of any other event or circumstance."),
        ],
        closing_lines=["Signed: Engineer's Representative", "Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 14 -- CTR-NRB4-0155
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="CTR-NRB4-0155",
        title="Contractor's Rebuttal — Determination ENG-NRB4-0072",
        doc_type="CORRESPONDENCE",
        doc_type_tag="CORRESPONDENCE",
        letterhead="CONTRACTOR",
        date="24-Mar-2023",
        from_="Contractor, Project Manager, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Rebuttal — Determination ENG-NRB4-0072 — Pier P4 Pile Position P4-N4",
        body=[
            ("para", "We refer to the Engineer's determination ENG-NRB4-0072 dated 10-Mar-2023, "
                     "granting an extension of the Time for Completion of 3 weeks, rather than "
                     "the 6 weeks claimed in CTR-NRB4-0142, in respect of pile position P4-N4."),
            ("para", "We do not accept the apportionment made. As set out in our Critical Path "
                     "Analysis CPA-NRB4-001, the redesign process necessitated by the ground "
                     "condition — comprising the geotechnical investigation and Site "
                     "Instruction SI-NRB4-027 — was itself the controlling constraint on "
                     "completion of pile position P4-N4 throughout the period Rig PR-2 was out "
                     "of service. Boring could not have proceeded to a design that did not yet "
                     "exist, whether or not Rig PR-2 was available, until SI-NRB4-027 was "
                     "issued on 22-Nov-2022. We submit that the rig's unavailability was "
                     "therefore not, in fact, an independently operative cause during the "
                     "period before that instruction was issued, and that the Engineer's "
                     "apportionment overstates the effect of the plant breakdown."),
            ("para", "We nonetheless note the Engineer's determination and will govern "
                     "ourselves accordingly pending any further resolution of this matter, "
                     "without prejudice to our position that the full 6 weeks claimed remains "
                     "due."),
        ],
        closing_lines=["Regards,", "Project Manager", "Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),
]
