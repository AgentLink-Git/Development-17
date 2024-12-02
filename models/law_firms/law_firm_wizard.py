# models/law_firms/law_firm_wizard.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError

class LawFirmWizard(models.TransientModel):
    _name = "law.firm.wizard"
    _description = "Law Firm Wizard"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    deal_id = fields.Many2one("deal.records", string="Deal", required=True)
    end_id = fields.Many2one("deal.end", string="End", required=True)
    action_type = fields.Selection(
        [
            ("add", "Add Law Firm"),
            ("archive", "Archive Law Firm"),
        ],
        string="Action",
        required=True,
        default="add",
    )

    # Fields for adding a new law firm
    partner_id = fields.Many2one(
        "res.partner",
        string="Law Firm",
        domain="[('is_company', '=', True), ('is_law_firm', '=', True)]",
    )
    create_new = fields.Boolean(string="Create New Law Firm")
    name = fields.Char(string="Law Firm Name")

    # Fields for managing associated lawyers
    lawyer_ids = fields.Many2many(
        "res.partner",
        string="Lawyers",
        domain="[('is_lawyer', '=', True)]",
        help="Select lawyers to associate with this law firm for this deal.",
    )
    create_new_lawyer = fields.Boolean(string="Create New Lawyer")
    new_lawyer_name = fields.Char(string="New Lawyer Name")
    new_lawyer_email = fields.Char(string="New Lawyer Email")
    
    def action_execute(self):
        """Execute the action based on the selection to add or archive a law firm."""
        self.ensure_one()
        if self.action_type == "add":
            self._action_add_law_firm()
        elif self.action_type == "archive":
            self._action_archive_law_firm()
        return {"type": "ir.actions.act_window_close"}

    def _action_add_law_firm(self):
        """Handle the addition of a law firm, creating a new one if necessary."""
        partner = self._get_or_create_partner()

        # Archive existing active law firm and remove archived firms for this end in the deal
        self._archive_existing_firms()

        # Create new law firm record for this deal and mark as active
        law_firm = self.env["law.firm"].create({
            "partner_id": partner.id,
            "deal_id": self.deal_id.id,
            "end_id": self.end_id.id,
            "active_status": "active",
        })

        # Add or link selected lawyers to the new law firm for this deal
        self._add_lawyers_to_firm(law_firm)

    def _get_or_create_partner(self):
        """Retrieve or create a law firm partner."""
        if self.create_new:
            if not self.name:
                raise UserError(_("Please provide a name for the new law firm."))
            return self.env["res.partner"].create({
                "name": self.name,
                "is_company": True,
                "is_law_firm": True,
                "company_id": self.env.company.id,
                "country_id": self.env.ref("base.ca").id,  # Default to Canada
            })
        elif self.partner_id:
            return self.partner_id
        else:
            raise UserError(_("Please select an existing law firm or choose to create a new one."))

    def _archive_existing_firms(self):
        """Archive any existing active law firm and delete archived law firms for this deal and end."""
        active_firm = self._get_active_law_firm()
        if active_firm:
            active_firm.write({"active_status": "archived"})
        archived_firms = self._get_archived_law_firms()
        if archived_firms:
            archived_firms.unlink()

    def _get_active_law_firm(self):
        """Retrieve the currently active law firm for this deal and end."""
        return self.env["law.firm"].search([
            ("deal_id", "=", self.deal_id.id),
            ("end_id", "=", self.end_id.id),
            ("active_status", "=", "active"),
        ], limit=1)

    def _get_archived_law_firms(self):
        """Retrieve any archived law firms for this deal and end."""
        return self.env["law.firm"].search([
            ("deal_id", "=", self.deal_id.id),
            ("end_id", "=", self.end_id.id),
            ("active_status", "=", "archived"),
        ])

    def _add_lawyers_to_firm(self, law_firm):
        """Add or create lawyers associated with the law firm for this deal."""
        lawyer_records = []
        if self.create_new_lawyer:
            if not self.new_lawyer_name:
                raise UserError(_("Please provide a name for the new lawyer."))
            new_lawyer = self.env["res.partner"].create({
                "name": self.new_lawyer_name,
                "email": self.new_lawyer_email,
                "is_lawyer": True,
                "parent_id": law_firm.partner_id.id,
                "company_id": self.env.company.id,
            })
            lawyer_records.append(new_lawyer)
        else:
            lawyer_records.extend(self.lawyer_ids)

        # Link lawyers to the law firm specifically for this deal
        for lawyer in lawyer_records:
            self.env["lawyer"].create({
                "partner_id": lawyer.id,
                "law_firm_id": law_firm.id,
                "deal_id": self.deal_id.id,
                "active_status": "active",
            })

    def _action_archive_law_firm(self):
        """Archive the currently active law firm and its lawyers for this end in the deal."""
        active_firm = self._get_active_law_firm()
        if not active_firm:
            raise UserError(_("There is no active law firm to archive for this end."))
        active_firm.write({"active_status": "archived"})
        
        # Archive lawyers associated with the law firm in the context of this deal
        active_firm.lawyer_ids.filtered(lambda l: l.deal_id == self.deal_id).write({"active_status": "archived"})