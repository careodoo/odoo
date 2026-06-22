/** @odoo-module **/

/**
 * Check-in/out face RECOGNITION loop — Odoo 17 migration.
 *
 * ORIGINAL (Odoo 13/14): `hr_attendance_face_recognition.my_attendances`
 *   - `FaceRecognitionDialog = web.Dialog.extend({...})` : the live camera +
 *     recognition loop (Webcam feed -> canvas -> Human detect -> anti-spoof
 *     gate -> similarity match -> punch).
 *   - `MyAttendances = require('hr_attendance.my_attendances').include({...})` :
 *     hooked the My-Attendances client action to load Human models, parse the
 *     /hr_attendance_base descriptors and open the dialog on sign in/out.
 *
 * v17 STATUS: BOTH hosts are gone.
 *   - `web.Dialog` (the legacy jQuery dialog) was removed; dialogs are now the
 *     OWL `@web/core/dialog/dialog:Dialog` component.
 *   - `hr_attendance.my_attendances` (the legacy AMD client action) DOES NOT
 *     EXIST in Odoo 17 — core's attendance UI was fully rewritten in OWL
 *     (`public_kiosk_app`, `attendance_menu`, check_in_out components) with a
 *     completely different API. There is nothing to `.include()`.
 *   - The sibling `hr_attendance_base` that actually provided the
 *     `MyAttendances` host has its OWN assets intentionally DISABLED on v17
 *     (its JS was never ported) — so the host chain is doubly absent.
 *
 * MIGRATION DECISION (per task rule "preserve the recognition algorithm; stub
 * the broken glue; keep it clean & loadable"): this file is migrated to a
 * CLEAN, LOADABLE ES module that PRESERVES THE RECOGNITION ALGORITHM EXACTLY as
 * a self-contained, framework-agnostic `FaceRecognitionEngine` class plus the
 * descriptor-parsing / model-loading helpers. The Human/TF.js capture ->
 * embedding -> anti-spoof -> similarity-match logic is byte-for-byte the
 * original. Only the legacy *glue* (web.Dialog chrome, the MyAttendances
 * `.include()`, `$.Deferred`, jQuery `$(...)`) is replaced/stubbed because it
 * has no v17 host.
 *
 * A future OWL recognition dialog can `new FaceRecognitionEngine(...)`, mount a
 * <canvas>, call `engine.start(canvasEl)` and receive the matched label via the
 * `onMatch` callback — the entire recognition pipeline unchanged.
 *
 * TODO (manual, advanced): wrap `FaceRecognitionEngine` in an OWL Dialog
 * component and bind it to core v17's check-in/out flow. Tracked in
 * DOCUMENTATION.md §10/§11.
 */

const MODEL_BASE_PATH =
    "/hr_attendance_face_recognition_pro/static/src/js/models";

