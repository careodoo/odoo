import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import '../scan_screen.dart';
import '../pdf_report_screen.dart';
import 'collections_stats.dart';
import 'collections_customers.dart';
import 'collections_targets.dart';

/// ====== ثيم نظام التحصيل ======
class Coll {
  static const green = Color(0xFF0E7C5A); // زمرّدي أساسي (المال)
  static const greenD = Color(0xFF0A5E44);
  static const gold = Color(0xFFB8860B);
  static const bg = Color(0xFFF4F6F7);
  static const ink = Color(0xFF14241E);
  static const slate = Color(0xFF6B7A75);
  static const red = Color(0xFFDC2626);

  static Color state(String code) {
    switch (code) {
      case 'ok': return const Color(0xFF16A34A);
      case 'late': return const Color(0xFFD97706);
      case 'no_response': return const Color(0xFFEA580C);
      case 'refuses': return const Color(0xFFDC2626);
      case 'legal': return const Color(0xFF6D28D9);
      default: return slate;
    }
  }
}

String money(num v, [String sym = '']) {
  final s = v.toStringAsFixed(3);
  final parts = s.split('.');
  final intp = parts[0].replaceAllMapped(
      RegExp(r'\B(?=(\d{3})+(?!\d))'), (m) => ',');
  return '$intp.${parts[1]}${sym.isEmpty ? '' : ' $sym'}';
}

/// ====== الشاشة الرئيسية: لوحة المحصّل ======
class CollectionsHome extends StatefulWidget {
  const CollectionsHome({super.key, this.accent = Coll.green});
  final Color accent;
  @override
  State<CollectionsHome> createState() => _CollectionsHomeState();
}

class _CollectionsHomeState extends State<CollectionsHome> {
  Map<String, dynamic>? _d;
  bool _loading = true;
  String? _err;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _err = null; });
    try {
      final d = await context.read<AuthProvider>().api.collectionsHome();
      if (mounted) setState(() { _d = d; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _err = '$e'; _loading = false; });
    }
  }

  void _openList({String f = '', String title = ''}) {
    Navigator.push(context, MaterialPageRoute(
        builder: (_) => CollectionsList(filter: f, title: title))).then((_) => _load());
  }

  Future<void> _scan() async {
    final code = await Navigator.push<String>(
        context, MaterialPageRoute(builder: (_) => const ScanScreen(returnCode: true)));
    if (code == null || code.isEmpty || !mounted) return;
    try {
      final inv = await context.read<AuthProvider>().api.collectionsBarcode(code);
      if (!mounted) return;
      Navigator.push(context, MaterialPageRoute(
          builder: (_) => CollectionsDetail(id: inv['id'] as int))).then((_) => _load());
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(tr('لا توجد فاتورة لهذا الرمز', 'No invoice for this code'))));
      }
    }
  }

  Future<void> _sendReminders() async {
    final ok = await showDialog<bool>(context: context, builder: (_) => AlertDialog(
      title: Text(tr('إرسال تذكيرات', 'Send reminders')),
      content: Text(tr('سيُرسَل إشعار لكل محصّل بعدد ومبلغ فواتيره المتأخرة. متابعة؟',
          'Each collector gets a push with their overdue count & amount. Continue?')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(tr('إرسال', 'Send'))),
      ],
    ));
    if (ok != true || !mounted) return;
    try {
      final r = await context.read<AuthProvider>().api.collectionsRemindersSend();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(tr('أُرسلت التذكيرات إلى ${r['collectors_notified']} محصّل',
                'Reminders sent to ${r['collectors_notified']} collectors'))));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: gLang == 'en' ? TextDirection.ltr : TextDirection.rtl,
      child: Scaffold(
        backgroundColor: Coll.bg,
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _err != null
                ? _errorView()
                : RefreshIndicator(onRefresh: _load, child: _body()),
      ),
    );
  }

  Widget _errorView() => Center(
      child: Padding(padding: const EdgeInsets.all(24), child: Column(
        mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.cloud_off_rounded, size: 48, color: Coll.slate),
          const SizedBox(height: 12),
          Text(tr('تعذّر تحميل اللوحة', 'Could not load'), style: const TextStyle(fontWeight: FontWeight.w700)),
          const SizedBox(height: 12),
          FilledButton(onPressed: _load, child: Text(tr('إعادة', 'Retry'))),
        ])));

  Widget _body() {
    final d = _d!;
    final sym = '${d['currency'] ?? ''}';
    final isMgr = d['is_manager'] == true;
    final byState = Map<String, dynamic>.from(d['by_state'] ?? {});
    final fc = Map<String, dynamic>.from(d['forecast'] ?? {});
    return CustomScrollView(slivers: [
      SliverToBoxAdapter(child: _hero(d, sym, isMgr)),
      SliverPadding(
        padding: const EdgeInsets.fromLTRB(14, 0, 14, 24),
        sliver: SliverList(delegate: SliverChildListDelegate([
          const SizedBox(height: 14),
          // KPIs
          Row(children: [
            Expanded(child: _kpi(tr('مفتوحة', 'Open'), '${numOf(d['open_count']).toInt()}',
                money(numOf(d['open_amount']), sym), Icons.receipt_long_rounded, Coll.green,
                () => _openList(f: 'open', title: tr('الفواتير المفتوحة', 'Open invoices')))),
            const SizedBox(width: 10),
            Expanded(child: _kpi(tr('متأخّرة', 'Overdue'), '${numOf(d['overdue_count']).toInt()}',
                money(numOf(d['overdue_amount']), sym), Icons.warning_amber_rounded, const Color(0xFFDC2626),
                () => _openList(f: 'overdue', title: tr('المتأخّرات', 'Overdue')))),
          ]),
          const SizedBox(height: 10),
          _collectedCard(d, sym),
          const SizedBox(height: 18),
          _sectionTitle(tr('حسب الحالة', 'By status')),
          const SizedBox(height: 8),
          _statesRow(byState),
          const SizedBox(height: 18),
          _sectionTitle(tr('المتوقّع تحصيله', 'Forecast')),
          const SizedBox(height: 8),
          _forecastCard('week', tr('خلال أسبوع', 'Within a week'), fc, sym),
          _forecastCard('current_month', tr('خلال الشهر الحالي', 'This month'), fc, sym),
          _forecastCard('month', tr('خلال شهر', 'Within a month'), fc, sym),
          const SizedBox(height: 18),
          // أزرار مربّعة منظّمة — 3 في السطر
          GridView.count(
            crossAxisCount: 3, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 10, crossAxisSpacing: 10, childAspectRatio: 1,
            children: [
              _sqTile(Icons.insights_rounded, tr('الإحصائيات', 'Analytics'), const Color(0xFF2563EB),
                  () => Navigator.push(context, MaterialPageRoute(builder: (_) => const CollectionsStats()))),
              _sqTile(Icons.list_alt_rounded, tr('الفواتير', 'Invoices'), Coll.green,
                  () => _openList(title: tr('فواتير التحصيل', 'Collection invoices'))),
              _sqTile(Icons.people_alt_rounded, tr('العملاء', 'Customers'), const Color(0xFF7A1340),
                  () => Navigator.push(context, MaterialPageRoute(builder: (_) => const CollectionsCustomers()))),
              _sqTile(Icons.flag_rounded, tr('التارجت', 'Targets'), const Color(0xFF0891B2),
                  () => Navigator.push(context, MaterialPageRoute(builder: (_) => const CollectionsTargets()))),
              _sqTile(Icons.qr_code_scanner_rounded, tr('بحث', 'Search'), Coll.gold, _scan),
              if (isMgr)
                _sqTile(Icons.notifications_active_rounded, tr('تذكيرات', 'Reminders'),
                    const Color(0xFF6D28D9), _sendReminders),
            ],
          ),
        ])),
      ),
    ]);
  }

  Widget _hero(Map d, String sym, bool isMgr) => Container(
        padding: EdgeInsets.fromLTRB(18, MediaQuery.of(context).padding.top + 16, 18, 20),
        decoration: const BoxDecoration(
          gradient: LinearGradient(colors: [Coll.greenD, Coll.green],
              begin: Alignment.topLeft, end: Alignment.bottomRight),
          borderRadius: BorderRadius.vertical(bottom: Radius.circular(26)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            IconButton(onPressed: () => Navigator.maybePop(context),
                icon: const Icon(Icons.arrow_back_rounded, color: Colors.white)),
            const Text('💰', style: TextStyle(fontSize: 22)),
            const SizedBox(width: 8),
            Expanded(child: Text(tr('التحصيل', 'Collections'),
                style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900))),
            if (isMgr)
              Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2),
                    borderRadius: BorderRadius.circular(20)),
                child: Text(tr('مدير', 'Manager'),
                    style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700))),
          ]),
          const SizedBox(height: 10),
          Text(tr('إجمالي المتبقّي للتحصيل', 'Total outstanding'),
              style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 13)),
          const SizedBox(height: 4),
          Text(money(numOf(d['open_amount']), sym),
              style: const TextStyle(color: Colors.white, fontSize: 30, fontWeight: FontWeight.w900)),
        ]),
      );

  Widget _kpi(String label, String big, String sub, IconData ic, Color c, VoidCallback onTap) =>
      Material(color: Colors.white, borderRadius: BorderRadius.circular(16),
        child: InkWell(borderRadius: BorderRadius.circular(16), onTap: onTap,
          child: Container(padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.black.withValues(alpha: 0.05))),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Container(width: 30, height: 30, alignment: Alignment.center,
                    decoration: BoxDecoration(color: c.withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(9)),
                    child: Icon(ic, size: 17, color: c)),
                const Spacer(),
                Text(big, style: TextStyle(fontSize: 22, fontWeight: FontWeight.w900, color: c)),
              ]),
              const SizedBox(height: 8),
              Text(label, style: const TextStyle(fontWeight: FontWeight.w700, color: Coll.ink)),
              const SizedBox(height: 2),
              Text(sub, style: const TextStyle(fontSize: 12, color: Coll.slate)),
            ]))));

  Widget _collectedCard(Map d, String sym) => Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(borderRadius: BorderRadius.circular(16),
          gradient: LinearGradient(colors: [Coll.gold.withValues(alpha: 0.14), Colors.white]),
          border: Border.all(color: Coll.gold.withValues(alpha: 0.3))),
        child: Row(children: [
          Container(width: 42, height: 42, alignment: Alignment.center,
              decoration: BoxDecoration(color: Coll.gold.withValues(alpha: 0.18),
                  borderRadius: BorderRadius.circular(12)),
              child: const Icon(Icons.savings_rounded, color: Coll.gold)),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(tr('محصّل هذا الشهر', 'Collected this month'),
                style: const TextStyle(color: Coll.slate, fontSize: 12.5)),
            const SizedBox(height: 2),
            Text(money(numOf(d['collected_month']), sym),
                style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w900, color: Coll.gold)),
          ])),
          Text('${numOf(d['collected_month_count']).toInt()} ${tr('سند', 'receipts')}',
              style: const TextStyle(color: Coll.slate, fontSize: 12)),
        ]),
      );

  Widget _sectionTitle(String t) => Text(t,
      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: Coll.ink));

  Widget _statesRow(Map byState) {
    final items = [
      ['ok', tr('ملتزم', 'OK')],
      ['late', tr('متأخّر', 'Late')],
      ['no_response', tr('لا يتجاوب', 'No reply')],
      ['refuses', tr('يرفض', 'Refuses')],
      ['legal', tr('قانوني', 'Legal')],
    ];
    return Wrap(spacing: 8, runSpacing: 8, children: items.map((e) {
      final code = e[0]; final n = numOf(byState[code]).toInt();
      final c = Coll.state(code);
      return InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: () => _openList(f: code, title: e[1]),
        child: Container(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(color: c.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(20), border: Border.all(color: c.withValues(alpha: 0.3))),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            Container(width: 8, height: 8, decoration: BoxDecoration(color: c, shape: BoxShape.circle)),
            const SizedBox(width: 6),
            Text(e[1], style: TextStyle(color: c, fontWeight: FontWeight.w700, fontSize: 12.5)),
            const SizedBox(width: 6),
            Text('$n', style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 12.5)),
          ])),
      );
    }).toList());
  }

  Widget _forecastCard(String key, String label, Map fc, String sym) {
    final m = Map<String, dynamic>.from(fc[key] ?? {});
    final n = numOf(m['count']).toInt();
    final amt = numOf(m['amount']);
    if (n == 0) return const SizedBox.shrink();
    return Container(margin: const EdgeInsets.only(bottom: 8),
      child: Material(color: Colors.white, borderRadius: BorderRadius.circular(14),
        child: InkWell(borderRadius: BorderRadius.circular(14),
          onTap: () => _openList(f: key, title: label),
          child: Container(padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(14),
                border: Border.all(color: Colors.black.withValues(alpha: 0.05))),
            child: Row(children: [
              const Icon(Icons.event_available_rounded, color: Coll.green, size: 20),
              const SizedBox(width: 10),
              Expanded(child: Text(label, style: const TextStyle(fontWeight: FontWeight.w700, color: Coll.ink))),
              Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                Text(money(amt, sym), style: const TextStyle(fontWeight: FontWeight.w900, color: Coll.green)),
                Text('$n ${tr('فاتورة', 'inv')}', style: const TextStyle(fontSize: 11, color: Coll.slate)),
              ]),
            ])))),
    );
  }

  // مربّع احترافي منظّم (أيقونة فوق + مسمّى مختصر)
  Widget _sqTile(IconData ic, String t, Color c, VoidCallback onTap) => Material(
      color: Colors.white, borderRadius: BorderRadius.circular(16),
      child: InkWell(borderRadius: BorderRadius.circular(16), onTap: onTap,
        child: Container(
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(16),
              border: Border.all(color: c.withValues(alpha: 0.18)),
              boxShadow: [BoxShadow(color: c.withValues(alpha: 0.06), blurRadius: 10, offset: const Offset(0, 4))]),
          padding: const EdgeInsets.all(10),
          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            Container(width: 46, height: 46,
              decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(13)),
              child: Icon(ic, color: c, size: 24)),
            const SizedBox(height: 8),
            Text(t, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Coll.ink, fontWeight: FontWeight.w800, fontSize: 12.5)),
          ]))));
}

