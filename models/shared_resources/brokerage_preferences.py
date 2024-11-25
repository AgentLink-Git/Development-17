# models/shared_resources/brokerage_preferences.py

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class BrokeragePreferences(models.Model):
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

    COMMISSION_PAYMENT_SELECTION = [
        ("seller_broker", "Seller's Broker"),
        ("seller_law_firm", "Seller's Law Firm"),
        ("buyer_law_firm", "Buyer's Law Firm"),
        ("buyer_broker", "Buyer's Broker"),
    ]

    # ================================
    # Fields Definition
    # ================================
    name = fields.Char(
        string="Name",
        default="Default Brokerage Preferences",
        required=True,
        tracking=True,
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
        """Override the create method to ensure only one record exists."""
        if self.search_count([]) >= 1:
            raise ValidationError(
                _("Only one Brokerage Preferences record is allowed.")
            )
        return super(BrokeragePreferences, self).create(vals)

    @api.constrains("name")
    def _check_single_record(self):
        """Constraint to ensure only one record exists."""
        if self.search_count([]) > 1:
            raise ValidationError(
                _("Only one Brokerage Preferences record is allowed.")
            )

    # Advance Maximum Percentage
    advance_maximum_percentage = fields.Float(
        string="Advance Maximum Percentage",
        default=70.0,
        help="Maximum percentage available for commission advances.",
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
        string="Seller Broker: Pay Trust Excess To",
        tracking=True,
    )
    buyer_broker_pays_trust_excess_to = fields.Selection(
        selection=TRUST_EXCESS_SELECTION,
        string="Buyer Broker: Pay Trust Excess To",
        tracking=True,
    )

    # Taxes
    tax_ids = fields.Many2many(
        "account.tax",
        string="Taxes",
        required=True,
        tracking=True,
    )

    total_tax = fields.Float(
        string="Total Tax",
        compute="_compute_total_tax",
        store=True,
        tracking=True,
    )

    @api.depends("tax_ids")
    def _compute_total_tax(self):
        """Compute the total tax based on selected taxes."""
        for record in self:
            record.total_tax = sum(tax.amount for tax in record.tax_ids)

    # Conveyancing Options
    seller_broker_conveys_to_seller_law_firm = fields.Boolean(
        string="Seller's Law Firm",
    )
    seller_broker_conveys_to_buyer_law_firm = fields.Boolean(
        string="Buyer's Law Firm",
    )
    seller_broker_conveys_to_buyer_broker = fields.Boolean(
        string="Buyer's Broker",
    )
    seller_end_or_double_end = fields.Boolean(
        string="Is Double End",
    )
    buyer_broker_conveys_to_seller_law_firm = fields.Boolean(
        string="Seller's Law Firm",
    )
    buyer_broker_conveys_to_buyer_law_firm = fields.Boolean(
        string="Buyer's Law Firm",
    )
    buyer_broker_conveys_to_seller_broker = fields.Boolean(
        string="Seller's Broker",
    )
    brokerage_deposit_policy = fields.Char(
        string="Brokerage Deposit Policy",
    )

    # Address Fields
    show_street_direction_prefix = fields.Boolean(
        string="Show Street Direction Prefix",
    )
    show_street_direction_suffix = fields.Boolean(
        string="Show Street Direction Suffix",
    )

    # Bank Journals and Accounts
    receipt_brokers_to = fields.Many2one(
        "account.journal",
        string="Receipt Brokers To",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
    )
    pay_brokers_from = fields.Many2one(
        "account.journal",
        string="Pay Brokers From",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
    )
    split_the_broker_payment = fields.Boolean(
        string="Split the Broker Payment",
        tracking=True,
    )
    pay_broker_split_payment_from = fields.Many2one(
        "account.journal",
        string="Pay Broker's Split Payment From",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
    )
    receipt_law_firms_to = fields.Many2one(
        "account.journal",
        string="Receipt Law Firms To",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
    )
    pay_law_firms_from = fields.Many2one(
        "account.journal",
        string="Pay Law Firms From",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
    )
    receipt_sales_agents_to = fields.Many2one(
        "account.journal",
        string="Receipt Sales Agents To",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
    )
    pay_sales_agents_from = fields.Many2one(
        "account.journal",
        string="Pay Sales Agents From",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
    )
    receipt_buyers_and_sellers_to = fields.Many2one(
        "account.journal",
        string="Receipt Buyers/Sellers To",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
    )
    pay_buyers_and_sellers_from = fields.Many2one(
        "account.journal",
        string="Pay Buyers/Sellers From",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
    )
    pay_unlicensed_referrals_from = fields.Many2one(
        "account.journal",
        string="Pay Unlicensed Referrals From",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
    )
    brokerage_income_account = fields.Many2one(
        "account.journal",
        string="Brokerage Income Account",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
    )
    commission_receipt_account = fields.Many2one(
        "account.journal",
        string="Commission Receipt Account",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
    )
    trust_bank_account = fields.Many2one(
        "account.journal",
        string="Trust Bank Journal",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
    )

    # Conveyancing Notes
    conveyancing_ap_notes = fields.Text(string="Convey A/P Notes")
    conveyancing_ar_notes = fields.Text(string="Convey A/R Notes")
    conveyancing_department_phone = fields.Char(string="Conveyancing Department Phone")
    conveyancing_email = fields.Char(string="Conveyancing Email")

    # Account Fields
    trust_liability_account = fields.Many2one(
        "account.account",
        string="Liability - Trust Funds",
        domain=[("user_type_id.type", "=", "liability")],
        required=True,
        tracking=True,
    )
    commission_income_account = fields.Many2one(
        "account.account",
        string="Commission Income Account",
        domain=[("user_type_id.type", "=", "income")],
        required=True,
        tracking=True,
    )
    company_tax_account = fields.Many2one(
        "account.tax",
        string="Tax Account",
        required=True,
        tracking=True,
    )

    # Journals
    trust_journal = fields.Many2one(
        "account.journal",
        string="Trust Journal",
        domain=[("type", "=", "sale")],
        required=True,
        tracking=True,
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
    )
    agent_commission_journal = fields.Many2one(
        "account.journal",
        string="Commission - Sales Agent",
        domain=[("type", "=", "purchase")],
        required=True,
        tracking=True,
    )
    other_broker_commission_journal = fields.Many2one(
        "account.journal",
        string="Commission - Broker",
        domain=[("type", "=", "purchase")],
        required=True,
        tracking=True,
    )
    referral_commission_journal = fields.Many2one(
        "account.journal",
        string="Commission - Referral",
        domain=[("type", "=", "purchase")],
        required=True,
        tracking=True,
    )
    inter_account_transfer = fields.Many2one(
        "account.journal",
        string="Internal Account Transfer",
        domain=[("type", "=", "bank")],
        required=True,
        tracking=True,
    )

    # Product-Based Accounting
    trust_deposit_product_id = fields.Many2one(
        "product.product",
        string="Trust Deposits",
        domain=[("type", "=", "service")],
        required=True,
        help="Product used for Trust Deposits (Escrow).",
        tracking=True,
    )
    trust_excess_funds_product_id = fields.Many2one(
        "product.product",
        string="Excess Funds",
        domain=[("type", "=", "service")],
        required=True,
        help="Product used for Trust Excess Funds.",
        tracking=True,
    )
    commission_product_id = fields.Many2one(
        "product.product",
        string="Commission Product",
        domain=[("type", "=", "service")],
        required=True,
        help="Product used to receipt commissions.",
        tracking=True,
    )
    commission_receipt_product_id = fields.Many2one(
        "product.product",
        string="Commission Receipt",
        domain=[("type", "=", "service")],
        required=True,
        help="Product used to receipt commissions.",
        tracking=True,
    )
    tax_collected_product_id = fields.Many2one(
        "product.product",
        string="Tax Collected",
        domain=[("type", "=", "service")],
        required=True,
        help="Product used to collect taxes.",
        tracking=True,
    )
    sales_agent_commission_product_id = fields.Many2one(
        "product.product",
        string="Sales Agent Commission",
        domain=[("type", "=", "service")],
        required=True,
        help="Product used to pay Sales Agent commission.",
        tracking=True,
    )
    sales_agent_expense_product_id = fields.Many2one(
        "product.product",
        string="Sales Agent Expenses",
        domain=[("type", "=", "service")],
        required=True,
        help="Product used for Sales Agent expenses.",
        tracking=True,
    )
    broker_commission_product_id = fields.Many2one(
        "product.product",
        string="Broker Commission Product",
        domain=[("type", "=", "service")],
        required=True,
        help="Product used to pay Broker commissions.",
        tracking=True,
    )
