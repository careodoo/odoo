import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import '../attendance_screen.dart';
import '../pms/pms_section.dart';
import '../pms/pms_employee_file.dart';
import '../pdf_report_screen.dart';
import '../../core/account_deletion.dart';

/// The «My» module — the signed-in user's own hub: who they are, how they're
/// doing, the services they can start, and their requests with live statuses.
/// Shared by the management and project-management shells.
class MyScreen extends StatefulWidget {
  final Color accent;
  const MyScreen({super.key, this.accent = const Color(0xFF4F46E5)});
  @override
  State<MyScreen> createState() => _MyScreenState();
}

class _MyScreenState extends State<MyScreen> {
  Map<String, dynamic>? _d;
  String? _error;
  bool _busy = false;

  static const _ink = Color(0xFF1E293B);
  static const _slate = Color(0xFF64748B);

  @override
  void initState() {
    super.initState();
    _load();
  }

  List<Map> _delegations = const [];

  Future<void> _load() async {
    setState(() => _error = null);
    try {
      final d = await context.read<AuthProvider>().api.myHub();
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
    // Sections delegated to me — non-fatal if it fails.
    try {
      final dg = await context.read<AuthProvider>().api.pmsMyDelegations();
      if (mounted) setState(() => _delegations = ((dg['delegations'] as List?) ?? const []).cast<Map>());
    } catch (_) {}
  }

  Color get _c => widget.accent;

  static const _reqTint = {
    'leaves': Color(0xFF16A34A),
    'permissions': Color(0xFF0891B2),
    'loans': Color(0xFFD97706),
    'expenses': Color(0xFF7C3AED),
  };

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      body: RefreshIndicator(
        onRefresh: _load,
        color: _c,
        child: _error != null
            ? ListView(children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(24, 120, 24, 24),
                  child: Column(children: [
                    const Icon(Icons.cloud_off_rounded, size: 44, color: _slate),
                    const SizedBox(height: 12),
                    Text(tr('تعذّر تحميل صفحتك', 'Could not load your page'),
                        style: const TextStyle(fontWeight: FontWeight.w800, color: _ink)),
                    const SizedBox(height: 6),
                    Text('$_error', textAlign: TextAlign.center,
                        style: const TextStyle(color: _slate, fontSize: 12)),
                  ]),
                )
              ])
            : _d == null
                ? Center(child: CircularProgressIndicator(color: _c))
                : _body(_d!),
      ),
    );
  }

  Widget _body(Map d) {
    final p = (d['profile'] as Map?) ?? const {};
    final stats = ((d['stats'] as List?) ?? const []).cast<Map>();
    final services = ((d['services'] as List?) ?? const []).cast<Map>();
    final requests = ((d['requests'] as List?) ?? const []).cast<Map>();
    return ListView(padding: EdgeInsets.zero, children: [
      _headerCard(p, stats),
      if (_delegations.isNotEmpty) ...[
        _sectionTitle(tr('مفوَّض إليّ للمتابعة', 'Delegated to me'),
            Icons.assignment_ind_rounded, trailing: '${_delegations.length}'),
        for (final dg in _delegations) _delegationCard(dg),
      ],
      _sectionTitle(tr('الخدمات الذاتية', 'Self-service'), Icons.grid_view_rounded),
      _servicesGrid(services),
      _sectionTitle(tr('طلباتي', 'My requests'), Icons.receipt_long_rounded,
          trailing: '${requests.length}'),
      if (requests.isEmpty)
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 8),
          child: Text(tr('لا طلبات بعد', 'No requests yet'),
              style: const TextStyle(color: _slate, fontSize: 12.5)),
        )
      else
        for (final r in requests) _requestCard(r),
      // Account controls — deletion must always be reachable (App Store 5.1.1v).
      const SizedBox(height: 20),
      Center(child: TextButton.icon(
        onPressed: () => showDeleteAccountFlow(context),
        icon: const Icon(Icons.delete_forever_rounded, size: 18, color: Color(0xFFB91C1C)),
        label: Text(tr('حذف الحساب', 'Delete account'),
            style: const TextStyle(color: Color(0xFFB91C1C), fontWeight: FontWeight.w800)),
      )),
      const SizedBox(height: 24),
    ]);
  }

  // ---- header: avatar + identity + stat strip ---------------------------
  Widget _headerCard(Map p, List<Map> stats) {
    final initial = '${p['name'] ?? '?'}'.trim();
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
            colors: [_c, _c.withValues(alpha: 0.78)],
            begin: Alignment.topRight, end: Alignment.bottomLeft),
      ),
      child: SafeArea(
        bottom: false,
        child: Padding(
          padding: const EdgeInsets.fromLTRB(18, 16, 18, 18),
          child: Column(children: [
            Row(children: [
              CircleAvatar(
                radius: 30,
                backgroundColor: Colors.white24,
                backgroundImage: p['avatar_url'] != null
                    ? NetworkImage('${p['avatar_url']}')
                    : null,
                child: p['avatar_url'] == null
                    ? Text(initial.isEmpty ? '?' : initial.characters.first,
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 22))
                    : null,
              ),
              const SizedBox(width: 14),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${p['name'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
                if (p['job'] != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text('${p['job']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 12.5, fontWeight: FontWeight.w600)),
                  ),
                if (p['department'] != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 1),
                    child: Text('${p['department']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.7), fontSize: 11)),
                  ),
              ])),
              if (p['is_manager'] == true)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                  decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(20)),
                  child: Text(tr('مدير', 'Manager'),
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 10)),
                ),
            ]),
            if (stats.isNotEmpty) ...[
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.symmetric(vertical: 12),
                decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.16),
                    borderRadius: BorderRadius.circular(16)),
                child: Row(children: [
                  for (var i = 0; i < stats.length; i++) ...[
                    if (i > 0) Container(width: 1, height: 28, color: Colors.white24),
                    Expanded(child: Column(children: [
                      Text('${stats[i]['value'] ?? 0}',
                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
                      const SizedBox(height: 2),
                      Text(gLang == 'en' ? '${stats[i]['en'] ?? ''}' : '${stats[i]['ar'] ?? ''}',
                          maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
                          style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 9.5, fontWeight: FontWeight.w700)),
                    ])),
                  ],
                ]),
              ),
            ],
          ]),
        ),
      ),
    );
  }

  Widget _sectionTitle(String t, IconData ic, {String? trailing}) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 18, 16, 8),
        child: Row(children: [
          Icon(ic, size: 18, color: _c),
          const SizedBox(width: 7),
          Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: _ink)),
          const Spacer(),
          if (trailing != null)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(color: _c.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(20)),
              child: Text(trailing, style: TextStyle(color: _c, fontWeight: FontWeight.w800, fontSize: 11)),
            ),
        ]),
      );

  Widget _delegationCard(Map dg) {
    final pending = '${dg['state'] ?? 'accepted'}' == 'pending';
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 0, 14, 10),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: (pending ? const Color(0xFFF59E0B) : _c).withValues(alpha: 0.30)),
      ),
      clipBehavior: Clip.antiAlias,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: pending
              ? null
              : () => Navigator.push(context, MaterialPageRoute(
                  builder: (_) => PmsSectionScreen(
                      projectId: dg['project_id'] as int,
                      code: '${dg['section_code']}',
                      label: '${dg['section_label']}'))),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(children: [
              Row(children: [
                Container(
                  padding: const EdgeInsets.all(9),
                  decoration: BoxDecoration(
                      color: (pending ? const Color(0xFFF59E0B) : _c).withValues(alpha: 0.10),
                      borderRadius: BorderRadius.circular(11)),
                  child: Icon(pending ? Icons.assignment_late_rounded : Icons.folder_shared_rounded,
                      color: pending ? const Color(0xFFB45309) : _c, size: 20),
                ),
                const SizedBox(width: 12),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${dg['section_label']}',
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: _ink)),
                  const SizedBox(height: 2),
                  Text('${dg['project'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: _slate, fontSize: 11.5)),
                  if (dg['granted_by'] != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Text(tr('من: ${dg['granted_by']}', 'By: ${dg['granted_by']}'),
                          style: const TextStyle(color: _slate, fontSize: 10.5)),
                    ),
                ])),
                if (dg['date_until'] != null)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(color: const Color(0xFFF59E0B).withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
                    child: Text('${tr('حتى', 'until')} ${dg['date_until']}',
                        style: const TextStyle(color: Color(0xFFB45309), fontWeight: FontWeight.w700, fontSize: 9.5)),
                  )
                else if (!pending)
                  Icon(Icons.chevron_left_rounded, color: _c.withValues(alpha: 0.5)),
              ]),
              if (pending) ...[
                const SizedBox(height: 10),
                Row(children: [
                  Expanded(child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(
                        foregroundColor: const Color(0xFFE11D48),
                        side: const BorderSide(color: Color(0xFFE11D48)),
                        padding: const EdgeInsets.symmetric(vertical: 9)),
                    onPressed: _busy ? null : () => _respondDelegation(dg, 'reject'),
                    icon: const Icon(Icons.close_rounded, size: 16),
                    label: Text(tr('رفض', 'Reject'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12)),
                  )),
                  const SizedBox(width: 8),
                  Expanded(child: FilledButton.icon(
                    style: FilledButton.styleFrom(
                        backgroundColor: const Color(0xFF16A34A),
                        padding: const EdgeInsets.symmetric(vertical: 9)),
                    onPressed: _busy ? null : () => _respondDelegation(dg, 'accept'),
                    icon: const Icon(Icons.check_rounded, size: 16),
                    label: Text(tr('قبول', 'Accept'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12)),
                  )),
                ]),
              ],
            ]),
          ),
        ),
      ),
    );
  }

  Future<void> _respondDelegation(Map dg, String act) async {
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.pmsDelegationRespond(dg['id'] as int, act);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(act == 'accept' ? tr('تم قبول التفويض', 'Delegation accepted') : tr('تم رفض التفويض', 'Delegation rejected')),
          backgroundColor: act == 'accept' ? const Color(0xFF16A34A) : const Color(0xFFE11D48)));
      await _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e'), backgroundColor: const Color(0xFFE11D48)));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  // ---- services as professional icon tiles ------------------------------
  Widget _servicesGrid(List<Map> services) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        child: GridView.count(
          crossAxisCount: 3,
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 10,
          crossAxisSpacing: 10,
          childAspectRatio: 1.02,
          children: [for (final s in services) _serviceTile(s)],
        ),
      );

  Widget _serviceTile(Map s) => Material(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: () => _openService('${s['key']}'),
          child: Container(
            decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              Container(
                padding: const EdgeInsets.all(11),
                decoration: BoxDecoration(color: _c.withValues(alpha: 0.10), shape: BoxShape.circle),
                child: Text('${s['icon'] ?? '•'}', style: const TextStyle(fontSize: 22)),
              ),
              const SizedBox(height: 8),
              Text(gLang == 'en' ? '${s['en'] ?? ''}' : '${s['ar'] ?? ''}',
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 11.5, color: _ink)),
            ]),
          ),
        ),
      );

  // Service key → the create-form source it maps to (null = handled elsewhere).
  static const _serviceSource = {
    'leave': 'leaves', 'loan': 'loans', 'permission': 'permissions',
    'expense': 'expenses',
  };

  Future<void> _openService(String key) async {
    if (key == 'profile') {
      final p = (_d?['profile'] as Map?) ?? const {};
      final eid = p['employee_id'];
      if (eid == null) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(tr('لا يوجد ملف موظف مرتبط بحسابك', 'No employee file linked to your account')),
            backgroundColor: _c));
        return;
      }
      Navigator.push(context, MaterialPageRoute(
          builder: (_) => PmsEmployeeFileScreen(employeeId: eid as int, name: '${p['name'] ?? tr('بياناتي', 'My data')}')));
      return;
    }
    if (key == 'attendance' || key == 'timesheet') {
      // From «My», always show the signed-in user's OWN attendance.
      final eid = (_d?['profile'] as Map?)?['employee_id'];
      Navigator.push(context, MaterialPageRoute(
          builder: (_) => AttendanceScreen(lockEmployeeId: eid is int ? eid : null)));
      return;
    }
    final source = _serviceSource[key];
    if (source != null) {
      final created = await showModalBottomSheet<bool>(
        context: context, isScrollControlled: true, backgroundColor: Colors.white,
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
        builder: (_) => _MyCreateSheet(source: source, accent: _c),
      );
      if (created == true) _load();
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(tr('سيتوفّر إنشاء هذا الطلب هنا قريبًا', 'Creating this request here is coming soon')),
        backgroundColor: _c));
  }

  // ---- my requests, each clickable + deletable if draft -----------------
  Widget _requestCard(Map r) {
    final tint = _reqTint['${r['source']}'] ?? _slate;
    final canDelete = r['can_delete'] == true;
    return Container(
      margin: const EdgeInsets.fromLTRB(14, 0, 14, 10),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(15),
        border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => _openRequest(r),
        child: Row(children: [
        Container(width: 5, height: 76, color: tint),
        Expanded(child: Padding(
          padding: const EdgeInsets.fromLTRB(12, 11, 8, 11),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Text('${r['icon'] ?? ''} ', style: const TextStyle(fontSize: 13)),
              Text(gLang == 'en' ? '${r['en'] ?? ''}' : '${r['ar'] ?? ''}',
                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12, color: tint)),
              const Spacer(),
              if (r['state'] != null)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(color: tint.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(20)),
                  child: Text('${r['state']}', style: TextStyle(color: tint, fontWeight: FontWeight.w800, fontSize: 10)),
                ),
            ]),
            const SizedBox(height: 5),
            Text('${r['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: _ink)),
            const SizedBox(height: 3),
            Row(children: [
              if (r['date'] != null)
                Text('${r['date']}', style: const TextStyle(color: _slate, fontSize: 10.5)),
              if (r['amount'] != null) ...[
                const SizedBox(width: 10),
                Text('${r['amount']}', style: TextStyle(color: tint, fontWeight: FontWeight.w800, fontSize: 11.5)),
              ],
            ]),
          ]),
        )),
        if (canDelete)
          IconButton(
            tooltip: tr('حذف', 'Delete'),
            icon: const Icon(Icons.delete_outline_rounded, color: Color(0xFFE11D48), size: 20),
            onPressed: _busy ? null : () => _confirmDelete(r),
          )
        else
          Padding(padding: const EdgeInsets.only(left: 6),
              child: Icon(Icons.chevron_left_rounded, color: tint.withValues(alpha: 0.5))),
      ]),
      ),
    );
  }

  Future<void> _openRequest(Map r) async {
    await showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _MyRequestSheet(
          source: '${r['source']}', id: r['id'] as int,
          accent: _reqTint['${r['source']}'] ?? _c),
    );
    if (mounted) _load();
  }

  Future<void> _confirmDelete(Map r) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: Text(tr('حذف الطلب', 'Delete request'),
            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
        content: Text(tr('سيُحذف «${r['title']}». لا يمكن التراجع.',
            '"${r['title']}" will be deleted. This cannot be undone.')),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('تراجع', 'Back'))),
          FilledButton(
              style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE11D48)),
              onPressed: () => Navigator.pop(c, true),
              child: Text(tr('حذف', 'Delete'))),
        ],
      ),
    );
    if (ok != true || !mounted) return;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.myDelete('${r['source']}', r['id'] as int);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('تم الحذف', 'Deleted')), backgroundColor: const Color(0xFF16A34A)));
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('$e'), backgroundColor: const Color(0xFFE11D48)));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }
}

