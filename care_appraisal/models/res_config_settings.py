# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    perf_task_ontime = fields.Float(
        string='Task on-time (reward)', config_parameter='care_perf.task_ontime')
    perf_task_overdue = fields.Float(
        string='Task overdue (penalty)', config_parameter='care_perf.task_overdue')
    perf_att_present = fields.Float(
        string='Full attendance', config_parameter='care_perf.att_present')
    perf_att_short = fields.Float(
        string='Short day (penalty)', config_parameter='care_perf.att_short')
    perf_att_min_hours = fields.Float(
        string='Min hours for a full day', config_parameter='care_perf.att_min_hours')
    perf_att_overtime_bonus = fields.Float(
        string='Overtime bonus', config_parameter='care_perf.att_overtime_bonus')
    perf_penalty_points = fields.Float(
        string='Approved penalty impact', config_parameter='care_perf.penalty_points')
    perf_bonus_points = fields.Float(
        string='Approved bonus impact', config_parameter='care_perf.bonus_points')
    perf_notify_disabled = fields.Boolean(
        string='Disable performance notifications', config_parameter='care_perf.notify_disabled')
    perf_notify_threshold = fields.Float(
        string='Notification threshold (points)', config_parameter='care_perf.notify_threshold')
    perf_reward_threshold = fields.Float(
        string='Reward suggestion threshold (points)', config_parameter='care_perf.reward_threshold')
    perf_reward_per_point = fields.Float(
        string='Reward amount per point', config_parameter='care_perf.reward_per_point')
    perf_low_threshold = fields.Float(
        string='Low-performance alert threshold (points)', config_parameter='care_perf.low_threshold')
