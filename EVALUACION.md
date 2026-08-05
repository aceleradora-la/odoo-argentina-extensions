# Evaluación del módulo y migración a Odoo 18 / 19 (Community y Enterprise)

Evaluación del código original (rama `master`, serie 17.0) y detalle de los
cambios aplicados. Todo lo que se afirma acá está verificado contra el código
real de `odoo/odoo` 17.0/18.0/19.0, `ingadhoc/odoo-argentina-ce`,
`ingadhoc/odoo-argentina-ee` e `ingadhoc/odoo-argentina`, no contra documentación.

---

## 1. Resumen ejecutivo

| Objetivo | Estado |
|---|---|
| Odoo 18 Community | **Listo.** Todas las APIs usadas siguen existiendo sin cambios. |
| Odoo 19 Community | **Código listo, bloqueado por upstream.** ADHOC todavía no migró `l10n_ar_afipws*` a 19: están `installable: False`. |
| Odoo 18 Enterprise | **Implementado, sin probar contra la fuente.** `l10n_ar_edi` es cerrado. |
| Odoo 19 Enterprise | **Implementado, sin probar contra la fuente.** Ídem. |

La migración en sí resultó ser la parte **menor** del trabajo: entre 17.0, 18.0 y
19.0 no cambió prácticamente ninguna de las APIs que el módulo usa. Lo que sí
apareció fue un conjunto de defectos preexistentes, varios de ellos capaces de
cortar la emisión o de generar un archivo que AFIP rechaza.

---

## 2. Compatibilidad de versiones: qué se verificó

### 2.1 APIs que el módulo consume — sin cambios en 17 → 18 → 19

| API | Origen | 18.0 | 19.0 |
|---|---|---|---|
| `_get_journal_letter(counterpart_partner)` | core `l10n_ar` | igual | igual |
| `_get_codes_per_journal_type(afip_pos_system)` | core `l10n_ar` | igual | igual |
| `_get_l10n_ar_afip_pos_types_selection()` | core `l10n_ar` | igual | igual |
| `_get_formatted_sequence(number)` | core `l10n_ar` | igual | igual |
| `_get_sequence_format_param()` → `year_length` | core `account` | igual | igual |
| `_l10n_ar_get_amounts()` → `vat_amount`, … | core `l10n_ar` | igual | igual |
| `_get_reconciled_payments()` | core `account` | existe | existe |
| `account.tax.compute_all()` | core `account` | misma firma | misma firma |
| `_get_afip_ws`, `_get_type_mapping`, `base_map_invoice_info`, `pyafipws_add_tax` | ADHOC CE | igual | igual |

De hecho, `l10n_ar_afipws` y `l10n_ar_afipws_fe` son **byte a byte idénticos**
entre las ramas `18.0` y `19.0` de `odoo-argentina-ce`, salvo el manifest.

### 2.2 Lo que sí rompía

| Tema | Detalle | Solución |
|---|---|---|
| **`<tree>` eliminado** | `tree` dejó de ser un tipo de vista válido: en 18 y 19 la selección de `ir.ui.view.type` es `list`, no `tree`. Afectaba a la vista lista, al `view_mode="tree,form"` y al `mode="tree"` del x2many. | Todo migrado a `<list>` / `list,form`. |
| **Chatter** | El bloque `<div class="oe_chatter">` con los tres campos ya no se usa; en 18/19 es el tag `<chatter/>`. | Reemplazado. |
| **`afip_col_2` renombrado** | La vista de contacto hacía xpath sobre `//group[@name='afip_col_2']`, que **no es de Odoo ni del módulo**: lo aporta `l10n_ar_ux` (repo `odoo-argentina`), que ni siquiera estaba declarado como dependencia. En 19.0 ese grupo pasó a llamarse `arca_col_2`, con lo cual la instalación fallaba. | Reanclado a `l10n_ar.base_view_partner_form`, sobre el campo `l10n_ar_afip_responsibility_type_id`, que es core y existe igual en 17/18/19. Se elimina la dependencia oculta. |

---

## 3. Defectos encontrados (no relacionados con la versión)

### 3.1 Bloqueantes

**a) `KeyError` seguro al facturar con descuento** — `account_move_ws.py`

```python
line_temp["bonif"] = (
    line.discount and str("%.2f" % (line_temp["precio"] * line_temp["qty"] - line_temp["importe"])) or None
)
...
line_temp["importe"] = "%.2f" % (line.price_total + vat_amount)   # se asigna DESPUÉS
```

`line_temp["importe"]` se lee antes de existir. Cualquier línea con descuento
cortaba la emisión. Y aunque existiera, es un `str`: `float - str` es `TypeError`.
Corregido calculando la bonificación sobre importes netos, igual que hace el
módulo hermano de ADHOC.

