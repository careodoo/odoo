// شاشتا صيانة المركبات + بترول استيشن لمدير المشروع.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'pms_shell.dart';

// ========================= صيانة المركبات =========================
class VehicleServicesScreen extends StatefulWidget {
  const VehicleServicesScreen({super.key});
  @override
  State<VehicleServicesScreen> createState() => _VehicleServicesScreenState();
}

class _VehicleServicesScreenState extends State<VehicleServicesScreen> {
  late Future<Map<String, dynamic>> _f;
  @override
  void initState() { super.initState(); _reload(); }
  void _reload() { _f = context.read<AuthProvider>().api.pmsVehicles(); }

  Color _stC(String s) => s == 'done' ? Pms.green : s == 'cancelled' ? Pms.slate : Pms.amber;

  Future<void> _report(Map r) async {
    final api = context.read<AuthProvider>().api;
    final t = await api.token;
    await launchUrl(Uri.parse('${api.baseUrl}${api.pmsVehicleReportPath(r['id'] as int)}?token=${t ?? ''}'),
        mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: gIsRtl ? TextDirection.rtl : TextDirection.ltr,
      child: Scaffold(
        backgroundColor: Pms.bg,
        appBar: AppBar(title: Text(tr('صيانة المركبات', 'Vehicle Services')),
            backgroundColor: Pms.violet, foregroundColor: Colors.white),
        floatingActionButton: FloatingActionButton.extended(
          backgroundColor: Pms.violet, icon: const Icon(Icons.add, color: Colors.white),
          label: Text(tr('تسجيل صيانة', 'New service'), style: const TextStyle(color: Colors.white)),
          onPressed: _openCreate),
        body: FutureBuilder<Map<String, dynamic>>(
          future: _f,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
            if (snap.hasError) return Center(child: Padding(padding: const EdgeInsets.all(24), child: Text('${snap.error}', textAlign: TextAlign.center, style: const TextStyle(color: Pms.slate))));
            final kpi = Map<String, dynamic>.from(snap.data?['kpi'] ?? {});
            final items = List<Map>.from(snap.data?['items'] ?? const []);
            return RefreshIndicator(
              onRefresh: () async => setState(_reload),
              child: ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 90), children: [
                Row(children: [
                  _kpi('${kpi['total'] ?? 0}', tr('سجلات', 'Records'), Pms.violet),
                  _kpi('${kpi['running'] ?? 0}', tr('قيد التنفيذ', 'Running'), Pms.amber),
                  _kpi('${kpi['done'] ?? 0}', tr('منجزة', 'Done'), Pms.green),
                ]),
                const SizedBox(height: 6),
                Row(children: [
                  _kpi('${kpi['total_year'] ?? 0} ${kpi['currency'] ?? ''}', tr('تكلفة السنة', 'Year cost'), Pms.deep),
                ]),
                const SizedBox(height: 10),
                if (items.isEmpty) Padding(padding: const EdgeInsets.all(30), child: Center(child: Text(tr('لا توجد سجلات', 'No records'), style: const TextStyle(color: Pms.slate)))),
                ...items.map((r) => _card(r)),
              ]),
            );
          },
        ),
      ),
    );
  }

  Widget _kpi(String v, String l, Color c) => Expanded(child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 3),
        padding: const EdgeInsets.all(11),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border(right: BorderSide(color: c, width: 3))),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(v, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: c)),
          Text(l, style: const TextStyle(fontSize: 11, color: Pms.slate)),
        ])));

  Widget _card(Map r) {
    final st = (r['state'] ?? '').toString();
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: const Color(0xFFE5E7EB))),
      child: Padding(padding: const EdgeInsets.all(12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${r['vehicle'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w900, color: Pms.ink, fontSize: 15)),
            Text('${r['plate'] ?? ''} · ${r['service_type'] ?? ''}', style: const TextStyle(color: Pms.slate, fontSize: 12)),
          ])),
          Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(color: _stC(st).withOpacity(.12), borderRadius: BorderRadius.circular(999)),
            child: Text('${r['state_label'] ?? st}', style: TextStyle(color: _stC(st), fontWeight: FontWeight.w800, fontSize: 11.5))),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Text('${r['amount'] ?? 0} ${r['currency'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w900, color: Pms.violet, fontSize: 15)),
          const SizedBox(width: 12),
          Expanded(child: Text('${r['type_label'] ?? ''} · ${r['date'] ?? ''}${(r['next_date'] ?? '') != '' ? ' → ${r['next_date']}' : ''}', style: const TextStyle(color: Pms.slate, fontSize: 12), overflow: TextOverflow.ellipsis)),
          TextButton.icon(onPressed: () => _report(r), icon: const Icon(Icons.print, size: 18), label: Text(tr('طباعة', 'Print'))),
        ]),
      ])),
    );
  }

  Future<void> _openCreate() async {
    Map<String, dynamic> data;
    try { data = await _f; } catch (_) { return; }
    final meta = Map<String, dynamic>.from(data['meta'] ?? {});
    if (List.from(meta['vehicles'] ?? []).isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('لا توجد مركبات ضمن مشاريعك', 'No vehicles in your projects'))));
      return;
    }
    final ok = await showModalBottomSheet<bool>(context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(18))),
      builder: (_) => _VehicleCreateSheet(meta: meta));
    if (ok == true && mounted) setState(_reload);
  }
}

