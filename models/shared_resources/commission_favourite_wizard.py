# models/shared_resources/commission_favourite_wizard.py

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class CommissionFavouriteWizard(models.TransientModel):
    _name = "commission.favourite.wizard"
    _description = "Wizard to Apply Commission Favourites"

    # =====================
    # Fields
    # =====================
    record_model = fields.Selection(
        [("listing.records", "Listing"), ("deal.records", "Deal")],
        string="Record Model",
        required=True,
        help="Select the type of record (Listing or Deal).",
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
    )
    buyer_side_commission_favourite_id = fields.Many2one(
        "commission.favourite",
        string="Buyer Side Commission Favourite",
        domain="[('commission_category', '=', 'buyer_side_commission'), ('company_id', '=', company_id)]",
        help="Select a favourite for Buyer Side Commission based on the company.",
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
        Apply selected commission favourites and update commission lines.
        """
        self.ensure_one()

        if not self.record_id:
            raise ValidationError(
                _("Please select a record to apply commission favourites.")
            )

        if self.record_model == "listing.records":
            self._apply_favourites_to_listing()
        elif self.record_model == "deal.records":
            self._apply_favourites_to_deal()
        else:
            raise ValidationError(_("Invalid record type."))

        return {"type": "ir.actions.act_window_close"}

    def _apply_favourites_to_listing(self):
        """
        Apply commission favourites to a listing record.
        """
        if not self.record_id._name == "listing.records":
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
        """
        if not self.record_id._name == "deal.records":
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
        Apply a single commission favourite to a record.
        """
        record[commission_type_field] = favourite.commission_type
        record[percentage_field] = favourite.total_commission_percentage or 0.0
        record[plus_flat_field] = favourite.commission_flat_fee_plus or 0.0
        record[less_flat_field] = favourite.commission_flat_fee_less or 0.0

        # Clear existing commission lines
        record[line_ids_field] = [(5, 0, 0)]

        # Populate commission lines
        commission_lines = [
            (
                0,
                0,
                {
                    "commission_type": self._get_commission_type_value(
                        favourite.commission_category
                    ),
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
                f"Commission lines populated from favourite '{favourite.name}'."
            )

    def _get_commission_type_value(self, category):
        """
        Map commission category to its corresponding type value.
        """
        return {
            "total_commission": "total",
            "buyer_side_commission": "buyer_side",
        }.get(category, "total")

    # =====================
    # Onchange Methods
    # =====================
    @api.onchange("record_id")
    def _onchange_record_id(self):
        """
        Pre-populate fields based on the selected record.
        """
        if self.record_id:
            self.company_id = self.record_id.company_id.id
            if self.record_model == "listing.records":
                self.total_commission_favourite_id = (
                    self.record_id.total_commission_favourite_id
                )
                self.buyer_side_commission_favourite_id = (
                    self.record_id.buyer_side_commission_favourite_id
                )
            elif self.record_model == "deal.records":
                self.total_commission_favourite_id = (
                    self.record_id.total_commission_favourite_id
                )
                self.buyer_side_commission_favourite_id = (
                    self.record_id.buyer_side_commission_favourite_id
                )
        else:
            self.total_commission_favourite_id = False
            self.buyer_side_commission_favourite_id = False

    # =====================
    # Constraints
    # =====================
    @api.constrains(
        "total_commission_favourite_id", "buyer_side_commission_favourite_id"
    )
    def _check_favourites_company_match(self):
        """
        Ensure that selected favourites belong to the same company as the record.
        """
        for wizard in self:
            if wizard.record_id:
                company_id = wizard.record_id.company_id.id
                if (
                    wizard.total_commission_favourite_id
                    and wizard.total_commission_favourite_id.company_id.id != company_id
                ):
                    raise ValidationError(
                        _(
                            "Total Commission Favourite must belong to the same company as the record."
                        )
                    )
                if (
                    wizard.buyer_side_commission_favourite_id
                    and wizard.buyer_side_commission_favourite_id.company_id.id
                    != company_id
                ):
                    raise ValidationError(
                        _(
                            "Buyer Side Commission Favourite must belong to the same company as the record."
                        )
                    )
