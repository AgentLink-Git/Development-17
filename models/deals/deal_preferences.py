# models/deals/deal_preferences.py

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class DealPreferences(models.Model):
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
    )

    tax_ids = fields.Many2many(
        "account.tax",
        string="Taxes",
        tracking=True,
    )

    # Payment Source Selections
    seller_broker_is_paid_by = fields.Selection(
        selection=PAYMENT_SOURCE_SELECTION,
        string="Seller's Broker is Paid By",
        tracking=True,
    )
    buyer_broker_is_paid_by = fields.Selection(
        selection=PAYMENT_SOURCE_SELECTION,
        string="Buyer's Broker is Paid By",
        tracking=True,
    )
    who_holds_the_deposit = fields.Selection(
        selection=WHO_HOLDS_DEPOSIT_SELECTION,
        string="Who Holds Deposits",
        tracking=True,
    )

    seller_broker_pays_trust_excess_to = fields.Selection(
        selection=TRUST_EXCESS_SELECTION,
        string="Seller Broker: Pay Excess Funds To",
        tracking=True,
    )
    buyer_broker_pays_trust_excess_to = fields.Selection(
        selection=TRUST_EXCESS_SELECTION,
        string="Buyer Broker: Pay Excess Funds To",
        tracking=True,
    )

    # Conveyancing Options
    seller_broker_conveys_to_seller_lawyer = fields.Boolean(
        string="Seller Broker Conveys To Seller's Lawyer",
    )
    seller_broker_conveys_to_buyer_lawyer = fields.Boolean(
        string="Seller Broker Conveys To Buyer's Lawyer",
    )
    seller_broker_conveys_to_buyer_broker = fields.Boolean(
        string="Seller Broker Conveys To Buyer's Broker",
    )
    is_seller_end_or_double_end = fields.Boolean(
        string="Is Seller End or Double End",
    )
    buyer_broker_conveys_to_seller_lawyer = fields.Boolean(
        string="Buyer Broker Conveys To Seller's Lawyer",
    )
    buyer_broker_conveys_to_buyer_lawyer = fields.Boolean(
        string="Buyer Broker Conveys To Buyer's Lawyer",
    )
    buyer_broker_conveys_to_seller_broker = fields.Boolean(
        string="Buyer Broker Conveys To Seller's Broker",
    )
    brokerage_deposit_policy = fields.Text(
        string="Brokerage Deposit Policy",
    )

    # ================================
    # Methods
    # ================================
    @api.model
    def default_get(self, fields_list):
        """Populate defaults from Brokerage Preferences."""
        defaults = super().default_get(fields_list)
        brokerage_prefs = self.env["brokerage.preferences"].search([], limit=1)
        if brokerage_prefs:
            field_mapping = {
                "tax_ids": "tax_ids",
                "seller_broker_is_paid_by": "seller_broker_is_paid_by",
                "buyer_broker_is_paid_by": "buyer_broker_is_paid_by",
                "who_holds_the_deposit": "who_holds_the_deposit",
                "seller_broker_pays_trust_excess_to": "seller_broker_pays_trust_excess_to",
                "buyer_broker_pays_trust_excess_to": "buyer_broker_pays_trust_excess_to",
                "seller_broker_conveys_to_seller_lawyer": "seller_broker_conveys_to_seller_lawyer",
                "seller_broker_conveys_to_buyer_lawyer": "seller_broker_conveys_to_buyer_lawyer",
                "seller_broker_conveys_to_buyer_broker": "seller_broker_conveys_to_buyer_broker",
                "is_seller_end_or_double_end": "is_seller_end_or_double_end",
                "buyer_broker_conveys_to_seller_lawyer": "buyer_broker_conveys_to_seller_lawyer",
                "buyer_broker_conveys_to_buyer_lawyer": "buyer_broker_conveys_to_buyer_lawyer",
                "buyer_broker_conveys_to_seller_broker": "buyer_broker_conveys_to_seller_broker",
                "brokerage_deposit_policy": "brokerage_deposit_policy",
            }
            for deal_field, brokerage_field in field_mapping.items():
                if deal_field in fields_list:
                    value = getattr(brokerage_prefs, brokerage_field, False)
                    field = self._fields.get(deal_field)
                    if field:
                        if isinstance(field, fields.Many2many):
                            defaults[deal_field] = [(6, 0, value.ids)]
                        elif isinstance(field, fields.Many2one):
                            defaults[deal_field] = value.id if value else False
                        else:
                            defaults[deal_field] = value
        return defaults

    @api.onchange("brokerage_preferences_id")
    def _onchange_brokerage_preferences_id(self):
        """Update fields based on selected Brokerage Preferences."""
        prefs = self.brokerage_preferences_id
        if prefs:
            field_mapping = {
                "tax_ids": "tax_ids",
                "seller_broker_is_paid_by": "seller_broker_is_paid_by",
                "buyer_broker_is_paid_by": "buyer_broker_is_paid_by",
                "who_holds_the_deposit": "who_holds_the_deposit",
                "seller_broker_pays_trust_excess_to": "seller_broker_pays_trust_excess_to",
                "buyer_broker_pays_trust_excess_to": "buyer_broker_pays_trust_excess_to",
                "seller_broker_conveys_to_seller_lawyer": "seller_broker_conveys_to_seller_lawyer",
                "seller_broker_conveys_to_buyer_lawyer": "seller_broker_conveys_to_buyer_lawyer",
                "seller_broker_conveys_to_buyer_broker": "seller_broker_conveys_to_buyer_broker",
                "is_seller_end_or_double_end": "is_seller_end_or_double_end",
                "buyer_broker_conveys_to_seller_lawyer": "buyer_broker_conveys_to_seller_lawyer",
                "buyer_broker_conveys_to_buyer_lawyer": "buyer_broker_conveys_to_buyer_lawyer",
                "buyer_broker_conveys_to_seller_broker": "buyer_broker_conveys_to_seller_broker",
                "brokerage_deposit_policy": "brokerage_deposit_policy",
            }
            for deal_field, brokerage_field in field_mapping.items():
                value = getattr(prefs, brokerage_field, False)
                field = self._fields.get(deal_field)
                if field:
                    if isinstance(field, fields.Many2many):
                        setattr(self, deal_field, value)
                    elif isinstance(field, fields.Many2one):
                        setattr(self, deal_field, value.id if value else False)
                    else:
                        setattr(self, deal_field, value)
