import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/app_version.dart';
import 'pdf_report_screen.dart';
import 'waste_trip_map.dart';

/// Client waste transfer & treatment: collection orders + trips, with a
/// new-order form. Scoped to the client's waste projects.
class ClientWasteScreen extends StatefulWidget {
  const ClientWasteScreen({super.key, this.initialKind = 'orders', this.embedded = false});
  final String initialKind;
  final bool embedded; // shown as a nav tab (hide its own AppBar back)
  @override
  State<ClientWasteScreen> createState() => _ClientWasteScreenState();
}

class _ClientWasteScreenState extends State<ClientWasteScreen> {
  Map<String, dynamic>? _summary;
  late String _kind = widget.initialKind;
  Future<List<dynamic>>? _list;
  String _q = '';
  String? _stateFilter;

  // clean number formatting (removes float artifacts like 6.548000000000001)
  static String _n(dynamic v) {
    if (v is num) return v == v.roundToDouble() ? v.toInt().toString() : v.toStringAsFixed(1);
    return '$v';
  }

  static const _kinds = [
    ['orders', '♻️ الأوامر', 'Orders'],
    ['trips', '🚛 الرحلات', 'Trips'],
    ['centers', '🏭 المراكز', 'Centers'],
  ];
  static const _stL = {
    'draft': 'مسودة', 'scheduled': 'مجدول', 'pickuped': 'تم الالتقاط', 'arrived': 'وصل',
    'processing': 'قيد المعالجة', 'delivered': 'تم التسليم', 'completed': 'مكتمل', 'cancelled': 'ملغى',
  };
  static const _stC = {
    'draft': Color(0xFF94A3B8), 'scheduled': Color(0xFF3B82F6), 'pickuped': Color(0xFF0891B2),
    'arrived': Color(0xFF6366F1), 'processing': Color(0xFFF59E0B), 'delivered': Color(0xFF16A34A),
    'completed': Color(0xFF16A34A), 'cancelled': Color(0xFFE11D48),
  };

  @override
  void initState() {
    super.initState();
    _loadSummary();
    _load();
  }

  Future<void> _loadSummary() async {
    try {
      final s = await context.read<AuthProvider>().api.clientWasteSummary();
      if (mounted) setState(() => _summary = s);
    } catch (_) {}
  }

  void _load() => setState(() => _list = context.read<AuthProvider>().api.clientWaste(_kind, q: _q, state: _stateFilter));

