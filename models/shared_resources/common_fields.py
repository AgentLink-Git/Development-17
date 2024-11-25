# models/shared_resources/common_fields.py

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class BusinessSource(models.Model):
    _name = "business.source"
    _description = "Business Source"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
    ]
    name = fields.Char(string="Business Source")
    business_source_type = fields.Char(string="Type")
    sequence = fields.Integer(string="Sequence")
    is_active = fields.Boolean(string="Active", default=True)


class CitiesAndTowns(models.Model):
    _name = "cities.and.towns"
    _description = "Cities & Towns"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
    ]
    name = fields.Char(string="City or Town", required=True)
    is_active = fields.Boolean(string="Active", default=True)

    _sql_constraints = [
        ("name_unique", "unique(name)", "City/Town names must be unique.")
    ]


class DealEnd(models.Model):
    _name = "deal.end"
    _description = "End"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
    ]
    name = fields.Char(string="End")
    end_type = fields.Selection(
        [
            ("buyer", "Buyer"),
            ("seller", "Seller"),
            ("landlord", "Landlord"),
            ("tenant", "Tenant"),
            ("double_end", "Double End"),
        ],
        string="Type",
    )


class PropertyType(models.Model):
    _name = "property.type"
    _description = "Property Type"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
    ]
    name = fields.Char(string="Name", required=True)
    property_type = fields.Char(string="Type")
    sequence = fields.Integer(string="Sequence", default=1)
    is_active = fields.Boolean(string="Active", default=True)

    _sql_constraints = [
        ("name_unique", "unique(name)", "Property Type names must be unique.")
    ]


class StreetType(models.Model):
    _name = "street.type"
    _description = "Street Type"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
    ]
    name = fields.Char(string="Street Type", required=True)
    street_type = fields.Char(string="Type")
    sequence = fields.Integer(string="Sequence", default=1)
    is_active = fields.Boolean(string="Active", default=True)

    _sql_constraints = [
        ("name_unique", "unique(name)", "Street Type names must be unique.")
    ]
