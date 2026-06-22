# ent_ohrms_loan — Developer Handover Documentation

> **Enterprise OpenHRMS Loan Management** — the **Enterprise (`hr_payroll`) variant** of the
> Open-HRMS staff-loan module for Odoo 17. Lets employees request a **loan/advance**, splits it
> into monthly **installments**, runs it through a **draft → submitted → approved** workflow,
> and then **auto-deducts each installment from the employee's payslip** via a dedicated
> `LO` salary rule. This is a third-party Cybrosys / Open-HRMS module (OPL-1 licensed), lightly
> used as-is. UI labels are English; Arabic exists only as an `i18n/ar_001.po` translation.
> Read this before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `ent_ohrms_loan` |
| Display name | Enterprise OpenHRMS Loan Management |
| Version | `17.0.1.0.0` |
| Odoo | 17.0 Enterprise |
| License | OPL-1 (Odoo Proprietary) |
| Author | Cybrosys Techno Solutions / Open HRMS |
| Depends | `base`, `hr_payroll`, `hr`, `account` |
| External Python libs | **None beyond stdlib** — `datetime`, `dateutil.relativedelta` (ships with Odoo) |
| New models | `hr.loan` (Loan Request), `hr.loan.line` (Installment Line) |
| Inherited models | `hr.employee`, `hr.payslip`, `hr.payslip.input`, `hr.payslip.input.type`, `hr.payroll.structure`, `hr.salary.rule` |
| Reports / Wizards / Crons / JS assets | **None** (N/A — see §6, §7, §11) |
| Application | `False` (it slots a menu under the standard **Employees** app) |

### Deployment (this server)
- DB: `odoo17` · service: `odoo-17.service` (systemd) · runs as user `odoo`.
- Python venv: `/home/odoo/.pyenv/versions/odoo-17-env/bin/python`
- Odoo bin: `/home/odoo/odoo-17.0+e.20241205/odoo-bin` · conf: `/home/odoo/odoo.conf`
- Addons path includes `/home/odoo/care` (this repo, branch `17`).
- **Update + restart:**
  ```bash
  sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
    /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
    -d odoo17 -u ent_ohrms_loan --stop-after-init --no-http
  sudo systemctl restart odoo-17.service
  ```
- No dev mode. The module ships no JS/SCSS, so no asset-bundle concerns. Log file:
  `/var/log/odoo/odoo-17.log`.

---

## 2. Relationship to `ohrms_loan` (Community variant)

> ⚠️ **Critical:** the sibling module `/home/odoo/care/ohrms_loan` ("Open HRMS Loan Management")
> is the **Community** edition of the same feature. **Both define the very same `hr.loan` /
> `hr.loan.line` models** and the same `LO` salary rule/input plumbing. They are
> **mutually exclusive — do not install both** (duplicate model definitions, duplicate XML
> ids would collide / fight on update).

| | `ent_ohrms_loan` (this module) | `ohrms_loan` (community) |
|---|---|---|
| Payroll dependency | **`hr_payroll`** (Enterprise) | `hr_payroll_community` |
| Models | identical (`hr.loan`, `hr.loan.line`) | identical |
| Inherited payroll views | `hr_payroll.*` view refs | `hr_payroll_community.*` view refs |

Functionally the two are the same loan workflow; the **only** real difference is which payroll
engine they bind to. Since this server runs Odoo 17 **Enterprise**, **`ent_ohrms_loan` is the
correct one** to keep installed.

---

## 3. Architecture overview

