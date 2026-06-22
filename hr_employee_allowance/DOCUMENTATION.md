# hr_employee_allowance — Developer Handover Documentation

> **HR Employee Allowance** — a small Odoo 17 add-on that lets HR record employee
> **allowance requests** (بدلات الموظفين). It defines a two-level allowance catalogue
> (Type → Package), an allowance-request record tied to an employee for a date period,
> and a **"Request Allowance"** button on the employee form. UI labels are English.
> This file is the single source of truth for handover — read it before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `hr_employee_allowance` |
| Display name | HR Employee Allowance |
| Version | `17.0` (manifest) |
| Odoo | 17.0 |
| License | Other proprietary |
| Category | Uncategorized |
| Depends | `hr` |
| External Python libs | **None** (only `odoo` core imports) |
| New models | `hr.allowance.type`, `hr.allowance.package`, `hr.allowance.request` |
| Inherited models | `hr.employee` (adds one action button) |
| Reports | **N/A** |
| Crons / automation | **N/A** |
| JS / OWL assets | **N/A** |

### Deployment (this server)
- DB: `odoo17` · service: `odoo-17.service` (systemd) · runs as user `odoo`.
- Python venv: `/home/odoo/.pyenv/versions/odoo-17-env/bin/python`
- Odoo bin: `/home/odoo/odoo-17.0+e.20241205/odoo-bin` · conf: `/home/odoo/odoo.conf`
- Addons path includes `/home/odoo/care` (this repo, branch `17`).
- **Update + restart:**
  ```bash
  sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
    /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
    -d odoo17 -u hr_employee_allowance --stop-after-init --no-http
  sudo systemctl restart odoo-17.service
  ```
- No dev mode. There are no JS/SCSS assets, so a module `-u` plus a restart is all that's
  needed after edits. Log file: `/var/log/odoo/odoo-17.log`.

---

## 2. Architecture overview

```
hr.allowance.type        (catalogue level 1 — e.g. "Housing", "Transport")
└── one2many → hr.allowance.package   (catalogue level 2 — variants/tiers of a type)

hr.allowance.request     (the actual request record)
├── many2one → hr.allowance.type      (required)
├── many2one → hr.allowance.package   (required; domain-filtered to the chosen type)
├── many2one → hr.employee            (required)
├── start_date / end_date            (the allowance period)
└── display_name (computed) = "<employee>-<type>-<package>"

hr.employee (inherited)
└── action_allowance_request()        → opens a pre-filled hr.allowance.request form

UI surfaces:
  • Tree / Form views for request and type
  • Menus under the HR app (Allowances + Configuration → Allowance Type)
  • "Request Allowance" button injected into the standard employee form header
```

**Design notes**
- This is a **lightweight CRUD module** — no workflow/state machine, no mail.thread, no
  computed analytics beyond `display_name`, no reports, no crons, no settings.
- The catalogue is two levels deep: a **Type** owns many **Packages**; a request picks one
  Type and one Package, with the Package field domain-restricted to the selected Type.

---

## 3. Data model

### 3.1 `hr.allowance.type` (`models/hr_allowance_type.py`)
Catalogue master — the top-level allowance category.

| Field | Type | Purpose |
|---|---|---|
| `name` | Char (required), label "Type" | the allowance type name |
| `package_ids` | One2many → `hr.allowance.package` (inverse `allowance_type_id`) | the packages/tiers under this type |

No computed fields, no methods. `_description = 'Hr Allowance Type'`.

### 3.2 `hr.allowance.package` (`models/hr_allowance_package.py`)
Catalogue detail — a package/variant belonging to one type.

| Field | Type | Purpose |
|---|---|---|
| `name` | Char (required), label "Package" | the package name |
| `allowance_type_id` | Many2one → `hr.allowance.type`, label "Type" | parent type (inverse of `package_ids`) |

No computed fields, no methods. `_description = 'Hr Allowance Package'`.

### 3.3 `hr.allowance.request` (`models/hr_allowance_request.py`)
The actual allowance request for an employee over a date range.

| Field | Type | Purpose |
|---|---|---|
| `allowance_type_id` | Many2one → `hr.allowance.type` (required), label "Allowance Type" | which type is requested |
| `allowance_package_id` | Many2one → `hr.allowance.package` (required), label "Allowance Package" | which package; **`domain="[('allowance_type_id','=',allowance_type_id)]"`** so only packages of the chosen type are selectable |
| `employee_id` | Many2one → `hr.employee` (required), label "Employee" | the requesting employee |
| `start_date` | Date (required), label "From" | start of the allowance period |
| `end_date` | Date (required), label "To" | end of the allowance period |

