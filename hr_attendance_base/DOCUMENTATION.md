# hr_attendance_base — Developer Handover Documentation

> **HR Attendance (Professional) — Technical Base** for Odoo 17.
> A thin third-party "platform" layer (by EURO ODOO / Artem Shurshilov) that sits on
> top of standard `hr_attendance` and re-wires the **manual check-in / check-out flow** so
> that richer add-on modules (mobile, IP-fencing, geolocation, tokens, webcam, face
> recognition, kiosk) can hang extra data off every attendance punch through a shared
> `_context` convention. By itself this module only adds **mobile-device flags** to
> attendances, a custom attendance form, an extra security group set, and a JSON
> controller endpoint — the heavier features live in sibling modules that *depend on this
> one*. Read this before touching the code; it is the single source of truth for handover.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `hr_attendance_base` |
| Display name | `hr attendance professional policy technical base` |
| Version | `17.0` (manifest) — changelog stamps `15.4.1.3` (upstream lineage) |
| Odoo | 17.0 |
| License | `OPL-1` (Odoo Proprietary License v1.0) — paid app (price `9 EUR`) |
| Author / website | EURO ODOO, Shurshilov Artem · https://eurodoo.com |
| Category | Human Resources |
| Depends | `base`, `web`, `hr_attendance` |
| External Python libs | **none** (pure Odoo ORM/HTTP) |
| Front-end libs (shipped, not loaded) | SweetAlert2 (`Swal`), legacy `web.*` AMD modules |
| Inherited models | `hr.employee`, `hr.attendance` |
| New models | **none** (no new `_name`) |
| Controller route | `/hr_attendance_base` (JSON, `auth='user'`) |

> **Important framing for the new dev:** this is an *upstream-purchased* "eco-system base"
> module, not a bespoke client module. Its job per the manifest summary is *"quick and
> effective interaction and inheritance for all modules dependent on it, forming one
> eco-system."* Much of the shipped JS/CSS and the `parse_param` plumbing is scaffolding
> for **paid sibling add-ons** (IP / geo / token / webcam / face-recognition / kiosk) that
> are **not present in this repo**. See §11 Gotchas before assuming a feature is "broken."

### Deployment (this server)

DB `odoo17` · systemd `odoo-17.service` · runs as user `odoo`. Addons path includes
`/home/odoo/care` (this repo, branch `17`).

Update + restart:
```bash
/home/odoo/.pyenv/versions/odoo-17-env/bin/python \
  /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
  -d odoo17 -u hr_attendance_base --stop-after-init --no-http
sudo systemctl restart odoo-17.service
```
- Run the update as the `odoo` user if invoking from another shell account
  (`sudo -u odoo …`). No dev mode. Log file: `/var/log/odoo/odoo-17.log`.
- This module has **no `assets` block active** in the manifest (see §10) — a plain `-u`
  is enough for the Python/XML changes; there are no asset bundles to regenerate from
  this module.

---

## 2. Architecture overview

```
                          standard hr_attendance
                                   │
            ┌──────────────────────┴───────────────────────┐
            │ inherits                                       │ inherits
            ▼                                                ▼
   hr.attendance (_inherit)                         hr.employee (_inherit)
   ── adds mobile flags ──                          ── re-wires the punch flow ──
   • employee_id_image (related image_1920)         • attendance_manual(next_action, pin)
   • ismobile_check_in  (Boolean)                    •   → bypasses PIN, calls _attendance_action
   • ismobile_check_out (Boolean)                    • parse_param(vals, mode)  ◄─ context bridge
                                                      • _attendance_action_change() (override)
            ▲                                                 │ writes vals built from _context
            │ custom form view                                ▼
   hr_attendance_view_form_base ──────────────►  hr.attendance record (check_in/out + flags)
   (priority 80, replaces <sheet>)

   HTTP:  /hr_attendance_base  (JSON, auth=user)  ── returns {} ── handshake/ping endpoint
                                                     consumed by the shipped JS widgets

   Security:  HR PRO  (User → Manager → Admin, implied chain)
              Kiosk Attendance (User)  ── gates the kiosk "no user" menu

   Sibling add-on modules (NOT in this repo) depend on hr_attendance_base and read the
   *_check_in / *_check_out columns + the _context keys produced by parse_param().
```

**Design principle — the `_context` bridge.** The central trick of this module is that the
front-end attendance widgets push a *bag of per-punch metadata* (IP, geo string, token,
webcam snapshot, face image, "is mobile" flag, kiosk shop id, rendered access HTML…) into
the RPC `context`. `parse_param()` on `hr.employee` then translates those `_context` keys
into `<feature>_check_in` / `<feature>_check_out` field values on the `hr.attendance`
record being created/updated. **This base module only declares the `ismobile_*` columns;**
every other key written by `parse_param` (`geospatial_*`, `ip_*`, `geo_*`, `token_*`,
`webcam_*`, `user_agent_html_*`, `face_recognition_image_*`, `kiosk_shop_id_*`, and the
`accesses` loop) targets columns expected to be created by **dependent add-on modules**.
On a clean install of just this module, those `vals.update(...)` lines simply never fire
because the corresponding `_context` keys are absent.

