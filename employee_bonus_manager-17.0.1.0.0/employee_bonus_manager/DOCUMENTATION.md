# employee_bonus_manager — Developer Handover Documentation

> **Employee Bonus** — a third‑party (Cybrosys) Odoo 17 module that manages
> employee bonus requests through a multi‑step approval workflow
> (draft → submit → department head → manager → accounting head), posts a
> double‑entry accounting journal for each approved bonus, and feeds the approved
> amount back into the employee's **payslip** as an "other input" line.
> UI is **English**. The module ships inside the
> `employee_bonus_manager-17.0.1.0.0/` bundle alongside `hr_payroll_community`
> (its payroll dependency) — this file documents **only** `employee_bonus_manager`.
> Read this before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `employee_bonus_manager` |
| Display name | **Employee Bonus** |
| Version | `17.0.1.0.0` |
| Odoo | 17.0 |
| Category | Human Resources |
| Depends | `account`, **`hr_payroll_community`** (community payroll — ships in the same bundle; payslip integration relies on it) |
| External Python libs | **None** (only stdlib via Odoo ORM) |
| Author / License | Cybrosys Techno Solutions · AGPL‑3 |
| Application | `True` (own top‑level menu "Bonus Requests") |
| Models | `bonus.request` (central), `bonus.reason`, `hr.payslip` (inherited) |
| Sequence | `bonus.request` → prefix `BR/`, 4‑digit padding |

### Deployment (this server)
- DB: `odoo17` · service: `odoo-17.service` (systemd) · runs as user `odoo`.
- Python venv: `/home/odoo/.pyenv/versions/odoo-17-env/bin/python`
- Odoo bin: `/home/odoo/odoo-17.0+e.20241205/odoo-bin` · conf: `/home/odoo/odoo.conf`
- **Update + restart:**
  ```bash
  sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
    /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
    -d odoo17 -u employee_bonus_manager --stop-after-init --no-http
  sudo systemctl restart odoo-17.service
  ```
- No dev mode. Log file: `/var/log/odoo/odoo-17.log`.
- **`hr_payroll_community` must be installed first** (it is a hard `depends` and the
  salary‑rule / structure data records reference its XML ids). If it is missing the
  module will not install.

---

## 2. Architecture overview

```
bonus.request   (central model — mail.thread, _rec_name = reference)
├── many2one → hr.employee        (employee_id, required)
│              └─ onchange fills department_id + job_id
├── many2one → bonus.reason       (bonus_reason_id, required — config master)
├── many2one → account.journal    (journal_id, type=general, required at 'accounting')
├── many2one → account.move       (move_id — the posted bonus journal entry)
├── many2one → account.account    (credit_account_id / debit_account_id)
└── state machine:
      draft → submitted → department_approved → manager_approved → accounting
                    └──────────────► rejected ──► (reset) ──► draft

bonus.reason     (simple master: just `name`)

hr.payslip (inherited)
  └─ onchange(employee_id, date_from, date_to, struct_id):
       if structure contains the BONUS rule → sum posted bonuses in the
       payslip period → push as an `input_line_ids` row (code BONUS)

Data records (XML):
  • ir.sequence  BR/####
  • hr.salary.rule  "Employee Bonus" (code BONUS, category ALW, amount = inputs.BONUS.amount)
  • hr.payroll.structure  structure_base  ← adds the BONUS rule to the base structure
```

**Design notes**
- The whole flow is a **linear state machine** on `bonus.request`; each transition is a
  button method that stamps the actor (`*_user_id` / `*_manager_id`) and a date, and
  bumps `state`. There are no computed analytics or crons.
- The accounting step creates **and immediately posts** a balanced `account.move`
  (debit_account vs credit_account, both = `bonus_amount`).
- Payroll integration is **pull‑based via an onchange** on the payslip — there is no
  push from bonus → payslip. The bonus only lands on a payslip when the payslip is
  (re)computed for a period that contains posted bonus moves *and* the chosen salary
  structure includes the BONUS rule.

---

## 3. Data model

### 3.1 `bonus.request` (central — `models/bonus_request.py`)
`_inherit = 'mail.thread'` · `_rec_name = 'reference'` · `_description = 'Create Bonus Request'`

