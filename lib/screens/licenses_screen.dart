import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// «التراخيص والاشتراكات» — مطابق للموكاب المرجعي:
/// تبويبان: لوحة التحكم (KPIs + دائرة الحالة + إجراء مطلوب + حسب النوع) وتراخيصي
/// (فلترة بالحالة + بحث + بطاقات). كل مستخدم يرى تراخيصه فقط (النطاق من الخادم).
class LicensesScreen extends StatefulWidget {
  const LicensesScreen({super.key});
  @override
  State<LicensesScreen> createState() => _LicensesScreenState();
}

// هوية CARE
const _navy = Color(0xFF0F2B5B);
const _navy2 = Color(0xFF1C4FA0);
const _gold = Color(0xFFB8922F);
const _ok = Color(0xFF16A34A);
const _warn = Color(0xFFD97706);
const _bad = Color(0xFFDC2626);
const _ground = Color(0xFFEEF1F7);

Color _statusColor(String? s) => s == 'valid'
    ? _ok : s == 'expiring' ? _warn : s == 'expired' ? _bad : const Color(0xFF8A94AD);

IconData _typeIcon(String? t) {
  switch (t) {
    case 'subscription': return Icons.cloud_rounded;
    case 'certificate': return Icons.verified_rounded;
    case 'insurance': return Icons.shield_rounded;
    case 'vehicle': return Icons.directions_car_rounded;
    case 'membership': return Icons.card_membership_rounded;
    default: return Icons.account_balance_rounded;
  }
}

String _money(dynamic v) {
  final n = (v is num) ? v : num.tryParse('$v') ?? 0;
  final s = n.toStringAsFixed(n == n.roundToDouble() ? 0 : 3);
  // فاصلة آلاف
  final parts = s.split('.');
  final b = parts[0].replaceAllMapped(RegExp(r'(\d)(?=(\d{3})+$)'), (m) => '${m[1]},');
  return parts.length > 1 ? '$b.${parts[1]}' : b;
}

class _LicensesScreenState extends State<LicensesScreen> with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(length: 2, vsync: this);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _ground,
      appBar: AppBar(
        title: Text(tr('التراخيص والاشتراكات', 'Licenses & Subscriptions')),
        backgroundColor: _navy, foregroundColor: Colors.white,
        bottom: TabBar(controller: _tabs, indicatorColor: _gold, indicatorWeight: 3,
          labelColor: Colors.white, unselectedLabelColor: Colors.white70,
          labelStyle: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5),
          tabs: [
            Tab(text: tr('لوحة التحكم', 'Dashboard')),
            Tab(text: tr('تراخيصي', 'My Licenses')),
          ]),
      ),
      body: TabBarView(controller: _tabs, children: const [
        _DashboardTab(),
        _ListTab(),
      ]),
    );
  }
}

// ============================ لوحة التحكم ============================
class _DashboardTab extends StatefulWidget {
  const _DashboardTab();
  @override
  State<_DashboardTab> createState() => _DashboardTabState();
}

class _DashboardTabState extends State<_DashboardTab> with AutomaticKeepAliveClientMixin {
  Map<String, dynamic>? _d;
  bool _loading = true;
  String? _err;

