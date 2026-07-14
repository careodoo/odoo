# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """Care HR Policy / Labour-law engine.

    All regulatory numbers live here as configuration (not code) so they can
    be changed when the law or company policy changes, taking effect across
    payroll, leaves and end-of-service calculations.
    """
    _inherit = 'res.config.settings'

    # --- Leaves (Kuwait) ---
    care_annual_leave_days = fields.Integer(
        string='Annual Leave (days/yr)', default=30,
        config_parameter='care_hr.annual_leave_days')
    care_leave_entitlement_months = fields.Integer(
        string='Entitlement After (months)', default=9,
        config_parameter='care_hr.leave_entitlement_months')
    care_sick_full_days = fields.Integer(
        string='Sick Full-pay (days)', default=15,
        config_parameter='care_hr.sick_full_days')

    # --- End of Service (Kuwait) ---
    care_eos_first5_days = fields.Integer(
        string='EOS days/yr (first 5y)', default=15,
        config_parameter='care_hr.eos_first5_days')
    care_eos_after5_days = fields.Integer(
        string='EOS days/yr (after 5y)', default=30,
        config_parameter='care_hr.eos_after5_days')
    care_eos_cap_years = fields.Float(
        string='EOS Cap (years of pay)', default=1.5,
        config_parameter='care_hr.eos_cap_years')

    # --- Notice / Probation ---
    care_notice_days = fields.Integer(
        string='Notice Period (days)', default=30,
        config_parameter='care_hr.notice_days')
    care_probation_days = fields.Integer(
        string='Probation (days)', default=100,
        config_parameter='care_hr.probation_days')

    # --- Working hours / Overtime ---
    care_daily_hours = fields.Float(
        string='Daily Hours', default=8.0,
        config_parameter='care_hr.daily_hours')
    care_ot_rate_normal = fields.Float(
        string='Overtime Rate (normal)', default=1.25,
        config_parameter='care_hr.ot_rate_normal')
    care_ot_rate_holiday = fields.Float(
        string='Overtime Rate (holiday)', default=1.5,
        config_parameter='care_hr.ot_rate_holiday')
    care_ot_monthly_cap = fields.Float(
        string='Monthly OT Cap (hours)', default=0.0,
        config_parameter='care_hr.ot_monthly_cap')

    # --- Wages / Allowances ---
    care_base_wage_default = fields.Float(
        string='Default Base Wage', default=75.0,
        config_parameter='care_hr.base_wage_default')
    care_penalty_monthly_cap = fields.Float(
        string='Monthly Penalty Cap', default=0.0,
        config_parameter='care_hr.penalty_monthly_cap')
    care_allowance_senior_threshold = fields.Float(
        string='Allowance Senior-Approval Threshold', default=0.0,
        config_parameter='care_hr.allowance_senior_threshold',
        help='Allowances above this amount (or any cash allowance) require a '
             'Senior Approver (Top Management) in addition to the dept. manager.')

    # --- Document/Residency alerts ---
    care_doc_alert_days = fields.Integer(
        string='Document Expiry Alert (days)', default=60,
        config_parameter='care_hr.doc_alert_days')

    # --- Attendance coverage monitor ---
    care_coverage_days = fields.Integer(
        string='No-Attendance Threshold (days)', default=3,
        config_parameter='care_hr.coverage_days',
        help='Flag active workers with no attendance for this many days.')
