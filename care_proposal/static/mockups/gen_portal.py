# -*- coding: utf-8 -*-
"""Customer Service-Request Portal — visual mockups (wkhtmltoimage friendly)."""
import os, subprocess
OUT=os.path.dirname(os.path.abspath(__file__)); W=1180

CSS="""
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'DejaVu Sans',Arial,sans-serif;background:#f4f7fb;color:#0f172a;width:1180px}
.nav{background:#fff;border-bottom:1px solid #e5eaf1;height:60px;padding:0 28px;line-height:60px}
.nav .logo{font-weight:bold;font-size:19px;color:#0ea5e9;display:inline-block}
.nav .lk{display:inline-block;margin-left:22px;color:#475569;font-size:14px}
.nav .lk.on{color:#0ea5e9;font-weight:bold}
.nav .acc{float:right;color:#475569;font-size:14px}
.hero{background:#0b1220;color:#fff;padding:34px 28px}
.hero h1{font-size:26px;margin-bottom:6px}.hero p{color:#9fb3c8;font-size:15px}
.wrap{padding:24px 28px}
.h1{font-size:23px;font-weight:bold;margin-bottom:2px}
.sub{color:#64748b;font-size:14px;margin-bottom:18px}
.card{display:inline-block;vertical-align:top;background:#fff;border:1px solid #e5eaf1;border-radius:14px;
 box-shadow:0 1px 4px rgba(15,23,42,.06);padding:18px;margin:0 16px 18px 0}
.svc{width:255px;text-align:center;padding:22px 16px}
.svc .ic{font-size:30px}.svc .t{font-weight:bold;font-size:16px;margin:8px 0 4px}.svc .d{color:#64748b;font-size:13px}
.steps{margin-bottom:20px}
.step{display:inline-block;color:#94a3b8;font-size:14px;margin-right:10px}
.step .n{display:inline-block;width:24px;height:24px;line-height:24px;text-align:center;border-radius:50%;background:#e2e8f0;color:#64748b;margin-right:6px}
.step.on{color:#0ea5e9;font-weight:bold}.step.on .n{background:#0ea5e9;color:#fff}
.step.done .n{background:#10b981;color:#fff}
label{display:block;font-size:13px;color:#475569;font-weight:600;margin:12px 0 4px}
.inp{display:block;width:100%;border:1px solid #cbd5e1;border-radius:9px;padding:10px 12px;font-size:14px;color:#334155;background:#fbfdff}
.inp.area{height:78px}
.btn{display:inline-block;border-radius:10px;padding:11px 20px;font-size:14px;border:1px solid #cbd5e1;background:#fff;color:#0f172a}
.btn.p{background:#0ea5e9;border-color:#0ea5e9;color:#fff;font-weight:bold}
.btn.g{background:#10b981;border-color:#10b981;color:#fff;font-weight:bold}
.col{display:inline-block;vertical-align:top}
.chip{display:inline-block;background:#e0f2fe;color:#0369a1;border:1px solid #bae6fd;border-radius:8px;padding:4px 10px;font-size:13px;margin:3px}
.badge{display:inline-block;border-radius:20px;padding:3px 12px;font-size:12px;font-weight:bold}
.bg-blue{background:#dbeafe;color:#1e40af}.bg-green{background:#dcfce7;color:#166534}
.bg-amber{background:#fef3c7;color:#92400e}.bg-slate{background:#e2e8f0;color:#334155}.bg-sky{background:#e0f2fe;color:#0369a1}
table{border-collapse:collapse;width:100%}
th{background:#f1f5f9;color:#475569;font-size:11px;text-transform:uppercase;text-align:left;padding:10px;border-bottom:1px solid #e2e8f0}
td{padding:11px;border-bottom:1px solid #eef2f7;font-size:13px}
.mono{font-family:'DejaVu Sans Mono',monospace}
.right{text-align:right}.center{text-align:center}.small{font-size:12px;color:#64748b}
.tl{margin:6px 0}
.tl .it{padding:8px 0 8px 26px;position:relative;font-size:14px;border-left:2px solid #e2e8f0;margin-left:8px}
.tl .it .dot{position:absolute;left:-7px;top:12px;width:12px;height:12px;border-radius:50%;background:#cbd5e1}
.tl .it.done{color:#16a34a}.tl .it.done .dot{background:#10b981}
.tl .it.now{color:#0ea5e9;font-weight:bold}.tl .it.now .dot{background:#0ea5e9}
.tl .it .tm{color:#94a3b8;font-size:12px;font-weight:normal}
.ok{background:#ecfdf5;border:1px solid #a7f3d0;border-radius:12px;padding:20px;text-align:center}
.ok .big{font-size:22px;font-weight:bold;color:#065f46}
.sr{display:inline-block;background:#0b1220;color:#fff;border-radius:10px;padding:8px 16px;font-size:18px;letter-spacing:1px;margin:10px 0}
.note{background:#f0f9ff;border:1px solid #bae6fd;border-radius:10px;padding:12px 14px;font-size:13px;color:#075985;margin-top:10px}
.sec{background:#fff;border:1px solid #e5eaf1;border-radius:14px;overflow:hidden;margin-bottom:16px}
.sec .hd{padding:13px 16px;border-bottom:1px solid #eef2f7;font-weight:bold;background:#fbfcfe}
.sec .bd{padding:16px}
.email{max-width:620px;margin:0 auto;display:block;border:1px solid #e5eaf1;border-radius:12px;overflow:hidden;background:#fff}
.email .eh{background:#0ea5e9;color:#fff;padding:16px 20px;font-size:17px;font-weight:bold}
.email .eb{padding:20px}
"""
def nav(active):
    L=lambda t,a:f"<span class='lk {'on' if a==active else ''}'>{t}</span>"
    return (f"<div class='nav'><span class='logo'>◈ Care Services</span>"
            f"{L('Request a Service','req')}{L('Track Request','track')}{L('My Requests','my')}"
            f"<span class='acc'>◐ Ahmed (Ministry of Health) ▾</span></div>")
