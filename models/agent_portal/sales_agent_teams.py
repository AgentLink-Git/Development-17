# models/agent_portal/sales_agent_teams.py

"""
Module for managing Sales Agent Teams.
Defines SalesAgentTeamWizard, SalesAgentTeams, and SalesAgentTeamMember models
to handle the creation and application of sales agent teams to deals or listings,
ensuring proper commission distributions and data integrity through validations.
"""

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class SalesAgentTeamWizard(models.TransientModel):
    _name = "sales.agent.team.wizard"
    _description = "Sales Agent Team Wizard"

    team_id = fields.Many2one(
        "sales.agent.teams",
        string="Select Team",
        required=True,
        domain=[("active", "=", True)],
        help="Select an active team to apply."
    )
    target_type = fields.Selection(
        [("deal", "Deal"), ("listing", "Listing")],
        string="Apply To",
        required=True,
        help="Choose whether to apply the team to a Deal or Listing."
    )
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        domain=[("is_active", "=", True)],
        help="Select the Deal to apply the team to."
    )
    listing_id = fields.Many2one(
        "listing.records",
        string="Listing",
        domain=[("status", "not in", ["sold", "cancelled"])],
        help="Select the Listing to apply the team to."
    )
    end_id = fields.Many2one(
        "deal.end",
        string="End",
        required=True,
        help="Select the End associated with the Deal or Listing."
    )

    @api.onchange('target_type')
    def _onchange_target_type(self):
        """Reset target fields based on selected target type."""
        if self.target_type == 'deal':
            self.listing_id = False
        elif self.target_type == 'listing':
            self.deal_id = False

    @api.constrains("deal_id", "listing_id", "target_type")
    def _check_target_selection(self):
        """Ensure that the appropriate target is selected based on target type."""
        for rec in self:
            if rec.target_type == 'deal' and not rec.deal_id:
                raise ValidationError(_("Please select a Deal to apply the team to."))
            elif rec.target_type == 'listing' and not rec.listing_id:
                raise ValidationError(_("Please select a Listing to apply the team to."))

    def apply_team(self):
        """
        Apply the selected team to the chosen deal or listing.
        Ensures that total commission percentages do not exceed 100%.
        """
        self.ensure_one()
        team = self.team_id
        end = self.end_id

        # Determine target record and related field
        if self.target_type == 'deal':
            target_record = self.deal_id
            target_field = 'deal_id'
            target_name = 'Deal'
        elif self.target_type == 'listing':
            target_record = self.listing_id
            target_field = 'listing_id'
            target_name = 'Listing'
        else:
            raise ValidationError(_("Invalid target type selected."))

        if not target_record:
            raise ValidationError(_("Please select a %s to apply the team to.") % target_name)

        # Calculate existing and new commission percentages
        domain = [
            (target_field, '=', target_record.id),
            ("end_id", "=", end.id),
        ]
        existing_percentage = sum(
            self.env["sales.agents.and.referrals"].search(domain).mapped("percentage_of_end")
        )
        new_percentage = sum(member.percentage for member in team.team_member_ids)

        if existing_percentage + new_percentage > 100:
            raise ValidationError(
                _("Applying this team will exceed the total commission percentage for the selected %s and end.") % target_name
            )

        # Prepare and create referral records
        referrals = [
            {
                "partner_id": member.partner_id.id,
                target_field: target_record.id,
                "end_id": end.id,
                "payment_type": "agent",
                "sales_agent_id": member.partner_id.id,
                "percentage_of_end": member.percentage,
            }
            for member in team.team_member_ids
        ]
        self.env["sales.agents.and.referrals"].create(referrals)

        _logger.info(
            "Applied team '%s' to %s ID: %s with total percentage: %s",
            team.name,
            target_name,
            target_record.id,
            new_percentage,
        )

        return {"type": "ir.actions.act_window_close"}


class SalesAgentTeams(models.Model):
    _name = "sales.agent.teams"
    _description = "Sales Agent Teams"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Team Name", required=True, tracking=True, help="Name of the sales agent team.")
    team_member_ids = fields.One2many(
        "sales.agent.team.member",
        "team_id",
        string="Team Members",
        tracking=True,
        help="Members of the sales agent team."
    )
    active = fields.Boolean(string="Active", default=True, tracking=True, help="Indicates if the team is active.")

    @api.constrains("team_member_ids")
    def _check_total_percentage(self):
        """Ensure that the total commission percentage of team members equals 100%."""
        for team in self:
            total = sum(member.percentage for member in team.team_member_ids)
            if total != 100:
                raise ValidationError(
                    _("The total commission percentage for team '%s' must equal 100%%.") % team.name
                )

    @api.constrains("team_member_ids")
    def _check_team_members(self):
        """Ensure that the team has at least one member."""
        for team in self:
            if not team.team_member_ids:
                raise ValidationError(_("The team '%s' must have at least one team member.") % team.name)


class SalesAgentTeamMember(models.Model):
    _name = "sales.agent.team.member"
    _description = "Sales Agent Team Member"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _sql_constraints = [
        ('unique_team_member', 'unique(team_id, partner_id)', 'A Sales Agent cannot be added multiple times to the same team.'),
    ]

    team_id = fields.Many2one(
        "sales.agent.teams",
        string="Team",
        ondelete="cascade",
        required=True,
        help="Associated sales agent team."
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Sales Agent",
        domain=[("is_sales_agent", "=", True)],
        required=True,
        help="Sales agent to be added to the team."
    )
    percentage = fields.Float(
        string="Commission Percentage",
        required=True,
        help="Commission percentage allocated to this team member."
    )

    @api.constrains("percentage")
    def _check_percentage(self):
        """Ensure that the commission percentage is between 0 and 100."""
        for record in self:
            if not (0 < record.percentage <= 100):
                raise ValidationError(
                    _("Commission percentage must be greater than 0 and less than or equal to 100.")
                )