# models/agent_portal/commission_plan.py

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CommissionPlan(models.Model):
    _name = "commission.plan"
    _description = "Commission Plan"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # =====================
    # Basic Information
    # =====================
    name = fields.Char(
        string="Name",
        required=True,
        tracking=True,
    )
    revenue_type = fields.Selection(
        [
            ("straight_commission", "Straight Commission"),
            ("graduated_commission", "Graduated Commission"),
        ],
        string="Revenue Type",
        required=True,
        tracking=True,
    )
    account_product = fields.Many2one(
        "product.product",
        string="Product",
        required=True,
        ondelete="restrict",
        tracking=True,
    )
    commission_percentage = fields.Float(
        string="Commission %",
        default=0.0,
        help="Percentage of the deal to be taken as commission.",
        tracking=True,
    )
    flat_fee = fields.Monetary(
        string="Flat Fee",
        default=0.0,
        help="Fixed fee to be deducted from the deal.",
        currency_field="currency_id",
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        tracking=True,
    )
    levels_based_on = fields.Selection(
        [
            ("net_commission", "Net Commission"),
            ("gross_commission", "Gross Commission"),
            ("number_of_ends", "# of Ends"),
            ("ytd_fees_paid", "YTD Fees Paid"),
        ],
        string="Levels Based On",
        default="gross_commission",
        required=True,
        tracking=True,
    )
    deal_class_ids = fields.Many2many(
        "deal.class",
        string="Deal Classes",
        domain=[("is_active", "=", True)],
        tracking=True,
    )
    sales_agent_ids = fields.Many2many(
        "res.partner",
        string="Sales Agents",
        domain=[("is_sales_agent", "=", True)],
        help="Sales agents to whom this commission plan applies.",
        tracking=True,
    )
    graduated_commission_ids = fields.One2many(
        "graduated.commission",
        "commission_plan_id",
        string="Graduated Commissions",
        help="Defines graduated commission tiers.",
        tracking=True,
    )

    # =====================
    # Methods
    # =====================

    def compute_commission_amount(self, previous_gross, deal_gross):
        """
        Calculate the commission amount based on the commission plan,
        handling both straight and graduated commission tiers.

        :param previous_gross: Cumulative gross amount before this deal
        :param deal_gross: Gross amount for this deal
        :return: Calculated commission amount
        """
        self.ensure_one()

        if self.revenue_type == "straight_commission":
            # Straight Commission Calculation
            commission_amount = (
                deal_gross * (self.commission_percentage / 100.0)
            ) + self.flat_fee
            return commission_amount

        elif self.revenue_type == "graduated_commission":
            # Graduated Commission Calculation
            total_commission = 0.0
            remaining_deal_gross = deal_gross

            # Get the graduated commission tiers sorted by 'commission_from'
            graduated_commissions = self.graduated_commission_ids.sorted(
                "commission_from"
            )

            for tier in graduated_commissions:
                tier_from = tier.commission_from
                tier_to = tier.commission_to
                tier_percentage = tier.commission_percentage / 100.0

                # Calculate the cumulative amounts for this tier
                cumulative_from = max(tier_from - previous_gross, 0.0)
                cumulative_to = tier_to - previous_gross

                # Amount applicable for this tier
                tier_amount = min(remaining_deal_gross, cumulative_to - cumulative_from)

                if tier_amount <= 0:
                    continue

                # Calculate commission for this tier
                tier_commission = (tier_amount * tier_percentage) + tier.flat_fee
                total_commission += tier_commission

                # Reduce the remaining deal gross amount
                remaining_deal_gross -= tier_amount

                # If all deal gross has been allocated, break
                if remaining_deal_gross <= 0:
                    break

            return total_commission

        else:
            raise ValidationError(_("Invalid revenue type for commission calculation."))

    # =====================
    # Onchange Methods
    # =====================
    @api.onchange("revenue_type")
    def _onchange_revenue_type(self):
        if self.revenue_type == "graduated_commission":
            self.commission_percentage = 0.0
            self.flat_fee = 0.0
        else:
            self.graduated_commission_ids = [(5, 0, 0)]  # Clear graduated commissions

    # =====================
    # Constraints
    # =====================
    @api.constrains(
        "commission_percentage", "flat_fee", "graduated_commission_ids", "revenue_type"
    )
    def _check_commission_values(self):
        for record in self:
            if record.revenue_type == "straight_commission":
                if not (0 <= record.commission_percentage <= 100):
                    raise ValidationError(
                        _("Commission percentage must be between 0 and 100.")
                    )
                if record.flat_fee < 0:
                    raise ValidationError(_("Flat fee cannot be negative."))
                if record.graduated_commission_ids:
                    raise ValidationError(
                        _(
                            "Graduated commissions should not be set for straight commission plans."
                        )
                    )
            elif record.revenue_type == "graduated_commission":
                if record.commission_percentage != 0.0:
                    raise ValidationError(
                        _(
                            "Commission percentage must be zero for graduated commission plans."
                        )
                    )
                if record.flat_fee != 0.0:
                    raise ValidationError(
                        _("Flat fee must be zero for graduated commission plans.")
                    )
                if not record.graduated_commission_ids:
                    raise ValidationError(
                        _("Please define graduated commissions for this plan.")
                    )


