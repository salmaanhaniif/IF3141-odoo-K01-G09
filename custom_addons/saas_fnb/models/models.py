from odoo import models, fields, api
from odoo.exceptions import ValidationError

class FnbInventory(models.Model):
    _name = 'fnb.inventory'
    _description = 'Inventaris Bahan Baku'

    name = fields.Char(string="Nama Bahan Baku", required=True)
    category = fields.Selection([
        ('raw', 'Bahan Mentah (Sayur, Daging)'),
        ('dry', 'Bahan Kering (Tepung, Bumbu)'),
        ('packaging', 'Kemasan (Cup, Kantong)'),
    ], string="Kategori", required=True, default='raw')
    
    quantity = fields.Float(string="Stok Aktual", required=True, default=0.0)
    uom = fields.Selection([
        ('kg', 'Kilogram (kg)'),
        ('g', 'Gram (g)'),
        ('l', 'Liter (L)'),
        ('ml', 'Mililiter (ml)'),
        ('pcs', 'Pcs')
    ], string="Satuan", required=True, default='kg')
    
    company_id = fields.Many2one(
        'res.company',
        string='Perusahaan',
        required=True,
        default=lambda self: self.env.company,
        readonly=True,
    )
    currency_id = fields.Many2one(
        'res.currency',
        string='Mata Uang',
        related='company_id.currency_id',
        store=True,
        readonly=True,
    )
    cost_price = fields.Monetary(string="Harga Modal Satuan", currency_field='currency_id', default=0.0)
    min_stock = fields.Float(string="Batas Peringatan Stok", default=5.0, help="Jika stok di bawah angka ini, status akan menjadi 'Menipis'")

    # Field yang dihitung otomatis berdasarkan jumlah stok
    stock_status = fields.Selection([
        ('safe', 'Aman'),
        ('low', 'Menipis'),
        ('empty', 'Habis')
    ], string="Status Ketersediaan", compute='_compute_stock_status', store=True)

    @api.depends('quantity', 'min_stock')
    def _compute_stock_status(self):
        for record in self:
            if record.quantity <= 0:
                record.stock_status = 'empty'
            elif record.quantity <= record.min_stock:
                record.stock_status = 'low'
            else:
                record.stock_status = 'safe'

