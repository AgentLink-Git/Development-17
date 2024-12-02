# models/financial/trust_excess_funds.py

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)

class TrustRefund(models.Model):
    _name = "trust.refund"
    _description = "Trust Refund"
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
        selection=[("trust_refund", "Trust Refund")],
        default="trust_refund",
        required=True,
        tracking=True,
    )
    amount = fields.Monetary(
        string="Amount",
        currency_field="currency_id",
        compute="_compute_refund_amount",
        store=True,
        readonly=False,
        help="Amount to refund based on the deposit type and transactions.",
    )
    deposited = fields.Monetary(
        string="Deposited Amount",
        currency_field="currency_id",
        tracking=True,
        readonly=True,
    )

    # =====================
    # Date Fields
    # =====================
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

    # =====================
    # Additional Fields
    # =====================
    refund_deposit_type = fields.Selection(
        selection=[("buyer", "Buyer Deposit"), ("seller", "Seller Deposit")],
        string="Refund Deposit Type",
        required=True,
        tracking=True,
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
    is_refunded = fields.Boolean(
        string="Is Refunded",
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
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        ondelete="cascade",
    )
    transaction_line_ids = fields.One2many(
        "transaction.line",
        "trust_refund_id",
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
        records = super(TrustRefund, self).create(vals_list)
        return records

    def write(self, vals):
        if "held_by" in vals and not vals.get("held_by"):
            raise UserError(_("Please specify who holds the trust funds."))
        return super(TrustRefund, self).write(vals)

    # =====================
    # Default Values
    # =====================
    @api.model
    def default_get(self, fields_list):
        res = super(TrustRefund, self).default_get(fields_list)
        deal_id = res.get('deal_id')
        if deal_id:
            deal = self.env['deal.records'].browse(deal_id)
            deposit_types = []
            if deal.buyer_deposit > 0:
                deposit_types.append('buyer')
            if deal.seller_deposit > 0:
                deposit_types.append('seller')
            if len(deposit_types) == 1:
                res['refund_deposit_type'] = deposit_types[0]
        return res

    # =====================
    # Computed Methods
    # =====================

    @api.depends("refund_deposit_type", "deal_id.transaction_line_ids")
    def _compute_trust_balance(self):
        for record in self:
            if not record.deal_id or not record.refund_deposit_type:
                record.trust_balance = 0.0
                continue

            # Filter transactions based on deposit type
            if record.refund_deposit_type == 'buyer':
                transactions = record.deal_id.transaction_line_ids.filtered(
                    lambda t: t.transaction_type in ['trust_receipt', 'trust_refund']
                    and t.received_from_id == 'buyer'
                    and t.held_by == "our_office"
                )
            elif record.refund_deposit_type == 'seller':
                transactions = record.deal_id.transaction_line_ids.filtered(
                    lambda t: t.transaction_type in ['trust_receipt', 'trust_refund']
                    and t.received_from_id == 'seller'
                    and t.held_by == "our_office"
                )
            else:
                transactions = self.env['transaction.line']

            # Sum amounts to get net trust balance for the deposit type
            record.trust_balance = sum(transactions.mapped('amount'))

    @api.depends("trust_balance")
    def _compute_refund_amount(self):
        for record in self:
            record.amount = abs(record.trust_balance) if record.trust_balance < 0 else record.trust_balance

    # =====================
    # Action Methods
    # =====================

    def action_return_trust_deposit(self):
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

        trust_balance = self.trust_balance

        if trust_balance <= 0:
            raise UserError(_("No available trust balance to refund for the selected deposit type."))

        # Get the partner to refund
        partner = self._get_partner_for_refund()
        if not partner:
            raise ValidationError(_("No matching buyer/seller found for this transaction."))

        # Create and post refund invoice
        refund_invoice = self._create_refund_invoice(partner, brokerage_prefs, trust_balance)
        refund_invoice.action_post()
        self.invoice_id = refund_invoice.id

        # Register payment
        payment = self._register_payment(brokerage_prefs, refund_invoice, trust_balance)
        payment.action_post()
        self.payment_id = payment.id
        refund_invoice.payment_reference = payment.name

        # Create transaction line
        self._create_transaction_line(trust_balance, payment, brokerage_prefs, partner)

        # Update fields
        self.write({
            'is_refunded': True,
            'date_posted': fields.Date.today(),
        })

        # Update deal's deposit amount
        if self.refund_deposit_type == 'buyer':
            deal.buyer_deposit -= self.amount
        elif self.refund_deposit_type == 'seller':
            deal.seller_deposit -= self.amount

        # Notification
        message = _("A trust refund payment of %s has been successfully created and posted.") % trust_balance
        return self._display_notification(_("Payment Created and Posted!"), message)

    # =====================
    # Helper Methods
    # =====================

    def _get_partner_for_refund(self):
        # Collate buyer or seller names
        if self.refund_deposit_type == "buyer":
            buyers = self.deal_id.buyers_sellers_ids.filtered(
                lambda bs: bs.end_id.type == "buyer"
            )
            if not buyers:
                return False
            # Collate names
            names = " and/or ".join(buyers.mapped("partner_id.name"))
            # Use the first buyer's partner as the base
            partner = buyers[0].partner_id
        elif self.refund_deposit_type == "seller":
            sellers = self.deal_id.buyers_sellers_ids.filtered(
                lambda bs: bs.end_id.type == "seller"
            )
            if not sellers:
                return False
            # Collate names
            names = " and/or ".join(sellers.mapped("partner_id.name"))
            # Use the first seller's partner as the base
            partner = sellers[0].partner_id
        else:
            return False

        # Create or update a partner record with the collated names
        partner_name = names
        existing_partner = self.env['res.partner'].search([('name', '=', partner_name)], limit=1)
        if existing_partner:
            return existing_partner
        else:
            # Create a new partner record
            partner_vals = {
                'name': partner_name,
                'is_company': False,
                'customer_rank': 0,
                'supplier_rank': 0,
            }
            new_partner = self.env['res.partner'].create(partner_vals)
            return new_partner

    def _create_refund_invoice(self, partner, brokerage_prefs, amount):
        product = brokerage_prefs.trust_deposit_product_id
        if not product:
            raise UserError(
                _("The 'Trust Deposits' product is not configured in Brokerage Preferences.")
            )
        invoice_line = {
            "product_id": product.id,
            "account_id": brokerage_prefs.trust_liability_account.id,
            "name": _("Trust Deposit Refund"),
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

    def _register_payment(self, brokerage_prefs, refund_invoice, amount):
        payment_method = self.env.ref(
            "account.account_payment_method_manual_out", raise_if_not_found=False
        )
        if not payment_method:
            raise UserError(
                _("Manual Out Payment Method is not defined. Please check the configuration.")
            )

        payment_vals = {
            'payment_date': fields.Date.today(),
            'amount': amount,
            'payment_type': 'outbound',
            'partner_type': 'customer',
            'partner_id': refund_invoice.partner_id.id,
            'journal_id': brokerage_prefs.trust_bank_account.id,
            'payment_method_id': payment_method.id,
            'communication': refund_invoice.name,
            'deal_id': self.deal_id.id,
        }
        payment = self.env['account.payment'].create(payment_vals)
        return payment

    def _create_transaction_line(self, amount, payment, brokerage_prefs, partner):
        transaction_line_vals = {
            "transaction_type": "trust_refund",
            "deal_id": self.deal_id.id,
            "amount": -amount,  # Negative amount for refund
            "deposited": -amount,
            "date_received": self.date_received,
            "date_posted": fields.Date.today(),
            "journal_type": "trust",
            "held_by": self.held_by,
            "payment_method": self.payment_method,
            "reference_number": self.reference_number,
            "received_from_id": self.refund_deposit_type,
            "notes": self.notes,
            "invoice_id": self.invoice_id.id,
            "payment_id": payment.id,
            "bank_account_id": brokerage_prefs.trust_bank_account.id,
            "partner_id": partner.id,
            "trust_refund_id": self.id,
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

    # =====================
    # Onchange Methods
    # =====================

    @api.onchange('deal_id')
    def _onchange_deal_id(self):
        if not self.deal_id:
            return
        deposit_types = []
        if self.deal_id.buyer_deposit > 0:
            deposit_types.append(('buyer', 'Buyer Deposit'))
        if self.deal_id.seller_deposit > 0:
            deposit_types.append(('seller', 'Seller Deposit'))

        if len(deposit_types) == 1:
            self.refund_deposit_type = deposit_types[0][0]
        else:
            self.refund_deposit_type = False

    @api.onchange('refund_deposit_type')
    def _onchange_refund_deposit_type(self):
        self._compute_trust_balance()
        self._compute_refund_amount()

    # =====================
    # Constraints
    # =====================

    @api.constrains('refund_deposit_type')
    def _check_refund_deposit_type(self):
        for record in self:
            if not record.refund_deposit_type:
                raise ValidationError(_("Please select the type of deposit to refund."))