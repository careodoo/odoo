import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'searchable_picker.dart';
import 'scan_screen.dart';

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
  int? _teamId;
  bool _assignTeam = false;      // a round is often owned by whoever is on shift
  final _every = TextEditingController(text: '1');
  String _unit = 'hour';
  final _remind = TextEditingController(text: '15');
  String _remindUnit = 'minute';
  bool _scanning = false;
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
    _every.dispose();
    _remind.dispose();
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
    if (_assignTeam ? _teamId == null : _workerId == null) {
      _snack(_assignTeam ? tr('اختر الفريق', 'Choose the team')
                         : tr('اختر العامل المسنَد', 'Choose the assigned worker'));
      return;
    }
    final every = int.tryParse(_every.text.trim()) ?? 0;
    if (every < 1) { _snack(tr('مدة التكرار غير صحيحة', 'Invalid repeat interval')); return; }
    setState(() => _submitting = true);
    final body = <String, dynamic>{
      'name': _name.text.trim(), 'facility_id': _facilityId, 'location_id': _locationId,
      'service_id': _serviceId,
      'employee_id': _assignTeam ? null : _workerId,
      'team_id': _assignTeam ? _teamId : null,
      'interval_value': every,
      'interval_unit': _unit,
      'remind_before': int.tryParse(_remind.text.trim()) ?? 0,
      'remind_unit': _remindUnit,
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
    final teams = (_opts!['teams'] as List?)?.cast<Map>() ?? const [];
    final iUnits = (_opts!['interval_units'] as List?)?.cast<Map>() ?? const [];
    final rUnits = (_opts!['remind_units'] as List?)?.cast<Map>() ?? const [];
    return [
      _label(Icons.title_rounded, tr('اسم الجدول', 'Schedule name')),
      const SizedBox(height: 8),
      TextField(controller: _name, decoration: _deco(tr('مثال: تنظيف دورات المياه', 'e.g. Restroom cleaning'))),
      const SizedBox(height: 16),
      _label(Icons.apartment_rounded, tr('المرفق والموقع', 'Facility & location')),
      const SizedBox(height: 8),
      SearchableField(
        label: tr('المرفق', 'Facility'), icon: Icons.apartment_rounded, value: _facilityId, accent: _c, allowClear: false,
        options: [for (final f in (_opts!['facilities'] as List).cast<Map>()) PickOption(value: f['id'], label: '${f['name']}')],
        onChanged: (v) => setState(() { _facilityId = v as int?; _locationId = null; }),
      ),
      if (_locations.isNotEmpty) ...[
        const SizedBox(height: 10),
        SearchableField(
          label: tr('الموقع (اختياري)', 'Location (optional)'), icon: Icons.pin_drop_rounded, value: _locationId, accent: _c,
          options: [for (final l in _locations) PickOption(value: l['id'], label: '${l['name']}')],
          onChanged: (v) => setState(() => _locationId = v as int?),
        ),
        const SizedBox(height: 8),
        // Picking the site you are standing in beats hunting for it in a list
        // of two hundred. The QR carries the location code, the tag its uid —
        // both already exist on the location record.
        SizedBox(width: double.infinity, child: OutlinedButton.icon(
          onPressed: _scanning ? null : _scanLocation,
          icon: const Icon(Icons.qr_code_scanner_rounded, size: 18),
          style: OutlinedButton.styleFrom(foregroundColor: _c,
              side: BorderSide(color: _c.withValues(alpha: 0.5)),
              padding: const EdgeInsets.symmetric(vertical: 12),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
          label: Text(tr('تحديد الموقع بمسح QR أو NFC', 'Set location by QR or NFC scan'),
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
        )),
      ],
      const SizedBox(height: 16),
      _label(Icons.design_services_rounded, tr('الخدمة والمنفّذ', 'Service & worker')),
      const SizedBox(height: 8),
      SearchableField(
        label: tr('الخدمة', 'Service'), icon: Icons.design_services_rounded, value: _serviceId, accent: _c,
        options: [for (final s in services) PickOption(value: s['id'], label: '${s['name']}')],
        onChanged: (v) => setState(() => _serviceId = v as int?),
      ),
      const SizedBox(height: 10),
      // Assign to a person or to a team — a recurring round usually belongs to
      // whoever is on shift, not to one named worker who may be on leave.
      SegmentedButton<bool>(
        segments: [
          ButtonSegment(value: false, icon: const Icon(Icons.person_rounded, size: 16),
              label: Text(tr('عامل', 'Worker'))),
          ButtonSegment(value: true, icon: const Icon(Icons.groups_rounded, size: 16),
              label: Text(tr('فريق', 'Team'))),
        ],
        selected: {_assignTeam},
        showSelectedIcon: false,
        style: ButtonStyle(visualDensity: VisualDensity.compact,
            textStyle: WidgetStateProperty.all(const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800))),
        onSelectionChanged: (v) => setState(() => _assignTeam = v.first),
      ),
      const SizedBox(height: 10),
      if (!_assignTeam)
        SearchableField(
          label: tr('العامل المسنَد', 'Assigned worker'), icon: Icons.person_rounded, value: _workerId, accent: _c,
          options: [for (final w in workers) PickOption(value: w['id'], label: '${w['name']}', sublabel: w['job'] != null ? '${w['job']}' : null)],
          onChanged: (v) => setState(() => _workerId = v as int?),
        )
      else
        SearchableField(
          label: tr('الفريق المسنَد', 'Assigned team'), icon: Icons.groups_rounded, value: _teamId, accent: _c,
          options: [for (final t in teams) PickOption(value: t['id'], label: '${t['name']}',
              sublabel: t['members'] != null ? tr('${t['members']} عضو', '${t['members']} members') : null)],
          onChanged: (v) => setState(() => _teamId = v as int?),
        ),
      const SizedBox(height: 16),
      _label(Icons.repeat_rounded, tr('التكرار والنافذة', 'Repeat & window')),
      const SizedBox(height: 8),
      // A cycle is a number AND a unit. Minutes-only forced "every 90 days" to
      // be typed as 129600 minutes, which nobody does correctly.
      Row(children: [
        Expanded(flex: 2, child: TextField(
          controller: _every, keyboardType: TextInputType.number,
          decoration: _deco(tr('يتكرّر كل', 'Repeat every')),
        )),
        const SizedBox(width: 9),
        Expanded(flex: 3, child: _unitDrop(iUnits, _unit, (v) => setState(() => _unit = v))),
      ]),
      const SizedBox(height: 14),
      _label(Icons.notifications_active_rounded, tr('التنبيه قبل الموعد', 'Remind before')),
      const SizedBox(height: 8),
      Row(children: [
        Expanded(flex: 2, child: TextField(
          controller: _remind, keyboardType: TextInputType.number,
          decoration: _deco(tr('نبّه قبل', 'Notify before')),
        )),
        const SizedBox(width: 9),
        Expanded(flex: 3, child: _unitDrop(rUnits, _remindUnit, (v) => setState(() => _remindUnit = v))),
      ]),
      const SizedBox(height: 6),
      Text(tr('اجعلها صفرًا لإلغاء التنبيه المسبق.', 'Set to zero for no advance reminder.'),
          style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
      const SizedBox(height: 12),
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

  Widget _unitDrop(List<Map> units, String value, ValueChanged<String> onCh) {
    final items = units.isNotEmpty
        ? units
        : const [{'code': 'minute', 'label': 'دقيقة'}, {'code': 'hour', 'label': 'ساعة'},
                 {'code': 'day', 'label': 'يوم'}, {'code': 'month', 'label': 'شهر'}];
    final codes = items.map((u) => '${u['code']}').toList();
    return DropdownButtonFormField<String>(
      initialValue: codes.contains(value) ? value : codes.first,
      decoration: _deco(''),
      items: [for (final u in items)
        DropdownMenuItem(value: '${u['code']}',
            child: Text('${u['label']}', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)))],
      onChanged: (v) { if (v != null) onCh(v); },
    );
  }

  /// Match a scanned payload against the loaded locations. The QR encodes the
  /// location's code; a tag reports its uid. Both are on the record already, so
  /// this resolves locally rather than costing a round trip.
  bool _applyScan(String raw, {required bool nfc}) {
    final v = raw.trim().toLowerCase();
    if (v.isEmpty) return false;
    for (final l in _locations) {
      final key = '${nfc ? (l['nfc_uid'] ?? '') : (l['code'] ?? '')}'.trim().toLowerCase();
      if (key.isNotEmpty && key == v) {
        setState(() => _locationId = l['id'] as int?);
        _snack(tr('الموقع: ${l['name']}', 'Location: ${l['name']}'));
        return true;
      }
    }
    return false;
  }

  /// ScanScreen already offers QR and NFC and is the screen workers know, so
  /// the form borrows it whole instead of reimplementing either reader.
  Future<void> _scanLocation() async {
    setState(() => _scanning = true);
    try {
      final code = await Navigator.push<String>(
          context, MaterialPageRoute(builder: (_) => const ScanScreen(returnCode: true)));
      if (code == null || !mounted) return;
      // A QR carries the location code, a tag its uid — try both.
      if (!_applyScan(code, nfc: false) && !_applyScan(code, nfc: true)) {
        _snack(tr('لا يطابق أي موقع في هذا المرفق', 'No location in this facility matches'));
      }
    } catch (e) {
      if (mounted) _snack('$e');
    } finally {
      if (mounted) setState(() => _scanning = false);
    }
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


  Widget _check(String label, bool v, ValueChanged<bool> onCh) => CheckboxListTile(
        value: v, onChanged: (x) => onCh(x ?? false), activeColor: _c,
        contentPadding: EdgeInsets.zero, dense: true,
        controlAffinity: ListTileControlAffinity.leading,
        title: Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
      );
}
