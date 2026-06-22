# hr_vacation_mngmt — Developer Handover Documentation

> **Open HRMS Vacation Management** — a Cybrosys/Open HRMS module for Odoo 17 that extends
> employee leave (`hr.leave`) handling with: pending-work re-assignment before a leave is
> approved, overlapping-leave detection, **flight-ticket booking + supplier invoicing**,
> **leave-salary payroll rules** (Basic / Gross), and an automated leave-reminder e-mail.
> The module is a third-party Cybrosys product (AGPL-3); UI labels are **English**. A small
> amount of Arabic exists only in the bundled translation file (`i18n/ar_001.po`).
> Read this before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `hr_vacation_mngmt` |
| Display name | **Open HRMS Vacation Management** |
| Version | `17.0.1.0.1` |
| Odoo | 17.0 |
| Category | Human Resources |
| License | AGPL-3 |
| Author | Cybrosys Techno Solutions / Open HRMS |
| Depends | `hr_leave_request_aliasing`, `project`, `hr_payroll_community`, `account` |
| External Python libs | None beyond stdlib (`datetime`, `timedelta`) — no third-party packages |
| New models | `hr.flight.ticket`, `pending.task`, `task.reassign` (wizard) |
| Inherited models | `hr.leave`, `hr.payslip`, `res.config.settings` |

### Ships in a bundle (siblings)
This module lives inside the bundle folder `hr_vacation_mngmt-17.0.1.0.1/`, which also
contains two **sibling modules it depends on** (both must be installed first / available on
the addons path):
- **`hr_leave_request_aliasing`** ("Open HRMS Leave Request Aliasing") — listed in
  `depends`. Adds mail-alias-based leave request creation.
- **`hr_payroll_community`** ("Odoo 17 HR Payroll") — listed in `depends`. Provides
  `hr.payslip`, salary rules/categories (`ALW`, `BASIC`), the contribution register model,
  and the payroll Settings view this module extends. **The whole leave-salary feature and
  the payslip view inheritance break without it.**

> The `i18n/ar_001.po` Arabic translation is bundled but the module loads no Arabic UI by
> default; treat strings as English unless a translation is activated.

### Deployment (this server)
- DB: `odoo17` · service: `odoo-17.service` (systemd) · runs as user `odoo`.
- Python venv: `/home/odoo/.pyenv/versions/odoo-17-env/bin/python`
- Odoo bin: `/home/odoo/odoo-17.0+e.20241205/odoo-bin` · conf: `/home/odoo/odoo.conf`
- This bundle lives outside the main `/home/odoo/care` repo at
  `/home/odoo/care/hr_vacation_mngmt-17.0.1.0.1/`; ensure that parent folder (containing all
  three sibling modules) is on the addons path before installing.
- **Update + restart:**
  ```bash
  sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
    /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
    -d odoo17 -u hr_vacation_mngmt --stop-after-init --no-http
  sudo systemctl restart odoo-17.service
  ```
- Log file: `/var/log/odoo/odoo-17.log`. No dev mode required (no JS/SCSS assets here).

---

## 2. Architecture overview

```
hr.leave  (inherited — the central object)
├── one2many → pending.task            (work the employee must hand off before leave)
│                 └── used by → task.reassign  (TransientModel wizard)
│                                    └── creates → project.task (one per pending task)
├── one2many → hr.flight.ticket        (employee travel for the leave)
│                 └── action_confirm_ticket() → account.move (in_invoice, vendor bill)
├── many2many (computed) → overlapping_leaves_ids   (same-dept validated leaves that clash)
├── many2many (computed) → holiday_managers_ids     (hr_holidays managers, for reminders)
└── related → remaining_leaves (employee.remaining_leaves), leave_salary selector

hr.payslip (inherited)  →  leave_salary Boolean → injects Leave-Salary salary rule
                            (Basic or Gross, per `default_leave_salary` setting)

res.config.settings (inherited) → 5 config_parameters (reminder + expense + leave-salary)

Automation:
  • ir.cron "Flight ticket status update"  → hr.flight.ticket.run_update_ticket_status()
  • ir.cron "HR Leave Reminder"            → hr.leave.send_leave_reminder()
                                              (mail.template email_template_hr_leave_reminder_mail)
```

**Design notes**
- The approval flow is **interception-based**: overriding `hr.leave.action_approve()` so that
  if a leave has pending tasks, a wizard (`task.reassign`) must be filled before the leave is
  actually validated. No pending tasks → straight to `action_validate()`.
