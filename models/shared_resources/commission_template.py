# models/shared_resources/commission_template.py

"""
Module for managing Commission Templates.
This module defines the CommissionTemplate and CommissionTemplateLine models, which store
commission configurations and their respective lines. It ensures data integrity through
constraints and provides comprehensive logging for auditing and debugging purposes.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class CommissionTemplate(models.Model):
    """
    Model for storing Commission Templates.
    This model holds configurations for different types of commissions, including their categories,
    types, percentages, and associated lines. It ensures that commission percentages are within valid
    ranges and that each template has at least one commission line.
    """
    _name = "commission.template"
    _description = "Commission Template"
    _rec_name = "name"
    _order = "name asc"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # =====================
    # Fields
    # =====================

    name = fields.Char(
        string="Name",
        required=True,
        help="Name of the commission template.",
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help="Company associated with this commission template.",
        tracking=True,
        index=True,
    )
    commission_category = fields.Selection(
        [
            ('total_commission', 'Total Commission'),
            ('buyer_side_commission', 'Buyer Side Commission'),
        ],
        string="Commission Category",
        required=True,
        help="Category of the commission template.",
        tracking=True,
    )
    commission_type = fields.Selection(
        [
            ('tiered', 'Tiered Percentage'),
            ('fixed', 'Fixed Percentage'),
            ('flat_fee', 'Flat Fee'),
        ],
        string="Commission Type",
        required=True,
        help="Type of commission.",
        tracking=True,
    )
    total_commission_percentage = fields.Float(
        string="Total Commission Percentage (%)",
        help="Overall commission percentage.",
        default=0.0,
        tracking=True,
    )
    commission_flat_fee_plus = fields.Monetary(
        string="+ Flat Fee ($)",
        currency_field="currency_id",
        help="Additional flat fee to add.",
        default=0.0,
        tracking=True,
    )
    commission_flat_fee_less = fields.Monetary(
        string="- Flat Fee ($)",
        currency_field="currency_id",
        help="Flat fee to subtract.",
        default=0.0,
        tracking=True,
    )
    commission_template_line_ids = fields.One2many(
        "commission.template.line",
        "commission_template_id",
        string="Commission Template Lines",
        help="Lines associated with this commission template.",
        copy=True,
        auto_join=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        string="Currency",
        readonly=True,
    )

    # =====================
    # Constraints
    # =====================

    @api.constrains('total_commission_percentage', 'commission_type')
    def _check_total_commission_percentage(self):
        """
        Ensure that the total commission percentage is between 0 and 100
        for commission types that require it.
        """
        for record in self:
            if record.commission_type in ['fixed', 'tiered'] and not (0 <= record.total_commission_percentage <= 100):
                raise ValidationError(_("Total Commission Percentage must be between 0 and 100."))

    @api.constrains('commission_template_line_ids')
    def _check_template_lines(self):
        """
        Ensure that each commission template has at least one commission line.
        """
        for record in self:
            if not record.commission_template_line_ids:
                raise ValidationError(_("Commission Template must have at least one commission line."))


class CommissionTemplateLine(models.Model):
    """
    Model for storing Commission Template Lines.
    Each line represents a specific portion of the selling price and its associated commission
    percentage. The lines are ordered by sequence and must have valid values.
    """
    _name = "commission.template.line"
    _description = "Commission Template Line"
    _order = "sequence asc"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # =====================
    # Fields
    # =====================

    commission_template_id = fields.Many2one(
        "commission.template",
        string="Commission Template",
        required=True,
        ondelete="cascade",
        help="The commission template associated with this line.",
        tracking=True,
        index=True,
    )
    commission_type = fields.Selection(
        [
            ('total', 'Total Commission'),
            ('buyer_side', 'Buyer Side Commission'),
        ],
        string="Commission Type",
        required=True,
        help="Type of commission this line represents.",
        tracking=True,
    )
    commission_category = fields.Selection(
        [
            ('first', 'First'),
            ('next', 'Next'),
            ('total_selling_price', 'Total Selling Price'),
            ('remainder', 'Remainder'),
        ],
        string="Commission Category",
        required=True,
        help="Category of the commission line.",
        tracking=True,
    )
    portion_of_selling_price = fields.Monetary(
        string="Portion of Selling Price ($)",
        required=True,
        currency_field="currency_id",
        help="The portion of the selling price that this line's commission calculations are based on.",
        default=0.0,
        tracking=True,
    )
    commission_percentage = fields.Float(
        string="Commission Percentage (%)",
        required=True,
        help="Commission percentage for this portion of the selling price.",
        default=0.0,
        tracking=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        default=1,
        help="Sequence order of the commission template line.",
        tracking=True,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help="Company associated with this commission template.",
        tracking=True,
        index=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        string="Currency",
        readonly=True,
    )

    # =====================
    # Constraints
    # =====================

    @api.constrains('portion_of_selling_price', 'commission_percentage', 'commission_category')
    def _check_line_values(self):
        """
        Ensure that:
        - Portion of Selling Price is greater than 0.
        - Commission Percentage is between 0 and 100.
        - Final commission categories ('total_selling_price', 'remainder') have valid portions.
        """
        for record in self:
            if record.portion_of_selling_price <= 0:
                raise ValidationError(_("Portion of Selling Price must be greater than 0."))

            if not (0 <= record.commission_percentage <= 100):
                raise ValidationError(_("Commission Percentage must be between 0 and 100."))

            if record.commission_category in ['total_selling_price', 'remainder'] and record.portion_of_selling_price <= 0:
                raise ValidationError(_("Final commission categories must cover the remaining selling price."))

    # =====================
    # Methods
    # =====================

    @api.model
    def create(self, vals):
        """
        Override the create method to set default sequence if not provided.
        """
        if 'sequence' not in vals or not vals['sequence']:
            # Find the current highest sequence for the commission_template_id and increment by 1
            existing_sequences = self.search([
                ('commission_template_id', '=', vals.get('commission_template_id'))
            ]).mapped('sequence')
            vals['sequence'] = max(existing_sequences, default=0) + 1
        return super().create(vals)

    def write(self, vals):
        """
        Override the write method to handle sequence changes if necessary.
        """
        result = super().write(vals)
        if 'sequence' in vals:
            _logger.debug(f"Updated sequence to {vals['sequence']} for commission template line IDs {self.ids}.")
        return result

    def name_get(self):
        """
        Override the name_get method to provide a meaningful name for each commission template line.
        """
        result = []
        for record in self:
            name = f"{record.commission_type.capitalize()} - {record.commission_percentage}% of ${record.portion_of_selling_price:,.2f}"
            result.append((record.id, name))
        return result