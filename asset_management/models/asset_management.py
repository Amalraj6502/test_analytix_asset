from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from datetime import date


class AssetWarrantyDetails(models.Model):
    _name = 'asset.warranty.details'

    name = fields.Char(string='details')

class AssetLocation(models.Model):
    _name = 'asset.management.location'
    _rec_name = 'location_code'


    name = fields.Char(string='location')
    country_id = fields.Many2one('res.country', string='Country')
    location_code = fields.Char(string='Location Code')


class AssetPurchase(models.Model):
    _name = 'asset.purchase'
    name = fields.Char(string='Purchase')

class AssetWarranty(models.Model):
    _name ='asset.warranty'
    name = fields.Char(string='Warranty')

class Asset(models.Model):
    _name = 'asset.management'
    _description = 'Asset Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.constrains('asset_type_id')
    def _check_asset_type_pending_qty(self):
        if self.env.user.has_group('asset_management.group_bypass_asset_pending_qty'):
            return
        for rec in self:
            if rec.asset_type_id and rec.asset_type_id.pending_asset_qty <= 0:
                raise UserError(_("The selected Asset Type '%s' has 0 pending quantity. You cannot create or assign this asset.") % rec.asset_type_id.name)

    # for test and service assets
    asset_type_test = fields.Selection(
        related='asset_type_id.asset_type',
        store=True
    )
    validity_date = fields.Date(string="Validity Date")
    end_date = fields.Date(string="End Date")
    quantity_on_hand = fields.Integer(string="Available Quantity", readonly=True)
    initial_quantity = fields.Integer(string="Initial Quantity", help="The first time entered quantity")

    asset_code_id = fields.Many2one('asset.code', string="Asset Model", )
    asset_description = fields.Text(string="Asset Description")

    model_name = fields.Char(
        related='asset_code_id.model_name',
        string='Model Name',
        store=True
    )




    # for upgrades lines
    order_line_ids = fields.One2many('upgrades.details.line', 'line_id', string="Order Lines")

    # for asset admin (Many2many – multiple admins per asset)
    asset_admin_ids = fields.Many2many(
        'res.users',
        'asset_management_admin_rel',
        'asset_id',
        'user_id',
        string="Asset Admins", required=True, tracking=True
    )
    subscription_type = fields.Selection([('basic', 'Basic'),('standard', 'Standard'),('premium', 'Premium')],)


    # for upload the image
    upload_image_asset = fields.Image(string="Upload Image Asset")

    # Basic Asset Information
    name = fields.Char(string="Asset Sequence No", required=True, copy=False,
                       default=lambda self: _('New'), tracking=True)  # readonly enforced via write() + view groups

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

    asset_model = fields.Char(string="Asset Model")

    # for company
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, required=True)


    # for filter
    filter_service = fields.Char(string="Filter Service")
    filter_storable = fields.Char(string="Filter Storable")










    product_id = fields.Many2one('product.product', string="Associated Product",
                                 help="Select the product used in this asset from available options")
    asset_type_id = fields.Many2one('asset.type', string="Asset Type", required=True,
                                    tracking=True,
                                    help="Classification of the asset (e.g., Equipment, Vehicle, Building)")

    # Depreciation Settings
    depreciation_apply = fields.Boolean(string="Enable Depreciation",
                                        help="Check to apply depreciation calculations for this asset")

    # Vendor and Purchase Information
    expired_warranty_date = fields.Date(string="Expired Warranty Date")

    # warranty description
    warranty_description = fields.Text(string="Warranty Description")



    vendor_id = fields.Many2one('asset.vendor', string="Associated Vendor ",
                                help="Select the vendor or supplier of this asset")
    invoice_date = fields.Date(string="Invoice Date", tracking=True, help="Date when the asset was purchased or acquired")
    amount = fields.Float(string="Purchase Price", required=True, tracking=True, help="Initial cost of acquiring the asset")
    asset_location = fields.Many2one('asset.management.location', string="Asset Location", required=True, tracking=True)
    warranty_id = fields.Many2one('asset.warranty', string="Vendor Warranty", tracking=True)
    asset_purchase_id = fields.Many2one('asset.purchase',string="Asset Purchase From")


    # Computed Financial Fields
    current_amount = fields.Float(string="Current Book Value", compute="_compute_current_amount",
                                  help="Current value of the asset after depreciation (Read-only)")
    total_depreciation_amount = fields.Float(string="Accumulated Depreciation",
                                             compute='_compute_total_depreciation_amount', store=True,
                                             help="Total depreciation applied to the asset to date (Read-only)")
    total_maintenance_amount = fields.Float(string="Total Maintenance Cost",

                                            compute='_compute_total_maintenance_amount', store=True,
                                            help="Sum of all maintenance expenses for this asset (Read-only)")
    # Asset Status
    status = fields.Selection([
        ('assign', 'Assign'),
        ('remote_user', 'Remote User'),
        ('return', 'Return'),
        ('in_stock', 'Storable In Stock'),
        ('repair', 'Repair'),
        ('depreciated', 'Depreciated'),
        ('service_in_stock', 'Service In stock'),
        ('no_stock', 'No Stock'),
        ('expired', 'Expired'),
        ('scrap', 'Scrapped')
    ], compute="_compute_status", store=True, string="Status", default='in_stock', tracking=True)
    scrap_date = fields.Date(string="Scrap Date", tracking=True)
    scrap_state = fields.Selection([
        ('fully_scrapped', 'Fully Scrapped'),
        ('semi_scrapped', 'Semi Scrapped')
    ], string="Scrap State", tracking=True)
    scrap_value = fields.Integer(string="Scrap Value")

    # Related Documents and Entries
    document_ids = fields.Many2many('ir.attachment', string="Asset Documentation",
                                    help="Upload multiple documents related to the asset (e.g., Warranty,Invoice)")
    transfer_ids = fields.One2many('asset.transfer.entry', 'asset_id', string="Transfer Entries")
    maintenance_ids = fields.One2many('asset.maintenance.entry', 'asset_id', string="Maintenance Entries")
    depreciation_ids = fields.One2many('asset.depreciation.entry', 'asset_id', string="Depreciation Entries")

    # Link to maintenance.equipment
    equipment_id = fields.Many2one('maintenance.equipment', string="Linked Equipment", readonly=True, copy=False)
    maintenance_request_count = fields.Integer(
        string='Maintenance Requests',
        compute='_compute_maintenance_request_count'
    )

    # Additional Information
    last_depreciation_date = fields.Date(string="Last Depreciation Date", help="Last Depreciation Entry Date",
                                         readonly=True)
    transfer_count = fields.Integer(string='Asset Transfer History',
                                    compute='_compute_all_count', store=True)
    maintenance_count = fields.Integer(string='Maintenanockce Records',
                                       compute='_compute_all_count', store=True)
    depreciation_count = fields.Integer(string='Depreciation Entries',
                                        compute='_compute_all_count', store=True)
    invoice_attachment_ids = fields.Many2many('ir.attachment', 'asset_mgt_attach_rel', 'asset_id', 'att_id', string="Vendor Bill")

    invoice_id = fields.Many2one('account.move', string="Associated Invoice")
    months_left = fields.Integer(string='Months Left', )
    assigned_user = fields.Char(string="Assigned User", compute='_compute_assigned_user',
                                store=True)
    assign_by = fields.Char(string="Assigned By", compute='_compute_assigned_user',
                            store=True)
    remaining_warranty = fields.Char(string="Remaining Warranty",
                                     compute="_compute_months_left", store=True)
    warranty_status = fields.Char(string='Warranty Status')

    asset_date = fields.Date(string="Acquisition Date")
    warranty_details_id = fields.Many2one('asset.warranty.details', string="Warranty Details")
    asset_item_ids = fields.One2many('asset.management.item', 'asset_id', string="Asset Items")
    purchase_line_id = fields.Many2one('purchase.order.line', string="Source Purchase Line", readonly=True, copy=False)


    @api.onchange('asset_type_id')
    def _onchange_asset_type_id(self):
        for rec in self:
            if rec.asset_type_id and rec.asset_type_id.customer_ids:
                rec.asset_admin_ids = [(6, 0, rec.asset_type_id.customer_ids.ids)]

    # for service product quantity
    @api.depends('quantity_on_hand', 'end_date', 'asset_type_test', 'asset_item_ids.status')
    def _compute_status(self):
        today = date.today()
        for rec in self:
            # ⛔ Skip manually scrapped assets to ensure status persists
            if rec.status == 'scrap':
                continue

            # 👉 Apply logic ONLY for service
            if rec.asset_type_test != 'service':
                continue  # skip other records

            # 🔴 Check if all sub-items are expired
            if rec.asset_item_ids and all(item.status == 'expiry' for item in rec.asset_item_ids):
                rec.status = 'expired'
                continue

            # 🔴 Highest priority → Expired (based on parent date)
            if rec.end_date and rec.end_date < today:
                rec.status = 'expired'

            # 🟡 No stock
            elif rec.quantity_on_hand == 0:
                rec.status = 'no_stock'

            # 🟢 In stock
            else:
                rec.status = 'service_in_stock'

    def action_add_to_stock(self):
        for rec in self:
            rec.status = 'in_stock'

    def action_assign_asset(self):
        for rec in self:
            rec.status = 'assign'

    def action_return_asset(self):
        for rec in self:
            rec.status = 'return'

    def action_renew_service(self):
        for rec in self:
            # Build chatter message to log old details before reset
            chatter_msg = f"Service Renewal Initiated" \
                          f"The service asset was expired. Old details recorded below:" \
                          f"• Old Invoice Date: {rec.invoice_date or 'N/A'}" \
                          f"• Old Purchase Price: {rec.amount}" \
                          f"• Old Validity Date: {rec.validity_date or 'N/A'}" \
                          f"• Old Expiry Date: {rec.end_date or 'N/A'}" \
                          f"• Old Vendor Bill: {rec.vendor_bill_id.name if rec.vendor_bill_id else 'N/A'}"
            
            rec.message_post(body=chatter_msg)
            
            # Update/Reset fields for new cycle
            rec.write({
                'invoice_date': False,
                'amount': 0.0,
                'vendor_bill_id': False,
                'validity_date': False,
                'end_date': False,
                'invoice_attachment_ids': [(5, 0, 0)],
            })

    # Compute warranty expiry date
    @api.depends('invoice_date', 'warranty_id')
    def _compute_warranty_expiry(self):
        for rec in self:
            if rec.invoice_date and rec.warranty_id:
                years = float(rec.warranty_id.name)
                months = int(years * 12)

                rec.expired_warranty_date = rec.invoice_date + relativedelta(
                    months=months
                )
            else:
                rec.expired_warranty_date = False

    # Compute methods
    @api.depends('expired_warranty_date')
    def _compute_months_left(self):
        today = fields.Date.today()
        for record in self:
            if record.expired_warranty_date:
                if record.expired_warranty_date < today:
                    record.remaining_warranty = 'Expired'
                    record.warranty_status = 'expired'

                elif record.expired_warranty_date == today:
                    record.remaining_warranty = 'Today'
                    record.warranty_status = 'danger'

                else:
                    rd = relativedelta(record.expired_warranty_date, today)
                    total_months = rd.years * 12 + rd.months + (
                            rd.days / 30)  # Approximate

                    if total_months > 6:
                        record.warranty_status = 'success'
                    elif 3 <= total_months <= 6:
                        record.warranty_status = 'warning'
                    else:
                        record.warranty_status = 'danger'
                    years = rd.years
                    months = rd.months
                    days = rd.days

                    parts = []
                    if years > 0:
                        parts = [f"{years} year{'s' if years > 1 else ''}"]
                    elif months > 0:
                        parts = [f"{months} month{'s' if months > 1 else ''}"]
                    elif days > 0:
                        parts = [f"{days} day{'s' if days > 1 else ''}"]

                    print("parts : ", parts)
                    record.remaining_warranty = ', '.join(parts)

            else:
                record.remaining_warranty = 'No warranty'
                record.warranty_status = 'expired'

    @api.depends('transfer_ids')
    def _compute_assigned_user(self):
        for record in self:
            # Check if there are any transfer entries
            if record.transfer_ids:
                # Retrieve the most recent transfer entry based on 'assign_date'
                last_transfer = record.transfer_ids[-1]
                if last_transfer:
                    # Get the user who assigned the asset in the last transfer
                    record.assigned_user = last_transfer.transfer_employee_id.name
                    record.assign_by = last_transfer.assign_by.id
                else:
                    record.assigned_user = ''
                    record.assign_by = ''
            else:
                # Handle the case where there are no transfer entries
                record.assigned_user = ''
                record.assign_by = ''

    def _compute_maintenance_request_count(self):
        for record in self:
            record.maintenance_request_count = self.env['maintenance.request'].search_count([
                ('equipment_id.name', '=', record.name)
            ])

    def action_view_items(self):
        self.ensure_one()
        return {
            'name': 'Sub Assets',
            'type': 'ir.actions.act_window',
            'res_model': 'asset.management.item',
            'view_mode': 'tree,form',
            'domain': [('asset_id', '=', self.id)],
            'context': {'default_asset_id': self.id},
        }

    def action_open_maintenance_requests(self):
        self.ensure_one()
        # Find the first equipment matching the asset name to use as default for new requests
        equipment = self.env['maintenance.equipment'].search([
            ('name', '=', self.name)
        ], limit=1)
        if not equipment:
            equipment = self.env['maintenance.equipment'].create({
                'name': self.name,
            })
            
        return {
            'name': 'Maintenance Requests',
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.request',
            'view_mode': 'kanban,tree,form',
            'views': [
                (self.env.ref('maintenance.hr_equipment_request_view_kanban').id, 'kanban'),
                (self.env.ref('maintenance.hr_equipment_request_view_tree').id, 'tree'),
                (self.env.ref('maintenance.hr_equipment_request_view_form').id, 'form'),
            ],
            # 🌟 Changed this to find ALL requests where the equipment name matches the asset name
            'domain': [('equipment_id.name', '=', self.name)],
            'context': {
                'default_equipment_id': equipment.id,
                'search_default_active': True,
            },
        }

    @api.depends('transfer_ids', 'maintenance_ids', 'depreciation_ids')
    def _compute_all_count(self):
        for record in self:
            record.transfer_count = len(record.transfer_ids)
            record.maintenance_count = len(record.maintenance_ids)
            record.depreciation_count = len(record.depreciation_ids)

    @api.depends('amount', )
    def _compute_current_amount(self):
        for record in self:
            record.current_amount = record.amount - record.total_depreciation_amount

    @api.depends('depreciation_ids.depreciation_amount')
    def _compute_total_depreciation_amount(self):
        for record in self:
            record.total_depreciation_amount = sum(record.depreciation_ids.mapped('depreciation_amount'))

    @api.depends('maintenance_ids.maintenance_amount')
    def _compute_total_maintenance_amount(self):
        for record in self:
            record.total_maintenance_amount = sum(record.maintenance_ids.mapped('maintenance_amount'))

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """
        Override to bypass 'Asset multi company' record rule for the
        repair_asset_id / return_asset_id dropdowns.

        Critical fix: Odoo evaluates each One2many domain clause as a
        SEPARATE EXISTS subquery, so searching:
            [transfer_ids.status='assigned', transfer_ids.employee_id=X]
        can match assets where those two conditions are on DIFFERENT transfer
        entries (e.g. an old returned entry + a new entry for someone else).

        Solution: query asset.transfer.entry directly so BOTH conditions
        are enforced on the SAME row, then return the matching asset IDs.
        """
        args = args or []

        is_assigned_search = any(
            isinstance(leaf, (list, tuple)) and len(leaf) == 3
            and leaf[0] == 'transfer_ids.status' and leaf[2] == 'assigned'
            for leaf in args
        )

        if is_assigned_search:
            # Extract employee_id value from the domain args (may or may not be present)
            employee_id = None
            for leaf in args:
                if (isinstance(leaf, (list, tuple)) and len(leaf) == 3
                        and leaf[0] == 'transfer_ids.transfer_employee_id'):
                    employee_id = leaf[2]

            # Build transfer.entry domain — both conditions on the SAME row
            transfer_domain = [('status', '=', 'assigned')]
            if employee_id:
                transfer_domain.append(('transfer_employee_id', '=', employee_id))

            # sudo() bypasses all company record rules
            transfers = self.env['asset.transfer.entry'].sudo().search(transfer_domain)
            asset_ids = transfers.mapped('asset_id').ids

            # Optionally filter by typed name
            asset_domain = [('id', 'in', asset_ids)]
            if name:
                asset_domain.append((self._rec_name, operator, name))

            records = self.sudo().search(asset_domain, limit=limit)
            return records.sudo().name_get()

        return super().name_search(name=name, args=args, operator=operator, limit=limit)

    def name_get(self):
        """
        Show descriptive label in dropdowns:
        [Asset Type] Sequence → Assigned Employee
        Falls back gracefully when data is incomplete.
        """
        result = []
        for rec in self.sudo():
            # Sequence number
            seq = rec.name if (rec.name and rec.name != 'New') else ''
            # Asset type name
            asset_type = rec.asset_type_id.name if rec.asset_type_id else ''
            # Who it is assigned to (from latest transfer entry)
            assigned = ''
            if rec.transfer_ids:
                latest = rec.transfer_ids.filtered(
                    lambda t: t.status == 'assigned'
                )
                if latest:
                    assigned = latest[-1].transfer_employee_id.name or ''

            parts = []
            if asset_type:
                parts.append(f'[{asset_type}]')
            if seq:
                parts.append(seq)
            if assigned:
                parts.append(f'→ {assigned}')

            label = ' '.join(parts) if parts else (rec.name or 'Asset')
            result.append((rec.id, label))
        return result

    @api.model
    def create(self, vals):
        if 'quantity_on_hand' in vals and vals['quantity_on_hand']:
            vals['initial_quantity'] = vals['quantity_on_hand']

        if vals.get('name', 'New') == 'New':

            company = self.env.company
            company_prefix = company.asset_code or ''

            asset_type = self.env['asset.type'].browse(vals.get('asset_type_id'))
            type_code = (asset_type.code or 'GEN').upper()

            # 🔹 Resolve asset_code_id record from vals
            asset_code = self.env['asset.code'].browse(vals.get('asset_code_id')) if vals.get('asset_code_id') else None
            asset_code_name = (asset_code.name or '') if asset_code else ''

            # 🔹 Filter by company + asset type
            last_asset = self.search([
                ('asset_type_id', '=', asset_type.id),
                ('company_id', '=', company.id)
            ], order="id desc", limit=1)

            if last_asset and last_asset.name:
                last_number = int(last_asset.name.split('-')[-1])
                next_number = last_number + 1
            else:
                next_number = 1

            seq = str(next_number).zfill(3)

            vals['name'] = f"{company_prefix}-{type_code}-{asset_code_name}-{seq}"
            vals['company_id'] = company.id

        # ✅ Step 1: Create your model record (outside the if condition to ensure it always runs)
        record = super().create(vals)

        # ✅ Step 2: Create maintenance.equipment record
        category = self.env['maintenance.equipment.category'].search([
            ('name', '=', record.asset_type_id.name)
        ], limit=1)
        equipment = self.env['maintenance.equipment'].create({
            'name': record.name,  #  same name
            'category_id': record.asset_type_id.id if category else False,
            # map other fields if needed
            # 'category_id': record.asset_type_id.id,
            # 'company_id': record.company_id.id,
        })
        record.equipment_id = equipment.id

        # ✅ Step 3: Automatically register on PO line
        if record.asset_type_id:
            record._register_asset_on_po_line()

        return record

    def write(self, vals):
        # ── Sequence protection ──────────────────────────────────────────────
        # Only users with "Edit Sequence Access" may change the Asset Sequence No.
        if 'name' in vals and not self.env.user.has_group(
                'asset_management.group_edit_sequence'):
            raise UserError(_(
                "You do not have permission to edit the Asset Sequence Number. "
                "Please ask an administrator to grant you the "
                "'Edit Sequence Access' right."
            ))
        # ────────────────────────────────────────────────────────────────────
        if 'asset_type_id' in vals:
            for rec in self:
                # Unregister from the old line before switching
                if rec.purchase_line_id:
                    rec.purchase_line_id.asset_registered_qty = max(0, rec.purchase_line_id.asset_registered_qty - 1)
                    rec.purchase_line_id = False

        res = super().write(vals)

        if 'asset_type_id' in vals:
            for rec in self:
                rec._register_asset_on_po_line()
        return res

    def unlink(self):
        for rec in self:
            if rec.purchase_line_id:
                rec.purchase_line_id.asset_registered_qty = max(0, rec.purchase_line_id.asset_registered_qty - 1)
        return super().unlink()

    def _register_asset_on_po_line(self):
        self.ensure_one()
        # If purchase_line_id is already set (e.g. from wizard), just increment it
        if self.purchase_line_id:
            self.purchase_line_id.asset_registered_qty += 1
            return

        # Find matching product by name
        product = self.env['product.product'].search([('name', '=', self.asset_type_id.name)], limit=1)
        if product:
            # Find the first PO line for this product that has pending quantity
            po_lines = self.env['purchase.order.line'].search([
                ('product_id', '=', product.id),
                ('qty_received', '>', 0)
            ], order='id asc')
            
            # Since pending_asset_qty is computed, we filter in Python
            target_line = po_lines.filtered(lambda l: l.pending_asset_qty > 0)
            
            if target_line:
                target_line[0].asset_registered_qty += 1
                self.purchase_line_id = target_line[0].id

    # @api.model
    # def create(self, vals):
    #     if vals.get('name', 'New') == 'New':
    #         # If asset_type_id is provided during creation
    #         asset_type_id = vals.get('asset_type_id')
    #         if asset_type_id:
    #             asset_type = self.env['asset.type'].browse(asset_type_id)
    #             if asset_type.name.lower() == 'laptop':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-LAP-{seq_number}'
    #             elif asset_type.name.lower() == 'desktop':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-DSK-{seq_number}'
    #             elif asset_type.name.lower() == 'monitor':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-MTR-{seq_number}'
    #             elif asset_type.name.lower() == 'keyboard':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-KYB-{seq_number}'
    #             elif asset_type.name.lower() == 'mouse':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-MOUS-{seq_number}'
    #             elif asset_type.name.lower() == 'headset desktop':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-HSDK-{seq_number}'
    #             elif asset_type.name.lower() == 'webcam':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-WBCM-{seq_number}'
    #             elif asset_type.name.lower() == 'usb hub':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-USBHUB-{seq_number}'
    #             elif asset_type.name.lower() == 'usb lan adapter':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-USBLAN-{seq_number}'
    #             elif asset_type.name.lower() == 'smart phone':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-SPH-{seq_number}'
    #             elif asset_type.name.lower() == 'feature phone':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-FPH-{seq_number}'
    #             elif asset_type.name.lower() == 'voip phone':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-VPH-{seq_number}'
    #             elif asset_type.name.lower() == 'laptop charger':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-LPCH-{seq_number}'
    #             elif asset_type.name.lower() == 'printer':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-PNTR-{seq_number}'
    #             elif asset_type.name.lower() == 'cctv':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-CCTV-{seq_number}'
    #             elif asset_type.name.lower() == 'nvr':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-NVR-{seq_number}'
    #             elif asset_type.name.lower() == 'nas':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-NAS-{seq_number}'
    #             elif asset_type.name.lower() == 'server':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-SR-{seq_number}'
    #             elif asset_type.name.lower() == 'network switch':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-NS-{seq_number}'
    #             elif asset_type.name.lower() == 'access point':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-AP-{seq_number}'
    #             elif asset_type.name.lower() == 'wifi router':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-WR-{seq_number}'
    #             elif asset_type.name.lower() == 'usb':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-USB-{seq_number}'
    #             elif asset_type.name.lower() == 'hard drive':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-HD-{seq_number}'
    #             elif asset_type.name.lower() == 'sst':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-SST-{seq_number}'
    #             elif asset_type.name.lower() == 'ram ddr4':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-RAMDDR4-{seq_number}'
    #             elif asset_type.name.lower() == 'ram ddr3':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-RAMDDR3-{seq_number}'
    #             elif asset_type.name.lower() == 'headset laptop':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-HSLP-{seq_number}'
    #             elif asset_type.name.lower() == 'projector':
    #
    #                 seq_number = self.env['ir.sequence'].next_by_code('asset.management') or '0000'
    #                 vals['name'] = f'ANX-PJR-{seq_number}'
    #             else:
    #                 # Default sequence logic
    #                 vals['name'] = self.env['ir.sequence'].next_by_code('asset.management') or 'New'
    #         else:
    #             # If asset_type_id not set, use default
    #             vals['name'] = self.env['ir.sequence'].next_by_code('asset.management') or 'New'
    #     return super(Asset, self).create(vals)

    def generate_depreciation_entries(self):
        """Generate depreciation entries with value subtraction."""
        assets = self.search(
            [('status', '!=', 'destroyed'), ('depreciation_apply', '=', True)])

        for asset in assets:
            # Check if the maximum number of depreciation entries has been reached
            existing_entries_count = self.env['asset.depreciation.entry'].search_count(
                [('asset_id', '=', asset.id), ('create_uid', '=', 1)])
            max_entries = asset.asset_type_id.maximum_depreciation_entries

            if max_entries and existing_entries_count >= max_entries:
                continue  # Skip this asset if the maximum number of entries has been reached

            # Determine the starting date for depreciation
            start_date = asset.last_depreciation_date if asset.last_depreciation_date else asset.invoice_date
            if not start_date:
                continue  # Skip if no valid starting date

            # Calculate next depreciation date
            if asset.asset_type_id.depreciation_frequency == 'yearly':
                next_depreciation_date = start_date + relativedelta(
                    years=asset.asset_type_id.depreciation_start_delay)
            elif asset.asset_type_id.depreciation_frequency == 'monthly':
                next_depreciation_date = start_date + relativedelta(
                    months=asset.asset_type_id.depreciation_start_delay)
            elif asset.asset_type_id.depreciation_frequency == 'days':
                next_depreciation_date = start_date + timedelta(
                    days=asset.asset_type_id.depreciation_start_delay)
            else:
                continue  # Invalid depreciation type

            # Check if depreciation needs to be applied today
            if next_depreciation_date > datetime.today().date():
                continue  # Skip if next depreciation date is in the future

            # Determine the depreciation amount and subtract it from the value
            if asset.asset_type_id.depreciation_method == 'fix':
                depreciation_amount = asset.asset_type_id.depreciation_rate
            elif asset.asset_type_id.depreciation_method == 'percentage':
                base_amount = asset.amount if asset.asset_type_id.depreciation_basis == 'real_value' else asset.current_amount
                depreciation_amount = (
                                              base_amount * asset.asset_type_id.depreciation_rate) / 100
            else:
                continue  # Invalid depreciation value type

            # Subtract the depreciation amount from the asset's value
            if asset.asset_type_id.depreciation_basis == 'real_value':
                asset.amount -= depreciation_amount
            else:
                asset.total_depreciation_amount -= depreciation_amount

            # Update the last depreciation date and create an entry in the depreciation model
            asset.last_depreciation_date = next_depreciation_date

            # Create a depreciation entry in the 'asset.depreciation' model
            self.env['asset.depreciation.entry'].create({
                'asset_id': asset.id,
                'created_by': self.env.uid,
                'depreciation_amount': depreciation_amount,
                'entry_date': datetime.today().date(),
            })

            print(
                f"Depreciation Entry Created for {asset.name}: {depreciation_amount} deducted on {next_depreciation_date}"
            )


