# models/shared_resources/notification_mixin.py

from odoo import models

class NotificationMixin(models.AbstractModel):
    _name = 'notification.mixin'
    _description = 'Mixin for Notifications'

    def display_notification(self, title, message, notification_type='success'):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": notification_type,
                "sticky": False,
            },
        }
