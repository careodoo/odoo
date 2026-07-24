import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'scan_screen.dart';

/// دوريات الحارس: قائمة الدوريات المجدولة/الجارية، وفتح الدورية لعرض نقاط
/// التفتيش ومسحها (QR/NFC) لإثبات الحضور، مع بدء/إنهاء الدورية ونسبة الإكمال.
class SecurityPatrolsScreen extends StatefulWidget {
  const SecurityPatrolsScreen({super.key});
  @override
  State<SecurityPatrolsScreen> createState() => _SecurityPatrolsScreenState();
}

class _SecurityPatrolsScreenState extends State<SecurityPatrolsScreen> {
  static const _navy = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);

  Map<String, dynamic>? _data;
  bool _loading = true;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final d = await context.read<AuthProvider>().api.securityMyPatrols();
      if (mounted) setState(() { _data = d; _loading = false; });
    } catch (_) { if (mounted) setState(() => _loading = false); }
  }

  Color _st(String s) => switch (s) {
        'in_progress' => const Color(0xFF4AA8FF), 'completed' => const Color(0xFF37C98A),
        'cancelled' => const Color(0xFFE5484D), _ => const Color(0xFFF7A23B),
      };

  @override
  Widget build(BuildContext context) {
    final items = ((_data?['items'] as List?) ?? const []).cast<Map>();
    final st = (_data?['stats'] as Map?) ?? const {};
    return Scaffold(
      backgroundColor: _navy,
      appBar: AppBar(title: Text(tr('دورياتي', 'My patrols')), backgroundColor: _navy),
      body: Column(children: [
        Padding(padding: const EdgeInsets.fromLTRB(12, 8, 12, 6), child: Row(children: [
          _stat('${st['scheduled'] ?? 0}', tr('مجدولة', 'Scheduled'), const Color(0xFFF7A23B)),
          _stat('${st['in_progress'] ?? 0}', tr('جارية', 'Active'), const Color(0xFF4AA8FF)),
          _stat('${st['completed'] ?? 0}', tr('منجزة', 'Done'), const Color(0xFF37C98A)),
        ])),
        Expanded(child: _loading
            ? const Center(child: CircularProgressIndicator())
            : items.isEmpty
                ? Center(child: Text(tr('لا دوريات مسندة إليك.', 'No patrols assigned to you.'), style: const TextStyle(color: _muted)))
                : RefreshIndicator(onRefresh: _load, child: ListView.builder(
                    padding: const EdgeInsets.all(12), itemCount: items.length,
                    itemBuilder: (_, i) => _card2(items[i])))),
      ]),
    );
  }

  Widget _stat(String v, String l, Color c) => Expanded(child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 3), padding: const EdgeInsets.symmetric(vertical: 9),
        decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(12)),
        child: Column(children: [
          Text(v, style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 17)),
          Text(l, style: const TextStyle(color: _muted, fontSize: 9.5, fontWeight: FontWeight.w600)),
        ])));

  Widget _card2(Map p) {
    final total = (p['points_total'] ?? 0) as int;
    final done = (p['points_done'] ?? 0) as int;
    final ratio = total > 0 ? done / total : 0.0;
    final c = _st('${p['state']}');
    return Card(color: _card, child: InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: () => showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
          builder: (_) => _PatrolSheet(id: p['id'] as int)).then((_) => _load()),
      child: Padding(padding: const EdgeInsets.all(12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(width: 40, height: 40, alignment: Alignment.center,
              decoration: BoxDecoration(color: c.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(11)),
              child: const Icon(Icons.route_rounded, color: Colors.white, size: 20)),
          const SizedBox(width: 11),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${p['name'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13.5)),
            Text([p['route'], p['premise'], p['scheduled_start']].where((x) => x != null).join(' · '),
                maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 11)),
          ])),
          Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(color: c.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(20)),
              child: Text('${p['state_label'] ?? p['state']}', style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 9.5))),
        ]),
        const SizedBox(height: 10),
        ClipRRect(borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(value: ratio, minHeight: 7, backgroundColor: _navy, valueColor: AlwaysStoppedAnimation(c))),
        const SizedBox(height: 5),
        Text('$done / $total ${tr('نقطة', 'points')}', style: const TextStyle(color: _muted, fontSize: 11)),
      ]))));
  }
}

class _PatrolSheet extends StatefulWidget {
  const _PatrolSheet({required this.id});
  final int id;
  @override
  State<_PatrolSheet> createState() => _PatrolSheetState();
}

