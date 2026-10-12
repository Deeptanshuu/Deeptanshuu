#!/usr/bin/env python3
"""Render the whoburnedmore token-burn panel in the deeptanshu.tech brand palette.

Pulls public usage from the whoburnedmore JSON API (no key, no secrets) and
writes assets/whoburnedmore.svg.

The API only splits usage by tool per period, not per day, so each run also
records today's per-tool split (period=today -> byTool) in data/token-history.json.
Re-running on the same UTC day overwrites that day, and the 30-day bars are
stacked by tool for every day the history covers. Width and insets match render_contributions.py
(833 wide, rx 14) so the two panels stack as one grid; this one is taller to
fit the per-tool breakdown.

Stdlib only - no pip install needed in the Action.
"""
import os, re, json, ssl, datetime, urllib.request, urllib.error

# ---- brand tokens (deeptanshu.tech: monochrome, green accent) ----
BG="#09090a"; HAIR="#ffffff14"
FG="#fafafa"; DIM2="#ffffff9e"; FAINT="#ffffff55"
SEP="#ffffff40"   # dim "·" separator, as in the site\'s chips
MONO="ui-monospace,'JetBrains Mono','SF Mono',Menlo,Consolas,monospace"

# width identical to render_contributions.py so both panels share one grid
W=833; H=328

# tools shown on their own (stacking order, bottom up); everything else is "Other".
# name, colour (brand colour where the brand has one), icon in tool-icons/
TOOLS={
    "claude":  ("Claude Code","#d97757","claudecode"),
    "pi":      ("Pi",         "#a78bfa","pi"),
    "hermes":  ("Hermes",     "#4d4dff","hermesagent.png"),  # site blue #0000f2, lifted to read on black; official app icon
    "opencode":("OpenCode",   "#8e8b8b","opencode"),      # monochrome brand; icon keeps its own two tones
    "cursor":  ("Cursor",     "#6b7a8f","cursor"),
    "codex":   ("Codex",      "#fafafa","codex"),
}
OTHER=("Other","#52525b",None)
ICON_DIR=os.path.join(os.path.dirname(os.path.abspath(__file__)),"tool-icons")
HISTORY_KEEP=400   # days of per-tool history to retain

# Load-in + idle motion. GitHub serves these as <img>, so there is no hover;
# everything plays on load, and only "live" bits loop. Reduced motion = static.
EASE="cubic-bezier(.22,1,.36,1)"
STYLE=f"""<style>
@keyframes grow{{from{{transform:scaleY(0)}}to{{transform:scaleY(1)}}}}
@keyframes wipe{{from{{transform:scaleX(0)}}to{{transform:scaleX(1)}}}}
@keyframes rise{{from{{opacity:0;transform:translateY(6px)}}to{{opacity:1;transform:none}}}}
@keyframes breathe{{0%,100%{{opacity:1}}50%{{opacity:.45}}}}
.bar{{transform-box:fill-box;transform-origin:50% 100%;animation:grow .8s {EASE} both}}
.wipe{{transform-box:fill-box;transform-origin:0 50%;animation:wipe 1.1s {EASE} .5s both}}
.rise{{animation:rise .7s {EASE} both}}
.live{{animation:breathe 2.4s ease-in-out infinite}}
.today{{animation:grow .8s {EASE} both,breathe 3s ease-in-out 1.6s infinite}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>"""
PADL=33; PADR=33; RIGHT=W-PADR   # symmetric inset so the card reads centred

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
    allt=sum(d["tokens"] for d in daily)*7
    shares={"claude":.67,"pi":.14,"hermes":.085,"opencode":.064,"cursor":.034,"codex":.003,"gemini":.0002,"goose":.0001}
    hist={d["date"]:{t:int(d["tokens"]*f*random.uniform(.5,1.5)) for t,f in shares.items()}
          for d in daily[-9:]}
    return {"history":hist,
            "all":{"totals":tot(allt),"daily":daily,
                   "byTool":[{"tool":t,"tokens":int(allt*f)} for t,f in shares.items()]},
            "today":{"totals":tot(daily[-1]["tokens"])},
            "week":{"totals":tot(sum(d["tokens"] for d in daily[-7:]))},
            "year":{"totals":tot(sum(d["tokens"] for d in daily)*6.4)}}

def human(n):
    if n>=1e9: return f"{n/1e9:.1f}B"
    if n>=1e6: return f"{n/1e6:.1f}M"
    if n>=1e3: return f"{n/1e3:.1f}K"
    return f"{n:.0f}"

