# CARE HR — Complete System Blueprint (v1)

> A strong, integrated HR system for a Kuwait **services company** (cleaning, security & guarding, hospitality, washing, …) that **recruits sponsored foreign labor** (Nepal/Bangladesh + global drivers). Benchmark: **MenaITech** (match its core pillars, exceed it on care-kw specifics). One unified **Employees** app · **Dashboard landing** (role-gated) · **configurable Access Profiles** · **mobile attendance**.

---

## 0) Design principles
- **One app, internal menus.** All custom HR areas live as sub-menus inside a single **Employees** app; only Odoo's native/core models keep their external menus.
- **Dashboard is the landing page** — system-wide KPIs, visible only to users who have the right (role-gated).
- **One source of truth** per concept (one `hr.attendance`, one compensation engine) — no parallel/duplicate data.
- **Configurable permissions** (Access Profiles) down to field / tab / menu, per role — no code to re-tune.
- **Every field tracked in chatter**; every workflow audited (standing policy).
- **Lifecycle-orchestrated**: requisition → recruit → mobilize → onboard → deploy → operate → offboard, all linked.

---

## 1) Architecture — 14 pillars

| # | Pillar (المجال) | Covers | Replaces / unifies |
|---|---|---|---|
| 1 | **Core HR & Personnel Affairs** (شئون موظفين) | Employee 360, contracts, org, sectors | care_hr, care_department |
| 2 | **Recruitment & Manpower** | Manpower requisition → recruitment → offer | manpower_requisition |
| 3 | **Mobilization & Onboarding** | Foreign-labor pipeline (arrival→medical→biometric→work-permit→iqama→housing→transport), orientation, stages | employee_orientation, employee_stages, hr.action.joining |
| 4 | **Time & Attendance** | Biometric devices + **mobile app** + bulk + timesheet + shifts | to_attendance_device, care_attendance, care_timesheet, hr_attendance_*, hr_employee_shift |
| 5 | **Leaves & Permissions** | Leaves, leave-return, permissions (إذن), public holidays | care_hr leave, hr_leave_dashboard, permission_request |
| 6 | **Payroll & Compensation** ⭐ | Salary engine + allowances + loans + bonuses + commissions + overtime + **EOS gratuity** + **WPS** | ohrms_loan, hr_employee_allowance, bonus_request, commission_plan, hr_overtime_compensation, ent_hr_payroll_extension |
| 7 | **Documents & Compliance** | Docs, licenses, **iqama/work-permit expiry center** | oh_employee_documents_expiry, certificate_license_expiry |
| 8 | **Discipline, Rewards & Legal** | Disciplinary, warnings/rewards, lawsuits | ent_hr_disciplinary_tracking, hr_reward_warning, oh_hr_lawsuit_management |
| 9 | **Welfare & Logistics** | **Housing/hostel**, uniform/PPE, **transport** | hostel (in `care`), care_uniform_delivery |
| 10 | **Performance & Skills** | Appraisals (360), skills/competencies, training | hr_skills, (new performance) |
| 11 | **Employee Self-Service (ESS)** | Web + **mobile**: requests, payslip, balances, docs | (new) |
| 12 | **Analytics & Dashboards** | Landing dashboard + drill-downs + BI | advance_hr_attendance_dashboard, leave dashboards |
| 13 | **Access & Security** | **Access Profiles** (roles → field/tab/menu rights) | (new) |
| 14 | **Org & Sectors** | Sector (حكومي/خاص) → project → site → department | care_department |

---

## 2) Unified "Employees" app — menu tree

```
👤 EMPLOYEES (app)
├── 📊 Dashboard                      ← landing (role-gated)
├── 👥 Employees
│     ├── Directory / Employee 360
│     ├── Org Chart
│     └── Sectors & Projects & Sites
├── 🧭 Onboarding & Mobilization
│     ├── Mobilization Pipeline (arrival→medical→biometric→permit→iqama→housing→transport)
│     ├── Orientation & Checklists
│     └── Employee Stages
├── 🧱 Recruitment & Manpower
│     ├── Manpower Requisitions
│     └── Recruitment (job/applicants)        ← may stay native Odoo
├── ⏱️ Time & Attendance
│     ├── Live Attendance (today) + Map
│     ├── Mobile Punches  · Biometric Devices · Bulk Attendance · Timesheets
│     └── Shifts & Rosters
├── 🌴 Leaves & Permissions
│     ├── Leave Requests · Leave Returns · Permissions (إذن) · Overtime
│     └── Balances & Calendar
├── 💰 Payroll & Compensation
│     ├── Payslips & Batches · Salary Structures/Rules
│     ├── Allowances · Loans · Bonuses · Commissions · Overtime pay
│     └── End-of-Service (EOS) · WPS export · GOSI/Insurance
├── 📁 Documents & Compliance
│     ├── Employee Documents · Licenses/Certificates
│     └── Expiry Center (iqama / work-permit / passport / license)
├── ⚖️ Discipline & Legal
│     ├── Disciplinary Actions · Warnings & Rewards · Announcements
│     └── Lawsuits / Legal Cases
├── 🏠 Welfare & Logistics
│     ├── Housing / Hostel (hostel→floor→flat→room→bed)
│     ├── Uniform / PPE Issuance
│     └── Transport (routes, ride check-in, cost)
├── 📈 Performance
│     ├── Appraisals (360°) · Skills & Competencies · Training
├── 🙋 Self-Service (ESS)              ← portal/mobile entry
└── ⚙️ Configuration
      ├── Access Profiles (permissions tree)
      └── Master data (allowance types, doc types, shift types, …)
```
*External (native Odoo) menus kept as-is:* Recruitment core, base Attendances kiosk, base Time Off config, base Payroll config (where used).

