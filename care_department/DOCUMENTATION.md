# care_department — Developer Handover Documentation

> **Care Department** turns the standard Odoo `hr.department` record into a lightweight
> **"department / project hub"** for the client. It extends `hr.department` with a logo,
> a project link, an attachments tab, a per-department user allow-list (record visibility),
> Shift-Approver settings, and a row of **stat buttons** that count and drill into the
> department's Employees, Vehicles, Tasks, Purchase Orders, Sale Orders, Attendances,
> Letters, Time Off, Shifts and Applicants. It also adds a `department_id` field to
> `fleet.vehicle` so vehicles can belong to a department. UI labels are English; the data
> is the client's Kuwait HR setup. Read this before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `care_department` |
| Display name | Care Department |
| Version | `0.1` (manifest) — runs on Odoo 17 |
| Author / website | "My Company" / placeholder (manifest never customised) |
| Category | Uncategorized |
| Depends | `base`, `hr`, `care_sale`, `purchase`, `fleet`, `project`, `hr_attendance`, `hr_recruitment`, `hr_employee_shift`, `sp_letter_v15`, `hr_holidays`, `purchase_report`, `care_attendance` |
| External Python libs | none |
| Inherited models | `hr.department`, `fleet.vehicle` |
| New models | none (this module only extends existing ones) |
| Reports / Crons / JS | none |
| Data files loaded | `views/hr_department.xml`, `views/fleet_vehicle.xml` |

> ⚠️ **`security/ir.model.access.csv` is NOT loaded** — it is commented out in the manifest
> `data` list and the file is just a header row with no rows. No new access rules ship with
> this module; it relies entirely on the access rules of `hr`/`fleet`/etc. See §9.

### Deployment (this server)
DB `odoo17` · systemd `odoo-17.service` · user `odoo`. Update + restart:
```bash
/home/odoo/.pyenv/versions/odoo-17-env/bin/python \
  /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
  -d odoo17 -u care_department --stop-after-init --no-http
sudo systemctl restart odoo-17.service
```
- Run as the `odoo` user (e.g. `sudo -u odoo …`). Addons path includes `/home/odoo/care`
  (this repo, branch `17`). Conf: `/home/odoo/odoo.conf`. Log: `/var/log/odoo/odoo-17.log`.
- No dev mode. After editing the XML views, a module `-u` reloads the view definitions; a
  restart serves them.
- **Heavy dependency chain** — this module depends on 13 modules including several custom
  ones (`care_sale`, `hr_employee_shift`, `sp_letter_v15`, `purchase_report`,
  `care_attendance`). If any of those fail to load, `care_department` will not update. Update
  the dependencies first if they changed.

---

## 2. Architecture overview

This module adds **no new models**. It enriches two existing models and bolts a
project/department dashboard onto the standard department form.

```
hr.department  (inherited — models/hr_department.py)
│
├── self-reference     department_id  → hr.department         (a "parent project/department" link, company-scoped)
├── project link       project_id     → project.project       (+ dates, amount, period, estimated months)
│
├── visibility         allowed_user_ids → res.users           (drives the kanban action domain)
│                       has_higher_manager / higher_manager_access / is_modifier (gates)
│
├── presentation       logo (Binary)  ·  attachment_ids → ir.attachment (M2m)
│
└── stat buttons (10 computed counts, each with a button_show_* drill-down action):
        employee_count   → hr.employee            (department_id = self)
        vehicle_count    → fleet.vehicle          (department_id = self)        ← new field, see below
        task_count       → project.task           (project_id = self.project_id)
        purchase_order_count → purchase.order      (department_id = self)
        sale_order_count → sale.order             (department_id = self)
        attendance_count → bulk.attendance         (self in department_ids)      ← from care_attendance
        letter_count     → letter.file            (department_id = self)         ← from sp_letter_v15
        leave_count      → hr.leave               (employee_id.department_id = self)
        shift_count      → employee.shift.request  (current_/new_department = self) ← from hr_employee_shift
        applicant_count  → hr.applicant           (department_id = self)

fleet.vehicle  (inherited — models/fleet_vehicle.py)
└── department_id → hr.department   (so a vehicle belongs to a department)

UI:
  • hr.department FORM  — fully re-laid-out: logo + title, Shift Approvers / Options /
                          Attachments / Project tabs, stat-button box (dashboard-only)
  • hr.department KANBAN — adds the logo image
  • "Care Projects" act_window + menu — kanban of departments the current user may see
  • fleet.vehicle FORM  — adds department_id after manager_id
```

