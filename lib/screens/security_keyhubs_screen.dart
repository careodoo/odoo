import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Key custody board — hubs, the keys inside each, their NFC tag, who holds
/// them now, and the latest in/out log. Read-only mirror of security_management.
class SecurityKeyhubsScreen extends StatefulWidget {
  const SecurityKeyhubsScreen({super.key});
  @override
  State<SecurityKeyhubsScreen> createState() => _SecurityKeyhubsScreenState();
}

class _SecurityKeyhubsScreenState extends State<SecurityKeyhubsScreen> {
  static const _accent = Color(0xFFB45309);
  Future<List<dynamic>>? _f;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _f = context.read<AuthProvider>().api.securityKeyhubs();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      appBar: AppBar(
        backgroundColor: _accent, foregroundColor: Colors.white,
        title: Text(tr('هبات المفاتيح', 'Key hubs'),
            style: const TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: FutureBuilder<List<dynamic>>(
        future: _f,
        builder: (_, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator(color: _accent));
          }
          if (snap.hasError) {
            return Center(child: Text('${snap.error}', style: const TextStyle(color: Colors.black54)));
          }
          final hubs = (snap.data ?? const []).cast<Map>();
          if (hubs.isEmpty) {
            return RefreshIndicator(
              onRefresh: () async => setState(_load),
              child: ListView(children: [
                const SizedBox(height: 160),
                Center(child: Text(tr('لا لوحات مفاتيح', 'No key hubs'),
                    style: const TextStyle(color: Colors.black54))),
              ]),
            );
          }
          return RefreshIndicator(
            color: _accent,
            onRefresh: () async => setState(_load),
            child: ListView(
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 24),
              children: [for (final h in hubs) _hubCard(h)],
            ),
          );
        },
      ),
    );
  }

  Widget _hubCard(Map h) {
    final keys = (h['keys'] as List?) ?? const [];
    final out = h['out_count'] ?? 0;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFE3E7EE))),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          leading: CircleAvatar(backgroundColor: _accent.withOpacity(0.12),
              child: const Icon(Icons.vpn_key_rounded, color: _accent, size: 20)),
          title: Text('${h['name'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14)),
          subtitle: Text([
            if (h['code'] != null) '${h['code']}',
            if (h['location'] != null) '📍 ${h['location']}',
            if (h['responsible'] != null) '👤 ${h['responsible']}',
          ].join(' · '), style: const TextStyle(fontSize: 11.5, color: Colors.black54)),
          trailing: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            Text('${h['key_count'] ?? 0}', style: const TextStyle(fontWeight: FontWeight.w900, color: _accent)),
            Text('${tr('خارج', 'out')} $out', style: const TextStyle(fontSize: 10, color: Colors.black45)),
          ]),
          childrenPadding: const EdgeInsets.fromLTRB(10, 0, 10, 8),
          children: [for (final k in keys.cast<Map>()) _keyRow(k)],
        ),
      ),
    );
  }

  Widget _keyRow(Map k) {
    final out = k['state'] == 'checked_out';
    final c = out ? const Color(0xFFE11D48) : const Color(0xFF16A34A);
    final logs = (k['logs'] as List?) ?? const [];
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(color: const Color(0xFFF8F9FB), borderRadius: BorderRadius.circular(12)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.key_rounded, size: 16, color: Colors.black45),
          const SizedBox(width: 6),
          Expanded(child: Text('${k['name'] ?? ''} · ${tr('باب', 'door')} ${k['door'] ?? '—'}',
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5))),
          Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(color: c.withOpacity(0.14), borderRadius: BorderRadius.circular(20)),
              child: Text('${k['state_label'] ?? ''}', style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 10.5))),
        ]),
        const SizedBox(height: 3),
        Text([
          '🔢 ${k['key_number'] ?? '—'}',
          if (k['nfc'] != null) '📡 ${k['nfc']}',
          if (k['holder'] != null) '👤 ${k['holder']}',
          if (k['out_since'] != null) '🕒 ${k['out_since']}',
        ].join(' · '), style: const TextStyle(fontSize: 11, color: Colors.black54)),
        if (logs.isNotEmpty) ...[
          const Divider(height: 12),
          for (final l in logs.cast<Map>().take(3))
            Padding(padding: const EdgeInsets.only(bottom: 2),
                child: Text('• ${l['op'] ?? ''} — ${l['by'] ?? '—'} · ${l['at'] ?? ''}',
                    style: const TextStyle(fontSize: 10.5, color: Colors.black45))),
        ],
      ]),
    );
  }
}
