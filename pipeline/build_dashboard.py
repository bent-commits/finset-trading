"""Generate the static dashboard (docs/index.html) from results.json + trades.json.

Self-contained: data is inlined into the HTML, so it works on GitHub Pages and
locally (file://). Chart.js is loaded from CDN.
"""
import os
import json
from datetime import date, timedelta

from common import load_json, save_json, DATA_DIR, DOCS_DIR
import backtest as bt

NOK = "kr"


def _fmt(n):
    return f"{n:,.0f}".replace(",", " ")


def current_holdings(trades, as_of_iso, lookback_days=bt.LOOKBACK_DAYS):
    sig = bt.build_signal_index(trades)
    lookback = (date.fromisoformat(as_of_iso) - timedelta(days=lookback_days)).isoformat()
    w = bt.weights_as_of(sig, as_of_iso, lookback)
    return sorted(({"ticker": k, "weight": round(v, 4)} for k, v in w.items()),
                  key=lambda x: x["weight"], reverse=True)


def latest_buys(trades, n=18):
    buys = [t for t in trades if t["side"] == "buy"]
    buys.sort(key=lambda t: t["pub_date"], reverse=True)
    out = []
    for t in buys[:n]:
        out.append({"pub_date": t["pub_date"], "tx_date": t["tx_date"],
                    "ticker": t["ticker"], "politician": t["politician"],
                    "amount_mid": t["amount_mid"]})
    return out


def make_insight(strategies, congress_name):
    def leader(label):
        rows = [(n, d["metrics"][label]) for n, d in strategies.items()
                if label in d["metrics"]]
        rows.sort(key=lambda r: r[1]["end_value"], reverse=True)
        return rows[0] if rows else None
    mx = leader("max")
    r3 = leader("3y")
    parts = []
    if mx:
        n, m = mx
        parts.append(f"Siden {m['from'][:4]} har <b>{n}</b> gitt mest: "
                     f"{_fmt(m['end_value'])} kr (+{m['total_return']*100:.0f} %, "
                     f"{m['cagr']*100:.1f} % i året).")
    cong = strategies.get(congress_name, {}).get("metrics", {})
    if mx and mx[0] == congress_name and r3 and r3[0] != congress_name:
        c3 = cong.get("3y", {})
        parts.append(f"Men <b>fordelen har ikke vedvart</b>: siste 3 år leder "
                     f"{r3[0]} ({r3[1]['total_return']*100:.0f} %) mens Congress-"
                     f"porteføljen ga {c3.get('total_return',0)*100:.0f} % — og med "
                     f"høyere risiko (største fall {abs(cong.get('max',{}).get('max_drawdown',0))*100:.0f} %).")
    elif mx:
        parts.append("Bildet varierer mellom tidshorisontene — se tabellen under.")
    return " ".join(parts)


def build():
    res = load_json(os.path.join(DATA_DIR, "results.json"))
    trades = load_json(os.path.join(DATA_DIR, "trades.json"))
    if not res:
        raise SystemExit("run backtest.py first")

    data = {
        "generated_at": res["generated_at"],
        "data_through": res["data_through"],
        "latest_trade": res.get("latest_trade"),
        "launch": res.get("launch"),
        "capital_nok": res["capital_nok"],
        "start": res["start"],
        "congress_name": res["congress_name"],
        "star_name": res.get("star_name"),
        "star_current": res.get("star_current"),
        "star_history": res.get("star_history"),
        "n_trades": res["n_trades"],
        "config": res["config"],
        "strategies": res["strategies"],
        "holdings": current_holdings(trades, res["data_through"]),
        "latest_buys": latest_buys(trades),
        "insight": make_insight(res["strategies"], res["congress_name"]),
    }
    save_json(os.path.join(DOCS_DIR, "data.json"), data)

    html = HTML.replace("/*__DATA__*/", json.dumps(data, ensure_ascii=False))
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote {os.path.join(DOCS_DIR, 'index.html')}")