def page(active,inner,hero=None):
    h=f"<div class='hero'><h1>{hero[0]}</h1><p>{hero[1]}</p></div>" if hero else ""
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{nav(active)}{h}<div class='wrap'>{inner}</div></body></html>"

screens=[]

# P1 — landing: choose service
svcs=[("🧹","Cleaning","Facility & deep cleaning"),("🛡️","Security","Guards & access control"),
("👷","Manpower","Skilled & general labor"),("🏨","Hospitality","Catering & front-of-house"),
("🔧","Maintenance","Technical & MEP"),("📦","Other","Describe your need")]
cards="".join([f"<div class='card svc'><div class='ic'>{i}</div><div class='t'>{t}</div><div class='d'>{d}</div></div>" for i,t,d in svcs])
inner=f"<div class='steps'><span class='step on'><span class='n'>1</span>Choose service</span><span class='step'><span class='n'>2</span>Specifications</span><span class='step'><span class='n'>3</span>Contact &amp; submit</span></div>{cards}"
screens.append(("p1_request","Portal — Request a Service",page("req",inner,("Request a Service","Tell us what you need — we'll review it and send you a tailored quote."))))

# P2 — specifications (service-type aware)
inner=f"""<div class='steps'><span class='step done'><span class='n'>✓</span>Choose service</span><span class='step on'><span class='n'>2</span>Specifications</span><span class='step'><span class='n'>3</span>Contact &amp; submit</span></div>
<div class='h1'>Cleaning — Specifications</div><div class='sub'>Fields adapt to the chosen service type</div>
<div class='card' style='width:560px'>
<label>Site / Location</label><input class='inp' value='Sabah Hospital — Block C, Kuwait City'>
<label>Area (m²)</label><input class='inp' value='12,000'>
<label>Number of floors</label><input class='inp' value='6'>
<label>Frequency</label><input class='inp' value='Daily · 2 shifts'>
<label>Preferred start date</label><input class='inp' value='01-Aug-2026'>
<label>Estimated duration</label><input class='inp' value='12 months'>
</div>
<div class='card' style='width:560px'>
<label>Special requirements (free text)</label><textarea class='inp area'>ICU & operating-theatre grade disinfection, infection-control certified staff, night shift coverage, eco-friendly chemicals only.</textarea>
<label>Add-ons</label><div><span class='chip'>✔ Uniforms</span><span class='chip'>✔ Supervisor</span><span class='chip'>＋ Consumables</span><span class='chip'>＋ Waste handling</span></div>
<label>Attachments</label><div class='note'>📎 site_plan.pdf · floor_layout.png · scope_brief.docx &nbsp; (drag &amp; drop)</div>
<label>Budget range (optional)</label><input class='inp' value='KWD 180,000 – 230,000 / year'>
<div style='margin-top:16px'><span class='btn'>← Back</span> <span class='btn p'>Continue →</span></div>
</div>"""
screens.append(("p2_specs","Portal — Specifications",page("req",inner)))

