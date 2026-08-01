# -*- coding: utf-8 -*-
"""Генерує index.html — тижневий аналіз failed-ордерів по топ-15 партнерах (UA stores)."""
import json, collections
from pathlib import Path
HERE = Path(__file__).parent
d = json.load(open(HERE / "data.json"))

def num(x): return float(x) if x is not None else 0.0
def i(x): return int(num(x))

wt, wr = d["weekly_totals"], d["weekly_reasons"]
weeks = sorted({r["wk"] for r in wt})
meta = {m["grp"]: m for m in d["meta"]}

REASONS = ['Партнер відхилив','Партнер не відповів (тайм-аут)','Партнер не прийняв (інше)',
           'Клієнт скасував','Проблема з курʼєром','Система / оплата / інше']
RCOLOR = {
  'Партнер відхилив':'#dc2626',
  'Партнер не відповів (тайм-аут)':'#ea580c',
  'Партнер не прийняв (інше)':'#f59e0b',
  'Клієнт скасував':'#2563eb',
  'Проблема з курʼєром':'#7c3aed',
  'Система / оплата / інше':'#6b7280',
}

# ---- partner totals ----
tot = collections.defaultdict(lambda:[0,0,0])
gmv = collections.defaultdict(lambda:[0.0,0.0])  # [deliv_gmv, lost_gmv]
for r in wt:
    g=r["grp"] or "—"; tot[g][0]+=i(r["total"]); tot[g][1]+=i(r["delivered"]); tot[g][2]+=i(r["failed"])
    gmv[g][0]+=num(r.get("deliv_gmv")); gmv[g][1]+=num(r.get("lost_gmv"))
G=sum(v[0] for v in tot.values()); D=sum(v[1] for v in tot.values()); F=sum(v[2] for v in tot.values())
GMV_DELIV=sum(v[0] for v in gmv.values()); GMV_LOST=sum(v[1] for v in gmv.values())
top = sorted(tot.items(), key=lambda kv:-kv[1][2])[:15]
topnames=[g for g,_ in top]
TOPN=len(top)

# ---- overall weekly ----
ow = collections.defaultdict(lambda:[0,0,0])
for r in wt:
    ow[r["wk"]][0]+=i(r["total"]); ow[r["wk"]][1]+=i(r["delivered"]); ow[r["wk"]][2]+=i(r["failed"])
ow_total=[ow[w][0] for w in weeks]; ow_failed=[ow[w][2] for w in weeks]
ow_rate=[round(ow[w][2]/ow[w][0]*100,2) if ow[w][0] else 0 for w in weeks]

# ---- reason totals & weekly (top10) ----
rtot=collections.defaultdict(int)
rgmv=collections.defaultdict(float)
rweek=collections.defaultdict(lambda:collections.defaultdict(int))
preason=collections.defaultdict(lambda:collections.defaultdict(int))  # partner->reason
for r in wr:
    g=r["grp"] or "—"
    if g in topnames:
        rtot[r["reason"]]+=i(r["n"]); rweek[r["reason"]][r["wk"]]+=i(r["n"])
        rgmv[r["reason"]]+=num(r.get("gmv"))
        preason[g][r["reason"]]+=i(r["n"])
TF=sum(rtot.values())
# overall weekly lost gmv
ow_lostgmv=collections.defaultdict(float)
for r in wt:
    ow_lostgmv[r["wk"]]+=num(r.get("lost_gmv"))
prov_share=(rtot['Партнер відхилив']+rtot['Партнер не відповів (тайм-аут)']+rtot['Партнер не прийняв (інше)'])/TF*100

# ---- weekly per partner (rate + counts) ----
byw=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0]))
for r in wt:
    g=r["grp"] or "—"
    if g in topnames:
        byw[g][r["wk"]][0]+=i(r["total"]); byw[g][r["wk"]][1]+=i(r["failed"])

def prate(g,w):
    t,f=byw[g][w]; return f/t*100 if t else None

# ---- top failing stores among top10 ----
stores=[s for s in d["stores"] if (s["grp"] or "—") in topnames]
for s in stores:
    s["_f"]=i(s["failed"]); s["_t"]=i(s["total"]); s["_r"]=s["_f"]/s["_t"]*100 if s["_t"] else 0
stores=sorted(stores,key=lambda s:-s["_f"])[:15]

# dominant reason per partner
def dom_reason(g):
    rs=preason[g]
    if not rs: return ("—",0)
    k=max(rs,key=rs.get); return (k, rs[k]/sum(rs.values())*100)

wlabels=[w[5:].replace("-",".") for w in weeks]  # MM.DD

# heatmap color
def hcol(v):
    if v is None: return ("","-")
    if v>=20: return ("cell-crit","%.1f%%"%v)
    if v>=10: return ("cell-warn","%.1f%%"%v)
    if v>=6: return ("","%.1f%%"%v)
    return ("cell-good","%.1f%%"%v)

# WoW change first->last available week per partner
def wow(g):
    vals=[(w,prate(g,w)) for w in weeks if prate(g,w) is not None]
    if len(vals)<2: return None
    return vals[-1][1]-vals[0][1]

# ============ build partner rows ============
rows_html=""
medals=["🥇","🥈","🥉"]+[""]*20
for idx,(g,v) in enumerate(top):
    total,deliv,fail=v; rate=fail/total*100
    dr,drp=dom_reason(g)
    m=meta.get(g,{})
    seg=(m.get("seg") or "—")
    ch=wow(g)
    ch_html=(f'<span class="{"down" if ch>0 else "up"}">{"+" if ch>0 else ""}{ch:.1f} п.п.</span>' if ch is not None else "—")
    badge = 'badge-r' if rate>=12 else ('badge-y' if rate>=7 else 'badge-g')
    lost=gmv[g][1]
    rows_html+=f"""<tr>
      <td>{medals[idx]} <b>{g}</b><div style="font-size:10px;color:#6b7280">{seg}</div></td>
      <td class="num">{total:,}</td>
      <td class="num"><b>{fail:,}</b></td>
      <td class="num"><span class="badge {badge}">{rate:.1f}%</span></td>
      <td class="num" style="color:#991b1b;font-weight:700">€{lost:,.0f}</td>
      <td class="num">{ch_html}</td>
      <td><span style="color:{RCOLOR.get(dr,'#333')};font-weight:600">{dr}</span> <span style="color:#6b7280">{drp:.0f}%</span></td>
    </tr>""".replace(",", " ")

# totals row for top-15 table (summed header)
t_created=sum(v[0] for _,v in top)
t_failed=sum(v[2] for _,v in top)
t_rate=t_failed/t_created*100 if t_created else 0
t_lost=sum(gmv[g][1] for g,_ in top)
_dr=max(rtot,key=rtot.get) if rtot else "—"
_drp=rtot[_dr]/TF*100 if TF else 0
totals_row=f"""<tr style="background:#1A1A2E">
  <td style="color:#fff;font-weight:700">РАЗОМ топ-15 ({TOPN})</td>
  <td class="num" style="color:#fff;font-weight:700">{t_created:,}</td>
  <td class="num" style="color:#fff;font-weight:700">{t_failed:,}</td>
  <td class="num"><span class="badge badge-r">{t_rate:.1f}%</span></td>
  <td class="num" style="color:#fca5a5;font-weight:800">€{t_lost:,.0f}</td>
  <td class="num" style="color:#9ca3af">{t_failed/F*100:.0f}% усіх фейлів</td>
  <td style="color:#e5e7eb"><span class="dot" style="background:{RCOLOR.get(_dr,'#fff')}"></span> {_dr} <span style="color:#9ca3af">{_drp:.0f}%</span></td>
</tr>""".replace(",", " ")

# heatmap rows
heat_html=""
for g,_ in top:
    cells=""
    for w in weeks:
        cls,txt=hcol(prate(g,w))
        cells+=f'<td class="num {cls}">{txt}</td>'
    heat_html+=f'<tr><td style="white-space:nowrap"><b>{g}</b></td>{cells}</tr>'

# per-partner reason stacked bars (share)
pbar_html=""
for g,_ in top:
    rs=preason[g]; s=sum(rs.values()) or 1
    seg=""
    for reason in REASONS:
        n=rs.get(reason,0)
        if n<=0: continue
        pct=n/s*100
        seg+=f'<div class="bar-fill" style="width:{pct:.1f}%;background:{RCOLOR[reason]}" title="{reason}: {n} ({pct:.0f}%)">{(("%.0f%%"%pct) if pct>=8 else "")}</div>'
    pbar_html+=f'<div class="store-row"><div class="store-name" title="{g}">{g} <b style="color:#111">{sum(rs.values())}</b></div><div class="bar-bg" style="display:flex">{seg}</div></div>'

# stores table
store_html=""
for s in stores:
    store_html+=f'<tr><td><b>{s["grp"]}</b></td><td>{s["store"]}</td><td>{s.get("city") or "—"}</td><td class="num">{s["_t"]:,}</td><td class="num"><b>{s["_f"]:,}</b></td><td class="num"><span class="badge {"badge-r" if s["_r"]>=12 else ("badge-y" if s["_r"]>=7 else "badge-g")}">{s["_r"]:.1f}%</span></td></tr>'.replace(",", " ")

# reason legend
legend_html="".join(f'<span><span class="dot" style="background:{RCOLOR[r]}"></span>{r}</span>' for r in REASONS)

