import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'waste_ops_shell.dart';
import 'pdf_report_screen.dart';

// ============================================================================
// شاشات مدير العمليات: سجل الرحلات + سجلات الاستلام (أرشيف + حالي) بالوسائط.
// ============================================================================

/// شبكة وسائط (صور/فيديو) قابلة للفتح.
class WasteMediaGrid extends StatelessWidget {
  const WasteMediaGrid({super.key, required this.media, this.proof});
  final List media;
  final String? proof;

  @override
  Widget build(BuildContext context) {
    final items = <Map>[];
    if (proof != null) items.add({'url': proof, 'is_video': false, 'proof': true});
    items.addAll(media.cast<Map>());
    if (items.isEmpty) return const SizedBox.shrink();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Icon(Icons.perm_media_rounded, size: 16, color: WOps.green),
        const SizedBox(width: 6),
        Text('${tr('الصور والفيديو', 'Photos & videos')} (${items.length})',
            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: WOps.deep)),
      ]),
      const SizedBox(height: 8),
      GridView.count(
        crossAxisCount: 3, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
        mainAxisSpacing: 8, crossAxisSpacing: 8,
        children: [for (final m in items) _thumb(context, m)],
      ),
    ]);
  }

  Widget _thumb(BuildContext context, Map m) {
    final url = '${m['url']}';
    final isVideo = m['is_video'] == true;
    return GestureDetector(
      onTap: () async {
        if (isVideo) {
          final u = Uri.parse(url);
          if (await canLaunchUrl(u)) launchUrl(u, mode: LaunchMode.externalApplication);
        } else {
          showDialog(context: context, builder: (_) => Dialog(
            backgroundColor: Colors.black,
            child: Stack(children: [
              InteractiveViewer(child: Center(child: Image.network(url, fit: BoxFit.contain))),
              Positioned(top: 6, right: 6, child: IconButton(
                icon: const Icon(Icons.close_rounded, color: Colors.white),
                onPressed: () => Navigator.pop(context))),
            ]),
          ));
        }
      },
      child: ClipRRect(
        borderRadius: BorderRadius.circular(10),
        child: Stack(fit: StackFit.expand, children: [
          Container(color: const Color(0xFFE2E8F0)),
          if (!isVideo) Image.network(url, fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => const Icon(Icons.broken_image_rounded, color: WOps.slate)),
          if (isVideo) Container(color: Colors.black87,
              child: const Center(child: Icon(Icons.play_circle_fill_rounded, color: Colors.white, size: 34))),
          if (m['proof'] == true) Positioned(bottom: 4, left: 4, child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(color: WOps.green, borderRadius: BorderRadius.circular(6)),
              child: Text(tr('إثبات', 'Proof'), style: const TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.w700)))),
        ]),
      ),
    );
  }
}