# P3 — contact & submit success
inner=f"""<div class='steps'><span class='step done'><span class='n'>✓</span>Choose service</span><span class='step done'><span class='n'>✓</span>Specifications</span><span class='step on'><span class='n'>3</span>Submitted</span></div>
<div class='ok' style='max-width:680px;margin:10px auto;display:block'>
<div style='font-size:34px'>✅</div>
<div class='big'>Your request has been received</div>
<div class='sr mono'>SR-00427</div>
<div class='small'>A confirmation was emailed to <b>ahmed@moh.gov.kw</b> with a tracking link.</div>
<div class='note' style='text-align:left;margin-top:14px'>
<b>What happens next</b><br>
1) Our team reviews &amp; approves your request (typically within 1 business day).<br>
2) We prepare a tailored quotation based on your specifications.<br>
3) You'll get the quote by email — track anytime with <b>SR-00427</b> + your email, or in <b>My Requests</b>.</div>
<div style='margin-top:16px'><span class='btn'>Track this request →</span> <span class='btn p'>Go to My Requests</span></div>
</div>"""
screens.append(("p3_submitted","Portal — Submitted",page("req",inner)))

# P4 — public tracking
inner=f"""<div class='h1'>Track your request</div><div class='sub'>No account needed — enter your request number and email</div>
<div class='card' style='width:360px'>
<label>Request number</label><input class='inp mono' value='SR-00427'>
<label>Email</label><input class='inp' value='ahmed@moh.gov.kw'>
<div style='margin-top:14px'><span class='btn p'>Track →</span></div></div>
<div class='card' style='width:700px'>
<div style='font-weight:bold;font-size:16px'>SR-00427 · Cleaning — Sabah Hospital <span class='badge bg-sky'>Quoting</span></div>
<div class='small' style='margin:4px 0 10px'>Submitted 22-Jun-2026 · assigned to Sara</div>
<div class='tl'>
<div class='it done'><span class='dot'></span>Request received <span class='tm'>22 Jun, 09:14</span></div>
<div class='it done'><span class='dot'></span>Reviewed &amp; approved <span class='tm'>22 Jun, 15:02</span></div>
<div class='it now'><span class='dot'></span>Preparing your quotation <span class='tm'>in progress</span></div>
<div class='it'><span class='dot'></span>Quote sent</div>
<div class='it'><span class='dot'></span>Accepted</div>
</div>
<div class='note'>💬 Need to add info? Reply to the confirmation email — it attaches to your request automatically.</div></div>"""
screens.append(("p4_track","Portal — Track Request",page("track",inner,("Track Request","Follow your service request status in real time."))))

