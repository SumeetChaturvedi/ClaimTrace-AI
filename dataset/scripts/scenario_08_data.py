"""Verbatim structured data for Scenario 8's 8 approved documents."""

from pdf_template import DocumentSpec

SCENARIO = 8

DOCUMENTS: list[DocumentSpec] = [

    # Document 1 -- WPR-NRB4-018
    DocumentSpec(
        doc_id="WPR-NRB4-018",
        title="Weekly Progress Report No. 18 — Week Ending 31-May-2022",
        doc_type="PROGRESS_REPORT",
        doc_type_tag="WEEKLY PROGRESS REPORT",
        letterhead="CONTRACTOR",
        date="03-Jun-2022",
        from_="Contractor, Planning Engineer, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        extra_meta=[("Period Ending", "31-May-2022")],
        subject="Weekly Progress Report No. 18",
        body=[
            ("para", "1. OVERALL PROGRESS: Cumulative physical progress against the revised "
                     "programme (incorporating EOT-01, revised Time for Completion "
                     "23-Sep-2023) is as follows:"),
            ("para", "Planned cumulative progress to date: 52%"),
            ("para", "Actual cumulative progress to date: 46%"),
            ("para", "Shortfall: 6 percentage points, estimated at approximately 5 weeks of "
                     "critical path slippage if not addressed."),
            ("para", "2. STRUCTURAL WORKS: Substructure and superstructure works remain "
                     "substantially complete across all piers, consistent with progress "
                     "reported at Meeting No. 26 (MOM-NRB4-026, 20-Mar-2022). Deck slab pours "
                     "at Piers P5–P7 completed 22-Apr-2022. No structural activity currently "
                     "on the critical path."),
            ("para", "3. APPROACH ROAD PAVEMENT: This is the principal source of the "
                     "shortfall. Sub-base and base layer works on both left and right bank "
                     "approaches are behind the revised programme, attributable to: (a) "
                     "productivity below planned rates in compaction of localised soft spots "
                     "requiring additional treatment before base layer placement; and (b) "
                     "restricted plant access to the pavement works in the vicinity of Pier P5 "
                     "during the period NCR-NRB4-001 was open (18-Mar-2022 to 06-May-2022), "
                     "during which haul routes through that area were limited."),
            ("para", "4. CRITICAL PATH: The critical path currently runs through completion "
                     "of approach road pavement (both banks) to parapet and expansion joint "
                     "installation, to testing and commissioning, to the Taking-Over "
                     "Certificate application. Total float on the drainage and signage "
                     "activities remains positive but is being eroded by the pavement "
                     "shortfall."),
            ("para", "5. OTHER ACTIVITY: Bearing installation inspection completed at "
                     "Abutment A1, satisfactory. Routine safety induction conducted for 6 new "
                     "starters joining the pavement works team."),
            ("para", "We are preparing a Recovery Programme for submission to the Engineer."),
        ],
        closing_lines=["Reported by: Planning Engineer, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 2 -- PGM-NRB4-Rev07
    DocumentSpec(
        doc_id="PGM-NRB4-Rev07",
        title="Updated Programme, Revision 07 — Current Status",
        doc_type="PROGRAMME",
        doc_type_tag="UPDATED PROGRAMME",
        letterhead="CONTRACTOR",
        date="03-Jun-2022",
        from_="Contractor, Planning Engineer, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        extra_meta=[("Data Date", "31-May-2022")],
        subject="Updated Programme Revision 07, reflecting Weekly Progress Report WPR-NRB4-018",
        body=[
            ("subheading", "KEY MILESTONES:"),
            ("para", "Commencement Date: 15-Jan-2021 (actual)"),
            ("para", "Substructure complete, all piers: 20-Feb-2022 (actual)"),
            ("para", "Superstructure erection and deck slab complete, all spans: 22-Apr-2022 "
                     "(actual)"),
            ("para", "Approach road pavement complete, both banks: currently forecast "
                     "14-Nov-2022 (was 10-Oct-2022 per Revision 06)"),
            ("para", "Testing and commissioning complete: currently forecast 20-Jul-2023"),
            ("para", "Revised Time for Completion (per EOT-01): 23-Sep-2023"),
            ("subheading", "CRITICAL PATH ACTIVITIES (current):"),
            ("table", {
                "headers": ["Activity", "Description", "% Complete"],
                "rows": [
                    ["ACT-4210", "Approach road sub-base, left bank", "60%"],
                    ["ACT-4220", "Approach road base layer, left bank", "25%"],
                    ["ACT-4310", "Approach road sub-base, right bank", "55%"],
                    ["ACT-4320", "Approach road base layer, right bank", "20%"],
                    ["ACT-5100", "Parapet and expansion joint installation", "not started"],
                    ["ACT-6100", "Testing and commissioning", "not started"],
                ],
            }),
            ("para", "Logic links: ACT-4210 is predecessor to ACT-4220 (base layer, left "
                     "bank). ACT-4310 is predecessor to ACT-4320 (base layer, right bank). "
                     "ACT-5100 is successor to ACT-4220 and ACT-4320. ACT-6100 is successor "
                     "to ACT-5100."),
            ("para", "TOTAL FLOAT: Drainage (ACT-4400) and signage/marking (ACT-4500) "
                     "activities currently retain 3 weeks total float each, down from 8 weeks "
                     "at Revision 06, reflecting erosion of float by the pavement shortfall "
                     "identified in WPR-NRB4-018."),
            ("para", "This programme will be superseded by the Recovery Programme currently "
                     "in preparation."),
        ],
        closing_lines=["Prepared by: Planning Engineer, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 3 -- PROD-NRB4-002
    DocumentSpec(
        doc_id="PROD-NRB4-002",
        title="Productivity Summary — Approach Road Pavement Works",
        doc_type="TECHNICAL_REPORT",
        doc_type_tag="PRODUCTIVITY SUMMARY",
        letterhead="CONTRACTOR",
        date="08-Jun-2022",
        from_="Contractor, Planning Engineer, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Productivity Summary — Approach Road Pavement Works, February to May 2022",
        body=[
            ("table", {
                "headers": ["Activity", "Planned Rate", "Achieved Rate", "Variance"],
                "rows": [
                    ["Sub-base, left bank", "45 m/day", "33 m/day", "-27%"],
                    ["Sub-base, right bank", "45 m/day", "31 m/day", "-31%"],
                    ["Base layer, both", "30 m/day", "22 m/day", "-27%"],
                ],
                "right_align_cols": [1, 2, 3],
            }),
            ("para", "ANALYSIS: The achieved rates across both banks are consistently 27–31% "
                     "below planned rates, indicating a systemic productivity issue rather "
                     "than an isolated cause. Site records indicate: (a) localised soft spots "
                     "requiring sub-grade improvement before sub-base placement occurred at a "
                     "higher frequency than allowed for in the original productivity "
                     "assumptions, adding an average of 0.4 days per 100m of formation "
                     "treated; and (b) a single paving crew has been working both banks "
                     "sequentially rather than in parallel, extending the overall duration "
                     "even where daily rates on an individual bank are close to planned."),
            ("para", "CONCLUSION: The single-crew, sequential-working approach is the larger "
                     "contributor to the overall programme shortfall. Deploying a second, "
                     "independent crew to work the right bank in parallel with the existing "
                     "crew on the left bank is expected to have a materially greater effect "
                     "on recovery than further increasing the rate of a single crew."),
        ],
        closing_lines=["Prepared by: Planning Engineer, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 4 -- RPN-NRB4-001
    DocumentSpec(
        doc_id="RPN-NRB4-001",
        title="Recovery Programme Narrative",
        doc_type="PROGRAMME",
        doc_type_tag="RECOVERY PROGRAMME",
        letterhead="CONTRACTOR",
        date="15-Jun-2022",
        from_="Contractor, Project Manager, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Recovery Programme — Approach Road Pavement Works",
        body=[
            ("para", "Further to Weekly Progress Report WPR-NRB4-018, Updated Programme "
                     "PGM-NRB4-Rev07, and Productivity Summary PROD-NRB4-002, we submit the "
                     "following Recovery Programme."),
            ("para", "1. OBJECTIVE: Recover the current 6 percentage point / approximately "
                     "5-week shortfall against the revised programme, and protect the revised "
                     "Time for Completion of 23-Sep-2023 (per EOT-01, ENG-NRB4-0019)."),
            ("subheading", "2. RECOVERY MEASURES:"),
            ("bullet", "(a) Deployment of a second, independent paving crew (\"Paving Train "
                       "2\") to work the right bank approach road in parallel with the "
                       "existing crew (\"Paving Train 1\") on the left bank, rather than "
                       "sequentially, as recommended in PROD-NRB4-002."),
            ("bullet", "(b) Additional geotechnical inspection resource to reduce the cycle "
                       "time between compaction and the Engineer's sign-off, minimising "
                       "standing time between sub-base and base layer activities."),
            ("bullet", "(c) A dedicated drainage and kerb subcontractor gang, engaged to work "
                       "ahead of the pavement crews and remove drainage installation from the "
                       "pavement critical path."),
            ("bullet", "(d) Intensified use of Saturday working, already permitted under "
                       "Particular Conditions Part C.1, across all three additional resources "
                       "above."),
            ("bullet", "(e) Early procurement of parapet and expansion joint materials, to "
                       "ensure ACT-5100 is not delayed by material availability once pavement "
                       "works are complete."),
            ("para", "3. RECOVERY TARGET: We target recovery of the full 5-week shortfall by "
                     "end September 2022, restoring alignment with Updated Programme "
                     "PGM-NRB4-Rev07's underlying logic and the revised Time for Completion. "
                     "We will report progress against this target in our Weekly Progress "
                     "Reports."),
            ("para", "4. RISK: We note that Paving Train 2 is a newly mobilised crew and may "
                     "require a short period to reach full productivity; we do not consider "
                     "this materially affects the overall recovery strategy given the "
                     "combined effect of measures (a) to (e)."),
            ("para", "Supporting Resource Loading Plan RLP-NRB4-001 is submitted separately."),
        ],
        closing_lines=["Submitted by: Project Manager, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 5 -- RLP-NRB4-001
    DocumentSpec(
        doc_id="RLP-NRB4-001",
        title="Resource Loading Plan — Recovery Programme",
        doc_type="PROGRAMME",
        doc_type_tag="RESOURCE LOADING PLAN",
        letterhead="CONTRACTOR",
        date="15-Jun-2022",
        from_="Contractor, Planning Engineer, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        subject="Resource Loading Plan — Recovery Programme RPN-NRB4-001",
        body=[
            ("table", {
                "headers": ["Resource", "Current", "Additional", "Mobilisation Date"],
                "rows": [
                    ["Paving Train 2 (crew of 14 + 1 paver, 2 rollers)", "0", "1",
                     "27-Jun-2022"],
                    ["Geotechnical inspector", "1", "1", "20-Jun-2022"],
                    ["Drainage/kerb subcontractor gang (Suvarna Civil Works Pvt. Ltd.)",
                     "0", "1 (12)", "04-Jul-2022"],
                    ["Site supervisors, pavement works", "2", "1", "27-Jun-2022"],
                ],
                "right_align_cols": [1, 2],
            }),
            ("para", "Saturday working will apply to all resources above from mobilisation, "
                     "within the hours permitted under Particular Conditions Part C.1 "
                     "(07:00–19:00, Monday to Saturday)."),
            ("para", "Paving Train 2 will be sourced through the Contractor's existing "
                     "subcontract with its established asphalt supplier and is expected to "
                     "reach full planned productivity within 3 weeks of mobilisation, based "
                     "on the Contractor's experience with comparable crew mobilisations on "
                     "other projects."),
        ],
        closing_lines=["Prepared by: Planning Engineer, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 6 -- COORD-NRB4-001
    DocumentSpec(
        doc_id="COORD-NRB4-001",
        title="Minutes of Coordination Meeting — Recovery Programme",
        doc_type="MEETING_MINUTES",
        doc_type_tag="COORDINATION MEETING MINUTES",
        letterhead="ENGINEER",
        date="22-Jun-2022",
        from_="Resident Engineer, Meridian Engineering Consultants",
        to="Distribution list — Employer, Engineer, Contractor",
        extra_meta=[
            ("Meeting", "Recovery Programme Coordination Meeting"),
            ("Venue", "NRB-4 Site Office, Left Bank Approach"),
            ("Present", "Er. Anand Vasker (Resident Engineer, Meridian Engineering "
                        "Consultants); Project Manager and Planning Engineer (Sagara "
                        "Constructions Pvt. Ltd.); Project Representative (National Highways "
                        "Infrastructure Authority)"),
        ],
        body=[
            ("heading", "1. RECOVERY PROGRAMME:"),
            ("para", "The Contractor presented Recovery Programme Narrative RPN-NRB4-001 and "
                     "Resource Loading Plan RLP-NRB4-001. The Engineer noted the diagnosis in "
                     "Productivity Summary PROD-NRB4-002 (sequential single-crew working as "
                     "the principal cause) was consistent with its own observations, and that "
                     "parallel working via a second paving crew was a reasonable primary "
                     "measure. The Engineer requested weekly reporting of Paving Train 2's "
                     "productivity against the assumed 3-week ramp-up period in RLP-NRB4-001, "
                     "to allow early identification if the measure is not performing as "
                     "assumed. The Employer's representative noted no objection to the "
                     "proposed subcontract engagement of Suvarna Civil Works Pvt. Ltd. for "
                     "drainage and kerb works."),
            ("heading", "2. PROCUREMENT:"),
            ("para", "Contractor confirmed purchase orders raised for parapet and expansion "
                     "joint materials per RPN-NRB4-001 item (e), delivery expected September "
                     "2022."),
            ("heading", "3. LOGISTICS:"),
            ("para", "Site compound layout to be adjusted from 27-Jun-2022 to accommodate "
                     "Paving Train 2's plant and materials storage on the right bank; no "
                     "impact on existing structural works areas."),
            ("heading", "4. WORKFORCE:"),
            ("para", "Additional site supervisor for pavement works confirmed starting "
                     "27-Jun-2022, per RLP-NRB4-001."),
            ("heading", "5. AGREED ACTION:"),
            ("para", "The Engineer will issue its formal review of the Recovery Programme "
                     "following review of at least 4 weeks of progress data under the "
                     "recovery measures."),
        ],
        closing_lines=["Minutes recorded by: Resident Engineer, Meridian Engineering "
                       "Consultants"],
        scenario=SCENARIO,
    ),

    # Document 7 -- WPR-NRB4-023
    DocumentSpec(
        doc_id="WPR-NRB4-023",
        title="Weekly Progress Report No. 23 — Week Ending 24-Jul-2022",
        doc_type="PROGRESS_REPORT",
        doc_type_tag="WEEKLY PROGRESS REPORT",
        letterhead="CONTRACTOR",
        date="29-Jul-2022",
        from_="Contractor, Planning Engineer, Sagara Constructions Pvt. Ltd.",
        to="Engineer, Meridian Engineering Consultants",
        extra_meta=[("Period Ending", "24-Jul-2022")],
        subject="Weekly Progress Report No. 23 — Recovery Programme Status",
        body=[
            ("para", "1. OVERALL PROGRESS: Cumulative shortfall against the revised programme "
                     "has reduced from 6 percentage points (31-May-2022, WPR-NRB4-018) to 3 "
                     "percentage points as of 24-Jul-2022, approximately half the original "
                     "shortfall recovered to date."),
            ("para", "2. PAVING TRAIN 1 (LEFT BANK, EXISTING CREW): Achieving 104% of planned "
                     "productivity since resequencing to work solely the left bank; ahead of "
                     "the recovery target for this front."),
            ("para", "3. PAVING TRAIN 2 (RIGHT BANK, NEW CREW): Mobilised 27-Jun-2022 as "
                     "planned. Achieved only 58% of planned productivity in its first three "
                     "weeks, below the ramp-up assumption in Resource Loading Plan "
                     "RLP-NRB4-001, attributable to crew familiarisation with site-specific "
                     "working conditions and a temporary shortage of an experienced paver "
                     "operator, resolved by reassignment of an operator from Paving Train 1 "
                     "for one week of on-the-job mentoring. Productivity in week commencing "
                     "18-Jul-2022 improved to 93% of planned rate and is trending toward full "
                     "planned productivity."),
            ("para", "4. DRAINAGE/KERB SUBCONTRACTOR (SUVARNA CIVIL WORKS): Mobilised "
                     "04-Jul-2022, achieving planned productivity from the second week of "
                     "engagement; drainage works are no longer on the critical path."),
            ("para", "5. GEOTECHNICAL SIGN-OFF CYCLE TIME: Reduced from an average of 1.8 "
                     "days to 0.9 days between compaction and Engineer's approval, consistent "
                     "with the additional inspector mobilised under RLP-NRB4-001."),
            ("para", "6. FORECAST: Based on current trends, full recovery of the shortfall "
                     "remains achievable within the original recovery target of end September "
                     "2022, notwithstanding Paving Train 2's slower-than-assumed start."),
            ("para", "7. OTHER ACTIVITY: Delivery of first batch of parapet materials "
                     "received 18-Jul-2022, ahead of the September forecast in "
                     "COORD-NRB4-001. Routine bearing inspection at Pier P4, satisfactory."),
        ],
        closing_lines=["Reported by: Planning Engineer, Sagara Constructions Pvt. Ltd."],
        scenario=SCENARIO,
    ),

    # Document 8 -- ENG-NRB4-0052
    DocumentSpec(
        doc_id="ENG-NRB4-0052",
        title="Engineer's Programme Review — Recovery Programme RPN-NRB4-001",
        doc_type="APPROVAL",
        doc_type_tag="ENGINEER'S PROGRAMME REVIEW",
        letterhead="ENGINEER",
        date="08-Aug-2022",
        from_="Engineer, Meridian Engineering Consultants",
        to="Contractor, Sagara Constructions Pvt. Ltd.",
        cc="National Highways Infrastructure Authority",
        subject="Programme Review — Recovery Programme RPN-NRB4-001",
        body=[
            ("para", "We have reviewed Recovery Programme Narrative RPN-NRB4-001, Resource "
                     "Loading Plan RLP-NRB4-001, and progress reported in Weekly Progress "
                     "Reports WPR-NRB4-018 and WPR-NRB4-023, together with the discussion at "
                     "Coordination Meeting COORD-NRB4-001."),
            ("para", "1. DIAGNOSIS: We agree with the diagnosis in Productivity Summary "
                     "PROD-NRB4-002 that sequential single-crew working was the principal "
                     "contributor to the shortfall identified in WPR-NRB4-018, and that "
                     "parallel working via a second paving crew was an appropriate primary "
                     "response."),
            ("para", "2. PERFORMANCE OF MEASURES: We note that Paving Train 2 did not achieve "
                     "the productivity ramp-up assumed in RLP-NRB4-001, reaching only 58% of "
                     "planned productivity in its first three weeks against an assumed "
                     "full-productivity period of 3 weeks. We consider this a genuine, if "
                     "modest, underperformance of one measure within the Recovery Programme, "
                     "not a failure of the overall strategy: Paving Train 1, the drainage and "
                     "kerb subcontractor, and the geotechnical sign-off measure have each "
                     "performed at or above the levels assumed, and Paving Train 2 has since "
                     "recovered to 93% of planned productivity and is trending toward full "
                     "performance."),
            ("para", "3. OVERALL ASSESSMENT: The combined effect of the measures in "
                     "RPN-NRB4-001 has reduced the shortfall from 6 percentage points to 3 "
                     "percentage points over approximately eight weeks, consistent with the "
                     "recovery trajectory implied by the end-September 2022 target. We "
                     "consider the Recovery Programme technically credible and, "
                     "notwithstanding the slower start of one measure, reasonably capable of "
                     "achieving full recovery within the stated target period."),
            ("para", "4. DETERMINATION: We accept the Recovery Programme as a reasonable "
                     "basis for protecting the revised Time for Completion of 23-Sep-2023 "
                     "(per EOT-01, ENG-NRB4-0019). We request continued weekly reporting of "
                     "progress against the recovery target, and reserve the right to review "
                     "this determination should the recovery trajectory subsequently "
                     "deteriorate."),
        ],
        closing_lines=["Signed: Engineer's Representative", "Meridian Engineering Consultants"],
        scenario=SCENARIO,
    ),
]
