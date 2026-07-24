import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';
import 'package:url_launcher/url_launcher.dart';
import 'dart:convert';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/api_client.dart';
import '../core/i18n.dart';

/// Security incidents: list recent + report a new one. Writes straight into
/// Security Manager (security.incident.report) via /api/v1/security/incidents.
class SecurityIncidentsScreen extends StatefulWidget {
  const SecurityIncidentsScreen({super.key});
  @override
  State<SecurityIncidentsScreen> createState() => _SecurityIncidentsScreenState();
}

class _SecurityIncidentsScreenState extends State<SecurityIncidentsScreen> {
  late Future<List<dynamic>> _future;

  static const types = {
    'theft': 'سرقة/سطو', 'vandalism': 'تخريب', 'trespassing': 'تسلّل',
    'assault': 'اعتداء', 'fire': 'حريق', 'medical': 'طارئ طبي',
    'suspicious': 'نشاط مشبوه', 'other': 'أخرى',
  };
  static const severities = {'low': 'منخفض', 'medium': 'متوسط', 'high': 'عالٍ', 'critical': 'حرج'};

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _future = context.read<AuthProvider>().api.securityList('incidents');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0B1220),
      appBar: AppBar(title: Text(tr('البلاغات الأمنية', 'Incidents'))),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openForm,
        icon: const Icon(Icons.add_alert),
        label: Text(tr('تسجيل حادث', 'Report incident')),
        backgroundColor: const Color(0xFFE5484D),
      ),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<List<dynamic>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return _msg('خطأ: ${snap.error}');
            }
            final items = snap.data ?? const [];
            if (items.isEmpty) return _msg(tr('لا بلاغات مسجّلة.', 'No incidents.'));
            return ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: items.length,
              itemBuilder: (_, i) => _card(items[i] as Map),
            );
          },
        ),
      ),
    );
  }

  Widget _msg(String t) => ListView(children: [
        const SizedBox(height: 120),
        Center(child: Text(t, style: const TextStyle(color: Color(0xFF9CB2CD)))),
      ]);

  Color _sevColor(String s) => switch (s) {
        'critical' => const Color(0xFFE5484D),
        'high' => const Color(0xFFF2603F),
        'medium' => const Color(0xFFF7A23B),
        _ => const Color(0xFF37C98A),
      };

  Widget _card(Map i) {
    return Card(
      color: const Color(0xFF152238),
      child: ListTile(
        onTap: () => _openIncident(i),
        leading: CircleAvatar(
          backgroundColor: _sevColor(i['severity'] as String? ?? 'low'),
          child: const Icon(Icons.warning_amber, color: Colors.white, size: 20),
        ),
        title: Text('${i['name']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
        subtitle: Text(
          '${types[i['type']] ?? i['type']} · ${severities[i['severity']] ?? i['severity']}\n${i['description'] ?? ''}',
          style: const TextStyle(color: Color(0xFF9CB2CD)),
        ),
        trailing: const Icon(Icons.chevron_left_rounded, color: Color(0xFF6B7A90)),
        isThreeLine: true,
      ),
    );
  }

  void _openIncident(Map i) {
    showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => _IncidentDetailSheet(id: intOf(i['id']), sevColor: _sevColor),
    ).then((_) => setState(_load));
  }


  void _openForm() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF152238),
      builder: (_) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
        child: _IncidentForm(onSaved: () {
          Navigator.pop(context);
          setState(_load);
        }),
      ),
    );
  }
}

/// Full incident report — mirrors the Security Manager Incident Report: every
/// field, media gallery (photo + video capture), updates log and the workflow
/// transitions (report → investigate → resolve → close) + police notify.
class _IncidentDetailSheet extends StatefulWidget {
  const _IncidentDetailSheet({required this.id, required this.sevColor});
  final int id;
  final Color Function(String) sevColor;
  @override
  State<_IncidentDetailSheet> createState() => _IncidentDetailSheetState();
}

class _IncidentDetailSheetState extends State<_IncidentDetailSheet> {
  Map<String, dynamic>? _d;
  bool _busy = false;