def group(by_tool):
    """{tool: tokens} -> [(key, tokens)] for the named tools in TOOLS order, then 'other'."""
    out={k:0 for k in TOOLS}; other=0
    for t,v in by_tool.items():
        if t in out: out[t]+=v
        else: other+=v
    rows=[(k,v) for k,v in out.items() if v>0]
    if other>0: rows.append(("other",other))
    return rows

def meta(key):
    return TOOLS.get(key, OTHER)

_icons={}
def icon(key, x, y, size, color):
    """Inline a tool icon at (x, y): 24x24 SVGs are tinted with color, PNGs (full-colour
    app icons) are embedded as-is; Other gets a dot."""
    file=meta(key)[2]
    if not file:
        r=size*0.32
        return f'<circle cx="{x+size/2:.1f}" cy="{y+size/2:.1f}" r="{r:.1f}" fill="{color}"/>'
    if file.endswith(".png"):
        if file not in _icons:
            import base64
            _icons[file]=base64.b64encode(open(os.path.join(ICON_DIR,file),"rb").read()).decode()
        s=size+1   # app icons carry their own padding; nudge up to match glyph weight
        return (f'<image x="{x-0.5:.1f}" y="{y-0.5:.1f}" width="{s}" height="{s}" '
                f'href="data:image/png;base64,{_icons[file]}"/>')
    if file not in _icons:
        svg=open(os.path.join(ICON_DIR,file+".svg")).read()
        inner=re.sub(r"<title>.*?</title>","",svg[svg.index(">")+1:svg.rindex("</svg>")])
        _icons[file]=inner
    return (f'<g transform="translate({x:.1f},{y:.1f}) scale({size/24:.4f})" fill="{color}" fill-rule="evenodd">'
            f'{_icons[file]}</g>')

def short(s):
    m=int(s[5:7]); return f"{['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m-1]} {int(s[8:10])}"

def bars_bg(data):
    """30-day daily bars, stacked by tool. Only days the history covers get a bar (the API
    has no per-day split); earlier days are a faint tick so the 30-day axis still reads."""
    daily=(data["all"].get("daily") or [])[-30:]
    if not daily: return ""
    hist=data.get("history") or {}
    mx=max(d["tokens"] for d in daily) or 1
    n=len(daily)
    span=RIGHT-PADL
    step=span/n
    bw=min(18.0, step-6)
    base=206.0; maxh=44.0; minh=2.0; p=0.45   # sqrt-ish: flat days stay readable
    out=[]
    for i,d in enumerate(daily):
        v=d["tokens"]
        x=PADL+i*step+(step-bw)/2
        h=minh if v<=0 else max(minh, maxh*(v/mx)**p)
        rows=group(hist.get(d["date"]) or {}) if v>0 else []
        tot=sum(t for _,t in rows)
        if not tot:
            out.append(f'<rect x="{x:.1f}" y="{base-1:.1f}" width="{bw:.1f}" height="1" fill="{HAIR}"/>')
            continue
        cls="today" if i==n-1 else "bar"
        out.append(f'<g class="{cls}" style="animation-delay:{i*25}ms">')
        cid=f"b{i}"
        out.append(f'<clipPath id="{cid}"><rect x="{x:.1f}" y="{base-h:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="2.5"/></clipPath><g clip-path="url(#{cid})">')
        y=base
        for key,t in rows:   # TOOLS order, bottom up
            sh=h*t/tot
            out.append(f'<rect x="{x:.1f}" y="{y-sh:.2f}" width="{bw:.1f}" height="{sh:.2f}" fill="{meta(key)[1]}"/>')
            y-=sh
        out.append('</g></g>')
    right=f"{short(daily[0]['date'])} &#8594; {short(daily[-1]['date'])}"
    tracked=sorted(d["date"] for d in daily if hist.get(d["date"]))
    left="LAST 30 DAYS &#183; BY TOOL"
    if tracked and tracked[0]!=daily[0]["date"]:
        left+=f'<tspan letter-spacing="0" fill="{SEP}">  &#183;  tracked since {short(tracked[0])}</tspan>'
    out.append(f'<text x="{PADL}" y="152" font-family="{MONO}" font-size="10" letter-spacing="2" fill="{FAINT}">{left}</text>')
    out.append(f'<text x="{RIGHT}" y="152" text-anchor="end" font-family="{MONO}" font-size="10" fill="{FAINT}">{right}</text>')
    return "".join(out)

