# hr_holidays_balance_report — Developer Handover Documentation

> **HR Balance Leave Report** — a small Cybrosys (third-party) reporting module for
> Odoo 17. It adds a single read-only **PostgreSQL view** model that, per employee and
> per leave type, shows **Allocated Balance**, **Taken Leaves** and **Remaining Balance**,
> exposed as a tree / pivot / graph report under *Time Off → Reporting*. UI labels are
> English. There is no Python business logic beyond the SQL view definition. Read this
> before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `hr_holidays_balance_report` |
| Display name | `HR Balance Leave Report` |
| Version | `17.0.1.0.0` |
| Odoo | 17.0 |
| Category | Human Resources |
| Author / Maintainer | Cybrosys Techno Solutions (third-party, AGPL-3) |
| Depends | `hr_holidays` |
| External Python libs | **None** (only `odoo` stdlib imports: `fields`, `models`, `tools`) |
| Key model | `report.balance.leave` (`_auto = False` — SQL view) |
| Menu | *Leave Balance Report* under `hr_holidays.menu_hr_holidays_report` (Time Off → Reporting) |
| Application | `False` · `installable: True` · `auto_install: False` |

### Deployment (this server)
- DB: `odoo17` · service: `odoo-17.service` (systemd) · runs as user `odoo`.
- Python venv: `/home/odoo/.pyenv/versions/odoo-17-env/bin/python`
- Odoo bin: `/home/odoo/odoo-17.0+e.20241205/odoo-bin` · conf: `/home/odoo/odoo.conf`
- Addons path includes `/home/odoo/care` (this repo, branch `17`).
- **Update + restart:**
  ```bash
  sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
    /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
    -d odoo17 -u hr_holidays_balance_report --stop-after-init --no-http
  sudo systemctl restart odoo-17.service
  ```
- No dev mode. The `-u` re-runs `init()` (re-creates the SQL view); the restart serves it.
  Log file: `/var/log/odoo/odoo-17.log`.

---

## 2. Architecture overview

```
report.balance.leave   (_auto = False — read-only PostgreSQL VIEW "report_balance_leave")
│
│  Built in init() by raw SQL: CREATE OR REPLACE VIEW … (one row per employee × leave type)
│
├── reads  hr_employee            (active employees, gender, country, department, job, company)
├── reads  hr_leave_allocation    (al.number_of_days  → allocated_days)
├── reads  hr_leave_type          (the leave-type grouping key)
└── reads  hr_leave               (validated requests → taken_days)

UI surfaces (report/report_balance_leave_views.xml):
  • Tree view  (create="0", read-only)
  • Pivot + Graph views (via action view_mode = tree,pivot,graph)
  • Search view with 5 Group-By filters (employee/department/leave type/job/gender)
  • act_window action + menuitem under Time Off → Reporting

Security:
  • ir.model.access.csv  — full read/write/create/unlink (no group restriction)
  • ir.rule              — multi-company rule on company_id
```

**Design principle** — this is a classic Odoo "SQL-view report" module: all computation
lives in a single `CREATE VIEW` statement, so the data is always live (no stored fields,
no cron, no recompute). The model is `_auto = False`; Odoo never creates a real table for
it.

---

## 3. Data model

### 3.1 `report.balance.leave` (`report/report_balance_leave.py`)
`_name = 'report.balance.leave'` · `_description = 'Leave Balance Report'` · `_auto = False`.

All fields are `readonly=True` (the model is a read-only view).

| Field | Type | Source column | Meaning |
|---|---|---|---|
| `emp_id` | Many2one `hr.employee` | `e.id` | Employee |
| `gender` | Char | `e.gender` | Employee gender |
| `department_id` | Many2one `hr.department` | `e.department_id` | Department |
| `country_id` | Many2one `res.country` | `e.country_id` | Nationality |
| `job_id` | Many2one `hr.job` | `e.job_id` | Job position |
| `leave_type_id` | Many2one `hr.leave.type` | `lt.id` | Leave type |
| `allocated_days` | Integer | `SUM(al.number_of_days)` | **Allocated Balance** |
| `taken_days` | Integer | `SUM(... validated leaves ...)` | **Taken Leaves** |
| `balance_days` | Integer | allocated − taken | **Remaining Balance** |
| `company_id` | Many2one `res.company` | `e.company_id` | Company |

