# -*- coding: utf-8 -*-
"""Dedicated CAFM org hierarchy: Client → Project → Team → Member(+shift).

Each level is a first-class CAFM record that *links to* the underlying Odoo
record (res.partner / project.project) via a "linked record" field you can pick
or create inline — instead of managing raw partners/projects directly."""
from odoo import api, fields, models, _

OPEN_STATES = ('new', 'assigned', 'in_progress')


class CafmShiftType(models.Model):
    _name = 'care.cafm.shift.type'
    _description = 'نوع الوردية'
    _order = 'start_time'

    name = fields.Char(string='الوردية', required=True, translate=True)
    code = fields.Char(string='الرمز')
    start_time = fields.Float(string='من', help='بصيغة 24 ساعة')
    end_time = fields.Float(string='إلى')
    days = fields.Char(string='الأيام', help='مثال: الأحد–الخميس')
    color = fields.Integer(string='لون')
    active = fields.Boolean(default=True)

    def name_get(self):
        res = []
        for s in self:
            t = '%s' % s.name
            if s.start_time or s.end_time:
                t += ' (%02d:%02d–%02d:%02d)' % (int(s.start_time), round((s.start_time % 1) * 60),
                                                 int(s.end_time), round((s.end_time % 1) * 60))
            res.append((s.id, t))
        return res


class CafmClient(models.Model):
    _name = 'care.cafm.client'
    _description = 'عميل CAFM'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='اسم العميل', required=True, tracking=True, translate=True)
    code = fields.Char(string='الرمز', copy=False, readonly=True, default=lambda s: _('جديد'))
    active = fields.Boolean(default=True)
    partner_id = fields.Many2one('res.partner', string='العميل المرتبط (أودو)', tracking=True,
                                 help='اختر جهة الاتصال الموجودة في أودو، أو أنشئ واحدة جديدة مباشرة.')
    user_ids = fields.Many2many('res.users', 'cafm_client_user_rel', 'client_id', 'user_id',
                                string='مستخدمو العميل', help='مستخدمو البوّابة التابعون لهذا العميل.')
    phone = fields.Char(related='partner_id.phone', readonly=False, string='الهاتف')
    email = fields.Char(related='partner_id.email', readonly=False, string='البريد')
    can_add_workers = fields.Boolean(string='يُسمح بإضافة عمّال', tracking=True,
                                     help='يفتح لمستخدمي العميل إنشاء أوامر العمل وإضافة العمّال.')
    shop_product_ids = fields.Many2many(
        related='partner_id.cafm_shop_product_ids', readonly=False, string='منتجات المتجر',
        help='المنتجات التي تظهر في متجر هذا العميل. اتركها فارغة لعرض كل المنتجات.')
    project_ids = fields.One2many('care.cafm.project', 'client_id', string='المشاريع')
    notes = fields.Html(string='ملاحظات')
    color = fields.Integer()
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    # ---- which app/portal sections this client sees --------------------------
    portal_mode = fields.Selection([
        ('auto', 'تلقائي (حسب الخدمات المقدَّمة)'),
        ('custom', 'مخصّص (اختيار يدوي للقوائم)'),
    ], string='قوائم البوابة', default='auto', required=True, tracking=True,
        help='تلقائي: تظهر القوائم حسب الخدمات الفعلية للعميل. مخصّص: تختار أنت بالضبط أي القوائم تظهر له.')
    portal_section_ids = fields.Many2many(
        'care.cafm.portal.section', 'cafm_client_section_rel', 'client_id', 'section_id',
        string='القوائم الظاهرة للعميل',
        help='في الوضع المخصّص: القوائم/الخدمات التي يراها هذا العميل داخل التطبيق فقط.')

    def visible_section_codes(self, service_types=None):
        """The set of section codes this client may see in the app/portal."""
        self.ensure_one()
        Section = self.env['care.cafm.portal.section'].sudo()
        if self.portal_mode == 'custom':
            codes = set(self.portal_section_ids.mapped('code'))
            codes |= set(Section.search([('always_on', '=', True)]).mapped('code'))
            return codes
        return Section.auto_codes_for_types(service_types or set())

    project_count = fields.Integer(compute='_compute_counts', string='المشاريع')
    user_count = fields.Integer(compute='_compute_counts', string='المستخدمون')
    facility_count = fields.Integer(compute='_compute_counts', string='المرافق')
    open_wo = fields.Integer(compute='_compute_counts', string='أوامر مفتوحة')

    @api.depends('project_ids', 'user_ids', 'partner_id')
    def _compute_counts(self):
        WO = self.env['care.cafm.workorder']
        Fac = self.env['care.cafm.facility']
        for c in self:
            c.project_count = len(c.project_ids)
            c.user_count = len(c.user_ids)
            facs = Fac.search([('partner_id', '=', c.partner_id.id)]) if c.partner_id else Fac.browse()
            c.facility_count = len(facs)
            c.open_wo = WO.search_count([('facility_id', 'in', facs.ids), ('state', 'in', OPEN_STATES)]) if facs else 0

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('code', _('جديد')) in (_('جديد'), 'New', '/', False):
                v['code'] = self.env['ir.sequence'].next_by_code('care.cafm.client') or '/'
        recs = super().create(vals_list)
        recs._sync_partner()
        return recs

    def write(self, vals):
        res = super().write(vals)
        if {'can_add_workers', 'partner_id'} & set(vals):
            self._sync_partner()
        return res

    def _sync_partner(self):
        """Keep the linked partner's CAFM flags in step so the portal/app
        (which scope by partner) keep working transparently."""
        for c in self:
            if c.partner_id:
                c.partner_id.sudo().write({
                    'is_cafm_client': True,
                    'cafm_can_add_workers': c.can_add_workers,
                })

    def action_open_projects(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('مشاريع %s') % self.name,
            'res_model': 'care.cafm.project', 'view_mode': 'kanban,tree,form',
            'domain': [('client_id', '=', self.id)],
            'context': {'default_client_id': self.id},
        }


