# ent_hr_disciplinary_tracking — Developer Handover Documentation

> **Enterprise Open HRMS Disciplinary Tracking** — a Cybrosys / Open HRMS module for
> Odoo 17 that records **employee disciplinary actions**. Each record captures a
> disciplinary *reason*, the employee's *explanation* (with attachments) and the
> manager's *action*, and walks through a draft → explanation → action workflow on a
> `mail.thread` (chatter + activities). Reasons and actions are picked from a shared
> **category master** (`discipline.category`); each employee form shows a smart button
> with their validated-disciplinary count. UI is **English** (this is an upstream
> Cybrosys module, unmodified — no Arabic labels present). Read this before touching
> the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `ent_hr_disciplinary_tracking` |
| Display name | Enterprise Open HRMS Disciplinary Tracking |
| Version | `17.0.1.0.0` |
| Odoo | 17.0 (Enterprise — "ent" = OpenHRMS enterprise edition) |
| Category | Human Resources |
| Depends | `mail`, `hr` |
| External Python libs | **None** (stdlib only) |
| Author / License | Cybrosys Techno Solutions / Open HRMS · **OPL-1** (proprietary) |
| Models | `disciplinary.action` (central), `discipline.category` (master), `hr.employee` (inherited) |
| Reports | **N/A** (no QWeb/PDF reports) |
| Crons / mail templates | **N/A** |
| Settings / config params | **N/A** |
| Assets / JS | **N/A** (only `static/description/*` marketing assets) |

### Deployment (this server)
DB `odoo17` · systemd `odoo-17.service` · runs as user `odoo`. Update + restart:
```bash
sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
  /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
  -d odoo17 -u ent_hr_disciplinary_tracking --stop-after-init --no-http
sudo systemctl restart odoo-17.service
```
- Addons path includes `/home/odoo/care` (this repo, branch `17`). No dev mode.
- No external libraries to install; pure-Python module on top of `hr` + `mail`.
- Log file: `/var/log/odoo/odoo-17.log`.

> ⚠️ `data/demo_data.xml` is loaded **unconditionally** via the `data` key (not the
> `demo` key) — see Gotchas §9. Re-running `-u` will not duplicate it (records have
> XML ids), but it ships sample employees/categories/records into production.

---

## 2. Architecture overview

```
disciplinary.action  (central model — mail.thread + mail.activity.mixin)
├── many2one  employee_name      → hr.employee     (the disciplined employee)
├── many2one  department_name    → hr.department   (auto-filled from employee)
├── many2one  discipline_reason  → discipline.category  [domain category_type=disciplinary]
├── many2one  action             → discipline.category  [domain category_type=action]
├── many2many attachment_ids     → ir.attachment   (employee evidence)
└── state machine: draft → explain → submitted → action   (+ cancel)

discipline.category   (master list — reasons AND actions, split by category_type)

hr.employee (inherited)
└── discipline_count (computed)  → smart button → opens this employee's
                                    VALIDATED disciplinary records

Sequence: ir.sequence code 'disciplinary.action', prefix 'DIS', padding 3  (→ DIS001)
```

**Design notes**
- One central transactional model (`disciplinary.action`) + one master
  (`discipline.category`) that doubles as both the *reason* and the *action* picklist,
  discriminated by its `category_type` Selection (`disciplinary` / `action`). Both
  the reason and the action fields point at the **same** model with different
  `domain`s.
- The workflow is enforced purely in Python button methods + `ValidationError`
  guards; there are no QWeb reports, no crons, no settings, no JS.
- The `read_only` field is a per-user **permission flag computed from the current
  user's group** (manager vs. not) and used to gate field editability in the form.

---

## 3. Data model

### 3.1 `disciplinary.action` (central — `models/disciplinary_action.py`)
`_inherit = ['mail.thread', 'mail.activity.mixin']` · `_description = "Disciplinary Action"`
(no custom `_order` / `_rec_name`).