```
hr.loan  (Loan Request — mail.thread, mail.activity.mixin)
│   name (LO/0001 from ir.sequence)  ·  employee_id  ·  loan_amount
│   installment (count)  ·  payment_date (start)  ·  state machine
│   total/balance/total_paid (computed, stored)
│
├── one2many → hr.loan.line   (one row per monthly installment)
│        date · amount · paid · loan_id · employee_id · payslip_id
│
└── action_compute_installment()  ──generates──►  the installment lines
                                                  (loan_amount / installment, +1 month each)

Workflow:  draft ──submit──► waiting_approval_1 ──approve──► approve
                 └──cancel──► cancel        └──refuse──► refuse   (manager-gated)

Payroll integration (the payback half):
  hr.salary.rule  "LO"  (category DED, python: result = - inputs['LO'].amount)
        ▲ attached to ▼
  hr.payroll.structure "Regular Pay"   ◄── ir sequence + data records seed all this
        │
  hr.payslip.compute_sheet()  ── finds approved loan installments whose date ∈ payslip
        │                          period, not yet paid → pushes them as an "Other Input"
        ▼                          line of type LO  (input.loan_line_id ← the installment)
  hr.payslip.action_payslip_done() ── marks each linked installment line.paid = True
                                       and recomputes the loan balance

hr.employee (inherited)   loan_count smart-button → action_loans (list of this emp's loans)
hr.payroll.structure / hr.salary.rule (inherited)   + company_id (multi-company, hidden field)
hr.payslip.input / .input.type (inherited)   + loan_line_id / input_id link fields
```

**Design notes**
- The loan **request** and the loan **repayment** are two halves wired together by the `LO`
  code: the salary rule reads `inputs['LO']`, and `compute_sheet` injects that input line from
  the matching, due, unpaid installment.
- All money rollups (`total_amount`, `balance_amount`, `total_paid_amount`) are **stored
  computed** fields driven by `_compute_loan_amount` (recomputed explicitly after compute and
  after payslip-done; see Gotchas §11).

---

## 4. Data model

### 4.1 `hr.loan` — Loan Request (`models/hr_loan.py`)
`_name = 'hr.loan'` · `_inherit = ['mail.thread', 'mail.activity.mixin']` · `_description = "Loan Request"`

| Field | Type | Purpose / notes |
|---|---|---|
| `name` | Char | Loan reference, default `/`, **readonly**; set on create from sequence `hr.loan.seq` → `LO/0001` |
| `date` | Date | Request date, default today, readonly |
| `employee_id` | M2o `hr.employee` | **required**; defaulted in `default_get` to the employee linked to the current/`context user_id` |
| `department_id` | M2o `hr.department` | related (readonly) from `employee_id.department_id` |
| `job_position_id` | M2o `hr.job` | related (readonly) from `employee_id.job_id` |
| `installment` | Integer | Number of installments, default `1` |
| `payment_date` | Date | **required**, "Payment Start Date", default today — first installment date |
| `loan_amount` | Float | **required**, total principal |
| `loan_line_ids` | O2m `hr.loan.line` | the generated installment schedule (indexed) |
| `total_amount` | Float | stored computed = `loan_amount` |
| `balance_amount` | Float | stored computed = `loan_amount − Σ paid installments` |
| `total_paid_amount` | Float | stored computed = `Σ paid installments` |
| `company_id` | M2o `res.company` | default = user's company |
| `currency_id` | M2o `res.currency` | **required**, default = company currency |
| `state` | Selection | `draft` / `waiting_approval_1` (label **"Submitted"**) / `approve` / `refuse` / `cancel`; tracked, `copy=False`, default `draft` |

**Computed logic — `_compute_loan_amount(self)`** (no `@api.depends`; called explicitly):
sums `amount` of installment lines where `paid` is True → sets `total_paid_amount`,
`balance_amount = loan_amount − total_paid`, and `total_amount = loan_amount`.

**Key methods / workflow:**
- `default_get(field_list)` — pre-fills `employee_id` from the current user (or a `user_id`
  passed in context).
- `create(values)` — **guard:** raises `ValidationError("The employee has already a pending
  installment")` if the employee already has an **approved** loan with non-zero `balance_amount`
  (one active loan at a time). Then assigns `name` from the `hr.loan.seq` sequence.
  > Note: uses the deprecated `ir.sequence.get('hr.loan.seq')` API and a single-record
  > `@api.model create` signature (not the batched `create(vals_list)`). Works on 17 but is
  > old-style — see Gotchas.
- `action_compute_installment()` — **wipes** `loan_line_ids` and regenerates them:
  `amount = loan_amount / installment`, one line per installment starting at `payment_date`,
  each `+1 month` (`relativedelta(months=1)`), then recomputes totals. Button label
  **"Compute Installment"**.
