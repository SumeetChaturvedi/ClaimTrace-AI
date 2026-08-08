"""Verbatim structured data for the 4 approved Contract Package documents,
transcribed exactly from the persisted, already-corrected source files in
backend/storage/contracts/*.txt (the version with the reformatted two-line
sub-clause headings from Dataset V2 Implementation Task 01 -- unchanged
here). Dates normalized from "5 December 2020" to the project's DD-Mon-YYYY
display convention (A.10); no substantive wording altered.

These 4 documents use DocumentType CONTRACT, a canonical type not
exercised by Scenarios 1-9, and are letterheaded "JOINT" (the existing
neutral, project-branded identity already used for JIR-NRB4-001 in
Scenario 9) since they are contract instruments belonging to the project
as a whole, not correspondence from a single party. No new template
family or rendering primitive was required -- this reuses the existing
heading/subheading/para/bullet block system.
"""

from pdf_template import DocumentSpec

DOCUMENTS: list[DocumentSpec] = [

    # ------------------------------------------------------------------
    # NRB4-GC-2020 -- General Conditions (Extract)
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="NRB4-GC-2020",
        title="Conditions of Contract — General Conditions (Extract of Relevant Clauses)",
        doc_type="CONTRACT",
        doc_type_tag="GENERAL CONDITIONS (EXTRACT)",
        letterhead="JOINT",
        date="05-Dec-2020",
        from_="National Highways Infrastructure Authority (Employer)",
        to="Meridian Engineering Consultants (Engineer); Sagara Constructions Pvt. Ltd. "
           "(Contractor)",
        extra_meta=[
            ("Employer", "National Highways Infrastructure Authority"),
            ("Engineer", "Meridian Engineering Consultants"),
            ("Contractor", "Sagara Constructions Pvt. Ltd."),
        ],
        body=[
            ("subheading", "PREFATORY NOTE"),
            ("para", "This document reproduces, in extract form, those Clauses and "
                     "Sub-Clauses of the General Conditions of Contract considered relevant "
                     "to the day-to-day administration of the Contract. It is not a "
                     "reproduction of the Contract in full, and no Clause or Sub-Clause not "
                     "appearing in this extract should be taken to be absent from the "
                     "Contract or of lesser standing than those which do appear. Terms "
                     "defined elsewhere in the Contract carry the same meaning wherever used "
                     "in this extract. Numbering follows the Contract's own Clause "
                     "structure; Clauses omitted from this extract are indicated only by the "
                     "gaps in numbering."),

            ("heading", "CLAUSE 1 — GENERAL PROVISIONS"),
            ("subheading", "1.3 — Notices"),
            ("para", "Wherever the Contract requires a notice, consent, approval, "
                     "certificate, determination or instruction to be given or issued by one "
                     "Party to the other, or by the Engineer to either Party, it shall be in "
                     "writing and shall be treated as validly given only once received at "
                     "the address nominated by the recipient for that purpose in the "
                     "Contract Data, or at such other address as the recipient may from time "
                     "to time nominate in writing."),
            ("para", "A notice delivered by hand or by registered post shall be treated as "
                     "received on the date of actual delivery as evidenced by a signed "
                     "receipt. A notice sent by electronic mail to a nominated electronic "
                     "address shall be treated as received at the time shown on the sender's "
                     "transmission record, unless the sender receives an automated "
                     "notification that delivery has failed, in which case the notice shall "
                     "be treated as not given until delivered by another means permitted "
                     "under this Sub-Clause."),
            ("para", "Every notice shall identify the Clause or Sub-Clause of the Contract "
                     "under which it is given and shall set out, with reasonable "
                     "particularity, the matter to which it relates. A notice which does not "
                     "do so may be returned by the recipient with a request for "
                     "clarification, and time shall not begin to run against the recipient "
                     "until a compliant notice is received."),
            ("para", "Where this Contract states a period within which a notice must be "
                     "given, that period shall be calculated from the date on which the "
                     "Party giving notice first became aware, or ought reasonably to have "
                     "become aware, of the matter giving rise to the notice, and not from "
                     "any later date on which the consequences of that matter became fully "
                     "apparent. Saturdays, Sundays and public holidays observed at the Site "
                     "shall be included in the calculation of any such period unless the "
                     "Contract expressly provides otherwise."),
            ("para", "Nothing in this Sub-Clause relieves either Party or the Engineer of "
                     "any other requirement as to the form, content or timing of a "
                     "particular notice set out elsewhere in the Contract, and where such a "
                     "requirement conflicts with this Sub-Clause, the more specific "
                     "requirement shall prevail."),

            ("heading", "CLAUSE 3 — THE ENGINEER"),
            ("subheading", "3.3 — Engineer's Instructions"),
            ("para", "The Engineer may, at any time, issue to the Contractor such "
                     "instructions as the Engineer considers necessary for the proper "
                     "execution of the Works and the remedying of any defect therein, "
                     "consistent with the Contract. Every instruction shall be given in "
                     "writing. Where the Engineer, or a person authorised by the Engineer, "
                     "gives an instruction orally in circumstances of urgency, that "
                     "instruction shall be confirmed in writing by the Engineer within two "
                     "days, and the Contractor shall likewise confirm in writing, within the "
                     "same period, any oral instruction upon which the Contractor intends to "
                     "act, failing which the instruction shall be of no effect."),
            ("para", "The Contractor shall comply with every instruction validly given under "
                     "this Sub-Clause, save where compliance would require the Contractor to "
                     "act unlawfully or would be rendered impossible by circumstances beyond "
                     "the Contractor's control, in which case the Contractor shall notify "
                     "the Engineer without delay, stating the grounds of objection."),
            ("para", "An instruction given under this Sub-Clause shall not, of itself, "
                     "constitute a Variation. Where an instruction has the effect described "
                     "in Sub-Clause 13.1, it shall be treated as an instruction to vary the "
                     "Works and dealt with accordingly under Clause 13, and the Contractor "
                     "shall promptly draw to the Engineer's attention any instruction which "
                     "the Contractor considers to have that effect, without prejudice to the "
                     "Contractor's obligation to comply with the instruction in the "
                     "meantime."),
            ("para", "The Engineer may delegate authority to give instructions under this "
                     "Sub-Clause to a named Engineer's Representative or other authorised "
                     "person, by notice to the Contractor stating the scope of the "
                     "delegation. The Contractor shall be entitled to treat any instruction "
                     "given within the stated scope of such a delegation as an instruction "
                     "of the Engineer for all purposes of the Contract, until the delegation "
                     "is withdrawn or varied by further notice."),
            ("para", "Where the Contractor considers that an instruction is ambiguous, or is "
                     "inconsistent with another instruction or with the Contract, the "
                     "Contractor shall notify the Engineer promptly, and the Engineer shall "
                     "clarify or resolve the inconsistency within seven days, during which "
                     "period the Contractor shall proceed on the basis of a reasonable "
                     "interpretation of the instruction unless directed otherwise."),

            ("heading", "CLAUSE 4 — THE CONTRACTOR"),
            ("subheading", "4.1 — Contractor's General Obligations"),
            ("para", "The Contractor shall design, to the extent (if any) stated in the "
                     "Employer's Requirements, and shall execute and complete the Works in "
                     "accordance with the Contract, and shall remedy any defects in the "
                     "Works, using materials, plant and workmanship of the standard "
                     "specified in the Employer's Requirements and the Specification. Save "
                     "to the extent so stated, the design of the Permanent Works is the "
                     "Employer's responsibility, and the Contractor shall not depart from "
                     "the Drawings issued by the Engineer without an instruction under "
                     "Clause 3 or Clause 13."),
            ("para", "The Contractor shall be responsible for the adequacy, stability and "
                     "safety of all Site operations, all methods of construction, and all "
                     "Temporary Works, whether or not any design for Temporary Works has "
                     "been reviewed or commented upon by the Engineer."),
            ("para", "If the Contractor becomes aware of an error, omission or ambiguity in "
                     "a Drawing, Specification or other document issued by or on behalf of "
                     "the Employer, the Contractor shall notify the Engineer promptly upon "
                     "becoming aware of it, and shall not proceed with the affected part of "
                     "the Works until the Engineer has issued a clarifying instruction, save "
                     "where the Contract or an instruction of the Engineer requires "
                     "otherwise."),
            ("para", "The Contractor shall provide all supervision, labour, materials, "
                     "Contractor's Equipment and other things, whether of a temporary or "
                     "permanent nature, required for the Works, except to the extent "
                     "otherwise stated in the Contract."),
            ("para", "The Contractor shall conduct its operations so as not to interfere "
                     "unnecessarily with the convenience of the public, or the access to and "
                     "use of any adjoining land, and shall comply with all applicable laws, "
                     "permits and approvals relevant to the execution of the Works."),
            ("para", "The Contractor shall appoint a Contractor's Representative, notified "
                     "to the Engineer, who shall have full authority to act on the "
                     "Contractor's behalf for the purposes of the Contract, and through whom "
                     "all instructions of the Engineer shall ordinarily be communicated to "
                     "the Contractor's personnel."),
            ("para", "Compliance by the Contractor with an instruction, approval or consent "
                     "of the Engineer shall not relieve the Contractor of any obligation "
                     "under this Sub-Clause, save to the extent that the Contract expressly "
                     "provides otherwise."),

            ("heading", "CLAUSE 8 — COMMENCEMENT, DELAYS AND SUSPENSION"),
            ("subheading", "8.4 — Extension of Time for Completion"),
            ("para", "The Contractor shall be entitled to an extension of the Time for "
                     "Completion if and to the extent that completion of the Works for the "
                     "purposes of Taking-Over is or will be delayed by any of the following "
                     "causes:"),
            ("bullet", "(a) a Variation instructed under Clause 13, unless the Variation was "
                       "itself necessitated by a breach of the Contract by the Contractor;"),
            ("bullet", "(b) a cause of delay for which the Contract expressly entitles the "
                       "Contractor to an extension, including exceptionally adverse "
                       "conditions of a kind that a reasonably experienced contractor could "
                       "not have foreseen at the date of the Letter of Acceptance, but "
                       "excluding any condition, event or restriction addressed elsewhere in "
                       "the Contract as a foreseeable or contractually anticipated risk;"),
            ("bullet", "(c) any act, omission or default of the Employer, the Engineer, or "
                       "of another contractor engaged by the Employer, which impedes the "
                       "Contractor's progress; or"),
            ("bullet", "(d) any other cause of delay which the Contract expressly states "
                       "shall entitle the Contractor to an extension of time."),
            ("para", "An extension shall be granted only where the Contractor has given "
                     "notice of the delay in accordance with Sub-Clause 20.1, and has, upon "
                     "request, provided the Engineer with such particulars of the delay and "
                     "its likely effect on the programme as the Engineer may reasonably "
                     "require."),
            ("para", "Upon receiving such particulars, the Engineer shall assess the delay "
                     "and shall notify the Contractor of the extension (if any) granted, "
                     "giving reasons, within twenty-eight days of receiving particulars "
                     "sufficient to make an assessment, or such further period as the "
                     "Engineer may reasonably require where the full effect of the delay "
                     "cannot yet be determined, in which case the Engineer shall make an "
                     "interim determination and a final determination once the effect is "
                     "known."),
            ("para", "Where a delay results partly from a cause described above and partly "
                     "from a cause for which the Contractor is responsible, the Engineer "
                     "shall apportion the resulting delay between the two causes to the "
                     "extent reasonably practicable, and shall grant an extension only in "
                     "respect of the portion attributable to a cause described above."),
            ("para", "A revision to the Time for Completion granted under this Sub-Clause "
                     "does not, of itself, entitle the Contractor to any additional payment; "
                     "entitlement to payment in connection with a cause of delay is to be "
                     "established, where applicable, under Sub-Clause 20.1 or such other "
                     "provision of the Contract as applies to that cause."),

            ("subheading", "8.7 — Delay Damages"),
            ("para", "If the Contractor fails to achieve Taking-Over of the Works, or any "
                     "Section for which a separate Time for Completion is stated, within the "
                     "Time for Completion as it may have been extended under Sub-Clause 8.4, "
                     "the Contractor shall pay to the Employer delay damages for every day "
                     "which elapses between the Time for Completion and the date stated in "
                     "the relevant Taking-Over Certificate, at the rate stated in the "
                     "Contract Data, subject to the maximum amount (if any) stated in the "
                     "Contract Data."),
            ("para", "Delay damages payable under this Sub-Clause represent a genuine "
                     "pre-estimate, agreed between the Parties, of the loss likely to be "
                     "suffered by the Employer as a result of late completion, and are not a "
                     "penalty. The Employer shall not be required to prove the amount of its "
                     "actual loss in order to recover delay damages, and payment of delay "
                     "damages shall be the Employer's sole and exclusive remedy against the "
                     "Contractor for the Contractor's failure to achieve the Time for "
                     "Completion, without prejudice to any other remedy available to the "
                     "Employer in respect of a different breach of the Contract."),
            ("para", "The Engineer may certify the deduction of delay damages accrued under "
                     "this Sub-Clause from any amount otherwise due to the Contractor under "
                     "Clause 14, and shall notify the Contractor of the basis of any such "
                     "deduction at the time of certification."),
            ("para", "Where an extension of time is subsequently granted under Sub-Clause "
                     "8.4 in respect of a period for which delay damages have already been "
                     "deducted, the Employer shall repay to the Contractor, without "
                     "interest, the amount of delay damages attributable to that period "
                     "within the period stated for payment under Sub-Clause 14.7."),
            ("para", "Once the maximum amount of delay damages (if stated in the Contract "
                     "Data) has been reached, the Contractor shall have no further liability "
                     "under this Sub-Clause for continuing delay, without prejudice to the "
                     "Employer's other rights and remedies under the Contract or otherwise "
                     "in respect of the Contractor's failure to complete the Works."),

            ("heading", "CLAUSE 13 — VARIATIONS AND ADJUSTMENTS"),
            ("subheading", "13.1 — Right to Vary"),
            ("para", "The Engineer may, at any time before the issue of the Taking-Over "
                     "Certificate for the Works, initiate a Variation, either by instructing "
                     "the Contractor to carry out the Variation or by requesting the "
                     "Contractor to submit a proposal for a Variation before an instruction "
                     "is given."),
            ("para", "A Variation may include any of the following: a change to the "
                     "quantities of an item of work included in the Contract; a change to "
                     "the quality, character or other characteristic of an item of work; a "
                     "change to the levels, lines, position or dimensions of any part of the "
                     "Works; the omission of work, save that work may not be omitted for the "
                     "purpose of having it carried out by another contractor or by the "
                     "Employer's own forces; any additional work necessary for the "
                     "completion of the Works; or a change to the sequence or timing of "
                     "execution of the Works."),
            ("para", "The Contractor shall not vary the Works except pursuant to an "
                     "instruction given under this Sub-Clause, or as otherwise agreed in "
                     "writing between the Parties. Work carried out by the Contractor "
                     "otherwise than pursuant to such an instruction or agreement shall not "
                     "entitle the Contractor to additional payment or time, save to the "
                     "extent the Engineer subsequently confirms the work in writing as an "
                     "instructed Variation."),
            ("para", "Where the Engineer requests a proposal under this Sub-Clause, the "
                     "Contractor is not obliged to proceed with the work described in the "
                     "request unless and until an instruction to vary is subsequently given, "
                     "and the request itself shall not be treated as an instruction for the "
                     "purposes of this Clause."),
            ("para", "The right to instruct a Variation under this Sub-Clause is subject to "
                     "any threshold or additional approval requirement stated elsewhere in "
                     "the Contract in respect of Variations of a stated estimated value, and "
                     "an instruction given without the approval so required shall not bind "
                     "the Employer as against the Contractor unless and until that approval "
                     "is obtained or the Employer is estopped from denying its validity."),

            ("subheading", "13.3 — Variation Procedure"),
            ("para", "Where the Engineer requests a proposal under Sub-Clause 13.1, the "
                     "Contractor shall respond in writing within the period stated in the "
                     "request, or within fourteen days if no period is stated, either "
                     "submitting a proposal comprising a description of the work to be "
                     "carried out, the effect (if any) on the programme for completion, and "
                     "the Contractor's estimate of the cost, or explaining in writing why "
                     "the Contractor is unable to comply, or is unable to comply within the "
                     "period requested."),
            ("para", "Following receipt of a proposal, or upon deciding to proceed without "
                     "first requesting one, the Engineer shall issue an instruction to the "
                     "Contractor to carry out the Variation, confirm that no Variation is to "
                     "proceed, or request the Contractor to revise the proposal. An "
                     "instruction to carry out a Variation shall be given in writing in "
                     "accordance with Sub-Clause 3.3."),
            ("para", "The value of a Variation shall be determined by applying the rates and "
                     "prices in the Bill of Quantities to the varied work, where the varied "
                     "work is of similar character and executed under similar conditions to "
                     "work priced in the Bill of Quantities. Where no such rate or price "
                     "exists, or where the character or conditions of the varied work differ "
                     "materially, a new rate or price shall be agreed between the Engineer "
                     "and the Contractor or, failing agreement, determined by the Engineer, "
                     "having regard to the rates and prices in the Bill of Quantities so far "
                     "as reasonably applicable and to the reasonable cost of executing the "
                     "work."),
            ("para", "The Contractor shall proceed with the execution of an instructed "
                     "Variation without delay, notwithstanding that the value of the "
                     "Variation has not yet been agreed or determined, and any disagreement "
                     "as to value shall be dealt with under Sub-Clause 20.1 without "
                     "suspending performance of the instructed work, save where the Contract "
                     "expressly entitles the Contractor to suspend performance pending "
                     "payment."),
            ("para", "The Engineer shall include the value of Variations instructed and "
                     "executed, whether or not finally agreed, in the calculation of amounts "
                     "due under Clause 14, on the basis of the Engineer's then-current "
                     "assessment, subject to later adjustment once the value of the "
                     "Variation is finally agreed or determined."),

            ("heading", "CLAUSE 14 — CONTRACT PRICE AND PAYMENT"),
            ("subheading", "14.3 — Application for Interim Payment Certificates"),
            ("para", "The Contractor shall submit to the Engineer, at the end of each month, "
                     "a Statement in the form and number of copies stated in the Contract "
                     "Data, showing in detail the amounts to which the Contractor considers "
                     "itself entitled, including the estimated value of the Permanent and "
                     "Temporary Works executed up to the end of that month, together with "
                     "such supporting records, measurements and calculations as the Engineer "
                     "may reasonably require to verify the amounts claimed."),
            ("para", "Each Statement shall separately identify the value of work executed "
                     "under the original Bill of Quantities, the value of work executed "
                     "pursuant to instructed Variations, whether or not finally valued, and "
                     "any amount claimed under Sub-Clause 20.1 which has, by the date of the "
                     "Statement, been notified to the Engineer with sufficient particulars "
                     "for its value to be estimated."),
            ("para", "The Engineer shall review each Statement and shall be entitled to "
                     "exclude or adjust any amount which is not, in the Engineer's opinion, "
                     "adequately substantiated by the records and measurements provided, or "
                     "which has not been executed in accordance with the Contract, giving "
                     "reasons for any such exclusion or adjustment to the Contractor in "
                     "writing."),
            ("para", "From the amount otherwise due, there shall be deducted retention at "
                     "the percentage stated in the Contract Data, until the cumulative "
                     "amount retained reaches the limit (if any) stated in the Contract "
                     "Data, after which no further retention shall be deducted from amounts "
                     "subsequently certified."),
            ("para", "A Statement which is not submitted in the form, or with the supporting "
                     "information, required by this Sub-Clause may be returned by the "
                     "Engineer for correction and resubmission, and the periods stated in "
                     "Sub-Clause 14.7 shall run from the date of receipt of a compliant "
                     "Statement."),

            ("subheading", "14.7 — Payment"),
            ("para", "The Engineer shall, within the period stated in the Contract Data "
                     "after receiving a Statement submitted in accordance with Sub-Clause "
                     "14.3, issue to the Employer, with a copy to the Contractor, an Interim "
                     "Payment Certificate stating the amount which the Engineer considers "
                     "due, together with such supporting particulars as enable the "
                     "Contractor to reconcile the certified amount against the Statement "
                     "submitted."),
            ("para", "The Employer shall pay to the Contractor the amount certified by the "
                     "Engineer within the period stated in the Contract Data after the date "
                     "of the Interim Payment Certificate."),
            ("para", "If the Employer fails to pay a certified amount within the period "
                     "stated in this Sub-Clause, the Contractor shall be entitled to receive "
                     "financing charges on the overdue amount, compounded monthly, at the "
                     "rate stated in the Contract Data, for the period of the delay in "
                     "payment, without prejudice to any other right or remedy available to "
                     "the Contractor under the Contract."),
            ("para", "The Employer may withhold or set off against a certified amount only "
                     "such sum as is properly due to the Employer under the Contract, and "
                     "only where the Employer has given the Contractor notice, with "
                     "particulars, of the amount withheld and the grounds for withholding "
                     "it, not later than the date payment would otherwise fall due."),
            ("para", "Payment of an amount in an Interim Payment Certificate shall not be "
                     "taken as an admission by the Employer or the Engineer of the accuracy "
                     "of any Statement, record or claim on which the certified amount is "
                     "based, and any amount overpaid or underpaid as a result of a "
                     "subsequent correction may be adjusted in a later Interim Payment "
                     "Certificate."),

            ("heading", "CLAUSE 20 — CLAIMS"),
            ("subheading", "20.1 — Contractor's Claims"),
            ("para", "Where the Contractor considers that it is entitled to an extension of "
                     "the Time for Completion under Sub-Clause 8.4, or to additional payment "
                     "under any provision of the Contract, or otherwise in connection with "
                     "the execution of the Works, the Contractor shall give notice to the "
                     "Engineer describing the event or circumstance giving rise to the "
                     "claim."),
            ("para", "Notice under this Sub-Clause shall be given not later than "
                     "twenty-eight days after the Contractor became aware, or ought "
                     "reasonably to have become aware, of the event or circumstance. If the "
                     "Contractor fails to give notice within this period, the Contractor "
                     "shall not be entitled to any extension of time or additional payment "
                     "in respect of that event or circumstance, and the Employer shall be "
                     "discharged from all liability in connection with it."),
            ("para", "Following a valid notice, the Contractor shall keep such "
                     "contemporaneous records as may reasonably be necessary to substantiate "
                     "the claim, and shall permit the Engineer to inspect such records. "
                     "Within forty-two days of the notice, or such other period as may be "
                     "agreed, the Contractor shall submit a fully detailed claim, including "
                     "the contractual or other basis of the claim and supporting particulars "
                     "of the extension of time or additional payment claimed. Where the "
                     "effect of the event or circumstance is continuing, the Contractor "
                     "shall submit interim particulars at monthly intervals thereafter and a "
                     "final claim within twenty-eight days of the effects ceasing."),
            ("para", "The Engineer shall respond to a claim submitted under this Sub-Clause "
                     "with a determination, approving, rejecting or approving in part the "
                     "extension of time or additional payment claimed, giving reasons for "
                     "any part not approved, within forty-two days of receiving the fully "
                     "detailed claim, or such particulars as are reasonably sufficient for "
                     "the Engineer to make a determination, whichever is the later."),
            ("para", "An extension of time or additional payment shall not be granted under "
                     "this Sub-Clause otherwise than in accordance with a determination of "
                     "the Engineer made under this Sub-Clause, or by agreement between the "
                     "Parties, and nothing in this Sub-Clause limits either Party's rights "
                     "under the dispute resolution provisions of the Contract in respect of "
                     "a determination with which that Party disagrees."),

            ("total_box", "[END OF EXTRACT]"),
        ],
        closing_lines=[],
        scenario=0,
    ),

    # ------------------------------------------------------------------
    # NRB4-PC-2020 -- Particular Conditions
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="NRB4-PC-2020",
        title="Conditions of Contract — Particular Conditions",
        doc_type="CONTRACT",
        doc_type_tag="PARTICULAR CONDITIONS",
        letterhead="JOINT",
        date="05-Dec-2020",
        from_="National Highways Infrastructure Authority (Employer)",
        to="Meridian Engineering Consultants (Engineer); Sagara Constructions Pvt. Ltd. "
           "(Contractor)",
        extra_meta=[
            ("Employer", "National Highways Infrastructure Authority"),
            ("Engineer", "Meridian Engineering Consultants"),
            ("Contractor", "Sagara Constructions Pvt. Ltd."),
        ],
        body=[
            ("subheading", "PREFATORY NOTE"),
            ("para", "These Particular Conditions amend and supplement the General "
                     "Conditions of Contract in the respects, and to the extent, set out "
                     "below. Where a provision of these Particular Conditions states that a "
                     "Sub-Clause of the General Conditions is replaced, the replacement "
                     "provision applies in place of the General Conditions provision for all "
                     "purposes of the Contract. Where a provision states that a Sub-Clause is "
                     "supplemented, the General Conditions provision continues to apply, read "
                     "together with the additional matter set out below. Save as expressly "
                     "stated in these Particular Conditions, the General Conditions remain of "
                     "full force and effect. Any Sub-Clause not mentioned in these Particular "
                     "Conditions is unamended."),

            ("heading", "PART A — AMENDMENTS RELATING TO CLAUSE 1 (GENERAL PROVISIONS)"),
            ("subheading", "A.1 — Notice Addresses and Communication Protocol"),
            ("para", "Sub-Clause 1.3 is supplemented as follows. For the purposes of the "
                     "Contract, the addresses for service of notices are those stated in the "
                     "Contract Data, or such substitute address as a Party or the Engineer "
                     "may nominate by not less than seven days' prior written notice to the "
                     "others. Each Party shall maintain a Site office at the Site at which "
                     "notices addressed to that Party's Representative may be delivered by "
                     "hand during normal working hours, in addition to any postal or "
                     "electronic address nominated."),
            ("para", "All correspondence of a technical or contractual nature, including but "
                     "not limited to requests for information, submittals, notices of delay "
                     "or claim, and Statements under Clause 14, shall be logged by the sender "
                     "under a sequential reference number identifying the originating Party "
                     "and the calendar year, and the recipient shall acknowledge receipt in "
                     "writing, by return correspondence or by electronic mail, within two "
                     "working days. Failure to acknowledge receipt does not affect the "
                     "validity or effective date of a notice given in accordance with "
                     "Sub-Clause 1.3, but a Party which repeatedly fails to acknowledge "
                     "correspondence may be required by the Engineer to establish an "
                     "alternative communication protocol."),
            ("para", "Where these Particular Conditions or the Engineer require a document "
                     "to be submitted in a stated number of copies, one copy shall in every "
                     "case additionally be provided in electronic format unless the Engineer "
                     "directs otherwise."),

            ("heading", "PART B — AMENDMENTS RELATING TO CLAUSE 3 (THE ENGINEER)"),
            ("subheading", "B.1 — Engineer's Delegated Representative"),
            ("para", "Sub-Clause 3.3 is supplemented as follows. The Engineer shall appoint, "
                     "and notify to the Contractor before the Commencement Date, a Resident "
                     "Engineer who shall be based at the Site and who is hereby delegated the "
                     "Engineer's authority to give day-to-day instructions under Sub-Clause "
                     "3.3, to witness and approve measurement under Clause 14, and to grant "
                     "or withhold consent at Hold Points under Part C.6 of these Particular "
                     "Conditions. The Resident Engineer's authority does not extend to the "
                     "determination of claims under Sub-Clause 20.1, the issue of Variation "
                     "instructions with an estimated value exceeding the threshold stated in "
                     "Part E.1 below, or any matter which the Engineer notifies the "
                     "Contractor in writing is reserved to the Engineer personally."),
            ("para", "Any instruction given by the Resident Engineer within the scope of the "
                     "delegation recorded under this Part shall be treated as an instruction "
                     "of the Engineer for all purposes of the Contract. The Engineer shall "
                     "promptly notify the Contractor in writing of any replacement of the "
                     "Resident Engineer, or any variation to the scope of the delegation "
                     "described above."),
            ("subheading", "B.2 — Monthly Progress Meetings"),
            ("para", "A progress meeting shall be held monthly, at the Site or at such other "
                     "place as the Engineer may direct, on a date fixed by the Engineer's "
                     "Representative and notified to the Contractor not less than five days "
                     "in advance. The meeting shall be attended by the Contractor's "
                     "Representative, or a duly authorised deputy, together with such other "
                     "personnel of either Party as the matters on the agenda may require, and "
                     "shall address progress against the current programme, outstanding "
                     "instructions and submittals, anticipated delays, and any other matter "
                     "either Party wishes to raise."),
            ("para", "The Engineer shall issue minutes of each progress meeting within five "
                     "working days of the meeting. A matter recorded in the minutes shall be "
                     "treated as agreed unless a Party notifies the Engineer in writing, "
                     "within five working days of issue, of a specific matter it disputes, in "
                     "which case the minutes shall stand save as to the disputed matter, "
                     "which shall be recorded as unresolved and addressed at the following "
                     "meeting or by separate correspondence."),

            ("heading", "PART C — AMENDMENTS RELATING TO CLAUSE 4 (THE CONTRACTOR)"),
            ("subheading", "C.1 — Working Hours and Permitted Construction Windows"),
            ("para", "Sub-Clause 4.1 is supplemented as follows. Save as provided below, the "
                     "Contractor shall carry out the Works only between 07:00 and 19:00 "
                     "hours, Monday to Saturday inclusive. Work on Sundays, on public "
                     "holidays observed at the Site, or outside the hours stated above, shall "
                     "not be carried out without the prior written consent of the Engineer, "
                     "which shall not be unreasonably withheld where the Contractor "
                     "demonstrates a genuine operational need, but which the Engineer may "
                     "make subject to conditions addressing noise, lighting, traffic "
                     "management or other matters affecting persons or property in the "
                     "vicinity of the Site."),
            ("subheading", "C.2 — Site Access Restrictions"),
            ("para", "The Contractor's access to and use of the Site shall be confined to "
                     "the areas identified for that purpose in the Drawings and shall at all "
                     "times respect any right of way, easement, or restriction affecting land "
                     "within or adjacent to the Site of which the Engineer notifies the "
                     "Contractor. The Contractor shall maintain unobstructed access for the "
                     "Suvarna District Water Resources Department and other authorities "
                     "having a statutory right of access to the river and its banks, and "
                     "shall not store materials, plant or spoil within any setback or buffer "
                     "area identified in the Employer's Requirements without the Engineer's "
                     "prior written consent."),
            ("subheading", "C.3 — River Environmental Protection Requirements"),
            ("para", "The Contractor shall carry out the Works in accordance with the "
                     "conditions attached to the environmental clearance issued in respect of "
                     "the Works by the Vantara Environmental Protection Board, a copy of "
                     "which has been provided to the Contractor, and any subsequent condition "
                     "notified to the Contractor by the Engineer. Without limiting the "
                     "foregoing, the Contractor shall install and maintain silt curtains and "
                     "other turbidity control measures for the duration of any in-river work, "
                     "shall not discharge fuel, oil, wash-water or other effluent into the "
                     "river or its banks, and shall store fuel and hazardous materials only "
                     "within bunded areas approved by the Engineer."),
            ("para", "The Contractor shall engage, at its own cost, an environmental monitor "
                     "to record water quality and other parameters required by the "
                     "environmental clearance, and shall provide monitoring records to the "
                     "Engineer on a monthly basis. Nothing in this Part C.3 affects the "
                     "operation of the Monsoon Period restriction set out in Part D.1 below, "
                     "which applies independently of, and in addition to, any environmental "
                     "clearance condition."),
            ("subheading", "C.4 — Utility Coordination Responsibilities"),
            ("para", "The Employer shall be responsible for procuring the relocation, "
                     "diversion or protection of any utility, apparatus or installation shown "
                     "on the Drawings as requiring relocation, save to the extent the "
                     "Employer's Requirements state that responsibility rests with the "
                     "Contractor. The Contractor shall coordinate the sequencing and "
                     "programming of its own operations with the owners of any utility "
                     "notified to the Contractor by the Engineer as crossing, adjacent to, or "
                     "otherwise affecting the Site, and shall afford such owners reasonable "
                     "access to carry out relocation or protective works."),
            ("para", "If the Contractor encounters, in the course of executing the Works, a "
                     "utility, apparatus or installation not shown on the Drawings and not "
                     "otherwise disclosed to the Contractor in writing before the "
                     "Commencement Date, the Contractor shall cease work in the immediate "
                     "vicinity to the extent necessary for safety, shall notify the Engineer "
                     "without delay, and shall thereafter comply with the Engineer's "
                     "instructions as to how the Works are to proceed in that vicinity, "
                     "without prejudice to any entitlement the Contractor may have under "
                     "Sub-Clause 8.4 or Sub-Clause 20.1 in consequence."),
            ("subheading", "C.5 — Key Personnel"),
            ("para", "The Contractor's Representative and the Engineer's Resident Engineer "
                     "appointed under Part B.1 above are designated as Key Personnel for the "
                     "purposes of the Contract. Neither Party shall replace or reassign its "
                     "Key Personnel without giving the other not less than fourteen days' "
                     "prior written notice, save in case of incapacity, resignation or other "
                     "circumstance beyond that Party's reasonable control, in which case "
                     "notice shall be given as soon as practicable. A replacement for a Key "
                     "Personnel role shall have qualifications and experience reasonably "
                     "equivalent to those of the person replaced, and the appointing Party "
                     "shall provide the other Party with a curriculum vitae or equivalent "
                     "summary of the replacement's qualifications upon request."),
            ("subheading", "C.6 — Quality and Inspection Requirements"),
            ("para", "The Contractor shall carry out sampling and testing of materials and "
                     "workmanship at the frequency, and to the standards, stated in the "
                     "Employer's Requirements, using the independent testing laboratories "
                     "nominated by the Engineer for that purpose. Test results shall be "
                     "provided to the Engineer within five working days of the relevant "
                     "test."),
            ("para", "The Employer's Requirements identify certain stages of the Works as "
                     "Hold Points, beyond which the Contractor shall not proceed without the "
                     "prior written consent of the Engineer or the Resident Engineer. The "
                     "Contractor shall request such consent not less than two working days "
                     "before the Hold Point is reached, providing such records and test "
                     "results as are then available, and shall maintain a register of Hold "
                     "Points reached, consents requested, and consents given or withheld, "
                     "which shall be available for the Engineer's inspection at all times. "
                     "Proceeding beyond a Hold Point without the consent required by this "
                     "Part C.6 shall be at the Contractor's own risk as to any consequence of "
                     "doing so."),
            ("subheading", "C.7 — Record Keeping Requirements"),
            ("para", "The Contractor shall maintain, and make available to the Engineer on "
                     "request, a Site diary recording daily weather conditions, labour and "
                     "plant deployed, work carried out, and any event of note, and shall "
                     "submit a Daily Progress Report to the Engineer in a form to be agreed "
                     "within thirty days of the Commencement Date. The Contractor shall "
                     "retain all records relevant to the execution of the Works, including "
                     "but not limited to Site diaries, Daily Progress Reports, measurement "
                     "records, test results and correspondence, for a period of not less "
                     "than three years following the issue of the Performance Certificate, "
                     "and shall provide copies to the Engineer upon reasonable request during "
                     "that period."),
            ("subheading", "C.8 — Performance Security"),
            ("para", "Sub-Clause 4.2 is supplemented as follows. The Contractor shall, "
                     "within twenty-one days of the Commencement Date, provide the Employer "
                     "with an unconditional and irrevocable bank guarantee, in a form "
                     "approved by the Employer, in the amount stated in the Contract Data, "
                     "being ten per cent of the Contract Amount. The Performance Security "
                     "shall remain valid until the issue of the Performance Certificate, and "
                     "the Contractor shall extend its validity as necessary to maintain "
                     "continuous cover until that date. The Employer shall return the "
                     "Performance Security to the Contractor within twenty-one days of the "
                     "issue of the Performance Certificate."),

            ("heading", "PART D — AMENDMENTS RELATING TO CLAUSE 8 (COMMENCEMENT, DELAYS AND "
                        "SUSPENSION)"),
            ("subheading", "D.1 — Monsoon Period Restriction"),
            ("para", "Sub-Clause 8.4 is supplemented as follows. The Parties acknowledge "
                     "that the river is subject to a seasonal rise in water level and flow "
                     "between 1 June and 30 September in each year of the Contract period "
                     "(the \"Monsoon Period\"). Save with the prior written consent of the "
                     "Engineer, the Contractor shall not carry out piling, pile-cap "
                     "construction, cofferdam work, or any other work below the normal water "
                     "level of the river during the Monsoon Period. This restriction is a "
                     "known and foreseeable condition of the Site as at the date of the "
                     "Letter of Acceptance, has been allowed for by the Contractor in its "
                     "programme and pricing, and does not of itself constitute a cause of "
                     "delay entitling the Contractor to an extension of time under Sub-Clause "
                     "8.4."),
            ("subheading", "D.2 — Adverse Weather Event"),
            ("para", "Sub-Clause 8.4 is further supplemented as follows. Notwithstanding "
                     "Part D.1 above, if rainfall recorded at the Site rain gauge, or in the "
                     "absence of a reliable Site reading, at the nearest gauge operated by "
                     "the Suvarna District Water Resources Department, exceeds 100 "
                     "millimetres in any continuous twenty-four hour period, and the "
                     "Contractor demonstrates that the Works were thereby delayed to an "
                     "extent, or in a manner, beyond what could reasonably have been "
                     "anticipated having regard to the Monsoon Period restriction in Part D.1 "
                     "(an \"Adverse Weather Event\"), the resulting delay shall be a cause of "
                     "delay for the purposes of Sub-Clause 8.4(b), subject to the Contractor "
                     "giving notice and particulars in accordance with Sub-Clause 20.1."),
            ("subheading", "D.3 — Delay Damages"),
            ("para", "Sub-Clause 8.7 is supplemented as follows. The rate of delay damages "
                     "referred to in Sub-Clause 8.7 is 0.05 per cent of the Contract Amount "
                     "for each day of delay, and the maximum amount of delay damages payable "
                     "under Sub-Clause 8.7 is 10 per cent of the Contract Amount, as stated "
                     "in the Contract Data."),

            ("heading", "PART E — AMENDMENTS RELATING TO CLAUSE 13 (VARIATIONS AND "
                        "ADJUSTMENTS)"),
            ("subheading", "E.1 — Approval Threshold for Variations"),
            ("para", "Sub-Clause 13.1 is supplemented as follows. Where the Engineer's "
                     "estimate of the value of a proposed Variation exceeds five hundred "
                     "thousand Vantaran Dollars (VTD 500,000), the Engineer shall not issue "
                     "an instruction to carry out that Variation without the prior written "
                     "consent of the Employer. The Engineer shall seek such consent promptly "
                     "upon forming the estimate referred to above, and shall keep the "
                     "Contractor informed, upon request, of the status of that approval, but "
                     "the time taken to obtain the Employer's consent under this Part E.1 "
                     "shall not, of itself, relieve the Contractor of any obligation to give "
                     "notice under Sub-Clause 20.1 in respect of the delay or cost "
                     "consequences of the Variation once instructed."),
            ("subheading", "E.2 — Engineer's Response Period"),
            ("para", "Sub-Clause 13.3 is supplemented as follows. The Engineer shall respond "
                     "to a proposal submitted by the Contractor under Sub-Clause 13.3 within "
                     "fourteen days of receipt, either instructing the Variation, confirming "
                     "that it is not to proceed, or requesting a revised proposal, failing "
                     "which the Contractor may by notice to the Engineer treat the proposal "
                     "as under continued consideration and request a response within a "
                     "further seven days."),

            ("heading", "PART F — AMENDMENTS RELATING TO CLAUSE 14 (CONTRACT PRICE AND "
                        "PAYMENT)"),
            ("subheading", "F.1 — Retention"),
            ("para", "Sub-Clause 14.3 is supplemented as follows. Retention shall be "
                     "deducted at the rate of five per cent from each amount otherwise due, "
                     "until the cumulative amount retained reaches the Limit of Retention "
                     "Money stated in the Contract Data, being five per cent of the Contract "
                     "Amount, after which no further retention shall be deducted."),
            ("subheading", "F.2 — Payment Timing"),
            ("para", "Sub-Clause 14.7 is replaced with the following. The Engineer shall "
                     "issue an Interim Payment Certificate within twenty-one days of "
                     "receiving a Statement submitted in accordance with Sub-Clause 14.3. "
                     "The Employer shall pay the Contractor the amount certified within "
                     "fifty-six days of the date of the Statement to which the certificate "
                     "relates. Financing charges on any amount not paid within this period "
                     "shall accrue at the rate stated in the Contract Data."),

            ("heading", "PART G — AMENDMENTS RELATING TO CLAUSE 20 (CLAIMS)"),
            ("subheading", "G.1 — Confirmation of Notice Period"),
            ("para", "Sub-Clause 20.1 is confirmed as unamended by these Particular "
                     "Conditions. For the avoidance of doubt, the twenty-eight day period for "
                     "giving notice of a claim under Sub-Clause 20.1 applies to every claim "
                     "arising under the Contract, including a claim arising from an Adverse "
                     "Weather Event under Part D.2, a Variation under Clause 13, or any other "
                     "cause, and time runs from the date the Contractor became aware, or "
                     "ought reasonably to have become aware, of the event or circumstance "
                     "giving rise to the claim, and not from any later date."),

            ("total_box", "[END OF PARTICULAR CONDITIONS]"),
        ],
        closing_lines=[],
        scenario=0,
    ),

    # ------------------------------------------------------------------
    # NRB4-CD-2020 -- Contract Data
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="NRB4-CD-2020",
        title="Contract Data",
        doc_type="CONTRACT",
        doc_type_tag="CONTRACT DATA",
        letterhead="JOINT",
        date="05-Dec-2020",
        from_="National Highways Infrastructure Authority (Employer)",
        to="Meridian Engineering Consultants (Engineer); Sagara Constructions Pvt. Ltd. "
           "(Contractor)",
        body=[
            ("para", "This Contract Data forms part of the Contract and provides the "
                     "specific values, periods, rates and particulars referred to in the "
                     "General Conditions and the Particular Conditions. Where an entry below "
                     "states the Sub-Clause or Particular Condition to which it relates, that "
                     "entry supplies the value or period left open by that provision. Terms "
                     "used below carry the meanings given to them elsewhere in the Contract."),

            ("heading", "1. THE PARTIES"),
            ("para", "Employer: National Highways Infrastructure Authority"),
            ("para", "Employer's Address for Notices: NHIA Project Office, Plot 14, Sector "
                     "9, Government Complex, Vantara City, Republic of Vantara"),
            ("para", "Employer's Electronic Address: projects.nrb4@nhia.gov.vt"),
            ("para", "Engineer: Meridian Engineering Consultants"),
            ("para", "Engineer's Address for Notices: Meridian House, 22 Riverside Avenue, "
                     "Vantara City, Republic of Vantara"),
            ("para", "Engineer's Site Office: NRB-4 Site Office, Left Bank Approach, Nandira "
                     "River Crossing, Suvarna District"),
            ("para", "Engineer's Electronic Address: nrb4.engineer@meridianconsult.vt"),
            ("para", "Contractor: Sagara Constructions Pvt. Ltd."),
            ("para", "Contractor's Address for Notices: Sagara House, 8 Industrial Estate "
                     "Road, Vantara City, Republic of Vantara"),
            ("para", "Contractor's Site Office: NRB-4 Contractor's Site Office, Right Bank "
                     "Approach, Nandira River Crossing, Suvarna District"),
            ("para", "Contractor's Electronic Address: nrb4.pm@sagaraconstructions.vt"),

            ("heading", "2. THE PROJECT"),
            ("para", "Project Name: Nandira River Bridge Project — Package NRB-4"),
            ("para", "Contract Number: NHIA/NRB4/CW/2020-01"),
            ("para", "Site Location: National Highway NH-14 Realignment, km 212+400 to km "
                     "213+040, crossing the Nandira River, Suvarna District, Republic of "
                     "Vantara"),

            ("heading", "3. KEY DATES AND PERIODS"),
            ("para", "Letter of Acceptance Date: 10 November 2020"),
            ("para", "Commencement Date: 15 January 2021"),
            ("para", "Time for Completion: 30 months from the Commencement Date, being 15 "
                     "July 2023"),
            ("para", "Taking-Over Period (period for the Engineer to issue the Taking-Over "
                     "Certificate, or a notice of reasons for not doing so, following the "
                     "Contractor's application): 21 days"),
            ("para", "Defects Notification Period (Sub-Clause referenced in the General "
                     "Conditions): 365 days from the date stated in the Taking-Over "
                     "Certificate"),

            ("heading", "4. CONTRACT AMOUNT AND CURRENCY"),
            ("para", "Payment Currency: Vantaran Dollar (VTD)"),
            ("para", "Contract Amount: VTD 42,000,000 (Vantaran Dollars forty-two million)"),

            ("heading", "5. SECURITY"),
            ("para", "Performance Security Percentage: 10 per cent of the Contract Amount"),
            ("para", "Performance Security: VTD 4,200,000, in the form of an unconditional "
                     "and irrevocable bank guarantee, to be provided within 21 days of the "
                     "Commencement Date in accordance with Part C.8 of the Particular "
                     "Conditions"),

            ("heading", "6. RETENTION"),
            ("para", "Retention Percentage (Sub-Clause 14.3): 5 per cent of each amount "
                     "otherwise due"),
            ("para", "Limit of Retention Money: VTD 2,100,000, being 5 per cent of the "
                     "Contract Amount"),

            ("heading", "7. DELAY DAMAGES"),
            ("para", "Delay Damages Rate (Sub-Clause 8.7, as supplemented by Part D.3 of "
                     "the Particular Conditions): 0.05 per cent of the Contract Amount for "
                     "each day of delay, being VTD 21,000 per day"),
            ("para", "Maximum Delay Damages: 10 per cent of the Contract Amount, being VTD "
                     "4,200,000"),

            ("heading", "8. PAYMENT"),
            ("para", "Interim Payment Frequency (Sub-Clause 14.3): Monthly"),
            ("para", "Engineer Certification Period (Sub-Clause 14.7, as replaced by Part "
                     "F.2 of the Particular Conditions): 21 days from receipt of a compliant "
                     "Statement"),
            ("para", "Employer Payment Period (Sub-Clause 14.7, as replaced by Part F.2 of "
                     "the Particular Conditions): 56 days from the date of the Statement to "
                     "which the Interim Payment Certificate relates"),
            ("para", "Interest Rate on Late Payment: 12 per cent per annum, compounded "
                     "monthly, from the date payment fell due until the date of actual "
                     "payment"),

            ("heading", "9. NOTICE PERIOD FOR CLAIMS"),
            ("para", "Period for Notice of Claim (Sub-Clause 20.1, confirmed unamended by "
                     "Part G.1 of the Particular Conditions): 28 days from the date the "
                     "Contractor became aware, or ought reasonably to have become aware, of "
                     "the event or circumstance giving rise to the claim"),

            ("heading", "10. WORKING DAYS AND HOURS"),
            ("para", "Working Days (Part C.1 of the Particular Conditions): Monday to "
                     "Saturday, excluding public holidays observed at the Site"),
            ("para", "Working Hours (Part C.1 of the Particular Conditions): 07:00 to "
                     "19:00"),

            ("heading", "11. ENGINEER'S RESIDENT REPRESENTATIVE"),
            ("para", "Resident Engineer: Er. Anand Vasker"),
            ("para", "Address: NRB-4 Site Office, Left Bank Approach, Nandira River "
                     "Crossing, Suvarna District"),
            ("para", "Scope of Delegation: as recorded in the Engineer's notice to the "
                     "Contractor issued pursuant to Part B.1 of the Particular Conditions"),

            ("total_box", "[END OF CONTRACT DATA]"),
        ],
        closing_lines=[],
        scenario=0,
    ),

    # ------------------------------------------------------------------
    # NRB4-ER-2020 -- Employer's Requirements (Extract)
    # ------------------------------------------------------------------
    DocumentSpec(
        doc_id="NRB4-ER-2020",
        title="Employer's Requirements (Extract)",
        doc_type="CONTRACT",
        doc_type_tag="EMPLOYER'S REQUIREMENTS (EXTRACT)",
        letterhead="JOINT",
        date="05-Dec-2020",
        from_="National Highways Infrastructure Authority (Employer)",
        to="Meridian Engineering Consultants (Engineer); Sagara Constructions Pvt. Ltd. "
           "(Contractor)",
        body=[
            ("para", "This document sets out the Employer's technical requirements for the "
                     "design (to the extent stated), construction, testing and handover of "
                     "the Works. It is a technical requirements document and does not form "
                     "the Conditions of Contract; where a technical matter set out below has "
                     "contractual consequence, that consequence is dealt with in the General "
                     "Conditions or the Particular Conditions, and this document is to be "
                     "read together with those documents and with the Drawings and "
                     "Specification. This is an extract; matters not addressed below are not "
                     "to be taken as excluded from the Contractor's obligations under the "
                     "Contract."),

            ("heading", "1. PROJECT OVERVIEW"),
            ("para", "The Works comprise the design (to the extent stated in this document), "
                     "construction and commissioning of a new river bridge and associated "
                     "approach works carrying the National Highway NH-14 realignment across "
                     "the Nandira River, together with all ancillary civil, structural and "
                     "drainage works necessary for the bridge and approaches to be brought "
                     "into safe public use. The Works are located between approximate "
                     "chainage km 212+400 and km 213+040, Suvarna District, Republic of "
                     "Vantara."),
            ("para", "The Contractor is responsible for constructing the Works in accordance "
                     "with the reference design issued by the Engineer, this document, the "
                     "Specification and the Drawings, and for such elements of design as are "
                     "expressly identified in this document as the Contractor's "
                     "responsibility."),

            ("heading", "2. SCOPE OF WORKS"),
            ("para", "The Scope of Works includes, without limitation: site clearance and "
                     "preparatory works; temporary diversion of traffic and construction of "
                     "any temporary access required for construction; foundation and "
                     "substructure works for the bridge, including piling, pile caps, piers "
                     "and abutments; superstructure works, including precast or cast-in-situ "
                     "girders, deck slab, parapets, expansion joints, bearings and drainage; "
                     "approach road formation, pavement and associated drainage on both banks "
                     "within the defined limits of the Site; permanent traffic signage and "
                     "road marking within the limits of the Works; testing, commissioning and "
                     "load testing of the completed structure; and remedying of defects "
                     "during the Defects Notification Period."),
            ("para", "The Scope of Works excludes permanent electrical street lighting "
                     "installations, which are the subject of a separate package, save that "
                     "the Contractor shall provide such conduit and duct crossings within the "
                     "Works as are shown on the Drawings to accommodate that separate "
                     "package."),

            ("heading", "3. BRIDGE CONFIGURATION"),
            ("para", "The bridge shall comprise 8 spans with an overall length of "
                     "approximately 640 metres, supported on 2 abutments (Abutment A1 on the "
                     "left bank and Abutment A2 on the right bank) and 7 piers (Piers P1 to "
                     "P7, numbered sequentially from Abutment A1), with an average span "
                     "length of approximately 80 metres. Piers P3 to P7 are located within or "
                     "adjacent to the active river channel; Piers P1 and P2 are located on "
                     "the left bank approach outside the normal river channel."),
            ("para", "The bridge shall carry a dual two-lane carriageway with hard "
                     "shoulders, with an overall deck width of not less than 14 metres, "
                     "together with parapets and a maintenance walkway on one side as shown "
                     "on the Drawings. The soffit of the superstructure shall provide a "
                     "clearance of not less than 6 metres above the Highest Flood Level "
                     "notified by the Suvarna District Water Resources Department, measured "
                     "at the deepest point of the river channel beneath each span."),

            ("heading", "4. STRUCTURAL PERFORMANCE REQUIREMENTS"),
            ("para", "The Works shall be designed and constructed for a design life of 100 "
                     "years. Structural design, to the extent it is the Contractor's "
                     "responsibility under this document, shall be carried out in accordance "
                     "with the Vantara National Bridge Design Code and such other codes and "
                     "standards as are identified in the Specification. The bridge shall be "
                     "designed for the seismic zone and live load class stated in the "
                     "Specification, and for hydraulic loading corresponding to the design "
                     "flood discharge stated in the Specification."),
            ("para", "Save as expressly stated in this document, the design of the Permanent "
                     "Works, including the design of the substructure and superstructure, is "
                     "provided by the Employer through the Engineer, and the Contractor "
                     "shall construct the Permanent Works strictly in accordance with the "
                     "Drawings issued for construction, save to the extent an instruction "
                     "under Clause 3 or Clause 13 of the General Conditions directs "
                     "otherwise."),

            ("heading", "5. MATERIALS"),
            ("para", "Concrete used in substructure elements, including pile caps, piers and "
                     "abutments, shall achieve a minimum characteristic compressive strength "
                     "of Grade M40. Concrete used in superstructure elements, including "
                     "girders and deck slab, shall achieve a minimum characteristic "
                     "compressive strength of Grade M45. Reinforcement shall be high yield "
                     "strength deformed bars of the grade stated in the Specification, and "
                     "shall be accompanied by mill test certificates traceable to the batch "
                     "of steel used in each pour. Cement, aggregates, admixtures and any "
                     "precast elements shall conform to the standards and source approvals "
                     "stated in the Specification, and the Contractor shall obtain the "
                     "Engineer's approval of each proposed source of materials before that "
                     "source is used on the Works."),

            ("heading", "6. FOUNDATIONS"),
            ("para", "Pier and abutment foundations shall be piled foundations, of the type, "
                     "diameter and founding criteria shown on the Drawings, founded on strata "
                     "meeting the bearing and settlement criteria stated in the Specification. "
                     "Pile installation shall be carried out in accordance with an approved "
                     "method statement under Section 16 of this document, and each pile shall "
                     "be subject to the integrity and load testing regime stated in the "
                     "Specification. Where ground conditions encountered during piling differ "
                     "from those indicated in the geotechnical information provided with the "
                     "tender documents, the Contractor shall notify the Engineer promptly and "
                     "shall not proceed with the affected foundation until the Engineer has "
                     "reviewed the matter."),

            ("heading", "7. TEMPORARY WORKS"),
            ("para", "The Contractor is responsible for the design, adequacy and safety of "
                     "all Temporary Works, including but not limited to cofferdams, "
                     "falsework, formwork, staging, access trestles and any temporary works "
                     "platform required for construction within the river channel. Temporary "
                     "Works design shall be prepared by a suitably qualified person and shall "
                     "be submitted to the Engineer for review under Section 16 of this "
                     "document before the relevant Temporary Works are constructed. "
                     "Engineer's review of Temporary Works design does not relieve the "
                     "Contractor of responsibility for its adequacy."),

            ("heading", "8. UTILITIES"),
            ("para", "The Drawings show the location of utilities known to the Employer at "
                     "the date of issue, including an overhead transmission line owned by "
                     "Vantara Power Grid Corporation running generally parallel to the "
                     "highway corridor and crossing it at one or more locations shown on the "
                     "Utility Drawings, and an underground water trunk main owned by Suvarna "
                     "Water Board crossing the river near the left bank approach. The "
                     "Contractor shall verify the location of any utility shown on the "
                     "Drawings by trial pit or other non-destructive method before carrying "
                     "out excavation within 5 metres of its indicated position, and shall "
                     "coordinate the timing of its operations with the relevant utility owner "
                     "in accordance with Part C.4 of the Particular Conditions."),
            ("para", "The utility information provided with the tender documents is based on "
                     "records supplied by the relevant utility owners and may not be complete "
                     "or fully accurate. The Contractor shall exercise reasonable skill and "
                     "care in locating utilities and shall report to the Engineer without "
                     "delay any utility, apparatus or installation encountered that is not "
                     "shown on the Drawings or otherwise disclosed in writing before the "
                     "Commencement Date."),

            ("heading", "9. ENVIRONMENTAL PROTECTION"),
            ("para", "The Contractor shall carry out the Works in compliance with the "
                     "environmental clearance issued by the Vantara Environmental Protection "
                     "Board and the requirements of Part C.3 of the Particular Conditions. "
                     "Without limiting those requirements, the Contractor shall prepare and "
                     "submit to the Engineer, before commencing any in-river work, a River "
                     "Works Environmental Management Plan addressing turbidity control, spill "
                     "prevention and response, disposal of spoil and construction waste, and "
                     "protection of riverbank vegetation outside the limits of the Works. "
                     "In-river work shall not commence until the Engineer has confirmed no "
                     "objection to the Management Plan."),

            ("heading", "10. QUALITY ASSURANCE"),
            ("para", "The Contractor shall implement and maintain a quality management system "
                     "appropriate to the nature and scale of the Works, and shall submit an "
                     "Inspection and Test Plan for each principal element of the Works "
                     "(piling, substructure concrete, superstructure concrete, and pavement) "
                     "for the Engineer's review before that element of work commences. Each "
                     "Inspection and Test Plan shall identify the Hold Points applicable to "
                     "that element in accordance with Section 11 of this document, the "
                     "inspections and tests to be carried out, and the records to be "
                     "generated."),

            ("heading", "11. INSPECTION AND HOLD POINTS"),
            ("para", "The following stages of the Works are designated Hold Points, at which "
                     "the Contractor shall not proceed without the prior written consent of "
                     "the Engineer or the Resident Engineer, requested in accordance with "
                     "Part C.6 of the Particular Conditions:"),
            ("bullet", "(a) founding level and pile-cap excavation, before placing blinding "
                       "concrete;"),
            ("bullet", "(b) reinforcement fixing for any substructure or superstructure "
                       "element, before placement of formwork over that reinforcement;"),
            ("bullet", "(c) formwork and falsework for any element, before placing "
                       "concrete;"),
            ("bullet", "(d) each concrete pour, which shall be witnessed by the Engineer's "
                       "Representative or the Resident Engineer or their nominee;"),
            ("bullet", "(e) backfilling around any foundation or substructure element, "
                       "before backfill is placed;"),
            ("bullet", "(f) erection or launching of any girder or precast element; and"),
            ("bullet", "(g) load testing of the completed structure, before issue of the "
                       "Taking-Over Certificate."),
            ("para", "The Contractor shall maintain the Hold Point register required by Part "
                     "C.6 of the Particular Conditions and shall not treat a Hold Point as "
                     "cleared until the Engineer's or Resident Engineer's written consent has "
                     "been recorded in that register."),

            ("heading", "12. TESTING REQUIREMENTS"),
            ("para", "Concrete testing shall be carried out at a minimum frequency of one set "
                     "of three cubes for every pour, or for every 30 cubic metres placed in a "
                     "continuous pour exceeding that volume, tested at 7 and 28 days by the "
                     "independent testing laboratory nominated by the Engineer. Reinforcement "
                     "shall be tested by mill certificate verification and, where required by "
                     "the Specification, by independent sample testing. Compacted fill and "
                     "backfill shall be tested for density and moisture content at the "
                     "frequency stated in the Specification. Pile integrity and load testing "
                     "shall be carried out in accordance with Section 6 of this document and "
                     "the Specification. The completed bridge shall be subject to a static "
                     "and, where required by the Specification, dynamic load test before the "
                     "Taking-Over Certificate is issued, the results of which shall be "
                     "reviewed and accepted by the Engineer."),

            ("heading", "13. SURVEY REQUIREMENTS"),
            ("para", "The Contractor shall establish and maintain survey control points "
                     "referenced to the benchmarks and coordinate system stated in the "
                     "Specification, and shall engage a qualified surveyor to verify the "
                     "setting-out of foundations, piers and abutments before construction of "
                     "each element and to record as-built levels and positions on "
                     "completion. Setting-out and as-built survey shall be within the "
                     "tolerances stated in the Specification, and survey records shall be "
                     "submitted to the Engineer for each principal element before the "
                     "corresponding Hold Point under Section 11 is cleared."),

            ("heading", "14. CONSTRUCTION RECORDS"),
            ("para", "In addition to the general record-keeping obligations in Part C.7 of "
                     "the Particular Conditions, the Contractor shall maintain, for each "
                     "concrete pour, a pour record identifying the date, location, quantity, "
                     "source and batching details of the concrete placed, the ambient "
                     "conditions, and the personnel and Engineer's representative present; "
                     "and for each pile, a pile record identifying installation date, depth, "
                     "founding stratum, and the results of any integrity or load test carried "
                     "out on that pile. These records shall be submitted to the Engineer "
                     "within five working days of the event to which they relate."),

            ("heading", "15. SHOP DRAWINGS"),
            ("para", "The Contractor shall prepare and submit shop drawings, including "
                     "reinforcement bar bending schedules, formwork and falsework drawings, "
                     "and precast element drawings, for the Engineer's review not less than "
                     "fourteen days before the drawing is required for construction. The "
                     "Engineer shall return each shop drawing marked as approved, approved "
                     "with comments, or rejected, within seven days of receipt. Construction "
                     "shall not proceed on the basis of a shop drawing that has not been "
                     "returned marked approved or approved with comments, and where returned "
                     "with comments, the Contractor shall resubmit incorporating those "
                     "comments before proceeding."),

            ("heading", "16. METHOD STATEMENTS"),
            ("para", "The Contractor shall submit a method statement for the Engineer's "
                     "review before commencing each of the following activities: piling; "
                     "cofferdam construction and dewatering; Temporary Works erection under "
                     "Section 7 of this document; concrete pours below water level or of a "
                     "continuous volume exceeding 100 cubic metres; and erection or launching "
                     "of girders or precast elements. Each method statement shall identify "
                     "the sequence of work, plant and equipment to be used, temporary works "
                     "involved, and the safety measures to be adopted. The Engineer's "
                     "confirmation of no objection to a method statement does not relieve the "
                     "Contractor of responsibility for the adequacy of the method or the "
                     "safety of its execution, and the relevant activity shall not commence "
                     "until that confirmation has been given."),

            ("heading", "17. AS-BUILT DOCUMENTATION"),
            ("para", "Before application for the Taking-Over Certificate, the Contractor "
                     "shall submit as-built drawings for all Permanent Works, incorporating "
                     "all changes from the issued-for-construction Drawings; operation and "
                     "maintenance manuals for bearings, expansion joints, drainage systems "
                     "and any mechanical or electrical equipment forming part of the Works; a "
                     "consolidated set of construction records compiled under Section 14 of "
                     "this document; test certificates and survey records compiled under "
                     "Sections 12 and 13 of this document; and warranty or guarantee "
                     "documentation for materials and proprietary items incorporated in the "
                     "Works. The Engineer shall confirm receipt of complete as-built "
                     "documentation as a condition of issuing the Taking-Over Certificate."),

            ("total_box", "[END OF EMPLOYER'S REQUIREMENTS EXTRACT]"),
        ],
        closing_lines=[],
        scenario=0,
    ),
]
