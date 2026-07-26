import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/api_client.dart';
import '../core/i18n.dart';

/// مراقبة مراكز التكلفة على الجوال: إحصائيات الميزانيات + بطاقات المراكز بنِسَب
/// الاستهلاك (أشرطة ملوّنة) + تفصيل شهري لكل مركز. للقراءة (مرآة لباك ايند).
class CostCenterScreen extends StatefulWidget {
  const CostCenterScreen({super.key});
  @override
  State<CostCenterScreen> createState() => _CostCenterScreenState();
}

class _CostCenterScreenState extends State<CostCenterScreen> {
  static const _c = Color(0xFF0F766E);   // أخضر مالي احترافي
  static const _bg = Color(0xFFF4F6F8);
  static const _ink = Color(0xFF1F2A37);
  static const _grey = Color(0xFF6B7A8D);

  Map<String, dynamic>? _ov;
  List _items = const [];
  bool _loading = true;
  String _q = '';

  ApiClient get _api => context.read<AuthProvider>().api;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final ov = await _api.costCenterOverview();
      if (mounted) setState(() => _ov = ov);
      await _loadList();
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _loadList() async {
    try {
      final l = await _api.costCenterList(q: _q.isEmpty ? null : _q);
      if (mounted) setState(() => _items = l);
    } catch (_) {}
  }

  Color _usageColor(double u) => u >= 90 ? const Color(0xFFDC2626) : u >= 70 ? const Color(0xFFF59E0B) : const Color(0xFF16A34A);
  String _n(dynamic v) { final d = (v as num?)?.toDouble() ?? 0; if (d >= 1000000) return '${(d/1000000).toStringAsFixed(1)}M'; if (d >= 1000) return '${(d/1000).toStringAsFixed(1)}K'; return d % 1 == 0 ? d.toInt().toString() : d.toStringAsFixed(1); }

