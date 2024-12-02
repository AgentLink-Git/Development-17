# models/sales_agents/sales_agents_and_referrals.py

"""
Module for managing Sales Agents and Referrals.
Defines SalesAgentsAndReferrals, SalesAgentTeamWizard, SalesAgentTeams, and SalesAgentTeamMember models
to handle the creation, application, and management of sales agents, referrals, and their associations
with deals and listings. Ensures proper commission distributions and data integrity through validations.
"""

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

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
        help="Select the partner associated with this referral."
    )

    # =====================
    # Deal and Listing Relationships
    # =====================
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        domain=[("is_active", "=", True)],
        help="Select the deal associated with this referral."
    )
    listing_id = fields.Many2one(
        "listing.records",
        string="Listing",
        domain=[("status", "not in", ["sold", "cancelled"])],
        ondelete="cascade",
        help="Select the listing associated with this referral."
    )
    end_id = fields.Many2one(
        "deal.end",
        string="End",
        required=True,
        ondelete="cascade",
        tracking=True,
        help="Select the end associated with the deal or listing."
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
        help="Type of payment associated with this referral."
    )
    sales_agent_id = fields.Many2one(
        "res.partner",
        string="Sales Agent",
        domain=[("is_sales_agent", "=", True)],
        tracking=True,
        help="Select the sales agent involved in this referral."
    )
    other_broker_id = fields.Many2one(
        "res.partner",
        string="Other Brokerage",
        domain=[("is_other_broker", "=", True)],
        tracking=True,
        help="Select the other brokerage involved in this referral."
    )
    other_broker_agent_id = fields.Many2one(
        "res.partner",
        string="Other Broker Agent",
        domain=[("is_other_broker_agent", "=", True)],
        tracking=True,
        help="Select the agent from the other brokerage."
    )
    buyers_sellers_id = fields.Many2one(
        "res.partner",
        string="Contact",
        domain=[("is_buyer_seller", "=", True)],
        tracking=True,
        help="Select the contact involved in this referral."
    )
    account_move_id = fields.Many2one(
        "account.move",
        string="Account Move",
        ondelete="cascade",
        required=True,
        help="Related Account Move.",
    )
    for_sale_or_lease = fields.Selection(
        [("for_sale", "For Sale"), ("for_lease", "For Lease")],
        string="For Sale/Lease",
        tracking=True,
        help="Indicate whether the referral is for sale or lease."
    )
    referral_letter_on_file = fields.Boolean(
        string="Referral Letter on File",
        default=False,
        tracking=True,
        help="Indicates if a referral letter is on file."
    )

    # =====================
    # Contact Information Fields (for updating res.partner)
    # =====================
    street = fields.Char(
        related='partner_id.street', string='Street', store=True
    )
    street2 = fields.Char(
        related='partner_id.street2', string='Street2', store=True
    )
    city = fields.Char(
        related='partner_id.city', string='City', store=True
    )
    state_id = fields.Many2one(
        'res.country.state', related='partner_id.state_id', string='State', store=True
    )
    zip = fields.Char(
        related='partner_id.zip', string='Zip', store=True
    )
    country_id = fields.Many2one(
        'res.country', related='partner_id.country_id', string='Country', store=True
    )
    phone = fields.Char(
        related='partner_id.phone', string='Phone', store=True
    )
    email = fields.Char(
        related='partner_id.email', string='Email', store=True
    )
    website = fields.Char(
        related='partner_id.website', string='Website', store=True
    )
    vat = fields.Char(
        related='partner_id.vat', string='Tax ID', store=True
    )
    sales_agent_note = fields.Html(
        related='partner_id.comment',
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
        help="Base commission calculated based on the deal."
    )
    buyer_side_commission = fields.Monetary(
        string="Buyer Side Commission",
        compute="_compute_buyer_side_commission",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Commission from the buyer's side."
    )
    seller_side_commission = fields.Monetary(
        string="Seller Side Commission",
        compute="_compute_seller_side_commission",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Commission from the seller's side."
    )
    percentage_of_end = fields.Float(
        string="% of End",
        default=100.0,
        required=True,
        tracking=True,
        help="Percentage of the end amount allocated to this referral."
    )
    plus_flat_fee = fields.Monetary(
        string="+ Flat Fee",
        currency_field="currency_id",
        tracking=True,
        help="Additional flat fee added to the commission."
    )
    less_flat_fee = fields.Monetary(
        string="- Flat Fee",
        currency_field="currency_id",
        tracking=True,
        help="Flat fee deducted from the commission."
    )
    commission_plan_less_flat = fields.Monetary(
        string="- Flat Fee (Commission Plan)",
        currency_field="currency_id",
        tracking=True,
        help="Flat fee from the commission plan deducted."
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
        help="Specify which side the double end applies to."
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
        help="Total gross amount from the deal after commissions."
    )
    total_split_fees = fields.Monetary(
        string="Total Splits & Fees",
        compute="_compute_total_split_fees",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Total splits and fees calculated from commission plans."
    )
    total_net_amount = fields.Monetary(
        string="Total Net",
        compute="_compute_total_net_amount",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Net amount after deducting splits and fees."
    )

    # =====================
    # Commission Plan Fields
    # =====================
    commission_plan_ids = fields.Many2many(
        "commission.plan",
        string="Commission Plans",
        compute="_compute_commission_plans",
        store=True,
        help="Commission plans applicable to this referral based on deal class and sales agent."
    )
    commission_plan_line_ids = fields.One2many(
        "deal.commission.plan.line",
        "sales_agent_line_id",
        string="Commission Plan Lines",
        help="Detailed commission plan lines associated with this referral."
    )

    # =====================
    # Tax Fields
    # =====================
    tax_ids = fields.Many2many(
        "account.tax",
        string="Taxes",
        compute="_compute_tax_ids",
        store=True,
        help="Applicable taxes for this referral."
    )
    tax = fields.Monetary(
        string="Tax",
        compute="_compute_tax",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Total tax amount calculated."
    )
    total_tax = fields.Float(
        string="Total Tax Rate",
        compute="_compute_total_tax",
        store=True,
        tracking=True,
        help="Total tax rate applied."
    )

    # =====================
    # Financial Balances
    # =====================
    due_to_contact = fields.Monetary(
        string="Due to Contact",
        currency_field="currency_id",
        compute="_compute_due_amounts",
        store=True,
        help="Amount due to the contact."
    )
    due_from_contact = fields.Monetary(
        string="Due from Contact",
        currency_field="currency_id",
        compute="_compute_due_amounts",
        store=True,
        help="Amount due from the contact."
    )
    payable_amount = fields.Monetary(
        string="Payable",
        compute="_compute_payable_amount",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Total payable amount after tax and net calculations."
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
        help="Type of payable or receivable."
    )

    # =====================
    # Advance Fields (Applicable only to Sales Agents)
    # =====================
    amount_advanced = fields.Monetary(
        string="Amount Advanced",
        currency_field="currency_id",
        tracking=True,
        help="Amount advanced to the sales agent."
    )
    advance_amt_repaid = fields.Monetary(
        string="Advance Repaid",
        currency_field="currency_id",
        tracking=True,
        help="Amount of the advance that has been repaid."
    )
    advance_amt_outstanding = fields.Monetary(
        string="Advance Outstanding",
        compute="_compute_advance_amt_outstanding",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Outstanding amount of the advance."
    )
    available_for_advance = fields.Monetary(
        string="Available for Advance",
        compute="_compute_available_for_advance",
        store=True,
        currency_field="currency_id",
        tracking=True,
        help="Amount available for future advances based on brokerage preferences."
    )
    amount_requested = fields.Monetary(
        string="Amount Requested",
        currency_field="currency_id",
        tracking=True,
        help="Amount requested for advance."
    )
    advance_approved = fields.Boolean(
        string="Advance Approved",
        default=False,
        tracking=True,
        help="Indicates if the advance has been approved."
    )

    # =====================
    # Mentorship
    # =====================
    mentorship_line_ids = fields.One2many(
        "sales.agent.mentorship.line",
        "sales_agent_line_id",
        string="Mentorship Lines",
        help="Lines representing mentorship applications related to this referral."
    )

    # =====================
    # Notes and Additional Information
    # =====================
    sales_agent_note = fields.Html(
        string="Sales Agent Notes",
        related='partner_id.comment',
        store=True,
        tracking=True,
        help="Additional notes about the sales agent."
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
        """Compute the base commission based on the deal and end type."""
        for rec in self:
            end_type = rec.end_id.type
            if end_type in ["buyer", "tenant"]:
                rec.base_commission = rec.deal_id.buyer_side_total or 0.0
            elif end_type in ["seller", "landlord"]:
                rec.base_commission = rec.deal_id.seller_side_total or 0.0
            elif end_type == "double_end":
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
        """Compute the buyer side commission."""
        for rec in self:
            rec.buyer_side_commission = rec.deal_id.buyer_side_total or 0.0

    @api.depends("deal_id.seller_side_total")
    def _compute_seller_side_commission(self):
        """Compute the seller side commission."""
        for rec in self:
            rec.seller_side_commission = rec.deal_id.seller_side_total or 0.0

    @api.depends("base_commission", "percentage_of_end", "plus_flat_fee", "less_flat_fee")
    def _compute_gross_amount(self):
        """Compute the gross amount after applying percentages and fees."""
        for rec in self:
            rec.gross_amount = (
                (rec.base_commission * rec.percentage_of_end / 100.0)
                + rec.plus_flat_fee
                - rec.less_flat_fee
            )

    @api.depends("commission_plan_line_ids.split_fees")
    def _compute_total_split_fees(self):
        """Compute the total splits and fees from commission plan lines."""
        for rec in self:
            rec.total_split_fees = sum(rec.commission_plan_line_ids.mapped("split_fees"))

    @api.depends("gross_amount", "total_split_fees")
    def _compute_total_net_amount(self):
        """Compute the total net amount after deducting splits and fees."""
        for rec in self:
            rec.total_net_amount = rec.gross_amount - rec.total_split_fees

    @api.depends("payment_type", "sales_agent_id", "sales_agent_id.vat", "other_broker_id")
    def _compute_tax_ids(self):
        """Compute applicable taxes based on payment type and associated entities."""
        for rec in self:
            rec.tax_ids = rec._get_default_taxes() if rec._is_tax_applicable() else False

    def _get_default_taxes(self):
        """Retrieve default taxes from deal preferences or fallback to purchase taxes."""
        deal_preferences = self.env["deal.preference"].search([], limit=1)
        if deal_preferences and deal_preferences.tax_ids:
            return deal_preferences.tax_ids
        else:
            # Fallback to default purchase taxes if deal preferences are not set
            return self.env["account.tax"].search([("type_tax_use", "=", "purchase")], limit=1)

    def _is_tax_applicable(self):
        """Determine if taxes are applicable based on payment type."""
        return self.payment_type in ["sales_agent", "other_broker"]

    @api.depends("total_net_amount", "tax_ids")
    def _compute_tax(self):
        """Compute the total tax amount."""
        for rec in self:
            if rec.tax_ids and rec.total_net_amount:
                taxes = rec.tax_ids.compute_all(rec.total_net_amount)
                rec.tax = taxes["total_included"] - taxes["total_excluded"]
            else:
                rec.tax = 0.0

    @api.depends("tax_ids")
    def _compute_total_tax(self):
        """Compute the total tax rate applied."""
        for rec in self:
            rec.total_tax = sum(tax.amount for tax in rec.tax_ids)

    @api.depends("gross_amount", "total_split_fees")
    def _compute_payable_amount(self):
        """Compute the payable amount after tax and net calculations."""
        for rec in self:
            rec.payable_amount = rec.total_net_amount + rec.tax

    @api.depends("payable_amount", "end_id.type")
    def _compute_payable_type(self):
        """Determine the type of payable or receivable based on end type."""
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
        """Compute the outstanding amount of the advance."""
        for rec in self:
            rec.advance_amt_outstanding = rec.amount_advanced - rec.advance_amt_repaid

    @api.depends("gross_amount", "total_split_fees")
    def _compute_available_for_advance(self):
        """Compute the amount available for advance based on brokerage preferences."""
        for rec in self:
            if rec.payment_type == "sales_agent":
                brokerage_prefs = self.env['brokerage.preferences'].search([], limit=1)
                if not brokerage_prefs:
                    raise ValidationError(_("Please configure the Brokerage Preferences with the Advance Maximum Percentage."))
                advance_percentage = brokerage_prefs.advance_maximum_percentage / 100.0
                rec.available_for_advance = (rec.gross_amount - rec.total_split_fees) * advance_percentage
            else:
                rec.available_for_advance = 0.0

    @api.depends("deal_id.deal_class_id", "sales_agent_id")
    def _compute_commission_plans(self):
        """Compute applicable commission plans based on deal class and sales agent."""
        for rec in self:
            if rec.payment_type == "sales_agent" and rec.sales_agent_id and rec.deal_id:
                plans = self.env["commission.plan"].search([
                    ("deal_class_ids", "in", rec.deal_id.deal_class_id.ids),
                    ("sales_agent_ids", "=", rec.sales_agent_id.id),
                ])
                rec.commission_plan_ids = plans
            else:
                rec.commission_plan_ids = False

    @api.depends("deal_id.offer_date")
    def _compute_tax_ids(self):
        """Recompute tax IDs when deal offer date changes."""
        for rec in self:
            rec._compute_tax()

    @api.depends("deal_id")
    def _compute_due_amounts(self):
        """Compute amounts due to or from the contact based on payable amount."""
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

    # =====================
    # Constraints
    # =====================
    @api.constrains("percentage_of_end")
    def _check_percentage_of_end_deal(self):
        """Ensure that the percentage of end is between 0 and 100 and does not exceed 100% in total."""
        for record in self:
            if not (0 < record.percentage_of_end <= 100):
                raise ValidationError(
                    _("Commission percentage must be greater than 0 and less than or equal to 100%.")
                )
            total_percentage = (
                sum(
                    self.search([
                        ("deal_id", "=", record.deal_id.id),
                        ("end_id", "=", record.end_id.id),
                        ("id", "!=", record.id),
                    ]).mapped("percentage_of_end")
                ) + record.percentage_of_end
            )
            if total_percentage > 100:
                raise ValidationError(_("The total percentage of end cannot exceed 100%."))

    @api.constrains("payment_type", "sales_agent_id", "other_broker_id", "buyers_sellers_id")
    def _check_payment_type_requirements(self):
        """Ensure that required fields are set based on the payment type and only relevant fields are filled."""
        for rec in self:
            if rec.payment_type == "sales_agent":
                if not rec.sales_agent_id:
                    raise ValidationError(
                        _("Please select an existing Sales Agent when Payment Type is 'Sales Agent'.")
                    )
                # Ensure other fields are not set
                if rec.other_broker_id or rec.buyers_sellers_id:
                    raise ValidationError(_("Sales Agent fields should not be filled for this Payment Type."))
            elif rec.payment_type == "other_broker":
                if not rec.other_broker_id:
                    raise ValidationError(
                        _("Please select or create a Brokerage when Payment Type is 'Other Broker'.")
                    )
                # Ensure other fields are not set
                if rec.sales_agent_id or rec.buyers_sellers_id:
                    raise ValidationError(_("Brokerage fields should not be filled for this Payment Type."))
            elif rec.payment_type == "non_licensee":
                if not rec.buyers_sellers_id:
                    raise ValidationError(
                        _("Please select or create a Contact when Payment Type is 'Non-Licensee'.")
                    )
                # Ensure other fields are not set
                if rec.sales_agent_id or rec.other_broker_id:
                    raise ValidationError(_("Contact fields should not be filled for this Payment Type."))

    @api.constrains("payment_type", "amount_advanced", "advance_amt_repaid")
    def _check_advance_applicability(self):
        """Ensure that advances are only applicable to Sales Agents."""
        for rec in self:
            if rec.payment_type != "sales_agent" and (
                rec.amount_advanced > 0 or rec.advance_amt_repaid > 0
            ):
                raise ValidationError(_("Advances are only applicable to Sales Agents."))

    @api.constrains("listing_id")
    def _check_listing_financial_calculations(self):
        """Ensure no financial calculations are done for listings without associated deals."""
        for rec in self:
            if rec.listing_id and not rec.deal_id:
                # Reset financial fields if not associated with a deal
                financial_fields = [
                    'base_commission', 'buyer_side_commission', 'seller_side_commission',
                    'gross_amount', 'total_split_fees', 'total_net_amount',
                    'tax', 'total_tax', 'payable_amount'
                ]
                for field in financial_fields:
                    setattr(rec, field, 0.0)

    # =====================
    # Onchange Methods
    # =====================
    @api.onchange("payment_type")
    def _onchange_payment_type(self):
        """Reset fields based on the selected payment type and recompute taxes."""
        for rec in self:
            if rec.payment_type == "sales_agent":
                rec.other_broker_id = False
                rec.other_broker_agent_id = False
                rec.buyers_sellers_id = False
                rec.sales_agent_id = rec.partner_id if rec.partner_id.is_sales_agent else False
            elif rec.payment_type == "other_broker":
                rec.sales_agent_id = False
                rec.buyers_sellers_id = False
                rec.other_broker_agent_id = False
                rec.other_broker_id = rec.partner_id if rec.partner_id.is_other_broker else False
            elif rec.payment_type == "non_licensee":
                rec.sales_agent_id = False
                rec.other_broker_id = False
                rec.buyers_sellers_id = rec.partner_id if rec.partner_id.is_buyer_seller else False
                rec.tax_ids = False
                rec.tax = 0.0
                rec.total_tax = 0.0

            # Recompute taxes after changing payment type
            rec._compute_tax_ids()
            rec._compute_tax()
            rec._compute_total_tax()

    @api.onchange("sales_agent_id")
    def _onchange_sales_agent_id(self):
        """Update partner information and apply commission plans when sales agent changes."""
        for rec in self:
            if rec.sales_agent_id:
                rec.partner_id = rec.sales_agent_id
                rec._compute_tax_ids()
                rec._apply_commission_plans()
                rec._compute_available_for_advance()
            else:
                rec.partner_id = False

    @api.onchange("other_broker_id")
    def _onchange_other_broker_id(self):
        """Update partner information when other broker changes."""
        for rec in self:
            if rec.other_broker_id:
                rec.partner_id = rec.other_broker_id
                rec._compute_tax_ids()
            else:
                rec.partner_id = False

    @api.onchange("buyers_sellers_id")
    def _onchange_buyers_sellers_id(self):
        """Update partner information when buyers/sellers contact changes."""
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
        """Ensure that the percentage of end does not exceed 100%."""
        for rec in self:
            if rec.percentage_of_end > 100:
                rec.percentage_of_end = 100
            total_percentage = (
                sum(
                    self.search([
                        ("deal_id", "=", rec.deal_id.id),
                        ("end_id", "=", rec.end_id.id),
                        ("id", "!=", rec.id),
                    ]).mapped("percentage_of_end")
                ) + rec.percentage_of_end
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
        """Recompute taxes when relevant fields change."""
        for rec in self:
            rec._compute_tax_ids()
            rec._compute_tax()
            rec._compute_total_tax()

    @api.onchange("deal_id")
    def _onchange_deal_id(self):
        """Compute financial fields when deal changes."""
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
            # Reset financial fields if no deal is selected
            financial_fields = [
                'base_commission', 'buyer_side_commission', 'seller_side_commission',
                'gross_amount', 'total_split_fees', 'total_net_amount',
                'tax', 'total_tax', 'payable_amount'
            ]
            for field in financial_fields:
                setattr(self, field, 0.0)

    # =====================
    # Helper Methods
    # =====================
    def _apply_commission_plans(self):
        """Apply applicable commission plans to the referral."""
        for rec in self:
            rec.commission_plan_line_ids.unlink()  # Remove existing commission lines
            for plan in rec.commission_plan_ids:
                commission_record = rec.sales_agent_id.sales_agent_commission_id
                if commission_record and commission_record.commission_earned < commission_record.commission_cap:
                    self.env["deal.commission.plan.line"].create({
                        "commission_id": commission_record.id,
                        "sales_agent_line_id": rec.id,
                        "commission_plan_id": plan.id,
                    })
                    _logger.info(
                        "Applied Commission Plan ID: %s to Sales Agents and Referrals ID: %s",
                        plan.id, rec.id
                    )
            rec._compute_total_commission()

    def _compute_total_commission(self):
        """Compute total commission from commission plan lines."""
        for rec in self:
            total_commission = sum(rec.commission_plan_line_ids.mapped("commission_amount"))
            total_flat_fee = sum(rec.commission_plan_line_ids.mapped("flat_fee"))
            rec.total_split_fees = total_commission + total_flat_fee
            rec.total_net_amount = rec.gross_amount - rec.total_split_fees
            rec._compute_tax()
            rec._compute_payable_amount()

    def _update_partner_information(self):
        """Update the related partner's contact information based on referral data."""
        for rec in self:
            # List of fields to sync with res.partner
            partner_fields = [
                'street', 'street2', 'city', 'state_id', 'zip',
                'country_id', 'phone', 'email', 'website', 'vat', 'comment'
            ]
            vals = {}
            for field in partner_fields:
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
        """Override create method to apply commission plans and update partner information."""
        res = super(SalesAgentsAndReferrals, self).create(vals)
        res._onchange_payment_type()
        res._apply_commission_plans()
        res._update_partner_information()
        _logger.info("Created SalesAgentsAndReferrals with ID: %s", res.id)
        return res

    def write(self, vals):
        """Override write method to apply commission plans and update partner information."""
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
        """Customize the display name to include payment type."""
        result = []
        for rec in self:
            name = rec.partner_id.name or ""
            if rec.payment_type == 'sales_agent':
                name += " (Sales Agent)"
            elif rec.payment_type == 'other_broker':
                name += " (Other Broker)"
            elif rec.payment_type == 'non_licensee':
                name += " (Non-Licensee)"
            result.append((rec.id, name))
        return result

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """
        Customize the name_search to filter based on payment type and partner attributes.
        """
        args = args or []
        if name:
            partner_domain = [('name', operator, name)]
            payment_type = self._context.get('payment_type')
            if payment_type:
                if payment_type == 'sales_agent':
                    partner_domain.append(('is_sales_agent', '=', True))
                elif payment_type == 'other_broker':
                    partner_domain.append(('is_other_broker', '=', True))
                elif payment_type == 'non_licensee':
                    partner_domain.append(('is_buyer_seller', '=', True))
            partner_ids = self.env['res.partner'].search(partner_domain).ids
            args += [('partner_id', 'in', partner_ids)]
        records = self.search(args, limit=limit)
        return records.name_get()

    # =====================
    # Additional Methods
    # =====================
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
        sales_agents = self.env["sales.agents.and.referrals"].search([
            ("deal_id", "=", self.deal_id.id),
            ("end_id", "=", self.end_id.id),
            ("payment_type", "=", "sales_agent"),
        ])
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

    def action_view_team_members(self):
        """
        Action to view team members associated with the sales agent.
        """
        self.ensure_one()
        team_members = self.env["sales.agent.team.member"].search([
            ("partner_id", "=", self.sales_agent_id.id)
        ])
        if not team_members:
            raise UserError(_("No team members found for this sales agent."))

        return {
            "type": "ir.actions.act_window",
            "name": "Team Members",
            "view_mode": "tree,form",
            "res_model": "sales.agent.team.member",
            "domain": [("id", "in", team_members.ids)],
            "context": {
                "default_team_id": team_members.team_id.id,
            },
            "target": "current",
        }

    @api.model
    def default_get(self, fields_list):
        """Set default values for new records."""
        res = super(SalesAgentsAndReferrals, self).default_get(fields_list)
        res["company_id"] = self.env.company.id
        res["percentage_of_end"] = self._get_default_percentage_of_end()
        return res

    def _get_default_percentage_of_end(self):
        """Calculate the default percentage of end based on existing records."""
        if self._context.get("default_deal_id") and self._context.get("default_end_id"):
            deal_id = self._context["default_deal_id"]
            end_id = self._context["default_end_id"]
            existing_percentages = sum(
                self.search_count([
                    ("deal_id", "=", deal_id),
                    ("end_id", "=", end_id),
                    ("id", "!=", self.id if self else 0),
                ])
            )
            return max(0.0, min(100.0, 100.0 - existing_percentages))
        return 100.0

    def unlink(self):
        """Override unlink to remove related mentorship lines before deletion."""
        for rec in self:
            rec.mentorship_line_ids.unlink()
        _logger.info("Unlinked SalesAgentsAndReferrals records: %s", self.ids)
        return super(SalesAgentsAndReferrals, self).unlink()