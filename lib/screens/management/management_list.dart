import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'management_home.dart' show Mgmt;
import '../pms/pms_employee_file.dart';
import '../pdf_report_screen.dart';
import '../excel_export.dart';
import '../media_viewer_screen.dart';
import 'management_analytics.dart';

/// Parse a `#RRGGBB` string into a Color (falls back to slate).
Color mgmtHex(String? hex, [Color fallback = Mgmt.slate]) {
  if (hex == null || hex.isEmpty) return fallback;
  var h = hex.replaceAll('#', '').trim();
  if (h.length == 6) h = 'FF$h';
  final v = int.tryParse(h, radix: 16);
  return v == null ? fallback : Color(v);
}

/// A professional, state-coloured status chip used across list & detail.
/// Reads `state` (label) + `state_color` (#hex) from the record map.
Widget mgmtStateChip(Map src, {double fontSize = 10}) {
  final label = '${src['state'] ?? ''}';
  if (label.isEmpty) return const SizedBox.shrink();
  final c = mgmtHex('${src['state_color'] ?? ''}');
  return Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
    decoration: BoxDecoration(
        color: c.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: c.withValues(alpha: 0.34))),
    child: Row(mainAxisSize: MainAxisSize.min, children: [
      Container(width: 6, height: 6, decoration: BoxDecoration(color: c, shape: BoxShape.circle)),
      const SizedBox(width: 5),
      Text(label, style: TextStyle(color: c, fontSize: fontSize, fontWeight: FontWeight.w800)),
    ]),
  );
}

/// Native list for one management system (purchases, tenders, employees, …).
/// The server returns only rows this user may read.
class ManagementListScreen extends StatefulWidget {
  const ManagementListScreen({
    super.key, required this.appKey, required this.title, required this.icon, required this.accent,
    this.initialFilters});
  final String appKey, title, icon;
  final Color accent;
  final Map<String, String>? initialFilters;

  @override
  State<ManagementListScreen> createState() => _ManagementListScreenState();
}

class _ManagementListScreenState extends State<ManagementListScreen> {
  late Future<Map<String, dynamic>> _f;
  final _search = TextEditingController();
  Timer? _debounce;
  String _q = '';
  Map<String, dynamic>? _last;
  final Map<String, String> _filters = {}; // dept / etype / emp_status / state
  Map<String, dynamic> _empBadges = {}; // per-key {count,pending} for the emp row
  bool _docGrid = false; // documents (files): grid vs list view

  bool get _isProposals => widget.appKey == 'proposals';
  bool get _isEmployees => widget.appKey == 'employees';

  @override
  void initState() {
    super.initState();
    if (widget.initialFilters != null) _filters.addAll(widget.initialFilters!);
    _reload();
    if (_isEmployees) _loadEmpBadges();
  }

  Future<void> _loadEmpBadges() async {
    try {
      final b = await context.read<AuthProvider>().api.managementEmpModules();
      if (mounted) setState(() => _empBadges = b);
    } catch (_) {/* badges are optional */}
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _search.dispose();
    super.dispose();
  }

  void _reload() {
    final fut = context.read<AuthProvider>().api
        .managementList(widget.appKey, q: _q, filters: _filters.isEmpty ? null : _filters);
    fut.then((d) { if (mounted) setState(() => _last = d); }).catchError((_) {});
    setState(() => _f = fut);
  }

  void _setFilter(String key, String? value) {
    setState(() {
      if (value == null) {
        _filters.remove(key);
      } else {
        _filters[key] = value;
      }
    });
    _reload();
  }

  Future<void> _export() async {
    final q = _q.isEmpty ? '' : '&q=${Uri.encodeQueryComponent(_q)}';
    await exportExcelFile(context,
        path: '/management/${widget.appKey}/export?lang=$gLang$q',
        fileName: '${widget.appKey}.xlsx');
  }

