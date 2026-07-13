import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'add_worker_screen.dart';

/// Client self-management console: create/delete buildings, floors, locations,
/// teams (and add workers). Mirrors the portal management page.
class ManageScreen extends StatefulWidget {
  const ManageScreen({super.key});
  @override
  State<ManageScreen> createState() => _ManageScreenState();
}

class _ManageScreenState extends State<ManageScreen> {
  Map<String, dynamic>? _o;
  bool _loading = true, _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final o = await context.read<AuthProvider>().api.manageOptions();
      if (mounted) setState(() { _o = o; _loading = false; });
    } catch (e) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _do(Future<void> Function() f, String ok) async {
    if (_busy) return;
    setState(() => _busy = true);
    try {
      await f();
      await _load();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ok)));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  List _l(String k) => (_o?[k] as List?) ?? const [];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('إدارة المنشأة', 'Manage facility'))),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _o == null
              ? Center(child: Text(tr('لا صلاحية.', 'Not allowed.')))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(padding: const EdgeInsets.all(14), children: [
                    _buildings(),
                    _floors(),
                    _locations(),
                    _assets(),
                    _teams(),
                    _workers(),
                    const SizedBox(height: 24),
                  ]),
                ),
    );
  }

  Widget _section(String title, IconData icon, List<Widget> children) => Card(
        margin: const EdgeInsets.only(bottom: 14),
        child: Padding(padding: const EdgeInsets.all(14), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [Icon(icon, size: 20, color: const Color(0xFF0B6EA8)), const SizedBox(width: 8),
            Text(title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15))]),
          const SizedBox(height: 10),
          ...children,
        ])),
      );

  Widget _tile(String label, VoidCallback onDelete) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(children: [
          Expanded(child: Text(label, style: const TextStyle(fontSize: 13.5))),
          IconButton(icon: const Icon(Icons.delete_outline, color: Color(0xFFE11D48), size: 20), onPressed: _busy ? null : onDelete),
        ]),
      );

  Future<void> _confirmDelete(String kind, int id) async {
    final ok = await showDialog<bool>(context: context, builder: (_) => AlertDialog(
      title: Text(tr('تأكيد الحذف', 'Confirm delete')),
      content: Text(tr('هل تريد الحذف؟', 'Delete this item?')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE11D48)),
            onPressed: () => Navigator.pop(context, true), child: Text(tr('حذف', 'Delete'))),
      ],
    ));
    if (ok == true) _do(() => context.read<AuthProvider>().api.manageDelete(kind, id), tr('تم الحذف', 'Deleted'));
  }

  // ---- sections ----
  Widget _buildings() {
    final name = TextEditingController();
    int? fac = _l('facilities').isNotEmpty ? _l('facilities').first['id'] as int : null;
    String? type = _l('building_types').isNotEmpty ? _l('building_types').first['v'] as String : null;
    return _section(tr('المباني', 'Buildings'), Icons.apartment, [
      StatefulBuilder(builder: (_, set) => Column(children: [
        _field(name, tr('اسم المبنى', 'Building name')),
        Row(children: [
          Expanded(child: _dd<int>(fac, [for (final f in _l('facilities')) DropdownMenuItem(value: f['id'] as int, child: Text('${f['name']}'))], (v) => set(() => fac = v), tr('المرفق', 'Facility'))),
          const SizedBox(width: 8),
          Expanded(child: _dd<String>(type, [for (final t in _l('building_types')) DropdownMenuItem(value: t['v'] as String, child: Text('${t['l']}'))], (v) => set(() => type = v), tr('النوع', 'Type'))),
        ]),
        _addBtn(() => _do(() => context.read<AuthProvider>().api.manageUpsert('building', {'name': name.text.trim(), 'facility_id': fac, 'building_type': type}), tr('أُضيف المبنى', 'Building added'))),
      ])),
      const Divider(),
      for (final b in _l('buildings')) _tile('🧱 ${b['name']} (${b['floors']} ${tr('أدوار', 'floors')})', () => _confirmDelete('building', b['id'] as int)),
    ]);
  }

  Widget _floors() {
    final name = TextEditingController();
    int? bld = _l('buildings').isNotEmpty ? _l('buildings').first['id'] as int : null;
    return _section(tr('الأدوار', 'Floors'), Icons.layers, [
      StatefulBuilder(builder: (_, set) => Column(children: [
        _field(name, tr('اسم الدور', 'Floor name')),
        _dd<int>(bld, [for (final b in _l('buildings')) DropdownMenuItem(value: b['id'] as int, child: Text('${b['name']}'))], (v) => set(() => bld = v), tr('المبنى', 'Building')),
        _addBtn(() => _do(() => context.read<AuthProvider>().api.manageUpsert('floor', {'name': name.text.trim(), 'building_id': bld}), tr('أُضيف الدور', 'Floor added'))),
      ])),
      const Divider(),
      for (final f in _l('floors')) _tile('🪜 ${f['building']} ← ${f['name']}', () => _confirmDelete('floor', f['id'] as int)),
    ]);
  }

  Widget _locations() {
    final name = TextEditingController();
    int? fl = _l('floors').isNotEmpty ? _l('floors').first['id'] as int : null;
    String? type = _l('location_types').isNotEmpty ? _l('location_types').first['v'] as String : null;
    return _section(tr('المواقع', 'Locations'), Icons.meeting_room, [
      StatefulBuilder(builder: (_, set) => Column(children: [
        _field(name, tr('اسم الموقع/الغرفة', 'Location/room name')),
        Row(children: [
          Expanded(child: _dd<int>(fl, [for (final f in _l('floors')) DropdownMenuItem(value: f['id'] as int, child: Text('${f['building']} ← ${f['name']}'))], (v) => set(() => fl = v), tr('الدور', 'Floor'))),
          const SizedBox(width: 8),
          Expanded(child: _dd<String>(type, [for (final t in _l('location_types')) DropdownMenuItem(value: t['v'] as String, child: Text('${t['l']}'))], (v) => set(() => type = v), tr('النوع', 'Type'))),
        ]),
        _addBtn(() => _do(() => context.read<AuthProvider>().api.manageUpsert('location', {'name': name.text.trim(), 'floor_id': fl, 'location_type': type}), tr('أُضيف الموقع (رمز QR تلقائي)', 'Location added (QR auto)'))),
      ])),
      Text('${tr('إجمالي المواقع', 'Total locations')}: ${_o?['locations_count'] ?? 0} · ${tr('يُولَّد رمز QR تلقائياً', 'QR generated automatically')}',
          style: TextStyle(color: Theme.of(context).colorScheme.outline, fontSize: 12)),
    ]);
  }

  Widget _assets() {
    final name = TextEditingController();
    int? fac = _l('facilities').isNotEmpty ? _l('facilities').first['id'] as int : null;
    String? cat = _l('asset_categories').isNotEmpty ? _l('asset_categories').first['v'] as String : null;
    if (_l('asset_categories').isEmpty) return const SizedBox.shrink();
    return _section(tr('الأصول', 'Assets'), Icons.precision_manufacturing, [
      StatefulBuilder(builder: (_, set) => Column(children: [
        _field(name, tr('اسم الأصل', 'Asset name')),
        Row(children: [
          Expanded(child: _dd<int>(fac, [for (final f in _l('facilities')) DropdownMenuItem(value: f['id'] as int, child: Text('${f['name']}'))], (v) => set(() => fac = v), tr('المرفق', 'Facility'))),
          const SizedBox(width: 8),
          Expanded(child: _dd<String>(cat, [for (final c in _l('asset_categories')) DropdownMenuItem(value: c['v'] as String, child: Text('${c['l']}'))], (v) => set(() => cat = v), tr('الفئة', 'Category'))),
        ]),
        _addBtn(() => _do(() => context.read<AuthProvider>().api.manageUpsert('asset', {'name': name.text.trim(), 'facility_id': fac, 'category': cat}), tr('أُضيف الأصل', 'Asset added'))),
      ])),
      const Divider(),
      for (final a in _l('assets')) _tile('🏭 ${a['code'] ?? ''} · ${a['name']}', () => _confirmDelete('asset', a['id'] as int)),
    ]);
  }

  Widget _teams() {
    final name = TextEditingController();
    int? fac = _l('facilities').isNotEmpty ? _l('facilities').first['id'] as int : null;
    int? svc = _l('services').isNotEmpty ? _l('services').first['id'] as int : null;
    return _section(tr('الفرق', 'Teams'), Icons.groups, [
      StatefulBuilder(builder: (_, set) => Column(children: [
        _field(name, tr('اسم الفريق', 'Team name')),
        Row(children: [
          Expanded(child: _dd<int>(fac, [for (final f in _l('facilities')) DropdownMenuItem(value: f['id'] as int, child: Text('${f['name']}'))], (v) => set(() => fac = v), tr('المرفق', 'Facility'))),
          const SizedBox(width: 8),
          Expanded(child: _dd<int>(svc, [for (final s in _l('services')) DropdownMenuItem(value: s['id'] as int, child: Text('${s['name']}'))], (v) => set(() => svc = v), tr('الخدمة', 'Service'))),
        ]),
        _addBtn(() => _do(() => context.read<AuthProvider>().api.manageUpsert('team', {'name': name.text.trim(), 'facility_id': fac, 'service_id': svc}), tr('أُضيف الفريق', 'Team added'))),
      ])),
      const Divider(),
      for (final t in _l('teams')) _tile('👥 ${t['name']} · ${t['service'] ?? ''}', () => _confirmDelete('team', t['id'] as int)),
    ]);
  }

  Widget _workers() => _section(tr('العمّال', 'Workers'), Icons.engineering, [
        FilledButton.icon(
          onPressed: () async {
            await Navigator.push(context, MaterialPageRoute(builder: (_) => const AddWorkerScreen()));
            _load();
          },
          icon: const Icon(Icons.person_add),
          label: Text(tr('➕ إضافة عامل / مستخدم', '➕ Add worker / user')),
          style: FilledButton.styleFrom(backgroundColor: const Color(0xFF16A34A), minimumSize: const Size.fromHeight(46)),
        ),
      ]);

  // ---- form helpers ----
  Widget _field(TextEditingController c, String hint) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: TextField(controller: c, decoration: InputDecoration(hintText: hint, border: const OutlineInputBorder(), isDense: true)),
      );
  Widget _dd<T>(T? value, List<DropdownMenuItem<T>> items, ValueChanged<T?> onCh, String label) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: DropdownButtonFormField<T>(value: value, isExpanded: true, items: items, onChanged: onCh,
            decoration: InputDecoration(labelText: label, border: const OutlineInputBorder(), isDense: true)),
      );
  Widget _addBtn(VoidCallback onTap) => SizedBox(width: double.infinity, child: FilledButton.icon(
        onPressed: _busy ? null : onTap, icon: const Icon(Icons.add), label: Text(tr('إضافة', 'Add')),
        style: FilledButton.styleFrom(backgroundColor: const Color(0xFF16A34A))));
}