  @override
  bool get wantKeepAlive => true;
  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() { _loading = true; _err = null; });
    try {
      final d = await context.read<AuthProvider>().api.licensesDashboard();
      if (mounted) setState(() { _d = d; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _err = '$e'; _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_err != null) {
      return Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
        Text(tr('تعذّر التحميل', 'Failed to load'), style: const TextStyle(color: _bad)),
        const SizedBox(height: 8),
        FilledButton(onPressed: _load, child: Text(tr('إعادة', 'Retry'))),
      ]));
    }
    final k = (_d?['kpis'] as Map?) ?? const {};
    final cur = '${_d?['currency'] ?? 'KWD'}';
    final canAll = _d?['can_see_all'] == true;
    final byStatus = ((_d?['by_status'] as List?) ?? const []).cast<Map>();
    final byType = ((_d?['by_type'] as List?) ?? const []).cast<Map>();
    final action = ((_d?['action_needed'] as List?) ?? const []).cast<Map>();
    final timeline = ((_d?['timeline'] as List?) ?? const []).cast<Map>();

    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 30), children: [
        // شارة النطاق
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(color: _navy.withValues(alpha: .06), borderRadius: BorderRadius.circular(10)),
          child: Row(children: [
            Icon(canAll ? Icons.shield_rounded : Icons.person_rounded, size: 16, color: _navy),
            const SizedBox(width: 8),
            Expanded(child: Text(
              canAll ? tr('وضع الإدارة: كل سجلات الشركة', 'Admin: all company records')
                     : tr('تُعرض مؤشرات سجلاتك فقط', 'Showing your own records only'),
              style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: _navy))),
          ]),
        ),
        const SizedBox(height: 12),
        // مربّعات KPI
        GridView.count(
          crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 10, crossAxisSpacing: 10, childAspectRatio: 1.55,
          children: [
            _kpi('${k['total'] ?? 0}', tr('إجمالي السجلات', 'Total records'), Icons.description_rounded, _navy2),
            _kpi('${k['valid'] ?? 0}', tr('سارية المفعول', 'Valid'), Icons.check_circle_rounded, _ok,
                sub: '${k['valid_pct'] ?? 0}%'),
            _kpi('${k['expiring_90'] ?? 0}', tr('تنتهي خلال 90 يوم', 'Expiring in 90d'), Icons.schedule_rounded, _warn,
                sub: tr('منها ${k['expiring_30'] ?? 0} خلال 30', '${k['expiring_30'] ?? 0} within 30d'), stripe: _warn),
            _kpi('${k['expired'] ?? 0}', tr('منتهية', 'Expired'), Icons.cancel_rounded, _bad, stripe: _bad),
            _kpi('${_money(k['total_fees'])} $cur', tr('إجمالي الرسوم', 'Total fees'), Icons.payments_rounded, _gold),
            _kpi('${k['renewals_month'] ?? 0}', tr('تجديدات خلال 30 يوم', 'Renewals in 30d'), Icons.autorenew_rounded, _navy),
            _kpi('${k['responsibles'] ?? 0}', tr('المسؤولون', 'Responsibles'), Icons.groups_rounded, _navy2),
            _kpi('${k['compliance'] ?? 0}%', tr('نسبة الالتزام', 'Compliance'), Icons.trending_up_rounded, _ok),
          ],
        ),
        const SizedBox(height: 16),
        // دائرة الحالة
        _panel(tr('حالة السجلات', 'Records status'), Icons.pie_chart_rounded,
          child: Row(children: [
            _StatusDonut(rows: byStatus),
            const SizedBox(width: 16),
            Expanded(child: Column(children: [
              for (final s in byStatus) _legendRow(s),
            ])),
          ]),
        ),
        const SizedBox(height: 12),
        // إجراء مطلوب
        _panel(tr('الأقرب انتهاءً — إجراء مطلوب', 'Action needed'), Icons.warning_amber_rounded,
          child: action.isEmpty
            ? Padding(padding: const EdgeInsets.all(14), child: Text(tr('لا شيء قريب الانتهاء 🎉', 'Nothing due 🎉'),
                style: const TextStyle(color: Color(0xFF64748B))))
            : Column(children: [for (final a in action) _actionRow(a, cur)]),
        ),
        const SizedBox(height: 12),
        // حسب النوع
        _panel(tr('حسب النوع', 'By type'), Icons.category_rounded,
          child: Column(children: [for (final t in byType) _typeBar(t, byType)]),
        ),
        const SizedBox(height: 12),
        // الخط الزمني
        _panel(tr('انتهاءات الأشهر القادمة', 'Upcoming expiries'), Icons.calendar_month_rounded,
          child: _Timeline(rows: timeline)),
      ]),
    );
  }

  Widget _kpi(String v, String l, IconData ic, Color c, {String? sub, Color? stripe}) => Container(
    padding: const EdgeInsets.all(13),
    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
      border: stripe != null ? Border(right: BorderSide(color: stripe, width: 4)) : null,
      boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: .04), blurRadius: 8, offset: const Offset(0, 2))]),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
      Container(width: 30, height: 30, decoration: BoxDecoration(color: c.withValues(alpha: .12), borderRadius: BorderRadius.circular(8)),
        child: Icon(ic, size: 17, color: c)),
      const SizedBox(height: 8),
      FittedBox(fit: BoxFit.scaleDown, alignment: AlignmentDirectional.centerStart,
        child: Text(v, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 22, color: Color(0xFF16233F)))),
      const SizedBox(height: 2),
      Text(l, maxLines: 1, overflow: TextOverflow.ellipsis,
        style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: Color(0xFF5A6683))),
      if (sub != null) Text(sub, style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: c)),
    ]),
  );

  Widget _panel(String title, IconData ic, {required Widget child}) => Container(
    padding: const EdgeInsets.all(15),
    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
      boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: .04), blurRadius: 8, offset: const Offset(0, 2))]),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [Icon(ic, size: 18, color: _navy), const SizedBox(width: 8),
        Text(title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: Color(0xFF16233F)))]),
      const SizedBox(height: 12),
      child,
    ]),
  );

  Widget _legendRow(Map s) {
    final c = _statusColor('${s['key']}');
    return Padding(padding: const EdgeInsets.symmetric(vertical: 4), child: Row(children: [
      Container(width: 12, height: 12, decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(4))),
      const SizedBox(width: 8),
      Expanded(child: Text('${s['label']}', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700))),
      Text('${s['count']}', style: const TextStyle(fontWeight: FontWeight.w900)),
      const SizedBox(width: 6),
      Text('${s['pct']}%', style: const TextStyle(fontSize: 11.5, color: Color(0xFF8A94AD), fontWeight: FontWeight.w700)),
    ]));
  }

  Widget _actionRow(Map a, String cur) {
    final c = Color(int.parse('0xFF${(a['color'] ?? '#dc2626').toString().replaceAll('#', '')}'));
    return InkWell(
      onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => LicenseDetailScreen(id: a['id'] as int))),
      child: Container(
        margin: const EdgeInsets.only(bottom: 8), padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(color: const Color(0xFFF7F9FC), borderRadius: BorderRadius.circular(11),
          border: Border.all(color: const Color(0xFFE2E7F1))),
        child: Row(children: [
          Container(width: 8, height: 36, decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(5))),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${a['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
            const SizedBox(height: 2),
            Text('${a['authority']} · ${_money(a['fees'])} $cur', maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 11.5, color: Color(0xFF5A6683), fontWeight: FontWeight.w600)),
          ])),
          Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(color: c.withValues(alpha: .12), borderRadius: BorderRadius.circular(20)),
            child: Text('${a['badge']}', style: TextStyle(color: c, fontSize: 10.5, fontWeight: FontWeight.w800))),
        ]),
      ),
    );
  }

  Widget _typeBar(Map t, List<Map> all) {
    final maxV = all.fold<int>(1, (p, e) => math.max(p, (e['count'] ?? 0) as int));
    final pct = ((t['count'] ?? 0) as int) / maxV;
    final c = Color(int.parse('0xFF${(t['color'] ?? '#0f2b5b').toString().replaceAll('#', '')}'));
    return Padding(padding: const EdgeInsets.symmetric(vertical: 5), child: Row(children: [
      SizedBox(width: 110, child: Text('${t['label']}', maxLines: 1, overflow: TextOverflow.ellipsis,
        style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700))),
      Expanded(child: ClipRRect(borderRadius: BorderRadius.circular(6),
        child: LinearProgressIndicator(value: pct, minHeight: 9, backgroundColor: const Color(0xFFF0F2F7), color: c))),
      const SizedBox(width: 8),
      Text('${t['count']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12)),
    ]));
  }
}

// دائرة الحالة (رسم يدوي)
class _StatusDonut extends StatelessWidget {
  const _StatusDonut({required this.rows});
  final List<Map> rows;
  @override
  Widget build(BuildContext context) {
    final total = rows.fold<int>(0, (p, e) => p + ((e['count'] ?? 0) as int));
    return SizedBox(width: 108, height: 108, child: CustomPaint(
      painter: _DonutPainter(rows), child: Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
        Text('$total', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 22, color: Color(0xFF16233F))),
        Text(tr('سجل', 'records'), style: const TextStyle(fontSize: 10, color: Color(0xFF8A94AD), fontWeight: FontWeight.w700)),
      ]))),
    );
  }
}

