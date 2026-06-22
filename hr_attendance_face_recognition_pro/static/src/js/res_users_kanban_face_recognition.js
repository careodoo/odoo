/** @odoo-module **/

/**
 * Face ENROLMENT — Odoo 17 migration.
 *
 * ORIGINAL (Odoo 13/14): `attendances_face_recognition_access.res_users_kanban_face_recognition`
 * included `web.relational_fields:FieldOne2Many` to hook the "Add face" kanban on
 * res.users / hr.employee. On save of a new image it ran Human on the uploaded
 * photo, derived the base64 descriptor + landmark-overlay image, and created a
 * res.users.image / hr.employee.image record.
 *
 * v17 STATUS: `web.relational_fields`, `web.field_registry`, `core.qweb` and the
 * `FieldOne2Many` widget were REMOVED in the OWL rewrite — there is NO host
 * widget to `.include()` any more. The one2many is now the OWL `X2ManyField`
 * component, whose save pipeline is entirely different. A faithful
 * "wrapper-only" port is therefore impossible without a full OWL re-author.
 *
 * MIGRATION DECISION (per task rule "prefer a clean, loadable result, stub the
 * advanced feature, document it"): this file is migrated to a CLEAN, LOADABLE
 * ES module that PRESERVES THE RECOGNITION ALGORITHM EXACTLY as reusable,
 * exported helpers (Human detect -> embedding -> base64 descriptor -> overlay
 * image -> create record via the v17 ORM service). The legacy auto-hook into
 * the kanban save flow is the only thing stubbed — it has no v17 host. A future
 * OWL "Add face" component can import `enrolFaceFromImage()` below and get the
 * full, unchanged pipeline.
 *
 * Algorithm (detect/embedding/match) is byte-for-byte the original; only the
 * module wrapper and the create() call (legacy `this._rpc` -> ORM service) changed.
 *
 * TODO (manual, advanced): build an OWL component / view button that calls
 * `enrolFaceFromImage(orm, model, ownerId, imageEl, record)` to restore the
 * one-click "Add face" UX. Tracked in DOCUMENTATION.md §10.
 */

import { registry } from "@web/core/registry";

const MODEL_BASE_PATH =
    "/hr_attendance_face_recognition_pro/static/src/js/models";

/** Human config used for enrolment (face detect + mesh + description). Verbatim. */
const ENROL_HUMAN_CONFIG = {
    debug: false,
    async: true,
    modelBasePath: MODEL_BASE_PATH,
    face: {
        face: { enabled: true },
        mesh: { enabled: true },
        description: { enabled: true },
        detector: { rotation: false },
        iris: { enabled: false },
        emotion: { enabled: false },
    },
    hand: { enabled: false },
    body: { enabled: false },
    object: { enabled: false },
    gesture: { enabled: false },
    segmentation: { enabled: false },
    filter: { enabled: false },
};

/** Lazily create + load a Human engine instance for enrolment. */
export async function loadEnrolModels() {
    // `Human` is the global exposed by static/src/js/lib/human.js
    const human = new Human.Human(ENROL_HUMAN_CONFIG);
    await human.load();
    return human;
}

/**
 * Serialise a Float32 embedding to base64 (33% bigger but JSON-safe).
 * Preserved verbatim from the legacy `_f32base64`.
 */
export function f32base64(descriptorArray1024) {
    return btoa(
        String.fromCharCode(
            ...new Uint8Array(new Float32Array(descriptorArray1024).buffer)
        )
    );
}

/**
 * Render Human's landmark overlay for an image and return it as a base64
 * data-URL. Preserved verbatim from the legacy `_drawDescriptor`.
 */
export async function drawDescriptor(human, image, result) {
    const img = await human.image(image);
    const canvas = img.canvas;

    const canvas2 = document.createElement("canvas");
    canvas2.width = canvas.width;
    canvas2.height = canvas.height;

    human.draw.all(canvas2, result);
    return canvas2.toDataURL();
}

/**
 * Detect a single face on a base64/<img> source and produce the descriptor
 * (base64 embedding) + overlay image. Preserved verbatim from the legacy
 * `_detectFaceFromImageBase64`.
 */
export async function detectFaceFromImageBase64(human, image) {
    const result = await human.detect(image);

    if (!result.face.length) {
        return {
            descriptorBase64: false,
            imageDescriptorBase64: false,
            error: "Not found faces",
        };
    }

    const imageDescriptorBase64 = await drawDescriptor(human, image, result);
    const descriptorBase64 = f32base64(result.face[0].embedding);

    return {
        descriptorBase64,
        imageDescriptorBase64: imageDescriptorBase64.split(",")[1],
        error: false,
    };
}

/**
 * Full enrolment pipeline: detect face on `imageEl`, compute descriptor, and
 * create the *.image record via the v17 ORM service.
 *
 * Legacy `this._rpc({model, method:'create', args:[vals]})` -> `orm.create`.
 * `model` is "res.users" or "hr.employee" (the OWNER model); the image model
 * and owner FK are derived from it exactly as the original did.
 *
 * @returns {object} { id } on success, or { error } if no face was found.
 */
export async function enrolFaceFromImage(orm, model, ownerId, imageEl, baseVals = {}) {
    const human = await loadEnrolModels();
    const res = await detectFaceFromImageBase64(human, imageEl);
    if (res.error) {
        return { error: res.error };
    }

    const vals = {
        descriptor: res.descriptorBase64,
        image_detection: res.imageDescriptorBase64,
        image: baseVals.image,
        name: baseVals.name,
        sequence: baseVals.sequence,
    };

    let imageModel = "res.users.image";
    if (model === "res.users") {
        vals.res_user_id = ownerId;
    }
    if (model === "hr.employee") {
        imageModel = "hr.employee.image";
        vals.hr_employee_id = ownerId;
    }

    const id = await orm.create(imageModel, [vals]);
    return { id };
}

/**
 * Toggle the `.only-descriptor` overlay layer. Preserved (DOM-only) from the
 * legacy `_hide_canvas_face_recognition`.
 */
export function hideCanvasFaceRecognition() {
    document.querySelectorAll(".only-descriptor").forEach((el) => {
        el.style.display = el.style.display === "none" ? "" : "none";
    });
    document
        .querySelectorAll(".o-kanban-button-hide-face-recognition")
        .forEach((btn) => {
            btn.classList.toggle("badge-success");
            btn.classList.toggle("badge-warning");
        });
}

// Expose the enrolment helpers on a private registry category so a future OWL
// "Add face" component (or other modules) can consume them without re-importing
// the whole file. This registration cannot fail at load.
registry
    .category("hr_attendance_face_recognition_pro")
    .add("enrol_helpers", {
        loadEnrolModels,
        f32base64,
        drawDescriptor,
        detectFaceFromImageBase64,
        enrolFaceFromImage,
        hideCanvasFaceRecognition,
    });