**Identity / workflow:**
| Field | Type | Notes |
|---|---|---|
| `reference` | Char | Sequence `BR/####`, set in `create()`, `copy=False` |
| `state` | Selection | `draft, submitted, department_approved, manager_approved, rejected, accounting`. `tracking=True`, `copy=False`, `group_expand='_group_expand_states'` (all states show as kanban columns). Label of `accounting` = "Accounting Head Approved" |
| `employee_id` | M2o `hr.employee` | required, tracked |
| `user_id` | M2o `res.users` | related `employee_id.user_id` (read‑only mirror) |
| `department_id` | M2o `hr.department` | filled by onchange, stored |
| `job_id` | M2o `hr.job` | filled by onchange, stored |
| `bonus_reason_id` | M2o `bonus.reason` | **required** |
| `bonus_amount` | Float | the bonus value, tracked |
| `currency_id` | M2o `res.currency` | default = user company currency, read‑only |
| `company_id` | M2o `res.company` | default = `env.company`, read‑only |

**Actor / audit stamps (all `readonly`, `copy=False`):**
`confirmed_user_id` + `confirmed_date` (submit), `department_manager_id` +
`department_approved_date` (department approval), `hr_manager_id` +
`manager_approved_date` (manager approval).

**Accounting:**
| Field | Type | Notes |
|---|---|---|
| `journal_id` | M2o `account.journal` | `company_dependent=True`, `domain [('type','=','general')]`, **required in `accounting` state** (legacy `states={...}` attr — see Gotchas) |
| `move_id` | M2o `account.move` | the created/posted bonus entry, read‑only |
| `credit_account_id` | M2o `account.account` | credit side of the entry |
| `debit_account_id` | M2o `account.account` | debit side of the entry |

**Methods:**
- `create(vals)` — `@api.model` override; assigns the `bonus.request` sequence to
  `reference` when it is `'New'`/absent.
- `_onchange_employee_id()` — copies the employee's `department_id` and `job_id` onto the request.
- `_group_expand_states()` — returns all state keys so the kanban shows every column even when empty.
- `action_confirm()` → `submitted` (+ stamps `confirmed_user_id`/`confirmed_date`).
- `action_department_approve()` → `department_approved` (+ `department_manager_id`/`department_approved_date`).
- `action_manager_approve()` → `manager_approved` (+ `hr_manager_id`/`manager_approved_date`).
- `action_reject()` → `rejected`.
- `action_reset_to_draft()` → `draft` and **clears all actor/date stamps**.
- `action_post_journal_entry()` — creates an `account.move` (ref = `reference`,
  date = `manager_approved_date`, two balanced lines: credit `credit_account_id` /
  debit `debit_account_id`, each = `bonus_amount`, line names = `employee.name-reference`),
  sets it to `posted`, stores it in `move_id`, and moves the request to `accounting`.
- `action_view_journal_items()` — opens the linked `account.move` form.

### 3.2 `bonus.reason` (`models/bonus_reason.py`)
Master list of bonus reasons. Single field `name` (Char, required). Managed under
**Configuration → Bonus Reasons**.

### 3.3 `hr.payslip` (inherited — `models/hr_payslip.py`)
Adds one `@api.onchange('employee_id', 'date_from', 'date_to', 'struct_id')` method
`_onchange_employee_id`:
1. Resolves the salary rule `employee_bonus_manager.hr_salary_rule_bonus` (the BONUS rule).
2. **Only acts if** that rule's name is among the names of `struct_id.rule_ids` (i.e. the
   chosen salary structure actually contains the BONUS rule).
3. Searches `bonus.request` for the employee where `state == 'accounting'`,
   `move_id.state == 'posted'`, and the move date falls within `date_from..date_to`.
4. Sums their `bonus_amount` and writes a single `input_line_ids` row
   (`name='Bonus'`, `code='BONUS'`, `contract_id`, `amount=<sum>`).

> ⚠️ This **replaces** `input_line_ids` with a single Bonus line via `(0,0,{...})`
> on an onchange (see Gotchas — re‑triggering can drop other inputs, and it only runs
> in form onchange context, not on programmatic recompute).

---

## 4. Workflow & roles

| Step | Button (form header) | Method | Allowed group | Resulting state |
|---|---|---|---|---|
| Submit | **Submit** | `action_confirm` | any User (visible in `draft`) | `submitted` |
| Department approval | **Approve by Department** | `action_department_approve` | `…group_department` (Department Head) | `department_approved` |
| Manager approval | **Approve by Manager** | `action_manager_approve` | `…group_manager` (Manager) | `manager_approved` |
| Reject | **Reject** | `action_reject` | Department Head (in `submitted`) or Manager (in `department_approved`) | `rejected` |
| Reset | **Reset to Draft** | `action_reset_to_draft` | Department Head (in `rejected`) | `draft` |
| Accounting | **Accounting Head Approval** | `action_post_journal_entry` | `account.group_account_manager` (in `manager_approved`) | `accounting` |

