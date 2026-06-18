#!/usr/bin/env python3
"""Render a contribution heatmap in the deeptanshu.tech brand palette.

Live mode (in CI): set GH_USERNAME + GITHUB_TOKEN, queries the GitHub
GraphQL contribution calendar and writes assets/contributions.svg.
Preview mode (local, no token): generates deterministic mock data so the
visual can be checked without hitting the API.

Stdlib only — no pip install needed in the Action.
"""
import os, json, datetime, urllib.request

# ---- brand tokens (rebrand.deeptanshu.tech) ----
BG="#09090a"; HAIR="#ffffff14"; RULE="#ffffff1c"
FG="#fafafa"; DIM="#ffffff80"; DIM2="#ffffff9e"; FAINT="#ffffff55"
GOLD="#e8b339"; GREEN="#34d058"
# gold intensity ramp: empty -> bright gold (level 0..4)
LEVELS=["#16161a","#4a3b18","#8a6a20","#c0922c","#e8b339"]
MONO="ui-monospace,'JetBrains Mono','SF Mono',Menlo,Consolas,monospace"

CELL=11; GAP=3; STEP=CELL+GAP
GX=66; GY=70          # grid origin
PADR=28
W=GX + 53*STEP - GAP + PADR
H=GY + 7*STEP - GAP + 44

def fetch_live(user, token):
    q = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
      totalContributions weeks{contributionDays{contributionCount date weekday color}}}}}}"""
    body = json.dumps({"query": q, "variables": {"login": user}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": user})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [[d["contributionCount"] for d in w["contributionDays"]] for w in cal["weeks"]]
    return cal["totalContributions"], weeks, cal["weeks"]

def mock():
    import random; random.seed(4)
    today = datetime.date(2026, 6, 18)
    start = today - datetime.timedelta(weeks=52)
    start -= datetime.timedelta(days=start.weekday()+1 if start.weekday()!=6 else 0)
    weeks=[]; meta=[]; total=0
    d=start
    for _ in range(53):
        col=[]; days=[]
        for wd in range(7):
            # weekday bias + streaky bursts
            base = random.random()
            burst = 1.0 if random.random()<0.18 else 0.0
            c = int(max(0, (base*6 + burst*9 - 1.5) * (0.55 if wd in (0,6) else 1)))
            col.append(c); total+=c
            days.append({"date": d.isoformat(), "weekday": wd})
            d += datetime.timedelta(days=1)
        weeks.append(col); meta.append({"contributionDays": days})
    return total, weeks, meta

def level(c):
    if c<=0: return 0
    if c<=2: return 1
    if c<=5: return 2
    if c<=9: return 3
    return 4

def streaks(weeks, meta):
    flat=[]
    for wi,w in enumerate(weeks):
        for di,c in enumerate(w):
            flat.append(c)
    cur=0; best=0
    for c in reversed(flat):
        if c>0: cur+=1
        else: break
    run=0
    for c in flat:
        run = run+1 if c>0 else 0
        best=max(best,run)
    return cur, best

def render(total, weeks, meta):
    MONTHS=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    cells=[]
    # month labels: place when a week's first day starts a new month
    month_lbls=[]; last_m=None
    for wi,w in enumerate(meta):
        first = w["contributionDays"][0]["date"]
        m = int(first[5:7])
        if m!=last_m:
            month_lbls.append((GX + wi*STEP, MONTHS[m-1])); last_m=m
    for wi,w in enumerate(weeks):
        for di,c in enumerate(w):
            x=GX+wi*STEP; y=GY+di*STEP
            cells.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" fill="{LEVELS[level(c)]}"/>')
    months_svg="".join(f'<text x="{x}" y="{GY-10}" font-family="{MONO}" font-size="10" fill="{DIM}">{m}</text>'
                       for x,m in month_lbls)
    daylbl="".join(f'<text x="{GX-10}" y="{GY+r*STEP+CELL-1.5}" text-anchor="end" font-family="{MONO}" font-size="10" fill="{FAINT}">{d}</text>'
                   for r,d in [(1,"Mon"),(3,"Wed"),(5,"Fri")])
    legend_x=W-PADR-150; legend_y=GY+7*STEP+14
    legend="".join(f'<rect x="{legend_x+34+i*16}" y="{legend_y-9}" width="11" height="11" rx="2.5" fill="{c}"/>'
                   for i,c in enumerate(LEVELS))
    cur,best=streaks(weeks,meta)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">
  <rect x="1" y="1" width="{W-2}" height="{H-2}" rx="14" fill="{BG}" stroke="{HAIR}"/>
  <text x="{GX-0}" y="38" font-family="{MONO}" font-size="11" letter-spacing="3" fill="{FAINT}">CONTRIBUTION ACTIVITY</text>
  <text x="{W-PADR}" y="38" text-anchor="end" font-family="{MONO}" font-size="13" fill="{DIM2}">{total:,} commits <tspan fill="{GOLD}">·</tspan> {cur}d streak</text>
  <line x1="{GX}" y1="50" x2="{W-PADR}" y2="50" stroke="{HAIR}"/>
  {months_svg}
  {daylbl}
  {"".join(cells)}
  <text x="{legend_x}" y="{legend_y}" text-anchor="end" font-family="{MONO}" font-size="10" fill="{FAINT}">less</text>
  {legend}
  <text x="{legend_x+34+5*16+4}" y="{legend_y}" font-family="{MONO}" font-size="10" fill="{FAINT}">more</text>
</svg>
'''

def main():
    user=os.environ.get("GH_USERNAME"); token=os.environ.get("GITHUB_TOKEN")
    if user and token:
        total,weeks,meta=fetch_live(user,token); print(f"live: {total} contributions")
    else:
        total,weeks,meta=mock(); print(f"mock: {total} contributions")
    out=os.environ.get("OUT","assets/contributions.svg")
    open(out,"w").write(render(total,weeks,meta))
    print("wrote", out)

if __name__=="__main__":
    main()
