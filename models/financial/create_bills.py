# models/financial/create_bills.py

"""
Module for generating and processing bills related to deals.
Extends the 'deal.records' model to include functionalities for:
- Generating bills for sales agents and brokers.
- Handling split payments and journal entries.
- Transferring funds from Trust Account to Accounts Receivable (AR).
- Processing payments for unpaid bills.
- Generating expense invoices for sales agents.
"""

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class CreateBills(models.Model):
    _inherit = 'deal.records'
    _description = "Deal Records Extension for Bill Generation"

    # =====================
    # Bill Generation Methods
    # =====================

    def _generate_sales_agent_bills(self):
        """
        Generate bills for sales agents associated with the deal.
        Differentiates calculations based on payment type.
        Handles split fees and creates corresponding journal entries.
        """
        for deal in self:
            sales_agents = deal.sales_agents_ids.filtered(lambda sa: sa.payable_amount > 0)
            if not sales_agents:
                _logger.info(f"No sales agents to process for Deal ID: {deal.id}")
                continue  # No sales agents to process

            # Retrieve the Sales Agent Commission Product from DealPreferences
            commission_product = deal.deal_preferences_id.sales_agent_commission_product_id
            if not commission_product:
                _logger.error("Sales Agent Commission Product is not set in Deal Preferences.")
                raise ValidationError(_("Sales Agent Commission Product is not set in Deal Preferences."))

            # Ensure the product has the necessary account properties
            if not commission_product.property_account_income_id:
                _logger.error("Property Income Account for Sales Agent Commission Product is not set.")
                raise ValidationError(_("Property Income Account for Sales Agent Commission Product is not set."))

            # Fetch necessary accounts from Deal Preferences
            tax_account = deal.deal_preferences_id.company_tax_account
            commission_income_account = deal.deal_preferences_id.commission_income_account

            if not tax_account or not commission_income_account:
                raise UserError(_("Please set the Company Tax Account and Commission Income Account in Deal Preferences."))

            for agent in sales_agents:
                if not agent.partner_id:
                    _logger.error(f"Sales Agent record (ID: {agent.id}) must have an associated partner.")
                    raise UserError(_("Sales Agent must have an associated partner."))

                if not agent.payable_amount:
                    _logger.warning(f"Sales Agent {agent.partner_id.name} has a payable amount of 0.")
                    continue  # Skip agents with no payable amount

                # Determine price based on payment_type
                if agent.payment_type in ["person", "broker"] and agent.payable_amount > 0:
                    price = agent.gross_amount
                elif agent.payment_type == "agent" and agent.payable_amount > 0:
                    price = agent.net_amount
                else:
                    price = 0

                if not price:
                    _logger.warning(f"Sales Agent {agent.partner_id.name} has a payable amount of 0 after calculation.")
                    continue  # Skip if price is zero after calculation

                tax = agent.tax
                tax_ids = agent.tax_ids

                if tax_ids:
                    invoice_lines = [
                        (
                            0,
                            0,
                            {
                                "product_id": self.env.ref("property_transaction.tax_collected").id,
                                "name": "Tax Input Credit",
                                "account_id": tax_account.id,
                                "quantity": 1,
                                "price_unit": tax,
                                "tax_ids": [(6, 0, tax_ids.ids)],
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "product_id": self.env.ref("property_transaction.sale_agent_commission").id,
                                "name": "Payable to Sales Agents",
                                "account_id": commission_income_account.id,
                                "quantity": 1,
                                "price_unit": price,
                                "tax_ids": [(6, 0, tax_ids.ids)],
                            },
                        ),
                    ]
                else:
                    invoice_lines = [
                        (
                            0,
                            0,
                            {
                                "product_id": self.env.ref("property_transaction.sale_agent_commission").id,
                                "name": "Payable to Sales Agents",
                                "account_id": commission_income_account.id,
                                "quantity": 1,
                                "price_unit": price,
                                "tax_ids": [],
                            },
                        )
                    ]

                invoice_vals = {
                    "move_type": "in_invoice",
                    "partner_id": agent.partner_id.id,
                    "invoice_date": fields.Date.today(),
                    "invoice_line_ids": invoice_lines,
                    "deal_id": deal.id,
                }

                invoice = self.env["account.move"].create(invoice_vals)
                invoice.action_post()
                _logger.info(f"Generated Sales Agent Bill (ID: {invoice.id}) for Agent: {agent.partner_id.name}")

                # Handle split fees and journal entries if plans are present
                if agent.plans:
                    for plan in agent.plans:
                        if plan.account_product:
                            product_account = plan.account_product.property_account_income_id
                            amount = agent.split_fees
                            journal_entry_vals = [
                                (
                                    0,
                                    0,
                                    {
                                        "account_id": commission_income_account.id,
                                        "name": "Split & Fees",
                                        "debit": amount,
                                        "credit": 0,
                                    },
                                ),
                                (
                                    0,
                                    0,
                                    {
                                        "account_id": product_account.id,
                                        "name": "Split & Fees from the deal",
                                        "debit": 0,
                                        "credit": amount,
                                    },
                                ),
                            ]
                            journal_entry = self.env["account.move"].create(
                                {
                                    "move_type": "entry",
                                    "invoice_date": fields.Date.today(),
                                    "line_ids": journal_entry_vals,
                                    "deal_id": deal.id,
                                    "ref": f"{deal.name} Transfer split and fees from sales agent company split to commission plan Account",
                                }
                            )
                            journal_entry.action_post()
                            _logger.info(f"Created Journal Entry (ID: {journal_entry.id}) for Split & Fees")

    def _generate_broker_bills(self):
        """
        Generate bills for brokers associated with the deal.
        Handles trust account balance validations and split payments if necessary.
        """
        for deal in self:
            brokers = deal.deal_buyer_brokers_ids.filtered(lambda b: b.amount_payable > 0)
            if not brokers:
                _logger.info(f"No brokers to process for Deal ID: {deal.id}")
                continue  # No brokers to process

            # Retrieve the Broker Commission Product from DealPreferences
            broker_commission_product = deal.deal_preferences_id.broker_commission_product_id
            if not broker_commission_product:
                _logger.error("Broker Commission Product is not set in Deal Preferences.")
                raise ValidationError(_("Broker Commission Product is not set in Deal Preferences."))

            # Ensure the product has the necessary account properties
            if not broker_commission_product.property_account_income_id:
                _logger.error("Property Income Account for Broker Commission Product is not set.")
                raise ValidationError(_("Property Income Account for Broker Commission Product is not set."))

            # Fetch necessary accounts from Deal Preferences
            tax_account = deal.deal_preferences_id.company_tax_account
            commission_income_account = deal.deal_preferences_id.commission_income_account
            trust_account = deal.deal_preferences_id.trust_bank_account

            if not tax_account or not commission_income_account or not trust_account:
                raise UserError(_("Please set the Company Tax Account, Commission Income Account, and Trust Bank Account in Deal Preferences."))

            for broker in brokers:
                if not broker.broker_id:
                    _logger.error(f"Broker record (ID: {broker.id}) must have an associated broker.")
                    raise UserError(_("Broker must have an associated broker."))

                if not broker.amount_payable:
                    _logger.warning(f"Broker {broker.broker_id.name} has a payable amount of 0.")
                    continue  # Skip brokers with no payable amount

                price = broker.amount_payable
                trust_balance = abs(trust_account.current_balance)

                # Determine if split payment is required
                split_payment = price > trust_balance and \
                                deal.deal_preferences_id.split_broker_payment and \
                                deal.deal_preferences_id.pay_broker_split_from

                if split_payment:
                    # Partial payment from Trust Account and remainder from another account
                    if broker.tax:
                        invoice_lines = [
                            (
                                0,
                                0,
                                {
                                    "product_id": self.env.ref("property_transaction.tax_collected").id,
                                    "name": "Tax Input Credit",
                                    "account_id": tax_account.id,
                                    "quantity": 1,
                                    "price_unit": broker.tax,
                                    "tax_ids": [(6, 0, broker.tax_ids.ids)],
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "product_id": self.env.ref("property_transaction.broker_commission").id,
                                    "name": "Payable to Broker",
                                    "account_id": trust_account.id,
                                    "quantity": 1,
                                    "price_unit": trust_balance,
                                    "tax_ids": [],
                                },
                            ),
                            (
                                0,
                                0,
                                {
                                    "product_id": self.env.ref("property_transaction.broker_commission").id,
                                    "name": "Payable to Broker",
                                    "account_id": commission_income_account.id,
                                    "quantity": 1,
                                    "price_unit": abs(price - trust_balance),
                                    "tax_ids": [],
                                },
                            ),
                        ]
                    else:
                        invoice_lines = [
                            (
                                0,
                                0,
                                {
                                    "product_id": self.env.ref("property_transaction.broker_commission").id,
                                    "name": "Payable to Broker",
                                    "account_id": trust_account.id,
                                    "quantity": 1,
                                    "price_unit": price,
                                    "tax_ids": [],
                                },
                            ),
                        ]
                elif price <= trust_balance:
                    invoice_lines = [
                        (
                            0,
                            0,
                            {
                                "product_id": self.env.ref("property_transaction.broker_commission").id,
                                "name": "Payable to Broker",
                                "account_id": trust_account.id,
                                "quantity": 1,
                                "price_unit": price,
                                "tax_ids": [],
                            },
                        ),
                    ]
                else:
                    # Price equals trust_balance
                    invoice_lines = [
                        (
                            0,
                            0,
                            {
                                "product_id": self.env.ref("property_transaction.broker_commission").id,
                                "name": "Payable to Broker",
                                "account_id": trust_account.id,
                                "quantity": 1,
                                "price_unit": price,
                                "tax_ids": [],
                            },
                        ),
                    ]

                invoice_vals = {
                    "move_type": "in_invoice",
                    "partner_id": broker.broker_id.id,
                    "invoice_date": fields.Date.today(),
                    "invoice_line_ids": invoice_lines,
                    "deal_id": deal.id,
                }

                invoice = self.env["account.move"].create(invoice_vals)
                invoice.action_post()
                _logger.info(f"Generated Broker Bill (ID: {invoice.id}) for Broker: {broker.broker_id.name}")

    def _transfer_money_from_trust_to_ar(self):
        """
        Transfer money from the Trust Account to the Accounts Receivable (AR) account.
        """
        for deal in self:
            deal_preference = deal.deal_preferences_id
            debit_account = deal_preference.trust_liability_account
            credit_account = deal_preference.commission_income_account

            if not debit_account or not credit_account:
                raise UserError(_("Please set the Trust Liability Account and Commission Income Account in Deal Preferences."))

            trust_balance = abs(deal_preference.trust_bank_account.current_balance)
            if trust_balance <= 0:
                _logger.warning(f"Trust Bank Account balance is insufficient for Deal ID: {deal.id}")
                continue  # No funds to transfer

            # Create journal entry to offset the trust liability
            journal_entry_vals = [
                (
                    0,
                    0,
                    {
                        "account_id": debit_account.id,
                        "name": "Trust Funds",
                        "debit": -trust_balance,  # Negative to debit
                        "credit": 0,
                    },
                ),
                (
                    0,
                    0,
                    {
                        "account_id": credit_account.id,
                        "name": "Commission From Deals",
                        "debit": 0,
                        "credit": trust_balance,  # Positive to credit
                    },
                ),
            ]

            journal_entry = self.env["account.move"].create(
                {
                    "move_type": "entry",
                    "date": fields.Date.today(),
                    "line_ids": journal_entry_vals,
                    "deal_id": deal.id,
                    "ref": f"{deal.name} Transfer money from Trust Account to Operating Account",
                }
            )
            journal_entry.action_post()
            _logger.info(f"Transferred {trust_balance} from Trust to AR for Deal ID {deal.id}")

    def action_pay_bills(self):
        """
        Process payment for all unpaid bills related to the deal and transfer funds from Trust to AR.
        """
        for deal in self:
            # Search for unpaid bills related to the deal
            bills = self.env["account.move"].search([
                ("deal_id", "=", deal.id),
                ("move_type", "=", "in_invoice"),
                ("payment_state", "!=", "paid"),
            ])

            for bill in bills:
                if bill.payment_state != 'in_payment':
                    # Register payment using the payment wizard
                    payment_wizard = self.env["account.payment.register"].with_context(
                        active_model="account.move",
                        active_ids=[bill.id],
                        active_id=bill.id,
                    ).create({"amount": bill.amount_total})

                    payment_wizard.action_create_payments()

                    # Retrieve the created payment
                    payment = self.env["account.payment"].search([
                        ("payment_reference", "=", bill.name),
                        ("state", "=", "posted"),
                    ], limit=1)

                    if payment:
                        bill.write({"payment_reference": payment.name})
                        _logger.info(f"Bill ID {bill.id} paid via Payment ID {payment.id}")

            # Transfer funds from Trust to AR after payments
            self._transfer_money_from_trust_to_ar()

        # Display success notification
        self.env.user.notify_success(
            title=_("Bills Paid"),
            message=_("All the bills are paid successfully!"),
            sticky=False
        )

        # Reload the client view
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def _generate_sales_agent_expense_invoice(self):
        """
        Generate expense invoices for sales agents.
        """
        for deal in self:
            sales_agents = deal.sales_agents_ids.filtered(lambda sa: sa.expense_amount > 0)
            if not sales_agents:
                _logger.info(f"No sales agent expenses to process for Deal ID: {deal.id}")
                continue  # No expenses to process

            # Retrieve the Sales Agent Expense Product from DealPreferences
            expense_product = deal.deal_preferences_id.sales_agent_expense_product_id
            if not expense_product:
                _logger.error("Sales Agent Expense Product is not set in Deal Preferences.")
                raise ValidationError(_("Sales Agent Expense Product is not set in Deal Preferences."))

            # Ensure the product has the necessary account properties
            if not expense_product.property_account_expense_id:
                _logger.error("Property Expense Account for Sales Agent Expense Product is not set.")
                raise ValidationError(_("Property Expense Account for Sales Agent Expense Product is not set."))

            # Fetch necessary accounts from Deal Preferences
            expense_account = deal.deal_preferences_id.company_tax_account  # Assuming expense account
            pay_sales_agents_journal = deal.deal_preferences_id.pay_sales_agents_from

            if not expense_account or not pay_sales_agents_journal:
                raise UserError(_("Please set the Company Tax Account and Pay Sales Agents From Journal in Deal Preferences."))

            for agent in sales_agents:
                if not agent.partner_id:
                    _logger.error(f"Sales Agent record (ID: {agent.id}) must have an associated partner.")
                    raise UserError(_("Sales Agent must have an associated partner."))

                if not agent.expense_amount:
                    _logger.warning(f"Sales Agent {agent.partner_id.name} has an expense amount of 0.")
                    continue  # Skip agents with no expense amount

                # Expense invoice creation logic
                expense_invoice_vals = {
                    "move_type": "in_invoice",
                    "partner_id": agent.partner_id.id,
                    "invoice_date": fields.Date.today(),
                    "deal_id": deal.id,
                    "journal_id": pay_sales_agents_journal.id,
                    "invoice_line_ids": [
                        (
                            0,
                            0,
                            {
                                "product_id": expense_product.id,
                                "account_id": expense_product.property_account_expense_id.id,
                                "name": "Sales Agent Expense",
                                "quantity": 1,
                                "price_unit": agent.expense_amount,
                                "tax_ids": [(6, 0, expense_product.taxes_id.ids)],
                            },
                        )
                    ],
                }

                expense_invoice = self.env["account.move"].create(expense_invoice_vals)
                expense_invoice.action_post()
                _logger.info(f"Generated Sales Agent Expense Invoice (ID: {expense_invoice.id}) for Agent: {agent.partner_id.name}")

    def get_trust_balance(self):
        """
        Calculate the current trust balance for the deal.
        """
        self.ensure_one()
        # Utilize mixin's method
        trust_balance = self.deal_financial_logic_mixin.get_trust_balance(self)
        _logger.info(f"Trust Balance for Deal ID {self.id}: {trust_balance}")
        return trust_balance