class AssetTransferEntry(models.Model):
    _name = 'asset.transfer.entry'
    _description = 'Asset Transfer Entry'

    # Fields for tracking asset transfers
    asset_id = fields.Many2one('asset.management', string="Asset Reference",
                               help="Choose the asset for which the transfer is being recorded")
    transfer_employee_id = fields.Many2one('hr.employee', string="Assigned To",
                                           help="Employee who is receiving or has received the asset")
    assign_date = fields.Date(string="Assign Date", help="Date when the asset was assigned to the employee")
    assign_by = fields.Many2one('res.users', string="Assign By", default=lambda self: self.env.user,
                                help="Person responsible for assigning the asset")
    return_date = fields.Date(string="Return Date", help="Date when the asset was returned by the employee")
    status = fields.Selection([
        ('assigned', 'Assigned'),
        ('returned', 'Returned'),
        ('under_maintenance', 'Under Maintenance')
    ], string="Status", help="Current status of the asset transfer")

#     for upload images in a history wise
    upload_image = fields.One2many('ir.attachment', 'res_id', string="Asset Image")


class AssetMaintenanceEntry(models.Model):
    _name = 'asset.maintenance.entry'
    _description = 'Asset Maintenance Entry'

    # Fields for tracking asset maintenance

    asset_id = fields.Many2one('asset.management', string="Asset Reference",
                               help="Choose the asset for undergoing maintenance or repair is being recorded")
    maintenance_vendor_id = fields.Many2one('asset.vendor', string="Select Vendor",
                                            help="Vendor or technician performing the maintenance or repair")
    assign_date = fields.Date(string="Service Start Date",
                              help="Date when the asset was sent for maintenance or repair")
    assign_by = fields.Many2one('res.users', string="Requested By", default=lambda self: self.env.user,
                                help="Person who initiated the maintenance or repair request")
    return_date = fields.Date(string="Completion Date", help="Date when the maintenance or repair was completed")
    maintenance_status = fields.Selection([
        ('in_progress', 'In Progress'),
        ('pending', 'Pending'),
        ('completed', 'Completed')
    ], string="Status", help="Current status of the maintenance or repair process")
    maintenance_amount = fields.Float(string="Amount")
    invoice_id = fields.Many2one('account.move', string="Invoice")
    file_name = fields.Char(string='File Name')
    document = fields.Binary(string='Documents', required=True)

    maintaince_id = fields.Many2one('asset.request', string="Maintenance Entry",)


