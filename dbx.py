# -*- coding: utf-8 -*-
"""Shared Databricks REST-API query helper (reuses VARUS .env)."""
import json, os, time, urllib.request, ssl
from pathlib import Path

ENV = Path("/Users/yuliia.nikolaieva/Downloads/Reports GIT HUB/VARUS/.env")
for line in ENV.read_text().splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, _, v = line.partition("=")
    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

HOST = os.environ["DATABRICKS_HOST"]
TOKEN = os.environ["DATABRICKS_TOKEN"]
WID = os.environ["DATABRICKS_WAREHOUSE_ID"]
_CTX = ssl.create_default_context()
if os.environ.get("DATABRICKS_TLS_NO_VERIFY", "").lower() in ("1", "true", "yes"):
    _CTX.check_hostname = False
    _CTX.verify_mode = ssl.CERT_NONE


def run(sql):
    body = json.dumps({"warehouse_id": WID, "statement": sql,
                       "wait_timeout": "50s", "format": "JSON_ARRAY"}).encode()
    req = urllib.request.Request("https://%s/api/2.0/sql/statements" % HOST, data=body,
        headers={"Authorization": "Bearer %s" % TOKEN, "Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, context=_CTX))
    sid = d["statement_id"]
    while d["status"]["state"] in ("PENDING", "RUNNING"):
        time.sleep(3)
        d = json.load(urllib.request.urlopen(urllib.request.Request(
            "https://%s/api/2.0/sql/statements/%s" % (HOST, sid),
            headers={"Authorization": "Bearer %s" % TOKEN}), context=_CTX))
    if d["status"]["state"] != "SUCCEEDED":
        raise SystemExit("FAIL " + json.dumps(d["status"]))
    cols = [c["name"] for c in d["result"]["manifest"]["schema"]["columns"]] if False else None
    return d.get("result", {}).get("data_array", []) or []


def run_cols(sql):
    """Return (columns, rows)."""
    body = json.dumps({"warehouse_id": WID, "statement": sql,
                       "wait_timeout": "50s", "format": "JSON_ARRAY"}).encode()
    req = urllib.request.Request("https://%s/api/2.0/sql/statements" % HOST, data=body,
        headers={"Authorization": "Bearer %s" % TOKEN, "Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, context=_CTX))
    sid = d["statement_id"]
    while d["status"]["state"] in ("PENDING", "RUNNING"):
        time.sleep(3)
        d = json.load(urllib.request.urlopen(urllib.request.Request(
            "https://%s/api/2.0/sql/statements/%s" % (HOST, sid),
            headers={"Authorization": "Bearer %s" % TOKEN}), context=_CTX))
    if d["status"]["state"] != "SUCCEEDED":
        raise SystemExit("FAIL " + json.dumps(d["status"]))
    manifest = d.get("result", {}).get("manifest") or d.get("manifest", {})
    cols = [c["name"] for c in manifest["schema"]["columns"]]
    return cols, d.get("result", {}).get("data_array", []) or []


if __name__ == "__main__":
    # 1) distinct order states, last 2 months, UA stores
    print("== order_state distribution (UA store, last 60d) ==")
    c, rows = run_cols("""
      SELECT f.order_state, COUNT(*) n
      FROM hive_metastore.ng_delivery_spark.fact_order_delivery f
      JOIN hive_metastore.ng_delivery_spark.dim_provider_v2 p ON f.provider_id=p.provider_id
      WHERE p.country_code='ua' AND p.delivery_vertical LIKE 'store%'
        AND f.order_created_date >= DATE_SUB(CURRENT_DATE(), 60)
      GROUP BY 1 ORDER BY 2 DESC
    """)
    for r in rows:
        print("  ", r)

    # 2) columns of fact_order_delivery mentioning cancel/fail/reason/reject
    print("== reason crosstab (failed+rejected, UA store, 60d) ==")
    c, rows = run_cols("""
      SELECT f.order_state,
        f.is_rejected_by_provider AS prov_rej,
        f.is_not_responded_by_provider AS prov_noresp,
        f.is_order_not_accepted_by_provider AS prov_notacc,
        CASE WHEN f.number_courier_rejects>0 THEN 1 ELSE 0 END AS courier_rej,
        f.has_eater_cancellation_ticket AS eater_cancel,
        COUNT(*) n
      FROM hive_metastore.ng_delivery_spark.fact_order_delivery f
      JOIN hive_metastore.ng_delivery_spark.dim_provider_v2 p ON f.provider_id=p.provider_id
      WHERE p.country_code='ua' AND p.delivery_vertical LIKE 'store%'
        AND f.order_created_date >= DATE_SUB(CURRENT_DATE(), 60)
        AND f.order_state IN ('failed','rejected')
      GROUP BY 1,2,3,4,5,6 ORDER BY n DESC
    """)
    print(" ", c)
    for r in rows:
        print("  ", r)
