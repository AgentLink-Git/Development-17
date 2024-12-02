# models/shared_resources/address_compute_mixin.py

"""
Module for managing Address Computations and Capitalizations.
This mixin provides computed fields for full and partial addresses, ensures proper
capitalization of address components, and maintains data integrity through constraints
and validation. It is designed to be inherited by other models requiring address-related
functionalities.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

# Configure the logger for this module
_logger = logging.getLogger(__name__)


class AddressComputeMixin(models.AbstractModel):
    """
    Abstract model providing address computation and capitalization functionalities.
    This mixin includes computed fields for various address formats and ensures that
    specific address fields are properly capitalized or title-cased. It also enforces
    data integrity through constraints and validation methods.
    """
    _name = "address.compute.mixin"
    _description = "Mixin for Address Fields"

    # =====================
    # Field Definitions
    # =====================
    full_address = fields.Char(
        compute="_compute_full_address",
        store=True,
        string="Full Address",
        help="Complete address combining all address components."
    )
    partial_address_with_city = fields.Char(
        compute="_compute_partial_address_with_city",
        store=True,
        string="Address with City",
        help="Address including the city."
    )
    partial_address_without_city = fields.Char(
        compute="_compute_partial_address_without_city",
        store=True,
        string="Address without City",
        help="Address excluding the city."
    )
    city_state_postal = fields.Char(
        compute="_compute_city_state_postal",
        store=True,
        string="City, State, Postal",
        help="Combination of city, state, and postal code."
    )

    # Define the fields that need to be fully capitalized
    FIELDS_TO_UPPERCASE = [
        'suite_number',
        'street_number',
        'postal_code',
        'legal_plan',
        'legal_block',
        'legal_lot',
        'legal_long',
    ]

    # Define the field that requires title capitalization
    FIELD_TO_TITLECASE = 'street_name'

    # =====================
    # Computed Fields Methods
    # =====================

    @api.depends(
        "suite_number",
        "street_number",
        "street_direction_prefix",
        "street_name",
        "street_type_id.name",
        "street_direction_suffix",
        "city_id.name",
        "state_id.name",
        "postal_code",
    )
    def _compute_full_address(self):
        """
        Compute the full address by combining all address components.
        """
        for rec in self:
            suite_part = f", Suite {rec.suite_number}" if rec.suite_number else ""
            parts = [
                rec.street_number or "",
                rec.street_direction_prefix or "",
                rec.street_name or "",
                rec.street_type_id.name or "",
                rec.street_direction_suffix or "",
                suite_part,
                f", {rec.city_id.name}" if rec.city_id else "",
                f", {rec.state_id.name}" if rec.state_id else "",
                f", {rec.postal_code}" if rec.postal_code else "",
            ]
            rec.full_address = " ".join(filter(None, parts)).strip()
            _logger.debug(f"Computed full_address for record ID {rec.id}: {rec.full_address}")

    @api.depends(
        "suite_number",
        "street_number",
        "street_direction_prefix",
        "street_name",
        "street_type_id.name",
        "street_direction_suffix",
        "city_id.name",
    )
    def _compute_partial_address_with_city(self):
        """
        Compute the partial address including the city.
        """
        for rec in self:
            suite_part = f", Suite {rec.suite_number}" if rec.suite_number else ""
            parts = [
                rec.street_number or "",
                rec.street_direction_prefix or "",
                rec.street_name or "",
                rec.street_type_id.name or "",
                rec.street_direction_suffix or "",
                suite_part,
                f", {rec.city_id.name}" if rec.city_id else "",
            ]
            rec.partial_address_with_city = " ".join(filter(None, parts)).strip()
            _logger.debug(f"Computed partial_address_with_city for record ID {rec.id}: {rec.partial_address_with_city}")

    @api.depends(
        "suite_number",
        "street_number",
        "street_direction_prefix",
        "street_name",
        "street_type_id.name",
        "street_direction_suffix",
    )
    def _compute_partial_address_without_city(self):
        """
        Compute the partial address excluding the city.
        """
        for rec in self:
            suite_part = f", Suite {rec.suite_number}" if rec.suite_number else ""
            parts = [
                rec.street_number or "",
                rec.street_direction_prefix or "",
                rec.street_name or "",
                rec.street_type_id.name or "",
                rec.street_direction_suffix or "",
                suite_part,
            ]
            rec.partial_address_without_city = " ".join(filter(None, parts)).strip()
            _logger.debug(f"Computed partial_address_without_city for record ID {rec.id}: {rec.partial_address_without_city}")

    @api.depends(
        "city_id.name",
        "state_id.name",
        "postal_code",
    )
    def _compute_city_state_postal(self):
        """
        Compute the combination of city, state, and postal code.
        """
        for rec in self:
            parts = [
                rec.city_id.name if rec.city_id else "",
                f", {rec.state_id.name}" if rec.state_id else "",
                f", {rec.postal_code}" if rec.postal_code else "",
            ]
            rec.city_state_postal = " ".join(filter(None, parts)).strip()
            _logger.debug(f"Computed city_state_postal for record ID {rec.id}: {rec.city_state_postal}")

    # =====================
    # Capitalization Methods
    # =====================

    @api.onchange(
        "suite_number",
        "street_number",
        "postal_code",
        "legal_plan",
        "legal_block",
        "legal_lot",
        "legal_long",
        "street_name",
    )
    def _onchange_capitalize_fields(self):
        """
        Onchange method to handle capitalization in the UI.
        Fully capitalizes specified fields and title-cases the street_name field.
        """
        for rec in self:
            # Fully capitalize specified fields if they have a value
            for field in self.FIELDS_TO_UPPERCASE:
                value = getattr(rec, field, False)
                if value:
                    setattr(rec, field, value.upper())
                    _logger.debug(f"Capitalized field '{field}' for record ID {rec.id}: {value.upper()}")

            # Title-case the street_name field
            if rec.street_name:
                original_street_name = rec.street_name
                rec.street_name = self._title_case(rec.street_name)
                _logger.debug(f"Title-cased 'street_name' for record ID {rec.id}: '{original_street_name}' to '{rec.street_name}'")

    def _title_case(self, text):
        """
        Helper method to title-case a given text.

        Args:
            text (str): The text to be title-cased.

        Returns:
            str: Title-cased text.
        """
        return ' '.join(word.capitalize() for word in text.split())

    @api.model
    def create(self, vals):
        """
        Override the create method to enforce capitalization before creation.

        Args:
            vals (dict): Values to create the record with.

        Returns:
            record: The created record.
        """
        _logger.debug(f"Creating record with initial vals: {vals}")
        vals = self._prepare_vals_for_capitalization(vals)
        return super(AddressComputeMixin, self).create(vals)

    def write(self, vals):
        """
        Override the write method to enforce capitalization before updating.

        Args:
            vals (dict): Values to write to the record.

        Returns:
            bool: True if write is successful.
        """
        _logger.debug(f"Writing vals to record ID(s) {self.ids}: {vals}")
        vals = self._prepare_vals_for_capitalization(vals)
        return super(AddressComputeMixin, self).write(vals)

    def _prepare_vals_for_capitalization(self, vals):
        """
        Prepare vals by capitalizing specified fields.

        Args:
            vals (dict): Original vals.

        Returns:
            dict: Modified vals with capitalization applied.
        """
        # Fully capitalize specified fields
        for field in self.FIELDS_TO_UPPERCASE:
            if field in vals and vals[field]:
                original_value = vals[field]
                vals[field] = vals[field].upper()
                _logger.debug(f"Capitalized field '{field}': '{original_value}' to '{vals[field]}'")

        # Title-case the street_name field
        if self.FIELD_TO_TITLECASE in vals and vals[self.FIELD_TO_TITLECASE]:
            original_street_name = vals[self.FIELD_TO_TITLECASE]
            vals[self.FIELD_TO_TITLECASE] = self._title_case(vals[self.FIELD_TO_TITLECASE])
            _logger.debug(
                f"Title-cased field '{self.FIELD_TO_TITLECASE}': '{original_street_name}' to '{vals[self.FIELD_TO_TITLECASE]}'"
            )

        return vals

    # =====================
    # Helper Methods
    # =====================

    def _title_case(self, text):
        """
        Helper method to title-case a given text.

        Args:
            text (str): The text to be title-cased.

        Returns:
            str: Title-cased text.
        """
        return ' '.join(word.capitalize() for word in text.split())