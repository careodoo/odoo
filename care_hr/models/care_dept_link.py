# -*- coding: utf-8 -*-
import difflib
from odoo import fields, models, api, _


class HrDepartment(models.Model):
    """Bulk department->project linking helper. Completing this mapping is what
    makes the Billing / Profitability / SLA coverage figures accurate (workers
    are tied to projects via their department)."""
    _inherit = 'hr.department'

    # stored (not computed) so it never costs anything on normal department
    # reads -- it is filled on demand by the suggestion action.
    suggested_project_id = fields.Many2one('project.project', string='Suggested Project', copy=False)
    suggested_score = fields.Integer(string='Match %', copy=False)

    @api.model
    def action_generate_project_suggestions(self):
        """Fuzzy-match each unlinked department to the closest project by name."""
        projects = self.env['project.project'].search([])
        pmap = {}
        for p in projects:
            nm = (p.name or '').strip()
            if nm:
                pmap.setdefault(nm, p.id)
        names = list(pmap)
        n = 0
        for d in self.search([('project_id', '=', False)]):
            nm = (d.name or '').strip()
            if not nm:
                continue
            best = difflib.get_close_matches(nm, names, n=1, cutoff=0.5)
            if best:
                d.suggested_project_id = pmap[best[0]]
                d.suggested_score = int(round(difflib.SequenceMatcher(None, nm, best[0]).ratio() * 100))
                n += 1
            else:
                d.suggested_project_id = False
                d.suggested_score = 0
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Suggestions'),
                       'message': _('%s departments matched to a project.') % n,
                       'type': 'success', 'sticky': False,
                       'next': {'type': 'ir.actions.act_window_close'}},
        }

    def action_apply_suggestion(self):
        for d in self:
            if d.suggested_project_id and not d.project_id:
                d.project_id = d.suggested_project_id

    @api.model
    def action_apply_all_strong(self):
        """Apply suggestions with a high match score (>=80%) in bulk."""
        deps = self.search([('project_id', '=', False),
                            ('suggested_project_id', '!=', False),
                            ('suggested_score', '>=', 80)])
        for d in deps:
            d.project_id = d.suggested_project_id
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Linked'),
                       'message': _('%s high-confidence links applied.') % len(deps),
                       'type': 'success', 'sticky': False,
                       'next': {'type': 'ir.actions.act_window_close'}},
        }