/// ====== قائمة الفواتير ======
class CollectionsList extends StatefulWidget {
  const CollectionsList({super.key, this.filter = '', this.title = ''});
  final String filter;
  final String title;
  @override
  State<CollectionsList> createState() => _CollectionsListState();
}

class _CollectionsListState extends State<CollectionsList> {
  final _rows = <dynamic>[];
  final _search = TextEditingController();
  late String _f;
  int _total = 0;
  bool _loading = true;
  String _q = '';

  @override
  void initState() {
    super.initState();
    _f = widget.filter;
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final r = await context.read<AuthProvider>().api
          .collectionsInvoices(f: _f, q: _q, limit: 500);
      if (mounted) {
        setState(() {
          _rows..clear()..addAll((r['data'] as List?) ?? []);
          _total = numOf(r['total']).toInt();
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) { setState(() => _loading = false); }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: gLang == 'en' ? TextDirection.ltr : TextDirection.rtl,
      child: Scaffold(
        backgroundColor: Coll.bg,
        appBar: AppBar(backgroundColor: Coll.green, foregroundColor: Colors.white,
            title: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              Text(widget.title.isEmpty ? tr('الفواتير', 'Invoices') : widget.title,
                  style: const TextStyle(fontSize: 17)),
              if (!_loading) Text('$_total ${tr('فاتورة', 'invoices')}',
                  style: TextStyle(fontSize: 12, color: Colors.white.withValues(alpha: 0.85), fontWeight: FontWeight.w400)),
            ]),
            elevation: 0),
        body: Column(children: [
          _searchBar(),
          _filterChips(),
          if (!_loading && _rows.isNotEmpty) _statStrip(),
          Expanded(child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _rows.isEmpty
                  ? Center(child: Text(tr('لا توجد فواتير', 'No invoices'),
                      style: const TextStyle(color: Coll.slate)))
                  : RefreshIndicator(onRefresh: _load, child: ListView.builder(
                      padding: const EdgeInsets.fromLTRB(12, 4, 12, 20),
                      itemCount: _rows.length,
                      itemBuilder: (_, i) => _invCard(_rows[i] as Map))))
        ]),
      ),
    );
  }

  Widget _searchBar() => Padding(padding: const EdgeInsets.fromLTRB(12, 10, 12, 6),
      child: TextField(controller: _search,
        textInputAction: TextInputAction.search,
        onSubmitted: (v) { _q = v.trim(); _load(); },
        decoration: InputDecoration(
          hintText: tr('بحث: رقم فاتورة / عميل', 'Search: invoice / customer'),
          prefixIcon: const Icon(Icons.search_rounded),
          suffixIcon: _q.isEmpty ? null : IconButton(icon: const Icon(Icons.close_rounded),
              onPressed: () { _search.clear(); _q = ''; _load(); }),
          filled: true, fillColor: Colors.white, isDense: true,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
        )));

  Widget _filterChips() {
    final chips = [
      ['', tr('الكل', 'All')],
      ['unpaid', tr('غير محصّلة', 'Uncollected')],
      ['paid', tr('محصّلة', 'Collected')],
      ['overdue', tr('متأخّرة', 'Overdue')],
      ['no_response', tr('لا يتجاوب', 'No reply')],
      ['refuses', tr('يرفض', 'Refuses')],
      ['legal', tr('قانوني', 'Legal')],
      ['ok', tr('ملتزم', 'OK')],
    ];
    return SizedBox(height: 42, child: ListView(scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      children: chips.map((e) {
        final sel = _f == e[0];
        return Padding(padding: const EdgeInsetsDirectional.only(end: 8),
          child: ChoiceChip(label: Text(e[1]), selected: sel,
            selectedColor: Coll.green, labelStyle: TextStyle(
                color: sel ? Colors.white : Coll.ink, fontWeight: FontWeight.w700, fontSize: 12.5),
            backgroundColor: Colors.white,
            onSelected: (_) { setState(() => _f = e[0]); _load(); }));
      }).toList()));
  }

  // شرائح إحصائية صغيرة أسفل الفلاتر (محسوبة من القائمة المعروضة)
  Widget _statStrip() {
    final customers = _rows.map((e) => (e as Map)['partner_id']).toSet().length;
    num value = 0, overdueAmt = 0;
    for (final e in _rows) {
      final m = e as Map;
      value += numOf(m['amount_residual']);
      if (m['is_overdue'] == true) overdueAmt += numOf(m['amount_residual']);
    }
    final sym = _rows.isNotEmpty ? '${(_rows.first as Map)['symbol'] ?? ''}' : '';
    Widget chip(IconData ic, String v, String l, Color c) => Container(
        margin: const EdgeInsetsDirectional.only(end: 8),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(10),
            border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(ic, size: 15, color: c), const SizedBox(width: 5),
          Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Text(v, style: TextStyle(fontWeight: FontWeight.w900, color: c, fontSize: 12.5)),
            Text(l, style: const TextStyle(color: Coll.slate, fontSize: 9.5)),
          ]),
        ]));
    return SizedBox(height: 48, child: ListView(scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.fromLTRB(12, 2, 12, 4), children: [
        chip(Icons.people_alt_rounded, '$customers', tr('عملاء', 'Customers'), const Color(0xFF2563EB)),
        chip(Icons.receipt_long_rounded, '$_total', tr('فواتير', 'Invoices'), Coll.green),
        chip(Icons.payments_rounded, money(value, sym), tr('قيمة المتبقّي', 'Outstanding'), Coll.gold),
        chip(Icons.warning_amber_rounded, money(overdueAmt, sym), tr('المتأخّر', 'Overdue'), const Color(0xFFDC2626)),
      ]));
  }

  Widget _invCard(Map r) {
    final sc = '${r['state_code'] ?? ''}';
    final c = Coll.state(sc);
    final overdue = r['is_overdue'] == true;
    final paid = '${r['payment_state'] ?? ''}' == 'paid';
    final delivered = r['delivered'] == true;
    final lastAct = '${r['last_activity'] ?? ''}';
    return Card(margin: const EdgeInsets.only(bottom: 10), elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14),
          side: BorderSide(color: Colors.black.withValues(alpha: 0.06))),
      child: InkWell(borderRadius: BorderRadius.circular(14),
        onTap: () => Navigator.push(context, MaterialPageRoute(
            builder: (_) => CollectionsDetail(id: r['id'] as int))).then((_) => _load()),
        child: Padding(padding: const EdgeInsets.all(13),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text('${r['partner'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w800, color: Coll.ink, fontSize: 14.5))),
              if (sc.isNotEmpty)
                Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                  decoration: BoxDecoration(color: c.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(20)),
                  child: Text('${r['state'] ?? ''}',
                      style: TextStyle(color: c, fontWeight: FontWeight.w700, fontSize: 11))),
            ]),
            const SizedBox(height: 4),
            Text('${r['name'] ?? ''}', style: const TextStyle(color: Coll.slate, fontSize: 12)),
            const SizedBox(height: 10),
            Row(children: [
              _miniStat(tr('المتبقّي', 'Residual'),
                  money(numOf(r['amount_residual']), '${r['symbol'] ?? ''}'), Coll.green),
              const SizedBox(width: 16),
              _miniStat(tr('الإجمالي', 'Total'),
                  money(numOf(r['amount_total']), '${r['symbol'] ?? ''}'), Coll.slate),
              const Spacer(),
              if (overdue)
                Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(color: const Color(0xFFDC2626).withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(8)),
                  child: Text('${numOf(r['days_overdue']).toInt()} ${tr('يوم تأخّر', 'd late')}',
                      style: const TextStyle(color: Color(0xFFDC2626), fontWeight: FontWeight.w700, fontSize: 11))),
            ]),
            const SizedBox(height: 9),
            const Divider(height: 1),
            const SizedBox(height: 8),
            Wrap(spacing: 6, runSpacing: 6, crossAxisAlignment: WrapCrossAlignment.center, children: [
              _tag(paid ? Icons.check_circle_rounded : Icons.pending_rounded,
                  paid ? tr('محصّلة', 'Collected') : tr('غير محصّلة', 'Uncollected'),
                  paid ? const Color(0xFF16A34A) : const Color(0xFFD97706)),
              _tag(delivered ? Icons.local_shipping_rounded : Icons.inbox_rounded,
                  delivered ? tr('مُسلّمة', 'Delivered') : tr('غير مُسلّمة', 'Not delivered'),
                  delivered ? Coll.green : Coll.slate),
              if (lastAct.isNotEmpty)
                _tag(Icons.history_rounded, '${tr('آخر نشاط', 'Last')}: $lastAct', const Color(0xFF2563EB)),
            ]),
          ]))));
  }

  Widget _tag(IconData ic, String l, Color c) => Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(color: c.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(8)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(ic, size: 12.5, color: c), const SizedBox(width: 4),
        Text(l, style: TextStyle(color: c, fontWeight: FontWeight.w700, fontSize: 10.5)),
      ]));

  Widget _miniStat(String l, String v, Color c) => Column(
      crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(l, style: const TextStyle(fontSize: 10.5, color: Coll.slate)),
        Text(v, style: TextStyle(fontWeight: FontWeight.w900, color: c, fontSize: 13)),
      ]);
}

