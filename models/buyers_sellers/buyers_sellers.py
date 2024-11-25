# models/buyers_sellers/buyers_sellers.py

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class BuyerSellerType(models.Model):
    _name = "buyer.seller.type"
    _description = "Buyer/Seller and Tenant/Landlord Types"
    _inherit = ["mail.thread", "mail.activity.mixin", "shared.fields.mixin"]

    name = fields.Char(string="Name", required=True, tracking=True)
    for_sale_or_lease = fields.Selection(
        [
            ("for_sale", "For Sale"),
            ("for_lease", "For Lease"),
        ],
        string="For Sale or Lease",
        required=True,
        tracking=True,
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
        tracking=True,
    )

    @api.onchange("for_sale_or_lease")
    def _onchange_for_sale_or_lease(self):
        """Set buyer_seller_type domain based on for_sale_or_lease selection."""
        if self.for_sale_or_lease == "for_sale":
            return {
                "domain": {
                    "buyer_seller_type": [
                        ("buyer_seller_type", "in", ["buyer", "seller"])
                    ]
                }
            }
        elif self.for_sale_or_lease == "for_lease":
            return {
                "domain": {
                    "buyer_seller_type": [
                        ("buyer_seller_type", "in", ["tenant", "landlord"])
                    ]
                }
            }
        else:
            return {"domain": {"buyer_seller_type": []}}


