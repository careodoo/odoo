# -*- coding: utf-8 -*-
from odoo import api, fields, models


class EsignMixin(models.AbstractModel):
    """مِكسِن يضيف التوقيع الإلكتروني لأي موديول فيه موافقات.

    يرث الموديول هذا المِكسِن فيحصل على:
      - esignature_ids: تواقيع هذا السجل (محسوبة من السجل المركزي).
      - esign(role, role_en): يُنشئ توقيع المستخدم الحالي على هذا السجل.
    تُستدعى esign() من دالة الاعتماد (action_approve/…) في الموديول.
    """
    _name = 'esign.mixin'
    _description = 'Electronic Signature Mixin'

    esignature_ids = fields.One2many('care.esignature', compute='_compute_esignature_ids',
                                     string='التواقيع الإلكترونية')
    esignature_count = fields.Integer(compute='_compute_esignature_ids', string='عدد التواقيع')

    def _compute_esignature_ids(self):
        Sig = self.env['care.esignature'].sudo()
        for rec in self:
            sigs = Sig.search([('model', '=', rec._name), ('res_id', '=', rec.id)]) if rec.id else Sig.browse()
            rec.esignature_ids = sigs
            rec.esignature_count = len(sigs)

    def esign(self, role='', role_en=''):
        """توقيع المستخدم الحالي على هذا السجل بصفة معيّنة. يعيد سجل التوقيع."""
        self.ensure_one()
        return self.env['care.esignature'].esign_sign(self._name, self.id, role=role, role_en=role_en)

    def esign_for_role(self, role):
        """التوقيع المطابق لصفة معيّنة على هذا السجل (أو recordset فارغ) — للتقارير."""
        self.ensure_one()
        return self.esignature_ids.filtered(lambda s: (s.signer_role or '') == (role or ''))[:1]

    def action_open_esignatures(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': 'التواقيع الإلكترونية',
            'res_model': 'care.esignature', 'view_mode': 'tree,form',
            'domain': [('model', '=', self._name), ('res_id', '=', self.id)],
            'context': {'create': False},
        }
