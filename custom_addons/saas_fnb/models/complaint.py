from odoo import models, fields, api
from odoo.exceptions import ValidationError


class FnbComplaint(models.Model):
    _name = 'fnb.complaint'
    _description = 'Data Komplain Pelanggan'
    _order = 'complaint_date desc, id desc'

    name = fields.Char(string="Nomor Komplain", required=True, readonly=True, copy=False, default="Baru")
    customer_name = fields.Char(string="Nama Pelanggan", required=True)
    customer_phone = fields.Char(string="Nomor Telepon")
    complaint_date = fields.Datetime(string="Tanggal Komplain", default=fields.Datetime.now, required=True)
    complaint_level = fields.Selection([
        ('low', 'Rendah'),
        ('medium', 'Sedang'),
        ('high', 'Tinggi')
    ], string="Tingkat Komplain", required=True, default='low')
    complaint_category = fields.Selection([
        ('service', 'Pelayanan'),
        ('food_quality', 'Kualitas Makanan/Minuman'),
        ('cleanliness', 'Kebersihan'),
        ('delay', 'Keterlambatan Pesanan'),
        ('other', 'Lainnya')
    ], string="Kategori", required=True, default='service')
    chronology = fields.Text(string="Kronologi Komplain")
    description = fields.Text(string="Detail Komplain", required=True)

    status = fields.Selection([
        ('new', 'Baru'),
        ('handling', 'Diproses'),
        ('resolved', 'Selesai')
    ], string="Status Komplain", default='new', required=True)

    recommended_action = fields.Selection([
        ('apology', 'Sampaikan Permintaan Maaf'),
        ('replace_menu', 'Ganti Menu/Produk'),
        ('refund', 'Refund'),
        ('voucher', 'Berikan Voucher Kompensasi')
    ], string="Rekomendasi Aksi SOP", compute='_compute_recommended_action', store=True)

    selected_action = fields.Selection([
        ('apology', 'Sampaikan Permintaan Maaf'),
        ('replace_menu', 'Ganti Menu/Produk'),
        ('refund', 'Refund'),
        ('voucher', 'Berikan Voucher Kompensasi')
    ], string="Aksi yang Dipilih")

    action_status = fields.Selection([
        ('pending', 'Belum Dilakukan'),
        ('done', 'Sudah Dilakukan')
    ], string="Status Aksi", default='pending', required=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == 'Baru':
                vals['name'] = self.env['ir.sequence'].next_by_code('fnb.complaint') or 'Baru'
            vals.setdefault('status', 'new')
            vals.setdefault('action_status', 'pending')
            if not vals.get('chronology'):
                raise ValidationError("Kronologi komplain wajib diisi sebelum menyimpan.")
        return super().create(vals_list)

    @api.depends('complaint_level')
    def _compute_recommended_action(self):
        for rec in self:
            if rec.complaint_level == 'high':
                rec.recommended_action = 'refund'
            elif rec.complaint_level == 'medium':
                rec.recommended_action = 'replace_menu'
            else:
                rec.recommended_action = 'apology'

    @api.onchange('complaint_level')
    def _onchange_complaint_level(self):
        for rec in self:
            if not rec.selected_action:
                rec.selected_action = rec.recommended_action

    def action_start_handling(self):
        """Start handling complaint"""
        for rec in self:
            if rec.status != 'new':
                raise ValidationError("Komplain hanya bisa diproses dari status Baru.")
            rec.status = 'handling'

    def action_mark_resolved(self):
        """Mark complaint as resolved"""
        for rec in self:
            if rec.status != 'handling':
                raise ValidationError("Komplain hanya bisa diselesaikan saat status Diproses.")
            rec.status = 'resolved'

    def action_execute_selected_action(self):
        """Execute the selected action"""
        for rec in self:
            if rec.status != 'handling':
                raise ValidationError("Aksi penanganan hanya bisa dijalankan saat status Diproses.")
            if not rec.selected_action:
                raise ValidationError("Pilih aksi terlebih dahulu sebelum mengeksekusi.")

            rec.action_status = 'done'
        return True
