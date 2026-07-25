import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/api_client.dart';
import '../core/i18n.dart';

/// موديول التدريب بالكامل: طلبات التدريب (training.application) مع سطورها
/// (الدورات/المواضيع/المراكز/القاعات) والمهام والمراحل — هيدر إحصائيات + فلاتر
/// + بطاقات ملوّنة بالمرحلة + تفاصيل + نموذج إضافة مطابق للباك ايند.
class TrainingScreen extends StatefulWidget {
  const TrainingScreen({super.key});
  @override
  State<TrainingScreen> createState() => _TrainingScreenState();
}

class _TrainingScreenState extends State<TrainingScreen> {
  static const _c = Color(0xFF5B4B8A);       // بنفسجي تدريب احترافي
  static const _bg = Color(0xFFF5F6FA);
  static const _ink = Color(0xFF1F2A37);
  static const _grey = Color(0xFF6B7A8D);

  Map<String, dynamic>? _ov, _opts;
  List _apps = const [];
  bool _loading = true;
  int? _fStage, _fEmp;
  String _q = '';

  ApiClient get _api => context.read<AuthProvider>().api;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final ov = await _api.trainingOverview();
      Map<String, dynamic>? opts;
      try { opts = await _api.trainingOptions(); } catch (_) {}
      if (mounted) setState(() { _ov = ov; _opts = opts; });
      await _loadApps();
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _loadApps() async {
    try {
      final l = await _api.trainingApplications(stage: _fStage, employee: _fEmp, q: _q.isEmpty ? null : _q);
      if (mounted) setState(() => _apps = l);
    } catch (_) {}
  }

  List get _stages => ((_opts?['stages'] as List?) ?? const []).cast();
  List get _employees => ((_opts?['employees'] as List?) ?? const []).cast();

  Color _stageColor(Map a) {
    if (a['is_completed'] == true) return const Color(0xFF16A34A);
    if (a['is_approved'] == true) return const Color(0xFF2563EB);
    return const Color(0xFFF59E0B);
  }

