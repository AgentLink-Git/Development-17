# models/shared_resources/brokerage_preferences.py

"""
Module for managing Brokerage Preferences.
This module defines the BrokeragePreferences model, which stores global settings and configurations
related to brokerage operations. It ensures that only a single record exists and provides mechanisms
for calculating taxes and managing various brokerage-related accounts and journals.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

# Configure the logger for this module
_logger = logging.getLogger(__name__)


class BrokeragePreferences(models.Model):
    """
    Model for storing Brokerage Preferences.
    This model holds global settings and configurations for brokerage operations,
    including payment sources, deposit handling, tax configurations, and account mappings.
    It ensures that only one instance of BrokeragePreferences exists in the system.
    """
    _name = "brokerage.preferences"
    _description = "Brokerage Preferences"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "name"

    # ================================
    # Selection Options as Class Variables
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

    name = fields.Char(
        string="Name",
        default="Default Brokerage Preferences",
        required=True,
        tracking=True,
        help="Name of the Brokerage Preferences record. Must be unique.",
    )

    # Ensure only one record exists via SQL constraint
    _sql_constraints = [
        (
            "unique_brokerage_preferences",
            "unique(name)",
            "Only one Brokerage Preferences record is allowed.",
        ),
    ]

    @api.model
    def create(self, vals):
        """
        Override the create method to ensure only one record exists.
        
        Args:
            vals (dict): Values to create the record with.
        
        Returns:
            record: The created record.
        
        Raises:
            ValidationError: If attempting to create more than one Brokerage Preferences record.
        """
        if self.search_count([]) >= 1:
            _logger.error("Attempt to create multiple Brokerage Preferences records.")
            raise ValidationError(_("Only one Brokerage Preferences record is allowed."))
        _logger.debug("Creating Brokerage Preferences record with vals: %s", vals)
        return super(BrokeragePreferences, self).create(vals)

    @api.constrains("name")
    def _check_single_record(self):
        """
        Constraint to ensure only one Brokerage Preferences record exists.
        
        Raises:
            ValidationError: If more than one Brokerage Preferences record is found.
        """
        if self.search_count([]) > 1:
            _logger.error("Multiple Brokerage Preferences records detected.")
            raise ValidationError(_("Only one Brokerage Preferences record is allowed."))

    # ================================
    # Brokerage Settings Fields
    # ================================

    # Advance Maximum Percentage
    advance_maximum_percentage = fields.Float(
        string="Advance Maximum Percentage",
        default=70.0,
        help="Maximum percentage available for commission advances.",
        tracking=True,
    )

    # Payment Source Selections
    seller_broker_is_paid_by = fields.Selection(
        selection=PAYMENT_SOURCE_SELECTION,
        string="Seller's Broker is Paid By",
        tracking=True,
        help="Select the payment source for the Seller's Broker.",
    )
    buyer_broker_is_paid_by = fields.Selection(
        selection=PAYMENT_SOURCE_SELECTION,
        string="Buyer's Broker is Paid By",
        tracking=True,
        help="Select the payment source for the Buyer's Broker.",
    )
    who_holds_the_deposit = fields.Selection(
        selection=WHO_HOLDS_DEPOSIT_SELECTION,
        string="Who Holds Deposits",
        tracking=True,
        help="Determine which entity holds the deposits.",
    )
    seller_broker_pays_trust_excess_to = fields.Selection(
        selection=TRUST_EXCESS_SELECTION,
        string="Seller Broker: Pay Trust Excess To",
        tracking=True,
        help="Select the entity to which the Seller Broker pays trust excess.",
    )
    buyer_broker_pays_trust_excess_to = fields.Selection(
        selection=TRUST_EXCESS_SELECTION,
        string="Buyer Broker: Pay Trust Excess To",
        tracking=True,
        help="Select the entity to which the Buyer Broker pays trust excess.",
    )

    # Taxes
    tax_ids = fields.Many2many(
        "account.tax",
        string="Taxes",
        required=True,
        tracking=True,
        help="Select applicable taxes.",
    )

    total_tax = fields.Float(
        string="Total Tax",
        compute="_compute_total_tax",
        store=True,
        tracking=True,
        help="Total tax calculated based on selected taxes.",
    )

    @api.depends("tax_ids")
    def _compute_total_tax(self):
        """
        Compute the total tax based on selected taxes.
        """
        for record in self:
            record.total_tax = sum(tax.amount for tax in record.tax_ids)
            _logger.debug(
                "Computed total_tax for Brokerage Preferences ID %s: %s",
                record.id,
                record.total_tax,
            )

    # Conveyancing Options
    seller_broker_conveys_to_seller_law_firm = fields.Boolean(
        string="Seller's Law Firm",
        help="Whether the Seller's Broker conveys to the Seller's Law Firm.",
    )
    seller_broker_conveys_to_buyer_law_firm = fields.Boolean(
        string="Buyer's Law Firm",
        help="Whether the Seller's Broker conveys to the Buyer's Law Firm.",
    )
    seller_broker_conveys_to_buyer_broker = fields.Boolean(
        string="Buyer's Broker",
        help="Whether the Seller's Broker conveys to the Buyer's Broker.",
    )
    seller_end_or_double_end = fields.Boolean(
        string="Is Double End",
        help="Indicates if the brokerage setup is a double end.",
    )
    buyer_broker_conveys_to_seller_law_firm = fields.Boolean(
        string="Seller's Law Firm",
        help="Whether the Buyer's Broker conveys to the Seller's Law Firm.",
    )
    buyer_broker_conveys_to_buyer_law_firm = fields.Boolean(
        string="Buyer's Law Firm",
        help="Whether the Buyer's Broker conveys to the Buyer's Law Firm.",
    )
    buyer_broker_conveys_to_seller_broker = fields.Boolean(
        string="Seller's Broker",
        help="Whether the Buyer's Broker conveys to the Seller's Broker.",
    )
    brokerage_deposit_policy = fields.Char(
        string="Brokerage Deposit Policy",
        help="Policy description for brokerage deposits.",
    )

    # Address Fields
    show_street_direction_prefix = fields.Boolean(
        string="Show Street Direction Prefix",
        help="Toggle to show/hide street direction prefix in addresses.",
    )
    show_street_direction_suffix = fields.Boolean(
        string="Show Street Direction Suffix",
        help="Toggle to show/hide street direction suffix in addresses.",
    )

    # ================================
    # Bank Journals and Accounts
    # ================================

    receipt_brokers_to = fields.Many2one(
        "account.journal",
        string="Receipt Brokers To",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
        help="Journal used to receive funds from brokers.",
    )
    pay_brokers_from = fields.Many2one(
        "account.journal",
        string="Pay Brokers From",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
        help="Journal used to pay brokers.",
    )
    split_the_broker_payment = fields.Boolean(
        string="Split the Broker Payment",
        tracking=True,
        help="Whether to split broker payments across multiple accounts.",
    )
    pay_broker_split_payment_from = fields.Many2one(
        "account.journal",
        string="Pay Broker's Split Payment From",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
        help="Journal used to pay split broker payments.",
    )
    receipt_law_firms_to = fields.Many2one(
        "account.journal",
        string="Receipt Law Firms To",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
        help="Journal used to receive funds from law firms.",
    )
    pay_law_firms_from = fields.Many2one(
        "account.journal",
        string="Pay Law Firms From",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
        help="Journal used to pay law firms.",
    )
    receipt_sales_agents_to = fields.Many2one(
        "account.journal",
        string="Receipt Sales Agents To",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
        help="Journal used to receive funds from sales agents.",
    )
    pay_sales_agents_from = fields.Many2one(
        "account.journal",
        string="Pay Sales Agents From",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
        help="Journal used to pay sales agents.",
    )
    receipt_buyers_and_sellers_to = fields.Many2one(
        "account.journal",
        string="Receipt Buyers/Sellers To",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
        help="Journal used to receive funds from buyers and sellers.",
    )
    pay_buyers_and_sellers_from = fields.Many2one(
        "account.journal",
        string="Pay Buyers/Sellers From",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
        help="Journal used to pay buyers and sellers.",
    )
    pay_unlicensed_referrals_from = fields.Many2one(
        "account.journal",
        string="Pay Unlicensed Referrals From",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
        help="Journal used to pay unlicensed referrals.",
    )
    brokerage_income_account = fields.Many2one(
        "account.journal",
        string="Brokerage Income Account",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
        help="Journal used for brokerage income.",
    )
    commission_receipt_account = fields.Many2one(
        "account.journal",
        string="Commission Receipt Account",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
        help="Journal used to receive commission payments.",
    )
    trust_bank_account = fields.Many2one(
        "account.journal",
        string="Trust Bank Journal",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
        help="Journal used for trust funds.",
    )

    # ================================
    # Conveyancing Notes
    # ================================

    conveyancing_ap_notes = fields.Text(
        string="Convey A/P Notes",
        help="Accounts Payable notes related to conveyancing.",
    )
    conveyancing_ar_notes = fields.Text(
        string="Convey A/R Notes",
        help="Accounts Receivable notes related to conveyancing.",
    )
    conveyancing_phone = fields.Char(
        string="Conveyancing Department Phone",
        help="Phone number for the conveyancing department.",
    )
    conveyancing_email = fields.Char(
        string="Conveyancing Email",
        help="Email address for the conveyancing department.",
    )

    # ================================
    # Account Fields
    # ================================

    trust_liability_account = fields.Many2one(
        "account.account",
        string="Liability - Trust Funds",
        domain=[("user_type_id.type", "=", "liability")],
        required=True,
        tracking=True,
        help="Account used to track liability for trust funds.",
    )
    commission_income_account = fields.Many2one(
        "account.account",
        string="Commission Income Account",
        domain=[("user_type_id.type", "=", "income")],
        required=True,
        tracking=True,
        help="Account used to record commission income.",
    )
    company_tax_account = fields.Many2one(
        "account.tax",
        string="Tax Account",
        required=True,
        tracking=True,
        help="Tax account used by the company.",
    )

    # ================================
    # Journals
    # ================================

    trust_journal = fields.Many2one(
        "account.journal",
        string="Trust Journal",
        domain=[("type", "=", "sale")],
        required=True,
        tracking=True,
        help="Journal used for trust fund transactions.",
    )
    trust_excess_fund_journal = fields.Many2one(
        "account.journal",
        string="Trust Excess Fund Journal",
        domain=[("type", "=", "sale")],
        required=True,
        help="Journal used for recording trust excess funds transactions.",
        tracking=True,
    )
    commission_journal = fields.Many2one(
        "account.journal",
        string="Commission Receipt Journal",
        domain=[("type", "=", "sale")],
        required=True,
        tracking=True,
        help="Journal used to receive commission payments.",
    )
    agent_commission_journal = fields.Many2one(
        "account.journal",
        string="Commission - Sales Agent",
        domain=[("type", "=", "purchase")],
        required=True,
        tracking=True,
        help="Journal used to pay sales agent commissions.",
    )
    other_broker_commission_journal = fields.Many2one(
        "account.journal",
        string="Commission - Broker",
        domain=[("type", "=", "purchase")],
        required=True,
        tracking=True,
        help="Journal used to pay broker commissions.",
    )
    referral_commission_journal = fields.Many2one(
        "account.journal",
        string="Commission - Referral",
        domain=[("type", "=", "purchase")],
        required=True,
        tracking=True,
        help="Journal used to pay referral commissions.",
    )
    inter_account_transfer = fields.Many2one(
        "account.journal",
        string="Internal Account Transfer",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
        help="Journal used for internal account transfers.",
    )

    # ================================
    # Product-Based Accounting
    # ================================

    trust_deposit_product_id = fields.Many2one(
        "product.product",
        string="Trust Deposits",
        domain=[("type", "=", "service")],
        required=True,
        tracking=True,
        help="Product used for Trust Deposits (Escrow).",
    )
    trust_excess_funds_product_id = fields.Many2one(
        "product.product",
        string="Excess Funds",
        domain=[("type", "=", "service")],
        required=True,
        tracking=True,
        help="Product used for Trust Excess Funds.",
    )
    commission_product_id = fields.Many2one(
        "product.product",
        string="Commission Product",
        domain=[("type", "=", "service")],
        required=True,
        tracking=True,
        help="Product used to receipt commissions.",
    )
    commission_receipt_product_id = fields.Many2one(
        "product.product",
        string="Commission Receipt",
        domain=[("type", "=", "service")],
        required=True,
        tracking=True,
        help="Product used to receipt commissions.",
    )
    tax_collected_product_id = fields.Many2one(
        "product.product",
        string="Tax Collected",
        domain=[("type", "=", "service")],
        required=True,
        tracking=True,
        help="Product used to collect taxes.",
    )
    sales_agent_commission_product_id = fields.Many2one(
        "product.product",
        string="Sales Agent Commission",
        domain=[("type", "=", "service")],
        required=True,
        tracking=True,
        help="Product used to pay Sales Agent commission.",
    )
    sales_agent_expense_product_id = fields.Many2one(
        "product.product",
        string="Sales Agent Expenses",
        domain=[("type", "=", "service")],
        required=True,
        tracking=True,
        help="Product used for Sales Agent expenses.",
    )
    broker_commission_product_id = fields.Many2one(
        "product.product",
        string="Broker Commission Product",
        domain=[("type", "=", "service")],
        required=True,
        tracking=True,
        help="Product used to pay Broker commissions.",
    )

    # ================================
    # Constraints
    # ================================

    @api.constrains(
        "advance_maximum_percentage",
        "receipt_brokers_to",
        "pay_brokers_from",
        "pay_broker_split_payment_from",
        "receipt_law_firms_to",
        "pay_law_firms_from",
        "receipt_sales_agents_to",
        "pay_sales_agents_from",
        "receipt_buyers_and_sellers_to",
        "pay_buyers_and_sellers_from",
        "pay_unlicensed_referrals_from",
        "brokerage_income_account",
        "commission_receipt_account",
        "trust_bank_account",
        "trust_liability_account",
        "commission_income_account",
        "company_tax_account",
        "trust_journal",
        "trust_excess_fund_journal",
        "commission_journal",
        "agent_commission_journal",
        "other_broker_commission_journal",
        "referral_commission_journal",
        "inter_account_transfer",
        "trust_deposit_product_id",
        "trust_excess_funds_product_id",
        "commission_product_id",
        "commission_receipt_product_id",
        "tax_collected_product_id",
        "sales_agent_commission_product_id",
        "sales_agent_expense_product_id",
        "broker_commission_product_id",
    )
    def _validate_brokerage_preferences(self):
        """
        Ensure that all required fields are properly set and valid.
        
        Raises:
            ValidationError: If any required field is missing or contains invalid data.
        """
        for record in self:
            if not (0 <= record.advance_maximum_percentage <= 100):
                _logger.error(
                    f"Invalid advance_maximum_percentage: {record.advance_maximum_percentage} for record ID {record.id}"
                )
                raise ValidationError(
                    _("Advance Maximum Percentage must be between 0 and 100.")
                )
            # Additional validations can be added here as needed
            _logger.debug(f"Brokerage Preferences ID {record.id} passed all validations.")

    # ================================
    # Override Unlink Method
    # ================================

    def unlink(self):
        """
        Override the unlink method to prevent deletion of the Brokerage Preferences record.
        
        Raises:
            ValidationError: Always raises an error to prevent deletion.
        """
        for record in self:
            _logger.warning(
                f"Attempt to delete Brokerage Preferences record ID {record.id}."
            )
            raise ValidationError(_("Cannot delete the Brokerage Preferences record."))
        return super(BrokeragePreferences, self).unlink()