class CafmProject(models.Model):
    _name = 'care.cafm.project'
    _description = 'مشروع CAFM'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='اسم المشروع', required=True, tracking=True, translate=True)
    code = fields.Char(string='الرمز', copy=False, readonly=True, default=lambda s: _('جديد'))
    active = fields.Boolean(default=True)
    client_id = fields.Many2one('care.cafm.client', string='العميل', required=True, tracking=True, ondelete='cascade')
    partner_id = fields.Many2one(related='client_id.partner_id', store=True, string='جهة العميل')
    project_id = fields.Many2one('project.project', string='المشروع المرتبط (أودو)', tracking=True,
                                 help='اربط بمشروع أودو موجود أو أنشئ واحداً جديداً.')
    manager_ids = fields.Many2many('res.users', 'cafm_proj_mgr_rel', 'project_id', 'user_id', string='مديرو المشروع')
    manager_id = fields.Many2one('res.users', string='مدير المشروع (رئيسي)', tracking=True)
    supervisor_ids = fields.Many2many('res.users', 'cafm_proj_sup_rel', 'project_id', 'user_id', string='المشرفون')
    quality_ids = fields.Many2many('res.users', 'cafm_proj_qc_rel', 'project_id', 'user_id', string='مراقبة الجودة')
    user_ids = fields.Many2many('res.users', 'cafm_proj_user_rel', 'project_id', 'user_id', string='مستخدمون آخرون')
    team_ids = fields.One2many('care.cafm.team', 'cafm_project_id', string='الفرق')
    facility_ids = fields.Many2many('care.cafm.facility', 'cafm_proj_fac_rel', 'project_id', 'facility_id', string='المرافق')
    material_ids = fields.Many2many('product.product', 'cafm_proj_material_rel', 'project_id', 'product_id',
                                    string='مواد المشروع', help='المواد المختارة من المخزون لهذا المشروع.')
    logo = fields.Image(string='شعار المشروع', max_width=1024, max_height=1024,
                        help='يظهر هذا الشعار على المبنى في العرض ثلاثي الأبعاد.')
    notes = fields.Html(string='ملاحظات')
    color = fields.Integer()
    company_id = fields.Many2one('res.company', default=lambda s: s.env.company)

    team_count = fields.Integer(compute='_compute_counts', string='الفرق')
    facility_count = fields.Integer(compute='_compute_counts', string='المرافق')
    member_count = fields.Integer(compute='_compute_counts', string='الأعضاء')
    open_wo = fields.Integer(compute='_compute_counts', string='أوامر مفتوحة')

    @api.depends('team_ids', 'facility_ids', 'team_ids.member_line_ids')
    def _compute_counts(self):
        WO = self.env['care.cafm.workorder']
        for p in self:
            p.team_count = len(p.team_ids)
            p.facility_count = len(p.facility_ids)
            p.member_count = len(p.team_ids.mapped('member_line_ids'))
            p.open_wo = WO.search_count([('facility_id', 'in', p.facility_ids.ids), ('state', 'in', OPEN_STATES)]) if p.facility_ids else 0

    @api.model_create_multi
    def create(self, vals_list):
        for v in vals_list:
            if v.get('code', _('جديد')) in (_('جديد'), 'New', '/', False):
                v['code'] = self.env['ir.sequence'].next_by_code('care.cafm.project') or '/'
        recs = super().create(vals_list)
        recs._sync_primary_manager()
        return recs

    def write(self, vals):
        res = super().write(vals)
        if {'manager_ids', 'manager_id'} & set(vals):
            self._sync_primary_manager()
        return res

    def _sync_primary_manager(self):
        for p in self:
            if p.manager_ids and p.manager_id not in p.manager_ids:
                super(CafmProject, p).write({'manager_id': p.manager_ids[0].id})
            elif not p.manager_ids and p.manager_id:
                p.manager_ids = [(4, p.manager_id.id)]

    def action_open_teams(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': _('فِرَق %s') % self.name,
            'res_model': 'care.cafm.team', 'view_mode': 'kanban,tree,form',
            'domain': [('cafm_project_id', '=', self.id)],
            'context': {'default_cafm_project_id': self.id},
        }


