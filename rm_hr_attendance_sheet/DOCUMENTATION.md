# rm_hr_attendance_sheet — Developer Handover Documentation

> **HR Attendance Sheet And Policies** — a third-party Odoo 17 module (CDS Solutions /
> Ramadan Khalil) that turns raw `hr.attendance` check-in/out punches into a per-employee,
> per-month **Attendance Sheet**. For every calendar day it compares the employee's
> *planned* working hours (from the contract's `resource.calendar`) against the *actual*
> attendance, then computes **overtime, late-in, early-out ("diff time"), and absence**
> hours, applying configurable **Attendance Policies** (rate/fixed rules with escalating
> 1st–5th-occurrence factors). Sheets feed a `hr.payslip` via salary rules. UI is English.
> This file is the handover source of truth — read it before touching the code.

> ⚠️ This is a **vendor module under OPL-1 license** (`'license': 'OPL-1'`, paid module,
> `'price': 99`). The code header says *"It is forbidden to publish, distribute,
> sublicense, or sell copies."* Treat edits as local customizations to a purchased addon,
> not as owned source.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `rm_hr_attendance_sheet` |
| Display name | HR Attendance Sheet And Policies |
| Version | `17.0` (manifest) |
| Odoo | 17.0 (Enterprise — depends on `hr_payroll`) |
| Depends | `base`, `hr`, `hr_payroll`, `hr_holidays`, `hr_attendance` |
| External Python libs | `pytz`, `python-dateutil` (`relativedelta`), `babel` (all already in the Odoo venv) — **no extra pip install needed** |
| Author / vendor | CDS Solutions SRL, Eng. Ramadan Khalil (`rkhalil1990@gmail.com`) |
| License | OPL-1 (paid) |
| Main models | `attendance.sheet`, `attendance.sheet.line`, `hr.attendance.policy` |
| New models (total) | 14 (sheet, line, batch, policy + 5 rule models + 4 rule-line models, public holiday, change wizard) |
| Inherited models | `hr.contract`, `hr.payslip`, `resource.calendar` |
| Menus | English labels, under **Attendances** and **Time Off** apps |

### Deployment (this server)
- DB: `odoo17` · service: `odoo-17.service` (systemd) · runs as user `odoo`.
- Python venv: `/home/odoo/.pyenv/versions/odoo-17-env/bin/python`
- Odoo bin: `/home/odoo/odoo-17.0+e.20241205/odoo-bin` · conf: `/home/odoo/odoo.conf`
- Addons path includes `/home/odoo/care` (this repo, branch `17`).
- **Update + restart:**
  ```bash
  sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
    /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
    -d odoo17 -u rm_hr_attendance_sheet --stop-after-init --no-http
  sudo systemctl restart odoo-17.service
  ```
- No dev mode. After a successful `-u`, restart the service to serve the new state.
  Log file: `/var/log/odoo/odoo-17.log`.

---

## 2. Architecture overview

```
hr.attendance  (standard — raw check_in/check_out punches)
        │  read-only source, queried per day
        ▼
attendance.sheet  (one per employee per month — mail.thread.cc + mail.activity.mixin)
├── employee_id      → hr.employee
├── contract_id      → hr.contract        (resolved from employee + period)
├── att_policy_id    → hr.attendance.policy (taken from the contract)
├── batch_id         → attendance.sheet.batch  (optional, bulk generation)
├── payslip_id       → hr.payslip          (created on approval)
└── line_ids  one2many → attendance.sheet.line   (ONE LINE PER DAY)
         each line: planned in/out, actual in/out, worked_hours,
                    overtime / late_in / diff_time (+ act_* raw values),
                    status (ab / weekend / ph / leave)

hr.attendance.policy   (the rule engine container)
├── overtime_rule_ids  m2m → hr.overtime.rule    (workday / weekend / ph: after + rate)
├── late_rule_id       m2o → hr.late.rule    → hr.late.rule.line   (time threshold, rate/fix, 1st–5th factors)
├── diff_rule_id       m2o → hr.diff.rule    → hr.diff.rule.line    (same shape as late)
└── absence_rule_id    m2o → hr.absence.rule → hr.absence.rule.line (counter 1–5 → rate)

resource.calendar (inherited)  → adds att_get_work_intervals / att_interval_clean /
                                  att_interval_without_leaves (planned-interval helpers)
hr.public.holiday  (new model) → per-employee / department / tag holiday calendar
hr.contract (inherited)        → att_policy_id, auto_attendance_sheet, attendance_sheet_based
hr.payslip  (inherited)        → attendance_sheet_ids + computed overtime/late/absence/diff totals
attendance.sheet.line.change   (TransientModel wizard) → manual override of one day's figures

Automation:  2 ir.cron (monthly create, daily update*) ·  data.xml seeds payroll plumbing
```

**Design principles**
- The **whole value of the module is `attendance.sheet.get_attendances()`** — a ~400-line
  per-day reconciliation of planned vs actual intervals (see §4.2). Everything else is
  plumbing around it.
- All deduction/allowance amounts live in **policy rules**, not code, so HR tunes behaviour
  without edits. Rules support escalating factors for repeat offences (1st late, 2nd late…).
- The sheet stores both the **raw measured value** (`act_overtime`, `act_late_in`,
  `act_diff_time`) and the **policy-applied value** (`overtime`, `late_in`, `diff_time`).
  Payroll deducts/pays from the policy-applied columns.

---

## 3. The day-status model (status values on each line)

Each `attendance.sheet.line` carries a `status` selection that drives the totals and the
payslip. **Keys are stable:**

| `status` key | Label | Meaning |
|---|---|---|
| `''` (empty) | — | Normal working day with attendance (overtime/late/diff computed) |
| `ab` | Absence | Working day with **no** attendance at all → counts as absence |
| `weekend` | Week End | Day outside the calendar's working intervals (any attendance = weekend overtime) |
| `ph` | Public Holiday | Matched an active `hr.public.holiday` (any attendance = PH overtime) |
| `leave` | Leave | A validated `hr.leave` overlapped the missing time (diff excused) |

`_compute_sheet_total` aggregates these into the header counters: `no_overtime`/`tot_overtime`,
`no_late`/`tot_late`, `no_absence`/`tot_absence` (lines where `diff_time>0 and status=="ab"`),
and `no_difftime`/`tot_difftime` (lines where `diff_time>0 and status!="ab"`).

---

## 4. Data model

### 4.1 `attendance.sheet` (`models/hr_attendance_sheet.py`)
`_inherit = ['mail.thread.cc', 'mail.activity.mixin']`. One sheet = one employee, one month.

**Identity / period:** `name` (auto: *"Attendance Sheet - <employee> - <Month Year>"*),
`employee_id` (required), `department_id` (related, stored), `company_id`, `date_from`
(defaults to 1st of current month), `date_to` (defaults to last day of current month),
`contract_id` (resolved, readonly except draft), `att_policy_id` (required, from contract),
`batch_id`, `payslip_id`.

**State machine** (`state`, readonly, indexed): `draft → confirm → done`
(Draft / Confirmed / Approved). Buttons: `action_confirm`, `action_approve`
(creates payslip + sets done), `action_draft`.

**Computed header totals** (`_compute_sheet_total`, all `store=True`, depend on the lines):
`no_overtime`, `tot_overtime`, `no_late`, `tot_late`, `no_absence`, `tot_absence`,
`no_difftime`, `tot_difftime`, `tot_worked_hour`.
> ⚠️ **`tot_worked_hour` is declared with the label `"Total Late In"` and is never assigned
> in `_compute_sheet_total`** — it stays 0. The payslip's `worked_hours` reads from it, so
> worked hours roll up as 0 today (see Gotchas).

**Key methods:**
- `onchange_employee()` (`@api.onchange` on employee/date_from/date_to) — builds `name`,
  sets `company_id`, resolves the contract via `employee._get_contracts(date_from, date_to)`,
  copies `contract.att_policy_id` onto the sheet. **Raises `ValidationError`** if no valid
  contract or no policy.
- `create()` / `write()` overrides call `onchange_employee()` so the contract/policy are
  re-resolved even on programmatic create (the inline comments call this *"fix deletion of
  contract"*).
- `get_attendances()` — **the core engine** (see §4.2). Wipes `line_ids` and rebuilds them.
  Bound to the form's **"Get Attendances"** button (draft only).
- `check_date()` (`@api.constrains`) — blocks overlapping sheets for the same employee.
- `unlink()` — the "can't delete confirmed/approved" guard is **commented out** (currently
  any sheet can be deleted; `pass` placeholder left in).
- `action_create_payslip()` / `action_payslip()` — create (once) and open an `hr.payslip`
  for the sheet's period, linking it via `attendance_sheet_ids` and calling `compute_sheet()`.
- `create_payslip()` — an **alternate, legacy** payslip builder using
  `onchange_employee_id`; not wired to any button. Large blocks of worked-day-line logic are
  commented out throughout this file.
- `_cron_generate_attendance_sheet()` — monthly cron (see §6).

### 4.2 `get_attendances()` — the reconciliation engine (read carefully before editing)
For each sheet, for each day in `[date_from, date_to]`:
1. Resolve the employee timezone (`emp.tz`, **required** — raises if missing) and the
   contract's `resource_calendar_id` (**required** — raises if missing).
2. Get the day's **planned work intervals** from the calendar via
   `att_get_work_intervals` (resource.calendar helper, §4.7), the **actual attendance
   intervals** from `hr.attendance` (`get_attendance_intervals`, completed punches only —
   rows with no `check_out` are skipped), validated **leaves** (`_get_emp_leave_intervals`,
   only `state == 'validate'`), and active **public holidays** (`get_public_holiday`).
3. Branch by day type:
   - **Working day + public holiday** → any attendance is paid as PH overtime
     (`ph_after` / `ph_rate`); status `ph`.
   - **Working day, normal** → for each planned interval, match overlapping attendance
     intervals; derive **late-in** (planned start → first actual in), **overtime** (last
     actual out beyond planned end), and **diff/early-out** (planned time not covered by
     attendance). If no attendance at all → status `ab` (absence). Leaves excuse the
     uncovered intervals (`att_interval_without_leaves`) and flip status to `leave`. Extra
     attendance outside any planned interval is logged as separate overtime lines
     ("overtime out of work intervals").
   - **Non-working day (weekend)** → any attendance is weekend overtime
     (`we_after` / `we_rate`); status `weekend`. No attendance → an empty `weekend` line.
4. Raw values pass through the policy methods (`get_late`, `get_diff`, `get_absence`,
   `get_overtime` thresholds) before being written to the line.

> Floats are **decimal hours** (e.g. `8.5` = 8h30) — every time field uses `widget="float_time"`.
> `_get_float_from_time` converts a tz-aware datetime to that decimal-hour float.
> All `hr.attendance` reads use `.sudo()`.

### 4.3 `attendance.sheet.line`
One **day** of a sheet. `att_sheet_id` (cascade), `employee_id` (related), `date`,
`day` (weekday selection `0`=Monday…`6`=Sunday), `state` (related to sheet, but with an
extra `sum`/`Summary` value in its own selection that the sheet state never sets).
Time fields (all decimal-hour floats, readonly): `pl_sign_in`, `pl_sign_out` (planned),
`ac_sign_in`, `ac_sign_out` (actual), `worked_hours`, `overtime` + `act_overtime`,
`late_in` + `act_late_in`, `diff_time` + `act_diff_time`, plus `status` and `note`.
The `act_*` columns are the **measured** values; the unprefixed columns are **after policy**.

### 4.4 `hr.attendance.policy` + rule models (`models/hr_attendance_policy.py`)
The policy is a container of rules with three evaluation helpers:

- **`get_overtime()`** → dict of `wd_/we_/ph_` × `rate`/`after`. Picks the first
  `hr.overtime.rule` of each `type` (`workday`/`weekend`/`ph`) linked via
  `overtime_rule_ids`. `active_after` = hours of overtime ignored before paying;
  `rate` = multiplier.
- **`get_late(period, cnt)`** / **`get_diff(period, cnt)`** → walk the rule's lines
  (`hr.late.rule.line` / `hr.diff.rule.line`) sorted by `time` threshold descending; the
  first line whose `time` ≤ the period applies. Line `type` is `rate` (`rate*period*factor`)
  or `fix` (`amount*factor`). **`first…fifth`** are escalation factors selected by how many
  times the employee already hit that threshold this sheet — `cnt` is a running counter list
  threaded through the day loop.
- **`get_absence(period, cnt)`** → `hr.absence.rule.line` keyed by `counter` (1st–5th
  absence) → `rate * period`. `cnt` here is the running absence-day index (`abs_cnt`).

Supporting models: `hr.overtime.rule` (name/type/active_after/rate), `hr.policy.overtime.line`
(an unused intermediate line model with an onchange copy from a rule), `hr.late.rule` +
`…line`, `hr.diff.rule` + `…line`, `hr.absence.rule` + `…line`.

### 4.5 `hr.public.holiday` (`models/hr_holidays.py`)
`_inherit = ['mail.thread']`. `name`, `date_from`/`date_to` (required), `state`
(`inactive`/`active`, default inactive — **only `active` ones count**), `note`.
Targeting: `type_select` (`emp`/`dep`/`tag`) with `emp_ids`/`dep_ids`/`cat_ids`. An
`@api.onchange` (`get_employee_ids`) expands department/tag selection into `emp_ids`.
`get_public_holiday()` on the sheet: if a PH has **no** `emp_ids` it applies to everyone;
otherwise only to listed employees.
> ⚠️ A leftover `print('ph is', …)` debug statement is in `get_public_holiday` (§ Gotchas).

### 4.6 `hr.contract` (inherited — `models/hr_contract.py`)
Adds `att_policy_id` (M2o policy), `auto_attendance_sheet` (Boolean — include in the
monthly cron), `attendance_sheet_based` (Boolean — payslip must use an approved sheet).

### 4.7 `resource.calendar` (inherited — `models/resource.py`)
Adds attendance helpers used by the engine: `_attendance_intervals` (single-resource wrapper
over the v17 batch API), `att_get_work_intervals` (planned intervals for a day, tz→UTC,
cleaned), `att_interval_clean` (merge/sort overlapping intervals), and
`att_interval_without_leaves` (subtract leave intervals from a planned interval).

### 4.8 `hr.payslip` (inherited — `models/hr_payroll.py`)
Adds `attendance_sheet_ids` (O2m, `ondelete='cascade'`) and computed totals
(`overtime_no/_hours`, `late_no/_hours`, `absent_no/_hours`, `diff_no/_hours`,
`worked_days`, `worked_hours`) summed from the linked sheets by `_compute_att_sheet_data`.
> ⚠️ `worked_days` is summed from a local var that's never incremented → always 0;
> `worked_hours` reads `sheet.tot_worked_hour` which is never set → always 0.
`set_payslip_attendance_sheet()` auto-links **approved** (`state='done'`) sheets in range.
`compute_sheet()` override: if `contract.attendance_sheet_based`, it requires an approved
sheet and raises `UserError` if none exists.

### 4.9 `attendance.sheet.batch` (`models/att_sheet_batch.py`)
Bulk generation per **department** for a period. State machine
`draft → att_gen → att_sub → done` (Draft / Sheets Generated / Sheets Submitted / Close).
`gen_att_sheet()` creates a sheet per employee in the department and runs `get_attendances()`;
`submit_att_sheet()` confirms all draft sheets; `action_done()` approves all confirmed
sheets (creating their payslips). Has an `ir.sequence` (`ASB######`) defined but the model
does not auto-assign it in code.

### 4.10 `attendance.sheet.line.change` (wizard — `wizard/change_att_data.py`)
TransientModel to **manually override** one day's `overtime` / `late_in` / `diff_time`,
with a **required `note`**. `default_get` pre-fills from the active line; `change_att_data()`
writes the values back. Manager-only button on each line (form, draft only).
> Note: it writes to the line but **does not retrigger** the sheet totals recompute —
> a commented-out `calculate_att_data()` call (a method that doesn't exist) is left in.

---

## 5. Views & menus

- **`hr_attendance_sheet_view.xml`** — sheet form (header buttons, period, PaySlip stat
  button when approved, **Attendances** tab = the day lines with a manager "edit data"
  button, **Attendance Data** tab = the four totals), list, line form, search
  (filters: To Approve / Approved; group by employee / start month).
  Menus: **Attendances → Attendance Sheets** (`attendance_sheet_menu`) → *Attendance sheets*.
  The module also grants the `hr_attendance` root menu to `group_attendance_sheet_user`.
- **`attendance_sheet_batch_view.xml`** — batch form/list + menu
  **Attendances → Attendance Sheets → Attendance sheet Batches**.
- **`hr_attendance_policy_view.xml`** — policy form (overtime rules inline + diff/late/absence
  rule pickers) and forms/lists for each rule model. Menus under
  **Attendances → Attendance Sheet Setting** (manager-only): *Attendances Policies* and
  *Attendance Rules → {OverTime, Late In, Difference Time, Absence} Rules*.
- **`hr_contract_view.xml`** — inherits `hr_payroll.hr_contract_form_inherit`, injects
  `att_policy_id` (**required**), `auto_attendance_sheet`, `attendance_sheet_based` after
  the salary structure type.
- **`hr_public_holiday_view.xml`** — public-holiday form/list + menu under
  **Time Off** (`hr_holidays.menu_hr_holidays_root`).
- **`hr_payslip_view.xml`** — adds an **Attendance Sheets** page to the payslip form
  (linked sheets + the five totals groups).
- **`resource_view.xml`** — declares a `resource.calendar` form view with an **empty
  `inherit_id`** and an essentially empty arch (legacy/no-op).
- **`wizard/change_att_data_view.xml`** — the override wizard dialog + its action.

> **Reports:** *N/A* — this module defines **no QWeb/PDF report templates**. It only
> declares a default `report.paperformat` (`paperformat_attendance_sheet`) in `data.xml`,
> which sets the global default A4 portrait paperformat but is not bound to any report here.

---

## 6. Automation (`data/ir_cron.xml`)

| Cron | Interval | Code | Status |
|---|---|---|---|
| Monthly Create Attendance Sheet | every 7 days | `model._cron_generate_attendance_sheet()` | **Works.** Creates current-month sheets for every employee on an `open` contract with `auto_attendance_sheet=True` and a policy; skips if a sheet already exists; calls `get_attendances()`. Errors are caught and logged, not raised. |
| Daily Update Attendance Sheet | every 12 hours | `model._cron_update_attendance_sheet(shift_days=0)` | **⚠️ BROKEN — method does not exist** on `attendance.sheet`. This cron raises `AttributeError` every run (logged in `ir_cron`). Either implement `_cron_update_attendance_sheet` or disable the cron. See Gotchas. |

---

## 7. Settings & seed data (`data/data.xml`, `data/ir_sequence.xml`)

`data.xml` (all `noupdate="1"`) wires the **payroll side**:
- 5 `hr.work.entry.type` (`ATTSHOT` overtime, `ATTSHLI` late, `ATTSHUL` unpaid leave,
  `ATTSHDT` diff, `ATTSHAB` absence).
- `hr.payroll.structure.type` **"Attendance Sheet"** + structure
  **"Attendance Sheet Salary Structure"** (its `default_struct_id`).
- 4 `hr.salary.rule` on that structure: **ABS** absence, **LATE** late-in, **DIFF**
  difference-time (all under category `DED`), and **OVT** overtime (category `ALW`).
  Each computes `±(<hours> * contract.wage / (9*26))` — i.e. a **9-hour day, 26-day month**
  daily-rate basis. Conditions key off the payslip's computed `*_no` fields.
  > ⚠️ The **OVT** rule's `amount_python_compute` uses `result = -(…)` (negative), so as
  > seeded overtime **deducts** rather than adds despite being in the allowance category.
  > Verify the sign before relying on overtime pay.
- A `Permission` `hr.leave.type` (hourly), the default `report.paperformat`, and a sample
  `resource.calendar` (Mon–Thu + Sun, 08:00–16:00).

`ir_sequence.xml`: sequence `attendance.sheet.batch` (prefix `ASB`, padding 6).

`demo/demo.xml` (loaded only with demo data): one employee "Ramadan Khalil", a month of
`hr.attendance` punches, a public holiday, and a full set of demo policy rules + contract.

---

## 8. Security (`security/`)

- `security.xml` — module category **"Attendance Sheet"** with two groups:
  - `group_attendance_sheet_user` (**User**) — implies `hr.group_hr_user`.
  - `group_attendance_sheet_manager` (**Manager**) — implies the User group.
  - Grants the Manager group to `base.user_admin`.
- `ir.model.access.csv` — User generally has **read on config models** (policies/rules) and
  **CRUD on sheets/lines/batches**; Manager has **CRUD everywhere**. The override wizard
  (`attendance.sheet.line.change`) is **manager-only** (matching the view button group).
  `hr.public.holiday` access is granted via the `hr_holidays` user/manager groups.
- No record rules (`ir.rule`) and no multi-company rules are defined — *N/A*. Sheets carry a
  `company_id` but isolation is not enforced by a record rule here.

**The approval gate** is enforced purely by the **`group_attendance_sheet_manager` group on
the `action_approve` button** in the form, not by record rules.

---

## 9. Assets / JS

*N/A* — no OWL components, no `web.assets_*` bundles, no SCSS/JS. `static/description/` holds
only the App-Store listing page (`index.html`, banner, screenshots, icons). The UI is plain
backend XML views.

---

## 10. Gotchas & notes (read before debugging)

- **Daily cron is broken.** `_cron_update_attendance_sheet(shift_days=0)` is referenced by
  `ir_cron_cds_hr_attendance_sheet_daily_update` but **never defined** → `AttributeError`
  every 12h. Disable the cron or implement the method. (The XML id even carries a stray
  `cds` prefix unlike its sibling.)
- **Worked hours roll up as 0.** `attendance.sheet.tot_worked_hour` is declared (mislabeled
  "Total Late In") but **never assigned** in `_compute_sheet_total`; the payslip's
  `worked_hours`/`worked_days` therefore compute to 0. The day lines *do* carry per-day
  `worked_hours`; only the header/payslip rollup is missing. Fix in `_compute_sheet_total`
  if payroll needs total worked hours.
- **Overtime salary rule sign.** The seeded **OVT** rule computes a **negative** amount
  (`result=-(…)`) under the allowance category — overtime would *reduce* net pay as shipped.
  Confirm/flip the sign per client requirement.
- **Engine prerequisites raise, not warn.** `get_attendances()` and `onchange_employee()`
  raise `ValidationError`/`Warning` if the employee has no timezone (`emp.tz`), no contract
  in range, no `resource_calendar_id` on the contract, or no attendance policy. Bulk/cron
  generation will fail loudly per employee for any of these.
- **Only validated leaves & completed punches count.** `hr.leave` is filtered to
  `state='validate'`; `hr.attendance` rows with no `check_out` are skipped entirely.
- **Only `active` public holidays count** (default is `inactive`) — newly created holidays
  must be set Active before regenerating sheets.
- **Leftover debug `print`** in `hr.public.holiday.get_public_holiday` (`print('ph is', …)`)
  spams stdout during generation — safe to remove.
- **Wizard override doesn't recompute totals.** Editing a day via the change wizard writes
  the line but the (nonexistent) `calculate_att_data()` recompute is commented out. Because
  the header totals are *stored computed* fields on `line_ids`, an ORM write *should*
  retrigger `_compute_sheet_total` — but the manual `overtime/late/diff` edits bypass the
  `act_*` columns, so audit figures and policy figures can diverge.
- **`unlink` guard disabled.** The "can't delete confirmed/approved sheet" check is commented
  out — any sheet is deletable. Re-enable in `attendance.sheet.unlink()` if needed.
- **`track_visibility='onchange'`** is used on several `state` fields — this is the **v8–v12
  spelling**; in v17 the attribute is `tracking=True`. It is silently ignored here, so state
  changes are **not tracked in the chatter**. Replace with `tracking=True` if audit trail
  matters.
- **Two payslip builders.** `action_create_payslip()` (used by Approve) and `create_payslip()`
  (legacy, unused) coexist. Don't wire the legacy one without testing.
- **Migrated/vendor v17 module:** views already use v17 `invisible="state != 'draft'"`
  Python-expression syntax (no `attrs`/`states`), so it loads cleanly on this server.
- **Daily-rate divisor `9*26` is hard-coded** in the salary rules (9h day, 26 working days).
  Edit the four `hr.salary.rule` records in `data.xml` (or override per-DB) to change it.

---

## 11. File map
```
__manifest__.py                     depends / data / demo
__init__.py                         imports wizard + models
models/
  hr_attendance_sheet.py            attendance.sheet (+ .line) — THE ENGINE (~900 lines)
  hr_attendance_policy.py           policy + overtime/late/diff/absence rules & rule lines
  att_sheet_batch.py                attendance.sheet.batch (department bulk generation)
  hr_holidays.py                    hr.public.holiday
  hr_contract.py                    hr.contract (att_policy_id, auto/based flags)
  hr_payroll.py                     hr.payslip (sheet link + computed totals + compute_sheet)
  resource.py                       resource.calendar interval helpers
wizard/
  change_att_data.py / _view.xml    attendance.sheet.line.change (manual day override)
data/
  data.xml                          work-entry types, payroll structure, salary rules, paperformat, leave type, sample calendar
  ir_cron.xml                       monthly create (works) + daily update (BROKEN)
  ir_sequence.xml                   ASB###### batch sequence
demo/demo.xml                       demo employee, punches, holiday, policy, contract
security/
  security.xml                      User / Manager groups + category
  ir.model.access.csv               per-model ACLs
views/
  hr_attendance_sheet_view.xml      sheet form/list/line/search + menus
  attendance_sheet_batch_view.xml   batch form/list + menu
  hr_attendance_policy_view.xml     policy + all rule views + setting menus
  hr_contract_view.xml              contract form injection
  hr_public_holiday_view.xml        public holiday form/list + Time Off menu
  hr_payslip_view.xml               payslip Attendance Sheets page
  resource_view.xml                 empty/no-op resource.calendar view (legacy)
static/description/                  App-Store listing assets only (no runtime JS/CSS)
LICENSE.md                          OPL-1
```