**Design notes**
- Several fields referenced in the view (`employee_shift_approval_1/2/3`,
  `old_manager_approval`, `new_manager_approval`, `working_hours_modifier`) are **NOT** defined
  in this module — they come from the `hr_employee_shift` dependency. This module only adds the
  *Shift Approvers* page that surfaces them.
- The stat-button box only appears when the form is opened **with context
  `{'dashboard_view': True}`** — i.e. from the module's own "Care Projects" action, not from
  the standard HR → Departments menu.
- `show_*` booleans (10 of them, default `True`) let a manager hide individual stat buttons per
  department.

---

## 3. Data model

### 3.1 `hr.department` (inherited — `models/hr_department.py`)

**Links & project block**

| Field | Type | Notes |
|---|---|---|
| `department_id` | M2o `hr.department` (label "Department") | self-reference, domain limits to same/no company |
| `logo` | Binary | shown as avatar on form + image on kanban |
| `attachment_ids` | M2m `ir.attachment` | Attachments tab (`many2many_binary` widget) |
| `project_id` | M2o `project.project` | the department's project (drives `task_count`) |
| `project_start_date` / `project_end_date` | Date | project window |
| `project_amount` | Float | project value |
| `project_social_file` | M2o `hr.social.contracts` | social-insurance file link |
| `project_period` | Float | project period |
| `project_estimated_months` | Float (computed `compute_project_estimated_months`, **stored**) | months between start & end dates |

**Visibility / permission gates**

| Field | Type | Notes |
|---|---|---|
| `allowed_user_ids` | M2m `res.users` | users allowed to see this department; **drives the "Care Projects" action domain** |
| `has_higher_manager` | Boolean (computed `compute_has_higher_manager`, **stored**, depends `manager_id`) | true when the manager has a parent manager |
| `higher_manager_access` | Boolean | grant the manager's parent access (only editable by a "modifier") |
| `is_modifier` | Boolean (computed `compute_is_modifier`, **not stored**) | true for ERP-manager / system-admin users; gates `readonly`/`invisible` on most fields |

**Stat-button counts** (all computed, **not stored** — recomputed on each read)

`employee_count`, `vehicle_count`, `task_count`, `purchase_order_count`, `sale_order_count`,
`attendance_count`, `letter_count`, `leave_count`, `shift_count`, `applicant_count`.

**Stat-button visibility toggles** (Boolean, default `True`)

`show_employees`, `show_vehicles`, `show_tasks`, `show_purchase_orders`, `show_sale_orders`,
`show_attendances`, `show_letters`, `show_leaves` (label "Show Time Off"), `show_shifts`,
`show_applicants`.

**Methods**

| Method | Purpose |
|---|---|
| `compute_is_modifier` | sets `is_modifier=True` if the user is in `base.group_erp_manager` or `base.group_system` |
| `compute_has_higher_manager` | `@api.depends('manager_id')` → `bool(manager_id.parent_id)` |
| `compute_allowed_user_ids` | **`@api.onchange('manager_id','higher_manager_access')`** — rebuilds `allowed_user_ids` = all ERP-managers + all system users + the manager's user + (if `higher_manager_access`) the parent manager's user. Note: this is an **onchange**, so it only fires while editing the form, not on background writes. |
| `compute_project_estimated_months` | `@api.depends('project_start_date','project_end_date')` — month delta between the two dates |
| `compute_<x>_count` | one per stat button — `search_count` on the target model (see table below) |
| `button_show_<x>` | one per stat button — returns an `ir.actions.act_window` filtered to this department |

**Count / drill-down mapping** (source model and domain for each stat button)

