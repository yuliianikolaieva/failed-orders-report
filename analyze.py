# -*- coding: utf-8 -*-
import json, collections
from pathlib import Path
d = json.load(open(Path(__file__).parent / "data.json"))

def num(x):
    return float(x) if x is not None else 0.0

wt = d["weekly_totals"]
wr = d["weekly_reasons"]

# weeks sorted
weeks = sorted({r["wk"] for r in wt})
print("weeks:", weeks)

# partner totals
tot = collections.defaultdict(lambda: [0, 0, 0])  # total, delivered, failed
for r in wt:
    g = r["grp"] or "—"
    tot[g][0] += int(num(r["total"]))
    tot[g][1] += int(num(r["delivered"]))
    tot[g][2] += int(num(r["failed"]))

# overall
G = sum(v[0] for v in tot.values()); D = sum(v[1] for v in tot.values()); F = sum(v[2] for v in tot.values())
print(f"\nOVERALL UA stores: total={G} delivered={D} failed={F} fail_rate={F/G*100:.2f}%")

top = sorted(tot.items(), key=lambda kv: -kv[1][2])[:10]
print("\nTOP 10 partners by failed orders:")
for g, v in top:
    print(f"  {g:<22} failed={v[2]:>5}  total={v[0]:>6}  fail_rate={v[2]/v[0]*100:5.2f}%")

topnames = [g for g, _ in top]

# reason totals for top 10
print("\nReason mix for TOP10:")
rc = collections.defaultdict(int)
for r in wr:
    if (r["grp"] or "—") in topnames:
        rc[r["reason"]] += int(num(r["n"]))
tf = sum(rc.values())
for reason, n in sorted(rc.items(), key=lambda kv:-kv[1]):
    print(f"  {reason:<34} {n:>5}  {n/tf*100:4.1f}%")

# weekly fail rate for top 10 partners
print("\nWeekly fail-rate per top partner (%):")
byw = collections.defaultdict(lambda: collections.defaultdict(lambda:[0,0]))
for r in wt:
    g = r["grp"] or "—"
    if g in topnames:
        byw[g][r["wk"]][0]+=int(num(r["total"]))
        byw[g][r["wk"]][1]+=int(num(r["failed"]))
hdr = "  %-20s"%"" + "".join(f"{w[5:]:>7}" for w in weeks)
print(hdr)
for g,_ in top:
    line = "  %-20s"%g[:20]
    for w in weeks:
        t,f = byw[g][w]
        line += f"{(f/t*100 if t else 0):6.1f}%".rjust(7) if t else "     - "
    print(line)
