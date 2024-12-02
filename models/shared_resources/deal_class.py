# models/shared_resources/deal_class.py

"""
Module for managing Deal Classes.
This module defines the DealClass model, which represents different classes of deals or listings.
It includes fields to categorize deals as for sale or lease, manage the number of ends, and associate
with specific deal types. The module ensures data integrity through constraints and provides comprehensive
logging for auditing and debugging purposes.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

# Configure the logger for this module
_logger = logging.getLogger(__name__)


class DealClass(models.Model):
    """
    Model for storing Deal Classes.
    Represents different classes of deals or listings, categorizing them as for sale or lease,
    and associating with specific deal ends. Ensures that a deal class cannot be both for sale
    and for lease simultaneously and that it is properly categorized.
    """
    _name = 'deal.class'
    _description = "Listing/Deal Classes"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name asc'

    # =====================
    # Fields
    # =====================

    name = fields.Char(
        string="Class",
        required=True,
        tracking=True,
        help="Name of the deal class."
    )
    no_of_ends = fields.Float(
        string="# Ends",
        default=1.0,
        tracking=True,
        help="Number of ends associated with this deal class."
    )
    for_sale = fields.Boolean(
        string="For Sale",
        default=False,
        tracking=True,
        help="Indicates if the deal class is for sale."
    )
    for_lease = fields.Boolean(
        string="For Lease",
        default=False,
        tracking=True,
        help="Indicates if the deal class is for lease."
    )
    end_id = fields.Many2one(
        'deal.end',
        string="We Represent",
        required=True,
        tracking=True,
        help="The type of deal end represented by this class."
    )
    is_active = fields.Boolean(
        string="Active",
        default=True,
        tracking=True,
        help="Indicates whether the deal class is active."
    )

    # Contextual Fields
    for_sale_or_lease = fields.Selection(
        selection=[
            ('for_sale', 'For Sale'),
            ('for_lease', 'For Lease')
        ],
        string="Sale or Lease",
        required=True,
        default='for_sale',
        tracking=True,
        help="Specify whether the deal class is for sale or for lease."
    )
    listing_id = fields.Many2one(
        'listing.record',
        string="Listing",
        tracking=True,
        help="Associated listing record."
    )
    deal_id = fields.Many2one(
        'deal.records',
        string="Deal",
        tracking=True,
        help="Associated deal record."
    )

    # =====================
    # Constraints
    # =====================

    @api.constrains('for_sale', 'for_lease')
    def _check_sale_or_lease(self):
        """
        Ensure that a DealClass cannot be both for sale and for lease simultaneously.
        Raises:
            UserError: If both for_sale and for_lease are set to True or both are False.
        """
        for record in self:
            if record.for_sale and record.for_lease:
                _logger.error(
                    f"Deal Class '{record.name}' (ID: {record.id}) cannot be both For Sale and For Lease."
                )
                raise UserError("A Deal Class cannot be marked as both For Sale and For Lease.")
            if not record.for_sale and not record.for_lease:
                _logger.error(
                    f"Deal Class '{record.name}' (ID: {record.id}) must be either For Sale or For Lease."
                )
                raise UserError("Please specify whether the Deal Class is For Sale or For Lease.")

    @api.constrains('for_sale_or_lease')
    def _check_for_sale_or_lease_selection(self):
        """
        Ensure that the for_sale_or_lease selection aligns with the for_sale and for_lease fields.
        Raises:
            UserError: If the selection does not match the boolean fields.
        """
        for record in self:
            if record.for_sale_or_lease == 'for_sale' and not record.for_sale:
                _logger.error(
                    f"Deal Class '{record.name}' (ID: {record.id}) has inconsistent sale settings."
                )
                raise UserError("Mismatch between 'Sale or Lease' selection and 'For Sale' field.")
            if record.for_sale_or_lease == 'for_lease' and not record.for_lease:
                _logger.error(
                    f"Deal Class '{record.name}' (ID: {record.id}) has inconsistent lease settings."
                )
                raise UserError("Mismatch between 'Sale or Lease' selection and 'For Lease' field.")

    # =====================
    # Onchange Methods
    # =====================

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
            _logger.debug("No associated Listing or Deal. Removing domain restrictions.")
            return {'domain': {'deal_class_id': []}}

        # Determine the type based on sale or lease
        if self.for_sale_or_lease == "for_sale":
            if is_listing:
                # For sellers in listings
                domain = [
                    ('deal_end_id.type', 'in', ['seller', 'double_end']),
                    ('for_sale', '=', True)
                ]
                _logger.debug("Setting domain for 'deal_class_id' for sellers in listings.")
            else:
                # For buyers in deals
                domain = [
                    ('deal_end_id.type', '=', 'buyer'),
                    ('for_sale', '=', True)
                ]
                _logger.debug("Setting domain for 'deal_class_id' for buyers in deals.")
        elif self.for_sale_or_lease == "for_lease":
            if is_listing:
                # For landlords in listings
                domain = [
                    ('deal_end_id.type', 'in', ['landlord', 'double_end']),
                    ('for_lease', '=', True)
                ]
                _logger.debug("Setting domain for 'deal_class_id' for landlords in listings.")
            else:
                # For tenants in deals
                domain = [
                    ('deal_end_id.type', '=', 'tenant'),
                    ('for_lease', '=', True)
                ]
                _logger.debug("Setting domain for 'deal_class_id' for tenants in deals.")
        else:
            # Default domain if neither sale nor lease is selected
            domain = []
            _logger.debug("Defaulting domain for 'deal_class_id' with no specific conditions.")

        # Set the domain for deal_class_id field
        _logger.debug(f"Domain set for 'deal_class_id': {domain}")
        return {'domain': {'deal_class_id': domain}}

    # =====================
    # Override Methods
    # =====================

    @api.model
    def create(self, vals):
        """
        Override the create method to ensure that either for_sale or for_lease is set.
        Raises:
            UserError: If neither for_sale nor for_lease is set.
        """
        if not vals.get('for_sale') and not vals.get('for_lease'):
            _logger.error("Attempted to create Deal Class without specifying sale or lease.")
            raise UserError("Please specify whether the Deal Class is For Sale or For Lease.")
        _logger.debug(f"Creating Deal Class with values: {vals}")
        return super(DealClass, self).create(vals)

    def write(self, vals):
        """
        Override the write method to ensure that either for_sale or for_lease is set.
        Raises:
            UserError: If both for_sale and for_lease are set or neither is set.
        """
        if 'for_sale' in vals or 'for_lease' in vals:
            for record in self:
                for_sale = vals.get('for_sale', record.for_sale)
                for_lease = vals.get('for_lease', record.for_lease)
                if for_sale and for_lease:
                    _logger.error(
                        f"Attempted to update Deal Class '{record.name}' (ID: {record.id}) "
                        f"to be both For Sale and For Lease."
                    )
                    raise UserError("A Deal Class cannot be marked as both For Sale and For Lease.")
                if not for_sale and not for_lease:
                    _logger.error(
                        f"Attempted to update Deal Class '{record.name}' (ID: {record.id}) "
                        f"without specifying sale or lease."
                    )
                    raise UserError("Please specify whether the Deal Class is For Sale or For Lease.")
        _logger.debug(f"Updating Deal Class with values: {vals}")
        return super(DealClass, self).write(vals)

    # =====================
    # Utility Methods
    # =====================

    def _log_deal_class_update(self, field_name, old_value, new_value):
        """
        Utility method for logging updates to deal class fields.

        Args:
            field_name (str): The name of the field being updated.
            old_value (Any): The old value of the field.
            new_value (Any): The new value of the field.
        """
        _logger.info(
            f"Updated '{field_name}': '{old_value}' -> '{new_value}' "
            f"for Deal Class ID {self.id}."
        )

    def write(self, vals):
        """
        Override the write method to log updates to specific fields.
        """
        for record in self:
            for field in ['name', 'no_of_ends', 'for_sale', 'for_lease', 'end_id']:
                if field in vals:
                    old_value = getattr(record, field)
                    new_value = vals[field]
                    record._log_deal_class_update(field, old_value, new_value)
        return super(DealClass, self).write(vals)