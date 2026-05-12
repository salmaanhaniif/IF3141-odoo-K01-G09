from odoo import models, fields, api


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
            elif record.quantity < record.min_stock:
                record.stock_status = 'low'
            else:
                record.stock_status = 'safe'
