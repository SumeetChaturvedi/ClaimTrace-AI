"""Verbatim structured data for Scenario 3's 9 approved documents."""

from pdf_template import DocumentSpec

SCENARIO = 3

DOCUMENTS: list[DocumentSpec] = [

    # Document 1 -- DPR-0920-2021
    DocumentSpec(
        doc_id="DPR-0920-2021",
        title="Daily Progress Report — Pier P3 Excavation Resumption, 20-Sep-2021",
        doc_type="PROGRESS_REPORT",
        doc_type_tag="DAILY PROGRESS REPORT",
        letterhead="CONTRACTOR",
        date="20-Sep-2021",
        from_="Site Engineer, Sagara Constructions Pvt. Ltd.",
        to="Engineer's Site Office (Meridian Engineering Consultants)",
        extra_meta=[("Location", "Pier P3, Nandira River Bridge Project — Package NRB-4")],
        body=[
            ("heading", "WORK CARRIED OUT TODAY:"),
            ("bullet", "Continued excavation for Pier P3 pile cap following handback of the "
                       "area by Vantara Power Grid Corporation on 10-Sep-2021 (VPGC-NRB4-0045) "
                       "and resumption of works on 15-Sep-2021."),
            ("bullet", "On reaching founding level in the north-east quadrant of the "
                       "excavation — the same quadrant in which the transmission tower "
                       "foundation was originally encountered (DPR-0128-2021) — the exposed "
                       "ground was found to consist of loosely compacted backfill material to "
                       "a depth of approximately 3 metres, rather than the undisturbed natural "
                       "stratum present elsewhere across the founding level. This is "
                       "consistent with the backfilling of the excavation left by removal of "
                       "the former tower foundation."),
            ("bullet", "Excavation in the affected zone halted pending the Engineer's review. "
                       "Excavation elsewhere across the Pier P3 footprint continued and is "
                       "substantially complete."),
            ("bullet", "Trial pits dug at 3 locations within the affected zone at the "
                       "Engineer's Representative's request for further investigation."),
            ("bullet", "Elsewhere on site: girder erection preparation continuing at Pier P1; "
                       "routine plant servicing carried out on the second tower crane."),
            ("bullet", "Weather: Clear."),
            ("heading", "REMARKS:"),
            ("para", "The condition encountered differs materially from the geotechnical "
                     "information provided with the tender documents, which did not indicate "
                     "disturbed or backfilled ground within the Pier P3 founding stratum. "
                     "Contractor's Site Engineer to notify the Engineer formally in accordance "
                     "with Employer's Requirements Section 6."),
        ],
        closing_lines=["Reported by: Site Engineer, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 2 -- CTR-NRB4-0061
    DocumentSpec(
        doc_id="CTR-NRB4-0061",
        title="Notice of Differing Site Conditions — Pier P3 Founding Level",
        doc_type="NOTICE",
        doc_type_tag="NOTICE",
        letterhead="CONTRACTOR",
        date="22-Sep-2021",
        from_="Contractor, Project Manager, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Notice of Differing Site Conditions — Pier P3 Founding Level",
        body=[
            ("para", "We refer to Daily Progress Report DPR-0920-2021, recording that "
                     "excavation at Pier P3, resumed following handback of the area by "
                     "Vantara Power Grid Corporation (VPGC-NRB4-0045), has exposed loosely "
                     "compacted backfill material to a depth of approximately 3 metres within "
                     "the north-east quadrant of the founding level, in the same location as "
                     "the transmission tower foundation originally encountered on 28-Jan-2021 "
                     "(DPR-0128-2021)."),
            ("para", "Pursuant to Employer's Requirements Section 6, we give notice that the "
                     "condition encountered differs from the geotechnical information provided "
                     "with the tender documents. In accordance with that Section, we have not "
                     "proceeded with founding of the affected portion of the Pier P3 pile cap "
                     "pending the Engineer's review, and have made trial pits available for "
                     "the Engineer's investigation as requested."),
            ("para", "We consider this condition to be a direct consequence of the utility "
                     "relocation addressed in our earlier Notice CTR-NRB4-0021 and the "
                     "Engineer's determinations ENG-NRB4-0019 and ENG-NRB4-0024, and we "
                     "reserve our position as to entitlement pending the Engineer's "
                     "instruction as to how the affected foundation is to proceed."),
        ],
        closing_lines=["Regards,", "Project Manager", "Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 3 -- TM-NRB4-009
    DocumentSpec(
        doc_id="TM-NRB4-009",
        title="Technical Memorandum — Geotechnical Assessment of Pier P3 Founding Conditions",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="TECHNICAL MEMORANDUM",
        letterhead="ENGINEER",
        date="01-Oct-2021",
        from_="Meridian Engineering Consultants, Geotechnical Section",
        to="Project File",
        cc="National Highways Infrastructure Authority; Sagara Constructions Pvt. Ltd.",
        subject="Geotechnical Assessment — Pier P3 Founding Conditions, North-East Quadrant",
        body=[
            ("para", "1. BACKGROUND: Further to Notice CTR-NRB4-0061 and Daily Progress Report "
                     "DPR-0920-2021, this memorandum records the Engineer's assessment of "
                     "ground conditions in the north-east quadrant of the Pier P3 founding "
                     "level, following trial pitting carried out between 24-Sep-2021 and "
                     "30-Sep-2021."),
            ("para", "2. FINDINGS: Trial pits TP-1 to TP-3 confirm loosely compacted backfill "
                     "to depths ranging from 2.7 to 3.2 metres below design founding level, "
                     "occupying an area of approximately 4 metres by 4 metres within the "
                     "north-east quadrant. This is consistent with backfilling of the "
                     "excavation left by removal of the 132kV tower foundation referred to in "
                     "VPGC-NRB4-0045. The backfill material does not meet the bearing criteria "
                     "stated in the Specification and referred to in Employer's Requirements "
                     "Section 6, and is not suitable for direct founding of the pile cap as "
                     "designed."),
            ("para", "3. ASSESSMENT: Two options were considered: (a) full removal of the "
                     "backfill and replacement with mass concrete fill to founding level, or "
                     "(b) local enlargement and thickening of the pile cap with additional "
                     "reinforcement to redistribute load away from the affected zone, combined "
                     "with partial mass concrete replacement of the weakest backfill material. "
                     "Option (b) is recommended as it avoids the programme risk of a "
                     "substantially deeper excavation immediately adjacent to the completed "
                     "Pier P3 shaft reinforcement cage layout, and is compatible with the "
                     "founding levels already achieved elsewhere across the pile cap."),
            ("para", "4. RECOMMENDATION: The Engineer will issue a revised drawing for the Pier "
                     "P3 pile cap incorporating local enlargement, additional thickness, "
                     "partial mass concrete replacement, and additional reinforcement in the "
                     "affected zone, and will instruct this as a Variation under Sub-Clause "
                     "13.1, the condition not being one addressed by the original design."),
        ],
        closing_lines=["Prepared by: Geotechnical Section, Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # Document 4 -- DRG-NRB4-P3-PC-Rev02
    DocumentSpec(
        doc_id="DRG-NRB4-P3-PC-Rev02",
        title="Revised Drawing — Pier P3 Pile Cap, Revision 02",
        doc_type="DRAWING",
        doc_type_tag="DRAWING — ISSUED FOR CONSTRUCTION",
        letterhead="ENGINEER",
        date="08-Oct-2021",
        from_="Meridian Engineering Consultants",
        to="Sagara Constructions Pvt. Ltd.",
        extra_meta=[("Supersedes", "DRG-NRB4-P3-PC-Rev01")],
        subject="Pier P3 Pile Cap — Revised General Arrangement and Reinforcement Detail",
        body=[
            ("para", "Issued for construction in accordance with the recommendation in "
                     "Technical Memorandum TM-NRB4-009 dated 01-Oct-2021."),
            ("heading", "SUMMARY OF REVISION:"),
            ("bullet", "Pile cap plan dimension in the north-east quadrant enlarged from the "
                       "original 12.0m x 10.0m footprint to 13.5m x 10.0m, to redistribute "
                       "load around the backfilled zone identified in TM-NRB4-009."),
            ("bullet", "Pile cap thickness in the affected zone increased locally from 2.2m to "
                       "2.6m."),
            ("bullet", "Mass concrete replacement fill, Grade M20, to be placed within the "
                       "backfilled zone to design founding level before pile cap reinforcement "
                       "is fixed over that area."),
            ("bullet", "Additional reinforcement introduced in the enlarged and thickened zone "
                       "as detailed on the accompanying bar bending schedule, "
                       "DRG-NRB4-P3-PC-Rev02-BBS."),
            ("bullet", "All other dimensions, materials and reinforcement outside the affected "
                       "zone unchanged from DRG-NRB4-P3-PC-Rev01."),
            ("para", "This drawing shall be read together with Variation Order VO-NRB4-004. "
                     "Construction on the basis of this revision shall be subject to Hold "
                     "Points (a), (b), (c) and (d) under Employer's Requirements Section 11, "
                     "in the same manner as for the original design."),
        ],
        closing_lines=["Issued by: Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # Document 5 -- VO-NRB4-004
    DocumentSpec(
        doc_id="VO-NRB4-004",
        title="Variation Order VO-NRB4-004 — Pier P3 Pile Cap Redesign",
        doc_type="VARIATION",
        doc_type_tag="VARIATION ORDER",
        letterhead="ENGINEER",
        date="08-Oct-2021",
        from_="Engineer, Meridian Engineering Consultants",
        to="Contractor, Sagara Constructions Pvt. Ltd.",
        subject="Variation Order — Pier P3 Pile Cap Redesign, Founding Condition",
        body=[
            ("para", "Pursuant to Sub-Clause 13.1, the Engineer hereby instructs the following "
                     "Variation, arising from the differing site condition notified in "
                     "CTR-NRB4-0061 and assessed in Technical Memorandum TM-NRB4-009:"),
            ("para", "1. DESCRIPTION OF VARIATION: Local enlargement and thickening of the "
                     "Pier P3 pile cap in the north-east quadrant, mass concrete replacement "
                     "of unsuitable backfill material, and additional reinforcement, all as "
                     "shown on revised drawing DRG-NRB4-P3-PC-Rev02."),
            ("para", "2. REASON: The backfilled ground condition encountered within the former "
                     "tower foundation excavation does not meet the founding criteria in the "
                     "Specification and was not addressed by the original pile cap design."),
            ("para", "3. INSTRUCTION: The Contractor shall proceed with the additional "
                     "excavation, mass concrete replacement and enlarged pile cap works shown "
                     "on DRG-NRB4-P3-PC-Rev02, subject to the Hold Points identified in "
                     "Employer's Requirements Section 11 applying to the revised work in the "
                     "same manner as to the original design."),
            ("para", "4. VALUATION: In accordance with Sub-Clause 13.3, the Contractor shall "
                     "submit a priced quotation for the varied work, identifying quantities "
                     "and rates, for the Engineer's assessment. In the absence of a period "
                     "otherwise agreed, the Engineer will respond within 14 days of receipt of "
                     "a complete quotation, in accordance with Sub-Clause 13.3. Given the "
                     "value of the work involved, valuation of this Variation is subject to "
                     "the Employer's approval threshold under Particular Conditions Part E.1 "
                     "and does not fall within the Resident Engineer's delegated authority "
                     "under Particular Conditions Part B.1."),
            ("para", "This instruction is issued without prejudice to any other matter raised "
                     "in CTR-NRB4-0061."),
        ],
        closing_lines=["Signed: Engineer's Representative", "Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # Document 6 -- CTR-NRB4-0067
    DocumentSpec(
        doc_id="CTR-NRB4-0067",
        title="Contractor's Variation Quotation — VO-NRB4-004",
        doc_type="VARIATION",
        doc_type_tag="VARIATION QUOTATION",
        letterhead="CONTRACTOR",
        date="22-Oct-2021",
        from_="Contractor, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Variation Quotation — VO-NRB4-004 — Pier P3 Pile Cap Redesign",
        body=[
            ("para", "In accordance with Sub-Clause 13.3 and Variation Order VO-NRB4-004, we "
                     "submit our priced quotation for the varied works shown on drawing "
                     "DRG-NRB4-P3-PC-Rev02."),
            ("subheading", "COST BREAKDOWN:"),
            ("table", {
                "headers": ["Item", "Description", "Qty", "Rate (VTD)", "Amount (VTD)"],
                "rows": [
                    ["1", "Additional excavation and disposal of backfill", "48 m3", "1,850/m3", "88,800"],
                    ["2", "Mass concrete replacement fill, Grade M20", "22 m3", "6,400/m3", "140,800"],
                    ["3", "Additional reinforced concrete, Grade M40", "28 m3", "8,200/m3", "229,600"],
                    ["4", "Additional reinforcement steel", "3.1 t", "42,000/t", "130,200"],
                    ["5", "Additional formwork to enlarged pile cap edge", "38 m2", "1,450/m2", "55,100"],
                    ["6", "Disruption and extended standing time, plant and crew, "
                          "Pier P3, 14 days", "LS", "—", "42,900"],
                    ["", "", "", "TOTAL:", "VTD 687,400"],
                ],
                "right_align_cols": [2, 3, 4],
                "bold_last_row": True,
            }),
            ("para", "Items 1–5 are priced by reference to Contract rates for comparable items "
                     "in the Bill of Quantities, adjusted where no directly comparable rate "
                     "exists, in accordance with Sub-Clause 13.3. Item 6 reflects standing "
                     "time for plant and crew mobilised to the affected zone during the period "
                     "between notice CTR-NRB4-0061 and issue of drawing DRG-NRB4-P3-PC-Rev02, "
                     "during which work on the affected portion of the pile cap could not "
                     "proceed."),
            ("para", "Supporting quantity calculations and delivery records are available for "
                     "the Engineer's inspection."),
        ],
        closing_lines=["Regards,", "Project Manager / Quantity Surveyor",
                       "Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 7 -- ENG-NRB4-0031
    DocumentSpec(
        doc_id="ENG-NRB4-0031",
        title="Engineer's Assessment of Variation Quotation — VO-NRB4-004",
        doc_type="APPROVAL",
        doc_type_tag="ENGINEER'S ASSESSMENT",
        letterhead="ENGINEER",
        date="05-Nov-2021",
        from_="Engineer, Meridian Engineering Consultants",
        to="Contractor, Sagara Constructions Pvt. Ltd.",
        cc="National Highways Infrastructure Authority",
        subject="Assessment of Variation Quotation CTR-NRB4-0067 — VO-NRB4-004",
        body=[
            ("para", "We refer to your quotation CTR-NRB4-0067 dated 22-Oct-2021 for the "
                     "varied works instructed under VO-NRB4-004, and respond within the 14-day "
                     "period provided in Sub-Clause 13.3."),
            ("subheading", "ASSESSMENT BY ITEM:"),
            ("para", "Item 1 (Excavation and disposal, 48 m3): Accepted in full. Amount: VTD "
                     "88,800."),
            ("para", "Item 2 (Mass concrete replacement fill, 22 m3): Accepted in full. "
                     "Amount: VTD 140,800."),
            ("para", "Item 3 (Additional reinforced concrete, Grade M40): Our own measurement "
                     "against as-built dimensions recorded against drawing "
                     "DRG-NRB4-P3-PC-Rev02 indicates a quantity of 24 m3, not the 28 m3 "
                     "quoted. Adjusted amount: 24 m3 x VTD 8,200/m3 = VTD 196,800."),
            ("para", "Item 4 (Additional reinforcement steel): Our measurement, cross-checked "
                     "against the bar bending schedule DRG-NRB4-P3-PC-Rev02-BBS, indicates a "
                     "quantity of 2.6 tonnes, not 3.1 tonnes. Adjusted amount: 2.6 t x VTD "
                     "42,000/t = VTD 109,200."),
            ("para", "Item 5 (Additional formwork, 38 m2): Accepted in full. Amount: VTD "
                     "55,100."),
            ("para", "Item 6 (Disruption and extended standing time, lump sum VTD 42,900): Not "
                     "accepted. Valuation of a Variation under Sub-Clause 13.3 values the "
                     "varied work itself; it is not the mechanism for valuing standing time or "
                     "disruption arising from the period before an instruction is issued. Any "
                     "such claim would fall to be considered, if pursued, as a separate claim "
                     "under Sub-Clause 20.1, supported by its own notice and particulars, none "
                     "of which has been submitted. This item is accordingly valued at nil "
                     "under this assessment, without prejudice to the Contractor's right to "
                     "pursue it separately in accordance with Sub-Clause 20.1."),
            ("total_box", "ENGINEER'S RECOMMENDED VALUATION: VTD 590,700 (Items 1–5 as "
                          "adjusted; Item 6 nil)."),
            ("para", "As this valuation exceeds the threshold in Particular Conditions Part "
                     "E.1, it is submitted to the Employer for approval and does not fall "
                     "within the Resident Engineer's delegated authority under Particular "
                     "Conditions Part B.1. We will confirm the Employer's decision separately."),
        ],
        closing_lines=["Signed: Engineer's Representative", "Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # Document 8 -- MOM-NRB4-022
    DocumentSpec(
        doc_id="MOM-NRB4-022",
        title="Minutes of Monthly Progress Meeting No. 22",
        doc_type="MEETING_MINUTES",
        doc_type_tag="PROGRESS MEETING MINUTES",
        letterhead="ENGINEER",
        date="20-Nov-2021",
        from_="Resident Engineer, Meridian Engineering Consultants",
        to="Distribution list — Employer, Engineer, Contractor",
        extra_meta=[
            ("Meeting", "Monthly Progress Meeting No. 22"),
            ("Venue", "NRB-4 Site Office, Left Bank Approach"),
            ("Present", "Er. Anand Vasker (Resident Engineer, Meridian Engineering "
                        "Consultants); Project Manager and Quantity Surveyor (Sagara "
                        "Constructions Pvt. Ltd.); Project Representative (National Highways "
                        "Infrastructure Authority)"),
        ],
        body=[
            ("para", "Issued in accordance with Particular Conditions Part B.2, within 5 "
                     "working days of the meeting."),
            ("heading", "1. PREVIOUS MINUTES:"),
            ("para", "Minutes of Meeting No. 21 confirmed without amendment."),
            ("heading", "2. PROGRESS SUMMARY:"),
            ("para", "Girder erection at Pier P4 commenced 08-Nov-2021 following delivery of "
                     "the second precast segment batch. Superstructure works at Piers P1 and "
                     "P2 substantially complete. Pier P3 pile cap works outside the affected "
                     "north-east quadrant proceeding; works in the affected zone held pending "
                     "the Variation approval discussed below."),
            ("heading", "3. VARIATION VO-NRB4-004 (PIER P3 PILE CAP REDESIGN):"),
            ("para", "The Engineer summarised its assessment ENG-NRB4-0031 of the Contractor's "
                     "quotation CTR-NRB4-0067, noting a recommended valuation of VTD 590,700 "
                     "against the Contractor's quoted VTD 687,400, principally reflecting "
                     "adjusted concrete and reinforcement quantities and non-acceptance of the "
                     "disruption lump sum. The Contractor noted its quotation stood as "
                     "submitted but confirmed it would not delay works in the affected zone "
                     "pending resolution of valuation. The Employer's representative noted the "
                     "matter was under review for approval in accordance with Particular "
                     "Conditions Part E.1 and would respond formally."),
            ("heading", "4. QUALITY:"),
            ("para", "Concrete cube test results for October pours across all piers reported "
                     "satisfactory; no non-conformances raised."),
            ("heading", "5. PROCUREMENT:"),
            ("para", "Contractor confirmed the third and final precast girder segment batch "
                     "remains on schedule for delivery Q1 2022."),
            ("heading", "6. HEALTH AND SAFETY:"),
            ("para", "No lost-time incidents reported for the period."),
            ("heading", "7. NEXT MEETING:"),
            ("para", "Scheduled for 20-Dec-2021."),
        ],
        closing_lines=["Minutes recorded by: Resident Engineer, Meridian Engineering "
                       "Consultants"],
        scenario=SCENARIO,
    ),

    # Document 9 -- NHIA-NRB4-APR-006
    DocumentSpec(
        doc_id="NHIA-NRB4-APR-006",
        title="Employer's Approval — Variation VO-NRB4-004 Valuation",
        doc_type="APPROVAL",
        doc_type_tag="EMPLOYER'S APPROVAL",
        letterhead="EMPLOYER",
        date="25-Nov-2021",
        from_="National Highways Infrastructure Authority",
        to="Meridian Engineering Consultants",
        cc="Sagara Constructions Pvt. Ltd.",
        subject="Approval — Variation VO-NRB4-004 Valuation",
        body=[
            ("para", "We refer to the Engineer's assessment ENG-NRB4-0031 dated 05-Nov-2021 "
                     "of Contractor's Variation Quotation CTR-NRB4-0067, recommending a "
                     "valuation of VTD 590,700 for the works instructed under Variation Order "
                     "VO-NRB4-004."),
            ("para", "In accordance with Particular Conditions Part E.1, we confirm the "
                     "Employer's approval of the Engineer's recommended valuation of VTD "
                     "590,700 in full. We note the Engineer's basis for this figure, including "
                     "the adjustment of quoted concrete and reinforcement quantities to "
                     "measured amounts and the exclusion of the disruption item pending any "
                     "separate claim the Contractor may bring under Sub-Clause 20.1, and have "
                     "no further comment on the assessment."),
            ("para", "The Engineer is authorised to proceed on this basis and to include the "
                     "approved amount in the next Interim Payment Certificate in accordance "
                     "with Particular Conditions Part F.2."),
        ],
        closing_lines=["Regards,", "National Highways Infrastructure Authority"],
        scenario=SCENARIO,
    ),
]