class FnbOrder(models.Model):
    _name = 'fnb.order'
    _description = 'Nota Pemesanan POS'
    
    name = fields.Char(string="Nomor Nota", required=True, readonly=True, copy=False, default="Baru")
    customer_name = fields.Char(string="Nama Pelanggan")
    table_id = fields.Many2one('fnb.table', string="Meja", domain="[('status', '=', 'free')]")
    order_date = fields.Datetime(string="Tanggal Pesanan", default=fields.Datetime.now)
    
    # Relasi One2many ke baris pesanan
    order_line_ids = fields.One2many('fnb.order.line', 'order_id', string="Daftar Pesanan")
    
    # Field total yang dihitung otomatis
    total_amount = fields.Float(string="Total Pembayaran", compute="_compute_total_amount", store=True)

    status = fields.Selection([
        ('draft', 'Draft'),
        ('kitchen', 'Dapur'),
        ('done', 'Selesai')
    ], string="Status", default='draft')

    # Tambahkan field ini di dalam class FnbOrder
    payment_status = fields.Selection([
        ('unpaid', 'Belum Bayar'),
        ('paid', 'Lunas')
    ], string="Status Pembayaran", default='unpaid')

    # Fungsi untuk memanggil Pop-up Pembayaran
    def action_open_payment_wizard(self):
        self.ensure_one()
        return {
            'name': 'Proses Pembayaran Digital',
            'type': 'ir.actions.act_window',
            'res_model': 'fnb.payment',
            'view_mode': 'form',
            'target': 'new', # Atribut ini yang membuat tampilannya menjadi pop-up
            'context': {
                'default_order_id': self.id,
                'default_amount': self.total_amount, # Tarik total tagihan otomatis
            }
        }

    @api.depends('order_line_ids.subtotal')
    def _compute_total_amount(self):
        for order in self:
            order.total_amount = sum(line.subtotal for line in order.order_line_ids)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'Baru':
                vals['name'] = self.env['ir.sequence'].next_by_code('fnb.order') or 'Baru'
        return super().create(vals_list)

    def action_send_to_kitchen(self):
        """Move order status from draft to kitchen"""
        for rec in self:
            if rec.table_id and rec.table_id.status != 'free':
                raise ValidationError(f"Meja {rec.table_id.name} tidak tersedia.")
            rec.status = 'kitchen'
            if rec.table_id:
                rec.table_id.status = 'used'

    def action_done(self):
        for order in self:
            # Pengecekan (Validasi)
            for line in order.order_line_ids:
                menu = line.menu_id
                qty_ordered = line.quantity
                
                for recipe in menu.recipe_line_ids:
                    inventory_item = recipe.inventory_id
                    total_needed = recipe.quantity * qty_ordered
                    
                    # Jika stok tidak mencukupi, gagalkan proses dan munculkan error
                    if inventory_item.quantity < total_needed:
                        raise ValidationError(
                            f"Stok tidak mencukupi untuk menu '{menu.name}'!\n"
                            f"Bahan baku '{inventory_item.name}' hanya tersedia {inventory_item.quantity} {inventory_item.uom}, "
                            f"sedangkan yang dibutuhkan adalah {total_needed} {inventory_item.uom}."
                        )

            # Pemotongan Stok (Hanya dijalankan jika TAHAP 1 lolos semua)
            for line in order.order_line_ids:
                for recipe in line.menu_id.recipe_line_ids:
                    recipe.inventory_id.quantity -= (recipe.quantity * line.quantity)
                    
            order.status = 'done'
            if order.table_id:
                order.table_id.status = 'free'

class FnbMenu(models.Model):
    _name = 'fnb.menu'
    _description = 'Master Data Menu'

    name = fields.Char(string="Nama Menu", required=True)
    image = fields.Image(string="Gambar Menu", max_width=512, max_height=512)
    price = fields.Float(string="Harga", required=True)
    category = fields.Selection([
        ('food', 'Makanan'),
        ('beverage', 'Minuman'),
        ('snack', 'Camilan')
    ], string="Kategori", required=True)
    is_available = fields.Boolean(string="Tersedia", default=True)
    description = fields.Text(string="Deskripsi Singkat")
    
    recipe_line_ids = fields.One2many('fnb.recipe.line', 'menu_id', string="Resep / BOM")

class FnbRecipeLine(models.Model):
    _name = 'fnb.recipe.line'
    _description = 'Komposisi Resep Menu'

    menu_id = fields.Many2one('fnb.menu', string="Menu", ondelete='cascade')
    inventory_id = fields.Many2one('fnb.inventory', string="Bahan Baku", required=True)
    
    # Menarik satuan dari master inventaris secara otomatis untuk tampilan
    uom = fields.Selection(related='inventory_id.uom', string="Satuan", readonly=True)
    quantity = fields.Float(string="Kuantitas yang Dibutuhkan", required=True, default=1.0)

class FnbOrderLine(models.Model):
    _name = 'fnb.order.line'
    _description = 'Detail Item Pesanan'

    order_id = fields.Many2one('fnb.order', string="Ref Nota", ondelete='cascade')
    menu_id = fields.Many2one('fnb.menu', string="Menu", required=True)
    
    # Ambil harga dari master menu secara otomatis
    price_unit = fields.Float(string="Harga Satuan", related='menu_id.price', readonly=True)
    quantity = fields.Integer(string="Jumlah", default=1)
    subtotal = fields.Float(string="Subtotal", compute="_compute_subtotal", store=True)

    @api.depends('price_unit', 'quantity')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.price_unit * line.quantity

