from odoo import models, fields, api
from odoo.exceptions import ValidationError


class FnbPayment(models.Model):
    _name = 'fnb.payment'
    _description = 'Pembayaran Pesanan'
    _order = 'payment_date desc, id desc'

    name = fields.Char(string="Nomor Pembayaran", required=True, readonly=True, copy=False, default="Baru")
    order_id = fields.Many2one('fnb.order', string="Pesanan", required=True, ondelete='cascade')
    payment_date = fields.Datetime(string="Tanggal Pembayaran", default=fields.Datetime.now, required=True)
    amount = fields.Float(string="Jumlah Pembayaran", required=True)
    payment_method = fields.Selection([
        ('cash', 'Tunai'),
        ('card', 'Kartu Kredit'),
        ('transfer', 'Transfer Bank'),
        ('e_wallet', 'E-Wallet')
    ], string="Metode Pembayaran", required=True, default='cash')
    reference_number = fields.Char(string="Nomor Referensi Transaksi (Opsional)")
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Baru') == 'Baru':
                vals['name'] = self.env['ir.sequence'].next_by_code('fnb.payment') or 'Baru'
        return super().create(vals_list)

    def action_confirm_payment(self):
        """Confirm payment and update order status"""
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError("Jumlah pembayaran harus lebih dari 0.")
            if rec.order_id.total_amount > 0 and rec.amount < rec.order_id.total_amount:
                raise ValidationError(f"Jumlah pembayaran kurang. Total: {rec.order_id.total_amount}, Dibayar: {rec.amount}")
            rec.order_id.payment_status = 'paid'
