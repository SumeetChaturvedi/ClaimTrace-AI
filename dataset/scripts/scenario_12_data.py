"""Structured data for the 14 Scenario 12 documents — Employer Termination
and Final Account, Kestrel Flyover Interchange Project (Package KFI-2).

Phase 4 Task 04: this scenario belongs to an entirely NEW, independent
project (project_id=3), not the Nandira River Bridge Project (project_id=2,
Scenarios 1-11). New Employer (Kaldera Metropolitan Development Authority),
Engineer (Ashgrove Infrastructure Consultants), Contractor (Rennick
Builders Ltd.), country/city (Republic of Kaldera / Rostam City), currency
(Kaldera Dollar, KLD), contract number (KMDA/KFI2/CW/2019-04), and document
numbering (EPA-/EWN-/NTC-/CTR-/NOT-/ETC-/SHR-/AIV-/CFC-/EFA-/PST-/RET-/
LDA-/FCR-KFI2-0xx) -- no identifier, party, or clause number here is
shared with, or derived from, Scenarios 1-11 or the NRB4 contract package.
Uses the contract package added in KFI2-GC-2019.txt (Sub-Clauses 15.1-15.4,
Termination by Employer), the only clauses this scenario's determinations
require.

Story: by month 21 of a 24-month contract, the Contractor's progress has
fallen critically behind (41% complete against 88% planned), triggering an
Engineer's Progress Assessment, an Employer's Warning Notice, and
ultimately a formal Notice to Correct under Sub-Clause 15.1. The
Contractor's response is weak and progress does not recover to the
required level within the stated period, so the Employer terminates under
Sub-Clause 15.2. Handover and an Asset Inventory follow, then a Contractor
financial claim (part-justified by a genuine but limited utility
relocation delay near Ramp C, part overstated) and an Engineer's Final
Account resolving valuation, liquidated damages, retention, and the net
balance due -- a "partially accepted" outcome consistent with this
dataset's established storytelling pattern (Scenarios 1, 3, 10), not a
one-sided result for either Party.

Numeric consistency, carried through every document: Contract Amount KLD
36,000,000; Time for Completion 02-Jun-2021; Notice to Correct period
26-Apr-2021 to 07-Jun-2021 (42 days, the Contract Data Section 9 minimum);
progress 41% (08-Mar-2021) -> 46% (07-Jun-2021, NTC deadline) -> 47%
(25-Jun-2021, handover); termination effective 21-Jun-2021 (19 calendar
days after the Time for Completion); Liquidated Damages Rate KLD
21,600/day (Contract Data Section 7); a 5-day credit accepted for the
Ramp C utility relocation delay reduces the chargeable LD period from 19
to 14 days (KLD 302,400); gross certified value to termination KLD
15,100,000, retention withheld at 5% = KLD 755,000, net paid KLD
14,345,000 (Payment Statement PST-KFI2-011); final measured value (work +
materials) KLD 15,800,000 (Employer's Final Account EFA-KFI2-001); net
balance due to the Contractor KLD 1,152,600 (= 15,800,000 - 14,345,000 -
302,400), of which the released retention of KLD 755,000 forms part.
"""

from pdf_template import DocumentSpec
from contracts_data_kfi2 import KFI2_PROJECT_LINE, KFI2_CONTRACT_NO, KFI2_LETTERHEADS

SCENARIO = 12

