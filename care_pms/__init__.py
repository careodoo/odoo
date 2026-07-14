# -*- coding: utf-8 -*-
import logging
from . import models
from . import controllers

_logger = logging.getLogger(__name__)


def _assign_admins(env):
    grp = env.ref('care_pms.group_pms_admin', raise_if_not_found=False)
    if not grp:
        return
    users = env['res.users']
    for xmlid in ('base.user_admin',):
        u = env.ref(xmlid, raise_if_not_found=False)
        if u:
            users |= u
    sysg = env.ref('base.group_system', raise_if_not_found=False)
    if sysg:
        users |= sysg.users
    users = users.filtered(lambda u: u.active)
    if users:
        grp.sudo().write({'users': [(4, u.id) for u in users]})


def post_init_hook(env):
    try:
        env['project.task'].search([])._compute_is_overdue()
    except Exception as e:
        _logger.warning('care_pms overdue backfill: %s', e)
    try:
        _assign_admins(env)
    except Exception as e:
        _logger.warning('care_pms assign admins: %s', e)
    try:
        env['care.pms.i18n'].apply_ar()
    except Exception as e:
        _logger.warning('care_pms i18n: %s', e)
    _logger.info('care_pms: post_init complete')
