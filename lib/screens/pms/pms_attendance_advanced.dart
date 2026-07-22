import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'pms_shell.dart' show Pms;
import '../pdf_report_screen.dart';

/// Rich attendance view for a project: filter by month / date range / worker /
/// status, with live KPIs and a printable PDF report.
class AttendanceAdvancedScreen extends StatefulWidget {
  final int projectId;
  final String projectName;
  const AttendanceAdvancedScreen({super.key, required this.projectId, this.projectName = ''});
  @override
  State<AttendanceAdvancedScreen> createState() => _AttendanceAdvancedScreenState();
}

class _AttendanceAdvancedScreenState extends State<AttendanceAdvancedScreen> {
  // filters
  String _mode = 'month'; // 'month' | 'range'
  DateTime _month = DateTime(DateTime.now().year, DateTime.now().month);
  DateTime? _from, _to;
  int? _employeeId;
  String _status = 'all'; // all | present | absent
  String _q = '';

  Map<String, dynamic>? _data;
  List<dynamic> _employees = const [];
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  String _fmt(DateTime d) => d.toIso8601String().substring(0, 10);
  String _monthStr(DateTime d) => '${d.year}-${d.month.toString().padLeft(2, '0')}';

  Map<String, String?> _filterArgs() => {
        'month': _mode == 'month' ? _monthStr(_month) : null,
        'dateFrom': _mode == 'range' && _from != null ? _fmt(_from!) : null,
        'dateTo': _mode == 'range' && _to != null ? _fmt(_to!) : null,
      };

