from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_ar_iva_tur_get_afip_xml(self):
        """Devuelve la tupla (xml_request, xml_response) del pedido de CAE al WSCT.

        Este modulo no depende de ningun stack de facturacion electronica en
        particular, asi que resuelve los campos segun cual este instalado:

        * Community (``l10n_ar_afipws_fe``): ``afip_xml_request`` / ``afip_xml_response``.
        * Enterprise (``l10n_ar_edi``): ``l10n_ar_afip_xml_request`` / ``l10n_ar_afip_xml_response``.

        Los modulos ``l10n_ar_afipws_wsct`` y ``l10n_ar_edi_wsct`` sobrescriben este
        metodo con la implementacion directa de cada stack.
        """
        self.ensure_one()
        if "l10n_ar_afip_xml_request" in self._fields:
            return self.l10n_ar_afip_xml_request, self.l10n_ar_afip_xml_response
        if "afip_xml_request" in self._fields:
            return self.afip_xml_request, self.afip_xml_response
        raise UserError(
            _(
                "No se encontró ningún módulo de facturación electrónica instalado. "
                "Instalá 'l10n_ar_afipws_wsct' (Odoo Community) o 'l10n_ar_edi_wsct' "
                "(Odoo Enterprise) para poder generar el exportable de IVA Turismo."
            )
        )
