"""Utilidades de parseo de las respuestas del web service WSCT.

Se usa ``xml.etree.ElementTree`` de la biblioteca estandar en lugar de
``pysimplesoap``: alcanza para leer un tag y evita cargar una dependencia
externa al importar el modulo.
"""

import logging
import xml.etree.ElementTree as ET

_logger = logging.getLogger(__name__)


def iter_by_local_name(root, local_name):
    """Recorre los nodos cuyo nombre local sea ``local_name``, ignorando el namespace.

    AFIP devuelve el mismo cuerpo SOAP con prefijos distintos segun la libreria
    cliente que se use, asi que no conviene atarse a un namespace fijo.
    """
    for node in root.iter():
        if node.tag.rpartition("}")[2] == local_name:
            yield node


def get_invoice_number_from_response(xml_response):
    """Devuelve el numeroComprobante que asigno AFIP, o False si no se puede leer."""
    if not xml_response:
        return False
    try:
        root = ET.fromstring(xml_response)
    except ET.ParseError:
        _logger.warning("No se pudo parsear la respuesta XML del WSCT.", exc_info=True)
        return False

    for node in iter_by_local_name(root, "numeroComprobante"):
        try:
            return int((node.text or "").strip())
        except (TypeError, ValueError):
            continue
    return False
