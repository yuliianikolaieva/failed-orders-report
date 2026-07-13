# -*- coding: utf-8 -*-
"""Failed orders (order_state IN failed/rejected) — UA stores, last ~2 months.
Weekly breakdown by top-10 partners (group_name) and failure reason.
Writes data.json for the HTML report."""
import json
from pathlib import Path
from dbx import run_cols

HERE = Path(__file__).parent
# Період 01.05–30.06.2026, розбивка по тижнях (Пн–Нд).
START = "2026-05-01"
END = "2026-06-30"

# Мутуально-виключна класифікація причини (пріоритет зверху вниз)
REASON = """
CASE
  WHEN f.is_rejected_by_provider THEN 'Партнер відхилив'
  WHEN f.is_not_responded_by_provider THEN 'Партнер не відповів (тайм-аут)'
  WHEN f.is_order_not_accepted_by_provider THEN 'Партнер не прийняв (інше)'
  WHEN f.has_eater_cancellation_ticket THEN 'Клієнт скасував'
  WHEN f.number_courier_rejects > 0 THEN 'Проблема з курʼєром'
  ELSE 'Система / оплата / інше'
END
"""

BASE = f"""
FROM hive_metastore.ng_delivery_spark.fact_order_delivery f
JOIN hive_metastore.ng_delivery_spark.dim_provider_v2 p ON f.provider_id=p.provider_id
WHERE p.country_code='ua' AND p.delivery_vertical LIKE 'store%'
  AND f.order_created_date >= DATE'{START}' AND f.order_created_date <= DATE'{END}'
"""

GRP = "COALESCE(p.group_name, p.brand_name)"

def rows_to_dicts(cols, rows):
    out = []
    for r in rows:
        d = {}
        for k, v in zip(cols, r):
            d[k] = v
        out.append(d)
    return out

# 1) Weekly totals per partner (all terminal states)
print("Q1 weekly partner totals...")
c1, r1 = run_cols(f"""
SELECT {GRP} AS grp,
  DATE_FORMAT(DATE_TRUNC('week', f.order_created_date),'yyyy-MM-dd') AS wk,
  COUNT(*) AS total,
  SUM(CASE WHEN f.order_state='delivered' THEN 1 ELSE 0 END) AS delivered,
  SUM(CASE WHEN f.order_state IN ('failed','rejected') THEN 1 ELSE 0 END) AS failed,
  SUM(CASE WHEN f.order_state='delivered' THEN COALESCE(f.order_gmv_eur,0) ELSE 0 END) AS deliv_gmv,
  SUM(CASE WHEN f.order_state IN ('failed','rejected') THEN COALESCE(f.order_gmv_eur,0) ELSE 0 END) AS lost_gmv
{BASE}
GROUP BY 1,2
""")
weekly_totals = rows_to_dicts(c1, r1)
print("  rows", len(weekly_totals))

# 2) Weekly reason breakdown per partner (failed+rejected only)
print("Q2 weekly reason breakdown...")
c2, r2 = run_cols(f"""
SELECT {GRP} AS grp,
  DATE_FORMAT(DATE_TRUNC('week', f.order_created_date),'yyyy-MM-dd') AS wk,
  {REASON} AS reason,
  COUNT(*) AS n,
  SUM(COALESCE(f.order_gmv_eur,0)) AS gmv
{BASE}
  AND f.order_state IN ('failed','rejected')
GROUP BY 1,2,3
""")
weekly_reasons = rows_to_dicts(c2, r2)
print("  rows", len(weekly_reasons))

# 3) Partner metadata (segment, AM, cities, active stores)
print("Q3 partner meta...")
c3, r3 = run_cols(f"""
SELECT {GRP} AS grp,
  MAX(p.business_segment_v2) AS seg,
  CONCAT_WS(', ', COLLECT_SET(p.account_manager_name)) AS am,
  COUNT(DISTINCT p.provider_id) AS stores
FROM hive_metastore.ng_delivery_spark.dim_provider_v2 p
WHERE p.country_code='ua' AND p.delivery_vertical LIKE 'store%'
GROUP BY 1
""")
meta = rows_to_dicts(c3, r3)
print("  rows", len(meta))

# 4) Top failing stores (per store) for top partners — фетчимо всі, фільтруємо в Python
print("Q4 per-store failed...")
c4, r4 = run_cols(f"""
SELECT {GRP} AS grp,
  p.provider_name AS store,
  p.city_name AS city,
  COUNT(*) AS total,
  SUM(CASE WHEN f.order_state IN ('failed','rejected') THEN 1 ELSE 0 END) AS failed
{BASE}
GROUP BY 1,2,3
HAVING SUM(CASE WHEN f.order_state IN ('failed','rejected') THEN 1 ELSE 0 END) >= 10
""")
stores = rows_to_dicts(c4, r4)
print("  rows", len(stores))

json.dump({
    "start": START, "end": END,
    "weekly_totals": weekly_totals,
    "weekly_reasons": weekly_reasons,
    "meta": meta,
    "stores": stores,
}, open(HERE / "data.json", "w"), ensure_ascii=False)
print("saved data.json")
