# models/buyers_sellers/buyers_sellers_wizard.py

"""
Module for managing the Buyers/Sellers Creation Wizard.
This module defines transient models for a wizard that facilitates the creation of Buyers and Sellers
records based on user input. It includes validation, synchronization with res.partner, and logging
for auditing and debugging purposes.
"""

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

# Configure the logger for this module
_logger = logging.getLogger(__name__)


class BuyersSellersWizard(models.TransientModel):
    """
    Wizard to Create Buyers and Sellers.
    Provides an interface for users to input multiple Buyers/Sellers entries and create corresponding records.
    """
    _name = "buyers.sellers.wizard"
    _description = "Wizard to Create Buyers and Sellers"

    # =====================
    # Fields
    # =====================
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        ondelete='cascade',
        domain=[('is_other_broker', '=', True)],
    )
    line_ids = fields.One2many(
        "buyers.sellers.wizard.line",
        "wizard_id",
        string="Buyers/Sellers Entries",
        required=True,
        copy=True,
        help="List of Buyers/Sellers entries to be created."
    )

    # =====================
    # Action Methods
    # =====================

    def action_create_buyers_sellers(self):
        """
        Create Buyers/Sellers records from the wizard lines.
        Validates each line, creates or updates res.partner records, and then creates Buyers/Sellers records.
        Returns an action to open the created records in the form or tree view.
        Raises:
            UserError: If no entries are provided or creation fails.
        """
        self.ensure_one()

        if not self.line_ids:
            _logger.error("No Buyers/Sellers entries provided in the wizard.")
            raise UserError(_("Please add at least one Buyers/Sellers entry to proceed."))

        created_records = self.env['buyers.sellers']

        for line in self.line_ids:
            # Validate buyer_seller_type consistency
            if line.for_sale_or_lease == "for_sale" and line.buyer_seller_type not in ["buyer", "seller"]:
                _logger.error(
                    "Invalid buyer_seller_type '%s' for For Sale in wizard line ID %s.",
                    line.buyer_seller_type,
                    line.id
                )
                raise ValidationError(_("For Sale must be associated with Buyer or Seller type."))
            if line.for_sale_or_lease == "for_lease" and line.buyer_seller_type not in ["tenant", "landlord"]:
                _logger.error(
                    "Invalid buyer_seller_type '%s' for For Lease in wizard line ID %s.",
                    line.buyer_seller_type,
                    line.id
                )
                raise ValidationError(_("For Lease must be associated with Tenant or Landlord type."))

            # Check if partner already exists
            partner = self.env['res.partner'].search([('name', '=', line.partner_name)], limit=1)
            if not partner:
                # Create the res.partner record
                partner_vals = {
                    'name': line.partner_name,
                    'email': line.partner_email,
                    'phone': line.partner_phone,
                    'street': line.partner_street,
                    'street2': line.partner_street2,
                    'city': line.partner_city,
                    'state_id': line.partner_state_id.id,
                    'zip': line.partner_zip,
                    'country_id': line.partner_country_id.id,
                    'is_buyer_seller': True,  # Ensure this field exists in res.partner
                    'comment': line.notes,
                }
                _logger.debug("Creating res.partner with values: %s", partner_vals)
                partner = self.env['res.partner'].create(partner_vals)
                _logger.info("Created res.partner ID %s for BuyersSellersWizard line ID %s.", partner.id, line.id)
            else:
                # Update existing partner with new info
                partner_vals = {
                    'email': line.partner_email,
                    'phone': line.partner_phone,
                    'street': line.partner_street,
                    'street2': line.partner_street2,
                    'city': line.partner_city,
                    'state_id': line.partner_state_id.id,
                    'zip': line.partner_zip,
                    'country_id': line.partner_country_id.id,
                    'comment': line.notes,
                    'is_buyer_seller': True,
                }
                _logger.debug("Updating res.partner ID %s with values: %s", partner.id, partner_vals)
                partner.write(partner_vals)
                _logger.info("Updated res.partner ID %s for BuyersSellersWizard line ID %s.", partner.id, line.id)

            # Prepare values for Buyers/Sellers record
            buyers_sellers_vals = {
                'partner_id': partner.id,
                'end_id': line.end_id.id,
                'deal_id': line.deal_id.id if line.deal_id else False,
                'listing_id': line.listing_id.id if line.listing_id else False,
                'notes': line.notes,
                'company_id': self.env.company.id,
                'copy_address': False,  # Default value, adjust if needed
            }

            # Create the Buyers/Sellers record
            _logger.debug("Creating BuyersSellers record with values: %s", buyers_sellers_vals)
            buyers_sellers = self.env['buyers.sellers'].create(buyers_sellers_vals)
            created_records += buyers_sellers
            _logger.info("Created BuyersSellers record ID %s from wizard line ID %s.", buyers_sellers.id, line.id)

        if created_records:
            action = self.env.ref('your_module.action_buyers_sellers_form').read()[0]
            if len(created_records) == 1:
                action['res_id'] = created_records.id
                action['view_mode'] = 'form'
                _logger.debug("Redirecting to form view of BuyersSellers record ID %s.", created_records.id)
            else:
                action['domain'] = [('id', 'in', created_records.ids)]
                action['view_mode'] = 'tree,form'
                _logger.debug("Redirecting to tree view of multiple BuyersSellers records: %s.", created_records.ids)
            return action
        else:
            _logger.error("No BuyersSellers records were created from the wizard.")
            raise UserError(_("No Buyers/Sellers records were created."))


