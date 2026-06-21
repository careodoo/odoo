# care_uniform_delivery — Developer Handover Documentation

> **Care Uniform Delivery** — a small custom Odoo 17 module that records the
> handover of work **uniforms** (الزي / البدلة) to employees, with a captured
> signature as proof of receipt. It supports two flows: **individual** deliveries
> (one employee per record) and **bulk** deliveries (many employees on one
> record). It also adds two stat buttons to the standard `hr.employee` form so HR
> can see, per employee, how many uniform deliveries they have. This file is the
> single source of truth for handover — read it before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `care_uniform_delivery` |
| Display name | `Care Uniform Delivery` |
| Version | `0.1` (manifest) — runs on Odoo 17 |
| Depends | `base`, `hr` |
| External Python libs | none (pure Odoo ORM; no `requests`/`qrcode`/etc.) |
| New models | `uniform.delivery`, `uniform.type` |
| Inherited model | `hr.employee` (two stat buttons + their counts) |
| Reports | none |
| Crons / automation | none |
| Settings / config params | none |
| Security groups | none custom — uses `base.group_user` |
| Assets / JS | none custom (uses standard `signature` widget) |
| Menus | English labels |

> ⚠️ The `summary`/`description`/`author`/`website` in `__manifest__.py` are still
> the **Odoo scaffold placeholders** ("My Company", "http://www.yourcompany.com",
> "Long description of module's purpose"). They are cosmetic and do not affect
> behaviour, but should be filled in before any real publishing.

### Deployment (this server)
DB `odoo17` · systemd `odoo-17.service` · user `odoo`. Update + restart:
```bash
/home/odoo/.pyenv/versions/odoo-17-env/bin/python \
  /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
  -d odoo17 -u care_uniform_delivery --stop-after-init --no-http
sudo systemctl restart odoo-17.service
```
- Run as the `odoo` user (prefix with `sudo -u odoo` if invoking as another user).
- No external Python packages required — nothing to `pip install` in the venv.
- No JS/SCSS/QWeb assets, so the `-u` is only needed to load model/view changes;
  pure data tweaks still need it because views are XML.
- Log file: `/var/log/odoo/odoo-17.log`.

---

## 2. Architecture overview

```
hr.employee (inherited — models/hr_employee.py)
├── uniform_delivery_count       (Integer, computed) → count of individual deliveries
├── bulk_uniform_delivery_count  (Integer, computed) → count of bulk deliveries incl. this emp
├── button_show_uniform_delivery()        → opens individual deliveries for this employee
└── button_show_bulk_uniform_delivery()   → opens bulk deliveries that include this employee

uniform.delivery (models/uniform_delivery.py)   — the core record
├── many2one  → uniform.type        (which uniform / الزي)
├── many2one  → hr.employee  employee_id   (individual delivery target)
├── many2many → hr.employee  employee_ids  (bulk delivery targets)
├── Binary    → signature           (required — proof of receipt)
└── many2one  → res.company         (company_id, required)

uniform.type (models/uniform_type.py)           — simple master/lookup
└── name + sequence

Two menus / two act_window actions split the SAME model by domain:
  • "Uniform Delivery"      → domain [('employee_id','!=',False)]  (individual)
  • "Bulk Uniform Delivery" → domain [('employee_id','=',False)]   (bulk)
```

**Design notes**
- There is **one** physical model (`uniform.delivery`) for both flows. "Individual"
  vs "bulk" is purely a **domain split** on whether `employee_id` is set:
  - Individual record → `employee_id` filled, `employee_ids` empty.
  - Bulk record → `employee_id` empty (`False`), `employee_ids` filled.
- The split is also reflected in the form/tree via **context flags** (`show_employee`
  / `show_employees`) that hide whichever employee field doesn't apply — see §5.
- No workflow/state machine, no chatter (`mail.thread`), no reports, no crons.

---

## 3. Data model

### 3.1 `uniform.delivery` (`models/uniform_delivery.py`)
`_name = 'uniform.delivery'` · `_description = 'Uniform Delivery'` · `_order = 'sequence'`.

| Field | Type | Notes |
|---|---|---|
| `name` | Char | **required** — label for the delivery record |
| `sequence` | Integer (default `10`) | manual ordering (handle widget in tree) |
| `uniform_type_id` | Many2one `uniform.type` | which uniform was delivered |
| `date` | Date | delivery date |
| `employee_id` | Many2one `hr.employee` | the **individual** recipient (empty on bulk records) |
| `employee_ids` | Many2many `hr.employee` | the **bulk** recipients (empty on individual records) |
| `signature` | Binary | **required** — captured proof of receipt (signature widget) |
| `active` | Boolean (default `True`) | standard archive flag |
| `company_id` | Many2one `res.company` | **required**, default = `self.env.company` |

