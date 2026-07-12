import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/theme.dart';
import '../core/widgets.dart';
import 'workorders_screen.dart';
import 'scan_screen.dart';
import 'security_home.dart';
import 'supervisor_screen.dart';

/// Role router: the same app opens a different face depending on who logs in.
/// A security guard lands on the security command screen; a cleaner/agri worker
/// on the task-and-scan worker screen.
class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final profile = context.watch<AuthProvider>().profile!;
    if (profile.role == 'security') return const SecurityHome();
    return const WorkerHome();
  }
}

class WorkerHome extends StatelessWidget {
  const WorkerHome({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final p = auth.profile!;
    final st = ServiceTheme.of(p.role);
    return Scaffold(
      appBar: AppBar(
        title: Text('${st.icon}  ${st.label}'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () => context.read<AuthProvider>().logout(),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(18),
              child: Row(
                children: [
                  CircleAvatar(radius: 26, child: Text(p.name.characters.first)),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(p.name, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                        Text('مهامي المفتوحة: ${p.openWorkOrders}',
                            style: TextStyle(color: Theme.of(context).colorScheme.outline)),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 12),
          MyStatsRow(counts: p.counts),
          const SizedBox(height: 12),
          _BigAction(
            icon: Icons.qr_code_scanner,
            label: 'امسح رمز الموقع — إثبات الحضور',
            onTap: () => Navigator.push(context,
                MaterialPageRoute(builder: (_) => const ScanScreen())),
          ),
          _BigAction(
            icon: Icons.assignment_outlined,
            label: 'أوامر العمل الخاصة بي',
            onTap: () => Navigator.push(context,
                MaterialPageRoute(builder: (_) => const WorkOrdersScreen())),
          ),
          if (p.isSupervisor)
            _BigAction(
              icon: Icons.dashboard_customize,
              label: '🧭 لوحة المشرف — إحصائيات وإسناد',
              onTap: () => Navigator.push(context,
                  MaterialPageRoute(builder: (_) => const SupervisorScreen())),
            ),
        ],
      ),
    );
  }
}

class _BigAction extends StatelessWidget {
  const _BigAction({required this.icon, required this.label, required this.onTap});
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(18),
          child: Row(
            children: [
              Icon(icon, size: 30, color: cs.primary),
              const SizedBox(width: 16),
              Expanded(child: Text(label, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700))),
              const Icon(Icons.chevron_left),
            ],
          ),
        ),
      ),
    );
  }
}
