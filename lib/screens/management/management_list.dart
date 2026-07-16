import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'management_home.dart' show Mgmt;

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

  @override
  Widget build(BuildContext context) {
    final actions = (d['actions'] as List?) ?? [];
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.75, maxChildSize: 0.95, minChildSize: 0.4,
      builder: (_, sc) => ListView(controller: sc, padding: EdgeInsets.zero, children: [
          Container(
            padding: const EdgeInsets.fromLTRB(20, 14, 20, 18),
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: [widget.accent, widget.accent.withValues(alpha: 0.75)],
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
              ]),
              if (d['state'] != null) Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 4),
                  decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(20)),
                  child: Text('${d['state']}',
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 11.5)),
                ),
              ),
            ]),
          ),
          if (actions.isNotEmpty) Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 2),
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
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 12, 18, 24),
            child: Column(children: [
              for (final f in (d['fields'] as List? ?? []))
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    SizedBox(width: 118, child: Text('${(f as Map)['label']}',
                        style: const TextStyle(color: Mgmt.slate, fontSize: 12))),
                    Expanded(child: Text('${f['value']}',
                        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: Mgmt.ink))),
                  ]),
                ),
            ]),
          ),
        ]),
    );
  }
}
