"""Parseo del request/response SOAP del web service WSCT.

El parseo se hace por *nombre local* de los tags, ignorando el namespace y el
prefijo. Eso permite leer indistintamente los sobres que genera ``pysimplesoap``
(stack Community, ``l10n_ar_afipws_fe``) y los que genera ``zeep`` (stack
Enterprise, ``l10n_ar_edi``), que describen el mismo cuerpo con prefijos
distintos.
"""

import xml.etree.ElementTree as ET


def _local_name(node):
    return node.tag.rpartition("}")[2]


def _find(node, local_name):
    """Primer descendiente directo o indirecto con ese nombre local."""
    if node is None:
        return None
    for child in node.iter():
        if child is not node and _local_name(child) == local_name:
            return child
    return None


def _findall(node, local_name):
    if node is None:
        return []
    return [child for child in node.iter() if child is not node and _local_name(child) == local_name]


def _text(node, local_name, default=""):
    found = _find(node, local_name)
    if found is None or found.text is None:
        return default
    return found.text.strip()


def _float(node, local_name, default=0.0):
    raw = _text(node, local_name, "")
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


class Item:
    def __init__(self, tipo, codigoTurismo, codigo, descripcion, codigoAlicuotaIVA, importeIVA, importeItem):
        self.tipo = tipo
        self.codigoTurismo = codigoTurismo
        self.codigo = codigo
        self.descripcion = descripcion
        self.codigoAlicuotaIVA = codigoAlicuotaIVA
        self.importeIVA = float(importeIVA)
        self.importeItem = float(importeItem)


class SubtotalIVA:
    def __init__(self, codigo, importe):
        self.codigo = codigo
        self.importe = float(importe)


class ComprobanteAsociado:
    def __init__(self, codigoTipoComprobante, numeroPuntoVenta, numeroComprobante):
        self.codigoTipoComprobante = codigoTipoComprobante
        self.numeroPuntoVenta = numeroPuntoVenta
        self.numeroComprobante = numeroComprobante


class ComprobanteRequest:
    def __init__(self):
        self.codigoTipoComprobante = ""
        self.numeroPuntoVenta = ""
        self.numeroComprobante = ""
        self.fechaEmision = ""
        self.codigoTipoAutorizacion = ""
        self.codigoTipoDocumento = ""
        self.numeroDocumento = ""
        self.idImpositivo = ""
        self.codigoPais = ""
        self.domicilioReceptor = ""
        self.codigoRelacionEmisorReceptor = ""
        self.importeGravado = 0.0
        self.importeNoGravado = 0.0
        self.importeExento = 0.0
        self.importeReintegro = 0.0
        self.importeTotal = 0.0
        self.codigoMoneda = ""
        self.cotizacionMoneda = 0.0
        self.observaciones = ""
        self.items = []
        self.subtotales_iva = []
        self.comprobantes_asociados = []


class AuthRequest:
    def __init__(self, token, sign, cuitRepresentada):
        self.token = token
        self.sign = sign
        self.cuitRepresentada = cuitRepresentada


class AutorizarComprobanteRequest:
    def __init__(self, auth: AuthRequest, comprobante: ComprobanteRequest):
        self.auth = auth
        self.comprobante = comprobante


