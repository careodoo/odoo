# -*- coding: utf-8 -*-
from odoo import fields, models, api, _


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _sync_one_input(self, slip, input_type, total, label):
        """Replace the input line of a given type with a single line of `total`."""
        old = slip.input_line_ids.filtered(lambda l: l.input_type_id == input_type)
        if old:
            old.unlink()
        if total and total > 0:
            slip.write({'input_line_ids': [(0, 0, {
                'input_type_id': input_type.id,
                'amount': total,
                'name': label,
            })]})
            return True
        return False

    def _sync_care_inputs(self):
        """Inject approved penalties (deduction) and in-payslip allowances
        (addition) for the period. Idempotent: rebuilt on every compute."""
        pen_type = self.env.ref('care_hr.input_type_care_penalty', raise_if_not_found=False)
        alw_type = self.env.ref('care_hr.input_type_care_allowance', raise_if_not_found=False)
        vio_type = self.env.ref('care_hr.input_type_care_violation', raise_if_not_found=False)
        bon_type = self.env.ref('care_hr.input_type_care_bonus', raise_if_not_found=False)
        gosi_type = self.env.ref('care_hr.input_type_care_gosi', raise_if_not_found=False)
        loan_type = self.env.ref('care_hr.input_type_care_loan', raise_if_not_found=False)
        Bonus = self.env['care.bonus']
        Gosi = self.env['care.gosi']
        Loan = self.env['care.loan']
        ICP = self.env['ir.config_parameter'].sudo()
        cap = float(ICP.get_param('care_hr.penalty_monthly_cap') or 0.0)
        Penalty = self.env['care.penalty']
        Allowance = self.env['care.allowance']
        Violation = self.env['care.traffic.violation']
        for slip in self:
            if not slip.employee_id or not slip.date_from or not slip.date_to:
                continue
            period = [
                ('employee_id', '=', slip.employee_id.id),
                ('date', '>=', slip.date_from), ('date', '<=', slip.date_to),
                '|', ('payslip_id', '=', False), ('payslip_id', '=', slip.id),
            ]
            # --- penalties ---
            if pen_type:
                pens = Penalty.search(period + [('state', 'in', ('approved', 'done'))])
                total = sum(pens.mapped('amount'))
                if cap and total > cap:
                    total = cap
                if self._sync_one_input(slip, pen_type, total, _('Penalties')):
                    pens.write({'payslip_id': slip.id})
            # --- in-payslip allowances ---
            if alw_type:
                alws = Allowance.search(period + [
                    ('state', 'in', ('approved', 'done')),
                    ('payment_method', '=', 'in_payslip')])
                total = sum(alws.mapped('amount'))
                if self._sync_one_input(slip, alw_type, total, _('Allowances')):
                    alws.write({'payslip_id': slip.id})
            # --- in-payslip bonuses (addition) ---
            if bon_type:
                bons = Bonus.search(period + [
                    ('state', 'in', ('approved', 'done')),
                    ('payment_method', '=', 'in_payslip')])
                total = sum(bons.mapped('amount'))
                if self._sync_one_input(slip, bon_type, total, _('Bonus')):
                    bons.write({'payslip_id': slip.id})
            # --- GOSI employee share (recurring monthly deduction) ---
            if gosi_type:
                gosi = Gosi.search([('employee_id', '=', slip.employee_id.id),
                                    ('active', '=', True)], limit=1)
                self._sync_one_input(slip, gosi_type, gosi.employee_amount if gosi else 0.0, _('GOSI'))
            # --- loan / advance installment (deduction) ---
            if loan_type:
                total, _due = Loan._due_installment(slip.employee_id.id, slip.date_from, slip.date_to)
                self._sync_one_input(slip, loan_type, total, _('Loan / Advance'))
            # --- traffic violations (driver-liable). Keyed on driver_id.
            # Only inject not-yet-deducted approved ones (avoid re-deducting
            # historically paid/migrated records). ---
            if vio_type:
                vios = Violation.search([
                    ('driver_id', '=', slip.employee_id.id),
                    ('date', '>=', slip.date_from), ('date', '<=', slip.date_to),
                    ('responsible', '=', 'driver'),
                    '|',
                    '&', ('state', '=', 'approved'), ('payslip_id', '=', False),
                    '&', ('state', '=', 'deducted'), ('payslip_id', '=', slip.id),
                ])
                total = sum(vios.mapped('amount'))
                if self._sync_one_input(slip, vio_type, total, _('Traffic Violations')):
                    vios.write({'payslip_id': slip.id})

    def compute_sheet(self):
        self._sync_care_inputs()
        return super().compute_sheet()

    def action_payslip_done(self):
        res = super().action_payslip_done()
        for slip in self:
            self.env['care.penalty'].search([
                ('payslip_id', '=', slip.id), ('state', '=', 'approved')]).write({'state': 'done'})
            self.env['care.allowance'].search([
                ('payslip_id', '=', slip.id), ('state', '=', 'approved'),
                ('payment_method', '=', 'in_payslip')]).write({'state': 'done'})
            self.env['care.traffic.violation'].search([
                ('payslip_id', '=', slip.id), ('state', '=', 'approved')]).write({'state': 'deducted'})
            self.env['care.bonus'].search([
                ('payslip_id', '=', slip.id), ('state', '=', 'approved'),
                ('payment_method', '=', 'in_payslip')]).write({'state': 'done'})
            # register loan/advance installments actually deducted this period
            if slip.employee_id and slip.date_from:
                total, due = self.env['care.loan']._due_installment(
                    slip.employee_id.id, slip.date_from, slip.date_to)
                for ln in due:
                    ln._register_installment(min(ln.installment_amount, ln.balance))
        return res

    @api.model
    def _setup_care_payroll_rules(self):
        """Idempotently ensure the CARE_PENALTY (deduction) and CARE_ALLOWANCE
        (addition) rules exist on the Worker/Employee salary structures. Zero
        effect unless the matching input is present, so safe on live structures."""
        pen_type = self.env.ref('care_hr.input_type_care_penalty', raise_if_not_found=False)
        alw_type = self.env.ref('care_hr.input_type_care_allowance', raise_if_not_found=False)
        if not pen_type:
            return
        Rule = self.env['hr.salary.rule']
        Cat = self.env['hr.salary.rule.category']
        ded = Cat.search([('code', '=', 'DED')], limit=1) or Cat.search([], limit=1)
        alw = Cat.search([('code', '=', 'ALW')], limit=1) or ded
        structs = self.env['hr.payroll.structure'].search([])
        targets = structs.filtered(lambda s: (s.type_id.name or '') in ('Worker', 'Employee'))
        defs = [
            ('CARE_PENALTY', 'Penalties (Care)', ded, 200,
             'result = bool(inputs.get("CARE_PENALTY"))',
             'result = -(inputs.get("CARE_PENALTY") or 0).amount'),
            ('CARE_VIOLATION', 'Traffic Violations (Care)', ded, 205,
             'result = bool(inputs.get("CARE_VIOLATION"))',
             'result = -(inputs.get("CARE_VIOLATION") or 0).amount'),
            ('CARE_GOSI', 'GOSI Employee Share (Care)', ded, 210,
             'result = bool(inputs.get("CARE_GOSI"))',
             'result = -(inputs.get("CARE_GOSI") or 0).amount'),
            ('CARE_LOAN', 'Loan / Advance Installment (Care)', ded, 215,
             'result = bool(inputs.get("CARE_LOAN"))',
             'result = -(inputs.get("CARE_LOAN") or 0).amount'),
            ('CARE_ALLOWANCE', 'Allowances (Care)', alw, 50,
             'result = bool(inputs.get("CARE_ALLOWANCE"))',
             'result = (inputs.get("CARE_ALLOWANCE") or 0).amount'),
            ('CARE_BONUS', 'Bonus (Care)', alw, 55,
             'result = bool(inputs.get("CARE_BONUS"))',
             'result = (inputs.get("CARE_BONUS") or 0).amount'),
        ]
        for struct in targets:
            for code, name, cat, seq, cond_py, code_py in defs:
                vals = {
                    'name': name, 'code': code, 'category_id': cat.id,
                    'struct_id': struct.id, 'sequence': seq,
                    'condition_select': 'python', 'condition_python': cond_py,
                    'amount_select': 'code', 'amount_python_compute': code_py,
                    'appears_on_payslip': True,
                }
                rule = Rule.search([('code', '=', code), ('struct_id', '=', struct.id)], limit=1)
                if rule:
                    rule.write(vals)
                else:
                    Rule.create(vals)