class FnbTable(models.Model):
    _name = 'fnb.table'
    _description = 'Master Data Meja'

    name = fields.Char(string="Nomor/Nama Meja", required=True)
    capacity = fields.Integer(string="Kapasitas (Orang)", default=2)
    status = fields.Selection([
        ('free', 'Free'),
        ('reserved', 'Reserved'),
        ('used', 'Used')
    ], string="Status", default='free', required=True)
    location = fields.Selection([
        ('indoor', 'Dalam Ruangan'),
        ('outdoor', 'Luar Ruangan (Smoking Area)'),
        ('vip', 'Ruang VIP')
    ], string="Lokasi", default='indoor')

class FnbReservation(models.Model):
    _name = 'fnb.reservation'
    _description = 'Data Reservasi Pelanggan'
    _order = 'date_start desc'

    name = fields.Char(string="Kode Reservasi", readonly=True, copy=False, default="Baru")
    customer_name = fields.Char(string="Nama Pelanggan", required=True)
    customer_phone = fields.Char(string="Nomor Telepon")
    
    # Waktu Reservasi
    date_start = fields.Datetime(string="Waktu Mulai", required=True)
    date_stop = fields.Datetime(string="Waktu Selesai", required=True)
    
    table_id = fields.Many2one('fnb.table', string="Meja", required=True, domain="[('status', '=', 'free')]")
    number_of_people = fields.Integer(string="Jumlah Orang", required=True)
    
    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Dikonfirmasi')
    ], string="Status", default='draft')
    
    note = fields.Text(string="Catatan Khusus")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'Baru':
                vals['name'] = self.env['ir.sequence'].next_by_code('fnb.reservation') or 'Baru'
        return super().create(vals_list)

    def action_confirm(self):
        for rec in self:
            if rec.table_id.status != 'free':
                raise ValidationError(f"Meja {rec.table_id.name} tidak tersedia untuk reservasi.")
            rec.status = 'confirmed'
            rec.table_id.status = 'reserved'


