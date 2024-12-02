# models/shared_resources/commission_favourite_mixin.py

"""
Module for managing Commission Favourite functionalities.
This mixin provides mechanisms to handle commission favourites, including selecting
favourite commission configurations and updating related commission lines accordingly.
It ensures data integrity through constraints and provides comprehensive logging for auditing
and debugging purposes.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

# Configure the logger for this module
_logger = logging.getLogger(__name__)


class CommissionFavouriteMixin(models.AbstractModel):
    """
    Abstract model providing commission favourite management functionalities.
    This mixin includes fields for selecting commission favourites and handles the logic
    to populate or clear commission lines based on the selected favourites. It ensures
    that the selected favourites belong to the correct commission categories.
    """
    _name = "commission.favourite.mixin"
    _description = "Mixin for Commission Favourite Management"

    # =====================
    # Fields
    # =====================

    total_commission_favourite_id = fields.Many2one(
        "commission.favourite",
        string="Total Commission Favourite",
        domain="[('commission_category', '=', 'total_commission'), ('company_id', '=', company_id)]",
        help="Select a favourite for total commission.",
        index=True,
    )
    buyer_side_commission_favourite_id = fields.Many2one(
        "commission.favourite",
        string="Buyer Side Commission Favourite",
        domain="[('commission_category', '=', 'buyer_side_commission'), ('company_id', '=', company_id)]",
        help="Select a favourite for buyer side commission.",
        index=True,
    )

    # =====================
    # Onchange Methods
    # =====================

    @api.onchange("total_commission_favourite_id", "buyer_side_commission_favourite_id")
    def _onchange_commission_favourite(self):
        """
        Handle changes in commission favourites and update related commission lines and fields.
        This method is triggered when either the total commission favourite or buyer side commission
        favourite is changed. It populates or clears the commission lines based on the selected
        favourites unless the context specifies to skip population.
        """
        for rec in self:
            context = rec._context or {}
            if context.get("populate_commission_lines", True):
                # Update Total Commission Favourite
                rec._handle_commission_favourite_update(
                    favourite_id=rec.total_commission_favourite_id,
                    line_ids_field="total_commission_line_ids",
                    commission_type_field="total_commission_type",
                    percentage_total_field="total_commission_percentage",
                    flat_fee_plus_field="aggregate_flat_fee_plus",
                    flat_fee_less_field="aggregate_flat_fee_less",
                )
                # Update Buyer Side Commission Favourite
                rec._handle_commission_favourite_update(
                    favourite_id=rec.buyer_side_commission_favourite_id,
                    line_ids_field="buyer_side_commission_line_ids",
                    commission_type_field="buyer_side_commission_type",
                    percentage_total_field="buyer_side_commission_percentage",
                    flat_fee_plus_field="buyer_side_plus_flat_fee",
                    flat_fee_less_field="buyer_side_less_flat_fee",
                )
            else:
                _logger.debug(f"Skipped commission line population for record {rec.id}.")

    # =====================
    # Helper Methods
    # =====================

    def _handle_commission_favourite_update(
        self,
        favourite_id,
        line_ids_field,
        commission_type_field,
        percentage_total_field,
        flat_fee_plus_field,
        flat_fee_less_field,
    ):
        """
        Update commission lines and related fields based on a given favourite.

        Args:
            favourite_id (recordset): The selected commission favourite record.
            line_ids_field (str): The field name for commission lines.
            commission_type_field (str): The field name for commission type.
            percentage_total_field (str): The field name for total commission percentage.
            flat_fee_plus_field (str): The field name for aggregate flat fee plus.
            flat_fee_less_field (str): The field name for aggregate flat fee less.
        """
        if favourite_id:
            self._populate_commission_lines(
                favourite_id=favourite_id,
                line_ids_field=line_ids_field,
                commission_type_field=commission_type_field,
                percentage_total_field=percentage_total_field,
                flat_fee_plus_field=flat_fee_plus_field,
                flat_fee_less_field=flat_fee_less_field,
            )
        else:
            self._clear_commission_lines(
                line_ids_field=line_ids_field,
                commission_type_field=commission_type_field,
                percentage_total_field=percentage_total_field,
                flat_fee_plus_field=flat_fee_plus_field,
                flat_fee_less_field=flat_fee_less_field,
            )

    def _populate_commission_lines(
        self,
        favourite_id,
        line_ids_field,
        commission_type_field,
        percentage_total_field,
        flat_fee_plus_field,
        flat_fee_less_field,
    ):
        """
        Populate commission lines based on the selected favourite.

        Args:
            favourite_id (recordset): The selected commission favourite record.
            line_ids_field (str): The field name for commission lines.
            commission_type_field (str): The field name for commission type.
            percentage_total_field (str): The field name for total commission percentage.
            flat_fee_plus_field (str): The field name for aggregate flat fee plus.
            flat_fee_less_field (str): The field name for aggregate flat fee less.
        """
        if not favourite_id:
            return

        # Clear existing commission lines
        self[line_ids_field] = [(5, 0, 0)]
        _logger.debug(f"Cleared existing commission lines for field '{line_ids_field}'.")

        # Populate commission-related fields
        self[commission_type_field] = favourite_id.commission_type
        self[percentage_total_field] = favourite_id.total_commission_percentage or 0.0
        self[flat_fee_plus_field] = favourite_id.commission_flat_fee_plus or 0.0
        self[flat_fee_less_field] = favourite_id.commission_flat_fee_less or 0.0
        _logger.debug(
            f"Updated fields: {commission_type_field}={self[commission_type_field]}, "
            f"{percentage_total_field}={self[percentage_total_field]}, "
            f"{flat_fee_plus_field}={self[flat_fee_plus_field]}, "
            f"{flat_fee_less_field}={self[flat_fee_less_field]}"
        )

        # Populate commission lines
        lines_to_create = [
            (
                0,
                0,
                {
                    "commission_type": self._get_commission_type_value(favourite_id.commission_category),
                    "commission_category": line.commission_category,
                    "portion_of_selling_price": line.portion_of_selling_price,
                    "commission_percentage": line.commission_percentage,
                },
            )
            for line in favourite_id.commission_favourite_line_ids
        ]

        if lines_to_create:
            self[line_ids_field] = lines_to_create
            _logger.debug(
                f"Commission lines populated from favourite '{favourite_id.name}' for field '{line_ids_field}'."
            )
        else:
            _logger.debug(f"No commission lines found for favourite '{favourite_id.name}'.")

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
            line_ids_field (str): The field name for commission lines.
            commission_type_field (str): The field name for commission type.
            percentage_total_field (str): The field name for total commission percentage.
            flat_fee_plus_field (str): The field name for aggregate flat fee plus.
            flat_fee_less_field (str): The field name for aggregate flat fee less.
        """
        self[line_ids_field] = [(5, 0, 0)]
        self[commission_type_field] = False
        self[percentage_total_field] = 0.0
        self[flat_fee_plus_field] = 0.0
        self[flat_fee_less_field] = 0.0
        _logger.debug(
            f"Cleared commission lines and reset fields for '{line_ids_field}'."
        )

    def _get_commission_type_value(self, commission_category):
        """
        Map commission category to commission type value.

        Args:
            commission_category (str): The commission category.

        Returns:
            str: The corresponding commission type value.
        """
        mapping = {
            'total_commission': 'total',
            'buyer_side_commission': 'buyer_side',
        }
        commission_type = mapping.get(commission_category, 'total')
        _logger.debug(
            f"Mapped commission category '{commission_category}' to commission type '{commission_type}'."
        )
        return commission_type

    # =====================
    # Constraints
    # =====================

    @api.constrains("total_commission_favourite_id", "buyer_side_commission_favourite_id")
    def _check_commission_favourite_categories(self):
        """
        Validate that selected commission favourites match their respective categories.

        Raises:
            ValidationError: If selected favourites do not belong to the correct categories.
        """
        for rec in self:
            if (
                rec.total_commission_favourite_id
                and rec.total_commission_favourite_id.commission_category != "total_commission"
            ):
                _logger.error(
                    f"Invalid commission category for Total Commission Favourite: '{rec.total_commission_favourite_id.commission_category}' in record ID {rec.id}."
                )
                raise ValidationError(
                    _("The selected Total Commission Favourite does not belong to the 'total_commission' category.")
                )
            if (
                rec.buyer_side_commission_favourite_id
                and rec.buyer_side_commission_favourite_id.commission_category != "buyer_side_commission"
            ):
                _logger.error(
                    f"Invalid commission category for Buyer Side Commission Favourite: '{rec.buyer_side_commission_favourite_id.commission_category}' in record ID {rec.id}."
                )
                raise ValidationError(
                    _("The selected Buyer Side Commission Favourite does not belong to the 'buyer_side_commission' category.")
                )

    # =====================
    # Logging
    # =====================

    def _log_commission_update(self, field_name, old_value, new_value):
        """
        Utility method for logging commission updates.

        Args:
            field_name (str): The name of the field being updated.
            old_value (Any): The old value of the field.
            new_value (Any): The new value of the field.
        """
        _logger.info(f"Updated {field_name}: {old_value} -> {new_value}")