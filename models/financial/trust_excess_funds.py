# models/financial/trust_excess_funds.py

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class TrustExcessFunds(models.Model):
    _name = "trust.excess.funds"
    _description = "Trust Excess Funds"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "shared.fields.mixin",
    ]
    _rec_name = "deal_number"
    _order = "date_received desc"

    # =====================
    # Financial Fields
    # =====================
    transaction_type = fields.Selection(
        selection=[("trust_excess_payment", "Excess Payment")],
        default="trust_excess_payment",
        required=True,
        tracking=True,
    )
    amount = fields.Monetary(
        string="Amount",
        currency_field="currency_id",
        compute="_compute_excess_held",
        store=True,
        readonly=True,
        help="Amount of excess funds to be paid.",
    )
    date_received = fields.Date(
        string="Date Received",
        default=fields.Date.today,
        required=True,
        tracking=True,
    )
    date_posted = fields.Date(
        string="Date Posted",
        tracking=True,
        readonly=True,
    )
    excess_held = fields.Monetary(
        string="Excess Held",
        compute="_compute_excess_held",
        store=True,
        currency_field="currency_id",
        help="Computed excess funds held.",
    )

    # =====================
    # Additional Fields
    # =====================
    held_by = fields.Selection(
        [
            ("our_office", "Our Office"),
            ("other_broker", "Other Broker"),
            ("seller_lawyer", "Seller's Lawyer"),
            ("buyer_lawyer", "Buyer's Lawyer"),
        ],
        string="Held By",
        required=True,
        tracking=True,
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
        tracking=True,
    )
    reference_number = fields.Char(
        string="Reference Number",
        tracking=True,
    )
    notes = fields.Text(
        string="Notes",
        tracking=True,
    )

    # =====================
    # Status Fields
    # =====================
    is_paid = fields.Boolean(
        string="Is Paid",
        default=False,
        tracking=True,
    )

    # =====================
    # References to Financial Records
    # =====================
    invoice_id = fields.Many2one(
        "account.move",
        string="Invoice Reference",
        tracking=True,
        readonly=True,
    )
    payment_id = fields.Many2one(
        "account.payment",
        string="Payment Reference",
        tracking=True,
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
    transaction_line_ids = fields.One2many(
        "transaction.line",
        "trust_excess_funds_id",
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
    # Deal Preferences
    # =====================
    deal_preferences_id = fields.Many2one(
        "deal.preferences",
        string="Deal Preferences",
        related="deal_id.deal_preferences_id",
        readonly=True,
    )

    # =====================
    # Constraints and Overrides
    # =====================

    @api.constrains("held_by")
    def _check_held_by(self):
        for record in self:
            if not record.held_by:
                raise UserError(_("Please specify who holds the excess funds."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("held_by"):
                raise UserError(_("Please specify who holds the excess funds."))
        records = super(TrustExcessFunds, self).create(vals_list)
        return records

    def write(self, vals):
        if "held_by" in vals and not vals.get("held_by"):
            raise UserError(_("Please specify who holds the excess funds."))
        return super(TrustExcessFunds, self).write(vals)

    # =====================
    # Computed Methods
    # =====================

    @api.depends("deal_id")
    def _compute_trust_balance(self):
        for record in self:
            if record.deal_id:
                trust_transactions = record.deal_id.transaction_line_ids.filtered(
                    lambda t: t.journal_type == "trust" and t.held_by == "our_office"
                )
                record.trust_balance = sum(trust_transactions.mapped("amount"))
            else:
                record.trust_balance = 0.0

    @api.depends("deal_id")
    def _compute_excess_held(self):
        for rec in self:
            total_deposits = rec._get_total_deposits()
            amount_receivable = rec._get_amount_receivable()
            excess = total_deposits - amount_receivable
            rec.excess_held = excess if excess > 0 else 0.0
            rec.amount = rec.excess_held

    # =====================
    # Action Methods
    # =====================

    def action_pay_excess_funds(self):
        self.ensure_one()
        brokerage_prefs = self.env["brokerage.preferences"].search([], limit=1)

        # Validate Brokerage Preferences
        required_prefs_fields = [
            "trust_journal",
            "trust_liability_account",
            "trust_bank_account",
            "trust_deposit_product_id",
        ]
        missing_prefs_fields = [
            field
            for field in required_prefs_fields
            if not getattr(brokerage_prefs, field)
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

        price = self.excess_held

        if price <= 0:
            raise UserError(_("There are no excess funds to pay."))

        # Determine the partner to pay excess funds to
        partner = self._get_partner_for_excess_payment()
        if not partner:
            raise UserError(_("No partner found for excess funds payment."))

        # Create and post refund invoice
        refund_invoice = self._create_refund_invoice(partner, brokerage_prefs, price)
        refund_invoice.action_post()
        self.invoice_id = refund_invoice.id

        # Register payment
        payment = self._register_payment(brokerage_prefs, refund_invoice, price)
        payment.action_post()
        self.payment_id = payment.id
        refund_invoice.payment_reference = payment.name

        # Create transaction line
        self._create_transaction_line(price, payment, brokerage_prefs, partner)

        # Update fields
        self.write(
            {
                "is_paid": True,
                "date_posted": fields.Date.today(),
            }
        )

        # Notification
        message = (
            _("An excess fund payment of %s has been successfully created and posted.")
            % price
        )
        return self._display_notification(_("Excess Funds Paid!"), message)

    # =====================
    # Helper Methods
    # =====================

    def _get_total_deposits(self):
        self.ensure_one()
        deal = self.deal_id
        if not deal:
            return 0.0
        deposit_transactions = deal.transaction_line_ids.filtered(
            lambda t: t.transaction_type in ["trust_receipt", "trust_refund"]
            and t.journal_type == "trust"
            and t.held_by == "our_office"
        )
        total_deposits = sum(deposit_transactions.mapped("amount"))
        return total_deposits

    def _get_amount_receivable(self):
        self.ensure_one()
        deal = self.deal_id
        if not deal:
            return 0.0
        amount_receivable = deal.amount_receivable
        return amount_receivable

    def _get_partner_for_excess_payment(self):
        self.ensure_one()
        deal = self.deal_id
        payment_source = self._determine_excess_payment_source()
        if payment_source in ["buyer_lawyer", "seller_lawyer"]:
            return self._get_active_law_firm_partner(payment_source.split("_")[0])
        elif payment_source in ["buyer_brokerage", "seller_brokerage"]:
            return self._get_other_brokerage_partner()
        elif payment_source in ["buyer", "seller"]:
            return self._get_buyer_seller_partner(payment_source)
        else:
            return False

    def _determine_excess_payment_source(self):
        self.ensure_one()
        deal = self.deal_id
        if not deal:
            return None
        end_type = deal.end_id.type
        if end_type == "seller":
            return deal.seller_trust_overage
        elif end_type == "buyer":
            return deal.buyer_trust_overage
        else:
            return None

    def _get_active_law_firm_partner(self, role):
        law_firm = self.deal_id.law_firm_ids.filtered(
            lambda l: l.end_id.type == role and l.is_active
        )
        if law_firm:
            return law_firm[0].firm_id
        return False

    def _get_other_brokerage_partner(self):
        other_broker = self.deal_id.other_broker_ids.filtered(lambda ob: ob.is_active)
        if other_broker:
            return other_broker[0].brokerage_id
        return False

    def _get_buyer_seller_partner(self, role):
        buyers_sellers = self.deal_id.buyers_sellers_ids.filtered(
            lambda bs: bs.end_id.type == role
        )
        if buyers_sellers:
            names = " and/or ".join(buyers_sellers.mapped("partner_id.name"))
            partner = self.env["res.partner"].search([("name", "=", names)], limit=1)
            if not partner:
                partner = self.env["res.partner"].create({"name": names})
            return partner
        return False

    def _create_refund_invoice(self, partner, brokerage_prefs, amount):
        product = brokerage_prefs.trust_deposit_product_id
        if not product:
            raise UserError(
                _(
                    "The 'Trust Deposits' product is not configured in Brokerage Preferences."
                )
            )
        invoice_line = {
            "product_id": product.id,
            "account_id": brokerage_prefs.trust_liability_account.id,
            "name": _("Payment of Excess Funds"),
            "quantity": 1,
            "price_unit": amount,
            "tax_ids": [],
        }
        invoice_vals = {
            "move_type": "out_refund",
            "partner_id": partner.id,
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": [(0, 0, invoice_line)],
            "deal_id": self.deal_id.id,
            "journal_id": brokerage_prefs.trust_journal.id,
        }
        return self.env["account.move"].create(invoice_vals)

    def _register_payment(self, brokerage_prefs, invoice, amount):
        payment_method = self.env.ref(
            "account.account_payment_method_manual_out", raise_if_not_found=False
        )
        if not payment_method:
            raise UserError(
                _(
                    "Manual Out Payment Method is not defined. Please check the configuration."
                )
            )

        payment_vals = {
            "payment_date": fields.Date.today(),
            "amount": amount,
            "payment_type": "outbound",
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
            "transaction_type": "trust_excess_payment",
            "deal_id": self.deal_id.id,
            "amount": -amount,
            "deposited": -amount,
            "date_received": self.date_received,
            "date_posted": fields.Date.today(),
            "journal_type": "trust",
            "held_by": self.held_by,
            "payment_method": self.payment_method,
            "reference_number": self.reference_number,
            "notes": self.notes,
            "invoice_id": self.invoice_id.id,
            "payment_id": payment.id,
            "bank_account_id": brokerage_prefs.trust_bank_account.id,
            "partner_id": partner.id,
            "trust_excess_funds_id": self.id,
        }
        self.env["transaction.line"].create(transaction_line_vals)

    def _display_notification(self, title, message):
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