  Future<void> _load() async {
    setState(() { _busy = true; _error = null; });
    try {
      final a = _filterArgs();
      final d = await context.read<AuthProvider>().api.pmsAttendanceRecords(
        widget.projectId,
        month: a['month'], dateFrom: a['dateFrom'], dateTo: a['dateTo'],
        employeeId: _employeeId, status: _status, q: _q,
      );
      if (!mounted) return;
      setState(() {
        _data = d;
        if ((d['employees'] as List?)?.isNotEmpty ?? false) _employees = d['employees'] as List;
      });
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _openReport() {
    final a = _filterArgs();
    final path = context.read<AuthProvider>().api.pmsAttendanceReportPath(
      widget.projectId,
      month: a['month'], dateFrom: a['dateFrom'], dateTo: a['dateTo'],
      employeeId: _employeeId, status: _status,
    );
    Navigator.push(context, MaterialPageRoute(
        builder: (_) => PdfReportScreen(path: path, title: tr('تقرير الحضور', 'Attendance report'),
            fileName: 'attendance.pdf')));
  }

  @override
  Widget build(BuildContext context) {
    final d = _data;
    final stats = (d?['stats'] as Map?) ?? const {};
    final summary = (d?['summary'] as List?) ?? const [];
    return Scaffold(
      backgroundColor: Pms.bg,
      appBar: AppBar(
        backgroundColor: Pms.violet, foregroundColor: Colors.white, elevation: 0,
        title: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(tr('الحضور المتقدّم', 'Attendance'), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900)),
          if (widget.projectName.isNotEmpty)
            Text(widget.projectName, style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w500)),
        ]),
        actions: [
          IconButton(onPressed: _openReport, icon: const Icon(Icons.picture_as_pdf_rounded),
              tooltip: tr('تقرير PDF', 'PDF report')),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(padding: const EdgeInsets.fromLTRB(14, 14, 14, 30), children: [
          _filterCard(),
          const SizedBox(height: 14),
          if (_busy && d == null)
            const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator()))
          else if (_error != null)
            Padding(padding: const EdgeInsets.all(20), child: Text('$_error', style: const TextStyle(color: Pms.red)))
          else ...[
            _kpis(stats),
            const SizedBox(height: 8),
            Row(children: [
              Text(tr('كشف العاملين (${summary.length})', 'Workers (${summary.length})'),
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: Pms.ink)),
              const Spacer(),
              if (d?['period'] != null)
                Text('${d!['period']}', style: const TextStyle(fontSize: 11.5, color: Pms.slate)),
            ]),
            const SizedBox(height: 8),
            for (final s in summary) _workerRow(s as Map),
            if (summary.isEmpty) Padding(padding: const EdgeInsets.all(24),
                child: Center(child: Text(tr('لا نتائج للفلاتر المختارة', 'No results'), style: const TextStyle(color: Pms.slate)))),
          ],
        ]),
      ),
      bottomNavigationBar: SafeArea(child: Padding(
        padding: const EdgeInsets.fromLTRB(14, 6, 14, 10),
        child: SizedBox(height: 50, child: FilledButton.icon(
          style: FilledButton.styleFrom(backgroundColor: const Color(0xFF0E3A5F),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
          onPressed: _openReport,
          icon: const Icon(Icons.print_rounded),
          label: Text(tr('تصدير / طباعة تقرير PDF', 'Export / print PDF'),
              style: const TextStyle(fontWeight: FontWeight.w900)),
        )),
      )),
    );
  }

  Widget _filterCard() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFE5E7EB))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        // mode toggle
        Row(children: [
          _modeChip(tr('بالشهر', 'Month'), 'month'),
          const SizedBox(width: 8),
          _modeChip(tr('بمدة', 'Range'), 'range'),
        ]),
        const SizedBox(height: 12),
        if (_mode == 'month')
          InkWell(
            onTap: _pickMonth,
            child: _field(Icons.calendar_month_rounded, tr('الشهر', 'Month'), _monthStr(_month)),
          )
        else
          Row(children: [
            Expanded(child: InkWell(onTap: () => _pickDate(true),
                child: _field(Icons.event_rounded, tr('من', 'From'), _from != null ? _fmt(_from!) : '—'))),
            const SizedBox(width: 8),
            Expanded(child: InkWell(onTap: () => _pickDate(false),
                child: _field(Icons.event_rounded, tr('إلى', 'To'), _to != null ? _fmt(_to!) : '—'))),
          ]),
        const SizedBox(height: 12),
        // status segmented
        Row(children: [
          _statusChip(tr('الكل', 'All'), 'all'),
          const SizedBox(width: 6),
          _statusChip(tr('الحاضرون', 'Present'), 'present'),
          const SizedBox(width: 6),
          _statusChip(tr('الغائبون', 'Absent'), 'absent'),
        ]),
        const SizedBox(height: 12),
        // worker dropdown
        _workerPicker(),
        const SizedBox(height: 12),
        // search
        TextField(
          onChanged: (v) => _q = v,
          onSubmitted: (_) => _load(),
          decoration: InputDecoration(
            hintText: tr('بحث بالاسم أو البادج…', 'Search name or badge…'),
            prefixIcon: const Icon(Icons.search_rounded, size: 19),
            isDense: true, filled: true, fillColor: Pms.bg,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
          ),
        ),
        const SizedBox(height: 12),
        SizedBox(width: double.infinity, height: 46, child: FilledButton.icon(
          style: FilledButton.styleFrom(backgroundColor: Pms.violet,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
          onPressed: _busy ? null : _load,
          icon: const Icon(Icons.filter_alt_rounded),
          label: Text(tr('تطبيق الفلاتر', 'Apply filters'), style: const TextStyle(fontWeight: FontWeight.w900)),
        )),
      ]),
    );
  }

  Widget _field(IconData ic, String label, String val) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
        decoration: BoxDecoration(color: Pms.bg, borderRadius: BorderRadius.circular(12)),
        child: Row(children: [
          Icon(ic, size: 18, color: Pms.slate),
          const SizedBox(width: 8),
          Text(label, style: const TextStyle(fontSize: 12, color: Pms.slate)),
          const Spacer(),
          Text(val, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
        ]),
      );

  Widget _modeChip(String label, String v) {
    final on = _mode == v;
    return Expanded(child: GestureDetector(
      onTap: () => setState(() => _mode = v),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 9),
        alignment: Alignment.center,
        decoration: BoxDecoration(color: on ? Pms.violet : Pms.bg, borderRadius: BorderRadius.circular(10)),
        child: Text(label, style: TextStyle(color: on ? Colors.white : Pms.slate, fontWeight: FontWeight.w800, fontSize: 13)),
      ),
    ));
  }

  Widget _statusChip(String label, String v) {
    final on = _status == v;
    final c = v == 'present' ? Pms.green : v == 'absent' ? Pms.red : Pms.ink;
    return Expanded(child: GestureDetector(
      onTap: () => setState(() => _status = v),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 8),
        alignment: Alignment.center,
        decoration: BoxDecoration(
            color: on ? c.withValues(alpha: 0.12) : Pms.bg,
            borderRadius: BorderRadius.circular(10),
            border: Border.all(color: on ? c : Colors.transparent, width: 1.4)),
        child: Text(label, style: TextStyle(color: on ? c : Pms.slate, fontWeight: FontWeight.w800, fontSize: 12.5)),
      ),
    ));
  }

  Widget _workerPicker() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
      decoration: BoxDecoration(color: Pms.bg, borderRadius: BorderRadius.circular(12)),
      child: Row(children: [
        const Icon(Icons.person_search_rounded, size: 18, color: Pms.slate),
        const SizedBox(width: 8),
        Expanded(child: DropdownButtonHideUnderline(
          child: DropdownButton<int?>(
            isExpanded: true,
            value: _employeeId,
            hint: Text(tr('كل العمال', 'All workers'), style: const TextStyle(fontSize: 13)),
            items: [
              DropdownMenuItem<int?>(value: null, child: Text(tr('كل العمال', 'All workers'))),
              for (final e in _employees)
                DropdownMenuItem<int?>(value: (e as Map)['id'] as int,
                    child: Text('${e['name']}${e['badge'] != null ? ' · ${e['badge']}' : ''}',
                        maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 13))),
            ],
            onChanged: (v) => setState(() => _employeeId = v),
          ),
        )),
      ]),
    );
  }

  Widget _kpis(Map stats) {
    final entries = stats.entries.toList();
    return GridView.count(
      crossAxisCount: 3, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
      mainAxisSpacing: 8, crossAxisSpacing: 8, childAspectRatio: 1.5,
      children: [
        for (final e in entries)
          Container(
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFFE5E7EB))),
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              Text('${e.value}', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 20,
                  color: '${e.key}'.contains('غائب') ? Pms.red : '${e.key}'.contains('حاضر') ? Pms.green : Pms.ink)),
              const SizedBox(height: 2),
              Text('${e.key}', style: const TextStyle(fontSize: 11, color: Pms.slate, fontWeight: FontWeight.w700)),
            ]),
          ),
      ],
    );
  }

  Widget _workerRow(Map s) {
    final present = s['present'] == true;
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(13),
          border: Border.all(color: const Color(0xFFE5E7EB))),
      child: Row(children: [
        CircleAvatar(radius: 22, backgroundColor: Pms.bg,
            backgroundImage: s['image'] != null ? NetworkImage('${s['image']}') : null,
            child: s['image'] == null ? const Icon(Icons.person, color: Pms.slate) : null),
        const SizedBox(width: 11),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${s['name']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5)),
          const SizedBox(height: 2),
          Text('${s['badge'] != null ? '${tr('بادج', 'Badge')}: ${s['badge']}  •  ' : ''}'
              '${tr('أيام', 'Days')}: ${s['days']}  •  ${tr('ساعات', 'Hrs')}: ${s['hours']}',
              style: const TextStyle(fontSize: 11.5, color: Pms.slate, fontWeight: FontWeight.w600)),
        ])),
        Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(
                color: (present ? Pms.green : Pms.red).withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(16)),
            child: Text(present ? tr('حاضر', 'Present') : tr('غائب', 'Absent'),
                style: TextStyle(color: present ? Pms.green : Pms.red, fontWeight: FontWeight.w800, fontSize: 11))),
      ]),
    );
  }

  Future<void> _pickMonth() async {
    final d = await showDatePicker(context: context, initialDate: _month,
        firstDate: DateTime(2020), lastDate: DateTime(2100),
        initialDatePickerMode: DatePickerMode.year);
    if (d != null) setState(() => _month = DateTime(d.year, d.month));
  }

  Future<void> _pickDate(bool from) async {
    final d = await showDatePicker(context: context,
        initialDate: (from ? _from : _to) ?? DateTime.now(),
        firstDate: DateTime(2020), lastDate: DateTime(2100));
    if (d != null) setState(() { if (from) { _from = d; } else { _to = d; } });
  }
}
