# models/deals/deal_preferences.py

"""
Module for managing Deal Preferences, including brokerage settings, payment sources,
deposit holdings, trust excess distributions, and conveyancing options. This module
facilitates the configuration and customization of deal-related preferences to ensure
consistent and accurate financial transactions within the system.
"""

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

# Configure the logger for this module
_logger = logging.getLogger(__name__)


class DealPreferences(models.Model):
    """
    Model for storing and managing deal preferences. This includes settings related to
    brokerage preferences, payment sources, deposit holdings, trust excess distributions,
    and conveyancing options. The model inherits from 'mail.thread' and 'mail.activity.mixin'
    to enable chatter and activity tracking.
    """
    _name = "deal.preferences"
    _description = "Deal Preferences"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # ================================
    # Selection Options
    # ================================
    PAYMENT_SOURCE_SELECTION = [
        ("seller_law_firm", "Seller's Law Firm"),
        ("buyer_law_firm", "Buyer's Law Firm"),
        ("buyer_broker", "Buyer's Broker"),
        ("buyer", "Buyer"),
        ("seller", "Seller"),
    ]

    WHO_HOLDS_DEPOSIT_SELECTION = [
        ("seller_broker", "Seller's Broker"),
        ("buyer_broker", "Buyer's Broker"),
        ("seller_law_firm", "Seller's Law Firm"),
        ("buyer_law_firm", "Buyer's Law Firm"),
    ]

    TRUST_EXCESS_SELECTION = [
        ("buyer_law_firm", "Buyer's Law Firm"),
        ("seller_law_firm", "Seller's Law Firm"),
        ("seller", "Seller"),
        ("buyer", "Buyer"),
    ]

    # ================================
    # Fields Definition
    # ================================
    brokerage_preferences_id = fields.Many2one(
        "brokerage.preferences",
        string="Brokerage Preferences",
        ondelete="restrict",
        required=True,
        default=lambda self: self.env["brokerage.preferences"].search([], limit=1),
        help="Reference to the Brokerage Preferences that apply to this deal."
    )
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        ondelete="cascade",
        help="Reference to the specific deal this preference applies to.",
    )
    tax_ids = fields.Many2many(
        "account.tax",
        string="Applicable Taxes",
        tracking=True,
        help="Taxes applicable to this deal."
    )

    # ---------------------
    # Payment Source Selections
    # ---------------------
    seller_broker_is_paid_by = fields.Selection(
        selection=PAYMENT_SOURCE_SELECTION,
        string="Seller's Broker is Paid By",
        tracking=True,
        help="Select who pays the seller's broker."
    )
    buyer_broker_is_paid_by = fields.Selection(
        selection=PAYMENT_SOURCE_SELECTION,
        string="Buyer's Broker is Paid By",
        tracking=True,
        help="Select who pays the buyer's broker."
    )
    who_holds_the_deposit = fields.Selection(
        selection=WHO_HOLDS_DEPOSIT_SELECTION,
        string="Who Holds Deposits",
        tracking=True,
        help="Select who holds the deposits for this deal."
    )

    # ---------------------
    # Trust Excess Selections
    # ---------------------
    seller_broker_pays_trust_excess_to = fields.Selection(
        selection=TRUST_EXCESS_SELECTION,
        string="Seller Broker: Pay Excess Funds To",
        tracking=True,
        help="Select the recipient for excess funds from the seller's broker."
    )
    buyer_broker_pays_trust_excess_to = fields.Selection(
        selection=TRUST_EXCESS_SELECTION,
        string="Buyer Broker: Pay Excess Funds To",
        tracking=True,
        help="Select the recipient for excess funds from the buyer's broker."
    )

    # ---------------------
    # Conveyancing Options
    # ---------------------
    seller_broker_conveys_to_seller_lawyer = fields.Boolean(
        string="Seller Broker Conveys To Seller's Lawyer",
        tracking=True,
        help="Indicates if the seller's broker conveys funds to the seller's lawyer."
    )
    seller_broker_conveys_to_buyer_lawyer = fields.Boolean(
        string="Seller Broker Conveys To Buyer's Lawyer",
        tracking=True,
        help="Indicates if the seller's broker conveys funds to the buyer's lawyer."
    )
    seller_broker_conveys_to_buyer_broker = fields.Boolean(
        string="Seller Broker Conveys To Buyer's Broker",
        tracking=True,
        help="Indicates if the seller's broker conveys funds to the buyer's broker."
    )
    is_seller_end_or_double_end = fields.Boolean(
        string="Is Seller End or Double End",
        tracking=True,
        help="Indicates if the deal is a seller end or a double end."
    )
    buyer_broker_conveys_to_seller_lawyer = fields.Boolean(
        string="Buyer Broker Conveys To Seller's Lawyer",
        tracking=True,
        help="Indicates if the buyer's broker conveys funds to the seller's lawyer."
    )
    buyer_broker_conveys_to_buyer_lawyer = fields.Boolean(
        string="Buyer Broker Conveys To Buyer's Lawyer",
        tracking=True,
        help="Indicates if the buyer's broker conveys funds to the buyer's lawyer."
    )
    buyer_broker_conveys_to_seller_broker = fields.Boolean(
        string="Buyer Broker Conveys To Seller's Broker",
        tracking=True,
        help="Indicates if the buyer's broker conveys funds to the seller's broker."
    )
    brokerage_deposit_policy = fields.Text(
        string="Brokerage Deposit Policy",
        help="Detailed policy regarding brokerage deposits."
    )

    # ================================
    # Methods
    # ================================

    @api.model
    def default_get(self, fields_list):
        """
        Override the default_get method to populate default values from Brokerage Preferences.

        Args:
            fields_list (list): List of fields to get defaults for.

        Returns:
            dict: Dictionary of default values.
        """
        defaults = super().default_get(fields_list)
        brokerage_prefs = self.env["brokerage.preferences"].search([], limit=1)
        if brokerage_prefs:
            field_mapping = {
                'tax_ids': 'tax_ids',
                'seller_broker_is_paid_by': 'seller_broker_is_paid_by',
                'buyer_broker_is_paid_by': 'buyer_broker_is_paid_by',
                'who_holds_the_deposit': 'who_holds_the_deposit',
                'seller_broker_pays_trust_excess_to': 'seller_broker_pays_trust_excess_to',
                'buyer_broker_pays_trust_excess_to': 'buyer_broker_pays_trust_excess_to',
                'seller_broker_conveys_to_seller_lawyer': 'seller_broker_conveys_to_seller_lawyer',
                'seller_broker_conveys_to_buyer_lawyer': 'seller_broker_conveys_to_buyer_lawyer',
                'seller_broker_conveys_to_buyer_broker': 'seller_broker_conveys_to_buyer_broker',
                'is_seller_end_or_double_end': 'is_seller_end_or_double_end',
                'buyer_broker_conveys_to_seller_lawyer': 'buyer_broker_conveys_to_seller_lawyer',
                'buyer_broker_conveys_to_buyer_lawyer': 'buyer_broker_conveys_to_buyer_lawyer',
                'buyer_broker_conveys_to_seller_broker': 'buyer_broker_conveys_to_seller_broker',
                'brokerage_deposit_policy': 'brokerage_deposit_policy',
            }
            for deal_field, brokerage_field in field_mapping.items():
                if deal_field in fields_list:
                    value = getattr(brokerage_prefs, brokerage_field, False)
                    field = self._fields.get(deal_field)
                    if field:
                        if isinstance(field, fields.Many2many):
                            defaults[deal_field] = [(6, 0, value.ids)] if value else [(6, 0, [])]
                        elif isinstance(field, fields.Many2one):
                            defaults[deal_field] = value.id if value else False
                        else:
                            defaults[deal_field] = value
                        _logger.debug(
                            "Default_get: Set %s to %s",
                            deal_field, defaults[deal_field]
                        )
        else:
            _logger.warning("No Brokerage Preferences found to set defaults.")
        return defaults

    @api.onchange('brokerage_preferences_id')
    def _onchange_brokerage_preferences_id(self):
        """
        Update fields based on the selected Brokerage Preferences.
        """
        prefs = self.brokerage_preferences_id
        if prefs:
            field_mapping = {
                'tax_ids': 'tax_ids',
                'seller_broker_is_paid_by': 'seller_broker_is_paid_by',
                'buyer_broker_is_paid_by': 'buyer_broker_is_paid_by',
                'who_holds_the_deposit': 'who_holds_the_deposit',
                'seller_broker_pays_trust_excess_to': 'seller_broker_pays_trust_excess_to',
                'buyer_broker_pays_trust_excess_to': 'buyer_broker_pays_trust_excess_to',
                'seller_broker_conveys_to_seller_lawyer': 'seller_broker_conveys_to_seller_lawyer',
                'seller_broker_conveys_to_buyer_lawyer': 'seller_broker_conveys_to_buyer_lawyer',
                'seller_broker_conveys_to_buyer_broker': 'seller_broker_conveys_to_buyer_broker',
                'is_seller_end_or_double_end': 'is_seller_end_or_double_end',
                'buyer_broker_conveys_to_seller_lawyer': 'buyer_broker_conveys_to_seller_lawyer',
                'buyer_broker_conveys_to_buyer_lawyer': 'buyer_broker_conveys_to_buyer_lawyer',
                'buyer_broker_conveys_to_seller_broker': 'buyer_broker_conveys_to_seller_broker',
                'brokerage_deposit_policy': 'brokerage_deposit_policy',
            }
            for deal_field, brokerage_field in field_mapping.items():
                value = getattr(prefs, brokerage_field, False)
                field = self._fields.get(deal_field)
                if field:
                    if isinstance(field, fields.Many2many):
                        self[deal_field] = [(6, 0, value.ids)] if value else [(6, 0, [])]
                    elif isinstance(field, fields.Many2one):
                        self[deal_field] = value.id if value else False
                    else:
                        self[deal_field] = value
                    _logger.debug(
                        "_onchange_brokerage_preferences_id: Set %s to %s",
                        deal_field, getattr(self, deal_field)
                    )

    # ================================
    # Constraints
    # ================================

    @api.constrains('seller_broker_is_paid_by', 'buyer_broker_is_paid_by')
    def _check_broker_payment_sources(self):
        """
        Ensure that the payment sources for sellers' and buyers' brokers are not the same.
        """
        for record in self:
            if record.seller_broker_is_paid_by and record.buyer_broker_is_paid_by:
                if record.seller_broker_is_paid_by == record.buyer_broker_is_paid_by:
                    _logger.error(
                        "Seller Broker and Buyer Broker have the same payment source: %s",
                        record.seller_broker_is_paid_by
                    )
                    raise ValidationError(
                        _("Seller's Broker and Buyer's Broker cannot be paid by the same source.")
                    )
            _logger.debug(
                "Constrained Check: Seller Broker is paid by %s, Buyer Broker is paid by %s",
                record.seller_broker_is_paid_by,
                record.buyer_broker_is_paid_by
            )

    # ================================
    # Override Unlink Method
    # ================================

    def unlink(self):
        """
        Override the unlink method to prevent deletion of Deal Preferences that are linked to active deals.
        """
        for record in self:
            active_deals = self.env["deal.records"].search([("deal_preferences_id", "=", record.id)])
            if active_deals:
                _logger.warning(
                    "Attempt to delete Deal Preferences ID: %s linked to active deals.",
                    record.id
                )
                raise UserError(
                    _("Cannot delete Deal Preferences linked to active deals. Please unlink or deactivate them first.")
                )
            _logger.debug(
                "Deal Preferences ID: %s is safe to delete.",
                record.id
            )
        return super(DealPreferences, self).unlink()