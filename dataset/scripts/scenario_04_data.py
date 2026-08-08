"""Verbatim structured data for Scenario 4's 7 approved documents."""

from pdf_template import DocumentSpec

SCENARIO = 4

DOCUMENTS: list[DocumentSpec] = [

    # Document 1 -- STMT-NRB4-011
    DocumentSpec(
        doc_id="STMT-NRB4-011",
        title="Contractor's Monthly Statement No. 11",
        doc_type="PAYMENT",
        doc_type_tag="CONTRACTOR'S MONTHLY STATEMENT",
        letterhead="CONTRACTOR",
        date="03-Dec-2021",
        from_="Contractor, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        extra_meta=[("Period", "01-Nov-2021 to 30-Nov-2021")],
        subject="Monthly Statement No. 11, submitted in accordance with Sub-Clause 14.3",
        body=[
            ("para", "We submit our Statement for the above period as follows:"),
            ("para", "A. VALUE OF PERMANENT WORKS EXECUTED TO END OF PREVIOUS STATEMENT "
                     "(Statement No. 10, period ending 31-Oct-2021): VTD 24,150,000"),
            ("subheading", "B. VALUE OF WORK EXECUTED THIS PERIOD:"),
            ("table", {
                "rows": [
                    ["1.", "Girder erection, Piers P1–P4", "VTD 612,000"],
                    ["2.", "Approach road pavement, left bank", "VTD 398,300"],
                    ["3.", "Superstructure deck slab, Piers P1–P2", "VTD 470,000"],
                    ["4.", "Miscellaneous Bill of Quantities items", "VTD 240,000"],
                    ["", "Subtotal, routine work this period:", "VTD 1,720,300"],
                ],
                "right_align_cols": [2],
                "bold_last_row": True,
            }),
            ("para", "C. VARIATION VO-NRB4-004 (Pier P3 Pile Cap Redesign): As approved by the "
                     "Employer per NHIA-NRB4-APR-006 dated 25-Nov-2021, following the "
                     "Engineer's assessment ENG-NRB4-0031 dated 05-Nov-2021 of our quotation "
                     "CTR-NRB4-0067: VTD 590,700"),
            ("para", "D. TOTAL VALUE OF WORK EXECUTED THIS PERIOD (B + C): VTD 2,311,000"),
            ("para", "E. CUMULATIVE VALUE OF WORK EXECUTED TO DATE (A + D): VTD 26,461,000"),
            ("para", "We request that Retention be applied and the amount due under this "
                     "Statement be certified in accordance with Sub-Clause 14.3 and Particular "
                     "Conditions Part F.2."),
            ("para", "Supporting measurement records and delivery documentation for the items "
                     "above are available for the Engineer's verification."),
        ],
        closing_lines=["Submitted by: Quantity Surveyor, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 2 -- QMS-NRB4-011
    DocumentSpec(
        doc_id="QMS-NRB4-011",
        title="Quantity Measurement Summary — Statement No. 11",
        doc_type="MEASUREMENT",
        doc_type_tag="QUANTITY MEASUREMENT SUMMARY",
        letterhead="ENGINEER",
        date="10-Dec-2021",
        from_="Meridian Engineering Consultants",
        to="Project File",
        cc="Sagara Constructions Pvt. Ltd.",
        subject="Measurement in Support of Statement STMT-NRB4-011",
        body=[
            ("para", "Measurement carried out against Statement STMT-NRB4-011 dated "
                     "03-Dec-2021, in accordance with Sub-Clause 14.3."),
            ("subheading", "ITEM-BY-ITEM MEASUREMENT:"),
            ("para", "1. Girder erection, Piers P1–P4: Measured quantity confirms claimed "
                     "value. Accepted: VTD 612,000."),
            ("para", "2. Approach road pavement, left bank: Site measurement of compacted "
                     "pavement area indicates a lesser progressed quantity than claimed. "
                     "Adjusted: VTD 391,800 (claimed VTD 398,300)."),
            ("para", "3. Superstructure deck slab, Piers P1–P2: Measured quantity confirms "
                     "claimed value. Accepted: VTD 470,000."),
            ("para", "4. Miscellaneous Bill of Quantities items: Measured quantities confirm "
                     "claimed value. Accepted: VTD 240,000."),
            ("para", "5. Variation VO-NRB4-004: The value of VTD 590,700 is not subject to "
                     "further measurement under this Statement, being the fixed valuation "
                     "already approved by the Employer under NHIA-NRB4-APR-006 dated "
                     "25-Nov-2021, following the Engineer's assessment ENG-NRB4-0031 dated "
                     "05-Nov-2021. Included at approved value: VTD 590,700."),
            ("subheading", "REVISED VALUE OF WORK EXECUTED THIS PERIOD:"),
            ("table", {
                "rows": [
                    ["Routine work (measured)", "VTD 1,713,800"],
                    ["Variation VO-NRB4-004 (approved value)", "VTD 590,700"],
                    ["Total this period", "VTD 2,304,500"],
                ],
                "right_align_cols": [1],
                "bold_last_row": True,
            }),
            ("para", "REVISED CUMULATIVE VALUE OF WORK EXECUTED TO DATE: VTD 24,150,000 (to "
                     "end Statement No. 10) + VTD 2,304,500 = VTD 26,454,500"),
            ("para", "This measurement forms the basis for Interim Payment Certificate No. "
                     "11."),
        ],
        closing_lines=["Prepared by: Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # Document 3 -- IPC-NRB4-011
    DocumentSpec(
        doc_id="IPC-NRB4-011",
        title="Interim Payment Certificate No. 11",
        doc_type="PAYMENT",
        doc_type_tag="INTERIM PAYMENT CERTIFICATE",
        letterhead="ENGINEER",
        date="17-Dec-2021",
        from_="Engineer, Meridian Engineering Consultants",
        to="National Highways Infrastructure Authority",
        cc="Sagara Constructions Pvt. Ltd.",
        extra_meta=[
            ("Period", "01-Nov-2021 to 30-Nov-2021"),
            ("Statement Reference", "STMT-NRB4-011, dated 03-Dec-2021"),
        ],
        subject="Interim Payment Certificate No. 11",
        body=[
            ("para", "Issued in accordance with Sub-Clause 14.3, as replaced by Particular "
                     "Conditions Part F.2, within 21 days of the Statement date of "
                     "03-Dec-2021, on the basis of measurement recorded in QMS-NRB4-011 dated "
                     "10-Dec-2021."),
            ("subheading", "CERTIFICATION SUMMARY:"),
            ("table", {
                "rows": [
                    ["Cumulative value of work executed to date (per QMS-NRB4-011), "
                     "including Variation VO-NRB4-004:", "VTD 26,454,500"],
                    ["Less: Retention at 5% of cumulative value (Contract Data Section 6; "
                     "limit of Retention Money VTD 2,100,000 not reached at this cumulative "
                     "value):", "VTD 1,322,725"],
                    ["Cumulative amount due, net of Retention:", "VTD 25,131,775"],
                    ["Less: Amount previously certified, net of Retention (Interim Payment "
                     "Certificate No. 10, cumulative):", "VTD 22,942,500"],
                    ["GROSS AMOUNT DUE UNDER THIS CERTIFICATE:", "VTD 2,189,275"],
                    ["Less: Works Contract Tax deducted at source, 2% of the gross amount "
                     "due under this Certificate, per applicable Vantaran statutory "
                     "requirements (not a Contract deduction):", "VTD 43,786"],
                    ["NET AMOUNT CERTIFIED FOR PAYMENT — CERTIFICATE NO. 11:", "VTD 2,145,489"],
                ],
                "right_align_cols": [1],
                "bold_last_row": True,
            }),
            ("para", "NOTE ON VARIATION VO-NRB4-004: The value of VTD 590,700 is included in "
                     "the cumulative value of work executed to date above, being the fixed "
                     "sum approved by the Employer under NHIA-NRB4-APR-006 dated 25-Nov-2021. "
                     "No further quantity or valuation adjustment has been made to this item "
                     "at certification."),
            ("para", "PAYMENT DUE DATE: In accordance with Particular Conditions Part F.2, "
                     "the Employer shall pay the amount certified within 56 days of the "
                     "Statement date, being on or before 28-Jan-2022."),
        ],
        closing_lines=["Signed: Engineer's Representative", "Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),

    # Document 4 -- MOM-NRB4-023
    DocumentSpec(
        doc_id="MOM-NRB4-023",
        title="Minutes of Monthly Progress Meeting No. 23",
        doc_type="MEETING_MINUTES",
        doc_type_tag="PROGRESS MEETING MINUTES",
        letterhead="ENGINEER",
        date="20-Dec-2021",
        from_="Resident Engineer, Meridian Engineering Consultants",
        to="Distribution list — Employer, Engineer, Contractor",
        extra_meta=[
            ("Meeting", "Monthly Progress Meeting No. 23"),
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
            ("para", "Minutes of Meeting No. 22 confirmed without amendment."),
            ("heading", "2. PROGRESS SUMMARY:"),
            ("para", "Girder erection now complete at Piers P1–P4. Pier P3 pile cap works, "
                     "including the varied works under VO-NRB4-004, substantially complete; "
                     "concrete pour for the enlarged zone carried out 06-Dec-2021, witnessed "
                     "by the Engineer's Representative, Hold Point (d) cleared. Approach road "
                     "pavement works on the left bank continuing."),
            ("heading", "3. INTERIM PAYMENT CERTIFICATE NO. 11:"),
            ("para", "The Engineer confirmed issue of IPC-NRB4-011 on 17-Dec-2021, certifying "
                     "a net amount of VTD 2,145,489, including the approved value of Variation "
                     "VO-NRB4-004 (VTD 590,700) and reflecting a minor measured adjustment to "
                     "the claimed pavement quantity (QMS-NRB4-011). The Employer's "
                     "representative confirmed payment processing was underway and on track "
                     "for the due date of 28-Jan-2022 under Particular Conditions Part F.2."),
            ("heading", "4. QUALITY:"),
            ("para", "Cube test results for November pours reported satisfactory across all "
                     "locations; no non-conformances raised."),
            ("heading", "5. PROCUREMENT:"),
            ("para", "Contractor confirmed the third precast girder segment batch delivered "
                     "08-Dec-2021, ahead of schedule."),
            ("heading", "6. HEALTH AND SAFETY:"),
            ("para", "No lost-time incidents reported for the period."),
            ("heading", "7. NEXT MEETING:"),
            ("para", "Scheduled for 20-Jan-2022."),
        ],
        closing_lines=["Minutes recorded by: Resident Engineer, Meridian Engineering "
                       "Consultants"],
        scenario=SCENARIO,
    ),

    # Document 5 -- NHIA-NRB4-PAY-011
    DocumentSpec(
        doc_id="NHIA-NRB4-PAY-011",
        title="Employer's Payment Advice — Interim Payment Certificate No. 11",
        doc_type="PAYMENT",
        doc_type_tag="EMPLOYER'S PAYMENT ADVICE",
        letterhead="EMPLOYER",
        date="26-Jan-2022",
        from_="National Highways Infrastructure Authority",
        to="Sagara Constructions Pvt. Ltd.",
        cc="Meridian Engineering Consultants",
        subject="Payment Advice — Interim Payment Certificate No. 11",
        body=[
            ("para", "We refer to Interim Payment Certificate IPC-NRB4-011 dated 17-Dec-2021, "
                     "certifying a net amount of VTD 2,145,489 for the period 01-Nov-2021 to "
                     "30-Nov-2021, inclusive of the approved value of Variation VO-NRB4-004 "
                     "(VTD 590,700, per NHIA-NRB4-APR-006 dated 25-Nov-2021)."),
            ("para", "We confirm that payment of VTD 2,145,489 has been processed for transfer "
                     "to the Contractor's designated bank account and will be credited within "
                     "the Employer's Payment Period of 56 days from the Statement date of "
                     "03-Dec-2021, being on or before 28-Jan-2022, in accordance with "
                     "Particular Conditions Part F.2. As payment is made within this period, "
                     "no interest under Contract Data Section 8 arises in respect of this "
                     "Certificate."),
            ("para", "A bank transfer confirmation will follow separately upon completion of "
                     "the transfer."),
        ],
        closing_lines=["Regards,", "National Highways Infrastructure Authority"],
        scenario=SCENARIO,
    ),

    # Document 6 -- BTC-NRB4-011
    DocumentSpec(
        doc_id="BTC-NRB4-011",
        title="Bank Transfer Confirmation — Interim Payment Certificate No. 11",
        doc_type="PAYMENT",
        doc_type_tag="BANK TRANSFER CONFIRMATION",
        letterhead="EMPLOYER",
        date="27-Jan-2022",
        from_="National Highways Infrastructure Authority, Finance Section",
        to="Sagara Constructions Pvt. Ltd.",
        cc="Meridian Engineering Consultants",
        subject="Confirmation of Payment — Interim Payment Certificate No. 11",
        body=[
            ("para", "We confirm that a bank transfer of VTD 2,145,489 was executed on "
                     "27-Jan-2022 to the Contractor's designated account, in settlement of "
                     "Interim Payment Certificate IPC-NRB4-011 dated 17-Dec-2021."),
            ("para", "Transaction reference: NHIA-TXN-2022-0114"),
            ("para", "Amount transferred: VTD 2,145,489"),
            ("para", "Value date: 27-Jan-2022"),
            ("para", "This payment falls within the 56-day Employer Payment Period from the "
                     "Statement date of 03-Dec-2021 (due by 28-Jan-2022), in accordance with "
                     "Particular Conditions Part F.2."),
        ],
        closing_lines=["Regards,", "Finance Section", "National Highways Infrastructure "
                       "Authority"],
        scenario=SCENARIO,
    ),

    # Document 7 -- CTR-NRB4-0084
    DocumentSpec(
        doc_id="CTR-NRB4-0084",
        title="Contractor's Acknowledgement of Payment — Interim Payment Certificate No. 11",
        doc_type="CORRESPONDENCE",
        doc_type_tag="CORRESPONDENCE",
        letterhead="CONTRACTOR",
        date="28-Jan-2022",
        from_="Contractor, Sagara Constructions Pvt. Ltd.",
        to="National Highways Infrastructure Authority",
        cc="Meridian Engineering Consultants",
        subject="Acknowledgement of Payment — Interim Payment Certificate No. 11",
        body=[
            ("para", "We acknowledge receipt of VTD 2,145,489 on 27-Jan-2022 (BTC-NRB4-011), "
                     "in settlement of Interim Payment Certificate IPC-NRB4-011, within the "
                     "56-day period provided under Particular Conditions Part F.2. We confirm "
                     "this matches the amount certified by the Engineer."),
            ("para", "We note the measurement adjustment to the approach road pavement item "
                     "recorded in QMS-NRB4-011 (VTD 391,800 measured against VTD 398,300 "
                     "claimed) and do not dispute this adjustment; the difference will be "
                     "picked up in next month's Statement as the pavement works progress "
                     "further."),
            ("para", "We confirm no further comment on Interim Payment Certificate No. 11, "
                     "including the treatment of Variation VO-NRB4-004 at its approved value "
                     "of VTD 590,700."),
        ],
        closing_lines=["Regards,", "Quantity Surveyor", "Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),
]
