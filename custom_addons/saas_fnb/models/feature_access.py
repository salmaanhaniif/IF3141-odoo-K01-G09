from odoo import models, fields, api
from odoo.exceptions import ValidationError


class FnbFeatureAccess(models.Model):
    _name = 'fnb.feature.access'
    _description = 'Manajemen Akses Fitur per Role'
    _rec_name = 'group_id'

    group_id = fields.Many2one('res.groups', string='Role', required=True, ondelete='cascade')
    access_inventory = fields.Boolean(string='Akses Inventaris')
    access_master_menu = fields.Boolean(string='Akses Master Menu')
    access_order = fields.Boolean(string='Akses Pemesanan (POS)')
    access_reservation = fields.Boolean(string='Akses Reservasi')
    access_table = fields.Boolean(string='Akses Konfigurasi Meja')
    access_complaint = fields.Boolean(string='Akses Komplain')

    _sql_constraints = [
        ('fnb_feature_access_group_unique', 'unique(group_id)', 'Setiap role hanya boleh memiliki satu konfigurasi akses fitur.'),
    ]

    @api.constrains('group_id')
    def _check_group_not_admin(self):
        admin_group = self.env.ref('saas_fnb.group_fnb_admin', raise_if_not_found=False)
        for rec in self:
            if admin_group and rec.group_id == admin_group:
                raise ValidationError('Role Admin F&B tidak boleh diubah melalui konfigurasi ini.')

    _feature_targets = {
        'access_inventory': {
            'menu': 'saas_fnb.menu_fnb_inventory',
            'action': 'saas_fnb.action_fnb_inventory',
            'model': 'fnb.inventory',
        },
        'access_master_menu': {
            'menu': 'saas_fnb.menu_fnb_master_menu',
            'action': 'saas_fnb.action_fnb_menu',
            'model': 'fnb.menu',
        },
        'access_order': {
            'menu': 'saas_fnb.menu_fnb_order',
            'action': 'saas_fnb.action_fnb_order',
            'model': 'fnb.order',
            'depends': ['fnb.inventory'],
        },
        'access_reservation': {
            'menu': 'saas_fnb.menu_fnb_reservation',
            'action': 'saas_fnb.action_fnb_reservation',
            'model': 'fnb.reservation',
        },
        'access_table': {
            'menu': 'saas_fnb.menu_fnb_table',
            'action': 'saas_fnb.action_fnb_table',
            'model': 'fnb.table',
        },
        'access_complaint': {
            'menu': 'saas_fnb.menu_fnb_complaint',
            'action': 'saas_fnb.action_fnb_complaint',
            'model': 'fnb.complaint',
        },
    }

    def _apply_feature_access(self):
        """Apply feature access to group"""
        for rec in self:
            group = rec.group_id
            if not group:
                continue

            for field_name, target in self._feature_targets.items():
                is_enabled = bool(rec[field_name])
                command = (4, group.id) if is_enabled else (3, group.id)

                menu = self.env.ref(target['menu'], raise_if_not_found=False)
                if menu:
                    menu.sudo().write({'groups_id': [command]})

                action = self.env.ref(target['action'], raise_if_not_found=False)
                if action:
                    action.sudo().write({'groups_id': [command]})

                self._apply_model_access(group, target['model'], is_enabled)

                for dep_model in target.get('depends', []):
                    grants_access = is_enabled or any(
                        bool(rec[f])
                        for f, t in self._feature_targets.items()
                        if t.get('model') == dep_model
                    )
                    self._apply_model_access(group, dep_model, grants_access)

        self._sync_root_menu_visibility()

    @api.model
    def _sync_root_menu_visibility(self):
        root_menu = self.env.ref('saas_fnb.menu_fnb_root', raise_if_not_found=False)
        admin_group = self.env.ref('saas_fnb.group_fnb_admin', raise_if_not_found=False)
        if not root_menu or not admin_group:
            return

        records = self.sudo().search([])
        visible_group_ids = {
            admin_group.id,
            *records.filtered(
                lambda r: r.access_inventory
                or r.access_master_menu
                or r.access_order
                or r.access_reservation
                or r.access_table
                or r.access_complaint
            ).mapped('group_id').ids,
        }

        root_menu.sudo().write({'groups_id': [(6, 0, list(visible_group_ids))]})

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._apply_feature_access()
        return records

    def write(self, vals):
        result = super().write(vals)
        self._apply_feature_access()
        return result

    def unlink(self):
        targets = self._feature_targets()
        IrModelAccess = self.env['ir.model.access'].sudo()
        IrModel = self.env['ir.model'].sudo()

        for rec in self:
            group = rec.group_id
            for target in targets.values():
                model = IrModel.search([('model', '=', target['model'])], limit=1)
                if model:
                    IrModelAccess.search([
                        ('group_id', '=', group.id),
                        ('model_id', '=', model.id),
                    ]).unlink()

                menu = self.env.ref(target['menu'], raise_if_not_found=False)
                if menu:
                    menu.sudo().write({'groups_id': [(3, group.id)]})

                action = self.env.ref(target['action'], raise_if_not_found=False)
                if action:
                    action.sudo().write({'groups_id': [(3, group.id)]})

        result = super().unlink()
        self._sync_root_menu_visibility()
        return result

    def action_apply_access(self):
        self._apply_feature_access()
        return True
    def _apply_model_access(self, group, model_name, is_enabled):
        IrModelAccess = self.env['ir.model.access'].sudo()
        IrModel = self.env['ir.model'].sudo()

        model = IrModel.search([('model', '=', model_name)], limit=1)
        if not model:
            return

        existing = IrModelAccess.search([
            ('group_id', '=', group.id),
            ('model_id', '=', model.id),
        ], limit=1)

        if is_enabled:
            if not existing:
                IrModelAccess.create({
                    'name': f'access_{model_name.replace(".", "_")}_{group.id}',
                    'model_id': model.id,
                    'group_id': group.id,
                    'perm_read': True,
                    'perm_write': True,
                    'perm_create': False,
                    'perm_unlink': False,
                })
            else:
                existing.write({'perm_read': True, 'perm_write': True})
        else:
            if existing:
                existing.unlink()
