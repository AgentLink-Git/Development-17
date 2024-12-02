# models/other_brokers/select_broker_wizard.py

"""
Module for handling the Select Broker Wizard, allowing users to select an existing broker
or create a new one and associate it with a deal and end.
"""

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class SelectBrokerWizard(models.TransientModel):
    """
    Wizard to select an existing broker or create a new one for a deal and end.
    """
    _name = 'select.broker.wizard'
    _description = 'Select or Add Broker Wizard'
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # =====================
    # Broker Selection Fields
    # =====================
    partner_id = fields.Many2one(
        'res.partner',
        string='Partner',
        required=True,
        ondelete='cascade',
        domain=[('is_other_broker', '=', True)],
        tracking=True
    )
    other_broker_id = fields.Many2one(
        'other.broker',
        string='Select Existing Brokerage',
        domain=[('is_company', '=', True), ('is_other_broker', '=', True)],
        tracking=True,
    )
    create_new = fields.Boolean(
        string='Create New Brokerage',
        default=False,
        tracking=True,
    )

    # =====================
    # New Brokerage Information
    # =====================
    new_broker_name = fields.Char(
        string='Brokerage Name',
        tracking=True,
    )
    country_id = fields.Many2one(
        'res.country',
        string='Country',
        default=lambda self: self.env['res.country'].search([('code', '=', 'CA')], limit=1),
        tracking=True,
    )
    street = fields.Char(
        string='Street',
        tracking=True,
    )
    street2 = fields.Char(
        string='Street2',
        tracking=True,
    )
    city = fields.Char(
        string='City',
        tracking=True,
    )
    state_id = fields.Many2one(
        'res.country.state',
        string='Province',
        domain=lambda self: [('country_id', '=', self.country_id.id)] if self.country_id else [],
        tracking=True,
    )
    zip = fields.Char(
        string='Postal Code',
        tracking=True,
    )
    phone = fields.Char(
        string='Phone',
        tracking=True,
    )
    email = fields.Char(
        string='Email',
        tracking=True,
    )
    payment_method = fields.Selection(
        [
            ('cheque', 'Cheque'),
            ('direct_deposit', 'Direct Deposit'),
        ],
        string='Payment Method',
        tracking=True,
    )
    note = fields.Text(
        string='Notes',
        tracking=True,
    )

    # =====================
    # Deal and End Associations
    # =====================
    deal_id = fields.Many2one(
        'deal.records',
        string='Deal',
        required=True,
        ondelete='cascade',
        tracking=True,
    )
    end_id = fields.Many2one(
        'deal.end',
        string='End',
        required=True,
        ondelete='cascade',
        tracking=True,
    )

    # =====================
    # Methods
    # =====================

    def action_select_broker(self):
        """
        Select or create a broker and associate it with the deal and end.
        """
        self.ensure_one()
        self._check_existing_broker()
        broker = self._get_or_create_broker()
        self._associate_broker_with_deal_end(broker)

        return {'type': 'ir.actions.act_window_close'}

    @api.onchange('country_id')
    def _onchange_country_id(self):
        """
        Dynamically update the domain for state_id based on country_id.
        """
        if self.country_id:
            return {'domain': {'state_id': [('country_id', '=', self.country_id.id)]}}
        else:
            return {'domain': {'state_id': []}}

    @api.onchange('new_broker_name')
    def _onchange_new_broker_name(self):
        """
        Warn the user if a similar brokerage already exists.
        """
        if self.new_broker_name:
            similar_brokers_count = self.env['res.partner'].search_count([
                ('name', 'ilike', self.new_broker_name),
                ('is_other_broker', '=', True),
                ('is_company', '=', True)
            ])
            if similar_brokers_count >= 1:
                warning = {
                    'title': _('Similar Brokerage Found'),
                    'message': _('A brokerage with a similar name already exists. Please consider selecting it from the list.')
                }
                return {'warning': warning}

    # =====================
    # Helper Methods
    # =====================
    def _check_existing_broker(self):
        """
        Ensure no broker is already associated with the given deal and end.
        """
        existing_broker_count = self.env['other.broker'].search_count([
            ('deal_id', '=', self.deal_id.id),
            ('end_id', '=', self.end_id.id),
        ])
        if existing_broker_count >= 1:
            raise ValidationError(_("A broker is already associated with this deal and end. Please edit the existing broker instead of creating a new one."))

    def _get_or_create_broker(self):
        """
        Return the selected existing broker or create a new one.
        """
        if self.create_new:
            self._validate_new_broker_creation()
            return self._create_new_broker()
        else:
            if not self.other_broker_id:
                raise ValidationError(_('Please select an existing brokerage or choose to create a new one.'))
            return self.other_broker_id

    def _associate_broker_with_deal_end(self, broker):
        """
        Associate the broker with the current deal and end.
        """
        other_broker_vals = {
            'deal_id': self.deal_id.id,
            'end_id': self.end_id.id,
            'partner_id': broker.id,
        }
        self.env['other.broker'].create(other_broker_vals)
        _logger.debug(
            "Associated Other Broker ID: %s with Deal ID: %s and End ID: %s",
            broker.id, self.deal_id.id, self.end_id.id
        )

    def _validate_new_broker_creation(self):
        """
        Validate the creation of a new brokerage.
        """
        if not self.new_broker_name:
            raise ValidationError(_('Please provide the name of the new brokerage.'))

    def _create_new_broker(self):
        """
        Create a new brokerage as a res.partner record.
        """
        similar_brokers_count = self.env['res.partner'].search_count([
            ('name', 'ilike', self.new_broker_name),
            ('is_other_broker', '=', True),
            ('is_company', '=', True)
        ])
        if similar_brokers_count >= 1:
            raise ValidationError(_(
                'A brokerage with a similar name already exists. '
                'Please check the existing brokerages before creating a new one.'
            ))

        broker_vals = {
            'name': self.new_broker_name,
            'is_company': True,
            'is_other_broker': True,
            'street': self.street,
            'street2': self.street2,
            'city': self.city,
            'state_id': self.state_id.id if self.state_id else False,
            'zip': self.zip,
            'country_id': self.country_id.id if self.country_id else False,
            'phone': self.phone,
            'email': self.email,
            'payment_method': self.payment_method,
            'comment': self.note,
        }
        broker = self.env['res.partner'].create(broker_vals)
        _logger.debug("Created new brokerage with Partner ID: %s", broker.id)
        return broker

    # =====================
    # SQL Constraints (Optional)
    # =====================
    _sql_constraints = [
        ('unique_broker_per_deal_end',
         'UNIQUE(deal_id, end_id)',
         'Each deal and end combination can only have one associated broker.')
    ]