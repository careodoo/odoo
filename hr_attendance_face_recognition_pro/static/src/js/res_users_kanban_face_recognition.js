odoo.define('attendances_face_recognition_access.res_users_kanban_face_recognition', function (require) {
    "use strict";

    var core = require('web.core');
    var QWeb = core.qweb;
    var FieldOne2Many = require('web.relational_fields').FieldOne2Many;

    var BtnDescriptionFieldOne2Many = FieldOne2Many.include({
        init: function (parent, name, record, options) {
            this._super.apply(this, arguments);
            if (this.model == 'res.users' || this.model == 'hr.employee')
                this.promise_face_recognition = this.load_models();
        },

        _openFormDialog: function (params) {
            if ((this.model == 'res.users'|| this.model == 'hr.employee') && this.view.arch.tag === 'kanban') {
                var context = this.record.getContext(_.extend({},
                    this.recordParams,
                    { additionalContext: params.context }
                ));
                this.trigger_up('open_one2many_record', _.extend(params, {
                    domain: this.record.getDomain(this.recordParams),
                    context: context,
                    field: this.field,
                    fields_view: this.attrs.views && this.attrs.views.form,
                    parentID: this.value.id,
                    viewInfo: this.view,
                    deletable: this.activeActions.delete && params.deletable,
                    on_saved: async record => {
                        await this._progressbar(record, '_save_custom');
                    },
                }));
            }
            else
                this._super.apply(this, arguments);
        },

        _detectFaceFromImageBase64: async function (image) {
            const result = await this.human.detect(image);

            if (!result.face.length)
                return {
                    descriptorBase64: false,
                    imageDescriptorBase64: false,
                    error: 'Not found faces'
                }
            
            // if (result.face[0].real )
            let imageDescriptorBase64 = await this._drawDescriptor(image, result);
            let descriptorBase64 = this._f32base64(result.face[0].embedding)

            return {
                descriptorBase64: descriptorBase64,
                imageDescriptorBase64: imageDescriptorBase64.split(',')[1],
                error: false
            }
        },

        _save_custom: async function (record) {
            if (_.some(this.value.data, { id: record.id })) {
                await this._setValue({ operation: 'UPDATE', id: record.id });
            }
            else {
                var image = $('#face-recognition-image img')[0];
                let res = await this._detectFaceFromImageBase64(image)
                if (res.error) {
                    Swal.close();
                    Swal.fire({
                        title: 'Ooops',
                        html: 'Dont found face on image, please select other or crop face manually',
                        type: "warning",
                    });
                    return
                }

                record.data.descriptor = res.descriptorBase64
                record.data.image_detection = res.imageDescriptorBase64

                //this._setValue({ operation: 'CREATE', id: record.id, data:record.data });
                await this._create_image(record)
                await this._setValue({ operation: 'UPDATE', id: record.id });
                Swal.close();
                // location.reload();
                this.trigger_up('reload');
            }
        },

        _renderButtons: function () {
            if (this.activeActions.create) {
                if ((this.model == 'res.users'|| this.model == 'hr.employee') && !this.isReadonly && this.view.arch.tag === 'kanban') {
                    this.$buttons = $(QWeb.render('KanbanView.buttons', {
                        btnClass: 'btn-secondary',
                        create_text: this.nodeOptions.create_text,
                        model: this.field.relation,
                        face_mode: this.nodeOptions.face_mode,
                    }));
                    this.$buttons.on('click', 'button.o-kanban-button-new', this._onAddRecord.bind(this));
                    this.$buttons.on('click', 'button.o-kanban-button-hide-face-recognition', this._hide_canvas_face_recognition.bind(this));
                    if (this.nodeOptions.face_mode == 'user' && this.record.data.res_users_image_ids.count > 0)
                        this.$buttons = "<div>You already set images, if you want change it, contact your Administrator</div>";
                }
            }
            this._super.apply(this, arguments);
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
            def.resolve();
            return def
        },

        _hide_canvas_face_recognition: function () {
            $('.only-descriptor').toggle("slow", function () { });
            $('.o-kanban-button-hide-face-recognition').toggleClass('badge-success');
            $('.o-kanban-button-hide-face-recognition').toggleClass('badge-warning');
        },

        _progressbar: function (record, func) {
            return Swal.fire({
                title: 'Face descriptor create process...',
                html: 'I will close in automaticaly',
                timerProgressBar: true,
                allowOutsideClick: false,
                type: "info",
                backdrop: `
                rgba(0,0,123,0.0)
                url("/hr_attendance_face_recognition_pro/static/description/cat-space.gif")
                left top
                no-repeat
              `,
                willOpen: () => {
                    Swal.showLoading()
                    this[func](record);
                },
                willClose: () => {
                }
            });
        },

        _drawDescriptor: async function (image, result) {
            const img = await this.human.image(image);
            const canvas = img.canvas;

            let canvas2 = document.createElement('canvas');
            canvas2.width = canvas.width;
            canvas2.height = canvas.height;

            this.human.draw.all(canvas2, result);
            return canvas2.toDataURL();
        },

        _f32base64: function (descriptorArray1024) {
            // descriptor from float32 to base64 33% more data
            // console.log('BEFORE: ', descriptorArray1024)
            let f32base64 = btoa(String.fromCharCode(...(new Uint8Array(new Float32Array(descriptorArray1024).buffer))));
            // console.log('AFTER: ', new Float32Array(new Uint8Array([...atob(f32base64)].map(c => c.charCodeAt(0))).buffer))
            return f32base64;
        },

        // _save_descriptor: function (userImageID, descriptor, image_detection) {
        //     let modelImage = 'res.users.image';
        //     if (this.model == 'hr.employee')
        //         modelImage = 'hr.employee.image';
        //     return this._rpc({
        //         model: modelImage,
        //         method: 'write',
        //         args: [[userImageID], {
        //             descriptor: this._f32base64(descriptor),
        //             image_detection: image_detection,
        //         }],
        //     }).then(function () {
        //         console.log('descriptor success save');
        //     });
        // },

        _create_image: function (record) {
            let data = record.data;
            let vals = {
                descriptor: data.descriptor,
                image_detection: data.image_detection,
                image: data.image,
                name: data.name,
                sequence: data.sequence
            }

            let modelImage = 'res.users.image';
            if (this.model == 'res.users')
                vals.res_user_id = record.context.default_res_user_id
    
            if (this.model == 'hr.employee'){
                modelImage = 'hr.employee.image';
                vals.hr_employee_id = record.context.default_hr_employee_id
            }

            console.log(record, '_create_image');
            return this._rpc({
                model: modelImage,
                method: 'create',
                args: [vals],
            }).then(function () {
                Swal.close();
                console.log('descriptor success create');
            });
        },
    });


});