class AssetDepreciationEntry(models.Model):
    _name = 'asset.depreciation.entry'
    _description = 'Asset Depreciation Entry'

    # Fields for tracking asset depreciation
    asset_id = fields.Many2one('asset.management', string="Asset Reference",
                               help="Choose the asset for which depreciation is being recorded")
    depreciation_amount = fields.Float(string="Amount", help="The monetary value of depreciation applied in this entry")
    entry_date = fields.Date(string="Depreciation Date", help="Date when this depreciation entry was recorded")
    notes = fields.Text(string="Comments", help="Additional information or remarks about this depreciation entry")
    created_by = fields.Many2one('res.users', string="Recorded By", default=lambda self: self.env.user,
                                 help="Person who created this depreciation entry")


class AssetType(models.Model):
    _name = 'asset.type'
    _description = 'Asset Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # enables chatter & field tracking

    active = fields.Boolean(default=True, string="Active")

    # code for prefix
    code = fields.Char(string="Code", required=True, tracking=True)

    # Fields for defining asset types and their depreciation rules
    name = fields.Char(string='Name', required=True, tracking=True)
    stage = fields.Selection([('draft', 'Draft'), ('inventory', 'Inventory')], string="Stage", default='draft', tracking=True)
    customer_ids = fields.Many2many(
        'res.users',
        'asset_type_admin_rel',
        'asset_type_id',
        'user_id',
        string="Admins", default=lambda self: self.env.user, tracking=True
    )
    asset_type = fields.Selection([('storable', 'Storable'), ('service', 'Service')], string="Product Type", default='storable', required=True, tracking=True)
    image = fields.Image(string="Image")
    assign_type = fields.Selection([('individual', 'Individual'), ('department', 'Department')], string="Assign Type", default='individual', tracking=True)

    def action_create_product(self):
        for rec in self:
            if rec.stage == 'draft':
                detailed_type = 'product' if rec.asset_type == 'storable' else 'service'
                self.env['product.template'].create({
                    'name': rec.name,
                    'detailed_type': detailed_type,
                })
                rec.stage = 'inventory'

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        if self.env.context.get('asset_request_dropdown_bypass'):
            return super(AssetType, self.sudo()).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def _name_search(self, name, domain=None, operator='ilike', limit=None, order=None):
        if self.env.context.get('asset_request_dropdown_bypass'):
            return super(AssetType, self.sudo())._name_search(name=name, domain=domain, operator=operator, limit=limit, order=order)
        return super()._name_search(name=name, domain=domain, operator=operator, limit=limit, order=order)

    depreciation_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('days', 'Days')
    ], string='Depreciation Frequency',
        help="How often depreciation is calculated (Yearly, Monthly, or Daily)")

    depreciation_method = fields.Selection([
        ('fix', 'Fix'),
        ('percentage', 'Percentage')
    ], string='Depreciation Value Type',
        help="Whether depreciation is calculated as a percentage or fixed amount")

    depreciation_rate = fields.Float(string='Depreciation Rate',
                                     help="The percentage or fixed amount used to calculate depreciation")
    depreciation_start_delay = fields.Integer(string='Depreciation Start Delay',
                                              help="Time duration before depreciation begins after asset acquisition")
    depreciation_basis = fields.Selection([
        ('real_value', 'Purchase Price'),
        ('depreciation_value', 'Book Price')
    ], string='Depreciation Basis',
        help="Whether depreciation is applied to the adjusted value (after previous depreciation) or the original value")
    maximum_depreciation_entries = fields.Integer(string="Maximum Depreciation Entries",
                                                  help="The maximum number of depreciation entries allowed for this asset type")

    asset_count = fields.Integer(compute='_compute_asset_count', string="Asset Count")
    in_stock_count = fields.Integer(compute='_compute_status_counts', string="In Stock")
    repair_count = fields.Integer(compute='_compute_status_counts', string="In Repair")
    assign_count = fields.Integer(compute='_compute_status_counts', string="Assigned")
    service_in_stock_count = fields.Integer(compute='_compute_status_counts', string="Service In Stock")
    expired_count = fields.Integer(compute='_compute_status_counts', string="Expired")
    rfq_count = fields.Integer(compute='_compute_rfq_count', string="RFQ Count")
    total_received_qty = fields.Float(compute='_compute_qty_status', string="Total Received")
    total_asset_qty = fields.Float(compute='_compute_qty_status', string="Total in Assets")
    pending_asset_qty = fields.Float(compute='_compute_qty_status', string="Pending Asset Entry")

    def _compute_asset_count(self):
        for rec in self:
            rec.asset_count = self.env['asset.management'].search_count([('asset_type_id', '=', rec.id)])

    def _compute_status_counts(self):
        for rec in self:
            assets = self.env['asset.management'].search([('asset_type_id', '=', rec.id)])
            rec.in_stock_count = len(assets.filtered(lambda a: a.status == 'in_stock'))
            rec.repair_count = len(assets.filtered(lambda a: a.status == 'repair'))
            rec.assign_count = len(assets.filtered(lambda a: a.status == 'assign'))
            rec.service_in_stock_count = len(assets.filtered(lambda a: a.status == 'service_in_stock'))
            rec.expired_count = len(assets.filtered(lambda a: a.status == 'expired'))

    def _compute_qty_status(self):
        for rec in self:
            # 1. Calculate Pending Quantity from Purchase Order Lines
            products = self.env['product.product'].search([('name', '=', rec.name)])
            po_lines = self.env['purchase.order.line'].search([
                ('product_id', 'in', products.ids),
                '|',
                ('qty_received', '>', 0),
                '&',
                ('product_id.detailed_type', '=', 'service'),
                ('state', 'in', ['purchase', 'done'])
            ])
            rec.total_received_qty = sum(po_lines.mapped(lambda l: l.qty_received if l.product_id.detailed_type != 'service' else l.product_qty))
            rec.pending_asset_qty = sum(po_lines.mapped('pending_asset_qty'))

            # 2. Total already registered in Assets (for info)
            assets = self.env['asset.management'].search([('asset_type_id', '=', rec.id)])
            rec.total_asset_qty = sum(assets.mapped('initial_quantity'))

    def _compute_rfq_count(self):
        for rec in self:
            # Find products matching the asset type name
            products = self.env['product.product'].search([('name', '=', rec.name)])
            if products:
                # Find unique purchase orders containing these products
                po_ids = self.env['purchase.order.line'].search([
                    ('product_id', 'in', products.ids)
                ]).mapped('order_id').ids
                rec.rfq_count = len(po_ids)
            else:
                rec.rfq_count = 0

    def action_view_assets(self):
        self.ensure_one()
        return {
            'name': 'Assets',
            'type': 'ir.actions.act_window',
            'res_model': 'asset.management',
            'view_mode': 'tree,kanban,form',
            'domain': [('asset_type_id', '=', self.id), ('status', 'in', ['in_stock', 'repair', 'assign'])],
            'context': {
                'default_asset_type_id': self.id,
                'search_default_status': 1,
            },
        }

    def action_create_rfq(self):
        self.ensure_one()
        # Find the matching product.product by name
        product = self.env['product.product'].search(
            [('name', '=', self.name)], limit=1
        )
        return {
            'name': _('Create RFQ'),
            'type': 'ir.actions.act_window',
            'res_model': 'asset.create.rfq.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_asset_type_id': self.id,
                'default_product_id': product.id if product else False,
            }
        }

    def action_view_rfqs(self):
        self.ensure_one()
        # Find products matching the asset type name
        products = self.env['product.product'].search([('name', '=', self.name)])
        po_ids = self.env['purchase.order.line'].search([
            ('product_id', 'in', products.ids)
        ]).mapped('order_id').ids
        return {
            'name': _('Purchase Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'tree',
            'domain': [('id', 'in', po_ids)],
            'context': {'create': False},
        }

    def action_view_pending_asset_entry(self):
        self.ensure_one()
        # Find PO lines that have been received but not yet fully registered as assets
        products = self.env['product.product'].search([('name', '=', self.name)])
        return {
            'name': _('Pending Asset Registration'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.line',
            'view_mode': 'tree',
            'view_id': self.env.ref('asset_management.view_purchase_order_line_asset_tree').id,
            'domain': [('product_id', 'in', products.ids), ('pending_asset_qty', '>', 0)],
            'context': {'create': False},
        }


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    asset_registered_qty = fields.Float(string="Registered Asset Qty", default=0.0, copy=False)
    pending_asset_qty = fields.Float(compute='_compute_pending_asset_qty', string="To Register", store=True)
    total_pending_quantity = fields.Float(compute='_compute_total_pending_quantity', string="Total Pending Qty")

    @api.depends('product_id', 'qty_received', 'product_qty', 'asset_registered_qty', 'state')
    def _compute_total_pending_quantity(self):
        product_ids = self.mapped('product_id').ids
        if not product_ids:
            for line in self:
                line.total_pending_quantity = 0.0
            return
            
        all_lines = self.env['purchase.order.line'].search([
            ('product_id', 'in', product_ids),
            '|',
            ('qty_received', '>', 0),
            '&',
            ('product_id.detailed_type', '=', 'service'),
            ('state', 'in', ['purchase', 'done'])
        ])
        # Group by product
        totals = {}
        for l in all_lines:
            totals[l.product_id.id] = totals.get(l.product_id.id, 0.0) + l.pending_asset_qty
        
        for line in self:
            line.total_pending_quantity = totals.get(line.product_id.id, 0.0)

    @api.depends('qty_received', 'product_qty', 'asset_registered_qty', 'product_id.detailed_type', 'state')
    def _compute_pending_asset_qty(self):
        for line in self:
            if line.product_id.detailed_type == 'service':
                if line.state in ['purchase', 'done']:
                    line.pending_asset_qty = line.product_qty - line.asset_registered_qty
                else:
                    line.pending_asset_qty = 0.0
            else:
                line.pending_asset_qty = line.qty_received - line.asset_registered_qty

    def action_register_as_asset(self):
        self.ensure_one()
        if self.pending_asset_qty <= 0:
            raise UserError(_("No pending quantity to register for this line."))

        return {
            'name': _('Register Received Quantity'),
            'type': 'ir.actions.act_window',
            'res_model': 'asset.register.qty.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_line_id': self.id,
                'default_max_qty': self.pending_asset_qty,
                'default_quantity': self.pending_asset_qty,
            }
        }



class UpgradesDetailsLines(models.Model):
    _name = 'upgrades.details.line'
    _description = 'Upgrade Details'


    line_id = fields.Many2one('asset.management', string="Upgrade Details")
    upgrade_type = fields.Char(string="Upgrade Type")
    date_upgrade = fields.Date(string="Upgrade Date")
    whom_done = fields.Many2one('res.users', string="Done Person")
    upgrade_price = fields.Float(string="Upgrade Price")
    invoice_upload =fields.Binary(string="Invoice Upload")


class ResCompany(models.Model):
    _inherit = 'res.company'

    asset_code = fields.Char(string="Asset Prefix")



# for asset items (slots) based on quantity
class AssetManagementItem(models.Model):
    _name = 'asset.management.item'
    _description = 'Asset Item'
    _rec_name = 'name'

    name = fields.Char(string="Name", required=True)
    asset_id = fields.Many2one('asset.management', string="Asset", ondelete='cascade')
    status = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available'),
        ('in_hold', 'In Hold'),
        ('expiry', 'Expiry')

    ], compute="_compute_status", store=True, string="Status", default='available')
    reference_number = fields.Char(string="Reference Number")
    buy_date = fields.Date(string="Buy Date")
    end_date = fields.Date(string="End Date")
    reference_number_id = fields.Many2one('reference.number', string="Batch Number")

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

    invoice_date = fields.Date(string="Invoice Date")
    purchase_price = fields.Float(string='Purchase Price')
    invoice_attachment_ids = fields.Many2many('ir.attachment', 'asset_item_attach_rel', 'item_id', 'att_id', string="Vendor Bill")

    @api.depends('end_date')
    def _compute_status(self):
        today = fields.Date.today()
        for rec in self:
            if rec.end_date and rec.end_date < today:
                rec.status = 'expiry'
            elif rec.status == 'expiry' or not rec.status:
                rec.status = 'available'

