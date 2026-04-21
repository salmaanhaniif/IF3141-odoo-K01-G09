# -*- coding: utf-8 -*-
from odoo import models, fields, api

class FnbPayment(models.Model):
    _name = 'fnb.payment'
    _description = 'Transaksi Pembayaran'

    order_id = fields.Many2one('fnb.order', string="Referensi Pesanan", required=True, readonly=True)
    amount = fields.Float(string="Nominal Tagihan", required=True, readonly=True)
    
    payment_method = fields.Selection([
        ('cash', 'Tunai'),
        ('qris', 'QRIS'),
        ('ewallet', 'E-Wallet (GoPay/OVO/Dana)'),
        ('transfer', 'Transfer Bank')
    ], string="Metode Pembayaran", required=True, default='cash')
    
    payment_date = fields.Datetime(string="Waktu Pembayaran", default=fields.Datetime.now)
    # reference_number = fields.Char(string="Nomor Referensi Transaksi (Opsional)")

    def action_confirm_payment(self):
        # Logika ketika tombol bayar ditekan
        for rec in self:
            if rec.order_id:
                # Ubah status pesanan menjadi lunas
                rec.order_id.payment_status = 'paid'
                rec.order_id.status = 'done' # Otomatis selesaikan pesanan