**b) `contact_address_inline` no existe** — `account_move_ws.py`

El domicilio del receptor se leía de `commercial_partner.contact_address_inline`.
Ese campo **no existe** en Odoo 17/18/19 ni en ningún repo de ADHOC
(`odoo-argentina`, `-ce`, `-ee`, `partner`). Se verificó por grep en todos.
Reemplazado por un helper `_l10n_ar_wsct_get_address_inline()` construido sobre
`contact_address`, que sí es core.

**c) No existía ningún tipo de documento clase T**

`l10n_ar` acepta la letra `T` en la selección, pero **no trae ningún
`l10n_latam.document.type` que la use**. Los códigos 195 y 196 sí existen, pero
con letra `I` ("Facturas y comprobantes del exterior", para mapeo de
importaciones). Sin los tipos T, el diario WSCT no ofrecía documentos y el
reporte de IVA Turismo nunca listaba comprobantes. Se agregaron como data en
`l10n_ar_wsct_base` (el modelo no tiene restricción de unicidad sobre el código,
así que conviven con los de letra I).

### 3.2 Datos incorrectos en el exportable

**d) Campo equivocado en el registro 02** — `afip_iva_tur_report.py`

```python
tipo_comprobante_afip = comprobante.codigoTipoDocumento.zfill(3)   # ← tipo de doc del turista
```

El *tipo de comprobante* se llenaba con el *tipo de documento del turista*
(pasaporte, DNI…). `codigoTipoComprobante` se parseaba pero no se usaba en ningún
lado. Los registros 02 y 05 salían con el dato equivocado. Corregido a
`codigoTipoComprobante`.

**e) Acentos descolocaban el archivo**

El archivo es de **ancho fijo**, pero se escribía en UTF-8 y se rellenaba con
`ljust()`, que cuenta *caracteres*. Una descripción con acentos ocupaba más bytes
que columnas y corría todo el resto del registro. Se pasó a `latin-1` (un byte
por carácter).

**f) Campos sin recortar**

`ljust(200)` rellena pero no trunca: una descripción de más de 200 caracteres
alargaba el registro. Se agregaron helpers `_text_field` / `_num_field` /
`_amount_field` que rellenan, truncan el texto y **cortan la generación con un
error claro** si un numérico no entra, en vez de emitir un archivo mal formado.

**g) Notas de crédito excluidas**

El dominio filtraba `move_type = 'out_invoice'`, dejando afuera las notas de
crédito clase T (código 197), que sí deben informarse. Ampliado a
`('out_invoice', 'out_refund')`.

**h) Forma de pago por defecto contradictoria** ⚠️

Cuando el comprobante no tenía pagos conciliados, el registro 08 se escribía con
el código `"1"` y el comentario `# tipo 1 (transferencia)`. Pero en la selección
de `account.journal` el `"1"` es **tarjeta de crédito** y el `"3"` es
**transferencia bancaria**. Uno de los dos está mal.

Se unificó en `"3"`, que es lo consistente con las etiquetas del propio campo y
con la intención declarada en el comentario. **Conviene confirmar la tabla de
códigos contra el diseño de registro vigente de AFIP/ARCA**, porque acá el código
fuente se contradice a sí mismo y no hay forma de resolverlo desde adentro.

### 3.3 Interfaz y seguridad

| Problema | Detalle |
|---|---|
| **Lista de comprobantes invisible** | La página estaba envuelta en `groups="base.group_multi_company"`: en cualquier base de una sola compañía la lista de comprobantes no se veía. Quitado. |
| **Permisos sin grupo** | `ir.model.access.csv` daba lectura, escritura, creación y borrado a **cualquier usuario** (columna de grupo vacía). Acotado a `account.group_account_invoice` (sin borrado) y `account.group_account_manager`. |
| **Sin regla multi-compañía** | No había `ir.rule`: en multi-compañía se veían los informes y comprobantes de todas. Agregada. |
| **Vista del asistente inexistente** | La acción apuntaba por contexto a `afip_iva_tur_wizard_form_view`, que no estaba definida en ningún lado, y el asistente no tenía entrada de menú. Se creó la vista, con sus botones, y el ítem de menú. |
| **`warning` devuelto desde un botón** | `action_update_invoices` devolvía `{'warning': {...}}`, que no es una acción válida: el usuario no veía nada. Cambiado a `UserError`. |
| **`vat` sin validar** | `company_id.vat.replace(...)` reventaba con `AttributeError` si la compañía no tenía CUIT. Ahora valida 11 dígitos y avisa. |

### 3.4 Higiene

