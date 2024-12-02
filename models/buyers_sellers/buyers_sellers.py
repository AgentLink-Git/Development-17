# models/buyers_sellers/buyers_sellers.py

"""
Module for managing Buyers and Sellers.
This module defines the BuyerSellerType and BuyersSellers models, which handle
the categorization and management of buyers, sellers, tenants, and landlords.
It includes fields for financial tracking, address synchronization, and ensures
data integrity through constraints and comprehensive logging for auditing and debugging purposes.
"""

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

# Configure the logger for this module
_logger = logging.getLogger(__name__)


class BuyerSellerType(models.Model):
    """
    Model for Buyer/Seller and Tenant/Landlord Types.
    Categorizes contacts based on their role in sales or leases.
    """
    _name = "buyer.seller.type"
    _description = "Buyer/Seller and Tenant/Landlord Types"
    _inherit = ["mail.thread", "mail.activity.mixin", "shared.fields.mixin"]
    _order = "name asc"

    name = fields.Char(
        string="Name",
        required=True,
        tracking=True,
        help="Name of the Buyer/Seller or Tenant/Landlord type."
    )
    for_sale_or_lease = fields.Selection(
        selection=[
            ("for_sale", "For Sale"),
            ("for_lease", "For Lease"),
        ],
        string="For Sale or Lease",
        required=True,
        tracking=True,
        help="Specify whether this type is for sale or for lease."
    )
    buyer_seller_type = fields.Selection(
        selection=[
            ("buyer", "Buyer"),
            ("seller", "Seller"),
            ("tenant", "Tenant"),
            ("landlord", "Landlord"),
        ],
        string="Type",
        required=True,
        tracking=True,
        help="Role type: Buyer, Seller, Tenant, or Landlord."
    )

    @api.onchange("for_sale_or_lease")
    def _onchange_for_sale_or_lease(self):
        """
        Set buyer_seller_type domain based on for_sale_or_lease selection.
        Filters the available types to relevant options based on sale or lease.
        """
        if self.for_sale_or_lease == "for_sale":
            domain = [("buyer_seller_type", "in", ["buyer", "seller"])]
            _logger.debug("Setting domain for 'buyer_seller_type' to Buyer and Seller.")
        elif self.for_sale_or_lease == "for_lease":
            domain = [("buyer_seller_type", "in", ["tenant", "landlord"])]
            _logger.debug("Setting domain for 'buyer_seller_type' to Tenant and Landlord.")
        else:
            domain = []
            _logger.debug("Removing domain restrictions for 'buyer_seller_type'.")

        return {"domain": {"buyer_seller_type": domain}}


