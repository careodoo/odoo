import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';

class FacilityDetailScreen extends StatefulWidget {
  const FacilityDetailScreen({super.key, required this.facilityId, required this.name});
  final int facilityId;
  final String name;
  @override
  State<FacilityDetailScreen> createState() => _FacilityDetailScreenState();
}

class _FacilityDetailScreenState extends State<FacilityDetailScreen> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = context.read<AuthProvider>().api.clientFacility(widget.facilityId);
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: Text(widget.name)),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Center(child: Text('خطأ: ${snap.error}'));
          }
          final d = snap.data!;
          final buildings = (d['buildings'] as List?) ?? const [];
          final locations = (d['locations'] as List?) ?? const [];
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              if (d['address'] != null)
                Card(child: ListTile(leading: const Icon(Icons.place), title: Text('${d['address']}'))),
              const SizedBox(height: 8),
              Text('المباني (${buildings.length})', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
              for (final b in buildings)
                Card(child: ListTile(
                  leading: const Icon(Icons.apartment),
                  title: Text('${(b as Map)['name']}'),
                  trailing: Text('أدوار: ${b['floors']}', style: TextStyle(color: cs.outline)),
                )),
              const SizedBox(height: 12),
              Text('المواقع (QR) — ${locations.length}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
              for (final l in locations)
                Card(child: ListTile(
                  dense: true,
                  leading: Icon((l as Map)['checkpoint'] == true ? Icons.verified_user : Icons.qr_code, color: cs.primary),
                  title: Text('${l['name']}'),
                  subtitle: Text('${l['code']} · ${l['type']}', style: TextStyle(color: cs.outline, fontSize: 12)),
                )),
            ],
          );
        },
      ),
    );
  }
}
