from odoo import models, fields, api

class PoliceReportWizard(models.TransientModel):
    _name = 'security.police.report.wizard'
    _description = 'Police Report Wizard'

    incident_id = fields.Many2one('security.incident.report', string='Incident', readonly=True)
    police_report_number = fields.Char(string='Police Report Number', required=True)
    police_station = fields.Char(string='Police Station')
    reported_date = fields.Datetime(string='Reported Date', default=fields.Datetime.now, required=True)
    additional_notes = fields.Text(string='Additional Notes')

    def action_confirm(self):
        self.ensure_one()
        incident = self.incident_id
        incident.write({
            'police_report_number': self.police_report_number,
            'police_station': self.police_station,
            'reported_date': self.reported_date,
            'additional_notes': self.additional_notes,
            'police_notified': True,
        })
        return {'type': 'ir.actions.act_window_close'}