---

## 3. Data model

No new models are defined. Two standard models are inherited.

### 3.1 `hr.attendance` (inherited — `models/hr_attendance.py`)

| Field | Type | Notes |
|---|---|---|
| `employee_id_image` | `Image` (related `employee_id.image_1920`) | shown on the custom form under "Face control" |
| `ismobile_check_in` | `Boolean` | set when the **check-in** came from a mobile device (`config.device.isMobile` → `_context['ismobile']`) |
| `ismobile_check_out` | `Boolean` | same, for **check-out** |

> Commented-out (kept for reference, not active): `employee_id_department_id` (related
> department) and `employee_id_identification_id` (related identification, `groups="hr.group_hr_user"`).
> If a downstream report needs department/ID on the attendance row, these are the intended hooks.

### 3.2 `hr.employee` (inherited — `models/hr_employee.py`)

No new fields. Adds/overrides **methods** that reroute the punch flow:

| Method | Purpose |
|---|---|
| `attendance_manual(self, next_action, entered_pin=None)` | **Override** of the standard manual-attendance entrypoint. `ensure_one()`, then directly returns `self._attendance_action(next_action)` — **note it ignores `entered_pin`**, i.e. the PIN check is bypassed for this flow (the front-end widgets call it via RPC after their own access checks). |
| `parse_param(self, vals, mode='in')` | The **`_context` → field-value bridge** (see §2). Reads keys off `self._context` and, when present, writes `<key>_check_<mode>` entries into `vals`. `mode` is `'in'` for check-in, `'out'` for check-out. Also handles a generic `accesses` dict: for each access point it picks one of four pre-rendered HTML snippets (`access_allowed` / `access_denied` / `access_allowed_disable` / `access_denied_disable`) depending on `enable` × `access`. |
| `_attendance_action_change(self)` | **Override** of the core check-in/out toggler. If the employee is not currently `checked_in`, it builds `{employee_id, check_in}` vals, calls `parse_param(vals)` (default mode `'in'`), and **creates** an `hr.attendance`. Otherwise it finds the open record (`check_out = False`), builds `{check_out}` vals, calls `parse_param(vals, 'out')`, and **writes** it. Raises the standard `UserError` ("Cannot perform check out … could not find corresponding check in …") if no open check-in exists. |

**Context keys consumed by `parse_param`** (each becomes `…_check_in` / `…_check_out`):
`ismobile`, `geospatial_id`, `ip_id`, `ip`, `geo`, `token`, `webcam`, `user_agent_html`,
`face_recognition_image`, `kiosk_shop_id`, plus the dynamic `accesses` map and its four
HTML payload context keys (`access_allowed`, `access_denied`, `access_allowed_disable`,
`access_denied_disable`).

> **Reminder:** of all those, only `ismobile_check_in/out` exist as columns *in this
> module*. The rest are written only when a dependent add-on has declared the matching
> field — otherwise Odoo would raise on an unknown column. In practice the front-end only
> sends the extra keys when the corresponding feature module is installed and enabled.

---

## 4. Computed logic & workflows

There are **no computed fields, no `@api.depends`, no crons, no constraints, no mail
threads, and no state machines** in this module. The only "workflow" is the punch
override described in §3.2:

```
front-end widget (JS)
  → _rpc model=hr.employee, method=attendance_manual, args=[[emp_id], next_action], context={…metadata…}
      → attendance_manual()  (PIN ignored)
          → _attendance_action(next_action)   [core]
              → _attendance_action_change()    [overridden here]
                  → parse_param(vals, mode)     [context → vals]
                  → create()/write() hr.attendance
```

---

## 5. Views & wizards

**Wizards:** none.

**Views (`views/views.xml`):**

1. **`hr_attendance_view_form_base`** (`ir.ui.view`, `model=hr.attendance`, `priority=80`)
   — inherits `hr_attendance.hr_attendance_view_form` and **replaces the entire `<sheet>`**
   (`xpath //sheet position="replace"`). The replacement sheet shows:
   - A 4-col group: `check_in`, `check_out`, `ismobile_check_in`, `ismobile_check_out`,
     and `worked_hours` (rendered at `font-size:25px`).
   - A "Face control" group (col 8): `employee_id` + `employee_id_image`
     (`widget="image"`, `options='{"size": [100, 133]}'`).
   - Two empty placeholder groups **"Check in"** and **"Check out"** — these are
     **intentional extension points**: dependent add-ons xpath into them to drop their
     own per-feature fields (IP, geo, token, webcam, face). They look empty by design.

