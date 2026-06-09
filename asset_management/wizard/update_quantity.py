from odoo import models, fields, api

class UpdateQuantityWizard(models.TransientModel):
    _name = 'update.quantity.wizard'
    _description = 'Update Asset Quantity'

    quantity = fields.Integer(string='Quantity', required=True)
    reference_number = fields.Char(string='Reference Number')
    reference_number_id = fields.Many2one('reference.number',
        string='Batch Number',
    )
    buy_date = fields.Date(string='Buy Date')
    end_date = fields.Date(string='End Date')

    vendor_new_id = fields.Many2one(
        'res.partner',
        string="Vendor",
        domain=[('supplier_rank', '>', 0)]
    )

    vendor_bill_id = fields.Many2one(
        'account.move',
        string="Vendor Bill No",
        domain="[('partner_id','=',vendor_new_id),('move_type','=','in_invoice')]"
    )

    invoice_date = fields.Date(string="Invoice Date", help="Date when the asset was purchased or acquired")

    purchase_price = fields.Float(string='Purchase Price')
    invoice_attachment_ids = fields.Many2many('ir.attachment', 'update_qty_wizard_attach_rel', 'wiz_id', 'att_id', string="Vendor Bill")



    def action_apply(self):
        self.ensure_one()
        asset_id = self.env.context.get('active_id')
        if not asset_id:
            return
        
        asset = self.env['asset.management'].browse(asset_id)
        
        current_count = self.env['asset.management.item'].search_count([('asset_id', '=', asset.id)])

        # 1. Update quantity_on_hand
        asset.quantity_on_hand += self.quantity
        
        # 2. Create sub-assets (asset.management.item)
        attachment_commands = [(6, 0, self.invoice_attachment_ids.ids)] if self.invoice_attachment_ids else []
        for i in range(1, self.quantity + 1):
            item_name = f"{asset.name} {current_count + i}"

            self.env['asset.management.item'].create({
                'name': item_name,
                'asset_id': asset.id,
                'reference_number_id': self.reference_number_id.id,
                'status': 'available',
                'buy_date': self.buy_date,
                'end_date': self.end_date,
                'vendor_new_id': self.vendor_new_id.id,
                'vendor_bill_id': self.vendor_bill_id.id,
                'invoice_date': self.invoice_date,
                'purchase_price': self.purchase_price,
                'invoice_attachment_ids': attachment_commands,
            })
        
        # Update Batch Number (Reference Number) details
        if self.reference_number_id:
            self.reference_number_id.write({
                'buy_date': self.buy_date,
                'end_date': self.end_date,
            })
        
        return {'type': 'ir.actions.act_window_close'}
