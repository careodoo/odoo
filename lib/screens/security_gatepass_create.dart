import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';

/// Client issues a gate pass — personal (visitor) or vehicle — for their
/// premise. Starts as draft for the security team to approve.
class SecurityGatepassCreateSheet extends StatefulWidget {
  const SecurityGatepassCreateSheet({super.key});

  static Future<bool?> open(BuildContext context) => showModalBottomSheet<bool>(
        context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
        builder: (_) => const SecurityGatepassCreateSheet(),
      );

  @override
  State<SecurityGatepassCreateSheet> createState() => _SecurityGatepassCreateSheetState();
}

class _SecurityGatepassCreateSheetState extends State<SecurityGatepassCreateSheet> {
  Map<String, dynamic>? _opts;
  String? _error;
  int? _clientId;
  int? _premiseId;
  String _passType = 'personal';
  DateTime _from = DateTime.now();
  DateTime _to = DateTime.now().add(const Duration(days: 1));
  final _purpose = TextEditingController();
  final _person = TextEditingController();
  final _idNumber = TextEditingController();
  final _phone = TextEditingController();
  final _company = TextEditingController();
  bool _submitting = false;

  static const _c = Color(0xFFE5484D);
  static const _navy = Color(0xFF0E3A5F);

  @override
  void initState() {
    super.initState();
    _loadOptions();
  }

  @override
  void dispose() {
    for (final c in [_purpose, _person, _idNumber, _phone, _company]) { c.dispose(); }
    super.dispose();
  }