  void _onSearch(String v) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 420), () {
      if (!mounted) return;
      _q = v.trim();
      _reload();
    });
  }

  Widget _stateFilterBar() {
    final states = ((_last?['state_filters'] as List?) ?? const []).cast<Map>();
    final sel = _filters['state'];
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(children: [
          Padding(
            padding: const EdgeInsets.only(right: 6),
            child: ChoiceChip(
              label: Text(tr('الكل', 'All'), style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
              selected: sel == null,
              selectedColor: widget.accent.withValues(alpha: 0.15),
              onSelected: (_) => _setFilter('state', null),
            ),
          ),
          for (final s in states)
            Padding(
              padding: const EdgeInsets.only(right: 6),
              child: ChoiceChip(
                label: Text('${s['l']}', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
                selected: sel == '${s['v']}',
                selectedColor: widget.accent.withValues(alpha: 0.15),
                onSelected: (_) => _setFilter('state', sel == '${s['v']}' ? null : '${s['v']}'),
              ),
            ),
        ]),
      ),
    );
  }

  // Horizontal row of employee sub-module icons + a full-stats shortcut.
  static const List<(String, String, String, String, int)> _empModules = [
    ('attendance', '⏱️', 'الحضور', 'Attendance', 0xFF2563EB),
    ('leaves', '🌴', 'الإجازات', 'Leaves', 0xFF0891B2),
    ('hr_allowances', '💵', 'البدلات', 'Allowances', 0xFF0D9488),
    ('hr_loans', '💰', 'السُّلف', 'Loans', 0xFF7C3AED),
    ('hr_bonuses', '🎁', 'المكافآت', 'Bonuses', 0xFFF59E0B),
    ('hr_penalties', '⚠️', 'الجزاءات', 'Penalties', 0xFFE5484D),
    ('hr_eos', '🏁', 'إنهاء الخدمة', 'End of service', 0xFFB91C1C),
    ('hr_permissions', '🕒', 'الاستئذانات', 'Permissions', 0xFF6D28D9),
    ('hr_custody', '🧰', 'العهد', 'Custody', 0xFF9A3412),
    ('passports', '🛂', 'الجوازات', 'Passports', 0xFF0369A1),
    ('recruitment', '🧑‍💼', 'التوظيف', 'Recruitment', 0xFF7C3AED),
    ('documents', '📁', 'المستندات', 'Documents', 0xFF475569),
    ('correspondence', '✉️', 'المراسلات', 'Letters', 0xFF8B5CF6),
  ];

  Widget _employeeModulesRow() {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(8, 0, 8, 10),
      child: SizedBox(
        height: 76,
        child: ListView(
          scrollDirection: Axis.horizontal,
          children: [
            _empModTile('__stats', '📈', tr('الإحصائيات', 'Analytics'), Mgmt.red, isStats: true),
            for (final m in _empModules)
              _empModTile(m.$1, m.$2, gLang == 'en' ? m.$4 : m.$3, Color(m.$5)),
          ],
        ),
      ),
    );
  }

  Widget _empModTile(String key, String icon, String label, Color c, {bool isStats = false}) => SizedBox(
        width: 72,
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: () {
              if (isStats) {
                Navigator.push(context, MaterialPageRoute(builder: (_) => const ManagementAnalyticsScreen()));
              } else {
                final m = _empModules.firstWhere((e) => e.$1 == key);
                Navigator.push(context, MaterialPageRoute(builder: (_) => ManagementListScreen(
                    appKey: key, title: gLang == 'en' ? m.$4 : m.$3, icon: icon, accent: c)));
              }
            },
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 6, horizontal: 2),
              child: Column(mainAxisSize: MainAxisSize.min, children: [
                Stack(clipBehavior: Clip.none, children: [
                  Container(
                    width: 42, height: 42, alignment: Alignment.center,
                    decoration: BoxDecoration(
                        color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(13),
                        border: Border.all(color: c.withValues(alpha: 0.2))),
                    child: Text(icon, style: const TextStyle(fontSize: 20)),
                  ),
                  if (!isStats && (((_empBadges[key] as Map?)?['pending'] ?? 0) as int) > 0)
                    Positioned(right: -6, top: -6, child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                      constraints: const BoxConstraints(minWidth: 17),
                      decoration: BoxDecoration(color: const Color(0xFFDC2626), borderRadius: BorderRadius.circular(9),
                          border: Border.all(color: Colors.white, width: 1.4)),
                      child: Text('${((_empBadges[key] as Map)['pending'])}', textAlign: TextAlign.center,
                          style: const TextStyle(color: Colors.white, fontSize: 9.5, fontWeight: FontWeight.w900)),
                    )),
                ]),
                const SizedBox(height: 4),
                Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
                    style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700, color: isStats ? Mgmt.red : Mgmt.ink)),
              ]),
            ),
          ),
        ),
      );

  Widget _attFilterBar() {
    final depts = (((_last?['filters'] as Map?)?['departments'] as List?) ?? const []).cast<Map>();
    String? deptLabel() {
      final id = _filters['dept'];
      if (id == null) return null;
      final m = depts.where((d) => '${d['v']}' == id);
      return m.isEmpty ? null : '${m.first['l']}';
    }
    final period = _filters['period'];
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(children: [
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: Material(
              color: _filters['dept'] != null ? widget.accent.withValues(alpha: 0.12) : Mgmt.bg,
              borderRadius: BorderRadius.circular(20),
              child: InkWell(
                borderRadius: BorderRadius.circular(20),
                onTap: () async {
                  final opts = depts.map((d) => {'v': d['v'], 'l': d['l']}).toList().cast<Map>();
                  final chosen = await showModalBottomSheet<int>(
                    context: context, isScrollControlled: true, backgroundColor: Colors.white,
                    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
                    builder: (_) => _PickerSheet(title: tr('اختر القسم', 'Select department'), options: opts, accent: widget.accent),
                  );
                  if (chosen != null) _setFilter('dept', '$chosen');
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                  decoration: BoxDecoration(borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: _filters['dept'] != null ? widget.accent.withValues(alpha: 0.4) : Colors.black12)),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Text(deptLabel() ?? tr('القسم', 'Department'), style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: _filters['dept'] != null ? widget.accent : Mgmt.slate)),
                    if (_filters['dept'] != null) ...[const SizedBox(width: 4), InkWell(onTap: () => _setFilter('dept', null), child: Icon(Icons.close_rounded, size: 14, color: widget.accent))]
                    else Icon(Icons.expand_more_rounded, size: 15, color: _filters['dept'] != null ? widget.accent : Mgmt.slate),
                  ]),
                ),
              ),
            ),
          ),
          for (final t in [
            {'v': 'today', 'l': tr('اليوم', 'Today')},
            {'v': 'week', 'l': tr('الأسبوع', 'Week')},
            {'v': 'month', 'l': tr('الشهر', 'Month')},
          ])
            Padding(
              padding: const EdgeInsets.only(right: 6),
              child: ChoiceChip(
                label: Text('${t['l']}', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
                selected: period == t['v'],
                selectedColor: widget.accent.withValues(alpha: 0.15),
                onSelected: (_) => _setFilter('period', period == t['v'] ? null : '${t['v']}'),
              ),
            ),
          Padding(
            padding: const EdgeInsets.only(right: 6),
            child: ChoiceChip(
              label: Text('🟢 ${tr('مفتوح', 'Open')}', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
              selected: _filters['open'] == '1',
              selectedColor: const Color(0xFF16A34A).withValues(alpha: 0.15),
              onSelected: (_) => _setFilter('open', _filters['open'] == '1' ? null : '1'),
            ),
          ),
        ]),
      ),
    );
  }

  Widget _docFilterBar() {
    final folders = (((_last?['filters'] as Map?)?['folders'] as List?) ?? const []).cast<Map>();
    String? folderLabel() {
      final id = _filters['folder'];
      if (id == null) return null;
      final m = folders.where((f) => '${f['v']}' == id);
      return m.isEmpty ? null : '${m.first['l']}';
    }
    final ftype = _filters['ftype'];
    Widget chip(String label, bool active, VoidCallback onTap, {VoidCallback? onClear}) => Padding(
          padding: const EdgeInsets.only(right: 8),
          child: Material(
            color: active ? widget.accent.withValues(alpha: 0.12) : Mgmt.bg,
            borderRadius: BorderRadius.circular(20),
            child: InkWell(
              borderRadius: BorderRadius.circular(20), onTap: onTap,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                decoration: BoxDecoration(borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: active ? widget.accent.withValues(alpha: 0.4) : Colors.black12)),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Text(label, style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: active ? widget.accent : Mgmt.slate)),
                  if (active && onClear != null) ...[const SizedBox(width: 4), InkWell(onTap: onClear, child: Icon(Icons.close_rounded, size: 14, color: widget.accent))]
                  else Icon(Icons.expand_more_rounded, size: 15, color: active ? widget.accent : Mgmt.slate),
                ]),
              ),
            ),
          ),
        );
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(children: [
          chip(folderLabel() ?? tr('المجلّد', 'Folder'), _filters['folder'] != null, () async {
            final opts = folders.map((f) => {'v': f['v'], 'l': f['l']}).toList().cast<Map>();
            final chosen = await showModalBottomSheet<int>(
              context: context, isScrollControlled: true, backgroundColor: Colors.white,
              shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
              builder: (_) => _PickerSheet(title: tr('اختر المجلّد', 'Select folder'), options: opts, accent: widget.accent),
            );
            if (chosen != null) _setFilter('folder', '$chosen');
          }, onClear: () => _setFilter('folder', null)),
          for (final t in [
            {'v': 'image', 'l': '🖼️ ${tr('صور', 'Images')}'},
            {'v': 'pdf', 'l': '📕 PDF'},
          ])
            Padding(
              padding: const EdgeInsets.only(right: 6),
              child: ChoiceChip(
                label: Text('${t['l']}', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
                selected: ftype == t['v'],
                selectedColor: widget.accent.withValues(alpha: 0.15),
                onSelected: (_) => _setFilter('ftype', ftype == t['v'] ? null : '${t['v']}'),
              ),
            ),
        ]),
      ),
    );
  }

  Widget _employeeFilterBar() {
    final flt = (_last?['filters'] as Map?) ?? const {};
    final depts = ((flt['departments'] as List?) ?? const []).cast<Map>();
    final types = ((flt['types'] as List?) ?? const []).cast<Map>();
    String? deptLabel() {
      final id = _filters['dept'];
      if (id == null) return null;
      final m = depts.where((d) => '${d['v']}' == id);
      return m.isEmpty ? null : '${m.first['l']}';
    }
    String? typeLabel() {
      final v = _filters['etype'];
      if (v == null) return null;
      final m = types.where((t) => '${t['v']}' == v);
      return m.isEmpty ? null : '${m.first['l']}';
    }
    final status = _filters['emp_status'] ?? 'active';
    Widget chip(String label, bool active, VoidCallback onTap, {VoidCallback? onClear}) => Padding(
          padding: const EdgeInsets.only(right: 8),
          child: Material(
            color: active ? widget.accent.withValues(alpha: 0.12) : Mgmt.bg,
            borderRadius: BorderRadius.circular(20),
            child: InkWell(
              borderRadius: BorderRadius.circular(20),
              onTap: onTap,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: active ? widget.accent.withValues(alpha: 0.4) : Colors.black12)),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Text(label, style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: active ? widget.accent : Mgmt.slate)),
                  if (active && onClear != null) ...[
                    const SizedBox(width: 4),
                    InkWell(onTap: onClear, child: Icon(Icons.close_rounded, size: 14, color: widget.accent)),
                  ] else
                    Icon(Icons.expand_more_rounded, size: 15, color: active ? widget.accent : Mgmt.slate),
                ]),
              ),
            ),
          ),
        );
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(children: [
          chip(deptLabel() ?? tr('القسم', 'Department'), _filters['dept'] != null,
              () async {
                final opts = depts.map((d) => {'v': d['v'], 'l': d['l']}).toList().cast<Map>();
                final chosen = await showModalBottomSheet<int>(
                  context: context, isScrollControlled: true, backgroundColor: Colors.white,
                  shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
                  builder: (_) => _PickerSheet(title: tr('اختر القسم', 'Select department'), options: opts, accent: widget.accent),
                );
                if (chosen != null) _setFilter('dept', '$chosen');
              },
              onClear: () => _setFilter('dept', null)),
          chip(typeLabel() ?? tr('نوع التوظيف', 'Type'), _filters['etype'] != null,
              () async {
                final chosen = await showModalBottomSheet<String>(
                  context: context, backgroundColor: Colors.white,
                  shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
                  builder: (_) => SafeArea(child: Column(mainAxisSize: MainAxisSize.min, children: [
                    for (final t in types)
                      ListTile(title: Text('${t['l']}'), onTap: () => Navigator.pop(context, '${t['v']}')),
                  ])),
                );
                if (chosen != null) _setFilter('etype', chosen);
              },
              onClear: () => _setFilter('etype', null)),
          // status segmented (active / archived / all)
          for (final s in [
            {'v': 'active', 'l': tr('نشطون', 'Active')},
            {'v': 'archived', 'l': tr('مؤرشفون', 'Archived')},
            {'v': 'all', 'l': tr('الكل', 'All')},
          ])
            Padding(
              padding: const EdgeInsets.only(right: 6),
              child: ChoiceChip(
                label: Text('${s['l']}', style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
                selected: status == s['v'],
                selectedColor: widget.accent.withValues(alpha: 0.15),
                onSelected: (_) => _setFilter('emp_status', s['v'] == 'active' ? null : '${s['v']}'),
              ),
            ),
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Mgmt.bg,
      appBar: AppBar(
        backgroundColor: widget.accent, foregroundColor: Colors.white, elevation: 0,
        title: Row(children: [
          Text('${widget.icon} '),
          Expanded(child: Text(widget.title, overflow: TextOverflow.ellipsis)),
        ]),
        actions: [
          // Documents: toggle list / grid (grid shows thumbnails).
          if (widget.appKey == 'files')
            IconButton(
              tooltip: _docGrid ? tr('عرض قائمة', 'List view') : tr('عرض شبكي', 'Grid view'),
              icon: Icon(_docGrid ? Icons.view_list_rounded : Icons.grid_view_rounded),
              onPressed: () => setState(() => _docGrid = !_docGrid)),
          // Create lives at the TOP as a professional pill (not a bottom FAB).
          if (_last?['can_create'] == true)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
              child: Material(
                color: Colors.white.withValues(alpha: 0.20),
                borderRadius: BorderRadius.circular(20),
                child: InkWell(
                  borderRadius: BorderRadius.circular(20),
                  onTap: _onCreate,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      const Icon(Icons.add_rounded, size: 18, color: Colors.white),
                      const SizedBox(width: 4),
                      Text(_fabLabel(), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 12.5)),
                    ]),
                  ),
                ),
              ),
            ),
          // Biometric devices live inside the Attendance icon.
          if (widget.appKey == 'attendance')
            IconButton(
              tooltip: tr('أجهزة البصمة', 'Biometric devices'),
              icon: const Icon(Icons.fingerprint_rounded),
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ManagementListScreen(
                  appKey: 'bio_devices', title: tr('أجهزة البصمة', 'Biometric devices'), icon: '🔌', accent: const Color(0xFF6D28D9))))),
          // Only surface Export when there is actually something to export.
          if (((_last?['items'] as List?)?.isNotEmpty ?? false))
            IconButton(
              tooltip: tr('تصدير Excel', 'Export to Excel'),
              icon: const Icon(Icons.file_download_outlined),
              onPressed: _export),
        ],
      ),
      body: Column(children: [
        Container(
          color: Colors.white,
          padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
          child: TextField(
            controller: _search,
            onChanged: _onSearch,
            decoration: InputDecoration(
              hintText: tr('ابحث…', 'Search…'),
              prefixIcon: const Icon(Icons.search_rounded, size: 20),
              suffixIcon: _search.text.isEmpty ? null : IconButton(
                icon: const Icon(Icons.close_rounded, size: 18),
                onPressed: () { _search.clear(); _q = ''; _reload(); }),
              filled: true, fillColor: Mgmt.bg, isDense: true,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            ),
          ),
        ),
        if (_isEmployees) _employeeFilterBar(),
        if (_isEmployees) _employeeModulesRow(),
        if (widget.appKey == 'attendance') _attFilterBar(),
        if (widget.appKey == 'files') _docFilterBar(),
        if ((_last?['state_filters'] as List?)?.isNotEmpty == true) _stateFilterBar(),
        Expanded(
          child: RefreshIndicator(
            onRefresh: () async => _reload(),
            child: FutureBuilder<Map<String, dynamic>>(
              future: _f,
              builder: (_, snap) {
                if (snap.hasError) {
                  return ListView(children: [Padding(
                    padding: const EdgeInsets.all(40),
                    child: Center(child: Text('${snap.error}',
                        textAlign: TextAlign.center, style: const TextStyle(color: Mgmt.slate))))]);
                }
                if (!snap.hasData) return const Center(child: CircularProgressIndicator());
                final rows = (snap.data!['rows'] as List?) ?? [];
                final total = snap.data!['count'] ?? 0;
                if (rows.isEmpty) {
                  return ListView(children: [Padding(
                    padding: const EdgeInsets.only(top: 90),
                    child: Center(child: Text(tr('لا سجلات', 'No records'),
                        style: const TextStyle(color: Mgmt.slate, fontWeight: FontWeight.w700))))]);
                }
                final stats = (snap.data!['stats'] as List?) ?? const [];
                final currency = '${snap.data!['currency'] ?? ''}';
                // Documents grid view — thumbnail tiles.
                if (widget.appKey == 'files' && _docGrid) {
                  return GridView.builder(
                    padding: const EdgeInsets.fromLTRB(12, 10, 12, 90),
                    gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 3, childAspectRatio: 0.78, crossAxisSpacing: 8, mainAxisSpacing: 8),
                    itemCount: rows.length,
                    itemBuilder: (_, i) => _docGridTile(rows[i] as Map),
                  );
                }
                return ListView.separated(
                  padding: const EdgeInsets.fromLTRB(12, 8, 12, 90),
                  itemCount: rows.length + 1,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (_, i) {
                    if (i == 0) {
                      return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        if (stats.isNotEmpty) _statsHeader(stats.cast<Map>()),
                        Padding(
                          padding: const EdgeInsets.only(bottom: 4, top: 2),
                          child: Text(
                              tr('عرض ${rows.length} من $total', 'Showing ${rows.length} of $total'),
                              style: const TextStyle(color: Mgmt.slate, fontSize: 11.5, fontWeight: FontWeight.w700)),
                        ),
                      ]);
                    }
                    final r = rows[i - 1] as Map;
                    if (_isProposals) return _proposalCard(r, currency);
                    if (widget.appKey == 'tenders') return _tenderCard(r, currency);
                    if (widget.appKey == 'employees') return _employeeCard(r);
                    if (widget.appKey == 'leaves') return _leaveCard(r);
                    if (widget.appKey == 'crm') return _crmCard(r, currency);
                    if (r['ord'] != null) return _orderCard(r, currency);
                    if (r['exp'] != null) return _expenseCard(r);
                    if (r['fl'] != null) return _fleetCard(r);
                    if (r['xp'] != null) return _experienceCard(r);
                    if (r['vs'] != null) return _vsCard(r);
                    if (r['lt'] != null) return _letterCard(r);
                    if (r['ri'] != null) return _reqinvCard(r);
                    if (r['doc'] != null) return _docCard(r);
                    if (r['att'] != null) return _attCard(r);
                    if (r['dev'] != null) return _devCard(r);
                    if (r['appr'] != null) return _apprCard(r);
                    if (r['lg'] != null) return _legalCard(r);
                    if (r['pt'] != null) return _petrolCard(r);
                    if (r['pp'] != null) return _passportCard(r);
                    return _row(r);
                  },
                );
              },
            ),
          ),
        ),
      ]),
    );
  }

  Widget _row(Map r) => Material(
        color: Colors.white, borderRadius: BorderRadius.circular(14),
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
          child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
            child: Row(children: [
              if ('${r['logo_b64'] ?? ''}'.isNotEmpty)
                _logoBox('${r['logo_b64']}', '${r['title']}', size: 40)
              else if (r['image'] != null)
                ClipRRect(borderRadius: BorderRadius.circular(10),
                    child: Image.network('${context.read<AuthProvider>().api.baseUrl.replaceAll('/api/v1', '')}${r['image']}',
                        width: 40, height: 40, fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => _avatar(r)))
              else _avatar(r),
              const SizedBox(width: 11),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${r['title']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5, color: Mgmt.ink, height: 1.25)),
                if (r['subtitle'] != null) Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text('${r['subtitle']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Mgmt.slate, fontSize: 11.5)),
                ),
                if (r['date'] != null) Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text('${r['date']}'.split(' ').first,
                      style: const TextStyle(color: Mgmt.slate, fontSize: 10.5)),
                ),
              ])),
              Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                if (r['amount'] != null)
                  Text('${r['amount']}', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: widget.accent)),
                if (r['state'] != null) Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: mgmtStateChip(r),
                ),
              ]),
            ]),
          ),
        ),
      );

  // ---- Proposals: KPI header + rich per-record cards --------------------
  Widget _statsHeader(List<Map> stats) {
    String fmt(Map s) {
      final v = s['value'];
      final unit = '${s['unit'] ?? ''}';
      final txt = (s['money'] == true && v is num)
          ? v.toStringAsFixed(3)
          : '$v';
      return unit.isEmpty ? txt : '$txt$unit';
    }
    return SizedBox(
      height: 78,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(vertical: 6),
        itemCount: stats.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (_, i) {
          final s = stats[i];
          final c = mgmtHex('${s['color'] ?? ''}', widget.accent);
          return Container(
            width: 122,
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: c.withValues(alpha: 0.22))),
            child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Row(children: [
                    Text('${s['icon'] ?? ''} ', style: const TextStyle(fontSize: 12)),
                    Expanded(
                      child: Text(gLang == 'en' ? '${s['en']}' : '${s['ar']}',
                          maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: Mgmt.slate, fontSize: 10, fontWeight: FontWeight.w700)),
                    ),
                  ]),
                  const SizedBox(height: 5),
                  Text(fmt(s),
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 16.5)),
                ]),
          );
        },
      ),
    );
  }

  Widget _miniStat(String icon, String label, String value, Color c) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('$icon $label', style: const TextStyle(color: Mgmt.slate, fontSize: 9.5, fontWeight: FontWeight.w700)),
          const SizedBox(height: 1),
          Text(value, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 12.5)),
        ],
      );

  Widget _proposalCard(Map r, String currency) {
    final pr = (r['pr'] as Map?) ?? const {};
    final cur = currency.isEmpty ? '' : ' $currency';
    final margin = (pr['margin_pct'] as num?)?.toDouble() ?? 0;
    final marginColor = margin >= 20
        ? const Color(0xFF16A34A)
        : (margin >= 10 ? const Color(0xFFF59E0B) : Mgmt.red);
    final validityColor = mgmtHex('${pr['validity_color'] ?? ''}', Mgmt.slate);
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.fromLTRB(13, 12, 13, 11),
          decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.black12)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            // top row: ref + customer + state
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    if ('${pr['ref'] ?? ''}'.isNotEmpty)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                        margin: const EdgeInsetsDirectional.only(end: 6),
                        decoration: BoxDecoration(
                            color: widget.accent.withValues(alpha: 0.10),
                            borderRadius: BorderRadius.circular(7)),
                        child: Text('${pr['ref']}',
                            style: TextStyle(color: widget.accent, fontWeight: FontWeight.w900, fontSize: 10.5)),
                      ),
                    if (pr['service_type'] != null)
                      Expanded(
                        child: Text('${pr['service_type']}',
                            maxLines: 1, overflow: TextOverflow.ellipsis,
                            style: const TextStyle(color: Mgmt.ink, fontWeight: FontWeight.w800, fontSize: 12)),
                      ),
                  ]),
                  const SizedBox(height: 3),
                  Text('${pr['customer'] ?? r['subtitle'] ?? '—'}',
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Mgmt.slate, fontSize: 11.5, fontWeight: FontWeight.w600)),
                ]),
              ),
              mgmtStateChip(r),
            ]),
            const Divider(height: 16),
            // money row: cost · sale · profit%
            Row(children: [
              Expanded(child: _miniStat('💵', tr('التكلفة', 'Cost'),
                  '${(pr['cost'] as num?)?.toStringAsFixed(3) ?? '0'}$cur', Mgmt.ink)),
              Expanded(child: _miniStat('🏷️', tr('البيع', 'Sale'),
                  '${(pr['sale'] as num?)?.toStringAsFixed(3) ?? '0'}$cur', widget.accent)),
              Expanded(child: _miniStat('📈', tr('الربح', 'Profit'),
                  '${(pr['profit'] as num?)?.toStringAsFixed(3) ?? '0'}$cur  ·  ${margin.toStringAsFixed(1)}%', marginColor)),
            ]),
            const SizedBox(height: 9),
            // footer chips: manpower · services · validity · date
            Wrap(spacing: 6, runSpacing: 6, children: [
              if ((pr['manpower'] as num?) != null && (pr['manpower'] as num) > 0)
                _tag('👷 ${pr['manpower']}', Mgmt.slate),
              if ((pr['services'] as num?) != null && (pr['services'] as num) > 0)
                _tag('🧾 ${pr['services']}', Mgmt.slate),
              if ('${pr['validity_ar'] ?? ''}'.isNotEmpty && '${pr['validity']}' != 'none')
                _tag(gLang == 'en' ? '${pr['validity_en']}' : '${pr['validity_ar']}', validityColor),
              if (r['date'] != null)
                _tag('📅 ${'${r['date']}'.split(' ').first}', Mgmt.slate),
            ]),
          ]),
        ),
      ),
    );
  }

  Widget _tag(String text, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
            color: c.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(8)),
        child: Text(text, style: TextStyle(color: c, fontSize: 10, fontWeight: FontWeight.w700)),
      );

  Future<void> _createProposal() async {
    final created = await showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _ProposalCreateSheet(accent: widget.accent),
    );
    if (created == null || !mounted) return;
    _reload();
    // open the fresh quotation straight away
    await _openDetail(created['id'] as int, '${created['title'] ?? ''}');
  }

  Future<void> _createCrm() async {
    final created = await showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _CrmCreateSheet(accent: widget.accent),
    );
    if (created == null || !mounted) return;
    _reload();
    await _openDetail(created['id'] as int, '${created['title'] ?? ''}');
  }

  Future<void> _createPo() async {
    final created = await showModalBottomSheet<Map<String, dynamic>>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _PoFormSheet(accent: widget.accent),
    );
    if (created == null || !mounted) return;
    _reload();
    await _openDetail(created['id'] as int, '${created['title'] ?? ''}');
  }

  String _fabLabel() {
    if (_isProposals) return tr('عرض سعر جديد', 'New quotation');
    if (widget.appKey == 'purchases') return tr('أمر شراء جديد', 'New purchase');
    if (widget.appKey == 'crm') return tr('فرصة جديدة', 'New opportunity');
    return tr('إضافة جديد', 'Add new');
  }

  void _onCreate() {
    if (_isProposals) {
      _createProposal();
    } else if (widget.appKey == 'purchases') {
      _createPo();
    } else if (widget.appKey == 'crm') {
      _createCrm();
    } else {
      _createGeneric();
    }
  }

  Future<void> _createGeneric() async {
    final created = await showModalBottomSheet<Map<String, dynamic>>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _GenericCreateSheet(appKey: widget.appKey, accent: widget.accent),
    );
    if (created == null || !mounted) return;
    _reload();
    if (created['id'] != null) await _openDetail(created['id'] as int, '${created['title'] ?? ''}');
  }

  // ---- Tenders: logo + countdown + rich card ----------------------------
  Widget _logoBox(String? b64, String fallbackText, {double size = 46}) {
    Widget fb() => Container(
        width: size, height: size,
        decoration: BoxDecoration(
            color: widget.accent.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(11)),
        alignment: Alignment.center,
        child: Text(fallbackText.trim().isEmpty ? '?' : fallbackText.trim().characters.first,
            style: TextStyle(color: widget.accent, fontWeight: FontWeight.w900, fontSize: size * 0.4)));
    if (b64 == null || b64.isEmpty) return fb();
    return ClipRRect(
      borderRadius: BorderRadius.circular(11),
      child: Image.memory(base64Decode(b64),
          width: size, height: size, fit: BoxFit.cover, gaplessPlayback: true,
          errorBuilder: (_, __, ___) => fb()),
    );
  }

  Widget _tenderCard(Map r, String currency) {
    final tn = (r['tn'] as Map?) ?? const {};
    final cur = '${tn['currency'] ?? currency}';
    final money = cur.isEmpty ? '' : ' $cur';
    final dl = (tn['deadline'] as Map?) ?? const {};
    final dlColor = mgmtHex('${dl['color'] ?? ''}', Mgmt.slate);
    final prob = (tn['win_probability'] as num?)?.toDouble() ?? 0;
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 11),
          decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.black12)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              _logoBox('${tn['logo_b64'] ?? ''}', '${tn['organization'] ?? r['title']}'),
              const SizedBox(width: 11),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${tn['organization'] ?? r['title']}',
                      maxLines: 2, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Mgmt.ink, height: 1.25)),
                  if ('${tn['tender_no'] ?? ''}'.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Text('#️⃣ ${tn['tender_no']}',
                          maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: Mgmt.slate, fontSize: 10.5, fontWeight: FontWeight.w600)),
                    ),
                ]),
              ),
              mgmtStateChip(r),
            ]),
            const Divider(height: 15),
            Row(children: [
              // deadline countdown
              Expanded(
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 7),
                  decoration: BoxDecoration(
                      color: dlColor.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: dlColor.withValues(alpha: 0.30))),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Icon((dl['urgent'] == true) ? Icons.timer_rounded : Icons.event_available_rounded, size: 14, color: dlColor),
                    const SizedBox(width: 5),
                    Flexible(child: Text(gLang == 'en' ? '${dl['en']}' : '${dl['ar']}',
                        maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: TextStyle(color: dlColor, fontSize: 11, fontWeight: FontWeight.w800))),
                  ]),
                ),
              ),
              const SizedBox(width: 8),
              if ((tn['price'] as num?) != null && (tn['price'] as num) > 0)
                Text('${(tn['price'] as num).toStringAsFixed(3)}$money',
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: widget.accent)),
            ]),
            const SizedBox(height: 8),
            Wrap(spacing: 6, runSpacing: 6, children: [
              if (tn['closing_date'] != null)
                _tag('📅 ${'${tn['closing_date']}'.split(' ').first}', Mgmt.slate),
              if ((tn['guarantee'] as num?) != null && (tn['guarantee'] as num) > 0)
                _tag('🛡️ ${(tn['guarantee'] as num).toStringAsFixed(0)}$money', Mgmt.slate),
              if (prob > 0)
                _tag('📈 ${prob.toStringAsFixed(0)}%',
                    prob >= 60 ? const Color(0xFF16A34A) : (prob >= 35 ? const Color(0xFFF59E0B) : Mgmt.slate)),
              if ((tn['care_rank'] as num?) != null && (tn['care_rank'] as num) > 0)
                _tag('🥇 ${tr('ترتيبنا', 'Rank')} ${tn['care_rank']}', widget.accent),
              if (tn['winner'] != null)
                _tag('🏆 ${tn['winner']}', const Color(0xFF16A34A)),
            ]),
          ]),
        ),
      ),
    );
  }

  // ---- Employees: photo + status + attendance ---------------------------
  Widget _employeeCard(Map r) {
    final e = (r['emp'] as Map?) ?? const {};
    final attColor = mgmtHex('${e['attendance_color'] ?? ''}', Mgmt.slate);
    final presColor = mgmtHex('${e['presence_color'] ?? ''}', Mgmt.slate);
    final onDuty = '${e['attendance']}' == 'checked_in';
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Row(children: [
            Stack(children: [
              _logoBox('${e['photo_b64'] ?? ''}', '${r['title']}', size: 48),
              if (onDuty)
                Positioned(
                  right: 0, bottom: 0,
                  child: Container(
                    width: 14, height: 14,
                    decoration: BoxDecoration(
                        color: const Color(0xFF16A34A), shape: BoxShape.circle,
                        border: Border.all(color: Colors.white, width: 2)),
                  ),
                ),
            ]),
            const SizedBox(width: 11),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${r['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5, color: Mgmt.ink)),
                if (e['job'] != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 1),
                    child: Text('${e['job']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Mgmt.slate, fontSize: 11.5, fontWeight: FontWeight.w600)),
                  ),
                if (e['department'] != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 1),
                    child: Text('🏢 ${e['department']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Mgmt.slate, fontSize: 10)),
                  ),
                const SizedBox(height: 5),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  _tag(gLang == 'en' ? '${e['attendance_en']}' : '${e['attendance_ar']}', attColor),
                  _tag(gLang == 'en' ? '${e['presence_en']}' : '${e['presence_ar']}', presColor),
                  if (e['employee_type'] != null) _tag('${e['employee_type']}', Mgmt.slate),
                  if (e['active'] == false) _tag(tr('مؤرشف', 'Archived'), Mgmt.red),
                ]),
              ]),
            ),
            const Icon(Icons.chevron_left_rounded, color: Mgmt.slate),
          ]),
        ),
      ),
    );
  }

  Widget _avatar(Map r) => Container(
        width: 40, height: 40,
        decoration: BoxDecoration(color: widget.accent.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(10)),
        alignment: Alignment.center,
        child: Text('${r['title']}'.trim().isEmpty ? '?' : '${r['title']}'.trim().characters.first,
            style: TextStyle(color: widget.accent, fontWeight: FontWeight.w900)),
      );

  // ---- Orders (sales / purchases / invoices) ----------------------------
  Widget _orderCard(Map r, String currency) {
    final o = (r['ord'] as Map?) ?? const {};
    final cur = '${o['currency'] ?? currency}';
    final money = cur.isEmpty ? '' : ' $cur';
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              _logoBox('${o['logo_b64'] ?? ''}', '${o['partner'] ?? r['title']}', size: 42),
              const SizedBox(width: 10),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${o['partner'] ?? r['title']}',
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Mgmt.ink)),
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text('${r['title']}',
                        maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Mgmt.slate, fontSize: 10.5, fontWeight: FontWeight.w600)),
                  ),
                ]),
              ),
              Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                if ((o['amount'] as num?) != null)
                  Text('${(o['amount'] as num).toStringAsFixed(3)}$money',
                      style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: widget.accent)),
                const SizedBox(height: 4),
                mgmtStateChip(r),
              ]),
            ]),
            const SizedBox(height: 8),
            Wrap(spacing: 6, runSpacing: 6, children: [
              if (r['date'] != null) _tag('📅 ${'${r['date']}'.split(' ').first}', Mgmt.slate),
              if ((o['lines'] as num?) != null && (o['lines'] as num) > 0)
                _tag('🧾 ${o['lines']} ${tr('بند', 'items')}', Mgmt.slate),
              if (o['inv_ar'] != null)
                _tag(gLang == 'en' ? '${o['inv_en']}' : '${o['inv_ar']}', mgmtHex('${o['inv_color']}', Mgmt.slate)),
              if (o['pay_label'] != null)
                _tag('💳 ${o['pay_label']}', mgmtHex('${o['pay_color']}', Mgmt.slate)),
              if (o['salesperson'] != null) _tag('👤 ${o['salesperson']}', Mgmt.slate),
            ]),
          ]),
        ),
      ),
    );
  }

  // ---- Leaves (time off) ------------------------------------------------
  Widget _leaveCard(Map r) {
    final l = (r['lv'] as Map?) ?? const {};
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Row(children: [
            _logoBox('${l['photo_b64'] ?? ''}', '${l['employee'] ?? r['title']}', size: 46),
            const SizedBox(width: 11),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(
                    child: Text('${l['employee'] ?? r['title']}',
                        maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5, color: Mgmt.ink)),
                  ),
                  mgmtStateChip(r),
                ]),
                if (l['leave_type'] != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text('🌴 ${l['leave_type']}',
                        maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Mgmt.slate, fontSize: 11.5, fontWeight: FontWeight.w600)),
                  ),
                const SizedBox(height: 5),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  if ((l['days'] as num?) != null)
                    _tag('⏱️ ${l['days']} ${tr('يوم', 'days')}', widget.accent),
                  if (l['date_from'] != null)
                    _tag('${'${l['date_from']}'.split(' ').first} → ${'${l['date_to'] ?? ''}'.split(' ').first}', Mgmt.slate),
                ]),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  // ---- CRM (opportunities) ----------------------------------------------
  Widget _crmCard(Map r, String currency) {
    final o = (r['crm'] as Map?) ?? const {};
    final cur = '${o['currency'] ?? currency}';
    final money = cur.isEmpty ? '' : ' $cur';
    final prob = (o['probability'] as num?)?.toDouble() ?? 0;
    final stageColor = mgmtHex('${o['stage_color'] ?? ''}', widget.accent);
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Row(children: [
            _logoBox('${o['logo_b64'] ?? ''}', '${o['partner'] ?? r['title']}', size: 46),
            const SizedBox(width: 11),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${r['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Mgmt.ink)),
                if (o['partner'] != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 1),
                    child: Text('🏢 ${o['partner']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Mgmt.slate, fontSize: 11)),
                  ),
                const SizedBox(height: 5),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  if (o['stage'] != null)
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(
                          color: stageColor.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: stageColor.withValues(alpha: 0.34))),
                      child: Text('${o['stage']}', style: TextStyle(color: stageColor, fontSize: 10, fontWeight: FontWeight.w800)),
                    ),
                  if (prob > 0) _tag('📈 ${prob.toStringAsFixed(0)}%',
                      prob >= 70 ? const Color(0xFF16A34A) : (prob >= 40 ? const Color(0xFFF59E0B) : Mgmt.slate)),
                  if (o['salesperson'] != null) _tag('👤 ${o['salesperson']}', Mgmt.slate),
                ]),
              ]),
            ),
            if ((o['expected'] as num?) != null && (o['expected'] as num) > 0)
              Text('${(o['expected'] as num).toStringAsFixed(0)}$money',
                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: widget.accent)),
          ]),
        ),
      ),
    );
  }

  // ---- Employee expenses ------------------------------------------------
  Widget _expenseCard(Map r) {
    final e = (r['exp'] as Map?) ?? const {};
    final cur = '${e['currency'] ?? ''}';
    final money = cur.isEmpty ? '' : ' $cur';
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Row(children: [
            _logoBox('${e['photo_b64'] ?? ''}', '${e['employee'] ?? r['title']}', size: 46),
            const SizedBox(width: 11),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${r['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Mgmt.ink)),
                if (e['employee'] != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 1),
                    child: Text('👤 ${e['employee']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Mgmt.slate, fontSize: 11)),
                  ),
                const SizedBox(height: 5),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  if ((e['lines'] as num?) != null && (e['lines'] as num) > 0)
                    _tag('🧾 ${e['lines']} ${tr('بند', 'items')}', Mgmt.slate),
                  if (e['payment_mode'] != null) _tag('💳 ${e['payment_mode']}', Mgmt.slate),
                ]),
              ]),
            ),
            Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
              if ((e['amount'] as num?) != null)
                Text('${(e['amount'] as num).toStringAsFixed(3)}$money',
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: widget.accent)),
              const SizedBox(height: 4),
              mgmtStateChip(r),
            ]),
          ]),
        ),
      ),
    );
  }

  // ---- Fleet (vehicles) -------------------------------------------------
  Widget _fleetCard(Map r) {
    final v = (r['fl'] as Map?) ?? const {};
    final stColor = mgmtHex('${v['state_color'] ?? ''}', const Color(0xFF16A34A));
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Row(children: [
            SizedBox(
              width: 56, height: 56,
              child: '${v['image_b64'] ?? ''}'.isEmpty
                  ? Container(
                      decoration: BoxDecoration(
                          color: widget.accent.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(11)),
                      child: Icon(Icons.directions_car_rounded, color: widget.accent, size: 26))
                  : ClipRRect(
                      borderRadius: BorderRadius.circular(11),
                      child: Image.memory(base64Decode('${v['image_b64']}'),
                          width: 56, height: 56, fit: BoxFit.cover, gaplessPlayback: true,
                          errorBuilder: (_, __, ___) => Icon(Icons.directions_car_rounded, color: widget.accent, size: 26))),
            ),
            const SizedBox(width: 11),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(
                    child: Text('${v['model'] ?? r['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Mgmt.ink)),
                  ),
                  if (r['state'] != null) mgmtStateChip(r),
                ]),
                if ('${v['plate'] ?? ''}'.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 3),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                      decoration: BoxDecoration(
                          color: Mgmt.ink, borderRadius: BorderRadius.circular(5)),
                      child: Text('🔖 ${v['plate']}',
                          style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w900, letterSpacing: 1)),
                    ),
                  ),
                const SizedBox(height: 5),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  if (v['driver'] != null) _tag('🧑‍✈️ ${v['driver']}', const Color(0xFF16A34A))
                  else _tag(tr('بدون سائق', 'No driver'), Mgmt.slate),
                  if ((v['odometer'] as num?) != null && (v['odometer'] as num) > 0)
                    _tag('🛣️ ${(v['odometer'] as num).toStringAsFixed(0)} ${tr('كم', 'km')}', Mgmt.slate),
                  if (v['fuel'] != null) _tag('⛽ ${v['fuel']}', Mgmt.slate),
                  if (v['year'] != null) _tag('📆 ${v['year']}', Mgmt.slate),
                ]),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  // ---- Correspondence / letters -----------------------------------------
  Widget _letterCard(Map r) {
    final l = (r['lt'] as Map?) ?? const {};
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Row(children: [
            _logoBox('${l['photo_b64'] ?? ''}', '${l['employee'] ?? r['title']}', size: 46),
            const SizedBox(width: 11),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                    margin: const EdgeInsetsDirectional.only(end: 6),
                    decoration: BoxDecoration(color: widget.accent.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(6)),
                    child: Text('✉️ ${r['title']}', style: TextStyle(color: widget.accent, fontWeight: FontWeight.w900, fontSize: 10.5)),
                  ),
                  const Spacer(),
                  mgmtStateChip(r),
                ]),
                const SizedBox(height: 4),
                if (l['employee'] != null)
                  Text('👤 ${l['employee']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.ink)),
                const SizedBox(height: 3),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  if (l['letter_type'] != null) _tag('📄 ${l['letter_type']}', Mgmt.slate),
                  if (l['date'] != null) _tag('📅 ${'${l['date']}'.split(' ').first}', Mgmt.slate),
                ]),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  // ---- Approvals (approval.request) -------------------------------------
  Widget _apprCard(Map r) {
    final a = (r['appr'] as Map?) ?? const {};
    return Material(
      color: Colors.white, borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Row(children: [
            _logoBox('${a['photo_b64'] ?? ''}', '${a['owner'] ?? r['title']}', size: 46),
            const SizedBox(width: 11),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${r['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.ink))),
                  mgmtStateChip(r),
                ]),
                if (a['category'] != null)
                  Padding(padding: const EdgeInsets.only(top: 2),
                      child: Text('📋 ${a['category']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Mgmt.slate, fontSize: 11, fontWeight: FontWeight.w600))),
                const SizedBox(height: 5),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  if (a['owner'] != null) _tag('👤 ${a['owner']}', Mgmt.slate),
                  if ((a['approvers'] as num?) != null && (a['approvers'] as num) > 0) _tag('✍️ ${a['approvers']}', Mgmt.slate),
                  if ((a['amount'] as num?) != null && (a['amount'] as num) > 0) _tag('💰 ${a['amount']}', widget.accent),
                  if (a['date'] != null) _tag('📅 ${'${a['date']}'.split(' ').first}', Mgmt.slate),
                ]),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  // ---- Attendance (hr.attendance) ---------------------------------------
  Widget _attCard(Map r) {
    final a = (r['att'] as Map?) ?? const {};
    final open = a['open'] == true;
    return Material(
      color: Colors.white, borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Row(children: [
            Stack(children: [
              _logoBox('${a['photo_b64'] ?? ''}', '${a['employee'] ?? r['title']}', size: 46),
              if (open)
                Positioned(right: 0, bottom: 0, child: Container(width: 14, height: 14,
                    decoration: BoxDecoration(color: const Color(0xFF16A34A), shape: BoxShape.circle, border: Border.all(color: Colors.white, width: 2)))),
            ]),
            const SizedBox(width: 11),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${a['employee'] ?? r['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Mgmt.ink)),
                if (a['department'] != null)
                  Text('🏢 ${a['department']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Mgmt.slate, fontSize: 10.5)),
                const SizedBox(height: 5),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  if (a['check_in'] != null) _tag('🟢 ${'${a['check_in']}'.split(' ').length > 1 ? '${a['check_in']}'.split(' ')[1] : a['check_in']}', const Color(0xFF16A34A)),
                  if (a['check_out'] != null)
                    _tag('🔴 ${'${a['check_out']}'.split(' ').length > 1 ? '${a['check_out']}'.split(' ')[1] : a['check_out']}', Mgmt.red)
                  else _tag(tr('مفتوح', 'Open'), const Color(0xFF16A34A)),
                  if ((a['hours'] as num?) != null && (a['hours'] as num) > 0) _tag('⏳ ${a['hours']} ${tr('س', 'h')}', widget.accent),
                  if (a['date'] != null) _tag('📅 ${'${a['date']}'.split(' ').first}', Mgmt.slate),
                ]),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  // ---- Biometric devices (attendance.device) ----------------------------
  Widget _devCard(Map r) {
    final v = (r['dev'] as Map?) ?? const {};
    final stalled = v['stalled'] == true;
    final sc = stalled ? Mgmt.red : const Color(0xFF16A34A);
    return Material(
      color: Colors.white, borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Row(children: [
            Container(
              width: 46, height: 46, alignment: Alignment.center,
              decoration: BoxDecoration(color: sc.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)),
              child: Icon(stalled ? Icons.error_rounded : Icons.fingerprint_rounded, color: sc, size: 24),
            ),
            const SizedBox(width: 11),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${v['name'] ?? r['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Mgmt.ink))),
                  mgmtStateChip(r),
                ]),
                const SizedBox(height: 4),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  if (v['ip'] != null) _tag('🌐 ${v['ip']}${v['port'] != null ? ':${v['port']}' : ''}', Mgmt.slate),
                  if (v['location'] != null) _tag('📍 ${v['location']}', Mgmt.slate),
                  _tag(stalled ? tr('⚠️ متوقّف', '⚠️ Stalled') : tr('✅ يعمل', '✅ Online'), sc),
                ]),
              ]),
            ),
            const Icon(Icons.chevron_left_rounded, color: Mgmt.slate),
          ]),
        ),
      ),
    );
  }

  // ---- Documents (documents.document) -----------------------------------
  IconData _fileIcon(Map f) {
    if (f['is_image'] == true) return Icons.image_rounded;
    if (f['is_pdf'] == true) return Icons.picture_as_pdf_rounded;
    if (f['url'] != null) return Icons.link_rounded;
    return Icons.insert_drive_file_rounded;
  }

  Color _fileColor(Map f) {
    if (f['is_image'] == true) return const Color(0xFF0EA5E9);
    if (f['is_pdf'] == true) return Mgmt.red;
    return widget.accent;
  }

  String _fileSize(num? bytes) {
    final b = (bytes ?? 0).toDouble();
    if (b >= 1048576) return '${(b / 1048576).toStringAsFixed(1)} MB';
    if (b >= 1024) return '${(b / 1024).toStringAsFixed(0)} KB';
    return '${b.toStringAsFixed(0)} B';
  }

  Widget _docCard(Map r) {
    final f = (r['doc'] as Map?) ?? const {};
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Row(children: [
            _docThumb(f),
            const SizedBox(width: 11),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${f['name'] ?? r['title']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.ink, height: 1.25)),
                const SizedBox(height: 4),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  if (f['folder'] != null) _tag('📁 ${f['folder']}', Mgmt.slate),
                  if (f['owner'] != null) _tag('👤 ${f['owner']}', Mgmt.slate),
                  if ((f['size'] as num?) != null && (f['size'] as num) > 0) _tag('💾 ${_fileSize(f['size'] as num?)}', Mgmt.slate),
                  if (f['date'] != null) _tag('📅 ${'${f['date']}'.split(' ').first}', Mgmt.slate),
                ]),
              ]),
            ),
            const Icon(Icons.chevron_left_rounded, color: Mgmt.slate),
          ]),
        ),
      ),
    );
  }

  // A thumbnail for a document — real image preview for images (token URL),
  // a coloured file-type icon otherwise.
  Widget _docThumb(Map f, {double size = 46, double radius = 11}) {
    final fc = _fileColor(f);
    if (f['is_image'] == true && f['att_url'] != null) {
      return ClipRRect(
        borderRadius: BorderRadius.circular(radius),
        child: FutureBuilder<String>(
          future: context.read<AuthProvider>().api.tokenizedUrl('${f['att_url']}'),
          builder: (_, s) => s.hasData
              ? Image.network(s.data!, width: size, height: size, fit: BoxFit.cover, gaplessPlayback: true,
                  errorBuilder: (_, __, ___) => Container(width: size, height: size,
                      color: fc.withValues(alpha: 0.12), child: Icon(_fileIcon(f), color: fc, size: size * 0.5)))
              : Container(width: size, height: size, color: fc.withValues(alpha: 0.08)),
        ),
      );
    }
    return Container(
      width: size, height: size, alignment: Alignment.center,
      decoration: BoxDecoration(color: fc.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(radius)),
      child: Icon(_fileIcon(f), color: fc, size: size * 0.5),
    );
  }

  Widget _docGridTile(Map r) {
    final f = (r['doc'] as Map?) ?? const {};
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(12),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(6),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.black12)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Expanded(child: _docThumb(f, size: double.infinity, radius: 9)),
            const SizedBox(height: 5),
            Text('${f['name'] ?? r['title']}', maxLines: 2, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 10.5, color: Mgmt.ink, height: 1.2)),
          ]),
        ),
      ),
    );
  }

  // ---- Invoice requests (request.invoice) -------------------------------
  Widget _reqinvCard(Map r) {
    final ri = (r['ri'] as Map?) ?? const {};
    final cur = '${ri['currency'] ?? ''}';
    final money = cur.isEmpty ? '' : ' $cur';
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              _logoBox('${ri['logo_b64'] ?? ''}', '${ri['partner'] ?? r['title']}', size: 44),
              const SizedBox(width: 11),
              Expanded(
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                      margin: const EdgeInsetsDirectional.only(end: 6),
                      decoration: BoxDecoration(color: widget.accent.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(6)),
                      child: Text('📥 ${r['title']}', style: TextStyle(color: widget.accent, fontWeight: FontWeight.w900, fontSize: 10.5)),
                    ),
                    const Spacer(),
                    mgmtStateChip(r),
                  ]),
                  const SizedBox(height: 3),
                  Text('${ri['partner'] ?? '—'}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.ink)),
                ]),
              ),
              if ((ri['amount'] as num?) != null)
                Text('${(ri['amount'] as num).toStringAsFixed(3)}$money',
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: widget.accent)),
            ]),
            const SizedBox(height: 8),
            Wrap(spacing: 6, runSpacing: 4, children: [
              if (ri['project'] != null) _tag('🏗️ ${ri['project']}', Mgmt.slate),
              if ((ri['lines'] as num?) != null && (ri['lines'] as num) > 0) _tag('🧾 ${ri['lines']} ${tr('بند', 'items')}', Mgmt.slate),
              if ((ri['invoice_count'] as num?) != null && (ri['invoice_count'] as num) > 0)
                _tag('📄 ${ri['invoice_count']} ${tr('فاتورة', 'inv')}', const Color(0xFF16A34A)),
              if (ri['delivered'] == true) _tag('🚚 ${tr('مُسلّمة', 'Delivered')}', const Color(0xFF16A34A)),
              if (ri['date'] != null) _tag('📅 ${'${ri['date']}'.split(' ').first}', Mgmt.slate),
            ]),
          ]),
        ),
      ),
    );
  }

  // ---- Legal cases (hr.lawsuit) -----------------------------------------
  Widget _legalCard(Map r) {
    final lg = (r['lg'] as Map?) ?? const {};
    final sc = mgmtHex('${lg['state_color'] ?? '#64748B'}');
    final stLabel = gLang == 'en' ? '${lg['state_en'] ?? ''}' : '${lg['state_ar'] ?? ''}';
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${lg['party'] ?? r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.black12),
            // a thin severity rail on the leading edge by state
            gradient: LinearGradient(colors: [sc.withValues(alpha: 0.06), Colors.white], stops: const [0, 0.15],
                begin: AlignmentDirectional.centerStart, end: AlignmentDirectional.centerEnd),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Container(
                width: 44, height: 44, alignment: Alignment.center,
                decoration: BoxDecoration(color: sc.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(12)),
                child: const Text('⚖️', style: TextStyle(fontSize: 22)),
              ),
              const SizedBox(width: 11),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${lg['party'] ?? '—'}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: Mgmt.ink))),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2.5),
                    decoration: BoxDecoration(color: sc.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
                    child: Text(stLabel, style: TextStyle(color: sc, fontWeight: FontWeight.w900, fontSize: 10)),
                  ),
                ]),
                const SizedBox(height: 3),
                Text('${lg['code'] ?? ''}${lg['court'] != null ? ' · ${lg['court']}' : ''}',
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 11.5, color: Mgmt.slate)),
              ])),
            ]),
            const SizedBox(height: 8),
            Wrap(spacing: 6, runSpacing: 4, children: [
              if (lg['ref_no'] != null) _tag('#️⃣ ${lg['ref_no']}', Mgmt.slate),
              if (lg['hearing_date'] != null) _tag('📅 ${'${lg['hearing_date']}'.split(' ').first}', const Color(0xFFF59E0B)),
              if (lg['next_appointment'] != null) _tag('⏰ ${'${lg['next_appointment']}'.split(' ').first}', const Color(0xFF0EA5E9)),
              if ((lg['updates'] as num?) != null && (lg['updates'] as num) > 0)
                _tag('🗒️ ${lg['updates']} ${tr('تحديث', 'updates')}', const Color(0xFF7C3AED)),
            ]),
          ]),
        ),
      ),
    );
  }

  // ---- Fuel tanks (petrol.tank) -----------------------------------------
  Widget _petrolCard(Map r) {
    final pt = (r['pt'] as Map?) ?? const {};
    final progress = (numOf(pt['progress'], 0)).toDouble().clamp(0, 100).toDouble();
    final low = progress < 20;
    final barColor = low ? const Color(0xFFDC2626) : (progress < 50 ? const Color(0xFFF59E0B) : const Color(0xFF16A34A));
    return Material(
      color: Colors.white, borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${pt['name'] ?? r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Container(
                width: 44, height: 44, alignment: Alignment.center,
                decoration: BoxDecoration(color: barColor.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(12)),
                child: const Text('⛽', style: TextStyle(fontSize: 22)),
              ),
              const SizedBox(width: 11),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${pt['name'] ?? '—'}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: Mgmt.ink)),
                Text('${tr('السعة', 'Capacity')}: ${_num(pt['capacity'])} ${tr('لتر', 'L')}${pt['stage'] != null ? ' · ${pt['stage']}' : ''}',
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11.5, color: Mgmt.slate)),
              ])),
              Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                Text('${_num(pt['balance'])}', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: barColor)),
                Text(tr('لتر متبقٍ', 'L left'), style: const TextStyle(fontSize: 9.5, color: Mgmt.slate)),
              ]),
            ]),
            const SizedBox(height: 10),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(value: progress / 100, minHeight: 7,
                  backgroundColor: Mgmt.bg, valueColor: AlwaysStoppedAnimation(barColor)),
            ),
            const SizedBox(height: 8),
            Wrap(spacing: 6, runSpacing: 4, children: [
              _tag('🔋 ${progress.toInt()}%', barColor),
              if ((pt['charges'] as num?) != null) _tag('🛢️ ${pt['charges']} ${tr('شحنة', 'charges')}', Mgmt.slate),
              if ((pt['uses'] as num?) != null) _tag('🚗 ${pt['uses']} ${tr('صرف', 'uses')}', Mgmt.slate),
              if (pt['last_charge'] != null) _tag('📅 ${pt['last_charge']}', Mgmt.slate),
            ]),
          ]),
        ),
      ),
    );
  }

  String _num(dynamic v) {
    final n = v is num ? v : double.tryParse('$v') ?? 0;
    return n == n.roundToDouble() ? n.toInt().toString() : n.toStringAsFixed(1);
  }

  // ---- Passports (care.passport) ----------------------------------------
  Widget _passportCard(Map r) {
    final pp = (r['pp'] as Map?) ?? const {};
    final exColor = mgmtHex('${pp['expiry_color'] ?? ''}', Mgmt.slate);
    final stColor = mgmtHex('${pp['state_color'] ?? ''}', Mgmt.slate);
    return Material(
      color: Colors.white, borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${pp['employee'] ?? r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Row(children: [
            _logoBox('${pp['photo_b64'] ?? ''}', '${pp['employee'] ?? ''}', size: 44),
            const SizedBox(width: 11),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${pp['employee'] ?? '—'}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: Mgmt.ink)),
              const SizedBox(height: 2),
              Text('🛂 ${pp['passport_no'] ?? '—'}${pp['country'] != null ? ' · ${pp['country']}' : ''}',
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11.5, color: Mgmt.slate)),
              const SizedBox(height: 5),
              Wrap(spacing: 6, runSpacing: 4, children: [
                _tag(gLang == 'en' ? '${pp['state_en']}' : '${pp['state_ar']}', stColor),
                _tag('${gLang == 'en' ? pp['expiry_en'] : pp['expiry_ar']}${pp['expiry_date'] != null ? ' · ${pp['expiry_date']}' : ''}', exColor),
                if (pp['holder'] != null) _tag('🤝 ${pp['holder']}', const Color(0xFFF59E0B)),
              ]),
            ])),
          ]),
        ),
      ),
    );
  }

  // ---- Vehicle service --------------------------------------------------
  Widget _vsCard(Map r) {
    final v = (r['vs'] as Map?) ?? const {};
    final cur = '${v['currency'] ?? ''}';
    final money = cur.isEmpty ? '' : ' $cur';
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Row(children: [
            SizedBox(
              width: 48, height: 48,
              child: '${v['image_b64'] ?? ''}'.isEmpty
                  ? Container(decoration: BoxDecoration(color: widget.accent.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(11)),
                      child: Icon(Icons.build_rounded, color: widget.accent, size: 22))
                  : ClipRRect(borderRadius: BorderRadius.circular(11),
                      child: Image.memory(base64Decode('${v['image_b64']}'), width: 48, height: 48, fit: BoxFit.cover, gaplessPlayback: true,
                          errorBuilder: (_, __, ___) => Icon(Icons.build_rounded, color: widget.accent, size: 22))),
            ),
            const SizedBox(width: 11),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${v['vehicle'] ?? r['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.ink))),
                  mgmtStateChip(r),
                ]),
                if (v['service_type'] != null)
                  Padding(padding: const EdgeInsets.only(top: 2),
                      child: Text('🔧 ${v['service_type']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Mgmt.slate, fontSize: 11, fontWeight: FontWeight.w600))),
                const SizedBox(height: 5),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  if ('${v['plate'] ?? ''}'.isNotEmpty)
                    Container(padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                        decoration: BoxDecoration(color: Mgmt.ink, borderRadius: BorderRadius.circular(5)),
                        child: Text('🔖 ${v['plate']}', style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w900, letterSpacing: 1))),
                  if ((v['amount'] as num?) != null && (v['amount'] as num) > 0)
                    _tag('💰 ${(v['amount'] as num).toStringAsFixed(3)}$money', widget.accent),
                  if (v['date'] != null) _tag('📅 ${'${v['date']}'.split(' ').first}', Mgmt.slate),
                  if (v['next_service'] != null) _tag('⏰ ${'${v['next_service']}'.split(' ').first}', const Color(0xFFF59E0B)),
                ]),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  // ---- Experience / contracts -------------------------------------------
  Widget _experienceCard(Map r) {
    final x = (r['xp'] as Map?) ?? const {};
    final exp = (x['expiry'] as Map?) ?? const {};
    final expColor = mgmtHex('${exp['color'] ?? ''}', Mgmt.slate);
    final days = (x['days_to_expiry'] as num?)?.toInt() ?? 0;
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openDetail(r['id'] as int, '${r['title']}'),
        child: Container(
          padding: const EdgeInsets.all(11),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Row(children: [
            _logoBox('${x['logo_b64'] ?? ''}', '${x['partner'] ?? r['title']}', size: 46),
            const SizedBox(width: 11),
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${x['partner'] ?? r['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Mgmt.ink))),
                  mgmtStateChip(r),
                ]),
                Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text('${r['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Mgmt.slate, fontSize: 10.5, fontWeight: FontWeight.w600)),
                ),
                const SizedBox(height: 5),
                Wrap(spacing: 6, runSpacing: 4, children: [
                  _tag('⏳ ${days >= 0 ? tr('متبقٍ $days يوم', '$days days left') : tr('منتهٍ', 'Expired')}', expColor),
                  if ((x['renewed'] as num?) != null && (x['renewed'] as num) > 0)
                    _tag('🔄 ${x['renewed']}', const Color(0xFFF59E0B)),
                  if ((x['guarantees'] as num?) != null && (x['guarantees'] as num) > 0)
                    _tag('🛡️ ${x['guarantees']}', Mgmt.slate),
                  if (x['start'] != null) _tag('📅 ${'${x['start']}'.split(' ').first}', Mgmt.slate),
                ]),
              ]),
            ),
          ]),
        ),
      ),
    );
  }

  Future<void> _openDetail(int id, String title) async {
    // Employees open the full PMS-style file: photo, tags, and the tappable
    // icon-tile hub (documents, payslips, leaves, allowances, EOS, skills…).
    if (widget.appKey == 'employees') {
      Navigator.push(context, MaterialPageRoute(
          builder: (_) => PmsEmployeeFileScreen(employeeId: id, name: title)));
      return;
    }
    Map<String, dynamic>? d;
    try {
      d = await context.read<AuthProvider>().api.managementDetail(widget.appKey, id);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
      }
      return;
    }
    if (!mounted || d == null) return;
    if (!mounted) return;
    await showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (_) => _DetailSheet(
          appKey: widget.appKey, accent: widget.accent, initial: d!, onChanged: _reload),
    );
  }
}