class _DonutPainter extends CustomPainter {
  _DonutPainter(this.rows);
  final List<Map> rows;
  @override
  void paint(Canvas canvas, Size size) {
    final total = rows.fold<int>(0, (p, e) => p + ((e['count'] ?? 0) as int));
    final rect = Rect.fromLTWH(9, 9, size.width - 18, size.height - 18);
    final bg = Paint()..style = PaintingStyle.stroke..strokeWidth = 15..color = const Color(0xFFE2E7F1);
    canvas.drawArc(rect, 0, 2 * math.pi, false, bg);
    if (total == 0) return;
    double start = -math.pi / 2;
    for (final r in rows) {
      final frac = ((r['count'] ?? 0) as int) / total;
      if (frac <= 0) continue;
      final sweep = frac * 2 * math.pi;
      final p = Paint()..style = PaintingStyle.stroke..strokeWidth = 15..strokeCap = StrokeCap.butt
        ..color = _statusColor('${r['key']}');
      canvas.drawArc(rect, start, sweep, false, p);
      start += sweep;
    }
  }
  @override
  bool shouldRepaint(covariant _DonutPainter old) => true;
}

// الخط الزمني (أعمدة)
class _Timeline extends StatelessWidget {
  const _Timeline({required this.rows});
  final List<Map> rows;
  @override
  Widget build(BuildContext context) {
    final maxV = rows.fold<int>(1, (p, e) => math.max(p, (e['count'] ?? 0) as int));
    return SizedBox(height: 130, child: Row(crossAxisAlignment: CrossAxisAlignment.end,
      children: [for (final r in rows) Expanded(child: Column(mainAxisAlignment: MainAxisAlignment.end, children: [
        Text('${r['count']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12)),
        const SizedBox(height: 4),
        Container(
          height: 6 + 78 * (((r['count'] ?? 0) as int) / maxV),
          margin: const EdgeInsets.symmetric(horizontal: 5),
          decoration: BoxDecoration(
            color: ((r['count'] ?? 0) as int) >= 5 ? _navy : ((r['count'] ?? 0) as int) >= 3 ? _warn
              : ((r['count'] ?? 0) as int) >= 1 ? _gold : _ok,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(6)))),
        const SizedBox(height: 5),
        Text('${r['label']}', maxLines: 1, overflow: TextOverflow.ellipsis,
          style: const TextStyle(fontSize: 9.5, color: Color(0xFF5A6683), fontWeight: FontWeight.w700)),
      ]))]),
    );
  }
}

