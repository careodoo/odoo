import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'employee_profile_screen.dart';
import 'in_app_map_screen.dart';
import '../core/widgets.dart';
import '../core/record_report.dart';
import 'media_viewer_screen.dart';
import 'presence_scan_screen.dart';

class WorkOrderDetailScreen extends StatefulWidget {
  const WorkOrderDetailScreen({super.key, required this.id, required this.title});
  final int id;
  final String title;
  @override
  State<WorkOrderDetailScreen> createState() => _WorkOrderDetailScreenState();
}

class _WorkOrderDetailScreenState extends State<WorkOrderDetailScreen> with WidgetsBindingObserver {
  Map<String, dynamic>? _d;
  bool _loading = true;
  Timer? _timer;
  Duration _remaining = Duration.zero;
  final ImagePicker _picker = ImagePicker();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _load();
    // Android may destroy the app while the camera is in front of it (low
    // memory). On the way back Flutter relaunches at the home screen and the
    // capture would be lost — recover it here and upload it anyway.
    _recoverLostCapture();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _recoverLostCapture();
  }

  Future<void> _recoverLostCapture() async {
    try {
      final lost = await _picker.retrieveLostData();
      if (lost.isEmpty || lost.file == null) return;
      final f = lost.file!;
      final bytes = await f.readAsBytes();
      if (!mounted) return;
      final isVideo = lost.type == RetrieveType.video;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('جارٍ رفع الصورة المستعادة…', 'Uploading recovered capture…'))));
      await context.read<AuthProvider>().api
          .workOrderPhoto(widget.id, base64Encode(bytes), f.name, isVideo ? 'video' : 'photo');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تم الرفع للاعتماد', 'Uploaded for approval'))));
        _load();
      }
    } catch (_) {
      // nothing to recover — ignore
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final d = await context.read<AuthProvider>().api.workOrderDetail(widget.id);
      if (!mounted) return;
      setState(() { _d = d; _loading = false; });
      _setupTimer();
    } catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    }
  }

  void _setupTimer() {
    _timer?.cancel();
    if (_d?['state'] == 'in_progress' && _d?['start_datetime'] != null) {
      final start = DateTime.tryParse('${_d!['start_datetime']}Z')?.toLocal();
      final expected = (_d!['expected_minutes'] as int? ?? 0);
      // the SLA deadline is a hard target — the remaining time is the sooner of
      // (start + expected minutes) and the deadline.
      final deadline = _d!['deadline'] != null
          ? DateTime.tryParse('${_d!['deadline']}Z')?.toLocal()
          : null;
      if (start != null && (expected > 0 || deadline != null)) {
        void tick() {
          final now = DateTime.now();
          DateTime? target;
          if (expected > 0) target = start.add(Duration(minutes: expected));
          if (deadline != null && (target == null || deadline.isBefore(target))) {
            target = deadline;
          }
          setState(() => _remaining = target!.difference(now));
        }
        tick();
        _timer = Timer.periodic(const Duration(seconds: 1), (_) => tick());
      }
    }
  }

  Future<void> _act(Future<dynamic> Function() f, String ok) async {
    try {
      await f();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ok)));
        _load();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  void _openMap() {
    // Show the map inside the app; the map screen itself offers a hand-off to
    // the device's maps app for turn-by-turn directions.
    Navigator.push(context, MaterialPageRoute(builder: (_) => InAppMapScreen(
      query: '${_d?['map_query'] ?? widget.title}',
      title: tr('موقع المهمة', 'Task location'),
    )));
  }

  @override
  Widget build(BuildContext context) {
    final api = context.read<AuthProvider>().api;
    final p = context.read<AuthProvider>().profile!;
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: Text(tr('تفاصيل المهمة', 'Task details')), actions: [
        ReportButton(
            code: 'workorder',
            id: widget.id,
            title: tr('تقرير أمر العمل', 'Work order report'),
            compact: true),
        IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
      ]),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _d == null
              ? const Center(child: Text('تعذّر التحميل'))
              : ListView(padding: const EdgeInsets.all(16), children: [
                  _header(cs),
                  if (_d!['state'] == 'in_progress') _timerCard(),
                  if (_d!['state'] == 'done' || _d!['state'] == 'verified') ...[
                    const SizedBox(height: 12), _completionCard(),
                  ],
                  const SizedBox(height: 12),
                  if (_d!['instructions'] != null) ...[_instructionsCard(cs), const SizedBox(height: 12)],
                  if (((_d!['brief_media'] as List?) ?? const []).isNotEmpty) ...[_briefMediaCard(), const SizedBox(height: 12)],
                  _infoCard(cs),
                  const SizedBox(height: 12),
                  _actions(api, p),
                  const SizedBox(height: 16),
                  _resultCard(cs),
                  _historyCard(cs),
                ]),
    );
  }

  Widget _header(ColorScheme cs) {
    final st = _d!['state'] as String;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(gradient: LinearGradient(colors: [cs.primary, cs.primary.withValues(alpha: 0.7)]), borderRadius: BorderRadius.circular(16)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${_d!['name']}', style: const TextStyle(color: Colors.white70, fontSize: 12)),
        Text('${_d!['title']}', style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900)),
        const SizedBox(height: 6),
        Wrap(spacing: 6, children: [
          _chip(woStateLabel(st), kWoStateColor[st] ?? Colors.white24),
          _chip('${_d!['service']}', Colors.white24),
        ]),
      ]),
    );
  }

  Widget _chip(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(20)),
        child: Text(t, style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w700)),
      );

  /// When a task is finished, show how it landed against its SLA — early / on
  /// time / late — with the actual duration and the executor (tap → profile).
  Widget _completionCard() {
    DateTime? p(String? v) => v == null ? null : DateTime.tryParse('$v'.replaceFirst(' ', 'T'));
    final done = p(_d!['done_datetime'] as String?);
    final deadline = p(_d!['deadline'] as String?);
    final start = p(_d!['start_datetime'] as String?);
    final reqd = p(_d!['request_datetime'] as String?);
    // achievement vs deadline
    String verdict; Color vc; IconData vi;
    if (done != null && deadline != null) {
      final diff = deadline.difference(done); // +ve = before deadline
      if (diff.inMinutes >= 0) {
        verdict = diff.inHours >= 1
            ? tr('قبل الموعد بـ ${diff.inHours} س ${diff.inMinutes % 60} د', '${diff.inHours}h ${diff.inMinutes % 60}m early')
            : tr('قبل الموعد بـ ${diff.inMinutes} د', '${diff.inMinutes}m early');
        vc = const Color(0xFF16A34A); vi = Icons.verified_rounded;
      } else {
        final late = diff.abs();
        verdict = late.inHours >= 1
            ? tr('متأخر ${late.inHours} س ${late.inMinutes % 60} د', '${late.inHours}h ${late.inMinutes % 60}m late')
            : tr('متأخر ${late.inMinutes} د', '${late.inMinutes}m late');
        vc = const Color(0xFFE5484D); vi = Icons.running_with_errors_rounded;
      }
    } else {
      verdict = tr('أُنجزت', 'Completed'); vc = const Color(0xFF16A34A); vi = Icons.check_circle_rounded;
    }
    // actual duration
    final durMin = (_d!['duration_minutes'] ?? 0) is num ? (_d!['duration_minutes'] as num).toInt() : 0;
    final dur = durMin > 0
        ? (durMin >= 60 ? tr('${durMin ~/ 60} س ${durMin % 60} د', '${durMin ~/ 60}h ${durMin % 60}m') : tr('$durMin د', '${durMin}m'))
        : (start != null && done != null ? tr('${done.difference(start).inMinutes} د', '${done.difference(start).inMinutes}m') : '—');
    final empId = _d!['employee_id'];
    return Container(
      padding: const EdgeInsets.all(15),
      decoration: BoxDecoration(
        color: Colors.white, borderRadius: BorderRadius.circular(16),
        border: Border.all(color: vc.withValues(alpha: 0.3)),
        boxShadow: [BoxShadow(color: vc.withValues(alpha: 0.12), blurRadius: 10, offset: const Offset(0, 5))],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(vi, color: vc, size: 22),
          const SizedBox(width: 8),
          Expanded(child: Text(tr('نتيجة الإنجاز', 'Completion result'),
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15))),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(color: vc, borderRadius: BorderRadius.circular(20)),
            child: Text(verdict, style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w900)),
          ),
        ]),
        const SizedBox(height: 12),
        Row(children: [
          _cStat(Icons.timer_outlined, tr('مدة التنفيذ', 'Duration'), dur, const Color(0xFF0891B2)),
          _cStat(Icons.flag_rounded, tr('الموعد', 'Deadline'),
              deadline != null ? '${deadline.toLocal()}'.substring(5, 16) : '—', const Color(0xFF8B5CF6)),
          _cStat(Icons.task_alt_rounded, tr('الإنجاز', 'Done at'),
              done != null ? '${done.toLocal()}'.substring(5, 16) : '—', const Color(0xFF16A34A)),
        ]),
        if (reqd != null && done != null) ...[
          const SizedBox(height: 8),
          Text(tr('من الطلب للإنجاز: ${done.difference(reqd).inHours} ساعة',
                  'Request → done: ${done.difference(reqd).inHours}h'),
              style: TextStyle(fontSize: 11, color: Colors.grey.shade600, fontWeight: FontWeight.w600)),
        ],
        if (_d!['employee'] != null) ...[
          const Divider(height: 20),
          InkWell(
            onTap: empId == null ? null : () => Navigator.push(context, MaterialPageRoute(
                builder: (_) => EmployeeProfileScreen(employeeId: empId as int, name: '${_d!['employee']}'))),
            borderRadius: BorderRadius.circular(10),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(children: [
                CircleAvatar(radius: 16, backgroundColor: vc.withValues(alpha: 0.12),
                    child: Text('${_d!['employee']}'.characters.first,
                        style: TextStyle(color: vc, fontWeight: FontWeight.w900, fontSize: 13))),
                const SizedBox(width: 9),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(tr('المنفّذ', 'Executed by'),
                      style: TextStyle(fontSize: 10, color: Colors.grey.shade500, fontWeight: FontWeight.w600)),
                  Text('${_d!['employee']}',
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: Color(0xFF0E3A5F))),
                ])),
                if (empId != null) const Icon(Icons.chevron_left_rounded, color: Colors.grey),
              ]),
            ),
          ),
        ],
      ]),
    );
  }

  Widget _cStat(IconData ic, String label, String v, Color c) => Expanded(
        child: Column(children: [
          Icon(ic, size: 15, color: c),
          const SizedBox(height: 3),
          Text(v, maxLines: 1, overflow: TextOverflow.ellipsis, textAlign: TextAlign.center,
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12)),
          Text(label, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 8.5, color: Colors.grey.shade500, fontWeight: FontWeight.w700)),
        ]),
      );

  Widget _timerCard() {
    final over = _remaining.isNegative;
    final dur = _remaining.abs();
    final t = '${dur.inHours.toString().padLeft(2, '0')}:${(dur.inMinutes % 60).toString().padLeft(2, '0')}:${(dur.inSeconds % 60).toString().padLeft(2, '0')}';
    final c = over ? const Color(0xFFE5484D) : const Color(0xFF16A34A);
    return Container(
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: c.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(14), border: Border.all(color: c)),
      child: Row(children: [
        Icon(over ? Icons.timer_off : Icons.timer, color: c, size: 34),
        const SizedBox(width: 14),
        Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(over ? 'تجاوز الوقت المحدّد' : 'الوقت المتبقّي', style: TextStyle(color: c, fontWeight: FontWeight.w700)),
          Text(t, style: TextStyle(color: c, fontSize: 30, fontWeight: FontWeight.w900, fontFeatures: const [])),
        ]),
        const Spacer(),
        Text('المحدّد: ${_d!['expected_minutes']} د', style: TextStyle(color: Theme.of(context).colorScheme.outline)),
      ]),
    );
  }

  Widget _infoCard(ColorScheme cs) => Card(
        child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          _locationBlock(cs),
          _row(Icons.person, 'المُسنَد إليه', '${_d!['assignee'] ?? '—'}'),
          _row(Icons.flag, tr('الأولوية', 'Priority'), '${_d!['priority']}'),
          _row(Icons.schedule, tr('الموعد', 'Due'), '${_d!['deadline'] ?? '—'}'),
          if (_d!['description'] != null) ...[
            const Divider(),
            Text(tr('الوصف', 'Description'), style: TextStyle(color: cs.outline, fontSize: 12)),
            Text('${_d!['description']}'),
          ],
          const SizedBox(height: 10),
          OutlinedButton.icon(onPressed: _openMap, icon: const Icon(Icons.directions), label: Text(tr('توجّه إلى الموقع (خريطة)', 'Navigate (map)'))),
        ])),
      );

  // Detailed location: facility → building → floor → location (+ QR code)
  Widget _locationBlock(ColorScheme cs) {
    final loc = _d!['location_detail'] as Map?;
    if (loc == null) {
      return _row(Icons.location_on, tr('الموقع', 'Location'),
          '${_d!['facility']}${_d!['location'] != null ? ' — ${_d!['location']}' : ''}');
    }
    Widget seg(IconData i, String label, String? v) => (v == null || v.isEmpty)
        ? const SizedBox.shrink()
        : Padding(padding: const EdgeInsets.symmetric(vertical: 3), child: Row(children: [
            Icon(i, size: 16, color: cs.outline),
            const SizedBox(width: 8),
            SizedBox(width: 66, child: Text(label, style: TextStyle(color: cs.outline, fontSize: 12.5))),
            Expanded(child: Text(v, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5))),
          ]));
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: const Color(0xFF0B6EA8).withValues(alpha: 0.06), borderRadius: BorderRadius.circular(12)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.location_on, size: 18, color: Color(0xFF0B6EA8)),
          const SizedBox(width: 6),
          Text(tr('تفاصيل الموقع', 'Location details'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5)),
        ]),
        const SizedBox(height: 6),
        seg(Icons.location_city, tr('المرفق', 'Facility'), loc['facility'] as String?),
        seg(Icons.apartment, tr('المبنى', 'Building'), loc['building'] as String?),
        seg(Icons.layers, tr('الدور', 'Floor'), loc['floor'] as String?),
        seg(Icons.meeting_room, tr('الموقع', 'Location'), loc['name'] as String?),
        seg(Icons.qr_code, tr('رمز QR', 'QR code'), loc['code'] as String?),
      ]),
    );
  }

  Widget _row(IconData i, String l, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(children: [
          Icon(i, size: 18, color: Theme.of(context).colorScheme.outline),
          const SizedBox(width: 8),
          Text('$l: ', style: TextStyle(color: Theme.of(context).colorScheme.outline)),
          Expanded(child: Text(v, style: const TextStyle(fontWeight: FontWeight.w600))),
        ]),
      );

  Widget _actions(dynamic api, dynamic p) {
    final st = _d!['state'] as String;
    final missing = (_d!['proof_missing'] as List?) ?? const [];
    final canSubmit = _d!['can_submit'] == true;
    final canApprove = _d!['can_approve'] == true;
    final children = <Widget>[];
    if (st == 'new' || st == 'assigned') {
      children.add(FilledButton.icon(
        onPressed: _startWithPresence,
        icon: const Icon(Icons.play_arrow), label: Text(tr('بدء التنفيذ', 'Start'))));
    }
    // worker: submit result for approval — only when all required proof is present
    if (st == 'assigned' || st == 'in_progress') {
      if (missing.isNotEmpty) {
        children.add(Container(
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: const Color(0xFFF59E0B).withValues(alpha: 0.12), borderRadius: BorderRadius.circular(12)),
          child: Row(children: [
            const Icon(Icons.info_outline, color: Color(0xFFB45309), size: 20),
            const SizedBox(width: 8),
            Expanded(child: Text('${tr('مطلوب للاعتماد', 'Required to submit')}: ${missing.join('، ')}',
                style: const TextStyle(color: Color(0xFFB45309), fontSize: 12.5, fontWeight: FontWeight.w700))),
          ]),
        ));
      }
      children.add(FilledButton.icon(
        style: FilledButton.styleFrom(backgroundColor: const Color(0xFF16A34A)),
        onPressed: canSubmit ? () => _act(() => api.workOrderDone(widget.id), tr('تم الإرسال للاعتماد', 'Sent for approval')) : null,
        icon: const Icon(Icons.check), label: Text(tr('إتمام وإرسال للاعتماد', 'Complete & submit'))));
    }
    // supervisor: approve or return the result
    if (canApprove) {
      children.add(Row(children: [
        Expanded(child: FilledButton.icon(
          style: FilledButton.styleFrom(backgroundColor: const Color(0xFF0B6EA8)),
          onPressed: () => _act(() => api.workOrderVerify(widget.id), tr('تم الاعتماد والإغلاق', 'Approved and closed')),
          icon: const Icon(Icons.verified), label: Text(tr('اعتماد', 'Approve')))),
        const SizedBox(width: 8),
        Expanded(child: OutlinedButton.icon(
          style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFE5484D)),
          onPressed: _reject,
          icon: const Icon(Icons.undo), label: Text(tr('إرجاع', 'Return')))),
      ]));
    }
    // presence + evidence capture (worker)
    if (st == 'assigned' || st == 'in_progress') {
      children.add(Row(children: [
        Expanded(child: OutlinedButton.icon(onPressed: () => _capture(false),
            icon: const Icon(Icons.photo_camera), label: Text(tr('صورة', 'Photo')))),
        const SizedBox(width: 8),
        Expanded(child: OutlinedButton.icon(onPressed: () => _capture(true),
            icon: const Icon(Icons.videocam), label: Text(tr('فيديو', 'Video')))),
      ]));
    }
    children.add(OutlinedButton.icon(onPressed: _addNote, icon: const Icon(Icons.add_comment), label: Text(tr('إضافة ملاحظة', 'Add note'))));
    return Column(children: [for (final c in children) Padding(padding: const EdgeInsets.only(bottom: 8), child: SizedBox(width: double.infinity, child: c))]);
  }

  /// Presence gate: the worker must scan the location QR before the task starts.
  Future<void> _startWithPresence() async {
    final loc = _d!['location_detail'] as Map?;
    final expectedCode = (loc?['code'] as String?)?.trim();
    final expectedName = loc?['name'] as String?;
    final go = await showDialog<bool>(context: context, builder: (_) => AlertDialog(
      icon: const Icon(Icons.qr_code_scanner, color: Color(0xFF0B6EA8), size: 36),
      title: Text(tr('إثبات الحضور', 'Prove presence')),
      content: Text(
          tr('قبل بدء التنفيذ يجب إثبات وجودك بالموقع عبر مسح رمز QR الخاص به${expectedName != null ? '\n📍 $expectedName' : ''}',
             'Scan the location QR to prove you are on site${expectedName != null ? '\n📍 $expectedName' : ''}')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton.icon(onPressed: () => Navigator.pop(context, true),
            icon: const Icon(Icons.qr_code_scanner), label: Text(tr('امسح الآن', 'Scan now'))),
      ],
    ));
    if (go != true || !mounted) return;
    final code = await Navigator.push<String>(context,
        MaterialPageRoute(builder: (_) => PresenceScanScreen(expectedName: expectedName)));
    if (code == null || !mounted) return;
    // if the WO has a registered location code, it must match the scanned one
    if (expectedCode != null && expectedCode.isNotEmpty && code.trim() != expectedCode) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          backgroundColor: const Color(0xFFE5484D),
          content: Text(tr('الرمز الممسوح لا يطابق موقع المهمة — لم يُثبت الحضور',
              'Scanned code does not match the task location'))));
      return;
    }
    final api = context.read<AuthProvider>().api;
    try {
      await api.scan(code); // log the presence scan at the location
    } catch (_) {/* the start action also logs a tied scan */}
    await _act(() => api.workOrderStart(widget.id), tr('تم إثبات الحضور — بدأ التنفيذ والعدّاد يعمل', 'Presence confirmed — work started, timer running'));
  }

  Future<void> _reject() async {
    final ctrl = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (_) => AlertDialog(
      title: Text(tr('إرجاع المهمة', 'Return task')),
      content: TextField(controller: ctrl, maxLines: 3,
          decoration: InputDecoration(hintText: tr('سبب الإرجاع (يظهر للعامل)…', 'Reason (shown to the worker)…'))),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE5484D)),
          onPressed: () => Navigator.pop(context, true), child: Text(tr('إرجاع', 'Return'))),
      ],
    ));
    if (ok == true) {
      _act(() => context.read<AuthProvider>().api.workOrderReject(widget.id, ctrl.text.trim()), tr('أُرجعت المهمة للعامل', 'Task returned to the worker'));
    }
  }

  Future<void> _capture(bool video) async {
    final api = context.read<AuthProvider>().api;
    try {
      final XFile? x = video
          ? await _picker.pickVideo(source: ImageSource.camera, maxDuration: const Duration(seconds: 60))
          : await _picker.pickImage(source: ImageSource.camera, imageQuality: 70, maxWidth: 1600);
      if (x == null) return;
      final bytes = await x.readAsBytes();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('جارٍ الرفع…', 'Uploading…'))));
      await api.workOrderPhoto(widget.id, base64Encode(bytes), x.name, video ? 'video' : 'photo');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تم الرفع للاعتماد', 'Uploaded for approval'))));
        _load();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  Future<void> _addNote() async {
    final ctrl = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (_) => AlertDialog(
      title: Text(tr('إضافة ملاحظة', 'Add note')),
      content: TextField(controller: ctrl, maxLines: 3, decoration: const InputDecoration(hintText: 'اكتب ملاحظة...')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('إلغاء')),
        FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(tr('إرسال', 'Send'))),
      ],
    ));
    if (ok == true && ctrl.text.trim().isNotEmpty) {
      _act(() => context.read<AuthProvider>().api.workOrderNote(widget.id, ctrl.text.trim()), tr('أُضيفت الملاحظة', 'Note added'));
    }
  }

  Widget _instructionsCard(ColorScheme cs) => Card(
        color: const Color(0xFF0B6EA8).withValues(alpha: 0.06),
        child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.assignment_turned_in, color: Color(0xFF0B6EA8), size: 20),
            const SizedBox(width: 8),
            Text(tr('المطلوب تنفيذه', 'What to do'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
          ]),
          const SizedBox(height: 8),
          Text('${_d!['instructions']}', style: const TextStyle(fontSize: 14.5, height: 1.4)),
        ])),
      );

  // النتيجة — presence status + the photos/videos/description the worker submits
  Widget _resultCard(ColorScheme cs) {
    final result = (_d!['result'] as Map?) ?? const {};
    final proof = (_d!['proof'] as Map?) ?? const {};
    final photos = ((result['photos'] as List?) ?? const []).map((e) => e as Map).toList();
    final videos = ((result['videos'] as List?) ?? const []).map((e) => e as Map).toList();
    final all = [...photos, ...videos];
    final presenceOk = _d!['presence_verified'] == true;
    final rc = (_d!['rejection_count'] ?? 0) as int;
    return Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        const Icon(Icons.fact_check, color: Color(0xFF16A34A), size: 20),
        const SizedBox(width: 8),
        Text(tr('النتيجة', 'Result'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
        const Spacer(),
        if (rc > 0) Container(
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(color: const Color(0xFFE5484D).withValues(alpha: 0.15), borderRadius: BorderRadius.circular(12)),
          child: Text('${tr('أُرجعت', 'Returned')} ×$rc', style: const TextStyle(color: Color(0xFFE5484D), fontSize: 11, fontWeight: FontWeight.w800)),
        ),
      ]),
      const SizedBox(height: 10),
      if (proof['presence'] == true)
        _proofRow(Icons.qr_code_scanner, tr('إثبات الحضور (QR)', 'Presence (QR)'), presenceOk),
      if (proof['photo'] == true)
        _proofRow(Icons.photo_camera, tr('صورة', 'Photo'), photos.isNotEmpty),
      if (proof['video'] == true)
        _proofRow(Icons.videocam, tr('فيديو', 'Video'), videos.isNotEmpty),
      if (result['description'] != null) ...[
        const Divider(height: 18),
        Text('${result['description']}', style: const TextStyle(fontSize: 14)),
      ],
      if (all.isNotEmpty) ...[
        const SizedBox(height: 10),
        SizedBox(height: 90, child: _mediaStrip(all)),
      ] else Padding(padding: const EdgeInsets.only(top: 8), child: Text(
          tr('لم يُرفع دليل بعد.', 'No evidence uploaded yet.'), style: TextStyle(color: cs.outline, fontSize: 12.5))),
    ])));
  }

  Widget _proofRow(IconData i, String label, bool ok) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(children: [
          Icon(i, size: 17, color: Theme.of(context).colorScheme.outline),
          const SizedBox(width: 8),
          Expanded(child: Text(label, style: const TextStyle(fontSize: 13.5))),
          Icon(ok ? Icons.check_circle : Icons.cancel, size: 18, color: ok ? const Color(0xFF16A34A) : const Color(0xFFE5484D)),
        ]),
      );

  /// Photos/videos the client, quality inspector or supervisor attached — the
  /// visual brief of what is being asked for.
  Widget _briefMediaCard() {
    final brief = ((_d!['brief_media'] as List?) ?? const []).cast<Map>();
    return Card(
      color: const Color(0xFF0EA5A4).withValues(alpha: 0.06),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.photo_library_rounded, color: Color(0xFF0EA5A4), size: 20),
            const SizedBox(width: 8),
            Expanded(child: Text(tr('صور المطلوب (من العميل/الجودة)', 'Reference photos (client / quality)'),
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5))),
            Text('${brief.length}', style: const TextStyle(color: Color(0xFF0EA5A4), fontWeight: FontWeight.w900)),
          ]),
          const SizedBox(height: 10),
          SizedBox(height: 90, child: _mediaStrip(brief)),
        ]),
      ),
    );
  }

  Widget _mediaStrip(List<Map> media) => Builder(builder: (ctx) => ListView(scrollDirection: Axis.horizontal, children: [
        for (int i = 0; i < media.length; i++)
          Padding(padding: const EdgeInsets.only(left: 8), child: GestureDetector(
            onTap: () async {
              final tok = await ctx.read<AuthProvider>().api.token;
              if (!ctx.mounted) return;
              Navigator.push(ctx, MaterialPageRoute(
                  builder: (_) => MediaViewerScreen(media: media, index: i, token: tok)));
            },
            child: ClipRRect(borderRadius: BorderRadius.circular(10), child: Stack(children: [
              Image.network('${media[i]['thumb']}', width: 90, height: 90, fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => Container(width: 90, height: 90, color: const Color(0xFFEEF2F7), child: const Icon(Icons.play_circle))),
              if (media[i]['is_video'] == true || '${media[i]['type'] ?? ''}'.toLowerCase().contains('video'))
                const Positioned.fill(child: Center(child: Icon(Icons.play_circle_fill, color: Colors.white70, size: 34))),
            ])),
          )),
      ]));

  Widget _historyCard(ColorScheme cs) {
    final hist = (_d!['history'] as List).where((h) => (h as Map)['body'] != null && '${h['body']}'.trim().isNotEmpty).toList();
    return Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(tr('السجل (History)', 'History'), style: TextStyle(fontWeight: FontWeight.w800)),
      const SizedBox(height: 8),
      if (hist.isEmpty) Text(tr('لا سجل بعد', 'No history yet'), style: TextStyle(color: cs.outline)),
      for (final h in hist)
        Padding(padding: const EdgeInsets.symmetric(vertical: 6), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Icon(Icons.circle, size: 8, color: Color(0xFF0B6EA8)),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${(h as Map)['body']}'),
            Text('${h['author']} · ${'${h['date'] ?? ''}'.replaceAll('T', ' ').substring(0, ('${h['date']}').length.clamp(0, 16))}', style: TextStyle(color: cs.outline, fontSize: 11)),
          ])),
        ])),
    ])));
  }
}
