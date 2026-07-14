import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Client broadcast: send a notification to all/late/team/service/worker,
/// with a sent log showing recipients & read counts.
class NotifySendScreen extends StatefulWidget {
  const NotifySendScreen({super.key});
  @override
  State<NotifySendScreen> createState() => _NotifySendScreenState();
}

class _NotifySendScreenState extends State<NotifySendScreen> {
  Map<String, dynamic>? _opts;
  List<dynamic> _sent = [];
  final _title = TextEditingController();
  final _body = TextEditingController();
  String _audience = 'all';
  int? _teamId;
  String? _serviceType;
  int? _workerId;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final o = await context.read<AuthProvider>().api.notifyOptions();
      final s = await context.read<AuthProvider>().api.notifySent();
      if (mounted) setState(() {
            _opts = o;
            _sent = s;
          });
    } catch (_) {}
  }

  Future<void> _send() async {
    if (_title.text.trim().isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('أدخل العنوان', 'Enter title'))));
      return;
    }
    final body = <String, dynamic>{'audience': _audience, 'title': _title.text.trim(), 'body': _body.text.trim()};
    if (_audience == 'team') body['team_id'] = _teamId;
    if (_audience == 'service') body['service_type'] = _serviceType;
    if (_audience == 'worker') body['employee_id'] = _workerId;
    try {
      final r = await context.read<AuthProvider>().api.notifySend(body);
      if (!mounted) return;
      _title.clear();
      _body.clear();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('${tr('أُرسل إلى', 'Sent to')} ${r['recipients']}')));
      _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final o = _opts;
    return Scaffold(
      appBar: AppBar(title: Text(tr('إرسال إشعار', 'Send notification'))),
      body: o == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(14), children: [
              DropdownButtonFormField<String>(
                value: _audience,
                decoration: InputDecoration(labelText: tr('إلى', 'To'), border: const OutlineInputBorder()),
                items: [
                  DropdownMenuItem(value: 'all', child: Text(tr('كل العاملين', 'All workers'))),
                  DropdownMenuItem(value: 'late', child: Text(tr('العاملون المتأخرون', 'Late workers'))),
                  DropdownMenuItem(value: 'team', child: Text(tr('فريق', 'Team'))),
                  DropdownMenuItem(value: 'service', child: Text(tr('خدمة', 'Service'))),
                  DropdownMenuItem(value: 'worker', child: Text(tr('عامل محدّد', 'Specific worker'))),
                ],
                onChanged: (v) => setState(() => _audience = v!),
              ),
              const SizedBox(height: 10),
              if (_audience == 'team')
                _dropdown(tr('الفريق', 'Team'), (o['teams'] as List), _teamId, (v) => setState(() => _teamId = v)),
              if (_audience == 'service')
                _dropdownStr(tr('الخدمة', 'Service'), (o['services'] as List), _serviceType, (v) => setState(() => _serviceType = v)),
              if (_audience == 'worker')
                _dropdown(tr('العامل', 'Worker'), (o['workers'] as List), _workerId, (v) => setState(() => _workerId = v)),
              const SizedBox(height: 10),
              TextField(controller: _title, decoration: InputDecoration(labelText: tr('العنوان', 'Title'), border: const OutlineInputBorder())),
              const SizedBox(height: 10),
              TextField(controller: _body, maxLines: 3, decoration: InputDecoration(labelText: tr('النص', 'Message'), border: const OutlineInputBorder())),
              const SizedBox(height: 12),
              SizedBox(width: double.infinity, child: FilledButton.icon(onPressed: _send, icon: const Icon(Icons.send), label: Text(tr('إرسال', 'Send')))),
              const Divider(height: 30),
              Text(tr('سجل الإشعارات المُرسَلة', 'Sent log'), style: const TextStyle(fontWeight: FontWeight.w800)),
              if (_sent.isEmpty) Padding(padding: const EdgeInsets.all(16), child: Text(tr('لم تُرسِل إشعارات بعد', 'No notifications sent yet'))),
              ..._sent.map((g) => ListTile(
                    title: Text('${g['title']}'),
                    subtitle: Text('${g['date'] ?? ''}'),
                    trailing: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(color: Colors.green.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
                      child: Text('${g['read']}/${g['total']}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12)),
                    ),
                  )),
            ]),
    );
  }

  Widget _dropdown(String label, List items, int? val, ValueChanged<int?> onCh) => DropdownButtonFormField<int>(
        value: val,
        decoration: InputDecoration(labelText: label, border: const OutlineInputBorder()),
        items: items.map<DropdownMenuItem<int>>((x) => DropdownMenuItem(value: x['id'] as int, child: Text('${x['name']}'))).toList(),
        onChanged: onCh,
      );

  Widget _dropdownStr(String label, List items, String? val, ValueChanged<String?> onCh) => DropdownButtonFormField<String>(
        value: val,
        decoration: InputDecoration(labelText: label, border: const OutlineInputBorder()),
        items: items.map<DropdownMenuItem<String>>((x) => DropdownMenuItem(value: '${x['v']}', child: Text('${x['l']}'))).toList(),
        onChanged: onCh,
      );
}