| Field | Type | Notes |
|---|---|---|
| `name` | Char | **Reference**, required, `readonly`, `copy=False`, default `_('New')`; overwritten on create by the `disciplinary.action` sequence (→ `DIS001`). |
| `state` | Selection | `draft` / `explain` (Waiting Explanation) / `submitted` (Waiting Action) / `action` (Action Validated) / `cancel`; default `draft`. Uses the legacy `track_visibility='onchange'` attr. |
| `employee_name` | Many2one `hr.employee` | the disciplined employee, required. |
| `department_name` | Many2one `hr.department` | required; auto-set from the employee in `onchange_employee_name`. |
| `discipline_reason` | Many2one `discipline.category` | **Reason**, required, form `domain=[('category_type','=','disciplinary')]`. |
| `explanation` | Text | employee's explanation of the violation. |
| `action` | Many2one `discipline.category` | the disciplinary **action** taken, form `domain=[('category_type','=','action')]`. |
| `action_details` | Text | free-text details, required before validation. |
| `read_only` | Boolean | **computed** (`get_user`), default `True` — `True` when current user is an HR manager; used to gate editing in the form. |
| `warning` | Boolean | default `False`; declared but unused in logic (invisible helper field in the form). |
| `attachment_ids` | Many2many `ir.attachment` | employee-supplied supporting documents. |
| `note` | Text | Internal Note. |
| `joined_date` | Date | employee joining date (manually entered / from demo). |

**Methods / workflow**
- `create(vals)` — overrides to stamp `name` from `ir.sequence` code
  `disciplinary.action`. *(Uses the old single-record `@api.model create(vals)`
  signature, not the v17 batch `create(vals_list)` — see Gotchas.)*
- `get_user()` (`@api.depends('read_only')`) — sets `read_only = True` if the user is
  in `hr.group_hr_manager`, else `False`. (Self-depends; effectively recomputes per
  user/record load.)
- `onchange_employee_name()` — looks up the employee by name and copies their
  `department_id` into `department_name`; raises if the record is already validated
  (`state == 'action'`).
- `onchange_reason()` — blocks changing the reason once validated.
- **Workflow buttons (state transitions):**
  | Button method | From → To | Guard |
  |---|---|---|
  | `assign_function()` | draft → **explain** | — ("Proceed") |
  | `explanation_function()` | explain → **submitted** | requires `explanation` ("Submit") |
  | `action_function()` | submitted → **action** | requires `action` **and** non-empty `action_details` (rejects `<p><br></p>`) ("Validate Action") |
  | `cancel_function()` | draft/submitted → **cancel** | — ("Cancel") |
  | `set_to_function()` | cancel → **draft** | — ("Set to Draft") |

### 3.2 `discipline.category` (master — `models/discipline_category.py`)
`_description = 'Reason Category'`. A flat master list used for **both** reasons and
actions, split by `category_type`.

| Field | Type | Notes |
|---|---|---|
| `code` | Char | required — category code (e.g. `VIOLATION`, `WRITTEN`). |
| `name` | Char | required — display name. |
| `category_type` | Selection | `disciplinary` (Disciplinary Category) / `action` (Action Category). Drives the two form domains on `disciplinary.action`. |
| `description` | Text | details for this category. |

No methods. Seeded with reasons and actions from `data/demo_data.xml` (§7).

### 3.3 `hr.employee` (inherited — `models/hr_employee.py`)
| Field | Type | Notes |
|---|---|---|
| `discipline_count` | Integer (computed `_compute_discipline_count`, **not stored**) | count of this employee's disciplinary records in state `action` only. |

`_compute_discipline_count()` uses `read_group` over `disciplinary.action` filtered to
`state == 'action'`, grouped by `employee_name`, reading the
`employee_name_count` aggregate into a `{employee_id: count}` map. Backs the smart
button on the employee form.

> ⚠️ The compute reads the legacy `employee_name_count` key from `read_group`. On some
> v17 builds `read_group` returns `__count` instead — if the smart button always shows
> 0, this is the line to check (the sibling `care_hr` dashboard handles this with a
> `__count` fallback; this upstream module does not).

---

## 4. Views (`views/*.xml`)

### 4.1 `disciplinary_action_views.xml`
- **Search** (`employee_disciplinary_view_search`): search by `employee_name`,
  `department_name`, `joined_date`, `discipline_reason`; filters per state (Draft /
  Waiting Explanation / Waiting Action / Action Validated / Cancel); group-by State /
  Department / Joined Date.
- **Tree** (`employee_disciplinary_view_tree`): `name`, `employee_name`
  (`groups="hr.group_hr_manager"` — hidden from non-managers), `state`.
