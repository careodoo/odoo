# advance_hr_attendance_dashboard — Developer Handover Documentation

> Third‑party **Cybrosys** module that adds an **HR Attendance Dashboard** — a backend OWL
> client action showing a per‑employee grid of Present / Absent / Leave marks over a chosen
> date range (This Week / Last 15 days / This Month), with employee search and a PDF print of
> the grid. It also adds a `leave_code` to leave types (used to label and colour leave cells)
> and two settings for the Present/Absent marks. UI labels are English.
>
> ⚠️ **This is an Odoo 15 module** (`'version': '15.0'`, manifest) dropped into a **17.0**
> server. The JS and assets bundle use v15/legacy APIs that are removed/renamed in 17 — see
> §10 and §11 **before** assuming the dashboard works as‑is. Read this whole file before
> touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `advance_hr_attendance_dashboard` |
| Display name | Advance HR Attendance Dashboard |
| Version (manifest) | `15.0` — running on Odoo 17 server |
| Category | Human Resources |
| Depends | `hr_holidays`, `hr`, `hr_attendance` |
| External Python lib | **`pandas`** (date ranges) — declared in `external_dependencies` |
| Author / License | Cybrosys Techno Solutions · AGPL‑3 |
| Inherited models | `hr.employee`, `hr.leave.type`, `res.config.settings` |
| New models | **none** (only an `AbstractModel` report) |
| Client action | `attendance_dashboard` (OWL) |
| Config params | `advance_hr_attendance_dashboard.present`, `…dashboard.absent` |
| Report | 1 QWeb‑PDF (`report_hr_attendance`) — prints the dashboard grid |
| Security | **N/A** — no `security/` dir, no groups, no `ir.model.access.csv` |

### Deployment (this server)
- DB: `odoo17` · service: `odoo-17.service` (systemd) · runs as user `odoo`.
- Python venv: `/home/odoo/.pyenv/versions/odoo-17-env/bin/python`
- Odoo bin: `/home/odoo/odoo-17.0+e.20241205/odoo-bin` · conf: `/home/odoo/odoo.conf`
- Addons path includes `/home/odoo/care` (this repo, branch `17`).
- **Update + restart:**
  ```bash
  sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
    /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
    -d odoo17 -u advance_hr_attendance_dashboard --stop-after-init --no-http
  sudo systemctl restart odoo-17.service
  ```
- **Requires `pandas`** in the Odoo venv (`import pandas` is a hard top‑level import in
  `models/hr_employee.py` — a missing lib aborts module load). It is normally present.
- No dev mode. After editing JS/SCSS/XML assets, a module `-u` regenerates the asset bundles;
  a restart serves them. Log file: `/var/log/odoo/odoo-17.log`.

---

## 2. Architecture overview

```
hr.employee (inherited)
└── get_employee_leave_data(option)   @api.model
        │  builds a date list for option (this_week / last_15_days / this_month) via pandas
        │  reads cids cookie → allowed companies → loops employees
        │  raw SQL on hr_leave ⨝ hr_leave_type → leave cells (code + colour)
        │  employee.attendance_ids → present dates
        │  config_params present/absent → cell mark text
        └─ returns {employee_data:[…], filtered_duration_dates:[…]}  (plain dict)
                          ▲
                          │  web.rpc query (legacy)
                          │
OWL client action  "attendance_dashboard"   static/src/js/attendance_dashboard.js
  AttendanceDashboard (Component)
    • filter <select> (This Week / Last 15 days / This Month) → onclick_this_filter
    • search box → client-side row filter (_OnClickSearchEmployee)
    • Print PDF button → ir.actions.report with the rendered table HTML as data
    template "AttendanceDashboard"  static/src/xml/attendance_dashboard_templates.xml
    styles                          static/src/scss/attendance_dashboard.scss
                          │
                          │  doAction(ir.actions.report, data={tHead, tBody})
                          ▼
report.advance_hr_attendance_dashboard.report_hr_attendance  (AbstractModel)
  _get_report_values → passes `data` straight to the QWeb template
  template report_hr_attendance renders data['tHead'] / data['tBody'] via t-raw

hr.leave.type (inherited)        + leave_code Selection (UL/SL/RL/NL/ML/FL/CL/PL/OL)
res.config.settings (inherited)  + present / absent marks (config_parameter)
```

**Design notes**
- There is **no stored dashboard model and no new table**: the dashboard payload is computed
  on every RPC call by `get_employee_leave_data`. All state lives client‑side in OWL `useState`.
- Leave‑cell colours are **hard‑coded** in `get_employee_leave_data` keyed by the leave type's
  `color` index (1–11 → fixed hex), *not* by `leave_code`.
