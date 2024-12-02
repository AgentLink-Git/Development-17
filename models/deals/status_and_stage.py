# models/deals/status_and_stage.py

"""
Module for managing Deal Status and Stage, including the computation of deal stages based on various
criteria such as firm status, deposit receipt, conveyancing completion, and other deal-specific
conditions. This module extends the 'deal.records' model to incorporate status and stage tracking,
facilitating better deal lifecycle management and reporting.
"""

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

# Configure the logger for this module
_logger = logging.getLogger(__name__)


class StatusAndStage(models.Model):
    """
    Inherited model from 'deal.records' to add status and stage tracking functionality.
    This includes computed fields for stage, status, firm status, deposit receipt, missing law firms,
    and required documents. The model facilitates the automated progression of deal stages based on
    predefined business logic and conditions.
    """
    _inherit = 'deal.records'
    _description = 'Deal Records Extension for Status and Stage'

    # =====================
    # Stage and Status Fields
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
        help="Indicates whether the deal is firm."
    )
    firm_date = fields.Date(
        string="Firm Date",
        compute="_compute_firm_and_firm_date",
        store=True,
        readonly=True,
        tracking=True,
        help="Date when the deal became firm."
    )
    deposits_received = fields.Boolean(
        string="All Deposits Received",
        compute="_compute_deposits_received",
        store=True,
        readonly=True,
        tracking=True,
        help="Indicates whether all required deposits have been received."
    )
    missing_law_firm = fields.Boolean(
        string="Missing Law Firm",
        compute="_compute_missing_law_firm",
        store=True,
        readonly=True,
        tracking=True,
        help="Indicates whether a required law firm is missing."
    )
    required_documents_received = fields.Boolean(
        string="Required Documents Received",
        compute="_compute_required_documents_received",
        store=True,
        readonly=True,
        tracking=True,
        help="Indicates whether all required documents have been received."
    )
    is_closed = fields.Boolean(
        string="Is Closed",
        default=False,
        tracking=True,
        help="Indicates whether the deal is closed."
    )

    # =====================
    # Computation Methods
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
        """
        Compute the current stage of the deal based on various conditions and business logic.
        """
        today_date = fields.Date.today()
        for deal in self:
            _logger.debug("Computing stage for Deal ID: %s", deal.id)
            if deal.is_closed:
                deal.stage = "close"
                _logger.debug("Deal ID %s: Set stage to 'close'.", deal.id)
                continue
            if deal.collapsed_sale:
                deal.stage = "collapsed"
                _logger.debug("Deal ID %s: Set stage to 'collapsed'.", deal.id)
                continue

            if not deal.firm and not deal.collapsed_sale:
                deal.stage = "conditions_remaining"
                _logger.debug("Deal ID %s: Set stage to 'conditions_remaining'.", deal.id)
                continue

            if (
                deal.firm
                and not deal.collapsed_sale
                and not deal.deposits_received
                and not deal.missing_law_firm
            ):
                deal.stage = "deposit_required"
                _logger.debug("Deal ID %s: Set stage to 'deposit_required'.", deal.id)
                continue

            if (
                deal.firm
                and not deal.collapsed_sale
                and deal.deposits_received
                and deal.missing_law_firm
                and not deal.conveyancing_done
            ):
                deal.stage = "law_firm_required"
                _logger.debug("Deal ID %s: Set stage to 'law_firm_required'.", deal.id)
                continue

            if (
                deal.firm
                and not deal.collapsed_sale
                and not deal.deposits_received
                and deal.missing_law_firm
                and not deal.conveyancing_done
            ):
                deal.stage = "deposit_and_law_firm_required"
                _logger.debug("Deal ID %s: Set stage to 'deposit_and_law_firm_required'.", deal.id)
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
                _logger.debug("Deal ID %s: Set stage to 'agent_approval'.", deal.id)
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
                _logger.debug("Deal ID %s: Set stage to 'pay_trust_excess'.", deal.id)
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
                _logger.debug("Deal ID %s: Set stage to 'documents_required'.", deal.id)
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
                        and any([
                            deal.seller_broker_conveys_to_seller_lawyer,
                            deal.seller_broker_conveys_to_buyer_lawyer,
                            deal.seller_broker_conveys_to_buyer_broker,
                        ])
                    )
                    or (
                        deal.end_id.type in ["buyer", "tenant"]
                        and any([
                            deal.buyer_broker_conveys_to_seller_lawyer,
                            deal.buyer_broker_conveys_to_buyer_lawyer,
                            deal.buyer_broker_conveys_to_seller_broker,
                        ])
                    )
                )
            ):
                deal.stage = "convey_now"
                _logger.debug("Deal ID %s: Set stage to 'convey_now'.", deal.id)
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
                        and not any([
                            deal.seller_broker_conveys_to_seller_lawyer,
                            deal.seller_broker_conveys_to_buyer_lawyer,
                            deal.seller_broker_conveys_to_buyer_broker,
                        ])
                    )
                    or (
                        deal.end_id.type in ["buyer", "tenant"]
                        and not any([
                            deal.buyer_broker_conveys_to_seller_lawyer,
                            deal.buyer_broker_conveys_to_buyer_lawyer,
                            deal.buyer_broker_conveys_to_seller_broker,
                        ])
                    )
                )
            ):
                deal.stage = "awaiting_possession"
                _logger.debug("Deal ID %s: Set stage to 'awaiting_possession'.", deal.id)
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
                        and not any([
                            deal.seller_broker_conveys_to_seller_lawyer,
                            deal.seller_broker_conveys_to_buyer_lawyer,
                            deal.seller_broker_conveys_to_buyer_broker,
                        ])
                    )
                    or (
                        deal.end_id.type in ["buyer", "tenant"]
                        and not any([
                            deal.buyer_broker_conveys_to_seller_lawyer,
                            deal.buyer_broker_conveys_to_buyer_lawyer,
                            deal.buyer_broker_conveys_to_seller_broker,
                        ])
                    )
                )
            ):
                deal.stage = "awaiting_payout"
                _logger.debug("Deal ID %s: Set stage to 'awaiting_payout'.", deal.id)
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
                        and not any([
                            deal.seller_broker_conveys_to_seller_lawyer,
                            deal.seller_broker_conveys_to_buyer_lawyer,
                            deal.seller_broker_conveys_to_buyer_broker,
                        ])
                    )
                    or (
                        deal.end_id.type in ["buyer", "tenant"]
                        and not any([
                            deal.buyer_broker_conveys_to_seller_lawyer,
                            deal.buyer_broker_conveys_to_buyer_lawyer,
                            deal.buyer_broker_conveys_to_seller_broker,
                        ])
                    )
                )
            ):
                deal.stage = "awaiting_lawyer_letter"
                _logger.debug("Deal ID %s: Set stage to 'awaiting_lawyer_letter'.", deal.id)
                continue

            # Default stage
            deal.stage = "draft"
            _logger.debug("Deal ID %s: Set stage to 'draft'.", deal.id)

    @api.depends("stage")
    def _compute_status(self):
        """
        Compute the status of the deal based on its current stage.
        """
        for rec in self:
            _logger.debug("Computing status for Deal ID: %s based on stage: %s", rec.id, rec.stage)
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
                rec.status = "firm"  # Default to 'firm' if stage doesn't match any condition
            _logger.debug("Deal ID %s: Computed status as '%s'.", rec.id, rec.status)

    @api.depends('condition_line_ids.condition_removed', 'condition_line_ids.removal_date', 'condition_line_ids')
    def _compute_firm_and_firm_date(self):
        """
        Compute the 'firm' status and 'firm_date' based on conditions.
        """
        for deal in self:
            _logger.debug("Computing firm status and firm_date for Deal ID: %s", deal.id)
            if not deal.condition_line_ids:
                # No conditions associated; set firm to True and firm_date to offer_date
                deal.firm = True
                deal.firm_date = deal.offer_date
                _logger.debug(
                    "Deal ID %s: No conditions. Set firm=True and firm_date=%s.",
                    deal.id, deal.firm_date
                )
            else:
                # All conditions removed; set firm to True and firm_date to latest removal_date
                all_removed = all(line.condition_removed for line in deal.condition_line_ids)
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
                        _logger.debug(
                            "Deal ID %s: All conditions removed. Set firm_date to latest removal date %s.",
                            deal.id, deal.firm_date
                        )
                    else:
                        deal.firm_date = fields.Date.today()
                        _logger.debug(
                            "Deal ID %s: All conditions removed but no removal dates found. Set firm_date to today.",
                            deal.id
                        )
                else:
                    # If any condition is not removed, set firm to False and clear firm_date
                    deal.firm_date = False
                    _logger.debug(
                        "Deal ID %s: Not all conditions removed. Set firm=False and firm_date=False.",
                        deal.id
                    )

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
            _logger.debug("Computing deposits_received for Deal ID: %s", deal.id)
            # Filter transaction lines held by 'our_office'
            our_office_deposits = deal.transaction_line_ids.filtered(
                lambda tl: tl.held_by == "our_office"
            )

            if not our_office_deposits:
                # No deposits held by 'our_office'; consider deposits received
                deal.deposits_received = True
                _logger.debug(
                    "Deal ID %s: No deposits held by our_office. Set deposits_received=True.",
                    deal.id
                )
            else:
                # Sum of amounts equals sum of deposited
                total_amount = sum(our_office_deposits.mapped("amount"))
                total_deposited = sum(our_office_deposits.mapped("deposited"))

                deal.deposits_received = total_amount == total_deposited
                _logger.debug(
                    "Deal ID %s: Total Amount=%s, Total Deposited=%s. Set deposits_received=%s.",
                    deal.id, total_amount, total_deposited, deal.deposits_received
                )

    @api.depends('law_firm_ids.end_id.type', 'law_firm_ids.active_status')
    def _compute_missing_law_firm(self):
        """
        Compute whether a required law firm is missing based on the deal's end type.
        """
        for deal in self:
            _logger.debug("Computing missing_law_firm for Deal ID: %s", deal.id)
            seller_landlord_law_firm = False
            buyer_tenant_law_firm = False

            for lawyer in deal.law_firm_ids:
                if lawyer.end_id.type in ["seller", "landlord"] and lawyer.active_status == "active":
                    seller_landlord_law_firm = True
                if lawyer.end_id.type in ["buyer", "tenant"] and lawyer.active_status == "active":
                    buyer_tenant_law_firm = True

            # Determine if a required lawyer is missing based on the end type
            if deal.end_id.type in ['seller', 'landlord'] and not seller_landlord_law_firm:
                deal.missing_law_firm = True
                _logger.debug(
                    "Deal ID %s: Missing law firm for end type '%s'.",
                    deal.id, deal.end_id.type
                )
            elif deal.end_id.type in ['buyer', 'tenant'] and not buyer_tenant_law_firm:
                deal.missing_law_firm = True
                _logger.debug(
                    "Deal ID %s: Missing law firm for end type '%s'.",
                    deal.id, deal.end_id.type
                )
            else:
                deal.missing_law_firm = False
                _logger.debug(
                    "Deal ID %s: No missing law firm detected.",
                    deal.id
                )

    @api.depends('document_line_ids.document_required', 'document_line_ids.is_uploaded', 'document_line_ids.is_approved')
    def _compute_required_documents_received(self):
        """
        Compute whether all required documents have been received.
        """
        for deal in self:
            _logger.debug("Computing required_documents_received for Deal ID: %s", deal.id)
            required_docs = deal.document_line_ids.filtered(lambda dl: dl.document_required)
            if not required_docs:
                # No required documents; consider documents received
                deal.required_documents_received = True
                _logger.debug(
                    "Deal ID %s: No required documents. Set required_documents_received=True.",
                    deal.id
                )
            else:
                # Check if all required documents are uploaded and approved
                all_received = all(dl.is_uploaded and dl.is_approved for dl in required_docs)
                deal.required_documents_received = all_received
                _logger.debug(
                    "Deal ID %s: All required documents received=%s.",
                    deal.id, deal.required_documents_received
                )

    # =====================
    # Constraints
    # =====================

    @api.constrains('stage', 'status')
    def _check_stage_status_consistency(self):
        """
        Ensure that the stage and status fields are consistent with each other.
        """
        for deal in self:
            _logger.debug("Checking stage and status consistency for Deal ID: %s", deal.id)
            # Example Constraint: If stage is 'close', status must be 'close'
            if deal.stage == "close" and deal.status != "close":
                _logger.error(
                    "Stage is 'close' but status is '%s' for Deal ID: %s.",
                    deal.status, deal.id
                )
                raise ValidationError(
                    _("If the stage is 'Closed', the status must also be set to 'Closed'.")
                )
            # Additional constraints can be added here as per business logic
            _logger.debug(
                "Deal ID %s: Stage and status are consistent.",
                deal.id
            )

    # =====================
    # Override Unlink Method
    # =====================

    def unlink(self):
        """
        Override the unlink method to prevent deletion of deals that are in certain stages.
        """
        for record in self:
            if record.stage in ["close", "awaiting_payout", "awaiting_lawyer_letter"]:
                _logger.warning(
                    "Attempt to delete Deal ID: %s which is in stage '%s'.",
                    record.id, record.stage
                )
                raise UserError(
                    _("Cannot delete deals that are closed or awaiting payout/lawyer letter.")
                )
            _logger.debug(
                "Deal ID: %s is safe to delete.",
                record.id
            )
        return super(StatusAndStage, self).unlink()