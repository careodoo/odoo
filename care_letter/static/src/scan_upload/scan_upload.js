/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useRef, useState, useEffect, onWillUnmount } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class ScanUploadField extends Component {
    static template = "care_letter.ScanUpload";
    static props = { ...standardFieldProps };

    setup() {
        this.state = useState({ camera: false, error: "" });
        this.videoRef = useRef("video");
        this.fileRef = useRef("file");
        this.stream = null;

        // attach the camera stream once the <video> element is rendered
        useEffect(
            () => {
                if (this.state.camera && this.videoRef.el && this.stream) {
                    this.videoRef.el.srcObject = this.stream;
                    this.videoRef.el.play().catch(() => {});
                }
            },
            () => [this.state.camera]
        );
        onWillUnmount(() => this._stopCamera());
    }

    get value() {
        return this.props.record.data[this.props.name];
    }
    get imgSrc() {
        const v = this.value;
        return v ? `data:image/png;base64,${v}` : false;
    }

    _toBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(String(reader.result).split(",")[1]);
            reader.onerror = reject;
            reader.readAsDataURL(file);
        });
    }

    triggerFile() {
        if (this.fileRef.el) {
            this.fileRef.el.click();
        }
    }

    async onFile(ev) {
        const file = ev.target && ev.target.files && ev.target.files[0];
        if (!file) {
            return;
        }
        const b64 = await this._toBase64(file);
        await this.props.record.update({ [this.props.name]: b64 });
        ev.target.value = "";
    }

    async _getStream() {
        // Prefer the rear camera (mobile), but fall back to ANY available camera (desktop webcam).
        try {
            return await navigator.mediaDevices.getUserMedia({
                video: { facingMode: { ideal: "environment" } }, audio: false });
        } catch (e) {
            return await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        }
    }

    async startCamera() {
        this.state.error = "";
        try {
            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
                throw Object.assign(new Error("nomedia"), { name: "NotSupported" });
            }
            this.stream = await this._getStream();
            this.state.camera = true;
        } catch (e) {
            const name = e && e.name;
            if (name === "NotFoundError" || name === "OverconstrainedError" || name === "NotSupported" || name === "DevicesNotFoundError") {
                this.state.error = "لا توجد كاميرا متصلة بهذا الجهاز. استخدم زر «اختيار ملف» لرفع صورة السكان (امسح المستند ببرنامج السكانر ثم اختر الملف).";
            } else if (name === "NotAllowedError" || name === "PermissionDeniedError") {
                this.state.error = "تم رفض إذن الكاميرا. اسمح للموقع باستخدام الكاميرا من إعدادات المتصفح، أو استخدم «اختيار ملف».";
            } else {
                this.state.error = "تعذّر فتح الكاميرا: " + (e.message || e) + " — يمكنك استخدام «اختيار ملف».";
            }
        }
    }

    async capture() {
        const v = this.videoRef.el;
        if (!v) {
            return;
        }
        const canvas = document.createElement("canvas");
        canvas.width = v.videoWidth || 1280;
        canvas.height = v.videoHeight || 720;
        canvas.getContext("2d").drawImage(v, 0, 0, canvas.width, canvas.height);
        const b64 = canvas.toDataURL("image/png").split(",")[1];
        await this.props.record.update({ [this.props.name]: b64 });
        this._stopCamera();
    }

    _stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach((t) => t.stop());
            this.stream = null;
        }
        this.state.camera = false;
    }

    async clearImg() {
        await this.props.record.update({ [this.props.name]: false });
    }
}

export const scanUploadField = {
    component: ScanUploadField,
    displayName: "Scan / Upload",
    supportedTypes: ["binary"],
};

registry.category("fields").add("scan_upload", scanUploadField);
