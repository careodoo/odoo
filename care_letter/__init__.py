# -*- coding: utf-8 -*-
import logging
from lxml import etree

from . import models

_logger = logging.getLogger(__name__)

STUDIO_MAP = {
    'x_studio_follow_up_person': 'follow_up_person_id',
    'x_studio_notes': 'notes',
}


def _migrate_studio_fields(env):
    """Copy data from Odoo-Studio fields to native module fields, scrub views, drop studio fields."""
    cr = env.cr
    # 1) migrate data (both columns are stored on letter_file)
    for old, new in STUDIO_MAP.items():
        cr.execute("SELECT 1 FROM information_schema.columns "
                   "WHERE table_name='letter_file' AND column_name=%s", (old,))
        if not cr.fetchone():
            continue
        cr.execute("SELECT 1 FROM information_schema.columns "
                   "WHERE table_name='letter_file' AND column_name=%s", (new,))
        if not cr.fetchone():
            continue
        cr.execute("UPDATE letter_file SET {new} = {old} "
                   "WHERE {old} IS NOT NULL AND {new} IS NULL".format(new=new, old=old))
        _logger.info('care_letter: migrated %s -> %s (%s rows)', old, new, cr.rowcount)

    # 2) scrub studio field references out of every letter.file view
    views = env['ir.ui.view'].with_context(active_test=False).search([('model', '=', 'letter.file')])
    for view in views:
        arch = view.arch_db or ''
        if not any(name in arch for name in STUDIO_MAP):
            continue
        try:
            root = etree.fromstring(arch.encode('utf-8'))
            removed = False
            for name in STUDIO_MAP:
                for node in root.xpath("//field[@name='%s']" % name):
                    node.getparent().remove(node)
                    removed = True
            if removed:
                view.with_context(lang=None).arch_db = etree.tostring(root, encoding='unicode')
                _logger.info('care_letter: scrubbed studio fields from view %s', view.id)
        except Exception as e:
            _logger.warning('care_letter: could not scrub view %s: %s', view.id, e)

    # 3) delete the studio fields themselves (fresh search each time; name captured up-front)
    for fname in list(STUDIO_MAP):
        f = env['ir.model.fields'].search(
            [('model', '=', 'letter.file'), ('name', '=', fname)], limit=1)
        if not f:
            continue
        try:
            with env.cr.savepoint():
                f.with_context(_force_unlink=True).unlink()
            _logger.info('care_letter: deleted studio field %s', fname)
        except Exception as e:
            _logger.warning('care_letter: could not delete studio field %s: %s', fname, e)


def _backfill_lifecycle(env):
    """Derive direction / letter_state for the 1765 existing letters."""
    cr = env.cr
    # direction: all current refs are Care/... = outgoing
    cr.execute("UPDATE letter_file SET direction='outgoing' WHERE direction IS NULL")
    # lifecycle from existing signals
    cr.execute("""
        UPDATE letter_file lf SET letter_state = CASE
            WHEN lf.deli_date IS NOT NULL THEN 'delivered'
            WHEN EXISTS (SELECT 1 FROM ir_attachment a
                         WHERE a.res_model='letter.file' AND a.res_field='image_letter'
                         AND a.res_id=lf.id) THEN 'scanned'
            ELSE 'draft'
        END
        WHERE lf.letter_state IS NULL
    """)
    # OCR state: pending where a scan exists but no text yet
    cr.execute("""
        UPDATE letter_file lf SET ocr_state='pending'
        WHERE (lf.ocr_state IS NULL OR lf.ocr_state='none')
          AND EXISTS (SELECT 1 FROM ir_attachment a
                      WHERE a.res_model='letter.file' AND a.res_field='image_letter' AND a.res_id=lf.id)
    """)
    cr.execute("UPDATE letter_file SET ocr_state='none' WHERE ocr_state IS NULL")
    # requester defaults to creator
    cr.execute("UPDATE letter_file SET requester_id = create_uid WHERE requester_id IS NULL")
    _logger.info('care_letter: lifecycle backfilled')


def _cleanup_junk(env):
    """Remove the junk 'TEst' outgoing stage."""
    junk = env['outgoing.stage'].search([('name', 'in', ['TEst', 'TEST', 'test'])])
    if junk:
        env['letter.file'].search([('out_going_stage', 'in', junk.ids)]).write({'out_going_stage': False})
        junk.unlink()
        _logger.info('care_letter: removed junk stages')


def _assign_admins(env):
    """Give existing managers full access; everyone else keeps 'own letters only'."""
    admin_group = env.ref('care_letter.group_letter_admin', raise_if_not_found=False)
    if not admin_group:
        return
    managers = env['res.users']
    for xmlid in ('base.user_admin', 'base.user_root'):
        u = env.ref(xmlid, raise_if_not_found=False)
        if u:
            managers |= u
    hr_mgr = env.ref('hr.group_hr_manager', raise_if_not_found=False)
    if hr_mgr:
        managers |= hr_mgr.users
    sysg = env.ref('base.group_system', raise_if_not_found=False)
    if sysg:
        managers |= sysg.users
    managers = managers.filtered(lambda u: u.active)
    if managers:
        admin_group.sudo().write({'users': [(4, u.id) for u in managers]})
        _logger.info('care_letter: assigned %s admins', len(managers))


def post_init_hook(env):
    for step in (_migrate_studio_fields, _backfill_lifecycle, _cleanup_junk, _assign_admins):
        try:
            step(env)
        except Exception as e:
            _logger.exception('care_letter post_init step %s failed: %s', step.__name__, e)
    try:
        env['letter.i18n'].apply_ar()
        letters = env['letter.file'].search([])
        letters._compute_delivery()
        letters._compute_deadline_state()
        _logger.info('care_letter: post_init complete (%s letters)', len(letters))
    except Exception as e:
        _logger.exception('care_letter post_init finalize failed: %s', e)
