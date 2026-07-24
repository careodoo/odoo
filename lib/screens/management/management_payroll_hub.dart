import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'management_home.dart' show Mgmt;
import 'management_list.dart';

/// «الرواتب» — a parent hub grouping the payroll sub-systems (payslips, payroll
/// batches) each opening its full professional list with workflow + reports.
class ManagementPayrollHub extends StatefulWidget {
  const ManagementPayrollHub({super.key, this.accent = const Color(0xFF7C3AED)});
  final Color accent;
  @override
  State<ManagementPayrollHub> createState() => _ManagementPayrollHubState();
}

class _ManagementPayrollHubState extends State<ManagementPayrollHub> {
  Map<String, dynamic> _counts = {};

  // (key, icon, ar, en, color)
  static const _subs = [
    ('payroll', '💵', 'مسيّرات الرواتب', 'Payroll batches', 0xFF7C3AED),
    ('payslips', '🧾', 'قسائم الرواتب', 'Payslips', 0xFF0891B2),
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final b = await context.read<AuthProvider>().api.managementEmpModules();
      // reuse: payslips/payroll counts come from a lightweight apps call instead
      final apps = await context.read<AuthProvider>().api.managementApps();
      final m = <String, dynamic>{};
      for (final a in apps) {
        m['${(a as Map)['key']}'] = a;
      }
      if (mounted) setState(() => _counts = {...b, ...m});
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Mgmt.bg,
      appBar: AppBar(backgroundColor: widget.accent, foregroundColor: Colors.white,
          title: Text('💵 ${tr('الرواتب', 'Payroll')}')),
      body: ListView(padding: const EdgeInsets.all(14), children: [
        Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            gradient: LinearGradient(colors: [widget.accent, widget.accent.withValues(alpha: 0.7)],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(18),
          ),
          child: Row(children: [
            const Text('💵', style: TextStyle(fontSize: 30)),
            const SizedBox(width: 12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(tr('منظومة الرواتب', 'Payroll suite'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 17)),
              Text(tr('المسيّرات والقسائم والتقارير', 'Batches, payslips & reports'),
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12)),
            ])),
          ]),
        ),
        const SizedBox(height: 14),
        for (final s in _subs) _subTile(s),
      ]),
    );
  }

  Widget _subTile((String, String, String, String, int) s) {
    final c = Color(s.$5);
    final entry = _counts[s.$1] as Map?;
    final count = entry?['count'];
    final pending = (entry?['pending'] ?? 0) as int;
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Material(
        color: Colors.white, borderRadius: BorderRadius.circular(16),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ManagementListScreen(
              appKey: s.$1, title: gLang == 'en' ? s.$4 : s.$3, icon: s.$2, accent: c))),
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.black12)),
            child: Row(children: [
              Container(width: 46, height: 46, alignment: Alignment.center,
                  decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(13)),
                  child: Text(s.$2, style: const TextStyle(fontSize: 22))),
              const SizedBox(width: 13),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(gLang == 'en' ? s.$4 : s.$3, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: Mgmt.ink)),
                if (count != null) Text('${tr('العدد', 'Records')}: $count', style: const TextStyle(color: Mgmt.slate, fontSize: 11.5)),
              ])),
              if (pending > 0) Container(
                margin: const EdgeInsetsDirectional.only(end: 8),
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(color: const Color(0xFFE11D48), borderRadius: BorderRadius.circular(10)),
                child: Text('$pending', style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w900))),
              const Icon(Icons.chevron_left_rounded, color: Mgmt.slate),
            ]),
          ),
        ),
      ),
    );
  }
}
