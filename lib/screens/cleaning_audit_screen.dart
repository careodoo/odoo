import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';

const _navy = Color(0xFF0E3A5F);
const _sky = Color(0xFF0EA5E9);

Color _scoreColor(num s) => s >= 85
    ? const Color(0xFF16A34A)
    : (s >= 70 ? const Color(0xFF0891B2) : (s >= 60 ? const Color(0xFFF59E0B) : const Color(0xFFE5484D)));

/// تدقيق النظافة — a proper audit register: average score, pass/fail counts,
/// filters and search, and every audit opening its full checklist item by item
/// with the note behind each failure and the client's acknowledgement.
class CleaningAuditScreen extends StatefulWidget {
  const CleaningAuditScreen({super.key});
  @override
  State<CleaningAuditScreen> createState() => _CleaningAuditScreenState();
}

class _CleaningAuditScreenState extends State<CleaningAuditScreen> {
  Future<List<dynamic>>? _future;
  String _filter = 'all';
  String _q = '';

  static const _filters = [
    ('all', 'الكل', 'All'),
    ('failed', 'بها مخالفات', 'With failures'),
    ('passed', 'مطابقة', 'Clean'),
    ('disputed', 'معترض عليها', 'Disputed'),
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => setState(() =>
      _future = context.read<AuthProvider>().api.serviceList('cleaning/audits'));

  List<Map> _apply(List<dynamic> all) {
    var list = all.cast<Map>();
    switch (_filter) {
      case 'failed': list = list.where((a) => (numOf(a['fail_count'], 0)) > 0).toList(); break;
      case 'passed': list = list.where((a) => (numOf(a['fail_count'], 0)) == 0).toList(); break;
      case 'disputed': list = list.where((a) => a['client_ack'] == 'disputed').toList(); break;
    }
    if (_q.isNotEmpty) {
      final q = _q.toLowerCase();
      list = list.where((a) =>
          '${a['name']} ${a['facility'] ?? ''} ${a['location'] ?? ''} ${a['auditor'] ?? ''}'
              .toLowerCase().contains(q)).toList();
    }
    return list;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      appBar: AppBar(
        backgroundColor: _sky, foregroundColor: Colors.white,
        title: Text(tr('تدقيق النظافة', 'Cleaning audits'), style: const TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: RefreshIndicator(
        color: _sky,
        onRefresh: () async => _load(),
        child: FutureBuilder<List<dynamic>>(
          future: _future,
          builder: (_, snap) {
            if (!snap.hasData) return const Center(child: CircularProgressIndicator(color: _sky));
            final all = snap.data!;
            final shown = _apply(all);
            return Column(children: [
              _stats(all.cast<Map>()),
              _search(),
              _chips(),
              Expanded(child: shown.isEmpty
                  ? _empty(all.isEmpty
                      ? tr('لا عمليات تدقيق بعد', 'No audits yet')
                      : tr('لا نتائج في هذا التصنيف', 'Nothing in this filter'))
                  : ListView.builder(
                      padding: const EdgeInsets.fromLTRB(12, 4, 12, 20),
                      itemCount: shown.length,
                      itemBuilder: (_, i) => _card(shown[i]),
                    )),
            ]);
          },
        ),
      ),
    );
  }

  Widget _stats(List<Map> all) {
    final n = all.length;
    final avg = n == 0 ? 0.0 : all.fold<double>(0, (s, a) => s + (dblOf(a['score'], 0.0))) / n;
    final fails = all.fold<int>(0, (s, a) => s + ((numOf(a['fail_count'], 0)).toInt()));
    final clean = all.where((a) => (numOf(a['fail_count'], 0)) == 0).length;
    final disputed = all.where((a) => a['client_ack'] == 'disputed').length;
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 10, 12, 2),
      padding: const EdgeInsets.symmetric(vertical: 13, horizontal: 8),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.grey.shade200)),
      child: Row(children: [
        // average score as the headline
        Container(
          width: 58, height: 58, alignment: Alignment.center,
          decoration: BoxDecoration(color: _scoreColor(avg).withValues(alpha: 0.12), shape: BoxShape.circle,
              border: Border.all(color: _scoreColor(avg).withValues(alpha: 0.4), width: 2)),
          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            Text(avg.toStringAsFixed(0), style: TextStyle(color: _scoreColor(avg), fontSize: 18, fontWeight: FontWeight.w900, height: 1)),
            Text('%', style: TextStyle(color: _scoreColor(avg), fontSize: 9, fontWeight: FontWeight.w800)),
          ]),
        ),
        const SizedBox(width: 6),
        _cell('$n', tr('تدقيق', 'Audits'), _navy),
        _cell('$clean', tr('مطابقة', 'Clean'), const Color(0xFF16A34A)),
        _cell('$fails', tr('مخالفات', 'Failures'), const Color(0xFFE5484D)),
        _cell('$disputed', tr('اعتراضات', 'Disputed'), const Color(0xFFF59E0B)),
      ]),
    );
  }

  Widget _cell(String v, String l, Color c) => Expanded(child: Column(children: [
        Text(v, style: TextStyle(color: c, fontSize: 16, fontWeight: FontWeight.w900)),
        Text(l, textAlign: TextAlign.center, style: TextStyle(fontSize: 9.5, color: Colors.grey.shade600, fontWeight: FontWeight.w700)),
      ]));

  Widget _search() => Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
        child: TextField(
          onChanged: (v) => setState(() => _q = v),
          decoration: InputDecoration(
            hintText: tr('بحث بالمرفق أو الموقع أو المدقّق…', 'Search facility, location or auditor…'),
            prefixIcon: const Icon(Icons.search_rounded, size: 20),
            filled: true, fillColor: Colors.white, isDense: true,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          ),
        ),
      );

  Widget _chips() => SizedBox(
        height: 42,
        child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 8), children: [
          for (final f in _filters) Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
            child: ChoiceChip(
              selected: _filter == f.$1,
              label: Text(tr(f.$2, f.$3), style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: _filter == f.$1 ? Colors.white : _navy)),
              selectedColor: _sky, backgroundColor: Colors.white,
              side: BorderSide(color: _filter == f.$1 ? _sky : Colors.grey.shade300),
              onSelected: (_) => setState(() => _filter = f.$1),
            ),
          ),
        ]),
      );

  Widget _card(Map a) {
    final score = dblOf(a['score'], 0.0);
    final c = _scoreColor(score);
    final fails = (numOf(a['fail_count'], 0)).toInt();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Material(
        color: Colors.white, borderRadius: BorderRadius.circular(15),
        child: InkWell(
          borderRadius: BorderRadius.circular(15),
          onTap: () => _openDetail((a['id'] as num).toInt()),
          child: Container(
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(15), border: Border.all(color: Colors.grey.shade200)),
            padding: const EdgeInsets.all(12),
            child: Row(children: [
              Container(
                width: 48, height: 48, alignment: Alignment.center,
                decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(14), border: Border.all(color: c.withValues(alpha: 0.35))),
                child: Text('${score.round()}', style: TextStyle(color: c, fontSize: 17, fontWeight: FontWeight.w900)),
              ),
              const SizedBox(width: 12),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${a['location'] ?? a['facility'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: _navy))),
                  if (a['rating_label'] != null) _tag('${a['rating_label']}', c),
                ]),
                const SizedBox(height: 4),
                Text('${a['name']} · ${a['facility'] ?? ''} · ${_short('${a['date'] ?? ''}')}',
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
                const SizedBox(height: 6),
                Wrap(spacing: 6, runSpacing: 5, children: [
                  _tag('${a['items'] ?? 0} ${tr('بند', 'items')}', const Color(0xFF64748B)),
                  if (fails > 0) _tag('✗ $fails ${tr('مخالفة', 'failed')}', const Color(0xFFE5484D))
                  else _tag('✓ ${tr('بلا مخالفات', 'no failures')}', const Color(0xFF16A34A)),
                  if (a['client_ack'] == 'disputed') _tag('⚠ ${a['client_ack_label']}', const Color(0xFFF59E0B))
                  else if (a['client_ack'] == 'accepted') _tag('✓ ${a['client_ack_label']}', const Color(0xFF16A34A)),
                  if (a['auditor'] != null) _tag('👤 ${a['auditor']}', const Color(0xFF6366F1)),
                ]),
              ])),
              const Icon(Icons.chevron_left_rounded, color: Colors.grey, size: 20),
            ]),
          ),
        ),
      ),
    );
  }

  /// The full audit: score, context, and the checklist item by item.
  void _openDetail(int id) {
    showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.88, minChildSize: 0.5, maxChildSize: 0.96,
        builder: (_, sc) => FutureBuilder<Map<String, dynamic>>(
          future: context.read<AuthProvider>().api.cleaningAudit(id),
          builder: (_, snap) {
            final d = snap.data;
            final score = dblOf(d?['score'], 0.0);
            final c = _scoreColor(score);
            final lines = ((d?['lines'] as List?) ?? const []).cast<Map>();
            return Container(
              decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
              clipBehavior: Clip.antiAlias,
              child: Column(children: [
                CustomPaint(
                  painter: const BrandPattern(opacity: 0.06),
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.fromLTRB(20, 12, 20, 18),
                    decoration: BoxDecoration(gradient: LinearGradient(
                        colors: [c, Color.lerp(c, Colors.black, 0.42)!], begin: Alignment.topRight, end: Alignment.bottomLeft)),
                    child: Column(children: [
                      Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12),
                          decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
                      Row(children: [
                        Container(
                          width: 62, height: 62, alignment: Alignment.center,
                          decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), shape: BoxShape.circle,
                              border: Border.all(color: Colors.white.withValues(alpha: 0.5), width: 2)),
                          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                            Text(score.toStringAsFixed(0), style: const TextStyle(color: Colors.white, fontSize: 21, fontWeight: FontWeight.w900, height: 1)),
                            const Text('%', style: TextStyle(color: Colors.white70, fontSize: 10, fontWeight: FontWeight.w800)),
                          ]),
                        ),
                        const SizedBox(width: 14),
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text('${d?['location'] ?? d?['facility'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis,
                              style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900)),
                          const SizedBox(height: 4),
                          Text('${d?['name'] ?? ''} · ${_short('${d?['date'] ?? ''}')}',
                              style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 11.5)),
                          if (d?['rating_label'] != null) ...[
                            const SizedBox(height: 7),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                              decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.22), borderRadius: BorderRadius.circular(20)),
                              child: Text('${d!['rating_label']}', style: const TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.w900)),
                            ),
                          ],
                        ])),
                      ]),
                    ]),
                  ),
                ),
                Expanded(child: d == null
                    ? const Center(child: CircularProgressIndicator(color: _sky))
                    : ListView(controller: sc, padding: const EdgeInsets.all(16), children: [
                        _kv(Icons.apartment_rounded, tr('المرفق', 'Facility'), '${d['facility'] ?? '—'}'),
                        if (d['location'] != null) _kv(Icons.pin_drop_rounded, tr('الموقع', 'Location'), '${d['location']}'),
                        if (d['auditor'] != null) _kv(Icons.person_rounded, tr('المدقّق', 'Auditor'), '${d['auditor']}'),
                        if (d['template'] != null) _kv(Icons.checklist_rounded, tr('القالب', 'Template'), '${d['template']}'),
                        _kv(Icons.flag_rounded, tr('الحالة', 'State'), '${d['state_label'] ?? ''}'),
                        if (d['client_ack_label'] != null)
                          _kv(Icons.verified_user_rounded, tr('إقرار العميل', 'Client sign-off'), '${d['client_ack_label']}'),
                        if (d['client_ack_comment'] != null)
                          Container(
                            margin: const EdgeInsets.symmetric(vertical: 8),
                            padding: const EdgeInsets.all(12), width: double.infinity,
                            decoration: BoxDecoration(color: const Color(0xFFF59E0B).withValues(alpha: 0.08),
                                borderRadius: BorderRadius.circular(12), border: Border.all(color: const Color(0xFFF59E0B).withValues(alpha: 0.3))),
                            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              Text(tr('تعليق العميل', 'Client comment'),
                                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12, color: Color(0xFFB45309))),
                              const SizedBox(height: 4),
                              Text('${d['client_ack_comment']}', style: const TextStyle(fontSize: 13, height: 1.4, color: _navy)),
                            ]),
                          ),
                        const SizedBox(height: 14),
                        Row(children: [
                          const Icon(Icons.fact_check_rounded, size: 18, color: _navy), const SizedBox(width: 7),
                          Text(tr('بنود الفحص', 'Checklist'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: _navy)),
                          const Spacer(),
                          Text('${lines.where((l) => l['result'] == 'pass').length}/${lines.length} ${tr('مطابق', 'passed')}',
                              style: TextStyle(fontSize: 12, color: Colors.grey.shade600, fontWeight: FontWeight.w800)),
                        ]),
                        const SizedBox(height: 8),
                        for (final l in lines) _lineTile(l),
                        const SizedBox(height: 20),
                      ])),
              ]),
            );
          },
        ),
      ),
    );
  }

  Widget _lineTile(Map l) {
    final res = '${l['result']}';
    final ok = res == 'pass', na = res == 'na';
    final c = ok ? const Color(0xFF16A34A) : (na ? const Color(0xFF94A3B8) : const Color(0xFFE5484D));
    return Container(
      margin: const EdgeInsets.only(bottom: 7),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12),
          border: Border.all(color: ok ? Colors.grey.shade200 : c.withValues(alpha: 0.3))),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(ok ? Icons.check_circle_rounded : (na ? Icons.remove_circle_outline_rounded : Icons.cancel_rounded), color: c, size: 19),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${l['name']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: _navy)),
          if (l['note'] != null) ...[
            const SizedBox(height: 3),
            Text('${l['note']}', style: TextStyle(fontSize: 11.5, color: c, fontWeight: FontWeight.w600, height: 1.3)),
          ],
        ])),
        const SizedBox(width: 8),
        Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Text('${l['result_label']}', style: TextStyle(color: c, fontSize: 11, fontWeight: FontWeight.w900)),
          Text('${tr('وزن', 'weight')} ${l['weight']}', style: TextStyle(fontSize: 9.5, color: Colors.grey.shade500)),
        ]),
      ]),
    );
  }

  Widget _kv(IconData ic, String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(ic, size: 17, color: _sky), const SizedBox(width: 10),
          SizedBox(width: 100, child: Text(k, style: TextStyle(color: Colors.grey.shade600, fontSize: 12.5, fontWeight: FontWeight.w700))),
          Expanded(child: Text(v, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: _navy))),
        ]),
      );

  Widget _tag(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(7)),
        child: Text(t, style: TextStyle(color: c, fontSize: 10, fontWeight: FontWeight.w800)),
      );

  String _short(String dt) => dt.length >= 16 ? dt.substring(0, 16).replaceFirst('T', ' ') : dt;

  Widget _empty(String t) => ListView(children: [
        const SizedBox(height: 90),
        Icon(Icons.fact_check_outlined, size: 56, color: Colors.grey.shade300),
        const SizedBox(height: 12),
        Center(child: Text(t, style: TextStyle(color: Colors.grey.shade500, fontWeight: FontWeight.w600))),
      ]);
}
