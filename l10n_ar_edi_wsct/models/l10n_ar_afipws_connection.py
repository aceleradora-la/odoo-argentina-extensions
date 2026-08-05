from odoo import api, models

from .account_journal import WSCT_AFIP_WS

WSCT_WS_URLS = {
    "production": "https://serviciosjava.afip.gob.ar/wsct/CTService?wsdl",
    "testing": "https://fwshomo.afip.gov.ar/wsct/CTService?wsdl",
}


class L10nArAfipwsConnection(models.Model):
    _inherit = "l10n_ar.afipws.connection"

    @api.model
    def _l10n_ar_get_afip_ws_url(self, afip_ws, environment_type):
        if afip_ws != WSCT_AFIP_WS:
            return super()._l10n_ar_get_afip_ws_url(afip_ws, environment_type)
        return WSCT_WS_URLS.get(environment_type)
