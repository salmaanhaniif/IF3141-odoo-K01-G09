# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

# FR-01: Pencatatan inventaris bahan baku
class FnbInventory(models.Model):
    _name = 'fnb.inventory'
    _description = 'Inventaris Bahan Baku'
    
    name = fields.Char(string="Nama Bahan Baku", required=True)
    quantity = fields.Float(string="Kuantitas", required=True)
    # Tambahkan field lain sesuai kebutuhan warehouse/procurement

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
        ('done', 'Selesai'),
        ('cancel', 'Dibatalkan')
    ], string="Status", default='draft')

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
        """Mark order as done"""
        for rec in self:
            rec.status = 'done'

# FR-05, 06, 07: Manajemen komplain dan aksi
class FnbComplaint(models.Model):
    _name = 'fnb.complaint'
    _description = 'Manajemen Komplain Pelanggan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string="Judul Komplain", required=True, tracking=True)
    customer_name = fields.Char(string="Nama Pelanggan", required=True, tracking=True)
    severity_level = fields.Selection([
        ('low', 'Rendah'),
        ('medium', 'Sedang'),
        ('high', 'Tinggi - Perlu Tindakan Cepat')
    ], string="Tingkat Komplain", required=True)
    action_taken = fields.Boolean(string="Tindakan Telah Diambil", default=False)
    status = fields.Selection([
        ('open', 'Terbuka'),
        ('investigating', 'Menginvestigasi'),
        ('resolved', 'Selesai')
    ], string="Status", default='open', tracking=True)

    def action_investigate(self):
        for rec in self:
            rec.status = 'investigating'

    def action_resolve(self):
        for rec in self:
            if not rec.action_taken:
                # Validasi: Mencegah komplain ditutup jika tindakan belum diisi
                raise ValidationError("Detail tindakan SOP harus diisi sebelum komplain ditandai selesai!")
            rec.status = 'resolved'

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

    name = fields.Char(string="Kode Reservasi", readonly=True, default="Baru")
    customer_name = fields.Char(string="Nama Pelanggan", required=True)
    customer_phone = fields.Char(string="Nomor Telepon")
    
    # Waktu Reservasi
    date_start = fields.Datetime(string="Waktu Mulai", required=True)
    date_stop = fields.Datetime(string="Waktu Selesai", required=True)
    
    table_id = fields.Many2one('fnb.table', string="Meja", required=True)
    number_of_people = fields.Integer(string="Jumlah Orang", required=True)
    
    status = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Dikonfirmasi'),
        ('done', 'Selesai'),
        ('cancel', 'Dibatalkan')
    ], string="Status", default='draft')
    
    note = fields.Text(string="Catatan Khusus")

    def action_confirm(self):
        for rec in self:
            rec.status = 'confirmed'