import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// أدوات مشرف الأمن: لوحة حالة الفريق لحظياً (نشط/سكون/نائم) + إنشاء وإسناد
/// المهام والدوريات والتصاريح وسجلات التفتيش + إشعار الفريق. بثيم الأمن الداكن.
class SecuritySupervisorScreen extends StatefulWidget {
  const SecuritySupervisorScreen({super.key});
  @override
  State<SecuritySupervisorScreen> createState() => _SecuritySupervisorScreenState();
}

class _SecuritySupervisorScreenState extends State<SecuritySupervisorScreen> {
  static const _bg = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _red = Color(0xFFE5484D);
  static const _blue = Color(0xFF4AA8FF);
  static const _green = Color(0xFF37C98A);
  static const _amber = Color(0xFFF7A23B);
  static const _grey = Color(0xFF9CB2CD);

  Map<String, dynamic>? _opts;
  Map<String, dynamic>? _presence;
  bool _loading = true;

  static const _stateColor = {
    'active': _green, 'idle': _amber, 'sleep': _blue, 'offline': _grey,
  };
  static const _stateIcon = {
    'active': Icons.directions_run_rounded, 'idle': Icons.pause_circle_rounded,
    'sleep': Icons.bedtime_rounded, 'offline': Icons.cloud_off_rounded,
  };

