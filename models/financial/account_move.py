# models/financial/account_move.py

"""
Module for extending Account Move and Account Move Line models for Deal Integration.
Defines AccountMoveExtension and AccountMoveLineExtension models to incorporate additional
fields and functionalities related to deals, commissions, refunds, and financial computations.
Ensures proper linkage between financial transactions and deals, along with comprehensive
tracking and validation mechanisms.
"""

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountMoveExtension(models.Model):
    _inherit = "account.move"
    _description = "Extended Account Move for Deal Integration"

    transaction_line_id = fields.Many2one(
        'transaction.line',
        string='Transaction Line',
        help='Transaction line associated with this journal entry.',
    )
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        help="Reference to the associated deal.",
        ondelete="cascade",
        index=True,
    )

    # Refund Information
    is_refunded = fields.Boolean(
        string="Is Refunded",
        default=False,
        help="Indicates whether the transaction has been refunded.",
    )
    refund_invoice_id = fields.Many2one(
        "account.move",
        string="Refund Invoice",
        help="Reference to the refund invoice.",
    )

    # Buyer and Seller Information
    buyer = fields.Char(
        string="Buyer",
        help="Name of the buyer involved in the transaction.",
    )
    seller = fields.Char(
        string="Seller",
        help="Name of the seller involved in the transaction.",
    )

    # Financial Fields
    total_tax = fields.Monetary(
        string="Total Tax",
        currency_field="currency_id",
        help="Total tax amount for the transaction.",
    )
    total_commission = fields.Monetary(
        string="Total Commission",
        currency_field="currency_id",
        help="Total commission amount for the transaction.",
    )
    payable_amount = fields.Monetary(
        string="Payable Amount",
        currency_field="currency_id",
    )
    payable_id = fields.Many2one(
        "property.payable",
        string="Payable",
    )

    # Invoices and Bank Information
    original_invoice_id = fields.Many2one(
        "account.move",
        string="Original Invoice",
        help="Reference to the original invoice for the deposit.",
    )
    partner_bank_id = fields.Many2one(
        "res.partner.bank",
        string="Bank Account",
        help="Bank account of the partner.",
    )

    # Related Lines
    other_brokers_ids = fields.One2many(
        "other.broker",
        "deal_id",
        string="Other Brokers",
        help="Other brokers associated with this account move.",
    )
    law_firms_ids = fields.One2many(
        "law.firm",
        "deal_id",
        string="Law Firms",
        help="Law firms associated with this account move.",
    )
    buyers_sellers_ids = fields.One2many(
        "buyers.sellers",
        "deal_id",
        string="Buyers & Sellers",
        help="Buyers and Sellers associated with this account move.",
    )
    sales_agents_and_referrals_ids = fields.One2many(
        "sales.agents.and.referrals",
        "deal_id",
        string="Sales Agents & Referrals",
        help="Sales Agents & Referrals associated with this account move.",
    )
    commission_received_ids = fields.One2many(
        comodel_name="account.payment",
        inverse_name="deal_id",
        string="Commission Received",
        domain=[("is_commission_payment", "=", True), ("state", "=", "posted")],
        help="Commission payments received related to this deal.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to add custom logic if necessary."""
        records = super(AccountMoveExtension, self).create(vals_list)
        _logger.debug("Created Account Move with IDs: %s", records.ids)
        return records

    def write(self, vals):
        """Override write to add custom logic if necessary."""
        result = super(AccountMoveExtension, self).write(vals)
        _logger.debug("Updated Account Move IDs: %s", self.ids)
        return result


class AccountMoveLineExtension(models.Model):
    _inherit = "account.move.line"
    _description = "Extended Account Move Line for Deal Integration"

    # Conveyance Information
    is_conveyable = fields.Boolean(
        string="Is Conveyable?",
        default=False,
        help="Indicates if the move line is conveyable.",
    )
    conveyance_date = fields.Date(
        string="Conveyance Date",
        help="Date when the conveyance occurs.",
    )

    # Deal and Transaction Relationships
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        help="Reference to the associated deal.",
    )

    # Refund Information
    is_refunded = fields.Boolean(
        string="Is Refunded",
        default=False,
        help="Indicates whether the move line has been refunded.",
    )
    refund_invoice_id = fields.Many2one(
        "account.move",
        string="Refund Invoice",
        help="Reference to the refund invoice.",
    )

    # Buyer and Seller Information
    buyer = fields.Char(
        string="Buyer",
        help="Name of the buyer involved in the transaction.",
    )
    seller = fields.Char(
        string="Seller",
        help="Name of the seller involved in the transaction.",
    )

    # Financial Fields
    total_tax = fields.Monetary(
        string="Total Tax",
        currency_field="currency_id",
        help="Total tax amount for the transaction.",
    )
    total_commission = fields.Monetary(
        string="Total Commission",
        currency_field="currency_id",
        help="Total commission amount for the transaction.",
    )
    payable_amount = fields.Monetary(
        string="Payable Amount",
        currency_field="currency_id",
    )
    payable_id = fields.Many2one(
        "property.payable",
        string="Payable",
    )
    liability_amount = fields.Monetary(
        string="Liability Amount",
        compute="_compute_amounts",
        store=True,
        currency_field="currency_id",
        help="Calculated liability amount based on account.",
    )
    bank_amount = fields.Monetary(
        string="Bank Amount",
        compute="_compute_amounts",
        store=True,
        currency_field="currency_id",
        help="Calculated bank amount based on account.",
    )

    # Related Invoices and Bank Information
    original_invoice_id = fields.Many2one(
        "account.move",
        string="Original Invoice",
        help="Reference to the original invoice for the deposit.",
    )
    partner_bank_id = fields.Many2one(
        "res.partner.bank",
        string="Bank Account",
        help="Bank account of the partner.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'deal_id' not in vals:
                move_id = vals.get('move_id')
                if move_id:
                    move = self.env['account.move'].browse(move_id)
                    vals['deal_id'] = move.deal_id.id if move.deal_id else False
        return super(AccountMoveLineExtension, self).create(vals_list)

    def write(self, vals):
        res = super(AccountMoveLineExtension, self).write(vals)
        if 'move_id' in vals or 'deal_id' in vals:
            for line in self:
                if line.deal_id != line.move_id.deal_id:
                    line.deal_id = line.move_id.deal_id
        return res

    @api.constrains('deal_id', 'move_id')
    def _check_deal_consistency(self):
        for line in self:
            if line.deal_id != line.move_id.deal_id:
                raise ValidationError(_("The deal on the move line must match the deal on the move."))

    @api.depends("debit", "credit", "account_id", "move_id.date", "deal_id")
    def _compute_amounts(self):
        """Compute liability and bank amounts based on account types."""
        deal_preferences = self.env["deal.preferences"].search([], limit=1)
        if not deal_preferences:
            for line in self:
                line.liability_amount = 0.0
                line.bank_amount = 0.0
            _logger.warning(
                "Deal Preferences not set. Liability and Bank amounts set to 0."
            )
            return

        trust_liability_account = deal_preferences.trust_liability_account
        trust_bank_journal = deal_preferences.trust_bank_account
        trust_bank_account_id = (
            trust_bank_journal.default_account_id.id if trust_bank_journal else False
        )

        for line in self:
            liability = 0.0
            bank = 0.0

            if line.deal_id:
                if line.account_id == trust_liability_account:
                    liability = line.credit - line.debit
                elif (
                    trust_bank_account_id
                    and line.account_id.id == trust_bank_account_id
                ):
                    bank = line.debit - line.credit

            line.liability_amount = liability
            line.bank_amount = bank
            _logger.debug(
                "Computed amounts for line ID %s: Liability=%s, Bank=%s",
                line.id,
                liability,
                bank,
            )

    def _update_related_records(self):
        """Placeholder for any additional logic to update related records."""
        for record in self:
            pass

    @api.constrains("deal_id")
    def _check_deal_association(self):
        """Ensure that the move line is associated with a valid deal."""
        for record in self:
            if record.deal_id and not record.move_id.deal_id:
                raise ValidationError(
                    _("The move line's deal must match the move's deal.")
                )

    def action_view_liabilities(self):
        """Action to view liabilities related to this move line."""
        self.ensure_one()
        liabilities = self.env["property.payable"].search([
            ("account_move_line_id", "=", self.id)
        ])
        if not liabilities:
            raise UserError(_("No liabilities found for this move line."))

        return {
            "type": "ir.actions.act_window",
            "name": "Liabilities",
            "view_mode": "tree,form",
            "res_model": "property.payable",
            "domain": [("id", "in", liabilities.ids)],
            "context": {"default_account_move_line_id": self.id},
            "target": "current",
        }

    def action_view_banks(self):
        """Action to view bank accounts related to this move line."""
        self.ensure_one()
        banks = self.env["res.partner.bank"].search([
            ("id", "=", self.partner_bank_id.id)
        ])
        if not banks:
            raise UserError(_("No bank accounts found for this move line."))

        return {
            "type": "ir.actions.act_window",
            "name": "Bank Accounts",
            "view_mode": "tree,form",
            "res_model": "res.partner.bank",
            "domain": [("id", "in", banks.ids)],
            "context": {"default_partner_id": self.partner_id.id},
            "target": "current",
        }