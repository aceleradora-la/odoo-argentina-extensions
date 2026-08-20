# l10n_ar_afip_iva_tur/models/account_move_line.py

from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    l10n_ar_iva_tur_json = fields.Text(
        string='Datos IVA Tur (JSON)',
        copy=False,
        help=(
            "Datos de estadía exigidos por ARCA para el Registro Tipo 07 del "
            "exportable F.8089 (IVA Turismo). Formato JSON con claves fijas:\n"
            '{"fecha_ingreso": "2026-06-25", "unidad": 1, "tipo_unidad": "0011", '
            '"cantidad_personas": 2, "cantidad_noches": 3, "precio_unitario": 56904.50, '
            '"cuit_hotel": "30714877093"}\n'
            "- fecha_ingreso: fecha de check-in (AAAA-MM-DD o DD/MM/AAAA).\n"
            "- unidad: cantidad de habitaciones/unidades facturadas.\n"
            "- tipo_unidad: código de la tabla Tipo Unidad de ARCA "
            "(0001 persona, 0010 single, 0011 doble, 0012 triple, 0013 cuádruple, "
            "0014 plaza, etc.).\n"
            "- cantidad_personas: obligatorio salvo tipo_unidad 0014 (plaza).\n"
            "- cantidad_noches: admite decimales.\n"
            "- precio_unitario: por noche, SIN IVA.\n"
            "- cuit_hotel: sólo para Relación Emisor-Receptor 04/05/06 (agencias).\n"
            "Obligatorio para ítems con Código TUR 0001/0002; opcional (todo o nada) "
            "para 0005; no debe cargarse para ítems 91/97/99 ni Código TUR 0020/0021."
        ),
    )