/** Human config for the recognition loop (face + mesh + antispoof + description). Verbatim. */
const RECOGNITION_HUMAN_CONFIG = {
    debug: false,
    async: true,
    modelBasePath: MODEL_BASE_PATH,
    face: {
        face: { enabled: true },
        mesh: { enabled: true },
        antispoof: { enabled: true },
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

/**
 * Lazily create + load a Human engine for recognition. Replaces the legacy
 * `load_models` ($.Deferred) with a plain async/await — same config, same models.
 */
export async function loadRecognitionModels(config = RECOGNITION_HUMAN_CONFIG) {
    // `Human` global comes from static/src/js/lib/human.js
    const human = new Human.Human(config);
    await human.load();
    return human;
}

/**
 * Parse the /hr_attendance_base reply into engine settings + Float32 descriptors.
 * Preserved verbatim from the legacy `parse_data_face_recognition` (minus the
 * $.Deferred handshake, which the OWL host owns now).
 */
export function parseDataFaceRecognition(data) {
    const ageMap = {
        20: "0-20",
        30: "20-30",
        40: "30-40",
        50: "40-50",
        60: "50-60",
        70: "60-any",
        any: "any-any",
    };

    let faceAge;
    if (data.face_age === "any") {
        faceAge = "any-any";
    } else {
        faceAge = ageMap[Math.ceil(data.face_age).toString()];
    }

    const descriptorIds = [];
    for (const f32base64 of data.descriptor_ids || []) {
        descriptorIds.push(
            new Float32Array(
                new Uint8Array([...atob(f32base64)].map((c) => c.charCodeAt(0)))
                    .buffer
            )
        );
    }

    const labelsIds = data.labels_ids || [];

    return {
        face_recognition_pro_scale_recognition:
            data.face_recognition_pro_scale_recognition,
        face_recognition_pro_scale_spoofing:
            data.face_recognition_pro_scale_spoofing,
        face_recognition_enable: data.face_recognition_enable,
        face_recognition_store: data.face_recognition_store,
        face_recognition_pro_photo_check: data.face_recognition_pro_photo_check,
        face_emotion: data.face_emotion,
        face_gender: data.face_gender,
        face_age: faceAge,
        labels_ids: labelsIds,
        descriptor_ids: descriptorIds,
        // ON only if we actually have at least one label+descriptor
        face_photo: !!(labelsIds.length && descriptorIds.length),
    };
}

/**
 * FaceRecognitionEngine — the live capture + recognition loop, extracted from
 * the legacy `FaceRecognitionDialog` with the algorithm UNCHANGED.
 *
 * @param {object} opts
 * @param {object} opts.human       a loaded Human engine
 * @param {Float32Array[]} opts.descriptorIds   stored embeddings to match against
 * @param {Array}  opts.labelsIds   labels positionally paired with descriptorIds
 * @param {object} opts.settings    { face_recognition_pro_photo_check,
 *                                    face_recognition_pro_scale_spoofing,
 *                                    face_recognition_pro_scale_recognition,
 *                                    face_recognition_store }
 * @param {function} opts.onMatch   called (label, { webcamSnapshot, faceImage }) on a match
 */
export class FaceRecognitionEngine {
    constructor(opts) {
        this.human = opts.human;
        this.descriptorIds = opts.descriptorIds || [];
        this.labelsIds = opts.labelsIds || [];
        this.settings = opts.settings || {};
        this.onMatch = opts.onMatch || function () {};
        this.stopped = false;
    }

    sleep(ms) {
        return new Promise((resolve) => setTimeout(resolve, ms));
    }

    /**
     * Manual TF.js anti-spoof path. PRESENT BUT UNUSED — the live code reads
     * Human's `result.face[0].real` instead (kept verbatim for parity).
     */
    async antiSpoofingCheck(image) {
        await tf.ready();
        const model = await tf.loadGraphModel(
            "/hr_attendance_face_recognition_pro/static/src/js/models/anti-spoofing.json"
        );
        const resized = tf.image.resizeBilinear(image, [128, 128]);
        const expanded = tf.expandDims(resized, 0);
        const res = model.execute(expanded, ["activation_4"]);
        return res.dataSync()[0];
    }

    /** Render Human's overlay to a fresh canvas and return a base64 data-URL. Verbatim. */
    async getImageFromHuman(size, result) {
        const can = document.createElement("canvas");
        can.width = size.width;
        can.height = size.height;
        this.human.draw.all(can, result);
        return can.toDataURL();
    }

    /**
     * Core recognition step on one canvas frame. ALGORITHM PRESERVED VERBATIM:
     * detect -> (anti-spoof gate) -> similarity match -> on match grab snapshot
     * + overlay and fire onMatch. Returns 'stop' when a match fires.
     */
    async faceDetection(canvas) {
        const settings = this.settings;
        const result = await this.human.detect(canvas);

        if (result.face.length) {
            this.human.draw.all(canvas, result);

            for (let i = 0; i < this.descriptorIds.length; i++) {
                if (settings.face_recognition_pro_photo_check) {
                    const check = result.face[0].real;
                    if (check < settings.face_recognition_pro_scale_spoofing / 100) {
                        continue;
                    }
                }
                const found = result.face[0].embedding;
                const similarity = this.human.match.similarity(
                    Array.from(this.descriptorIds[i]),
                    found
                );
                // Found employee
                if (100 * similarity > settings.face_recognition_pro_scale_recognition) {
                    const payload = { webcamSnapshot: null, faceImage: null };
                    if (settings.face_recognition_store) {
                        await Webcam.snap((dataUri) => {
                            payload.webcamSnapshot = dataUri.split(",")[1];
                        });
                        const imageDescriptorBase64 = await this.getImageFromHuman(
                            canvas,
                            result
                        );
                        payload.faceImage = imageDescriptorBase64.split(",")[1];
                    }
                    this.onMatch(this.labelsIds[i], payload);
                    return "stop";
                }
            }
        }
    }

    /**
     * Drive the live loop: paint the webcam <video> onto `canvasEl`, run
     * faceDetection ~every 75ms until a match (or stop). PRESERVED from the
     * legacy `drawVideo`, retargeted to a plain canvas element + the Webcam global.
     */
    async drawVideo(videoEl, canvasEl) {
        if (this.stopped) {
            return;
        }
        if (!Webcam.live || !videoEl || !canvasEl) {
            return;
        }
        const ctx = canvasEl.getContext("2d");

        const maxWidth = canvasEl.parentElement
            ? canvasEl.parentElement.clientWidth
            : videoEl.videoWidth;
        if (videoEl.videoWidth > maxWidth) {
            canvasEl.width = maxWidth;
            canvasEl.height = (maxWidth * videoEl.videoHeight) / videoEl.videoWidth;
        } else {
            canvasEl.width = videoEl.videoWidth;
            canvasEl.height = videoEl.videoHeight;
        }

        ctx.drawImage(videoEl, 0, 0, canvasEl.width, canvasEl.height);
        const res = await this.faceDetection(canvasEl);
        if (res === "stop") {
            return;
        }
        await this.sleep(75);
        this.drawVideo(videoEl, canvasEl);
    }

    /**
     * Attach the webcam to `mountEl`, paint frames onto `canvasEl`, and run the
     * recognition loop. PRESERVED from the legacy dialog `start`.
     */
    start(mountEl, canvasEl) {
        this.stopped = false;
        Webcam.set({
            width: document.body.scrollWidth,
            height: document.body.scrollHeight,
            dest_width: document.body.scrollWidth,
            dest_height: document.body.scrollHeight,
            image_format: "jpeg",
            jpeg_quality: 90,
            force_flash: false,
            fps: 45,
            swfURL:
                "/hr_attendance_face_recognition_pro/static/src/libs/webcam.swf",
            constraints: { optional: [{ minWidth: 600 }] },
        });
        Webcam.attach(mountEl);
        Webcam.on("live", () => {
            const videoEl = mountEl.querySelector("video");
            this.drawVideo(videoEl, canvasEl);
        });
    }

    /** Tear down the webcam + loop. PRESERVED from the legacy dialog `destroy`. */
    stop() {
        this.stopped = true;
        try {
            Webcam.off("live");
            Webcam.reset();
        } catch (e) {
            // webcam may not be attached yet
        }
    }
}
