import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Reusable read-only list for a security resource (patrols / keys / gatepasses).
/// Each kind renders with its own title, subtitle and status chip mapping.
class SecurityListScreen extends StatefulWidget {
  const SecurityListScreen({super.key, required this.kind, required this.title});
  final String kind; // patrols | keys | gatepasses
  final String title;

  @override
  State<SecurityListScreen> createState() => _SecurityListScreenState();
}

class _SecurityListScreenState extends State<SecurityListScreen> {
  late Future<List<dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _future = context.read<AuthProvider>().api.securityList(widget.kind);
  }

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
            if (snap.hasError) return _msg('خطأ: ${snap.error}');
            final items = snap.data ?? const [];
            if (items.isEmpty) return _msg(tr('لا عناصر.', 'No items.'));
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

  static const _stateLabels = {
    // patrol
    'scheduled': 'مجدولة', 'in_progress': 'جارية', 'completed': 'مكتملة', 'cancelled': 'ملغاة',
    // key
    'available': 'بالخزانة', 'checked_out': 'مُسلَّم', 'maintenance': 'صيانة', 'lost': 'مفقود',
    // gate pass
    'draft': 'مسودة', 'pending': 'بانتظار الموافقة', 'approved': 'معتمد',
    'valid': 'ساري', 'expired': 'منتهٍ',
  };

  Color _stateColor(String s) => switch (s) {
        'in_progress' || 'valid' || 'available' || 'completed' || 'approved' => const Color(0xFF37C98A),
        'checked_out' || 'pending' => const Color(0xFFF7A23B),
        'lost' || 'expired' || 'cancelled' => const Color(0xFFE5484D),
        _ => const Color(0xFF6B7A90),
      };

  ({String title, String sub, IconData icon}) _fields(Map m) {
    switch (widget.kind) {
      case 'patrols':
        return (
          title: '${m['name']} — ${m['route'] ?? '—'}',
          sub: 'الحارس: ${m['guard'] ?? '—'} · ${m['premise'] ?? '—'} · نقاط: ${m['points']}',
          icon: Icons.route,
        );
      case 'keys':
        return (
          title: '${m['name']}',
          sub: '${m['premise'] ?? '—'}${m['holder'] != null ? ' · بحوزة: ${m['holder']}' : ''}',
          icon: Icons.vpn_key,
        );
      case 'gatepasses':
        return (
          title: '${m['name']} — ${m['visitor'] ?? ''}',
          sub: '${m['premise'] ?? '—'}${m['purpose'] != null ? ' · ${m['purpose']}' : ''}',
          icon: Icons.badge,
        );
      default:
        return (title: '${m['name'] ?? ''}', sub: '', icon: Icons.circle);
    }
  }

  Widget _card(Map m) {
    final f = _fields(m);
    final state = (m['state'] as String?) ?? '';
    return Card(
      color: const Color(0xFF152238),
      child: ListTile(
        onTap: () => _openDetail(m, f.icon),
        leading: CircleAvatar(
          backgroundColor: const Color(0xFF1E3A5F),
          child: Icon(f.icon, color: Colors.white, size: 20),
        ),
        title: Text(f.title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700)),
        subtitle: Text(f.sub, style: const TextStyle(color: Color(0xFF9CB2CD))),
        trailing: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(color: _stateColor(state), borderRadius: BorderRadius.circular(20)),
            child: Text(_stateLabels[state] ?? state,
                style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700)),
          ),
          const SizedBox(height: 4),
          const Icon(Icons.chevron_left_rounded, color: Color(0xFF6B7A90), size: 18),
        ]),
        isThreeLine: true,
      ),
    );
  }

  /// A localized label for a raw record key — so the detail sheet reads well.
  static const _keyLabels = {
    'name': 'المرجع', 'route': 'المسار', 'guard': 'الحارس', 'premise': 'الموقع',
    'points': 'عدد النقاط', 'holder': 'بحوزة', 'visitor': 'الزائر', 'purpose': 'الغرض',
    'date': 'التاريخ', 'start': 'البداية', 'end': 'النهاية', 'valid_from': 'ساري من',
    'valid_to': 'ساري حتى', 'company': 'الجهة', 'vehicle': 'المركبة', 'id_number': 'رقم الهوية',
    'phone': 'الهاتف', 'note': 'ملاحظة', 'notes': 'ملاحظات', 'checked_at': 'وقت التسليم',
    'returned_at': 'وقت الإرجاع', 'points_done': 'نقاط مُنجزة',
  };

  void _openDetail(Map m, IconData icon) {
    final state = (m['state'] as String?) ?? '';
    // meaningful key/values, skipping ids and empties
    final entries = m.entries.where((e) =>
        e.key != 'id' && e.key != 'state' && e.value != null && '${e.value}'.trim().isNotEmpty).toList();
    showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.6, minChildSize: 0.4, maxChildSize: 0.92,
        builder: (_, sc) => Container(
          decoration: const BoxDecoration(color: Color(0xFF0F1B2E), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
          clipBehavior: Clip.antiAlias,
          child: Column(children: [
            Container(
              padding: const EdgeInsets.fromLTRB(20, 14, 12, 16),
              decoration: const BoxDecoration(gradient: LinearGradient(colors: [Color(0xFF1E3A5F), Color(0xFF0B1220)], begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Column(children: [
                Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12), decoration: BoxDecoration(color: Colors.white38, borderRadius: BorderRadius.circular(3)))),
                Row(children: [
                  CircleAvatar(backgroundColor: const Color(0xFF1E3A5F), child: Icon(icon, color: Colors.white, size: 20)),
                  const SizedBox(width: 12),
                  Expanded(child: Text('${m['name'] ?? widget.title}', style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900))),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(color: _stateColor(state), borderRadius: BorderRadius.circular(20)),
                    child: Text(_stateLabels[state] ?? state, style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w800)),
                  ),
                ]),
              ]),
            ),
            Expanded(child: ListView(controller: sc, padding: const EdgeInsets.all(16), children: [
              for (final e in entries) Padding(
                padding: const EdgeInsets.symmetric(vertical: 7),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  SizedBox(width: 120, child: Text(_keyLabels[e.key] ?? e.key,
                      style: const TextStyle(color: Color(0xFF9CB2CD), fontSize: 12.5, fontWeight: FontWeight.w700))),
                  Expanded(child: Text('${e.value}', style: const TextStyle(color: Colors.white, fontSize: 13.5, fontWeight: FontWeight.w700))),
                ]),
              ),
            ])),
          ]),
        ),
      ),
    );
  }
}