  @override
  Widget build(BuildContext context) {
    final s = _summary;
    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: !widget.embedded,
        title: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
          Text(widget.embedded
              ? (_kind == 'trips' ? tr('الرحلات', 'Trips') : _kind == 'centers' ? tr('المراكز', 'Centers') : tr('طلبات النقل', 'Collection orders'))
              : tr('نقل ومعالجة النفايات', 'Waste')),
          Text('v${AppVersion.value} · ${tr('نقل النفايات', 'Waste')}',
              style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w500, color: Color(0xFF9AE6B4))),
        ]),
        actions: [
          IconButton(
            tooltip: tr('التقارير والإحصائيات', 'Reports & statistics'),
            icon: const Icon(Icons.insights_rounded),
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const WasteStatsScreen())),
          ),
          IconButton(
            tooltip: tr('لوحة التحكم الكاملة', 'Full dashboard'),
            icon: const Icon(Icons.dashboard_rounded),
            onPressed: _openPortal,
          ),
        ],
      ),
      body: Column(children: [
        _portalBanner(),
        if (s != null && s['available'] == true)
          SizedBox(
            height: 96,
            child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.all(8), children: [
              _stat('♻️', '${s['orders'] ?? 0}', tr('الأوامر', 'Orders'), const Color(0xFF16A34A)),
              _stat('⏳', '${s['open'] ?? 0}', tr('قيد التنفيذ', 'In progress'), const Color(0xFFF59E0B)),
              _stat('✅', '${s['completed'] ?? 0}', tr('مكتملة', 'Completed'), const Color(0xFF0891B2)),
              _stat('🚛', '${s['trips'] ?? 0}', tr('الرحلات', 'Trips'), const Color(0xFF6366F1)),
              _stat('🏭', '${s['centers'] ?? 0}', tr('المراكز', 'Centers'), const Color(0xFF334155)),
            ]),
          ),
        // chip selector — hidden when embedded as a focused nav tab
        if (!widget.embedded)
          SizedBox(
            height: 46,
            child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 8), children: [
              for (final k in _kinds)
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
                  child: ChoiceChip(
                    label: Text(gLang == 'en' ? k[2] : k[1]),
                    selected: _kind == k[0],
                    onSelected: (_) { setState(() => _kind = k[0]); _load(); },
                  ),
                ),
            ]),
          ),
        // top actions: new-order button + search/filter icon
        if (_kind != 'centers') _actionBar(),
        Expanded(
          child: FutureBuilder<List<dynamic>>(
            future: _list,
            builder: (_, snap) {
              if (!snap.hasData) return const Center(child: CircularProgressIndicator());
              final rows = snap.data!;
              if (rows.isEmpty) return Center(child: Text(tr('لا سجلات', 'No records')));
              return ListView.separated(
                padding: const EdgeInsets.all(8),
                itemCount: rows.length,
                separatorBuilder: (_, __) => _kind == 'orders' ? const SizedBox.shrink() : const Divider(height: 1),
                itemBuilder: (_, i) => _row(rows[i] as Map),
              );
            },
          ),
        ),
      ]),
    );
  }


  // native stats screen — this used to open the web portal in a WebView
  void _openPortal() => Navigator.push(context, MaterialPageRoute(
        builder: (_) => const WasteStatsScreen(),
      ));

  /// Prominent entry to the exact web portal dashboard (same data, reports,
  /// printing and colours as https://ecare.care-kw.com/service_orders).
  Widget _portalBanner() => Padding(
        padding: const EdgeInsets.fromLTRB(10, 10, 10, 2),
        child: InkWell(
          onTap: _openPortal,
          borderRadius: BorderRadius.circular(16),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [Color(0xFF115E4B), Color(0xFF16A34A)], begin: Alignment.topRight, end: Alignment.bottomLeft),
              borderRadius: BorderRadius.circular(16),
              boxShadow: [BoxShadow(color: const Color(0xFF16A34A).withValues(alpha: 0.3), blurRadius: 12, offset: const Offset(0, 5))],
            ),
            child: Row(children: [
              Container(padding: const EdgeInsets.all(9), decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(12)), child: const Icon(Icons.insert_chart_rounded, color: Colors.white, size: 24)),
              const SizedBox(width: 12),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(tr('لوحة التحكم الكاملة', 'Full control dashboard'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14.5)),
                const SizedBox(height: 2),
                Text(tr('كل الطلبات والرحلات والتقارير والطباعة', 'All orders, trips, reports & printing'), style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 11.5)),
              ])),
              const Icon(Icons.arrow_forward_ios_rounded, color: Colors.white, size: 15),
            ]),
          ),
        ),
      );

  static const _states = [
    ['', 'الكل', 'All'], ['scheduled', 'مجدول', 'Scheduled'], ['pickuped', 'تم الالتقاط', 'Picked'],
    ['arrived', 'وصل', 'Arrived'], ['processing', 'معالجة', 'Processing'], ['delivered', 'تسليم', 'Delivered'], ['completed', 'مكتمل', 'Done'], ['cancelled', 'ملغى', 'Cancelled'],
  ];

  bool get _filterActive => _q.isNotEmpty || (_stateFilter != null && _stateFilter!.isNotEmpty);

  Widget _actionBar() => Padding(
        padding: const EdgeInsets.fromLTRB(10, 8, 10, 4),
        child: Row(children: [
          if (_kind == 'orders')
            Expanded(child: SizedBox(height: 48, child: DecoratedBox(
              decoration: BoxDecoration(
                gradient: const LinearGradient(colors: [Color(0xFF115E4B), Color(0xFF16A34A)], begin: Alignment.topRight, end: Alignment.bottomLeft),
                borderRadius: BorderRadius.circular(14),
                boxShadow: [BoxShadow(color: const Color(0xFF16A34A).withValues(alpha: 0.35), blurRadius: 10, offset: const Offset(0, 4))],
              ),
              child: Material(color: Colors.transparent, child: InkWell(
                borderRadius: BorderRadius.circular(14), onTap: _newOrder,
                child: Center(child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Icon(Icons.add_circle_outline_rounded, color: Colors.white), SizedBox(width: 8),
                  Text(tr('طلب نقل جديد', 'New transfer request'), style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15)),
                ])),
              )),
            ))),
          if (_kind == 'orders') const SizedBox(width: 10),
          // search / filter icon button (badge when active)
          Stack(clipBehavior: Clip.none, children: [
            Container(
              width: 48, height: 48,
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: const Color(0xFFE2E8F0)), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 5, offset: Offset(0, 2))]),
              child: Material(color: Colors.transparent, child: InkWell(
                borderRadius: BorderRadius.circular(14), onTap: _openSearchDialog,
                child: const Icon(Icons.tune_rounded, color: Color(0xFF0E3A5F)),
              )),
            ),
            if (_filterActive) Positioned(top: -3, right: -3, child: Container(width: 14, height: 14, decoration: BoxDecoration(color: const Color(0xFFC0392B), shape: BoxShape.circle, border: Border.all(color: Colors.white, width: 2)))),
          ]),
        ]),
      );

  void _openSearchDialog() {
    final qCtrl = TextEditingController(text: _q);
    String? tmpState = _stateFilter;
    showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSt) => Padding(
        padding: EdgeInsets.fromLTRB(18, 16, 18, MediaQuery.of(ctx).viewInsets.bottom + 18),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.tune_rounded, color: Color(0xFF0E3A5F)), const SizedBox(width: 8),
            Text(tr('بحث وفلترة', 'Search & filter'), style: TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: Color(0xFF0E3A5F))),
            const Spacer(),
            TextButton(onPressed: () { qCtrl.clear(); setSt(() => tmpState = null); }, child: Text(tr('مسح', 'Clear'))),
          ]),
          const SizedBox(height: 12),
          TextField(controller: qCtrl, autofocus: true, decoration: InputDecoration(
            hintText: tr('بحث بالرقم أو الموقع…', 'Search by serial or location…'),
            prefixIcon: const Icon(Icons.search), filled: true, fillColor: const Color(0xFFF1F5F9),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none))),
          const SizedBox(height: 14),
          Text(tr('الحالة', 'Status'), style: TextStyle(fontWeight: FontWeight.w800, color: Color(0xFF64748B))),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final st in _states) ChoiceChip(
              label: Text(gLang == 'en' ? st[2] : st[1], style: const TextStyle(fontSize: 12.5)),
              selected: (tmpState ?? '') == st[0],
              selectedColor: const Color(0xFF16A34A),
              labelStyle: TextStyle(color: (tmpState ?? '') == st[0] ? Colors.white : const Color(0xFF0E3A5F), fontWeight: FontWeight.w700),
              onSelected: (_) => setSt(() => tmpState = st[0].isEmpty ? null : st[0]),
            ),
          ]),
          const SizedBox(height: 18),
          SizedBox(width: double.infinity, height: 50, child: ElevatedButton.icon(
            onPressed: () { setState(() { _q = qCtrl.text; _stateFilter = tmpState; }); _load(); Navigator.pop(ctx); },
            icon: const Icon(Icons.check_rounded),
            label: Text(tr('تطبيق', 'Apply'), style: TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0E3A5F), foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))))),
        ]),
      )),
    );
  }

  Widget _stat(String ic, String v, String l, Color c) => Container(
        width: 128,
        margin: const EdgeInsets.symmetric(horizontal: 4),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(14)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
          Text('$ic $v', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: c)),
          Text(l, style: const TextStyle(fontSize: 11, color: Colors.grey), maxLines: 1, overflow: TextOverflow.ellipsis),
        ]),
      );

  Widget _pill(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(20)),
        child: Text(t, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: c)),
      );

  Widget _row(Map r) {
    if (_kind == 'centers') {
      return ListTile(leading: const Text('🏭', style: TextStyle(fontSize: 22)), title: Text('${r['name']}', style: const TextStyle(fontWeight: FontWeight.w700)));
    }
    final st = '${r['state']}';
    final c = _stC[st] ?? Colors.blueGrey;
    if (_kind == 'trips') {
      return ListTile(
        leading: const Text('🚛', style: TextStyle(fontSize: 22)),
        title: Text('${r['sequence']}', style: const TextStyle(fontWeight: FontWeight.w700)),
        subtitle: Text('${r['pickup'] ?? ''} → ${r['center'] ?? ''} · ${_n(r['total_weight'] ?? 0)} كجم', maxLines: 2, overflow: TextOverflow.ellipsis),
        trailing: _pill(tr(_stL[st] ?? st, st), c),
        onTap: () => _openTrip(r),
      );
    }
    // ORDER row — professional summary (date, pickup, qty/weight, trip) instead of raw item list
    final cnt = r['items_count'] ?? 0;
    final qty = r['qty_total'] ?? 0;
    final wt = (r['weight_total'] ?? 0) is num ? (r['weight_total'] ?? 0) : 0;
    final date = _shortDate('${r['order_date'] ?? r['request_date'] ?? ''}');
    final meta = <String>[
      if (r['pickup'] != null) '📍 ${r['pickup']}',
      if (cnt != 0) '📦 $cnt ${tr('صنف', 'items')}',
      if ((wt as num) != 0) '⚖️ $wt كجم' else if (qty != 0) '×$qty',
      if (r['trip'] != null) '🚛 ${r['trip']}',
    ].join('  ·  ');
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 4, offset: Offset(0, 2))]),
      child: ListTile(
        onTap: () => _openOrder(r),
        leading: Container(width: 44, height: 44, decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(12)), alignment: Alignment.center, child: const Text('♻️', style: TextStyle(fontSize: 20))),
        title: Row(children: [
          Expanded(child: Text('${r['serial']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14.5))),
          if (date.isNotEmpty) Text(date, style: const TextStyle(fontSize: 11.5, color: Colors.grey, fontWeight: FontWeight.w600)),
        ]),
        subtitle: Padding(padding: const EdgeInsets.only(top: 3), child: Text(meta.isEmpty ? (r['project'] ?? '') : meta, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11.5, color: Color(0xFF64748B)))),
        trailing: _pill(tr(_stL[st] ?? st, st), c),
      ),
    );
  }

  String _shortDate(String dt) => dt.length >= 10 ? dt.substring(0, 10) : dt;

  static const _flow = ['draft', 'scheduled', 'pickuped', 'arrived', 'processing', 'delivered', 'completed'];

  Future<void> _openReport(String? path, String title) async {
    if (path == null) return;
    // Rendered inside the app (with share/print) — no browser hand-off.
    Navigator.push(context, MaterialPageRoute(
        builder: (_) => PdfReportScreen(path: path, title: title, fileName: '${title.replaceAll(' ', '-')}.pdf')));
  }

  void _zoom(String url) => showDialog(context: context, builder: (_) => Dialog(
        backgroundColor: Colors.black, insetPadding: const EdgeInsets.all(12),
        child: Stack(children: [
          InteractiveViewer(child: Image.network(url, errorBuilder: (_, __, ___) => const SizedBox(height: 200))),
          Positioned(top: 4, right: 4, child: IconButton(icon: const Icon(Icons.close, color: Colors.white), onPressed: () => Navigator.pop(context))),
        ]),
      ));

  void _openOrder(Map r) {
    final st = '${r['state']}';
    final cur = _flow.indexOf(st);
    final cancelled = st == 'cancelled';
    final items = (r['items'] as List?) ?? [];
    final c = _stC[st] ?? Colors.blueGrey;
    showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.9, maxChildSize: 0.96, minChildSize: 0.5,
        builder: (_, ctrl) => Container(
          decoration: const BoxDecoration(color: Color(0xFFF4F7FB), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
          clipBehavior: Clip.antiAlias,
          child: Column(children: [
            // gradient hero
            Container(
              padding: const EdgeInsets.fromLTRB(18, 12, 18, 16),
              decoration: const BoxDecoration(gradient: LinearGradient(colors: [Color(0xFF115E4B), Color(0xFF16A34A)], begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Column(children: [
                Container(width: 40, height: 4, decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3))),
                const SizedBox(height: 12),
                Row(children: [
                  const Text('♻️', style: TextStyle(fontSize: 26)),
                  const SizedBox(width: 10),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${r['serial']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 19)),
                    if (r['project'] != null) Text('${r['project']}', style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 12.5)),
                  ])),
                  Container(padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)), child: Text(tr(_stL[st] ?? st, st), style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 12))),
                  const SizedBox(width: 8),
                  if (r['report_path'] != null)
                    InkWell(
                      onTap: () => _openReport(r['report_path'] as String?, '${r['serial']}'),
                      borderRadius: BorderRadius.circular(12),
                      child: Container(
                        padding: const EdgeInsets.all(9),
                        decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.22), borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.white.withValues(alpha: 0.35))),
                        child: const Icon(Icons.print_rounded, color: Colors.white, size: 22),
                      ),
                    ),
                ]),
              ]),
            ),
            Expanded(child: ListView(controller: ctrl, padding: const EdgeInsets.all(16), children: [
              _card(tr('حالة الطلب', 'Order status'), [
                if (cancelled)
                  Text(tr('✖ تم إلغاء الطلب', '✖ Order cancelled'), style: TextStyle(color: Color(0xFFE11D48), fontWeight: FontWeight.w700))
                else
                  Column(children: [for (int i = 0; i < _flow.length; i++) _step(i, cur)]),
              ]),
              _card(tr('فريق العملية', 'Operation team'), [
                _kv(Icons.manage_accounts, tr('مدير العمليات', 'Ops manager'), r['ops_manager']),
                _kv(Icons.local_shipping_outlined, tr('السائق', 'Driver'), r['driver']),
                _kv(Icons.how_to_reg_outlined, tr('مستلم الكميات', 'Receiver'), r['receiver']),
                if ((r['final_weight'] ?? 0) != 0) _kv(Icons.scale_outlined, tr('الوزن النهائي', 'Final weight'), '${_n(r['final_weight'])} كجم'),
                if (r['final_note'] != null) _kv(Icons.sticky_note_2_outlined, tr('ملاحظة الاستلام', 'Receipt note'), r['final_note']),
              ]),
              _card(tr('التفاصيل', 'Details'), [
                _kv(Icons.place_outlined, tr('موقع الالتقاط', 'Pickup'), r['pickup']),
                _kv(Icons.route_outlined, tr('الرحلة', 'Trip'), r['trip']),
                _kv(Icons.schedule_rounded, tr('🕒 موعد الرفع المطلوب', '🕒 Requested pickup'),
                    r['order_date'] ?? r['request_date']),
                _kv(Icons.category_outlined, tr('النوع', 'Type'), r['type']),
              ]),
              if (items.isNotEmpty) _card(tr('الأصناف', 'Items'), [for (final i in items) _itemRow(i as Map)]),
              if (r['proof'] != null) _card(tr('صورة الإثبات', 'Proof photo'), [
                GestureDetector(onTap: () => _zoom('${r['proof']}'), child: ClipRRect(borderRadius: BorderRadius.circular(12), child: Image.network('${r['proof']}', width: double.infinity, fit: BoxFit.cover, errorBuilder: (_, __, ___) => const SizedBox()))),
              ]),
              if ((r['media'] as List?)?.isNotEmpty ?? false) _card(tr('صور وفيديوهات', 'Photos & videos'), [_mediaGallery(r['media'] as List)]),
              if (r['notes'] != null) _card(tr('ملاحظات', 'Notes'), [Text('${r['notes']}', style: const TextStyle(fontSize: 13, height: 1.4))]),
              const SizedBox(height: 80),
            ])),
            SafeArea(top: false, child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 6, 16, 10),
              child: SizedBox(height: 50, child: ElevatedButton.icon(
                onPressed: () => _openReport(r['report_path'] as String?, '${r['serial']}'),
                icon: const Icon(Icons.picture_as_pdf_rounded),
                label: Text(tr('عرض / طباعة التقرير', 'View / print report'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0E3A5F), foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
              )),
            )),
          ]),
        ),
      ),
    );
  }

  void _openTrip(Map r) {
    final items = (r['items'] as List?) ?? [];
    showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.82, maxChildSize: 0.95, minChildSize: 0.4,
        builder: (_, ctrl) => Container(
          decoration: const BoxDecoration(color: Color(0xFFF4F7FB), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
          clipBehavior: Clip.antiAlias,
          child: ListView(controller: ctrl, children: [
            Container(
              padding: const EdgeInsets.fromLTRB(18, 12, 18, 16),
              decoration: const BoxDecoration(gradient: LinearGradient(colors: [Color(0xFF334155), Color(0xFF0E3A5F)], begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Column(children: [
                Container(width: 40, height: 4, decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3))),
                const SizedBox(height: 12),
                Row(children: [
                  const Text('🚛', style: TextStyle(fontSize: 26)), const SizedBox(width: 10),
                  Expanded(child: Text('${r['sequence']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 19))),
                  if (r['report_path'] != null)
                    InkWell(
                      onTap: () => _openReport(r['report_path'] as String?, '${r['sequence']}'),
                      borderRadius: BorderRadius.circular(12),
                      child: Container(
                        padding: const EdgeInsets.all(9),
                        decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.white.withValues(alpha: 0.35))),
                        child: const Icon(Icons.print_rounded, color: Colors.white, size: 22),
                      ),
                    ),
                ]),
                const SizedBox(height: 14),
                Row(children: [
                  Expanded(child: _tstat('⚖️', _n(r['total_weight'] ?? 0), tr('الوزن الكلي', 'Weight'), const Color(0xFF38BDF8))),
                  const SizedBox(width: 8),
                  Expanded(child: _tstat('📦', _n(r['total_quantity'] ?? 0), tr('الكمية', 'Qty'), const Color(0xFFA5B4FC))),
                  const SizedBox(width: 8),
                  Expanded(child: _tstat('📋', '${r['order_count'] ?? 0}', tr('الأوامر', 'Orders'), const Color(0xFF6EE7B7))),
                ]),
              ]),
            ),
            Padding(padding: const EdgeInsets.all(16), child: Column(children: [
              // live driver tracking
              SizedBox(width: double.infinity, height: 48, child: ElevatedButton.icon(
                onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => WasteTripMapScreen(tripId: r['id'] as int, title: '${r['sequence']}'))),
                icon: const Icon(Icons.map_rounded),
                label: Text(tr('تتبّع السائق على الخريطة', 'Track driver on map'), style: const TextStyle(fontWeight: FontWeight.w800)),
                style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0E3A5F), foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
              )),
              const SizedBox(height: 12),
              _card(tr('المسار', 'Route'), [
                _kv(Icons.place_outlined, tr('الالتقاط', 'Pickup'), r['pickup']),
                _kv(Icons.factory_outlined, tr('مركز المعالجة', 'Center'), r['center']),
                _kv(Icons.local_shipping_outlined, tr('السائق', 'Driver'), r['driver']),
                _kv(Icons.groups_outlined, tr('الفريق', 'Team'), r['team']),
                _kv(Icons.event_outlined, tr('التاريخ', 'Date'), r['date']),
              ]),
              if (items.isNotEmpty) _card(tr('الأصناف المنقولة', 'Transported items'), [for (final i in items) _itemRow(i as Map, trip: true)]),
              if ((r['media'] as List?)?.isNotEmpty ?? false) _card(tr('صور وفيديوهات', 'Photos & videos'), [_mediaGallery(r['media'] as List)]),
              const SizedBox(height: 20),
            ])),
          ]),
        ),
      ),
    );
  }

  Widget _card(String title, List<Widget> children) => Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 2))]),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [Container(width: 4, height: 16, decoration: BoxDecoration(color: const Color(0xFF16A34A), borderRadius: BorderRadius.circular(3))), const SizedBox(width: 8), Text(title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: Color(0xFF0E3A5F)))]),
          const SizedBox(height: 10),
          ...children,
        ]),
      );

  Widget _itemRow(Map i, {bool trip = false}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: i['image'] != null
                ? Image.network('${i['image']}', width: 40, height: 40, fit: BoxFit.cover, errorBuilder: (_, __, ___) => _itemPh())
                : _itemPh(),
          ),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Text('${i['item'] ?? '—'}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5)),
            // unit weight, so "×186 · 390.6kg" can't be read as one piece = 390kg
            if ((i['unit_weight'] ?? 0) != 0)
              Text(tr('وزن القطعة ${_n(i['unit_weight'])} كجم', '${_n(i['unit_weight'])} kg/pc'),
                  style: const TextStyle(color: Colors.grey, fontSize: 10.5)),
          ])),
          Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4), decoration: BoxDecoration(color: const Color(0xFF16A34A).withValues(alpha: 0.1), borderRadius: BorderRadius.circular(8)),
              // `weight` is the LINE total (qty × piece) for orders and trips alike
              child: Text((i['weight'] ?? 0) != 0 ? '×${_n(i['qty'])} · ${_n(i['weight'])}kg' : '×${_n(i['qty'])}',
                  style: const TextStyle(color: Color(0xFF15803D), fontWeight: FontWeight.w800, fontSize: 12))),
        ]),
      );

  Widget _itemPh() => Container(width: 40, height: 40, color: const Color(0xFF16A34A).withValues(alpha: 0.1), alignment: Alignment.center, child: const Text('📦', style: TextStyle(fontSize: 18)));

  Widget _mediaGallery(List media) => SizedBox(
        height: 96,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          itemCount: media.length,
          separatorBuilder: (_, __) => const SizedBox(width: 8),
          itemBuilder: (_, i) {
            final m = media[i] as Map;
            final isVideo = m['is_video'] == true;
            return GestureDetector(
              onTap: () async {
                if (isVideo) {
                  // canLaunchUrl can report false even with a handler present,
                  // so attempt the launch and surface a real failure.
                  final u = Uri.parse('${m['url']}');
                  try {
                    if (await launchUrl(u, mode: LaunchMode.externalApplication)) return;
                  } catch (_) {}
                  if (mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text(tr('تعذّر فتح الفيديو', 'Could not open video'))));
                  }
                } else {
                  _zoom('${m['url']}');
                }
              },
              child: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Stack(alignment: Alignment.center, children: [
                  isVideo
                      ? Container(width: 128, height: 96, color: const Color(0xFF0E3A5F))
                      : Image.network('${m['url']}', width: 128, height: 96, fit: BoxFit.cover, errorBuilder: (_, __, ___) => Container(width: 128, height: 96, color: const Color(0xFFE2E8F0))),
                  if (isVideo) const Icon(Icons.play_circle_fill_rounded, color: Colors.white, size: 40),
                ]),
              ),
            );
          },
        ),
      );

  Widget _step(int i, int cur) {
    final done = cur >= i && cur >= 0;
    final s = _flow[i];
    final color = done ? const Color(0xFF16A34A) : Colors.grey.shade300;
    return IntrinsicHeight(child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Column(children: [
        Container(width: 28, height: 28, decoration: BoxDecoration(color: done ? color : Colors.white, shape: BoxShape.circle, border: Border.all(color: color, width: 2)), child: Icon(done ? Icons.check : Icons.circle_outlined, size: 15, color: done ? Colors.white : Colors.grey)),
        if (i < _flow.length - 1) Expanded(child: Container(width: 2, color: cur > i ? const Color(0xFF16A34A) : Colors.grey.shade300)),
      ]),
      const SizedBox(width: 12),
      Padding(padding: const EdgeInsets.only(top: 3, bottom: 14), child: Text(tr(_stL[s] ?? s, s), style: TextStyle(fontWeight: cur == i ? FontWeight.w900 : FontWeight.w600, color: done ? const Color(0xFF0E3A5F) : Colors.grey))),
    ]));
  }

  Widget _kv(IconData ic, String k, dynamic v) => (v == null || '$v'.isEmpty) ? const SizedBox.shrink() : Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(children: [Icon(ic, size: 17, color: Colors.grey), const SizedBox(width: 8), SizedBox(width: 110, child: Text(k, style: const TextStyle(color: Colors.grey, fontSize: 12.5))), Expanded(child: Text('$v', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)))]),
      );

  Widget _tstat(String ic, String v, String l, Color c) => Container(
        padding: const EdgeInsets.symmetric(vertical: 12), decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.13), borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.white.withValues(alpha: 0.18))),
        child: Column(children: [Text('$ic $v', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: c)), Text(l, style: TextStyle(fontSize: 10, color: Colors.white.withValues(alpha: 0.85)))]),
      );



  Future<void> _newOrder() async {
    final api = context.read<AuthProvider>().api;
    Map<String, dynamic> opt;
    try {
      opt = await api.clientWasteOptions();
    } catch (_) { return; }
    final projects = (opt['projects'] as List?) ?? [];
    if (projects.isEmpty) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('لا يوجد مشروع نفايات مرتبط', 'No waste project linked'))));
      return;
    }
    final pickups = (opt['pickups'] as List?) ?? [];
    final items = (opt['items'] as List?) ?? [];
    final types = (opt['types'] as List?) ?? [];
    int projId = projects.first['id'] as int;
    int? pickId, itemId, typeId;
    DateTime when = DateTime.now();
    final qtyCtrl = TextEditingController(text: '1');
    final notesCtrl = TextEditingController();
    String fmt(DateTime d) => '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}  ${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}';
    if (!mounted) return;
    InputDecoration dec(String label, IconData ic) => InputDecoration(labelText: label, prefixIcon: Icon(ic, size: 20, color: const Color(0xFF16A34A)), filled: true, fillColor: const Color(0xFFF4F7FB), border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none), isDense: true);
    final ok = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setSt) => Container(
          decoration: const BoxDecoration(color: Color(0xFFF4F7FB), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
          clipBehavior: Clip.antiAlias,
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Container(
              padding: const EdgeInsets.fromLTRB(18, 14, 18, 16),
              decoration: const BoxDecoration(gradient: LinearGradient(colors: [Color(0xFF115E4B), Color(0xFF16A34A)], begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Column(children: [
                Container(width: 40, height: 4, decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3))),
                const SizedBox(height: 12),
                Row(children: [const Text('♻️', style: TextStyle(fontSize: 26)), const SizedBox(width: 10), Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(tr('طلب رفع نفايات جديد', 'New collection order'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
                  Text(tr('اطلب رفع المخلفات من موقعك', 'Request pickup from your site'), style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 12)),
                ]))]),
              ]),
            ),
            Flexible(child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(16, 16, 16, MediaQuery.of(ctx).viewInsets.bottom + 16),
              child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                DropdownButtonFormField<int>(initialValue: projId, decoration: dec(tr('المشروع', 'Project'), Icons.folder_outlined),
                  items: [for (final p in projects) DropdownMenuItem(value: p['id'] as int, child: Text('${p['name']}'))], onChanged: (v) => setSt(() => projId = v ?? projId)),
                const SizedBox(height: 12),
                if (types.isNotEmpty) ...[
                  DropdownButtonFormField<int>(initialValue: typeId, decoration: dec(tr('نوع الطلب', 'Type'), Icons.category_outlined),
                    items: [for (final t in types) DropdownMenuItem(value: t['id'] as int, child: Text('${t['name']}'))], onChanged: (v) => setSt(() => typeId = v)),
                  const SizedBox(height: 12),
                ],
                if (pickups.isNotEmpty) ...[
                  DropdownButtonFormField<int>(initialValue: pickId, decoration: dec(tr('موقع الالتقاط', 'Pickup location'), Icons.place_outlined),
                    items: [for (final p in pickups) DropdownMenuItem(value: p['id'] as int, child: Text('${p['name']}'))], onChanged: (v) => setSt(() => pickId = v)),
                  const SizedBox(height: 12),
                ],
                // date & time picker
                InkWell(
                  onTap: () async {
                    final d = await showDatePicker(context: ctx, initialDate: when, firstDate: DateTime(2020), lastDate: DateTime(2100));
                    if (d == null) return;
                    final t = await showTimePicker(context: ctx, initialTime: TimeOfDay.fromDateTime(when));
                    setSt(() => when = DateTime(d.year, d.month, d.day, t?.hour ?? when.hour, t?.minute ?? when.minute));
                  },
                  child: InputDecorator(decoration: dec(tr('تاريخ ووقت الطلب', 'Request date & time'), Icons.event_outlined), child: Text(fmt(when), style: const TextStyle(fontWeight: FontWeight.w600))),
                ),
                const SizedBox(height: 12),
                Row(children: [
                  if (items.isNotEmpty) Expanded(flex: 2, child: DropdownButtonFormField<int>(initialValue: itemId, isExpanded: true, decoration: dec(tr('الصنف', 'Item'), Icons.recycling_outlined),
                    items: [for (final it in items) DropdownMenuItem(value: it['id'] as int, child: Text('${it['name']}', overflow: TextOverflow.ellipsis))], onChanged: (v) => setSt(() => itemId = v))),
                  if (items.isNotEmpty) const SizedBox(width: 10),
                  Expanded(child: TextField(controller: qtyCtrl, keyboardType: TextInputType.number, decoration: dec(tr('الكمية', 'Qty'), Icons.tag))),
                ]),
                const SizedBox(height: 12),
                TextField(controller: notesCtrl, maxLines: 2, decoration: dec(tr('ملاحظات', 'Notes'), Icons.sticky_note_2_outlined)),
                const SizedBox(height: 16),
                SizedBox(width: double.infinity, height: 52, child: ElevatedButton.icon(
                  onPressed: () => Navigator.pop(ctx, true), icon: const Icon(Icons.send_rounded),
                  label: Text(tr('إرسال الطلب', 'Submit request'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                  style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF16A34A), foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))))),
              ]),
            )),
          ]),
        ),
      ),
    );
    if (ok != true || !mounted) return;
    try {
      final iso = '${when.year}-${when.month.toString().padLeft(2, '0')}-${when.day.toString().padLeft(2, '0')} ${when.hour.toString().padLeft(2, '0')}:${when.minute.toString().padLeft(2, '0')}:00';
      final res = await api.clientWasteCreate(projId, pickupId: pickId, typeId: typeId, itemId: itemId, qty: double.tryParse(qtyCtrl.text) ?? 1.0, requestDatetime: iso, notes: notesCtrl.text);
      if (mounted) {
        _load();
        _loadSummary();
        await _wasteCongrats(res);
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  /// Congrats dialog after a trip is booked: the full trip card + a QR that
  /// leads to the trip record, and a Share button (professional PDF w/ QR).
  Future<void> _wasteCongrats(Map res) async {
    const green = Color(0xFF16A34A);
    final items = (res['items'] as List?) ?? const [];
    Widget kv(String k, String? v) => (v == null || v.isEmpty) ? const SizedBox.shrink()
        : Padding(padding: const EdgeInsets.symmetric(vertical: 3), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SizedBox(width: 96, child: Text(k, style: const TextStyle(color: Color(0xFF64748B), fontSize: 12))),
            const SizedBox(width: 6),
            Expanded(child: Text(v, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: Color(0xFF0F172A)))),
          ]));
    await showDialog(context: context, barrierDismissible: true, builder: (ctx) => Dialog(
      insetPadding: const EdgeInsets.all(18),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(22)),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 420),
        child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
          // celebratory header
          Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(20, 22, 20, 18),
            decoration: const BoxDecoration(
              gradient: LinearGradient(colors: [green, Color(0xFF0E7C43)], begin: Alignment.topRight, end: Alignment.bottomLeft),
              borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
            child: Column(children: [
              Container(width: 58, height: 58, alignment: Alignment.center,
                decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), shape: BoxShape.circle),
                child: const Text('🎉', style: TextStyle(fontSize: 30))),
              const SizedBox(height: 10),
              Text(tr('تم إنشاء طلب النقل بنجاح', 'Trip request created'),
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 17)),
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.22), borderRadius: BorderRadius.circular(20)),
                child: Text('${res['serial'] ?? ''}',
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13, letterSpacing: 0.5)),
              ),
            ]),
          ),
          Padding(padding: const EdgeInsets.fromLTRB(18, 16, 18, 6), child: Column(children: [
            // QR that leads to the trip record
            if (res['qr_image_url'] != null) Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: Colors.black12)),
              child: Column(children: [
                Image.network('${res['qr_image_url']}', width: 150, height: 150, fit: BoxFit.contain,
                    errorBuilder: (_, __, ___) => const SizedBox(width: 150, height: 150, child: Icon(Icons.qr_code_2_rounded, size: 90, color: Colors.black26))),
                const SizedBox(height: 4),
                Text(tr('امسح الرمز لعرض الرحلة', 'Scan to view the trip'),
                    style: const TextStyle(fontSize: 10.5, color: Color(0xFF64748B))),
              ]),
            ),
            const SizedBox(height: 14),
            Align(alignment: AlignmentDirectional.centerStart, child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              kv(tr('المشروع', 'Project'), res['project'] as String?),
              kv(tr('موقع الالتقاط', 'Pickup'), res['pickup'] as String?),
              kv(tr('النوع', 'Type'), res['type'] as String?),
              kv(tr('الموعد', 'Date/time'), (res['request_datetime'] as String?)?.replaceAll('T', ' ')),
              if (res['total_weight'] != null) kv(tr('الوزن التقديري', 'Est. weight'), '${res['total_weight']} كجم'),
              if (res['notes'] != null) kv(tr('ملاحظات', 'Notes'), res['notes'] as String?),
            ])),
            if (items.isNotEmpty) ...[
              const SizedBox(height: 8),
              Container(
                decoration: BoxDecoration(color: const Color(0xFFF1F5F9), borderRadius: BorderRadius.circular(12)),
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                child: Column(children: [
                  for (final it in items.cast<Map>())
                    Padding(padding: const EdgeInsets.symmetric(vertical: 2), child: Row(children: [
                      Expanded(child: Text('${it['name']}', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w600))),
                      Text('${it['qty']} × ${it['unit_weight']} = ${it['total_weight']} كجم',
                          style: const TextStyle(fontSize: 11, color: Color(0xFF64748B))),
                    ])),
                ]),
              ),
            ],
          ])),
          Padding(padding: const EdgeInsets.fromLTRB(16, 8, 16, 16), child: Column(children: [
            SizedBox(width: double.infinity, child: FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: green, padding: const EdgeInsets.symmetric(vertical: 13)),
              onPressed: () {
                Navigator.pop(ctx);
                Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
                    path: '/api/v1/client/waste/order/${res['id']}/report',
                    title: tr('تفاصيل الرحلة', 'Trip details'),
                    fileName: 'waste-order-${res['serial'] ?? res['id']}.pdf')));
              },
              icon: const Icon(Icons.ios_share_rounded, size: 18),
              label: Text(tr('مشاركة تفاصيل الرحلة (PDF + QR)', 'Share trip (PDF + QR)'),
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
            )),
            const SizedBox(height: 6),
            SizedBox(width: double.infinity, child: TextButton(
              onPressed: () => Navigator.pop(ctx),
              child: Text(tr('تم', 'Done'), style: const TextStyle(fontWeight: FontWeight.w800)),
            )),
          ])),
        ])),
      ),
    ));
  }
}

