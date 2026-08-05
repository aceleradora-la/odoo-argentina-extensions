from odoo import models


class AccountJournalWs(models.Model):
    _inherit = "account.journal"

    def wsct_pyafipws_cuit_document_classes(self, ws):
        # WSCT devuelve "codigo:descripcion" y el resto del stack espera "codigo,descripcion".
        doc_types = ws.ConsultarTiposComprobante()
        return [s.replace(":", ",") for s in doc_types]

    def wsct_pyafipws_point_of_sales(self, ws):
        return ws.ConsultarPuntosVenta()

    def wsct_get_pyafipws_last_invoice(self, l10n_ar_afip_pos_number, document_type, ws):
        return ws.ConsultarUltimoComprobanteAutorizado(document_type.code, l10n_ar_afip_pos_number)
