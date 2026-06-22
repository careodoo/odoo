# employee_late_check_in — Developer Handover Documentation

> **Employee Late Check-in** — a Cybrosys Technologies community add-on for Odoo 17
> that tracks how late employees check in (vs. their contract working schedule) and
> turns that lateness into a **payroll deduction**. A daily cron scans attendances,
> creates `late.check.in` records for employees over a configurable threshold, an HR
> manager approves/refuses them, and the approved penalty amounts flow into the
> payslip via a salary input + salary rule. UI is **English**. This file is the
> single source of truth for handover — read it before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `employee_late_check_in` |
| Display name | Employee Late Check-in |
| Version | `17.0.1.0.0` (manifest) — RELEASE_NOTES also lists a `17.0.1.0.1` bug-fix entry |
| Category | Human Resources |
| Odoo | 17.0 |
| Author / License | Cybrosys Techno Solutions · **LGPL-3** |
| Depends | `hr_attendance`, `hr_payroll_community`, `hr_contract` |
| External Python libs | **`pytz`** + stdlib `datetime` only (no third-party services) |
| New model | `late.check.in` |
| Inherited models | `hr.attendance`, `hr.employee`, `hr.employee.public`, `hr.payslip`, `res.company`, `res.config.settings` |
| Cron | 1 daily (`Attendance: Late Check-in`) |
| Salary rule / structure | `late_check_in` (code **LC**, category DED) + `late_check_in_salary_structure` (code **LCS**) |

> ⚠️ The parent bundle folder `employee_late_check_in-17.0.1.0.0/` also ships
> `hr_payroll_community`. **This document covers ONLY `employee_late_check_in`.**
> `hr_payroll_community` is a hard dependency (the salary rule, payslip inputs and
> `DED` category all come from it).

### Deployment (this server)
DB `odoo17` · systemd `odoo-17.service` · runs as user `odoo`. Update + restart:
```bash
sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
  /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
  -d odoo17 -u employee_late_check_in --stop-after-init --no-http
sudo systemctl restart odoo-17.service
```
> Requires the `pytz` package in the Odoo venv (it ships with Odoo, so normally
> present). No dev mode. Addons path includes `/home/odoo/care`.

---

## 2. Architecture overview

```
                  ┌─────────────────────────────────────────┐
   daily ir.cron  │ hr.attendance  (inherited)               │
  ───────────────▶│  • late_check_in (Integer, computed,     │
  late_check_in_  │    stored)  ← minutes late vs schedule   │
  records()       │  • late_check_in_records()  (cron body)  │
                  │  • unlink() override (cascade clean-up)  │
                  └───────────────┬─────────────────────────-┘
                                  │ create / update
                                  ▼
                  ┌─────────────────────────────────────────┐
                  │ late.check.in  (NEW model)               │
                  │  employee_id · late_minutes · date       │
                  │  attendance_id · penalty_amount (comp.)  │
                  │  state: draft→approved→deducted / refused│
                  │  approve() / reject()                    │
                  └───────────────┬─────────────────────────-┘
        approved records          │ pulled by date range + state=approved
                                  ▼
                  ┌─────────────────────────────────────────┐
                  │ hr.payslip  (inherited)                  │
                  │  late_check_in_ids (M2m)                 │
                  │  get_inputs() → adds input code "LC"     │
                  │  action_payslip_done() → mark 'deducted' │
                  └───────────────┬─────────────────────────-┘
                                  ▼
                  salary rule LC (category DED) → result = -amount

  res.company / res.config.settings  ── config_parameters ──▶ used by both
    deduction_amount · deduction_type · late_check_in_after · maximum_minutes

  hr.employee / hr.employee.public  ── smart button (late_check_in_count) ──▶
    opens that employee's late.check.in records
```

**Design notes**
- Detection runs in a **daily cron**, not in real time. `late_check_in` minutes are a
  stored computed field on `hr.attendance`; the cron materialises `late.check.in`
  rows from attendances that pass the threshold.
