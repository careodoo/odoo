import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'searchable_picker.dart';

/// Add or edit a client-OWNED asset (ownership is fixed to 'client' on the
/// backend). [existing] pre-fills the form for editing.
class AssetCreateSheet extends StatefulWidget {
  const AssetCreateSheet({super.key, this.existing});
  final Map? existing;

  static Future<bool?> open(BuildContext context, {Map? existing}) => showModalBottomSheet<bool>(
        context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
        builder: (_) => AssetCreateSheet(existing: existing),
      );

  @override
  State<AssetCreateSheet> createState() => _AssetCreateSheetState();
}

class _AssetCreateSheetState extends State<AssetCreateSheet> {
  Map<String, dynamic>? _opts;
  String? _error;
  final _name = TextEditingController();
  final _brand = TextEditingController();
  final _model = TextEditingController();
  final _serial = TextEditingController();
  final _barcode = TextEditingController();
  int? _facilityId;
  int? _locationId;
  String _category = 'other';
  String _status = 'operational';
  DateTime? _warranty;
  bool _submitting = false;

  static const _accent = Color(0xFF0891B2);
  static const _navy = Color(0xFF0E3A5F);

  bool get _isEdit => widget.existing != null;

  @override
  void initState() {
    super.initState();
    final e = widget.existing;
    if (e != null) {
      _name.text = '${e['name'] ?? ''}';
      _brand.text = '${e['brand'] ?? ''}';
      _model.text = '${e['model'] ?? ''}';
      _serial.text = '${e['serial'] ?? ''}';
      _barcode.text = '${e['barcode'] ?? ''}';
      _category = '${e['category'] ?? 'other'}';
      _status = '${e['status'] ?? 'operational'}';
      _facilityId = e['facility_id'] as int?;
    }
    _load();
  }

