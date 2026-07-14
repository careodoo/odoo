# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Baseline: mark all EXISTING tasks/attendances as already processed so the
    performance ledger only scores events that happen from installation onward."""
    env.cr.execute("UPDATE project_task SET performance_logged = TRUE WHERE performance_logged IS NOT TRUE")
    env.cr.execute("UPDATE hr_attendance SET performance_logged = TRUE WHERE performance_logged IS NOT TRUE")
