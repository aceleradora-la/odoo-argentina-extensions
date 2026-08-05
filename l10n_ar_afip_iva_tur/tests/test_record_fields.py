"""El exportable es de ancho fijo: cada campo tiene que ocupar exactamente lo que dice AFIP."""

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.l10n_ar_afip_iva_tur.models.afip_iva_tur_report import (
    IVA_TUR_ENCODING,
    _amount_field,
    _num_field,
    _text_field,
)


@tagged("post_install", "-at_install")
class TestRecordFields(TransactionCase):
    def test_text_field_pads_and_truncates(self):
        self.assertEqual(_text_field("AB", 5), "AB   ")
        self.assertEqual(_text_field(None, 3), "   ")
        # Antes se usaba ljust() sin recortar: una descripción larga corría todas
        # las columnas siguientes y AFIP rechazaba el archivo.
        self.assertEqual(_text_field("A" * 300, 200), "A" * 200)
        self.assertEqual(len(_text_field("A" * 300, 200)), 200)

    def test_num_field_pads_with_zeros(self):
        self.assertEqual(_num_field("77", 8, "test"), "00000077")
        self.assertEqual(_num_field(None, 4, "test"), "0000")

    def test_num_field_rejects_overflow(self):
        # Preferimos cortar la generación antes que emitir un archivo mal formado.
        with self.assertRaises(UserError):
            _num_field("123456", 3, "test")

    def test_amount_field_uses_cents(self):
        self.assertEqual(_amount_field(1210.0, 15, "test"), "000000000121000")
        self.assertEqual(_amount_field(0.1 + 0.2, 15, "test"), "000000000000030")
        self.assertEqual(len(_amount_field(1210.0, 15, "test")), 15)

    def test_accents_keep_field_width_in_bytes(self):
        """Con UTF-8 cada acento sumaba un byte extra y descolocaba el registro."""
        value = _text_field("Habitación doble ñandú", 50)
        self.assertEqual(len(value), 50)
        self.assertEqual(len(value.encode(IVA_TUR_ENCODING, errors="replace")), 50)
