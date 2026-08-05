from odoo import models

from odoo.addons.l10n_ar_afipws_wsct.afip_utils import get_invoice_number_from_response

from .account_journal import WSCT_AFIP_WS


class AccountMove(models.Model):
    _inherit = "account.move"

    def _set_next_sequence(self):
        """A diferencia de los demas web services, WSCT asigna el numero de comprobante.

        Por eso, en vez de tomar el proximo numero de la secuencia de Odoo, se usa el
        numeroComprobante que devolvio AFIP.
        """
        if self.journal_id.afip_ws != WSCT_AFIP_WS:
            return super()._set_next_sequence()

        if self.afip_auth_code and self.afip_xml_response:
            invoice_number = get_invoice_number_from_response(self.afip_xml_response)
            if invoice_number:
                last_sequence = self._get_formatted_sequence(invoice_number)
                sequence_format, format_values = self._get_sequence_format_param(last_sequence)
                format_values["year"] = self[self._sequence_date_field].year % (10 ** format_values["year_length"])
                format_values["month"] = self[self._sequence_date_field].month
                format_values["seq"] = invoice_number

                self[self._sequence_field] = sequence_format.format(**format_values)
                return None
        return super()._set_next_sequence()

    def _l10n_ar_iva_tur_get_afip_xml(self):
        """Devuelve (request, response) del WSCT tal como los guarda el stack Community."""
        self.ensure_one()
        return self.afip_xml_request, self.afip_xml_response
