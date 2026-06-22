from unittest.mock import MagicMock

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.to_attendance_device.pyzk.zk.base import ZK
from odoo.addons.to_attendance_device.pyzk.zk.finger import Finger
from odoo.addons.to_attendance_device.pyzk.zk.exception import ZKErrorResponse


@tagged('post_install', '-at_install')
class TestRWBFallback(TransactionCase):
    """Regression test: devices like the ZKTeco Horus E1-FP don't support the
    buffered template read (read_with_buffer -> 'RWB Not supported'). get_templates()
    must fall back to reading each user's fingers one by one instead of crashing."""

    def _make_zk(self):
        zk = ZK('127.0.0.1')
        # device claims enrolled fingers but rejects the buffered read
        zk.read_sizes = lambda: setattr(zk, 'fingers', 5)
        zk.read_with_buffer = MagicMock(side_effect=ZKErrorResponse("RWB Not supported"))

        class _U:
            def __init__(self, uid):
                self.uid = uid
                self.user_id = str(uid)

        zk.get_users = lambda: [_U(1), _U(2)]

        def fake_get_user_template(uid, temp_id=0, user_id=''):
            # user 1 -> slots 0,1 ; user 2 -> slot 0 ; everything else empty
            if uid == 1 and temp_id in (0, 1):
                return Finger(uid, temp_id, 1, b'TPL_U1_S%d' % temp_id)
            if uid == 2 and temp_id == 0:
                return Finger(uid, temp_id, 1, b'TPL_U2_S0')
            return Finger(uid, temp_id, 1, b'')

        zk.get_user_template = fake_get_user_template
        return zk

    def test_get_templates_falls_back_when_rwb_unsupported(self):
        zk = self._make_zk()
        templates = zk.get_templates()  # must not raise ZKErrorResponse
        # only the 3 non-empty fingers are returned; empty slots skipped
        self.assertEqual(len(templates), 3)
        self.assertTrue(all(len(f.template) > 0 for f in templates))
        keys = sorted((f.uid, f.fid) for f in templates)
        self.assertEqual(keys, [(1, 0), (1, 1), (2, 0)])

    def test_get_templates_empty_when_no_fingers(self):
        zk = ZK('127.0.0.1')
        zk.read_sizes = lambda: setattr(zk, 'fingers', 0)
        self.assertEqual(zk.get_templates(), [])
