# models/agent_portal/sales_agent_mentorship.py

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date


class SalesAgentMentorshipWizard(models.TransientModel):
    _name = "sales.agent.mentorship.wizard"
    _description = "Sales Agent Mentorship Wizard"

    mentorship_id = fields.Many2one(
        "sales.agent.mentorship",
        string="Select Mentorship",
        required=True,
        domain=[("active", "=", True)],
    )
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        required=True,
    )
    end_id = fields.Many2one(
        "deal.end",
        string="End",
        required=True,
    )

    def apply_mentorship_to_deal(self):
        """
        Apply the selected mentorship to the specified deal.
        """
        self.ensure_one()
        mentorship = self.mentorship_id
        deal = self.deal_id
        end = self.end_id

        if not mentorship.active:
            raise ValidationError(_("The selected mentorship is not active."))

        if end.type not in ["buyer", "seller", "landlord", "tenant"]:
            raise ValidationError(_("Invalid deal end type for mentorship."))

        if (
            mentorship.deal_class_ids
            and deal.deal_class_id not in mentorship.deal_class_ids
        ):
            raise ValidationError(
                _("This mentorship does not apply to the selected deal's class.")
            )

        # Check if mentee has hit their commission cap
        mentee_commissions = mentorship.mentee_id.sales_agent_commission_ids.filtered(
            lambda c: c.active
        )
        if any(c.sales_agent_hit_cap for c in mentee_commissions):
            raise ValidationError(
                _("The mentee has hit their commission cap. Cannot apply mentorship.")
            )

        # Calculate company portion and mentor share
        if not deal.amount_payable or not deal.split_fees:
            raise ValidationError(
                _("Deal amount payable or split fees are not properly set.")
            )

        company_portion = deal.amount_payable * (deal.split_fees / 100.0)
        mentor_share = company_portion * (mentorship.mentorship_percentage / 100.0)

        if (
            mentorship.annual_cap
            and (mentorship.yearly_paid + mentor_share) > mentorship.annual_cap
        ):
            raise ValidationError(
                _("Applying this mentorship would exceed the mentor's annual cap.")
            )

        if (
            mentorship.lifetime_cap
            and (mentorship.total_paid + mentor_share) > mentorship.lifetime_cap
        ):
            raise ValidationError(
                _("Applying this mentorship would exceed the mentor's lifetime cap.")
            )

        existing_line = self.env["sales.agent.mentorship.line"].search(
            [("mentorship_id", "=", mentorship.id), ("deal_id", "=", deal.id)],
            limit=1,
        )
        if existing_line:
            raise ValidationError(
                _("This mentorship has already been applied to the selected deal.")
            )

        mentor_commission = mentorship.mentor_commission_id
        if not mentor_commission or not mentor_commission.active:
            raise ValidationError(
                _("Mentor does not have an active commission record.")
            )

        if (
            mentor_commission.commission_cap
            and (mentor_commission.commission_earned + mentor_share)
            > mentor_commission.commission_cap
        ):
            raise ValidationError(
                _("Applying this mentorship would exceed the mentor's commission cap.")
            )

        # Create mentorship line (computed fields will calculate shares)
        mentorship_line = self.env["sales.agent.mentorship.line"].create(
            {
                "mentorship_id": mentorship.id,
                "deal_id": deal.id,
            }
        )

        mentorship._check_and_end_mentorship()
        mentor_commission.commission_earned += mentor_share

        # Link the mentorship line to the deal if the field exists
        if hasattr(deal, "mentorship_line_ids"):
            deal.mentorship_line_ids = [(4, mentorship_line.id)]

        return {"type": "ir.actions.act_window_close"}


