# models/deals/due_to_due_from.py

"""
Module for managing 'Due To' and 'Due From' calculations within Deal Records.
Extends the 'deal.records' model to compute various financial obligations
and receivables based on deal attributes and transaction data.
Ensures accurate tracking of amounts owed to and from different parties involved
in the deal, such as brokers, law firms, buyers, and sellers.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class DealRecords(models.Model):
    _inherit = 'deal.records'
    _description = 'Due To and Due From Calculations'

    # =====================
    # Due To Fields
    # =====================
    due_to_other_broker = fields.Monetary(
        string="Due to Broker",
        compute="_compute_due_to_and_due_from",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Amount due to the other broker involved in the deal.",
    )
    payable_to_other_broker = fields.Monetary(
        string="Payable to Broker",
        compute="_compute_payable_to_other_broker",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Net amount payable to the other broker after considering deposits.",
    )
    due_to_buyer_law_firm = fields.Monetary(
        string="Due to Buyer's Law Firm",
        compute="_compute_due_to_and_due_from",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Amount due to the buyer's law firm.",
    )
    due_to_seller_law_firm = fields.Monetary(
        string="Due to Seller's Law Firm",
        compute="_compute_due_to_and_due_from",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Amount due to the seller's law firm.",
    )
    due_to_buyer = fields.Monetary(
        string="Due to Buyer",
        compute="_compute_due_to_and_due_from",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Amount due to the buyer.",
    )
    due_to_seller = fields.Monetary(
        string="Due to Seller",
        compute="_compute_due_to_and_due_from",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Amount due to the seller.",
    )
    due_to_our_brokerage = fields.Monetary(
        string="Due to Our Brokerage",
        compute="_compute_due_to_and_due_from",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Amount due to our brokerage from the deal.",
    )

    # =====================
    # Due From Fields
    # =====================
    due_from_other_broker = fields.Monetary(
        string="Due From Broker",
        compute="_compute_due_to_and_due_from",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Amount due from the other broker involved in the deal.",
    )
    due_from_buyer_law_firm = fields.Monetary(
        string="Due From Buyer's Law Firm",
        compute="_compute_due_to_and_due_from",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Amount due from the buyer's law firm.",
    )
    due_from_seller_law_firm = fields.Monetary(
        string="Due From Seller's Law Firm",
        compute="_compute_due_to_and_due_from",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Amount due from the seller's law firm.",
    )
    due_from_buyer = fields.Monetary(
        string="Due From Buyer",
        compute="_compute_due_to_and_due_from",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Amount due from the buyer.",
    )
    due_from_seller = fields.Monetary(
        string="Due From Seller",
        compute="_compute_due_to_and_due_from",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Amount due from the seller.",
    )

    # =====================
    # Compute Methods
    # =====================
    @api.depends(
        'our_commission_and_tax',
        'buyer_side_total',
        'seller_side_total',
        'other_broker_trust_balance',
        'our_trust_excess_held',
        'end_id.type',
        'seller_broker_is_paid_by',
        'buyer_broker_is_paid_by',
        'our_trust_balance_held',
        'seller_broker_pays_trust_excess_to',
        'buyer_broker_pays_trust_excess_to',
        'transaction_line_ids',
        'deal_preferences_id',
    )
    def _compute_due_to_and_due_from(self):
        """
        Compute all 'Due To' and 'Due From' fields based on various conditions and financial data.
        """
        for rec in self:
            # Initialize all 'Due To' and 'Due From' fields to zero
            rec._initialize_due_fields()

            # Fetch Deal Preferences
            deal_preference = rec.deal_preferences_id
            if not deal_preference or not deal_preference.trust_bank_account:
                _logger.warning(
                    "Deal ID %s: Trust Bank Account is not configured in Deal Preferences.",
                    rec.id,
                )
                # Cannot proceed with calculations without trust bank account
                continue

            # Calculate Commission Received
            total_commission_we_have_received = rec.commission_we_have_received
            _logger.debug(
                "Total Commission Received for Deal ID %s: %s",
                rec.id,
                total_commission_we_have_received,
            )

            # The field 'other_broker_trust_balance' should be computed elsewhere
            other_broker_trust_balance = rec.other_broker_trust_balance

            # Compute 'Due To' Fields
            rec._compute_due_to_fields()

            # Compute 'Due From' Fields
            rec._compute_due_from_fields()

            # Logical Consistency Checks: Ensure no negative dues
            rec._validate_due_fields()

    def _initialize_due_fields(self):
        """
        Initialize all 'Due To' and 'Due From' fields to zero.
        """
        due_fields = [
            'due_to_other_broker',
            'due_to_buyer_law_firm',
            'due_to_seller_law_firm',
            'due_to_buyer',
            'due_to_seller',
            'due_from_other_broker',
            'due_from_buyer_law_firm',
            'due_from_seller_law_firm',
            'due_from_buyer',
            'due_from_seller',
            'due_to_our_brokerage',
        ]
        for field_name in due_fields:
            setattr(self, field_name, 0.0)
        _logger.debug("Initialized all 'Due To' and 'Due From' fields to 0.0 for Deal ID %s.", self.id)

    def _compute_due_to_fields(self):
        """
        Compute 'Due To' fields based on deal conditions and financial data.
        """
        for rec in self:
            # Compute Due to Broker
            if rec.buyer_broker_is_paid_by == "seller_broker":
                if rec.end_id.type in ["seller", "landlord"]:
                    rec.due_to_other_broker = rec.buyer_side_total or 0.0
                    _logger.debug(
                        "Due to Broker set to Buyer Side Total for Deal ID %s: %s",
                        rec.id,
                        rec.buyer_side_total,
                    )
                elif (
                    rec.end_id.type in ["buyer", "tenant"]
                    and rec.buyer_broker_pays_trust_excess_to == "seller_broker"
                ):
                    rec.due_to_other_broker = max(rec.our_trust_excess_held, 0.0)
                    _logger.debug(
                        "Due to Other Broker set to Our Trust Excess Held for Deal ID %s: %s",
                        rec.id,
                        rec.due_to_other_broker,
                    )

            # Compute Due to Law Firms, Buyer, and Seller
            if rec.our_trust_excess_held > 0:
                trust_excess = rec.our_trust_excess_held
                pays_to = (
                    rec.seller_broker_pays_trust_excess_to
                    if rec.end_id.type in ('seller', 'landlord', 'double_end')
                    else rec.buyer_broker_pays_trust_excess_to
                )

                if pays_to == 'buyer_law_firm':
                    rec.due_to_buyer_law_firm = trust_excess
                    _logger.debug(
                        "Due to Buyer's Law Firm for Deal ID %s: %s",
                        rec.id,
                        trust_excess,
                    )
                elif pays_to == 'seller_law_firm':
                    rec.due_to_seller_law_firm = trust_excess
                    _logger.debug(
                        "Due to Seller's Law Firm for Deal ID %s: %s",
                        rec.id,
                        trust_excess,
                    )
                elif pays_to == 'buyer':
                    rec.due_to_buyer = trust_excess
                    _logger.debug(
                        "Due to Buyer for Deal ID %s: %s",
                        rec.id,
                        trust_excess,
                    )
                elif pays_to == 'seller':
                    rec.due_to_seller = trust_excess
                    _logger.debug(
                        "Due to Seller for Deal ID %s: %s",
                        rec.id,
                        trust_excess,
                    )

            # Compute Due to Our Brokerage
            rec._compute_due_to_our_brokerage()

    def _compute_due_to_our_brokerage(self):
        """
        Compute 'Due to Our Brokerage' field based on trust excess and commission data.
        """
        for rec in self:
            if rec.our_trust_excess_held > 0:
                rec.due_to_our_brokerage = 0.0
                _logger.debug(
                    "Due to Our Brokerage remains 0 for Deal ID %s due to Excess Held > 0",
                    rec.id,
                )
            else:
                l_value = rec.our_commission_and_tax - (
                    rec.our_trust_balance_held
                    + rec.other_broker_trust_balance
                    + rec.commission_we_have_received
                )
                ls_value = rec.our_commission_and_tax - (
                    rec.our_trust_balance_held + rec.commission_we_have_received
                )

                if (
                    rec.end_id.type in ["seller", "landlord"]
                    and rec.buyer_broker_is_paid_by == "seller_broker"
                ):
                    if (
                        rec.buyer_broker_pays_trust_excess_to == "seller_broker"
                        and l_value > 0
                    ):
                        rec.due_to_our_brokerage = l_value
                        _logger.debug(
                            "Due to Our Brokerage set to l_value for Deal ID %s: %s",
                            rec.id,
                            l_value,
                        )
                    elif (
                        rec.buyer_broker_pays_trust_excess_to != "seller_broker"
                        and rec.other_broker_trust_excess_held == 0
                        and l_value > 0
                    ):
                        rec.due_to_our_brokerage = l_value
                        _logger.debug(
                            "Due to Our Brokerage set to l_value for Deal ID %s: %s",
                            rec.id,
                            l_value,
                        )
                    elif rec.our_commission_and_tax > (
                        rec.our_trust_balance_held + rec.commission_we_have_received
                    ):
                        rec.due_to_our_brokerage = ls_value
                        _logger.debug(
                            "Due to Our Brokerage set to ls_value for Deal ID %s: %s",
                            rec.id,
                            ls_value,
                        )

    def _compute_due_from_fields(self):
        """
        Compute 'Due From' fields based on deal conditions and financial data.
        """
        for rec in self:
            # Compute Due From Buyer's Law Firm
            if (
                rec.end_id.type in ('seller', 'landlord')
                and rec.seller_broker_is_paid_by == 'buyer_law_firm'
            ):
                rec.due_from_buyer_law_firm = max(rec.our_commission_and_tax - (
                    rec.our_trust_balance_held
                    + rec.commission_we_have_received
                ), 0.0)
                _logger.debug(
                    "Due From Buyer's Law Firm for Deal ID %s: %s",
                    rec.id,
                    rec.due_from_buyer_law_firm,
                )
            elif (
                rec.end_id.type in ('buyer', 'tenant')
                and rec.buyer_broker_is_paid_by == 'buyer_law_firm'
            ):
                rec.due_from_buyer_law_firm = max(rec.our_commission_and_tax - (
                    rec.our_trust_balance_held + rec.commission_we_have_received
                ), 0.0)
                _logger.debug(
                    "Due From Buyer's Law Firm for Deal ID %s: %s",
                    rec.id,
                    rec.due_from_buyer_law_firm,
                )

            # Compute Due From Seller's Law Firm
            if (
                rec.end_id.type in ('seller', 'landlord')
                and rec.seller_broker_is_paid_by == 'seller_law_firm'
            ):
                rec.due_from_seller_law_firm = max(rec.our_commission_and_tax - (
                    rec.our_trust_balance_held
                    + rec.commission_we_have_received
                ), 0.0)
                _logger.debug(
                    "Due From Seller's Law Firm for Deal ID %s: %s",
                    rec.id,
                    rec.due_from_seller_law_firm,
                )
            elif (
                rec.end_id.type in ('buyer', 'tenant')
                and rec.buyer_broker_is_paid_by == 'seller_law_firm'
            ):
                rec.due_from_seller_law_firm = max(rec.our_commission_and_tax - (
                    rec.our_trust_balance_held + rec.commission_we_have_received
                ), 0.0)
                _logger.debug(
                    "Due From Seller's Law Firm for Deal ID %s: %s",
                    rec.id,
                    rec.due_from_seller_law_firm,
                )

            # Compute Due From Buyer
            if (
                rec.end_id.type in ('seller', 'landlord')
                and rec.seller_broker_is_paid_by == 'buyer'
            ):
                rec.due_from_buyer = max(rec.our_commission_and_tax - (
                    rec.our_trust_balance_held
                    + rec.commission_we_have_received
                ), 0.0)
                _logger.debug(
                    "Due From Buyer for Deal ID %s: %s",
                    rec.id,
                    rec.due_from_buyer,
                )
            elif (
                rec.end_id.type in ('buyer', 'tenant')
                and rec.buyer_broker_is_paid_by == 'buyer'
            ):
                rec.due_from_buyer = max(rec.our_commission_and_tax - (
                    rec.our_trust_balance_held + rec.commission_we_have_received
                ), 0.0)
                _logger.debug(
                    "Due From Buyer for Deal ID %s: %s",
                    rec.id,
                    rec.due_from_buyer,
                )

            # Compute Due From Seller
            if (
                rec.end_id.type in ('seller', 'landlord')
                and rec.seller_broker_is_paid_by == 'seller'
            ):
                rec.due_from_seller = max(rec.our_commission_and_tax - (
                    rec.our_trust_balance_held
                    + rec.commission_we_have_received
                ), 0.0)
                _logger.debug(
                    "Due From Seller for Deal ID %s: %s",
                    rec.id,
                    rec.due_from_seller,
                )
            elif (
                rec.end_id.type in ('buyer', 'tenant')
                and rec.buyer_broker_is_paid_by == 'seller'
            ):
                rec.due_from_seller = max(rec.our_commission_and_tax - (
                    rec.our_trust_balance_held + rec.commission_we_have_received
                ), 0.0)
                _logger.debug(
                    "Due From Seller for Deal ID %s: %s",
                    rec.id,
                    rec.due_from_seller,
                )

            # Compute Due From Other Broker
            rec._compute_due_from_other_broker()

    def _compute_due_from_other_broker(self):
        """
        Compute 'Due From Broker' based on the deal type and broker payment conditions.
        """
        for rec in self:
            if rec.end_id.type in ["buyer", "tenant"] and rec.buyer_broker_is_paid_by == "seller_broker":
                calculated_due = rec.buyer_side_total - (
                    rec.our_trust_balance_held + rec.commission_we_have_received
                )
                rec.due_from_other_broker = max(calculated_due, 0.0) if rec.our_trust_balance_held < rec.buyer_side_total else 0.0
                _logger.debug(
                    "Due From Broker for Deal ID %s: %s",
                    rec.id,
                    rec.due_from_other_broker,
                )
            elif rec.end_id.type in ["seller", "landlord"]:
                if (
                    rec.other_broker_trust_excess_held > 0
                    and rec.buyer_broker_pays_trust_excess_to == "seller_broker"
                ):
                    rec.due_from_other_broker = rec.other_broker_trust_excess_held
                    _logger.debug(
                        "Due From Broker set to Other Broker Excess for Deal ID %s: %s",
                        rec.id,
                        rec.due_from_other_broker,
                    )
            else:
                rec.due_from_other_broker = 0.0
                _logger.debug(
                    "Due From Broker set to 0.0 by default for Deal ID %s",
                    rec.id,
                )

    def _validate_due_fields(self):
        """
        Validate that all 'Due To' and 'Due From' fields are non-negative.
        """
        for rec in self:
            due_fields = [
                'due_to_other_broker',
                'due_to_buyer_law_firm',
                'due_to_seller_law_firm',
                'due_to_buyer',
                'due_to_seller',
                'due_from_other_broker',
                'due_from_buyer_law_firm',
                'due_from_seller_law_firm',
                'due_from_buyer',
                'due_from_seller',
            ]
            errors = []
            for field_name in due_fields:
                due_amount = getattr(rec, field_name)
                if due_amount < 0:
                    errors.append(_("Amount in '%s' cannot be negative.") % rec._fields[field_name].string)

            if errors:
                _logger.warning(
                    "Deal ID %s has negative financial values: %s",
                    rec.id,
                    '; '.join(errors),
                )
                raise ValidationError("\n".join(errors))

    @api.depends(
        "due_to_other_broker",
        "other_broker_trust_balance",
    )
    def _compute_payable_to_other_broker(self):
        """
        Compute the amount payable to the other broker taking into consideration any deposits they hold.
        """
        for rec in self:
            if rec.other_broker_trust_balance >= rec.due_to_other_broker:
                rec.payable_to_other_broker = 0.0
                _logger.debug(
                    "Payable to Broker set to 0.0 for Deal ID %s because deposit >= due_to_other_broker",
                    rec.id,
                )
            elif rec.due_to_other_broker > 0:
                rec.payable_to_other_broker = rec.due_to_other_broker - rec.other_broker_trust_balance
                _logger.debug(
                    "Payable to Broker computed for Deal ID %s: %s",
                    rec.id,
                    rec.payable_to_other_broker,
                )
            else:
                rec.payable_to_other_broker = 0.0
                _logger.debug(
                    "Payable to Broker set to 0.0 by default for Deal ID %s",
                    rec.id,
                )

    # =====================
    # Constraints
    # =====================
    @api.constrains(
        "commission_we_have_received",
        "due_to_other_broker",
        "due_to_buyer_law_firm",
        "due_to_seller_law_firm",
        "due_to_buyer",
        "due_to_seller",
    )
    def _check_financials_positive(self):
        """
        Ensure that all 'Due To' fields and 'Commission We Have Received' are non-negative.
        """
        for record in self:
            errors = []
            if record.commission_we_have_received < 0:
                errors.append(_("Commission Received cannot be negative."))
            if record.due_to_other_broker < 0:
                errors.append(_("Amount Due to Broker cannot be negative."))
            if record.due_to_buyer_law_firm < 0:
                errors.append(_("Amount Due to Buyer's Law Firm cannot be negative."))
            if record.due_to_seller_law_firm < 0:
                errors.append(_("Amount Due to Seller's Law Firm cannot be negative."))
            if record.due_to_buyer < 0:
                errors.append(_("Amount Due to Buyer cannot be negative."))
            if record.due_to_seller < 0:
                errors.append(_("Amount Due to Seller cannot be negative."))

            if errors:
                _logger.warning(
                    "Deal ID %s has negative financial values: %s",
                    record.id,
                    '; '.join(errors),
                )
                raise ValidationError("\n".join(errors))

    @api.constrains(
        "amount_receivable",
        "deposit_received_from_buyer",
        "deposit_received_from_seller",
        "commission_we_have_received",
    )
    def _check_financial_totals(self):
        """
        Ensure that the sum of deposits and funds received does not exceed the amount receivable.
        """
        for record in self:
            total_received = (
                record.deposit_received_from_buyer
                + record.deposit_received_from_seller
                + record.commission_we_have_received
            )
            if total_received > record.amount_receivable:
                error_msg = _(
                    "Total deposits and funds received (%s) exceed the amount receivable (%s) for Deal '%s'."
                ) % (total_received, record.amount_receivable, record.name)
                _logger.error(error_msg)
                raise ValidationError(error_msg)

    @api.constrains(
        "amount_receivable",
        "deposit_received_from_buyer",
        "deposit_received_from_seller",
        "commission_receivable",
    )
    def _check_required_funds_positive(self):
        """
        Ensure that the required funds are not negative.
        """
        for rec in self:
            required_funds = rec.amount_receivable - (
                rec.deposit_received_from_buyer
                + rec.deposit_received_from_seller
                + rec.commission_receivable
            )
            if required_funds < 0:
                error_msg = _(
                    "Required funds cannot be negative for Deal '%s'. Please review the deposits and commissions."
                ) % rec.name
                _logger.error(error_msg)
                raise ValidationError(error_msg)