class CafmTeam(models.Model):
    _inherit = 'care.cafm.team'

    cafm_project_id = fields.Many2one('care.cafm.project', string='مشروع CAFM', index=True, ondelete='cascade')
    member_line_ids = fields.One2many('care.cafm.team.member', 'team_id', string='أعضاء الفريق والورديات')
    line_count = fields.Integer(compute='_compute_line_count', string='الأعضاء')
    # multiple supervisors / quality officers (the singular fields below stay in
    # sync as the "primary", so existing readers keep working)
    supervisor_ids = fields.Many2many('res.users', 'cafm_team_sup_rel', 'team_id', 'user_id', string='المشرفون')
    quality_ids = fields.Many2many('res.users', 'cafm_team_qc_rel', 'team_id', 'user_id', string='مراقبة الجودة')

    @api.depends('member_line_ids')
    def _compute_line_count(self):
        for t in self:
            t.line_count = len(t.member_line_ids)

    def _sync_primary_users(self):
        for t in self:
            vals = {}
            if t.supervisor_ids and t.supervisor_id not in t.supervisor_ids:
                vals['supervisor_id'] = t.supervisor_ids[0].id
            elif not t.supervisor_ids and t.supervisor_id:
                # backfill the plural from a pre-existing single value
                t.supervisor_ids = [(4, t.supervisor_id.id)]
            if t.quality_ids and t.quality_user_id not in t.quality_ids:
                vals['quality_user_id'] = t.quality_ids[0].id
            elif not t.quality_ids and t.quality_user_id:
                t.quality_ids = [(4, t.quality_user_id.id)]
            if vals:
                super(CafmTeam, t).write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        recs._sync_primary_users()
        return recs

    def write(self, vals):
        res = super().write(vals)
        if {'supervisor_ids', 'quality_ids', 'supervisor_id', 'quality_user_id'} & set(vals):
            self._sync_primary_users()
        return res


class CafmTeamMember(models.Model):
    _name = 'care.cafm.team.member'
    _description = 'عضو فريق CAFM (مع الوردية)'
    _order = 'team_id, id'

    team_id = fields.Many2one('care.cafm.team', string='الفريق', required=True, ondelete='cascade')
    # link to Odoo — pick by employee OR by user; each fills the other
    employee_id = fields.Many2one('hr.employee', string='الموظف/العامل (أودو)', required=True)
    user_id = fields.Many2one('res.users', string='المستخدم (أودو)')
    role = fields.Selection([
        ('worker', 'عامل'), ('supervisor', 'مشرف'), ('quality', 'مراقبة جودة'),
        ('driver', 'سائق'), ('technician', 'فني'), ('lead', 'رئيس فريق'),
    ], string='الدور', default='worker')
    shift_type_id = fields.Many2one('care.cafm.shift.type', string='الوردية')
    job_title = fields.Char(related='employee_id.job_title', string='المسمّى', readonly=True)
    phone = fields.Char(related='employee_id.mobile_phone', string='الهاتف', readonly=True)
    photo = fields.Binary(related='employee_id.image_128', string='الصورة')
    # context from the team
    cafm_project_id = fields.Many2one(related='team_id.cafm_project_id', store=True, string='المشروع')
    service_id = fields.Many2one(related='team_id.service_id', store=True, string='الخدمة')
    facility_id = fields.Many2one(related='team_id.facility_id', store=True, string='المرفق')
    # live workload
    open_wo = fields.Integer(compute='_compute_load', string='مفتوحة')
    overdue_wo = fields.Integer(compute='_compute_load', string='متأخرة')
    done_wo = fields.Integer(compute='_compute_load', string='منجزة')
    active = fields.Boolean(default=True)

    def name_get(self):
        rl = dict(self._fields['role'].selection)
        res = []
        for m in self:
            nm = m.employee_id.name or (m.user_id.name if m.user_id else '') or _('عضو')
            res.append((m.id, '%s — %s' % (nm, rl.get(m.role, ''))))
        return res

    @api.onchange('employee_id')
    def _onchange_employee(self):
        if self.employee_id and self.employee_id.user_id:
            self.user_id = self.employee_id.user_id

    @api.onchange('user_id')
    def _onchange_user(self):
        if self.user_id and not self.employee_id and self.user_id.employee_id:
            self.employee_id = self.user_id.employee_id

    def _compute_load(self):
        WO = self.env['care.cafm.workorder']
        for m in self:
            eid = m.employee_id.id
            if not eid:
                m.open_wo = m.overdue_wo = m.done_wo = 0
                continue
            m.open_wo = WO.search_count([('employee_id', '=', eid), ('state', 'in', OPEN_STATES)])
            m.overdue_wo = WO.search_count([('employee_id', '=', eid), ('is_overdue', '=', True)])
            m.done_wo = WO.search_count([('employee_id', '=', eid), ('state', 'in', ('done', 'verified'))])