/// Open one management record from anywhere (e.g. global search): employees →
/// the rich PMS file, everything else → the detail sheet with its actions.
Future<void> openManagementRecord(BuildContext context, String key, int id,
    {String title = '', Color accent = Mgmt.red}) async {
  if (key == 'employees') {
    Navigator.push(context, MaterialPageRoute(
        builder: (_) => PmsEmployeeFileScreen(employeeId: id, name: title)));
    return;
  }
  Map<String, dynamic>? d;
  try {
    d = await context.read<AuthProvider>().api.managementDetail(key, id);
  } catch (e) {
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
    }
    return;
  }
  if (!context.mounted || d == null) return;
  await showModalBottomSheet(
    context: context, isScrollControlled: true, backgroundColor: Colors.white,
    shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
    builder: (_) => _DetailSheet(appKey: key, accent: accent, initial: d!, onChanged: () {}),
  );
}

/// Record detail + its whitelisted workflow actions.
class _DetailSheet extends StatefulWidget {
  const _DetailSheet({required this.appKey, required this.accent, required this.initial, required this.onChanged});
  final String appKey;
  final Color accent;
  final Map<String, dynamic> initial;
  final VoidCallback onChanged;
  @override
  State<_DetailSheet> createState() => _DetailSheetState();
}

class _DetailSheetState extends State<_DetailSheet> {
  late Map<String, dynamic> d = widget.initial;
  bool _busy = false;
  String? _token;

  @override
  void initState() {
    super.initState();
    context.read<AuthProvider>().api.token.then((t) {
      if (mounted) setState(() => _token = t);
    });
  }

