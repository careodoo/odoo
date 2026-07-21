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
        # Bookkeeping (slide expiry + stamp last_used) must NOT run on every
        # request: the app fires many parallel calls, and concurrent UPDATEs to
        # the same token row raise 'could not serialize access due to concurrent
        # update', which poisons the request's transaction and fails it. So we
        # (1) throttle to at most once/hour, and (2) write in a SEPARATE cursor
        # so a serialization clash can never break the actual API request.
        if not rec.last_used or (now - rec.last_used) > timedelta(hours=1):
            rid = rec.id
            new_expiry = now + timedelta(days=self.TOKEN_TTL_DAYS)
            try:
                with self.env.registry.cursor() as newcr:
                    newcr.execute(
                        "UPDATE care_cafm_mobile_token SET last_used=%s, expiry=%s WHERE id=%s",
                        (now, new_expiry, rid))
                    newcr.commit()
            except Exception:
                pass  # never let token bookkeeping break a valid request
        return rec.user_id

    @api.model
    def _gc_expired(self):
        """Cron: deactivate expired tokens and purge very old ones."""
        now = fields.Datetime.now()
        self.sudo().search([('expiry', '<', now), ('active', '=', True)]).write({'active': False})
        old = self.sudo().search([('expiry', '<', now - timedelta(days=60))])
        old.unlink()
