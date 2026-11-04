// شاشة كشوف الدوام في تطبيق مدير المشروع — تماثل بوابة /my/pm.
// مشاريع → كشوف المشروع → الشبكة اليومية التفاعلية (نقر الخلية يبدّل الحالة).
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';

// ألوان الحالات (نفس مفتاح البوابة)
const Map<String, Color> kStatusColor = {
  'P': Color(0xFF16A34A), 'O': Color(0xFF64748B), 'A': Color(0xFFDC2626),
  'L': Color(0xFF7C3AED), 'H': Color(0xFF0E9488), 'S': Color(0xFFD97706),
  'T': Color(0xFF2563EB), 'E': Color(0xFFB8860B),
};
const _navy = Color(0xFF17315A);
const _violet = Color(0xFF6D33D6);

// ============ شاشة 1: المشاريع ============
class TimesheetScreen extends StatefulWidget {
  const TimesheetScreen({super.key});
  @override
  State<TimesheetScreen> createState() => _TimesheetScreenState();
}

class _TimesheetScreenState extends State<TimesheetScreen> {
  late Future<List<dynamic>> _f;
  @override
  void initState() {
    super.initState();
    _f = context.read<AuthProvider>().api.tsProjects();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('🗓️ ${tr('كشوف الدوام', 'Attendance Sheets')}'), backgroundColor: _violet, foregroundColor: Colors.white),
      body: FutureBuilder<List<dynamic>>(
        future: _f,
        builder: (c, s) {
          if (s.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
          if (s.hasError) return Center(child: Text(tr('تعذّر التحميل', 'Load failed')));
          final projs = s.data ?? [];
          if (projs.isEmpty) return Center(child: Text(tr('لا مشاريع متاحة', 'No projects available')));
          return ListView(padding: const EdgeInsets.all(12), children: [
            for (final p in projs)
              Card(
                child: ListTile(
                  leading: const CircleAvatar(backgroundColor: Color(0xFFEDE9FE), child: Icon(Icons.apartment_rounded, color: _violet)),
                  title: Text(p['name'] ?? '', style: const TextStyle(fontWeight: FontWeight.w800)),
                  subtitle: Text(p['dept'] ?? ''),
                  trailing: const Icon(Icons.chevron_left_rounded),
                  onTap: () => Navigator.push(c, MaterialPageRoute(
                      builder: (_) => SheetsScreen(projectId: p['id'], projectName: p['name'] ?? ''))),
                ),
              ),
          ]);
        },
      ),
    );
  }
}

// ============ شاشة 2: كشوف مشروع ============
class SheetsScreen extends StatefulWidget {
  final int projectId;
  final String projectName;
  const SheetsScreen({super.key, required this.projectId, required this.projectName});
  @override
  State<SheetsScreen> createState() => _SheetsScreenState();
}

class _SheetsScreenState extends State<SheetsScreen> {
  late Future<Map<String, dynamic>> _f;
  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => _f = context.read<AuthProvider>().api.tsSheets(widget.projectId);

  Color _stColor(String s) => s == 'approved' ? const Color(0xFF16A34A) : s == 'submit' ? const Color(0xFFD97706) : const Color(0xFF64748B);
  String _stLabel(String s) => s == 'approved' ? tr('معتمد', 'Approved') : s == 'submit' ? tr('بالانتظار', 'Pending') : tr('مسودة', 'Draft');

