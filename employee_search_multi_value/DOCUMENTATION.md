# employee_search_multi_value — Developer Handover Documentation

> **Employee Search Multi Value** — a tiny, OCA-derived utility module for Odoo 17.
> It adds a single virtual search field to the Employee filter bar that lets a user
> paste **several space-separated values at once** (e.g. a list of barcodes) and get
> back every employee matching *any* of them. There are **no JS widgets, no new
> stored data, no reports** — the whole feature is a server-side computed/search
> field plus a one-line search-view inheritance. Read this before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `employee_search_multi_value` |
| Display name | Employee Search Multi Value |
| Version | `17.0.1.0.1` |
| License | `AGPL-3` |
| Odoo | 17.0 |
| Depends | `hr` |
| External Python libs | None (stdlib `logging` + Odoo internals only) |
| New models | **None** — adds an `AbstractModel` mixin `hr.search.multi.mixin`, mixed into `hr.employee` |
| New stored fields | **None** — `search_multi` is a non-stored compute/search field |
| Reports / Crons / Settings UI | **N/A** (config is a single raw `ir.config_parameter`) |
| Origin | Derived from OCA (`Copyright 2020 ACSONE SA/NV`, AGPL-3) — see view header |

### Deployment (this server)
- DB: `odoo17` · service: `odoo-17.service` (systemd) · runs as user `odoo`.
- Python venv: `/home/odoo/.pyenv/versions/odoo-17-env/bin/python`
- Odoo bin: `/home/odoo/odoo-17.0+e.20241205/odoo-bin` · conf: `/home/odoo/odoo.conf`
- Addons path includes `/home/odoo/care` (this repo, branch `17`).
- **Update + restart:**
  ```bash
  sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
    /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
    -d odoo17 -u employee_search_multi_value --stop-after-init --no-http
  sudo systemctl restart odoo-17.service
  ```
- No dev mode. This module has no asset bundles (no JS/SCSS), so a plain `-u` to
  reload the Python model + the search view + the config parameter, then a restart,
  is all that is needed. Log file: `/var/log/odoo/odoo-17.log`.

---

## 2. Architecture overview

```
ir.config_parameter
  employee_search_multi_value.search_fields = ['barcode']   (data/, noupdate=1)
        │  read at search time
        ▼
hr.search.multi.mixin   (AbstractModel — models/hr.py)
  • search_multi : Char  (compute=_compute_search_multi, search=_search_multi)
  • _compute_search_multi  → always False (the field shows nothing; it's a search hook)
  • _get_search_fields     → safe_eval the config parameter → list of field names
  • _search_multi          → split input on spaces → OR(domain per field, "in" tuple)
        │  mixed into
        ▼
hr.employee  (_inherit = ['hr.employee','hr.search.multi.mixin'], _name = 'hr.employee')
        │  surfaced by
        ▼
views/hr_view.xml   inherits hr.view_employee_filter
  • adds <field name="search_multi"/> right after the existing Name search field
```

**Design principles**
- The feature is implemented as a **reusable `AbstractModel` mixin** (`hr.search.multi.mixin`)
  rather than directly on `hr.employee`. The same mixin could be mixed into any other
  model that wants the multi-value search; here only `hr.employee` uses it.
- `search_multi` is a classic **"virtual search field"** Odoo pattern: a `Char` with a
  `compute` (so it can appear in a view) and a `search=` method (so typing into it
  builds a custom domain instead of querying a stored column). It is **never stored**
  and always computes to `False` — it exists only to capture user input in the filter bar.
- **Which fields are searched is data-driven**, not hard-coded: the list comes from the
  `ir.config_parameter` `employee_search_multi_value.search_fields` (ships as `['barcode']`).

---

## 3. Data model

**No new persistent models and no new stored fields.**

### 3.1 `hr.search.multi.mixin` (`AbstractModel` — `models/hr.py`)
| Member | Type | Notes |
|---|---|---|
| `search_multi` | `Char` (label "Multiple search") | non-stored; `compute="_compute_search_multi"`, `search="_search_multi"` |
| `_compute_search_multi()` | compute | sets `search_multi = False` for all records (the field is display-only / input-only) |
| `_get_search_fields()` | `@api.model` | reads config param `employee_search_multi_value.search_fields`, `safe_eval`s it into a Python list; on `SyntaxError` logs and returns `[]` |
| `_search_multi(operator, value)` | search | builds the OR-domain (see §3.3) |

### 3.2 `hr.employee` (inherited — `models/hr.py`)
Declared as `_inherit = ["hr.employee", "hr.search.multi.mixin"]` with `_name = "hr.employee"`.
This is Odoo's **multiple-inheritance merge**: it pulls the mixin's `search_multi` field and
its methods onto the existing `hr.employee` model without creating a new model or table.
No other fields or methods are added.

### 3.3 Search semantics (`_search_multi`)
This is the core of the module — exact behaviour:

1. **Operator gate.** Only `=` and `ilike` are accepted. Both are rewritten internally to
   the `in` operator. Any other operator raises a `UserError`:
   *"Operator %s is not usable with multisearch"*. (In practice the search bar issues
   `ilike` when a user types a value, so this is the live path.)
2. **Tokenisation.** The typed string is split on spaces:
   `value_list = value.split(" ") if " " in value else [value]`.
   So `"123 456 789"` becomes `['123','456','789']`; a single token stays a one-element list.
3. **Per-field domains.** For each field name in `_get_search_fields()` (default `['barcode']`)
   it builds `[(field, 'in', tuple(value_list))]`.