- `action_submit()` → `waiting_approval_1`; `action_cancel()` → `cancel`;
  `action_refuse()` → `refuse`.
- `action_approve()` — **guard:** raises `ValidationError("Please Compute installment")` if
  there are no installment lines; otherwise → `approve`. (Button gated to `hr.group_hr_manager`.)
- `unlink()` — refuses deletion unless state is `draft` or `cancel`
  (`UserError`).

### 4.2 `hr.loan.line` — Installment Line (`models/hr_loan_line.py`)
`_name = "hr.loan.line"` · `_description = "Installment Line"`

| Field | Type | Purpose |
|---|---|---|
| `date` | Date | **required**, scheduled payment date of this installment |
| `employee_id` | M2o `hr.employee` | employee (copied from parent loan) |
| `amount` | Float | **required**, installment amount |
| `paid` | Boolean | set True once deducted on a confirmed payslip |
| `loan_id` | M2o `hr.loan` | parent loan |
| `payslip_id` | M2o `hr.payslip` | back-reference to the payslip (defined but not actively written by this module's code) |

### 4.3 `hr.employee` (inherited — `models/hr_employee.py`)
- `loan_count` (Integer, computed `_compute_loan_count`) — `search_count` of `hr.loan` for the
  employee, used by the form smart-button.
  > ⚠️ Bug-ish: `_compute_loan_count` uses `self.id` inside the `for record in self` loop
  > instead of `record.id`. Harmless on single records (form view) but would mis-count in a
  > multi-record context. Left as-shipped.
- `action_loans()` — `ensure_one()`; returns an act_window opening this employee's loans
  (tree,form) with `context={'create': False}`.

### 4.4 `hr.payslip` (inherited — `models/hr_payslip.py`)
The repayment engine. Three overrides/helpers:
- `compute_sheet()` — for each payslip: if the structure contains a salary rule with `code == 'LO'`,
  finds the employee's **approved** `hr.loan`; if its `loan_line_ids` has an installment whose
  `date` falls within `[date_from, date_to]` and is **not paid**, and no `LO` input already
  exists on the payslip, it calls `input_data_line(...)` to add an Other-Input line. Then calls
  `super().compute_sheet()`.
- `input_data_line(name, amount, loan)` — builds a `(0,0,{...})` input line of
  `input_type_id` = the `hr.payslip.input.type` whose `input_id` is the `LO` salary rule,
  `amount`, `name='LO'`, and `loan_line_id` = the installment line; assigns it to
  `input_line_ids`.
- `action_payslip_done()` — on confirming the payslip, every input line that has a
  `loan_line_id` is marked `paid = True` and its loan's `_compute_loan_amount()` is re-run so
  the balance drops. Then calls `super()`.

### 4.5 Small inherited helpers
- `hr.payslip.input` (`models/hr_payslip_input.py`) → adds `loan_line_id` (M2o `hr.loan.line`),
  the link that lets `action_payslip_done` find which installment a payslip input paid off.
- `hr.payslip.input.type` (`models/hr_payslip_input_type.py`) → adds `input_id`
  (M2o `hr.salary.rule`), used to resolve the `LO` input type from the `LO` rule.
- `hr.payroll.structure` (`models/hr_payroll_structure.py`) → adds `company_id` (multi-company,
  readonly, hidden in view).
- `hr.salary.rule` (`models/hr_salary_rule.py`) → adds `company_id` (same).

---

## 5. Views & menus (`views/`)

| File | What it adds |
|---|---|
| `hr_loan_views.xml` | **Tree** (name, employee, loan_amount, date, state), **Form** (header workflow buttons + statusbar, employee/amount/installment group, **Installments** notebook page with editable line tree and a subtotal footer showing total/paid/balance, chatter), **Search** (filter *My Requests*; group-by employee/department/status), `hr_loan_action` (default filter `my requests`), and the **menus**: `Loans & Advances` → `Loan` → `Request for Loan`, all under the standard HR root (`hr.menu_hr_root`). |
| `hr_employee_views.xml` | Inherits `hr.view_employee_form` → adds the **Loans** smart-button (`fa-money`, `action_loans`, `loan_count`). |
| `hr_payslip_views.xml` | Inherits `hr_payroll.view_hr_payslip_form` → adds the (invisible) `loan_line_id` field to the Other-Inputs line tree. |
| `hr_payroll_structure_views.xml` | Inherits `hr_payroll.view_hr_employee_grade_form` → adds the (invisible) `company_id`. |
| `hr_salary_rule_views.xml` | Inherits `hr_payroll.hr_salary_rule_form` → adds the (invisible) `company_id`. |

**Form workflow buttons:** *Compute Installment* (hidden when state ∈ approve/refuse),
*Submit* + *Cancel* (draft only), *Approve* + *Refuse* (manager only, `hr.group_hr_manager`,
shown for submitted). Several edit fields (`employee_id`, `loan_amount`, `installment`,
`payment_date`) become readonly once `state == 'approve'`.

**Wizards:** **N/A** — no `TransientModel` / wizard in this module.

---

## 6. Reports
**N/A** — the module ships **no QWeb/PDF reports**. (The `static/description/*` images are the
Odoo App-Store listing assets, not Odoo reports.)

---

## 7. Crons / automation
**N/A** — no `ir.cron`. The only "automation" is payslip-driven: installments are picked up and
marked paid as part of the normal **Compute Sheet** / **Confirm payslip** payroll flow (§4.4).

---

## 8. Settings / config parameters
**N/A** — no `res.config.settings` and no `ir.config_parameter`. Behaviour is fixed in code/data:
- One active (approved, non-zero-balance) loan per employee (enforced in `create`).
- Installment cadence is **monthly** (hard-coded `relativedelta(months=1)`).
- The `LO` rule/structure/sequence come from the seed data (§9).

---

## 9. Seed data (`data/`)

| File | Records |
|---|---|
| `ir_sequence_data.xml` | `ir.sequence` **`hr.loan.seq`** — prefix `LO/`, padding 4 (`LO/0001`). `noupdate="1"`. |
| `hr_payroll_structure_data.xml` | `hr.payroll.structure` **"Regular Pay"** (`hr_payroll_structure_regular_pay`), type = employee, no country, with unpaid-leave work-entry type. |
| `hr_salary_rule_data.xml` | `hr.salary.rule` **"Loan"** code **`LO`**, category `hr_payroll.DED` (deduction), python condition `result = 'LO' in inputs`, amount python `result = - inputs['LO'].amount`, `sequence 190`, attached to the *Regular Pay* structure. |
| `hr_payslip_input_type_data.xml` | `hr.payslip.input.type` **"Loan"** code **`LO`**, `input_id` → the `LO` salary rule. |

These four together are what make loan installments flow into payroll as a negative (deduction)
line. The `LO` code is the linchpin across all of them.

---

## 10. Security (`security/`)

### `ir.model.access.csv`
| Model | Group | R | W | C | U(nlink) |
|---|---|---|---|---|---|
| `hr.loan` | `base.group_user` | ✓ | ✓ | ✓ | ✗ |
| `hr.loan.line` | `base.group_user` | ✓ | ✓ | ✓ | ✗ |
| `hr.job` | `base.group_user` | ✓ | ✓ | ✓ | ✗ |
| `hr.loan` | `hr.group_hr_user` (officer) | ✓ | ✓ | ✓ | ✓ |
| `hr.loan.line` | `hr.group_hr_user` | ✓ | ✓ | ✓ | ✓ |
| `hr.loan` | `hr.group_hr_manager` | ✓ | ✓ | ✓ | ✓ |
| `hr.loan.line` | `hr.group_hr_manager` | ✓ | ✓ | ✓ | ✓ |

> Note: every internal user (`base.group_user`) can **create** loan requests but cannot delete
> them; only HR officers/managers can unlink (and even then `unlink()` blocks non-draft/cancel).

### `hr_loan_security.xml` (record rules, all `noupdate="1"`)
- `hr_loan_rule_group_user` — **global** multi-company rule:
  `company_id = False OR company_id child_of user.company_id`.
- `hr_loan_rule_group_hr_user` — full CRUD on `hr.loan` for `hr.group_hr_user`.
- `hr_loan_rule_group_user_own_loan` — `base.group_user` may read/write/create/unlink **only
  their own** loans (`employee_id.user_id = user.id`).

**Approval gate:** the *Approve*/*Refuse* buttons are restricted to `hr.group_hr_manager` in the
view; there is no separate dedicated loan group — it reuses the standard HR groups.

---

## 11. Assets / JS
**N/A** — no OWL components, no `web.assets_*` bundles, no SCSS/JS. The `static/description/`
tree is App-Store listing artwork only.

---

## 12. Gotchas & notes (read before debugging)

- **Do NOT install alongside `ohrms_loan`** (§2). They define the same models and will collide.
  On this Enterprise server, `ent_ohrms_loan` is the right one.
- **One active loan per employee:** `create()` blocks a new loan while the employee has an
  approved loan with non-zero balance. To grant a second loan, the first must be fully paid
  (balance 0) or refused/cancelled.
- **You must "Compute Installment" before approving** — `action_approve()` errors with *"Please
  Compute installment"* if there are no lines. The `LO` salary rule reads `inputs['LO']`, so an
  approved loan with no installment whose date hits the payslip period simply won't deduct.
- **Installment matching is period- and date-bound:** `compute_sheet` only injects an installment
  whose `date` ∈ `[date_from, date_to]` of the payslip **and** `paid == False`, and only if no
  `LO` input already exists on that payslip. Mis-set payment dates ⇒ silent no-deduction.
- **`paid` is flipped on `action_payslip_done`, not on compute.** If a payslip is computed but
  never confirmed, the installment stays unpaid and the balance doesn't move.
- **`_compute_loan_amount` has no `@api.depends`** — it's invoked manually (after compute, after
  payslip-done). If you change installments via other code paths, call it (or
  `loan._compute_loan_amount()`) yourself or `balance_amount` will go stale.
- **`_compute_loan_count` uses `self.id` not `record.id`** (§4.3) — fine for the single-record
  form button it serves; don't reuse it in batch.
- **Old-style API:** `create(values)` is `@api.model` single-record and uses the deprecated
  `ir.sequence.get(code)` (vs `next_by_code`). Still functions in 17; modernise carefully if you
  touch it (and keep the sequence side-effect + the pending-loan guard).
- **Salary rule is a hard deduction** (`category DED`, negative amount) appearing at sequence
  190 on the *Regular Pay* structure. An employee paid on a different structure that lacks the
  `LO` rule will never have loans deducted.
- **No reports/crons/settings/JS** — keep expectations modest; this is the stock Cybrosys loan
  module, not a customised one. Arabic is translation-only (`i18n/ar_001.po`).

---

## 13. File map
```
__manifest__.py                       depends: base, hr_payroll, hr, account
README.rst · doc/RELEASE_NOTES.md      App-store readme / changelog (v17.0.1.0.0)
i18n/ar_001.po                         Arabic translation (UI labels stay English)

models/
  __init__.py
  hr_loan.py            hr.loan  (request, workflow, installment generation)  ← core
  hr_loan_line.py       hr.loan.line  (installment row)
  hr_employee.py        +loan_count smart-button / action_loans
  hr_payslip.py         compute_sheet / input_data_line / action_payslip_done (deduction)
  hr_payslip_input.py        +loan_line_id link
  hr_payslip_input_type.py   +input_id (→ salary rule)
  hr_payroll_structure.py    +company_id
  hr_salary_rule.py          +company_id

data/
  ir_sequence_data.xml              hr.loan.seq  (LO/0001)
  hr_payroll_structure_data.xml     "Regular Pay" structure
  hr_salary_rule_data.xml           LO deduction rule
  hr_payslip_input_type_data.xml    LO input type

security/
  hr_loan_security.xml              multi-company + own-loan record rules
  ir.model.access.csv              user/officer/manager ACLs

views/
  hr_loan_views.xml                 tree/form/search + menus (Loans & Advances → Loan)
  hr_employee_views.xml             Loans smart-button on employee form
  hr_payslip_views.xml              loan_line_id on payslip inputs
  hr_payroll_structure_views.xml    company_id (hidden)
  hr_salary_rule_views.xml          company_id (hidden)

static/description/                  App-Store listing assets only (no runtime assets)
```
