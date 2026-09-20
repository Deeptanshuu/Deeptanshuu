#!/usr/bin/env python3
"""Render the whoburnedmore token-burn panel in the deeptanshu.tech brand palette.

Pulls public usage from the whoburnedmore JSON API (no key, no secrets) and
writes assets/whoburnedmore.svg. Geometry matches render_contributions.py
(833x209, rx 14) so the two panels stack as one grid.

Stdlib only - no pip install needed in the Action.
"""
import os, json, ssl, datetime, urllib.request, urllib.error

# ---- brand tokens (rebrand.deeptanshu.tech) ----
BG="#09090a"; HAIR="#ffffff14"
FG="#fafafa"; DIM2="#ffffff9e"; FAINT="#ffffff55"
GOLD="#e8b339"
# gold intensity ramp: empty -> bright gold (level 0..4)
LEVELS=["#16161a","#4a3b18","#8a6a20","#c0922c","#e8b339"]
MONO="ui-monospace,'JetBrains Mono','SF Mono',Menlo,Consolas,monospace"

# identical to render_contributions.py so both panels share one grid
W=833; H=209
PADL=66; PADR=28; RIGHT=W-PADR

API="https://api.whoburnedmore.com/v1/usage"
PERIODS=["today","week","year","all"]

def ssl_contexts():
    """CA bundles to try in order: certifi (local), then the system store (CI)."""
    paths=[]
    try:
        import certifi; paths.append(certifi.where())
    except ImportError:
        pass
    paths += ["/etc/ssl/cert.pem", "/etc/pki/tls/certs/ca-bundle.crt"]
    ctxs=[]
    for p in paths:
        if os.path.exists(p):
            try: ctxs.append(ssl.create_default_context(cafile=p))
            except Exception: pass
    ctxs.append(ssl.create_default_context())
    return ctxs

CTXS=ssl_contexts()

def get(handle, period, timeout=30):
    url=f"{API}/{handle}?period={period}"
    last=None
    for ctx in CTXS:
        req=urllib.request.Request(url, headers={"User-Agent":"profile-readme/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
                return json.load(r)
        except ssl.SSLError as e:
            last=e
    raise last

def fetch_live(handle):
    data={}
    for p in PERIODS:
        data[p]=get(handle,p)
        print(f"  {p}: {data[p]['totals']['tokens']:,} tokens")
    return data

def mock():
    """Deterministic local preview data, no network."""
    import random; random.seed(9)
    today=datetime.date(2026,9,20)
    daily=[]
    for i in range(30):
        d=today-datetime.timedelta(days=29-i)
        peak=1.0 if random.random()<0.15 else 0.0
        tok=int((random.random()**2*4e8+peak*6e8)+random.random()*2e7)
        daily.append({"date":d.isoformat(),"tokens":tok,"costUSD":tok/1.35e6})
    def tot(n): return {"tokens":n,"costUSD":n/1.35e6,"activeDays":264}
    return {"all":{"totals":tot(sum(d["tokens"] for d in daily)*7),"daily":daily},
            "today":{"totals":tot(daily[-1]["tokens"])},
            "week":{"totals":tot(sum(d["tokens"] for d in daily[-7:]))},
            "year":{"totals":tot(sum(d["tokens"] for d in daily)*6.4)}}

def human(n):
    if n>=1e9: return f"{n/1e9:.1f}B"
    if n>=1e6: return f"{n/1e6:.1f}M"
    if n>=1e3: return f"{n/1e3:.1f}K"
    return f"{n:.0f}"

def bars_bg(data):
    """30-day daily bars, coloured on the gold ramp by relative size."""
    daily=data["all"].get("daily") or []
    vals=[d["tokens"] for d in daily][-30:]
    if not vals: return ""
    mx=max(vals) or 1
    n=len(vals)
    span=RIGHT-PADL
    step=span/n
    bw=min(18.0, step-6)
    base=194.0; maxh=46.0; minh=2.0; p=0.45   # sqrt-ish: flat days stay readable
    out=[]
    for i,v in enumerate(vals):
        x=PADL+i*step+(step-bw)/2
        h=minh if v<=0 else max(minh, maxh*(v/mx)**p)
        r=v/mx
        q=0 if v<=0 else (4 if r>0.5 else 3 if r>0.2 else 2 if r>0.05 else 1)
        out.append(f'<rect x="{x:.1f}" y="{base-h:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="2.5" fill="{LEVELS[q]}"/>')
    first=daily[-n]["date"] if len(daily)>=n else daily[0]["date"]
    last=daily[-1]["date"]
    def short(s): 
        m=int(s[5:7]); return f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m-1]} {int(s[8:10])}"
    out.append(f'<text x="{PADL}" y="152" font-family="{MONO}" font-size="10" letter-spacing="2" fill="{FAINT}">LAST 30 DAYS</text>')
    out.append(f'<text x="{RIGHT}" y="152" text-anchor="end" font-family="{MONO}" font-size="10" fill="{FAINT}">{short(first)} &#8594; {short(last)}</text>')
    return "".join(out)

