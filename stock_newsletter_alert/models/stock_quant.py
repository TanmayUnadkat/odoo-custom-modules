from odoo import models


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def write(self, vals):
        result = super().write(vals)
        # Only run recovery check when the physical quantity actually changed
        if 'quantity' in vals:
            self._check_stock_recovery()
        return result

    def _check_stock_recovery(self):
        """
        After any stock quantity update, check whether products that previously
        triggered a low-stock alert have now recovered above their threshold.
        """
        recovered = self.env['product.template']
        seen_template_ids = set()

        for quant in self:
            tmpl = quant.product_id.product_tmpl_id

            # Skip duplicates within the same write batch
            if tmpl.id in seen_template_ids:
                continue
            seen_template_ids.add(tmpl.id)

            if not tmpl.stock_alert_threshold or not tmpl.low_stock_alert_sent:
                continue

            if tmpl.qty_available >= tmpl.stock_alert_threshold:
                recovered |= tmpl

        if recovered:
            self.env['product.template'].send_recovery_mailing(recovered)
