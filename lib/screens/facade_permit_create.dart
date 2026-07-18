import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';

/// Client issues a height-work permit: pick facility + elevation, set the safety
/// pre-requisites (risk assessment, equipment check), record wind vs the safe
/// limit (live safe/unsafe read-out), assign the crew, and submit for approval.
class FacadePermitCreateSheet extends StatefulWidget {
  const FacadePermitCreateSheet({super.key});

  static Future<bool?> open(BuildContext context) => showModalBottomSheet<bool>(
        context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
        builder: (_) => const FacadePermitCreateSheet(),
      );

  @override
  State<FacadePermitCreateSheet> createState() => _FacadePermitCreateSheetState();
}

class _FacadePermitCreateSheetState extends State<FacadePermitCreateSheet> {
  Map<String, dynamic>? _opts;
  String? _error;
  int? _facilityId;
  int? _zoneId;
  double _validHours = 6;
  double _windSpeed = 0;
  double _windLimit = 40;
  bool _risk = false;
  bool _equip = false;
  final Set<int> _workers = {};
  bool _submitting = false;

  static const _c = Color(0xFF7C3AED);
  static const _navy = Color(0xFF0E3A5F);

  @override
  void initState() {
    super.initState();
    _loadOptions();
  }

  Future<void> _loadOptions() async {
    try {
      final o = await context.read<AuthProvider>().api.clientFacadeOptions();
      if (!mounted) return;
      setState(() {
        _opts = o;
        final facs = (o['facilities'] as List?) ?? const [];
        if (facs.isNotEmpty) _facilityId = facs.first['id'] as int;
        _windLimit = ((o['wind_limit_default'] ?? 40) as num).toDouble();
      });
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  List<Map> get _zones {
    final z = (_opts?['zones'] as List?)?.cast<Map>() ?? const [];
    return z.where((x) => _facilityId == null || x['facility_id'] == _facilityId).toList();
  }

  bool get _safe => _windSpeed <= _windLimit;

  Future<void> _submit() async {
    if (_facilityId == null) { _snack(tr('اختر المرفق', 'Choose a facility')); return; }
    setState(() => _submitting = true);
    final body = <String, dynamic>{
      'facility_id': _facilityId,
      'zone_id': _zoneId,
      'valid_hours': _validHours,
      'wind_speed': _windSpeed,
      'wind_limit': _windLimit,
      'risk_assessed': _risk,
      'equipment_checked': _equip,
      'worker_ids': _workers.toList(),
    };
    try {
      final r = await context.read<AuthProvider>().api.clientFacadePermitCreate(body);
      if (!mounted) return;
      Navigator.pop(context, true);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(tr('تم إصدار التصريح ${r['name'] ?? ''} (${r['state_label'] ?? ''})',
            'Permit ${r['name'] ?? ''} issued (${r['state_label'] ?? ''})')),
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
                  colors: [Color.lerp(_c, Colors.white, 0.1)!, Color.lerp(_c, Colors.black, 0.3)!],
                  begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Column(children: [
                Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
                Row(children: [
                  Container(width: 42, height: 42, alignment: Alignment.center,
                      decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(12)),
                      child: const Icon(Icons.health_and_safety_rounded, color: Colors.white, size: 22)),
                  const SizedBox(width: 12),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(tr('إصدار تصريح عمل على ارتفاع', 'Issue height-work permit'),
                        style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
                    Text(tr('مع قفل السلامة حسب الرياح', 'With wind safety lockout'),
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
              style: FilledButton.styleFrom(backgroundColor: _safe ? _c : const Color(0xFFE11D48),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
              onPressed: _submitting ? null : _submit,
              icon: _submitting
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : Icon(_safe ? Icons.verified_user_rounded : Icons.warning_amber_rounded),
              label: Text(_safe ? tr('إصدار التصريح', 'Issue permit') : tr('إصدار (رياح غير آمنة)', 'Issue (wind unsafe)'),
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
            )),
          )),
        ]),
      ),
    );
  }

  List<Widget> _form() {
    return [
      _label(Icons.apartment_rounded, tr('المرفق والواجهة', 'Facility & elevation')),
      const SizedBox(height: 8),
      _dd<int?>(tr('المرفق', 'Facility'), _facilityId,
          [for (final f in (_opts!['facilities'] as List).cast<Map>()) DropdownMenuItem(value: f['id'] as int, child: Text('${f['name']}'))],
          (v) => setState(() { _facilityId = v; _zoneId = null; })),
      if (_zones.isNotEmpty) ...[
        const SizedBox(height: 10),
        _dd<int?>(tr('الواجهة (اختياري)', 'Elevation (optional)'), _zoneId,
            [const DropdownMenuItem(value: null, child: Text('—')),
             for (final z in _zones) DropdownMenuItem(value: z['id'] as int, child: Text('${z['name']} · ${z['method_label'] ?? ''}'))],
            (v) => setState(() => _zoneId = v)),
      ],
      const SizedBox(height: 16),
      _label(Icons.air_rounded, tr('السلامة والرياح', 'Safety & wind')),
      const SizedBox(height: 8),
      // live safe/unsafe banner
      Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: (_safe ? const Color(0xFF16A34A) : const Color(0xFFE11D48)).withValues(alpha: 0.1),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: (_safe ? const Color(0xFF16A34A) : const Color(0xFFE11D48)).withValues(alpha: 0.3)),
        ),
        child: Row(children: [
          Icon(_safe ? Icons.check_circle_rounded : Icons.dangerous_rounded,
              color: _safe ? const Color(0xFF16A34A) : const Color(0xFFE11D48)),
          const SizedBox(width: 10),
          Expanded(child: Text(
              _safe ? tr('الرياح ضمن الحدّ الآمن', 'Wind within safe limit')
                    : tr('الرياح تتجاوز الحدّ الآمن — لن يُعتمد', 'Wind exceeds safe limit — will not approve'),
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5,
                  color: _safe ? const Color(0xFF16A34A) : const Color(0xFFE11D48)))),
          Text('${_windSpeed.round()}/${_windLimit.round()}',
              style: TextStyle(fontWeight: FontWeight.w900, color: _safe ? const Color(0xFF16A34A) : const Color(0xFFE11D48))),
        ]),
      ),
      const SizedBox(height: 8),
      _slider(tr('سرعة الرياح (كم/س)', 'Wind speed (km/h)'), _windSpeed, 0, 100, (v) => setState(() => _windSpeed = v)),
      _slider(tr('الحدّ الآمن (كم/س)', 'Safe limit (km/h)'), _windLimit, 10, 80, (v) => setState(() => _windLimit = v)),
      _slider(tr('صلاحية التصريح (ساعات)', 'Valid for (hours)'), _validHours, 1, 12, (v) => setState(() => _validHours = v)),
      const SizedBox(height: 8),
      _check(tr('تقييم المخاطر مُرفق', 'Risk assessment attached'), _risk, (v) => setState(() => _risk = v)),
      _check(tr('فحص المعدّات/الحبال', 'Equipment/ropes checked'), _equip, (v) => setState(() => _equip = v)),
      if (!(_risk && _equip))
        Padding(padding: const EdgeInsets.only(top: 4, right: 4), child: Text(
            tr('ملاحظة: يُقدَّم التصريح للاعتماد بعد تأكيد تقييم المخاطر وفحص المعدّات.',
               'Note: the permit is submitted for approval once both safety checks are confirmed.'),
            style: TextStyle(fontSize: 10.5, color: Colors.grey.shade600))),
      const SizedBox(height: 16),
      _label(Icons.groups_rounded, tr('طاقم العمل', 'Work crew')),
      const SizedBox(height: 8),
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final w in (_opts!['workers'] as List).cast<Map>())
          FilterChip(
            selected: _workers.contains(w['id']),
            label: Text('${w['name']}', style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
            selectedColor: _c.withValues(alpha: 0.15),
            checkmarkColor: _c,
            onSelected: (on) => setState(() => on ? _workers.add(w['id'] as int) : _workers.remove(w['id'])),
          ),
      ]),
      const SizedBox(height: 8),
    ];
  }

  Widget _label(IconData ic, String t) => Row(children: [
        Icon(ic, size: 16, color: _c),
        const SizedBox(width: 7),
        Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
      ]);

  Widget _dd<T>(String label, T value, List<DropdownMenuItem<T>> items, ValueChanged<T?> onCh) =>
      DropdownButtonFormField<T>(
        value: value, isExpanded: true,
        decoration: InputDecoration(labelText: label, filled: true, fillColor: Colors.white,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300))),
        items: items, onChanged: onCh,
      );

  Widget _slider(String label, double v, double min, double max, ValueChanged<double> onCh) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Text(label, style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700)),
            const Spacer(),
            Text('${v.round()}', style: const TextStyle(fontWeight: FontWeight.w900, color: _c)),
          ]),
          Slider(value: v.clamp(min, max), min: min, max: max, activeColor: _c,
              divisions: (max - min).round(), onChanged: onCh),
        ]),
      );

  Widget _check(String label, bool v, ValueChanged<bool> onCh) => CheckboxListTile(
        value: v, onChanged: (x) => onCh(x ?? false),
        activeColor: _c, contentPadding: EdgeInsets.zero, dense: true,
        controlAffinity: ListTileControlAffinity.leading,
        title: Text(label, style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
      );
}
