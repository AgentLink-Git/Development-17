# models/res_partner/res_partner_bank.py

from odoo import models, fields


class ResPartnerBankInherit(models.Model):
    _inherit = "res.partner.bank"
    _description = "Inherited Res Partner Bank for Trust Integration"

    is_trust = fields.Boolean(
        string="Is Trust Account",
        default=False,
        help="Indicates whether this bank account is a trust account.",
    )