4. **Combine with OR.** All per-field domains are combined with
   `odoo.osv.expression.OR`, so a row matches if **any** configured field is `in` the value list.

> Net effect with the default config: typing `"BC001 BC002 BC003"` into the
> **Multiple search** field returns the employees whose `barcode` is any of those three.

**Gotcha — `in` is exact, not fuzzy.** Because the operator is forced to `in`, matches are
**exact equality** against each whole token (not substring/`ilike`). Even though the user's
keystroke arrives as `ilike`, this module deliberately converts it to `in`. So partial
barcodes will not match. To search additional / different fields, edit the config parameter
(see §7), not the code.

---

## 4. Views (`views/hr_view.xml`)

A single inherited search view:

- **`hr_search_view`** — `model="hr.employee"`, `inherit_id="hr.view_employee_filter"`
  (the standard Employees search/filter view). It inserts
  `<field name="search_multi"/>` **immediately after** the existing `name` search field.

That places the new **"Multiple search"** input in the Employees filter bar. There are
**no new actions, menus, list/form/kanban views, or windows** — the field rides on the
stock Employees views.

The XML file carries the upstream OCA copyright header (`Copyright 2020 ACSONE SA/NV`,
AGPL-3).

---

## 5. Reports

**N/A** — the module defines no QWeb/PDF reports.

---

## 6. Crons

**N/A** — no `ir.cron` jobs.

---

## 7. Settings / configuration

There is **no `res.config.settings` UI**. Configuration is a single raw system parameter:

- **`data/search_field_data.xml`** seeds (with `noupdate="1"`) an `ir.config_parameter`:
  - key: `employee_search_multi_value.search_fields`
  - value: `['barcode']`  (a Python-literal list, `safe_eval`-ed at search time)

**To change which fields the multi-search covers** (e.g. also match work email and phone),
edit the parameter value at **Settings → Technical → System Parameters** (developer mode),
keeping it a valid Python list of `hr.employee` field names, e.g.:

```python
['barcode', 'work_email', 'mobile_phone']
```

> Because the data record is `noupdate="1"`, a module `-u` will **not** overwrite a value
> a user has changed in the DB — your runtime edits survive upgrades. To force the shipped
> default back, delete/reset the parameter manually.
>
> Each listed field must exist on `hr.employee` and be a queryable column; only use fields
> that make sense with the `in` (exact-match) operator (see §3.3).

---

## 8. Security

**N/A (no module-specific security).** The module ships no `groups.xml`,
no `ir.model.access.csv`, and no record rules. It adds no new model/table, so it relies
entirely on the **standard `hr` access control** for `hr.employee`. `_get_search_fields()`
reads the config parameter with `.sudo()` so the lookup works regardless of the searching
user's rights on `ir.config_parameter`.

---

## 9. Assets / JS

**N/A — there is no JavaScript, no OWL component, no SCSS, and no `static/` directory.**

This is the key thing to understand about the module: despite living in the "search widget"
space, **all logic is server-side Python**. The multi-value behaviour is achieved purely
through the Odoo `compute`/`search` field pattern (§3) and a search-view inheritance (§4) —
not a custom front-end widget. There is nothing to register in an asset bundle.

---

## 10. Gotchas & notes

- **`in` means exact match, not substring.** `_search_multi` forces the operator to `in`,
  so each space-separated token must equal a field value exactly. Users expecting `ilike`
  fuzzy matching will be surprised. This is intentional (it's a bulk-lookup tool, e.g. scan
  many barcodes), not a bug.
- **Space is the only delimiter.** Tokenisation is `value.split(" ")`. Commas, tabs, or
  newlines are **not** split — `"123,456"` is treated as one token. Multiple consecutive
  spaces produce empty-string tokens in the list (which simply never match).
- **Config value must be a valid Python list literal.** `_get_search_fields` `safe_eval`s
  the parameter. A malformed value raises `SyntaxError`, which is caught → logged → returns
  `[]` (so the search silently matches nothing rather than crashing). Check
  `/var/log/odoo/odoo-17.log` for *"Error while evaluating search fields"* if multi-search
  stops returning results.
- **`noupdate="1"` on the config record** — module upgrades won't clobber a user-changed
  field list (see §7). Conversely, editing the value in `search_field_data.xml` and running
  `-u` will **not** update an existing DB record; change it in System Parameters instead.
- **Mixin reuse.** `hr.search.multi.mixin` is generic. If you ever want the same bulk search
  on another model, mix it in the same way (`_inherit = ['that.model','hr.search.multi.mixin']`)
  and add a `search_multi` field to that model's search view — but note the config parameter
  key and the searched-field list are **shared/global**, so all consumers would search the
  same field names unless you refactor `_get_search_fields`.
- **OCA origin.** This is an OCA-style module (ACSONE, AGPL-3). Keep the license header if
  you redistribute, and prefer upstreaming generic fixes.

---

## 11. File map
```
__manifest__.py                  name/version/depends(hr)/data list — AGPL-3
__init__.py                      → models
models/
  __init__.py                    → hr
  hr.py                          hr.search.multi.mixin (AbstractModel) + hr.employee inherit
data/
  search_field_data.xml          ir.config_parameter search_fields = ['barcode'] (noupdate=1)
views/
  hr_view.xml                    inherits hr.view_employee_filter → adds <field search_multi/>
```
(No `security/`, `reports/`, `static/`, `wizards/`, or `data/*cron*` — see §5–§9 for the N/A items.)
