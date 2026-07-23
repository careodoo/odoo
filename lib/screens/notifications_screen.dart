import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/deeplink.dart';
import 'generic_record_screen.dart';

class NotificationsScreen extends StatefulWidget {
  const NotificationsScreen({super.key});
  @override
  State<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends State<NotificationsScreen> {
  late Future<(List<dynamic>, int)> _future;

  static const _typeMeta = {
    'info': (Icons.info, Color(0xFF2F6DF6), 'معلومة'),
    'task': (Icons.assignment, Color(0xFF37C98A), 'مهمة'),
    'warning': (Icons.warning_amber, Color(0xFFF7A23B), 'تنبيه'),
    'alert': (Icons.error, Color(0xFFE5484D), 'طوارئ'),
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.notifications();

  Future<void> _readAll() async {
    await context.read<AuthProvider>().api.markAllNotifsRead();
    if (mounted) setState(_load);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(tr('الإشعارات', 'Notifications')),
        actions: [
          TextButton(
            onPressed: _readAll,
            child: Text(tr('تعليم الكل مقروء', 'Mark all read'), style: const TextStyle(color: Colors.white, fontSize: 12)),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<(List<dynamic>, int)>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return _msg('خطأ: ${snap.error}');
            }
            final items = snap.data?.$1 ?? const [];
            if (items.isEmpty) return _msg(tr('لا إشعارات.', 'No notifications.'));
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
        const SizedBox(height: 140),
        Center(child: Text(t, style: TextStyle(color: Theme.of(context).colorScheme.outline))),
      ]);

  Widget _card(Map n) {
    final meta = _typeMeta[n['type']] ?? _typeMeta['info']!;
    final read = n['is_read'] == true;
    return Card(
      child: ListTile(
        // Tapping a notification now OPENS its record (and marks it read).
        onTap: () async {
          if (!read) {
            await context.read<AuthProvider>().api.markNotifRead(n['id'] as int);
            if (mounted) setState(_load);
          }
          if (mounted) {
            var opened = openActionUrl(context, n['action_url'] as String?);
            // fall back to the generic record viewer via res_model/res_id
            if (!opened && n['res_model'] != null && n['res_id'] != null) {
              Navigator.push(context, MaterialPageRoute(builder: (_) => GenericRecordScreen(
                  model: '${n['res_model']}', recordId: n['res_id'] as int, title: '${n['title']}')));
              opened = true;
            }
            if (!opened && mounted) {
              ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                content: Text(tr('لا سجل مرتبط بهذا الإشعار', 'No record linked to this notification')),
                behavior: SnackBarBehavior.floating));
            }
          }
        },
        leading: CircleAvatar(backgroundColor: meta.$2.withValues(alpha: 0.15), child: Icon(meta.$1, color: meta.$2)),
        title: Text('${n['title']}',
            style: TextStyle(fontWeight: read ? FontWeight.w500 : FontWeight.w800)),
        subtitle: Text('${n['body'] ?? ''}\n${n['author'] ?? ''} · ${n['date'] ?? ''}',
            style: TextStyle(color: Theme.of(context).colorScheme.outline, fontSize: 12)),
        isThreeLine: true,
        trailing: read ? null : Container(width: 10, height: 10, decoration: BoxDecoration(color: meta.$2, shape: BoxShape.circle)),
      ),
    );
  }
}
