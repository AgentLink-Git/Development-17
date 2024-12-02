# models/documents/documents.py

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class DocumentDealStatus(models.Model):
    _name = 'document.deal.status'
    _description = 'Document Deal Status'

    code = fields.Char(string='Code', required=True)
    name = fields.Char(string='Name', required=True)


class DocumentType(models.Model):
    _name = "document.type"
    _description = "Document Type"

    # =====================
    # Fields
    # =====================
    name = fields.Char(string="Name", required=True)
    is_active = fields.Boolean(string="Active", default=True)
    document_required = fields.Boolean(string="Required Document", default=False)
    deal_class_ids = fields.Many2many(
        "deal.class",
        string="Deal Classes",
        help="Link document types to specific deal classes."
    )
    document_category = fields.Selection(
        selection=[
            ("contract", "Contract"),
            ("misc_document", "Miscellaneous"),
            ("admin_document", "Admin Document"),
        ],
        string="Document Category",
        required=True,
    )

    convey_ids = fields.Many2many(
        "deal.convey",
        string="Conveyances",
        help="Link document types to specific conveyancing details."
    )

    # Reintroduced Boolean Fields
    is_listing_document = fields.Boolean(string="Is Listing Document", default=False)
    is_deal_document = fields.Boolean(string="Is Deal Document", default=False)
    is_conveyancing_document = fields.Boolean(string="Is Conveyancing Document", default=False)

    convey_to_seller_law_firm = fields.Boolean(string="Convey to Seller Law Firm", default=False)
    convey_to_buyer_law_firm = fields.Boolean(string="Convey to Buyer Law Firm", default=False)
    convey_to_other_broker = fields.Boolean(string="Convey to Other Broker", default=False)

    # Fields indicating requirement per Deal status
    required_for_deal_status_ids = fields.Many2many(
        'document.deal.status',
        string="Required for Deal Status",
        help="Indicates at which deal statuses this document becomes required.",
    )

    # Fields indicating requirement per Listing status
    required_for_listing_status_ids = fields.Many2many(
        'document.listing.status',
        string="Required for Listing Status",
        help="Indicates at which listing statuses this document becomes required.",
    )

    # =====================
    # Constraints
    # =====================

    @api.constrains("is_listing_document", "is_deal_document")
    def _check_document_association(self):
        for rec in self:
            if not rec.is_listing_document and not rec.is_deal_document:
                raise ValidationError(_("A Document Type must be associated with at least a Listing or a Deal."))


class DocumentLine(models.Model):
    _name = "document.line"
    _description = "Document Line"
    _rec_name = "document_type_id"

    # =====================
    # Fields
    # =====================
    document_type_id = fields.Many2one(
        "document.type",
        string="Document Type",
        domain="[('is_active', '=', True)]",
        required=True,
    )
    document_required = fields.Boolean(
        string="Document Required",
        compute="_compute_document_required",
        store=True,
    )
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "document_line_attachment_rel",
        "document_line_id",
        "attachment_id",
        string="Attachments",
        help="You can attach the document files here.",
    )
    document_review = fields.Selection(
        [
            ("awaiting", "Awaiting Approval"),
            ("approved", "Approved by Office"),
            ("rejected", "Rejected by Office"),
            ("re_submitted", "Re-submitted by Agent"),
        ],
        string="Document Review",
        default="awaiting",
    )
    is_uploaded = fields.Boolean(
        string="Uploaded",
        compute="_compute_is_uploaded",
        store=True,
    )
    is_approved = fields.Boolean(
        string="Is Approved",
        compute="_compute_is_approved",
        store=True,
    )
    manually_removed = fields.Boolean(string="Manually Removed")

    # Relational Fields
    deal_id = fields.Many2one(
        "deal.records",
        string="Deal",
        ondelete="cascade",
    )
    listing_id = fields.Many2one(
        "listing.records",
        string="Listing",
        ondelete="cascade",
    )
    end_id = fields.Many2one(
        "deal.end",
        string="End",
        ondelete="set null",
    )

    # =====================
    # Compute Methods
    # =====================
    @api.depends("attachment_ids")
    def _compute_is_uploaded(self):
        for rec in self:
            rec.is_uploaded = bool(rec.attachment_ids)

    @api.depends("document_review")
    def _compute_is_approved(self):
        for rec in self:
            rec.is_approved = rec.document_review == "approved"

    @api.depends(
        "document_type_id",
        "deal_id.status",
        "listing_id.status",
        "document_type_id.required_for_deal_status_ids",
        "document_type_id.required_for_listing_status_ids",
        "deal_id.condition_line_ids.condition_removed",
    )
    def _compute_document_required(self):
        for rec in self:
            rec.document_required = False  # Default to False
            document_type = rec.document_type_id

            if rec.deal_id:
                deal_status = rec.deal_id.status  # Assuming status is a string code
                required_status_codes = document_type.required_for_deal_status_ids.mapped('code')

                if deal_status == 'pending' and 'pending' in required_status_codes:
                    rec.document_required = True
                elif deal_status == 'collapsed' and 'collapsed' in required_status_codes:
                    rec.document_required = True
                elif deal_status == 'closed' and 'close' in required_status_codes:
                    rec.document_required = True
                elif deal_status == 'firm':
                    if 'unconditional_sale' in required_status_codes:
                        # Check if there are no condition.line records for the deal
                        if not rec.deal_id.condition_line_ids:
                            rec.document_required = True
                    if 'removal_of_conditions' in required_status_codes:
                        # Check if all conditions are removed
                        if rec.deal_id.condition_line_ids and all(rec.deal_id.condition_line_ids.mapped('condition_removed')):
                            rec.document_required = True
            elif rec.listing_id:
                listing_status = rec.listing_id.status
                required_status_codes = document_type.required_for_listing_status_ids.mapped('code')
                if listing_status in required_status_codes:
                    rec.document_required = True

    # =====================
    # Constraints
    # =====================
    @api.constrains("deal_id", "listing_id")
    def _check_at_least_one_link(self):
        for rec in self:
            if not rec.deal_id and not rec.listing_id:
                raise ValidationError(
                    _("A Document Line must be linked to at least a Deal or a Listing.")
                )

    # =====================
    # Overridden Methods
    # =====================
    @api.model
    def create(self, vals):
        res = super(DocumentLine, self).create(vals)
        if res.attachment_ids:
            res.attachment_ids.write({
                "res_model": "document.line",
                "res_id": res.id,
            })
        return res

    def write(self, vals):
        res = super(DocumentLine, self).write(vals)
        if "attachment_ids" in vals:
            for rec in self:
                rec.attachment_ids.write({
                    "res_model": "document.line",
                    "res_id": rec.id,
                })
        return res