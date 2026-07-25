import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import '../models/models.dart';
import 'work_order_detail_screen.dart';

const _navy = Color(0xFF0E3A5F);
// ثيم داكن متّسق مع تطبيق الأمن
const _dbg = Color(0xFF0B1220);
const _dcard = Color(0xFF152238);
const _dtext = Color(0xFFEAF1FB);
const _dgrey = Color(0xFF9CB2CD);
const _dborder = Color(0xFF24344C);

/// My work orders — a professional register: a live count strip, state filters
/// and search, then rich cards. Actions (start / finish / proof) live inside the
/// record's own screen, not scattered across the list.
class WorkOrdersScreen extends StatefulWidget {
  const WorkOrdersScreen({super.key});
  @override
  State<WorkOrdersScreen> createState() => _WorkOrdersScreenState();
}

class _WorkOrdersScreenState extends State<WorkOrdersScreen> {
  late Future<List<WorkOrder>> _future;
  String _filter = 'all';
  String _q = '';

  static const _filters = [
    ('all', 'الكل', 'All'),
    ('open', 'مفتوحة', 'Open'),
    ('in_progress', 'قيد التنفيذ', 'Active'),
    ('overdue', 'متأخرة', 'Overdue'),
    ('done', 'منجزة', 'Done'),
  ];
  static const _prioColors = {
    '0': Color(0xFF64748B), '1': Color(0xFF0891B2),
    '2': Color(0xFFF7A23B), '3': Color(0xFFE5484D),
  };
  static const _prioLabels = {
    '0': ('منخفضة', 'Low'), '1': ('عادية', 'Normal'),
    '2': ('عالية', 'High'), '3': ('عاجلة', 'Urgent'),
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    final api = context.read<AuthProvider>().api;
    _future = api.workOrders().then((l) => [for (final j in l) WorkOrder.fromJson(j as Map)]);
  }

  bool _isOverdue(WorkOrder w) {
    if (!w.isOpen || w.deadline == null) return false;
    final d = DateTime.tryParse('${w.deadline}'.replaceFirst(' ', 'T'));
    return d != null && d.toLocal().isBefore(DateTime.now());
  }