- No computed fields, no overrides of `create`/`write`, no constraints, no methods.
  It is a plain data model.
- The `required=True` on `signature` is enforced both on the field **and** redundantly
  in the form view (`required="1"`); a delivery cannot be saved without a signature.

### 3.2 `uniform.type` (`models/uniform_type.py`)
`_name = 'uniform.type'` · `_description = 'Uniform Type'` · `_order = 'sequence'`.

| Field | Type | Notes |
|---|---|---|
| `name` | Char | uniform type label (note: **not** marked required) |
| `sequence` | Integer (default `10`) | manual ordering |

Simple master/lookup table referenced by `uniform.delivery.uniform_type_id`. Edited
inline via an `editable="bottom"` tree (see §5).

### 3.3 `hr.employee` (inherited — `models/hr_employee.py`)
`_inherit = 'hr.employee'`. Adds two **non-stored** computed integer counts and two
button actions used by the stat buttons on the employee form.

| Field | Type | Compute | Notes |
|---|---|---|---|
| `uniform_delivery_count` | Integer | `compute_uniform_delivery_count` | `search_count` of `uniform.delivery` where `employee_id == this employee` |
| `bulk_uniform_delivery_count` | Integer | `compute_bulk_uniform_delivery_count` | number of bulk deliveries (`employee_id == False`) whose `employee_ids` include this employee |

**Methods**
- `compute_uniform_delivery_count()` — counts individual deliveries for the employee
  via `search_count`.
- `compute_bulk_uniform_delivery_count()` — searches all bulk deliveries
  (`employee_id == False`) then `.filtered(lambda u: rec.id in u.employee_ids.ids)`
  and takes `len(...)`.
- `button_show_uniform_delivery()` — returns an `ir.actions.act_window` opening the
  individual deliveries tree for this employee
  (`domain = [('employee_id','=', self.id)]`, context `{'show_employee': True}`).
- `button_show_bulk_uniform_delivery()` — searches the bulk deliveries that include
  this employee and opens them in a tree (`domain = [('id','in', bulk.ids)]`,
  context `{'show_employees': True}`).

> **Performance gotcha:** `compute_bulk_uniform_delivery_count` loads **all** bulk
> `uniform.delivery` records into memory and Python-filters them on every recompute
> (both computes are non-stored, so they run on every form/list render that shows the
> field). Fine for small data volumes; if bulk-delivery counts grow large, convert to
> a stored/inverse or a domain-based `search_count` on `employee_ids`. Same `filtered`
> pattern is repeated in `button_show_bulk_uniform_delivery`.

---

## 4. Workflows

There is **no state machine**. The two operational flows are:

1. **Individual delivery** — open *Uniform Delivery → Uniform Delivery*, create a
   record, set `employee_id`, pick the `uniform_type_id`, capture the `signature`,
   save. The menu's action domain `[('employee_id','!=',False)]` keeps this list to
   individual records only.

2. **Bulk delivery** — open *Uniform Delivery → Bulk Uniform Delivery*, create a
   record, leave `employee_id` empty and fill `employee_ids` (many employees),
   capture one `signature`, save. The menu's action domain `[('employee_id','=',False)]`
   keeps this list to bulk records only.

3. **From an employee** — on the standard HR employee form, the two stat buttons
   ("Uniform Delivery" / "Bulk Uniform Delivery") show counts and drill into that
   employee's individual or bulk deliveries.

> **Data-integrity note:** nothing in code prevents creating a record with **both**
> `employee_id` and `employee_ids` set, or **neither**. The individual/bulk
> classification depends entirely on `employee_id` being set or not. A record with
> neither will not appear in the individual list and will appear in the bulk list
> (matching `employee_id == False`) but with no recipients.

---

## 5. Views & UI

All views live under `views/`. There are no kanban, search, pivot, graph or wizard
views — just form and tree.

### 5.1 `views/uniform_delivery.xml`
- **Form** (`uniform_delivery_view_form`): title = `name`; left group = `date`,
  `uniform_type_id`, `employee_id`; right group = `signature` (signature widget,
  `required="1"`) and `company_id`; below the groups, `employee_ids`.
  - `employee_id` is hidden when `context.get('show_employees')` is True (i.e. on the
    bulk action).
  - `employee_ids` is hidden when `context.get('show_employee')` is True (i.e. on the
    individual action).
  - `active` is rendered invisible (so the form still loads its value for archiving).
- **Tree** (`uniform_delivery_view_tree`): `sequence` (handle), `name`, `date`,
  `employee_id` (hidden when `show_employees`), `uniform_type_id`, `company_id`.
