import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// جدولة الأعمال — recurring task schedules with compliance.
class SchedulesScreen extends StatefulWidget {
  const SchedulesScreen({super.key});
  @override
  State<SchedulesScreen> createState() => _SchedulesScreenState();
}

class _SchedulesScreenState extends State<SchedulesScreen> {
  late Future<List<dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<AuthProvider>().api.clientSchedules();
  }

  Color _cc(num c) => c >= 90 ? const Color(0xFF16A34A) : c >= 70 ? const Color(0xFFF59E0B) : const Color(0xFFE11D48);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('جدولة الأعمال', 'Work schedules'))),
      body: FutureBuilder<List<dynamic>>(
        future: _future,
        builder: (_, snap) {
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final s = snap.data!;
          if (s.isEmpty) return Center(child: Text(tr('لا جداول عمل بعد', 'No schedules yet')));
          return ListView.builder(
            padding: const EdgeInsets.all(12),
            itemCount: s.length,
            itemBuilder: (_, i) {
              final x = s[i] as Map;
              final comp = (x['compliance'] as num?) ?? 0;
              return Card(
                child: Padding(
                  padding: const EdgeInsets.all(14),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      Expanded(child: Text('${x['name']}', style: const TextStyle(fontWeight: FontWeight.w800))),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 3),
                        decoration: BoxDecoration(color: _cc(comp).withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
                        child: Text('$comp%', style: TextStyle(color: _cc(comp), fontWeight: FontWeight.w800)),
                      ),
                    ]),
                    const SizedBox(height: 4),
                    Text('📍 ${x['location'] ?? ''} · 👤 ${x['employee'] ?? '—'}',
                        style: const TextStyle(color: Colors.grey, fontSize: 12)),
                    const SizedBox(height: 8),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(6),
                      child: LinearProgressIndicator(value: comp / 100, minHeight: 8, color: _cc(comp), backgroundColor: const Color(0xFFEEF2F7)),
                    ),
                    const SizedBox(height: 8),
                    Row(children: [
                      _chip('✅ ${x['done'] ?? 0}', const Color(0xFF16A34A)),
                      const SizedBox(width: 6),
                      _chip('⏰ ${x['late'] ?? 0}', const Color(0xFFF59E0B)),
                      const SizedBox(width: 6),
                      _chip('🚫 ${x['missed'] ?? 0}', const Color(0xFFE11D48)),
                      const Spacer(),
                      Text('${tr('كل', 'every')} ${x['every_minutes']}${tr('د', 'm')}', style: const TextStyle(fontSize: 12, color: Colors.grey)),
                    ]),
                  ]),
                ),
              );
            },
          );
        },
      ),
    );
  }

  Widget _chip(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(20)),
        child: Text(t, style: TextStyle(color: c, fontSize: 12, fontWeight: FontWeight.w700)),
      );
}
