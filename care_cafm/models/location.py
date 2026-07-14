# -*- coding: utf-8 -*-
import base64
import uuid
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class CafmFacility(models.Model):
    """A client site/facility under a contract/project — top of the location tree."""
    _name = 'care.cafm.facility'
    _description = 'CAFM Facility / Site'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(string='المرفق/الموقع', required=True, tracking=True, translate=True)
    code = fields.Char(string='الرمز')
    partner_id = fields.Many2one('res.partner', string='العميل', tracking=True)
    project_id = fields.Many2one('project.project', string='المشروع', tracking=True,
                                 help='ربط المرفق بمشروع في نظام إدارة المشاريع.')
    department_id = fields.Many2one('hr.department', string='القسم')
    address = fields.Char(string='العنوان')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    building_ids = fields.One2many('care.cafm.building', 'facility_id', string='المباني')
    location_ids = fields.One2many('care.cafm.location', 'facility_id', string='المواقع')
    building_count = fields.Integer(compute='_compute_counts')
    location_count = fields.Integer(compute='_compute_counts')
    workorder_count = fields.Integer(compute='_compute_counts')
    asset_count = fields.Integer(compute='_compute_counts')
    sla_compliance = fields.Float(string='التزام SLA %', compute='_compute_sla')
    wo_overdue_count = fields.Integer(string='متأخرة SLA', compute='_compute_sla')

    def _compute_sla(self):
        WO = self.env['care.cafm.workorder']
        for rec in self:
            done = WO.search([('facility_id', '=', rec.id), ('state', 'in', ('done', 'verified')),
                              ('done_datetime', '!=', False), ('deadline', '!=', False)])
            in_sla = done.filtered(lambda w: w.done_datetime <= w.deadline)
            rec.sla_compliance = (100.0 * len(in_sla) / len(done)) if done else 100.0
            rec.wo_overdue_count = WO.search_count([('facility_id', '=', rec.id), ('is_overdue', '=', True)])

    def _compute_counts(self):
        WO = self.env['care.cafm.workorder']
        Asset = self.env.get('account.asset')
        for rec in self:
            rec.building_count = len(rec.building_ids)
            rec.location_count = len(rec.location_ids)
            rec.workorder_count = WO.search_count([('facility_id', '=', rec.id)])
            rec.asset_count = (Asset.search_count([('cafm_facility_id', '=', rec.id)])
                               if Asset is not None and 'cafm_facility_id' in Asset._fields else 0)

    def action_view_locations(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('مواقع %s') % self.name,
                'res_model': 'care.cafm.location', 'view_mode': 'tree,form',
                'domain': [('facility_id', '=', self.id)],
                'context': {'default_facility_id': self.id}}

    def action_view_workorders(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('أوامر عمل %s') % self.name,
                'res_model': 'care.cafm.workorder', 'view_mode': 'tree,form,kanban',
                'domain': [('facility_id', '=', self.id)],
                'context': {'default_facility_id': self.id}}


class CafmBuilding(models.Model):
    _name = 'care.cafm.building'
    _description = 'CAFM Building'
    _order = 'facility_id, name'

    name = fields.Char(string='المبنى', required=True, translate=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True, ondelete='cascade')
    floor_ids = fields.One2many('care.cafm.floor', 'building_id', string='الأدوار')
    floor_count = fields.Integer(compute='_compute_counts')

    def _compute_counts(self):
        for rec in self:
            rec.floor_count = len(rec.floor_ids)


class CafmFloor(models.Model):
    _name = 'care.cafm.floor'
    _description = 'CAFM Floor'
    _order = 'building_id, sequence, name'

    name = fields.Char(string='الدور', required=True, translate=True)
    sequence = fields.Integer(default=10)
    building_id = fields.Many2one('care.cafm.building', string='المبنى', required=True, ondelete='cascade')
    facility_id = fields.Many2one(related='building_id.facility_id', store=True)
    location_ids = fields.One2many('care.cafm.location', 'floor_id', string='المواقع')


class CafmLocation(models.Model):
    """A room / area — the QR-tagged unit. Scanning it drives movement,
    issue-location, presence proof and the task timer."""
    _name = 'care.cafm.location'
    _description = 'CAFM Location (Room/Area)'
    _inherit = ['mail.thread']
    _order = 'facility_id, floor_id, name'

    name = fields.Char(string='الموقع/الغرفة', required=True, tracking=True, translate=True)
    code = fields.Char(string='رمز QR', required=True, copy=False, index=True,
                       default=lambda self: self._generate_code(),
                       help='الرمز الفريد المطبوع في ملصق QR — يُولَّد تلقائياً.')
    floor_id = fields.Many2one('care.cafm.floor', string='الدور', ondelete='cascade')
    building_id = fields.Many2one(related='floor_id.building_id', store=True, string='المبنى')
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', required=True,
                                  ondelete='cascade', index=True)
    location_type = fields.Selection([
        ('lobby', 'لوبي/مدخل'), ('office', 'مكتب'), ('restroom', 'دورة مياه'),
        ('corridor', 'ممر'), ('technical', 'غرفة فنية'), ('outdoor', 'خارجي/حديقة'),
        ('parking', 'موقف'), ('store', 'مخزن'), ('other', 'أخرى'),
    ], string='النوع', default='other')
    is_checkpoint = fields.Boolean(string='نقطة تفتيش (دورية)',
                                   help='تُستخدم كنقطة دورية للأمن/الجودة.')
    active = fields.Boolean(default=True)
    qr_url = fields.Char(compute='_compute_qr', string='رابط QR')
    qr_image = fields.Binary(compute='_compute_qr', string='رمز QR')
    last_scan_id = fields.Many2one('care.cafm.scan', compute='_compute_last_scan', string='آخر مسح')

    @api.depends('code')
    def _compute_qr(self):
        Report = self.env['ir.actions.report']
        for rec in self:
            rec.qr_url = ('/report/barcode/QR/%s?width=240&height=240'
                          % (rec.code or '')) if rec.code else False
            if rec.code:
                try:
                    png = Report.barcode('QR', rec.code, width=240, height=240)
                    rec.qr_image = base64.b64encode(png)
                except Exception:
                    rec.qr_image = False
            else:
                rec.qr_image = False

    def _compute_last_scan(self):
        Scan = self.env['care.cafm.scan']
        for rec in self:
            rec.last_scan_id = Scan.search([('location_id', '=', rec.id)],
                                           order='scan_datetime desc', limit=1).id

    _sql_constraints = [('code_uniq', 'unique(code)', 'رمز QR للموقع يجب أن يكون فريداً.')]

    @api.model
    def _generate_code(self):
        """A unique QR code: from the sequence when configured, else LOC-XXXXXX."""
        Seq = self.env['ir.sequence']
        code = Seq.next_by_code('care.cafm.location')
        guard = 0
        while (not code or self.sudo().search_count([('code', '=', code)])) and guard < 1000:
            code = Seq.next_by_code('care.cafm.location') or ('LOC-%s' % uuid.uuid4().hex[:8].upper())
            guard += 1
        return code or ('LOC-%s' % uuid.uuid4().hex[:8].upper())

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('code'):
                vals['code'] = self._generate_code()
        return super().create(vals_list)

    def action_generate_code(self):
        """Button: (re)generate the QR code for this location."""
        for rec in self:
            rec.code = rec._generate_code()

    def action_print_qr(self):
        return self.env.ref('care_cafm.action_report_location_qr').report_action(self)
