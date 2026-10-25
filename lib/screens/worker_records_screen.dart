import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// «سجلات العمال» — شاشة مجمّعة على مستوى مشاريع مدير المشروع:
/// فلتر فترة زمنية، بطاقات إحصائيات لكل نوع طلب (تتغيّر بالفترة)، وقائمة
/// بكل السجلات في تلك الفترة عبر كل أنواع إجراءات العمال.
/// تطابق شاشة البوابة /my/pm/worker-records.
class WorkerRecordsScreen extends StatefulWidget {
  const WorkerRecordsScreen({super.key});
  @override
  State<WorkerRecordsScreen> createState() => _WorkerRecordsScreenState();
}

const _navy = Color(0xFF0E3A5F);
const _bg = Color(0xFFF4F6FA);

class _WorkerRecordsScreenState extends State<WorkerRecordsScreen> {
  Future<Map<String, dynamic>>? _future;
  DateTime _from = DateTime.now().subtract(const Duration(days: 30));
  DateTime _to = DateTime.now();
  String? _activeKey; // فلتر عرض نوع واحد عند الضغط على بطاقة إحصائية

  @override
  void initState() {
    super.initState();
    _reload();
  }

  String _fmt(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  void _reload() {
    final api = context.read<AuthProvider>().api;
    setState(() {
      _future = api.pmsWorkerRecords(dateFrom: _fmt(_from), dateTo: _fmt(_to));
    });
  }

  Future<void> _pick(bool isFrom) async {
    final init = isFrom ? _from : _to;
    final d = await showDatePicker(
      context: context,
      initialDate: init,
      firstDate: DateTime(2020),
      lastDate: DateTime(2035),
    );
    if (d == null) return;
    setState(() {
      if (isFrom) {
        _from = d;
      } else {
        _to = d;
      }
      if (_from.isAfter(_to)) {
        final t = _from;
        _from = _to;
        _to = t;
      }
    });
    _reload();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _navy,
        foregroundColor: Colors.white,
        title: Text(tr('سجلات العمال', 'Worker records')),
      ),
      body: RefreshIndicator(
        color: _navy,
        onRefresh: () async => _reload(),
        child: FutureBuilder<Map<String, dynamic>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: Padding(
                  padding: EdgeInsets.only(top: 80), child: CircularProgressIndicator()));
            }
            if (snap.hasError) {
              return ListView(children: [
                _dateBar(),
                Padding(
                  padding: const EdgeInsets.all(24),
                  child: Center(child: Text(
                      tr('تعذّر تحميل السجلات', 'Could not load records'),
                      style: const TextStyle(color: Colors.red))),
                ),
              ]);
            }
            final d = snap.data ?? const {};
            final stats = List<Map<String, dynamic>>.from(
                (d['stats'] as List? ?? []).map((e) => Map<String, dynamic>.from(e)));
            final rows = List<Map<String, dynamic>>.from(
                (d['rows'] as List? ?? []).map((e) => Map<String, dynamic>.from(e)));
            final total = (d['total'] as num?)?.toInt() ?? 0;
            final workerCount = (d['worker_count'] as num?)?.toInt() ?? 0;
            final shown = _activeKey == null
                ? rows
                : rows.where((r) => r['proc_key'] == _activeKey).toList();

