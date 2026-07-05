import pytest


@pytest.fixture
def f3x_filing():
    """Shape matches a real F3X (periodic financial report) filing."""
    return {
        "header": {"record_type": "HDR"},
        "filing": {
            "form_type": "F3XN",
            "filer_committee_id_number": "C00089482",
            "committee_name": "UTAH REPUBLICAN PARTY",
            "coverage_from_date": "2025-05-01",
            "coverage_through_date": "2025-05-31",
            "col_a_total_receipts": 42655.80,
            "col_a_total_disbursements": 21283.49,
            "col_a_cash_on_hand_close_of_period": 66673.60,
        },
        "itemizations": {
            "Schedule A": [
                {
                    "contributor_organization_name": "",
                    "contributor_last_name": "Adams",
                    "contributor_first_name": "Gregory",
                    "contribution_amount": 1650.0,
                    "contributor_city": "Arlington",
                    "contributor_state": "VA",
                    "contribution_date": "2025-05-06",
                },
                {
                    "contributor_organization_name": "Utah State Tax Check Off",
                    "contribution_amount": 11729.0,
                    "contributor_city": "Salt Lake City",
                    "contributor_state": "UT",
                    "contribution_date": "2025-05-14",
                },
            ],
            "Schedule B": [
                {
                    "payee_organization_name": "Trump National Doral Hotel",
                    "expenditure_amount": 1013.61,
                    "expenditure_purpose_descrip": "RNC training",
                    "expenditure_date": "2025-05-19",
                },
                {
                    "payee_organization_name": "Uber.com",
                    "expenditure_amount": 19.77,
                    "expenditure_purpose_descrip": "Travel -Cabfare",
                    "expenditure_date": "2025-05-06",
                },
            ],
        },
    }


@pytest.fixture
def f1_filing():
    """Shape matches a real F1 (Statement of Organization) filing."""
    return {
        "header": {"record_type": "HDR"},
        "filing": {
            "form_type": "F1N",
            "filer_committee_id_number": "C00919000",
            "committee_name": "SOME PAC",
            "committee_type": "Independent Expenditure Committee",
            "committee_url": "https://example.com",
            "treasurer_first_name": "Jane",
            "treasurer_last_name": "Doe",
            "custodian_first_name": "John",
            "custodian_last_name": "Smith",
            "street_1": "123 Main St",
            "city": "Washington",
            "state": "DC",
            "zip_code": "20001",
        },
    }


@pytest.fixture
def f2_filing():
    """Shape matches a real F2 (Statement of Candidacy) filing."""
    return {
        "header": {"record_type": "HDR"},
        "filing": {
            "form_type": "F2A",
            "committee_id_number": "C00919111",
            "candidate_first_name": "Alex",
            "candidate_last_name": "Example",
            "candidate_office": "H",
            "candidate_state": "MD",
            "candidate_district": "05",
            "candidate_party_code": "DEM",
            "election_year": "2026",
        },
    }


@pytest.fixture
def f99_filing():
    """Shape matches a real F99 (Miscellaneous Text) filing."""
    return {
        "header": {"record_type": "HDR"},
        "filing": {
            "form_type": "F99",
            "filer_committee_id_number": "C00919222",
            "committee_name": "SOME COMMITTEE",
            "text": "This is a test F99 filing text content.",
            "text_code": "DEBT",
        },
    }


@pytest.fixture
def f24_filing():
    """Shape matches a real F24 (48-hour independent expenditure notice)."""
    return {
        "header": {"record_type": "HDR"},
        "filing": {
            "form_type": "F24N",
            "filer_committee_id_number": "C00919373",
            "committee_name": "SOME SUPER PAC",
        },
        "itemizations": {
            "Schedule E": [
                {
                    "payee_organization_name": "TKO Buying LLC",
                    "expenditure_amount": 146000.0,
                    "expenditure_purpose_descrip": "Digital Advertising",
                    "disbursement_date": "2026-07-01",
                    "support_oppose_code": "S",
                    "candidate_last_name": "EL-SAYED",
                    "candidate_first_name": "ABDUL",
                }
            ]
        },
    }
