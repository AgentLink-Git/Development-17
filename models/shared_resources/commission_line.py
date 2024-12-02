# models/shared_resources/commission_line.py

"""
Module for managing Commission Lines.
This module defines the CommissionLine model, which represents individual commission entries
associated with listings or deals. It includes logic to compute total commissions, handle
portion allocations based on commission categories, and enforce data integrity through constraints.
Comprehensive logging is implemented to facilitate auditing and debugging.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

# Configure the logger for this module
_logger = logging.getLogger(__name__)


class CommissionLine(models.Model):
    """
    Model for storing Commission Lines.
    Each commission line represents a specific portion of the selling price and its associated
    commission percentage. The lines are linked to listings or deals and are categorized
    to determine how portions of the selling price are allocated.
    """
    _name = "commission.line"
    _description = "Commission Line"
    _inherit = ["shared.fields.mixin"]
    _order = "sequence asc"

    # =====================
    # Fields
    # =====================
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        ondelete="cascade",
        help="Deal associated with this commission line.",
        index=True,
    )
    listing_id = fields.Many2one(
        "listing.records",
        string="Listing",
        ondelete="cascade",
        help="Listing associated with this commission line.",
        index=True,
    )
    commission_template_id = fields.Many2one(
        'commission.template',
        string="Commission Template",
        ondelete='restrict',
        required=True,
        help="Commission template defining the commission parameters.",
        index=True,
    )
    portion_of_selling_price = fields.Monetary(
        string="Selling Price Line Value ($)",
        required=True,
        help="The portion of the selling price that this line's commission calculations are based on.",
        default=0.0,
    )
    commission_percentage = fields.Float(
        string="Commission Percentage (%)",
        required=True,
        help="Commission percentage for this portion of the selling price.",
        default=0.0,
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
    )
    commission_type = fields.Selection(
        [
            ('total', 'Total'),
            ('buyer_side', 'Buyer Side'),
        ],
        string="Commission Type",
        required=True,
        default='total',
        help="Type of commission line: Total or Buyer Side.",
    )
    total_commission = fields.Monetary(
        string="Total Commission ($)",
        compute="_compute_total_commission",
        store=True,
        help="Total commission for this line.",
        currency_field='currency_id',
    )
    sequence = fields.Integer(
        string="Sequence",
        default=1,
        help="Sequence order of the commission line.",
    )
    commission_receipt_id = fields.Many2one(
        "commission.receipt",
        string="Related Commission Receipt",
        ondelete="cascade",
        help="Commission receipt related to the transaction.",
    )
    # =====================
    # Compute Fields
    # =====================

    @api.depends('commission_percentage', 'portion_of_selling_price')
    def _compute_total_commission(self):
        """
        Compute the total commission based on the portion of selling price and commission percentage.
        """
        for record in self:
            record.total_commission = (record.portion_of_selling_price * record.commission_percentage) / 100
            _logger.debug(
                f"Computed total_commission for record ID {record.id}: "
                f"({record.portion_of_selling_price} * {record.commission_percentage}) / 100 = {record.total_commission}"
            )

    # =====================
    # Onchange Methods
    # =====================

    @api.onchange('commission_category')
    def _onchange_commission_category(self):
        """
        Adjust the portion_of_selling_price based on the selected commission category.
        """
        if not self.deal_id:
            _logger.debug("No deal associated with this commission line; onchange_commission_category skipped.")
            return

        deal = self.deal_id
        sell_price = deal.sell_price or 0.0
        allocated_price = (
            sum(deal.total_commission_line_ids.mapped('portion_of_selling_price')) +
            sum(deal.buyer_side_commission_line_ids.mapped('portion_of_selling_price'))
        )
        remaining_price = max(sell_price - allocated_price, 0.0)
        original_portion = self.portion_of_selling_price

        if self.commission_category == 'first':
            self.portion_of_selling_price = remaining_price * 0.5
        elif self.commission_category == 'next':
            self.portion_of_selling_price = remaining_price * 0.3
        elif self.commission_category == 'remainder':
            self.portion_of_selling_price = remaining_price
        else:
            self.portion_of_selling_price = 0.0

        _logger.debug(
            f"Onchange_commission_category for record ID {self.id}: "
            f"Category '{self.commission_category}' changed portion_of_selling_price from {original_portion} to {self.portion_of_selling_price}."
        )

    # =====================
    # Constraints
    # =====================

    @api.constrains('portion_of_selling_price', 'commission_percentage', 'commission_category')
    def _check_commission_values(self):
        """
        Ensure that:
        - Portion of Selling Price is greater than 0.
        - Commission Percentage is between 0 and 100.
        - Final commission categories ('total_selling_price', 'remainder') have valid portions.
        """
        for record in self:
            if record.portion_of_selling_price <= 0:
                _logger.error(
                    f"Invalid portion_of_selling_price {record.portion_of_selling_price} "
                    f"for commission line ID {record.id}."
                )
                raise ValidationError(_("The portion of the selling price must be greater than zero."))

            if not (0 <= record.commission_percentage <= 100):
                _logger.error(
                    f"Invalid commission_percentage {record.commission_percentage} "
                    f"for commission line ID {record.id}."
                )
                raise ValidationError(_("Commission percentage must be between 0 and 100."))

            if record.commission_category in ['total_selling_price', 'remainder'] and record.portion_of_selling_price <= 0:
                _logger.error(
                    f"Invalid portion_of_selling_price {record.portion_of_selling_price} "
                    f"for final commission category '{record.commission_category}' "
                    f"in commission line ID {record.id}."
                )
                raise ValidationError(_("Remainder or total selling price categories must have a valid portion."))

    # =====================
    # Methods
    # =====================

    def name_get(self):
        """
        Override the name_get method to provide a meaningful name for each commission line.
        """
        result = []
        for record in self:
            name = (
                f"{record.commission_type.capitalize()} - "
                f"{record.commission_percentage}% of ${record.portion_of_selling_price:,.2f}"
            )
            result.append((record.id, name))
            _logger.debug(
                f"name_get for record ID {record.id}: '{name}'"
            )
        return result