- Flight tickets carry their own draft→confirmed→started→completed state machine and generate
  a **vendor bill** (`account.move`, `move_type='in_invoice'`) against a demo `Airlines`
  partner on confirm.
- Tunables (reminder toggle/day, leave-salary basis, expense account/product) are all
  `config_parameter` records under the `hr_vacation_mngmt.` prefix — except the reminder
  params (see Gotchas: the cron reads **un-prefixed** keys).

---

## 3. Data model

### 3.1 `hr.leave` (inherited — `models/hr_leave.py`)
| Field | Type | Notes |
|---|---|---|
| `remaining_leaves` | Float (related `employee_id.remaining_leaves`) | "Remaining Legal Leaves" shown on form |
| `overlapping_leaves_ids` | M2m `hr.leave` (computed) | `_compute_overlapping_leaves_ids` — other **validated** leaves in the same department whose date range overlaps |
| `pending_task_ids` | O2m `pending.task` (`leave_id`) | work to hand off before approval |
| `holiday_managers_ids` | M2m `res.users` (computed) | `_compute_holiday_managers_ids` — members of `hr_holidays.group_hr_holidays_manager` |
| `flight_ticket_ids` | O2m `hr.flight.ticket` (`leave_id`) | tickets booked for this leave |
| `expense_account_id` | M2o `account.account` | expense account for flight expenses |
| `leave_salary` | Selection `0=Basic / 1=Gross` | per-leave salary basis |

**Key methods:**
- `_compute_overlapping_leaves_ids()` — builds day-by-day date sets and flags overlaps with
  other same-department `state='validate'` leaves. *(See Gotcha: the inner overlap test
  compares a set with itself — effectively flags all same-dept validated leaves.)*
- **`action_approve()` (override)** — gates approval: requires
  `hr_holidays.group_hr_holidays_user`; the leave must be in `state='confirm'`; if it has
  `pending_task_ids` and a `user_id`, **opens the `task.reassign` wizard** (passing
  `default_leave_req_id`) instead of validating; otherwise calls `action_validate()`.
- `action_book_ticket()` — manager-only; opens the **Book Flight Ticket** form
  (`view_hr_book_flight_ticket_form`) pre-seeding `default_employee_id`/`default_leave_id`
  (both set to the leave id — note `hr.flight.ticket.employee_id` is itself a `hr.leave` m2o).
- `action_view_flight_ticket()` — opens the first ticket of the leave.
- **`send_leave_reminder()`** (`@api.model`) — cron entrypoint; see §6.

### 3.2 `hr.flight.ticket` (new — `models/hr_flight_ticket.py`)
Employee travel record tied to a leave. `_description = 'HR Flight Ticket'`.

| Field | Type | Notes |
|---|---|---|
| `name` | Char | ticket name |
| `employee_id` | M2o **`hr.leave`** (required) | "Employee" — actually points at the leave record (booking sets it to the leave id) |
| `ticket_type` | Selection `one`/`round` (default `round`) | one-way / round trip |
| `depart_from`, `destination` | Char (required) | route |
| `date_start` (required), `date_return` | Date | travel dates |
| `ticket_class` | Selection economy/premium_economy/business/first_class | |
| `ticket_fare` | Float | invoiced amount |
| `flight_details`, `return_flight_details` | Text | |
| `state` | Selection booked/confirmed/started/completed/canceled (default `booked`) | |
| `invoice_id` | M2o `account.move` | generated vendor bill |
| `leave_id` | M2o `hr.leave` | the leave this ticket belongs to |
| `company_id` | M2o `res.company` (default user company) | multi-company scoped |

**Methods:**
- `name_get()` — display as "Flight ticket for {employee} on {date_start} to {destination}".
- `check_valid_date()` (`@api.constrains`) — start date must be ≤ return date.
- `action_confirm_ticket()` — requires fare > 0 and an expense account
  (`hr_vacation_mngmt.expense_account_id` config param); finds a purchase journal for the
  company, resolves the demo `res_partner_data_airlines` vendor, computes due date from its
  payment term, and **creates a draft `in_invoice`** with one line (fare, expense account,
  `hr_vacation_mngmt.expense_product_id`). Sets state `confirmed` + links `invoice_id`.
- `action_cancel_ticket()` — `booked`→`canceled`; `confirmed` with a draft invoice →
  `canceled`. *(Gotcha: the `'open'` branch calls `self.invoice_id.action_invoice_cancel()`,
  a v8-era method that no longer exists in Odoo 17 — dead/broken path.)*
