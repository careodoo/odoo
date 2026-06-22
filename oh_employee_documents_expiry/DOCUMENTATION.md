# oh_employee_documents_expiry — Developer Handover Documentation

> **Open HRMS Employee Documents Expiry** — a third-party (Cybrosys / Open HRMS)
> Odoo 17 module that stores **employee documents** (passports, civil IDs, work
> permits, licences …) with an **expiry date**, and e-mails a renewal reminder
> via a daily cron as each document approaches/reaches its expiry. It adds a
> "Documents" smart button to the employee form, plus simple master data
> (Document Types, Document Templates). UI labels are English; this client's
> data/content is often Arabic. Read this before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `oh_employee_documents_expiry` |
| Display name | Open HRMS Employee Documents Expiry |
| Version | `17.0.1.0.0` |
| Odoo | 17.0 |
| License | LGPL-3 |
| Author / origin | Cybrosys Techno Solutions / Open HRMS (third-party, **not** in-house) |
| Depends | `hr` |
| External Python libs | **None** (stdlib only: `datetime`) |
| New models | `hr.employee.document`, `document.type`, `hr.document` |
| Inherited models | `hr.employee`, `ir.attachment` |
| Automation | 1 `ir.cron` — **Employee Document Expiration** (daily) |
| Reports / wizards / JS assets | **N/A** (none) |

### Deployment (this server)
DB `odoo17` · systemd `odoo-17.service` · user `odoo`. Update + restart:
```bash
sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
  /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
  -d odoo17 -u oh_employee_documents_expiry --stop-after-init --no-http
sudo systemctl restart odoo-17.service
```
- Addons path includes `/home/odoo/care` (this repo, branch `17`).
- No dev mode. Conf: `/home/odoo/odoo.conf`. Log: `/var/log/odoo/odoo-17.log`.
- No external libs to install — the module is pure Python/ORM.
- **Demo data** (`data/*_demo.xml`) loads only if the DB was created in demo
  mode. On `odoo17` (production) it is normally **not** loaded.

---

## 2. Architecture overview

```
hr.employee  (inherited)
├── document_count (computed) ──> "Documents" smart button (action_document_view)
└── (no stored back-link; counted by search on hr.employee.document)

hr.employee.document   (core model — one row per employee document)
├── employee_ref_id  ── many2one → hr.employee   (the owner; hidden field)
├── document_type_id ── many2one → document.type  (master data: passport/ID/…)
├── doc_attachment_ids ── many2many → ir.attachment  (scanned copies)
├── expiry_date / issue_date / before_days / notification_type
└── mail_reminder()  ◄── called daily by ir.cron → sends mail.mail to work_email

document.type   (master data — just a Name)
hr.document     (reusable "Document Template": name + note + attachments) — standalone
ir.attachment  (inherited: two m2m relation helper fields)

Automation:
  ir.cron "Employee Document Expiration" (daily) → model.mail_reminder()
```

**Design notes**
- This is an **upstream Cybrosys/Open HRMS addon**, lightly placed in the `care`
  repo. There is no Arabic-specific custom code; any Arabic appears only in the
  data users enter and in `i18n/ar_001.po` (Arabic translation file).
- The reminder logic lives entirely in `hr.employee.document.mail_reminder()`
  and is driven by `notification_type` + `before_days` + `expiry_date`.
- `hr.document` ("Document Templates") is a separate, **unrelated** master-data
  model — it is not linked to employees and not part of the expiry flow.

---

## 3. Data model

### 3.1 `hr.employee.document` (core — `models/hr_employee_document.py`)
One stored document belonging to an employee. `_description = 'HR Employee Documents'`.

| Field | Type | Purpose |
|---|---|---|
| `name` | Char (required, `copy=False`) | Document **number** (label "Document Number") |
| `description` | Text (`copy=False`) | Free-text description |
| `expiry_date` | Date (`copy=False`) | Expiry date — drives the reminder |
| `issue_date` | Date (default `now()`, `copy=False`) | Date issued |
| `employee_ref_id` | Many2one `hr.employee` (`invisible=1`, `copy=False`) | The owning employee (hidden; set via context default) |
| `document_type_id` | Many2one `document.type` | Document category (passport/ID/…) |
| `doc_attachment_ids` | Many2many `ir.attachment` (`doc_attach_rel`) | Scanned copies of the document |
| `before_days` | Integer | How many days **before** expiry to start notifying |
| `notification_type` | Selection | When to notify (see below) |

