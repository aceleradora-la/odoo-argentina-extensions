"""El parser tiene que leer igual los sobres SOAP de los dos stacks.

Community (``l10n_ar_afipws_fe`` con pysimplesoap) y Enterprise (``l10n_ar_edi``
con zeep) mandan el mismo cuerpo con prefijos y namespaces distintos.
"""

from odoo.tests.common import TransactionCase, tagged

from odoo.addons.l10n_ar_afip_iva_tur.afip_utils import (
    format_fixed_decimal,
    parse_afip_response,
    parse_autorizar_comprobante,
)

COMPROBANTE_BODY = """
      <authRequest>
        <token>TOKEN123</token>
        <sign>SIGN456</sign>
        <cuitRepresentada>30111111118</cuitRepresentada>
      </authRequest>
      <comprobanteRequest>
        <codigoTipoComprobante>195</codigoTipoComprobante>
        <numeroPuntoVenta>3</numeroPuntoVenta>
        <numeroComprobante>77</numeroComprobante>
        <fechaEmision>2026-07-15</fechaEmision>
        <codigoTipoDocumento>91</codigoTipoDocumento>
        <numeroDocumento>AB123456</numeroDocumento>
        <idImpositivo>5</idImpositivo>
        <codigoPais>203</codigoPais>
        <domicilioReceptor>Av Siempreviva 742 - Springfield</domicilioReceptor>
        <codigoRelacionEmisorReceptor>1</codigoRelacionEmisorReceptor>
        <importeGravado>1000.00</importeGravado>
        <importeNoGravado>0.00</importeNoGravado>
        <importeExento>0.00</importeExento>
        <importeReintegro>210.00</importeReintegro>
        <importeTotal>1210.00</importeTotal>
        <codigoMoneda>DOL</codigoMoneda>
        <cotizacionMoneda>1350.500000</cotizacionMoneda>
        <arrayItems>
          <item>
            <tipo>0</tipo>
            <codigoTurismo>2</codigoTurismo>
            <codigo>HAB-DOBLE</codigo>
            <descripcion>Alojamiento con desayuno</descripcion>
            <codigoAlicuotaIVA>5</codigoAlicuotaIVA>
            <importeIVA>210.00</importeIVA>
            <importeItem>1210.00</importeItem>
          </item>
        </arrayItems>
        <arraySubtotalesIVA>
          <subtotalIVA>
            <codigo>5</codigo>
            <importe>210.00</importe>
          </subtotalIVA>
        </arraySubtotalesIVA>
        <arrayComprobantesAsociados>
          <comprobanteAsociado>
            <codigoTipoComprobante>195</codigoTipoComprobante>
            <numeroPuntoVenta>3</numeroPuntoVenta>
            <numeroComprobante>70</numeroComprobante>
          </comprobanteAsociado>
        </arrayComprobantesAsociados>
      </comprobanteRequest>
"""

REQUEST_PYSIMPLESOAP = """<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"
               xmlns:ser="http://ar.gob.afip.wsct/CTService/">
  <soap:Body>
    <ser:autorizarComprobanteRequest>%s</ser:autorizarComprobanteRequest>
  </soap:Body>
</soap:Envelope>""" % COMPROBANTE_BODY

REQUEST_ZEEP = """<?xml version="1.0" encoding="UTF-8"?>
<soap-env:Envelope xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <ns0:autorizarComprobanteRequest xmlns:ns0="http://ar.gob.afip.wsct/CTService/">%s</ns0:autorizarComprobanteRequest>
  </soap-env:Body>
</soap-env:Envelope>""" % COMPROBANTE_BODY

RESPONSE_PYSIMPLESOAP = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:wsct="http://ar.gob.afip.wsct/CTService/">
  <soapenv:Body>
    <wsct:autorizarComprobanteResponse>
      <wsct:autorizarComprobanteReturn>
        <comprobanteResponse>
          <cuit>30111111118</cuit>
          <codigoTipoComprobante>195</codigoTipoComprobante>
          <numeroPuntoVenta>3</numeroPuntoVenta>
          <numeroComprobante>77</numeroComprobante>
          <CAE>75123456789012</CAE>
          <fechaVencimientoCAE>2026-07-25</fechaVencimientoCAE>
        </comprobanteResponse>
        <resultado>A</resultado>
      </wsct:autorizarComprobanteReturn>
    </wsct:autorizarComprobanteResponse>
  </soapenv:Body>
