# models/listings/listing_records.py

import uuid
import logging
from odoo import fields, api, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class ListingRecords(models.Model):
    _name = "listing.records"
    _description = "Listing Records"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "address.compute.mixin",
        "commission.setup.mixin",
        "commission.favourite.mixin",
    ]

    # =====================
    # Basic Information
    # =====================
    name = fields.Char(
        string="Listing", required=True, readonly=True, default=lambda self: _("New")
    )
    listing_number = fields.Char(
        string="Listing #",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        required=True,
        ondelete="cascade",
        help="Partner associated with this deal.",
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        string="Currency",
        readonly=True,
    )

    # =====================
    # Address & Legal Description
    # =====================
    suite_number = fields.Char(string="Suite Number", tracking=True)
    street_number = fields.Char(string="Street Number", tracking=True)
    street_direction_prefix = fields.Selection(
        selection=[
            ("east", "East"),
            ("ne", "NE"),
            ("nw", "NW"),
            ("north", "North"),
            ("se", "SE"),
            ("sw", "SW"),
            ("south", "South"),
            ("west", "West"),
        ],
        string="Street Direction Prefix",
        tracking=True,
    )
    street_name = fields.Char(string="Street Name", tracking=True)
    street_type_id = fields.Many2one(
        "street.type",
        string="Street Type",
        tracking=True,
    )
    street_direction_suffix = fields.Selection(
        selection=[
            ("east", "East"),
            ("ne", "NE"),
            ("nw", "NW"),
            ("north", "North"),
            ("se", "SE"),
            ("sw", "SW"),
            ("south", "South"),
            ("west", "West"),
        ],
        string="Street Direction Suffix",
        tracking=True,
    )
    city_id = fields.Many2one(
        "cities.and.towns",
        string="City",
        tracking=True,
    )
    state_id = fields.Many2one(
        "res.country.state",
        string="Province",
        tracking=True,
    )
    country_id = fields.Many2one(
        "res.country",
        string="Country",
        tracking=True,
    )
    postal_code = fields.Char(string="Postal Code", size=7, tracking=True)

    # Legal Description
    legal_plan = fields.Char(string="Plan/Condo Plan #", tracking=True)
    legal_block = fields.Char(string="Block/Unit #", tracking=True)
    legal_lot = fields.Char(string="Lot/Unit Factor #", tracking=True)
    legal_long = fields.Char(string="Long Legal (Rural)", tracking=True)

    # =====================
    # Representation (End)
    # =====================
    end_id = fields.Many2one(
        "deal.end", string="We Represent", tracking=True, index=True
    )
    # =====================
    # Price and Date Fields
    # =====================
    list_price = fields.Monetary(
        string="List Price",
        currency_field="currency_id",
        help="List price of the property",
    )
    sell_price = fields.Monetary(
        string="Sell Price",
        currency_field="currency_id",
        help="Selling price of the property",
    )
    list_date = fields.Date(string="List Date", tracking=True)
    expiry_date = fields.Date(string="Expiry Date", tracking=True)
    cancel_date = fields.Date(string="Cancel Date", tracking=True)
    offer_date = fields.Date(string="Offer Date", required=True, tracking=True)

    # =====================
    # Property Details
    # =====================
    deal_class_id = fields.Many2one(
        "deal.class",
        string="Class",
        domain="[('is_active','=',True)]",
        tracking=True,
        index=True,
    )
    property_type_id = fields.Many2one(
        "property.type",
        string="Property Type",
        domain="[('is_active', '=', True)]",
        tracking=True,
    )
    size = fields.Char(string="Size (Sq Ft/Sq M)", tracking=True)
    ml_number = fields.Char(string="ML Number", tracking=True)
    title_requested = fields.Boolean(string="Office to Order Title", tracking=True)
    title_ordered = fields.Boolean(string="Title Ordered", tracking=True)
    business_source_id = fields.Many2one(
        "business.source",
        string="Business Source",
        domain="[('is_active', '=', True)]",
        tracking=True,
    )
    for_sale_or_lease = fields.Selection(
        [
            ("for_sale", "For Sale"),
            ("for_lease", "For Lease"),
        ],
        string="For Sale or Lease",
        required=True,
        default="for_sale",
        tracking=True,
        help="Indicates whether the deal is for sale or lease.",
    )
    notes = fields.Html(string="Notes", tracking=True)

    # =====================
    # Status and Details
    # =====================
    is_listing_cancelled = fields.Boolean(string="Listing Cancelled", tracking=True)
    is_listing_sold = fields.Boolean(string="Listing Sold", tracking=True)
    status = fields.Selection(
        [
            ("draft", "Draft"),
            ("active", "Active"),
            ("expired", "Expired"),
            ("sold", "Sold"),
            ("cancelled", "Cancelled"),
        ],
        string="Status",
        tracking=True,
        index=True,
        default="draft",
    )

    # =====================
    # Relationships
    # =====================
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal Record",
        readonly=False,
        tracking=True,
        help="Related deal record.",
    )
    _sql_constraints = [
        (
            "listing_deal_unique",
            "unique(deal_id)",
            "A deal can be linked to only one listing.",
        ),
        (
            "listing_number_unique",
            "unique(listing_number)",
            "The Listing Number must be unique.",
        ),
    ]

    buyers_sellers_ids = fields.One2many(
        "buyers.sellers", "listing_id", string="Buyers/Sellers", tracking=True
    )
    sales_agents_and_referrals_ids = fields.One2many(
        "sales.agents.and.referrals",
        "listing_id",
        string="Sales Agents & Referrals",
        tracking=True,
    )
    sales_agent_mentorship_line_ids = fields.One2many(
        "sales.agent.mentorship.line",
        "deal_id",
        string="Sales Agent Mentorship Line",
        help="Mentorship records for sales agents.",
    )
    sales_agent_team_ids = fields.One2many(
        "sales.agent.team",
        "deal_id",
        string="Sales Agent Teams",
        help="Team records for sales agents.",
    )

    # =====================
    # InfoDirect & Media Tours
    # =====================
    info_direct_requested = fields.Boolean(string="InfoDirect Requested", tracking=True)
    info_direct_number = fields.Char(string="InfoDirect #", tracking=True)
    info_direct_link = fields.Char(string="InfoDirect Link", tracking=True)
    info_direct_done = fields.Boolean(string="InfoDirect Done", tracking=True)
    media_tour_requested = fields.Boolean(string="Media Tour Requested", tracking=True)
    media_tour_done = fields.Boolean(string="Media Tour Done", tracking=True)
    media_tour_link = fields.Char(string="Media Tour Link", tracking=True)

    # =====================
    # Documents
    # =====================
    document_line_ids = fields.One2many(
        "document.line", "listing_id", string="Documents"
    )
    required_document_ids = fields.One2many(
        "document.line",
        compute="_compute_required_documents",
        string="Required Documents",
    )
    all_documents_received = fields.Boolean(
        string="All Documents Received",
        compute="_compute_all_documents_received",
        store=True,
    )
    required_document_count = fields.Integer(
        string="# Required Documents",
        compute="_compute_required_document_count",
        store=True,
    )

    # =====================
    # Constraints and Onchange Methods
    # =====================
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

    @api.onchange(
        "expiry_date", "list_date", "is_listing_cancelled", "deal_id", "cancel_date"
    )
    def _onchange_status(self):
        today_date = fields.Date.today()
        for rec in self:
            if rec.deal_id:
                rec.status = "sold"
            elif rec.is_listing_cancelled and rec.cancel_date:
                rec.status = "cancelled"
            elif rec.list_date and rec.expiry_date:
                if rec.list_date <= today_date <= rec.expiry_date:
                    rec.status = "active"
                elif rec.expiry_date < today_date:
                    rec.status = "expired"
                else:
                    rec.status = "draft"
            else:
                rec.status = "draft"

    @api.onchange("sales_agents_and_referrals_ids")
    def _onchange_sales_agents_and_referrals_ids(self):
        total_percentage = sum(
            self.sales_agents_and_referrals_ids.mapped("percentage_of_end")
        )
        if total_percentage > 100:
            raise ValidationError(_("Total percentage of end should not exceed 100%."))

    # =====================
    # Document Compute Methods
    # =====================
    @api.depends(
        "document_line_ids.document_required", "document_line_ids.manually_removed"
    )
    def _compute_required_documents(self):
        for rec in self:
            required_documents = rec.document_line_ids.filtered(
                lambda d: d.document_required and not d.manually_removed
            )
            rec.required_document_ids = required_documents

    @api.depends(
        "document_line_ids.document_review",
        "document_line_ids.document_required",
        "document_line_ids.manually_removed",
    )
    def _compute_all_documents_received(self):
        for rec in self:
            pending_documents = rec.document_line_ids.filtered(
                lambda d: d.document_required
                and d.document_review != "approved"
                and not d.manually_removed
            )
            rec.all_documents_received = not bool(pending_documents)

    @api.depends(
        "document_line_ids.document_required", "document_line_ids.manually_removed"
    )
    def _compute_required_document_count(self):
        for rec in self:
            rec.required_document_count = len(
                rec.document_line_ids.filtered(
                    lambda d: d.document_required and not d.manually_removed
                )
            )

    def _update_required_documents(self):
        for rec in self:
            required_docs = self.env["document.type"].search(
                [
                    ("is_active", "=", True),
                    ("is_listing_document", "=", True),
                    ("seller_end", "=", True),
                    ("class_ids", "in", rec.deal_class_id.id),
                ]
            )
            existing_docs = rec.document_line_ids.filtered(
                lambda d: d.document_type_id.id in required_docs.ids
                and not d.manually_removed
            )
            missing_docs = required_docs - existing_docs.mapped("document_type_id")
            for doc_type in missing_docs:
                self.env["document.line"].create(
                    {
                        "document_type_id": doc_type.id,
                        "deal_id": rec.deal_id.id,
                        "listing_id": rec.id,
                        "end_id": rec.end_id.id,
                    }
                )

    # =====================
    # Override Create and Write Methods
    # =====================
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals["name"] = (
                str(uuid.uuid4())
                if vals.get("name", _("New")) == _("New")
                else vals["name"]
            )
            list_date = fields.Date.from_string(
                vals.get("list_date", fields.Date.context_today(self))
            )
            vals["listing_number"] = self.env["ir.sequence"].next_by_code(
                "listing.records", sequence_date=list_date.strftime("%Y-%m-%d")
            ) or _("New")
        listings = super(
            ListingRecords, self.with_context(populate_commission_lines=False)
        ).create(vals_list)
        listings._update_required_documents()
        return listings

    def write(self, vals):
        res = super(
            ListingRecords, self.with_context(populate_commission_lines=False)
        ).write(vals)
        self._update_required_documents()
        return res

    # =====================
    # Create Deal from Listing
    # =====================

    def action_open_commission_config_wizard(self):
        """
        Open a wizard for configuring commission details.
        """
        return {
            "type": "ir.actions.act_window",
            "name": "Configure Commission",
            "res_model": "commission.favourite.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_listing_id": self.id,
                "default_total_commission_favourite_id": self.total_commission_favourite_id.id,
                "default_buyer_side_commission_favourite_id": self.buyer_side_commission_favourite_id.id,
            },
        }

    def action_open_listing_wizard(self):
        """Open the listing wizard for adding or editing a listing."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Listing Wizard",
            "res_model": "listing.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_id": self.id,
                "default_listing_id": self.id,
                # Add other default values if necessary
            },
        }

    def action_create_deal(self):
        self.ensure_one()

        # Validate status requirements
        if self.status == "sold":
            raise ValidationError(
                _(
                    "This listing is already sold and cannot be used to create another deal."
                )
            )

        # Prepare Deal Values
        deal_vals = self._prepare_deal_vals()
        deal = self.env["deal.records"].create(deal_vals)

        # Link Deal to Documents and Transfer Buyers/Sellers and Agents
        self._link_to_deal(deal)
        self._transfer_related_data_to_deal(deal)

        # Update Listing Status and Mark as Sold
        self.status = "sold"
        self.is_listing_sold = True
        self.sell_price = deal.sell_price
        self.sell_date = deal.sell_date
        self._onchange_status()

        return {
            "type": "ir.actions.act_window",
            "name": _("Deal"),
            "res_model": "deal.records",
            "res_id": deal.id,
            "view_mode": "form",
            "target": "current",
        }

    def _prepare_deal_vals(self):
        """Prepare values for creating a new Deal record based on the current listing."""
        return {
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "listing_number": self.listing_number,
            "listing_id": self.id,
            "end_id": self.end_id.id,
            # Address
            "partial_address_with_city": self.partial_address_with_city,
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
            # Property Details
            "list_price": self.list_price,
            "list_date": self.list_date,
            "deal_class_id": self.deal_class_id.id,
            "property_type_id": self.property_type_id.id,
            "size": self.size,
            "ml_number": self.ml_number,
            "business_source_id": self.business_source_id.id,
            "for_sale_or_lease": self.for_sale_or_lease,
            "created_by_listing": True,
        }

    def _link_to_deal(self, deal):
        """Link the deal to conveyancing documents in the listing."""
        # Add deal_id to existing document lines where is_conveyancing_document == True
        listing_documents = self.document_line_ids.filtered(
            lambda d: d.document_type_id.is_conveyancing_document
        )
        listing_documents.write({"deal_id": deal.id})

    def _transfer_related_data_to_deal(self, deal):
        """Transfer related Buyers/Sellers and Sales Agents data to the newly created deal."""
        # Prepare Buyers/Sellers Data
        buyers_sellers_data = [
            (
                0,
                0,
                {
                    "partner_id": bs.partner_id.id,
                    "end_id": bs.end_id.id,
                    "notes": bs.notes,
                },
            )
            for bs in self.buyers_sellers_ids
        ]

        # Prepare Sales Agents & Referrals Data
        sales_agents_referrals_data = [
            (
                0,
                0,
                {
                    "sales_agent_id": sa.sales_agent_id.id,
                    "other_broker_id": sa.other_broker_id.id,
                    "buyers_sellers_id": sa.buyers_sellers_id.id,
                    "payment_type": sa.payment_type,
                    "percentage_of_end": sa.percentage_of_end,
                    "plus_flat_fee": sa.plus_flat_fee,
                    "less_flat_fee": sa.less_flat_fee,
                    "notes": sa.notes,
                    "end_id": sa.end_id.id,
                    "for_sale_or_lease": sa.for_sale_or_lease,
                    "referral_letter_on_file": sa.referral_letter_on_file,
                },
            )
            for sa in self.sales_agents_and_referrals_ids
        ]

        # Bulk Create Buyers/Sellers and Sales Agents & Referrals in Deal
        if buyers_sellers_data:
            deal.buyers_sellers_ids = buyers_sellers_data
        if sales_agents_referrals_data:
            deal.sales_agents_and_referrals_ids = sales_agents_referrals_data

    _sql_constraints = [
        (
            "listing_number_unique",
            "unique(listing_number)",
            "The Listing Number must be unique.",
        )
    ]

    def name_get(self):
        result = []
        for rec in self:
            name = rec.listing_number or "Listing"
            result.append((rec.id, name))
        return result
