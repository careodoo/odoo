# hr_reminder — Developer Handover Documentation

> **Open HRMS Reminders Todo** — a third-party **Cybrosys / OpenHRMS** module for Odoo 17.
> It lets an HR user define *generic, configurable reminders* over any date/datetime field
> of any `hr.*` model, then surfaces the currently-due reminders in a **systray bell
> dropdown**. Clicking a reminder opens the list of records whose date matches that reminder's
> rule. The module is small and almost entirely UI/controller-driven — there is **no cron, no
> e-mail, no scheduled job**. Arabic translations ship for the UI labels. Read this before
> touching the code.

> ⚠️ **Origin / customisation note:** this is an unmodified upstream Cybrosys module
> (author *Cybrosys Techno solutions, Open HRMS*). It is **not** a bespoke `care_*` module.
> No local customisations have been layered on top — keep upstream-compatibility in mind if
> you patch it (a future upstream update would overwrite changes made directly here).

---

## 1. At a glance

| | |
|---|---|
| Technical name | `hr_reminder` |
| Display name | Open HRMS Reminders Todo |
| Version | `17.0.1.0.0` |
| Odoo | 17.0 |
| Category | Human Resources |
| Depends | `hr` |
| External Python libs | **None** (stdlib `datetime.timedelta` only) |
| External services | None |
| Main / only model | `hr.reminder` |
| Inherited models | None |
| Controllers | `/hr_reminder/all_reminder`, `/hr_reminder/reminder_active` (JSON, `auth="public"`) |
| Assets | systray OWL component + SCSS/CSS (`web.assets_backend`) |
| License | LGPL-3 |
| Author / website | Cybrosys Techno Solutions · https://www.openhrms.com |

### Deployment (this server)
- DB: `odoo17` · service: `odoo-17.service` (systemd) · runs as user `odoo`.
- Python venv: `/home/odoo/.pyenv/versions/odoo-17-env/bin/python`
- Odoo bin: `/home/odoo/odoo-17.0+e.20241205/odoo-bin` · conf: `/home/odoo/odoo.conf`
- Addons path includes `/home/odoo/care` (this repo, branch `17`).
- **Update + restart:**
  ```bash
  sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
    /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
    -d odoo17 -u hr_reminder --stop-after-init --no-http
  sudo systemctl restart odoo-17.service
  ```
- No dev mode. After editing the JS / SCSS / CSS / OWL-XML assets, the module `-u`
  regenerates the `web.assets_backend` bundle; the restart serves it. A **hard browser
  refresh** is usually needed for the systray component to reload. Log file:
  `/var/log/odoo/odoo-17.log`.

---

## 2. Architecture overview

This module has **two halves** that meet at the JSON controllers:

```
CONFIG (backend, ORM)                       RUNTIME (browser, systray)
─────────────────────                       ──────────────────────────
hr.reminder  (the only model)               OWL systray component
  • name        (Title)                       ReminderMenu  (reminder_topbar.js)
  • model_id    → ir.model (hr.* only)        template owl.reminder_menu
  • field_id    → ir.model.fields            ┌─ bell icon in top-right systray
                  (date/datetime only)       │  click → showReminder()
  • search_by   today|set_period|set_date    │     └─ RPC /hr_reminder/all_reminder
  • days_before / date_set                   │           → list of DUE reminders → <select>
  • date_from / date_to                      │
  • expiry_date                              └─ "View" button → reminderActive()
  • company_id  → res.company                      └─ RPC /hr_reminder/reminder_active
                                                         → returns [model, field, rule…]
        ▲                                              → builds a domain on that field
        │ records configured in                        → action.doAction() opens the
        │ Reminders menu (tree/form)                      target model's records (target:new)
        │
   controllers/hr_reminder.py
   (decides which reminders are DUE today, and
    re-derives the date window for the chosen one)
```

**Design summary**
- The **model stores only the *rule*** (which model, which date field, and a time test).
- The **controller evaluates the rule against `today()`** and the **OWL systray** renders the
  result. There is **no stored "is-due" state and no notification record** — due-ness is
  computed live on each bell click.
- `search_by` is the heart of the logic; it has three modes (see §4.2).
- All date comparisons are **date-only** (`fields.Date.today()` / `fields.date.today()`),
  even though the target field may be a `datetime` — the controller/JS bracket it with
  `00:00:00`…`23:59:59` to build the final domain.

