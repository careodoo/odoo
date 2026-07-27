import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// «سجل البوابة» (زوّار ومركبات) — تسجيل سريع للحارس لأي زائر/مركبة/توصيل/مقاول
/// عند البوابة: دخول فوري ثم خروج بضغطة. ترويسة إحصائيات (بالداخل الآن/دخول
/// اليوم/خروج اليوم) + تبويبات + قائمة + زر تسجيل خروج لكل مَن بالداخل.
class SecurityGateLogScreen extends StatefulWidget {
  const SecurityGateLogScreen({super.key});
  @override
  State<SecurityGateLogScreen> createState() => _SecurityGateLogScreenState();
}

class _SecurityGateLogScreenState extends State<SecurityGateLogScreen> {
  static const _navy = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);
  static const _green = Color(0xFF37C98A);
  static const _amber = Color(0xFFF7A23B);
  static const _blue = Color(0xFF4AA8FF);
  static const _red = Color(0xFFE5484D);

  String _tab = 'inside';
  Map<String, dynamic>? _d;
  bool _loading = true;

  static const _typeIcon = {
    'visitor': Icons.person_rounded,
    'vehicle': Icons.directions_car_rounded,
    'delivery': Icons.local_shipping_rounded,
    'contractor': Icons.engineering_rounded,
  };
  static const _typeColor = {
    'visitor': _blue, 'vehicle': _amber, 'delivery': _green, 'contractor': Color(0xFFB07CF0),
  };

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final d = await context.read<AuthProvider>().api.securityGateLog(tab: _tab);
      if (mounted) setState(() { _d = d; _loading = false; });
    } catch (_) { if (mounted) setState(() => _loading = false); }
  }

  Future<void> _exit(int id) async {
    try {
      await context.read<AuthProvider>().api.securityGateExit(id);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          backgroundColor: _green, content: Text(tr('تم تسجيل الخروج', 'Exit recorded'))));
      await _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(backgroundColor: _red, content: Text('$e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final items = ((_d?['items'] as List?) ?? const []).cast<Map>();
    final st = (_d?['stats'] as Map?)?.cast<String, dynamic>() ?? const {};
    return Scaffold(
      backgroundColor: _navy,
      appBar: AppBar(
        title: Text(tr('سجل البوابة', 'Gate register')),
        backgroundColor: _navy,
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))],
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: _green, onPressed: _openCreate,
        icon: const Icon(Icons.add_rounded), label: Text(tr('تسجيل دخول', 'Log entry'))),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Column(children: [
              // ترويسة الإحصائيات
              Padding(
                padding: const EdgeInsets.fromLTRB(12, 12, 12, 6),
                child: Row(children: [
                  _stat(tr('بالداخل الآن', 'Inside now'), st['inside'], _amber),
                  const SizedBox(width: 8),
                  _stat(tr('دخول اليوم', 'In today'), st['in_today'], _green),
                  const SizedBox(width: 8),
                  _stat(tr('خروج اليوم', 'Out today'), st['out_today'], _blue),
                ]),
              ),
              // تبويبات
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 12),
                child: Row(children: [
                  _tabBtn('inside', tr('بالداخل', 'Inside')),
                  const SizedBox(width: 8),
                  _tabBtn('today', tr('اليوم', 'Today')),
                  const SizedBox(width: 8),
                  _tabBtn('all', tr('الكل', 'All')),
                ]),
              ),
              const SizedBox(height: 6),
              Expanded(child: items.isEmpty
                  ? Center(child: Text(tr('لا سجلات', 'No records'), style: const TextStyle(color: _muted)))
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.builder(
                        padding: const EdgeInsets.fromLTRB(12, 4, 12, 90),
                        itemCount: items.length,
                        itemBuilder: (_, i) => _tile(items[i].cast<String, dynamic>()),
                      ),
                    )),
            ]),
    );
  }

  Widget _stat(String label, dynamic v, Color c) => Expanded(
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 12),
          decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(14)),
          child: Column(children: [
            Text('${v ?? 0}', style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 22)),
            const SizedBox(height: 2),
            Text(label, style: const TextStyle(color: _muted, fontSize: 11)),
          ]),
        ),
      );

  Widget _tabBtn(String v, String label) {
    final on = _tab == v;
    return Expanded(
      child: GestureDetector(
        onTap: () { setState(() => _tab = v); _load(); },
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 9),
          decoration: BoxDecoration(
            color: on ? _blue : _card, borderRadius: BorderRadius.circular(10)),
          child: Text(label, textAlign: TextAlign.center,
              style: TextStyle(color: on ? Colors.white : _muted, fontWeight: FontWeight.w700, fontSize: 12.5)),
        ),
      ),
    );
  }

  Widget _tile(Map<String, dynamic> e) {
    final type = (e['type'] ?? 'visitor') as String;
    final c = _typeColor[type] ?? _blue;
    final inside = e['state'] == 'inside';
    final isVehicle = type == 'vehicle' || (e['plate'] != null);
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(14)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(width: 40, height: 40,
              decoration: BoxDecoration(color: c.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(11)),
              child: Icon(_typeIcon[type] ?? Icons.person_rounded, color: c, size: 21)),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${e['person'] ?? e['type_label'] ?? ''}',
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 14)),
            const SizedBox(height: 2),
            Text([e['type_label'], if (e['company'] != null) e['company']].whereType<String>().join(' · '),
                style: const TextStyle(color: _muted, fontSize: 11.5)),
          ])),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
            decoration: BoxDecoration(
                color: (inside ? _amber : _green).withValues(alpha: 0.16), borderRadius: BorderRadius.circular(20)),
            child: Text(inside ? tr('بالداخل', 'Inside') : tr('غادر', 'Left'),
                style: TextStyle(color: inside ? _amber : _green, fontWeight: FontWeight.w700, fontSize: 11)),
          ),
        ]),
        const SizedBox(height: 8),
        Wrap(spacing: 6, runSpacing: 6, children: [
          if (isVehicle && e['plate'] != null) _chip('🚗 ${e['plate']}', _amber),
          if ((e['persons_count'] ?? 1) > 1) _chip('👥 ${e['persons_count']}', _blue),
          if (e['host'] != null) _chip('${tr('لزيارة', 'host')}: ${e['host']}', _muted),
          if (e['id_number'] != null) _chip('🆔 ${e['id_number']}', _muted),
        ]),
        if (e['purpose'] != null) ...[
          const SizedBox(height: 6),
          Text('${e['purpose']}', style: const TextStyle(color: _muted, fontSize: 12)),
        ],
        Row(children: [
          const Icon(Icons.login_rounded, color: _green, size: 14),
          const SizedBox(width: 3),
          Text('${e['in_time'] ?? ''}', style: const TextStyle(color: _muted, fontSize: 11)),
          if (e['out_time'] != null) ...[
            const SizedBox(width: 12),
            const Icon(Icons.logout_rounded, color: _blue, size: 14),
            const SizedBox(width: 3),
            Text('${e['out_time']}', style: const TextStyle(color: _muted, fontSize: 11)),
          ],
          const Spacer(),
          if (inside) FilledButton.icon(
            style: FilledButton.styleFrom(
                backgroundColor: _red.withValues(alpha: 0.16), foregroundColor: _red,
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 0),
                minimumSize: const Size(0, 34)),
            onPressed: () => _exit(e['id'] as int),
            icon: const Icon(Icons.logout_rounded, size: 16),
            label: Text(tr('خروج', 'Exit'), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12)),
          ),
        ]),
      ]),
    );
  }

  Widget _chip(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(8)),
        child: Text(t, style: TextStyle(color: c == _muted ? _muted : c, fontWeight: FontWeight.w600, fontSize: 10.5)),
      );

  Future<void> _openCreate() async {
    final ok = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => const _GateEntrySheet(),
    );
    if (ok == true) { setState(() => _tab = 'inside'); await _load(); }
  }
}

