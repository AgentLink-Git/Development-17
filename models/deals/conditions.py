# models/deals/conditions.py

"""
Module for managing Condition Types and Condition Lines associated with deals.
This module defines models for categorizing conditions and tracking their status
within the deal lifecycle. It ensures data integrity through constraints and
provides comprehensive logging for auditing and debugging purposes.
"""

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

# Configure the logger for this module
_logger = logging.getLogger(__name__)


class ConditionType(models.Model):
    """
    Model for defining different types of conditions that can be associated with deals.
    This model allows categorization of conditions, enabling better management and tracking
    within the deal process. It inherits from 'mail.thread' and 'mail.activity.mixin' to
    facilitate chatter and activity tracking.
    """
    _name = 'condition.type'
    _description = "Condition Type"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, name"

    name = fields.Char(
        string="Name",
        required=True,
        help="Name of the condition type."
    )
    category = fields.Char(
        string="Category",
        help="Category or classification of the condition type."
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
        help="Sequence order for condition types."
    )
    is_active = fields.Boolean(
        string="Active",
        default=True,
        help="Activate or deactivate this condition type."
    )

    _sql_constraints = [
        ('unique_name', 'unique(name)', 'Condition Type name must be unique.')
    ]

    @api.constrains('sequence')
    def _check_sequence_positive(self):
        """
        Ensure that the sequence number is positive.
        """
        for record in self:
            if record.sequence < 0:
                _logger.error(
                    f"Condition Type ID {record.id} has a negative sequence: {record.sequence}"
                )
                raise ValidationError(_("Sequence must be a positive integer."))


class ConditionLine(models.Model):
    """
    Model for tracking individual conditions associated with a deal.
    Each condition line references a condition type and tracks its status, including
    removal dates and associated notes. This model ensures that necessary data is
    provided when conditions are marked as removed.
    """
    _name = 'condition.line'
    _description = "Condition Line"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "due_date"

    condition_type_id = fields.Many2one(
        "condition.type",
        string="Condition Type",
        domain="[('is_active', '=', True)]",
        tracking=True,
        required=True,
        help="Type of condition."
    )
    due_date = fields.Date(
        string="Due Date",
        tracking=True,
        help="The date by which the condition should be fulfilled."
    )
    condition_removed = fields.Boolean(
        string="Condition Removed",
        tracking=True,
        default=False,
        help="Indicates whether the condition has been removed."
    )
    removal_date = fields.Date(
        string="Removal Date",
        tracking=True,
        help="The date when the condition was removed."
    )
    notes = fields.Html(
        string="Notes",
        help="Additional notes or comments regarding the condition."
    )
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        ondelete="cascade",
        required=True,
        tracking=True,
        help="Reference to the associated deal."
    )

    @api.constrains('condition_removed', 'removal_date')
    def _check_removal_date(self):
        """
        Ensure that removal_date is set if condition_removed is True,
        and removal_date cannot be before due_date.
        """
        for record in self:
            if record.condition_removed and not record.removal_date:
                _logger.error(
                    f"Condition Line ID {record.id} marked as removed without a removal date."
                )
                raise ValidationError(
                    _("Removal date must be set if the condition is marked as removed.")
                )
            if record.removal_date and record.due_date and record.removal_date < record.due_date:
                _logger.error(
                    f"Condition Line ID {record.id} has a removal date {record.removal_date} before due date {record.due_date}."
                )
                raise ValidationError(
                    _("Removal date cannot be before the due date.")
                )

    @api.onchange('condition_removed')
    def _onchange_condition_removed(self):
        """
        Automatically set the removal_date to today if condition_removed is checked,
        and clear it if unchecked.
        """
        if self.condition_removed and not self.removal_date:
            self.removal_date = fields.Date.today()
            _logger.debug(
                f"Condition Line ID {self.id}: condition_removed set to True, removal_date set to today."
            )
        elif not self.condition_removed:
            self.removal_date = False
            _logger.debug(
                f"Condition Line ID {self.id}: condition_removed set to False, removal_date cleared."
            )