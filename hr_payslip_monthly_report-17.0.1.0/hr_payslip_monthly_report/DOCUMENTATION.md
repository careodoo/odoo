# hr_payslip_monthly_report — Developer Handover Documentation

> **Payroll Advanced Features** — a Cybrosys third-party add-on for Odoo 17
> **Community** that bolts three conveniences onto `hr_payroll_community`:
> (1) a **Payslip Analysis** pivot/graph report (SQL view) for monthly payroll
> analysis, (2) **automatic e-mail** of the payslip PDF to the employee on
> confirmation, plus a manual "Send Mail" button, and (3) a **mass-confirm**
> wizard to validate many payslips at once. UI is English. This file documents
> ONLY `hr_payslip_monthly_report` — the sibling `hr_payroll_community` in the
> same bundle folder is a dependency, not part of this module. Read this before
> touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `hr_payslip_monthly_report` |
| Display name | **Payroll Advanced Features** |
| Version | `17.0.1.0.0` (per `doc/RELEASE_NOTES.md`; manifest has no `version` key, so Odoo defaults it — bundle folder is named `…-17.0.1.0`) |
| Odoo | 17.0 **Community** |
| Category | Generic Modules/Human Resources |
| License | LGPL-3 |
| Author / maintainer | Cybrosys Techno Solutions |
| Depends | `hr_payroll_community`, `mail` |
| External Python libs | **None** beyond stdlib (`time`, `calendar.monthrange`, `datetime.date`, `logging`) |
| Models | `hr.payslip` (inherited), `res.config.settings` (inherited), `hr.payroll.report` (new SQL view, `_auto=False`), `payslip.confirm` (TransientModel wizard) |
| Application | `False` · auto_install `False` · installable `True` |

### Deployment (this server)
- DB: `odoo17` · service: `odoo-17.service` (systemd) · runs as user `odoo`.
- Python venv: `/home/odoo/.pyenv/versions/odoo-17-env/bin/python`
- Odoo bin: `/home/odoo/odoo-17.0+e.20241205/odoo-bin` · conf: `/home/odoo/odoo.conf`
- **Update + restart:**
  ```bash
  sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
    /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
    -d odoo17 -u hr_payslip_monthly_report --stop-after-init --no-http
  sudo systemctl restart odoo-17.service
  ```
- No dev mode. Log file: `/var/log/odoo/odoo-17.log`.
- **Hard prerequisite:** `hr_payroll_community` must be installed (it is shipped
  in the same bundle parent folder `hr_payslip_monthly_report-17.0.1.0/`). The
  module inherits its payslip form, its menu root, its security group, and its
  payslip PDF report — all `ref`s resolve against `hr_payroll_community`.
- `init()` of the SQL-view model runs on every `-u` (it `CREATE or REPLACE VIEW`),
  so re-updating after any change to `report/hr_payslip_report.py` rebuilds the view.

---

## 2. Architecture overview

```
hr.payslip  (INHERITED — from hr_payroll_community)
├── + is_send_mail (Boolean flag — "mail already sent")
├── action_payslip_done()  (OVERRIDE)
│      └── if config param send_payslip_by_email → set flag + send template
│          email_template_payslip to each payslip.employee_id.private_email
└── action_payslip_send()   (NEW)
       └── opens mail.compose.message wizard pre-loaded with the template
                 ▲                                    │
                 │ "Send Mail" button (form view)     │ uses report
                 │                                     ▼
res.config.settings (INHERITED)            mail.template  email_template_payslip
└── + send_payslip_by_email (Boolean)        (attaches hr_payroll_community
       stored as ir.config_parameter          .hr_payslip_report_action PDF)
       "send_payslip_by_email"

hr.payroll.report  (NEW — _auto=False PostgreSQL VIEW, read-only)
   built from hr_payslip_line ⋈ hr_payslip ⋈ hr_salary_rule
              ⋈ hr_employee ⋈ hr_salary_rule_category ⋈ department/job ⋈ company
   → exposed as a Pivot + Graph "Payslips" report under Payroll ▸ Reports

payslip.confirm  (NEW — TransientModel wizard)
   list-view action "Confirm Payslip" on hr.payslip
   → loops active_ids, calls action_payslip_done() on each non-cancel/non-done
```

**Design notes**
- The monthly report is **not** a QWeb-PDF; it is a **PostgreSQL view** surfaced
  as pivot + graph (analysis report), the same pattern as Odoo's stock/sale
  reporting. No xlsx/PDF generation code exists in this module for the analysis
  report. (The per-payslip PDF that gets e-mailed belongs to `hr_payroll_community`.)