- `run_update_ticket_status()` (`@api.model`) — cron entrypoint; promotes
  confirmed→started (start date reached) and confirmed/started→completed (return date passed).
- `action_view_invoice()` — opens the linked vendor bill.
- `action_book_ticket()` — closes the booking dialog window.

### 3.3 `pending.task` (new — `models/pending_task.py`)
Work an employee must hand off before their leave is approved.

| Field | Type | Notes |
|---|---|---|
| `name` | Char (required) | task name |
| `leave_id` | M2o `hr.leave` | parent leave |
| `dept_id` | M2o `hr.department` (related `leave_id.department_id`) | |
| `project_id` | M2o `project.project` (required) | target project for the created task |
| `description` | Text | |
| `assigned_person_id` | M2o `hr.employee`, domain `department_id == dept_id` | who takes over |
| `unavailable_employee_ids` | M2m `hr.employee` (computed) | `_compute_unavailable_employee_ids` — employees who are themselves on overlapping leave |

### 3.4 `task.reassign` (wizard — `wizard/task_reassign.py`)
TransientModel shown when approving a leave that has pending tasks.

| Field | Type | Notes |
|---|---|---|
| `leave_req_id` | M2o `hr.leave` | the leave being approved (from `default_leave_req_id`) |
| `pending_task_ids` | O2m `pending.task` (related, `readonly=False`) | editable list of the leave's pending tasks |

**Methods:**
- `action_approve()` — validates every pending task has an assignee (else `UserError`);
  rejects assignees who appear in `unavailable_employee_ids`; otherwise **creates a
  `project.task`** per pending task (name, project, description, and *removes* the assignee's
  user via `(3, user_id)` — note: this unlinks rather than assigns) and calls
  `leave_req_id.action_validate()`.
  *(Gotcha: `action_validate()` is called inside the per-task loop, so it runs once per task.)*
- `cancel()` — clears assignees and closes the wizard.

### 3.5 `hr.payslip` (inherited — `models/hr_payslip.py`)
- Adds `leave_salary` (Boolean) — "pay salary while on leave".
- Overrides `_get_payslip_lines(contract_ids, payslip_id)` (a full re-implementation of the
  core payroll computation, with the standard `BrowsableObject`/`InputLine`/`WorkedDays`/
  `Payslips` helper classes). When `payslip.leave_salary` is set, it **appends the Leave-Salary
  salary rule** (`hr_salary_rule_leave_salary_basic` or `_gross`) chosen by the
  `default_leave_salary` config param (`'0'`→Basic, `'1'`→Gross, default Basic) before
  sorting/evaluating rules.

### 3.6 `res.config.settings` (inherited — `models/res_config_settings.py`)
All `config_parameter`, prefix `hr_vacation_mngmt.` **except where noted**:

| Field | config_parameter | Notes |
|---|---|---|
| `leave_reminder` (Bool) | `hr_vacation_mngmt.leave_reminder` | enable reminder e-mails |
| `reminder_day_before` (Int) | `hr_vacation_mngmt.reminder_day_before` | days before leave to send |
| `default_leave_salary` (Sel 0/1) | `hr_vacation_mngmt.default_leave_salary` | Basic/Gross default; `default_model='hr.leave'` |
| `expense_account_id` (M2o account, **required**) | `hr_vacation_mngmt.expense_account_id` | domain `account_type='expense'` |
| `expense_product_id` (M2o product, **required**) | `hr_vacation_mngmt.expense_product_id` | domain `type='service'` |

---

## 4. Views (`views/*.xml`)

- **`hr_flight_ticket_views.xml`** — three views + action + menu:
  - Form (`hr_flight_ticket_view_form`, priority 0) — header Confirm/Cancel buttons,
    statusbar, Invoice stat button, field readonly logic per state.
  - Tree (`hr_flight_ticket_view_tree`, priority 1).
  - Booking form (`view_hr_book_flight_ticket_form`, priority 2) — the dialog launched from
    a leave's "Book Flight Ticket" button.
  - Action `action_hr_flight_tickets` + menu `hr_flight_tickets_menu_root` under
    **Time Off** (`hr_holidays.menu_hr_holidays_root`), restricted to
    `hr_holidays.group_hr_holidays_manager`.
