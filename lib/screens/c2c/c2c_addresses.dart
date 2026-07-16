import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'c2c_shell.dart';

/// Full-screen manager for the customer's saved delivery addresses.
class C2CAddressesScreen extends StatefulWidget {
  const C2CAddressesScreen({super.key, this.picking = false});

  /// when true the screen is opened as a picker → tapping a row returns it.
  final bool picking;

  @override
  State<C2CAddressesScreen> createState() => _C2CAddressesScreenState();
}

class _C2CAddressesScreenState extends State<C2CAddressesScreen> {
  late Future<List<dynamic>> _f;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => setState(() => _f = context.read<AuthProvider>().api.c2cAddresses());

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: C2C.bg,
      appBar: AppBar(
        backgroundColor: C2C.navy, foregroundColor: Colors.white, elevation: 0,
        title: Text(widget.picking ? tr('اختر عنوان التوصيل', 'Choose address') : tr('عناوين التوصيل', 'Delivery addresses')),
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: C2C.red, foregroundColor: Colors.white,
        onPressed: () => _edit(null),
        icon: const Icon(Icons.add_location_alt_rounded),
        label: Text(tr('عنوان جديد', 'New address'), style: const TextStyle(fontWeight: FontWeight.w800)),
      ),
      body: FutureBuilder<List<dynamic>>(
        future: _f,
        builder: (_, snap) {
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final list = snap.data!;
          if (list.isEmpty) return _empty();
          return ListView.separated(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 100),
            itemCount: list.length,
            separatorBuilder: (_, __) => const SizedBox(height: 10),
            itemBuilder: (_, i) => _card(list[i] as Map),
          );
        },
      ),
    );
  }

  Widget _empty() => Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(padding: const EdgeInsets.all(22), decoration: BoxDecoration(color: C2C.navy.withValues(alpha: 0.07), borderRadius: BorderRadius.circular(26)), child: const Icon(Icons.location_off_rounded, size: 46, color: C2C.navy)),
          const SizedBox(height: 14),
          Text(tr('لا توجد عناوين محفوظة', 'No saved addresses'), style: const TextStyle(fontWeight: FontWeight.w800, color: C2C.navy, fontSize: 15)),
          const SizedBox(height: 6),
          Text(tr('أضف عنواناً لتسريع طلباتك', 'Add one to speed up your orders'), style: const TextStyle(color: C2C.slate)),
        ]),
      );

  Widget _card(Map a) {
    final def = a['is_default'] == true;
    return Material(
      color: Colors.white, borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: widget.picking ? () => Navigator.pop(context, a) : () => _edit(a),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: def ? C2C.navy.withValues(alpha: 0.35) : Colors.black12),
          ),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(padding: const EdgeInsets.all(9), decoration: BoxDecoration(color: C2C.navy.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(12)), child: const Icon(Icons.location_on_rounded, color: C2C.navy)),
            const SizedBox(width: 12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Flexible(child: Text('${a['label']}', style: const TextStyle(fontWeight: FontWeight.w900, color: C2C.ink, fontSize: 14.5))),
                if (def) Container(margin: const EdgeInsetsDirectional.only(start: 8), padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2), decoration: BoxDecoration(color: C2C.navy, borderRadius: BorderRadius.circular(8)), child: Text(tr('افتراضي', 'Default'), style: const TextStyle(color: Colors.white, fontSize: 9.5, fontWeight: FontWeight.w800))),
              ]),
              const SizedBox(height: 4),
              Text('${a['full_address'] ?? ''}', style: const TextStyle(color: C2C.slate, fontSize: 12.5, height: 1.3)),
              if (a['phone'] != null) Padding(padding: const EdgeInsets.only(top: 4), child: Row(children: [const Icon(Icons.phone_rounded, size: 13, color: C2C.slate), const SizedBox(width: 4), Text('${a['phone']}', style: const TextStyle(color: C2C.slate, fontSize: 12))])),
            ])),
            if (widget.picking) const Icon(Icons.chevron_left_rounded, color: C2C.slate)
            else PopupMenuButton<String>(
              icon: const Icon(Icons.more_vert_rounded, color: C2C.slate),
              onSelected: (v) { if (v == 'edit') _edit(a); if (v == 'delete') _delete(a); },
              itemBuilder: (_) => [
                PopupMenuItem(value: 'edit', child: Text(tr('تعديل', 'Edit'))),
                PopupMenuItem(value: 'delete', child: Text(tr('حذف', 'Delete'), style: const TextStyle(color: C2C.red))),
              ],
            ),
          ]),
        ),
      ),
    );
  }

  Future<void> _delete(Map a) async {
    final ok = await showDialog<bool>(context: context, builder: (_) => AlertDialog(
      title: Text(tr('حذف العنوان', 'Delete address')),
      content: Text(tr('هل تريد حذف "${a['label']}"؟', 'Delete "${a['label']}"?')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: Text(tr('إلغاء', 'Cancel'))),
        TextButton(onPressed: () => Navigator.pop(context, true), child: Text(tr('حذف', 'Delete'), style: const TextStyle(color: C2C.red))),
      ],
    ));
    if (ok != true || !mounted) return;
    await context.read<AuthProvider>().api.c2cAddressDelete(a['id'] as int);
    if (mounted) _reload();
  }

  Future<void> _edit(Map? a) async {
    final saved = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _AddressForm(existing: a),
    );
    if (saved == true) _reload();
  }
}

