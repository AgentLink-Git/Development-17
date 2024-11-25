# models/financial/commission_receipt.py

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class CommissionReceipt(models.Model):
    _name = "commission.receipt"
    _description = "Commission Receipt"
    _inherit = ["transaction.line", "shared.fields.mixin"]
    _order = "date_received desc"

    # =====================
    # Transaction Details
    # =====================
    transaction_type = fields.Selection(
        selection=[("commission_receipt", "Commission Receipt")],
        default="commission_receipt",
        required=True,
        readonly=True,
        tracking=True,
    )

    # =====================
    # Partner Details
    # =====================
    receipt_commission_partner_id = fields.Many2one(
        "res.partner",
        string="Commission Partner",
        help="Partner associated with the commission receipt.",
        required=True,
        tracking=True,
    )
    # =====================
    # Date Fields
    # =====================
    date_received = fields.Date(
        string="Date Received",
        required=True,
        default=fields.Date.today,
        help="Date when the commission was received.",
        tracking=True,
    )
    date_posted = fields.Date(
        string="Date Posted",
        readonly=True,
        help="Date when the commission receipt was posted.",
    )

    # =====================
    # Payment Relationship
    # =====================
    payment_id = fields.Many2one(
        "account.payment",
        string="Payment",
        readonly=True,
        help="Linked payment record for the commission receipt.",
        tracking=True,
    )

    # =====================
    # Amount
    # =====================
    amount = fields.Monetary(
        string="Amount",
        currency_field="currency_id",
        required=True,
        help="Amount of the commission receipt.",
    )

    # =====================
    # State
    # =====================
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("posted", "Posted"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        readonly=True,
        default="draft",
        help="Status of the commission receipt.",
    )

    # =====================
    # Funds Received Calculation
    # =====================
    funds_received = fields.Monetary(
        string="Funds Received",
        compute="_compute_funds_received",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )

    # =====================
    # Constraints
    # =====================
    @api.constrains("amount", "deal_id", "receipt_commission_partner_id")
    def _check_commission_receipt_constraints(self):
        for record in self:
            if record.amount <= 0:
                raise ValidationError(_("Commission amount must be greater than zero."))
            if not record.deal_id:
                raise ValidationError(_("Commission receipt must be linked to a deal."))
            if not record.receipt_commission_partner_id:
                raise ValidationError(
                    _("Commission receipt must be associated with a partner.")
                )

    # =====================
    # Computation Methods
    # =====================
    @api.depends(
        "transaction_line_ids.deposited",
        "transaction_line_ids.journal_type",
        "transaction_line_ids.held_by",
    )
    def _compute_funds_received(self):
        """
        Compute the total funds received for the commission receipt.
        """
        for record in self:
            funds_received = sum(
                data.deposited
                for data in record.transaction_line_ids
                if data.journal_type == "non_trust" and data.held_by == "our_office"
            )
            record.funds_received = funds_received
            _logger.debug(
                "Computed funds_received for Commission Receipt ID %s: %s",
                record.id,
                funds_received,
            )

    # =====================
    # Action Methods
    # =====================
    def action_receipt_commissions(self):
        """
        Process the commission receipt by creating the invoice and payment,
        updating the deal's dues, and ensuring transactional integrity.
        """
        self.ensure_one()
        deal = self.deal_id
        brokerage_prefs = deal.deal_preferences_id

        # Validate Deal Preferences
        self.validate_deal_preferences(deal)

        # Ensure brokerage preferences for commissions are set
        required_prefs_fields = [
            "commission_journal",
            "commission_receipt_product_id",
            "commission_income_account",
            "tax_ids",
        ]
        missing_prefs_fields = [
            field
            for field in required_prefs_fields
            if not getattr(brokerage_prefs, field)
        ]
        if missing_prefs_fields:
            raise UserError(
                _(
                    "Please set up the following Commission settings in Brokerage Preferences: %s"
                )
                % ", ".join(missing_prefs_fields)
            )

        # Check trust balance to ensure it doesn't go negative
        trust_balance = deal.get_trust_balance()
        if self.amount > trust_balance:
            raise UserError(
                _(
                    "The trust balance cannot go below zero. Commission amount exceeds the available trust balance."
                )
            )

        # Identify the partner for commission receipt
        partner_id = self.receipt_commission_partner_id.id
        if not partner_id:
            raise ValidationError(
                _("No commission partner specified for this transaction.")
            )

        # Create and post invoice
        invoice = self._create_invoice(brokerage_prefs, partner_id, self.amount)
        invoice.action_post()
        self.invoice_id = invoice.id
        _logger.info(
            f"Commission Receipt ID {self.id}: Created and posted Invoice ID {invoice.id}"
        )

        # Register payment
        payment = self._register_payment(brokerage_prefs, invoice, self.amount)
        payment.action_post()
        self.payment_id = payment.id
        _logger.info(
            f"Commission Receipt ID {self.id}: Created and posted Payment ID {payment.id}"
        )

        # Link payment to invoice
        invoice.payment_reference = payment.name
        _logger.debug(
            f"Commission Receipt ID {self.id}: Linked Payment Reference to Invoice."
        )

        # Create a transaction line
        self._create_transaction_line(self.amount, payment, brokerage_prefs, partner_id)

        # Update the state to 'posted'
        self.state = "posted"
        _logger.info(f"Commission Receipt ID {self.id}: State updated to 'Posted'.")

        # Notification
        message = (
            _("Commission payment of %s has been successfully processed.") % self.amount
        )
        self._display_notification(_("Commission Payment Posted!"), message)

    # =====================
    # Helper Methods
    # =====================
    def _create_invoice(self, brokerage_prefs, partner_id, amount):
        """
        Creates an invoice for commission receipts.
        """
        # Use the commission_receipt_product_id from brokerage preferences
        product = brokerage_prefs.commission_receipt_product_id
        if not product:
            raise UserError(
                _(
                    "The 'Commission Receipt' product is not configured in Brokerage Preferences."
                )
            )

        # Prepare invoice lines
        invoice_line = (
            0,
            0,
            {
                "product_id": product.id,
                "name": _("Commission Receipt"),
                "account_id": brokerage_prefs.commission_income_account.id,
                "quantity": 1,
                "price_unit": amount,
                "tax_ids": [(6, 0, brokerage_prefs.tax_ids.ids)],
            },
        )

        # Create the invoice
        invoice_vals = {
            "move_type": "out_invoice",
            "journal_id": brokerage_prefs.commission_journal.id,
            "partner_id": partner_id,
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": [invoice_line],
            "deal_id": self.deal_id.id,
            "payment_reference": "A/R Commission",
        }

        invoice = self.env["account.move"].create(invoice_vals)
        _logger.debug(
            f"Commission Receipt ID {self.id}: Created Invoice ID {invoice.id} with amount {amount}"
        )
        return invoice

    def _register_payment(self, brokerage_prefs, invoice, amount):
        """
        Registers and returns the payment linked to the invoice for commission receipts.
        """
        payment_method = self.env.ref(
            "account.account_payment_method_manual_in", raise_if_not_found=False
        )
        if not payment_method:
            raise UserError(
                _(
                    "Manual In Payment Method is not defined. Please check the configuration."
                )
            )

        # Retrieve the bank account from the commission journal
        commission_journal = brokerage_prefs.commission_journal
        if not commission_journal.bank_account_id:
            raise UserError(
                _(
                    "The Commission Journal does not have an associated bank account. Please set it in Brokerage Preferences."
                )
            )

        payment_vals = {
            "payment_date": self.date_received or fields.Date.today(),
            "amount": amount,
            "payment_type": "inbound",
            "partner_type": "customer",  # 'customer' since it's an 'out_invoice'
            "partner_id": invoice.partner_id.id,
            "journal_id": commission_journal.id,
            "payment_method_id": payment_method.id,
            "communication": invoice.name,
            "deal_id": self.deal_id.id,
        }
        payment = self.env["account.payment"].create(payment_vals)
        _logger.debug(
            f"Commission Receipt ID {self.id}: Created Payment ID {payment.id} with amount {amount}"
        )
        return payment

    def _create_transaction_line(self, amount, payment, brokerage_prefs, partner_id):
        """
        Creates a transaction.line record for the commission receipt.
        """
        transaction_line_vals = {
            "transaction_type": "commission_receipt",
            "deal_id": self.deal_id.id,
            "amount": amount,  # Positive amount for receipt
            "deposited": amount,  # Assuming full amount is deposited
            "date_due": self.date_received,
            "date_received": self.date_received,
            "date_posted": self.date_posted or fields.Date.today(),
            "journal_type": "non_trust",
            "held_by": "our_office",
            "payment_method": payment.payment_method_id.name or "manual",
            "reference_number": payment.name,
            "received_from_id": partner_id,  # Assuming received_from_id is a valid field
            "notes": _("Commission Receipt linked to Payment ID: %s") % payment.id,
            "invoice_id": self.invoice_id.id,
            "payment_id": payment.id,
            "bank_account_id": brokerage_prefs.commission_journal.bank_account_id.id,
            "partner_id": partner_id,
            "related_transaction_form_id": self.id,  # Link back to CommissionReceipt
        }
        transaction_line = self.env["transaction.line"].create(transaction_line_vals)
        _logger.debug(
            f"Commission Receipt ID {self.id}: Created Transaction Line ID {transaction_line.id} with amount {amount}"
        )

    def _display_notification(self, title, message):
        """
        Displays a notification to the user.
        """
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": "success",
                "sticky": False,
            },
        }
