odoo.define('hr_attendance_face_recognition.my_attendances', function (require) {
    "use strict";

    var core = require('web.core');
    var Attendances = require('hr_attendance.my_attendances');
    var _t = core._t;
    var config = require('web.config');
    var Dialog = require('web.Dialog');

    var FaceRecognitionDialog = Dialog.extend({
        template: 'WebCamDialogFaceRecognition',
        init: function (parent, options) {
            options = options || {};
            options.fullscreen = config.device.isMobile;
            options.fullscreen = true;
            options.dialogClass = options.dialogClass || '' + ' o_act_window';
            options.size = 'large';
            options.title = _t("Face recognition process");
            this.labels_ids = options.labels_ids;
            this.descriptor_ids = options.descriptor_ids;
            this.labels_ids_emp = options.labels_ids_emp || [];
            // if face_recognition_mode true, after finded employee
            // call my_attendance for that employee without face_recognition
            console.log(options, 'options DIALOG')
            console.log(this)
            this.face_recognition_mode = options.face_recognition_mode;
            this.break = options.break;
            this.parent = parent;
            this._super(parent, options);
        },

        start: function () {
            let self = this;
            return this._super.apply(this, arguments).then(() => {
                Webcam.set({
                    width: document.body.scrollWidth,
                    height: document.body.scrollHeight,
                    dest_width: document.body.scrollWidth,
                    dest_height: document.body.scrollHeight,
                    image_format: 'jpeg',
                    jpeg_quality: 90,
                    force_flash: false,
                    fps: 45,
                    swfURL: '/hr_attendance_face_recognition_pro/static/src/libs/webcam.swf',
                    constraints: { optional: [{ minWidth: 600 }] }
                });
                Webcam.attach(this.$('#live_webcam')[0]);
                Webcam.on('live', (data) => {
                    self.drawVideo("video", "#ocr_canvas");
                });
            });
        },

        check_in_out: function (canvas, employee) {
            var debounced = _.debounce(() => {
                this.parent.face_recognition_access = true;

                if (this.face_recognition_mode) {
                    this.parent.do_action({
                        type: 'ir.actions.client',
                        tag: 'hr_attendance_my_attendances',
                        context: {
                            // check in/out without face recognition
                            'face_recognition_force': true,

                            'employee': employee,
                            'face_recognition_auto': this.parent.face_recognition_auto,
                            'webcam_snapshot': this.parent.webcam_snapshot,
                            'face_recognition_image': this.parent.face_recognition_image
                        },
                    });
                    return
                }
                // если нажата кнопка перерыва
                if (this.break)
                    this.parent.update_break_resume();
                else
                    this.parent.update_attendance();
            }, 500, true);
            debounced();
        },

        // check_face_filter: function (age, gender, emotion) {
        //     var age_access = false, gender_access = false, emotion_access = false;

        //     var p1 = this.parent.face_age.split('-')[0];
        //     var p2 = this.parent.face_age.split('-')[1];
        //     if (p1 === 'any')
        //         p1 = 0;
        //     if (p2 === 'any')
        //         p2 = 1000;
        //     p1 = Number(p1)
        //     p2 = Number(p2)

        //     if (age >= p1 && age <= p2)
        //         age_access = true;
        //     if (gender === this.parent.face_gender)
        //         gender_access = true;
        //     if (emotion === this.parent.face_emotion)
        //         emotion_access = true;

        //     if (this.parent.face_age === 'any-any')
        //         age_access = true;
        //     if (this.parent.face_gender === 'any')
        //         gender_access = true;
        //     if (this.parent.face_emotion === 'any')
        //         emotion_access = true;

        //     if (!age_access || !gender_access || !emotion_access)
        //         return false;
        //     return true;
        // },

        antiSpoofingCheck: async function(image){
            await tf.ready();
            // load model
            const model = await tf.loadGraphModel('/hr_attendance_face_recognition_pro/static/src/js/models/anti-spoofing.json');
            const resized = tf.image.resizeBilinear(image, [128, 128]);
            const expanded = tf.expandDims(resized, 0);
            const res = model.execute(expanded, ['activation_4']);
            return res.dataSync()[0]
        },

        face_detection: async function (video, canvas) {
            const result = await this.parent.human.detect(canvas);
            console.log(result, 'result')
            console.log(this.descriptor_ids, 'descriptor_ids')

            if (result.face.length) {
                this.parent.human.draw.all(canvas, result);

                for (let i = 0; i < this.descriptor_ids.length; i++) {
                    if (this.parent.face_recognition_pro_photo_check){
                        // let check = await this.antiSpoofingCheck(result.face[0].tensor)
                        let check = result.face[0].real;
                        console.log("check: " + check, this.parent.face_recognition_pro_scale_spoofing/100)
                        if (check < this.parent.face_recognition_pro_scale_spoofing/100)
                            continue
                        // let live = result.face[0].live;
                        // if (live < 80)
                        //     continue
                    }
                    const found = result.face[0].embedding
                    // debugger
                    const similarity = this.parent.human.match.similarity(Array.from(this.descriptor_ids[i]),found);
                    console.log(found, 'found')
                    console.log(Array.from(this.descriptor_ids[i]), 'db')
                    console.log(`face ${i} is ${100 * similarity}% simmilar`);
                    // Found employee
                    console.log(100 * similarity)
                    if (100 * similarity > this.parent.face_recognition_pro_scale_recognition) {
                        if (this.parent.face_recognition_store){
                            await Webcam.snap(data_uri => {
                                this.parent.webcam_snapshot = data_uri.split(',')[1];
                            });
                            let imageDescriptorBase64 = await this._getImageFromHuman(canvas, result);
                            this.parent.face_recognition_image = imageDescriptorBase64.split(',')[1];
                        }
                        this.check_in_out(canvas, this.labels_ids[i]);
                        return 'stop'
                    }
                }

            }
        },

        _getImageFromHuman: async function (size, result) {
            // create new canvas
            let can = document.createElement('canvas');
            can.width = size.width;
            can.height = size.height;

            // draw human output and return as image base64
            this.parent.human.draw.all(can, result);
            return can.toDataURL();
        },

        sleep: function (ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        },

        canvasGorizonCenter: function (canvas, position) {
            canvas.style.position = position;
            canvas.style.left = '50%';
            canvas.style.marginLeft = '-' + ($(canvas).width() / 2).toString() + 'px';
        },

        drawVideo: async function (sourceSelector, canvasSelector) {
            // 1. текущую картинку с тега видео
            if (Webcam.live)
                var video = this.$el.find(sourceSelector)[0];
            else
                return

            var canvas = this.$el.find(canvasSelector)[0];
            if (!canvas)
                return
            var ctx = canvas.getContext('2d');

            // если изображение с камеры слишком большое
            // уменьшаем его до размера диалогового окна
            if (video.videoWidth > this.$el.width()) {
                canvas.width = this.$el.width();
                canvas.height = (this.$el.width() * video.videoHeight) / video.videoWidth;
            }
            else {
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
            }

            this.canvasGorizonCenter(canvas, 'inherit');
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            let res = await this.face_detection(video, canvas);
            if (res == 'stop')
                return
            await this.sleep(75);
            this.drawVideo(sourceSelector, canvasSelector);
        },

        destroy: function () {
            if ($('.modal-footer .btn-primary').length)
                $('.modal-footer .btn-primary')[0].click();
            this.stop = true;
            Webcam.off('live');
            Webcam.reset();
            this._super.apply(this, arguments);
        },
    });

    var MyAttendances = Attendances.include({
        events: {
            "click .o_hr_attendance_sign_in_out_icon": _.debounce(function () {
                this.update_attendance_with_recognition();
            }, 200, true),
            "click .o_hr_attendance_break_resume_icon": _.debounce(function () {
                this.update_break_resume_with_recognition();
            }, 200, true),
            "click .o_hr_attendance_back_button": _.debounce(function () {
                this.do_action({
                    type: 'ir.actions.client',
                    tag: 'hr_attendance_kiosk_mode',
                });
            }, 200, true)
        },

        // parse data setting from server
        parse_data_face_recognition: function () {
            var self = this;

            self.state_read.then(function (data) {
                var data = self.data;
                self.face_recognition_pro_scale_recognition = data.face_recognition_pro_scale_recognition;
                self.face_recognition_pro_scale_spoofing =  data.face_recognition_pro_scale_spoofing;
                self.face_recognition_enable = data.face_recognition_enable;
                self.face_recognition_store = data.face_recognition_store;
                self.face_recognition_pro_photo_check = data.face_recognition_pro_photo_check;
                self.face_emotion = data.face_emotion;
                self.face_gender = data.face_gender;
                var age_map = {
                    '20': '0-20',
                    '30': '20-30',
                    '40': '30-40',
                    '50': '40-50',
                    '60': '50-60',
                    '70': '60-any',
                    'any': 'any-any'
                }
                if (data.face_age === 'any')
                    self.face_age = 'any-any';
                else
                    self.face_age = age_map[Math.ceil(data.face_age).toString()];

                if (!self.face_recognition_access)
                    self.face_recognition_access = false;

                self.labels_ids = data.labels_ids;
                self.descriptor_ids = [];
                for (var f32base64 of data.descriptor_ids) {
                    self.descriptor_ids.push(new Float32Array(new Uint8Array([...atob(f32base64)].map(c => c.charCodeAt(0))).buffer))
                }
                self.face_photo = true;
                if (!self.labels_ids.length || !self.descriptor_ids.length)
                    self.face_photo = false;
                self.state_save.resolve();
            });
        },

        load_models: async function () {
            let def = $.Deferred();
            const myConfig = {
                debug: false,
                async: true,
                modelBasePath: '/hr_attendance_face_recognition_pro/static/src/js/models',
                face: { // runs all face models
                    face: { enabled: true },
                    mesh: { enabled: true},
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
            this.human = new Human.Human(myConfig);
            await this.human.load();
            console.log(this.human, 'HUMAN')
            def.resolve();
            return def
        },

        start: function () {
            this.promise_face_recognition = this.load_models();
            this.promise_face_recognition.then(
                result => {
                    this.state_render.then(
                        render => {
                            console.log("models success loaded");
                            if (this.face_photo) {
                                this.$('.o_form_binary_file_web_cam').removeClass('btn-warning');
                                this.$('.o_form_binary_file_web_cam').addClass('btn-success');
                                this.$('.o_form_binary_file_web_cam').text('Face recognition ON');
                            }
                            else {
                                this.$('.o_form_binary_file_web_cam').removeClass('btn-warning');
                                this.$('.o_form_binary_file_web_cam').addClass('btn-danger');
                                this.$('.o_form_binary_file_web_cam').text('Face recognition no photos');
                            }
                        })
                })
            this.parse_data_face_recognition();
            return $.when(this._super.apply(this, arguments));
        },

        update_break_resume_with_recognition: function () {
            // if kiosk mode enable, recognition already done
            if (!this.face_recognition_enable || this.kiosk) {
                this.face_recognition_access = true;
                this.update_break_resume();
                return
            }

            this.promise_face_recognition.then(
                result => {
                    if (this.face_photo)
                        new FaceRecognitionDialog(this, {
                            labels_ids: this.labels_ids,
                            descriptor_ids: this.descriptor_ids,
                            break: true
                        }).open();
                    else
                        Swal.fire({
                            title: 'No one images/photos uploaded',
                            text: "Please go to your profile and upload 1 photo",
                            icon: 'error',
                            confirmButtonColor: '#3085d6',
                            confirmButtonText: 'Ok'
                        });
                },
                error => {
                    console.log(error);
                });
        },

        update_attendance_with_recognition: function () {
            // if kiosk mode enable, recognition already done
            if (!this.face_recognition_enable || this.kiosk) {
                this.face_recognition_access = true;
                this.update_attendance();
                return
            }

            this.promise_face_recognition.then(
                result => {
                    if (this.face_photo)
                        new FaceRecognitionDialog(this, {
                            labels_ids: this.labels_ids,
                            descriptor_ids: this.descriptor_ids
                        }).open();
                    else
                        Swal.fire({
                            title: 'No one images/photos uploaded',
                            text: "Please go to your profile and upload 1 photo",
                            icon: 'error',
                            confirmButtonColor: '#3085d6',
                            confirmButtonText: 'Ok'
                        });
                },
                error => {
                    console.log(error);
                });
        }

    });
    return { FaceRecognitionDialog: FaceRecognitionDialog }
});