# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Technogies @cybrosys(odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from markupsafe import Markup
from odoo import api, models


class ReportHrAttendance(models.AbstractModel):
    """This is an abstract model for the Attendance Report of Employees."""
    _name = 'report.advance_hr_attendance_dashboard.report_hr_attendance'
    _description = 'Attendance Report  of Employees'

    @api.model
    def _get_report_values(self, doc_ids, data=None):
        """Get the report values for the Attendance Report."""
        data = dict(data or {})
        # The client ships already-rendered table HTML (tHead/tBody). On Odoo 17
        # ``t-raw`` is removed, so the template uses ``t-out``; wrap the HTML in
        # ``Markup`` so it is emitted as markup instead of being escaped.
        for key in ('tHead', 'tBody'):
            if data.get(key):
                data[key] = Markup(data[key])
        return {
            'doc_model': 'hr.attendance',
            'data': data,
            'self': self,
        }
