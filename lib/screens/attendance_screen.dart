import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:geolocator/geolocator.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'pdf_report_screen.dart';
import 'employee_profile_screen.dart';
import 'excel_export.dart';

/// الحضور والانصراف — who is expected on each shift, who actually turned up,
/// who is missing, and every punch behind those numbers. Printable.
class AttendanceScreen extends StatefulWidget {
  const AttendanceScreen({super.key});
  @override
  State<AttendanceScreen> createState() => _AttendanceScreenState();
}

class _AttendanceScreenState extends State<AttendanceScreen> {
  Future<Map<String, dynamic>>? _future;
  int _tab = 0;
  String _period = 'month';
  int? _employeeId;
  int? _facilityId;

  static const _navy = Color(0xFF0E3A5F);
  static const _periods = [
    ('day', 'اليوم', 'Today'), ('week', 'الأسبوع', 'Week'),
    ('month', 'الشهر', 'Month'), ('year', 'السنة', 'Year'), ('all', 'الكل', 'All'),
  ];

  Map<String, dynamic>? _punch;   // {employee, checked_in, since}
  bool _punchBusy = false;

  @override
  void initState() {
    super.initState();
    _load();
    _loadPunch();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientAttendanceData(
      period: _period, employeeId: _employeeId, facilityId: _facilityId);

  Future<void> _loadPunch() async {
    try {
      final s = await context.read<AuthProvider>().api.attendanceStatus();
      if (mounted) setState(() => _punch = s);
    } catch (_) {
      if (mounted) setState(() => _punch = {'_unavailable': true});
    }
  }

  /// Best-effort GPS so the punch carries where it happened — never blocks it.
  Future<(double?, double?)> _whereAmI() async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) return (null, null);
      var p = await Geolocator.checkPermission();
      if (p == LocationPermission.denied) p = await Geolocator.requestPermission();
      if (p == LocationPermission.denied || p == LocationPermission.deniedForever) return (null, null);
      final pos = await Geolocator.getCurrentPosition(
          desiredAccuracy: LocationAccuracy.medium,
          timeLimit: const Duration(seconds: 6));
      return (pos.latitude, pos.longitude);
    } catch (_) {
      return (null, null);
    }
  }

  Future<void> _doPunch() async {
    setState(() => _punchBusy = true);
    try {
      final (lat, lng) = await _whereAmI();
      final r = await context.read<AuthProvider>().api.attendancePunch(lat: lat, lng: lng);
      if (!mounted) return;
      final inNow = r['checked_in'] == true;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(inNow ? tr('تم تسجيل الحضور ✅', 'Checked in ✅')
                             : tr('تم تسجيل الانصراف 👋', 'Checked out 👋')),
        backgroundColor: inNow ? const Color(0xFF16A34A) : const Color(0xFF64748B),
        behavior: SnackBarBehavior.floating,
      ));
      await _loadPunch();
      setState(_load);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('$e'), backgroundColor: const Color(0xFFE11D48),
          behavior: SnackBarBehavior.floating));
    } finally {
      if (mounted) setState(() => _punchBusy = false);
    }
  }

  Widget _punchCard() {
    final p = _punch;
    if (p == null) {
      return const Padding(padding: EdgeInsets.symmetric(vertical: 18),
          child: Center(child: SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2))));
    }
    if (p['_unavailable'] == true) return const SizedBox.shrink();  // no employee file
    final inNow = p['checked_in'] == true;
    final accent = inNow ? const Color(0xFF16A34A) : _navy;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: [accent, accent.withOpacity(0.82)],
            begin: Alignment.topLeft, end: Alignment.bottomRight),
        borderRadius: BorderRadius.circular(18),
        boxShadow: [BoxShadow(color: accent.withOpacity(0.3), blurRadius: 16, offset: const Offset(0, 6))],
      ),
      child: Row(children: [
        Container(width: 46, height: 46, decoration: BoxDecoration(
            color: Colors.white.withOpacity(0.2), shape: BoxShape.circle),
            child: Icon(inNow ? Icons.logout_rounded : Icons.login_rounded, color: Colors.white)),
        const SizedBox(width: 14),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${p['employee'] ?? ''}',
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15)),
          const SizedBox(height: 3),
          Text(inNow
                  ? '${tr('حاضر منذ', 'On since')} ${p['since'] ?? ''}'
                  : tr('لست مسجّلًا حاليًا', 'You are not checked in'),
              style: const TextStyle(color: Colors.white70, fontSize: 12, fontWeight: FontWeight.w600)),
        ])),
        FilledButton(
          onPressed: _punchBusy ? null : _doPunch,
          style: FilledButton.styleFrom(
            backgroundColor: Colors.white, foregroundColor: accent,
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          ),
          child: _punchBusy
              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))
              : Text(inNow ? tr('انصراف', 'Check out') : tr('حضور', 'Check in'),
                  style: const TextStyle(fontWeight: FontWeight.w900)),
        ),
      ]),
    );
  }

  /// Opens the server-rendered PDF — the same _attendance_data this screen
  /// reads — inside the app, where it can be shared or printed.
  void _print({int? employeeId}) {
    final q = StringBuffer('/cafm/attendance/report?period=$_period');
    if (employeeId != null) q.write('&employee_id=$employeeId');
    if (_facilityId != null) q.write('&facility_id=$_facilityId');
    Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
      title: tr('تقرير الحضور والانصراف', 'Attendance report'),
      path: q.toString(),
    )));
  }

  void _exportExcel({int? employeeId}) {
    final q = StringBuffer('/cafm/attendance/export?period=$_period');
    if (employeeId != null) q.write('&employee_id=$employeeId');
    if (_facilityId != null) q.write('&facility_id=$_facilityId');
    exportExcelFile(context,
        path: q.toString(),
        fileName: 'attendance-$_period.xlsx',
        shareText: tr('سجل الحضور والانصراف', 'Attendance records'));
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: Text(tr('الحضور والانصراف', 'Attendance')),
        actions: [
          IconButton(
            icon: const Icon(Icons.grid_on_rounded),
            tooltip: tr('تصدير Excel', 'Export Excel'),
            onPressed: () => _exportExcel(),
          ),
          IconButton(
            icon: const Icon(Icons.print_rounded),
            tooltip: tr('طباعة التقرير', 'Print report'),
            onPressed: () => _print(),
          ),
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
                onSelected: (_) => setState(() { _period = p.$1; _load(); }),
              )),
          ]),
        ),
        Expanded(child: FutureBuilder<Map<String, dynamic>>(
          future: _future,
          builder: (_, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return Center(child: Text('${snap.error}', style: TextStyle(color: cs.outline)));
            }
            final d = snap.data ?? const {};
            final totals = (d['totals'] as Map?) ?? const {};
            final shifts = (d['shifts'] as List?) ?? const [];
            final workers = (d['workers'] as List?) ?? const [];
            final records = (d['records'] as List?) ?? const [];
            return RefreshIndicator(
              onRefresh: () async => setState(_load),
              child: ListView(padding: const EdgeInsets.fromLTRB(12, 4, 12, 24), children: [
                _punchCard(),
                _totals(totals),
                const SizedBox(height: 12),
                _tabs(shifts.length, workers.length, records.length),
                const SizedBox(height: 10),
                if (_tab == 0) ...[
                  if (shifts.isEmpty)
                    _empty(tr('لا ورديات معرّفة لعاملي منشآتك.\nيلزم تسجيل الأعضاء في الفِرَق وتحديد ورديتهم.',
                        'No shifts defined for your sites.\nTeam members need a shift assigned.'), cs)
                  else
                    for (final s in shifts) _shiftBlock(s as Map),
                ] else if (_tab == 1) ...[
                  if (workers.isEmpty) _empty(tr('لا عاملين في هذه الفترة.', 'No workers in this period.'), cs),
                  for (final w in workers) _workerRow(w as Map),
                ] else ...[
                  if (records.isEmpty) _empty(tr('لا سجلات في هذه الفترة.', 'No records in this period.'), cs),
                  for (final r in records) _recordRow(r as Map),
                ],
              ]),
            );
          },
        )),
      ]),
    );
  }

  Widget _empty(String t, ColorScheme cs) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 46),
        child: Center(child: Column(children: [
          Icon(Icons.event_busy_rounded, size: 38, color: cs.outline.withValues(alpha: 0.4)),
          const SizedBox(height: 8),
          Text(t, textAlign: TextAlign.center,
              style: TextStyle(color: cs.outline, fontSize: 12.5, height: 1.5)),
        ])),
      );

  Widget _totals(Map t) {
    final expected = (t['expected'] ?? 0) as int;
    final came = (t['came_today'] ?? 0) as int;
    final rate = expected > 0 ? came * 100.0 / expected : 0.0;
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [Color(0xFF17547F), _navy],
            begin: Alignment.topRight, end: Alignment.bottomLeft),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(children: [
        Row(children: [
          _t('${t['present_now'] ?? 0}', tr('بالموقع الآن', 'On site')),
          _sep(),
          _t('${t['workers'] ?? 0}', tr('عامل', 'Workers')),
          _sep(),
          _t('${t['total_hours'] ?? 0}', tr('ساعة', 'Hours')),
          _sep(),
          _t('${t['days_covered'] ?? 0}', tr('يوم', 'Days')),
        ]),
        if (expected > 0) ...[
          const SizedBox(height: 11),
          Row(children: [
            Expanded(child: ClipRRect(
              borderRadius: BorderRadius.circular(5),
              child: LinearProgressIndicator(
                value: (rate / 100).clamp(0.0, 1.0), minHeight: 7,
                backgroundColor: Colors.white.withValues(alpha: 0.18),
                valueColor: AlwaysStoppedAnimation(
                    rate >= 80 ? const Color(0xFF4ADE80) : const Color(0xFFFBBF24)),
              ),
            )),
            const SizedBox(width: 9),
            Text(tr('حضر $came من $expected', '$came of $expected here'),
                style: const TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.w900)),
          ]),
        ],
        if (((t['incomplete'] ?? 0) as int) > 0) ...[
          const SizedBox(height: 8),
          Row(children: [
            const Icon(Icons.error_outline_rounded, size: 13, color: Color(0xFFFCA5A5)),
            const SizedBox(width: 5),
            Text(tr('${t['incomplete']} وردية بلا انصراف مسجّل', '${t['incomplete']} shifts with no punch-out'),
                style: const TextStyle(color: Color(0xFFFCA5A5), fontSize: 10, fontWeight: FontWeight.w700)),
          ]),
        ],
      ]),
    );
  }

  Widget _t(String v, String l) => Expanded(child: Column(children: [
        Text(v, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
        Text(l, maxLines: 1, overflow: TextOverflow.ellipsis,
            style: TextStyle(color: Colors.white.withValues(alpha: 0.7), fontSize: 9, fontWeight: FontWeight.w700)),
      ]));

  Widget _sep() => Container(width: 1, height: 24, color: Colors.white.withValues(alpha: 0.15));

  Widget _tabs(int shifts, int workers, int records) => Row(children: [
        for (final t in [
          (0, tr('الورديات', 'Shifts'), shifts, Icons.schedule_rounded),
          (1, tr('العاملون', 'Workers'), workers, Icons.people_alt_rounded),
          (2, tr('السجلات', 'Records'), records, Icons.list_alt_rounded),
        ]) ...[
          Expanded(child: InkWell(
            borderRadius: BorderRadius.circular(11),
            onTap: () => setState(() => _tab = t.$1),
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 8),
              decoration: BoxDecoration(
                color: _tab == t.$1 ? _navy : _navy.withValues(alpha: 0.06),
                borderRadius: BorderRadius.circular(11),
              ),
              child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                Icon(t.$4, size: 14, color: _tab == t.$1 ? Colors.white : _navy),
                const SizedBox(width: 5),
                Text('${t.$2} (${t.$3})',
                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800,
                        color: _tab == t.$1 ? Colors.white : _navy)),
              ]),
            ),
          )),
          if (t.$1 != 2) const SizedBox(width: 7),
        ],
      ]);

  /// One shift: its times, who is expected, and — the point — who is missing.
  Widget _shiftBlock(Map s) {
    final rate = (s['present_rate'] ?? 0) is num ? (s['present_rate'] as num).toDouble() : 0.0;
    final c = rate >= 80
        ? const Color(0xFF16A34A)
        : (rate >= 50 ? const Color(0xFFF7A23B) : const Color(0xFFE5484D));
    final members = (s['members'] as List?) ?? const [];
    final absent = members.where((m) => (m as Map)['came_today'] != true).toList();
    return Container(
      margin: const EdgeInsets.only(bottom: 11),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: c.withValues(alpha: 0.25)),
      ),
      clipBehavior: Clip.antiAlias,
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
          childrenPadding: const EdgeInsets.fromLTRB(10, 0, 10, 10),
          leading: Container(
            width: 44, height: 44, alignment: Alignment.center,
            decoration: BoxDecoration(
                gradient: LinearGradient(colors: [c, Color.lerp(c, Colors.black, 0.25)!]),
                borderRadius: BorderRadius.circular(13)),
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              Text('${rate.round()}%',
                  style: const TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w900)),
              Text(tr('حضور', 'Attendance'),
                  style: TextStyle(color: Colors.white70, fontSize: 6.5, fontWeight: FontWeight.w700)),
            ]),
          ),
          title: Row(children: [
            Flexible(child: Text('${s['name']}',
                maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14))),
            if (s['start'] != null) ...[
              const SizedBox(width: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                    color: _navy.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(6)),
                child: Text('${s['start']} – ${s['end'] ?? ''}',
                    style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, color: _navy)),
              ),
            ],
          ]),
          subtitle: Padding(
            padding: const EdgeInsets.only(top: 3),
            child: Row(children: [
              _b('${s['expected']}', tr('متوقَّع', 'expected'), Colors.grey.shade600),
              const SizedBox(width: 6),
              _b('${s['came']}', tr('حضر', 'here'), const Color(0xFF16A34A)),
              const SizedBox(width: 6),
              _b('${s['absent']}', tr('غائب', 'absent'),
                  ((s['absent'] ?? 0) as int) > 0 ? const Color(0xFFE5484D) : Colors.grey),
              if (s['days'] != null) ...[
                const SizedBox(width: 6),
                Flexible(child: Text('${s['days']}',
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 9, color: Colors.grey.shade500, fontWeight: FontWeight.w600))),
              ],
            ]),
          ),
          children: [
            if (absent.isNotEmpty)
              Container(
                width: double.infinity,
                margin: const EdgeInsets.only(bottom: 8),
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
                decoration: BoxDecoration(
                    color: const Color(0xFFE5484D).withValues(alpha: 0.07),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(color: const Color(0xFFE5484D).withValues(alpha: 0.2))),
                child: Row(children: [
                  const Icon(Icons.person_off_rounded, size: 13, color: Color(0xFFE5484D)),
                  const SizedBox(width: 6),
                  Expanded(child: Text(absent.map((m) => (m as Map)['name']).join('، '),
                      style: const TextStyle(
                          fontSize: 10.5, fontWeight: FontWeight.w700, color: Color(0xFFE5484D)))),
                ]),
              ),
            for (final m in members) _memberRow(m as Map),
          ],
        ),
      ),
    );
  }

  Widget _b(String v, String l, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(6)),
        child: Text('$v $l', style: TextStyle(fontSize: 9, fontWeight: FontWeight.w800, color: c)),
      );

  Widget _memberRow(Map m) {
    final here = m['present_now'] == true;
    final came = m['came_today'] == true;
    final c = here ? const Color(0xFF16A34A) : (came ? const Color(0xFF2F6DF6) : const Color(0xFFE5484D));
    return InkWell(
      borderRadius: BorderRadius.circular(10),
      onTap: () => _openWorker(m['id'] as int, '${m['name']}'),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 5, horizontal: 2),
        child: Row(children: [
          Container(width: 7, height: 7, decoration: BoxDecoration(color: c, shape: BoxShape.circle)),
          const SizedBox(width: 8),
          Builder(builder: (_) {
            final img = avatarImage(m['photo'] as String?);
            return CircleAvatar(
              radius: 14,
              backgroundColor: c.withValues(alpha: 0.14),
              backgroundImage: img,
              child: img == null
                  ? Text('${m['name']}'.characters.first,
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: c))
                  : null,
            );
          }),
          const SizedBox(width: 8),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${m['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
            Text([
              if (m['role'] != null) '${m['role']}',
              if (m['team'] != null) '${m['team']}',
              here ? tr('بالموقع الآن', 'on site') : (came ? tr('حضر اليوم', 'came today') : tr('لم يحضر', 'absent')),
            ].join(' · '),
                maxLines: 1, overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 9, color: Colors.grey.shade500, fontWeight: FontWeight.w600)),
          ])),
          if (((m['hours'] ?? 0) as num) > 0)
            Text(tr('${m['hours']} س', '${m['hours']}h'),
                style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w900, color: Color(0xFF0891B2))),
          Icon(Icons.chevron_left_rounded, size: 16, color: Colors.grey.shade400),
        ]),
      ),
    );
  }

  Widget _workerRow(Map w) => Card(
        margin: const EdgeInsets.only(bottom: 7),
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: () => _openWorker(w['id'] as int, '${w['name']}'),
          child: Padding(
            padding: const EdgeInsets.all(10),
            child: Row(children: [
              Builder(builder: (_) {
                final img = avatarImage(w['photo'] as String?);
                return CircleAvatar(
                  radius: 18,
                  backgroundColor: _navy.withValues(alpha: 0.1),
                  backgroundImage: img,
                  child: img == null
                      ? Text('${w['name']}'.characters.first,
                          style: const TextStyle(fontWeight: FontWeight.w900, color: _navy))
                      : null,
                );
              }),
              const SizedBox(width: 10),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Flexible(child: Text('${w['name']}',
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13))),
                  if (w['open'] == true) ...[
                    const SizedBox(width: 5),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                      decoration: BoxDecoration(
                          color: const Color(0xFF16A34A), borderRadius: BorderRadius.circular(5)),
                      child: Text(tr('بالموقع', 'on site'),
                          style: const TextStyle(fontSize: 7.5, fontWeight: FontWeight.w900, color: Colors.white)),
                    ),
                  ],
                ]),
                if (w['job'] != null)
                  Text('${w['job']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 10, color: Colors.grey.shade500)),
                const SizedBox(height: 4),
                Wrap(spacing: 5, runSpacing: 4, children: [
                  _b('${w['days']}', tr('يوم', 'days'), const Color(0xFF6366F1)),
                  _b('${w['shifts']}', tr('وردية', 'shifts'), const Color(0xFF0891B2)),
                  _b('${w['hours']}', tr('ساعة', 'hrs'), const Color(0xFF16A34A)),
                  _b('${w['avg_hours']}', tr('متوسط/يوم', 'avg/day'), Colors.grey.shade600),
                ]),
              ])),
              Column(mainAxisSize: MainAxisSize.min, children: [
                IconButton(
                  padding: EdgeInsets.zero, constraints: const BoxConstraints(),
                  icon: const Icon(Icons.grid_on_outlined, size: 17, color: Color(0xFF16A34A)),
                  tooltip: tr('تصدير Excel لهذا العامل', 'Export this worker'),
                  onPressed: () => _exportExcel(employeeId: w['id'] as int),
                ),
                const SizedBox(height: 8),
                IconButton(
                  padding: EdgeInsets.zero, constraints: const BoxConstraints(),
                  icon: const Icon(Icons.print_outlined, size: 17),
                  tooltip: tr('طباعة سجل هذا العامل', 'Print this worker'),
                  onPressed: () => _print(employeeId: w['id'] as int),
                ),
              ]),
            ]),
          ),
        ),
      );

  Widget _recordRow(Map r) => Card(
        margin: const EdgeInsets.only(bottom: 6),
        child: ListTile(
          dense: true,
          // Two timestamps side by side never said which way the punch went.
          // The icon and its colour answer that before the text is read.
          leading: Builder(builder: (_) {
            final out = r['punch'] == 'out';
            final c = out ? const Color(0xFFE11D48) : const Color(0xFF16A34A);
            return Container(
              width: 30, height: 30,
              decoration: BoxDecoration(
                  color: c.withValues(alpha: 0.12), shape: BoxShape.circle),
              child: Icon(out ? Icons.logout_rounded : Icons.login_rounded,
                  size: 16, color: c),
            );
          }),
          title: Text('${r['employee']}',
              maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5)),
          subtitle: Text(
              '${r['punch_label'] ?? ''} ${r['punch_at'] ?? ''} · '
              '${_hm(r['check_in'])} → ${_hm(r['check_out'])}'
              '${r['facility'] != null ? ' · ${r['facility']}' : ''}',
              maxLines: 1, overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 10.5, color: Colors.grey.shade600)),
          trailing: Text(tr('${r['hours']} س', '${r['hours']}h'),
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12, color: Color(0xFF0891B2))),
          onTap: () => _openWorker(r['employee_id'] as int, '${r['employee']}'),
        ),
      );

  String _hm(dynamic v) {
    final s = '${v ?? ''}';
    // Datetimes arrive as "YYYY-MM-DD HH:MM:SS"; anything shorter has no time.
    if (s.length < 16) return '—';
    return s.substring(11, 16);
  }

  void _openWorker(int id, String name) => Navigator.push(context, MaterialPageRoute(
      builder: (_) => EmployeeProfileScreen(employeeId: id, name: name)));
}
