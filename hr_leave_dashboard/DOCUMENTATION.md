# hr_leave_dashboard — Developer Handover Documentation

> **HR Leave Dashboard** — a **third-party Cybrosys** module for Odoo 17 that
> enriches the standard **Time Off (`hr_holidays`) dashboard** with four extra
> cards: an employee profile card, an org-chart card, a department card (current
> shift / upcoming holidays / who's on leave), and an approval-status card with a
> PDF "Leave Report". It also overlays **public holidays** on the Time Off
> calendar. It is implemented almost entirely as **OWL patches/extensions** of
> existing `hr_holidays` components — it adds **no new models, no menus, no
> security, no crons**. UI is **English**. Read this before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `hr_leave_dashboard` |
| Display name | Hr Leave Dashboard |
| Version | `17.0.1.0.0` |
| Odoo | 17.0 |
| Author / License | Cybrosys Techno Solutions · AGPL-3 |
| Depends | `base`, `hr_holidays`, `hr_org_chart` |
| External Python libs | **`pytz`** (shift/timezone), stdlib `datetime` · uses `odoo.tools.date_utils` |
| New models | **None** — only inherits `hr.employee` and `hr.leave` (+ one report `AbstractModel`) |
| New menus / actions | None (the dashboard surface is the stock Time Off dashboard) |
| Report | 1 QWeb-PDF — `hr_leave_dashboard.hr_leave_report` ("Leave report") |
| Security | **None** added (no groups, no `ir.model.access.csv`, no record rules) |

### Deployment (this server)
- DB: `odoo17` · service: `odoo-17.service` (systemd) · runs as user `odoo`.
- Python venv: `/home/odoo/.pyenv/versions/odoo-17-env/bin/python`
- Odoo bin: `/home/odoo/odoo-17.0+e.20241205/odoo-bin` · conf: `/home/odoo/odoo.conf`
- Addons path includes `/home/odoo/care` (this repo, branch `17`).
- **Update + restart:**
  ```bash
  sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
    /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
    -d odoo17 -u hr_leave_dashboard --stop-after-init --no-http
  sudo systemctl restart odoo-17.service
  ```
- No dev mode. This module is mostly **JS/SCSS/XML assets**; after editing them a
  module `-u` regenerates the `web.assets_backend` bundle and the restart serves
  it. Log file: `/var/log/odoo/odoo-17.log`.
- Requires the **`pytz`** package in the Odoo venv (standard with Odoo).

---

## 2. Architecture overview

This module is a **client-side extension layer** over `hr_holidays`. There is no
new backend data model — the Python side is just `@api.model` data-source methods
on the inherited `hr.leave`/`hr.employee` that the OWL cards call over RPC.

```
hr_holidays.TimeOffDashboard        (stock OWL dashboard — the surface)
   │  patched (time_off_emp_dashboard.js)  → loads 6 extra data calls onWillStart
   │  template extended (t-inherit "hr_holidays.TimeOffDashboard")
   └── adds 4 OWL cards after the stock o_timeoff_card:
        ├── TimeOffEmpCard        → employee profile (name/job/email/phone/dept/company)
        ├── TimeOffEmpOrgChart    → org-chart card (reuses /hr/get_org_chart)
        ├── EmpDepartmentCard     → current shift · upcoming holidays · on-leave list
        └── ApprovalStatusCard    → approved/to-approve/refused counts + "Print PDF"

hr_holidays Time Off Calendar       (stock calendar views)
   ├── TimeOffCalendarModel  patched → fetches publicHolidays per visible range
   └── TimeOffCalendarYearRenderer patched + usePublicHolidays hook
        → adds .fc-public-holiday CSS class to holiday cells

Backend data sources (no new tables):
  hr.leave (inherited)      get_current_employee · get_absentees · get_current_shift
                            get_upcoming_holidays · get_approval_status_count
                            get_all_validated_leaves
  hr.employee (inherited)   get_public_holidays · _get_public_holidays
  report.hr_leave_dashboard.hr_leave_report (AbstractModel) → Leave PDF
```

**Design notes**
- All dashboard data is delivered by **`@api.model` methods returning plain
  dicts/lists** that the OWL components fetch via `this.orm.call(...)`.
- The org-chart card **reuses the stock `hr_org_chart` controller route**
  (`/hr/get_org_chart`) and re-implements its OWL template under this module's
  namespace, so the look matches Odoo's native org chart.
- The "manager vs. user" split is decided client-side by
  `userService.hasGroup('hr_holidays.group_hr_holidays_manager')` — managers see
  a subordinate table + PDF print; regular users see their own counts.

---

## 3. Data model

**No new models.** Two inherited models, both adding only methods (no fields).

### 3.1 `hr.employee` (inherited — `models/hr_employee.py`)
Public-holiday data source for the calendar overlay. **No new fields.**

| Method | Notes |
|---|---|
| `get_public_holidays(start_date, end_date)` | Returns `{ 'YYYY-MM-DD': day_index, ... }` of public-holiday dates in range. Falls back to `self.env.user.employee_id` when called on an empty recordset. |
| `_get_public_holidays(start_date, end_date)` | Searches `resource.calendar.leaves` with `resource_id = False` (company-wide holidays) across `self.env.companies`. |

### 3.2 `hr.leave` (inherited — `models/hr_leave.py`)
All the dashboard card data sources. **No new fields** — only `@api.model`
helpers.

| Method | Returns / purpose |
|---|---|
| `_prepare_employee_data(employee)` | helper dict `{id, name, job_id, approval_status_count}` for a child/manager. |
| `get_current_employee()` | the logged-in employee's profile dict (name, job, image_1920, email, phone, calendar, department, company, parent/child ids, `manager`, `children`, counts). Feeds **all four cards** (the dashboard `onWillStart` calls this first). |
| `get_absentees()` | employees among the current user's `child_ids` whose **validated** leave spans now. **Raw SQL** join `hr_leave`↔`hr_employee` filtered to `state='validate'`. |
| `get_current_shift()` | the current employee's active shift name now, computed from `resource_calendar_id.attendance_ids` using the employee's **`pytz`** timezone (day-of-week + hour window match). |
| `get_upcoming_holidays()` | company public holidays (`resource_calendar_leaves WHERE resource_id is null`) whose `date_to` is after now (timezone-aware). |
| `get_approval_status_count(current_employee)` | `{validate_count, confirm_count, refuse_count}` via `search_count` per state. |
| `get_all_validated_leaves()` | list of all `state='validate'` leaves (id, employee, dates, leave type, days) — passed to the PDF report through the card. |

> The `get_absentees` SQL builds an `IN (...)`/`= id` clause from the child id
> list and uses `self._cr.execute` directly (see Gotchas re: 0-children edge case).

### 3.3 `report.hr_leave_dashboard.hr_leave_report` (AbstractModel — `report/hr_leave_report.py`)
QWeb-PDF report model. `_get_report_values(docids, data)`:
- Reads `data['duration']` (`today` / `this_week` / `this_month` / `this_year`)
  and builds the date window with `odoo.tools.date_utils.start_of/end_of`.
- Runs a **raw SQL** aggregate over `hr_employee ⋈ hr_leave_allocation ⋈ hr_leave ⋈
  hr_leave_type` for `state='validate'`, computing per (employee, leave type):
  `allocated_days`, `taken_days`, `balance_days`. **Two query variants:** scoped to
  the user's **own department** when the user has no `child_ids`, otherwise
  **all departments** (manager view).
- Filters rows whose leave range intersects the chosen duration window
  (`generate_date_range` builds the day list), dedupes by `(leave_type, emp_id)`,
  returns `{duration, filtered_list}`.
- Note: leave-type name is read from the jsonb translation column
  (`lt.name::jsonb->>'en_US'`) — English label only.

---

## 4. Dashboard data source (entry points)

The OWL `TimeOffDashboard` patch (`time_off_emp_dashboard.js`) calls these six
methods in `onWillStart`, all on `hr.leave`, passing
`context.employee_id = props.employeeId`:

```
get_current_employee   → currentEmployee.data   (drives every card)
get_absentees          → currentAbsentees.data  (EmpDepartmentCard "On Leave")
get_current_shift      → currentShift.data       (EmpDepartmentCard "Current Shift")
get_upcoming_holidays  → upcoming_holidays.data  (EmpDepartmentCard holidays)
get_approval_status_count([currentEmployee.id])  → approval_status_count
get_all_validated_leaves → all_validated_leaves  (ApprovalStatusCard → PDF data)
```

The calendar overlay calls `hr.employee.get_public_holidays` from the patched
`TimeOffCalendarModel.fetchPublicHolidays` (per visible range).

---

## 5. Views

**N/A** — this module adds **no backend XML views, no menus, no actions**
(besides the report action). It extends the existing Time Off dashboard purely
through OWL component patches and template inheritance; there is no `views/`
directory.

---

## 6. Reports

One QWeb-PDF report.

| Item | Value |
|---|---|
| Report action (`report/hr_leave_reports.xml`) | `hr_leave_report_action` — name "Leave report", `report_name = hr_leave_dashboard.hr_leave_report`, `model = hr.leave`, `qweb-pdf` |
| Template (`report/hr_leave_report_templates.xml`) | `hr_leave_report` — `web.external_layout`; title "Leave Report" + duration sub-heading (Absentees today/this week/this month/this year); table of Employee ID, Name, Leave Type, Allocated Balance, Taken Leaves, Remaining Balance |
| Report model (`report/hr_leave_report.py`) | `report.hr_leave_dashboard.hr_leave_report` (AbstractModel, see §3.3) |

Triggered client-side from `ApprovalStatusCard.printPdfReport()` (manager view),
which reads the `#duration` `<select>` value and calls `actionService.doAction`
with `type: ir.actions.report`, passing `{duration, all_validated_leaves}` as
`data`.

> Note: the report action's `report_name` (`hr_leave_dashboard.hr_leave_report`)
> matches the AbstractModel suffix, but the **template id is also
> `hr_leave_report`** (not the dotted form). Odoo resolves the report via the
> AbstractModel's `_get_report_values`; keep these three names consistent if you
> rename.

---

## 7. Crons

**N/A** — no `ir.cron` records, no scheduled jobs.

---

## 8. Settings

**N/A** — no `res.config.settings` extension, no `config_parameter`, no system
parameters. Behaviour is fixed in code; the only runtime toggle is the
manager-vs-user view, decided by `hr_holidays.group_hr_holidays_manager`
membership.

---

## 9. Security

**N/A (none added by this module).** There is no `security/` directory, no
groups, no `ir.model.access.csv`, no record rules. Access is whatever the stock
`hr_holidays` / `hr_org_chart` modules grant:
- Manager features (subordinate table, PDF print) gate on
  `hr_holidays.group_hr_holidays_manager` (checked **client-side** for UI only).
- Data methods run with the calling user's normal ORM permissions; `get_absentees`
  and the report use **raw SQL** (`self._cr.execute`) so they bypass record rules —
  keep that in mind for multi-company/confidentiality concerns (see Gotchas).

---

## 10. Assets / JS (OWL — the dashboard)

All registered in `__manifest__.py → assets/web.assets_backend`. There is **no
client-action tag** — the module **patches and extends the stock Time Off
dashboard** rather than registering a new screen.

### 10.1 JS files (`static/src/js/`)
| File | What it does |
|---|---|
| `time_off_emp_dashboard.js` | `patch(TimeOffDashboard.prototype)` — in `setup`/`onWillStart` loads the 6 RPC datasets into `useState` holders, resolves manager flag, defaults `props.employeeId` to the current employee. Registers the 4 cards into `TimeOffDashboard.components`. |
| `time_off_emp_card.js` | Defines OWL components **`TimeOffEmpCard`**, **`TimeOffEmpOrgChart`** (simple wrapper), **`EmpDepartmentCard`**, **`ApprovalStatusCard`** (incl. `printPdfReport()`). |
| `emp_org_chart.js` | Full org-chart component **`TimeOffEmpOrgChart`** + `TimeOffEmpOrgChartPopover`; fetches `/hr/get_org_chart` via RPC, handles employee redirect/popover/"more managers". (Note: same export name as the wrapper in `time_off_emp_card.js`; the dashboard imports `TimeOffEmpOrgChart` from `./emp_org_chart`.) |
| `hooks.js` | `usePublicHolidays(props)` — returns a day-render callback that adds the `fc-public-holiday` class to calendar cells present in `props.model.publicHolidays`. |
| `calendar_model.js` | `patch(TimeOffCalendarModel.prototype)` — adds `publicHolidays` to model data; `fetchPublicHolidays` calls `hr.employee.get_public_holidays` for the visible range; forces `month` scale on small screens. |
| `calendar_year_renderer.js` | `patch(TimeOffCalendarYearRenderer.prototype)` — wires `usePublicHolidays` into `onDayRender` to colour holiday days. |

### 10.2 Templates (`static/src/xml/`)
| File | Template(s) |
|---|---|
| `time_off_emp_dashboard_templates.xml` | `hr_leave_dashboard.TimeOffEmpDashboard` — `t-inherit="hr_holidays.TimeOffDashboard"` (extension), `xpath` inserts the 4 cards **after** the stock `o_timeoff_card`. |
| `time_off_emp_card_templates.xml` | `hr_leave_dashboard.TimeOffEmpCard` — employee profile card (image, job, working hours, email, phone, department, company). |
| `emp_department_card_templates.xml` | `hr_leave_dashboard.EmpDepartmentCard` — current shift, upcoming holidays, "On Leave" list. |
| `approval_status_card_templates.xml` | `hr_leave_dashboard.ApprovalStatusCard` — user view (Approved/To Approve/Refused counts) vs. manager view (duration `<select>` + "Print PDF" + subordinate table). |
| `emp_org_chart_templates.xml` | `hr_leave_dashboard.hr_org_chart` (+ `…hr_org_chart_employee`, `…_content`, `…hr_orgchart_emp_popover`) — re-implementation of the native org-chart markup. |

### 10.3 Styles (`static/src/css|scss/`)
- `static/src/css/hr_leave_dashboard.css` (~90 lines) — card layout/box styling.
- `static/src/scss/time_off_dashboard.scss`, `calendar_renderer.scss` — dashboard
  + holiday-cell styling.
- The manifest **also pulls in three styles from other modules** so the cards
  match the native look: `hr_org_chart/.../hr_org_chart.scss`,
  `hr_holidays/static/src/dashboard/time_off_card.scss`. **Charts: N/A** — this
  dashboard renders cards/tables/org-chart, no Chart.js.

---

## 11. Gotchas & notes (read before debugging)

- **No new models / menus / security / crons / settings.** If you're hunting for
  a config flag or access rule, it doesn't exist here — behaviour is hard-coded
  and access is inherited from `hr_holidays` / `hr_org_chart`.
- **Patch-based, not a client action.** The dashboard has **no `registry`
  client-action tag**; everything hangs off `patch(TimeOffDashboard.prototype)`
  and `t-inherit` of `hr_holidays.TimeOffDashboard`. An `hr_holidays` upgrade that
  renames those components/templates will silently break the cards — re-check the
  patch targets after any Odoo point-release.
- **`get_absentees` zero-children edge case:** the method only builds a query when
  the current user has **≥1** subordinate; with **0** children, no query runs and
  `self._cr` still holds the **previous** result set — `dictfetchall()` can return
  stale/garbage rows. Guard with an early `return []` if you touch it.
- **Raw SQL bypasses record rules / multi-company:** `get_absentees`,
  `get_upcoming_holidays`, and the report query use `self._cr.execute`. They do
  **not** honour ORM access rules or `company_id` filtering beyond what the SQL
  spells out — review before exposing to confidential leave data.
- **SQL string interpolation:** queries are built with `%`/`% str(tuple(...))`
  rather than parametrised `execute(query, params)`. Inputs are internal ids so
  injection risk is low, but it's fragile (e.g. a 1-tuple `(x,)` vs `(x, y)`),
  hence the separate "one child" branch.
- **Duplicate `TimeOffEmpOrgChart` export name** in two JS files
  (`time_off_emp_card.js` wrapper vs. `emp_org_chart.js` full component). The
  dashboard registers the **full** one from `emp_org_chart.js`. Don't "dedupe"
  blindly.
- **Leave-type label is English-only** in the report (`name::jsonb->>'en_US'`);
  it won't follow the user's language.
- **`printPdfReport` reads the DOM directly** via
  `this.__owl__.bdom.el.querySelectorAll("#duration")` + jQuery `$`. This relies
  on OWL internals (`__owl__.bdom`) and a global `$`; both are brittle across
  Odoo versions — a refactor target if it ever stops finding the `<select>`.
- **`get_current_shift` returns a shift name or `False`** based on a string-built
  `hour.minute` compared as a float (e.g. `"09.05"`→`9.05`) — minutes are treated
  as a fraction-of-100, not /60, so the hour-window match is approximate. Cosmetic
  for the card, but don't reuse this for real time math.
- **Calendar overlay scope:** `get_public_holidays` only returns **company-wide**
  `resource.calendar.leaves` (`resource_id = False`); per-resource/personal
  calendar leaves are not shown as "public holidays".

---

## 12. File map
```
__manifest__.py                  depends (hr_holidays, hr_org_chart) · data · assets
__init__.py                      → models, report
doc/RELEASE_NOTES.md             v17.0.1.0.0 initial commit (05.04.2024)
README.rst

models/
  hr_employee.py                 get_public_holidays / _get_public_holidays (calendar overlay)
  hr_leave.py                    6 @api.model dashboard data sources (cards + PDF data)

report/
  hr_leave_report.py             report.hr_leave_dashboard.hr_leave_report (AbstractModel, SQL aggregate)
  hr_leave_reports.xml           ir.actions.report "Leave report"
  hr_leave_report_templates.xml  QWeb-PDF template (external layout)

static/src/
  js/   time_off_emp_dashboard.js   patch TimeOffDashboard + register cards
        time_off_emp_card.js        TimeOffEmpCard / EmpDepartmentCard / ApprovalStatusCard (+ org wrapper)
        emp_org_chart.js            full org-chart component + popover (/hr/get_org_chart)
        hooks.js                    usePublicHolidays render hook
        calendar_model.js           patch TimeOffCalendarModel (fetch public holidays)
        calendar_year_renderer.js   patch year renderer (colour holiday cells)
  xml/  time_off_emp_dashboard_templates.xml   t-inherit hr_holidays.TimeOffDashboard
        time_off_emp_card_templates.xml        employee profile card
        emp_department_card_templates.xml      shift / holidays / on-leave
        approval_status_card_templates.xml     counts + Print PDF / subordinate table
        emp_org_chart_templates.xml            org-chart markup + popover
  css/  hr_leave_dashboard.css
  scss/ time_off_dashboard.scss · calendar_renderer.scss
  description/                    store assets (banner, icon, screenshots) — not loaded by Odoo

(no views/ · no security/ · no data/ crons · no res.config.settings)
```