  static const _navy = Color(0xFF0F1B2E);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);

  // workflow transitions available per state
  static const _flow = {
    'draft': [('report', 'إبلاغ رسمي', 'Report', Color(0xFF2563EB))],
    'reported': [('investigate', 'بدء التحقيق', 'Investigate', Color(0xFF0EA5E9))],
    'investigating': [('resolve', 'حل البلاغ', 'Resolve', Color(0xFF16A34A))],
    'resolved': [('close', 'إغلاق', 'Close', Color(0xFF64748B))],
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.incidentDetail(widget.id);
      if (mounted) setState(() => _d = d);
    } catch (_) {}
  }

  ApiClient get _api => context.read<AuthProvider>().api;

  void _snack(String m, [Color? c]) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: c, behavior: SnackBarBehavior.floating));

  Future<void> _addMedia(String kind) async {
    try {
      final picker = ImagePicker();
      final XFile? x = kind == 'video'
          ? await picker.pickVideo(source: ImageSource.camera, maxDuration: const Duration(seconds: 60))
          : await picker.pickImage(source: ImageSource.camera, maxWidth: 1600, imageQuality: 70);
      if (x == null) return;
      setState(() => _busy = true);
      final bytes = await x.readAsBytes();
      await _api.incidentMedia(widget.id, {'kind': kind, 'file': base64Encode(bytes), 'filename': x.name});
      await _load();
      if (mounted) _snack(kind == 'video' ? tr('أُضيف الفيديو', 'Video attached') : tr('أُضيفت الصورة', 'Photo attached'), const Color(0xFF16A34A));
    } catch (e) {
      if (mounted) _snack('$e', const Color(0xFFE11D48));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _pickFromGallery() async {
    try {
      final x = await ImagePicker().pickImage(source: ImageSource.gallery, maxWidth: 1600, imageQuality: 75);
      if (x == null) return;
      setState(() => _busy = true);
      final bytes = await x.readAsBytes();
      await _api.incidentMedia(widget.id, {'kind': 'photo', 'file': base64Encode(bytes), 'filename': x.name});
      await _load();
      if (mounted) _snack(tr('أُضيفت الصورة', 'Photo attached'), const Color(0xFF16A34A));
    } catch (e) {
      if (mounted) _snack('$e', const Color(0xFFE11D48));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _captureLocation() async {
    try {
      if (await Geolocator.checkPermission() == LocationPermission.denied) {
        await Geolocator.requestPermission();
      }
      final pos = await Geolocator.getCurrentPosition();
      await _api.incidentLocate(widget.id, pos.latitude, pos.longitude);
      await _load();
      if (mounted) _snack(tr('سُجّل الموقع', 'Location captured'), const Color(0xFF16A34A));
    } catch (e) {
      if (mounted) _snack('$e', const Color(0xFFE11D48));
    }
  }

  Future<void> _addUpdate() async {
    final ctrl = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      title: Text(tr('إضافة تحديث', 'Add update')),
      content: TextField(controller: ctrl, maxLines: 3, autofocus: true,
          decoration: InputDecoration(hintText: tr('ما الذي حدث بعد ذلك؟', 'What happened next?'), border: const OutlineInputBorder())),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(onPressed: () => Navigator.pop(c, true), child: Text(tr('إضافة', 'Add'))),
      ]));
    if (ok != true || ctrl.text.trim().isEmpty) return;
    try {
      await _api.incidentUpdate(widget.id, ctrl.text.trim());
      await _load();
      if (mounted) _snack(tr('أُضيف التحديث', 'Update added'), const Color(0xFF16A34A));
    } catch (e) {
      if (mounted) _snack('$e', const Color(0xFFE11D48));
    }
  }

  Future<void> _runAction(String key, {Map<String, dynamic>? extra}) async {
    setState(() => _busy = true);
    try {
      await _api.incidentAction(widget.id, key, extra: extra);
      await _load();
      if (mounted) _snack(tr('تم تنفيذ الإجراء', 'Action done'), const Color(0xFF16A34A));
    } catch (e) {
      if (mounted) _snack('$e', const Color(0xFFE11D48));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _resolveWithNotes() async {
    final ctrl = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      title: Text(tr('حل البلاغ', 'Resolve incident')),
      content: TextField(controller: ctrl, maxLines: 3, autofocus: true,
          decoration: InputDecoration(labelText: tr('ملاحظات الحل', 'Resolution notes'), border: const OutlineInputBorder())),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFF16A34A)),
            onPressed: () => Navigator.pop(c, true), child: Text(tr('حل', 'Resolve'))),
      ]));
    if (ok != true) return;
    await _runAction('resolve', extra: {'resolution_notes': ctrl.text.trim()});
  }

  Future<void> _notifyPolice() async {
    final ctrl = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      title: Text(tr('إبلاغ الشرطة', 'Notify police')),
      content: TextField(controller: ctrl,
          decoration: InputDecoration(labelText: tr('رقم بلاغ الشرطة (اختياري)', 'Police report # (optional)'), border: const OutlineInputBorder())),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(onPressed: () => Navigator.pop(c, true), child: Text(tr('تأكيد', 'Confirm'))),
      ]));
    if (ok != true) return;
    await _runAction('police', extra: {'police_report_number': ctrl.text.trim()});
  }

  Future<void> _escalate() async {
    setState(() => _busy = true);
    try {
      final r = await _api.incidentToWorkorder(widget.id);
      await _load();
      if (mounted) _snack('${tr('أُنشئ أمر العمل', 'Work order raised')}: ${r['workorder']}', const Color(0xFF16A34A));
    } catch (e) {
      if (mounted) _snack('$e', const Color(0xFFE11D48));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _openMedia(Map m) async {
    final url = await _api.incidentMediaUrl(intOf(m['id']));
    if (!mounted) return;
    if ('${m['kind']}' == 'video') {
      await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
    } else {
      showDialog(context: context, builder: (_) => Dialog(
        backgroundColor: Colors.black,
        child: InteractiveViewer(child: Image.network(url, fit: BoxFit.contain,
            errorBuilder: (_, __, ___) => const Padding(padding: EdgeInsets.all(40), child: Icon(Icons.broken_image, color: Colors.white54, size: 60)))),
      ));
    }
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final types = _SecurityIncidentsScreenState.types;
    final sevs = _SecurityIncidentsScreenState.severities;
    final sev = '${d?['severity'] ?? 'low'}';
    final sc = widget.sevColor(sev);
    final flow = _flow['${d?['state'] ?? ''}'] ?? const [];
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.75, minChildSize: 0.4, maxChildSize: 0.96,
      builder: (_, sController) => Container(
        decoration: const BoxDecoration(color: _navy, borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        clipBehavior: Clip.antiAlias,
        child: d == null
            ? const SizedBox(height: 300, child: Center(child: CircularProgressIndicator()))
            : Stack(children: [
                Column(children: [
                  // header
                  Container(
                    padding: const EdgeInsets.fromLTRB(20, 14, 20, 16),
                    decoration: BoxDecoration(gradient: LinearGradient(
                        colors: [sc, Color.lerp(sc, Colors.black, 0.45)!], begin: Alignment.topRight, end: Alignment.bottomLeft)),
                    child: Column(children: [
                      Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12),
                          decoration: BoxDecoration(color: Colors.white38, borderRadius: BorderRadius.circular(3)))),
                      Row(children: [
                        const Icon(Icons.warning_amber_rounded, color: Colors.white),
                        const SizedBox(width: 10),
                        Expanded(child: Text('${d['name'] ?? ''}', style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900))),
                        _chip('${d['state_label'] ?? d['state'] ?? ''}', Colors.white24),
                      ]),
                      const SizedBox(height: 8),
                      Row(children: [
                        _chip('${types[d['type']] ?? d['type_label'] ?? d['type'] ?? ''}', Colors.white24),
                        const SizedBox(width: 6),
                        _chip('${tr('الخطورة', 'Severity')}: ${sevs[sev] ?? d['severity_label'] ?? sev}', Colors.white24),
                      ]),
                    ]),
                  ),
                  Expanded(child: ListView(controller: sController, padding: const EdgeInsets.all(16), children: [
                    // evidence + capture
                    Wrap(spacing: 8, runSpacing: 8, children: [
                      _evBtn(Icons.photo_camera_rounded, tr('صورة', 'Photo'), () => _addMedia('photo')),
                      _evBtn(Icons.videocam_rounded, tr('فيديو', 'Video'), () => _addMedia('video')),
                      _evBtn(Icons.photo_library_rounded, tr('من المعرض', 'Gallery'), _pickFromGallery),
                      _evBtn(Icons.my_location_rounded, tr('الموقع', 'Location'), _captureLocation),
                      _evBtn(Icons.note_add_rounded, tr('تحديث', 'Update'), _addUpdate),
                      _evBtn(Icons.build_rounded, tr('أمر عمل', 'Work order'), _escalate),
                    ]),
                    // workflow buttons
                    if (flow.isNotEmpty || d['police_notified'] != true) ...[
                      const SizedBox(height: 12),
                      Wrap(spacing: 8, runSpacing: 8, children: [
                        for (final f in flow)
                          _wfBtn(f.$2, f.$3, f.$4, () => f.$1 == 'resolve' ? _resolveWithNotes() : _runAction(f.$1)),
                        if (d['police_notified'] != true)
                          _wfBtn('إبلاغ الشرطة', 'Notify police', const Color(0xFF7C3AED), _notifyPolice),
                      ]),
                    ],
                    // media gallery
                    if ((d['media'] as List?)?.isNotEmpty ?? false) ...[
                      const SizedBox(height: 16),
                      _sectionTitle('📎', tr('الأدلة والمرفقات', 'Evidence')),
                      SizedBox(height: 92, child: ListView(scrollDirection: Axis.horizontal, children: [
                        for (final m in (d['media'] as List).cast<Map>()) _mediaThumb(m),
                      ])),
                    ],
                    const SizedBox(height: 8),
                    // report details
                    _section(tr('تفاصيل البلاغ', 'Report details'), [
                      ('المُبلِّغ', 'Reporter', d['reporter']),
                      ('التاريخ', 'Date', d['date']),
                      ('الموقع', 'Premise', d['premise']),
                      ('المكان المحدد', 'Location', d['location']),
                      ('الوصف', 'Description', d['description']),
                      ('الإجراء المتخذ', 'Action taken', d['action_taken']),
                      ('الإحداثيات', 'GPS', d['located'] == true ? '${d['lat']}, ${d['lng']}' : null),
                    ]),
                    _section(tr('المستجيبون', 'Responders'), [
                      ('الحارس', 'Guard', d['guard']),
                      ('الفريق', 'Team', d['team']),
                      ('الدورية', 'Patrol', d['patrol']),
                      ('الشهود', 'Witnesses', (d['witnesses'] as List?)?.join('، ')),
                      ('الأطراف', 'Involved', (d['involved'] as List?)?.join('، ')),
                    ]),
                    _section(tr('الشرطة', 'Police'), [
                      ('تم الإبلاغ', 'Notified', d['police_notified'] == true ? tr('نعم', 'Yes') : tr('لا', 'No')),
                      ('رقم البلاغ', 'Report #', d['police_report_number']),
                    ]),
                    _section(tr('الحل والمتابعة', 'Resolution & follow-up'), [
                      ('تاريخ الحل', 'Resolved on', d['resolution_date']),
                      ('ملاحظات الحل', 'Resolution notes', d['resolution_notes']),
                      ('متابعة مطلوبة', 'Follow-up', d['follow_up_required'] == true ? tr('نعم', 'Yes') : null),
                      ('تاريخ المتابعة', 'Follow-up date', d['follow_up_date']),
                      ('ملاحظات المتابعة', 'Follow-up notes', d['follow_up_notes']),
                    ]),
                    if (d['workorder'] != null)
                      _section(tr('أمر العمل', 'Work order'), [('أمر العمل', 'Work order', d['workorder'])]),
                    // updates timeline
                    if ((d['updates'] as List?)?.isNotEmpty ?? false) ...[
                      _sectionTitle('🗒️', tr('سجل التحديثات', 'Updates log')),
                      for (final u in (d['updates'] as List).cast<Map>())
                        Padding(padding: const EdgeInsets.symmetric(vertical: 6),
                            child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              const Padding(padding: EdgeInsets.only(top: 4), child: Icon(Icons.circle, size: 8, color: Color(0xFF0EA5E9))),
                              const SizedBox(width: 10),
                              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                                Text('${u['body']}', style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600)),
                                Text('${u['by'] ?? ''} · ${u['at'] ?? ''}', style: const TextStyle(color: _muted, fontSize: 10.5)),
                              ])),
                            ])),
                    ],
                    const SizedBox(height: 24),
                  ])),
                ]),
                if (_busy) const Positioned.fill(child: ColoredBox(color: Color(0x66000000), child: Center(child: CircularProgressIndicator()))),
              ]),
      ),
    );
  }

  Widget _chip(String t, Color bg) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
        decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(20)),
        child: Text(t, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 11)),
      );

  Widget _sectionTitle(String icon, String t) => Padding(
        padding: const EdgeInsets.only(top: 14, bottom: 8),
        child: Row(children: [Text(icon), const SizedBox(width: 6),
          Text(t, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13.5))]),
      );

  Widget _section(String title, List<(String, String, dynamic)> rows) {
    final present = rows.where((r) => r.$3 != null && '${r.$3}'.trim().isNotEmpty).toList();
    if (present.isEmpty) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 12),
      decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(14)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 12.5)),
        const SizedBox(height: 8),
        for (final r in present) Padding(
          padding: const EdgeInsets.symmetric(vertical: 5),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            SizedBox(width: 116, child: Text(gLang == 'en' ? r.$2 : r.$1, style: const TextStyle(color: _muted, fontSize: 12, fontWeight: FontWeight.w700))),
            Expanded(child: Text('${r.$3}', style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w600))),
          ]),
        ),
      ]),
    );
  }

  Widget _mediaThumb(Map m) {
    final isVideo = '${m['kind']}' == 'video';
    return GestureDetector(
      onTap: () => _openMedia(m),
      child: Container(
        width: 92, height: 92, margin: const EdgeInsetsDirectional.only(end: 8),
        decoration: BoxDecoration(color: Colors.black26, borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.white24)),
        clipBehavior: Clip.antiAlias,
        child: isVideo
            ? const Center(child: Icon(Icons.play_circle_fill_rounded, color: Colors.white, size: 34))
            : FutureBuilder<String>(
                future: _api.incidentMediaUrl(intOf(m['id'])),
                builder: (_, s) => s.hasData
                    ? Image.network(s.data!, fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) => const Icon(Icons.image_not_supported, color: Colors.white38))
                    : const Center(child: SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2)))),
      ),
    );
  }

  Widget _evBtn(IconData ic, String label, VoidCallback onTap) => OutlinedButton.icon(
        onPressed: _busy ? null : onTap,
        icon: Icon(ic, size: 17, color: Colors.white),
        style: OutlinedButton.styleFrom(foregroundColor: Colors.white, side: const BorderSide(color: Colors.white38),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(11))),
        label: Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
      );

  Widget _wfBtn(String ar, String en, Color c, VoidCallback onTap) => FilledButton(
        style: FilledButton.styleFrom(backgroundColor: c, padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10)),
        onPressed: _busy ? null : onTap,
        child: Text(gLang == 'en' ? en : ar, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
      );
}

