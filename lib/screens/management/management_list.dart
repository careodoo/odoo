import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'management_home.dart' show Mgmt;
import '../pdf_report_screen.dart';
import '../excel_export.dart';

/// Native list for one management system (purchases, tenders, employees, …).
/// The server returns only rows this user may read.
class ManagementListScreen extends StatefulWidget {
  const ManagementListScreen({
    super.key, required this.appKey, required this.title, required this.icon, required this.accent});
  final String appKey, title, icon;
  final Color accent;

  @override
  State<ManagementListScreen> createState() => _ManagementListScreenState();
}

class _ManagementListScreenState extends State<ManagementListScreen> {
  late Future<Map<String, dynamic>> _f;
  final _search = TextEditingController();
  Timer? _debounce;
  String _q = '';

  @override
  void initState() {
    super.initState();
    _reload();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _search.dispose();
    super.dispose();
  }

  void _reload() => setState(
      () => _f = context.read<AuthProvider>().api.managementList(widget.appKey, q: _q));

  void _onSearch(String v) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 420), () {
      if (!mounted) return;
      _q = v.trim();
      _reload();
    });
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
                return ListView.separated(
                  padding: const EdgeInsets.fromLTRB(12, 8, 12, 20),
                  itemCount: rows.length + 1,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (_, i) {
                    if (i == 0) {
                      return Padding(
                        padding: const EdgeInsets.only(bottom: 4),
                        child: Text(
                            tr('عرض ${rows.length} من $total', 'Showing ${rows.length} of $total'),
                            style: const TextStyle(color: Mgmt.slate, fontSize: 11.5, fontWeight: FontWeight.w700)),
                      );
                    }
                    return _row(rows[i - 1] as Map);
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
              if (r['image'] != null)
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
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(color: widget.accent.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(20)),
                    child: Text('${r['state']}', style: TextStyle(color: widget.accent, fontSize: 10, fontWeight: FontWeight.w800)),
                  ),
                ),
              ]),
            ]),
          ),
        ),
      );

  Widget _avatar(Map r) => Container(
        width: 40, height: 40,
        decoration: BoxDecoration(color: widget.accent.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(10)),
        alignment: Alignment.center,
        child: Text('${r['title']}'.trim().isEmpty ? '?' : '${r['title']}'.trim().characters.first,
            style: TextStyle(color: widget.accent, fontWeight: FontWeight.w900)),
      );

  Future<void> _openDetail(int id, String title) async {
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

  @override
  Widget build(BuildContext context) {
    final actions = (d['actions'] as List?) ?? [];
    final sections = (d['sections'] as List?) ?? [];
    final canEdit = d['can_edit'] == true;
    final amount = d['amount'];
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
                  padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 4),
                  decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.22), borderRadius: BorderRadius.circular(20)),
                  child: Text('${d['state']}',
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 11.5)),
                ),
              ),
            ]),
          ),
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
          // ---- actions
          if (actions.isNotEmpty) Padding(
            padding: const EdgeInsets.fromLTRB(14, 14, 14, 2),
            child: Wrap(spacing: 8, runSpacing: 8, children: [
              for (final a in actions)
                SizedBox(
                  height: 42,
                  child: (a as Map)['style'] == 'primary'
                      ? ElevatedButton(
                          style: ElevatedButton.styleFrom(
                              backgroundColor: widget.accent, foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                          onPressed: _busy ? null : () => _run(a),
                          child: Text(gLang == 'en' ? '${a['en']}' : '${a['ar']}',
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
          ),
          // ---- reports (pdf viewer / xlsx download)
          _reportsCard(),
          // ---- line items
          _linesCard(),
          // ---- professional grouped sections
          for (final s in sections) _sectionCard(s as Map),
          // fallback flat list if the server sent no sections
          if (sections.isEmpty)
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
