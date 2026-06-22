# ohrms_holidays_approval — Developer Handover Documentation

> **Open HRMS Leave Multi-Level Approval** — a Cybrosys/Open-HRMS module for Odoo 17 that
> adds a **configurable multi-level (multi-approver) approval workflow** on top of the
> standard `hr_holidays` leave request. A leave **type** can be flagged as *Multi Level
> Approval*; it then carries an ordered/unordered set of **validators** (users). Each leave
> request of that type seeds one approval line per validator, and the request is only fully
> approved once **every** validator has approved. UI is English (standard Open-HRMS); this
> deployment runs Arabic content elsewhere but this module ships no Arabic labels of its own.
> Read this before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `ohrms_holidays_approval` |
| Display name | Open HRMS Leave Multi-Level Approval |
| Version | `17.0.1.0.0` |
| Odoo | 17.0 |
| Category | Human Resources |
| License | LGPL-3 |
| Author | Cybrosys Techno Solutions / Open HRMS |
| Depends | `hr_holidays` |
| External Python libs | **None** (pure Odoo ORM) |
| New models | `hr.holidays.validators`, `leave.validation.status` |
| Inherited models | `hr.leave`, `hr.leave.type` |
| Reports / Wizards / Crons | **None** (N/A) |
| Assets / JS | **None** (no `web.assets_*` bundle) |

### Deployment (this server)
DB `odoo17` · systemd `odoo-17.service` · user `odoo` · addons path includes `/home/odoo/care`
(this repo, branch `17`). Update + restart:
```bash
sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
  /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
  -d odoo17 -u ohrms_holidays_approval --stop-after-init --no-http
sudo systemctl restart odoo-17.service
```
No dev mode. Log file: `/var/log/odoo/odoo-17.log`. This module ships no JS/SCSS, so the
asset bundles are not affected — a plain `-u` + restart is sufficient.

---

## 2. Architecture overview

```
hr.leave.type  (inherited — models/hr_leave_type.py)
│   leave_validation_type  += 'multi'  (new Selection option "Multi Level Approval")
│   multi_level_validation (computed bool: True when leave_validation_type == 'multi')
│   validator_ids  ──many2many──►  hr.holidays.validators   (the approver roster for this type)
│
└── drives ────────────────────────────────────────────────────────────────┐
                                                                            ▼
hr.leave  (inherited — models/hr_leave.py)                          hr.holidays.validators
│   multi_level_validation  (related ← holiday_status_id)            (models/hr_holidays_validators.py)
│   validation_status_ids ──one2many──► leave.validation.status        user_id  → res.users
│   user_ids (computed: validators NOT yet approved)                   name     (related user name)
│   _onchange_holiday_status_id : seed one status line per validator
│   action_approve / approval_check : multi-level gate
│   action_refuse / action_draft   : overrides
│   _get_approval_requests : "Approval Requests" menu action
│
└── one2many ──►  leave.validation.status  (models/leave_validation_status.py)
                  leave_id           → hr.leave
                  user_id            → res.users  (this approver)
                  validation_status  (bool — has this approver approved?)
                  leave_comments     (text per approver)

Server action  "Approvals"  →  hr.leave._get_approval_requests()
Menu           hr_holidays.menu_hr_holidays_management → "Approval Requests"
```

**Design summary**
- The roster of approvers is configured **once per leave type** (`validator_ids` on
  `hr.leave.type`), via the new `hr.holidays.validators` lookup model.
- Every leave request of a multi-level type gets a **per-approver status line**
  (`leave.validation.status`) seeded by the `holiday_status_id` onchange.
- "Fully approved" = **all** status lines have `validation_status = True`. Only then does the
  request advance through the standard `hr.leave` validate path.
- A dedicated **"Approval Requests"** menu (server action) lists the confirmed requests where
  the current user is one of the validators.

---

## 3. Data model

### 3.1 `hr.holidays.validators` (new — `models/hr_holidays_validators.py`)
A small lookup model representing **one selectable leave validator (a user)**. Rows are
attached to leave types via `hr.leave.type.validator_ids` (m2m).

