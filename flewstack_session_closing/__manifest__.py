{
    'name': 'Flewstack POS Session Closing',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Add Handed Over stage and clear-cash flow for POS sessions',
    'depends': ['point_of_sale', 'account', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_journal_views.xml',
        'views/account_move_views.xml',
        'views/hr_employee_views.xml',
        'views/pos_session_views.xml',
        'wizard/account_move_transfer_cash_views.xml',
        'wizard/pos_session_clear_cash_views.xml',
    ],
    'application': False,
    'license': 'LGPL-3',
}
