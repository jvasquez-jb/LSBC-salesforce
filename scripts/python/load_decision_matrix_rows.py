"""Loads a decision matrix version's rows from data/decisionMatrices/<Name>.csv.

Usage: python3 scripts/python/load_decision_matrix_rows.py <MatrixName> [version number, default 1]
The version must be Draft (deploy the definition with <status>Draft</status> first, then redeploy as Active).
Rows go through the Connect API, because a direct CalculationMatrixRow insert skips the row hash key.
"""
import csv, json, subprocess, sys

name = sys.argv[1]
version = sys.argv[2] if len(sys.argv) > 2 else "1"


def sf(*args):
    r = subprocess.run(["sf", *args, "--json"], capture_output=True, text=True)
    return json.loads(r.stdout)


def query(soql):
    return sf("data", "query", "-q", soql)["result"]["records"]


label = query(f"SELECT MasterLabel FROM DecisionMatrixDefinition WHERE DeveloperName = '{name}'")[0]["MasterLabel"]
matrix = query(f"SELECT Id FROM CalculationMatrix WHERE Name = '{label}'")[0]["Id"]  # the matrix record is named by its label
ver = query(f"SELECT Id, VersionNumber FROM CalculationMatrixVersion WHERE CalculationMatrixId = '{matrix}' AND VersionNumber = {version}")[0]["Id"]
rows = list(csv.DictReader(open(f"data/decisionMatrices/{name}.csv")))
for i in range(0, len(rows), 50):
    body = {"rows": [{"rowData": dict(r)} for r in rows[i:i + 50]]}  # every column, blanks included: a row missing a column is rejected
    open("dm_rows.tmp.json", "w").write(json.dumps(body))
    r = subprocess.run(["sf", "api", "request", "rest", f"/services/data/v66.0/connect/omnistudio/decision-matrices/{matrix}/versions/{ver}/rows",
                        "--method", "POST", "--body", "@dm_rows.tmp.json"], capture_output=True, text=True)
    print(f"rows {i + 1}-{i + len(body['rows'])}:", (r.stdout or r.stderr)[:300].replace("\n", " "))