| Field | Type | Purpose |
|---|---|---|
| `user_id` | Many2one `res.users` (domain `share=False`) | The validator user (internal users only — portal/shared users excluded) |
| `name` | Char, `related='user_id.name'` | Display name (the user's name), shown in the validators tree |

No methods. View: a simple tree (`hr_holidays_validators_view_tree`) showing `name`.

### 3.2 `hr.leave.type` (inherited — `models/hr_leave_type.py`)
Adds the multi-level toggle and the approver roster.

| Field | Type | Purpose |
|---|---|---|
| `leave_validation_type` | Selection (`selection_add=[('multi','Multi Level Approval')]`) | Extends the standard validation-type selection with a new **"Multi Level Approval"** option |
| `multi_level_validation` | Boolean, computed (`_compute_multi_level_validation`), **not stored** | `True` iff `leave_validation_type == 'multi'`. Convenience flag used by views and mirrored onto `hr.leave` |
| `validator_ids` | Many2many `hr.holidays.validators` | The set of validators required to approve leaves of this type |

`_compute_multi_level_validation` (`@api.depends('leave_validation_type')`) — sets the bool
from the selection value.

### 3.3 `hr.leave` (inherited — `models/hr_leave.py`)
The core of the workflow. Adds approval tracking and overrides the approve/refuse/draft
actions.

| Field | Type | Purpose |
|---|---|---|
| `validation_status_ids` | One2many `leave.validation.status` (inverse `leave_id`) | One approval line per validator for this request; `track_visibility='always'` |
| `multi_level_validation` | Boolean, `related='holiday_status_id.multi_level_validation'` | Mirrors the type flag onto the request (drives view visibility) |
| `user_id` | Many2one `res.users`, default = current user | "Current user" helper (default `self.env.user`) |
| `user_ids` | Many2many `res.users`, computed (`_compute_user_ids`), **not stored** | The validators who have **not yet** approved — i.e. who still need to act. Used by the view to decide whether the current user may see the Approve/Refuse buttons |

**Computed logic**
- `_compute_user_ids` (`@api.depends('validation_status_ids')`) — searches the validators
  whose status line still has `validation_status = False`. When this set becomes empty, all
  approvers have signed off.

**Workflow methods**
- `_onchange_holiday_status_id` (`@api.onchange('holiday_status_id')`) — **seeds the approval
  lines**. Clears `validation_status_ids` (`(5,0,0)`), then for each `validator_ids.user_id`
  on the chosen leave type that is not already present, creates a new
  `leave.validation.status` line. This is what populates the **Validation Status** tab when
  you pick a multi-level leave type.
- `action_approve` — override. Guards that every record is in state `confirm` (label *"To
  Approve"*), then delegates to `approval_check()`.
- `approval_check` — **the multi-level gate.**
  1. Resolves the current employee and the target leave (via `active_id` context or `self.id`).
  2. If the current user (`self.env.uid`) is one of the request's validators, set **their**
     status line `validation_status = True`.
  3. Compute `approval_flag` = `True` only if **no** validator line is still unapproved.
  4. If fully approved:
     - records with `validation_type == 'both'` → `state = 'validate1'` + set
       `first_approver_id` (so the standard second-approver step still applies);
     - records with `validation_type != 'both'` → call standard `action_validate()`
       (final approval);
     - run `activity_update()` (unless `leave_fast_create` context), add the current user to
       `user_ids`, return `True`.
  5. If not yet fully approved, return `False` (request stays in `confirm`, awaiting the
     remaining validators).
- `action_refuse` — override. If the current user is one of the request's validators they may
  refuse: depending on state, set `state='refuse'` with `first_approver_id` (from
  `validate1`) or `second_approver_id`; unlink the calendar `meeting_id`; cascade
  `linked_request_ids.action_refuse()`; remove resource leave; `activity_update()`; and reset
  **their** status line to `False`. If the user is **not** a validator, the same refuse logic
  runs but **without** touching a status line (so a manager outside the roster can still
  refuse). Both branches require state in `confirm`/`validate`/`validate1` or raise a
  `UserError`.
- `action_draft` — override. Resets **every** validator status line to `False`, then calls
  `super().action_draft()`. Sending a request back to draft clears all prior approvals.
- `_get_approval_requests` — builds the **"Approval Requests"** action: searches all
  `hr.leave` in state `confirm`, keeps those where the current user appears in
  `validation_status_ids`, and returns an `ir.actions.act_window` (tree,form;
  `create=False`, `edit=False`) domain-limited to those ids.

### 3.4 `leave.validation.status` (new — `models/leave_validation_status.py`)
One approval line: **a validator's verdict on a specific leave request.**

| Field | Type | Purpose |
|---|---|---|
| `leave_id` | Many2one `hr.leave` | The leave request this line belongs to |
| `user_id` | Many2one `res.users` (domain `share=False`) | The validator |
| `validation_status` | Boolean, `readonly`, `track_visibility='always'` | Has this validator approved? Driven by `approval_check` / reset by refuse & draft |
| `leave_comments` | Text | Free-text comment from this validator |

`_onchange_user_id` (`@api.onchange('user_id')`) — **always raises a `UserError`**: changing
the validator on a leave request is forbidden; validators must be edited from the leave
**type** configuration. (In practice the tree is `create="false" delete="false"`, so this is
a belt-and-braces guard.)

---

## 4. Views (`views/*.xml`)

### 4.1 `hr_leave_views.xml` — leave request form + Approvals menu
Inherits `hr_holidays.hr_leave_view_form`:
- **Replaces** the standard `action_approve` button. New visibility:
  `invisible = state != 'confirm' or not active or (multi_level_validation and uid not in
  user_ids) or (not multi_level_validation and not can_approve)`.
  → For multi-level types the Approve button only shows while the current user is still a
  **pending** validator (`uid in user_ids`); for normal types it falls back to the standard
  `can_approve`.
- **Replaces** the standard `action_refuse` button with the analogous combined visibility
  (validator-or-standard, state in `confirm`/`validate1`/`validate`).
- Adds hidden helper fields `multi_level_validation` and `user_ids`, plus a **"Validation
  Status"** notebook page (visible only when `multi_level_validation` is true) showing the
  `validation_status_ids` tree: `user_id`, `validation_status`, and `leave_comments`
  (each validator can edit only their own comment via `readonly="user_id != uid"`). The tree
  is `create="false" delete="false"`; the whole field is read-only once the leave is
  `refuse`/`validate`.
- **Server action** `hr_leave_action` ("Approvals") — `state=code`, runs
  `model._get_approval_requests()`; also bound to the model (`binding_model_id`).
- **Menu** `hr_leave_menu` — **"Approval Requests"** under
  `hr_holidays.menu_hr_holidays_management`, sequence 1.

### 4.2 `hr_leave_type_views.xml` — leave type configuration
Inherits `hr_holidays.edit_holiday_status_form`:
- Tweaks `responsible_ids` visibility so it stays hidden for the `multi` validation type
  (alongside `no_validation`/`manager`) unless allocation requires an officer.
- Adds a **"Leave validation"** notebook page (visible only when
  `leave_validation_type == 'multi'`) exposing the `validator_ids` roster.

### 4.3 `hr_holidays_validators_views.xml` — validators lookup
A single tree view (`hr_holidays_validators_view_tree`) listing the validator `name`. No
menu/action of its own — surfaced through the m2m widget on the leave type.

---

## 5. Reports, Wizards, Crons, Settings, Assets

- **Reports:** N/A — module ships none.
- **Wizards / TransientModels:** N/A.
- **Cron jobs / automation:** N/A — no `ir.cron`. The only "automation" is the
  `_onchange_holiday_status_id` seeding and the approve/refuse overrides.
- **Settings / `config_parameter`:** N/A — no `res.config.settings` extension. Configuration
  is entirely on the **leave type** (`leave_validation_type = 'multi'` + `validator_ids`).
- **Assets / JS / OWL:** N/A — no `web.assets_*` entry in the manifest; only static
  description/screenshot images under `static/description/` (store listing art, not loaded
  at runtime).

---

## 6. Security (`security/ir.model.access.csv`)

No new groups or record rules — the module reuses the standard `hr_holidays` groups. ACLs:

| Model | Group | R | W | C | U(nlink) |
|---|---|---|---|---|---|
| `leave.validation.status` | `hr_holidays.group_hr_holidays_manager` | ✔ | ✔ | ✔ | ✔ |
| `leave.validation.status` | `hr_holidays.group_hr_holidays_user` | ✔ | ✔ | ✔ | ✔ |
| `leave.validation.status` | `base.group_user` | ✔ | ✔ | ✘ | ✘ |
| `hr.holidays.validators` | `hr_holidays.group_hr_holidays_manager` | ✔ | ✔ | ✔ | ✔ |
| `hr.holidays.validators` | `base.group_user` | ✔ | ✔ | ✘ | ✘ |

> Note: every internal user (`base.group_user`) gets **write** on `leave.validation.status`
> and `hr.holidays.validators`. That is required so a validator can flip their own status /
> comment, but it means any internal user technically has ORM write on these tables — the
> real gating is in the **button visibility** and the `approval_check`/`action_refuse` logic,
> not in the ACLs. The `_onchange_user_id` guard and `create=false/delete=false` on the tree
> further constrain editing in the UI.

`hr.leave` and `hr.leave.type` are inherited models, so they keep their existing
`hr_holidays` access rules and record rules.

---

## 7. Approval workflow — precise walkthrough

1. **Configure the type.** On a `hr.leave.type`, set **Validation** =
   *"Multi Level Approval"* (`leave_validation_type = 'multi'`). A **"Leave validation"** tab
   appears; add the required approvers to `validator_ids` (each is an
   `hr.holidays.validators` row → a `res.users`).
2. **Create the request.** An employee creates an `hr.leave`. When they pick the multi-level
   type, `_onchange_holiday_status_id` clears and **re-seeds** `validation_status_ids` with
   one `leave.validation.status` line per configured validator (all `validation_status=False`).
   The **"Validation Status"** tab shows the roster.
3. **Confirm.** Standard `hr.leave` flow moves the request to `confirm` ("To Approve").
4. **Each validator approves.** A validator opens the request (or finds it via **Approval
   Requests**) and clicks **Approve** → `action_approve` → `approval_check` sets that
   validator's line to `True`. `_compute_user_ids` removes them from `user_ids`, so their
   Approve button disappears. The request **stays in `confirm`** until the **last** validator
   approves.
5. **Final approval.** When no line is left unapproved (`approval_flag = True`):
   - `validation_type == 'both'` requests go to `validate1` (with `first_approver_id`),
     deferring to the standard second-level officer/manager step;
   - all other requests are finalized via the standard `action_validate()`.
6. **Refusal.** Any validator (or a manager outside the roster) can **Refuse** at
   `confirm`/`validate1`/`validate`; the request goes to `refuse`, the calendar meeting and
   linked requests are cleaned up, and (for a validator) their status line is reset.
7. **Reset to draft.** `action_draft` wipes **all** validator statuses back to `False`, so a
   re-submitted request must be re-approved by everyone.
8. **Approval Requests menu** (under *Time Off → Management*): lists every `confirm` leave
   where the current user is a validator; read-only list (no create/edit) to triage pending
   approvals.

---

## 8. Gotchas & notes (read before debugging)

- **Validators are seeded by an onchange, not a compute/create hook.** If a leave request is
  created **programmatically** or imported (bypassing the form `onchange`),
  `validation_status_ids` will be **empty** → `approval_check` sees no pending validators and
  the request can sail straight through. When creating leaves in code for multi-level types,
  populate `validation_status_ids` yourself.
- **Changing `validator_ids` on a type does NOT retro-update existing requests.** Seeding
  happens only when the request's `holiday_status_id` onchange fires. In-flight requests keep
  their original roster.
- **`multi_level_validation` and `user_ids` are non-stored computes.** Don't filter/group/
  search on them in domains or reports — they aren't in the DB.
- **`_onchange_user_id` on `leave.validation.status` always raises.** It's intentional: you
  cannot change a validator on a request; edit the leave type instead. Don't "fix" it by
  removing the raise without understanding the seeding model.
- **`track_visibility='always'`** is the legacy attribute name; in Odoo 17 the canonical
  attribute is `tracking=True`. It still works here but is non-idiomatic — note if you
  refactor chatter tracking.
- **ACL write is broad** (`base.group_user` can write both new models). Real authorization
  lives in the button `invisible` expressions + `approval_check`/`action_refuse` — change
  those together, not just the CSV.
- **Standard second-level approval still applies.** For leave types with
  `validation_type == 'both'`, multi-level approval only gets the request to `validate1`; the
  normal officer/manager second approval finishes it. Multi-level is an **additional** gate
  in front of the standard flow, not a replacement.
- **Depends only on `hr_holidays`.** No external Python libraries, no other custom modules —
  safe to update in isolation.

---

## 9. File map
```
__manifest__.py                         depends=['hr_holidays']; data: security + 3 view files
__init__.py                             → models
doc/RELEASE_NOTES.md                    v17.0.1.0.0 initial commit (09.01.2024)
README.rst                              store description
models/
  __init__.py
  hr_holidays_validators.py             hr.holidays.validators  (validator lookup)
  hr_leave_type.py                      hr.leave.type  (+ 'multi' type, validator_ids)
  hr_leave.py                           hr.leave  (workflow overrides — the core)
  leave_validation_status.py            leave.validation.status  (per-approver line)
security/
  ir.model.access.csv                   ACLs for the two new models
views/
  hr_leave_views.xml                    leave form buttons + Validation Status tab + Approvals menu
  hr_leave_type_views.xml               leave type "Leave validation" tab
  hr_holidays_validators_views.xml      validators tree
static/description/                     icon/banner/screenshots (store art — not runtime assets)
```
