import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Live activity feed + current worker locations for the client — sourced from
/// the workers' QR check-ins across the client's facilities.
class ClientActivityScreen extends StatefulWidget {
  const ClientActivityScreen({super.key});
  @override
  State<ClientActivityScreen> createState() => _ClientActivityScreenState();
}

class _ClientActivityScreenState extends State<ClientActivityScreen> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientActivity();

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: Text(tr('النشاط المباشر', 'Live activity'))),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<Map<String, dynamic>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) return Center(child: Text('${snap.error}'));
            final d = snap.data ?? const {};
            final feed = (d['feed'] as List?) ?? const [];
            final live = (d['live'] as List?) ?? const [];
            return ListView(padding: const EdgeInsets.all(14), children: [
              Text(tr('المواقع الحالية للعاملين', 'Current worker locations'),
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
              const SizedBox(height: 8),
              if (live.isEmpty) Text(tr('لا حركة مسجّلة.', 'No movement yet.'), style: TextStyle(color: cs.outline)),
              for (final w in live) _liveTile(w as Map, cs),
              const SizedBox(height: 16),
              Text(tr('سجل الحركة', 'Activity log'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
              const SizedBox(height: 8),
              for (final f in feed) _feedTile(f as Map, cs),
            ]);
          },
        ),
      ),
    );
  }

  Widget _liveTile(Map w, ColorScheme cs) {
    final fresh = w['fresh'] == true;
    final color = fresh ? const Color(0xFF16A34A) : const Color(0xFF94A3B8);
    return Card(child: ListTile(
      leading: _avatar(w),
      title: Text('${w['employee']}', style: const TextStyle(fontWeight: FontWeight.w700)),
      subtitle: Text('📍 ${w['location'] ?? '—'}${w['building'] != null ? ' · ${w['building']}' : ''}',
          style: TextStyle(color: cs.outline, fontSize: 12.5)),
      trailing: Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: color.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(12)),
        child: Text(fresh ? tr('نشط', 'Live') : tr('سابق', 'Past'),
            style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w800)),
      ),
    ));
  }

  Widget _feedTile(Map f, ColorScheme cs) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          _avatar(f, r: 16),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${f['employee'] ?? '—'} · ${f['type'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13)),
            Text('📍 ${f['location'] ?? '—'}${f['building'] != null ? ' · ${f['building']}' : ''}${f['facility'] != null ? ' — ${f['facility']}' : ''}',
                style: TextStyle(color: cs.outline, fontSize: 12)),
            Text('${'${f['when'] ?? ''}'.replaceAll('T', ' ')}', style: TextStyle(color: cs.outline, fontSize: 11)),
          ])),
        ]),
      );

  Widget _avatar(Map m, {double r = 22}) {
    final photo = m['photo'] as String?;
    if (photo != null && photo.startsWith('data:image')) {
      try {
        return CircleAvatar(radius: r, backgroundImage: MemoryImage(base64Decode(photo.split(',').last)));
      } catch (_) {}
    }
    return CircleAvatar(radius: r, child: Text('${m['employee'] ?? '?'}'.characters.first));
  }
}