The statusbar shows `draft,submitted,department_approved,manager_approved,accounting,posted`
(`posted` is listed in `statusbar_visible` but is **not** an actual state value — cosmetic only).

---

## 5. Views (`views/`)

### 5.1 `bonus_request_views.xml` — model `bonus.request`
- **Form** — header statusbar + transition buttons (gated by group + `invisible` on
  state); a `Journal Items` stat button (visible once `move_id` is set); title =
  `reference`, subtitle = `employee_id` (locked after draft); main group with
  department/job/reason + create date/`bonus_amount` (monetary, editable only in
  draft/submitted); **Extra Information** tab (the actor/date audit stamps);
  **Accounting Information** tab (gated to `account.group_account_manager`, visible only
  in `manager_approved`/`accounting`; `credit_account_id` required in `manager_approved`);
  chatter (followers + messages).
- **Tree** — `default_order='create_date'`, row decorations by state
  (draft=warning, department_approved=info, manager_approved=success, rejected=danger);
  state shown as a `badge`. Many columns `optional="hide"`.
- **Kanban** — `default_group_by="state"`, `records_draggable="0"`; card shows employee,
  reason, amount, reference, state.
- **Graph**, **Pivot** (employee × state), **Calendar** (`create_date`, colored by state,
  `create="0"`).
- **Search** — fields + Group By (state/employee/created date/department/job) + filters
  (confirmed/department‑approved/manager‑approved today; per‑state filters).
- **Actions** (all `tree,kanban,graph,pivot,calendar,form`):
  - `bonus_request_action` — "Bonus Requests" (all).
  - `bonus_request_department_action` — "Department Approval", domain `state='submitted'`, `create:False`.
  - `bonus_request_manager_action` — "Manager Approval", domain `state='department_approved'`, `create:False`.
  - `bonus_request_accounting_action` — "Accounting Head Approval", domain `state='manager_approved'`, `create:False`.

### 5.2 `bonus_reason_views.xml` — model `bonus.reason`
Editable tree (`editable="bottom"`) + simple form + action `bonus_reason_action`.

### 5.3 `employee_bonus_manager_menus.xml`
Top‑level app menu **"Bonus Requests"** (`employee_bonus_manager_menu_root`, own icon):
- **Requests** → *All Requests* (`bonus_request_action`).
- **Requests → For Approval** (Department Head group) → *Department* / *Manager* / *Accounting Head*
  (each sub‑menu gated to its respective group).
- **Configuration → Bonus Reasons**.

---

## 6. Wizards
**N/A** — the module ships no `wizards/` directory and no `TransientModel`.

## 7. Reports
**N/A** — no `reports/` directory and no `ir.actions.report`. (The `move_id` stat button
opens the standard accounting move form; not a QWeb report of this module.)

## 8. Crons
**N/A** — no `ir.cron` records.

## 9. Settings
**N/A** — no `res.config.settings` inheritance and no `config_parameter`. The only
configuration surface is the **Bonus Reasons** master (`bonus.reason`).

## 10. Assets / JS
**N/A** — no `web.assets_*` bundle, no OWL components, no JS/SCSS. The `static/`
directory contains **only the app‑store description** (`static/description/` — `icon.png`,
`banner.jpg`, `index.html`, screenshots/icons). `web_icon` for the root menu points at
`static/description/icon.png`.

---

## 11. Data records (`data/`)

| File | Record | Purpose |
|---|---|---|
| `ir_sequence_data.xml` | `ir_sequence_bonus_request` (`noupdate=1`) | sequence `bonus.request`, prefix `BR/`, padding 4, no company |
| `hr_salary_rule_data.xml` | `hr_salary_rule_bonus` (`noupdate=1`) | salary rule **Employee Bonus**, code `BONUS`, category `hr_payroll_community.ALW`, sequence 59, `amount_python_compute = "result = inputs.BONUS.amount"` |
| `hr_payroll_structure_data.xml` | overrides `hr_payroll_community.structure_base` (`noupdate=1`) | **re‑sets** `rule_ids` of the base structure to `[basic, taxable, net, BONUS]`, injecting the bonus rule |

---

## 12. Security (`security/`)

### 12.1 Groups (`employee_bonus_manager_groups.xml`)
Module category **"Employee Bonus"**. Three nested groups (each implies the previous):
- `employee_bonus_manager_group_user` — **User** (implies `base.group_user`). Default user added to it.
- `employee_bonus_manager_group_department` — **Department Head** (implies User).
- `employee_bonus_manager_group_manager` — **Manager** (implies Department Head; `base.user_root` + `base.user_admin` added).

