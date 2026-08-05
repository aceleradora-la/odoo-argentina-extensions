from odoo import _, api, models

# Sistema de punto de venta AFIP/ARCA y web service que agrega este modulo.
WSCT_POS_SYSTEM = "WSCT"
WSCT_AFIP_WS = "wsct"

# Comprobantes de turismo clase T: factura, nota de debito y nota de credito.
WSCT_DOCUMENT_CODES = ["195", "196", "197"]


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_journal_letter(self, counterpart_partner=False):
        self.ensure_one()
        if self.afip_ws == WSCT_AFIP_WS:
            return ["T"]
        return super()._get_journal_letter(counterpart_partner)

    def _get_codes_per_journal_type(self, afip_pos_system):
        # Se decide por el argumento y no por self.afip_ws (que es un campo calculado):
        # l10n_ar llama a este metodo con el sistema de PdV que se esta configurando,
        # que puede no coincidir todavia con el valor almacenado.
        if afip_pos_system == WSCT_POS_SYSTEM:
            return [("code", "in", WSCT_DOCUMENT_CODES)]
        return super()._get_codes_per_journal_type(afip_pos_system)

    def _get_l10n_ar_afip_pos_types_selection(self):
        res = super()._get_l10n_ar_afip_pos_types_selection()
        res.insert(0, (WSCT_POS_SYSTEM, _("Comprobantes de Turismo - Web Service")))
        return res

    def _get_afip_ws(self):
        res = super()._get_afip_ws()
        res.insert(0, (WSCT_AFIP_WS, _("Turismo - with detail - RG3971 (WSCT)")))
        return res

    @api.model
    def _get_type_mapping(self):
        res = super()._get_type_mapping()
        res[WSCT_POS_SYSTEM] = WSCT_AFIP_WS
        return res