> Note: `id` is synthesised in SQL via `row_number() OVER (ORDER BY e.id)` — it is **not**
> a stable database id and changes when the view is rebuilt. It exists only because Odoo
> requires an `id` column on every model.

### 3.2 How the balance figures are computed (the `init()` SQL view)
`init()` drops any existing view (`tools.drop_view_if_exists`) and runs
`CREATE OR REPLACE VIEW report_balance_leave AS (...)`. The query, in plain English:

```
FROM hr_employee e
JOIN      hr_leave_allocation al  ON al.employee_id = e.id
JOIN      hr_leave_type       lt  ON al.holiday_status_id = lt.id
LEFT JOIN hr_leave            l   ON l.employee_id = e.id
                                 AND l.holiday_status_id = lt.id
WHERE  e.active = TRUE
GROUP BY e.id, lt.id
```

Per `(employee, leave_type)` group it computes:
- `allocated_days` = `SUM(al.number_of_days)` — sum of all leave **allocations** of that
  type for that employee.
- `taken_days` = `SUM(CASE WHEN l.state = 'validate' THEN l.number_of_days ELSE 0 END)`
  — sum of **validated** leave requests only (drafts / to-approve / refused are ignored).
- `balance_days` = `allocated_days − taken_days` (`SUM(allocation) − SUM(validated leaves)`).

**Important computation caveats (read before trusting the numbers):**
- The driver is the **INNER JOIN to `hr_leave_allocation`**: an employee with **no
  allocation** of a given leave type produces **no row** — even if they have taken leaves
  of that type. Only allocated leave types appear.
- `taken_days` filters on `l.state = 'validate'` **only**. Odoo 17's leave workflow also
  has a `validate1` (second-approval) state; requests sitting in `validate1` are **not**
  counted as taken. There is no filter on the **allocation** state, so non-validated
  allocations are still summed into `allocated_days`.
- The `hr_leave` join has **no date/period filter** — it spans all time, not a fiscal
  year. Multi-year allocations and leaves are all aggregated together.
- A many-to-many fan-out risk exists: because both `hr_leave_allocation` and `hr_leave`
  are joined on the same `(employee, leave_type)` key before the `GROUP BY`, the SUMs can
  be inflated when an employee has **multiple allocation rows** for the same leave type
  (each leave row is duplicated per allocation row). Validate carefully against Odoo's own
  Time Off balance figures before relying on this for payroll.
- Fields are declared **Integer** in Python, so fractional/half-day leaves are truncated
  in the displayed columns.

---

## 4. Views & UI (`report/report_balance_leave_views.xml`)
| Record | id | Purpose |
|---|---|---|
| Search view | `report_balance_leave_view_search` | "Group By": **Employee** (`emp_id`), **Department** (`department_id`), **Leave Type** (`leave_type_id`), **Job** (`job_id`), **Gender** (`gender`). No text filters defined. |
| Tree view | `report_balance_leave_view_tree` | `create="0"` (read-only). Columns: employee, gender, country (Nationality), department, job, leave type, allocated / taken / balance days. |
| Action | `report_balance_leave_action` | `act_window` on `report.balance.leave`, `view_mode = tree,pivot,graph`, empty domain, bound search view. **Pivot and Graph views are not defined explicitly** — Odoo auto-generates them from the model fields. |
| Menu | `report_balance_leave_menu_root` | "Leave Balance Report", parent `hr_holidays.menu_hr_holidays_report` (Time Off → Reporting), `sequence=3`. |

No form view is defined (the report is list/pivot/graph only).

---

## 5. Reports (PDF / XLSX)
**N/A.** Despite the module name, there is **no QWeb-PDF report and no XLSX report**. The
"report" here is an analytical **screen view** (tree/pivot/graph) backed by a SQL view —
not a printable document. There is no `ir.actions.report`, no `report/*.xml` QWeb template,
and no XLSX/`report_xlsx` dependency. Users print via the standard list/pivot export
(Print → or the pivot/list "Download xlsx" built into Odoo), not via a module-defined
report.

## 6. Crons
**N/A.** No `ir.cron` records. The SQL view is always live; nothing is scheduled.

