# Orders Health — Weekly Deep-Dive (UA Stores)

Тижневий аналіз здоровʼя замовлень по Bolt Food UA Stores за 01.05–30.06.2026,
у форматі 3 вкладок:

- **Failed ордери** — топ-15 партнерів за фейлами, пояснення причин, втрачений GMV, теплокарта.
- **Bad orders** — доставлені, але «зіпсовані» замовлення (`is_bad_order`): винуватець (attribution) + причини, тижнева динаміка, топ-15.
- **Скарги (complaints)** — звернення у підтримку (`has_ticket`) + категорії, на що скаржаться клієнти.

## Що означає кожна причина (rejected vs failed)

- `rejected` — партнер жодного разу не прийняв замовлення (відхилив або не встиг за 5 хв → Bolt авто-скасовує).
- `failed` — замовлення зламалося переважно вже ПІСЛЯ прийняття (≈87% failed були прийняті), через кур'єра / скасування клієнта / оплату.

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
01.05–30.06.2026 (10 тижнів Пн–Нд; крайові тижні 27.04 і 29.06 часткові).

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
