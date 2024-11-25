# models/deals/reopen_deal.py

import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class DealRecords(models.Model):
    _inherit = "deal.records"

    # =====================
    # Methods for Reopening Deals
    # =====================

    def action_reopen_deal(self):
        """
        Reopen the deal by reversing allocations, invoices, bills, internal transfers,
        offset journal entries, pre-payments, reconciliations, transaction lines,
        and resetting commission calculations.
        Updates the deal's stage to 'Reopened', sends notifications, and creates audit logs.
        """
        self.ensure_one()
        _logger.info("Initiating reopening process for Deal ID: %s", self.id)

        # Revert Allocations and Financial Entries
        self._revert_financial_entries()

        # Reset Commission Calculations
        self._reset_commission_calculations()
        _logger.info("Commission calculations reset for Deal ID: %s", self.id)

        # Update Deal Stage to 'Reopened'
        reopened_stage = self.env.ref(
            "your_module.deal_stage_reopened", raise_if_not_found=False
        )
        if not reopened_stage:
            _logger.error("Reopened stage not found in module 'your_module'.")
            raise UserError(
                _(
                    "Reopened stage not found. Please ensure it is defined in your module."
                )
            )
        self.stage_id = reopened_stage.id
        _logger.info("Deal '%s' moved to stage '%s'.", self.name, reopened_stage.name)

        # Post Notification
        message = _("Deal has been reopened successfully.")
        self.message_post(
            body=message, message_type="notification", subtype_xmlid="mail.mt_note"
        )
        _logger.info("Notification sent for Deal ID: %s: %s", self.id, message)

        # Create Audit Log
        self._create_audit_log()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "message": message,
                "type": "success",
                "sticky": False,
            },
        }

    def _revert_financial_entries(self):
        """
        Revert all financial entries related to the deal closure.
        """
        self._revert_allocations()
        self._revert_invoices()
        self._revert_bills()
        self._revert_internal_transfers()
        self._revert_offset_journal_entries()
        self._revert_pre_payments()
        self._undo_reconciliations()
        self._cancel_transaction_lines()

    def _revert_allocations(self):
        """
        Revert allocation entries related to transferring funds from Trust Account to Operating Account.
        """
        allocations = self.env["account.move"].search(
            [
                ("deal_id", "=", self.id),
                ("move_type", "=", "entry"),
                (
                    "ref",
                    "ilike",
                    f"{self.deal_number} Transfer money from Trust Account to Operating Account",
                ),
                ("state", "=", "posted"),
            ]
        )
        for allocation in allocations:
            _logger.info(
                "Reverting allocation entry ID: %s for Deal ID: %s",
                allocation.id,
                self.id,
            )
            allocation.button_draft()
            allocation.unlink()
            _logger.info("Allocation entry ID: %s reverted and deleted.", allocation.id)

    def _revert_invoices(self):
        """
        Reverse invoices related to the deal's receipt commission partner.
        """
        invoices = self.env["account.move"].search(
            [
                ("deal_id", "=", self.id),
                ("move_type", "in", ["out_invoice", "out_refund"]),
                ("state", "=", "posted"),
            ]
        )
        for invoice in invoices:
            _logger.info(
                "Reverting Invoice ID: %s for Deal ID: %s", invoice.id, self.id
            )
            reversal_move = invoice._reverse_moves(
                default_values_list=[
                    {
                        "journal_id": invoice.journal_id.id,
                        "date": fields.Date.context_today(self),
                        "ref": _("Reversal of: %s") % invoice.name,
                    }
                ]
            )
            reversal_move.action_post()
            _logger.info("Invoice ID: %s reversed successfully.", invoice.id)

    def _revert_bills(self):
        """
        Reverse bills associated with sales agents and brokers linked to the deal.
        """
        bills = self.env["account.move"].search(
            [
                ("deal_id", "=", self.id),
                ("move_type", "in", ["in_invoice", "in_refund"]),
                ("state", "=", "posted"),
            ]
        )
        for bill in bills:
            _logger.info("Reverting Bill ID: %s for Deal ID: %s", bill.id, self.id)
            reversal_move = bill._reverse_moves(
                default_values_list=[
                    {
                        "journal_id": bill.journal_id.id,
                        "date": fields.Date.context_today(self),
                        "ref": _("Reversal of: %s") % bill.name,
                    }
                ]
            )
            reversal_move.action_post()
            _logger.info("Bill ID: %s reversed successfully.", bill.id)

    def _revert_internal_transfers(self):
        """
        Revert internal fund transfers between Operating and Trust Accounts.
        """
        payments = self.env["account.payment"].search(
            [
                ("deal_id", "=", self.id),
                ("is_internal_transfer", "=", True),
                ("state", "=", "posted"),
            ]
        )
        for payment in payments:
            _logger.info(
                "Reverting Internal Transfer Payment ID: %s for Deal ID: %s",
                payment.id,
                self.id,
            )
            payment.action_draft()
            payment.unlink()
            _logger.info(
                "Internal Transfer Payment ID: %s reverted and deleted.", payment.id
            )

    def _revert_offset_journal_entries(self):
        """
        Revert offset journal entries related to the deal's trust liabilities.
        """
        offset_entries = self.env["account.move"].search(
            [
                ("deal_id", "=", self.id),
                ("ref", "ilike", "Offset Trust Liability"),
                ("state", "=", "posted"),
            ]
        )
        for entry in offset_entries:
            _logger.info(
                "Reverting Offset Journal Entry ID: %s for Deal ID: %s",
                entry.id,
                self.id,
            )
            entry.button_draft()
            entry.unlink()
            _logger.info("Offset Journal Entry ID: %s reverted and deleted.", entry.id)

    def _revert_pre_payments(self):
        """
        Revert pre-payments associated with the deal.
        """
        payments = self.env["account.payment"].search(
            [
                ("deal_id", "=", self.id),
                ("is_commission_payment", "=", True),
                ("state", "=", "posted"),
            ]
        )
        for payment in payments:
            _logger.info(
                "Reverting Pre-Payment ID: %s for Deal ID: %s", payment.id, self.id
            )
            payment.action_draft()
            payment.unlink()
            _logger.info("Pre-Payment ID: %s reverted and deleted.", payment.id)

    def _undo_reconciliations(self):
        """
        Undo reconciliations related to the deal.
        """
        move_lines = self.env["account.move.line"].search(
            [
                ("move_id.deal_id", "=", self.id),
                ("reconciled", "=", True),
            ]
        )
        if move_lines:
            move_lines.remove_move_reconcile()
            _logger.info("Reconciliations undone for Deal ID: %s", self.id)

    def _cancel_transaction_lines(self):
        """
        Cancel transaction lines associated with the deal.
        """
        transaction_lines = self.env["transaction.line"].search(
            [
                ("deal_id", "=", self.id),
                ("state", "!=", "cancelled"),
            ]
        )
        for line in transaction_lines:
            _logger.info(
                "Cancelling Transaction Line ID: %s for Deal ID: %s", line.id, self.id
            )
            line.state = "cancelled"
            _logger.info("Transaction Line ID: %s cancelled.", line.id)

    def _reset_commission_calculations(self):
        """
        Reset commission calculations for the sales agents associated with the deal.
        """
        for agent_line in self.sales_agents_and_referrals_ids.filtered(
            lambda a: a.payment_type == "sales_agent"
        ):
            _logger.info(
                "Resetting commission calculations for Agent Line ID: %s", agent_line.id
            )
            agent_line.gross_amount = 0.0
            agent_line.commission_amount = 0.0
            agent_line.split_fees = 0.0
            agent_line.net_amount = 0.0

            # Adjust cumulative gross commissions for the partner
            partner = agent_line.partner_id
            if partner:
                # Recompute cumulative gross commissions excluding this deal
                cumulative_gross = partner.get_cumulative_gross_commissions(
                    exclude_deal_id=self.id
                )
                partner.cumulative_gross_commissions = cumulative_gross
                _logger.info(
                    "Cumulative gross commissions updated for Partner ID: %s",
                    partner.id,
                )

    def _create_audit_log(self):
        """
        Create an audit log entry for the deal reopening.
        """
        _logger.debug("Creating audit log for reopening Deal ID: %s", self.id)
        audit_log = self.env["deal.auditing"].create(
            {
                "deal_id": self.id,
                "user_id": self.env.user.id,
                "action": "reopened",
                "timestamp": fields.Datetime.now(),
                "notes": _(
                    "Deal has been reopened and related financial entries have been reversed."
                ),
            }
        )
        _logger.info(
            "Audit log created with ID: %s for Deal ID: %s", audit_log.id, self.id
        )