class BuyersSellers(models.Model):
    _name = "buyers.sellers"
    _description = "Buyers and Sellers"
    _inherits = {"res.partner": "partner_id"}
    _inherit = ["mail.thread", "mail.activity.mixin", "shared.fields.mixin"]
    _rec_name = "display_name"

    # =====================
    # Basic Fields
    # =====================
    partner_id = fields.Many2one(
        "res.partner",
        string="Contact",
        required=True,
        tracking=True,
        domain="[('is_buyer_seller', '=', True)]",
        ondelete="cascade",
    )
    end_id = fields.Many2one(
        "deal.end",
        string="Role",
        required=True,
        tracking=True,
    )
    listing_id = fields.Many2one(
        "listing.records",
        string="Listing",
        tracking=True,
        ondelete="set null",
    )
    display_name = fields.Char(
        string="Display Name",
        compute="_compute_display_name",
        store=True,
    )
    active = fields.Boolean(string="Active", default=True, tracking=True)
    notes = fields.Html(string="Notes", tracking=True)

    # =====================
    # Financial Fields
    # =====================
    payable_type = fields.Selection(
        [
            ("ar", "A/R - Receivable from this Contact"),
            ("ap", "A/P - Payable to this Contact"),
            ("no", "No Payables or Receivables"),
        ],
        string="Payable Type",
        compute="_compute_payable_type",
        store=True,
        tracking=True,
    )
    due_to_buyer_seller = fields.Monetary(
        string="Amount Due To",
        currency_field="currency_id",
        compute="_compute_due_amounts",
        store=True,
        tracking=True,
    )
    due_from_buyer_seller = fields.Monetary(
        string="Amount Due From",
        currency_field="currency_id",
        compute="_compute_due_amounts",
        store=True,
        tracking=True,
    )

    # =====================
    # Additional Fields
    # =====================
    for_sale_or_lease = fields.Selection(
        [
            ("for_sale", "For Sale"),
            ("for_lease", "For Lease"),
        ],
        string="For Sale or Lease",
        compute="_compute_for_sale_or_lease",
        store=True,
        readonly=True,
    )
    buyer_seller_type = fields.Selection(
        [
            ("buyer", "Buyer"),
            ("seller", "Seller"),
            ("tenant", "Tenant"),
            ("landlord", "Landlord"),
        ],
        string="Type",
        compute="_compute_buyer_seller_type",
        store=True,
        tracking=True,
    )
    copy_address = fields.Boolean(string="Copy Address from Listing/Deal")

    # =====================
    # Deposit Fields (for Deal only)
    # =====================
    total_buyer_deposit = fields.Monetary(
        string="Total Buyer Deposit",
        compute="_compute_total_buyer_deposit",
        store=True,
        currency_field="currency_id",
    )
    total_seller_deposit = fields.Monetary(
        string="Total Seller Deposit",
        compute="_compute_total_seller_deposit",
        store=True,
        currency_field="currency_id",
    )

    # =====================
    # Compute Methods
    # =====================

    @api.depends("listing_id.for_sale_or_lease", "deal_id.for_sale_or_lease")
    def _compute_for_sale_or_lease(self):
        """
        Populate `for_sale_or_lease` from either `listing_records` or `deal_records`.
        """
        for rec in self:
            if rec.listing_id:
                rec.for_sale_or_lease = rec.listing_id.for_sale_or_lease
            elif rec.deal_id:
                rec.for_sale_or_lease = rec.deal_id.for_sale_or_lease
            else:
                rec.for_sale_or_lease = False

    @api.depends("for_sale_or_lease", "end_id.type")
    def _compute_buyer_seller_type(self):
        """
        Determine whether the contact is referred to as
        a buyer/seller or tenant/landlord based on `for_sale_or_lease`.
        """
        for rec in self:
            if rec.for_sale_or_lease == "for_sale":
                rec.buyer_seller_type = rec.end_id.type
            elif rec.for_sale_or_lease == "for_lease":
                if rec.end_id.type == "buyer":
                    rec.buyer_seller_type = "tenant"
                elif rec.end_id.type == "seller":
                    rec.buyer_seller_type = "landlord"
                else:
                    rec.buyer_seller_type = False
            else:
                rec.buyer_seller_type = False

    @api.depends(
        "deal_id.due_to_buyer",
        "deal_id.due_from_buyer",
        "deal_id.due_to_seller",
        "deal_id.due_from_seller",
        "end_id.type",
    )
    def _compute_due_amounts(self):
        """
        Sets `due_to_buyer_seller` and `due_from_buyer_seller` based on values in deal's due fields.
        """
        for rec in self:
            if rec.deal_id:
                if rec.end_id.type in ["buyer", "tenant"]:
                    rec.due_to_buyer_seller = rec.deal_id.due_to_buyer or 0.0
                    rec.due_from_buyer_seller = rec.deal_id.due_from_buyer or 0.0
                elif rec.end_id.type in ["seller", "landlord"]:
                    rec.due_to_buyer_seller = rec.deal_id.due_to_seller or 0.0
                    rec.due_from_buyer_seller = rec.deal_id.due_from_seller or 0.0
                else:
                    rec.due_to_buyer_seller = 0.0
                    rec.due_from_buyer_seller = 0.0
            else:
                rec.due_to_buyer_seller = 0.0
                rec.due_from_buyer_seller = 0.0

    @api.depends("due_to_buyer_seller", "due_from_buyer_seller")
    def _compute_payable_type(self):
        """
        Determines the payable type based on due amounts.
        """
        for rec in self:
            if rec.due_to_buyer_seller > 0:
                rec.payable_type = "ap"
            elif rec.due_from_buyer_seller > 0:
                rec.payable_type = "ar"
            else:
                rec.payable_type = "no"

    @api.depends("deal_id")
    def _compute_total_buyer_deposit(self):
        """
        Calculates total deposits held from the buyer.
        """
        for rec in self:
            if rec.deal_id:
                buyer_deposits = self.env["transaction.line"].search(
                    [
                        ("deal_id", "=", rec.deal_id.id),
                        ("received_from_end_type", "=", "buyer"),
                        ("transaction_type", "=", "trust_receipt"),
                    ]
                )
                rec.total_buyer_deposit = sum(buyer_deposits.mapped("amount"))
                _logger.debug(
                    "Total Buyer Deposit for Buyer ID %s in Deal ID %s: %s",
                    rec.id,
                    rec.deal_id.id,
                    rec.total_buyer_deposit,
                )
            else:
                rec.total_buyer_deposit = 0.0

    @api.depends("deal_id")
    def _compute_total_seller_deposit(self):
        """
        Calculates total deposits held from the seller.
        """
        for rec in self:
            if rec.deal_id:
                seller_deposits = self.env["transaction.line"].search(
                    [
                        ("deal_id", "=", rec.deal_id.id),
                        ("received_from_end_type", "=", "seller"),
                        ("transaction_type", "=", "trust_receipt"),
                    ]
                )
                rec.total_seller_deposit = sum(seller_deposits.mapped("amount"))
                _logger.debug(
                    "Total Seller Deposit for Seller ID %s in Deal ID %s: %s",
                    rec.id,
                    rec.deal_id.id,
                    rec.total_seller_deposit,
                )
            else:
                rec.total_seller_deposit = 0.0

    @api.depends("partner_id", "end_id", "buyer_seller_type")
    def _compute_display_name(self):
        """
        Compute the display name for the record.
        """
        for rec in self:
            if rec.partner_id and rec.buyer_seller_type:
                rec.display_name = (
                    f"{rec.partner_id.name} ({rec.buyer_seller_type.title()})"
                )
            elif rec.partner_id and rec.end_id:
                rec.display_name = f"{rec.partner_id.name} ({rec.end_id.name.title()})"
            else:
                rec.display_name = rec.partner_id.name or _("New")

    # =====================
    # Onchange Methods
    # =====================

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        """
        Synchronize partner data when changed.
        """
        if self.partner_id:
            self.update(
                {
                    "phone": self.partner_id.phone,
                    "email": self.partner_id.email,
                    "street": self.partner_id.street,
                    "street2": self.partner_id.street2,
                    "city": self.partner_id.city,
                    "state_id": self.partner_id.state_id.id
                    if self.partner_id.state_id
                    else False,
                    "country_id": self.partner_id.country_id.id
                    if self.partner_id.country_id
                    else False,
                    "zip": self.partner_id.zip,
                    "company_type": self.partner_id.company_type,
                }
            )

    @api.onchange("copy_address")
    def _onchange_copy_address(self):
        """
        Copies address from listing or deal, if set.
        """
        if self.copy_address:
            source_record = self.deal_id or self.listing_id
            if source_record:
                self.update(
                    {
                        "street": source_record.street or self.street,
                        "street2": source_record.street2 or self.street2,
                        "city": source_record.city or self.city,
                        "state_id": source_record.state_id.id
                        if source_record.state_id
                        else self.state_id.id,
                        "country_id": source_record.country_id.id
                        if source_record.country_id
                        else self.country_id.id,
                        "zip": source_record.zip or self.zip,
                    }
                )
            else:
                _logger.warning(
                    "No 'deal_id' or 'listing_id' set for record ID %s. Cannot copy address.",
                    self.id,
                )

    # =====================
    # Constraints
    # =====================

    @api.constrains("partner_id", "end_id", "deal_id", "listing_id")
    def _check_for_duplicate_contact(self):
        """
        Ensure that the same contact with the same role is not added multiple times to the same deal or listing.
        """
        for rec in self:
            domain = [
                ("partner_id", "=", rec.partner_id.id),
                ("end_id", "=", rec.end_id.id),
                ("id", "!=", rec.id),
            ]
            if rec.deal_id:
                domain.append(("deal_id", "=", rec.deal_id.id))
            if rec.listing_id:
                domain.append(("listing_id", "=", rec.listing_id.id))
            existing = self.search(domain)
            if existing:
                raise ValidationError(
                    _(
                        "This contact with the same role already exists in this deal or listing."
                    )
                )

    # =====================
    # Helper Methods
    # =====================

    def _update_partner_info(self):
        """
        Updates partner information based on Buyers/Sellers record.
        """
        for rec in self:
            data = {
                "phone": rec.phone,
                "email": rec.email,
                "street": rec.street,
                "street2": rec.street2,
                "city": rec.city,
                "state_id": rec.state_id.id if rec.state_id else False,
                "country_id": rec.country_id.id if rec.country_id else False,
                "zip": rec.zip,
                "company_type": rec.company_type,
                "comment": rec.notes,
            }
            rec.partner_id.write(data)
            _logger.debug(
                "Updated partner info for Partner ID %s based on Buyers/Sellers record ID %s",
                rec.partner_id.id,
                rec.id,
            )

    # =====================
    # Overrides and Extensions
    # =====================

    @api.model
    def create(self, vals):
        """
        Override create method to update partner information.
        """
        record = super(BuyersSellers, self).create(vals)
        record._update_partner_info()
        return record

    def write(self, vals):
        """
        Override write method to update partner information.
        """
        result = super(BuyersSellers, self).write(vals)
        self._update_partner_info()
        return result

    # =====================
    # Name Search
    # =====================

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """
        Name search with filter for Buyer/Seller Contacts.
        """
        args = args or []
        if name:
            partners = self.env["res.partner"].search(
                ["|", ("name", operator, name), ("parent_id.name", operator, name)]
            )
            buyers_sellers = self.search(
                [("partner_id", "in", partners.ids)] + args, limit=limit
            )
        else:
            buyers_sellers = self.search(args, limit=limit)
        return buyers_sellers.name_get()
