import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'excel_export.dart';
import 'pdf_report_screen.dart';

/// The client's full asset register — KPIs, category/status filters, search,
/// and each asset opening a professional detail sheet with its QR label print,
/// work-order history and Excel export.
class ClientAssetsScreen extends StatefulWidget {
  const ClientAssetsScreen({super.key});
  @override
  State<ClientAssetsScreen> createState() => _ClientAssetsScreenState();
}

class _ClientAssetsScreenState extends State<ClientAssetsScreen> {
  Map<String, dynamic>? _summary;
  Future<List<dynamic>>? _list;
  String _category = 'all';
  String _status = 'all';
  String _q = '';
  Timer? _debounce;

  static const _accent = Color(0xFF0891B2);
  static const _navy = Color(0xFF0E3A5F);
  static const _catIcons = {
    'hvac': Icons.ac_unit_rounded, 'electrical': Icons.bolt_rounded,
    'plumbing': Icons.plumbing_rounded, 'elevator': Icons.elevator_rounded,
    'fire': Icons.local_fire_department_rounded, 'generator': Icons.electrical_services_rounded,
    'cctv': Icons.videocam_rounded, 'furniture': Icons.chair_rounded, 'other': Icons.category_rounded,
  };
  static const _statusStyle = {
    'operational': (Color(0xFF16A34A), Icons.check_circle_rounded),
    'maintenance': (Color(0xFFF7A23B), Icons.build_rounded),
    'faulty': (Color(0xFFE5484D), Icons.error_rounded),
    'retired': (Color(0xFF64748B), Icons.do_not_disturb_on_rounded),
  };