class CommissionPlanLine(models.Model):
    _name = "commission.plan.line"
    _description = "Commission Plan Line"
    _order = "sequence asc"

    sequence = fields.Integer(
        string="Sequence",
        default=1,
        help="Sequence of the commission plan line.",
    )
    sales_agent_line_id = fields.Many2one(
        "sales.agents.and.referrals",
        string="Sales Agent Line",
        required=True,
        ondelete="cascade",
    )
    commission_plan_id = fields.Many2one(
        "commission.plan",
        string="Commission Plan",
        required=True,
        help="Commission Plan applied to this line.",
    )
    revenue_type = fields.Selection(
        [
            ("straight_commission", "Straight Commission"),
            ("graduated_commission", "Graduated Commission"),
        ],
        string="Revenue Type",
        required=True,
    )
    commission_percentage = fields.Float(
        string="Commission %",
        help="Commission percentage for this line.",
    )
    flat_fee = fields.Float(
        string="Flat Fee ($)",
        help="Flat fee for this line.",
    )
    graduated_commission_ids = fields.One2many(
        "graduated.commission.line",
        "commission_plan_line_id",
        string="Graduated Commissions",
        help="Graduated commission tiers for this line.",
    )
    split_fees = fields.Monetary(
        string="Splits & Fees",
        compute="_compute_split_fees",
        store=True,
        currency_field="currency_id",
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="sales_agent_line_id.currency_id",
        store=True,
        readonly=True,
    )

    @api.onchange("commission_plan_id")
    def _onchange_commission_plan_id(self):
        for rec in self:
            plan = rec.commission_plan_id
            if plan:
                rec.revenue_type = plan.revenue_type
                rec.commission_percentage = plan.commission_percentage
                rec.flat_fee = plan.flat_fee
                # Copy graduated commissions to the line
                rec.graduated_commission_ids = [(5, 0, 0)]  # Clear existing lines
                for tier in plan.graduated_commission_ids:
                    rec.graduated_commission_ids = [
                        (
                            0,
                            0,
                            {
                                "sequence": tier.sequence,
                                "commission_from": tier.commission_from,
                                "commission_to": tier.commission_to,
                                "commission_percentage": tier.commission_percentage,
                                "flat_fee": tier.flat_fee,
                                "commission_plan_line_id": rec.id,
                            },
                        )
                    ]
            else:
                # Reset fields if no commission plan is selected
                rec.revenue_type = False
                rec.commission_percentage = 0.0
                rec.flat_fee = 0.0
                rec.graduated_commission_ids = False

    @api.depends(
        "revenue_type",
        "commission_percentage",
        "flat_fee",
        "graduated_commission_ids",
        "sales_agent_line_id.gross_amount",
    )
    def _compute_split_fees(self):
        for rec in self:
            commission_amount = 0.0
            gross_amount = rec.sales_agent_line_id.gross_amount

            if rec.revenue_type == "straight_commission":
                commission_amount = (
                    gross_amount * rec.commission_percentage / 100.0
                ) + rec.flat_fee
            elif rec.revenue_type == "graduated_commission":
                previous_gross_commissions = rec.sales_agent_line_id.sales_agent_id.get_cumulative_gross_commissions(
                    exclude_deal_id=rec.sales_agent_line_id.deal_id.id
                )
                deal_gross_commission = gross_amount
                commission_amount = rec._compute_graduated_commission(
                    previous_gross_commissions, deal_gross_commission
                )
            rec.split_fees = commission_amount

    def _compute_graduated_commission(self, previous_gross, deal_gross):
        """
        Calculate the commission amount based on the line's graduated commission tiers.
        """
        self.ensure_one()
        total_commission = 0.0
        remaining_deal_gross = deal_gross

        graduated_commissions = self.graduated_commission_ids.sorted("commission_from")

        for tier in graduated_commissions:
            tier_from = tier.commission_from
            tier_to = tier.commission_to
            tier_percentage = tier.commission_percentage / 100.0

            cumulative_from = max(tier_from - previous_gross, 0.0)
            cumulative_to = tier_to - previous_gross

            tier_amount = min(remaining_deal_gross, cumulative_to - cumulative_from)

            if tier_amount <= 0:
                continue

            tier_commission = (tier_amount * tier_percentage) + tier.flat_fee
            total_commission += tier_commission

            remaining_deal_gross -= tier_amount

            if remaining_deal_gross <= 0:
                break

        return total_commission