/// شريط بحث + فلتر شهر مشترك.
class WasteRecordsHeader extends StatelessWidget {
  const WasteRecordsHeader({super.key, required this.onSearch, required this.onMonth,
      required this.q, required this.month, this.tabs, this.tab, this.onTab, required this.onMonthlyReport});
  final ValueChanged<String> onSearch;
  final ValueChanged<String?> onMonth;
  final String q;
  final String? month;
  final List<String>? tabs;
  final int? tab;
  final ValueChanged<int>? onTab;
  final VoidCallback onMonthlyReport;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
      child: Column(children: [
        Row(children: [
          Expanded(child: SizedBox(height: 42, child: TextField(
            onChanged: onSearch,
            decoration: InputDecoration(
              hintText: tr('بحث برقم الطلب/الرحلة…', 'Search by number…'),
              prefixIcon: const Icon(Icons.search_rounded, size: 20),
              isDense: true, filled: true, fillColor: WOps.bg,
              contentPadding: const EdgeInsets.symmetric(vertical: 4),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            ),
          ))),
          const SizedBox(width: 8),
          _monthBtn(context),
          const SizedBox(width: 6),
          IconButton(
            tooltip: tr('التقرير الشهري', 'Monthly report'),
            onPressed: onMonthlyReport,
            icon: const Icon(Icons.picture_as_pdf_rounded, color: WOps.green),
          ),
        ]),
        if (tabs != null) ...[
          const SizedBox(height: 8),
          Row(children: [
            for (var i = 0; i < tabs!.length; i++)
              Expanded(child: GestureDetector(
                onTap: () => onTab?.call(i),
                child: Container(
                  margin: const EdgeInsets.symmetric(horizontal: 3),
                  padding: const EdgeInsets.symmetric(vertical: 8),
                  decoration: BoxDecoration(
                    color: tab == i ? WOps.green : WOps.bg, borderRadius: BorderRadius.circular(10)),
                  child: Text(tabs![i], textAlign: TextAlign.center,
                      style: TextStyle(color: tab == i ? Colors.white : WOps.slate,
                          fontWeight: FontWeight.w700, fontSize: 12.5)),
                ),
              )),
          ]),
        ],
      ]),
    );
  }

  Widget _monthBtn(BuildContext context) => OutlinedButton.icon(
        style: OutlinedButton.styleFrom(
          foregroundColor: month != null ? WOps.green : WOps.slate,
          side: BorderSide(color: month != null ? WOps.green : const Color(0xFFCBD5E1)),
          padding: const EdgeInsets.symmetric(horizontal: 10), minimumSize: const Size(0, 42)),
        onPressed: () async {
          final now = DateTime.now();
          final picked = await showDatePicker(
            context: context, initialDate: now, firstDate: DateTime(now.year - 3), lastDate: now,
            helpText: tr('اختر شهر الأرشيف', 'Pick archive month'));
          if (picked != null) onMonth('${picked.year}-${picked.month.toString().padLeft(2, '0')}');
        },
        icon: const Icon(Icons.calendar_month_rounded, size: 18),
        label: Text(month ?? tr('الشهر', 'Month'), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
      );
}

// ---------------------------------------------------------------------------
// سجل الرحلات (المدير)
// ---------------------------------------------------------------------------
class WasteOpsTripsScreen extends StatefulWidget {
  const WasteOpsTripsScreen({super.key});
  @override
  State<WasteOpsTripsScreen> createState() => _WasteOpsTripsScreenState();
}

class _WasteOpsTripsScreenState extends State<WasteOpsTripsScreen> {
  int _tab = 0;
  String _q = '';
  String? _month;
  late Future<List<dynamic>> _f;
  static const _filters = ['all', 'current', 'archive'];

  @override
  void initState() { super.initState(); _load(); }
  void _load() => setState(() => _f = context.read<AuthProvider>().api
      .wasteOpsTrips(filter: _filters[_tab], q: _q, month: _month));

  void _monthly() {
    final api = context.read<AuthProvider>().api;
    Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
        path: api.wasteOpsMonthlyReportPath(month: _month),
        title: tr('التقرير الشهري للرحلات', 'Monthly trips report'),
        fileName: 'waste-monthly-${_month ?? 'all'}.pdf')));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: WOps.bg,
      appBar: AppBar(backgroundColor: WOps.deep, foregroundColor: Colors.white,
          title: Text(tr('سجل الرحلات', 'Trips log'))),
      body: Column(children: [
        WasteRecordsHeader(
          q: _q, month: _month,
          tabs: [tr('الكل', 'All'), tr('الحالية', 'Current'), tr('الأرشيف', 'Archive')],
          tab: _tab, onTab: (i) { setState(() => _tab = i); _load(); },
          onSearch: (v) { _q = v; _load(); },
          onMonth: (m) { setState(() => _month = m); _load(); },
          onMonthlyReport: _monthly,
        ),
        Expanded(child: RefreshIndicator(
          onRefresh: () async => _load(),
          child: FutureBuilder<List<dynamic>>(
            future: _f,
            builder: (context, snap) {
              if (snap.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator(color: WOps.green));
              }
              final rows = (snap.data ?? const []).cast<Map>();
              if (rows.isEmpty) {
                return ListView(children: [const SizedBox(height: 120), Center(child: Column(children: [
                  const Icon(Icons.local_shipping_outlined, size: 54, color: WOps.slate),
                  const SizedBox(height: 8),
                  Text(tr('لا رحلات', 'No trips'), style: const TextStyle(color: WOps.slate)),
                ]))]);
              }
              return ListView.builder(
                padding: const EdgeInsets.all(12), itemCount: rows.length,
                itemBuilder: (_, i) => _tripCard(rows[i]),
              );
            },
          ),
        )),
      ]),
    );
  }

  Widget _tripCard(Map t) {
    final media = (t['media'] as List?) ?? const [];
    return GestureDetector(
      onTap: () => _openTrip(t),
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
            boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 8, offset: const Offset(0, 2))]),
        child: Padding(padding: const EdgeInsets.all(14), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(width: 42, height: 42, decoration: BoxDecoration(
                color: WOps.green.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)),
                child: const Icon(Icons.local_shipping_rounded, color: WOps.green)),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${tr('رحلة', 'Trip')} ${t['sequence'] ?? ''}',
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: WOps.ink)),
              Text([t['client'], t['center']].whereType<String>().join(' · '),
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: WOps.slate, fontSize: 12)),
            ])),
            _stateChip(t),
          ]),
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 6, children: [
            if (t['driver'] != null) _chip('🚚 ${t['driver']}'),
            if (t['date'] != null) _chip('📅 ${t['date']}'),
            _chip('⚖️ ${t['total_weight'] ?? 0} kg'),
            _chip('📦 ${(t['items'] as List?)?.length ?? 0}'),
            if (media.isNotEmpty) _chip('🖼️ ${media.length}'),
          ]),
        ])),
      ),
    );
  }

  void _openTrip(Map t) {
    showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
        builder: (_) => _RecordDetailSheet(record: t, isTrip: true));
  }
}

