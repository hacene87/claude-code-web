# -*- coding: utf-8 -*-
{
    'name': 'Partner Fax',
    'version': '17.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Add fax field to partner',
    'description': """
Partner Fax Field
=================
This module adds a fax number field to the partner (contact) form.

Features:
---------
* Adds a fax field to res.partner model
* Displays fax field in partner form view
* Displays fax field in partner tree view
    """,
    'author': 'Hacene',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'views/res_partner_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
