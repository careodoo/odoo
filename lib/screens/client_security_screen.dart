import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/service_ui.dart';

/// The client's security service in full: what is happening on their premises
/// right now, then every record behind it — incidents, patrols, gate passes,
/// visitors, inspections, guards and keys — searchable.
class ClientSecurityScreen extends StatefulWidget {
  const ClientSecurityScreen({super.key});
  @override
  State<ClientSecurityScreen> createState() => _ClientSecurityScreenState();
}

class _ClientSecurityScreenState extends State<ClientSecurityScreen> {
  static const _c = Color(0xFFE5484D);

  Map<String, dynamic>? _summary;
  String _kind = 'incidents';
  String _q = '';
  Future<List<dynamic>>? _list;
  final Map<String, int> _counts = {};

  static const _kinds = <(String, String, IconData)>[
    ('incidents', 'البلاغات', Icons.report_problem_rounded),
    ('patrols', 'الجولات', Icons.directions_walk_rounded),
    ('gatepasses', 'تصاريح الدخول', Icons.confirmation_number_rounded),
    ('visitors', 'الزوّار', Icons.person_add_alt_rounded),
    ('inspections', 'التفتيش', Icons.fact_check_rounded),
    ('guards', 'الحرّاس', Icons.shield_rounded),
    ('keys', 'المفاتيح', Icons.key_rounded),
  ];

  @override
  void initState() {
    super.initState();
    _loadSummary();
    _loadKind('incidents');
    _prefetchCounts();
  }

  Future<void> _loadSummary() async {
    try {
      final s = await context.read<AuthProvider>().api.clientSecuritySummary();
      if (mounted) setState(() => _summary = s);
    } catch (_) {/* the page still works without the band */}
  }

  /// Fill the tab counters so you can see where the records are without opening
  /// every tab in turn.
  Future<void> _prefetchCounts() async {
    for (final k in _kinds) {
      try {
        final rows = await context.read<AuthProvider>().api.clientSecurity(k.$1);
        if (mounted) setState(() => _counts[k.$1] = rows.length);
      } catch (_) {/* a kind that fails simply shows no counter */}
    }
  }

  void _loadKind(String k) => setState(() {
        _kind = k;
        _q = '';
        _list = context.read<AuthProvider>().api.clientSecurity(k);
      });