- **`hr_leave_views.xml`** — inherits `hr_holidays.hr_leave_view_form`: adds the Flight Ticket
  stat button + "Book Flight Ticket" header button (manager-only, shown when validated and no
  ticket yet), the `remaining_leaves` field, and two notebook pages — **Pending Works**
  (`pending_task_ids`) and **Overlapping Leaves** (`overlapping_leaves_ids`).
- **`hr_payslip_views.xml`** — inherits `hr_payroll_community.hr_payslip_view_form`; adds the
  `leave_salary` checkbox after `credit_note`.
- **`pending_task_views.xml`** — standalone form for `pending.task` (no menu/action; reached
  via the leave form / wizard).
- **`res_config_settings_views.xml`** — inherits `hr_payroll_community.res_config_settings_view_form`;
  adds a **Leaves** section (Leave Salary radio, Expense Account, Expense Product).
- **`wizard/task_reassign_views.xml`** — the re-assign wizard form (editable tree of pending
  tasks; Confirm→`action_approve`, Cancel→`cancel`).

---

## 5. Reports
**N/A** — this module defines no QWeb/PDF reports.

---

## 6. Crons & automation (`data/ir_cron_data.xml`)
| Cron record | Schedule | Method | Notes |
|---|---|---|---|
| `ir_cron_ticket_status_update` ("Flight ticket status update") | daily | `hr.flight.ticket.run_update_ticket_status()` | promotes ticket states by date |
| `hr_email_leave_reminder` ("HR Leave Reminder") | daily | `hr.leave.send_leave_reminder()` | reminder e-mails |

**`send_leave_reminder()` flow:** searches `state='validate'` leaves; reads the
`leave_reminder` toggle and `reminder_day_before` (see Gotcha — these are read as **un-prefixed**
config keys); for each leave whose `date_from − reminder_day_before == today`, renders the
`email_template_hr_leave_reminder_mail` template per holiday manager and sends it via
`mail.mail`. The template (`data/mail_data_templates.xml`) is a simple CDATA HTML body that
references `${object.no_of_days_temp}`, `date_from`, `date_to`.

---

## 7. Settings / config_parameters
See §3.6 for the field-level table. Summary of keys this module reads/writes:

| Key | Written by | Read by |
|---|---|---|
| `hr_vacation_mngmt.leave_reminder` | Settings | *(see Gotcha)* `send_leave_reminder` reads `leave_reminder` (no prefix) |
| `hr_vacation_mngmt.reminder_day_before` | Settings | *(see Gotcha)* reads `reminder_day_before` (no prefix) |
| `hr_vacation_mngmt.default_leave_salary` | Settings | `hr.payslip._get_payslip_lines` reads `default_leave_salary` (no prefix) |
| `hr_vacation_mngmt.expense_account_id` | Settings | `action_confirm_ticket` |
| `hr_vacation_mngmt.expense_product_id` | Settings | `action_confirm_ticket` |

---

## 8. Security (`security/`)
- **`ir.model.access.csv`** —
  - `hr.flight.ticket`, `pending.task`, `task.reassign` → full CRUD for both
    `hr_holidays.group_hr_holidays_user` and `base.group_user`.
  - `task.reassign` → additionally CRUD for `hr_holidays.group_hr_holidays_manager`.
  - `account.move` and `account.move.line` → **read-only** for
    `hr_holidays.group_hr_holidays_manager` (so managers can view generated bills).
- **`hr_flight_ticket_rule.xml`** — one global multi-company record rule
  `property_rule_hr_flight_ticket` on `hr.flight.ticket`
  (`company_id = False OR company_id child_of user company`).
- No new security **groups** are defined; the module reuses the standard `hr_holidays`
  user/manager groups.

---

## 9. Demo / seed data (loaded unconditionally, `noupdate="1"`)
> ⚠️ These are named `*_demo` but are listed in the **`data`** key (not `demo`), so they load
> on **every** install regardless of demo-data mode — `action_confirm_ticket` depends on the
> Airlines partner and salary rules existing.

- `data/hr_contribution_register_demo.xml` — `hr.contribution.register` "Leave Salary"
  (`hr_leave_salary_register`).
- `data/hr_salary_rule_demo.xml` — two `hr.salary.rule` records (same code `LS`, sequence 90,
  category `hr_payroll_community.ALW`): **Leave Salary Basic** (`result = categories.BASIC`)
  and **Leave Salary Gross** (`result = categories.BASIC + categories.ALW`).
- `data/res_partner_demo.xml` — `res_partner_data_airlines` ("Airlines") vendor used for
  flight-ticket bills.
- `data/mail_data_templates.xml` — the leave-reminder `mail.template`.

