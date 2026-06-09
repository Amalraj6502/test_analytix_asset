from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AssetRegisterQtyWizard(models.TransientModel):
    _name = 'asset.register.qty.wizard'
    _description = 'Wizard to Register Quantity'

    order_line_id = fields.Many2one('purchase.order.line', string='Purchase Order Line')
    max_qty = fields.Float(string='Max to Register')
    quantity = fields.Float(string='Quantity to Register', required=True)
    location_id = fields.Many2one('asset.management.location', string='Location')
    asset_model = fields.Char(string='Asset Model')
    asset_admin_ids = fields.Many2many('res.users', string='Asset Admins')

    def action_confirm_registration(self):
        self.ensure_one()
        if self.quantity <= 0:
            raise UserError(_("Quantity must be positive."))
        if self.quantity > self.max_qty:
            raise UserError(_("You cannot register more than the pending quantity (%s).") % self.max_qty)

        # Find matching asset type for the product
        asset_type = self.env['asset.type'].search([('name', '=', self.order_line_id.product_id.name)], limit=1)
        if not asset_type:
            raise UserError(_("No matching Asset Type found for product '%s'. Please create an Asset Type with this name first.") % self.order_line_id.product_id.name)

        # Create asset records equal to quantity
        for i in range(int(self.quantity)):
            self.env['asset.management'].create({
                'asset_type_id': asset_type.id,
                'purchase_line_id': self.order_line_id.id,
                'asset_location': self.location_id.id,
                'asset_model': self.asset_model,
                'asset_admin_ids': [(4, uid) for uid in self.asset_admin_ids.ids] if self.asset_admin_ids else [],
                'vendor_new_id': self.order_line_id.order_id.partner_id.id,
                'amount': self.order_line_id.price_unit,
                'invoice_date': fields.Date.today(),
            })

        return {'type': 'ir.actions.act_window_close'}
