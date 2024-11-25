from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class CommissionAdvance(models.Model):
    _name = "commission.advance"
    _description = "Commission Advance"
    _inherit = ["mail.thread", "mail.activity.mixin", "shared.fields.mixin"]

    # =====================
    # Basic Information
    # =====================
    partner_id = fields.Many2one(
        "res.partner",
        string="Sales Agent",
        required=True,
        domain=[("is_sales_agent", "=", True)],
        ondelete="restrict",
        tracking=True,
    )
    advance_request_date = fields.Date(
        string="Request Date",
        default=fields.Date.today,
        required=True,
        tracking=True,
    )
    advance_payment_date = fields.Date(
        string="Payment Date",
        tracking=True,
    )
    advance_approved_date = fields.Date(
        string="Approval Date",
        tracking=True,
    )
    advance_repaid_date = fields.Date(
        string="Repayment Date",
        tracking=True,
    )
    broker_approved_date = fields.Date(
        string="Broker Approval Date",
        tracking=True,
    )

    # =====================
    # Financial Details
    # =====================
    amount_requested = fields.Monetary(
        string="Amount Requested",
        currency_field="currency_id",
        required=True,
        tracking=True,
    )
    amount_advanced = fields.Monetary(
        string="Amount Advanced",
        currency_field="currency_id",
        readonly=True,
        tracking=True,
    )
    advance_fee = fields.Monetary(
        string="Advance Fee",
        currency_field="currency_id",
        readonly=True,
        tracking=True,
    )
    daily_interest_rate = fields.Float(
        string="Daily Interest Rate (%)",
        readonly=True,
        tracking=True,
    )
    interest_charges = fields.Monetary(
        string="Interest Charges",
        currency_field="currency_id",
        compute="_compute_interest_charges",
        store=True,
        tracking=True,
    )
    total_advance_fees = fields.Monetary(
        string="Total Advance Fees",
        currency_field="currency_id",
        compute="_compute_total_advance_fees",
        store=True,
        tracking=True,
    )
    advance_amt_repaid = fields.Monetary(
        string="Advance Repaid",
        currency_field="currency_id",
        default=0.0,
        tracking=True,
    )
    advance_amt_outstanding = fields.Monetary(
        string="Advance Outstanding",
        compute="_compute_advance_amt_outstanding",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    available_for_advance = fields.Monetary(
        string="Available for Advance",
        compute="_compute_available_for_advance",
        store=True,
        currency_field="currency_id",
    )

    # =====================
    # Status Fields
    # =====================
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("requested", "Requested"),
            ("approved", "Approved"),
            ("paid", "Paid"),
            ("repaid", "Repaid"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        tracking=True,
    )

    # =====================
    # Relationships
    # =====================
    payment_ids = fields.One2many(
        "account.payment",
        "commission_advance_id",
        string="Payments",
    )

    # =====================
    # Computed Fields
    # =====================
    @api.depends(
        "amount_advanced",
        "advance_fee",
        "advance_payment_date",
        "daily_interest_rate",
    )
    def _compute_interest_charges(self):
        for rec in self:
            if rec.amount_advanced and rec.advance_payment_date:
                days_outstanding = (fields.Date.today() - rec.advance_payment_date).days
                days_outstanding = max(days_outstanding, 0)  # Ensure non-negative
                # Calculate total interest: (amount_advanced + advance_fee) * (daily_interest_rate / 100) * days_outstanding
                total_interest = (
                    (rec.amount_advanced + rec.advance_fee)
                    * (rec.daily_interest_rate / 100.0)
                    * days_outstanding
                )
                rec.interest_charges = total_interest
            else:
                rec.interest_charges = 0.0

    @api.depends("advance_fee", "interest_charges")
    def _compute_total_advance_fees(self):
        for rec in self:
            rec.total_advance_fees = rec.advance_fee + rec.interest_charges

    @api.depends(
        "amount_advanced",
        "total_advance_fees",
        "advance_amt_repaid",
    )
    def _compute_advance_amt_outstanding(self):
        for rec in self:
            rec.advance_amt_outstanding = (
                rec.amount_advanced + rec.total_advance_fees - rec.advance_amt_repaid
            )

    @api.depends("deal_id", "partner_id")
    def _compute_available_for_advance(self):
        for rec in self:
            # Fetch the maximum percentage from brokerage preferences
            brokerage_prefs = self.env["brokerage.preferences"].search([], limit=1)
            max_percentage = brokerage_prefs.advance_maximum_percentage or 70.0
            # Compute available_for_advance using max_percentage
            sales_agent_line = self.env["sales.agents.and.referrals"].search(
                [
                    ("deal_id", "=", rec.deal_id.id),
                    ("partner_id", "=", rec.partner_id.id),
                ],
                limit=1,
            )
            if sales_agent_line:
                base_amount = (
                    sales_agent_line.gross_amount - sales_agent_line.split_fees
                )
                rec.available_for_advance = base_amount * (max_percentage / 100.0)
            else:
                rec.available_for_advance = 0.0

    # =====================
    # Lifecycle Methods
    # =====================
    def action_request_advance(self):
        """
        Transition from draft to requested.
        """
        self.ensure_one()
        if self.amount_requested <= 0:
            raise ValidationError(_("Amount requested must be greater than zero."))
        if self.amount_requested > self.available_for_advance:
            raise ValidationError(
                _("Amount requested exceeds the available amount for advance.")
            )
        self.state = "requested"

    def action_approve_advance(self):
        """
        Approve the advance request.
        """
        self.ensure_one()
        if self.state != "requested":
            raise ValidationError(_("Only requested advances can be approved."))

        # Fetch advance_fee and daily_interest_rate from brokerage preferences
        brokerage_prefs = self.env["brokerage.preferences"].search([], limit=1)
        if not brokerage_prefs:
            raise UserError(_("Brokerage Preferences are not configured."))

        self.advance_fee = brokerage_prefs.advance_fee or 0.0
        self.daily_interest_rate = brokerage_prefs.advance_daily_interest_rate or 0.0
        self.amount_advanced = self.amount_requested
        self.advance_payment_date = fields.Date.today()
        self.advance_approved_date = fields.Date.today()
        self.broker_approved_date = fields.Date.today()
        self.state = "approved"

        # Create a payment to the sales agent
        payment = self._create_advance_payment()
        _logger.info(
            f"Advance payment created with ID: {payment.id} for Commission Advance ID: {self.id}"
        )

    def _create_advance_payment(self):
        """
        Create a payment record for the commission advance.
        """
        payment_method = self.partner_id.payment_method
        if not payment_method:
            raise UserError(_("Sales Agent must have a payment method defined."))

        journal = self._get_journal_for_payment(payment_method)
        if not journal:
            raise UserError(
                _("No journal found for the payment method: %s") % payment_method
            )

        payment_vals = {
            "partner_id": self.partner_id.id,
            "amount": self.amount_advanced,
            "currency_id": self.currency_id.id,
            "payment_date": fields.Date.today(),
            "payment_type": "outbound",
            "journal_id": journal.id,
            "payment_method_id": self._get_payment_method_id(payment_method),
            "commission_advance_id": self.id,
            "ref": _("Commission Advance Payment"),
            "state": "draft",
        }
        payment = self.env["account.payment"].create(payment_vals)
        payment.action_post()
        return payment

    def _get_journal_for_payment(self, payment_method):
        """
        Retrieve the appropriate journal based on the payment method.
        """
        journal = False
        if payment_method == "cheque":
            journal = self.env["account.journal"].search(
                [("type", "=", "bank"), ("name", "ilike", "Cheque")], limit=1
            )
        elif payment_method == "direct_deposit":
            journal = self.env["account.journal"].search(
                [("type", "=", "bank"), ("name", "ilike", "Direct Deposit")], limit=1
            )
        return journal

    def _get_payment_method_id(self, payment_method):
        """
        Retrieve the payment method ID based on the payment method string.
        """
        if payment_method == "cheque":
            return self.env.ref("account.account_payment_method_manual_out").id
        elif payment_method == "direct_deposit":
            return self.env.ref("account.account_payment_method_manual_out").id
        else:
            return False

    def action_repay_advance(self):
        """
        Handle the repayment of the commission advance.
        """
        self.ensure_one()
        if self.state not in ["approved", "paid"]:
            raise ValidationError(_("Only approved or paid advances can be repaid."))
        if self.advance_amt_outstanding <= 0:
            raise ValidationError(_("No outstanding amount to repay."))

        # Repayment amount can be set via a wizard or similar; here we'll assume full repayment
        repayment_amount = self.advance_amt_outstanding

        # Create a payment from the sales agent to the company
        payment = self._create_repayment_payment(repayment_amount)
        _logger.info(
            f"Repayment payment created with ID: {payment.id} for Commission Advance ID: {self.id}"
        )

        # Update repaid amount and state
        self.advance_amt_repaid += repayment_amount
        if self.advance_amt_outstanding <= 0:
            self.state = "repaid"
            self.advance_repaid_date = fields.Date.today()

    def _create_repayment_payment(self, amount):
        """
        Create a payment record for the repayment.
        """
        payment_method = self.partner_id.payment_method
        if not payment_method:
            raise UserError(_("Sales Agent must have a payment method defined."))

        journal = self._get_journal_for_payment(payment_method)
        if not journal:
            raise UserError(
                _("No journal found for the payment method: %s") % payment_method
            )

        payment_vals = {
            "partner_id": self.partner_id.id,
            "amount": amount,
            "currency_id": self.currency_id.id,
            "payment_date": fields.Date.today(),
            "payment_type": "inbound",
            "journal_id": journal.id,
            "payment_method_id": self._get_payment_method_id(payment_method),
            "commission_advance_id": self.id,
            "ref": _("Commission Advance Repayment"),
            "state": "draft",
        }
        payment = self.env["account.payment"].create(payment_vals)
        payment.action_post()
        return payment

    # =====================
    # Constraints
    # =====================
    @api.constrains("amount_requested")
    def _check_amount_requested(self):
        for rec in self:
            if rec.amount_requested <= 0:
                raise ValidationError(_("Amount Requested must be greater than zero."))
            if rec.amount_requested > rec.available_for_advance:
                raise ValidationError(
                    _(
                        "Amount Requested cannot exceed the available amount for advance."
                    )
                )

    @api.constrains("partner_id", "deal_id")
    def _check_unique_advance_per_deal(self):
        for rec in self:
            existing = self.search(
                [
                    ("deal_id", "=", rec.deal_id.id),
                    ("partner_id", "=", rec.partner_id.id),
                    ("id", "!=", rec.id),
                    ("state", "!=", "cancelled"),
                ]
            )
            if existing:
                raise ValidationError(
                    _("A commission advance already exists for this deal and partner.")
                )

    # =====================
    # Overriding Unlink Method
    # =====================
    def unlink(self):
        for rec in self:
            if rec.state in ["approved", "paid", "repaid"]:
                raise UserError(
                    _("Cannot delete an approved, paid, or repaid commission advance.")
                )
        return super(CommissionAdvance, self).unlink()
