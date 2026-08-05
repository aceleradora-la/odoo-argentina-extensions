from datetime import datetime

from odoo import _, models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def wsct_request_autorization(self, ws):
        ws.CAESolicitar()
        if ws.CAE:
            # WSCT devuelve el vencimiento como AAAA/MM/DD y el resto del stack
            # (y el reporte de IVA Turismo) espera AAAAMMDD.
            parsed_date = datetime.strptime(ws.Vencimiento, "%Y/%m/%d")
            ws.Vencimiento = parsed_date.strftime("%Y%m%d")

    def wsct_map_invoice_info(self):
        invoice_info = self.base_map_invoice_info()

        amounts = invoice_info["amounts"]
        commercial_partner = invoice_info["commercial_partner"]
        country = invoice_info["country"]

        if not country:
            raise UserError(
                _("Para el web service WSCT el contacto %s debe tener un país configurado.", commercial_partner.name)
            )
        if not commercial_partner.codigo_relacion:
            raise UserError(
                _(
                    "Para emitir una Factura de Turismo hay que definir el Código de Relación "
                    "en el contacto %s.",
                    commercial_partner.name,
                )
            )

        invoice_info["lines"] = self.wsct_invoice_map_info_lines()

        invoice_info["imp_reintegro"] = "%.2f" % -amounts["vat_amount"]
        invoice_info["imp_subtotal"] = "%.2f" % self.amount_untaxed
        invoice_info["cod_pais"] = country.l10n_ar_afip_code
        invoice_info["id_impositivo"] = invoice_info["condicion_iva_receptor_id"]
        invoice_info["fecha_cbte"] = invoice_info["fecha_cbte"].strftime("%Y-%m-%d")
        invoice_info["domicilio"] = commercial_partner._l10n_ar_wsct_get_address_inline()
        invoice_info["cod_relacion"] = commercial_partner.codigo_relacion
        invoice_info["observaciones"] = False

        if invoice_info["CbteAsoc"]:
            invoice_info["cancela_misma_moneda_ext"] = None

        if country.code != "AR":
            if commercial_partner.is_company:
                invoice_info["nro_doc"] = country.l10n_ar_legal_entity_vat
            else:
                invoice_info["nro_doc"] = country.l10n_ar_natural_vat
            if not invoice_info["nro_doc"]:
                raise UserError(
                    _(
                        "El país %s no tiene configurado el CUIT genérico que AFIP/ARCA pide "
                        "para receptores del exterior.",
                        country.name,
                    )
                )

        return invoice_info

    def wsct_invoice_add_info(self, ws, invoice_info):
        for line in invoice_info["lines"]:
            ws.AgregarItem(
                line["item_type_t"],
                line["cod_tur"],
                line["codigo"],
                line["ds"],
                line["iva_id"],
                line["imp_iva"],
                line["importe"],
            )

        if invoice_info["CbteAsoc"]:
            doc_number_parts = self._l10n_ar_get_document_number_parts(
                invoice_info["CbteAsoc"].l10n_latam_document_number,
                invoice_info["CbteAsoc"].l10n_latam_document_type_id.code,
            )
            ws.AgregarCmpAsoc(
                invoice_info["CbteAsoc"].l10n_latam_document_type_id.code,
                doc_number_parts["point_of_sale"],
                doc_number_parts["invoice_number"],
                self.company_id.vat,
            )

        self.pyafipws_add_tax(ws)

    def wsct_pyafipws_create_invoice(self, ws, invoice_info):
        ws.CrearFactura(
            invoice_info["tipo_doc"],
            invoice_info["nro_doc"],
            invoice_info["doc_afip_code"],
            invoice_info["pos_number"],
            invoice_info["cbte_nro"],
            invoice_info["imp_total"],
            invoice_info["imp_tot_conc"],
            invoice_info["imp_neto"],
            invoice_info["imp_subtotal"],
            invoice_info["imp_trib"],
            invoice_info["imp_op_ex"],
            invoice_info["imp_reintegro"],
            invoice_info["fecha_cbte"],
            invoice_info["id_impositivo"],
            invoice_info["cod_pais"],
            invoice_info["domicilio"],
            invoice_info["cod_relacion"],
            invoice_info["moneda_id"],
            invoice_info["moneda_ctz"],
            invoice_info["observaciones"],
        )

    def wsct_invoice_map_info_lines(self):
        lines = []
        for line in self.invoice_line_ids.filtered(lambda x: x.display_type == "product"):
            line_temp = {}
            line_temp["codigo"] = line.product_id.default_code
            # unidad de referencia del producto si se comercializa
            # en una unidad distinta a la de consumo
            # uom is not mandatory, if no UOM we use "unit"
            if not line.product_uom_id:
                line_temp["umed"] = "7"
            elif not line.product_uom_id.l10n_ar_afip_code:
                raise UserError(_("La unidad de medida %s no tiene código AFIP.", line.product_uom_id.name))
            else:
                line_temp["umed"] = line.product_uom_id.l10n_ar_afip_code
            line_temp["ds"] = line.name
            line_temp["qty"] = line.quantity
            line_temp["precio"] = line.price_unit

            # El IVA que se informa por item es el IVA comun: el IVA Reintegro Turismo
            # va aparte, en el campo importeReintegro de la cabecera.
            tax_lines = line.tax_ids.filtered(
                lambda x: not x.l10n_ar_afipws_wsct_is_tourism_vat and x.tax_group_id.l10n_ar_vat_afip_code
            )
            line_temp["iva_id"] = tax_lines.tax_group_id.l10n_ar_vat_afip_code
            vat_taxes_amounts = tax_lines.compute_all(
                line.price_unit,
                self.currency_id,
                line.quantity,
                product=line.product_id,
                partner=self.partner_id,
            )

            vat_amount = sum(x["amount"] for x in vat_taxes_amounts["taxes"])

            line_temp["imp_iva"] = "%.2f" % vat_amount
            line_temp["importe"] = "%.2f" % (line.price_total + vat_amount)

            # Bonificacion: teorico menos importe, ambos netos de impuestos.
            # Antes se restaba line_temp["importe"], que todavia no estaba asignado
            # en este punto y ademas es un string, con lo cual cualquier linea con
            # descuento cortaba la emision con KeyError.
            line_temp["bonif"] = (
                "%.2f" % (line.price_unit * line.quantity - line.price_subtotal) if line.discount else None
            )

            # Factura T
            line_temp["item_type_t"] = line.product_id.categ_id.item_type_t
            line_temp["cod_tur"] = line.product_id.categ_id.cod_tur

            lines.append(line_temp)

        return lines