class _PatrolSheetState extends State<_PatrolSheet> {
  static const _navy = Color(0xFF0F1B2E);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);

  Map<String, dynamic>? _p;
  bool _busy = false;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try {
      final p = await context.read<AuthProvider>().api.securityPatrolDetail(widget.id);
      if (mounted) setState(() => _p = p);
    } catch (_) {}
  }

  void _snack(String m, [Color? c]) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: c, behavior: SnackBarBehavior.floating));

  Future<void> _action(String path) async {
    setState(() => _busy = true);
    try {
      final p = await context.read<AuthProvider>().api.securityPatrolAction(widget.id, path);
      if (mounted) setState(() { _p = p; _busy = false; });
    } catch (e) { if (mounted) { setState(() => _busy = false); _snack('$e'.replaceFirst('Exception: ', ''), const Color(0xFFE11D48)); } }
  }

  Future<void> _scan() async {
    final code = await Navigator.push<String>(context, MaterialPageRoute(builder: (_) => const ScanScreen(returnCode: true)));
    if (code == null || !mounted) return;
    setState(() => _busy = true);
    try {
      final r = await context.read<AuthProvider>().api.securityPatrolScan(code, widget.id);
      if (mounted) setState(() { _p = r['patrol'] as Map<String, dynamic>? ?? _p; _busy = false; });
      _snack(tr('✅ سُجّل مسح النقطة', '✅ Checkpoint scanned'), const Color(0xFF16A34A));
    } catch (e) { if (mounted) { setState(() => _busy = false); _snack('$e'.replaceFirst('Exception: ', ''), const Color(0xFFE11D48)); } }
  }

  @override
  Widget build(BuildContext context) {
    final p = _p;
    final st = '${p?['state'] ?? ''}';
    final points = ((p?['points'] as List?) ?? const []).cast<Map>();
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.82, maxChildSize: 0.96, minChildSize: 0.4,
      builder: (_, sc) => Container(
        decoration: const BoxDecoration(color: _navy, borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        clipBehavior: Clip.antiAlias,
        child: p == null ? const SizedBox(height: 240, child: Center(child: CircularProgressIndicator()))
            : Stack(children: [
                ListView(controller: sc, padding: const EdgeInsets.all(18), children: [
                  Center(child: Container(width: 42, height: 4, margin: const EdgeInsets.only(bottom: 14),
                      decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(3)))),
                  Row(children: [
                    const Icon(Icons.route_rounded, color: Color(0xFF4AA8FF), size: 24),
                    const SizedBox(width: 10),
                    Expanded(child: Text('${p['name'] ?? ''}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16))),
                    Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(color: Colors.white12, borderRadius: BorderRadius.circular(20)),
                        child: Text('${p['state_label'] ?? st}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 11))),
                  ]),
                  const SizedBox(height: 6),
                  Text('${p['points_done'] ?? 0} / ${p['points_total'] ?? 0} ${tr('نقطة مُسحت', 'points scanned')}',
                      style: const TextStyle(color: _muted, fontSize: 12)),
                  const SizedBox(height: 14),
                  // أزرار التحكّم
                  Row(children: [
                    if (st == 'scheduled')
                      Expanded(child: FilledButton.icon(onPressed: _busy ? null : () => _action('start'),
                          icon: const Icon(Icons.play_arrow_rounded, size: 18), style: FilledButton.styleFrom(backgroundColor: const Color(0xFF4AA8FF)),
                          label: Text(tr('بدء الدورية', 'Start patrol')))),
                    if (st == 'in_progress') ...[
                      Expanded(child: FilledButton.icon(onPressed: _busy ? null : _scan,
                          icon: const Icon(Icons.qr_code_scanner_rounded, size: 18), style: FilledButton.styleFrom(backgroundColor: const Color(0xFFF7A23B), foregroundColor: Colors.black),
                          label: Text(tr('مسح نقطة', 'Scan point')))),
                      const SizedBox(width: 8),
                      Expanded(child: OutlinedButton.icon(onPressed: _busy ? null : () => _action('complete'),
                          icon: const Icon(Icons.check_circle_rounded, size: 18, color: Color(0xFF37C98A)),
                          style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFF37C98A), side: const BorderSide(color: Color(0xFF37C98A))),
                          label: Text(tr('إنهاء', 'Complete')))),
                    ],
                  ]),
                  const SizedBox(height: 16),
                  Text(tr('نقاط التفتيش', 'Checkpoints'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13.5)),
                  const SizedBox(height: 8),
                  for (final pt in points) Container(
                    margin: const EdgeInsets.only(bottom: 6),
                    padding: const EdgeInsets.all(11),
                    decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(11)),
                    child: Row(children: [
                      Icon(pt['scanned'] == true ? Icons.check_circle_rounded : Icons.radio_button_unchecked_rounded,
                          color: pt['scanned'] == true ? const Color(0xFF37C98A) : _muted, size: 20),
                      const SizedBox(width: 10),
                      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Text('${pt['name'] ?? ''}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 12.5)),
                        Text([pt['code'], pt['unit']].where((x) => x != null).join(' · '), style: const TextStyle(color: _muted, fontSize: 10.5)),
                      ])),
                      if (pt['has_nfc'] == true) const Icon(Icons.nfc_rounded, size: 14, color: _muted),
                    ]),
                  ),
                  const SizedBox(height: 20),
                ]),
                if (_busy) const Positioned.fill(child: ColoredBox(color: Color(0x66000000), child: Center(child: CircularProgressIndicator()))),
              ]),
      ),
    );
  }
}