---

## 10. Assets / JS
**N/A** — no `web.assets_*` bundles, no OWL components, no SCSS/JS. The `static/description/`
tree is App-Store marketing artwork only (banner, icons, screenshots) and is not loaded by Odoo.

---

## 11. Gotchas & notes (read before debugging)
- **`expense_account_id` / `expense_product_id` are `required=True` in Settings.** Until both
  are configured, the **general Settings page may refuse to save** the payroll section. Set
  them right after install.
- **Prefix mismatch on config params (latent bug):** Settings *writes* prefixed keys
  (`hr_vacation_mngmt.leave_reminder`, `…reminder_day_before`, `…default_leave_salary`), but
  the runtime code (`send_leave_reminder`, `_get_payslip_lines`) *reads* the **un-prefixed**
  keys (`leave_reminder`, `reminder_day_before`, `default_leave_salary`). As written they
  read different parameters → the reminder/leave-salary-default features may not pick up the
  configured values. If these behave oddly, reconcile the key names. (The flight-ticket
  expense keys are consistent — both prefixed.)
- **`hr.flight.ticket.employee_id` is a `hr.leave` Many2one**, not `hr.employee`. The booking
  flow sets both `employee_id` and `leave_id` to the same leave id. `name_get` reads
  `employee_id.name` (a leave's display name). Don't assume it points at an employee.
- **`action_cancel_ticket` `'open'` branch is dead** — `account.move` has no
  `action_invoice_cancel()` in Odoo 17 (legacy v8 API). Invoice state `'open'` also no longer
  exists (it's `'posted'` now). Cancelling a confirmed ticket with a posted bill won't work.
- **`action_validate()` is called inside the per-task loop** in `task.reassign.action_approve`
  (and inside `_compute`-style code in `hr.leave.action_approve`'s else branch on a recordset)
  — fine for single records but be careful with multi-record actions.
- **`_compute_overlapping_leaves_ids` overlap test is effectively a no-op filter:** it
  intersects `leave_dates` with itself (`set(leave_dates).intersection(set(leave_dates))`),
  so it appends **every** same-department validated leave, not only genuinely overlapping
  ones. If "Overlapping Leaves" looks too broad, this is why.
- **Hard dependency on the two siblings:** `hr_payroll_community` supplies the payslip model,
  salary categories (`ALW`/`BASIC`) and the Settings/payslip views inherited here;
  `hr_leave_request_aliasing` is a declared dependency. Install/update those first.
- **Cybrosys upstream module** — keep local edits minimal/documented; a vendor update will
  overwrite the folder. This is not part of the `care` repo's git history.
- **`# -- coding: utf-8 --`** header (note the missing `#`-style `-*-`) is cosmetic; harmless.

---

## 12. File map
```
__manifest__.py                 depends (hr_leave_request_aliasing, project, hr_payroll_community, account)
README.rst · doc/RELEASE_NOTES.md
i18n/        ar_001.po           (Arabic translation, not auto-loaded)
models/
  hr_flight_ticket.py           hr.flight.ticket (new) — booking, invoice, status cron
  hr_leave.py                   hr.leave (inherit) — approve gate, overlaps, reminders, tickets
  hr_payslip.py                 hr.payslip (inherit) — leave_salary + _get_payslip_lines override
  pending_task.py               pending.task (new)
  res_config_settings.py        res.config.settings (inherit) — 5 config_parameters
wizard/
  task_reassign.py              task.reassign (TransientModel) — reassign + create project.task
  task_reassign_views.xml
views/
  hr_flight_ticket_views.xml    form/tree/booking-form + action + Time Off menu
  hr_leave_views.xml            inherits hr_holidays leave form
  hr_payslip_views.xml          inherits hr_payroll_community payslip form
  pending_task_views.xml        pending.task form
  res_config_settings_views.xml inherits hr_payroll_community settings form (Leaves section)
data/
  ir_cron_data.xml              2 crons (ticket status, leave reminder)
  mail_data_templates.xml       leave-reminder mail.template
  hr_salary_rule_demo.xml       Leave Salary Basic/Gross rules   (loaded as data, not demo)
  hr_contribution_register_demo.xml  Leave Salary register
  res_partner_demo.xml          Airlines vendor
security/
  ir.model.access.csv           ACLs (hr_holidays user/manager + base.group_user)
  hr_flight_ticket_rule.xml     multi-company record rule
static/description/             marketing artwork only (not loaded by Odoo)
```
