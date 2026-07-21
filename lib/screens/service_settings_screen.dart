import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// More → service settings. Each service the client has is a card of toggles:
/// which notifications they get for it, and whether they receive a weekly
/// digest. Client-specific, per service.
class ServiceSettingsScreen extends StatefulWidget {
  const ServiceSettingsScreen({super.key});
  @override
  State<ServiceSettingsScreen> createState() => _ServiceSettingsScreenState();
}

class _ServiceSettingsScreenState extends State<ServiceSettingsScreen> {
  static const _accent = Color(0xFF6366F1);
  Future<List<dynamic>>? _f;
  final _saving = <String>{};

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _f = context.read<AuthProvider>().api.serviceSettings();

  Future<void> _save(Map svc, String key, bool value) async {
    final code = '${svc['code']}';
    final prefs = Map<String, dynamic>.from(svc['prefs'] as Map);
    prefs[key] = value;
    setState(() { svc['prefs'] = prefs; _saving.add(code); });
    try {
      await context.read<AuthProvider>().api.saveServiceSetting(code, {key: value});
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('$e'), backgroundColor: const Color(0xFFE11D48)));
    } finally {
      if (mounted) setState(() => _saving.remove(code));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      appBar: AppBar(title: Text(tr('إعدادات الخدمات', 'Service settings'))),
      body: FutureBuilder<List<dynamic>>(
        future: _f,
        builder: (_, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator(color: _accent));
          }
          if (snap.hasError) {
            return Center(child: Text('${snap.error}', style: const TextStyle(color: Colors.black54)));
          }
          final services = (snap.data ?? const []).cast<Map>();
          if (services.isEmpty) {
            return Center(child: Text(tr('لا خدمات', 'No services'),
                style: const TextStyle(color: Colors.black54)));
          }
          return ListView(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 24),
            children: [
              Padding(padding: const EdgeInsets.only(bottom: 6, left: 4, right: 4),
                  child: Text(tr('تحكّم في إشعارات وتقارير كل خدمة على حدة.',
                      'Control notifications and reports for each service.'),
                      style: const TextStyle(color: Colors.black54, fontSize: 12.5))),
              for (final s in services) _serviceCard(s),
            ],
          );
        },
      ),
    );
  }

  Widget _serviceCard(Map s) {
    final prefs = (s['prefs'] as Map?) ?? const {};
    final busy = _saving.contains('${s['code']}');
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
          border: Border.all(color: const Color(0xFFE3E7EE))),
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          leading: Text('${s['icon'] ?? '🧩'}', style: const TextStyle(fontSize: 22)),
          title: Text('${s['name'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w800)),
          subtitle: busy ? Text(tr('يحفظ…', 'Saving…'), style: const TextStyle(fontSize: 11, color: _accent)) : null,
          childrenPadding: const EdgeInsets.fromLTRB(8, 0, 8, 8),
          children: [
            _toggle(s, 'notify_new', prefs['notify_new'] == true,
                tr('إشعار عند عمل جديد', 'Notify on new work')),
            _toggle(s, 'notify_done', prefs['notify_done'] == true,
                tr('إشعار عند الإنجاز', 'Notify on completion')),
            _toggle(s, 'notify_overdue', prefs['notify_overdue'] == true,
                tr('إشعار عند التأخّر', 'Notify when overdue')),
            _toggle(s, 'weekly_report', prefs['weekly_report'] == true,
                tr('تقرير أسبوعي', 'Weekly report')),
          ],
        ),
      ),
    );
  }

  Widget _toggle(Map s, String key, bool value, String label) => SwitchListTile(
        dense: true,
        activeColor: _accent,
        contentPadding: const EdgeInsets.symmetric(horizontal: 8),
        title: Text(label, style: const TextStyle(fontSize: 13.5)),
        value: value,
        onChanged: (v) => _save(s, key, v),
      );
}
