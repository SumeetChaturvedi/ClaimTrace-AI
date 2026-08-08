"""Verbatim structured data for Scenario 5's 7 approved documents."""

from pdf_template import DocumentSpec

SCENARIO = 5

DOCUMENTS: list[DocumentSpec] = [

    # Document 1 -- CTR-NRB4-0091
    DocumentSpec(
        doc_id="CTR-NRB4-0091",
        title="Contractor's Commercial Notice — Retention Treatment of Variation VO-NRB4-004",
        doc_type="NOTICE",
        doc_type_tag="CONTRACTOR COMMERCIAL NOTICE",
        letterhead="CONTRACTOR",
        date="10-Feb-2022",
        from_="Contractor, Commercial Manager, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        cc="National Highways Infrastructure Authority",
        subject="Commercial Notice — Retention Applied to Variation VO-NRB4-004, Interim "
                "Payment Certificate No. 11",
        body=[
            ("para", "Having reviewed our commercial records following receipt of payment "
                     "under Interim Payment Certificate IPC-NRB4-011 (confirmed by Employer's "
                     "Payment Advice NHIA-NRB4-PAY-011 and Bank Transfer Confirmation "
                     "BTC-NRB4-011, both dated January 2022), we raise the following "
                     "commercial notice."),
            ("para", "IPC-NRB4-011 applied Retention at 5 per cent to the full cumulative "
                     "value of work executed to date, including the value of Variation "
                     "VO-NRB4-004 (VTD 590,700). We do not consider this correct. Variation "
                     "VO-NRB4-004 compensates the Contractor for costs necessitated by ground "
                     "conditions arising from the Employer's own utility relocation works — it "
                     "is, in substance, a reimbursement of costs occasioned by a matter "
                     "outside the Contractor's control, rather than \"value of Permanent Works "
                     "executed\" of the kind Retention under Contract Data Section 6 is "
                     "intended to secure performance of. We submit that the value of "
                     "Variation VO-NRB4-004 should be excluded from the base to which "
                     "Retention is applied."),
            ("para", "On this basis, Retention on IPC-NRB4-011 should have been calculated as "
                     "follows:"),
            ("table", {
                "rows": [
                    ["Cumulative value of work executed to date, excluding Variation "
                     "VO-NRB4-004 (VTD 26,454,500 - VTD 590,700):", "VTD 25,863,800"],
                    ["Retention at 5 per cent:", "VTD 1,293,190"],
                    ["Retention actually applied under IPC-NRB4-011:", "VTD 1,322,725"],
                    ["Amount, in our view, wrongly retained:", "VTD 29,535"],
                ],
                "right_align_cols": [1],
                "bold_last_row": True,
            }),
            ("para", "We claim repayment of VTD 29,535, together with interest under "
                     "Contract Data Section 8 (12 per cent per annum, compounded monthly) "
                     "from 27-Jan-2022 (the date of the Bank Transfer Confirmation "
                     "BTC-NRB4-011) until the date of actual repayment, on the basis that "
                     "this sum remains an amount due and unpaid."),
            ("para", "We raise this matter not only in respect of IPC-NRB4-011, but to "
                     "establish the correct treatment for any future Variations valued and "
                     "certified under the Contract."),
        ],
        closing_lines=["Regards,", "Commercial Manager", "Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 2 -- NHIA-NRB4-COMM-003
    DocumentSpec(
        doc_id="NHIA-NRB4-COMM-003",
        title="Employer's Response — Commercial Notice CTR-NRB4-0091",
        doc_type="CORRESPONDENCE",
        doc_type_tag="EMPLOYER CORRESPONDENCE",
        letterhead="EMPLOYER",
        date="18-Feb-2022",
        from_="National Highways Infrastructure Authority",
        to="Meridian Engineering Consultants",
        cc="Sagara Constructions Pvt. Ltd.",
        subject="Commercial Notice CTR-NRB4-0091 — Retention on Variation VO-NRB4-004",
        body=[
            ("para", "We refer to the Contractor's Commercial Notice CTR-NRB4-0091 dated "
                     "10-Feb-2022, disputing the application of Retention to Variation "
                     "VO-NRB4-004 within Interim Payment Certificate IPC-NRB4-011."),
            ("para", "Our preliminary view is that Retention was correctly applied in "
                     "accordance with Contract Data Section 6 and Sub-Clause 14.3, and that "
                     "nothing in the Contract distinguishes Variations from other work for "
                     "Retention purposes. However, given the Contractor has raised this as a "
                     "matter of general application to future Variations, we consider it "
                     "appropriate for the Engineer to provide a formal commercial assessment "
                     "of the contractual position before we respond substantively."),
            ("para", "We would be grateful for the Engineer's assessment in due course."),
            ("para", "Separately, and unrelated to this matter, we confirm receipt of the "
                     "Contractor's notice of renewal of the Contractor's All Risks insurance "
                     "policy for the period from 15-Jan-2022, and have no comment on that "
                     "renewal."),
        ],
        closing_lines=["Regards,", "National Highways Infrastructure Authority"],
        scenario=SCENARIO,
    ),

    # Document 3 -- FCS-NRB4-011
    DocumentSpec(
        doc_id="FCS-NRB4-011",
        title="Financial Calculation Sheet — Retention Comparison, IPC-11",
        doc_type="MEASUREMENT",
        doc_type_tag="FINANCIAL CALCULATION SHEET",
        letterhead="ENGINEER",
        date="22-Feb-2022",
        from_="Meridian Engineering Consultants",
        to="Project File",
        cc="National Highways Infrastructure Authority; Sagara Constructions Pvt. Ltd.",
        subject="Retention Calculation Comparison — IPC-NRB4-011",
        body=[
            ("para", "Prepared in support of the Engineer's assessment of Commercial Notice "
                     "CTR-NRB4-0091."),
            ("subheading", "AS CERTIFIED (IPC-NRB4-011):"),
            ("table", {
                "rows": [
                    ["Cumulative value of work executed to date (including Variation "
                     "VO-NRB4-004):", "VTD 26,454,500"],
                    ["Retention at 5 per cent of cumulative value:", "VTD 1,322,725"],
                ],
                "right_align_cols": [1],
            }),
            ("subheading", "AS PROPOSED BY CONTRACTOR (CTR-NRB4-0091):"),
            ("table", {
                "rows": [
                    ["Cumulative value of work executed to date, excluding Variation "
                     "VO-NRB4-004:", "VTD 25,863,800"],
                    ["Retention at 5 per cent of cumulative value (Variation excluded from "
                     "base):", "VTD 1,293,190"],
                ],
                "right_align_cols": [1],
            }),
            ("total_box", "DIFFERENCE (amount in dispute): VTD 29,535"),
            ("para", "Note: this figure equals exactly 5 per cent of the value of Variation "
                     "VO-NRB4-004 (VTD 590,700), confirming that the two calculations differ "
                     "solely as to whether the Variation forms part of the Retention base, "
                     "and not as to any measured quantity, rate, or arithmetic step. No error "
                     "has been identified in either calculation on its own terms; the "
                     "disputed amount arises entirely from a difference in contractual "
                     "interpretation."),
        ],
        closing_lines=["Prepared by: Meridian Engineering Consultants, Commercial Section"],
        scenario=SCENARIO,
    ),

    # Document 4 -- PRE-NRB4-011
    DocumentSpec(
        doc_id="PRE-NRB4-011",
        title="Payment Register Extract — Certificates No. 09 to No. 11",
        doc_type="PAYMENT",
        doc_type_tag="PAYMENT REGISTER EXTRACT",
        letterhead="ENGINEER",
        date="22-Feb-2022",
        from_="Meridian Engineering Consultants",
        to="Project File",
        cc="National Highways Infrastructure Authority; Sagara Constructions Pvt. Ltd.",
        subject="Payment Register Extract — Interim Payment Certificates No. 09–11",
        body=[
            ("table", {
                "headers": ["Certificate", "Period Ending", "Cumulative Value",
                            "Retention (5%)", "Cumulative Net"],
                "rows": [
                    ["IPC-NRB4-009", "30-Sep-2021", "VTD 22,480,000", "VTD 1,124,000",
                     "VTD 21,356,000"],
                    ["IPC-NRB4-010", "31-Oct-2021", "VTD 24,150,000", "VTD 1,207,500",
                     "VTD 22,942,500"],
                    ["IPC-NRB4-011", "30-Nov-2021", "VTD 26,454,500", "VTD 1,322,725",
                     "VTD 25,131,775"],
                ],
                "right_align_cols": [2, 3, 4],
            }),
            ("para", "All three certificates were issued within the 21-day period under "
                     "Particular Conditions Part F.2, and all associated payments were made "
                     "within the 56-day Employer Payment Period; no interest under Contract "
                     "Data Section 8 has arisen on any certificate in this extract. Variation "
                     "VO-NRB4-004 first appears in the cumulative value at IPC-NRB4-011."),
            ("para", "Other certified items within this period include routine progress at "
                     "Piers P1–P5, approach road pavement, and superstructure works; no other "
                     "Variation has been certified in Certificates No. 09–11."),
        ],
        closing_lines=["Prepared by: Meridian Engineering Consultants, Commercial Section"],
        scenario=SCENARIO,
    ),

    # Document 5 -- CIM-NRB4-002
    DocumentSpec(
        doc_id="CIM-NRB4-002",
        title="Contract Interpretation Memorandum — Retention and Variations",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="CONTRACT INTERPRETATION MEMORANDUM",
        letterhead="ENGINEER",
        date="28-Feb-2022",
        from_="Meridian Engineering Consultants, Contracts Section",
        to="Project File",
        cc="National Highways Infrastructure Authority",
        subject="Contract Interpretation — Application of Retention to Variation Values",
        body=[
            ("para", "1. QUESTION: Whether the value of a Variation, once instructed under "
                     "Sub-Clause 13.1 and valued under Sub-Clause 13.3, forms part of the base "
                     "to which Retention under Contract Data Section 6 applies, as raised in "
                     "Commercial Notice CTR-NRB4-0091."),
            ("subheading", "2. CONTRACTUAL PROVISIONS CONSIDERED:"),
            ("bullet", "Sub-Clause 13.3 provides that the value of a Variation, once agreed or "
                       "determined, is to be included in the amount certified as due to the "
                       "Contractor. It establishes no separate payment mechanism outside "
                       "Sub-Clause 14.3 and no distinct treatment for Retention purposes."),
            ("bullet", "Sub-Clause 14.3 governs the Contractor's Statement and the amount to "
                       "be certified, without distinguishing the source of the value "
                       "comprising that amount (original Bill of Quantities items, "
                       "re-measured items, or Variations)."),
            ("bullet", "Contract Data Section 6 states Retention at 5 per cent \"of each "
                       "amount otherwise due,\" without qualification or carve-out for any "
                       "category of work."),
            ("bullet", "Particular Conditions Part E (Variation approval threshold and "
                       "response time) addresses procedural matters — authority to approve a "
                       "Variation and the period for response — and contains no provision "
                       "regarding Retention or payment mechanics."),
            ("para", "3. ANALYSIS: There is no basis in the General Conditions, Particular "
                     "Conditions, or Contract Data for treating a Variation's value as "
                     "falling outside \"each amount otherwise due\" for Retention purposes. "
                     "The Contractor's characterisation of Variation VO-NRB4-004 as a "
                     "\"reimbursement\" rather than \"value of work executed\" does not alter "
                     "its contractual treatment: Sub-Clause 13.3 values it, and Sub-Clause "
                     "14.3 certifies it, in the same manner as any other item comprising the "
                     "amount due. The origin or cause of a Variation (whether an Employer "
                     "instruction, an unforeseen condition, or otherwise) has no bearing on "
                     "how its value is treated once certified."),
            ("para", "4. CONCLUSION: The value of Variation VO-NRB4-004 is properly included "
                     "in the Retention base, and the calculation in IPC-NRB4-011 reflects the "
                     "correct application of Contract Data Section 6. No basis exists to "
                     "exclude it."),
        ],
        closing_lines=["Prepared by: Contracts Section, Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # Document 6 -- ENG-NRB4-0038
    DocumentSpec(
        doc_id="ENG-NRB4-0038",
        title="Engineer's Commercial Assessment — Commercial Notice CTR-NRB4-0091",
        doc_type="APPROVAL",
        doc_type_tag="ENGINEER'S COMMERCIAL ASSESSMENT",
        letterhead="ENGINEER",
        date="04-Mar-2022",
        from_="Engineer, Meridian Engineering Consultants",
        to="Contractor, Sagara Constructions Pvt. Ltd.",
        cc="National Highways Infrastructure Authority",
        subject="Assessment — Commercial Notice CTR-NRB4-0091 — Retention on Variation "
                "VO-NRB4-004",
        body=[
            ("para", "We refer to Commercial Notice CTR-NRB4-0091 dated 10-Feb-2022, the "
                     "Financial Calculation Sheet FCS-NRB4-011, the Payment Register Extract "
                     "PRE-NRB4-011, and our Contract Interpretation Memorandum CIM-NRB4-002, "
                     "all dated February 2022."),
            ("para", "1. RETENTION: We do not accept that Variation VO-NRB4-004 should be "
                     "excluded from the Retention base applied under Interim Payment "
                     "Certificate IPC-NRB4-011. Sub-Clause 13.3 provides that the value of a "
                     "Variation is included in the amount certified as due under Sub-Clause "
                     "14.3, without distinction as to the origin of that value. Contract Data "
                     "Section 6 applies Retention to \"each amount otherwise due\" without "
                     "qualification, and no provision of the General Conditions, Particular "
                     "Conditions, or Contract Data exempts Variations from Retention. The "
                     "characterisation of Variation VO-NRB4-004 as reimbursement rather than "
                     "value of work executed does not alter its treatment once certified. We "
                     "confirm the Retention of VTD 1,322,725 applied under IPC-NRB4-011, "
                     "calculated on the full cumulative value of VTD 26,454,500 including the "
                     "Variation, is correct."),
            ("para", "2. INTEREST: As no amount was wrongly retained, no amount is \"due and "
                     "unpaid\" within the meaning of Contract Data Section 8, and no basis "
                     "exists for interest to accrue on the VTD 29,535 identified in "
                     "CTR-NRB4-0091 or on any other sum in respect of IPC-NRB4-011. We note "
                     "separately, and without needing to determine it, that payment under "
                     "IPC-NRB4-011 was in any event made within the 56-day period confirmed "
                     "by Bank Transfer Confirmation BTC-NRB4-011, so no late payment has "
                     "occurred in respect of this Certificate on any view."),
            ("para", "3. DETERMINATION: Commercial Notice CTR-NRB4-0091 is rejected in full. "
                     "The Retention applied under IPC-NRB4-011 remains as certified, and no "
                     "repayment or interest is due. This determination applies equally to the "
                     "treatment of any future Variation certified under the Contract, absent a "
                     "contrary instruction agreed by both Parties."),
        ],
        closing_lines=["Signed: Engineer's Representative", "Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # Document 7 -- MOM-NRB4-026
    DocumentSpec(
        doc_id="MOM-NRB4-026",
        title="Minutes of Monthly Progress Meeting No. 26",
        doc_type="MEETING_MINUTES",
        doc_type_tag="PROGRESS MEETING MINUTES",
        letterhead="ENGINEER",
        date="20-Mar-2022",
        from_="Resident Engineer, Meridian Engineering Consultants",
        to="Distribution list — Employer, Engineer, Contractor",
        extra_meta=[
            ("Meeting", "Monthly Progress Meeting No. 26"),
            ("Venue", "NRB-4 Site Office, Left Bank Approach"),
            ("Present", "Er. Anand Vasker (Resident Engineer, Meridian Engineering "
                        "Consultants); Project Manager and Commercial Manager (Sagara "
                        "Constructions Pvt. Ltd.); Project Representative (National Highways "
                        "Infrastructure Authority)"),
        ],
        body=[
            ("para", "Issued in accordance with Particular Conditions Part B.2, within 5 "
                     "working days of the meeting."),
            ("heading", "1. PREVIOUS MINUTES:"),
            ("para", "Minutes of Meeting No. 25 confirmed without amendment."),
            ("heading", "2. PROGRESS SUMMARY:"),
            ("para", "Superstructure works across all piers approximately 94 per cent "
                     "complete. Deck slab pours ongoing at Piers P5–P7."),
            ("heading", "3. COMMERCIAL NOTICE CTR-NRB4-0091:"),
            ("para", "The Engineer confirmed issue of its assessment ENG-NRB4-0038 on "
                     "04-Mar-2022, rejecting the Contractor's claim that Variation VO-NRB4-004 "
                     "should be excluded from the Retention base, and rejecting the associated "
                     "interest claim. The Contractor noted it was reviewing the assessment and "
                     "reserved its position as to whether to pursue the matter further, but "
                     "confirmed no immediate further submission. The Employer's "
                     "representative noted the Employer's preliminary position in "
                     "NHIA-NRB4-COMM-003 was consistent with the Engineer's assessment."),
            ("heading", "4. PROCUREMENT:"),
            ("para", "Contractor confirmed receipt and payment of an invoice from its "
                     "formwork hire supplier for the extended hire period at Pier P3, "
                     "unrelated to the matters above."),
            ("heading", "5. INSURANCE:"),
            ("para", "Contractor confirmed the Contractor's All Risks policy renewal noted in "
                     "NHIA-NRB4-COMM-003 remains in effect, no further action required."),
            ("heading", "6. HEALTH AND SAFETY:"),
            ("para", "No lost-time incidents reported for the period."),
            ("heading", "7. NEXT MEETING:"),
            ("para", "Scheduled for 20-Apr-2022."),
        ],
        closing_lines=["Minutes recorded by: Resident Engineer, Meridian Engineering "
                       "Consultants"],
        scenario=SCENARIO,
    ),
]
