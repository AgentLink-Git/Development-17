# models/shared_resources/commission_template.py

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class CommissionTemplate(models.Model):
    _name = "commission.template"
    _description = "Commission Template"
    _rec_name = "name"

    name = fields.Char(
        string="Name", required=True, help="Name of the commission template."
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        help="Company associated with this commission template.",
    )
    commission_category = fields.Selection(
        [
            ("total_commission", "Total Commission"),
            ("buyer_side_commission", "Buyer Side Commission"),
        ],
        string="Commission Category",
        required=True,
        help="Category of the commission template.",
    )
    commission_type = fields.Selection(
        [
            ("tiered", "Tiered Percentage"),
            ("fixed", "Fixed Percentage"),
            ("flat_fee", "Flat Fee"),
        ],
        string="Commission Type",
        required=True,
        help="Type of commission.",
    )
    total_commission_percentage = fields.Float(
        string="Total Commission Percentage (%)", help="Overall commission percentage."
    )
    commission_flat_fee_plus = fields.Monetary(
        string="+ Flat Fee ($)",
        currency_field="currency_id",
        help="Additional flat fee to add.",
    )
    commission_flat_fee_less = fields.Monetary(
        string="- Flat Fee ($)",
        currency_field="currency_id",
        help="Flat fee to subtract.",
    )
    commission_template_line_ids = fields.One2many(
        "commission.template.line",
        "commission_template_id",
        string="Commission Template Lines",
        help="Lines associated with this commission template.",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        help="Currency for the commission.",
    )

    # Constraints
    @api.constrains("total_commission_percentage")
    def _check_total_commission_percentage(self):
        for record in self:
            if record.commission_type in ["fixed", "tiered"] and not (
                0 <= record.total_commission_percentage <= 100
            ):
                raise ValidationError(
                    _("Total Commission Percentage must be between 0 and 100.")
                )

    @api.constrains("commission_template_line_ids")
    def _check_template_lines(self):
        for record in self:
            if not record.commission_template_line_ids:
                raise ValidationError(
                    _("Commission Template must have at least one commission line.")
                )


class CommissionTemplateLine(models.Model):
    _name = "commission.template.line"
    _description = "Commission Template Line"

    commission_template_id = fields.Many2one(
        "commission.template",
        string="Commission Template",
        required=True,
        ondelete="cascade",
        help="The commission template associated with this line.",
    )
    commission_type = fields.Selection(
        [
            ("total", "Total Commission"),
            ("buyer_side", "Buyer Side Commission"),
        ],
        string="Commission Type",
        required=True,
        help="Type of commission this line represents.",
    )
    commission_category = fields.Selection(
        [
            ("first", "First"),
            ("next", "Next"),
            ("total_selling_price", "Total Selling Price"),
            ("remainder", "Remainder"),
        ],
        string="Commission Category",
        required=True,
        help="Category of the commission line.",
    )
    portion_of_selling_price = fields.Monetary(
        string="Portion of Selling Price ($)",
        required=True,
        help="The portion of the selling price that this line's commission calculations are based on.",
    )
    commission_percentage = fields.Float(
        string="Commission Percentage (%)",
        required=True,
        help="Commission percentage for this portion of the selling price.",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        help="Currency for the commission.",
    )

    # Constraints
    @api.constrains(
        "portion_of_selling_price", "commission_percentage", "commission_category"
    )
    def _check_line_values(self):
        for record in self:
            if record.portion_of_selling_price <= 0:
                raise ValidationError(
                    _("Portion of Selling Price must be greater than 0.")
                )
            if not (0 <= record.commission_percentage <= 100):
                raise ValidationError(
                    _("Commission percentage must be between 0 and 100.")
                )
            if (
                record.commission_category in ["total_selling_price", "remainder"]
                and record.portion_of_selling_price <= 0
            ):
                raise ValidationError(
                    _(
                        "Final commission categories must cover the remaining selling price."
                    )
                )
