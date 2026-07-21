import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Manage the pantry catalogue: the suppliers we buy from, and the materials
/// (consumables) registered against them. A supply typed fresh into every
/// purchase drifts under four spellings — this keeps the catalogue clean.
class HospSuppliersScreen extends StatefulWidget {
  const HospSuppliersScreen({super.key});
  @override
  State<HospSuppliersScreen> createState() => _HospSuppliersScreenState();
}

class _HospSuppliersScreenState extends State<HospSuppliersScreen> {
  static const _brown = Color(0xFF8A6D3B);
  Future<Map<String, dynamic>>? _f;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _f = context.read<AuthProvider>().api.hospSuppliers();

  Future<void> _editSupplier([Map? s]) async {
    final name = TextEditingController(text: '${s?['name'] ?? ''}');
    final phone = TextEditingController(text: '${s?['phone'] ?? ''}');
    final email = TextEditingController(text: '${s?['email'] ?? ''}');
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text(s == null ? tr('مورّد جديد', 'New supplier') : tr('تعديل مورّد', 'Edit supplier')),
        content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: name, decoration: InputDecoration(labelText: tr('الاسم', 'Name'))),
          TextField(controller: phone, decoration: InputDecoration(labelText: tr('الهاتف', 'Phone')), keyboardType: TextInputType.phone),
          TextField(controller: email, decoration: InputDecoration(labelText: tr('البريد', 'Email')), keyboardType: TextInputType.emailAddress),
        ])),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: Text(tr('حفظ', 'Save'))),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await context.read<AuthProvider>().api.hospSupplierSave({
        if (s != null) 'id': s['id'],
        'name': name.text.trim(), 'phone': phone.text.trim(), 'email': email.text.trim(),
      });
      if (mounted) { _snack(tr('تم الحفظ ✅', 'Saved ✅')); setState(_load); }
    } catch (e) { _snack('$e', err: true); }
  }

  Future<void> _newMaterial(List categories, List uoms, List suppliers) async {
    final name = TextEditingController();
    final pack = TextEditingController(text: '1000');
    final cost = TextEditingController(text: '0');
    final minq = TextEditingController(text: '0');
    String? cat = categories.isNotEmpty ? '${(categories.first as Map)['code']}' : 'other';
    String? uom = uoms.isNotEmpty ? '${(uoms.first as Map)['code']}' : 'g';
    int? supplierId;
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => StatefulBuilder(builder: (c, setD) => AlertDialog(
        title: Text(tr('تسجيل مادة', 'Register material')),
        content: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: name, decoration: InputDecoration(labelText: tr('اسم المادة', 'Material name'))),
          DropdownButtonFormField<String>(value: cat, isExpanded: true,
              decoration: InputDecoration(labelText: tr('الفئة', 'Category')),
              items: [for (final c in categories.cast<Map>()) DropdownMenuItem(value: '${c['code']}', child: Text('${c['label']}'))],
              onChanged: (v) => setD(() => cat = v)),
          DropdownButtonFormField<String>(value: uom, isExpanded: true,
              decoration: InputDecoration(labelText: tr('الوحدة', 'Unit')),
              items: [for (final u in uoms.cast<Map>()) DropdownMenuItem(value: '${u['code']}', child: Text('${u['label']}'))],
              onChanged: (v) => setD(() => uom = v)),
          DropdownButtonFormField<int>(value: supplierId, isExpanded: true,
              decoration: InputDecoration(labelText: tr('المورّد (اختياري)', 'Supplier (optional)')),
              items: [for (final s in suppliers.cast<Map>()) DropdownMenuItem(value: s['id'] as int, child: Text('${s['name']}'))],
              onChanged: (v) => setD(() => supplierId = v)),
          TextField(controller: pack, decoration: InputDecoration(labelText: tr('حجم العبوة (بالوحدة)', 'Pack size')), keyboardType: TextInputType.number),
          TextField(controller: cost, decoration: InputDecoration(labelText: tr('تكلفة الوحدة', 'Unit cost')), keyboardType: TextInputType.number),
          TextField(controller: minq, decoration: InputDecoration(labelText: tr('حد إعادة الطلب', 'Reorder level')), keyboardType: TextInputType.number),
        ])),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: Text(tr('تسجيل', 'Register'))),
        ],
      )),
    );
    if (ok != true) return;
    try {
      await context.read<AuthProvider>().api.hospSupplySave({
        'name': name.text.trim(), 'category': cat, 'uom_name': uom,
        'pack_size': double.tryParse(pack.text) ?? 1000,
        'unit_cost': double.tryParse(cost.text) ?? 0,
        'min_qty': double.tryParse(minq.text) ?? 0,
        if (supplierId != null) 'partner_id': supplierId,
        'supplier_type': supplierId != null ? 'external' : 'care',
      });
      if (mounted) { _snack(tr('سُجّلت المادة ✅', 'Material registered ✅')); setState(_load); }
    } catch (e) { _snack('$e', err: true); }
  }

  void _snack(String m, {bool err = false}) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: err ? const Color(0xFFE11D48) : _brown, behavior: SnackBarBehavior.floating));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      appBar: AppBar(backgroundColor: _brown, foregroundColor: Colors.white,
          title: Text(tr('الموردون والمواد', 'Suppliers & materials'),
              style: const TextStyle(fontWeight: FontWeight.w900))),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _f,
        builder: (_, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator(color: _brown));
          }
          final d = snap.data ?? const {};
          final suppliers = (d['suppliers'] as List?) ?? const [];
          final categories = (d['categories'] as List?) ?? const [];
          final uoms = (d['uoms'] as List?) ?? const [];
          return RefreshIndicator(
            color: _brown,
            onRefresh: () async => setState(_load),
            child: ListView(padding: const EdgeInsets.fromLTRB(14, 14, 14, 24), children: [
              Row(children: [
                Expanded(child: OutlinedButton.icon(
                    style: OutlinedButton.styleFrom(foregroundColor: _brown),
                    icon: const Icon(Icons.add_business_rounded),
                    label: Text(tr('مورّد جديد', 'New supplier')),
                    onPressed: () => _editSupplier())),
                const SizedBox(width: 8),
                Expanded(child: FilledButton.icon(
                    style: FilledButton.styleFrom(backgroundColor: _brown),
                    icon: const Icon(Icons.inventory_2_rounded),
                    label: Text(tr('تسجيل مادة', 'Register material')),
                    onPressed: () => _newMaterial(categories, uoms, suppliers))),
              ]),
              const SizedBox(height: 14),
              Text(tr('الموردون (${suppliers.length})', 'Suppliers (${suppliers.length})'),
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
              const SizedBox(height: 8),
              if (suppliers.isEmpty)
                Padding(padding: const EdgeInsets.all(20),
                    child: Center(child: Text(tr('لا موردين', 'No suppliers'), style: const TextStyle(color: Colors.black45)))),
              for (final s in suppliers.cast<Map>())
                Container(
                  margin: const EdgeInsets.only(bottom: 8),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
                      border: Border.all(color: const Color(0xFFE3E7EE))),
                  child: ListTile(
                    leading: CircleAvatar(backgroundColor: _brown.withOpacity(0.12),
                        child: const Icon(Icons.storefront_rounded, color: _brown, size: 20)),
                    title: Text('${s['name']}', style: const TextStyle(fontWeight: FontWeight.w800)),
                    subtitle: Text([if (s['phone'] != null) '📞 ${s['phone']}', if (s['email'] != null) '✉ ${s['email']}'].join(' · ')),
                    trailing: IconButton(icon: const Icon(Icons.edit_rounded, size: 18), onPressed: () => _editSupplier(s)),
                  ),
                ),
            ]),
          );
        },
      ),
    );
  }
}