  Future<void> _create() async {
    final now = DateTime.now();
    final from = DateTime(now.year, now.month, 1);
    final to = DateTime(now.year, now.month + 1, 0);
    final api = context.read<AuthProvider>().api;
    showDialog(context: context, builder: (c) {
      return AlertDialog(
        title: Text(tr('كشف فترة جديدة', 'New period')),
        content: Text('${tr('سيُنشأ كشف للشهر الحالي ويُعبّأ من البصمة', 'A sheet for the current month will be generated from biometrics')}\n${from.toIso8601String().substring(0, 10)} → ${to.toIso8601String().substring(0, 10)}'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c), child: Text(tr('إلغاء', 'Cancel'))),
          FilledButton(
            onPressed: () async {
              Navigator.pop(c);
              try {
                final data = await api.tsCreate({
                  'project_id': widget.projectId,
                  'date_from': from.toIso8601String().substring(0, 10),
                  'date_to': to.toIso8601String().substring(0, 10),
                  'fill': 'bio',
                });
                if (!mounted) return;
                Navigator.push(context, MaterialPageRoute(builder: (_) => GridScreen(tid: data['id']))).then((_) => setState(_reload));
              } catch (e) {
                if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
              }
            },
            child: Text(tr('توليد', 'Generate')),
          ),
        ],
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.projectName), backgroundColor: _violet, foregroundColor: Colors.white),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _create, backgroundColor: _violet,
        icon: const Icon(Icons.add), label: Text(tr('كشف جديد', 'New'), style: const TextStyle(color: Colors.white)),
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _f,
        builder: (c, s) {
          if (s.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
          if (s.hasError) return Center(child: Text(tr('تعذّر التحميل', 'Load failed')));
          final sheets = (s.data?['sheets'] ?? []) as List;
          if (sheets.isEmpty) return Center(child: Text(tr('لا كشوف بعد', 'No sheets yet')));
          return ListView(padding: const EdgeInsets.all(12), children: [
            for (final sh in sheets)
              Card(
                child: ListTile(
                  title: Text('${sh['name']} · ${sh['period']}', style: const TextStyle(fontWeight: FontWeight.w800)),
                  subtitle: Text('${sh['emp_count']} ${tr('عامل', 'workers')} · ${sh['date_from']} → ${sh['date_to']}'),
                  trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                      decoration: BoxDecoration(color: _stColor(sh['state']).withValues(alpha: 0.15), borderRadius: BorderRadius.circular(20)),
                      child: Text(_stLabel(sh['state']), style: TextStyle(color: _stColor(sh['state']), fontWeight: FontWeight.w800, fontSize: 11)),
                    ),
                    const SizedBox(height: 4),
                    Text('${tr('حضور', 'P')}: ${sh['present']}', style: const TextStyle(fontSize: 11, color: Color(0xFF16A34A), fontWeight: FontWeight.w700)),
                  ]),
                  onTap: () => Navigator.push(c, MaterialPageRoute(builder: (_) => GridScreen(tid: sh['id']))).then((_) => setState(_reload)),
                ),
              ),
          ]);
        },
      ),
    );
  }
}

// ============ شاشة 3: الشبكة اليومية التفاعلية ============
class GridScreen extends StatefulWidget {
  final int tid;
  const GridScreen({super.key, required this.tid});
  @override
  State<GridScreen> createState() => _GridScreenState();
}

class _GridScreenState extends State<GridScreen> {
  Map<String, dynamic>? _data;
  bool _loading = true;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      _data = await context.read<AuthProvider>().api.tsSheet(widget.tid);
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _toggle(int dayId, int li, int di) async {
    if (dayId == 0) return;
    try {
      final r = await context.read<AuthProvider>().api.tsDayToggle(dayId);
      setState(() {
        _data!['lines'][li]['days'][di]['status'] = r['status'];
        _data!['lines'][li]['present'] = r['present'];
        _data!['lines'][li]['absent'] = r['absent'];
        _data!['lines'][li]['salary'] = r['salary'];
      });
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  Future<void> _action(String act) async {
    setState(() => _busy = true);
    try {
      _data = await context.read<AuthProvider>().api.tsAction(widget.tid, act);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    final d = _data;
    return Scaffold(
      appBar: AppBar(
        title: Text(d != null ? '${d['name']} · ${d['period']}' : tr('الكشف', 'Sheet')),
        backgroundColor: _navy, foregroundColor: Colors.white,
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : d == null
              ? Center(child: Text(tr('تعذّر التحميل', 'Load failed')))
              : Column(children: [
                  // بطاقة المجاميع + الأزرار
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.all(12),
                    color: const Color(0xFFF6F8FC),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Wrap(spacing: 14, runSpacing: 6, children: [
                        _kpi(tr('حضور', 'Present'), '${d['total_present']}', const Color(0xFF16A34A)),
                        _kpi(tr('غياب', 'Absent'), '${d['total_absent']}', const Color(0xFFDC2626)),
                        _kpi(tr('أيام الراتب', 'Salary'), '${d['total_salary']}', const Color(0xFFD97706)),
                        _kpi(tr('الحالة', 'State'), d['state'], _navy),
                      ]),
                      const SizedBox(height: 8),
                      if (_busy) const LinearProgressIndicator(),
                      Wrap(spacing: 8, runSpacing: 6, children: [
                        if (d['state'] == 'draft') ...[
                          _btn(tr('الكل حاضر', 'All present'), () => _action('present')),
                          _btn(tr('إجازة أسبوعية', 'Weekly off'), () => _action('weekoff')),
                          _btn('📤 ${tr('تقديم', 'Submit')}', () => _action('submit'), color: _navy),
                        ],
                        if (d['state'] == 'submit' && d['can_approve'] == true)
                          _btn('✅ ${tr('اعتماد', 'Approve')}', () => _action('approve'), color: const Color(0xFF16A34A)),
                      ]),
                    ]),
                  ),
                  // الشبكة
                  Expanded(child: _grid(d)),
                  _legend(),
                ]),
    );
  }

  Widget _kpi(String l, String v, Color c) => Column(mainAxisSize: MainAxisSize.min, children: [
        Text(v, style: TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: c)),
        Text(l, style: const TextStyle(fontSize: 11, color: Color(0xFF5F6B85))),
      ]);