// ============================ تراخيصي (قائمة) ============================
class _ListTab extends StatefulWidget {
  const _ListTab();
  @override
  State<_ListTab> createState() => _ListTabState();
}

class _ListTabState extends State<_ListTab> with AutomaticKeepAliveClientMixin {
  List _items = const [];
  bool _loading = true;
  String _status = 'all';
  String _q = '';

  @override
  bool get wantKeepAlive => true;
  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final d = await context.read<AuthProvider>().api.licensesMine(status: _status, q: _q);
      if (mounted) setState(() { _items = d['data'] as List; _loading = false; });
    } catch (_) { if (mounted) setState(() => _loading = false); }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return Scaffold(
      backgroundColor: _ground,
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: _gold, onPressed: _openCreate,
        icon: const Icon(Icons.add), label: Text(tr('جديد', 'New'))),
      body: Column(children: [
        // بحث
        Padding(padding: const EdgeInsets.fromLTRB(12, 12, 12, 6),
          child: TextField(
            decoration: InputDecoration(
              hintText: tr('ابحث بالاسم أو الجهة…', 'Search name or authority…'),
              prefixIcon: const Icon(Icons.search_rounded), isDense: true, filled: true, fillColor: Colors.white,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)),
            onSubmitted: (v) { _q = v; _load(); })),
        // فلترة الحالة
        SizedBox(height: 44, child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 10), children: [
          for (final s in const [('all', 'الكل', 'All'), ('action', 'إجراء مطلوب', 'Action'),
              ('valid', 'سارية', 'Valid'), ('expiring', 'قريبة', 'Expiring'), ('expired', 'منتهية', 'Expired')])
            Padding(padding: const EdgeInsets.only(left: 7, top: 6, bottom: 6),
              child: ChoiceChip(label: Text(tr(s.$2, s.$3)), selected: _status == s.$1,
                selectedColor: _navy, labelStyle: TextStyle(color: _status == s.$1 ? Colors.white : _navy, fontWeight: FontWeight.w700, fontSize: 12),
                onSelected: (_) => setState(() { _status = s.$1; _load(); }))),
        ])),
        Expanded(child: _loading
          ? const Center(child: CircularProgressIndicator())
          : _items.isEmpty
            ? ListView(children: [const SizedBox(height: 100), const Icon(Icons.description_outlined, size: 72, color: Color(0xFFB6C2D2)),
                const SizedBox(height: 12), Center(child: Text(tr('لا توجد تراخيص', 'No licenses'), style: const TextStyle(color: Color(0xFF64748B))))])
            : RefreshIndicator(onRefresh: _load, child: ListView(padding: const EdgeInsets.fromLTRB(12, 4, 12, 90),
                children: [for (final l in _items) _card(l as Map)]))),
      ]),
    );
  }

  Widget _card(Map l) {
    final c = _statusColor('${l['status']}');
    final days = (l['days_to_expiry'] ?? 0) as int;
    return InkWell(
      onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => LicenseDetailScreen(id: l['id'] as int)))
        .then((_) => _load()),
      child: Container(
        margin: const EdgeInsets.only(bottom: 10), padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: .04), blurRadius: 8, offset: const Offset(0, 2))]),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(width: 42, height: 42, decoration: BoxDecoration(color: c.withValues(alpha: .12), borderRadius: BorderRadius.circular(11)),
              child: Icon(_typeIcon('${l['type']}'), color: c)),
            const SizedBox(width: 11),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${l['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: Color(0xFF1E293B))),
              const SizedBox(height: 2),
              Text('${l['authority'] ?? ''} · ${l['name'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Color(0xFF64748B), fontSize: 11)),
            ])),
            Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(color: c.withValues(alpha: .12), borderRadius: BorderRadius.circular(20)),
              child: Text('${l['status_label']}', style: TextStyle(color: c, fontSize: 10.5, fontWeight: FontWeight.w800))),
          ]),
          const SizedBox(height: 10),
          Row(children: [
            _chip(Icons.payments_rounded, '${_money(l['fees'])} ${l['currency']}'),
            const SizedBox(width: 8),
            _chip(Icons.event_rounded, '${l['expiry_date'] ?? '—'}'),
            const Spacer(),
            Text(days < 0 ? tr('منتهٍ منذ ${-days} يوم', 'Expired ${-days}d ago')
                          : tr('خلال $days يوم', 'in ${days}d'),
              style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 11.5)),
          ]),
        ]),
      ),
    );
  }

  Widget _chip(IconData ic, String t) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
    decoration: BoxDecoration(color: const Color(0xFFF7F9FC), borderRadius: BorderRadius.circular(8)),
    child: Row(mainAxisSize: MainAxisSize.min, children: [
      Icon(ic, size: 13, color: const Color(0xFF8A94AD)), const SizedBox(width: 4),
      Text(t, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Color(0xFF5A6683)))]));

  Future<void> _openCreate() async {
    final created = await showModalBottomSheet<bool>(context: context, isScrollControlled: true,
      backgroundColor: Colors.transparent, builder: (_) => const _CreateLicenseSheet());
    if (created == true) _load();
  }
}

