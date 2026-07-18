import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'searchable_picker.dart';

/// Client broadcast console: compose to a filtered audience (with live reach
/// preview), pick a type/priority, send now or schedule for later — plus a
/// dashboard of sent stats, the sent log, and pending scheduled sends.
class NotifySendScreen extends StatefulWidget {
  const NotifySendScreen({super.key});
  @override
  State<NotifySendScreen> createState() => _NotifySendScreenState();
}

class _NotifySendScreenState extends State<NotifySendScreen> with SingleTickerProviderStateMixin {
  Map<String, dynamic>? _opts;
  List<dynamic> _sent = [];
  List<dynamic> _scheduled = [];
  final _title = TextEditingController();
  final _body = TextEditingController();
  String _audience = 'all';
  String _ntype = 'info';
  int? _teamId;
  String? _serviceType;
  int? _workerId;
  DateTime? _schedule;
  int? _reach;
  bool _sending = false;
  late final TabController _tab;

  static const _accent = Color(0xFFC0392B);
  static const _navy = Color(0xFF0E3A5F);
  static const _types = {
    'info': (Color(0xFF3B82F6), Icons.info_rounded, 'معلومة', 'Info'),
    'task': (Color(0xFF16A34A), Icons.assignment_rounded, 'مهمة', 'Task'),
    'warning': (Color(0xFFF7A23B), Icons.warning_amber_rounded, 'تنبيه', 'Warning'),
    'alert': (Color(0xFFE5484D), Icons.error_rounded, 'طوارئ', 'Alert'),
  };

  @override
  void initState() {
    super.initState();
    _tab = TabController(length: 3, vsync: this);
    _load();
  }

