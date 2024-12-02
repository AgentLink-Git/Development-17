from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

class TrustReceipt(models.Model):
    _name = "trust.receipt"
    _description = "Trust Receipt Form"
    _inherit = ["shared.fields.mixin", "notification.mixin"]
    _rec_name = "deal_number"
    _order = "date_received desc"

    # =====================
    # Financial Fields
    # =====================
    transaction_type = fields.Selection(
        selection=[("trust_receipt", "Trust Receipt")],
        default="trust_receipt",
        required=True,
    )
    amount = fields.Monetary(
        string="Amount",
        currency_field="currency_id",
        required=True,
    )
    deposited = fields.Monetary(
        string="Deposited Amount",
        currency_field="currency_id",
    )

    # =====================
    # Date Fields
    # =====================
    date_received = fields.Date(
        string="Date Received",
        default=fields.Date.today,
        required=True,
    )
    date_due = fields.Date(
        string="Date Due",
    )
    date_posted = fields.Date(
        string="Date Posted",
        readonly=True,
    )

    # =====================
    # Additional Fields
    # =====================
    received_from_id = fields.Selection(
        selection=[("buyer", "Buyer"), ("seller", "Seller")],
        string="Received From",
        required=True,
    )
    held_by = fields.Selection(
        [
            ("our_office", "Our Office"),
            ("other_broker", "Other Broker"),
            ("seller_lawyer", "Seller's Lawyer"),
            ("buyer_lawyer", "Buyer's Lawyer"),
        ],
        string="Held By",
        required=True,
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
    )
    reference_number = fields.Char(
        string="Reference Number",
    )
    notes = fields.Text(
        string="Notes",
    )

    # =====================
    # Status Fields
    # =====================
    is_function_completed = fields.Boolean(
        string="Function Completed",
        default=False,
    )

    # =====================
    # References to Financial Records
    # =====================
    invoice_id = fields.Many2one(
        "account.move",
        string="Invoice Reference",
        readonly=True,
    )
    payment_id = fields.Many2one(
        "account.payment",
        string="Payment Reference",
        readonly=True,
    )

    # =====================
    # Computed Fields
    # =====================
    trust_balance = fields.Monetary(
        string="Trust Balance",
        compute="_compute_trust_balance",
        store=True,
        currency_field="currency_id",
    )

    # =====================
    # Relationships
    # =====================
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        ondelete="cascade",
    )
    transaction_line_ids = fields.One2many(
        "transaction.line",
        "trust_receipt_id",
        string="Transaction Lines",
        readonly=True,
    )

    # =====================
    # Hidden Fields
    # =====================
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        help="Used internally to assign a partner for invoices/payments.",
    )

    # =====================
    # Constraints and Overrides
    # =====================

    @api.constrains("held_by")
    def _check_held_by(self):
        for record in self:
            if not record.held_by:
                raise UserError(_("Please specify who holds the trust funds."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("held_by"):
                raise UserError(_("Please specify who holds the trust funds."))
        records = super(TrustReceipt, self).create(vals_list)
        return records

    def write(self, vals):
        if "held_by" in vals and not vals.get("held_by"):
            raise UserError(_("Please specify who holds the trust funds."))
        return super(TrustReceipt, self).write(vals)

    # =====================
    # Computed Methods
    # =====================

    @api.depends("transaction_line_ids.amount", "transaction_line_ids.transaction_type")
    def _compute_trust_balance(self):
        for record in self:
            record.trust_balance = sum(
                record.transaction_line_ids.filtered(
                    lambda t: t.transaction_type == "trust_receipt"
                ).mapped("amount")
            )

    # =====================
    # Action Methods
    # =====================

    def action_trust_receipt_deposit(self):
        self.ensure_one()
        brokerage_prefs = self.env["brokerage.preferences"].search([], limit=1)

        # Validate Deal Preferences
        self.deal_id.validate_deal_preferences()

        required_prefs_fields = [
            "trust_journal",
            "trust_deposit_product_id",
            "trust_liability_account",
            "trust_bank_account",
            "tax_ids",
        ]
        missing_prefs_fields = [
            field for field in required_prefs_fields if not getattr(brokerage_prefs, field)
        ]
        if missing_prefs_fields:
            raise UserError(
                _(
                    "Please set up the following Trust settings in Brokerage Preferences: %s"
                )
                % ", ".join(missing_prefs_fields)
            )

        deal = self.deal_id
        if not deal:
            raise ValidationError(_("Please save the Deal record before proceeding."))

        # Get the partner based on received_from_id
        partner = self._get_partner_from_received_from()
        if not partner:
            raise ValidationError(_("No matching buyer/seller found for this transaction."))

        # Update the deal's buyer_deposit or seller_deposit
        if self.received_from_id == "buyer":
            deal.buyer_deposit += self.amount
            _logger.info(
                f"Added {self.amount} to Deal ID {deal.id}'s buyer_deposit."
            )
        elif self.received_from_id == "seller":
            deal.seller_deposit += self.amount
            _logger.info(
                f"Added {self.amount} to Deal ID {deal.id}'s seller_deposit."
            )
        else:
            raise ValidationError(_("Invalid 'Received From' selection."))

        # Create and post invoice
        invoice = self._create_invoice(brokerage_prefs, partner, self.amount)
        invoice.action_post()
        self.invoice_id = invoice.id

        # Register payment
        payment = self._register_payment(brokerage_prefs, invoice, self.amount)
        payment.action_post()
        self.payment_id = payment.id
        invoice.payment_reference = payment.name

        # Create transaction line
        self._create_transaction_line(self.amount, payment, brokerage_prefs, partner)

        self.is_function_completed = True

        message = _("Payment of %s has been successfully posted.") % self.amount
        return self._display_notification(_("Payment Created and Posted!"), message)

    # =====================
    # Helper Methods
    # =====================

    def _get_partner_from_received_from(self):
        if self.received_from_id == "buyer":
            buyers = self.deal_id.buyers_sellers_ids.filtered(
                lambda bs: bs.end_id.type == "buyer"
            )
            return buyers[0].partner_id if buyers else False
        elif self.received_from_id == "seller":
            sellers = self.deal_id.buyers_sellers_ids.filtered(
                lambda bs: bs.end_id.type == "seller"
            )
            return sellers[0].partner_id if sellers else False
        return False

    def _create_invoice(self, brokerage_prefs, partner, amount):
        product = brokerage_prefs.trust_deposit_product_id
        if not product:
            raise UserError(
                _("The 'Trust Deposits' product is not configured in Brokerage Preferences.")
            )

        invoice_line = {
            "product_id": product.id,
            "name": _("Trust Deposit"),
            "account_id": brokerage_prefs.trust_liability_account.id,
            "quantity": 1,
            "tax_ids": [(6, 0, brokerage_prefs.tax_ids.ids)],
            "price_unit": amount,
        }
        invoice_vals = {
            "move_type": "out_invoice",
            "partner_id": partner.id,
            "invoice_date": self.date_received or fields.Date.today(),
            "invoice_line_ids": [(0, 0, invoice_line)],
            "deal_id": self.deal_id.id,
            "journal_id": brokerage_prefs.trust_journal.id,
        }
        return self.env["account.move"].create(invoice_vals)

    def _register_payment(self, brokerage_prefs, invoice, amount):
        payment_method = self.env.ref(
            "account.account_payment_method_manual_in", raise_if_not_found=False
        )
        if not payment_method:
            raise UserError(
                _("Manual In Payment Method is not defined. Please check the configuration.")
            )

        payment_vals = {
            "payment_date": self.date_received or fields.Date.today(),
            "amount": amount,
            "payment_type": "inbound",
            "partner_type": "customer",
            "partner_id": invoice.partner_id.id,
            "journal_id": brokerage_prefs.trust_bank_account.id,
            "payment_method_id": payment_method.id,
            "communication": invoice.name,
            "deal_id": self.deal_id.id,
        }
        return self.env["account.payment"].create(payment_vals)

    def _create_transaction_line(self, amount, payment, brokerage_prefs, partner):
        transaction_line_vals = {
            "transaction_type": "trust_receipt",
            "deal_id": self.deal_id.id,
            "amount": amount,
            "deposited": amount,
            "date_due": self.date_due,
            "date_received": self.date_received,
            "date_posted": fields.Date.today(),
            "journal_type": "trust",
            "held_by": self.held_by,
            "payment_method": self.payment_method,
            "reference_number": self.reference_number,
            "received_from_id": self.received_from_id,
            "notes": self.notes,
            "invoice_id": self.invoice_id.id,
            "payment_id": payment.id,
            "bank_account_id": brokerage_prefs.trust_bank_account.id,
            "partner_id": partner.id,
            "trust_receipt_id": self.id,
        }
        self.env["transaction.line"].create(transaction_line_vals)