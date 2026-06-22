# ent_hr_payroll_extension — Developer Handover Documentation

> **Enterprise OHRMS Payroll Extension** — a small third-party Open HRMS / Cybrosys
> add-on for Odoo 17. Despite the broad "payroll extension features" description in its
> manifest, the **installed code does exactly one thing**: it seeds a single payroll
> **salary structure** record (`Regular Pay`) tied to the standard *Employee* structure
> type, with unpaid leave wired in as the unpaid work-entry type. There is **no Python
> model code, no views, no wizards, no reports, no security, and no JS** in this build.
> UI labels are English. Read this before assuming the module carries more logic than it
> does — most of the heavy lifting is provided by the upstream `hr_payroll` /
> `hr_contract` modules it depends on.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `ent_hr_payroll_extension` |
| Display name | `Hr Payroll Extension` |
| Version | `17.0` (manifest); `doc/RELEASE_NOTES.md` still reads `15.0.1.0.0` — stale, not updated for the v17 port |
| Odoo | 17.0 Enterprise |
| Author / origin | Cybrosys Techno Solutions / Open HRMS (`https://www.openhrms.com`) |
| License | `OPL-1` (Odoo Proprietary License v1.0) |
| Category | `Generic Modules/Human Resources` |
| `application` | `True` (shows as an app, but ships no menus/actions of its own) |
| Depends | `base`, `hr`, `hr_payroll`, `hr_contract` |
| External Python libs | **None** |
| New models | **None** (no `models/` directory; `__init__.py` imports nothing) |
| Data records | **1** — `hr.payroll.structure` (`Regular Pay`) in `data/data_payroll.xml` |
| Views / wizards / reports / security / JS | **N/A** — none present |

### Deployment (this server)
- DB: `odoo17` · service: `odoo-17.service` (systemd) · runs as user `odoo`.
- Python venv: `/home/odoo/.pyenv/versions/odoo-17-env/bin/python`
- Odoo bin: `/home/odoo/odoo-17.0+e.20241205/odoo-bin` · conf: `/home/odoo/odoo.conf`
- Addons path includes `/home/odoo/care` (this repo, branch `17`).
- **Update + restart:**
  ```bash
  sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
    /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
    -d odoo17 -u ent_hr_payroll_extension --stop-after-init --no-http
  sudo systemctl restart odoo-17.service
  ```
- No dev mode. There are no JS/SCSS/XML asset bundles in this module, so the only effect
  of `-u` is to (re)apply the data record. Log file: `/var/log/odoo/odoo-17.log`.
- **Re-running `-u` is safe and idempotent**: the data record is loaded via the standard
  (updatable) `<data>` block, so on each update Odoo overwrites the `Regular Pay`
  structure back to the values in the XML. See the Gotchas section regarding manual edits
  being reverted.

---

## 2. Architecture overview

This is a **data-only module**. It contributes no executable code; it relies entirely on
the upstream payroll/contract framework. The full picture:

```
ent_hr_payroll_extension  (manifest + 1 data file — NO Python models)
│
├── __init__.py            (license header only — imports NOTHING)
├── __manifest__.py        (depends: base, hr, hr_payroll, hr_contract)
│
└── data/data_payroll.xml
        └── creates 1 record:
            hr.payroll.structure  id=structure_002  name="Regular Pay"
              ├─ type_id   → hr_contract.structure_type_employee   (Employee structure type)
              ├─ unpaid_work_entry_type_ids  (4,…) →
              │      hr_work_entry_contract.work_entry_type_unpaid_leave
              └─ country_id = False  (country-agnostic structure)

Upstream framework this plugs into (provided by depends, NOT this module):
  hr_payroll        → hr.payroll.structure, hr.payslip, salary rules, payslip run
  hr_contract       → hr.contract, hr.payroll.structure.type
  hr_work_entry_contract (transitive via hr_payroll) → hr.work.entry.type
```

**Design principle (such as it is):** the module exists purely to register a ready-made
"Regular Pay" salary structure so that contracts/payslips have something to select out of
the box. All payroll computation — salary rules, payslip generation, work entries — comes
from the standard Odoo `hr_payroll`/`hr_contract` apps.

---

## 3. Data model

**N/A — this module defines no Odoo models.** There is no `models/` directory, and
`__init__.py` contains only the Cybrosys/OPL-1 license header with **no import
statements**, so nothing is registered with the ORM.

The only persistent artifact it creates is a **record of an existing model**
(`hr.payroll.structure`, owned by upstream `hr_payroll`):

### 3.1 The seeded record — `hr.payroll.structure` `Regular Pay`
File: `data/data_payroll.xml` · XML id: `ent_hr_payroll_extension.structure_002`

| Field | Value | Meaning |
|---|---|---|
| `name` | `Regular Pay` | display name of the salary structure |
| `type_id` | `hr_contract.structure_type_employee` | links to the standard **Employee** `hr.payroll.structure.type` (so contracts of the Employee type can use this structure) |
| `unpaid_work_entry_type_ids` | `(4, ref('hr_work_entry_contract.work_entry_type_unpaid_leave'))` | adds the standard **Unpaid leave** work-entry type to the structure's set of unpaid types (used by payroll to know which work entries are unpaid) |
| `country_id` | `False` | structure is **not** tied to any country (generic / Kuwait-agnostic) |