- The single business toggle (`send_payslip_by_email`) is stored as an
  `ir.config_parameter`, read with `sudo()` in both the settings model and the
  payslip override.

---

## 3. Data model

### 3.1 `hr.payslip` (inherited — `models/hr_payslip.py`)
| Field | Type | Notes |
|---|---|---|
| `is_send_mail` | Boolean | "Is Send Mail" — marks that the payslip e-mail has been sent; hides the **Send Mail** button when `True` |

**Methods:**
- `action_payslip_done()` — **override**. Before/after `super()`:
  - If `ir.config_parameter` `send_payslip_by_email` is set, marks
    `is_send_mail = True`, then after the standard confirmation loops each
    payslip and, when `employee_id.private_email` is set, sends the
    `hr_payslip_monthly_report.email_template_payslip` template
    (`force_send=True`) and logs an info line. Returns the `super()` result.
  - **Gotcha:** the mail is gated on the **private** e-mail
    (`employee_id.private_email`), not the work e-mail. No private e-mail = no
    auto mail (silently skipped).
- `action_payslip_send()` — **new**. `ensure_one()`; sets `is_send_mail = True`;
  resolves the payslip template id and the `mail.email_compose_message_wizard_form`
  view via `ir.model.data._xmlid_lookup` (each guarded with `try/except ValueError`
  → `False`); returns an `ir.actions.act_window` opening `mail.compose.message`
  in a dialog (`target='new'`) pre-filled with `default_template_id`,
  `default_res_ids = self.ids`, `default_model='hr.payslip'`,
  `default_composition_mode='comment'`, `force_email=True`. Bound to the
  **Send Mail** button in the payslip form.

### 3.2 `res.config.settings` (inherited — `models/res_config_settings.py`)
| Field | Type | Notes |
|---|---|---|
| `send_payslip_by_email` | Boolean | "Automatic Send Payslip By Mail" — backed by `ir.config_parameter` key `send_payslip_by_email` |

`get_values()` reads the param (default `False`); `set_values()` writes it back.
Both use `sudo()`.

### 3.3 `hr.payroll.report` (NEW SQL VIEW — `report/hr_payslip_report.py`)
`_name = 'hr.payroll.report'`, **`_auto = False`** (read-only PostgreSQL view,
one row per payslip-line grouping). Rebuilt in `init()` via
`tools.drop_view_if_exists` + `CREATE or REPLACE VIEW` from `_select()`,
`_from()`, `_group_by()`.

**Fields (mapped from the view columns):**
| Field | Type | View source |
|---|---|---|
| `name` | M2o `hr.employee` ("Employee") | `emp.id` |
| `start_date` | Date (default `%Y-%m-01`, `invisible`) | search-only default window start |
| `end_date` | Date (default last day of current month via `monthrange`, `invisible`) | search-only default window end |
| `date_from` | Date ("From") | `ps.date_from` |
| `date_to` | Date ("To") | `ps.date_to` |
| `state` | Selection draft/verify(Waiting)/done/cancel(Rejected) | `ps.state` |
| `job_id` | M2o `hr.job` | `jb.id` |
| `company_id` | M2o `res.company` | `cmp.id` |
| `department_id` | M2o `hr.department` | `dp.id` |
| `rule_name` | M2o `hr.salary.rule.category` ("Rule Category") | `rl.id` |
| `rule_amount` | Float ("Amount") — the **measure** | `psl.total` |
| `struct_id` | M2o `hr.payroll.structure` | `ps.struct_id` |
| `rule_id` | M2o `hr.salary.rule` | `rlu.id` |

**SQL joins (`_from`):** `hr_payslip_line psl` → `hr_payslip ps` →
`hr_salary_rule rlu` → `hr_employee emp` → `hr_salary_rule_category rl`,
LEFT JOIN `hr_department dp`, LEFT JOIN `hr_job jb`, JOIN `res_company cmp`.
The view id is `min(psl.id)` aliased implicitly; grouping is over payslip /
employee / dept / job / company / dates / state / line total / line name /
category / rule (see `_group_by`).

> `start_date`/`end_date` carry Python defaults computed at **class-load time**
> (`date.today()`, `time.strftime`) — they exist only to seed search defaults and
> are marked `invisible`; they are not view columns. They are static for the life
> of the worker process (computed once at import), which is fine for their
> search-default role but means they don't "roll over" at midnight without a
> restart.

