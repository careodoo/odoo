import 'dart:async';
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
  static const types = {
    'theft': 'سرقة/سطو', 'vandalism': 'تخريب', 'trespassing': 'تسلّل',
    'assault': 'اعتداء', 'fire': 'حريق', 'medical': 'طارئ طبي',
    'suspicious': 'نشاط مشبوه', 'other': 'أخرى',
  };
  static const severities = {'low': 'منخفض', 'medium': 'متوسط', 'high': 'عالٍ', 'critical': 'حرج'};

  static const _navy = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);

  Map<String, dynamic>? _data;
  bool _loading = true;
  String _q = '', _state = 'all';
  int _offset = 0;
  final _limit = 20;
  Timer? _debounce;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final d = await context.read<AuthProvider>().api.securityIncidents(q: _q, state: _state, offset: _offset, limit: _limit);
      if (mounted) setState(() { _data = d; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _loading = false; });
    }
  }

  void _onSearch(String v) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 400), () {
      _q = v.trim(); _offset = 0; _load();
    });
  }

  @override
  Widget build(BuildContext context) {
    final items = ((_data?['items'] as List?) ?? const []).cast<Map>();
    final stats = (_data?['stats'] as Map?) ?? const {};
    final total = (_data?['total'] ?? 0) as int;
    return Scaffold(
      backgroundColor: _navy,
      appBar: AppBar(title: Text(tr('البلاغات الأمنية', 'Incidents')), backgroundColor: _navy),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openForm,
        icon: const Icon(Icons.add_alert),
        label: Text(tr('تسجيل حادث', 'Report incident')),
        backgroundColor: const Color(0xFFE5484D),
      ),
      body: Column(children: [
        // header stats
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
          child: Row(children: [
            _stat('${stats['total'] ?? 0}', tr('الكل', 'Total'), _muted),
            _stat('${stats['open'] ?? 0}', tr('مفتوحة', 'Open'), const Color(0xFF4AA8FF)),
            _stat('${stats['critical'] ?? 0}', tr('حرجة', 'Critical'), const Color(0xFFE5484D)),
            _stat('${stats['resolved'] ?? 0}', tr('مُغلقة', 'Closed'), const Color(0xFF37C98A)),
          ]),
        ),
        // search
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 4, 12, 6),
          child: TextField(
            style: const TextStyle(color: Colors.white),
            onChanged: _onSearch,
            decoration: InputDecoration(
              hintText: tr('بحث في البلاغات…', 'Search incidents…'),
              hintStyle: const TextStyle(color: _muted),
              prefixIcon: const Icon(Icons.search_rounded, color: _muted),
              filled: true, fillColor: _card, isDense: true,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            ),
          ),
        ),
        // state filter chips
        SizedBox(height: 38, child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
          for (final s in [('all', tr('الكل', 'All')), ('open', tr('مفتوحة', 'Open')), ('reported', tr('مُبلَّغة', 'Reported')), ('investigating', tr('قيد التحقيق', 'Investigating')), ('resolved', tr('محلولة', 'Resolved')), ('closed', tr('مغلقة', 'Closed'))])
            Padding(padding: const EdgeInsetsDirectional.only(end: 6), child: ChoiceChip(
              label: Text(s.$2, style: const TextStyle(fontSize: 11.5)),
              selected: _state == s.$1, backgroundColor: _card, selectedColor: const Color(0xFFE5484D),
              labelStyle: TextStyle(color: _state == s.$1 ? Colors.white : _muted, fontWeight: FontWeight.w700),
              onSelected: (_) { setState(() { _state = s.$1; _offset = 0; }); _load(); })),
        ])),
        Expanded(child: _loading
            ? const Center(child: CircularProgressIndicator())
            : items.isEmpty
                ? _msg(tr('لا بلاغات مطابقة.', 'No matching incidents.'))
                : RefreshIndicator(
                    onRefresh: _load,
                    child: ListView.builder(
                      padding: const EdgeInsets.all(12),
                      itemCount: items.length + 1,
                      itemBuilder: (_, i) {
                        if (i == items.length) return _pager(total);
                        return _card2(items[i]);
                      },
                    ),
                  )),
      ]),
    );
  }

  Widget _stat(String v, String l, Color c) => Expanded(child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 3),
        padding: const EdgeInsets.symmetric(vertical: 9),
        decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(12)),
        child: Column(children: [
          Text(v, style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 17)),
          Text(l, style: const TextStyle(color: _muted, fontSize: 9.5, fontWeight: FontWeight.w600)),
        ]),
      ));

  Widget _pager(int total) {
    final shown = _offset + (((_data?['items'] as List?) ?? const []).length);
    final hasMore = shown < total;
    if (_offset == 0 && !hasMore) return const SizedBox(height: 40);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
        if (_offset > 0) OutlinedButton(
          onPressed: () { setState(() => _offset = (_offset - _limit).clamp(0, _offset)); _load(); },
          child: Text(tr('السابق', 'Prev'))),
        const SizedBox(width: 12),
        Text('${_offset + 1}–$shown / $total', style: const TextStyle(color: _muted, fontSize: 12)),
        const SizedBox(width: 12),
        if (hasMore) OutlinedButton(
          onPressed: () { setState(() => _offset += _limit); _load(); },
          child: Text(tr('التالي', 'Next'))),
      ]),
    );
  }

  Widget _msg(String t) => ListView(children: [
        const SizedBox(height: 120),
        Center(child: Text(t, style: const TextStyle(color: _muted))),
      ]);

  Color _sevColor(String s) => switch (s) {
        'critical' => const Color(0xFFE5484D),
        'high' => const Color(0xFFF2603F),
        'medium' => const Color(0xFFF7A23B),
        _ => const Color(0xFF37C98A),
      };

  Color _stateColor(String s) => switch (s) {
        'resolved' || 'closed' => const Color(0xFF37C98A),
        'investigating' => const Color(0xFF4AA8FF),
        'reported' => const Color(0xFFF7A23B),
        _ => _muted,
      };

  Widget _card2(Map i) {
    final sev = '${i['severity'] ?? 'low'}';
    final sc = _sevColor(sev);
    final st = '${i['state'] ?? ''}';
    return Card(
      color: _card,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () => _openIncident(i),
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Container(width: 40, height: 40, alignment: Alignment.center,
                  decoration: BoxDecoration(color: sc.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(11)),
                  child: Icon(Icons.warning_amber_rounded, color: sc, size: 20)),
              const SizedBox(width: 11),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${i['name'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13.5)),
                Text('${types[i['type']] ?? i['type_label'] ?? ''} · ${i['premise'] ?? ''}',
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 11)),
              ])),
              Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(color: _stateColor(st).withValues(alpha: 0.16), borderRadius: BorderRadius.circular(20)),
                    child: Text('${i['state_label'] ?? st}', style: TextStyle(color: _stateColor(st), fontWeight: FontWeight.w800, fontSize: 9.5))),
                const SizedBox(height: 3),
                Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                    decoration: BoxDecoration(color: sc.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(20)),
                    child: Text('${severities[sev] ?? i['severity_label'] ?? sev}', style: TextStyle(color: sc, fontWeight: FontWeight.w800, fontSize: 9.5))),
              ]),
            ]),
            if (i['description'] != null) Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text('${i['description']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 12)),
            ),
            Padding(padding: const EdgeInsets.only(top: 6), child: Row(children: [
              if (i['date'] != null) ...[const Icon(Icons.schedule_rounded, size: 12, color: _muted), const SizedBox(width: 3),
                Text('${i['date']}', style: const TextStyle(color: _muted, fontSize: 10.5))],
              const Spacer(),
              if ((i['media_count'] as num?) != null && (i['media_count'] as num) > 0) ...[
                const Icon(Icons.attach_file_rounded, size: 12, color: _muted), const SizedBox(width: 2),
                Text('${i['media_count']}', style: const TextStyle(color: _muted, fontSize: 10.5))],
            ])),
          ]),
        ),
      ),
    );
  }

  void _openIncident(Map i) {
    showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => _IncidentDetailSheet(id: intOf(i['id']), sevColor: _sevColor),
    ).then((_) => _load());
  }


  void _openForm() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF0F1B2E),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _IncidentForm(onSaved: () { Navigator.pop(context); _offset = 0; _load(); }),
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

  Future<void> _resolveWithNotes([String key = 'resolve']) async {
    final isClose = key == 'close';
    final ctrl = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      title: Text(isClose ? tr('إغلاق البلاغ', 'Close incident') : tr('حل البلاغ', 'Resolve incident')),
      content: TextField(controller: ctrl, maxLines: 3, autofocus: true,
          decoration: InputDecoration(labelText: isClose ? tr('سبب الإغلاق', 'Closing reason') : tr('ملاحظات الحل', 'Resolution notes'), border: const OutlineInputBorder())),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(style: FilledButton.styleFrom(backgroundColor: isClose ? const Color(0xFF64748B) : const Color(0xFF16A34A)),
            onPressed: () => Navigator.pop(c, true), child: Text(isClose ? tr('إغلاق', 'Close') : tr('حل', 'Resolve'))),
      ]));
    if (ok != true) return;
    await _runAction(key, extra: {'resolution_notes': ctrl.text.trim()});
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
                          _wfBtn(f.$2, f.$3, f.$4, () => (f.$1 == 'resolve' || f.$1 == 'close') ? _resolveWithNotes(f.$1) : _runAction(f.$1)),
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
  static const _fieldBg = Color(0xFF1E3A5F);
  static const _muted = Color(0xFF9CB2CD);
  bool _full = false; // false = quick report, true = full report
  bool _busy = false, _loadingMeta = true;
  Map<String, dynamic>? _meta;

  String _type = 'suspicious';
  String _sev = 'medium';
  Map? _premise;
  final _desc = TextEditingController();
  final _location = TextEditingController();
  final _action = TextEditingController();
  final _policeRef = TextEditingController();
  bool _police = false;
  double? _lat, _lng;
  // media captured before the incident exists → uploaded right after creation
  final List<Map<String, dynamic>> _pending = [];

  @override
  void initState() {
    super.initState();
    _loadMeta();
  }

  Future<void> _loadMeta() async {
    try {
      final m = await context.read<AuthProvider>().api.incidentMeta();
      if (mounted) setState(() { _meta = m; _loadingMeta = false; });
    } catch (_) {
      if (mounted) setState(() => _loadingMeta = false);
    }
  }

  @override
  void dispose() {
    _desc.dispose(); _location.dispose(); _action.dispose(); _policeRef.dispose();
    super.dispose();
  }

  void _snack(String m, [Color? c]) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: c, behavior: SnackBarBehavior.floating));

  Future<void> _capture(String kind) async {
    try {
      final picker = ImagePicker();
      final XFile? x = kind == 'video'
          ? await picker.pickVideo(source: ImageSource.camera, maxDuration: const Duration(seconds: 60))
          : await picker.pickImage(source: ImageSource.camera, maxWidth: 1600, imageQuality: 70);
      if (x == null) return;
      final bytes = await x.readAsBytes();
      setState(() => _pending.add({'kind': kind, 'file': base64Encode(bytes), 'filename': x.name}));
    } catch (e) {
      if (mounted) _snack('$e', const Color(0xFFE11D48));
    }
  }

  Future<void> _grabLocation() async {
    try {
      if (await Geolocator.checkPermission() == LocationPermission.denied) {
        await Geolocator.requestPermission();
      }
      final p = await Geolocator.getCurrentPosition();
      setState(() { _lat = p.latitude; _lng = p.longitude; });
      _snack(tr('تم تحديد الموقع', 'Location captured'), const Color(0xFF16A34A));
    } catch (e) {
      if (mounted) _snack('$e', const Color(0xFFE11D48));
    }
  }

  Future<void> _save() async {
    if (_desc.text.trim().isEmpty) { _snack(tr('اكتب وصف البلاغ', 'Enter a description')); return; }
    setState(() => _busy = true);
    try {
      final body = <String, dynamic>{
        'type': _type, 'severity': _sev, 'description': _desc.text.trim(),
        if (_premise != null) 'premise_id': _premise!['v'],
        if (_lat != null) 'lat': _lat, if (_lng != null) 'lng': _lng,
      };
      if (_full) {
        body.addAll({
          if (_location.text.trim().isNotEmpty) 'location': _location.text.trim(),
          if (_action.text.trim().isNotEmpty) 'action_taken': _action.text.trim(),
          'police_notified': _police,
          if (_policeRef.text.trim().isNotEmpty) 'police_report_number': _policeRef.text.trim(),
        });
      }
      final rec = await context.read<AuthProvider>().api.createIncident(body);
      // upload any captured media onto the fresh incident
      final id = (rec['id'] as num?)?.toInt();
      if (id != null) {
        for (final m in _pending) {
          try { await context.read<AuthProvider>().api.incidentMedia(id, m); } catch (_) {}
        }
      }
      widget.onSaved();
    } catch (e) {
      if (mounted) { setState(() => _busy = false); _snack('$e', const Color(0xFFE11D48)); }
    }
  }

  @override
  Widget build(BuildContext context) {
    const white = TextStyle(color: Colors.white);
    final premises = ((_meta?['premises'] as List?) ?? const []).cast<Map>();
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.85, maxChildSize: 0.96, minChildSize: 0.5,
      builder: (_, sc) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
        child: ListView(controller: sc, padding: const EdgeInsets.all(20), children: [
          Center(child: Container(width: 42, height: 4, margin: const EdgeInsets.only(bottom: 14),
              decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(3)))),
          Text(tr('تسجيل حادث أمني', 'Report a security incident'),
              style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
          const SizedBox(height: 14),
          // quick vs full toggle
          SegmentedButton<bool>(
            segments: [
              ButtonSegment(value: false, icon: const Icon(Icons.bolt_rounded, size: 16), label: Text(tr('بلاغ سريع', 'Quick'))),
              ButtonSegment(value: true, icon: const Icon(Icons.description_rounded, size: 16), label: Text(tr('بلاغ مفصّل', 'Full'))),
            ],
            selected: {_full},
            onSelectionChanged: (s) => setState(() => _full = s.first),
            style: ButtonStyle(
              backgroundColor: WidgetStateProperty.resolveWith((st) => st.contains(WidgetState.selected) ? const Color(0xFFE5484D) : _fieldBg),
              foregroundColor: WidgetStateProperty.all(Colors.white),
            ),
          ),
          const SizedBox(height: 14),
          if (_loadingMeta) const Padding(padding: EdgeInsets.all(8), child: LinearProgressIndicator()),
          _drop(tr('النوع', 'Type'), _type, _SecurityIncidentsScreenState.types, (v) => setState(() => _type = v)),
          const SizedBox(height: 12),
          _drop(tr('الخطورة', 'Severity'), _sev, _SecurityIncidentsScreenState.severities, (v) => setState(() => _sev = v)),
          if (_sev == 'critical') Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Row(children: [const Icon(Icons.priority_high_rounded, color: Color(0xFFE5484D), size: 16),
              Expanded(child: Text(tr(' بلاغ حرج — سيتاح إشعار العميل بعد الحفظ', ' Critical — client notify available after saving'),
                  style: const TextStyle(color: Color(0xFFE5484D), fontSize: 11)))]),
          ),
          const SizedBox(height: 12),
          // premise picker
          if (premises.isNotEmpty)
            InkWell(
              onTap: () async {
                final p = await showModalBottomSheet<Map>(context: context, backgroundColor: _fieldBg,
                  builder: (_) => ListView(shrinkWrap: true, children: [
                    for (final pr in premises) ListTile(
                      title: Text('${pr['l']}', style: white),
                      onTap: () => Navigator.pop(context, pr)),
                  ]));
                if (p != null) setState(() => _premise = p);
              },
              child: InputDecorator(
                decoration: InputDecoration(labelText: tr('الموقع الأمني', 'Premise'), labelStyle: const TextStyle(color: _muted),
                    filled: true, fillColor: _fieldBg, border: const OutlineInputBorder()),
                child: Text(_premise == null ? tr('اختر…', 'Select…') : '${_premise!['l']}', style: white))),
          const SizedBox(height: 12),
          TextField(controller: _desc, style: white, maxLines: 3,
              decoration: _dec(tr('الوصف *', 'Description *'))),
          if (_full) ...[
            const SizedBox(height: 12),
            TextField(controller: _location, style: white, decoration: _dec(tr('المكان المحدد', 'Specific location'))),
            const SizedBox(height: 12),
            TextField(controller: _action, style: white, maxLines: 2, decoration: _dec(tr('الإجراء المتخذ', 'Action taken'))),
            const SizedBox(height: 8),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              title: Text(tr('تم إبلاغ الشرطة', 'Police notified'), style: white),
              value: _police, activeColor: const Color(0xFFE5484D),
              onChanged: (v) => setState(() => _police = v)),
            if (_police) TextField(controller: _policeRef, style: white, decoration: _dec(tr('رقم بلاغ الشرطة', 'Police report #'))),
          ],
          const SizedBox(height: 14),
          // media + location capture
          Wrap(spacing: 8, runSpacing: 8, children: [
            _capBtn(Icons.photo_camera_rounded, tr('صورة', 'Photo'), () => _capture('photo')),
            _capBtn(Icons.videocam_rounded, tr('فيديو', 'Video'), () => _capture('video')),
            _capBtn(_lat != null ? Icons.check_circle_rounded : Icons.my_location_rounded,
                _lat != null ? tr('الموقع ✓', 'Located ✓') : tr('تحديد الموقع', 'Locate'), _grabLocation),
          ]),
          if (_pending.isNotEmpty) Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text('${tr('مرفقات', 'Attachments')}: ${_pending.where((m) => m['kind'] == 'photo').length} 📷 · ${_pending.where((m) => m['kind'] == 'video').length} 🎥',
                style: const TextStyle(color: _muted, fontSize: 12)),
          ),
          const SizedBox(height: 18),
          FilledButton.icon(
            style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE5484D), minimumSize: const Size(0, 50)),
            onPressed: _busy ? null : _save,
            icon: _busy ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Icon(Icons.send_rounded),
            label: Text(_busy ? tr('جارٍ الحفظ…', 'Saving…') : tr('إرسال البلاغ', 'Submit report'), style: const TextStyle(fontWeight: FontWeight.w900)),
          ),
          const SizedBox(height: 10),
        ]),
      ),
    );
  }

  InputDecoration _dec(String label) => InputDecoration(
      labelText: label, labelStyle: const TextStyle(color: _muted),
      filled: true, fillColor: _fieldBg,
      border: const OutlineInputBorder(borderSide: BorderSide.none));

  Widget _drop(String label, String value, Map<String, String> opts, void Function(String) onCh) => DropdownButtonFormField<String>(
        value: value, dropdownColor: _fieldBg, style: const TextStyle(color: Colors.white),
        decoration: _dec(label),
        items: [for (final e in opts.entries) DropdownMenuItem(value: e.key, child: Text(e.value, style: const TextStyle(color: Colors.white)))],
        onChanged: (v) => onCh(v!),
      );

  Widget _capBtn(IconData ic, String label, VoidCallback onTap) => OutlinedButton.icon(
        onPressed: _busy ? null : onTap,
        icon: Icon(ic, size: 17, color: Colors.white),
        style: OutlinedButton.styleFrom(foregroundColor: Colors.white, side: const BorderSide(color: Colors.white38),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10)),
        label: Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
      );
}
