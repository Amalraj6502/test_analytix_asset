from odoo import fields, models

class AssetCode(models.Model):
    _name = 'asset.code'
    _description = 'Asset Code'

    name = fields.Char(string="Asset Code")
    model_name = fields.Char(string="Model Name")
    description = fields.Text(string="Description")