  // Prominent workflow-action bar shown right under the record header. Primary
  // actions (approve/confirm/submit …) read as filled buttons; secondary as
  // outlines; destructive in red — so the required action stands out at a glance.
  Widget _actionBar(List actions) {
    if (actions.isEmpty) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white, borderRadius: BorderRadius.circular(16),
        border: Border.all(color: widget.accent.withValues(alpha: 0.14)),
        boxShadow: [BoxShadow(color: widget.accent.withValues(alpha: 0.06), blurRadius: 10, offset: const Offset(0, 3))],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(Icons.bolt_rounded, size: 15, color: widget.accent),
          const SizedBox(width: 5),
          Text(tr('الإجراءات المتاحة', 'Available actions'),
              style: TextStyle(fontWeight: FontWeight.w900, fontSize: 11.5, color: widget.accent)),
        ]),
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final a in actions)
            SizedBox(
              height: 42,
              child: (a as Map)['style'] == 'primary'
                  ? ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(
                          backgroundColor: widget.accent, foregroundColor: Colors.white, elevation: 0,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                      icon: const Icon(Icons.check_circle_rounded, size: 17),
                      onPressed: _busy ? null : () => _run(a),
                      label: Text(gLang == 'en' ? '${a['en']}' : '${a['ar']}',
                          style: const TextStyle(fontWeight: FontWeight.w800)))
                  : OutlinedButton(
                      style: OutlinedButton.styleFrom(
                          foregroundColor: a['style'] == 'danger' ? Mgmt.red : Mgmt.slate,
                          side: BorderSide(color: a['style'] == 'danger' ? Mgmt.red : Colors.black26),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                      onPressed: _busy ? null : () => _run(a),
                      child: Text(gLang == 'en' ? '${a['en']}' : '${a['ar']}',
                          style: const TextStyle(fontWeight: FontWeight.w800))),
            ),
        ]),
      ]),
    );
  }

  Future<void> _run(Map a) async {
    if (a['confirm'] == true) {
      final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: Text(tr('تأكيد الإجراء', 'Confirm action'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
        content: Text(tr('هل تريد تنفيذ «${a['ar']}»؟', 'Run "${a['en']}"?')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('تراجع', 'Back'))),
          ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: Mgmt.red, foregroundColor: Colors.white),
            onPressed: () => Navigator.pop(c, true), child: Text(tr('نعم', 'Yes'))),
        ],
      ));
      if (ok != true) return;
    }
    if (!mounted) return;
    setState(() => _busy = true);
    try {
      final res = await context.read<AuthProvider>().api
          .managementAction(widget.appKey, d['id'] as int, '${a['key']}');
      if (!mounted) return;
      setState(() { d['state'] = res['state']; d['actions'] = res['actions']; });
      widget.onChanged();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('✅ تم: ${a['ar']}', '✅ Done: ${a['en']}')),
          backgroundColor: const Color(0xFF16A34A)));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _reload() async {
    try {
      final fresh = await context
          .read<AuthProvider>()
          .api
          .managementDetail(widget.appKey, d['id'] as int);
      if (mounted) setState(() => d = fresh);
    } catch (_) {}
  }

  Future<void> _editSheet() async {
    final editable = ((d['editable'] as List?) ?? const []).cast<Map>();
    if (editable.isEmpty) return;
    final saved = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _EditSheet(
          appKey: widget.appKey,
          id: d['id'] as int,
          accent: widget.accent,
          title: '${d['title']}',
          editable: editable),
    );
    if (saved == true) {
      await _reload();
      widget.onChanged();
    }
  }

  // ---- value rendering by type ------------------------------------------
  Widget _fieldRow(Map f) {
    final t = '${f['type']}';
    final v = '${f['value']}';
    Widget value;
    if (t == 'monetary' || t == 'float') {
      value = Text(v,
          style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: widget.accent));
    } else if (t == 'many2one') {
      value = Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
        decoration: BoxDecoration(
            color: widget.accent.withValues(alpha: 0.10),
            borderRadius: BorderRadius.circular(8)),
        child: Text(v,
            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12, color: widget.accent)),
      );
    } else {
      value = Text(v,
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: Mgmt.ink));
    }
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        SizedBox(
            width: 120,
            child: Text('${f['label']}',
                style: const TextStyle(color: Mgmt.slate, fontSize: 12))),
        const SizedBox(width: 6),
        Expanded(child: Align(alignment: AlignmentDirectional.centerStart, child: value)),
      ]),
    );
  }

  String _reportPath(Map r) =>
      '/api/v1/management/${widget.appKey}/${d['id']}/report?report=${Uri.encodeQueryComponent('${r['report']}')}';

  Future<void> _openReport(Map r) async {
    final path = _reportPath(r);
    if ('${r['type']}' == 'xlsx') {
      await exportExcelFile(context, path: path,
          fileName: '${widget.appKey}-${d['id']}.xlsx');
    } else {
      if (!mounted) return;
      Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
          path: path, title: gLang == 'en' ? '${r['en']}' : '${r['ar']}',
          fileName: '${widget.appKey}-${d['id']}.pdf')));
    }
  }

  // ---- Attachments (chatter + direct): openable, zoomable, shareable ----
  String _attUrl(Map a) => _token == null ? '${a['url']}' : '${a['url']}?token=$_token';

  Future<void> _openAttachment(Map a, List<Map> images) async {
    if (a['is_image'] == true) {
      final media = images.map((m) => {'url': _attUrl(m), 'name': m['name'], 'type': 'image'}).toList();
      final idx = images.indexWhere((m) => m['id'] == a['id']);
      Navigator.push(context, MaterialPageRoute(
          builder: (_) => MediaViewerScreen(media: media, index: idx < 0 ? 0 : idx, token: _token)));
    } else if (a['is_pdf'] == true) {
      Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
          path: '/api/v1/management/attachment/${a['id']}', title: '${a['name']}', fileName: '${a['name']}')));
    } else {
      // other file types: open the download/share viewer
      Navigator.push(context, MaterialPageRoute(builder: (_) => MediaViewerScreen(
          media: [{'url': _attUrl(a), 'name': a['name'], 'type': a['mimetype']}], token: _token)));
    }
  }

  Widget _attachmentTile(Map a, List<Map> images) {
    final isImg = a['is_image'] == true;
    final isPdf = a['is_pdf'] == true;
    return SizedBox(
      width: 96,
      child: Column(children: [
        Material(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          child: InkWell(
            borderRadius: BorderRadius.circular(12),
            onTap: () => _openAttachment(a, images),
            child: Container(
              width: 96, height: 84,
              clipBehavior: Clip.antiAlias,
              decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.black.withValues(alpha: 0.08)),
                  color: Mgmt.bg),
              child: isImg && _token != null
                  ? Image.network(_attUrl(a), fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => const Center(child: Icon(Icons.image_rounded, color: Mgmt.slate)))
                  : Center(child: Icon(isPdf ? Icons.picture_as_pdf_rounded : Icons.insert_drive_file_rounded,
                      size: 30, color: isPdf ? Mgmt.red : widget.accent)),
            ),
          ),
        ),
        const SizedBox(height: 3),
        Text('${a['name']}', maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
            style: const TextStyle(fontSize: 9.5, color: Mgmt.slate, fontWeight: FontWeight.w600)),
      ]),
    );
  }

  Widget _attachmentsCard() {
    final atts = ((d['attachments'] as List?) ?? const []).cast<Map>();
    if (atts.isEmpty) return const SizedBox.shrink();
    final images = atts.where((a) => a['is_image'] == true).toList();
    return _cardWrap([
      _sectionHead('📎', '${tr('المرفقات', 'Attachments')} (${atts.length})'),
      Padding(
        padding: const EdgeInsets.fromLTRB(12, 6, 12, 12),
        child: Wrap(spacing: 10, runSpacing: 10, children: [
          for (final a in atts) _attachmentTile(a, images),
        ]),
      ),
    ]);
  }

  Widget _reportsCard() {
    final reports = (d['reports'] as List?) ?? const [];
    if (reports.isEmpty) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(Icons.description_rounded, size: 16, color: widget.accent),
          const SizedBox(width: 6),
          Text(tr('التقارير', 'Reports'), style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: widget.accent)),
        ]),
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 8, children: [
          for (final r in reports.cast<Map>())
            OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                  foregroundColor: '${r['type']}' == 'xlsx' ? const Color(0xFF16A34A) : widget.accent,
                  side: BorderSide(color: ('${r['type']}' == 'xlsx' ? const Color(0xFF16A34A) : widget.accent).withValues(alpha: 0.5)),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(11))),
              onPressed: _busy ? null : () => _openReport(r),
              icon: Icon('${r['type']}' == 'xlsx' ? Icons.table_chart_rounded : Icons.picture_as_pdf_rounded, size: 16),
              label: Text(gLang == 'en' ? '${r['en']}' : '${r['ar']}',
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 11.5)),
            ),
        ]),
      ]),
    );
  }

  Widget _linesCard() {
    final lines = (d['lines'] as List?) ?? const [];
    if (lines.isEmpty) return const SizedBox.shrink();
    final cur = d['currency'] ?? '';
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 12, 14, 0),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
      clipBehavior: Clip.antiAlias,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          padding: const EdgeInsets.fromLTRB(14, 11, 14, 9),
          decoration: BoxDecoration(border: Border(bottom: BorderSide(color: Colors.grey.shade100))),
          child: Row(children: [
            Text('🧾 ', style: const TextStyle(fontSize: 14)),
            Text(tr('البنود (${lines.length})', 'Line items (${lines.length})'),
                style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: widget.accent)),
          ]),
        ),
        for (final l in lines.cast<Map>())
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
            child: Row(children: [
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${l['name']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12, color: Mgmt.ink)),
                if (l['qty'] != null || l['price'] != null)
                  Text([
                    if (l['qty'] != null) '${tr('كمية', 'Qty')}: ${l['qty']}',
                    if (l['price'] != null) '${tr('سعر', 'Unit')}: ${l['price']}',
                  ].join('  ·  '), style: const TextStyle(fontSize: 10, color: Mgmt.slate)),
              ])),
              if (l['subtotal'] != null)
                Text('${l['subtotal']} $cur',
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: widget.accent)),
            ]),
          ),
      ]),
    );
  }

  Widget _sectionCard(Map s) {
    final fields = (s['fields'] as List?) ?? const [];
    if (fields.isEmpty) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 12, 14, 0),
      decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          padding: const EdgeInsets.fromLTRB(14, 11, 14, 9),
          decoration: BoxDecoration(
              border: Border(bottom: BorderSide(color: Colors.grey.shade100))),
          child: Row(children: [
            Text('${s['icon'] ?? '📋'} ', style: const TextStyle(fontSize: 14)),
            Text(gLang == 'en' ? '${s['title_en'] ?? s['title']}' : '${s['title']}',
                style: TextStyle(
                    fontWeight: FontWeight.w900, fontSize: 12.5, color: widget.accent)),
          ]),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 4, 14, 10),
          child: Column(children: [for (final f in fields) _fieldRow(f as Map)]),
        ),
      ]),
    );
  }

  // ---- Proposals: professional detail blocks ----------------------------
  Future<void> _sendProposal() async {
    final clientEmail = '${(d['proposal'] as Map?)?['send_email'] ?? ''}';
    final choice = await showModalBottomSheet<String>(
      context: context, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => SafeArea(child: Column(mainAxisSize: MainAxisSize.min, children: [
        Padding(padding: const EdgeInsets.all(16),
            child: Text(tr('إرسال عرض السعر إلى', 'Send quotation to'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15))),
        if (clientEmail.isNotEmpty)
          ListTile(
            leading: const Icon(Icons.person_rounded, color: Color(0xFF16A34A)),
            title: Text(tr('العميل', 'The client')), subtitle: Text(clientEmail),
            onTap: () => Navigator.pop(context, 'client')),
        ListTile(
          leading: Icon(Icons.person_search_rounded, color: widget.accent),
          title: Text(tr('اختيار مستلم آخر', 'Choose another recipient')),
          onTap: () => Navigator.pop(context, 'other')),
        const SizedBox(height: 8),
      ])),
    );
    if (choice == null || !mounted) return;
    String? email;
    if (choice == 'other') {
      Map<String, dynamic> rec;
      try {
        rec = await context.read<AuthProvider>().api.managementPoRecipients();
      } catch (e) {
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
        return;
      }
      if (!mounted) return;
      final opts = ((rec['recipients'] as List?) ?? const [])
          .map((e) => {'v': e['v'], 'l': '${e['l']}  ·  ${e['email']}', 'email': e['email']}).toList().cast<Map>();
      final picked = await showModalBottomSheet<String>(
        context: context, isScrollControlled: true, backgroundColor: Colors.white,
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
        builder: (_) => _RecipientPicker(options: opts, accent: widget.accent),
      );
      if (picked == null || !mounted) return;
      email = picked;
    }
    setState(() => _busy = true);
    try {
      final res = await context.read<AuthProvider>().api.managementProposalSend(d['id'] as int, email: email);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('✅ أُرسل العرض إلى ${res['email']}', '✅ Sent to ${res['email']}')),
          backgroundColor: const Color(0xFF16A34A)));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _editProposal() async {
    final saved = await showModalBottomSheet<Map<String, dynamic>>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _ProposalCreateSheet(accent: widget.accent, editId: d['id'] as int),
    );
    if (saved != null && mounted) {
      await _reload();
      widget.onChanged();
    }
  }

  Widget _kpiCell(String label, String value, Color c, {bool big = false}) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(label, style: const TextStyle(color: Mgmt.slate, fontSize: 10.5, fontWeight: FontWeight.w700)),
          const SizedBox(height: 3),
          Text(value, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: big ? 18 : 14.5)),
        ],
      );

  Widget _proposalBlock() {
    final p = d['proposal'] as Map?;
    if (p == null) return const SizedBox.shrink();
    final h = (p['header'] as Map?) ?? const {};
    final dates = (p['dates'] as Map?) ?? const {};
    final breakdown = (p['breakdown'] as List?) ?? const [];
    final info = (p['service_info'] as List?) ?? const [];
    final cur = '${h['currency'] ?? ''}';
    String m(dynamic v) => '${(v as num?)?.toStringAsFixed(3) ?? '0.000'}${cur.isEmpty ? '' : ' $cur'}';
    final margin = (h['margin_pct'] as num?)?.toDouble() ?? 0;
    final marginColor = margin >= 20
        ? const Color(0xFF16A34A)
        : (margin >= 10 ? const Color(0xFFF59E0B) : Mgmt.red);
    final validityColor = mgmtHex('${dates['validity_color'] ?? ''}', Mgmt.slate);

    return Column(children: [
      // ---- money KPI card: cost / sale / profit / margin
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            gradient: LinearGradient(
                colors: [widget.accent.withValues(alpha: 0.10), widget.accent.withValues(alpha: 0.03)],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: widget.accent.withValues(alpha: 0.18))),
        child: Column(children: [
          Row(children: [
            Expanded(child: _kpiCell(tr('سعر البيع', 'Sale price'), m(h['sale']), widget.accent, big: true)),
            Container(width: 1, height: 40, color: Colors.black.withValues(alpha: 0.08)),
            const SizedBox(width: 10),
            Expanded(child: _kpiCell(tr('التكلفة', 'Cost'), m(h['cost']), Mgmt.ink, big: true)),
          ]),
          const Divider(height: 20),
          Row(children: [
            Expanded(child: _kpiCell(tr('صافي الربح', 'Net profit'), m(h['profit']), marginColor)),
            Container(width: 1, height: 34, color: Colors.black.withValues(alpha: 0.08)),
            const SizedBox(width: 10),
            Expanded(
              child: Row(children: [
                Expanded(child: _kpiCell(tr('نسبة الربح', 'Margin %'), '${margin.toStringAsFixed(1)}%', marginColor)),
                _pctRing(margin, marginColor),
              ]),
            ),
          ]),
          if ((h['individual_sales'] as num?) != null && (h['individual_sales'] as num) > 0) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(10)),
              child: Row(children: [
                Text('👤 ${tr('للفرد', 'Per person')}',
                    style: const TextStyle(color: Mgmt.slate, fontSize: 11, fontWeight: FontWeight.w700)),
                const Spacer(),
                Text('${tr('تكلفة', 'cost')} ${m(h['individual_cost'])}  ·  ${tr('بيع', 'sale')} ${m(h['individual_sales'])}',
                    style: const TextStyle(color: Mgmt.ink, fontSize: 11, fontWeight: FontWeight.w800)),
              ]),
            ),
          ],
        ]),
      ),
      // ---- dates & validity strip
      if (dates.isNotEmpty)
        Container(
          margin: const EdgeInsets.fromLTRB(14, 10, 14, 0),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
              color: Colors.white, borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
          child: Wrap(spacing: 14, runSpacing: 8, crossAxisAlignment: WrapCrossAlignment.center, children: [
            if (dates['proposal_date'] != null)
              _dateChip('📅', tr('تاريخ العرض', 'Date'), '${dates['proposal_date']}'.split(' ').first),
            if (dates['expire_date'] != null)
              _dateChip('⏰', tr('ينتهي', 'Expires'), '${dates['expire_date']}'.split(' ').first),
            if (dates['mobilization_date'] != null)
              _dateChip('🚩', tr('المباشرة', 'Mobilize'), '${dates['mobilization_date']}'.split(' ').first),
            if ((dates['period'] as num?) != null && (dates['period'] as num) > 0)
              _dateChip('🗓️', tr('المدة', 'Period'), '${dates['period']} ${tr('شهر', 'mo')}'),
            if ('${dates['validity']}' != 'none')
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                decoration: BoxDecoration(
                    color: validityColor.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: validityColor.withValues(alpha: 0.34))),
                child: Text(
                    '${gLang == 'en' ? dates['validity_en'] : dates['validity_ar']}'
                    '${(dates['days_to_expire'] as num?) != null && (dates['days_to_expire'] as num) > 0 ? ' · ${dates['days_to_expire']}${tr('ي', 'd')}' : ''}',
                    style: TextStyle(color: validityColor, fontSize: 10.5, fontWeight: FontWeight.w800)),
              ),
          ]),
        ),
      // ---- send-to-client + edit
      Padding(
        padding: const EdgeInsets.fromLTRB(14, 10, 14, 0),
        child: Row(children: [
          if (p['can_send'] == true) ...[
            Expanded(
              child: SizedBox(
                height: 46,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF16A34A), foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
                  onPressed: _busy ? null : _sendProposal,
                  icon: const Icon(Icons.send_rounded, size: 17),
                  label: Text(tr('إرسال', 'Send'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13)),
                ),
              ),
            ),
            const SizedBox(width: 8),
          ],
          Expanded(
            child: SizedBox(
              height: 46,
              child: OutlinedButton.icon(
                style: OutlinedButton.styleFrom(
                    foregroundColor: widget.accent, side: BorderSide(color: widget.accent),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
                onPressed: _busy ? null : _editProposal,
                icon: const Icon(Icons.edit_rounded, size: 17),
                label: Text(tr('تعديل', 'Edit'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13)),
              ),
            ),
          ),
        ]),
      ),
      // ---- linked contract(s)
      if ((p['contracts'] as List?)?.isNotEmpty == true)
        _cardWrap([
          _sectionHead('📜', tr('العقود المرتبطة', 'Linked contracts')),
          for (final ct in (p['contracts'] as List).cast<Map>())
            Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: () => openManagementRecord(context, 'experience', ct['id'] as int, title: '${ct['name']}', accent: widget.accent),
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  child: Row(children: [
                    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${ct['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: Mgmt.ink)),
                      if (ct['start'] != null)
                        Text('📅 ${'${ct['start']}'.split(' ').first}', style: const TextStyle(color: Mgmt.slate, fontSize: 10.5)),
                    ])),
                    mgmtStateChip(ct),
                    const Icon(Icons.chevron_left_rounded, color: Mgmt.slate),
                  ]),
                ),
              ),
            ),
        ]),
      // ---- cost breakdown
      if (breakdown.isNotEmpty)
        Container(
          margin: const EdgeInsets.fromLTRB(14, 12, 14, 0),
          decoration: BoxDecoration(
              color: Colors.white, borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              padding: const EdgeInsets.fromLTRB(14, 11, 14, 9),
              decoration: BoxDecoration(border: Border(bottom: BorderSide(color: Colors.grey.shade100))),
              child: Row(children: [
                const Text('🧮 ', style: TextStyle(fontSize: 14)),
                Text(tr('مكوّنات التكلفة', 'Cost breakdown'),
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: widget.accent)),
              ]),
            ),
            for (final b in breakdown.cast<Map>())
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
                child: Row(children: [
                  Expanded(child: Text(gLang == 'en' ? '${b['en']}' : '${b['ar']}',
                      style: const TextStyle(color: Mgmt.ink, fontSize: 12, fontWeight: FontWeight.w600))),
                  Text(m(b['value']),
                      style: const TextStyle(color: Mgmt.ink, fontSize: 12.5, fontWeight: FontWeight.w800)),
                ]),
              ),
            Container(
              padding: const EdgeInsets.fromLTRB(14, 9, 14, 11),
              decoration: BoxDecoration(
                  color: widget.accent.withValues(alpha: 0.05),
                  borderRadius: const BorderRadius.vertical(bottom: Radius.circular(16))),
              child: Row(children: [
                Expanded(child: Text(tr('إجمالي التكلفة', 'Total cost'),
                    style: TextStyle(color: widget.accent, fontSize: 12.5, fontWeight: FontWeight.w900))),
                Text(m(h['cost']),
                    style: TextStyle(color: widget.accent, fontSize: 13.5, fontWeight: FontWeight.w900)),
              ]),
            ),
          ]),
        ),
      // ---- service info
      if (info.isNotEmpty)
        Container(
          margin: const EdgeInsets.fromLTRB(14, 12, 14, 0),
          decoration: BoxDecoration(
              color: Colors.white, borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              padding: const EdgeInsets.fromLTRB(14, 11, 14, 9),
              decoration: BoxDecoration(border: Border(bottom: BorderSide(color: Colors.grey.shade100))),
              child: Row(children: [
                const Text('🧾 ', style: TextStyle(fontSize: 14)),
                Text(tr('بيانات الخدمة والتفاصيل', 'Service details'),
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: widget.accent)),
              ]),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(6, 4, 6, 8),
              child: Column(children: [
                for (final f in info.cast<Map>())
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 7),
                    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${f['icon'] ?? '•'}  ', style: const TextStyle(fontSize: 13)),
                      SizedBox(width: 96, child: Text(gLang == 'en' ? '${f['en']}' : '${f['ar']}',
                          style: const TextStyle(color: Mgmt.slate, fontSize: 11.5))),
                      const SizedBox(width: 6),
                      Expanded(child: Text('${f['value']}',
                          style: const TextStyle(color: Mgmt.ink, fontSize: 12.5, fontWeight: FontWeight.w700))),
                    ]),
                  ),
              ]),
            ),
          ]),
        ),
    ]);
  }

  Widget _dateChip(String icon, String label, String value) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        children: [
          Text('$icon $label', style: const TextStyle(color: Mgmt.slate, fontSize: 9.5, fontWeight: FontWeight.w700)),
          const SizedBox(height: 1),
          Text(value, style: const TextStyle(color: Mgmt.ink, fontSize: 12, fontWeight: FontWeight.w800)),
        ],
      );

  Widget _pctRing(double pct, Color c) => SizedBox(
        width: 34, height: 34,
        child: Stack(alignment: Alignment.center, children: [
          SizedBox(
            width: 34, height: 34,
            child: CircularProgressIndicator(
                value: (pct.clamp(0, 100)) / 100.0, strokeWidth: 4,
                backgroundColor: c.withValues(alpha: 0.15),
                valueColor: AlwaysStoppedAnimation(c)),
          ),
          Text('${pct.round()}', style: TextStyle(color: c, fontSize: 9, fontWeight: FontWeight.w900)),
        ]),
      );

  Widget _sectionHead(String icon, String title) => Container(
        padding: const EdgeInsets.fromLTRB(14, 11, 14, 9),
        decoration: BoxDecoration(border: Border(bottom: BorderSide(color: Colors.grey.shade100))),
        child: Row(children: [
          Text('$icon ', style: const TextStyle(fontSize: 14)),
          Text(title, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: widget.accent)),
        ]),
      );

  Widget _cardWrap(List<Widget> children) => Container(
        margin: const EdgeInsets.fromLTRB(14, 12, 14, 0),
        decoration: BoxDecoration(
            color: Colors.white, borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: children),
      );

  Widget _infoRows(List info) => Padding(
        padding: const EdgeInsets.fromLTRB(6, 4, 6, 8),
        child: Column(children: [
          for (final f in info.cast<Map>())
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 7),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${f['icon'] ?? '•'}  ', style: const TextStyle(fontSize: 13)),
                SizedBox(width: 108, child: Text(gLang == 'en' ? '${f['en']}' : '${f['ar']}',
                    style: const TextStyle(color: Mgmt.slate, fontSize: 11.5))),
                const SizedBox(width: 6),
                Expanded(child: Text('${f['value']}',
                    style: const TextStyle(color: Mgmt.ink, fontSize: 12.5, fontWeight: FontWeight.w700))),
              ]),
            ),
        ]),
      );

  Future<void> _openTenderTab(String code, String label) async {
    setState(() => _busy = true);
    Map<String, dynamic>? res;
    try {
      res = await context.read<AuthProvider>().api.managementTenderTab(d['id'] as int, code);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
    if (res == null || !mounted) return;
    await _showLines(label, (res['lines'] as List?) ?? const []);
  }

  Future<void> _openFleetLog(String code, String label) async {
    setState(() => _busy = true);
    Map<String, dynamic>? res;
    try {
      res = await context.read<AuthProvider>().api.managementFleetLog(d['id'] as int, code);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
    if (res == null || !mounted) return;
    await _showLines(label, (res['lines'] as List?) ?? const []);
  }

  Future<void> _showLines(String label, List lines) async {
    await showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.75, maxChildSize: 0.95, minChildSize: 0.4,
        builder: (_, sc) => Column(children: [
          Container(
            padding: const EdgeInsets.fromLTRB(18, 14, 12, 12),
            decoration: BoxDecoration(
                gradient: LinearGradient(colors: [widget.accent, widget.accent.withValues(alpha: 0.72)],
                    begin: Alignment.topRight, end: Alignment.bottomLeft),
                borderRadius: const BorderRadius.vertical(top: Radius.circular(22))),
            child: Row(children: [
              Expanded(child: Text('$label · ${lines.length}',
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15))),
              IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close_rounded, color: Colors.white)),
            ]),
          ),
          Expanded(
            child: lines.isEmpty
                ? Center(child: Text(tr('لا بيانات', 'No data'), style: const TextStyle(color: Mgmt.slate, fontWeight: FontWeight.w700)))
                : ListView.separated(
                    controller: sc, padding: const EdgeInsets.all(12),
                    itemCount: lines.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (_, i) {
                      final l = lines[i] as Map;
                      final pairs = (l['pairs'] as List?) ?? const [];
                      return Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                            color: Mgmt.bg, borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: Colors.black.withValues(alpha: 0.05))),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text('${l['name']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.ink)),
                          if (pairs.isNotEmpty) const SizedBox(height: 6),
                          for (final p in pairs.cast<Map>())
                            Padding(
                              padding: const EdgeInsets.symmetric(vertical: 3),
                              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                SizedBox(width: 120, child: Text('${p['label']}',
                                    style: const TextStyle(color: Mgmt.slate, fontSize: 11))),
                                const SizedBox(width: 6),
                                Expanded(child: Text('${p['value']}',
                                    style: TextStyle(
                                        color: (p['type'] == 'float' || p['type'] == 'monetary') ? widget.accent : Mgmt.ink,
                                        fontSize: 12, fontWeight: FontWeight.w700))),
                              ]),
                            ),
                        ]),
                      );
                    },
                  ),
          ),
        ]),
      ),
    );
  }

  Widget _tenderBlock() {
    final t = d['tender'] as Map?;
    if (t == null) return const SizedBox.shrink();
    final h = (t['header'] as Map?) ?? const {};
    final dates = (t['dates'] as Map?) ?? const {};
    final info = (t['service_info'] as List?) ?? const [];
    final tabs = (t['tabs'] as List?) ?? const [];
    final prep = (t['prep'] as Map?) ?? const {};
    final cur = '${h['currency'] ?? ''}';
    String m(dynamic v) => '${(v as num?)?.toStringAsFixed(3) ?? '0.000'}${cur.isEmpty ? '' : ' $cur'}';
    final dl = (dates['deadline'] as Map?) ?? const {};
    final dlColor = mgmtHex('${dl['color'] ?? ''}', Mgmt.slate);
    final prob = (h['win_probability'] as num?)?.toDouble() ?? 0;
    final probColor = prob >= 60 ? const Color(0xFF16A34A) : (prob >= 35 ? const Color(0xFFF59E0B) : Mgmt.slate);
    final prep1 = (prep['checklist_total'] as num?) ?? 0;
    final prep2 = (prep['requirement_total'] as num?) ?? 0;

    return Column(children: [
      // financial KPI card
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            gradient: LinearGradient(
                colors: [widget.accent.withValues(alpha: 0.10), widget.accent.withValues(alpha: 0.03)],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: widget.accent.withValues(alpha: 0.18))),
        child: Column(children: [
          Row(children: [
            Expanded(child: _kpiCell(tr('قيمة المناقصة', 'Tender value'), m(h['price']), widget.accent, big: true)),
            if ((h['our_price'] as num?) != null && (h['our_price'] as num) > 0) ...[
              Container(width: 1, height: 40, color: Colors.black.withValues(alpha: 0.08)),
              const SizedBox(width: 10),
              Expanded(child: _kpiCell(tr('سعرنا', 'Our price'), m(h['our_price']), Mgmt.ink, big: true)),
            ],
          ]),
          const Divider(height: 20),
          Row(children: [
            Expanded(child: _kpiCell(tr('احتمالية الفوز', 'Win prob.'), '${prob.toStringAsFixed(0)}%', probColor)),
            _pctRing(prob, probColor),
            const SizedBox(width: 10),
            Container(width: 1, height: 34, color: Colors.black.withValues(alpha: 0.08)),
            const SizedBox(width: 10),
            Expanded(child: _kpiCell(tr('الضمان', 'Guarantee'), m(h['guarantee']), Mgmt.ink)),
          ]),
          if ((h['price_gap'] as num?) != null && (h['price_gap'] as num) != 0) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(10)),
              child: Row(children: [
                Text('📊 ${tr('فارق السعر', 'Price gap')}', style: const TextStyle(color: Mgmt.slate, fontSize: 11, fontWeight: FontWeight.w700)),
                const Spacer(),
                Text('${m(h['price_gap'])}  ·  ${(h['price_gap_pct'] as num?)?.toStringAsFixed(1) ?? '0'}%',
                    style: const TextStyle(color: Mgmt.ink, fontSize: 11.5, fontWeight: FontWeight.w800)),
              ]),
            ),
          ],
        ]),
      ),
      // dates & deadline strip
      Container(
        margin: const EdgeInsets.fromLTRB(14, 10, 14, 0),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        decoration: BoxDecoration(
            color: Colors.white, borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
        child: Wrap(spacing: 14, runSpacing: 8, crossAxisAlignment: WrapCrossAlignment.center, children: [
          if (dates['issue_date'] != null) _dateChip('📢', tr('الطرح', 'Issued'), '${dates['issue_date']}'.split(' ').first),
          if (dates['closing_date'] != null) _dateChip('⏰', tr('الإغلاق', 'Closing'), '${dates['closing_date']}'.split(' ').first),
          if (dates['meeting_date'] != null) _dateChip('🤝', tr('الاجتماع', 'Meeting'), '${dates['meeting_date']}'.split(' ').first),
          if ((dates['period'] as num?) != null && (dates['period'] as num) > 0)
            _dateChip('🗓️', tr('المدة', 'Period'), '${dates['period']} ${tr('شهر', 'mo')}'),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
            decoration: BoxDecoration(
                color: dlColor.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20),
                border: Border.all(color: dlColor.withValues(alpha: 0.34))),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Icon((dl['urgent'] == true) ? Icons.timer_rounded : Icons.event_available_rounded, size: 13, color: dlColor),
              const SizedBox(width: 5),
              Text(gLang == 'en' ? '${dl['en']}' : '${dl['ar']}',
                  style: TextStyle(color: dlColor, fontSize: 10.5, fontWeight: FontWeight.w800)),
            ]),
          ),
        ]),
      ),
      // preparation progress
      if (prep1 > 0 || prep2 > 0)
        Container(
          margin: const EdgeInsets.fromLTRB(14, 10, 14, 0),
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
          decoration: BoxDecoration(
              color: Colors.white, borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
          child: Row(children: [
            if (prep1 > 0)
              Expanded(child: _progressLine('✅ ${tr('التحضير', 'Checklist')}',
                  (prep['checklist_pct'] as num?)?.toDouble() ?? 0, '${prep['checklist_done']}/${prep['checklist_total']}')),
            if (prep1 > 0 && prep2 > 0) const SizedBox(width: 16),
            if (prep2 > 0)
              Expanded(child: _progressLine('📋 ${tr('المتطلبات', 'Requirements')}',
                  (prep['requirement_pct'] as num?)?.toDouble() ?? 0, '${prep['requirement_ready']}/${prep['requirement_total']}')),
          ]),
        ),
      // tab tiles (backend tabs: price analysis, manpower, …)
      if (tabs.isNotEmpty)
        _cardWrap([
          _sectionHead('🗂️', tr('التبويبات والتحليلات', 'Tabs & analysis')),
          Padding(
            padding: const EdgeInsets.fromLTRB(10, 10, 10, 12),
            child: Wrap(spacing: 9, runSpacing: 9, children: [
              for (final tab in tabs.cast<Map>()) _tabTile(tab),
            ]),
          ),
        ]),
      // organization & tender info
      if (info.isNotEmpty)
        _cardWrap([
          _sectionHead('🏢', tr('بيانات الجهة والمناقصة', 'Organization & tender')),
          _infoRows(info),
        ]),
    ]);
  }

  Widget _progressLine(String label, double pct, String frac) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Expanded(child: Text(label, style: const TextStyle(color: Mgmt.ink, fontSize: 11.5, fontWeight: FontWeight.w800))),
            Text(frac, style: const TextStyle(color: Mgmt.slate, fontSize: 10.5, fontWeight: FontWeight.w700)),
          ]),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
                value: (pct.clamp(0, 100)) / 100.0, minHeight: 7,
                backgroundColor: widget.accent.withValues(alpha: 0.12),
                valueColor: AlwaysStoppedAnimation(widget.accent)),
          ),
        ],
      );

  Widget _tabTile(Map tab) {
    final count = (tab['count'] as num?)?.toInt() ?? 0;
    final enabled = count > 0;
    final label = gLang == 'en' ? '${tab['en']}' : '${tab['ar']}';
    return SizedBox(
      // exactly 3 tiles per row: full width − card margins(28) − padding(20) − 2 gaps(18)
      width: ((MediaQuery.of(context).size.width - 28 - 20 - 18) / 3) - 1,
      child: Opacity(
        opacity: enabled ? 1 : 0.5,
        child: Material(
          color: widget.accent.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(13),
          child: InkWell(
            borderRadius: BorderRadius.circular(13),
            onTap: enabled && !_busy ? () => _openTenderTab('${tab['code']}', label) : null,
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
              decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(13),
                  border: Border.all(color: widget.accent.withValues(alpha: 0.16))),
              child: Column(children: [
                Stack(clipBehavior: Clip.none, children: [
                  Text('${tab['icon']}', style: const TextStyle(fontSize: 22)),
                  if (count > 0)
                    Positioned(
                      right: -10, top: -6,
                      child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                        decoration: BoxDecoration(color: widget.accent, borderRadius: BorderRadius.circular(10)),
                        child: Text('$count', style: const TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.w900)),
                      ),
                    ),
                ]),
                const SizedBox(height: 7),
                Text(label, maxLines: 2, textAlign: TextAlign.center, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: Mgmt.ink, height: 1.15)),
              ]),
            ),
          ),
        ),
      ),
    );
  }

  Widget _orderBlock() {
    final o = d['order'] as Map?;
    if (o == null) return const SizedBox.shrink();
    final h = (o['header'] as Map?) ?? const {};
    final st = (o['status'] as Map?) ?? const {};
    final info = (o['service_info'] as List?) ?? const [];
    final cur = '${h['currency'] ?? ''}';
    String m(dynamic v) => '${(v as num?)?.toStringAsFixed(3) ?? '0.000'}${cur.isEmpty ? '' : ' $cur'}';
    final hasPaid = h['residual'] != null;
    final residual = (h['residual'] as num?)?.toDouble() ?? 0;
    return Column(children: [
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            gradient: LinearGradient(
                colors: [widget.accent.withValues(alpha: 0.10), widget.accent.withValues(alpha: 0.03)],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: widget.accent.withValues(alpha: 0.18))),
        child: Column(children: [
          Row(children: [
            Expanded(child: _kpiCell(tr('الإجمالي', 'Total'), m(h['total']), widget.accent, big: true)),
            Container(width: 1, height: 40, color: Colors.black.withValues(alpha: 0.08)),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              _miniKV(tr('قبل الضريبة', 'Untaxed'), m(h['untaxed'])),
              const SizedBox(height: 4),
              _miniKV(tr('الضريبة', 'Tax'), m(h['tax'])),
            ])),
          ]),
          if (hasPaid) ...[
            const Divider(height: 20),
            Row(children: [
              Expanded(child: _kpiCell(tr('المدفوع', 'Paid'), m(h['paid']), const Color(0xFF16A34A))),
              Container(width: 1, height: 34, color: Colors.black.withValues(alpha: 0.08)),
              const SizedBox(width: 10),
              Expanded(child: _kpiCell(tr('المتبقّي', 'Residual'), m(h['residual']),
                  residual > 0 ? Mgmt.red : const Color(0xFF16A34A))),
            ]),
          ],
          if (st.isNotEmpty) ...[
            const SizedBox(height: 12),
            Wrap(spacing: 8, runSpacing: 8, children: [
              if (st['recv_ar'] != null)
                _statusPill('🚚', gLang == 'en' ? '${st['recv_en']}' : '${st['recv_ar']}', mgmtHex('${st['recv_color']}', Mgmt.slate)),
              if (st['inv_ar'] != null)
                _statusPill('🧾', gLang == 'en' ? '${st['inv_en']}' : '${st['inv_ar']}', mgmtHex('${st['inv_color']}', Mgmt.slate)),
              if (st['pay_label'] != null)
                _statusPill('💳', '${st['pay_label']}', mgmtHex('${st['pay_color']}', Mgmt.slate)),
            ]),
          ],
        ]),
      ),
      // ---- send-to-vendor + edit (purchase orders)
      if (widget.appKey == 'purchases')
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 0),
          child: Row(children: [
            if (o['can_send'] == true) ...[
              Expanded(
                child: SizedBox(
                  height: 46,
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF16A34A), foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
                    onPressed: _busy ? null : _sendPo,
                    icon: const Icon(Icons.send_rounded, size: 17),
                    label: Text(tr('إرسال', 'Send'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13)),
                  ),
                ),
              ),
              const SizedBox(width: 8),
            ],
            Expanded(
              child: SizedBox(
                height: 46,
                child: OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                      foregroundColor: widget.accent, side: BorderSide(color: widget.accent),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
                  onPressed: _busy ? null : _editPo,
                  icon: const Icon(Icons.edit_rounded, size: 17),
                  label: Text(tr('تعديل', 'Edit'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13)),
                ),
              ),
            ),
          ]),
        ),
      // ---- delivery + invoice tabs (purchase orders)
      if ((o['tabs'] as List?)?.isNotEmpty == true)
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 0),
          child: Row(children: [
            for (final tab in (o['tabs'] as List).cast<Map>()) ...[
              Expanded(
                child: Material(
                  color: widget.accent.withValues(alpha: 0.06),
                  borderRadius: BorderRadius.circular(14),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(14),
                    onTap: _busy ? null : () => _openPoTab('${tab['code']}', gLang == 'en' ? '${tab['en']}' : '${tab['ar']}'),
                    child: Container(
                      margin: const EdgeInsets.symmetric(horizontal: 3),
                      padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 8),
                      decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: widget.accent.withValues(alpha: 0.16))),
                      child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                        Text('${tab['icon']}', style: const TextStyle(fontSize: 20)),
                        const SizedBox(width: 8),
                        Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text(gLang == 'en' ? '${tab['en']}' : '${tab['ar']}',
                              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 11.5, color: Mgmt.ink)),
                          Text('${tab['count']}', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: widget.accent)),
                        ]),
                      ]),
                    ),
                  ),
                ),
              ),
            ],
          ]),
        ),
      if (info.isNotEmpty)
        _cardWrap([
          _sectionHead('🏢', tr('بيانات الطرف والتفاصيل', 'Partner & details')),
          _infoRows(info),
        ]),
    ]);
  }

  Future<void> _openPoTab(String code, String label) async {
    if (code == 'deliveries') return _openDeliveries(label);
    return _openPoInvoices(label);
  }

  Future<void> _sendPo() async {
    // choose recipient: vendor (default) or pick another
    final choice = await showModalBottomSheet<String>(
      context: context, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => SafeArea(child: Column(mainAxisSize: MainAxisSize.min, children: [
        Padding(padding: const EdgeInsets.all(16),
            child: Text(tr('إرسال أمر الشراء إلى', 'Send purchase order to'),
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15))),
        ListTile(
          leading: const Icon(Icons.storefront_rounded, color: Color(0xFF16A34A)),
          title: Text(tr('المورّد', 'The vendor')),
          subtitle: Text('${(d['order'] as Map?)?['send_email'] ?? ''}'),
          onTap: () => Navigator.pop(context, 'vendor')),
        ListTile(
          leading: Icon(Icons.person_search_rounded, color: widget.accent),
          title: Text(tr('اختيار مستلم آخر', 'Choose another recipient')),
          onTap: () => Navigator.pop(context, 'other')),
        const SizedBox(height: 8),
      ])),
    );
    if (choice == null || !mounted) return;
    String? email;
    if (choice == 'other') {
      Map<String, dynamic> rec;
      try {
        rec = await context.read<AuthProvider>().api.managementPoRecipients();
      } catch (e) {
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
        return;
      }
      if (!mounted) return;
      final opts = ((rec['recipients'] as List?) ?? const [])
          .map((e) => {'v': e['v'], 'l': '${e['l']}  ·  ${e['email']}', 'email': e['email']}).toList().cast<Map>();
      final pickedEmail = await showModalBottomSheet<String>(
        context: context, isScrollControlled: true, backgroundColor: Colors.white,
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
        builder: (_) => _RecipientPicker(options: opts, accent: widget.accent),
      );
      if (pickedEmail == null || !mounted) return;
      email = pickedEmail;
    }
    setState(() => _busy = true);
    try {
      final res = await context.read<AuthProvider>().api.managementPoSend(d['id'] as int, email: email);
      if (!mounted) return;
      await _reload();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('✅ أُرسل إلى ${res['email']}', '✅ Sent to ${res['email']}')),
          backgroundColor: const Color(0xFF16A34A)));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _editPo() async {
    final saved = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _PoFormSheet(accent: widget.accent, editId: d['id'] as int),
    );
    if (saved == true && mounted) {
      await _reload();
      widget.onChanged();
    }
  }

  Future<void> _openDeliveries(String label) async {
    setState(() => _busy = true);
    Map<String, dynamic>? res;
    try {
      res = await context.read<AuthProvider>().api.managementPoDeliveries(d['id'] as int);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
    if (res == null || !mounted) return;
    await showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _DeliveriesSheet(
          poId: d['id'] as int, accent: widget.accent, initial: res!, onChanged: _reload),
    );
  }

  Future<void> _openPoInvoices(String label) async {
    setState(() => _busy = true);
    Map<String, dynamic>? res;
    try {
      res = await context.read<AuthProvider>().api.managementPoInvoices(d['id'] as int);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
    if (res == null || !mounted) return;
    final invoices = (res['invoices'] as List?) ?? const [];
    await showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.7, maxChildSize: 0.95, minChildSize: 0.4,
        builder: (_, sc) => Column(children: [
          _sheetHeader('🧾 ${tr('الفواتير', 'Invoices')} · ${invoices.length}'),
          Expanded(
            child: invoices.isEmpty
                ? Center(child: Text(tr('لا فواتير', 'No invoices'), style: const TextStyle(color: Mgmt.slate, fontWeight: FontWeight.w700)))
                : ListView.separated(
                    controller: sc, padding: const EdgeInsets.all(12),
                    itemCount: invoices.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (_, i) {
                      final inv = invoices[i] as Map;
                      final cur = '${inv['currency'] ?? ''}';
                      return Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                            color: Mgmt.bg, borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: Colors.black.withValues(alpha: 0.05))),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Row(children: [
                            Expanded(child: Text('${inv['name']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Mgmt.ink))),
                            Text('${(inv['amount'] as num?)?.toStringAsFixed(3) ?? '0'} $cur',
                                style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: widget.accent)),
                          ]),
                          const SizedBox(height: 6),
                          Wrap(spacing: 6, runSpacing: 6, children: [
                            mgmtStateChip(inv),
                            if (inv['payment'] != null)
                              _statusPill('💳', '${inv['payment']}', mgmtHex('${inv['payment_color']}', Mgmt.slate)),
                            if ((inv['residual'] as num?) != null && (inv['residual'] as num) > 0)
                              _statusPill('⏳', '${tr('متبقّي', 'Due')} ${(inv['residual'] as num).toStringAsFixed(3)} $cur', Mgmt.red),
                            if (inv['date'] != null) _statusPill('📅', '${'${inv['date']}'.split(' ').first}', Mgmt.slate),
                          ]),
                        ]),
                      );
                    },
                  ),
          ),
        ]),
      ),
    );
  }

  Widget _sheetHeader(String title) => Container(
        padding: const EdgeInsets.fromLTRB(18, 14, 12, 12),
        decoration: BoxDecoration(
            gradient: LinearGradient(colors: [widget.accent, widget.accent.withValues(alpha: 0.72)],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(22))),
        child: Row(children: [
          Expanded(child: Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15))),
          IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close_rounded, color: Colors.white)),
        ]),
      );

  Widget _miniKV(String k, String v) => Row(children: [
        Expanded(child: Text(k, style: const TextStyle(color: Mgmt.slate, fontSize: 11, fontWeight: FontWeight.w600))),
        Text(v, style: const TextStyle(color: Mgmt.ink, fontSize: 12, fontWeight: FontWeight.w800)),
      ]);

  Widget _statusPill(String icon, String label, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
        decoration: BoxDecoration(
            color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20),
            border: Border.all(color: c.withValues(alpha: 0.34))),
        child: Text('$icon $label', style: TextStyle(color: c, fontSize: 11.5, fontWeight: FontWeight.w800)),
      );

  Widget _fleetBlock() {
    final v = d['fleet'] as Map?;
    if (v == null) return const SizedBox.shrink();
    final specs = (v['service_info'] as List?) ?? (v['specs'] as List?) ?? const [];
    final counts = (v['counts'] as List?) ?? const [];
    final contract = v['contract'] as Map?;
    final img = '${v['image_b64'] ?? ''}';
    return Column(children: [
      // photo banner + plate
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(borderRadius: BorderRadius.circular(18), color: widget.accent.withValues(alpha: 0.06)),
        child: Column(children: [
          SizedBox(
            height: 150, width: double.infinity,
            child: img.isEmpty
                ? Icon(Icons.directions_car_rounded, size: 60, color: widget.accent.withValues(alpha: 0.5))
                : Image.memory(base64Decode(img), fit: BoxFit.cover, gaplessPlayback: true,
                    errorBuilder: (_, __, ___) => Icon(Icons.directions_car_rounded, size: 60, color: widget.accent.withValues(alpha: 0.5))),
          ),
          Padding(
            padding: const EdgeInsets.all(12),
            child: Row(children: [
              if ('${v['plate'] ?? ''}'.isNotEmpty)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(color: Mgmt.ink, borderRadius: BorderRadius.circular(7)),
                  child: Text('🔖 ${v['plate']}',
                      style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w900, letterSpacing: 2)),
                ),
              const Spacer(),
              if (v['model'] != null)
                Flexible(child: Text('${v['model']}', textAlign: TextAlign.end, maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.ink))),
            ]),
          ),
        ]),
      ),
      // contract expiry chip
      if (contract != null && contract['expiry'] != null)
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 0),
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(
                color: mgmtHex('${contract['color']}', Mgmt.slate).withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: mgmtHex('${contract['color']}', Mgmt.slate).withValues(alpha: 0.3))),
            child: Row(children: [
              Icon(Icons.event_available_rounded, size: 17, color: mgmtHex('${contract['color']}', Mgmt.slate)),
              const SizedBox(width: 8),
              Expanded(child: Text(tr('انتهاء العقد', 'Contract expiry'),
                  style: const TextStyle(color: Mgmt.ink, fontSize: 12, fontWeight: FontWeight.w700))),
              Text('${'${contract['expiry']}'.split(' ').first}  ·  ${contract['days']} ${tr('يوم', 'd')}',
                  style: TextStyle(color: mgmtHex('${contract['color']}', Mgmt.slate), fontSize: 12, fontWeight: FontWeight.w900)),
            ]),
          ),
        ),
      // count tiles (tappable → the vehicle's log records)
      if (counts.isNotEmpty)
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 0),
          child: Row(children: [
            for (final ct in counts.cast<Map>()) ...[
              Expanded(
                child: Material(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(13),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(13),
                    onTap: ((ct['count'] as num?) ?? 0) > 0 && !_busy
                        ? () => _openFleetLog('${ct['code']}', gLang == 'en' ? '${ct['en']}' : '${ct['ar']}')
                        : null,
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
                      margin: const EdgeInsets.symmetric(horizontal: 3),
                      decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(13),
                          border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
                      child: Column(children: [
                        Text('${ct['icon']}', style: const TextStyle(fontSize: 18)),
                        const SizedBox(height: 3),
                        Text('${ct['count']}', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: widget.accent)),
                        Text(gLang == 'en' ? '${ct['en']}' : '${ct['ar']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                            style: const TextStyle(color: Mgmt.slate, fontSize: 9.5, fontWeight: FontWeight.w700)),
                      ]),
                    ),
                  ),
                ),
              ),
            ],
          ]),
        ),
      if (specs.isNotEmpty)
        _cardWrap([_sectionHead('🚗', tr('مواصفات المركبة', 'Vehicle specs')), _infoRows(specs)]),
    ]);
  }

  Widget _crmBlock() {
    final c = d['crm'] as Map?;
    if (c == null) return const SizedBox.shrink();
    final h = (c['header'] as Map?) ?? const {};
    final info = (c['service_info'] as List?) ?? const [];
    final cur = '${h['currency'] ?? ''}';
    final prob = (h['probability'] as num?)?.toDouble() ?? 0;
    final stageColor = mgmtHex('${h['stage_color'] ?? ''}', widget.accent);
    final probColor = prob >= 70 ? const Color(0xFF16A34A) : (prob >= 40 ? const Color(0xFFF59E0B) : Mgmt.slate);
    return Column(children: [
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            gradient: LinearGradient(
                colors: [widget.accent.withValues(alpha: 0.10), widget.accent.withValues(alpha: 0.03)],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: widget.accent.withValues(alpha: 0.18))),
        child: Row(children: [
          Expanded(child: _kpiCell(tr('الإيراد المتوقع', 'Expected revenue'),
              '${(h['expected'] as num?)?.toStringAsFixed(3) ?? '0'}${cur.isEmpty ? '' : ' $cur'}', widget.accent, big: true)),
          Container(width: 1, height: 40, color: Colors.black.withValues(alpha: 0.08)),
          const SizedBox(width: 12),
          Column(mainAxisSize: MainAxisSize.min, children: [
            _pctRing(prob, probColor),
            const SizedBox(height: 4),
            Text('${prob.toStringAsFixed(0)}%', style: TextStyle(color: probColor, fontWeight: FontWeight.w900, fontSize: 12)),
          ]),
        ]),
      ),
      if (h['stage'] != null)
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 0),
          child: Align(
            alignment: AlignmentDirectional.centerStart,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(
                  color: stageColor.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: stageColor.withValues(alpha: 0.34))),
              child: Text('🎯 ${h['stage']}', style: TextStyle(color: stageColor, fontSize: 12, fontWeight: FontWeight.w800)),
            ),
          ),
        ),
      if (info.isNotEmpty)
        _cardWrap([_sectionHead('📇', tr('بيانات الفرصة والتواصل', 'Opportunity & contact')), _infoRows(info)]),
    ]);
  }

  Widget _leaveBlock() {
    final lv = d['leave'] as Map?;
    if (lv == null) return const SizedBox.shrink();
    final info = (lv['service_info'] as List?) ?? const [];
    final photo = '${lv['photo_b64'] ?? ''}';
    return Column(children: [
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            gradient: LinearGradient(
                colors: [widget.accent.withValues(alpha: 0.10), widget.accent.withValues(alpha: 0.03)],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: widget.accent.withValues(alpha: 0.18))),
        child: Row(children: [
          if (photo.isNotEmpty)
            ClipRRect(borderRadius: BorderRadius.circular(30),
                child: Image.memory(base64Decode(photo), width: 54, height: 54, fit: BoxFit.cover, gaplessPlayback: true)),
          if (photo.isNotEmpty) const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Text('${lv['employee'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: Mgmt.ink)),
            if (lv['leave_type'] != null)
              Padding(padding: const EdgeInsets.only(top: 2),
                  child: Text('🌴 ${lv['leave_type']}', style: const TextStyle(color: Mgmt.slate, fontSize: 12, fontWeight: FontWeight.w600))),
          ])),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Text('${lv['days'] ?? 0}', style: TextStyle(color: widget.accent, fontWeight: FontWeight.w900, fontSize: 22)),
            Text(tr('يوم', 'days'), style: const TextStyle(color: Mgmt.slate, fontSize: 10.5, fontWeight: FontWeight.w700)),
          ]),
        ]),
      ),
      Container(
        margin: const EdgeInsets.fromLTRB(14, 10, 14, 0),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
            color: Colors.white, borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
        child: Row(children: [
          Expanded(child: _dateChip('📅', tr('من', 'From'), '${lv['date_from'] ?? ''}'.split(' ').first)),
          const Icon(Icons.arrow_forward_rounded, size: 16, color: Mgmt.slate),
          Expanded(child: Align(alignment: AlignmentDirectional.centerEnd,
              child: _dateChip('🏁', tr('إلى', 'To'), '${lv['date_to'] ?? ''}'.split(' ').first))),
        ]),
      ),
      if (info.isNotEmpty)
        _cardWrap([_sectionHead('📋', tr('تفاصيل الإجازة', 'Leave details')), _infoRows(info)]),
    ]);
  }

  Future<void> _openExpLog(String code, String label) async {
    setState(() => _busy = true);
    Map<String, dynamic>? res;
    try {
      res = await context.read<AuthProvider>().api.managementExperienceLog(d['id'] as int, code);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
    if (res == null || !mounted) return;
    await _showLines(label, (res['lines'] as List?) ?? const []);
  }

  Widget _experienceBlock() {
    final x = d['experience'] as Map?;
    if (x == null) return const SizedBox.shrink();
    final exp = (x['expiry'] as Map?) ?? const {};
    final info = (x['service_info'] as List?) ?? const [];
    final refs = (x['refs'] as List?) ?? const [];
    final tabs = (x['tabs'] as List?) ?? const [];
    final expColor = mgmtHex('${exp['color'] ?? ''}', Mgmt.slate);
    final days = (x['days_to_expiry'] as num?)?.toInt() ?? 0;
    return Column(children: [
      // expiry + renewed banner
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            gradient: LinearGradient(
                colors: [expColor.withValues(alpha: 0.12), expColor.withValues(alpha: 0.03)],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: expColor.withValues(alpha: 0.25))),
        child: Row(children: [
          Icon(days >= 0 ? Icons.verified_rounded : Icons.error_rounded, color: expColor, size: 30),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(days >= 0 ? tr('متبقٍ على الانتهاء', 'Time to expiry') : tr('العقد منتهٍ', 'Contract expired'),
                style: const TextStyle(color: Mgmt.slate, fontSize: 11.5, fontWeight: FontWeight.w700)),
            Text(days >= 0 ? tr('$days يوم', '$days days') : tr('منذ ${-days} يوم', '${-days} days ago'),
                style: TextStyle(color: expColor, fontWeight: FontWeight.w900, fontSize: 19)),
          ])),
          if (x['is_renewed'] == true)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(color: const Color(0xFFF59E0B).withValues(alpha: 0.15), borderRadius: BorderRadius.circular(20)),
              child: Text('🔄 ${tr('ممدّد', 'Renewed')}', style: const TextStyle(color: Color(0xFFB45309), fontSize: 11, fontWeight: FontWeight.w900)),
            ),
        ]),
      ),
      // source references (proposal / tender) — openable
      if (refs.isNotEmpty)
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 0),
          child: Row(children: [
            for (final ref in refs.cast<Map>()) ...[
              Expanded(
                child: Material(
                  color: widget.accent.withValues(alpha: 0.06),
                  borderRadius: BorderRadius.circular(13),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(13),
                    onTap: () => openManagementRecord(context, '${ref['key']}', ref['id'] as int, title: '${ref['name']}', accent: widget.accent),
                    child: Container(
                      margin: const EdgeInsets.symmetric(horizontal: 3),
                      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 10),
                      decoration: BoxDecoration(borderRadius: BorderRadius.circular(13), border: Border.all(color: widget.accent.withValues(alpha: 0.16))),
                      child: Row(children: [
                        Text('${ref['icon']} ', style: const TextStyle(fontSize: 17)),
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                          Text(gLang == 'en' ? '${ref['en']}' : '${ref['ar']}', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 11, color: widget.accent)),
                          Text('${ref['name']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 10, color: Mgmt.slate)),
                        ])),
                        const Icon(Icons.chevron_left_rounded, size: 16, color: Mgmt.slate),
                      ]),
                    ),
                  ),
                ),
              ),
            ],
          ]),
        ),
      // renewals / guarantees / lines tabs
      if (tabs.isNotEmpty)
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 0),
          child: Row(children: [
            for (final tab in tabs.cast<Map>()) ...[
              Expanded(
                child: Material(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(13),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(13),
                    onTap: ((tab['count'] as num?) ?? 0) > 0 && !_busy
                        ? () => _openExpLog('${tab['code']}', gLang == 'en' ? '${tab['en']}' : '${tab['ar']}')
                        : null,
                    child: Container(
                      margin: const EdgeInsets.symmetric(horizontal: 3),
                      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
                      decoration: BoxDecoration(borderRadius: BorderRadius.circular(13), border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
                      child: Column(children: [
                        Text('${tab['icon']}', style: const TextStyle(fontSize: 18)),
                        const SizedBox(height: 3),
                        Text('${tab['count']}', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: widget.accent)),
                        Text(gLang == 'en' ? '${tab['en']}' : '${tab['ar']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                            style: const TextStyle(color: Mgmt.slate, fontSize: 9.5, fontWeight: FontWeight.w700)),
                      ]),
                    ),
                  ),
                ),
              ),
            ],
          ]),
        ),
      if (info.isNotEmpty)
        _cardWrap([_sectionHead('📄', tr('بيانات العقد', 'Contract details')), _infoRows(info)]),
    ]);
  }

  IconData _fileIcon(Map f) {
    if (f['is_image'] == true) return Icons.image_rounded;
    if (f['is_pdf'] == true) return Icons.picture_as_pdf_rounded;
    if (f['url'] != null) return Icons.link_rounded;
    return Icons.insert_drive_file_rounded;
  }

  Color _fileColor(Map f) {
    if (f['is_image'] == true) return const Color(0xFF0EA5E9);
    if (f['is_pdf'] == true) return Mgmt.red;
    return widget.accent;
  }

  Future<void> _openDocFile(Map f) async {
    final id = f['att_id'];
    if (f['is_image'] == true && id != null) {
      final url = _token == null ? '${f['att_url']}' : '${f['att_url']}?token=$_token';
      Navigator.push(context, MaterialPageRoute(builder: (_) => MediaViewerScreen(
          media: [{'url': url, 'name': f['name'], 'type': 'image'}], token: _token)));
    } else if (id != null) {
      Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
          path: '/api/v1/management/attachment/$id', title: '${f['name']}', fileName: '${f['name']}')));
    } else if (f['url'] != null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('${f['url']}')));
    }
  }

  Widget _approvalBlock() {
    final ap = d['approval'] as Map?;
    if (ap == null) return const SizedBox.shrink();
    final info = (ap['service_info'] as List?) ?? const [];
    final approvers = (ap['approvers'] as List?) ?? const [];
    return Column(children: [
      if (info.isNotEmpty)
        _cardWrap([_sectionHead('📋', tr('بيانات الطلب', 'Request details')), _infoRows(info)]),
      if (approvers.isNotEmpty)
        _cardWrap([
          _sectionHead('✍️', tr('المعتمدون', 'Approvers')),
          for (final a in approvers.cast<Map>())
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
              child: Row(children: [
                Icon(Icons.account_circle_rounded, size: 20, color: Mgmt.slate),
                const SizedBox(width: 8),
                Expanded(child: Text('${a['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: Mgmt.ink))),
                if (a['status'] != null) mgmtStateChip(a),
              ]),
            ),
        ]),
    ]);
  }

  Widget _deviceBlock() {
    final dev = d['device'] as Map?;
    if (dev == null) return const SizedBox.shrink();
    final info = (dev['service_info'] as List?) ?? const [];
    final stalled = dev['stalled'] == true;
    final sc = stalled ? Mgmt.red : const Color(0xFF16A34A);
    return Column(children: [
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            color: sc.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(16),
            border: Border.all(color: sc.withValues(alpha: 0.25))),
        child: Row(children: [
          Icon(stalled ? Icons.error_rounded : Icons.fingerprint_rounded, color: sc, size: 32),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(stalled ? tr('الجهاز متوقّف', 'Device stalled') : tr('الجهاز يعمل', 'Device online'),
                style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: sc)),
            Text(tr('استخدم الأزرار لفحص الاتصال أو سحب البصمات', 'Use the buttons to check connection or fetch attendance'),
                style: const TextStyle(color: Mgmt.slate, fontSize: 11)),
          ])),
        ]),
      ),
      if (info.isNotEmpty)
        _cardWrap([_sectionHead('🔌', tr('بيانات الجهاز', 'Device details')), _infoRows(info)]),
    ]);
  }

  Widget _documentBlock() {
    final doc = d['document'] as Map?;
    if (doc == null) return const SizedBox.shrink();
    final f = (doc['file'] as Map?) ?? const {};
    final info = (doc['service_info'] as List?) ?? const [];
    final fc = _fileColor(f);
    final canOpen = f['att_id'] != null || f['url'] != null;
    return Column(children: [
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
            color: Colors.white, borderRadius: BorderRadius.circular(18),
            border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
        child: Column(children: [
          // image preview or file-type icon
          if (f['is_image'] == true && f['att_id'] != null && _token != null)
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: Image.network('${f['att_url']}?token=$_token',
                  height: 180, width: double.infinity, fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => Icon(_fileIcon(f), size: 64, color: fc)),
            )
          else
            Container(
              height: 120, width: double.infinity, alignment: Alignment.center,
              decoration: BoxDecoration(color: fc.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(12)),
              child: Icon(_fileIcon(f), size: 56, color: fc),
            ),
          const SizedBox(height: 12),
          Text('${f['name'] ?? ''}', textAlign: TextAlign.center, maxLines: 3, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5, color: Mgmt.ink)),
          if (canOpen) ...[
            const SizedBox(height: 12),
            SizedBox(
              width: double.infinity, height: 46,
              child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(backgroundColor: fc, foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
                onPressed: () => _openDocFile(f),
                icon: const Icon(Icons.open_in_new_rounded, size: 18),
                label: Text(tr('فتح الملف', 'Open file'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5)),
              ),
            ),
          ],
          // Share row — like the backend: apps / email / copy link.
          const SizedBox(height: 10),
          Row(children: [
            Expanded(child: _shareBtn(Icons.ios_share_rounded, tr('مشاركة', 'Share'), () => _shareDoc('apps'))),
            const SizedBox(width: 8),
            Expanded(child: _shareBtn(Icons.email_rounded, tr('بريد', 'Email'), () => _shareDoc('email'))),
            const SizedBox(width: 8),
            Expanded(child: _shareBtn(Icons.link_rounded, tr('نسخ الرابط', 'Copy link'), () => _shareDoc('copy'))),
          ]),
        ]),
      ),
      if (info.isNotEmpty)
        _cardWrap([_sectionHead('🗂️', tr('بيانات الوثيقة', 'Document details')), _infoRows(info)]),
    ]);
  }

  Widget _shareBtn(IconData ic, String label, VoidCallback onTap) => OutlinedButton(
        style: OutlinedButton.styleFrom(
            foregroundColor: widget.accent, side: BorderSide(color: widget.accent.withValues(alpha: 0.4)),
            padding: const EdgeInsets.symmetric(vertical: 9),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(11))),
        onPressed: _busy ? null : onTap,
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(ic, size: 18), const SizedBox(height: 3),
          Text(label, style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800)),
        ]),
      );

  Map<String, dynamic>? _shareCache;
  Future<void> _shareDoc(String how) async {
    setState(() => _busy = true);
    try {
      _shareCache ??= await context.read<AuthProvider>().api.managementDocumentShare(d['id'] as int);
      final link = '${_shareCache!['share_url'] ?? _shareCache!['download_url'] ?? ''}';
      final name = '${_shareCache!['name'] ?? tr('مستند', 'Document')}';
      if (link.isEmpty) {
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تعذّر إنشاء رابط', 'Could not create a link'))));
        return;
      }
      if (how == 'copy') {
        await Clipboard.setData(ClipboardData(text: link));
        if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(tr('نُسخ الرابط', 'Link copied')), backgroundColor: const Color(0xFF16A34A)));
      } else if (how == 'email') {
        final uri = Uri(scheme: 'mailto', query: 'subject=${Uri.encodeComponent(name)}&body=${Uri.encodeComponent('$name\n$link')}');
        await launchUrl(uri, mode: LaunchMode.externalApplication);
      } else {
        await Share.share('$name\n$link', subject: name);
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _reqinvBlock() {
    final ri = d['reqinv'] as Map?;
    if (ri == null) return const SizedBox.shrink();
    final h = (ri['header'] as Map?) ?? const {};
    final st = (ri['status'] as Map?) ?? const {};
    final refs = (ri['refs'] as List?) ?? const [];
    final lines = (ri['lines'] as List?) ?? const [];
    final info = (ri['service_info'] as List?) ?? const [];
    final cur = '${h['currency'] ?? ''}';
    final money = cur.isEmpty ? '' : ' $cur';
    return Column(children: [
      // financial header + status
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            gradient: LinearGradient(colors: [widget.accent.withValues(alpha: 0.10), widget.accent.withValues(alpha: 0.03)], begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(18), border: Border.all(color: widget.accent.withValues(alpha: 0.18))),
        child: Column(children: [
          Row(children: [
            Expanded(child: _kpiCell(tr('قيمة الطلب', 'Request value'),
                '${(h['amount'] as num?)?.toStringAsFixed(3) ?? '0'}$money', widget.accent, big: true)),
          ]),
          if (st.isNotEmpty) ...[
            const SizedBox(height: 12),
            Wrap(spacing: 8, runSpacing: 8, children: [
              if ((st['invoice_count'] as num?) != null && (st['invoice_count'] as num) > 0)
                _statusPill('📄', '${st['invoice_count']} ${tr('فاتورة', 'invoices')}', const Color(0xFF16A34A)),
              _statusPill(st['delivered'] == true ? '🚚' : '📦',
                  st['delivered'] == true ? tr('مُسلّمة', 'Delivered') : tr('غير مُسلّمة', 'Not delivered'),
                  st['delivered'] == true ? const Color(0xFF16A34A) : Mgmt.slate),
            ]),
          ],
        ]),
      ),
      // source refs (proposal / contract / project) — openable
      if (refs.isNotEmpty)
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 0),
          child: Row(children: [
            for (final ref in refs.cast<Map>()) ...[
              Expanded(
                child: Material(
                  color: widget.accent.withValues(alpha: 0.06), borderRadius: BorderRadius.circular(13),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(13),
                    onTap: () => openManagementRecord(context, '${ref['key']}', ref['id'] as int, title: '${ref['name']}', accent: widget.accent),
                    child: Container(
                      margin: const EdgeInsets.symmetric(horizontal: 3),
                      padding: const EdgeInsets.symmetric(vertical: 11, horizontal: 8),
                      decoration: BoxDecoration(borderRadius: BorderRadius.circular(13), border: Border.all(color: widget.accent.withValues(alpha: 0.16))),
                      child: Column(mainAxisSize: MainAxisSize.min, children: [
                        Text('${ref['icon']}', style: const TextStyle(fontSize: 17)),
                        const SizedBox(height: 3),
                        Text(gLang == 'en' ? '${ref['en']}' : '${ref['ar']}', style: TextStyle(fontWeight: FontWeight.w800, fontSize: 10.5, color: widget.accent)),
                        Text('${ref['name']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 9, color: Mgmt.slate)),
                      ]),
                    ),
                  ),
                ),
              ),
            ],
          ]),
        ),
      // lines
      if (lines.isNotEmpty)
        _cardWrap([
          _sectionHead('🧾', tr('بنود الطلب', 'Request lines')),
          for (final l in lines.cast<Map>())
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
              child: Row(children: [
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${l['name']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12, color: Mgmt.ink)),
                  if (l['qty'] != null || l['days'] != null || l['price'] != null)
                    Text([
                      if (l['qty'] != null) '${tr('كمية', 'Qty')}: ${l['qty']}',
                      if (l['days'] != null && (l['days'] as num) > 0) '${tr('أيام', 'Days')}: ${l['days']}',
                      if (l['price'] != null) '${tr('سعر', 'Price')}: ${l['price']}',
                    ].join('  ·  '), style: const TextStyle(fontSize: 10, color: Mgmt.slate)),
                ])),
                if (l['subtotal'] != null)
                  Text('${(l['subtotal'] as num).toStringAsFixed(3)}$money', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: widget.accent)),
              ]),
            ),
        ]),
      if (info.isNotEmpty)
        _cardWrap([_sectionHead('📋', tr('بيانات الطلب', 'Request details')), _infoRows(info)]),
    ]);
  }

  // ---- Fuel tanks (petrol.tank) -----------------------------------------
  String _num(dynamic v) {
    final n = v is num ? v : double.tryParse('$v') ?? 0;
    return n == n.roundToDouble() ? n.toInt().toString() : n.toStringAsFixed(1);
  }

  Widget _petrolBlock() {
    final p = d['petrol'] as Map?;
    if (p == null) return const SizedBox.shrink();
    final h = (p['header'] as Map?) ?? const {};
    final charges = ((p['charges'] as List?) ?? const []).cast<Map>();
    final uses = ((p['uses'] as List?) ?? const []).cast<Map>();
    final transfers = ((p['transfers'] as List?) ?? const []).cast<Map>();
    final progress = (numOf(h['progress'], 0)).toDouble().clamp(0, 100).toDouble();
    final barColor = progress < 20 ? const Color(0xFFDC2626) : (progress < 50 ? const Color(0xFFF59E0B) : const Color(0xFF16A34A));
    final canEdit = d['can_edit'] != false;
    Widget kpi(String ar, String en, dynamic v, Color c) => Expanded(child: Column(children: [
          Text(_num(v), style: TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: c)),
          Text(gLang == 'en' ? en : ar, textAlign: TextAlign.center, style: const TextStyle(fontSize: 9.5, color: Mgmt.slate)),
        ]));
    return Column(children: [
      // gauge header
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            gradient: LinearGradient(colors: [barColor.withValues(alpha: 0.10), barColor.withValues(alpha: 0.03)], begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(18), border: Border.all(color: barColor.withValues(alpha: 0.18))),
        child: Column(children: [
          Row(children: [
            const Text('⛽', style: TextStyle(fontSize: 22)),
            const SizedBox(width: 8),
            Expanded(child: Text('${_num(h['balance'])} / ${_num(h['capacity'])} ${tr('لتر', 'L')}',
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: Mgmt.ink))),
            Text('${progress.toInt()}%', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: barColor)),
          ]),
          const SizedBox(height: 10),
          ClipRRect(borderRadius: BorderRadius.circular(7),
              child: LinearProgressIndicator(value: progress / 100, minHeight: 10, backgroundColor: Colors.white, valueColor: AlwaysStoppedAnimation(barColor))),
          const SizedBox(height: 12),
          Row(children: [
            kpi('مشحون', 'Charged', h['charged'], const Color(0xFF16A34A)),
            kpi('مصروف', 'Used', h['used'], const Color(0xFFDC2626)),
            kpi('وارد', 'In', h['incoming'], const Color(0xFF0EA5E9)),
            kpi('صادر', 'Out', h['outgoing'], const Color(0xFFF59E0B)),
          ]),
        ]),
      ),
      // add buttons
      if (canEdit)
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 0),
          child: Row(children: [
            Expanded(child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFF16A34A), side: const BorderSide(color: Color(0xFF16A34A)), padding: const EdgeInsets.symmetric(vertical: 10)),
              onPressed: _busy ? null : _addPetrolCharge,
              icon: const Icon(Icons.add_rounded, size: 17), label: Text(tr('شحنة', 'Charge'), style: const TextStyle(fontWeight: FontWeight.w800)))),
            const SizedBox(width: 8),
            Expanded(child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFDC2626), side: const BorderSide(color: Color(0xFFDC2626)), padding: const EdgeInsets.symmetric(vertical: 10)),
              onPressed: _busy ? null : _addPetrolUse,
              icon: const Icon(Icons.remove_rounded, size: 17), label: Text(tr('صرف', 'Use'), style: const TextStyle(fontWeight: FontWeight.w800)))),
          ]),
        ),
      // charges
      if (charges.isNotEmpty)
        _cardWrap([
          _sectionHead('🛢️', tr('الشحنات (${charges.length})', 'Charges (${charges.length})')),
          for (final c in charges.take(20))
            _petrolLine('${c['name'] ?? ''}', c['date'], '+${_num(c['quantity'])} ${tr('لتر', 'L')}',
                c['cost'] != null && (c['cost'] as num) > 0 ? '${_num(c['cost'])} ${tr('د.ك', 'KWD')}' : null, const Color(0xFF16A34A)),
        ]),
      // uses
      if (uses.isNotEmpty)
        _cardWrap([
          _sectionHead('🚗', tr('عمليات الصرف (${uses.length})', 'Uses (${uses.length})')),
          for (final u in uses.take(20))
            _petrolLine('${u['vehicle'] ?? u['name'] ?? ''}', u['datetime'], '-${_num(u['quantity'])} ${tr('لتر', 'L')}',
                u['rate'] != null && (u['rate'] as num) > 0 ? '${_num(u['rate'])} ${tr('ل/كم', 'L/km')}' : (u['odometer'] != null ? '${_num(u['odometer'])} ${tr('كم', 'km')}' : null),
                const Color(0xFFDC2626)),
        ]),
      // transfers
      if (transfers.isNotEmpty)
        _cardWrap([
          _sectionHead('🔄', tr('التحويلات (${transfers.length})', 'Transfers (${transfers.length})')),
          for (final t in transfers.take(20))
            _petrolLine('${t['from'] ?? '—'} → ${t['to'] ?? '—'}', t['date'], '${_num(t['quantity'])} ${tr('لتر', 'L')}',
                '${t['state']}', const Color(0xFF0EA5E9)),
        ]),
    ]);
  }

  Widget _petrolLine(String title, dynamic date, String amount, String? sub, Color c) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
        child: Row(children: [
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: Mgmt.ink)),
            if (date != null) Text('$date', style: const TextStyle(fontSize: 10.5, color: Mgmt.slate)),
          ])),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Text(amount, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: c)),
            if (sub != null) Text(sub, style: const TextStyle(fontSize: 10, color: Mgmt.slate)),
          ]),
        ]),
      );

  Future<void> _addPetrolCharge() async {
    final qty = TextEditingController();
    final cost = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      title: Text(tr('شحن الخزان', 'Charge tank'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
      content: Column(mainAxisSize: MainAxisSize.min, children: [
        TextField(controller: qty, autofocus: true, keyboardType: TextInputType.number,
            decoration: InputDecoration(labelText: tr('الكمية (لتر) *', 'Quantity (L) *'), border: const OutlineInputBorder())),
        const SizedBox(height: 10),
        TextField(controller: cost, keyboardType: TextInputType.number,
            decoration: InputDecoration(labelText: tr('التكلفة', 'Cost'), border: const OutlineInputBorder())),
      ]),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFF16A34A)),
            onPressed: () => Navigator.pop(c, true), child: Text(tr('حفظ', 'Save'))),
      ]));
    if (ok != true || qty.text.trim().isEmpty) return;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.managementPetrolCharge(d['id'] as int, {
        'quantity': double.tryParse(qty.text.trim()) ?? 0,
        'cost': double.tryParse(cost.text.trim()) ?? 0,
      });
      await _reload();
      widget.onChanged();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('✅ سُجّلت الشحنة', '✅ Charge added')), backgroundColor: const Color(0xFF16A34A)));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _addPetrolUse() async {
    final qty = TextEditingController();
    final odo = TextEditingController();
    Map? vehicle;
    final ok = await showDialog<bool>(context: context, builder: (c) => StatefulBuilder(builder: (c, setD) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      title: Text(tr('صرف وقود', 'Record fuel use'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
      content: Column(mainAxisSize: MainAxisSize.min, children: [
        InkWell(
          onTap: () async {
            final picked = await showModalBottomSheet<Map>(context: context, isScrollControlled: true, backgroundColor: Colors.white,
              shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
              builder: (_) => RelationSearchSheet(model: 'fleet.vehicle', title: tr('اختر المركبة', 'Select vehicle'), accent: widget.accent));
            if (picked != null) setD(() => vehicle = picked);
          },
          child: InputDecorator(
            decoration: InputDecoration(labelText: tr('المركبة', 'Vehicle'), border: const OutlineInputBorder()),
            child: Text(vehicle == null ? tr('اختر…', 'Select…') : '${vehicle!['l']}', style: const TextStyle(fontSize: 13)))),
        const SizedBox(height: 10),
        TextField(controller: qty, keyboardType: TextInputType.number,
            decoration: InputDecoration(labelText: tr('الكمية (لتر) *', 'Quantity (L) *'), border: const OutlineInputBorder())),
        const SizedBox(height: 10),
        TextField(controller: odo, keyboardType: TextInputType.number,
            decoration: InputDecoration(labelText: tr('قراءة العداد', 'Odometer'), border: const OutlineInputBorder())),
      ]),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFFDC2626)),
            onPressed: () => Navigator.pop(c, true), child: Text(tr('حفظ', 'Save'))),
      ])));
    if (ok != true || qty.text.trim().isEmpty) return;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.managementPetrolUse(d['id'] as int, {
        'quantity': double.tryParse(qty.text.trim()) ?? 0,
        'odometer_value': double.tryParse(odo.text.trim()) ?? 0,
        if (vehicle != null) 'vehicle_id': vehicle!['v'],
      });
      await _reload();
      widget.onChanged();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('✅ سُجّل الصرف', '✅ Use recorded')), backgroundColor: const Color(0xFF16A34A)));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  // ---- Passports (care.passport) ----------------------------------------
  Widget _passportBlock() {
    final p = d['passport'] as Map?;
    if (p == null) return const SizedBox.shrink();
    final h = (p['header'] as Map?) ?? const {};
    final info = ((p['info'] as List?) ?? const []).cast<Map>();
    final moves = ((p['movements'] as List?) ?? const []).cast<Map>();
    final isOut = h['state'] == 'out';
    final exColor = mgmtHex('${h['expiry_color'] ?? ''}', Mgmt.slate);
    final canEdit = d['can_edit'] != false;
    return Column(children: [
      // status header
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            gradient: LinearGradient(colors: [exColor.withValues(alpha: 0.10), exColor.withValues(alpha: 0.03)], begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(18), border: Border.all(color: exColor.withValues(alpha: 0.18))),
        child: Row(children: [
          const Text('🛂', style: TextStyle(fontSize: 24)),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${h['passport_no'] ?? '—'}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: Mgmt.ink)),
            const SizedBox(height: 3),
            Wrap(spacing: 6, children: [
              _statusPill('📄', gLang == 'en' ? '${h['state_en']}' : '${h['state_ar']}', mgmtHex('${h['state_color'] ?? ''}', Mgmt.slate)),
              _statusPill('⏰', '${gLang == 'en' ? h['expiry_en'] : h['expiry_ar']}${h['expiry_date'] != null ? ' · ${h['expiry_date']}' : ''}', exColor),
            ]),
          ])),
        ]),
      ),
      // check-in / check-out
      if (canEdit)
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 10, 14, 0),
          child: isOut
              ? SizedBox(width: double.infinity, child: FilledButton.icon(
                  style: FilledButton.styleFrom(backgroundColor: const Color(0xFF16A34A), minimumSize: const Size(0, 46)),
                  onPressed: _busy ? null : _passportCheckin,
                  icon: const Icon(Icons.login_rounded, size: 18),
                  label: Text(tr('إرجاع للأرشيف', 'Return to archive'), style: const TextStyle(fontWeight: FontWeight.w900))))
              : SizedBox(width: double.infinity, child: FilledButton.icon(
                  style: FilledButton.styleFrom(backgroundColor: const Color(0xFFF59E0B), minimumSize: const Size(0, 46)),
                  onPressed: _busy ? null : _passportCheckout,
                  icon: const Icon(Icons.logout_rounded, size: 18),
                  label: Text(tr('إخراج الجواز', 'Check out'), style: const TextStyle(fontWeight: FontWeight.w900)))),
        ),
      if (info.isNotEmpty)
        _cardWrap([_sectionHead('🛂', tr('بيانات الجواز', 'Passport details')), _infoRows(info)]),
      if (moves.isNotEmpty)
        _cardWrap([
          _sectionHead('🔄', tr('حركات الجواز (${moves.length})', 'Movements (${moves.length})')),
          for (final m in moves.take(20))
            _petrolLine(
                '${m['type_label'] ?? ''}${m['custodian'] != null ? ' · ${m['custodian']}' : ''}',
                m['date'], m['type'] == 'out' ? tr('خروج', 'OUT') : tr('دخول', 'IN'),
                m['shelf'], m['type'] == 'out' ? const Color(0xFFF59E0B) : const Color(0xFF16A34A)),
        ]),
    ]);
  }

  Future<void> _passportCheckout() async {
    final reasons = {'travel_leave': tr('سفر - إجازة', 'Travel - Leave'), 'final_exit': tr('خروج نهائي', 'Final Exit'), 'pro_residency': tr('مندوب - إقامة', 'PRO - Residency')};
    String reason = 'travel_leave';
    final ok = await showDialog<bool>(context: context, builder: (c) => StatefulBuilder(builder: (c, setD) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      title: Text(tr('إخراج الجواز', 'Check out passport'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
      content: Column(mainAxisSize: MainAxisSize.min, children: [
        for (final e in reasons.entries) RadioListTile<String>(
          contentPadding: EdgeInsets.zero, dense: true,
          value: e.key, groupValue: reason, title: Text(e.value, style: const TextStyle(fontSize: 13)),
          onChanged: (v) => setD(() => reason = v!)),
      ]),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFFF59E0B)),
            onPressed: () => Navigator.pop(c, true), child: Text(tr('إخراج', 'Check out'))),
      ])));
    if (ok != true) return;
    await _passportMove('checkout', {'reason': reason});
  }

  Future<void> _passportCheckin() async {
    final shelf = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      title: Text(tr('إرجاع الجواز', 'Return passport'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
      content: TextField(controller: shelf, autofocus: true,
          decoration: InputDecoration(labelText: tr('الموقع/الرف', 'Shelf / location'), border: const OutlineInputBorder())),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFF16A34A)),
            onPressed: () => Navigator.pop(c, true), child: Text(tr('إرجاع', 'Return'))),
      ]));
    if (ok != true) return;
    await _passportMove('checkin', {'shelf_location': shelf.text.trim()});
  }

  Future<void> _passportMove(String dir, Map<String, dynamic> body) async {
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.managementPassportMove(d['id'] as int, dir, body);
      await _reload();
      widget.onChanged();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('✅ تم', '✅ Done')), backgroundColor: const Color(0xFF16A34A)));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  // ---- Legal cases (hr.lawsuit) -----------------------------------------
  Widget _legalBlock() {
    final lg = d['legal'] as Map?;
    if (lg == null) return const SizedBox.shrink();
    final h = (lg['header'] as Map?) ?? const {};
    final parties = ((lg['parties'] as List?) ?? const []).cast<Map>();
    final details = lg['details'];
    final updates = ((lg['updates'] as List?) ?? const []).cast<Map>();
    final sc = mgmtHex('${h['state_color'] ?? ''}', widget.accent);
    final canEdit = d['can_edit'] != false && (d['actions'] != null); // updates gated like edits
    Widget dateChip(String icon, String? label, String? val, Color c) => val == null ? const SizedBox.shrink()
        : Expanded(child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 3),
            padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 6),
            decoration: BoxDecoration(color: c.withValues(alpha: 0.07), borderRadius: BorderRadius.circular(13),
                border: Border.all(color: c.withValues(alpha: 0.16))),
            child: Column(children: [
              Text(icon, style: const TextStyle(fontSize: 15)),
              const SizedBox(height: 3),
              Text(label ?? '', style: const TextStyle(fontSize: 9, color: Mgmt.slate)),
              Text('$val'.split(' ').first, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 10.5, color: c)),
            ]),
          ));
    return Column(children: [
      // case header — code + ref + state + key dates
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            gradient: LinearGradient(colors: [sc.withValues(alpha: 0.10), sc.withValues(alpha: 0.03)], begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(18), border: Border.all(color: sc.withValues(alpha: 0.18))),
        child: Column(children: [
          Row(children: [
            const Text('⚖️', style: TextStyle(fontSize: 20)),
            const SizedBox(width: 8),
            Expanded(child: Text('${h['code'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: Mgmt.ink))),
            if (h['ref_no'] != null) _statusPill('#️⃣', '${h['ref_no']}', sc),
          ]),
          if (h['filing_date'] != null || h['hearing_date'] != null || h['next_appointment'] != null) ...[
            const SizedBox(height: 12),
            Row(children: [
              dateChip('📌', tr('الرفع', 'Filed'), h['filing_date'] as String?, Mgmt.slate),
              dateChip('📅', tr('الجلسة', 'Hearing'), h['hearing_date'] as String?, const Color(0xFFF59E0B)),
              dateChip('⏰', tr('الموعد القادم', 'Next'), h['next_appointment'] as String?, const Color(0xFF0EA5E9)),
            ]),
          ],
        ]),
      ),
      if (parties.isNotEmpty)
        _cardWrap([_sectionHead('👥', tr('أطراف القضية', 'Parties')), _infoRows(parties)]),
      if (details != null && '$details'.trim().isNotEmpty)
        _cardWrap([
          _sectionHead('📝', tr('تفاصيل القضية', 'Case details')),
          Padding(padding: const EdgeInsets.fromLTRB(14, 0, 14, 12),
              child: Text('$details', style: const TextStyle(fontSize: 12.5, color: Mgmt.ink, height: 1.5))),
        ]),
      // updates log (timeline) + add button
      _cardWrap([
        Row(children: [
          Expanded(child: _sectionHead('🗒️', tr('سجل التحديثات', 'Updates log'))),
          if (canEdit) Padding(
            padding: const EdgeInsetsDirectional.only(end: 12),
            child: Material(
              color: widget.accent.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20),
              child: InkWell(
                borderRadius: BorderRadius.circular(20),
                onTap: _busy ? null : _addLegalUpdate,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Icon(Icons.add_rounded, size: 15, color: widget.accent),
                    const SizedBox(width: 3),
                    Text(tr('تحديث', 'Add'), style: TextStyle(color: widget.accent, fontWeight: FontWeight.w800, fontSize: 11)),
                  ]),
                ),
              ),
            ),
          ),
        ]),
        if (updates.isEmpty)
          Padding(padding: const EdgeInsets.fromLTRB(14, 0, 14, 12),
              child: Text(tr('لا توجد تحديثات بعد', 'No updates yet'), style: const TextStyle(color: Mgmt.slate, fontSize: 12))),
        for (var i = 0; i < updates.length; i++) _legalUpdateRow(updates[i], i == updates.length - 1),
      ]),
    ]);
  }

  Widget _legalUpdateRow(Map u, bool last) => Padding(
        padding: const EdgeInsets.fromLTRB(14, 0, 14, 0),
        child: IntrinsicHeight(child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Column(children: [
            Container(width: 11, height: 11, margin: const EdgeInsets.only(top: 3),
                decoration: BoxDecoration(color: widget.accent, shape: BoxShape.circle,
                    border: Border.all(color: widget.accent.withValues(alpha: 0.25), width: 3))),
            if (!last) Expanded(child: Container(width: 2, color: widget.accent.withValues(alpha: 0.18))),
          ]),
          const SizedBox(width: 11),
          Expanded(child: Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text('${u['name'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.ink))),
                if (u['datetime'] != null) Text('${u['datetime']}', style: const TextStyle(fontSize: 10, color: Mgmt.slate)),
              ]),
              if (u['details'] != null && '${u['details']}'.trim().isNotEmpty)
                Padding(padding: const EdgeInsets.only(top: 2),
                    child: Text('${u['details']}', style: const TextStyle(fontSize: 11.5, color: Mgmt.slate, height: 1.4))),
              if (u['partner'] != null)
                Padding(padding: const EdgeInsets.only(top: 2), child: Text('👤 ${u['partner']}', style: const TextStyle(fontSize: 10.5, color: Mgmt.slate))),
            ]),
          )),
        ])),
      );

  Future<void> _addLegalUpdate() async {
    final nameC = TextEditingController();
    final detailsC = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: Text(tr('تحديث جديد على القضية', 'New case update'), style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w900)),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: nameC, autofocus: true,
              decoration: InputDecoration(labelText: tr('العنوان *', 'Title *'), border: const OutlineInputBorder())),
          const SizedBox(height: 10),
          TextField(controller: detailsC, maxLines: 3,
              decoration: InputDecoration(labelText: tr('التفاصيل', 'Details'), border: const OutlineInputBorder())),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
          FilledButton(style: FilledButton.styleFrom(backgroundColor: widget.accent),
              onPressed: () => Navigator.pop(c, true), child: Text(tr('حفظ', 'Save'))),
        ],
      ),
    );
    if (ok != true || nameC.text.trim().isEmpty) return;
    if (!mounted) return;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.managementLegalUpdate(
          d['id'] as int, name: nameC.text.trim(), details: detailsC.text.trim());
      await _reload();
      widget.onChanged();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('✅ أُضيف التحديث', '✅ Update added')), backgroundColor: const Color(0xFF16A34A)));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _letterBlock() {
    final l = d['letter'] as Map?;
    if (l == null) return const SizedBox.shrink();
    final info = (l['service_info'] as List?) ?? const [];
    final photo = '${l['photo_b64'] ?? ''}';
    final body = '${l['body'] ?? ''}';
    return Column(children: [
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            gradient: LinearGradient(colors: [widget.accent.withValues(alpha: 0.10), widget.accent.withValues(alpha: 0.03)], begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(18), border: Border.all(color: widget.accent.withValues(alpha: 0.18))),
        child: Row(children: [
          if (photo.isNotEmpty)
            ClipRRect(borderRadius: BorderRadius.circular(28), child: Image.memory(base64Decode(photo), width: 52, height: 52, fit: BoxFit.cover, gaplessPlayback: true)),
          if (photo.isNotEmpty) const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Text('${l['employee'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: Mgmt.ink)),
            if (l['letter_type'] != null)
              Padding(padding: const EdgeInsets.only(top: 2),
                  child: Text('📄 ${l['letter_type']}', style: const TextStyle(color: Mgmt.slate, fontSize: 12, fontWeight: FontWeight.w600))),
          ])),
        ]),
      ),
      if (info.isNotEmpty)
        _cardWrap([_sectionHead('✉️', tr('بيانات الخطاب', 'Letter details')), _infoRows(info)]),
      if (body.isNotEmpty)
        _cardWrap([
          _sectionHead('📝', tr('نص الخطاب', 'Letter body')),
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 4, 14, 12),
            child: Text(body, style: const TextStyle(color: Mgmt.ink, fontSize: 12.5, height: 1.5)),
          ),
        ]),
    ]);
  }

  Widget _vserviceBlock() {
    final v = d['vservice'] as Map?;
    if (v == null) return const SizedBox.shrink();
    final h = (v['header'] as Map?) ?? const {};
    final info = (v['service_info'] as List?) ?? const [];
    final img = '${v['image_b64'] ?? ''}';
    final cur = '${h['currency'] ?? ''}';
    return Column(children: [
      Container(
        margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
            gradient: LinearGradient(colors: [widget.accent.withValues(alpha: 0.10), widget.accent.withValues(alpha: 0.03)], begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(18), border: Border.all(color: widget.accent.withValues(alpha: 0.18))),
        child: Row(children: [
          if (img.isNotEmpty)
            ClipRRect(borderRadius: BorderRadius.circular(12), child: Image.memory(base64Decode(img), width: 60, height: 60, fit: BoxFit.cover, gaplessPlayback: true))
          else Container(width: 60, height: 60, decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)), child: Icon(Icons.build_rounded, color: widget.accent, size: 28)),
          const SizedBox(width: 14),
          Expanded(child: _kpiCell(tr('تكلفة الصيانة', 'Service cost'),
              '${(h['amount'] as num?)?.toStringAsFixed(3) ?? '0'}${cur.isEmpty ? '' : ' $cur'}', widget.accent, big: true)),
        ]),
      ),
      if (info.isNotEmpty)
        _cardWrap([_sectionHead('🔧', tr('تفاصيل الصيانة', 'Service details')), _infoRows(info)]),
      // this vehicle's full service history + running total
      if (((v['history'] as List?) ?? const []).isNotEmpty)
        _cardWrap([
          Row(children: [
            Expanded(child: _sectionHead('🗂️', tr('سجل صيانة المركبة', 'Vehicle service history'))),
            if ((v['total_spent'] as num?) != null)
              Padding(padding: const EdgeInsetsDirectional.only(end: 12),
                  child: Text('${tr('الإجمالي', 'Total')}: ${(v['total_spent'] as num).toStringAsFixed(3)}${cur.isEmpty ? '' : ' $cur'}',
                      style: TextStyle(fontWeight: FontWeight.w900, fontSize: 11.5, color: widget.accent))),
          ]),
          for (final s in ((v['history'] as List?) ?? const []).cast<Map>().take(20))
            Container(
              margin: const EdgeInsets.symmetric(horizontal: 12, vertical: 3),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
              decoration: BoxDecoration(
                  color: s['current'] == true ? widget.accent.withValues(alpha: 0.07) : Mgmt.bg,
                  borderRadius: BorderRadius.circular(10),
                  border: s['current'] == true ? Border.all(color: widget.accent.withValues(alpha: 0.3)) : null),
              child: Row(children: [
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${s['service'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12, color: Mgmt.ink)),
                  Text([if (s['date'] != null) '${s['date']}', if (s['odometer'] != null) '${s['odometer']} ${tr('كم', 'km')}'].join(' · '),
                      style: const TextStyle(fontSize: 10.5, color: Mgmt.slate)),
                ])),
                Text('${(numOf(s['amount'], 0)).toStringAsFixed(3)}${cur.isEmpty ? '' : ' $cur'}',
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12, color: widget.accent)),
              ]),
            ),
        ]),
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final actions = (d['actions'] as List?) ?? [];
    final sections = (d['sections'] as List?) ?? [];
    final canEdit = d['can_edit'] == true;
    final isProposal = d['proposal'] != null;
    final isTender = d['tender'] != null;
    final isOrder = d['order'] != null;
    final isFleet = d['fleet'] != null;
    final isCrm = d['crm'] != null;
    final isLeave = d['leave'] != null;
    final isExperience = d['experience'] != null;
    final isVservice = d['vservice'] != null;
    final isLetter = d['letter'] != null;
    final isReqinv = d['reqinv'] != null;
    final isDocument = d['document'] != null;
    final isDevice = d['device'] != null;
    final isApproval = d['approval'] != null;
    final isLegal = d['legal'] != null;
    final isPetrol = d['petrol'] != null;
    final isPassport = d['passport'] != null;
    final richDetail = isProposal || isTender || isOrder || isFleet || isCrm || isLeave || isExperience || isVservice || isLetter || isReqinv || isDocument || isDevice || isApproval || isLegal || isPetrol || isPassport;
    final amount = richDetail ? null : d['amount'];
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.82, maxChildSize: 0.96, minChildSize: 0.45,
      builder: (_, sc) => Stack(children: [
        ListView(controller: sc, padding: EdgeInsets.zero, children: [
          // ---- header
          Container(
            padding: const EdgeInsets.fromLTRB(20, 14, 20, 18),
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: [widget.accent, widget.accent.withValues(alpha: 0.72)],
                  begin: Alignment.topRight, end: Alignment.bottomLeft),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(24))),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Center(child: Container(width: 42, height: 4,
                  decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(4)))),
              const SizedBox(height: 14),
              Row(children: [
                Text('${d['icon']} ', style: const TextStyle(fontSize: 18)),
                Expanded(child: Text('${d['title']}',
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16))),
                if (canEdit)
                  Material(
                    color: Colors.white.withValues(alpha: 0.18),
                    borderRadius: BorderRadius.circular(11),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(11),
                      onTap: _busy ? null : _editSheet,
                      child: const Padding(
                        padding: EdgeInsets.all(7),
                        child: Icon(Icons.edit_rounded, color: Colors.white, size: 18)),
                    ),
                  ),
              ]),
              if (d['state'] != null) Padding(
                padding: const EdgeInsets.only(top: 10),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
                  decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(20),
                      boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.12), blurRadius: 6, offset: const Offset(0, 2))]),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Container(width: 7, height: 7,
                        decoration: BoxDecoration(color: mgmtHex('${d['state_color'] ?? ''}', widget.accent), shape: BoxShape.circle)),
                    const SizedBox(width: 6),
                    Text('${d['state']}',
                        style: TextStyle(color: mgmtHex('${d['state_color'] ?? ''}', widget.accent), fontWeight: FontWeight.w900, fontSize: 11.5)),
                  ]),
                ),
              ),
            ]),
          ),
          // ---- workflow actions: a prominent bar right under the header
          _actionBar(actions),
          // ---- professional detail blocks per system
          if (isProposal) _proposalBlock(),
          if (isTender) _tenderBlock(),
          if (isOrder) _orderBlock(),
          if (isFleet) _fleetBlock(),
          if (isCrm) _crmBlock(),
          if (isLeave) _leaveBlock(),
          if (isExperience) _experienceBlock(),
          if (isVservice) _vserviceBlock(),
          if (isLetter) _letterBlock(),
          if (isReqinv) _reqinvBlock(),
          if (isDocument) _documentBlock(),
          if (isDevice) _deviceBlock(),
          if (isApproval) _approvalBlock(),
          if (isLegal) _legalBlock(),
          if (isPetrol) _petrolBlock(),
          if (isPassport) _passportBlock(),
          // ---- amount highlight
          if (amount != null)
            Container(
              margin: const EdgeInsets.fromLTRB(14, 14, 14, 0),
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
              decoration: BoxDecoration(
                  color: widget.accent.withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(16)),
              child: Row(children: [
                Icon(Icons.payments_rounded, color: widget.accent, size: 20),
                const SizedBox(width: 10),
                Text(tr('القيمة', 'Amount'),
                    style: const TextStyle(color: Mgmt.slate, fontWeight: FontWeight.w700, fontSize: 12.5)),
                const Spacer(),
                Text('$amount',
                    style: TextStyle(color: widget.accent, fontWeight: FontWeight.w900, fontSize: 17)),
              ]),
            ),
          // ---- reports (pdf viewer / xlsx download)
          _attachmentsCard(),
          _reportsCard(),
          // ---- line items
          _linesCard(),
          // ---- professional grouped sections (rich blocks replace these)
          if (!richDetail) for (final s in sections) _sectionCard(s as Map),
          // fallback flat list if the server sent no sections
          if (!richDetail && sections.isEmpty)
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 12, 18, 0),
              child: Column(children: [
                for (final f in (d['fields'] as List? ?? [])) _fieldRow(f as Map),
              ]),
            ),
          const SizedBox(height: 26),
        ]),
        if (_busy)
          const Positioned.fill(child: ColoredBox(color: Color(0x11000000),
              child: Center(child: CircularProgressIndicator()))),
      ]),
    );
  }
}

