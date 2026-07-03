import xml.etree.ElementTree as ET

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
    ns = {
        "soap": "http://schemas.xmlsoap.org/soap/envelope/",
        "ser": "http://ar.gob.afip.wsct/CTService/",
    }

    root = ET.fromstring(xml_string)
    req = root.find(".//ser:autorizarComprobanteRequest", ns)
    if req is None:
        raise ValueError("No se encontró el nodo autorizarComprobanteRequest en el XML")

    # --- authRequest ---
    auth_node = req.find("authRequest")
    if auth_node is None:
        raise ValueError("No se encontró el nodo authRequest en el XML")

    auth = AuthRequest(
        token=auth_node.findtext("token", ""),
        sign=auth_node.findtext("sign", ""),
        cuitRepresentada=auth_node.findtext("cuitRepresentada", ""),
    )

    # --- comprobanteRequest ---
    comp_node = req.find("comprobanteRequest")
    if comp_node is None:
        raise ValueError("No se encontró el nodo comprobanteRequest en el XML")

    comp = ComprobanteRequest()
    comp.codigoTipoComprobante = comp_node.findtext("codigoTipoComprobante", "")
    comp.numeroPuntoVenta = comp_node.findtext("numeroPuntoVenta", "")
    comp.numeroComprobante = comp_node.findtext("numeroComprobante", "")
    comp.fechaEmision = comp_node.findtext("fechaEmision", "")
    comp.codigoTipoAutorizacion = comp_node.findtext("codigoTipoAutorizacion", "")
    comp.codigoTipoDocumento = comp_node.findtext("codigoTipoDocumento", "")
    comp.numeroDocumento = comp_node.findtext("numeroDocumento", "")
    comp.idImpositivo = comp_node.findtext("idImpositivo", "")
    comp.codigoPais = comp_node.findtext("codigoPais", "")
    comp.domicilioReceptor = comp_node.findtext("domicilioReceptor", "")
    comp.codigoRelacionEmisorReceptor = comp_node.findtext("codigoRelacionEmisorReceptor", "")
    comp.importeGravado = float(comp_node.findtext("importeGravado", "0"))
    comp.importeNoGravado = float(comp_node.findtext("importeNoGravado", "0"))
    comp.importeExento = float(comp_node.findtext("importeExento", "0"))
    comp.importeReintegro = float(comp_node.findtext("importeReintegro", "0"))
    comp.importeTotal = float(comp_node.findtext("importeTotal", "0"))
    comp.codigoMoneda = comp_node.findtext("codigoMoneda", "")
    comp.cotizacionMoneda = float(comp_node.findtext("cotizacionMoneda", "0"))
    comp.observaciones = comp_node.findtext("observaciones", "")

    # --- Items ---
    for item_node in comp_node.findall(".//item"):
        item = Item(
            tipo=item_node.findtext("tipo", ""),
            codigoTurismo=item_node.findtext("codigoTurismo", ""),
            codigo=item_node.findtext("codigo", ""),
            descripcion=item_node.findtext("descripcion", ""),
            codigoAlicuotaIVA=item_node.findtext("codigoAlicuotaIVA", ""),
            importeIVA=float(item_node.findtext("importeIVA", "0")),
            importeItem=float(item_node.findtext("importeItem", "0")),
        )
        comp.items.append(item)

    # --- Subtotales IVA ---
    for iva_node in comp_node.findall(".//subtotalIVA"):
        sub = SubtotalIVA(
            codigo=iva_node.findtext("codigo", ""),
            importe=float(iva_node.findtext("importe", "0")),
        )
        comp.subtotales_iva.append(sub)

    # --- Comprobantes Asociados (si existen) ---
    for ca_node in comp_node.findall(".//comprobanteAsociado"):
        ca = ComprobanteAsociado(
            codigoTipoComprobante=ca_node.findtext("codigoTipoComprobante", ""),
            numeroPuntoVenta=ca_node.findtext("numeroPuntoVenta", ""),
            numeroComprobante=ca_node.findtext("numeroComprobante", ""),
        )
        comp.comprobantes_asociados.append(ca)

    return AutorizarComprobanteRequest(auth=auth, comprobante=comp)

class ComprobanteResponse:
    def __init__(self):
        self.cuit: str = ""
        self.codigoTipoComprobante: str = ""
        self.numeroPuntoVenta: str = ""
        self.numeroComprobante: str = ""
        self.fechaEmision: str = ""
        self.tipo_autorizacion: str = ""       # "CAE" o "CAI"
        self.codigo_autorizacion: str = ""     # valor del CAE/CAI
        self.fechaVencimiento: str = ""        # fecha de vencimiento del CAE/CAI
        self.resultado: str = ""


def parse_afip_response(xml_string: str) -> ComprobanteResponse:
    ns = {
        "soap": "http://schemas.xmlsoap.org/soap/envelope/",
        "wsct": "http://ar.gob.afip.wsct/CTService/"
    }

    root = ET.fromstring(xml_string)
    # El elemento raíz de la respuesta ("ns2:autorizarComprobanteResponse" en la respuesta
    # real de AFIP) usa el namespace wsct, pero sus hijos (autorizarComprobanteReturn,
    # comprobanteResponse, resultado, etc.) NO heredan ese namespace: al no llevar el
    # prefijo, quedan en el namespace vacío. Por eso se busca sin prefijo a partir de ahí.
    comp_resp_node = root.find(
        ".//wsct:autorizarComprobanteResponse/autorizarComprobanteReturn/comprobanteResponse",
        ns
    )
    resultado_node = root.find(
        ".//wsct:autorizarComprobanteResponse/autorizarComprobanteReturn/resultado",
        ns
    )

    comp = ComprobanteResponse()
    if comp_resp_node is not None:
        comp.cuit = comp_resp_node.findtext("cuit", "")
        comp.codigoTipoComprobante = comp_resp_node.findtext("codigoTipoComprobante", "")
        comp.numeroPuntoVenta = comp_resp_node.findtext("numeroPuntoVenta", "")
        comp.numeroComprobante = comp_resp_node.findtext("numeroComprobante", "")
        comp.fechaEmision = comp_resp_node.findtext("fechaEmision", "")

        # Detectar si viene CAE o CAI
        if comp_resp_node.find("CAE") is not None:
            comp.tipo_autorizacion = "CAE"
            comp.codigo_autorizacion = comp_resp_node.findtext("CAE", "")
            comp.fechaVencimiento = comp_resp_node.findtext("fechaVencimientoCAE", "")
        elif comp_resp_node.find("CAI") is not None:
            comp.tipo_autorizacion = "CAI"
            comp.codigo_autorizacion = comp_resp_node.findtext("CAI", "")
            comp.fechaVencimiento = comp_resp_node.findtext("fechaVencimientoCAI", "")
        else:
            comp.tipo_autorizacion = ""
            comp.codigo_autorizacion = ""
            comp.fechaVencimiento = ""

    if resultado_node is not None:
        comp.resultado = resultado_node.text or ""

    return comp

def format_fixed_decimal(value: float, int_digits: int = 12, dec_digits: int = 6) -> str:
    # separo parte entera y decimal
    entero, decimal = f"{value:.{dec_digits}f}".split(".")
    
    # relleno la parte entera con ceros a la izquierda
    entero = entero.zfill(int_digits)
    
    # concateno entero + decimal
    return entero + decimal