# P5 — my requests (logged in)
rows=[("SR-00427","Cleaning","Sabah Hospital","22-Jun","Quoting","bg-sky","—"),
("SR-00391","Security","HQ Tower","02-Jun","Quote ready","bg-amber","KWD 88,200"),
("SR-00355","Manpower","Warehouse","18-May","Accepted","bg-green","KWD 41,000"),
("SR-00310","Cleaning","Clinic B","02-May","Declined","bg-slate","—")]
trs="".join([f"<tr><td class='mono'>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td><span class='badge {r[5]}'>{r[4]}</span></td><td class='right'>{r[6]}</td><td class='center'>›</td></tr>" for r in rows])
inner=f"""<div class='h1'>My Service Requests</div><div class='sub'>All your requests and quotations in one place</div>
<div style='margin-bottom:14px'><span class='btn p'>＋ New Request</span></div>
<div class='sec'><table><tr><th>Request #</th><th>Service</th><th>Site</th><th>Submitted</th><th>Status</th><th class='right'>Quote</th><th></th></tr>{trs}</table></div>"""
screens.append(("p5_my","Portal — My Requests",page("my",inner,("My Requests","Welcome back, Ahmed — Ministry of Health"))))

# P6 — request detail + quote with accept
inner=f"""<div class='h1'>SR-00391 · Security — HQ Tower <span class='badge bg-amber'>Quote ready</span></div>
<div class='sub'>Submitted 02-Jun-2026 · linked quotation PROP00230</div>
<div class='card' style='width:560px'>
<div style='font-weight:bold;margin-bottom:8px'>Your specifications</div>
<div class='small' style='line-height:22px'>Site: HQ Tower (18 floors)<br>Guards: 12 · 3 shifts · 24/7<br>Access control + CCTV monitoring<br>Start: 01-Jul-2026 · 12 months<br>Notes: SIA-certified, Arabic+English</div>
<div style='margin-top:12px'><span class='chip'>📎 site_brief.pdf</span><span class='chip'>📎 floorplan.png</span></div>
<div class='tl' style='margin-top:14px'>
<div class='it done'><span class='dot'></span>Received</div><div class='it done'><span class='dot'></span>Approved</div>
<div class='it done'><span class='dot'></span>Quote sent <span class='tm'>10 Jun</span></div><div class='it now'><span class='dot'></span>Awaiting your decision</div></div></div>
<div class='card' style='width:560px'>
<div style='font-weight:bold;margin-bottom:8px'>Quotation PROP00230</div>
<table><tr><th>Item</th><th class='right'>Qty</th><th class='right'>Total</th></tr>
<tr><td>Security guard (day)</td><td class='right'>6</td><td class='right'>42,000</td></tr>
<tr><td>Security guard (night)</td><td class='right'>6</td><td class='right'>40,200</td></tr>
<tr><td>CCTV monitoring</td><td class='right'>1</td><td class='right'>6,000</td></tr>
<tr style='background:#f8fafc'><td><b>Total / year</b></td><td></td><td class='right'><b>KWD 88,200</b></td></tr></table>
<div style='margin-top:14px'><span class='btn g'>✔ Accept &amp; e-Sign</span> <span class='btn'>Request changes</span> <span class='btn'>Download PDF</span></div>
<div class='note'>Accepting moves it to <b>Won</b> and we begin contracting automatically.</div></div>"""
screens.append(("p6_detail","Portal — Request + Quote",page("my",inner)))