def tools_bg(data):
    """All-time split by tool: one stacked bar plus an icon legend underneath."""
    rows=group({t["tool"]:t["tokens"] for t in (data["all"].get("byTool") or [])})
    if not rows: return ""
    named=sorted([r for r in rows if r[0]!="other"], key=lambda r:-r[1])
    rows=named+[r for r in rows if r[0]=="other"]
    total=sum(t for _,t in rows)
    span=RIGHT-PADL; y=250; bh=10; gap=2; minw=3.0
    # every group gets at least minw px so small ones stay visible; the rest is proportional
    free=span-gap*(len(rows)-1)-minw*len(rows)
    out=[f'<text x="{PADL}" y="238" font-family="{MONO}" font-size="10" letter-spacing="2" fill="{FAINT}">BY TOOL &#183; ALL TIME</text>']
    x=float(PADL)
    out.append('<g class="wipe">')
    for key,t in rows:
        w=minw+free*t/total
        out.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{bh}" rx="2" fill="{meta(key)[1]}"/>')
        x+=w+gap
    out.append('</g>')
    cols=4; gut=24; colw=(span+gut)/cols   # last column ends flush at RIGHT
    for i,(key,t) in enumerate(rows):
        cx=PADL+(i%cols)*colw; cy=284+(i//cols)*22
        name,color,_=meta(key)
        pct=100*t/total
        pcts=f"{pct:.0f}%" if pct>=1 else "&lt;1%"
        out.append(f'<g class="rise" style="animation-delay:{900+i*70}ms">'+icon(key,cx,cy-10.5,13,color)+
                   f'<text x="{cx+20:.1f}" y="{cy}" font-family="{MONO}" font-size="11" fill="{DIM2}">{name}</text>'
                   f'<text x="{cx+colw-gut:.1f}" y="{cy}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{FAINT}">{human(t)} <tspan fill="{SEP}">&#183;</tspan> {pcts}</text></g>')
    return "".join(out)

def load_history(path):
    try:
        with open(path) as f: return json.load(f).get("days",{})
    except (FileNotFoundError, ValueError):
        return {}

def save_history(path, days, today):
    """Record today's per-tool split (overwrites earlier runs on the same UTC day)."""
    date=today.get("from") or today.get("to")
    split={t["tool"]:t["tokens"] for t in today.get("byTool") or [] if t.get("tokens",0)>0}
    if not date or not split: return days
    days=dict(days); days[date]=dict(sorted(split.items(), key=lambda kv:-kv[1]))
    days=dict(sorted(days.items())[-HISTORY_KEEP:])
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path,"w") as f:
        json.dump({"source":"https://api.whoburnedmore.com/v1/usage (period=today, byTool)",
                   "days":days}, f, indent=1)
        f.write("\n")
    print(f"  history: {date} -> {split}")
    return days

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
    active=allt.get("activeDays")
    bits=[]
    if active: bits.append(f"{active} active days")
    bits.append(f"synced {synced} UTC")
    meta=f' <tspan fill="{SEP}">&#183;</tspan> '.join(bits)
    meta_w=len(" · ".join(bits))*13*0.6
    dot=f'<circle class="live" cx="{RIGHT-meta_w-10:.1f}" cy="33.5" r="3" fill="{FG}"/>' 
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">
  {STYLE}
  <rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="{BG}" stroke="{HAIR}"/>
  {rule()}
  {dot}<text x="{RIGHT}" y="38" text-anchor="end" font-family="{MONO}" font-size="13" fill="{DIM2}">{meta}</text>
  <line x1="{PADL}" y1="50" x2="{RIGHT}" y2="50" stroke="{HAIR}"/>
  <g class="rise"><text x="{PADL}" y="112" font-family="{MONO}" font-size="52" fill="{FG}">{human(allt["tokens"])}</text>
  <text x="{PADL}" y="132" font-family="{MONO}" font-size="10" letter-spacing="1.5" fill="{FAINT}">TOKENS BURNED &#183; ALL TIME</text></g>
  <g class="rise" style="animation-delay:150ms">{stats}</g>
  {bars_bg(data)}
  <line x1="{PADL}" y1="220" x2="{RIGHT}" y2="220" stroke="{HAIR}"/>
  {tools_bg(data)}
</svg>
'''

def main():
    handle=os.environ.get("WBM_HANDLE","deeptanshuu")
    out=os.environ.get("OUT","assets/whoburnedmore.svg")
    history=os.environ.get("HISTORY","data/token-history.json")
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
        data["history"]=save_history(history, load_history(history), data["today"])
    open(out,"w").write(render(data))
    print("wrote", out)

if __name__=="__main__":
    main()