- **Actions**
  - `uniform_delivery_action` — "Uniform Delivery", `view_mode tree,form`,
    context `{'show_employee': True}`, domain `[('employee_id','!=',False)]`.
  - `bulk_uniform_delivery_action` — "Bulk Uniform Delivery", `view_mode tree,form`,
    context `{'show_employees': True}`, domain `[('employee_id','=',False)]`.
- **Menus**
  - `uniform_delivery_root` — top-level "Uniform Delivery" (sequence 60).
  - `uniform_delivery_menu` — child "Uniform Delivery" (sequence 1) → individual action.
  - `bulk_uniform_delivery_menu` — child "Bulk Uniform Delivery" (sequence 3) → bulk action.

> The context flag names are **easy to confuse**: `show_employee` (singular) is used
> by the *individual* action and **hides `employee_ids`**; `show_employees` (plural)
> is used by the *bulk* action and **hides `employee_id`**. Keep the singular/plural
> mapping straight when editing.

### 5.2 `views/uniform_type.xml`
- **Tree** (`uniform_type_view_tree`): `editable="bottom"`, `sequence` (handle),
  `name`. No separate form view (inline editing only).
- **Action** `uniform_type_action` — "Uniform Type", `view_mode tree`.
- **Menu** `uniform_type_menu` — child "Uniform Type" under the root (sequence 2).

### 5.3 `views/hr_employee.xml`
Inherits `hr.view_employee_form` and injects two `oe_stat_button`s into the standard
`button_box` (`fa-black-tie` icon, `statinfo` widget):
- "Uniform Delivery" → `button_show_uniform_delivery`, count `uniform_delivery_count`.
- "Bulk Uniform Delivery" → `button_show_bulk_uniform_delivery`, count
  `bulk_uniform_delivery_count`.

---

## 6. Reports
None. The module defines no QWeb/PDF reports.

## 7. Crons / automation
None. No `ir.cron`, no `mail.template`, no automated actions, no server actions.

## 8. Settings / config parameters
None. No `res.config.settings` inheritance and no `ir.config_parameter` usage.

## 9. Security (`security/ir.model.access.csv`)
Only an access CSV — **no** custom `groups.xml` and **no** record rules.

| ID | Model | Group | R | W | C | U |
|---|---|---|---|---|---|---|
| `access_uniform_delivery` | `uniform.delivery` | `base.group_user` | ✓ | ✓ | ✓ | ✓ |
| `access_uniform_type` | `uniform.type` | `base.group_user` | ✓ | ✓ | ✓ | ✓ |

- Every internal user (`base.group_user`) has full CRUD on both models.
- `hr.employee` access is inherited from the standard `hr` module — unchanged here.
- `company_id` exists on `uniform.delivery` but **no multi-company record rule** is
  defined, so records are not company-isolated unless a global rule from elsewhere
  applies. If multi-company isolation is needed, add a record rule.

## 10. Assets / JS
None custom. The `signature` field uses Odoo's built-in `signature` widget; no
SCSS/OWL/JS bundles are added by this module.

---

## 11. Gotchas & notes (read before debugging)
- **Single model, two flows by domain.** `uniform.delivery` is the only delivery
  model; "Bulk" vs individual is the `employee_id` set/unset domain split. Don't add a
  second model — extend behaviour by domain/context.
- **Context flag naming.** `show_employee` (singular, individual action) hides
  `employee_ids`; `show_employees` (plural, bulk action) hides `employee_id`. Mixing
  them up will show the wrong field in the wrong list.
- **No guard against mixed/empty recipients.** Code does not enforce that exactly one
  of `employee_id` / `employee_ids` is set. Consider a `@api.constrains` if data
  hygiene matters.
- **Non-stored counts recompute every render** and `compute_bulk_uniform_delivery_count`
  loads all bulk records into Python — acceptable at small scale, watch it as data grows.
- **Manifest placeholders** are still the scaffold defaults (`author`, `website`,
  `summary`, `description`). Update before any external distribution.
- **`uniform.type.name` is not required** — empty-named types are possible.
- **No reports/crons/settings/security groups** — if a handover checklist expects
  them, they genuinely do not exist in this module.

---

## 12. File map
```
__manifest__.py                  depends: base, hr  · data: access csv + 3 view files
__init__.py                      → models
models/
  __init__.py                    uniform_delivery · uniform_type · hr_employee
  uniform_delivery.py            uniform.delivery   (core record + signature)
  uniform_type.py                uniform.type       (simple master/lookup)
  hr_employee.py                 hr.employee inherit (2 stat buttons + counts)
security/
  ir.model.access.csv            full CRUD on both models for base.group_user
views/
  uniform_delivery.xml           form + tree + 2 actions + root/child menus
  uniform_type.xml               editable tree + action + menu
  hr_employee.xml                stat buttons on standard employee form
```
