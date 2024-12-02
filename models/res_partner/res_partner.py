# models/res_partner/res_partner.py

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class ResPartnerExtension(models.Model):
    _inherit = [
        "res.partner"
    ]

    # =====================
    # Role Identification Fields
    # =====================
    is_buyer_seller = fields.Boolean(
        string="Is Buyer/Seller",
        default=False,
        help="Indicates if the partner is a Buyer or Seller.",
    )
    is_law_firm = fields.Boolean(
        string="Is Law Firm",
        default=False,
        help="Indicates if the partner is a Law Firm.",
    )
    is_lawyer = fields.Boolean(
        string="Is Lawyer",
        default=False,
        help="Indicates if the partner is a Lawyer associated with a Law Firm.",
    )
    is_sales_agent = fields.Boolean(
        string="Is Our Sales Agent",
        default=False,
        help="Indicates if the partner is one of our Sales Agents.",
    )
    is_other_broker = fields.Boolean(
        string="Is Other Broker",
        default=False,
        help="Indicates if the partner is a real estate broker.",
    )
    is_other_broker_agent = fields.Boolean(
        string="Is Other Broker Agent",
        default=False,
        help="Indicates if the partner is an Agent with another real estate broker.",
    )

    # =====================
    # Additional Fields for Financial Transactions
    # =====================
    payment_method = fields.Selection(
        selection=[("cheque", "Cheque"), ("direct_deposit", "Direct Deposit")],
        string="Payment Method",
        default="direct_deposit",
        required=True,
        help="Select the preferred payment method for this partner.",
    )

    deposit_instructions_received = fields.Boolean(
        string="Deposit Instructions Received",
        default=False,
        help="Indicates if the partner has provided our office with their banking information so we can make payment via Direct Deposits.",
    )

    # =====================
    # Boolean Fields
    # =====================
    deduct_agent_expenses = fields.Boolean(
        string="Deduct Agent Expenses",
        default=True,
        help="Controls whether agent expenses will be deducted from payments to this partner.",
    )
    allow_commission_advances = fields.Boolean(
        string="Allow Commission Advances",
        default=False,
        help="Indicates whether this partner is allowed to request commission advances.",
    )

    # =====================
    # Relationships
    # =====================
    transaction_line_ids = fields.One2many(
        "transaction.line", "partner_id", string="Transaction Lines"
    )
    deal_ids = fields.One2many(
        "deal.records",
        "partner_id",
        string="Deals",
        help="Deals associated with this partner.",
    )
    listing_ids = fields.One2many(
        "listing.records",
        "partner_id",
        string="Deals",
        help="Deals associated with this partner.",
    )

    other_broker_ids = fields.One2many(
        "other.broker", "partner_id", string="Other Broker"
    )
    other_broker_agent_ids = fields.One2many(
        "other.broker.agent", "partner_id", string="Other Broker Agent"
    )
    select_broker_wizard_ids = fields.One2many(
        "select.broker.wizard", "partner_id", string="Other Broker"
    )
    law_firm_ids = fields.One2many(
        "law.firm", "partner_id", string="Law Firm"
    )
    lawyer_ids = fields.One2many(
        "lawyer", "partner_id", string="Lawyer"
    )
    law_firm_wizard_ids = fields.One2many(
        "law.firm.wizard", "partner_id", string="Law Firm"
    )
    sales_agents_and_referrals_ids = fields.One2many(
        "sales.agents.and.referrals", "partner_id", string="Sales Agents and Referrals"
    )
    buyers_sellers_ids = fields.One2many(
        "buyers.sellers", "partner_id", string="Buyers/Sellers"
    )
    buyers_sellers_wizard_ids = fields.One2many(
        "buyers.sellers.wizard", "partner_id", string="Buyers/Sellers"
    )

    # =====================
    # Sales Agent Cumulative Commission Totals
    # =====================
    fee_anniversary = fields.Date(
        string="Fee Anniversary",
        help="The date on which the agent's cumulative commission totals reset each year.",
    )
    gross_amount_total = fields.Monetary(
        string="Total Gross Amount",
        currency_field="currency_id",
        default=0.0,
    )
    split_fees_total = fields.Monetary(
        string="Total Split Fees",
        currency_field="currency_id",
        default=0.0,
    )
    net_amount_total = fields.Monetary(
        string="Total Net Amount",
        currency_field="currency_id",
        default=0.0,
    )
    ends_total = fields.Integer(
        string="Total Ends",
        default=0,
    )

    # =====================
    # Constraints
    # =====================
    @api.constrains("is_other_broker", "is_other_broker_agent")
    def _check_broker_roles(self):
        for partner in self:
            if partner.is_other_broker and partner.is_other_broker_agent:
                raise ValidationError(
                    _("A partner cannot be both a Broker and a Broker's Agent.")
                )

    @api.constrains("is_other_broker_agent", "parent_broker_id")
    def _check_broker_agent_parent(self):
        for partner in self:
            if partner.is_other_broker_agent and not partner.parent_broker_id:
                raise ValidationError(
                    _("An Agent must be linked to a Parent broker.")
                )

    @api.constrains("is_law_firm", "is_lawyer")
    def _check_law_firm_roles(self):
        for partner in self:
            if partner.is_law_firm and partner.is_lawyer:
                raise ValidationError(
                    _("A partner cannot be both a Law Firm and a Lawyer.")
                )

    @api.constrains("is_lawyer", "parent_law_firm_id")
    def _check_lawyer_parent(self):
        for partner in self:
            if partner.is_lawyer and not partner.parent_law_firm_id:
                raise ValidationError(
                    _("A Lawyer must be linked to a Parent Law Firm.")
                )

    @api.constrains("is_sales_agent", "is_buyer_seller")
    def _check_sales_agent_referral_roles(self):
        for partner in self:
            if partner.is_sales_agent and partner.is_buyer_seller:
                raise ValidationError(
                    _(
                        "A partner cannot be both a Sales Agent and a Buyer/Seller. If a Sales Agent is buying or selling a property, please create a new Buyer/Seller contact for that Sales Agent."
                    )
                )

    # =====================
    # Compute Methods
    # =====================
    @api.depends('sales_agents_and_referrals_ids', 'sales_agents_and_referrals_ids.deal_id.stage_id', 'fee_anniversary')
    def _compute_cumulative_totals(self):
        for partner in self:
            if not partner.fee_anniversary:
                partner.gross_amount_total = 0.0
                partner.split_fees_total = 0.0
                partner.net_amount_total = 0.0
                partner.ends_total = 0
                continue

            today = fields.Date.today()
            fee_anniversary = partner.fee_anniversary

            # Adjust for leap years
            if fee_anniversary.month == 2 and fee_anniversary.day == 29:
                if not calendar.isleap(today.year):
                    fee_anniversary = fee_anniversary.replace(day=28)

            anniversary_date = fee_anniversary.replace(year=today.year)

            if today >= anniversary_date:
                period_start = anniversary_date
                period_end = anniversary_date + relativedelta(years=1) - timedelta(days=1)
            else:
                period_start = anniversary_date - relativedelta(years=1)
                period_end = anniversary_date - timedelta(days=1)

            # Get all deals closed within the current anniversary period
            deals = self.env['deal.records'].search([
                ('sales_agents_and_referrals_ids.sales_agent_id', '=', partner.id),
                ('stage_id.is_closed', '=', True),
                ('close_date', '>=', period_start),
                ('close_date', '<=', period_end),
            ])

            gross_total = 0.0
            split_fees_total = 0.0
            net_amount_total = 0.0
            ends_total = 0

            for deal in deals:
                for agent_line in deal.sales_agents_and_referrals_ids.filtered(lambda l: l.sales_agent_id == partner):
                    gross_total += agent_line.gross_amount
                    split_fees_total += agent_line.total_split_fees
                    net_amount_total += agent_line.total_net_amount
                    ends_total += 1  # Assuming one end per agent_line

            partner.gross_amount_total = gross_total
            partner.split_fees_total = split_fees_total
            partner.net_amount_total = net_amount_total
            partner.ends_total = ends_total

    # =====================
    # Override Methods
    # =====================
    @api.model
    def create(self, vals):
        partner = super(ResPartnerExtension, self).create(vals)
        partner._post_create_actions()
        return partner

    def write(self, vals):
        res = super(ResPartnerExtension, self).write(vals)
        self._post_write_actions(vals)
        return res

    def _post_create_actions(self):
        """
        Perform actions after creating a partner, such as initializing related records.
        """
        # Example: If a partner is marked as a broker, initialize related records or perform other actions.
        if self.is_other_broker:
            # Initialize related broker records if necessary
            pass

    def _post_write_actions(self, vals):
        """
        Perform actions after updating a partner, such as validating role changes.
        """
        # Example: If a broker agent's parent broker changes, perform necessary updates.
        if "parent_broker_id" in vals and self.is_other_broker_agent:
            # Perform updates related to parent broker change
            pass