/// ====== تفاصيل الفاتورة + الإجراءات ======
class CollectionsDetail extends StatefulWidget {
  const CollectionsDetail({super.key, required this.id});
  final int id;
  @override
  State<CollectionsDetail> createState() => _CollectionsDetailState();
}

class _CollectionsDetailState extends State<CollectionsDetail> {
  Map<String, dynamic>? _d;
  bool _loading = true;
  String? _err; // نصّ الخطأ الفعلي — يظهر للمستخدم بدل رسالة عامة

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _err = null; });
    try {
      final d = await _ap.api.collectionsInvoice(widget.id);
      if (mounted) setState(() { _d = d; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _err = '$e'; _loading = false; });
    }
  }

  AuthProvider get _ap => context.read<AuthProvider>();

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: gLang == 'en' ? TextDirection.ltr : TextDirection.rtl,
      child: Scaffold(
        backgroundColor: Coll.bg,
        appBar: AppBar(backgroundColor: Coll.green, foregroundColor: Colors.white,
            title: Text(tr('الفاتورة', 'Invoice')), elevation: 0),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _d == null
                ? Center(child: Padding(padding: const EdgeInsets.all(24),
                    child: Column(mainAxisSize: MainAxisSize.min, children: [
                      const Icon(Icons.error_outline_rounded, color: Coll.red, size: 40),
                      const SizedBox(height: 10),
                      Text(tr('تعذّر فتح الفاتورة', 'Could not open invoice'),
                          style: const TextStyle(fontWeight: FontWeight.w800, color: Coll.ink, fontSize: 15)),
                      if ((_err ?? '').isNotEmpty) ...[
                        const SizedBox(height: 8),
                        Text(_err!, textAlign: TextAlign.center,
                            style: const TextStyle(color: Coll.slate, fontSize: 12.5)),
                      ],
                      const SizedBox(height: 16),
                      FilledButton.icon(onPressed: _load,
                          style: FilledButton.styleFrom(backgroundColor: Coll.green),
                          icon: const Icon(Icons.refresh_rounded, size: 18),
                          label: Text(tr('إعادة المحاولة', 'Retry'))),
                    ])))
                : RefreshIndicator(onRefresh: _load, child: _body()),
        bottomNavigationBar: (_d == null || _d?['readonly'] == true) ? null : _actionBar(),
      ),
    );
  }

  Widget _body() {
    final d = _d!;
    final sym = '${d['symbol'] ?? ''}';
    final sc = '${d['state_code'] ?? ''}';
    final payments = (d['payments'] as List?) ?? [];
    final activities = (d['activities'] as List?) ?? [];
    return ListView(padding: const EdgeInsets.fromLTRB(14, 14, 14, 24), children: [
      // بطاقة المبلغ
      Container(padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(borderRadius: BorderRadius.circular(18),
          gradient: const LinearGradient(colors: [Coll.greenD, Coll.green])),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: InkWell(
              onTap: d['partner_id'] == null ? null : () => Navigator.push(context, MaterialPageRoute(
                  builder: (_) => CustomerProfile(partnerId: d['partner_id'] as int))).then((_) => _load()),
              child: Row(children: [
                Flexible(child: Text('${d['partner'] ?? ''}',
                    style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900,
                        decoration: TextDecoration.underline, decorationColor: Colors.white54))),
                const SizedBox(width: 4),
                const Icon(Icons.open_in_new_rounded, color: Colors.white70, size: 15),
              ]))),
            if (sc.isNotEmpty)
              Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.22),
                    borderRadius: BorderRadius.circular(20)),
                child: Text('${d['state'] ?? ''}',
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 11.5))),
          ]),
          const SizedBox(height: 2),
          Text('${d['name'] ?? ''}', style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12.5)),
          const SizedBox(height: 14),
          Row(children: [
            _heroAmt(tr('المتبقّي', 'Residual'), money(numOf(d['amount_residual']), sym), true),
            const SizedBox(width: 20),
            _heroAmt(tr('الإجمالي', 'Total'), money(numOf(d['amount_total']), sym), false),
            const SizedBox(width: 20),
            _heroAmt(tr('محصّل', 'Collected'), money(numOf(d['collected_total']), sym), false),
          ]),
        ])),
      const SizedBox(height: 12),
      // تواريخ
      _infoRow(Icons.event_rounded, tr('تاريخ الفاتورة', 'Invoice date'), '${d['invoice_date'] ?? '-'}'),
      _infoRow(Icons.event_busy_rounded, tr('تاريخ الاستحقاق', 'Due date'), '${d['date_due'] ?? '-'}',
          trailing: d['is_overdue'] == true
              ? '${numOf(d['days_overdue']).toInt()} ${tr('يوم تأخّر', 'days late')}' : null),
      if ('${d['collection_date'] ?? ''}'.isNotEmpty)
        _infoRow(Icons.event_available_rounded, tr('تاريخ التحصيل', 'Collection date'), '${d['collection_date']}'),
      if ('${d['forecast'] ?? ''}'.isNotEmpty)
        _infoRow(Icons.schedule_rounded, tr('المتوقّع', 'Forecast'), '${d['forecast']}'),
      if ('${d['collector'] ?? ''}'.isNotEmpty)
        _infoRow(Icons.person_rounded, tr('المحصّل', 'Collector'), '${d['collector']}'),
      // اتصال العميل
      if ('${d['partner_phone'] ?? ''}'.isNotEmpty || '${d['partner_mobile'] ?? ''}'.isNotEmpty)
        _contactRow(d),
      if ('${d['note'] ?? ''}'.isNotEmpty) ...[
        const SizedBox(height: 6),
        Container(padding: const EdgeInsets.all(12), decoration: BoxDecoration(
            color: const Color(0xFFFFF7E6), borderRadius: BorderRadius.circular(12)),
          child: Row(children: [const Icon(Icons.sticky_note_2_rounded, size: 18, color: Coll.gold),
            const SizedBox(width: 8), Expanded(child: Text('${d['note']}',
                style: const TextStyle(color: Coll.ink, fontSize: 13)))])),
      ],
      const SizedBox(height: 10),
      // حالة التسليم
      _deliveryCard(d),
      const SizedBox(height: 8),
      Row(children: [
        if (d['has_pdf'] == true)
          Expanded(child: OutlinedButton.icon(onPressed: () => _openPdf(d),
            icon: const Icon(Icons.picture_as_pdf_rounded, size: 18),
            label: Text(tr('عرض الفاتورة', 'View invoice')),
            style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFF7A1340),
                side: const BorderSide(color: Color(0xFF7A1340))))),
        if (d['has_pdf'] == true) const SizedBox(width: 8),
        Expanded(child: OutlinedButton.icon(onPressed: () => Navigator.push(context, MaterialPageRoute(
            builder: (_) => CustomerStatement(partnerId: d['partner_id'] as int))),
          icon: const Icon(Icons.account_balance_wallet_rounded, size: 18),
          label: Text(tr('كشف الحساب', 'Statement')),
          style: OutlinedButton.styleFrom(foregroundColor: Coll.green,
              side: const BorderSide(color: Coll.green)))),
      ]),
      const SizedBox(height: 18),
      // الدفعات
      _blockTitle(tr('الدفعات', 'Payments'), '${payments.length}'),
      if (payments.isEmpty) _emptyHint(tr('لا دفعات بعد', 'No payments yet'))
      else ...payments.map((p) => _payTile(p as Map, sym)),
      const SizedBox(height: 18),
      // الأنشطة
      _blockTitle(tr('الاتصالات والزيارات', 'Calls & visits'), '${activities.length}'),
      if (activities.isEmpty) _emptyHint(tr('لا أنشطة بعد', 'No activities yet'))
      else ...activities.map((a) => _actTile(a as Map)),
    ]);
  }

  Widget _deliveryCard(Map d) {
    final delivered = d['delivered'] == true;
    final c = delivered ? Coll.green : Coll.slate;
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: (delivered || _d?['readonly'] == true) ? () => _showDeliveryInfo(d) : _deliverDialog,
      child: Container(padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(color: delivered ? const Color(0xFFEAF6F1) : Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: c.withValues(alpha: delivered ? 0.3 : 0.12))),
        child: Row(children: [
          Icon(delivered ? Icons.mark_email_read_rounded : Icons.local_shipping_outlined, color: c, size: 20),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(delivered ? tr('تم تسليم الفاتورة', 'Invoice delivered') : tr('لم تُسلَّم الفاتورة بعد', 'Not delivered yet'),
                style: const TextStyle(fontWeight: FontWeight.w800, color: Coll.ink, fontSize: 13.5)),
            if (delivered)
              Text('${d['delivery_method_label'] ?? ''} · ${d['delivery_date'] ?? ''}'
                  '${d['has_delivery_attachment'] == true ? tr(' · مرفق ✓', ' · attach ✓') : ''}',
                  style: const TextStyle(color: Coll.slate, fontSize: 11.5)),
          ])),
          Icon(Icons.chevron_left_rounded, color: c),
        ])),
    );
  }

  Future<void> _openPdf(Map d) async {
    final url = await _ap.api.collectionsPdfUrl(widget.id);
    if (!mounted) return;
    Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
        url: url, title: tr('فاتورة ${d['name'] ?? ''}', 'Invoice ${d['name'] ?? ''}'),
        fileName: 'invoice-${d['name'] ?? ''}.pdf')));
  }

  // عرض بيانات وصورة التسليم لفاتورة مُسلّمة (بدل فتح نموذج التسجيل من جديد)
  Future<void> _showDeliveryInfo(Map d) async {
    final hasImg = d['has_delivery_attachment'] == true;
    final imgUrl = hasImg ? await _ap.api.collectionsDeliveryImageUrl(widget.id) : null;
    if (!mounted) return;
    await showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => Directionality(
        textDirection: gLang == 'en' ? TextDirection.ltr : TextDirection.rtl,
        child: Padding(padding: EdgeInsets.fromLTRB(18, 16, 18, 16 + MediaQuery.of(context).viewInsets.bottom),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              const Icon(Icons.mark_email_read_rounded, color: Coll.green),
              const SizedBox(width: 8),
              Text(tr('بيانات التسليم', 'Delivery details'),
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: Coll.ink)),
            ]),
            const SizedBox(height: 12),
            _dRow(tr('طريقة التسليم', 'Method'), '${d['delivery_method_label'] ?? '—'}'),
            _dRow(tr('تاريخ التسليم', 'Date'), '${d['delivery_date'] ?? '—'}'),
            _dRow(tr('سلّمها', 'By'), '${d['delivered_by'] ?? '—'}'),
            if ('${d['delivery_note'] ?? ''}'.isNotEmpty) _dRow(tr('ملاحظة', 'Note'), '${d['delivery_note']}'),
            const SizedBox(height: 12),
            if (hasImg && imgUrl != null) ...[
              Text(tr('صورة إثبات التسليم', 'Proof photo'),
                  style: const TextStyle(fontWeight: FontWeight.w700, color: Coll.slate, fontSize: 12.5)),
              const SizedBox(height: 8),
              ClipRRect(borderRadius: BorderRadius.circular(12),
                child: Image.network(imgUrl, fit: BoxFit.cover, width: double.infinity,
                  loadingBuilder: (c, ch, p) => p == null ? ch : const SizedBox(height: 160, child: Center(child: CircularProgressIndicator())),
                  errorBuilder: (c, e, s) => Container(height: 120, alignment: Alignment.center,
                      color: const Color(0xFFF1F3F4), child: Text(tr('تعذّر تحميل الصورة', 'Image failed'), style: const TextStyle(color: Coll.slate))))),
            ] else
              Text(tr('لا توجد صورة مرفقة', 'No attached photo'), style: const TextStyle(color: Coll.slate)),
            const SizedBox(height: 14),
            SizedBox(width: double.infinity, child: OutlinedButton.icon(
              onPressed: () { Navigator.pop(context); _deliverDialog(); },
              icon: const Icon(Icons.edit_rounded, size: 18),
              label: Text(tr('تعديل التسليم', 'Edit delivery')))),
          ]))));
  }

  Widget _dRow(String l, String v) => Padding(padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        SizedBox(width: 110, child: Text(l, style: const TextStyle(color: Coll.slate, fontSize: 12.5))),
        Expanded(child: Text(v, style: const TextStyle(fontWeight: FontWeight.w700, color: Coll.ink, fontSize: 13))),
      ]));

  Future<void> _deliverDialog() async {
    String method = 'hand';
    final note = TextEditingController();
    String? photo;
    final res = await showModalBottomSheet<bool>(context: context, isScrollControlled: true,
      backgroundColor: Colors.white, shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (ctx) => StatefulBuilder(builder: (ctx, setM) => Directionality(
        textDirection: gLang == 'en' ? TextDirection.ltr : TextDirection.rtl,
        child: Padding(padding: EdgeInsets.fromLTRB(18, 16, 18, MediaQuery.of(ctx).viewInsets.bottom + 18),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            _sheetHandle(), _sheetTitle(tr('تسليم الفاتورة للعميل', 'Deliver invoice')),
            const SizedBox(height: 10),
            Wrap(spacing: 8, children: [
              ['hand', tr('✋ يدوي', '✋ Hand')], ['email', tr('📧 إلكتروني/إيميل', '📧 Email')], ['courier', tr('🚚 مندوب', '🚚 Courier')],
            ].map((m) => ChoiceChip(label: Text(m[1]), selected: method == m[0],
                selectedColor: Coll.green,
                labelStyle: TextStyle(color: method == m[0] ? Colors.white : Coll.ink),
                onSelected: (_) => setM(() => method = m[0]))).toList()),
            const SizedBox(height: 12),
            _field(note, tr('ملاحظة التسليم', 'Delivery note')),
            const SizedBox(height: 10),
            OutlinedButton.icon(onPressed: () async {
                final x = await ImagePicker().pickImage(source: ImageSource.camera, imageQuality: 65, maxWidth: 1600);
                if (x != null) { final b = await x.readAsBytes(); setM(() => photo = base64Encode(b)); }
              },
              icon: Icon(photo == null ? Icons.add_a_photo_rounded : Icons.check_circle_rounded,
                  color: photo == null ? Coll.slate : Coll.green),
              label: Text(photo == null ? tr('إرفاق صورة التسليم (اختياري)', 'Attach photo (optional)')
                  : tr('أُرفقت الصورة ✓', 'Photo attached ✓'))),
            const SizedBox(height: 16),
            SizedBox(width: double.infinity, child: FilledButton(
              style: FilledButton.styleFrom(backgroundColor: Coll.green,
                  padding: const EdgeInsets.symmetric(vertical: 14)),
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(tr('تأكيد التسليم', 'Confirm delivery'), style: const TextStyle(fontWeight: FontWeight.w800)))),
          ])))));
    if (res != true) return;
    try {
      await _ap.api.collectionsDeliver(widget.id, {
        'method': method, 'note': note.text.trim(),
        if (photo != null) 'attachment': photo,
      });
      _snack(tr('سُجّل تسليم الفاتورة', 'Delivery recorded'));
      _load();
    } catch (e) { _snack('$e'); }
  }

  Widget _heroAmt(String l, String v, bool big) => Column(
      crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(l, style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 11)),
        const SizedBox(height: 2),
        Text(v, style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: big ? 17 : 13)),
      ]);

  Widget _infoRow(IconData ic, String l, String v, {String? trailing}) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(children: [
        Icon(ic, size: 18, color: Coll.slate), const SizedBox(width: 10),
        Text(l, style: const TextStyle(color: Coll.slate, fontSize: 13)),
        const Spacer(),
        Text(v, style: const TextStyle(color: Coll.ink, fontWeight: FontWeight.w700, fontSize: 13)),
        if (trailing != null) ...[const SizedBox(width: 8),
          Container(padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
            decoration: BoxDecoration(color: const Color(0xFFDC2626).withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(7)),
            child: Text(trailing, style: const TextStyle(color: Color(0xFFDC2626),
                fontWeight: FontWeight.w700, fontSize: 11)))],
      ]));

  Widget _contactRow(Map d) {
    final phone = '${d['partner_mobile'] ?? ''}'.isNotEmpty
        ? '${d['partner_mobile']}' : '${d['partner_phone'] ?? ''}';
    return Padding(padding: const EdgeInsets.symmetric(vertical: 6), child: Row(children: [
      const Icon(Icons.phone_rounded, size: 18, color: Coll.slate), const SizedBox(width: 10),
      Text(tr('هاتف العميل', 'Customer phone'), style: const TextStyle(color: Coll.slate, fontSize: 13)),
      const Spacer(),
      Text(phone, style: const TextStyle(color: Coll.ink, fontWeight: FontWeight.w700, fontSize: 13)),
      const SizedBox(width: 8),
      InkWell(onTap: () => launchUrl(Uri.parse('tel:$phone')),
        child: const Icon(Icons.call_rounded, size: 20, color: Coll.green)),
    ]));
  }

  Widget _blockTitle(String t, String count) => Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(children: [
        Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: Coll.ink)),
        const SizedBox(width: 8),
        Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
          decoration: BoxDecoration(color: Coll.green.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(20)),
          child: Text(count, style: const TextStyle(color: Coll.green, fontWeight: FontWeight.w800, fontSize: 12))),
      ]));

  Widget _emptyHint(String t) => Padding(padding: const EdgeInsets.symmetric(vertical: 10),
      child: Text(t, style: const TextStyle(color: Coll.slate, fontStyle: FontStyle.italic)));

  Widget _payTile(Map p, String sym) {
    final isCheque = p['method'] == 'cheque';
    return Container(margin: const EdgeInsets.only(bottom: 8), padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(isCheque ? Icons.receipt_rounded
              : p['method'] == 'transfer' ? Icons.swap_horiz_rounded : Icons.payments_rounded,
              size: 18, color: Coll.green),
          const SizedBox(width: 8),
          Text('${p['method_label'] ?? ''}',
              style: const TextStyle(fontWeight: FontWeight.w700, color: Coll.ink, fontSize: 13)),
          const Spacer(),
          Text(money(numOf(p['amount']), sym),
              style: const TextStyle(fontWeight: FontWeight.w900, color: Coll.green, fontSize: 14)),
        ]),
        const SizedBox(height: 4),
        Row(children: [
          Text('${p['name'] ?? ''} · ${p['date'] ?? ''}',
              style: const TextStyle(color: Coll.slate, fontSize: 11.5)),
          const Spacer(),
          if (p['is_partial'] == true)
            Container(padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
              decoration: BoxDecoration(color: const Color(0xFFD97706).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(7)),
              child: Text(tr('جزئي · متبقٍّ ${money(numOf(p['residual_after']), sym)}',
                  'Partial · left ${money(numOf(p['residual_after']), sym)}'),
                  style: const TextStyle(color: Color(0xFFD97706), fontWeight: FontWeight.w700, fontSize: 10.5))),
        ]),
        if (isCheque && '${p['cheque_no'] ?? ''}'.isNotEmpty)
          Padding(padding: const EdgeInsets.only(top: 4),
            child: Text('${tr('شيك', 'Cheque')} ${p['cheque_no']} — ${p['cheque_bank'] ?? ''}',
                style: const TextStyle(color: Coll.slate, fontSize: 11.5))),
        // زر التراجع عن الدفعة — لمدير التحصيل فقط
        if (_d?['is_manager'] == true && p['id'] != null) ...[
          const Divider(height: 14),
          Align(alignment: AlignmentDirectional.centerEnd,
            child: TextButton.icon(
              style: TextButton.styleFrom(foregroundColor: Coll.red,
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 2)),
              onPressed: _loading ? null : () => _undoPayment(p),
              icon: const Icon(Icons.undo_rounded, size: 16),
              label: Text(tr('تراجع عن التحصيل', 'Undo payment'),
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12)))),
        ],
      ]));
  }

  // ===== تراجع عن دفعة تحصيل (مدير التحصيل) =====
  Future<void> _undoPayment(Map p) async {
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      title: Text(tr('تراجع عن التحصيل', 'Undo payment')),
      content: Text(tr('سيتم حذف دفعة التحصيل (${money(numOf(p['amount']), '')}) وإزالة التحصيل عن الفاتورة. متابعة؟',
          'This will delete the payment and remove it from the invoice. Continue?')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(style: FilledButton.styleFrom(backgroundColor: Coll.red),
            onPressed: () => Navigator.pop(c, true), child: Text(tr('تراجع', 'Undo'))),
      ]));
    if (ok != true || !mounted) return;
    try {
      await _ap.api.collectionsUndoPayment(p['id'] as int);
      if (!mounted) return;
      _snack(tr('تمّ التراجع عن التحصيل', 'Payment undone'));
      await _load();
    } catch (e) {
      if (mounted) _snack('$e');
    }
  }

  Widget _actTile(Map a) {
    return Container(margin: const EdgeInsets.only(bottom: 8), padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Text('${a['kind_label'] ?? ''}',
              style: const TextStyle(fontWeight: FontWeight.w700, color: Coll.ink, fontSize: 13)),
          const Spacer(),
          if ('${a['outcome_label'] ?? ''}'.isNotEmpty)
            Text('${a['outcome_label']}', style: const TextStyle(color: Coll.green, fontWeight: FontWeight.w700, fontSize: 12)),
        ]),
        const SizedBox(height: 4),
        Text('${a['comment'] ?? ''}', style: const TextStyle(color: Coll.ink, fontSize: 13)),
        const SizedBox(height: 4),
        Row(children: [
          Text('${a['date'] ?? ''}', style: const TextStyle(color: Coll.slate, fontSize: 11)),
          if ('${a['promise_date'] ?? ''}'.isNotEmpty) ...[const Spacer(),
            Text('${tr('وعد بالدفع', 'Promise')}: ${a['promise_date']}',
                style: const TextStyle(color: Coll.gold, fontWeight: FontWeight.w700, fontSize: 11))],
        ]),
      ]));
  }

  // ---- شريط الإجراءات السفلي ----
  Widget _actionBar() {
    final d = _d!;
    final canLegal = d['can_legal'] == true;
    return SafeArea(child: Padding(padding: const EdgeInsets.fromLTRB(10, 8, 10, 10),
      child: Row(children: [
        Expanded(child: _act(Icons.payments_rounded, tr('تحصيل', 'Collect'), Coll.green, _payDialog)),
        const SizedBox(width: 8),
        Expanded(child: _act(Icons.phone_in_talk_rounded, tr('نشاط', 'Activity'), Coll.gold, _activityDialog)),
        const SizedBox(width: 8),
        Expanded(child: _act(Icons.flag_rounded, tr('الحالة', 'Status'), const Color(0xFF2563EB), _stateDialog)),
        if (canLegal) ...[const SizedBox(width: 8),
          Expanded(child: _act(Icons.gavel_rounded, tr('قانوني', 'Legal'), const Color(0xFF6D28D9), _legalDialog))],
      ])));
  }

  Widget _act(IconData ic, String t, Color c, VoidCallback onTap) => Material(
      color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(12),
      child: InkWell(borderRadius: BorderRadius.circular(12), onTap: onTap,
        child: Padding(padding: const EdgeInsets.symmetric(vertical: 10),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Icon(ic, color: c, size: 20), const SizedBox(height: 3),
            Text(t, style: TextStyle(color: c, fontWeight: FontWeight.w700, fontSize: 11.5)),
          ]))));

  // ===== تحصيل دفعة =====
  Future<void> _payDialog() async {
    final amount = TextEditingController();
    final recipient = TextEditingController();
    final chequeNo = TextEditingController();
    final chequeBank = TextEditingController();
    final note = TextEditingController();
    String method = 'cash';
    DateTime payDate = DateTime.now();
    final res = await showModalBottomSheet<bool>(context: context, isScrollControlled: true,
      backgroundColor: Colors.white, shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (ctx) => StatefulBuilder(builder: (ctx, setM) => Directionality(
        textDirection: gLang == 'en' ? TextDirection.ltr : TextDirection.rtl,
        child: Padding(padding: EdgeInsets.fromLTRB(18, 16, 18, MediaQuery.of(ctx).viewInsets.bottom + 18),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            _sheetHandle(), _sheetTitle(tr('تسجيل تحصيل', 'Record payment')),
            const SizedBox(height: 10),
            Wrap(spacing: 8, children: [
              ['cash', tr('نقد', 'Cash')], ['cheque', tr('شيك', 'Cheque')], ['transfer', tr('تحويل', 'Transfer')],
            ].map((m) => ChoiceChip(label: Text(m[1]), selected: method == m[0],
                selectedColor: Coll.green,
                labelStyle: TextStyle(color: method == m[0] ? Colors.white : Coll.ink),
                onSelected: (_) => setM(() => method = m[0]))).toList()),
            const SizedBox(height: 10),
            // تاريخ التحصيل الفعلي (يمكن اختيار تاريخ قديم)
            InkWell(onTap: () async {
                final d = await showDatePicker(context: ctx, initialDate: payDate,
                    firstDate: DateTime(2020), lastDate: DateTime.now());
                if (d != null) setM(() => payDate = d);
              },
              borderRadius: BorderRadius.circular(10),
              child: Container(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
                decoration: BoxDecoration(borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: Colors.black26)),
                child: Row(children: [
                  const Icon(Icons.event_rounded, size: 18, color: Coll.green),
                  const SizedBox(width: 8),
                  Text('${tr('تاريخ التحصيل', 'Collection date')}: ${payDate.toIso8601String().substring(0, 10)}',
                      style: const TextStyle(fontWeight: FontWeight.w700, color: Coll.ink)),
                  const Spacer(),
                  const Icon(Icons.edit_calendar_rounded, size: 18, color: Coll.slate),
                ]))),
            const SizedBox(height: 10),
            _field(amount, tr('المبلغ المحصّل', 'Amount'), number: true),
            if (method == 'cheque') ...[
              const SizedBox(height: 10), _field(chequeNo, tr('رقم الشيك', 'Cheque no')),
              const SizedBox(height: 10), _field(chequeBank, tr('البنك', 'Bank')),
            ],
            const SizedBox(height: 10), _field(recipient, tr('اسم المستلِم', 'Recipient')),
            const SizedBox(height: 10), _field(note, tr('ملاحظات', 'Note'), lines: 2),
            const SizedBox(height: 16),
            SizedBox(width: double.infinity, child: FilledButton(
              style: FilledButton.styleFrom(backgroundColor: Coll.green,
                  padding: const EdgeInsets.symmetric(vertical: 14)),
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(tr('حفظ التحصيل', 'Save'), style: const TextStyle(fontWeight: FontWeight.w800)))),
          ])))));
    if (res != true) return;
    final amt = double.tryParse(amount.text.trim()) ?? 0;
    if (amt <= 0) { _snack(tr('أدخل مبلغاً صحيحاً', 'Enter a valid amount')); return; }
    try {
      await _ap.api.collectionsPay(widget.id, {
        'method': method, 'amount': amt,
        'date': payDate.toIso8601String().substring(0, 10),
        'recipient': recipient.text.trim(), 'note': note.text.trim(),
        if (method == 'cheque') 'cheque_no': chequeNo.text.trim(),
        if (method == 'cheque') 'cheque_bank': chequeBank.text.trim(),
      });
      _snack(tr('سُجّل التحصيل', 'Payment recorded'));
      _load();
    } catch (e) { _snack('$e'); }
  }

  // ===== نشاط =====
  Future<void> _activityDialog() async {
    final comment = TextEditingController();
    String kind = 'call';
    String? outcome;
    final res = await showModalBottomSheet<bool>(context: context, isScrollControlled: true,
      backgroundColor: Colors.white, shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (ctx) => StatefulBuilder(builder: (ctx, setM) => Directionality(
        textDirection: gLang == 'en' ? TextDirection.ltr : TextDirection.rtl,
        child: Padding(padding: EdgeInsets.fromLTRB(18, 16, 18, MediaQuery.of(ctx).viewInsets.bottom + 18),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            _sheetHandle(), _sheetTitle(tr('تسجيل اتصال/زيارة', 'Log call/visit')),
            const SizedBox(height: 10),
            Wrap(spacing: 8, children: [
              ['call', tr('📞 اتصال', '📞 Call')], ['visit', tr('🏢 زيارة', '🏢 Visit')], ['note', tr('💬 ملاحظة', '💬 Note')],
            ].map((m) => ChoiceChip(label: Text(m[1]), selected: kind == m[0],
                selectedColor: Coll.gold,
                labelStyle: TextStyle(color: kind == m[0] ? Colors.white : Coll.ink),
                onSelected: (_) => setM(() => kind = m[0]))).toList()),
            const SizedBox(height: 12),
            Text(tr('النتيجة', 'Outcome'), style: const TextStyle(fontWeight: FontWeight.w700, color: Coll.slate)),
            const SizedBox(height: 6),
            Wrap(spacing: 8, runSpacing: 6, children: [
              ['promised', tr('وعد بالدفع', 'Promised')], ['partial', tr('دفع جزئي', 'Partial')],
              ['no_response', tr('لا يتجاوب', 'No reply')], ['refused', tr('رفض الدفع', 'Refused')],
              ['reschedule', tr('إعادة جدولة', 'Reschedule')],
            ].map((m) => ChoiceChip(label: Text(m[1]), selected: outcome == m[0],
                selectedColor: Coll.green,
                labelStyle: TextStyle(color: outcome == m[0] ? Colors.white : Coll.ink, fontSize: 12),
                onSelected: (_) => setM(() => outcome = outcome == m[0] ? null : m[0]))).toList()),
            const SizedBox(height: 12),
            _field(comment, tr('التعليق', 'Comment'), lines: 3),
            const SizedBox(height: 16),
            SizedBox(width: double.infinity, child: FilledButton(
              style: FilledButton.styleFrom(backgroundColor: Coll.gold,
                  padding: const EdgeInsets.symmetric(vertical: 14)),
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(tr('حفظ النشاط', 'Save'), style: const TextStyle(fontWeight: FontWeight.w800)))),
          ])))));
    if (res != true) return;
    if (comment.text.trim().isEmpty) { _snack(tr('اكتب تعليقاً', 'Write a comment')); return; }
    try {
      await _ap.api.collectionsActivity(widget.id, {
        'kind': kind, 'comment': comment.text.trim(),
        if (outcome != null) 'outcome': outcome,
      });
      _snack(tr('حُفظ النشاط', 'Activity saved'));
      _load();
    } catch (e) { _snack('$e'); }
  }

  // ===== الحالة + المتوقّع + ملاحظة =====
  Future<void> _stateDialog() async {
    final d = _d!;
    String? state = '${d['state_code'] ?? ''}'.isEmpty ? null : '${d['state_code']}';
    if (state == 'legal') state = null;
    String? fc = '${d['forecast_code'] ?? ''}'.isEmpty ? null : '${d['forecast_code']}';
    final note = TextEditingController(text: '${d['note'] ?? ''}');
    final res = await showModalBottomSheet<bool>(context: context, isScrollControlled: true,
      backgroundColor: Colors.white, shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (ctx) => StatefulBuilder(builder: (ctx, setM) => Directionality(
        textDirection: gLang == 'en' ? TextDirection.ltr : TextDirection.rtl,
        child: Padding(padding: EdgeInsets.fromLTRB(18, 16, 18, MediaQuery.of(ctx).viewInsets.bottom + 18),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            _sheetHandle(), _sheetTitle(tr('تحديث الحالة والمتوقّع', 'Status & forecast')),
            const SizedBox(height: 12),
            Text(tr('الحالة', 'Status'), style: const TextStyle(fontWeight: FontWeight.w700, color: Coll.slate)),
            const SizedBox(height: 6),
            Wrap(spacing: 8, runSpacing: 6, children: [
              ['ok', tr('ملتزم', 'OK')], ['late', tr('متأخّر', 'Late')],
              ['no_response', tr('لا يتجاوب', 'No reply')], ['refuses', tr('يرفض', 'Refuses')],
            ].map((m) => ChoiceChip(label: Text(m[1]), selected: state == m[0],
                selectedColor: Coll.state(m[0]),
                labelStyle: TextStyle(color: state == m[0] ? Colors.white : Coll.ink, fontSize: 12),
                onSelected: (_) => setM(() => state = state == m[0] ? null : m[0]))).toList()),
            const SizedBox(height: 14),
            Text(tr('المتوقّع تحصيله', 'Forecast'), style: const TextStyle(fontWeight: FontWeight.w700, color: Coll.slate)),
            const SizedBox(height: 6),
            Wrap(spacing: 8, runSpacing: 6, children: [
              ['week', tr('خلال أسبوع', 'A week')], ['current_month', tr('الشهر الحالي', 'This month')],
              ['month', tr('خلال شهر', 'A month')],
            ].map((m) => ChoiceChip(label: Text(m[1]), selected: fc == m[0],
                selectedColor: Coll.green,
                labelStyle: TextStyle(color: fc == m[0] ? Colors.white : Coll.ink, fontSize: 12),
                onSelected: (_) => setM(() => fc = fc == m[0] ? null : m[0]))).toList()),
            const SizedBox(height: 12),
            _field(note, tr('ملاحظة التحصيل', 'Collection note'), lines: 2),
            const SizedBox(height: 16),
            SizedBox(width: double.infinity, child: FilledButton(
              style: FilledButton.styleFrom(backgroundColor: const Color(0xFF2563EB),
                  padding: const EdgeInsets.symmetric(vertical: 14)),
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(tr('حفظ', 'Save'), style: const TextStyle(fontWeight: FontWeight.w800)))),
          ])))));
    if (res != true) return;
    try {
      await _ap.api.collectionsState(widget.id, {
        'state': state ?? false, 'forecast': fc ?? false, 'note': note.text.trim(),
      });
      _snack(tr('حُفظت الحالة', 'Saved'));
      _load();
    } catch (e) { _snack('$e'); }
  }

  // ===== التحويل القانوني (مدير) =====
  Future<void> _legalDialog() async {
    final reason = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (_) => Directionality(
      textDirection: gLang == 'en' ? TextDirection.ltr : TextDirection.rtl,
      child: AlertDialog(
        title: Text(tr('تحويل للإدارة القانونية', 'Transfer to legal')),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          Text(tr('سيُعلَّم العميل كمتعثّر وتُحوَّل الفاتورة قانونياً.',
              'The invoice will be marked legal.')),
          const SizedBox(height: 12),
          TextField(controller: reason, decoration: InputDecoration(
              hintText: tr('سبب التحويل', 'Reason'), border: const OutlineInputBorder())),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: Text(tr('إلغاء', 'Cancel'))),
          FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFF6D28D9)),
              onPressed: () => Navigator.pop(context, true), child: Text(tr('تحويل', 'Transfer'))),
        ])));
    if (ok != true) return;
    try {
      await _ap.api.collectionsLegal(widget.id, reason.text.trim());
      _snack(tr('حُوّلت قانونياً', 'Transferred'));
      _load();
    } catch (e) { _snack('$e'); }
  }

  // ---- helpers ----
  Widget _sheetHandle() => Center(child: Container(width: 40, height: 4,
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(color: Colors.black12, borderRadius: BorderRadius.circular(4))));
  Widget _sheetTitle(String t) => Text(t,
      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: Coll.ink));
  Widget _field(TextEditingController c, String hint, {bool number = false, int lines = 1}) =>
      TextField(controller: c, maxLines: lines,
        keyboardType: number ? const TextInputType.numberWithOptions(decimal: true) : TextInputType.text,
        inputFormatters: number ? [FilteringTextInputFormatter.allow(RegExp(r'[0-9.]'))] : null,
        decoration: InputDecoration(labelText: hint, isDense: true,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(10))));
  void _snack(String m) {
    if (mounted) { ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m))); }
  }
}