/// A form that builds itself from the server's field spec, for a self-service
/// request (leave, loan, …). The server validates and creates.
class _MyCreateSheet extends StatefulWidget {
  final String source;
  final Color accent;
  const _MyCreateSheet({required this.source, required this.accent});
  @override
  State<_MyCreateSheet> createState() => _MyCreateSheetState();
}

class _MyCreateSheetState extends State<_MyCreateSheet> {
  Map<String, dynamic>? _meta;
  String? _error;
  bool _busy = false;
  final Map<String, dynamic> _vals = {};
  final Map<String, TextEditingController> _ctrls = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final m = await context.read<AuthProvider>().api.myMeta(widget.source);
      if (mounted) setState(() => _meta = m);
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  @override
  void dispose() {
    for (final c in _ctrls.values) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _pickDate(String name, bool withTime) async {
    final init = DateTime.tryParse('${_vals[name] ?? ''}') ?? DateTime.now();
    final d = await showDatePicker(context: context, initialDate: init,
        firstDate: DateTime(2020), lastDate: DateTime(2100));
    if (d == null) return;
    var out = d;
    if (withTime) {
      final t = await showTimePicker(context: context, initialTime: TimeOfDay.fromDateTime(init));
      if (t != null) out = DateTime(d.year, d.month, d.day, t.hour, t.minute);
    }
    setState(() => _vals[name] = withTime
        ? '${out.toIso8601String().substring(0, 16).replaceFirst('T', ' ')}:00'
        : out.toIso8601String().substring(0, 10));
  }

  InputDecoration _dec(String label) => InputDecoration(
        labelText: label, isDense: true,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
      );

  Widget _field(Map f) {
    final name = '${f['name']}';
    final t = '${f['type']}';
    if (t == 'm2o' || t == 'selection') {
      final opts = ((f['options'] as List?) ?? const []).cast<Map>();
      return Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: DropdownButtonFormField(
          value: _vals[name], isExpanded: true, decoration: _dec('${f['label']}'),
          items: [for (final o in opts) DropdownMenuItem(value: o['v'], child: Text('${o['l']}', overflow: TextOverflow.ellipsis))],
          onChanged: (v) => setState(() => _vals[name] = v),
        ),
      );
    }
    if (t == 'date' || t == 'datetime') {
      return Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: InkWell(
          onTap: () => _pickDate(name, t == 'datetime'),
          child: InputDecorator(
            decoration: _dec('${f['label']}'),
            child: Row(children: [
              Icon(Icons.event_rounded, size: 18, color: widget.accent),
              const SizedBox(width: 8),
              Text('${_vals[name] ?? tr('اختر', 'Pick')}', style: const TextStyle(fontWeight: FontWeight.w700)),
            ]),
          ),
        ),
      );
    }
    final isNum = t == 'float' || t == 'integer';
    _ctrls[name] ??= TextEditingController();
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: TextField(
        controller: _ctrls[name],
        keyboardType: isNum ? const TextInputType.numberWithOptions(decimal: true) : TextInputType.text,
        maxLines: t == 'text' ? 3 : 1,
        decoration: _dec('${f['label']}'),
      ),
    );
  }

  Future<void> _save() async {
    final fields = ((_meta?['fields'] as List?) ?? const []).cast<Map>();
    for (final f in fields) {
      final name = '${f['name']}';
      final t = '${f['type']}';
      if (_ctrls.containsKey(name)) {
        final raw = _ctrls[name]!.text.trim();
        if (raw.isEmpty) continue;
        _vals[name] = (t == 'float') ? (double.tryParse(raw) ?? 0)
            : (t == 'integer') ? (int.tryParse(raw) ?? 0) : raw;
      }
    }
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.myCreate(widget.source, _vals);
      if (!mounted) return;
      Navigator.pop(context, true);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('تم إرسال الطلب', 'Request submitted')), backgroundColor: const Color(0xFF16A34A)));
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: const Color(0xFFE11D48)));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: DraggableScrollableSheet(
        expand: false, initialChildSize: 0.6, maxChildSize: 0.92,
        builder: (_, sc) {
          if (_error != null) {
            return Center(child: Padding(padding: const EdgeInsets.all(24), child: Text('$_error')));
          }
          if (_meta == null) {
            return const SizedBox(height: 200, child: Center(child: CircularProgressIndicator()));
          }
          final fields = ((_meta!['fields'] as List?) ?? const []).cast<Map>();
          return ListView(controller: sc, padding: const EdgeInsets.fromLTRB(20, 14, 20, 20), children: [
            Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 16),
                decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(4)))),
            Text('${_meta!['title'] ?? tr('طلب جديد', 'New request')}',
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: _MyScreenState._ink)),
            const SizedBox(height: 16),
            for (final f in fields) _field(f),
            const SizedBox(height: 8),
            SizedBox(height: 48, child: FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: widget.accent,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
              onPressed: _busy ? null : _save,
              icon: _busy
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.send_rounded),
              label: Text(tr('إرسال الطلب', 'Submit request'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
            )),
          ]);
        },
      ),
    );
  }
}