| Count field / button | Target model | Domain |
|---|---|---|
| `employee_count` / `button_show_employees` | `hr.employee` | `department_id = self` (kanban,tree) |
| `vehicle_count` / `button_show_vehicles` | `fleet.vehicle` | `department_id = self` (kanban,tree) |
| `task_count` / `button_show_tasks` | `project.task` | `project_id = self.project_id` (kanban,tree) |
| `purchase_order_count` / `button_show_purchase_orders` | `purchase.order` | `department_id = self` (tree,kanban). **Count is gated by `show_purchase_orders`** (returns 0 when hidden) |
| `sale_order_count` / `button_show_sale_orders` | `sale.order` | `department_id = self` (tree) |
| `attendance_count` / `button_show_attendances` | `bulk.attendance` | `self.id in a.department_ids` — **computed in Python via `.filtered()`, not a search domain** (tree) |
| `letter_count` / `button_show_letters` | `letter.file` | `department_id = self` (kanban,tree) |
| `leave_count` / `button_show_leaves` | `hr.leave` | `employee_id.department_id = self` (tree) |
| `shift_count` / `button_show_shifts` | `employee.shift.request` | `current_department = self OR new_department = self` (tree) |
| `applicant_count` / `button_show_applicants` | `hr.applicant` | `department_id = self` (tree) |

> Several of these target models / fields are provided by dependencies, not core Odoo:
> `bulk.attendance` (+ `department_ids`) from **`care_attendance`**, `letter.file`
> (+ `department_id`) from **`sp_letter_v15`**, `employee.shift.request`
> (+ `current_department`/`new_department`) from **`hr_employee_shift`**, `hr.social.contracts`,
> and the `department_id` on `purchase.order`/`sale.order` (custom). If a dependency is removed,
> the matching compute will raise.

### 3.2 `fleet.vehicle` (inherited — `models/fleet_vehicle.py`)
Adds a single field:

| Field | Type | Notes |
|---|---|---|
| `department_id` | M2o `hr.department` | which department owns the vehicle; back-references `vehicle_count` above |

Surfaced on the fleet form (see §4.3).

---

## 4. Views (`views/*.xml`)

### 4.1 `hr.department` form — `care_view_department_form`
Inherits `hr.view_department_form` and **heavily re-lays-out** the standard form:

- **Stat-button box** (`button_box`) is *replaced* and made `invisible="not context.get('dashboard_view', False)"` — so it shows only via the module's own action. 10 `oe_stat_button`s, each `invisible="not show_<x>"` and bound to its `button_show_<x>` method with a `statinfo` count.
- The default `name` field is removed and re-rendered as a title block with the **`logo`** image avatar and a "Department Name" header.
- After `parent_id`: adds `project_id`, hidden `has_higher_manager` & `is_modifier`, and `higher_manager_access` (`readonly="not is_modifier"`).
- The second group is replaced by a **notebook** with four pages:
  - **Shift Approvers** — `employee_shift_approval_1/2/3` (readonly unless modifier), `old_manager_approval`, `new_manager_approval`, `working_hours_modifier`. *(All these fields come from `hr_employee_shift`, not this module.)*
  - **Options** (`invisible="not is_modifier"`) — the 10 `show_*` toggles + `allowed_user_ids` (`many2many_tags`).
  - **Attachments** (`readonly="not is_modifier"`) — `attachment_ids` (`many2many_binary`).
  - **Project** — the project block fields (start/end/amount/social file/period/estimated months), each `readonly="not is_modifier"`.

### 4.2 `hr.department` kanban — `care_hr_department_view_kanban`
Inherits `hr.hr_department_view_kanban`; injects the **`logo`** image (`options="{'size':[0,90]}"`) after the card header title.

### 4.3 `fleet.vehicle` form — `care_fleet_vehicle_view_form`
Inherits `fleet.fleet_vehicle_view_form`; adds `department_id` right after `manager_id`.

### 4.4 Action + menu — "Care Projects"
- `care_hr_department_kanban_action` (`ir.actions.act_window`, model `hr.department`,
  `view_mode = kanban,tree,form`) with:
  - **`context = {'dashboard_view': True}`** → this is what makes the stat buttons appear.
  - **`domain = [('allowed_user_ids', 'in', [uid])]`** → users only see departments where they
    are in `allowed_user_ids` (so building that list correctly is essential — see Gotchas).
  - reuses `hr.view_department_filter` as the search view.
