import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/service_ui.dart';
import 'excel_export.dart';
import 'security_gatepass_create.dart';
import 'client_workorder_create.dart';

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
  static const _kindColors = {
    'incidents': Color(0xFFE5484D), 'patrols': Color(0xFF2563EB),
    'gatepasses': Color(0xFF16A34A), 'visitors': Color(0xFF7C3AED),
    'inspections': Color(0xFF0EA5A4), 'guards': Color(0xFF4338CA),
    'keys': Color(0xFFF59E0B),
  };
  Color get _kc => _kindColors[_kind] ?? _c;

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
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: _kc, foregroundColor: Colors.white,
        icon: const Icon(Icons.add_rounded),
        label: Text(tr('إجراء أمني', 'Security action'), style: const TextStyle(fontWeight: FontWeight.w900)),
        onPressed: _actionMenu,
      ),
      appBar: AppBar(
        title: Text(tr('الأمن', 'Security')),
        actions: [
          IconButton(
            icon: const Icon(Icons.grid_on_rounded),
            tooltip: tr('تصدير تصاريح الدخول', 'Export gate passes'),
            onPressed: () => exportExcelFile(context, path: '/cafm/security/gatepasses/export',
                fileName: 'gate-passes.xlsx', shareText: tr('تصاريح الدخول', 'Gate passes')),
          ),
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
            color: _kc,
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
          ServiceTabs(kinds: _kinds, current: _kind, onSelect: _loadKind, color: _kc, counts: _counts),
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
                  color: _kc,
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

  /// The client's security actions in one menu: raise a security work order or
  /// issue a gate pass.
  void _actionMenu() => showModalBottomSheet(context: context, backgroundColor: Colors.transparent, builder: (_) => Container(
        decoration: const BoxDecoration(color: Colors.white, borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
        padding: const EdgeInsets.fromLTRB(8, 10, 8, 18),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 10),
              decoration: BoxDecoration(color: Colors.black12, borderRadius: BorderRadius.circular(3))),
          ListTile(
            leading: Container(width: 40, height: 40, alignment: Alignment.center,
                decoration: BoxDecoration(color: const Color(0xFFE5484D).withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)),
                child: const Icon(Icons.add_task_rounded, color: Color(0xFFE5484D))),
            title: Text(tr('طلب عمل أمني', 'Security work order'), style: const TextStyle(fontWeight: FontWeight.w800)),
            subtitle: Text(tr('ارفع طلب عمل لخدمة الأمن وأسنِده', 'Raise & assign a security work order'), style: const TextStyle(fontSize: 11.5)),
            onTap: () async {
              Navigator.pop(context);
              final created = await ClientWorkorderCreateSheet.open(context, presetServiceType: 'security');
              if (created == true && mounted) { _loadSummary(); _prefetchCounts(); }
            },
          ),
          ListTile(
            leading: Container(width: 40, height: 40, alignment: Alignment.center,
                decoration: BoxDecoration(color: const Color(0xFF16A34A).withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)),
                child: const Icon(Icons.confirmation_number_rounded, color: Color(0xFF16A34A))),
            title: Text(tr('إصدار تصريح دخول', 'Issue gate pass'), style: const TextStyle(fontWeight: FontWeight.w800)),
            subtitle: Text(tr('لزائر أو مركبة', 'For a visitor or vehicle'), style: const TextStyle(fontSize: 11.5)),
            onTap: () async {
              Navigator.pop(context);
              final created = await SecurityGatepassCreateSheet.open(context);
              if (created == true && mounted) { _loadSummary(); _loadKind('gatepasses'); _prefetchCounts(); }
            },
          ),
        ]),
      ));

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
    return InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: () => _openRecord(r, '$title'),
      child: Container(
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
                    color: _kc.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(7)),
                child: Text('$state',
                    style: TextStyle(fontSize: 8.5, fontWeight: FontWeight.w900, color: _kc)),
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
        const SizedBox(height: 6),
        Row(mainAxisAlignment: MainAxisAlignment.end, children: [
          Text(tr('التفاصيل', 'Details'), style: TextStyle(fontSize: 10, color: _kc, fontWeight: FontWeight.w800)),
          Icon(Icons.chevron_left_rounded, size: 15, color: _kc),
        ]),
      ]),
    ),
    );
  }

  /// A professional detail sheet showing every populated field of a security
  /// record, with human labels.
  void _openRecord(Map r, String title) {
    const labels = {
      'name': 'المرجع', 'type': 'النوع', 'premise': 'الموقع', 'route': 'المسار',
      'guard': 'الحارس', 'company': 'الجهة', 'phone': 'الهاتف', 'purpose': 'الغرض',
      'visitor': 'الزائر', 'inspector': 'المفتّش', 'holder': 'حائز المفتاح',
      'vehicle': 'المركبة', 'persons': 'عدد الأشخاص', 'severity': 'الخطورة',
      'location': 'الموقع', 'date': 'التاريخ', 'check_in': 'الدخول', 'check_out': 'الخروج',
      'start': 'البداية', 'end': 'النهاية', 'valid_from': 'صالح من', 'valid_until': 'صالح حتى',
      'state_label': 'الحالة', 'description': 'الوصف',
    };
    final entries = <MapEntry<String, String>>[];
    labels.forEach((k, lbl) {
      final v = r[k];
      if (v != null && '$v'.trim().isNotEmpty && '$v' != 'null') {
        entries.add(MapEntry(lbl, '$v'.replaceFirst('T', ' ')));
      }
    });
    showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.6, maxChildSize: 0.92,
        builder: (_, sc) => Container(
          decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
          clipBehavior: Clip.antiAlias,
          child: ListView(controller: sc, padding: EdgeInsets.zero, children: [
            Container(
              padding: const EdgeInsets.fromLTRB(20, 14, 20, 16),
              decoration: BoxDecoration(gradient: LinearGradient(
                  colors: [_kc, Color.lerp(_kc, Colors.black, 0.3)!], begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Row(children: [
                const Icon(Icons.shield_rounded, color: Colors.white, size: 24),
                const SizedBox(width: 10),
                Expanded(child: Text(title, style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900))),
                if (r['state_label'] != null)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(20)),
                    child: Text('${r['state_label']}', style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w900)),
                  ),
              ]),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
                child: Column(children: [
                  for (var i = 0; i < entries.length; i++) ...[
                    if (i > 0) Divider(height: 1, color: Colors.grey.shade200),
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 11),
                      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        SizedBox(width: 110, child: Text(entries[i].key,
                            style: TextStyle(fontSize: 12, color: Colors.grey.shade600, fontWeight: FontWeight.w600))),
                        Expanded(child: Text(entries[i].value,
                            style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: Color(0xFF0E3A5F)))),
                      ]),
                    ),
                  ],
                ]),
              ),
            ),
          ]),
        ),
      ),
    );
  }
}
