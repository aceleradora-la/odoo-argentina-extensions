# AFIP IVA Turismo - Exportable F.8089

Genera el archivo de texto (Registro Tipo 01 a 08) del Régimen Informativo de
Reintegro del IVA facturado por servicios de alojamiento a turistas
extranjeros (Formulario AFIP F.8089), a partir de los comprobantes Tipo T
(Factura/ND/NC T) emitidos vía `l10n_ar_afipws_fe`.

## Estado conocido / pendiente

- **Registro Tipo 07 (Datos del Ítem):** AFIP exige, para Código TUR 0001/0002
  (servicio de alojamiento), los campos CUIT del alojamiento, fecha de
  ingreso, unidad, tipo de unidad, cantidad de personas, cantidad de noches y
  precio unitario. Hoy Odoo **no captura esta información en ningún lado**
  (ni en la factura, ni en sus líneas, ni en el producto): el envío WSCT a
  AFIP (`l10n_ar_afipws_wsct`) sólo informa código/descripción/IVA/importe
  por ítem. El módulo deja estos campos en blanco/cero a propósito. Para
  cumplir estrictamente con el régimen en comprobantes con estos códigos TUR,
  hace falta agregar esos campos (p. ej. en la línea de factura) y completar
  el mapeo en `models/afip_iva_tur_report.py`.
- **Registro Tipo 04 (Datos del Turista):** país de nacionalidad y país de
  residencia del turista se informan iguales al país del receptor del
  comprobante, por no existir hoy un campo separado para cada uno en Odoo.
