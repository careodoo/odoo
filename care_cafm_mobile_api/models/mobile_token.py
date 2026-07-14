# -*- coding: utf-8 -*-
import secrets
from datetime import timedelta
from odoo import api, fields, models


class MobileToken(models.Model):
    """A bearer token issued to a user's device for the native mobile app.
    Stateless-ish: the app stores the token; each request presents it in the
    Authorization header. Tokens expire and can be revoked (active=False)."""
    _name = 'care.cafm.mobile.token'
    _description = 'CAFM Mobile Auth Token'
    _order = 'create_date desc'
    _rec_name = 'user_id'

    user_id = fields.Many2one('res.users', string='المستخدم', required=True,
                              ondelete='cascade', index=True)
    token = fields.Char(string='الرمز', required=True, index=True, copy=False)
    device = fields.Char(string='الجهاز')
    expiry = fields.Datetime(string='ينتهي في', required=True)
    last_used = fields.Datetime(string='آخر استخدام')
    active = fields.Boolean(default=True)

    _sql_constraints = [('token_uniq', 'unique(token)', 'الرمز يجب أن يكون فريداً.')]

    # Token lifetime (days). Kept generous for a field app; refreshed on use.
    TOKEN_TTL_DAYS = 30

    @api.model
    def issue(self, user, device=None):
        """Create and return a fresh token record for the given user."""
        rec = self.sudo().create({
            'user_id': user.id,
            'token': secrets.token_urlsafe(48),
            'device': (device or '')[:128],
            'expiry': fields.Datetime.now() + timedelta(days=self.TOKEN_TTL_DAYS),
        })
        return rec

    @api.model
    def resolve(self, raw_token):
        """Return the res.users for a valid, unexpired token — or None.
        Also slides the expiry forward and stamps last_used (keeps active
        field devices logged in)."""
        if not raw_token:
            return None
        rec = self.sudo().search([('token', '=', raw_token), ('active', '=', True)], limit=1)
        if not rec:
            return None
        now = fields.Datetime.now()
        if rec.expiry and rec.expiry < now:
            rec.active = False
            return None
        rec.write({'last_used': now,
                   'expiry': now + timedelta(days=self.TOKEN_TTL_DAYS)})
        return rec.user_id

    @api.model
    def _gc_expired(self):
        """Cron: deactivate expired tokens and purge very old ones."""
        now = fields.Datetime.now()
        self.sudo().search([('expiry', '<', now), ('active', '=', True)]).write({'active': False})
        old = self.sudo().search([('expiry', '<', now - timedelta(days=60))])
        old.unlink()
