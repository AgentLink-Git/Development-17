# models/sales_agents/sales_agents_and_referrals.py

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class SalesAgentsAndReferrals(models.Model):
    _name = "sales.agents.and.referrals"
    _description = "Sales Agents and Referrals"
    _inherit = ["mail.thread", "mail.activity.mixin", "shared.fields.mixin"]
    _rec_name = "partner_id"

    # =====================
    # Partner and Company Information
    # =====================
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        required=True,
        ondelete="cascade",
        auto_join=True,
        tracking=True,
    )

    # =====================
    # Deal and Listing Relationships
    # =====================

    listing_id = fields.Many2one(
        "listing.records",
        string="Listing",
        domain=[("status", "not in", ["sold", "cancelled"])],
        ondelete="cascade",
        tracking=True,
    )
    end_id = fields.Many2one(
        "deal.end",
        string="End",
        required=True,
        ondelete="cascade",
        tracking=True,
    )

    # =====================
    # Payment Type and Related Fields
    # =====================
    payment_type = fields.Selection(
        [
            ("sales_agent", "Sales Agent Commission"),
            ("other_broker", "Referral to a Real Estate Brokerage"),
            ("non_licensee", "Referral to a Non-Licensee"),
        ],
        string="Payment Type",
        default="sales_agent",
        required=True,
        tracking=True,
    )
    sales_agent_id = fields.Many2one(
        "res.partner",
        string="Sales Agent",
        domain=[("is_sales_agent", "=", True)],
        tracking=True,
    )
    other_broker_id = fields.Many2one(
        "res.partner",
        string="Other Brokerage",
        domain=[("is_other_broker", "=", True)],
        tracking=True,
    )
    other_broker_agent_id = fields.Many2one(
        "res.partner",
        string="Other Broker Agent",
        domain=[("is_other_broker_agent", "=", True)],
        tracking=True,
    )
    buyers_sellers_id = fields.Many2one(
        "res.partner",
        string="Contact",
        domain=[("is_buyer_seller", "=", True)],
        tracking=True,
    )
    for_sale_or_lease = fields.Selection(
        [("for_sale", "For Sale"), ("for_lease", "For Lease")],
        string="For Sale/Lease",
        tracking=True,
    )
    referral_letter_on_file = fields.Boolean(
        string="Referral Letter on File",
        default=False,
        tracking=True,
    )

    # =====================
    # Contact Information Fields (for updating res.partner)
    # =====================
    street = fields.Char(related="partner_id.street", string="Street", store=True)
    street2 = fields.Char(related="partner_id.street2", string="Street2", store=True)
    city = fields.Char(related="partner_id.city", string="City", store=True)
    state_id = fields.Many2one(
        "res.country.state", related="partner_id.state_id", string="State", store=True
    )
    zip = fields.Char(related="partner_id.zip", string="Zip", store=True)
    country_id = fields.Many2one(
        "res.country", related="partner_id.country_id", string="Country", store=True
    )
    phone = fields.Char(related="partner_id.phone", string="Phone", store=True)
    email = fields.Char(related="partner_id.email", string="Email", store=True)
    website = fields.Char(related="partner_id.website", string="Website", store=True)
    vat = fields.Char(related="partner_id.vat", string="Tax ID", store=True)
    sales_agent_note = fields.Html(
        related="partner_id.comment",
        string="Sales Agent Notes",
        store=True,
        tracking=True,
    )

    # =====================
    # Commission and Fees
    # =====================
    base_commission = fields.Monetary(
        string="Base Commission",
        compute="_compute_base_commission",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    buyer_side_commission = fields.Monetary(
        string="Buyer Side Commission",
        compute="_compute_buyer_side_commission",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    seller_side_commission = fields.Monetary(
        string="Seller Side Commission",
        compute="_compute_seller_side_commission",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    percentage_of_end = fields.Float(
        string="% of End",
        default=100.0,
        required=True,
        tracking=True,
    )
    plus_flat_fee = fields.Monetary(
        string="+ Flat Fee",
        currency_field="currency_id",
        tracking=True,
    )
    less_flat_fee = fields.Monetary(
        string="- Flat Fee",
        currency_field="currency_id",
        tracking=True,
    )
    commission_plan_less_flat = fields.Monetary(
        string="- Flat Fee (Commission Plan)",
        currency_field="currency_id",
        tracking=True,
    )
    double_end_side = fields.Selection(
        [
            ("buyer", "Buyer"),
            ("seller", "Seller"),
            ("landlord", "Landlord"),
            ("tenant", "Tenant"),
        ],
        string="Double End Side",
        tracking=True,
    )

    # =====================
    # Financial Computations
    # =====================
    gross_amount = fields.Monetary(
        string="Gross Amount",
        compute="_compute_gross_amount",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    total_split_fees = fields.Monetary(
        string="Total Splits & Fees",
        compute="_compute_total_split_fees",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    total_net_amount = fields.Monetary(
        string="Total Net",
        compute="_compute_total_net_amount",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )

    # =====================
    # Commission Plan Fields
    # =====================
    commission_plan_ids = fields.Many2many(
        "commission.plan",
        string="Commission Plans",
        compute="_compute_commission_plans",
        store=True,
    )
    commission_plan_line_ids = fields.One2many(
        "deal.commission.plan.line",
        "sales_agent_line_id",
        string="Commission Plan Lines",
        help="Commission Plan Lines for this Sales Agent in the Deal.",
    )

    # =====================
    # Tax Fields
    # =====================
    tax_ids = fields.Many2many(
        "account.tax",
        string="Taxes",
        compute="_compute_tax_ids",
        store=True,
    )
    tax = fields.Monetary(
        string="Tax",
        compute="_compute_tax",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    total_tax = fields.Float(
        string="Total Tax Rate",
        compute="_compute_total_tax",
        store=True,
        tracking=True,
    )

    # =====================
    # Financial Balances
    # =====================
    due_to_contact = fields.Monetary(
        string="Due to Contact",
        currency_field="currency_id",
        compute="_compute_due_amounts",
        store=True,
    )
    due_from_contact = fields.Monetary(
        string="Due from Contact",
        currency_field="currency_id",
        compute="_compute_due_amounts",
        store=True,
    )
    payable_amount = fields.Monetary(
        string="Payable",
        compute="_compute_payable_amount",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    payable_type = fields.Selection(
        [
            ("ar", "A/R - Receivable from this Contact"),
            ("ap", "A/P - Payable to this Contact"),
            ("no", "No Payables or Receivables"),
        ],
        string="Payable/Receivable Type",
        compute="_compute_payable_type",
        store=True,
        tracking=True,
    )

    # =====================
    # Advance Fields (Applicable only to Sales Agents)
    # =====================
    amount_advanced = fields.Monetary(
        string="Amount Advanced",
        currency_field="currency_id",
        tracking=True,
    )
    advance_amt_repaid = fields.Monetary(
        string="Advance Repaid",
        currency_field="currency_id",
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
        tracking=True,
    )
    amount_requested = fields.Monetary(
        string="Amount Requested",
        currency_field="currency_id",
        tracking=True,
    )
    advance_approved = fields.Boolean(
        string="Advance Approved",
        default=False,
        tracking=True,
    )

    # =====================
    # Mentorship
    # =====================
    mentorship_line_ids = fields.One2many(
        "sales.agent.mentorship.line",
        "sales_agent_line_id",
        string="Mentorship Lines",
    )

    # =====================
    # Notes and Additional Information
    # =====================
    sales_agent_note = fields.Html(
        string="Sales Agent Notes",
        related="partner_id.comment",
        store=True,
        tracking=True,
    )

    # =====================
    # Computed Methods
    # =====================
    @api.depends(
        "deal_id.buyer_side_total",
        "deal_id.seller_side_total",
        "end_id.type",
        "double_end_side",
    )
    def _compute_base_commission(self):
        for rec in self:
            if rec.end_id.type in ["buyer", "tenant"]:
                rec.base_commission = rec.deal_id.buyer_side_total or 0.0
            elif rec.end_id.type in ["seller", "landlord"]:
                rec.base_commission = rec.deal_id.seller_side_total or 0.0
            elif rec.end_id.type == "double_end":
                if rec.double_end_side in ["buyer", "tenant"]:
                    rec.base_commission = rec.deal_id.buyer_side_total or 0.0
                elif rec.double_end_side in ["seller", "landlord"]:
                    rec.base_commission = rec.deal_id.seller_side_total or 0.0
                else:
                    rec.base_commission = 0.0
            else:
                rec.base_commission = 0.0

    @api.depends("deal_id.buyer_side_total")
    def _compute_buyer_side_commission(self):
        for rec in self:
            rec.buyer_side_commission = rec.deal_id.buyer_side_total or 0.0

    @api.depends("deal_id.seller_side_total")
    def _compute_seller_side_commission(self):
        for rec in self:
            rec.seller_side_commission = rec.deal_id.seller_side_total or 0.0

    @api.depends(
        "base_commission", "percentage_of_end", "plus_flat_fee", "less_flat_fee"
    )
    def _compute_gross_amount(self):
        for rec in self:
            rec.gross_amount = (
                (rec.base_commission * rec.percentage_of_end / 100.0)
                + rec.plus_flat_fee
                - rec.less_flat_fee
            )

    @api.depends("commission_plan_line_ids.split_fees")
    def _compute_total_split_fees(self):
        for rec in self:
            rec.total_split_fees = sum(
                rec.commission_plan_line_ids.mapped("split_fees")
            )

    @api.depends("gross_amount", "total_split_fees")
    def _compute_total_net_amount(self):
        for rec in self:
            rec.total_net_amount = rec.gross_amount - rec.total_split_fees

    @api.depends(
        "payment_type", "sales_agent_id", "sales_agent_id.vat", "other_broker_id"
    )
    def _compute_tax_ids(self):
        for rec in self:
            rec.tax_ids = False  # Default to no taxes
            if rec.payment_type == "sales_agent":
                if rec.sales_agent_id and rec.sales_agent_id.vat:
                    rec.tax_ids = rec._get_default_taxes()
            elif rec.payment_type == "other_broker":
                rec.tax_ids = rec._get_default_taxes()
            # Non-licensees do not have taxes in this context

    def _get_default_taxes(self):
        """
        Helper method to retrieve default taxes from deal preferences or other configuration.
        """
        deal_preferences = self.env["deal.preference"].search([], limit=1)
        if deal_preferences and deal_preferences.tax_ids:
            return deal_preferences.tax_ids
        else:
            # Fallback to default taxes if deal preferences are not set
            return self.env["account.tax"].search(
                [("type_tax_use", "=", "purchase")], limit=1
            )

    @api.depends("total_net_amount", "tax_ids")
    def _compute_tax(self):
        for rec in self:
            tax_total = 0.0
            if rec.tax_ids and rec.total_net_amount:
                # Compute taxes using the tax_ids
                taxes = rec.tax_ids.compute_all(rec.total_net_amount)
                tax_total = taxes["total_included"] - taxes["total_excluded"]
            rec.tax = tax_total

    @api.depends("tax_ids")
    def _compute_total_tax(self):
        for rec in self:
            rec.total_tax = sum(tax.amount for tax in rec.tax_ids)

    @api.depends("total_net_amount", "tax")
    def _compute_payable_amount(self):
        for rec in self:
            rec.payable_amount = rec.total_net_amount + rec.tax

    @api.depends("payable_amount", "end_id.type")
    def _compute_payable_type(self):
        for rec in self:
            if rec.end_id.type in ["seller", "landlord"]:
                if rec.payable_amount > 0:
                    rec.payable_type = "ap"
                elif rec.payable_amount < 0:
                    rec.payable_type = "ar"
                else:
                    rec.payable_type = "no"
            elif rec.end_id.type in ["buyer", "tenant"]:
                if rec.payable_amount > 0:
                    rec.payable_type = "ar"
                elif rec.payable_amount < 0:
                    rec.payable_type = "ap"
                else:
                    rec.payable_type = "no"
            else:
                rec.payable_type = "no"

    @api.depends("amount_advanced", "advance_amt_repaid")
    def _compute_advance_amt_outstanding(self):
        for rec in self:
            rec.advance_amt_outstanding = rec.amount_advanced - rec.advance_amt_repaid

    @api.depends("gross_amount", "total_split_fees")
    def _compute_available_for_advance(self):
        for rec in self:
            if rec.payment_type == "sales_agent":
                # Retrieve the brokerage preferences record
                brokerage_prefs = self.env["brokerage.preferences"].search([], limit=1)
                if not brokerage_prefs:
                    raise ValidationError(
                        _(
                            "Please configure the Brokerage Preferences with the Advance Maximum Percentage."
                        )
                    )
                advance_percentage = brokerage_prefs.advance_maximum_percentage / 100.0
                rec.available_for_advance = (
                    rec.gross_amount - rec.total_split_fees
                ) * advance_percentage
            else:
                rec.available_for_advance = 0.0

    @api.depends("payable_amount")
    def _compute_due_amounts(self):
        for rec in self:
            if rec.payable_amount > 0:
                rec.due_to_contact = rec.payable_amount
                rec.due_from_contact = 0.0
            elif rec.payable_amount < 0:
                rec.due_to_contact = 0.0
                rec.due_from_contact = -rec.payable_amount
            else:
                rec.due_to_contact = 0.0
                rec.due_from_contact = 0.0

    @api.depends("sales_agent_id", "deal_id.deal_class_id")
    def _compute_commission_plans(self):
        for rec in self:
            if rec.payment_type == "sales_agent" and rec.sales_agent_id:
                plans = self.env["commission.plan"].search(
                    [
                        ("deal_class_ids", "in", rec.deal_id.deal_class_id.ids),
                        ("sales_agent_ids", "=", rec.sales_agent_id.id),
                    ]
                )
                rec.commission_plan_ids = plans
            else:
                rec.commission_plan_ids = False

    # =====================
    # Constraints
    # =====================
    @api.constrains("percentage_of_end")
    def _check_percentage_of_end_deal(self):
        for record in self:
            if not (0 < record.percentage_of_end <= 100):
                raise ValidationError(
                    _(
                        "Commission percentage must be greater than 0 and less than or equal to 100%."
                    )
                )
            total_percentage = (
                sum(
                    self.search(
                        [
                            ("deal_id", "=", record.deal_id.id),
                            ("end_id", "=", record.end_id.id),
                            ("id", "!=", record.id),
                        ]
                    ).mapped("percentage_of_end")
                )
                + record.percentage_of_end
            )
            if total_percentage > 100:
                raise ValidationError(
                    _("The total percentage of end cannot exceed 100%.")
                )

    @api.constrains(
        "payment_type", "sales_agent_id", "other_broker_id", "buyers_sellers_id"
    )
    def _check_payment_type_requirements(self):
        for rec in self:
            if rec.payment_type == "sales_agent":
                if not rec.sales_agent_id:
                    raise ValidationError(
                        _(
                            "Please select an existing Sales Agent when Payment Type is 'Sales Agent'."
                        )
                    )
            elif rec.payment_type == "other_broker":
                if not rec.other_broker_id:
                    raise ValidationError(
                        _(
                            "Please select or create a Brokerage when Payment Type is 'Other Broker'."
                        )
                    )
            elif rec.payment_type == "non_licensee":
                if not rec.buyers_sellers_id:
                    raise ValidationError(
                        _(
                            "Please select or create a Contact when Payment Type is 'Non-Licensee'."
                        )
                    )
            # Ensure only the selected type's field is filled
            if rec.payment_type != "sales_agent" and rec.sales_agent_id:
                raise ValidationError(
                    _("Sales Agent should not be filled for this Payment Type.")
                )
            if rec.payment_type != "other_broker" and rec.other_broker_id:
                raise ValidationError(
                    _("Brokerage should not be filled for this Payment Type.")
                )
            if rec.payment_type != "non_licensee" and rec.buyers_sellers_id:
                raise ValidationError(
                    _("Contact should not be filled for this Payment Type.")
                )

    @api.constrains("payment_type", "amount_advanced", "advance_amt_repaid")
    def _check_advance_applicability(self):
        for rec in self:
            if rec.payment_type != "sales_agent" and (
                rec.amount_advanced > 0 or rec.advance_amt_repaid > 0
            ):
                raise ValidationError(
                    _("Advances are only applicable to Sales Agents.")
                )

    @api.constrains("listing_id")
    def _check_listing_financial_calculations(self):
        for rec in self:
            if rec.listing_id and not rec.deal_id:
                # Ensure no financial calculations are done
                rec.base_commission = 0.0
                rec.buyer_side_commission = 0.0
                rec.seller_side_commission = 0.0
                rec.gross_amount = 0.0
                rec.total_split_fees = 0.0
                rec.total_net_amount = 0.0
                rec.tax = 0.0
                rec.total_tax = 0.0
                rec.payable_amount = 0.0

    # =====================
    # Onchange Methods
    # =====================
    @api.onchange("payment_type")
    def _onchange_payment_type(self):
        for rec in self:
            if rec.payment_type == "sales_agent":
                rec.other_broker_id = False
                rec.other_broker_agent_id = False
                rec.buyers_sellers_id = False
                rec.sales_agent_id = (
                    rec.partner_id if rec.partner_id.is_sales_agent else False
                )
                rec._onchange_tax_recompute()
            elif rec.payment_type == "other_broker":
                rec.sales_agent_id = False
                rec.buyers_sellers_id = False
                rec.other_broker_agent_id = False
                rec.other_broker_id = (
                    rec.partner_id if rec.partner_id.is_other_broker else False
                )
                rec._onchange_tax_recompute()
            elif rec.payment_type == "non_licensee":
                rec.sales_agent_id = False
                rec.other_broker_id = False
                rec.buyers_sellers_id = (
                    rec.partner_id if rec.partner_id.is_buyer_seller else False
                )
                rec.tax_ids = False
                rec.tax = 0.0
                rec.total_tax = 0.0

    @api.onchange("sales_agent_id")
    def _onchange_sales_agent_id(self):
        for rec in self:
            if rec.sales_agent_id:
                rec.partner_id = rec.sales_agent_id
                rec._onchange_tax_recompute()
                rec._apply_commission_plans()
                rec._compute_available_for_advance()
            else:
                rec.partner_id = False

    @api.onchange("other_broker_id")
    def _onchange_other_broker_id(self):
        for rec in self:
            if rec.other_broker_id:
                rec.partner_id = rec.other_broker_id
                rec._onchange_tax_recompute()
            else:
                rec.partner_id = False

    @api.onchange("buyers_sellers_id")
    def _onchange_buyers_sellers_id(self):
        for rec in self:
            if rec.buyers_sellers_id:
                rec.partner_id = rec.buyers_sellers_id
                rec.tax_ids = False
                rec.tax = 0.0
                rec.total_tax = 0.0
            else:
                rec.partner_id = False

    @api.onchange("percentage_of_end")
    def _onchange_percentage_of_end(self):
        for rec in self:
            if rec.percentage_of_end > 100:
                rec.percentage_of_end = 100
            total_percentage = (
                sum(
                    self.search(
                        [
                            ("deal_id", "=", rec.deal_id.id),
                            ("end_id", "=", rec.end_id.id),
                            ("id", "!=", rec.id),
                        ]
                    ).mapped("percentage_of_end")
                )
                + rec.percentage_of_end
            )
            if total_percentage > 100:
                remaining = 100 - (total_percentage - rec.percentage_of_end)
                rec.percentage_of_end = max(0.0, remaining)
                return {
                    "warning": {
                        "title": "Percentage Exceeded",
                        "message": "The total percentage of end cannot exceed 100%. Adjusted to remaining percentage.",
                    }
                }

    @api.onchange(
        "payment_type", "sales_agent_id", "sales_agent_id.vat", "other_broker_id"
    )
    def _onchange_tax_recompute(self):
        for rec in self:
            rec._compute_tax_ids()
            rec._compute_tax()
            rec._compute_total_tax()

    @api.onchange("deal_id")
    def _onchange_deal_id(self):
        if self.deal_id:
            self._compute_base_commission()
            self._compute_buyer_side_commission()
            self._compute_seller_side_commission()
            self._compute_gross_amount()
            self._compute_total_split_fees()
            self._compute_total_net_amount()
            self._compute_tax()
            self._compute_total_tax()
            self._compute_payable_amount()
        else:
            self.base_commission = 0.0
            self.buyer_side_commission = 0.0
            self.seller_side_commission = 0.0
            self.gross_amount = 0.0
            self.total_split_fees = 0.0
            self.total_net_amount = 0.0
            self.tax = 0.0
            self.total_tax = 0.0
            self.payable_amount = 0.0

    # =====================
    # Helper Methods
    # =====================
    def _apply_commission_plans(self):
        for rec in self:
            rec.commission_plan_line_ids.unlink()  # Remove existing commission lines
            for plan in rec.commission_plan_ids:
                commission_record = rec.sales_agent_id.sales_agent_commission_id
                if (
                    commission_record
                    and commission_record.commission_earned
                    < commission_record.commission_cap
                ):
                    self.env["deal.commission.plan.line"].create(
                        {
                            "commission_id": commission_record.id,
                            "sales_agent_line_id": rec.id,
                            "commission_plan_id": plan.id,
                        }
                    )
                    _logger.info(
                        "Applied Commission Plan ID: %s to Sales Agent Line ID: %s",
                        plan.id,
                        rec.id,
                    )
            rec._compute_total_commission()

    def _compute_total_commission(self):
        for rec in self:
            total_commission = sum(
                rec.commission_plan_line_ids.mapped("commission_amount")
            )
            total_flat_fee = sum(rec.commission_plan_line_ids.mapped("flat_fee"))
            rec.total_split_fees = total_commission + total_flat_fee
            rec.total_net_amount = rec.gross_amount - rec.total_split_fees
            rec._compute_tax()
            rec._compute_payable_amount()

    def _update_partner_information(self):
        """
        Method to update the contact information of the partner directly from this model.
        """
        for rec in self:
            # Update the partner's contact information if fields have changed
            partner_fields = [
                "street",
                "street2",
                "city",
                "state_id",
                "zip",
                "country_id",
                "phone",
                "email",
                "website",
                "vat",
                "comment",
            ]
            vals = {}
            for field in partner_fields:
                # Get the value from the related field
                model_value = getattr(rec, field)
                partner_value = getattr(rec.partner_id, field)
                if model_value != partner_value:
                    vals[field] = model_value
            if vals:
                rec.partner_id.write(vals)
                _logger.info(
                    "Updated partner information for Partner ID: %s", rec.partner_id.id
                )

    # =====================
    # Override Create and Write Methods
    # =====================
    @api.model
    def create(self, vals):
        res = super(SalesAgentsAndReferrals, self).create(vals)
        res._onchange_payment_type()
        res._apply_commission_plans()
        res._update_partner_information()
        _logger.info("Created SalesAgentsAndReferrals with ID: %s", res.id)
        return res

    def write(self, vals):
        res = super(SalesAgentsAndReferrals, self).write(vals)
        self._onchange_payment_type()
        self._apply_commission_plans()
        self._update_partner_information()
        _logger.info("Updated SalesAgentsAndReferrals records: %s", self.ids)
        return res

    # =====================
    # Name Get and Name Search Methods
    # =====================
    def name_get(self):
        result = []
        for rec in self:
            name = rec.partner_id.name
            if rec.payment_type == "sales_agent":
                name = f"{name} (Sales Agent)"
            elif rec.payment_type == "other_broker":
                name = f"{name} (Other Broker)"
            elif rec.payment_type == "non_licensee":
                name = f"{name} (Non-Licensee)"
            result.append((rec.id, name))
        return result

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = args or []
        if name:
            partner_domain = [("name", operator, name)]
            if self._context.get("payment_type"):
                payment_type = self._context["payment_type"]
                if payment_type == "sales_agent":
                    partner_domain.append(("is_sales_agent", "=", True))
                elif payment_type == "other_broker":
                    partner_domain.append(("is_other_broker", "=", True))
                elif payment_type == "non_licensee":
                    partner_domain.append(("is_buyer_seller", "=", True))
            partner_ids = self.env["res.partner"].search(partner_domain).ids
            args += [("partner_id", "in", partner_ids)]
        records = self.search(args, limit=limit)
        return records.name_get()

    # =====================
    # Additional Methods
    # =====================
    @api.model
    def default_get(self, fields_list):
        res = super(SalesAgentsAndReferrals, self).default_get(fields_list)
        res["company_id"] = self.env.company.id
        res["percentage_of_end"] = self._get_default_percentage_of_end()
        return res

    def _get_default_percentage_of_end(self):
        if self._context.get("default_deal_id") and self._context.get("default_end_id"):
            deal_id = self._context["default_deal_id"]
            end_id = self._context["default_end_id"]
            existing_percentages = sum(
                self.search_count(
                    [
                        ("deal_id", "=", deal_id),
                        ("end_id", "=", end_id),
                        ("id", "!=", self.id if self else 0),
                    ]
                )
            )
            return max(0.0, min(100.0, 100.0 - existing_percentages))
        return 100.0

    def unlink(self):
        for rec in self:
            rec.mentorship_line_ids.unlink()
        _logger.info("Unlinked SalesAgentsAndReferrals records: %s", self.ids)
        return super(SalesAgentsAndReferrals, self).unlink()

    def action_view_commission_plan_lines(self):
        """
        Action to view commission plan lines in a separate window.
        """
        self.ensure_one()
        commission_plan_lines = self.commission_plan_line_ids
        if not commission_plan_lines:
            raise UserError(_("No Commission Plan Lines found for this record."))

        return {
            "type": "ir.actions.act_window",
            "name": "Commission Plan Lines",
            "view_mode": "tree,form",
            "res_model": "deal.commission.plan.line",
            "domain": [("id", "in", commission_plan_lines.ids)],
            "context": {
                "default_sales_agent_line_id": self.id,
            },
            "target": "current",
        }

    def action_send_email(self):
        """Method to send email to the contact."""
        template = self.env.ref(
            "agentlink_transaction_manager.email_template_buyers_sellers",
            raise_if_not_found=False,
        )
        if not template:
            raise UserError(
                _(
                    "Email template 'agentlink_transaction_manager.email_template_buyers_sellers' not found."
                )
            )
        template.send_mail(self.id, force_send=True)
        _logger.info("Sent email for SalesAgentsAndReferrals ID: %s", self.id)

    def action_print_document(self):
        """Method to print related documents."""
        report = self.env.ref(
            "agentlink_transaction_manager.report_buyers_sellers",
            raise_if_not_found=False,
        )
        if not report:
            raise UserError(
                _(
                    "Report 'agentlink_transaction_manager.report_buyers_sellers' not found."
                )
            )
        _logger.info("Printing document for SalesAgentsAndReferrals ID: %s", self.id)
        return report.report_action(self)

    def action_view_sales_agents(self):
        """
        Action to view sales agents in a separate window.
        """
        self.ensure_one()
        sales_agents = self.env["sales.agents.and.referrals"].search(
            [
                ("deal_id", "=", self.deal_id.id),
                ("end_id", "=", self.end_id.id),
                ("payment_type", "=", "sales_agent"),
            ]
        )
        if not sales_agents:
            raise UserError(_("No Sales Agents found for this deal."))

        return {
            "type": "ir.actions.act_window",
            "name": "Sales Agents and Referrals",
            "view_mode": "tree,form",
            "res_model": "sales.agents.and.referrals",
            "domain": [("id", "in", sales_agents.ids)],
            "context": {
                "default_deal_id": self.deal_id.id,
                "default_end_id": self.end_id.id,
            },
            "target": "current",
        }

    _sql_constraints = [
        (
            "unique_broker_per_deal_end",
            "UNIQUE(deal_id, end_id)",
            "Each deal and end combination can only have one associated broker.",
        )
    ]