- **Form** (`employee_disciplinary_view_form`): header workflow buttons (mapped to the
  methods in §3.1, each `invisible` per state; Validate/Cancel/Set-to-Draft restricted
  to `hr.group_hr_manager`), statusbar `draft,explain,action`. Sheet shows the
  reference, employee, department (manager-only), `joined_date`, and a notebook with
  two pages:
  - **Disciplinary Information** — `discipline_reason` (domain disciplinary),
    `explanation` + `attachment_ids` (`many2many_binary`, both hidden in `draft`),
    `note`.
  - **Action Information** — visible only in `submitted`/`action`; `action` (domain
    action, manager-only) and `action_details` (manager-only, shown once an action is
    chosen). Editability gated by `read_only`/`state`.
  - Chatter (`message_follower_ids`, `activity_ids`, `message_ids`).
- **Window actions:**
  - `action_disciplinary_action` — **"Disciplinary Action"**, `tree,form`, domain over
    all five states. Bound to the menu.
  - `disciplinary_action_details` — **"Disciplinary Actions"**, filtered to
    `state == 'action'` **and** `employee_name.id == active_id`; opened by the employee
    smart button (passes the employee as `active_id`).
  - `disciplinary_action_details_view` — **"Disciplinary Action Details"**, domain
    `state != 'draft'`. (Defined but **not** referenced by any menu/button in this
    module — see Gotchas.)
- **`hr.employee` form inherit** (`view_employee_form`): injects the smart button into
  `button_box` — `discipline_count` (`statinfo`, `fa-info-circle`) opening
  `disciplinary_action_details`.
- **Menus:** root `disciplinary_action` ("Disciplinary Actions") under `hr.menu_hr_root`
  (seq 23) → child `disciplinary_action_create` → `action_disciplinary_action`.

### 4.2 `discipline_category_views.xml`
Search / Tree / Form for `discipline.category` (form: `name`, `code`, `category_type`,
`description`). Action `action_disciplinary_category_view`. Menu
`disciplinary_category_view` ("Discipline Category", **manager-only**) under the
disciplinary root, seq 3.

### Wizards
**N/A** — no `wizards/` directory, no `TransientModel`.

---

## 5. Reports
**N/A** — no `reports/` directory, no QWeb-PDF templates, no report records.

## 6. Crons / automation / mail templates
**N/A** — no `ir.cron`, no `mail.template`. (The model is a `mail.thread`, so it gets
standard chatter/activity tracking via the mixin, but no module-defined automation.)

## 7. Data (`data/demo_data.xml`)
Loaded via the manifest **`data`** key (always, not demo-gated). Contains:
- The **sequence** `seq_disciplinary_action` (code `disciplinary.action`, prefix `DIS`,
  padding 3) — required for `create()` to work.
- **Disciplinary reason categories**: Violation of Company Rules, Mis-behaviour to
  Co-workers, Damage to company properties, Not Follow Management Instructions, Work
  Performance Issues.
- **Action categories**: No Action, Verbal Warning, Written Warning, Meet the Manager,
  Suspend the Employee (one week), Terminate the Employee.
- **Sample data**: a `Marketing` department, a `Jack Mark Rose` employee, and one
  example `disciplinary.action` record.

> The sequence is the only **functionally required** record here; everything else is
> sample/seed data (see Gotchas §9).

## 8. Settings / config parameters
**N/A** — no `res.config.settings` inherit, no `ir.config_parameter` usage.

---

## 9. Security (`security/`)

### `ir.model.access.csv`
| ACL | Model | Group | R / W / C / U |
|---|---|---|---|
| `view_disciplinary_action` | `disciplinary.action` | `hr.group_hr_manager` | 1/1/1/1 |
| `view_disciplinary_action_user` | `disciplinary.action` | `base.group_user` | 1/1/0/0 |
| `view_disciplinary_action` *(dup id)* | `disciplinary.action` | `hr.group_hr_user` | 1/1/1/1 |
| `view_discipline_category` | `discipline.category` | `hr.group_hr_manager` | 1/1/1/1 |

