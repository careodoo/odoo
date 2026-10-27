import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'collections_home.dart' show Coll, money;

/// شاشة إحصائيات التحصيل الكاملة داخل التطبيق — بمثيل إحصائيات الباك-إند.
class CollectionsStats extends StatefulWidget {
  const CollectionsStats({super.key});
  @override
  State<CollectionsStats> createState() => _CollectionsStatsState();
}

class _CollectionsStatsState extends State<CollectionsStats> {
  Map<String, dynamic>? _d;
  Map<String, dynamic> _opts = {'companies': [], 'customers': [], 'collectors': [], 'years': []};
  bool _loading = true;
  String _preset = 'year';
  int _year = DateTime.now().year;
  String _basis = 'invoice';
  int _partner = 0, _company = 0, _collector = 0;
  DateTime? _from, _to;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    try {
      _opts = await context.read<AuthProvider>().api.collectionsFilterOptions();
    } catch (_) {}
    await _load();
  }

  Map<String, String> _range() {
    final y = _year;
    String f = '', t = '';
    switch (_preset) {
      case 'all': return {};
      case 'custom':
        if (_from != null) f = _from!.toIso8601String().substring(0, 10);
        if (_to != null) t = _to!.toIso8601String().substring(0, 10);
        break;
      case 'ytd': f = '$y-01-01'; t = DateTime.now().toIso8601String().substring(0, 10); break;
      case 'half': f = '$y-01-01'; t = '$y-06-30'; break;
      case 'quarter': f = '$y-01-01'; t = '$y-03-31'; break;
      case 'month':
        final m = DateTime.now().month;
        final last = DateTime(y, m + 1, 0).day;
        f = '$y-${m.toString().padLeft(2, '0')}-01';
        t = '$y-${m.toString().padLeft(2, '0')}-${last.toString().padLeft(2, '0')}';
        break;
      default: f = '$y-01-01'; t = '$y-12-31';
    }
    return {if (f.isNotEmpty) 'date_from': f, if (t.isNotEmpty) 'date_to': t};
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final filters = <String, String>{
        ..._range(),
        'date_basis': _basis,
        if (_partner != 0) 'partner_id': '$_partner',
        if (_company != 0) 'company_id': '$_company',
        if (_collector != 0) 'collector_id': '$_collector',
      };
      final d = await context.read<AuthProvider>().api.collectionsStats(filters: filters);
      if (mounted) setState(() { _d = d; _loading = false; });
    } catch (e) {
      if (mounted) setState(() => _loading = false);
    }
  }

  String get _sym => '${_d?['currency'] ?? ''}';

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: gLang == 'en' ? TextDirection.ltr : TextDirection.rtl,
      child: Scaffold(
        backgroundColor: Coll.bg,
        appBar: AppBar(backgroundColor: Coll.green, foregroundColor: Colors.white, elevation: 0,
            title: Text(tr('إحصائيات التحصيل', 'Collection analytics'))),
        body: Column(children: [
          _filterBar(),
          Expanded(child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _d == null
                  ? Center(child: Text(tr('تعذّر التحميل', 'Load failed')))
                  : RefreshIndicator(onRefresh: _load, child: _body())),
        ]),
      ),
    );
  }

  Widget _filterBar() => Container(
      color: Coll.greenD,
      padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
      child: Column(children: [
        SizedBox(height: 34, child: ListView(scrollDirection: Axis.horizontal, children: [
          for (final p in [['month', tr('الشهر', 'Month')], ['quarter', tr('الربع', 'Quarter')],
            ['half', tr('نصف', 'Half')], ['year', tr('سنوي', 'Year')], ['ytd', tr('حتى تاريخه', 'YTD')], ['all', tr('الكل', 'All')]])
            Padding(padding: const EdgeInsetsDirectional.only(end: 6),
              child: _chip(p[1], _preset == p[0], () { setState(() => _preset = p[0]); _load(); })),
        ])),
        const SizedBox(height: 6),
        Row(children: [
          Expanded(child: _basisToggle()),
          const SizedBox(width: 8),
          _yearDrop(),
          const SizedBox(width: 8),
          IconButton(onPressed: _openFilters, icon: const Icon(Icons.tune_rounded, color: Colors.white), tooltip: tr('فلاتر', 'Filters')),
        ]),
      ]));

  Widget _chip(String t, bool sel, VoidCallback onTap) => InkWell(onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(alignment: Alignment.center, padding: const EdgeInsets.symmetric(horizontal: 13),
        decoration: BoxDecoration(color: sel ? Colors.white : Colors.white.withValues(alpha: 0.16),
            borderRadius: BorderRadius.circular(16)),
        child: Text(t, style: TextStyle(color: sel ? Coll.greenD : Colors.white,
            fontWeight: FontWeight.w700, fontSize: 12.5))));

  Widget _basisToggle() => Container(
      decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(10)),
      padding: const EdgeInsets.all(3),
      child: Row(children: [
        for (final b in [['invoice', tr('ت.الفاتورة', 'Inv date')], ['collection', tr('ت.التحصيل', 'Coll date')]])
          Expanded(child: InkWell(onTap: () { setState(() => _basis = b[0]); _load(); },
            child: Container(alignment: Alignment.center, padding: const EdgeInsets.symmetric(vertical: 6),
              decoration: BoxDecoration(color: _basis == b[0] ? Coll.gold : Colors.transparent,
                  borderRadius: BorderRadius.circular(8)),
              child: Text(b[1], style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 11.5))))),
      ]));

  Widget _yearDrop() => Container(
      padding: const EdgeInsets.symmetric(horizontal: 10),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(9)),
      child: DropdownButtonHideUnderline(child: DropdownButton<int>(
        value: _year, isDense: true,
        items: [for (final y in (_opts['years'] as List? ?? [_year])) DropdownMenuItem(value: y as int, child: Text('$y'))],
        onChanged: (v) { if (v != null) { setState(() => _year = v); _load(); } })));

  Future<void> _openFilters() async {
    await showModalBottomSheet(context: context, backgroundColor: Colors.white, isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (ctx) => StatefulBuilder(builder: (ctx, setM) => Directionality(
        textDirection: gLang == 'en' ? TextDirection.ltr : TextDirection.rtl,
        child: Padding(padding: const EdgeInsets.all(18),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(tr('فلاتر متقدّمة', 'Advanced filters'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17)),
            const SizedBox(height: 14),
            _optDrop(tr('العميل', 'Customer'), 'customers', _partner, (v) => setM(() => _partner = v)),
            const SizedBox(height: 10),
            _optDrop(tr('الشركة', 'Company'), 'companies', _company, (v) => setM(() => _company = v)),
            if ((_opts['collectors'] as List? ?? []).isNotEmpty) ...[
              const SizedBox(height: 10),
              _optDrop(tr('المحصّل', 'Collector'), 'collectors', _collector, (v) => setM(() => _collector = v)),
            ],
            const SizedBox(height: 10),
            Row(children: [
              Expanded(child: OutlinedButton.icon(onPressed: () async {
                  final d = await showDatePicker(context: ctx, initialDate: _from ?? DateTime.now(),
                      firstDate: DateTime(2020), lastDate: DateTime.now());
                  if (d != null) setM(() { _from = d; _preset = 'custom'; });
                }, icon: const Icon(Icons.event, size: 16), label: Text(tr('من', 'From')))),
              const SizedBox(width: 8),
              Expanded(child: OutlinedButton.icon(onPressed: () async {
                  final d = await showDatePicker(context: ctx, initialDate: _to ?? DateTime.now(),
                      firstDate: DateTime(2020), lastDate: DateTime.now());
                  if (d != null) setM(() { _to = d; _preset = 'custom'; });
                }, icon: const Icon(Icons.event, size: 16), label: Text(tr('إلى', 'To')))),
            ]),
            const SizedBox(height: 16),
            SizedBox(width: double.infinity, child: FilledButton(
              style: FilledButton.styleFrom(backgroundColor: Coll.green, padding: const EdgeInsets.symmetric(vertical: 14)),
              onPressed: () { Navigator.pop(ctx); _load(); },
              child: Text(tr('تطبيق', 'Apply'), style: const TextStyle(fontWeight: FontWeight.w800)))),
          ])))));
  }

  Widget _optDrop(String label, String key, int val, void Function(int) onCh) {
    final items = (_opts[key] as List? ?? []);
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(label, style: const TextStyle(color: Coll.slate, fontSize: 12, fontWeight: FontWeight.w700)),
      Container(padding: const EdgeInsets.symmetric(horizontal: 10),
        decoration: BoxDecoration(border: Border.all(color: Colors.black26), borderRadius: BorderRadius.circular(9)),
        child: DropdownButtonHideUnderline(child: DropdownButton<int>(
          value: val, isExpanded: true, isDense: true,
          items: [DropdownMenuItem(value: 0, child: Text(tr('الكل', 'All'))),
            for (final o in items) DropdownMenuItem(value: o['id'] as int,
              child: Text('${o['name']}', maxLines: 1, overflow: TextOverflow.ellipsis))],
          onChanged: (v) => onCh(v ?? 0)))),
    ]);
  }

  Widget _body() {
    final d = _d!;
    final k = Map<String, dynamic>.from(d['kpis'] ?? {});
    return ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 28), children: [
      // KPIs
      GridView.count(crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
        mainAxisSpacing: 10, crossAxisSpacing: 10, childAspectRatio: 1.5, children: [
          _kpi('🧾', tr('المُصدَر', 'Invoiced'), money(numOf(k['invoiced']), _sym), Coll.green,
              '${numOf(k['invoice_count']).toInt()} ${tr('فاتورة', 'inv')}'),
          _kpi('💵', tr('المحصّل', 'Collected'), money(numOf(k['collected']), _sym), Coll.gold, ''),
          _kpi('⏳', tr('المتبقّي', 'Outstanding'), money(numOf(k['outstanding']), _sym), const Color(0xFF2563EB),
              '${numOf(k['unpaid_count']).toInt()}'),
          _kpi('⚠️', tr('المتأخّرات', 'Overdue'), money(numOf(k['overdue_amount']), _sym), const Color(0xFFDC2626),
              '${numOf(k['overdue_count']).toInt()} · ${tr('م.', 'avg')} ${numOf(k['avg_days']).toInt()}${tr('ي', 'd')}'),
        ]),
      const SizedBox(height: 10),
      // نسبة + مؤشرات
      Row(children: [
        Expanded(child: _rateCard(numOf(k['rate']).toDouble())),
        const SizedBox(width: 10),
        Expanded(child: _miniCol([
          [tr('عملاء', 'Customers'), '${numOf(k['customers']).toInt()}'],
          [tr('م. أيام التحصيل', 'Avg collect days'), '${numOf(k['avg_collect_days']).toInt()}'],
          [tr('محصّلة يدوياً', 'Settled'), '${numOf(k['settled_count']).toInt()}'],
          [tr('اتصالات/زيارات', 'Activities'), '${numOf(k['activities']).toInt()}'],
        ])),
      ]),
      const SizedBox(height: 16),
      _section(tr('المُصدَر مقابل المحصّل (شهرياً)', 'Invoiced vs collected (monthly)'),
          _monthly(d['monthly'] as List? ?? [])),
      const SizedBox(height: 14),
      _section(tr('المتبقّي حسب الحالة', 'By status'), _byState(d['by_state'] as List? ?? [])),
      const SizedBox(height: 14),
      _section(tr('أعمار الديون', 'Aging'), _aging(d['aging'] as List? ?? [], numOf(k['outstanding']))),
      const SizedBox(height: 14),
      _section('🏆 ${tr('الأفضل التزاماً', 'Best payers')}',
          _custTable(d['best_customers'] as List? ?? [], best: true)),
      const SizedBox(height: 14),
      _section('🚩 ${tr('الأسوأ تأخّراً', 'Worst (overdue)')}',
          _custTable(d['worst_customers'] as List? ?? [], best: false)),
      const SizedBox(height: 14),
      _section(tr('أكبر المدينين', 'Top debtors'), _topDebtors(d['top_debtors'] as List? ?? [])),
      const SizedBox(height: 14),
      _section(tr('حسب الشركة', 'By company'), _byCompany(d['by_company'] as List? ?? [])),
      const SizedBox(height: 14),
      _section(tr('المحصّل حسب طريقة الدفع', 'By payment method'), _methods(d['methods'] as List? ?? [])),
      const SizedBox(height: 14),
      _section('🥇 ${tr('لوحة المحصّلين', 'Collectors')}', _collectors(d['collectors_board'] as List? ?? [])),
      const SizedBox(height: 14),
      _section(tr('الشيكات والوعود', 'Cheques & promises'),
          _chequesPromises(Map<String, dynamic>.from(d['cheques'] ?? {}), Map<String, dynamic>.from(d['promises'] ?? {}))),
      const SizedBox(height: 14),
      _section(tr('المتوقّع تحصيله', 'Forecast'), _forecast(d['forecast'] as List? ?? [])),
    ]);
  }

  // ---- widgets ----
  Widget _card(Widget child) => Container(padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.black.withValues(alpha: 0.05))), child: child);

  Widget _section(String title, Widget child) => _card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(title, style: const TextStyle(fontWeight: FontWeight.w900, color: Coll.ink, fontSize: 14.5)),
        const SizedBox(height: 12), child,
      ]));

  // الأيقونة فوق الرقم؛ الرقم داخل FittedBox يتقلّص ليظهر كاملاً مهما كبر (ملايين).
  Widget _kpi(String ic, String l, String v, Color c, String sub) => Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.black.withValues(alpha: 0.05))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
        Container(width: 32, height: 32, alignment: Alignment.center,
          decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(9)),
          child: Text(ic, style: const TextStyle(fontSize: 16))),
        SizedBox(width: double.infinity, child: FittedBox(fit: BoxFit.scaleDown, alignment: AlignmentDirectional.centerStart,
          child: Text(v, maxLines: 1, style: TextStyle(fontWeight: FontWeight.w900, color: c, fontSize: 21)))),
        Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(l, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w700, color: Coll.ink, fontSize: 12.5)),
          if (sub.isNotEmpty) Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Coll.slate, fontSize: 10.5)),
        ]),
      ]));

  Widget _rateCard(double rate) => _card(Column(children: [
        Text(tr('نسبة التحصيل', 'Collection rate'), style: const TextStyle(color: Coll.slate, fontSize: 12)),
        const SizedBox(height: 10),
        SizedBox(width: 92, height: 92, child: Stack(alignment: Alignment.center, children: [
          SizedBox(width: 92, height: 92, child: CircularProgressIndicator(
            value: (rate / 100).clamp(0, 1), strokeWidth: 10,
            backgroundColor: const Color(0xFFEEF2F1), color: Coll.green)),
          Text('${rate.toStringAsFixed(1)}%', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: Coll.ink)),
        ])),
      ]));

  Widget _miniCol(List<List<String>> rows) => _card(Column(children: [
        for (final r in rows) Padding(padding: const EdgeInsets.symmetric(vertical: 5),
          child: Row(children: [
            Expanded(child: Text(r[0], style: const TextStyle(color: Coll.slate, fontSize: 12.5))),
            Text(r[1], style: const TextStyle(fontWeight: FontWeight.w900, color: Coll.ink, fontSize: 14)),
          ])),
      ]));

  Widget _monthly(List m) {
    if (m.isEmpty) return _empty();
    double mx = 1;
    for (final x in m) { mx = [mx, numOf(x['invoiced']).toDouble(), numOf(x['collected']).toDouble()].reduce((a, b) => a > b ? a : b); }
    return Column(children: [
      SizedBox(height: 130, child: ListView(scrollDirection: Axis.horizontal, children: [
        for (final x in m) Padding(padding: const EdgeInsets.symmetric(horizontal: 5),
          child: Column(mainAxisAlignment: MainAxisAlignment.end, children: [
            Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
              _bar(numOf(x['invoiced']).toDouble(), mx, const Color(0xFF93C5C0)),
              const SizedBox(width: 3),
              _bar(numOf(x['collected']).toDouble(), mx, Coll.green),
            ]),
            const SizedBox(height: 4),
            Text('${x['label']}', style: const TextStyle(fontSize: 9, color: Coll.slate)),
          ])),
      ])),
      const SizedBox(height: 8),
      Row(mainAxisAlignment: MainAxisAlignment.center, children: [
        _legend(const Color(0xFF93C5C0), tr('مُصدَر', 'Invoiced')), const SizedBox(width: 16),
        _legend(Coll.green, tr('محصّل', 'Collected')),
      ]),
    ]);
  }

  Widget _bar(double v, double mx, Color c) => Container(width: 12,
      height: (v / mx * 108).clamp(2, 108), decoration: BoxDecoration(color: c,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(4))));

  Widget _legend(Color c, String t) => Row(mainAxisSize: MainAxisSize.min, children: [
        Container(width: 10, height: 10, decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(3))),
        const SizedBox(width: 4), Text(t, style: const TextStyle(fontSize: 11, color: Coll.slate)),
      ]);

  Widget _byState(List s) {
    if (s.isEmpty) return _empty();
    return Column(children: [for (final x in s) Padding(padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(children: [
        Container(width: 10, height: 10, decoration: BoxDecoration(color: Coll.state('${x['code']}'), shape: BoxShape.circle)),
        const SizedBox(width: 8),
        Expanded(child: Text('${x['label']}', style: const TextStyle(color: Coll.ink, fontSize: 13))),
        Text('${x['count']}', style: const TextStyle(color: Coll.slate, fontSize: 12)),
        const SizedBox(width: 10),
        Text(money(numOf(x['amount']), _sym), style: const TextStyle(fontWeight: FontWeight.w800, color: Coll.ink, fontSize: 12.5)),
      ]))]);
  }

  Widget _aging(List a, num total) {
    if (a.isEmpty) return _empty();
    Color ac(String b) => {'0-30': const Color(0xFF16A34A), '31-60': const Color(0xFFD97706),
      '61-90': const Color(0xFFEA580C), '90+': const Color(0xFFDC2626)}[b] ?? Coll.slate;
    return Column(children: [for (final x in a) Padding(padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(children: [
        SizedBox(width: 48, child: Text('${x['bucket']}', style: const TextStyle(fontWeight: FontWeight.w700, color: Coll.ink, fontSize: 12.5))),
        Expanded(child: ClipRRect(borderRadius: BorderRadius.circular(6),
          child: LinearProgressIndicator(value: total > 0 ? (numOf(x['amount']) / total).clamp(0, 1).toDouble() : 0,
            minHeight: 13, backgroundColor: const Color(0xFFEEF2F1), color: ac('${x['bucket']}')))),
        const SizedBox(width: 10),
        Text('${money(numOf(x['amount']), _sym)} · ${x['count']}', style: const TextStyle(color: Coll.slate, fontSize: 11)),
      ]))]);
  }

  Widget _custTable(List c, {required bool best}) {
    if (c.isEmpty) return _empty();
    return Column(children: [for (final x in c) Padding(padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(children: [
        Expanded(child: Text('${x['partner']}', maxLines: 1, overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: Coll.ink, fontSize: 13, fontWeight: FontWeight.w600))),
        if (best) ...[
          Text(money(numOf(x['collected']), _sym), style: const TextStyle(fontWeight: FontWeight.w800, color: Coll.green, fontSize: 12.5)),
          const SizedBox(width: 8), Text('${numOf(x['rate']).toStringAsFixed(0)}%', style: const TextStyle(color: Coll.slate, fontSize: 11)),
        ] else ...[
          Text(money(numOf(x['overdue']), _sym), style: const TextStyle(fontWeight: FontWeight.w800, color: Color(0xFFDC2626), fontSize: 12.5)),
          const SizedBox(width: 8), Text('${numOf(x['avg_days']).toInt()}${tr('ي', 'd')}', style: const TextStyle(color: Coll.slate, fontSize: 11)),
        ],
      ]))]);
  }

  Widget _topDebtors(List t) {
    if (t.isEmpty) return _empty();
    return Column(children: [for (var i = 0; i < t.length; i++) Padding(padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(children: [
        Text('${i + 1}', style: const TextStyle(color: Coll.slate, fontSize: 12)), const SizedBox(width: 8),
        Expanded(child: Text('${t[i]['partner']}', maxLines: 1, overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: Coll.ink, fontSize: 13))),
        Text(money(numOf(t[i]['outstanding']), _sym), style: const TextStyle(fontWeight: FontWeight.w800, color: Coll.green, fontSize: 12.5)),
      ]))]);
  }

  Widget _byCompany(List c) {
    if (c.isEmpty) return _empty();
    return Column(children: [for (final x in c) Padding(padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(children: [
        Expanded(child: Text('${x['name']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Coll.ink, fontSize: 13))),
        Text('${money(numOf(x['outstanding']), _sym)} · ${x['count']}', style: const TextStyle(fontWeight: FontWeight.w700, color: Coll.slate, fontSize: 12)),
      ]))]);
  }

  Widget _methods(List m) {
    if (m.isEmpty) return _empty();
    return Row(children: [for (final x in m) Expanded(child: Column(children: [
      Text('${x['label']}', style: const TextStyle(color: Coll.slate, fontSize: 12)),
      const SizedBox(height: 4),
      Text(money(numOf(x['amount']), _sym), style: const TextStyle(fontWeight: FontWeight.w900, color: Coll.green, fontSize: 14)),
    ]))]);
  }

  Widget _collectors(List c) {
    if (c.isEmpty) return _empty();
    return Column(children: [for (final x in c) Padding(padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(children: [
        Expanded(child: Text('${x['name']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Coll.ink, fontSize: 13))),
        Text(money(numOf(x['collected']), _sym), style: const TextStyle(fontWeight: FontWeight.w800, color: Coll.green, fontSize: 12.5)),
        const SizedBox(width: 8), Text('${numOf(x['receipts']).toInt()} ${tr('سند', 'rcpt')}', style: const TextStyle(color: Coll.slate, fontSize: 11)),
      ]))]);
  }

  Widget _chequesPromises(Map c, Map p) => Row(children: [
        _box(tr('شيكات تحت التحصيل', 'Cheques pending'), '${numOf(c['pending_count']).toInt()}', Coll.gold),
        const SizedBox(width: 8),
        _box(tr('شيكات مرتجعة', 'Bounced'), '${numOf(c['bounced_count']).toInt()}', const Color(0xFFDC2626)),
        const SizedBox(width: 8),
        _box(tr('وعود قادمة', 'Promises'), '${numOf(p['upcoming']).toInt()}', Coll.green),
        const SizedBox(width: 8),
        _box(tr('وعود متأخّرة', 'Late prom.'), '${numOf(p['overdue']).toInt()}', const Color(0xFFDC2626)),
      ]);

  Widget _box(String l, String v, Color c) => Expanded(child: Container(
      padding: const EdgeInsets.symmetric(vertical: 10), alignment: Alignment.center,
      decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)),
      child: Column(children: [
        Text(v, style: TextStyle(fontWeight: FontWeight.w900, color: c, fontSize: 18)),
        Text(l, textAlign: TextAlign.center, style: const TextStyle(color: Coll.slate, fontSize: 10)),
      ])));

  Widget _forecast(List f) {
    if (f.isEmpty) return _empty();
    return Row(children: [for (final x in f) Expanded(child: Container(
      margin: const EdgeInsets.symmetric(horizontal: 3), padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(color: const Color(0xFFF7FAF9), borderRadius: BorderRadius.circular(10),
          border: Border.all(color: const Color(0xFFE3ECEA))),
      child: Column(children: [
        Text('${x['label']}', textAlign: TextAlign.center, style: const TextStyle(color: Coll.slate, fontSize: 11)),
        const SizedBox(height: 3),
        Text(money(numOf(x['amount']), _sym), style: const TextStyle(fontWeight: FontWeight.w900, color: Coll.green, fontSize: 13)),
        Text('${numOf(x['count']).toInt()}', style: const TextStyle(color: Coll.slate, fontSize: 10)),
      ])))]);
  }

  Widget _empty() => const Padding(padding: EdgeInsets.symmetric(vertical: 10),
      child: Text('—', style: TextStyle(color: Coll.slate)));
}