// ============================ التفاصيل ============================
class LicenseDetailScreen extends StatefulWidget {
  const LicenseDetailScreen({super.key, required this.id});
  final int id;
  @override
  State<LicenseDetailScreen> createState() => _LicenseDetailScreenState();
}

class _LicenseDetailScreenState extends State<LicenseDetailScreen> {
  Map<String, dynamic>? _d;
  bool _loading = true;

  @override
  void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    setState(() => _loading = true);
    try { final d = await context.read<AuthProvider>().api.licenseDetail(widget.id);
      if (mounted) setState(() { _d = d; _loading = false; }); }
    catch (_) { if (mounted) setState(() => _loading = false); }
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final c = _statusColor('${d?['status']}');
    return Scaffold(
      backgroundColor: _ground,
      appBar: AppBar(title: Text(tr('تفاصيل الترخيص', 'License Details')),
        backgroundColor: _navy, foregroundColor: Colors.white),
      floatingActionButton: (d == null) ? null : FloatingActionButton.extended(
        backgroundColor: _navy, onPressed: _renew,
        icon: const Icon(Icons.autorenew_rounded), label: Text(tr('تجديد', 'Renew'))),
      body: _loading ? const Center(child: CircularProgressIndicator())
        : d == null ? Center(child: Text(tr('تعذّر التحميل', 'Failed to load')))
        : ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 90), children: [
          // رأس
          Container(padding: const EdgeInsets.all(15),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
              boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: .04), blurRadius: 8, offset: const Offset(0, 2))]),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Container(width: 52, height: 52, decoration: BoxDecoration(color: c.withValues(alpha: .12), borderRadius: BorderRadius.circular(13)),
                  child: Icon(_typeIcon('${d['type']}'), color: c, size: 26)),
                const SizedBox(width: 12),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${d['title']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17)),
                  const SizedBox(height: 2),
                  Text('${d['name']} · ${d['type_label']}', style: const TextStyle(fontSize: 11.5, color: Color(0xFF8A94AD), fontWeight: FontWeight.w700)),
                ])),
              ]),
              const SizedBox(height: 10),
              Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(color: c.withValues(alpha: .12), borderRadius: BorderRadius.circular(20)),
                child: Text('${d['status_label']}', style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 12))),
            ])),
          const SizedBox(height: 12),
          // صورة الترخيص
          if ('${d['image_url']}'.isNotEmpty) ...[
            _sect(tr('صورة الترخيص', 'License image'), Icons.image_rounded,
              child: ClipRRect(borderRadius: BorderRadius.circular(10),
                child: _AuthImage(url: '${d['image_url']}'))),
            const SizedBox(height: 12),
          ],
          // الحقول
          _sect(tr('البيانات', 'Details'), Icons.info_outline_rounded, child: Column(children: [
            _row(tr('الجهة / المزوّد', 'Authority / Provider'), '${d['authority'] ?? '—'}'),
            _row(tr('رقم الترخيص', 'License No.'), '${d['number'] ?? '—'}'),
            _row(tr('الرسوم', 'Fees'), '${_money(d['fees'])} ${d['currency']}'),
            _row(tr('دورة التجديد', 'Renewal cycle'), '${d['renewal_cycle_label'] ?? '—'}'),
            _row(tr('تاريخ الإصدار', 'Issue date'), '${d['issue_date'] ?? '—'}'),
            _row(tr('تاريخ الانتهاء', 'Expiry date'), '${d['expiry_date'] ?? '—'}', color: c),
            _row(tr('المسؤول', 'Responsible'), '${d['responsible'] ?? '—'}'),
            if ('${d['backup'] ?? ''}'.isNotEmpty) _row(tr('مسؤول احتياطي', 'Backup'), '${d['backup']}'),
            _row(tr('إجمالي المدفوع', 'Total paid'), '${_money(d['total_paid'])} ${d['currency']}'),
          ])),
          if ('${d['note'] ?? ''}'.isNotEmpty) ...[
            const SizedBox(height: 12),
            _sect(tr('ملاحظات', 'Notes'), Icons.notes_rounded,
              child: Text('${d['note']}', style: const TextStyle(fontSize: 13, color: Color(0xFF334155)))),
          ],
          const SizedBox(height: 12),
          // السجل التاريخي
          _sect(tr('السجل التاريخي', 'History'), Icons.history_rounded, child: Column(children: [
            for (final h in ((d['history'] as List?) ?? const []).cast<Map>()) _histRow(h, '${d['currency']}'),
            if (((d['history'] as List?) ?? const []).isEmpty)
              Text(tr('لا يوجد سجل بعد', 'No history yet'), style: const TextStyle(color: Color(0xFF64748B))),
          ])),
        ]),
    );
  }

  Widget _sect(String t, IconData ic, {required Widget child}) => Container(
    padding: const EdgeInsets.all(15),
    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
      boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: .04), blurRadius: 8, offset: const Offset(0, 2))]),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [Icon(ic, size: 17, color: _navy), const SizedBox(width: 8),
        Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14))]),
      const SizedBox(height: 12), child,
    ]));

  Widget _row(String k, String v, {Color? color}) => Padding(padding: const EdgeInsets.symmetric(vertical: 5),
    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      SizedBox(width: 130, child: Text(k, style: const TextStyle(fontSize: 12.5, color: Color(0xFF8A94AD), fontWeight: FontWeight.w700))),
      Expanded(child: Text(v, style: TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800, color: color ?? const Color(0xFF16233F)))),
    ]));

  Widget _histRow(Map h, String cur) => Padding(padding: const EdgeInsets.symmetric(vertical: 6),
    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Column(children: [
        Container(width: 12, height: 12, decoration: const BoxDecoration(color: _ok, shape: BoxShape.circle)),
        Container(width: 2, height: 34, color: const Color(0xFFE2E7F1)),
      ]),
      const SizedBox(width: 10),
      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('${h['event_label']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5))),
          Text('${h['date'] ?? ''}', style: const TextStyle(fontSize: 10.5, color: Color(0xFF8A94AD), fontWeight: FontWeight.w700)),
        ]),
        const SizedBox(height: 2),
        Text([
          if ('${h['new_expiry'] ?? ''}'.isNotEmpty) tr('حتى ${h['new_expiry']}', 'until ${h['new_expiry']}'),
          if (((h['fee_paid'] ?? 0) as num) > 0) '${_money(h['fee_paid'])} $cur',
          if ('${h['by'] ?? ''}'.isNotEmpty) '${h['by']}',
        ].join(' · '), style: const TextStyle(fontSize: 11.5, color: Color(0xFF5A6683), fontWeight: FontWeight.w600)),
        if ('${h['note'] ?? ''}'.isNotEmpty)
          Text('${h['note']}', style: const TextStyle(fontSize: 11, color: Color(0xFF94A3B8))),
      ])),
    ]));

  Future<void> _renew() async {
    final res = await showModalBottomSheet<bool>(context: context, isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => _RenewSheet(id: widget.id, currentExpiry: '${_d?['expiry_date'] ?? ''}', fees: _d?['fees']));
    if (res == true) _load();
  }
}

