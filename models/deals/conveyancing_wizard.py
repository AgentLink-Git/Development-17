# models/deals/conveyancing_wizard.py

"""
Module for managing Conveyancing Wizard operations, including sending conveyancing emails
with necessary attachments to selected parties such as law firms and brokers. This wizard
facilitates the selection of recipients and ensures that all required information is
included before dispatching the email. Additionally, it logs the process and creates
audit entries for tracking purposes.
"""

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

# Configure the logger for this module
_logger = logging.getLogger(__name__)


class ConveyancingWizard(models.TransientModel):
    """
    Transient model for the Conveyancing Wizard. This wizard allows users to select
    specific law firms and brokers to include in conveyancing emails. It handles the
    preparation of email attachments, sending of emails, marking entities as conveyed,
    and creating audit logs for tracking purposes.
    """
    _name = "conveyancing.wizard"
    _description = "Conveyancing Wizard"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # =====================
    # Field Definitions
    # =====================

    deal_id = fields.Many2one(
        'deal.records',
        string="Deal",
        required=True,
        default=lambda self: self._default_deal_id(),
        help="The deal record associated with this conveyancing process.",
    )
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
        string="Other Broker",
        default=False,
        help="Select to include other brokers in the conveyancing email.",
    )

    # =====================
    # Default Methods
    # =====================

    def _default_deal_id(self):
        """
        Set the default deal_id based on the active_id from the context.
        """
        active_id = self.env.context.get("active_id")
        if active_id:
            return self.env['deal.records'].browse(active_id)
        return None

    # =====================
    # Action Methods
    # =====================

    def send_conveyancing_email(self):
        """
        Send a conveyancing email with necessary attachments to selected parties based on
        the user's selections in the wizard. This method performs the following steps:
            1. Retrieves the active deal record from the context.
            2. Gathers selected law firms and brokers based on the wizard's boolean fields.
            3. Checks for the presence of required email addresses.
            4. Retrieves the appropriate email template.
            5. Prepares and attaches necessary documents.
            6. Marks the selected law firms and brokers as conveyed.
            7. Sends the email and logs the action.
            8. Creates an audit log entry for tracking purposes.
        """
        _logger.info("Initiating conveyancing email sending process.")
        try:
            deal = self.deal_id
            if not deal:
                _logger.error("No deal is associated with this wizard.")
                raise UserError(_("No deal is associated with this wizard."))

            _logger.debug(f"Processing deal: {deal.name} (ID: {deal.id})")

            # Gather law firms and brokers based on selections
            law_firms = deal.law_firm_ids
            brokers = deal.other_broker_ids

            # Filter based on wizard selections
            selected_law_firms = self._filter_law_firms(law_firms)
            selected_brokers = self._filter_brokers(brokers)

            # Check for email addresses
            self._validate_email_addresses(selected_law_firms, selected_brokers)

            # Retrieve the email template
            template = self._get_email_template()

            # Prepare attachments
            attachments = self._prepare_attachments(deal)
            _logger.debug(f"Prepared {len(attachments)} attachments for the email.")

            # Attach documents to the email template
            template.attachment_ids = [(6, 0, attachments.ids)]
            _logger.debug("Attached documents to the email template.")

            # Mark law firms and brokers as conveyed
            self._mark_conveyed(selected_law_firms)
            self._mark_conveyed(selected_brokers)
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

    # =====================
    # Helper Methods
    # =====================

    def _filter_law_firms(self, law_firms):
        """
        Filter law firms based on the wizard's selections.

        Args:
            law_firms (recordset): Recordset of law firms associated with the deal.

        Returns:
            recordset: Filtered recordset of law firms.
        """
        _logger.debug("Filtering law firms based on selections.")
        if self.buyer_law_firm:
            law_firms = law_firms.filtered(lambda l: l.end_id.type == 'buyer')
            _logger.debug(f"Filtered to buyer law firms: {law_firms.ids}")
        if self.seller_law_firm:
            law_firms = law_firms.filtered(lambda l: l.end_id.type == 'seller')
            _logger.debug(f"Filtered to seller law firms: {law_firms.ids}")
        return law_firms

    def _filter_brokers(self, brokers):
        """
        Filter brokers based on the wizard's selections.

        Args:
            brokers (recordset): Recordset of brokers associated with the deal.

        Returns:
            recordset: Filtered recordset of brokers.
        """
        _logger.debug("Filtering brokers based on selections.")
        if self.other_broker:
            brokers = brokers.filtered(lambda b: b.is_active)
            _logger.debug(f"Filtered to active other brokers: {brokers.ids}")
        return brokers

    def _validate_email_addresses(self, law_firms, brokers):
        """
        Validate that selected law firms and brokers have the necessary email addresses.

        Args:
            law_firms (recordset): Selected law firms.
            brokers (recordset): Selected brokers.

        Raises:
            UserError: If any selected entity is missing an email address.
        """
        _logger.debug("Validating email addresses for selected law firms and brokers.")
        missing_emails = []
        
        for law_firm in law_firms:
            if not law_firm.partner_id.email:
                missing_emails.append(f"Law Firm: {law_firm.partner_id.name}")

        for broker in brokers:
            if not broker.partner_id.email:
                missing_emails.append(f"Broker: {broker.partner_id.name}")

        if missing_emails:
            error_message = _(
                "Email address missing for the following entities:\n%s"
            ) % "\n".join(missing_emails)
            _logger.error(error_message)
            raise UserError(error_message)

    def _get_email_template(self):
        """
        Retrieve the conveyancing email template.

        Returns:
            record: The email template record.

        Raises:
            UserError: If the email template is not found.
        """
        try:
            template = self.env.ref(
                "your_module_name.conveyancing_email_template"
            )
            _logger.debug(f"Using email template ID: {template.id}")
            return template
        except ValueError:
            error_message = _(
                "Email template 'conveyancing_email_template' not found in 'your_module_name'."
            )
            _logger.error(error_message)
            raise UserError(error_message)

    def _prepare_attachments(self, deal):
        """
        Prepare and retrieve attachments for the email based on the deal's documents.

        Args:
            deal (record): The deal record.

        Returns:
            recordset: Recordset of attachments to be included in the email.
        """
        _logger.debug(f"Preparing attachments for deal ID: {deal.id}")
        Attachment = self.env["ir.attachment"]
        attachments = self.env["ir.attachment"]

        for document in deal.document_line_ids:
            if not document.document:
                _logger.warning(
                    f"Document '{document.name}' is missing file data."
                )
                continue

            attachment = Attachment.create(
                {
                    "name": document.name,
                    "type": "binary",
                    "datas": document.document,
                    "mimetype": "application/pdf",
                    "res_model": 'deal.records',
                    "res_id": deal.id,
                }
            )
            attachments |= attachment

        _logger.debug(f"Total attachments prepared: {len(attachments)}")
        return attachments

    def _mark_conveyed(self, entities):
        """
        Mark selected entities (law firms or brokers) as conveyed and set the re_conveyed flag.

        Args:
            entities (recordset): Recordset of entities to be marked as conveyed.
        """
        _logger.debug(f"Marking {len(entities)} entities as conveyed.")
        entities.write({'conveyed': True, 're_conveyed': True})

    def _create_audit_log(self, deal, attachments):
        """
        Create an audit log entry for the conveyancing email sent.

        Args:
            deal (record): The deal record.
            attachments (recordset): Recordset of attachments included in the email.
        """
        _logger.debug(f"Creating audit log for deal ID: {deal.id}")
        audit_log = self.env["convey.auditing"].create(
            {
                "deal_id": deal.id,
                "user_id": self.env.user.id,
                "email_sent": True,
                "attachment_ids": [(6, 0, attachments.ids)],
                "timestamp": fields.Datetime.now(),
                "notes": _("Conveyancing email sent with attachments: %s") % ", ".join(attachments.mapped('name')),
            }
        )
        _logger.info(
            f"Audit log created with ID: {audit_log.id} for deal ID: {deal.id}"
        )