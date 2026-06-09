from odoo import models, fields

class MaintenanceRequestInherit(models.Model):
    _inherit = "maintenance.request"


    maintenance_request_type = fields.Selection([('general_request', 'General Request'), ('equipment_request', 'Equipment Request')], string="Maintenance Request Type")

    def write(self, vals):
        res = super(MaintenanceRequestInherit, self).write(vals)
        if 'stage_id' in vals:
            for request in self:
                if request.stage_id and request.stage_id.name and request.stage_id.name.lower() in ['scrap', 'scrapped']:
                    if request.equipment_id:
                        asset = self.env['asset.management'].search([('name', '=', request.equipment_id.name)], limit=1)
                        if asset and asset.status != 'scrap':
                            asset.write({
                                'status': 'scrap',
                                'scrap_date': fields.Date.today()
                            })
        return res