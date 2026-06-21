# ohrms_loan — Developer Handover Documentation

> **Open HRMS Loan Management** (OSI / Open-HRMS, by Cybrosys) for Odoo 17.
> Lets staff raise **loan / advance requests** that go through a
> `draft → submitted → approved` workflow. On approval the loan is split into
> monthly **installments**, and each installment is automatically pulled into the
> employee's **payslip** as a salary deduction (rule code `LO`) and marked **paid**
> once the payslip is confirmed. UI is English; this client's DB also ships an
> Arabic translation (`i18n/ar_001.po`). Read this before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `ohrms_loan` |
| Display name | Open HRMS Loan Management |
| Version | `17.0` (manifest) |
| Odoo | 17.0 |
| Author / origin | Cybrosys Techno Solutions, Open HRMS — `https://www.openhrms.com` |
| License | AGPL-3 |
| Depends | `base`, `hr_payroll_community`, `hr`, `account` |
| External Python libs | `babel`, `dateutil` (stdlib-adjacent, already in the Odoo venv) — no special install |
| Key models | `hr.loan`, `hr.loan.line`, inherits `hr.employee`, `hr.payslip`, `hr.payslip.input` |
| Application | `False` (it slots under the existing **HR** app menu) |

> ⚠️ **Hard dependency: `hr_payroll_community`** (the OCA/community payroll, *not*
> Odoo Enterprise `hr_payroll`). The payslip view inherit, the `LO` salary rule and
> the `get_inputs()` override all target that module. If `hr_payroll_community` is
> not installed/updated, this module will not load.

### Deployment (this server)
DB `odoo17` · systemd `odoo-17.service` · runs as user `odoo` ·
addons path includes `/home/odoo/care` (this repo, branch `17`).