/// Waste statistics & reports — filter by period (month/year/custom), see
/// detailed aggregates + breakdowns, and print the monthly report (exact
/// service_order PDF) via the portal.
class WasteStatsScreen extends StatefulWidget {
  const WasteStatsScreen({super.key});
  @override
  State<WasteStatsScreen> createState() => _WasteStatsScreenState();
}

class _WasteStatsScreenState extends State<WasteStatsScreen> {
  static const _navy = Color(0xFF0E3A5F);
  static const _green = Color(0xFF16A34A);
  Future<Map<String, dynamic>>? _stats;
  DateTime _from = DateTime(DateTime.now().year, DateTime.now().month, 1);
  DateTime _to = DateTime.now();
  String _preset = 'month';

  @override
  void initState() {
    super.initState();
    _load();
  }

  String _fmt(DateTime d) => '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
  void _load() => setState(() => _stats = context.read<AuthProvider>().api.clientWasteStats(dateFrom: _fmt(_from), dateTo: _fmt(_to)));

  void _setPreset(String p) {
    final now = DateTime.now();
    setState(() {
      _preset = p;
      if (p == 'month') { _from = DateTime(now.year, now.month, 1); _to = now; }
      else if (p == 'last') { _from = DateTime(now.year, now.month - 1, 1); _to = DateTime(now.year, now.month, 0); }
      else if (p == 'year') { _from = DateTime(now.year, 1, 1); _to = now; }
      else if (p == 'all') { _from = DateTime(2020, 1, 1); _to = now; }
    });
    _load();
  }

