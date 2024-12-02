# /models/law_firms/lawyer.py

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

class Lawyer(models.Model):
    _name = "lawyer"
    _description = "Law Firm's Lawyer Contact"
    _inherits = {'res.partner': 'partner_id'}
    _inherit = ["mail.thread", "mail.activity.mixin", "notification.mixin"]
    _rec_name = "id"

    # Inherited Partner
    partner_id = fields.Many2one(
        'res.partner',
        string='Lawyer',
        required=True,
        ondelete='cascade',
        domain=[('is_lawyer', '=', True)],
        tracking=True
    )
    # Status for this deal
    active_status = fields.Selection(
        [("active", "Active"), ("archived", "Archived")],
        default="active",
        string="Active Lawyer",
        tracking=True,
    )
    # Relationships
    law_firm_id = fields.Many2one(
        "law.firm",
        string="Law Firm",
        required=True,
        ondelete="cascade",
        tracking=True,
    )
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        domain=[("is_active", "=", True)],
        required=True,
        ondelete="cascade",
        tracking=True,
    )

    # Constraints
    @api.constrains('partner_id.name', 'law_firm_id')
    def _check_duplicate_lawyer(self):
        """Ensure that a lawyer contact does not appear multiple times within the same law firm."""
        for rec in self:
            if self._is_duplicate_lawyer(rec):
                raise ValidationError(
                    _('The contact "%s" is already a lawyer in the "%s" law firm. Please review existing entries before adding a new one.')
                    % (rec.partner_id.name, rec.law_firm_id.partner_id.name)
                )

    def _is_duplicate_lawyer(self, record):
        """Helper method to check for duplicate lawyers within the same law firm."""
        existing = self.search([
            ('partner_id.name', '=', record.partner_id.name),
            ('law_firm_id', '=', record.law_firm_id.id),
            ('id', '!=', record.id),
        ])
        return bool(existing)

    # Override Create Method
    @api.model
    def create(self, vals):
        """Create a lawyer contact and update partner attributes to classify as lawyer."""
        res = super(Lawyer, self).create(vals)
        res._update_partner_to_lawyer()
        return res

    # Override Write Method
    def write(self, vals):
        """Update the lawyer record and ensure partner attributes reflect lawyer classification."""
        res = super(Lawyer, self).write(vals)
        for rec in self:
            rec._update_partner_to_lawyer()
        return res

    def _update_partner_to_lawyer(self):
        """Update the partner's attributes to classify as a lawyer under the specific law firm."""
        self.partner_id.write({
            "is_company": False,
            "is_lawyer": True,
            "parent_id": self.law_firm_id.partner_id.id,
        })
        _logger.info("Updated partner %s to lawyer under law firm %s", self.partner_id.name, self.law_firm_id.partner_id.name)

    # Name Get and Name Search Methods
    def name_get(self):
        """Customize display name to show lawyer's partner name."""
        return [(rec.id, rec.partner_id.name or "Lawyer") for rec in self]

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """Enable searching by partner name or parent partner name for easier navigation."""
        args = args or []
        if name:
            partner_ids = self._get_partner_ids_by_name(name, operator)
            args += [("partner_id", "in", partner_ids)]
        records = self.search(args, limit=limit)
        return records.name_get()

    def _get_partner_ids_by_name(self, name, operator):
        """Helper method to fetch partner IDs by name for name_search."""
        return self.env["res.partner"].search(
            ["|", ("name", operator, name), ("parent_id.name", operator, name)]
        ).ids