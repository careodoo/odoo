/** @odoo-module  */
import publicWidget from 'web.public.widget';
import { qweb } from "web.core";


publicWidget.registry.AddLinePW = publicWidget.Widget.extend({
  selector: '#servie_order_lines',
  events: {
    'click #add_line': '_onAddLine',
  },
  _onAddLine: function () {
    const tableBody = $('#servie_order_lines_body');
    var $new_row = $('.order_line_row').clone(true);
    $new_row.removeClass('d-none');
    $new_row.removeClass('order_line_row');
    $new_row.addClass('order_cost_line');
    $new_row.insertBefore($('.order_line_row'));
    tableBody.append($new_row);
    // this.lines[this.row_id] = {'product_id': this.products[0][0], 'description': '', 'quantity':''}
    // this.row_id ++;
    // $content.appendTo($('.products_table'));
    console.log(this)
  },
});
