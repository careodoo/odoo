import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'location_picker.dart';
import 'searchable_picker.dart';

/// Professional "raise a work order" sheet for the client: pick facility +
/// location, target a service or a team, set priority, describe the job, and
/// optionally assign it directly to a specific worker.
class ClientWorkorderCreateSheet extends StatefulWidget {
  const ClientWorkorderCreateSheet({super.key, this.presetServiceType});
  final String? presetServiceType;

  /// Returns true via Navigator.pop when a work order was created.
  static Future<bool?> open(BuildContext context, {String? presetServiceType}) =>
      showModalBottomSheet<bool>(
        context: context,
        isScrollControlled: true,
        backgroundColor: Colors.transparent,
        builder: (_) => ClientWorkorderCreateSheet(presetServiceType: presetServiceType),
      );

  @override
  State<ClientWorkorderCreateSheet> createState() => _ClientWorkorderCreateSheetState();
}

class _WoMedia {
  _WoMedia(this.name, this.mimetype, this.b64, this.isVideo);
  final String name, mimetype, b64;
  final bool isVideo;
}

class _ClientWorkorderCreateSheetState extends State<ClientWorkorderCreateSheet> {
  Map<String, dynamic>? _opts;
  String? _error;
  final _title = TextEditingController();
  final _desc = TextEditingController();
  int? _facilityId;
  int? _locationId;
  int? _serviceId;
  int? _teamId;
  int? _workerId;
  String _priority = '1';
  bool _assign = false;
  bool _submitting = false;
  final List<_WoMedia> _media = [];
  final _picker = ImagePicker();

  static const _navy = Color(0xFF0E3A5F);
  static const _accent = Color(0xFFC0392B);
  static const _prio = {
    '0': (Color(0xFF64748B), Icons.low_priority_rounded, 'منخفضة', 'Low'),
    '1': (Color(0xFF0891B2), Icons.horizontal_rule_rounded, 'عادية', 'Normal'),
    '2': (Color(0xFFF7A23B), Icons.priority_high_rounded, 'عالية', 'High'),
    '3': (Color(0xFFE5484D), Icons.local_fire_department_rounded, 'عاجلة', 'Urgent'),
  };

  @override
  void initState() {
    super.initState();
    _loadOptions();
  }

  @override
  void dispose() {
    _title.dispose();
    _desc.dispose();
    super.dispose();
  }