---

## 3. Module-level constants / helpers
**N/A** — no module-level constants, schemas, or helper modules. Logic is inline in
`models/hr_reminder.py` (field defs only) and `controllers/hr_reminder.py`.

---

## 4. Data model

### 4.1 `hr.reminder` (`models/hr_reminder.py`) — the only model
`_name = 'hr.reminder'` · `_description = "HR Reminder"` · **no `_inherit`, no `_order`,
no chatter.** Plain `models.Model`.

| Field | Type | Required | Purpose / notes |
|---|---|---|---|
| `name` | Char | yes | **Title** of the reminder (the label shown in the systray `<select>`; the runtime lookup matches on this — see Gotchas). |
| `model_id` | Many2one `ir.model` | yes | Target model. **Domain `[('model','like','hr')]`** — only models whose technical name contains `hr` are selectable. `ondelete='cascade'`. |
| `field_id` | Many2one `ir.model.fields` | yes | The date field to watch. **Domain `[('model_id','=',model_id),('ttype','in',['datetime','date'])]`** — only date/datetime fields of the chosen model. `ondelete='cascade'`. |
| `search_by` | Selection | yes | Rule mode: `today` / `set_period` / `set_date`. Drives all logic. |
| `days_before` | Integer | no | "Reminder before" — days before `date_set` the reminder starts showing (only meaningful for `set_date`). |
| `date_set` | Date | no | "Select Date" — the anchor date for `set_date` mode. |
| `date_from` | Date | no | "Start Date" — window start for `set_period` mode. |
| `date_to` | Date | no | "End Date" — window end for `set_period` mode. |
| `expiry_date` | Date | no | "Reminder Expiry Date" — after this date the reminder stops appearing (applies to `set_period` and `set_date`; **not** to `today`). |
| `company_id` | Many2one `res.company` | yes | Company of the record; default `self.env.user.company_id`. Used by the multi-company record rule (§9). |

**No methods, no computes, no constraints, no overrides** in the model — it is a pure
configuration record. All behaviour lives in the controllers and JS.

### 4.2 The `search_by` rule modes (where the real logic lives)
Evaluated in `controllers/hr_reminder.py → all_reminder()` to decide if a reminder is **due
today**, and re-evaluated in the JS to build the final record domain:

| Mode | Label | Due-today test (controller) | Required form fields |
|---|---|---|---|
| `today` | Today | **Always due** — appears every day, unconditionally. | (none extra) |
| `set_period` | Set Period | `date_from <= today <= date_to` **and** (`expiry_date` empty or `today <= expiry_date`). | `date_from`, `date_to` (both required in view), optional `expiry_date`. |
| `set_date` | Set Date | `today >= (date_set − days_before)` **and** (`expiry_date` empty or `today <= expiry_date`). | `date_set` (required), `days_before`, optional `expiry_date`. |

> Note the form makes `expiry_date` visible for both `set_period` and `set_date`
> (`invisible="search_by == 'today'"`), and `days_before` visible only for `set_date`.

---

## 5. Views (`views/hr_reminder_views.xml`)
- **Form** (`hr_reminder_view_form`): title (`name`) as the `oe_title`; two columns —
  left: `model_id`, `search_by`, `date_from`, `date_set`, `date_to`, `company_id`; right:
  `field_id`, `days_before`, `expiry_date`. Conditional visibility/`required` driven by
  `search_by` (v17 Python-expression `invisible`/`required`, e.g.
  `invisible="search_by not in ['set_period']"`).
- **Tree** (`hr_reminder_view_tree`, titled *"Pop-Up Reminder"*): `name`, `model_id`,
  `field_id`, `company_id`.
- **Action** `hr_reminder_action` — *"Reminders"*, `res_model=hr.reminder`,
  `view_mode="tree,form"`, with a no-content "Click here to configure new periodic reminder."
- **Menu** `hr_reminder_menu` — **top-level app menu** *"Reminders"* (`sequence=8`,
  `web_icon` = the module icon), opens the action. There is **no parent menu under HR** — it
  is its own root app entry.

### Wizards
**N/A** — no `TransientModel` / wizards.

---

