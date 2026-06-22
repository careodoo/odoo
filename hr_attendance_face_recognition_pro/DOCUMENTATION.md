# hr_attendance_face_recognition_pro — Developer Handover Documentation

> Third-party (EURO ODOO / Artem Shurshilov) **face-recognition attendance** add-on for
> Odoo 17. Lets employees check in / out by having their face matched against pre-enrolled
> photos in the browser. All recognition runs **client-side in JavaScript** (the
> [Human](https://github.com/vladmandic/human) TensorFlow.js library); the server only
> stores enrolment images, face **descriptors** (embeddings), tuning thresholds and the
> optional check-in/out snapshots. It plugs into `hr_attendance_base` (a sibling add-on
> that re-implements the standard My-Attendances / Kiosk client actions). UI labels are
> **English**. This file is the handover source of truth — read it before touching the code.
>
> ⚠️ **Read §10 (Assets) and §11 (Gotchas) first.** The frontend is **dormant on this
> install**: the `assets` block in `__manifest__.py` is commented out and the JS is written
> against the legacy Odoo 13/14 (`odoo.define` + `web.basic_fields`) API. As shipped on
> Odoo 17, none of the face-recognition UI loads. The Python models, controller, security
> and settings DO load and migrate cleanly.

---

## 1. At a glance

| | |
|---|---|
| Technical name | `hr_attendance_face_recognition_pro` |
| Display name | `hr attendance face recognition pro` |
| Version (manifest) | `17.0` (internal changelog tracks `15.7.2.8`) |
| Odoo | 17.0 |
| License | OPL-1 (proprietary, paid app — €122) |
| Author / site | EURO ODOO, Artem Shurshilov · https://eurodoo.com |
| Depends | `base`, `web`, **`hr_attendance_base`**, **`web_image_webcam`**, **`field_image_editor`** |
| External JS libs (bundled) | **Human** (`human.js`, TensorFlow.js face engine + `.bin/.json` models), **webcam.js** (`Webcam` jpeg-snap lib), **SweetAlert (`Swal`)**, **TensorFlow.js (`tf`)** |
| External Python libs | **None** (no `requests`/`face_recognition`/`dlib` — all ML is in-browser) |
| New models | `hr.employee.image`, `res.users.image` |
| Inherited models | `hr.attendance`, `hr.employee`, `res.users`, `res.config.settings` |
| Controller | extends `hr_attendance_base`'s `/hr_attendance_base` JSON route |
| Reports / Crons / Wizards | **N/A** (none defined) |

### Deployment (this server)
- DB: `odoo17` · service: `odoo-17.service` (systemd) · runs as user `odoo`.
- Python venv: `/home/odoo/.pyenv/versions/odoo-17-env/bin/python`
- Odoo bin: `/home/odoo/odoo-17.0+e.20241205/odoo-bin` · conf: `/home/odoo/odoo.conf`
- Addons path includes `/home/odoo/care` (this repo, branch `17`).
- **Update + restart:**
  ```bash
  sudo -u odoo /home/odoo/.pyenv/versions/odoo-17-env/bin/python \
    /home/odoo/odoo-17.0+e.20241205/odoo-bin -c /home/odoo/odoo.conf \
    -d odoo17 -u hr_attendance_face_recognition_pro --stop-after-init --no-http
  sudo systemctl restart odoo-17.service
  ```
- No dev mode. The three sibling dependencies (`hr_attendance_base`, `web_image_webcam`,
  `field_image_editor`) must be installed first — all are present under `/home/odoo/care`.
- No Python packages to `pip install` — recognition is entirely browser-side.

---

## 2. Architecture overview

```
                         BROWSER (all ML runs here)
  ┌──────────────────────────────────────────────────────────────────────┐
  │  Human (TensorFlow.js) ── face detect / embedding / antispoof          │
  │  Webcam.js ── camera capture → jpeg snapshot                           │
  │  Swal ── popups / progress                                             │
  │                                                                        │
  │  ENROLMENT (kanban "Add face")          CHECK-IN/OUT (My Attend/Kiosk) │
  │  res_users_kanban_face_recognition.js   my_attendances_face_recognition│
  │   detect face on uploaded image          + kiosk_mode_face_recognition │
  │   → embedding → base64 "descriptor"      live video → embedding        │
  │   → create *.image record                → human.match.similarity vs   │
  │                                            stored descriptors          │
  │  widget_image_recognition.js  (image widget that toggles the           │
  │   detection-overlay image)                                             │
  └───────────────┬───────────────────────────────┬──────────────────────┘
                  │ create *.image                 │ JSON /hr_attendance_base
                  ▼                                ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │ SERVER (Odoo, Python — only storage + thresholds + glue)               │
  │                                                                        │
  │ res.users      ──1:N──► res.users.image     (name,image,descriptor)    │
  │ hr.employee    ──1:N──► hr.employee.image   (name,image,descriptor)    │
  │   + face_emotion / face_gender / face_age   (per-person filters)       │
  │                                                                        │
  │ hr.attendance (inherited): stores check-in/out snapshot + FaceID html  │
  │ res.config.settings: thresholds & toggles → ir.config_parameter        │
  │ controllers.py: enriches /hr_attendance_base reply with descriptors +  │
  │                 settings the JS needs                                  │
  └──────────────────────────────────────────────────────────────────────┘
```

**Design notes**
- A **descriptor** is the Human face **embedding** (a `Float32Array`) serialised to base64
  and stored as a `Char` on the `*.image` record. Matching = cosine-style similarity between
  the live face embedding and each stored descriptor, compared in the browser.
- Two parallel enrolment models exist — one keyed to **`res.users`** (the logged-in user's
  own face, used by My-Attendances) and one keyed to **`hr.employee`** (used by Kiosk mode,
  where any employee may appear). They are byte-for-byte identical in shape.
- The server is deliberately thin: no Python face library, no AI calls. All thresholds are
  `ir.config_parameter`s read back by the controller and shipped to the JS.

---

## 3. Data model

### 3.1 `hr.attendance` (inherited — `models/hr_attendance.py`)
Adds storage for the optional visual audit trail of each punch:

| Field | Type | Notes |
|---|---|---|
| `face_recognition_image_check_in` / `_check_out` | Binary (readonly) | the Human detection-overlay image at check in / out |
| `face_recognition_access_check_in` / `_check_out` | Html (readonly) | "FaceID in" / "FaceID out" marker shown in list/form |
| `webcam_check_in` / `webcam_check_out` | Binary (readonly) | raw webcam jpeg snapshot at check in / out |

These are populated **only** when the **Face control** setting (`face_recognition_pro_store`)
is on; otherwise they stay empty and the form shows a "Disable Face recognition store image"
hint instead.

### 3.2 `hr.employee` (inherited — `models/hr_employee.py`)
| Field | Type | Notes |
|---|---|---|
| `recognition_image_ids` | O2m → `hr.employee.image` | enrolled faces for this employee (`copy=True`) |
| `face_emotion` | Selection (required, default `any`) | neutral/happy/sad/angry/fearful/disgusted/surprised/any — "emotion that must be performed for access" |
| `face_gender` | Selection (required, default `any`) | male/female/any |
| `face_age` | Selection (required, default `any`) | `20`/`30`/`40`/`50`/`60`/`70`/`any` (band upper bounds: 0-20 … 60-any) |

> The emotion/gender/age **filters are not enforced** in the shipped JS — the
> `check_face_filter` function in `my_attendances_face_recognition.js` is commented out, and
> the load configs disable the `emotion` model. Fields exist and are persisted for forward
> compatibility only. (Typo preserved from source: the `face_age` field uses `srtring=` not
> `string=`, so its label falls back to the field name.)

### 3.3 `hr.employee.image` (`models/hr_employee.py`)
`_inherit = ['image.mixin']`, `_order = 'sequence, id'`. One enrolled face photo.

| Field | Type | Notes |
|---|---|---|
| `name` | Char (required) | image label |
| `sequence` | Integer (default 10) | kanban handle order |
| `image` | Image (required) | the enrolment photo |
| `image_detection` | Image | Human's overlay render (face landmarks drawn) |
| `hr_employee_id` | M2o → `hr.employee` (`ondelete='cascade'`) | owner |
| `descriptor` | Char (readonly) | base64-encoded face embedding |

**SQL constraint** `check_descriptor`: `check(length(descriptor)>50)` — a record must carry a
real embedding; you cannot save an image whose descriptor failed to compute.

### 3.4 `res.users` (inherited — `models/res_users.py`)
Mirror of `hr.employee` above, keyed to the user: `res_users_image_ids` (O2m →
`res.users.image`), plus identical `face_emotion` / `face_gender` / `face_age`.

### 3.5 `res.users.image` (`models/res_users.py`)
Byte-for-byte identical to `hr.employee.image` but with `res_user_id` (M2o → `res.users`,
cascade) instead of `hr_employee_id`. Same `check_descriptor` SQL constraint.

### 3.6 `res.config.settings` (inherited — `models/res_config_settings.py`)
See §8 — all tuning knobs, stored as `ir.config_parameter`.

---

## 4. Controller (`controllers/controllers.py`)

`HrAttendanceWebcam` **extends** `hr_attendance_base`'s `HrAttendanceBase` and overrides its
JSON route:

```
@http.route('/hr_attendance_base', auth='user', type="json")
def index(self, **kw):
```

It calls `super().index()` then **enriches the reply** with everything the browser engine
needs:
- the six settings (access on/off, store, kiosk-auto, photo/anti-spoof check, and the two
  scale thresholds) read from `ir.config_parameter` (`sudo`);
- **`descriptor_ids`** + **`labels_ids`** — the face descriptors to match against, plus the
  label each one maps to:
  - **Kiosk mode** (`kw['face_recognition_mode'] == 'kiosk'`): every
    `hr.employee.image` with a descriptor, with `labels_ids` as **dicts**
    (`{id, attendance_state, name, hours_today, user_id}`) so the kiosk can act on any
    employee.
  - **My-Attendances** (default): only the current user's faces — first from
    `res.users.image` of `request.env.user` (label = the linked employee's id), then from
    `hr.employee.image` of that user's employee (label = the image id);
- the current user's `face_emotion` / `face_gender` / `face_age`.

> The matching of a descriptor to a label is **positional** — `descriptor_ids[i]` pairs with
> `labels_ids[i]`. Keep the two lists appended in lock-step if you edit this. In My-Attendances
> the two label sources are heterogeneous (employee id vs image id) — a latent quirk, but it
> works because there is normally one enrolment source per user.

The commented-out `/login_kiosk` route and `werkzeug` import are dead code (removed per
changelog `15.7.2.8 [DEL] del kiosk login handle`).

---

## 5. Recognition & enrolment flow (the JS)

All four JS modules use the **legacy `odoo.define(...)` API** and bundle the Human engine
from `static/src/js/lib/human.js` + the TF models under `static/src/js/models/`.

### 5.1 Enrolment — `res_users_kanban_face_recognition.js`
Includes `web.relational_fields:FieldOne2Many` for the `res.users` / `hr.employee` face
kanban ("Add face"). On save of a new image:
1. `human.detect(image)` on the uploaded photo (`_detectFaceFromImageBase64`).
2. No face → Swal warning, abort.
3. Face found → `_f32base64(embedding)` produces the base64 **descriptor**;
   `_drawDescriptor` renders the landmark overlay (→ `image_detection`).
4. `_create_image` RPCs `create` on `res.users.image` / `hr.employee.image` with
   `{descriptor, image_detection, image, name, sequence, <owner_id>}`.
5. A Swal "Face descriptor create process…" modal (with the `cat-space.gif` backdrop) covers
   the async work; the view reloads after.
- For `face_mode: 'user'`, if the user already has ≥1 image the Add button is replaced with
  *"You already set images, if you want change it, contact your Administrator"* — self-service
  enrolment is one-shot.

### 5.2 Check in/out — `my_attendances_face_recognition.js`
Includes `hr_attendance.my_attendances` (from `hr_attendance_base`).
- `start()` lazy-loads the Human models (`load_models`, with `antispoof` enabled) and parses
  the settings/descriptors from the `/hr_attendance_base` reply
  (`parse_data_face_recognition` — note descriptors are rebuilt into `Float32Array`s from
  base64). It paints the camera button green ("Face recognition ON") / red ("…no photos").
- Clicking sign-in/out (or break/resume) routes through
  `update_attendance_with_recognition` → opens **`FaceRecognitionDialog`** (template
  `WebCamDialogFaceRecognition`). If `face_recognition_enable` is off or in kiosk, it just
  calls the normal `update_attendance()`.
- **`FaceRecognitionDialog`** (the core loop):
  1. `Webcam.set/attach` a live feed; `drawVideo` paints frames onto `#ocr_canvas` every
     ~75 ms.
  2. `face_detection`: `human.detect(canvas)`; if a face is present, draw overlay, then for
     each stored descriptor:
     - **Anti-spoof gate** (if `face_recognition_pro_photo_check`): uses Human's
       `result.face[0].real`; if `< scale_spoofing/100`, skip (reject photos-of-photos).
     - **Match**: `human.match.similarity(storedDescriptor, liveEmbedding)`; if
       `100*similarity > scale_recognition` → it's a match.
  3. On match: if **store** is on, grab the webcam jpeg (`Webcam.snap`) + the Human overlay
     image and stash them on the parent (`webcam_snapshot`, `face_recognition_image`); then
     `check_in_out` fires the punch (debounced 500 ms) and returns `'stop'`.
- `antiSpoofingCheck` (a manual `tf.loadGraphModel('…/anti-spoofing.json')` path) is **present
  but unused** — the live code reads `result.face[0].real` from Human instead.

### 5.3 Kiosk — `kiosk_mode_face_recognition.js`
Includes `hr_attendance.kiosk_mode`. Loads Human (with `detector.rotation` on for varied
angles), RPCs `/hr_attendance_base` with `face_recognition_mode: 'kiosk'`, and on "Select
Employee" opens the same `FaceRecognitionDialog` in **`face_recognition_mode: 'kiosk'`**. When
a face matches, instead of punching directly it redirects to `hr_attendance_my_attendances`
for the matched employee with `face_recognition_force: true` (skip a second recognition pass).
A small `state_read → state_save → state_render` deferred handshake sequences model-load,
data-load and template-render.

### 5.4 Image widget — `widget_image_recognition.js`
Registers field widget **`image_recognition`** (extends `FieldBinaryImage`). Renders via the
`ImageRecognition-img` QWeb template and adds a **"Hide/Show faces on images"** toggle
(`.o-kanban-button-hide-face-recognition`) that hides the `.only-descriptor` overlay layer.
Sizes the snapshot 1:1 on mobile vs 600×400 on desktop. Used by the `*.image` kanban/form and
the `hr.attendance` form snapshot fields.

---

## 6. Reports
**N/A** — the module defines no QWeb/PDF reports.

## 7. Crons
**N/A** — no `ir.cron` records.

---

## 8. Settings (`res.config.settings` → Settings ▸ Attendances)

`res_config_settings_views.xml` injects a face-recognition block into the standard HR
Attendances settings page. All values persist as `ir.config_parameter`:

| Setting field | config_parameter key | Default | Meaning |
|---|---|---|---|
| `face_recognition_pro_access` | `hr_attendance_face_recognition_pro_access` | off | **master switch** — require face recognition to punch |
| `face_recognition_pro_scale_recognition` | `face_recognition_pro_scale_recognition` | **55** | similarity % to accept a match (higher = stricter), range 0-100 |
| `face_recognition_pro_store` | `hr_attendance_face_recognition_pro_store` | off | **Face control** — store snapshot + descriptor on each punch (heavy on disk) |
| `face_recognition_pro_kiosk_auto` | `hr_attendance_face_recognition_pro_kiosk_auto` | off | auto-fire check in/out the moment a face is found in kiosk |
| `face_recognition_pro_photo_check` | `face_recognition_pro_photo_check` | off | anti-spoofing — reject a photo held to the camera |
| `face_recognition_pro_scale_spoofing` | `face_recognition_pro_scale_spoofing` | **70** | anti-spoof "liveness" % threshold, 0 disables, range 0-100 |

`set_values()` writes the params and raises a `ValidationError` if either scale is outside
0-100. `get_values()` reads them back, defaulting the two scales to 55 / 70 when unset. The
sub-settings are hidden in the UI until **access** is on (and the spoof scale until **photo
check** is on).

---

## 9. Security (`security/ir.model.access.csv`)

Only ACLs — **no record rules, no new groups** (groups are reused from `hr_attendance` and
`hr_attendance_base`). Both new models (`res.users.image`, `hr.employee.image`) get:

| Group | Perms |
|---|---|
| `hr_attendance.group_hr_attendance_manager` | full CRUD |
| `hr_attendance.group_hr_attendance_user` | read/write/create, **no unlink** |
| `hr_attendance_base.group_hr_attendance_admin_pro` | full CRUD |
| `hr_attendance_base.group_hr_attendance_manager_pro` | read/write/create, no unlink |
| `hr_attendance_base.group_hr_attendance_user_pro` | **read-only** |

The **Faces** menu (`menu_hr_attendance_view_face_recognition_table`, under Attendances) is
restricted to `group_hr_attendance_manager`. Note the `hr_attendance_base.*_pro` groups are
the gating set (per changelog `15.5.2.7`). There are no record rules, so visibility of
enrolment images is by ACL only — keep this in mind if multi-company isolation is needed.

---

## 10. Assets / JS (CRITICAL)

> **The `assets` declaration in `__manifest__.py` is COMMENTED OUT** (lines ~43-61). As
> shipped, Odoo loads **none** of this module's CSS, JS libs, ML models or QWeb templates.
> The Python side (models, controller, security, settings views) loads fine, but the
> browser-side recognition does not run.

Two compounding problems for Odoo 17:
1. **Commented assets block.** It references the **legacy bundle `web.assets_qweb`** (removed
   in Odoo 15+) for `attendance.xml` / `kiosk.xml`. To enable, assets must be re-declared
   under `web.assets_backend` using current Odoo-17 asset syntax.
2. **Legacy JS API.** All four JS files use `odoo.define('name', function(require){…})` with
   `web.basic_fields`, `web.field_registry`, `web.relational_fields`, `web.core.qweb`,
   `Dialog`, deferreds (`$.Deferred`) and jQuery `t-extend` QWeb templates — the Odoo
   ≤13/14 widget framework. Odoo 17's web client is **OWL**; these modules will not load as-is
   even once the asset paths are fixed. A real revival means porting to OWL
   (`@odoo-module`, `registry`, components) — a substantial rewrite, not a path tweak.

If a working face-recognition flow is required on this Odoo 17 install, budget for that port;
do not assume uncommenting the manifest is sufficient.

**Bundled assets inventory** (present on disk, ready to be wired up):
- `static/src/js/lib/human.js` — the Human face engine (TF.js); excluded from cloc.
- `static/src/js/lib/webcam.js` (+ `webcam.swf` Flash fallback) — camera capture.
- `static/src/js/models/` — the TF model weights/manifests Human loads
  (`blazeface`, `facemesh`, `faceres`, `antispoof`, `liveness`, `emotion`, `iris`,
  `mb3-centernet`, `selfie`, `handlandmark*`, `movenet-lightning`, `centernet`, …) plus
  `models.json`. Served from `modelBasePath: '/hr_attendance_face_recognition_pro/static/src/js/models'`.
- `static/src/css/lightbox.css`, `toogle_button.css`.
- `static/src/xml/attendance.xml` (the `WebCamDialogFaceRecognition`, `ImageRecognition-img`,
  kanban-button and main-menu-camera-button templates), `static/src/xml/kiosk.xml`.
- External globals the JS assumes exist: `Human`, `Webcam`, `tf`, `Swal` (SweetAlert).

---

## 11. Gotchas & history (read before debugging)

- **Frontend is dormant on Odoo 17** — see §10. "Face recognition does nothing" is expected
  until the assets are re-declared AND the JS is ported to OWL.
- **No Python ML dependency** — everything (detect, embedding, anti-spoof, match) is in the
  browser. Don't go looking for `dlib`/`face_recognition`/`requests`; there are none.
- **`webcam.swf` is Flash** — the SWF fallback (`swfURL` in `my_attendances`) is dead in all
  modern browsers; capture relies on `getUserMedia`. Requires **HTTPS** (or `localhost`) for
  the browser to grant camera access.
- **Descriptor SQL constraint** `length(descriptor)>50` — any save of a `*.image` with a
  short/missing descriptor (e.g. detection failed, or an attempt to insert a raw photo without
  running Human) is rejected at the DB. The JS always populates it; direct SQL/imports must
  too.
- **Two enrolment models** (`res.users.image` vs `hr.employee.image`) are intentional, not
  duplication-by-accident: users-images feed My-Attendances, employee-images feed Kiosk. The
  controller reads them differently (dict labels for kiosk, positional ids for self).
- **emotion/gender/age filters are inert** — fields persist but the gating JS is commented out
  and the emotion model is disabled in the load config. Don't promise customers face-mood
  gating without re-implementing it.
- **Manual `antiSpoofingCheck` is unused** — live anti-spoof uses Human's `face[0].real`. The
  standalone `anti-spoofing.json` graph-model path exists but isn't called.
- **Positional descriptor↔label pairing** in the controller — edits that reorder/filter one
  list must mirror the other.
- **Field typo** `srtring=` on `face_age` (both models) — harmless, label falls back to field
  name; left as-is to avoid churn but worth knowing if a label "looks wrong".
- **Settings keys are inconsistent** — three use the `hr_attendance_face_recognition_pro_*`
  prefix, three use a bare `face_recognition_pro_*` prefix. Match them exactly when reading
  params elsewhere.
- **Sibling dependency load order** — `hr_attendance_base` must update first if both change;
  this module's controller subclasses its `HrAttendanceBase` and its JS includes its client
  actions.
- **Odoo shell doesn't auto-commit** — call `env.cr.commit()` for any data fix run via
  `odoo-bin shell`, or it rolls back on exit.

---

## 12. File map
```
__manifest__.py              depends/data; assets block COMMENTED OUT (see §10)
__init__.py                  → controllers, models
changelog.rst                upstream version history (15.7.2.8 latest)

controllers/
  controllers.py             extends hr_attendance_base /hr_attendance_base JSON route

models/
  hr_attendance.py           snapshot + FaceID fields on hr.attendance
  hr_employee.py             hr.employee filters + hr.employee.image model
  res_users.py               res.users filters + res.users.image model
  res_config_settings.py     6 settings → ir.config_parameter

security/
  ir.model.access.csv        ACLs for the two *.image models (no rules, no new groups)

views/
  views.xml                  res.users.image tree + Faces menu/action + hr.attendance list/form
  res_users.xml              res.users face page + image form/kanban
  hr_employee.xml            hr.employee face page + image form/kanban
  res_config_settings_views.xml   settings block

static/src/
  js/
    my_attendances_face_recognition.js     check-in/out dialog + recognition loop (legacy API)
    kiosk_mode_face_recognition.js         kiosk recognition (legacy API)
    res_users_kanban_face_recognition.js   enrolment: image → descriptor (legacy API)
    widget_image_recognition.js            'image_recognition' field widget (legacy API)
    lib/   human.js · webcam.js · webcam.swf
    models/  TF.js model weights (blazeface, facemesh, faceres, antispoof, liveness, …)
  xml/   attendance.xml · kiosk.xml   (QWeb, legacy web.assets_qweb)
  css/   lightbox.css · toogle_button.css
  description/   store assets (icon, gifs, mp4 demos, index.html)
```