  String _stLabel(String s) => {
    'active': tr('نشط', 'Active'), 'idle': tr('سكون', 'Idle'),
    'sleep': tr('نائم', 'Asleep'), 'offline': tr('غير متصل', 'Offline'),
  }[s] ?? s;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final api = context.read<AuthProvider>().api;
      final o = await api.securitySupOptions();
      Map<String, dynamic>? p;
      try { p = await api.securitySupPresence(); } catch (_) {}
      if (mounted) setState(() { _opts = o; _presence = p; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _loading = false; });
    }
  }

  /// فتح بروفايل الحارس عند الضغط عليه في بلوك حالة الفريق.
  void _openGuard(int? gid, String name) {
    if (gid == null) return;
    showModalBottomSheet(
      context: context, backgroundColor: const Color(0xFF15213B), isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => FutureBuilder<Map<String, dynamic>>(
        future: context.read<AuthProvider>().api.securitySupGuard(gid),
        builder: (ctx, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const SizedBox(height: 220, child: Center(child: CircularProgressIndicator(color: _green)));
          }
          final g = snap.data ?? {};
          Widget kv(IconData i, String k, String? v) => (v == null || v.isEmpty)
              ? const SizedBox.shrink()
              : Padding(padding: const EdgeInsets.symmetric(vertical: 5), child: Row(children: [
                  Icon(i, color: _grey, size: 16), const SizedBox(width: 10),
                  Text('$k: ', style: const TextStyle(color: _grey, fontSize: 12.5)),
                  Expanded(child: Text(v, style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600))),
                ]));
          final st = '${g['state'] ?? 'offline'}';
          return Padding(
            padding: EdgeInsets.fromLTRB(20, 16, 20, 20 + MediaQuery.of(ctx).viewInsets.bottom),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              Container(width: 44, height: 4, margin: const EdgeInsets.only(bottom: 14),
                  decoration: BoxDecoration(color: const Color(0xFF33465F), borderRadius: BorderRadius.circular(4))),
              Row(children: [
                CircleAvatar(radius: 26, backgroundColor: const Color(0xFF1F3050),
                    backgroundImage: (g['photo'] != null && '${g['photo']}'.isNotEmpty) ? NetworkImage('${g['photo']}') : null,
                    child: (g['photo'] == null || '${g['photo']}'.isEmpty)
                        ? Text(name.isNotEmpty ? name.characters.first : '؟', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 20)) : null),
                const SizedBox(width: 12),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${g['name'] ?? name}', style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
                  const SizedBox(height: 3),
                  Row(children: [
                    Container(width: 8, height: 8, decoration: BoxDecoration(color: _stateColor[st] ?? _grey, shape: BoxShape.circle)),
                    const SizedBox(width: 6),
                    Text(_stLabel(st), style: TextStyle(color: _stateColor[st] ?? _grey, fontSize: 12, fontWeight: FontWeight.w800)),
                    if (g['on_shift'] == true) ...[const SizedBox(width: 8),
                      Container(padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                          decoration: BoxDecoration(color: const Color(0xFF16A34A).withValues(alpha: .2), borderRadius: BorderRadius.circular(20)),
                          child: Text(tr('على الشيفت', 'On shift'), style: const TextStyle(color: Color(0xFF34D399), fontSize: 10, fontWeight: FontWeight.w800)))],
                  ]),
                ])),
              ]),
              const SizedBox(height: 14),
              Row(children: [
                Expanded(child: _miniStat(tr('مهام مفتوحة', 'Open tasks'), '${g['tasks_open'] ?? 0}', const Color(0xFFF59E0B))),
                const SizedBox(width: 10),
                Expanded(child: _miniStat(tr('مهام منجزة', 'Done'), '${g['tasks_done'] ?? 0}', _green)),
              ]),
              const SizedBox(height: 12),
              kv(Icons.groups_rounded, tr('الفريق', 'Team'), g['team'] as String?),
              kv(Icons.location_on_rounded, tr('الموقع', 'Premise'), g['premise'] as String?),
              kv(Icons.badge_rounded, tr('البادج', 'Badge'), g['badge'] as String?),
              kv(Icons.phone_rounded, tr('الهاتف', 'Phone'), g['phone'] as String?),
              kv(Icons.login_rounded, tr('بداية الشيفت', 'Shift since'), g['shift_since'] as String?),
              kv(Icons.access_time_rounded, tr('آخر ظهور', 'Last seen'), g['last_seen'] as String?),
              if (g['heart_rate'] != null) kv(Icons.favorite_rounded, tr('نبض القلب', 'Heart rate'), '${g['heart_rate']}'),
              if (g['battery'] != null) kv(Icons.battery_full_rounded, tr('البطارية', 'Battery'), '${g['battery']}%'),
            ]),
          );
        },
      ),
    );
  }

  Widget _miniStat(String label, String value, Color c) => Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(color: const Color(0xFF1B2A44), borderRadius: BorderRadius.circular(12)),
        child: Column(children: [
          Text(value, style: TextStyle(color: c, fontSize: 20, fontWeight: FontWeight.w900)),
          Text(label, style: const TextStyle(color: _grey, fontSize: 11)),
        ]),
      );

  List<Map> get _guards => ((_opts?['guards'] as List?) ?? const []).cast<Map>();
  List<Map> get _routes => ((_opts?['routes'] as List?) ?? const []).cast<Map>();
  List<Map> get _teams => ((_opts?['teams'] as List?) ?? const []).cast<Map>();
  List<Map> get _premises => ((_opts?['premises'] as List?) ?? const []).cast<Map>();
  List<Map> get _categories => ((_opts?['task_categories'] as List?) ?? const []).cast<Map>();
  // القوائم [value,label] من الخادم
  List<List> get _inspTypes => ((_opts?['inspection_types'] as List?) ?? const []).map((e) => (e as List)).toList();
  List<List> get _severities => ((_opts?['severities'] as List?) ?? const []).map((e) => (e as List)).toList();
  List<List> get _passTypes => ((_opts?['pass_types'] as List?) ?? const []).map((e) => (e as List)).toList();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(backgroundColor: const Color(0xFF1E3A5F), foregroundColor: Colors.white,
          title: Text(tr('أدوات المشرف', 'Supervisor tools')),
          actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))]),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: _blue))
          : ListView(padding: const EdgeInsets.all(14), children: [
              _presenceCard(),
              const SizedBox(height: 16),
              Text(tr('إجراءات', 'Actions'), style: const TextStyle(color: _grey, fontWeight: FontWeight.w800, fontSize: 13)),
              const SizedBox(height: 10),
              GridView.count(crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
                mainAxisSpacing: 12, crossAxisSpacing: 12, childAspectRatio: 1.35, children: [
                  _action('📋', tr('مهمة جديدة', 'New task'), _blue, _taskForm),
                  _action('🚨', tr('دورية جديدة', 'New patrol'), _red, _patrolForm),
                  _action('🎫', tr('تصريح دخول', 'Gate pass'), _amber, _gatepassForm),
                  _action('🔍', tr('سجل تفتيش', 'Inspection'), _green, _inspectionForm),
                  _action('📢', tr('إشعار الفريق', 'Notify team'), const Color(0xFF8B5CF6), _notifyForm),
                ]),
            ]),
    );
  }

  // ---- لوحة حالة الفريق ----
  Widget _presenceCard() {
    final members = ((_presence?['members'] as List?) ?? const []).cast<Map>();
    final counts = (_presence?['counts'] as Map?) ?? const {};
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withValues(alpha: .06))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.monitor_heart_rounded, color: _green, size: 18), const SizedBox(width: 8),
          Text(tr('حالة الفريق', 'Team status'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15)),
          const Spacer(),
          Text('${_presence?['total'] ?? 0} ${tr('عضو', 'members')}', style: const TextStyle(color: _grey, fontSize: 12)),
        ]),
        const SizedBox(height: 10),
        Row(children: [
          for (final s in const ['active', 'idle', 'sleep', 'offline'])
            Expanded(child: Column(children: [
              Icon(_stateIcon[s], color: _stateColor[s], size: 18),
              const SizedBox(height: 3),
              Text('${counts[s] ?? 0}', style: TextStyle(color: _stateColor[s], fontWeight: FontWeight.w900, fontSize: 16)),
              Text(_stLabel(s), style: const TextStyle(color: _grey, fontSize: 10)),
            ])),
        ]),
        if (members.isNotEmpty) ...[
          const Divider(color: Color(0xFF24344C), height: 20),
          for (final m in members) InkWell(
            onTap: () => _openGuard(m['guard_id'] as int?, '${m['name']}'),
            borderRadius: BorderRadius.circular(8),
            child: Padding(padding: const EdgeInsets.symmetric(vertical: 6), child: Row(children: [
              Container(width: 9, height: 9, decoration: BoxDecoration(color: _stateColor[m['state']] ?? _grey, shape: BoxShape.circle)),
              const SizedBox(width: 9),
              Expanded(child: Text('${m['name']}', style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600))),
              if (m['on_shift'] == true) ...[
                Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                    decoration: BoxDecoration(color: const Color(0xFF16A34A).withValues(alpha: .18), borderRadius: BorderRadius.circular(20)),
                    child: Text(tr('على الشيفت', 'On shift'), style: const TextStyle(color: Color(0xFF34D399), fontSize: 9.5, fontWeight: FontWeight.w800))),
                const SizedBox(width: 6)],
              if (m['heart_rate'] != null) ...[const Icon(Icons.favorite_rounded, color: _red, size: 12), const SizedBox(width: 3),
                Text('${m['heart_rate']}', style: const TextStyle(color: _grey, fontSize: 11))],
              const SizedBox(width: 8),
              Text(_stLabel('${m['state']}'), style: TextStyle(color: _stateColor[m['state']] ?? _grey, fontSize: 11, fontWeight: FontWeight.w800)),
              const Icon(Icons.chevron_left_rounded, color: _grey, size: 18),
            ])),
          ),
        ] else Padding(padding: const EdgeInsets.only(top: 10), child: Text(tr('لا بيانات حالة بعد — تُحدَّث عند نشاط أجهزة الفريق', 'No status yet — updates as team devices report'), style: const TextStyle(color: _grey, fontSize: 11.5))),
      ]),
    );
  }

  Widget _action(String emoji, String label, Color c, VoidCallback onTap) => Material(
        color: _card, borderRadius: BorderRadius.circular(16),
        child: InkWell(borderRadius: BorderRadius.circular(16), onTap: onTap, child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: c.withValues(alpha: .3))),
          child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(emoji, style: const TextStyle(fontSize: 26)),
            const Spacer(),
            Text(label, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14)),
            const SizedBox(height: 2),
            Row(children: [Text(tr('إنشاء', 'Create'), style: TextStyle(color: c, fontSize: 11, fontWeight: FontWeight.w700)),
              Icon(Icons.chevron_left_rounded, color: c, size: 16)]),
          ]),
        )),
      );

  // ---- نماذج الإنشاء ----
  void _sheet(String title, List<Widget> Function(StateSetter set) fields, Future<void> Function() onSubmit) {
    showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: _bg,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => StatefulBuilder(builder: (ctx, setSheet) => Padding(
        padding: EdgeInsets.only(left: 16, right: 16, top: 16, bottom: MediaQuery.of(ctx).viewInsets.bottom + 20),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 17)),
          const SizedBox(height: 14),
          ...fields(setSheet),
          const SizedBox(height: 16),
          FilledButton(style: FilledButton.styleFrom(backgroundColor: _blue, padding: const EdgeInsets.symmetric(vertical: 14)),
            onPressed: () async {
              try { await onSubmit(); if (ctx.mounted) Navigator.pop(ctx); _ok(title); _load(); }
              catch (e) { _err('$e'.replaceFirst('Exception: ', '')); }
            },
            child: Text(tr('حفظ وإسناد', 'Save & assign'), style: const TextStyle(fontWeight: FontWeight.w900))),
        ]),
      )));
  }

  Widget _tf(TextEditingController c, String hint, {int lines = 1, TextInputType? kb}) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: TextField(controller: c, maxLines: lines, keyboardType: kb, style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(hintText: hint, hintStyle: const TextStyle(color: _grey),
            filled: true, fillColor: _card, border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12))),
      );

  Widget _dropdown<T>(String hint, T? value, List<DropdownMenuItem<T>> items, ValueChanged<T?> onCh) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: Container(padding: const EdgeInsets.symmetric(horizontal: 14), decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(12)),
          child: DropdownButton<T>(value: value, isExpanded: true, underline: const SizedBox(), dropdownColor: _card,
            hint: Text(hint, style: const TextStyle(color: _grey)), style: const TextStyle(color: Colors.white),
            items: items, onChanged: onCh)),
      );

  // منتقي تاريخ (اختياري وقت) — يعرض القيمة المختارة ويستدعي onPick بنص ISO
  Widget _dateTf(String label, DateTime? value, bool withTime, ValueChanged<DateTime> onPick) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: InkWell(
          borderRadius: BorderRadius.circular(12),
          onTap: () async {
            final now = DateTime.now();
            final d = await showDatePicker(context: context, initialDate: value ?? now,
                firstDate: DateTime(now.year - 1), lastDate: DateTime(now.year + 3),
                builder: (c, w) => Theme(data: ThemeData.dark().copyWith(colorScheme: const ColorScheme.dark(primary: _blue, surface: _card)), child: w!));
            if (d == null || !mounted) return;
            TimeOfDay? t;
            if (withTime) {
              t = await showTimePicker(context: context, initialTime: TimeOfDay.fromDateTime(value ?? now),
                  builder: (c, w) => Theme(data: ThemeData.dark().copyWith(colorScheme: const ColorScheme.dark(primary: _blue, surface: _card)), child: w!));
            }
            onPick(DateTime(d.year, d.month, d.day, t?.hour ?? 0, t?.minute ?? 0));
          },
          child: Container(padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
            decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(12)),
            child: Row(children: [
              Icon(withTime ? Icons.event_note_rounded : Icons.event_rounded, color: _blue, size: 18),
              const SizedBox(width: 10),
              Expanded(child: Text(value == null ? label : _fmt(value, withTime),
                  style: TextStyle(color: value == null ? _grey : Colors.white, fontWeight: value == null ? FontWeight.normal : FontWeight.w700))),
              if (value != null) const Icon(Icons.check_circle_rounded, color: _green, size: 16),
            ])),
        ),
      );

  String _fmt(DateTime d, bool t) {
    String two(int n) => n.toString().padLeft(2, '0');
    final date = '${d.year}-${two(d.month)}-${two(d.day)}';
    return t ? '$date ${two(d.hour)}:${two(d.minute)}' : date;
  }

  String _iso(DateTime d, bool t) => t ? '${_fmt(d, false)} ${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}:00' : _fmt(d, false);

  Widget _label(String t) => Padding(padding: const EdgeInsets.only(bottom: 6, top: 4),
      child: Text(t, style: const TextStyle(color: _grey, fontSize: 12, fontWeight: FontWeight.w800)));

  void _taskForm() {
    final name = TextEditingController(); final desc = TextEditingController(); final dur = TextEditingController();
    int? guard; int? team; int? cat; String prio = '1';
    DateTime? startD; DateTime? deadline;
    _sheet(tr('مهمة جديدة', 'New task'), (set) => [
      _label(tr('بيانات المهمة', 'Task details')),
      _tf(name, tr('عنوان المهمة *', 'Task title *')),
      _tf(desc, tr('الوصف والتعليمات', 'Description & instructions'), lines: 3),
      _dropdown<int>(tr('التصنيف', 'Category'), cat, [for (final c in _categories) DropdownMenuItem(value: c['id'] as int, child: Text('${c['name']}'))], (v) => set(() => cat = v)),
      _label(tr('الإسناد', 'Assignment')),
      _dropdown<int>(tr('الفريق', 'Team'), team, [for (final t in _teams) DropdownMenuItem(value: t['id'] as int, child: Text('${t['name']}${t['shift'] != null ? ' · ${t['shift']}' : ''}'))], (v) => set(() => team = v)),
      _dropdown<int>(tr('إسناد لحارس', 'Assign to guard'), guard, [for (final g in _guards) DropdownMenuItem(value: g['id'] as int, child: Text('${g['name']}'))], (v) => set(() => guard = v)),
      _dropdown<String>(tr('الأولوية', 'Priority'), prio, [
        DropdownMenuItem(value: '0', child: Text(tr('منخفض', 'Low'))), DropdownMenuItem(value: '1', child: Text(tr('عادي', 'Normal'))),
        DropdownMenuItem(value: '2', child: Text(tr('مرتفع', 'High'))), DropdownMenuItem(value: '3', child: Text(tr('عاجل', 'Urgent')))], (v) => set(() => prio = v ?? '1')),
      _label(tr('التوقيت', 'Scheduling')),
      _dateTf(tr('تاريخ البدء', 'Start date'), startD, true, (d) => set(() => startD = d)),
      _dateTf(tr('الموعد النهائي', 'Deadline'), deadline, true, (d) => set(() => deadline = d)),
      _tf(dur, tr('المدة المقدّرة (ساعات)', 'Estimated duration (hours)'), kb: const TextInputType.numberWithOptions(decimal: true)),
    ], () async {
      if (name.text.trim().isEmpty) throw Exception(tr('العنوان مطلوب', 'Title required'));
      await context.read<AuthProvider>().api.securitySupTaskCreate({
        'name': name.text.trim(), if (desc.text.trim().isNotEmpty) 'description': desc.text.trim(),
        if (cat != null) 'category_id': cat, if (team != null) 'team_id': team,
        if (guard != null) 'assigned_guard_id': guard, 'priority': prio,
        if (startD != null) 'start_date': _iso(startD!, true),
        if (deadline != null) 'deadline': _iso(deadline!, true),
        if (dur.text.trim().isNotEmpty) 'duration': dur.text.trim()});
    });
  }

  void _patrolForm() {
    int? route; int? guard; int? team; String ptype = 'routine';
    DateTime? sched;
    _sheet(tr('دورية جديدة', 'New patrol'), (set) => [
      _label(tr('المسار والنوع', 'Route & type')),
      _dropdown<int>(tr('المسار *', 'Route *'), route, [for (final r in _routes) DropdownMenuItem(value: r['id'] as int, child: Text('${r['name']}${r['premise'] != null ? ' · ${r['premise']}' : ''}'))], (v) => set(() => route = v)),
      _dropdown<String>(tr('نوع الدورية', 'Patrol type'), ptype, [
        DropdownMenuItem(value: 'routine', child: Text(tr('روتينية', 'Routine'))), DropdownMenuItem(value: 'special', child: Text(tr('خاصة', 'Special'))),
        DropdownMenuItem(value: 'emergency', child: Text(tr('طارئة', 'Emergency')))], (v) => set(() => ptype = v ?? 'routine')),
      _label(tr('الإسناد والتوقيت', 'Assignment & timing')),
      _dropdown<int>(tr('الفريق', 'Team'), team, [for (final t in _teams) DropdownMenuItem(value: t['id'] as int, child: Text('${t['name']}'))], (v) => set(() => team = v)),
      _dropdown<int>(tr('الحارس', 'Guard'), guard, [for (final g in _guards) DropdownMenuItem(value: g['id'] as int, child: Text('${g['name']}'))], (v) => set(() => guard = v)),
      _dateTf(tr('موعد بدء الدورية', 'Scheduled start'), sched, true, (d) => set(() => sched = d)),
    ], () async {
      if (route == null) throw Exception(tr('اختر المسار', 'Select route'));
      await context.read<AuthProvider>().api.securitySupPatrolCreate({
        'route_id': route, 'patrol_type': ptype,
        if (team != null) 'team_id': team, if (guard != null) 'guard_id': guard,
        if (sched != null) 'scheduled_start': _iso(sched!, true)});
    });
  }

  void _gatepassForm() {
    final person = TextEditingController(); final phone = TextEditingController();
    final idnum = TextEditingController(); final purpose = TextEditingController();
    String ptype = 'personal'; int? prem;
    DateTime? startD; DateTime? endD;
    _sheet(tr('تصريح دخول', 'Gate pass'), (set) => [
      _label(tr('نوع التصريح والموقع', 'Type & premise')),
      _dropdown<String>(tr('نوع التصريح', 'Pass type'), ptype,
          _passTypes.isNotEmpty
              ? [for (final p in _passTypes) DropdownMenuItem(value: '${p[0]}', child: Text('${p[1]}'))]
              : [DropdownMenuItem(value: 'personal', child: Text(tr('شخص', 'Personal'))), DropdownMenuItem(value: 'vehicle', child: Text(tr('مركبة', 'Vehicle')))],
          (v) => set(() => ptype = v ?? 'personal')),
      _dropdown<int>(tr('الموقع', 'Premise'), prem, [for (final p in _premises) DropdownMenuItem(value: p['id'] as int, child: Text('${p['name']}'))], (v) => set(() => prem = v)),
      _label(tr('بيانات الزائر', 'Visitor details')),
      _tf(person, tr('اسم الشخص *', 'Person name *')),
      _tf(phone, tr('رقم الهاتف', 'Phone'), kb: TextInputType.phone),
      _tf(idnum, tr('رقم الهوية', 'ID number')),
      _tf(purpose, tr('الغرض من الزيارة', 'Purpose of visit'), lines: 2),
      _label(tr('فترة الصلاحية', 'Validity period')),
      _dateTf(tr('من تاريخ', 'Valid from'), startD, false, (d) => set(() => startD = d)),
      _dateTf(tr('إلى تاريخ', 'Valid until'), endD, false, (d) => set(() => endD = d)),
    ], () async {
      if (person.text.trim().isEmpty) throw Exception(tr('الاسم مطلوب', 'Name required'));
      await context.read<AuthProvider>().api.securitySupGatepassCreate({
        'person_name': person.text.trim(), 'pass_type': ptype,
        if (phone.text.trim().isNotEmpty) 'phone': phone.text.trim(),
        if (idnum.text.trim().isNotEmpty) 'id_number': idnum.text.trim(),
        if (purpose.text.trim().isNotEmpty) 'purpose': purpose.text.trim(),
        if (prem != null) 'premise_id': prem,
        if (startD != null) 'start_date': _iso(startD!, false),
        if (endD != null) 'end_date': _iso(endD!, false)});
    });
  }

  void _inspectionForm() {
    final desc = TextEditingController(); final area = TextEditingController(); final action = TextEditingController();
    String type = 'routine'; String sev = 'medium'; int? prem;
    DateTime? followUp;
    _sheet(tr('سجل تفتيش', 'Inspection'), (set) => [
      _label(tr('تصنيف التفتيش', 'Inspection classification')),
      _dropdown<String>(tr('النوع', 'Type'), type,
          _inspTypes.isNotEmpty
              ? [for (final t in _inspTypes) DropdownMenuItem(value: '${t[0]}', child: Text('${t[1]}'))]
              : [DropdownMenuItem(value: 'routine', child: Text(tr('روتيني', 'Routine')))],
          (v) => set(() => type = v ?? 'routine')),
      _dropdown<String>(tr('درجة الخطورة', 'Severity'), sev,
          _severities.isNotEmpty
              ? [for (final s in _severities) DropdownMenuItem(value: '${s[0]}', child: Text('${s[1]}'))]
              : [DropdownMenuItem(value: 'medium', child: Text(tr('متوسط', 'Medium')))],
          (v) => set(() => sev = v ?? 'medium')),
      _dropdown<int>(tr('الموقع', 'Premise'), prem, [for (final p in _premises) DropdownMenuItem(value: p['id'] as int, child: Text('${p['name']}'))], (v) => set(() => prem = v)),
      _label(tr('التفاصيل', 'Details')),
      _tf(area, tr('المنطقة/القسم المُفتَّش', 'Inspected area / section')),
      _tf(desc, tr('الملاحظات والمخالفات', 'Findings & violations'), lines: 3),
      _tf(action, tr('الإجراء التصحيحي المطلوب', 'Required corrective action'), lines: 2),
      _dateTf(tr('تاريخ المتابعة', 'Follow-up date'), followUp, false, (d) => set(() => followUp = d)),
    ], () async {
      await context.read<AuthProvider>().api.securitySupInspectionCreate({
        'inspection_type': type, 'severity': sev,
        if (prem != null) 'premise_id': prem,
        if (area.text.trim().isNotEmpty) 'area': area.text.trim(),
        'issue_description': desc.text.trim(),
        if (action.text.trim().isNotEmpty) 'corrective_action': action.text.trim(),
        if (followUp != null) 'follow_up_date': _iso(followUp!, false)});
    });
  }

  void _notifyForm() {
    final title = TextEditingController(); final msg = TextEditingController();
    _sheet(tr('إشعار الفريق', 'Notify team'), (set) => [
      _tf(title, tr('العنوان (اختياري)', 'Title (optional)')),
      _tf(msg, tr('نص الرسالة', 'Message'), lines: 3),
    ], () async {
      if (msg.text.trim().isEmpty) throw Exception(tr('الرسالة مطلوبة', 'Message required'));
      await context.read<AuthProvider>().api.securitySupNotify(msg.text.trim(), title: title.text.trim().isEmpty ? null : title.text.trim());
    });
  }

  void _ok(String what) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('${tr('تمّ', 'Done')} — $what'), backgroundColor: _green));
  void _err(String m) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: _red));
}
