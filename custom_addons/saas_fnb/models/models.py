# -*- coding: utf-8 -*-
from odoo import models, fields, api

# FR-01: Pencatatan inventaris bahan baku
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
    
    cost_price = fields.Float(string="Harga Modal Satuan")
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

# FR-02: Pencatatan nota pemesanan
class FnbOrder(models.Model):
    _name = 'fnb.order'
    _description = 'Nota Pemesanan POS'
    
    name = fields.Char(string="Nomor Nota", required=True, readonly=True, copy=False, default="Baru")
    customer_name = fields.Char(string="Nama Pelanggan")
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
            rec.status = 'kitchen'

    def action_done(self):
        for order in self:
            # Loop setiap item yang dipesan di nota ini
            for line in order.order_line_ids:
                menu = line.menu_id
                qty_ordered = line.quantity
                
                # Loop setiap bahan baku di dalam resep menu tersebut
                for recipe in menu.recipe_line_ids:
                    inventory_item = recipe.inventory_id
                    # Hitung total bahan yang terpakai = kebutuhan resep x jumlah pesanan
                    total_deduction = recipe.quantity * qty_ordered
                    
                    # Kurangi stok di gudang
                    inventory_item.quantity -= total_deduction
                    
            # Ubah status nota menjadi selesai
            order.status = 'done'

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
    
    table_id = fields.Many2one('fnb.table', string="Meja", required=True)
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
            rec.status = 'confirmed'