# models/financials/bank_balances.py

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class DealRecords(models.Model):
    _inherit = "deal.records"

    # =====================
    # Balances & Displays
    # =====================
    bank_balances_display = fields.Html(
        string="Bank Balances",
        compute="_compute_bank_balances_display",
        store=False,
        readonly=True,
    )
    required_funds_display = fields.Html(
        string="Required Funds",
        compute="_compute_required_funds_display",
        store=False,
        readonly=True,
    )
    # =====================
    # Payment Accounts
    # =====================
    payment_accounts_display = fields.Html(
        string="Payment Accounts",
        compute="_compute_payment_accounts_display",
        store=False,
        readonly=True,
    )
    # =====================
    # Invoice and Bill Counts
    # =====================
    deal_invoice_count = fields.Integer(
        string="Invoice Count",
        compute="_compute_deal_invoice_and_bill_count",
        store=False,
        help="Number of related invoices.",
    )
    deal_bill_count = fields.Integer(
        string="Bill Count",
        compute="_compute_deal_invoice_and_bill_count",
        store=False,
        help="Number of related bills.",
    )

    # =====================
    # Compute Methods
    # =====================

    @api.depends("invoice_ids", "bill_ids")
    def _compute_deal_invoice_and_bill_count(self):
        """
        Compute the number of related invoices and bills.
        """
        for rec in self:
            invoices = rec.invoice_ids.filtered(
                lambda inv: inv.move_type in ["out_invoice", "out_refund"]
            )
            bills = rec.bill_ids.filtered(lambda bill: bill.move_type == "in_invoice")
            rec.deal_invoice_count = len(invoices)
            rec.deal_bill_count = len(bills)

    @api.depends("transaction_line_ids.amount", "transaction_line_ids.journal_id")
    def _compute_bank_balances_display(self):
        """
        Compute and display bank balances related to the deal.
        """
        for rec in self:
            journal_totals = {}
            for transaction in rec.transaction_line_ids.filtered(
                lambda t: t.journal_id.type == "bank"
            ):
                journal_name = transaction.journal_id.name
                journal_totals[journal_name] = (
                    journal_totals.get(journal_name, 0.0) + transaction.amount
                )

            if journal_totals:
                balance_lines = "".join(
                    f"<li>{journal}: {rec.currency_id.symbol or rec.currency_id.name} {amount:,.2f}</li>"
                    for journal, amount in journal_totals.items()
                )
                rec.bank_balances_display = f"<ul>{balance_lines}</ul>"
            else:
                rec.bank_balances_display = "<p>No bank balances available.</p>"

    @api.depends("deal_preferences_id")
    def _compute_payment_accounts_display(self):
        """
        Compute and display payment accounts for the deal based on deal preferences.
        """
        for record in self:
            deal_preference = record.deal_preferences_id
            if not deal_preference:
                record.payment_accounts_display = "<p>No deal preferences set.</p>"
                continue

            payment_accounts = {
                "Sales Agents": deal_preference.pay_sales_agents_from.name or "Not Set",
                "Referrals": deal_preference.pay_unlicensed_referrals_from.name
                or "Not Set",
                "Brokers": deal_preference.pay_brokers_from.name or "Not Set",
                "Broker Split Payment": deal_preference.pay_broker_split_payment_from.name
                or "Not Set",
                "Law Firms": deal_preference.pay_law_firms_from.name or "Not Set",
                "Buyers/Sellers": deal_preference.pay_buyers_and_sellers_from.name
                or "Not Set",
                "Company Profit": deal_preference.pay_company_profit_to.name
                or "Not Set",
            }
            funds_html = "<ul>"
            for key, value in payment_accounts.items():
                funds_html += f"<li><strong>{key}:</strong> {value}</li>"
            funds_html += "</ul>"
            record.payment_accounts_display = funds_html

    @api.depends("transaction_line_ids", "currency_id")
    def _compute_required_funds_display(self):
        """
        Compute and display required funds for the deal.
        """
        for record in self:
            required_funds, _ = record.calculate_payment_requirements()
            if required_funds:
                funds_html = "<ul>"
                for fund in required_funds:
                    amount_formatted = f"{record.currency_id.symbol or record.currency_id.name} {fund['amount']:,.2f}"
                    funds_html += f"<li>{fund['account_name']}: {amount_formatted}</li>"
                funds_html += "</ul>"
                record.required_funds_display = funds_html
            else:
                record.required_funds_display = "<p>No required funds.</p>"

    def calculate_payment_requirements(self):
        """
        Calculate the required funds for the deal.
        Returns a tuple: (required_funds_list, total_amount)
        """
        required_funds = []
        total_amount = 0.0

        # Example logic: sum up amounts from certain transaction lines
        for transaction in self.transaction_line_ids:
            if transaction.transaction_type == "payment" and transaction.amount > 0:
                required_funds.append(
                    {
                        "account_name": transaction.journal_id.name,
                        "amount": transaction.amount,
                    }
                )
                total_amount += transaction.amount

        return required_funds, total_amount

    # =====================
    # Action Methods
    # =====================

    def action_view_deal_invoices(self):
        """
        Action to view related invoices.
        """
        self.ensure_one()
        action = self.env.ref("account.action_move_out_invoice_type").read()[0]
        action["domain"] = [("id", "in", self.invoice_ids.ids)]
        action["context"] = {"default_deal_id": self.id}
        return action

    def action_view_deal_bills(self):
        """
        Action to view related bills.
        """
        self.ensure_one()
        action = self.env.ref("account.action_move_in_invoice_type").read()[0]
        action["domain"] = [("id", "in", self.bill_ids.ids)]
        action["context"] = {"default_deal_id": self.id}
        return action