  @override
  Widget build(BuildContext context) {
    final avail = _ov?['available'] != false;
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(backgroundColor: _c, foregroundColor: Colors.white,
          title: Text(tr('التدريب', 'Training')),
          actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))]),
      floatingActionButton: avail ? FloatingActionButton.extended(
        backgroundColor: _c, foregroundColor: Colors.white, onPressed: _createForm,
        icon: const Icon(Icons.add_rounded), label: Text(tr('طلب تدريب', 'New request'), style: const TextStyle(fontWeight: FontWeight.w900))) : null,
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: _c))
          : !avail
              ? Center(child: Text(tr('موديول التدريب غير مثبّت', 'Training module not installed'), style: const TextStyle(color: _grey)))
              : Column(children: [
                  _statsHeader(),
                  _filterBar(),
                  Expanded(child: _apps.isEmpty
                      ? Center(child: Text(tr('لا طلبات تدريب', 'No training requests'), style: const TextStyle(color: _grey)))
                      : RefreshIndicator(onRefresh: _loadApps, color: _c,
                          child: ListView.builder(padding: const EdgeInsets.all(12), itemCount: _apps.length,
                              itemBuilder: (_, i) => _appCard(_apps[i] as Map)))),
                ]),
    );
  }

  Widget _statsHeader() {
    final s = (_ov?['stats'] as Map?) ?? const {};
    final chips = <(String, String, IconData, Color)>[
      (tr('الطلبات', 'Requests'), '${s['applications'] ?? 0}', Icons.school_rounded, _c),
      (tr('قيد التنفيذ', 'In progress'), '${s['in_progress'] ?? 0}', Icons.pending_actions_rounded, const Color(0xFFF59E0B)),
      (tr('معتمَدة', 'Approved'), '${s['approved'] ?? 0}', Icons.verified_rounded, const Color(0xFF2563EB)),
      (tr('مكتملة', 'Completed'), '${s['completed'] ?? 0}', Icons.task_alt_rounded, const Color(0xFF16A34A)),
      (tr('المهام', 'Tasks'), '${s['tasks'] ?? 0}', Icons.checklist_rounded, const Color(0xFF0EA5A4)),
      (tr('المراكز', 'Centers'), '${s['centers'] ?? 0}', Icons.location_city_rounded, const Color(0xFF64748B)),
    ];
    return Container(color: _c, padding: const EdgeInsets.fromLTRB(10, 6, 10, 12),
      child: SizedBox(height: 72, child: ListView.separated(scrollDirection: Axis.horizontal, itemCount: chips.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (_, i) { final c = chips[i]; return Container(width: 104, padding: const EdgeInsets.all(9),
          decoration: BoxDecoration(color: Colors.white.withValues(alpha: .1), borderRadius: BorderRadius.circular(12)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
            Row(children: [Icon(c.$3, color: Colors.white, size: 15), const SizedBox(width: 4),
              Expanded(child: Text(c.$1, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.white70, fontSize: 10.5)))]),
            const SizedBox(height: 4),
            Text(c.$2, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
          ])); })));
  }

  Widget _filterBar() => Container(color: Colors.white, padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
    child: SizedBox(height: 38, child: ListView(scrollDirection: Axis.horizontal, children: [
      SizedBox(width: 160, child: TextField(onChanged: (v) { _q = v; _loadApps(); }, style: const TextStyle(fontSize: 13),
        decoration: InputDecoration(hintText: tr('بحث…', 'Search…'), prefixIcon: const Icon(Icons.search_rounded, size: 18),
          isDense: true, contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8), filled: true, fillColor: const Color(0xFFF1F4F8),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none)))),
      const SizedBox(width: 8),
      _drop<int>(tr('المرحلة', 'Stage'), _fStage, [for (final s in _stages) (s['id'] as int, '${s['name']}')], (v) { setState(() => _fStage = v); _loadApps(); }),
      const SizedBox(width: 8),
      _drop<int>(tr('الموظف', 'Employee'), _fEmp, [for (final e in _employees) (e['id'] as int, '${e['name']}')], (v) { setState(() => _fEmp = v); _loadApps(); }),
    ])));

  Widget _appCard(Map a) {
    final col = _stageColor(a);
    return Container(margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: .04), blurRadius: 8, offset: const Offset(0, 2))]),
      clipBehavior: Clip.antiAlias,
      child: InkWell(onTap: () => _detail(a), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(height: 4, color: col),
        Padding(padding: const EdgeInsets.all(12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('${a['training_name'] ?? a['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w800, color: _ink, fontSize: 15))),
            Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(color: col.withValues(alpha: .14), borderRadius: BorderRadius.circular(20)),
                child: Text('${a['stage'] ?? ''}', style: TextStyle(color: col, fontWeight: FontWeight.w800, fontSize: 11))),
          ]),
          const SizedBox(height: 3),
          Text('${a['name']} · ${a['application_name'] ?? ''}', style: const TextStyle(color: _grey, fontSize: 12)),
          const SizedBox(height: 8),
          Wrap(spacing: 14, runSpacing: 4, children: [
            _meta(Icons.person_rounded, '${a['employee'] ?? '—'}'),
            _meta(Icons.engineering_rounded, '${a['responsible'] ?? '—'}'),
            _meta(Icons.event_rounded, '${a['date_start'] ?? ''} → ${a['date_end'] ?? ''}'),
            _meta(Icons.menu_book_rounded, '${a['lines_count'] ?? 0} ${tr('دورة', 'courses')}'),
            _meta(Icons.checklist_rounded, '${a['task_count'] ?? 0} ${tr('مهمة', 'tasks')}'),
          ]),
        ])),
      ])));
  }

  Widget _meta(IconData i, String t) => Row(mainAxisSize: MainAxisSize.min, children: [
    Icon(i, size: 13, color: _grey), const SizedBox(width: 4), Text(t, style: const TextStyle(color: _grey, fontSize: 11.5))]);

  Future<void> _detail(Map brief) async {
    showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => DraggableScrollableSheet(expand: false, initialChildSize: .75, maxChildSize: .95,
        builder: (_, sc) => FutureBuilder<Map<String, dynamic>>(
          future: _api.trainingApplication(brief['id'] as int),
          builder: (_, snap) {
            if (!snap.hasData) return const Center(child: Padding(padding: EdgeInsets.all(40), child: CircularProgressIndicator(color: _c)));
            final a = snap.data!;
            final lines = (a['lines'] as List?) ?? const [];
            final tasks = (a['tasks'] as List?) ?? const [];
            return ListView(controller: sc, padding: const EdgeInsets.all(16), children: [
              Center(child: Container(width: 40, height: 4, decoration: BoxDecoration(color: const Color(0xFFE0E5EB), borderRadius: BorderRadius.circular(4)))),
              const SizedBox(height: 12),
              Text('${a['training_name']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 20, color: _ink)),
              Text('${a['name']} · ${a['stage'] ?? ''}', style: const TextStyle(color: _grey, fontSize: 13)),
              const SizedBox(height: 12),
              Wrap(spacing: 10, runSpacing: 10, children: [
                for (final e in [
                  (tr('الموظف', 'Employee'), '${a['employee'] ?? '—'}'), (tr('المسؤول', 'Responsible'), '${a['responsible'] ?? '—'}'),
                  (tr('المشروع', 'Project'), '${a['project'] ?? '—'}'), (tr('من', 'From'), '${a['date_start'] ?? '—'}'),
                  (tr('إلى', 'To'), '${a['date_end'] ?? '—'}'), (tr('المهام', 'Tasks'), '${a['task_count'] ?? 0}'),
                ]) _statBox(e.$1, e.$2),
              ]),
              if ((a['description'] ?? '').toString().isNotEmpty) ...[
                const SizedBox(height: 14), Text(tr('الوصف', 'Description'), style: const TextStyle(fontWeight: FontWeight.w800, color: _ink)),
                const SizedBox(height: 4), Text('${a['description']}', style: const TextStyle(color: _grey, fontSize: 13)),
              ],
              const SizedBox(height: 16),
              _section(tr('الدورات', 'Courses'), lines.length),
              for (final l in lines) _lineRow(l as Map),
              const SizedBox(height: 14),
              Row(children: [
                Expanded(child: Text(tr('المهام', 'Tasks'), style: const TextStyle(fontWeight: FontWeight.w800, color: _ink, fontSize: 15))),
                if (tasks.isEmpty && lines.isNotEmpty) FilledButton.icon(
                  style: FilledButton.styleFrom(backgroundColor: _c, visualDensity: VisualDensity.compact),
                  onPressed: () async {
                    final nav = Navigator.of(context); final msg = ScaffoldMessenger.of(context);
                    try { await _api.trainingCreateTasks(a['id'] as int); nav.pop(); _load();
                      msg.showSnackBar(SnackBar(content: Text(tr('أُنشئت المهام', 'Tasks created')), backgroundColor: const Color(0xFF16A34A)));
                    } catch (e) { _err('$e'.replaceFirst('Exception: ', '')); }
                  },
                  icon: const Icon(Icons.playlist_add_rounded, size: 18), label: Text(tr('إنشاء المهام', 'Create tasks'))),
              ]),
              const SizedBox(height: 6),
              if (tasks.isEmpty) Text(tr('لا مهام بعد', 'No tasks yet'), style: const TextStyle(color: _grey, fontSize: 12))
              else for (final t in tasks) _taskRow(t as Map),
            ]);
          })));
  }

  Widget _section(String t, int n) => Padding(padding: const EdgeInsets.only(bottom: 8),
    child: Row(children: [Text(t, style: const TextStyle(fontWeight: FontWeight.w800, color: _ink, fontSize: 15)), const SizedBox(width: 6),
      Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 1), decoration: BoxDecoration(color: _c.withValues(alpha: .12), borderRadius: BorderRadius.circular(20)),
        child: Text('$n', style: const TextStyle(color: _c, fontSize: 12, fontWeight: FontWeight.w800)))]));

  Widget _lineRow(Map l) => Container(margin: const EdgeInsets.only(bottom: 8), padding: const EdgeInsets.all(11),
    decoration: BoxDecoration(color: const Color(0xFFF6F8FB), borderRadius: BorderRadius.circular(12)),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('${l['course'] ?? '—'}', style: const TextStyle(fontWeight: FontWeight.w800, color: _ink, fontSize: 13.5)),
      if (((l['content'] as List?) ?? const []).isNotEmpty)
        Padding(padding: const EdgeInsets.only(top: 3), child: Text('${(l['content'] as List).join('، ')}', style: const TextStyle(color: _grey, fontSize: 12))),
      const SizedBox(height: 5),
      Wrap(spacing: 12, children: [
        if ((l['center'] ?? '').toString().isNotEmpty) _meta(Icons.location_city_rounded, '${l['center']}'),
        if ((l['room'] ?? '').toString().isNotEmpty) _meta(Icons.meeting_room_rounded, '${l['room']}'),
        _meta(Icons.event_rounded, '${l['date_start'] ?? ''} → ${l['date_end'] ?? ''}'),
      ]),
    ]));

  Widget _taskRow(Map t) => Padding(padding: const EdgeInsets.symmetric(vertical: 4),
    child: Row(children: [const Icon(Icons.check_circle_outline_rounded, size: 16, color: _c), const SizedBox(width: 8),
      Expanded(child: Text('${t['name']}', style: const TextStyle(color: _ink, fontSize: 12.5))),
      if ((t['stage'] ?? '').toString().isNotEmpty) Text('${t['stage']}', style: const TextStyle(color: _grey, fontSize: 11))]));

  Widget _statBox(String k, String v) => Container(width: 150, padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(color: const Color(0xFFF6F8FB), borderRadius: BorderRadius.circular(12)),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(k, style: const TextStyle(color: _grey, fontSize: 11.5)), const SizedBox(height: 3),
      Text(v, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _ink, fontWeight: FontWeight.w900, fontSize: 15))]));

  // ---- نموذج إنشاء طلب تدريب (حقول مطابقة) ----
  void _createForm() {
    final appName = TextEditingController(); final trName = TextEditingController(); final desc = TextEditingController();
    int? emp, resp, project, stage; DateTime? start, end;
    final projects = ((_opts?['projects'] as List?) ?? const []).cast();
    showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => StatefulBuilder(builder: (ctx, set) => Padding(
        padding: EdgeInsets.only(left: 16, right: 16, top: 16, bottom: MediaQuery.of(ctx).viewInsets.bottom + 20),
        child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Center(child: Container(width: 40, height: 4, decoration: BoxDecoration(color: const Color(0xFFE0E5EB), borderRadius: BorderRadius.circular(4)))),
          const SizedBox(height: 12),
          Text(tr('طلب تدريب جديد', 'New training request'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 18, color: _ink)),
          const SizedBox(height: 14),
          _tf(appName, tr('اسم الطلب *', 'Application name *')),
          _tf(trName, tr('اسم التدريب *', 'Training name *')),
          _drop2<int>(tr('الموظف *', 'Employee *'), emp, [for (final e in _employees) (e['id'] as int, '${e['name']}')], (v) => set(() => emp = v)),
          _drop2<int>(tr('المسؤول *', 'Responsible *'), resp, [for (final e in _employees) (e['id'] as int, '${e['name']}')], (v) => set(() => resp = v)),
          _drop2<int>(tr('المشروع *', 'Project *'), project, [for (final p in projects) (p['id'] as int, '${p['name']}')], (v) => set(() => project = v)),
          _drop2<int>(tr('المرحلة', 'Stage'), stage, [for (final s in _stages) (s['id'] as int, '${s['name']}')], (v) => set(() => stage = v)),
          _dateField(tr('تاريخ البدء *', 'Start date *'), start, (d) => set(() => start = d)),
          _dateField(tr('تاريخ الانتهاء *', 'End date *'), end, (d) => set(() => end = d)),
          _tf(desc, tr('الوصف', 'Description'), lines: 2),
          const SizedBox(height: 16),
          FilledButton(style: FilledButton.styleFrom(backgroundColor: _c, padding: const EdgeInsets.symmetric(vertical: 14)),
            onPressed: () async {
              if (appName.text.trim().isEmpty || trName.text.trim().isEmpty || emp == null || resp == null || project == null || start == null || end == null) {
                _err(tr('أكمل الحقول المطلوبة (*)', 'Complete required fields (*)')); return;
              }
              final msg = ScaffoldMessenger.of(context);
              try {
                await _api.trainingCreate({
                  'application_name': appName.text.trim(), 'training_name': trName.text.trim(),
                  'employee_id': emp, 'responsible_id': resp, 'project_id': project,
                  if (stage != null) 'stage_id': stage,
                  'date_start': _fmtD(start!), 'date_end': _fmtD(end!),
                  if (desc.text.trim().isNotEmpty) 'description': desc.text.trim(),
                });
                if (ctx.mounted) Navigator.pop(ctx); _load();
                msg.showSnackBar(SnackBar(content: Text(tr('تم إنشاء الطلب', 'Request created')), backgroundColor: const Color(0xFF16A34A)));
              } catch (e) { _err('$e'.replaceFirst('Exception: ', '')); }
            },
            child: Text(tr('حفظ', 'Save'), style: const TextStyle(fontWeight: FontWeight.w900))),
        ])))));
  }

  Widget _tf(TextEditingController c, String hint, {int lines = 1}) => Padding(padding: const EdgeInsets.only(bottom: 10),
    child: TextField(controller: c, maxLines: lines, decoration: InputDecoration(labelText: hint, filled: true, fillColor: const Color(0xFFF6F8FB),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none), contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13))));

  Widget _drop<T>(String hint, T? value, List<(T, String)> items, ValueChanged<T?> onCh) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 12), alignment: Alignment.center,
    decoration: BoxDecoration(color: const Color(0xFFF1F4F8), borderRadius: BorderRadius.circular(10)),
    child: DropdownButton<T>(value: value, isDense: true, underline: const SizedBox(), hint: Text(hint, style: const TextStyle(fontSize: 12.5, color: _grey)),
        style: const TextStyle(fontSize: 12.5, color: _ink),
        items: [DropdownMenuItem<T>(value: null, child: Text(tr('الكل', 'All'), style: const TextStyle(fontSize: 12.5))),
          for (final it in items) DropdownMenuItem<T>(value: it.$1, child: Text(it.$2, style: const TextStyle(fontSize: 12.5)))], onChanged: onCh));

  Widget _drop2<T>(String hint, T? value, List<(T, String)> items, ValueChanged<T?> onCh) => Padding(padding: const EdgeInsets.only(bottom: 10),
    child: Container(padding: const EdgeInsets.symmetric(horizontal: 14), decoration: BoxDecoration(color: const Color(0xFFF6F8FB), borderRadius: BorderRadius.circular(12)),
      child: DropdownButton<T>(value: value, isExpanded: true, underline: const SizedBox(), hint: Text(hint, style: const TextStyle(color: _grey)),
          items: [for (final it in items) DropdownMenuItem<T>(value: it.$1, child: Text(it.$2, overflow: TextOverflow.ellipsis))], onChanged: onCh)));

  Widget _dateField(String label, DateTime? value, ValueChanged<DateTime> onPick) => Padding(padding: const EdgeInsets.only(bottom: 10),
    child: InkWell(borderRadius: BorderRadius.circular(12),
      onTap: () async {
        final now = DateTime.now();
        final d = await showDatePicker(context: context, initialDate: value ?? now, firstDate: DateTime(now.year - 1), lastDate: DateTime(now.year + 3));
        if (d != null) onPick(d);
      },
      child: Container(padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 15), decoration: BoxDecoration(color: const Color(0xFFF6F8FB), borderRadius: BorderRadius.circular(12)),
        child: Row(children: [const Icon(Icons.event_rounded, color: _c, size: 18), const SizedBox(width: 10),
          Text(value == null ? label : _fmtD(value), style: TextStyle(color: value == null ? _grey : _ink, fontWeight: value == null ? FontWeight.normal : FontWeight.w700))]))));

  String _fmtD(DateTime d) { String two(int n) => n.toString().padLeft(2, '0'); return '${d.year}-${two(d.month)}-${two(d.day)}'; }
  void _err(String m) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m), backgroundColor: const Color(0xFFDC2626)));
}
