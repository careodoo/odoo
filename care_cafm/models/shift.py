# -*- coding: utf-8 -*-
import math
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CafmFacilityGeo(models.Model):
    _inherit = 'care.cafm.facility'

    geo_lat = fields.Float(string='خط العرض', digits=(10, 7))
    geo_lng = fields.Float(string='خط الطول', digits=(10, 7))
    geo_radius = fields.Integer(string='نطاق الوردية (متر)', default=200,
                                help='المسافة المسموح بها من مركز الموقع لفتح الوردية.')


class CafmBuildingDesign(models.Model):
    """Design attributes that drive the real 3D building shape — each client's
    building is drawn from its own type/area/dimensions/basement."""
    _inherit = 'care.cafm.building'

    building_type = fields.Selection([
        ('tower', 'برج'), ('commercial', 'تجاري'), ('mall', 'مجمّع تجاري'),
        ('residential', 'سكني'), ('villa', 'فيلا'), ('warehouse', 'مستودع'),
        ('mixed', 'متعدّد الاستخدام'), ('other', 'أخرى'),
    ], string='نوع المبنى', default='commercial')
    total_area = fields.Float(string='المساحة (م²)')
    width_m = fields.Integer(string='العرض (م)', default=24)
    depth_m = fields.Integer(string='العمق (م)', default=18)
    floor_height_m = fields.Float(string='ارتفاع الدور (م)', default=3.4)
    has_basement = fields.Boolean(string='يوجد سرداب')
    basement_count = fields.Integer(string='عدد الأدوار السفلية', default=0)
    color = fields.Char(string='لون الواجهة', default='#9ac2ff')
    # ---- richer customization (feeds the 3D model) ----
    elevators = fields.Integer(string='عدد المصاعد', default=2)
    stairs = fields.Integer(string='عدد السلالم', default=1)
    entrances = fields.Integer(string='عدد المداخل', default=1)
    rooms_per_floor = fields.Integer(string='غرف/دور (افتراضي)', default=6)
    facade_style = fields.Selection([
        ('glass', 'زجاجي'), ('concrete', 'خرساني'), ('stone', 'حجري'),
        ('brick', 'طوب'), ('mixed', 'مختلط'),
    ], string='نمط الواجهة', default='glass')
    roof_type = fields.Selection([
        ('flat', 'مسطّح'), ('dome', 'قبّة'), ('pitched', 'جملوني'), ('helipad', 'مهبط'),
    ], string='نوع السطح', default='flat')
    night_lights = fields.Boolean(string='نوافذ مضيئة', default=True)
    logo_url = fields.Char(string='رابط لوجو المبنى')


class ResCompanyShift(models.Model):
    _inherit = 'res.company'

    cafm_shift_notify_user_ids = fields.Many2many(
        'res.users', 'cafm_shift_notify_rel', 'company_id', 'user_id',
        string='مستلمو إشعارات الوردية',
        help='من يُخطَر عند فتح/إغلاق أي وردية. إن تُرك فارغاً تُخطَر مجموعات المشرفين.')
    cafm_shift_enforce_hours = fields.Boolean(
        string='إلزام ساعات العمل', default=False,
        help='منع فتح الوردية خارج ساعات عمل الموظف (من جدول العمل).')


class ResConfigSettingsShift(models.TransientModel):
    _inherit = 'res.config.settings'

    cafm_shift_notify_user_ids = fields.Many2many(
        related='company_id.cafm_shift_notify_user_ids', readonly=False)
    cafm_shift_enforce_hours = fields.Boolean(
        related='company_id.cafm_shift_enforce_hours', readonly=False)


