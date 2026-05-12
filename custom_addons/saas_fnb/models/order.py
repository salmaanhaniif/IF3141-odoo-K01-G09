from odoo import models, fields, api
from odoo.exceptions import ValidationError


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
