{
    'name': 'POS Invoice QR Code Jordan',
    'version': '19.0.1.0.0',
    'depends': ['point_of_sale', 'account', 'l10n_jo_edi'],
    'data': [],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_invoice_qr_jo/static/src/css/**/*',
            'pos_invoice_qr_jo/static/src/overrides/order_receipt/**/*',
            'pos_invoice_qr_jo/static/src/overrides/pos_order_line/**/*',
            'pos_invoice_qr_jo/static/src/overrides/payment_screen/**/*',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'summary': 'Display Jordan EDI QR code on POS receipts when invoice is created',
    'description': """
This module adds invoice functionality to POS payment screen and displays 
the Jordan EDI QR code on receipts when an invoice is created.

Features:
- Invoice button in payment screen
- Automatic invoice creation
- Display invoice QR code on receipt11
    """,
}
