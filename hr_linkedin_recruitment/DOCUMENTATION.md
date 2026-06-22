# hr_linkedin_recruitment — Developer Handover Documentation

> **Advanced HR-LinkedIn Integration** — a third-party **Cybrosys** connector for Odoo 17
> that lets an HR recruiter **share a job position (`hr.job`) to LinkedIn** via OAuth 2.0,
> then **pull back the likes/comments** on the shared post. It extends `hr.job` and
> `auth.oauth.provider`, adds a small `linkedin.comments` store, and exposes LinkedIn
> credentials in the Recruitment settings. UI is English. This file is the single source of
> truth for handover — read it before touching the code.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `hr_linkedin_recruitment` |
| Display name | Advanced HR-LinkedIn Integration |
| Version | `17.0.1.0.0` |
| Odoo | 17.0 |
| Author / License | Cybrosys Techno Solutions · LGPL-3 (third-party addon, **not** in-house) |
| Depends | `hr_recruitment`, `auth_oauth` |
| External Python libs | **`mechanize`**, **`linkedin`** (imported as `linkedin_v2`), plus `requests` (stdlib `json`, `logging`, `urllib`) |
| Inherited models | `hr.job`, `auth.oauth.provider`, `res.config.settings` |
| New model | `linkedin.comments` |
| External service | **LinkedIn REST API v2 / OAuth 2.0** (`api.linkedin.com`, `www.linkedin.com/oauth/v2`) |
| Controllers | 1 public HTTP route — `/linkedin/redirect` (OAuth callback) |
| Reports / Crons | **N/A** (none defined) |

### Deployment (this server)
- DB: `odoo17` · service: `odoo-17.service` (systemd) · runs as user `odoo`.
- Python venv: `/home/odoo/.pyenv/versions/odoo-17-env/bin/python`
- Odoo bin: `/home/odoo/odoo-17.0+e.20241205/odoo-bin` · conf: `/home/odoo/odoo.conf`
- Addons path includes `/home/odoo/care` (this repo, branch `17`).
- **Update + restart:**
  ```bash
  sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
    /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
    -d odoo17 -u hr_linkedin_recruitment --stop-after-init --no-http
  sudo systemctl restart odoo-17.service
  ```
- No dev mode. Log file: `/var/log/odoo/odoo-17.log`.
- ⚠️ **External Python deps must exist in the venv** (`mechanize`, `linkedin`). They are
  imported in a `try/except ImportError` that only **logs** — the module still installs
  without them, but the share flow will break at runtime. See §11 Gotchas.

---

## 2. Architecture overview

```
                         ┌──────────────────────────────────────────┐
                         │  hr.job  (inherited — models/hr_job.py)   │
                         │  fields: access_token, update_key,        │
                         │  comments, like_comment, post_likes,      │
                         │  post_commands                            │
                         └──────────────────────────────────────────┘
                            │ share_linkedin()        ▲ likes_comments()
                            │ (button)                │ (button)
                            ▼                         │
   1. Authorize redirect → www.linkedin.com/oauth/v2/authorization
      (response_type=code, client_id, redirect_uri=/linkedin/redirect, state=hr.job.id)
                            │
                            ▼
   2. LinkedIn redirects back → /linkedin/redirect   (controller, auth='public')
      ┌──────────────────────────────────────────────────────────────────────┐
      │ LinkedinSocial.social_linkedin_callbacks (controller/...py)           │
      │  • exchange code → access_token (oauth/v2/accessToken)                │
      │  • read client_id/secret from auth.oauth.provider 'provider_linkedin' │
      │  • read username/password from ir.config_parameter                    │
      │  • GET /v2/userinfo → person URN (sub)                                │
      │  • POST /v2/ugcPosts → publish job name as a LinkedIn post            │
      │  • store access_token + '+' + post-id back on hr.job.access_token     │
      │  • redirect user back to the hr.job form                              │
      └──────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
   3. likes_comments() → GET /v2/socialActions/{urn}            (likes/comments counts)
                       → GET /v2/socialActions/{urn}/comments   (each comment text)
                            │
                            ▼
            ┌───────────────────────────────────────────┐
            │ linkedin.comments (new model)             │
            │  post_id, comments_id, linkedin_comments  │
            └───────────────────────────────────────────┘

   auth.oauth.provider (inherited)  +  client_secret field
   res.config.settings (inherited)  →  ir.config_parameter recruitment.li_username / li_password
```

**Design notes**
- Credentials are split across **two stores**: the OAuth **`client_id` / `client_secret`**
  live on the `auth.oauth.provider` record `provider_linkedin`; the LinkedIn **account
  username / password** live as `ir.config_parameter` keys set from Recruitment Settings.
- The composite `access_token` field encodes **two values joined by `+`**:
  `"<access_token>+<post_urn/id>"`. Everything downstream `.split('+')` to recover them.
