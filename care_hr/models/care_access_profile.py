# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class CareAccessProfile(models.Model):
    """Configurable access profile. Each profile owns a generated security
    group; its model-permission lines are synced to ir.model.access records,
    and the group is assigned to the profile's users. Applying is explicit so
    administrators control exactly when access changes take effect."""
    _name = 'care.access.profile'
    _description = 'Access Profile'
    _order = 'name'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    note = fields.Text()
    group_id = fields.Many2one('res.groups', string='Generated Group', readonly=True, copy=False)
    user_ids = fields.Many2many('res.users', string='Users')
    line_ids = fields.One2many('care.access.profile.line', 'profile_id', string='Permissions')
    line_count = fields.Integer(compute='_compute_counts')
    applied = fields.Boolean(readonly=True, copy=False)

    @api.depends('line_ids')
    def _compute_counts(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    def _ensure_group(self):
        self.ensure_one()
        if not self.group_id:
            cat = self.env.ref('care_hr.module_care_hr', raise_if_not_found=False)
            grp = self.env['res.groups'].create({
                'name': 'Access Profile: %s' % self.name,
                'category_id': cat.id if cat else False,
            })
            self.group_id = grp.id
        return self.group_id

    def action_apply(self):
        """Sync the profile to a real security group + ir.model.access rows."""
        Access = self.env['ir.model.access']
        for profile in self:
            group = profile._ensure_group()
            tag = 'care_ap_%s_' % profile.id
            # remove previously generated access rows for this profile
            Access.search([('name', '=like', tag + '%')]).unlink()
            for line in profile.line_ids:
                Access.create({
                    'name': '%s%s' % (tag, line.model_id.model),
                    'model_id': line.model_id.id,
                    'group_id': group.id,
                    'perm_read': line.perm_read,
                    'perm_write': line.perm_write,
                    'perm_create': line.perm_create,
                    'perm_unlink': line.perm_unlink,
                })
            # sync group membership to exactly the profile's users
            current = group.users
            to_add = profile.user_ids - current
            to_remove = current - profile.user_ids
            if to_add:
                group.write({'users': [(4, u.id) for u in to_add]})
            if to_remove:
                group.write({'users': [(3, u.id) for u in to_remove]})
            profile.applied = True
        return True

    def unlink(self):
        # clean generated access rows + groups
        Access = self.env['ir.model.access']
        for profile in self:
            Access.search([('name', '=like', 'care_ap_%s_%%' % profile.id)]).unlink()
            if profile.group_id:
                profile.group_id.unlink()
        return super().unlink()


class CareAccessProfileLine(models.Model):
    _name = 'care.access.profile.line'
    _description = 'Access Profile Permission Line'

    profile_id = fields.Many2one('care.access.profile', required=True, ondelete='cascade')
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade')
    perm_read = fields.Boolean(string='Read', default=True)
    perm_write = fields.Boolean(string='Write')
    perm_create = fields.Boolean(string='Create')
    perm_unlink = fields.Boolean(string='Delete')

    _sql_constraints = [
        ('model_uniq', 'unique(profile_id, model_id)',
         'A model can appear only once per access profile.'),
    ]