// صورة تحتاج توكن (Bearer) — نجلبها عبر ApiClient origin مع الهيدر.
class _AuthImage extends StatelessWidget {
  const _AuthImage({required this.url});
  final String url;
  @override
  Widget build(BuildContext context) {
    return FutureBuilder<String?>(
      future: context.read<AuthProvider>().api.token,
      builder: (_, snap) {
        if (!snap.hasData) return const SizedBox(height: 160, child: Center(child: CircularProgressIndicator()));
        return Image.network(url, headers: {'Authorization': 'Bearer ${snap.data}'},
          fit: BoxFit.cover, width: double.infinity,
          errorBuilder: (_, __, ___) => Container(height: 160, color: const Color(0xFFF0F2F7),
            child: const Icon(Icons.broken_image_rounded, color: Color(0xFFB6C2D2), size: 40)));
      });
  }
}

// ============================ تجديد (Sheet) ============================
class _RenewSheet extends StatefulWidget {
  const _RenewSheet({required this.id, required this.currentExpiry, this.fees});
  final int id;
  final String currentExpiry;
  final dynamic fees;
  @override
  State<_RenewSheet> createState() => _RenewSheetState();
}

class _RenewSheetState extends State<_RenewSheet> {
  DateTime? _newExpiry;
  late final TextEditingController _fee = TextEditingController(text: '${widget.fees ?? ''}');
  final _note = TextEditingController();
  bool _saving = false;