**`notification_type` Selection values:**
| Key | Label | Meaning |
|---|---|---|
| `single` | Notification on expiry date | mail only on the exact expiry date |
| `multi` | Notification before few days | mail on `expiry_date − before_days` **and** on the expiry date |
| `everyday` | Everyday till expiry date | mail every day from `expiry_date − before_days` onward (`today >= expiry − before_days`) |
| `everyday_after` | Notification on and after expiry | mail every day up to `expiry_date + before_days` (`today <= expiry + before_days`) |

**Key methods:**
- **`mail_reminder()`** — the cron entrypoint. Iterates **all** documents with a
  set `expiry_date` (`search([('expiry_date','!=',False)])`), evaluates whether
  *today* is a notification day for that record's `notification_type`/`before_days`,
  and if so builds an HTML body and creates+sends a `mail.mail` to
  `employee_ref_id.work_email`. Subject: `Document-%s Expired On %s`.
  - **Fallback rule:** if `notification_type` is **empty**, it notifies when
    `today == expiry_date − 7 days` (hard-coded 7-day default).
- **`_check_expiry_date()`** — `@api.constrains('expiry_date')`. Raises
  `UserError('Your Document Is Expired.')` if `expiry_date < today` on
  create/write. **Gotcha:** you cannot save a document whose expiry date is
  already in the past (see §11).

### 3.2 `document.type` (`models/document_type.py`)
Master data to categorise documents. `_description = 'Document Type'`.
Single field: `name` (Char, required). Managed from Configuration (see §5).

### 3.3 `hr.document` (`models/hr_document.py`)
A standalone **"Document Template"** record — *not* linked to employees and *not*
part of the expiry flow. `_description = 'HR Document Template '`.
| Field | Type | Purpose |
|---|---|---|
| `name` | Char (required, `copy=False`) | Template/document name |
| `note` | Text (`copy=False`) | Note |
| `attach_ids` | Many2many `ir.attachment` (`attach_rel`) | Attached copies |

### 3.4 `hr.employee` (inherited — `models/hr_employee.py`)
Adds:
| Field / method | Type | Purpose |
|---|---|---|
| `document_count` | Integer (computed `_compute_document_count`, **not stored**) | Count of `hr.employee.document` where `employee_ref_id == self` (via `sudo().search_count`) |
| `action_document_view()` | method | Opens the employee's documents list/form, filtered by `employee_ref_id`, with `default_employee_ref_id` in context so new rows pre-link to this employee |

The smart button on the employee form calls `action_document_view`.

### 3.5 `ir.attachment` (inherited — `models/ir_attachment.py`)
Adds two **invisible helper** Many2many fields that back the attachment relations
on the models above:
- `doc_attach_rel` → `hr.employee.document` (relation table `doc_attachment_ids`).
- `attach_rel` → `hr.document` (relation table `attach_ids`).
These exist so the inverse side of the m2m attachment links resolves; they are
`invisible=1` and not shown in any view.

---

## 4. Views

All view files are under `views/`. There are **no wizards, no QWeb/PDF reports,
and no JS/OWL assets** in this module.

### 4.1 `views/hr_employee_document_views.xml`
- **Employee form inherit** (`view_employee_form`, inherits `hr.view_employee_form`):
  adds a **"Documents"** stat button (`oe_stat_button`, icon `fa-list-ol`,
  `widget="statinfo"` over `document_count`) into the employee `oe_button_box`,
  calling `action_document_view`.
- **`hr.employee.document` form** — two groups (name, employee, type, attachments /
  issue & expiry dates, notification type, before_days) + a "Description" notebook
  page. `before_days` is hidden when `notification_type == 'single'`.
- **`hr.employee.document` tree** — name, employee, document type, expiry date.
- **Search** — single "Group By → Employee" filter (`group_by:employee_ref_id`).
- **Action** `hr_employee_document_action` — "Employee Documents", `tree,form`,
  default context `{'search_default_Employee': 1}` (opens grouped by employee).
