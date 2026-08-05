import base64
import datetime
import io
import logging
import xml.etree.ElementTree as ET

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.l10n_ar_afip_iva_tur.afip_utils import (
    format_fixed_decimal,
    parse_afip_response,
    parse_autorizar_comprobante,
)

_logger = logging.getLogger(__name__)

# Codigo de regimen AFIP/ARCA del Régimen de Alojamiento de Turistas Extranjeros.
IVA_TUR_REGIME_CODE = "8089"

# Comprobantes clase T alcanzados por el regimen.
IVA_TUR_DOCUMENT_CODES = ["195", "196", "197", "362"]

# El exportable es de ancho fijo, asi que se escribe en una codificacion de un byte
# por caracter. Con UTF-8 cualquier acento corria las columnas y AFIP rechazaba el archivo.
IVA_TUR_ENCODING = "latin-1"

# Forma de pago que se informa cuando el comprobante no tiene pagos conciliados.
# El código original escribía "1" con el comentario "transferencia", pero en la
# selección de account.journal el "1" es tarjeta de crédito y el "3" es
# transferencia bancaria. Se usa el valor consistente con esas etiquetas.
IVA_TUR_DEFAULT_PAYMENT_TYPE = "3"


def _text_field(value, width):
    """Campo alfanumerico de ancho fijo, alineado a izquierda y truncado si se pasa."""
    return str(value or "").strip()[:width].ljust(width)


def _num_field(value, width, label):
    """Campo numerico de ancho fijo, alineado a derecha con ceros."""
    text = str(value or 0)
    if len(text) > width:
        raise UserError(
            _(
                "El valor '%(value)s' del campo %(label)s no entra en los %(width)s caracteres "
                "que exige el diseño de registro de AFIP/ARCA.",
                value=text,
                label=label,
                width=width,
            )
        )
    return text.zfill(width)


def _amount_field(amount, width, label):
    """Importe en centavos, sin coma decimal, alineado a derecha con ceros."""
    return _num_field(int(round((amount or 0.0) * 100)), width, label)


