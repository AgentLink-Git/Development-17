# models/shared_resources/deal_class.py

from odoo import models, fields, api
from odoo.exceptions import UserError


class DealClass(models.Model):
    _name = "deal.class"
    _description = "Listing/Deal Classes"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name"
    _sql_constraints = [
        ("name_unique", "unique(name)", "The class name must be unique.")
    ]

    name = fields.Char(string="Class", required=True, tracking=True)
    no_of_ends = fields.Float(string="# Ends", default=1.0, tracking=True)
    for_sale = fields.Boolean(string="For Sale", default=False, tracking=True)
    for_lease = fields.Boolean(string="For Lease", default=False, tracking=True)
    end_id = fields.Many2one(
        "deal.end", string="We Represent", required=True, tracking=True
    )
    is_active = fields.Boolean(string="Active", default=True, tracking=True)

    # Contextual Fields
    for_sale_or_lease = fields.Selection(
        selection=[("for_sale", "For Sale"), ("for_lease", "For Lease")],
        string="Sale or Lease",
        required=True,
        default="for_sale",
        tracking=True,
    )
    deal_class_id = fields.Many2one("trade.class", string="Trade Class", tracking=True)
    listing_id = fields.Many2one("listing.record", string="Listing", tracking=True)
    deal_id = fields.Many2one("deal.records", string="Deal", tracking=True)

    @api.onchange("for_sale_or_lease", "listing_id", "deal_id")
    def _onchange_deal_class_domain(self):
        """
        Dynamically sets the domain for deal_class_id based on the deal context.
        Determines whether the context is a listing or a deal and adjusts the domain accordingly.
        """
        domain = []

        # Determine if the record is associated with a listing or a deal
        is_listing = bool(self.listing_id)
        is_deal = bool(self.deal_id)

        if not is_listing and not is_deal:
            # If neither listing nor deal is set, no domain restrictions
            return {"domain": {"deal_class_id": []}}

        # Determine the type based on sale or lease
        if self.for_sale_or_lease == "for_sale":
            if is_listing:
                # For sellers in listings
                domain = [
                    ("deal_end_id.type", "in", ["seller", "double_end"]),
                    ("for_sale", "=", True),
                ]
            else:
                # For buyers in deals
                domain = [("deal_end_id.type", "=", "buyer"), ("for_sale", "=", True)]
        elif self.for_sale_or_lease == "for_lease":
            if is_listing:
                # For landlords in listings
                domain = [
                    ("deal_end_id.type", "in", ["landlord", "double_end"]),
                    ("for_lease", "=", True),
                ]
            else:
                # For tenants in deals
                domain = [("deal_end_id.type", "=", "tenant"), ("for_lease", "=", True)]
        else:
            # Default domain if neither sale nor lease is selected
            domain = []

        # Set the domain for deal_class_id field
        return {"domain": {"deal_class_id": domain}}

    @api.constrains("for_sale", "for_lease")
    def _check_sale_or_lease(self):
        """
        Ensure that a DealClass cannot be both for sale and for lease simultaneously.
        """
        for record in self:
            if record.for_sale and record.for_lease:
                raise UserError(
                    "A Deal Class cannot be marked as both For Sale and For Lease."
                )

    @api.model
    def create(self, vals):
        """
        Override the create method to ensure that either for_sale or for_lease is set.
        """
        if not vals.get("for_sale") and not vals.get("for_lease"):
            raise UserError(
                "Please specify whether the Deal Class is for Sale or for Lease."
            )
        return super(DealClass, self).create(vals)

    def write(self, vals):
        """
        Override the write method to ensure that either for_sale or for_lease is set.
        """
        if "for_sale" in vals or "for_lease" in vals:
            for record in self:
                for_sale = vals.get("for_sale", record.for_sale)
                for_lease = vals.get("for_lease", record.for_lease)
                if for_sale and for_lease:
                    raise UserError(
                        "A Deal Class cannot be marked as both For Sale and For Lease."
                    )
                if not for_sale and not for_lease:
                    raise UserError(
                        "Please specify whether the Deal Class is for Sale or for Lease."
                    )
        return super(DealClass, self).write(vals)
