import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Generic Security Manager section list (guards / teams / schedules / patrol
/// points / logs / inspections / tasks) — mirrors the backend module sections.
class SecuritySectionScreen extends StatefulWidget {
  const SecuritySectionScreen({super.key, required this.kind, required this.title});
  final String kind;
  final String title;
  @override
  State<SecuritySectionScreen> createState() => _SecuritySectionScreenState();
}

class _SecuritySectionScreenState extends State<SecuritySectionScreen> {
  late Future<List<dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.securityData(widget.kind);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0B1220),
      appBar: AppBar(title: Text(widget.title)),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<List<dynamic>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) return _msg('${snap.error}');
            final items = snap.data ?? const [];
            if (items.isEmpty) return _msg(tr('لا عناصر.', 'No items.'));
            return ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: items.length,
              separatorBuilder: (_, __) => const SizedBox(height: 6),
              itemBuilder: (_, i) => _card(items[i] as Map),
            );
          },
        ),
      ),
    );
  }

  Widget _msg(String t) => ListView(children: [
        const SizedBox(height: 130),
        Center(child: Text(t, style: const TextStyle(color: Color(0xFF9CB2CD)))),
      ]);

  Widget _card(Map m) {
    return Card(
      color: const Color(0xFF152238),
      child: ListTile(
        onTap: m['id'] != null ? () => _openDetail(m['id'] as int) : null,
        title: Text('${m['title'] ?? ''}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
        subtitle: Text([m['sub'], m['meta']].where((e) => e != null && '$e'.isNotEmpty).join('\n'),
            style: const TextStyle(color: Color(0xFF9CB2CD), fontSize: 12.5)),
        isThreeLine: (m['sub'] != null && m['meta'] != null),
        trailing: Row(mainAxisSize: MainAxisSize.min, children: [
          if (m['status'] != null && '${m['status']}'.isNotEmpty)
            Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(color: const Color(0xFF1E3A5F), borderRadius: BorderRadius.circular(20)),
                child: Text('${m['status']}', style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700))),
          const SizedBox(width: 4),
          const Icon(Icons.chevron_left, color: Color(0xFF6E86A6), size: 20),
        ]),
      ),
    );
  }

  void _openDetail(int id) {
    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF0F1B30),
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(18))),
      builder: (_) => FractionallySizedBox(
        heightFactor: 0.7,
        child: FutureBuilder<Map<String, dynamic>>(
          future: context.read<AuthProvider>().api.securityRecord(widget.kind, id),
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return Center(child: Text('${snap.error}', style: const TextStyle(color: Color(0xFF9CB2CD))));
            }
            final d = snap.data ?? const {};
            final rows = (d['rows'] as List?) ?? const [];
            return Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Container(
                padding: const EdgeInsets.fromLTRB(18, 16, 18, 12),
                child: Row(children: [
                  const Icon(Icons.shield, color: Color(0xFF4F9BD9)),
                  const SizedBox(width: 10),
                  Expanded(child: Text('${d['title'] ?? widget.title}',
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 16))),
                  IconButton(onPressed: () => Navigator.pop(context), icon: const Icon(Icons.close, color: Color(0xFF9CB2CD))),
                ]),
              ),
              const Divider(height: 1, color: Color(0xFF22304A)),
              Expanded(
                child: ListView.separated(
                  padding: const EdgeInsets.all(18),
                  itemCount: rows.length,
                  separatorBuilder: (_, __) => const Divider(height: 18, color: Color(0xFF1B2942)),
                  itemBuilder: (_, i) {
                    final r = rows[i] as Map;
                    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${r['label']}', style: const TextStyle(color: Color(0xFF6E86A6), fontSize: 12)),
                      const SizedBox(height: 3),
                      Text('${r['value']}', style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w600)),
                    ]);
                  },
                ),
              ),
            ]);
          },
        ),
      ),
    );
  }
}
