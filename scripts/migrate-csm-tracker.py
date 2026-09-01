#!/usr/bin/env python3
"""One-time migration: CSM Tracker's raw seed JSON -> Command Center's clean schema.

Usage: python3 migrate-csm-tracker.py --input seed.json --output migration-output.json
Writes migration-review.md alongside --output for anything that needs a human look.
"""
import argparse
import json

# new_field: [old keys, highest priority first]. First non-null value wins.
# This is where CSM Tracker's *Fallback / snake_case / camelCase duplicate
# fields collapse into one clean field.
FIELD_MAP = {
    "arrActive": ["arrLive", "arr", "arrFallback"],
    "arrSumOfAmount": ["arrSumOfAmount"],
    "renewalDate": ["renewalLive", "renewal_date", "renewalFallback"],
    "meetingCadence": ["cadence"],
    "churnScore": ["churnScore"],
    "csmSentiment": ["csmSentiment"],
    "risk": ["risk"],
    "riskRecords": ["riskRecords"],
    "expansionPipeline": ["pipeline"],
    "activeProcessing": ["activeProcessing"],
    "customerServiceStartDate": ["serviceStartDate", "customer_since", "customerSinceFallback"],
    "supportLevel": ["supportLevel", "support", "supportFallback"],
    "fiscalYear": ["fiscalYear", "fiscal_year", "fiscalYearFallback"],
    "processingFrequency": ["processingFreq", "commissions_processing"],
    "previousTool": ["previousTool", "previous_tool", "previousToolFallback"],
    "seatsOccupied": ["seatsOccupied"],
    "payeesPurchased": ["payeesPurchased", "payees_purchased", "payeesFallback"],
    "seatUtilization": ["seatUtilization", "seat_utilization", "seatUtilFallback"],
    "instanceSeatCount": ["instanceSeatCount"],
    "msaPriceIncreaseCap": ["priceIncreaseCap", "price_increase_cap"],
    "capResearchStatus": ["capStatus", "cap_status"],
    "ciqExecutiveSponsor": ["execSponsor", "exec_sponsor", "execSponsorFallback"],
    "lastEbr": ["lastEbr", "last_ebr"],
    "notes": ["notes"],
    "privatePublic": ["companyType", "private_public", "privatePublicFallback"],
    "industry": ["industry", "industryFallback"],
}

# consumed by FIELD_MAP or folded elsewhere; never carried through unchanged
DROP = {
    "arr", "arrFallback", "arrLive", "renewal_date", "renewalFallback", "renewalLive",
    "cadence", "pipeline", "serviceStartDate", "customer_since", "customerSinceFallback",
    "support", "supportFallback", "supportLevel", "fiscal_year", "fiscalYearFallback",
    "fiscalYear", "processingFreq", "commissions_processing", "previous_tool",
    "previousToolFallback", "previousTool", "payees_purchased", "payeesFallback",
    "payeesPurchased", "seat_utilization", "seatUtilFallback", "seatUtilization",
    "price_increase_cap", "priceIncreaseCap", "cap_status", "capStatus", "exec_sponsor",
    "execSponsorFallback", "execSponsor", "last_ebr", "lastEbr", "companyType",
    "private_public", "privatePublicFallback", "industryFallback", "industry",
    "churnScore", "csmSentiment", "risk", "riskRecords", "activeProcessing",
    "seatsOccupied", "instanceSeatCount", "notes",
    # implementation fields folded below, not passed through raw
    "impl_status", "implProjects", "impl_owner", "active_impl", "activeImplFlag", "implActive",
}


