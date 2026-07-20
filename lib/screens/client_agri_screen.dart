import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/service_ui.dart';
import 'pdf_report_screen.dart';

/// Client-facing landscaping/agriculture suite: overview + trees/plants,
/// tree works, irrigation zones and the species care guide (scoped to the
/// client's facilities). Mirrors the portal's agriculture section.
class ClientAgriScreen extends StatefulWidget {
  const ClientAgriScreen({super.key});
  @override
  State<ClientAgriScreen> createState() => _ClientAgriScreenState();
}

class _ClientAgriScreenState extends State<ClientAgriScreen> {
  Map<String, dynamic>? _summary;
  String _kind = 'plants';
  Future<List<dynamic>>? _list;

  static const _c = Color(0xFF16A34A);
  String _q = '';
  String? _speciesCat;
  static const _kinds = <(String, String, String, IconData)>[
    ('plants', 'الأشجار', 'Trees', Icons.park_rounded),
    ('operations', 'الأعمال', 'Operations', Icons.content_cut_rounded),
    ('zones', 'الريّ', 'Irrigation', Icons.water_drop_rounded),
    ('species', 'الأنواع', 'Species', Icons.menu_book_rounded),
  ];

  @override
  void initState() {
    super.initState();
    _loadSummary();
    _loadKind('plants');
  }

  Future<void> _loadSummary() async {
    try {
      final s = await context.read<AuthProvider>().api.clientAgriSummary();
      if (mounted) setState(() => _summary = s);
    } catch (_) {}
  }

  void _loadKind(String k) => setState(() {
        _kind = k;
        _q = '';
        _list = context.read<AuthProvider>().api.clientAgri(k);
      });