# ---- пояснення причин (що саме означає) ----
EXPLAIN = {
 'Партнер відхилив': {
   'flag':'is_rejected_by_provider = true · order_state = rejected',
   'who':'Партнер','fault':'fault',
   'what':'Партнер <b>активно натиснув «Відхилити»</b> у планшеті/додатку Bolt на вхідне замовлення. За правилами Bolt це роблять, коли позиції немає в наявності, кухня/склад закривається або точка перевантажена і не встигає зібрати.',
   'why':'Замовлення так і не було прийняте — клієнт одразу отримує скасування. Це прямий сигнал про <b>out-of-stock, неактуальне меню або режим роботи</b>.'
 },
 'Партнер не відповів (тайм-аут)': {
   'flag':'is_not_responded_by_provider = true · order_state = rejected',
   'who':'Партнер','fault':'fault',
   'what':'Партнер <b>не відреагував на замовлення протягом 5 хвилин</b> (за загальними умовами Bolt партнер має підтвердити або відхилити протягом 5 хв). Після тайм-ауту Bolt <b>автоматично скасовує</b> замовлення й компенсує клієнту.',
   'why':'Найтиповіша партнерська причина. Означає, що <b>ніхто не дивиться в планшет</b>: не заряджений/вимкнений девайс, немає звуку сповіщень, точка фактично не працює, або не увімкнено auto-accept.'
 },
 'Партнер не прийняв (інше)': {
   'flag':'is_order_not_accepted_by_provider = true (без rejected/тайм-ауту)',
   'who':'Партнер','fault':'fault',
   'what':'Замовлення <b>не отримало статусу «Прийнято»</b> з боку партнера, але це не класичне «відхилив» і не чистий 5-хв тайм-аут (проміжні/технічні сценарії неприйняття на стороні точки).',
   'why':'Залишкова партнерська категорія — теж вказує на проблеми з прийняттям замовлень на точці.'
 },
 'Клієнт скасував': {
   'flag':'has_eater_cancellation_ticket = true',
   'who':'Клієнт','fault':'neutral',
   'what':'На замовлення заведено <b>тикет скасування від клієнта</b> — користувач сам скасував (передумав, помилився, надто довге очікування).',
   'why':'Не провина партнера напряму, але <b>довге очікування/повільне прийняття</b> провокує скасування. Частина таких замовлень встигла бути прийнятою партнером до скасування.'
 },
 "Проблема з курʼєром": {
   'flag':'number_courier_rejects > 0',
   'who':'Логістика','fault':'neutral',
   'what':'По замовленню були <b>відмови кур\'єрів</b> від призначення (або кур\'єра не вдалося знайти вчасно). Замовлення падає на етапі доставки.',
   'why':'Проблема ліквідності кур\'єрів / зон доставки, а не партнера. Іноді комбінується зі скасуванням клієнта через довге очікування.'
 },
 'Система / оплата / інше': {
   'flag':'жоден прапорець не спрацював',
   'who':'Система','fault':'neutral',
   'what':'Замовлення впало <b>без явного прапорця причини</b>: найчастіше це <b>відхилення оплати/авторизації картки</b>, технічні/платіжні збої або антифрод (за класифікацією Bolt статус Failed = payment declined / processing error).',
   'why':'Не залежить від партнера. Дивитись у бік платіжного процесингу та технічних інцидентів.'
 },
}
FAULTBADGE={'fault':('badge-r','Партнер'),'neutral':('badge-b',None)}
explain_html=""
for reason in REASONS:
    e=EXPLAIN[reason]; n=rtot.get(reason,0); pct=n/TF*100 if TF else 0
    whocls={'Партнер':'badge-r','Клієнт':'badge-b','Логістика':'badge-y','Система':'badge-y'}.get(e['who'],'badge-b')
    explain_html+=f"""<div class="card" style="border-left:4px solid {RCOLOR[reason]}">
      <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
        <span class="dot" style="background:{RCOLOR[reason]};width:12px;height:12px"></span>
        <h3 style="margin:0">{reason}</h3>
        <span class="badge {whocls}" style="margin-left:auto">{e['who']}</span>
        <span class="badge badge-y">{n} · {pct:.0f}%</span>
      </div>
      <div style="font-size:12.5px;color:#374151;margin-bottom:8px">{e['what']}</div>
      <div style="font-size:12px;color:#6b7280;margin-bottom:8px"><b>Наслідок:</b> {e['why']}</div>
      <div style="font-size:11px;color:#334155;background:#f1f5f9;border-radius:6px;padding:6px 9px"><code style="font-size:11px">{e['flag']}</code></div>
    </div>"""

# ---- lost GMV aggregates ----
PARTNER_REASONS = {'Партнер відхилив','Партнер не відповів (тайм-аут)','Партнер не прийняв (інше)'}
GMV_LOST_TOP = sum(rgmv.values())
lost_partner = sum(rgmv[r] for r in PARTNER_REASONS)
ow_lost = [round(ow_lostgmv[w]) for w in weeks]
# reason -> lost gmv table
rgmv_html=""
for reason in sorted(REASONS, key=lambda r:-rgmv[r]):
    v=rgmv[reason]; sh=v/GMV_LOST_TOP*100 if GMV_LOST_TOP else 0
    who={'Партнер відхилив':'Партнер','Партнер не відповів (тайм-аут)':'Партнер','Партнер не прийняв (інше)':'Партнер','Клієнт скасував':'Клієнт',"Проблема з курʼєром":'Логістика','Система / оплата / інше':'Система'}[reason]
    rgmv_html+=f'<tr><td><span class="dot" style="background:{RCOLOR[reason]}"></span> {reason}</td><td>{who}</td><td class="num"><b>€{v:,.0f}</b></td><td class="num">{sh:.0f}%</td></tr>'.replace(",", " ")
# top partners by lost gmv
top_lost=sorted(topnames, key=lambda g:-gmv[g][1])[:8]
toplost_html=""
for g in top_lost:
    toplost_html+=f'<tr><td><b>{g}</b></td><td class="num">{tot[g][2]:,}</td><td class="num" style="color:#991b1b;font-weight:700">€{gmv[g][1]:,.0f}</td><td class="num">{gmv[g][1]/GMV_LOST*100:.1f}%</td></tr>'.replace(",", " ")

# ================= BAD ORDERS =================
bw = d.get("bad_weekly", []); ba = d.get("bad_attr", [])
BAD=sum(i(r["bad"]) for r in bw); DEL_B=sum(i(r["delivered"]) for r in bw)
TIC=sum(i(r["tickets"]) for r in bw); LATE10=sum(i(r["late10"]) for r in bw); LOW=sum(i(r["lowrate"]) for r in bw)
bad_rate=BAD/DEL_B*100 if DEL_B else 0
tic_rate=TIC/DEL_B*100 if DEL_B else 0
late_rate=LATE10/DEL_B*100 if DEL_B else 0

ACTOR_LABEL={'provider':'Партнер','courier':'Курʼєр','supply':'Ліквідність кур\'єрів','eater':'Клієнт','bolt':'Bolt (платформа)','unknown':'Невідомо'}
ACTOR_COLOR={'provider':'#dc2626','courier':'#7c3aed','supply':'#ea580c','eater':'#2563eb','bolt':'#0891b2','unknown':'#9ca3af'}
actor=collections.defaultdict(int)
for r in ba: actor[r["actor"]]+=i(r["n"])
BATT=sum(actor.values()) or 1
actor_order=[a for a in ['provider','courier','supply','eater','bolt','unknown'] if actor.get(a)]

def btheme(rs):
    rs=(rs or "").lower()
    if any(k in rs for k in ("delay","eta_error","late","took_longer","not_moving","redispatch","starvation","dispatch","batching","assignment","underestimate","overestimate","cold")): return "Запізнення / довга доставка"
    if "out_of_stock" in rs: return "Немає товару (out of stock)"
    if "did_not_respond" in rs or "closed" in rs or "too_many_orders" in rs or "device_issue" in rs or "do_not_wish" in rs: return "Партнер недоступний / не прийняв"
    if "manually_failed_by_cs" in rs or "automatically_failed" in rs: return "Скасовано підтримкою / системою"
    if "missing_item" in rs or "wrong_item" in rs or "entirely_wrong" in rs or "ignored_my_order_notes" in rs: return "Відсутні / неправильні позиції"
    if any(k in rs for k in ("spoiled","undercooked","overcooked","expired","object_detected","contaminated","poisoning","damaged","spilled","does_not_match","description","photo","expectations","burnt")): return "Якість їжі / товару"
    if "courier" in rs: return "Проблеми з курʼєром"
    if "never_delivered" in rs: return "Не доставлено"
    if any(k in rs for k in ("price","charged","pin","menu","question")): return "Оплата / ціна / питання"
    return "Інше"
THEME_COLOR={
 "Запізнення / довга доставка":"#ea580c","Скасовано підтримкою / системою":"#6b7280",
 "Партнер недоступний / не прийняв":"#dc2626","Відсутні / неправильні позиції":"#7c3aed",
 "Немає товару (out of stock)":"#f59e0b","Проблеми з курʼєром":"#0891b2",
 "Якість їжі / товару":"#16a34a","Оплата / ціна / питання":"#2563eb","Не доставлено":"#991b1b","Інше":"#9ca3af"}
th=collections.defaultdict(int)
for r in ba: th[btheme(r["reason"])]+=i(r["n"])
TTH=sum(th.values()) or 1

# weekly overall
bw_del=collections.defaultdict(int); bw_bad=collections.defaultdict(int); bw_tic=collections.defaultdict(int)
for r in bw:
    bw_del[r["wk"]]+=i(r["delivered"]); bw_bad[r["wk"]]+=i(r["bad"]); bw_tic[r["wk"]]+=i(r["tickets"])
ow_bad=[bw_bad[w] for w in weeks]
ow_badrate=[round(bw_bad[w]/bw_del[w]*100,2) if bw_del[w] else 0 for w in weeks]
ow_tic=[bw_tic[w] for w in weeks]
ow_ticrate=[round(bw_tic[w]/bw_del[w]*100,2) if bw_del[w] else 0 for w in weeks]
# weekly actor stacked
awk=collections.defaultdict(lambda:collections.defaultdict(int))
for r in ba: awk[r["actor"]][r["wk"]]+=i(r["n"])