### 3.4 `payslip.confirm` (wizard — `wizard/payslip_confirm.py`)
`_name = 'payslip.confirm'` · `_description = 'Mass Confirm Payslip'` ·
TransientModel, **no fields**.
- `confirm_payslip()` — reads `active_ids` from context, and for each id searches
  the payslip with `state not in ('cancel','done')` and calls
  `action_payslip_done()` on it (which itself may fire the auto-mail). Used to
  validate a multi-selection of payslips in one click.

---

## 4. Views & wizards (`views/`, `wizard/…_views.xml`)

- **`views/hr_payslip_views.xml`** — inherits `hr_payroll_community.hr_payslip_view_form`
  and, after the `action_compute_sheet` button, injects a **Send Mail** button
  (`name="action_payslip_send"`, `class="oe_highlight"`,
  `invisible="is_send_mail == True"`) plus the hidden `is_send_mail` field.
- **`views/res_config_settings_views.xml`** — inherits `base.res_config_settings_view_form`
  (priority 45), and after the `hr_payroll_localization` block inside the
  `hr_payroll_community` settings page adds a setting box **"Payroll Email
  Notification"** bound to `send_payslip_by_email`.
- **`wizard/payslip_confirm_views.xml`** — form for `payslip.confirm` (a grey
  "Do you want to confirm these Payslips?" prompt + **Confirm Payslip** /
  **Cancel** footer) and the action `payslip_confirm_action`
  (`target='new'`) bound to `hr.payslip` **list view** via
  `binding_model_id = hr_payroll_community.model_hr_payslip`,
  `binding_view_types = list` → appears in the list "Action" cog menu.
- **`report/hr_payslip_report_views.xml`** — pivot, graph, and search views for
  `hr.payroll.report` plus the action and menus (see §5).

---

## 5. Reports

There are **two distinct "report" concepts**; do not confuse them.

### 5.1 Payslip Analysis report (this module's report — pivot/graph, NOT pdf/xlsx)
- **Pivot** `hr_payroll_report_view_pivot` — rows: `name` (Employee); columns:
  `date_from` by **month**; measure: `rule_amount`.
- **Graph** `hr_payroll_report_view_graph` — rows: `date_from`; measure: `rule_amount`.
- **Search** `hr_payroll_report_search` — fields `name`, `date_from`,
  `company_id` (multi-company only), hidden `start_date`/`end_date`; filters
  **This Month**, **This Year** (note the `%%` escaping for the `time.strftime`
  domains), **Done**, **Draft**; group-by **Employee / Job / Department / Status /
  Company**.
- **Action** `hr_payroll_report_action` — "Payslips", `view_mode = pivot,graph`,
  `context = {'search_default_year':1}` (opens on the current year).
- **Menus:** a **Reports** parent menu (`menu_hr_payslip_reports`, seq 45) under
  `hr_payroll_community.menu_hr_payroll_community_root`, and **Payslip Report**
  (`menu_hr_payslip_view_report`, seq 10) → the action. Both restricted to
  `hr_payroll_community.group_hr_payroll_community_user`.

> No XLSX or QWeb-PDF generation exists for this analysis report — it is a live
> pivot/graph over the SQL view. There is **no `report_xlsx`/`xlsxwriter`
> dependency** and no `ir.actions.report` defined in this module.

### 5.2 Payslip PDF that gets e-mailed (belongs to `hr_payroll_community`)
The mail template attaches `hr_payroll_community.hr_payslip_report_action` (the
standard per-payslip PDF) via `report_template_ids` — defined in the dependency,
not here. This module only references it.

---

## 6. Crons
**N/A** — this module defines no `ir.cron` records. Auto-mail is triggered
synchronously by payslip confirmation (`action_payslip_done`), not by a scheduler.

---

## 7. Settings
One setting only, on the existing Payroll settings page:

| Setting (label) | Field / param | Effect |
|---|---|---|
| **Payroll Email Notification** ("Automatic Send Payslip By Mail") | `send_payslip_by_email` → `ir.config_parameter` `send_payslip_by_email` | When on, confirming a payslip auto-sends the payslip PDF to the employee's **private** e-mail via `email_template_payslip` |

To enable: **Settings ▸ Payroll** (the `hr_payroll_community` config page) ▸ tick
**Payroll Email Notification**.

---