## 6. Reports
**N/A** — no QWeb / PDF reports, no `report.*` records, no `paperformat`.

---

## 7. Crons / automation
**N/A — IMPORTANT.** Despite being a "reminder" module, there is **no `ir.cron`**, no
scheduled action, and no e-mail/notification dispatch. Reminders are **pull-based, computed
live in the browser**:

1. The user clicks the **bell** in the systray → `showReminder()` (JS) calls
   `POST /hr_reminder/all_reminder`.
2. `all_reminder()` (controller) iterates **all** `hr.reminder` records, applies the
   `search_by` test (§4.2) against `today()`, and returns the **due** ones as
   `[{id, name}]`. These populate the `<select>` dropdown.
3. The user picks one and clicks **View** → `reminderActive()` (JS) calls
   `POST /hr_reminder/reminder_active` with `{reminder_name: <selected name>}`.
4. `reminder_active()` looks the reminder up **by `name`** (`sudo()`), and returns a flat
   **positional list**:
   `[model, field_name, search_by, date_set, date_from, date_to, id, today, ttype,
   days_before, (date_set − days_before if date_set)]`.
5. The JS reads that list by index, builds a domain on `field_name` bracketed to the day
   boundaries, and `action.doAction()` opens the target model's records in a new dialog
   (`target:'new'`, list view). The domain per mode:
   - `today`     → `field BETWEEN today 00:00:00 .. today 23:59:59`
   - `set_date`  → `field BETWEEN (date_set−days_before) 00:00:00 .. date_set 23:59:59`
   - `set_period`→ `field BETWEEN date_from 00:00:00 .. date_to 23:59:59`

> So a reminder "notifies" nobody passively — it only shows when a logged-in user opens the
> bell. If you need proactive (e-mail / activity) reminders, this module does **not** provide
> them; that would be a new feature (add an `ir.cron` + `mail.activity`/`mail.mail`).

### Controllers (`controllers/hr_reminder.py`)
| Route | Type | Auth | Returns |
|---|---|---|---|
| `/hr_reminder/all_reminder` | json | **public** | list of due reminders `[{id,name}]` |
| `/hr_reminder/reminder_active` | json | **public** | positional list describing the picked reminder (see above) |

> ⚠️ Both routes are `auth="public"`. `all_reminder` uses `request.env['hr.reminder'].search`
> (no `sudo`), so it runs as the current (possibly public) user and is subject to ACLs/record
> rules. `reminder_active` uses **`.sudo()`** and matches **by `name`** — see Gotchas.

---

## 8. Settings / config parameters
**N/A** — no `res.config.settings` inheritance and no `ir.config_parameter`. All tuning is
per-reminder record data.

---

## 9. Security (`security/`)
- **`ir.model.access.csv`** (3 lines, all on `hr.reminder`):

  | Access id | Group | R | W | C | U(nlink) |
  |---|---|---|---|---|---|
  | `access_hr_reminder_officer` | `hr.group_hr_user` (HR Officer) | ✔ | ✔ | ✔ | ✔ |
  | `access_hr_reminder_administrator` | `hr.group_hr_manager` (HR Manager) | ✔ | ✔ | ✔ | ✔ |
  | `access_hr_reminder_user` | `base.group_user` (Internal User) | ✗ | ✗ | ✗ | ✗ |

  > The internal-user row is all-zero — i.e. plain employees get **no** ORM access to
  > `hr.reminder`; only HR Officers/Managers can configure or read reminders. (The public
  > JSON controller bypasses the menu but is still ACL-gated for `all_reminder`.)
- **`hr_reminder_security.xml`** — one **global** `ir.rule`
  `hr_reminder_company_rule` (multi-company): domain
  `['|',('company_id','=',False),('company_id','child_of',[user.company_id.id])]`.
- **No custom groups** are declared by this module — it reuses standard `hr` groups.

---

## 10. Assets / JS (`static/src/…`, bundle `web.assets_backend`)
| File | Role |
|---|---|
| `js/reminder_topbar.js` | OWL `ReminderMenu` component; registered in the **`systray`** registry as `reminder_menu`. `setup()` wires `action` + `rpc` services and a `useState({all_remainders:[]})`. `showReminder()` fills the dropdown; `reminderActive()` opens the matching records. Template = `owl.reminder_menu`. |
| `xml/reminder_topbar.xml` | OWL template `owl.reminder_menu` — the bell icon + dropdown with a `<select id="reminder_select">` of reminder names and a **View** button. |
| `scss/reminder.scss` | Styles the systray dropdown (rounded corners, padding). |
| `css/notification.css` | Notification/label colours + a duplicate of the dropdown styling. |

