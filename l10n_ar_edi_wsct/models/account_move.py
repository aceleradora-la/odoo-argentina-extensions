from markupsafe import Markup

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import plaintext2html
from odoo.tools.float_utils import float_repr

from .account_journal import WSCT_AFIP_WS

# El WSCT usa fechas ISO, a diferencia de wsfe/wsfex/wsbfe que usan AAAAMMDD.
WSCT_DATE_FORMAT = "%Y-%m-%d"


class AccountMove(models.Model):
    _inherit = "account.move"

    # -------------------------------------------------------------------------
    # Solicitud de CAE
    # -------------------------------------------------------------------------

    def _l10n_ar_do_afip_ws_request_cae(self, client, auth, transport):
        """Pide el CAE al WSCT para los comprobantes de turismo y delega el resto."""
        non_wsct = self.filtered(lambda x: x.journal_id.l10n_ar_afip_ws != WSCT_AFIP_WS)
        if non_wsct:
            return_info = super(AccountMove, non_wsct)._l10n_ar_do_afip_ws_request_cae(client, auth, transport)
            if return_info:
                return return_info

        wsct_moves = self.filtered(
            lambda x: x.journal_id.l10n_ar_afip_ws == WSCT_AFIP_WS and not x.l10n_ar_afip_auth_code
        )
        for inv in wsct_moves:
            errors = obs = events = ""
            return_codes = []
            values = {}

            inv.l10n_ar_check_rate()

            request_data = inv._wsct_get_cae_request()
            wsct_auth = inv.journal_id._wsct_convert_auth(auth)
            response = client.service.autorizarComprobante(wsct_auth, request_data)

            if response and response.resultado in ("A", "O") and response.comprobanteResponse:
                result = response.comprobanteResponse
                values = {
                    "l10n_ar_afip_auth_mode": "CAE",
                    "l10n_ar_afip_auth_code": result.CAE and str(result.CAE) or "",
                    "l10n_ar_afip_auth_code_due": result.fechaVencimientoCAE,
                    "l10n_ar_afip_result": response.resultado,
                }

            if response.arrayObservaciones:
                obs = "".join(
                    _("\n* Código %s: %s", ob.codigo, ob.descripcion)
                    for ob in response.arrayObservaciones.codigoDescripcion
                )
                return_codes += [str(ob.codigo) for ob in response.arrayObservaciones.codigoDescripcion]
            if response.arrayErrores:
                errors = "".join(
                    _("\n* Código %s: %s", err.codigo, err.descripcion)
                    for err in response.arrayErrores.codigoDescripcion
                )
                return_codes += [str(err.codigo) for err in response.arrayErrores.codigoDescripcion]
            if response.evento:
                events = _("\n* Código %s: %s", response.evento.codigo, response.evento.descripcion)
                return_codes += [str(response.evento.codigo)]

            return_info = inv._prepare_return_msg(WSCT_AFIP_WS, errors, obs, events, return_codes)
            xml_response, xml_request = transport.xml_response, transport.xml_request

            if values.get("l10n_ar_afip_result") not in ("A", "O"):
                if not self.env.context.get("l10n_ar_invoice_skip_commit"):
                    self.env.cr.rollback()
                if inv.exists():
                    inv.sudo().write(
                        {
                            "l10n_ar_afip_xml_request": xml_request,
                            "l10n_ar_afip_xml_response": xml_response,
                        }
                    )
                if not self.env.context.get("l10n_ar_invoice_skip_commit"):
                    self.env.cr.commit()  # pylint: disable=invalid-commit
                return return_info

            values.update(
                l10n_ar_afip_xml_request=xml_request,
                l10n_ar_afip_xml_response=xml_response,
            )
            inv.sudo().write(values)
            if return_info:
                inv.message_post(
                    body=Markup("<p><b>%s%s</b></p>") % (_("AFIP Messages"), plaintext2html(return_info, "em"))
                )

    # -------------------------------------------------------------------------
    # Armado del comprobanteRequest
    # -------------------------------------------------------------------------

    def _wsct_get_cae_request(self):
        """Arma el comprobanteRequest del WSCT."""
        self.ensure_one()
        partner = self.commercial_partner_id
        country = partner.country_id

        if not country:
            raise UserError(_("Para el web service WSCT el contacto %s debe tener un país configurado.", partner.name))
        if not partner.codigo_relacion:
            raise UserError(
                _("Para emitir una Factura de Turismo hay que definir el Código de Relación en el contacto %s.", partner.name)
            )

        base_lines, _tax_lines = self._get_rounded_base_and_tax_lines()
        amounts = self._l10n_ar_get_amounts(base_lines=base_lines)
        partner_id_code = self._get_partner_code_id(partner)

        invoice_number = self._l10n_ar_get_document_number_parts(
            self.l10n_latam_document_number,
            self.l10n_latam_document_type_id.code,
        )["invoice_number"]

        res = {
            "codigoTipoComprobante": int(self.l10n_latam_document_type_id.code),
            "numeroPuntoVenta": int(self.journal_id.l10n_ar_afip_pos_number),
            "numeroComprobante": invoice_number,
            "fechaEmision": self.invoice_date.strftime(WSCT_DATE_FORMAT),
            "codigoTipoDocumento": int(partner_id_code) if partner_id_code else 99,
            "numeroDocumento": self._wsct_get_receiver_document_number(partner, country, partner_id_code),
            "idImpositivo": self.partner_id.l10n_ar_afip_responsibility_type_id.code,
            "codigoPais": country.l10n_ar_afip_code,
            "domicilioReceptor": partner._l10n_ar_wsct_get_address_inline(),
            "codigoRelacionEmisorReceptor": partner.codigo_relacion,
            "importeGravado": float_repr(amounts["vat_taxable_amount"], 2),
            "importeNoGravado": float_repr(amounts["vat_untaxed_base_amount"], 2),
            "importeExento": float_repr(amounts["vat_exempt_base_amount"], 2),
            "importeSubtotal": float_repr(self.amount_untaxed, 2),
            # El IVA Reintegro Turismo se informa aparte del IVA comun y con signo invertido.
            "importeReintegro": float_repr(-amounts["vat_amount"], 2),
            "importeOtrosTributos": float_repr(amounts["not_vat_taxes_amount"], 2),
            "importeTotal": float_repr(self.amount_total, 2),
            "codigoMoneda": self.currency_id.l10n_ar_afip_code,
            "cotizacionMoneda": float_repr(1 / self.invoice_currency_rate, 6),
            "arrayItems": self._wsct_get_items(),
            "arraySubtotalesIVA": self._wsct_get_vat_subtotals(base_lines),
            "observaciones": None,
        }

        related_invoice = self._wsct_get_related_invoice_data()
        if related_invoice:
            res["arrayComprobantesAsociados"] = [related_invoice]

        tributes = self._get_tributes(base_lines=base_lines)
        if tributes:
            res["arrayOtrosTributos"] = tributes

        return res

    def _wsct_get_receiver_document_number(self, partner, country, partner_id_code):
        """Número de documento del receptor.

        Para receptores del exterior AFIP/ARCA pide el CUIT genérico del país, distinto
        según se trate de una persona jurídica o de una persona física.
        """
        self.ensure_one()
        if country.code == "AR":
            return partner_id_code and partner._get_id_number_sanitize() or 0

        number = country.l10n_ar_legal_entity_vat if partner.is_company else country.l10n_ar_natural_vat
        if not number:
            raise UserError(
                _(
                    "El país %s no tiene configurado el CUIT genérico que AFIP/ARCA pide para "
                    "receptores del exterior.",
                    country.name,
                )
            )
        return number

    def _wsct_get_items(self):
        """Detalle de items del comprobante de turismo.

        Se calcula igual que en el stack Community (``l10n_ar_afipws_wsct``) para que
        ambas ediciones generen exactamente el mismo exportable de IVA Turismo.
        """
        self.ensure_one()
        items = []
        for line in self.invoice_line_ids.filtered(lambda x: x.display_type == "product"):
            category = line.product_id.categ_id
            vat_taxes = line.tax_ids.filtered(
                lambda x: not x.l10n_ar_afipws_wsct_is_tourism_vat and x.tax_group_id.l10n_ar_vat_afip_code
            )
            computed = vat_taxes.compute_all(
                line.price_unit,
                self.currency_id,
                line.quantity,
                product=line.product_id,
                partner=self.partner_id,
            )
            vat_amount = sum(tax["amount"] for tax in computed["taxes"])

            items.append(
                {
                    "tipo": category.item_type_t,
                    "codigoTurismo": category.cod_tur,
                    "codigo": line.product_id.default_code or None,
                    "descripcion": line.name,
                    "codigoAlicuotaIVA": vat_taxes.tax_group_id.l10n_ar_vat_afip_code,
                    "importeIVA": float_repr(vat_amount, 2),
                    "importeItem": float_repr(line.price_total + vat_amount, 2),
                }
            )
        return items

    def _wsct_get_vat_subtotals(self, base_lines):
        self.ensure_one()
        return [
            {"codigo": item["Id"], "importe": float_repr(item["Importe"], 2)}
            for item in self._get_vat(base_lines=base_lines)
        ]

    def _wsct_get_related_invoice_data(self):
        self.ensure_one()
        related_inv = self._found_related_invoice()
        if not related_inv:
            return {}
        return {
            "codigoTipoComprobante": related_inv.l10n_latam_document_type_id.code,
            "numeroPuntoVenta": related_inv.journal_id.l10n_ar_afip_pos_number,
            "numeroComprobante": self._l10n_ar_get_document_number_parts(
                related_inv.l10n_latam_document_number,
                related_inv.l10n_latam_document_type_id.code,
            )["invoice_number"],
            "cuit": self.company_id.vat,
        }

    # -------------------------------------------------------------------------
    # Integración con el exportable de IVA Turismo
    # -------------------------------------------------------------------------

    def _l10n_ar_iva_tur_get_afip_xml(self):
        """Devuelve (request, response) del WSCT tal como los guarda el stack Enterprise."""
        self.ensure_one()
        return self.l10n_ar_afip_xml_request, self.l10n_ar_afip_xml_response
