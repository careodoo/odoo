import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'work_order_detail_screen.dart';

/// All work orders across the client's facilities, filterable by state — the
/// client's "أوامر العمل" tab.
class ClientWorkOrdersScreen extends StatefulWidget {
  const ClientWorkOrdersScreen({super.key});
  @override
  State<ClientWorkOrdersScreen> createState() => _ClientWorkOrdersScreenState();
}

class _ClientWorkOrdersScreenState extends State<ClientWorkOrdersScreen> {
  String _state = 'all';
  Future<List<dynamic>>? _future;

  static const _filters = [
    ('all', 'الكل', 'All'), ('open', 'مفتوحة', 'Open'),
    ('in_progress', 'جارية', 'Active'), ('done', 'للاعتماد', 'To approve'),
    ('verified', 'مُعتمدة', 'Approved'),
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientWorkOrders(state: _state);

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: Text(tr('أوامر العمل', 'Work orders'))),
      body: Column(children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          child: Row(children: [
            for (final f in _filters)
              Padding(padding: const EdgeInsets.only(left: 6), child: ChoiceChip(
                label: Text(tr(f.$2, f.$3)), selected: _state == f.$1,
                onSelected: (_) => setState(() { _state = f.$1; _load(); }),
              )),
          ]),
        ),
        Expanded(child: RefreshIndicator(
          onRefresh: () async => setState(_load),
          child: FutureBuilder<List<dynamic>>(
            future: _future,
            builder: (context, snap) {
              if (snap.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snap.hasError) return ListView(children: [const SizedBox(height: 120), Center(child: Text('${snap.error}', style: TextStyle(color: cs.outline)))]);
              final wos = snap.data ?? const [];
              if (wos.isEmpty) return ListView(children: [const SizedBox(height: 140), Center(child: Text(tr('لا أوامر عمل.', 'No work orders.'), style: TextStyle(color: cs.outline)))]);
              return ListView.builder(
                padding: const EdgeInsets.all(12),
                itemCount: wos.length,
                itemBuilder: (_, i) {
                  final w = wos[i] as Map;
                  return Card(child: ListTile(
                    title: Text('${w['title']}', style: const TextStyle(fontWeight: FontWeight.w700)),
                    subtitle: Text('${w['name']} · ${w['facility']}${w['location'] != null ? ' · ${w['location']}' : ''}',
                        style: TextStyle(color: cs.outline, fontSize: 12)),
                    trailing: WoStateBadge('${w['state']}'),
                    onTap: () => Navigator.push(context, MaterialPageRoute(
                        builder: (_) => WorkOrderDetailScreen(id: w['id'] as int, title: '${w['title']}'))),
                  ));
                },
              );
            },
          ),
        )),
      ]),
    );
  }
}
