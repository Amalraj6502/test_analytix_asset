from odoo import models, fields, api

class RenewServiceWizard(models.TransientModel):
    _name = 'renew.service.wizard'
    _description = 'Renew Service Asset'

    asset_id = fields.Many2one('asset.management', string="Asset", default=lambda self: self.env.context.get('active_id'))
    buy_date = fields.Date(string='New Purchase Date')
    end_date = fields.Date(string='New End Date', required=True)
    reference_number_id = fields.Many2one('reference.number', string='Batch Number', required=True)

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

    purchase_price = fields.Float(string='Purchase Price')
    invoice_attachment_ids = fields.Many2many('ir.attachment', 'renew_wizard_attach_rel', 'wiz_id', 'att_id', string="Vendor Bill")

    def action_apply(self):
        self.ensure_one()
        if self.reference_number_id:
            # Find all items with the same reference number under the same parent asset
            related_items = self.env['asset.management.item'].search([
                ('asset_id', '=', self.asset_id.id),
                ('reference_number_id', '=', self.reference_number_id.id)
            ])
            attachment_commands = [(6, 0, self.invoice_attachment_ids.ids)] if self.invoice_attachment_ids else []
            related_items.write({
                'buy_date': self.buy_date,
                'end_date': self.end_date,
                'vendor_new_id': self.vendor_new_id.id,
                'vendor_bill_id': self.vendor_bill_id.id,
                'purchase_price': self.purchase_price,
                'invoice_attachment_ids': attachment_commands,
            })
            # Update Batch Number (Reference Number) details
            self.reference_number_id.write({
                'buy_date': self.buy_date,
                'end_date': self.end_date,
            })
        return {'type': 'ir.actions.act_window_close'}
