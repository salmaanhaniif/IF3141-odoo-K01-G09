from odoo import models, fields


class FnbTable(models.Model):
    _name = 'fnb.table'
    _description = 'Daftar Meja'

    name = fields.Char(string="Nomor/Nama Meja", required=True)
    capacity = fields.Integer(string="Kapasitas", required=True, default=4)
    location = fields.Selection([
        ('indoor', 'Indoor'),
        ('outdoor', 'Outdoor'),
        ('vip', 'VIP Room')
    ], string="Lokasi", required=True, default='indoor')
    status = fields.Selection([
        ('free', 'Kosong'),
        ('reserved', 'Dipesan'),
        ('used', 'Terpakai')
    ], string="Status", default='free', required=True)