**Computed logic**
- `_compute_display_name()` — `@api.depends('employee_id', 'allowance_type_id',
  'allowance_package_id')`; sets `display_name` to
  `"<employee.name>-<allowance_type.name>-<allowance_package.name>"`. This overrides the
  standard `display_name` so request records read meaningfully in lists, m2o pickers and
  breadcrumbs. (Not stored — it's the conventional `display_name` override.)

No `state`, no workflow methods, no mail.thread.

### 3.4 `hr.employee` (inherited — `models/hr_employee.py`)
Adds **one method only** (no new fields):
- `action_allowance_request()` — returns an `ir.actions.act_window` that opens the
  `hr.allowance.request` **form** (view `hr_allowance_request_form_view`) with
  `context={'default_employee_id': self.id}`, i.e. a new request pre-filled with the
  current employee. Bound to the "Request Allowance" header button (see §4).

---

## 4. Views & menus

All views are plain backend QWeb (no kanban, no search customisation, no OWL).

### 4.1 `views/hr_allowance_request_views.xml`
- **Tree** (`hr_allowance_request_tree_view`): `employee_id`, `allowance_type_id`,
  `allowance_package_id`, `start_date`, `end_date`.
- **Form** (`hr_allowance_request_form_view`): employee, type, package, and a **period**
  row rendering `start_date`/`end_date` with the `daterange` widget
  (`related_start_date`/`related_end_date` options) and a right-arrow icon between them.
- **Action** (`hr_allowance_request_action`): "Allowance Requests", `view_mode tree,form`.
- **Menu** (`menu_hr_allowance_request`): under `hr.menu_hr_root` (the HR app root),
  `sequence=5`.

### 4.2 `views/hr_allowance_type_views.xml`
- **Tree** (`hr_allowance_type_tree_view`): `name`, `package_ids` (`many2many_tags`).
- **Form** (`hr_allowance_type_form_view`): `name` plus an "Allowance Package" notebook page
  with an inline (`editable="bottom"`) tree of `package_ids` (`name` only).
- **Action** (`hr_allowance_type_action`): "Allowance Type", `view_mode tree,form`.
- **Menu** (`menu_hr_allowance_type`): under
  `hr.menu_human_resources_configuration` (HR → Configuration), `sequence=5`.

### 4.3 `views/hr_employee_views.xml`
- `view_employee_form_inherit_hr_allowance` — inherits `hr.view_employee_form` and injects
  a **"Request Allowance"** button (`oe_stat_button`, `type="object"`,
  `name="action_allowance_request"`) **inside the employee form `//header`**.
  > Note: the button uses the `oe_stat_button` CSS class but is placed in the header (not in
  > the stat-button box), so it renders as a header action button.

### Wizards
**N/A** — there are no `TransientModel` wizards.

---

## 5. Reports
**N/A** — the module defines no QWeb-PDF or other reports.

## 6. Crons / automation
**N/A** — no `ir.cron` records, no scheduled actions, no server actions.

## 7. Settings / config_parameters
**N/A** — no `res.config.settings` inheritance and no `ir.config_parameter` usage.

---

## 8. Security (`security/`)

### 8.1 `hr_allowance_security.xml`
- `module_category_hr_employee_allowance` — module category "HR Employee Allowance".
- `group_hr_employee_allowance_manager` — group **"Administrator"** under that category;
  `implied_ids` includes `hr.group_hr_user` (so the manager is also an HR user), and the
  group is pre-assigned to `base.user_root` and `base.user_admin`.

### 8.2 `ir.model.access.csv`
| Model | Group | R | W | C | D |
|---|---|---|---|---|---|
| `hr.allowance.type` | `base.group_user` (all internal users) | ✓ | | | |
| `hr.allowance.package` | `base.group_user` | ✓ | | | |
| `hr.allowance.type` | `group_hr_employee_allowance_manager` | ✓ | ✓ | ✓ | ✓ |
| `hr.allowance.package` | `group_hr_employee_allowance_manager` | ✓ | ✓ | ✓ | ✓ |
| `hr.allowance.request` | `base.group_user` | ✓ | ✓ | ✓ | ✓ |

**Access model in plain terms:**
- Every internal user can **read** the allowance catalogue (Type/Package) but only the
  **Administrator** group can create/edit/delete it.
- Every internal user has **full CRUD on allowance requests** — there is no record rule
  scoping requests to their own employee record, so any internal user can see and edit all
  requests. Tighten this with a record rule if multi-tenant/privacy isolation is needed.

There are **no record rules** (`ir.rule`) defined in this module.

## 9. Assets / JS
**N/A** — no `static/` directory, no `assets` key in the manifest, no OWL components.

---

## 10. Gotchas & notes (read before changing)
- **`README.rst` is empty** (0 bytes) — there is no upstream description to rely on; this
  file is the documentation.
- **No workflow / no state** — a request is just a flat record. If you add an approval
  workflow, you'll be introducing `state`, mail.thread, and button methods from scratch.
- **Package domain depends on the type** — `allowance_package_id` is domain-filtered by
  `allowance_type_id`. If you set the package before/without the type via code or import,
  the domain won't protect you; validate the pair if you add server-side creation paths.
- **`display_name` is computed, not stored** — it concatenates three related names. If any
  of employee/type/package is unset it will render `False` in the string. Keep all three
  required (they currently are) or guard the compute before relying on it.
- **The "Request Allowance" button** sits in the employee form `//header` with the
  `oe_stat_button` class. If a future Odoo/theme change affects header button styling,
  check this placement.
- **Manager group is auto-assigned to root/admin** via `users` eval in the security XML —
  on `-u` this re-adds those users to the group; harmless but worth knowing.
- **No reports, crons, settings, or JS** — keep the module lean; don't add an `assets`
  bundle unless a real UI need arises.

---

## 11. File map
```
__manifest__.py                       depends=['hr']; loads security then views
README.rst                            (empty)
models/   hr_allowance_type.py        hr.allowance.type    (catalogue level 1)
          hr_allowance_package.py     hr.allowance.package (catalogue level 2)
          hr_allowance_request.py     hr.allowance.request (the request + display_name)
          hr_employee.py              hr.employee (inherit) — action_allowance_request()
security/ hr_allowance_security.xml   category + Administrator group
          ir.model.access.csv         ACLs (read for users, CRUD for manager / requests)
views/    hr_allowance_type_views.xml      tree/form/action/menu (Configuration)
          hr_allowance_request_views.xml   tree/form/action/menu (HR root)
          hr_employee_views.xml            employee-form header button
```
