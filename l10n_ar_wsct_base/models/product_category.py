from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    item_type_t = fields.Selection(
        string="Tipo de Item",
        selection=[
            ("0", "Item general"),
            ("97", "Anticipo"),
            ("99", "Descuento general"),
        ],
        help="Tipo de item a informar en el detalle del comprobante de turismo (clase T).",
    )

    cod_tur = fields.Selection(
        string="Código de Turismo",
        selection=[
            ("1", "Servicio de hotelería - alojamiento sin desayuno"),
            ("2", "Servicio de hotelería - alojamiento con desayuno"),
            ("5", "Excedente"),
        ],
        help="Código de turismo AFIP/ARCA que corresponde a los productos de esta categoría.",
    )
