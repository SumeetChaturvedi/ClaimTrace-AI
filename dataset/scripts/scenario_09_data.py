"""Verbatim structured data for Scenario 9's 7 approved documents."""

from pdf_template import DocumentSpec

SCENARIO = 9

DOCUMENTS: list[DocumentSpec] = [

    # Document 1 -- CTR-NRB4-0198
    DocumentSpec(
        doc_id="CTR-NRB4-0198",
        title="Contractor's Application for the Taking-Over Certificate",
        doc_type="NOTICE",
        doc_type_tag="APPLICATION FOR TAKING-OVER",
        letterhead="CONTRACTOR",
        date="05-Sep-2023",
        from_="Contractor, Project Manager, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Application for the Taking-Over Certificate — Nandira River Bridge Project, "
                "Package NRB-4",
        body=[
            ("para", "We hereby apply for the Taking-Over Certificate in respect of the "
                     "Works, pursuant to Sub-Clause 10.1, on the basis that the bridge and "
                     "approach works are complete and fit for their intended purpose in "
                     "accordance with the Contract."),
            ("para", "1. STRUCTURAL COMPLETION: All substructure and superstructure works are "
                     "complete across all 8 spans, Abutment A1 to Abutment A2, consistent "
                     "with progress reported at Meeting No. 26 (MOM-NRB4-026) and confirmed "
                     "complete by 22-Apr-2022."),
            ("para", "2. LOAD TESTING: Static and dynamic load testing of the completed "
                     "structure was carried out 28-Aug-2023 to 30-Aug-2023 in accordance with "
                     "Employer's Requirements Sections 11 and 12, and the results were "
                     "accepted by the Engineer by letter ENG-NRB4-0058 dated 01-Sep-2023."),
            ("para", "3. APPROACH ROAD AND FINISHING WORKS: Approach road pavement on both "
                     "banks, drainage, parapets, and expansion joint installation are "
                     "complete, consistent with the recovery trajectory reported following "
                     "acceptance of the Recovery Programme (ENG-NRB4-0052, 08-Aug-2022)."),
            ("para", "4. PROGRAMME: We note this Application is made 18 days ahead of the "
                     "revised Time for Completion of 23-Sep-2023 (per EOT-01, ENG-NRB4-0019)."),
            ("para", "5. OUTSTANDING MATTERS: A small number of minor items remain "
                     "outstanding, as will be identified during the Engineer's inspection. We "
                     "consider none of these items affects the fitness of the Works for their "
                     "intended purpose or prevents Taking-Over, and we are prepared to "
                     "complete any such items within an agreed period following Taking-Over."),
            ("para", "We request the Engineer's inspection at the earliest opportunity, and "
                     "confirm the Works, drawings, and manuals are available for review, save "
                     "as-built drawings for 2 of the 8 spans, which remain in preparation and "
                     "will be identified in our submission to the inspection."),
        ],
        closing_lines=["Regards,", "Project Manager", "Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 2 -- EIN-NRB4-001
    DocumentSpec(
        doc_id="EIN-NRB4-001",
        title="Engineer's Inspection Notes — Taking-Over Inspection",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="ENGINEER'S INSPECTION NOTES",
        letterhead="ENGINEER",
        date="09-Sep-2023",
        from_="Er. Anand Vasker, Resident Engineer, Meridian Engineering Consultants",
        to="Project File",
        cc="Meridian Engineering Consultants (Principal)",
        subject="Inspection Notes — Taking-Over Inspection, Day 2 (of 3)",
        body=[
            ("para", "Inspection commenced 08-Sep-2023, continuing today; to conclude "
                     "10/11-Sep-2023."),
            ("para", "STRUCTURAL: Walked full deck length, Abutment A1 to Abutment A2. No "
                     "structural cracking, spalling, or other defect observed at any pier or "
                     "span. Bearings and expansion joints inspected at all 7 piers and both "
                     "abutments; installation appears correct and consistent with approved "
                     "drawings. No structural or safety-critical observation to date."),
            ("para", "DECK DRAINAGE: Minor ponding observed on the deck surface at one "
                     "location, approximately mid-span between Piers P5 and P6, following "
                     "overnight rain. Localised, does not affect traffic safety, appears "
                     "attributable to a shallow drainage channel grading deficiency over a "
                     "short length. Minor item, will be listed for correction."),
            ("para", "PARAPETS: Visible transport and handling marks (surface abrasion, no "
                     "structural significance) on parapet sections at three locations. Minor, "
                     "cosmetic."),
            ("para", "APPROACH ROAD: Pavement, marking, and drainage on both banks "
                     "inspected, satisfactory. Two traffic sign posts not yet installed on "
                     "the right bank approach, positions marked but signs not yet fixed. "
                     "Minor."),
            ("para", "DOCUMENTATION: As-built drawings received and reviewed for 6 of 8 "
                     "spans; 2 spans (P6–P7, P7–A2) outstanding, Contractor advises these are "
                     "in final drafting. Noted, not a physical defect."),
            ("para", "Preliminary view: nothing observed to date indicates the Works are not "
                     "substantially complete or not fit for their intended purpose. "
                     "Continuing inspection tomorrow to confirm no further items arise."),
        ],
        closing_lines=["Notes recorded by: Er. Anand Vasker, Resident Engineer"],
        scenario=SCENARIO,
    ),

    # Document 3 -- JIR-NRB4-001
    DocumentSpec(
        doc_id="JIR-NRB4-001",
        title="Joint Inspection Report — Taking-Over Inspection",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="JOINT INSPECTION REPORT",
        letterhead="JOINT",
        date="11-Sep-2023",
        from_="Meridian Engineering Consultants, jointly with Sagara Constructions Pvt. Ltd.",
        to="National Highways Infrastructure Authority",
        cc="Sagara Constructions Pvt. Ltd.",
        extra_meta=[
            ("Inspection Period", "08-Sep-2023 to 11-Sep-2023"),
            ("Participants", "Er. Anand Vasker (Resident Engineer, Meridian Engineering "
                             "Consultants); Project Manager and Site Engineer (Sagara "
                             "Constructions Pvt. Ltd.); Project Representative (National "
                             "Highways Infrastructure Authority, present 10-Sep-2023)"),
        ],
        subject="Joint Inspection Report — Application CTR-NRB4-0198",
        body=[
            ("para", "1. SCOPE: Full walk-through inspection of the bridge structure "
                     "(Abutment A1 to Abutment A2, all 8 spans), both approach roads, and "
                     "associated drainage, signage, and finishing works, together with review "
                     "of completed testing and available documentation."),
            ("para", "2. STRUCTURAL CONDITION: No critical or structural defect identified at "
                     "any location. Load testing (28–30-Aug-2023) previously accepted by the "
                     "Engineer (ENG-NRB4-0058) confirmed satisfactory structural performance. "
                     "Bearings, expansion joints, and deck surfacing are consistent with the "
                     "approved drawings and free of defect materially affecting structural "
                     "performance or safety."),
            ("para", "3. MINOR ITEMS IDENTIFIED: Four items are identified as outstanding, "
                     "none of which is assessed as critical or as preventing beneficial use "
                     "of the Works. These are consolidated in Punch List PL-NRB4-001."),
            ("para", "4. OTHER COMPLETION-STAGE MATTERS (not assessed as defects): minor "
                     "verge reinstatement near Abutment A2 following construction access is "
                     "in progress as routine site restoration; operation and maintenance "
                     "manuals for bearings and expansion joints are complete in content and "
                     "in final binding for handover; a training session for the Employer's "
                     "maintenance staff on bearing and expansion joint maintenance is being "
                     "scheduled; contractual spare parts (bearing shims, joint seal sections) "
                     "are in transit and expected within 2 weeks. None of these matters is "
                     "considered to affect readiness for Taking-Over."),
            ("para", "5. CONCLUSION: The Works are substantially complete and fit for their "
                     "intended purpose. The items in Punch List PL-NRB4-001 are minor and, in "
                     "the Engineer's assessment, appropriately addressed by listing them for "
                     "completion within an agreed period following Taking-Over, in accordance "
                     "with Sub-Clause 10.1, rather than delaying Taking-Over."),
        ],
        closing_lines=["Signed jointly by: Meridian Engineering Consultants and Sagara "
                       "Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 4 -- PL-NRB4-001
    DocumentSpec(
        doc_id="PL-NRB4-001",
        title="Punch List — Taking-Over Inspection",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="PUNCH LIST",
        letterhead="ENGINEER",
        date="12-Sep-2023",
        from_="Meridian Engineering Consultants",
        to="Sagara Constructions Pvt. Ltd.",
        cc="National Highways Infrastructure Authority",
        subject="Punch List — Joint Inspection Report JIR-NRB4-001",
        body=[
            ("table", {
                "headers": ["Item", "Location", "Description", "Classification",
                            "Target Completion"],
                "rows": [
                    ["1", "Right bank approach, km 212+950 and km 213+020",
                     "Two traffic sign posts, positions marked, signs not yet installed",
                     "Minor", "27-Sep-2023 (15 days)"],
                    ["2", "Parapets, spans P4–P5, P5–P6, P6–P7",
                     "Surface abrasion/handling marks, touch-up painting required",
                     "Minor", "02-Oct-2023 (20 days)"],
                    ["3", "Deck, mid-span P5–P6",
                     "Localised drainage channel grading deficiency causing minor ponding; "
                     "regrading required over approximately 2m",
                     "Minor", "02-Oct-2023 (20 days)"],
                    ["4", "Documentation",
                     "As-built drawings outstanding for spans P6–P7 and P7–A2",
                     "Minor (documentation only)", "12-Oct-2023 (30 days)"],
                ],
            }),
            ("para", "CLASSIFICATION BASIS: None of the items above is a structural, safety, "
                     "or functional defect. Item 3 is the most significant item listed and is "
                     "assessed as a localised finishing deficiency not affecting deck "
                     "drainage performance overall or vehicle safety. No item on this list is "
                     "assessed as preventing beneficial use of the Works."),
            ("para", "This Punch List forms the basis of Outstanding Works Register "
                     "OWR-NRB4-001."),
        ],
        closing_lines=["Prepared by: Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # Document 5 -- OWR-NRB4-001
    DocumentSpec(
        doc_id="OWR-NRB4-001",
        title="Outstanding Works Register",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="OUTSTANDING WORKS REGISTER",
        letterhead="ENGINEER",
        date="12-Sep-2023",
        from_="Meridian Engineering Consultants",
        to="Sagara Constructions Pvt. Ltd.",
        cc="National Highways Infrastructure Authority",
        subject="Outstanding Works Register — Established Following Punch List PL-NRB4-001",
        body=[
            ("table", {
                "headers": ["Register ID", "Punch List Item", "Status", "Target Date",
                            "Responsible"],
                "rows": [
                    ["OWR-001-01", "PL-NRB4-001 Item 1 (signage)", "Open", "27-Sep-2023",
                     "Contractor"],
                    ["OWR-001-02", "PL-NRB4-001 Item 2 (parapet touch-up)", "Open",
                     "02-Oct-2023", "Contractor"],
                    ["OWR-001-03", "PL-NRB4-001 Item 3 (deck drainage regrading)", "Open",
                     "02-Oct-2023", "Contractor"],
                    ["OWR-001-04", "PL-NRB4-001 Item 4 (as-built drawings, 2 spans)", "Open",
                     "12-Oct-2023", "Contractor"],
                ],
            }),
            ("para", "This register will be updated as each item is completed and verified "
                     "by the Engineer, and will remain open for tracking purposes within the "
                     "Defects Notification Period (365 days from the date stated in the "
                     "Taking-Over Certificate, per Contract Data Section 3), notwithstanding "
                     "that the Works are considered ready for Taking-Over notwithstanding "
                     "these items."),
        ],
        closing_lines=["Maintained by: Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # Document 6 -- COMP-NRB4-001
    DocumentSpec(
        doc_id="COMP-NRB4-001",
        title="Minutes of Completion Meeting — Taking-Over",
        doc_type="MEETING_MINUTES",
        doc_type_tag="COMPLETION MEETING MINUTES",
        letterhead="ENGINEER",
        date="14-Sep-2023",
        from_="Resident Engineer, Meridian Engineering Consultants",
        to="Distribution list — Employer, Engineer, Contractor",
        extra_meta=[
            ("Meeting", "Completion Meeting — Taking-Over"),
            ("Venue", "NRB-4 Site Office, Left Bank Approach"),
            ("Present", "Er. Anand Vasker (Resident Engineer, Meridian Engineering "
                        "Consultants); Project Manager (Sagara Constructions Pvt. Ltd.); "
                        "Project Representative (National Highways Infrastructure "
                        "Authority)"),
        ],
        body=[
            ("heading", "1. JOINT INSPECTION REPORT AND PUNCH LIST:"),
            ("para", "The Engineer summarised JIR-NRB4-001, PL-NRB4-001, and OWR-NRB4-001. "
                     "All parties agreed the four listed items are minor, none is structural "
                     "or safety-related, and none prevents beneficial use of the Works. The "
                     "Contractor confirmed the target completion dates in OWR-NRB4-001 are "
                     "achievable and accepted responsibility for completing each item within "
                     "the Defects Notification Period."),
            ("heading", "2. EMPLOYER'S POSITION:"),
            ("para", "The Employer's representative confirmed no objection to Taking-Over "
                     "proceeding on this basis and noted the Application (CTR-NRB4-0198) was "
                     "made 18 days ahead of the revised Time for Completion of 23-Sep-2023."),
            ("heading", "3. TAKING-OVER CERTIFICATE:"),
            ("para", "The Engineer confirmed its intention to issue the Taking-Over "
                     "Certificate, listing the four Punch List items as outstanding work to "
                     "be completed within the periods in OWR-NRB4-001, in accordance with "
                     "Sub-Clause 10.1. Target issue date: on or before 22-Sep-2023, within "
                     "the 21-day Taking-Over Period under Contract Data Section 3."),
            ("heading", "4. HANDOVER MATTERS:"),
            ("para", "Contractor confirmed operation and maintenance manuals are in final "
                     "binding, training for the Employer's maintenance staff on bearing and "
                     "expansion joint maintenance is being scheduled for early October 2023, "
                     "and contractual spare parts remain in transit, expected within 2 weeks. "
                     "None of these matters affects the Taking-Over decision."),
            ("heading", "5. DEFECTS NOTIFICATION PERIOD:"),
            ("para", "All parties noted the Defects Notification Period of 365 days will run "
                     "from the date stated in the Taking-Over Certificate, per Contract Data "
                     "Section 3."),
        ],
        closing_lines=["Minutes recorded by: Resident Engineer, Meridian Engineering "
                       "Consultants"],
        scenario=SCENARIO,
    ),

    # Document 7 -- TOC-NRB4-001
    DocumentSpec(
        doc_id="TOC-NRB4-001",
        title="Taking-Over Certificate",
        doc_type="APPROVAL",
        doc_type_tag="CERTIFICATE",
        letterhead="ENGINEER",
        date="22-Sep-2023",
        from_="Engineer, Meridian Engineering Consultants",
        to="Sagara Constructions Pvt. Ltd.",
        cc="National Highways Infrastructure Authority",
        subject="Taking-Over Certificate — Nandira River Bridge Project, Package NRB-4",
        body=[
            ("para", "Issued pursuant to Sub-Clause 10.1, in response to the Contractor's "
                     "Application CTR-NRB4-0198 dated 05-Sep-2023, following Joint Inspection "
                     "Report JIR-NRB4-001, and within the 21-day Taking-Over Period under "
                     "Contract Data Section 3."),
            ("para", "1. CERTIFICATION: We certify that the Works — the bridge structure "
                     "(Abutment A1 to Abutment A2, all 8 spans) and associated approach works "
                     "— were complete in accordance with the Contract, save for the minor "
                     "items listed below, and fit for their intended purpose, with effect "
                     "from 22-Sep-2023."),
            ("para", "2. BASIS: This certification is supported by satisfactory static and "
                     "dynamic load testing (accepted by ENG-NRB4-0058, 01-Sep-2023), Joint "
                     "Inspection Report JIR-NRB4-001, and the absence of any structural, "
                     "safety, or functional defect identified during inspection."),
            ("para", "3. OUTSTANDING ITEMS: The following items, listed in Punch List "
                     "PL-NRB4-001 and tracked in Outstanding Works Register OWR-NRB4-001, "
                     "remain outstanding and shall be completed within the periods stated: "
                     "(1) traffic signage, right bank approach — by 27-Sep-2023; (2) parapet "
                     "touch-up painting, three locations — by 02-Oct-2023; (3) deck drainage "
                     "regrading, mid-span P5–P6 — by 02-Oct-2023; (4) as-built drawings, "
                     "spans P6–P7 and P7–A2 — by 12-Oct-2023. None of these items is "
                     "considered to affect the validity of this Certificate."),
            ("para", "4. DEFECTS NOTIFICATION PERIOD: The Defects Notification Period of 365 "
                     "days, per Contract Data Section 3, runs from the date of this "
                     "Certificate, 22-Sep-2023, and will accordingly expire 21-Sep-2024."),
            ("para", "5. TIME FOR COMPLETION: This Certificate is issued 1 day before the "
                     "revised Time for Completion of 23-Sep-2023 (per EOT-01, ENG-NRB4-0019). "
                     "No delay damages arise under Sub-Clause 8.7 or Contract Data Section "
                     "7."),
        ],
        closing_lines=["Signed: Engineer's Representative", "Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),
]
