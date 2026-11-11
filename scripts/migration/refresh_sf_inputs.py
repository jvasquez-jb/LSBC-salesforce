#!/usr/bin/env python3
"""Refresh the org files the migration scripts read, in <working folder>/sf.

Usage: python3 -I refresh_sf_inputs.py <working folder>   (uses the default org)

Writes:
  auth_types.json        licence type name -> Id
  account_ids.csv        LegacyKey__c, Id, PersonContactId of every migrated account
  alert_categories.json  stop code developer name -> id, label, description
  describe_Account.json  sf sobject describe -s Account
  us_states.json         the US state codes the org's address picklist accepts
Run it after every account load, and after licence types or stop codes change.
"""
import csv, json, os, subprocess, sys

sf_dir = os.path.join(sys.argv[1], "sf")
os.makedirs(sf_dir, exist_ok=True)


def sf(*args):
    r = subprocess.run(["sf", *args, "--json"], capture_output=True, text=True)
    return json.loads(r.stdout)["result"]


def query(soql):
    return sf("data", "query", "-q", soql)["records"]


types = {r["Name"]: r["Id"] for r in query("SELECT Id, Name FROM RegulatoryAuthorizationType")}
json.dump(types, open(os.path.join(sf_dir, "auth_types.json"), "w"), indent=1)

accounts = query("SELECT Id, LegacyKey__c, PersonContactId FROM Account WHERE LegacyKey__c != null")
with open(os.path.join(sf_dir, "account_ids.csv"), "w", newline="") as fh:
    w = csv.writer(fh, lineterminator="\n")
    w.writerow(["LegacyKey__c", "Id", "PersonContactId"])
    for r in accounts:
        w.writerow([r["LegacyKey__c"], r["Id"], r.get("PersonContactId") or ""])

cats = {r["DeveloperName"]: {"id": r["Id"], "label": r["MasterLabel"], "desc": r.get("Description") or ""}
        for r in query("SELECT Id, DeveloperName, MasterLabel, Description FROM RecordAlertCategory")}
json.dump(cats, open(os.path.join(sf_dir, "alert_categories.json"), "w"), indent=1)

describe = sf("sobject", "describe", "-s", "Account")
json.dump({"result": describe}, open(os.path.join(sf_dir, "describe_Account.json"), "w"))
US = set("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY "
         "NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY PR VI GU AS MP AA AE AP".split())
states = sorted({p["value"] for f in describe["fields"] if f["name"] == "BillingStateCode"
                 for p in f["picklistValues"] if p["active"]} & US)  # the picklist holds every country's states
json.dump(states, open(os.path.join(sf_dir, "us_states.json"), "w"))
print(f"{len(types)} licence types, {len(accounts)} accounts, {len(cats)} stop codes, {len(states)} state codes")
