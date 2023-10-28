odoo.define('sms_notification.fields', function (require) {
"use strict";

var basic_fields = require('web.basic_fields');
var core = require('web.core');
var session = require('web.session');

var _t = core._t;

/**
 * Override of FieldPhone to add a button calling SMS composer if option activated (default)
 */

var Phone = basic_fields.FieldPhone;
Phone.include({
    /**
     * Open SMS composer wizard
     *
     * @private
     */
    _onClickSMS: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();

//        var context = session.user_context;
//        console.log('this>>', this)
//        context = _.extend({}, context, {
//            default_res_model: this.model,
//            default_res_id: parseInt(this.res_id),
//            default_to: this.value,
//            default_composition_mode: 'comment',
//        });
        var self = this;
        return this.do_action({
            title: _t('Send SMS Text Message'),
            name: _t('Send SMS Text Message'),
            type: 'ir.actions.act_window',
            res_model: 'wk.sms.sms',
            target: 'new',
            views: [[false, 'form']],
//            context: context,
        }, {
        on_close: function () {
            self.trigger_up('reload');
        }});
    },

});

return Phone;

});
