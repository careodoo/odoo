# care_timesheet — Developer Handover Documentation

> **Care Timesheet** — a small custom Odoo 17 module that reconciles **employee
> attendance** over a date interval against an expected/target count, computes the
> shortfall, and **back-fills the missing `hr.attendance` records** automatically when an
> approver approves the document. In short: pick a department + date range, generate a line
> per employee with their *actual* attendance count, type in the *target* count, and on
> approval the module creates synthetic attendance records for the difference (on days the
> employee did **not** already work, respecting the employee's working-calendar weekdays).
> UI labels are English. Read this before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `care_timesheet` |
| Display name | Care Timesheet |
| Summary | "compare employee attendance within time interval and create new attendance records based on it" |
| Version | `0.1` (manifest) — runs on Odoo 17 |
| Author | Ahmed Gaber |
| Depends | `base`, `hr`, `hr_attendance` |
| External Python libs | none beyond stdlib `datetime` + `dateutil.relativedelta` (already in Odoo) |
| New models | `care.timesheet`, `care.timesheet.line` |
| Inherited models | `hr.attendance` |
| Sequence | `care.timesheet` → prefix `CT`, padding 3 |
| Reports | none |
| Crons | none |
| Assets/JS | none |

### Deployment (this server)
DB `odoo17` · systemd `odoo-17.service` · user `odoo`. Update + restart:
```bash
/home/odoo/.pyenv/versions/odoo-17-env/bin/python \
  /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
  -d odoo17 -u care_timesheet --stop-after-init --no-http
sudo systemctl restart odoo-17.service
```
- Addons path includes `/home/odoo/care` (this repo, branch `17`).
- No dev mode. The `-u` reloads data/views; the restart serves the running workers.
- Log file: `/var/log/odoo/odoo-17.log`.

---

## 2. Architecture overview

```
care.timesheet  (the reconciliation document — draft → submit → approved)
├── header: name (CT-seq), date_from, date_to, department_id, company_id, state, active
└── one2many → care.timesheet.line   (one row per employee in the department)
        ├── employee_id  (hr.employee)
        ├── actual   (Integer)  attendance days the employee ALREADY has in range
        ├── count    (Integer)  TARGET attendance count (typed in by user)
        └── diff     (Integer, computed/stored = count - actual, must be ≥ 0)

hr.attendance  (inherited)
├── department_id      related → employee_id.department_id   (stored, enables fast grouping)
└── care_timesheet_id  many2one → care.timesheet  (back-link tagging records this doc created)

Workflow:
  button_generate_timesheet  → (re)build lines from current attendance counts (raw SQL)
  button_submit              → state = 'submit'
  button_approve             → for each line with diff>0: create `diff` hr.attendance
                               records on free calendar-weekdays; state = 'approved'
```

**Design notes**
- Counting is done in **raw SQL** straight against `hr_attendance` (`self.env.cr.execute`)
  for speed and simplicity, not via the ORM.
- The relationship between the document and the records it generated is captured by the
  `care_timesheet_id` field added to `hr.attendance`, so generated records are traceable.
- There is no report, no cron, no JS, no config parameter — this is a focused two-model
  CRUD + workflow module.

---

## 3. Data model

### 3.1 `care.timesheet` (`models/care_timesheet.py`)
The reconciliation document. `_description = 'Care Timesheet'`. No `_inherit`, no chatter.

| Field | Type | Notes |
|---|---|---|
| `name` | Char | Reference; `required`, `copy=False`, `readonly`, `index`, default `_('New')`. Filled from the `care.timesheet` ir.sequence on create (prefix `CT`). |
| `line_ids` | One2many `care.timesheet.line` (inverse `timesheet_id`) | the per-employee rows |
| `date_from` | Date | "From", required — start of the interval |
| `date_to` | Date | "To", required — end of the interval |
| `department_id` | Many2one `hr.department` | which department to reconcile |
| `company_id` | Many2one `res.company` | required, default `self.env.company` |
| `state` | Selection `draft` / `submit` (Submitted) / `approved` | default `draft` |
| `active` | Boolean | default `True` (archiving) |

**Constraints / overrides**
- `check_dates` (`@api.constrains('date_from','date_to')`): raises `UserError`
  *"Date From shouldn't before Date To !"* when `date_from > date_to`.
  > ⚠️ **Bug note:** the constraint loops `for rec in self` but then compares `self.date_from`
  > / `self.date_to` (singleton attribute access on a possibly-multi recordset) instead of
  > `rec.date_from` / `rec.date_to`. Harmless on single-record saves; would raise a
  > singleton error on a multi-record write. The message wording is also reversed
  > ("shouldn't before" should read "shouldn't be after").
- `create(vals)` (`@api.model`): if `name` is still `'New'`, pulls the next value from the
  `care.timesheet` sequence (`CT###`). Uses the legacy single-dict signature, not the v17
  `@api.model_create_multi` batch form.

**Workflow methods**
- **`button_generate_timesheet()`** — clears `line_ids` (`(5,0,0)`), then runs raw SQL:
  ```sql
  SELECT employee_id, count(id) FROM hr_attendance
  WHERE department_id = %s AND check_in::date >= %s AND check_in::date <= %s
  GROUP BY employee_id
  ```
  and creates one line per employee with `actual = count(id)` (their existing attendance
  days in range). This relies on the **`department_id` column added to `hr.attendance`** by
  this module (see 3.3).
  > ⚠️ **Note:** lines are written one-at-a-time inside the loop via
  > `self.line_ids = [(0,0,{...})]`; each assignment is a separate write. Functionally it
  > appends, but it is not batched.
- **`button_submit()`** — sets `state = 'submit'`.
- **`button_approve()`** — the core logic. For each line where `diff > 0`:
  1. Reads the employee's `resource_calendar_id`: `hours = calendar.hours_per_day` and the
     set of working weekdays `calendar.attendance_ids.mapped('dayofweek')`.
  2. `get_worked_days(emp, start, end)` returns the dates the employee **already** has
     attendance on (raw SQL on `hr_attendance`).
  3. Builds `all_possible_days` = every date in `[date_from, date_to]` whose
     `str(weekday())` is a working weekday of the calendar; then
     `available_days = all_possible_days − worked_days` (set difference, **order not
     guaranteed**).
  4. For `i in range(line.diff)`: creates an `hr.attendance` with
     `check_in = available_days[i]`, `check_out = check_in + hours`, and
     `care_timesheet_id = self.id` (tagging the generated record).
  5. `line.actual += line.diff` and `line.count = 0`.
  Finally sets `state = 'approved'`.
  > ⚠️ **Gotchas in approve:**
  > - `available_days` comes from a Python `set` difference → **unordered**;
  >   `available_days[i]` picks arbitrary free days, and if `diff` exceeds the number of
  >   free working days an **`IndexError`** is raised (no guard).
  > - `available_days[i]` is a `date`; `check_in` on `hr.attendance` is a `Datetime`.
  >   Odoo coerces the date to midnight UTC — generated check-ins land at 00:00, and TZ is
  >   not applied.
  > - Setting `line.count = 0` recomputes `diff` to 0 (see line model), so re-approving is
  >   effectively neutralised; `actual` already absorbed the difference.
- **`get_worked_days(emp, start, end)`** — helper: raw SQL selecting `check_in` for the
  employee in range, returns a list of `check_in.date()` values.

### 3.2 `care.timesheet.line` (`models/care_timesheet.py`)
One row per employee on a document. `_description = 'Care Timesheet Line'`.

| Field | Type | Notes |
|---|---|---|
| `timesheet_id` | Many2one `care.timesheet` | parent document |
| `employee_id` | Many2one `hr.employee` | the employee |
| `actual` | Integer | attendance days the employee currently has (filled by generate / incremented on approve) |
| `count` | Integer | **target** attendance count, typed by the user |
| `diff` | Integer, `compute='compute_diff'`, `store=True` | `count - actual` (the shortfall to back-fill) |

- `compute_diff` (`@api.depends('actual','count')`): `diff = 0` unless **both** `actual`
  and `count` are truthy, then `diff = count - actual`.
  > ⚠️ Because the guard is `if rec.actual and rec.count`, a line with `actual = 0`
  > (employee never attended) keeps `diff = 0` and gets **no** records generated — a
  > zero-actual employee is silently skipped.
- `check_diff` (`@api.constrains('diff')`): raises `UserError`
  *"{employee} count should be more than actual!"* when `diff < 0` (target below actual).

### 3.3 `hr.attendance` (inherited — `models/hr_attendance.py`)
`_inherit = 'hr.attendance'`. Adds two fields:

| Field | Type | Notes |
|---|---|---|
| `department_id` | Many2one `hr.department`, `related="employee_id.department_id"`, `store=True` | denormalised + stored so `button_generate_timesheet`'s SQL can filter/group by department directly on the table |
| `care_timesheet_id` | Many2one `care.timesheet` | back-link tagging attendance records created by a given timesheet document |

> The **stored** `department_id` is load-bearing: the generate/approve SQL queries
> `hr_attendance.department_id` directly. If it were non-stored related, the SQL would
> break (no column).

---

## 4. Views (`views/`)

### 4.1 `care.timesheet` views (`views/care_timesheet.xml`)
- **Tree** (`care_timesheet_view_tree`): `name`, `date_from`, `date_to`, `department_id`,
  `state` as a **badge** (`decoration-success` when `approved`, `decoration-warning` when
  `submit`). `active` hidden.
- **Form** (`care_timesheet_view_form`): header with three buttons —
  **Submit** (`button_submit`, visible only when `state == 'draft'`),
  **Approve** (`button_approve`, visible only when `state == 'submit'`),
  **Generate Timesheet** (`button_generate_timesheet`, always visible) — plus the `state`
  statusbar. Body: title `name`, a group with `date_from` / `department_id` / `date_to`,
  and a **Lines** notebook page with an `editable="bottom"` tree over `line_ids`:
  `employee_id` (readonly, `force_save="1"`), `actual` (readonly, `force_save="1"`),
  `count` (editable), `diff` (readonly compute).
  > `force_save="1"` lets the readonly `employee_id`/`actual` values persist even though the
  > fields are readonly in the UI.
- **Action** `care_timesheet_action`: window action on `care.timesheet`, `view_mode
  tree,form`, name **"Timesheet"**.
- **Menus**: root menu `care_timesheet_root` (**"Timesheet"**, sequence 50, gated by
  `group_care_timesheet_user`) → child `care_timesheet_menu` ("Timesheet") opening the
  action. The root menu has **no parent** (it is a top-level menu).

### 4.2 `hr.attendance` view extension (`views/hr_attendance.xml`)
`care_view_attendance_tree` inherits the standard `hr_attendance.view_attendance_tree` and
adds the `care_timesheet_id` column after `check_out`, so generated attendance rows show
which timesheet document created them.

There are **no** search, kanban, pivot, or graph views, and no wizards.

---

## 5. Data / sequence (`data/sequence.xml`)
One `ir.sequence` record `seq_care_timesheet`: name "Care Timesheet", code
`care.timesheet`, prefix `CT`, padding `3`, `company_id = False` (global, not per-company).
Consumed by `care.timesheet.create`. Names look like `CT001`, `CT002`, …

---

## 6. Security (`security/`)
- **`groups.xml`** — module category `module_care_timesheet` ("Care Timesheet") and two
  groups:
  - `group_care_timesheet_user` — **User**.
  - `group_care_timesheet_approver` — **Approver**, `implied_ids` includes the User group
    (an approver is also a user).
- **`ir.model.access.csv`**:
  | Model | Group | R | W | C | U(nlink) |
  |---|---|---|---|---|---|
  | `care.timesheet` (`..._u`) | `group_care_timesheet_user` | ✓ | ✓ | ✓ | ✓ |
  | `care.timesheet` (`..._a`) | `group_care_timesheet_user` | ✓ | ✓ | ✓ | ✓ |
  | `care.timesheet.line` (`..._u`) | `group_care_timesheet_user` | ✓ | ✓ | ✓ | ✓ |
  | `care.timesheet.line` (`..._a`) | `group_care_timesheet_approver` | ✓ | ✓ | ✓ | ✓ |
  > ⚠️ **Note:** the second `care.timesheet` ACL row (`access_care_timesheet_a`, meant for
  > the approver) is actually pointed at `group_care_timesheet_user`, not the approver group
  > — likely a copy/paste slip. Functionally both groups still get full access (approver
  > implies user), so it is harmless but worth fixing for clarity.
- **`rules.xml`** — three record rules on `care.timesheet`:
  - `care_timesheet_comp_rule` — **global** multi-company rule:
    `['|',('company_id','=',False),('company_id','in',company_ids)]`.
  - `care_timesheet_rule_user_own` — users (`group_care_timesheet_user`) see only their own
    documents: `[('create_uid','=',user.id)]`.
  - `care_timesheet_rule_manager` — approvers (`group_care_timesheet_approver`) see all:
    `[(1,'=',1)]`.
  > The approval gate is enforced purely by **button visibility + the approver record rule**,
  > not by field-level locks. `button_approve` itself does **not** check the user's group —
  > anyone who can see the Approve button (state submitted) and reach the record can run it.
  > There are also **no** ACL/record rules declared for `hr.attendance` here — it relies on
  > the standard `hr_attendance` module's security.

---

## 7. Reports / Crons / Settings / Assets
- **Reports:** none.
- **Cron jobs:** none.
- **Settings / config parameters:** none (no `res.config.settings` inheritance).
- **Assets / JS / SCSS / OWL:** none.

---

## 8. Gotchas & notes (read before debugging)
- **`available_days` ordering & `IndexError`** — `button_approve` fills shortfalls from an
  **unordered** set difference and indexes it directly; if `diff` exceeds the number of free
  working days in the range, `available_days[i]` throws `IndexError`. There is no guard.
- **Zero-actual employees are skipped** — `compute_diff` only sets `diff` when *both*
  `actual` and `count` are truthy, so an employee with no existing attendance (`actual = 0`)
  always gets `diff = 0` and no back-fill.
- **Date vs Datetime** — generated `check_in`/`check_out` use a `date` placed into a
  `Datetime` field → midnight, no timezone handling. Generated attendance lands at 00:00.
- **`check_dates` constraint uses `self.` not `rec.`** — works for single-record saves;
  would raise a singleton error on multi-record writes. The error wording is also inverted.
- **Stored related `department_id` on `hr.attendance` is required** — the generate/approve
  raw SQL filters/groups by `hr_attendance.department_id`. Keep `store=True`.
- **No chatter / no logging** — the document has no `mail.thread`; approvals leave no audit
  trail beyond `create_uid` and the `care_timesheet_id` tag on generated attendances.
- **Legacy `create` signature** — uses `@api.model def create(self, vals)`, not the v17
  `@api.model_create_multi`. Fine on 17 but flagged by linters; batch creates still route
  through it.
- **ACL approver row mislinked** — see §6 (`access_care_timesheet_a` references the *user*
  group). Harmless but a correctness wart.
- **Module metadata is boilerplate** — manifest `category` is "Uncategorized", `website` is
  the placeholder `http://www.yourcompany.com`; tidy if publishing.

---

## 9. File map
```
__manifest__.py                  name/summary/depends(base,hr,hr_attendance)/data list
__init__.py                      → models
models/
  __init__.py                    → care_timesheet, hr_attendance
  care_timesheet.py              care.timesheet + care.timesheet.line (workflow + raw SQL)
  hr_attendance.py               hr.attendance inherit: department_id (stored related) + care_timesheet_id
data/
  sequence.xml                   ir.sequence care.timesheet (prefix CT, padding 3)
security/
  groups.xml                     User / Approver groups + module category
  ir.model.access.csv            ACLs for care.timesheet(.line)
  rules.xml                      multi-company + own/all record rules
views/
  care_timesheet.xml             tree/form, action, menus (top-level "Timesheet")
  hr_attendance.xml              adds care_timesheet_id column to attendance tree
```