/// A professional edit form for the whitelisted fields of one record. The
/// server decides which fields are editable and enforces the ACL again on save.
class _EditSheet extends StatefulWidget {
  const _EditSheet({
    required this.appKey,
    required this.id,
    required this.accent,
    required this.title,
    required this.editable,
  });
  final String appKey;
  final int id;
  final Color accent;
  final String title;
  final List<Map> editable;

  @override
  State<_EditSheet> createState() => _EditSheetState();
}

class _EditSheetState extends State<_EditSheet> {
  final Map<String, dynamic> _vals = {};
  final Map<String, TextEditingController> _ctrls = {};
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    for (final f in widget.editable) {
      final name = '${f['name']}';
      final t = '${f['type']}';
      _vals[name] = f['value'];
      if (t == 'char' || t == 'text' || t == 'float' || t == 'monetary' || t == 'integer') {
        _ctrls[name] = TextEditingController(text: f['value'] == null ? '' : '${f['value']}');
      }
    }
  }

  @override
  void dispose() {
    for (final c in _ctrls.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _pickDate(String name, bool withTime) async {
    DateTime init = DateTime.now();
    final cur = _vals[name];
    if (cur is String && cur.isNotEmpty) {
      init = DateTime.tryParse(cur) ?? init;
    }
    final d = await showDatePicker(
        context: context,
        initialDate: init,
        firstDate: DateTime(2015),
        lastDate: DateTime(2100));
    if (d == null) return;
    var out = d;
    if (withTime) {
      final t = await showTimePicker(
          context: context, initialTime: TimeOfDay.fromDateTime(init));
      if (t != null) {
        out = DateTime(d.year, d.month, d.day, t.hour, t.minute);
      }
    }
    final s = withTime
        ? '${out.toIso8601String().substring(0, 16).replaceFirst('T', ' ')}:00'
        : out.toIso8601String().substring(0, 10);
    setState(() => _vals[name] = s);
  }

  Future<void> _save() async {
    // pull text controllers into the value map
    for (final f in widget.editable) {
      final name = '${f['name']}';
      final t = '${f['type']}';
      if (_ctrls.containsKey(name)) {
        final raw = _ctrls[name]!.text.trim();
        if (t == 'float' || t == 'monetary') {
          _vals[name] = double.tryParse(raw) ?? 0;
        } else if (t == 'integer') {
          _vals[name] = int.tryParse(raw) ?? 0;
        } else {
          _vals[name] = raw;
        }
      }
    }
    setState(() => _busy = true);
    try {
      await context
          .read<AuthProvider>()
          .api
          .managementWrite(widget.appKey, widget.id, _vals);
      if (!mounted) return;
      Navigator.pop(context, true);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('✅ تم الحفظ', '✅ Saved')),
          backgroundColor: const Color(0xFF16A34A)));
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
      }
    }
  }

  Widget _label(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 6, top: 14),
        child: Text(t,
            style: const TextStyle(
                fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.slate)),
      );

  InputDecoration _dec() => InputDecoration(
        isDense: true,
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: Colors.grey.shade300)),
        focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide(color: widget.accent, width: 1.6)),
      );

  Widget _field(Map f) {
    final name = '${f['name']}';
    final t = '${f['type']}';
    if (t == 'many2one' || t == 'selection') {
      final opts = ((f['options'] as List?) ?? const []).cast<Map>();
      final cur = _vals[name];
      return DropdownButtonFormField(
        value: opts.any((o) => o['v'] == cur) ? cur : null,
        isExpanded: true,
        decoration: _dec(),
        items: [
          for (final o in opts)
            DropdownMenuItem(value: o['v'], child: Text('${o['l']}', overflow: TextOverflow.ellipsis)),
        ],
        onChanged: (v) => _vals[name] = v,
      );
    }
    if (t == 'date' || t == 'datetime') {
      return InkWell(
        onTap: () => _pickDate(name, t == 'datetime'),
        child: InputDecorator(
          decoration: _dec(),
          child: Row(children: [
            Icon(Icons.event_rounded, size: 18, color: widget.accent),
            const SizedBox(width: 8),
            Text('${_vals[name] ?? tr('اختر التاريخ', 'Pick a date')}',
                style: const TextStyle(fontWeight: FontWeight.w700)),
          ]),
        ),
      );
    }
    if (t == 'boolean') {
      return SwitchListTile(
        contentPadding: EdgeInsets.zero,
        activeColor: widget.accent,
        value: _vals[name] == true,
        title: Text(tr('نعم', 'Yes')),
        onChanged: (v) => setState(() => _vals[name] = v),
      );
    }
    final isNum = t == 'float' || t == 'monetary' || t == 'integer';
    return TextField(
      controller: _ctrls[name],
      keyboardType: isNum ? const TextInputType.numberWithOptions(decimal: true) : TextInputType.text,
      maxLines: t == 'text' ? 3 : 1,
      decoration: _dec(),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.7,
        maxChildSize: 0.95,
        builder: (_, sc) => ListView(controller: sc, padding: const EdgeInsets.fromLTRB(20, 12, 20, 20), children: [
          Center(child: Container(width: 40, height: 4,
              decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(4)))),
          const SizedBox(height: 14),
          Row(children: [
            Icon(Icons.edit_note_rounded, color: widget.accent),
            const SizedBox(width: 8),
            Expanded(child: Text(tr('تعديل السجل', 'Edit record'),
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16))),
          ]),
          Text(widget.title, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Mgmt.slate, fontSize: 12.5)),
          for (final f in widget.editable) ...[
            _label('${f['label']}'),
            _field(f),
          ],
          const SizedBox(height: 22),
          SizedBox(
            height: 48,
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                  backgroundColor: widget.accent, foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
              onPressed: _busy ? null : _save,
              icon: _busy
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.check_rounded),
              label: Text(tr('حفظ', 'Save'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
            ),
          ),
        ]),
      ),
    );
  }
}

