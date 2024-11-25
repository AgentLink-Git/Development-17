# models/shared_resources/commission_favourite.py

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class CommissionFavourite(models.Model):
    _name = "commission.favourite"
    _description = "Commission Favourite"
    _order = "name asc"
    _rec_name = "name"

    # =====================
    # Fields
    # =====================

    name = fields.Char(
        string="Name", required=True, help="Name of the commission favourite."
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        help="Company associated with this commission favourite.",
        index=True,
    )
    commission_category = fields.Selection(
        [
            ("total_commission", "Total Commission"),
            ("buyer_side_commission", "Buyer Side Commission"),
        ],
        string="Commission Category",
        required=True,
        help="Category of the commission favourite.",
        tracking=True,
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
        tracking=True,
    )
    total_commission_percentage = fields.Float(
        string="Total Commission Percentage (%)",
        help="Overall commission percentage.",
        digits=(16, 2),
        default=0.0,
        tracking=True,
    )
    commission_flat_fee_plus = fields.Monetary(
        string="+ Flat Fee ($)",
        currency_field="currency_id",
        help="Additional flat fee to add.",
        default=0.0,
        tracking=True,
    )
    commission_flat_fee_less = fields.Monetary(
        string="- Flat Fee ($)",
        currency_field="currency_id",
        help="Flat fee to subtract.",
        default=0.0,
        tracking=True,
    )
    commission_favourite_line_ids = fields.One2many(
        "commission.favourite.line",
        "commission_favourite_id",
        string="Commission Favourite Lines",
        help="Lines associated with this commission favourite.",
        copy=True,
        auto_join=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        help="Currency for the commission.",
        readonly=True,
    )

    # =====================
    # Constraints
    # =====================

    @api.constrains("total_commission_percentage", "commission_type")
    def _check_total_commission_percentage(self):
        """
        Ensure that the total commission percentage is between 0 and 100
        for commission types that require it.
        """
        for record in self:
            if record.commission_type in ["fixed", "tiered"]:
                if not (0 <= record.total_commission_percentage <= 100):
                    raise ValidationError(
                        _(
                            "Total Commission Percentage must be between 0 and 100 for the selected commission type."
                        )
                    )

    @api.constrains("commission_favourite_line_ids")
    def _check_favourite_lines(self):
        """
        Ensure that each commission favourite has at least one commission line.
        """
        for record in self:
            if not record.commission_favourite_line_ids:
                raise ValidationError(
                    _("Commission Favourite must have at least one commission line.")
                )


class CommissionFavouriteLine(models.Model):
    _name = "commission.favourite.line"
    _description = "Commission Favourite Line"
    _order = "sequence asc"

    # =====================
    # Fields
    # =====================

    commission_favourite_id = fields.Many2one(
        "commission.favourite",
        string="Commission Favourite",
        required=True,
        ondelete="cascade",
        help="The commission favourite associated with this line.",
        index=True,
    )
    sequence = fields.Integer(
        string="Sequence",
        default=1,
        help="Sequence order of the commission favourite line.",
    )
    commission_type = fields.Selection(
        [
            ("total", "Total Commission"),
            ("buyer_side", "Buyer Side Commission"),
        ],
        string="Commission Type",
        required=True,
        help="Type of commission this line represents.",
        tracking=True,
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
        tracking=True,
    )
    portion_of_selling_price = fields.Monetary(
        string="Portion of Selling Price ($)",
        required=True,
        help="The portion of the selling price that this line's commission calculations are based on.",
        digits=(16, 2),
        default=0.0,
        tracking=True,
    )
    commission_percentage = fields.Float(
        string="Commission Percentage (%)",
        required=True,
        help="Commission percentage for this portion of the selling price.",
        digits=(16, 2),
        default=0.0,
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        help="Currency for the commission.",
        readonly=True,
    )

    # =====================
    # Constraints
    # =====================

    @api.constrains(
        "portion_of_selling_price", "commission_percentage", "commission_category"
    )
    def _check_line_values(self):
        """
        Ensure that:
        - Portion of Selling Price is greater than 0.
        - Commission Percentage is between 0 and 100.
        - Final commission categories ('total_selling_price', 'remainder') have valid portions.
        """
        for record in self:
            if record.portion_of_selling_price <= 0:
                raise ValidationError(
                    _("Portion of Selling Price must be greater than 0.")
                )
            if not (0 <= record.commission_percentage <= 100):
                raise ValidationError(
                    _("Commission Percentage must be between 0 and 100.")
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

    # =====================
    # Methods
    # =====================

    @api.model
    def create(self, vals):
        """
        Override the create method to set default sequence if not provided.
        """
        if "sequence" not in vals or not vals["sequence"]:
            vals["sequence"] = (
                self.search_count(
                    [
                        (
                            "commission_favourite_id",
                            "=",
                            vals.get("commission_favourite_id"),
                        )
                    ]
                )
                + 1
            )
        return super(CommissionFavouriteLine, self).create(vals)

    def write(self, vals):
        """
        Override the write method to handle sequence changes if necessary.
        """
        return super(CommissionFavouriteLine, self).write(vals)

    # Optional: Add any computed fields or helper methods if needed
