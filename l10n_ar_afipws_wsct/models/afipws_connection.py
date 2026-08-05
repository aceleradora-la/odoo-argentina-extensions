from odoo import _, fields, models
from odoo.exceptions import UserError

from .account_journal import WSCT_AFIP_WS

WSCT_WS_URLS = {
    "production": "https://serviciosjava.afip.gob.ar/wsct/CTService?wsdl",
    "testing": "https://fwshomo.afip.gov.ar/wsct/CTService?wsdl",
}


class AfipwsConnection(models.Model):
    _inherit = "afipws.connection"

    afip_ws = fields.Selection(
        selection_add=[
            (WSCT_AFIP_WS, "Comprobantes de Turismo - Web Service"),
        ],
        ondelete={
            WSCT_AFIP_WS: "set default",
        },
    )

    def _get_ws(self, afip_ws):
        if afip_ws != WSCT_AFIP_WS:
            return super()._get_ws(afip_ws)
        try:
            from pyafipws.wsct import WSCT
        except ImportError as error:
            raise UserError(
                _("Para usar el web service WSCT hay que instalar la librería pyafipws en el servidor.")
            ) from error
        return WSCT()

    def get_afip_ws_url(self, afip_ws, environment_type):
        if afip_ws != WSCT_AFIP_WS:
            return super().get_afip_ws_url(afip_ws, environment_type)
        return WSCT_WS_URLS["production" if environment_type == "production" else "testing"]
