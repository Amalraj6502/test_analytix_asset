from odoo import models, fields, api


class AssetRequest(models.Model):
    _name = 'asset.request'
    _description = 'Asset Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, copy=False, readonly=True, default='New')
    employee_id = fields.Many2one('hr.employee', string='Requested By', required=True, tracking=True, default=lambda self: self.env.user.employee_id)
    requested_for = fields.Char(string="Requested For")
    requested_employee_id = fields.Many2one('hr.employee', string="Requested Employee", domain="[('department_id', '=', department_id)]")
    department_id = fields.Many2one('hr.department', string='Department Name', required=True, tracking=True)
    manager_id = fields.Many2one('hr.employee', string='Department Manager', tracking=True)
    asset_name = fields.Char(string='Asset Type')
    asset_category_id = fields.Many2one('asset.type', string='Asset Category', required=True)

    request_type = fields.Selection([('new', 'New'),('repair', 'Repair'),('replace', 'Replace'),('return', 'Return')], string='Request Type', required=True)
    return_asset_id = fields.Many2one(
        'asset.management',
        string='Return Asset',
        domain="[('transfer_ids.status', '=', 'assigned'), ('transfer_ids.transfer_employee_id', '=', employee_id)]"
    )

    # for service based asset senario
    asset_type_test = fields.Selection(
        related='asset_category_id.asset_type',
        store=True
    )

    asset_name_service_id = fields.Many2one(
        'asset.management',
        string='Asset Name',
        domain="[('status', '=', 'service_in_stock')]"
    )

    asset_item_id = fields.Many2one(
        'asset.management.item',
        string="Asset Item",
        domain="[('asset_id', '=', asset_name_service_id), ('status', '=', 'available')]"
    )

    item_available_qty = fields.Integer(
        string='Item Available Quantity',
        compute='_compute_item_available_qty',
        store=True,
    )

    @api.depends('asset_name_service_id')
    def _compute_item_available_qty(self):
        for rec in self:
            count = 0
            if rec.asset_name_service_id:
                count = self.env['asset.management.item'].search_count([
                    ('asset_id', '=', rec.asset_name_service_id.id),
                    ('status', '=', 'available')
                ])
            rec.item_available_qty = count

    @api.onchange('asset_name_service_id')
    def _onchange_asset_name_service_id(self):
        if self.asset_name_service_id:
            self.asset_item_id = False

    allocated_service_id = fields.Many2one('asset.management', string='Allocated Service Asset')
    allocated_service_ids = fields.Many2many('asset.management', compute='_compute_allocated_service_ids', string='Allocated Service Assets')

    @api.depends('employee_id', 'requested_employee_id', 'employee_type')
    def _compute_allocated_service_ids(self):
        for rec in self:
            # Check who the target employee is based on the request configuration
            target_employee = rec.requested_employee_id if rec.employee_type == 'exist_employee' and rec.requested_employee_id else rec.employee_id
            
            # Find all active allocations for this employee from the service allocation model
            allocations = self.env['employee.allocation.service'].search([
                ('assigned_to_id', '=', target_employee.id),
                ('service_status', '=', 'allocated')
            ])
            
            # Populate the Many2many field with the service assets found
            rec.allocated_service_ids = allocations.mapped('asset_Service_id')







    
    # -------------------------------------------------------------------------
    # UI-ONLY PROXY FIELD (Does NOT affect your backend functions like action_submit, etc.)
    # -------------------------------------------------------------------------
    request_type_normal = fields.Selection(
        [('new', 'New'), ('repair', 'Repair'), ('replace', 'Replace')],
        string='Request Type',
        compute='_compute_request_type_normal', 
        inverse='_inverse_request_type_normal'
    )
    
    is_self_request = fields.Boolean(compute='_compute_is_self_request')
    justification = fields.Text(string='Additional Comment', required=True)
    asset_allocated_date = fields.Datetime(string='Asset Allocated Date')
    expected_date = fields.Date(string='Expected Date', required=True)
    priority = fields.Selection([('high', 'High'),('medium', 'Medium'),('low', 'Low')], string='Priority', required=True, tracking=True)
    status = fields.Selection([('draft', 'Draft'),('submitted', 'Submitted'),('approved', 'Approved'),('rejected', 'Rejected'),('received', 'Received')], default='draft', string='Status', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    is_manager = fields.Boolean(compute='_compute_is_manager')
    is_asset_request_admin = fields.Boolean(compute='_compute_is_asset_request_admin')
    is_department_head = fields.Boolean(compute='_compute_is_department_head')
    is_hr_department = fields.Boolean(compute='_compute_is_hr_department')
    asset_code = fields.Char(string="Asset Code", help="Please Mention The Asset Code Before Submit The Request")
    requested_datetime = fields.Datetime(
        string="Requested Date",
        default=fields.Datetime.now,
        tracking=True
    )
    employee_type = fields.Selection([
        ('new_employee', 'New Employee'),
        ('exist_employee', 'Existing Employee')
    ])

    repair_asset_id = fields.Many2one(
        'asset.management',
        string="Repair Asset",
        domain="[('transfer_ids.status', '=', 'assigned'), ('transfer_ids.transfer_employee_id', '=', employee_id)]"
    )

    asset_name_id = fields.Many2one(
        'asset.management',
        string='Asset Name',
        domain="[('status', '=', 'in_stock'), ('asset_type_id', '=', asset_category_id)]"
    )

    # for service and storable

    available_qty = fields.Integer(
        string='Available Quantity',
        compute='_compute_available_qty'
    )

    available_qty_service = fields.Integer(
        string='Available Quantity',
        compute='_compute_available_qty_service',
        store=True,
    )




    maintaice_line = fields.One2many('asset.maintenance.entry', 'maintaince_id', string="Lines")

    upload_image = fields.One2many('ir.attachment', 'res_id', string="Asset Image")

    repair_status = fields.Selection([
        ('none', 'None'),
        ('sent', 'Sent to Repair'),
        ('collected', 'Collected')
    ], string='Repair Status', default='none', tracking=True)

    request_method = fields.Selection(
        [
            ('for_me', 'For Me'),
            ('for_someone', 'For Someone')
        ],
        string="For Applying",
        default='for_me'

    )

    is_replaced = fields.Boolean(string="Is Replaced", default=False, tracking=True)

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(AssetRequest, self).fields_get(allfields, attributes)
        # if 'request_type' in res and 'selection' in res['request_type']:
        #     employee = self.env.user.employee_id
        #     is_dept_head = bool(
        #         employee and self.env['hr.department'].search_count([
        #             ('manager_id', '=', employee.id)
        #         ])
        #     )
        #     is_admin = self.env.user.has_group('asset_management.assets_admin_group')
        #
        #     if not (is_dept_head or is_admin):
        #         res['request_type']['selection'] = [
        #             (k, v) for k, v in res['request_type']['selection'] if k != 'return'
        #         ]

        if 'employee_type' in res and 'selection' in res['employee_type']:
            is_hr_or_admin = self.env.user.has_group('asset_management.hr_department_group') or self.env.user.has_group('asset_management.assets_admin_group')
            if not is_hr_or_admin:
                res['employee_type']['selection'] = [
                    (k, v) for k, v in res['employee_type']['selection'] if k == 'exist_employee'
                ]

        return res





    @api.depends('employee_id', 'requested_employee_id', 'employee_type')
    def _compute_repair_asset_domain_ids(self):
        """Fetch ALL assigned assets across ALL companies using sudo()."""
        # Search once outside the loop – same result for every record
        assets = self.env['asset.management'].sudo().search([
            ('transfer_ids.status', '=', 'assigned'),
        ])
        for rec in self:
            rec._repair_asset_domain_ids = assets

    @api.depends('employee_id', 'requested_employee_id', 'employee_type')
    def _compute_return_asset_domain_ids(self):
        """Fetch ALL assigned assets across ALL companies using sudo()."""
        # Search once outside the loop – same result for every record
        assets = self.env['asset.management'].sudo().search([
            ('transfer_ids.status', '=', 'assigned'),
        ])
        for rec in self:
            rec._return_asset_domain_ids = assets

    @api.depends('employee_id')
    def _compute_is_self_request(self):
        for rec in self:
            rec.is_self_request = (rec.employee_id == self.env.user.employee_id)

    @api.depends('request_type')
    def _compute_request_type_normal(self):
        for rec in self:
            if rec.request_type in ['new', 'repair', 'replace']:
                rec.request_type_normal = rec.request_type
            else:
                rec.request_type_normal = False

    def _inverse_request_type_normal(self):
        for rec in self:
            if rec.request_type_normal:
                rec.request_type = rec.request_type_normal

    @api.onchange('request_type_normal')
    def _onchange_request_type_normal(self):
        if self.request_type_normal:
            self.request_type = self.request_type_normal

    @api.depends('asset_category_id')
    def _compute_available_qty(self):
        for rec in self:
            count = 0
            if rec.asset_category_id:
                count = self.env['asset.management'].search_count([
                    ('status', '=', 'in_stock'),
                    ('asset_type_id', '=', rec.asset_category_id.id)
                ])
            rec.available_qty = count




    @api.depends('asset_category_id', 'asset_category_id.asset_type')
    def _compute_available_qty_service(self):
        for rec in self:
            total_qty = 0
            # If category is selected and its type is 'service'
            if rec.asset_category_id and rec.asset_category_id.asset_type == 'service':
                # Match: asset.management.asset_type_id == asset.request.asset_category_id
                # (This is the category match you asked for)
                service_assets = self.env['asset.management'].search([
                    ('asset_type_id', '=', rec.asset_category_id.id)
                ])
                # Sum the on_hand_quantity from all matching assets
                total_qty = sum(service_assets.mapped('quantity_on_hand'))
            
            rec.available_qty_service = total_qty




    def action_approve_admin(self):
        for rec in self:
            rec.status = 'received'

            if rec.asset_type_test == 'service':
                if rec.asset_name_service_id:
                    rec.asset_name_service_id.quantity_on_hand -= 1
                    if rec.asset_item_id:
                        rec.asset_item_id.status = 'not_available'
                    
                    # Create allocation record for service asset
                    self.env['employee.allocation.service'].create({
                        'name': rec.name,
                        'assigned_to_id': rec.requested_employee_id.id if rec.employee_type == 'exist_employee' and rec.requested_employee_id else rec.employee_id.id,
                        'department_id': rec.department_id.id,
                        'allocation_date': rec.asset_allocated_date,
                        'asset_Service_id': rec.asset_name_service_id.id,
                        'asset_item_id': rec.asset_item_id.id if rec.asset_item_id else False,
                        'service_status': 'allocated',
                    })
            else:
                asset = rec.asset_name_id

                if rec.employee_type == 'new_employee':
                    asset.write({
                        'status': 'assign'
                    })
                    transfer = self.env['asset.transfer.entry'].create({
                        'asset_id': asset.id,
                        'status': 'assigned',
                        'assign_date': rec.asset_allocated_date,
                    })

                else:
                    # If exist_employee, use requested_employee_id. Otherwise fallback to employee_id
                    target_employee_id = rec.requested_employee_id.id if rec.employee_type == 'exist_employee' and rec.requested_employee_id else rec.employee_id.id
                    
                    transfer = self.env['asset.transfer.entry'].create({
                        'asset_id': asset.id,
                        'transfer_employee_id': target_employee_id,
                        'assign_date': rec.asset_allocated_date,
                        'status': 'assigned'
                    })

                    # if rec.employee_type == 'exist_employee':
                    #     transfer.status = 'assigned'

                    # Copy attachments
                    for attachment in rec.upload_image:
                        attachment.copy({
                            'res_model': 'asset.transfer.entry',
                            'res_id': transfer.id,
                        })

                    asset.status = 'assign'










    # def action_approve_admin(self):
    #     for rec in self:
    #         rec.status = 'received'
    #
    #         asset = rec.asset_name_id  # no need to search again
    #
    #         if asset:
    #             transfer = self.env['asset.transfer.entry'].create({
    #                 'asset_id': asset.id,
    #                 'transfer_employee_id': rec.employee_id.id,
    #                 'assign_date': rec.asset_allocated_date,
    #             })
    #
    #             # Copy attachments
    #             for attachment in rec.upload_image:
    #                 attachment.copy({
    #                     'res_model': 'asset.transfer.entry',
    #                     'res_id': transfer.id,
    #                 })
    #
    #             # Only when request is for someone
    #             if rec.request_method == 'for_someone' and rec.request_type == 'new':
    #                 transfer.status = 'assigned'
    #
    #                 asset.write({
    #                     'status': 'assign'
    #                 })



    def action_send_to_repair(self):
        for rec in self:
            rec.repair_status = 'sent'
            if rec.repair_asset_id:
                rec.repair_asset_id.status = 'repair'
                # Change transfer entry status
                for transfer in rec.repair_asset_id.transfer_ids:
                    transfer.status = 'under_maintenance'

                # ✅ Use the asset's linked equipment, or find/create one
                asset = rec.repair_asset_id
                equipment = asset.equipment_id
                if not equipment:
                    # Try to find existing equipment by name
                    equipment = self.env['maintenance.equipment'].search([
                        ('name', '=', asset.name)
                    ], limit=1)
                    if not equipment:
                        equipment = self.env['maintenance.equipment'].create({
                            'name': asset.name,
                            'company_id': self.env.company.id,
                        })
                    # Link it back to the asset
                    asset.equipment_id = equipment.id

                # ✅ Create Maintenance Request linked to the asset's equipment
                team = self.env['maintenance.team'].search([], limit=1)
                self.env['maintenance.request'].create({
                    'name': rec.justification or 'Repair Request',
                    'equipment_id': equipment.id,
                    'maintenance_team_id': team.id if team else False,
                    'company_id': self.env.company.id,
                })


    def action_collect_from_repair(self):
        for rec in self:
            rec.repair_status = 'collected'
            if rec.repair_asset_id:
                rec.repair_asset_id.status = 'assign'
                # Change transfer entry status
                for transfer in rec.repair_asset_id.transfer_ids:
                    transfer.status = 'assigned'
            rec.status = 'received'



            # rec.status = 'received'
            # for line in rec.maintaice_line:
            #     if line.asset_id:
            #         line.asset_id.status = 'assign'

    def action_replace_asset(self):
        for rec in self:
            if rec.repair_asset_id:
                asset = rec.repair_asset_id

                asset.status = 'return'
                rec.is_replaced = True

                # Set return_date on latest transfer entry
                transfer = self.env['asset.transfer.entry'].search([
                    ('asset_id', '=', asset.id),
                    ('status', '=', 'assigned')
                ], order='assign_date desc', limit=1)

                if transfer:
                    transfer.return_date = fields.Date.today()
                    transfer.status = 'returned'

            # ✅ Service logic added here
            if rec.asset_type_test == 'service' and rec.allocated_service_id:
                asset = rec.allocated_service_id
                # Match the exact employee who currently has this asset
                target_employee_id = rec.requested_employee_id.id if rec.employee_type == 'exist_employee' and rec.requested_employee_id else rec.employee_id.id

                # Find the active allocation record for this employee and asset
                allocation = self.env['employee.allocation.service'].search([
                    ('assigned_to_id', '=', target_employee_id),
                    ('asset_Service_id', '=', asset.id),
                    ('service_status', '=', 'allocated')
                ], limit=1)

                if allocation:
                    # 1. Update allocation status
                    allocation.service_status = 'returned'

                    # 2. Update sub-item status
                    if allocation.asset_item_id:
                        allocation.asset_item_id.status = 'available'

                    # 3. Increase quantity on the parent asset
                    asset.quantity_on_hand += 1
                    
    def action_return_asset(self):
        for rec in self:
            if rec.request_type == 'return':
                # Match the exact employee who currently has this asset
                target_employee_id = rec.requested_employee_id.id if rec.employee_type == 'exist_employee' and rec.requested_employee_id else rec.employee_id.id

                if rec.asset_type_test == 'service' and rec.allocated_service_id:
                    # --- SERVICE RETURN LOGIC ---
                    asset = rec.allocated_service_id
                    
                    # Find the active allocation record for this employee and asset
                    allocation = self.env['employee.allocation.service'].search([
                        ('assigned_to_id', '=', target_employee_id),
                        ('asset_Service_id', '=', asset.id),
                        # ('service_status', '=', 'allocated')
                    ], limit=1)
                    
                    if allocation:
                        # 1. Update the allocation status to 'returned'
                        allocation.service_status = 'returned'
                        
                        # 2. Set the sub-item status back to 'available'
                        if allocation.asset_item_id:
                            allocation.asset_item_id.status = 'available'
                        
                        # 3. Increment the quantity_on_hand of the service asset
                        asset.quantity_on_hand += 1
                        
                elif rec.return_asset_id:
                    # --- STORABLE RETURN LOGIC (Original) ---
                    asset = rec.return_asset_id
                    
                    # Change the asset.management status to 'return'
                    asset.status = 'return'
                    
                    # Search for the specific matching 'assigned' transfer entry
                    transfer = self.env['asset.transfer.entry'].search([
                        ('asset_id', '=', asset.id),
                        ('transfer_employee_id', '=', target_employee_id),
                        ('status', '=', 'assigned')
                    ], order='assign_date desc', limit=1)
                    
                    if transfer:
                        transfer.status = 'returned'
                        transfer.return_date = fields.Date.today()
                        
                # Finally mark the request itself as finalized
                rec.status = 'received'

    @api.depends('department_id.manager_id')
    def _compute_is_manager(self):
        for rec in self:
            is_admin = self.env.user.has_group('asset_management.assets_admin_group')
            rec.is_manager = is_admin or (rec.department_id and rec.department_id.manager_id.user_id == self.env.user)

    @api.depends('asset_category_id.customer_id')
    def _compute_is_asset_request_admin(self):
        for rec in self:
            is_admin = self.env.user.has_group('asset_management.assets_admin_group')
            rec.is_asset_request_admin = is_admin or (rec.asset_category_id and rec.asset_category_id.customer_id.id == self.env.user.id)

    @api.depends('department_id')
    def _compute_is_department_head(self):
        employee = self.env.user.employee_id
        is_dept_head = bool(
            employee and self.env['hr.department'].search_count([
                ('manager_id', '=', employee.id)
            ])
        )
        for rec in self:
            rec.is_department_head = is_dept_head

    @api.depends_context('uid')
    @api.depends('employee_id')
    def _compute_is_hr_department(self):
        is_hr = self.env.user.has_group('asset_management.hr_department_group')
        for rec in self:
            rec.is_hr_department = is_hr

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id and self.employee_id.department_id:
            self.department_id = self.employee_id.department_id

    def action_submit(self):
        for rec in self:
            rec.status = 'submitted'
            if rec.department_id and rec.department_id.manager_id:
                rec.manager_id = rec.department_id.manager_id

    def action_approve(self):
        for rec in self:
            rec.status = 'approved'
            # No email/notification sent – admin can view the request directly.


    def action_reject(self):
        for rec in self:
            rec.status = 'rejected'

    def _get_or_create_company_sequence(self, company):
        """
        Find or create a per-company ir.sequence for asset requests.
        Each company gets its own independent counter starting from 1.
        """
        IrSequence = self.env['ir.sequence'].sudo()

        # Search for an existing sequence scoped to this specific company
        sequence = IrSequence.search([
            ('code', '=', 'asset.request'),
            ('company_id', '=', company.id),
        ], limit=1)

        if not sequence:
            # Auto-create a new isolated sequence for this company
            sequence = IrSequence.create({
                'name': f'Asset Request - {company.name}',
                'code': 'asset.request',
                'prefix': '',
                'padding': 3,
                'number_next': 1,
                'number_increment': 1,
                'company_id': company.id,
            })

        return sequence

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                company_id = vals.get('company_id') or self.env.company.id
                company = self.env['res.company'].browse(company_id)

                # Get (or auto-create) the sequence that belongs ONLY to this company
                sequence = self._get_or_create_company_sequence(company)
                seq = sequence.next_by_id()  # increments only this company's counter

                prefix = company.asset_code or ''

                vals['name'] = f'AR-{prefix}-{seq}'

        return super().create(vals_list)

    # @api.model_create_multi
    # def create(self, vals_list):
    #     seq_model = self.env['ir.sequence']
    #
    #     for vals in vals_list:
    #         if vals.get('name', 'New') == 'New':
    #             seq = seq_model.next_by_code('asset.request') or '000'
    #
    #             company = self.env['res.company'].browse(
    #                 vals.get('company_id', self.env.company.id)
    #             )
    #
    #             prefix = company.asset_code or 'COMP'
    #
    #             vals['name'] = f'AR-{prefix}-{seq}'
    #
    #     return super().create(vals_list)

    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         if vals.get('name', 'New') == 'New':
    #             # Get sequence
    #             seq = self.env['ir.sequence'].next_by_code('asset.request') or '000'
    #
    #             # Get company prefix
    #             company_id = vals.get('company_id') or self.env.company.id
    #             company = self.env['res.company'].browse(company_id)
    #             prefix = company.asset_code or 'COMP'
    #
    #             vals['name'] = f'AR-{prefix}-{seq}'
    #     return super().create(vals_list)




class MaintenanceRequest(models.Model):
    _name = 'asset.maintenance.request'
    _description = 'Asset Maintenance Request'

    name = fields.Char(string='Name')
    employee_id = fields.Many2one('hr.employee', string='Employee Name', tracking=True, default=lambda self: self.env.user.employee_id)
    department_id = fields.Many2one('hr.department', string='Department Name', required=True, tracking=True)
    asset_id = fields.Many2one('asset.management', string='Asset Type')
    priority = fields.Selection([('high', 'High'),('medium', 'Medium'),('low', 'Low')], string='Priority', required=True)
    description = fields.Text(string='Description')



















