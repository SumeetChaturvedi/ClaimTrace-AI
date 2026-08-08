"""Verbatim structured data for Scenario 6's 6 approved documents."""

from pdf_template import DocumentSpec

SCENARIO = 6

DOCUMENTS: list[DocumentSpec] = [

    # Document 1 -- CTR-NRB4-0098
    DocumentSpec(
        doc_id="CTR-NRB4-0098",
        title="Notice of Dissatisfaction — Engineer's Commercial Assessment ENG-NRB4-0038",
        doc_type="NOTICE",
        doc_type_tag="NOTICE OF DISSATISFACTION",
        letterhead="CONTRACTOR",
        date="25-Mar-2022",
        from_="Contractor, Commercial Manager, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        cc="National Highways Infrastructure Authority",
        subject="Notice of Dissatisfaction — Engineer's Commercial Assessment ENG-NRB4-0038 "
                "dated 04-Mar-2022",
        body=[
            ("para", "We refer to the Engineer's Commercial Assessment ENG-NRB4-0038 dated "
                     "04-Mar-2022, determining our Commercial Notice CTR-NRB4-0091 dated "
                     "10-Feb-2022 and rejecting the position set out in that notice and in "
                     "the supporting analysis we have reviewed, including Contract "
                     "Interpretation Memorandum CIM-NRB4-002."),
            ("para", "We confirm, for the avoidance of doubt, that we do not dispute any "
                     "factual or arithmetic matter recorded in ENG-NRB4-0038, the Financial "
                     "Calculation Sheet FCS-NRB4-011, or Interim Payment Certificate "
                     "IPC-NRB4-011. The value of Variation VO-NRB4-004, the cumulative "
                     "figures, and the amounts certified and paid are all agreed. Our "
                     "dissatisfaction is confined entirely to the Engineer's contractual "
                     "interpretation, namely: (a) that Sub-Clause 13.3 requires a Variation's "
                     "value to be treated identically to other work for Retention purposes; "
                     "and (b) that Contract Data Section 6's reference to \"each amount "
                     "otherwise due\" admits no distinction based on the nature or origin of "
                     "that amount. We maintain the interpretation set out in CTR-NRB4-0091 "
                     "remains the better reading of the Contract."),
            ("para", "Pursuant to Sub-Clause 20.4, we hereby give notice of our "
                     "dissatisfaction with ENG-NRB4-0038, within 28 days of its issue, and "
                     "confirm this dispute is referable to the Dispute Adjudication Board in "
                     "accordance with the Contract, should it not be resolved by other means "
                     "in the interim."),
            ("para", "We remain open to amicable discussion of this matter in accordance with "
                     "Sub-Clause 20.5 before any formal referral is pursued."),
        ],
        closing_lines=["Regards,", "Commercial Manager", "Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 2 -- NHIA-NRB4-COMM-004
    DocumentSpec(
        doc_id="NHIA-NRB4-COMM-004",
        title="Employer's Acknowledgement — Notice of Dissatisfaction CTR-NRB4-0098",
        doc_type="CORRESPONDENCE",
        doc_type_tag="EMPLOYER CORRESPONDENCE",
        letterhead="EMPLOYER",
        date="01-Apr-2022",
        from_="National Highways Infrastructure Authority",
        to="Sagara Constructions Pvt. Ltd.",
        cc="Meridian Engineering Consultants",
        subject="Acknowledgement — Notice of Dissatisfaction CTR-NRB4-0098",
        body=[
            ("para", "We acknowledge receipt of your Notice of Dissatisfaction CTR-NRB4-0098 "
                     "dated 25-Mar-2022, issued in respect of the Engineer's Commercial "
                     "Assessment ENG-NRB4-0038 dated 04-Mar-2022."),
            ("para", "We confirm the Notice was received within 28 days of ENG-NRB4-0038 and "
                     "is accordingly noted as validly and timely issued under Sub-Clause 20.4. "
                     "We note your confirmation that no factual or arithmetic matter is in "
                     "dispute, and that the matter is confined to the contractual "
                     "interpretation addressed in ENG-NRB4-0038 and Contract Interpretation "
                     "Memorandum CIM-NRB4-002."),
            ("para", "Our position, consistent with the Engineer's assessment, remains that "
                     "Retention was correctly applied to the full cumulative value certified "
                     "under IPC-NRB4-011, including the value of Variation VO-NRB4-004, and "
                     "that no repayment or interest is due. We are, as you have proposed, "
                     "willing to explore an amicable resolution of this matter under "
                     "Sub-Clause 20.5 before either Party takes further formal steps."),
        ],
        closing_lines=["Regards,", "National Highways Infrastructure Authority"],
        scenario=SCENARIO,
    ),

    # Document 3 -- LCM-NRB4-001
    DocumentSpec(
        doc_id="LCM-NRB4-001",
        title="Legal and Contracts Memorandum — Validity and Merits of Notice of "
              "Dissatisfaction CTR-NRB4-0098",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="LEGAL AND CONTRACTS MEMORANDUM",
        letterhead="ENGINEER",
        date="08-Apr-2022",
        from_="Meridian Engineering Consultants, Contracts Section",
        to="Project File",
        cc="National Highways Infrastructure Authority",
        subject="Notice of Dissatisfaction CTR-NRB4-0098 — Procedural and Substantive Review",
        body=[
            ("para", "1. PROCEDURAL VALIDITY: CTR-NRB4-0098 was issued 25-Mar-2022, 21 days "
                     "after ENG-NRB4-0038 (04-Mar-2022), within the 28-day period under "
                     "Sub-Clause 20.4. It identifies the determination in dispute with "
                     "sufficient particularity and confirms no factual matter is contested. "
                     "We assess the Notice as procedurally valid."),
            ("para", "2. SUBSTANTIVE REVIEW: We have re-examined the interpretive question "
                     "addressed in Contract Interpretation Memorandum CIM-NRB4-002 in light of "
                     "the specific grounds raised in CTR-NRB4-0098. The Contractor's position "
                     "rests on characterising Variation VO-NRB4-004 by reference to its cause "
                     "(an Employer-side ground condition) rather than its contractual "
                     "treatment once instructed and valued. Sub-Clause 13.3 draws no such "
                     "distinction: a Variation, once valued, is included in the amount due "
                     "under Sub-Clause 14.3 in the same manner as any other item. Contract "
                     "Data Section 6 similarly draws no distinction by origin. We find no "
                     "textual basis in the Contract for the interpretation advanced in "
                     "CTR-NRB4-0091 and CTR-NRB4-0098, and no provision that would support "
                     "treating any Variation differently from other certified work for "
                     "Retention purposes."),
            ("para", "3. CONCLUSION: The Notice of Dissatisfaction is procedurally valid and "
                     "properly before the Parties for resolution. On the merits, however, we "
                     "see no basis to depart from the determination in ENG-NRB4-0038. We "
                     "recommend the Employer maintain its position in any amicable discussion "
                     "under Sub-Clause 20.5, while remaining open to hearing any further "
                     "textual argument the Contractor may raise that has not already been "
                     "addressed in CIM-NRB4-002 or this memorandum."),
        ],
        closing_lines=["Prepared by: Contracts Section, Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # Document 4 -- SMM-NRB4-004
    DocumentSpec(
        doc_id="SMM-NRB4-004",
        title="Minutes of Senior Management Meeting No. 4 — Commercial Dispute Review",
        doc_type="MEETING_MINUTES",
        doc_type_tag="SENIOR MANAGEMENT MEETING MINUTES",
        letterhead="EMPLOYER",
        date="15-Apr-2022",
        from_="Project Representative, National Highways Infrastructure Authority",
        to="Distribution list — Employer, Engineer, Contractor senior management",
        extra_meta=[
            ("Meeting", "Senior Management Meeting No. 4"),
            ("Venue", "NHIA Project Office, Sector 9, Government Complex, Vantara City"),
            ("Present", "Project Representative (National Highways Infrastructure "
                        "Authority); Principal (Meridian Engineering Consultants); Director "
                        "(Sagara Constructions Pvt. Ltd.)"),
        ],
        body=[
            ("heading", "1. COMMERCIAL DISPUTE — RETENTION ON VO-NRB4-004:"),
            ("para", "The Engineer's Principal summarised the position: Notice of "
                     "Dissatisfaction CTR-NRB4-0098, confirmed procedurally valid in "
                     "LCM-NRB4-001, contests only the contractual interpretation underlying "
                     "ENG-NRB4-0038 and CIM-NRB4-002, with no factual or arithmetic matter in "
                     "dispute. The Contractor's Director confirmed the Contractor's position "
                     "remains as set out in CTR-NRB4-0091 and CTR-NRB4-0098, and expressed a "
                     "preference to attempt amicable resolution under Sub-Clause 20.5 before "
                     "any formal referral. The Employer's representative agreed to this "
                     "approach and confirmed the Employer's position, consistent with the "
                     "Engineer's assessment, remains unchanged. It was agreed the Contractor "
                     "would initiate without-prejudice correspondence proposing a discussion "
                     "meeting."),
            ("heading", "2. PROJECT BUDGET REVIEW:"),
            ("para", "The Employer's representative noted the project remains within the "
                     "approved Contract Amount of VTD 42,000,000, with Variation VO-NRB4-004 "
                     "and routine re-measurement tracking within contingency allowances; no "
                     "budget concerns raised."),
            ("heading", "3. STAFFING:"),
            ("para", "The Engineer confirmed a replacement quantity surveyor has joined the "
                     "Resident Engineer's team with effect from 01-Apr-2022, unrelated to the "
                     "matters above."),
            ("heading", "4. EQUIPMENT PLANNING:"),
            ("para", "The Contractor's Director noted planning for demobilisation of the "
                     "second tower crane following completion of girder erection works, "
                     "expected Q3 2022."),
            ("heading", "5. PROCUREMENT STATUS:"),
            ("para", "Contractor confirmed all major material procurement for the remaining "
                     "superstructure and pavement works is on schedule, with no outstanding "
                     "long-lead items."),
            ("heading", "6. NEXT MEETING:"),
            ("para", "To be scheduled following conclusion of the amicable discussion on the "
                     "retention matter, or in any event within six months."),
        ],
        closing_lines=["Minutes recorded by: Project Representative, National Highways "
                       "Infrastructure Authority"],
        scenario=SCENARIO,
    ),

    # Document 5 -- CTR-NRB4-0104
    DocumentSpec(
        doc_id="CTR-NRB4-0104",
        title="Without Prejudice Correspondence — Proposal for Amicable Discussion",
        doc_type="CORRESPONDENCE",
        doc_type_tag="WITHOUT PREJUDICE",
        letterhead="CONTRACTOR",
        date="22-Apr-2022",
        from_="Contractor, Commercial Manager, Sagara Constructions Pvt. Ltd.",
        to="National Highways Infrastructure Authority",
        cc="Meridian Engineering Consultants",
        subject="Without Prejudice — Proposal for Amicable Discussion, Retention on "
                "Variation VO-NRB4-004",
        body=[
            ("total_box", "WITHOUT PREJUDICE"),
            ("para", "Further to Senior Management Meeting SMM-NRB4-004 held 15-Apr-2022, and "
                     "in accordance with Sub-Clause 20.5, we propose a without-prejudice "
                     "meeting to discuss whether the matters raised in our Notice of "
                     "Dissatisfaction CTR-NRB4-0098 can be resolved by agreement, without "
                     "recourse to the Dispute Adjudication Board."),
            ("para", "For the purpose of this discussion only, and without prejudice to our "
                     "position as set out in CTR-NRB4-0091 and CTR-NRB4-0098, we would be "
                     "prepared to discuss the treatment of Retention on future Variations "
                     "prospectively, while reserving our position as to the VTD 29,535 "
                     "identified in respect of IPC-NRB4-011 specifically."),
            ("para", "We propose the meeting take place at the NRB-4 Site Office within four "
                     "weeks of this letter. This letter and any discussion arising from it "
                     "are without prejudice and shall not be referred to in any subsequent "
                     "Dispute Adjudication Board or arbitration proceedings, save as the "
                     "Parties may otherwise agree."),
        ],
        closing_lines=["Regards,", "Commercial Manager", "Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 6 -- DRPN-NRB4-001
    DocumentSpec(
        doc_id="DRPN-NRB4-001",
        title="Dispute Resolution Preparation Note — Retention Interpretation Dispute",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="DISPUTE RESOLUTION PREPARATION NOTE",
        letterhead="ENGINEER",
        date="29-Apr-2022",
        from_="Meridian Engineering Consultants, Contracts Section",
        to="National Highways Infrastructure Authority (Project File)",
        subject="Preparation Note — Retention Interpretation Dispute (VO-NRB4-004)",
        body=[
            ("para", "1. SUMMARY OF DISPUTE: The Contractor contends that the value of "
                     "Variation VO-NRB4-004 (VTD 590,700, approved under NHIA-NRB4-APR-006) "
                     "should be excluded from the Retention base applied under Interim "
                     "Payment Certificate IPC-NRB4-011, and claims VTD 29,535 plus interest. "
                     "No factual or arithmetic matter is in dispute; the disagreement is "
                     "confined to the interpretation of Sub-Clause 13.3 and Contract Data "
                     "Section 6."),
            ("para", "2. DOCUMENT RECORD: CTR-NRB4-0091 (Commercial Notice) → "
                     "NHIA-NRB4-COMM-003 (Employer preliminary response) → FCS-NRB4-011 / "
                     "PRE-NRB4-011 (calculation and register support) → CIM-NRB4-002 "
                     "(Engineer's interpretation memorandum) → ENG-NRB4-0038 (Engineer's "
                     "determination, rejecting the claim) → CTR-NRB4-0098 (Notice of "
                     "Dissatisfaction) → NHIA-NRB4-COMM-004 (Employer acknowledgement) → "
                     "LCM-NRB4-001 (procedural and substantive review, confirming "
                     "ENG-NRB4-0038) → CTR-NRB4-0104 (without-prejudice proposal for amicable "
                     "discussion)."),
            ("para", "3. ASSESSMENT OF MERITS: Both CIM-NRB4-002 and LCM-NRB4-001 "
                     "independently conclude that Sub-Clause 13.3 and Contract Data Section 6 "
                     "provide no basis to exclude a Variation's value from Retention, "
                     "regardless of the Variation's underlying cause. We are not aware of any "
                     "provision of the General Conditions, Particular Conditions, or Contract "
                     "Data that supports the Contractor's interpretation. In our assessment, "
                     "the Engineer's determination in ENG-NRB4-0038 remains the correct "
                     "contractual position, and the Notice of Dissatisfaction, while "
                     "procedurally valid, is unlikely to succeed on its merits should it "
                     "proceed to the Dispute Adjudication Board."),
            ("para", "4. STATUS AND NEXT STEPS: A without-prejudice discussion meeting has "
                     "been proposed by the Contractor (CTR-NRB4-0104) and is expected within "
                     "four weeks of that letter. No referral to the Dispute Adjudication "
                     "Board has yet been made by either Party. This note will be updated "
                     "following the outcome of the amicable discussion."),
        ],
        closing_lines=["Prepared by: Contracts Section, Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),
]