class BuyersSellers(models.Model):
    """
    Model for Buyers and Sellers.
    Inherits from res.partner and manages additional information specific to buyers, sellers,
    tenants, and landlords, including financial tracking and address synchronization.
    """
    _name = "buyers.sellers"
    _description = "Buyers and Sellers"
    _inherits = {"res.partner": "partner_id"}
    _inherit = ["mail.thread", "mail.activity.mixin", "shared.fields.mixin"]
    _rec_name = "display_name"
    _order = "display_name asc"

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
        help="Associated contact from res.partner marked as Buyer/Seller."
    )
    end_id = fields.Many2one(
        "deal.end",
        string="Role",
        required=True,
        tracking=True,
        help="Role of the contact in the deal (Buyer, Seller, Tenant, Landlord)."
    )
    deal_id = fields.Many2one(
        'deal.records',
        string='Deal',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    listing_id = fields.Many2one(
        "listing.records",
        string="Listing",
        tracking=True,
        ondelete="set null",
        help="Associated listing record."
    )
    display_name = fields.Char(
        string="Display Name",
        compute="_compute_display_name",
        store=True,
        help="Computed display name combining contact name and role."
    )
    active = fields.Boolean(
        string="Active",
        default=True,
        tracking=True,
        help="Indicates whether the buyer/seller record is active."
    )
    account_move_id = fields.Many2one(
        "account.move",
        string="Account Move",
        ondelete="cascade",
        required=True,
        help="Related Account Move.",
    )
    notes = fields.Html(
        string="Notes",
        tracking=True,
        help="Additional notes or comments."
    )

    # =====================
    # Financial Fields
    # =====================
    payable_type = fields.Selection(
        selection=[
            ("ar", "A/R - Receivable from this Contact"),
            ("ap", "A/P - Payable to this Contact"),
            ("no", "No Payables or Receivables"),
        ],
        string="Payable Type",
        compute="_compute_payable_type",
        store=True,
        tracking=True,
        help="Determines if the contact has accounts receivable, payable, or none."
    )
    due_to_buyer_seller = fields.Monetary(
        string="Amount Due To",
        currency_field="currency_id",
        compute="_compute_due_amounts",
        store=True,
        tracking=True,
        help="Amount owed to this contact."
    )
    due_from_buyer_seller = fields.Monetary(
        string="Amount Due From",
        currency_field="currency_id",
        compute="_compute_due_amounts",
        store=True,
        tracking=True,
        help="Amount owed by this contact."
    )

    # =====================
    # Additional Fields
    # =====================
    for_sale_or_lease = fields.Selection(
        selection=[
            ("for_sale", "For Sale"),
            ("for_lease", "For Lease"),
        ],
        string="For Sale or Lease",
        compute="_compute_for_sale_or_lease",
        store=True,
        readonly=True,
        help="Determined from associated listing or deal whether for sale or lease."
    )
    buyer_seller_type = fields.Selection(
        selection=[
            ("buyer", "Buyer"),
            ("seller", "Seller"),
            ("tenant", "Tenant"),
            ("landlord", "Landlord"),
        ],
        string="Type",
        compute="_compute_buyer_seller_type",
        store=True,
        tracking=True,
        help="Role type based on sale or lease context."
    )
    copy_address = fields.Boolean(
        string="Copy Address from Listing/Deal",
        help="If checked, copies address details from the associated listing or deal."
    )

    # =====================
    # Deposit Fields (for Deal only)
    # =====================
    total_buyer_deposit = fields.Monetary(
        string="Total Buyer Deposit",
        compute="_compute_total_buyer_deposit",
        store=True,
        currency_field="currency_id",
        help="Total deposits held from the buyer."
    )
    total_seller_deposit = fields.Monetary(
        string="Total Seller Deposit",
        compute="_compute_total_seller_deposit",
        store=True,
        currency_field="currency_id",
        help="Total deposits held from the seller."
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
                _logger.debug(
                    f"Set 'for_sale_or_lease' to '{rec.listing_id.for_sale_or_lease}' "
                    f"from Listing ID {rec.listing_id.id}."
                )
            elif rec.deal_id:
                rec.for_sale_or_lease = rec.deal_id.for_sale_or_lease
                _logger.debug(
                    f"Set 'for_sale_or_lease' to '{rec.deal_id.for_sale_or_lease}' "
                    f"from Deal ID {rec.deal_id.id}."
                )
            else:
                rec.for_sale_or_lease = False
                _logger.debug("No Listing or Deal associated; 'for_sale_or_lease' set to False.")

    @api.depends("for_sale_or_lease", "end_id.type")
    def _compute_buyer_seller_type(self):
        """
        Determine whether the contact is referred to as
        a buyer/seller or tenant/landlord based on `for_sale_or_lease`.
        """
        for rec in self:
            if rec.for_sale_or_lease == "for_sale":
                rec.buyer_seller_type = rec.end_id.type
                _logger.debug(
                    f"Set 'buyer_seller_type' to '{rec.end_id.type}' for Sale."
                )
            elif rec.for_sale_or_lease == "for_lease":
                if rec.end_id.type == "buyer":
                    rec.buyer_seller_type = "tenant"
                    _logger.debug("Mapped 'buyer' to 'tenant' for Lease.")
                elif rec.end_id.type == "seller":
                    rec.buyer_seller_type = "landlord"
                    _logger.debug("Mapped 'seller' to 'landlord' for Lease.")
                else:
                    rec.buyer_seller_type = False
                    _logger.debug("No mapping found for 'buyer_seller_type' in Lease context.")
            else:
                rec.buyer_seller_type = False
                _logger.debug("'for_sale_or_lease' is neither 'for_sale' nor 'for_lease'.")

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
                    _logger.debug(
                        f"Set 'due_to_buyer_seller' to {rec.due_to_buyer_seller} and "
                        f"'due_from_buyer_seller' to {rec.due_from_buyer_seller} for Buyer/Tenant."
                    )
                elif rec.end_id.type in ["seller", "landlord"]:
                    rec.due_to_buyer_seller = rec.deal_id.due_to_seller or 0.0
                    rec.due_from_buyer_seller = rec.deal_id.due_from_seller or 0.0
                    _logger.debug(
                        f"Set 'due_to_buyer_seller' to {rec.due_to_buyer_seller} and "
                        f"'due_from_buyer_seller' to {rec.due_from_buyer_seller} for Seller/Landlord."
                    )
                else:
                    rec.due_to_buyer_seller = 0.0
                    rec.due_from_buyer_seller = 0.0
                    _logger.debug(
                        f"No valid 'end_id.type' found for Deal ID {rec.deal_id.id}; set dues to 0."
                    )
            else:
                rec.due_to_buyer_seller = 0.0
                rec.due_from_buyer_seller = 0.0
                _logger.debug("No Deal associated; set dues to 0.")

    @api.depends("due_to_buyer_seller", "due_from_buyer_seller")
    def _compute_payable_type(self):
        """
        Determines the payable type based on due amounts.
        """
        for rec in self:
            if rec.due_to_buyer_seller > 0:
                rec.payable_type = "ap"
                _logger.debug(
                    f"Set 'payable_type' to 'A/P' for record ID {rec.id}."
                )
            elif rec.due_from_buyer_seller > 0:
                rec.payable_type = "ar"
                _logger.debug(
                    f"Set 'payable_type' to 'A/R' for record ID {rec.id}."
                )
            else:
                rec.payable_type = "no"
                _logger.debug(
                    f"Set 'payable_type' to 'No Payables or Receivables' for record ID {rec.id}."
                )

    @api.depends("deal_id")
    def _compute_total_buyer_deposit(self):
        """
        Calculates total deposits held from the buyer.
        """
        for rec in self:
            if rec.deal_id:
                buyer_deposits = self.env["transaction.line"].search([
                    ("deal_id", "=", rec.deal_id.id),
                    ("received_from_end_type", "=", "buyer"),
                    ("transaction_type", "=", "trust_receipt"),
                ])
                rec.total_buyer_deposit = sum(buyer_deposits.mapped("amount"))
                _logger.debug(
                    "Total Buyer Deposit for BuyerSeller ID %s in Deal ID %s: %s",
                    rec.id,
                    rec.deal_id.id,
                    rec.total_buyer_deposit,
                )
            else:
                rec.total_buyer_deposit = 0.0
                _logger.debug(
                    "No Deal associated with BuyerSeller ID %s; set 'total_buyer_deposit' to 0.",
                    rec.id,
                )

    @api.depends("deal_id")
    def _compute_total_seller_deposit(self):
        """
        Calculates total deposits held from the seller.
        """
        for rec in self:
            if rec.deal_id:
                seller_deposits = self.env["transaction.line"].search([
                    ("deal_id", "=", rec.deal_id.id),
                    ("received_from_end_type", "=", "seller"),
                    ("transaction_type", "=", "trust_receipt"),
                ])
                rec.total_seller_deposit = sum(seller_deposits.mapped("amount"))
                _logger.debug(
                    "Total Seller Deposit for BuyerSeller ID %s in Deal ID %s: %s",
                    rec.id,
                    rec.deal_id.id,
                    rec.total_seller_deposit,
                )
            else:
                rec.total_seller_deposit = 0.0
                _logger.debug(
                    "No Deal associated with BuyerSeller ID %s; set 'total_seller_deposit' to 0.",
                    rec.id,
                )

    @api.depends("partner_id", "end_id", "buyer_seller_type")
    def _compute_display_name(self):
        """
        Compute the display name for the record by combining contact name and role type.
        """
        for rec in self:
            if rec.partner_id and rec.buyer_seller_type:
                rec.display_name = f"{rec.partner_id.name} ({rec.buyer_seller_type.title()})"
                _logger.debug(
                    f"Computed 'display_name' as '{rec.display_name}' for BuyerSeller ID {rec.id}."
                )
            elif rec.partner_id and rec.end_id:
                rec.display_name = f"{rec.partner_id.name} ({rec.end_id.name.title()})"
                _logger.debug(
                    f"Computed 'display_name' as '{rec.display_name}' using 'end_id' for BuyerSeller ID {rec.id}."
                )
            else:
                rec.display_name = rec.partner_id.name or _("New")
                _logger.debug(
                    f"Computed 'display_name' as '{rec.display_name}' for BuyerSeller ID {rec.id}."
                )

    # =====================
    # Onchange Methods
    # =====================
    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        """
        Synchronize partner data when the partner_id is changed.
        Copies relevant address and contact information from res.partner.
        """
        if self.partner_id:
            update_data = {
                'phone': self.partner_id.phone,
                'email': self.partner_id.email,
                'street': self.partner_id.street,
                'street2': self.partner_id.street2,
                'city': self.partner_id.city,
                'state_id': self.partner_id.state_id.id if self.partner_id.state_id else False,
                'country_id': self.partner_id.country_id.id if self.partner_id.country_id else False,
                'zip': self.partner_id.zip,
                'company_type': self.partner_id.company_type,
            }
            self.update(update_data)
            _logger.debug(
                "Synchronized partner data for BuyerSeller ID %s from Partner ID %s.",
                self.id,
                self.partner_id.id,
            )

    @api.onchange("copy_address")
    def _onchange_copy_address(self):
        """
        Copies address from listing or deal if copy_address is set.
        """
        if self.copy_address:
            source_record = self.deal_id or self.listing_id
            if source_record:
                address_data = {
                    'street': source_record.street or self.street,
                    'street2': source_record.street2 or self.street2,
                    'city': source_record.city or self.city,
                    'state_id': source_record.state_id.id if source_record.state_id else self.state_id.id,
                    'country_id': source_record.country_id.id if source_record.country_id else self.country_id.id,
                    'zip': source_record.zip or self.zip,
                }
                self.update(address_data)
                _logger.debug(
                    "Copied address from %s ID %s to BuyerSeller ID %s.",
                    "Deal" if self.deal_id else "Listing",
                    source_record.id,
                    self.id,
                )
            else:
                _logger.warning(
                    "No 'deal_id' or 'listing_id' set for BuyerSeller ID %s. Cannot copy address.",
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
                _logger.error(
                    f"Duplicate contact with role found for BuyerSeller ID {rec.id}."
                )
                raise ValidationError(
                    _("This contact with the same role already exists in this deal or listing.")
                )

    # =====================
    # Helper Methods
    # =====================
    def _update_partner_info(self):
        """
        Updates partner information based on BuyersSellers record.
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
                "Updated partner info for Partner ID %s based on BuyersSellers record ID %s",
                rec.partner_id.id,
                rec.id,
            )

    # =====================
    # Overrides and Extensions
    # =====================
    @api.model
    def create(self, vals):
        """
        Override the create method to update partner information after creation.
        Raises:
            UserError: If partner synchronization fails.
        """
        record = super(BuyersSellers, self).create(vals)
        try:
            record._update_partner_info()
        except Exception as e:
            _logger.error(
                "Failed to update partner info for BuyersSellers ID %s: %s",
                record.id,
                e
            )
            raise UserError(_("Failed to synchronize partner information. Please check logs for details."))
        return record

    def write(self, vals):
        """
        Override the write method to update partner information after update.
        Raises:
            UserError: If partner synchronization fails.
        """
        result = super(BuyersSellers, self).write(vals)
        try:
            self._update_partner_info()
        except Exception as e:
            _logger.error(
                "Failed to update partner info for BuyersSellers IDs %s: %s",
                self.ids,
                e
            )
            raise UserError(_("Failed to synchronize partner information. Please check logs for details."))
        return result

    # =====================
    # Name Search
    # =====================
    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """
        Name search with filter for Buyer/Seller Contacts.
        Searches based on contact name or parent contact name.
        """
        args = args or []
        if name:
            partners = self.env["res.partner"].search(
                ["|", ("name", operator, name), ("parent_id.name", operator, name)]
            )
            buyers_sellers = self.search(
                [("partner_id", "in", partners.ids)] + args, limit=limit
            )
            _logger.debug(
                "Performed name_search with name='%s'. Found %d BuyersSellers records.",
                name,
                len(buyers_sellers)
            )
        else:
            buyers_sellers = self.search(args, limit=limit)
            _logger.debug(
                "Performed name_search without name filter. Found %d BuyersSellers records.",
                len(buyers_sellers)
            )
        return buyers_sellers.name_get()