class _IncidentForm extends StatefulWidget {
  const _IncidentForm({required this.onSaved});
  final VoidCallback onSaved;
  @override
  State<_IncidentForm> createState() => _IncidentFormState();
}

class _IncidentFormState extends State<_IncidentForm> {
  String _type = 'suspicious';
  String _sev = 'medium';
  final _desc = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _desc.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_desc.text.trim().isEmpty) return;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.createIncident(
          type: _type, severity: _sev, description: _desc.text.trim());
      widget.onSaved();
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final white = TextStyle(color: Colors.white);
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(tr('تسجيل حادث أمني', 'Report a security incident'),
              style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w800)),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            value: _type,
            dropdownColor: const Color(0xFF1E3A5F),
            style: white,
            decoration: InputDecoration(labelText: tr('النوع', 'Type'), labelStyle: white),
            items: [
              for (final e in _SecurityIncidentsScreenState.types.entries)
                DropdownMenuItem(value: e.key, child: Text(e.value, style: white)),
            ],
            onChanged: (v) => setState(() => _type = v!),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            value: _sev,
            dropdownColor: const Color(0xFF1E3A5F),
            style: white,
            decoration: InputDecoration(labelText: tr('الخطورة', 'Severity'), labelStyle: white),
            items: [
              for (final e in _SecurityIncidentsScreenState.severities.entries)
                DropdownMenuItem(value: e.key, child: Text(e.value, style: white)),
            ],
            onChanged: (v) => setState(() => _sev = v!),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _desc,
            style: white,
            maxLines: 3,
            decoration: InputDecoration(labelText: tr('الوصف', 'Description'), labelStyle: white),
          ),
          const SizedBox(height: 20),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE5484D)),
            onPressed: _busy ? null : _save,
            child: _busy
                ? const SizedBox(height: 22, width: 22, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : Text(tr('إرسال البلاغ', 'Submit report')),
          ),
        ],
      ),
    );
  }
}
