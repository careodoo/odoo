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

  List<Map> get _guards => ((_opts?['guards'] as List?) ?? const []).cast<Map>();
  List<Map> get _routes => ((_opts?['routes'] as List?) ?? const []).cast<Map>();

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
          for (final m in members) Padding(padding: const EdgeInsets.only(bottom: 8), child: Row(children: [
            Container(width: 9, height: 9, decoration: BoxDecoration(color: _stateColor[m['state']] ?? _grey, shape: BoxShape.circle)),
            const SizedBox(width: 9),
            Expanded(child: Text('${m['name']}', style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600))),
            if (m['heart_rate'] != null) ...[const Icon(Icons.favorite_rounded, color: _red, size: 12), const SizedBox(width: 3),
              Text('${m['heart_rate']}', style: const TextStyle(color: _grey, fontSize: 11))],
            const SizedBox(width: 10),
            Text(_stLabel('${m['state']}'), style: TextStyle(color: _stateColor[m['state']] ?? _grey, fontSize: 11, fontWeight: FontWeight.w800)),
          ])),
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

  void _taskForm() {
    final name = TextEditingController(); final desc = TextEditingController();
    int? guard; String prio = '1';
    _sheet(tr('مهمة جديدة', 'New task'), (set) => [
      _tf(name, tr('عنوان المهمة', 'Task title')),
      _tf(desc, tr('الوصف (اختياري)', 'Description (optional)'), lines: 2),
      _dropdown<int>(tr('إسناد لحارس', 'Assign to guard'), guard, [for (final g in _guards) DropdownMenuItem(value: g['id'] as int, child: Text('${g['name']}'))], (v) => set(() => guard = v)),
      _dropdown<String>(tr('الأولوية', 'Priority'), prio, [
        DropdownMenuItem(value: '0', child: Text(tr('منخفض', 'Low'))), DropdownMenuItem(value: '1', child: Text(tr('عادي', 'Normal'))),
        DropdownMenuItem(value: '2', child: Text(tr('مرتفع', 'High'))), DropdownMenuItem(value: '3', child: Text(tr('عاجل', 'Urgent')))], (v) => set(() => prio = v ?? '1')),
    ], () async {
      if (name.text.trim().isEmpty) throw Exception(tr('العنوان مطلوب', 'Title required'));
      await context.read<AuthProvider>().api.securitySupTaskCreate({
        'name': name.text.trim(), if (desc.text.trim().isNotEmpty) 'description': desc.text.trim(),
        if (guard != null) 'assigned_guard_id': guard, 'priority': prio});
    });
  }

  void _patrolForm() {
    int? route; int? guard;
    _sheet(tr('دورية جديدة', 'New patrol'), (set) => [
      _dropdown<int>(tr('المسار', 'Route'), route, [for (final r in _routes) DropdownMenuItem(value: r['id'] as int, child: Text('${r['name']}'))], (v) => set(() => route = v)),
      _dropdown<int>(tr('الحارس', 'Guard'), guard, [for (final g in _guards) DropdownMenuItem(value: g['id'] as int, child: Text('${g['name']}'))], (v) => set(() => guard = v)),
    ], () async {
      if (route == null) throw Exception(tr('اختر المسار', 'Select route'));
      await context.read<AuthProvider>().api.securitySupPatrolCreate({'route_id': route, if (guard != null) 'guard_id': guard});
    });
  }

  void _gatepassForm() {
    final person = TextEditingController(); final purpose = TextEditingController();
    _sheet(tr('تصريح دخول', 'Gate pass'), (set) => [
      _tf(person, tr('اسم الشخص', 'Person name')),
      _tf(purpose, tr('الغرض', 'Purpose')),
    ], () async {
      if (person.text.trim().isEmpty) throw Exception(tr('الاسم مطلوب', 'Name required'));
      await context.read<AuthProvider>().api.securitySupGatepassCreate({'person_name': person.text.trim(), 'purpose': purpose.text.trim()});
    });
  }

  void _inspectionForm() {
    final desc = TextEditingController(); String type = 'routine'; String sev = 'medium';
    _sheet(tr('سجل تفتيش', 'Inspection'), (set) => [
      _dropdown<String>(tr('النوع', 'Type'), type, [
        DropdownMenuItem(value: 'routine', child: Text(tr('روتيني', 'Routine'))), DropdownMenuItem(value: 'special', child: Text(tr('خاص', 'Special'))),
        DropdownMenuItem(value: 'follow_up', child: Text(tr('متابعة', 'Follow-up'))), DropdownMenuItem(value: 'audit', child: Text(tr('تدقيق', 'Audit')))], (v) => set(() => type = v ?? 'routine')),
      _dropdown<String>(tr('الخطورة', 'Severity'), sev, [
        DropdownMenuItem(value: 'low', child: Text(tr('منخفض', 'Low'))), DropdownMenuItem(value: 'medium', child: Text(tr('متوسط', 'Medium'))),
        DropdownMenuItem(value: 'high', child: Text(tr('عالٍ', 'High'))), DropdownMenuItem(value: 'critical', child: Text(tr('حرج', 'Critical')))], (v) => set(() => sev = v ?? 'medium')),
      _tf(desc, tr('الوصف/الملاحظات', 'Description'), lines: 3),
    ], () async {
      await context.read<AuthProvider>().api.securitySupInspectionCreate({
        'inspection_type': type, 'severity': sev, 'issue_description': desc.text.trim()});
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
