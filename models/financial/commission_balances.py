# models/financial/commission_balances.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class DealRecords(models.Model):
    _inherit = "deal.records"
    _description = "Calculate Commission Balances"

    # =====================
    # Financial Fields
    # =====================
    our_commission_and_tax = fields.Monetary(
        string="Our Commission & Tax",
        compute="_compute_our_commission_and_tax",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    commission_we_have_received = fields.Monetary(
        string="Commission Received",
        compute="_compute_commission_we_have_received",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    commission_balance = fields.Monetary(
        string="Commission Balance",
        compute="_compute_commission_balance",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )

    # =====================
    # Computed Methods
    # =====================

    @api.depends(
        "end_id.type",
        "seller_side_total",
        "buyer_side_total",
        "total_amount",
        "buyer_broker_is_paid_by",
        "seller_broker_pays_trust_excess_to",
        "buyer_broker_pays_trust_excess_to",
        "other_broker_trust_excess_held",
        "deal_class_id",
        "our_trust_balance_held",
        "commission_we_have_received",
    )
    def _compute_our_commission_and_tax(self):
        """
        Compute the commission and tax earned based on deal type and brokerage payments.
        """
        for rec in self:
            commission = 0.0
            if rec.end_id.type in ["buyer", "tenant"]:
                commission = rec.buyer_side_total
                _logger.debug(
                    "Our Commission & Tax set to buyer_side_total: %s",
                    rec.buyer_side_total,
                )
            elif rec.end_id.type == "double_end":
                commission = rec.total_amount
                _logger.debug(
                    "Our Commission & Tax set to total_amount: %s", rec.total_amount
                )
            elif (
                rec.end_id.type in ["seller", "landlord"]
                and rec.buyer_broker_is_paid_by == "seller_broker"
                and rec.buyer_broker_pays_trust_excess_to == "seller_broker"
            ):
                commission = rec.total_amount
                _logger.debug(
                    "Our Commission & Tax set to total_amount: %s", rec.total_amount
                )
            elif (
                rec.end_id.type in ["seller", "landlord"]
                and rec.buyer_broker_is_paid_by == "seller_broker"
                and rec.buyer_broker_pays_trust_excess_to != "seller_broker"
                and rec.other_broker_trust_excess_held > 0
            ):
                commission = rec.seller_side_total
                _logger.debug(
                    "Our Commission & Tax set to seller_side_total: %s",
                    rec.seller_side_total,
                )
            elif (
                rec.end_id.type in ["seller", "landlord"]
                and rec.buyer_broker_is_paid_by == "seller_broker"
                and rec.buyer_broker_pays_trust_excess_to != "seller_broker"
                and rec.other_broker_trust_excess_held == 0
            ):
                commission = rec.total_amount
                _logger.debug(
                    "Our Commission & Tax set to total_amount: %s", rec.total_amount
                )
            else:
                commission = 0.0
                _logger.debug("Our Commission & Tax set to 0.0")
            rec.our_commission_and_tax = commission

    @api.depends(
        "transaction_line_ids.deposited",
        "transaction_line_ids.transaction_type",
        "transaction_line_ids.journal_type",
        "transaction_line_ids.held_by",
    )
    def _compute_commission_we_have_received(self):
        """
        Compute the total commission received excluding trust deposits.
        """
        for rec in self:
            rec.commission_we_have_received = rec._get_commission_we_have_received()
            _logger.debug(
                "Computed Commission Received: %s for Deal ID %s",
                rec.commission_we_have_received,
                rec.id,
            )

    @api.depends(
        "transaction_line_ids.deposited",
        "transaction_line_ids.transaction_type",
    )
    def _compute_commission_balance(self):
        """
        Compute the net commission balance (receipts - payments).
        """
        for rec in self:
            rec.commission_balance = rec._get_commission_balance()
            _logger.debug(
                "Commission Balance for Deal ID %s: %s", rec.id, rec.commission_balance
            )

    # =====================
    # Commission Calculation Methods
    # =====================

    def _get_commission_we_have_received(self):
        """
        Calculate the total commission received excluding buyer or seller deposits.

        Returns:
            float: Commission received excluding trust deposits.
        """
        self.ensure_one()
        commission_transactions = self.transaction_line_ids.filtered(
            lambda t: t.transaction_type == "commission_receipt"
            and t.journal_type == "non_trust"
            and t.held_by == "our_office"
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
            lambda t: t.transaction_type == "commission_receipt"
        )
        commission_payments = self.transaction_line_ids.filtered(
            lambda t: t.transaction_type == "commission_payment"
        )
        total_receipts = sum(t.deposited for t in commission_receipts)
        total_payments = sum(t.deposited for t in commission_payments)
        net_balance = total_receipts - total_payments
        _logger.debug(
            "Net Commission Balance for Deal ID %s: %s",
            self.id,
            net_balance,
        )
        return net_balance