def parse_autorizar_comprobante(xml_string: str) -> AutorizarComprobanteRequest:
    if not xml_string:
        raise ValueError("El comprobante no tiene guardado el XML de solicitud enviado a AFIP/ARCA")

    root = ET.fromstring(xml_string)
    req = root if _local_name(root) == "autorizarComprobanteRequest" else _find(root, "autorizarComprobanteRequest")
    if req is None:
        raise ValueError("No se encontró el nodo autorizarComprobanteRequest en el XML")

    auth_node = _find(req, "authRequest")
    if auth_node is None:
        raise ValueError("No se encontró el nodo authRequest en el XML")

    auth = AuthRequest(
        token=_text(auth_node, "token"),
        sign=_text(auth_node, "sign"),
        cuitRepresentada=_text(auth_node, "cuitRepresentada"),
    )

    comp_node = _find(req, "comprobanteRequest")
    if comp_node is None:
        raise ValueError("No se encontró el nodo comprobanteRequest en el XML")

    comp = ComprobanteRequest()
    comp.codigoTipoComprobante = _text(comp_node, "codigoTipoComprobante")
    comp.numeroPuntoVenta = _text(comp_node, "numeroPuntoVenta")
    comp.numeroComprobante = _text(comp_node, "numeroComprobante")
    comp.fechaEmision = _text(comp_node, "fechaEmision")
    comp.codigoTipoAutorizacion = _text(comp_node, "codigoTipoAutorizacion")
    comp.codigoTipoDocumento = _text(comp_node, "codigoTipoDocumento")
    comp.numeroDocumento = _text(comp_node, "numeroDocumento")
    comp.idImpositivo = _text(comp_node, "idImpositivo")
    comp.codigoPais = _text(comp_node, "codigoPais")
    comp.domicilioReceptor = _text(comp_node, "domicilioReceptor")
    comp.codigoRelacionEmisorReceptor = _text(comp_node, "codigoRelacionEmisorReceptor")
    comp.importeGravado = _float(comp_node, "importeGravado")
    comp.importeNoGravado = _float(comp_node, "importeNoGravado")
    comp.importeExento = _float(comp_node, "importeExento")
    comp.importeReintegro = _float(comp_node, "importeReintegro")
    comp.importeTotal = _float(comp_node, "importeTotal")
    comp.codigoMoneda = _text(comp_node, "codigoMoneda")
    comp.cotizacionMoneda = _float(comp_node, "cotizacionMoneda")
    comp.observaciones = _text(comp_node, "observaciones")

    for item_node in _findall(comp_node, "item"):
        comp.items.append(
            Item(
                tipo=_text(item_node, "tipo"),
                codigoTurismo=_text(item_node, "codigoTurismo"),
                codigo=_text(item_node, "codigo"),
                descripcion=_text(item_node, "descripcion"),
                codigoAlicuotaIVA=_text(item_node, "codigoAlicuotaIVA"),
                importeIVA=_float(item_node, "importeIVA"),
                importeItem=_float(item_node, "importeItem"),
            )
        )

    for iva_node in _findall(comp_node, "subtotalIVA"):
        comp.subtotales_iva.append(
            SubtotalIVA(
                codigo=_text(iva_node, "codigo"),
                importe=_float(iva_node, "importe"),
            )
        )

    for ca_node in _findall(comp_node, "comprobanteAsociado"):
        comp.comprobantes_asociados.append(
            ComprobanteAsociado(
                codigoTipoComprobante=_text(ca_node, "codigoTipoComprobante"),
                numeroPuntoVenta=_text(ca_node, "numeroPuntoVenta"),
                numeroComprobante=_text(ca_node, "numeroComprobante"),
            )
        )

    return AutorizarComprobanteRequest(auth=auth, comprobante=comp)


class ComprobanteResponse:
    def __init__(self):
        self.cuit = ""
        self.codigoTipoComprobante = ""
        self.numeroPuntoVenta = ""
        self.numeroComprobante = ""
        self.fechaEmision = ""
        self.tipo_autorizacion = ""  # "CAE" o "CAI"
        self.codigo_autorizacion = ""  # valor del CAE/CAI
        self.fechaVencimiento = ""  # fecha de vencimiento del CAE/CAI
        self.resultado = ""


def parse_afip_response(xml_string: str) -> ComprobanteResponse:
    if not xml_string:
        raise ValueError("El comprobante no tiene guardada la respuesta de AFIP/ARCA")

    root = ET.fromstring(xml_string)
    return_node = _find(root, "autorizarComprobanteReturn")
    comp_resp_node = _find(return_node if return_node is not None else root, "comprobanteResponse")
    resultado_node = _find(return_node if return_node is not None else root, "resultado")

    comp = ComprobanteResponse()
    if comp_resp_node is not None:
        comp.cuit = _text(comp_resp_node, "cuit")
        comp.codigoTipoComprobante = _text(comp_resp_node, "codigoTipoComprobante")
        comp.numeroPuntoVenta = _text(comp_resp_node, "numeroPuntoVenta")
        comp.numeroComprobante = _text(comp_resp_node, "numeroComprobante")
        comp.fechaEmision = _text(comp_resp_node, "fechaEmision")

        # Detectar si viene CAE o CAI
        if _find(comp_resp_node, "CAE") is not None:
            comp.tipo_autorizacion = "CAE"
            comp.codigo_autorizacion = _text(comp_resp_node, "CAE")
            comp.fechaVencimiento = _text(comp_resp_node, "fechaVencimientoCAE")
        elif _find(comp_resp_node, "CAI") is not None:
            comp.tipo_autorizacion = "CAI"
            comp.codigo_autorizacion = _text(comp_resp_node, "CAI")
            comp.fechaVencimiento = _text(comp_resp_node, "fechaVencimientoCAI")

    if resultado_node is not None:
        comp.resultado = (resultado_node.text or "").strip()

    return comp


def format_fixed_decimal(value: float, int_digits: int = 12, dec_digits: int = 6) -> str:
    """Importe en formato fijo sin separador: parte entera con ceros + parte decimal."""
    entero, decimal = f"{value:.{dec_digits}f}".split(".")
    return entero.zfill(int_digits) + decimal
