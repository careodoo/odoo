/** @odoo-module  */
import publicWidget from 'web.public.widget';


// publicWidget.registry.AddLinePW = publicWidget.Widget.extend({
//   selector: '#servie_order_lines',
//   events: {
//     'click #add_line': '_onAddLine',
//   },
//   _onAddLine: function () {
//     const tableBody = $('#servie_order_lines_body');
//     var $new_row = $('.order_line_row').clone(true);
//     $new_row.removeClass('d-none');
//     $new_row.removeClass('order_line_row');
//     $new_row.addClass('order_cost_line');
//     $new_row.insertBefore($('.order_line_row'));
//     tableBody.append($new_row);
//     // this.lines[this.row_id] = {'product_id': this.products[0][0], 'description': '', 'quantity':''}
//     // this.row_id ++;
//     // $content.appendTo($('.products_table'));
//     console.log(this)
//   },
// });
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