- The PDF report does **not** re‑query the DB — the client ships the already‑rendered table
  HTML (`tHead`/`tBody`) into the report `data`, and QWeb dumps it back with `t-raw`.

---

## 3. Data model

> No new persistent models are declared. Three existing models are inherited to add fields /
> one method, plus one report `AbstractModel`.

### 3.1 `hr.employee` (inherited — `models/hr_employee.py`)
`_inherit = 'hr.employee'`, `_check_company_auto = True`. **No new fields.** One method:

**`get_employee_leave_data(self, option)` — `@api.model`** — the dashboard data source.
- `option` ∈ `'this_week' | 'this_month' | 'last_15_days'`:
  - `this_week` / `this_month` → `pandas.date_range` over `date_utils.start_of/end_of` of the
    current week/month, formatted `"%Y-%m-%d"`.
  - `last_15_days` → list of the last 15 calendar days (today back).
- Reads the **`cids` cookie** from `request.httprequest.cookies` to get the allowed company
  ids, then `search([('company_id', '=', allowed_company_ids)])` over employees.
  ⚠️ See §11 — `'='` against a **list** and the cookie dependency are both fragile.
- For each employee:
  - **Raw SQL** joins `hr_leave` ⨝ `hr_leave_type` for `state = 'validate'` leaves of that
    employee, pulling `leave_code` and `color`; expands each leave's
    `request_date_from … request_date_to` into per‑day strings via `pandas.date_range`, and
    keeps those days that fall inside the selected range.
  - Collects **present dates** from `employee.attendance_ids` (`check_in.date()`).
  - For each date in the range it builds a cell:
    - present → the **Present mark** (config param, capitalised); else the **Absent mark**;
    - if the date is a leave day → cell text becomes the **leave_code** and `color` is mapped
      from the leave type's `color` index (1→`#F06050`, 2→`#F4A460`, … 11→`#9365B8`, else
      white), and `total_absent_count` is incremented.
  - `leave_data` is reversed (`[::-1]`) so newest date is first.
- Returns `{'employee_data': [...], 'filtered_duration_dates': dates[::-1]}` (plain dict for RPC).

> Note: `total_absent_count` actually counts **leave days**, not absences, despite the name.

### 3.2 `hr.leave.type` (inherited — `models/hr_leave_type.py`)
Adds one field:

| Field | Type | Notes |
|---|---|---|
| `leave_code` | Selection, **required**, default `'NL'` | `UL/SL/RL/NL/ML/FL/CL/PL/OL` (Unpaid / Sick / Regular / Normal / Maternity / Festival / Compensatory / Paid / Other). Shown as the leave‑cell label on the dashboard. Help text spells each out. |

> ⚠️ `required=True` with default `'NL'`: existing leave types get `NL` on upgrade; new ones
> must keep a code. The grid's leave label comes from this field.

### 3.3 `res.config.settings` (inherited — `models/res_config_settings.py`)
Adds two `config_parameter` Selection settings (no `set_values` override):

| Field | config_parameter | Choices |
|---|---|---|
| `present` | `advance_hr_attendance_dashboard.present` | `present`→Present, `✔`, `✅`, `p`→P |
| `absent` | `advance_hr_attendance_dashboard.absent` | `absent`→Absent, `✘`, `❌`, `⭕`, `a`→A |

`get_employee_leave_data` reads these params to label Present/Absent cells. **If unset, both
are `False`** → the code's `if marks:` guard leaves the cell `state = None` (blank cell). Set
them in Settings to get marks. Surfaced under Attendance settings (see §6).

### 3.4 `report.advance_hr_attendance_dashboard.report_hr_attendance` (`report/hr_attendance_report.py`)
`AbstractModel`, `_name = 'report.advance_hr_attendance_dashboard.report_hr_attendance'`.
`_get_report_values(doc_ids, data=None)` returns `{'doc_model': 'hr.attendance', 'data': data,
'self': self}` — it just forwards the `data` payload the client passed in. (Contains a
leftover `print(data)` debug line.)

---

## 4. Views / wizards

- **`views/hr_leave_type_views.xml`** — extends `hr_holidays.edit_holiday_status_form`;
  inserts `leave_code` after `leave_validation_type` on the leave‑type form.
- **`views/res_config_settings_views.xml`** — extends
  `hr_attendance.res_config_settings_view_form` (priority 80); injects a **"Choose Attendance
  Marks"** section inside the `hr_attendance` settings block with the `present` and `absent`
  fields (both `required="1"`).
- **`views/advance_hr_attendance_dashboard_menus.xml`** — the client action + menu (see §10).

**Wizards:** **N/A** — none.

---

## 5. Reports

One QWeb‑PDF report that prints the on‑screen dashboard grid.