HTML = r"""<!DOCTYPE html>
<html lang="no">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Finset Trading — Kongress vs. Indeks</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
<style>
:root{
  --bg:#0d1117; --panel:#161b22; --panel2:#1c2230; --border:#2a3038;
  --txt:#e6edf3; --muted:#8b949e;
  --cong:#f5c451; --sp:#4493f8; --world:#3fb950; --oslo:#db6d28;
  --good:#3fb950; --bad:#f85149;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--txt);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  line-height:1.5;-webkit-font-smoothing:antialiased}
.wrap{max-width:1100px;margin:0 auto;padding:24px 18px 60px}
header{display:flex;flex-wrap:wrap;align-items:baseline;gap:8px 16px;
  border-bottom:1px solid var(--border);padding-bottom:16px;margin-bottom:22px}
h1{font-size:23px;margin:0;font-weight:680;letter-spacing:-.3px}
.sub{color:var(--muted);font-size:13px}
.brand{width:44px;height:44px;border-radius:11px;background:var(--cong);color:#1a1500;
  display:flex;align-items:center;justify-content:center;font-weight:780;font-size:17px;letter-spacing:-.5px;flex-shrink:0}
h1 .accent{color:var(--cong)}
.meta{margin-left:auto;color:var(--muted);font-size:12.5px;text-align:right}
.pill{display:inline-block;background:var(--panel2);border:1px solid var(--border);
  border-radius:20px;padding:2px 10px;font-size:12px;color:var(--muted)}
.insight{background:linear-gradient(180deg,#1a2030,#161b22);border:1px solid var(--border);
  border-left:3px solid var(--cong);border-radius:10px;padding:14px 16px;margin-bottom:22px;font-size:14.5px}
.tabs{display:flex;gap:6px;margin-bottom:18px;flex-wrap:wrap}
.tab{background:var(--panel);border:1px solid var(--border);color:var(--muted);
  padding:7px 15px;border-radius:8px;cursor:pointer;font-size:13.5px;font-weight:560;transition:.12s}
.tab:hover{color:var(--txt)}
.tab.active{background:var(--cong);color:#1a1500;border-color:var(--cong)}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));gap:12px;margin-bottom:24px}
.card{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:15px 16px;position:relative;overflow:hidden}
.card .bar{position:absolute;top:0;left:0;width:100%;height:3px}
.card.win{box-shadow:0 0 0 1px var(--cong),0 6px 24px -8px rgba(245,196,81,.4)}
.card .nm{font-size:12.5px;color:var(--muted);height:34px;font-weight:560}
.card .val{font-size:23px;font-weight:720;margin:6px 0 2px;letter-spacing:-.5px}
.card .ret{font-size:13.5px;font-weight:620}
.card .crown{position:absolute;top:11px;right:12px;font-size:15px}
.up{color:var(--good)} .down{color:var(--bad)}
.grid2{display:grid;grid-template-columns:1.55fr 1fr;gap:18px;margin-bottom:24px}
.panel{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:16px}
.panel h2{font-size:14px;margin:0 0 12px;font-weight:620;color:var(--txt)}
.chartbox{height:340px;position:relative}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:right;padding:7px 8px;border-bottom:1px solid var(--border);white-space:nowrap}
th:first-child,td:first-child{text-align:left}
th{color:var(--muted);font-weight:560;font-size:11.5px;text-transform:uppercase;letter-spacing:.4px}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px;vertical-align:middle}
.hold{display:flex;align-items:center;gap:9px;padding:5px 0;font-size:13px}
.hold .tk{font-weight:620;width:64px}
.hbar{flex:1;height:7px;background:var(--panel2);border-radius:4px;overflow:hidden}
.hbar > i{display:block;height:100%;background:var(--cong);border-radius:4px}
.hold .pct{width:46px;text-align:right;color:var(--muted)}
.trades td{font-size:12.5px}
.tag{font-size:11px;padding:1px 7px;border-radius:5px;background:rgba(63,185,80,.15);color:var(--good);font-weight:600}
footer{margin-top:30px;color:var(--muted);font-size:12px;border-top:1px solid var(--border);padding-top:16px}
footer b{color:var(--txt)}
.disc{background:#1a1410;border:1px solid #3a2a15;border-radius:8px;padding:12px 14px;color:#d9b88a;font-size:12.5px;margin-top:14px}
@media(max-width:820px){.cards{grid-template-columns:repeat(2,1fr)}.grid2{grid-template-columns:1fr}.meta{margin-left:0;text-align:left}}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div style="display:flex;align-items:center;gap:13px">
    <div class="brand">FT</div>
    <div>
      <h1>Finset&nbsp;Trading</h1>
      <div class="sub"><b style="color:var(--txt);font-weight:600">Kongress vs. Indeks</b> — lønner det seg å følge amerikanske politikeres aksjekjøp, eller å kjøpe indeksfond? Målt i kroner.</div>
    </div>
  </div>
  <div class="meta" id="meta"></div>
</header>

<div class="insight" id="insight"></div>
<div id="starnote" style="font-size:13px;margin:-8px 0 18px"></div>

<div class="tabs" id="tabs"></div>
<div class="cards" id="cards"></div>

<div class="grid2">
  <div class="panel">
    <h2>Verdiutvikling — 1 500 000 kr investert ved periodestart</h2>
    <div class="chartbox"><canvas id="chart"></canvas></div>
  </div>
  <div class="panel">
    <h2>Congress-porteføljens beholdning nå <span class="pill" id="holdcount"></span></h2>
    <div id="holdings"></div>
  </div>
</div>

<div class="panel" style="margin-bottom:24px">
  <h2>Nøkkeltall (valgt periode)</h2>
  <div style="overflow-x:auto"><table id="metrics"></table></div>
</div>

<div class="panel">
  <h2>Siste rapporterte kjøp fra politikerne</h2>
  <div style="overflow-x:auto"><table class="trades" id="trades"></table></div>
</div>

<footer>
  <div><b>Metode:</b> Congress-porteføljen holder hver måned de 20 aksjene med størst netto kjøp blant
  House-politikerne siste 12 måneder, vektet etter kjøpsstørrelse (maks 10 % per aksje).
  Handler legges inn på <b>publiseringsdato</b> (ikke politikerens hemmelige handelsdato) — opptil
  45 dagers forsinkelse er bakt inn. Amerikanske aksjer regnes i USD og veksles til NOK til daglig kurs.
  Kostnader med: kurtasje/spread (0,20 %) og valutapåslag (0,50 %) per rebalansering, samt utbytteskatt.
  Indeksfondene belastes årlig forvaltningshonorar. Avkastning er total (utbytte reinvestert).
  Risikotall: årlig svingning (volatilitet), største verdifall (drawdown) og Sharpe (avkastning per risiko).
  <b>Stjernetrader</b> følger hver måned den ene politikeren hvis kjøp har gjort det best frem til da
  (punkt-i-tid, uten å se i fasiten) — en ærlig test av om «følg den beste» faktisk fungerer.</div>
  <div class="disc"><b>Viktig:</b> Dette er en analyse / simulert papirportefølje — ikke ekte handel, og
  ingen kjøp eller salg utføres. Dette er ikke investeringsrådgivning og ingen anbefaling om å plassere
  ekte penger. Historisk avkastning er ingen garanti for fremtidig. Data: House-disclosures via
  house-stock-watcher, priser via Yahoo Finance. Senatet kommer som tillegg.</div>
</footer>
</div>

<script>
const DATA = /*__DATA__*/;
const COL = {}; const ORDER = [];
(function(){
  const c = DATA.congress_name;
  COL[c] = getComputedStyle(document.documentElement).getPropertyValue('--cong').trim();
  COL["S&P 500 (USA)"] = '#4493f8';
  COL["Globalt indeksfond (MSCI World)"] = '#3fb950';
  COL["Oslo Bors (OSEBX)"] = '#db6d28';
  if(DATA.star_name) COL[DATA.star_name] = '#bc8cff';
  ORDER.push(c);
  if(DATA.star_name) ORDER.push(DATA.star_name);
  ORDER.push("S&P 500 (USA)", "Globalt indeksfond (MSCI World)", "Oslo Bors (OSEBX)");
})();
const HORIZONS = [["live","Live siden "+(DATA.launch||'')],["max","Siden "+DATA.start.slice(0,4)],["5y","5 år"],["3y","3 år"],["1y","1 år"]];
const CAP = DATA.capital_nok;
const fmt = n => Math.round(n).toLocaleString('nb-NO');
const pct = n => (n>=0?'+':'')+(n*100).toFixed(1)+' %';
let sel = 'max', chart;

function metricFor(name,h){ const m=DATA.strategies[name].metrics; return m[h]||m['max']; }

function sliceSeries(name,h){
  const s = DATA.strategies[name].series;
  const m = metricFor(name,h);
  const from = m.from;
  const cut = s.filter(p=>p[0]>=from);
  const base = cut.length?cut[0][1]:1;
  return cut.map(p=>[p[0], p[1]/base*CAP]);   // rebase to 1.5M at window start
}

function renderTabs(){
  const t = document.getElementById('tabs'); t.innerHTML='';
  HORIZONS.forEach(([h,lab])=>{
    if(!DATA.strategies[DATA.congress_name].metrics[h]) return;
    const b=document.createElement('div'); b.className='tab'+(h===sel?' active':'');
    b.textContent=lab; b.onclick=()=>{sel=h;renderAll();}; t.appendChild(b);
  });
}

function renderCards(){
  const rows = ORDER.map(n=>[n,metricFor(n,sel)]).sort((a,b)=>b[1].end_value-a[1].end_value);
  const win = rows[0][0];
  const el=document.getElementById('cards'); el.innerHTML='';
  rows.forEach(([n,m])=>{
    const d=document.createElement('div'); d.className='card'+(n===win?' win':'');
    d.innerHTML=`<div class="bar" style="background:${COL[n]}"></div>
      ${n===win?'<div class="crown">👑</div>':''}
      <div class="nm">${n}</div>
      <div class="val">${fmt(m.end_value)} kr</div>
      <div class="ret ${m.total_return>=0?'up':'down'}">${pct(m.total_return)} · ${(m.cagr*100).toFixed(1)} %/år</div>`;
    el.appendChild(d);
  });
}

function renderMetrics(){
  const rows = ORDER.map(n=>[n,metricFor(n,sel)]).sort((a,b)=>b[1].end_value-a[1].end_value);
  const t=document.getElementById('metrics');
  t.innerHTML=`<tr><th>Strategi</th><th>Sluttverdi</th><th>Avkastning</th><th>Pr. år</th>
    <th>Svingning</th><th>Største fall</th><th>Sharpe</th></tr>`+
    rows.map(([n,m])=>`<tr>
      <td><span class="dot" style="background:${COL[n]}"></span>${n}</td>
      <td><b>${fmt(m.end_value)}</b></td>
      <td class="${m.total_return>=0?'up':'down'}">${pct(m.total_return)}</td>
      <td>${(m.cagr*100).toFixed(1)} %</td>
      <td>${(m.vol*100).toFixed(1)} %</td>
      <td class="down">${(m.max_drawdown*100).toFixed(1)} %</td>
      <td>${m.sharpe.toFixed(2)}</td></tr>`).join('');
}

function renderChart(){
  const ds = ORDER.map(n=>{
    const s=sliceSeries(n,sel);
    return {label:n,data:s.map(p=>({x:p[0],y:p[1]})),borderColor:COL[n],
      backgroundColor:COL[n],borderWidth:n===DATA.congress_name?2.4:1.6,
      pointRadius:0,tension:.12};
  });
  if(chart) chart.destroy();
  chart=new Chart(document.getElementById('chart'),{type:'line',
    data:{datasets:ds},
    options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},
      plugins:{legend:{labels:{color:'#8b949e',boxWidth:12,font:{size:11.5}}},
        tooltip:{callbacks:{label:c=>c.dataset.label+': '+fmt(c.parsed.y)+' kr'}}},
      scales:{
        x:{type:'time',time:{unit: sel==='1y'?'month':'year'},ticks:{color:'#8b949e',maxRotation:0},grid:{color:'#21262d'}},
        y:{ticks:{color:'#8b949e',callback:v=>(v/1e6).toFixed(1)+' M'},grid:{color:'#21262d'}}}}});
}

function renderHoldings(){
  const h=DATA.holdings.slice(0,12); const mx=h.length?h[0].weight:1;
  document.getElementById('holdcount').textContent=DATA.holdings.length+' aksjer';
  document.getElementById('holdings').innerHTML=h.map(x=>`<div class="hold">
    <span class="tk">${x.ticker}</span>
    <span class="hbar"><i style="width:${(x.weight/mx*100).toFixed(0)}%"></i></span>
    <span class="pct">${(x.weight*100).toFixed(1)} %</span></div>`).join('');
}

function renderTrades(){
  const t=document.getElementById('trades');
  t.innerHTML=`<tr><th>Publisert</th><th>Politiker</th><th>Aksje</th><th>Beløp (≈USD)</th></tr>`+
    DATA.latest_buys.map(b=>`<tr>
      <td>${b.pub_date}</td><td>${b.politician||'—'}</td>
      <td><span class="tag">KJØP</span> ${b.ticker}</td>
      <td>${fmt(b.amount_mid)} $</td></tr>`).join('');
}

function renderMeta(){
  document.getElementById('meta').innerHTML=
    `<span class="pill">Priser t.o.m. ${DATA.data_through}</span><br>`+
    `<span style="font-size:11.5px">Oppdatert ${DATA.generated_at} · siste politiker-handel ${DATA.latest_trade||'—'} · ${fmt(DATA.n_trades)} handler · House</span>`;
  document.getElementById('insight').innerHTML='💡 '+DATA.insight;
  const sn=document.getElementById('starnote');
  if(DATA.star_current&&sn){
    sn.innerHTML=`<span style="display:inline-block;width:9px;height:9px;border-radius:50%;background:${COL[DATA.star_name]};margin-right:7px;vertical-align:middle"></span>`+
      `<b style="color:var(--txt)">Stjernetrader</b> følger nå <b style="color:var(--txt)">${DATA.star_current}</b> `+
      `<span style="color:var(--muted)">— bytter hver måned til politikeren med best resultat frem til da (punkt-i-tid, ingen fasit).</span>`;
  }
}

function renderAll(){renderTabs();renderCards();renderMetrics();renderChart();}
renderMeta();renderHoldings();renderTrades();renderAll();
</script>
</body>
</html>"""


if __name__ == "__main__":
    build()