# for employee allocation


class ReferenceNumber(models.Model):
    _name = 'reference.number'
    _description = 'Reference Number'

    name = fields.Char(string="Reference Number")
    buy_date = fields.Date(string="Buy Date")
    end_date = fields.Date(string="End Date")
    status = fields.Selection([
        ('expired', 'Expired'),
        ('not_expired', 'Not Expired')
    ], string="Status", compute="_compute_status", store=True)

    @api.depends('end_date')
    def _compute_status(self):
        today = fields.Date.today()
        for rec in self:
            if rec.end_date and rec.end_date < today:
                rec.status = 'expired'
            else:
                rec.status = 'not_expired'

class EmployeeAllocationService(models.Model):
    _name = 'employee.allocation.service'


    name = fields.Char(string="Employee Allocation Service Name")
    assigned_to_id = fields.Many2one('hr.employee', string="Assigned To")
    department_id = fields.Many2one('hr.department', string="Department")
    allocation_date = fields.Date(string="Allocation Date")
    asset_Service_id = fields.Many2one('asset.management', string="Asset Service", domain="[('asset_type_test', '=', 'service')]")
    asset_item_id = fields.Many2one('asset.management.item', string="Asset Item")
    service_status = fields.Selection([('draft', 'Draft'),('allocated', 'Allocated'),('returned', 'Returned'),('expired', 'Expired'),('in_hold', 'In Hold')], string="Service Status", default='draft')
    assigned_by = fields.Many2one('res.users', string="Assigned By", default=lambda self: self.env.user, readonly=True)

    def action_assign(self):
        for record in self:
            if record.asset_item_id:
                record.asset_item_id.status = 'not_available'
            record.service_status = 'allocated'

    def action_return(self):
        for record in self:
            if record.asset_item_id:
                record.asset_item_id.status = 'available'
            record.service_status = 'returned'

    def action_hold(self):
        for record in self:
            record.service_status = 'in_hold'
            record.asset_item_id.status = 'in_hold'

    def action_hold_to_return(self):
        for record in self:
            record.service_status = 'returned'
            record.asset_item_id.status = 'available'



class AssetCode(models.Model):
    _name = 'asset.code'
    _description = 'Asset Code'

    name = fields.Char(string="Asset Code")
    model_name = fields.Char(string="Model Name")
    description = fields.Text(string="Description")