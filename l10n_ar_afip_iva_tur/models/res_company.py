from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    afip_iva_tur_agent_identification = fields.Selection(
        [
            ("C", "Compañía"),
            ("O", "Otro"),
        ],
        string="Identificación Agente IVA Tur.",
        default="C",
        help="Identificación del agente de recaudación para el Régimen de Alojamiento de Turistas "
        "Extranjeros. Normalmente 'C' (Compañía).",
    )
