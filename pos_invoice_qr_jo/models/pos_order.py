# -*- coding: utf-8 -*-

from odoo import models, fields, api
from werkzeug.urls import url_encode

class PosOrder(models.Model):
    _inherit = 'pos.order'
    invoice_qr_code = fields.Char(
        string='Invoice QR Code',
        related='account_move.l10n_jo_edi_qr',  # Directly link to the QR code field in the invoice
        help='QR code from the related invoice'
        
    )
    invoice_qr_code_src = fields.Char(
        string='QR Code',
        compute='_compute_l10n_jo_qr_code_src',
        # store=True,
        help='QR code from the related invoice'
    )

    @api.model
    def _load_pos_data_fields(self, config):
        fields_list = super()._load_pos_data_fields(config)
        if not fields_list:
            return fields_list
        extra_fields = ["invoice_qr_code", "invoice_qr_code_src"]
        for field_name in extra_fields:
            if field_name not in fields_list:
                fields_list.append(field_name)
        return fields_list
    @api.depends('account_move.l10n_jo_edi_qr')
    def _compute_l10n_jo_qr_code_src(self):
        for record in self:
            if not record.invoice_qr_code:
                record.invoice_qr_code_src = False
            else:
                encoded_params = url_encode({
                    'barcode_type': 'QR',
                    'value': record.invoice_qr_code,
                    'width': 200,
                    'height': 200,
                })
                record.invoice_qr_code_src = f'/report/barcode/?{encoded_params}'
    