            return ListView(
              padding: const EdgeInsets.only(bottom: 28),
              children: [
                _dateBar(),
                _summary(total, workerCount, stats.length),
                _statsGrid(stats),
                _recordsHeader(shown.length),
                if (shown.isEmpty)
                  Padding(
                    padding: const EdgeInsets.all(30),
                    child: Center(child: Text(
                        tr('لا سجلات في هذه الفترة', 'No records in this period'),
                        style: const TextStyle(color: Colors.black54))),
                  )
                else
                  ...shown.map(_recordTile),
              ],
            );
          },
        ),
      ),
    );
  }

  // شريط فلتر الفترة
  Widget _dateBar() {
    Widget box(String label, DateTime v, bool isFrom) => Expanded(
          child: InkWell(
            onTap: () => _pick(isFrom),
            borderRadius: BorderRadius.circular(10),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFFCBD5E1)),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label, style: const TextStyle(
                      fontSize: 11, color: Colors.black54, fontWeight: FontWeight.w600)),
                  const SizedBox(height: 3),
                  Row(children: [
                    const Icon(Icons.calendar_today_rounded, size: 14, color: _navy),
                    const SizedBox(width: 6),
                    Text(_fmt(v), style: const TextStyle(
                        fontSize: 14, fontWeight: FontWeight.w700, color: _navy)),
                  ]),
                ],
              ),
            ),
          ),
        );
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 6),
      child: Row(children: [
        box(tr('من تاريخ', 'From'), _from, true),
        const SizedBox(width: 10),
        box(tr('إلى تاريخ', 'To'), _to, false),
      ]),
    );
  }

  Widget _summary(int total, int workers, int types) {
    Widget chip(IconData ic, String val, String label, Color c) => Expanded(
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 4),
            padding: const EdgeInsets.symmetric(vertical: 12),
            decoration: BoxDecoration(
              color: c.withOpacity(.10),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: c.withOpacity(.35)),
            ),
            child: Column(children: [
              Icon(ic, color: c, size: 20),
              const SizedBox(height: 5),
              Text('$val', style: TextStyle(
                  fontSize: 20, fontWeight: FontWeight.w800, color: c)),
              Text(label, style: const TextStyle(
                  fontSize: 11, color: Colors.black54, fontWeight: FontWeight.w600)),
            ]),
          ),
        );
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 6, 12, 2),
      child: Row(children: [
        chip(Icons.description_rounded, '$total', tr('إجمالي السجلات', 'Total'), _navy),
        chip(Icons.groups_rounded, '$workers', tr('العمال', 'Workers'), const Color(0xFF0E7C86)),
        chip(Icons.category_rounded, '$types', tr('الأنواع', 'Types'), const Color(0xFF7C3AED)),
      ]),
    );
  }

  // شبكة بطاقات الإحصائيات لكل نوع — الضغط يفلتر القائمة
  Widget _statsGrid(List<Map<String, dynamic>> stats) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(10, 10, 10, 2),
      child: Wrap(
        spacing: 8,
        runSpacing: 8,
        children: stats.map((s) {
          final key = s['key'] as String?;
          final cnt = (s['count'] as num?)?.toInt() ?? 0;
          final active = _activeKey == key;
          return InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: () => setState(() => _activeKey = active ? null : key),
            child: Container(
              width: (MediaQuery.of(context).size.width - 20 - 16) / 3,
              padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 6),
              decoration: BoxDecoration(
                color: active ? _navy : Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                    color: active ? _navy : const Color(0xFFE2E8F0)),
                boxShadow: active
                    ? null
                    : const [BoxShadow(color: Color(0x0F000000), blurRadius: 4, offset: Offset(0, 2))],
              ),
              child: Column(children: [
                Text('${s['icon'] ?? '📋'}', style: const TextStyle(fontSize: 20)),
                const SizedBox(height: 4),
                Text('$cnt', style: TextStyle(
                    fontSize: 18, fontWeight: FontWeight.w800,
                    color: active ? Colors.white : _navy)),
                const SizedBox(height: 2),
                Text('${s['label'] ?? ''}',
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    textAlign: TextAlign.center,
                    style: TextStyle(
                        fontSize: 11, fontWeight: FontWeight.w600,
                        color: active ? Colors.white70 : Colors.black87)),
              ]),
            ),
          );
        }).toList(),
      ),
    );
  }

  Widget _recordsHeader(int n) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 18, 16, 6),
      child: Row(children: [
        const Icon(Icons.list_alt_rounded, size: 18, color: _navy),
        const SizedBox(width: 8),
        Text(tr('السجلات', 'Records'),
            style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800, color: _navy)),
        const SizedBox(width: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 2),
          decoration: BoxDecoration(
              color: _navy.withOpacity(.10), borderRadius: BorderRadius.circular(20)),
          child: Text('$n', style: const TextStyle(
              fontSize: 12, fontWeight: FontWeight.w700, color: _navy)),
        ),
        if (_activeKey != null) ...[
          const Spacer(),
          TextButton.icon(
            onPressed: () => setState(() => _activeKey = null),
            icon: const Icon(Icons.clear_rounded, size: 16),
            label: Text(tr('إلغاء الفلتر', 'Clear')),
            style: TextButton.styleFrom(foregroundColor: _navy),
          ),
        ],
      ]),
    );
  }

  Widget _recordTile(Map<String, dynamic> r) {
    final state = (r['state_label'] ?? '').toString();
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 0, 12, 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: const [BoxShadow(color: Color(0x0F000000), blurRadius: 4, offset: Offset(0, 2))],
      ),
      child: Row(children: [
        Container(
          width: 40, height: 40,
          alignment: Alignment.center,
          decoration: BoxDecoration(
              color: _navy.withOpacity(.08), borderRadius: BorderRadius.circular(10)),
          child: Text('${r['icon'] ?? '📋'}', style: const TextStyle(fontSize: 20)),
        ),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('${r['emp'] ?? '—'}',
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      fontSize: 14, fontWeight: FontWeight.w700, color: Colors.black87)),
              const SizedBox(height: 2),
              Row(children: [
                Text('${r['proc_label'] ?? ''}',
                    style: const TextStyle(fontSize: 12.5, color: _navy, fontWeight: FontWeight.w600)),
                const Text('  ·  ', style: TextStyle(color: Colors.black26)),
                Text('${r['date'] ?? ''}',
                    style: const TextStyle(fontSize: 12, color: Colors.black54)),
              ]),
            ],
          ),
        ),
        if (state.isNotEmpty)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
            decoration: BoxDecoration(
                color: const Color(0xFFEFF3F9), borderRadius: BorderRadius.circular(20)),
            child: Text(state, style: const TextStyle(
                fontSize: 11, fontWeight: FontWeight.w600, color: _navy)),
          ),
      ]),
    );
  }
}
