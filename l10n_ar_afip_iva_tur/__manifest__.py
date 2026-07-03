# l10n_ar_afip_iva_tur/__manifest__.py
{
    'name': 'Argentina - AFIP IVA Turismo Exportable',
    'version': '19.0.1.0.0',
    'category': 'Localization/Accounting',
    'summary': 'Generación del exportable para el Régimen de Alojamiento de Turistas Extranjeros (IVA Turismo) de AFIP.',
    'author': 'aceleradora.la',
    'website': 'www.aceleradora.la',
    'depends': [
        'account',
        'l10n_ar',
        'l10n_ar_afipws_fe',
        'l10n_latam_base',
        'l10n_latam_invoice_document',
        'base',
        'mail', # <-- ¡AÑADE ESTA LÍNEA!
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/res_company_views.xml',
        'views/afip_iva_tur_report_views.xml',
        'views/account_journal_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'AGPL-3',
    'images': ['static/description/icon.png'],
}