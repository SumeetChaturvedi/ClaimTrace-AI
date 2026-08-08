"""Structured, VERBATIM data for the 7 approved Scenario 1 documents.

Every string value below is copied unchanged from the approved
"Dataset V2 -- Scenario 1 -- Document Generation" deliverable. No wording
has been added, removed, reworded, or summarized. The only transformation
applied is mechanical: (1) the metadata fields that were originally
written as inline header lines (e.g. "LETTER REF: CTR-NRB4-0021") are
lifted into the structured `DocumentSpec` fields the template's metadata
box expects, and (2) prose paragraphs that were hand-wrapped at ~78
characters for chat display are joined back into single logical
paragraphs (line-wrap is presentational, not wording). Every substantive
word, number, date, and identifier is unchanged.
"""

from pdf_template import DocumentSpec

SCENARIO = 1

DOCUMENTS: list[DocumentSpec] = [

    # ------------------------------------------------------------------
    # Document 1 -- DPR-0128-2021
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="DPR-0128-2021",
        title="Daily Progress Report — Pier 3 Excavation, 28-Jan-2021",
        doc_type="PROGRESS_REPORT",
        doc_type_tag="DAILY PROGRESS REPORT",
        letterhead="CONTRACTOR",
        date="28-Jan-2021",
        from_="Site Engineer, Sagara Constructions Pvt. Ltd.",
        to="Engineer's Site Office (Meridian Engineering Consultants)",
        extra_meta=[("Location", "Pier P3, Nandira River Bridge Project — Package NRB-4")],
        body=[
            ("heading", "WORK CARRIED OUT TODAY:"),
            ("bullet", "Continued open excavation for Pier P3 pile cap, north-east quadrant, "
                       "to a depth of approximately 2.4m below existing ground level."),
            ("bullet", "At approximately 11:15, excavation exposed a concrete foundation block "
                       "and associated buried cabling consistent with a transmission tower "
                       "footing, situated within the Pier P3 excavation footprint. This "
                       "structure is not shown on the Drawings issued for construction."),
            ("bullet", "Excavation in the immediate vicinity was stopped as a safety precaution. "
                       "Remainder of the pile cap excavation outside the affected quadrant "
                       "continued."),
            ("bullet", "Labour deployed: 14 general labourers, 2 excavator operators, 1 "
                       "supervisor."),
            ("bullet", "Weather: Clear."),
            ("heading", "REMARKS:"),
            ("para", "The exposed structure is believed to be associated with the 132kV "
                     "transmission line referred to in Employer's Requirements Section 8 "
                     "(Utilities), which is shown on the Utility Drawings as running generally "
                     "parallel to the highway corridor. However, the specific tower foundation "
                     "encountered today, situated within the Pier P3 footprint itself, does not "
                     "appear on the Drawings or on the Utility Drawings provided with the tender "
                     "documents. Photographs taken and retained. Contractor's Site Engineer to "
                     "notify the Engineer formally in accordance with Particular Conditions Part "
                     "C.4."),
        ],
        closing_lines=["Reported by: Site Engineer, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 2 -- CTR-NRB4-0021
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="CTR-NRB4-0021",
        title="Notice of Delay — Unforeseen Utility Conflict at Pier P3",
        doc_type="NOTICE",
        doc_type_tag="NOTICE",
        letterhead="CONTRACTOR",
        date="10-Feb-2021",
        from_="Contractor, Project Manager, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject=("Notice of Delay — Unforeseen Utility Conflict, Pier P3 — Nandira River "
                 "Bridge Project, Package NRB-4"),
        body=[
            ("para", "We write further to the discovery on 28-Jan-2021, recorded in Daily "
                     "Progress Report DPR-0128-2021, of a transmission tower foundation within "
                     "the excavation footprint for Pier P3. This structure is not shown on the "
                     "Drawings issued for construction, nor on the Utility Drawings referred to "
                     "in Employer's Requirements Section 8."),
            ("para", "Pursuant to Sub-Clause 20.1 of the Conditions of Contract, we hereby give "
                     "notice that this event constitutes a cause of delay for which we consider "
                     "the Contractor entitled to an extension of the Time for Completion under "
                     "Sub-Clause 8.4(c), being an act, omission or default attributable to the "
                     "Employer's side in respect of the completeness of utility information "
                     "provided with the tender documents."),
            ("para", "Excavation and pile cap works at Pier P3 remain suspended in the affected "
                     "quadrant pending confirmation from the relevant utility owner as to the "
                     "nature of the structure and any relocation required. We are keeping "
                     "contemporaneous records of the resulting impact on our programme in "
                     "accordance with Sub-Clause 20.1 and will submit fully detailed particulars "
                     "within 42 days of this notice, in accordance with the Contract."),
            ("para", "We reserve our rights to claim an extension of time and any associated "
                     "cost consequences arising from this event."),
        ],
        closing_lines=["Regards,", "Project Manager", "Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 3 -- SI-NRB4-014
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="SI-NRB4-014",
        title="Site Instruction SI-NRB4-014 — Resequencing of Works, Pier P3",
        doc_type="SITE_INSTRUCTION",
        doc_type_tag="SITE INSTRUCTION",
        letterhead="ENGINEER",
        date="25-Feb-2021",
        from_="Engineer (on behalf of Employer), per Er. Anand Vasker, Resident Engineer, "
              "acting within the delegation recorded under Particular Conditions Part B.1",
        to="Contractor, Sagara Constructions Pvt. Ltd.",
        extra_meta=[("Project", "Nandira River Bridge Project — Package NRB-4")],
        body=[
            ("heading", "INSTRUCTION:"),
            ("para", "Further to your Notice CTR-NRB4-0021 dated 10-Feb-2021 concerning the "
                     "unforeseen utility structure at Pier P3, and pending confirmation from "
                     "Vantara Power Grid Corporation of the relocation requirements, the "
                     "Contractor is instructed as follows:"),
            ("para", "1. Excavation and pile cap works at Pier P3 shall remain suspended in the "
                     "affected quadrant until further instruction."),
            ("para", "2. The Contractor shall resequence its programme to prioritise "
                     "substructure works at Piers P1, P2, P4 and P5, and associated approach "
                     "works, so as to maintain overall progress during the period of suspension "
                     "at Pier P3."),
            ("para", "3. The Contractor shall afford Vantara Power Grid Corporation and its "
                     "representatives reasonable access to the affected area for investigation "
                     "and relocation works, in accordance with Particular Conditions Part C.4."),
            ("para", "This instruction is issued without prejudice to any entitlement to "
                     "extension of time or additional cost the Contractor may have under "
                     "Sub-Clause 8.4 or Sub-Clause 20.1 in respect of this event, which remains "
                     "under the Engineer's consideration."),
        ],
        closing_lines=["Signed: Er. Anand Vasker, Resident Engineer"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 4 -- VPGC-NRB4-0012
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="VPGC-NRB4-0012",
        title="Vantara Power Grid Corporation — Relocation Timeline Confirmation",
        doc_type="CORRESPONDENCE",
        doc_type_tag="CORRESPONDENCE",
        letterhead="THIRD_PARTY",
        letterhead_org_override="Vantara Power Grid Corporation",
        date="05-Mar-2021",
        from_="Vantara Power Grid Corporation, Network Operations",
        to="Meridian Engineering Consultants (Engineer)",
        cc="Sagara Constructions Pvt. Ltd. (Contractor)",
        subject="Relocation of 132kV Tower Foundation — Pier P3, Nandira River Bridge Project",
        body=[
            ("para", "We refer to the site inspection carried out jointly with your "
                     "representatives and the Contractor on 15-Feb-2021, following notification "
                     "of a tower foundation encountered within the Pier P3 excavation. We "
                     "confirm that this foundation forms part of our 132kV transmission network "
                     "and was not correctly reflected in the utility records provided in "
                     "connection with this project; we regret the resulting discrepancy with "
                     "the Drawings."),
            ("para", "Relocation of the affected tower and associated foundation to the "
                     "alignment shown on the enclosed drawing will require design approval, "
                     "statutory clearances, and construction of the replacement foundation and "
                     "tower prior to decommissioning of the existing structure. On this basis, "
                     "we estimate a duration of 14 weeks from commencement of relocation works "
                     "to full decommissioning and handover of the affected area."),
            ("para", "We will confirm the commencement date for relocation works separately "
                     "once internal approvals are finalised, and will keep the Engineer "
                     "informed of progress throughout."),
        ],
        closing_lines=["Regards,", "Network Operations", "Vantara Power Grid Corporation"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 5 -- CTR-NRB4-0028
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="CTR-NRB4-0028",
        title="Contractor's Detailed Particulars — Pier P3 Utility Conflict Delay",
        doc_type="CORRESPONDENCE",
        doc_type_tag="CORRESPONDENCE",
        letterhead="CONTRACTOR",
        date="24-Mar-2021",
        from_="Contractor, Project Manager, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Detailed Particulars in Support of Notice CTR-NRB4-0021 — Pier P3 Utility "
                "Conflict",
        body=[
            ("para", "In accordance with Sub-Clause 20.1 and further to our Notice CTR-NRB4-0021 "
                     "dated 10-Feb-2021, we submit the following particulars in support of our "
                     "claim for an extension of the Time for Completion."),
            ("para", "1. EVENT: Discovery on 28-Jan-2021 of an undisclosed 132kV tower "
                     "foundation within the Pier P3 excavation footprint (DPR-0128-2021), "
                     "confirmed by Vantara Power Grid Corporation on 05-Mar-2021 "
                     "(VPGC-NRB4-0012) as requiring relocation, with an estimated relocation "
                     "duration of 14 weeks from commencement."),
            ("para", "2. CONTRACTUAL BASIS: Sub-Clause 8.4(c), the event being attributable to "
                     "the completeness of utility information provided with the tender "
                     "documents, and not a risk allocated to the Contractor under the Contract "
                     "or the Employer's Requirements."),
            ("para", "3. PROGRAMME IMPACT: Pier P3 substructure works, on the critical path for "
                     "completion of the river crossing, have been suspended since 28-Jan-2021 "
                     "per Site Instruction SI-NRB4-014. While resequencing under SI-NRB4-014 has "
                     "allowed continued progress at Piers P1, P2, P4 and P5, our programme "
                     "analysis indicates that the Pier P3 suspension will, absent full "
                     "mitigation, translate into a net critical path delay to Substantial "
                     "Completion once the relocation is complete. We will submit a final "
                     "assessment of the net delay once the relocation is finished and Pier P3 "
                     "works can resume, in accordance with Sub-Clause 8.4."),
            ("para", "4. RECORDS MAINTAINED: Site diary entries, Daily Progress Reports, and "
                     "correspondence with Vantara Power Grid Corporation, all available for the "
                     "Engineer's inspection."),
            ("para", "We confirm this submission is made without prejudice to further "
                     "particulars as the effects of this event continue, and we will update the "
                     "Engineer at monthly intervals as required by the Contract."),
        ],
        closing_lines=["Regards,", "Project Manager", "Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 6 -- VPGC-NRB4-0045
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="VPGC-NRB4-0045",
        title="Vantara Power Grid Corporation — Utility Relocation Completion Notice",
        doc_type="CORRESPONDENCE",
        doc_type_tag="CORRESPONDENCE",
        letterhead="THIRD_PARTY",
        letterhead_org_override="Vantara Power Grid Corporation",
        date="10-Sep-2021",
        from_="Vantara Power Grid Corporation, Network Operations",
        to="Meridian Engineering Consultants (Engineer)",
        cc="Sagara Constructions Pvt. Ltd. (Contractor)",
        subject="Completion of Tower Relocation — Pier P3, Nandira River Bridge Project",
        body=[
            ("para", "Further to our letter VPGC-NRB4-0012 dated 05-Mar-2021, we confirm that "
                     "relocation of the 132kV tower and foundation previously situated within "
                     "the Pier P3 footprint is now complete, and the affected area is handed "
                     "back for construction purposes with effect from today's date."),
            ("para", "We note that the relocation works, once commenced, took approximately 22 "
                     "weeks to complete against our original 14-week estimate. This was due to "
                     "an extended statutory clearance process for the replacement tower "
                     "alignment and a delay in sourcing a specialised component for the new "
                     "foundation, both outside our original allowance. We regret any impact "
                     "this extended duration may have caused to the Nandira River Bridge "
                     "Project programme."),
        ],
        closing_lines=["Regards,", "Network Operations", "Vantara Power Grid Corporation"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 7 -- ENG-NRB4-0019
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="ENG-NRB4-0019",
        title="Engineer's Determination — Extension of Time (EOT-01), Pier P3 Utility "
              "Conflict",
        doc_type="APPROVAL",
        doc_type_tag="ENGINEER'S DETERMINATION",
        letterhead="ENGINEER",
        date="25-Sep-2021",
        from_="Engineer, Meridian Engineering Consultants",
        to="Contractor, Sagara Constructions Pvt. Ltd.",
        subject="Determination — EOT-01 — Extension of Time Claim, Pier P3 Utility Conflict "
                "(Notice CTR-NRB4-0021)",
        body=[
            ("para", "We refer to your Notice CTR-NRB4-0021 dated 10-Feb-2021 and detailed "
                     "particulars CTR-NRB4-0028 dated 24-Mar-2021, claiming an extension of the "
                     "Time for Completion arising from the unforeseen utility structure "
                     "encountered at Pier P3 on 28-Jan-2021."),
            ("para", "Having reviewed the particulars submitted, Site Instruction SI-NRB4-014, "
                     "and the confirmation from Vantara Power Grid Corporation (VPGC-NRB4-0012 "
                     "and VPGC-NRB4-0045) that relocation works, once commenced, extended to "
                     "approximately 22 weeks against a 14-week estimate, we make the following "
                     "determination under Sub-Clause 8.4:"),
            ("para", "1. ENTITLEMENT: The event is accepted as falling within Sub-Clause 8.4(c). "
                     "The utility structure was not shown on the Drawings or Utility Drawings "
                     "provided with the tender documents, and its presence within the Pier P3 "
                     "footprint could not reasonably have been foreseen by the Contractor at "
                     "the date of the Letter of Acceptance."),
            ("para", "2. ASSESSMENT OF DELAY: Although the affected area remained unavailable "
                     "for approximately 32 weeks in total (28-Jan-2021 to 10-Sep-2021), the "
                     "resequencing instructed under SI-NRB4-014 allowed the Contractor to "
                     "maintain progress at Piers P1, P2, P4 and P5 for the greater part of this "
                     "period without corresponding loss to the overall programme. Based on our "
                     "review of the Contractor's updated programme and critical path analysis, "
                     "we assess the net critical path delay to Substantial Completion "
                     "attributable to this event at 10 weeks."),
            ("para", "3. DETERMINATION: An extension of the Time for Completion of 10 weeks is "
                     "hereby granted under Sub-Clause 8.4, revising the Time for Completion "
                     "accordingly. This extension relates solely to the Pier P3 utility "
                     "conflict addressed in this determination."),
            ("para", "This determination does not address, and is without prejudice to, any "
                     "other notice or claim the Contractor may have submitted or may submit in "
                     "respect of any other event or circumstance."),
        ],
        closing_lines=["Signed: Engineer's Representative", "Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),
]