- The post body is simply the **job name** (`hr.job.name`); there is no rich content / media.

---

## 3. Data model

### 3.1 `hr.job` (inherited — `models/hr_job.py`, class `HrJobShare`)
| Field | Type | Notes |
|---|---|---|
| `update_key` | Char (readonly) | set truthy after a successful share; hides the Share button |
| `access_token` | Char | composite `"<token>+<post-id>"` written by the controller |
| `comments` | Boolean (default False) | toggles visibility of the **Like/Comments** header button (set True by `share_linkedin`) |
| `like_comment` | Boolean (default False) | toggles visibility of the Likes/Comments/View smart buttons (set True by `likes_comments`) |
| `post_likes` | Integer | total likes on the shared post |
| `post_commands` | Integer | total comments on the shared post (note the misspelling "commands") |

**Methods:**
- `_get_linkedin_post_redirect_uri()` — `url_join(base_url, '/linkedin/redirect')`.
  ⚠️ contains a leftover `print('url', ...)` debug statement.
- `share_linkedin()` — button. Sets `comments=True`, reads `client_id`/`client_secret`
  from the `provider_linkedin` record (raises `ValidationError` if empty), builds the
  LinkedIn **authorization** URL with a large `scope` string and `state=self.id`, returns an
  `ir.actions.act_url` (target `self`) to send the browser to LinkedIn.
- `share_request(method, url, access_token, data)` — generic LinkedIn HTTP POST helper
  (`oauth2_access_token` param, 60s timeout). Returns the `requests` response.
- `get_urn(method, url, access_token)` — generic GET helper (used by the controller to hit
  `/v2/userinfo`).
- `user_response_like()` — **stub**, returns nothing (the "Likes" smart button is display-only).
- `likes_comments()` — button. Sets `like_comment=True`, splits `access_token` on `+` to get
  the post URN, GETs `/v2/socialActions/{urn}` → fills `post_likes` / `post_commands`, then
  GETs `/v2/socialActions/{urn}/comments` and **creates `linkedin.comments` rows** for each
  new comment (dedup against existing `comments_id`). Uses `LinkedIn-Version: 202308`.
- `user_response_commends()` — button → opens the `linkedin.comments` tree filtered to this
  post (`domain=[('post_id','=',self.id)]`).
- `view_shared_post()` — GETs `/v2/me`, reads `vanityName`, returns an `act_url` to the
  member's LinkedIn `recent-activity` page.

### 3.2 `linkedin.comments` (new — `models/linkedin_comments.py`)
Plain model (no `_inherit`). Stores retrieved comments.
| Field | Type | Notes |
|---|---|---|
| `post_id` | Integer | the `hr.job` id the comment belongs to (raw int, **not** a Many2one) |
| `comments_id` | Char | LinkedIn comment id (used for dedup) |
| `linkedin_comments` | Char | the comment text |

### 3.3 `auth.oauth.provider` (inherited — `models/auth_outh_provider.py`)
Adds one field so LinkedIn (and similar apps that need a secret) can store it:
| Field | Type | Notes |
|---|---|---|
| `client_secret` | Char | "Only need LinkedIn, Twitter etc.." |

> Filename is `auth_outh_provider.py` — note the **misspelling** ("outh"), keep it when importing.

### 3.4 `res.config.settings` (inherited — `models/recruitment_config.py`)
Two transient fields backed by `ir.config_parameter` (prefix `recruitment.`):
| Field | config_parameter key | Notes |
|---|---|---|
| `li_username` | `recruitment.li_username` | LinkedIn account username |
| `li_password` | `recruitment.li_password` | LinkedIn account password (masked in the view) |

`set_values()` / `get_values()` are overridden to persist/read those two params.

### 3.5 `models/mechanize_op.py`
**No Odoo model.** Defines a `MechanizeRedirectHandler` subclass of
`mechanize.HTTPRedirectHandler` that rewrites 301/302/303/307/refresh redirects and short-
circuits any redirect leaving `www.linkedin.com`. Wrapped in `try/except ImportError`
(warns only). **Not referenced anywhere else in the module** — dead/legacy scaffolding from
the old `python-linkedin` login flow. Imported by `models/__init__.py`? — **No**, it is not
in `models/__init__.py`, so it is never loaded by Odoo at all.

---

## 4. Controller (`controller/hr_linkedin_recruitment.py`)

Single class `LinkedinSocial(http.Controller)` with one route:

| Route | Type | Auth | Method |
|---|---|---|---|
| `/linkedin/redirect` | `http`, `website=True` | **`public`** | `social_linkedin_callbacks` |