- Tunables are stored as **`ir.config_parameter`** values (written from Settings),
  so HR can change deduction amount/type and thresholds without code edits.
- Payroll integration is **input-based**: approved penalties become a payslip input
  (`LC`), consumed by the `late_check_in` salary rule.

---

## 3. Data model

### 3.1 `late.check.in`  (NEW — `models/late_check_in.py`)
The core record: one late check-in event for one employee.

| Field | Type | Notes |
|---|---|---|
| `name` | Char (readonly) | sequence reference (`LC00001…`), set in `create()` |
| `employee_id` | M2o `hr.employee` | the late employee |
| `late_minutes` | Integer | minutes late |
| `date` | Date | the attendance check-in date |
| `penalty_amount` | Float (computed, **not stored**) | `_compute_penalty_amount` — amount to deduct |
| `state` | Selection | `draft → approved → deducted`, or `refused` (default `draft`) |
| `attendance_id` | M2o `hr.attendance` | source attendance (1:1 link used for dedup/cleanup) |

**Methods:**
- `create(vals_list)` — `@api.model`; assigns `name` from sequence `late.check.in`
  (`next_by_code`, fallback `'/'`), then `super(...).create(vals_list)` under `sudo()`.
  > ⚠️ Signature is the legacy single-dict `create` (not v17 batch `@api.model_create_multi`).
  > It mutates `vals_list['name']` directly, so callers must pass a single dict (the cron does).
- `_compute_penalty_amount()` — reads `deduction_amount` config param. If
  `deduction_type == 'minutes'`, `penalty_amount = amount × late_minutes`; otherwise
  (`total`) it is the flat `amount`.
  > ⚠️ Has **no `@api.depends`** — it is a manual compute, recomputed on read, never stored.
  > It reads the **bare** param key `deduction_amount`/`deduction_type` (see Gotchas §10).
- `approve()` → `state = 'approved'`.
- `reject()` → `state = 'refused'`.

### 3.2 `hr.attendance`  (inherited — `models/hr_attendance.py`)
| Field | Type | Notes |
|---|---|---|
| `late_check_in` | Integer (computed, **stored**) | minutes late vs the contract morning schedule |

**Methods:**
- `_compute_late_check_in()` — `@api.depends('check_in')`. For each attendance with a
  contract, iterates `contract_id.resource_calendar_id.attendance_ids`; for the line
  matching the check-in **weekday** and `day_period == 'morning'`, it converts the
  UTC `check_in` to **the current user's timezone** (`self.env.user.tz`), compares the
  time-of-day against the schedule's `hour_from`, and stores the positive difference in
  minutes. Defaults to `0.0` when not late or no morning schedule.
  > ⚠️ Only **morning** schedule lines are checked, and it uses **`self.env.user.tz`**
  > (the running user — the cron runs as `base.user_root`), not the employee's tz. See §10.
- `late_check_in_records()` — **the cron body**. Reads `late_check_in_after` (min
  threshold) and `maximum_minutes` (upper bound) config params (bare keys, default 0).
  For every attendance: if no `late.check.in` exists for it yet and
  `late_check_in > minutes_after` **and** `minutes_after < late_check_in < max_limit`,
  it creates a `late.check.in`; if a record already exists it updates its
  `late_minutes`/`date`/`attendance_id`.
  > ⚠️ The guard is doubled/contradictory: `rec.late_check_in > minutes_after AND
  > minutes_after < rec.late_check_in < max_limit`. The second clause subsumes the
  > first, so effectively a record is created only when
  > `minutes_after < late_check_in < max_limit`. An attendance at or above `max_limit`
  > is intentionally ignored (treated as absence/other leave — see Settings help text).
- `unlink()` — override: deletes the matching `late.check.in` rows before deleting the
  attendance.
  > ⚠️ Bug to be aware of: the `return super().unlink()` sits **inside** the `for record
  > in self` loop, so on a multi-record unlink it returns after the first record. Cleanup
  > of later records' late.check.in rows may be skipped. Fine for single-record unlinks.

