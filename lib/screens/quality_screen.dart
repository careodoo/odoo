import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Quality rounds / observations (الجولات والجودة): log an observation, track
/// its severity/state, and convert it into a corrective work order.
class QualityScreen extends StatefulWidget {
  const QualityScreen({super.key});
  @override
  State<QualityScreen> createState() => _QualityScreenState();
}

class _QualityScreenState extends State<QualityScreen> {
  late Future<List<dynamic>> _future;

  static const _sev = {
    'low': Color(0xFF94A3B8), 'medium': Color(0xFF3B82F6), 'high': Color(0xFFF59E0B), 'critical': Color(0xFFE11D48),
  };
  static const _stC = {
    'open': Color(0xFF3B82F6), 'assigned': Color(0xFF6366F1), 'fixing': Color(0xFFF59E0B),
    'reinspect': Color(0xFF7C3AED), 'closed': Color(0xFF16A34A), 'cancelled': Color(0xFF94A3B8),
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientObservations();

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final canConvert = context.read<AuthProvider>().profile?.canAddWorkers ?? false;
    return Scaffold(
      appBar: AppBar(title: Text(tr('الجودة والجولات', 'Quality & rounds'))),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _newObs, icon: const Icon(Icons.add), label: Text(tr('ملاحظة', 'Observation'))),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<List<dynamic>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator());
            if (snap.hasError) return ListView(children: [const SizedBox(height: 120), Center(child: Text('${snap.error}', style: TextStyle(color: cs.outline)))]);
            final list = snap.data ?? const [];
            if (list.isEmpty) return ListView(children: [const SizedBox(height: 140), Center(child: Text(tr('لا ملاحظات', 'No observations'), style: TextStyle(color: cs.outline)))]);
            return ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: list.length,
              itemBuilder: (_, i) {
                final o = list[i] as Map;
                final sv = _sev[o['severity']] ?? const Color(0xFF3B82F6);
                final oc = _stC[o['state']] ?? const Color(0xFF64748B);
                return Card(child: ListTile(
                  onTap: canConvert && o['workorder'] == null ? () => _convert(o['id'] as int) : null,
                  title: Text('${o['title']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                  subtitle: Text('${o['name']} · ${o['facility'] ?? ''}${o['workorder'] != null ? ' · 🛠️ ${o['workorder']}' : ''}',
                      style: TextStyle(color: cs.outline, fontSize: 12)),
                  trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
                    _pill(o['severity_label'], sv),
                    const SizedBox(height: 4),
                    _pill(o['state_label'], oc),
                  ]),
                ));
              },
            );
          },
        ),
      ),
    );
  }

  Widget _pill(dynamic t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(12)),
        child: Text('${t ?? ''}', style: TextStyle(color: c, fontSize: 10.5, fontWeight: FontWeight.w800)),
      );

  Future<void> _convert(int id) async {
    final ok = await showDialog<bool>(context: context, builder: (_) => AlertDialog(
      title: Text(tr('تحويل إلى أمر عمل', 'Convert to work order')),
      content: Text(tr('إنشاء أمر عمل تصحيحي من هذه الملاحظة؟', 'Create a corrective work order?')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(tr('تحويل', 'Convert'))),
      ],
    ));
    if (ok != true) return;
    try {
      await context.read<AuthProvider>().api.observationToWorkOrder(id);
      if (mounted) { ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تم التحويل لأمر عمل', 'Converted')))); setState(_load); }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  Future<void> _newObs() async {
    final api = context.read<AuthProvider>().api;
    final facs = await api.facilities();
    final svcs = await api.servicesList();
    if (!mounted) return;
    final title = TextEditingController();
    final desc = TextEditingController();
    int? facId = facs.isNotEmpty ? facs.first['id'] as int : null;
    int? svcId;
    String sev = 'medium';
    final ok = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(18))),
      builder: (ctx) => Padding(
        padding: EdgeInsets.fromLTRB(16, 16, 16, MediaQuery.of(ctx).viewInsets.bottom + 16),
        child: StatefulBuilder(builder: (ctx, set) => Column(mainAxisSize: MainAxisSize.min, children: [
          Text(tr('ملاحظة جودة جديدة', 'New quality observation'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
          const SizedBox(height: 12),
          TextField(controller: title, decoration: InputDecoration(labelText: tr('الملاحظة', 'Observation'), border: const OutlineInputBorder(), isDense: true)),
          const SizedBox(height: 10),
          DropdownButtonFormField<int>(value: facId, isExpanded: true, decoration: InputDecoration(labelText: tr('المرفق', 'Facility'), border: const OutlineInputBorder(), isDense: true),
              items: [for (final f in facs) DropdownMenuItem(value: f['id'] as int, child: Text('${f['name']}'))], onChanged: (v) => set(() => facId = v)),
          const SizedBox(height: 10),
          DropdownButtonFormField<int>(value: svcId, isExpanded: true, decoration: InputDecoration(labelText: tr('الخدمة (اختياري)', 'Service (optional)'), border: const OutlineInputBorder(), isDense: true),
              items: [const DropdownMenuItem(value: null, child: Text('—')), for (final s in svcs) DropdownMenuItem(value: s['id'] as int, child: Text('${s['name']}'))], onChanged: (v) => set(() => svcId = v)),
          const SizedBox(height: 10),
          DropdownButtonFormField<String>(value: sev, isExpanded: true, decoration: InputDecoration(labelText: tr('الخطورة', 'Severity'), border: const OutlineInputBorder(), isDense: true),
              items: [
                DropdownMenuItem(value: 'low', child: Text(tr('منخفضة', 'Low'))),
                DropdownMenuItem(value: 'medium', child: Text(tr('متوسطة', 'Medium'))),
                DropdownMenuItem(value: 'high', child: Text(tr('عالية', 'High'))),
                DropdownMenuItem(value: 'critical', child: Text(tr('حرجة', 'Critical'))),
              ], onChanged: (v) => set(() => sev = v ?? 'medium')),
          const SizedBox(height: 10),
          TextField(controller: desc, maxLines: 2, decoration: InputDecoration(labelText: tr('الوصف', 'Description'), border: const OutlineInputBorder(), isDense: true)),
          const SizedBox(height: 14),
          SizedBox(width: double.infinity, child: FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(tr('تسجيل', 'Log')))),
        ])),
      ),
    );
    if (ok != true || title.text.trim().isEmpty) return;
    try {
      await api.createObservation({'title': title.text.trim(), 'facility_id': facId, 'service_id': svcId, 'severity': sev, 'description': desc.text.trim()});
      if (mounted) { ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('سُجّلت الملاحظة', 'Recorded')))); setState(_load); }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }
}
