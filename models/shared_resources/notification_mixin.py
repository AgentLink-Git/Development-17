# models/shared_resources/notification_mixin.py

from odoo import models, fields, api, _  # Essential imports
from odoo.exceptions import ValidationError  # If you plan to use exceptions
import logging

_logger = logging.getLogger(__name__)


class NotificationMixin(models.AbstractModel):
    _name = "notification.mixin"
    _description = "Notification Mixin"

    # Example fields (adjust as needed)
    notification_count = fields.Integer(
        string="Notification Count",
        compute="_compute_notification_count",
        store=True,
        readonly=True,
    )

    @api.depends("some_field")  # Replace 'some_field' with actual dependencies
    def _compute_notification_count(self):
        for record in self:
            # Example computation
            record.notification_count = len(record.some_related_field)

    # Example method
    def send_notification(self, message):
        # Implement your notification logic here
        _logger.info(f"Sending notification: {message}")
        # You can use Odoo's mail gateway or other methods to send notifications
