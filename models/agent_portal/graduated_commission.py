# models/agent_portal/graduated_commission.py

"""
Module for managing Graduated Commissions.
Defines GraduatedCommission and GraduatedCommissionLine models to handle graduated
commission tiers within commission plans.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class GraduatedCommission(models.Model):
    _name = 'graduated.commission'
    _description = "Graduated Commission"
    _order = 'sequence asc'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    sequence = fields.Integer(
        string='Sequence',
        required=True,
        default=1,
        help="Determines the order of commission tiers.",
        tracking=True,
    )
    commission_from = fields.Monetary(
        string='From',
        required=True,
        help="Starting amount for this commission tier.",
        currency_field='currency_id',
        tracking=True,
    )
    commission_to = fields.Monetary(
        string='To',
        required=True,
        help="Ending amount for this commission tier.",
        currency_field='currency_id',
        tracking=True,
    )
    commission_percentage = fields.Float(
        string="Commission %",
        required=True,
        help="Commission percentage for this tier.",
        tracking=True,
    )
    flat_fee = fields.Monetary(
        string="Flat Fee",
        default=0.0,
        help="Flat fee for this commission tier.",
        currency_field='currency_id',
        tracking=True,
    )
    commission_plan_id = fields.Many2one(
        "commission.plan",
        string="Commission Plan",
        ondelete="cascade",
        required=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='commission_plan_id.currency_id',
        string='Currency',
        store=True,
        readonly=True,
        help="Currency of the commission plan.",
    )

    # =====================
    # Constraints
    # =====================
    @api.constrains('commission_from', 'commission_to', 'commission_percentage', 'flat_fee')
    def _check_graduated_commission_values(self):
        """
        Ensure that commission_from is less than commission_to,
        commission_percentage is between 0 and 100,
        and flat_fee is non-negative.
        """
        for record in self:
            if record.commission_from >= record.commission_to:
                raise ValidationError(_("Commission 'From' must be less than 'To'."))
            if not (0 <= record.commission_percentage <= 100):
                raise ValidationError(_("Commission percentage must be between 0 and 100."))
            if record.flat_fee < 0:
                raise ValidationError(_("Flat fee cannot be negative."))


class GraduatedCommissionLine(models.Model):
    _name = 'graduated.commission.line'
    _description = "Graduated Commission Line"
    _order = 'sequence asc'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    sequence = fields.Integer(
        string='Sequence',
        default=1,
        help="Sequence of the commission tier.",
    )
    commission_plan_id = fields.Many2one(
        "commission.plan",
        string="Commission Plan",
        ondelete="cascade",
        required=True,
        tracking=True,
    )
    commission_plan_line_id = fields.Many2one(
        'commission.plan.line',
        string="Commission Plan Line",
        required=True,
        ondelete='cascade',
        help="Associated commission plan line.",
    )
    commission_from = fields.Float(
        string='From ($)',
        required=True,
        help="Starting amount for this commission tier.",
    )
    commission_to = fields.Float(
        string='To ($)',
        required=True,
        help="Ending amount for this commission tier.",
    )
    commission_percentage = fields.Float(
        string="Commission %",
        required=True,
        help="Commission percentage for this tier.",
    )
    flat_fee = fields.Float(
        string="Flat Fee ($)",
        default=0.0,
        help="Flat fee for this tier.",
    )

    # =====================
    # Constraints
    # =====================
    @api.constrains('commission_from', 'commission_to', 'commission_percentage', 'flat_fee')
    def _check_graduated_commission_line_values(self):
        """
        Ensure that commission_from is less than commission_to,
        commission_percentage is between 0 and 100,
        and flat_fee is non-negative.
        """
        for record in self:
            if record.commission_from >= record.commission_to:
                raise ValidationError(_("Commission 'From' must be less than 'To'."))
            if not (0 <= record.commission_percentage <= 100):
                raise ValidationError(_("Commission percentage must be between 0 and 100."))
            if record.flat_fee < 0:
                raise ValidationError(_("Flat fee cannot be negative."))