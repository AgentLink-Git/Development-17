# models/financial/account_payment.py

"""
Module for extending Account Payment models for Deal Integration.
Defines AccountPaymentExtension and AccountPaymentRegisterExtension models
to incorporate additional fields and functionalities related to deals,
commissions, and financial operations. Ensures proper linkage between
payments and deals, along with comprehensive tracking and validation mechanisms.
"""

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountPaymentExtension(models.Model):
    _inherit = "account.payment"
    _description = "Extended Account Payment for Deal Integration"

    # =====================
    # Fields
    # =====================
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        help="Reference to the associated deal.",
        ondelete="cascade",
        index=True,
    )
    is_commission_payment = fields.Boolean(
        string="Is Commission Payment",
        default=False,
        help="Indicates whether this payment is related to a commission.",
    )
    sequence_number = fields.Char(
        string="Sequence Number",
        help="Sequence number for the payment.",
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
        help="Method of payment used for the transaction.",
    )
    type_of_payment = fields.Selection(
        [
            ('payment', 'Payment'),
            ('receipt', 'Receipt'),
        ],
        string="Type of Payment",
        required=True,
        default='payment',
    )
    bank_journal_id = fields.Many2one(
        'account.journal',
        string='Bank Journal',
        help="Bank journal associated with this payment.",
    )
    transaction_type = fields.Selection(
        [
            ("trust_receipt", "Trust Receipt"),
            ("trust_refund", "Trust Refund"),
            ("trust_excess_payment", "Trust Excess Payment"),
            ("commission_payment", "Commission Payment"),
            ("commission_receipt", "Commission Receipt"),
            ("transfer", "Transfer"),
        ],
        string="Transaction Type",
        help="Type of financial transaction.",
    )
    transaction_line_ids = fields.Many2many(
        'transaction.line',
        'transaction_line_account_payment_rel',
        'account_payment_id',
        'transaction_line_id',
        string='Transaction Lines',
    )

    # =====================
    # Override Methods
    # =====================
    @api.model
    def create(self, vals):
        """
        Override create to associate payment with deal if provided.
        Ensures that the payment adheres to financial rules.
        """
        deal_id = vals.get('deal_id')
        if deal_id:
            deal = self.env['deal.records'].browse(deal_id)
            if deal.exists():
                _logger.debug("Associating payment with Deal ID: %s", deal.id)
                # Validate deal's financial state before creating payment
                if deal.stage_id.name != 'Closed':
                    raise UserError(_("Payments can only be made for deals that are closed."))
        payment = super(AccountPaymentExtension, self).create(vals)
        _logger.info(
            "Created Payment ID: %s for Deal ID: %s",
            payment.id,
            payment.deal_id.id if payment.deal_id else 'N/A'
        )
        return payment

    def write(self, vals):
        """
        Override write to handle updates related to deal association.
        Ensures that any changes comply with financial rules.
        """
        deal_id = vals.get('deal_id')
        if deal_id:
            deal = self.env['deal.records'].browse(deal_id)
            if deal.exists():
                _logger.debug("Updating payment association to Deal ID: %s", deal.id)
                if deal.stage_id.name != 'Closed':
                    raise UserError(_("Payments can only be associated with deals that are closed."))
        result = super(AccountPaymentExtension, self).write(vals)
        _logger.info(
            "Updated Payment IDs: %s with vals: %s",
            self.ids,
            vals
        )
        return result

    def action_post(self):
        """
        Override action_post to perform additional operations upon posting a payment.
        This includes updating deal records and triggering financial operations.
        """
        res = super(AccountPaymentExtension, self).action_post()
        for payment in self:
            if payment.deal_id:
                _logger.debug(
                    "Processing post operations for Payment ID: %s associated with Deal ID: %s",
                    payment.id,
                    payment.deal_id.id,
                )
                # Update deal's funds received
                if hasattr(payment.deal_id, 'update_funds_received'):
                    payment.deal_id.update_funds_received(payment.amount)
                else:
                    _logger.warning(
                        "Method 'update_funds_received' not found on Deal ID: %s",
                        payment.deal_id.id,
                    )
                # Reconcile payment with deal's financial records
                if hasattr(payment.deal_id, 'reconcile_payment'):
                    payment.deal_id.reconcile_payment(payment)
                else:
                    _logger.warning(
                        "Method 'reconcile_payment' not found on Deal ID: %s",
                        payment.deal_id.id,
                    )
        return res


class AccountPaymentRegisterExtension(models.TransientModel):
    _inherit = "account.payment.register"
    _description = "Extended Account Payment Register for Deal Integration"

    # =====================
    # Override Methods
    # =====================
    def _create_payments(self):
        """
        Override to include deal_id in payment creation if applicable.
        """
        payments = super(AccountPaymentRegisterExtension, self)._create_payments()
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        if active_model == 'deal.records' and active_id:
            deal = self.env['deal.records'].browse(active_id)
            if deal.exists():
                if deal.stage_id.name != 'Closed':
                    raise UserError(_("Payments can only be registered for deals that are closed."))
                payments.write({'deal_id': deal.id})
                _logger.debug("Associated Payments with Deal ID: %s", deal.id)
        return payments