# l10n_ar_afip_iva_tur/models/afip_iva_tur_report.py

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
import datetime
import io
import base64
import logging
from odoo.addons.l10n_ar_afip_iva_tur.afip_utils import parse_autorizar_comprobante, format_fixed_decimal, parse_afip_response

_logger = logging.getLogger(__name__)

class AfipIvaTurReport(models.Model):
    _name = 'afip.iva.tur.report'
    _description = 'AFIP IVA Turismo Report'
    _inherit = ['mail.thread', 'mail.activity.mixin'] # Hereda para el chatter
    _order = 'date_from desc'

    name = fields.Char(
        string='Nombre del Reporte',
        compute='_compute_name',
        store=True,
        help="Nombre generado automáticamente para el reporte (ej. IVA TUR 2025/06)"
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        required=True,
        default=lambda self: self.env.company
    )
    
    date_from = fields.Date(
        string='Fecha Desde',
        required=True,
        default=lambda self: datetime.date.today().replace(day=1)
    )
    
    date_to = fields.Date(
        string='Fecha Hasta',
        required=True,
        default=lambda self: datetime.date.today()
    )
    
    date_payment = fields.Date(
        string='Fecha de Pago (Exportable)',
        required=True,
        default=lambda self: datetime.date.today() + datetime.timedelta(days=1), 
        help="Fecha que se utilizará como 'Fecha de Pago' en el archivo exportable de AFIP IVA Turismo."
    )

    state = fields.Selection([
        ('draft', 'Borrador'),
        ('generated', 'Generado'),
        ('presented', 'Presentado'),
    ], string='Estado', default='draft', readonly=True, copy=False,
        help="Estado del reporte: Borrador (se pueden editar los datos), Generado (listo para presentar), Presentado (reporte enviado a AFIP)."
    )
    
    invoice_ids = fields.Many2many(
        'account.move',
        string='Comprobantes Incluidos',
        domain=[('move_type', 'in', ('out_invoice', 'out_refund')), ('state', '=', 'posted')],
        help="Listado de comprobantes Tipo T incluidos en este reporte. Se completará automáticamente al generar el borrador."
    )
    
    exported_file = fields.Binary(
        string='Archivo TXT Exportado',
        readonly=True,
        attachment=True,
        help="Archivo TXT generado para la presentación en AFIP."
    )
    
    exported_filename = fields.Char(
        string='Nombre del Archivo',
        readonly=True,
    )
    
    presentation_date = fields.Date(
        string='Fecha de Presentación',
        readonly=True,
        help="Fecha en que el reporte fue marcado como presentado."
    )
    
    sequence = fields.Integer(
        string='Número de Remesa',
        readonly=True,
        default=0,
        help='Número de intentos para presentar el reporte.'        
    )

    @api.depends('date_from', 'date_to')
    def _compute_name(self):
        for rec in self:
            if rec.date_from and rec.date_to:
                rec.name = _("IVA TUR %s/%s") % (rec.date_from.year, str(rec.date_from.month).zfill(2))
            else:
                rec.name = False

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise ValidationError(_("La 'Fecha Desde' no puede ser posterior a la 'Fecha Hasta'."))

    def action_clear_invoices(self):
        """ Acción para eliminar todos los comprobantes de la lista si el reporte está en borrador. """
        self.ensure_one()
        if self.state == 'presented':
            raise UserError(_("No puede limpiar los comprobantes de un reporte ya presentado. Cree uno nuevo si necesita corregir."))
        if self.state == 'draft':
            self.invoice_ids = [(5, 0, 0)] # Comando (5, 0, 0) vacía completamente el many2many
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Comprobantes Borrados'),
                    'message': _('Todos los comprobantes han sido eliminados del reporte borrador.'),
                    'type': 'info',
                    'sticky': False,
                }
            }
        else:
            pass
    
    # --- CAMBIO CLAVE AQUÍ: Renombramos action_generate_draft a action_update_invoices ---
    def action_update_invoices(self):
        """ Acción para actualizar la lista de comprobantes del reporte, añadiendo los no duplicados. """
        self.ensure_one()
        afip_iva_tur_doc_codes = ['195', '196', '197', '362']

        doc_type_ids = self.env['l10n_latam.document.type'].search([
            ('code', 'in', afip_iva_tur_doc_codes),
            ('l10n_ar_letter', '=', 'T'),
        ]).ids

        if not doc_type_ids:
            self.invoice_ids = [(5, 0, 0)]
            self.state = 'draft'
            return {
                'warning': {
                    'title': _("Advertencia"),
                    'message': _("No se encontraron tipos de documento AFIP configurados para 'IVA Turismo' (códigos: %s, letra 'T')." % afip_iva_tur_doc_codes),
                }
            }

        domain = [
            ('company_id', '=', self.company_id.id),
            # out_invoice = Factura T / Nota de Débito T, out_refund = Nota de Crédito T.
            # Filtrar sólo por out_invoice dejaba afuera todas las Notas de Crédito T (197).
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('l10n_latam_document_type_id', 'in', doc_type_ids),
        ]

        # Facturas candidatas que Odoo encuentra para este período y criterios (invoices que *podrían* ir en este reporte)
        invoices_found_in_period = self.env['account.move'].search(domain)
        
        # --- Lógica MEJORADA para identificar y reportar *solo* las duplicadas conflictivas ---
        # 1. Obtener todas las facturas que *ya están* en *otros* reportes (excluyendo el reporte actual)
        all_invoices_in_other_reports_excluding_self = self.env['afip.iva.tur.report'].search([
            ('id', '!=', self.id), # Excluir el reporte que estamos generando/editando
        ]).mapped('invoice_ids') # Esto da un recordset de todas las facturas ya usadas en otros reportes

        # 2. Encontrar la intersección: cuáles de las 'invoices_found_in_period' (candidatas para ESTE reporte)
        #    ya se encuentran en 'all_invoices_in_other_reports_excluding_self'.
        #    Esto nos da las facturas que *realmente causan el conflicto*.
        
        conflicting_invoices = invoices_found_in_period & all_invoices_in_other_reports_excluding_self

        if conflicting_invoices:
            duplicate_messages = []
            for inv_conflict in conflicting_invoices:
                # Para cada factura en conflicto, encontrar los reportes específicos donde ya está
                reports_containing_this_invoice = self.env['afip.iva.tur.report'].search([
                    ('id', '!=', self.id), # Excluir el reporte actual
                    ('invoice_ids', 'in', inv_conflict.id) # Buscar reportes que contengan esta factura
                ])
                report_info = ", ".join([f"{r.name} (ID: {r.id})" for r in reports_containing_this_invoice])
                duplicate_messages.append(
                    _("La factura %s ya está incluida en el reporte(s): %s") % (inv_conflict.name, report_info)
                )
            
            raise UserError(_(
                "No se pueden agregar los siguientes comprobantes por estar ya incluidos en otros reportes de IVA Turismo:\n\n%s"
            ) % "\n".join(duplicate_messages))
        # --- FIN Lógica MEJORADA ---

        # Si no hay conflictos, asignamos todas las facturas encontradas en el período a este reporte
        self.invoice_ids = [(6, 0, invoices_found_in_period.ids)]
        self.state = 'generated' # Si se actualizaron los comprobantes, el reporte pasa a generado
        
        if not invoices_found_in_period:
            self.state = 'draft' # Si no se encontraron facturas, queda en borrador
            return {
                'warning': {
                    'title': _("Advertencia"),
                    'message': _("No se encontraron comprobantes Tipo T para el período seleccionado."),
                }
            }
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'afip.iva.tur.report',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
            'context': self.env.context,
            'flags': {'action_buttons': True, 'reload': True},
        }
    # --- FIN CAMBIO CLAVE: Renombramos action_generate_draft a action_update_invoices ---

    def action_generate_file(self):
        """ Acción para generar el archivo TXT a partir de los comprobantes ya cargados. """
        self.ensure_one()
        if not self.invoice_ids:
            raise UserError(_("No hay comprobantes asociados a este reporte para generar el archivo."))
        
        output = io.StringIO()

        # --- REGISTRO TIPO 1: CABECERA DEL ARCHIVO ---
        cuit_informante = self.company_id.vat.replace('-', '').strip()
        # PERÍODO: mes/año que se está declarando (no la fecha de generación del archivo)
        periodo = self.date_from.strftime('%Y%m')
        sin_movimiento = "0" if len(self.invoice_ids) > 0 else "1"
        # SECUENCIA (rectificativa): 2 posiciones, 00 = original, >00 = rectificativas sucesivas
        secuencia = str(self.sequence % 100).zfill(2)

        line1 = (
            "01" +
            cuit_informante +
            periodo +
            secuencia +
            "0103" +
            "858" +
            "8089" +
            "00100" +
            sin_movimiento
        )
        output.write(line1 + '\r\n')

        for inv in self.invoice_ids:  
            
            comprobante = parse_autorizar_comprobante(inv.afip_xml_request).comprobante
            response = parse_afip_response(inv.afip_xml_response)
                      
            # --- REGISTRO TIPO 2: COMPROBANTE DE VENTA ---
            tipo_comprobante_afip = comprobante.codigoTipoComprobante.zfill(3)
            punto_venta = comprobante.numeroPuntoVenta.zfill(5)
            numero_comprobante = comprobante.numeroComprobante.zfill(8)
            fecha_emision = inv.invoice_date.strftime('%Y%m%d') if inv.invoice_date else '00000000'
            tipo_doc_turista = comprobante.codigoTipoDocumento.zfill(2)
            nro_doc_turista = comprobante.numeroDocumento.ljust(20)
            codigo_pais = comprobante.codigoPais.zfill(4)
            id_impositivo = comprobante.idImpositivo.zfill(2)
            codigo_relacion = comprobante.codigoRelacionEmisorReceptor.zfill(2)
            importe_gravado = str(int(round(comprobante.importeGravado * 100))).zfill(15)
            importe_no_gravado = str(int(round(comprobante.importeNoGravado * 100))).zfill(15)
            importe_exento = str(int(round(comprobante.importeExento * 100))).zfill(15)
            # IMPORTE REINTEGRO es un campo numérico sin signo; el XML de AFIP lo trae
            # negativo (convención interna de WSCT), por eso se informa en valor absoluto.
            importe_reintegro = str(abs(int(round(comprobante.importeReintegro * 100)))).zfill(15)
            importe_total = str(int(round(comprobante.importeTotal * 100))).zfill(15)

            codigo_moneda = comprobante.codigoMoneda.ljust(3)
            # Despues del PES revisar que la cotizacion sean 18 caracteres, 6 decimales
            cotizacion_moneda = format_fixed_decimal(comprobante.cotizacionMoneda)
            
            # Alfanumérico (3) / Numérico (14): deben mantener ancho fijo aun si vienen vacíos
            # (comprobante emitido por Controlador Fiscal en vez de CAE/CAI)
            tipo_auth = (response.tipo_autorizacion or '').ljust(3)
            codigo_auth = (response.codigo_autorizacion or '').zfill(14)

            codigo_control_fiscal = "".ljust(6)
            serie_control_fiscal = "".zfill(10)

            line2 = "".join(str(x) for x in (
                "02",
                tipo_comprobante_afip,
                punto_venta,
                numero_comprobante,
                fecha_emision,
                tipo_doc_turista,
                nro_doc_turista,
                codigo_pais,
                id_impositivo,
                codigo_relacion,
                importe_gravado,
                importe_no_gravado,
                importe_exento,
                importe_reintegro,
                codigo_moneda,
                cotizacion_moneda,
                tipo_auth,
                codigo_auth,
                codigo_control_fiscal,
                serie_control_fiscal,
                importe_total,
            ))
            output.write(line2 + '\r\n')

            # --- REGISTRO TIPO 3: TOTALES DEL COMPROBANTE DE VENTA (Base IVA) ---
            for iva in comprobante.subtotales_iva:
                codigo_iva = "11" if iva.codigo == "5" else "10"
                # Base imponible = Importe IVA / alícuota (21% en ambos códigos 10 y 11,
                # la diferencia entre ellos es si aplica o no el reintegro)
                base_imponible = str(int(round(iva.importe * 100 / 0.21))).zfill(15)
                importe_iva = str(int(round(iva.importe * 100))).zfill(15)
                
                line3 = "".join(str(x) for x in (
                    "03", codigo_iva, base_imponible, importe_iva,
                ))
                output.write(line3 + '\r\n')

            # --- REGISTRO TIPO 4: DATOS DEL TURISTA EXTRANJERO ---
            nombre_turista = str(inv.partner_id.name or '').strip().ljust(50)
            
            line4 = "".join(str(x) for x in (
                "04", tipo_doc_turista, nro_doc_turista, codigo_pais,
                nombre_turista, codigo_pais, codigo_pais,
            ))
            output.write(line4 + '\r\n')

            # --- REGISTRO TIPO 5: DATOS DEL REINTEGRO ---
            # Sólo corresponde informarlo cuando la Relación Emisor-Receptor es 04, 05 ó 06
            # (agencia intermediaria). Si es 01, 02 ó 03 (alojamiento directo al turista) el
            # manual indica explícitamente que NO debe informarse este registro.
            if codigo_relacion in ('04', '05', '06'):
                line5 = "".join(str(x) for x in (
                    "05", cuit_informante, tipo_comprobante_afip, punto_venta,
                    numero_comprobante, tipo_auth, codigo_auth, fecha_emision,
                    codigo_control_fiscal, serie_control_fiscal, importe_reintegro,
                ))
                output.write(line5 + '\r\n')
            
            # --- REGISTRO TIPO 6: COMPROBANTES ASOCIADOS ---
            for comp_asociado in comprobante.comprobantes_asociados:
                codigo_comp_asociado = comp_asociado.codigoTipoComprobante.zfill(3)
                punto_venta_comp_asociado = comp_asociado.numeroPuntoVenta.zfill(5)
                numero_comp_asociado = comp_asociado.numeroComprobante.zfill(8)
                
                line6 = "".join(str(x) for x in (
                    "06", codigo_comp_asociado, punto_venta_comp_asociado, numero_comp_asociado,
                ))
                output.write(line6 + '\r\n')

            # --- REGISTRO TIPO 7: CONCEPTOS DE DETALLE DEL COMPROBANTE ---
            # TODO(IVA-TUR): CUIT del alojamiento, fecha de ingreso, unidad, tipo de unidad,
            # cantidad de personas, cantidad de noches y precio unitario son OBLIGATORIOS por
            # AFIP para Código TUR 0001/0002 (servicio de alojamiento), pero Odoo no captura
            # hoy esa información en ningún lado (ni factura, ni línea, ni producto): el envío
            # WSCT a AFIP (l10n_ar_afipws_wsct) sólo manda código/descripción/IVA/importe.
            # Quedan en blanco/cero a propósito hasta que se agreguen esos campos (p.ej. en la
            # línea de factura) y se complete este mapeo.
            for item in comprobante.items:
                tipo_item = item.tipo.zfill(2)
                cod_tur_item = item.codigoTurismo.zfill(4)
                codigo_item = item.codigo.ljust(50)
                cuit_hotel = "".ljust(11)
                fecha_ingreso_item = "".ljust(8)
                unidad_item = "".ljust(4)
                tipo_unidad_item = "".ljust(4)
                cantidad_personas = "".ljust(2)
                descripcion_item = item.descripcion.ljust(200)
                cantidad_noches = "".ljust(5)
                precio_unitario = "".ljust(18)
                codigo_iva_item = "11" if item.codigoAlicuotaIVA == "5" else "10"
                importe_iva_item = str(int(round(item.importeIVA * 100))).zfill(15)
                importe_total_item = str(int(round(item.importeItem * 100))).zfill(15)
                
                line7 = "".join(str(x) for x in (
                    "07", tipo_item, cod_tur_item, codigo_item, cuit_hotel,
                    fecha_ingreso_item, unidad_item, tipo_unidad_item, cantidad_personas,
                    descripcion_item, cantidad_noches, precio_unitario, codigo_iva_item,
                    importe_iva_item, importe_total_item,
                ))
                output.write(line7 + '\r\n')

            # --- REGISTRO TIPO 8: MEDIOS DE PAGO ---
            
            payments = inv._get_reconciled_payments()

            # Campos comunes (vacíos por especificación)
            codigo_swift = "".ljust(11)
            tipo_cuenta = "".ljust(2)
            numero_tarjeta = "".ljust(6)
            numero_cuenta = "".ljust(20)
            
            if not payments:
                # Sin pagos: tipo 3 (transferencia bancaria) con total de la factura.
                # Según la Tabla Tipo de Cuenta del manual: 1=Tarjeta de crédito,
                # 2=Tarjeta de débito, 3=Transferencia bancaria.
                line8 = "".join(str(x) for x in (
                    "08",
                    "3",  # tipo_forma_pago (transferencia bancaria)
                    codigo_swift,
                    tipo_cuenta,
                    numero_tarjeta,
                    numero_cuenta,
                    str(int(round(inv.amount_total * 100))).zfill(15),
                ))
                output.write(line8 + '\r\n')
            else:
                 # Con pagos: generar un registro por cada pago
                for pay in payments:
                    tipo_forma_pago = pay.journal_id.l10n_ar_afip_wsct_payment_type or '3'
                    importe_medio_pago = str(int(round(pay.amount * 100))).zfill(15)

                    line8 = "".join(str(x) for x in (
                        "08", tipo_forma_pago, codigo_swift, tipo_cuenta,
                        numero_tarjeta, numero_cuenta, importe_medio_pago,
                    ))
                    output.write(line8 + '\r\n')
        
        content = output.getvalue()
        
        def _get_export_filename_report(record):
            cuit_informante_clean = record.company_id.vat.replace('-', '').strip() # CUIT sin guiones/puntos
            # Asegurar que el CUIT tiene 11 dígitos, rellenar si es necesario, o truncar
            cuit_informante_padded = cuit_informante_clean.ljust(11, '0')[:11] # Rellenar con 0 y truncar a 11

            # PERÍODO informado en el archivo: el mes/año del reporte, no la fecha de generación
            periodo = record.date_from.strftime('%Y%m') # AAAAMM

            # Asumimos '0000' para la primera remesa.
            # Si necesitas un manejo de remesas, esto implicaría un campo en afip.iva.tur.report
            # para almacenar la última remesa del período.
            numero_remesa = str(record.sequence).zfill(4)

            # Formato: F + COD_REGIMEN + CUIT_INFORMATE + PERIODO_AAAAMM + NRO_REMESA + .TXT
            # COD_REGIMEN = 8089 para IVA Turismo
            ## 00 completa el periodo en 8 dígitos
            return f"F8089.{cuit_informante_padded}.{periodo}00.{numero_remesa}.TXT"

        # Revisar nombre del archivo
        filename = _get_export_filename_report(self)

        # AFIP valida la longitud de cada registro en BYTES, leyendo el archivo como
        # Latin-1 (ISO-8859-1). En UTF-8 los caracteres acentuados ocupan 2 bytes y
        # desalinean el registro completo (p.ej. "habitación" sumaba +1 byte por tilde
        # y el registro 07 pasaba de 342 a 344). Latin-1 garantiza 1 byte por carácter.
        encoded_content = base64.b64encode(content.encode('latin-1', errors='replace'))

        self.write({
            'exported_file': encoded_content,
            'exported_filename': filename,
            'sequence': self.sequence + 1, # Incrementa la secuencia de remesa
        })
        self.state = 'generated'
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
            'flags': {'action_buttons': True, 'reload': True}, # Asegura que los botones se refresquen
        }

    def action_mark_as_presented(self):
        """ Acción para marcar el reporte como presentado. """
        self.ensure_one()
        if self.state == 'draft':
            raise UserError(_("No puede marcar un borrador de reporte como presentado. Genere el borrador primero."))
        self.write({
            'state': 'presented',
            'presentation_date': fields.Date.today(),
        })
        # --- CAMBIO CLAVE: Refrescar la vista después de la acción ---
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
            'flags': {'action_buttons': True, 'reload': True},
        }
        # --- FIN CAMBIO CLAVE ---

    def action_set_to_draft(self):
        """ Acción para volver el reporte a estado borrador. """
        self.ensure_one()
        if self.state == 'presented':
            raise UserError(_("No puede volver un reporte presentado a borrador. Cree uno nuevo si necesita corregir."))
        self.write({
            'state': 'draft',
            'exported_file': False,
            'exported_filename': False,
            'presentation_date': False,
            'invoice_ids': [(5, 0, 0)],
        })
        # --- CAMBIO CLAVE: Refrescar la vista después de la acción ---
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
            'flags': {'action_buttons': True, 'reload': True},
        }
        # --- FIN CAMBIO CLAVE ---