# per-partner
btot=collections.defaultdict(lambda:[0,0,0])  # deliv, bad, tickets
bweekp=collections.defaultdict(lambda:collections.defaultdict(lambda:[0,0]))  # partner->wk->[deliv,bad]
for r in bw:
    g=r["grp"] or "—"; btot[g][0]+=i(r["delivered"]); btot[g][1]+=i(r["bad"]); btot[g][2]+=i(r["tickets"])
    bweekp[g][r["wk"]][0]+=i(r["delivered"]); bweekp[g][r["wk"]][1]+=i(r["bad"])
topbad=sorted(btot.items(),key=lambda kv:-kv[1][1])[:15]

# actor table + doughnut data
actor_tbl=""
for a in actor_order:
    n=actor[a]; actor_tbl+=f'<tr><td><span class="dot" style="background:{ACTOR_COLOR[a]}"></span> {ACTOR_LABEL[a]}</td><td class="num"><b>{n:,}</b></td><td class="num">{n/BATT*100:.0f}%</td></tr>'.replace(",", " ")
# theme table (з описом кожної теми)
THEME_DESC={
 "Запізнення / довга доставка":"Замовлення доставлене із запізненням: довге готування партнером, повільна доставка/помилка ETA курʼєра, довге призначення курʼєра або страва приїхала холодною.",
 "Скасовано підтримкою / системою":"Замовлення позначене як bad через ручне скасування оператором підтримки (manually_failed_by_cs) або автоматичне скасування системою.",
 "Партнер недоступний / не прийняв":"Партнер не відповів на замовлення, був зачинений, перевантажений або мав проблему з девайсом (did_not_respond, closed, too_many_orders, device_issue).",
 "Відсутні / неправильні позиції":"Клієнт отримав не ті або не всі товари: відсутня позиція, неправильний товар, цілком інше замовлення, проігноровані примітки.",
 "Немає товару (out of stock)":"Позиції не було в наявності на момент збору замовлення (items_out_of_stock).",
 "Проблеми з курʼєром":"Дії/поведінка курʼєра: не знайшов клієнта, грубість, проблема зі здачею, не виходив на звʼязок.",
 "Якість їжі / товару":"Зіпсований смак/запах, недо-/переготовано, прострочене, пошкоджене, сторонній предмет, не відповідає опису чи фото.",
 "Оплата / ціна / питання":"Питання щодо ціни/розрахунку, подвійне списання, помилка в меню, питання по PIN/оплаті.",
 "Не доставлено":"Замовлення так і не доставили клієнту (order_never_delivered).",
 "Інше":"Інші або нерозпізнані причини.",
}
theme_tbl=""
for t,n in sorted(th.items(),key=lambda kv:-kv[1]):
    theme_tbl+=f'<tr><td><span class="dot" style="background:{THEME_COLOR.get(t,"#9ca3af")}"></span> <b>{t}</b><div style="font-size:10.5px;color:#6b7280;margin-top:2px;line-height:1.4">{THEME_DESC.get(t,"")}</div></td><td class="num"><b>{n:,}</b></td><td class="num">{n/TTH*100:.0f}%</td></tr>'.replace(",", " ")
# per-partner bad table + heatmap
def bhcol(v):
    if v is None: return ("","-")
    if v>=12: return ("cell-crit","%.1f%%"%v)
    if v>=8: return ("cell-warn","%.1f%%"%v)
    if v>=5: return ("","%.1f%%"%v)
    return ("cell-good","%.1f%%"%v)
badrows=""
for idx,(g,v) in enumerate(topbad):
    dl,bd,tk=v; br=bd/dl*100 if dl else 0; tr_=tk/dl*100 if dl else 0
    bbadge='badge-r' if br>=12 else ('badge-y' if br>=8 else 'badge-g')
    tbadge='badge-r' if tr_>=6 else ('badge-y' if tr_>=3 else 'badge-g')
    badrows+=f'<tr><td>{medals[idx]} <b>{g}</b></td><td class="num">{dl:,}</td><td class="num"><b>{bd:,}</b></td><td class="num"><span class="badge {bbadge}">{br:.1f}%</span></td><td class="num">{tk:,}</td><td class="num"><span class="badge {tbadge}">{tr_:.1f}%</span></td></tr>'.replace(",", " ")
# totals row bad
B_del=sum(v[0] for _,v in topbad); B_bad=sum(v[1] for _,v in topbad); B_tic=sum(v[2] for _,v in topbad)
badtotals=f'<tr style="background:#1A1A2E"><td style="color:#fff;font-weight:700">РАЗОМ топ-15</td><td class="num" style="color:#fff;font-weight:700">{B_del:,}</td><td class="num" style="color:#fff;font-weight:700">{B_bad:,}</td><td class="num"><span class="badge badge-r">{B_bad/B_del*100:.1f}%</span></td><td class="num" style="color:#fff;font-weight:700">{B_tic:,}</td><td class="num"><span class="badge badge-r">{B_tic/B_del*100:.1f}%</span></td></tr>'.replace(",", " ")
# heatmap bad rate
badheat=""
for g,_ in topbad:
    cells=""
    for w in weeks:
        dlb=bweekp[g][w]; rate=dlb[1]/dlb[0]*100 if dlb[0] else None
        cls,txt=bhcol(rate); cells+=f'<td class="num {cls}">{txt}</td>'
    badheat+=f'<tr><td style="white-space:nowrap"><b>{g}</b></td>{cells}</tr>'

# ================= COMPLAINTS (скарги) =================
def ctheme(rs):
    rs=(rs or "").lower()
    if "missing_item" in rs or "wrong_item" in rs or "entirely_wrong" in rs or "ignored_my_order_notes" in rs: return "Відсутні / неправильні позиції"
    if any(k in rs for k in ("spoiled","undercooked","overcooked","expired","object_detected","contaminated","poisoning","damaged","spilled","does_not_match","description","photo","expectations","burnt","cold")): return "Якість їжі / товару"
    if "never_delivered" in rs: return "Не доставлено"
    if "courier" in rs: return "Проблеми з курʼєром"
    if any(k in rs for k in ("late","took_longer","not_moving")): return "Довге очікування / запізнення"
    if any(k in rs for k in ("price","charged","pin","menu","question","calculation")): return "Оплата / ціна / питання"
    return "Інше"
CTHEME_COLOR={"Відсутні / неправильні позиції":"#7c3aed","Якість їжі / товару":"#16a34a",
 "Не доставлено":"#991b1b","Проблеми з курʼєром":"#0891b2","Довге очікування / запізнення":"#ea580c",
 "Оплата / ціна / питання":"#2563eb","Інше":"#9ca3af"}
comp=collections.defaultdict(int)
for r in ba:
    rs=(r["reason"] or "")
    if "eater" in rs.lower():
        comp[ctheme(rs)]+=i(r["n"])
CTOT=sum(comp.values()) or 1
comp_tbl=""
for t,n in sorted(comp.items(),key=lambda kv:-kv[1]):
    comp_tbl+=f'<tr><td><span class="dot" style="background:{CTHEME_COLOR.get(t,"#9ca3af")}"></span> {t}</td><td class="num"><b>{n:,}</b></td><td class="num">{n/CTOT*100:.0f}%</td></tr>'.replace(",", " ")
# per-partner tickets (complaints)
ctop=sorted(btot.items(), key=lambda kv:-kv[1][2])[:15]
comprows=""
for idx,(g,v) in enumerate(ctop):
    dl,bd,tk=v; tr_=tk/dl*100 if dl else 0
    tbadge='badge-r' if tr_>=6 else ('badge-y' if tr_>=3 else 'badge-g')
    comprows+=f'<tr><td>{medals[idx]} <b>{g}</b></td><td class="num">{dl:,}</td><td class="num"><b>{tk:,}</b></td><td class="num"><span class="badge {tbadge}">{tr_:.1f}%</span></td></tr>'.replace(",", " ")
C_del=sum(v[0] for _,v in ctop); C_tic=sum(v[2] for _,v in ctop)
comptotals=f'<tr style="background:#1A1A2E"><td style="color:#fff;font-weight:700">РАЗОМ топ-15</td><td class="num" style="color:#fff;font-weight:700">{C_del:,}</td><td class="num" style="color:#fff;font-weight:700">{C_tic:,}</td><td class="num"><span class="badge badge-r">{C_tic/C_del*100:.1f}%</span></td></tr>'.replace(",", " ")

# ================= SMB PARTNERS (all, operational metrics) =================
_meta_list=d.get("meta",[])
smb_names={m["grp"] for m in _meta_list if (m.get("seg") or "").lower().find("smb")>=0}
meta_by={m["grp"]:m for m in _meta_list}
_smb_total_in_base=sum(1 for m in _meta_list if (m.get("seg") or "").lower().find("smb")>=0)
p_tot=collections.defaultdict(lambda:[0,0,0,0.0,0.0])   # created, delivered, failed, deliv_gmv, lost_gmv
for r in wt:
    g=r["grp"] or "—"
    p_tot[g][0]+=i(r["total"]); p_tot[g][1]+=i(r["delivered"]); p_tot[g][2]+=i(r["failed"])
    p_tot[g][3]+=num(r.get("deliv_gmv")); p_tot[g][4]+=num(r.get("lost_gmv"))
p_bad=collections.defaultdict(lambda:[0,0,0,0,0])       # delivered_b, bad, tickets, late10, lowrate
for r in bw:
    g=r["grp"] or "—"
    p_bad[g][0]+=i(r["delivered"]); p_bad[g][1]+=i(r["bad"]); p_bad[g][2]+=i(r["tickets"])
    p_bad[g][3]+=i(r["late10"]); p_bad[g][4]+=i(r["lowrate"])
