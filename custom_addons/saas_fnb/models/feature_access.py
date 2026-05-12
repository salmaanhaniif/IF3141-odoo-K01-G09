from odoo import models, fields, api
from odoo.exceptions import ValidationError


class FnbFeatureAccess(models.Model):
    _name = 'fnb.feature.access'
    _description = 'Manajemen Akses Fitur per Role'

    group_id = fields.Many2one('res.groups', string='Role', required=True, ondelete='cascade')
    access_inventory = fields.Boolean(string='Akses Inventaris')
    access_order = fields.Boolean(string='Akses Pemesanan')
    access_reservation = fields.Boolean(string='Akses Reservasi')
    access_table = fields.Boolean(string='Akses Konfigurasi Meja')
    access_complaint = fields.Boolean(string='Akses Komplain')
    access_master_menu = fields.Boolean(string='Akses Master Menu')

    _sql_constraints = [
        ('fnb_feature_access_group_unique', 'unique(group_id)', 'Setiap role hanya boleh memiliki satu konfigurasi akses fitur.'),
    ]

    @api.constrains('group_id')
    def _check_group_not_admin(self):
        admin_group = self.env.ref('saas_fnb.group_fnb_admin', raise_if_not_found=False)
        for rec in self:
            if admin_group and rec.group_id == admin_group:
                raise ValidationError('Role Admin F&B tidak boleh diubah melalui konfigurasi ini.')

    def _feature_targets(self):
        """Map features to their target models and menu items"""
        return {
            'access_inventory': {
                'models': ['fnb.inventory'],
                'menus': ['saas_fnb.menu_fnb_inventory']
            },
            'access_order': {
                'models': ['fnb.order', 'fnb.order.line'],
                'menus': ['saas_fnb.menu_fnb_order']
            },
            'access_reservation': {
                'models': ['fnb.reservation'],
                'menus': ['saas_fnb.menu_fnb_reservation']
            },
            'access_table': {
                'models': ['fnb.table'],
                'menus': ['saas_fnb.menu_fnb_table']
            },
            'access_complaint': {
                'models': ['fnb.complaint'],
                'menus': ['saas_fnb.menu_fnb_complaint']
            },
            'access_master_menu': {
                'models': ['fnb.menu', 'fnb.recipe.line'],
                'menus': ['saas_fnb.menu_fnb_master_menu']
            }
        }

    def _apply_feature_access(self):
        """Apply feature access to group"""
        for rec in self:
            targets = rec._feature_targets()
            for feature, target_info in targets.items():
                is_enabled = getattr(rec, feature, False)
                # Feature access logic can be extended here

    def _sync_root_menu_visibility(self):
        """Sync root menu visibility based on feature access"""
        root_menu = self.env.ref('saas_fnb.menu_fnb_root', raise_if_not_found=False)
        admin_group = self.env.ref('saas_fnb.group_fnb_admin', raise_if_not_found=False)
        if not root_menu or not admin_group:
            return

        records = self.sudo().search([])
        visible_group_ids = {
            admin_group.id,
            *records.filtered(
                lambda r: r.access_inventory
                or r.access_order
                or r.access_reservation
                or r.access_table
                or r.access_complaint
                or r.access_master_menu
            ).mapped('group_id.id')
        }

        root_menu.write({'groups_id': [(6, 0, list(visible_group_ids))]})

    def create(self, vals_list):
        result = super().create(vals_list)
        result._apply_feature_access()
        result._sync_root_menu_visibility()
        return result

    def write(self, vals):
        result = super().write(vals)
        self._apply_feature_access()
        self._sync_root_menu_visibility()
        return result

    def unlink(self):
        result = super().unlink()
        self._sync_root_menu_visibility()
        return result

    def action_apply_access(self):
        self._apply_feature_access()
        return True
