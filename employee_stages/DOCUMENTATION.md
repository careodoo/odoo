# employee_stages — Developer Handover Documentation

> Third‑party **Cybrosys** community module that adds an **employee life‑cycle stage**
> field (Slap On → Grounding → Test Period → Employment → Notice Period → Resigned /
> Terminated) to `hr.employee`, with button‑driven transitions and a **stage‑history log**
> (each stage's start/end date + duration). UI labels are English. This is a small,
> self‑contained inherit‑only module — read this before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `employee_stages` |
| Display name | Employee Stages |
| Version | `17.0.1.0.0` |
| Odoo | 17.0 |
| Category | Human Resources |
| Depends | `hr` |
| External Python libs | **None** (stdlib only) |
| Author / maintainer | Cybrosys Techno Solutions |
| License | LGPL‑3 |
| New model | `hr.employee.status.history` |
| Inherited models | `hr.employee`, `hr.employee.public` |
| Wizard | `employee.stage` (TransientModel) |
| Reports / Crons / JS assets | **None** (N/A) |

### Deployment (this server)
- DB: `odoo17` · service: `odoo-17.service` (systemd) · runs as user `odoo`.
- Python venv: `/home/odoo/.pyenv/versions/odoo-17-env/bin/python`
- Odoo bin: `/home/odoo/odoo-17.0+e.20241205/odoo-bin` · conf: `/home/odoo/odoo.conf`
- **Update + restart:**
  ```bash
  sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
    /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
    -d odoo17 -u employee_stages --stop-after-init --no-http
  sudo systemctl restart odoo-17.service
  ```
- No dev mode. This module ships only Python + XML (no JS/SCSS assets), so a module `-u`
  plus a restart is all that is needed after edits. Log file: `/var/log/odoo/odoo-17.log`.

---

## 2. Architecture overview

```
hr.employee  (inherited)
├── state                 Selection — current stage (7 values), default 'joined'
├── stages_history_ids    one2many → hr.employee.status.history
└── stage transition buttons (form header):
       action_start_grounding · action_start_test_period · Set as Employee (wizard)
       action_start_notice_period · action_relived · action_terminate
                    │
                    ▼  (each button creates / closes a history row)
hr.employee.status.history  (new model — one row per stage occurrence)
├── employee_id (m2o hr.employee)   start_date   end_date
├── state (same 7-value Selection)  duration (computed = end − start, days)

hr.employee.public  (inherited)
└── state  — related (read-only) to employee_id.state, so the stage is
             visible/searchable in public-employee contexts

employee.stage  (TransientModel — wizard)
└── related_user_id (m2o res.users) → optionally links a portal/internal user
    when promoting to Employment, then delegates to employee.set_as_employee()
```

**Design notes**
- The whole module is **inherit‑only** plus one small detail model and one wizard. There is
  no central new business object — it bolts a state machine onto the standard employee.
- Every stage transition is a **Python button method** on `hr.employee` that does two
  things: (1) set the new `state`, and (2) write the history log — close the previous
  stage's row (`end_date`) and `create()` a new open row (`start_date`).
- **Two transitions archive the employee** (`active = False`): `action_relived`
  (Resigned) and `action_terminate` (Terminated).

---

## 3. Data model

### 3.1 `hr.employee` (inherited — `models/hr_employee.py`)

| Field | Type | Notes |
|---|---|---|
| `state` | Selection | The employee's current stage. 7 values (see below). `default='joined'`, `copy=False`, `track_visibility='always'`. |
| `stages_history_ids` | One2many → `hr.employee.status.history` (`employee_id`) | The full stage history log for this employee. |

**`state` Selection values (key → label):**

| Key | Label | Notes |
|---|---|---|
| `joined` | **Slap On** | = Joined. Default on create. |
| `grounding` | **Grounding** | = Training. |
| `test_period` | **Test Period** | = Probation. |
| `employment` | **Employment** | The "active employee" state. |
| `notice_period` | **Notice Period** | |
| `relieved` | **Resigned** | Archives the employee (`active=False`). |
| `terminate` | **Terminated** | Archives the employee (`active=False`). |

> The field `help` text documents the aliases: *"Slap On: Joined / Grounding: Training /
> Test period: Probation"*.

**Methods / workflow** (all on `hr.employee`):

- **`create(vals_list)`** (`@api.model_create_multi`) — after the standard create, seeds the
  first history row: `{start_date: today, state: 'joined'}`. So every new employee starts in
  **Slap On** with an open history entry. *(Uses `.stages_history_ids.sudo().create(...)`.)*
- **`action_start_grounding()`** — `state='grounding'`; creates a new history row
  (start=today, state=grounding). **Note:** does *not* close the prior `joined` row's
  `end_date` (see Gotchas).
- **`action_start_test_period()`** — `state='test_period'`; closes the `grounding` history
  row (`end_date=today`) and creates a `test_period` row.
- **`set_as_employee()`** — `state='employment'`; closes the `test_period` row
  (`end_date=today`) and creates an `employment` row. Invoked via the **wizard** (see 3.4),
  which may also set `user_id` first.
- **`action_start_notice_period()`** — `state='notice_period'`; closes the `employment`
  row and creates a `notice_period` row.
- **`action_relived()`** — `state='relieved'`, **`active=False`**; closes the
  `notice_period` row and creates a `relieved` row (created with `end_date=today`, no
  `start_date`).
- **`action_terminate()`** — `state='terminate'`, **`active=False`**; closes the
  `employment` row if present, **else** closes the `grounding` row; creates a `terminate`
  row (with `end_date=today`, no `start_date`). This is the early‑exit path from
  Grounding/Employment.

**Typical happy‑path flow:**
```
joined ──Start Grounding──▶ grounding ──Start Test Period──▶ test_period
   └──────────── Set as Employee (wizard) ────────────────────────┘
                              ▼
employment ──Start Notice Period──▶ notice_period ──Relieved──▶ relieved (archived)

Early exit:  grounding | employment ──Terminate──▶ terminate (archived)
Shortcut:    joined | test_period  ──Set as Employee──▶ employment
```

### 3.2 `hr.employee.status.history` (new — `models/hr_employee.py`)
`_name = 'hr.employee.status.history'` · `_description = 'Status History'`

| Field | Type | Notes |
|---|---|---|
| `employee_id` | Many2one → `hr.employee` | Owner of the history row. `invisible=1`. |
| `state` | Selection (same 7 values) | Which stage this row records. |
| `start_date` | Date | Stage start. |
| `end_date` | Date | Stage end (set when the next transition fires). |
| `duration` | Integer (computed, **not stored**) | `_compute_get_duration` — `end_date − start_date` in days (0 if either date missing). |

`_compute_get_duration` (`@api.depends('start_date','end_date')`): per row, `duration = 0`
unless both dates present, then `(end_date − start_date).days`.

### 3.3 `hr.employee.public` (inherited — `models/hr_employee_public.py`)
Adds a **read‑only related** field so the stage is exposed in public‑employee views/contexts
(where the private `hr.employee` record isn't directly accessible):

| Field | Type | Notes |
|---|---|---|
| `state` | Selection, `related='employee_id.state'`, string "Stage" | Mirror of the employee's current stage. |

### 3.4 `employee.stage` (wizard — `wizard/employee_stage.py`)
`_name = 'employee.stage'` · `TransientModel` · `_description = "Set Related User"`

| Field | Type | Notes |
|---|---|---|
| `related_user_id` | Many2one → `res.users` | Optional user to link to the employee on promotion. |

- **`set_as_employee()`** — reads `employee_id` from `self._context`, browses that
  `hr.employee`, optionally sets `employee.user_id = related_user_id`, then calls
  `employee.set_as_employee()` (the model method in 3.1) to move the record to **Employment**
  and write the history.

This wizard is the "Set as Employee" button on the employee form (the only transition that
opens a dialog — all others are direct object buttons).

---

## 4. Views (`views/hr_employee_views.xml`)

All views **inherit** standard `hr` views (no new menus/actions for stages beyond the wizard
action):

- **Employee form** (`view_employee_form`, inherits `hr.view_employee_form`):
  - Into `//header`: the six stage transition buttons, each gated by `invisible="state not in (...)"`:
    - **Start Grounding** → `action_start_grounding` (visible when `joined`)
    - **Start Test Period** → `action_start_test_period` (visible when `grounding`)
    - **Set as Employee** → action `employee_stages.employee_stage_action` (the wizard),
      visible when `joined`/`test_period`, passes `context="{'employee_id': id}"`
    - **Start Notice Period** → `action_start_notice_period` (visible when `employment`)
    - **Relieved** → `action_relived` (visible when `notice_period`)
    - **Terminate** → `action_terminate` (visible when `grounding`/`employment`)
  - A `state` **statusbar** widget (`statusbar_visible="joined,grounding,employment"`).
  - A new notebook page **"Status History"** (after `hr_settings`) showing the
    `stages_history_ids` tree: `state`, `start_date`, `end_date`, `duration` (with `sum="Total"`).
- **Employee tree** (`view_employee_tree`): adds the `state` column after `parent_id`.
- **Employee search** (`view_employee_filter`): adds a `state` searchable field, an
  **"Employees"** filter (`domain=[('state','=','employment')]`), and a **"State"**
  group‑by (`group_by:'state'`).
- **Employee kanban** (`hr_kanban_view_employees`): adds the `state` to the kanban card
  (after the 3rd `<li>`, shown only when `state` has a value).
- **Action override** — re‑declares `hr.open_view_employee_list_my` (the standard
  "Employees" action) with `context={"search_default_employee":1}`, i.e. the employees list
  **opens pre‑filtered to `state == 'employment'`** via the "Employees" search filter.
  > ⚠️ Gotcha: this overrides a *core* Odoo action record, so the default employees screen
  > now hides anyone not in the Employment stage unless the filter is removed. See Gotchas.

### 4.1 Wizard view (`wizard/employee_stage_views.xml`)
- `employee_stage_view_form` — a simple form with `related_user_id` and a **"Set as
  Employee"** object button (`name="set_as_employee"`).
- `employee_stage_action` — `ir.actions.act_window`, `target='new'` (dialog), opening the
  wizard form. Referenced by the form‑header "Set as Employee" button.

---

## 5. Reports
**N/A** — the module ships no QWeb / PDF reports.

## 6. Crons / automation
**N/A** — no `ir.cron`, no `base.automation`, no scheduled actions. All transitions are
manual button clicks.

## 7. Settings / config_parameters
**N/A** — no `res.config.settings` inherit, no `ir.config_parameter`. README states *"No
additional configurations needed."*

## 8. Assets / JS
**N/A** — no `static/src` JS/SCSS/OWL. The `static/description/` tree is only the Odoo Apps
store listing (banner, icon, screenshots, `index.html`) and is **not loaded** at runtime.

---

## 9. Security (`security/ir.model.access.csv`)

Four ACL rows (no custom groups, no record rules — reuses standard HR groups):

| Model | Group | R | W | C | U(nlink) |
|---|---|:--:|:--:|:--:|:--:|
| `employee.stage` (wizard) | `hr.group_hr_manager` | ✓ | ✓ | ✓ | ✓ |
| `employee.stage` (wizard) | `hr.group_hr_user` | ✓ | ✓ | ✓ | ✗ |
| `hr.employee.status.history` | `hr.group_hr_manager` | ✓ | ✓ | ✓ | ✓ |
| `hr.employee.status.history` | `hr.group_hr_user` | ✓ | ✓ | ✓ | ✗ |

- HR **Officers** (`group_hr_user`) get read/write/create but **not delete** on history rows
  and the wizard; HR **Managers** (`group_hr_manager`) get full CRUD.
- `state` / `stages_history_ids` on `hr.employee` inherit the standard employee access (no
  separate rule); `hr.employee.public.state` follows public‑employee access.

---

## 10. Gotchas & notes (read before debugging)

- **`joined → grounding` does not close the `joined` history row.** `action_start_grounding`
  creates the grounding row but never writes `end_date` on the open `joined` row, so the
  first history entry stays open (its `duration` reads 0). Every *other* transition closes
  its predecessor. If you need a complete duration ledger, fix this method.
- **`relieved` / `terminate` rows have no `start_date`.** `action_relived` and
  `action_terminate` create their history row with only `end_date=today`, so those rows show
  `duration = 0`. Intentional in the upstream module, but surprising on reports.
- **Resigned and Terminated archive the employee** (`active = False`). After those
  transitions the employee disappears from default lists (needs the *Archived* filter).
  There is **no un‑archive / re‑activate** transition in this module — reverse it manually.
- **Core action override side‑effect:** the module re‑declares
  `hr.open_view_employee_list_my` to default‑filter to Employment‑stage employees. New hires
  still in `joined`/`grounding`/`test_period` won't appear on the standard Employees screen
  until you clear the "Employees" filter. If the client reports "missing employees", this is
  why.
- **`track_visibility='always'`** on `state` is the Odoo ≤13 spelling; in Odoo 17 the
  supported attribute is `tracking=True`. It is silently ignored here, so **stage changes are
  not chatter‑tracked** despite the intent. Switch to `tracking=True` if tracking is wanted
  (and ensure `hr.employee` carries `mail.thread`, which it does).
- **`search()` used instead of filtered recordset** inside the button methods
  (`self.stages_history_ids.search([...])`) — works because the buttons run on a single
  record, but it's a full model search each click. Fine at this scale; don't copy the pattern
  into bulk operations.
- **No state‑machine guard at the data layer.** Transitions are enforced only by the form
  buttons' `invisible` conditions — calling the methods directly (RPC/shell) can move between
  any states. Validate in code if you expose these elsewhere.
- **`sudo()` on history writes** — all history create/write calls use `.sudo()`, so even an
  HR user without unlink can still log transitions; access control on the history model is
  therefore effectively for *direct* edits of the history tree, not the workflow itself.
- **Cybrosys upstream module:** keep changes minimal/marked if you intend to take future
  Cybrosys updates; the version line is `17.0.1.0.0` (initial 17.0 release, 12 Dec 2023 per
  `doc/RELEASE_NOTES.md`).

---

## 11. File map
```
__manifest__.py                  depends=['hr']; data: security, wizard view, employee views
__init__.py                      → models, wizard
models/
  __init__.py                    → hr_employee, hr_employee_public
  hr_employee.py                 HrEmployee (inherit) + EmployeeStageHistory (new model)
  hr_employee_public.py          hr.employee.public (inherit) — related `state`
wizard/
  __init__.py                    → employee_stage
  employee_stage.py              employee.stage TransientModel (Set Related User)
  employee_stage_views.xml       wizard form + act_window (target=new)
views/
  hr_employee_views.xml          form header buttons + statusbar + Status History page;
                                 tree/search/kanban inherits; Employees action override
security/
  ir.model.access.csv            4 ACL rows (hr user / hr manager)
README.rst                       Cybrosys store readme
doc/RELEASE_NOTES.md             v17.0.1.0.0 (2023-12-12, initial commit)
static/description/              Apps-store listing assets only (NOT loaded by Odoo)
```
