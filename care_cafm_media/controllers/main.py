# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class CafmMediaController(http.Controller):

    @http.route('/cafm/media/presign', type='json', auth='user')
    def presign(self, filename=None, content_type='application/octet-stream', **kw):
        """Client asks for a presigned PUT URL, then uploads the file DIRECTLY to
        object storage (bypassing the Odoo server entirely)."""
        return request.env['care.cafm.media'].presign_put(filename or 'file', content_type)

    @http.route('/cafm/media/register', type='json', auth='user')
    def register(self, key=None, public_url=None, res_model=None, res_id=None,
                 name=None, media_type='photo', size_kb=0, **kw):
        """After the direct upload succeeds, register the object as a media record."""
        m = request.env['care.cafm.media'].register(
            key, public_url, res_model, res_id, name, media_type, size_kb)
        return {'id': m.id, 'url': m.url}
