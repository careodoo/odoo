import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// الحضور والانصراف — per-worker days/hours + all shift records.
class AttendanceScreen extends StatefulWidget {
  const AttendanceScreen({super.key});
  @override
  State<AttendanceScreen> createState() => _AttendanceScreenState();
}

class _AttendanceScreenState extends State<AttendanceScreen> {
  late Future<Map<String, dynamic>> _future;
  int _tab = 0;

  @override
  void initState() {
    super.initState();
    _future = context.read<AuthProvider>().api.clientAttendanceData();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('الحضور والانصراف', 'Attendance'))),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _future,
        builder: (_, snap) {
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final workers = (snap.data!['workers'] as List?) ?? [];
          final records = (snap.data!['records'] as List?) ?? [];
          final t = (snap.data!['totals'] as Map?) ?? {};
          return Column(children: [
            SizedBox(
              height: 92,
              child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.all(8), children: [
                _stat('🟢', '${t['present_now'] ?? 0}', tr('حاضرون الآن', 'Present now'), const Color(0xFF16A34A)),
                _stat('👥', '${t['workers'] ?? 0}', tr('عاملون', 'Workers'), const Color(0xFF6366F1)),
                _stat('🕐', '${t['total_hours'] ?? 0}', tr('إجمالي الساعات', 'Total hours'), const Color(0xFF0891B2)),
                _stat('🗂️', '${t['records'] ?? 0}', tr('السجلات', 'Records'), const Color(0xFF334155)),
              ]),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: SegmentedButton<int>(
                segments: [
                  ButtonSegment(value: 0, label: Text(tr('لكل عامل', 'Per worker'))),
                  ButtonSegment(value: 1, label: Text(tr('كل السجلات', 'All records'))),
                ],
                selected: {_tab},
                onSelectionChanged: (s) => setState(() => _tab = s.first),
              ),
            ),
            Expanded(
              child: _tab == 0
                  ? ListView.separated(
                      padding: const EdgeInsets.all(8),
                      itemCount: workers.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (_, i) {
                        final w = workers[i] as Map;
                        return ListTile(
                          title: Text('${w['name']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                          subtitle: Text('${w['job'] ?? '—'}'),
                          trailing: Text('${tr('أيام', 'days')}: ${w['days']} · ${w['hours']}${tr('س', 'h')}',
                              style: const TextStyle(fontWeight: FontWeight.w700)),
                        );
                      },
                    )
                  : ListView.separated(
                      padding: const EdgeInsets.all(8),
                      itemCount: records.length,
                      separatorBuilder: (_, __) => const Divider(height: 1),
                      itemBuilder: (_, i) {
                        final r = records[i] as Map;
                        return ListTile(
                          title: Text('${r['employee']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                          subtitle: Text('${r['facility'] ?? '—'} · ${r['check_in'] ?? ''}'),
                          trailing: r['open'] == true
                              ? const Chip(label: Text('🟢', style: TextStyle(fontSize: 12)), padding: EdgeInsets.zero)
                              : Text('${r['hours']}${tr('س', 'h')}'),
                        );
                      },
                    ),
            ),
          ]);
        },
      ),
    );
  }

  Widget _stat(String ic, String v, String l, Color c) => Container(
        width: 128,
        margin: const EdgeInsets.symmetric(horizontal: 4),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(14)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
          Text('$ic $v', style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800, color: c)),
          Text(l, style: const TextStyle(fontSize: 11, color: Colors.grey), maxLines: 1, overflow: TextOverflow.ellipsis),
        ]),
      );
}