- **`report/hr_attendance_reports.xml`**
  - `paperformat_attendance` — A4, **Landscape**, `default=True`. (⚠️ `default=True` makes this
    paperformat a candidate global default; harmless but noteworthy.)
  - `action_report_hr_attendance` — `ir.actions.report`, `model = hr.employee`, `qweb-pdf`,
    `report_name = advance_hr_attendance_dashboard.report_hr_attendance`.
- **`report/hr_attendance_templates.xml`** — template `report_hr_attendance`:
  `web.html_container` → `web.external_layout` → `<h2>Attendance Report</h2>` + a `<table>`
  rendering `data['tHead']` and `data['tBody']` via **`t-raw`** (raw HTML injection).

**How it's invoked:** the **Print PDF** button on the dashboard calls
`action.doAction({type:'ir.actions.report', report_name:'…report_hr_attendance',
data:{tHead, tBody}})`, shipping the rendered table HTML; the AbstractModel passes it through
and QWeb dumps it. There is **no print menu/button on any backend form** — printing is only
reachable from the dashboard.

> ⚠️ `t-raw` on client‑supplied HTML is an XSS/markup‑injection vector and `t-raw` is the
> deprecated v15 form (v17 prefers `t-out`). It still renders in 17 but is on the way out.

---

## 6. Settings / config parameters

| Param | Set by | Read by | Effect |
|---|---|---|---|
| `advance_hr_attendance_dashboard.present` | Settings → Attendance → "Choose Attendance Marks" | `get_employee_leave_data` | label text for present cells |
| `advance_hr_attendance_dashboard.absent` | same | `get_employee_leave_data` | label text for absent cells |

No other system parameters, no `set_values` override, no recompute logic.

---

## 7. Crons / automation

**N/A** — no `ir.cron`, no scheduled actions, no mail templates, no server actions.

---

## 8. Security

**N/A — there is no `security/` directory.** No groups, **no `ir.model.access.csv`**, no
record rules. Consequences:

- The new **fields** (`leave_code`, `present`, `absent`) ride on the access rights of their
  base models (`hr.leave.type`, `res.config.settings`), so they're governed by standard HR /
  settings groups.
- The **dashboard menu + client action** have no group restriction → visible to anyone who can
  see the Attendance app's root menu (`hr_attendance.menu_hr_attendance_root`).
- `get_employee_leave_data` is `@api.model` and reads **all** employees in the allowed
  companies with `sudo()` only on the config params; ordinary record rules on `hr.employee`
  still apply to the `search`, but the **raw SQL** on `hr_leave` bypasses ORM access rules /
  record rules entirely — any user who can call the method sees validated‑leave data for the
  returned employees. Keep this in mind if leave data is sensitive.

---

## 9. Assets / JS — the dashboard (read carefully)

### 9.1 Bundle declaration (`__manifest__.py` → `assets`)
```python
'web.assets_backend': [
    ".../static/src/js/attendance_dashboard.js",
    ".../static/src/scss/attendance_dashboard.scss",
],
'web.assets_qweb': [          # ⚠️ v15 bundle — see §11
    ".../static/src/xml/attendance_dashboard_templates.xml",
],
```

### 9.2 Client action (`views/advance_hr_attendance_dashboard_menus.xml`)
- `ir.actions.client` `action_dashboard_attendance`, **`tag = attendance_dashboard`**.
- Menu `menu_attendance_dashboard` (**"Dashboard"**, sequence 0) under
  `hr_attendance.menu_hr_attendance_root`.

### 9.3 OWL component (`static/src/js/attendance_dashboard.js`)
`AttendanceDashboard extends Component`, registered as
`registry.category("actions").add("attendance_dashboard", …)`, template `"AttendanceDashboard"`.

- `setup()` — `useService('action')`, `useState({filteredDurationDates, employeeData})`,
  `useRef('attendance-dashboard')`, then **defaults to "This Week"** via
  `onclick_this_filter("this_week")`.
- `onChangeFilter(ev)` — fires on the `<select>` change → `onclick_this_filter(value)`.
- `onclick_this_filter(filter)` — **`rpc.query({model:'hr.employee',
  method:'get_employee_leave_data', args:[filter]})`** and writes the result into `state`.
- `_OnClickSearchEmployee(ev)` — pure client‑side row filter on the table by employee name
  (`data-name`), hiding non‑matching rows.
- `_OnClickPdfReport(ev)` — grabs the table's `thead`/`tbody` innerHTML and `doAction`s the
  QWeb‑PDF report with `data:{tHead, tBody}` (see §5).
- `formatDate(inputDate)` — `YYYY-MM-DD` → `DD-MON-YYYY` (English month abbreviations).