/// نموذج تسجيل دخول جديد.
class _GateEntrySheet extends StatefulWidget {
  const _GateEntrySheet();
  @override
  State<_GateEntrySheet> createState() => _GateEntrySheetState();
}

class _GateEntrySheetState extends State<_GateEntrySheet> {
  static const _navy = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);
  static const _green = Color(0xFF37C98A);
  static const _blue = Color(0xFF4AA8FF);
  static const _red = Color(0xFFE5484D);

  String _type = 'visitor';
  final _name = TextEditingController();
  final _idnum = TextEditingController();
  final _phone = TextEditingController();
  final _company = TextEditingController();
  final _host = TextEditingController();
  final _purpose = TextEditingController();
  final _plate = TextEditingController();
  final _count = TextEditingController(text: '1');
  bool _saving = false;

  static const _types = [
    ['visitor', 'زائر', 'Visitor', Icons.person_rounded],
    ['vehicle', 'مركبة', 'Vehicle', Icons.directions_car_rounded],
    ['delivery', 'توصيل', 'Delivery', Icons.local_shipping_rounded],
    ['contractor', 'مقاول', 'Contractor', Icons.engineering_rounded],
  ];

  @override
  void dispose() {
    for (final c in [_name, _idnum, _phone, _company, _host, _purpose, _plate, _count]) { c.dispose(); }
    super.dispose();
  }

  Future<void> _save() async {
    if (_name.text.trim().isEmpty && _plate.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          backgroundColor: _red, content: Text(tr('أدخل الاسم أو رقم اللوحة', 'Enter name or plate'))));
      return;
    }
    setState(() => _saving = true);
    try {
      await context.read<AuthProvider>().api.securityGateEntry({
        'entry_type': _type,
        'person_name': _name.text.trim(),
        'id_number': _idnum.text.trim(),
        'phone': _phone.text.trim(),
        'company': _company.text.trim(),
        'host_name': _host.text.trim(),
        'purpose': _purpose.text.trim(),
        'plate': _plate.text.trim(),
        'persons_count': int.tryParse(_count.text.trim()) ?? 1,
      });
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) {
        setState(() => _saving = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(backgroundColor: _red, content: Text('$e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final bottom = MediaQuery.of(context).viewInsets.bottom;
    final isVehicle = _type == 'vehicle';
    return Container(
      padding: EdgeInsets.fromLTRB(16, 14, 16, bottom + 16),
      decoration: const BoxDecoration(color: _navy, borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      child: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Center(child: Container(width: 40, height: 4, decoration: BoxDecoration(color: _muted.withValues(alpha: 0.4), borderRadius: BorderRadius.circular(4)))),
          const SizedBox(height: 14),
          Text(tr('تسجيل دخول عند البوابة', 'Log gate entry'),
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 16)),
          const SizedBox(height: 12),
          // نوع الدخول
          Row(children: _types.map((t) {
            final on = _type == t[0];
            return Expanded(child: Padding(
              padding: const EdgeInsets.only(right: 6),
              child: GestureDetector(
                onTap: () => setState(() => _type = t[0] as String),
                child: Container(
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  decoration: BoxDecoration(
                      color: on ? _blue : _card, borderRadius: BorderRadius.circular(11)),
                  child: Column(children: [
                    Icon(t[3] as IconData, color: on ? Colors.white : _muted, size: 20),
                    const SizedBox(height: 3),
                    Text(tr(t[1] as String, t[2] as String),
                        style: TextStyle(color: on ? Colors.white : _muted, fontSize: 10.5, fontWeight: FontWeight.w600)),
                  ]),
                ),
              ),
            ));
          }).toList()),
          const SizedBox(height: 12),
          _tf(_name, tr('الاسم', 'Name')),
          if (isVehicle) _tf(_plate, tr('رقم اللوحة', 'License plate')),
          Row(children: [
            Expanded(child: _tf(_idnum, tr('رقم الهوية', 'ID number'))),
            const SizedBox(width: 8),
            Expanded(child: _tf(_phone, tr('الهاتف', 'Phone'), number: true)),
          ]),
          _tf(_company, tr('الجهة/الشركة', 'Company')),
          _tf(_host, tr('المُستضيف (لزيارة من؟)', 'Host')),
          _tf(_purpose, tr('الغرض', 'Purpose')),
          _tf(_count, tr('عدد الأشخاص', 'Persons count'), number: true),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity, height: 50,
            child: FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: _green),
              onPressed: _saving ? null : _save,
              icon: _saving
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.login_rounded),
              label: Text(tr('تسجيل الدخول', 'Log entry'), style: const TextStyle(fontWeight: FontWeight.w800)),
            ),
          ),
        ]),
      ),
    );
  }

  Widget _tf(TextEditingController c, String hint, {bool number = false}) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: TextField(
          controller: c,
          keyboardType: number ? TextInputType.number : TextInputType.text,
          style: const TextStyle(color: Colors.white, fontSize: 13.5),
          decoration: InputDecoration(
            hintText: hint, hintStyle: const TextStyle(color: _muted, fontSize: 12.5),
            filled: true, fillColor: _card,
            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 13),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(11), borderSide: BorderSide.none),
          ),
        ),
      );
}
