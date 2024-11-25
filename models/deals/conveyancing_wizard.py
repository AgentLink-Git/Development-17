# models/deals/conveyancing_wizard.py

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ConveyancingWizard(models.TransientModel):
    _name = "conveyancing.wizard"
    _description = "Conveyancing Wizard"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # Boolean fields for selecting individual law firms and brokers
    buyer_law_firm = fields.Boolean(
        string="Buyer's Law Firm",
        default=False,
        help="Select to include the buyer's Law Firm in the conveyancing email.",
    )
    seller_law_firm = fields.Boolean(
        string="Seller's Law Firm",
        default=False,
        help="Select to include the seller's Law Firm in the conveyancing email.",
    )
    other_broker = fields.Boolean(
        string="Other broker",
        default=False,
        help="Select to include other brokers in the conveyancing email.",
    )

    def send_conveyancing_email(self):
        """Send conveyancing email with necessary attachments to selected parties."""
        _logger.info("Initiating conveyancing email sending process.")
        try:
            # Retrieve the active deal record
            active_id = self.env.context.get("active_id")
            if not active_id:
                _logger.error("No active deal found in the context.")
                raise UserError(_("No active deal found in the context."))

            deal = self.env["deal.records"].browse(active_id)
            if not deal.exists():
                _logger.error(f"Deal with ID {active_id} does not exist.")
                raise UserError(_("The selected deal does not exist."))

            _logger.debug(f"Processing deal: {deal.name} (ID: {deal.id})")

            # Gather lawyers and brokers based on selections
            law_firm = self.env["deal.law_firm"].search([("deal_id", "=", deal.id)])
            brokers = self.env["deal.other.brokers"].search([("deal_id", "=", deal.id)])

            # Filter based on wizard selections
            if self.buyer_law_firm:
                law_firm = law_firm.filtered(lambda l: l.is_buyer_law_firm)
                _logger.debug(f"Filtered to buyer law_firm: {law_firm.ids}")
            if self.seller_law_firm:
                law_firm = law_firm.filtered(lambda l: l.is_seller_law_firm)
                _logger.debug(f"Filtered to seller law_firm: {law_firm.ids}")
            if self.other_broker:
                brokers = brokers.filtered(lambda b: b.is_other_broker)
                _logger.debug(f"Filtered to other brokers: {brokers.ids}")

            # Check for email addresses
            missing_emails = False
            missing_email_entities = []
            if (self.buyer_law_firm or self.seller_law_firm) and not law_firm.mapped(
                "agent_email"
            ):
                missing_emails = True
                missing_email_entities.append("law_firm")
                _logger.warning("Missing email addresses for selected law_firms.")
            if self.other_broker and not brokers.mapped("convey_email"):
                missing_emails = True
                missing_email_entities.append("Other brokers")
                _logger.warning("Missing email addresses for selected brokers.")

            if missing_emails:
                error_message = _(
                    "Email address missing for %s. Cannot send email."
                ) % ", ".join(missing_email_entities)
                _logger.error(error_message)
                raise UserError(error_message)

            # Retrieve the email template
            try:
                template = self.env.ref(
                    "agentlink_transaction_manager.conveyancing_email_template"
                )
                _logger.debug(f"Using email template ID: {template.id}")
            except ValueError:
                error_message = _(
                    "Email template 'agentlink_transaction_manager.conveyancing_email_template' not found."
                )
                _logger.error(error_message)
                raise UserError(error_message)

            # Prepare attachments
            attachments = self._prepare_attachments(deal)
            _logger.debug(f"Prepared {len(attachments)} attachments for the email.")

            # Update the email template with attachments
            template.attachment_ids = [(6, 0, attachments.ids)]
            _logger.debug("Attached documents to the email template.")

            # Mark lawyers and brokers as conveyed
            self._mark_conveyed(law_firm)
            self._mark_conveyed(brokers)
            _logger.info("Marked selected Law Firms and brokers as conveyed.")

            # Send the email
            template.send_mail(deal.id, force_send=True)
            _logger.info(f"Conveyancing email sent successfully for deal ID: {deal.id}")

            # Post a success message
            self.message_post(
                body=_("Conveyancing email sent successfully."),
                message_type="notification",
                subtype_xmlid="mail.mt_note",
            )

            # Create an audit log entry
            self._create_audit_log(deal, attachments)

        except UserError as ue:
            _logger.warning(f"UserError encountered: {ue.name}")
            raise
        except Exception as e:
            _logger.exception(
                "An unexpected error occurred while sending conveyancing email."
            )
            raise UserError(_("Error: Failed to send email. %s") % str(e))

    def _prepare_attachments(self, deal):
        """Prepare and retrieve attachments for the email."""
        _logger.debug(f"Preparing attachments for deal ID: {deal.id}")
        Attachment = self.env["ir.attachment"]
        attachments = self.env["ir.attachment"].browse()

        for document in deal.document_ids:
            # Ensure that 'deal.document_ids' has 'file_name' and 'document' fields
            attachment = Attachment.search(
                [
                    ("name", "=", document.file_name),
                    ("res_model", "=", deal._name),
                    ("res_id", "=", deal.id),
                ],
                limit=1,
            )
            if not attachment:
                _logger.debug(
                    f"Creating new attachment for document: {document.file_name}"
                )
                attachment = Attachment.create(
                    {
                        "name": document.file_name,
                        "type": "binary",
                        "datas": document.document,
                        "mimetype": "application/pdf",
                        "store_fname": document.file_name,
                        "res_model": deal._name,
                        "res_id": deal.id,
                    }
                )
            attachments |= attachment

        _logger.debug(f"Total attachments prepared: {len(attachments)}")
        return attachments

    def _mark_conveyed(self, entities):
        """Mark entities as conveyed and set re_conveyed flag."""
        _logger.debug(f"Marking {len(entities)} entities as conveyed.")
        for entity in entities:
            if not entity.conveyed:
                entity.conveyed = True
                entity.re_conveyed = True
                _logger.debug(
                    f"Entity ID {entity.id} marked as conveyed and re-conveyed."
                )

    def _create_audit_log(self, deal, attachments):
        """Create an audit log entry for the conveyancing email sent."""
        _logger.debug(f"Creating audit log for deal ID: {deal.id}")
        audit_log = self.env["convey.auditing"].create(
            {
                "deal_id": deal.id,
                "user_id": self.env.user.id,
                "email_sent": True,
                "attachment_ids": [(6, 0, attachments.ids)],
                "timestamp": fields.Datetime.now(),
                "notes": f"Conveyancing email sent with attachments: {', '.join(attachments.mapped('name'))}",
            }
        )
        _logger.info(
            f"Audit log created with ID: {audit_log.id} for deal ID: {deal.id}"
        )