2. **`hr_attendance.menu_hr_attendance_kiosk_no_user_mode`** (re-declared `ir.ui.menu`)
   — **re-parents** the standard kiosk "no user" menu to top-level (`parent_id = False`)
   and restricts it to `group_kiosk_attendance_user` (see §9). This is how the kiosk
   menu visibility is gated.

> The commented-out `assets_backend_hr_attendance_base` `<template>` at the top of the
> file is the **legacy v13/v15 asset-injection block** (link/script tags for the CSS + JS).
> It is disabled — see §10.

---

## 6. Reports

**None.** No QWeb-PDF reports, no `ir.actions.report`, no paperformats.

---

## 7. Crons / automation

**None.** No `ir.cron`, no automated actions, no server actions, no scheduled jobs.

---

## 8. Settings / config parameters

**None.** No `res.config.settings` inheritance, no `ir.config_parameter` keys, no system
parameters. All behaviour is driven by runtime RPC `_context` (see §3.2), not by stored
settings.

---

## 9. Security (`security/hr_attendance_security.xml`)

No `ir.model.access.csv` and no record rules ship with this module (the inherited
`hr.attendance` / `hr.employee` keep their standard ACLs). The file declares **categories
and groups only:**

**Category `HR PRO`** (`category_hr_attendance_pro`, parent = `Human Resources`), with an
implied-chain group ladder:

| Group | XML id | Implies / membership |
|---|---|---|
| **User** | `group_hr_attendance_user_pro` | auto-adds **every internal user** — `users = [(4, ref('base.group_user'))]` (so all employees get the "User" pro role on install; per changelog `15.4.1.3 [ADD] auto apply group user`) |
| **Manager** | `group_hr_attendance_manager_pro` | `implied_ids = [user_pro]` |
| **Admin** | `group_hr_attendance_admin_pro` | `implied_ids = [manager_pro]`; members = `base.user_root`, `base.user_admin` |

> The `implied_ids` to `hr.group_hr_user` / `hr.group_hr_manager` are present but
> **commented out** — the pro groups deliberately do *not* drag in standard HR rights.

**Category `Kiosk Attendance`** (`module_kiosk_attendance`):

| Group | XML id | Used for |
|---|---|---|
| **User** | `group_kiosk_attendance_user` | gates the re-parented kiosk "no user" menu (§5) |

---

## 10. Assets / JS

The manifest's `assets` block (and the legacy `qweb` list, and the in-XML
`assets_backend_hr_attendance_base` template) are **all commented out**. So on this server
the shipped front-end files are **present in the repo but not loaded by Odoo**:

```
static/src/css/steps.css
static/src/css/sweetalert2.css
static/src/js/lib/sweetalert2.js
static/src/js/attendances_base.js
static/src/js/kiosk_mode_base.js
static/src/xml/base.xml
```

What they *would* do if re-enabled (legacy **Odoo-13/15-era `odoo.define` AMD** code — **not**
OWL; it `require('web.core')`, `web.config`, `hr_attendance.my_attendances`,
`hr_attendance.kiosk_confirm`):

- **`attendances_base.js`** — `MyAttendances.include({...})`. Overrides the "My
  Attendances" widget's `init` / `willStart` / `start` with a `$.Deferred()` state machine
  (`state_read → state_save → state_render`). On punch (`update_attendance`) it gathers the
  enabled access points (`geo/webcam/ip/token/face_recognition/geospatial`), optionally
  snaps a webcam frame, runs `check_access()` (SweetAlert "Access denied" if any required
  point failed), then `send_data()` → `_rpc(model='hr.employee', method='attendance_manual', context={…})`.
- **`kiosk_mode_base.js`** — `KioskModeConfirm.include({...})`. Same pattern for the kiosk
  confirmation screen; rebinds the sign-in/out icon click (debounced 200 ms) to its own
  `update_attendance`/`send_data`. Its `accesses` set omits `geospatial`.
- **`base.xml`** — four tiny QWeb templates rendered into the RPC context as access-status
  icons: `HrAttendanceAccessAllowed` (green check), `HrAttendanceAccessDenied` (red ban),
  and the two greyed "…Disable" variants.

These widgets are the **producers** of the `_context` metadata that `parse_param` consumes.
They reference globals (`Swal`, `Webcam`) and helper methods (`parse_data_geo`, `geolocation`,
`parse_data_webcam`, `parse_data_ip`, `parse_data_token`, `parse_data_face_recognition`,
`parse_data_geospatial`) that are **defined in the dependent add-on modules**, not here.