class _VehicleCreateSheet extends StatefulWidget {
  final Map<String, dynamic> meta;
  const _VehicleCreateSheet({required this.meta});
  @override
  State<_VehicleCreateSheet> createState() => _VehicleCreateSheetState();
}

class _VehicleCreateSheetState extends State<_VehicleCreateSheet> {
  int? _vehicle; int? _stype; int? _vendor; String? _type;
  final _amount = TextEditingController(); final _odo = TextEditingController();
  final _desc = TextEditingController(); final _notes = TextEditingController();
  bool _fire = false; bool _busy = false;

  List<Map> get _vehicles => List<Map>.from(widget.meta['vehicles'] ?? const []);
  List<Map> get _stypes => List<Map>.from(widget.meta['service_types'] ?? const []);
  List<Map> get _types => List<Map>.from(widget.meta['types'] ?? const []);
  List<Map> get _vendors => List<Map>.from(widget.meta['vendors'] ?? const []);

  @override
  void initState() { super.initState(); if (_types.isNotEmpty) _type = _types.first['value']?.toString(); }

  Future<void> _submit() async {
    if (_vehicle == null) { _snack(tr('اختر المركبة', 'Choose a vehicle')); return; }
    setState(() => _busy = true);
    final api = context.read<AuthProvider>().api;
    final vals = <String, dynamic>{
      'vehicle_id': _vehicle, 'service_type_id': _stype, 'type': _type,
      'amount': double.tryParse(_amount.text.trim()) ?? 0,
      'odometer_value': double.tryParse(_odo.text.trim()) ?? 0,
      'vendor_id': _vendor, 'description': _desc.text.trim(), 'notes': _notes.text.trim(), 'fire': _fire,
    };
    try { await api.pmsVehicleCreate(vals); if (mounted) Navigator.pop(context, true); }
    catch (e) { if (mounted) { setState(() => _busy = false); _snack('$e'); } }
  }

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m), backgroundColor: Pms.red));

  @override
  Widget build(BuildContext context) {
    return Directionality(textDirection: gIsRtl ? TextDirection.rtl : TextDirection.ltr,
      child: Padding(padding: EdgeInsets.only(left: 16, right: 16, top: 16, bottom: MediaQuery.of(context).viewInsets.bottom + 16),
        child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Center(child: Text(tr('تسجيل صيانة مركبة', 'New vehicle service'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: Pms.violet))),
          const SizedBox(height: 14),
          _ddInt(tr('المركبة', 'Vehicle'), _vehicle, _vehicles, (v) => setState(() => _vehicle = v)),
          const SizedBox(height: 10),
          _ddInt(tr('نوع الخدمة', 'Service type'), _stype, _stypes, (v) => setState(() => _stype = v)),
          const SizedBox(height: 10),
          _ddStr(tr('التصنيف', 'Category'), _type, _types, (v) => setState(() => _type = v)),
          const SizedBox(height: 10),
          Row(children: [
            Expanded(child: TextField(controller: _amount, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: _dec(tr('التكلفة', 'Cost')))),
            const SizedBox(width: 10),
            Expanded(child: TextField(controller: _odo, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: _dec(tr('العدّاد', 'Odometer')))),
          ]),
          const SizedBox(height: 10),
          _ddInt(tr('المورّد / الورشة', 'Vendor'), _vendor, _vendors, (v) => setState(() => _vendor = v)),
          const SizedBox(height: 10),
          TextField(controller: _desc, decoration: _dec(tr('الوصف', 'Description'))),
          const SizedBox(height: 10),
          TextField(controller: _notes, maxLines: 2, decoration: _dec(tr('ملاحظات', 'Notes'))),
          SwitchListTile(value: _fire, onChanged: (v) => setState(() => _fire = v), title: Text(tr('طفاية حريق', 'Fire extinguisher')), activeColor: Pms.violet, contentPadding: EdgeInsets.zero),
          SizedBox(height: 48, child: ElevatedButton(onPressed: _busy ? null : _submit,
            style: ElevatedButton.styleFrom(backgroundColor: Pms.violet, foregroundColor: Colors.white),
            child: _busy ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : Text(tr('حفظ', 'Save'), style: const TextStyle(fontWeight: FontWeight.w800)))),
        ]))));
  }

  InputDecoration _dec(String l) => InputDecoration(labelText: l, filled: true, fillColor: Pms.bg, border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none));
  Widget _ddInt(String l, int? v, List<Map> opts, ValueChanged<int?> onCh) => DropdownButtonFormField<int>(value: v, isExpanded: true, decoration: _dec(l),
      items: opts.map((o) => DropdownMenuItem<int>(value: o['id'] as int, child: Text('${o['name']}', overflow: TextOverflow.ellipsis))).toList(), onChanged: onCh);
  Widget _ddStr(String l, String? v, List<Map> opts, ValueChanged<String?> onCh) { if (opts.isEmpty) return const SizedBox.shrink();
    return DropdownButtonFormField<String>(value: v, isExpanded: true, decoration: _dec(l),
      items: opts.map((o) => DropdownMenuItem<String>(value: o['value']?.toString(), child: Text('${o['label']}', overflow: TextOverflow.ellipsis))).toList(), onChanged: onCh); }
}

