from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    codigo_relacion = fields.Selection(
        string="Código de Relación",
        selection=[
            ("1", "Alojamiento Directo a Turista No Residente"),
            ("2", "Alojamiento a Agencia de Viaje Residente"),
            ("3", "Alojamiento a Agencia de Viaje No Residente"),
        ],
        help="Código de relación entre emisor y receptor que se informa en la Factura de Turismo.",
    )

    def _l10n_ar_wsct_get_address_inline(self):
        """Domicilio del receptor en una sola linea, para el campo domicilioReceptor del WSCT.

        La version original usaba ``contact_address_inline``, que no existe ni en Odoo
        estandar ni en los repos de ADHOC, con lo cual fallaba con AttributeError.
        """
        self.ensure_one()
        return " - ".join(part.strip() for part in (self.contact_address or "").splitlines() if part.strip())
