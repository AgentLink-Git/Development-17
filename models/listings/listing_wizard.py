# models/listings/listing_wizard.py

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ListingWizard(models.TransientModel):
    _name = "listing.wizard"
    _description = "Listing Wizard"

    # Basic Information
    name = fields.Char(string="Listing Name", required=True)
    listing_number = fields.Char(string="Listing #", readonly=True)
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        string="Currency",
        readonly=True,
    )

    # Address & Legal Description
    suite_number = fields.Char(string="Suite/Unit Number")
    street_number = fields.Char(string="Street Number")
    street_name = fields.Char(string="Street Name")
    street_type_id = fields.Many2one("street.type", string="Street Type")
    street_direction_prefix = fields.Char(string="Street Direction Prefix")
    street_direction_suffix = fields.Char(string="Street Direction Suffix")
    city_id = fields.Many2one("res.city", string="City")
    state_id = fields.Many2one("res.country.state", string="State")
    country_id = fields.Many2one("res.country", string="Country")
    postal_code = fields.Char(string="Postal Code")
    legal_plan = fields.Char(string="Legal Plan")
    legal_block = fields.Char(string="Legal Block")
    legal_lot = fields.Char(string="Legal Lot")
    legal_long = fields.Char(string="Legal Long Description")

    # Representation (End)
    end_id = fields.Many2one("deal.end", string="We Represent", required=True)

    # Price and Date Fields
    list_price = fields.Monetary(
        string="List Price",
        currency_field="currency_id",
        required=True,
        help="List price of the property",
    )
    sell_price = fields.Monetary(
        string="Sell Price",
        currency_field="currency_id",
        help="Selling price of the property",
    )
    list_date = fields.Date(string="List Date", required=True)
    expiry_date = fields.Date(string="Expiry Date", required=True)
    cancel_date = fields.Date(string="Cancel Date")
    offer_date = fields.Date(string="Offer Date", required=True)

    # Property Details
    deal_class_id = fields.Many2one(
        "deal.class",
        string="Class",
        domain="[('is_active','=',True)]",
        required=True,
    )
    property_type_id = fields.Many2one(
        "property.type",
        string="Property Type",
        domain="[('is_active', '=', True)]",
        required=True,
    )
    size = fields.Char(string="Size (Sq Ft/Sq M)")
    ml_number = fields.Char(string="ML Number")
    business_source_id = fields.Many2one(
        "business.source",
        string="Business Source",
        domain="[('is_active', '=', True)]",
    )
    for_sale_or_lease = fields.Selection(
        [("for_sale", "For Sale"), ("for_lease", "For Lease")],
        default="for_sale",
        string="For Sale or Lease",
        required=True,
    )
    notes = fields.Html(string="Notes")

    # Status
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("expired", "Expired"),
            ("sold", "Sold"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        default="draft",
        required=True,
    )

    # Existing Listing (for editing)
    listing_id = fields.Many2one("listing.records", string="Listing", readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super(ListingWizard, self).default_get(fields_list)
        listing_id = self.env.context.get("active_id")
        if listing_id:
            listing = self.env["listing.records"].browse(listing_id)
            res.update(
                {
                    "listing_id": listing.id,
                    "name": listing.name,
                    "listing_number": listing.listing_number,
                    "company_id": listing.company_id.id,
                    "suite_number": listing.suite_number,
                    "street_number": listing.street_number,
                    "street_name": listing.street_name,
                    "street_type_id": listing.street_type_id.id,
                    "street_direction_prefix": listing.street_direction_prefix,
                    "street_direction_suffix": listing.street_direction_suffix,
                    "city_id": listing.city_id.id,
                    "state_id": listing.state_id.id,
                    "country_id": listing.country_id.id,
                    "postal_code": listing.postal_code,
                    "legal_plan": listing.legal_plan,
                    "legal_block": listing.legal_block,
                    "legal_lot": listing.legal_lot,
                    "legal_long": listing.legal_long,
                    "end_id": listing.end_id.id,
                    "list_price": listing.list_price,
                    "sell_price": listing.sell_price,
                    "list_date": listing.list_date,
                    "expiry_date": listing.expiry_date,
                    "cancel_date": listing.cancel_date,
                    "offer_date": listing.offer_date,
                    "deal_class_id": listing.deal_class_id.id,
                    "property_type_id": listing.property_type_id.id,
                    "size": listing.size,
                    "ml_number": listing.ml_number,
                    "business_source_id": listing.business_source_id.id,
                    "for_sale_or_lease": listing.for_sale_or_lease,
                    "notes": listing.notes,
                    "status": listing.status,
                }
            )
        else:
            res.update(
                {
                    "status": "draft",
                }
            )
        return res

    def action_create_or_update_listing(self):
        self.ensure_one()
        vals = {
            "name": self.name,
            "company_id": self.company_id.id,
            "suite_number": self.suite_number,
            "street_number": self.street_number,
            "street_name": self.street_name,
            "street_type_id": self.street_type_id.id,
            "street_direction_prefix": self.street_direction_prefix,
            "street_direction_suffix": self.street_direction_suffix,
            "city_id": self.city_id.id,
            "state_id": self.state_id.id,
            "country_id": self.country_id.id,
            "postal_code": self.postal_code,
            "legal_plan": self.legal_plan,
            "legal_block": self.legal_block,
            "legal_lot": self.legal_lot,
            "legal_long": self.legal_long,
            "end_id": self.end_id.id,
            "list_price": self.list_price,
            "sell_price": self.sell_price,
            "list_date": self.list_date,
            "expiry_date": self.expiry_date,
            "cancel_date": self.cancel_date,
            "offer_date": self.offer_date,
            "deal_class_id": self.deal_class_id.id,
            "property_type_id": self.property_type_id.id,
            "size": self.size,
            "ml_number": self.ml_number,
            "business_source_id": self.business_source_id.id,
            "for_sale_or_lease": self.for_sale_or_lease,
            "notes": self.notes,
            "status": self.status,
        }

        if self.listing_id:
            # Update existing listing
            self.listing_id.write(vals)
            listing = self.listing_id
        else:
            # Create new listing
            listing = self.env["listing.records"].create(vals)

        return {
            "type": "ir.actions.act_window",
            "name": _("Listing"),
            "res_model": "listing.records",
            "res_id": listing.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.constrains("list_date", "expiry_date")
    def _check_list_expiry_date(self):
        for record in self:
            if (
                record.list_date
                and record.expiry_date
                and record.expiry_date <= record.list_date
            ):
                raise ValidationError(_("Expiry Date must be greater than List Date."))

    @api.constrains("list_price")
    def _check_list_price(self):
        for record in self:
            if record.list_price <= 0:
                raise ValidationError(_("List Price must be greater than zero."))
