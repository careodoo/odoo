odoo.define('hr_attendance_face_recognition.kiosk_mode', function (require) {
    "use strict";

    var core = require('web.core');
    var KioskMode = require('hr_attendance.kiosk_mode');
    var FaceRecognitionDialog = require('hr_attendance_face_recognition.my_attendances').FaceRecognitionDialog;


    var FaceRecognitionKioskMode = KioskMode.include({
        events: {
            "click .o_hr_attendance_button_employees": function () {
                this.start();
            },
        },
        // loaded models there for best perfomance
        load_models: async function () {
            let def = $.Deferred();
            const myConfig = {
                // backend: 'webgl',
                modelBasePath: '/hr_attendance_face_recognition_pro/static/src/js/models',
                face: {
                    enabled: true,
                    detector: { rotation: true, return: true },
                    mesh: { enabled: true },
                    description: { enabled: true },
                },
            };
            this.human = new Human.Human(myConfig);
            await this.human.load();
            def.resolve();
            return def
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
                self.face_recognition_auto = data.face_recognition_auto;
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
                //self.labels_ids_emp = JSON.parse(data.labels_ids_emp);
                self.labels_ids_emp = data.labels_ids_emp;
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

        init: function (parent, options) {
            this.promise_face_recognition = this.load_models();
            // state when end request /hr_attendance_base
            this.state_read = $.Deferred();
            // after read, we write data to memory 
            this.state_save = $.Deferred();
            // after save we render page template
            this.state_render = $.Deferred();
            // after render we bind click action on template and add map
            this._super(parent, options);
        },

        start: function () {
            var self = this;
            var def_hr_attendance_base = this._rpc({
                route: '/hr_attendance_base',
                params: {
                    face_recognition_mode: 'kiosk'
                },
            }).then(function (data) {
                self.data = data;
                self.state_read.resolve();
                self.state_save.then(function () {
                    self.state_render.resolve();
                });
            });
            self.parse_data_face_recognition();
            return $.when(def_hr_attendance_base, this._super.apply(this, arguments)).then(
                result => {
                    this.promise_face_recognition.then(
                        result => {
                            this.state_save.then(
                                result => {
                                    if (this.face_photo)
                                        new FaceRecognitionDialog(this, {
                                            labels_ids: this.labels_ids,
                                            descriptor_ids: this.descriptor_ids,
                                            labels_ids_emp: this.labels_ids_emp,
                                            // after finded redirect to my attendance 
                                            // without face recognition control
                                            face_recognition_mode: 'kiosk'
                                        }).open();
                                    else
                                        Swal.fire({
                                            title: 'No one images/photos uploaded',
                                            text: "Please go to your profile and upload 1 photo",
                                            icon: 'error',
                                            confirmButtonColor: '#3085d6',
                                            confirmButtonText: 'Ok'
                                        });
                                })
                        })
                })
        },
    });
});
