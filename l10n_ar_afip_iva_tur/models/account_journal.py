from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # Va acá y no en los módulos WSCT porque este dato no se envía a AFIP/ARCA al
    # pedir el CAE: se usa únicamente en el registro 08 del exportable de IVA Turismo.
    l10n_ar_afip_wsct_payment_type = fields.Selection(
        [
            ("1", "Tarjeta de crédito"),
            ("2", "Tarjeta de débito"),
            ("3", "Transferencia Bancaria"),
        ],
        string="Forma de pago",
        help="Forma de pago a informar en el registro de medios de pago del exportable de IVA Turismo.",
    )
