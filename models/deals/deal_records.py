# models/deals/deal_records.py

"""
Module for managing Deal Records, including creation, updates, and associations with brokers,
agents, documents, and financial transactions.
"""

import uuid
import logging
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class DealRecords(models.Model):
    """
    Model representing Deal Records, handling all aspects of a real estate deal,
    including broker associations, financial transactions, and related documents.
    """
    _name = "deal.records"
    _description = "Deal Records"
    _order = "possession_date desc"
    _inherit = [
        "mail.thread",
        "mail.activity.mixin",
        "address.compute.mixin",
        "commission.favourite.mixin",
        "commission.setup.mixin",
        "notification.mixin",
    ]

    # =====================
    # Basic Information
    # =====================
    name = fields.Char(
        string="Name",
        compute="_compute_name",
        store=True,
    )
    deal_number = fields.Char(
        string="Deal #",
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _("New"),
        index=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
        required=True,
        tracking=True,
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Partner",
        required=True,
        ondelete="cascade",
        help="Partner associated with this deal.",
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        related="company_id.currency_id",
        string="Currency",
        readonly=True,
    )
    account_move_ids = fields.One2many(
        "account.move",
        "deal_id",
        string="Journal Entries",
        help="Journal entries related to this deal.",
    )
    account_move_line_ids = fields.One2many(
        'account.move.line',
        'deal_id',
        string='Journal Items',
        help='Journal items related to this deal.',
    )
    # =====================
    # Address & Legal Description
    # =====================
    suite_number = fields.Char(string="Suite Number", tracking=True)
    street_number = fields.Char(string="Street Number", tracking=True)
    street_direction_prefix = fields.Selection(
        selection=[
            ('east', 'East'),
            ('ne', 'NE'),
            ('nw', 'NW'),
            ('north', 'North'),
            ('se', 'SE'),
            ('sw', 'SW'),
            ('south', 'South'),
            ('west', 'West'),
        ],
        string="Street Direction Prefix",
        tracking=True,
    )
    street_name = fields.Char(string="Street Name", tracking=True)
    street_type_id = fields.Many2one(
        "street.type",
        string="Street Type",
        tracking=True,
    )
    street_direction_suffix = fields.Selection(
        selection=[
            ('east', 'East'),
            ('ne', 'NE'),
            ('nw', 'NW'),
            ('north', 'North'),
            ('se', 'SE'),
            ('sw', 'SW'),
            ('south', 'South'),
            ('west', 'West'),
        ],
        string="Street Direction Suffix",
        tracking=True,
    )
    city_id = fields.Many2one(
        "cities.and.towns",
        string="City",
        tracking=True,
    )
    state_id = fields.Many2one(
        "res.country.state",
        string="Province",
        tracking=True,
    )
    country_id = fields.Many2one(
        "res.country",
        string="Country",
        tracking=True,
    )
    postal_code = fields.Char(string="Postal Code", size=7, tracking=True)

    # Legal Description
    legal_plan = fields.Char(string="Plan/Condo Plan #", tracking=True)
    legal_block = fields.Char(string="Block/Unit #", tracking=True)
    legal_lot = fields.Char(string="Lot/Unit Factor #", tracking=True)
    legal_long = fields.Char(string="Long Legal (Rural)", tracking=True)

    # =====================
    # End - We Represent
    # =====================
    end_id = fields.Many2one(
        "deal.end",
        string="We Represent",
        tracking=True,
        index=True
    )

    # =====================
    # Price and Date Fields
    # =====================
    list_price = fields.Monetary(string="List Price", tracking=True)
    list_date = fields.Date(string="List Date", tracking=True)
    sell_price = fields.Monetary(string="Sell Price", tracking=True)
    offer_date = fields.Date(string="Offer Date", required=True, tracking=True)
    possession_date = fields.Date(string="Closing Date", tracking=True)
    collapsed_date = fields.Date(
        string="Collapsed Date",
        tracking=True,
        help="Date when the sale collapsed.",
    )

    # =====================
    # Property Details
    # =====================
    property_type_id = fields.Many2one(
        'property.type',
        string="Property Type",
        domain="[('is_active', '=', True)]",
        tracking=True,
    )
    size = fields.Char(string="Size (Sq Ft/Sq M)", tracking=True)
    ml_number = fields.Char(string="ML Number", tracking=True)
    title_requested = fields.Boolean(string="Office to Order Title", tracking=True)
    title_ordered = fields.Boolean(string="Title Ordered", tracking=True)
    business_source_id = fields.Many2one(
        'business.source',
        string="Business Source",
        domain="[('is_active', '=', True)]",
        tracking=True,
    )
    for_sale_or_lease = fields.Selection(
        [
            ("for_sale", "For Sale"),
            ("for_lease", "For Lease"),
        ],
        string="For Sale or Lease",
        required=True,
        default="for_sale",
        tracking=True,
        help="Indicates whether the deal is for sale or lease.",
    )
    notes = fields.Html(string="Notes", tracking=True)

    collapsed_sale = fields.Boolean(
        string="Collapsed Sale",
        tracking=True,
        help="Indicates if the sale has collapsed.",
    )

    created_by_listing = fields.Boolean(
        string="Sold Listing",
        help="Indicates if the deal was created from a listing.",
    )
    listing_number = fields.Char(
        string="Listing #",
        related="listing_id.listing_number",
        store=True,
        readonly=True,
        tracking=True,
        help="Listing number from the related listing record.",
    )
    listing_id = fields.Many2one(
        "listing.records",
        string="Listing Record",
        readonly=False,  # Allow setting via the wizard
        tracking=True,
        help="Related listing record.",
    )

    # =====================
    # Deal Class
    # =====================
    deal_class_id = fields.Many2one(
        "deal.class",
        string="Class",
        domain="[('is_active','=',True)]",
        tracking=True,
        index=True,
    )

    # =====================
    # Buyers/Sellers
    # =====================
    buyers_sellers_ids = fields.One2many(
        "buyers.sellers",
        "deal_id",
        string="Buyers/Sellers",
        tracking=True
    )
    buyers_sellers_wizard_ids = fields.One2many(
        "buyers.sellers.wizard",
        "deal_id",
        string="Buyers/Sellers",
        tracking=True
    )
    buyer_names = fields.Char(
        string="Buyer Names",
        compute="_compute_buyer_seller_names",
        store=True,
        readonly=True,
    )
    seller_names = fields.Char(
        string="Seller Names",
        compute="_compute_buyer_seller_names",
        store=True,
        readonly=True,
    )
    buyer_seller_label = fields.Char(
        string="Party Type",
        compute="_compute_buyer_seller_label",
        store=True,
        help="Label indicating the type of party based on deal type.",
    )

    @api.depends("buyers_sellers_ids.end_id.type", "buyers_sellers_ids.partner_id.name")
    def _compute_buyer_seller_names(self):
        """
        Compute buyer and seller names based on related buyers_sellers_ids.
        """
        for record in self:
            buyers = record.buyers_sellers_ids.filtered(
                lambda bs: bs.end_id.type in ["buyer", "tenant"]
            )
            sellers = record.buyers_sellers_ids.filtered(
                lambda bs: bs.end_id.type in ["seller", "landlord"]
            )
            record.buyer_names = ", ".join(buyers.mapped("partner_id.name"))
            record.seller_names = ", ".join(sellers.mapped("partner_id.name"))

    @api.depends("for_sale_or_lease")
    def _compute_buyer_seller_label(self):
        """
        Compute the label for Buyers/Sellers based on sale or lease.
        """
        for rec in self:
            if rec.for_sale_or_lease == "for_sale":
                rec.buyer_seller_label = "Buyer/Seller"
            else:
                rec.buyer_seller_label = "Tenant/Landlord"

    # =====================
    # Sales Agents & Referrals
    # =====================
    sales_agents_and_referrals_ids = fields.One2many(
        "sales.agents.and.referrals",
        "deal_id",
        string="Sales Agents & Referrals",
        tracking=True,
    )
    sales_agents_count = fields.Integer(
        string="Sales Agents Count",
        compute="_compute_sales_agents_count",
        store=True,
        help="Number of sales agents associated with the deal.",
    )
    sales_agent_mentorship_line_ids = fields.One2many(
        'sales.agent.mentorship.line',
        'deal_id',
        string="Sales Agent Mentorship Line",
        help="Mentorship records for sales agents.",
    )
    sales_agent_mentorship_wizard_ids = fields.One2many(
        'sales.agent.mentorship.wizard',
        'deal_id',
        string="Sales Agent Mentorship Wizard",
        help="Mentorship records for sales agents.",
    )
    commission_advance_ids = fields.One2many(
        'commission.advance',
        'deal_id',
        string="Commission Advances",
        help="Advance commission records.",
    )

    @api.depends("sales_agents_and_referrals_ids")
    def _compute_sales_agents_count(self):
        """
        Compute the number of sales agents associated with the deal.
        """
        for rec in self:
            rec.sales_agents_count = len(rec.sales_agents_and_referrals_ids)

    # =====================
    # Other Brokers and their Agents
    # =====================
    other_broker_ids = fields.One2many(
        "other.broker",
        "deal_id",
        string="Other Brokers",
        tracking=True,
        help="Other brokerage associated with the deal.",
    )
    other_broker_agent_ids = fields.One2many(
        "other.broker.agent",
        "deal_id",
        string="Other Broker Agents",
        tracking=True,
        help="Other brokerage agents associated with the deal.",
    )
    select_broker_wizard_ids = fields.One2many(
        "select.broker.wizard",
        "deal_id",
        string="Other Brokers",
        tracking=True,
        help="Other brokerage associated with the deal.",
    )

    # =====================
    # Law Firms and Lawyers
    # =====================
    law_firm_ids = fields.One2many(
        "law.firm",
        "deal_id",
        string="Law Firms",
        tracking=True,
        help="Law firms associated with the deal.",
    )
    lawyer_ids = fields.One2many(
        "lawyer",
        "deal_id",
        string="Lawyers",
        tracking=True,
        help="Lawyers associated with the deal.",
    )
    law_firm_wizard_ids = fields.One2many(
        "law.firm.wizard",
        "deal_id",
        string="Law Firm Wizard",
        tracking=True,
        help="Law firms associated with the deal.",
    )
    # =====================
    # Conditions
    # =====================
    condition_line_ids = fields.One2many(
        "condition.line",
        "deal_id",
        string="Conditions",
        tracking=True,
        help="Conditions associated with the deal.",
    )

    # =====================
    # Trust Deposits
    # =====================
    trust_receipt_ids = fields.One2many(
        "trust.receipt",
        "deal_id",
        string="Trust Receipts",
        tracking=True,
        help="Trust receipts related to the deal.",
    )
    trust_refund_ids = fields.One2many(
        "trust.refund",
        "deal_id",
        string="Trust Refunds",
        tracking=True,
        help="Trust refunds related to the deal.",
    )
    trust_excess_funds_ids = fields.One2many(
        "trust.excess.funds",
        "deal_id",
        string="Trust Excess Funds",
        tracking=True,
        help="Trust excess funds related to the deal.",
    )

    # =====================
    # Documents
    # =====================
    document_line_ids = fields.One2many(
        "document.line",
        "deal_id",
        string="Documents",
        tracking=True,
        help="Documents related to the deal.",
    )
    required_document_count = fields.Integer(
        string="# Required Documents",
        compute="_compute_required_document_count",
        store=True,
    )

    @api.depends("document_line_ids.document_required", "document_line_ids.manually_removed")
    def _compute_required_document_count(self):
        """
        Count the number of required documents.
        """
        for rec in self:
            rec.required_document_count = len(
                rec.document_line_ids.filtered(
                    lambda d: d.document_required and not d.manually_removed
                )
            )

    # =====================
    # Commission Fields
    # =====================
    total_commission_line_ids = fields.One2many(
        "commission.line",
        "deal_id",
        string="Total Commission Lines",
        domain=[('commission_type', '=', 'total')],
        tracking=True,
    )
    buyer_side_commission_line_ids = fields.One2many(
        "commission.line",
        "deal_id",
        string="Buyer Side Commission Lines",
        domain=[('commission_type', '=', 'buyer_side')],
        tracking=True,
    )

    # =====================
    # Commission Setup Fields
    # =====================
    # Inherited from CommissionSetupMixin

    # =====================
    # Commission Favourites Fields
    # =====================
    # Inherited from CommissionFavouriteMixin

    # =====================
    # Commission Fields for Total Commission
    # =====================
    total_commission_type = fields.Selection(
        [
            ("tiered", "Tiered Percentage"),
            ("fixed", "Fixed Percentage"),
            ("flat_fee", "Flat Fee"),
        ],
        string="Total Commission Type",
        tracking=True,
    )
    total_commission_percentage = fields.Float(
        string="Total Commission Percentage (%)",
        tracking=True,
    )
    aggregate_flat_fee_plus = fields.Monetary(
        string="+ Flat Fee",
        currency_field="currency_id",
        help="Additional flat fee to add for total commission.",
        tracking=True,
        default=0.0,
    )
    aggregate_flat_fee_less = fields.Monetary(
        string="- Flat Fee",
        currency_field="currency_id",
        help="Flat fee to subtract for total commission.",
        tracking=True,
        default=0.0,
    )

    # =====================
    # Commission Fields for Buyer Side Commission
    # =====================
    buyer_side_commission_type = fields.Selection(
        [
            ("tiered", "Tiered Percentage"),
            ("fixed", "Fixed Percentage"),
            ("flat_fee", "Flat Fee"),
        ],
        string="Buyer Side Commission Type",
        tracking=True,
    )
    buyer_side_commission_percentage = fields.Float(
        string="Buyer Side Commission Percentage (%)",
        tracking=True,
    )
    buyer_side_plus_flat_fee = fields.Monetary(
        string="+ Flat Fee",
        currency_field="currency_id",
        help="Additional flat fee to add for buyer side commission.",
        tracking=True,
        default=0.0,
    )
    buyer_side_less_flat_fee = fields.Monetary(
        string="- Flat Fee",
        currency_field="currency_id",
        help="Flat fee to subtract for buyer side commission.",
        tracking=True,
        default=0.0,
    )

    # =====================
    # Deal Preferences
    # =====================
    deal_preferences_id = fields.Many2one(
        "deal.preferences",
        string="Deal Preferences",
        tracking=True,
        domain="[('deal_id', '=', id)]",
        help="Preference related to the deal.",
    )

    # =====================
    # Transaction Lines
    # =====================
    transaction_line_ids = fields.One2many(
        'transaction.line',
        'deal_id',
        string='Transaction Lines',
        help="Transaction lines associated with the deal.",
    )

    # =====================
    # Deal Payments
    # =====================
    account_payment_ids = fields.One2many(
        "account.payment",
        "deal_id",
        string="Account Payments",
        tracking=True,
        help="Payment entries related to the deal.",
    )

    # =====================
    # Commission Receipt
    # =====================
    commission_receipt_ids = fields.One2many(
        "commission.receipt",
        "deal_id",
        string="Commission Receipts",
        tracking=True,
        help="Commission receipts related to the deal.",
    )

    # =====================
    # Deal Confirmation
    # =====================
    agent_confirmation = fields.Boolean(
        string="All Info Correct",
        tracking=True
    )
    agent_signature = fields.Char(
        string="Enter Full Name",
        tracking=True
    )
    brokerage_confirmation = fields.Boolean(
        string="Office Approval"
    )
    agent_confirmation_datetime = fields.Datetime(
        string="Date/Time",
        tracking=True
    )

    @api.onchange("agent_confirmation")
    def _onchange_agent_confirmation_datetime(self):
        """
        Automatically set or unset the agent confirmation datetime based on agent confirmation.
        """
        for rec in self:
            if rec.agent_confirmation:
                rec.agent_confirmation_datetime = fields.Datetime.now()
            else:
                rec.agent_confirmation_datetime = False

    # =====================
    # Override Create and Write Methods
    # =====================
    @api.model_create_multi
    def create(self, vals_list):
        """
        Override the create method to handle sequence generation based on 'offer_date'
        and populate commission lines.
        """
        for vals in vals_list:
            # Handle Sequence Generation based on 'offer_date'
            offer_date = fields.Date.from_string(
                vals.get("offer_date", fields.Date.context_today(self))
            )
            seq_date = offer_date.strftime("%Y-%m-%d")
            vals["deal_number"] = (
                self.env["ir.sequence"]
                .with_context(force_company=self.env.user.company_id.id)
                .next_by_code("deal.records", sequence_date=seq_date)
                or _("New")
            )
        # Create the Deal Records with commission line population enabled
        deals = super(DealRecords, self.with_context(populate_commission_lines=True)).create(vals_list)
        # Update Required Documents
        deals._update_required_documents()
        return deals

    def write(self, vals):
        """
        Override the write method to enable commission line population and update required documents.
        """
        res = super(DealRecords, self.with_context(populate_commission_lines=True)).write(vals)
        self._update_required_documents()
        return res

    @api.depends('deal_number')
    def _compute_name(self):
        """
        Compute the name of the deal based on the deal number.
        """
        for rec in self:
            rec.name = rec.deal_number or _("Deal")

    # =====================
    # Update Required Documents Method
    # =====================
    def _update_required_documents(self):
        """
        Update required documents based on the deal's class and other criteria.
        """
        for rec in self:
            # Fetch required DocumentTypes based on the deal's deal class and other criteria
            required_docs = self.env["document.type"].search(
                [
                    ("is_active", "=", True),
                    ("document_category", "=", "deal_document"),
                    ("class_ids", "in", rec.deal_class_id.id),
                    "|",
                    ("buyer_end", "=", True),
                    ("seller_end", "=", True),
                ]
            )
            required_doc_ids = required_docs.ids

            # Fetch existing DocumentLines linked to this deal and required DocumentTypes
            existing_doc_ids = rec.document_line_ids.filtered(
                lambda d: d.document_type_id.id in required_doc_ids and not d.manually_removed
            ).mapped("document_type_id.id")

            # Determine missing DocumentTypes
            missing_doc_ids = set(required_doc_ids) - set(existing_doc_ids)

            # Create DocumentLines for missing DocumentTypes
            for doc_id in missing_doc_ids:
                self.env["document.line"].create(
                    {
                        "document_type_id": doc_id,
                        "deal_id": rec.id,
                        "end_id": rec.end_id.id,
                    }
                )

    # =====================
    # Action Methods
    # =====================
    def action_view_buyers_sellers(self):
        """
        Action to view Buyers/Sellers associated with the deal.
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Buyers/Sellers"),
            "res_model": "buyers.sellers",
            "view_mode": "tree,form",
            "domain": [("deal_id", "=", self.id)],
            "context": {"default_deal_id": self.id},
            "target": "current",
        }

    def action_view_sales_agents_and_referrals(self):
        """
        Action to view Sales Agents & Referrals associated with the deal.
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Sales Agents & Referrals"),
            "res_model": "sales.agents.and.referrals",
            "view_mode": "tree,form",
            "domain": [("deal_id", "=", self.id)],
            "context": {"default_deal_id": self.id},
            "target": "current",
        }

    def action_view_law_firms(self):
        """
        Action to view Law Firms associated with the deal.
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Law Firms"),
            "res_model": "law.firm",
            "view_mode": "tree,form",
            "domain": [("deal_id", "=", self.id)],
            "context": {"default_deal_id": self.id},
            "target": "current",
        }

    def action_view_other_brokers(self):
        """
        Action to view Other Brokers associated with the deal.
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Other Brokers"),
            "res_model": "other.broker",
            "view_mode": "tree,form",
            "domain": [("deal_id", "=", self.id)],
            "context": {"default_deal_id": self.id},
            "target": "current",
        }

    def action_view_documents(self):
        """
        Action to view Documents related to the deal.
        """
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Documents"),
            "res_model": "document.line",
            "view_mode": "tree,form",
            "domain": [("deal_id", "=", self.id)],
            "context": {"default_deal_id": self.id},
            "target": "current",
        }

    # =====================
    # Additional Fields for Invoices and Bills
    # =====================
    invoice_ids = fields.One2many(
        "account.move",
        "deal_id",
        string="Invoices",
        domain=[("move_type", "in", ["out_invoice", "out_refund"])],
        help="Invoices related to the deal.",
    )
    bill_ids = fields.One2many(
        "account.move",
        "deal_id",
        string="Bills",
        domain=[("move_type", "=", "in_invoice")],
        help="Bills related to the deal.",
    )

    def link_invoices_bills(self):
        """
        Link all invoices and bills related to this deal.
        """
        for deal in self:
            invoices = self.env["account.move"].search(
                [("deal_id", "=", deal.id), ("move_type", "in", ["out_invoice", "out_refund"])]
            )
            bills = self.env["account.move"].search(
                [("deal_id", "=", deal.id), ("move_type", "=", "in_invoice")]
            )
            deal.invoice_ids = [(6, 0, invoices.ids)]
            deal.bill_ids = [(6, 0, bills.ids)]

    # =====================
    # Constraints
    # =====================
    @api.constrains("possession_date", "offer_date")
    def _check_offer_date_possession_date(self):
        """
        Ensure that the Closing Date is after the Offer Date.
        """
        for rec in self:
            if rec.possession_date and rec.offer_date:
                if rec.possession_date <= rec.offer_date:
                    raise ValidationError(
                        _("The Closing Date must be after the Offer Date.")
                    )

    @api.constrains("sell_price")
    def _check_sell_price(self):
        """
        Ensure that the Sell Price is not negative.
        """
        for rec in self:
            if rec.sell_price < 0:
                raise ValidationError(_("Sell Price cannot be negative."))

    @api.constrains("sales_agents_and_referrals_ids")
    def _check_sales_agents_percentage(self):
        """
        Ensure that the total Percentage of End does not exceed 100%.
        """
        for rec in self:
            total_percentage = sum(
                rec.sales_agents_and_referrals_ids.mapped("percentage_of_end")
            )
            if total_percentage > 100:
                raise ValidationError(_("The total Percentage of End should not exceed 100%."))

    # =====================
    # Override Unlink Method to Handle Related Records
    # =====================
    def unlink(self):
        """
        Override the unlink method to prevent deletion of deals with linked invoices or bills
        and to delete related document lines.
        """
        for rec in self:
            # Perform necessary checks before deletion
            if rec.invoice_ids or rec.bill_ids:
                raise UserError(
                    _("Cannot delete a deal with linked invoices or bills.")
                )
            # Delete related document lines
            rec.document_line_ids.unlink()
        return super(DealRecords, self).unlink()

    # =====================
    # Default Get Method
    # =====================
    @api.model
    def default_get(self, fields_list):
        """
        Override the default_get method to set default values for company_id and country_id.
        """
        res = super(DealRecords, self).default_get(fields_list)
        res["company_id"] = self.env.company.id
        res["country_id"] = (
            self.env["res.country"].search([("code", "=", "CA")], limit=1).id
        )
        return res

    # =====================
    # Name Get Method
    # =====================
    def name_get(self):
        """
        Override the name_get method to display the deal's name or a default label.
        """
        result = []
        for rec in self:
            name = rec.name or _("Deal")
            result.append((rec.id, name))
        return result

    # =====================
    # SQL Constraints
    # =====================
    _sql_constraints = [
        ('deal_listing_unique', 'unique(listing_id)', 'A listing can be linked to only one deal.'),
        ('deal_number_unique', 'unique(deal_number)', 'The Deal Number must be unique.'),
    ]