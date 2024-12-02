# models/financial/trust_balances.py

"""
Module for calculating and managing trust balances within Deal Records.
Extends the 'deal.records' model to compute various trust-related financial metrics
based on transaction data. Ensures accurate tracking of deposits, trust balances,
and excess funds held by both our brokerage and other brokers involved in the deal.
"""

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DealRecords(models.Model):
    _inherit = 'deal.records'
    _description = 'Calculate Trust Balances'

    # =====================
    # Financial Fields
    # =====================
    deposit_received_from_buyer = fields.Monetary(
        string="Deposit Received from Buyer",
        compute="_compute_deposit_received_from_buyer",
        currency_field="currency_id",
        tracking=True,
        store=True,
        help="Total deposit received from the buyer.",
    )
    deposit_received_from_seller = fields.Monetary(
        string="Deposit Received from Seller",
        compute="_compute_deposit_received_from_seller",
        currency_field="currency_id",
        tracking=True,
        store=True,
        help="Total deposit received from the seller.",
    )

    our_trust_balance_held = fields.Monetary(
        string="Our Trust Balance Held",
        compute="_compute_our_trust_balance_held",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Amount of trust balance held by our brokerage.",
    )
    our_trust_excess_held = fields.Monetary(
        string="Our Trust Excess Held",
        compute="_compute_our_trust_excess_held",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Excess trust funds held by our brokerage after fulfilling obligations.",
    )
    other_broker_trust_balance = fields.Monetary(
        string="Other Broker Deposit",
        compute="_compute_other_broker_trust_balance",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Trust balance held by the other broker involved in the deal.",
    )
    other_broker_trust_excess_held = fields.Monetary(
        string="Other Broker Trust Excess Held",
        compute="_compute_other_broker_trust_excess_held",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Excess trust funds held by the other broker after fulfilling obligations.",
    )

    # =====================
    # Trust Calculation Methods
    # =====================

    def _get_trust_transactions(self, transaction_types=None, held_by=None, received_from=None):
        """
        Helper method to retrieve trust transactions based on specified criteria.

        :param transaction_types: List of transaction types to filter.
        :param held_by: Entity holding the funds ('our_office' or 'other_broker').
        :param received_from: Entity from whom the funds were received ('buyer' or 'seller').
        :return: Recordset of 'transaction.line' records matching the criteria.
        """
        self.ensure_one()
        domain = [('deal_id', '=', self.id)]
        if transaction_types:
            domain.append(('transaction_type', 'in', transaction_types))
        if held_by:
            domain.append(('held_by', '=', held_by))
        if received_from:
            domain.append(('received_from_id', '=', received_from))
        transactions = self.env['transaction.line'].search(domain)
        _logger.debug(
            "Retrieved %d trust transactions for Deal ID %s with domain %s.",
            len(transactions),
            self.id,
            domain,
        )
        return transactions

    def get_total_trust_balance(self):
        """
        Calculate the overall trust balance for the deal.

        :return: Total trust balance as a float.
        """
        trust_transactions = self._get_trust_transactions(
            transaction_types=['trust_receipt', 'trust_refund', 'trust_excess_payment']
        )
        total_amount = sum(t.amount for t in trust_transactions)
        _logger.debug(
            "Total Trust Balance for Deal ID %s: %s",
            self.id,
            total_amount,
        )
        return total_amount

    def get_our_trust_balance(self):
        """
        Calculate the trust balance held by our office.

        :return: Our trust balance as a float.
        """
        trust_transactions = self._get_trust_transactions(
            transaction_types=['trust_receipt', 'trust_refund', 'trust_excess_payment'],
            held_by='our_office'
        )
        total_amount = sum(t.amount for t in trust_transactions)
        _logger.debug(
            "Our Trust Balance for Deal ID %s: %s",
            self.id,
            total_amount,
        )
        return total_amount

    def get_other_broker_trust_balance(self):
        """
        Calculate the trust balance held by the other broker.

        :return: Other broker's trust balance as a float.
        """
        trust_transactions = self._get_trust_transactions(
            transaction_types=['trust_receipt', 'trust_refund', 'trust_excess_payment'],
            held_by='other_broker'
        )
        total_amount = sum(t.amount for t in trust_transactions)
        _logger.debug(
            "Other Broker Trust Balance for Deal ID %s: %s",
            self.id,
            total_amount,
        )
        return total_amount

    def get_deposit_received_from_buyer(self):
        """
        Calculate the trust deposit received from the buyer.

        :return: Deposit amount from buyer as a float.
        """
        trust_transactions = self._get_trust_transactions(
            transaction_types=['trust_receipt'],
            received_from='buyer'
        )
        total_amount = sum(t.amount for t in trust_transactions)
        _logger.debug(
            "Deposit Received from Buyer for Deal ID %s: %s",
            self.id,
            total_amount,
        )
        return total_amount

    def get_deposit_received_from_seller(self):
        """
        Calculate the trust deposit received from the seller.

        :return: Deposit amount from seller as a float.
        """
        trust_transactions = self._get_trust_transactions(
            transaction_types=['trust_receipt'],
            received_from='seller'
        )
        total_amount = sum(t.amount for t in trust_transactions)
        _logger.debug(
            "Deposit Received from Seller for Deal ID %s: %s",
            self.id,
            total_amount,
        )
        return total_amount

    def get_trust_excess_paid(self, held_by='our_office'):
        """
        Calculate the trust excess paid by a specific entity.

        :param held_by: Entity that paid the excess ('our_office' or 'other_broker').
        :return: Total trust excess paid as a float.
        """
        excess_transactions = self._get_trust_transactions(
            transaction_types=['trust_excess_payment'],
            held_by=held_by
        )
        total_amount = sum(t.amount for t in excess_transactions)
        _logger.debug(
            "Trust Excess Paid (held by %s) for Deal ID %s: %s",
            held_by,
            self.id,
            total_amount,
        )
        return total_amount

    # =====================
    # Computed Methods for Fields
    # =====================

    @api.depends('transaction_line_ids.amount', 'transaction_line_ids.transaction_type', 'transaction_line_ids.held_by')
    def _compute_our_trust_balance_held(self):
        """
        Compute our trust balance held using the integrated calculation methods.
        """
        for rec in self:
            rec.our_trust_balance_held = rec.get_our_trust_balance()
            _logger.debug(
                "Computed 'Our Trust Balance Held': %s for Deal ID %s",
                rec.our_trust_balance_held,
                rec.id,
            )

    @api.depends('transaction_line_ids.amount', 'transaction_line_ids.transaction_type', 'transaction_line_ids.held_by')
    def _compute_other_broker_trust_balance(self):
        """
        Compute other broker's trust balance using the integrated calculation methods.
        """
        for rec in self:
            rec.other_broker_trust_balance = rec.get_other_broker_trust_balance()
            _logger.debug(
                "Computed 'Other Broker Trust Balance': %s for Deal ID %s",
                rec.other_broker_trust_balance,
                rec.id,
            )

    @api.depends('transaction_line_ids.amount', 'transaction_line_ids.transaction_type', 'transaction_line_ids.held_by')
    def _compute_other_broker_trust_excess_held(self):
        """
        Compute other broker's trust excess held.
        """
        for rec in self:
            total_excess_paid = rec.get_trust_excess_paid(held_by='other_broker')
            rec.other_broker_trust_excess_held = rec.other_broker_trust_balance - total_excess_paid
            _logger.debug(
                "Computed 'Other Broker Trust Excess Held': %s for Deal ID %s",
                rec.other_broker_trust_excess_held,
                rec.id,
            )

    @api.depends('transaction_line_ids.amount', 'transaction_line_ids.transaction_type', 'transaction_line_ids.received_from_id')
    def _compute_deposit_received_from_buyer(self):
        """
        Compute the deposit received from the buyer.
        """
        for rec in self:
            rec.deposit_received_from_buyer = rec.get_deposit_received_from_buyer()
            _logger.debug(
                "Computed 'Deposit Received from Buyer': %s for Deal ID %s",
                rec.deposit_received_from_buyer,
                rec.id,
            )

    @api.depends('transaction_line_ids.amount', 'transaction_line_ids.transaction_type', 'transaction_line_ids.received_from_id')
    def _compute_deposit_received_from_seller(self):
        """
        Compute the deposit received from the seller.
        """
        for rec in self:
            rec.deposit_received_from_seller = rec.get_deposit_received_from_seller()
            _logger.debug(
                "Computed 'Deposit Received from Seller': %s for Deal ID %s",
                rec.deposit_received_from_seller,
                rec.id,
            )

    @api.depends(
        "end_id.type",
        "seller_broker_is_paid_by",
        "buyer_broker_is_paid_by",
        "buyer_broker_pays_trust_excess_to",
        "seller_broker_pays_trust_excess_to",
        "our_trust_balance_held",
        "commission_we_have_received",
        "other_broker_trust_balance",
        "our_commission_and_tax_receivable",
        "other_broker_trust_excess_held",
    )
    def _compute_our_trust_excess_held(self):
        """
        Compute the excess held based on commission and deposits.
        """
        for rec in self:
            total_funds = rec.our_trust_balance_held + rec.commission_we_have_received
            excess = 0.0

            # Conditions based on deal type and broker payment settings
            if rec.end_id.type in ["seller", "landlord"]:
                if (
                    rec.buyer_broker_is_paid_by == "seller_broker"
                    and rec.buyer_broker_pays_trust_excess_to == "seller_broker"
                ):
                    if total_funds > rec.our_commission_and_tax_receivable:
                        excess = total_funds - rec.our_commission_and_tax_receivable
                        _logger.debug(
                            "Our Trust Excess Held (Condition 1): %s for Deal ID %s",
                            excess,
                            rec.id,
                        )
                        rec.our_trust_excess_held = excess
                        continue
                if (
                    rec.buyer_broker_is_paid_by == "seller_broker"
                    and rec.buyer_broker_pays_trust_excess_to != "seller_broker"
                    and rec.other_broker_trust_excess_held == 0
                ):
                    if total_funds > rec.our_commission_and_tax_receivable:
                        excess = total_funds - rec.our_commission_and_tax_receivable
                        _logger.debug(
                            "Our Trust Excess Held (Condition 2): %s for Deal ID %s",
                            excess,
                            rec.id,
                        )
                        rec.our_trust_excess_held = excess
                        continue

            # General excess calculation
            if rec.our_commission_and_tax_receivable < total_funds:
                excess = total_funds - rec.our_commission_and_tax_receivable
                _logger.debug(
                    "Our Trust Excess Held (General): %s for Deal ID %s",
                    excess,
                    rec.id,
                )
                rec.our_trust_excess_held = excess
            else:
                rec.our_trust_excess_held = 0.0
                _logger.debug(
                    "Our Trust Excess Held set to 0.0 for Deal ID %s",
                    rec.id,
                )