/// A professional create form for a new quotation (proposal). Fetches the
/// pickers (customers, service types, modes) from the server, then posts the
/// chosen values. Returns {id, ref, title} on success.
class _ProposalCreateSheet extends StatefulWidget {
  const _ProposalCreateSheet({required this.accent, this.editId});
  final Color accent;
  final int? editId;
  @override
  State<_ProposalCreateSheet> createState() => _ProposalCreateSheetState();
}

class _ProposalCreateSheetState extends State<_ProposalCreateSheet> {
  Map<String, dynamic>? _meta;
  bool _loading = true, _busy = false;
  String? _err;

  int? _partnerId, _serviceTypeId;
  String? _partnerName;
  String? _proposalDate, _expireDate, _mobDate, _mode;
  bool _linesEditable = true;
  final _site = TextEditingController();
  final _period = TextEditingController();
  final _margin = TextEditingController(text: '20');
  final _notes = TextEditingController();
  final List<Map<String, dynamic>> _services = [];

  bool get _isEdit => widget.editId != null;

  @override
  void initState() {
    super.initState();
    _proposalDate = DateTime.now().toIso8601String().substring(0, 10);
    _load();
  }

  @override
  void dispose() {
    _site.dispose(); _period.dispose(); _margin.dispose(); _notes.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final api = context.read<AuthProvider>().api;
      final m = await api.managementProposalMeta();
      if (_isEdit) {
        final ed = await api.managementProposalEditData(widget.editId!);
        _partnerId = ed['partner_id'] as int?;
        _partnerName = ed['partner_name'] as String?;
        _serviceTypeId = ed['service_type_id'] as int?;
        _proposalDate = ed['proposal_date'] as String?;
        _expireDate = ed['expire_date'] as String?;
        _mobDate = ed['mobilization_date'] as String?;
        _mode = ed['mode'] as String?;
        _site.text = '${ed['service_site'] ?? ''}';
        _period.text = ((ed['proposal_period'] as num?) ?? 0) > 0 ? '${ed['proposal_period']}' : '';
        _margin.text = ((ed['target_margin_pct'] as num?) ?? 0) > 0 ? '${ed['target_margin_pct']}' : '';
        _notes.text = '${ed['notes'] ?? ''}';
        _linesEditable = ed['lines_editable'] == true;
        for (final s in ((ed['services'] as List?) ?? const []).cast<Map>()) {
          _services.add({'service_id': s['service_id'], 'name': s['name'], 'quantity': s['quantity']});
        }
      }
      if (mounted) setState(() { _meta = m; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _err = '$e'; _loading = false; });
    }
  }

  Future<void> _addService() async {
    final opts = ((_meta?['services'] as List?) ?? const []).cast<Map>()
        .map((e) => {'v': e['v'], 'l': '${e['l']}${(e['type'] ?? '').toString().isNotEmpty ? '  ·  ${e['type']}' : ''}'})
        .toList().cast<Map>();
    if (opts.isEmpty) return;
    final chosen = await showModalBottomSheet<int>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => _PickerSheet(title: tr('اختر الخدمة', 'Select service'), options: opts, accent: widget.accent),
    );
    if (chosen == null) return;
    final svc = ((_meta?['services'] as List?) ?? const []).cast<Map>().firstWhere((e) => e['v'] == chosen);
    setState(() => _services.add({'service_id': chosen, 'name': svc['l'], 'quantity': 1}));
  }

  Future<void> _pick(String which) async {
    final now = DateTime.now();
    final cur = which == 'p' ? _proposalDate : (which == 'e' ? _expireDate : _mobDate);
    final init = (cur != null && cur.isNotEmpty) ? DateTime.tryParse(cur) ?? now : now;
    final d = await showDatePicker(
        context: context, initialDate: init,
        firstDate: DateTime(2015), lastDate: DateTime(2100));
    if (d == null) return;
    final s = d.toIso8601String().substring(0, 10);
    setState(() {
      if (which == 'p') _proposalDate = s;
      else if (which == 'e') _expireDate = s;
      else _mobDate = s;
    });
  }

  Future<void> _pickCustomer() async {
    final list = ((_meta?['customers'] as List?) ?? const []).cast<Map>();
    final chosen = await showModalBottomSheet<int>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => _PickerSheet(title: tr('اختر العميل', 'Select customer'), options: list, accent: widget.accent),
    );
    if (chosen != null) setState(() => _partnerId = chosen);
  }

  String? _customerLabel() {
    final list = ((_meta?['customers'] as List?) ?? const []).cast<Map>();
    final m = list.where((e) => e['v'] == _partnerId);
    if (m.isNotEmpty) return '${m.first['l']}';
    return _partnerName; // edit mode: name came from edit-data
  }

  Future<void> _submit() async {
    if (_partnerId == null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('اختر العميل أولًا', 'Select a customer first')), backgroundColor: Mgmt.red));
      return;
    }
    setState(() => _busy = true);
    try {
      final api = context.read<AuthProvider>().api;
      final services = _services.map((s) => {'service_id': s['service_id'], 'quantity': s['quantity']}).toList();
      final vals = <String, dynamic>{
        'partner_id': _partnerId,
        'service_type_id': _serviceTypeId,
        if (_proposalDate != null) 'proposal_date': _proposalDate,
        if (_expireDate != null) 'expire_date': _expireDate,
        if (_mobDate != null) 'mobilization_date': _mobDate,
        'service_site': _site.text.trim(),
        if (_mode != null) 'mode': _mode,
        'proposal_period': _period.text.trim(),
        if (_margin.text.trim().isNotEmpty) 'target_margin_pct': _margin.text.trim(),
        'notes': _notes.text.trim(),
        if (_linesEditable) 'services': services,
      };
      if (_isEdit) {
        await api.managementProposalUpdate(widget.editId!, vals);
        if (mounted) Navigator.pop(context, {'id': widget.editId, 'edited': true});
      } else {
        final res = await api.managementProposalCreate(vals);
        if (mounted) Navigator.pop(context, res);
      }
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
      }
    }
  }

  InputDecoration _dec(String hint) => InputDecoration(
        hintText: hint, isDense: true, filled: true, fillColor: Mgmt.bg,
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
      );

  Widget _label(String t) => Padding(
        padding: const EdgeInsets.fromLTRB(2, 14, 2, 6),
        child: Text(t, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.ink)),
      );

  Widget _tap(String? value, String hint, IconData icon, VoidCallback onTap) => InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 13),
          decoration: BoxDecoration(color: Mgmt.bg, borderRadius: BorderRadius.circular(12)),
          child: Row(children: [
            Icon(icon, size: 18, color: widget.accent),
            const SizedBox(width: 10),
            Expanded(child: Text(value ?? hint,
                maxLines: 1, overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 13,
                    color: value == null ? Mgmt.slate : Mgmt.ink,
                    fontWeight: value == null ? FontWeight.w500 : FontWeight.w700))),
            const Icon(Icons.chevron_left_rounded, color: Mgmt.slate),
          ]),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final types = ((_meta?['service_types'] as List?) ?? const []).cast<Map>();
    final modes = ((_meta?['modes'] as List?) ?? const []).cast<Map>();
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.9, maxChildSize: 0.96, minChildSize: 0.5,
      builder: (_, sc) => Column(children: [
        Container(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
          decoration: BoxDecoration(
            gradient: LinearGradient(colors: [widget.accent, widget.accent.withValues(alpha: 0.72)],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(22))),
          child: Column(children: [
            Center(child: Container(width: 42, height: 4,
                decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(4)))),
            const SizedBox(height: 12),
            Row(children: [
              const Text('📊 ', style: TextStyle(fontSize: 18)),
              Expanded(child: Text(_isEdit ? tr('تعديل عرض السعر', 'Edit quotation') : tr('عرض سعر جديد', 'New quotation'),
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16))),
              IconButton(onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.close_rounded, color: Colors.white)),
            ]),
          ]),
        ),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _err != null
                  ? Center(child: Padding(padding: const EdgeInsets.all(30),
                      child: Text(_err!, textAlign: TextAlign.center, style: const TextStyle(color: Mgmt.slate))))
                  : ListView(controller: sc, padding: const EdgeInsets.fromLTRB(16, 4, 16, 24), children: [
                      _label('${tr('العميل', 'Customer')} *'),
                      _tap(_customerLabel(), tr('اختر العميل', 'Select customer'), Icons.business_rounded, _pickCustomer),
                      _label(tr('نوع الخدمة', 'Service type')),
                      _dropdown(types, _serviceTypeId, (v) => setState(() => _serviceTypeId = v), tr('اختر النوع', 'Select type')),
                      Row(children: [
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          _label(tr('تاريخ العرض', 'Proposal date')),
                          _tap(_proposalDate, tr('اختر', 'Pick'), Icons.event_rounded, () => _pick('p')),
                        ])),
                        const SizedBox(width: 10),
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          _label(tr('تاريخ الانتهاء', 'Expiry date')),
                          _tap(_expireDate, tr('اختر', 'Pick'), Icons.event_busy_rounded, () => _pick('e')),
                        ])),
                      ]),
                      Row(children: [
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          _label(tr('تاريخ المباشرة', 'Mobilization')),
                          _tap(_mobDate, tr('اختر', 'Pick'), Icons.flag_rounded, () => _pick('m')),
                        ])),
                        const SizedBox(width: 10),
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          _label(tr('المدة (شهور)', 'Period (months)')),
                          TextField(controller: _period, keyboardType: TextInputType.number, decoration: _dec('0')),
                        ])),
                      ]),
                      _label(tr('موقع الخدمة', 'Service site')),
                      TextField(controller: _site, decoration: _dec(tr('العنوان / الموقع', 'Address / site'))),
                      if (modes.isNotEmpty) ...[
                        _label(tr('نمط الفوترة', 'Billing mode')),
                        _dropdownStr(modes, _mode, (v) => setState(() => _mode = v), tr('اختر', 'Select')),
                      ],
                      // ---- services (proposal.service catalog)
                      Padding(
                        padding: const EdgeInsets.only(top: 16, bottom: 6),
                        child: Row(children: [
                          Text(tr('الخدمات', 'Services'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.ink)),
                          const Spacer(),
                          if (_linesEditable)
                            TextButton.icon(onPressed: _addService, icon: const Icon(Icons.add_rounded, size: 18),
                                style: TextButton.styleFrom(foregroundColor: widget.accent),
                                label: Text(tr('إضافة خدمة', 'Add service'), style: const TextStyle(fontWeight: FontWeight.w800))),
                        ]),
                      ),
                      if (!_linesEditable)
                        Container(
                          padding: const EdgeInsets.all(10), margin: const EdgeInsets.only(bottom: 6),
                          decoration: BoxDecoration(color: const Color(0xFFF59E0B).withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)),
                          child: Text(tr('الخدمات تُعدّل في حالة المسودة فقط.', 'Services editable only in draft.'),
                              style: const TextStyle(color: Color(0xFFB45309), fontSize: 11, fontWeight: FontWeight.w700)),
                        ),
                      if (_services.isEmpty)
                        Padding(padding: const EdgeInsets.symmetric(vertical: 8),
                            child: Text(tr('لا خدمات بعد', 'No services yet'), style: const TextStyle(color: Mgmt.slate, fontSize: 12))),
                      for (int i = 0; i < _services.length; i++)
                        Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.fromLTRB(12, 8, 6, 8),
                          decoration: BoxDecoration(color: Mgmt.bg, borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.black.withValues(alpha: 0.05))),
                          child: Row(children: [
                            Expanded(child: Text('${_services[i]['name']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12, color: Mgmt.ink))),
                            SizedBox(
                              width: 62,
                              child: TextFormField(
                                initialValue: '${_services[i]['quantity']}',
                                keyboardType: TextInputType.number, textAlign: TextAlign.center,
                                enabled: _linesEditable,
                                decoration: InputDecoration(labelText: tr('عدد', 'Qty'), isDense: true,
                                    contentPadding: const EdgeInsets.symmetric(horizontal: 6, vertical: 8)),
                                onChanged: (v) => _services[i]['quantity'] = double.tryParse(v) ?? 1,
                              ),
                            ),
                            if (_linesEditable)
                              IconButton(onPressed: () => setState(() => _services.removeAt(i)),
                                  icon: const Icon(Icons.delete_outline_rounded, size: 18, color: Mgmt.red)),
                          ]),
                        ),
                      _label(tr('هامش الربح المستهدف %', 'Target margin %')),
                      TextField(controller: _margin, keyboardType: TextInputType.number, decoration: _dec('20')),
                      _label(tr('ملاحظات', 'Notes')),
                      TextField(controller: _notes, maxLines: 3, decoration: _dec(tr('ملاحظات إضافية…', 'Extra notes…'))),
                      const SizedBox(height: 20),
                      SizedBox(
                        height: 50,
                        child: ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                              backgroundColor: widget.accent, foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
                          onPressed: _busy ? null : _submit,
                          icon: _busy
                              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                              : Icon(_isEdit ? Icons.save_rounded : Icons.add_rounded),
                          label: Text(_isEdit ? tr('حفظ التعديلات', 'Save changes') : tr('إنشاء العرض', 'Create quotation'),
                              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
                        ),
                      ),
                    ]),
        ),
      ]),
    );
  }

  Widget _dropdown(List<Map> opts, int? value, ValueChanged<int?> onChanged, String hint) =>
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        decoration: BoxDecoration(color: Mgmt.bg, borderRadius: BorderRadius.circular(12)),
        child: DropdownButtonHideUnderline(
          child: DropdownButton<int>(
            value: value, isExpanded: true, hint: Text(hint, style: const TextStyle(fontSize: 13, color: Mgmt.slate)),
            items: [for (final o in opts) DropdownMenuItem(value: o['v'] as int, child: Text('${o['l']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13)))],
            onChanged: onChanged,
          ),
        ),
      );

  Widget _dropdownStr(List<Map> opts, String? value, ValueChanged<String?> onChanged, String hint) =>
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        decoration: BoxDecoration(color: Mgmt.bg, borderRadius: BorderRadius.circular(12)),
        child: DropdownButtonHideUnderline(
          child: DropdownButton<String>(
            value: value, isExpanded: true, hint: Text(hint, style: const TextStyle(fontSize: 13, color: Mgmt.slate)),
            items: [for (final o in opts) DropdownMenuItem(value: '${o['v']}', child: Text('${o['l']}', style: const TextStyle(fontSize: 13)))],
            onChanged: onChanged,
          ),
        ),
      );
}