## 8. Security (`security/ir.model.access.csv`)
Two ACL rows, both granted full CRUD to
`hr_payroll_community.group_hr_payroll_community_user`:

| Access id | Model | r/w/c/u |
|---|---|---|
| `access_hr_payslip_monthly_report_manager` | `hr.payroll.report` | 1/1/1/1 |
| `access_group_user` | `payslip.confirm` | 1/1/1/1 |

No record rules, no new security groups. (Write/create/unlink on `hr.payroll.report`
are nominal — it is an `_auto=False` view and not writable in practice.)

---

## 9. Assets / JS
**N/A** — no JS, SCSS, or OWL components, and **no `assets` key** in the manifest.
The `static/description/` tree (banner, icon, `index.html`, screenshots, icons)
is the Odoo Apps store listing artwork only — **not loaded by Odoo at runtime**.

---

## 10. Gotchas & notes
- **Auto-mail uses `private_email`, not `work_email`.** Employees without a
  private e-mail are silently skipped on confirmation. Verify private e-mails
  before relying on the automation.
- **`hr_payroll_community` is mandatory.** Every inherit/ref (payslip form, menu
  root, payroll user group, `model_hr_payslip`, `hr_payslip_report_action`)
  resolves against it. Update that module first if both changed.
- **The analysis report is a SQL view (`_auto=False`).** Editing
  `report/hr_payslip_report.py` requires a module `-u` to run `init()` and rebuild
  the view; a plain restart will not pick up SQL changes.
- **`start_date`/`end_date` are import-time constants** (computed once when the
  class loads) and `invisible` — they seed search defaults only; they don't
  auto-roll at midnight without a worker restart.
- **`mail.template` `body_html` uses CDATA** here (it is a QWeb/Jinja-rendered
  template via `mail`), unlike some other modules that forbid CDATA — this is
  valid for `mail.template`.
- **`is_send_mail` only hides the manual button / records intent.** It does not
  itself prevent re-sending: `action_payslip_send` always sets it `True`;
  `action_payslip_done` sets it only when the config param is on. There is no
  uniqueness/idempotency guard preventing a second send via the compose wizard.
- **Mass-confirm skips `cancel`/`done`** payslips by design (the search domain
  filters them out); selecting already-done payslips is a no-op, not an error.
- **Version mismatch:** `RELEASE_NOTES.md` says `17.0.1.0.0`, the bundle folder is
  `…-17.0.1.0`, and the manifest omits `version` entirely. Treat `17.0.1.0.0` as
  authoritative; add a `version` key to the manifest if precise versioning matters.
- **Vendor module:** authored by Cybrosys (LGPL-3). Local customisations will be
  overwritten by a vendor re-import — track any edits in git.

---

## 11. File map
```
__manifest__.py                       depends: hr_payroll_community, mail; data load order below
__init__.py                           imports models, report, wizard
models/
  __init__.py
  hr_payslip.py                       inherit hr.payslip: is_send_mail, action_payslip_done (override), action_payslip_send
  res_config_settings.py             inherit res.config.settings: send_payslip_by_email (config_parameter)
report/
  __init__.py
  hr_payslip_report.py               hr.payroll.report — _auto=False SQL VIEW (_select/_from/_group_by/init)
  hr_payslip_report_views.xml        pivot + graph + search + action + Reports/Payslip Report menus
wizard/
  __init__.py
  payslip_confirm.py                 payslip.confirm — Mass Confirm Payslip wizard (confirm_payslip)
  payslip_confirm_views.xml          wizard form + list-bound action (Action cog on hr.payslip list)
views/
  hr_payslip_views.xml               payslip form: "Send Mail" button + hidden is_send_mail
  res_config_settings_views.xml      Payroll settings: "Payroll Email Notification" toggle
data/
  mail_template_data.xml             email_template_payslip (Monthly Payslip Email; attaches community PDF)
security/
  ir.model.access.csv                ACLs for hr.payroll.report & payslip.confirm (payroll user group)
static/description/                   Apps-store listing assets only (NOT runtime assets)
doc/RELEASE_NOTES.md                  v17.0.1.0.0 — initial commit
README.rst
```

> **Manifest `data` load order:** `security/ir.model.access.csv` →
> `views/hr_payslip_views.xml` → `views/res_config_settings_views.xml` →
> `data/mail_template_data.xml` → `wizard/payslip_confirm_views.xml` →
> `report/hr_payslip_report_views.xml`.