- **Menu** `hr_employee_document_menu` — "Documents" under
  `hr.menu_hr_employee_payroll`, restricted to **`hr.group_hr_manager`**.

### 4.2 `views/document_type_views.xml`
- Form + editable tree (`editable="bottom"`) for `document.type` (just `name`).
- Action `document_type_action` ("Employee Document Types").
- **Parent menu** `menu_human_resources_configuration_document` ("Employee
  Document") under `hr.menu_human_resources_configuration`, gated to
  **`base.group_no_one`** (developer/technical features only — see §11).
- Child menu `document_type_menu` ("Employee Document Types") → the action.

### 4.3 `views/hr_document_views.xml`
- Form + tree for `hr.document` (Document Templates).
- Action `hr_document_action` ("Document Templates").
- Menu `hr_document_menu` ("Document Templates") under the same
  "Employee Document" configuration parent, restricted to **`hr.group_hr_manager`**.

### Menu summary
```
Employees
└── (employee form) ► [Documents] smart button
Employees ▸ Payroll ▸ Documents              (hr_employee_document_menu, hr_manager)
Employees ▸ Configuration ▸ Employee Document  (parent, base.group_no_one)
        ├── Document Templates                (hr_document_menu, hr_manager)
        └── Employee Document Types           (document_type_menu)
```

---

## 5. Reports
**N/A** — this module defines no QWeb/PDF reports.

## 6. Wizards
**N/A** — no `TransientModel` / wizard.

---

## 7. Automation — cron (the heart of this module)

`data/ir_cron_data.xml` (loaded with `noupdate="1"`):

| Field | Value |
|---|---|
| `id` | `ir_cron_scheduler_employee_data_reminder` |
| Name | **Employee Document Expiration** |
| Interval | every **1 day** (`interval_number=1`, `interval_type=days`) |
| `numbercall` | `-1` (runs indefinitely) |
| `doall` | `False` (skipped missed runs are not caught up) |
| Model | `hr.employee.document` |
| State | `code` |
| Code | `model.mail_reminder()` |

So once a day Odoo calls `hr.employee.document.mail_reminder()`, which loops over
every document with an `expiry_date` and e-mails the owning employee when the
day matches the document's `notification_type` rule (see §3.1).

> ⚠️ `noupdate="1"` means edits to the cron record in this XML are **not**
> re-applied on `-u` after first install. To change the schedule, edit the cron
> record in the UI (Settings ▸ Technical ▸ Scheduled Actions) or clear
> `ir_model_data.noupdate` for this record once.

### Mail delivery details
- Reminders are sent as raw `mail.mail` records (created + `.send()` immediately),
  **not** via a `mail.template`. The body is built inline in Python.
- Recipient = `employee_ref_id.work_email`. **If the employee has no work e-mail,
  `email_to` is empty** and the mail will not reach anyone (no guard exists).
- `author_id` = the cron-executing user's partner (the cron runs as its
  configured user, default OdooBot/admin).

---

## 8. Settings / config parameters
**N/A** — the module uses **no** `ir.config_parameter` and adds **no**
`res.config.settings` fields. The only "settings" are per-document
(`notification_type`, `before_days`) and the cron schedule itself.

---

## 9. Security

`security/ir.model.access.csv` only (no record rules, no custom groups):

| Model | Group | R | W | C | U(nlink) |
|---|---|---|---|---|---|
| `hr.employee.document` | `base.group_user` | ✓ | – | – | – |
| `hr.employee.document` | `hr.group_hr_user` | ✓ | ✓ | ✓ | – |
| `hr.employee.document` | `hr.group_hr_manager` | ✓ | ✓ | ✓ | ✓ |
| `hr.document` | `base.group_user` | ✓ | – | – | – |
| `hr.document` | `hr.group_hr_user` | ✓ | ✓ | ✓ | – |
| `hr.document` | `hr.group_hr_manager` | ✓ | ✓ | ✓ | ✓ |
| `document.type` | `hr.group_hr_manager` | ✓ | ✓ | ✓ | ✓ |

