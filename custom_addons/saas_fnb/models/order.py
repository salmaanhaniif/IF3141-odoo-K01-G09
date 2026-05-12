from odoo import models, fields, api
from odoo.exceptions import ValidationError


class FnbOrder(models.Model):
    _name = 'fnb.order'
    _description = 'Nota Pemesanan'
    _order = 'order_date desc, id desc'

    name = fields.Char(string="Nomor Pesanan", required=True, readonly=True, copy=False, default="Baru")
    customer_name = fields.Char(string="Nama Pelanggan", required=True)
    order_date = fields.Datetime(string="Tanggal Pesanan", default=fields.Datetime.now, required=True)
    table_id = fields.Many2one('fnb.table', string="Meja")
    order_line_ids = fields.One2many('fnb.order.line', 'order_id', string="Item Pesanan")
    payment_ids = fields.One2many('fnb.payment', 'order_id', string="Pembayaran")

    status = fields.Selection([
        ('draft', 'Draft'),
        ('kitchen', 'Dapur'),
        ('done', 'Selesai')
    ], string="Status", default='draft', required=True)

    payment_status = fields.Selection([
        ('unpaid', 'Belum Bayar'),
        ('paid', 'Sudah Bayar')
    ], string="Status Pembayaran", default='unpaid', required=True)

    total_amount = fields.Float(string="Total", compute='_compute_total_amount', store=True)

    @api.depends('order_line_ids.subtotal')
    def _compute_total_amount(self):
        for order in self:
            order.total_amount = sum(line.subtotal for line in order.order_line_ids)

    def action_open_payment_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pembayaran',
            'res_model': 'fnb.payment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_order_id': self.id,
                'default_amount': self.total_amount,
            }
        }

    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Baru') == 'Baru':
                vals['name'] = self.env['ir.sequence'].next_by_code('fnb.order') or 'Baru'
        return super().create(vals_list)

    def action_send_to_kitchen(self):
        """Move order status from draft to kitchen"""
        for rec in self:
            if rec.status == 'draft':
                rec.status = 'kitchen'
                if rec.table_id:
                    rec.table_id.status = 'used'

    def action_done(self):
        """Mark order as done"""
        for order in self:
            if order.status != 'kitchen':
                raise ValidationError("Pesanan harus dalam status Dapur untuk diselesaikan.")
            if order.payment_status != 'paid':
                raise ValidationError("Pesanan harus sudah dibayar sebelum diselesaikan.")
            order.status = 'done'
            if order.table_id:
                order.table_id.status = 'free'


class FnbOrderLine(models.Model):
    _name = 'fnb.order.line'
    _description = 'Item Pesanan'

    order_id = fields.Many2one('fnb.order', string="Pesanan", required=True, ondelete='cascade')
    menu_id = fields.Many2one('fnb.menu', string="Menu", required=True)
    quantity = fields.Float(string="Jumlah", required=True, default=1.0)
    price = fields.Float(string="Harga Satuan", related='menu_id.price', store=True)
    subtotal = fields.Float(string="Subtotal", compute='_compute_subtotal', store=True)

    @api.depends('quantity', 'price')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price