  @override
  Widget build(BuildContext context) {
    final s = _summary ?? const {};
    final label = _kinds.firstWhere((k) => k.$1 == _kind).$2;
    return Scaffold(
      appBar: AppBar(
        title: Text(tr('الأمن', 'Security')),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            onPressed: () { _loadSummary(); _loadKind(_kind); _prefetchCounts(); },
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async { await _loadSummary(); _loadKind(_kind); },
        child: ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
          ServiceHero(
            title: tr('الأمن', 'Security'),
            subtitle: tr('${s['premises'] ?? 0} موقع تحت الحراسة', '${s['premises'] ?? 0} premises guarded'),
            icon: Icons.shield_rounded,
            color: _c,
            stats: [
              (tr('بلاغ مفتوح', 'open'), '${s['incidents_open'] ?? 0}',
                  ((s['incidents_open'] ?? 0) as int) > 0 ? const Color(0xFFDC2626) : null),
              (tr('إجمالي البلاغات', 'incidents'), '${s['incidents_total'] ?? 0}', null),
              (tr('جولة جارية', 'patrols'), '${s['patrols_ongoing'] ?? 0}', null),
              (tr('تصريح فعّال', 'passes'), '${s['gatepasses_active'] ?? 0}', null),
              (tr('حارس بالموقع', 'guards'), '${s['guards_present'] ?? 0}', null),
              (tr('مفتاح مُصرَف', 'keys out'), '${s['keys_out'] ?? 0}', null),
              (tr('تفتيش قائم', 'inspections'), '${s['inspections_open'] ?? 0}', null),
            ],
            // Each number opens the records it counts.
            onStatTap: (i) => _loadKind(const [
              'incidents', 'incidents', 'patrols', 'gatepasses', 'guards', 'keys', 'inspections',
            ][i]),
          ),
          const SizedBox(height: 12),
          ServiceTabs(kinds: _kinds, current: _kind, onSelect: _loadKind, color: _c, counts: _counts),
          const SizedBox(height: 10),
          FutureBuilder<List<dynamic>>(
            future: _list,
            builder: (_, snap) {
              if (snap.connectionState == ConnectionState.waiting) {
                return const Padding(
                  padding: EdgeInsets.symmetric(vertical: 50),
                  child: Center(child: CircularProgressIndicator()),
                );
              }
              if (snap.hasError) {
                return Padding(
                  padding: const EdgeInsets.symmetric(vertical: 40),
                  child: Center(child: Text('${snap.error}', style: const TextStyle(color: Colors.grey))),
                );
              }
              final all = snap.data ?? const [];
              final rows = _q.isEmpty
                  ? all
                  : all.where((r) => _hay(r as Map).contains(_q.toLowerCase())).toList();
              return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                if (all.length > 6) ...[
                  TextField(
                    onChanged: (v) => setState(() => _q = v),
                    decoration: InputDecoration(
                      hintText: tr('ابحث في $label…', 'Search $label…'),
                      prefixIcon: const Icon(Icons.search_rounded, size: 19),
                      isDense: true, filled: true,
                      border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                    ),
                  ),
                  const SizedBox(height: 10),
                ],
                MoreList(
                  items: rows,
                  color: _c,
                  header: label,
                  emptyText: _q.isEmpty
                      ? tr('لا سجلات في $label.', 'No $label records.')
                      : tr('لا نتائج للبحث.', 'No matches.'),
                  itemBuilder: (_, r, __) => _row(r as Map),
                ),
              ]);
            },
          ),
        ]),
      ),
    );
  }

  String _hay(Map r) => r.values.map((v) => '$v').join(' ').toLowerCase();

  /// Severity is the one thing on a security record that must read instantly.
  (Color, String) _severity(Map r) {
    final s = '${r['severity'] ?? ''}'.toLowerCase();
    if (s.isEmpty || s == 'null') return (Colors.transparent, '');
    if (s.contains('critical') || s.contains('حرج') || s.contains('عالي') || s.contains('high')) {
      return (const Color(0xFFDC2626), '${r['severity']}');
    }
    if (s.contains('medium') || s.contains('متوسط')) return (const Color(0xFFF7A23B), '${r['severity']}');
    return (const Color(0xFF16A34A), '${r['severity']}');
  }

  Widget _row(Map r) {
    final title = r['name'] ?? r['visitor'] ?? r['guard'] ?? '—';
    final sev = _severity(r);
    final state = r['state_label'] ?? r['state'];
    final facts = <String>[
      for (final k in ['type', 'premise', 'route', 'guard', 'company', 'inspector', 'holder', 'location'])
        if (r[k] != null && '${r[k]}'.isNotEmpty) '${r[k]}',
    ];
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (sev.$1 != Colors.transparent) ...[
            Container(width: 3.5, height: 34,
                decoration: BoxDecoration(color: sev.$1, borderRadius: BorderRadius.circular(3))),
            const SizedBox(width: 9),
          ],
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('$title', maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
            if (r['date'] != null)
              Padding(
                padding: const EdgeInsets.only(top: 2),
                child: Row(children: [
                  Icon(Icons.schedule_rounded, size: 10, color: Colors.grey.shade500),
                  const SizedBox(width: 3),
                  Text('${r['date']}'.replaceFirst('T', ' '),
                      style: TextStyle(fontSize: 9.5, color: Colors.grey.shade600, fontWeight: FontWeight.w600)),
                ]),
              ),
          ])),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            if (sev.$2.isNotEmpty)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                decoration: BoxDecoration(color: sev.$1, borderRadius: BorderRadius.circular(7)),
                child: Text(sev.$2,
                    style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w900, color: Colors.white)),
              ),
            if (state != null) ...[
              const SizedBox(height: 3),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                decoration: BoxDecoration(
                    color: _c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(7)),
                child: Text('$state',
                    style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w900, color: _c)),
              ),
            ],
          ]),
        ]),
        if (facts.isNotEmpty) ...[
          const SizedBox(height: 8),
          Wrap(spacing: 5, runSpacing: 5, children: [
            for (final f in facts.take(5))
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                decoration: BoxDecoration(
                    color: Colors.grey.withValues(alpha: 0.09), borderRadius: BorderRadius.circular(7)),
                child: Text(f, maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w600, color: Colors.grey.shade700)),
              ),
          ]),
        ],
        if (r['description'] != null && '${r['description']}'.trim().isNotEmpty) ...[
          const SizedBox(height: 7),
          Text('${r['description']}', maxLines: 3, overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 11, height: 1.5, color: Colors.grey.shade700)),
        ],
      ]),
    );
  }
}
