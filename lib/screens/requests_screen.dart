import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'searchable_picker.dart';

/// Service Requests (طلبات الخدمة): a client submits a request and follows it
/// until it becomes a work order — the mockup's "request → closure" path.
class RequestsScreen extends StatefulWidget {
  const RequestsScreen({super.key});
  @override
  State<RequestsScreen> createState() => _RequestsScreenState();
}

class _RequestsScreenState extends State<RequestsScreen> {
  late Future<List<dynamic>> _future;

  static const _stateColor = {
    'new': Color(0xFF2F6DF6), 'in_review': Color(0xFFF59E0B),
    'converted': Color(0xFF16A34A), 'rejected': Color(0xFFE11D48), 'closed': Color(0xFF64748B),
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientRequests();

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: Text(tr('طلبات الخدمة', 'Service requests'))),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _newRequest,
        icon: const Icon(Icons.add),
        label: Text(tr('طلب جديد', 'New request')),
      ),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<List<dynamic>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
            if (snap.hasError) return ListView(children: [const SizedBox(height: 120), Center(child: Text('${snap.error}', style: TextStyle(color: cs.outline)))]);
            final list = snap.data ?? const [];
            if (list.isEmpty) return ListView(children: [const SizedBox(height: 140), Center(child: Text(tr('لا طلبات — أنشئ طلبك الأول.', 'No requests yet.'), style: TextStyle(color: cs.outline)))]);
            return ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: list.length,
              itemBuilder: (_, i) {
                final r = list[i] as Map;
                final c = _stateColor[r['state_raw']] ?? const Color(0xFF64748B);
                return Card(child: ListTile(
                  onTap: () => _openRequest(r),
                  title: Text('${r['title']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                  subtitle: Text('${r['name']} · ${r['facility'] ?? ''}${r['workorder'] != null ? ' · 🛠️ ${r['workorder']}' : ''}',
                      style: TextStyle(color: cs.outline, fontSize: 12)),
                  trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, mainAxisSize: MainAxisSize.min, children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                      decoration: BoxDecoration(color: c.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(12)),
                      child: Text('${r['state'] ?? ''}', style: TextStyle(color: c, fontSize: 11, fontWeight: FontWeight.w800)),
                    ),
                    const SizedBox(height: 2),
                    const Icon(Icons.chevron_left_rounded, size: 16, color: Colors.grey),
                  ]),
                ));
              },
            );
          },
        ),
      ),
    );
  }

  /// A professional request detail sheet with the full data and the actions the
  /// client can take: convert to a work order, cancel, or view the linked WO.
  void _openRequest(Map r) {
    final c = _stateColor[r['state_raw']] ?? const Color(0xFF64748B);
    showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.6, maxChildSize: 0.92,
        builder: (_, sc) => Container(
          decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
          clipBehavior: Clip.antiAlias,
          child: ListView(controller: sc, padding: EdgeInsets.zero, children: [
            Container(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 16),
              decoration: BoxDecoration(gradient: LinearGradient(colors: [c, Color.lerp(c, Colors.black, 0.3)!], begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${r['title']}', style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900))),
                  Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
                      child: Text('${r['state'] ?? ''}', style: TextStyle(color: c, fontSize: 11.5, fontWeight: FontWeight.w900))),
                ]),
                Text('${r['name']}', style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12.5)),
              ]),
            ),
            Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
                child: Column(children: [
                  _kv2(tr('المرفق', 'Facility'), r['facility']),
                  _kv2(tr('الموقع', 'Location'), r['location']),
                  _kv2(tr('الخدمة', 'Service'), r['service']),
                  _kv2(tr('التاريخ', 'Date'), '${r['when'] ?? ''}'.replaceFirst('T', ' ')),
                  if (r['workorder'] != null) _kv2(tr('أمر العمل', 'Work order'), r['workorder']),
                  if (r['reject_reason'] != null) _kv2(tr('سبب الرفض', 'Reject reason'), r['reject_reason']),
                ]),
              ),
              if (r['description'] != null && '${r['description']}'.trim().isNotEmpty) ...[
                const SizedBox(height: 12),
                Container(padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text(tr('الوصف', 'Description'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: Color(0xFF0E3A5F))),
                      const SizedBox(height: 4),
                      Text('${r['description']}', style: TextStyle(fontSize: 12.5, height: 1.5, color: Colors.grey.shade700)),
                    ])),
              ],
              const SizedBox(height: 16),
              // ===== actions =====
              if (r['can_convert'] == true)
                SizedBox(width: double.infinity, child: FilledButton.icon(
                  style: FilledButton.styleFrom(backgroundColor: const Color(0xFF16A34A), padding: const EdgeInsets.symmetric(vertical: 13), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                  onPressed: () => _action(r['id'] as int, 'convert'),
                  icon: const Icon(Icons.build_rounded, size: 18),
                  label: Text(tr('تحويل إلى أمر عمل', 'Convert to work order'), style: const TextStyle(fontWeight: FontWeight.w900)),
                )),
              if (r['can_cancel'] == true) ...[
                const SizedBox(height: 8),
                SizedBox(width: double.infinity, child: OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFE11D48), side: const BorderSide(color: Color(0xFFE11D48)), padding: const EdgeInsets.symmetric(vertical: 12), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                  onPressed: () => _action(r['id'] as int, 'cancel'),
                  icon: const Icon(Icons.close_rounded, size: 18),
                  label: Text(tr('إلغاء الطلب', 'Cancel request'), style: const TextStyle(fontWeight: FontWeight.w800)),
                )),
              ],
              const SizedBox(height: 8),
            ])),
          ]),
        ),
      ),
    );
  }

  Widget _kv2(String k, dynamic v) {
    if (v == null || '$v'.trim().isEmpty) return const SizedBox.shrink();
    return Padding(padding: const EdgeInsets.symmetric(vertical: 9), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      SizedBox(width: 100, child: Text(k, style: TextStyle(fontSize: 12, color: Colors.grey.shade600, fontWeight: FontWeight.w600))),
      Expanded(child: Text('$v', style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700, color: Color(0xFF0E3A5F)))),
    ]));
  }

  Future<void> _action(int id, String kind) async {
    try {
      final api = context.read<AuthProvider>().api;
      if (kind == 'convert') { await api.requestConvert(id); } else { await api.requestCancel(id); }
      if (!mounted) return;
      Navigator.pop(context); // close sheet
      setState(_load);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(kind == 'convert' ? tr('حُوّل الطلب إلى أمر عمل', 'Converted to work order') : tr('أُلغي الطلب', 'Request cancelled')),
        backgroundColor: const Color(0xFF16A34A), behavior: SnackBarBehavior.floating));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  Future<void> _newRequest() async {
    final api = context.read<AuthProvider>().api;
    final facs = await api.facilities();
    final svcs = await api.servicesList();
    // The waste catalogue, so a collection request can say what it is
    // carrying instead of leaving the crew to guess the vehicle.
    Map<String, dynamic> cat = const {'types': [], 'items': []};
    try { cat = await api.wasteCatalogue(); } catch (_) {}
    if (!mounted) return;
    final title = TextEditingController();
    final desc = TextEditingController();
    int? facId = facs.isNotEmpty ? facs.first['id'] as int : null;
    int? svcId;
    int prio = 1;
    var wasteScope = 'general';
    int? wasteTypeId;
    final wasteItems = <int>{};
    final wasteNote = TextEditingController();
    final types = ((cat['types'] as List?) ?? const []).cast<Map>();
    final items = ((cat['items'] as List?) ?? const []).cast<Map>();
    bool isWaste() {
      if (svcId == null) return false;
      final m = svcs.firstWhere((x) => x['id'] == svcId, orElse: () => const {});
      return '${m['type'] ?? ''}' == 'waste';
    }
    final ok = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(18))),
      builder: (ctx) => Padding(
        padding: EdgeInsets.fromLTRB(16, 16, 16, MediaQuery.of(ctx).viewInsets.bottom + 16),
        child: StatefulBuilder(builder: (ctx, set) => Column(mainAxisSize: MainAxisSize.min, children: [
          Text(tr('طلب خدمة جديد', 'New service request'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
          const SizedBox(height: 12),
          TextField(controller: title, decoration: InputDecoration(labelText: tr('عنوان الطلب', 'Title'), border: const OutlineInputBorder(), isDense: true)),
          const SizedBox(height: 10),
          SearchableField(
            label: tr('المرفق', 'Facility'), icon: Icons.apartment_rounded, value: facId, allowClear: false,
            options: [for (final f in facs) PickOption(value: f['id'], label: '${f['name']}')],
            onChanged: (v) => set(() => facId = v as int?)),
          const SizedBox(height: 10),
          SearchableField(
            label: tr('الخدمة (اختياري)', 'Service (optional)'), icon: Icons.design_services_rounded, value: svcId,
            options: [for (final s in svcs) PickOption(value: s['id'], label: '${s['name']}')],
            onChanged: (v) => set(() => svcId = v as int?)),
          // Only asked when it is a collection — every other service would
          // just be answering a question that does not apply to it.
          if (isWaste()) ...[
            const SizedBox(height: 12),
            Align(
              alignment: AlignmentDirectional.centerStart,
              child: Text(tr('ما المطلوب نقله؟', 'What is being collected?'),
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13)),
            ),
            const SizedBox(height: 7),
            SegmentedButton<String>(
              segments: [
                ButtonSegment(value: 'general', label: Text(tr('عام', 'General'))),
                ButtonSegment(value: 'type', label: Text(tr('فئة', 'Category'))),
                ButtonSegment(value: 'items', label: Text(tr('أصناف', 'Items'))),
              ],
              selected: {wasteScope},
              showSelectedIcon: false,
              style: ButtonStyle(
                  visualDensity: VisualDensity.compact,
                  textStyle: WidgetStateProperty.all(
                      const TextStyle(fontSize: 12, fontWeight: FontWeight.w800))),
              onSelectionChanged: (v) => set(() => wasteScope = v.first),
            ),
            if (wasteScope == 'type') ...[
              const SizedBox(height: 10),
              SearchableField(
                label: tr('الفئة', 'Category'), icon: Icons.category_rounded,
                value: wasteTypeId,
                options: [for (final t in types) PickOption(value: t['id'], label: '${t['name']}')],
                onChanged: (v) => set(() => wasteTypeId = v as int?)),
            ],
            if (wasteScope == 'items') ...[
              const SizedBox(height: 8),
              Wrap(spacing: 6, runSpacing: 6, children: [
                for (final it in items)
                  FilterChip(
                    label: Text('${it['name']}', style: const TextStyle(fontSize: 11.5)),
                    selected: wasteItems.contains(intOf(it['id'])),
                    onSelected: (v) => set(() => v
                        ? wasteItems.add(intOf(it['id']))
                        : wasteItems.remove(intOf(it['id']))),
                  ),
              ]),
            ],
            if (wasteScope == 'general') ...[
              const SizedBox(height: 10),
              TextField(controller: wasteNote,
                  decoration: InputDecoration(
                      labelText: tr('وصف المنقولات (اختياري)', 'Describe the load (optional)'),
                      hintText: tr('مثال: أثاث مكتبي قديم', 'e.g. old office furniture'),
                      border: const OutlineInputBorder(), isDense: true)),
            ],
          ],
          const SizedBox(height: 10),
          DropdownButtonFormField<int>(value: prio, isExpanded: true, decoration: InputDecoration(labelText: tr('الأولوية', 'Priority'), border: const OutlineInputBorder(), isDense: true),
              items: const [DropdownMenuItem(value: 0, child: Text('عادية')), DropdownMenuItem(value: 1, child: Text('متوسطة')), DropdownMenuItem(value: 2, child: Text('عالية')), DropdownMenuItem(value: 3, child: Text('عاجلة'))], onChanged: (v) => set(() => prio = v ?? 1)),
          const SizedBox(height: 10),
          TextField(controller: desc, maxLines: 3, decoration: InputDecoration(labelText: tr('الوصف', 'Description'), border: const OutlineInputBorder(), isDense: true)),
          const SizedBox(height: 14),
          SizedBox(width: double.infinity, child: FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(tr('إرسال الطلب', 'Submit')))),
        ])),
      ),
    );
    if (ok != true || title.text.trim().isEmpty) return;
    try {
      await api.createRequest({
        'title': title.text.trim(), 'facility_id': facId, 'service_id': svcId,
        'priority': prio, 'description': desc.text.trim(),
        if (isWaste()) 'waste_scope': wasteScope,
        if (isWaste() && wasteScope == 'type' && wasteTypeId != null)
          'waste_type_id': wasteTypeId,
        if (isWaste() && wasteScope == 'items' && wasteItems.isNotEmpty)
          'waste_item_ids': wasteItems.toList(),
        if (isWaste() && wasteScope == 'general' && wasteNote.text.trim().isNotEmpty)
          'waste_note': wasteNote.text.trim(),
      });
      if (mounted) { ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تم إرسال الطلب', 'Request submitted')))); setState(_load); }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }
}