class _AddressForm extends StatefulWidget {
  const _AddressForm({this.existing});
  final Map? existing;
  @override
  State<_AddressForm> createState() => _AddressFormState();
}

class _AddressFormState extends State<_AddressForm> {
  late final Map<String, TextEditingController> _c;
  bool _default = false;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    final e = widget.existing ?? {};
    _c = {
      for (final k in ['label', 'area', 'block', 'street', 'building', 'floor', 'apartment', 'landmark', 'phone', 'notes'])
        k: TextEditingController(text: e[k]?.toString() ?? '')
    };
    _default = e['is_default'] == true;
  }

  @override
  void dispose() {
    for (final v in _c.values) {
      v.dispose();
    }
    super.dispose();
  }

  Future<void> _save() async {
    if (_c['label']!.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('أدخل اسم العنوان', 'Enter a label')), backgroundColor: C2C.red));
      return;
    }
    setState(() => _busy = true);
    try {
      final body = {for (final e in _c.entries) e.key: e.value.text.trim(), 'is_default': _default};
      if (widget.existing != null) body['id'] = widget.existing!['id'];
      await context.read<AuthProvider>().api.c2cAddressSave(body);
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: C2C.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 14, 16, MediaQuery.of(context).viewInsets.bottom + 16),
      child: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Center(child: Container(width: 42, height: 4, decoration: BoxDecoration(color: Colors.black12, borderRadius: BorderRadius.circular(4)))),
          const SizedBox(height: 12),
          Text(widget.existing == null ? tr('عنوان جديد', 'New address') : tr('تعديل العنوان', 'Edit address'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: C2C.navy)),
          const SizedBox(height: 14),
          _f('label', tr('اسم العنوان (المنزل، العمل)', 'Label (Home, Work)'), Icons.bookmark_border_rounded),
          const SizedBox(height: 9),
          _f('area', tr('المنطقة', 'Area'), Icons.map_outlined),
          const SizedBox(height: 9),
          Row(children: [Expanded(child: _f('block', tr('قطعة', 'Block'), Icons.grid_view_rounded)), const SizedBox(width: 9), Expanded(child: _f('street', tr('شارع', 'Street'), Icons.add_road_rounded))]),
          const SizedBox(height: 9),
          Row(children: [Expanded(child: _f('building', tr('مبنى/منزل', 'Building'), Icons.home_outlined)), const SizedBox(width: 9), Expanded(child: _f('floor', tr('دور', 'Floor'), Icons.stairs_outlined)), const SizedBox(width: 9), Expanded(child: _f('apartment', tr('شقة', 'Apt'), Icons.meeting_room_outlined))]),
          const SizedBox(height: 9),
          _f('landmark', tr('علامة مميزة', 'Landmark'), Icons.push_pin_outlined),
          const SizedBox(height: 9),
          _f('phone', tr('الهاتف', 'Phone'), Icons.phone_outlined, phone: true),
          const SizedBox(height: 9),
          _f('notes', tr('ملاحظات', 'Notes'), Icons.notes_rounded),
          const SizedBox(height: 6),
          SwitchListTile(
            contentPadding: EdgeInsets.zero, activeColor: C2C.navy, value: _default,
            onChanged: (v) => setState(() => _default = v),
            title: Text(tr('اجعله العنوان الافتراضي', 'Set as default'), style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
          ),
          const SizedBox(height: 8),
          SizedBox(width: double.infinity, height: 50, child: ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: C2C.navy, foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
            onPressed: _busy ? null : _save,
            child: _busy ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : Text(tr('حفظ', 'Save'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
          )),
        ]),
      ),
    );
  }

  Widget _f(String k, String hint, IconData ic, {bool phone = false}) => TextField(
        controller: _c[k], keyboardType: phone ? TextInputType.phone : TextInputType.text,
        decoration: InputDecoration(hintText: hint, prefixIcon: Icon(ic, size: 20), filled: true, fillColor: C2C.bg, isDense: true, border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)),
      );
}