  @override
  Widget build(BuildContext context) {
    final s = _summary ?? const {};
    final label = (() { final k = _kinds.firstWhere((x) => x.$1 == _kind); return tr(k.$2, k.$3); })();
    return Scaffold(
      appBar: AppBar(
        title: Text(tr('الزراعة والحدائق', 'Landscaping')),
        actions: [IconButton(icon: const Icon(Icons.refresh_rounded),
            onPressed: () { _loadSummary(); _loadKind(_kind); })],
      ),
      body: RefreshIndicator(
        onRefresh: () async { await _loadSummary(); _loadKind(_kind); },
        child: ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
          ServiceHero(
            title: tr('الزراعة والحدائق', 'Landscaping'),
            subtitle: tr('${s['zones'] ?? 0} منطقة ريّ · ${s['plants'] ?? 0} شجرة', '${s['zones'] ?? 0} zones · ${s['plants'] ?? 0} plants'),
            icon: Icons.park_rounded,
            color: _c,
            stats: [
              (tr('أشجار ونباتات', 'plants'), '${s['plants'] ?? 0}', null),
              (tr('تحتاج عناية', 'poor'), '${s['plants_poor'] ?? 0}',
                  ((s['plants_poor'] ?? 0) as int) > 0 ? const Color(0xFFF59E0B) : null),
              (tr('فحص متأخّر', 'overdue'), '${s['inspections_overdue'] ?? 0}',
                  ((s['inspections_overdue'] ?? 0) as int) > 0 ? const Color(0xFFDC2626) : null),
              (tr('تقليم مستحقّ', 'prune'), '${s['prune_due'] ?? 0}', null),
              (tr('تسميد مستحقّ', 'fertilize'), '${s['fertilize_due'] ?? 0}', null),
              (tr('مناطق ريّ', 'zones'), '${s['zones'] ?? 0}', null),
              (tr('م³ الشهر', 'm³ mo'), '${s['water_month_m3'] ?? 0}', null),
            ],
            onStatTap: (i) => _loadKind(const [
              'plants', 'plants', 'plants', 'plants', 'plants', 'zones', 'zones'][i]),
          ),
          const SizedBox(height: 12),
          ServiceTabs(kinds: _kinds, current: _kind, onSelect: _loadKind, color: _c),
          const SizedBox(height: 10),
          FutureBuilder<List<dynamic>>(
            future: _list,
            builder: (_, snap) {
              if (snap.connectionState == ConnectionState.waiting) {
                return const Padding(padding: EdgeInsets.symmetric(vertical: 50),
                    child: Center(child: CircularProgressIndicator()));
              }
              final all = snap.data ?? const [];
              final rows = _q.isEmpty
                  ? all
                  : all.where((r) => (r as Map).values.map((v) => '$v').join(' ').toLowerCase()
                      .contains(_q.toLowerCase())).toList();
              // The species catalogue is a reference directory: searchable,
              // filterable by kind, and every entry opens. It used to be a
              // fixed-ratio grid whose Expanded image squeezed the names into
              // each other.
              if (_kind == 'species') {
                final cats = <String>{for (final r in all) '${(r as Map)['category'] ?? ''}'}
                    .where((x) => x.isNotEmpty).toList()..sort();
                var list = rows;
                if (_speciesCat != null) {
                  list = list.where((r) => (r as Map)['category'] == _speciesCat).toList();
                }
                return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  _searchField(label),
                  const SizedBox(height: 10),
                  SizedBox(
                    height: 36,
                    child: ListView(scrollDirection: Axis.horizontal, children: [
                      _catChip(null, tr('الكل', 'All'), all.length),
                      for (final c in cats)
                        _catChip(c, c, all.where((r) => (r as Map)['category'] == c).length),
                    ]),
                  ),
                  const SizedBox(height: 6),
                  Text('${list.length} ${tr('نوع', 'species')}',
                      style: TextStyle(fontSize: 11.5, color: Colors.grey.shade500,
                          fontWeight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  if (list.isEmpty)
                    _emptyBox(label)
                  else
                    for (final r in list) _speciesRow(r as Map),
                ]);
              }
              return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                if (all.length > 6) ...[_searchField(label), const SizedBox(height: 10)],
                MoreList(
                  items: rows,
                  color: _c,
                  header: label,
                  emptyText: tr('لا سجلات في $label.', 'No $label records.'),
                  itemBuilder: (_, r, __) => Padding(
                    padding: const EdgeInsets.only(bottom: 6),
                    child: Material(
                      color: Theme.of(context).cardColor,
                      borderRadius: BorderRadius.circular(12),
                      child: _row(r as Map),
                    ),
                  ),
                ),
              ]);
            },
          ),
        ]),
      ),
    );
  }

  Widget _searchField(String label) => TextField(
        onChanged: (v) => setState(() => _q = v),
        decoration: InputDecoration(
          hintText: tr('ابحث في $label…', 'Search $label…'),
          prefixIcon: const Icon(Icons.search_rounded, size: 19),
          isDense: true, filled: true,
          border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
        ),
      );

  Widget _emptyBox(String label) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 42),
        child: Center(child: Text(tr('لا سجلات في $label.', 'No $label records.'),
            style: TextStyle(color: Colors.grey.shade500))),
      );

  static const _healthColors = {
    'good': Color(0xFF16A34A), 'fair': Color(0xFFF59E0B),
    'poor': Color(0xFFE11D48), 'dead': Color(0xFF334155),
  };

  Widget _row(Map r) {
    if (_kind == 'plants') {
      final hc = _healthColors[r['health']] ?? Colors.blueGrey;
      final overdue = r['inspection_overdue'] == true;
      return ListTile(
        leading: (r['image'] != null)
            ? CircleAvatar(backgroundImage: NetworkImage('${r['image']}'))
            : CircleAvatar(backgroundColor: hc.withValues(alpha: 0.15), child: const Text('🌳')),
        title: Text('${r['name']}', style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text([r['species'], r['facility'], r['zone']].where((x) => x != null && '$x'.isNotEmpty).join(' · '),
            maxLines: 2, overflow: TextOverflow.ellipsis),
        trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
          _pill('${r['health_label']}', hc),
          if (overdue) const Padding(padding: EdgeInsets.only(top: 3), child: Text('⚠️ فحص', style: TextStyle(fontSize: 10, color: Color(0xFFE11D48)))),
        ]),
        onTap: () => _openPlant(r['id'] as int),
      );
    }
    if (_kind == 'operations') {
      final rc = r['result_raw'] == 'failed'
          ? const Color(0xFFE11D48)
          : r['result_raw'] == 'partial' ? const Color(0xFFF59E0B) : const Color(0xFF16A34A);
      return ListTile(
        title: Text('${r['type']} — ${r['plant'] ?? r['facility'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text([r['date'], r['done_by'], r['material']].where((x) => x != null && '$x'.isNotEmpty).join(' · '),
            maxLines: 2, overflow: TextOverflow.ellipsis),
        trailing: _pill('${r['result']}', rc),
      );
    }
    // zones
    final due = r['is_due'] == true;
    final mo = (r['moisture_pct'] ?? 0);
    const planC = {'approved': Color(0xFF16A34A), 'rejected': Color(0xFFE11D48), 'pending': Color(0xFFF59E0B)};
    const planL = {'approved': 'معتمدة', 'rejected': 'مرفوضة', 'pending': 'بانتظار'};
    final ps = '${r['plan_state'] ?? 'pending'}';
    return ListTile(
      leading: const Text('💧', style: TextStyle(fontSize: 22)),
      title: Row(children: [
        Flexible(child: Text('${r['name']}', style: const TextStyle(fontWeight: FontWeight.w700), overflow: TextOverflow.ellipsis)),
        if (r['weather_based'] == true) const Padding(padding: EdgeInsets.only(right: 4, left: 4), child: Text('🇰🇼', style: TextStyle(fontSize: 12))),
      ]),
      subtitle: Text('${r['facility'] ?? ''} · ${r['method'] ?? ''} · 💦 ${r['water_month_m3'] ?? 0} م³ · 🌱 ${r['plant_count'] ?? 0}',
          maxLines: 2, overflow: TextOverflow.ellipsis),
      trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
        _pill('$mo%', mo < 30 ? const Color(0xFFE11D48) : mo < 45 ? const Color(0xFFF59E0B) : const Color(0xFF16A34A)),
        Padding(padding: const EdgeInsets.only(top: 3), child: _pill(tr(planL[ps] ?? ps, ps), planC[ps] ?? Colors.grey)),
        if (due) const Text('🚿', style: TextStyle(fontSize: 11)),
      ]),
      onTap: () => _zonePlan(r),
    );
  }

  Future<void> _zonePlan(Map z) async {
    final commentCtrl = TextEditingController(text: '${z['plan_comment'] ?? ''}');
    final act = await showModalBottomSheet<String>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (ctx) => Padding(
        padding: EdgeInsets.fromLTRB(16, 0, 16, MediaQuery.of(ctx).viewInsets.bottom + 16),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('💧 ${z['name']}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          Text('${z['facility'] ?? ''} · ${z['method'] ?? ''} · ${z['duration_min'] ?? 0} ${tr('دقيقة', 'min')}', style: const TextStyle(color: Colors.grey)),
          const SizedBox(height: 14),
          Text(tr('موافقتك على خطة الريّ', 'Approve this irrigation plan'), style: const TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 8),
          TextField(controller: commentCtrl, decoration: InputDecoration(hintText: tr('تعليق (اختياري)', 'Comment (optional)'), border: const OutlineInputBorder()), maxLines: 2),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF16A34A), foregroundColor: Colors.white),
              onPressed: () => Navigator.pop(ctx, 'approve'), icon: const Icon(Icons.check), label: Text(tr('اعتماد', 'Approve')))),
            const SizedBox(width: 10),
            Expanded(child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFE11D48), foregroundColor: Colors.white),
              onPressed: () => Navigator.pop(ctx, 'reject'), icon: const Icon(Icons.close), label: Text(tr('رفض', 'Reject')))),
          ]),
        ]),
      ),
    );
    if (act == null || !mounted) return;
    try {
      await context.read<AuthProvider>().api.clientAgriZoneDecision(z['id'] as int, act, comment: commentCtrl.text);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(act == 'approve' ? tr('تم اعتماد الخطة', 'Plan approved') : tr('تم رفض الخطة', 'Plan rejected'))));
        _loadKind('zones');
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  Widget _catChip(String? code, String label, int n) => Padding(
        padding: const EdgeInsets.only(left: 6),
        child: ChoiceChip(
          selected: _speciesCat == code,
          label: Text('$label ($n)',
              style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800,
                  color: _speciesCat == code ? Colors.white : const Color(0xFF14202B))),
          selectedColor: _c, backgroundColor: Colors.white,
          side: BorderSide(color: _speciesCat == code ? _c : Colors.grey.shade300),
          onSelected: (_) => setState(() => _speciesCat = code),
        ),
      );

  /// One species: both names, the botanical name, and the facts a crew works
  /// from. Tapping opens the full care guide.
  Widget _speciesRow(Map s) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Material(
          color: Colors.white,
          borderRadius: BorderRadius.circular(14),
          child: InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: () => _openSpecies(s),
            child: Container(
              padding: const EdgeInsets.all(11),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.grey.shade200),
              ),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Container(
                  width: 46, height: 46, alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: _c.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(12),
                    image: s['image'] != null
                        ? DecorationImage(image: NetworkImage('${s['image']}'), fit: BoxFit.cover)
                        : null,
                  ),
                  child: s['image'] == null
                      ? Text(_speciesEmoji('${s['category_raw'] ?? ''}'),
                          style: const TextStyle(fontSize: 22))
                      : null,
                ),
                const SizedBox(width: 11),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${s['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14,
                          color: Color(0xFF14202B))),
                  if (s['name_en'] != null)
                    Text('${s['name_en']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700,
                            color: Colors.grey.shade600)),
                  if (s['scientific_name'] != null)
                    Text('${s['scientific_name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 11, fontStyle: FontStyle.italic,
                            color: Colors.grey.shade400)),
                  const SizedBox(height: 6),
                  Wrap(spacing: 5, runSpacing: 5, children: [
                    _pill('${s['category']}', Colors.blueGrey),
                    _pill('💧 ${s['water_need']}', const Color(0xFF0369A1)),
                    _pill('☀️ ${s['sun_exposure']}', const Color(0xFFB45309)),
                    if (s['heat_tolerant'] == true)
                      _pill('🇰🇼 ${tr('يتحمّل الحر', 'heat')}', const Color(0xFF16A34A)),
                    if (s['salt_tolerant'] == true)
                      _pill('🧂 ${tr('ملوحة', 'salt')}', const Color(0xFF0891B2)),
                    if ((numOf(s['plant_count'], 0)) > 0)
                      _pill('🌱 ${s['plant_count']}', const Color(0xFF7C3AED)),
                  ]),
                ])),
                Icon(Icons.chevron_left_rounded, color: Colors.grey.shade400),
              ]),
            ),
          ),
        ),
      );

  String _speciesEmoji(String cat) => const {
        'tree': '🌳', 'palm': '🌴', 'shrub': '🌿', 'flower': '🌸',
        'grass': '🌾', 'cactus': '🌵', 'groundcover': '☘️',
      }[cat] ?? '🌱';

  void _openSpecies(Map s) => showModalBottomSheet(
        context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
        builder: (ctx) => DraggableScrollableSheet(
          expand: false, initialChildSize: 0.72, minChildSize: 0.4, maxChildSize: 0.95,
          builder: (_, sc) => Container(
            decoration: const BoxDecoration(color: Colors.white,
                borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
            clipBehavior: Clip.antiAlias,
            child: ListView(controller: sc, padding: EdgeInsets.zero, children: [
              Container(
                width: double.infinity,
                padding: const EdgeInsets.fromLTRB(20, 14, 20, 18),
                decoration: BoxDecoration(
                    gradient: LinearGradient(colors: [_c, _c.withValues(alpha: 0.72)],
                        begin: Alignment.topRight, end: Alignment.bottomLeft)),
                child: Column(children: [
                  Center(child: Container(width: 40, height: 4,
                      margin: const EdgeInsets.only(bottom: 14),
                      decoration: BoxDecoration(color: Colors.white54,
                          borderRadius: BorderRadius.circular(3)))),
                  Text(_speciesEmoji('${s['category_raw'] ?? ''}'),
                      style: const TextStyle(fontSize: 38)),
                  const SizedBox(height: 6),
                  Text('${s['name']}', textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.white, fontSize: 19,
                          fontWeight: FontWeight.w900)),
                  if (s['name_en'] != null)
                    Text('${s['name_en']}',
                        style: const TextStyle(color: Colors.white70, fontSize: 13.5,
                            fontWeight: FontWeight.w700)),
                  if (s['scientific_name'] != null)
                    Text('${s['scientific_name']}',
                        style: const TextStyle(color: Colors.white54, fontSize: 12,
                            fontStyle: FontStyle.italic)),
                ]),
              ),
              Padding(
                padding: const EdgeInsets.all(16),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  GridView.count(
                    crossAxisCount: 2, shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    childAspectRatio: 3.1, crossAxisSpacing: 9, mainAxisSpacing: 9,
                    children: [
                      _fact('💧', tr('احتياج الماء', 'Water'), '${s['water_need']}'),
                      _fact('☀️', tr('التعرّض للشمس', 'Sun'), '${s['sun_exposure']}'),
                      _fact('✂️', tr('دورة التقليم', 'Pruning'),
                          '${s['prune_interval_days']} ${tr('يوم', 'days')}'),
                      _fact('🌱', tr('دورة التسميد', 'Feeding'),
                          '${s['fertilize_interval_days']} ${tr('يوم', 'days')}'),
                      _fact('🇰🇼', tr('حرارة الكويت', 'Kuwait heat'),
                          s['heat_tolerant'] == true ? tr('يتحمّل', 'Tolerant')
                                                     : tr('لا يتحمّل', 'Not tolerant')),
                      _fact('🧂', tr('الملوحة', 'Salinity'),
                          s['salt_tolerant'] == true ? tr('يتحمّل', 'Tolerant')
                                                     : tr('لا يتحمّل', 'Not tolerant')),
                    ],
                  ),
                  if (s['care_guide'] != null) ...[
                    const SizedBox(height: 18),
                    Text(tr('دليل العناية', 'Care guide'),
                        style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5,
                            color: Color(0xFF14202B))),
                    const SizedBox(height: 7),
                    Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(13),
                      decoration: BoxDecoration(color: const Color(0xFFF6F7F9),
                          borderRadius: BorderRadius.circular(13)),
                      child: Text('${s['care_guide']}',
                          style: const TextStyle(fontSize: 13, height: 1.6)),
                    ),
                  ],
                  if ((numOf(s['plant_count'], 0)) > 0) ...[
                    const SizedBox(height: 14),
                    Row(children: [
                      Icon(Icons.park_rounded, size: 16, color: _c),
                      const SizedBox(width: 7),
                      Text('${s['plant_count']} ${tr('نبتة من هذا النوع في مواقعك',
                          'planted at your sites')}',
                          style: TextStyle(fontSize: 12.5, color: Colors.grey.shade700,
                              fontWeight: FontWeight.w700)),
                    ]),
                  ],
                  const SizedBox(height: 16),
                ]),
              ),
            ]),
          ),
        ),
      );

  Widget _fact(String icon, String label, String value) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 8),
        decoration: BoxDecoration(color: const Color(0xFFF6F7F9),
            borderRadius: BorderRadius.circular(12)),
        child: Row(children: [
          Text(icon, style: const TextStyle(fontSize: 16)),
          const SizedBox(width: 8),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min, children: [
            Text(label, style: TextStyle(fontSize: 9.5, color: Colors.grey.shade500,
                fontWeight: FontWeight.w700)),
            Text(value, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w900,
                    color: Color(0xFF14202B))),
          ])),
        ]),
      );

  Widget _pill(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(20)),
        child: Text(t, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: c)),
      );

  Future<void> _openPlant(int id) async {
    showDialog(context: context, builder: (_) => const Center(child: CircularProgressIndicator()));
    Map<String, dynamic> d;
    try {
      d = await context.read<AuthProvider>().api.clientAgriPlant(id);
    } catch (_) {
      if (mounted) Navigator.pop(context);
      return;
    }
    if (!mounted) return;
    Navigator.pop(context);
    final ops = (d['operations'] as List?) ?? [];
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.7,
        maxChildSize: 0.95,
        builder: (_, ctrl) => ListView(controller: ctrl, padding: const EdgeInsets.all(16), children: [
          if (d['image'] != null)
            ClipRRect(borderRadius: BorderRadius.circular(12), child: Image.network('${d['image']}', height: 170, width: double.infinity, fit: BoxFit.cover)),
          const SizedBox(height: 10),
          Text('${d['name']}', style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800)),
          if (d['species'] != null) Text('${d['species']}', style: const TextStyle(color: Colors.grey)),
          const SizedBox(height: 10),
          Row(children: [
            Expanded(child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF15803D), foregroundColor: Colors.white,
                  padding: const EdgeInsets.symmetric(vertical: 12), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
              onPressed: () => _requestWork(id, '${d['name']}'),
              icon: const Icon(Icons.build_rounded, size: 18),
              label: Text(tr('طلب عمل', 'Request work'), style: const TextStyle(fontWeight: FontWeight.w800)),
            )),
            const SizedBox(width: 8),
            Expanded(child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFF15803D),
                  side: const BorderSide(color: Color(0xFF15803D)),
                  padding: const EdgeInsets.symmetric(vertical: 12), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
                title: tr('بطاقة الشجرة', 'Tree card'),
                path: '/cafm/agri/tree/$id/card',
                fileName: 'tree-card-$id.pdf',
              ))),
              icon: const Icon(Icons.qr_code_2_rounded, size: 18),
              label: Text(tr('بطاقة QR', 'QR card'), style: const TextStyle(fontWeight: FontWeight.w800)),
            )),
          ]),
          const Divider(height: 22),
          _kv(tr('المرفق', 'Facility'), d['facility']),
          _kv(tr('منطقة الريّ', 'Zone'), d['zone']),
          _kv(tr('العمر', 'Age'), '${d['age_years'] ?? 0} ${tr('سنة', 'yrs')}'),
          _kv(tr('الارتفاع', 'Height'), '${d['height_m'] ?? 0} ${tr('م', 'm')}'),
          _kv(tr('قطر الجذع', 'Trunk'), '${d['trunk_cm'] ?? 0} ${tr('سم', 'cm')}'),
          _kv(tr('آخر فحص', 'Last insp.'), d['last_inspection']),
          _kv(tr('الفحص القادم', 'Next insp.'), d['next_inspection']),
          _kv(tr('التقليم القادم', 'Next prune'), d['next_prune']),
          _kv(tr('التسميد القادم', 'Next fertilize'), d['next_fertilize']),
          if (d['gps'] != null) _kv('GPS', d['gps']),
          if (ops.isNotEmpty) ...[
            const Divider(height: 22),
            Text(tr('سجل الأعمال', 'Works history'), style: const TextStyle(fontWeight: FontWeight.w800)),
            const SizedBox(height: 6),
            for (final o in ops)
              ListTile(
                dense: true,
                contentPadding: EdgeInsets.zero,
                title: Text('${o['type']} · ${o['date'] ?? ''}'),
                subtitle: Text([o['done_by'], o['material']].where((x) => x != null && '$x'.isNotEmpty).join(' · ')),
                trailing: (o['cost'] != null && o['cost'] != 0) ? Text('${o['cost']}') : null,
              ),
          ],
          if (d['care_note'] != null) ...[
            const Divider(height: 22),
            Text('${d['care_note']}', style: const TextStyle(color: Colors.black87)),
          ],
        ]),
      ),
    );
  }

  static const _reqOps = [
    ['prune', '✂️', 'تقليم', 'Prune'],
    ['inspect', '🔎', 'فحص', 'Inspect'],
    ['pest', '🐛', 'مكافحة آفات', 'Pest control'],
    ['fertilize', '🌱', 'تسميد', 'Fertilize'],
    ['water', '💧', 'ريّ إضافي', 'Extra water'],
    ['weed', '🌾', 'إزالة أعشاب', 'Weeding'],
    ['remove', '🪓', 'إزالة/قطع', 'Removal'],
    ['other', '🛠️', 'أخرى', 'Other'],
  ];
  static const _reqPrio = [
    ['0', 'منخفضة', 'Low', Color(0xFF64748B)],
    ['1', 'عادية', 'Normal', Color(0xFF0891B2)],
    ['2', 'عالية', 'High', Color(0xFFF7A23B)],
    ['3', 'عاجلة', 'Urgent', Color(0xFFE5484D)],
  ];

  Future<void> _requestWork(int plantId, String plantName) async {
    String op = 'prune';
    String priority = '1';
    DateTime? preferred;
    final noteCtrl = TextEditingController();
    const green = Color(0xFF15803D);
    final ok = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => StatefulBuilder(
        builder: (ctx, setSt) => Container(
          decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
          clipBehavior: Clip.antiAlias,
          padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.fromLTRB(20, 14, 20, 16),
              decoration: const BoxDecoration(gradient: LinearGradient(
                  colors: [Color(0xFF1a8c48), Color(0xFF0e5c30)], begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  const Icon(Icons.park_rounded, color: Colors.white, size: 24),
                  const SizedBox(width: 10),
                  Expanded(child: Text(tr('طلب عمل على الشجرة', 'Request tree work'),
                      style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900))),
                  IconButton(icon: const Icon(Icons.close_rounded, color: Colors.white), onPressed: () => Navigator.pop(ctx, false)),
                ]),
                Text(plantName, style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 13)),
              ]),
            ),
            Flexible(child: ListView(shrinkWrap: true, padding: const EdgeInsets.all(16), children: [
              Text(tr('نوع العمل المطلوب', 'Type of work'), style: const TextStyle(fontWeight: FontWeight.w900, color: Color(0xFF0E3A5F))),
              const SizedBox(height: 8),
              Wrap(spacing: 7, runSpacing: 7, children: [
                for (final o in _reqOps)
                  ChoiceChip(
                    label: Text('${o[1]} ${gLang == 'en' ? o[3] : o[2]}', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                    selected: op == o[0],
                    selectedColor: green.withValues(alpha: 0.18),
                    onSelected: (_) => setSt(() => op = o[0] as String),
                  ),
              ]),
              const SizedBox(height: 14),
              Text(tr('الأولوية', 'Priority'), style: const TextStyle(fontWeight: FontWeight.w900, color: Color(0xFF0E3A5F))),
              const SizedBox(height: 8),
              Row(children: [
                for (final pr in _reqPrio)
                  Expanded(child: GestureDetector(
                    onTap: () => setSt(() => priority = pr[0] as String),
                    child: Container(
                      margin: const EdgeInsets.symmetric(horizontal: 3),
                      padding: const EdgeInsets.symmetric(vertical: 9),
                      decoration: BoxDecoration(
                        color: priority == pr[0] ? pr[3] as Color : Colors.white,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(color: priority == pr[0] ? pr[3] as Color : Colors.grey.shade300)),
                      child: Text(gLang == 'en' ? '${pr[2]}' : '${pr[1]}', textAlign: TextAlign.center,
                          style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800,
                              color: priority == pr[0] ? Colors.white : const Color(0xFF0E3A5F))),
                    ),
                  )),
              ]),
              const SizedBox(height: 14),
              InkWell(
                onTap: () async {
                  final d = await showDatePicker(context: ctx, initialDate: DateTime.now().add(const Duration(days: 1)),
                      firstDate: DateTime.now(), lastDate: DateTime.now().add(const Duration(days: 180)));
                  if (d != null) setSt(() => preferred = d);
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.grey.shade300)),
                  child: Row(children: [
                    const Icon(Icons.event_rounded, size: 18, color: green),
                    const SizedBox(width: 10),
                    Text(preferred == null ? tr('التاريخ المفضّل (اختياري)', 'Preferred date (optional)')
                        : '${preferred!.toLocal()}'.substring(0, 10),
                        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
                    const Spacer(),
                    if (preferred != null) IconButton(icon: const Icon(Icons.close_rounded, size: 18), onPressed: () => setSt(() => preferred = null)),
                  ]),
                ),
              ),
              const SizedBox(height: 12),
              TextField(controller: noteCtrl, maxLines: 3,
                  decoration: InputDecoration(hintText: tr('ملاحظات إضافية (اختياري)', 'Additional notes (optional)'),
                      filled: true, fillColor: Colors.white,
                      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)))),
              const SizedBox(height: 16),
              SizedBox(height: 50, child: FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: green, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
                onPressed: () => Navigator.pop(ctx, true),
                icon: const Icon(Icons.send_rounded),
                label: Text(tr('إرسال الطلب', 'Send request'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
              )),
            ])),
          ]),
        ),
      ),
    );
    if (ok != true || !mounted) return;
    try {
      await context.read<AuthProvider>().api.clientAgriRequest(plantId, op,
          note: noteCtrl.text, priority: priority,
          preferredDate: preferred == null ? null : '${preferred!.toLocal()}'.substring(0, 10));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(tr('أُرسل الطلب إلى فريق الزراعة', 'Request sent to landscaping team')),
            backgroundColor: const Color(0xFF16A34A), behavior: SnackBarBehavior.floating));
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  Widget _kv(String k, dynamic v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 130, child: Text(k, style: const TextStyle(color: Colors.grey))),
          Expanded(child: Text('${v ?? '—'}', style: const TextStyle(fontWeight: FontWeight.w600))),
        ]),
      );
}
