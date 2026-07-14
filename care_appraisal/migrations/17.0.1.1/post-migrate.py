# -*- coding: utf-8 -*-


def migrate(cr, version):
    """Baseline existing penalties/bonuses as already processed so only events
    approved from this upgrade onward feed the performance ledger."""
    for table in ('care_penalty', 'care_bonus'):
        cr.execute(
            "UPDATE %s SET performance_logged = TRUE WHERE performance_logged IS NOT TRUE" % table
        )