- `care_menu_hr_department_kanban` menu item ("Care Projects"), `groups="hr.group_hr_user"`.

No wizards, no list/search views of its own beyond the inherited ones.

---

## 5. Reports
None. This module ships no QWeb/PDF reports.

## 6. Crons / automation
None. No `ir.cron`, no scheduled actions, no mail templates.

## 7. Settings / config parameters
None. No `res.config.settings` extension and no `ir.config_parameter` usage.

## 8. Assets / JS
None. No `static/` directory, no OWL components, no SCSS/JS.

---

## 9. Security
- **`security/ir.model.access.csv` exists but is empty** (header row only) **and is commented
  out** of the manifest `data` list — so it is not loaded. This module declares **no** access
  rules, groups, or record rules of its own.
- Access to the new/extended data therefore inherits from the base modules:
  - `hr.department` / `fleet.vehicle` use the standard `hr` / `fleet` access rules.
  - The new fields are visible/editable to whoever can already edit those records, further gated
    in the **view** by `is_modifier` (ERP-manager / system) `readonly`/`invisible` expressions —
    this is **UI-level gating only, not ORM security**.
- The "Care Projects" **menu** is restricted to `hr.group_hr_user`; the **action domain**
  (`allowed_user_ids in [uid]`) is the practical visibility filter for which departments a user
  sees in that dashboard.

---

## 10. Gotchas & notes (read before debugging)

- **Stat buttons missing?** They are `invisible` unless the form is opened with context
  `{'dashboard_view': True}`. Only the "Care Projects" action sets that context — the standard
  HR → Departments form will *not* show them. This is intentional.
- **`allowed_user_ids` is populated by an `@api.onchange`**, not a stored compute or `create`/
  `write` override. It only refills while a user edits the form (on `manager_id` /
  `higher_manager_access` change). Departments created/imported in the background will have an
  **empty** `allowed_user_ids` and therefore be **invisible in the "Care Projects" dashboard**
  until someone re-saves the form. If users report "I can't see my department," check this.
- **Empty / unloaded security CSV** — do not assume this module adds permissions. If you need
  per-department ORM security, you must add it (and uncomment the manifest line).
- **Manifest is the scaffold default** — `name`/`summary`/`description`/`author`/`website`/
  `category` were never customised. Cosmetic, but worth tidying on handover.
- **Cross-module field/model coupling** — many counts target models and fields owned by
  dependencies (`bulk.attendance`, `letter.file`, `employee.shift.request`, `hr.social.contracts`,
  custom `department_id` on purchase/sale orders, and the Shift-Approver fields). The module will
  not update if those deps are broken, and a compute will raise at runtime if a target field is
  removed. Keep the dependency chain healthy.
- **`attendance_count` is O(n)** — it loads *all* `bulk.attendance` records and `.filtered()`s
  them in Python (the M2m `department_ids` isn't queried with a domain). Fine for small data;
  watch it if attendance volume grows.
- **`purchase_order_count`** is the only count gated by its `show_*` toggle (returns 0 when
  `show_purchase_orders` is off); the others always compute regardless of their toggle (the toggle
  only hides the button in the view).
- **Count fields are non-stored computes** — they recompute on every department read; no
  invalidation/storage. Acceptable here, but they can't be searched/grouped on.

---

## 11. File map
```
__manifest__.py                 depends (13 modules) · data (2 view files) · security CSV commented out
__init__.py                     → models
models/
  __init__.py                   imports hr_department, fleet_vehicle
  hr_department.py              inherits hr.department: project block, allowed_user_ids,
                                logo/attachments, 10 stat-button counts + button_show_* actions
  fleet_vehicle.py              inherits fleet.vehicle: adds department_id
security/
  ir.model.access.csv           header only — EMPTY and NOT loaded (commented out in manifest)
views/
  hr_department.xml             form (relaid-out + stat box), kanban (logo),
                                "Care Projects" act_window + menu
  fleet_vehicle.xml             adds department_id to the fleet form
```