### Controller (`controllers/controllers.py`)

```python
@http.route('/hr_attendance_base', auth='user', type="json", cors='*')
def index(self, **kw):
    return {}
```

A single JSON route that **returns an empty dict**. In this base module it is effectively a
handshake/ping the JS widgets call before a punch (`route: '/hr_attendance_base'`). Dependent
modules are expected to **override/extend** this controller to return the real per-feature
configuration (`geo_enable`, `webcam_enable`, `ip_enable`, `token_enable`,
`face_recognition_enable`, `geospatial_enable`, …) that the widgets branch on.

---

## 11. Gotchas & notes (read before debugging)

- **It is a *base/SDK* module, not a feature module.** The summary literally says it forms
  "one eco-system" for *dependent* modules. Out of the box it adds only: mobile-punch
  flags, a custom attendance form, the HR PRO / Kiosk group sets, and the `/hr_attendance_base`
  ping. Do not expect IP/geo/token/webcam/face/kiosk-shop behaviour from this repo alone —
  those live in sibling paid add-ons that are **not present here**.
- **`parse_param` writes columns this module doesn't define.** Only `ismobile_check_in/out`
  exist here. Every other `vals.update({key + '_check_' + mode: …})` assumes a dependent
  module created the column. If you ever push one of those `_context` keys (e.g. `ip`,
  `token`) without the owning module installed, the subsequent `create`/`write` will fail
  on an unknown field. The JS is written to only send keys when the matching feature is
  enabled by the controller response — keep that contract.
- **PIN is bypassed.** `attendance_manual(next_action, entered_pin=None)` ignores
  `entered_pin` and goes straight to `_attendance_action`. Front-end access checks
  (SweetAlert `check_access`) are the gate, not the Odoo PIN. Security-sensitive
  deployments should be aware the server-side PIN enforcement of standard kiosk mode is
  not applied through this path.
- **Form view uses `position="replace"` on `//sheet`.** This is brittle across Odoo
  upgrades and conflicts with any other module that also replaces the attendance form
  sheet. The two empty "Check in"/"Check out" groups are extension anchors — don't delete
  them thinking they're dead markup. `priority=80` makes this view win over lower-priority
  inheritors.
- **Legacy front-end.** All JS is pre-OWL `odoo.define` AMD using jQuery `$.Deferred`,
  `web.core`, `QWeb`. If/when the assets are re-enabled on Odoo 17 they will need porting
  (Odoo 17 ships the OWL attendance app; these `hr_attendance.my_attendances` /
  `kiosk_confirm` AMD modules no longer exist in core). As shipped they are **inert**.
- **Auto-applied User group.** Installing this module silently grants the **HR PRO → User**
  group to *all* internal users (`base.group_user`). If you need to scope pro features,
  remove that `users` line and assign manually.
- **Version mismatch.** Manifest `version` is `17.0` but `changelog.rst` tracks the
  upstream `15.4.x` lineage — the module was carried forward from a v15 product. Treat the
  changelog as historical context, not a v17 change log.
- **License is OPL-1 (paid).** This is a purchased third-party app. Respect the proprietary
  license header in every `.py` file before redistributing or copying code out.

---

## 12. File map

```
__manifest__.py                 depends: base, web, hr_attendance · data: security + views
                                (assets/qweb blocks commented out)
changelog.rst                   upstream lineage (15.4.1.2 / 15.4.1.3)

__init__.py                     → controllers, models
controllers/
  __init__.py                   → controllers
  controllers.py                /hr_attendance_base JSON route (returns {})
models/
  __init__.py                   → hr_employee, hr_attendance
  hr_attendance.py              hr.attendance (_inherit): employee_id_image,
                                ismobile_check_in/out
  hr_employee.py                hr.employee (_inherit): attendance_manual,
                                parse_param (context→vals bridge),
                                _attendance_action_change (punch override)
security/
  hr_attendance_security.xml    HR PRO (User→Manager→Admin) + Kiosk Attendance (User)
                                — groups/categories only, no ACL csv, no record rules
views/
  views.xml                     hr.attendance custom form (priority 80, replaces <sheet>);
                                re-parents/gates kiosk no-user menu;
                                legacy asset <template> (commented out)
static/src/
  js/attendances_base.js        legacy AMD: MyAttendances.include (NOT loaded)
  js/kiosk_mode_base.js         legacy AMD: KioskModeConfirm.include (NOT loaded)
  js/lib/sweetalert2.js         SweetAlert2 vendor lib (NOT loaded)
  css/steps.css, css/sweetalert2.css   styling (NOT loaded)
  xml/base.xml                  4 access-status icon QWeb templates (NOT loaded)
static/description/             app-store screenshots, icon.png, index.html
```