  @override
  Widget build(BuildContext context) {
    final avail = _ov?['available'] != false;
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(backgroundColor: _c, foregroundColor: Colors.white,
          title: Text(tr('مراكز التكلفة', 'Cost centers')),
          actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))]),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: _c))
          : !avail
              ? Center(child: Text(tr('الموديول غير مثبّت', 'Module not installed'), style: const TextStyle(color: _grey)))
              : Column(children: [
                  _statsHeader(),
                  Container(color: Colors.white, padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
                    child: TextField(onChanged: (v) { _q = v; _loadList(); }, style: const TextStyle(fontSize: 13),
                      decoration: InputDecoration(hintText: tr('بحث عن مركز…', 'Search center…'), prefixIcon: const Icon(Icons.search_rounded, size: 19),
                        isDense: true, filled: true, fillColor: const Color(0xFFF1F4F8),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)))),
                  Expanded(child: _items.isEmpty
                      ? Center(child: Text(tr('لا مراكز تكلفة', 'No cost centers'), style: const TextStyle(color: _grey)))
                      : RefreshIndicator(onRefresh: _loadList, color: _c,
                          child: ListView.builder(padding: const EdgeInsets.all(12), itemCount: _items.length,
                              itemBuilder: (_, i) => _card(_items[i] as Map)))),
                ]),
    );
  }

  Widget _statsHeader() {
    final s = (_ov?['stats'] as Map?) ?? const {};
    final chips = <(String, String, Color)>[
      (tr('المراكز', 'Centers'), '${s['centers'] ?? 0}', _c),
      (tr('الميزانية', 'Budget'), _n(s['total']), const Color(0xFF2563EB)),
      (tr('المستهلك', 'Used'), _n(s['used']), const Color(0xFFDC2626)),
      (tr('المتبقّي', 'Remaining'), _n(s['remaining']), const Color(0xFF16A34A)),
      (tr('متوسط الاستهلاك', 'Avg usage'), '${_n(s['avg_usage'])}%', const Color(0xFF8B5CF6)),
      (tr('قارب النفاد', 'Near limit'), '${s['over'] ?? 0}', const Color(0xFFF59E0B)),
    ];
    return Container(color: _c, padding: const EdgeInsets.fromLTRB(10, 8, 10, 12),
      child: SizedBox(height: 70, child: ListView.separated(scrollDirection: Axis.horizontal, itemCount: chips.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (_, i) { final c = chips[i]; return Container(width: 110, padding: const EdgeInsets.all(9),
          decoration: BoxDecoration(color: Colors.white.withValues(alpha: .12), borderRadius: BorderRadius.circular(12)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
            Text(c.$1, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.white70, fontSize: 10.5)),
            const SizedBox(height: 4),
            Text(c.$2, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 17)),
          ])); })));
  }

  Widget _card(Map c) {
    final usage = (c['usage'] as num?)?.toDouble() ?? 0;
    final col = _usageColor(usage);
    return Container(margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: .04), blurRadius: 8, offset: const Offset(0, 2))]),
      clipBehavior: Clip.antiAlias,
      child: InkWell(onTap: () => _detail(c), child: Padding(padding: const EdgeInsets.all(13), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('${c['name']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800, color: _ink, fontSize: 14))),
          if ((c['type'] ?? '').toString().isNotEmpty) Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(color: _c.withValues(alpha: .1), borderRadius: BorderRadius.circular(20)),
              child: Text('${c['type']}', style: const TextStyle(color: _c, fontSize: 11, fontWeight: FontWeight.w700))),
        ]),
        const SizedBox(height: 10),
        ClipRRect(borderRadius: BorderRadius.circular(6),
          child: LinearProgressIndicator(value: (usage / 100).clamp(0, 1), minHeight: 8, backgroundColor: const Color(0xFFE9EDF2), color: col)),
        const SizedBox(height: 6),
        Row(children: [
          Text('${usage.toStringAsFixed(1)}% ${tr('مستهلك', 'used')}', style: TextStyle(color: col, fontWeight: FontWeight.w800, fontSize: 12)),
          const Spacer(),
          _kv(tr('الميزانية', 'Budget'), _n(c['total'])),
          const SizedBox(width: 14),
          _kv(tr('المتبقّي', 'Remaining'), _n(c['remaining'])),
        ]),
      ]))));
  }

  Widget _kv(String k, String v) => Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
    Text(k, style: const TextStyle(color: _grey, fontSize: 10)), Text(v, style: const TextStyle(color: _ink, fontWeight: FontWeight.w800, fontSize: 13))]);

  Future<void> _detail(Map brief) async {
    showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => DraggableScrollableSheet(expand: false, initialChildSize: .7, maxChildSize: .95,
        builder: (_, sc) => FutureBuilder<Map<String, dynamic>>(
          future: _api.costCenterDetail(brief['id'] as int),
          builder: (_, snap) {
            if (!snap.hasData) return const Center(child: Padding(padding: EdgeInsets.all(40), child: CircularProgressIndicator(color: _c)));
            final c = snap.data!;
            final months = (c['months'] as List?) ?? const [];
            return ListView(controller: sc, padding: const EdgeInsets.all(16), children: [
              Center(child: Container(width: 40, height: 4, decoration: BoxDecoration(color: const Color(0xFFE0E5EB), borderRadius: BorderRadius.circular(4)))),
              const SizedBox(height: 12),
              Text('${c['name']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 19, color: _ink)),
              const SizedBox(height: 12),
              Wrap(spacing: 10, runSpacing: 10, children: [
                for (final e in [
                  (tr('الميزانية', 'Budget'), _n(c['total'])), (tr('المستهلك', 'Used'), _n(c['used'])),
                  (tr('المتبقّي', 'Remaining'), _n(c['remaining'])), (tr('الاستهلاك %', 'Usage %'), '${c['usage']}%'),
                  (tr('حدّ الشراء', 'Purchase limit'), _n(c['purchase_limit'])), (tr('الفترة', 'Period'), '${c['start'] ?? '—'} → ${c['end'] ?? '—'}'),
                ]) _statBox(e.$1, e.$2),
              ]),
              const SizedBox(height: 16),
              Text(tr('التفصيل الشهري', 'Monthly breakdown'), style: const TextStyle(fontWeight: FontWeight.w800, color: _ink, fontSize: 15)),
              const SizedBox(height: 8),
              if (months.isEmpty) Text(tr('لا ميزانيات شهرية', 'No monthly budgets'), style: const TextStyle(color: _grey, fontSize: 12))
              else for (final m in months) _monthRow(m as Map),
            ]);
          })));
  }

  Widget _monthRow(Map m) {
    final usage = (m['usage'] as num?)?.toDouble() ?? 0;
    final col = _usageColor(usage);
    return Container(margin: const EdgeInsets.only(bottom: 8), padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(color: const Color(0xFFF6F8FB), borderRadius: BorderRadius.circular(12)),
      child: Column(children: [
        Row(children: [
          Expanded(child: Text('${m['label']}', style: const TextStyle(fontWeight: FontWeight.w800, color: _ink, fontSize: 13))),
          Text('${usage.toStringAsFixed(0)}%', style: TextStyle(color: col, fontWeight: FontWeight.w800, fontSize: 12)),
        ]),
        const SizedBox(height: 6),
        ClipRRect(borderRadius: BorderRadius.circular(5),
          child: LinearProgressIndicator(value: (usage / 100).clamp(0, 1), minHeight: 6, backgroundColor: const Color(0xFFE9EDF2), color: col)),
        const SizedBox(height: 6),
        Row(children: [
          _mkv(tr('الإجمالي', 'Total'), _n(m['total'])),
          _mkv(tr('مستهلك', 'Used'), _n(m['used'])),
          _mkv(tr('متبقّي', 'Left'), _n(m['remaining'])),
          if (((m['orders'] as int?) ?? 0) > 0) _mkv(tr('أوامر', 'POs'), '${m['orders']}'),
        ]),
      ]));
  }

  Widget _mkv(String k, String v) => Expanded(child: Column(children: [
    Text(k, style: const TextStyle(color: _grey, fontSize: 10)), Text(v, style: const TextStyle(color: _ink, fontWeight: FontWeight.w700, fontSize: 12.5))]));

  Widget _statBox(String k, String v) => Container(width: 152, padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(color: const Color(0xFFF6F8FB), borderRadius: BorderRadius.circular(12)),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(k, style: const TextStyle(color: _grey, fontSize: 11.5)), const SizedBox(height: 3),
      Text(v, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _ink, fontWeight: FontWeight.w900, fontSize: 15))]));
}