  @override
  void dispose() {
    _tab.dispose();
    _title.dispose();
    _body.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final api = context.read<AuthProvider>().api;
      final o = await api.notifyOptions();
      final s = await api.notifySent();
      final sc = await api.notifyScheduled();
      if (mounted) setState(() { _opts = o; _sent = s; _scheduled = sc; });
      _refreshReach();
    } catch (_) {}
  }

  Map<String, dynamic> _audienceBody() {
    final b = <String, dynamic>{'audience': _audience};
    if (_audience == 'team') b['team_id'] = _teamId;
    if (_audience == 'service') b['service_type'] = _serviceType;
    if (_audience == 'worker') b['employee_id'] = _workerId;
    return b;
  }

  Future<void> _refreshReach() async {
    setState(() => _reach = null);
    try {
      final n = await context.read<AuthProvider>().api.notifyPreview(_audienceBody());
      if (mounted) setState(() => _reach = n);
    } catch (_) {}
  }

  Future<void> _pickSchedule() async {
    final now = DateTime.now();
    final d = await showDatePicker(
      context: context, firstDate: now, lastDate: now.add(const Duration(days: 365)),
      initialDate: _schedule ?? now.add(const Duration(hours: 1)),
    );
    if (d == null || !mounted) return;
    final t = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(_schedule ?? now.add(const Duration(hours: 1))),
    );
    if (t == null) return;
    setState(() => _schedule = DateTime(d.year, d.month, d.day, t.hour, t.minute));
  }

  Future<void> _send() async {
    if (_title.text.trim().isEmpty) {
      _snack(tr('أدخل عنوان الإشعار', 'Enter a title'), _accent);
      return;
    }
    setState(() => _sending = true);
    final body = _audienceBody()
      ..addAll({'title': _title.text.trim(), 'body': _body.text.trim(), 'ntype': _ntype});
    if (_schedule != null) {
      body['scheduled_datetime'] = _schedule!.toUtc().toIso8601String().split('.').first.replaceFirst('T', ' ');
      body['audience_label'] = _audienceLabel();
    }
    try {
      final r = await context.read<AuthProvider>().api.notifySend(body);
      if (!mounted) return;
      _title.clear();
      _body.clear();
      final scheduled = r['scheduled'] == true;
      setState(() { _schedule = null; });
      _snack(
        scheduled
            ? tr('تمت جدولة الإشعار لـ ${r['recipients']} مستلم', 'Scheduled for ${r['recipients']} recipients')
            : tr('أُرسل إلى ${r['recipients']} مستلم', 'Sent to ${r['recipients']} recipients'),
        const Color(0xFF16A34A),
      );
      _load();
      if (scheduled) _tab.animateTo(2);
    } catch (e) {
      if (mounted) _snack('$e', _accent);
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  void _snack(String m, Color c) => ScaffoldMessenger.of(context)
      .showSnackBar(SnackBar(content: Text(m), backgroundColor: c, behavior: SnackBarBehavior.floating));

  String _audienceLabel() {
    switch (_audience) {
      case 'all': return tr('كل العاملين', 'All workers');
      case 'late': return tr('المتأخرون', 'Late workers');
      case 'team': return tr('فريق', 'Team');
      case 'service': return tr('خدمة', 'Service');
      case 'worker': return tr('عامل محدّد', 'Specific worker');
    }
    return '';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF6F7F9),
      appBar: AppBar(
        title: Text(tr('مركز الإشعارات', 'Notification center')),
        backgroundColor: _accent, foregroundColor: Colors.white,
        bottom: TabBar(
          controller: _tab,
          indicatorColor: Colors.white, labelColor: Colors.white,
          unselectedLabelColor: Colors.white70,
          labelStyle: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5),
          tabs: [
            Tab(text: tr('إرسال', 'Compose')),
            Tab(text: tr('المُرسَلة', 'Sent')),
            Tab(text: tr('المجدولة (${_scheduled.length})', 'Scheduled (${_scheduled.length})')),
          ],
        ),
      ),
      body: _opts == null
          ? const Center(child: CircularProgressIndicator(color: _accent))
          : TabBarView(controller: _tab, children: [_compose(), _sentTab(), _scheduledTab()]),
    );
  }

  // ————————————————————————————————————————————— compose tab
  Widget _compose() {
    final o = _opts!;
    return ListView(padding: const EdgeInsets.all(14), children: [
      // audience picker
      _label(Icons.groups_rounded, tr('الجمهور المستهدف', 'Target audience')),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final a in const [
          ('all', Icons.public_rounded), ('late', Icons.running_with_errors_rounded),
          ('team', Icons.diversity_3_rounded), ('service', Icons.design_services_rounded),
          ('worker', Icons.person_rounded),
        ])
          _audChip(a.$1, a.$2),
      ]),
      const SizedBox(height: 10),
      if (_audience == 'team')
        _dropdown(tr('اختر الفريق', 'Select team'), (o['teams'] as List), _teamId,
            (v) { setState(() => _teamId = v); _refreshReach(); }),
      if (_audience == 'service')
        _dropdownStr(tr('اختر الخدمة', 'Select service'), (o['services'] as List), _serviceType,
            (v) { setState(() => _serviceType = v); _refreshReach(); }),
      if (_audience == 'worker')
        _dropdown(tr('اختر العامل', 'Select worker'), (o['workers'] as List), _workerId,
            (v) { setState(() => _workerId = v); _refreshReach(); }),
      // reach preview
      _reachBanner(),
      const SizedBox(height: 16),
      // type / priority
      _label(Icons.flag_rounded, tr('نوع الإشعار', 'Notification type')),
      const SizedBox(height: 8),
      Row(children: [
        for (final e in _types.entries) Expanded(child: _typeChip(e.key)),
      ]),
      const SizedBox(height: 16),
      // content
      _label(Icons.edit_rounded, tr('المحتوى', 'Content')),
      const SizedBox(height: 8),
      _field(_title, tr('العنوان', 'Title'), Icons.title_rounded),
      const SizedBox(height: 10),
      _field(_body, tr('نص الرسالة', 'Message'), Icons.notes_rounded, lines: 4),
      const SizedBox(height: 16),
      // schedule
      _scheduleRow(),
      const SizedBox(height: 18),
      SizedBox(
        height: 52,
        child: FilledButton.icon(
          style: FilledButton.styleFrom(
            backgroundColor: _schedule != null ? _navy : _accent,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          ),
          onPressed: _sending ? null : _send,
          icon: _sending
              ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
              : Icon(_schedule != null ? Icons.schedule_send_rounded : Icons.send_rounded),
          label: Text(
            _schedule != null ? tr('جدولة الإرسال', 'Schedule send') : tr('إرسال الآن', 'Send now'),
            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15),
          ),
        ),
      ),
      const SizedBox(height: 20),
    ]);
  }

  Widget _reachBanner() {
    return Container(
      margin: const EdgeInsets.only(top: 10),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: [_navy, Color.lerp(_navy, Colors.black, 0.3)!]),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Row(children: [
        const Icon(Icons.campaign_rounded, color: Colors.white, size: 20),
        const SizedBox(width: 10),
        Expanded(child: Text(tr('سيصل هذا الإشعار إلى', 'This notification will reach'),
            style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 12, fontWeight: FontWeight.w600))),
        _reach == null
            ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
            : Text(tr('$_reach مستلم', '$_reach recipients'),
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15)),
      ]),
    );
  }

  Widget _scheduleRow() {
    return Container(
      padding: const EdgeInsets.all(4),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _schedule != null ? _navy : Colors.grey.shade300),
      ),
      child: ListTile(
        leading: Icon(Icons.schedule_rounded, color: _schedule != null ? _navy : Colors.grey.shade500),
        title: Text(_schedule != null ? tr('مجدول', 'Scheduled') : tr('إرسال فوري', 'Send immediately'),
            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5)),
        subtitle: Text(
          _schedule != null
              ? '${_schedule!.toLocal()}'.substring(0, 16)
              : tr('اضغط لجدولة الإرسال لاحقًا', 'Tap to schedule for later'),
          style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600),
        ),
        trailing: _schedule != null
            ? IconButton(icon: const Icon(Icons.close_rounded, size: 20), onPressed: () => setState(() => _schedule = null))
            : const Icon(Icons.chevron_left_rounded),
        onTap: _pickSchedule,
      ),
    );
  }

  Widget _audChip(String v, IconData ic) {
    final on = _audience == v;
    return GestureDetector(
      onTap: () { setState(() => _audience = v); _refreshReach(); },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 9),
        decoration: BoxDecoration(
          color: on ? _accent : Colors.white,
          borderRadius: BorderRadius.circular(22),
          border: Border.all(color: on ? _accent : Colors.grey.shade300),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(ic, size: 15, color: on ? Colors.white : _navy),
          const SizedBox(width: 6),
          Text(_audLabel(v), style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: on ? Colors.white : _navy)),
        ]),
      ),
    );
  }

  String _audLabel(String v) {
    switch (v) {
      case 'all': return tr('الكل', 'All');
      case 'late': return tr('المتأخرون', 'Late');
      case 'team': return tr('فريق', 'Team');
      case 'service': return tr('خدمة', 'Service');
      case 'worker': return tr('عامل', 'Worker');
    }
    return v;
  }

  Widget _typeChip(String key) {
    final s = _types[key]!;
    final on = _ntype == key;
    return GestureDetector(
      onTap: () => setState(() => _ntype = key),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        margin: const EdgeInsets.symmetric(horizontal: 3),
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(
          color: on ? s.$1 : Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: on ? s.$1 : Colors.grey.shade300),
        ),
        child: Column(children: [
          Icon(s.$2, size: 20, color: on ? Colors.white : s.$1),
          const SizedBox(height: 4),
          Text(tr(s.$3, s.$4), style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: on ? Colors.white : _navy)),
        ]),
      ),
    );
  }

  Widget _label(IconData ic, String t) => Row(children: [
        Icon(ic, size: 16, color: _accent),
        const SizedBox(width: 7),
        Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
      ]);

  Widget _field(TextEditingController c, String label, IconData ic, {int lines = 1}) => TextField(
        controller: c, maxLines: lines,
        decoration: InputDecoration(
          labelText: label, prefixIcon: Icon(ic, size: 20),
          filled: true, fillColor: Colors.white,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: _accent, width: 1.6)),
        ),
      );

  Widget _dropdown(String label, List items, int? val, ValueChanged<int?> onCh) => Padding(
        padding: const EdgeInsets.only(bottom: 4),
        child: SearchableField(
          label: label, icon: Icons.search_rounded, value: val, accent: _accent, allowClear: false,
          options: [for (final x in items) PickOption(value: x['id'],
              label: '${x['name']}', sublabel: x['job'] != null ? '${x['job']}' : (x['facility'] != null ? '${x['facility']}' : null))],
          onChanged: (v) => onCh(v as int?),
        ),
      );

  Widget _dropdownStr(String label, List items, String? val, ValueChanged<String?> onCh) => Padding(
        padding: const EdgeInsets.only(bottom: 4),
        child: SearchableField(
          label: label, icon: Icons.search_rounded, value: val, accent: _accent, allowClear: false,
          options: [for (final x in items) PickOption(value: '${x['v']}', label: '${x['l']}', search: '${x['v']}')],
          onChanged: (v) => onCh(v as String?),
        ),
      );

  // ————————————————————————————————————————————— sent tab (stats + log)
  Widget _sentTab() {
    final batches = _sent.length;
    final totalRecips = _sent.fold<int>(0, (s, g) => s + (((g as Map)['total'] ?? 0) as int));
    final totalRead = _sent.fold<int>(0, (s, g) => s + (((g as Map)['read'] ?? 0) as int));
    final rate = totalRecips > 0 ? (totalRead * 100 / totalRecips).round() : 0;
    return RefreshIndicator(
      color: _accent,
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.all(14), children: [
        // stats dashboard
        CustomPaint(
          painter: const BrandPattern(opacity: 0.06),
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [Color(0xFFE24A3B), Color(0xFFC0392B), Color(0xFF8E241B)],
                  begin: Alignment.topRight, end: Alignment.bottomLeft),
              borderRadius: BorderRadius.circular(18),
              boxShadow: [BoxShadow(color: _accent.withValues(alpha: 0.3), blurRadius: 12, offset: const Offset(0, 6))],
            ),
            child: Row(children: [
              _stat('$batches', tr('حملة', 'Campaigns'), Icons.campaign_rounded),
              _statDiv(),
              _stat('$totalRecips', tr('مستلم', 'Recipients'), Icons.people_rounded),
              _statDiv(),
              _stat('$rate%', tr('نسبة القراءة', 'Read rate'), Icons.mark_email_read_rounded),
            ]),
          ),
        ),
        const SizedBox(height: 16),
        _label(Icons.history_rounded, tr('سجل الحملات', 'Campaign log')),
        const SizedBox(height: 8),
        if (_sent.isEmpty)
          Padding(padding: const EdgeInsets.all(30), child: Center(
              child: Text(tr('لم تُرسِل إشعارات بعد', 'No notifications sent yet'),
                  style: TextStyle(color: Colors.grey.shade500)))),
        ..._sent.map((g) => _sentCard(g as Map)),
      ]),
    );
  }

  Widget _sentCard(Map g) {
    final total = (g['total'] ?? 0) as int;
    final read = (g['read'] ?? 0) as int;
    final pct = total > 0 ? read / total : 0.0;
    final t = _types['${g['ntype']}'] ?? _types['info']!;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: Colors.white, borderRadius: BorderRadius.circular(14),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 7, offset: const Offset(0, 3))],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(
            width: 36, height: 36, alignment: Alignment.center,
            decoration: BoxDecoration(color: t.$1.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(10)),
            child: Icon(t.$2, size: 18, color: t.$1),
          ),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${g['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: _navy)),
            Text('${g['date'] ?? ''}'.replaceFirst('T', ' ').split('.').first,
                style: TextStyle(fontSize: 10.5, color: Colors.grey.shade500)),
          ])),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
            decoration: BoxDecoration(color: const Color(0xFF16A34A).withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
            child: Text('$read/$total', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12, color: Color(0xFF16A34A))),
          ),
        ]),
        const SizedBox(height: 10),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: pct, minHeight: 6,
            backgroundColor: Colors.grey.shade200,
            valueColor: const AlwaysStoppedAnimation(Color(0xFF16A34A)),
          ),
        ),
      ]),
    );
  }

  Widget _stat(String v, String l, IconData ic) => Expanded(
        child: Column(children: [
          Icon(ic, color: Colors.white, size: 18),
          const SizedBox(height: 4),
          Text(v, style: const TextStyle(color: Colors.white, fontSize: 19, fontWeight: FontWeight.w900)),
          Text(l, style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 10, fontWeight: FontWeight.w600)),
        ]),
      );

  Widget _statDiv() => Container(width: 1, height: 36, color: Colors.white.withValues(alpha: 0.2));

  // ————————————————————————————————————————————— scheduled tab
  Widget _scheduledTab() {
    return RefreshIndicator(
      color: _accent,
      onRefresh: _load,
      child: _scheduled.isEmpty
          ? ListView(children: [
              const SizedBox(height: 100),
              Icon(Icons.schedule_rounded, size: 60, color: Colors.grey.shade300),
              const SizedBox(height: 12),
              Center(child: Text(tr('لا إشعارات مجدولة', 'No scheduled notifications'),
                  style: TextStyle(color: Colors.grey.shade500, fontWeight: FontWeight.w600))),
            ])
          : ListView(padding: const EdgeInsets.all(14), children: [
              ..._scheduled.map((s) => _schedCard(s as Map)),
            ]),
    );
  }

  Widget _schedCard(Map s) {
    final t = _types['${s['ntype']}'] ?? _types['info']!;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: Colors.white, borderRadius: BorderRadius.circular(14),
        border: Border.all(color: _navy.withValues(alpha: 0.15)),
      ),
      child: Row(children: [
        Container(
          width: 42, height: 42, alignment: Alignment.center,
          decoration: BoxDecoration(color: t.$1.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)),
          child: Icon(t.$2, color: t.$1, size: 20),
        ),
        const SizedBox(width: 11),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${s['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: _navy)),
          const SizedBox(height: 3),
          Row(children: [
            const Icon(Icons.schedule_rounded, size: 12, color: _navy),
            const SizedBox(width: 4),
            Text('${s['scheduled_datetime']}'.replaceFirst('T', ' ').split('.').first,
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: _navy)),
          ]),
          const SizedBox(height: 2),
          Text(tr('${s['recipients']} مستلم · ${s['audience'] ?? ''}', '${s['recipients']} recipients · ${s['audience'] ?? ''}'),
              style: TextStyle(fontSize: 10.5, color: Colors.grey.shade500)),
        ])),
        IconButton(
          icon: const Icon(Icons.cancel_rounded, color: Color(0xFFE5484D)),
          tooltip: tr('إلغاء', 'Cancel'),
          onPressed: () async {
            try {
              await context.read<AuthProvider>().api.notifyScheduledCancel(s['id'] as int);
              _load();
            } catch (e) {
              if (mounted) _snack('$e', _accent);
            }
          },
        ),
      ]),
    );
  }
}