// ========================= بترول استيشن =========================
class PetrolStationScreen extends StatefulWidget {
  const PetrolStationScreen({super.key});
  @override
  State<PetrolStationScreen> createState() => _PetrolStationScreenState();
}

class _PetrolStationScreenState extends State<PetrolStationScreen> {
  late Future<Map<String, dynamic>> _f;
  @override
  void initState() { super.initState(); _reload(); }
  void _reload() { _f = context.read<AuthProvider>().api.pmsPetrol(); }

  Future<void> _report(Map t) async {
    final api = context.read<AuthProvider>().api;
    final tok = await api.token;
    await launchUrl(Uri.parse('${api.baseUrl}${api.pmsPetrolTankReportPath(t['id'] as int)}?token=${tok ?? ''}'), mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(textDirection: gIsRtl ? TextDirection.rtl : TextDirection.ltr,
      child: Scaffold(backgroundColor: Pms.bg,
        appBar: AppBar(title: Text(tr('بترول استيشن', 'Petrol Station')), backgroundColor: const Color(0xFF0D7A5F), foregroundColor: Colors.white),
        body: FutureBuilder<Map<String, dynamic>>(future: _f, builder: (context, snap) {
          if (snap.connectionState != ConnectionState.done) return const Center(child: CircularProgressIndicator());
          if (snap.hasError) return Center(child: Padding(padding: const EdgeInsets.all(24), child: Text('${snap.error}', textAlign: TextAlign.center, style: const TextStyle(color: Pms.slate))));
          final data = snap.data ?? {};
          final kpi = Map<String, dynamic>.from(data['kpi'] ?? {});
          final tanks = List<Map>.from(data['tanks'] ?? const []);
          final meta = Map<String, dynamic>.from(data['meta'] ?? {});
          return RefreshIndicator(onRefresh: () async => setState(_reload),
            child: ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
              Row(children: [
                _kpi('${kpi['tanks'] ?? 0}', tr('خزانات', 'Tanks'), const Color(0xFF2563EB)),
                _kpi('${kpi['total_balance'] ?? 0}', tr('الرصيد', 'Balance'), Pms.green),
                _kpi('${kpi['used_month'] ?? 0}', tr('مصروف الشهر', 'Used/mo'), Pms.red),
              ]),
              const SizedBox(height: 10),
              Row(children: [
                _actBtn(tr('شحن', 'Charge'), Icons.add, const Color(0xFF0D7A5F), () => _sheet('charge', tanks, meta)),
                _actBtn(tr('صرف', 'Use'), Icons.remove, Pms.amber, () => _sheet('use', tanks, meta)),
                _actBtn(tr('تحويل', 'Transfer'), Icons.swap_horiz, const Color(0xFF7C3AED), () => _sheet('transfer', tanks, meta)),
              ]),
              const SizedBox(height: 12),
              ...tanks.map((t) => _tankCard(t)),
            ]));
        }),
      ),
    );
  }

  Widget _kpi(String v, String l, Color c) => Expanded(child: Container(margin: const EdgeInsets.symmetric(horizontal: 3), padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border(right: BorderSide(color: c, width: 3))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [Text(v, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: c)), Text(l, style: const TextStyle(fontSize: 11, color: Pms.slate))])));

  Widget _actBtn(String l, IconData i, Color c, VoidCallback onTap) => Expanded(child: Padding(padding: const EdgeInsets.symmetric(horizontal: 3),
      child: ElevatedButton.icon(onPressed: onTap, icon: Icon(i, size: 18, color: Colors.white), label: Text(l, style: const TextStyle(color: Colors.white)),
          style: ElevatedButton.styleFrom(backgroundColor: c, padding: const EdgeInsets.symmetric(vertical: 12)))));

  Widget _tankCard(Map t) {
    final prog = (numOf(t['progress'])).clamp(0, 100).toDouble();
    return Container(margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: const Color(0xFFE5E7EB))),
      child: Padding(padding: const EdgeInsets.all(12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('${t['name']}', style: const TextStyle(fontWeight: FontWeight.w900, color: Pms.ink, fontSize: 15))),
          Text('${t['balance']} / ${t['capacity']}', style: const TextStyle(fontWeight: FontWeight.w800, color: Pms.ink)),
          IconButton(onPressed: () => _report(t), icon: const Icon(Icons.print, size: 20, color: Pms.slate)),
        ]),
        if ((t['stage'] ?? '').toString().isNotEmpty) Text('${t['stage']}', style: const TextStyle(color: Pms.slate, fontSize: 12)),
        const SizedBox(height: 8),
        ClipRRect(borderRadius: BorderRadius.circular(999), child: LinearProgressIndicator(value: prog / 100, minHeight: 9, backgroundColor: const Color(0xFFEEF2F8), color: const Color(0xFF0D7A5F))),
        const SizedBox(height: 4),
        Text('${t['progress']}% · ${tr('آخر شحنة', 'Last charge')}: ${t['last_charge'] ?? '—'}', style: const TextStyle(color: Pms.slate, fontSize: 11)),
      ])));
  }

  Future<void> _sheet(String mode, List<Map> tanks, Map meta) async {
    if (tanks.isEmpty) { ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('لا توجد خزانات', 'No tanks')))); return; }
    final ok = await showModalBottomSheet<bool>(context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(18))),
      builder: (_) => _PetrolSheet(mode: mode, tanks: tanks, vehicles: List<Map>.from(meta['vehicles'] ?? const [])));
    if (ok == true && mounted) setState(_reload);
  }
}

