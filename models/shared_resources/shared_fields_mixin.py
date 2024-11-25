# models/shared_resources/shared_fields.py

from odoo import models, fields


class SharedFieldsMixin(models.AbstractModel):
    _name = "shared.fields.mixin"
    _description = "Shared Fields Mixin"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        string="Currency",
        readonly=True,
    )
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        ondelete="cascade",
        tracking=True,
    )
    deal_number = fields.Char(
        string="Deal Number",
        store=True,
        readonly=True,
    )
