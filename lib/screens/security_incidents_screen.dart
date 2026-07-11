import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';

/// Security incidents: list recent + report a new one. Writes straight into
/// Security Manager (security.incident.report) via /api/v1/security/incidents.
class SecurityIncidentsScreen extends StatefulWidget {
  const SecurityIncidentsScreen({super.key});
  @override
  State<SecurityIncidentsScreen> createState() => _SecurityIncidentsScreenState();
}

class _SecurityIncidentsScreenState extends State<SecurityIncidentsScreen> {
  late Future<List<dynamic>> _future;

  static const types = {
    'theft': 'سرقة/سطو', 'vandalism': 'تخريب', 'trespassing': 'تسلّل',
    'assault': 'اعتداء', 'fire': 'حريق', 'medical': 'طارئ طبي',
    'suspicious': 'نشاط مشبوه', 'other': 'أخرى',
  };
  static const severities = {'low': 'منخفض', 'medium': 'متوسط', 'high': 'عالٍ', 'critical': 'حرج'};

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _future = context.read<AuthProvider>().api.securityList('incidents');
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0B1220),
      appBar: AppBar(title: const Text('البلاغات الأمنية')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _openForm,
        icon: const Icon(Icons.add_alert),
        label: const Text('تسجيل حادث'),
        backgroundColor: const Color(0xFFE5484D),
      ),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<List<dynamic>>(
          future: _future,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return _msg('خطأ: ${snap.error}');
            }
            final items = snap.data ?? const [];
            if (items.isEmpty) return _msg('لا بلاغات مسجّلة.');
            return ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: items.length,
              itemBuilder: (_, i) => _card(items[i] as Map),
            );
          },
        ),
      ),
    );
  }

  Widget _msg(String t) => ListView(children: [
        const SizedBox(height: 120),
        Center(child: Text(t, style: const TextStyle(color: Color(0xFF9CB2CD)))),
      ]);

  Color _sevColor(String s) => switch (s) {
        'critical' => const Color(0xFFE5484D),
        'high' => const Color(0xFFF2603F),
        'medium' => const Color(0xFFF7A23B),
        _ => const Color(0xFF37C98A),
      };

  Widget _card(Map i) {
    return Card(
      color: const Color(0xFF152238),
      child: ListTile(
        leading: CircleAvatar(
          backgroundColor: _sevColor(i['severity'] as String? ?? 'low'),
          child: const Icon(Icons.warning_amber, color: Colors.white, size: 20),
        ),
        title: Text('${i['name']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
        subtitle: Text(
          '${types[i['type']] ?? i['type']} · ${severities[i['severity']] ?? i['severity']}\n${i['description'] ?? ''}',
          style: const TextStyle(color: Color(0xFF9CB2CD)),
        ),
        isThreeLine: true,
      ),
    );
  }

  void _openForm() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: const Color(0xFF152238),
      builder: (_) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
        child: _IncidentForm(onSaved: () {
          Navigator.pop(context);
          setState(_load);
        }),
      ),
    );
  }
}

class _IncidentForm extends StatefulWidget {
  const _IncidentForm({required this.onSaved});
  final VoidCallback onSaved;
  @override
  State<_IncidentForm> createState() => _IncidentFormState();
}

class _IncidentFormState extends State<_IncidentForm> {
  String _type = 'suspicious';
  String _sev = 'medium';
  final _desc = TextEditingController();
  bool _busy = false;

  @override
  void dispose() {
    _desc.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (_desc.text.trim().isEmpty) return;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.createIncident(
          type: _type, severity: _sev, description: _desc.text.trim());
      widget.onSaved();
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    const white = TextStyle(color: Colors.white);
    return Padding(
      padding: const EdgeInsets.all(20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text('تسجيل حادث أمني',
              style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w800)),
          const SizedBox(height: 16),
          DropdownButtonFormField<String>(
            value: _type,
            dropdownColor: const Color(0xFF1E3A5F),
            style: white,
            decoration: const InputDecoration(labelText: 'النوع', labelStyle: white),
            items: [
              for (final e in _SecurityIncidentsScreenState.types.entries)
                DropdownMenuItem(value: e.key, child: Text(e.value, style: white)),
            ],
            onChanged: (v) => setState(() => _type = v!),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            value: _sev,
            dropdownColor: const Color(0xFF1E3A5F),
            style: white,
            decoration: const InputDecoration(labelText: 'الخطورة', labelStyle: white),
            items: [
              for (final e in _SecurityIncidentsScreenState.severities.entries)
                DropdownMenuItem(value: e.key, child: Text(e.value, style: white)),
            ],
            onChanged: (v) => setState(() => _sev = v!),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _desc,
            style: white,
            maxLines: 3,
            decoration: const InputDecoration(labelText: 'الوصف', labelStyle: white),
          ),
          const SizedBox(height: 20),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE5484D)),
            onPressed: _busy ? null : _save,
            child: _busy
                ? const SizedBox(height: 22, width: 22, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : const Text('إرسال البلاغ'),
          ),
        ],
      ),
    );
  }
}
