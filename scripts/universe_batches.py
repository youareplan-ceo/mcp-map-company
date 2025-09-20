import csv, sys, math
import argparse
p=argparse.ArgumentParser(); p.add_argument("--csv",required=True); p.add_argument("--batch",type=int,default=500)
a=p.parse_args()
with open(a.csv,newline='') as f:
    r=csv.reader(f); header=next(r); rows=[row for row in r if len(row)==3]
n=len(rows); b=math.ceil(n/a.batch)
for i in range(b):
    chunk=rows[i*a.batch:(i+1)*a.batch]
    print(f"# batch {i+1}/{b} size={len(chunk)}")
    # ↓ 여기서 chunk를 시그널 엔진으로 전달하면 됨
