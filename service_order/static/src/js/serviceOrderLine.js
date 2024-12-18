/** @odoo-module  */

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.PrintReport = publicWidget.Widget.extend({
  selector: '#print_list_report',
  events: {
    'click #print_report_btn': '_onAddLine',
  },
  _onAddLine: function () {
    console.log(this)
    const dateFrom = $('#date_from').val();
    const dateTo = $('#date_to').val();
    window.location.href = `/service_order/print?date_from=${dateFrom}&date_to=${dateTo}`;
  },
});
