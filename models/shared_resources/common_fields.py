# models/shared_resources/common_fields.py

"""
Module for managing Common Fields.
This module defines several common models used across the application, including BusinessSource,
CitiesAndTowns, DealEnd, PropertyType, and StreetType. It ensures data integrity through
constraints and provides comprehensive logging for auditing and debugging purposes.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

# Configure the logger for this module
_logger = logging.getLogger(__name__)


class BusinessSource(models.Model):
    """
    Model for storing Business Sources.
    Represents different sources of business within the system.
    """
    _name = "business.source"
    _description = "Business Source"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence asc, name asc"

    name = fields.Char(
        string="Business Source",
        required=True,
        help="Name of the business source.",
        tracking=True,
    )
    business_source_type = fields.Char(
        string="Type",
        help="Type of the business source.",
        tracking=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        default=1,
        help="Sequence order for the business source.",
        tracking=True,
    )
    is_active = fields.Boolean(
        string="Active",
        default=True,
        help="Indicates whether the business source is active.",
        tracking=True,
    )

    _sql_constraints = [
        (
            "name_unique",
            "unique(name)",
            "Business Source names must be unique."
        )
    ]

    @api.constrains('name')
    def _check_unique_name(self):
        """
        Ensure that the Business Source name is unique.
        """
        for record in self:
            existing = self.search([
                ('name', '=', record.name),
                ('id', '!=', record.id)
            ])
            if existing:
                _logger.error(
                    f"Duplicate Business Source name '{record.name}' found for record ID {record.id}."
                )
                raise ValidationError(_("Business Source names must be unique."))


class CitiesAndTowns(models.Model):
    """
    Model for storing Cities and Towns.
    Represents different cities and towns within the system.
    """
    _name = "cities.and.towns"
    _description = "Cities & Towns"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name asc"

    name = fields.Char(
        string="City or Town",
        required=True,
        help="Name of the city or town.",
        tracking=True,
    )
    is_active = fields.Boolean(
        string="Active",
        default=True,
        help="Indicates whether the city or town is active.",
        tracking=True,
    )

    _sql_constraints = [
        (
            "name_unique",
            "unique(name)",
            "City/Town names must be unique."
        )
    ]

    @api.constrains('name')
    def _check_unique_name(self):
        """
        Ensure that the City or Town name is unique.
        """
        for record in self:
            existing = self.search([
                ('name', '=', record.name),
                ('id', '!=', record.id)
            ])
            if existing:
                _logger.error(
                    f"Duplicate City/Town name '{record.name}' found for record ID {record.id}."
                )
                raise ValidationError(_("City/Town names must be unique."))


class DealEnd(models.Model):
    """
    Model for storing Deal Ends.
    Represents different types of ends related to deals, such as Buyer, Seller, etc.
    """
    _name = "deal.end"
    _description = "Deal End"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "name asc"

    name = fields.Char(
        string="End",
        required=True,
        help="Name of the deal end.",
        tracking=True,
    )
    end_type = fields.Selection(
        [
            ("buyer", "Buyer"),
            ("seller", "Seller"),
            ("landlord", "Landlord"),
            ("tenant", "Tenant"),
            ("double_end", "Double End"),
        ],
        string="Type",
        required=True,
        help="Type of the deal end.",
        tracking=True,
    )

    _sql_constraints = [
        (
            "name_unique",
            "unique(name)",
            "Deal End names must be unique."
        )
    ]

    @api.constrains('name')
    def _check_unique_name(self):
        """
        Ensure that the Deal End name is unique.
        """
        for record in self:
            existing = self.search([
                ('name', '=', record.name),
                ('id', '!=', record.id)
            ])
            if existing:
                _logger.error(
                    f"Duplicate Deal End name '{record.name}' found for record ID {record.id}."
                )
                raise ValidationError(_("Deal End names must be unique."))


class PropertyType(models.Model):
    """
    Model for storing Property Types.
    Represents different types of properties within the system.
    """
    _name = "property.type"
    _description = "Property Type"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence asc, name asc"

    name = fields.Char(
        string="Name",
        required=True,
        help="Name of the property type.",
        tracking=True,
    )
    property_type = fields.Char(
        string="Type",
        help="Type description of the property.",
        tracking=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        default=1,
        help="Sequence order for the property type.",
        tracking=True,
    )
    is_active = fields.Boolean(
        string="Active",
        default=True,
        help="Indicates whether the property type is active.",
        tracking=True,
    )

    _sql_constraints = [
        (
            "name_unique",
            "unique(name)",
            "Property Type names must be unique."
        )
    ]

    @api.constrains('name')
    def _check_unique_name(self):
        """
        Ensure that the Property Type name is unique.
        """
        for record in self:
            existing = self.search([
                ('name', '=', record.name),
                ('id', '!=', record.id)
            ])
            if existing:
                _logger.error(
                    f"Duplicate Property Type name '{record.name}' found for record ID {record.id}."
                )
                raise ValidationError(_("Property Type names must be unique."))


class StreetType(models.Model):
    """
    Model for storing Street Types.
    Represents different types of streets within the system.
    """
    _name = "street.type"
    _description = "Street Type"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence asc, name asc"

    name = fields.Char(
        string="Street Type",
        required=True,
        help="Name of the street type.",
        tracking=True,
    )
    street_type = fields.Char(
        string="Type",
        help="Type description of the street.",
        tracking=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        default=1,
        help="Sequence order for the street type.",
        tracking=True,
    )
    is_active = fields.Boolean(
        string="Active",
        default=True,
        help="Indicates whether the street type is active.",
        tracking=True,
    )

    _sql_constraints = [
        (
            "name_unique",
            "unique(name)",
            "Street Type names must be unique."
        )
    ]

    @api.constrains('name')
    def _check_unique_name(self):
        """
        Ensure that the Street Type name is unique.
        """
        for record in self:
            existing = self.search([
                ('name', '=', record.name),
                ('id', '!=', record.id)
            ])
            if existing:
                _logger.error(
                    f"Duplicate Street Type name '{record.name}' found for record ID {record.id}."
                )
                raise ValidationError(_("Street Type names must be unique."))