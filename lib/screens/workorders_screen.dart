import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import '../models/models.dart';
import 'work_order_detail_screen.dart';

class WorkOrdersScreen extends StatefulWidget {
  const WorkOrdersScreen({super.key});
  @override
  State<WorkOrdersScreen> createState() => _WorkOrdersScreenState();
}

class _WorkOrdersScreenState extends State<WorkOrdersScreen> {
  late Future<List<WorkOrder>> _future;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    final api = context.read<AuthProvider>().api;
    _future = api.workOrders().then((l) => [for (final j in l) WorkOrder.fromJson(j as Map)]);
  }

  Future<void> _act(WorkOrder w, bool start) async {
    final api = context.read<AuthProvider>().api;
    try {
      start ? await api.workOrderStart(w.id) : await api.workOrderDone(w.id);
      setState(_load);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(tr('أوامر العمل', 'Work orders'))),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<List<WorkOrder>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return _Center(text: 'خطأ: ${snap.error}');
            }
            final items = snap.data ?? const [];
            if (items.isEmpty) return const _Center(text: 'لا توجد أوامر عمل حالياً.');
            return ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: items.length,
              itemBuilder: (_, i) => _WoCard(w: items[i], onStart: () => _act(items[i], true), onDone: () => _act(items[i], false)),
            );
          },
        ),
      ),
    );
  }
}

class _WoCard extends StatelessWidget {
  const _WoCard({required this.w, required this.onStart, required this.onDone});
  final WorkOrder w;
  final VoidCallback onStart;
  final VoidCallback onDone;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => Navigator.push(context, MaterialPageRoute(
            builder: (_) => WorkOrderDetailScreen(id: w.id, title: w.title))),
        child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(child: Text(w.title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w800))),
                WoStateBadge(w.state),
              ],
            ),
            const SizedBox(height: 4),
            Text('${w.name} · ${w.facility}${w.location != null ? ' · ${w.location}' : ''}',
                style: TextStyle(color: cs.outline, fontSize: 13)),
            if (w.deadline != null)
              Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text('الموعد: ${w.deadline}', style: TextStyle(color: cs.outline, fontSize: 12)),
              ),
            const SizedBox(height: 12),
            Row(
              children: [
                if (!w.inProgress && w.isOpen)
                  Expanded(
                    child: FilledButton.icon(
                      onPressed: onStart,
                      icon: const Icon(Icons.play_arrow),
                      label: Text(tr('امسح للبدء', 'Scan to start')),
                    ),
                  ),
                if (w.inProgress)
                  Expanded(
                    child: FilledButton.icon(
                      style: FilledButton.styleFrom(backgroundColor: const Color(0xFF16794A)),
                      onPressed: onDone,
                      icon: const Icon(Icons.check),
                      label: Text(tr('تم — أوقف العدّاد', 'Done — stop timer')),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
      ),
    );
  }
}

class _Center extends StatelessWidget {
  const _Center({required this.text});
  final String text;
  @override
  Widget build(BuildContext context) => ListView(
        children: [
          const SizedBox(height: 120),
          Center(child: Text(text, style: TextStyle(color: Theme.of(context).colorScheme.outline))),
        ],
      );
}