/// A searchable single-select bottom sheet for long option lists (customers).
class _PickerSheet extends StatefulWidget {
  const _PickerSheet({required this.title, required this.options, required this.accent});
  final String title;
  final List<Map> options;
  final Color accent;
  @override
  State<_PickerSheet> createState() => _PickerSheetState();
}

class _PickerSheetState extends State<_PickerSheet> {
  String _q = '';
  @override
  Widget build(BuildContext context) {
    final filtered = _q.isEmpty
        ? widget.options
        : widget.options.where((o) => '${o['l']}'.toLowerCase().contains(_q.toLowerCase())).toList();
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.8, maxChildSize: 0.95, minChildSize: 0.5,
      builder: (_, sc) => Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
          child: Row(children: [
            Expanded(child: Text(widget.title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15))),
            IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close_rounded)),
          ]),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: TextField(
            autofocus: true,
            onChanged: (v) => setState(() => _q = v),
            decoration: InputDecoration(
              hintText: tr('ابحث…', 'Search…'),
              prefixIcon: const Icon(Icons.search_rounded, size: 20),
              filled: true, fillColor: Mgmt.bg, isDense: true,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            ),
          ),
        ),
        const SizedBox(height: 8),
        Expanded(
          child: ListView.separated(
            controller: sc,
            itemCount: filtered.length,
            separatorBuilder: (_, __) => Divider(height: 1, color: Colors.grey.shade100),
            itemBuilder: (_, i) => ListTile(
              title: Text('${filtered[i]['l']}', style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600)),
              onTap: () => Navigator.pop(context, filtered[i]['v'] as int),
            ),
          ),
        ),
      ]),
    );
  }
}

/// Create a new CRM opportunity — professional form with searchable customer
/// picker, stage/owner dropdowns and contact fields. Returns {id, title}.
class _CrmCreateSheet extends StatefulWidget {
  const _CrmCreateSheet({required this.accent});
  final Color accent;
  @override
  State<_CrmCreateSheet> createState() => _CrmCreateSheetState();
}

class _CrmCreateSheetState extends State<_CrmCreateSheet> {
  Map<String, dynamic>? _meta;
  bool _loading = true, _busy = false;
  String? _err;

  int? _partnerId, _stageId, _userId;
  final _name = TextEditingController();
  final _contact = TextEditingController();
  final _email = TextEditingController();
  final _phone = TextEditingController();
  final _revenue = TextEditingController();
  final _desc = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _name.dispose(); _contact.dispose(); _email.dispose();
    _phone.dispose(); _revenue.dispose(); _desc.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final m = await context.read<AuthProvider>().api.managementCrmMeta();
      if (mounted) setState(() {
        _meta = m; _loading = false;
        _userId = m['me'] as int?;
        final stages = (m['stages'] as List?) ?? const [];
        if (stages.isNotEmpty) _stageId = stages.first['v'] as int?;
      });
    } catch (e) {
      if (mounted) setState(() { _err = '$e'; _loading = false; });
    }
  }

  Future<void> _pickCustomer() async {
    final list = ((_meta?['customers'] as List?) ?? const []).cast<Map>();
    final chosen = await showModalBottomSheet<int>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => _PickerSheet(title: tr('اختر العميل', 'Select customer'), options: list, accent: widget.accent),
    );
    if (chosen != null) setState(() => _partnerId = chosen);
  }

  String? _customerLabel() {
    final list = ((_meta?['customers'] as List?) ?? const []).cast<Map>();
    final m = list.where((e) => e['v'] == _partnerId);
    return m.isEmpty ? null : '${m.first['l']}';
  }

  Future<void> _submit() async {
    if (_name.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('أدخل عنوان الفرصة', 'Enter an opportunity title')), backgroundColor: Mgmt.red));
      return;
    }
    setState(() => _busy = true);
    try {
      final vals = <String, dynamic>{
        'name': _name.text.trim(),
        if (_partnerId != null) 'partner_id': _partnerId,
        if (_stageId != null) 'stage_id': _stageId,
        if (_userId != null) 'user_id': _userId,
        if (_contact.text.trim().isNotEmpty) 'contact_name': _contact.text.trim(),
        if (_email.text.trim().isNotEmpty) 'email_from': _email.text.trim(),
        if (_phone.text.trim().isNotEmpty) 'phone': _phone.text.trim(),
        if (_revenue.text.trim().isNotEmpty) 'expected_revenue': _revenue.text.trim(),
        if (_desc.text.trim().isNotEmpty) 'description': _desc.text.trim(),
      };
      final res = await context.read<AuthProvider>().api.managementCrmCreate(vals);
      if (mounted) Navigator.pop(context, res);
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
      }
    }
  }

  InputDecoration _dec(String hint) => InputDecoration(
        hintText: hint, isDense: true, filled: true, fillColor: Mgmt.bg,
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
      );

  Widget _label(String t) => Padding(
        padding: const EdgeInsets.fromLTRB(2, 14, 2, 6),
        child: Text(t, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.ink)),
      );

  Widget _tap(String? value, String hint, IconData icon, VoidCallback onTap) => InkWell(
        borderRadius: BorderRadius.circular(12), onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 13),
          decoration: BoxDecoration(color: Mgmt.bg, borderRadius: BorderRadius.circular(12)),
          child: Row(children: [
            Icon(icon, size: 18, color: widget.accent),
            const SizedBox(width: 10),
            Expanded(child: Text(value ?? hint, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 13, color: value == null ? Mgmt.slate : Mgmt.ink,
                    fontWeight: value == null ? FontWeight.w500 : FontWeight.w700))),
            const Icon(Icons.chevron_left_rounded, color: Mgmt.slate),
          ]),
        ),
      );

  Widget _dropdown(List<Map> opts, int? value, ValueChanged<int?> onChanged, String hint) =>
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        decoration: BoxDecoration(color: Mgmt.bg, borderRadius: BorderRadius.circular(12)),
        child: DropdownButtonHideUnderline(
          child: DropdownButton<int>(
            value: value, isExpanded: true, hint: Text(hint, style: const TextStyle(fontSize: 13, color: Mgmt.slate)),
            items: [for (final o in opts) DropdownMenuItem(value: o['v'] as int, child: Text('${o['l']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13)))],
            onChanged: onChanged,
          ),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final stages = ((_meta?['stages'] as List?) ?? const []).cast<Map>();
    final users = ((_meta?['users'] as List?) ?? const []).cast<Map>();
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.9, maxChildSize: 0.96, minChildSize: 0.5,
      builder: (_, sc) => Column(children: [
        Container(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
          decoration: BoxDecoration(
            gradient: LinearGradient(colors: [widget.accent, widget.accent.withValues(alpha: 0.72)],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(22))),
          child: Column(children: [
            Center(child: Container(width: 42, height: 4,
                decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(4)))),
            const SizedBox(height: 12),
            Row(children: [
              const Text('🎯 ', style: TextStyle(fontSize: 18)),
              Expanded(child: Text(tr('فرصة جديدة', 'New opportunity'),
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16))),
              IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close_rounded, color: Colors.white)),
            ]),
          ]),
        ),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _err != null
                  ? Center(child: Padding(padding: const EdgeInsets.all(30),
                      child: Text(_err!, textAlign: TextAlign.center, style: const TextStyle(color: Mgmt.slate))))
                  : ListView(controller: sc, padding: const EdgeInsets.fromLTRB(16, 4, 16, 24), children: [
                      _label('${tr('عنوان الفرصة', 'Opportunity title')} *'),
                      TextField(controller: _name, decoration: _dec(tr('مثال: عقد نظافة برج...', 'e.g. Cleaning contract...'))),
                      _label(tr('العميل', 'Customer')),
                      _tap(_customerLabel(), tr('اختر العميل', 'Select customer'), Icons.business_rounded, _pickCustomer),
                      Row(children: [
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          _label(tr('المرحلة', 'Stage')),
                          _dropdown(stages, _stageId, (v) => setState(() => _stageId = v), tr('اختر', 'Select')),
                        ])),
                        const SizedBox(width: 10),
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          _label(tr('المندوب', 'Owner')),
                          _dropdown(users, _userId, (v) => setState(() => _userId = v), tr('اختر', 'Select')),
                        ])),
                      ]),
                      _label(tr('الإيراد المتوقع', 'Expected revenue')),
                      TextField(controller: _revenue, keyboardType: TextInputType.number, decoration: _dec('0.000')),
                      _label(tr('جهة الاتصال', 'Contact name')),
                      TextField(controller: _contact, decoration: _dec(tr('اسم الشخص', 'Person name'))),
                      Row(children: [
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          _label(tr('البريد', 'Email')),
                          TextField(controller: _email, keyboardType: TextInputType.emailAddress, decoration: _dec('name@company.com')),
                        ])),
                        const SizedBox(width: 10),
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          _label(tr('الهاتف', 'Phone')),
                          TextField(controller: _phone, keyboardType: TextInputType.phone, decoration: _dec('+965...')),
                        ])),
                      ]),
                      _label(tr('ملاحظات', 'Notes')),
                      TextField(controller: _desc, maxLines: 3, decoration: _dec(tr('تفاصيل الفرصة…', 'Opportunity details…'))),
                      const SizedBox(height: 20),
                      SizedBox(
                        height: 50,
                        child: ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(
                              backgroundColor: widget.accent, foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
                          onPressed: _busy ? null : _submit,
                          icon: _busy
                              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                              : const Icon(Icons.add_rounded),
                          label: Text(tr('إنشاء الفرصة', 'Create opportunity'),
                              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
                        ),
                      ),
                    ]),
        ),
      ]),
    );
  }
}

/// The purchase order's deliveries (stock pickings) with a one-tap "Receive"
/// action per picking that isn't done yet.
class _DeliveriesSheet extends StatefulWidget {
  const _DeliveriesSheet({required this.poId, required this.accent, required this.initial, required this.onChanged});
  final int poId;
  final Color accent;
  final Map<String, dynamic> initial;
  final VoidCallback onChanged;
  @override
  State<_DeliveriesSheet> createState() => _DeliveriesSheetState();
}

class _DeliveriesSheetState extends State<_DeliveriesSheet> {
  late Map<String, dynamic> d = widget.initial;
  bool _busy = false;

  Future<void> _reload() async {
    try {
      final r = await context.read<AuthProvider>().api.managementPoDeliveries(widget.poId);
      if (mounted) setState(() => d = r);
    } catch (_) {}
  }

