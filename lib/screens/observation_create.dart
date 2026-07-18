import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'location_picker.dart';

/// Professional "new quality observation" form: facility + searchable/QR/NFC
/// location, severity, description, and captured or uploaded photos & videos.
class ObservationCreateSheet extends StatefulWidget {
  const ObservationCreateSheet({super.key});

  static Future<bool?> open(BuildContext context) => showModalBottomSheet<bool>(
        context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
        builder: (_) => const ObservationCreateSheet(),
      );

  @override
  State<ObservationCreateSheet> createState() => _ObservationCreateSheetState();
}

class _Media {
  _Media(this.name, this.mimetype, this.b64, this.isVideo);
  final String name, mimetype, b64;
  final bool isVideo;
}

class _ObservationCreateSheetState extends State<ObservationCreateSheet> {
  List<dynamic>? _facs;
  List<dynamic>? _svcs;
  List<Map> _locations = const [];
  String? _error;
  final _title = TextEditingController();
  final _desc = TextEditingController();
  int? _facId;
  int? _svcId;
  int? _locId;
  String? _locLabel;
  String _sev = 'medium';
  final List<_Media> _media = [];
  bool _submitting = false;
  final _picker = ImagePicker();

  static const _accent = Color(0xFF0EA5A4);
  static const _navy = Color(0xFF0E3A5F);
  static const _sevs = [
    ('low', 'منخفضة', 'Low', Color(0xFF64748B)),
    ('medium', 'متوسطة', 'Medium', Color(0xFF0891B2)),
    ('high', 'عالية', 'High', Color(0xFFF7A23B)),
    ('critical', 'حرجة', 'Critical', Color(0xFFE5484D)),
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _title.dispose();
    _desc.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final api = context.read<AuthProvider>().api;
      final facs = await api.facilities();
      final svcs = await api.servicesList();
      if (!mounted) return;
      setState(() {
        _facs = facs;
        _svcs = svcs;
        if (facs.isNotEmpty) _facId = facs.first['id'] as int;
      });
      _loadLocations();
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  Future<void> _loadLocations() async {
    if (_facId == null) return;
    try {
      final d = await context.read<AuthProvider>().api.clientFacility(_facId!);
      if (mounted) setState(() => _locations = ((d['locations'] as List?) ?? const []).cast<Map>());
    } catch (_) {
      if (mounted) setState(() => _locations = const []);
    }
  }

  Future<void> _addPhoto(ImageSource src) async {
    try {
      final x = await _picker.pickImage(source: src, imageQuality: 60, maxWidth: 1600);
      if (x == null) return;
      final bytes = await x.readAsBytes();
      setState(() => _media.add(_Media(x.name, 'image/jpeg', base64Encode(bytes), false)));
    } catch (e) {
      _snack('$e');
    }
  }

  Future<void> _addVideo(ImageSource src) async {
    try {
      final x = await _picker.pickVideo(source: src, maxDuration: const Duration(seconds: 30));
      if (x == null) return;
      final bytes = await x.readAsBytes();
      if (bytes.length > 12 * 1024 * 1024) {
        _snack(tr('الفيديو كبير جداً (الحد 12 ميجا)', 'Video too large (max 12 MB)'));
        return;
      }
      setState(() => _media.add(_Media(x.name, 'video/mp4', base64Encode(bytes), true)));
    } catch (e) {
      _snack('$e');
    }
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

  Future<void> _submit() async {
    if (_title.text.trim().isEmpty) { _snack(tr('أدخل الملاحظة', 'Enter the observation')); return; }
    setState(() => _submitting = true);
    try {
      await context.read<AuthProvider>().api.createObservation({
        'title': _title.text.trim(), 'facility_id': _facId, 'location_id': _locId,
        'service_id': _svcId, 'severity': _sev, 'description': _desc.text.trim(),
        'media': [for (final m in _media) {'name': m.name, 'mimetype': m.mimetype, 'data': m.b64}],
      });
      if (!mounted) return;
      Navigator.pop(context, true);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(tr('سُجّلت الملاحظة', 'Observation recorded')),
        backgroundColor: const Color(0xFF16A34A), behavior: SnackBarBehavior.floating));
    } catch (e) {
      if (mounted) { setState(() => _submitting = false); _snack('$e'); }
    }
  }

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: _accent, behavior: SnackBarBehavior.floating));

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.92, minChildSize: 0.5, maxChildSize: 0.96,
      builder: (_, sc) => Container(
        decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        clipBehavior: Clip.antiAlias,
        child: Column(children: [
          CustomPaint(
            painter: const BrandPattern(opacity: 0.07),
            child: Container(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
              decoration: BoxDecoration(gradient: LinearGradient(
                  colors: [_accent, Color.lerp(_accent, Colors.black, 0.35)!], begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Column(children: [
                Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
                Row(children: [
                  Container(width: 42, height: 42, alignment: Alignment.center,
                      decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(12)),
                      child: const Icon(Icons.fact_check_rounded, color: Colors.white, size: 22)),
                  const SizedBox(width: 12),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(tr('ملاحظة جودة جديدة', 'New quality observation'),
                        style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
                    Text(tr('وثّقها بالصور والفيديو والموقع', 'Document with media & location'),
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 11.5)),
                  ])),
                  IconButton(icon: const Icon(Icons.close_rounded, color: Colors.white), onPressed: () => Navigator.pop(context)),
                ]),
              ]),
            ),
          ),
          Expanded(child: _facs == null
              ? Center(child: _error != null ? Text(_error!, style: const TextStyle(color: Colors.grey)) : const CircularProgressIndicator(color: _accent))
              : ListView(controller: sc, padding: const EdgeInsets.all(16), children: _form())),
          if (_facs != null) SafeArea(top: false, child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
            child: SizedBox(height: 52, child: FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: _accent, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
              onPressed: _submitting ? null : _submit,
              icon: _submitting
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.check_rounded),
              label: Text(tr('تسجيل الملاحظة', 'Log observation'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
            )),
          )),
        ]),
      ),
    );
  }

  List<Widget> _form() {
    return [
      _lbl(Icons.edit_rounded, tr('الملاحظة', 'Observation')),
      const SizedBox(height: 8),
      _field(_title, tr('مثال: أرضية غير نظيفة بالمدخل', 'e.g. Dirty floor at the entrance')),
      const SizedBox(height: 16),
      _lbl(Icons.apartment_rounded, tr('المرفق والموقع', 'Facility & location')),
      const SizedBox(height: 8),
      _dd<int?>(tr('المرفق', 'Facility'), _facId,
          [for (final f in _facs!) DropdownMenuItem(value: f['id'] as int, child: Text('${f['name']}'))],
          (v) => setState(() { _facId = v; _locId = null; _locLabel = null; _loadLocations(); })),
      const SizedBox(height: 10),
      _locationField(),
      const SizedBox(height: 16),
      _lbl(Icons.flag_rounded, tr('الخطورة', 'Severity')),
      const SizedBox(height: 8),
      Row(children: [for (final s in _sevs) Expanded(child: _sevChip(s))]),
      const SizedBox(height: 16),
      _lbl(Icons.design_services_rounded, tr('الخدمة (اختياري)', 'Service (optional)')),
      const SizedBox(height: 8),
      _dd<int?>(tr('الخدمة', 'Service'), _svcId,
          [const DropdownMenuItem(value: null, child: Text('—')),
           for (final s in _svcs ?? const []) DropdownMenuItem(value: s['id'] as int, child: Text('${s['name']}'))],
          (v) => setState(() => _svcId = v)),
      const SizedBox(height: 16),
      _lbl(Icons.perm_media_rounded, tr('صور وفيديو', 'Photos & video')),
      const SizedBox(height: 8),
      _mediaStrip(),
      const SizedBox(height: 16),
      _lbl(Icons.notes_rounded, tr('الوصف', 'Description')),
      const SizedBox(height: 8),
      _field(_desc, tr('تفاصيل إضافية…', 'Extra details…'), lines: 3),
      const SizedBox(height: 8),
    ];
  }

  Widget _locationField() {
    return InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: _locations.isEmpty ? null : () async {
        final picked = await LocationPickerSheet.open(context, locations: _locations,
            title: tr('اختر موقع الملاحظة', 'Choose observation location'));
        if (picked != null && mounted) setState(() {
          _locId = picked['id'] as int?;
          _locLabel = '${picked['name']}${picked['code'] != null ? ' · ${picked['code']}' : ''}';
        });
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.grey.shade300)),
        child: Row(children: [
          const Icon(Icons.pin_drop_rounded, size: 20, color: _accent),
          const SizedBox(width: 10),
          Expanded(child: Text(
            _locLabel ?? (_locations.isEmpty ? tr('لا مواقع لهذا المرفق', 'No locations for this facility')
                : tr('الموقع (بحث / QR / NFC) — اختياري', 'Location (search / QR / NFC) — optional')),
            maxLines: 1, overflow: TextOverflow.ellipsis,
            style: TextStyle(fontSize: 13, fontWeight: _locLabel != null ? FontWeight.w800 : FontWeight.w500,
                color: _locLabel != null ? _navy : Colors.grey.shade500),
          )),
          if (_locId != null)
            GestureDetector(onTap: () => setState(() { _locId = null; _locLabel = null; }),
                child: const Icon(Icons.close_rounded, size: 18, color: Colors.grey))
          else const Icon(Icons.chevron_left_rounded, color: Colors.grey),
        ]),
      ),
    );
  }

  Widget _mediaStrip() {
    return SizedBox(
      height: 84,
      child: ListView(scrollDirection: Axis.horizontal, children: [
        InkWell(
          onTap: _mediaMenu,
          borderRadius: BorderRadius.circular(12),
          child: Container(
            width: 84, height: 84,
            decoration: BoxDecoration(color: _accent.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(12),
                border: Border.all(color: _accent.withValues(alpha: 0.3))),
            child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
              const Icon(Icons.add_a_photo_rounded, color: _accent, size: 24),
              const SizedBox(height: 4),
              Text(tr('إضافة', 'Add'), style: const TextStyle(color: _accent, fontSize: 11, fontWeight: FontWeight.w800)),
            ]),
          ),
        ),
        for (var i = 0; i < _media.length; i++)
          Padding(
            padding: const EdgeInsets.only(right: 8),
            child: Stack(children: [
              Container(
                width: 84, height: 84,
                decoration: BoxDecoration(borderRadius: BorderRadius.circular(12), color: Colors.black12),
                clipBehavior: Clip.antiAlias,
                child: _media[i].isVideo
                    ? const Center(child: Icon(Icons.play_circle_fill_rounded, color: Color(0xFFE5484D), size: 34))
                    : Image.memory(base64Decode(_media[i].b64), fit: BoxFit.cover),
              ),
              Positioned(top: 2, right: 2, child: GestureDetector(
                onTap: () => setState(() => _media.removeAt(i)),
                child: Container(
                  decoration: const BoxDecoration(color: Colors.black54, shape: BoxShape.circle),
                  child: const Icon(Icons.close_rounded, color: Colors.white, size: 16),
                ),
              )),
              if (_media[i].isVideo)
                const Positioned(bottom: 2, left: 2, child: Icon(Icons.videocam_rounded, color: Colors.white, size: 15)),
            ]),
          ),
      ]),
    );
  }

  Widget _sevChip((String, String, String, Color) s) {
    final on = _sev == s.$1;
    return GestureDetector(
      onTap: () => setState(() => _sev = s.$1),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        margin: const EdgeInsets.symmetric(horizontal: 3),
        padding: const EdgeInsets.symmetric(vertical: 10),
        decoration: BoxDecoration(color: on ? s.$4 : Colors.white, borderRadius: BorderRadius.circular(11),
            border: Border.all(color: on ? s.$4 : Colors.grey.shade300)),
        child: Text(tr(s.$2, s.$3), textAlign: TextAlign.center,
            style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: on ? Colors.white : _navy)),
      ),
    );
  }

  Widget _lbl(IconData ic, String t) => Row(children: [
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
          focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: _accent, width: 1.5)),
        ),
      );

  Widget _dd<T>(String label, T value, List<DropdownMenuItem<T>> items, ValueChanged<T?> onCh) =>
      DropdownButtonFormField<T>(
        value: value, isExpanded: true,
        decoration: InputDecoration(labelText: label, filled: true, fillColor: Colors.white,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300))),
        items: items, onChanged: onCh,
      );
}