class CafmShift(models.Model):
    _name = 'care.cafm.shift'
    _description = 'CAFM Shift (geofenced)'
    _order = 'check_in desc'

    name = fields.Char(default='/', copy=False, readonly=True)
    employee_id = fields.Many2one('hr.employee', string='الموظف', required=True, index=True)
    facility_id = fields.Many2one('care.cafm.facility', string='المرفق', index=True)
    check_in = fields.Datetime(string='بداية الوردية', readonly=True, copy=False)
    check_out = fields.Datetime(string='نهاية الوردية', readonly=True, copy=False)
    in_lat = fields.Float(digits=(10, 7))
    in_lng = fields.Float(digits=(10, 7))
    out_lat = fields.Float(digits=(10, 7))
    out_lng = fields.Float(digits=(10, 7))
    in_distance = fields.Integer(string='بُعد الدخول (م)')
    duration_hours = fields.Float(string='المدة (ساعة)', compute='_compute_duration', store=True)
    state = fields.Selection([('open', 'مفتوحة'), ('closed', 'مغلقة')], default='open', index=True)
    within_hours = fields.Boolean(string='ضمن ساعات العمل', default=True)
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    @api.model
    def _within_working_hours(self, employee, when=None):
        """True if `when` falls in the employee's working-hours calendar (or no
        calendar is set)."""
        cal = employee.resource_calendar_id
        if not cal or not cal.attendance_ids:
            return True
        when = when or fields.Datetime.now()
        dt = fields.Datetime.context_timestamp(self, when)
        dow, hour = str(dt.weekday()), dt.hour + dt.minute / 60.0
        return any(a.dayofweek == dow and a.hour_from <= hour <= a.hour_to
                   for a in cal.attendance_ids)

    @api.depends('check_in', 'check_out')
    def _compute_duration(self):
        for r in self:
            if r.check_in and r.check_out:
                r.duration_hours = (r.check_out - r.check_in).total_seconds() / 3600.0
            else:
                r.duration_hours = 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('care.cafm.shift') or _('SH')
        return super().create(vals_list)

    @staticmethod
    def _haversine(lat1, lng1, lat2, lng2):
        r = 6371000.0
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dp = math.radians(lat2 - lat1)
        dl = math.radians(lng2 - lng1)
        a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
        return int(r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)))

    @api.model
    def open_for(self, employee, lat, lng):
        """Open a shift for the employee if within any of their facilities' fence."""
        if self.search_count([('employee_id', '=', employee.id), ('state', '=', 'open')]):
            raise UserError(_('لديك وردية مفتوحة بالفعل.'))
        # candidate facilities: from the employee's work orders (with coordinates)
        WO = self.env['care.cafm.workorder'].sudo()
        facs = WO.search([('employee_id', '=', employee.id)]).mapped('facility_id')
        facs = facs.filtered(lambda f: f.geo_lat and f.geo_lng)
        best = None
        for f in facs:
            dist = self._haversine(lat, lng, f.geo_lat, f.geo_lng)
            if dist <= (f.geo_radius or 200) and (best is None or dist < best[1]):
                best = (f, dist)
        if not best:
            raise UserError(_('أنت خارج نطاق أي موقع مُصرّح — لا يمكن فتح الوردية.'))
        in_hours = self._within_working_hours(employee)
        if not in_hours and self.env.company.cafm_shift_enforce_hours:
            raise UserError(_('خارج ساعات عملك المقرّرة — لا يمكن فتح الوردية.'))
        return self.create({
            'employee_id': employee.id, 'facility_id': best[0].id,
            'check_in': fields.Datetime.now(), 'in_lat': lat, 'in_lng': lng,
            'in_distance': best[1], 'state': 'open', 'within_hours': in_hours,
        })

    def close_shift(self, lat=None, lng=None):
        self.write({'state': 'closed', 'check_out': fields.Datetime.now(),
                    'out_lat': lat or 0.0, 'out_lng': lng or 0.0})


class HrEmployeeAvailability(models.Model):
    _inherit = 'hr.employee'

    cafm_on_shift = fields.Boolean(string='في وردية', compute='_compute_on_shift', search='_search_on_shift')

    def _compute_on_shift(self):
        Shift = self.env['care.cafm.shift']
        for e in self:
            e.cafm_on_shift = bool(Shift.search_count([('employee_id', '=', e.id), ('state', '=', 'open')]))

    def _search_on_shift(self, operator, value):
        open_emp = self.env['care.cafm.shift'].search([('state', '=', 'open')]).mapped('employee_id').ids
        if (operator == '=' and value) or (operator == '!=' and not value):
            return [('id', 'in', open_emp)]
        return [('id', 'not in', open_emp)]


class AttendanceReport(models.AbstractModel):
    """Feeds the attendance PDF. The values come from the same
    _attendance_data() the portal and app read, passed in via `data`, so the
    printed report can never drift from what the screen showed."""
    _name = 'report.care_cafm.report_attendance_doc'
    _description = 'تقرير الحضور والانصراف'

    @api.model
    def _get_report_values(self, docids, data=None):
        d = dict(data or {})
        d.setdefault('totals', {})
        d.setdefault('printed_on', fields.Datetime.to_string(fields.Datetime.now())[:16])
        return {'doc_ids': docids, 'doc_model': 'care.cafm.shift', 'docs': [], 'd': d}