class _PetrolSheet extends StatefulWidget {
  final String mode; final List<Map> tanks; final List<Map> vehicles;
  const _PetrolSheet({required this.mode, required this.tanks, required this.vehicles});
  @override
  State<_PetrolSheet> createState() => _PetrolSheetState();
}

class _PetrolSheetState extends State<_PetrolSheet> {
  int? _tank; int? _toTank; int? _vehicle;
  final _qty = TextEditingController(); final _cost = TextEditingController(); final _odo = TextEditingController();
  bool _busy = false;

  bool get isCharge => widget.mode == 'charge';
  bool get isUse => widget.mode == 'use';
  bool get isTransfer => widget.mode == 'transfer';
  String get _title => isCharge ? tr('شحن خزان', 'Charge tank') : isUse ? tr('صرف من خزان', 'Use from tank') : tr('تحويل بين خزانات', 'Transfer');
  Color get _c => isCharge ? const Color(0xFF0D7A5F) : isUse ? Pms.amber : const Color(0xFF7C3AED);

  Future<void> _submit() async {
    if (_tank == null) { _snack(tr('اختر الخزان', 'Choose tank')); return; }
    if (isTransfer && _toTank == null) { _snack(tr('اختر خزان الوجهة', 'Choose destination')); return; }
    final qty = double.tryParse(_qty.text.trim()) ?? 0;
    if (qty <= 0) { _snack(tr('أدخل كمية صحيحة', 'Enter a valid quantity')); return; }
    setState(() => _busy = true);
    final api = context.read<AuthProvider>().api;
    try {
      if (isCharge) {
        await api.pmsPetrolCharge({'tank_id': _tank, 'quantity': qty, 'cost': double.tryParse(_cost.text.trim()) ?? 0});
      } else if (isUse) {
        await api.pmsPetrolUse({'tank_id': _tank, 'quantity': qty, 'vehicle_id': _vehicle, 'odometer_value': double.tryParse(_odo.text.trim()) ?? 0});
      } else {
        await api.pmsPetrolTransfer({'from_tank_id': _tank, 'to_tank_id': _toTank, 'quantity': qty});
      }
      if (mounted) Navigator.pop(context, true);
    } catch (e) { if (mounted) { setState(() => _busy = false); _snack('$e'); } }
  }

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m), backgroundColor: Pms.red));

  @override
  Widget build(BuildContext context) {
    return Directionality(textDirection: gIsRtl ? TextDirection.rtl : TextDirection.ltr,
      child: Padding(padding: EdgeInsets.only(left: 16, right: 16, top: 16, bottom: MediaQuery.of(context).viewInsets.bottom + 16),
        child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Center(child: Text(_title, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: _c))),
          const SizedBox(height: 14),
          _dd(isTransfer ? tr('من خزان', 'From tank') : tr('الخزان', 'Tank'), _tank, widget.tanks, (v) => setState(() => _tank = v)),
          if (isTransfer) ...[const SizedBox(height: 10), _dd(tr('إلى خزان', 'To tank'), _toTank, widget.tanks, (v) => setState(() => _toTank = v))],
          if (isUse) ...[const SizedBox(height: 10), _ddv(tr('المركبة', 'Vehicle'), _vehicle, widget.vehicles, (v) => setState(() => _vehicle = v))],
          const SizedBox(height: 10),
          TextField(controller: _qty, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: _dec(tr('الكمية (لتر)', 'Quantity (L)'))),
          if (isCharge) ...[const SizedBox(height: 10), TextField(controller: _cost, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: _dec(tr('التكلفة', 'Cost')))],
          if (isUse) ...[const SizedBox(height: 10), TextField(controller: _odo, keyboardType: const TextInputType.numberWithOptions(decimal: true), decoration: _dec(tr('قراءة العدّاد', 'Odometer')))],
          const SizedBox(height: 16),
          SizedBox(height: 48, child: ElevatedButton(onPressed: _busy ? null : _submit,
            style: ElevatedButton.styleFrom(backgroundColor: _c, foregroundColor: Colors.white),
            child: _busy ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : Text(tr('تنفيذ', 'Submit'), style: const TextStyle(fontWeight: FontWeight.w800)))),
        ]))));
  }

  InputDecoration _dec(String l) => InputDecoration(labelText: l, filled: true, fillColor: Pms.bg, border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none));
  Widget _dd(String l, int? v, List<Map> opts, ValueChanged<int?> onCh) => DropdownButtonFormField<int>(value: v, isExpanded: true, decoration: _dec(l),
      items: opts.map((o) => DropdownMenuItem<int>(value: o['id'] as int, child: Text('${o['name']}', overflow: TextOverflow.ellipsis))).toList(), onChanged: onCh);
  Widget _ddv(String l, int? v, List<Map> opts, ValueChanged<int?> onCh) => DropdownButtonFormField<int>(value: v, isExpanded: true, decoration: _dec(l),
      items: [const DropdownMenuItem<int>(value: null, child: Text('—')), ...opts.map((o) => DropdownMenuItem<int>(value: o['id'] as int, child: Text('${o['name']}', overflow: TextOverflow.ellipsis)))], onChanged: onCh);
}