  Widget _btn(String t, VoidCallback onTap, {Color color = _violet}) => ElevatedButton(
        onPressed: _busy ? null : onTap,
        style: ElevatedButton.styleFrom(backgroundColor: color, foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8), textStyle: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
        child: Text(t),
      );

  Widget _grid(Map<String, dynamic> d) {
    final dayNums = (d['day_nums'] ?? []) as List;
    final lines = (d['lines'] ?? []) as List;
    const cell = 30.0;
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: SingleChildScrollView(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          // ترويسة الأيام
          Row(children: [
            _hcell(tr('الاسم', 'Name'), 130, bold: true),
            for (final n in dayNums) SizedBox(width: cell, child: Center(child: Text('$n', style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w700)))),
            _hcell(tr('ح', 'P'), 34, bold: true),
            _hcell(tr('غ', 'A'), 34, bold: true),
          ]),
          // صفوف العمال
          for (int li = 0; li < lines.length; li++)
            Row(children: [
              _hcell(lines[li]['name'] ?? '', 130),
              for (int di = 0; di < (lines[li]['days'] as List).length; di++)
                _dayCell(lines[li]['days'][di], li, di, cell),
              _hcell('${lines[li]['present']}', 34, color: const Color(0xFF16A34A)),
              _hcell('${lines[li]['absent']}', 34, color: const Color(0xFFDC2626)),
            ]),
        ]),
      ),
    );
  }

  Widget _hcell(String t, double w, {bool bold = false, Color? color}) => Container(
        width: w, height: 30, alignment: Alignment.center,
        decoration: BoxDecoration(border: Border.all(color: const Color(0xFFE4E9F2), width: .5)),
        child: Text(t, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 11, fontWeight: bold ? FontWeight.w800 : FontWeight.w600, color: color)),
      );

  Widget _dayCell(Map day, int li, int di, double cell) {
    final st = day['status'] ?? '-';
    final isX = st == 'X' || st == '-';
    final c = kStatusColor[st];
    return GestureDetector(
      onTap: isX ? null : () => _toggle(day['id'], li, di),
      child: Container(
        width: cell, height: 30, alignment: Alignment.center,
        decoration: BoxDecoration(
          color: c ?? const Color(0xFFE2E8F0),
          border: Border.all(color: const Color(0xFFE4E9F2), width: .5),
        ),
        child: Text(isX ? '—' : st, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: c != null ? Colors.white : const Color(0xFF94A3B8))),
      ),
    );
  }

  Widget _legend() {
    const items = {'P': 'حاضر', 'O': 'أسبوعية', 'A': 'غائب', 'L': 'إجازة', 'H': 'عطلة', 'S': 'مرضي'};
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(8),
      color: Colors.white,
      child: Wrap(spacing: 10, runSpacing: 4, children: [
        for (final e in items.entries)
          Row(mainAxisSize: MainAxisSize.min, children: [
            Container(width: 16, height: 16, alignment: Alignment.center, decoration: BoxDecoration(color: kStatusColor[e.key], borderRadius: BorderRadius.circular(4)), child: Text(e.key, style: const TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.w900))),
            const SizedBox(width: 3),
            Text(tr(e.value, e.key), style: const TextStyle(fontSize: 11)),
          ]),
      ]),
    );
  }
}
