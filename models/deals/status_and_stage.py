# models/deals/status_and_stage.py

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StatusAndStage(models.Model):
    _inherit = "deal.records"
    _description = "Deal Records Extension for Status and Stage"

    # =====================
    # Stage Field Integration
    # =====================
    stage = fields.Selection(
        [
            ("draft", "Draft"),
            ("collapsed", "Collapsed"),
            ("reopened", "Re-Opened"),
            ("payout_now", "Close & Pay Deal"),
            ("awaiting_payout", "Awaiting Funds"),
            ("awaiting_lawyer_letter", "Awaiting Lawyer Letter"),
            ("awaiting_possession", "Awaiting Possession"),
            ("convey_now", "Convey Now"),
            ("pay_trust_excess", "Pay Trust Excess"),
            ("law_firm_required", "Law Firm Required"),
            ("deposit_required", "Deposit Required"),
            ("documents_required", "Documents Required"),
            ("deposit_and_law_firm_required", "Deposit & Law Firm Required"),
            ("conditions_remaining", "Conditions Remaining"),
            ("agent_approval", "Agent Approval"),
            ("close", "Closed"),
        ],
        string="Stage",
        compute="_compute_stage",
        store=True,
        tracking=True,
        help="Current stage of the deal.",
    )

    # =====================
    # Status Field Integration
    # =====================
    status = fields.Selection(
        [
            ("firm", "Firm"),
            ("pending", "Pending"),
            ("collapsed", "Collapsed"),
            ("close", "Closed"),
        ],
        string="Status",
        compute="_compute_status",
        store=True,
        tracking=True,
        help="Current status of the deal.",
    )

    # =====================
    # Helper Fields
    # =====================
    firm = fields.Boolean(
        string="Firm",
        compute="_compute_firm_and_firm_date",
        store=True,
        readonly=True,
        tracking=True,
    )
    firm_date = fields.Date(
        string="Firm Date",
        compute="_compute_firm_and_firm_date",
        store=True,
        readonly=True,
        tracking=True,
    )
    deposits_received = fields.Boolean(
        string="All Deposits Received",
        compute="_compute_deposits_received",
        store=True,
        readonly=True,
        tracking=True,
    )
    missing_law_firm = fields.Boolean(
        string="Missing Law Firm",
        compute="_compute_missing_law_firm",
        store=True,
        readonly=True,
        tracking=True,
    )
    required_documents_received = fields.Boolean(
        string="Required Documents Received",
        compute="_compute_required_documents_received",
        store=True,
        readonly=True,
        tracking=True,
    )
    is_closed = fields.Boolean(
        string="Is Closed",
        default=False,
        tracking=True,
    )
    # =====================
    # Stage Computation Method
    # =====================
    @api.depends(
        "collapsed_sale",
        "collapsed_date",
        "firm",
        "missing_law_firm",
        "end_id.type",
        "conveyancing_done",
        "deposits_received",
        "required_documents_received",
        "our_trust_excess_held",
        "seller_broker_conveys_to_seller_lawyer",
        "seller_broker_conveys_to_buyer_lawyer",
        "seller_broker_conveys_to_buyer_broker",
        "buyer_broker_conveys_to_seller_lawyer",
        "buyer_broker_conveys_to_buyer_lawyer",
        "buyer_broker_conveys_to_seller_broker",
        "due_to_our_brokerage",
        "commission_received",
        "possession_date",
        "agent_confirmation",
        "payout_available",
        "lawyer_payout_letter",
        "is_closed",
    )
    def _compute_stage(self):
        today_date = fields.Date.today()
        for deal in self:
            if deal.is_closed:
                deal.stage = "close"
                continue
            if deal.collapsed_sale:
                deal.stage = "collapsed"
                continue

            if not deal.firm and not deal.collapsed_sale:
                deal.stage = "conditions_remaining"
                continue

            if (
                deal.firm
                and not deal.collapsed_sale
                and not deal.deposits_received
                and not deal.missing_law_firm
            ):
                deal.stage = "deposit_required"
                continue

            if (
                deal.firm
                and not deal.collapsed_sale
                and deal.deposits_received
                and deal.missing_law_firm
                and not deal.conveyancing_done
            ):
                deal.stage = "law_firm_required"
                continue

            if (
                deal.firm
                and not deal.collapsed_sale
                and not deal.deposits_received
                and deal.missing_law_firm
                and not deal.conveyancing_done
            ):
                deal.stage = "deposit_and_law_firm_required"
                continue

            if (
                deal.firm
                and not deal.collapsed_sale
                and deal.deposits_received
                and not deal.missing_law_firm
                and not deal.agent_confirmation
                and not deal.conveyancing_done
            ):
                deal.stage = "agent_approval"
                continue

            if (
                deal.firm
                and not deal.collapsed_sale
                and deal.deposits_received
                and not deal.missing_law_firm
                and deal.agent_confirmation
                and not deal.conveyancing_done
                and deal.our_trust_excess_held > 0
            ):
                deal.stage = "pay_trust_excess"
                continue

            if (
                deal.firm
                and not deal.collapsed_sale
                and deal.deposits_received
                and not deal.missing_law_firm
                and deal.agent_confirmation
                and not deal.conveyancing_done
                and deal.our_trust_excess_held == 0
                and not deal.required_documents_received
            ):
                deal.stage = "documents_required"
                continue

            if (
                deal.firm
                and not deal.collapsed_sale
                and deal.deposits_received
                and not deal.missing_law_firm
                and deal.agent_confirmation
                and not deal.conveyancing_done
                and deal.our_trust_excess_held == 0
                and deal.required_documents_received
                and (
                    (
                        deal.end_id.type in ["seller", "landlord"]
                        and (
                            deal.seller_broker_conveys_to_seller_lawyer
                            or deal.seller_broker_conveys_to_buyer_lawyer
                            or deal.seller_broker_conveys_to_buyer_broker
                        )
                    )
                    or (
                        deal.end_id.type in ["buyer", "tenant"]
                        and (
                            deal.buyer_broker_conveys_to_seller_lawyer
                            or deal.buyer_broker_conveys_to_buyer_lawyer
                            or deal.buyer_broker_conveys_to_seller_broker
                        )
                    )
                )
            ):
                deal.stage = "convey_now"
                continue

            if (
                deal.firm
                and not deal.collapsed_sale
                and deal.deposits_received
                and not deal.missing_law_firm
                and deal.agent_confirmation
                and deal.our_trust_excess_held == 0
                and deal.required_documents_received
                and today_date < deal.possession_date
                and (
                    deal.conveyancing_done
                    or (
                        deal.end_id.type in ["seller", "landlord"]
                        and not any(
                            [
                                deal.seller_broker_conveys_to_seller_lawyer,
                                deal.seller_broker_conveys_to_buyer_lawyer,
                                deal.seller_broker_conveys_to_buyer_broker,
                            ]
                        )
                    )
                    or (
                        deal.end_id.type in ["buyer", "tenant"]
                        and not any(
                            [
                                deal.buyer_broker_conveys_to_seller_lawyer,
                                deal.buyer_broker_conveys_to_buyer_lawyer,
                                deal.buyer_broker_conveys_to_seller_broker,
                            ]
                        )
                    )
                )
            ):
                deal.stage = "awaiting_possession"
                continue

            if (
                deal.firm
                and not deal.collapsed_sale
                and deal.deposits_received
                and not deal.missing_law_firm
                and deal.agent_confirmation
                and deal.our_trust_excess_held == 0
                and deal.required_documents_received
                and today_date >= deal.possession_date
                and deal.due_to_our_brokerage > 0
                and not deal.lawyer_payout_letter
                and (
                    deal.conveyancing_done
                    or (
                        deal.end_id.type in ["seller", "landlord"]
                        and not any(
                            [
                                deal.seller_broker_conveys_to_seller_lawyer,
                                deal.seller_broker_conveys_to_buyer_lawyer,
                                deal.seller_broker_conveys_to_buyer_broker,
                            ]
                        )
                    )
                    or (
                        deal.end_id.type in ["buyer", "tenant"]
                        and not any(
                            [
                                deal.buyer_broker_conveys_to_seller_lawyer,
                                deal.buyer_broker_conveys_to_buyer_lawyer,
                                deal.buyer_broker_conveys_to_seller_broker,
                            ]
                        )
                    )
                )
            ):
                deal.stage = "awaiting_payout"
                continue

            if (
                deal.firm
                and not deal.collapsed_sale
                and deal.deposits_received
                and not deal.missing_law_firm
                and deal.agent_confirmation
                and deal.our_trust_excess_held == 0
                and deal.required_documents_received
                and today_date >= deal.possession_date
                and deal.due_to_our_brokerage == 0
                and deal.commission_received == 0
                and not deal.lawyer_payout_letter
                and (
                    deal.conveyancing_done
                    or (
                        deal.end_id.type in ["seller", "landlord"]
                        and not any(
                            [
                                deal.seller_broker_conveys_to_seller_lawyer,
                                deal.seller_broker_conveys_to_buyer_lawyer,
                                deal.seller_broker_conveys_to_buyer_broker,
                            ]
                        )
                    )
                    or (
                        deal.end_id.type in ["buyer", "tenant"]
                        and not any(
                            [
                                deal.buyer_broker_conveys_to_seller_lawyer,
                                deal.buyer_broker_conveys_to_buyer_lawyer,
                                deal.buyer_broker_conveys_to_seller_broker,
                            ]
                        )
                    )
                )
            ):
                deal.stage = "awaiting_lawyer_letter"
                continue

            if (
                deal.firm
                and not deal.collapsed_sale
                and deal.deposits_received
                and not deal.missing_law_firm
                and deal.agent_confirmation
                and deal.our_trust_excess_held == 0
                and deal.required_documents_received
                and today_date >= deal.possession_date
                and deal.due_to_our_brokerage == 0
                and (deal.commission_received > 0 or deal.lawyer_payout_letter)
                and (
                    deal.conveyancing_done
                    or (
                        deal.end_id.type in ["seller", "landlord"]
                        and not any(
                            [
                                deal.seller_broker_conveys_to_seller_lawyer,
                                deal.seller_broker_conveys_to_buyer_lawyer,
                                deal.seller_broker_conveys_to_buyer_broker,
                            ]
                        )
                    )
                    or (
                        deal.end_id.type in ["buyer", "tenant"]
                        and not any(
                            [
                                deal.buyer_broker_conveys_to_seller_lawyer,
                                deal.buyer_broker_conveys_to_buyer_lawyer,
                                deal.buyer_broker_conveys_to_seller_broker,
                            ]
                        )
                    )
                )
            ):
                deal.stage = "payout_now"
                continue

            # Default stage
            deal.stage = "draft"

    # =====================
    # Status Computation Method
    # =====================
    @api.depends("stage")
    def _compute_status(self):
        """
        Compute the status based on the current stage of the deal.
        """
        for rec in self:
            if rec.stage == "collapsed":
                rec.status = "collapsed"
            elif rec.stage == "conditions_remaining":
                rec.status = "pending"
            elif rec.stage in [
                "agent_approval",
                "convey_now",
                "pay_trust_excess",
                "awaiting_possession",
                "awaiting_payout",
                "awaiting_lawyer_letter",
                "payout_now",
                "law_firm_required",
                "deposit_required",
                "documents_required",
                "deposit_and_law_firm_required",
            ]:
                rec.status = "firm"
            elif rec.stage == "close":
                rec.status = "close"
            else:
                rec.status = "firm"

    # =====================
    # Helper Compute Methods
    # =====================

    @api.depends(
        "condition_line_ids.condition_removed",
        "condition_line_ids.removal_date",
        "condition_line_ids",
    )
    def _compute_firm_and_firm_date(self):
        """
        Compute the 'firm' status and 'firm_date' based on conditions.
        """
        for deal in self:
            if not deal.condition_line_ids:
                # No conditions associated; set firm to True and firm_date to offer_date
                deal.firm = True
                deal.firm_date = deal.offer_date
            else:
                # All conditions removed; set firm to True and firm_date to latest removal_date
                all_removed = all(
                    line.condition_removed for line in deal.condition_line_ids
                )
                deal.firm = all_removed

                if all_removed:
                    removal_dates = [
                        line.removal_date
                        for line in deal.condition_line_ids
                        if line.removal_date
                    ]
                    if removal_dates:
                        latest_removal_date = max(removal_dates)
                        deal.firm_date = latest_removal_date
                    else:
                        deal.firm_date = fields.Date.today()
                else:
                    # If any condition is not removed, set firm to False and clear firm_date
                    deal.firm_date = False

    @api.depends(
        "transaction_line_ids.held_by",
        "transaction_line_ids.amount",
        "transaction_line_ids.deposited",
    )
    def _compute_deposits_received(self):
        """
        Compute whether all deposits have been received.
        """
        for deal in self:
            # Filter transaction lines held by 'our_office'
            our_office_deposits = deal.transaction_line_ids.filtered(
                lambda tl: tl.held_by == "our_office"
            )

            if not our_office_deposits:
                # No deposits held by 'our_office'; consider deposits received
                deal.deposits_received = True
            else:
                # Sum of amounts equals sum of deposited
                total_amount = sum(our_office_deposits.mapped("amount"))
                total_deposited = sum(our_office_deposits.mapped("deposited"))

                deal.deposits_received = total_amount == total_deposited

    @api.depends("law_firm_ids.end_id.type", "law_firm_ids.active_status")
    def _compute_missing_law_firm(self):
        """
        Compute whether a required law firm is missing based on the deal's end type.
        """
        for deal in self:
            seller_landlord_law_firm = False
            buyer_tenant_law_firm = False

            for lawyer in deal.law_firm_ids:
                if (
                    lawyer.end_id.type in ["seller", "landlord"]
                    and lawyer.active_status == "active"
                ):
                    seller_landlord_law_firm = True
                if (
                    lawyer.end_id.type in ["buyer", "tenant"]
                    and lawyer.active_status == "active"
                ):
                    buyer_tenant_law_firm = True

            # Determine if a required lawyer is missing based on the end type
            if (
                deal.end_id.type in ["seller", "landlord"]
                and not seller_landlord_law_firm
            ):
                deal.missing_law_firm = True
            elif deal.end_id.type in ["buyer", "tenant"] and not buyer_tenant_law_firm:
                deal.missing_law_firm = True
            else:
                deal.missing_law_firm = False

    @api.depends(
        "document_line_ids.document_required",
        "document_line_ids.is_uploaded",
        "document_line_ids.is_approved",
    )
    def _compute_required_documents_received(self):
        for deal in self:
            required_docs = deal.document_line_ids.filtered(
                lambda dl: dl.document_required
            )
            if not required_docs:
                deal.all_documents_received = True
            else:
                all_received = all(
                    dl.is_uploaded and dl.is_approved for dl in required_docs
                )
                deal.all_documents_received = all_received
