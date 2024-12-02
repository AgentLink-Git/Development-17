# models/deals/deal_statistics.py

"""
Module for extending Deal Records with statistical computations, including commission distributions,
market analysis, and tracking of deal-related financial metrics.
"""

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

# Configure the logger for this module
_logger = logging.getLogger(__name__)


class DealRecords(models.Model):
    """
    Inherited model from 'deal.records' to add statistical fields and computations related to deals.
    This includes calculations for commissions sent to the office, market performance metrics,
    and tracking of conveyancing activities.
    """
    _inherit = "deal.records"
    _description = "Deal Records Extension for Statistics"

    # =====================
    # Deal Statistics Fields
    # =====================
    seller_side_to_office = fields.Monetary(
        string="Seller Side to Office",
        currency_field="currency_id",
        compute="_compute_seller_side_to_office",
        store=True,
    )
    buyer_side_to_office = fields.Monetary(
        string="Buyer Side to Office",
        currency_field="currency_id",
        compute="_compute_buyer_side_to_office",
        store=True,
    )
    total_to_office = fields.Monetary(
        string="Total to Office",
        currency_field="currency_id",
        compute="_compute_total_to_office",
        store=True,
    )
    ask_vs_sell = fields.Float(
        string="% Ask vs Sell",
        compute="_compute_ask_vs_sell",
        store=True,
        help="Percentage difference between sell price and list price.",
    )
    days_on_market = fields.Integer(
        string="Days on Market",
        compute="_compute_days_on_market",
        store=True,
        help="Number of days the deal has been on the market.",
    )
    no_of_ends = fields.Float(
        related="deal_class_id.no_of_ends",
        string="# End",
        store=True,
        readonly=True,
        help="Number of ends associated with the deal class.",
    )
    conveyancing_done = fields.Boolean(
        string="Conveyancing Done",
        help="Indicates whether conveyancing has been completed.",
    )
    lawyer_payout_letter = fields.Boolean(
        string="Lawyer Payout Letter",
        help="Indicates whether the lawyer payout letter has been received.",
    )

    # =====================
    # Computation Methods
    # =====================

    @api.depends("sales_agents_and_referrals_ids.commission_plan_line_ids.split_fees")
    def _compute_seller_side_to_office(self):
        """
        Compute the total seller side commissions sent to the office.
        """
        for deal in self:
            seller_commissions = deal.sales_agents_and_referrals_ids.filtered(
                lambda sa: sa.end_id.type in ["seller", "landlord"]
            )
            total = sum(seller_commissions.mapped("commission_plan_line_ids.split_fees"))
            deal.seller_side_to_office = total if seller_commissions else 0.0
            _logger.debug(
                "Deal ID %s: Computed seller_side_to_office as %s",
                deal.id, deal.seller_side_to_office
            )

    @api.depends("sales_agents_and_referrals_ids.commission_plan_line_ids.split_fees")
    def _compute_buyer_side_to_office(self):
        """
        Compute the total buyer side commissions sent to the office.
        """
        for deal in self:
            buyer_commissions = deal.sales_agents_and_referrals_ids.filtered(
                lambda sa: sa.end_id.type in ["buyer", "tenant"]
            )
            total = sum(buyer_commissions.mapped("commission_plan_line_ids.split_fees"))
            deal.buyer_side_to_office = total if buyer_commissions else 0.0
            _logger.debug(
                "Deal ID %s: Computed buyer_side_to_office as %s",
                deal.id, deal.buyer_side_to_office
            )

    @api.depends("seller_side_to_office", "buyer_side_to_office")
    def _compute_total_to_office(self):
        """
        Compute the total commissions sent to the office.
        """
        for deal in self:
            deal.total_to_office = deal.seller_side_to_office + deal.buyer_side_to_office
            _logger.debug(
                "Deal ID %s: Computed total_to_office as %s",
                deal.id, deal.total_to_office
            )

    @api.depends("sell_price", "list_price")
    def _compute_ask_vs_sell(self):
        """
        Compute the percentage difference between sell price and list price.
        """
        for deal in self:
            if deal.list_price:
                deal.ask_vs_sell = (deal.sell_price / deal.list_price) * 100
            else:
                deal.ask_vs_sell = 0.0
            _logger.debug(
                "Deal ID %s: Computed ask_vs_sell as %s%%",
                deal.id, deal.ask_vs_sell
            )

    @api.depends("list_date", "offer_date", "end_id.type")
    def _compute_days_on_market(self):
        """
        Compute the number of days the deal has been on the market.
        """
        today = fields.Date.today()
        for deal in self:
            if deal.end_id.type in ["buyer", "tenant"]:
                deal.days_on_market = 0
            else:
                if deal.list_date and deal.offer_date:
                    delta = (deal.offer_date - deal.list_date).days
                    deal.days_on_market = max(delta, 0)
                else:
                    deal.days_on_market = 0
            _logger.debug(
                "Deal ID %s: Computed days_on_market as %s",
                deal.id, deal.days_on_market
            )

    # =====================
    # Onchange Methods
    # =====================

    @api.onchange("sales_agents_and_referrals_ids")
    def _onchange_sales_agents_and_referrals_ids(self):
        """
        Trigger computation of commissions when sales_agents_and_referrals_ids change.
        """
        for deal in self:
            deal._compute_seller_side_to_office()
            deal._compute_buyer_side_to_office()
            deal._compute_total_to_office()
            _logger.debug(
                "Deal ID %s: Triggered onchange computation for commissions.",
                deal.id
            )

    # =====================
    # Constraints
    # =====================

    @api.constrains("seller_side_to_office", "buyer_side_to_office", "total_to_office")
    def _check_office_portion(self):
        """
        Ensure that the office portions are not negative.
        """
        for deal in self:
            if deal.seller_side_to_office < 0:
                raise ValidationError(_("Seller Side to Office cannot be negative."))
            if deal.buyer_side_to_office < 0:
                raise ValidationError(_("Buyer Side to Office cannot be negative."))
            if deal.total_to_office < 0:
                raise ValidationError(_("Total to Office cannot be negative."))
            _logger.debug(
                "Deal ID %s: Validated office portions.",
                deal.id
            )