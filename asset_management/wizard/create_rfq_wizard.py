from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AssetCreateRfqWizard(models.TransientModel):
    _name = 'asset.create.rfq.wizard'
    _description = 'Wizard to Create RFQ from Asset Type'

    creation_type = fields.Selection([
        ('new', 'New'),
        ('exist', 'Exist')
    ], string='Type', default='new', required=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor', required=True, domain=[('supplier_rank', '>', 0)])
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    reference_number_id = fields.Many2one('reference.number', string='Batch Number', domain=[('status', '=', 'expired')])
    asset_type_id = fields.Many2one('asset.type', string='Asset Type')

    def action_generate_rfq(self):
        self.ensure_one()
        if self.quantity <= 0.0:
            raise UserError(_("Quantity must be strictly positive."))

        name = self.product_id.name
        if self.creation_type == 'exist' and self.reference_number_id:
            name += f" (Renewal for Batch: {self.reference_number_id.name})"

        # Create the RFQ (draft purchase order)
        rfq = self.env['purchase.order'].create({
            'partner_id': self.vendor_id.id,
            'order_line': [(0, 0, {
                'product_id': self.product_id.id,
                'name': name,
                'product_qty': self.quantity,
                'price_unit': self.product_id.standard_price or 0.0,
            })],
        })

        # Return action to open the created RFQ
        return {
            'name': _('Request for Quotation'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': rfq.id,
            'view_mode': 'form',
            'target': 'current',
        }
