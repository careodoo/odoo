# -*- coding: utf-8 -*-
"""Shared helper: alert the CARE 2 CARE back-office when customer-initiated
work arrives (a booking, a shop order, a contract request).

Recipients are configured per work-type on c2c.settings; an empty list means
no broadcast at all (same rule as the tender notification routing)."""
from odoo import models


class C2CTeamNotify(models.AbstractModel):
    _name = 'c2c.team.notify.mixin'
    _description = 'CARE 2 CARE — back-office alert helper'

    # subclasses override: the c2c.settings m2m field holding the recipients,
    # and the app deep-link prefix used for the push action_url.
    _notify_setting_field = None
    _notify_action_prefix = 'c2c'

    def _notify_team(self, title, body, activity=False):
        """Subscribe + chatter + push (+ optional To-Do) the configured users."""
        self.ensure_one()
        if not self._notify_setting_field or 'c2c.settings' not in self.env:
            return
        cfg = self.env['c2c.settings'].sudo().get_settings()
        if self._notify_setting_field not in cfg._fields:
            return
        users = cfg[self._notify_setting_field]
        if not users:
            return  # unconfigured = stay quiet
        partners = users.mapped('partner_id')
        if partners:
            self.message_subscribe(partner_ids=partners.ids)
            self.message_post(body=body, partner_ids=partners.ids)
        if 'care.cafm.notification' in self.env:
            try:
                self.env['care.cafm.notification'].sudo().push(
                    users, title, body, ntype='info',
                    action_url='%s/%s' % (self._notify_action_prefix, self.id))
            except Exception:
                pass
        if activity and 'activity_ids' in self._fields:
            for u in users:
                try:
                    self.activity_schedule('mail.mail_activity_data_todo',
                                           user_id=u.id, summary=title, note=body)
                except Exception:
                    pass