  Future<void> _receive(int pickingId) async {
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      title: Text(tr('تأكيد الاستلام', 'Confirm receipt'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
      content: Text(tr('سيتم استلام كل الكميات وتأكيد التسليم.', 'All quantities will be received and the delivery validated.')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('تراجع', 'Back'))),
        ElevatedButton(
          style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF16A34A), foregroundColor: Colors.white),
          onPressed: () => Navigator.pop(c, true), child: Text(tr('استلام', 'Receive'))),
      ],
    ));
    if (ok != true || !mounted) return;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.managementPickingValidate(pickingId);
      if (!mounted) return;
      await _reload();
      widget.onChanged();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('✅ تم تأكيد الاستلام', '✅ Receipt confirmed')), backgroundColor: const Color(0xFF16A34A)));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final list = (d['deliveries'] as List?) ?? const [];
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.75, maxChildSize: 0.95, minChildSize: 0.4,
      builder: (_, sc) => Stack(children: [
        Column(children: [
          Container(
            padding: const EdgeInsets.fromLTRB(18, 14, 12, 12),
            decoration: BoxDecoration(
                gradient: LinearGradient(colors: [widget.accent, widget.accent.withValues(alpha: 0.72)],
                    begin: Alignment.topRight, end: Alignment.bottomLeft),
                borderRadius: const BorderRadius.vertical(top: Radius.circular(22))),
            child: Row(children: [
              Expanded(child: Text('🚚 ${tr('التسليمات', 'Deliveries')} · ${list.length}',
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15))),
              IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close_rounded, color: Colors.white)),
            ]),
          ),
          Expanded(
            child: list.isEmpty
                ? Center(child: Text(tr('لا تسليمات', 'No deliveries'), style: const TextStyle(color: Mgmt.slate, fontWeight: FontWeight.w700)))
                : ListView.separated(
                    controller: sc, padding: const EdgeInsets.all(12),
                    itemCount: list.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (_, i) {
                      final pk = list[i] as Map;
                      final moves = (pk['moves'] as List?) ?? const [];
                      final canRecv = pk['can_validate'] == true;
                      return Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                            color: Mgmt.bg, borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: Colors.black.withValues(alpha: 0.05))),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Row(children: [
                            Expanded(child: Text('${pk['name']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Mgmt.ink))),
                            mgmtStateChip({'state': gLang == 'en' ? pk['state_en'] : pk['state_ar'], 'state_color': pk['state_color']}),
                          ]),
                          if (pk['type'] != null || pk['scheduled'] != null)
                            Padding(padding: const EdgeInsets.only(top: 3),
                              child: Text([
                                if (pk['type'] != null) '${pk['type']}',
                                if (pk['scheduled'] != null) '📅 ${'${pk['scheduled']}'.split(' ').first}',
                              ].join('  ·  '), style: const TextStyle(color: Mgmt.slate, fontSize: 10.5))),
                          if (moves.isNotEmpty) ...[
                            const Divider(height: 14),
                            for (final mv in moves.cast<Map>())
                              Padding(
                                padding: const EdgeInsets.symmetric(vertical: 2),
                                child: Row(children: [
                                  Expanded(child: Text('${mv['product']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                                      style: const TextStyle(fontSize: 11.5, color: Mgmt.ink, fontWeight: FontWeight.w600))),
                                  Text('${mv['done']}/${mv['demand']}',
                                      style: const TextStyle(fontSize: 11, color: Mgmt.slate, fontWeight: FontWeight.w800)),
                                ]),
                              ),
                          ],
                          if (canRecv) Padding(
                            padding: const EdgeInsets.only(top: 10),
                            child: SizedBox(
                              width: double.infinity, height: 40,
                              child: ElevatedButton.icon(
                                style: ElevatedButton.styleFrom(
                                    backgroundColor: const Color(0xFF16A34A), foregroundColor: Colors.white,
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(11))),
                                onPressed: _busy ? null : () => _receive(pk['id'] as int),
                                icon: const Icon(Icons.check_circle_rounded, size: 17),
                                label: Text(tr('تأكيد الاستلام', 'Receive'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5)),
                              ),
                            ),
                          ),
                        ]),
                      );
                    },
                  ),
          ),
        ]),
        if (_busy) const Positioned.fill(child: ColoredBox(color: Color(0x11000000), child: Center(child: CircularProgressIndicator()))),
      ]),
    );
  }
}

/// Searchable recipient picker that returns the chosen email.
class _RecipientPicker extends StatefulWidget {
  const _RecipientPicker({required this.options, required this.accent});
  final List<Map> options;
  final Color accent;
  @override
  State<_RecipientPicker> createState() => _RecipientPickerState();
}

class _RecipientPickerState extends State<_RecipientPicker> {
  String _q = '';
  @override
  Widget build(BuildContext context) {
    final filtered = _q.isEmpty
        ? widget.options
        : widget.options.where((o) => '${o['l']}'.toLowerCase().contains(_q.toLowerCase())).toList();
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.8, maxChildSize: 0.95, minChildSize: 0.5,
      builder: (_, sc) => Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
          child: Row(children: [
            Expanded(child: Text(tr('اختر المستلم', 'Select recipient'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15))),
            IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close_rounded)),
          ]),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: TextField(
            autofocus: true,
            onChanged: (v) => setState(() => _q = v),
            decoration: InputDecoration(
              hintText: tr('ابحث…', 'Search…'),
              prefixIcon: const Icon(Icons.search_rounded, size: 20),
              filled: true, fillColor: Mgmt.bg, isDense: true,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            ),
          ),
        ),
        const SizedBox(height: 8),
        Expanded(
          child: ListView.separated(
            controller: sc,
            itemCount: filtered.length,
            separatorBuilder: (_, __) => Divider(height: 1, color: Colors.grey.shade100),
            itemBuilder: (_, i) => ListTile(
              title: Text('${filtered[i]['l']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
              onTap: () => Navigator.pop(context, '${filtered[i]['email']}'),
            ),
          ),
        ),
      ]),
    );
  }
}

/// Create or edit a purchase order — vendor picker, a line editor with live
/// product search, reference + notes. Returns {id,title} (create) or true (edit).
class _PoFormSheet extends StatefulWidget {
  const _PoFormSheet({required this.accent, this.editId});
  final Color accent;
  final int? editId;
  @override
  State<_PoFormSheet> createState() => _PoFormSheetState();
}

class _PoFormSheetState extends State<_PoFormSheet> {
  bool _loading = true, _busy = false;
  String? _err, _currency = '';
  bool _linesEditable = true;
  int? _partnerId;
  String? _partnerName;
  final _ref = TextEditingController();
  final _notes = TextEditingController();
  List<Map<String, dynamic>> _vendors = [];
  final List<Map<String, dynamic>> _lines = [];

  bool get _isEdit => widget.editId != null;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _ref.dispose(); _notes.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final api = context.read<AuthProvider>().api;
      final meta = await api.managementPoMeta();
      _vendors = ((meta['vendors'] as List?) ?? const []).cast<Map>().map((e) => Map<String, dynamic>.from(e)).toList();
      _currency = '${meta['currency'] ?? ''}';
      if (_isEdit) {
        final ed = await api.managementPoEditData(widget.editId!);
        _partnerId = ed['partner_id'] as int?;
        _partnerName = ed['partner_name'] as String?;
        _ref.text = '${ed['partner_ref'] ?? ''}';
        _notes.text = '${ed['notes'] ?? ''}';
        _linesEditable = ed['lines_editable'] == true;
        _currency = '${ed['currency'] ?? _currency}';
        for (final l in ((ed['lines'] as List?) ?? const []).cast<Map>()) {
          _lines.add({'product_id': l['product_id'], 'name': l['name'], 'qty': l['qty'], 'price': l['price'], 'uom': l['uom']});
        }
      }
      if (mounted) setState(() => _loading = false);
    } catch (e) {
      if (mounted) setState(() { _err = '$e'; _loading = false; });
    }
  }

  double get _total {
    double t = 0;
    for (final l in _lines) {
      t += ((l['qty'] as num?) ?? 0) * ((l['price'] as num?) ?? 0);
    }
    return t;
  }

  Future<void> _pickVendor() async {
    final opts = _vendors.map((e) => {'v': e['v'], 'l': e['l']}).toList().cast<Map>();
    final chosen = await showModalBottomSheet<int>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => _PickerSheet(title: tr('اختر المورّد', 'Select vendor'), options: opts, accent: widget.accent),
    );
    if (chosen != null) {
      setState(() {
        _partnerId = chosen;
        _partnerName = '${_vendors.firstWhere((e) => e['v'] == chosen)['l']}';
      });
    }
  }

  Future<void> _addLine() async {
    final prod = await showModalBottomSheet<Map<String, dynamic>>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => _ProductSearchSheet(accent: widget.accent),
    );
    if (prod != null) {
      setState(() => _lines.add({
            'product_id': prod['id'], 'name': prod['name'],
            'qty': 1.0, 'price': prod['price'], 'uom': prod['uom'],
          }));
    }
  }

  Future<void> _editLineQtyPrice(int i) async {
    final l = _lines[i];
    final qtyC = TextEditingController(text: '${l['qty']}');
    final priceC = TextEditingController(text: '${l['price']}');
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      title: Text('${l['name']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w800)),
      content: Column(mainAxisSize: MainAxisSize.min, children: [
        TextField(controller: qtyC, keyboardType: TextInputType.number,
            decoration: InputDecoration(labelText: tr('الكمية', 'Quantity'))),
        TextField(controller: priceC, keyboardType: TextInputType.number,
            decoration: InputDecoration(labelText: tr('السعر', 'Unit price'))),
      ]),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
        ElevatedButton(
          style: ElevatedButton.styleFrom(backgroundColor: widget.accent, foregroundColor: Colors.white),
          onPressed: () => Navigator.pop(c, true), child: Text(tr('حفظ', 'Save'))),
      ],
    ));
    if (ok == true) {
      setState(() {
        l['qty'] = double.tryParse(qtyC.text) ?? l['qty'];
        l['price'] = double.tryParse(priceC.text) ?? l['price'];
      });
    }
  }

  Future<void> _save() async {
    if (_partnerId == null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('اختر المورّد', 'Select a vendor')), backgroundColor: Mgmt.red));
      return;
    }
    if (!_isEdit && _lines.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('أضف بندًا واحدًا على الأقل', 'Add at least one line')), backgroundColor: Mgmt.red));
      return;
    }
    setState(() => _busy = true);
    try {
      final api = context.read<AuthProvider>().api;
      final lines = _lines.map((l) => {'product_id': l['product_id'], 'name': l['name'], 'qty': l['qty'], 'price': l['price']}).toList();
      if (_isEdit) {
        await api.managementPoUpdate(widget.editId!, {
          'partner_id': _partnerId, 'partner_ref': _ref.text.trim(), 'notes': _notes.text.trim(),
          if (_linesEditable) 'lines': lines,
        });
        if (mounted) Navigator.pop(context, true);
      } else {
        final res = await api.managementPoCreate({
          'partner_id': _partnerId, 'partner_ref': _ref.text.trim(), 'notes': _notes.text.trim(), 'lines': lines,
        });
        if (mounted) Navigator.pop(context, res);
      }
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
      }
    }
  }

  InputDecoration _dec(String hint) => InputDecoration(
        hintText: hint, isDense: true, filled: true, fillColor: Mgmt.bg,
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
      );

  Widget _label(String t) => Padding(
        padding: const EdgeInsets.fromLTRB(2, 14, 2, 6),
        child: Text(t, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.ink)),
      );

  @override
  Widget build(BuildContext context) {
    final money = (_currency ?? '').isEmpty ? '' : ' $_currency';
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.92, maxChildSize: 0.96, minChildSize: 0.5,
      builder: (_, sc) => Column(children: [
        Container(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
          decoration: BoxDecoration(
            gradient: LinearGradient(colors: [widget.accent, widget.accent.withValues(alpha: 0.72)],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(22))),
          child: Column(children: [
            Center(child: Container(width: 42, height: 4, decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(4)))),
            const SizedBox(height: 12),
            Row(children: [
              const Text('🛒 ', style: TextStyle(fontSize: 18)),
              Expanded(child: Text(_isEdit ? tr('تعديل أمر الشراء', 'Edit purchase order') : tr('أمر شراء جديد', 'New purchase order'),
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16))),
              IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close_rounded, color: Colors.white)),
            ]),
          ]),
        ),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _err != null
                  ? Center(child: Padding(padding: const EdgeInsets.all(30), child: Text(_err!, textAlign: TextAlign.center, style: const TextStyle(color: Mgmt.slate))))
                  : ListView(controller: sc, padding: const EdgeInsets.fromLTRB(16, 4, 16, 24), children: [
                      _label('${tr('المورّد', 'Vendor')} *'),
                      InkWell(
                        borderRadius: BorderRadius.circular(12), onTap: _pickVendor,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 13),
                          decoration: BoxDecoration(color: Mgmt.bg, borderRadius: BorderRadius.circular(12)),
                          child: Row(children: [
                            Icon(Icons.storefront_rounded, size: 18, color: widget.accent),
                            const SizedBox(width: 10),
                            Expanded(child: Text(_partnerName ?? tr('اختر المورّد', 'Select vendor'),
                                maxLines: 1, overflow: TextOverflow.ellipsis,
                                style: TextStyle(fontSize: 13, color: _partnerName == null ? Mgmt.slate : Mgmt.ink,
                                    fontWeight: _partnerName == null ? FontWeight.w500 : FontWeight.w700))),
                            const Icon(Icons.chevron_left_rounded, color: Mgmt.slate),
                          ]),
                        ),
                      ),
                      // lines
                      Padding(
                        padding: const EdgeInsets.only(top: 16, bottom: 6),
                        child: Row(children: [
                          Text(tr('البنود', 'Lines'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.ink)),
                          const Spacer(),
                          if (_linesEditable)
                            TextButton.icon(onPressed: _addLine, icon: const Icon(Icons.add_rounded, size: 18),
                                style: TextButton.styleFrom(foregroundColor: widget.accent),
                                label: Text(tr('إضافة بند', 'Add line'), style: const TextStyle(fontWeight: FontWeight.w800))),
                        ]),
                      ),
                      if (!_linesEditable)
                        Container(
                          padding: const EdgeInsets.all(10), margin: const EdgeInsets.only(bottom: 6),
                          decoration: BoxDecoration(color: const Color(0xFFF59E0B).withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)),
                          child: Text(tr('لا يمكن تعديل البنود بعد التأكيد — يمكن تعديل بيانات الرأس فقط.', 'Lines are locked after confirmation — header only.'),
                              style: const TextStyle(color: Color(0xFFB45309), fontSize: 11, fontWeight: FontWeight.w700)),
                        ),
                      if (_lines.isEmpty)
                        Padding(padding: const EdgeInsets.symmetric(vertical: 16),
                            child: Center(child: Text(tr('لا بنود بعد', 'No lines yet'), style: const TextStyle(color: Mgmt.slate)))),
                      for (int i = 0; i < _lines.length; i++)
                        Container(
                          margin: const EdgeInsets.only(bottom: 8),
                          padding: const EdgeInsets.all(11),
                          decoration: BoxDecoration(color: Mgmt.bg, borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.black.withValues(alpha: 0.05))),
                          child: Row(children: [
                            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              Text('${_lines[i]['name']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                                  style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: Mgmt.ink)),
                              const SizedBox(height: 3),
                              Text('${_lines[i]['qty']} × ${_lines[i]['price']}$money  =  ${(((_lines[i]['qty'] as num?) ?? 0) * ((_lines[i]['price'] as num?) ?? 0)).toStringAsFixed(3)}$money',
                                  style: TextStyle(color: widget.accent, fontSize: 11.5, fontWeight: FontWeight.w800)),
                            ])),
                            if (_linesEditable) ...[
                              IconButton(onPressed: () => _editLineQtyPrice(i), icon: Icon(Icons.edit_rounded, size: 18, color: widget.accent)),
                              IconButton(onPressed: () => setState(() => _lines.removeAt(i)), icon: const Icon(Icons.delete_outline_rounded, size: 18, color: Mgmt.red)),
                            ],
                          ]),
                        ),
                      // total
                      Container(
                        margin: const EdgeInsets.only(top: 4),
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                        decoration: BoxDecoration(color: widget.accent.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(12)),
                        child: Row(children: [
                          Text(tr('الإجمالي (قبل الضريبة)', 'Subtotal'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.ink)),
                          const Spacer(),
                          Text('${_total.toStringAsFixed(3)}$money', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: widget.accent)),
                        ]),
                      ),
                      _label(tr('مرجع المورّد', 'Vendor reference')),
                      TextField(controller: _ref, decoration: _dec(tr('رقم عرض السعر لدى المورّد', 'Vendor quote ref'))),
                      _label(tr('ملاحظات', 'Notes')),
                      TextField(controller: _notes, maxLines: 3, decoration: _dec(tr('ملاحظات…', 'Notes…'))),
                      const SizedBox(height: 20),
                      SizedBox(
                        height: 50,
                        child: ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(backgroundColor: widget.accent, foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
                          onPressed: _busy ? null : _save,
                          icon: _busy
                              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                              : Icon(_isEdit ? Icons.save_rounded : Icons.add_rounded),
                          label: Text(_isEdit ? tr('حفظ التعديلات', 'Save changes') : tr('إنشاء أمر الشراء', 'Create purchase order'),
                              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
                        ),
                      ),
                    ]),
        ),
      ]),
    );
  }
}

/// Live product search that returns the chosen product {id,name,price,uom}.
class _ProductSearchSheet extends StatefulWidget {
  const _ProductSearchSheet({required this.accent});
  final Color accent;
  @override
  State<_ProductSearchSheet> createState() => _ProductSearchSheetState();
}

class _ProductSearchSheetState extends State<_ProductSearchSheet> {
  Timer? _deb;
  bool _busy = false;
  List<Map> _results = [];

  @override
  void initState() {
    super.initState();
    _search('');
  }

  @override
  void dispose() {
    _deb?.cancel();
    super.dispose();
  }

  void _onChanged(String v) {
    _deb?.cancel();
    _deb = Timer(const Duration(milliseconds: 350), () => _search(v.trim()));
  }

  Future<void> _search(String q) async {
    setState(() => _busy = true);
    try {
      final r = await context.read<AuthProvider>().api.managementProductsSearch(q);
      if (mounted) setState(() { _results = ((r['products'] as List?) ?? const []).cast<Map>(); _busy = false; });
    } catch (_) {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.85, maxChildSize: 0.95, minChildSize: 0.5,
      builder: (_, sc) => Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
          child: Row(children: [
            Expanded(child: Text(tr('اختر منتجًا', 'Select product'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15))),
            IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close_rounded)),
          ]),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: TextField(
            autofocus: true, onChanged: _onChanged,
            decoration: InputDecoration(
              hintText: tr('ابحث بالاسم أو الكود…', 'Search by name or code…'),
              prefixIcon: const Icon(Icons.search_rounded, size: 20),
              suffixIcon: _busy ? const Padding(padding: EdgeInsets.all(12), child: SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))) : null,
              filled: true, fillColor: Mgmt.bg, isDense: true,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            ),
          ),
        ),
        const SizedBox(height: 8),
        Expanded(
          child: _results.isEmpty
              ? Center(child: Text(_busy ? '' : tr('لا نتائج', 'No results'), style: const TextStyle(color: Mgmt.slate)))
              : ListView.separated(
                  controller: sc,
                  itemCount: _results.length,
                  separatorBuilder: (_, __) => Divider(height: 1, color: Colors.grey.shade100),
                  itemBuilder: (_, i) {
                    final p = _results[i];
                    return ListTile(
                      title: Text('${p['name']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600)),
                      subtitle: Text([if ('${p['code'] ?? ''}'.isNotEmpty) '${p['code']}', if (p['uom'] != null) '${p['uom']}'].join(' · '),
                          style: const TextStyle(fontSize: 11, color: Mgmt.slate)),
                      trailing: Text('${p['price']}', style: TextStyle(fontWeight: FontWeight.w900, color: widget.accent)),
                      onTap: () => Navigator.pop(context, Map<String, dynamic>.from(p)),
                    );
                  },
                ),
        ),
      ]),
    );
  }
}

/// A config-driven create form: renders fields from the server's create-meta
/// (char/text/number/date/selection/many2one) and posts a generic create.
class _GenericCreateSheet extends StatefulWidget {
  const _GenericCreateSheet({required this.appKey, required this.accent});
  final String appKey;
  final Color accent;
  @override
  State<_GenericCreateSheet> createState() => _GenericCreateSheetState();
}

class _GenericCreateSheetState extends State<_GenericCreateSheet> {
  bool _loading = true, _busy = false;
  String? _err, _titleAr, _titleEn;
  List<Map> _fields = [];
  final Map<String, dynamic> _vals = {};        // name -> raw value
  final Map<String, String> _labels = {};       // name -> chosen m2o label

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final m = await context.read<AuthProvider>().api.managementCreateMeta(widget.appKey);
      if (mounted) setState(() {
        _fields = ((m['fields'] as List?) ?? const []).cast<Map>();
        _titleAr = '${m['ar']}'; _titleEn = '${m['en']}';
        _loading = false;
      });
    } catch (e) {
      if (mounted) setState(() { _err = '$e'; _loading = false; });
    }
  }

  Future<void> _pickDate(String name) async {
    final cur = _vals[name];
    final init = (cur is String && cur.isNotEmpty) ? DateTime.tryParse(cur) ?? DateTime.now() : DateTime.now();
    final d = await showDatePicker(context: context, initialDate: init, firstDate: DateTime(2010), lastDate: DateTime(2100));
    if (d != null) setState(() => _vals[name] = d.toIso8601String().substring(0, 10));
  }

  Future<void> _pickRelation(Map f) async {
    final name = '${f['name']}';
    if (f['search'] != null) {
      final picked = await showModalBottomSheet<Map>(
        context: context, isScrollControlled: true, backgroundColor: Colors.white,
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
        builder: (_) => RelationSearchSheet(model: '${f['search']}', title: gLang == 'en' ? '${f['en']}' : '${f['ar']}', accent: widget.accent),
      );
      if (picked != null) setState(() { _vals[name] = picked['v']; _labels[name] = '${picked['l']}'; });
    } else {
      final opts = ((f['options'] as List?) ?? const []).cast<Map>();
      final chosen = await showModalBottomSheet<int>(
        context: context, isScrollControlled: true, backgroundColor: Colors.white,
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
        builder: (_) => _PickerSheet(title: gLang == 'en' ? '${f['en']}' : '${f['ar']}', options: opts, accent: widget.accent),
      );
      if (chosen != null) {
        setState(() {
          _vals[name] = chosen;
          _labels[name] = '${opts.firstWhere((o) => o['v'] == chosen, orElse: () => {'l': ''})['l']}';
        });
      }
    }
  }

  Future<void> _submit() async {
    for (final f in _fields) {
      if (f['required'] == true && (_vals['${f['name']}'] == null || '${_vals['${f['name']}']}'.trim().isEmpty)) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(tr('«${f['ar']}» مطلوب', '"${f['en']}" is required')), backgroundColor: Mgmt.red));
        return;
      }
    }
    setState(() => _busy = true);
    try {
      final res = await context.read<AuthProvider>().api.managementGenericCreate(widget.appKey, _vals);
      if (mounted) Navigator.pop(context, res);
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
      }
    }
  }

  InputDecoration _dec(String hint) => InputDecoration(
        hintText: hint, isDense: true, filled: true, fillColor: Mgmt.bg,
        contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
      );

  Widget _fieldWidget(Map f) {
    final name = '${f['name']}';
    final type = '${f['type']}';
    final label = gLang == 'en' ? '${f['en']}' : '${f['ar']}';
    final req = f['required'] == true ? ' *' : '';
    Widget input;
    if (type == 'many2one') {
      input = InkWell(
        borderRadius: BorderRadius.circular(12), onTap: () => _pickRelation(f),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 13),
          decoration: BoxDecoration(color: Mgmt.bg, borderRadius: BorderRadius.circular(12)),
          child: Row(children: [
            Expanded(child: Text(_labels[name] ?? tr('اختر…', 'Select…'), maxLines: 1, overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 13, color: _labels[name] == null ? Mgmt.slate : Mgmt.ink, fontWeight: _labels[name] == null ? FontWeight.w500 : FontWeight.w700))),
            const Icon(Icons.chevron_left_rounded, color: Mgmt.slate),
          ]),
        ),
      );
    } else if (type == 'selection') {
      final opts = ((f['options'] as List?) ?? const []).cast<Map>();
      input = Container(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        decoration: BoxDecoration(color: Mgmt.bg, borderRadius: BorderRadius.circular(12)),
        child: DropdownButtonHideUnderline(
          child: DropdownButton<String>(
            value: _vals[name] as String?, isExpanded: true, hint: Text(tr('اختر', 'Select'), style: const TextStyle(fontSize: 13, color: Mgmt.slate)),
            items: [for (final o in opts) DropdownMenuItem(value: '${o['v']}', child: Text('${o['l']}', style: const TextStyle(fontSize: 13)))],
            onChanged: (v) => setState(() => _vals[name] = v),
          ),
        ),
      );
    } else if (type == 'date') {
      input = InkWell(
        borderRadius: BorderRadius.circular(12), onTap: () => _pickDate(name),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 13),
          decoration: BoxDecoration(color: Mgmt.bg, borderRadius: BorderRadius.circular(12)),
          child: Row(children: [
            Icon(Icons.event_rounded, size: 18, color: widget.accent), const SizedBox(width: 10),
            Text('${_vals[name] ?? tr('اختر التاريخ', 'Pick date')}', style: TextStyle(fontSize: 13, color: _vals[name] == null ? Mgmt.slate : Mgmt.ink, fontWeight: FontWeight.w700)),
          ]),
        ),
      );
    } else {
      input = TextField(
        keyboardType: (type == 'float' || type == 'monetary' || type == 'integer') ? TextInputType.number : null,
        maxLines: type == 'text' ? 3 : 1,
        onChanged: (v) => _vals[name] = v,
        decoration: _dec(label),
      );
    }
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Padding(padding: const EdgeInsets.fromLTRB(2, 14, 2, 6),
          child: Text('$label$req', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: Mgmt.ink))),
      input,
    ]);
  }

  @override
  Widget build(BuildContext context) {
    final title = gLang == 'en' ? (_titleEn ?? 'Create') : (_titleAr ?? 'إضافة');
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.9, maxChildSize: 0.96, minChildSize: 0.5,
      builder: (_, sc) => Column(children: [
        Container(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
          decoration: BoxDecoration(
            gradient: LinearGradient(colors: [widget.accent, widget.accent.withValues(alpha: 0.72)], begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: const BorderRadius.vertical(top: Radius.circular(22))),
          child: Column(children: [
            Center(child: Container(width: 42, height: 4, decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(4)))),
            const SizedBox(height: 12),
            Row(children: [
              const Icon(Icons.add_circle_rounded, color: Colors.white), const SizedBox(width: 8),
              Expanded(child: Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16))),
              IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close_rounded, color: Colors.white)),
            ]),
          ]),
        ),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _err != null
                  ? Center(child: Padding(padding: const EdgeInsets.all(30), child: Text(_err!, textAlign: TextAlign.center, style: const TextStyle(color: Mgmt.slate))))
                  : ListView(controller: sc, padding: const EdgeInsets.fromLTRB(16, 4, 16, 24), children: [
                      for (final f in _fields) _fieldWidget(f),
                      const SizedBox(height: 22),
                      SizedBox(
                        height: 50,
                        child: ElevatedButton.icon(
                          style: ElevatedButton.styleFrom(backgroundColor: widget.accent, foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
                          onPressed: _busy ? null : _submit,
                          icon: _busy ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Icon(Icons.check_rounded),
                          label: Text(tr('إنشاء', 'Create'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
                        ),
                      ),
                    ]),
        ),
      ]),
    );
  }
}

/// Live relation search (res.partner / hr.employee / fleet.vehicle …) → {v,l}.
class RelationSearchSheet extends StatefulWidget {
  const RelationSearchSheet({required this.model, required this.title, required this.accent});
  final String model, title;
  final Color accent;
  @override
  State<RelationSearchSheet> createState() => RelationSearchSheetState();
}

class RelationSearchSheetState extends State<RelationSearchSheet> {
  Timer? _deb;
  bool _busy = false;
  List<Map> _results = [];

  @override
  void initState() {
    super.initState();
    _search('');
  }

  @override
  void dispose() {
    _deb?.cancel();
    super.dispose();
  }

  void _onChanged(String v) {
    _deb?.cancel();
    _deb = Timer(const Duration(milliseconds: 350), () => _search(v.trim()));
  }

  Future<void> _search(String q) async {
    setState(() => _busy = true);
    try {
      final r = await context.read<AuthProvider>().api.managementRelationSearch(widget.model, q);
      if (mounted) setState(() { _results = ((r['options'] as List?) ?? const []).cast<Map>(); _busy = false; });
    } catch (_) {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.85, maxChildSize: 0.95, minChildSize: 0.5,
      builder: (_, sc) => Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 14, 16, 8),
          child: Row(children: [
            Expanded(child: Text(widget.title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15))),
            IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close_rounded)),
          ]),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: TextField(
            autofocus: true, onChanged: _onChanged,
            decoration: InputDecoration(
              hintText: tr('ابحث…', 'Search…'),
              prefixIcon: const Icon(Icons.search_rounded, size: 20),
              suffixIcon: _busy ? const Padding(padding: EdgeInsets.all(12), child: SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))) : null,
              filled: true, fillColor: Mgmt.bg, isDense: true,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            ),
          ),
        ),
        const SizedBox(height: 8),
        Expanded(
          child: ListView.separated(
            controller: sc,
            itemCount: _results.length,
            separatorBuilder: (_, __) => Divider(height: 1, color: Colors.grey.shade100),
            itemBuilder: (_, i) => ListTile(
              title: Text('${_results[i]['l']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600)),
              onTap: () => Navigator.pop(context, Map<String, dynamic>.from(_results[i])),
            ),
          ),
        ),
      ]),
    );
  }
}
