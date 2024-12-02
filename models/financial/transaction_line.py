# models/transaction_line.py

"""
Module for managing Transaction Lines within Deals.
Defines the TransactionLine model, which handles various types of financial transactions
associated with deals, including trust receipts, refunds, commissions, and transfers.
Ensures accurate tracking and processing of financial data related to different partners
such as brokers, law firms, buyers, sellers, and referrals.
"""

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
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        ondelete="cascade",
        help="Deal associated with this commission line.",
        index=True,
    )
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
        help="Type of financial transaction.",
    )

    is_refunded = fields.Boolean(
        string="Is Refunded",
        default=False,
        help="Indicates whether the transaction has been refunded.",
    )

    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        help="Used internally to assign a partner for invoices/payments.",
    )

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
    )

    law_firm_id = fields.Many2one(
        "law.firm",
        string="Law Firm",
        ondelete="set null",
        help="Law firm involved in the transaction.",
    )
    other_broker_id = fields.Many2one(
        "other.broker",
        string="Other Broker",
        ondelete="set null",
        help="Other broker involved in the transaction.",
    )
    sales_agents_and_referrals_id = fields.Many2one(
        "sales.agents.and.referrals",
        string="Sales Agent/Referral",
        ondelete="set null",
        help="Sales agent or referral associated with the transaction.",
    )
    buyers_sellers_id = fields.Many2one(
        "buyers.sellers",
        string="Buyer/Seller",
        ondelete="set null",
        help="Buyer or seller associated with the transaction.",
    )
    buyer_name = fields.Char(
        string="Buyer Name",
        compute="_compute_buyer_seller_names",
        store=True,
        help="Name of the buyer involved in the transaction.",
    )
    seller_name = fields.Char(
        string="Seller Name",
        compute="_compute_buyer_seller_names",
        store=True,
        help="Name of the seller involved in the transaction.",
    )
    amount = fields.Monetary(
        string="Amount",
        required=True,
        currency_field="currency_id",
        help="Total amount of the transaction.",
    )
    deposited = fields.Monetary(
        string="Deposited",
        required=True,
        currency_field="currency_id",
        help="Amount that has been deposited.",
    )
    date_due = fields.Date(
        string="Date Due",
        help="Due date for the transaction.",
    )
    date_received = fields.Date(
        string="Date Received",
        help="Date when the transaction was received.",
    )
    date_posted = fields.Date(
        string="Date Posted",
        help="Date when the transaction was posted.",
    )

    journal_type = fields.Selection(
        [
            ("trust", "Trust"),
            ("non_trust", "Non-Trust"),
        ],
        string="Journal Type",
        required=True,
        help="Type of journal associated with the transaction.",
    )

    held_by = fields.Selection(
        [
            ("our_office", "Our Office"),
            ("other_broker", "Other Broker"),
            ("seller_lawyer", "Seller's Lawyer"),
            ("buyer_lawyer", "Buyer's Lawyer"),
        ],
        string="Held By",
        help="Entity holding the funds for the transaction.",
    )

    payment_method = fields.Selection(
        [
            ("draft", "Bank Draft"),
            ("direct_deposit", "Direct Deposit"),
            ("cheque", "Cheque"),
            ("cash", "Cash"),
        ],
        string="Payment Method",
        default="direct_deposit",
        help="Method of payment used for the transaction.",
    )

    reference_number = fields.Char(
        string="Reference Number",
        help="Reference number for the transaction.",
    )

    received_from_id = fields.Selection(
        [("buyer", "Buyer"), ("seller", "Seller")],
        default="buyer",
        string="Received From",
        help="Entity from whom the transaction was received.",
    )

    notes = fields.Text(
        string="Notes",
        help="Additional notes or comments about the transaction.",
    )

    invoice_id = fields.Many2one(
        "account.move",
        string="Invoice Reference",
        help="Invoice associated with the transaction.",
    )
    trust_receipt_id = fields.Many2one(
        "trust.receipt",
        string="Related Trust Receipt",
        ondelete="cascade",
        help="Trust receipt related to the transaction.",
    )
    trust_refund_id = fields.Many2one(
        "trust.refund",
        string="Related Trust Refund",
        ondelete="cascade",
        help="Trust refund related to the transaction.",
    )
    trust_excess_funds_id = fields.Many2one(
        "trust.excess.funds",
        string="Related Excess Fund",
        ondelete="cascade",
        help="Excess funds related to the transaction.",
    )
    commission_receipt_id = fields.Many2one(
        "commission.receipt",
        string="Related Commission Receipt",
        ondelete="cascade",
        help="Commission receipt related to the transaction.",
    )
    bank_account_id = fields.Many2one(
        "account.journal",
        string="Bank Account",
        required=True,
        domain=[('type', '=', 'bank')],
        help="Bank account associated with this transaction.",
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Journal",
        required=True,
        help="Journal associated with the transaction.",
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
    )
    account_payment_ids = fields.Many2many(
        'account.payment',
        'transaction_line_account_payment_rel',
        'transaction_line_id',
        'account_payment_id',
        string="Payment Entries",
        help="Payment entries associated with this transaction.",
    )
    account_move_ids = fields.One2many(
        "account.move",
        "transaction_line_id",
        string="Journal Entries",
        help="Journal entries related to this transaction line.",
    )

    # =====================
    # Compute Methods
    # =====================

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

            end_type = record.buyers_sellers_id.end_id.type
            partner_name = record.buyers_sellers_id.partner_id.name or ""

            if end_type in ["buyer", "tenant"]:
                record.buyer_name = partner_name
            else:
                record.buyer_name = ""

            if end_type in ["seller", "landlord"]:
                record.seller_name = partner_name
            else:
                record.seller_name = ""

    # =====================
    # Onchange Methods
    # =====================

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
            _logger.warning("Brokerage preferences not found.")
            self.bank_account_id = False
            return

        journals = self.get_payment_journals()
        if journals:
            self.bank_account_id = journals[0].id
        else:
            self.bank_account_id = False

    # =====================
    # Helper Methods
    # =====================

    def get_payment_journals(self):
        """
        Retrieve payment journals based on transaction direction and partner type.
        """
        self.ensure_one()
        brokerage_prefs = self.env['brokerage.preferences'].search([], limit=1)
        if not brokerage_prefs:
            return []

        journals = []
        prefs = brokerage_prefs

        if self.transaction_direction == 'payment':
            if self.partner_type == 'other_broker':
                if prefs.pay_brokers_from:
                    journals.append(prefs.pay_brokers_from)
                if prefs.split_the_broker_payment and prefs.pay_broker_split_payment_from:
                    journals.append(prefs.pay_broker_split_payment_from)
            elif self.partner_type == 'law_firm' and prefs.pay_law_firms_from:
                journals.append(prefs.pay_law_firms_from)
            elif self.partner_type == 'sales_agent' and prefs.pay_sales_agents_from:
                journals.append(prefs.pay_sales_agents_from)
            elif self.partner_type in ['buyer', 'seller'] and prefs.pay_buyers_and_sellers_from:
                journals.append(prefs.pay_buyers_and_sellers_from)
            elif self.partner_type == 'unlicensed_referral' and prefs.pay_unlicensed_referrals_from:
                journals.append(prefs.pay_unlicensed_referrals_from)
        elif self.transaction_direction == 'receipt':
            if self.partner_type == 'other_broker' and prefs.receipt_brokers_to:
                journals.append(prefs.receipt_brokers_to)
            elif self.partner_type == 'law_firm' and prefs.receipt_law_firms_to:
                journals.append(prefs.receipt_law_firms_to)
            elif self.partner_type == 'sales_agent' and prefs.receipt_sales_agents_to:
                journals.append(prefs.receipt_sales_agents_to)
            elif self.partner_type in ['buyer', 'seller'] and prefs.receipt_buyers_and_sellers_to:
                journals.append(prefs.receipt_buyers_and_sellers_to)

        return journals

    def get_journal_balance(self, journal):
        """
        Calculate the current balance of the given journal's account.
        """
        account = journal.default_account_id
        if not account:
            _logger.warning("No default account set for journal '%s'.", journal.name)
            return 0.0

        balance_data = self.env['account.move.line'].read_group(
            [('account_id', '=', account.id), ('move_id.state', '=', 'posted')],
            ['debit', 'credit'],
            ['account_id']
        )
        if balance_data:
            debit = balance_data[0].get('debit', 0.0)
            credit = balance_data[0].get('credit', 0.0)
            balance = credit - debit
            _logger.debug(
                "Calculated balance for account '%s' in journal '%s': %s",
                account.name,
                journal.name,
                balance,
            )
            return balance
        _logger.debug("No move lines found for account '%s' in journal '%s'.", account.name, journal.name)
        return 0.0

    def process_split_payment(self, total_amount, journals):
        """
        Process split payment by creating multiple payment entries if needed.

        :param total_amount: The total amount to be paid.
        :param journals: List of journals to process the payment from.
        :return: List of created payments.
        :raises UserError: If insufficient funds are available in the journals.
        """
        created_payments = []
        remaining_amount = total_amount

        for journal in journals:
            balance = self.get_journal_balance(journal)
            if balance <= 0:
                _logger.info("No available balance in journal '%s'. Skipping.", journal.name)
                continue

            pay_amount = min(balance, remaining_amount)
            payment_method = self.env.ref('account.account_payment_method_manual_out')
            sequence = self.env["ir.sequence"].next_by_code('account.payment')

            payment_vals = {
                'deal_id': self.deal_id.id,
                'partner_id': self.partner_id.id,
                'payment_method_id': payment_method.id,
                'payment_type': 'outbound' if self.transaction_direction == 'payment' else 'inbound',
                'amount': pay_amount,
                'journal_id': journal.id,
                'payment_date': self.date_posted if self.transaction_direction == 'payment' else self.date_received,
                'communication': self.reference_number,
                'transaction_type': self.transaction_type,
                'transaction_line_ids': [(4, self.id)],
            }
            account_payment = self.env['account.payment'].create(payment_vals)
            created_payments.append(account_payment)
            self.account_payment_ids = [(4, account_payment.id)]

            _logger.debug(
                "Created payment '%s' for amount %s from journal '%s'.",
                account_payment.name,
                pay_amount,
                journal.name,
            )

            remaining_amount -= pay_amount
            if remaining_amount <= 0:
                break

        if remaining_amount > 0:
            error_msg = _("Not enough funds in the designated journals to complete the payment.")
            _logger.error(error_msg)
            raise UserError(error_msg)

        return created_payments
    # =====================
    # Name Get Method
    # =====================

    def name_get(self):
        """
        Custom display name for transaction lines.
        Combines deal number and transaction type for better identification.
        """
        result = []
        transaction_type_map = dict(self._fields['transaction_type'].selection)
        for record in self:
            deal_number = record.deal_number or "No Deal Number"
            trans_type = transaction_type_map.get(record.transaction_type, 'Unknown')
            name = f"{deal_number} - {trans_type}"
            result.append((record.id, name))
            return result