## 7. Settings
**N/A.** No `res.config.settings` extension and no `ir.config_parameter`. README states
"No additional configurations needed."

## 8. Security (`security/`)
- `ir.model.access.csv` — a single ACL `access_report_balance_leave` on
  `model_report_balance_leave` with **read/write/create/unlink all = 1** and **no
  `group_id`** (so it applies to all internal users). Note: write/create/unlink are
  granted in the CSV but are effectively no-ops because the model is a read-only SQL view
  (`_auto = False`) and the tree view sets `create="0"`.
- `report_balance_leave_security.xml` — one `ir.rule`
  `report_balance_leave_rule_multi_company` ("Time Off Balance Report: multi company
  rule") with domain `['|', ('company_id','=',False), ('company_id','in',company_ids)]`,
  so each user only sees rows for their allowed companies.

> Load order in `__manifest__.py` `data`: security XML and CSV load **before** the view
> file, as required (the report view references the model/action that the security file's
> `model_id` ref relies on existing).

## 9. Assets / JS
**N/A.** No `static/src` JavaScript, SCSS, OWL components or asset bundles. The
`static/description/` folder contains only the Cybrosys store listing (`index.html`,
`banner.png`, `icon.png`, screenshots and marketing icons) — these are **not** loaded by
Odoo at runtime (the manifest only references `static/description/banner.png` via
`images`).

## 10. Gotchas & notes (read before debugging)
- **Read-only SQL view:** `_auto = False`. To change what the report shows you edit the
  `CREATE VIEW` SQL in `report/report_balance_leave.py::init()`, then run a module `-u`
  (which re-executes `init()` and rebuilds the view). Editing only the Python field list
  without updating the SQL `SELECT` will desync columns.
- **Inner join hides employees without an allocation** — see §3.2. If a leave type is
  "missing" for someone, check whether they actually have an `hr.leave.allocation` of that
  type.
- **`taken_days` counts only `state = 'validate'`** — leaves in `validate1`
  (second-level-approval) or any other state are excluded. Adjust the `CASE` if the client
  uses two-step approval.
- **No period scoping** — the view aggregates across all years. There is no year/date
  filter in the SQL or the search view; "remaining balance" is lifetime, not annual.
- **Possible SUM inflation** with multiple allocations per (employee, leave type) — the
  allocation × leave cross join multiplies the leave-day sum. Reconcile against Odoo's
  native Time Off allocation/balance before using for anything official.
- **Integer fields truncate** half-day leaves.
- **Module name vs. content:** "Report" here means an analytical view, not a printable
  PDF/XLSX (see §5). Don't go looking for a QWeb template — there isn't one.
- **Third-party (Cybrosys) module** under AGPL-3. Keep the copyright headers. Original
  authors: Athul (V16), Fathima Mazlin AM (V17). Upstream support: odoo@cybrosys.com.

## 11. File map
```
__manifest__.py                              depends=hr_holidays · data (security, view) · AGPL-3
__init__.py                                  → report
README.rst                                   Cybrosys readme (store text)
doc/RELEASE_NOTES.md                         v17.0.1.0.0 — initial commit (03.04.2024)
report/
    __init__.py                              → report_balance_leave
    report_balance_leave.py                  report.balance.leave model (_auto=False SQL view + init())
    report_balance_leave_views.xml           search / tree / act_window action / menu
security/
    ir.model.access.csv                      single ACL, all internal users, no group
    report_balance_leave_security.xml        multi-company ir.rule
static/description/                          Cybrosys store listing only (NOT loaded at runtime):
    index.html · banner.png · icon.png · assets/{icons,misc,modules,screenshots}/*
```

---

### Quick orientation for the next developer
This is one of the simplest module shapes in Odoo: a single `_auto = False` model whose
entire behaviour is one SQL `CREATE VIEW` in `init()`, surfaced as a grouped tree/pivot/
graph under Time Off → Reporting. There is no Python logic, no wizard, no cron, no JS, no
printable report, and no settings. To extend it (add a column, change the "taken"
definition, add a year filter), edit the SQL in
`report/report_balance_leave.py`, mirror any new column as a `fields.*` on the model and a
`<field>` in the tree/search views, then `-u` and restart.
