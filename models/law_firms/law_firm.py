# models/law_firms/law_firm.py

import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

class LawFirm(models.Model):
    _name = "law.firm"
    _description = "Law Firm"
    _inherits = {'res.partner': 'partner_id'}
    _inherit = ["mail.thread", "mail.activity.mixin", "notification.mixin", "shared.fields.mixin"]
    _rec_name = "id"

    # Inherited Partner
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        ondelete='cascade',
        domain=[('is_law_firm', '=', True)],
        tracking=True
    )

    # Status for this deal
    active_status = fields.Selection(
        [("active", "Active"), ("archived", "Archived")],
        default="active",
        string="Active Law Firm",
        tracking=True,
    )

    # Relationships
    deal_id = fields.Many2one(
        'deal.records',
        string='Deal',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    lawyer_ids = fields.One2many(
        "lawyer",
        "lawyer_id",
        string="Lawyers",
        ondelete='cascade',
        domain=[("is_lawyer", "=", True)],
        tracking=True,
    )
    transaction_line_ids = fields.One2many(
        "transaction.line",
        compute="_compute_transaction_line_ids",
        string="Transaction Lines",
        store=False,
    )
    account_move_id = fields.Many2one(
        "account.move",
        string="Account Move",
        ondelete="cascade",
        required=True,
        help="Related Account Move.",
    )

    # Basic Fields
    end_id = fields.Many2one(
        "deal.end",
        string="End",
        required=True,
        tracking=True,
    )
    active_status = fields.Selection(
        [("active", "Active"), ("archived", "Archived")],
        default="active",
        string="Status",
        tracking=True,
    )

    # Financial Fields
    due_from_law_firm = fields.Monetary(
        string="Due from Law Firm",
        currency_field="currency_id",
        tracking=True,
        compute="_compute_financials",
        store=True,
    )
    due_to_law_firm = fields.Monetary(
        string="Due to Law Firm",
        currency_field="currency_id",
        tracking=True,
        compute="_compute_financials",
        store=True,
    )
    payment_method = fields.Selection(
        selection=[("cheque", "Cheque"), ("direct_deposit", "Direct Deposit")],
        string="Payment Method",
        help="Select the preferred payment method for this law firm.",
        tracking=True,
    )
    deposit_instructions_received = fields.Boolean(
        string="Deposit Instructions Received",
        default=False,
        help="Indicates if the law firm has provided banking information for Direct Deposits.",
        tracking=True,
    )

    # Conveyancing Fields
    conveyed = fields.Boolean(string="Conveyed", tracking=True)
    convey_datetime = fields.Datetime(
        string="Conveyed Date/Time", tracking=True, readonly=True
    )
    re_conveyed = fields.Boolean(string="Re-Conveyed", tracking=True)
    re_conveyed_datetime = fields.Datetime(
        string="Re-Conveyed Date/Time", tracking=True, readonly=True
    )
    convey_reason = fields.Selection(
        [
            ("additional_info", "Additional Info Provided"),
            ("did_not_receive", "Did Not Receive/Misplaced"),
            ("possession_date", "Possession Date Change"),
            ("price", "Price Change"),
            ("updated_commission", "Updated Commission"),
            ("updated_law_firm", "Updated Law Firm"),
        ],
        string="Convey Reason",
        tracking=True,
    )
    note = fields.Html(string="Notes", tracking=True)

    # Compute Fields
    payment_type = fields.Selection(
        [
            ("ar", "A/R - Receivable from this Firm"),
            ("ap", "A/P - Payable to this Firm"),
            ("no", "No Payable or Receivable"),
        ],
        string="Type",
        compute="_compute_payment_type",
        store=True,
    )

    # Constraints
    @api.constrains("end_id", "active_status")
    def _check_single_active_and_archived_law_firm_per_end(self):
        """Ensure only one active and one archived law firm per end."""
        for record in self:
            if record.active_status == "active":
                if self._active_firm_exists(record):
                    raise ValidationError(
                        _("Only one active law firm is allowed per end (Buyer or Seller).")
                    )
            elif record.active_status == "archived":
                self._delete_existing_archived_firm(record)

    def _active_firm_exists(self, record):
        """Check if another active firm exists for the same end."""
        active_firms = self.search([
            ("deal_id", "=", record.deal_id.id),
            ("end_id", "=", record.end_id.id),
            ("active_status", "=", "active"),
            ("id", "!=", record.id),
        ])
        return bool(active_firms)

    def _delete_existing_archived_firm(self, record):
        """Delete any existing archived law firm for the same end."""
        archived_firms = self.search([
            ("deal_id", "=", record.deal_id.id),
            ("end_id", "=", record.end_id.id),
            ("active_status", "=", "archived"),
            ("id", "!=", record.id),
        ])
        if archived_firms:
            _logger.info("Deleting existing archived law firm for Deal ID: %s, End ID: %s", record.deal_id.id, record.end_id.id)
            archived_firms.unlink()

    # Override Create Method
    @api.model
    def create(self, vals):
        """Create a new law firm and mark as company law firm."""
        res = super(LawFirm, self).create(vals)
        res.partner_id.write({
            "is_company": True,
            "is_law_firm": True,
            "company_id": res.company_id.id,
        })
        return res

    # Override Write Method to Handle Archiving Logic
    def write(self, vals):
        """Update the law firm record and apply archiving rules."""
        if 'active_status' in vals and vals['active_status'] == 'archived':
            for record in self:
                self._delete_existing_archived_firm(record)
        res = super(LawFirm, self).write(vals)
        self.partner_id.write({
            "is_company": True,
            "is_law_firm": True,
            "company_id": self.company_id.id,
        })
        return res

    # Onchange Methods
    @api.onchange("conveyed")
    def _onchange_conveyed(self):
        """Set convey date/time when conveyed is toggled."""
        self.convey_datetime = fields.Datetime.now() if self.conveyed else False

    @api.onchange("re_conveyed")
    def _onchange_re_conveyed(self):
        """Set re-convey date/time when re_conveyed is toggled."""
        self.re_conveyed_datetime = fields.Datetime.now() if self.re_conveyed else False

    # Compute Methods
    @api.depends("due_from_law_firm", "due_to_law_firm", "active_status")
    def _compute_payment_type(self):
        """Determine the type of financial relationship with the law firm."""
        for rec in self:
            if rec.active_status == "active":
                rec.payment_type = "ar" if rec.due_from_law_firm > 0 else "ap" if rec.due_to_law_firm > 0 else "no"
            else:
                rec.payment_type = "no"

    @api.depends(
        'deal_id.due_from_buyer_law_firm', 'deal_id.due_to_buyer_law_firm', 
        'deal_id.due_from_seller_law_firm', 'deal_id.due_to_seller_law_firm', 
        'end_id.type'
    )
    def _compute_financials(self):
        """Aggregate amounts due from and due to the law firm based on their end."""
        for rec in self:
            if rec.end_id.type in ['buyer', 'tenant']:
                rec.due_from_law_firm = rec.deal_id.due_from_buyer_law_firm or 0.0
                rec.due_to_law_firm = rec.deal_id.due_to_buyer_law_firm or 0.0
            elif rec.end_id.type in ['seller', 'landlord']:
                rec.due_from_law_firm = rec.deal_id.due_from_seller_law_firm or 0.0
                rec.due_to_law_firm = rec.deal_id.due_to_seller_law_firm or 0.0
            else:
                rec.due_from_law_firm = 0.0
                rec.due_to_law_firm = 0.0

    @api.depends("deal_id", "partner_id")
    def _compute_transaction_line_ids(self):
        """Link related transaction lines for the law firm."""
        for record in self:
            if record.deal_id and record.partner_id:
                record.transaction_line_ids = self.env["transaction.line"].search([
                    ("deal_id", "=", record.deal_id.id),
                    ("partner_id", "=", record.partner_id.id)
                ])
            else:
                record.transaction_line_ids = False

    # Helper Methods
    def get_payment_details(self):
        """
        Retrieve the partner's bank account and corresponding journal based on payment method.
        Returns:
            tuple: (partner_bank_id, bank_journal_id)
        """
        self.ensure_one()
        if not self.payment_method:
            raise UserError(_("Payment method is not set for this Law Firm."))

        journal = self.env["account.journal"].search(
            [("name", "=", self.payment_method), ("type", "=", "bank")], limit=1
        )
        if not journal:
            _logger.warning("No bank journal found for payment method '%s'.", self.payment_method)
            raise UserError(_("No bank journal found for payment method '%s'.") % self.payment_method)

        partner_bank = self.partner_id.bank_ids.filtered(
            lambda b: b.company_id == self.company_id
        )
        if not partner_bank:
            _logger.warning("No bank account found for Law Firm partner in company '%s'.", self.company_id.name)
            raise UserError(_("No bank account found for the Law Firm partner in company '%s'.") % self.company_id.name)

        return partner_bank[0].id, journal.id

    # Action Methods
    def action_update_law_firm(self):
        """Open a wizard to update law firm details."""
        self.ensure_one()
        return {
            "name": _("Update Law Firm"),
            "type": "ir.actions.act_window",
            "res_model": "law.firm.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_deal_id": self.deal_id.id,
                "default_end_id": self.end_id.id,
            },
        }

    # Name Get and Name Search Methods
    def name_get(self):
        """Customize displayed name to show partner name."""
        return [(rec.id, rec.partner_id.name or "Law Firm") for rec in self]

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        """Enable searching by partner name for easier navigation."""
        args = args or []
        if name:
            partner_ids = (
                self.env["res.partner"]
                .search(
                    ["|", ("name", operator, name), ("parent_id.name", operator, name)]
                )
                .ids
            )
            args += [("partner_id", "in", partner_ids)]
        records = self.search(args, limit=limit)
        return records.name_get()

    display_name = fields.Char(
        string="Display Name",
        compute="_compute_display_name",
        store=True,
    )