**Flow** (this is the OAuth callback LinkedIn calls after the user authorizes):
1. Parse `code` and `state` from the query string (`state` carries the `hr.job` id).
2. POST `code` + `client_id`/`client_secret` + `redirect_uri` to
   `https://www.linkedin.com/oauth/v2/accessToken` → extract `access_token`.
3. Read `client_id`/`client_secret` from `provider_linkedin` (raise `ValidationError` if
   empty); read `recruitment.li_username` / `recruitment.li_password` from
   `ir.config_parameter` (raise if missing).
4. GET `https://api.linkedin.com/v2/userinfo` → person URN (`sub`).
5. POST a `ugcPosts` payload (author = `urn:li:person:<sub>`, `shareCommentary.text` =
   the job name, visibility PUBLIC) to `https://api.linkedin.com/v2/ugcPosts`.
6. On HTTP **201** write `access_token + '+' + <post id>` back to the job and set
   `update_key=True`. 404/409/other raise `Warning`.
7. Build a `LinkedInAuthentication` object (from the `linkedin_v2` lib) — **its result is
   never used** (legacy / dead).
8. Redirect the browser back to the `hr.job` form (`web#id=…&model=hr.job&action=…`).

> ⚠️ The route is `auth='public'` and performs privileged writes — see §11.

---

## 5. Views (`views/`)

| File | Inherits | What it adds |
|---|---|---|
| `hr_job_linkedin_likes_comments_views.xml` | `hr.view_hr_job_form` | A `<header>` with **Share on LinkedIn** (`share_linkedin`, hidden once `update_key` set) and **Like/Comments** (`likes_comments`, hidden until `comments`) buttons; hidden technical fields after `department_id`; three smart buttons in the button box: **Likes** (`user_response_like`), **Comments** (`user_response_commends`), **View Posts** (`view_shared_post`) — all gated `invisible="not like_comment"`, `groups="base.group_user"`. |
| `linkedin_comments_views.xml` | — | Tree view for `linkedin.comments` (`create="false"`, shows `linkedin_comments`) + window action **"Post Comments"**. |
| `oauth_views.xml` | `auth_oauth.view_oauth_provider_form` | Shows the new `client_secret` field after `client_id` on the OAuth provider form. |
| `recruitment_config_settings.xml` | `hr_recruitment.res_config_settings_view_form` | Adds a **"LinkedIn Credentials"** section (username + password) after the `recruitment_process_div` block in Recruitment Settings. |

