# models/financials/bank_balances.py

"""
Module for extending Deal Records with financial displays.
Defines additional computed fields to display bank balances, required funds,
payment accounts, and counts of related invoices and bills. Provides actions
to view related invoices and bills directly from the deal.
"""

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class DealRecords(models.Model):
    _inherit = 'deal.records'
    _description = "Extended Deal Records with Financial Displays"

    # =====================
    # Balances & Displays
    # =====================
    bank_balances_display = fields.Html(
        string="Bank Balances",
        compute="_compute_bank_balances_display",
        readonly=True,
        help="Displays the current bank balances associated with the deal.",
    )
    required_funds_display = fields.Html(
        string="Required Funds",
        compute="_compute_required_funds_display",
        readonly=True,
        help="Displays the funds required for the deal based on financial computations.",
    )
    payment_accounts_display = fields.Html(
        string="Payment Accounts",
        compute="_compute_payment_accounts_display",
        readonly=True,
        help="Displays the payment accounts configured for the deal based on deal preferences.",
    )

    # =====================
    # Invoice and Bill Counts
    # =====================
    deal_invoice_count = fields.Integer(
        string="Invoice Count",
        compute="_compute_deal_invoice_and_bill_count",
        readonly=True,
        help="Number of related invoices for the deal.",
    )
    deal_bill_count = fields.Integer(
        string="Bill Count",
        compute="_compute_deal_invoice_and_bill_count",
        readonly=True,
        help="Number of related bills for the deal.",
    )

    # =====================
    # Compute Methods
    # =====================
    @api.depends('invoice_ids', 'bill_ids')
    def _compute_deal_invoice_and_bill_count(self):
        """
        Compute the number of related invoices and bills for each deal.
        """
        for rec in self:
            invoices = rec.invoice_ids.filtered(lambda inv: inv.move_type in ['out_invoice', 'out_refund'])
            bills = rec.bill_ids.filtered(lambda bill: bill.move_type == 'in_invoice')
            rec.deal_invoice_count = len(invoices)
            rec.deal_bill_count = len(bills)
            _logger.debug(
                "Deal ID %s has %s invoices and %s bills.",
                rec.id,
                rec.deal_invoice_count,
                rec.deal_bill_count,
            )

    @api.depends('transaction_line_ids.amount', 'transaction_line_ids.journal_id')
    def _compute_bank_balances_display(self):
        """
        Compute and display bank balances related to the deal.
        Generates an HTML unordered list of journal names and their corresponding total amounts.
        """
        for rec in self:
            journal_totals = {}
            bank_transactions = rec.transaction_line_ids.filtered(lambda t: t.journal_id.type == 'bank')

            for transaction in bank_transactions:
                journal_name = transaction.journal_id.name
                journal_totals[journal_name] = journal_totals.get(journal_name, 0.0) + transaction.amount

            if journal_totals:
                balance_lines = "".join(
                    f"<li>{journal}: {rec.currency_id.symbol or rec.currency_id.name} {amount:,.2f}</li>"
                    for journal, amount in journal_totals.items()
                )
                rec.bank_balances_display = f"<ul>{balance_lines}</ul>"
            else:
                rec.bank_balances_display = "<p>No bank balances available.</p>"

            _logger.debug(
                "Computed bank balances for Deal ID %s: %s",
                rec.id,
                rec.bank_balances_display,
            )

    @api.depends('deal_preferences_id')
    def _compute_payment_accounts_display(self):
        """
        Compute and display payment accounts for the deal based on deal preferences.
        Generates an HTML unordered list of payment account categories and their corresponding account names.
        """
        for record in self:
            deal_preference = record.deal_preferences_id
            if not deal_preference:
                record.payment_accounts_display = "<p>No deal preferences set.</p>"
                _logger.warning(
                    "Deal Preferences not set for Deal ID %s. Payment accounts display set to default.",
                    record.id,
                )
                continue

            payment_accounts = {
                "Sales Agents": deal_preference.pay_sales_agents_from.name or "Not Set",
                "Referrals": deal_preference.pay_unlicensed_referrals_from.name or "Not Set",
                "Brokers": deal_preference.pay_brokers_from.name or "Not Set",
                "Broker Split Payment": deal_preference.pay_broker_split_payment_from.name or "Not Set",
                "Law Firms": deal_preference.pay_law_firms_from.name or "Not Set",
                "Buyers/Sellers": deal_preference.pay_buyers_and_sellers_from.name or "Not Set",
                "Company Profit": deal_preference.pay_company_profit_to.name or "Not Set",
            }

            funds_html = "<ul>"
            for key, value in payment_accounts.items():
                funds_html += f"<li><strong>{key}:</strong> {value}</li>"
            funds_html += "</ul>"
            record.payment_accounts_display = funds_html

            _logger.debug(
                "Computed payment accounts for Deal ID %s: %s",
                record.id,
                record.payment_accounts_display,
            )

    @api.depends('transaction_line_ids', 'currency_id')
    def _compute_required_funds_display(self):
        """
        Compute and display required funds for the deal.
        Generates an HTML unordered list of required funds with account names and formatted amounts.
        """
        for record in self:
            required_funds, total_amount = record.calculate_payment_requirements()
            if required_funds:
                funds_html = "<ul>"
                for fund in required_funds:
                    amount_formatted = f"{record.currency_id.symbol or record.currency_id.name} {fund['amount']:,.2f}"
                    funds_html += f"<li>{fund['account_name']}: {amount_formatted}</li>"
                funds_html += "</ul>"
                record.required_funds_display = funds_html
            else:
                record.required_funds_display = "<p>No required funds.</p>"

            _logger.debug(
                "Computed required funds for Deal ID %s: %s",
                record.id,
                record.required_funds_display,
            )

    def calculate_payment_requirements(self):
        """
        Calculate the required funds for the deal.
        Returns a tuple: (required_funds_list, total_amount)
        """
        required_funds = []
        total_amount = 0.0

        # Example logic: sum up amounts from certain transaction lines
        # Adjust the filtering criteria as per actual business logic
        for transaction in self.transaction_line_ids:
            if transaction.transaction_type == 'payment' and transaction.amount > 0:
                required_funds.append({
                    'account_name': transaction.journal_id.name,
                    'amount': transaction.amount,
                })
                total_amount += transaction.amount

        _logger.debug(
            "Calculated payment requirements for Deal ID %s: %s required funds, Total Amount: %s",
            self.id,
            required_funds,
            total_amount,
        )

        return required_funds, total_amount

    # =====================
    # Action Methods
    # =====================
    def action_view_deal_invoices(self):
        """
        Action to view related invoices.
        Opens a window displaying all invoices associated with the deal.
        """
        self.ensure_one()
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        action['domain'] = [('id', 'in', self.invoice_ids.ids)]
        action['context'] = {'default_deal_id': self.id}
        _logger.debug(
            "Action to view invoices triggered for Deal ID %s.",
            self.id,
        )
        return action

    def action_view_deal_bills(self):
        """
        Action to view related bills.
        Opens a window displaying all bills associated with the deal.
        """
        self.ensure_one()
        action = self.env.ref('account.action_move_in_invoice_type').read()[0]
        action['domain'] = [('id', 'in', self.bill_ids.ids)]
        action['context'] = {'default_deal_id': self.id}
        _logger.debug(
            "Action to view bills triggered for Deal ID %s.",
            self.id,
        )
        return action