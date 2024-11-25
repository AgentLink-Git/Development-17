# models/other_brokers/other_broker.py

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class OtherBroker(models.Model):
    _name = "other.broker"
    _description = "Other Brokers"
    _inherits = {"res.partner": "partner_id"}
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "notification.mixin",
        "shared.fields.mixin",
    ]
    _rec_name = "partner_id"

    # =====================
    # Partner Information
    # =====================
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        required=True,
        ondelete="cascade",
        domain=[("is_other_broker", "=", True)],
        tracking=True,
    )

    # =====================
    # Relational Fields
    # =====================
    other_broker_agent_ids = fields.One2many(
        "other.broker.agent",
        "other_broker_id",
        string="Agents",
        related="partner_id.agent_ids",
        tracking=True,
    )

    # =====================
    # Commission & Payment Information
    # =====================
    payable_to_other_broker = fields.Monetary(
        string="Payable to Other Broker",
        related="deal_id.payable_to_other_broker",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    other_broker_trust_balance = fields.Monetary(
        string="Other Broker Trust Balance",
        related="deal_id.other_broker_trust_balance",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    other_broker_trust_excess_held = fields.Monetary(
        string="Other Broker Trust Excess Held",
        related="deal_id.other_broker_trust_excess_held",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    amount_payable = fields.Monetary(
        string="Amount Payable",
        related="deal_id.due_to_other_broker",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    amount_receivable = fields.Monetary(
        string="Amount Receivable",
        related="deal_id.due_from_other_broker",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    tax_on_commission = fields.Monetary(
        string="Tax on Commission",
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
            ("no", "No Payables or Receivables"),
        ],
        string="Broker Type",
        compute="_compute_broker_type",
        store=True,
        tracking=True,
    )
    deposit_instructions_received = fields.Boolean(
        string="Deposit Instructions Received",
        default=False,
        help="Indicates if the broker has provided banking information for Direct Deposits.",
        tracking=True,
    )

    # =====================
    # Additional Fields
    # =====================
    payment_method = fields.Selection(
        selection=[("cheque", "Cheque"), ("direct_deposit", "Direct Deposit")],
        string="Payment Method",
        related="partner_id.payment_method",
        store=True,
        tracking=True,
    )
    note = fields.Html(
        string="Notes",
        related="partner_id.comment",
        store=True,
        tracking=True,
    )

    # =====================
    # Compute Methods
    # =====================
    @api.depends("end_id.type", "payable_to_other_broker", "amount_receivable")
    def _compute_broker_type(self):
        for rec in self:
            if rec.payable_to_other_broker > 0:
                rec.broker_type = (
                    "ap" if rec.end_id.type in ["seller", "landlord"] else "ar"
                )
            elif rec.amount_receivable > 0:
                rec.broker_type = (
                    "ar" if rec.end_id.type in ["seller", "landlord"] else "ap"
                )
            else:
                rec.broker_type = "no"

    @api.depends("payable_to_other_broker", "amount_receivable")
    def _compute_tax_on_commission(self):
        for rec in self:
            tax_amount = 0.0
            try:
                if rec.payable_to_other_broker > 0:
                    taxes = rec._get_applicable_taxes()
                    tax_result = taxes.compute_all(
                        rec.payable_to_other_broker,
                        rec.currency_id,
                        1,
                        partner=rec.partner_id,
                    )
                    tax_amount = (
                        tax_result["total_included"] - tax_result["total_excluded"]
                    )
                elif rec.amount_receivable > 0:
                    taxes = rec._get_applicable_taxes()
                    tax_result = taxes.compute_all(
                        rec.amount_receivable,
                        rec.currency_id,
                        1,
                        partner=rec.partner_id,
                    )
                    tax_amount = (
                        tax_result["total_included"] - tax_result["total_excluded"]
                    )
            except UserError as e:
                _logger.error(
                    "Tax computation failed for Other Broker ID: %s - %s", rec.id, e
                )
                rec.tax_on_commission = 0.0
                continue
            rec.tax_on_commission = tax_amount

    def _get_applicable_taxes(self):
        """
        Retrieve applicable taxes for the other broker based on the deal preferences.
        """
        self.ensure_one()
        deal_prefs = self.deal_id.deal_preferences_id
        if deal_prefs and deal_prefs.tax_ids:
            return deal_prefs.tax_ids
        else:
            # Fallback to company purchase taxes
            default_taxes = self.env["account.tax"].search(
                [
                    ("type_tax_use", "=", "purchase"),
                    ("company_id", "=", self.company_id.id),
                    ("active", "=", True),
                ]
            )
            if not default_taxes:
                raise UserError(_("No default purchase taxes defined for the company."))
            return default_taxes

    # =====================
    # Constraints
    # =====================
    @api.constrains("deal_id", "end_id")
    def _check_single_broker_per_deal_end(self):
        for rec in self:
            existing_brokers = self.search_count(
                [
                    ("deal_id", "=", rec.deal_id.id),
                    ("end_id", "=", rec.end_id.id),
                    ("id", "!=", rec.id),
                ]
            )
            if existing_brokers >= 1:
                raise ValidationError(
                    _(
                        "Only one other broker can be associated with each end (Buyer or Seller) of a deal at a time."
                    )
                )

    @api.constrains("end_id.type")
    def _check_no_other_broker_for_double_end(self):
        for rec in self:
            if rec.end_id.type == "double_end":
                existing_brokers = self.search_count(
                    [
                        ("deal_id", "=", rec.deal_id.id),
                        ("end_id.type", "=", rec.end_id.type),
                        ("id", "!=", rec.id),
                    ]
                )
                if existing_brokers >= 1:
                    raise ValidationError(
                        _("No other brokers are allowed for double-ended deals.")
                    )

    # =====================
    # Overridden Methods
    # =====================
    @api.model
    def create(self, vals):
        res = super(OtherBroker, self).create(vals)
        # Ensure the partner is marked as an other broker and associated with the correct company
        res.partner_id.write(
            {
                "is_company": True,
                "is_other_broker": True,
                "company_id": res.company_id.id,
            }
        )
        _logger.info(
            "Created Other Broker with ID: %s linked to Partner ID: %s",
            res.id,
            res.partner_id.id,
        )
        return res

    def write(self, vals):
        res = super(OtherBroker, self).write(vals)
        if "is_other_broker" in vals or "company_id" in vals:
            self.partner_id.write(
                {
                    "is_company": True,
                    "is_other_broker": True,
                    "company_id": self.company_id.id,
                }
            )
            _logger.info(
                "Updated Other Broker's Partner ID: %s with new values.",
                self.partner_id.id,
            )
        return res

    # =====================
    # Name and Search Methods
    # =====================
    def name_get(self):
        result = []
        for rec in self:
            name = rec.partner_id.name or "Other Broker"
            result.append((rec.id, name))
        return result

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = args or []
        if name:
            broker_ids = self.search(
                [
                    ("partner_id.name", operator, name),
                    ("partner_id.is_other_broker", "=", True),
                ]
            ).ids
            args += [("id", "in", broker_ids)]
        records = self.search(args, limit=limit)
        return records.name_get()
