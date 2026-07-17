import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'pdf_report_screen.dart';
import 'excel_export.dart';

/// Every attendance record for a single worker on this client's sites — with
/// period filters, a search box, headline stats, and print / Excel export.
class EmployeeAttendanceScreen extends StatefulWidget {
  const EmployeeAttendanceScreen({super.key, required this.employeeId, required this.name});
  final int employeeId;
  final String name;
  @override
  State<EmployeeAttendanceScreen> createState() => _EmployeeAttendanceScreenState();
}

class _EmployeeAttendanceScreenState extends State<EmployeeAttendanceScreen> {
  Future<Map<String, dynamic>>? _future;
  String _period = 'month';
  String _query = '';
  String _stateFilter = 'all'; // all / open / closed / incomplete

  static const _navy = Color(0xFF0E3A5F);
  static const _accent = Color(0xFFC0392B);
  static const _periods = [
    ('day', 'اليوم', 'Today'), ('week', 'الأسبوع', 'Week'),
    ('month', 'الشهر', 'Month'), ('year', 'السنة', 'Year'), ('all', 'الكل', 'All'),
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api
      .clientEmployeeAttendance(widget.employeeId, period: _period);

  void _print() => Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
        title: tr('سجل حضور ${widget.name}', '${widget.name} attendance'),
        path: '/cafm/attendance/report?period=$_period&employee_id=${widget.employeeId}',
      )));

  void _excel() => exportExcelFile(context,
      path: '/cafm/attendance/export?period=$_period&employee_id=${widget.employeeId}',
      fileName: 'attendance-${widget.employeeId}-$_period.xlsx',
      shareText: tr('سجل حضور ${widget.name}', '${widget.name} attendance'));

  bool _matchRecord(Map r) {
    if (_stateFilter == 'open' && r['open'] != true) return false;
    if (_stateFilter == 'closed' && (r['open'] == true)) return false;
    if (_stateFilter == 'incomplete' && !(r['open'] != true && r['check_out'] == null)) return false;
    if (_query.isEmpty) return true;
    final q = _query.toLowerCase();
    return '${r['facility'] ?? ''}${r['date'] ?? ''}'.toLowerCase().contains(q);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F7F9),
      appBar: AppBar(
        title: Text(tr('سجل الحضور', 'Attendance log')),
        backgroundColor: _accent, foregroundColor: Colors.white,
        actions: [
          IconButton(icon: const Icon(Icons.grid_on_rounded), tooltip: tr('تصدير Excel', 'Export Excel'), onPressed: _excel),
          IconButton(icon: const Icon(Icons.print_rounded), tooltip: tr('طباعة', 'Print'), onPressed: _print),
        ],
      ),
      body: Column(children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Row(children: [
            for (final p in _periods)
              Padding(padding: const EdgeInsets.only(left: 6), child: ChoiceChip(
                label: Text(tr(p.$2, p.$3), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
                selected: _period == p.$1,
                selectedColor: _accent,
                labelStyle: TextStyle(color: _period == p.$1 ? Colors.white : _navy, fontWeight: FontWeight.w700),
                onSelected: (_) => setState(() { _period = p.$1; _load(); }),
              )),
          ]),
        ),
        Expanded(child: FutureBuilder<Map<String, dynamic>>(
          future: _future,
          builder: (_, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator(color: _accent));
            }
            if (snap.hasError) return Center(child: Text('${snap.error}', style: const TextStyle(color: Colors.grey)));
            final d = snap.data ?? const {};
            final records = ((d['records'] as List?) ?? const []).cast<Map>();
            final totals = (d['totals'] as Map?) ?? const {};
            final worker = ((d['workers'] as List?) ?? const []).cast<Map>();
            final w = worker.isNotEmpty ? worker.first : const {};
            final shown = records.where(_matchRecord).toList();
            return RefreshIndicator(
              color: _accent,
              onRefresh: () async => setState(_load),
              child: ListView(padding: const EdgeInsets.fromLTRB(12, 4, 12, 24), children: [
                _statsCard(totals, w),
                const SizedBox(height: 12),
                _searchBar(),
                const SizedBox(height: 8),
                _stateChips(records),
                const SizedBox(height: 10),
                Row(children: [
                  Text(tr('السجلات (${shown.length})', 'Records (${shown.length})'),
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
                ]),
                const SizedBox(height: 6),
                if (shown.isEmpty)
                  Padding(padding: const EdgeInsets.all(34), child: Center(
                      child: Text(tr('لا سجلات مطابقة', 'No matching records'),
                          style: TextStyle(color: Colors.grey.shade500)))),
                ...shown.map(_recordCard),
              ]),
            );
          },
        )),
      ]),
    );
  }

  Widget _statsCard(Map t, Map w) {
    return CustomPaint(
      painter: const BrandPattern(opacity: 0.06),
      child: Container(
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [Color(0xFF17547F), _navy],
              begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.circular(18),
        ),
        child: Column(children: [
          Row(children: [
            _s('${w['days'] ?? t['days_covered'] ?? 0}', tr('يوم', 'Days'), Icons.event_rounded),
            _div(),
            _s('${w['shifts'] ?? t['records'] ?? 0}', tr('وردية', 'Shifts'), Icons.badge_rounded),
            _div(),
            _s('${w['hours'] ?? t['total_hours'] ?? 0}', tr('ساعة', 'Hours'), Icons.schedule_rounded),
            _div(),
            _s('${w['avg_hours'] ?? t['avg_hours'] ?? 0}', tr('متوسط/يوم', 'Avg/day'), Icons.trending_up_rounded),
          ]),
          if (((w['incomplete'] ?? t['incomplete'] ?? 0) as int) > 0) ...[
            const SizedBox(height: 10),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
              decoration: BoxDecoration(color: const Color(0xFFFCA5A5).withValues(alpha: 0.18), borderRadius: BorderRadius.circular(10)),
              child: Row(children: [
                const Icon(Icons.error_outline_rounded, size: 14, color: Color(0xFFFCA5A5)),
                const SizedBox(width: 6),
                Text(tr('${w['incomplete'] ?? t['incomplete']} وردية بلا انصراف مسجّل',
                        '${w['incomplete'] ?? t['incomplete']} shifts with no punch-out'),
                    style: const TextStyle(color: Color(0xFFFCA5A5), fontSize: 10.5, fontWeight: FontWeight.w700)),
              ]),
            ),
          ],
        ]),
      ),
    );
  }

  Widget _s(String v, String l, IconData ic) => Expanded(child: Column(children: [
        Icon(ic, color: Colors.white70, size: 15),
        const SizedBox(height: 3),
        Text(v, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900)),
        Text(l, maxLines: 1, overflow: TextOverflow.ellipsis,
            style: TextStyle(color: Colors.white.withValues(alpha: 0.72), fontSize: 8.5, fontWeight: FontWeight.w700)),
      ]));

  Widget _div() => Container(width: 1, height: 30, color: Colors.white.withValues(alpha: 0.15));

  Widget _searchBar() => TextField(
        onChanged: (v) => setState(() => _query = v),
        decoration: InputDecoration(
          hintText: tr('ابحث بالمنشأة أو التاريخ…', 'Search facility or date…'),
          prefixIcon: const Icon(Icons.search_rounded, size: 20),
          isDense: true, filled: true, fillColor: Colors.white,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: _accent, width: 1.5)),
        ),
      );

  Widget _stateChips(List<Map> records) {
    final open = records.where((r) => r['open'] == true).length;
    final incomplete = records.where((r) => r['open'] != true && r['check_out'] == null).length;
    final chips = [
      ('all', tr('الكل', 'All'), records.length),
      ('open', tr('مفتوحة', 'Open'), open),
      ('closed', tr('مغلقة', 'Closed'), records.length - open),
      ('incomplete', tr('ناقصة', 'Incomplete'), incomplete),
    ];
    return SizedBox(
      height: 34,
      child: ListView(scrollDirection: Axis.horizontal, children: [
        for (final ch in chips)
          Padding(padding: const EdgeInsets.only(left: 7), child: ChoiceChip(
            selected: _stateFilter == ch.$1,
            showCheckmark: false,
            visualDensity: VisualDensity.compact,
            label: Text('${ch.$2} (${ch.$3})',
                style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800,
                    color: _stateFilter == ch.$1 ? Colors.white : _navy)),
            selectedColor: _navy,
            backgroundColor: Colors.white,
            side: BorderSide(color: _stateFilter == ch.$1 ? _navy : Colors.grey.shade300),
            onSelected: (_) => setState(() => _stateFilter = ch.$1),
          )),
      ]),
    );
  }

  Widget _recordCard(Map r) {
    final open = r['open'] == true;
    final incomplete = !open && r['check_out'] == null;
    final c = open ? const Color(0xFF16A34A) : (incomplete ? const Color(0xFFE5484D) : const Color(0xFF0891B2));
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white, borderRadius: BorderRadius.circular(14),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 6, offset: const Offset(0, 3))],
      ),
      child: Row(children: [
        Container(width: 4, height: 42, decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(2))),
        const SizedBox(width: 11),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.event_rounded, size: 13, color: _navy),
            const SizedBox(width: 5),
            Text('${r['date'] ?? '—'}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: _navy)),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
              child: Text(open ? tr('مفتوحة', 'Open') : (incomplete ? tr('ناقصة', 'Incomplete') : tr('مغلقة', 'Closed')),
                  style: TextStyle(color: c, fontSize: 9.5, fontWeight: FontWeight.w900)),
            ),
          ]),
          const SizedBox(height: 5),
          Row(children: [
            _chip(Icons.login_rounded, _hm(r['check_in']), const Color(0xFF16A34A)),
            const SizedBox(width: 6),
            _chip(Icons.logout_rounded, _hm(r['check_out']), const Color(0xFFE5484D)),
            const SizedBox(width: 6),
            _chip(Icons.timelapse_rounded, tr('${r['hours'] ?? 0} س', '${r['hours'] ?? 0}h'), const Color(0xFF0891B2)),
          ]),
          if (r['facility'] != null) ...[
            const SizedBox(height: 4),
            Row(children: [
              Icon(Icons.place_rounded, size: 11, color: Colors.grey.shade500),
              const SizedBox(width: 3),
              Flexible(child: Text('${r['facility']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 10.5, color: Colors.grey.shade600))),
            ]),
          ],
        ])),
      ]),
    );
  }

  Widget _chip(IconData ic, String v, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(7)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(ic, size: 11, color: c),
          const SizedBox(width: 3),
          Text(v, style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: c)),
        ]),
      );

  String _hm(dynamic v) {
    final s = '${v ?? ''}';
    if (s.length < 16) return '—';
    return s.substring(11, 16);
  }
}
