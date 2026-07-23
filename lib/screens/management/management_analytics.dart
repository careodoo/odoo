import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'management_home.dart' show Mgmt;
import 'management_list.dart' show mgmtHex, ManagementListScreen;
import 'housing_hub_screen.dart';

/// Executive analytics dashboard — KPIs + charts across all management systems.
class ManagementAnalyticsScreen extends StatefulWidget {
  const ManagementAnalyticsScreen({super.key});
  @override
  State<ManagementAnalyticsScreen> createState() => _ManagementAnalyticsScreenState();
}

class _ManagementAnalyticsScreenState extends State<ManagementAnalyticsScreen> {
  late Future<Map<String, dynamic>> _f;
  String _period = 'all';

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => setState(() => _f = context.read<AuthProvider>().api.managementAnalytics(period: _period));

  void _setPeriod(String p) {
    if (p == _period) return;
    setState(() => _period = p);
    _reload();
  }

  Widget _periodBar() {
    Widget chip(String v, String label) => Expanded(
          child: GestureDetector(
            onTap: () => _setPeriod(v),
            child: Container(
              margin: const EdgeInsets.symmetric(horizontal: 3),
              padding: const EdgeInsets.symmetric(vertical: 9),
              alignment: Alignment.center,
              decoration: BoxDecoration(
                  color: _period == v ? Mgmt.red : Colors.white,
                  borderRadius: BorderRadius.circular(11),
                  border: Border.all(color: _period == v ? Mgmt.red : Colors.black12)),
              child: Text(label, style: TextStyle(
                  fontWeight: FontWeight.w800, fontSize: 12.5,
                  color: _period == v ? Colors.white : Mgmt.slate)),
            ),
          ),
        );
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(children: [
        chip('all', tr('الكل', 'All')),
        chip('year', tr('هذه السنة', 'This year')),
        chip('month', tr('هذا الشهر', 'This month')),
      ]),
    );
  }

  static String fmt(num v) {
    final a = v.abs();
    if (a >= 1000000) return '${(v / 1000000).toStringAsFixed(a >= 10000000 ? 0 : 1)}M';
    if (a >= 1000) return '${(v / 1000).toStringAsFixed(a >= 10000 ? 0 : 1)}k';
    return v is int || v == v.roundToDouble() ? '${v.round()}' : v.toStringAsFixed(1);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Mgmt.bg,
      appBar: AppBar(
        backgroundColor: Mgmt.red, foregroundColor: Colors.white, elevation: 0,
        title: Text('📈 ${tr('لوحة التحليلات', 'Analytics')}'),
      ),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: FutureBuilder<Map<String, dynamic>>(
          future: _f,
          builder: (_, snap) {
            if (snap.hasError) {
              return ListView(children: [Padding(padding: const EdgeInsets.all(40),
                  child: Center(child: Text('${snap.error}', textAlign: TextAlign.center, style: const TextStyle(color: Mgmt.slate))))]);
            }
            if (!snap.hasData) return const Center(child: CircularProgressIndicator());
            final d = snap.data!;
            final cur = '${d['currency'] ?? ''}';
            final kpis = ((d['kpis'] as List?) ?? const []).cast<Map>();
            final charts = (d['charts'] as Map?) ?? const {};
            final attention = ((d['attention'] as List?) ?? const []).cast<Map>();
            return ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 28), children: [
              _periodBar(),
              const SizedBox(height: 8),
              if (attention.isNotEmpty) _attentionCard(attention),
              _kpiGrid(kpis, cur),
              if (charts['trend'] != null) _trendCard(charts['trend'] as Map, cur),
              Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                if (charts['housing'] != null) Expanded(child: _donutCard(
                    tr('إشغال السكن', 'Housing'),
                    [(charts['housing']['occupied'] as num).toDouble(), (charts['housing']['vacant'] as num).toDouble()],
                    [const Color(0xFF16A34A), const Color(0xFFF59E0B)],
                    ['${tr('مشغول', 'Occupied')} ${charts['housing']['occupied']}', '${tr('شاغر', 'Vacant')} ${charts['housing']['vacant']}'],
                    '${charts['housing']['pct']}%')),
                if (charts['housing'] != null && charts['fleet'] != null) const SizedBox(width: 10),
                if (charts['fleet'] != null) Expanded(child: _donutCard(
                    tr('الأسطول', 'Fleet'),
                    [(charts['fleet']['assigned'] as num).toDouble(), (charts['fleet']['free'] as num).toDouble()],
                    [const Color(0xFF2563EB), const Color(0xFF94A3B8)],
                    ['${tr('مُسند', 'Assigned')} ${charts['fleet']['assigned']}', '${tr('متاح', 'Free')} ${charts['fleet']['free']}'],
                    '${charts['fleet']['total']}')),
              ]),
              if (charts['proposals_by_state'] != null)
                _barsCard('📊 ${tr('عروض الأسعار حسب الحالة', 'Proposals by state')}',
                    (charts['proposals_by_state'] as List).cast<Map>(), cur: '', money: false,
                    onRowTap: (e) => _openProposalsState(e['code'] as String?)),
              if (charts['crm_stages'] != null)
                _barsCard('🎯 ${tr('الفرص حسب المرحلة (الإيراد المتوقع)', 'CRM pipeline by stage')}',
                    (charts['crm_stages'] as List).cast<Map>(), cur: cur, money: true),
            ]);
          },
        ),
      ),
    );
  }

  static const Map<String, String> _kpiApp = {
    'sales': 'sales', 'purchases': 'purchases', 'pipeline': 'proposals',
    'crm': 'crm', 'tenders': 'tenders', 'employees': 'employees',
  };

  void _openKpi(Map k) {
    final key = '${k['key']}';
    final accent = mgmtHex('${k['color'] ?? ''}', Mgmt.red);
    if (key == 'occupancy') {
      Navigator.push(context, MaterialPageRoute(builder: (_) => HousingHubScreen(accent: accent)));
      return;
    }
    final app = _kpiApp[key];
    if (app == null) return;
    Navigator.push(context, MaterialPageRoute(builder: (_) => ManagementListScreen(
        appKey: app, title: gLang == 'en' ? '${k['en']}' : '${k['ar']}',
        icon: '${k['icon'] ?? ''}', accent: accent)));
  }

  void _openProposalsState(String? code) {
    if (code == null) return;
    Navigator.push(context, MaterialPageRoute(builder: (_) => ManagementListScreen(
        appKey: 'proposals', title: tr('عروض الأسعار', 'Proposals'), icon: '📊',
        accent: const Color(0xFF7C3AED), initialFilters: {'state': code})));
  }

  void _openAttention(Map a) {
    Navigator.push(context, MaterialPageRoute(builder: (_) => ManagementListScreen(
        appKey: '${a['key']}', title: gLang == 'en' ? '${a['en']}' : '${a['ar']}',
        icon: '${a['icon'] ?? ''}', accent: mgmtHex('${a['color'] ?? ''}', Mgmt.red),
        initialFilters: '${a['states'] ?? ''}'.isEmpty ? null : {'state': '${a['states']}'})));
  }

  Widget _attentionCard(List<Map> items) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 8),
      decoration: BoxDecoration(
          color: Colors.white, borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFF59E0B).withValues(alpha: 0.35)),
          boxShadow: [BoxShadow(color: const Color(0xFFF59E0B).withValues(alpha: 0.08), blurRadius: 9, offset: const Offset(0, 3))]),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Text('⚡ ', style: TextStyle(fontSize: 15)),
          Text(tr('يحتاج إجراء', 'Needs attention'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: Color(0xFFB45309))),
        ]),
        const SizedBox(height: 4),
        for (final a in items)
          Material(
            color: Colors.transparent,
            child: InkWell(
              borderRadius: BorderRadius.circular(10),
              onTap: () => _openAttention(a),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 2),
                child: Row(children: [
                  Text('${a['icon'] ?? ''} ', style: const TextStyle(fontSize: 15)),
                  Expanded(child: Text(gLang == 'en' ? '${a['en']}' : '${a['ar']}',
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: Mgmt.ink))),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                    decoration: BoxDecoration(color: mgmtHex('${a['color'] ?? ''}', Mgmt.red), borderRadius: BorderRadius.circular(20)),
                    child: Text('${a['count']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 11.5)),
                  ),
                  const Icon(Icons.chevron_left_rounded, size: 17, color: Mgmt.slate),
                ]),
              ),
            ),
          ),
      ]),
    );
  }

  Widget _kpiGrid(List<Map> kpis, String cur) => GridView.count(
        crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
        mainAxisSpacing: 10, crossAxisSpacing: 10, childAspectRatio: 1.7,
        children: [
          for (final k in kpis)
            Material(
              color: Colors.white, borderRadius: BorderRadius.circular(16),
              child: InkWell(
                borderRadius: BorderRadius.circular(16),
                onTap: (_kpiApp.containsKey('${k['key']}') || '${k['key']}' == 'occupancy') ? () => _openKpi(k) : null,
                child: Container(
                  padding: const EdgeInsets.all(13),
                  decoration: BoxDecoration(borderRadius: BorderRadius.circular(16),
                      boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 9, offset: const Offset(0, 3))]),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
                    Row(children: [
                      Text('${k['icon'] ?? ''}', style: const TextStyle(fontSize: 17)),
                      const Spacer(),
                      Container(width: 9, height: 9, decoration: BoxDecoration(color: mgmtHex('${k['color'] ?? ''}', Mgmt.red), shape: BoxShape.circle)),
                    ]),
                    Text('${fmt(k['value'] as num? ?? 0)}${k['unit'] != null ? ' ${k['unit']}' : ''}',
                        maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontWeight: FontWeight.w900, fontSize: 20, color: mgmtHex('${k['color'] ?? ''}', Mgmt.ink))),
                    Row(children: [
                      Expanded(child: Text(gLang == 'en' ? '${k['en']}' : '${k['ar']}',
                          maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: Mgmt.slate, fontSize: 11, fontWeight: FontWeight.w700))),
                      if (_kpiApp.containsKey('${k['key']}') || '${k['key']}' == 'occupancy')
                        const Icon(Icons.chevron_left_rounded, size: 16, color: Mgmt.slate),
                    ]),
                  ]),
                ),
              ),
            ),
        ],
      );

  Widget _card(String title, Widget child) => Container(
        margin: const EdgeInsets.only(top: 12),
        padding: const EdgeInsets.fromLTRB(14, 13, 14, 14),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
            boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 9, offset: const Offset(0, 3))]),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: Mgmt.ink)),
          const SizedBox(height: 14),
          child,
        ]),
      );

  Widget _trendCard(Map t, String cur) {
    final labels = ((t['labels'] as List?) ?? const []).cast<String>();
    final sales = ((t['sales'] as List?) ?? const []).map((e) => (e as num).toDouble()).toList();
    final purch = ((t['purchases'] as List?) ?? const []).map((e) => (e as num).toDouble()).toList();
    final maxV = [
      ...sales, ...purch, 1.0,
    ].reduce(math.max);
    return _card('📉 ${tr('المبيعات مقابل المشتريات (٦ أشهر)', 'Sales vs Purchases (6 mo)')}', Column(children: [
      SizedBox(
        height: 130,
        child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
          for (int i = 0; i < labels.length; i++)
            Expanded(child: Column(mainAxisAlignment: MainAxisAlignment.end, children: [
              Row(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
                _bar(i < sales.length ? sales[i] : 0, maxV, const Color(0xFF16A34A)),
                const SizedBox(width: 3),
                _bar(i < purch.length ? purch[i] : 0, maxV, const Color(0xFF2563EB)),
              ]),
              const SizedBox(height: 5),
              Text(labels[i], style: const TextStyle(fontSize: 9.5, color: Mgmt.slate, fontWeight: FontWeight.w700)),
            ])),
        ]),
      ),
      const SizedBox(height: 10),
      Row(mainAxisAlignment: MainAxisAlignment.center, children: [
        _legend(const Color(0xFF16A34A), tr('المبيعات', 'Sales')),
        const SizedBox(width: 16),
        _legend(const Color(0xFF2563EB), tr('المشتريات', 'Purchases')),
      ]),
    ]));
  }

  Widget _bar(double v, double maxV, Color c) {
    final h = maxV <= 0 ? 0.0 : (v / maxV * 104).clamp(v > 0 ? 3.0 : 0.0, 104.0);
    return Container(width: 11, height: h,
        decoration: BoxDecoration(color: c, borderRadius: const BorderRadius.vertical(top: Radius.circular(3))));
  }

  Widget _legend(Color c, String label) => Row(mainAxisSize: MainAxisSize.min, children: [
        Container(width: 11, height: 11, decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(3))),
        const SizedBox(width: 5),
        Text(label, style: const TextStyle(fontSize: 11, color: Mgmt.slate, fontWeight: FontWeight.w700)),
      ]);

  Widget _donutCard(String title, List<double> values, List<Color> colors, List<String> legends, String centerText) {
    return _card(title, Column(children: [
      SizedBox(
        height: 108, width: 108,
        child: CustomPaint(
          painter: _DonutPainter(values, colors),
          child: Center(child: Text(centerText, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: Mgmt.ink))),
        ),
      ),
      const SizedBox(height: 10),
      for (int i = 0; i < legends.length; i++)
        Padding(padding: const EdgeInsets.only(top: 2), child: Align(alignment: AlignmentDirectional.centerStart, child: _legend(colors[i], legends[i]))),
    ]));
  }

  Widget _barsCard(String title, List<Map> data, {required String cur, required bool money, void Function(Map)? onRowTap}) {
    final maxV = [
      ...data.map((e) => (e['value'] as num?)?.toDouble() ?? 0), 1.0,
    ].reduce(math.max);
    return _card(title, Column(children: [
      for (final e in data)
        InkWell(
          onTap: onRowTap == null ? null : () => onRowTap(e),
          borderRadius: BorderRadius.circular(8),
          child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 5),
          child: Row(children: [
            SizedBox(width: 96, child: Text('${e['label']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 11, color: Mgmt.ink, fontWeight: FontWeight.w700))),
            const SizedBox(width: 8),
            Expanded(child: ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(
                value: (((e['value'] as num?)?.toDouble() ?? 0) / maxV).clamp(0, 1),
                minHeight: 15,
                backgroundColor: const Color(0xFFF1F5F9),
                valueColor: AlwaysStoppedAnimation(mgmtHex('${e['color'] ?? ''}', Mgmt.red)),
              ),
            )),
            const SizedBox(width: 8),
            SizedBox(width: 62, child: Text(
                money ? '${fmt(e['value'] as num? ?? 0)}${cur.isEmpty ? '' : ' $cur'}' : '${e['value']}',
                textAlign: TextAlign.end, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: Mgmt.ink))),
          ]),
        ),
        ),
    ]));
  }
}

class _DonutPainter extends CustomPainter {
  _DonutPainter(this.values, this.colors);
  final List<double> values;
  final List<Color> colors;

  @override
  void paint(Canvas canvas, Size size) {
    final total = values.fold<double>(0, (a, b) => a + b);
    final rect = Rect.fromCircle(center: size.center(Offset.zero), radius: size.width / 2 - 8);
    final stroke = 15.0;
    if (total <= 0) {
      canvas.drawArc(rect, 0, 2 * math.pi, false,
          Paint()..style = PaintingStyle.stroke..strokeWidth = stroke..color = const Color(0xFFE2E8F0));
      return;
    }
    double start = -math.pi / 2;
    for (int i = 0; i < values.length; i++) {
      final sweep = values[i] / total * 2 * math.pi;
      canvas.drawArc(rect, start, sweep, false,
          Paint()
            ..style = PaintingStyle.stroke
            ..strokeWidth = stroke
            ..strokeCap = StrokeCap.butt
            ..color = colors[i % colors.length]);
      start += sweep;
    }
  }

  @override
  bool shouldRepaint(covariant _DonutPainter old) => old.values != values;
}
