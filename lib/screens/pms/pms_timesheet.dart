// Timesheets screen in the project-manager app — mirrors the /my/pm portal.
// Projects → project timesheets → interactive daily grid (clicking a cell toggles the status).
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';

// Status colors (same key as the portal)
const Map<String, Color> kStatusColor = {
  'P': Color(0xFF16A34A), 'O': Color(0xFF64748B), 'A': Color(0xFFDC2626),
  'L': Color(0xFF7C3AED), 'H': Color(0xFF0E9488), 'S': Color(0xFFD97706),
  'T': Color(0xFF2563EB), 'E': Color(0xFFB8860B),
};
const _navy = Color(0xFF17315A);
const _violet = Color(0xFF6D33D6);

// ============ Screen 1: Projects ============
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

// ============ Screen 2: Project timesheets ============
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

// ============ Screen 3: Interactive daily grid ============
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
                  // Totals card + buttons
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
                  // رقائق حالات العمّال (مطابق للبورتال)
                  _workerStatusChips(d),
                  // The grid
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
    final dayDows = (d['day_dows'] ?? []) as List;
    final lines = (d['lines'] ?? []) as List;
    const cell = 26.0;
    const nameW = 172.0;
    final origin = context.read<AuthProvider>().api.origin;
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      child: SingleChildScrollView(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          // رأس الأعمدة: الاسم + (رقم اليوم + يوم الأسبوع) + ح/غ/إ (مطابق للبورتال)
          Row(children: [
            _hdr(tr('العامل', 'Worker'), nameW, align: Alignment.centerRight),
            for (int i = 0; i < dayNums.length; i++)
              SizedBox(
                width: cell,
                child: Container(
                  height: 34,
                  decoration: BoxDecoration(color: const Color(0xFFF6F8FC), border: Border.all(color: const Color(0xFFE4E9F2), width: .5)),
                  child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                    Text('${dayNums[i]}', style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: Color(0xFF5F6B85))),
                    Text(i < dayDows.length ? '${dayDows[i]}' : '', style: const TextStyle(fontSize: 8, color: Color(0xFF9AA4BB), fontWeight: FontWeight.w600)),
                  ]),
                ),
              ),
            _hdr(tr('ح', 'P'), 30), _hdr(tr('غ', 'A'), 30), _hdr(tr('إ', 'E'), 30),
          ]),
          // صفوف العمّال (+ صفوف البدلاء تحت كل عامل غائب)
          for (int li = 0; li < lines.length; li++) ...[
            Row(children: [
              _workerCell(lines[li] as Map, nameW, origin),
              for (int di = 0; di < (lines[li]['days'] as List).length; di++)
                _dayCell(lines[li]['days'][di], li, di, cell),
              _tot('${lines[li]['present']}', const Color(0xFF16A34A)),
              _tot('${lines[li]['absent']}', const Color(0xFFDC2626)),
              _tot('${lines[li]['ot'] ?? 0}', const Color(0xFFB45309), bg: const Color(0xFFFEF9C3)),
            ]),
            for (final sr in ((lines[li]['sub_rows'] ?? []) as List))
              _subRow(sr as Map, lines[li]['days'] as List, nameW, cell),
          ],
        ]),
      ),
    );
  }

  Widget _hdr(String t, double w, {Alignment align = Alignment.center}) => Container(
        width: w, height: 34, alignment: align, padding: const EdgeInsets.symmetric(horizontal: 6),
        decoration: BoxDecoration(color: const Color(0xFFF6F8FC), border: Border.all(color: const Color(0xFFE4E9F2), width: .5)),
        child: Text(t, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: Color(0xFF5F6B85))),
      );

  Widget _tot(String t, Color color, {Color? bg}) => Container(
        width: 30, height: 36, alignment: Alignment.center,
        decoration: BoxDecoration(color: bg, border: Border.all(color: const Color(0xFFE4E9F2), width: .5)),
        child: Text(t, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: color)),
      );

  // عمود العامل: أفاتار + الاسم + باركود + الوظيفة (مطابق للبورتال)
  Widget _workerCell(Map ln, double w, String origin) {
    final name = (ln['name'] ?? '').toString();
    final badge = (ln['badge'] ?? '').toString();
    final job = (ln['job'] ?? '').toString();
    final eid = ln['emp_id'];
    return Container(
      width: w, height: 36, padding: const EdgeInsets.symmetric(horizontal: 8),
      decoration: BoxDecoration(color: Colors.white, border: Border.all(color: const Color(0xFFE4E9F2), width: .5)),
      child: Row(children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(7),
          child: Image.network(
            '$origin/web/image/hr.employee/$eid/image_128',
            width: 28, height: 28, fit: BoxFit.cover,
            errorBuilder: (_, __, ___) => Container(
              width: 28, height: 28, color: const Color(0xFFEEF2FB), alignment: Alignment.center,
              child: Text(name.isNotEmpty ? name.characters.first : '?', style: const TextStyle(fontWeight: FontWeight.w900, color: _navy, fontSize: 12)),
            ),
          ),
        ),
        const SizedBox(width: 7),
        Expanded(
          child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(name, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: Color(0xFF13213A))),
            Row(children: [
              if (badge.isNotEmpty)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 4),
                  decoration: BoxDecoration(color: const Color(0xFFEEF4FF), borderRadius: BorderRadius.circular(4)),
                  child: Text('#$badge', style: const TextStyle(fontSize: 8.5, fontWeight: FontWeight.w800, color: Color(0xFF2563EB))),
                ),
              const SizedBox(width: 4),
              Expanded(child: Text(job, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 9, color: Color(0xFF5F6B85)))),
            ]),
          ]),
        ),
      ]),
    );
  }

  Widget _dayCell(Map day, int li, int di, double cell) {
    final st = (day['status'] ?? '-').toString();
    final isX = st == 'X';
    final isEmpty = st == '-' || st.isEmpty;
    final c = kStatusColor[st];
    if (isX) {
      return GestureDetector(
        onTap: null,
        child: Container(
          width: cell, height: 36,
          decoration: BoxDecoration(border: Border.all(color: const Color(0xFFE4E9F2), width: .5)),
          child: CustomPaint(painter: _HatchPainter(), child: const Center(child: Text('—', style: TextStyle(fontSize: 10, color: Color(0xFF94A3B8), fontWeight: FontWeight.w900)))),
        ),
      );
    }
    // مصدر الخانة: بصمة لِما مصدره البصمة، وأيقونتان (بصمة+قلم) إذا عُدّلت يدويًا
    final bool edited = day['edited'] == true;
    final bool isBio = !isEmpty && ((day['source'] == 'bio') || edited);
    final bool isMan = !isEmpty && edited;
    final bool covSub = day['sub'] == true && !isEmpty; // غطّى اليوم عاملٌ بديل
    return GestureDetector(
      onTap: isEmpty ? null : () => _toggle(day['id'], li, di),
      child: Container(
        width: cell, height: 36, alignment: Alignment.center,
        decoration: BoxDecoration(
          color: c ?? Colors.white,
          border: covSub
              ? Border.all(color: const Color(0xFF6D33D6), width: 1.6)
              : Border.all(color: const Color(0xFFE4E9F2), width: .5),
        ),
        child: Stack(alignment: Alignment.center, clipBehavior: Clip.none, children: [
          Text(isEmpty ? '—' : st, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: c != null ? Colors.white : const Color(0xFFCBD5E1))),
          if (covSub)
            Positioned(top: -1, right: 1, child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 2),
              decoration: BoxDecoration(color: const Color(0xFF6D33D6), borderRadius: BorderRadius.circular(3)),
              child: const Text('بديل', style: TextStyle(fontSize: 6.5, fontWeight: FontWeight.w900, color: Colors.white)),
            )),
          if (isBio || isMan)
            Positioned(bottom: 0, left: 1, child: Row(mainAxisSize: MainAxisSize.min, children: [
              if (isBio) const Icon(Icons.fingerprint, size: 9, color: Color(0xFF0D9488)),
              if (isMan) const Icon(Icons.edit, size: 8, color: Color(0xFFD97706)),
            ])),
        ]),
      ),
    );
  }

  // صفّ البديل تحت العامل الغائب: أيام البدل «B» مظلَّلة بنفسجيًّا، وبقيتها مُعتَّمة
  Widget _subRow(Map sr, List days, double nameW, double cell) {
    final cover = Set<String>.from((sr['cover'] ?? []) as List);
    return Row(children: [
      Container(
        width: nameW, height: 34, padding: const EdgeInsets.symmetric(horizontal: 6),
        alignment: Alignment.centerRight,
        decoration: const BoxDecoration(
          color: Color(0x0F6D33D6),
          border: Border(right: BorderSide(color: Color(0xFF6D33D6), width: 3), bottom: BorderSide(color: Color(0xFFE4E9F2), width: .5)),
        ),
        child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
          Text('🔄 ${sr['name']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, color: Color(0xFF6D33D6))),
          Text('${sr['ref']} · ${sr['state_label']} · ${sr['cost']} د.ك', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 7.5, color: Color(0xFF94A3B8))),
        ]),
      ),
      for (final dd in days)
        Container(
          width: cell, height: 34, alignment: Alignment.center,
          decoration: BoxDecoration(
            color: cover.contains('${dd['date']}') ? const Color(0x336D33D6) : const Color(0x08000000),
            border: Border.all(color: const Color(0xFFE4E9F2), width: .5),
          ),
          child: cover.contains('${dd['date']}')
              ? const Text('B', style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w900, color: Color(0xFF6D33D6)))
              : const SizedBox.shrink(),
        ),
      _tot('${sr['days']}', const Color(0xFF6D33D6)),
      _tot('', const Color(0xFF6D33D6)),
      _tot('', const Color(0xFF6D33D6)),
    ]);
  }

  // رقائق توزيع حالات العمّال أعلى الشبكة (مثل البورتال: On Leave / Active …)
  Widget _workerStatusChips(Map<String, dynamic> d) {
    final lines = (d['lines'] ?? []) as List;
    final counts = <String, int>{};
    int subCount = 0;
    for (final l in lines) {
      final lbl = ((l as Map)['worker_status_label'] ?? '').toString();
      if (lbl.isNotEmpty) counts[lbl] = (counts[lbl] ?? 0) + 1;
      if (((l['sub_rows'] ?? []) as List).isNotEmpty) subCount++;
    }
    if (counts.isEmpty && subCount == 0) return const SizedBox.shrink();
    Color chipColor(String l) {
      if (l.contains('إجاز') || l.toLowerCase().contains('leave')) return const Color(0xFFD97706);
      if (l.contains('وقف') || l.toLowerCase().contains('susp')) return const Color(0xFFDC2626);
      return const Color(0xFF16A34A);
    }
    return Container(
      width: double.infinity,
      color: Colors.white,
      padding: const EdgeInsets.fromLTRB(8, 8, 8, 4),
      child: Wrap(spacing: 7, runSpacing: 5, children: [
        for (final e in counts.entries)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 4),
            decoration: BoxDecoration(
              color: chipColor(e.key).withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: chipColor(e.key).withValues(alpha: 0.35)),
            ),
            child: Text('${e.key} · ${e.value}',
                style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: chipColor(e.key))),
          ),
        if (subCount > 0)
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xFF6D33D6).withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: const Color(0xFF6D33D6).withValues(alpha: 0.4)),
            ),
            child: Text('🔄 لديهم بديل · $subCount',
                style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: Color(0xFF6D33D6))),
          ),
      ]),
    );
  }

  Widget _legend() {
    // المفتاح الكامل — مطابق للبورتال (9 رموز)
    const items = {
      'P': 'حاضر', 'O': 'إجازة أسبوعية', 'A': 'غائب', 'L': 'إجازة سنوية',
      'H': 'عطلة رسمية', 'S': 'مرضي', 'T': 'تأخير', 'E': 'إضافي', 'X': 'خارج المشروع',
    };
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(8),
      color: Colors.white,
      child: Wrap(spacing: 10, runSpacing: 4, children: [
        const Text('المفتاح:', style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: Color(0xFF5F6B85))),
        for (final e in items.entries)
          Row(mainAxisSize: MainAxisSize.min, children: [
            Container(
              width: 16, height: 16, alignment: Alignment.center,
              decoration: BoxDecoration(color: kStatusColor[e.key] ?? const Color(0xFFCBD5E1), borderRadius: BorderRadius.circular(4)),
              child: Text(e.key, style: const TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.w900)),
            ),
            const SizedBox(width: 3),
            Text(e.value, style: const TextStyle(fontSize: 11)),
          ]),
      ]),
    );
  }
}

// نمط التظليل المائل لخلايا «خارج المشروع» (X) — مطابق للبورتال
class _HatchPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final bg = Paint()..color = const Color(0xFFE2E8F0);
    canvas.drawRect(Offset.zero & size, bg);
    final p = Paint()
      ..color = const Color(0xFFCBD5E1)
      ..strokeWidth = 2;
    for (double x = -size.height; x < size.width; x += 6) {
      canvas.drawLine(Offset(x, 0), Offset(x + size.height, size.height), p);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
