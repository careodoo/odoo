import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

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

  static const _kinds = [
    ['plants', '🌳 الأشجار', 'Trees'],
    ['operations', '✂️ الأعمال', 'Works'],
    ['zones', '💧 الريّ', 'Irrigation'],
    ['species', '📖 الأنواع', 'Species'],
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
        _list = context.read<AuthProvider>().api.clientAgri(k);
      });

  @override
  Widget build(BuildContext context) {
    final s = _summary;
    return Scaffold(
      appBar: AppBar(title: Text(tr('الزراعة والحدائق', 'Landscaping'))),
      body: Column(children: [
        if (s != null && s['available'] == true)
          SizedBox(
            height: 96,
            child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.all(8), children: [
              _stat('🌳', '${s['plants'] ?? 0}', tr('أشجار ونباتات', 'Trees & plants'), const Color(0xFF16A34A)),
              _stat('🩺', '${s['plants_poor'] ?? 0}', tr('تحتاج عناية', 'Needs care'), const Color(0xFFF59E0B)),
              _stat('🔎', '${s['inspections_overdue'] ?? 0}', tr('فحص متأخّر', 'Overdue insp.'), const Color(0xFFE11D48)),
              _stat('✂️', '${s['prune_due'] ?? 0}', tr('تقليم مستحقّ', 'Pruning due'), const Color(0xFF0891B2)),
              _stat('💧', '${s['zones'] ?? 0}', tr('مناطق ريّ', 'Zones'), const Color(0xFF0EA5E9)),
              _stat('💦', '${s['water_month_m3'] ?? 0}', tr('م³ هذا الشهر', 'm³ month'), const Color(0xFF3B82F6)),
            ]),
          ),
        SizedBox(
          height: 46,
          child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 8), children: [
            for (final k in _kinds)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
                child: ChoiceChip(
                  label: Text(gLang == 'en' ? k[2] : k[1]),
                  selected: _kind == k[0],
                  onSelected: (_) => _loadKind(k[0]),
                ),
              ),
          ]),
        ),
        Expanded(
          child: FutureBuilder<List<dynamic>>(
            future: _list,
            builder: (_, snap) {
              if (!snap.hasData) return const Center(child: CircularProgressIndicator());
              final rows = snap.data!;
              if (rows.isEmpty) return Center(child: Text(tr('لا سجلات', 'No records')));
              if (_kind == 'species') {
                return GridView.builder(
                  padding: const EdgeInsets.all(10),
                  gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                      maxCrossAxisExtent: 320, childAspectRatio: 1.55, crossAxisSpacing: 10, mainAxisSpacing: 10),
                  itemCount: rows.length,
                  itemBuilder: (_, i) => _speciesCard(rows[i] as Map),
                );
              }
              return ListView.separated(
                padding: const EdgeInsets.all(8),
                itemCount: rows.length,
                separatorBuilder: (_, __) => const Divider(height: 1),
                itemBuilder: (_, i) => _row(rows[i] as Map),
              );
            },
          ),
        ),
      ]),
    );
  }

  Widget _stat(String ic, String v, String l, Color c) => Container(
        width: 132,
        margin: const EdgeInsets.symmetric(horizontal: 4),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(14)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
          Text('$ic $v', style: TextStyle(fontSize: 19, fontWeight: FontWeight.w800, color: c)),
          Text(l, style: const TextStyle(fontSize: 11, color: Colors.grey), maxLines: 1, overflow: TextOverflow.ellipsis),
        ]),
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

  Widget _speciesCard(Map s) => Card(
        clipBehavior: Clip.antiAlias,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Expanded(
            child: s['image'] != null
                ? Image.network('${s['image']}', width: double.infinity, fit: BoxFit.cover)
                : Container(width: double.infinity, color: const Color(0xFF16A34A).withValues(alpha: 0.12), child: const Center(child: Text('🌳', style: TextStyle(fontSize: 40)))),
          ),
          Padding(
            padding: const EdgeInsets.all(10),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${s['name']}', style: const TextStyle(fontWeight: FontWeight.w800), maxLines: 1, overflow: TextOverflow.ellipsis),
              const SizedBox(height: 4),
              Wrap(spacing: 4, runSpacing: 4, children: [
                _pill('${s['category']}', Colors.blueGrey),
                _pill('💧 ${s['water_need']}', const Color(0xFF0369A1)),
                if (s['heat_tolerant'] == true) _pill('🇰🇼', const Color(0xFF16A34A)),
              ]),
              const SizedBox(height: 4),
              Text('✂️ ${tr('تقليم كل', 'prune')} ${s['prune_interval_days']}${tr('ي', 'd')} · 🌱 ${s['fertilize_interval_days']}${tr('ي', 'd')}',
                  style: const TextStyle(fontSize: 11, color: Colors.grey)),
            ]),
          ),
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
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF15803D), foregroundColor: Colors.white),
              onPressed: () => _requestWork(id, '${d['name']}'),
              icon: const Icon(Icons.build),
              label: Text(tr('طلب عمل على هذه الشجرة', 'Request a work on this tree')),
            ),
          ),
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
    ['pest', '🐛', 'مكافحة آفات', 'Pest'],
    ['fertilize', '🌱', 'تسميد', 'Fertilize'],
    ['water', '💧', 'ريّ', 'Water'],
    ['other', '•', 'أخرى', 'Other'],
  ];

  Future<void> _requestWork(int plantId, String plantName) async {
    String op = 'prune';
    final noteCtrl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => StatefulBuilder(
        builder: (ctx, setSt) => AlertDialog(
          title: Text(tr('طلب عمل', 'Request work')),
          content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(plantName, style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 10),
            Wrap(spacing: 6, runSpacing: 6, children: [
              for (final o in _reqOps)
                ChoiceChip(
                  label: Text('${o[1]} ${gLang == 'en' ? o[3] : o[2]}'),
                  selected: op == o[0],
                  onSelected: (_) => setSt(() => op = o[0]),
                ),
            ]),
            const SizedBox(height: 10),
            TextField(controller: noteCtrl, decoration: InputDecoration(hintText: tr('ملاحظات (اختياري)', 'Notes (optional)'), border: const OutlineInputBorder()), maxLines: 2),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('إلغاء', 'Cancel'))),
            ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: Text(tr('إرسال', 'Send'))),
          ],
        ),
      ),
    );
    if (ok != true || !mounted) return;
    try {
      await context.read<AuthProvider>().api.clientAgriRequest(plantId, op, note: noteCtrl.text);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('أُرسل الطلب إلى فريق الزراعة', 'Request sent to landscaping team'))));
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
