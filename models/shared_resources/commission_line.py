# models/shared_resources/commission_line.py

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class CommissionLine(models.Model):
    _name = "commission.line"
    _description = "Commission Line"

    # Fields
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        ondelete="cascade",
        help="Deal associated with this commission line.",
    )
    listing_id = fields.Many2one(
        "listing.records",
        string="Listing",
        ondelete="cascade",
        help="Listing associated with this commission line.",
    )
    commission_form_id = fields.Many2one(
        "commission.form",
        string="Commission Form",
        ondelete="restrict",
        required=True,
        tracking=True,
        help="Commission form defining the commission parameters.",
    )
    portion_of_selling_price = fields.Monetary(
        string="Selling Price Line Value ($)",
        required=True,
        help="The portion of the selling price that this line's commission calculations are based on.",
    )
    commission_percentage = fields.Float(
        string="Commission Percentage (%)",
        required=True,
        help="Commission percentage for this portion of the selling price.",
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
    commission_type = fields.Selection(
        [
            ("total", "Total"),
            ("buyer_side", "Buyer Side"),
        ],
        string="Commission Type",
        required=True,
        default="total",
        help="Type of commission line: Total or Buyer Side.",
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        required=True,
        default=lambda self: self.env.company.currency_id,
        help="Currency of the commission line.",
    )
    total_commission = fields.Monetary(
        string="Total Commission ($)",
        compute="_compute_total_commission",
        store=True,
        help="Total commission for this line.",
    )

    # Compute Fields
    @api.depends("commission_percentage", "portion_of_selling_price")
    def _compute_total_commission(self):
        for record in self:
            record.total_commission = (
                record.portion_of_selling_price * record.commission_percentage
            ) / 100

    # Onchange Methods
    @api.onchange("commission_category")
    def _onchange_commission_category(self):
        if not self.deal_id:
            return
        deal = self.deal_id
        sell_price = deal.sell_price or 0.0
        allocated_price = sum(
            deal.total_commission_line_ids.mapped("portion_of_selling_price")
        ) + sum(deal.buyer_side_commission_line_ids.mapped("portion_of_selling_price"))
        remaining_price = max(sell_price - allocated_price, 0.0)
        if self.commission_category == "first":
            self.portion_of_selling_price = remaining_price * 0.5
        elif self.commission_category == "next":
            self.portion_of_selling_price = remaining_price * 0.3
        elif self.commission_category == "remainder":
            self.portion_of_selling_price = remaining_price
        else:
            self.portion_of_selling_price = 0.0

    # Constraints
    @api.constrains(
        "portion_of_selling_price", "commission_percentage", "commission_category"
    )
    def _check_commission_values(self):
        for record in self:
            if record.portion_of_selling_price <= 0:
                raise ValidationError(
                    _("The portion of the selling price must be greater than zero.")
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
                        "Remainder or total selling price categories must have a valid portion."
                    )
                )

    # Name Get
    def name_get(self):
        result = []
        for record in self:
            name = f"{record.commission_type.capitalize()} - {record.commission_percentage}% of ${record.portion_of_selling_price:,.2f}"
            result.append((record.id, name))
        return result
