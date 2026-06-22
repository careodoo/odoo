/** @odoo-module **/

/**
 * Kiosk-mode face RECOGNITION — Odoo 17 migration.
 *
 * ORIGINAL (Odoo 13/14): `hr_attendance_face_recognition.kiosk_mode` did
 * `require('hr_attendance.kiosk_mode').include({...})`, loaded Human with
 * detector rotation on, RPC'd /hr_attendance_base with
 * `face_recognition_mode:'kiosk'`, and opened the shared `FaceRecognitionDialog`
 * in kiosk mode; on a match it redirected to `hr_attendance_my_attendances` for
 * the matched employee with `face_recognition_force:true`.
 *
 * v17 STATUS: `hr_attendance.kiosk_mode` (legacy AMD) DOES NOT EXIST in Odoo 17
 * — core's kiosk is the OWL `public_kiosk_app`. The sibling `hr_attendance_base`
 * kiosk host is also disabled. So, as with my_attendances, there is no host to
 * `.include()` and no legacy Dialog to reuse.
 *
 * MIGRATION DECISION: migrated to a CLEAN, LOADABLE ES module that reuses the
 * preserved, framework-agnostic `FaceRecognitionEngine` (from
 * my_attendances_face_recognition.js) and exposes a kiosk-tuned model loader +
 * the kiosk RPC helper. The recognition ALGORITHM is unchanged; only the legacy
 * client-action `.include()` glue (which has no v17 host) is dropped.
 *
 * A future OWL kiosk component can:
 *   1. `human = await loadKioskModels()`
 *   2. `data = await loadKioskData(rpc)`  // /hr_attendance_base, kiosk mode
 *   3. `engine = new FaceRecognitionEngine({ human, ...parsed, onMatch })`
 *   4. on match -> action.doAction('hr_attendance_my_attendances', {context:{
 *        employee, face_recognition_force:true, ... }})
 *
 * TODO (manual, advanced): build that OWL kiosk wrapper + redirect. Tracked in
 * DOCUMENTATION.md §10.
 */

import {
    FaceRecognitionEngine,
    parseDataFaceRecognition,
} from "@hr_attendance_face_recognition_pro/js/my_attendances_face_recognition";

const MODEL_BASE_PATH =
    "/hr_attendance_face_recognition_pro/static/src/js/models";

/** Kiosk Human config (detector rotation ON for varied angles). Verbatim. */
const KIOSK_HUMAN_CONFIG = {
    modelBasePath: MODEL_BASE_PATH,
    face: {
        enabled: true,
        detector: { rotation: true, return: true },
        mesh: { enabled: true },
        description: { enabled: true },
    },
};

/** Lazily create + load a Human engine for kiosk recognition. */
export async function loadKioskModels() {
    // `Human` global comes from static/src/js/lib/human.js
    const human = new Human.Human(KIOSK_HUMAN_CONFIG);
    await human.load();
    return human;
}

/**
 * Fetch the kiosk descriptors/settings from the controller and parse them.
 * Legacy `this._rpc({route:'/hr_attendance_base', params:{face_recognition_mode:'kiosk'}})`
 * -> the OWL `rpc` service. Returns the parsed engine settings + descriptors.
 *
 * @param {function} rpc  the v17 rpc service (useService("rpc"))
 */
export async function loadKioskData(rpc) {
    const data = await rpc("/hr_attendance_base", {
        face_recognition_mode: "kiosk",
    });
    return parseDataFaceRecognition(data);
}

// Re-export the engine so kiosk consumers import everything from one place.
export { FaceRecognitionEngine };