### 3.3 `hr.employee`  (inherited — `models/hr_employee.py`)
| Field | Type | Notes |
|---|---|---|
| `late_check_in_count` | Integer (computed, not stored) | count of this employee's `late.check.in` records |

- `_compute_late_check_in_count()` — `search_count` on `late.check.in`. **No `@api.depends`**.
- `action_to_open_late_check_in_records()` — returns an act_window opening
  `late.check.in` filtered to this employee (`view_mode tree,form`, limit 80). Backs the
  smart button.

### 3.4 `hr.employee.public`  (inherited — `models/hr_employees_public.py`)
Mirror of 3.3 on the public employee model (`late_check_in_count` +
`action_to_open_late_check_in_records` + `_compute_late_check_in_count`) so the smart
button works for users who only see the public employee record.

### 3.5 `hr.payslip`  (inherited — `models/hr_payslip.py`)
| Field | Type | Notes |
|---|---|---|
| `late_check_in_ids` | M2m `late.check.in` | approved late records pulled onto the payslip |

- `get_inputs(contracts, date_from, date_to)` — `@api.model` override. Searches
  `late.check.in` for the payslip's employee within the period and `state == 'approved'`,
  sets `late_check_in_ids`, and appends one input dict using the **`LC`** salary input
  type (`employee_late_check_in.late_check_in`) with `amount = sum(penalty_amount)`.
  > ⚠️ It calls `super().get_inputs(contracts, date_to, date_from)` — **date_to and
  > date_from are passed swapped** to super. It then uses `self.date_to`/`self.date_from`
  > for its own search, so this module's logic is correct, but be careful if super's
  > behaviour depends on argument order.
- `action_payslip_done()` — marks every linked `late_check_in_ids` record as
  `state = 'deducted'`, then calls super.

### 3.6 `res.company`  (inherited — `models/res_company.py`)
Adds company-level fields backing the (company-dependent) settings:
`deduction_amount` (Float), `currency_id` (M2o, default company currency),
`maximum_minutes` (Char), `late_check_in_after` (Char), `deduction_type`
(Selection `minutes`/`total`, default `minutes`).

### 3.7 `res.config.settings`  (inherited — `models/res_config_settings.py`)
TransientModel exposing the same four tunables as **`config_parameter`** fields, prefix
`employee_late_check_in.`:
`deduction_amount`, `maximum_minutes` (Char, default `"240"`), `late_check_in_after`
(Char), `deduction_type` (default `"minutes"`), plus `currency_id`.
`set_values()` ALSO writes the **bare** param keys (`deduction_amount`,
`maximum_minutes`, `late_check_in_after`, `deduction_type`) via `set_param` — see §10,
this is the bridge between the settings form and what the runtime code reads.

---

## 4. Views (`views/*.xml`)

- **`late_check_in_views.xml`** — defines:
  - `ir.sequence` `late.check.in` (prefix `LC`, padding 5).
  - **Form** (`create="false"`): statusbar (`draft,approved`), **Approve** / **Refuse**
    buttons (visible only in `draft`, group `hr.group_hr_manager`), and the record fields.
    `employee_id` is hidden once out of draft.
  - **Search**: Group-By **Employee**.
  - **Tree**: name, employee, late_minutes, date, penalty_amount.
  - Window action `late_check_in_action` (default group-by employee) + menu
    **Late Check-in** under `hr_attendance.menu_hr_attendance_root` (group
    `hr.group_hr_user`).
- **`hr_attendance_views.xml`** — adds the `late_check_in` column to the standard
  attendance tree (after `check_out`).
- **`hr_employee_views.xml`** — adds the **Late Check-In** smart button
  (`oe_stat_button`, `fa-clock-o`, `statinfo` widget) to both `hr.employee` and
  `hr.employee.public` forms.
- **`hr_payslip_views.xml`** — adds `late_check_in_ids` (invisible) to the payslip form
  so the M2m is populated/saved.
