import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'employee_profile_screen.dart';

const Map<String, Color> kStatusColor = {
  'on_task': Color(0xFF16A34A),
  'available': Color(0xFF2F6DF6),
  'recent': Color(0xFFF59E0B),
  'off': Color(0xFF94A3B8),
};
String statusLabel(String s) => {
      'on_task': tr('ينفّذ مهمة', 'On task'),
      'available': tr('متاح', 'Available'),
      'recent': tr('نشاط حديث', 'Recent'),
      'off': tr('خارج الوردية', 'Off'),
    }[s] ??
    s;

/// Client roster: every worker serving the client's sites, with photo, live
/// status and current location. Tapping opens the full profile + statistics.
class ClientTeamScreen extends StatefulWidget {
  const ClientTeamScreen({super.key});
  @override
  State<ClientTeamScreen> createState() => _ClientTeamScreenState();
}

class _ClientTeamScreenState extends State<ClientTeamScreen> {
  late Future<List<dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientTeam();

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: Text(tr('الفريق', 'Team'))),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<List<dynamic>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) return Center(child: Text('${snap.error}'));
            final team = snap.data ?? const [];
            if (team.isEmpty) {
              return ListView(children: [
                const SizedBox(height: 140),
                Center(child: Text(tr('لا عاملين بعد.', 'No workers yet.'), style: TextStyle(color: cs.outline))),
              ]);
            }
            return ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: team.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) => _tile(team[i] as Map, cs),
            );
          },
        ),
      ),
    );
  }

  Widget _tile(Map m, ColorScheme cs) {
    final status = '${m['status'] ?? 'off'}';
    final color = kStatusColor[status] ?? const Color(0xFF94A3B8);
    return Card(
      child: ListTile(
        onTap: () => Navigator.push(context, MaterialPageRoute(
            builder: (_) => EmployeeProfileScreen(employeeId: m['id'] as int, name: '${m['name']}'))),
        leading: Stack(children: [
          _avatar(m, 24),
          Positioned(bottom: 0, right: 0, child: Container(
            width: 14, height: 14,
            decoration: BoxDecoration(color: color, shape: BoxShape.circle, border: Border.all(color: cs.surface, width: 2)),
          )),
        ]),
        title: Text('${m['name']}', style: const TextStyle(fontWeight: FontWeight.w800)),
        subtitle: Text([
          if (m['job'] != null) '${m['job']}',
          if (m['current_location'] != null) '📍 ${m['current_location']}${m['building'] != null ? ' · ${m['building']}' : ''}',
        ].join('\n'), style: TextStyle(color: cs.outline, fontSize: 12.5)),
        isThreeLine: m['job'] != null && m['current_location'] != null,
        trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(color: color.withValues(alpha: 0.15), borderRadius: BorderRadius.circular(12)),
            child: Text(statusLabel(status), style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w800)),
          ),
          const SizedBox(height: 4),
          Text('${tr('مفتوحة', 'Open')} ${m['open_tasks'] ?? 0}', style: TextStyle(color: cs.outline, fontSize: 11)),
        ]),
      ),
    );
  }

  static Widget _avatar(Map m, double r) {
    final photo = m['photo'] as String?;
    if (photo != null && photo.startsWith('data:image')) {
      try {
        return CircleAvatar(radius: r, backgroundImage: MemoryImage(base64Decode(photo.split(',').last)));
      } catch (_) {}
    }
    return CircleAvatar(radius: r, child: Text('${m['name'] ?? '?'}'.characters.first));
  }
}