class SalesAgentMentorship(models.Model):
    _name = "sales.agent.mentorship"
    _description = "Sales Agent Mentorship"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    mentor_id = fields.Many2one(
        "res.partner",
        string="Mentor",
        domain=[("is_sales_agent", "=", True)],
        required=True,
        tracking=True,
    )
    mentee_id = fields.Many2one(
        "res.partner",
        string="Mentee",
        domain=[("is_sales_agent", "=", True)],
        required=True,
        tracking=True,
    )
    mentorship_percentage = fields.Float(
        string="Mentorship Percentage",
        required=True,
        help="Percentage of the company's portion to be allocated to the mentor.",
        tracking=True,
    )
    active = fields.Boolean(
        string="Active",
        default=True,
        tracking=True,
    )
    start_date = fields.Date(
        string="Start Date",
        default=fields.Date.context_today,
        tracking=True,
    )
    end_date = fields.Date(
        string="End Date",
        help="Optional date to automatically end the mentorship.",
        tracking=True,
    )
    annual_cap = fields.Monetary(
        string="Annual Cap",
        currency_field="currency_id",
        help="Maximum amount the mentor can receive per year.",
        tracking=True,
    )
    lifetime_cap = fields.Monetary(
        string="Lifetime Cap",
        currency_field="currency_id",
        help="Maximum total amount the mentor can receive throughout the mentorship.",
        tracking=True,
    )
    deal_class_ids = fields.Many2many(
        "deal.class",
        string="Applicable Deal Classes",
        help="Only deals belonging to these classes will incur mentorship fees.",
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="mentor_id.currency_id",
        string="Currency",
        readonly=True,
        store=True,
    )
    total_paid = fields.Monetary(
        string="Total Paid",
        compute="_compute_total_paid",
        store=True,
        currency_field="currency_id",
    )
    yearly_paid = fields.Monetary(
        string="Yearly Paid",
        compute="_compute_yearly_paid",
        store=True,
        currency_field="currency_id",
    )
    mentorship_line_ids = fields.One2many(
        "sales.agent.mentorship.line",
        "mentorship_id",
        string="Mentorship Lines",
    )
    mentor_commission_id = fields.Many2one(
        "sales.agent.commission",
        string="Mentor Commission",
        required=True,
        ondelete="cascade",
        tracking=True,
    )

    @api.depends("mentorship_line_ids.mentor_share")
    def _compute_total_paid(self):
        for record in self:
            record.total_paid = sum(record.mentorship_line_ids.mapped("mentor_share"))

    @api.depends("mentorship_line_ids.mentor_share")
    def _compute_yearly_paid(self):
        current_year = date.today().year
        for record in self:
            yearly_lines = record.mentorship_line_ids.filtered(
                lambda l: l.deal_id.offer_date
                and l.deal_id.offer_date.year == current_year
            )
            record.yearly_paid = sum(yearly_lines.mapped("mentor_share"))

    @api.constrains("mentor_id", "mentee_id")
    def _check_unique_mentorship(self):
        for record in self:
            if record.mentor_id == record.mentee_id:
                raise ValidationError(_("A mentor cannot be the same as the mentee."))
            existing = self.search(
                [
                    ("mentor_id", "=", record.mentor_id.id),
                    ("mentee_id", "=", record.mentee_id.id),
                    ("active", "=", True),
                    ("id", "!=", record.id),
                ],
                limit=1,
            )
            if existing:
                raise ValidationError(
                    _("An active mentorship already exists between these agents.")
                )

    @api.constrains("mentorship_percentage")
    def _check_percentage_range(self):
        for record in self:
            if not (0 < record.mentorship_percentage <= 100):
                raise ValidationError(
                    _(
                        "Mentorship percentage must be greater than 0 and less than or equal to 100."
                    )
                )

    @api.constrains("annual_cap", "lifetime_cap")
    def _check_caps(self):
        for record in self:
            if record.annual_cap and record.annual_cap <= 0:
                raise ValidationError(_("Annual Cap must be greater than 0."))
            if record.lifetime_cap and record.lifetime_cap <= 0:
                raise ValidationError(_("Lifetime Cap must be greater than 0."))

    def _check_and_end_mentorship(self):
        """
        Check if the mentorship should be ended based on end date or caps.
        """
        for mentorship in self:
            if mentorship.active:
                if mentorship.end_date and fields.Date.today() >= mentorship.end_date:
                    mentorship.active = False
                elif (
                    mentorship.annual_cap
                    and mentorship.yearly_paid >= mentorship.annual_cap
                ):
                    mentorship.active = False
                elif (
                    mentorship.lifetime_cap
                    and mentorship.total_paid >= mentorship.lifetime_cap
                ):
                    mentorship.active = False

    @api.model_create_multi
    def create(self, vals_list):
        records = super(SalesAgentMentorship, self).create(vals_list)
        records._check_and_end_mentorship()
        return records

    def write(self, vals):
        res = super(SalesAgentMentorship, self).write(vals)
        self._check_and_end_mentorship()
        return res


class SalesAgentMentorshipLine(models.Model):
    _name = "sales.agent.mentorship.line"
    _description = "Sales Agent Mentorship Line"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    mentorship_id = fields.Many2one(
        "sales.agent.mentorship",
        string="Mentorship",
        ondelete="cascade",
        required=True,
    )
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        required=True,
        ondelete="cascade",
    )
    mentor_share = fields.Monetary(
        string="Mentor Share",
        compute="_compute_mentor_share",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    company_share = fields.Monetary(
        string="Company Share",
        compute="_compute_company_share",
        store=True,
        currency_field="currency_id",
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="deal_id.currency_id",
        string="Currency",
        readonly=True,
        store=True,
    )

    @api.depends(
        "deal_id.amount_payable",
        "mentorship_id.mentorship_percentage",
        "deal_id.split_fees",
    )
    def _compute_mentor_share(self):
        for line in self:
            if (
                line.deal_id.amount_payable
                and line.deal_id.split_fees
                and line.mentorship_id.mentorship_percentage
            ):
                company_portion = line.deal_id.amount_payable * (
                    line.deal_id.split_fees / 100.0
                )
                line.mentor_share = company_portion * (
                    line.mentorship_id.mentorship_percentage / 100.0
                )
            else:
                line.mentor_share = 0.0

    @api.depends("mentor_share", "deal_id.amount_payable", "deal_id.split_fees")
    def _compute_company_share(self):
        for line in self:
            if line.deal_id.amount_payable and line.deal_id.split_fees:
                company_portion = line.deal_id.amount_payable * (
                    line.deal_id.split_fees / 100.0
                )
                line.company_share = company_portion - line.mentor_share
            else:
                line.company_share = 0.0
