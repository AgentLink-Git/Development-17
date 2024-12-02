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

    team_id = fields.Many2one("sales.agent.team", string="Select Team", required=True, domain=[("active", "=", True)])
    target_type = fields.Selection([("deal", "Deal"), ("listing", "Listing")], string="Apply To", required=True)
    deal_id = fields.Many2one("deal.records", string="Deal", domain=[("is_active", "=", True)])
    listing_id = fields.Many2one("listing.records", string="Listing", domain=[("status", "not in", ["sold", "cancelled"])])
    end_id = fields.Many2one("deal.end", string="End", required=True)

    @api.onchange("target_type")
    def _onchange_target_type(self):
        self.deal_id = False
        self.listing_id = False

    @api.constrains("deal_id", "listing_id", "target_type")
    def _check_target_selection(self):
        for rec in self:
            if rec.target_type == "deal" and not rec.deal_id:
                raise ValidationError(_("Please select a Deal to apply the team to."))
            elif rec.target_type == "listing" and not rec.listing_id:
                raise ValidationError(_("Please select a Listing to apply the team to."))

    def apply_team(self):
        self.ensure_one()
        team = self.team_id
        end = self.end_id

        if self.target_type == "deal":
            target_record = self.deal_id
            target_model_field = "deal_id"
            target_type_name = "Deal"
        elif self.target_type == "listing":
            target_record = self.listing_id
            target_model_field = "listing_id"
            target_type_name = "Listing"
        else:
            raise ValidationError(_("Invalid target type selected."))

        if not target_record:
            raise ValidationError(_("Please select a %s to apply the team to.") % target_type_name)

        domain = [
            (target_model_field, "=", target_record.id),
            ("end_id", "=", end.id),
        ]
        existing_percentage = sum(
            self.env["sales.agents.and.referrals"]
            .search(domain)
            .mapped("percentage_of_end")
        )

        total_percentage_to_add = sum(
            member.percentage for member in team.team_member_ids
        )
        if existing_percentage + total_percentage_to_add > 100:
            raise ValidationError(
                _("Applying this team will exceed the total commission percentage for the selected %s and end.") % target_type_name
            )

        referrals = []
        for member in team.team_member_ids:
            referrals.append(
                {
                    "partner_id": member.partner_id.id,
                    target_model_field: target_record.id,
                    "end_id": end.id,
                    "payment_type": "agent",
                    "sales_agent_id": member.partner_id.id,
                    "percentage_of_end": member.percentage,
                }
            )

        self.env["sales.agents.and.referrals"].create(referrals)
        _logger.info(
            "Applied team '%s' to %s ID: %s with total percentage: %s",
            team.name,
            target_type_name,
            target_record.id,
            total_percentage_to_add,
        )

        return {"type": "ir.actions.act_window_close"}

class SalesAgentTeam(models.Model):
    _name = "sales.agent.team"
    _description = "Sales Agent Team"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    name = fields.Char(string="Team Name", required=True, tracking=True)
    team_member_ids = fields.One2many("sales.agent.team.member", "team_id", string="Team Members", tracking=True)
    active = fields.Boolean(string="Active", default=True, tracking=True)

    @api.constrains("team_member_ids")
    def _check_total_percentage(self):
        for team in self:
            total = sum(member.percentage for member in team.team_member_ids)
            if total != 100:
                raise ValidationError(
                    _("The total commission percentage for team '%s' must equal 100%%.")
                    % team.name
                )


class SalesAgentTeamMember(models.Model):
    _name = "sales.agent.team.member"
    _description = "Sales Agent Team Member"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    team_id = fields.Many2one(
        "sales.agent.teams",
        string="Team",
        ondelete="cascade",
        required=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Sales Agent",
        domain=[("is_sales_agent", "=", True)],
        required=True,
    )
    percentage = fields.Float(string="Commission Percentage", required=True)

    @api.constrains("percentage")
    def _check_percentage(self):
        for record in self:
            if not (0 < record.percentage <= 100):
                raise ValidationError(
                    _(
                        "Commission percentage must be greater than 0 and less than or equal to 100."
                    )
                )