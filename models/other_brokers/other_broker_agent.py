# models/other_brokers/other_broker_agent.py

"""
Module for managing Other Broker Agents, extending res.partner with additional agent information
and associations to other brokers and deals.
"""

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class OtherBrokerAgent(models.Model):
    """
    Model representing Other Broker Agents, inheriting from res.partner and associating with other brokers and deals.
    """
    _name = 'other.broker.agent'
    _description = 'Other Broker Agent'
    _inherits = {'res.partner': 'partner_id'}
    _inherit = ["mail.thread", "mail.activity.mixin", "notification.mixin", "shared.fields.mixin"]
    _rec_name = "partner_id"

    # =====================
    # Partner Information
    # =====================
    partner_id = fields.Many2one(
        'res.partner',
        string='Agent Contact',
        required=True,
        ondelete='cascade',
        domain=[('is_other_broker_agent', '=', True)],
        tracking=True
    )

    # =====================
    # Relational Fields
    # =====================
    other_broker_id = fields.Many2one(
        'other.broker',
        string='Other Broker',
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        required=True,
        ondelete="cascade",
        help="Reference to the associated deal.",
    )

    # =====================
    # Commission & Payment Information
    # =====================
    payable_to_other_broker = fields.Monetary(
        related="deal_id.payable_to_other_broker",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    other_broker_trust_balance = fields.Monetary(
        related="deal_id.other_broker_trust_balance",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    other_broker_trust_excess_held = fields.Monetary(
        related="deal_id.other_broker_trust_excess_held",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    amount_payable = fields.Monetary(
        related="deal_id.due_to_other_broker",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    amount_receivable = fields.Monetary(
        related="deal_id.due_from_other_broker",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    tax_on_commission = fields.Monetary(
        compute="_compute_tax_on_commission",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )

    # =====================
    # Broker-specific Fields
    # =====================
    end_id = fields.Many2one(
        "deal.end",
        string="End",
        required=True,
        tracking=True,
    )
    broker_type = fields.Selection(
        [
            ("ar", "A/R - Receivable from this Brokerage"),
            ("ap", "A/P - Payable to this Brokerage"),
            ("no", "No Payables or Receivables")
        ],
        compute="_compute_broker_type",
        store=True,
        tracking=True,
    )
    deposit_instructions_received = fields.Boolean(
        default=False,
        help="Indicates if the broker has provided banking information for Direct Deposits.",
        tracking=True,
    )

    # =====================
    # Additional Fields
    # =====================
    payment_method = fields.Selection(
        selection=[("cheque", "Cheque"), ("direct_deposit", "Direct Deposit")],
        related="partner_id.payment_method",
        store=True,
        tracking=True,
    )
    note = fields.Html(
        related="partner_id.comment",
        store=True,
        tracking=True,
    )

    # =====================
    # Compute Methods
    # =====================
    @api.depends("end_id.type", "payable_to_other_broker", "amount_receivable")
    def _compute_broker_type(self):
        """
        Compute the broker type based on payable and receivable amounts and the deal end type.
        """
        for rec in self:
            if rec.payable_to_other_broker > 0:
                rec.broker_type = "ap" if rec.end_id.type in ["seller", "landlord"] else "ar"
            elif rec.amount_receivable > 0:
                rec.broker_type = "ar" if rec.end_id.type in ["seller", "landlord"] else "ap"
            else:
                rec.broker_type = "no"

    @api.depends('payable_to_other_broker', 'amount_receivable')
    def _compute_tax_on_commission(self):
        """
        Compute the tax on commission based on payable or receivable amounts.
        """
        for rec in self:
            tax_amount = 0.0
            try:
                if rec.payable_to_other_broker > 0:
                    taxes = rec._get_applicable_taxes()
                    tax_result = taxes.compute_all(
                        rec.payable_to_other_broker,
                        rec.currency_id,
                        1,
                        partner=rec.partner_id
                    )
                    tax_amount = tax_result['total_included'] - tax_result['total_excluded']
                elif rec.amount_receivable > 0:
                    taxes = rec._get_applicable_taxes()
                    tax_result = taxes.compute_all(
                        rec.amount_receivable,
                        rec.currency_id,
                        1,
                        partner=rec.partner_id
                    )
                    tax_amount = tax_result['total_included'] - tax_result['total_excluded']
            except UserError as e:
                _logger.error(
                    "Tax computation failed for Other Broker Agent ID: %s - %s",
                    rec.id, e
                )
                rec.tax_on_commission = 0.0
                continue
            rec.tax_on_commission = tax_amount

    def _get_applicable_taxes(self):
        """
        Retrieve applicable taxes for the other broker agent based on the deal preferences.
        """
        self.ensure_one()
        deal_prefs = self.deal_id.deal_preferences_id
        if deal_prefs and deal_prefs.tax_ids:
            return deal_prefs.tax_ids
        else:
            # Fallback to company purchase taxes
            default_taxes = self.env['account.tax'].search([
                ('type_tax_use', '=', 'purchase'),
                ('company_id', '=', self.company_id.id),
                ('active', '=', True),
            ])
            if not default_taxes:
                raise UserError(_("No default purchase taxes defined for the company."))
            return default_taxes

    # =====================
    # Constraints
    # =====================
    @api.constrains("deal_id", "end_id")
    def _check_single_broker_per_deal_end(self):
        """
        Ensure that only one broker is associated with each deal and end combination.
        """
        for rec in self:
            existing_brokers = self.search_count([
                ("deal_id", "=", rec.deal_id.id),
                ("end_id", "=", rec.end_id.id),
                ("id", "!=", rec.id),
            ])
            if existing_brokers >= 1:
                raise ValidationError(
                    _("Only one other broker can be associated with each end (Buyer or Seller) of a deal at a time.")
                )

    @api.constrains("end_id.type")
    def _check_no_other_broker_for_double_end(self):
        """
        Prevent associating other brokers with double-ended deals.
        """
        for rec in self:
            if rec.end_id.type == 'double_end':
                existing_brokers = self.search_count([
                    ("deal_id", "=", rec.deal_id.id),
                    ("end_id.type", "=", rec.end_id.type),
                    ("id", "!=", rec.id),
                ])
                if existing_brokers >= 1:
                    raise ValidationError(_("No other brokers are allowed for double-ended deals."))

    @api.constrains('partner_id')
    def _check_duplicate_agent(self):
        """
        Ensure that an agent is not duplicated within the same brokerage.
        """
        for rec in self:
            if rec.partner_id:
                existing = self.search([
                    ('partner_id', '=', rec.partner_id.id),
                    ('other_broker_id', '=', rec.other_broker_id.id),
                    ('id', '!=', rec.id)
                ])
                if existing:
                    raise ValidationError(_(
                        'The agent "%s" is already associated with the brokerage "%s". '
                        'Please review existing entries before adding a new one.'
                    ) % (rec.partner_id.name, rec.other_broker_id.partner_id.name))

    # =====================
    # Overridden Methods
    # =====================
    @api.model
    def create(self, vals):
        """
        Override the create method to ensure the partner is marked as an other broker agent
        and associated with the correct brokerage.
        """
        res = super(OtherBrokerAgent, self).create(vals)
        # Update partner to be marked as an other broker agent
        res.partner_id.write({
            "is_company": False,
            "is_other_broker_agent": True,
            "parent_id": res.other_broker_id.partner_id.id,
        })
        _logger.debug(
            "Created Other Broker Agent with ID: %s linked to Partner ID: %s",
            res.id, res.partner_id.id
        )
        return res

    def write(self, vals):
        """
        Override the write method to update the partner's brokerage information when necessary.
        """
        res = super(OtherBrokerAgent, self).write(vals)
        if 'other_broker_id' in vals:
            self.partner_id.write({
                "parent_id": self.other_broker_id.partner_id.id,
            })
        if 'is_other_broker_agent' in vals:
            self.partner_id.write({
                "is_other_broker_agent": True,
            })
        _logger.debug(
            "Updated Other Broker Agent with ID: %s",
            self.id
        )
        return res

    # =====================
    # Name and Search Methods
    # =====================
    def name_get(self):
        """
        Override the name_get method to display the partner's name or a default label.
        """
        result = []
        for rec in self:
            name = rec.partner_id.name or "Other Broker Agent"
            result.append((rec.id, name))
        return result

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """
        Override the name_search method to allow searching by agent's name or parent broker's name.
        """
        args = args or []
        if name:
            # Search by agent name or parent broker name
            partner_ids = (
                self.env["res.partner"]
                .search([
                    "|",
                    ("name", operator, name),
                    ("parent_id.name", operator, name)
                ])
                .ids
            )
            args += [("partner_id", "in", partner_ids)]
        records = self.search(args, limit=limit)
        return records.name_get()

    # =====================
    # SQL Constraints
    # =====================
    _sql_constraints = [
        ('unique_agent_broker_deal',
         'UNIQUE(partner_id, other_broker_id, deal_id)',
         'Each agent can only be associated with a specific brokerage and deal once.')
    ]