  @override
  Widget build(BuildContext context) {
    return Padding(padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: Container(padding: const EdgeInsets.all(18),
        decoration: const BoxDecoration(color: Colors.white, borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Center(child: Container(width: 40, height: 4, decoration: BoxDecoration(color: const Color(0xFFE2E7F1), borderRadius: BorderRadius.circular(2)))),
          const SizedBox(height: 14),
          Text(tr('تجديد الترخيص', 'Renew License'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17)),
          const SizedBox(height: 14),
          ListTile(contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.event_rounded, color: _navy),
            title: Text(tr('تاريخ الانتهاء الجديد', 'New expiry date')),
            subtitle: Text(_newExpiry == null ? tr('اختر التاريخ', 'Pick a date') : '${_newExpiry!.toIso8601String().split('T').first}'),
            trailing: const Icon(Icons.chevron_left_rounded),
            onTap: () async {
              final now = DateTime.now();
              final picked = await showDatePicker(context: context, initialDate: now.add(const Duration(days: 365)),
                firstDate: now, lastDate: DateTime(now.year + 10));
              if (picked != null) setState(() => _newExpiry = picked);
            }),
          const SizedBox(height: 6),
          TextField(controller: _fee, keyboardType: TextInputType.number,
            decoration: InputDecoration(labelText: tr('الرسوم المدفوعة', 'Fee paid'), border: const OutlineInputBorder())),
          const SizedBox(height: 12),
          TextField(controller: _note, maxLines: 2,
            decoration: InputDecoration(labelText: tr('ملاحظات', 'Notes'), border: const OutlineInputBorder())),
          const SizedBox(height: 16),
          SizedBox(width: double.infinity, child: FilledButton(
            style: FilledButton.styleFrom(backgroundColor: _navy, padding: const EdgeInsets.symmetric(vertical: 14)),
            onPressed: _saving || _newExpiry == null ? null : _save,
            child: _saving ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
              : Text(tr('حفظ التجديد', 'Save renewal')))),
          const SizedBox(height: 8),
        ]),
      ));
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      await context.read<AuthProvider>().api.licenseRenew(widget.id, {
        'new_expiry': _newExpiry!.toIso8601String().split('T').first,
        'fee_paid': num.tryParse(_fee.text) ?? 0,
        'note': _note.text,
      });
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) { setState(() => _saving = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'))); }
    }
  }
}

// ============================ إنشاء (Sheet) ============================
class _CreateLicenseSheet extends StatefulWidget {
  const _CreateLicenseSheet();
  @override
  State<_CreateLicenseSheet> createState() => _CreateLicenseSheetState();
}

class _CreateLicenseSheetState extends State<_CreateLicenseSheet> {
  final _title = TextEditingController();
  final _number = TextEditingController();
  final _fee = TextEditingController();
  String _type = 'government';
  String _cycle = 'annual';
  int? _authority;
  DateTime? _expiry;
  Map<String, dynamic>? _opts;
  bool _saving = false;

