import json
from pathlib import Path

DATASET = Path(__file__).resolve().parents[1] / "examples" / "datasets" / "ostereo_demo_v1.json"

PLACEHOLDERS = {"", "n/a", "na", "null", "none", "-", "unknown"}

OLD_ACCT_FIELDS = [
    "Account_Name__c", "Account_Name_c", "Account_Name", "account_name", "account_name_c",
    "Artist_Name_pka_or_dba__c", "Artist_Name_pka_or_dba_c", "Artist_Name__c", "Artist_Name_c", "artist_name",
    "Legal_Name__c", "Legal_Name_c", "legal_name", "Payee__c", "Payee_c", "Account",
]

NEW_ACCT_FIELDS = [
    "Account_Name__c", "Account_Name_c", "Account_Name", "account_name", "account_name_c", "account_name__c",
    "Company_Name__c", "Company_Name_c", "Company_Name", "company_name", "company_name_c", "company_name__c",
    "Artist_Name_pka_or_dba__c", "Artist_Name_pka_or_dba_c", "Artist_Name__c", "Artist_Name_c", "artist_name",
    "Legal_Name__c", "Legal_Name_c", "legal_name",
    "Payee__c", "Payee_c", "Name", "Account",
]


def _load_dataset():
    return json.loads(DATASET.read_text())


def _is_blank(v):
    if v is None:
        return True
    s = str(v).strip().lower()
    return s in PLACEHOLDERS


def _extract_account(row, fields):
    for key in fields:
        val = row.get(key)
        if val is None:
            continue
        s = str(val).strip()
        if s and s.lower() not in PLACEHOLDERS:
            return s
    return ""


def _find_account_for_file(rows, file_name, fields):
    for row in rows:
        if row.get("File_Name_c") != file_name:
            continue
        acct = _extract_account(row, fields)
        if acct:
            return acct
    return ""


def _old_group_label(rows, file_name):
    acct = _find_account_for_file(rows, file_name, OLD_ACCT_FIELDS)
    if acct:
        return acct
    return file_name


def _new_group_label(rows, file_name):
    acct = _find_account_for_file(rows, file_name, NEW_ACCT_FIELDS)
    if acct:
        return acct
    return file_name


def _old_contract_first_row_index(rows, file_name, field_key):
    first = None
    for idx, row in enumerate(rows):
        if row.get("File_Name_c") != file_name:
            continue
        val = row.get(field_key)
        blank = val is None or str(val).strip() == ""
        if blank:
            return idx
        if first is None:
            first = idx
    return first


def _new_account_first_row_index(rows, account_name, field_key):
    first = None
    for idx, row in enumerate(rows):
        acct = _extract_account(row, NEW_ACCT_FIELDS)
        if acct != account_name:
            continue
        val = row.get(field_key)
        if _is_blank(val):
            return idx
        if first is None:
            first = idx
    return first


def _old_order(items):
    order = []
    seen = set()
    for item in items:
        key = (item["sheet_name"], item["field_key"], item["reason_code"])
        if key not in seen:
            seen.add(key)
            order.append(key)
    return order


def _new_order(items):
    def sort_key(item):
        return (
            (item.get("field_key") or "").lower(),
            (item.get("reason_code") or "").lower(),
            (item.get("severity") or "").lower(),
            int(item.get("row_index") or -1),
            item.get("request_id") or "",
        )

    ordered = sorted(items, key=sort_key)
    order = []
    seen = set()
    for item in ordered:
        key = (item["sheet_name"], item["field_key"], item["reason_code"])
        if key not in seen:
            seen.add(key)
            order.append(key)
    return order


def test_account_first_resolution_prefers_missing_row():
    data = _load_dataset()
    rows = data["sheets"]["Accounts"]["rows"]
    file_name = "The_Theorist_-_Increased_Payout_Threshold_Request.pdf"
    account_name = "THE THEORIST"
    field_key = "Billing_Zip_Postal_Code_c"

    old_idx = _old_contract_first_row_index(rows, file_name, field_key)
    new_idx = _new_account_first_row_index(rows, account_name, field_key)

    assert old_idx is not None
    assert new_idx is not None
    assert rows[old_idx][field_key] == "L9K0C5"
    assert str(rows[new_idx][field_key]).strip().lower() in PLACEHOLDERS
    assert old_idx != new_idx


def test_company_name_used_for_grouping_label():
    data = _load_dataset()
    rows = data["sheets"]["Accounts"]["rows"]
    file_name = "Xmart_x_Ostereo_Distribution_Agreement_(FINAL_SIGNED).pdf"

    old_label = _old_group_label(rows, file_name)
    new_label = _new_group_label(rows, file_name)

    assert old_label != new_label
    assert new_label == "Xmart Digital PVT Ltd"


def test_section_field_order_deterministic():
    file_name = "The_Theorist_-_Increased_Payout_Threshold_Request.pdf"
    items = [
        {
            "sheet_name": "Accounts",
            "field_key": "Billing_Zip_Postal_Code_c",
            "reason_code": "MISSING_REQUIRED",
            "severity": "blocker",
            "row_index": 133,
        },
        {
            "sheet_name": "Accounts",
            "field_key": "Account_Type_c",
            "reason_code": "PICKLIST_INVALID",
            "severity": "warning",
            "row_index": 60,
        },
        {
            "sheet_name": "Accounts",
            "field_key": "Legal_Name_c",
            "reason_code": "MISSING_REQUIRED",
            "severity": "blocker",
            "row_index": 60,
        },
        {
            "sheet_name": "Accounts",
            "field_key": "",
            "reason_code": "OCR_MOJIBAKE",
            "severity": "blocker",
            "row_index": 60,
        },
    ]

    old = _old_order(items)
    new = _new_order(items)

    assert old != new
    assert new == [
        ("Accounts", "", "OCR_MOJIBAKE"),
        ("Accounts", "Account_Type_c", "PICKLIST_INVALID"),
        ("Accounts", "Billing_Zip_Postal_Code_c", "MISSING_REQUIRED"),
        ("Accounts", "Legal_Name_c", "MISSING_REQUIRED"),
    ]
