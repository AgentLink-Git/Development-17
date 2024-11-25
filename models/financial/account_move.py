# models/financials/account_move.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class AccountMoveExtension(models.Model):
    _inherit = "account.move"
    _description = "Extended Account Move for Deal Integration"

    # =====================
    # Fields
    # =====================

    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        help="Reference to the associated deal.",
        tracking=True,
    )
    is_refunded = fields.Boolean(
        string="Is Refunded",
        default=False,
        help="Indicates whether the transaction has been refunded.",
        tracking=True,
    )
    transaction_line_id = fields.Many2one(
        "transaction.line",
        string="Transaction Line",
        help="Reference to the related transaction line.",
        tracking=True,
    )
    buyer = fields.Char(
        string="Buyer",
        help="Name of the buyer involved in the transaction.",
        tracking=True,
    )
    seller = fields.Char(
        string="Seller",
        help="Name of the seller involved in the transaction.",
        tracking=True,
    )
    total_tax = fields.Monetary(
        string="Total Tax",
        currency_field="currency_id",
        help="Total tax amount for the transaction.",
        tracking=True,
    )
    total_commission = fields.Monetary(
        string="Total Commission",
        currency_field="currency_id",
        help="Total commission amount for the transaction.",
        tracking=True,
    )
    original_invoice_id = fields.Many2one(
        "account.move",
        string="Original Invoice",
        help="Reference to the original invoice for the deposit.",
        tracking=True,
    )
    refund_invoice_id = fields.Many2one(
        "account.move",
        string="Refund Invoice",
        help="Reference to the refund invoice.",
        tracking=True,
    )
    partner_bank_id = fields.Many2one(
        "res.partner.bank",
        string="Bank Account",
        help="Bank account of the partner.",
        tracking=True,
    )
    payable_amount = fields.Monetary(
        string="Payable Amount", currency_field="currency_id", tracking=True
    )
    payable_id = fields.Many2one(
        "property.payable",
        string="Payable",
        tracking=True,
    )
    commission_received_ids = fields.One2many(
        comodel_name="account.payment",
        inverse_name="deal_id",
        string="Commission Received",
        domain=[("is_commission_payment", "=", True), ("state", "=", "posted")],
    )

    # =====================
    # Methods
    # =====================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to add custom logic if necessary."""
        records = super(AccountMoveExtension, self).create(vals_list)
        # Add additional logic here if required
        _logger.debug("Created Account Move with IDs: %s", records.ids)
        return records

    def write(self, vals):
        """Override write to add custom logic if necessary."""
        result = super(AccountMoveExtension, self).write(vals)
        # Add additional logic here if required
        _logger.debug("Updated Account Move IDs: %s", self.ids)
        return result


class AccountMoveLineExtension(models.Model):
    _inherit = "account.move.line"
    _description = "Extended Account Move Line for Deal Integration"

    # =====================
    # Fields
    # =====================
    date = fields.Date(
        string="Date",
        related="move_id.date",
        store=True,
        help="Date of the move.",
        tracking=True,
    )
    is_refunded = fields.Boolean(string="Is Refunded", default=False, tracking=True)

    buyer = fields.Char(string="Buyer", tracking=True)
    seller = fields.Char(string="Seller", tracking=True)
    total_tax = fields.Monetary(
        string="Total Tax", currency_field="currency_id", tracking=True
    )
    total_commission = fields.Monetary(
        string="Total Commission", currency_field="currency_id", tracking=True
    )
    original_invoice_id = fields.Many2one(
        "account.move",
        string="Original Invoice",
        help="Reference to the original invoice for the deposit.",
        tracking=True,
    )
    refund_invoice_id = fields.Many2one(
        "account.move",
        string="Refund Invoice",
        help="Reference to the refund invoice.",
        tracking=True,
    )
    partner_bank_id = fields.Many2one(
        "res.partner.bank", string="Bank Account", tracking=True
    )
    payable_amount = fields.Monetary(
        string="Payable Amount", currency_field="currency_id", tracking=True
    )
    payable_id = fields.Many2one("property.payable", string="Payable", tracking=True)
    liability_amount = fields.Monetary(
        string="Liability Amount",
        compute="_compute_amounts",
        store=True,
        currency_field="currency_id",
        help="Calculated liability amount based on account.",
        tracking=True,
    )
    bank_amount = fields.Monetary(
        string="Bank Amount",
        compute="_compute_amounts",
        store=True,
        currency_field="currency_id",
        help="Calculated bank amount based on account.",
        tracking=True,
    )

    # =====================
    # Compute Methods
    # =====================

    @api.depends("debit", "credit", "account_id", "move_id.date", "deal_id")
    def _compute_amounts(self):
        """Compute liability and bank amounts based on account types."""
        for line in self:
            deal_preferences = self.env["deal.preferences"].search(
                [("company_id", "=", line.company_id.id)], limit=1
            )
            if not deal_preferences:
                line.liability_amount = 0.0
                line.bank_amount = 0.0
                _logger.warning(
                    "Deal Preferences not set for company %s. Liability and Bank amounts set to 0.",
                    line.company_id.name,
                )
                continue

            trust_liability_account = deal_preferences.trust_liability_account
            trust_bank_journal = deal_preferences.trust_bank_account
            trust_bank_account_id = (
                trust_bank_journal.default_account_id.id
                if trust_bank_journal
                else False
            )

            liability = 0.0
            bank = 0.0

            if line.account_id == trust_liability_account:
                liability = line.credit - line.debit
            elif trust_bank_account_id and line.account_id.id == trust_bank_account_id:
                bank = line.debit - line.credit

            line.liability_amount = liability
            line.bank_amount = bank
            _logger.debug(
                "Computed amounts for line ID %s: Liability=%s, Bank=%s",
                line.id,
                liability,
                bank,
            )

    # =====================
    # Methods
    # =====================

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to add custom logic if necessary."""
        records = super(AccountMoveLineExtension, self).create(vals_list)
        # Add additional logic here if required
        _logger.debug("Created Account Move Line with IDs: %s", records.ids)
        return records

    def write(self, vals):
        """Override write to add custom logic if necessary."""
        result = super(AccountMoveLineExtension, self).write(vals)
        # Add additional logic here if required
        _logger.debug("Updated Account Move Line IDs: %s", self.ids)
        return result
