# -*- coding: utf-8 -*-
"""Шукаємо офіційні пояснення прапорців причин: коментарі колонок + приклади."""
from dbx import run_cols

FLAGS = ["is_rejected_by_provider","is_not_responded_by_provider",
         "is_order_not_accepted_by_provider","is_accepted_by_provider",
         "has_eater_cancellation_ticket","number_courier_rejects","order_state"]

print("== column comments (DESCRIBE EXTENDED) ==")
c, rows = run_cols("DESCRIBE TABLE EXTENDED hive_metastore.ng_delivery_spark.fact_order_delivery")
for r in rows:
    if r[0] in FLAGS:
        print(f"  {r[0]:<36} | {r[1]:<12} | comment: {r[2]}")

print("\n== state x accept/reject timestamps присутність ==")
c, rows = run_cols("""
SELECT f.order_state,
  SUM(CASE WHEN f.is_rejected_by_provider THEN 1 ELSE 0 END) prov_rej,
  SUM(CASE WHEN f.is_not_responded_by_provider THEN 1 ELSE 0 END) prov_noresp,
  SUM(CASE WHEN f.is_order_not_accepted_by_provider THEN 1 ELSE 0 END) prov_notacc,
  SUM(CASE WHEN f.is_accepted_by_provider THEN 1 ELSE 0 END) prov_acc,
  SUM(CASE WHEN f.number_courier_rejects>0 THEN 1 ELSE 0 END) courier_rej,
  SUM(CASE WHEN f.has_eater_cancellation_ticket THEN 1 ELSE 0 END) eater_cx,
  SUM(CASE WHEN f.order_accepted_by_provider_at IS NOT NULL THEN 1 ELSE 0 END) has_acc_ts,
  COUNT(*) n
FROM hive_metastore.ng_delivery_spark.fact_order_delivery f
JOIN hive_metastore.ng_delivery_spark.dim_provider_v2 p ON f.provider_id=p.provider_id
WHERE p.country_code='ua' AND p.delivery_vertical LIKE 'store%'
  AND f.order_created_date >= DATE'2026-05-01' AND f.order_created_date <= DATE'2026-06-30'
GROUP BY 1 ORDER BY n DESC
""")
print(" ", c)
for r in rows:
    print("  ", r)