  @override
  void dispose() {
    for (final c in [_name, _brand, _model, _serial, _barcode]) { c.dispose(); }
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final o = await context.read<AuthProvider>().api.clientAssetOptions();
      if (!mounted) return;
      setState(() {
        _opts = o;
        final facs = (o['facilities'] as List?) ?? const [];
        if (_facilityId == null && facs.isNotEmpty) _facilityId = facs.first['id'] as int;
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
    if (_name.text.trim().isEmpty) { _snack(tr('أدخل اسم الأصل', 'Enter asset name')); return; }
    setState(() => _submitting = true);
    final body = <String, dynamic>{
      'name': _name.text.trim(), 'facility_id': _facilityId, 'location_id': _locationId,
      'category': _category, 'status': _status,
      'brand': _brand.text.trim(), 'model': _model.text.trim(),
      'serial': _serial.text.trim(), 'barcode': _barcode.text.trim(),
      if (_warranty != null) 'warranty_end': '${_warranty!.toLocal()}'.substring(0, 10),
    };
    try {
      final api = context.read<AuthProvider>().api;
      if (_isEdit) {
        await api.clientAssetUpdate(widget.existing!['id'] as int, body);
      } else {
        await api.clientAssetCreate(body);
      }
      if (!mounted) return;
      Navigator.pop(context, true);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(_isEdit ? tr('حُدّث الأصل', 'Asset updated') : tr('أُضيف الأصل', 'Asset added')),
        backgroundColor: const Color(0xFF16A34A), behavior: SnackBarBehavior.floating));
    } catch (e) {
      if (mounted) { setState(() => _submitting = false); _snack('$e'); }
    }
  }

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: _accent, behavior: SnackBarBehavior.floating));

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
                  colors: [const Color(0xFF0EA5C4), Color.lerp(_accent, Colors.black, 0.3)!], begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Column(children: [
                Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12),
                    decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
                Row(children: [
                  Container(width: 42, height: 42, alignment: Alignment.center,
                      decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(12)),
                      child: const Icon(Icons.precision_manufacturing_rounded, color: Colors.white, size: 22)),
                  const SizedBox(width: 12),
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text(_isEdit ? tr('تعديل أصل', 'Edit asset') : tr('إضافة أصل', 'Add asset'),
                        style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
                    Text(tr('أصولك الخاصة', 'Your own assets'),
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 11.5)),
                  ])),
                  IconButton(icon: const Icon(Icons.close_rounded, color: Colors.white), onPressed: () => Navigator.pop(context)),
                ]),
              ]),
            ),
          ),
          Expanded(child: _opts == null
              ? Center(child: _error != null ? Text(_error!, style: const TextStyle(color: Colors.grey)) : const CircularProgressIndicator(color: _accent))
              : ListView(controller: sc, padding: const EdgeInsets.all(16), children: _form())),
          if (_opts != null) SafeArea(top: false, child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
            child: SizedBox(height: 52, child: FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: _accent, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
              onPressed: _submitting ? null : _submit,
              icon: _submitting ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Icon(Icons.save_rounded),
              label: Text(_isEdit ? tr('حفظ التعديلات', 'Save changes') : tr('إضافة الأصل', 'Add asset'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
            )),
          )),
        ]),
      ),
    );
  }

  List<Widget> _form() {
    final cats = (_opts!['categories'] as List?)?.cast<Map>() ?? const [];
    final stats = (_opts!['statuses'] as List?)?.cast<Map>() ?? const [];
    return [
      _lbl(Icons.label_rounded, tr('بيانات الأصل', 'Asset details')),
      const SizedBox(height: 8),
      _field(_name, tr('اسم الأصل *', 'Asset name *')),
      const SizedBox(height: 10),
      SearchableField(
        label: tr('الفئة', 'Category'), icon: Icons.category_rounded, value: _category, accent: _accent, allowClear: false,
        options: [for (final c in cats) PickOption(value: c['v'], label: '${c['l']}', search: '${c['v']}')],
        onChanged: (v) => setState(() => _category = '$v'),
      ),
      const SizedBox(height: 10),
      SearchableField(
        label: tr('الحالة', 'Status'), icon: Icons.toggle_on_rounded, value: _status, accent: _accent, allowClear: false,
        options: [for (final s in stats) PickOption(value: s['v'], label: '${s['l']}', search: '${s['v']}')],
        onChanged: (v) => setState(() => _status = '$v'),
      ),
      const SizedBox(height: 16),
      _lbl(Icons.apartment_rounded, tr('الموقع', 'Location')),
      const SizedBox(height: 8),
      SearchableField(
        label: tr('المرفق', 'Facility'), icon: Icons.apartment_rounded, value: _facilityId, accent: _accent, allowClear: false,
        options: [for (final f in (_opts!['facilities'] as List).cast<Map>()) PickOption(value: f['id'], label: '${f['name']}')],
        onChanged: (v) => setState(() { _facilityId = v as int?; _locationId = null; }),
      ),
      if (_locations.isNotEmpty) ...[
        const SizedBox(height: 10),
        SearchableField(
          label: tr('الموقع (اختياري)', 'Location (optional)'), icon: Icons.pin_drop_rounded, value: _locationId, accent: _accent,
          options: [for (final l in _locations) PickOption(value: l['id'], label: '${l['name']}')],
          onChanged: (v) => setState(() => _locationId = v as int?),
        ),
      ],
      const SizedBox(height: 16),
      _lbl(Icons.info_outline_rounded, tr('المواصفات', 'Specs')),
      const SizedBox(height: 8),
      Row(children: [
        Expanded(child: _field(_brand, tr('الماركة', 'Brand'))),
        const SizedBox(width: 10),
        Expanded(child: _field(_model, tr('الموديل', 'Model'))),
      ]),
      const SizedBox(height: 10),
      Row(children: [
        Expanded(child: _field(_serial, tr('الرقم التسلسلي', 'Serial'))),
        const SizedBox(width: 10),
        Expanded(child: _field(_barcode, tr('الباركود', 'Barcode'))),
      ]),
      const SizedBox(height: 10),
      InkWell(
        onTap: () async {
          final d = await showDatePicker(context: context, initialDate: _warranty ?? DateTime.now(),
              firstDate: DateTime(2000), lastDate: DateTime.now().add(const Duration(days: 3650)));
          if (d != null) setState(() => _warranty = d);
        },
        child: InputDecorator(
          decoration: InputDecoration(labelText: tr('انتهاء الضمان', 'Warranty end'), prefixIcon: const Icon(Icons.verified_rounded, size: 19),
              filled: true, fillColor: Colors.white,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
              enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300))),
          child: Text(_warranty == null ? tr('غير محدد', 'Not set') : '${_warranty!.toLocal()}'.substring(0, 10),
              style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w700)),
        ),
      ),
      const SizedBox(height: 8),
    ];
  }

  Widget _lbl(IconData ic, String t) => Row(children: [
        Icon(ic, size: 16, color: _accent),
        const SizedBox(width: 7),
        Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
      ]);

  Widget _field(TextEditingController c, String label) => TextField(
        controller: c,
        decoration: InputDecoration(labelText: label, filled: true, fillColor: Colors.white, isDense: true,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: _accent, width: 1.5))),
      );
}