// ---------------------------------------------------------------------------
// سجلات الاستلام (المدير)
// ---------------------------------------------------------------------------
class WasteOpsReceiptsScreen extends StatefulWidget {
  const WasteOpsReceiptsScreen({super.key});
  @override
  State<WasteOpsReceiptsScreen> createState() => _WasteOpsReceiptsScreenState();
}

class _WasteOpsReceiptsScreenState extends State<WasteOpsReceiptsScreen> {
  String _q = '';
  String? _month;
  late Future<List<dynamic>> _f;

  @override
  void initState() { super.initState(); _load(); }
  void _load() => setState(() => _f = context.read<AuthProvider>().api.wasteOpsReceipts(q: _q, month: _month));

  void _monthly() {
    final api = context.read<AuthProvider>().api;
    Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
        path: api.wasteOpsMonthlyReportPath(month: _month),
        title: tr('تقرير الاستلام الشهري', 'Monthly intake report'),
        fileName: 'waste-monthly-${_month ?? 'all'}.pdf')));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: WOps.bg,
      appBar: AppBar(backgroundColor: WOps.deep, foregroundColor: Colors.white,
          title: Text(tr('سجلات الاستلام', 'Intake records'))),
      body: Column(children: [
        WasteRecordsHeader(
          q: _q, month: _month,
          onSearch: (v) { _q = v; _load(); },
          onMonth: (m) { setState(() => _month = m); _load(); },
          onMonthlyReport: _monthly,
        ),
        Expanded(child: RefreshIndicator(
          onRefresh: () async => _load(),
          child: FutureBuilder<List<dynamic>>(
            future: _f,
            builder: (context, snap) {
              if (snap.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator(color: WOps.green));
              }
              final rows = (snap.data ?? const []).cast<Map>();
              if (rows.isEmpty) {
                return ListView(children: [const SizedBox(height: 120), Center(child: Column(children: [
                  const Icon(Icons.factory_outlined, size: 54, color: WOps.slate),
                  const SizedBox(height: 8),
                  Text(tr('لا سجلات استلام', 'No intake records'), style: const TextStyle(color: WOps.slate)),
                ]))]);
              }
              return ListView.builder(
                padding: const EdgeInsets.all(12), itemCount: rows.length,
                itemBuilder: (_, i) => _receiptCard(rows[i]),
              );
            },
          ),
        )),
      ]),
    );
  }

  Widget _receiptCard(Map o) {
    final media = (o['media'] as List?) ?? const [];
    final hasMedia = media.isNotEmpty || o['proof'] != null;
    return GestureDetector(
      onTap: () => showModalBottomSheet(context: context, isScrollControlled: true,
          backgroundColor: Colors.transparent, builder: (_) => _RecordDetailSheet(record: o, isTrip: false)),
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
            boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 8, offset: const Offset(0, 2))]),
        child: Padding(padding: const EdgeInsets.all(14), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(width: 42, height: 42, decoration: BoxDecoration(
                color: const Color(0xFF0891B2).withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)),
                child: const Icon(Icons.inventory_2_rounded, color: Color(0xFF0891B2))),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${tr('طلب', 'Order')} ${o['serial'] ?? ''}',
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: WOps.ink)),
              Text([o['client'], o['center']].whereType<String>().join(' · '),
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: WOps.slate, fontSize: 12)),
            ])),
            _stateChip(o),
          ]),
          const SizedBox(height: 10),
          Wrap(spacing: 8, runSpacing: 6, children: [
            if (o['receiver'] != null) _chip('🏭 ${o['receiver']}'),
            _chip('⚖️ ${o['final_weight'] ?? 0} kg'),
            if (o['date'] != null) _chip('📅 ${o['date']}'),
            if (hasMedia) _chip('🖼️ ${media.length + (o['proof'] != null ? 1 : 0)}'),
          ]),
        ])),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// تفاصيل السجل (رحلة/استلام) — أصناف + وسائط + تقرير
