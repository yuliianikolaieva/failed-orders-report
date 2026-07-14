# -*- coding: utf-8 -*-
import json, collections
from pathlib import Path
d = json.load(open(Path(__file__).parent / "data.json"))
def i(x):
    try: return int(float(x))
    except: return 0

bw=d["bad_weekly"]; ba=d["bad_attr"]
weeks=sorted({r["wk"] for r in bw})
print("weeks:",weeks)

# overall bad order
BAD=sum(i(r["bad"]) for r in bw); DEL=sum(i(r["delivered"]) for r in bw)
TIC=sum(i(r["tickets"]) for r in bw); LATE=sum(i(r["late10"]) for r in bw); LOW=sum(i(r["lowrate"]) for r in bw)
print(f"\nOVERALL delivered={DEL}  bad={BAD} ({BAD/DEL*100:.1f}%)  tickets={TIC} ({TIC/DEL*100:.1f}%)  late10={LATE} ({LATE/DEL*100:.1f}%)  lowrate={LOW}")

# actor at fault
actor=collections.defaultdict(int)
for r in ba: actor[r["actor"]]+=i(r["n"])
TA=sum(actor.values())
print("\nActor at fault:")
for a,n in sorted(actor.items(),key=lambda kv:-kv[1]): print(f"  {a:<10} {n:>5} {n/TA*100:4.1f}%")

# reason themes
def theme(rs):
    rs=(rs or "").lower()
    if any(k in rs for k in ("delay","eta_error","late","took_longer","not_moving","redispatch","starvation","dispatch","batching","assignment","underestimate","overestimate")): return "Запізнення / доставка"
    if "out_of_stock" in rs: return "Немає товару (out of stock)"
    if "did_not_respond" in rs or "closed" in rs or "too_many_orders" in rs or "device_issue" in rs or "do_not_wish" in rs: return "Партнер недоступний / не прийняв"
    if "manually_failed_by_cs" in rs or "automatically_failed" in rs: return "Скасовано підтримкою/системою"
    if "missing_item" in rs or "wrong_item" in rs or "entirely_wrong" in rs or "ignored_my_order_notes" in rs: return "Відсутні / неправильні позиції"
    if any(k in rs for k in ("spoiled","cold","undercooked","overcooked","expired","object_detected","contaminated","poisoning","damaged","spilled","does_not_match","description","photo","expectations")): return "Якість їжі / товару"
    if "courier" in rs: return "Проблеми з кур'єром"
    if "never_delivered" in rs: return "Не доставлено"
    if any(k in rs for k in ("price","charged","pin","menu","question")): return "Оплата / ціна / питання"
    return "Інше"
th=collections.defaultdict(int)
for r in ba: th[theme(r["reason"])]+=i(r["n"])
TT=sum(th.values())
print("\nBad order reason themes:")
for t,n in sorted(th.items(),key=lambda kv:-kv[1]): print(f"  {t:<34} {n:>5} {n/TT*100:4.1f}%")

# top15 by failed (reuse) for bad order rate context: top partners by bad count
tot=collections.defaultdict(lambda:[0,0,0])  # delivered, bad, tickets
for r in bw:
    g=r["grp"] or "—"; tot[g][0]+=i(r["delivered"]); tot[g][1]+=i(r["bad"]); tot[g][2]+=i(r["tickets"])
topbad=sorted(tot.items(),key=lambda kv:-kv[1][1])[:15]
print("\nTop-15 by bad orders:")
for g,v in topbad:
    print(f"  {g:<22} deliv={v[0]:>6} bad={v[1]:>4} ({v[1]/v[0]*100 if v[0] else 0:4.1f}%) tickets={v[2]:>4} ({v[2]/v[0]*100 if v[0] else 0:4.1f}%)")
