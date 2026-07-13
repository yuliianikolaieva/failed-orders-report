# Failed Orders — Weekly Deep-Dive (UA Stores)

Тижневий аналіз failed-ордерів по Bolt Food UA Stores за останні ~2 місяці:
топ-10 партнерів за кількістю фейлів, причини (реконструйовані з прапорців),
розбивка по тижнях, теплокарта fail-rate і топ точок-порушників.

## Structure

- `index.html` — звіт (публікується на GitHub Pages). Українською.
- `dbx.py` — helper-конектор до Databricks (REST API, бере креди з `VARUS/.env`).
- `build_data.py` — тягне weekly × partner × reason агрегати → `data.json`.
- `build_html.py` — рендерить `index.html` з `data.json`.
- `analyze.py` — швидка перевірка топ-10 / причин / тижневих fail-rate у консолі.

## How to refresh

```bash
python3 build_data.py    # pull fresh data from Databricks (needs VARUS/.env credentials)
python3 build_html.py    # render index.html
```

## Data & definitions

Source: Databricks `hive_metastore.ng_delivery_spark.fact_order_delivery` joined to
`dim_provider_v2`, Bolt UA, `delivery_vertical LIKE 'store%'`, period by `order_created_date`
11.05–12.07.2026 (9 повних тижнів Пн–Нд).

- **Failed order** = `order_state IN ('failed','rejected')`.
- **Fail-rate** = failed / усі створені замовлення (delivered + failed + rejected + waiting).
- **Партнер** = `COALESCE(group_name, brand_name)`; **точка** = provider.
- **Тижні** = `DATE_TRUNC('week', order_created_date)`; останній неповний тиждень виключено.

### Reason taxonomy (пріоритетна, взаємовиключна)

1. `is_rejected_by_provider` → Партнер відхилив
2. `is_not_responded_by_provider` → Партнер не відповів (тайм-аут)
3. `is_order_not_accepted_by_provider` → Партнер не прийняв (інше)
4. `has_eater_cancellation_ticket` → Клієнт скасував
5. `number_courier_rejects > 0` → Проблема з кур'єром
6. else → Система / оплата / інше

У таблиці немає текстового поля причини — категорії реконструйовані з булевих прапорців.