  @override
  void initState() {
    super.initState();
    _loadSummary();
    _load();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  Future<void> _loadSummary() async {
    try {
      final s = await context.read<AuthProvider>().api.clientAssetsSummary();
      if (mounted) setState(() => _summary = s);
    } catch (_) {}
  }

  void _load() => _list = context.read<AuthProvider>().api.clientAssets(category: _category, status: _status, q: _q);

  void _search(String v) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 400), () { if (mounted) setState(() { _q = v; _load(); }); });
  }

  @override
  Widget build(BuildContext context) {
    final s = _summary ?? const {};
    return Scaffold(
      backgroundColor: const Color(0xFFF6F7F9),
      appBar: AppBar(
        title: Text(tr('الأصول', 'Assets')),
        backgroundColor: _accent, foregroundColor: Colors.white,
        actions: [
          IconButton(icon: const Icon(Icons.grid_on_rounded), tooltip: tr('تصدير Excel', 'Export Excel'),
              onPressed: () => exportExcelFile(context, path: '/cafm/assets/export',
                  fileName: 'assets.xlsx', shareText: tr('سجل الأصول', 'Asset register'))),
        ],
      ),
      body: RefreshIndicator(
        color: _accent,
        onRefresh: () async { await _loadSummary(); setState(_load); },
        child: ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
          _kpis(s),
          const SizedBox(height: 12),
          _searchBar(),
          const SizedBox(height: 8),
          _statusChips(s),
          const SizedBox(height: 8),
          _categoryChips(s),
          const SizedBox(height: 8),
          FutureBuilder<List<dynamic>>(
            future: _list,
            builder: (_, snap) {
              if (snap.connectionState == ConnectionState.waiting) {
                return const Padding(padding: EdgeInsets.symmetric(vertical: 50), child: Center(child: CircularProgressIndicator(color: _accent)));
              }
              final rows = (snap.data ?? const []).cast<Map>();
              if (rows.isEmpty) {
                return Padding(padding: const EdgeInsets.all(40), child: Center(
                    child: Text(tr('لا أصول مطابقة', 'No matching assets'), style: TextStyle(color: Colors.grey.shade500))));
              }
              return Column(children: [
                Align(alignment: Alignment.centerRight, child: Padding(
                  padding: const EdgeInsets.only(bottom: 6, right: 4),
                  child: Text(tr('${rows.length} أصل', '${rows.length} assets'),
                      style: TextStyle(fontSize: 12, color: Colors.grey.shade600, fontWeight: FontWeight.w700)))),
                ...rows.map(_assetCard),
              ]);
            },
          ),
        ]),
      ),
    );
  }

  Widget _kpis(Map s) {
    if (s['available'] == false) return const SizedBox.shrink();
    return CustomPaint(
      painter: const BrandPattern(opacity: 0.06),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [Color(0xFF0EA5C4), Color(0xFF0891B2), Color(0xFF0E5E73)],
              begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.circular(18),
          boxShadow: [BoxShadow(color: _accent.withValues(alpha: 0.3), blurRadius: 12, offset: const Offset(0, 6))],
        ),
        child: Column(children: [
          Row(children: [
            _kpi('${s['total'] ?? 0}', tr('إجمالي الأصول', 'Total assets'), Icons.inventory_2_rounded),
            _kdiv(),
            _kpi('${s['operational'] ?? 0}', tr('تعمل', 'Operational'), Icons.check_circle_rounded),
            _kdiv(),
            _kpi('${s['maintenance'] ?? 0}', tr('صيانة', 'Maintenance'), Icons.build_rounded),
            _kdiv(),
            _kpi('${s['faulty'] ?? 0}', tr('معطّلة', 'Faulty'), Icons.error_rounded),
          ]),
          if (((s['warranty_soon'] ?? 0) as int) > 0 || ((s['inspection_due'] ?? 0) as int) > 0) ...[
            const SizedBox(height: 12),
            Row(children: [
              if (((s['warranty_soon'] ?? 0) as int) > 0)
                Expanded(child: _alert(Icons.verified_rounded, tr('${s['warranty_soon']} ضمان ينتهي قريبًا', '${s['warranty_soon']} warranties expiring'))),
              if (((s['warranty_soon'] ?? 0) as int) > 0 && ((s['inspection_due'] ?? 0) as int) > 0) const SizedBox(width: 8),
              if (((s['inspection_due'] ?? 0) as int) > 0)
                Expanded(child: _alert(Icons.event_busy_rounded, tr('${s['inspection_due']} فحص مستحقّ', '${s['inspection_due']} inspections due'))),
            ]),
          ],
        ]),
      ),
    );
  }

  Widget _kpi(String v, String l, IconData ic) => Expanded(child: Column(children: [
        Icon(ic, color: Colors.white, size: 17),
        const SizedBox(height: 4),
        Text(v, style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
        Text(l, maxLines: 1, overflow: TextOverflow.ellipsis,
            style: TextStyle(color: Colors.white.withValues(alpha: 0.82), fontSize: 9, fontWeight: FontWeight.w600)),
      ]));

  Widget _kdiv() => Container(width: 1, height: 34, color: Colors.white.withValues(alpha: 0.2));

  Widget _alert(IconData ic, String t) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(10)),
        child: Row(children: [
          Icon(ic, size: 14, color: Colors.white),
          const SizedBox(width: 6),
          Expanded(child: Text(t, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.w700))),
        ]),
      );

  Widget _searchBar() => TextField(
        onChanged: _search,
        decoration: InputDecoration(
          hintText: tr('ابحث بالاسم أو الرمز أو الرقم التسلسلي…', 'Search name, code or serial…'),
          prefixIcon: const Icon(Icons.search_rounded, size: 20),
          isDense: true, filled: true, fillColor: Colors.white,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
        ),
      );

  Widget _statusChips(Map s) {
    final chips = [
      ('all', tr('الكل', 'All'), Icons.apps_rounded),
      ('operational', tr('تعمل', 'Operational'), Icons.check_circle_rounded),
      ('maintenance', tr('صيانة', 'Maintenance'), Icons.build_rounded),
      ('faulty', tr('معطّلة', 'Faulty'), Icons.error_rounded),
      ('retired', tr('خارج الخدمة', 'Retired'), Icons.do_not_disturb_on_rounded),
    ];
    return SizedBox(height: 36, child: ListView(scrollDirection: Axis.horizontal, children: [
      for (final ch in chips)
        Padding(padding: const EdgeInsets.only(left: 7), child: ChoiceChip(
          selected: _status == ch.$1, showCheckmark: false, visualDensity: VisualDensity.compact,
          avatar: Icon(ch.$3, size: 15, color: _status == ch.$1 ? Colors.white : _navy),
          label: Text(ch.$2, style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: _status == ch.$1 ? Colors.white : _navy)),
          selectedColor: _accent, backgroundColor: Colors.white,
          side: BorderSide(color: _status == ch.$1 ? _accent : Colors.grey.shade300),
          onSelected: (_) => setState(() { _status = ch.$1; _load(); }),
        )),
    ]));
  }

  Widget _categoryChips(Map s) {
    final cats = ((s['by_category'] as List?) ?? const []).cast<Map>();
    if (cats.isEmpty) return const SizedBox.shrink();
    return SizedBox(height: 34, child: ListView(scrollDirection: Axis.horizontal, children: [
      Padding(padding: const EdgeInsets.only(left: 7), child: ChoiceChip(
        selected: _category == 'all', showCheckmark: false, visualDensity: VisualDensity.compact,
        label: Text(tr('كل الفئات', 'All categories'), style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: _category == 'all' ? Colors.white : _navy)),
        selectedColor: _navy, backgroundColor: Colors.white,
        side: BorderSide(color: _category == 'all' ? _navy : Colors.grey.shade300),
        onSelected: (_) => setState(() { _category = 'all'; _load(); }),
      )),
      for (final c in cats)
        Padding(padding: const EdgeInsets.only(left: 7), child: ChoiceChip(
          selected: _category == c['v'], showCheckmark: false, visualDensity: VisualDensity.compact,
          avatar: Icon(_catIcons['${c['v']}'] ?? Icons.category_rounded, size: 14, color: _category == c['v'] ? Colors.white : _navy),
          label: Text('${c['l']} (${c['count']})', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: _category == c['v'] ? Colors.white : _navy)),
          selectedColor: _navy, backgroundColor: Colors.white,
          side: BorderSide(color: _category == c['v'] ? _navy : Colors.grey.shade300),
          onSelected: (_) => setState(() { _category = '${c['v']}'; _load(); }),
        )),
    ]));
  }

  Widget _assetCard(Map a) {
    final ss = _statusStyle['${a['status']}'] ?? (const Color(0xFF64748B), Icons.help_rounded);
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: Colors.white, borderRadius: BorderRadius.circular(14),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 6, offset: const Offset(0, 3))],
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => _openAsset(a['id'] as int, '${a['name']}'),
        child: Padding(
          padding: const EdgeInsets.all(11),
          child: Row(children: [
            Container(
              width: 46, height: 46, alignment: Alignment.center,
              decoration: BoxDecoration(color: _accent.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(12)),
              child: Icon(_catIcons['${a['category']}'] ?? Icons.category_rounded, color: _accent, size: 24),
            ),
            const SizedBox(width: 11),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${a['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: _navy)),
              const SizedBox(height: 2),
              Text([
                if (a['code'] != null) '${a['code']}',
                if (a['building'] != null) '${a['building']}',
                if (a['location'] != null) '${a['location']}',
              ].join(' · '), maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
              if (a['brand'] != null || a['model'] != null) ...[
                const SizedBox(height: 2),
                Text([a['brand'], a['model']].where((x) => x != null).join(' '),
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 10, color: Colors.grey.shade500)),
              ],
            ])),
            Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(color: ss.$1.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Icon(ss.$2, size: 11, color: ss.$1),
                  const SizedBox(width: 3),
                  Text('${a['status_label']}', style: TextStyle(color: ss.$1, fontSize: 9.5, fontWeight: FontWeight.w900)),
                ]),
              ),
              const SizedBox(height: 6),
              if (((a['wo_count'] ?? 0) as int) > 0)
                Text(tr('${a['wo_count']} أمر عمل', '${a['wo_count']} WOs'),
                    style: TextStyle(fontSize: 9.5, color: Colors.grey.shade500, fontWeight: FontWeight.w600)),
            ]),
          ]),
        ),
      ),
    );
  }

  void _openAsset(int id, String name) {
    showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.85, minChildSize: 0.5, maxChildSize: 0.96,
        builder: (_, sc) => FutureBuilder<Map<String, dynamic>>(
          future: context.read<AuthProvider>().api.clientAsset(id),
          builder: (_, snap) {
            final d = snap.data ?? const {};
            final ss = _statusStyle['${d['status']}'] ?? (const Color(0xFF64748B), Icons.help_rounded);
            final wos = ((d['workorders'] as List?) ?? const []).cast<Map>();
            return Container(
              decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
              clipBehavior: Clip.antiAlias,
              child: ListView(controller: sc, padding: EdgeInsets.zero, children: [
                CustomPaint(
                  painter: const BrandPattern(opacity: 0.07),
                  child: Container(
                    padding: const EdgeInsets.fromLTRB(20, 14, 20, 16),
                    decoration: BoxDecoration(gradient: LinearGradient(
                        colors: [_accent, Color.lerp(_accent, Colors.black, 0.3)!], begin: Alignment.topRight, end: Alignment.bottomLeft)),
                    child: Row(children: [
                      Container(
                        width: 48, height: 48, alignment: Alignment.center,
                        decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(13)),
                        child: Icon(_catIcons['${d['category']}'] ?? Icons.category_rounded, color: Colors.white, size: 26),
                      ),
                      const SizedBox(width: 12),
                      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(name, style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
                        if (d['code'] != null) Text('${d['code']}', style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 12)),
                      ])),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
                        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
                        child: Row(mainAxisSize: MainAxisSize.min, children: [
                          Icon(ss.$2, size: 12, color: ss.$1),
                          const SizedBox(width: 4),
                          Text('${d['status_label'] ?? ''}', style: TextStyle(color: ss.$1, fontSize: 10.5, fontWeight: FontWeight.w900)),
                        ]),
                      ),
                    ]),
                  ),
                ),
                if (snap.connectionState == ConnectionState.waiting)
                  const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator(color: _accent)))
                else Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    // print QR label CTA
                    SizedBox(width: double.infinity, child: OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(foregroundColor: _accent, side: const BorderSide(color: _accent),
                          padding: const EdgeInsets.symmetric(vertical: 12), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                      onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
                        title: tr('ملصق الأصل (QR)', 'Asset label (QR)'),
                        path: '/cafm/asset/$id/label', fileName: 'asset-label-$id.pdf'))),
                      icon: const Icon(Icons.qr_code_2_rounded, size: 18),
                      label: Text(tr('طباعة ملصق QR', 'Print QR label'), style: const TextStyle(fontWeight: FontWeight.w800)),
                    )),
                    const SizedBox(height: 14),
                    _card(Column(children: [
                      _kv(tr('الفئة', 'Category'), d['category_label']),
                      _kv(tr('الملكية', 'Ownership'), d['ownership']),
                      _kv(tr('المرفق', 'Facility'), d['facility']),
                      _kv(tr('المبنى', 'Building'), d['building']),
                      _kv(tr('الموقع', 'Location'), d['location']),
                      _kv(tr('الماركة', 'Brand'), d['brand']),
                      _kv(tr('الموديل', 'Model'), d['model']),
                      _kv(tr('الرقم التسلسلي', 'Serial'), d['serial']),
                      _kv(tr('الباركود', 'Barcode'), d['barcode']),
                    ])),
                    const SizedBox(height: 12),
                    _card(Column(children: [
                      _kv(tr('تاريخ التركيب', 'Installed'), d['install_date']),
                      _kv(tr('انتهاء الضمان', 'Warranty end'), d['warranty_end']),
                      _kv(tr('آخر فحص', 'Last inspection'), d['last_inspection']),
                      _kv(tr('الفحص القادم', 'Next inspection'), d['next_inspection']),
                      _kv(tr('آخر جرد', 'Last audit'), d['last_audit']),
                    ])),
                    if (d['notes'] != null && '${d['notes']}'.trim().isNotEmpty) ...[
                      const SizedBox(height: 12),
                      _card(Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text(tr('ملاحظات', 'Notes'), style: const TextStyle(fontWeight: FontWeight.w900, color: _navy, fontSize: 13)),
                        const SizedBox(height: 4),
                        Text('${d['notes']}', style: TextStyle(fontSize: 12.5, height: 1.5, color: Colors.grey.shade700)),
                      ])),
                    ],
                    if (wos.isNotEmpty) ...[
                      const SizedBox(height: 14),
                      Row(children: [
                        const Icon(Icons.assignment_rounded, size: 16, color: _accent),
                        const SizedBox(width: 6),
                        Text(tr('أوامر العمل (${wos.length})', 'Work orders (${wos.length})'),
                            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
                      ]),
                      const SizedBox(height: 8),
                      ...wos.map((w) => Container(
                            margin: const EdgeInsets.only(bottom: 6),
                            padding: const EdgeInsets.all(11),
                            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
                            child: Row(children: [
                              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                Text('${w['title'] ?? w['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
                                Text('${w['name']} · ${w['date'] ?? ''}', style: TextStyle(fontSize: 10.5, color: Colors.grey.shade500)),
                              ])),
                              Text('${w['state']}', style: TextStyle(fontSize: 10, color: Colors.grey.shade600, fontWeight: FontWeight.w700)),
                            ]),
                          )),
                    ],
                    const SizedBox(height: 8),
                  ]),
                ),
              ]),
            );
          },
        ),
      ),
    );
  }

  Widget _card(Widget child) => Container(
        width: double.infinity, padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
        child: child,
      );

  Widget _kv(String k, dynamic v) {
    if (v == null || '$v'.trim().isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 9),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        SizedBox(width: 120, child: Text(k, style: TextStyle(fontSize: 12, color: Colors.grey.shade600, fontWeight: FontWeight.w600))),
        Expanded(child: Text('$v', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: _navy))),
      ]),
    );
  }
}