p_reason=collections.defaultdict(lambda:collections.defaultdict(int))
for r in wr:
    if (r["grp"] or "—") in smb_names:
        p_reason[r["grp"] or "—"][r["reason"]]+=i(r["n"])

smb_list=sorted([g for g in smb_names if p_tot[g][0]>0], key=lambda g:-p_tot[g][0])
# SMB aggregate KPIs
S_created=sum(p_tot[g][0] for g in smb_list); S_deliv=sum(p_tot[g][1] for g in smb_list)
S_failed=sum(p_tot[g][2] for g in smb_list); S_gmv=sum(p_tot[g][3] for g in smb_list)
S_lost=sum(p_tot[g][4] for g in smb_list)
S_bad=sum(p_bad[g][1] for g in smb_list); S_bdeliv=sum(p_bad[g][0] for g in smb_list)
S_tic=sum(p_bad[g][2] for g in smb_list); S_late=sum(p_bad[g][3] for g in smb_list)
_sset=set(smb_list)
smb_act=sum(num(r.get("active_time")) for r in d.get("availability",[]) if r["grp"] in _sset)
smb_wrk=sum(num(r.get("working_time")) for r in d.get("availability",[]) if r["grp"] in _sset)
S_avail=smb_act/smb_wrk*100 if smb_wrk else 0
smb_accv=sum(num(r.get("acc_v")) for r in d.get("acceptance",[]) if r["grp"] in _sset)
smb_accw=sum(num(r.get("acc_w")) for r in d.get("acceptance",[]) if r["grp"] in _sset)
S_acc=smb_accv/smb_accw*100 if smb_accw else 0

def pct(a,b): return a/b*100 if b else 0
def badge_for(v,warn,crit):
    return 'badge-r' if v>=crit else ('badge-y' if v>=warn else 'badge-g')
def badge_hi(v,good,bad):
    return 'badge-g' if v>=good else ('badge-r' if v<bad else 'badge-y')

# availability & acceptance per partner
avail_by={}
for r in d.get("availability",[]):
    act=num(r.get("active_time")); wrk=num(r.get("working_time"))
    avail_by[r["grp"]] = act/wrk*100 if wrk else None
acc_by={}
for r in d.get("acceptance",[]):
    v=num(r.get("acc_v")); w=num(r.get("acc_w"))
    acc_by[r["grp"]] = v/w*100 if w else None

smb_rows=""
for g in smb_list:
    cr,dl,fl,dgmv,lgmv=p_tot[g]
    bdl,bd,tk,lt,lw=p_bad[g]
    fr=pct(fl,cr); br=pct(bd,bdl); tr_=pct(tk,bdl); ltr=pct(lt,bdl)
    aov=dgmv/dl if dl else 0
    dom=max(p_reason[g],key=p_reason[g].get) if p_reason[g] else "—"
    m=meta_by.get(g,{}); am=(m.get("am") or "").strip() or "—"; stores_n=i(m.get("stores"))
    av=avail_by.get(g); ac=acc_by.get(g)
    av_cell=(f'<span class="badge {badge_hi(av,85,70)}">{av:.0f}%</span>' if av is not None else '<span style="color:#cbd5e1">—</span>')
    ac_cell=(f'<span class="badge {badge_hi(ac,95,85)}">{ac:.0f}%</span>' if ac is not None else '<span style="color:#cbd5e1">—</span>')
    av_v=(f"{av:.2f}" if av is not None else "-1"); ac_v=(f"{ac:.2f}" if ac is not None else "-1")
    smb_rows+=(f'<tr>'
      f'<td data-v="{g}"><b>{g}</b></td>'
      f'<td class="num" data-v="{dgmv:.0f}"><b>€{dgmv:,.0f}</b></td>'
      f'<td class="num" data-v="{ac_v}">{ac_cell}</td>'
      f'<td class="num" data-v="{av_v}">{av_cell}</td>'
      f'<td data-v="{am}" style="font-size:11px;color:#6b7280">{am}</td>'
      f'<td class="num" data-v="{stores_n}">{stores_n}</td>'
      f'<td class="num" data-v="{cr}">{cr:,}</td>'
      f'<td class="num" data-v="{dl}">{dl:,}</td>'
      f'<td class="num" data-v="{fr:.2f}"><span class="badge {badge_for(fr,7,12)}">{fr:.1f}%</span></td>'
      f'<td class="num" data-v="{br:.2f}"><span class="badge {badge_for(br,8,12)}">{br:.1f}%</span></td>'
      f'<td class="num" data-v="{tr_:.2f}"><span class="badge {badge_for(tr_,3,6)}">{tr_:.1f}%</span></td>'
      f'<td class="num" data-v="{ltr:.2f}">{ltr:.1f}%</td>'
      f'<td class="num" data-v="{aov:.2f}">€{aov:.1f}</td>'
      f'<td class="num" data-v="{lgmv:.0f}" style="color:#991b1b">€{lgmv:,.0f}</td>'
      f'<td style="font-size:11px">{dom}</td>'
      f'</tr>').replace(",", " ")

# chart data
import json as _j
JS = {
  "weeks": wlabels,
  "bad_actor_labels":[ACTOR_LABEL[a] for a in actor_order],
  "bad_actor_data":[actor[a] for a in actor_order],
  "bad_actor_colors":[ACTOR_COLOR[a] for a in actor_order],
  "bad_actor_week":[[awk[a].get(w,0) for w in weeks] for a in actor_order],
  "ow_bad":ow_bad, "ow_badrate":ow_badrate, "ow_tic":ow_tic, "ow_ticrate":ow_ticrate,
  "comp_labels":[t for t,_ in sorted(comp.items(),key=lambda kv:-kv[1])],
  "comp_data":[n for _,n in sorted(comp.items(),key=lambda kv:-kv[1])],
  "comp_colors":[CTHEME_COLOR.get(t,"#9ca3af") for t,_ in sorted(comp.items(),key=lambda kv:-kv[1])],
  "ow_failed": ow_failed, "ow_rate": ow_rate, "ow_lost": ow_lost,
  "reasons": REASONS,
  "rcolors": [RCOLOR[r] for r in REASONS],
  "rtot": [rtot.get(r,0) for r in REASONS],
  "rweek": [[rweek[r].get(w,0) for w in weeks] for r in REASONS],
}

def fmt(n): return f"{n:,}".replace(",", " ")

