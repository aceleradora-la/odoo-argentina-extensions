# AFIP IVA Turismo - Exportable F.8089

Genera el archivo de texto (Registro Tipo 01 a 08) del Régimen Informativo de
Reintegro del IVA facturado por servicios de alojamiento a turistas
extranjeros (Formulario AFIP/ARCA F.8089), a partir de los comprobantes Tipo T
(Factura/ND/NC T) emitidos vía `l10n_ar_afipws_fe` + `l10n_ar_afipws_wsct`.

## Datos de estadía (Registro Tipo 07): campo JSON por línea de factura

ARCA exige, para cada ítem de alojamiento (Código TUR 0001/0002), el detalle
de la estadía: fecha de ingreso, cantidad de unidades, tipo de unidad,
cantidad de personas, cantidad de noches y precio unitario. Odoo no captura
estos datos en la facturación estándar, por lo que este módulo agrega el campo
**`l10n_ar_iva_tur_json`** (texto JSON) en `account.move.line`.

El campo puede cargarse:

- **Por integración** (API externa, PMS): un `write` sobre la línea de
  factura vía XML-RPC/JSON-RPC. El campo es un campo custom sin impacto
  contable, por lo que puede escribirse también en facturas ya publicadas.
- **Manualmente**: en la factura, columna opcional "Datos IVA Tur (JSON)" de
  las líneas (activarla desde el selector de columnas de la lista de líneas).

### Esquema del JSON (claves fijas)

```json
{
  "fecha_ingreso": "2026-06-25",
  "unidad": 1,
  "tipo_unidad": "0011",
  "cantidad_personas": 2,
  "cantidad_noches": 3,
  "precio_unitario": 56904.50,
  "cuit_hotel": "30714877093"
}
```

| Clave | Tipo | Descripción |
|---|---|---|
| `fecha_ingreso` | string | Fecha de check-in. Formatos aceptados: `AAAA-MM-DD` (recomendado), `DD/MM/AAAA`, `DD-MM-AAAA`, `AAAAMMDD`. Se exporta como `DDMMAAAA`. |
| `unidad` | int | Cantidad de habitaciones / unidades funcionales facturadas en el ítem. |
| `tipo_unidad` | string | Código de la tabla "Tipo Unidad" de ARCA (ver abajo). Puede ir con o sin ceros a la izquierda (`"11"` = `"0011"`). |
| `cantidad_personas` | int | Cantidad de personas. **Obligatorio salvo** `tipo_unidad` = `0014` (plaza). |
| `cantidad_noches` | number | Cantidad de noches. Admite decimales (formato ARCA: 3 enteros + 2 decimales; máximo 90 por validación de ARCA). |
| `precio_unitario` | number | Precio por noche **sin IVA** (formato ARCA: 12 enteros + 6 decimales). |
| `cuit_hotel` | string | CUIT del alojamiento. **Sólo** para Relación Emisor-Receptor 04/05/06 (agencias que facturan servicios de un hotel). No cargar en el caso hotel→turista directo. |

Los números aceptan string con coma o punto decimal (`"3"`, `3`, `"56904,50"`).

### Tabla Tipo Unidad (ARCA)

| Código | Descripción |
|---|---|
| 0001 | persona |
| 0002 | carpa |
| 0003 | bungalow |
| 0004 | cabaña |
| 0005 | departamento |
| 0010 | single |
| 0011 | doble |
| 0012 | triple |
| 0013 | cuádruple |
| 0014 | plaza (para hostel) |

### Cuándo es obligatorio (validado al generar el TXT)

Según el manual F.8089 (sección 4.7), por Tipo de Ítem y Código TUR del ítem:

- **Obligatorio**: Tipo Ítem `00` + Código TUR `0001`/`0002` (alojamiento
  sin/con desayuno). Si falta algún dato, la generación del archivo se corta
  con un error que lista factura, línea y claves faltantes.
- **Opcional (todo o nada)**: Código TUR `0005` (Excedente). Si se informa
  alguno de `unidad` / `cantidad_noches` / `precio_unitario`, deben
  informarse los tres.
- **No debe cargarse**: Tipo Ítem `91` (ajuste IVA), `97` (anticipo), `99`
  (descuento), y Código TUR `0020`/`0021`. Si el JSON está cargado igual en
  esos ítems, el módulo lo ignora (exporta en blanco, como exige ARCA).

### Correspondencia línea ↔ ítem

Cada línea de producto de la factura se corresponde 1 a 1 y en el mismo orden
con los ítems del XML enviado a WSCT (`arrayItems`), que es de donde salen los
registros 07. Cargar el JSON en la línea correcta.

## Otras notas

- **Codificación del archivo**: se exporta en Latin-1 (ISO-8859-1) porque ARCA
  valida las longitudes de registro en bytes. No usar UTF-8.
- **Registro Tipo 04 (Datos del Turista)**: país de nacionalidad y país de
  residencia del turista se informan iguales al país del receptor del
  comprobante, por no existir hoy un campo separado para cada uno en Odoo.
