import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/theme.dart';
import '../core/widgets.dart';
import 'employee_attendance_screen.dart';

/// "ملفي" — the worker's complete personal file: photo & identity, where they
/// are assigned (project / client / facility / team / supervisor), residency and
/// permit dates, accommodation, and their attendance summary. Document and
/// attendance blocks appear only when enabled in the app settings.
class WorkerFileScreen extends StatefulWidget {
  const WorkerFileScreen({super.key});
  @override
  State<WorkerFileScreen> createState() => _WorkerFileScreenState();
}

const _navy = Color(0xFF0E3A5F);

class _WorkerFileScreenState extends State<WorkerFileScreen> {
  Future<Map<String, dynamic>>? _future;
  String? _token;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final api = context.read<AuthProvider>().api;
    final t = await api.token;
    if (!mounted) return;
    setState(() { _token = t; _future = api.meProfile(); });
  }

  @override
  Widget build(BuildContext context) {
    final p = context.watch<AuthProvider>().profile!;
    final st = ServiceTheme.of(p.role);
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      appBar: AppBar(
        title: Text(tr('ملفي الشخصي', 'My file')),
        backgroundColor: st.accent, foregroundColor: Colors.white,
      ),
      body: RefreshIndicator(
        color: st.accent,
        onRefresh: _load,
        child: FutureBuilder<Map<String, dynamic>>(
          future: _future,
          builder: (_, snap) {
            if (!snap.hasData) return const Center(child: Padding(padding: EdgeInsets.only(top: 100), child: CircularProgressIndicator()));
            final d = snap.data!;
            if (d['has_employee'] == false) {
              return ListView(children: [const SizedBox(height: 140), Center(child: Text(tr('لا يوجد ملف موظف مرتبط', 'No linked employee file'), style: TextStyle(color: Colors.grey.shade500)))]);
            }
            final id = (d['identity'] as Map?) ?? {};
            final asg = d['assignment'] as Map?;
            final doc = d['documents'] as Map?;
            final acc = d['accommodation'] as Map?;
            final att = d['attendance'] as Map?;
            return ListView(padding: EdgeInsets.zero, children: [
              _header(st, id, p),
              _section(Icons.badge_rounded, tr('بيانات الموظف', 'Employee details'), [
                if (id['english_name'] != null) _kv(tr('الاسم بالإنجليزية', 'English name'), '${id['english_name']}'),
                if (id['job'] != null) _kv(tr('المسمى الوظيفي', 'Job title'), '${id['job']}'),
                if (id['department'] != null) _kv(tr('القسم', 'Department'), '${id['department']}'),
                if (id['manager'] != null) _kv(tr('المدير المباشر', 'Manager'), '${id['manager']}'),
                if (id['joining_date'] != null) _kv(tr('تاريخ الالتحاق', 'Joining date'), '${id['joining_date']}'),
                if (id['mobile'] != null) _kv(tr('الجوال', 'Mobile'), '${id['mobile']}'),
                if (id['work_phone'] != null) _kv(tr('هاتف العمل', 'Work phone'), '${id['work_phone']}'),
                if (id['work_email'] != null) _kv(tr('البريد', 'Email'), '${id['work_email']}'),
              ]),
              if (asg != null) _section(Icons.account_tree_rounded, tr('التكليف الحالي', 'Current assignment'), [
                if (asg['project'] != null) _kv(tr('المشروع', 'Project'), '${asg['project']}'),
                if (asg['client'] != null) _kv(tr('العميل', 'Client'), '${asg['client']}'),
                if (asg['facility'] != null) _kv(tr('المرفق', 'Facility'), '${asg['facility']}'),
                if (asg['service'] != null) _kv(tr('الخدمة', 'Service'), '${asg['service']}'),
                if (asg['team'] != null) _kv(tr('الفريق', 'Team'), '${asg['team']}'),
                if (asg['supervisor'] != null) _kv(tr('المشرف', 'Supervisor'), '${asg['supervisor']}'),
              ]),
              if (doc != null && doc.values.any((v) => v != null && v != false))
                _section(Icons.description_rounded, tr('الإقامة والوثائق', 'Residency & documents'), [
                  if (_has(doc['residency_start'])) _kv(tr('بداية الإقامة', 'Residency start'), '${doc['residency_start']}'),
                  if (_has(doc['residency_end'])) _kv(tr('انتهاء الإقامة', 'Residency end'), '${doc['residency_end']}', warn: true),
                  if (_has(doc['permit_start'])) _kv(tr('بداية التصريح', 'Permit start'), '${doc['permit_start']}'),
                  if (_has(doc['permit_end'])) _kv(tr('انتهاء التصريح', 'Permit end'), '${doc['permit_end']}', warn: true),
                  if (_has(doc['passport_no'])) _kv(tr('رقم الجواز', 'Passport no'), '${doc['passport_no']}'),
                  if (_has(doc['civil_code'])) _kv(tr('الرقم المدني', 'Civil ID'), '${doc['civil_code']}'),
                  if (_has(doc['moi_number'])) _kv(tr('رقم الداخلية', 'MOI number'), '${doc['moi_number']}'),
                ]),
              if (acc != null) _section(Icons.hotel_rounded, tr('السكن', 'Accommodation'), [
                if (acc['hostel'] != null) _kv(tr('المبنى', 'Hostel'), '${acc['hostel']}'),
                if (acc['room'] != null) _kv(tr('الغرفة', 'Room'), '${acc['room']}'),
                if (acc['bed'] != null) _kv(tr('السرير', 'Bed'), '${acc['bed']}'),
              ]),
              if (att != null) ...[
                Padding(padding: const EdgeInsets.fromLTRB(14, 16, 14, 6), child: Row(children: [
                  const Icon(Icons.fingerprint_rounded, size: 17, color: _navy), const SizedBox(width: 7),
                  Text(tr('الحضور هذا الشهر', 'Attendance this month'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: _navy)),
                ])),
                Padding(padding: const EdgeInsets.symmetric(horizontal: 12), child: Row(children: [
                  Expanded(child: StatCard(label: tr('أيام', 'Days'), value: _i(att['days']), color: const Color(0xFF7C3AED), icon: Icons.event_available_rounded)),
                  const SizedBox(width: 8),
                  Expanded(child: StatCard(label: tr('ساعات', 'Hours'), value: _i(att['hours']), color: const Color(0xFF0891B2), icon: Icons.schedule_rounded)),
                  const SizedBox(width: 8),
                  Expanded(child: StatCard(label: tr('ورديات', 'Shifts'), value: _i(att['shifts']), color: const Color(0xFF16A34A), icon: Icons.badge_rounded)),
                ])),
                if (p.employeeId != null) Padding(
                  padding: const EdgeInsets.fromLTRB(12, 10, 12, 0),
                  child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(foregroundColor: _navy, side: const BorderSide(color: _navy), minimumSize: const Size.fromHeight(48)),
                    onPressed: () => Navigator.push(context, MaterialPageRoute(
                        builder: (_) => EmployeeAttendanceScreen(employeeId: p.employeeId!, name: p.name))),
                    icon: const Icon(Icons.history_rounded, size: 19),
                    label: Text(tr('عرض السجل الكامل', 'View full record'), style: const TextStyle(fontWeight: FontWeight.w900)),
                  ),
                ),
              ],
              const SizedBox(height: 28),
            ]);
          },
        ),
      ),
    );
  }

  bool _has(dynamic v) => v != null && v != false && '$v'.isNotEmpty;

  Widget _header(ServiceTheme st, Map id, dynamic p) {
    final photo = id['photo'];
    return CustomPaint(
      painter: const BrandPattern(opacity: 0.07),
      child: Container(
        padding: const EdgeInsets.fromLTRB(18, 18, 18, 20),
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: [st.accent, Color.lerp(st.accent, Colors.black, 0.42)!], begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: const BorderRadius.vertical(bottom: Radius.circular(26)),
        ),
        child: Row(children: [
          Container(
            padding: const EdgeInsets.all(3),
            decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: Colors.white.withValues(alpha: 0.4), width: 2)),
            child: CircleAvatar(
              radius: 34, backgroundColor: Colors.white,
              backgroundImage: (photo != null && _token != null)
                  ? NetworkImage('${context.read<AuthProvider>().api.baseUrl}$photo'.replaceFirst('/api/v1/api/v1', '/api/v1'),
                      headers: {'Authorization': 'Bearer $_token'})
                  : null,
              child: photo == null
                  ? Text(p.name.isNotEmpty ? p.name.trim().characters.first : '?',
                      style: TextStyle(color: st.accent, fontSize: 26, fontWeight: FontWeight.w900))
                  : null,
            ),
          ),
          const SizedBox(width: 15),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${id['name'] ?? p.name}', maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
            if (id['job'] != null) ...[
              const SizedBox(height: 4),
              Text('${id['job']}', style: TextStyle(color: Colors.white.withValues(alpha: 0.92), fontSize: 12.5)),
            ],
            if (id['joining_date'] != null) ...[
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(20)),
                child: Text('${tr('منذ', 'since')} ${id['joining_date']}',
                    style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w800)),
              ),
            ],
          ])),
        ]),
      ),
    );
  }

  Widget _section(IconData ic, String title, List<Widget> rows) {
    final shown = rows.whereType<Widget>().toList();
    if (shown.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 16, 12, 0),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Padding(padding: const EdgeInsets.only(bottom: 8, right: 2), child: Row(children: [
          Icon(ic, size: 17, color: _navy), const SizedBox(width: 7),
          Text(title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: _navy)),
        ])),
        Container(
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.grey.shade200)),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
          child: Column(children: shown),
        ),
      ]),
    );
  }

  Widget _kv(String k, String v, {bool warn = false}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 130, child: Text(k, style: TextStyle(color: Colors.grey.shade600, fontSize: 12.5, fontWeight: FontWeight.w700))),
          Expanded(child: Text(v, style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5,
              color: warn ? const Color(0xFFB45309) : _navy))),
        ]),
      );
}

int _i(dynamic v) => v is int ? v : (v is num ? v.round() : int.tryParse('$v') ?? 0);