Notes:
- Every internal user (`base.group_user`) can **read** documents/templates;
  only HR Officers (`hr.group_hr_user`) can create/edit, and only HR Managers
  can delete.
- **`document.type` has no read access for non-managers.** A plain HR officer
  opening a document form may not be able to read the `document_type_id` label
  (only managers have ACL on `document.type`). Keep this in mind if officers
  report blank/permission errors on the type field.
- The menus that expose these models are themselves gated (Documents & templates
  → `hr.group_hr_manager`; type parent menu → `base.group_no_one`).

---

## 10. Assets / JS
**N/A** — no `static/src` JS/SCSS/OWL. The `static/description/` tree is only the
Odoo Apps store listing (banner, icon, screenshots, `index.html`) and is not
loaded into any asset bundle.

---

## 11. Gotchas & notes (read before debugging)

- **Cannot save a past-dated document.** The `@api.constrains('expiry_date')`
  raises `UserError('Your Document Is Expired.')` whenever `expiry_date < today`.
  This blocks back-dating/importing already-expired documents and also blocks
  re-saving a record once its expiry date has passed (any later write that
  re-validates the field will fail). If historical/expired docs must be stored,
  this constraint has to be relaxed.
- **`everyday_after` is mislabelled vs. behaviour.** Its label says "on and
  after expiry", but the condition is `today <= expiry_date + before_days` — i.e.
  it sends every day from *now until `before_days` after expiry*, not strictly
  after the expiry date. Combined with the past-date constraint above, the
  "after expiry" window is effectively unreachable through the UI once the date
  passes.
- **No work e-mail = silent no-op.** `mail_reminder` sets `email_to` from
  `work_email` with no fallback/log; documents for employees without a work
  e-mail simply never notify.
- **Reminder goes to the employee, not HR.** The mail is addressed to the
  document owner's `work_email`. There is no manager/HR copy and no chatter post.
- **`mail_reminder` scans the whole table daily.** It does `search([('expiry_date','!=',False)])`
  with no date pre-filter, then evaluates each in Python. Fine for typical HR
  volumes; be aware if document counts grow very large.
- **`issue_date` default is evaluated at module load** (`default=fields.datetime.now()`
  is a value, not a lambda). In practice Odoo Date fields coerce it, but note it
  is not a per-record `lambda self: ...` default.
- **`document.type` config menu is hidden** behind `base.group_no_one` — it only
  appears in developer mode. To let HR manage types normally, change the parent
  menu's `groups` (currently `base.group_no_one`).
- **Third-party / upstream module.** This is a Cybrosys Open HRMS addon. Prefer
  keeping local changes minimal and documented here, so future upstream updates
  remain mergeable. Demo XML is gated to demo-mode DBs and won't load on `odoo17`.
- **`ir.attachment` helper fields are invisible** and only exist to back the m2m
  relations on `hr.employee.document` / `hr.document`; don't expose or repurpose
  them.

---

## 12. File map
```
__manifest__.py                     depends=['hr']; data + demo lists
__init__.py / models/__init__.py    module + model registration
models/
  hr_employee_document.py           CORE — hr.employee.document + mail_reminder() + constraint
  document_type.py                  document.type (master data: name)
  hr_document.py                    hr.document  (standalone "Document Template")
  hr_employee.py                    hr.employee inherit — document_count + smart button
  ir_attachment.py                  ir.attachment inherit — m2m relation helpers
data/
  ir_cron_data.xml                  daily cron → model.mail_reminder()  (noupdate)
  document_type_demo.xml            demo only
  hr_work_location_demo.xml         demo only
  hr_employee_demo.xml              demo only
  hr_employee_document_demo.xml     demo only
views/
  hr_employee_document_views.xml    employee smart button + document form/tree/search/menu
  document_type_views.xml           type form/tree + config menus
  hr_document_views.xml             template form/tree + menu
security/
  ir.model.access.csv               ACLs (no record rules, no custom groups)
i18n/ar_001.po                      Arabic translations
doc/RELEASE_NOTES.md                upstream changelog (v17.0.1.0.0)
README.rst                          upstream readme
static/description/                 Apps-store listing assets only (NOT loaded by Odoo)
```
