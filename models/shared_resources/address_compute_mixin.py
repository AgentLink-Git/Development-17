# models/shared_resources/address_compute_mixin.py

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class AddressComputeMixin(models.AbstractModel):
    _name = "address.compute.mixin"
    _description = "Mixin for Address Fields"

    # Computed Address Fields
    full_address = fields.Char(
        compute="_compute_full_address", store=True, string="Full Address"
    )
    partial_address_with_city = fields.Char(
        compute="_compute_partial_address_with_city",
        store=True,
        string="Address with City",
    )
    partial_address_without_city = fields.Char(
        compute="_compute_partial_address_without_city",
        store=True,
        string="Address without City",
    )
    city_state_postal = fields.Char(
        compute="_compute_city_state_postal",
        store=True,
        string="City, State, Postal",
    )

    # Define the fields that need to be fully capitalized
    FIELDS_TO_UPPERCASE = [
        "suite_number",
        "street_number",
        "postal_code",
        "legal_plan",
        "legal_block",
        "legal_lot",
        "legal_long",
    ]

    # Define the field that requires title capitalization
    FIELD_TO_TITLECASE = "street_name"

    # Onchange method to handle capitalization in the UI
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
        for rec in self:
            # Fully capitalize specified fields if they have a value
            for field in self.FIELDS_TO_UPPERCASE:
                value = getattr(rec, field)
                if value:
                    setattr(rec, field, value.upper())

            # Title-case the street_name field
            if rec.street_name:
                rec.street_name = self._title_case(rec.street_name)

    # Helper method for title-casing
    def _title_case(self, text):
        return " ".join(word.capitalize() for word in text.split())

    # Override create to enforce capitalization
    @api.model
    def create(self, vals):
        # Capitalize fields before creation
        vals = self._prepare_vals_for_capitalization(vals)
        return super(AddressComputeMixin, self).create(vals)

    # Override write to enforce capitalization
    def write(self, vals):
        # Capitalize fields before writing
        vals = self._prepare_vals_for_capitalization(vals)
        return super(AddressComputeMixin, self).write(vals)

    # Prepare vals for capitalization
    def _prepare_vals_for_capitalization(self, vals):
        # Fully capitalize specified fields
        for field in self.FIELDS_TO_UPPERCASE:
            if field in vals and vals[field]:
                vals[field] = vals[field].upper()

        # Title-case the street_name field
        if self.FIELD_TO_TITLECASE in vals and vals[self.FIELD_TO_TITLECASE]:
            vals[self.FIELD_TO_TITLECASE] = self._title_case(
                vals[self.FIELD_TO_TITLECASE]
            )

        return vals

    # Compute Methods
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
        for rec in self:
            # Determine the suite number with ", Suite " prefix if present
            suite_part = f", Suite {rec.suite_number}" if rec.suite_number else ""

            parts = [
                rec.street_number or "",
                rec.street_direction_prefix or "",
                rec.street_name or "",
                rec.street_type_id.name or "",
                rec.street_direction_suffix or "",
                suite_part,
                ", " + rec.city_id.name if rec.city_id else "",
                ", " + rec.state_id.name if rec.state_id else "",
                ", " + rec.postal_code if rec.postal_code else "",
            ]
            rec.full_address = " ".join(filter(None, parts)).strip()

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
        for rec in self:
            # Determine the suite number with ", Suite " prefix if present
            suite_part = f", Suite {rec.suite_number}" if rec.suite_number else ""

            parts = [
                rec.street_number or "",
                rec.street_direction_prefix or "",
                rec.street_name or "",
                rec.street_type_id.name or "",
                rec.street_direction_suffix or "",
                suite_part,
                ", " + rec.city_id.name if rec.city_id else "",
            ]
            rec.partial_address_with_city = " ".join(filter(None, parts)).strip()

    @api.depends(
        "suite_number",
        "street_number",
        "street_direction_prefix",
        "street_name",
        "street_type_id.name",
        "street_direction_suffix",
    )
    def _compute_partial_address_without_city(self):
        for rec in self:
            # Determine the suite number with ", Suite " prefix if present
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

    @api.depends(
        "city_id.name",
        "state_id.name",
        "postal_code",
    )
    def _compute_city_state_postal(self):
        for rec in self:
            parts = [
                rec.city_id.name if rec.city_id else "",
                ", " + rec.state_id.name if rec.state_id else "",
                ", " + rec.postal_code if rec.postal_code else "",
            ]
            rec.city_state_postal = " ".join(filter(None, parts)).strip()
