# -*- coding: utf-8 -*-
import base64
import logging
import uuid
from odoo import fields, models, api, _

_logger = logging.getLogger(__name__)


class CafmMedia(models.Model):
    """A media reference (photo/video/before-after) stored EXTERNALLY (S3/R2) —
    the record keeps only the URL, never the binary, so the server/DB stay light."""
    _name = 'care.cafm.media'
    _description = 'CAFM Media (external)'
    _order = 'create_date desc, id desc'

    name = fields.Char(string='الاسم')
    media_type = fields.Selection([
        ('photo', 'صورة'), ('before', 'قبل'), ('after', 'بعد'),
        ('video', 'فيديو'), ('document', 'مستند'),
    ], string='النوع', default='photo')
    url = fields.Char(string='الرابط', required=True, help='رابط الملف على التخزين الخارجي.')
    thumbnail_url = fields.Char(string='المصغّرة')
    object_key = fields.Char(string='مفتاح الكائن')
    external = fields.Boolean(string='تخزين خارجي', default=True)
    size_kb = fields.Integer(string='الحجم (KB)')
    workorder_id = fields.Many2one('care.cafm.workorder', ondelete='cascade', index=True)
    observation_id = fields.Many2one('care.cafm.observation', ondelete='cascade', index=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    # ---------- external storage helpers ----------
    @api.model
    def _cfg(self, key, default=''):
        return self.env['ir.config_parameter'].sudo().get_param('care_cafm_media.' + key, default)

    @api.model
    def _s3_client(self):
        import boto3
        return boto3.client(
            's3',
            endpoint_url=self._cfg('endpoint_url') or None,
            region_name=self._cfg('region') or None,
            aws_access_key_id=self._cfg('access_key'),
            aws_secret_access_key=self._cfg('secret_key'))

    @api.model
    def _external_enabled(self):
        return self._cfg('backend') == 's3' and self._cfg('bucket') and self._cfg('access_key')

    @api.model
    def presign_put(self, filename, content_type='application/octet-stream'):
        """Return a presigned PUT URL so the mobile app/portal uploads the file
        DIRECTLY to object storage — it never passes through the Odoo server."""
        if not self._external_enabled():
            return {'error': _('التخزين الخارجي غير مُهيّأ — أدخل بيانات S3/R2 في الإعدادات.')}
        bucket = self._cfg('bucket')
        key = 'cafm/%s-%s' % (uuid.uuid4().hex[:12], filename)
        try:
            url = self._s3_client().generate_presigned_url(
                'put_object',
                Params={'Bucket': bucket, 'Key': key, 'ContentType': content_type},
                ExpiresIn=3600)
        except Exception as e:
            _logger.warning('CAFM presign failed: %s', e)
            return {'error': str(e)}
        public = (self._cfg('public_base_url') or '').rstrip('/') + '/' + key
        return {'upload_url': url, 'key': key, 'public_url': public}

    @api.model
    def register(self, key, public_url, res_model=None, res_id=None, name=None,
                 media_type='photo', size_kb=0):
        """Register an already-uploaded external object as a media record."""
        vals = {'name': name or key, 'url': public_url, 'object_key': key,
                'media_type': media_type, 'external': True, 'size_kb': size_kb}
        if res_model == 'care.cafm.workorder':
            vals['workorder_id'] = int(res_id)
        elif res_model == 'care.cafm.observation':
            vals['observation_id'] = int(res_id)
        return self.create(vals)

    @api.model
    def store_binary(self, b64data, filename, res_model=None, res_id=None, media_type='photo'):
        """Upload a base64 file: to S3/R2 if configured (direct, no DB binary),
        else fall back to an ir.attachment (still a URL, not a binary on the record)."""
        raw = base64.b64decode(b64data or b'')
        size_kb = int(len(raw) / 1024)
        if self._external_enabled():
            bucket = self._cfg('bucket')
            key = 'cafm/%s-%s' % (uuid.uuid4().hex[:12], filename)
            try:
                self._s3_client().put_object(Bucket=bucket, Key=key, Body=raw)
                public = (self._cfg('public_base_url') or '').rstrip('/') + '/' + key
                return self.register(key, public, res_model, res_id, filename, media_type, size_kb)
            except Exception as e:
                _logger.warning('CAFM S3 put failed, falling back: %s', e)
        # fallback: attachment (kept out of the business record; served by URL)
        att = self.env['ir.attachment'].create({
            'name': filename, 'datas': b64data, 'res_model': res_model or False,
            'res_id': int(res_id) if res_id else 0, 'public': True})
        url = '/web/content/%s?download=false' % att.id
        vals = {'name': filename, 'url': url, 'external': False, 'media_type': media_type,
                'size_kb': size_kb}
        if res_model == 'care.cafm.workorder':
            vals['workorder_id'] = int(res_id)
        elif res_model == 'care.cafm.observation':
            vals['observation_id'] = int(res_id)
        return self.create(vals)


class Workorder(models.Model):
    _inherit = 'care.cafm.workorder'
    media_ids = fields.One2many('care.cafm.media', 'workorder_id', string='الوسائط')
    media_count = fields.Integer(compute='_compute_media')

    def _compute_media(self):
        for r in self:
            r.media_count = len(r.media_ids)


class Observation(models.Model):
    _inherit = 'care.cafm.observation'
    media_ids = fields.One2many('care.cafm.media', 'observation_id', string='الوسائط')
    media_count = fields.Integer(compute='_compute_media')

    def _compute_media(self):
        for r in self:
            r.media_count = len(r.media_ids)


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    cafm_media_backend = fields.Selection([
        ('odoo', 'داخل Odoo (افتراضي)'), ('s3', 'تخزين خارجي S3/R2'),
    ], string='تخزين وسائط CAFM', default='odoo',
        config_parameter='care_cafm_media.backend')
    cafm_media_endpoint = fields.Char('S3 Endpoint URL', config_parameter='care_cafm_media.endpoint_url')
    cafm_media_region = fields.Char('S3 Region', config_parameter='care_cafm_media.region')
    cafm_media_bucket = fields.Char('S3 Bucket', config_parameter='care_cafm_media.bucket')
    cafm_media_access_key = fields.Char('Access Key', config_parameter='care_cafm_media.access_key')
    cafm_media_secret_key = fields.Char('Secret Key', config_parameter='care_cafm_media.secret_key')
    cafm_media_public_base = fields.Char('Public Base URL (CDN)', config_parameter='care_cafm_media.public_base_url')
