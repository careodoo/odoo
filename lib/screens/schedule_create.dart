import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';

/// Client adds a recurring work schedule: name, facility+location, service,
/// assigned worker, repeat interval, working window, and proof requirements.
class ScheduleCreateSheet extends StatefulWidget {
  const ScheduleCreateSheet({super.key});

  static Future<bool?> open(BuildContext context) => showModalBottomSheet<bool>(
        context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
        builder: (_) => const ScheduleCreateSheet(),
      );

  @override
  State<ScheduleCreateSheet> createState() => _ScheduleCreateSheetState();
}

class _ScheduleCreateSheetState extends State<ScheduleCreateSheet> {
  Map<String, dynamic>? _opts;
  String? _error;
  final _name = TextEditingController();
  int? _facilityId;
  int? _locationId;
  int? _serviceId;
  int? _workerId;
  double _every = 60;
  RangeValues _window = const RangeValues(7, 19);
  bool _presence = true;
  bool _photo = true;
  bool _submitting = false;

  static const _c = Color(0xFF0D9488);
  static const _navy = Color(0xFF0E3A5F);

  @override
  void initState() {
    super.initState();
    _loadOptions();
  }

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  Future<void> _loadOptions() async {
    try {
      final o = await context.read<AuthProvider>().api.clientScheduleOptions();
      if (!mounted) return;
      setState(() {
        _opts = o;
        final facs = (o['facilities'] as List?) ?? const [];
        if (facs.isNotEmpty) _facilityId = facs.first['id'] as int;
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

  Future<void> _submit() async {
    if (_name.text.trim().isEmpty) { _snack(tr('أدخل اسم الجدول', 'Enter a name')); return; }
    if (_serviceId == null) { _snack(tr('اختر الخدمة', 'Choose a service')); return; }
    if (_workerId == null) { _snack(tr('اختر العامل المسنَد', 'Choose the assigned worker')); return; }
    setState(() => _submitting = true);
    final body = <String, dynamic>{
      'name': _name.text.trim(), 'facility_id': _facilityId, 'location_id': _locationId,
      'service_id': _serviceId, 'employee_id': _workerId,
      'every_minutes': _every.round(),
      'window_start': _window.start, 'window_end': _window.end,
      'require_presence': _presence, 'require_photo': _photo,
    };
    try {
      await context.read<AuthProvider>().api.clientScheduleCreate(body);
      if (!mounted) return;
      Navigator.pop(context, true);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(tr('تم إنشاء الجدول', 'Schedule created')),
        backgroundColor: const Color(0xFF16A34A), behavior: SnackBarBehavior.floating));
    } catch (e) {
      if (mounted) { setState(() => _submitting = false); _snack('$e'); }
    }
  }

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: _c, behavior: SnackBarBehavior.floating));

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.9, minChildSize: 0.5, maxChildSize: 0.96,
      builder: (_, sc) => Container(
        decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        clipBehavior: Clip.antiAlias,
        child: Column(children: [
          CustomPaint(
            painter: const BrandPattern(opacity: 0.07),
            child: Container(
              padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
              decoration: BoxDecoration(gradient: LinearGradient(
                  colors: [_c, Color.lerp(_c, Colors.black, 0.3)!], begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Column(children: [
                Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
                Row(children: [
                  Container(width: 42, height: 42, alignment: Alignment.center,
                      decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(12)),
                      child: const Icon(Icons.event_repeat_rounded, color: Colors.white, size: 22)),
                  const SizedBox(width: 12),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(tr('جدول عمل جديد', 'New work schedule'),
                        style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
                    Text(tr('مهمة متكررة مع إثبات تنفيذ', 'Recurring task with proof'),
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 11.5)),
                  ])),
                  IconButton(icon: const Icon(Icons.close_rounded, color: Colors.white), onPressed: () => Navigator.pop(context)),
                ]),
              ]),
            ),
          ),
          Expanded(child: _opts == null
              ? Center(child: _error != null ? Text(_error!, style: const TextStyle(color: Colors.grey)) : const CircularProgressIndicator(color: _c))
              : ListView(controller: sc, padding: const EdgeInsets.all(16), children: _form())),
          if (_opts != null) SafeArea(top: false, child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
            child: SizedBox(height: 52, child: FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: _c, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
              onPressed: _submitting ? null : _submit,
              icon: _submitting
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.check_rounded),
              label: Text(tr('إنشاء الجدول', 'Create schedule'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
            )),
          )),
        ]),
      ),
    );
  }

  List<Widget> _form() {
    final services = (_opts!['services'] as List?)?.cast<Map>() ?? const [];
    final workers = (_opts!['workers'] as List?)?.cast<Map>() ?? const [];
    return [
      _label(Icons.title_rounded, tr('اسم الجدول', 'Schedule name')),
      const SizedBox(height: 8),
      TextField(controller: _name, decoration: _deco(tr('مثال: تنظيف دورات المياه', 'e.g. Restroom cleaning'))),
      const SizedBox(height: 16),
      _label(Icons.apartment_rounded, tr('المرفق والموقع', 'Facility & location')),
      const SizedBox(height: 8),
      _dd<int?>(tr('المرفق', 'Facility'), _facilityId,
          [for (final f in (_opts!['facilities'] as List).cast<Map>()) DropdownMenuItem(value: f['id'] as int, child: Text('${f['name']}'))],
          (v) => setState(() { _facilityId = v; _locationId = null; })),
      if (_locations.isNotEmpty) ...[
        const SizedBox(height: 10),
        _dd<int?>(tr('الموقع (اختياري)', 'Location (optional)'), _locationId,
            [const DropdownMenuItem(value: null, child: Text('—')),
             for (final l in _locations) DropdownMenuItem(value: l['id'] as int, child: Text('${l['name']}'))],
            (v) => setState(() => _locationId = v)),
      ],
      const SizedBox(height: 16),
      _label(Icons.design_services_rounded, tr('الخدمة والمنفّذ', 'Service & worker')),
      const SizedBox(height: 8),
      _dd<int?>(tr('الخدمة', 'Service'), _serviceId,
          [const DropdownMenuItem(value: null, child: Text('—')),
           for (final s in services) DropdownMenuItem(value: s['id'] as int, child: Text('${s['name']}'))],
          (v) => setState(() => _serviceId = v)),
      const SizedBox(height: 10),
      _dd<int?>(tr('العامل المسنَد', 'Assigned worker'), _workerId,
          [const DropdownMenuItem(value: null, child: Text('—')),
           for (final w in workers) DropdownMenuItem(value: w['id'] as int, child: Text('${w['name']}${w['job'] != null ? ' · ${w['job']}' : ''}'))],
          (v) => setState(() => _workerId = v)),
      const SizedBox(height: 16),
      _label(Icons.repeat_rounded, tr('التكرار والنافذة', 'Repeat & window')),
      const SizedBox(height: 8),
      Row(children: [
        Text(tr('يتكرّر كل', 'Repeat every'), style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700)),
        const Spacer(),
        Text(tr('${_every.round()} دقيقة', '${_every.round()} min'), style: const TextStyle(fontWeight: FontWeight.w900, color: _c)),
      ]),
      Slider(value: _every, min: 15, max: 480, divisions: 31, activeColor: _c,
          label: '${_every.round()}', onChanged: (v) => setState(() => _every = v)),
      Row(children: [
        Text(tr('نافذة العمل', 'Working window'), style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700)),
        const Spacer(),
        Text('${_window.start.round()}:00 – ${_window.end.round()}:00', style: const TextStyle(fontWeight: FontWeight.w900, color: _c)),
      ]),
      RangeSlider(values: _window, min: 0, max: 24, divisions: 24, activeColor: _c,
          labels: RangeLabels('${_window.start.round()}:00', '${_window.end.round()}:00'),
          onChanged: (v) => setState(() => _window = v)),
      const SizedBox(height: 8),
      _check(tr('إثبات حضور (QR)', 'Presence proof (QR)'), _presence, (v) => setState(() => _presence = v)),
      _check(tr('صورة إثبات', 'Photo proof'), _photo, (v) => setState(() => _photo = v)),
      const SizedBox(height: 8),
    ];
  }

  Widget _label(IconData ic, String t) => Row(children: [
        Icon(ic, size: 16, color: _c),
        const SizedBox(width: 7),
        Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
      ]);

  InputDecoration _deco(String hint) => InputDecoration(
        hintText: hint, filled: true, fillColor: Colors.white,
        hintStyle: TextStyle(fontSize: 13, color: Colors.grey.shade400),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: _c, width: 1.5)),
      );

  Widget _dd<T>(String label, T value, List<DropdownMenuItem<T>> items, ValueChanged<T?> onCh) =>
      DropdownButtonFormField<T>(
        value: value, isExpanded: true,
        decoration: InputDecoration(labelText: label, filled: true, fillColor: Colors.white,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300))),
        items: items, onChanged: onCh,
      );

  Widget _check(String label, bool v, ValueChanged<bool> onCh) => CheckboxListTile(
        value: v, onChanged: (x) => onCh(x ?? false), activeColor: _c,
        contentPadding: EdgeInsets.zero, dense: true,
        controlAffinity: ListTileControlAffinity.leading,
        title: Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
      );
}
