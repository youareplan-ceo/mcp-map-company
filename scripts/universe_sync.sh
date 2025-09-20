#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DST_US="$ROOT/data/universe/us_all.csv"
DST_KR="$ROOT/data/universe/kr_all.csv"
TMP_DIR="$(mktemp -d)"; trap 'rm -rf "$TMP_DIR"' EXIT
log() { printf "[*] %s\n" "$*"; }

log "Universe sync start"

US_NAS="$TMP_DIR/nasdaqtraded.txt"
US_OTH="$TMP_DIR/otherlisted.txt"
curl -fsSL "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt" -o "$US_NAS"
curl -fsSL "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt" -o "$US_OTH"

# nasdaqtraded.txt  (1=Nasdaq Traded, 2=Symbol, 3=Security Name, 6=ETF, 8=Test Issue)
awk -F'|' '
  NR>1 && $1!="Nasdaq Traded" && $1!="File Creation Time" && $1=="Y" && $8=="N" && $6=="N" && $2!="" {
    sym=$2; name=$3; gsub(/"/,"\"\"",name);
    print sym ",NASDAQ,\"" name "\""
  }
' "$US_NAS" > "$TMP_DIR/us_nas.csv"

# otherlisted.txt (1=ACT Symbol, 2=Security Name, 3=Exchange(A/N/P=AMEX/NYSE/ARCA), 7=Test Issue)
awk -F'|' '
  NR>1 && $1!="ACT Symbol" && $7!="Y" && $1 ~ /^[A-Z0-9.\-]+$/ && $2!="" {
    sym=$1; name=$2; ex=$3;
    if (ex=="A") exo="AMEX"; else if (ex=="N") exo="NYSE"; else if (ex=="P") exo="ARCA"; else exo=ex;
    gsub(/"/,"\"\"",name);
    print sym "," exo ",\"" name "\""
  }
' "$US_OTH" > "$TMP_DIR/us_oth.csv"

{ echo "symbol,exchange,name"; cat "$TMP_DIR/us_nas.csv" "$TMP_DIR/us_oth.csv" | sort -u; } > "$DST_US"

PYBIN="$ROOT/.venv-universe/bin/python3"; [[ -x "$PYBIN" ]] || PYBIN="$(command -v python3 || command -v python)"
"$PYBIN" - <<'PY' || { "$PYBIN" -m pip install --quiet --upgrade finance-datareader pandas && "$PYBIN" - <<'PY'; }
import pandas as pd, FinanceDataReader as fdr
def pick(df, cands):
    for c in cands:
        if c in df.columns: return c
    raise KeyError(cands)
def listing(market):
    df = fdr.StockListing(market)
    sym = pick(df, ['Symbol','Code'])
    name = pick(df, ['Name','NameKorean'])
    mkt  = pick(df, ['Market','MarketId','Exchange'])
    out = df[[sym, mkt, name]].dropna()
    out.columns = ['symbol','exchange','name']
    out['symbol'] = out['symbol'].astype(str).str.replace('.0','', regex=False).str.zfill(6)
    out['exchange'] = out['exchange'].replace({'KOSPI':'KRX','KOSDAQ':'KRX','KONEX':'KRX'})
    return out
df = pd.concat([listing('KRX'), listing('KOSDAQ')], ignore_index=True).drop_duplicates(subset=['symbol']).sort_values('symbol')
df.to_csv('data/universe/kr_all.csv', index=False)
PY
import pandas as pd, FinanceDataReader as fdr
def pick(df, cands):
    for c in cands:
        if c in df.columns: return c
    raise KeyError(cands)
def listing(market):
    df = fdr.StockListing(market)
    sym = pick(df, ['Symbol','Code'])
    name = pick(df, ['Name','NameKorean'])
    mkt  = pick(df, ['Market','MarketId','Exchange'])
    out = df[[sym, mkt, name]].dropna()
    out.columns = ['symbol','exchange','name']
    out['symbol'] = out['symbol'].astype(str).str.replace('.0','', regex=False).str.zfill(6)
    out['exchange'] = out['exchange'].replace({'KOSPI':'KRX','KOSDAQ':'KRX','KONEX':'KRX'})
    return out
df = pd.concat([listing('KRX'), listing('KOSDAQ')], ignore_index=True).drop_duplicates(subset=['symbol']).sort_values('symbol')
df.to_csv('data/universe/kr_all.csv', index=False)
PY

log "US CSV: $(wc -l < "$DST_US") lines (including header)"
log "KR CSV: $(wc -l < "$DST_KR") lines (including header)"
log "Universe sync done"
