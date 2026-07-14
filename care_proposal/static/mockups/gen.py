# -*- coding: utf-8 -*-
"""Generate high-fidelity PNG mockups for the Care Proposal redesign.
Rendered with wkhtmltoimage (QtWebKit) -> avoid flexbox/grid/var(); use
tables, inline-block, fixed widths, gradients, border-radius, box-shadow."""
import os, subprocess

OUT = os.path.dirname(os.path.abspath(__file__))
W = 1280

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'DejaVu Sans',Arial,Helvetica,sans-serif;background:#eef2f7;color:#0f172a;width:1280px}
.top{background:#0b1220;color:#fff;height:54px;padding:0 20px;line-height:54px}
.top .brand{font-weight:bold;font-size:18px;color:#7dd3fc;display:inline-block}
.top .crumb{color:#94a3b8;font-size:13px;display:inline-block;margin-left:14px}
.top .user{float:right;color:#cbd5e1;font-size:13px}
.top .pill{display:inline-block;background:#1e293b;color:#7dd3fc;border-radius:12px;padding:2px 10px;font-size:12px;margin-left:8px}
.page{padding:22px 24px}
.h1{font-size:22px;font-weight:bold;margin-bottom:2px}
.sub{color:#64748b;font-size:13px;margin-bottom:18px}
.card{display:inline-block;vertical-align:top;background:#fff;border:1px solid #e2e8f0;border-radius:12px;
      box-shadow:0 1px 3px rgba(15,23,42,.06);padding:16px;margin:0 14px 16px 0}
.card .ct{color:#64748b;font-size:12px;text-transform:uppercase;letter-spacing:.4px;margin-bottom:8px}
.kpi .big{font-size:28px;font-weight:bold}
.kpi .d{font-size:12px;margin-top:4px}
.up{color:#16a34a}.down{color:#dc2626}.mut{color:#94a3b8}
.btn{display:inline-block;border-radius:8px;padding:7px 14px;font-size:13px;border:1px solid #cbd5e1;background:#fff;color:#0f172a;margin-right:8px}
.btn.p{background:#4f46e5;border-color:#4f46e5;color:#fff}
.btn.g{background:#16a34a;border-color:#16a34a;color:#fff}
.btn.w{background:#f59e0b;border-color:#f59e0b;color:#fff}
.badge{display:inline-block;border-radius:20px;padding:2px 10px;font-size:12px;font-weight:bold}
.bg-green{background:#dcfce7;color:#166534}.bg-amber{background:#fef3c7;color:#92400e}
.bg-red{background:#fee2e2;color:#991b1b}.bg-blue{background:#dbeafe;color:#1e40af}
.bg-slate{background:#e2e8f0;color:#334155}.bg-indigo{background:#e0e7ff;color:#3730a3}
table{border-collapse:collapse;width:100%}
th{background:#f1f5f9;color:#475569;font-size:11px;text-transform:uppercase;letter-spacing:.3px;text-align:left;padding:9px 10px;border-bottom:1px solid #e2e8f0}
td{padding:10px;border-bottom:1px solid #eef2f7;font-size:13px}
.bar{height:14px;border-radius:7px;background:#4f46e5;display:inline-block;vertical-align:middle}
.bar2{background:#0ea5e9}.bar3{background:#10b981}.bar4{background:#f59e0b}.bar5{background:#64748b}
.barbg{background:#eef2f7;border-radius:7px;display:inline-block;width:170px;height:14px;vertical-align:middle;margin-right:8px}
.barbg .bar{display:block}
.stage{display:inline-block;padding:6px 16px;border-radius:20px;background:#e2e8f0;color:#475569;font-size:12px;margin-right:6px}
.stage.on{background:#4f46e5;color:#fff}
.stage.done{background:#c7d2fe;color:#3730a3}
.sec{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:0;margin-bottom:16px;overflow:hidden}
.sec .hd{padding:12px 16px;border-bottom:1px solid #eef2f7;font-weight:bold;font-size:14px;background:#fbfcfe}
.sec .bd{padding:14px 16px}
.tabbar{border-bottom:2px solid #e2e8f0;margin:6px 0 14px}
.tab{display:inline-block;padding:8px 14px;font-size:13px;color:#64748b}
.tab.on{color:#4f46e5;border-bottom:2px solid #4f46e5;font-weight:bold;margin-bottom:-2px}
.kv{font-size:13px;line-height:26px}
.kv b{color:#475569;display:inline-block;width:130px;font-weight:600}
.mono{font-family:'DejaVu Sans Mono',monospace}
.right{text-align:right}.center{text-align:center}
.small{font-size:12px;color:#64748b}
.chip{display:inline-block;background:#eef2ff;color:#4338ca;border:1px solid #c7d2fe;border-radius:8px;padding:3px 9px;font-size:12px;margin:2px}
.panel{background:#0b1220;color:#e2e8f0;border-radius:12px;padding:14px 16px}
.panel .big{font-size:22px;font-weight:bold;color:#fff}
.warn{background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;border-radius:8px;padding:8px 12px;font-size:12px;margin-top:8px}
.radio{display:inline-block;border:1px solid #cbd5e1;border-radius:8px;padding:7px 12px;font-size:13px;margin-right:8px;color:#475569}
.radio.on{border-color:#4f46e5;background:#eef2ff;color:#3730a3;font-weight:bold}
.dim{opacity:.55}
"""

def shell(title, crumb, body):
    return f"""<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>
<div class='top'><span class='brand'>CARE • Proposals</span>
<span class='crumb'>{crumb}</span><span class='user'>◐ Sara — Care Cleaning Co. ▾</span></div>
<div class='page'>{body}</div></body></html>"""

def barrow(label, pct, val, cls="bar", w=170):
    px = int(pct/100.0*w)
    return (f"<div style='margin:7px 0'><span style='display:inline-block;width:120px;font-size:13px'>{label}</span>"
            f"<span class='barbg' style='width:{w}px'><span class='{cls}' style='width:{px}px'></span></span>"
            f"<span class='small' style='margin-left:8px'>{val}</span></div>")

screens = []

# 1) DASHBOARD
kpis = "".join([
 "<div class='card kpi'><div class='ct'>Pipeline Value</div><div class='big'>KWD 1,240,500</div><div class='d up'>▲ 12% vs last quarter</div></div>",
 "<div class='card kpi'><div class='ct'>Win Rate</div><div class='big'>38%</div><div class='d mut'>19 / 50 won</div></div>",
 "<div class='card kpi'><div class='ct'>Avg Margin</div><div class='big'>22.4%</div><div class='d down'>▼ 1.1 pts</div></div>",
 "<div class='card kpi'><div class='ct'>Expiring ≤ 7d</div><div class='big'>6</div><div class='d mut'>KWD 88,200</div></div>",
 "<div class='card kpi'><div class='ct'>Awaiting Approval</div><div class='big'>4</div><div class='d mut'>your action</div></div>",
])
stagechart = "".join([barrow("Draft",30,"14 · 120k","bar"),barrow("Submitted",20,"8 · 90k","bar2"),
 barrow("Approval",14,"4 · 62k","bar4"),barrow("Won",90,"19 · 410k","bar3"),barrow("Lost",16,"7 · 80k","bar5")])
typechart = "".join([barrow("Cleaning",100,"540k","bar"),barrow("Security",60,"320k","bar2"),
 barrow("Manpower",40,"210k","bar3"),barrow("Hospitality",18,"95k","bar4"),barrow("Other",14,"75k","bar5")])
trend = """<svg width='560' height='150'>
<polyline points='10,120 100,90 190,100 280,55 370,70 460,40 550,60' style='fill:none;stroke:#4f46e5;stroke-width:3'/>
<polyline points='10,135 100,120 190,128 280,100 370,112 460,92 550,105' style='fill:none;stroke:#10b981;stroke-width:3'/>
<text x='10' y='148' style='font-size:11px;fill:#94a3b8'>Jan</text><text x='100' y='148' style='font-size:11px;fill:#94a3b8'>Feb</text>
<text x='190' y='148' style='font-size:11px;fill:#94a3b8'>Mar</text><text x='280' y='148' style='font-size:11px;fill:#94a3b8'>Apr</text>
<text x='370' y='148' style='font-size:11px;fill:#94a3b8'>May</text><text x='460' y='148' style='font-size:11px;fill:#94a3b8'>Jun</text></svg>
<div class='small'><span style='color:#4f46e5'>● value</span> &nbsp; <span style='color:#10b981'>● won</span></div>"""
attention = """<div style='font-size:13px;line-height:30px'>
<span class='badge bg-amber'>⚠ 6</span> proposals expiring in 7 days<br>
<span class='badge bg-blue'>⏳ 4</span> awaiting your approval<br>
<span class='badge bg-red'>✎ 3</span> margin &lt; 10% — review<br>
<span class='badge bg-slate'>↻ 2</span> reference cost outdated</div>"""
topcust = """<table><tr><th>#</th><th>Customer</th><th class='right'>Value</th><th class='right'>Props</th></tr>
<tr><td>1</td><td>Ministry of Health</td><td class='right'>210,000</td><td class='right'>4</td></tr>
<tr><td>2</td><td>KOC</td><td class='right'>180,000</td><td class='right'>3</td></tr>
<tr><td>3</td><td>Amiri Diwan</td><td class='right'>145,000</td><td class='right'>2</td></tr>
<tr><td>4</td><td>Municipality</td><td class='right'>98,000</td><td class='right'>5</td></tr></table>"""
body = f"""<div class='h1'>Dashboard</div><div class='sub'>Company: Care Cleaning Co. · This Quarter · live</div>
{kpis}
<div class='card' style='width:600px'><div class='ct'>Pipeline by Stage</div>{stagechart}</div>
<div class='card' style='width:600px'><div class='ct'>Value by Service Type</div>{typechart}</div>
<div class='card' style='width:600px'><div class='ct'>Monthly Trend (value &amp; count)</div>{trend}</div>
<div class='card' style='width:285px'><div class='ct'>Needs Attention</div>{attention}</div>
<div class='card' style='width:285px'><div class='ct'>Top Customers</div>{topcust}</div>
<div class='card' style='width:1198px'><div class='ct'>KPIs</div>
<span class='chip'>Avg cycle draft→won 9.4d</span><span class='chip'>Approval SLA 1.8d</span>
<span class='chip'>Expected value (Σ margin×win%) KWD 286k</span><span class='chip'>Revisions / proposal 1.7</span>
<span class='chip'>Quotes sent this month 23</span><span class='chip'>Acceptance rate 41%</span></div>"""
screens.append(("01_dashboard","Dashboard", shell("Dashboard","Proposals › Dashboard",body)))

# 2) PROPOSAL LIST
rows = [
 ("PROP00231","Ministry of Health","Cleaning","210,000","24%","bg-green","12 Jul","Won","bg-green","v2"),
 ("PROP00230","KOC","Security","88,200","9%","bg-red","28 Jun","Approval","bg-blue","v1"),
 ("PROP00229","Amiri Diwan","Hospitality","41,000","31%","bg-green","05 Jul","Draft","bg-slate","v1"),
 ("PROP00228","Municipality","Manpower","63,500","17%","bg-amber","02 Jul","Submitted","bg-amber","v1"),
 ("PROP00227","Gulf Bank","Cleaning","120,000","26%","bg-green","19 Jul","Won","bg-green","v3"),
 ("PROP00226","KNPC","Security","95,400","12%","bg-amber","21 Jun","Lost","bg-red","v2"),
]
trs=""
for r in rows:
    trs+=(f"<tr><td class='mono'>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td class='right'>{r[3]}</td>"
          f"<td class='center'><span class='badge {r[5]}'>{r[4]}</span></td><td>{r[6]}</td>"
          f"<td><span class='badge {r[8]}'>{r[7]}</span></td><td class='center'>{r[9]}</td></tr>")
body=f"""<div class='h1'>Proposals</div>
<div style='margin-bottom:14px'><span class='btn p'>＋ New</span>
<span class='btn'>My</span><span class='btn'>Awaiting me</span><span class='btn'>Expiring</span><span class='btn'>Won</span>
<span style='float:right' class='btn'>≣ List</span><span style='float:right' class='btn'>▦ Kanban</span></div>
<div class='sec'><table>
<tr><th>Ref</th><th>Customer</th><th>Service Type</th><th class='right'>Value</th><th class='center'>Margin</th><th>Valid</th><th>Stage</th><th class='center'>Rev</th></tr>
{trs}</table></div>
<div class='small'>Margin badge: <span class='badge bg-green'>≥20%</span> <span class='badge bg-amber'>10–20%</span> <span class='badge bg-red'>&lt;10%</span></div>"""
screens.append(("02_list","Proposals List", shell("Proposals","Proposals › All",body)))

# 3) PROPOSAL FORM
body=f"""<div style='margin-bottom:10px'>
<span class='btn p'>Submit</span><span class='btn'>Send ✉</span><span class='btn g'>Approve</span>
<span class='btn'>Reject</span><span class='btn g'>Won</span>
<span style='float:right' class='btn'>⋯</span><span style='float:right' class='btn'>New Revision</span><span style='float:right' class='btn'>Duplicate</span></div>
<div style='margin-bottom:14px'>
<span class='stage done'>Draft</span><span class='stage done'>Submitted</span><span class='stage on'>Approval</span>
<span class='stage'>Approved</span><span class='stage'>Won</span>
<span style='float:right' class='badge bg-green' style='font-size:13px'>Margin 24%</span></div>
<div class='h1'>PROP00231 · Ministry of Health — Cleaning <span class='badge bg-indigo'>v2</span></div>
<div class='sub'>Quotation for cleaning services · Sabah Hospital</div>
<div class='card' style='width:585px'>
<div class='kv'><b>Customer</b> Ministry of Health</div><div class='kv'><b>Contact</b> Ahmed Ali · +965 …</div>
<div class='kv'><b>Proposal #</b> <span class='mono'>PROP00231</span></div><div class='kv'><b>Date</b> 22-Jun-2026</div>
<div class='kv'><b>Valid to</b> 12-Jul-2026 <span class='badge bg-amber'>20 days</span></div>
<div class='kv'><b>CRM Lead</b> OPP/Cleaning MoH ↗</div><div class='kv'><b>Salesperson</b> ◐ Sara</div></div>
<div class='card' style='width:585px'>
<div class='kv'><b>Service Type</b> Cleaning</div><div class='kv'><b>Site / City</b> Sabah Hospital · Kuwait</div>
<div class='kv'><b>Mobilization</b> 01-Aug-2026</div><div class='kv'><b>Period</b> 12 months · Billing Monthly</div>
<div class='kv'><b>Currency</b> KWD</div><div class='kv'><b>Revision of</b> PROP00231 v1 ↗</div></div>
<div class='tabbar'><span class='tab on'>Pricing</span><span class='tab'>Services</span><span class='tab'>Manpower</span>
<span class='tab'>Materials &amp; Equip</span><span class='tab'>Transport</span><span class='tab'>Scope</span>
<span class='tab'>Terms</span><span class='tab'>Approvals</span><span class='tab'>Print</span><span class='tab'>Analysis</span></div>
<div class='panel' style='width:1198px'>
<table style='color:#e2e8f0'><tr>
<td style='border:none'><div class='small' style='color:#94a3b8'>COST</div><div class='big'>KWD 159,600</div></td>
<td style='border:none'><div class='small' style='color:#94a3b8'>MARGIN</div><div class='big'>KWD 50,400 · 24%</div></td>
<td style='border:none'><div class='small' style='color:#94a3b8'>PRICE</div><div class='big'>KWD 210,000</div></td>
<td style='border:none'><div class='small' style='color:#94a3b8'>EXPECTED (×win 60%)</div><div class='big'>KWD 30,240</div></td>
</tr></table></div>"""
screens.append(("03_form","Proposal Form", shell("Proposal","Proposals › PROP00231",body)))

# 4) PRICING WORKSPACE
prows=[
 ("Cleaner – day shift","60","180.000","+12 +4 +6","202.0","24%","bg-green","250.5","15,030"),
 ("Cleaner – night","20","195.000","+12 +4 +9","220.0","18%","bg-amber","259.6","5,192"),
 ("Supervisor","4","420.000","+0 +0 +6","426.0","30%","bg-green","554.0","2,216"),
]
ptr=""
for r in prows:
    ptr+=(f"<tr><td>{r[0]}</td><td class='right'>{r[1]}</td><td class='right mono'>{r[2]}</td>"
          f"<td class='center small'>{r[3]}</td><td class='right'>{r[4]}</td>"
          f"<td class='center'><span class='badge {r[6]}'>{r[5]}</span></td>"
          f"<td class='right'>{r[7]}</td><td class='right'><b>{r[8]}</b></td></tr>")
build="".join([f"<div class='kv'><b>{k}</b> {v}</div>" for k,v in
 [("Salary","140.0"),("Residency","18.0"),("Accommodation","12.0"),("Uniform","6.0"),("Insurance","4.0"),
  ("Mat allocated","12.0"),("Equip allocated","4.0"),("Transport allocated","6.0")]])
body=f"""<div class='h1'>Pricing Workspace <span class='small'>— PROP00231</span></div>
<div class='sub'>Frozen cost snapshot · catalog edits never change this proposal</div>
<div style='margin-bottom:12px'>
<span class='radio'>Cost-plus %</span><span class='radio on'>Target margin %</span><span class='radio'>Target price</span><span class='radio'>Manual</span>
<span style='float:right' class='btn'>↻ Re-sync catalog</span>
<span class='chip'>Global margin: 24%</span><span class='chip'>Round to: 1 KWD</span><span class='chip'>Apply to: All lines</span></div>
<div class='sec'><table>
<tr><th>Service line (frozen)</th><th class='right'>Qty</th><th class='right'>Unit cost</th><th class='center'>+Mat +Eq +Tr</th>
<th class='right'>Cost/u</th><th class='center'>Margin</th><th class='right'>Price/u</th><th class='right'>Total</th></tr>
{ptr}</table></div>
<div class='warn'>⚠ "Cleaner – night" margin 18% &lt; threshold 20% → manager approval required on submit</div>
<div class='card' style='width:430px;margin-top:14px'><div class='ct'>Cost build-up (selected · from snapshot)</div>{build}</div>
<div class='card' style='width:430px;margin-top:14px'><div class='ct'>Price Scenarios</div>
<div class='kv'><span class='radio'>Economy · 15%</span> KWD 198,000</div>
<div class='kv'><span class='radio on'>Standard · 24%</span> KWD 210,000</div>
<div class='kv'><span class='radio'>Premium · 32%</span> KWD 228,000</div>
<div style='margin-top:8px'><span class='btn'>Save scenario</span><span class='btn'>Compare</span></div></div>"""
screens.append(("04_pricing","Pricing Workspace", shell("Pricing Workspace","Proposals › PROP00231 › Pricing",body)))

# 5) SERVICE CATALOG
comp="".join([f"<tr><td>{t}</td><td class='right mono'>{c}</td><td class='small'>{n}</td></tr>" for t,c,n in
 [("Salary","140.0","base"),("Residency","18.0",""),("Accommodation","12.0",""),("Uniform","6.0",""),("Insurance","4.0","")]])
books="""<tr><td>Default</td><td class='right'>176.0</td><td class='small'>—</td></tr>
<tr><td>Ministry of Health</td><td class='right'>199.0</td><td class='small'>eff 01-Jan-26</td></tr>
<tr><td>KOC</td><td class='right'>162.0</td><td class='small'>eff 01-Jan-26</td></tr>"""
body=f"""<div class='h1'>Service Catalog</div><div class='sub'>Definition only · cost types are configurable</div>
<div class='card' style='width:585px'>
<div class='kv'><b>Service</b> Cleaner – day shift</div><div class='kv'><b>Type</b> <span class='badge bg-indigo'>Manpower</span></div>
<div class='kv'><b>Code</b> CLN-D</div><div class='kv'><b>UoM</b> worker</div><div class='kv'><b>Hours/day</b> 8 · <b>Days/wk</b> 6</div>
<div class='ct' style='margin-top:10px'>Default cost components (template)</div>
<table><tr><th>Component</th><th class='right'>Cost</th><th>Note</th></tr>{comp}</table>
<div style='margin-top:8px'><span class='btn'>＋ component</span></div></div>
<div class='card' style='width:585px'>
<div class='ct'>Cost Books for this service</div>
<table><tr><th>Customer</th><th class='right'>Total/worker</th><th>Effective</th></tr>{books}</table>
<div style='margin-top:8px'><span class='btn p'>＋ Customer book</span></div>
<div class='warn' style='margin-top:14px'>ⓘ Editing here changes only NEW proposals/books. Existing proposals stay frozen.
Use "Re-sync" inside a proposal to pull new costs deliberately.</div></div>"""
screens.append(("05_catalog","Service Catalog", shell("Service Catalog","Configuration › Services",body)))

# 6) CUSTOMER COST BOOK
cb="".join([f"<tr><td>{c}</td><td class='right'>{d}</td><td class='right'><b>{m}</b></td><td class='center {cl}'>{delta}</td><td class='small'>{note}</td></tr>"
 for c,d,m,delta,cl,note in [
 ("Salary","140.0","155.0","+15.0","up","site allowance"),
 ("Residency","18.0","18.0","—","mut",""),
 ("Accommodation","12.0","20.0","+8.0","up","on-site housing"),
 ("Uniform","6.0","6.0","—","mut",""),
 ("Insurance","4.0","6.0","+2.0","up","high-risk site")]])
body=f"""<div class='h1'>Cost Book · Ministry of Health</div>
<div class='sub'>Same service, customer-specific cost · dated versions · frozen into proposals</div>
<div class='card' style='width:1198px'>
<div class='kv'><b>Service</b> Cleaner – day shift &nbsp;&nbsp; <b style='width:90px'>Effective</b> 01-Jan-2026 &nbsp;&nbsp; <b style='width:70px'>Currency</b> KWD</div>
<table style='margin-top:10px'><tr><th>Component</th><th class='right'>Default</th><th class='right'>This customer</th><th class='center'>Δ</th><th>Note</th></tr>
{cb}
<tr style='background:#f8fafc'><td><b>Total / worker</b></td><td class='right'>176.0</td><td class='right'><b>205.0</b></td><td class='center up'>+29.0</td><td></td></tr></table>
<div style='margin-top:12px' class='small'>Version history:
<span class='chip'>v3 · 01-Jan-26 (active)</span><span class='chip'>v2 · 01-Jul-25</span><span class='chip'>v1 · 01-Jan-25</span></div></div>"""
screens.append(("06_costbook","Customer Cost Book", shell("Cost Book","Configuration › Cost Books",body)))

# 7) CRM
body=f"""<div class='h1'>Opportunity · Cleaning MoH</div>
<div style='margin-bottom:12px'><span class='stage'>New</span><span class='stage done'>Qualified</span>
<span class='stage on'>Proposition</span><span class='stage'>Won</span>
<span style='float:right' class='badge bg-blue'>Proposals 2 · Won 1</span></div>
<div style='margin-bottom:14px'><span class='btn p'>＋ Create Proposal ▾</span><span class='btn'>New Revision</span>
<span class='small'>menu: blank · from template · copy winning bid</span></div>
<div class='card' style='width:1198px'>
<div class='kv'><b>Expected revenue</b> <b style='width:auto'>KWD 210,000</b> <span class='small'>⟵ auto from winning proposal</span></div>
<table style='margin-top:10px'><tr><th>Proposal</th><th>Service</th><th class='right'>Value</th><th class='center'>Margin</th><th>Status</th><th></th></tr>
<tr><td class='mono'>PROP00231 v2</td><td>Cleaning</td><td class='right'>210,000</td><td class='center'><span class='badge bg-green'>24%</span></td><td><span class='badge bg-blue'>Approval</span></td><td><span class='badge bg-amber'>★ winning</span></td></tr>
<tr class='dim'><td class='mono'>PROP00231 v1</td><td>Cleaning</td><td class='right'>198,000</td><td class='center'>19%</td><td><span class='badge bg-slate'>Superseded</span></td><td></td></tr>
<tr><td class='mono'>PROP00188</td><td>Security</td><td class='right'>88,200</td><td class='center'>9%</td><td><span class='badge bg-red'>Lost</span></td><td></td></tr></table>
<div class='warn' style='margin-top:12px'>Sync: proposal Won → lead Won + revenue · lead Lost → proposals Lost ·
★ winning_proposal drives expected_revenue · activities mirrored</div></div>"""
screens.append(("07_crm","CRM Integration", shell("CRM","CRM › Opportunity",body)))

# 8) DUPLICATE DIALOG
body=f"""<div class='h1'>&nbsp;</div>
<div class='card' style='width:520px;margin:40px auto;display:block'>
<div style='font-size:16px;font-weight:bold;margin-bottom:14px'>Duplicate / Revise — PROP00231</div>
<div class='radio'>Exact copy (new ref, Draft)</div><br><br>
<div class='radio on'>New revision of PROP00231 → becomes v3</div><br><br>
<div class='radio'>Copy to another customer ▸ [ select… ]</div>
<div class='small' style='margin:6px 0 14px 10px'>└ re-price using that customer's Cost Book</div>
<div style='font-size:13px;line-height:28px'>
<span class='chip'>✔ services</span><span class='chip'>✔ cost lines</span>
<span class='chip'>✗ manual price overrides</span><span class='chip'>✔ scope/terms</span></div>
<div style='margin-top:16px;text-align:right'><span class='btn'>Cancel</span><span class='btn p'>Create →</span></div></div>"""
screens.append(("08_duplicate","Duplicate / Revision", shell("Duplicate","Proposals › Duplicate",body)))

# 9) CUSTOMER PDF
body=f"""<div class='h1'>Customer Proposal — PDF preview</div><div class='sub'>Per-company branding · service-type-aware price table</div>
<div class='card' style='width:760px;margin:0 auto;display:block'>
<div style='text-align:center;border-bottom:2px solid #4f46e5;padding-bottom:10px;margin-bottom:14px'>
<div style='font-size:20px;font-weight:bold;color:#4f46e5'>CARE CLEANING CO.</div>
<div class='small'>[ company logo &amp; header from res.company ]</div></div>
<div class='kv'><b>Proposal for</b> Ministry of Health &nbsp;&nbsp; <b style='width:60px'>Ref</b> PROP00231 v2</div>
<div class='kv'><b>Valid until</b> 12-Jul-2026 &nbsp;&nbsp; <b style='width:60px'>Date</b> 22-Jun-2026</div>
<div class='ct' style='margin-top:12px'>▸ Manpower services</div>
<table><tr><th>#</th><th>Location</th><th>Role</th><th class='center'>Hrs/d</th><th class='center'>Days/wk</th><th class='right'>Qty</th><th class='right'>Price</th><th class='right'>Total</th></tr>
<tr><td>1</td><td>Sabah H.</td><td>Cleaner day</td><td class='center'>8</td><td class='center'>6</td><td class='right'>60</td><td class='right'>250.5</td><td class='right'>15,030</td></tr></table>
<div class='ct' style='margin-top:10px'>▸ Fixed services <span class='small'>(no hrs/days columns)</span></div>
<table><tr><th>#</th><th>Location</th><th>Service</th><th class='center'>Unit</th><th class='right'>Qty</th><th class='right'>Price</th><th class='right'>Total</th></tr>
<tr><td>1</td><td>Sabah H.</td><td>Deep disinfection</td><td class='center'>visit</td><td class='right'>4</td><td class='right'>900</td><td class='right'>3,600</td></tr></table>
<div style='text-align:right;font-size:16px;font-weight:bold;margin-top:12px;color:#4f46e5'>GRAND TOTAL &nbsp; KWD 210,000</div>
<div class='small' style='margin-top:10px;border-top:1px solid #e2e8f0;padding-top:8px'>Terms · Acceptance (signature) · [ company footer + QR ]</div></div>"""
screens.append(("09_report","Customer PDF", shell("Customer PDF","Proposals › Report",body)))

# 10) SETTINGS
body=f"""<div class='h1'>Proposal Settings</div><div class='sub'>Pricing, approvals, CRM, reports</div>
<div class='sec' style='width:1198px'><div class='hd'>Pricing</div><div class='bd'>
<div class='kv'><b>Default strategy</b> Target margin · default 20%</div>
<div class='kv'><b>Margin guard</b> below 10% → require manager approval</div>
<div class='kv'><b>Round price to</b> 1.000 KWD</div>
<div class='kv'><b>Cost components</b> <span class='chip'>salary</span><span class='chip'>residency</span><span class='chip'>uniform</span><span class='chip'>insurance</span><span class='chip'>+ add</span></div></div></div>
<div class='sec' style='width:585px'><div class='hd'>Approval matrix (by amount)</div><div class='bd'>
<div class='kv'><b>≤ 50k</b> auto-approve</div><div class='kv'><b>50–200k</b> manager</div><div class='kv'><b>&gt; 200k</b> general manager</div></div></div>
<div class='sec' style='width:585px;margin-left:14px'><div class='hd'>CRM &amp; Reports</div><div class='bd'>
<div class='kv'>✔ sync stage &nbsp; ✔ rollup revenue &nbsp; ✔ mark lead won</div>
<div class='kv'><b>Reports</b> per-company branding profiles</div>
<div class='kv'><b>Numbering</b> PROP##### · revisions vN</div></div></div>"""
screens.append(("10_settings","Settings", shell("Settings","Configuration › Settings",body)))

# render all
links=[]
for fn,title,htmlsrc in screens:
    hp=os.path.join(OUT,fn+".html"); pp=os.path.join(OUT,fn+".png")
    open(hp,"w",encoding="utf-8").write(htmlsrc)
    subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access",
        "--disable-smart-width","--width",str(W),"--quality","92",hp,pp],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(hp)
    links.append((fn+".png",title))
    print("rendered",fn+".png")

# gallery
cards="".join([f"""<div style='margin:0 0 28px'>
<div style='font-weight:bold;font-size:16px;color:#0f172a;margin:6px 0'>{i+1}. {t}</div>
<a href='{f}'><img src='{f}' style='width:100%;border:1px solid #e2e8f0;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.08)'></a></div>"""
 for i,(f,t) in enumerate(links)])
gal=f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Care Proposal — Visual Mockups</title>
<style>body{{background:#f1f5f9;font-family:Arial;margin:0}}.w{{max-width:980px;margin:0 auto;padding:24px}}
h1{{color:#1e293b}}.s{{color:#64748b;margin-bottom:20px}}</style></head>
<body><div class='w'><h1>Care Proposal — Visual Mockups</h1>
<div class='s'>Redesign concept · {len(links)} screens · click any image to enlarge</div>{cards}</div></body></html>"""
open(os.path.join(OUT,"index.html"),"w",encoding="utf-8").write(gal)
print("gallery written:",len(links),"screens")