- **`res_config_settings_views.xml`** — adds a **Late Check-in** block inside the HR
  Attendance settings app: Deduction Amount + Deduction Type, Late Check-in Starts After
  (minutes), Maximum Late Minute (minutes). All `company_dependent="1"`.

**Wizards:** N/A (no `wizards/` directory).

---

## 5. Reports
**N/A** — the module ships no QWeb/PDF reports. Output is purely the payroll deduction
(salary rule `LC`) and the `late.check.in` list/form views. The `static/description/`
assets are Cybrosys store marketing (banner, screenshots, icon, `index.html`), **not**
loaded by Odoo at runtime.

---

## 6. Crons (`data/ir_cron_data.xml`)

| Cron | Model | Method | Schedule | User |
|---|---|---|---|---|
| **Attendance: Late Check-in** (`ir_cron_late_check_in`) | `hr.attendance` | `model.late_check_in_records()` | every **1 day**, `numbercall=-1`, `doall=False` | `base.user_root` |

`forcecreate="True"`. This is the only automation entry point — it scans **all**
attendances each run (`self.sudo().search([])`) and materialises/updates
`late.check.in` records. Because it runs as root, the timezone used by
`_compute_late_check_in` is root's `tz` (see §10).

---

## 7. Settings & config parameters

Set via **Settings → HR Attendance → Late Check-in** (`res.config.settings`). Each
field is `config_parameter` `employee_late_check_in.<key>` **and** `set_values()` also
writes the bare `<key>`. The runtime code (attendance cron + penalty compute) reads the
**bare keys**:

| Setting (label) | config_parameter key | bare key read at runtime | Used by |
|---|---|---|---|
| Deduction Amount | `employee_late_check_in.deduction_amount` | `deduction_amount` | `_compute_penalty_amount` |
| Deduction Type (Per Minutes / Per Total) | `employee_late_check_in.deduction_type` | `deduction_type` | `_compute_penalty_amount` |
| Late Check-in Starts After (min) | `employee_late_check_in.late_check_in_after` | `late_check_in_after` | `late_check_in_records` (lower threshold) |
| Maximum Late Minute (min, default 240) | `employee_late_check_in.maximum_minutes` | `maximum_minutes` | `late_check_in_records` (upper bound) |

**Behaviour:** an attendance lateness `L` produces a record only when
`late_check_in_after < L < maximum_minutes`. `Per Minutes` → penalty = amount × minutes;
`Per Total` → penalty = flat amount.

---

## 8. Salary rule & structure (`data/salary_rule.xml`)

- `late_check_in` (`hr.salary.rule`) — name **Late Check-in**, code **`LC`**,
  sequence 6, category `hr_payroll_community.DED` (deduction). `amount_select = code`;
  the Python compute reads `inputs.LC.amount` and returns `result = -amount`
  (negative → deducted). Wrapped in try/except defaulting to 0.
- `late_check_in_salary_structure` (`hr.payroll.structure`) — code **`LCS`**, name
  *Base Salary Structure For Late Check-in*, rule_ids = basic + net + taxable +
  `late_check_in`, company `base.main_company`.

> The `late_check_in` salary rule record is also referenced by id as the **salary input
> type** in `hr_payslip.get_inputs()` (`self.env.ref('employee_late_check_in.late_check_in')`,
> used for `.name` and `.code`). The input `code` lands as `inputs.LC` in the rule.

---

## 9. Security (`security/ir.model.access.csv`)

Only model granted is `late.check.in`:

| Group | read | write | create | unlink |
|---|---|---|---|---|
| `hr.group_hr_manager` | ✓ | ✓ | ✗ | ✓ |
| `hr.group_hr_user` | ✓ | ✓ | ✗ | ✗ |
| `base.group_user` | ✓ | ✗ | ✗ | ✗ |

