from odoo import _, fields, models


class AfipIvaTurWizard(models.TransientModel):
    _name = "afip.iva.tur.wizard"
    _description = "AFIP IVA Turismo Exportable Wizard - Generador de Reporte"

    date_from = fields.Date(
        string="Fecha Desde",
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
    )
    date_to = fields.Date(
        string="Fecha Hasta",
        required=True,
        default=lambda self: fields.Date.context_today(self),
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )

    def action_create_iva_tur_report(self):
        """Crea un nuevo afip.iva.tur.report en borrador y lo abre."""
        self.ensure_one()
        report = self.env["afip.iva.tur.report"].create(
            {
                "date_from": self.date_from,
                "date_to": self.date_to,
                "company_id": self.company_id.id,
                "state": "draft",
            }
        )

        return {
            "type": "ir.actions.act_window",
            "name": _("Reporte AFIP IVA Turismo"),
            "res_model": "afip.iva.tur.report",
            "view_mode": "form",
            "res_id": report.id,
            "target": "current",
        }
