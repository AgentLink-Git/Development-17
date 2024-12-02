# models/deals/close_deal.py

"""
Module for handling the closure of Deal Records, including financial operations,
commission computations, invoice creation, and partner financial updates.
"""

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class DealRecords(models.Model):
    """
    Inherited model from 'deal.records' to handle the closure of deals,
    including financial transactions, commission calculations, and document management.
    """
    _inherit = 'deal.records'

    # =====================
    # Fields
    # =====================
    is_closed = fields.Boolean(
        string='Is Closed',
        default=False,
    )
    receipt_commission_partner_id = fields.Many2one(
        'res.partner',
        string='Receipt Commission Partner',
    )
    receipt_commission_journal_id = fields.Many2one(
        'account.journal',
        string='Receipt Commission Journal',
    )
    receipt_is_commission_payment = fields.Boolean(
        string='Receipt is Commission Payment',
    )

    deposit_received_from_buyer = fields.Monetary(
        string='Deposit Received from Buyer',
        currency_field='currency_id',
    )
    deposit_received_from_seller = fields.Monetary(
        string='Deposit Received from Seller',
        currency_field='currency_id',
    )
    commission_receivable = fields.Monetary(
        string='Commission Receivable',
        currency_field='currency_id',
    )
    tax_receivable = fields.Monetary(
        string='Tax Receivable',
        currency_field='currency_id',
    )

    # =====================
    # Methods
    # =====================

    def action_close_deal(self):
        """
        Main method to close a deal, handling all necessary financial operations.
        """
        self.ensure_one()
        _logger.info("Closing deal: %s", self.name)

        # Validate Deal Preferences before proceeding
        self.validate_deal_preferences()

        # Set deal as closed
        self.is_closed = True
        _logger.info("Deal '%s' marked as closed.", self.name)

        # Compute Commissions Before Payments
        self._compute_sales_agent_commissions()

        # Calculate payment requirements
        required_funds, available_funds = self.calculate_payment_requirements()
        _logger.info("Payment requirements calculated. Required: %s, Available: %s", required_funds, available_funds)

        # Handle inter-company transfers
        brokerage_preference = self.env['brokerage.preferences'].search([], limit=1)
        self.handle_inter_company_transfer(
            available_funds=available_funds,
            required_funds=required_funds,
            brokerage_preference=brokerage_preference
        )
        _logger.info("Handled inter-company transfers.")

        # Create pre-payment
        pre_payment = self._create_pre_payment()
        _logger.info("Pre-payment created with ID: %s.", pre_payment.id)

        # Create invoice to close the deal
        invoice = self._create_invoice_close_deal()
        _logger.info("Invoice created to close the deal with ID: %s.", invoice.id)

        # Update res.partner fields based on the deal closure
        self._update_partner_financials_on_close()

        # Launch the payment wizard
        action = self.env.ref('your_module.action_payment_wizard_form').read()[0]
        action['context'] = {'default_deal_id': self.id}
        return action

    def _compute_sales_agent_commissions(self):
        """
        Compute commissions for sales agents using methods from the updated commission plan models.
        """
        for agent_line in self.sales_agents_and_referrals_ids.filtered(lambda a: a.payment_type == "sales_agent"):
            agent_line._apply_commission_plans()
            _logger.info("Commission for %s calculated.", agent_line.partner_id.name)

    def _create_pre_payment(self):
        """
        Create a pre-payment record for the deal.
        """
        deal_preference = self.deal_preferences_id
        trust_bank_journal = deal_preference.trust_bank_account

        if not trust_bank_journal:
            raise UserError(_("Trust Bank Account is not set in Deal Preferences."))

        # Determine the amount to pre-pay based on deposits
        price = self.deposit_received_from_buyer or self.deposit_received_from_seller or 0.0

        if price <= 0:
            raise UserError(_("No deposit held to create a pre-payment."))

        # Determine partner and journal based on deal end type
        partner_bank_id, partner_id, bank_journal_id = self.get_account_and_partner_based_on_receipt_end_type()

        if not partner_id:
            raise UserError(_("A payable Partner could not be found."))

        if not bank_journal_id:
            # Use the trust bank journal if not set
            bank_journal = trust_bank_journal
            if not bank_journal:
                raise UserError(_("No trust bank journal available."))
            bank_journal_id = bank_journal.id

        # Get the receivable account from the partner
        partner = self.env["res.partner"].browse(partner_id)
        receivable_account = partner.property_account_receivable_id

        if not receivable_account:
            raise UserError(_("A receivable account could not be found for the Partner."))

        # Determine if the journal is for commission based on trust bank journal
        is_commission_payment = bank_journal_id != trust_bank_journal.id
        journal_type = "trust" if bank_journal_id == trust_bank_journal.id else "non_trust"

        # Create the payment record
        payment_method = self.env.ref('account.account_payment_method_manual_in', raise_if_not_found=False)
        if not payment_method:
            raise UserError(_("Manual In Payment Method is not defined. Please check the configuration."))

        payment_vals = {
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": partner_id,
            "amount": price,
            "currency_id": self.currency_id.id,
            "payment_date": fields.Date.today(),
            "payment_method_id": payment_method.id,
            "ref": _("Receipt Commission"),
            "deal_id": self.id,
            "journal_id": bank_journal_id,
            "is_commission_payment": is_commission_payment,
        }

        payment = self.env["account.payment"].create(payment_vals)
        payment.action_post()

        # Create transaction line for the payment
        self.env["transaction.line"].create({
            "transaction_type": "commission_receipt",
            "held_by": "our_office",
            "date_due": fields.Date.today(),
            "date_received": fields.Date.today(),
            "date_posted": fields.Date.today(),
            "amount": price,
            "deposited": price,
            "payment_method": "cheque" if payment.payment_method_id.code == "manual_in" else "eft",
            "deal_id": self.id,
            "bank_account_id": bank_journal_id,
            "journal_type": journal_type,
            "transaction_direction": 'receipt',
            "partner_type": 'customer',
        })

        # Notify the user
        self.env.user.notify_info(
            message=_("Payment for %s has been successfully posted.") % price,
            title=_("Payment Created and Posted!"),
            sticky=False,
        )

        # Update deal with payment information
        self.write({
            "receipt_commission_partner_id": partner_id,
            "receipt_commission_journal_id": bank_journal_id,
            "receipt_is_commission_payment": is_commission_payment,
        })

        return payment

    def _create_invoice_close_deal(self):
        """
        Create an invoice to close the deal.
        """
        deal_preference = self.deal_preferences_id
        if not deal_preference:
            raise UserError(
                _("Deal Preferences must be set before creating an invoice.")
            )

        # Fetch required products from deal preferences
        commission_product = deal_preference.commission_receipt_product_id
        tax_product = deal_preference.tax_collected_product_id

        if not commission_product:
            raise UserError(_("The 'Commission Receipt' product is not set in Deal Preferences."))
        if not tax_product:
            raise UserError(_("The 'Tax Collected' product is not set in Deal Preferences."))

        # Ensure required accounts are set in preferences
        tax_account = deal_preference.company_tax_account
        commission_account = deal_preference.commission_income_account

        if not tax_account or not commission_account:
            raise UserError(_("Please set the necessary accounts in Deal Preferences."))

        # Prepare invoice lines
        invoice_lines = self._prepare_invoice_lines(
            commission_product, tax_product, commission_account, tax_account
        )

        # Create the invoice
        invoice_vals = {
            "move_type": "out_invoice",
            "journal_id": deal_preference.commission_journal.id,
            "partner_id": self.receipt_commission_partner_id.id,
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": invoice_lines,
            "deal_id": self.id,
            "payment_reference": "A/R Commission",
        }

        invoice = self.env["account.move"].create(invoice_vals)
        invoice.action_post()

        if invoice:
            self._reconcile_pre_payment_with_invoice(invoice)
            _logger.info("Invoice %s posted and reconciled.", invoice.name)

        return invoice

    def _prepare_invoice_lines(self, commission_product, tax_product, commission_account, tax_account):
        """
        Prepare invoice lines for commission and tax.
        """
        commission_line = (0, 0, {
            "product_id": commission_product.id,
            "account_id": commission_account.id,
            "name": commission_product.name or _("Commission Income"),
            "quantity": 1,
            "price_unit": self.commission_receivable,
            "tax_ids": [(6, 0, commission_product.taxes_id.ids)],
        })

        tax_line = (0, 0, {
            "product_id": tax_product.id,
            "account_id": tax_account.id,
            "name": tax_product.name or _("Tax Collected"),
            "quantity": 1,
            "price_unit": self.tax_receivable,
            "tax_ids": [(6, 0, tax_product.taxes_id.ids)],
        })

        return [commission_line, tax_line]

    def _reconcile_pre_payment_with_invoice(self, invoice):
        """
        Reconcile pre-payments with the created invoice.
        """
        pre_payments = self.env["account.payment"].search([
            ("partner_id", "=", invoice.partner_id.id),
            ("deal_id", "=", self.id),
            ("state", "=", "posted"),
            ("is_commission_payment", "=", True),
        ])

        invoice_lines = invoice.line_ids.filtered(lambda line: not line.reconciled and line.debit > 0)

        for pre_payment in pre_payments:
            payment_lines = pre_payment.move_id.line_ids.filtered(lambda l: not l.reconciled and l.credit > 0)

            for payment_line in payment_lines:
                for invoice_line in invoice_lines:
                    if payment_line.account_id == invoice_line.account_id:
                        (payment_line + invoice_line).reconcile()
                        _logger.info(
                            "Reconciled payment line ID: %s with invoice line ID: %s.",
                            payment_line.id, invoice_line.id
                        )
                        break

    def get_account_and_partner_based_on_receipt_end_type(self):
        """
        Find and return partner_bank_id, partner_id, and bank_journal_id based on the deal's receipt commission partner.
        """
        partner_id = self.receipt_commission_partner_id.id
        bank_journal_id = self.receipt_commission_journal_id.id
        partner_bank_id = False

        if partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            partner_banks = partner.bank_ids
            if partner_banks:
                partner_bank_id = partner_banks[0].id

            if not bank_journal_id:
                # Use default bank journal if not set
                bank_journal = self.env['account.journal'].search([('type', '=', 'bank')], limit=1)
                bank_journal_id = bank_journal.id if bank_journal else False

        return partner_bank_id, partner_id, bank_journal_id

    def validate_deal_preferences(self):
        """
        Validate that all necessary deal preferences are set.
        """
        deal_preference = self.deal_preferences_id
        if not deal_preference:
            raise UserError(_("Deal Preferences must be set before closing the deal."))

        required_fields = [
            'trust_bank_account',
            'commission_journal',
            'commission_receipt_product_id',
            'tax_collected_product_id',
            'company_tax_account',
            'commission_income_account'
        ]
        missing_fields = [field for field in required_fields if not getattr(deal_preference, field)]
        if missing_fields:
            field_names = [
                self.env['ir.model.fields'].search(
                    [('model', '=', 'deal.preferences'), ('name', '=', field)], limit=1
                ).field_description or field for field in missing_fields
            ]
            raise UserError(_("Please set the following fields in Deal Preferences: %s") % ", ".join(field_names))

    def calculate_payment_requirements(self):
        """
        Calculate required funds and available funds for the deal.
        """
        # Implement logic to calculate required funds and available funds
        required_funds = self.commission_receivable + self.tax_receivable
        available_funds = self.deposit_received_from_buyer + self.deposit_received_from_seller
        return required_funds, available_funds

    def handle_inter_company_transfer(self, available_funds, required_funds, brokerage_preference):
        """
        Handle inter-company transfers if needed.
        """
        if available_funds < required_funds:
            shortfall = required_funds - available_funds
            _logger.warning("Available funds are less than required funds by %s. Handling inter-company transfer.", shortfall)
            # Implement inter-company transfer logic here
            # For example, create a journal entry to record the transfer
            # Placeholder for actual transfer logic
            raise UserError(_("Insufficient funds to close the deal. Please handle the shortfall manually."))

    def _update_partner_financials_on_close(self):
        """
        Update res.partner fields based on the deal closure:
        - gross_amount_total
        - split_fees_total
        - net_amount_total
        - ends_total
        """
        for agent_line in self.sales_agents_and_referrals_ids.filtered(lambda a: a.payment_type == "sales_agent"):
            partner = agent_line.partner_id
            if not partner:
                continue

            # Update res.partner fields
            partner.gross_amount_total += agent_line.gross_amount
            partner.split_fees_total += agent_line.split_fees
            partner.net_amount_total += agent_line.net_amount
            partner.ends_total += 1  # Assuming each deal counts as one end

            # Handle fee anniversary
            if partner.fee_anniversary:
                today = fields.Date.today()
                try:
                    anniversary_date = partner.fee_anniversary.replace(year=today.year)
                except ValueError:
                    # Handle February 29th for non-leap years
                    anniversary_date = partner.fee_anniversary.replace(year=today.year, day=28)
                if today == anniversary_date:
                    _logger.info("Fee anniversary reached for Partner ID: %s", partner.id)
                    # Implement any special actions needed on fee anniversary
                    # For example, reset cumulative totals, apply bonuses, etc.
                    self._handle_fee_anniversary(partner)

    def _handle_fee_anniversary(self, partner):
        """
        Handle actions required when a sales agent reaches their fee anniversary.
        """
        # Example: Reset cumulative totals or apply bonuses
        _logger.info("Handling fee anniversary for Partner ID: %s", partner.id)
        # Reset cumulative totals
        partner.gross_amount_total = 0.0
        partner.split_fees_total = 0.0
        partner.net_amount_total = 0.0
        partner.ends_total = 0

    # =====================
    # Constraints
    # =====================

    @api.constrains('sales_agents_and_referrals_ids')
    def _check_sales_agent_lines(self):
        """
        Ensure that there is at least one Sales Agent or Referral associated with the deal.
        """
        for deal in self:
            if not deal.sales_agents_and_referrals_ids:
                raise ValidationError(_("Please add at least one Sales Agent or Referral to the deal."))

    # =====================
    # Override Unlink Method
    # =====================

    def unlink(self):
        """
        Override the unlink method to prevent deletion of closed deals and handle related records.
        """
        for deal in self:
            if deal.is_closed:
                raise UserError(_("Closed deals cannot be deleted."))
        return super(DealRecords, self).unlink()