> No group has model-level **create** — records are created by the cron/`get_inputs`
> under **`sudo()`** (`create` and `late_check_in_records` both sudo). The form view is
> `create="false"`. **Approve/Refuse buttons are gated to `hr.group_hr_manager`** in the
> view. No record rules (`rules.xml`) and no custom groups (`groups.xml`) — N/A.

---

## 10. Gotchas & notes (read before debugging)

- **Two key namespaces for the same settings.** Settings store values under
  `employee_late_check_in.<key>` (the `config_parameter`) AND, via `set_values()`,
  under the **bare `<key>`**. The runtime code (`_compute_penalty_amount`,
  `late_check_in_records`) reads the **bare keys**. If you ever set params only through
  the prefixed key (e.g. via `ir.config_parameter` UI or a data file), the runtime won't
  see them — always go through the Settings form, which writes both.
- **Timezone is the *current user's*, not the employee's.** `_compute_late_check_in`
  uses `self.env.user.tz`. The cron runs as `base.user_root`, so root's timezone decides
  what "late" means for everyone. If lateness looks wrong, check root user's tz.
- **Only morning schedule is evaluated.** Lateness is computed against the
  `day_period == 'morning'` calendar line of the matching weekday. Afternoon-only or
  split shifts won't trigger detection.
- **Threshold guard is redundant/over-constrained.** In `late_check_in_records` the
  condition `late_check_in > minutes_after AND minutes_after < late_check_in < max_limit`
  reduces to `minutes_after < late_check_in < max_limit`. Lateness ≥ `max_limit` is
  deliberately skipped (treated as absence per the settings help text).
- **`unlink()` returns inside the loop** — multi-record deletes may leave orphan
  `late.check.in` rows for records after the first. Safe for single deletes.
- **`create()` is legacy single-dict + mutates the arg.** Not `@api.model_create_multi`;
  pass one dict. The `_compute_penalty_amount` has no `@api.depends`, nor does
  `_compute_late_check_in_count` — they recompute on every read.
- **`get_inputs` passes `date_to, date_from` to super swapped.** Module logic uses
  `self.date_*`, so it works, but don't "fix" the call without checking super.
- **No real-time detection.** Records appear only after the daily cron runs; a payslip
  generated before the cron won't include that day's lateness.
- **Cron scans every attendance every run** (`search([])`) — on large attendance tables
  this is O(all rows) daily; acceptable for typical HR volumes but watch performance.
- **Hard dependency on `hr_payroll_community`** (the community payroll add-on shipped in
  the same bundle) for `DED` category, payslip inputs, and structure rules. `hr_contract`
  is required for the employee→working-schedule link used in detection.

---

## 11. Assets / JS
**N/A** — no `web.assets_*` bundles, no OWL/JS. `static/description/` is store marketing
only and is not served by Odoo.

---

## 12. File map
```
__manifest__.py                  depends (hr_attendance, hr_payroll_community, hr_contract) / data list
README.rst · doc/RELEASE_NOTES.md
models/
  hr_attendance.py               late_check_in field + compute + cron body + unlink override
  hr_employee.py                 late_check_in_count smart button (hr.employee)
  hr_employees_public.py         same smart button on hr.employee.public
  hr_payslip.py                  late_check_in_ids + get_inputs (LC input) + action_payslip_done
  late_check_in.py               NEW model late.check.in (penalty, state machine, sequence)
  res_company.py                 company-level tunable fields
  res_config_settings.py         settings form + set_values (writes bare param keys)
data/
  ir_cron_data.xml               daily cron "Attendance: Late Check-in"
  salary_rule.xml                LC salary rule (category DED) + LCS structure
security/
  ir.model.access.csv            late.check.in ACLs (manager/user/base.group_user)
views/
  late_check_in_views.xml        sequence + form/tree/search + action + menu
  hr_attendance_views.xml        late_check_in column on attendance tree
  hr_employee_views.xml          smart buttons (employee + public)
  hr_payslip_views.xml           invisible late_check_in_ids on payslip
  res_config_settings_views.xml  Late Check-in settings block
static/description/              store marketing assets (NOT loaded by Odoo)
```