- `bk_afip_iva_tur_wizard.py`: 216 líneas de backup muerto, no importado. Eliminado.
- `pysimplesoap` se importaba al cargar el módulo sólo para leer un tag; se pasó a `ElementTree` de la stdlib.
- `except:` desnudo → `except ET.ParseError`.
- Manifests: faltaban `license` e `installable` en `l10n_ar_afipws_wsct`, la versión era `"0.2"`, el autor `"Mr Blitz"` y el sitio `yourcompany.com`. Faltaba declarar `external_dependencies` de `pyafipws`.
- Antipatrón de traducción `_("texto %s" % valor)` (traduce el texto ya interpolado) → `_("texto %s", valor)`.
- El repo no tenía **ningún test**. Se agregaron para el parser SOAP y el ancho fijo.

---

## 4. Community vs Enterprise

Son dos stacks sin ningún solapamiento:

| | Community | Enterprise |
|---|---|---|
| Módulo base | `l10n_ar_afipws_fe` (ADHOC) | `l10n_ar_edi` (Odoo) |
| Cliente SOAP | `pyafipws` / `pysimplesoap` | `zeep` |
| Campo del WS en diario | `afip_ws` | `l10n_ar_afip_ws` |
| Modelo de conexión | `afipws.connection` | `l10n_ar.afipws.connection` |
| XML del pedido | `afip_xml_request` | `l10n_ar_afip_xml_request` |
| Punto de extensión | `<ws>_map_invoice_info`, `<ws>_pyafipws_create_invoice`… | `_l10n_ar_do_afip_ws_request_cae` |

Por eso el soporte Enterprise es un **módulo aparte**, no una variante. La
estructura quedó así:

```
l10n_ar_wsct_base          modelo de datos común (ambas ediciones)
├── l10n_ar_afipws_wsct    adaptador Community
├── l10n_ar_edi_wsct       adaptador Enterprise
└── l10n_ar_afip_iva_tur   exportable (agnóstico de edición)
```

`l10n_ar_afip_iva_tur` ya no depende de `l10n_ar_afipws_fe`: resuelve el XML del
CAE vía `account.move._l10n_ar_iva_tur_get_afip_xml()`, que implementa cada
adaptador. El parser se reescribió para buscar por **nombre local** de tag,
ignorando namespace y prefijo, de modo que lee igual los sobres de `pysimplesoap`
y los de `zeep`. Hay tests que lo verifican con ambos formatos.

### Limitaciones declaradas

- **`l10n_ar_edi_wsct` no se pudo compilar ni ejecutar**: `odoo/enterprise` es un
  repositorio privado. Está escrito siguiendo `l10n_ar_wsmtxca_ws` de
  `odoo-argentina-ee`, que es el único ejemplo público de agregar un web service
  sobre `l10n_ar_edi` y está mantenido para 18.0 y 19.0. Las firmas usadas
  (`_l10n_ar_do_afip_ws_request_cae`, `_prepare_return_msg`, `_get_tributes`,
  `_get_partner_code_id`, `_found_related_invoice`, `l10n_ar_check_rate`,
  `_l10n_ar_get_afip_ws_url`) salen de ahí. **Requiere prueba en homologación.**
- Deliberadamente **no** se usó `saas_client_l10n_ar` (dependencia interna de
  ADHOC, no pública), de la que `l10n_ar_wsmtxca_ws` toma
  `_ws_verify_request_data` y `l10n_ar_action_preview_xml`.
- El cálculo de importes por ítem en Enterprise replica exactamente el de
  Community (`compute_all` sobre los impuestos filtrados) para que ambas
  ediciones generen el mismo exportable.

---

## 5. Ramas

| Rama | Serie |
|---|---|
| `18.0` | Odoo 18.0 |
| `19.0` | Odoo 19.0 |

El código es el mismo en ambas: sólo cambia el prefijo de versión de los
manifests, porque no hay diferencias de API entre 18 y 19 para lo que este
módulo usa.

---

## 6. Qué falta probar

Nada de esto se pudo ejecutar acá: no hay una instancia de Odoo ni credenciales
de AFIP en este entorno. Lo que sí se corrió: compilación de todo el Python,
validación XML de todas las vistas, chequeo de manifests y dependencias, y los
tests del parser contra sobres de ambos stacks.

Pendiente en un entorno real:

1. Instalación limpia en Odoo 18 CE con `odoo-argentina-ce` y `pyafipws`.
2. Emisión de una factura T contra homologación, **incluyendo una línea con
   descuento** (el caso que antes cortaba).
3. Generación del TXT y validación con el aplicativo de AFIP, prestando atención
   al registro 02 (el del tipo de comprobante corregido) y a descripciones con
   acentos.
4. Todo el circuito en Enterprise con `l10n_ar_edi`.
5. Odoo 19 CE queda a la espera de la migración de ADHOC.
