"""Verbatim structured data for the 4 Contract Package documents of Project
3 (Phase 4 Task 04 — Scenario 12), transcribed exactly from the persisted
source files in backend/storage/contracts/KFI2-*.txt. Content matches those
.txt files paragraph-for-paragraph; only the layout differs (heading/
subheading/para blocks for PDF rendering here, vs. the plain "number on its
own line" format ClauseParser expects there).

This project (Kestrel Flyover Interchange Project — Package KFI-2) is
entirely independent of the Nandira River Bridge Project (Dataset V2,
project_id=2): new Employer (Kaldera Metropolitan Development Authority),
new Engineer (Ashgrove Infrastructure Consultants), new Contractor (Rennick
Builders Ltd.), new country/city (Republic of Kaldera / Rostam City), new
currency (Kaldera Dollar, KLD), new contract number
(KMDA/KFI2/CW/2019-04), and entirely fresh document-id and clause-number
conventions -- no identifier, reference, or clause number here was reused
from Scenarios 1-11 or the NRB4 contract package. Uses the letterhead_registry/
project_line DocumentSpec fields added in pdf_template.py for exactly this
purpose (independent-project branding); every existing NRB4 DocumentSpec
leaves those fields unset and is unaffected.

These 4 documents use DocumentType CONTRACT (the same canonical type
NRB4-GC-2020 etc. use) and are letterheaded "JOINT", mirroring
contracts_data.py's own precedent exactly.
"""

from pdf_template import DocumentSpec
from reportlab.lib import colors

KFI2_PROJECT_LINE = "Kestrel Flyover Interchange Project — Package KFI-2"
KFI2_CONTRACT_NO = "KMDA/KFI2/CW/2019-04"

KFI2_LETTERHEADS = {
    "EMPLOYER": dict(
        wordmark="KMDA",
        subtext="Kaldera Metropolitan Development Authority",
        legal_name="Kaldera Metropolitan Development Authority",
        address=["KMDA Project Office, Level 4, Civic Tower, Rostam City"],
        rule_color=colors.HexColor("#7A4B1F"),
    ),
    "ENGINEER": dict(
        wordmark="ASHGROVE",
        subtext="Infrastructure Consultants",
        legal_name="Ashgrove Infrastructure Consultants",
        address=["Ashgrove House, 14 Prospect Street, Rostam City"],
        rule_color=colors.HexColor("#1F5C4A"),
    ),
    "CONTRACTOR": dict(
        wordmark="RENNICK",
        subtext="Builders Ltd.",
        legal_name="Rennick Builders Ltd.",
        address=["Rennick Yard, 45 Foundry Road, Rostam City"],
        rule_color=colors.HexColor("#5C1F3A"),
    ),
    "THIRD_PARTY": dict(
        wordmark=None,
        subtext=None,
        legal_name=None,
        address=[],
        rule_color=colors.HexColor("#555555"),
    ),
    "JOINT": dict(
        wordmark="KESTREL FLYOVER INTERCHANGE PROJECT",
        subtext="Package KFI-2",
        legal_name=None,
        address=[],
        rule_color=colors.HexColor("#3A3A3A"),
    ),
}

_JOINT_META = [
    ("Employer", "Kaldera Metropolitan Development Authority"),
    ("Engineer", "Ashgrove Infrastructure Consultants"),
    ("Contractor", "Rennick Builders Ltd."),
]

