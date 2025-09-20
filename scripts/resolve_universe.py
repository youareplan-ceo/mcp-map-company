import os, csv, argparse, sys
from pathlib import Path
def load_csv(path):
    with open(path, newline='') as f:
        r=csv.reader(f); next(r); return [row for row in r if len(row)==3]
def resolve(tokens, root):
    m=[]; udir=Path(root)/"data/universe"
    for t in tokens:
        t=t.strip()
        if t.upper()=="ALL:US": m+=load_csv(udir/"us_all.csv")
        elif t.upper()=="ALL:KR": m+=load_csv(udir/"kr_all.csv")
        elif t: m.append([t, "", ""])
    # 중복 제거(심볼 기준)
    seen=set(); out=[]
    for sym,ex,name in m:
        if sym in seen: continue
        seen.add(sym); out.append([sym,ex,name])
    return out
if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--universe",required=False,default=os.getenv("STOCK_UNIVERSE","ALL:US,ALL:KR")); p.add_argument("--root",default=".")
    a=p.parse_args(); toks=[x for x in a.universe.split(",") if x.strip()]
    rows=resolve(toks, a.root)
    print(len(rows))
    for r in rows[:10]:
        print(",".join(r))
