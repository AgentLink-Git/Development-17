# models/deals/conditions.py

import logging

_logger = logging.getLogger(__name__)

# =====================
# Condition Type
# =====================
from odoo import models, fields, api


class ConditionType(models.Model):
    _name = "condition.type"
    _description = "Condition Type"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Name", required=True)
    type = fields.Char(string="Type")
    sequence = fields.Integer(string="Sequence", default=10)
    is_active = fields.Boolean(string="Active", default=True)

    # =====================
    # Condition Line
    # =====================


from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ConditionLine(models.Model):
    _name = "condition.line"
    _description = "Condition Line"

    condition_type_id = fields.Many2one(
        "condition.type",
        string="Condition Type",
        domain="[('is_active','=',True)]",
        tracking=True,
        required=True,
    )
    due_date = fields.Date(string="Due Date", tracking=True)
    condition_removed = fields.Boolean(
        string="Condition Removed", tracking=True, default=False
    )
    removal_date = fields.Date(string="Removal Date", tracking=True)
    notes = fields.Html(string="Notes")
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        ondelete="cascade",
        required=True,
        tracking=True,
    )
