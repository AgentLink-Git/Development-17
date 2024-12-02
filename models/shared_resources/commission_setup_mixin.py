# models/shared_resources/commission_setup_mixin.py

"""
Module for managing Commission Setup Mixins.
This mixin provides shared fields and methods for managing commission templates,
including functionalities to populate and clear commission lines based on selected templates.
Comprehensive logging and validation are implemented to maintain data integrity and facilitate debugging.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

# Configure the logger for this module
_logger = logging.getLogger(__name__)


class CommissionSetupMixin(models.AbstractModel):
    """
    Mixin for Commission Setup Fields and Methods.
    This abstract model provides shared fields and methods to manage commission templates
    and their associated commission lines. It facilitates the population and clearing
    of commission lines based on selected templates, ensuring consistency and data integrity.
    """
    _name = "commission.setup.mixin"
    _description = "Mixin for Commission Setup Fields and Methods"

    # =====================
    # Commission Templates Fields
    # =====================

    total_commission_template_id = fields.Many2one(
        "commission.template",
        string="Total Commission Template",
        index=True,
        domain="[('commission_category', '=', 'total_commission'), ('company_id', '=', company_id)]",
        help="Select a template for total commission.",
    )
    buyer_side_commission_template_id = fields.Many2one(
        "commission.template",
        string="Buyer Side Commission Template",
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
        This method handles both Total and Buyer Side commission templates,
        ensuring that commission lines are appropriately populated or cleared
        when templates are selected or deselected.
        """
        for rec in self:
            context_allow_population = rec._context.get("populate_commission_lines", True)

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

        Args:
            template_id (recordset): The selected commission template.
            line_ids_field (str): The field name for commission lines on the record.
            commission_type_field (str): The field name for commission type on the record.
            percentage_total_field (str): The field name for total commission percentage on the record.
            flat_fee_plus_field (str): The field name for aggregate flat fee plus on the record.
            flat_fee_less_field (str): The field name for aggregate flat fee less on the record.
        """
        if not template_id:
            _logger.debug("No commission template selected; skipping population of commission lines.")
            return

        # Determine commission type based on template
        commission_type_value = self._get_commission_type_value(template_id.commission_category)
        _logger.debug(
            f"Determined commission_type_value '{commission_type_value}' for commission category '{template_id.commission_category}'."
        )

        # Clear existing commission lines
        self[line_ids_field] = [(5, 0, 0)]
        _logger.debug(f"Cleared existing commission lines for field '{line_ids_field}'.")

        # Set commission type and percentages
        self[commission_type_field] = commission_type_value
        self[percentage_total_field] = template_id.total_commission_percentage or 0.0
        self[flat_fee_plus_field] = template_id.commission_flat_fee_plus or 0.0
        self[flat_fee_less_field] = template_id.commission_flat_fee_less or 0.0
        _logger.debug(
            f"Set fields for '{commission_type_field}' to '{commission_type_value}', "
            f"'{percentage_total_field}' to {self[percentage_total_field]}, "
            f"'{flat_fee_plus_field}' to {self[flat_fee_plus_field]}, "
            f"'{flat_fee_less_field}' to {self[flat_fee_less_field]}."
        )

        # Populate commission lines from template
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
            _logger.debug(f"Commission lines populated from template '{template_id.name}'.")
        else:
            _logger.warning(f"No commission lines found in template '{template_id.name}' to populate.")

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

        Args:
            line_ids_field (str): The field name for commission lines on the record.
            commission_type_field (str): The field name for commission type on the record.
            percentage_total_field (str): The field name for total commission percentage on the record.
            flat_fee_plus_field (str): The field name for aggregate flat fee plus on the record.
            flat_fee_less_field (str): The field name for aggregate flat fee less on the record.
        """
        self[line_ids_field] = [(5, 0, 0)]
        self[commission_type_field] = False
        self[percentage_total_field] = 0.0
        self[flat_fee_plus_field] = 0.0
        self[flat_fee_less_field] = 0.0
        _logger.debug(
            f"Cleared commission lines and reset fields for '{line_ids_field}', "
            f"'{commission_type_field}', '{percentage_total_field}', "
            f"'{flat_fee_plus_field}', and '{flat_fee_less_field}'."
        )

    def _get_commission_type_value(self, commission_category):
        """
        Determine the commission type value based on the commission category.

        Args:
            commission_category (str): The commission category.

        Returns:
            str: The corresponding commission type value.
        """
        mapping = {
            "total_commission": "total",
            "buyer_side_commission": "buyer_side",
        }
        commission_type = mapping.get(commission_category, "total")
        _logger.debug(
            f"Mapped commission_category '{commission_category}' to commission_type '{commission_type}'."
        )
        return commission_type

    # =====================
    # Constraints
    # =====================

    @api.constrains("total_commission_template_id", "buyer_side_commission_template_id")
    def _check_commission_templates(self):
        """
        Validate the selected commission templates to ensure correct categories.

        Raises:
            ValidationError: If any selected commission template does not match the expected category.
        """
        for record in self:
            if (
                record.total_commission_template_id
                and record.total_commission_template_id.commission_category != "total_commission"
            ):
                _logger.error(
                    f"Invalid commission_category '{record.total_commission_template_id.commission_category}' "
                    f"for Total Commission Template '{record.total_commission_template_id.name}' (ID: {record.total_commission_template_id.id})."
                )
                raise ValidationError(
                    _("The selected Total Commission Template does not match the 'total_commission' category.")
                )
            if (
                record.buyer_side_commission_template_id
                and record.buyer_side_commission_template_id.commission_category != "buyer_side_commission"
            ):
                _logger.error(
                    f"Invalid commission_category '{record.buyer_side_commission_template_id.commission_category}' "
                    f"for Buyer Side Commission Template '{record.buyer_side_commission_template_id.name}' (ID: {record.buyer_side_commission_template_id.id})."
                )
                raise ValidationError(
                    _("The selected Buyer Side Commission Template does not match the 'buyer_side_commission' category.")
                )