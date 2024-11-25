from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

class TransactionLine(models.Model):
    _name = "transaction.line"
    _description = "Transaction Line"
    _inherit = ["shared.fields.mixin"]
    _order = "date_received desc"

    # =====================
    # Fields
    # =====================

    # Transaction Type
    transaction_type = fields.Selection(
        [
            ("trust_receipt", "Trust Receipt"),
            ("trust_refund", "Trust Refund"),
            ("trust_excess_payment", "Trust Excess Payment"),
            ("commission_payment", "Commission Payment"),
            ("commission_receipt", "Commission Receipt"),
            ("transfer", "Transfer"),
        ],
        string="Transaction Type",
        required=True,
        tracking=True,
    )

    # Refund Status
    is_refunded = fields.Boolean(string="Is Refunded", default=False)

    # Partner Computations
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        related="buyers_sellers_id.partner_id",
        store=True,
        readonly=False,  # Set to False if manual override is needed
    )

    # Partner Type and Transaction Direction
    partner_type = fields.Selection(
        [
            ('other_broker', "Other Broker"),
            ('law_firm', "Law Firm"),
            ('sales_agent', "Sales Agent"),
            ('buyer', "Buyer"),
            ('seller', "Seller"),
            ('unlicensed_referral', "Unlicensed Referral"),
        ],
        string="Partner Type",
        help="Type of the partner involved in the transaction.",
        tracking=True,
    )

    # Additional Relationships
    law_firm_id = fields.Many2one("law.firm", string="Law Firm", ondelete="set null")
    other_broker_id = fields.Many2one("other.broker", string="Other Broker", ondelete="set null")
    sales_agents_and_referrals_id = fields.Many2one("sales.agents.and.referrals", string="Sales Agent/Referral", ondelete="set null")
    buyers_sellers_id = fields.Many2one("buyers.sellers", string="Buyer/Seller", ondelete="set null")

    # Computed Buyer/Seller Names
    buyer_name = fields.Char(
        string="Buyer Name",
        compute="_compute_buyer_seller_names",
        store=True,
    )
    seller_name = fields.Char(
        string="Seller Name",
        compute="_compute_buyer_seller_names",
        store=True,
    )

    @api.depends("buyers_sellers_id.partner_id.name", "buyers_sellers_id.end_id.type")
    def _compute_buyer_seller_names(self):
        """
        Compute the buyer and seller names based on the related buyers_sellers_id.
        """
        for record in self:
            if not record.buyers_sellers_id:
                record.buyer_name = ""
                record.seller_name = ""
                continue

            if record.buyers_sellers_id.end_id.type in ["buyer", "tenant"]:
                record.buyer_name = record.buyers_sellers_id.partner_id.name
            else:
                record.buyer_name = ""

            if record.buyers_sellers_id.end_id.type in ["seller", "landlord"]:
                record.seller_name = record.buyers_sellers_id.partner_id.name
            else:
                record.seller_name = ""

    # Financial Fields
    amount = fields.Monetary(
        string="Amount",
        required=True,
        tracking=True,
        currency_field="currency_id",
    )
    deposited = fields.Monetary(
        string="Deposited",
        required=True,
        tracking=True,
        currency_field="currency_id",
    )
    date_due = fields.Date(string="Date Due", tracking=True)
    date_received = fields.Date(string="Date Received", tracking=True)
    date_posted = fields.Date(string="Date Posted", tracking=True)

    # Journal Type
    journal_type = fields.Selection(
        [
            ("trust", "Trust"),
            ("non_trust", "Non-Trust"),
        ],
        string="Journal Type",
        required=True,
        tracking=True,
    )

    # Held By
    held_by = fields.Selection(
        [
            ("our_office", "Our Office"),
            ("other_broker", "Other Broker"),
            ("seller_lawyer", "Seller's Lawyer"),
            ("buyer_lawyer", "Buyer's Lawyer"),
        ],
        string="Held By",
        tracking=True,
    )

    # Payment Method
    payment_method = fields.Selection(
        [
            ("draft", "Bank Draft"),
            ("direct_deposit", "Direct Deposit"),
            ("cheque", "Cheque"),
            ("cash", "Cash"),
        ],
        string="Payment Method",
        default="direct_deposit",
        tracking=True,
    )

    # Reference Number
    reference_number = fields.Char(string="Reference Number", tracking=True)

    # Received From
    received_from_id = fields.Selection(
        [("buyer", "Buyer"), ("seller", "Seller")],
        default="buyer",
        string="Received From",
        tracking=True,
    )

    # Notes
    notes = fields.Text(string="Notes", tracking=True)

    # Relationships
    invoice_id = fields.Many2one(
        "account.move",
        string="Invoice Reference",
    )
    payment_id = fields.Many2one(
        "account.payment",
        string="Payment Reference",
    )
    trust_receipt_id = fields.Many2one(
        "trust.receipt",
        string="Related Trust Receipt",
        ondelete="cascade",
    )
    trust_refund_id = fields.Many2one(
        "trust.refund",
        string="Related Trust Refund",
        ondelete="cascade",
    )
    trust_excess_funds_id = fields.Many2one(
        "trust.excess.funds",
        string="Related Excess Fund",
        ondelete="cascade",
    )
    commission_receipt_id = fields.Many2one(
        "commission.receipt",
        string="Related Commission Receipt",
        ondelete="cascade",
    )

    # Bank Account and Journal
    bank_account_id = fields.Many2one(
        "account.journal",
        string="Bank Account",
        required=True,
        domain=[('type', '=', 'bank')],
        help="Bank account associated with this transaction.",
        tracking=True,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        tracking=True,
    )
    transaction_direction = fields.Selection(
        [
            ('receipt', "Receipt"),
            ('payment', "Payment"),
        ],
        string="Transaction Direction",
        required=True,
        default='receipt',
        help="Direction of the transaction: Receipt or Payment.",
        tracking=True,
    )

    # Payment Entries
    payment_entry_ids = fields.Many2many(
        'payment.entry',
        'transaction_line_payment_entry_rel',
        'transaction_line_id',
        'payment_entry_id',
        string="Payment Entries",
        help="Payment entries associated with this transaction.",
    )

    # Onchange Methods
    @api.onchange('journal_id', 'transaction_direction', 'partner_type')
    def _onchange_journal_transaction_partner_type(self):
        """
        Dynamically suggest bank account based on journal and partner type.
        """
        if not self.journal_id:
            self.bank_account_id = False
            return

        brokerage_prefs = self.env['brokerage.preferences'].search([], limit=1)
        if not brokerage_prefs:
            self.bank_account_id = False
            return

        journals = self.get_payment_journals()
        self.bank_account_id = journals[0].id if journals else False

    # Helper Methods
    def get_payment_journals(self):
        """
        Retrieve payment journals based on direction and partner type.
        """
        self.ensure_one()
        brokerage_prefs = self.env['brokerage.preferences'].search([], limit=1)
        if not brokerage_prefs:
            return []

        journals = []
        if self.transaction_direction == 'payment':
            if self.partner_type == 'other_broker':
                if brokerage_prefs.pay_brokers_from:
                    journals.append(brokerage_prefs.pay_brokers_from)
                if brokerage_prefs.split_the_broker_payment and brokerage_prefs.pay_broker_split_payment_from:
                    journals.append(brokerage_prefs.pay_broker_split_payment_from)
            elif self.partner_type == 'law_firm' and brokerage_prefs.pay_law_firms_from:
                journals.append(brokerage_prefs.pay_law_firms_from)
            elif self.partner_type == 'sales_agent' and brokerage_prefs.pay_sales_agents_from:
                journals.append(brokerage_prefs.pay_sales_agents_from)
            elif self.partner_type in ['buyer', 'seller'] and brokerage_prefs.pay_buyers_and_sellers_from:
                journals.append(brokerage_prefs.pay_buyers_and_sellers_from)
            elif self.partner_type == 'unlicensed_referral' and brokerage_prefs.pay_unlicensed_referrals_from:
                journals.append(brokerage_prefs.pay_unlicensed_referrals_from)
        elif self.transaction_direction == 'receipt':
            if self.partner_type == 'other_broker' and brokerage_prefs.receipt_brokers_to:
                journals.append(brokerage_prefs.receipt_brokers_to)
            elif self.partner_type == 'law_firm' and brokerage_prefs.receipt_law_firms_to:
                journals.append(brokerage_prefs.receipt_law_firms_to)
            elif self.partner_type == 'sales_agent' and brokerage_prefs.receipt_sales_agents_to:
                journals.append(brokerage_prefs.receipt_sales_agents_to)
            elif self.partner_type in ['buyer', 'seller'] and brokerage_prefs.receipt_buyers_and_sellers_to:
                journals.append(brokerage_prefs.receipt_buyers_and_sellers_to)
        return [journal for journal in journals if journal]

    def get_journal_balance(self, journal):
        """
        Calculate the current balance of the given journal's account.
        """
        account = journal.default_account_id
        if not account:
            return 0.0

        balance_data = self.env['account.move.line'].read_group(
            [('account_id', '=', account.id), ('move_id.state', '=', 'posted')],
            ['debit', 'credit'],
            ['account_id']
        )
        return balance_data[0]['credit'] - balance_data[0]['debit'] if balance_data else 0.0

    def process_split_payment(self, total_amount, journals):
        """
        Process split payment by creating multiple payment entries if needed.
        """
        created_payments = []
        remaining_amount = total_amount

        for journal in journals:
            balance = self.get_journal_balance(journal)
            if balance <= 0:
                continue

            pay_amount = min(balance, remaining_amount)
            sequence_code = "payment.cheque" if 'cheque' in journal.name.lower() else "payment.eft"
            sequence = self.env["ir.sequence"].next_by_code(sequence_code) or "/"

            payment_entry = self.env['payment.entry'].create({
                'deal_id': self.deal_id.id,
                'partner_id': self.partner_id.id,
                'payment_method': 'cheque' if 'cheque' in journal.name.lower() else 'eft',
                'sequence_number': sequence,
                'payment_date': self.date_posted if self.transaction_direction == 'payment' else self.date_received,
                'type_of_payment': 'payment',
                'state': 'draft',
                'bank_journal_id': journal.id,
                'amount': pay_amount,
                'transaction_type': self.transaction_type,
                'transaction_line_ids': [(4, self.id)],
            })
            created_payments.append(payment_entry)
            self.payment_entry_ids = [(4, payment_entry.id)]

            remaining_amount -= pay_amount
            if remaining_amount <= 0:
                break

        if remaining_amount > 0:
            raise UserError(_("Not enough funds in the designated journals to complete the payment."))

        return created_payments

    # Name Get Method
    def name_get(self):
        """
        Custom display name for transaction lines.
        """
        result = []
        for record in self:
            deal_number = record.deal_number if record.deal_number else "No Deal Number"
            trans_type = dict(self._fields['transaction_type'].selection).get(record.transaction_type, 'Unknown')
            name = f"{deal_number} - {trans_type}"
            result.append((record.id, name))
        return result