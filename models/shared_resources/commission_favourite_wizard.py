# models/shared_resources/commission_favourite_wizard.py

"""
Module for managing Commission Favourite Wizard functionalities.
This wizard allows users to apply selected commission favourites to either Listing or Deal records.
It ensures that the selected favourites are compatible with the chosen record type and company.
Comprehensive logging and validation are implemented to maintain data integrity and facilitate debugging.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

# Configure the logger for this module
_logger = logging.getLogger(__name__)


class CommissionFavouriteWizard(models.TransientModel):
    """
    Wizard to Apply Commission Favourites to Listing or Deal Records.
    This wizard facilitates the selection and application of commission favourites to the specified record.
    It ensures that the selected favourites belong to the same company as the record and updates
    the commission lines accordingly.
    """
    _name = "commission.favourite.wizard"
    _description = "Wizard to Apply Commission Favourites"

    # =====================
    # Fields
    # =====================

    record_model = fields.Selection(
        [
            ("listing.records", "Listing"),
            ("deal.records", "Deal")
        ],
        string="Record Model",
        required=True,
        help="Select the type of record (Listing or Deal) to which commission favourites will be applied.",
    )
    record_id = fields.Reference(
        selection=[
            ("listing.records", "Listing Record"),
            ("deal.records", "Deal Record"),
        ],
        string="Record",
        required=True,
        help="The listing or deal record to which commission favourites will be applied.",
    )
    total_commission_favourite_id = fields.Many2one(
        "commission.favourite",
        string="Total Commission Favourite",
        domain="[('commission_category', '=', 'total_commission'), ('company_id', '=', company_id)]",
        help="Select a favourite for Total Commission based on the company.",
        index=True,
    )
    buyer_side_commission_favourite_id = fields.Many2one(
        "commission.favourite",
        string="Buyer Side Commission Favourite",
        domain="[('commission_category', '=', 'buyer_side_commission'), ('company_id', '=', company_id)]",
        help="Select a favourite for Buyer Side Commission based on the company.",
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self.env.company,
        help="Company associated with the record.",
    )

    # =====================
    # Action Methods
    # =====================

    def apply_commission_favourites(self):
        """
        Apply selected commission favourites and update commission lines on the chosen record.
        This method determines the type of record (Listing or Deal) and applies the favourites accordingly.
        """
        self.ensure_one()

        if not self.record_id:
            _logger.error("No record selected in Commission Favourite Wizard.")
            raise ValidationError(_("Please select a record to apply commission favourites."))

        if self.record_model == "listing.records":
            self._apply_favourites_to_listing()
        elif self.record_model == "deal.records":
            self._apply_favourites_to_deal()
        else:
            _logger.error(f"Invalid record model selected: {self.record_model}")
            raise ValidationError(_("Invalid record type selected."))

        _logger.info(
            f"Commission favourites applied to record ID {self.record_id.id} of model {self.record_model}."
        )
        return {"type": "ir.actions.act_window_close"}

    def _apply_favourites_to_listing(self):
        """
        Apply commission favourites to a listing record.
        Validates the record type and applies the selected commission favourites.
        """
        if self.record_id._name != "listing.records":
            _logger.error(
                f"Selected record is not a listing: {self.record_id._name} (ID: {self.record_id.id})"
            )
            raise ValidationError(_("Selected record is not a listing."))

        if self.total_commission_favourite_id:
            self._apply_commission_favourite(
                favourite=self.total_commission_favourite_id,
                record=self.record_id,
                line_ids_field="total_commission_line_ids",
                commission_type_field="total_commission_type",
                percentage_field="total_commission_percentage",
                plus_flat_field="total_plus_flat_fee",
                less_flat_field="total_less_flat_fee",
            )
        if self.buyer_side_commission_favourite_id:
            self._apply_commission_favourite(
                favourite=self.buyer_side_commission_favourite_id,
                record=self.record_id,
                line_ids_field="buyer_side_commission_line_ids",
                commission_type_field="buyer_side_commission_type",
                percentage_field="buyer_side_commission_percentage",
                plus_flat_field="buyer_side_plus_flat_fee",
                less_flat_field="buyer_side_less_flat_fee",
            )

    def _apply_favourites_to_deal(self):
        """
        Apply commission favourites to a deal record.
        Validates the record type and applies the selected commission favourites.
        """
        if self.record_id._name != "deal.records":
            _logger.error(
                f"Selected record is not a deal: {self.record_id._name} (ID: {self.record_id.id})"
            )
            raise ValidationError(_("Selected record is not a deal."))

        if self.total_commission_favourite_id:
            self._apply_commission_favourite(
                favourite=self.total_commission_favourite_id,
                record=self.record_id,
                line_ids_field="total_commission_line_ids",
                commission_type_field="total_commission_type",
                percentage_field="total_commission_percentage",
                plus_flat_field="aggregate_flat_fee_plus",
                less_flat_field="aggregate_flat_fee_less",
            )
        if self.buyer_side_commission_favourite_id:
            self._apply_commission_favourite(
                favourite=self.buyer_side_commission_favourite_id,
                record=self.record_id,
                line_ids_field="buyer_side_commission_line_ids",
                commission_type_field="buyer_side_commission_type",
                percentage_field="buyer_side_commission_percentage",
                plus_flat_field="buyer_side_plus_flat_fee",
                less_flat_field="buyer_side_less_flat_fee",
            )

    def _apply_commission_favourite(
        self,
        favourite,
        record,
        line_ids_field,
        commission_type_field,
        percentage_field,
        plus_flat_field,
        less_flat_field,
    ):
        """
        Apply a single commission favourite to a record by updating commission-related fields and lines.

        Args:
            favourite (recordset): The selected commission favourite record.
            record (recordset): The target record (Listing or Deal) to apply the favourite to.
            line_ids_field (str): The field name for commission lines on the record.
            commission_type_field (str): The field name for commission type on the record.
            percentage_field (str): The field name for total commission percentage on the record.
            plus_flat_field (str): The field name for aggregate flat fee plus on the record.
            less_flat_field (str): The field name for aggregate flat fee less on the record.
        """
        _logger.debug(
            f"Applying commission favourite '{favourite.name}' to record ID {record.id}."
        )

        # Update commission-related fields
        record[commission_type_field] = favourite.commission_type
        record[percentage_field] = favourite.total_commission_percentage or 0.0
        record[plus_flat_field] = favourite.commission_flat_fee_plus or 0.0
        record[less_flat_field] = favourite.commission_flat_fee_less or 0.0
        _logger.debug(
            f"Updated fields for record ID {record.id}: "
            f"{commission_type_field}={record[commission_type_field]}, "
            f"{percentage_field}={record[percentage_field]}, "
            f"{plus_flat_field}={record[plus_flat_field]}, "
            f"{less_flat_field}={record[less_flat_field]}"
        )

        # Clear existing commission lines
        record[line_ids_field] = [(5, 0, 0)]
        _logger.debug(f"Cleared existing commission lines for field '{line_ids_field}' on record ID {record.id}.")

        # Populate commission lines from favourite
        commission_lines = [
            (
                0,
                0,
                {
                    "commission_type": self._get_commission_type_value(favourite.commission_category),
                    "commission_category": line.commission_category,
                    "portion_of_selling_price": line.portion_of_selling_price,
                    "commission_percentage": line.commission_percentage,
                },
            )
            for line in favourite.commission_favourite_line_ids
        ]

        if commission_lines:
            record[line_ids_field] = commission_lines
            _logger.debug(
                f"Commission lines populated from favourite '{favourite.name}' for field '{line_ids_field}' on record ID {record.id}."
            )
        else:
            _logger.warning(
                f"No commission lines found in favourite '{favourite.name}' to populate for record ID {record.id}."
            )

    def _get_commission_type_value(self, category):
        """
        Map commission category to its corresponding type value.

        Args:
            category (str): The commission category.

        Returns:
            str: The corresponding commission type value.
        """
        mapping = {
            "total_commission": "total",
            "buyer_side_commission": "buyer_side",
        }
        commission_type = mapping.get(category, "total")
        _logger.debug(
            f"Mapped commission category '{category}' to commission type '{commission_type}'."
        )
        return commission_type

    # =====================
    # Onchange Methods
    # =====================

    @api.onchange("record_id")
    def _onchange_record_id(self):
        """
        Pre-populate fields based on the selected record.
        Sets the company_id and pre-fills commission favourite selections if applicable.
        """
        if self.record_id:
            self.company_id = self.record_id.company_id.id
            _logger.debug(
                f"Pre-populating wizard fields based on selected record ID {self.record_id.id}."
            )
            if self.record_model == "listing.records":
                self.total_commission_favourite_id = self.record_id.total_commission_favourite_id
                self.buyer_side_commission_favourite_id = self.record_id.buyer_side_commission_favourite_id
                _logger.debug("Pre-populated commission favourites for Listing record.")
            elif self.record_model == "deal.records":
                self.total_commission_favourite_id = self.record_id.total_commission_favourite_id
                self.buyer_side_commission_favourite_id = self.record_id.buyer_side_commission_favourite_id
                _logger.debug("Pre-populated commission favourites for Deal record.")
        else:
            self.total_commission_favourite_id = False
            self.buyer_side_commission_favourite_id = False
            _logger.debug("Cleared commission favourites as no record is selected.")

    # =====================
    # Constraints
    # =====================
    @api.constrains("total_commission_favourite_id", "buyer_side_commission_favourite_id")
    def _check_favourites_company_match(self):
        """
        Ensure that selected favourites belong to the same company as the record.

        Raises:
            ValidationError: If any selected favourite does not belong to the same company.
        """
        for wizard in self:
            if wizard.record_id:
                company_id = wizard.record_id.company_id.id
                if wizard.total_commission_favourite_id:
                    if wizard.total_commission_favourite_id.company_id.id != company_id:
                        _logger.error(
                            f"Total Commission Favourite company ID {wizard.total_commission_favourite_id.company_id.id} "
                            f"does not match record's company ID {company_id}."
                        )
                        raise ValidationError(
                            _("Total Commission Favourite must belong to the same company as the record.")
                        )
                if wizard.buyer_side_commission_favourite_id:
                    if wizard.buyer_side_commission_favourite_id.company_id.id != company_id:
                        _logger.error(
                            f"Buyer Side Commission Favourite company ID {wizard.buyer_side_commission_favourite_id.company_id.id} "
                            f"does not match record's company ID {company_id}."
                        )
                        raise ValidationError(
                            _("Buyer Side Commission Favourite must belong to the same company as the record.")
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