class AfipIvaTurReport(models.Model):
    _name = "afip.iva.tur.report"
    _description = "AFIP IVA Turismo Report"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "date_from desc"

    name = fields.Char(
        string="Nombre del Reporte",
        compute="_compute_name",
        store=True,
        help="Nombre generado automáticamente para el reporte (ej. IVA TUR 2025/06)",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )

    date_from = fields.Date(
        string="Fecha Desde",
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )

    date_to = fields.Date(
        string="Fecha Hasta",
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )

    date_payment = fields.Date(
        string="Fecha de Pago (Exportable)",
        required=True,
        default=lambda self: fields.Date.context_today(self) + datetime.timedelta(days=1),
        help="Fecha que se utilizará como 'Fecha de Pago' en el archivo exportable de AFIP IVA Turismo.",
    )

    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("generated", "Generado"),
            ("presented", "Presentado"),
        ],
        string="Estado",
        default="draft",
        readonly=True,
        copy=False,
        tracking=True,
        help="Estado del reporte: Borrador (se pueden editar los datos), Generado (listo para "
        "presentar), Presentado (reporte enviado a AFIP).",
    )

    invoice_ids = fields.Many2many(
        "account.move",
        string="Comprobantes Incluidos",
        domain="[('move_type', 'in', ('out_invoice', 'out_refund')), ('state', '=', 'posted'),"
        " ('company_id', '=', company_id)]",
        help="Listado de comprobantes Tipo T incluidos en este reporte. Se completará "
        "automáticamente al actualizar los comprobantes.",
    )

    invoice_count = fields.Integer(
        string="Cantidad de Comprobantes",
        compute="_compute_invoice_count",
    )

    exported_file = fields.Binary(
        string="Archivo TXT Exportado",
        readonly=True,
        attachment=True,
        help="Archivo TXT generado para la presentación en AFIP.",
    )

    exported_filename = fields.Char(
        string="Nombre del Archivo",
        readonly=True,
    )

    presentation_date = fields.Date(
        string="Fecha de Presentación",
        readonly=True,
        help="Fecha en que el reporte fue marcado como presentado.",
    )

    sequence = fields.Integer(
        string="Número de Remesa",
        readonly=True,
        default=0,
        help="Número de intentos para presentar el reporte.",
    )

    @api.depends("date_from")
    def _compute_name(self):
        for rec in self:
            if rec.date_from:
                rec.name = _("IVA TUR %(year)s/%(month)s", year=rec.date_from.year, month="%02d" % rec.date_from.month)
            else:
                rec.name = False

    @api.depends("invoice_ids")
    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)

    @api.constrains("date_from", "date_to")
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError(_("La 'Fecha Desde' no puede ser posterior a la 'Fecha Hasta'."))

    def _get_sanitized_cuit(self):
        """CUIT del informante, sin guiones ni puntos y validado a 11 dígitos."""
        self.ensure_one()
        cuit = "".join(char for char in (self.company_id.vat or "") if char.isdigit())
        if len(cuit) != 11:
            raise UserError(
                _(
                    "La compañía %(company)s no tiene un CUIT válido de 11 dígitos configurado, "
                    "que es obligatorio para generar el exportable de IVA Turismo.",
                    company=self.company_id.display_name,
                )
            )
        return cuit

    def action_clear_invoices(self):
        """Elimina todos los comprobantes de la lista si el reporte está en borrador."""
        self.ensure_one()
        if self.state != "draft":
            raise UserError(
                _("Solo se pueden limpiar los comprobantes de un reporte en borrador. Volvé el reporte a borrador.")
            )
        self.invoice_ids = [fields.Command.clear()]
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Comprobantes Borrados"),
                "message": _("Todos los comprobantes han sido eliminados del reporte borrador."),
                "type": "info",
                "sticky": False,
            },
        }

    def action_update_invoices(self):
        """Actualiza la lista de comprobantes del reporte con los del período."""
        self.ensure_one()
        if self.state == "presented":
            raise UserError(_("No puede modificar un reporte ya presentado. Cree uno nuevo si necesita corregir."))

        doc_type_ids = (
            self.env["l10n_latam.document.type"]
            .search(
                [
                    ("code", "in", IVA_TUR_DOCUMENT_CODES),
                    ("l10n_ar_letter", "=", "T"),
                ]
            )
            .ids
        )

        if not doc_type_ids:
            raise UserError(
                _(
                    "No se encontraron tipos de documento AFIP/ARCA configurados para IVA Turismo "
                    "(códigos %(codes)s, letra 'T').",
                    codes=", ".join(IVA_TUR_DOCUMENT_CODES),
                )
            )

        invoices_found_in_period = self.env["account.move"].search(
            [
                ("company_id", "=", self.company_id.id),
                ("move_type", "in", ("out_invoice", "out_refund")),
                ("state", "=", "posted"),
                ("invoice_date", ">=", self.date_from),
                ("invoice_date", "<=", self.date_to),
                ("l10n_latam_document_type_id", "in", doc_type_ids),
            ]
        )

        # Un comprobante no puede informarse en dos reportes distintos.
        conflicting_reports = self.env["afip.iva.tur.report"].search(
            [
                ("id", "!=", self.id),
                ("invoice_ids", "in", invoices_found_in_period.ids),
            ]
        )
        conflicting_invoices = invoices_found_in_period & conflicting_reports.mapped("invoice_ids")

        if conflicting_invoices:
            details = []
            for invoice in conflicting_invoices:
                reports = conflicting_reports.filtered(lambda r, inv=invoice: inv in r.invoice_ids)
                details.append("%s → %s" % (invoice.display_name, ", ".join(reports.mapped("name"))))
            raise UserError(
                _(
                    "No se pueden agregar los siguientes comprobantes porque ya están incluidos "
                    "en otros reportes de IVA Turismo:\n\n%(details)s",
                    details="\n".join(details),
                )
            )

        if not invoices_found_in_period:
            raise UserError(_("No se encontraron comprobantes Tipo T para el período seleccionado."))

        self.invoice_ids = [fields.Command.set(invoices_found_in_period.ids)]
        self.state = "generated"
        return True

    def _get_export_filename(self):
        """Formato AFIP: F + COD_REGIMEN + CUIT + PERIODO(AAAAMM + 00) + NRO_REMESA + .TXT"""
        self.ensure_one()
        periodo = fields.Date.context_today(self).strftime("%Y%m")
        return "F%s.%s.%s00.%s.TXT" % (
            IVA_TUR_REGIME_CODE,
            self._get_sanitized_cuit(),
            periodo,
            str(self.sequence).zfill(4),
        )

    def _get_invoice_afip_data(self, invoice):
        """Parsea el request/response del WSCT guardado en el comprobante."""
        xml_request, xml_response = invoice._l10n_ar_iva_tur_get_afip_xml()
        try:
            comprobante = parse_autorizar_comprobante(xml_request).comprobante
            response = parse_afip_response(xml_response)
        except (ValueError, ET.ParseError) as error:
            raise UserError(
                _(
                    "No se pudo leer el XML de AFIP/ARCA del comprobante %(invoice)s: %(error)s",
                    invoice=invoice.display_name,
                    error=error,
                )
            ) from error
        return comprobante, response

    def _generate_file_content(self):
        """Arma el contenido del exportable según el diseño de registro del régimen 8089."""
        self.ensure_one()
        output = io.StringIO()
        cuit_informante = self._get_sanitized_cuit()

        # --- REGISTRO TIPO 1: CABECERA DEL ARCHIVO ---
        output.write(
            "01"
            + cuit_informante
            + fields.Date.context_today(self).strftime("%Y%m")
            + str(self.sequence).zfill(4)
            + "0103"
            + "858"
            + IVA_TUR_REGIME_CODE
            + "00100"
            + ("0" if self.invoice_ids else "1")
            + "\r\n"
        )

        for inv in self.invoice_ids:
            comprobante, response = self._get_invoice_afip_data(inv)

            # --- REGISTRO TIPO 2: COMPROBANTE DE VENTA ---
            # Antes se usaba codigoTipoDocumento (tipo de documento del turista) como
            # tipo de comprobante, con lo cual el registro 02 salía con el dato equivocado.
            tipo_comprobante_afip = _num_field(comprobante.codigoTipoComprobante, 3, "tipo de comprobante")
            punto_venta = _num_field(comprobante.numeroPuntoVenta, 5, "punto de venta")
            numero_comprobante = _num_field(comprobante.numeroComprobante, 8, "número de comprobante")
            fecha_emision = inv.invoice_date.strftime("%Y%m%d") if inv.invoice_date else "00000000"
            tipo_doc_turista = _num_field(comprobante.codigoTipoDocumento, 2, "tipo de documento del turista")
            nro_doc_turista = _text_field(comprobante.numeroDocumento, 20)
            codigo_pais = _num_field(comprobante.codigoPais, 4, "código de país")
            id_impositivo = _num_field(comprobante.idImpositivo, 2, "ID impositivo")
            codigo_relacion = _num_field(comprobante.codigoRelacionEmisorReceptor, 2, "código de relación")
            importe_gravado = _amount_field(comprobante.importeGravado, 15, "importe gravado")
            importe_no_gravado = _amount_field(comprobante.importeNoGravado, 15, "importe no gravado")
            importe_exento = _amount_field(comprobante.importeExento, 15, "importe exento")
            importe_reintegro = _amount_field(comprobante.importeReintegro, 15, "importe de reintegro")
            importe_total = _amount_field(comprobante.importeTotal, 15, "importe total")
            codigo_moneda = _text_field(comprobante.codigoMoneda, 3)
            cotizacion_moneda = format_fixed_decimal(comprobante.cotizacionMoneda)
            tipo_auth = _text_field(response.tipo_autorizacion, 3)
            codigo_auth = _num_field(response.codigo_autorizacion, 14, "código de autorización")
            codigo_control_fiscal = " " * 6
            serie_control_fiscal = "0" * 10

            output.write(
                "02"
                + tipo_comprobante_afip
                + punto_venta
                + numero_comprobante
                + fecha_emision
                + tipo_doc_turista
                + nro_doc_turista
                + codigo_pais
                + id_impositivo
                + codigo_relacion
                + importe_gravado
                + importe_no_gravado
                + importe_exento
                + importe_reintegro
                + codigo_moneda
                + cotizacion_moneda
                + tipo_auth
                + codigo_auth
                + codigo_control_fiscal
                + serie_control_fiscal
                + importe_total
                + "\r\n"
            )

            # --- REGISTRO TIPO 3: TOTALES DEL COMPROBANTE DE VENTA (Base IVA) ---
            for iva in comprobante.subtotales_iva:
                output.write(
                    "03"
                    + ("11" if iva.codigo == "5" else "10")
                    + "0" * 15
                    + _amount_field(iva.importe, 15, "importe de IVA")
                    + "\r\n"
                )

            # --- REGISTRO TIPO 4: DATOS DEL TURISTA EXTRANJERO ---
            output.write(
                "04"
                + tipo_doc_turista
                + nro_doc_turista
                + codigo_pais
                + _text_field(inv.partner_id.name, 50)
                + codigo_pais
                + codigo_pais
                + "\r\n"
            )

            # --- REGISTRO TIPO 5: IMPUESTOS Y PERCEPCIONES DEL COMPROBANTE ---
            output.write(
                "05"
                + cuit_informante
                + tipo_comprobante_afip
                + punto_venta
                + numero_comprobante
                + tipo_auth
                + codigo_auth
                + fecha_emision
                + codigo_control_fiscal
                + serie_control_fiscal
                + importe_reintegro
                + "\r\n"
            )

            # --- REGISTRO TIPO 6: COMPROBANTES ASOCIADOS ---
            for asociado in comprobante.comprobantes_asociados:
                output.write(
                    "06"
                    + _num_field(asociado.codigoTipoComprobante, 3, "tipo de comprobante asociado")
                    + _num_field(asociado.numeroPuntoVenta, 5, "punto de venta asociado")
                    + _num_field(asociado.numeroComprobante, 8, "número de comprobante asociado")
                    + "\r\n"
                )

            # --- REGISTRO TIPO 7: CONCEPTOS DE DETALLE DEL COMPROBANTE ---
            for item in comprobante.items:
                output.write(
                    "07"
                    + _num_field(item.tipo, 2, "tipo de item")
                    + _num_field(item.codigoTurismo, 4, "código de turismo")
                    + _text_field(item.codigo, 50)
                    + " " * 11  # CUIT del hotel
                    + " " * 8  # fecha de ingreso
                    + " " * 4  # unidad
                    + " " * 4  # tipo de unidad
                    + " " * 2  # cantidad de personas
                    + _text_field(item.descripcion, 200)
                    + " " * 5  # cantidad de noches
                    + " " * 18  # precio unitario
                    + ("11" if item.codigoAlicuotaIVA == "5" else "10")
                    + _amount_field(item.importeIVA, 15, "importe de IVA del item")
                    + _amount_field(item.importeItem, 15, "importe del item")
                    + "\r\n"
                )

            # --- REGISTRO TIPO 8: MEDIOS DE PAGO ---
            codigo_swift = " " * 11
            tipo_cuenta = " " * 2
            numero_tarjeta = " " * 6
            numero_cuenta = " " * 20
            payments = inv._get_reconciled_payments()

            if not payments:
                # Sin pagos conciliados: se informa una transferencia por el total del comprobante.
                output.write(
                    "08"
                    + IVA_TUR_DEFAULT_PAYMENT_TYPE
                    + codigo_swift
                    + tipo_cuenta
                    + numero_tarjeta
                    + numero_cuenta
                    + _amount_field(inv.amount_total, 15, "importe del medio de pago")
                    + "\r\n"
                )
            else:
                for pay in payments:
                    output.write(
                        "08"
                        + (pay.journal_id.l10n_ar_afip_wsct_payment_type or IVA_TUR_DEFAULT_PAYMENT_TYPE)
                        + codigo_swift
                        + tipo_cuenta
                        + numero_tarjeta
                        + numero_cuenta
                        + _amount_field(pay.amount, 15, "importe del medio de pago")
                        + "\r\n"
                    )

        return output.getvalue()

    def action_generate_file(self):
        """Genera el archivo TXT a partir de los comprobantes ya cargados."""
        self.ensure_one()
        if self.state == "presented":
            raise UserError(_("No puede regenerar el archivo de un reporte ya presentado."))
        if not self.invoice_ids:
            raise UserError(_("No hay comprobantes asociados a este reporte para generar el archivo."))

        content = self._generate_file_content()

        self.write(
            {
                "exported_file": base64.b64encode(content.encode(IVA_TUR_ENCODING, errors="replace")),
                "exported_filename": self._get_export_filename(),
                "sequence": self.sequence + 1,
                "state": "generated",
            }
        )
        self.message_post(body=_("Se generó el archivo %s.", self.exported_filename))
        return True

    def action_mark_as_presented(self):
        """Marca el reporte como presentado."""
        self.ensure_one()
        if self.state == "draft":
            raise UserError(_("No puede marcar un borrador como presentado. Genere el archivo primero."))
        self.write(
            {
                "state": "presented",
                "presentation_date": fields.Date.context_today(self),
            }
        )
        return True

    def action_set_to_draft(self):
        """Vuelve el reporte a estado borrador."""
        self.ensure_one()
        if self.state == "presented":
            raise UserError(_("No puede volver un reporte presentado a borrador. Cree uno nuevo si necesita corregir."))
        self.write(
            {
                "state": "draft",
                "exported_file": False,
                "exported_filename": False,
                "presentation_date": False,
                "invoice_ids": [fields.Command.clear()],
            }
        )
        return True
