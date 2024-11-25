from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class CommissionSetupMixin(models.AbstractModel):
    _name = "commission.setup.mixin"
    _description = "Mixin for Commission Setup Fields and Methods"

    # =====================
    # Commission Templates Fields
    # =====================
    total_commission_template_id = fields.Many2one(
        "commission.template",
        string="Total Commission Template",
        tracking=True,
        index=True,
        domain="[('commission_category', '=', 'total_commission'), ('company_id', '=', company_id)]",
        help="Select a template for total commission.",
    )
    buyer_side_commission_template_id = fields.Many2one(
        "commission.template",
        string="Buyer Side Commission Template",
        tracking=True,
        index=True,
        domain="[('commission_category', '=', 'buyer_side_commission'), ('company_id', '=', company_id)]",
        help="Select a template for buyer side commission.",
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        help="Company for the record.",
    )

    # =====================
    # Onchange Methods for Dynamic Domains
    # =====================
    @api.onchange("total_commission_template_id", "buyer_side_commission_template_id")
    def _onchange_commission_template(self):
        """
        Populate or clear commission lines based on selected Commission Templates.
        """
        for rec in self:
            context_allow_population = rec._context.get(
                "populate_commission_lines", True
            )

            # Total Commission Template Handling
            if rec.total_commission_template_id and context_allow_population:
                rec._populate_commission_lines(
                    template_id=rec.total_commission_template_id,
                    line_ids_field="total_commission_line_ids",
                    commission_type_field="total_commission_type",
                    percentage_total_field="total_commission_percentage",
                    flat_fee_plus_field="aggregate_flat_fee_plus",
                    flat_fee_less_field="aggregate_flat_fee_less",
                )
            elif context_allow_population:
                rec._clear_commission_lines(
                    line_ids_field="total_commission_line_ids",
                    commission_type_field="total_commission_type",
                    percentage_total_field="total_commission_percentage",
                    flat_fee_plus_field="aggregate_flat_fee_plus",
                    flat_fee_less_field="aggregate_flat_fee_less",
                )

            # Buyer Side Commission Template Handling
            if rec.buyer_side_commission_template_id and context_allow_population:
                rec._populate_commission_lines(
                    template_id=rec.buyer_side_commission_template_id,
                    line_ids_field="buyer_side_commission_line_ids",
                    commission_type_field="buyer_side_commission_type",
                    percentage_total_field="buyer_side_commission_percentage",
                    flat_fee_plus_field="buyer_side_plus_flat_fee",
                    flat_fee_less_field="buyer_side_less_flat_fee",
                )
            elif context_allow_population:
                rec._clear_commission_lines(
                    line_ids_field="buyer_side_commission_line_ids",
                    commission_type_field="buyer_side_commission_type",
                    percentage_total_field="buyer_side_commission_percentage",
                    flat_fee_plus_field="buyer_side_plus_flat_fee",
                    flat_fee_less_field="buyer_side_less_flat_fee",
                )

    # =====================
    # Helper Methods to Populate Commission Lines
    # =====================
    def _populate_commission_lines(
        self,
        template_id,
        line_ids_field,
        commission_type_field,
        percentage_total_field,
        flat_fee_plus_field,
        flat_fee_less_field,
    ):
        """
        Populate commission lines based on the selected template.
        """
        if not template_id:
            return

        # Determine commission type based on template
        commission_type_value = self._get_commission_type_value(
            template_id.commission_category
        )

        # Clear existing commission lines
        self[line_ids_field] = [(5, 0, 0)]

        # Set commission type and percentages
        self[commission_type_field] = commission_type_value
        self[percentage_total_field] = template_id.total_commission_percentage or 0.0
        self[flat_fee_plus_field] = template_id.commission_flat_fee_plus or 0.0
        self[flat_fee_less_field] = template_id.commission_flat_fee_less or 0.0

        # Populate commission lines
        commission_template_lines = [
            (
                0,
                0,
                {
                    "commission_type": commission_type_value,
                    "commission_category": line.commission_category,
                    "portion_of_selling_price": line.portion_of_selling_price,
                    "commission_percentage": line.commission_percentage,
                },
            )
            for line in template_id.commission_template_line_ids
        ]

        if commission_template_lines:
            self[line_ids_field] = commission_template_lines
            _logger.debug(
                f"Commission lines populated from template '{template_id.name}'."
            )
        else:
            _logger.debug(
                f"No commission lines found for template '{template_id.name}'."
            )

    def _clear_commission_lines(
        self,
        line_ids_field,
        commission_type_field,
        percentage_total_field,
        flat_fee_plus_field,
        flat_fee_less_field,
    ):
        """
        Clear commission lines and reset related fields.
        """
        self[line_ids_field] = [(5, 0, 0)]
        self[commission_type_field] = False
        self[percentage_total_field] = 0.0
        self[flat_fee_plus_field] = 0.0
        self[flat_fee_less_field] = 0.0
        _logger.debug(f"Commission lines cleared for field '{line_ids_field}'.")

    def _get_commission_type_value(self, commission_category):
        """
        Determine the commission type value based on the commission category.
        """
        if commission_category == "total_commission":
            return "total"
        elif commission_category == "buyer_side_commission":
            return "buyer_side"
        return "total"  # Default value if category is unknown

    # =====================
    # Constraints
    # =====================
    @api.constrains("total_commission_template_id", "buyer_side_commission_template_id")
    def _check_commission_templates(self):
        """
        Validate the selected commission templates to ensure correct categories.
        """
        for record in self:
            if (
                record.total_commission_template_id
                and record.total_commission_template_id.commission_category
                != "total_commission"
            ):
                raise ValidationError(
                    _(
                        "The selected Total Commission Template does not match the 'total_commission' category."
                    )
                )
            if (
                record.buyer_side_commission_template_id
                and record.buyer_side_commission_template_id.commission_category
                != "buyer_side_commission"
            ):
                raise ValidationError(
                    _(
                        "The selected Buyer Side Commission Template does not match the 'buyer_side_commission' category."
                    )
                )
