from odoo import models, fields, api
from odoo.exceptions import ValidationError


class FnbReservation(models.Model):
    _name = 'fnb.reservation'
    _description = 'Reservasi Meja'
    _order = 'reservation_date desc, id desc'

    name = fields.Char(string="Nomor Reservasi", required=True, readonly=True, copy=False, default="Baru")
    customer_name = fields.Char(string="Nama Pelanggan", required=True)
    customer_phone = fields.Char(string="Nomor Telepon")
    reservation_date = fields.Datetime(string="Tanggal Reservasi", required=True)
    table_id = fields.Many2one('fnb.table', string="Meja", required=True)
    guest_count = fields.Integer(string="Jumlah Tamu", required=True, default=1)
    notes = fields.Text(string="Catatan")

    status = fields.Selection([
        ('pending', 'Menunggu'),
        ('confirmed', 'Dikonfirmasi'),
        ('cancelled', 'Dibatalkan')
    ], string="Status", default='pending', required=True)

    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'Baru') == 'Baru':
                vals['name'] = self.env['ir.sequence'].next_by_code('fnb.reservation') or 'Baru'
        return super().create(vals_list)

    def action_confirm(self):
        """Confirm reservation"""
        for rec in self:
            if rec.status != 'pending':
                raise ValidationError("Hanya reservasi dengan status Menunggu yang bisa dikonfirmasi.")
            if rec.table_id.status != 'free':
                raise ValidationError("Meja tidak tersedia untuk tanggal tersebut.")
            rec.status = 'confirmed'
            rec.table_id.status = 'reserved'
