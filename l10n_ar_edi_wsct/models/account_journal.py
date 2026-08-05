from odoo import _, api, models
from odoo.exceptions import UserError

# Sistema de punto de venta AFIP/ARCA y web service que agrega este modulo.
WSCT_POS_SYSTEM = "WSCTWS"
WSCT_AFIP_WS = "wsct"

# Comprobantes de turismo clase T: factura, nota de debito y nota de credito.
WSCT_DOCUMENT_CODES = ["195", "196", "197"]


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_l10n_ar_afip_ws(self):
        res = super()._get_l10n_ar_afip_ws()
        return res + [(WSCT_AFIP_WS, _("Turismo - con detalle - RG3971 (WSCT)"))]

    def _get_l10n_ar_afip_pos_types_selection(self):
        res = super()._get_l10n_ar_afip_pos_types_selection()
        res.append((WSCT_POS_SYSTEM, _("Comprobantes de Turismo - Web Service")))
        return res

    @api.depends("l10n_ar_afip_pos_system")
    def _compute_l10n_ar_afip_ws(self):
        super()._compute_l10n_ar_afip_ws()
        for rec in self:
            if rec.l10n_ar_afip_pos_system == WSCT_POS_SYSTEM:
                rec.l10n_ar_afip_ws = WSCT_AFIP_WS

    def _get_journal_letter(self, counterpart_partner=False):
        self.ensure_one()
        if self.l10n_ar_afip_ws == WSCT_AFIP_WS:
            return ["T"]
        return super()._get_journal_letter(counterpart_partner)

    @api.model
    def _get_codes_per_journal_type(self, afip_pos_system):
        if afip_pos_system != WSCT_POS_SYSTEM:
            return super()._get_codes_per_journal_type(afip_pos_system)
        return [("code", "in", WSCT_DOCUMENT_CODES)]

    @api.model
    def _wsct_convert_auth(self, auth):
        """Traduce el ticket de acceso al formato que espera el WSDL del WSCT."""
        return {
            "token": auth.get("Token"),
            "sign": auth.get("Sign"),
            "cuitRepresentada": auth.get("Cuit"),
        }

    def _l10n_ar_get_afip_last_invoice_number(self, document_type):
        """Consulta el último comprobante autorizado para el punto de venta y tipo dados."""
        if self.l10n_ar_afip_ws != WSCT_AFIP_WS:
            return super()._l10n_ar_get_afip_last_invoice_number(document_type)
        self.ensure_one()
        if self.env.registry.in_test_mode():
            return 0

        connection = self.company_id._l10n_ar_get_connection(self.l10n_ar_afip_ws)
        client, auth = connection._get_client()
        response = client.service.consultarUltimoComprobanteAutorizado(
            self._wsct_convert_auth(auth),
            consultaUltimoComprobanteAutorizadoRequest={
                "codigoTipoComprobante": document_type.code,
                "numeroPuntoVenta": self.l10n_ar_afip_pos_number,
            },
        )

        errors = self._wsct_format_errors(response)
        if errors:
            # 1502: no hay comprobantes emitidos todavia para ese tipo y punto de venta.
            if self._wsct_error_codes(response) == ["1502"]:
                return 0
            raise UserError(
                _("Recibimos este error al consultar el último número de comprobante a AFIP/ARCA:\n%s", errors)
            )
        return response.numeroComprobante or 0

    def l10n_ar_check_afip_pos_number(self):
        if self.l10n_ar_afip_ws != WSCT_AFIP_WS:
            return super().l10n_ar_check_afip_pos_number()
        self.ensure_one()
        connection = self.company_id._l10n_ar_get_connection(self.l10n_ar_afip_ws)
        client, auth = connection._get_client()
        response = client.service.consultarPuntosVenta(self._wsct_convert_auth(auth))
        raise UserError(_("Puntos de venta habilitados en AFIP/ARCA:\n%s", response))

    def l10n_ar_check_afip_doc_types(self):
        if self.l10n_ar_afip_ws != WSCT_AFIP_WS:
            return super().l10n_ar_check_afip_doc_types()
        self.ensure_one()
        connection = self.company_id._l10n_ar_get_connection(self.l10n_ar_afip_ws)
        client, auth = connection._get_client()
        response = client.service.consultarTiposComprobante(self._wsct_convert_auth(auth))
        raise UserError(
            _(
                "Tipos de comprobante autorizados en AFIP/ARCA:\n%s",
                self._format_afip_doc_types(self.l10n_ar_afip_ws, response),
            )
        )

    def _format_afip_doc_types(self, ws, response):
        if ws != WSCT_AFIP_WS:
            return super()._format_afip_doc_types(ws, response)
        documents = (response.get("arrayTiposComprobante") or {}).get("codigoDescripcion") or []
        return "".join(" - [%s] %s\n" % (doc["codigo"], doc["descripcion"]) for doc in documents)

    @api.model
    def _wsct_error_codes(self, response):
        errors = getattr(response, "arrayErrores", None)
        if not errors:
            return []
        return [str(err.codigo) for err in errors.codigoDescripcion]

    @api.model
    def _wsct_format_errors(self, response):
        errors = getattr(response, "arrayErrores", None)
        if not errors:
            return ""
        return "".join("\n* Código %s: %s" % (err.codigo, err.descripcion) for err in errors.codigoDescripcion)