**Update + restart:**
```bash
/home/odoo/.pyenv/versions/odoo-17-env/bin/python \
  /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
  -d odoo17 -u ohrms_loan --stop-after-init --no-http
sudo systemctl restart odoo-17.service
```
- No dev mode. Run the `-u` (run it as the `odoo` user if your shell isn't already),
  then restart the service. Log file: `/var/log/odoo/odoo-17.log`.

---

## 2. Architecture overview

```
hr.loan  (Loan Request — mail.thread, mail.activity.mixin)
├── employee_id   → hr.employee   (required)
├── department_id → hr.department (related, readonly)
├── job_position  → hr.job        (related, readonly)
├── company_id / currency_id
├── state: draft → waiting_approval_1 (Submitted) → approve / refuse / cancel
└── one2many → hr.loan.line  (installment schedule)
                ├── date, amount, paid
                ├── loan_id    → hr.loan
                └── payslip_id → hr.payslip   (where it was deducted)

hr.employee (inherited)   loan_count  + stat button → loans
hr.payslip (inherited)    onchange_employee / get_inputs() pull due installment as input "LO"
                          action_payslip_done() → marks the installment paid
hr.payslip.input (inherited)  loan_line_id  (back-link from a payslip input to the installment)

Payroll wiring (data/salary_rule_loan.xml):
  hr.rule.input  "LO"  ──feeds──▶  hr.salary.rule "LO" (category DED, deduction)
  amount_python_compute:  result = inputs.LO and -(inputs.LO.amount)
```

**How the end-to-end flow works**
1. Employee/HR creates an `hr.loan`, sets `loan_amount`, `installment` (count) and
   `payment_date` (first installment date).
2. **Compute Installment** button (`compute_installment`) wipes and regenerates
   `loan_lines` — one line per month, `loan_amount / installment` each, monthly steps.
3. **Submit** → **Approve** (HR). Approval is blocked unless installment lines exist.
4. When a payslip is generated for that employee covering an installment's date,
   `get_inputs()` injects the installment amount into the payslip input row coded `LO`;
   the `LO` salary rule deducts it (negative, category DED).
5. **Confirming the payslip** (`action_payslip_done`) sets `loan.line.paid = True` and
   recomputes the loan balance.

---

## 3. Data model

### 3.1 `hr.loan` (`models/hr_loan.py`) — the Loan Request
`_name = 'hr.loan'` · `_inherit = ['mail.thread', 'mail.activity.mixin']` ·
`_description = "Loan Request"`

| Field | Type | Notes |
|---|---|---|
| `name` | Char | Loan reference, `readonly`, default `"/"`; set from sequence `hr.loan.seq` on create (`LO/0001`…) |
| `date` | Date | Request date, `readonly`, default today |
| `employee_id` | M2o `hr.employee` | **required**; auto-defaulted to the current user's employee (`default_get`) |
| `department_id` | M2o `hr.department` | `related="employee_id.department_id"`, readonly |
| `job_position` | M2o `hr.job` | `related="employee_id.job_id"`, readonly |
| `installment` | Integer | number of installments, default 1 |
| `payment_date` | Date | **required**, first installment date, default today |
| `loan_lines` | O2m `hr.loan.line` | the installment schedule (indexed) |
| `company_id` | M2o `res.company` | readonly, default user company; editable in `draft` (legacy `states={...}`) |
| `currency_id` | M2o `res.currency` | **required**, default company currency |
| `loan_amount` | Float | **required**, principal |
| `total_amount` | Float | stored, computed `_compute_loan_amount` — equals `loan_amount` |
| `balance_amount` | Float | stored, computed — `loan_amount − Σ paid installments` |
| `total_paid_amount` | Float | stored, computed — `Σ paid installments` |
| `state` | Selection | `draft / waiting_approval_1 (Submitted) / approve / refuse / cancel`; `tracking=True`, `copy=False`, default `draft` |

**Computed logic — `_compute_loan_amount()`**
Iterates `loan_lines`, sums `amount` where `paid` is True → `total_paid_amount`;
`balance_amount = loan_amount − total_paid`; `total_amount = loan_amount`. Called from
`compute_installment()` and from `action_payslip_done()` (in `hr_payroll.py`) so the
balance updates whenever an installment is paid.

**Key methods**
- `default_get(field_list)` — preselects `employee_id` from the loan's `user_id`
  (or the current user) so a self-service request is pre-filled.
- `create(values)` — **one-active-loan guard:** raises `ValidationError("The employee
  has already a pending installment")` if the employee already has an `approve` loan
  with non-zero `balance_amount`. Then assigns `name` from `ir.sequence` `hr.loan.seq`.
  > Note: uses the deprecated `ir.sequence.get(code)` API and the single-dict
  > (non-batch) `create` signature — works in 17 but is legacy style.
- `compute_installment()` — `loan_lines.unlink()` then creates `installment` lines from
  `payment_date`, each `loan_amount / installment`, stepping `+1 month`
  (`relativedelta`); recomputes amounts. **Re-running it rebuilds the whole schedule.**
- `action_submit()` → `waiting_approval_1` · `action_cancel()` → `cancel` ·
  `action_refuse()` → `refuse`.
- `action_approve()` — refuses to approve (`ValidationError "Please Compute
  installment"`) if there are no `loan_lines`; otherwise → `approve`.
- `unlink()` — blocks deletion (`UserError`) unless state is `draft` or `cancel`.

### 3.2 `hr.loan.line` (`models/hr_loan.py`) — Installment Line
`_name = "hr.loan.line"` · `_description = "Installment Line"`

| Field | Type | Notes |
|---|---|---|
| `date` | Date | **required**, due date of this installment |
| `amount` | Float | **required**, installment amount |
| `paid` | Boolean | set True when deducted on a confirmed payslip |
| `employee_id` | M2o `hr.employee` | |
| `loan_id` | M2o `hr.loan` | parent |
| `payslip_id` | M2o `hr.payslip` | payslip the installment was taken on (back-reference) |

### 3.3 `hr.employee` (inherited — `models/hr_loan.py`)
Adds `loan_count` (Integer, computed `_compute_employee_loans` — `search_count` of this
employee's loans). Surfaced as a stat button on the employee form (see §4).
> Note: `_compute_employee_loans` is written for a single record (uses `self.id`); the
> stat button works because each employee form is a singleton, but the compute is not
> batch-safe.

### 3.4 `hr.payslip.input` (inherited — `models/hr_payroll.py`)
Adds `loan_line_id` (M2o `hr.loan.line`) — links a payslip input row back to the loan
installment it represents, so confirming the slip can mark the right installment paid.

### 3.5 `hr.payslip` (inherited — `models/hr_payroll.py`)
- `onchange_employee()` — overridden onchange on `employee_id / date_from / date_to`
  that rebuilds the slip name, contract, worked-day lines **and input lines** (so the
  loan input appears). Mirrors the community payslip onchange; keep in sync with
  `hr_payroll_community` if that changes.
  > Contains a leftover `print(date_from, date_to, '001qq')` debug line — harmless but
  > should be removed.
- `get_inputs(contract_ids, date_to, date_from)` — calls `super`, then for every
  `approve` loan of the contract's employee, finds the installment whose `date` falls in
  `[date_from, date_to]` and is **not** `paid`, and writes its `amount` + `loan_line_id`
  onto the input row whose `code == 'LO'`.
  > ⚠️ Argument names here are `(contract_ids, date_to, date_from)` but it's invoked as
  > `get_inputs(contracts, date_from, date_to)` in `onchange_employee` — the positional
  > order is effectively swapped vs. the signature names. The date range is symmetric in
  > use so it works, but don't "fix" the names without tracing both call sites.
- `action_payslip_done()` — for each input line with a `loan_line_id`, sets the
  installment `paid = True` and recomputes the loan balance, then `super()`.

---

## 4. Views (`views/`)

### 4.1 `hr_loan.xml`
- **Tree** (`hr_loan_tree_view`): `name`, `employee_id`, `loan_amount`, `date`, `state`.
- **Form** (`hr_loan_form_view`):
  - Header buttons: **Compute Installment** (hidden when `state in ['approve','refuse']`),
    **Submit** (draft only), **Cancel** (draft only), **Approve** / **Refuse** (gated to
    `hr.group_hr_manager, hr.group_hr_user`). Statusbar `draft → waiting_approval_1 →
    approve`.
  - Body: `employee_id`, `date`, `department_id`, `job_position`, `loan_amount`,
    `installment`, `payment_date`, `company_id` / `currency_id` (multi-company only).
    Several fields become `readonly` once `state == 'approve'`.
  - **Installments** tab: editable `loan_lines` tree (`date`, `amount`, hidden `paid`) +
    a subtotal footer (`total_amount`, `total_paid_amount`, `balance_amount`, monetary).
  - Chatter (followers + thread).
- **Search** (`view_loan_request_search_form`): filter **My Requests**
  (`employee_id.user_id == uid`); group-by Employee / Department / Status.
- **Menus:** `Loans & Advances` (under `hr.menu_hr_root`, seq 20) → `Loan` →
  **Request for Loan** (action `action_hr_loan_request`, default filter `myrequest`).
- **Employee stat button:** `view_employee_form_loan_inherit` injects a `loan_count`
  stat button (action `act_hr_employee_loan_request`, a binding action on `hr.employee`)
  into the employee form's button box, visible to HR user/manager.

### 4.2 `hr_payroll.xml`
`hr_payslip_form_inherit_view` inherits `hr_payroll_community.view_hr_payslip_form` and
adds the hidden `loan_line_id` field into the payslip **Other Inputs** tree (so the
input ↔ installment link is carried, but not shown to users).

### 4.3 `hr_loan_seq.xml`
`ir.sequence` `ir_seq_hr_loan` (code `hr.loan.seq`, prefix `LO/`, padding 4) —
`noupdate="1"`, generates loan names like `LO/0001`.

---

## 5. Payroll integration & salary rule (`data/salary_rule_loan.xml`)
- `hr.salary.rule` **`LO`** ("Loan"): category `hr_payroll_community.DED` (deduction),
  `amount_select = code`, `amount_python_compute = result = inputs.LO and -(inputs.LO.amount)`
  (negative → it subtracts), `appears_on_payslip`, `sequence 190`.
- `hr.rule.input` **`LO`** ("Loan"): the input definition (`input_id` → the `LO` rule)
  that makes the `LO` input slot exist on payslips.

`data noupdate="0"` — so re-running `-u` will refresh these records.

> The whole deduction hinges on the **`LO` code** matching across: the rule input, the
> salary rule, and the `result.get('code') == 'LO'` check in `get_inputs()`. Change one,
> change all three.

---

## 6. Security (`security/`)

### `ir.model.access.csv`
| Group | `hr.loan` | `hr.loan.line` |
|---|---|---|
| `base.group_user` (any internal user) | R/W/Create, **no unlink** | R/W (line: no create/unlink) |
| `hr.group_hr_user` (HR Officer) | full CRUD | full CRUD |
| `hr.group_hr_manager` (HR Manager) | full CRUD | full CRUD |

Also grants `base.group_user` R/W/Create on `hr.job` (so the related job field
resolves for self-service users).

### `security.xml` (record rules, `noupdate="1"`)
- `rule_hr_loan` — **multi-company** global rule: a user only sees loans of their own
  company (or company-less).
- `hr_loan_rule` — **"User: Modify own loan only"**: `base.group_user` is restricted to
  loans where `employee_id.user_id == user` (full RWCU on *their own* loans).
- `hr_loan_manager_rule` — grants `hr.group_hr_user` full RWCU across loans (overrides
  the own-loan restriction for HR officers).

**Net effect:** an ordinary employee sees/edits only their own loan requests; HR
officers and managers see and manage all (within their company). The **Approve/Refuse**
buttons are additionally group-gated in the form view.

---

## 7. Internationalization
`i18n/ar_001.po` ships an **Arabic** translation of all UI strings (this is a Kuwait
client). The model labels and code identifiers stay English; install the language and
the UI renders Arabic. There is no separate `.pot`; update the `.po` if you add strings.

---

## 8. Gotchas & notes (read before debugging)
- **`hr_payroll_community` is mandatory and the integration is tightly coupled** —
  payslip view inherit (`view_hr_payslip_form`), the `DED` category, the `LO` rule input
  and the `get_inputs`/`onchange_employee` overrides all reference it. Enterprise
  `hr_payroll` will not work as a drop-in.
- **One active loan per employee.** `create()` blocks a new loan while the employee has
  an `approve` loan with a non-zero balance. To grant a second loan, the first must be
  fully repaid (balance 0) or not approved.
- **Compute Installment is destructive** — it `unlink()`s and rebuilds all lines. Don't
  hand-edit installment lines and then press it again.
- **Approval requires installment lines** (`action_approve` raises otherwise). The UX is:
  Compute Installment → Submit → Approve.
- **`paid` is only flipped on payslip confirmation** (`action_payslip_done`), never by
  hand in the standard flow. The loan balance recomputes from `paid` lines.
- **Legacy API surface:** `ir.sequence.get()` (deprecated), single-dict `create()`,
  `states={...}` on `company_id`, and a non-batch `_compute_employee_loans`. All function
  in 17 but are pre-modern style — be cautious when refactoring.
- **Stray `print(...)` debug** in `hr.payslip.onchange_employee` — safe to delete.
- **`get_inputs` arg-name/position mismatch** (see §3.5) — leave the call sites as-is.
- Deletion is blocked unless `draft`/`cancel` (`unlink` override) — to remove an approved
  loan, cancel it first (or unlink as a manager after cancel).

---

## 9. File map
```
__manifest__.py                     depends: base, hr_payroll_community, hr, account
__init__.py / models/__init__.py
models/
  hr_loan.py        hr.loan, hr.loan.line, hr.employee (loan_count)
  hr_payroll.py     hr.payslip, hr.payslip.input inherits (installment → payslip)
views/
  hr_loan.xml       tree / form / search / menus / employee stat button
  hr_loan_seq.xml   ir.sequence hr.loan.seq (LO/####)
  hr_payroll.xml    payslip Other-Inputs inherit (hidden loan_line_id)
data/
  salary_rule_loan.xml   hr.salary.rule "LO" (DED) + hr.rule.input "LO"
security/
  ir.model.access.csv    access for base user / HR user / HR manager
  security.xml           multi-company + own-loan + HR-officer record rules
i18n/ar_001.po           Arabic translation
doc/RELEASE_NOTES.md     upstream changelog
README.md                upstream Cybrosys readme
static/description/       app-store icon, banner, screenshots (not loaded at runtime)
```