</soapenv:Envelope>"""

RESPONSE_ZEEP = """<?xml version="1.0" encoding="UTF-8"?>
<soap-env:Envelope xmlns:soap-env="http://schemas.xmlsoap.org/soap/envelope/">
  <soap-env:Body>
    <ns0:autorizarComprobanteResponse xmlns:ns0="http://ar.gob.afip.wsct/CTService/">
      <ns0:autorizarComprobanteReturn>
        <comprobanteResponse>
          <cuit>30111111118</cuit>
          <numeroComprobante>77</numeroComprobante>
          <CAI>75123456789012</CAI>
          <fechaVencimientoCAI>2026-07-25</fechaVencimientoCAI>
        </comprobanteResponse>
        <resultado>A</resultado>
      </ns0:autorizarComprobanteReturn>
    </ns0:autorizarComprobanteResponse>
  </soap-env:Body>
</soap-env:Envelope>"""


@tagged("post_install", "-at_install")
class TestAfipUtils(TransactionCase):
    def _assert_comprobante(self, xml):
        comp = parse_autorizar_comprobante(xml).comprobante
        # El tipo de comprobante y el tipo de documento del turista son distintos:
        # confundirlos rompía el registro 02 del exportable.
        self.assertEqual(comp.codigoTipoComprobante, "195")
        self.assertEqual(comp.codigoTipoDocumento, "91")
        self.assertEqual(comp.numeroComprobante, "77")
        self.assertEqual(comp.codigoPais, "203")
        self.assertEqual(comp.codigoRelacionEmisorReceptor, "1")
        self.assertEqual(comp.importeReintegro, 210.0)
        self.assertEqual(comp.cotizacionMoneda, 1350.5)
        self.assertEqual(len(comp.items), 1)
        self.assertEqual(comp.items[0].codigoTurismo, "2")
        self.assertEqual(comp.items[0].importeItem, 1210.0)
        self.assertEqual(len(comp.subtotales_iva), 1)
        self.assertEqual(comp.subtotales_iva[0].codigo, "5")
        self.assertEqual(len(comp.comprobantes_asociados), 1)
        self.assertEqual(comp.comprobantes_asociados[0].numeroComprobante, "70")

    def test_request_community_stack(self):
        self._assert_comprobante(REQUEST_PYSIMPLESOAP)

    def test_request_enterprise_stack(self):
        self._assert_comprobante(REQUEST_ZEEP)

    def test_response_cae(self):
        response = parse_afip_response(RESPONSE_PYSIMPLESOAP)
        self.assertEqual(response.tipo_autorizacion, "CAE")
        self.assertEqual(response.codigo_autorizacion, "75123456789012")
        self.assertEqual(response.resultado, "A")
        self.assertEqual(response.numeroComprobante, "77")

    def test_response_cai(self):
        response = parse_afip_response(RESPONSE_ZEEP)
        self.assertEqual(response.tipo_autorizacion, "CAI")
        self.assertEqual(response.codigo_autorizacion, "75123456789012")
        self.assertEqual(response.fechaVencimiento, "2026-07-25")

    def test_missing_xml_raises(self):
        with self.assertRaises(ValueError):
            parse_autorizar_comprobante("")
        with self.assertRaises(ValueError):
            parse_autorizar_comprobante("<a><b/></a>")
        with self.assertRaises(ValueError):
            parse_afip_response("")

    def test_format_fixed_decimal(self):
        # 12 dígitos enteros + 6 decimales, sin separador
        self.assertEqual(len(format_fixed_decimal(1350.5)), 18)
        self.assertEqual(format_fixed_decimal(1350.5), "000000001350500000")
        self.assertEqual(format_fixed_decimal(1.0), "000000000001000000")
