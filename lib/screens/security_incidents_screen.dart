import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';
import 'dart:convert';
import 'package:provider/provider.dart';
import '../core/auth.dart';
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
    final sev = i['severity'] as String? ?? 'low';
    final entries = i.entries.where((e) =>
        e.key != 'id' && e.value != null && '${e.value}'.trim().isNotEmpty).toList();
    final labels = {'name': 'المرجع', 'type': 'النوع', 'severity': 'الخطورة', 'description': 'الوصف',
        'premise': 'الموقع', 'location': 'المكان', 'guard': 'الحارس', 'date': 'التاريخ',
        'state': 'الحالة', 'reported_by': 'المُبلِّغ', 'action': 'الإجراء', 'note': tr('ملاحظة', 'Note')};
    showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.6, minChildSize: 0.4, maxChildSize: 0.92,
        builder: (_, sc) => Container(
          decoration: const BoxDecoration(color: Color(0xFF0F1B2E), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
          clipBehavior: Clip.antiAlias,
          child: Column(children: [
            Container(
              padding: const EdgeInsets.fromLTRB(20, 14, 20, 16),
              decoration: BoxDecoration(gradient: LinearGradient(colors: [_sevColor(sev), Color.lerp(_sevColor(sev), Colors.black, 0.45)!], begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Column(children: [
                Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12), decoration: BoxDecoration(color: Colors.white38, borderRadius: BorderRadius.circular(3)))),
                Row(children: [
                  const Icon(Icons.warning_amber_rounded, color: Colors.white),
                  const SizedBox(width: 10),
                  Expanded(child: Text('${i['name'] ?? ''}', style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900))),
                  Text('${severities[sev] ?? sev}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800)),
                ]),
              ]),
            ),
            Expanded(child: ListView(controller: sc, padding: const EdgeInsets.all(16), children: [
              // Evidence bar: a typed report is what the reporter remembers,
              // not what happened. Photo, location and updates are what an
              // insurer or a dispute will actually ask for.
              Wrap(spacing: 8, runSpacing: 8, children: [
                _evBtn(Icons.photo_camera_rounded, tr('صورة', 'Photo'),
                    () => _addPhoto(intOf(i['id']))),
                _evBtn(Icons.my_location_rounded, tr('الموقع', 'Location'),
                    () => _captureLocation(intOf(i['id']))),
                _evBtn(Icons.note_add_rounded, tr('تحديث', 'Update'),
                    () => _addUpdate(intOf(i['id']))),
                _evBtn(Icons.build_rounded, tr('أمر عمل', 'Work order'),
                    () => _escalate(intOf(i['id']))),
              ]),
              const Divider(color: Colors.white24, height: 24),
              for (final e in entries) Padding(
                padding: const EdgeInsets.symmetric(vertical: 7),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  SizedBox(width: 110, child: Text(labels[e.key] ?? e.key, style: const TextStyle(color: Color(0xFF9CB2CD), fontSize: 12.5, fontWeight: FontWeight.w700))),
                  Expanded(child: Text(e.key == 'type' ? '${types[e.value] ?? e.value}' : (e.key == 'severity' ? '${severities[e.value] ?? e.value}' : '${e.value}'),
                      style: const TextStyle(color: Colors.white, fontSize: 13.5, fontWeight: FontWeight.w700))),
                ]),
              ),
            ])),
          ]),
        ),
      ),
    );
  }

  Widget _evBtn(IconData ic, String label, VoidCallback onTap) => OutlinedButton.icon(
        onPressed: onTap,
        icon: Icon(ic, size: 17, color: Colors.white),
        style: OutlinedButton.styleFrom(
            foregroundColor: Colors.white,
            side: const BorderSide(color: Colors.white38),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(11))),
        label: Text(label, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800)),
      );

  void _snack(String m, [Color? c]) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: c, behavior: SnackBarBehavior.floating));

  Future<void> _addPhoto(int id) async {
    try {
      final x = await ImagePicker().pickImage(
          source: ImageSource.camera, maxWidth: 1600, imageQuality: 70);
      if (x == null) return;
      final bytes = await x.readAsBytes();
      await context.read<AuthProvider>().api.incidentMedia(id, {
        'kind': 'photo', 'file': base64Encode(bytes), 'filename': x.name,
      });
      if (mounted) _snack(tr('أُضيفت الصورة للبلاغ', 'Photo attached'), const Color(0xFF16A34A));
    } catch (e) {
      if (mounted) _snack('$e', const Color(0xFFE11D48));
    }
  }

  Future<void> _captureLocation(int id) async {
    try {
      final ok = await Geolocator.checkPermission();
      if (ok == LocationPermission.denied) {
        await Geolocator.requestPermission();
      }
      final pos = await Geolocator.getCurrentPosition();
      await context.read<AuthProvider>().api.incidentLocate(id, pos.latitude, pos.longitude);
      if (mounted) _snack(tr('سُجّل موقع البلاغ', 'Location captured'), const Color(0xFF16A34A));
    } catch (e) {
      if (mounted) _snack('$e', const Color(0xFFE11D48));
    }
  }

  Future<void> _addUpdate(int id) async {
    final ctrl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text(tr('إضافة تحديث', 'Add update')),
        content: TextField(controller: ctrl, maxLines: 3, autofocus: true,
            decoration: InputDecoration(
                hintText: tr('ما الذي حدث بعد ذلك؟', 'What happened next?'),
                border: const OutlineInputBorder())),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: Text(tr('إضافة', 'Add'))),
        ],
      ),
    );
    if (ok != true || ctrl.text.trim().isEmpty) return;
    try {
      await context.read<AuthProvider>().api.incidentUpdate(id, ctrl.text.trim());
      if (mounted) _snack(tr('أُضيف التحديث', 'Update added'), const Color(0xFF16A34A));
    } catch (e) {
      if (mounted) _snack('$e', const Color(0xFFE11D48));
    }
  }

  Future<void> _escalate(int id) async {
    try {
      final r = await context.read<AuthProvider>().api.incidentToWorkorder(id);
      if (mounted) _snack('${tr('أُنشئ أمر العمل', 'Work order raised')}: ${r['workorder']}',
          const Color(0xFF16A34A));
    } catch (e) {
      if (mounted) _snack('$e', const Color(0xFFE11D48));
    }
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