  @override
  void initState() { super.initState(); _loadOpts(); }
  Future<void> _loadOpts() async {
    try { final o = await context.read<AuthProvider>().api.licenseOptions();
      if (mounted) setState(() => _opts = o); } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final types = ((_opts?['types'] as List?) ?? const []).cast<Map>();
    final cycles = ((_opts?['cycles'] as List?) ?? const []).cast<Map>();
    final auths = ((_opts?['authorities'] as List?) ?? const []).cast<Map>();
    return Padding(padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: Container(padding: const EdgeInsets.all(18),
        decoration: const BoxDecoration(color: Colors.white, borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
        child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Center(child: Container(width: 40, height: 4, decoration: BoxDecoration(color: const Color(0xFFE2E7F1), borderRadius: BorderRadius.circular(2)))),
          const SizedBox(height: 14),
          Text(tr('ترخيص / اشتراك جديد', 'New license / subscription'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17)),
          const SizedBox(height: 14),
          TextField(controller: _title, decoration: InputDecoration(labelText: tr('اسم الترخيص / الاشتراك', 'License / Subscription name'), border: const OutlineInputBorder())),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(value: _type, isExpanded: true,
            decoration: InputDecoration(labelText: tr('النوع', 'Type'), border: const OutlineInputBorder()),
            items: [for (final t in types) DropdownMenuItem(value: '${t['value']}', child: Text('${t['label']}'))],
            onChanged: (v) => setState(() => _type = v ?? 'government')),
          const SizedBox(height: 12),
          DropdownButtonFormField<int>(value: _authority, isExpanded: true,
            decoration: InputDecoration(labelText: tr('الجهة / المزوّد', 'Authority / Provider'), border: const OutlineInputBorder()),
            items: [for (final a in auths) DropdownMenuItem(value: a['id'] as int, child: Text('${a['name']}', overflow: TextOverflow.ellipsis))],
            onChanged: (v) => setState(() => _authority = v)),
          const SizedBox(height: 12),
          TextField(controller: _number, decoration: InputDecoration(labelText: tr('رقم الترخيص', 'License No.'), border: const OutlineInputBorder())),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(child: TextField(controller: _fee, keyboardType: TextInputType.number,
              decoration: InputDecoration(labelText: tr('الرسوم', 'Fees'), border: const OutlineInputBorder()))),
            const SizedBox(width: 10),
            Expanded(child: DropdownButtonFormField<String>(value: _cycle, isExpanded: true,
              decoration: InputDecoration(labelText: tr('الدورة', 'Cycle'), border: const OutlineInputBorder()),
              items: [for (final c in cycles) DropdownMenuItem(value: '${c['value']}', child: Text('${c['label']}', overflow: TextOverflow.ellipsis))],
              onChanged: (v) => setState(() => _cycle = v ?? 'annual'))),
          ]),
          const SizedBox(height: 6),
          ListTile(contentPadding: EdgeInsets.zero, leading: const Icon(Icons.event_rounded, color: _navy),
            title: Text(tr('تاريخ الانتهاء', 'Expiry date')),
            subtitle: Text(_expiry == null ? tr('اختر التاريخ', 'Pick a date') : _expiry!.toIso8601String().split('T').first),
            onTap: () async {
              final now = DateTime.now();
              final p = await showDatePicker(context: context, initialDate: now.add(const Duration(days: 365)),
                firstDate: DateTime(now.year - 5), lastDate: DateTime(now.year + 10));
              if (p != null) setState(() => _expiry = p);
            }),
          const SizedBox(height: 12),
          SizedBox(width: double.infinity, child: FilledButton(
            style: FilledButton.styleFrom(backgroundColor: _navy, padding: const EdgeInsets.symmetric(vertical: 14)),
            onPressed: _saving || _title.text.trim().isEmpty ? null : _save,
            child: _saving ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
              : Text(tr('حفظ', 'Save')))),
          const SizedBox(height: 8),
        ]))),
    );
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      await context.read<AuthProvider>().api.licenseCreate({
        'title': _title.text.trim(),
        'license_type': _type,
        'authority_id': _authority,
        'license_number': _number.text.trim(),
        'fees': num.tryParse(_fee.text) ?? 0,
        'renewal_cycle': _cycle,
        'expiry_date': _expiry?.toIso8601String().split('T').first,
      });
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) { setState(() => _saving = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'))); }
    }
  }
}
