/** @odoo-module **/

/**
 * Face Attendance Kiosk — a self-contained Odoo 17 client action that wires the
 * (migration-preserved) Human/TF.js recognition engine into a working check-in
 * flow, WITHOUT patching core v17's rewritten attendance components.
 *
 * Flow:  loadRecognitionModels() -> /hr_attendance_base (kiosk descriptors)
 *        -> parseDataFaceRecognition() -> FaceRecognitionEngine.start()
 *        -> onMatch -> POST /face_attendance/punch -> show result -> resume.
 */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import {
    parseDataFaceRecognition,
    FaceRecognitionEngine,
    loadRecognitionModels,
} from "@hr_attendance_face_recognition_pro/js/my_attendances_face_recognition";

export class FaceAttendanceKiosk extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.mountRef = useRef("mount");
        this.canvasRef = useRef("canvas");
        this.state = useState({
            status: "جارٍ تحميل نماذج التعرّف…",
            lastName: "",
            lastAction: "",
            error: "",
        });
        this.engine = null;
        this.cooldown = false;

        onWillStart(async () => {
            try {
                this.human = await loadRecognitionModels();
                const raw = await this.rpc("/hr_attendance_base", {
                    face_recognition_mode: "kiosk",
                });
                this.parsed = parseDataFaceRecognition(raw);
            } catch (e) {
                this.state.error = "تعذّر تحميل بيانات التعرّف: " + (e.message || e);
            }
        });

        onMounted(() => this._start());
        onWillUnmount(() => {
            if (this.engine) {
                this.engine.stop();
            }
        });
    }

    _start() {
        if (this.state.error || !this.parsed) {
            return;
        }
        if (!this.parsed.descriptor_ids || !this.parsed.descriptor_ids.length) {
            this.state.error = "لا يوجد موظفون مسجّلون ببصمة وجهية بعد. أضِف صور الوجه من بطاقة الموظف.";
            return;
        }
        this.state.status = "وجّه وجهك نحو الكاميرا…";
        this.engine = new FaceRecognitionEngine({
            human: this.human,
            descriptorIds: this.parsed.descriptor_ids,
            labelsIds: this.parsed.labels_ids,
            settings: this.parsed,
            onMatch: (label, payload) => this._onMatch(label, payload),
        });
        this.engine.start(this.mountRef.el, this.canvasRef.el);
    }

    _resume() {
        this.cooldown = false;
        this.state.lastName = "";
        this.state.lastAction = "";
        this.state.error = "";
        this.state.status = "وجّه وجهك نحو الكاميرا…";
        if (this.engine) {
            this.engine.stopped = false;
            const video = this.mountRef.el && this.mountRef.el.querySelector("video");
            if (video) {
                this.engine.drawVideo(video, this.canvasRef.el);
            } else {
                this.engine.start(this.mountRef.el, this.canvasRef.el);
            }
        }
    }

    async _onMatch(label, payload) {
        if (this.cooldown) {
            return;
        }
        this.cooldown = true;
        const employeeId = label && (label.id !== undefined ? label.id : label);
        try {
            const res = await this.rpc("/face_attendance/punch", {
                employee_id: employeeId,
                snapshot: (payload && payload.webcamSnapshot) || false,
            });
            if (res && !res.error) {
                this.state.lastName = res.name;
                this.state.lastAction = res.action;
                this.state.status = "";
            } else {
                this.state.error = "تعذّر تسجيل الحضور.";
            }
        } catch (e) {
            this.state.error = "خطأ في تسجيل الحضور: " + (e.message || e);
        }
        setTimeout(() => this._resume(), 4000);
    }
}

FaceAttendanceKiosk.template = "hr_attendance_face_recognition_pro.FaceAttendanceKiosk";

registry.category("actions").add("face_attendance_kiosk", FaceAttendanceKiosk);
