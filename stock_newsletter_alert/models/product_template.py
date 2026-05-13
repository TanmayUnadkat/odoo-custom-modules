from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    stock_alert_threshold = fields.Float(
        string='Stock Alert Threshold',
        default=0.0,
        help=(
            'A newsletter alert is sent to all subscribers when available qty '
            'falls below this value. Set to 0 to disable alerts for this product.'
        ),
    )
    low_stock_alert_sent = fields.Boolean(
        string='Low Stock Alert Sent',
        default=False,
        copy=False,
        help=(
            'Managed automatically by the system.\n'
            'True  → a low-stock alert has been sent; waiting for stock to recover.\n'
            'False → no pending alert; cron will check again on next run.'
        ),
    )

    @api.model
    def _get_stock_alert_mailing_list(self):
        """Return the pre-defined 'Stock Alerts' mailing list record."""
        return self.env.ref(
            'stock_newsletter_alert.mailing_list_stock_alerts',
            raise_if_not_found=False,
        )

    @api.model
    def _build_product_table(self, products, qty_color):
        """
        Build an HTML <table> listing product name, current qty, and threshold.
        qty_color  — hex colour applied to the qty cell (red for low, green for recovered).
        """
        rows = ''.join(
            f"""
            <tr>
                <td style="padding:10px 12px;border-bottom:1px solid #eee;">
                    {p.name}
                </td>
                <td style="padding:10px 12px;border-bottom:1px solid #eee;
                            text-align:center;color:{qty_color};font-weight:bold;">
                    {p.qty_available:.1f}
                </td>
                <td style="padding:10px 12px;border-bottom:1px solid #eee;
                            text-align:center;color:#6c757d;">
                    {p.stock_alert_threshold:.1f}
                </td>
            </tr>"""
            for p in products
        )
        return f"""
        <table style="width:100%;border-collapse:collapse;margin:20px 0;font-size:14px;">
            <thead>
                <tr style="background:#f8f9fa;">
                    <th style="padding:10px 12px;text-align:left;
                                border-bottom:2px solid #dee2e6;">Product</th>
                    <th style="padding:10px 12px;text-align:center;
                                border-bottom:2px solid #dee2e6;">Current Qty</th>
                    <th style="padding:10px 12px;text-align:center;
                                border-bottom:2px solid #dee2e6;">Threshold</th>
                </tr>
            </thead>
            <tbody>{rows}</tbody>
        </table>"""

    @api.model
    def _send_stock_mailing(self, subject, body_html):
        """
        Create a mailing.mailing record and send it to the Stock Alerts list.
        """
        mailing_list = self._get_stock_alert_mailing_list()
        if not mailing_list:
            return

        # Resolve the mailing.contact model id for mailing_model_id
        mailing_contact_model = self.env['ir.model'].search(
            [('model', '=', 'mailing.contact')], limit=1
        )
        if not mailing_contact_model:
            return

        mailing = self.env['mailing.mailing'].sudo().create({
            'subject': subject,
            'body_html': body_html,
            'mailing_model_id': mailing_contact_model.id,
            'contact_list_ids': [(4, mailing_list.id)],
            'mailing_type': 'mail',
        })

        mailing.action_send_mail() # will send mail to its subscribers

    #  Cron — Low Stock Alert                                             #
    @api.model
    def run_low_stock_cron(self):
        """
        Called daily by the scheduled action.
        Finds all products that:
          - have a threshold set (> 0)
          - have NOT already had an alert sent
          - are currently below their threshold
        Sends ONE combined email to every subscriber on the mailing list.
        Sets low_stock_alert_sent = True so we don't spam on every run.
        """
        templates = self.search([
            ('stock_alert_threshold', '>', 0),
            ('low_stock_alert_sent', '=', False),
        ])

        low_stock = templates.filtered(
            lambda p: p.qty_available < p.stock_alert_threshold
        )

        if not low_stock:
            return

        table = self._build_product_table(low_stock, '#e74c3c')

        body_html = f"""
        <div style="font-family:Arial,sans-serif;max-width:620px;
                    margin:0 auto;padding:24px;">

            <h2 style="color:#e74c3c;border-bottom:2px solid #e74c3c;
                        padding-bottom:10px;margin-top:0;">
                &#9888; Low Stock Alert
            </h2>

            <p style="margin-top:0;">
                The following products are currently <strong>low in stock</strong>
                on our store. Current website availability is listed below:
            </p>

            {table}

            <p>Visit our shop to check availability updates.</p>

        </div>"""

        self._send_stock_mailing(
            subject='Low Stock Alert: Products Running Low',
            body_html=body_html,
        )

        # Flag products so we don't re-alert until stock recovers
        low_stock.write({'low_stock_alert_sent': True})

    #  Recovery Alert (called from stock_quant override)                  #
    @api.model
    def send_recovery_mailing(self, recovered_products):
        """
        Send ONE combined 'back in stock' email to all subscribers.
        Resets low_stock_alert_sent so the cron cycle can repeat if stock drops again.
        """
        table = self._build_product_table(recovered_products, '#28a745')

        body_html = f"""
        <div style="font-family:Arial,sans-serif;max-width:620px;
                    margin:0 auto;padding:24px;">

            <h2 style="color:#28a745;border-bottom:2px solid #28a745;
                        padding-bottom:10px;margin-top:0;">
                &#9989; Back In Stock
            </h2>

            <p style="margin-top:0;">
                Great news! The following products are now
                <strong>back above the stock threshold</strong> on our store:
            </p>

            {table}

            <p>Visit our shop to check availability updates.</p>

        </div>"""

        self._send_stock_mailing(
            subject='Back In Stock: Products Available Again',
            body_html=body_html,
        )

        # Reset flag so the next stock drop will trigger a fresh alert
        recovered_products.write({'low_stock_alert_sent': False})