class FnbComplaint(models.Model):
    _name = 'fnb.complaint'
    _description = 'Data Komplain Pelanggan'
    _order = 'complaint_date desc, id desc'

    name = fields.Char(string="Nomor Komplain", required=True, readonly=True, copy=False, default="Baru")
    customer_name = fields.Char(string="Nama Pelanggan", required=True)
    customer_phone = fields.Char(string="Nomor Telepon")
    complaint_date = fields.Datetime(string="Tanggal Komplain", default=fields.Datetime.now, required=True)
    complaint_level = fields.Selection([
        ('low', 'Rendah'),
        ('medium', 'Sedang'),
        ('high', 'Tinggi')
    ], string="Tingkat Komplain", required=True, default='low')
    complaint_category = fields.Selection([
        ('service', 'Pelayanan'),
        ('food_quality', 'Kualitas Makanan/Minuman'),
        ('cleanliness', 'Kebersihan'),
        ('delay', 'Keterlambatan Pesanan'),
        ('other', 'Lainnya')
    ], string="Kategori", required=True, default='service')
    chronology = fields.Text(string="Kronologi Komplain")
    description = fields.Text(string="Detail Komplain", required=True)

    status = fields.Selection([
        ('new', 'Baru'),
        ('handling', 'Diproses'),
        ('resolved', 'Selesai')
    ], string="Status Komplain", default='new', required=True)

    recommended_action = fields.Selection([
        ('apology', 'Sampaikan Permintaan Maaf'),
        ('replace_menu', 'Ganti Menu/Produk'),
        ('refund', 'Refund'),
        ('voucher', 'Berikan Voucher Kompensasi')
    ], string="Rekomendasi Aksi SOP", compute='_compute_recommended_action', store=True)

    selected_action = fields.Selection([
        ('apology', 'Sampaikan Permintaan Maaf'),
        ('replace_menu', 'Ganti Menu/Produk'),
        ('refund', 'Refund'),
        ('voucher', 'Berikan Voucher Kompensasi')
    ], string="Aksi Dipilih")

    action_status = fields.Selection([
        ('pending', 'Belum Dilakukan'),
        ('done', 'Sudah Dilakukan')
    ], string="Status Aksi", default='pending', required=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'Baru':
                vals['name'] = self.env['ir.sequence'].next_by_code('fnb.complaint') or 'Baru'
            vals.setdefault('status', 'new')
            vals.setdefault('action_status', 'pending')
            if not vals.get('chronology'):
                raise ValidationError("Kronologi komplain wajib diisi sebelum menyimpan.")
        return super().create(vals_list)

    @api.depends('complaint_level')
    def _compute_recommended_action(self):
        for rec in self:
            if rec.complaint_level == 'high':
                rec.recommended_action = 'refund'
            elif rec.complaint_level == 'medium':
                rec.recommended_action = 'replace_menu'
            else:
                rec.recommended_action = 'apology'

    @api.onchange('complaint_level')
    def _onchange_complaint_level(self):
        for rec in self:
            if not rec.selected_action:
                rec.selected_action = rec.recommended_action

    def action_start_handling(self):
        for rec in self:
            if rec.status != 'new':
                raise ValidationError("Komplain hanya bisa diproses dari status Baru.")
            rec.status = 'handling'

    def action_mark_resolved(self):
        for rec in self:
            if rec.status != 'handling':
                raise ValidationError("Komplain hanya bisa diselesaikan saat status Diproses.")
            rec.status = 'resolved'

    def action_execute_selected_action(self):
        for rec in self:
            if rec.status != 'handling':
                raise ValidationError("Aksi penanganan hanya bisa dijalankan saat status Diproses.")
            if not rec.selected_action:
                raise ValidationError("Pilih aksi terlebih dahulu sebelum mengeksekusi.")

            rec.action_status = 'done'
        return True


class FnbFeatureAccess(models.Model):
    _name = 'fnb.feature.access'
    _description = 'Manajemen Akses Fitur per Role'
    _rec_name = 'group_id'

    group_id = fields.Many2one(
        'res.groups',
        string='Role',
        required=True,
    )
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

    @api.model
    def _feature_targets(self):
        return {
            'access_inventory': {
                'menu': 'saas_fnb.menu_fnb_inventory',
                'action': 'saas_fnb.action_fnb_inventory',
            },
            'access_master_menu': {
                'menu': 'saas_fnb.menu_fnb_master_menu',
                'action': 'saas_fnb.action_fnb_menu',
            },
            'access_order': {
                'menu': 'saas_fnb.menu_fnb_order',
                'action': 'saas_fnb.action_fnb_order',
            },
            'access_reservation': {
                'menu': 'saas_fnb.menu_fnb_reservation',
                'action': 'saas_fnb.action_fnb_reservation',
            },
            'access_table': {
                'menu': 'saas_fnb.menu_fnb_table',
                'action': 'saas_fnb.action_fnb_table',
            },
            'access_complaint': {
                'menu': 'saas_fnb.menu_fnb_complaint',
                'action': 'saas_fnb.action_fnb_complaint',
            },
        }

    def _apply_feature_access(self):
        targets = self._feature_targets()
        for rec in self:
            group = rec.group_id
            if not group:
                continue

            for field_name, target in targets.items():
                is_enabled = bool(rec[field_name])
                command = (4, group.id) if is_enabled else (3, group.id)

                menu = self.env.ref(target['menu'], raise_if_not_found=False)
                if menu:
                    menu.sudo().write({'groups_id': [command]})

                action = self.env.ref(target['action'], raise_if_not_found=False)
                if action:
                    action.sudo().write({'groups_id': [command]})

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
        groups = self.mapped('group_id')
        result = super().unlink()

        for group in groups:
            for target in targets.values():
                menu = self.env.ref(target['menu'], raise_if_not_found=False)
                if menu:
                    menu.sudo().write({'groups_id': [(3, group.id)]})

                action = self.env.ref(target['action'], raise_if_not_found=False)
                if action:
                    action.sudo().write({'groups_id': [(3, group.id)]})

        self._sync_root_menu_visibility()
        return result

    def action_apply_access(self):
        self._apply_feature_access()
        return True