# P7 — backend triage/approval (internal)
inner=f"""<div style='margin-bottom:10px'><span class='btn p'>Approve &amp; Assign</span><span class='btn'>Request info</span><span class='btn'>Decline</span><span class='btn g'>Create Quotation →</span></div>
<div style='margin-bottom:14px'><span class='badge bg-blue'>New</span> → <span class='badge bg-amber'>Under Review</span> → <span class='badge bg-green'>Approved</span> → Priced → Sent → Won</div>
<div class='h1'>SR-00427 · Cleaning — Sabah Hospital</div><div class='sub'>Inbound portal request · SLA 1 business day ⏱ 6h left</div>
<div class='card' style='width:560px'>
<div style='font-weight:bold;margin-bottom:6px'>Requester</div>
<div class='small' style='line-height:24px'>Ahmed Ali · ahmed@moh.gov.kw · +965 …<br>Ministry of Health <span class='badge bg-slate'>Portal user</span><br>Source: Portal · 22-Jun 09:14</div>
<div style='font-weight:bold;margin:12px 0 6px'>Specifications (from portal)</div>
<div class='small' style='line-height:22px'>Area 12,000 m² · 6 floors · Daily 2 shifts<br>ICU/OT-grade disinfection · infection-control staff<br>Eco chemicals · uniforms · supervisor<br>Start 01-Aug · 12 months · Budget 180–230k</div>
<div style='margin-top:10px'><span class='chip'>📎 site_plan.pdf</span><span class='chip'>📎 floor_layout.png</span></div></div>
<div class='card' style='width:560px'>
<div style='font-weight:bold;margin-bottom:6px'>Triage</div>
<label>Assign to</label><input class='inp' value='◐ Sara (Cleaning team)'>
<label>Service type</label><input class='inp' value='Cleaning'>
<label>Priority</label><input class='inp' value='High'>
<label>Internal note</label><textarea class='inp area'>Strong fit. Use MoH cost book. Watch infection-control certification cost.</textarea>
<div class='note' style='margin-top:10px'>On <b>Create Quotation</b>: a proposal is generated with specs mapped, customer cost book applied, and a CRM lead linked.</div></div>"""
screens.append(("p7_backend","Internal — Request Triage",page("my",inner)))

# P8 — email mockup
inner=f"""<div class='h1'>Status email (customer)</div><div class='sub'>Sent at each milestone with a one-click tracking link</div>
<div class='email'>
<div class='eh'>◈ Care Services — your request SR-00427</div>
<div class='eb'>
<p style='font-size:14px;line-height:22px'>Dear Ahmed,</p>
<p style='font-size:14px;line-height:22px'>Good news — your request <b>SR-00427</b> (Cleaning · Sabah Hospital) has been
<b>reviewed and approved</b>. Our team is now preparing your tailored quotation.</p>
<div style='text-align:center;margin:18px 0'><span class='btn p'>Track your request →</span></div>
<table style='margin-top:8px'><tr><td><b>Request #</b></td><td class='mono'>SR-00427</td></tr>
<tr><td><b>Service</b></td><td>Cleaning — Sabah Hospital</td></tr>
<tr><td><b>Status</b></td><td><span class='badge bg-sky'>Quoting</span></td></tr>
<tr><td><b>Assigned</b></td><td>Sara · Cleaning team</td></tr></table>
<p class='small' style='margin-top:14px'>Reply to this email to add details — they attach to your request automatically.</p>
<p class='small'>Care Services · Kuwait · this link is private to you.</p></div></div>"""
screens.append(("p8_email","Email — Status Update",page("track",inner)))

# render + gallery
links=[]
for fn,title,src in screens:
    hp=os.path.join(OUT,fn+".html"); pp=os.path.join(OUT,fn+".png")
    open(hp,"w",encoding="utf-8").write(src)
    subprocess.run(["/usr/local/bin/wkhtmltoimage","--enable-local-file-access","--disable-smart-width",
        "--width",str(W),"--quality","92",hp,pp],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    os.remove(hp); links.append((fn+".png",title)); print("rendered",fn+".png")
cards="".join([f"<div style='margin:0 0 28px'><div style='font-weight:bold;font-size:16px;margin:6px 0'>{i+1}. {t}</div><a href='{f}'><img src='{f}' style='width:100%;border:1px solid #e2e8f0;border-radius:10px;box-shadow:0 2px 8px rgba(0,0,0,.08)'></a></div>" for i,(f,t) in enumerate(links)])
gal=f"""<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Care — Customer Service-Request Portal Mockups</title>
<style>body{{background:#f1f5f9;font-family:Arial;margin:0}}.w{{max-width:980px;margin:0 auto;padding:24px}}h1{{color:#1e293b}}.s{{color:#64748b;margin-bottom:20px}}</style></head>
<body><div class='w'><h1>Customer Service-Request Portal — Mockups</h1>
<div class='s'>{len(links)} screens · click any image to enlarge · <a href='index.html'>← back to main proposal mockups</a></div>{cards}</div></body></html>"""
open(os.path.join(OUT,"portal.html"),"w",encoding="utf-8").write(gal)
print("portal gallery:",len(links),"screens")