  List<WorkOrder> _apply(List<WorkOrder> all) {
    var list = all;
    switch (_filter) {
      case 'open': list = list.where((w) => w.isOpen).toList(); break;
      case 'in_progress': list = list.where((w) => w.inProgress).toList(); break;
      case 'overdue': list = list.where(_isOverdue).toList(); break;
      case 'done': list = list.where((w) => !w.isOpen).toList(); break;
    }
    if (_q.isNotEmpty) {
      final q = _q.toLowerCase();
      list = list.where((w) =>
          '${w.title} ${w.name} ${w.facility} ${w.location ?? ''}'.toLowerCase().contains(q)).toList();
    }
    // most urgent first: overdue, then in-progress, then by priority
    list.sort((a, b) {
      final oa = _isOverdue(a) ? 0 : 1, ob = _isOverdue(b) ? 0 : 1;
      if (oa != ob) return oa - ob;
      final ia = a.inProgress ? 0 : 1, ib = b.inProgress ? 0 : 1;
      if (ia != ib) return ia - ib;
      return int.parse(b.priority).compareTo(int.parse(a.priority));
    });
    return list;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _dbg,
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E3A5F), foregroundColor: Colors.white,
        title: Text(tr('أوامر العمل', 'Work orders'), style: const TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: RefreshIndicator(
        color: _navy,
        onRefresh: () async => setState(_load),
        child: FutureBuilder<List<WorkOrder>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator(color: _navy));
            }
            if (snap.hasError) return _msg('${snap.error}');
            final all = snap.data ?? const <WorkOrder>[];
            final shown = _apply(all);
            return Column(children: [
              _counts(all),
              _search(),
              _chips(),
              Expanded(child: shown.isEmpty
                  ? _msg(all.isEmpty
                      ? tr('لا توجد أوامر عمل حالياً', 'No work orders yet')
                      : tr('لا نتائج في هذا التصنيف', 'Nothing in this filter'))
                  : ListView.builder(
                      padding: const EdgeInsets.fromLTRB(12, 4, 12, 20),
                      itemCount: shown.length,
                      itemBuilder: (_, i) => _card(shown[i]),
                    )),
            ]);
          },
        ),
      ),
    );
  }

  Widget _counts(List<WorkOrder> all) {
    final open = all.where((w) => w.isOpen).length;
    final active = all.where((w) => w.inProgress).length;
    final late = all.where(_isOverdue).length;
    final done = all.where((w) => !w.isOpen).length;
    Widget cell(String v, String l, Color c) => Expanded(child: Column(children: [
          Text(v, style: TextStyle(color: c, fontSize: 17, fontWeight: FontWeight.w900)),
          Text(l, style: const TextStyle(fontSize: 10, color: _dgrey, fontWeight: FontWeight.w700)),
        ]));
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 10, 12, 2),
      padding: const EdgeInsets.symmetric(vertical: 12),
      decoration: BoxDecoration(color: _dcard, borderRadius: BorderRadius.circular(14), border: Border.all(color: _dborder)),
      child: Row(children: [
        cell('$open', tr('مفتوحة', 'Open'), const Color(0xFF0891B2)),
        cell('$active', tr('قيد التنفيذ', 'Active'), const Color(0xFFF7A23B)),
        cell('$late', tr('متأخرة', 'Overdue'), const Color(0xFFE5484D)),
        cell('$done', tr('منجزة', 'Done'), const Color(0xFF16A34A)),
      ]),
    );
  }

  Widget _search() => Padding(
        padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
        child: TextField(
          onChanged: (v) => setState(() => _q = v),
          style: const TextStyle(color: _dtext),
          decoration: InputDecoration(
            hintText: tr('بحث بالعنوان أو الرقم أو الموقع…', 'Search title, ref or location…'),
            hintStyle: const TextStyle(color: _dgrey),
            prefixIcon: const Icon(Icons.search_rounded, size: 20, color: _dgrey),
            filled: true, fillColor: _dcard, isDense: true,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: _dborder)),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: _dborder)),
          ),
        ),
      );

  Widget _chips() => SizedBox(
        height: 42,
        child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 8), children: [
          for (final f in _filters) Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
            child: ChoiceChip(
              selected: _filter == f.$1,
              label: Text(tr(f.$2, f.$3), style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: _filter == f.$1 ? Colors.white : _dgrey)),
              selectedColor: const Color(0xFF1E3A5F), backgroundColor: _dcard,
              side: BorderSide(color: _filter == f.$1 ? const Color(0xFF4AA8FF) : _dborder),
              onSelected: (_) => setState(() => _filter = f.$1),
            ),
          ),
        ]),
      );

  /// A record card. Everything you can *do* with it lives inside the record —
  /// tapping opens the detail screen where start / finish / proof live.
  Widget _card(WorkOrder w) {
    final late = _isOverdue(w);
    final pc = _prioColors[w.priority] ?? const Color(0xFF0891B2);
    final stripe = late ? const Color(0xFFE5484D) : (w.inProgress ? const Color(0xFFF7A23B) : pc);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Material(
        color: _dcard, borderRadius: BorderRadius.circular(15),
        child: InkWell(
          borderRadius: BorderRadius.circular(15),
          onTap: () async {
            await Navigator.push(context, MaterialPageRoute(
                builder: (_) => WorkOrderDetailScreen(id: w.id, title: w.title)));
            if (mounted) setState(_load);
          },
          child: Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(15),
              border: Border.all(color: late ? const Color(0xFFE5484D).withValues(alpha: 0.45) : _dborder),
            ),
            padding: const EdgeInsets.all(12),
            child: Row(children: [
              Container(width: 5, height: 58, decoration: BoxDecoration(color: stripe, borderRadius: BorderRadius.circular(4))),
              const SizedBox(width: 12),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text(w.title, maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w900, color: _dtext))),
                  WoStateBadge(w.state),
                ]),
                const SizedBox(height: 5),
                Row(children: [
                  Icon(Icons.apartment_rounded, size: 13, color: _dgrey),
                  const SizedBox(width: 4),
                  Expanded(child: Text('${w.facility}${w.location != null ? ' · ${w.location}' : ''}',
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 11.5, color: _dgrey))),
                ]),
                const SizedBox(height: 7),
                Wrap(spacing: 6, runSpacing: 5, children: [
                  _tag(w.name, const Color(0xFF64748B)),
                  _tag(tr(_prioLabels[w.priority]?.$1 ?? '', _prioLabels[w.priority]?.$2 ?? ''), pc),
                  if (w.deadline != null)
                    _tag('${late ? '⚠ ' : '🕐 '}${_shortDate(w.deadline!)}',
                        late ? const Color(0xFFE5484D) : const Color(0xFF0891B2)),
                  if (w.inProgress && w.durationMinutes > 0)
                    _tag('⏱ ${w.durationMinutes.round()}${tr('د', 'm')}', const Color(0xFFF7A23B)),
                ]),
              ])),
              const SizedBox(width: 4),
              const Icon(Icons.chevron_left_rounded, color: _dgrey, size: 20),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _tag(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(7)),
        child: Text(t, style: TextStyle(color: c, fontSize: 10, fontWeight: FontWeight.w800)),
      );

  String _shortDate(String dt) => dt.length >= 16 ? dt.substring(5, 16) : dt;

  Widget _msg(String text) => ListView(children: [
        const SizedBox(height: 100),
        Icon(Icons.assignment_outlined, size: 56, color: _dborder),
        const SizedBox(height: 12),
        Center(child: Text(text, textAlign: TextAlign.center,
            style: TextStyle(color: _dgrey, fontWeight: FontWeight.w600))),
      ]);
}