class BuyersSellersWizardLine(models.TransientModel):
    """
    Wizard Line for Buyers and Sellers.
    Represents a single entry in the Buyers/Sellers creation wizard, capturing all necessary information
    for creating or updating BuyersSellers records.
    """
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
        help="Reference to the parent BuyersSellersWizard."
    )

    # ---------------------
    # Partner Information
    # ---------------------
    partner_name = fields.Char(
        string="Contact Name",
        required=True,
        help="Name of the contact."
    )
    partner_email = fields.Char(
        string="Email",
        help="Email address of the contact."
    )
    partner_phone = fields.Char(
        string="Phone",
        help="Phone number of the contact."
    )
    partner_street = fields.Char(
        string="Street",
        help="Street address of the contact."
    )
    partner_street2 = fields.Char(
        string="Street2",
        help="Additional street information."
    )
    partner_city = fields.Char(
        string="City",
        help="City of the contact."
    )
    partner_state_id = fields.Many2one(
        'res.country.state',
        string="State",
        help="State of the contact."
    )
    partner_zip = fields.Char(
        string="Zip",
        help="ZIP code of the contact."
    )
    partner_country_id = fields.Many2one(
        'res.country',
        string="Country",
        help="Country of the contact."
    )

    # ---------------------
    # Buyers/Sellers Specific Fields
    # ---------------------
    end_id = fields.Many2one(
        "deal.end",
        string="Role",
        required=True,
        help="Role of the contact in the deal (Buyer, Seller, Tenant, Landlord)."
    )
    for_sale_or_lease = fields.Selection(
        [("for_sale", "For Sale"), ("for_lease", "For Lease")],
        string="For Sale or Lease",
        required=True,
        help="Specify whether the entry is for sale or lease."
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
        help="Role type based on sale or lease context."
    )
    notes = fields.Html(
        string="Notes",
        help="Additional notes or comments."
    )

    # =====================
    # Constraints
    # =====================
    @api.constrains('buyer_seller_type', 'for_sale_or_lease')
    def _check_type_consistency(self):
        """
        Ensure that the buyer_seller_type is consistent with for_sale_or_lease selection.
        Raises:
            ValidationError: If there's a mismatch between type and sale/lease selection.
        """
        for rec in self:
            if rec.for_sale_or_lease == "for_sale" and rec.buyer_seller_type not in ["buyer", "seller"]:
                _logger.error(
                    "Mismatch: 'for_sale_or_lease' is 'for_sale' but 'buyer_seller_type' is '%s' for wizard line ID %s.",
                    rec.buyer_seller_type,
                    rec.id
                )
                raise ValidationError(_("For Sale must be associated with Buyer or Seller type."))
            if rec.for_sale_or_lease == "for_lease" and rec.buyer_seller_type not in ["tenant", "landlord"]:
                _logger.error(
                    "Mismatch: 'for_sale_or_lease' is 'for_lease' but 'buyer_seller_type' is '%s' for wizard line ID %s.",
                    rec.buyer_seller_type,
                    rec.id
                )
                raise ValidationError(_("For Lease must be associated with Tenant or Landlord type."))

    @api.constrains('deal_id', 'listing_id')
    def _check_deal_or_listing(self):
        """
        Ensure that at least one of deal_id or listing_id is set.
        Raises:
            ValidationError: If neither deal_id nor listing_id is set.
        """
        for rec in self:
            if not rec.deal_id and not rec.listing_id:
                _logger.error(
                    "Neither 'deal_id' nor 'listing_id' set for wizard line ID %s.",
                    rec.id
                )
                raise ValidationError(_("You must select either a Deal or a Listing."))

    # =====================
    # Onchange Methods
    # =====================
    @api.onchange('for_sale_or_lease')
    def _onchange_for_sale_or_lease(self):
        """
        Update the domain of buyer_seller_type based on the for_sale_or_lease selection.
        """
        if self.for_sale_or_lease == 'for_sale':
            domain = [('buyer_seller_type', 'in', ['buyer', 'seller'])]
            _logger.debug("Onchange: Setting domain for 'buyer_seller_type' to Buyer and Seller.")
        elif self.for_sale_or_lease == 'for_lease':
            domain = [('buyer_seller_type', 'in', ['tenant', 'landlord'])]
            _logger.debug("Onchange: Setting domain for 'buyer_seller_type' to Tenant and Landlord.")
        else:
            domain = []
            _logger.debug("Onchange: Removing domain restrictions for 'buyer_seller_type'.")
        return {'domain': {'buyer_seller_type': domain}}

    @api.onchange('deal_id')
    def _onchange_deal_id(self):
        """
        Clear listing_id if deal_id is selected to maintain data integrity.
        """
        if self.deal_id:
            _logger.debug(
                "Onchange: Clearing 'listing_id' because 'deal_id' is selected for wizard line ID %s.",
                self.id
            )
            self.listing_id = False

    @api.onchange('listing_id')
    def _onchange_listing_id(self):
        """
        Clear deal_id if listing_id is selected to maintain data integrity.
        """
        if self.listing_id:
            _logger.debug(
                "Onchange: Clearing 'deal_id' because 'listing_id' is selected for wizard line ID %s.",
                self.id
            )
            self.deal_id = False