  Future<void> _loadOptions() async {
    try {
      final o = await context.read<AuthProvider>().api.clientWorkorderOptions();
      if (!mounted) return;
      setState(() {
        _opts = o;
        final facs = (o['facilities'] as List?) ?? const [];
        if (facs.isNotEmpty) _facilityId = facs.first['id'] as int;
        if (widget.presetServiceType != null) {
          final svc = (o['services'] as List?)?.cast<Map>().firstWhere(
              (s) => '${s['type']}' == widget.presetServiceType, orElse: () => const {});
          if (svc != null && svc.isNotEmpty) _serviceId = svc['id'] as int;
        }
      });
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  List<Map> get _locations {
    final facs = (_opts?['facilities'] as List?)?.cast<Map>() ?? const [];
    final f = facs.firstWhere((x) => x['id'] == _facilityId, orElse: () => const {});
    return ((f['locations'] as List?) ?? const []).cast<Map>();
  }

  List<Map> get _teams {
    final teams = (_opts?['teams'] as List?)?.cast<Map>() ?? const [];
    return teams.where((t) => _facilityId == null || t['facility_id'] == _facilityId).toList();
  }

  Future<void> _submit() async {
    if (_title.text.trim().isEmpty) {
      _snack(tr('أدخل عنوان أمر العمل', 'Enter a work-order title'));
      return;
    }
    if (_serviceId == null && _teamId == null) {
      _snack(tr('اختر الخدمة أو الفريق', 'Choose a service or team'));
      return;
    }
    setState(() => _submitting = true);
    final body = <String, dynamic>{
      'title': _title.text.trim(),
      'facility_id': _facilityId,
      'service_id': _serviceId,
      'team_id': _teamId,
      'location_id': _locationId,
      'priority': _priority,
      'description': _desc.text.trim(),
      if (_assign && _workerId != null) 'employee_id': _workerId,
      'media': [for (final m in _media) {'name': m.name, 'mimetype': m.mimetype, 'data': m.b64}],
    };
    try {
      await context.read<AuthProvider>().api.clientWorkorderCreate(body);
      if (!mounted) return;
      Navigator.pop(context, true);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(tr('تم إنشاء أمر العمل بنجاح', 'Work order created')),
        backgroundColor: const Color(0xFF16A34A), behavior: SnackBarBehavior.floating));
    } catch (e) {
      if (mounted) {
        setState(() => _submitting = false);
        _snack('$e');
      }
    }
  }

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: _accent, behavior: SnackBarBehavior.floating));

  Future<void> _addPhoto(ImageSource src) async {
    final x = await _picker.pickImage(source: src, imageQuality: 60, maxWidth: 1600);
    if (x == null) return;
    final b = await x.readAsBytes();
    setState(() => _media.add(_WoMedia(x.name, 'image/jpeg', base64Encode(b), false)));
  }

  Future<void> _addVideo(ImageSource src) async {
    final x = await _picker.pickVideo(source: src, maxDuration: const Duration(seconds: 30));
    if (x == null) return;
    final b = await x.readAsBytes();
    if (b.length > 12 * 1024 * 1024) { _snack(tr('الفيديو كبير جداً (الحد 12 ميجا)', 'Video too large (max 12 MB)')); return; }
    setState(() => _media.add(_WoMedia(x.name, 'video/mp4', base64Encode(b), true)));
  }

  void _mediaMenu() => showModalBottomSheet(context: context, builder: (_) => SafeArea(child: Wrap(children: [
        ListTile(leading: const Icon(Icons.photo_camera_rounded, color: _accent), title: Text(tr('التقاط صورة', 'Take photo')),
            onTap: () { Navigator.pop(context); _addPhoto(ImageSource.camera); }),
        ListTile(leading: const Icon(Icons.videocam_rounded, color: Color(0xFFE5484D)), title: Text(tr('تسجيل فيديو', 'Record video')),
            onTap: () { Navigator.pop(context); _addVideo(ImageSource.camera); }),
        ListTile(leading: const Icon(Icons.photo_library_rounded, color: Color(0xFF7C3AED)), title: Text(tr('صورة من المعرض', 'Photo from gallery')),
            onTap: () { Navigator.pop(context); _addPhoto(ImageSource.gallery); }),
        ListTile(leading: const Icon(Icons.video_library_rounded, color: Color(0xFF0891B2)), title: Text(tr('فيديو من المعرض', 'Video from gallery')),
            onTap: () { Navigator.pop(context); _addVideo(ImageSource.gallery); }),
      ])));

  Widget _mediaStrip() => SizedBox(height: 84, child: ListView(scrollDirection: Axis.horizontal, children: [
        InkWell(onTap: _mediaMenu, borderRadius: BorderRadius.circular(12), child: Container(
          width: 84, height: 84,
          decoration: BoxDecoration(color: _accent.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(12), border: Border.all(color: _accent.withValues(alpha: 0.3))),
          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            const Icon(Icons.add_a_photo_rounded, color: _accent, size: 24),
            const SizedBox(height: 4),
            Text(tr('إضافة', 'Add'), style: const TextStyle(color: _accent, fontSize: 11, fontWeight: FontWeight.w800)),
          ]),
        )),
        for (var i = 0; i < _media.length; i++) Padding(padding: const EdgeInsets.only(right: 8), child: Stack(children: [
          Container(width: 84, height: 84, clipBehavior: Clip.antiAlias,
              decoration: BoxDecoration(borderRadius: BorderRadius.circular(12), color: Colors.black12),
              child: _media[i].isVideo
                  ? const Center(child: Icon(Icons.play_circle_fill_rounded, color: Color(0xFFE5484D), size: 34))
                  : Image.memory(base64Decode(_media[i].b64), fit: BoxFit.cover)),
          Positioned(top: 2, right: 2, child: GestureDetector(onTap: () => setState(() => _media.removeAt(i)),
              child: Container(decoration: const BoxDecoration(color: Colors.black54, shape: BoxShape.circle),
                  child: const Icon(Icons.close_rounded, color: Colors.white, size: 16)))),
        ])),
      ]));

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false,
      initialChildSize: 0.9,
      minChildSize: 0.5,
      maxChildSize: 0.96,
      builder: (_, sc) => Container(
        decoration: const BoxDecoration(
          color: Color(0xFFF6F7F9),
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        ),
        clipBehavior: Clip.antiAlias,
        child: Column(children: [
          // header
          CustomPaint(
            painter: const BrandPattern(opacity: 0.07),
            child: Container(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
              decoration: const BoxDecoration(
                gradient: LinearGradient(colors: [Color(0xFFE24A3B), Color(0xFFC0392B), Color(0xFF8E241B)],
                    begin: Alignment.topRight, end: Alignment.bottomLeft),
              ),
              child: Column(children: [
                Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
                Row(children: [
                  Container(
                    width: 42, height: 42, alignment: Alignment.center,
                    decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(12)),
                    child: const Icon(Icons.add_task_rounded, color: Colors.white, size: 22),
                  ),
                  const SizedBox(width: 12),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(tr('أمر عمل جديد', 'New work order'),
                        style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
                    Text(tr('أسنِد لأي خدمة أو فريق أو عامل', 'Assign to any service, team or worker'),
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 11.5)),
                  ])),
                  IconButton(icon: const Icon(Icons.close_rounded, color: Colors.white), onPressed: () => Navigator.pop(context)),
                ]),
              ]),
            ),
          ),
          Expanded(child: _opts == null
              ? Center(child: _error != null
                  ? Text(_error!, style: const TextStyle(color: Colors.grey))
                  : const CircularProgressIndicator(color: _accent))
              : ListView(controller: sc, padding: const EdgeInsets.all(16), children: _form())),
          // submit bar
          if (_opts != null)
            SafeArea(top: false, child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
              child: SizedBox(height: 52, child: FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: _accent,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
                onPressed: _submitting ? null : _submit,
                icon: _submitting
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.send_rounded),
                label: Text(tr('إنشاء أمر العمل', 'Create work order'),
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
              )),
            )),
        ]),
      ),
    );
  }

  List<Widget> _form() {
    final services = (_opts!['services'] as List?)?.cast<Map>() ?? const [];
    return [
      _label(Icons.title_rounded, tr('عنوان المهمة', 'Task title')),
      const SizedBox(height: 8),
      _field(_title, tr('مثال: صيانة مكيّف الدور الثاني', 'e.g. Fix 2nd floor AC')),
      const SizedBox(height: 16),
      _label(Icons.apartment_rounded, tr('المرفق والموقع', 'Facility & location')),
      const SizedBox(height: 8),
      SearchableField(
        label: tr('المرفق', 'Facility'), icon: Icons.apartment_rounded, value: _facilityId, allowClear: false,
        options: [for (final f in (_opts!['facilities'] as List).cast<Map>()) PickOption(value: f['id'], label: '${f['name']}')],
        onChanged: (v) => setState(() { _facilityId = v as int?; _locationId = null; _teamId = null; }),
      ),
      if (_locations.isNotEmpty) ...[
        const SizedBox(height: 10),
        _locationField(),
      ],
      const SizedBox(height: 16),
      _label(Icons.design_services_rounded, tr('الخدمة', 'Service')),
      const SizedBox(height: 8),
      SearchableField(
        label: tr('نوع الخدمة', 'Service type'), icon: Icons.design_services_rounded, value: _serviceId,
        options: [for (final s in services) PickOption(value: s['id'], label: '${s['name']}', sublabel: '${s['type_label'] ?? ''}', search: '${s['type'] ?? ''} ${s['type_label'] ?? ''}')],
        onChanged: (v) => setState(() => _serviceId = v as int?),
      ),
      if (_teams.isNotEmpty) ...[
        const SizedBox(height: 10),
        SearchableField(
          label: tr('توجيه لفريق (اختياري)', 'Route to team (optional)'), icon: Icons.diversity_3_rounded, value: _teamId,
          options: [for (final t in _teams) PickOption(value: t['id'], label: '${t['name']}', sublabel: t['service'] != null ? '${t['service']}' : null)],
          onChanged: (v) => setState(() => _teamId = v as int?),
        ),
      ],
      const SizedBox(height: 16),
      _label(Icons.flag_rounded, tr('الأولوية', 'Priority')),
      const SizedBox(height: 8),
      Row(children: [for (final e in _prio.entries) Expanded(child: _prioChip(e.key))]),
      const SizedBox(height: 16),
      // direct assignment
      Container(
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
            border: Border.all(color: _assign ? _navy : Colors.grey.shade300)),
        child: Column(children: [
          SwitchListTile(
            value: _assign,
            activeColor: _navy,
            onChanged: (v) => setState(() => _assign = v),
            title: Text(tr('إسناد مباشر لعامل', 'Assign directly to a worker'),
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5)),
            subtitle: Text(tr('يبدأ الأمر كمُسنَد لهذا العامل', 'Starts assigned to this worker'),
                style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
          ),
          if (_assign) Padding(
            padding: const EdgeInsets.fromLTRB(14, 0, 14, 12),
            child: SearchableField(
              label: tr('العامل', 'Worker'), icon: Icons.person_rounded, value: _workerId,
              options: [for (final w in (_opts!['workers'] as List).cast<Map>())
                PickOption(value: w['id'], label: '${w['name']}', sublabel: w['job'] != null ? '${w['job']}' : null)],
              onChanged: (v) => setState(() => _workerId = v as int?),
            ),
          ),
        ]),
      ),
      const SizedBox(height: 16),
      _label(Icons.perm_media_rounded, tr('صور وفيديو (اختياري)', 'Photos & video (optional)')),
      const SizedBox(height: 8),
      _mediaStrip(),
      const SizedBox(height: 16),
      _label(Icons.notes_rounded, tr('تفاصيل إضافية', 'Extra details')),
      const SizedBox(height: 8),
      _field(_desc, tr('وصف المشكلة، الملاحظات، المتطلبات…', 'Describe the issue, notes, requirements…'), lines: 4),
      const SizedBox(height: 8),
    ];
  }

  /// A tappable location field that opens the searchable picker (with QR + NFC
  /// scanning), instead of a long flat dropdown.
  Widget _locationField() {
    final sel = _locationId == null ? null
        : _locations.firstWhere((l) => l['id'] == _locationId, orElse: () => const {});
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: () async {
        final picked = await LocationPickerSheet.open(context, locations: _locations,
            title: tr('اختر موقع أمر العمل', 'Choose work-order location'));
        if (picked != null && mounted) setState(() => _locationId = picked['id'] as int?);
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12),
            border: Border.all(color: Colors.grey.shade300)),
        child: Row(children: [
          Icon(Icons.pin_drop_rounded, size: 20, color: _accent),
          const SizedBox(width: 10),
          Expanded(child: Text(
            sel == null || sel.isEmpty ? tr('الموقع (بحث / QR / NFC) — اختياري', 'Location (search / QR / NFC) — optional')
                : '${sel['name']}${sel['code'] != null ? ' · ${sel['code']}' : ''}',
            maxLines: 1, overflow: TextOverflow.ellipsis,
            style: TextStyle(fontSize: 13, fontWeight: sel != null && sel.isNotEmpty ? FontWeight.w800 : FontWeight.w500,
                color: sel != null && sel.isNotEmpty ? _navy : Colors.grey.shade500),
          )),
          if (_locationId != null)
            GestureDetector(onTap: () => setState(() => _locationId = null),
                child: const Icon(Icons.close_rounded, size: 18, color: Colors.grey))
          else const Icon(Icons.chevron_left_rounded, color: Colors.grey),
        ]),
      ),
    );
  }

  Widget _label(IconData ic, String t) => Row(children: [
        Icon(ic, size: 16, color: _accent),
        const SizedBox(width: 7),
        Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
      ]);

  Widget _field(TextEditingController c, String hint, {int lines = 1}) => TextField(
        controller: c, maxLines: lines,
        decoration: InputDecoration(
          hintText: hint, filled: true, fillColor: Colors.white,
          hintStyle: TextStyle(fontSize: 13, color: Colors.grey.shade400),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: _accent, width: 1.6)),
        ),
      );


  Widget _prioChip(String key) {
    final s = _prio[key]!;
    final on = _priority == key;
    return GestureDetector(
      onTap: () => setState(() => _priority = key),
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
          Icon(s.$2, size: 18, color: on ? Colors.white : s.$1),
          const SizedBox(height: 3),
          Text(tr(s.$3, s.$4), style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: on ? Colors.white : _navy)),
        ]),
      ),
    );
  }
}
