# models/buyers_sellers/buyers_sellers_wizard.py

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class BuyersSellersWizard(models.TransientModel):
    _name = "buyers.sellers.wizard"
    _description = "Wizard to Create Buyers and Sellers"

    # =====================
    # Fields
    # =====================
    line_ids = fields.One2many(
        "buyers.sellers.wizard.line",
        "wizard_id",
        string="Buyers/Sellers Entries",
        required=True,
        copy=True,
    )

    # Action to create Buyers/Sellers records
    def action_create_buyers_sellers(self):
        """
        Create Buyers/Sellers records from the wizard lines.
        """
        self.ensure_one()

        if not self.line_ids:
            raise UserError(
                _("Please add at least one Buyers/Sellers entry to proceed.")
            )

        created_records = self.env["buyers.sellers"]

        for line in self.line_ids:
            # Validate buyer_seller_type consistency
            if line.for_sale_or_lease == "for_sale" and line.buyer_seller_type not in [
                "buyer",
                "seller",
            ]:
                raise ValidationError(
                    _("For Sale must be associated with Buyer or Seller type.")
                )
            if (
                line.for_sale_or_lease == "for_lease"
                and line.buyer_seller_type not in ["tenant", "landlord"]
            ):
                raise ValidationError(
                    _("For Lease must be associated with Tenant or Landlord type.")
                )

            # Check if partner already exists
            partner = self.env["res.partner"].search(
                [("name", "=", line.partner_name)], limit=1
            )
            if not partner:
                # Create the res.partner record
                partner_vals = {
                    "name": line.partner_name,
                    "email": line.partner_email,
                    "phone": line.partner_phone,
                    "street": line.partner_street,
                    "street2": line.partner_street2,
                    "city": line.partner_city,
                    "state_id": line.partner_state_id.id,
                    "zip": line.partner_zip,
                    "country_id": line.partner_country_id.id,
                    "is_buyer_seller": True,  # Ensure this field exists in res.partner
                    "comment": line.notes,
                }
                partner = self.env["res.partner"].create(partner_vals)
            else:
                # Update existing partner with new info
                partner.write(
                    {
                        "email": line.partner_email,
                        "phone": line.partner_phone,
                        "street": line.partner_street,
                        "street2": line.partner_street2,
                        "city": line.partner_city,
                        "state_id": line.partner_state_id.id,
                        "zip": line.partner_zip,
                        "country_id": line.partner_country_id.id,
                        "comment": line.notes,
                        "is_buyer_seller": True,
                    }
                )

            # Prepare values for Buyers/Sellers record
            buyers_sellers_vals = {
                "partner_id": partner.id,
                "end_id": line.end_id.id,
                "deal_id": line.deal_id.id if line.deal_id else False,
                "listing_id": line.listing_id.id if line.listing_id else False,
                "notes": line.notes,
                "company_id": self.env.company.id,
                "copy_address": False,  # Default value, adjust if needed
            }

            # Create the Buyers/Sellers record
            buyers_sellers = self.env["buyers.sellers"].create(buyers_sellers_vals)
            created_records += buyers_sellers

        if created_records:
            action = self.env.ref("your_module.action_buyers_sellers_form").read()[0]
            if len(created_records) == 1:
                action["res_id"] = created_records.id
                action["view_mode"] = "form"
            else:
                action["domain"] = [("id", "in", created_records.ids)]
                action["view_mode"] = "tree,form"
            return action
        else:
            raise UserError(_("No Buyers/Sellers records were created."))


class BuyersSellersWizardLine(models.TransientModel):
    _name = "buyers.sellers.wizard.line"
    _description = "Wizard Line for Buyers and Sellers"

    # =====================
    # Fields
    # =====================
    wizard_id = fields.Many2one(
        "buyers.sellers.wizard",
        string="Wizard",
        ondelete="cascade",
        required=True,
    )

    # Partner Information
    partner_name = fields.Char(string="Contact Name", required=True)
    partner_email = fields.Char(string="Email")
    partner_phone = fields.Char(string="Phone")
    partner_street = fields.Char(string="Street")
    partner_street2 = fields.Char(string="Street2")
    partner_city = fields.Char(string="City")
    partner_state_id = fields.Many2one("res.country.state", string="State")
    partner_zip = fields.Char(string="Zip")
    partner_country_id = fields.Many2one("res.country", string="Country")

    # Buyers/Sellers Specific Fields
    end_id = fields.Many2one(
        "deal.end",
        string="Role",
        required=True,
    )
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        required=True,
        ondelete="cascade",
    )
    listing_id = fields.Many2one(
        "listing.records",
        string="Listing",
        ondelete="cascade",
    )
    for_sale_or_lease = fields.Selection(
        [("for_sale", "For Sale"), ("for_lease", "For Lease")],
        string="For Sale or Lease",
        required=True,
    )
    buyer_seller_type = fields.Selection(
        [
            ("buyer", "Buyer"),
            ("seller", "Seller"),
            ("tenant", "Tenant"),
            ("landlord", "Landlord"),
        ],
        string="Type",
        required=True,
    )
    notes = fields.Html(string="Notes")

    # =====================
    # Constraints
    # =====================

    @api.constrains("buyer_seller_type", "for_sale_or_lease")
    def _check_type_consistency(self):
        for rec in self:
            if rec.for_sale_or_lease == "for_sale" and rec.buyer_seller_type not in [
                "buyer",
                "seller",
            ]:
                raise ValidationError(
                    _("For Sale must be associated with Buyer or Seller type.")
                )
            if rec.for_sale_or_lease == "for_lease" and rec.buyer_seller_type not in [
                "tenant",
                "landlord",
            ]:
                raise ValidationError(
                    _("For Lease must be associated with Tenant or Landlord type.")
                )

    @api.constrains("deal_id", "listing_id")
    def _check_deal_or_listing(self):
        for rec in self:
            if not rec.deal_id and not rec.listing_id:
                raise ValidationError(_("You must select either a Deal or a Listing."))

    # =====================
    # Onchange Methods
    # =====================

    @api.onchange("for_sale_or_lease")
    def _onchange_for_sale_or_lease(self):
        if self.for_sale_or_lease == "for_sale":
            return {
                "domain": {"buyer_seller_type": [("key", "in", ["buyer", "seller"])]}
            }
        elif self.for_sale_or_lease == "for_lease":
            return {
                "domain": {"buyer_seller_type": [("key", "in", ["tenant", "landlord"])]}
            }
        else:
            return {"domain": {"buyer_seller_type": []}}

    @api.onchange("deal_id")
    def _onchange_deal_id(self):
        if self.deal_id:
            self.listing_id = False  # Clear listing if deal is selected

    @api.onchange("listing_id")
    def _onchange_listing_id(self):
        if self.listing_id:
            self.deal_id = False  # Clear deal if listing is selected
