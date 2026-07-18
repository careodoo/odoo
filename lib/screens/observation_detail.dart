import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'media_viewer_screen.dart';

/// Quality-observation detail sheet: shows the full record with its photos &
/// videos, lets the client add more media, and either cancel the observation or
/// convert it into a corrective work order.
class ObservationDetailSheet extends StatefulWidget {
  const ObservationDetailSheet(this.id, {super.key});
  final int id;
  static Future<bool?> open(BuildContext c, int id) => showModalBottomSheet<bool>(
        context: c, isScrollControlled: true, backgroundColor: Colors.transparent,
        builder: (_) => ObservationDetailSheet(id),
      );
  @override
  State<ObservationDetailSheet> createState() => _ObservationDetailSheetState();
}

const _accent = Color(0xFF0EA5A4);
const _navy = Color(0xFF0E3A5F);
const _sevColors = {
  'low': Color(0xFF64748B), 'medium': Color(0xFF3B82F6), 'high': Color(0xFFF59E0B), 'critical': Color(0xFFE11D48),
};

class _ObservationDetailSheetState extends State<ObservationDetailSheet> {
  Map<String, dynamic>? _o;
  bool _busy = false;
  bool _changed = false;
  String? _token;
  final _picker = ImagePicker();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final api = context.read<AuthProvider>().api;
      final o = await api.observationDetail(widget.id);
      final t = await api.token;
      if (mounted) setState(() { _o = o; _token = t; });
    } catch (e) {
      if (mounted) _snack('$e');
    }
  }

  Future<void> _addMedia() async {
    final kind = await showModalBottomSheet<String>(context: context, builder: (_) => SafeArea(child: Wrap(children: [
      ListTile(leading: const Icon(Icons.photo_camera_rounded, color: _accent), title: Text(tr('التقاط صورة', 'Take photo')), onTap: () => Navigator.pop(context, 'cam_photo')),
      ListTile(leading: const Icon(Icons.videocam_rounded, color: Color(0xFFE5484D)), title: Text(tr('تسجيل فيديو', 'Record video')), onTap: () => Navigator.pop(context, 'cam_video')),
      ListTile(leading: const Icon(Icons.photo_library_rounded, color: Color(0xFF7C3AED)), title: Text(tr('صورة من المعرض', 'Photo from gallery')), onTap: () => Navigator.pop(context, 'gal_photo')),
      ListTile(leading: const Icon(Icons.video_library_rounded, color: Color(0xFF0891B2)), title: Text(tr('فيديو من المعرض', 'Video from gallery')), onTap: () => Navigator.pop(context, 'gal_video')),
    ])));
    if (kind == null) return;
    try {
      Map<String, dynamic>? item;
      if (kind.endsWith('photo')) {
        final x = await _picker.pickImage(source: kind.startsWith('cam') ? ImageSource.camera : ImageSource.gallery, imageQuality: 60, maxWidth: 1600);
        if (x == null) return;
        item = {'name': x.name, 'mimetype': 'image/jpeg', 'data': base64Encode(await x.readAsBytes())};
      } else {
        final x = await _picker.pickVideo(source: kind.startsWith('cam') ? ImageSource.camera : ImageSource.gallery, maxDuration: const Duration(seconds: 30));
        if (x == null) return;
        final b = await x.readAsBytes();
        if (b.length > 12 * 1024 * 1024) { _snack(tr('الفيديو كبير جداً (الحد 12 ميجا)', 'Video too large (max 12 MB)')); return; }
        item = {'name': x.name, 'mimetype': 'video/mp4', 'data': base64Encode(b)};
      }
      setState(() => _busy = true);
      await context.read<AuthProvider>().api.observationAddMedia(widget.id, [item]);
      _changed = true;
      await _load();
      if (mounted) { setState(() => _busy = false); _snack(tr('تمت إضافة الوسائط', 'Media added')); }
    } catch (e) {
      if (mounted) { setState(() => _busy = false); _snack('$e'); }
    }
  }

  Future<void> _cancel() async {
    if (!await _confirm(tr('إلغاء هذه الملاحظة؟', 'Cancel this observation?'))) return;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.observationCancel(widget.id);
      _changed = true;
      await _load();
      if (mounted) setState(() => _busy = false);
    } catch (e) {
      if (mounted) { setState(() => _busy = false); _snack('$e'); }
    }
  }

  Future<void> _convert() async {
    if (!await _confirm(tr('إنشاء أمر عمل تصحيحي من هذه الملاحظة؟', 'Create a corrective work order?'))) return;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.observationToWorkOrder(widget.id);
      _changed = true;
      await _load();
      if (mounted) { setState(() => _busy = false); _snack(tr('تم التحويل لأمر عمل', 'Converted to work order')); }
    } catch (e) {
      if (mounted) { setState(() => _busy = false); _snack('$e'); }
    }
  }

  Future<bool> _confirm(String msg) async => (await showDialog<bool>(context: context, builder: (c) => AlertDialog(
        title: Text(tr('تأكيد', 'Confirm')),
        content: Text(msg),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('تراجع', 'Back'))),
          FilledButton(style: FilledButton.styleFrom(backgroundColor: _accent), onPressed: () => Navigator.pop(c, true), child: Text(tr('تأكيد', 'Confirm'))),
        ],
      ))) ?? false;

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: _accent, behavior: SnackBarBehavior.floating));

  @override
  Widget build(BuildContext context) {
    final o = _o;
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.9, minChildSize: 0.5, maxChildSize: 0.96,
      builder: (_, sc) => Container(
        decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        clipBehavior: Clip.antiAlias,
        child: Column(children: [
          _header(o),
          Expanded(child: o == null
              ? const Center(child: CircularProgressIndicator(color: _accent))
              : ListView(controller: sc, padding: const EdgeInsets.all(16), children: _body(o))),
          if (o != null) _actions(o),
        ]),
      ),
    );
  }

  Widget _header(Map? o) {
    final sc = _sevColors['${o?['severity']}'] ?? _accent;
    return CustomPaint(painter: const BrandPattern(opacity: 0.06), child: Container(
      padding: const EdgeInsets.fromLTRB(20, 12, 12, 16),
      decoration: BoxDecoration(gradient: LinearGradient(colors: [sc, Color.lerp(sc, Colors.black, 0.4)!], begin: Alignment.topRight, end: Alignment.bottomLeft)),
      child: Column(children: [
        Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12), decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
        Row(children: [
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${o?['name'] ?? ''}', style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12, fontWeight: FontWeight.w700)),
            const SizedBox(height: 2),
            Text('${o?['title'] ?? tr('تفاصيل الملاحظة', 'Observation details')}', style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
          ])),
          IconButton(icon: const Icon(Icons.close_rounded, color: Colors.white), onPressed: () => Navigator.pop(context, _changed)),
        ]),
        if (o != null) Padding(padding: const EdgeInsets.only(top: 8), child: Row(children: [
          _hpill('${o['severity_label']}'), const SizedBox(width: 8), _hpill('${o['state_label']}'),
          if (o['workorder'] != null) ...[const SizedBox(width: 8), _hpill('🛠️ ${o['workorder']}')],
        ])),
      ]),
    ));
  }

  List<Widget> _body(Map o) {
    final media = (o['media'] as List?) ?? const [];
    return [
      _kv(Icons.apartment_rounded, tr('المرفق', 'Facility'), '${o['facility'] ?? '—'}'),
      if (o['location'] != null) _kv(Icons.pin_drop_rounded, tr('الموقع', 'Location'), '${o['location']}'),
      if (o['service'] != null) _kv(Icons.design_services_rounded, tr('الخدمة', 'Service'), '${o['service']}'),
      if (o['assignee'] != null) _kv(Icons.person_rounded, tr('المسؤول', 'Assignee'), '${o['assignee']}'),
      if (o['deadline'] != null) _kv(Icons.event_rounded, tr('الموعد النهائي', 'Deadline'), '${o['deadline']}'),
      if (o['raised_by'] != null) _kv(Icons.record_voice_over_rounded, tr('أبلغ عنها', 'Raised by'), '${o['raised_by']}'),
      const SizedBox(height: 10),
      if (o['description'] != null) _para(tr('الوصف', 'Description'), '${o['description']}'),
      const SizedBox(height: 6),
      Row(children: [
        Icon(Icons.perm_media_rounded, size: 17, color: _accent), const SizedBox(width: 7),
        Text(tr('الصور والفيديو', 'Photos & video'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
        const Spacer(),
        TextButton.icon(onPressed: _busy ? null : _addMedia, icon: const Icon(Icons.add_a_photo_rounded, size: 18, color: _accent),
            label: Text(tr('إضافة', 'Add'), style: const TextStyle(color: _accent, fontWeight: FontWeight.w900))),
      ]),
      const SizedBox(height: 6),
      _mediaGrid(media),
      const SizedBox(height: 20),
    ];
  }

  Widget _mediaGrid(List media) {
    if (media.isEmpty) {
      return Container(
        padding: const EdgeInsets.symmetric(vertical: 22), alignment: Alignment.center,
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.grey.shade200)),
        child: Text(tr('لا توجد وسائط — اضغط «إضافة»', 'No media — tap “Add”'), style: TextStyle(color: Colors.grey.shade500)),
      );
    }
    return Wrap(spacing: 8, runSpacing: 8, children: [
      for (var i = 0; i < media.length; i++) GestureDetector(
        onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) =>
            MediaViewerScreen(media: media.cast<Map>(), index: i, token: _token))),
        child: Container(
          width: 88, height: 88, clipBehavior: Clip.antiAlias,
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(12), color: Colors.black12),
          child: (media[i]['is_video'] == true)
              ? const Center(child: Icon(Icons.play_circle_fill_rounded, color: Color(0xFFE5484D), size: 34))
              : Image.network('${media[i]['thumb'] ?? media[i]['url']}',
                  fit: BoxFit.cover, headers: _token != null ? {'Authorization': 'Bearer $_token'} : null,
                  errorBuilder: (_, __, ___) => const Icon(Icons.broken_image_rounded, color: Colors.grey)),
        ),
      ),
    ]);
  }

  Widget _actions(Map o) {
    final canConvert = o['can_convert'] == true;
    final canCancel = o['can_cancel'] == true;
    return SafeArea(top: false, child: Padding(
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 12),
      child: _busy
          ? const Center(child: Padding(padding: EdgeInsets.all(8), child: CircularProgressIndicator(color: _accent)))
          : Row(children: [
              if (canCancel) Expanded(child: OutlinedButton.icon(
                style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFE5484D), minimumSize: const Size.fromHeight(50), side: const BorderSide(color: Color(0xFFE5484D))),
                onPressed: _cancel, icon: const Icon(Icons.block_rounded, size: 19),
                label: Text(tr('إلغاء', 'Cancel'), style: const TextStyle(fontWeight: FontWeight.w900)),
              )),
              if (canCancel && canConvert) const SizedBox(width: 10),
              if (canConvert) Expanded(flex: 2, child: FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: _accent, minimumSize: const Size.fromHeight(50)),
                onPressed: _convert, icon: const Icon(Icons.build_rounded, size: 19),
                label: Text(tr('تحويل لأمر عمل', 'To work order'), style: const TextStyle(fontWeight: FontWeight.w900)),
              )),
              if (!canConvert && !canCancel) Expanded(child: Center(
                child: Text(tr('لا إجراءات متاحة', 'No actions available'), style: TextStyle(color: Colors.grey.shade500)))),
            ]),
    ));
  }

  Widget _kv(IconData ic, String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(ic, size: 17, color: _accent), const SizedBox(width: 10),
          SizedBox(width: 96, child: Text(k, style: TextStyle(color: Colors.grey.shade600, fontSize: 12.5, fontWeight: FontWeight.w700))),
          Expanded(child: Text(v, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: _navy))),
        ]),
      );

  Widget _para(String t, String v) => Container(
        margin: const EdgeInsets.only(bottom: 8), padding: const EdgeInsets.all(12), width: double.infinity,
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.grey.shade200)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: _accent)),
          const SizedBox(height: 4),
          Text(v, style: const TextStyle(fontSize: 13, height: 1.4, color: _navy)),
        ]),
      );

  Widget _hpill(String t) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(20), border: Border.all(color: Colors.white.withValues(alpha: 0.5))),
        child: Text(t, style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w800)),
      );
}
