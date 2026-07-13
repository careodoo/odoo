import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

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
                  title: Text('${r['title']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                  subtitle: Text('${r['name']} · ${r['facility'] ?? ''}${r['workorder'] != null ? ' · 🛠️ ${r['workorder']}' : ''}',
                      style: TextStyle(color: cs.outline, fontSize: 12)),
                  trailing: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                    decoration: BoxDecoration(color: c.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(12)),
                    child: Text('${r['state'] ?? ''}', style: TextStyle(color: c, fontSize: 11, fontWeight: FontWeight.w800)),
                  ),
                ));
              },
            );
          },
        ),
      ),
    );
  }

  Future<void> _newRequest() async {
    final api = context.read<AuthProvider>().api;
    final facs = await api.facilities();
    final svcs = await api.servicesList();
    if (!mounted) return;
    final title = TextEditingController();
    final desc = TextEditingController();
    int? facId = facs.isNotEmpty ? facs.first['id'] as int : null;
    int? svcId;
    int prio = 1;
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
          DropdownButtonFormField<int>(value: facId, isExpanded: true, decoration: InputDecoration(labelText: tr('المرفق', 'Facility'), border: const OutlineInputBorder(), isDense: true),
              items: [for (final f in facs) DropdownMenuItem(value: f['id'] as int, child: Text('${f['name']}'))], onChanged: (v) => set(() => facId = v)),
          const SizedBox(height: 10),
          DropdownButtonFormField<int>(value: svcId, isExpanded: true, decoration: InputDecoration(labelText: tr('الخدمة (اختياري)', 'Service (optional)'), border: const OutlineInputBorder(), isDense: true),
              items: [const DropdownMenuItem(value: null, child: Text('—')), for (final s in svcs) DropdownMenuItem(value: s['id'] as int, child: Text('${s['name']}'))], onChanged: (v) => set(() => svcId = v)),
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
      await api.createRequest({'title': title.text.trim(), 'facility_id': facId, 'service_id': svcId, 'priority': prio, 'description': desc.text.trim()});
      if (mounted) { ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تم إرسال الطلب', 'Request submitted')))); setState(_load); }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }
}