**JS gotchas (this build / upstream code):**
- Uses **`this.env.services.rpc`** and the legacy **jQuery** `$("#reminder_select").val()`
  to read the selection. jQuery is still available in Odoo 17 backend but is deprecated; the
  `rpc` service is also legacy. Both work today but are fragile across minor upgrades.
- `reminderActive()` reads the controller's **positional return list by hard-coded indices**
  (`reminder[i+1]`, `+2`, `+3`, `+4`, `+5`, `+7`, `+10`). The loop is `for (i=0;i<1;i++)`,
  i.e. it runs exactly once — the indices are effectively absolute. **If you change the order
  or length of the list returned by `reminder_active()` in the controller, you must update
  these indices in the JS in lockstep**, or the wrong domain is built.
- The systray template renders a static `o_notification_counter` `<span>` but **nothing ever
  sets a count** — there is no unread badge number.

---

## 11. Gotchas & notes (read before debugging)
- **No cron / no push.** Reminders are only seen when a user opens the bell. See §7. This is
  the single biggest surprise for a "reminder" module.
- **Lookup by `name`, not `id`.** `reminder_active()` searches
  `[('name','=', reminder_name)]`. If two reminders share the same **Title**, the loop
  appends *both* their data into one flat list and the index math reads the **first** one's
  fields mixed with stale offsets → wrong/duplicated results. **Keep `name` unique** (there
  is no SQL/`@api.constrains` uniqueness — it is only a convention).
- **`auth="public"` + index-based contract.** The controller↔JS contract is positional and
  brittle (see §10). Treat the controller return shape as a frozen interface.
- **`set_date` domain is one-sided in practice.** Due-test is `today >= date_set − days_before`
  with no lower expiry except `expiry_date`; the opened-records domain spans
  `(date_set − days_before) .. date_set`. Records *after* `date_set` won't show.
- **`model_id` domain `like 'hr'`** matches any model whose technical name *contains* `hr`
  (e.g. `hr.*`, but also anything else with `hr` in it). It is a substring match, not a
  strict `hr.` prefix.
- **Mixed date APIs.** Controller uses both `fields.date.today()` and `fields.Date.today()`;
  comparisons are date-only while the target field may be datetime — hence the JS appends
  `00:00:00` / `23:59:59` to bracket the day.
- **Upstream module.** This is stock Cybrosys/OpenHRMS code. Prefer extending via a separate
  bridge module over editing here, so a future upstream re-sync doesn't clobber your changes.
- **`expiry_date` does not gate `today` mode** — a `today` reminder shows forever regardless
  of `expiry_date` (the field is hidden for `today` in the form anyway).
- **Translations.** `i18n/ar_001.po` ships Arabic for the UI labels
  (e.g. *Search By* → «البحث بواسطة»). The model/field technical names stay English.

---

## 12. File map
```
__manifest__.py                     depends=['hr'] · data · assets bundle
__init__.py                         imports controllers, models
controllers/
  hr_reminder.py                    2 public JSON routes (all_reminder, reminder_active)
models/
  hr_reminder.py                    hr.reminder (config-only model; no methods)
security/
  hr_reminder_security.xml          multi-company global ir.rule
  ir.model.access.csv               HR user/manager CRUD; internal user = no access
views/
  hr_reminder_views.xml             form · tree · action · top-level "Reminders" menu
static/src/
  js/reminder_topbar.js             OWL systray component (registry: systray)
  xml/reminder_topbar.xml           owl.reminder_menu template (bell + dropdown + View)
  scss/reminder.scss                dropdown styling
  css/notification.css              label/notification styling
i18n/ar_001.po                      Arabic UI translations
doc/RELEASE_NOTES.md                v17.0.1.0.0 — initial commit (28.11.2023)
static/description/                 store listing assets (banner/icon/screenshots) — not loaded by Odoo logic
README.rst
```
