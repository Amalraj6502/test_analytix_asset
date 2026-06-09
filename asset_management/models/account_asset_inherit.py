from odoo import models, fields

class AccountAsset(models.Model):
    _inherit = 'account.asset.asset'

    asset_management_id = fields.Many2one(
        'asset.management',
        string='Asset Management',
        help='Link to Asset Management record'
    )