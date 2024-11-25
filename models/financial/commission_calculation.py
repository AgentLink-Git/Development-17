# models/financial/commission_calculation.py

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class DealRecords(models.Model):
    _inherit = "deal.records"
    _description = "Commission Calculations for Deal Records"

    # =====================
    # Commission Fields for Total Commission
    # =====================
    total_commission_type = fields.Selection(
        [
            ("tiered", "Tiered Percentage"),
            ("fixed", "Fixed Percentage"),
            ("flat_fee", "Flat Fee"),
        ],
        string="Total Commission Type",
        tracking=True,
    )
    total_commission_line_subtotal = fields.Float(
        string="Subtotal",
        compute="_compute_total_commission_line_subtotal",
        store=True,
        help="Subtotal of the calculated total commission lines.",
    )
    total_plus_flat_fee = fields.Monetary(
        string="+ Flat Fee",
        currency_field="currency_id",
        help="Additional flat fee to add for total commission.",
        tracking=True,
        default=0.0,
    )
    total_less_flat_fee = fields.Monetary(
        string="- Flat Fee",
        currency_field="currency_id",
        help="Flat fee to subtract for total commission.",
        tracking=True,
        default=0.0,
    )

    # =====================
    # Commission Fields for Buyer Side Commission
    # =====================
    buyer_side_commission_type = fields.Selection(
        [
            ("tiered", "Tiered Percentage"),
            ("fixed", "Fixed Percentage"),
            ("flat_fee", "Flat Fee"),
        ],
        string="Buyer Side Commission Type",
        tracking=True,
    )
    buyer_side_commission_line_subtotal = fields.Float(
        string="Subtotal",
        compute="_compute_buyer_side_commission_line_subtotal",
        store=True,
        help="Subtotal of the calculated buyer side commission lines.",
    )
    buyer_side_plus_flat_fee = fields.Monetary(
        string="+ Flat Fee",
        currency_field="currency_id",
        help="Additional flat fee to add for buyer side commission.",
        tracking=True,
        default=0.0,
    )
    buyer_side_less_flat_fee = fields.Monetary(
        string="- Flat Fee",
        currency_field="currency_id",
        help="Flat fee to subtract for buyer side commission.",
        tracking=True,
        default=0.0,
    )

    # =====================
    # Seller Side Commissions
    # =====================
    seller_side_commission = fields.Monetary(
        string="Seller Side Commission",
        currency_field="currency_id",
        compute="_compute_seller_side_commission",
        store=True,
        tracking=True,
    )
    seller_side_tax = fields.Monetary(
        string="Seller Side Tax",
        compute="_compute_seller_side_tax",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    seller_side_total = fields.Monetary(
        string="Seller Side Total",
        compute="_compute_seller_side_total",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )

    # =====================
    # Buyer Side Commissions
    # =====================
    buyer_side_commission = fields.Monetary(
        string="Buyer Side Commission",
        currency_field="currency_id",
        compute="_compute_buyer_side_commission",
        store=True,
        tracking=True,
    )
    buyer_side_tax = fields.Monetary(
        string="Buyer Side Tax",
        compute="_compute_buyer_side_tax",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    buyer_side_total = fields.Monetary(
        string="Buyer Side Total",
        compute="_compute_buyer_side_total",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )

    # =====================
    # Total Commissions
    # =====================
    total_commission = fields.Monetary(
        string="Total Commission",
        compute="_compute_total_commission",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    total_tax = fields.Monetary(
        string="Total Tax",
        compute="_compute_total_tax",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    total_amount = fields.Monetary(
        string="Total Amount",
        compute="_compute_total_amount",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )

    # =====================
    # Commission Line Fields (Assuming One2many Relationships)
    # =====================
    total_commission_line_ids = fields.One2many(
        "commission.line",
        "deal_id",
        string="Total Commission Lines",
    )
    buyer_side_commission_line_ids = fields.One2many(
        "commission.line",
        "deal_id",
        string="Buyer Side Commission Lines",
    )

    # =====================
    # Compute Methods
    # =====================

    @api.depends("total_commission_line_ids.subtotal")
    def _compute_total_commission_line_subtotal(self):
        """
        Compute the subtotal for total commission lines.
        """
        for rec in self:
            rec.total_commission_line_subtotal = sum(
                line.subtotal for line in rec.total_commission_line_ids
            )

    @api.depends("buyer_side_commission_line_ids.subtotal")
    def _compute_buyer_side_commission_line_subtotal(self):
        """
        Compute the subtotal for buyer side commission lines.
        """
        for rec in self:
            rec.buyer_side_commission_line_subtotal = sum(
                line.subtotal for line in rec.buyer_side_commission_line_ids
            )

    @api.depends("total_commission", "buyer_side_commission")
    def _compute_seller_side_commission(self):
        """
        Compute the seller side commission.
        """
        for rec in self:
            rec.seller_side_commission = (
                rec.total_commission - rec.buyer_side_commission
            )
            _logger.debug(
                "Seller Side Commission for Deal ID %s: %s",
                rec.id,
                rec.seller_side_commission,
            )

    @api.depends("seller_side_commission", "tax_rate")
    def _compute_seller_side_tax(self):
        """
        Compute the seller side tax based on seller side commission.
        """
        for rec in self:
            rec.seller_side_tax = (
                rec.seller_side_commission * (rec.tax_rate or 0.0) / 100.0
            )

    @api.depends("seller_side_commission", "seller_side_tax")
    def _compute_seller_side_total(self):
        """
        Compute the total seller side commission including tax.
        """
        for rec in self:
            rec.seller_side_total = rec.seller_side_commission + rec.seller_side_tax

    @api.depends("buyer_side_commission", "tax_rate")
    def _compute_buyer_side_tax(self):
        """
        Compute the buyer side tax based on buyer side commission.
        """
        for rec in self:
            rec.buyer_side_tax = (
                rec.buyer_side_commission * (rec.tax_rate or 0.0) / 100.0
            )

    @api.depends("buyer_side_commission", "buyer_side_tax")
    def _compute_buyer_side_total(self):
        """
        Compute the total buyer side commission including tax.
        """
        for rec in self:
            rec.buyer_side_total = rec.buyer_side_commission + rec.buyer_side_tax

    @api.depends("seller_side_tax", "buyer_side_tax")
    def _compute_total_tax(self):
        """
        Compute the total tax by summing seller and buyer side taxes.
        """
        for rec in self:
            rec.total_tax = rec.seller_side_tax + rec.buyer_side_tax

    @api.depends("seller_side_commission", "buyer_side_commission")
    def _compute_total_commission(self):
        """
        Compute the total commission by summing seller and buyer side commissions.
        """
        for rec in self:
            rec.total_commission = (
                rec.seller_side_commission + rec.buyer_side_commission
            )

    @api.depends("total_commission", "total_tax")
    def _compute_total_amount(self):
        """
        Compute the total amount by summing total commission and total tax.
        """
        for rec in self:
            rec.total_amount = rec.total_commission + rec.total_tax

    # =====================
    # Onchange Methods
    # =====================

    @api.onchange(
        "total_commission_type",
        "total_plus_flat_fee",
        "total_less_flat_fee",
        "total_commission_line_subtotal",
        "sell_price",
        "total_commission_line_ids",
    )
    def _onchange_total_commission(self):
        """
        Update total commission based on selected type and related fields.
        """
        for rec in self:
            if rec.total_commission_type == "flat_fee":
                rec.total_commission = rec.total_plus_flat_fee - rec.total_less_flat_fee
            elif rec.total_commission_type == "fixed":
                rec.total_commission = (
                    (rec.sell_price * rec.total_commission_line_subtotal / 100.0)
                    + rec.total_plus_flat_fee
                    - rec.total_less_flat_fee
                )
            elif rec.total_commission_type == "tiered":
                rec.total_commission = rec._calculate_tiered_commission(
                    rec.total_commission_line_ids
                )
            else:
                rec.total_commission = 0.0

    @api.onchange(
        "buyer_side_commission_type",
        "buyer_side_plus_flat_fee",
        "buyer_side_less_flat_fee",
        "buyer_side_commission_line_subtotal",
        "sell_price",
        "buyer_side_commission_line_ids",
    )
    def _onchange_buyer_side_commission(self):
        """
        Update buyer side commission based on buyer side commission type and related fields.
        """
        for rec in self:
            if rec.buyer_side_commission_type == "flat_fee":
                rec.buyer_side_commission = (
                    rec.buyer_side_plus_flat_fee - rec.buyer_side_less_flat_fee
                )
            elif rec.buyer_side_commission_type == "fixed":
                rec.buyer_side_commission = (
                    (rec.sell_price * rec.buyer_side_commission_line_subtotal / 100.0)
                    + rec.buyer_side_plus_flat_fee
                    - rec.buyer_side_less_flat_fee
                )
            elif rec.buyer_side_commission_type == "tiered":
                rec.buyer_side_commission = rec._calculate_tiered_commission(
                    rec.buyer_side_commission_line_ids
                )
            else:
                rec.buyer_side_commission = 0.0

    @api.onchange("total_commission", "buyer_side_commission")
    def _onchange_seller_side_commission(self):
        """
        Update seller side commission based on total commission and buyer side commission.
        """
        for rec in self:
            rec.seller_side_commission = (
                rec.total_commission - rec.buyer_side_commission
            )

    # =====================
    # Helper Methods
    # =====================

    def _calculate_tiered_commission(self, commission_lines):
        """
        Calculate commission for tiered commission lines.

        Args:
            commission_lines (recordset): Commission lines to calculate.

        Returns:
            float: Calculated commission amount.
        """
        self.ensure_one()
        total_commission = 0.0
        remaining_amount = self.sell_price

        for line in commission_lines.sorted(key=lambda l: l.sequence):
            applicable_amount = min(remaining_amount, line.amount)
            line_commission = applicable_amount * (line.percentage / 100.0)
            total_commission += line_commission
            remaining_amount -= applicable_amount
            _logger.debug(
                "Line %s: amount=%s, percentage=%s, line_commission=%s",
                line.id,
                applicable_amount,
                line.percentage,
                line_commission,
            )
            if remaining_amount <= 0:
                break

        # Include flat fees
        total_commission += self.total_plus_flat_fee
        total_commission -= self.total_less_flat_fee

        _logger.debug("Total Tiered Commission Calculated: %s", total_commission)
        return total_commission

    # =====================
    # Constraints
    # =====================

    @api.constrains("seller_side_commission", "buyer_side_commission")
    def _check_commissions_positive(self):
        """
        Ensure that seller and buyer side commissions are not negative.
        """
        for record in self:
            if record.seller_side_commission < 0:
                raise ValidationError(_("Seller side commissions cannot be negative."))
            if record.buyer_side_commission < 0:
                raise ValidationError(_("Buyer side commissions cannot be negative."))