  Future<void> _loadOptions() async {
    try {
      final o = await context.read<AuthProvider>().api.clientSecurityOptions();
      if (!mounted) return;
      setState(() {
        _opts = o;
        final clients = (o['clients'] as List?) ?? const [];
        if (clients.isNotEmpty) _clientId = clients.first['id'] as int;
        final prem = (o['premises'] as List?) ?? const [];
        if (prem.isNotEmpty) _premiseId = prem.first['id'] as int;
      });
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  Future<void> _pickDate(bool from) async {
    final d = await showDatePicker(
      context: context, initialDate: from ? _from : _to,
      firstDate: DateTime.now().subtract(const Duration(days: 1)),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (d == null) return;
    setState(() {
      if (from) { _from = d; if (_to.isBefore(_from)) _to = _from.add(const Duration(days: 1)); }
      else { _to = d; }
    });
  }

  String _fmt(DateTime d) => '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  Future<void> _submit() async {
    if (_purpose.text.trim().isEmpty) { _snack(tr('أدخل الغرض', 'Enter purpose')); return; }
    if (_passType == 'personal' && _person.text.trim().isEmpty) { _snack(tr('أدخل اسم الزائر', 'Enter visitor name')); return; }
    setState(() => _submitting = true);
    final body = <String, dynamic>{
      'client_id': _clientId, 'premise_id': _premiseId,
      'pass_type': _passType, 'purpose': _purpose.text.trim(),
      'start_date': _fmt(_from), 'end_date': _fmt(_to),
      if (_passType == 'personal') 'person_name': _person.text.trim(),
      if (_passType == 'personal') 'id_number': _idNumber.text.trim(),
      if (_passType == 'personal') 'phone': _phone.text.trim(),
      if (_passType == 'personal') 'company': _company.text.trim(),
    };
    try {
      final r = await context.read<AuthProvider>().api.clientSecurityGatepassCreate(body);
      if (!mounted) return;
      Navigator.pop(context, true);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(tr('تم إصدار التصريح ${r['name'] ?? ''}', 'Gate pass ${r['name'] ?? ''} issued')),
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
                  colors: [Color.lerp(_c, Colors.white, 0.1)!, Color.lerp(_c, Colors.black, 0.3)!],
                  begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Column(children: [
                Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
                Row(children: [
                  Container(width: 42, height: 42, alignment: Alignment.center,
                      decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(12)),
                      child: const Icon(Icons.confirmation_number_rounded, color: Colors.white, size: 22)),
                  const SizedBox(width: 12),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(tr('إصدار تصريح دخول', 'Issue gate pass'),
                        style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
                    Text(tr('لزائر أو مركبة — يُعتمد من الأمن', 'Visitor or vehicle — security approves'),
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
                  : const Icon(Icons.confirmation_number_rounded),
              label: Text(tr('إصدار التصريح', 'Issue pass'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
            )),
          )),
        ]),
      ),
    );
  }

  List<Widget> _form() {
    final prem = (_opts!['premises'] as List?)?.cast<Map>() ?? const [];
    return [
      _label(Icons.category_rounded, tr('نوع التصريح', 'Pass type')),
      const SizedBox(height: 8),
      Row(children: [
        _typeChip('personal', Icons.person_rounded, tr('زائر', 'Visitor')),
        const SizedBox(width: 8),
        _typeChip('vehicle', Icons.directions_car_rounded, tr('مركبة', 'Vehicle')),
      ]),
      if (prem.isNotEmpty) ...[
        const SizedBox(height: 16),
        _label(Icons.location_on_rounded, tr('الموقع', 'Premise')),
        const SizedBox(height: 8),
        _dd<int?>(tr('المنشأة', 'Premise'), _premiseId,
            [for (final p in prem) DropdownMenuItem(value: p['id'] as int, child: Text('${p['name']}'))],
            (v) => setState(() => _premiseId = v)),
      ],
      const SizedBox(height: 16),
      _label(Icons.date_range_rounded, tr('مدة الصلاحية', 'Validity')),
      const SizedBox(height: 8),
      Row(children: [
        Expanded(child: _dateBtn(tr('من', 'From'), _from, () => _pickDate(true))),
        const SizedBox(width: 10),
        Expanded(child: _dateBtn(tr('إلى', 'To'), _to, () => _pickDate(false))),
      ]),
      if (_passType == 'personal') ...[
        const SizedBox(height: 16),
        _label(Icons.badge_rounded, tr('بيانات الزائر', 'Visitor details')),
        const SizedBox(height: 8),
        _field(_person, tr('اسم الزائر', 'Visitor name'), Icons.person_outline_rounded),
        const SizedBox(height: 10),
        Row(children: [
          Expanded(child: _field(_idNumber, tr('رقم الهوية', 'ID number'), Icons.credit_card_rounded)),
          const SizedBox(width: 10),
          Expanded(child: _field(_phone, tr('الهاتف', 'Phone'), Icons.phone_rounded, number: true)),
        ]),
        const SizedBox(height: 10),
        _field(_company, tr('الجهة/الشركة', 'Company'), Icons.business_rounded),
      ],
      const SizedBox(height: 16),
      _label(Icons.notes_rounded, tr('الغرض', 'Purpose')),
      const SizedBox(height: 8),
      _field(_purpose, tr('غرض الزيارة/الدخول', 'Purpose of visit/entry'), Icons.edit_rounded, lines: 3),
      const SizedBox(height: 8),
    ];
  }

  Widget _typeChip(String v, IconData ic, String label) {
    final on = _passType == v;
    return Expanded(child: GestureDetector(
      onTap: () => setState(() => _passType = v),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: on ? _c : Colors.white, borderRadius: BorderRadius.circular(12),
          border: Border.all(color: on ? _c : Colors.grey.shade300)),
        child: Column(children: [
          Icon(ic, size: 20, color: on ? Colors.white : _c),
          const SizedBox(height: 4),
          Text(label, style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: on ? Colors.white : _navy)),
        ]),
      ),
    ));
  }

  Widget _dateBtn(String label, DateTime d, VoidCallback onTap) => InkWell(
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.grey.shade300)),
          child: Row(children: [
            const Icon(Icons.event_rounded, size: 16, color: _navy),
            const SizedBox(width: 8),
            Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(label, style: TextStyle(fontSize: 10, color: Colors.grey.shade500, fontWeight: FontWeight.w600)),
              Text(_fmt(d), style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w800)),
            ]),
          ]),
        ),
      );

  Widget _label(IconData ic, String t) => Row(children: [
        Icon(ic, size: 16, color: _c),
        const SizedBox(width: 7),
        Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
      ]);

  Widget _field(TextEditingController c, String label, IconData ic, {int lines = 1, bool number = false}) => TextField(
        controller: c, maxLines: lines,
        keyboardType: number ? TextInputType.phone : TextInputType.text,
        decoration: InputDecoration(
          labelText: label, prefixIcon: Icon(ic, size: 19), filled: true, fillColor: Colors.white,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: _c, width: 1.5)),
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