DOCUMENTS: list[DocumentSpec] = [

    # ------------------------------------------------------------------
    # KFI2-GC-2019 -- General Conditions (Extract: Clause 15 only)
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="KFI2-GC-2019",
        title="Conditions of Contract — General Conditions (Extract of Relevant Clauses)",
        doc_type="CONTRACT",
        doc_type_tag="GENERAL CONDITIONS (EXTRACT)",
        letterhead="JOINT",
        date="20-May-2019",
        from_="Kaldera Metropolitan Development Authority (Employer)",
        to="Ashgrove Infrastructure Consultants (Engineer); Rennick Builders Ltd. "
           "(Contractor)",
        contract_no=KFI2_CONTRACT_NO,
        extra_meta=_JOINT_META,
        project_line=KFI2_PROJECT_LINE,
        letterhead_registry=KFI2_LETTERHEADS,
        body=[
            ("subheading", "PREFATORY NOTE"),
            ("para", "This document reproduces, in extract form, those Clauses and "
                     "Sub-Clauses of the General Conditions of Contract considered relevant "
                     "to termination and final account matters on this Contract. It is not a "
                     "reproduction of the Contract in full, and no Clause or Sub-Clause not "
                     "appearing in this extract should be taken to be absent from the "
                     "Contract or of lesser standing than those which do appear. This "
                     "Contract, and this extract, are entirely independent of, and share no "
                     "clause numbering, defined terms, or party identity with, any other "
                     "contract package."),

            ("heading", "CLAUSE 15 — TERMINATION BY EMPLOYER"),
            ("subheading", "15.1 — Notice to Correct"),
            ("para", "If the Contractor fails to carry out any obligation under the "
                     "Contract, including a failure to proceed with the Works with due "
                     "diligence having regard to the then-current programme, the Engineer "
                     "may give the Contractor notice specifying the failure and requiring "
                     "the Contractor to remedy it within a stated period, being a period the "
                     "Engineer considers reasonable having regard to the nature of the "
                     "failure. If the Contractor fails to remedy the failure within the "
                     "period stated in the notice, or within any extension of that period "
                     "the Engineer may allow, the Employer may proceed under Sub-Clause "
                     "15.2."),
            ("para", "A notice under this Sub-Clause shall identify, with reasonable "
                     "particularity, the respect in which the Contractor has failed to "
                     "comply with the Contract, the action required to remedy that failure, "
                     "and the period within which it must be remedied. The Contractor shall "
                     "respond to a notice under this Sub-Clause in writing, stating the steps "
                     "it will take to remedy the failure identified and the programme for "
                     "doing so."),

            ("subheading", "15.2 — Termination by Employer"),
            ("para", "The Employer may terminate the Contract, by notice to the Contractor, "
                     "if the Contractor:"),
            ("bullet", "(a) fails to remedy, within the period stated in a notice given "
                       "under Sub-Clause 15.1, a failure identified in that notice;"),
            ("bullet", "(b) abandons the Works or plainly demonstrates an intention not to "
                       "continue performance of its obligations under the Contract;"),
            ("bullet", "(c) without reasonable excuse, fails to proceed with the Works with "
                       "due diligence, having regard to the then-current programme, such "
                       "that completion within the Time for Completion (as it may have been "
                       "extended) is no longer achievable; or"),
            ("bullet", "(d) is in persistent or repeated breach of a material obligation "
                       "under the Contract."),
            ("para", "A notice of termination under this Sub-Clause shall state the ground "
                     "or grounds relied upon and the date on which termination is to take "
                     "effect, being a date not less than seven days after the date of the "
                     "notice. On the date termination takes effect, the Contractor shall "
                     "cease further execution of the Works, leave the Site, and deliver up "
                     "to the Employer such Contractor's documents, Plant, Materials and "
                     "other things as the Employer instructs, and the Employer may complete "
                     "the Works itself or through others."),

            ("subheading", "15.3 — Valuation at Date of Termination"),
            ("para", "As soon as practicable after termination takes effect under Sub-Clause "
                     "15.2, the Engineer shall proceed to value the Works properly executed "
                     "and Materials delivered to and reasonably credited on the Site as at "
                     "the date of termination, having regard to the Contractor's Statements, "
                     "measurement records, and such further records or inspection as the "
                     "Engineer considers necessary, and shall notify the Contractor of that "
                     "valuation, with reasons."),

            ("subheading", "15.4 — Payment after Termination"),
            ("para", "Following a valuation under Sub-Clause 15.3, the Engineer shall "
                     "determine, and certify in a Final Payment Certificate, the net balance "
                     "due as between the Employer and the Contractor, calculated as follows: "
                     "there shall be credited to the Contractor the value of the Works "
                     "properly executed and Materials reasonably credited under Sub-Clause "
                     "15.3, together with any other sum properly due to the Contractor under "
                     "the Contract as at the date of termination; and there shall be credited "
                     "to the Employer the amount already certified and paid to the "
                     "Contractor as at the date of termination, and delay damages accrued, "
                     "at the rate stated in the Contract Data, for each day between the Time "
                     "for Completion (as it may have been extended) and the date of "
                     "termination. A cost, loss or expense arising from or in connection with "
                     "the Contractor's own default, including its demobilisation from the "
                     "Site following termination under this Clause, is not a sum properly "
                     "due to the Contractor for the purposes of this Sub-Clause."),
            ("para", "Retention Money held by the Employer as at the date of termination "
                     "shall be included in the calculation under this Sub-Clause and "
                     "released to the Contractor only to the extent, and at the time, the "
                     "resulting net balance is due to the Contractor. The net balance "
                     "determined under this Sub-Clause, whether due to the Contractor or to "
                     "the Employer, shall be paid within the period stated in the Contract "
                     "Data for payment of a Final Payment Certificate."),

            ("total_box", "[END OF EXTRACT]"),
        ],
        closing_lines=[],
        scenario=0,
    ),

    # ------------------------------------------------------------------
    # KFI2-PC-2019 -- Particular Conditions
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="KFI2-PC-2019",
        title="Conditions of Contract — Particular Conditions",
        doc_type="CONTRACT",
        doc_type_tag="PARTICULAR CONDITIONS",
        letterhead="JOINT",
        date="20-May-2019",
        from_="Kaldera Metropolitan Development Authority (Employer)",
        to="Ashgrove Infrastructure Consultants (Engineer); Rennick Builders Ltd. "
           "(Contractor)",
        contract_no=KFI2_CONTRACT_NO,
        extra_meta=_JOINT_META,
        project_line=KFI2_PROJECT_LINE,
        letterhead_registry=KFI2_LETTERHEADS,
        body=[
            ("subheading", "PREFATORY NOTE"),
            ("para", "These Particular Conditions amend and supplement the General "
                     "Conditions of Contract in the respects, and to the extent, set out "
                     "below. Save as expressly stated in these Particular Conditions, the "
                     "General Conditions remain of full force and effect. Any Sub-Clause not "
                     "mentioned in these Particular Conditions is unamended."),

            ("heading", "PART A — AMENDMENTS RELATING TO NOTICES"),
            ("subheading", "A.1 — Notice Addresses and Communication Protocol"),
            ("para", "Wherever the Contract requires a notice, certificate, determination "
                     "or instruction to be given or issued by one Party to the other, or by "
                     "the Engineer to either Party, it shall be in writing and shall be "
                     "treated as validly given only once received at the address nominated "
                     "by the recipient for that purpose in the Contract Data, or at such "
                     "other address as the recipient may from time to time nominate in "
                     "writing. A notice sent by electronic mail to a nominated electronic "
                     "address shall be treated as received at the time shown on the sender's "
                     "transmission record."),

            ("heading", "PART B — AMENDMENTS RELATING TO THE ENGINEER"),
            ("subheading", "B.1 — Engineer's Delegated Representative"),
            ("para", "The Engineer shall appoint, and notify to the Contractor before the "
                     "Commencement Date, a Resident Engineer who shall be based at the Site "
                     "and who is hereby delegated the Engineer's authority to give "
                     "day-to-day instructions, to witness and approve measurement, and to "
                     "issue a notice under Sub-Clause 15.1 on the Engineer's behalf. The "
                     "Resident Engineer's authority does not extend to a notice of "
                     "termination under Sub-Clause 15.2 or a Final Payment Certificate under "
                     "Sub-Clause 15.4, both of which are reserved to the Engineer "
                     "personally."),

            ("heading", "PART C — AMENDMENTS RELATING TO CLAUSE 15 (TERMINATION BY "
                        "EMPLOYER)"),
            ("subheading", "C.1 — Minimum Period for a Notice to Correct"),
            ("para", "Sub-Clause 15.1 is supplemented as follows. A notice given under "
                     "Sub-Clause 15.1 shall state a period of not less than the minimum "
                     "period stated in the Contract Data, and shall identify, by reference "
                     "to the Contractor's then-current accepted programme and the "
                     "Contractor's own monthly progress reports, the specific respects in "
                     "which the Contractor has failed to proceed with the Works with due "
                     "diligence."),
            ("subheading", "C.2 — Confirmation of Termination Procedure"),
            ("para", "For the avoidance of doubt, a notice of termination given under "
                     "Sub-Clause 15.2 in reliance on the Contractor's failure to remedy a "
                     "notice given under Sub-Clause 15.1 shall not be given before the "
                     "period stated in that Sub-Clause 15.1 notice has expired, and shall "
                     "identify the Sub-Clause 15.1 notice relied upon and the manner in "
                     "which the Contractor failed to remedy it."),

            ("total_box", "[END OF PARTICULAR CONDITIONS]"),
        ],
        closing_lines=[],
        scenario=0,
    ),

    # ------------------------------------------------------------------
    # KFI2-CD-2019 -- Contract Data
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="KFI2-CD-2019",
        title="Contract Data",
        doc_type="CONTRACT",
        doc_type_tag="CONTRACT DATA",
        letterhead="JOINT",
        date="20-May-2019",
        from_="Kaldera Metropolitan Development Authority (Employer)",
        to="Ashgrove Infrastructure Consultants (Engineer); Rennick Builders Ltd. "
           "(Contractor)",
        contract_no=KFI2_CONTRACT_NO,
        project_line=KFI2_PROJECT_LINE,
        letterhead_registry=KFI2_LETTERHEADS,
        body=[
            ("para", "This Contract Data forms part of the Contract and provides the "
                     "specific values, periods, rates and particulars referred to in the "
                     "General Conditions and the Particular Conditions. This Contract is "
                     "entirely independent of any other contract package; no party, address, "
                     "rate, or period below is shared with, or derived from, any other "
                     "project."),

            ("heading", "1. THE PARTIES"),
            ("para", "Employer: Kaldera Metropolitan Development Authority"),
            ("para", "Employer's Address for Notices: KMDA Project Office, Level 4, Civic "
                     "Tower, Rostam City, Republic of Kaldera"),
            ("para", "Employer's Electronic Address: projects.kfi2@kmda.gov.kl"),
            ("para", "Engineer: Ashgrove Infrastructure Consultants"),
            ("para", "Engineer's Address for Notices: Ashgrove House, 14 Prospect Street, "
                     "Rostam City, Republic of Kaldera"),
            ("para", "Engineer's Site Office: KFI-2 Site Office, Verrin District, Rostam "
                     "City"),
            ("para", "Engineer's Electronic Address: kfi2.engineer@ashgroveconsult.kl"),
            ("para", "Contractor: Rennick Builders Ltd."),
            ("para", "Contractor's Address for Notices: Rennick Yard, 45 Foundry Road, "
                     "Rostam City, Republic of Kaldera"),
            ("para", "Contractor's Site Office: KFI-2 Contractor's Compound, Verrin "
                     "District, Rostam City"),
            ("para", "Contractor's Electronic Address: kfi2.pm@rennickbuilders.kl"),

            ("heading", "2. THE PROJECT"),
            ("para", "Project Name: Kestrel Flyover Interchange Project — Package KFI-2"),
            ("para", "Contract Number: KMDA/KFI2/CW/2019-04"),
            ("para", "Site Location: Rostam Central Junction, connecting Highway N-7 and "
                     "Ring Road R-2, Verrin District, Rostam City, Republic of Kaldera"),

            ("heading", "3. KEY DATES AND PERIODS"),
            ("para", "Letter of Acceptance Date: 6 May 2019"),
            ("para", "Commencement Date: 3 June 2019"),
            ("para", "Time for Completion: 24 months from the Commencement Date, being 2 "
                     "June 2021"),
            ("para", "Defects Notification Period: 365 days from the date stated in the "
                     "Taking-Over Certificate (not reached on this Contract; the Contract "
                     "was terminated before Taking-Over)"),

            ("heading", "4. CONTRACT AMOUNT AND CURRENCY"),
            ("para", "Payment Currency: Kaldera Dollar (KLD)"),
            ("para", "Contract Amount: KLD 36,000,000 (Kaldera Dollars thirty-six million)"),

            ("heading", "5. SECURITY"),
            ("para", "Performance Security Percentage: 10 per cent of the Contract Amount"),
            ("para", "Performance Security: KLD 3,600,000, in the form of an unconditional "
                     "and irrevocable bank guarantee"),

            ("heading", "6. RETENTION"),
            ("para", "Retention Percentage: 5 per cent of each amount otherwise due"),
            ("para", "Limit of Retention Money: KLD 1,800,000, being 5 per cent of the "
                     "Contract Amount"),

            ("heading", "7. DELAY DAMAGES"),
            ("para", "Delay Damages Rate (Sub-Clause 15.4): 0.06 per cent of the Contract "
                     "Amount for each day of delay, being KLD 21,600 per day"),
            ("para", "Maximum Delay Damages: 10 per cent of the Contract Amount, being KLD "
                     "3,600,000"),

            ("heading", "8. PAYMENT"),
            ("para", "Interim Payment Frequency: Monthly"),
            ("para", "Engineer Certification Period: 21 days from receipt of a compliant "
                     "Statement"),
            ("para", "Employer Payment Period (including payment of a Final Payment "
                     "Certificate under Sub-Clause 15.4): 56 days from the date of "
                     "certification"),

            ("heading", "9. NOTICE TO CORRECT"),
            ("para", "Minimum period to be stated in a notice under Sub-Clause 15.1 "
                     "(Particular Conditions Part C.1): not less than 42 days from the date "
                     "of the notice, save where the Engineer states a shorter period is "
                     "reasonable having regard to the nature and urgency of the failure "
                     "identified"),

            ("heading", "10. WORKING DAYS AND HOURS"),
            ("para", "Working Days: Monday to Saturday, excluding public holidays observed "
                     "at the Site"),
            ("para", "Working Hours: 07:00 to 19:00"),

            ("heading", "11. ENGINEER'S RESIDENT REPRESENTATIVE"),
            ("para", "Resident Engineer: Er. Priya Solheim"),
            ("para", "Address: KFI-2 Site Office, Verrin District, Rostam City"),
            ("para", "Scope of Delegation: as recorded in the Engineer's notice to the "
                     "Contractor issued pursuant to Part B.1 of the Particular Conditions"),

            ("total_box", "[END OF CONTRACT DATA]"),
        ],
        closing_lines=[],
        scenario=0,
    ),

    # ------------------------------------------------------------------
    # KFI2-ER-2019 -- Employer's Requirements (Extract)
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="KFI2-ER-2019",
        title="Employer's Requirements (Extract)",
        doc_type="CONTRACT",
        doc_type_tag="EMPLOYER'S REQUIREMENTS (EXTRACT)",
        letterhead="JOINT",
        date="20-May-2019",
        from_="Kaldera Metropolitan Development Authority (Employer)",
        to="Ashgrove Infrastructure Consultants (Engineer); Rennick Builders Ltd. "
           "(Contractor)",
        contract_no=KFI2_CONTRACT_NO,
        project_line=KFI2_PROJECT_LINE,
        letterhead_registry=KFI2_LETTERHEADS,
        body=[
            ("para", "This document sets out the Employer's technical requirements for the "
                     "construction and commissioning of the Works. It is a technical "
                     "requirements document and does not form the Conditions of Contract. "
                     "This is an extract; matters not addressed below are not to be taken as "
                     "excluded from the Contractor's obligations under the Contract."),

            ("heading", "1. PROJECT OVERVIEW"),
            ("para", "The Works comprise the design (to the extent stated in the "
                     "Specification), construction and commissioning of an elevated flyover "
                     "interchange connecting Highway N-7 and Ring Road R-2 at Rostam Central "
                     "Junction, together with all ancillary civil, structural, drainage and "
                     "signage works necessary for the interchange to be brought into safe "
                     "public use. The Works are located within Verrin District, Rostam City, "
                     "Republic of Kaldera."),

            ("heading", "2. SCOPE OF WORKS"),
            ("para", "The Scope of Works includes, without limitation: site clearance and "
                     "preparatory works; temporary traffic management and diversion for the "
                     "duration of construction; foundation and substructure works, including "
                     "piling, pile caps and piers; superstructure works, including precast "
                     "girders, deck slab, parapets, expansion joints and bearings; ramp and "
                     "approach works connecting to Highway N-7 and Ring Road R-2; permanent "
                     "signage, lighting conduit and road marking within the limits of the "
                     "Works; and testing and commissioning of the completed structure."),

            ("heading", "3. STRUCTURE CONFIGURATION"),
            ("para", "The flyover shall comprise 6 spans with an overall length of "
                     "approximately 480 metres, supported on 2 abutments and 5 piers, "
                     "carrying a dual two-lane carriageway with hard shoulders over Rostam "
                     "Central Junction. The Works shall be designed and constructed for a "
                     "design life of 100 years, in accordance with the Kaldera National "
                     "Bridge Design Code and the Specification."),

            ("heading", "4. PROGRAMME AND RESOURCING"),
            ("para", "The Contractor shall maintain, and resource the Works in accordance "
                     "with, a programme complying with Section 5 of this document, updated "
                     "monthly, showing planned versus actual progress by principal element "
                     "(piling, substructure, superstructure, ramps, finishing works). The "
                     "Contractor shall deploy labour, plant and supervision consistent with "
                     "the resource levels stated in its accepted programme, and shall notify "
                     "the Engineer promptly of any material shortfall in resourcing and the "
                     "reason for it."),

            ("heading", "5. PROGRAMME REQUIREMENTS"),
            ("para", "The Contractor's programme shall show a planned percentage of overall "
                     "contract value complete at each monthly reporting date, against which "
                     "actual progress is to be measured and reported in the Contractor's "
                     "monthly progress report. A shortfall of more than 15 percentage points "
                     "between planned and actual overall progress at any reporting date, "
                     "sustained for two or more consecutive reporting periods, shall be "
                     "treated by the Engineer as a material indicator of a failure to "
                     "proceed with due diligence for the purposes of Sub-Clause 15.1."),

            ("heading", "6. QUALITY AND RECORDS"),
            ("para", "The Contractor shall maintain a Site diary, monthly progress reports, "
                     "and measurement records sufficient to support Statements submitted "
                     "under the Contract, and shall retain all such records for inspection "
                     "by the Engineer. Utilities shown on the Drawings, including a water "
                     "main crossing the Site near Ramp C, are based on records supplied by "
                     "the relevant utility owner and may not be complete; the Contractor "
                     "shall verify utility locations before excavation and report promptly "
                     "any utility encountered that is not shown on the Drawings."),

            ("total_box", "[END OF EMPLOYER'S REQUIREMENTS EXTRACT]"),
        ],
        closing_lines=[],
        scenario=0,
    ),
]
