# Odoo Argentina — Factura de Turismo (WSCT) e IVA Turismo

Extensiones sobre la localización argentina de Odoo para emitir **comprobantes
clase T** (Factura de Turismo, RG 3971 / web service WSCT) y generar el
**exportable del Régimen de Alojamiento de Turistas Extranjeros** (régimen 8089).

Soporta **Odoo 18.0 y 19.0**, en **Community y Enterprise**.

## Módulos

| Módulo | Edición | Descripción |
|---|---|---|
| `l10n_ar_wsct_base` | Ambas | Modelo de datos común: campos de turismo en categoría de producto, contacto e impuesto, y los tipos de documento clase T. |
| `l10n_ar_afipws_wsct` | Community | Pedido de CAE al WSCT sobre el stack de ADHOC (`l10n_ar_afipws_fe`, con `pyafipws`). |
| `l10n_ar_edi_wsct` | Enterprise | Pedido de CAE al WSCT sobre `l10n_ar_edi` (con `zeep`). |
| `l10n_ar_afip_iva_tur` | Ambas | Generación del archivo TXT de presentación de IVA Turismo. |

`l10n_ar_afipws_wsct` y `l10n_ar_edi_wsct` son **mutuamente excluyentes**:
implementan el mismo web service sobre stacks que no comparten ni los nombres de
los campos ni los de los métodos. Se instala el que corresponda a la edición.

`l10n_ar_afip_iva_tur` funciona con cualquiera de los dos: obtiene el XML del
pedido de CAE a través de `account.move._l10n_ar_iva_tur_get_afip_xml()`, que
cada uno implementa.

## Instalación

### Odoo 18 / 19 Community

Requiere el stack AFIP de ADHOC y `pyafipws`:

```
git clone -b 18.0 https://github.com/ingadhoc/odoo-argentina-ce
pip install pyafipws
```

Luego instalar `l10n_ar_afipws_wsct` (arrastra `l10n_ar_wsct_base`) y
`l10n_ar_afip_iva_tur`.

> **Odoo 19 Community:** al día de hoy ADHOC no publicó todavía la migración de
> `l10n_ar_afipws` / `l10n_ar_afipws_fe`: en la rama `19.0` esos módulos están
> marcados `installable: False`. Hasta que salga esa migración, la variante
> Community en Odoo 19 no se puede instalar. El código de este repo ya está
> preparado, la dependencia es la que falta.

### Odoo 18 / 19 Enterprise

Requiere `l10n_ar_edi` (viene con Enterprise). Instalar `l10n_ar_edi_wsct` y
`l10n_ar_afip_iva_tur`.

> `l10n_ar_edi_wsct` está escrito siguiendo el patrón de `l10n_ar_wsmtxca_ws` de
> ADHOC, pero `l10n_ar_edi` es de código cerrado y no se pudo compilar ni
> ejecutar contra la fuente real. **Probarlo en homologación antes de producción.**

## Configuración

1. **Diario de ventas:** sistema de punto de venta *"Comprobantes de Turismo -
   Web Service"*. Habilita los tipos de documento 195/196/197 clase T.
2. **Categorías de producto:** completar *Tipo de Item* y *Código de Turismo*.
3. **Impuesto de reintegro:** marcar *IVA Reintegro Turismo* en el impuesto
   correspondiente (pestaña Opciones avanzadas).
4. **Contactos:** completar *Código de Relación* y el país del turista.
5. **Diarios de banco/efectivo:** completar *Forma de pago* (pestaña Ajustes
   avanzados) para que el registro 08 del exportable salga con el medio correcto.

## Uso del exportable

Contabilidad → Informes → IVA Turismo:

1. **Crear Informe IVA Turismo** con el período.
2. **Actualizar Comprobantes** trae los comprobantes clase T del período. Un
   comprobante no puede estar en dos informes.
3. **Generar Archivo TXT** produce el archivo `F8089.<CUIT>.<AAAAMM>00.<remesa>.TXT`.
4. **Marcar como Presentado** una vez presentado ante AFIP/ARCA.

## Tests

```
odoo -d <base> -i l10n_ar_afip_iva_tur --test-enable --stop-after-init
```

Cubren el parseo de los sobres SOAP de ambos stacks y el ancho fijo de los campos
del exportable.

## Historial

Ver [`EVALUACION.md`](EVALUACION.md) para el detalle de la evaluación del código
original (versión 17.0) y de los cambios aplicados en esta migración.
