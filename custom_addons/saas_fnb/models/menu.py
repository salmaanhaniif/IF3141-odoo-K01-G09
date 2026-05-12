from odoo import models, fields


class FnbMenu(models.Model):
    _name = 'fnb.menu'
    _description = 'Master Menu'

    name = fields.Char(string="Nama Menu", required=True)
    price = fields.Float(string="Harga Jual", required=True)
    category = fields.Selection([
        ('food', 'Makanan'),
        ('beverage', 'Minuman'),
        ('snack', 'Camilan')
    ], string="Kategori", required=True, default='food')
    is_available = fields.Boolean(string="Tersedia", default=True)
    description = fields.Text(string="Deskripsi")
    recipe_line_ids = fields.One2many('fnb.recipe.line', 'menu_id', string="Resep/BOM")
    image = fields.Image(string="Gambar Menu", max_width=512, max_height=512)


class FnbRecipeLine(models.Model):
    _name = 'fnb.recipe.line'
    _description = 'Resep/BOM Menu'

    menu_id = fields.Many2one('fnb.menu', string="Menu", required=True, ondelete='cascade')
    inventory_id = fields.Many2one('fnb.inventory', string="Bahan Baku", required=True)
    quantity = fields.Float(string="Jumlah", required=True, default=1.0)
    uom = fields.Selection(related='inventory_id.uom', string='Satuan', readonly=True)
