import 'package:flutter/material.dart';
import 'i18n.dart';
import '../screens/work_order_detail_screen.dart';
import '../screens/orders_screen.dart';

/// Route a backend `action_url` (e.g. `/workorder/5`, `/order/3`) to the
/// screen that shows that record. Returns true if it navigated.
///
/// The backend only emits a handful of shapes (`/workorder/<id>`,
/// `/order/<id>`, `/chat/<id>`); anything unknown is ignored gracefully so a
/// tap never throws.
bool openActionUrl(BuildContext context, String? url) {
  if (url == null || url.isEmpty) return false;
  final m = RegExp(r'/([a-z_]+)/(\d+)').firstMatch(url);
  if (m == null) return false;
  final kind = m.group(1);
  final id = int.tryParse(m.group(2) ?? '');
  if (id == null) return false;
  Widget? screen;
  switch (kind) {
    case 'workorder':
      screen = WorkOrderDetailScreen(id: id, title: tr('أمر العمل', 'Work order'));
      break;
    case 'order':
      screen = const OrdersScreen();
      break;
  }
  if (screen == null) return false;
  Navigator.push(context, MaterialPageRoute(builder: (_) => screen!));
  return true;
}
