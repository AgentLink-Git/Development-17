# models/financial/commission_calculation.py

"""
Module for extending Deal Records with commission balance calculations.
Defines additional computed fields to display commissions and taxes,
and provides methods to calculate and manage these financial metrics.
Ensures accurate tracking of commissions received and balances based on deal attributes.
"""

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class DealRecords(models.Model):
    _inherit = "deal.records"
    _description = "Extended Deal Records with Commission Calculations"

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
        default="fixed",
        help="Select the type of total commission calculation.",
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
        default=0.0,
        tracking=True,
        help="Additional flat fee to add for total commission.",
    )
    total_less_flat_fee = fields.Monetary(
        string="- Flat Fee",
        currency_field="currency_id",
        default=0.0,
        tracking=True,
        help="Flat fee to subtract for total commission.",
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
        default="fixed",
        help="Select the type of buyer side commission calculation.",
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
        default=0.0,
        tracking=True,
        help="Additional flat fee to add for buyer side commission.",
    )
    buyer_side_less_flat_fee = fields.Monetary(
        string="- Flat Fee",
        currency_field="currency_id",
        default=0.0,
        tracking=True,
        help="Flat fee to subtract for buyer side commission.",
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
        help="Commission amount for the seller side.",
    )
    seller_side_tax = fields.Monetary(
        string="Seller Side Tax",
        compute="_compute_seller_side_tax",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Tax amount for the seller side commission.",
    )
    seller_side_total = fields.Monetary(
        string="Seller Side Total",
        compute="_compute_seller_side_total",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Total amount for the seller side commission including tax.",
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
        help="Commission amount for the buyer side.",
    )
    buyer_side_tax = fields.Monetary(
        string="Buyer Side Tax",
        compute="_compute_buyer_side_tax",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Tax amount for the buyer side commission.",
    )
    buyer_side_total = fields.Monetary(
        string="Buyer Side Total",
        compute="_compute_buyer_side_total",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Total amount for the buyer side commission including tax.",
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
        help="Total commission from both seller and buyer sides.",
    )
    total_tax = fields.Monetary(
        string="Total Tax",
        compute="_compute_total_tax",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Total tax from both seller and buyer side commissions.",
    )
    total_amount = fields.Monetary(
        string="Total Amount",
        compute="_compute_total_amount",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Total amount including commissions and taxes.",
    )

    # =====================
    # Commission Line Fields (One2many Relationships)
    # =====================
    total_commission_line_ids = fields.One2many(
        'commission.line',
        'deal_id',
        string="Total Commission Lines",
        help="Commission lines contributing to the total commission.",
    )
    buyer_side_commission_line_ids = fields.One2many(
        'commission.line',
        'deal_id',
        string="Buyer Side Commission Lines",
        help="Commission lines contributing to the buyer side commission.",
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
            _logger.debug(
                "Total Commission Line Subtotal for Deal ID %s: %s",
                rec.id,
                rec.total_commission_line_subtotal,
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
            _logger.debug(
                "Buyer Side Commission Line Subtotal for Deal ID %s: %s",
                rec.id,
                rec.buyer_side_commission_line_subtotal,
            )

    @api.depends("total_commission", "buyer_side_commission")
    def _compute_seller_side_commission(self):
        """
        Compute the seller side commission based on total and buyer side commissions.
        """
        for rec in self:
            rec.seller_side_commission = rec.total_commission - rec.buyer_side_commission
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
            tax_rate = rec.tax_rate or 0.0
            rec.seller_side_tax = rec.seller_side_commission * tax_rate / 100.0
            _logger.debug(
                "Seller Side Tax for Deal ID %s: %s (Tax Rate: %s%%)",
                rec.id,
                rec.seller_side_tax,
                tax_rate,
            )

    @api.depends("seller_side_commission", "seller_side_tax")
    def _compute_seller_side_total(self):
        """
        Compute the total seller side commission including tax.
        """
        for rec in self:
            rec.seller_side_total = rec.seller_side_commission + rec.seller_side_tax
            _logger.debug(
                "Seller Side Total for Deal ID %s: %s",
                rec.id,
                rec.seller_side_total,
            )

    @api.depends("buyer_side_commission", "tax_rate")
    def _compute_buyer_side_tax(self):
        """
        Compute the buyer side tax based on buyer side commission.
        """
        for rec in self:
            tax_rate = rec.tax_rate or 0.0
            rec.buyer_side_tax = rec.buyer_side_commission * tax_rate / 100.0
            _logger.debug(
                "Buyer Side Tax for Deal ID %s: %s (Tax Rate: %s%%)",
                rec.id,
                rec.buyer_side_tax,
                tax_rate,
            )

    @api.depends("buyer_side_commission", "buyer_side_tax")
    def _compute_buyer_side_total(self):
        """
        Compute the total buyer side commission including tax.
        """
        for rec in self:
            rec.buyer_side_total = rec.buyer_side_commission + rec.buyer_side_tax
            _logger.debug(
                "Buyer Side Total for Deal ID %s: %s",
                rec.id,
                rec.buyer_side_total,
            )

    @api.depends("seller_side_tax", "buyer_side_tax")
    def _compute_total_tax(self):
        """
        Compute the total tax by summing seller and buyer side taxes.
        """
        for rec in self:
            rec.total_tax = rec.seller_side_tax + rec.buyer_side_tax
            _logger.debug(
                "Total Tax for Deal ID %s: %s",
                rec.id,
                rec.total_tax,
            )

    @api.depends("seller_side_commission", "buyer_side_commission")
    def _compute_total_commission(self):
        """
        Compute the total commission by summing seller and buyer side commissions.
        """
        for rec in self:
            rec.total_commission = rec.seller_side_commission + rec.buyer_side_commission
            _logger.debug(
                "Total Commission for Deal ID %s: %s",
                rec.id,
                rec.total_commission,
            )

    @api.depends("total_commission", "total_tax")
    def _compute_total_amount(self):
        """
        Compute the total amount by summing total commission and total tax.
        """
        for rec in self:
            rec.total_amount = rec.total_commission + rec.total_tax
            _logger.debug(
                "Total Amount for Deal ID %s: %s",
                rec.id,
                rec.total_amount,
            )

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
            old_commission = rec.total_commission
            if rec.total_commission_type == "flat_fee":
                rec.total_commission = rec.total_plus_flat_fee - rec.total_less_flat_fee
                _logger.debug(
                    "Total Commission (Flat Fee) for Deal ID %s set to: %s",
                    rec.id,
                    rec.total_commission,
                )
            elif rec.total_commission_type == "fixed":
                percentage = rec.total_commission_line_subtotal or 0.0
                rec.total_commission = (
                    (rec.sell_price * percentage / 100.0)
                    + rec.total_plus_flat_fee
                    - rec.total_less_flat_fee
                )
                _logger.debug(
                    "Total Commission (Fixed) for Deal ID %s set to: %s",
                    rec.id,
                    rec.total_commission,
                )
            elif rec.total_commission_type == "tiered":
                rec.total_commission = rec._calculate_tiered_commission(
                    rec.total_commission_line_ids
                )
                _logger.debug(
                    "Total Commission (Tiered) for Deal ID %s set to: %s",
                    rec.id,
                    rec.total_commission,
                )
            else:
                rec.total_commission = 0.0
                _logger.debug(
                    "Total Commission for Deal ID %s reset to 0.0",
                    rec.id,
                )

            if old_commission != rec.total_commission:
                rec._compute_seller_side_commission()

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
            old_buyer_commission = rec.buyer_side_commission
            if rec.buyer_side_commission_type == "flat_fee":
                rec.buyer_side_commission = rec.buyer_side_plus_flat_fee - rec.buyer_side_less_flat_fee
                _logger.debug(
                    "Buyer Side Commission (Flat Fee) for Deal ID %s set to: %s",
                    rec.id,
                    rec.buyer_side_commission,
                )
            elif rec.buyer_side_commission_type == "fixed":
                percentage = rec.buyer_side_commission_line_subtotal or 0.0
                rec.buyer_side_commission = (
                    (rec.sell_price * percentage / 100.0)
                    + rec.buyer_side_plus_flat_fee
                    - rec.buyer_side_less_flat_fee
                )
                _logger.debug(
                    "Buyer Side Commission (Fixed) for Deal ID %s set to: %s",
                    rec.id,
                    rec.buyer_side_commission,
                )
            elif rec.buyer_side_commission_type == "tiered":
                rec.buyer_side_commission = rec._calculate_tiered_commission(
                    rec.buyer_side_commission_line_ids
                )
                _logger.debug(
                    "Buyer Side Commission (Tiered) for Deal ID %s set to: %s",
                    rec.id,
                    rec.buyer_side_commission,
                )
            else:
                rec.buyer_side_commission = 0.0
                _logger.debug(
                    "Buyer Side Commission for Deal ID %s reset to 0.0",
                    rec.id,
                )

            if old_buyer_commission != rec.buyer_side_commission:
                rec._compute_seller_side_commission()

    @api.onchange("total_commission", "buyer_side_commission")
    def _onchange_seller_side_commission(self):
        """
        Update seller side commission based on total commission and buyer side commission.
        """
        for rec in self:
            rec.seller_side_commission = rec.total_commission - rec.buyer_side_commission
            _logger.debug(
                "Updated Seller Side Commission for Deal ID %s: %s",
                rec.id,
                rec.seller_side_commission,
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
                "Commission Line ID %s: Applicable Amount=%s, Percentage=%s%%, Line Commission=%s",
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
        _logger.debug(
            "Total Tiered Commission for Deal ID %s: %s",
            self.id,
            total_commission,
        )
        return total_commission

    def _get_commission_we_have_received(self):
        """
        Calculate the total commission received excluding trust deposits.

        Returns:
            float: Commission received excluding trust deposits.
        """
        self.ensure_one()
        commission_transactions = self.transaction_line_ids.filtered(
            lambda t: t.transaction_type == 'commission_receipt'
                      and t.journal_type == 'non_trust'
                      and t.held_by == 'our_office'
        )
        total_amount = sum(t.deposited for t in commission_transactions)
        _logger.debug(
            "Commission Received (Excluding Trust Deposits) for Deal ID %s: %s",
            self.id,
            total_amount,
        )
        return total_amount

    def _get_commission_balance(self):
        """
        Calculate the net commission balance (receipts - payments).

        Returns:
            float: Net commission balance.
        """
        self.ensure_one()
        commission_receipts = self.transaction_line_ids.filtered(
            lambda t: t.transaction_type == 'commission_receipt'
        )
        commission_payments = self.transaction_line_ids.filtered(
            lambda t: t.transaction_type == 'commission_payment'
        )
        total_receipts = sum(t.deposited for t in commission_receipts)
        total_payments = sum(t.deposited for t in commission_payments)
        net_balance = total_receipts - total_payments

        _logger.debug(
            "Net Commission Balance for Deal ID %s: Receipts=%s, Payments=%s, Balance=%s",
            self.id,
            total_receipts,
            total_payments,
            net_balance,
        )
        return net_balance

    # =====================
    # Constraints
    # =====================
    @api.constrains(
        'our_commission_and_tax',
        'commission_we_have_received',
        'commission_balance'
    )
    def _check_commission_fields(self):
        """
        Ensure that commission fields are non-negative.
        """
        for rec in self:
            if rec.our_commission_and_tax < 0:
                raise ValidationError(_("Our Commission & Tax cannot be negative for Deal ID %s.") % rec.id)
            if rec.commission_we_have_received < 0:
                raise ValidationError(_("Commission Received cannot be negative for Deal ID %s.") % rec.id)
            # Commission balance can be negative if payments exceed receipts
            _logger.debug(
                "Validated Commission Fields for Deal ID %s: "
                "Our Commission & Tax=%s, Commission Received=%s, Commission Balance=%s",
                rec.id,
                rec.our_commission_and_tax,
                rec.commission_we_have_received,
                rec.commission_balance,
            )

    # =====================
    # Additional Methods
    # =====================
    def reset_commission_fields(self):
        """
        Reset commission-related fields to zero.
        Useful for scenarios where commissions need to be recalculated.
        """
        for rec in self:
            rec.our_commission_and_tax = 0.0
            rec.commission_we_have_received = 0.0
            rec.commission_balance = 0.0
            _logger.info(
                "Reset commission fields for Deal ID %s.",
                rec.id,
            )

    def update_commission_fields(self):
        """
        Trigger the recomputation of commission fields.
        """
        for rec in self:
            rec._compute_total_commission_line_subtotal()
            rec._compute_buyer_side_commission_line_subtotal()
            rec._compute_total_commission()
            rec._compute_buyer_side_commission()
            rec._compute_seller_side_commission()
            rec._compute_seller_side_tax()
            rec._compute_seller_side_total()
            rec._compute_buyer_side_tax()
            rec._compute_buyer_side_total()
            rec._compute_total_tax()
            rec._compute_total_amount()
            _logger.info(
                "Updated commission fields for Deal ID %s.",
                rec.id,
            )