### 9.4 Template (`static/src/xml/attendance_dashboard_templates.xml`)
`AttendanceDashboard` (`owl="1"`): a header, the filter `<select>` (This Week / Last 15 days /
This Month), **Print PDF** button, search box + **Search** button, and the grid
`#attendance_table_nm` — columns = `filtered_duration_dates` (formatted), rows = employees,
each leave cell coloured via `t-attf-style="background: {{ leave.color }}"` and showing
`leave.state`; last column = `total_absent_count`.

### 9.5 Styles (`static/src/scss/attendance_dashboard.scss`)
Minimal: table/cell borders, float of the side table, grey cell text. Heavy styling is inline
in the template.

---

## 10. Gotchas & history (read before debugging)

This module was authored for **Odoo 15**. Several constructs are deprecated or **removed in
Odoo 17** and are the first places to look if the dashboard is blank, errors, or won't load:

1. **`web.assets_qweb` bundle is gone in v17.** OWL templates now load via
   `web.assets_backend` (XML listed there directly). The manifest still registers the template
   under `web.assets_qweb` → on 17 the template **may never be registered**, so the client
   action renders nothing / "template AttendanceDashboard not found". Fix: move the XML into
   `web.assets_backend`.
2. **`const { useRef } = owl.hooks;`** — `owl.hooks` no longer exists in the OWL shipped with
   v17; `useRef`/`useState` come from the `@odoo/owl` import. This line can throw at module
   eval and break the whole backend JS bundle. Use `const { Component, useState, useRef } = owl;`.
3. **`import rpc from "web.rpc";`** — the legacy `web.rpc` module is removed in v17. The modern
   path is `useService("orm")` → `this.orm.call('hr.employee','get_employee_leave_data',[filter])`.
   As written, `rpc.query(...)` will be `undefined`/import‑fail on 17.
4. **`<div t-raw=…>` inside `<table>` (report template)** — `t-raw` is deprecated (use `t-out`),
   and a `<div>` directly under `<table>` is invalid HTML; wkhtmltopdf usually tolerates it.
5. **`request.httprequest.cookies.get('cids')`** — the dashboard data depends on the `cids`
   company cookie. If the cookie is absent/oddly formatted, `cids.split(',')` raises
   `AttributeError`/`ValueError`. Also `('company_id', '=', allowed_company_ids)` compares a
   field to a **list** — this is technically wrong (should be `'in'`); it happens to work when
   one company is selected but is incorrect for multi‑company.
6. **Leave colours are hard‑coded** by the leave type's `color` index (1–11), not configurable;
   colour ≠ `leave_code`. A 12th colour falls back to white (invisible text).
7. **`total_absent_count` counts leave days, not absences** — naming is misleading in any
   report built on it.
8. **No security files** (§8): the dashboard menu is visible to all Attendance users and the
   raw‑SQL leave query bypasses ORM access control.
9. **`print(data)`** debug statement left in `_get_report_values` — spams the server log on
   each PDF print.
10. **Manifest `version` is `15.0`** (not a full `17.0.x.y.z`) — cosmetic, but signals the
    module was never properly ported. Treat any "dashboard doesn't work" report as a port issue
    first (items 1–3), not a logic bug.

---

## 11. File map
```
__manifest__.py                 depends (hr_holidays/hr/hr_attendance), data, assets, pandas dep
__init__.py                     → models, report
doc/RELEASE_NOTES.md            v15.0.1.0.0 initial commit
README.rst                      Cybrosys readme

models/
  __init__.py
  hr_employee.py                get_employee_leave_data() — the dashboard data source (raw SQL + pandas)
  hr_leave_type.py              + leave_code Selection (UL/SL/RL/NL/ML/FL/CL/PL/OL)
  res_config_settings.py        + present / absent marks (config_parameter)

report/
  __init__.py
  hr_attendance_report.py       report AbstractModel — forwards client `data` to QWeb
  hr_attendance_reports.xml     paperformat_attendance (A4 landscape) + ir.actions.report
  hr_attendance_templates.xml   QWeb template report_hr_attendance (t-raw tHead/tBody)

views/
  advance_hr_attendance_dashboard_menus.xml   ir.actions.client (tag attendance_dashboard) + menu
  hr_leave_type_views.xml                     leave_code on leave-type form
  res_config_settings_views.xml               "Choose Attendance Marks" settings section

static/src/
  js/attendance_dashboard.js                  OWL AttendanceDashboard component (⚠ v15 APIs)
  xml/attendance_dashboard_templates.xml      OWL template AttendanceDashboard
  scss/attendance_dashboard.scss              minimal grid styling
static/description/                           Cybrosys store assets (banner/icon/screenshots) — not loaded by Odoo

security/                                     N/A — does not exist
```