> The `(4, id)` ORM command **links** the existing unpaid-leave work-entry type without
> removing anything else. On every `-u` this is re-asserted.

**Salary rules / payslip / contract inherits:** **N/A.** This module adds **no** new
salary rules, **no** payslip or contract model inherits, and **no** rule categories. How
amounts flow on a payslip (basic, allowances, deductions, net) is entirely determined by
the salary rules attached upstream to whichever structure is in use — this add-on only
makes the `Regular Pay` structure *exist* and be selectable. If `Regular Pay` carries no
salary rules of its own (none are defined here), payslips generated against it will
produce no computed lines until rules are added through the standard Payroll UI or another
module.

---

## 4. Views & wizards
**N/A.** No `views/` or `wizards/` directories. The module ships no forms, lists, search
views, menus, actions, or wizards. The seeded structure is managed through the standard
Payroll app screens (Payroll → Configuration → Salary Structures).

## 5. Reports
**N/A.** No `reports/` directory and no `ir.actions.report` records.

## 6. Crons / automation
**N/A.** No `ir.cron` records and no server actions.

## 7. Settings / config parameters
**N/A.** No `res.config.settings` inherit and no `ir.config_parameter` usage.

## 8. Security — groups & access
**N/A.** No `security/` directory, no `groups.xml`, and **no `ir.model.access.csv`**.
Because the module declares no models of its own, it needs no ACLs; access to the seeded
`hr.payroll.structure` record is governed by the upstream `hr_payroll` module's security
(Payroll Officer / Manager groups).

## 9. Assets / JS
**N/A.** No `assets` key in the manifest and no `static/src` code. The `static/` tree
contains **only marketing/description artwork** for the Odoo Apps store listing —
`static/description/` (`banner.png`, `icon.png`, `index.html`, and the `assets/icons/*`
and `images/*` PNG/GIF files). None of these are loaded into any Odoo asset bundle and
none affect runtime behaviour.

---

## 10. Gotchas & notes (read before debugging)

- **Stale version metadata.** Manifest says `17.0` but `README.rst` and
  `doc/RELEASE_NOTES.md` still describe **V15** ("Enterprise OHRMS Payroll Extension V15",
  "Version 15.0.1.0.0", links to Odoo 15 docs, and even an AGPLv3 license note that
  contradicts the manifest's `OPL-1`). Treat the README/RELEASE_NOTES as historical noise;
  the **manifest is authoritative** (`17.0`, `OPL-1`).
- **README over-promises.** `README.rst` claims "Added Advance Fields On Employee Master"
  and the description says "payroll extension features" — **neither is true in this
  build**. There are no employee-master field additions and no model code at all. The only
  real effect is the single `Regular Pay` salary-structure record.
- **XML id vs. name mismatch.** The record's XML id is `structure_002` but its `name` is
  `Regular Pay`. Don't assume `structure_002` is a second of several structures — it is the
  only record this module ships.
- **Updates revert manual edits.** The record lives inside a normal `<data>` block (not
  `noupdate="1"`), so any change a user makes to `Regular Pay` (its type, country, or
  unpaid work-entry types) in the UI will be **overwritten on the next `-u`** of this
  module. If you intend the seeded values to be a one-time default that users may edit
  freely, wrap the record in `<data noupdate="1">`.
- **External-ref load order.** The data file references `hr_contract.structure_type_employee`
  and `hr_work_entry_contract.work_entry_type_unpaid_leave`. Both come from the dependency
  chain (`hr_contract` is a direct dependency; `hr_work_entry_contract` is pulled in
  transitively via `hr_payroll`). If either upstream module fails to install, this
  module's data load will raise a missing-external-id error.
- **No salary rules here.** If payroll on the `Regular Pay` structure comes out empty,
  that is expected — this module supplies the *structure shell* only, not the rules that
  compute basic/allowances/deductions/net. Add rules through the Payroll UI or a separate
  module.
- **Minor XML formatting quirk.** `data/data_payroll.xml` has leading-whitespace
  indentation before the `<odoo>` root and a slightly unusual closing-tag layout. This is
  cosmetic and parses fine; no action needed.

---

## 11. File map
```
__manifest__.py              name/version/depends + the single data file
__init__.py                  license header ONLY — imports nothing (no models)
README.rst                   STALE (describes the V15 release; over-promises features)
doc/RELEASE_NOTES.md         STALE (Version 15.0.1.0.0, 18.10.2021)
data/
  data_payroll.xml           the ONE record: hr.payroll.structure "Regular Pay"
static/description/          Apps-store marketing only (banner/icon/index.html + icons/, images/)
                             — NOT loaded into any Odoo asset bundle

(no models/ · no views/ · no wizards/ · no reports/ · no security/ · no static/src/)
```
