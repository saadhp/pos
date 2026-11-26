# Copyright 2026 Saad Elbahi
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "POS Payment Method Live Assign",
    "summary": "Assign non-cash payment methods to POS configs during open sessions",
    "version": "18.0.1.0.0",
    "category": "Sales/Point of Sale",
    "website": "https://github.com/OCA/pos",
    "author": "Saad Elbahi, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "development_status": "Beta",
    "maintainers": ["saadhp"],
    "depends": ["point_of_sale"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/pos_live_payment_wizard_views.xml",
        "views/pos_payment_method_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_payment_method_live_assign/static/src/app/pos_live_payment_sync.esm.js",
        ],
    },
    "installable": True,
}