def migrate_account(old):
    new = {"accountId": old.get("sfdcId"), "sfdcId": old.get("sfdcId"), "accountName": old.get("name")}
    review = []

    for new_key, candidates in FIELD_MAP.items():
        present = [(c, old[c]) for c in candidates if old.get(c) not in (None, "")]
        new[new_key] = present[0][1] if present else None
        # only worth a human look when candidates actively disagree — missing
        # data entirely (no candidate populated) isn't a migration problem
        distinct = {json.dumps(v, sort_keys=True) for _, v in present}
        if len(distinct) > 1:
            review.append(f"{old.get('name')!r}: {new_key} candidates disagree — {present}, took {present[0][0]!r}")

    # Implementation: one column, several source fields
    new["implementation"] = old.get("impl_status") or (
        "Active" if old.get("activeImplFlag") or old.get("implActive") or old.get("active_impl") else "None"
    )
    new["implementationOwner"] = old.get("impl_owner")
    new["implementationProjects"] = old.get("implProjects", [])

    # everything else not in FIELD_MAP/DROP/implementation passes through unchanged
    for k, v in old.items():
        if k in DROP or k in ("sfdcId", "name"):
            continue
        if k not in new:
            new[k] = v

    return new, review


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    old = json.load(open(args.input))
    accounts, review = [], []
    for a in old["accounts"]:
        new_a, a_review = migrate_account(a)
        accounts.append(new_a)
        review.extend(a_review)

    # overrides map is keyed by account name already using clean field names
    # (risk, cadence, capStatus, ...) — rename any old key names that changed above
    override_rename = {"cadence": "meetingCadence", "capStatus": "capResearchStatus"}
    overrides = {
        name: {override_rename.get(k, k): v for k, v in fields.items()}
        for name, fields in old.get("overrides", {}).items()
    }

    out = {
        "accounts": accounts,
        "overrides": overrides,
        "meetings": {},
        "tasks": old.get("tasks", []),
        "archived": old.get("archived", []),
        "customTypes": old.get("customTypes", []),
        "layout": old.get("layout"),
        "kpiVisible": old.get("kpiVisible"),
        "columnSort": old.get("columnSort", {}),
        "columnWidths": old.get("columnWidths", {}),
        "lastSynced": {
            "salesforce": old.get("lastSynced", {}).get("salesforce"),
            "meetings": None,
            "eodTodo": old.get("lastSynced", {}).get("eodTodo"),
        },
        "syncLocks": {"bob": None, "meetings": None, "todos": None},
    }
    json.dump(out, open(args.output, "w"), indent=2)

    review_path = args.output.rsplit(".", 1)[0] + "-review.md"
    with open(review_path, "w") as f:
        f.write("# Migration review\n\n")
        if review:
            f.write(f"{len(review)} field(s) need a manual look:\n\n")
            for r in review:
                f.write(f"- {r}\n")
        else:
            f.write("Nothing flagged — every account mapped cleanly.\n")

    print(f"{len(accounts)} accounts, {len(out['tasks'])} tasks, {len(out['archived'])} archived")
    print(f"review: {len(review)} item(s) -> {review_path}")


def demo():
    """ponytail check: one account, one duplicate-pair conflict, confirm priority + drop."""
    sample = {
        "name": "Acme", "sfdcId": "001x", "arr": 100, "arrLive": 200, "arrFallback": 50,
        "arrSumOfAmount": 200, "renewal_date": "2026-01-01", "renewalLive": None,
        "renewalFallback": "2025-01-01", "cadence": "Monthly", "churnScore": 10,
        "csmSentiment": "Thriving", "risk": "Low", "riskRecords": [], "pipeline": 0,
        "activeProcessing": True, "serviceStartDate": "2022-01-01", "supportLevel": "Standard",
        "fiscalYear": "Jan-Dec", "processingFreq": "Monthly", "previousTool": "Excel",
        "seatsOccupied": 10, "payeesPurchased": 10, "seatUtilization": 1.0,
        "instanceSeatCount": 10, "priceIncreaseCap": "3%", "capStatus": "Confirmed",
        "execSponsor": None, "lastEbr": None, "notes": None, "companyType": "Private",
        "industry": "Tech", "impl_status": "Completed", "implProjects": [], "impl_owner": "X",
        "stage": "Live",
    }
    new, review = migrate_account(sample)
    assert new["arrActive"] == 200, "should prefer arrLive over arr/arrFallback"
    assert new["renewalDate"] == "2026-01-01", "should fall back to renewal_date when renewalLive is null"
    assert new["implementation"] == "Completed"
    assert new["stage"] == "Live", "unrelated fields pass through unchanged"
    assert "arrLive" not in new and "arr" not in new
    assert any("arrActive candidates disagree" in r for r in review), "3 disagreeing ARR values should be flagged"
    assert not any("lastEbr" in r for r in review), "lastEbr entirely missing isn't a disagreement"
    print("demo() ok")


if __name__ == "__main__":
    import sys
    if "--demo" in sys.argv:
        demo()
    else:
        main()