/// ====== كشف حساب العميل ======
class CustomerStatement extends StatefulWidget {
  const CustomerStatement({super.key, required this.partnerId});
  final int partnerId;
  @override
  State<CustomerStatement> createState() => _CustomerStatementState();
}

class _CustomerStatementState extends State<CustomerStatement> {
  Map<String, dynamic>? _d;
  bool _loading = true;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.collectionsStatement(widget.partnerId);
      if (mounted) setState(() { _d = d; _loading = false; });
    } catch (e) { if (mounted) setState(() => _loading = false); }
  }

  void _share() {
    final d = _d; if (d == null) return;
    final sym = '${d['currency'] ?? ''}';
    final b = StringBuffer();
    b.writeln('${tr('كشف حساب', 'Statement')}: ${d['partner']}');
    b.writeln('${tr('عدد الفواتير', 'Invoices')}: ${d['invoice_count']}');
    b.writeln('${tr('الإجمالي', 'Total')}: ${money(numOf(d['total']), sym)}');
    b.writeln('${tr('المحصّل', 'Collected')}: ${money(numOf(d['collected']), sym)}');
    b.writeln('${tr('المتبقّي', 'Residual')}: ${money(numOf(d['residual']), sym)}');
    Share.share(b.toString());
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: gLang == 'en' ? TextDirection.ltr : TextDirection.rtl,
      child: Scaffold(
        backgroundColor: Coll.bg,
        appBar: AppBar(backgroundColor: Coll.green, foregroundColor: Colors.white,
            title: Text(tr('كشف الحساب', 'Statement')), elevation: 0,
            actions: [IconButton(onPressed: _share, icon: const Icon(Icons.share_rounded))]),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _d == null ? Center(child: Text(tr('تعذّر التحميل', 'Load failed'))) : _body(),
      ),
    );
  }

  Widget _body() {
    final d = _d!;
    final sym = '${d['currency'] ?? ''}';
    final invs = (d['invoices'] as List?) ?? [];
    return ListView(padding: const EdgeInsets.fromLTRB(14, 14, 14, 24), children: [
      Container(padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(borderRadius: BorderRadius.circular(16),
          gradient: const LinearGradient(colors: [Coll.greenD, Coll.green])),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${d['partner'] ?? ''}',
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
          if ('${d['phone'] ?? ''}'.isNotEmpty)
            Text('${d['phone']}', style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12.5)),
          const SizedBox(height: 14),
          Row(children: [
            _sv(tr('المتبقّي', 'Residual'), money(numOf(d['residual']), sym), true),
            const SizedBox(width: 18),
            _sv(tr('الإجمالي', 'Total'), money(numOf(d['total']), sym), false),
            const SizedBox(width: 18),
            _sv(tr('محصّل', 'Collected'), money(numOf(d['collected']), sym), false),
          ]),
        ])),
      const SizedBox(height: 14),
      Text('${tr('الفواتير', 'Invoices')} (${d['invoice_count']})',
          style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: Coll.ink)),
      const SizedBox(height: 8),
      ...invs.map((e) {
        final r = e as Map; final c = Coll.state('${r['state_code'] ?? ''}');
        return Card(margin: const EdgeInsets.only(bottom: 8), elevation: 0,
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12),
              side: BorderSide(color: Colors.black.withValues(alpha: 0.06))),
          child: ListTile(
            onTap: () => Navigator.push(context, MaterialPageRoute(
                builder: (_) => CollectionsDetail(id: r['id'] as int))),
            title: Text('${r['name'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
            subtitle: Text('${r['invoice_date'] ?? ''} · ${tr('استحقاق', 'due')} ${r['date_due'] ?? ''}',
                style: const TextStyle(fontSize: 11.5)),
            trailing: Column(mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.end, children: [
                Text(money(numOf(r['amount_residual']), sym),
                    style: const TextStyle(fontWeight: FontWeight.w900, color: Coll.green, fontSize: 13)),
                if ('${r['state'] ?? ''}'.isNotEmpty)
                  Text('${r['state']}', style: TextStyle(color: c, fontSize: 10.5, fontWeight: FontWeight.w700)),
              ])));
      }),
    ]);
  }

  Widget _sv(String l, String v, bool big) => Column(
      crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(l, style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 11)),
        Text(v, style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: big ? 17 : 13)),
      ]);
}
