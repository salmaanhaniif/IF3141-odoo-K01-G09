from odoo import models, fields, api
from odoo.exceptions import ValidationError


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