DOCUMENTS: list[DocumentSpec] = [

    # ------------------------------------------------------------------
    # Document 1 -- EPA-KFI2-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="EPA-KFI2-001",
        title="Engineer's Progress Assessment — Month 21",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="PROGRESS ASSESSMENT",
        letterhead="ENGINEER",
        date="08-Mar-2021",
        from_="Resident Engineer, Ashgrove Infrastructure Consultants",
        to="Kaldera Metropolitan Development Authority",
        cc="Rennick Builders Ltd.",
        contract_no=KFI2_CONTRACT_NO,
        project_line=KFI2_PROJECT_LINE,
        letterhead_registry=KFI2_LETTERHEADS,
        subject="Progress Assessment — Month 21 of the Contract Period",
        body=[
            ("para", "This assessment reviews progress against the accepted programme as at "
                     "the end of Month 21 of the Contract period (Commencement Date "
                     "03-Jun-2019; Time for Completion 02-Jun-2021)."),
            ("heading", "FINDINGS:"),
            ("table", {
                "headers": ["Element", "Planned % Complete", "Actual % Complete", "Shortfall"],
                "rows": [
                    ["Piling and substructure", "100%", "78%", "22 pts"],
                    ["Superstructure (girders, deck)", "85%", "31%", "54 pts"],
                    ["Ramps and approach works", "80%", "22%", "58 pts"],
                    ["Signage and finishing works", "60%", "5%", "55 pts"],
                    ["Overall (by contract value)", "88%", "41%", "47 pts"],
                ],
            }),
            ("para", "Overall progress has fallen from a shortfall of 19 percentage points "
                     "at Month 19 to 47 percentage points at this assessment, a widening gap "
                     "over two consecutive reporting periods. This is a material indicator of "
                     "a failure to proceed with the Works with due diligence for the purposes "
                     "of Sub-Clause 15.1, per the threshold stated in Employer's Requirements "
                     "Section 5."),
            ("heading", "CONTRIBUTING FACTORS OBSERVED:"),
            ("bullet", "Labour and plant deployed on Site have been consistently below the "
                       "levels shown in the Contractor's own accepted programme for the past "
                       "four months, per Site attendance records."),
            ("bullet", "A water main crossing the Site near Ramp C, not fully resolved by the "
                       "utility owner until 15-Feb-2021, delayed the start of Ramp C "
                       "substructure works by approximately 5 weeks. This is a genuine, "
                       "limited factor, but does not account for the shortfall recorded at "
                       "any other element of the Works, including superstructure and "
                       "signage/finishing, where the utility crossing has no bearing."),
            ("bullet", "No recovery programme has been submitted since the informal request "
                       "raised at Monthly Progress Meeting No. 18 (03-Dec-2020)."),
            ("heading", "RECOMMENDATION:"),
            ("para", "Given the scale and persistence of the shortfall, and that it extends "
                     "materially beyond the elements affected by the Ramp C utility delay, we "
                     "recommend the Employer consider formal escalation, beginning with a "
                     "warning to the Contractor, if progress does not visibly improve at the "
                     "next reporting date."),
        ],
        closing_lines=["Prepared by: Resident Engineer, Ashgrove Infrastructure Consultants"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 2 -- EWN-KFI2-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="EWN-KFI2-001",
        title="Employer's Warning Notice — Inadequate Progress",
        doc_type="NOTICE",
        doc_type_tag="WARNING NOTICE",
        letterhead="EMPLOYER",
        date="19-Mar-2021",
        from_="Kaldera Metropolitan Development Authority",
        to="Rennick Builders Ltd.",
        cc="Ashgrove Infrastructure Consultants",
        contract_no=KFI2_CONTRACT_NO,
        project_line=KFI2_PROJECT_LINE,
        letterhead_registry=KFI2_LETTERHEADS,
        subject="Warning Notice — Inadequate Progress, Kestrel Flyover Interchange Project",
        body=[
            ("para", "We refer to the Engineer's Progress Assessment EPA-KFI2-001 dated "
                     "08-Mar-2021, recording overall progress of 41 per cent against a "
                     "planned 88 per cent at Month 21 of the Contract period, a shortfall "
                     "that has widened over the two most recent reporting periods."),
            ("para", "This is a serious matter. At the current rate of progress, the Works "
                     "will not be completed within the Time for Completion of 02-Jun-2021, "
                     "nor within any period we would regard as a reasonable extension of it. "
                     "We note the Ramp C utility relocation delay recorded in EPA-KFI2-001 is "
                     "acknowledged, but cannot account for the shortfall recorded at the "
                     "superstructure or signage and finishing elements, where no such delay "
                     "applies."),
            ("para", "We require Rennick Builders Ltd. to submit, within 14 days of this "
                     "notice, a corrective action plan addressing labour and plant "
                     "mobilisation and a credible path to recovering progress. This notice is "
                     "given informally, ahead of and without prejudice to any notice the "
                     "Engineer may separately consider issuing under Sub-Clause 15.1 if "
                     "progress does not visibly improve."),
        ],
        closing_lines=["Regards,", "Kaldera Metropolitan Development Authority"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 3 -- NTC-KFI2-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="NTC-KFI2-001",
        title="Notice to Correct NTC-KFI2-001 — Failure to Proceed with Due Diligence",
        doc_type="NOTICE",
        doc_type_tag="NOTICE TO CORRECT",
        letterhead="ENGINEER",
        date="26-Apr-2021",
        from_="Engineer, Ashgrove Infrastructure Consultants",
        to="Rennick Builders Ltd.",
        cc="Kaldera Metropolitan Development Authority",
        contract_no=KFI2_CONTRACT_NO,
        project_line=KFI2_PROJECT_LINE,
        letterhead_registry=KFI2_LETTERHEADS,
        subject="Notice to Correct — Sub-Clause 15.1",
        body=[
            ("para", "Pursuant to Sub-Clause 15.1, and further to Progress Assessment "
                     "EPA-KFI2-001 (08-Mar-2021) and Warning Notice EWN-KFI2-001 "
                     "(19-Mar-2021), we give notice that the Contractor has failed to proceed "
                     "with the Works with due diligence, having regard to the then-current "
                     "programme, in that overall progress stood at 41 per cent against a "
                     "planned 88 per cent as at 08-Mar-2021, a shortfall sustained and "
                     "widening over the two most recent reporting periods, and no corrective "
                     "action plan has been received in response to EWN-KFI2-001."),
            ("para", "In accordance with Particular Conditions Part C.1 and Contract Data "
                     "Section 9, the Contractor is required, within 42 days of this notice "
                     "(by 07-Jun-2021), to:"),
            ("bullet", "(a) mobilise labour and plant to the resource levels shown in the "
                       "Contractor's own accepted programme, across all principal elements of "
                       "the Works, not only those affected by the Ramp C utility relocation;"),
            ("bullet", "(b) submit, within 21 days of this notice, a recovery programme "
                       "demonstrating an achievable path to completion, and commence "
                       "executing it; and"),
            ("bullet", "(c) achieve not less than 55 per cent overall progress, by contract "
                       "value, by 07-Jun-2021."),
            ("para", "Failure to remedy each of the above within the period stated may result "
                     "in termination under Sub-Clause 15.2."),
        ],
        closing_lines=["Signed: Engineer's Representative", "Ashgrove Infrastructure "
                       "Consultants"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 4 -- CTR-KFI2-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="CTR-KFI2-001",
        title="Contractor's Response — Notice to Correct NTC-KFI2-001",
        doc_type="CORRESPONDENCE",
        doc_type_tag="CORRESPONDENCE",
        letterhead="CONTRACTOR",
        date="10-May-2021",
        from_="Project Manager, Rennick Builders Ltd.",
        to="Engineer, Ashgrove Infrastructure Consultants",
        cc="Kaldera Metropolitan Development Authority",
        contract_no=KFI2_CONTRACT_NO,
        project_line=KFI2_PROJECT_LINE,
        letterhead_registry=KFI2_LETTERHEADS,
        subject="Response to Notice to Correct NTC-KFI2-001",
        body=[
            ("para", "We acknowledge Notice to Correct NTC-KFI2-001 dated 26-Apr-2021 and "
                     "respond as follows."),
            ("para", "1. We accept that overall progress is behind programme. We consider "
                     "part of this shortfall is attributable to the delayed resolution of the "
                     "water main crossing near Ramp C, which was not cleared by the utility "
                     "owner until 15-Feb-2021, some 9 weeks later than shown in our tender "
                     "programme, and which affected our sequencing of plant and labour across "
                     "the wider Site, not only Ramp C itself."),
            ("para", "2. We have re-mobilised additional labour and one further piling rig to "
                     "Site with effect from 03-May-2021, and enclose a recovery programme "
                     "targeting substantial improvement in overall progress by 07-Jun-2021, "
                     "though we note achieving the full 55 per cent target in the time "
                     "remaining will be challenging."),
            ("para", "3. We are addressing this matter as a priority and will report progress "
                     "against the enclosed recovery programme at each subsequent progress "
                     "meeting."),
        ],
        closing_lines=["Regards,", "Project Manager", "Rennick Builders Ltd."],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 5 -- NOT-KFI2-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="NOT-KFI2-001",
        title="Notice of Termination NOT-KFI2-001",
        doc_type="NOTICE",
        doc_type_tag="NOTICE OF TERMINATION",
        letterhead="EMPLOYER",
        date="14-Jun-2021",
        from_="Kaldera Metropolitan Development Authority",
        to="Rennick Builders Ltd.",
        cc="Ashgrove Infrastructure Consultants",
        contract_no=KFI2_CONTRACT_NO,
        project_line=KFI2_PROJECT_LINE,
        letterhead_registry=KFI2_LETTERHEADS,
        subject="Notice of Termination — Sub-Clause 15.2",
        body=[
            ("para", "We refer to Notice to Correct NTC-KFI2-001 dated 26-Apr-2021, requiring "
                     "the Contractor, by 07-Jun-2021, to mobilise to programme resource "
                     "levels, submit and commence a recovery programme, and achieve not less "
                     "than 55 per cent overall progress."),
            ("para", "The Engineer's assessment as at 07-Jun-2021 records overall progress of "
                     "46 per cent, against the 55 per cent required. While a recovery "
                     "programme was submitted with Contractor's Response CTR-KFI2-001 dated "
                     "10-May-2021, actual progress against it has fallen materially short at "
                     "every reporting point since."),
            ("para", "Pursuant to Sub-Clause 15.2, we hereby terminate the Contract on the "
                     "following grounds: (a) failure to remedy, within the period stated in "
                     "NTC-KFI2-001, the failures identified in that notice; and (b) persistent "
                     "failure to proceed with the Works with due diligence, sustained over the "
                     "period recorded in Progress Assessment EPA-KFI2-001 and subsequent "
                     "reporting, such that completion within the Time for Completion (as it "
                     "may have been extended) is no longer achievable."),
            ("para", "This ground is independent of, and additional to, the Ramp C utility "
                     "relocation delay referred to in CTR-KFI2-001: the shortfall recorded "
                     "against the 55 per cent target is materially greater than any delay "
                     "attributable to that single, limited event."),
            ("para", "Termination shall take effect on 21-Jun-2021, being not less than seven "
                     "days from the date of this notice. The Contractor shall cease further "
                     "execution of the Works, leave the Site, and deliver up Contractor's "
                     "documents, Plant, Materials and other things as instructed by the "
                     "Engineer, in accordance with Sub-Clause 15.2."),
        ],
        closing_lines=["Regards,", "Kaldera Metropolitan Development Authority"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 6 -- ETC-KFI2-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="ETC-KFI2-001",
        title="Engineer's Termination Certificate",
        doc_type="APPROVAL",
        doc_type_tag="TERMINATION CERTIFICATE",
        letterhead="ENGINEER",
        date="22-Jun-2021",
        from_="Engineer, Ashgrove Infrastructure Consultants",
        to="Rennick Builders Ltd.",
        cc="Kaldera Metropolitan Development Authority",
        contract_no=KFI2_CONTRACT_NO,
        project_line=KFI2_PROJECT_LINE,
        letterhead_registry=KFI2_LETTERHEADS,
        subject="Termination Certificate — Notice of Termination NOT-KFI2-001",
        body=[
            ("para", "We refer to Notice of Termination NOT-KFI2-001 dated 14-Jun-2021, "
                     "issued by the Employer under Sub-Clause 15.2, stating termination would "
                     "take effect 21-Jun-2021."),
            ("para", "We certify that termination of the Contract took effect on 21-Jun-2021 "
                     "in accordance with that notice, and confirm the procedural requirements "
                     "of Sub-Clause 15.2 and Particular Conditions Part C.2 were satisfied: "
                     "the notice identified the Sub-Clause 15.1 notice relied upon "
                     "(NTC-KFI2-001), the manner in which the Contractor failed to remedy it, "
                     "and was given after the period stated in that notice (expiring "
                     "07-Jun-2021) had elapsed, with not less than seven days' notice of the "
                     "date termination would take effect."),
            ("para", "Site handover and valuation under Sub-Clauses 15.3 and 15.4 will follow "
                     "separately."),
        ],
        closing_lines=["Signed: Engineer's Representative", "Ashgrove Infrastructure "
                       "Consultants"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 7 -- SHR-KFI2-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="SHR-KFI2-001",
        title="Site Handover Record",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="SITE HANDOVER RECORD",
        letterhead="JOINT",
        date="25-Jun-2021",
        from_="Ashgrove Infrastructure Consultants",
        to="Kaldera Metropolitan Development Authority",
        cc="Rennick Builders Ltd.",
        contract_no=KFI2_CONTRACT_NO,
        project_line=KFI2_PROJECT_LINE,
        letterhead_registry=KFI2_LETTERHEADS,
        extra_meta=[
            ("Participants", "Resident Engineer (Ashgrove Infrastructure Consultants); "
                             "Project Manager, Rennick Builders Ltd. (attended under "
                             "reservation of rights, without prejudice to CTR-KFI2-001)"),
        ],
        subject="Site Handover Record — Following Termination Certificate ETC-KFI2-001",
        body=[
            ("para", "Site handover inspection carried out 25-Jun-2021, following termination "
                     "effective 21-Jun-2021 (Termination Certificate ETC-KFI2-001)."),
            ("heading", "MEASURED PROGRESS AT HANDOVER:"),
            ("table", {
                "headers": ["Element", "Measured % Complete"],
                "rows": [
                    ["Piling and substructure", "82%"],
                    ["Superstructure (girders, deck)", "34%"],
                    ["Ramps and approach works", "26%"],
                    ["Signage and finishing works", "6%"],
                    ["Overall (by contract value)", "47%"],
                ],
            }),
            ("para", "Overall measured progress at handover (47%) is marginally higher than "
                     "the 46% recorded at the Notice to Correct deadline (07-Jun-2021), "
                     "reflecting limited further work completed during the notice period "
                     "before termination took effect."),
            ("heading", "SITE CONDITION:"),
            ("bullet", "Piers 1-5 and both abutments substantially complete to substructure "
                       "level; superstructure girders erected on Piers 1-3 only."),
            ("bullet", "Ramp C substructure approximately 40% complete, consistent with the "
                       "delayed start following the utility relocation."),
            ("bullet", "No safety-critical defect or hazard identified requiring immediate "
                       "attention; Site secured and handed to the Employer's care."),
            ("para", "The Contractor's representative confirmed attendance without prejudice "
                     "to the Contractor's position, recorded separately, that the shortfall "
                     "against the Notice to Correct target was affected by the Ramp C utility "
                     "relocation delay."),
            ("para", "Asset Inventory AIV-KFI2-001 records Plant, Materials and Temporary "
                     "Works remaining on Site as at this handover."),
        ],
        closing_lines=["Signed jointly by: Ashgrove Infrastructure Consultants and Rennick "
                       "Builders Ltd. (under reservation, as noted above)"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 8 -- AIV-KFI2-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="AIV-KFI2-001",
        title="Asset Inventory — Plant, Materials and Temporary Works at Handover",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="ASSET INVENTORY",
        letterhead="ENGINEER",
        date="25-Jun-2021",
        from_="Ashgrove Infrastructure Consultants",
        to="Kaldera Metropolitan Development Authority",
        cc="Rennick Builders Ltd.",
        contract_no=KFI2_CONTRACT_NO,
        project_line=KFI2_PROJECT_LINE,
        letterhead_registry=KFI2_LETTERHEADS,
        subject="Asset Inventory — Recorded at Site Handover, 25-Jun-2021",
        body=[
            ("para", "Schedule of Plant, Materials and Temporary Works recorded on Site at "
                     "the handover inspection of 25-Jun-2021 (Site Handover Record "
                     "SHR-KFI2-001), for the purposes of valuation under Sub-Clause 15.3."),
            ("table", {
                "headers": ["Item", "Quantity/Description", "Condition", "Credited Value (KLD)"],
                "rows": [
                    ["Precast girders, undelivered spans", "8 no., stored at Contractor's "
                     "compound", "New, undamaged", "420,000"],
                    ["Reinforcement steel, cut and bent", "Bar bending schedule Ramp C/D",
                     "New, unfixed", "165,000"],
                    ["Falsework and formwork, Ramp C piers", "In place, partially struck",
                     "Serviceable", "95,000"],
                    ["Total Materials credited:", "", "", "680,000"],
                ],
                "right_align_cols": [3],
                "bold_last_row": True,
            }),
            ("para", "Contractor's Equipment (piling rigs, cranes, site accommodation) is "
                     "excluded from this schedule as it remains the Contractor's own property "
                     "and was removed from Site by the Contractor between 22-Jun-2021 and "
                     "24-Jun-2021, ahead of the handover inspection."),
            ("para", "The total Materials credit of KLD 680,000 is carried into the valuation "
                     "in Employer's Final Account EFA-KFI2-001."),
        ],
        closing_lines=["Prepared by: Ashgrove Infrastructure Consultants"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 9 -- CFC-KFI2-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="CFC-KFI2-001",
        title="Contractor's Financial Claim — Following Termination",
        doc_type="CLAIM",
        doc_type_tag="CONTRACTOR FINANCIAL CLAIM",
        letterhead="CONTRACTOR",
        date="23-Jul-2021",
        from_="Project Manager, Rennick Builders Ltd.",
        to="Engineer, Ashgrove Infrastructure Consultants",
        cc="Kaldera Metropolitan Development Authority",
        contract_no=KFI2_CONTRACT_NO,
        project_line=KFI2_PROJECT_LINE,
        letterhead_registry=KFI2_LETTERHEADS,
        subject="Financial Claim Following Termination — Sub-Clauses 15.3 and 15.4",
        body=[
            ("para", "Further to Termination Certificate ETC-KFI2-001 and Site Handover "
                     "Record SHR-KFI2-001, we submit our claim for the sums we consider "
                     "properly due following termination."),
            ("para", "1. VALUATION OF WORK AND MATERIALS: We consider the value of work "
                     "properly executed and materials on Site is KLD 17,200,000, higher than "
                     "the 47 per cent handover measurement would suggest at contract rates, "
                     "reflecting preliminaries and mobilisation costs substantially incurred "
                     "but not separately measured under the Bill of Quantities structure."),
            ("para", "2. TERMINATION VALIDITY: While we do not, at this stage, formally "
                     "dispute the Employer's entitlement to terminate, we maintain, as stated "
                     "in CTR-KFI2-001, that the Ramp C utility relocation delay (utility owner "
                     "resolution not complete until 15-Feb-2021, some 9 weeks later than "
                     "programmed) materially affected our ability to meet the 55 per cent "
                     "target in Notice to Correct NTC-KFI2-001, and should be reflected as a "
                     "credit against any liquidated damages assessed."),
            ("para", "3. DEMOBILISATION COSTS: We claim KLD 320,000 in respect of costs "
                     "incurred removing Contractor's Equipment and demobilising our workforce "
                     "following termination."),
            ("para", "4. RETENTION: We request that retention held to date be released in "
                     "full as part of the final account, there being no defect or outstanding "
                     "obligation of a kind retention is intended to secure."),
            ("para", "We look forward to the Engineer's valuation under Sub-Clause 15.3 and "
                     "Final Payment Certificate under Sub-Clause 15.4."),
        ],
        closing_lines=["Regards,", "Project Manager", "Rennick Builders Ltd."],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 10 -- EFA-KFI2-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="EFA-KFI2-001",
        title="Employer's Final Account — Valuation and Determination at Termination",
        doc_type="APPROVAL",
        doc_type_tag="FINAL ACCOUNT / DETERMINATION",
        letterhead="ENGINEER",
        date="15-Sep-2021",
        from_="Engineer, Ashgrove Infrastructure Consultants",
        to="Rennick Builders Ltd.",
        cc="Kaldera Metropolitan Development Authority",
        contract_no=KFI2_CONTRACT_NO,
        project_line=KFI2_PROJECT_LINE,
        letterhead_registry=KFI2_LETTERHEADS,
        subject="Final Account and Determination — Sub-Clauses 15.3 and 15.4",
        body=[
            ("para", "We refer to Notice of Termination NOT-KFI2-001, Site Handover Record "
                     "SHR-KFI2-001, Asset Inventory AIV-KFI2-001, and Contractor's Financial "
                     "Claim CFC-KFI2-001. Having reviewed the particulars submitted, we "
                     "determine the Final Account under Sub-Clauses 15.3 and 15.4 as "
                     "follows."),
            ("para", "1. TERMINATION VALIDITY AND PROCEDURE: We confirm the Employer was "
                     "entitled to terminate under Sub-Clause 15.2, on the grounds stated in "
                     "NOT-KFI2-001: failure to remedy Notice to Correct NTC-KFI2-001 within "
                     "the stated period (progress of 46% against the 55% required by "
                     "07-Jun-2021), and persistent failure to proceed with due diligence "
                     "sustained over the preceding period. We confirm the procedure required "
                     "by Particular Conditions Part C.2 was followed: NOT-KFI2-001 was given "
                     "after NTC-KFI2-001's period expired, identified that notice and the "
                     "manner of non-compliance, and gave seven days' notice of the "
                     "termination date, consistent with Termination Certificate ETC-KFI2-001."),
            ("para", "2. VALUATION OF WORK AND MATERIALS: We do not accept CFC-KFI2-001's "
                     "claimed valuation of KLD 17,200,000, which includes preliminaries and "
                     "mobilisation cost components not measurable as work properly executed "
                     "under the Bill of Quantities. Based on the Site Handover Record's "
                     "measured progress (47% overall) applied at contract rates, adjusted for "
                     "items measured but not yet certified, we determine the value of work "
                     "properly executed at KLD 15,120,000, together with KLD 680,000 for "
                     "Materials credited per Asset Inventory AIV-KFI2-001, a total of KLD "
                     "15,800,000 -- an increase over the amount previously certified, "
                     "reflecting work executed but not yet included in a Statement at the "
                     "date of termination."),
            ("para", "3. DEMOBILISATION COSTS: We reject the claimed KLD 320,000 "
                     "demobilisation cost. Under Sub-Clause 15.4, a cost, loss or expense "
                     "arising from or in connection with the Contractor's own default, "
                     "including demobilisation following termination under Clause 15, is not "
                     "a sum properly due to the Contractor."),
            ("para", "4. UTILITY RELOCATION CREDIT: We accept, consistent with Progress "
                     "Assessment EPA-KFI2-001's own finding, that the Ramp C utility "
                     "relocation delay (resolved 15-Feb-2021, approximately 9 weeks late) is a "
                     "genuine factor, but limited to the Ramp C element alone; it does not "
                     "excuse the shortfall recorded at superstructure or signage/finishing "
                     "elements, which is the substantial basis for termination. We credit 5 "
                     "days against the liquidated damages period on this account, per "
                     "Liquidated Damages Assessment LDA-KFI2-001."),
            ("para", "5. LIQUIDATED DAMAGES: Per LDA-KFI2-001, liquidated damages of KLD "
                     "302,400 (14 days at KLD 21,600/day, after the 5-day utility credit) are "
                     "recoverable and are credited to the Employer in this account."),
            ("para", "6. NET BALANCE: Per Payment Statement PST-KFI2-011 and Retention "
                     "Calculation RET-KFI2-001, the net balance due, and full release of "
                     "retention, are determined as follows:"),
            ("table", {
                "headers": ["Item", "Amount (KLD)"],
                "rows": [
                    ["Value of work properly executed and Materials (para 2)", "15,800,000"],
                    ["Less: amount already certified and paid to date (PST-KFI2-011)",
                     "(14,345,000)"],
                    ["Less: liquidated damages (para 5 / LDA-KFI2-001)", "(302,400)"],
                    ["NET BALANCE DUE TO THE CONTRACTOR", "1,152,600"],
                ],
                "right_align_cols": [1],
                "bold_last_row": True,
            }),
            ("para", "7. RETENTION: Retention held to date (KLD 755,000, per RET-KFI2-001) is "
                     "included within, and released in full as part of, the net balance "
                     "determined above, the balance being due to the Contractor."),
            ("para", "A Final Payment Certificate for KLD 1,152,600, due to the Contractor, "
                     "will be issued for payment within the period stated in the Contract "
                     "Data."),
        ],
        closing_lines=["Signed: Engineer's Representative", "Ashgrove Infrastructure "
                       "Consultants"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 11 -- PST-KFI2-011
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="PST-KFI2-011",
        title="Payment Statement — Reconciliation of Amounts Certified and Paid to Date",
        doc_type="PAYMENT",
        doc_type_tag="PAYMENT STATEMENT",
        letterhead="ENGINEER",
        date="15-Sep-2021",
        from_="Ashgrove Infrastructure Consultants",
        to="Kaldera Metropolitan Development Authority",
        cc="Rennick Builders Ltd.",
        contract_no=KFI2_CONTRACT_NO,
        project_line=KFI2_PROJECT_LINE,
        letterhead_registry=KFI2_LETTERHEADS,
        subject="Payment Statement — Interim Payment Certificates 1-10, to Date of Termination",
        body=[
            ("para", "This statement reconciles amounts certified and paid under Interim "
                     "Payment Certificates 1 to 10, covering the period from the Commencement "
                     "Date (03-Jun-2019) to the last Statement submitted before termination "
                     "(31-May-2021), for the purposes of Employer's Final Account "
                     "EFA-KFI2-001."),
            ("table", {
                "headers": ["Item", "Amount (KLD)"],
                "rows": [
                    ["Gross value certified (IPCs 1-10)", "15,100,000"],
                    ["Less: retention withheld at 5%", "(755,000)"],
                    ["NET AMOUNT PAID TO CONTRACTOR TO DATE", "14,345,000"],
                ],
                "right_align_cols": [1],
                "bold_last_row": True,
            }),
            ("para", "No amount certified under IPCs 1-10 is in dispute; Contractor's "
                     "Financial Claim CFC-KFI2-001 does not challenge any previously certified "
                     "amount, only the valuation of work executed since the last Statement and "
                     "the treatment of retention and liquidated damages, addressed separately "
                     "in Retention Calculation RET-KFI2-001 and Liquidated Damages Assessment "
                     "LDA-KFI2-001."),
            ("para", "The net amount paid to date of KLD 14,345,000 is carried into Employer's "
                     "Final Account EFA-KFI2-001 as the deduction against the final measured "
                     "value."),
        ],
        closing_lines=["Prepared by: Ashgrove Infrastructure Consultants"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 12 -- RET-KFI2-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="RET-KFI2-001",
        title="Retention Calculation — Sub-Clause 15.4",
        doc_type="MEASUREMENT",
        doc_type_tag="RETENTION CALCULATION",
        letterhead="ENGINEER",
        date="15-Sep-2021",
        from_="Ashgrove Infrastructure Consultants",
        to="Kaldera Metropolitan Development Authority",
        cc="Rennick Builders Ltd.",
        contract_no=KFI2_CONTRACT_NO,
        project_line=KFI2_PROJECT_LINE,
        letterhead_registry=KFI2_LETTERHEADS,
        subject="Retention Calculation — Held to Date of Termination and Treatment Under "
                "Sub-Clause 15.4",
        body=[
            ("para", "This calculation records retention held as at the date of termination "
                     "and its treatment under Sub-Clause 15.4, for the purposes of Employer's "
                     "Final Account EFA-KFI2-001."),
            ("table", {
                "headers": ["Item", "Amount (KLD)"],
                "rows": [
                    ["Gross value certified to date (PST-KFI2-011)", "15,100,000"],
                    ["Retention Percentage (Contract Data Section 6)", "5%"],
                    ["Retention held to date", "755,000"],
                    ["Limit of Retention Money (Contract Data Section 6)", "1,800,000"],
                ],
                "right_align_cols": [1],
            }),
            ("para", "The Limit of Retention Money (KLD 1,800,000) was not reached; retention "
                     "continued to be deducted at 5% on every Statement to date of "
                     "termination, and the full KLD 755,000 remains held by the Employer as "
                     "at this calculation."),
            ("para", "Per Sub-Clause 15.4, Retention Money held at the date of termination is "
                     "included in, and released only to the extent, and at the time, the net "
                     "balance under that Sub-Clause is due to the Contractor. As determined in "
                     "Employer's Final Account EFA-KFI2-001, the net balance (KLD 1,152,600) "
                     "is due to the Contractor; the full retention of KLD 755,000 is "
                     "accordingly released as part of that balance, with no amount withheld."),
        ],
        closing_lines=["Prepared by: Ashgrove Infrastructure Consultants"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 13 -- LDA-KFI2-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="LDA-KFI2-001",
        title="Liquidated Damages Assessment — Sub-Clause 15.4",
        doc_type="MEASUREMENT",
        doc_type_tag="LIQUIDATED DAMAGES ASSESSMENT",
        letterhead="ENGINEER",
        date="15-Sep-2021",
        from_="Ashgrove Infrastructure Consultants",
        to="Kaldera Metropolitan Development Authority",
        cc="Rennick Builders Ltd.",
        contract_no=KFI2_CONTRACT_NO,
        project_line=KFI2_PROJECT_LINE,
        letterhead_registry=KFI2_LETTERHEADS,
        subject="Liquidated Damages Assessment — Period from Time for Completion to "
                "Termination",
        body=[
            ("para", "This assessment calculates liquidated damages accrued under Sub-Clause "
                     "15.4, for the period between the Time for Completion and the date of "
                     "termination, for the purposes of Employer's Final Account "
                     "EFA-KFI2-001."),
            ("table", {
                "headers": ["Item", "Value"],
                "rows": [
                    ["Time for Completion (Contract Data Section 3)", "02-Jun-2021"],
                    ["Date of termination (Termination Certificate ETC-KFI2-001)",
                     "21-Jun-2021"],
                    ["Gross period", "19 days"],
                    ["Less: credit for Ramp C utility relocation delay (EFA-KFI2-001, "
                     "para 4)", "(5 days)"],
                    ["Chargeable period", "14 days"],
                    ["Delay Damages Rate (Contract Data Section 7)", "KLD 21,600/day"],
                    ["LIQUIDATED DAMAGES DUE", "KLD 302,400"],
                ],
            }),
            ("para", "The chargeable period of 14 days is well within the Maximum Delay "
                     "Damages figure of KLD 3,600,000 (Contract Data Section 7); no cap "
                     "applies. This assessment does not extend liquidated damages beyond the "
                     "date of termination; Sub-Clause 15.4 credits the Employer for delay "
                     "damages only to that date, not to any later date on which the Works may "
                     "eventually be completed by others."),
            ("para", "The 5-day utility credit reflects the genuine, limited Ramp C delay "
                     "recorded in Progress Assessment EPA-KFI2-001 and accepted in "
                     "EFA-KFI2-001, and is not extended to any part of the shortfall at other "
                     "elements of the Works, which the Engineer's determination attributes to "
                     "the Contractor's own performance."),
        ],
        closing_lines=["Prepared by: Ashgrove Infrastructure Consultants"],
        scenario=SCENARIO,
    ),

    # ------------------------------------------------------------------
    # Document 14 -- FCR-KFI2-001
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="FCR-KFI2-001",
        title="Final Correspondence — Employer's Final Account EFA-KFI2-001",
        doc_type="CORRESPONDENCE",
        doc_type_tag="CORRESPONDENCE",
        letterhead="CONTRACTOR",
        date="29-Sep-2021",
        from_="Project Manager, Rennick Builders Ltd.",
        to="Engineer, Ashgrove Infrastructure Consultants",
        cc="Kaldera Metropolitan Development Authority",
        contract_no=KFI2_CONTRACT_NO,
        project_line=KFI2_PROJECT_LINE,
        letterhead_registry=KFI2_LETTERHEADS,
        subject="Final Correspondence — Employer's Final Account EFA-KFI2-001",
        body=[
            ("para", "We refer to Employer's Final Account EFA-KFI2-001 dated 15-Sep-2021, "
                     "determining a net balance of KLD 1,152,600 due to us, including full "
                     "release of retention."),
            ("para", "We do not accept the rejection of our KLD 320,000 demobilisation cost "
                     "claim, nor the valuation of work and materials at KLD 15,800,000 rather "
                     "than the KLD 17,200,000 claimed in CFC-KFI2-001, and we reserve our "
                     "position on both points. We note the Engineer's acceptance of a 5-day "
                     "credit for the Ramp C utility relocation delay against liquidated "
                     "damages, though we consider a longer credit would have been justified "
                     "given the delay's effect on our wider sequencing."),
            ("para", "Notwithstanding the above, we do not intend to escalate this matter "
                     "further at this time, and confirm receipt of the net balance of KLD "
                     "1,152,600 will be treated as final settlement of the amounts addressed "
                     "in EFA-KFI2-001, without prejudice to our reserved position should we "
                     "elect to pursue it under the Contract's dispute resolution provisions at "
                     "a later date."),
            ("para", "We confirm all Contractor's Equipment has been removed from Site and "
                     "note the Engineer's confirmation that no further outstanding matter "
                     "affects this account."),
        ],
        closing_lines=["Regards,", "Project Manager", "Rennick Builders Ltd."],
        scenario=SCENARIO,
    ),
]