  Future<void> _pickRange() async {
    final r = await showDateRangePicker(context: context, firstDate: DateTime(2020), lastDate: DateTime(2100), initialDateRange: DateTimeRange(start: _from, end: _to));
    if (r != null) { setState(() { _preset = 'custom'; _from = r.start; _to = r.end; }); _load(); }
  }

  Future<void> _printMonthly(String? path) async {
    if (path == null) return;
    Navigator.push(context, MaterialPageRoute(
        builder: (_) => PdfReportScreen(
            path: path, title: tr('تقرير النفايات', 'Waste report'), fileName: 'waste-report.pdf')));
  }


  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F7FB),
      appBar: AppBar(backgroundColor: _navy, foregroundColor: Colors.white, title: Text(tr('التقارير والإحصائيات', 'Reports & statistics'))),
      body: Column(children: [
        // period selector
        Container(
          color: Colors.white,
          padding: const EdgeInsets.fromLTRB(10, 10, 10, 8),
          child: Column(children: [
            SizedBox(height: 38, child: ListView(scrollDirection: Axis.horizontal, children: [
              for (final p in [['month', tr('هذا الشهر', 'This month')], ['last', tr('الشهر الماضي', 'Last month')], ['year', tr('هذه السنة', 'This year')], ['all', tr('الكل', 'All')]])
                Padding(padding: const EdgeInsets.only(right: 6), child: ChoiceChip(label: Text(p[1]), selected: _preset == p[0], onSelected: (_) => _setPreset(p[0]), selectedColor: _green, labelStyle: TextStyle(color: _preset == p[0] ? Colors.white : _navy, fontWeight: FontWeight.w700, fontSize: 12.5))),
              Padding(padding: const EdgeInsets.only(right: 6), child: ActionChip(avatar: const Icon(Icons.date_range, size: 16), label: Text(tr('مخصص', 'Custom')), onPressed: _pickRange)),
            ])),
            const SizedBox(height: 4),
            Text('${_fmt(_from)}  →  ${_fmt(_to)}', style: const TextStyle(color: Colors.grey, fontSize: 12, fontWeight: FontWeight.w600)),
          ]),
        ),
        Expanded(child: FutureBuilder<Map<String, dynamic>>(
          future: _stats,
          builder: (_, snap) {
            if (!snap.hasData) return const Center(child: CircularProgressIndicator(color: _green));
            final d = snap.data!;
            final byItem = (d['by_item'] as List?) ?? [];
            final byMonth = (d['by_month'] as List?) ?? [];
            final maxM = byMonth.isEmpty ? 1.0 : byMonth.map((m) => (m['orders'] as num).toDouble()).reduce((a, b) => a > b ? a : b);
            return ListView(padding: const EdgeInsets.all(14), children: [
              GridView.count(crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(), childAspectRatio: 1.7, crossAxisSpacing: 12, mainAxisSpacing: 12, children: [
                _kpi('📋', '${d['total_orders'] ?? 0}', tr('إجمالي الطلبات', 'Total orders'), _navy),
                _kpi('✅', '${d['completed'] ?? 0}', tr('مكتملة', 'Completed'), _green),
                _kpi('⚖️', '${d['total_weight'] ?? 0}', tr('الوزن (كجم)', 'Weight (kg)'), const Color(0xFF0891B2)),
                _kpi('📦', '${d['total_quantity'] ?? 0}', tr('إجمالي الكمية', 'Total qty'), const Color(0xFF6366F1)),
              ]),
              const SizedBox(height: 8),
              if (byMonth.isNotEmpty) _panel(tr('حسب الشهر', 'By month'), Column(children: [
                for (final m in byMonth.reversed) Padding(padding: const EdgeInsets.symmetric(vertical: 4), child: Row(children: [
                  SizedBox(width: 62, child: Text('${m['month']}', style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: _navy))),
                  Expanded(child: Stack(children: [
                    Container(height: 22, decoration: BoxDecoration(color: Colors.grey.shade100, borderRadius: BorderRadius.circular(6))),
                    FractionallySizedBox(widthFactor: ((m['orders'] as num).toDouble() / maxM).clamp(0.04, 1.0), child: Container(height: 22, decoration: BoxDecoration(gradient: const LinearGradient(colors: [_green, Color(0xFF15803D)]), borderRadius: BorderRadius.circular(6)))),
                  ])),
                  const SizedBox(width: 8),
                  Text('${m['orders']} · ${m['weight']}kg', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Colors.grey)),
                ])),
              ])),
              if (byItem.isNotEmpty) _panel(tr('أكثر الأصناف', 'Top items'), Column(children: [
                for (final i in byItem) Padding(padding: const EdgeInsets.symmetric(vertical: 5), child: Row(children: [
                  ClipRRect(borderRadius: BorderRadius.circular(9), child: i['image'] != null ? Image.network('${i['image']}', width: 38, height: 38, fit: BoxFit.cover, errorBuilder: (_, __, ___) => _ph()) : _ph()),
                  const SizedBox(width: 10),
                  Expanded(child: Text('${i['name']}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5))),
                  Text('${i['qty']}', style: const TextStyle(fontWeight: FontWeight.w900, color: _green, fontSize: 15)),
                  Text('  (${i['orders']})', style: const TextStyle(fontSize: 11, color: Colors.grey)),
                ])),
              ])),
              const SizedBox(height: 12),
              SizedBox(height: 52, child: ElevatedButton.icon(
                onPressed: () => _printMonthly(d['print_path'] as String?),
                icon: const Icon(Icons.print_rounded),
                label: Text(tr('طباعة التقرير الشهري', 'Print monthly report'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
                style: ElevatedButton.styleFrom(backgroundColor: _navy, foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
              )),
              const SizedBox(height: 24),
            ]);
          },
        )),
      ]),
    );
  }

  Widget _ph() => Container(width: 38, height: 38, color: _green.withValues(alpha: 0.1), alignment: Alignment.center, child: const Text('📦', style: TextStyle(fontSize: 17)));

  Widget _kpi(String ic, String v, String l, Color c) => Container(
        padding: const EdgeInsets.all(14),
        // A borderRadius is only legal on a uniform Border; the accent edge is a
        // bar of its own, or this asserts at paint time and goes grey.
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
            boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 2))],
            border: Border.all(color: Colors.black12)),
        child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Container(width: 4, decoration: BoxDecoration(color: c,
              borderRadius: BorderRadius.circular(2))),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
          Row(children: [Text(ic, style: const TextStyle(fontSize: 19)), const Spacer(), Text(v, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 22, color: c))]),
          const SizedBox(height: 3),
          Text(l, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Colors.grey)),
        ])),
        ]),
      );

  Widget _panel(String title, Widget child) => Container(
        margin: const EdgeInsets.only(top: 12),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 2))]),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [Container(width: 4, height: 16, decoration: BoxDecoration(color: _green, borderRadius: BorderRadius.circular(3))), const SizedBox(width: 8), Text(title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: _navy))]),
          const SizedBox(height: 10),
          child,
        ]),
      );
}