The **accounting** step is gated to the standard `account.group_account_manager`, not a module group.

### 12.2 Access rights (`ir.model.access.csv`)
| Model | User | Department Head | Manager |
|---|---|---|---|
| `bonus.request` | R/W/C | R/W/C | R/W/C + **delete** |
| `bonus.reason` | R/W/C | R/W/C | R/W/C + **delete** |

Only the **Manager** group has unlink rights.

### 12.3 Record rules (`bonus_request_security.xml`, `noupdate=1`)
`bonus_request_rule_company` — standard multi‑company rule on `bonus.request`
(`company_id = False OR company_id in company_ids`). No ownership/per‑user rules — any
User can read/write all requests within their company.

---

## 13. Gotchas & notes (read before debugging)

- **Hard payroll dependency.** `depends = ['account', 'hr_payroll_community']`. The salary
  rule references `hr_payroll_community.ALW`, and `hr_payroll_structure_data.xml`
  overrides `hr_payroll_community.structure_base`. If payroll isn't installed, install
  fails. The bundle ships `hr_payroll_community` for exactly this reason.
- **Structure override is destructive.** `hr_payroll_structure_data.xml` rewrites
  `structure_base.rule_ids` to exactly `[basic, taxable, net, BONUS]` with `(6,0,[...])`.
  If the site has customised the base structure's rules, **reinstalling/updating this
  module wipes those customisations** off `structure_base`. It is `noupdate=1`, so it only
  applies on install (or forced reload), but be aware.
- **Bonus reaches payslip only via onchange.** `hr.payslip._onchange_employee_id` runs in
  **form onchange context only**. A payslip computed purely server‑side (batch, scripted)
  won't get the Bonus input line unless the onchange path is triggered. The chosen
  structure must also contain the BONUS rule (the override adds it to `structure_base`
  only — other structures won't pick up bonuses).
- **Onchange overwrites `input_line_ids`.** The payslip onchange sets
  `input_line_ids = [(0,0,{...})]` — it does not merge. If the structure contains the
  BONUS rule, re‑triggering the onchange replaces existing manual input lines with the
  single Bonus line.
- **Bonus is matched by move date, not approval date.** The payslip pulls bonuses where the
  *posted journal entry's date* (= `manager_approved_date`) falls inside the payslip
  period. A bonus posted with a manager‑approval date outside the period won't appear.
- **`create()` not batch‑safe.** Uses the legacy single‑dict `@api.model def create(self, vals)`
  signature (not `create_multi`). Bulk/import creates may bypass per‑record sequence logic.
- **Journal entry posts immediately.** `action_post_journal_entry` sets the move to
  `posted` directly (no `action_post()`); credit/debit accounts and a `general` journal
  must be set or the move will be unbalanced/invalid.
- **Legacy `states=` attribute.** `journal_id` uses the v13‑era
  `states={'accounting': [('required', True)]}` definition. It still works in 17 for the
  *required* attr but is the old style; the form view instead uses v17
  `required="state == 'manager_approved'"` on `credit_account_id`. Don't mix the two when editing.
- **`statusbar_visible` lists a non‑existent `posted` state** — purely cosmetic; the real
  terminal state is `accounting`.
- **No per‑user record rule.** Any User can see and edit every company request — the
  approval gating is purely button/group visibility, not record‑level isolation.
- **Third‑party (Cybrosys) module** — keep changes minimal and documented; upstream updates
  may overwrite local edits.

---

## 14. File map
```
__manifest__.py                  depends (account, hr_payroll_community), data list
__init__.py → models/__init__.py
models/
  bonus_request.py               central model + state machine + journal posting
  bonus_reason.py                bonus.reason master (name only)
  hr_payslip.py                  inherited — onchange injects BONUS input line
data/
  ir_sequence_data.xml           BR/#### sequence
  hr_salary_rule_data.xml        BONUS salary rule (category ALW)
  hr_payroll_structure_data.xml  injects BONUS into structure_base (destructive override)
security/
  employee_bonus_manager_groups.xml   User / Department Head / Manager (+ category)
  bonus_request_security.xml          multi-company record rule
  ir.model.access.csv                 ACLs (Manager-only unlink)
views/
  bonus_request_views.xml        form/tree/kanban/graph/pivot/calendar/search + 4 actions
  bonus_reason_views.xml         tree/form + action
  employee_bonus_manager_menus.xml    app menu + approval sub-menus
static/description/              app-store assets only (icon/banner/index.html/screenshots) — not loaded
doc/RELEASE_NOTES.md · README.rst
```
