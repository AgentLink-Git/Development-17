# models/commission_advance.py

"""
Module for managing Commission Advances.
This module defines the CommissionAdvance model, which handles the creation, approval,
payment, and repayment of commission advances for sales agents. It includes
fields for tracking financial details, status transitions, and relationships
with other models such as res.partner and account.payment.
"""

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

# Configure the logger for this module
_logger = logging.getLogger(__name__)


class CommissionAdvance(models.Model):
    """
    Model for Commission Advance.
    Manages commission advances requested by sales agents, including approval,
    payment, interest calculations, and repayments.
    """
    _name = "commission.advance"
    _description = "Commission Advance"
    _inherit = ["mail.thread", "mail.activity.mixin", "shared.fields.mixin"]
    _order = "advance_request_date desc"

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
        help="Select the sales agent requesting the commission advance."
    )
    deal_id = fields.Many2one(
        'deal.records',
        string='Deal',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    advance_request_date = fields.Date(
        string="Request Date",
        default=fields.Date.today,
        required=True,
        tracking=True,
        help="Date when the advance was requested."
    )
    advance_payment_date = fields.Date(
        string="Payment Date",
        tracking=True,
        help="Date when the advance was paid."
    )
    advance_approved_date = fields.Date(
        string="Approval Date",
        tracking=True,
        help="Date when the advance was approved."
    )
    advance_repaid_date = fields.Date(
        string="Repayment Date",
        tracking=True,
        help="Date when the advance was fully repaid."
    )
    broker_approved_date = fields.Date(
        string="Broker Approval Date",
        tracking=True,
        help="Date when the broker approved the advance."
    )

    # =====================
    # Financial Details
    # =====================
    amount_requested = fields.Monetary(
        string="Amount Requested",
        currency_field="currency_id",
        required=True,
        tracking=True,
        help="Total amount requested for the commission advance."
    )
    amount_advanced = fields.Monetary(
        string="Amount Advanced",
        currency_field="currency_id",
        readonly=True,
        tracking=True,
        help="Amount that has been advanced to the sales agent."
    )
    advance_fee = fields.Monetary(
        string="Advance Fee",
        currency_field="currency_id",
        readonly=True,
        tracking=True,
        help="Fee charged for the advance."
    )
    daily_interest_rate = fields.Float(
        string="Daily Interest Rate (%)",
        readonly=True,
        tracking=True,
        help="Daily interest rate applied to the advance."
    )
    interest_charges = fields.Monetary(
        string="Interest Charges",
        currency_field="currency_id",
        compute="_compute_interest_charges",
        store=True,
        tracking=True,
        help="Total interest charges accumulated on the advance."
    )
    total_advance_fees = fields.Monetary(
        string="Total Advance Fees",
        currency_field="currency_id",
        compute="_compute_total_advance_fees",
        store=True,
        tracking=True,
        help="Sum of advance fee and interest charges."
    )
    advance_amt_repaid = fields.Monetary(
        string="Advance Repaid",
        currency_field="currency_id",
        default=0.0,
        tracking=True,
        help="Amount of the advance that has been repaid."
    )
    advance_amt_outstanding = fields.Monetary(
        string="Advance Outstanding",
        compute="_compute_advance_amt_outstanding",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Remaining amount of the advance that is outstanding."
    )
    available_for_advance = fields.Monetary(
        string="Available for Advance",
        compute="_compute_available_for_advance",
        store=True,
        currency_field='currency_id',
        help="Maximum amount available for the advance based on brokerage preferences."
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
        help="Current status of the commission advance."
    )

    # =====================
    # Relationships
    # =====================
    payment_ids = fields.One2many(
        "account.payment",
        "commission_advance_id",
        string="Payments",
        help="Payments associated with this commission advance."
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
        """
        Compute the interest charges based on the amount advanced, advance fee,
        daily interest rate, and the number of days outstanding.
        """
        for rec in self:
            if rec.amount_advanced and rec.advance_payment_date:
                days_outstanding = (fields.Date.today() - rec.advance_payment_date).days
                days_outstanding = max(days_outstanding, 0)  # Ensure non-negative
                # Calculate total interest: (amount_advanced + advance_fee) * (daily_interest_rate / 100) * days_outstanding
                total_interest = (rec.amount_advanced + rec.advance_fee) * (rec.daily_interest_rate / 100.0) * days_outstanding
                rec.interest_charges = total_interest
                _logger.debug(
                    "Computed interest charges: %s for CommissionAdvance ID %s",
                    rec.interest_charges,
                    rec.id
                )
            else:
                rec.interest_charges = 0.0
                _logger.debug(
                    "No interest charges computed for CommissionAdvance ID %s.",
                    rec.id
                )

    @api.depends("advance_fee", "interest_charges")
    def _compute_total_advance_fees(self):
        """
        Compute the total advance fees by summing the advance fee and interest charges.
        """
        for rec in self:
            rec.total_advance_fees = rec.advance_fee + rec.interest_charges
            _logger.debug(
                "Computed total advance fees: %s for CommissionAdvance ID %s",
                rec.total_advance_fees,
                rec.id
            )

    @api.depends(
        "amount_advanced",
        "total_advance_fees",
        "advance_amt_repaid",
    )
    def _compute_advance_amt_outstanding(self):
        """
        Compute the outstanding advance amount by subtracting the repaid amount
        from the sum of amount advanced and total advance fees.
        """
        for rec in self:
            rec.advance_amt_outstanding = (
                rec.amount_advanced + rec.total_advance_fees - rec.advance_amt_repaid
            )
            _logger.debug(
                "Computed advance amount outstanding: %s for CommissionAdvance ID %s",
                rec.advance_amt_outstanding,
                rec.id
            )

    @api.depends('deal_id', 'partner_id')
    def _compute_available_for_advance(self):
        """
        Compute the available amount for advance based on brokerage preferences
        and the sales agent's deal details.
        """
        for rec in self:
            # Fetch the maximum percentage from brokerage preferences
            brokerage_prefs = self.env['brokerage.preferences'].search([], limit=1)
            max_percentage = brokerage_prefs.advance_maximum_percentage or 70.0
            # Compute available_for_advance using max_percentage
            sales_agent_line = self.env['sales.agents.and.referrals'].search([
                ('deal_id', '=', rec.deal_id.id),
                ('partner_id', '=', rec.partner_id.id)
            ], limit=1)
            if sales_agent_line:
                base_amount = sales_agent_line.gross_amount - sales_agent_line.split_fees
                rec.available_for_advance = base_amount * (max_percentage / 100.0)
                _logger.debug(
                    "Computed available for advance: %s for CommissionAdvance ID %s",
                    rec.available_for_advance,
                    rec.id
                )
            else:
                rec.available_for_advance = 0.0
                _logger.debug(
                    "No sales agent line found. Set available for advance to 0 for CommissionAdvance ID %s.",
                    rec.id
                )

    # =====================
    # Lifecycle Methods
    # =====================
    def action_request_advance(self):
        """
        Transition the commission advance from draft to requested.
        Validates the requested amount and updates the state.
        """
        self.ensure_one()
        _logger.debug("Requesting commission advance for CommissionAdvance ID %s.", self.id)

        if self.amount_requested <= 0:
            _logger.error("Amount requested must be greater than zero for CommissionAdvance ID %s.", self.id)
            raise ValidationError(_("Amount requested must be greater than zero."))

        if self.amount_requested > self.available_for_advance:
            _logger.error(
                "Amount requested exceeds available for advance for CommissionAdvance ID %s.",
                self.id
            )
            raise ValidationError(_("Amount requested cannot exceed the available amount for advance."))

        self.state = "requested"
        _logger.info("CommissionAdvance ID %s transitioned to 'requested' state.", self.id)

    def action_approve_advance(self):
        """
        Approve the commission advance request.
        Sets the advance fee and daily interest rate from brokerage preferences,
        updates relevant fields, transitions the state to approved, and creates a payment.
        """
        self.ensure_one()
        _logger.debug("Approving commission advance for CommissionAdvance ID %s.", self.id)

        if self.state != "requested":
            _logger.error(
                "Attempted to approve commission advance not in 'requested' state for ID %s.",
                self.id
            )
            raise ValidationError(_("Only requested advances can be approved."))

        # Fetch advance_fee and daily_interest_rate from brokerage preferences
        brokerage_prefs = self.env["brokerage.preferences"].search([], limit=1)
        if not brokerage_prefs:
            _logger.error("Brokerage Preferences are not configured.")
            raise UserError(_("Brokerage Preferences are not configured."))

        self.advance_fee = brokerage_prefs.advance_fee or 0.0
        self.daily_interest_rate = brokerage_prefs.advance_daily_interest_rate or 0.0
        self.amount_advanced = self.amount_requested
        today = fields.Date.today()
        self.advance_payment_date = today
        self.advance_approved_date = today
        self.broker_approved_date = today
        self.state = "approved"
        _logger.info("CommissionAdvance ID %s approved.", self.id)

        # Create a payment to the sales agent
        payment = self._create_advance_payment()
        _logger.info(
            "Advance payment created with ID: %s for CommissionAdvance ID: %s",
            payment.id,
            self.id
        )

    def _create_advance_payment(self):
        """
        Create a payment record for the commission advance.
        """
        payment_method = self.partner_id.payment_method
        if not payment_method:
            _logger.error("Sales Agent ID %s must have a payment method defined.", self.partner_id.id)
            raise UserError(_("Sales Agent must have a payment method defined."))

        journal = self._get_journal_for_payment(payment_method)
        if not journal:
            _logger.error("No journal found for payment method: %s", payment_method)
            raise UserError(_("No journal found for the payment method: %s") % payment_method)

        payment_method_id = self._get_payment_method_id(payment_method)
        if not payment_method_id:
            _logger.error("No payment method ID found for payment method: %s", payment_method)
            raise UserError(_("No payment method found for the payment method: %s") % payment_method)

        payment_vals = {
            "partner_id": self.partner_id.id,
            "amount": self.amount_advanced,
            "currency_id": self.currency_id.id,
            "payment_date": fields.Date.today(),
            "payment_type": "outbound",
            "journal_id": journal.id,
            "payment_method_id": payment_method_id,
            "commission_advance_id": self.id,
            "ref": _("Commission Advance Payment"),
            "state": "draft",
        }
        _logger.debug("Creating advance payment with values: %s", payment_vals)
        payment = self.env["account.payment"].create(payment_vals)
        payment.action_post()
        _logger.debug("Advance payment posted with ID: %s", payment.id)
        return payment

    def _get_journal_for_payment(self, payment_method):
        """
        Retrieve the appropriate journal based on the payment method.
        """
        journal = False
        if payment_method == "cheque":
            journal = self.env["account.journal"].search([
                ("type", "=", "bank"),
                ("name", "ilike", "Cheque")
            ], limit=1)
        elif payment_method == "direct_deposit":
            journal = self.env["account.journal"].search([
                ("type", "=", "bank"),
                ("name", "ilike", "Direct Deposit")
            ], limit=1)
        _logger.debug(
            "Retrieved journal: %s for payment method: %s",
            journal.name if journal else "None",
            payment_method
        )
        return journal

    def _get_payment_method_id(self, payment_method):
        """
        Retrieve the payment method ID based on the payment method string.
        """
        if payment_method == "cheque":
            return self.env.ref('account.account_payment_method_manual_out').id
        elif payment_method == "direct_deposit":
            return self.env.ref('account.account_payment_method_manual_out').id
        _logger.debug("No payment method ID found for payment method: %s", payment_method)
        return False

    def action_repay_advance(self):
        """
        Handle the repayment of the commission advance.
        Creates a repayment payment, updates the repaid amount, and transitions the state if fully repaid.
        """
        self.ensure_one()
        _logger.debug("Repaying commission advance for CommissionAdvance ID %s.", self.id)

        if self.state not in ["approved", "paid"]:
            _logger.error(
                "Attempted to repay commission advance not in 'approved' or 'paid' state for ID %s.",
                self.id
            )
            raise ValidationError(_("Only approved or paid advances can be repaid."))

        if self.advance_amt_outstanding <= 0:
            _logger.error(
                "No outstanding amount to repay for CommissionAdvance ID %s.",
                self.id
            )
            raise ValidationError(_("No outstanding amount to repay."))

        # Repayment amount can be set via a wizard or similar; here we'll assume full repayment
        repayment_amount = self.advance_amt_outstanding
        _logger.debug(
            "Repaying amount: %s for CommissionAdvance ID %s.",
            repayment_amount,
            self.id
        )

        # Create a payment from the sales agent to the company
        payment = self._create_repayment_payment(repayment_amount)
        _logger.info(
            "Repayment payment created with ID: %s for CommissionAdvance ID: %s",
            payment.id,
            self.id
        )

        # Update repaid amount and state
        self.advance_amt_repaid += repayment_amount
        _logger.debug(
            "Updated advance_amt_repaid to %s for CommissionAdvance ID %s.",
            self.advance_amt_repaid,
            self.id
        )

        if self.advance_amt_outstanding <= 0:
            self.state = "repaid"
            self.advance_repaid_date = fields.Date.today()
            _logger.info(
                "CommissionAdvance ID %s fully repaid and transitioned to 'repaid' state.",
                self.id
            )

    def _create_repayment_payment(self, amount):
        """
        Create a payment record for the repayment.
        """
        payment_method = self.partner_id.payment_method
        if not payment_method:
            _logger.error("Sales Agent ID %s must have a payment method defined for repayment.", self.partner_id.id)
            raise UserError(_("Sales Agent must have a payment method defined."))

        journal = self._get_journal_for_payment(payment_method)
        if not journal:
            _logger.error("No journal found for repayment payment method: %s", payment_method)
            raise UserError(_("No journal found for the payment method: %s") % payment_method)

        payment_method_id = self._get_payment_method_id(payment_method)
        if not payment_method_id:
            _logger.error("No payment method ID found for repayment payment method: %s", payment_method)
            raise UserError(_("No payment method found for the payment method: %s") % payment_method)

        payment_vals = {
            "partner_id": self.partner_id.id,
            "amount": amount,
            "currency_id": self.currency_id.id,
            "payment_date": fields.Date.today(),
            "payment_type": "inbound",
            "journal_id": journal.id,
            "payment_method_id": payment_method_id,
            "commission_advance_id": self.id,
            "ref": _("Commission Advance Repayment"),
            "state": "draft",
        }
        _logger.debug("Creating repayment payment with values: %s", payment_vals)
        payment = self.env["account.payment"].create(payment_vals)
        payment.action_post()
        _logger.debug("Repayment payment posted with ID: %s", payment.id)
        return payment

    # =====================
    # Constraints
    # =====================
    @api.constrains("amount_requested")
    def _check_amount_requested(self):
        """
        Ensure that the amount requested is greater than zero and does not exceed the available amount for advance.
        """
        for rec in self:
            if rec.amount_requested <= 0:
                _logger.error(
                    "Amount Requested must be greater than zero for CommissionAdvance ID %s.",
                    rec.id
                )
                raise ValidationError(
                    _("Amount Requested must be greater than zero.")
                )
            if rec.amount_requested > rec.available_for_advance:
                _logger.error(
                    "Amount Requested exceeds available for advance for CommissionAdvance ID %s.",
                    rec.id
                )
                raise ValidationError(
                    _("Amount Requested cannot exceed the available amount for advance.")
                )

    @api.constrains("partner_id", "deal_id")
    def _check_unique_advance_per_deal(self):
        """
        Ensure that only one commission advance exists per deal and partner, excluding cancelled states.
        """
        for rec in self:
            existing = self.search([
                ("deal_id", "=", rec.deal_id.id),
                ("partner_id", "=", rec.partner_id.id),
                ("id", "!=", rec.id),
                ("state", "!=", "cancelled"),
            ])
            if existing:
                _logger.error(
                    "Duplicate commission advance found for deal ID %s and partner ID %s.",
                    rec.deal_id.id,
                    rec.partner_id.id
                )
                raise ValidationError(
                    _("A commission advance already exists for this deal and partner.")
                )

    # =====================
    # Overriding Unlink Method
    # =====================
    def unlink(self):
        """
        Override the unlink method to prevent deletion of approved, paid, or repaid commission advances.
        """
        for rec in self:
            if rec.state in ["approved", "paid", "repaid"]:
                _logger.error(
                    "Attempted to delete a commission advance in '%s' state for ID %s.",
                    rec.state,
                    rec.id
                )
                raise UserError(
                    _("Cannot delete an approved, paid, or repaid commission advance.")
                )
            _logger.debug(
                "Deleting CommissionAdvance ID %s in '%s' state.",
                rec.id,
                rec.state
            )
        return super(CommissionAdvance, self).unlink()
		
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

class CommissionAdvance(models.Model):
    _name = "commission.advance"
    _description = "Commission Advance"
    _inherit = ["mail.thread", "mail.activity.mixin", "shared.fields.mixin"]

    partner_id = fields.Many2one('res.partner', string="Partner", required=True)
    advance_request_date = fields.Date(string="Advance Request Date", required=True)
    advance_payment_date = fields.Date(string="Payment Date", tracking=True)
    advance_approved_date = fields.Date(string="Approval Date", tracking=True)
    advance_repaid_date = fields.Date(string="Repayment Date", tracking=True)
    broker_approved_date = fields.Date(string="Broker Approval Date", tracking=True)
    amount_requested = fields.Monetary(string="Amount Requested", required=True)
    amount_advanced = fields.Monetary(string="Amount Advanced")
    advance_fee = fields.Monetary(string="Advance Fee")
    daily_interest_rate = fields.Float(string="Daily Interest Rate")
    interest_charges = fields.Monetary(string="Interest Charges", compute="_compute_interest_charges", store=True)
    total_advance_fees = fields.Monetary(string="Total Advance Fees", compute="_compute_total_advance_fees", store=True)
    advance_amt_repaid = fields.Monetary(string="Advance Amount Repaid")
    advance_amt_outstanding = fields.Monetary(string="Advance Amount Outstanding", compute="_compute_advance_amt_outstanding", store=True)
    available_for_advance = fields.Monetary(string="Available for Advance", compute="_compute_available_for_advance", store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('repaid', 'Repaid'),
        ('cancelled', 'Cancelled')
    ], string="Status", default='draft', tracking=True)
    payment_ids = fields.One2many('account.payment', 'commission_advance_id', string="Payments")

    @api.depends('daily_interest_rate', 'amount_advanced')
    def _compute_interest_charges(self):
        for record in self:
            record.interest_charges = (record.daily_interest_rate / 100) * record.amount_advanced

    @api.depends('amount_requested', 'advance_fee')
    def _compute_total_advance_fees(self):
        for record in self:
            record.total_advance_fees = record.amount_requested + record.advance_fee

    @api.depends('amount_requested', 'advance_amt_repaid')
    def _compute_advance_amt_outstanding(self):
        for record in self:
            record.advance_amt_outstanding = record.amount_requested - record.advance_amt_repaid

    @api.depends('amount_requested', 'total_advance_fees')
    def _compute_available_for_advance(self):
        for record in self:
            record.available_for_advance = record.amount_requested - record.total_advance_fees

    def action_request_advance(self):
        self.state = 'requested'

    def action_approve_advance(self):
        self.state = 'approved'

    def _create_advance_payment(self):
        # Create advance payment logic
        pass

    def _get_journal_for_payment(self, payment_method):
        # Get journal for payment logic
        pass

    def _get_payment_method_id(self, payment_method):
        # Get payment method ID logic
        pass

    def action_repay_advance(self):
        self.state = 'repaid'

    def _create_repayment_payment(self, amount):
        # Create repayment payment logic
        pass

    def _check_amount_requested(self):
        if self.amount_requested <= 0:
            raise ValidationError(_("The requested amount must be greater than zero."))

    def _check_unique_advance_per_deal(self):
        # Check unique advance per deal logic
        pass

    def unlink(self):
        if self.state not in ('draft', 'cancelled'):
            raise ValidationError(_("You cannot delete a record that is not in draft or cancelled state."))
        return super(CommissionAdvance, self).unlink()