/// One self-service request in full detail: its fields, status, a printable
/// report where one exists (leave), and share/print actions.
class _MyRequestSheet extends StatefulWidget {
  final String source;
  final int id;
  final Color accent;
  const _MyRequestSheet({required this.source, required this.id, required this.accent});
  @override
  State<_MyRequestSheet> createState() => _MyRequestSheetState();
}

class _MyRequestSheetState extends State<_MyRequestSheet> {
  Map<String, dynamic>? _d;
  String? _error;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.myDetail(widget.source, widget.id);
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      initialChildSize: 0.7, minChildSize: 0.4, maxChildSize: 0.95, expand: false,
      builder: (context, sc) {
        if (_error != null) {
          return Center(child: Padding(padding: const EdgeInsets.all(24),
              child: Text(_error!, textAlign: TextAlign.center, style: const TextStyle(color: Color(0xFF64748B)))));
        }
        if (_d == null) return const Center(child: CircularProgressIndicator());
        final d = _d!;
        final fields = ((d['fields'] as List?) ?? const []).cast<Map>();
        final reportPath = d['report_path'];
        return ListView(controller: sc, padding: EdgeInsets.zero, children: [
          Container(
            padding: const EdgeInsets.fromLTRB(20, 18, 20, 18),
            decoration: BoxDecoration(
              gradient: LinearGradient(colors: [widget.accent, widget.accent.withValues(alpha: 0.78)],
                  begin: Alignment.topRight, end: Alignment.bottomLeft),
              borderRadius: const BorderRadius.vertical(top: Radius.circular(22)),
            ),
            child: Row(children: [
              Text('${d['icon'] ?? ''}', style: const TextStyle(fontSize: 26)),
              const SizedBox(width: 10),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(gLang == 'en' ? '${d['en'] ?? ''}' : '${d['ar'] ?? ''}',
                    style: const TextStyle(color: Colors.white70, fontSize: 12, fontWeight: FontWeight.w700)),
                Text('${d['title'] ?? ''}', maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16)),
              ])),
              if (d['state'] != null)
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                  decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(9)),
                  child: Text('${d['state']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 11)),
                ),
            ]),
          ),
          Padding(padding: const EdgeInsets.fromLTRB(18, 12, 18, 6), child: Column(children: [
            for (final f in fields) Padding(
              padding: const EdgeInsets.symmetric(vertical: 7),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                SizedBox(width: 120, child: Text('${f['label']}',
                    style: const TextStyle(color: Color(0xFF64748B), fontSize: 12.5))),
                const SizedBox(width: 8),
                Expanded(child: Text('${f['value']}', textAlign: TextAlign.end,
                    style: const TextStyle(fontWeight: FontWeight.w700, color: Color(0xFF1E293B), fontSize: 13))),
              ]),
            ),
          ])),
          if (reportPath != null) Padding(
            padding: const EdgeInsets.fromLTRB(18, 8, 18, 24),
            child: SizedBox(width: double.infinity, child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(foregroundColor: widget.accent,
                  side: BorderSide(color: widget.accent.withValues(alpha: 0.5)),
                  padding: const EdgeInsets.symmetric(vertical: 12)),
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
                  path: '$reportPath', title: tr('تقرير الطلب', 'Request report'),
                  fileName: '${widget.source}-${widget.id}.pdf'))),
              icon: const Icon(Icons.print_rounded, size: 18),
              label: Text(tr('طباعة / مشاركة التقرير', 'Print / share report'),
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
            )),
          )
          else const SizedBox(height: 20),
        ]);
      },
    );
  }
}