> No standalone menu items are defined; the **"Post Comments"** action exists but is not
> attached to a menu (reached via the job form's Comments smart button).

---

## 6. Reports
**N/A** — the module defines no QWeb / PDF reports.

## 7. Crons
**N/A** — the module defines no `ir.cron` jobs. Likes/comments are pulled **on demand** by
clicking the Like/Comments button; nothing runs on a schedule.

---

## 8. Settings & configuration (credentials)

Three pieces of configuration are required before the share flow works:

1. **OAuth app credentials** — on the LinkedIn OAuth provider record
   (`data/auth_linkedin_data.xml`, `xml_id = hr_linkedin_recruitment.provider_linkedin`,
   `noupdate="1"`). Set via **Settings → Users & Companies → OAuth Providers → LinkedIn**:
   - `client_id` (standard `auth.oauth.provider` field)
   - `client_secret` (added by this module — see §3.3)
   The seed record presets `auth_endpoint`, `scope`
   (`r_basicprofile r_emailaddress w_share w_member_social`),
   `validation_endpoint` / `data_endpoint` (`https://api.linkedin.com/v2/me`),
   `css_class` (`fa fa-linkedin-square`), and `body` ("Share post with LinkedIn").
   > Note: the actual authorize-request scope is **hard-coded in `share_linkedin()`** and is
   > much broader than the seed `scope` field (see §11).

2. **LinkedIn account credentials** — via **Settings → Recruitment → LinkedIn Credentials**:
   - `li_username` → `ir.config_parameter` `recruitment.li_username`
   - `li_password` → `ir.config_parameter` `recruitment.li_password`
   The controller **raises a `ValidationError`** if either is missing.

3. **Redirect URI** — automatically `<web.base.url>/linkedin/redirect`
   (`_get_linkedin_post_redirect_uri`). This exact URL must be whitelisted in the LinkedIn
   developer app's "Authorized redirect URLs". `web.base.url` must be correct/public.

| config_parameter key | Set from | Purpose |
|---|---|---|
| `recruitment.li_username` | Recruitment Settings | LinkedIn login username |
| `recruitment.li_password` | Recruitment Settings | LinkedIn login password |
| `web.base.url` | core (System Parameters) | builds the OAuth redirect URI |

---

## 9. Security (`security/ir.model.access.csv`)
A single ACL line:
- `linkedin.comments` → CRUD (read/write/create/unlink) for **`base.group_user`** (all
  internal users).

No record rules, no custom groups. The inherited models (`hr.job`, `auth.oauth.provider`,
`res.config.settings`) rely on the access already defined by `hr_recruitment` / `auth_oauth`
/ base. Buttons in the job view are gated `groups="base.group_user"`.

---

## 10. Assets / JS
**N/A** — no OWL components, no JS/SCSS, no `assets` bundle. `static/description/*` is only
the Odoo App Store listing (icon, banner, screenshots) and is **not loaded** by the running
app.

---

## 11. Gotchas & notes (read before debugging)

- **External libs are soft dependencies in code but hard at runtime.** `mechanize` and
  `linkedin_v2` are imported under `try/except ImportError` that only logs. The manifest
  lists `external_dependencies.python = ['mechanize', 'linkedin']`, so Odoo will **refuse to
  install** unless those are importable. Install into the venv:
  `/home/odoo/.pyenv/versions/odoo-17-env/bin/pip install mechanize python-linkedin`.
  The controller imports `from linkedin_v2 import linkedin` — confirm that the installed
  package exposes the `linkedin_v2` namespace.
- **`mechanize_op.py` and the `linkedin` lib are effectively dead code.** `mechanize_op.py`
  is not in `models/__init__.py` (never imported). The `LinkedInAuthentication` object built
  in the controller is never used. The real work is plain `requests` calls. You can ignore
  both when debugging the live flow, but **do not remove `mechanize`/`linkedin` from the
  manifest** without also removing the imports, or installs that have the libs will be fine
  while the lint/CI expectations shift.
- **LinkedIn API has changed since this was written (2024).** It targets API
  `LinkedIn-Version: 202308`/`202208`, `r_basicprofile`/`w_share` scopes and `/v2/ugcPosts`.
  LinkedIn has since deprecated several of these (UGC Posts → Posts API, `r_liteprofile`,
  legacy social-actions). Expect to revisit scopes, versions, and endpoints if shares start
  failing with 4xx. The authorize scope string in `share_linkedin()` requests **partner-only
  scopes** (`r_ads`, `r_organization_admin`, …) that a normal app cannot obtain.
- **`access_token` is a composite.** It is stored as `"<token>+<post-id>"`. All readers do
  `.split('+')[0]` (token) / `[1]` (post urn). If you change the format, update every reader
  in `hr_job.py` and the controller.
- **Public route doing privileged work.** `/linkedin/redirect` is `auth='public'` yet writes
  to `hr.job` and reads credentials. It trusts the `state` query param as an `hr.job` id with
  no ownership check. Treat as a security review item if hardening.
- **Stored LinkedIn password in plaintext config param.** `recruitment.li_password` is a
  System Parameter (readable by admins). The settings field masks it in the UI only.
- **Leftover debug `print`** in `_get_linkedin_post_redirect_uri()` — harmless but noisy in
  the log; remove if cleaning up.
- **`raise Warning(...)`** in the controller uses the bare builtin `Warning`, not an Odoo
  exception — it surfaces as a 500, not a friendly dialog.
- **Misspelled identifiers are load-bearing:** model file `auth_outh_provider.py`, field
  `post_commands` (means comments), method `user_response_commends`. Match them exactly.
- This is an **unmodified third-party Cybrosys addon** (LGPL-3). There is no in-house
  customization layer; upstream updates would overwrite it.

---

## 12. File map
```
__manifest__.py                  depends (hr_recruitment, auth_oauth), data list, external_deps
__init__.py                      → controller, models
controller/
  hr_linkedin_recruitment.py     /linkedin/redirect OAuth callback (share post)
models/
  __init__.py                    → auth_outh_provider, hr_job, linkedin_comments, recruitment_config
  hr_job.py                      hr.job inherit: share / likes_comments / smart buttons
  linkedin_comments.py           linkedin.comments model (post_id, comments_id, text)
  auth_outh_provider.py          auth.oauth.provider inherit: + client_secret
  recruitment_config.py          res.config.settings inherit: li_username / li_password
  mechanize_op.py                MechanizeRedirectHandler — NOT imported (dead code)
data/
  auth_linkedin_data.xml         provider_linkedin auth.oauth.provider seed (noupdate)
security/
  ir.model.access.csv            linkedin.comments CRUD for base.group_user
views/
  hr_job_linkedin_likes_comments_views.xml   job form: Share/Like buttons + smart buttons
  linkedin_comments_views.xml                comments tree + "Post Comments" action
  oauth_views.xml                            OAuth provider form: client_secret
  recruitment_config_settings.xml            Recruitment settings: LinkedIn Credentials
doc/
  requirment.txt                 external pip deps note (mechanize, python-linkedin)
  RELEASE_NOTES.md               v17.0.1.0.0 initial commit
static/description/              App Store listing assets (icon/banner/screenshots) — not loaded
README.rst
```
