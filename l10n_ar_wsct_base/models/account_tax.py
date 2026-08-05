from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_ar_afipws_wsct_is_tourism_vat = fields.Boolean(
        string="IVA Reintegro Turismo",
        default=False,
        help="Indica si el impuesto es IVA Reintegro Turismo, necesario para emitir Factura de Turismo",
    )