---

## 3) The Dashboard (landing — role-gated)

A powerful OWL dashboard; **each card/section honors Access Profiles** (a user only sees the KPIs they're allowed).

**KPI cards:** Headcount · New joiners (MTD) · Departures · Present today % · On leave today · Pending approvals (mine) · Expiring docs (≤30d) · In mobilization · Vacant positions · Monthly payroll cost · Overtime hours (MTD) · Housing occupancy %.

**Charts:** Headcount by **sector / department / nationality / job** · Onboarding pipeline funnel (arrival→…→deployed) · Attendance trend (present/absent/leave) · Leaves by type · Document-expiry timeline (next 90 days) · Payroll cost trend · Overtime by project · Housing & transport cost by project · Turnover rate · Gender/age split.

**Action widgets:** "Needs attention" (expiring iqamas, late returns, pending approvals, undeployed clearances), my approvals inbox, recent joiners, today's roster.

---

## 4) Screen inventory (all screens)

**Core HR:** Employee 360 (profile + tabs: personal, job/contract, sector/project/site, documents, attendance, leaves, payroll, compensation, discipline, housing, uniform, transport, skills, history), Org chart, Sectors, Projects, Sites, Directory list/kanban/map.

**Onboarding:** Mobilization board (kanban by stage), Mobilization record (checklist: medical, biometric, work-permit, iqama, housing-assign, transport-assign with dates/cost/attachments), Orientation, Stages timeline.

**Recruitment/Manpower:** Requisition form (with approvals), Requisition board, link to applicants.

**Time & Attendance:** Live board + map (who/where now), Mobile punch review, Device manager, Bulk attendance, Timesheet, Shift/roster planner, Attendance corrections/approvals.

**Leaves & Permissions:** Leave request, Leave return (fix the inverted day-calc bug), Permission (إذن) with hours wallet, Overtime request, Balances, Calendar.

**Payroll & Compensation:** Payslip, Payroll batch, Salary structure/rules, **Compensation hub** (one screen: allowances/loans/bonuses/commissions/overtime/deductions per employee/period with states draft→approved→paid), EOS calculator, WPS export wizard, GOSI/insurance.

**Documents & Compliance:** Document record, Expiry center (calendar + list + alerts), License/certificate, Renewal workflow, bulk renew.

**Discipline & Legal:** Disciplinary action (draft→explain→action→validated), Warning/Reward, Announcement, Lawsuit + updates timeline + appointment reminders.

**Welfare & Logistics:** Hostel hierarchy + bed assignment + occupancy map + maintenance, Uniform issuance (individual/bulk + signature), Transport routes + ride check-in + cost allocation.

**Performance:** Appraisal (360°), Skills matrix, Training program + certificates.

**ESS (web+mobile):** Home, My attendance + punch, My leaves/permissions/overtime (request+status), My payslips, My documents + expiry alerts, My team (manager), Approvals inbox, Announcements.

**Config:** Access Profiles designer, master data screens.

---

## 5) Developed reports (per-company branding, Arabic/English, role-gated)
Employee profile/ID card · Joining · Clearance · Absence · Leave-return · Leave request · Salary slip · Payroll summary · **EOS settlement** · **WPS file** · Manpower requisition · Document-expiry report · Disciplinary letter · Warning/reward letter · Lawsuit report · Uniform issuance · Housing occupancy & cost · Transport cost · Attendance sheet (by project/site) · Overtime report · Headcount & turnover · Nationality/visa report · Orientation certificate · Exit interview.

---

## 6) Ideas — UI improvements
- **Employee 360** single screen with smart-button stat tiles (docs, attendance, leaves, loans, discipline, housing, uniform) + a status ribbon (active/suspended/notice/resigned) + **compliance traffic-light** (iqama/permit/medical valid?).
- **Kanban boards** for every workflow (mobilization, requisition, disciplinary, leaves) with drag-to-advance.
- **Live attendance map** (Leaflet) of who's punched at which site now.
- **Expiry center** = one calendar/heatmap of all expiring docs across the company, color-coded, with bulk-renew.
- **Global "Approvals inbox"** consolidating every pending approval (leave/permission/overtime/loan/bonus/requisition/shift) in one place.
- **Compliance gates** surfaced inline (can't deploy to sensitive site without valid security clearance; can't pay without valid iqama).
- Arabic-first RTL, dark/light, mobile-responsive ESS.

## 7) Ideas — procedure / workflow improvements
- **Unified approval framework**: one engine (per request type, dept/sector override, N-level, escalation on SLA, full audit) — replaces today's scattered config-param/db/python-group approvals.
- **Compensation hub**: every earning/deduction (allowance/bonus/commission/overtime/loan/late-fee) becomes a hub line `draft→approved→paid`; **payslip pulls from the hub** → nothing approved is ever "forgotten" before payroll.
- **Mobilization orchestration**: requisition → recruit → mobilization checklist auto-creates document/expiry records + housing + transport + biometric enrollment tasks; deployment blocked until compliance complete.
- **Attendance reconciliation**: device + mobile + bulk write to one `hr.attendance` with **dedup + conflict detection**; permission/leave auto-block conflicting punches; timesheet gap-fill becomes idempotent.
- **Offboarding orchestration**: resignation → clearance (configurable, sign-off per item) → exit interview → EOS settlement → document collection → housing/uniform return → final pay — all linked and gated.
- **EOS & WPS**: automated end-of-service gratuity per Kuwait labor law + WPS salary file export (MenaITech-grade).
- **Sector-aware compliance**: government-project employees enforce stricter doc/clearance rules automatically.

## 8) Mobile attendance app (its own ideas)
Geofencing per site · selfie + face/liveness · QR/NFC site punch · offline+sync · supervisor **team/bulk punch** · punch tied to site/project (billing) · driver **ride check-in** · ESS in-app (requests/approvals/payslip/balances/doc-alerts) · manager live map + approvals · mock-GPS detection + device binding · clearance-gated deployment. Unifies into the single `hr.attendance`.

---

## 9) GAP & DEFECTS ANALYSIS (current system) — بيان الخلل والفجوات

### 🔴 Critical defects (bugs)
1. **Hostel `compute_labor_cost` ÷ 0** — `price / used_places` crashes when a hostel has 0 occupants (`care/models/hostel.py:25-30`).
2. **Leave-return day math inverted** — `compute_actual_leave_days` / `compute_late_days` compute days *before* leave, not after (`care_hr/hr_action_leave_return.py:62-75`); and `button_approve` mutates the original `hr.leave` directly.
3. **Manpower `hr_user_ids` default** evaluates at module-load, not per record (`manpower_requisition`).
4. **Bonus `day_value = wage/26`** hardcoded working days (`bonus_request/models/models.py`).

### 🟠 Architectural gaps
1. **No unified payroll/compensation** — allowances, bonuses, commissions, overtime are approved but **never reach payroll**; only loans do (via 2 incompatible modules). → biggest gap.
2. **No EOS gratuity, no WPS, no GOSI** integration (core Gulf payroll needs).
3. **Fragmented approvals** — every module invents its own approver mechanism (config param / DB / python group); no escalation, weak audit.
4. **No unified Personnel-Affairs 360** — documents, discipline, lawsuits, uniform, housing scattered; no single employee view.
5. **Attendance has no dedup/conflict control** — device + bulk + timesheet create `hr.attendance` independently; permission/leave don't block punches; timesheet gap-fill not idempotent (can duplicate).
6. **Document/expiry fragmented** — employee docs vs partner certs vs security certs in 3 systems; some only alert **after** expiry; inefficient daily full-scan crons.
7. **Lifecycle not orchestrated** — requisition ⇄ resignation ⇄ exit-interview ⇄ clearance not linked; stage transitions unguarded; clearance can precede resignation approval.
8. **No real mobilization/onboarding workflow** for sponsored foreign labor (the company's core reality) — joining is a single record, not the medical→biometric→permit→iqama→housing→transport pipeline.
9. **Welfare not costed** — housing & transport are "on the company" but **not allocated to projects** nor fed to accounting/payroll.
10. **Security clearances** for sensitive sites (MoD) not modeled as a deployment gate.

### 🟡 Quality gaps
- Many computed counts non-stored (perf), hardcoded clearance lines, no chatter on financial events, weak/duplicate field naming (hostel `is_available`/`vacation`), no consent/GDPR note for biometric/face data, raw SQL in dashboards (injection risk), per-module duplicated attendance dashboards.

---

## 10) Phased implementation plan (after mockup sign-off)

1. **Foundation & shell** — unified Employees app + menu tree + **Access Profiles** engine + Org/Sectors model + Employee 360.
2. **Onboarding/Mobilization** — foreign-labor pipeline + documents/expiry center + orientation/stages.
3. **Time & Attendance unification** — one `hr.attendance` (device+bulk+mobile) + dedup/conflict + shifts/roster; then the **mobile app**.
4. **Leaves & Permissions** — fix bugs, unified approvals, balances/calendar.
5. **Payroll & Compensation engine** — compensation hub + salary structures + allowances/loans/bonuses/commissions/overtime + **EOS + WPS + GOSI**.
6. **Discipline/Legal + Welfare** — disciplinary/warnings/lawsuits + housing/uniform/transport with **cost allocation**.
7. **Performance + ESS (web+mobile)**.
8. **Dashboard & BI** (role-gated) + all developed reports.
9. **Standing policy** (perms matrix + chatter tracking) applied throughout.

---

*Next: visual mockup images for every screen (served as a gallery link), then implementation per phase after sign-off.*