// ---------------------------------------------------------------------------
class _RecordDetailSheet extends StatelessWidget {
  const _RecordDetailSheet({required this.record, required this.isTrip});
  final Map record;
  final bool isTrip;

  @override
  Widget build(BuildContext context) {
    final items = (record['items'] as List?) ?? const [];
    final media = (record['media'] as List?) ?? const [];
    final title = isTrip ? '${tr('رحلة', 'Trip')} ${record['sequence'] ?? ''}'
                         : '${tr('طلب', 'Order')} ${record['serial'] ?? ''}';
    return DraggableScrollableSheet(
      initialChildSize: 0.9, minChildSize: 0.5, maxChildSize: 0.96, expand: false,
      builder: (context, sc) => Container(
        decoration: const BoxDecoration(color: WOps.bg, borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
        child: Column(children: [
          Container(width: double.infinity, padding: const EdgeInsets.fromLTRB(18, 14, 18, 16),
            decoration: const BoxDecoration(color: WOps.deep, borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12),
                  decoration: BoxDecoration(color: Colors.white38, borderRadius: BorderRadius.circular(3)))),
              Row(children: [
                Expanded(child: Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18))),
                _stateChip(record),
              ]),
              const SizedBox(height: 6),
              Text([record['client'], record['center'], record['driver'], record['receiver']]
                  .whereType<String>().join(' · '),
                  style: const TextStyle(color: Colors.white70, fontSize: 12.5)),
            ]),
          ),
          Expanded(child: ListView(controller: sc, padding: const EdgeInsets.all(16), children: [
            // ملخّص
            Container(padding: const EdgeInsets.all(12), decoration: BoxDecoration(
                color: Colors.white, borderRadius: BorderRadius.circular(14)),
              child: Row(mainAxisAlignment: MainAxisAlignment.spaceAround, children: [
                _stat(tr('الكمية', 'Qty'), '${record['total_quantity'] ?? record['qty_total'] ?? '-'}'),
                _stat(tr('الوزن', 'Weight'), '${record['total_weight'] ?? record['final_weight'] ?? 0} kg'),
                _stat(tr('التاريخ', 'Date'), '${record['date'] ?? '-'}'),
              ])),
            if ((record['final_note'] ?? '').toString().isNotEmpty) ...[
              const SizedBox(height: 10),
              Container(padding: const EdgeInsets.all(12), width: double.infinity, decoration: BoxDecoration(
                  color: const Color(0xFFFFF7ED), borderRadius: BorderRadius.circular(12), border: Border.all(color: const Color(0xFFFED7AA))),
                child: Text('📝 ${record['final_note']}', style: const TextStyle(color: Color(0xFF9A3412), fontSize: 13))),
            ],
            // ---- كامل التفاصيل ----
            const SizedBox(height: 14),
            Text(tr('التفاصيل', 'Details'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: WOps.deep)),
            const SizedBox(height: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
              child: Column(children: [
                _detail(Icons.tag_rounded, tr('الحالة', 'State'), '${record['state_label'] ?? '-'}'),
                _detail(Icons.business_rounded, tr('المشروع', 'Project'), record['project']),
                _detail(Icons.receipt_long_rounded, tr('الطلب', 'Order'), record['order_serial'] ?? record['serial']),
                _detail(Icons.person_rounded, tr('العميل', 'Client'), record['client']),
                _detail(Icons.location_on_outlined, tr('موقع الالتقاط', 'Pickup'), record['pickup']),
                _detail(Icons.factory_rounded, tr('مركز المعالجة', 'Center'), record['center']),
                _detail(Icons.local_shipping_rounded, tr('السائق', 'Driver'), record['driver']),
                _detail(Icons.how_to_reg_rounded, tr('المستلم', 'Receiver'), record['receiver']),
                _detail(Icons.confirmation_number_outlined, tr('المرجع', 'Reference'), record['reference']),
                _detail(Icons.event_rounded, tr('تاريخ الرحلة', 'Trip date'), record['date']),
                _detail(Icons.schedule_rounded, tr('موعد الرفع', 'Pickup time'), record['pickup_at']),
              ]),
            ),
            // الأصناف
            if (items.isNotEmpty) ...[
              const SizedBox(height: 14),
              Text(tr('الأصناف', 'Items'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: WOps.deep)),
              const SizedBox(height: 8),
              for (final l in items.cast<Map>()) Container(
                margin: const EdgeInsets.only(bottom: 6), padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(10)),
                child: Row(children: [
                  const Icon(Icons.category_rounded, size: 18, color: WOps.green),
                  const SizedBox(width: 8),
                  Expanded(child: Text('${l['item'] ?? '-'}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13))),
                  Text('${l['qty'] ?? 0} × ${l['weight'] ?? 0}kg',
                      style: const TextStyle(color: WOps.slate, fontWeight: FontWeight.w700, fontSize: 12)),
                ]),
              ),
            ],
            // الوسائط
            const SizedBox(height: 14),
            WasteMediaGrid(media: media, proof: record['proof'] as String?),
            const SizedBox(height: 18),
            // التقرير
            if (record['report_path'] != null) SizedBox(width: double.infinity, height: 50,
              child: FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: WOps.green),
                onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
                    path: '${record['report_path']}',
                    title: tr('التقرير الكامل', 'Full report'),
                    fileName: '${isTrip ? 'trip' : 'order'}-${record['id']}.pdf'))),
                icon: const Icon(Icons.picture_as_pdf_rounded),
                label: Text(tr('عرض / طباعة التقرير الكامل', 'View / print full report'),
                    style: const TextStyle(fontWeight: FontWeight.w800)),
              )),
            const SizedBox(height: 20),
          ])),
        ]),
      ),
    );
  }

  Widget _stat(String l, String v) => Column(children: [
        Text(v, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: WOps.ink)),
        Text(l, style: const TextStyle(color: WOps.slate, fontSize: 11)),
      ]);

  /// صف تفصيلي — يُعرض فقط إن كانت القيمة موجودة.
  Widget _detail(IconData ic, String k, dynamic v) {
    final val = (v ?? '').toString().trim();
    if (val.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Icon(ic, size: 17, color: WOps.slate),
        const SizedBox(width: 10),
        SizedBox(width: 92, child: Text(k, style: const TextStyle(color: WOps.slate, fontSize: 12.5))),
        Expanded(child: Text(val, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: WOps.ink))),
      ]),
    );
  }
}

// ---- shared bits -----------------------------------------------------------
Widget _chip(String t) => Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
      decoration: BoxDecoration(color: WOps.bg, borderRadius: BorderRadius.circular(8)),
      child: Text(t, style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w600, color: WOps.ink)),
    );

Widget _stateChip(Map r) {
  final done = r['state'] == 'completed' || r['state'] == 'delivered';
  final c = done ? WOps.green : (r['state'] == 'cancelled' ? const Color(0xFFE11D48) : WOps.amber);
  return Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
    decoration: BoxDecoration(color: c.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(20)),
    child: Text('${r['state_label'] ?? ''}', style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 11)),
  );
}
