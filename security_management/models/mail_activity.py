from odoo import models, api
from odoo.tools.translate import _

class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def _action_done(self, feedback=False, attachment_ids=None):
        """Override to handle boolean feedback values before they reach the template"""
        # Convert boolean values to strings to prevent template rendering errors
        if isinstance(feedback, bool):
            if feedback:
                feedback = _("Completed")
            else:
                feedback = ""  # Empty string instead of False to prevent split() error
        return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def message_post_with_source(self, source_model, message_type='notification', subtype_id=False, **kwargs):
        """Override to handle boolean feedback values in the context before they reach the template"""
        # Fix the feedback value in the context to avoid template rendering issues
        if 'mail_activity_feedback' in self.env.context and isinstance(self.env.context['mail_activity_feedback'], bool):
            # Create a new context with the feedback as a string
            ctx = dict(self.env.context)
            if self.env.context['mail_activity_feedback'] is True:
                ctx['mail_activity_feedback'] = "Completed"
            else:
                ctx['mail_activity_feedback'] = ""  # Empty string instead of False
            return super(MailThread, self.with_context(ctx)).message_post_with_source(
                source_model, message_type=message_type, subtype_id=subtype_id, **kwargs
            )
        
        return super(MailThread, self).message_post_with_source(
            source_model, message_type=message_type, subtype_id=subtype_id, **kwargs
        )
