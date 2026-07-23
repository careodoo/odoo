import 'package:flutter/material.dart';
import 'i18n.dart';
import '../screens/work_order_detail_screen.dart';
import '../screens/orders_screen.dart';
import '../screens/pms/pms_tasks.dart';
import '../screens/pms/pms_employee_file.dart';

/// Route a backend `action_url` (e.g. `/workorder/5`, `/pms/task/3`,
/// `/pms/employee/9`) to the screen that shows that record. Returns true if it
/// navigated. Unknown shapes are ignored gracefully so a tap never throws.
bool openActionUrl(BuildContext context, String? url) {
  if (url == null || url.isEmpty) return false;
  // Match the LAST `/word/number` in the path, so `/pms/task/5` → (task, 5)
  // and `/pms/employee/9` → (employee, 9) resolve to the leaf record.
  final matches = RegExp(r'/([a-z_]+)/(\d+)').allMatches(url).toList();
  if (matches.isEmpty) return false;
  final m = matches.last;
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
    case 'task':
      screen = PmsTaskDetail(taskId: id);
      break;
    case 'employee':
      screen = PmsEmployeeFileScreen(employeeId: id, name: tr('ملف العامل', 'Employee'));
      break;
  }
  if (screen == null) return false;
  Navigator.push(context, MaterialPageRoute(builder: (_) => screen!));
  return true;
}
