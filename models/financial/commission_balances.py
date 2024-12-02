# models/financial/commission_balances.py

"""
Module for extending Deal Records with commission balance calculations.
Defines additional computed fields to display commissions and taxes,
and provides methods to calculate and manage these financial metrics.
Ensures accurate tracking of commissions received and balances based on deal attributes.
"""

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class DealRecords(models.Model):
    _inherit = 'deal.records'
    _description = 'Extended Deal Records with Commission Balances'

    # =====================
    # Financial Fields
    # =====================
    our_commission_and_tax = fields.Monetary(
        string="Our Commission & Tax",
        compute="_compute_our_commission_and_tax",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Commission and tax earned by our company based on the deal terms."
    )
    commission_we_have_received = fields.Monetary(
        string="Commission Received",
        compute="_compute_commission_we_have_received",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Total commission received excluding trust deposits."
    )
    commission_balance = fields.Monetary(
        string="Commission Balance",
        compute="_compute_commission_balance",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Net commission balance after subtracting payments."
    )

    # =====================
    # Compute Methods
    # =====================
    @api.depends(
        'end_id.type',
        'seller_side_total',
        'buyer_side_total',
        'total_amount',
        'buyer_broker_is_paid_by',
        'seller_broker_pays_trust_excess_to',
        'buyer_broker_pays_trust_excess_to',
        'other_broker_trust_excess_held',
        'deal_class_id',
        'our_trust_balance_held',
        'commission_we_have_received',
    )
    def _compute_our_commission_and_tax(self):
        """
        Compute the commission and tax earned based on deal type and brokerage payments.
        """
        for rec in self:
            commission = 0.0
            end_type = rec.end_id.type
            broker_paid_by = rec.buyer_broker_is_paid_by
            broker_pays_excess_to = rec.buyer_broker_pays_trust_excess_to
            other_broker_excess = rec.other_broker_trust_excess_held

            _logger.debug(
                "Computing Our Commission & Tax for Deal ID %s: End Type=%s, Broker Paid By=%s, "
                "Broker Pays Excess To=%s, Other Broker Excess Held=%s",
                rec.id, end_type, broker_paid_by, broker_pays_excess_to, other_broker_excess
            )

            if end_type in ["buyer", "tenant"]:
                commission = rec.buyer_side_total or 0.0
                _logger.debug("Commission set to buyer_side_total: %s", commission)
            elif end_type == "double_end":
                commission = rec.total_amount or 0.0
                _logger.debug("Commission set to total_amount: %s", commission)
            elif end_type in ["seller", "landlord"]:
                if broker_paid_by == "seller_broker":
                    if broker_pays_excess_to == "seller_broker":
                        commission = rec.total_amount or 0.0
                        _logger.debug("Commission set to total_amount: %s", commission)
                    elif broker_pays_excess_to != "seller_broker" and other_broker_excess > 0:
                        commission = rec.seller_side_total or 0.0
                        _logger.debug("Commission set to seller_side_total: %s", commission)
                    else:
                        commission = rec.total_amount or 0.0
                        _logger.debug("Commission set to total_amount: %s", commission)
                else:
                    commission = 0.0
                    _logger.debug("Commission set to 0.0 due to broker payment conditions.")
            else:
                commission = 0.0
                _logger.debug("Commission set to 0.0 for unhandled end type.")

            rec.our_commission_and_tax = commission

    @api.depends(
        'transaction_line_ids.deposited',
        'transaction_line_ids.transaction_type',
        'transaction_line_ids.journal_type',
        'transaction_line_ids.held_by',
    )
    def _compute_commission_we_have_received(self):
        """
        Compute the total commission received excluding trust deposits.
        """
        for rec in self:
            commission_received = rec._get_commission_we_have_received()
            rec.commission_we_have_received = commission_received
            _logger.debug(
                "Commission Received for Deal ID %s: %s",
                rec.id,
                commission_received,
            )

    @api.depends(
        'transaction_line_ids.deposited',
        'transaction_line_ids.transaction_type',
    )
    def _compute_commission_balance(self):
        """
        Compute the net commission balance (receipts - payments).
        """
        for rec in self:
            commission_balance = rec._get_commission_balance()
            rec.commission_balance = commission_balance
            _logger.debug(
                "Commission Balance for Deal ID %s: %s",
                rec.id,
                commission_balance,
            )

    # =====================
    # Helper Methods
    # =====================
    def _get_commission_we_have_received(self):
        """
        Calculate the total commission received excluding buyer or seller deposits.

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
            rec._compute_our_commission_and_tax()
            rec._compute_commission_we_have_received()
            rec._compute_commission_balance()
            _logger.info(
                "Updated commission fields for Deal ID %s.",
                rec.id,
            )