> ⚠️ **Duplicate ACL id `view_disciplinary_action`** appears on lines 2 and 5 with
> different groups. On load the second (`hr.group_hr_user`, full CRUD) **overwrites**
> the first record's `xmlid` — net effect: HR users get full CRUD, the
> `hr.group_hr_manager` row from line 2 is effectively replaced. Base users
> (`base.group_user`) get read/write but not create/unlink. `discipline.category` has
> **no** ACL for plain users — only managers can read the category master.

### `security.xml` (record rules)
- `disciplinary_action_employee` (group `base.group_user`): domain
  `[('employee_name.user_id.id','=',user.id)]` — ordinary users see **only their own**
  disciplinary records.
- `disciplinary_action_manager` (group `hr.group_hr_manager`): domain `[]` — managers
  see **all**.

---

## 10. Assets / JS
**N/A** — no `web.assets_*` bundles. The `static/description/` tree (banner, icon,
`index.html`, screenshots, marketing icons) is **App-Store listing material only**,
not loaded by Odoo at runtime. `static/description/images/employee_image.jpg` is
referenced by the demo employee record.

---

## 11. Gotchas & notes (read before debugging)

- **Demo data ships to production.** `demo_data.xml` is under the manifest **`data`**
  key, so it installs on every DB (sample employee "Jack Mark Rose", a Marketing
  department, and a sample disciplinary record), not only demo DBs. If you don't want
  the samples, move it to the `demo` key or strip the sample records — but **keep the
  `ir.sequence`**, which `create()` depends on.
- **Sequence is mandatory.** `create()` calls
  `next_by_code('disciplinary.action')`; if `seq_disciplinary_action` is missing,
  `name` becomes `False` and creation breaks. Don't delete it.
- **Legacy `create(vals)` signature.** The override uses the single-dict
  `@api.model create(vals)` form, not v17's batched `create(vals_list)`. It still works
  via ORM back-compat but only stamps the sequence on the first record of a multi-create
  and may warn — convert to `@api.model_create_multi` if you touch it.
- **`track_visibility='onchange'`** on `state` is the **deprecated v13-era** attribute
  (replaced by `tracking=True` in modern Odoo). It is silently ignored in v17 — state
  changes may not appear in the chatter. Change to `tracking=True` if you need state
  tracking.
- **Duplicate ACL id** (`view_disciplinary_action`) — see §9; the second row wins.
  Don't assume the first (manager) row is in effect.
- **`onchange_employee_name` matches by name, not id.** It does
  `search([('name','=', self.employee_name.name)])` to find the department — fragile
  with duplicate employee names (picks the first match). Prefer
  `self.employee_name.department_id` directly.
- **`read_only` is a permission flag, not a lock.** It is computed from the user's
  group and only drives `readonly=` attrs in the form; it does not enforce anything at
  the ORM level. Real enforcement is the record rules + ACLs in §9.
- **`disciplinary_action_details_view` action is orphaned** — defined but referenced by
  nothing in this module. Safe to ignore or wire up.
- **Smart-button count may read 0** on builds where `read_group` returns `__count`
  rather than `employee_name_count` (see §3.3).
- **No `_order`** — list ordering falls back to `id`. The default action shows all
  states; use the search filters to scope.

---

## 12. File map
```
__manifest__.py                  depends (mail, hr); data list; OPL-1
data/        demo_data.xml        sequence + reason/action categories + sample records
models/      disciplinary_action.py   (central model + workflow)
             discipline_category.py    (reason/action master)
             hr_employee.py            (discipline_count smart-button compute)
security/    ir.model.access.csv  (4 ACL rows — note duplicate id)
             security.xml          (2 record rules: own vs. all)
views/       disciplinary_action_views.xml   (search/tree/form/actions/menus + employee inherit)
             discipline_category_views.xml   (search/tree/form/action/menu)
i18n/        ar_001.po             (Arabic translations of UI strings)
doc/         RELEASE_NOTES.md      (v17.0.1.0.0 initial commit)
README.rst
static/description/   banner/icon/index.html/screenshots   (App-Store listing only)
```

> **N/A sections for this module:** Reports (§5), Crons/automation/mail templates (§6),
> Settings/config parameters (§8), Assets/JS (§10), Wizards (§4). The module is a small,
> self-contained HR add-on: two new models, one inherited model, views, security, and
> seed data — no external services, no background jobs, no client-side code.