def rule(prefix=""):
    return f'<text x="{PADL}" y="38" font-family="{MONO}" font-size="11" letter-spacing="3" fill="{FAINT}">{prefix}TOKEN BURN</text>'

def render(data):
    allt=data["all"]["totals"]
    cols=[("THIS YEAR",human(data["year"]["totals"]["tokens"])),
          ("THIS WEEK",human(data["week"]["totals"]["tokens"])),
          ("TODAY",human(data["today"]["totals"]["tokens"]))]
    xs=[RIGHT-330, RIGHT-165, RIGHT]
    stats="".join(
        f'<text x="{x}" y="86" text-anchor="end" font-family="{MONO}" font-size="10" letter-spacing="1.5" fill="{FAINT}">{lbl}</text>'
        f'<text x="{x}" y="112" text-anchor="end" font-family="{MONO}" font-size="22" fill="{DIM2}">{val}</text>'
        for (lbl,val),x in zip(cols,xs))
    synced=(data["all"].get("lastSyncedAt") or "")[:10] or datetime.date.today().isoformat()
    cost=allt.get("costUSD")
    active=allt.get("activeDays")
    bits=[]
    if active: bits.append(f"{active} active days")
    if cost: bits.append(f"est. ${human(cost)} API value")
    bits.append(f"synced {synced} UTC")
    meta=f' <tspan fill="{GOLD}">&#183;</tspan> '.join(bits)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">
  <rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="{BG}" stroke="{HAIR}"/>
  {rule()}
  <text x="{RIGHT}" y="38" text-anchor="end" font-family="{MONO}" font-size="13" fill="{DIM2}">{meta}</text>
  <line x1="{PADL}" y1="50" x2="{RIGHT}" y2="50" stroke="{HAIR}"/>
  <text x="{PADL}" y="112" font-family="{MONO}" font-size="52" fill="{FG}">{human(allt["tokens"])}</text>
  <text x="{PADL}" y="132" font-family="{MONO}" font-size="10" letter-spacing="1.5" fill="{FAINT}">TOKENS BURNED &#183; ALL TIME</text>
  {stats}
  {bars_bg(data)}
</svg>
'''

def main():
    handle=os.environ.get("WBM_HANDLE","deeptanshuu")
    out=os.environ.get("OUT","assets/whoburnedmore.svg")
    if os.environ.get("MOCK"):
        data=mock(); print(f"mock: {human(data['all']['totals']['tokens'])} tokens")
    else:
        try:
            print(f"live: {handle}")
            data=fetch_live(handle)
        except (urllib.error.URLError, urllib.error.HTTPError, KeyError, ValueError) as e:
            # never blank out a good panel on a transient API failure
            print(f"::warning::whoburnedmore fetch failed ({e}); keeping existing {out}")
            if os.path.exists(out): return
            raise SystemExit(1)
    open(out,"w").write(render(data))
    print("wrote", out)

if __name__=="__main__":
    main()
