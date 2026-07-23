import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'management_home.dart' show Mgmt;
import 'management_list.dart';

/// Global search across every management system — one box, results grouped by
/// system. Tapping a result opens the record (employee file or detail sheet).
class ManagementSearchScreen extends StatefulWidget {
  const ManagementSearchScreen({super.key});
  @override
  State<ManagementSearchScreen> createState() => _ManagementSearchScreenState();
}

class _ManagementSearchScreenState extends State<ManagementSearchScreen> {
  final _ctrl = TextEditingController();
  Timer? _debounce;
  Future<Map<String, dynamic>>? _f;
  String _q = '';

  static const _tint = {
    'purchases': Color(0xFF7C3AED), 'sales': Color(0xFF16A34A), 'tenders': Color(0xFF0891B2),
    'proposals': Color(0xFF9333EA), 'employees': Color(0xFF0D9488), 'leaves': Color(0xFF0EA5E9),
    'expenses': Color(0xFFEA580C), 'invoices': Color(0xFF9D174D), 'experience': Color(0xFFF59E0B),
    'legal': Color(0xFF7C2D12), 'payslips': Color(0xFF16A34A), 'payroll': Color(0xFF15803D),
    'hostels': Color(0xFFB45309), 'hostel_beds': Color(0xFF334155), 'crm': Color(0xFFDB2777),
  };

  @override
  void dispose() { _debounce?.cancel(); _ctrl.dispose(); super.dispose(); }

  void _onChanged(String v) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 400), () {
      final t = v.trim();
      if (!mounted || t == _q) return;
      setState(() {
        _q = t;
        _f = t.length < 2 ? null : context.read<AuthProvider>().api.managementSearch(t);
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Mgmt.bg,
      appBar: AppBar(
        backgroundColor: Mgmt.red, foregroundColor: Colors.white, elevation: 0,
        title: TextField(
          controller: _ctrl, autofocus: true, onChanged: _onChanged,
          style: const TextStyle(color: Colors.white, fontSize: 16),
          cursorColor: Colors.white,
          decoration: InputDecoration(
            hintText: tr('ابحث في كل الأنظمة…', 'Search all systems…'),
            hintStyle: const TextStyle(color: Colors.white70),
            border: InputBorder.none,
            suffixIcon: _q.isEmpty ? null : IconButton(
              icon: const Icon(Icons.close_rounded, color: Colors.white70),
              onPressed: () { _ctrl.clear(); setState(() { _q = ''; _f = null; }); }),
          ),
        ),
      ),
      body: _f == null
          ? _hint()
          : FutureBuilder<Map<String, dynamic>>(
              future: _f,
              builder: (_, snap) {
                if (snap.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snap.hasError) {
                  return Center(child: Padding(padding: const EdgeInsets.all(24),
                      child: Text('${snap.error}', textAlign: TextAlign.center, style: const TextStyle(color: Mgmt.slate))));
                }
                final d = snap.data ?? const {};
                final groups = (d['groups'] as List?) ?? const [];
                final total = d['total'] ?? 0;
                if (groups.isEmpty) {
                  return _msg(Icons.search_off_rounded, tr('لا نتائج', 'No results'),
                      tr('جرّب كلمة أخرى', 'Try another term'));
                }
                return ListView(padding: const EdgeInsets.fromLTRB(12, 10, 12, 24), children: [
                  Padding(padding: const EdgeInsets.only(bottom: 6, right: 4),
                      child: Text(tr('$total نتيجة', '$total results'),
                          style: const TextStyle(color: Mgmt.slate, fontSize: 12, fontWeight: FontWeight.w700))),
                  for (final g in groups.cast<Map>()) _group(g),
                ]);
              },
            ),
    );
  }

  Widget _hint() => _msg(Icons.travel_explore_rounded, tr('بحث شامل', 'Global search'),
      tr('اكتب حرفين على الأقل للبحث في كل أنظمة الإدارة', 'Type at least 2 characters to search every system'));

  Widget _group(Map g) {
    final c = _tint['${g['key']}'] ?? Mgmt.slate;
    final rows = (g['rows'] as List?) ?? const [];
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
      clipBehavior: Clip.antiAlias,
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          padding: const EdgeInsets.fromLTRB(12, 10, 12, 9),
          decoration: BoxDecoration(border: Border(bottom: BorderSide(color: Colors.grey.shade100))),
          child: Row(children: [
            Text('${g['icon']} ', style: const TextStyle(fontSize: 15)),
            Text(gLang == 'en' ? '${g['en']}' : '${g['ar']}',
                style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: c)),
            const Spacer(),
            if (numOf(g['count'], 0) > rows.length)
              TextButton(
                onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => ManagementListScreen(
                    appKey: '${g['key']}', title: gLang == 'en' ? '${g['en']}' : '${g['ar']}', icon: '${g['icon']}', accent: c))),
                child: Text(tr('عرض الكل (${g['count']})', 'View all (${g['count']})'), style: TextStyle(fontSize: 11.5, color: c)),
              ),
          ]),
        ),
        for (final r in rows.cast<Map>())
          InkWell(
            onTap: () => openManagementRecord(context, '${g['key']}', r['id'] as int, title: '${r['title']}', accent: c),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              child: Row(children: [
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${r['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: Mgmt.ink)),
                  if (r['subtitle'] != null) Text('${r['subtitle']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Mgmt.slate, fontSize: 11)),
                ])),
                if (r['amount'] != null) Padding(padding: const EdgeInsets.only(left: 8),
                    child: Text('${r['amount']}', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12, color: c))),
                if (r['state'] != null) Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                  decoration: BoxDecoration(color: c.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(7)),
                  child: Text('${r['state']}', style: TextStyle(color: c, fontSize: 9, fontWeight: FontWeight.w800)),
                ),
                const Icon(Icons.chevron_left_rounded, color: Mgmt.slate, size: 18),
              ]),
            ),
          ),
      ]),
    );
  }

  Widget _msg(IconData i, String t, String s) => Center(child: Padding(padding: const EdgeInsets.all(30),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(i, size: 46, color: Mgmt.slate),
          const SizedBox(height: 12),
          Text(t, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15, color: Mgmt.ink)),
          const SizedBox(height: 6),
          Text(s, textAlign: TextAlign.center, style: const TextStyle(color: Mgmt.slate, fontSize: 12)),
        ])));
}
