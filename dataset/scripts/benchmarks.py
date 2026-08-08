"""The 9 approved benchmark questions for Dataset V2 (Scenarios 1-9) — each
is that scenario's own primary investigation question and documented
expected outcome, as already established during document generation."""

BENCHMARKS = [
    {
        "scenario": 1,
        "id": "EOT-01",
        "question": "Was the Contractor entitled to an extension of time for the Pier 3 "
                     "utility conflict, and if so, for how long?",
        "expected_outcome": "Partially Accepted — EOT-01 grants a 10-week extension of "
                             "time under Sub-Clause 8.4(c) for the undisclosed 132kV tower "
                             "foundation encountered at Pier P3.",
        "expected_decisive_docs": [
            "ENG-NRB4-0019", "CTR-NRB4-0021", "CTR-NRB4-0028",
            "VPGC-NRB4-0012", "VPGC-NRB4-0045",
        ],
        "expected_clause_hint": ["8.4", "20.1"],
    },
    {
        "scenario": 2,
        "id": "MONSOON-DISPUTE",
        "question": "Was the Contractor entitled to additional time beyond EOT-01 for "
                     "monsoon conditions during the Pier P3 relocation?",
        "expected_outcome": "Rejected — the original 10-week EOT-01 extension stands; "
                             "monsoon-season productivity loss is a Contractor risk under "
                             "Particular Conditions Part D.1 and does not increase the "
                             "Sub-Clause 8.4(c) entitlement.",
        "expected_decisive_docs": [
            "ENG-NRB4-0024", "ENG-NRB4-0019", "MET-NRB4-2021-03", "PGM-NRB4-Rev04",
        ],
        "expected_clause_hint": ["8.4"],
    },
    {
        "scenario": 3,
        "id": "VO-004-VALUATION",
        "question": "Was the Engineer's valuation of Variation VO-NRB4-004 reasonable and "
                     "contractually justified?",
        "expected_outcome": "The Variation is genuine (Pier P3 pile cap redesign necessitated "
                             "by disturbed backfill); the Engineer's valuation of VTD 590,700 "
                             "(against the Contractor's VTD 687,400 quotation) is "
                             "substantially correct — measured-quantity adjustments accepted, "
                             "disruption lump sum correctly excluded.",
        "expected_decisive_docs": [
            "ENG-NRB4-0031", "CTR-NRB4-0067", "VO-NRB4-004", "NHIA-NRB4-APR-006",
        ],
        "expected_clause_hint": ["13.1", "13.3"],
    },
    {
        "scenario": 4,
        "id": "IPC-11-CERTIFICATION",
        "question": "Was Variation VO-NRB4-004 correctly included in Interim Payment "
                     "Certificate No. 11, and was payment made in accordance with the "
                     "Contract?",
        "expected_outcome": "Correctly included at its approved value (VTD 590,700); "
                             "retention and certification arithmetic correct; payment made "
                             "within the 56-day period, so no interest arises.",
        "expected_decisive_docs": [
            "IPC-NRB4-011", "NHIA-NRB4-APR-006", "NHIA-NRB4-PAY-011", "BTC-NRB4-011",
        ],
        "expected_clause_hint": ["14.3", "14.7"],
    },
    {
        "scenario": 5,
        "id": "RETENTION-INTERPRETATION",
        "question": "Was retention correctly applied to Variation VO-NRB4-004 in IPC-11, "
                     "and is interest payable?",
        "expected_outcome": "Retention was correctly applied to the full cumulative value "
                             "including the Variation, per Sub-Clause 13.3/14.3 and Contract "
                             "Data Section 6 (no exemption for Variations); no interest is "
                             "payable.",
        "expected_decisive_docs": [
            "ENG-NRB4-0038", "CIM-NRB4-002", "CTR-NRB4-0091", "FCS-NRB4-011",
        ],
        "expected_clause_hint": ["13.3", "14.3"],
    },
    {
        "scenario": 6,
        "id": "NOD-VALIDITY",
        "question": "Is the Contractor's Notice of Dissatisfaction procedurally valid, and "
                     "is it likely to succeed on the merits?",
        "expected_outcome": "Procedurally valid and timely (within 28 days); unlikely to "
                             "succeed on the merits — the Engineer's retention interpretation "
                             "in ENG-NRB4-0038 remains correct; dispute remains formally open, "
                             "pending amicable discussion.",
        "expected_decisive_docs": [
            "CTR-NRB4-0098", "LCM-NRB4-001", "DRPN-NRB4-001", "ENG-NRB4-0038",
        ],
        "expected_clause_hint": ["20.1"],
    },
    {
        "scenario": 7,
        "id": "NCR-001-QUALITY",
        "question": "Was the Pier P5 concrete quality non-conformance legitimate, and does "
                     "the structure remain structurally acceptable?",
        "expected_outcome": "NCR-NRB4-001 was legitimately triggered by low Test Set B cube "
                             "results, but core testing and UPV survey confirm the in-place "
                             "concrete is structurally adequate; no demolition required; NCR "
                             "closed.",
        "expected_decisive_docs": [
            "LAB-NRB4-034", "LAB-NRB4-041", "ENG-NRB4-0045", "ENG-NRB4-0049",
        ],
        "expected_clause_hint": [],
    },
    {
        "scenario": 8,
        "id": "RECOVERY-PROGRAMME",
        "question": "Is the Contractor's Recovery Programme credible, and does it support "
                     "the revised completion strategy?",
        "expected_outcome": "Credible and accepted by the Engineer; the shortfall reduced "
                             "from 6 to 3 percentage points over the reporting period; one "
                             "measure (Paving Train 2) underperformed initially but recovered, "
                             "not undermining the overall strategy.",
        "expected_decisive_docs": [
            "ENG-NRB4-0052", "WPR-NRB4-018", "WPR-NRB4-023", "RPN-NRB4-001",
        ],
        "expected_clause_hint": [],
    },
    {
        "scenario": 9,
        "id": "TAKING-OVER",
        "question": "Do the outstanding punch-list items prevent Practical Completion of "
                     "the Works?",
        "expected_outcome": "No — the four outstanding items are all minor (none structural "
                             "or safety-related); the Engineer was contractually justified in "
                             "issuing the Taking-Over Certificate while requiring their "
                             "completion within an agreed period.",
        "expected_decisive_docs": [
            "TOC-NRB4-001", "JIR-NRB4-001", "PL-NRB4-001",
        ],
        "expected_clause_hint": [],
    },
]