HTML = f"""<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bolt Food UA — Failed Orders: тижневий розбір топ-15 партнерів</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js"></script>
<style>
:root{{--bg:#F8F9FA;--card:#fff;--border:#e5e7eb;--text:#1A1A2E;--muted:#6b7280;--green:#34D186;--red:#dc2626;--yellow:#ca8a04;--blue:#2563eb;--purple:#7c3aed;--orange:#ea580c;--accent:#34D186;--accent-dark:#1A1A2E}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--bg);color:var(--text);font-family:'Inter',-apple-system,system-ui,sans-serif;line-height:1.65}}
.container{{max-width:1240px;margin:0 auto;padding:28px}}
.header{{display:flex;align-items:center;gap:20px;margin-bottom:32px;padding-bottom:24px;border-bottom:2px solid var(--border)}}
.logo-dot{{width:44px;height:44px;border-radius:10px;background:linear-gradient(135deg,#dc2626,#1A1A2E);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:800;font-size:18px}}
h1{{font-size:24px;font-weight:700;color:var(--accent-dark)}}
.subtitle{{color:var(--muted);font-size:13px;margin-top:2px}}
.report-meta{{margin-left:auto;text-align:right;color:var(--muted);font-size:12px}}
.btn-pdf{{display:inline-flex;align-items:center;gap:7px;background:var(--accent-dark);color:#fff;border:none;border-radius:8px;padding:10px 18px;font-size:13px;font-weight:600;cursor:pointer;transition:opacity .2s;margin-top:8px}}
.btn-pdf:hover{{opacity:.85}} .btn-pdf svg{{width:15px;height:15px}}
h2{{font-size:18px;font-weight:700;margin-bottom:16px;padding-bottom:8px;border-bottom:1px solid var(--border);color:var(--accent-dark)}}
h3{{font-size:14px;font-weight:600;margin-bottom:10px}}
.section{{margin-bottom:36px}}
.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
.grid-3{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}}
.grid-4{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:18px;box-shadow:0 1px 3px rgba(0,0,0,0.04)}}
.kpi{{text-align:center;padding:16px 12px}}
.kpi-label{{font-size:11px;color:var(--muted);text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px;line-height:1.3}}
.kpi-value{{font-size:26px;font-weight:700}}
.kpi-sub{{font-size:11px;margin-top:4px;font-weight:600}}
.up{{color:var(--green)}}.down{{color:var(--red)}}.neutral{{color:var(--yellow)}}.stable{{color:var(--muted)}}
.chart-box{{position:relative;height:300px}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th{{text-align:left;padding:8px 10px;border-bottom:2px solid var(--border);color:var(--muted);font-weight:600;font-size:10px;text-transform:uppercase;letter-spacing:.4px;white-space:nowrap}}
td{{padding:8px 10px;border-bottom:1px solid #f3f4f6}}
tr:hover{{background:#f9fafb}}
.num{{text-align:right;font-variant-numeric:tabular-nums}}
.badge{{display:inline-block;padding:2px 9px;border-radius:99px;font-size:10px;font-weight:700}}
.badge-g{{background:#dcfce7;color:#166534}}.badge-r{{background:#fee2e2;color:#991b1b}}.badge-y{{background:#fef9c3;color:#854d0e}}.badge-b{{background:#dbeafe;color:#1e40af}}
.cell-crit{{background:#fee2e2!important;color:#991b1b;font-weight:700}}
.cell-warn{{background:#fef9c3!important;color:#854d0e;font-weight:600}}
.cell-good{{background:#dcfce7!important;color:#166534}}
.insight{{border-left:3px solid var(--blue);background:#eff6ff;border-radius:0 8px 8px 0;padding:12px 16px;margin-bottom:10px;font-size:13px}}
.insight.warn{{border-color:var(--orange);background:#fff7ed}}
.insight.good{{border-color:var(--green);background:#f0fdf4}}
.insight.action{{border-color:var(--purple);background:#f5f3ff}}
.insight.crit{{border-color:var(--red);background:#fef2f2}}
.insight-title{{font-weight:700;margin-bottom:3px}}
.insight-text{{color:#374151;font-size:12.5px}}
.store-row{{display:flex;align-items:center;gap:8px;margin-bottom:6px}}
.store-name{{font-size:11px;min-width:210px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.bar-bg{{flex:1;height:20px;background:#f3f4f6;border-radius:3px;overflow:hidden;position:relative}}
.bar-fill{{height:100%;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;color:#fff}}
.legend{{display:flex;gap:16px;flex-wrap:wrap;font-size:11px;color:var(--muted);margin-top:12px}}
.legend span{{display:inline-flex;align-items:center;gap:5px}}
.dot{{width:10px;height:10px;border-radius:3px;display:inline-block}}
.method{{background:#0f172a;color:#e2e8f0;border-radius:10px;padding:20px 22px;font-size:12.5px}}
.method code{{background:#1e293b;color:#7dd3fc;padding:1px 6px;border-radius:4px;font-size:11.5px}}
.method h3{{color:#fff}} .method b{{color:#fff}}
.tabs{{display:flex;gap:6px;margin-bottom:26px;border-bottom:2px solid var(--border);flex-wrap:wrap}}
.tab{{appearance:none;background:none;border:none;padding:12px 20px;font-size:14px;font-weight:600;color:var(--muted);cursor:pointer;border-bottom:3px solid transparent;margin-bottom:-2px;font-family:inherit;display:flex;align-items:center;gap:8px}}
.tab:hover{{color:var(--text)}}
.tab.active{{color:var(--accent-dark);border-bottom-color:var(--red)}}
.tab .cnt{{font-size:11px;font-weight:700;background:#f1f5f9;color:#475569;border-radius:99px;padding:2px 8px}}
.tab.active .cnt{{background:#fee2e2;color:#991b1b}}
.tabpane{{display:none}}
.tabpane.active{{display:block}}
table.sortable th{{cursor:pointer;user-select:none}}
table.sortable th:hover{{color:var(--text)}}
@media(max-width:900px){{.grid-2,.grid-3,.grid-4{{grid-template-columns:1fr}}}}
@media print{{body{{background:#fff}}.card{{box-shadow:none}}.btn-pdf{{display:none}}.tab{{display:none}}.tabpane{{display:block!important}}}}
</style>
</head>
<body>
<div class="container" id="report">

<div class="header">
  <div class="logo-dot">✕</div>
  <div>
    <h1>Orders Health — тижневий розбір</h1>
    <div class="subtitle">Bolt Food UA · Stores · Failed · Bad orders · Скарги · топ-15 партнерів, причини та тижнева динаміка</div>
  </div>
  <div class="report-meta">
    Період: 01.05 – 30.06.2026 (10 тижнів, 2 часткові)<br>
    Джерело: Databricks · <code>fact_order_delivery</code><br>
    Сформовано: 14.07.2026
    <br>
    <button class="btn-pdf" onclick="downloadPDF()">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 3v12m0 0l-4-4m4 4l4-4M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2"/></svg>
      Завантажити PDF
    </button>
  </div>
</div>

<div class="tabs">
  <button class="tab active" id="tab-failed" onclick="showTab('failed')">✕ Failed ордери <span class="cnt">{fmt(F)}</span></button>
  <button class="tab" id="tab-bad" onclick="showTab('bad')">⚠ Bad orders <span class="cnt">{fmt(BAD)}</span></button>
  <button class="tab" id="tab-comp" onclick="showTab('comp')">💬 Скарги <span class="cnt">{fmt(TIC)}</span></button>
  <button class="tab" id="tab-smb" onclick="showTab('smb')">🏪 SMB партнери <span class="cnt">{len(smb_list)}</span></button>
</div>

<div class="tabpane active" id="pane-failed">

<!-- VERDICT -->
<div class="section">
  <div class="insight crit">
    <div class="insight-title">Головний висновок: половина втрачених замовлень — на боці партнера</div>
    <div class="insight-text">За 01.05–30.06.2026 по UA Stores впало <b>{fmt(F)} замовлень</b> ({F/G*100:.1f}% від {fmt(G)} створених). У топ-15 партнерів <b>{prov_share:.0f}% усіх фейлів — партнерська провина</b> (не відповіли за 5 хв / відхилили / не прийняли), і лише решта — кур'єр, клієнт або система. Найгостріша точка — <b>BEER MARKET</b> ({fmt(tot['BEER MARKET'][2])} фейлів, {tot['BEER MARKET'][2]/tot['BEER MARKET'][0]*100:.1f}%) та <b>ANRI-PHARM</b> ({tot.get('ANRI-PHARM',[0,0,0])[2]/max(tot.get('ANRI-PHARM',[1])[0],1)*100:.0f}% fail-rate).</div>
  </div>
</div>

<!-- KPI -->
<div class="section">
  <div class="grid-4">
    <div class="card kpi"><div class="kpi-label">Failed ордери (UA stores)</div><div class="kpi-value">{fmt(F)}</div><div class="kpi-sub down">{F/G*100:.1f}% fail-rate</div></div>
    <div class="card kpi"><div class="kpi-label">Втрачений GMV (орієнтовно)</div><div class="kpi-value" style="color:#991b1b">€{GMV_LOST/1000:.1f}k</div><div class="kpi-sub down">{GMV_LOST/(GMV_DELIV+GMV_LOST)*100:.1f}% від потенц. GMV</div></div>
    <div class="card kpi"><div class="kpi-label">Партнерська провина (топ-15)</div><div class="kpi-value">{prov_share:.0f}%</div><div class="kpi-sub down">не відповіли / відхилили</div></div>
    <div class="card kpi"><div class="kpi-label">Найгірший партнер</div><div class="kpi-value" style="font-size:20px">BEER MARKET</div><div class="kpi-sub down">{tot['BEER MARKET'][2]/tot['BEER MARKET'][0]*100:.1f}% · €{gmv['BEER MARKET'][1]/1000:.1f}k</div></div>
  </div>
</div>

<!-- REASON EXPLANATIONS -->
<div class="section">
  <h2>1. Що означає кожна причина</h2>
  <div class="insight" style="margin-bottom:14px">
    <div class="insight-title">Спершу: чим «rejected» відрізняється від «failed»</div>
    <div class="insight-text"><b>rejected</b> — партнер <b>жодного разу не прийняв</b> замовлення (відхилив або не встиг за 5 хв → Bolt авто-скасовує). <b>failed</b> — замовлення зламалося <b>здебільшого вже ПІСЛЯ прийняття партнером</b> (≈87% failed-ордерів були прийняті, а потім впали через кур'єра, скасування клієнта чи оплату). Нижче — 6 взаємовиключних причин, до яких ми звели обидва стани.</div>
  </div>
  <div class="grid-3">
    {explain_html}
  </div>
</div>

<!-- TREND -->
<div class="section">
  <h2>2. Динаміка по тижнях (уся мережа UA Stores)</h2>
  <div class="grid-2">
    <div class="card">
      <h3>Failed-ордери та fail-rate по тижнях</h3>
      <div class="chart-box"><canvas id="chartTrend"></canvas></div>
    </div>
    <div class="card">
      <h3>Структура причин по тижнях (топ-15 партнерів)</h3>
      <div class="chart-box"><canvas id="chartReasonWeek"></canvas></div>
      <div class="legend">{legend_html}</div>
    </div>
  </div>
</div>

<!-- TOP10 TABLE -->
<div class="section">
  <h2>3. Топ-15 партнерів за кількістю failed-ордерів</h2>
  <div class="card">
    <table>
      <thead><tr><th>Партнер</th><th class="num">Створено</th><th class="num">Failed</th><th class="num">Fail-rate</th><th class="num">Втрач. GMV</th><th class="num">Тренд (перш.→ост. тижд.)</th><th>Домінуюча причина</th></tr></thead>
      <tbody>{totals_row}{rows_html}</tbody>
    </table>
  </div>
</div>

<!-- LOST GMV -->
<div class="section">
  <h2>4. Скільки GMV втрачено</h2>
  <div class="insight warn" style="margin-bottom:14px">
    <div class="insight-title">≈ €{GMV_LOST:,.0f} втраченого GMV за 2 місяці</div>
    <div class="insight-text">Кожен failed/rejected ордер несе свою вартість кошика (<code>order_gmv_eur</code>), тому це <b>пряма оцінка</b>, а не проєкція. Разом по UA Stores впало <b>€{GMV_LOST:,.0f}</b> — це <b>{GMV_LOST/(GMV_DELIV+GMV_LOST)*100:.1f}%</b> від потенційного GMV (доставлено €{GMV_DELIV:,.0f}). З них у топ-15 — €{GMV_LOST_TOP:,.0f}, а <b>€{lost_partner:,.0f} ({lost_partner/GMV_LOST_TOP*100:.0f}%) — через партнерські причини</b> (найбільш «поверненна» частина, якщо полагодити прийняття замовлень).</div>
  </div>
  <div class="grid-3" style="margin-bottom:16px">
    <div class="card kpi"><div class="kpi-label">Втрачено GMV, усього</div><div class="kpi-value" style="color:#991b1b">€{GMV_LOST/1000:.1f}k</div><div class="kpi-sub down">{GMV_LOST/(GMV_DELIV+GMV_LOST)*100:.1f}% від потенц.</div></div>
    <div class="card kpi"><div class="kpi-label">Партнерські причини (топ-15)</div><div class="kpi-value" style="color:#ea580c">€{lost_partner/1000:.1f}k</div><div class="kpi-sub neutral">{lost_partner/GMV_LOST_TOP*100:.0f}% — потенційно поверненно</div></div>
    <div class="card kpi"><div class="kpi-label">У середньому за тиждень</div><div class="kpi-value">€{GMV_LOST/len(weeks)/1000:.1f}k</div><div class="kpi-sub stable">по {len(weeks)} тижнях</div></div>
  </div>
  <div class="grid-2">
    <div class="card">
      <h3>Втрачений GMV по тижнях, €</h3>
      <div class="chart-box"><canvas id="chartLost"></canvas></div>
    </div>
    <div class="card">
      <h3>Втрачений GMV за причиною (топ-15)</h3>
      <table>
        <thead><tr><th>Причина</th><th>Хто</th><th class="num">Втрач. GMV</th><th class="num">Частка</th></tr></thead>
        <tbody>{rgmv_html}</tbody>
      </table>
      <h3 style="margin-top:16px">Топ-8 партнерів за втраченим GMV</h3>
      <table>
        <thead><tr><th>Партнер</th><th class="num">Failed</th><th class="num">Втрач. GMV</th><th class="num">% від усіх втрат</th></tr></thead>
        <tbody>{toplost_html}</tbody>
      </table>
    </div>
  </div>
</div>

<!-- REASON MIX + HEATMAP -->
<div class="section">
  <h2>5. Причини фейлів та тижнева теплокарта</h2>
  <div class="grid-2">
    <div class="card">
      <h3>Розподіл причин (топ-15, {fmt(TF)} фейлів)</h3>
      <div class="chart-box"><canvas id="chartReasonMix"></canvas></div>
    </div>
    <div class="card">
      <h3>Fail-rate по тижнях, % (теплокарта)</h3>
      <div style="overflow-x:auto">
      <table>
        <thead><tr><th>Партнер</th>{"".join(f'<th class="num">{w}</th>' for w in wlabels)}</tr></thead>
        <tbody>{heat_html}</tbody>
      </table>
      </div>
      <div class="legend"><span><span class="dot" style="background:#dcfce7"></span>&lt;6% ок</span><span><span class="dot" style="background:#fef9c3"></span>6–10% увага</span><span><span class="dot" style="background:#fee2e2"></span>&ge;10% критично / &ge;20%</span></div>
    </div>
  </div>
</div>

<!-- PER PARTNER REASON -->
<div class="section">
  <h2>6. Структура причин по кожному партнеру</h2>
  <div class="card">
    {pbar_html}
    <div class="legend">{legend_html}</div>
  </div>
</div>

<!-- WHAT HAPPENED -->
<div class="section">
  <h2>7. Що трапилось — розбір за тижнями</h2>
  <div class="grid-2">
    <div class="insight crit">
      <div class="insight-title">BEER MARKET — системний партнерський фейл</div>
      <div class="insight-text">{fmt(tot['BEER MARKET'][2])} фейлів, fail-rate тримається <b>15–20%</b> весь період з піком у червні (19,8% на 08.06). Домінує <b>{dom_reason('BEER MARKET')[0]}</b> ({dom_reason('BEER MARKET')[1]:.0f}%). Це не разовий збій, а хронічна неприйнятність замовлень — потрібен розбір режиму роботи точок і налаштувань auto-accept.</div>
    </div>
    <div class="insight warn">
      <div class="insight-title">ANRI-PHARM — провал онбордингу</div>
      <div class="insight-text">Стартував тижнем 18.05 з <b>55% fail-rate</b>, поступово знизився до ~20%. Класична крива нового/погано інтегрованого партнера: перші тижні — партнер не встигає приймати. Тренд позитивний, але рівень усе ще критичний.</div>
    </div>
    <div class="insight good">
      <div class="insight-title">VARUS — під контролем, покращення</div>
      <div class="insight-text">Найбільший за обсягом ({fmt(tot['VARUS'][0])} замовлень), але fail-rate помірний ({tot['VARUS'][2]/tot['VARUS'][0]*100:.1f}%) і <b>знизився</b> з 7,8% до 5,5%. Абсолютна кількість фейлів велика через масштаб, а не через якість.</div>
    </div>
    <div class="insight warn">
      <div class="insight-title">Малі точки з екстремальним fail-rate</div>
      <div class="insight-text">Кілька дрібних за обсягом партнерів дають <b>40–60% fail-rate</b> (напр. VAPERY | VAPE SHOP ~59%, RODYNNA KOVBASKA ~47%). Абсолют невеликий, але це майже непрацюючі точки — кандидати на паузу/деактивацію або терміновий розбір режиму роботи.</div>
    </div>
    <div class="insight action">
      <div class="insight-title">Куди дивитись далі</div>
      <div class="insight-text">{prov_share:.0f}% фейлів топ-15 — партнерські. Пріоритет: (1) BEER MARKET, ANRI-PHARM, PYVNA BORODA, RUKAVYCHKA, BEERLAND — fail-rate &gt;10%; (2) увімкнути/перевірити <b>auto-accept</b> та години роботи; (3) алерти на партнерів з тайм-аутом прийняття (5-хв правило); (4) окремо — платіжні фейли в категорії «Система / оплата».</div>
    </div>
  </div>
</div>

<!-- STORES -->
<div class="section">
  <h2>8. Топ точок-порушників (у межах топ-15 партнерів)</h2>
  <div class="card">
    <table>
      <thead><tr><th>Партнер</th><th>Точка</th><th>Місто</th><th class="num">Створено</th><th class="num">Failed</th><th class="num">Fail-rate</th></tr></thead>
      <tbody>{store_html}</tbody>
    </table>
  </div>
</div>

<!-- METHOD -->
<div class="section">
  <h2>9. Методологія та пояснення розрахунку (dbx)</h2>
  <div class="method">
    <h3>Джерело даних</h3>
    <p>Databricks (профіль <code>bolt-common</code>), таблиця фактів замовлень <code>main.ng_delivery.fact_order_delivery</code>, зджойнена з <code>dim_provider_v2</code> по <code>provider_id</code>. Фільтр: <code>country_code='ua'</code>, <code>delivery_vertical LIKE 'store%'</code>, період <code>order_created_date</code> 11.05–12.07.2026.</p>
    <h3 style="margin-top:14px">Що вважаємо "failed"</h3>
    <p><b>Failed order = </b><code>order_state IN ('failed','rejected')</code>. Знаменник fail-rate = усі створені замовлення (<code>delivered + failed + rejected</code> + рідкісні waiting).</p>
    <h3 style="margin-top:14px">Втрачений GMV</h3>
    <p><b>Lost GMV = </b><code>SUM(order_gmv_eur)</code> по рядках зі станом failed/rejected. Поле заповнене на 100% таких рядків (це вартість кошика на момент оформлення), тому оцінка пряма. Крос-валідація через <code>failed_cnt × AOV</code> партнера дала розбіжність &lt;5%. «Партнерські причини» = сума GMV по причинах відхилив / не відповів / не прийняв — найбільш поверненна частина.</p>
    <h3 style="margin-top:14px">Класифікація причин (пріоритетна, взаємовиключна)</h3>
    <p>У таблиці немає текстового поля причини, тому причина реконструйована з булевих прапорців у пріоритеті зверху вниз:</p>
    <p>1. <code>is_rejected_by_provider</code> → <b>Партнер відхилив</b><br>
    2. <code>is_not_responded_by_provider</code> → <b>Партнер не відповів (тайм-аут)</b><br>
    3. <code>is_order_not_accepted_by_provider</code> → <b>Партнер не прийняв (інше)</b><br>
    4. <code>has_eater_cancellation_ticket</code> → <b>Клієнт скасував</b><br>
    5. <code>number_courier_rejects &gt; 0</code> → <b>Проблема з курʼєром</b><br>
    6. інакше → <b>Система / оплата / інше</b></p>
    <p style="margin-top:10px;color:#94a3b8">Тижні — <code>DATE_TRUNC('week', order_created_date)</code> (Пн–Нд). Крайові тижні 27.04 (лише 01–03.05) та 29.06 (лише 29–30.06) часткові. Партнер = <code>COALESCE(group_name, brand_name)</code>. Топ-15 обрано за абсолютною кількістю failed-ордерів.</p>
  </div>
</div>

</div><!-- /pane-failed -->

<!-- ============ BAD ORDERS TAB ============ -->
<div class="tabpane" id="pane-bad">
  <div class="section">
    <div class="insight warn">
      <div class="insight-title">Bad orders: {bad_rate:.1f}% доставлених замовлень «зіпсовані» — і в {actor['provider']/BATT*100:.0f}% випадків винен партнер</div>
      <div class="insight-text">Bad order — це <b>доставлене</b> замовлення, яке пішло не так (переважно <b>запізнення</b>, а також out-of-stock, відсутні позиції, якість). За період таких <b>{fmt(BAD)} з {fmt(DEL_B)}</b> ({bad_rate:.1f}%). Головна причина — <b>запізнення/довга доставка ({th['Запізнення / довга доставка']/TTH*100:.0f}%)</b>. За винуватцем: партнер {actor['provider']/BATT*100:.0f}%, курʼєр {actor['courier']/BATT*100:.0f}%, ліквідність {actor['supply']/BATT*100:.0f}%.</div>
    </div>
  </div>
  <div class="section">
    <div class="grid-4">
      <div class="card kpi"><div class="kpi-label">Bad orders</div><div class="kpi-value" style="color:#ea580c">{fmt(BAD)}</div><div class="kpi-sub down">{bad_rate:.1f}% доставлених</div></div>
      <div class="card kpi"><div class="kpi-label">Запізнення &gt;10 хв</div><div class="kpi-value">{fmt(LATE10)}</div><div class="kpi-sub neutral">{late_rate:.1f}% доставлених</div></div>
      <div class="card kpi"><div class="kpi-label">Провина партнера</div><div class="kpi-value">{actor['provider']/BATT*100:.0f}%</div><div class="kpi-sub down">{fmt(actor['provider'])} bad-ордерів</div></div>
      <div class="card kpi"><div class="kpi-label">Низькі оцінки їжі (&le;3)</div><div class="kpi-value">{fmt(LOW)}</div><div class="kpi-sub stable">за період</div></div>
    </div>
  </div>
  <div class="section">
    <h2>1. Хто винен та за що (attribution)</h2>
    <div class="grid-2">
      <div class="card"><h3>Винуватець bad-ордера</h3><div class="chart-box"><canvas id="chartActor"></canvas></div></div>
      <div class="card"><h3>Причини bad-ордерів (теми)</h3>
        <table><thead><tr><th>Причина</th><th class="num">К-сть</th><th class="num">Частка</th></tr></thead><tbody>{theme_tbl}</tbody></table>
      </div>
    </div>
  </div>
  <div class="section">
    <h2>2. Динаміка по тижнях</h2>
    <div class="grid-2">
      <div class="card"><h3>Bad-order rate та кількість по тижнях</h3><div class="chart-box"><canvas id="chartBadTrend"></canvas></div></div>
      <div class="card"><h3>Bad-ордери за винуватцем по тижнях</h3><div class="chart-box"><canvas id="chartActorWeek"></canvas></div></div>
    </div>
  </div>
  <div class="section">
    <h2>3. Топ-15 партнерів за bad-ордерами</h2>
    <div class="card">
      <table>
        <thead><tr><th>Партнер</th><th class="num">Доставлено</th><th class="num">Bad</th><th class="num">Bad-rate</th><th class="num">Скарги (тикети)</th><th class="num">Ticket-rate</th></tr></thead>
        <tbody>{badtotals}{badrows}</tbody>
      </table>
    </div>
  </div>
  <div class="section">
    <h2>4. Bad-order rate по тижнях, % (теплокарта)</h2>
    <div class="card"><div style="overflow-x:auto"><table>
      <thead><tr><th>Партнер</th>{"".join(f'<th class="num">{w}</th>' for w in wlabels)}</tr></thead>
      <tbody>{badheat}</tbody>
    </table></div>
    <div class="legend"><span><span class="dot" style="background:#dcfce7"></span>&lt;5%</span><span><span class="dot" style="background:#fef9c3"></span>8–12%</span><span><span class="dot" style="background:#fee2e2"></span>&ge;12%</span></div>
    </div>
  </div>
</div><!-- /pane-bad -->

<!-- ============ COMPLAINTS TAB ============ -->
<div class="tabpane" id="pane-comp">
  <div class="section">
    <div class="insight" style="border-color:#2563eb;background:#eff6ff">
      <div class="insight-title">Скарги: {fmt(TIC)} звернень у підтримку ({tic_rate:.1f}% доставлених)</div>
      <div class="insight-text">«Скарга» тут = замовлення зі зверненням у підтримку (<code>has_ticket</code>) + категорії, на що саме скаржаться клієнти (з attribution, eater-reported). Найчастіше клієнти скаржаться на <b>{sorted(comp.items(),key=lambda kv:-kv[1])[0][0] if comp else '—'}</b>. Додатково {fmt(LOW)} замовлень отримали <b>низьку оцінку їжі (&le;3)</b>.</div>
    </div>
  </div>
  <div class="section">
    <div class="grid-4">
      <div class="card kpi"><div class="kpi-label">Скарги (тикети)</div><div class="kpi-value" style="color:#2563eb">{fmt(TIC)}</div><div class="kpi-sub down">{tic_rate:.1f}% доставлених</div></div>
      <div class="card kpi"><div class="kpi-label">Категорій скарг (eater)</div><div class="kpi-value">{fmt(CTOT)}</div><div class="kpi-sub stable">issues attributed</div></div>
      <div class="card kpi"><div class="kpi-label">Низькі оцінки їжі</div><div class="kpi-value">{fmt(LOW)}</div><div class="kpi-sub neutral">рейтинг &le;3</div></div>
      <div class="card kpi"><div class="kpi-label">Запізнення &gt;10 хв</div><div class="kpi-value">{fmt(LATE10)}</div><div class="kpi-sub neutral">{late_rate:.1f}% доставлених</div></div>
    </div>
  </div>
  <div class="section">
    <h2>1. На що скаржаться клієнти</h2>
    <div class="grid-2">
      <div class="card"><h3>Категорії скарг (eater-reported)</h3><div class="chart-box"><canvas id="chartComp"></canvas></div></div>
      <div class="card"><h3>Деталізація</h3>
        <table><thead><tr><th>Категорія</th><th class="num">К-сть</th><th class="num">Частка</th></tr></thead><tbody>{comp_tbl}</tbody></table>
      </div>
    </div>
  </div>
  <div class="section">
    <h2>2. Скарги по тижнях</h2>
    <div class="card"><h3>Тикети та ticket-rate по тижнях</h3><div class="chart-box" style="height:280px"><canvas id="chartTicTrend"></canvas></div></div>
  </div>
  <div class="section">
    <h2>3. Топ-15 партнерів за скаргами</h2>
    <div class="card">
      <table>
        <thead><tr><th>Партнер</th><th class="num">Доставлено</th><th class="num">Скарги (тикети)</th><th class="num">Ticket-rate</th></tr></thead>
        <tbody>{comptotals}{comprows}</tbody>
      </table>
    </div>
  </div>
  <div class="section">
    <div class="method">
      <h3>Пояснення (dbx)</h3>
      <p><b>Bad order</b> = <code>fact_order_delivery.is_bad_order = true</code> серед доставлених. Атрибуція винуватця й причини — з таблиці <code>int_order_bad_order_attribution</code> (<code>bad_order_actor_at_fault</code>, <code>bad_order_main_reason</code>), зджойнена по <code>order_id</code>. Причини згруповано в теми.</p>
      <p style="margin-top:8px"><b>Скарга</b> = замовлення зі зверненням у підтримку <code>has_ticket = true</code>. Категорії скарг — з eater-reported причин attribution (<code>bad_order_main_reason LIKE '%eater%'</code>). Низька оцінка — <code>order_food_rating_value &le; 3</code>; запізнення — <code>is_order_delivered_10_min_late</code>.</p>
    </div>
  </div>
</div><!-- /pane-comp -->

<!-- ============ SMB PARTNERS TAB ============ -->
<div class="tabpane" id="pane-smb">
  <div class="section">
    <div class="insight" style="border-color:#0891b2;background:#ecfeff">
      <div class="insight-title">Усі SMB-партнери з операційними метриками</div>
      <div class="insight-text">Повний список <b>{len(smb_list)} SMB-партнерів</b> (сегмент <code>SMB (AM Segment)</code>), які мали замовлення за 01.05–30.06.2026 (з {_smb_total_in_base} SMB-партнерів у базі). Таблицю можна <b>сортувати</b> (клік на заголовок) та <b>шукати</b> за назвою. Метрики: обсяг, <b>availability</b> (частка часу онлайн), <b>acceptance</b> (частка прийнятих замовлень), fail-rate, bad-rate, скарги, запізнення, AOV, GMV, втрачений GMV, домінуюча причина фейлів.</div>
    </div>
  </div>
  <div class="section">
    <div class="grid-3">
      <div class="card kpi"><div class="kpi-label">SMB-партнерів (з замовл.)</div><div class="kpi-value">{len(smb_list)}</div><div class="kpi-sub stable">{sum(p_tot[g][1] for g in smb_list):,} доставлених</div></div>
      <div class="card kpi"><div class="kpi-label">Availability (SMB)</div><div class="kpi-value" style="color:{'#16a34a' if S_avail>=85 else ('#ca8a04' if S_avail>=70 else '#dc2626')}">{S_avail:.0f}%</div><div class="kpi-sub stable">active / working time</div></div>
      <div class="card kpi"><div class="kpi-label">Acceptance (SMB)</div><div class="kpi-value" style="color:{'#16a34a' if S_acc>=95 else ('#ca8a04' if S_acc>=85 else '#dc2626')}">{S_acc:.0f}%</div><div class="kpi-sub stable">прийнято партнером</div></div>
      <div class="card kpi"><div class="kpi-label">Fail-rate (SMB)</div><div class="kpi-value" style="color:#dc2626">{pct(S_failed,S_created):.1f}%</div><div class="kpi-sub down">{S_failed:,} фейлів</div></div>
      <div class="card kpi"><div class="kpi-label">Bad-rate / Скарги (SMB)</div><div class="kpi-value" style="color:#ea580c">{pct(S_bad,S_bdeliv):.1f}%</div><div class="kpi-sub neutral">скарги {pct(S_tic,S_bdeliv):.1f}%</div></div>
      <div class="card kpi"><div class="kpi-label">GMV / Втрачено (SMB)</div><div class="kpi-value">€{S_gmv/1000:.0f}k</div><div class="kpi-sub down">втрачено €{S_lost/1000:.1f}k</div></div>
    </div>
  </div>
  <div class="section">
    <h2>Операційні метрики по кожному SMB-партнеру</h2>
    <div class="card">
      <input id="smbSearch" onkeyup="filterSMB()" placeholder="🔍 Пошук партнера…" style="width:100%;padding:10px 12px;margin-bottom:12px;border:1px solid var(--border);border-radius:8px;font-size:13px;font-family:inherit">
      <div style="overflow-x:auto">
      <table class="sortable" id="smbTable">
        <thead><tr>
          <th onclick="sortSMB(0,'s')">Партнер ▲▼</th>
          <th class="num" onclick="sortSMB(1,'n')">GMV</th>
          <th class="num" onclick="sortSMB(2,'n')">Acceptance</th>
          <th class="num" onclick="sortSMB(3,'n')">Availability</th>
          <th onclick="sortSMB(4,'s')">AM</th>
          <th class="num" onclick="sortSMB(5,'n')">Точки</th>
          <th class="num" onclick="sortSMB(6,'n')">Замовл.</th>
          <th class="num" onclick="sortSMB(7,'n')">Достав.</th>
          <th class="num" onclick="sortSMB(8,'n')">Fail-rate</th>
          <th class="num" onclick="sortSMB(9,'n')">Bad-rate</th>
          <th class="num" onclick="sortSMB(10,'n')">Скарги</th>
          <th class="num" onclick="sortSMB(11,'n')">Late&gt;10хв</th>
          <th class="num" onclick="sortSMB(12,'n')">AOV</th>
          <th class="num" onclick="sortSMB(13,'n')">Втрач.GMV</th>
          <th onclick="sortSMB(14,'s')">Дом. причина фейлів</th>
        </tr></thead>
        <tbody>{smb_rows}</tbody>
      </table>
      </div>
      <div style="font-size:11px;color:#9ca3af;margin-top:8px">Клік на заголовок — сортування. Fail/Bad/Скарги: зелений — ок, жовтий — увага, червоний — критично. <b>Availability</b> = active/working time (<code>etl_delivery_provider_daily_availability</code>); <b>Acceptance</b> = <code>provider_acceptance_rate</code> (<code>fact_provider_weekly</code>); для availability/acceptance зелений = високий (добре). «—» — немає даних за період.</div>
    </div>
  </div>
</div><!-- /pane-smb -->

<div style="text-align:center;color:#9ca3af;font-size:11px;margin-top:24px">Bolt Food UA · Orders Health (Failed · Bad · Скарги · SMB) · дані з Databricks за 01.05–30.06.2026</div>

</div>

<script>
const D={_j.dumps(JS, ensure_ascii=False)};
const gridc='#eef1f4';
const pctY={{grid:{{drawOnChartArea:false}},position:'right',title:{{display:true,text:'%'}}}};
const built={{}};

function buildFailed(){{
  new Chart(document.getElementById('chartTrend'),{{
    data:{{labels:D.weeks,datasets:[
      {{type:'bar',label:'Failed ордери',data:D.ow_failed,backgroundColor:'#fca5a5',yAxisID:'y',order:2}},
      {{type:'line',label:'Fail-rate %',data:D.ow_rate,borderColor:'#dc2626',backgroundColor:'#dc2626',tension:.3,yAxisID:'y1',order:1,pointRadius:3}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom'}}}},
      scales:{{y:{{position:'left',title:{{display:true,text:'ордери'}},grid:{{color:gridc}}}},
        y1:{{position:'right',title:{{display:true,text:'%'}},grid:{{drawOnChartArea:false}},suggestedMax:10}}}}}}
  }});
  new Chart(document.getElementById('chartLost'),{{
    type:'bar',
    data:{{labels:D.weeks,datasets:[{{label:'Втрачений GMV, €',data:D.ow_lost,backgroundColor:'#f87171',borderColor:'#dc2626',borderWidth:1}}]}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}},
      tooltip:{{callbacks:{{label:(c)=>'€'+c.parsed.y.toLocaleString('uk-UA')}}}}}},
      scales:{{x:{{grid:{{display:false}}}},y:{{grid:{{color:gridc}},ticks:{{callback:(v)=>'€'+(v/1000)+'k'}}}}}}}}
  }});
  new Chart(document.getElementById('chartReasonWeek'),{{
    type:'bar',
    data:{{labels:D.weeks,datasets:D.reasons.map((r,idx)=>({{label:r,data:D.rweek[idx],backgroundColor:D.rcolors[idx]}}))}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},
      scales:{{x:{{stacked:true,grid:{{display:false}}}},y:{{stacked:true,grid:{{color:gridc}}}}}}}}
  }});
  new Chart(document.getElementById('chartReasonMix'),{{
    type:'doughnut',
    data:{{labels:D.reasons,datasets:[{{data:D.rtot,backgroundColor:D.rcolors,borderWidth:2,borderColor:'#fff'}}]}},
    options:{{responsive:true,maintainAspectRatio:false,cutout:'55%',plugins:{{legend:{{position:'right',labels:{{boxWidth:12,font:{{size:11}}}}}}}}}}
  }});
}}

function buildBad(){{
  new Chart(document.getElementById('chartActor'),{{
    type:'doughnut',
    data:{{labels:D.bad_actor_labels,datasets:[{{data:D.bad_actor_data,backgroundColor:D.bad_actor_colors,borderWidth:2,borderColor:'#fff'}}]}},
    options:{{responsive:true,maintainAspectRatio:false,cutout:'55%',plugins:{{legend:{{position:'right',labels:{{boxWidth:12,font:{{size:11}}}}}}}}}}
  }});
  new Chart(document.getElementById('chartBadTrend'),{{
    data:{{labels:D.weeks,datasets:[
      {{type:'bar',label:'Bad orders',data:D.ow_bad,backgroundColor:'#fdba74',yAxisID:'y',order:2}},
      {{type:'line',label:'Bad-rate %',data:D.ow_badrate,borderColor:'#ea580c',backgroundColor:'#ea580c',tension:.3,yAxisID:'y1',order:1,pointRadius:3}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom'}}}},
      scales:{{y:{{position:'left',grid:{{color:gridc}}}},y1:{{position:'right',grid:{{drawOnChartArea:false}},suggestedMax:20}}}}}}
  }});
  new Chart(document.getElementById('chartActorWeek'),{{
    type:'bar',
    data:{{labels:D.weeks,datasets:D.bad_actor_labels.map((l,idx)=>({{label:l,data:D.bad_actor_week[idx],backgroundColor:D.bad_actor_colors[idx]}}))}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom',labels:{{boxWidth:11,font:{{size:10}}}}}}}},
      scales:{{x:{{stacked:true,grid:{{display:false}}}},y:{{stacked:true,grid:{{color:gridc}}}}}}}}
  }});
}}

function buildComp(){{
  new Chart(document.getElementById('chartComp'),{{
    type:'doughnut',
    data:{{labels:D.comp_labels,datasets:[{{data:D.comp_data,backgroundColor:D.comp_colors,borderWidth:2,borderColor:'#fff'}}]}},
    options:{{responsive:true,maintainAspectRatio:false,cutout:'55%',plugins:{{legend:{{position:'right',labels:{{boxWidth:12,font:{{size:11}}}}}}}}}}
  }});
  new Chart(document.getElementById('chartTicTrend'),{{
    data:{{labels:D.weeks,datasets:[
      {{type:'bar',label:'Скарги (тикети)',data:D.ow_tic,backgroundColor:'#93c5fd',yAxisID:'y',order:2}},
      {{type:'line',label:'Ticket-rate %',data:D.ow_ticrate,borderColor:'#2563eb',backgroundColor:'#2563eb',tension:.3,yAxisID:'y1',order:1,pointRadius:3}}
    ]}},
    options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{position:'bottom'}}}},
      scales:{{y:{{position:'left',grid:{{color:gridc}}}},y1:{{position:'right',grid:{{drawOnChartArea:false}},suggestedMax:10}}}}}}
  }});
}}

const BUILDERS={{failed:buildFailed,bad:buildBad,comp:buildComp,smb:function(){{}}}};
const TABS=['failed','bad','comp','smb'];
function showTab(id){{
  TABS.forEach(t=>{{
    document.getElementById('pane-'+t).classList.toggle('active', t===id);
    document.getElementById('tab-'+t).classList.toggle('active', t===id);
  }});
  if(!built[id]){{ BUILDERS[id](); built[id]=true; }}
}}
showTab('failed');

let smbSort={{col:-1,dir:1}};
function sortSMB(col,type){{
  const tb=document.querySelector('#smbTable tbody');
  const rows=Array.from(tb.querySelectorAll('tr'));
  smbSort.dir = (smbSort.col===col)? -smbSort.dir : (type==='n'? -1 : 1);
  smbSort.col=col;
  rows.sort((a,b)=>{{
    let x=a.children[col].getAttribute('data-v'), y=b.children[col].getAttribute('data-v');
    if(type==='n'){{x=parseFloat(x)||0;y=parseFloat(y)||0;return (x-y)*smbSort.dir;}}
    return String(x).localeCompare(String(y),'uk')*smbSort.dir;
  }});
  rows.forEach(r=>tb.appendChild(r));
}}
function filterSMB(){{
  const q=document.getElementById('smbSearch').value.toLowerCase();
  document.querySelectorAll('#smbTable tbody tr').forEach(r=>{{
    const name=r.children[0].getAttribute('data-v').toLowerCase();
    const am=(r.children[4].getAttribute('data-v')||'').toLowerCase();
    r.style.display=(name.includes(q)||am.includes(q))?'':'none';
  }});
}}

function downloadPDF(){{
  TABS.forEach(t=>{{ if(!built[t]){{ BUILDERS[t](); built[t]=true; }} document.getElementById('pane-'+t).classList.add('active'); }});
  const el=document.getElementById('report');
  setTimeout(()=>{{
    html2pdf().set({{margin:6,filename:'orders-health-ua-stores.pdf',image:{{type:'jpeg',quality:.98}},
      html2canvas:{{scale:2,useCORS:true}},jsPDF:{{unit:'mm',format:'a3',orientation:'portrait'}}}}).from(el).save()
      .then(()=>['bad','comp','smb'].forEach(t=>document.getElementById('pane-'+t).classList.remove('active')));
  }},400);
}}
</script>
</body>
</html>
"""
open(HERE / "index.html", "w").write(HTML)
print("wrote index.html", len(HTML), "bytes")
