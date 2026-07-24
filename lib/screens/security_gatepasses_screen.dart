import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'scan_screen.dart';

/// «تصاريح البوابة» — visitor gate passes by state, with scan-to-find, approve/
/// reject, and check-in / check-out at the gate.
class SecurityGatePassesScreen extends StatefulWidget {
  const SecurityGatePassesScreen({super.key});
  @override
  State<SecurityGatePassesScreen> createState() => _SecurityGatePassesScreenState();
}

class _SecurityGatePassesScreenState extends State<SecurityGatePassesScreen> {
  static const _navy = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);

  Map<String, dynamic>? _data;
  bool _loading = true;
  String _state = '';

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final d = await context.read<AuthProvider>().api.securityGatepasses(state: _state);
      if (mounted) setState(() { _data = d; _loading = false; });
    } catch (_) { if (mounted) setState(() => _loading = false); }
  }

  Future<void> _scan() async {
    final code = await Navigator.push<String>(context, MaterialPageRoute(builder: (_) => const ScanScreen(returnCode: true)));
    if (code == null || !mounted) return;
    try {
      final g = await context.read<AuthProvider>().api.securityGatepassScan(code);
      if (mounted) _open(g['id'] as int);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('$e'.replaceFirst('Exception: ', '')), backgroundColor: const Color(0xFFE11D48)));
    }
  }

  void _open(int id) => showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => _GpSheet(id: id)).then((_) => _load());

  Color _stColor(String s) => switch (s) {
        'approved' || 'valid' => const Color(0xFF37C98A), 'pending' => const Color(0xFFF7A23B),
        'rejected' || 'cancelled' => const Color(0xFFE5484D), 'expired' => _muted, _ => _muted,
      };

  @override
  Widget build(BuildContext context) {
    final items = ((_data?['items'] as List?) ?? const []).cast<Map>();
    final st = (_data?['stats'] as Map?) ?? const {};
    return Scaffold(
      backgroundColor: _navy,
      appBar: AppBar(title: Text(tr('تصاريح البوابة', 'Gate passes')), backgroundColor: _navy),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: const Color(0xFF16A34A), foregroundColor: Colors.white,
        onPressed: _scan, icon: const Icon(Icons.qr_code_scanner_rounded),
        label: Text(tr('مسح تصريح', 'Scan pass'), style: const TextStyle(fontWeight: FontWeight.w900))),
      body: Column(children: [
        Padding(padding: const EdgeInsets.fromLTRB(12, 8, 12, 4), child: Row(children: [
          _stat('${st['total'] ?? 0}', tr('الكل', 'Total'), _muted),
          _stat('${st['pending'] ?? 0}', tr('معلّقة', 'Pending'), const Color(0xFFF7A23B)),
          _stat('${st['approved'] ?? 0}', tr('معتمدة', 'Approved'), const Color(0xFF37C98A)),
          _stat('${st['onsite'] ?? 0}', tr('بالداخل', 'On-site'), const Color(0xFF4AA8FF)),
        ])),
        SizedBox(height: 40, child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 12), children: [
          for (final s in [('', tr('الكل', 'All')), ('pending', tr('معلّقة', 'Pending')), ('approved', tr('معتمدة', 'Approved')), ('valid', tr('سارية', 'Valid')), ('onsite', tr('بالداخل', 'On-site')), ('expired', tr('منتهية', 'Expired'))])
            Padding(padding: const EdgeInsetsDirectional.only(end: 6), child: ChoiceChip(
              label: Text(s.$2, style: const TextStyle(fontSize: 11.5)),
              selected: _state == s.$1, backgroundColor: _card, selectedColor: const Color(0xFF16A34A),
              labelStyle: TextStyle(color: _state == s.$1 ? Colors.white : _muted, fontWeight: FontWeight.w700),
              onSelected: (_) { setState(() => _state = s.$1); _load(); })),
        ])),
        Expanded(child: _loading
            ? const Center(child: CircularProgressIndicator())
            : items.isEmpty
                ? Center(child: Text(tr('لا تصاريح.', 'No gate passes.'), style: const TextStyle(color: _muted)))
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

  Widget _card2(Map g) {
    final st = '${g['state']}';
    final onsite = g['checked_in'] == true && g['checked_out'] != true;
    return Card(color: _card, child: InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: () => _open(g['id'] as int),
      child: Padding(padding: const EdgeInsets.all(12), child: Row(children: [
        Container(width: 42, height: 42, alignment: Alignment.center,
            decoration: BoxDecoration(color: _stColor(st).withValues(alpha: 0.16), borderRadius: BorderRadius.circular(11)),
            child: Icon(onsite ? Icons.login_rounded : Icons.badge_rounded, color: _stColor(st), size: 20)),
        const SizedBox(width: 11),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${g['visitor'] ?? g['name'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13.5)),
          Text([g['name'], g['type'], if (g['plate'] != null) '🚗 ${g['plate']}'].where((x) => x != null).join(' · '),
              maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 11)),
          if (g['valid_until'] != null) Text('⏳ ${g['valid_until']}', style: const TextStyle(color: _muted, fontSize: 10.5)),
        ])),
        Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(color: _stColor(st).withValues(alpha: 0.16), borderRadius: BorderRadius.circular(20)),
              child: Text('${g['state_label'] ?? st}', style: TextStyle(color: _stColor(st), fontWeight: FontWeight.w800, fontSize: 9.5))),
          if (onsite) const Padding(padding: EdgeInsets.only(top: 3), child: Text('🟢 بالداخل', style: TextStyle(color: Color(0xFF4AA8FF), fontSize: 9.5, fontWeight: FontWeight.w700))),
        ]),
      ]))));
  }
}

class _GpSheet extends StatefulWidget {
  const _GpSheet({required this.id});
  final int id;
  @override
  State<_GpSheet> createState() => _GpSheetState();
}

class _GpSheetState extends State<_GpSheet> {
  static const _navy = Color(0xFF0F1B2E);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);

  Map<String, dynamic>? _g;
  bool _busy = false;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try {
      final g = await context.read<AuthProvider>().api.securityGatepassDetail(widget.id);
      if (mounted) setState(() => _g = g);
    } catch (_) {}
  }

  void _snack(String m, [Color? c]) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: c, behavior: SnackBarBehavior.floating));

  Future<void> _act(String key, {String? reason}) async {
    setState(() => _busy = true);
    try {
      final g = await context.read<AuthProvider>().api.securityGatepassAction(widget.id, key, reason: reason);
      if (mounted) setState(() { _g = g; _busy = false; });
      _snack(tr('تم', 'Done'), const Color(0xFF16A34A));
    } catch (e) { if (mounted) { setState(() => _busy = false); _snack('$e'.replaceFirst('Exception: ', ''), const Color(0xFFE11D48)); } }
  }

  Future<void> _reject() async {
    final ctrl = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      title: Text(tr('رفض التصريح', 'Reject pass')),
      content: TextField(controller: ctrl, autofocus: true, decoration: InputDecoration(labelText: tr('السبب', 'Reason'), border: const OutlineInputBorder())),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE5484D)), onPressed: () => Navigator.pop(c, true), child: Text(tr('رفض', 'Reject'))),
      ]));
    if (ok == true) await _act('reject', reason: ctrl.text.trim());
  }

  @override
  Widget build(BuildContext context) {
    final g = _g;
    final st = '${g?['state'] ?? ''}';
    final onsite = g?['checked_in'] == true && g?['checked_out'] != true;
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.78, maxChildSize: 0.96, minChildSize: 0.4,
      builder: (_, sc) => Container(
        decoration: const BoxDecoration(color: _navy, borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        clipBehavior: Clip.antiAlias,
        child: g == null ? const SizedBox(height: 260, child: Center(child: CircularProgressIndicator()))
            : Stack(children: [
                ListView(controller: sc, padding: const EdgeInsets.all(18), children: [
                  Center(child: Container(width: 42, height: 4, margin: const EdgeInsets.only(bottom: 14),
                      decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(3)))),
                  Row(children: [
                    const Icon(Icons.badge_rounded, color: Color(0xFF16A34A), size: 24),
                    const SizedBox(width: 10),
                    Expanded(child: Text('${g['visitor'] ?? ''}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16))),
                    Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(color: Colors.white12, borderRadius: BorderRadius.circular(20)),
                        child: Text('${g['state_label'] ?? st}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 11))),
                  ]),
                  const SizedBox(height: 14),
                  Wrap(spacing: 8, runSpacing: 8, children: [
                    if (st == 'draft') _b(tr('تقديم', 'Submit'), const Color(0xFFF7A23B), () => _act('submit')),
                    if (st == 'pending') ...[
                      _b(tr('اعتماد', 'Approve'), const Color(0xFF16A34A), () => _act('approve')),
                      _b(tr('رفض', 'Reject'), const Color(0xFFE5484D), _reject),
                    ],
                    if ((st == 'approved' || st == 'valid') && g['checked_in'] != true)
                      _b(tr('دخول الزائر', 'Check in'), const Color(0xFF4AA8FF), () => _act('checkin')),
                    if (onsite) _b(tr('خروج الزائر', 'Check out'), const Color(0xFF7C3AED), () => _act('checkout')),
                    if (st != 'cancelled' && st != 'rejected') _b(tr('إلغاء', 'Cancel'), _muted, () => _act('cancel'), outline: true),
                  ]),
                  const SizedBox(height: 16),
                  _info(tr('بيانات الزائر', 'Visitor'), [
                    (tr('الزائر', 'Visitor'), g['visitor']),
                    (tr('الهاتف', 'Phone'), g['visitor_phone']),
                    (tr('الشركة', 'Company'), g['visitor_company']),
                    (tr('اللوحة', 'Plate'), g['plate']),
                  ], phone: '${g['visitor_phone'] ?? ''}'),
                  const SizedBox(height: 12),
                  _info(tr('التصريح', 'Pass'), [
                    (tr('الرقم', 'Number'), g['name']),
                    (tr('النوع', 'Type'), g['type']),
                    (tr('الغرض', 'Purpose'), g['purpose']),
                    (tr('من', 'From'), g['valid_from']),
                    (tr('حتى', 'Until'), g['valid_until']),
                    (tr('الموقع', 'Premise'), g['premise']),
                    (tr('المضيف', 'Host'), g['host']),
                    (tr('مرافقة مطلوبة', 'Escort'), g['require_escort'] == true ? (g['escort'] ?? tr('نعم', 'Yes')) : null),
                    (tr('دخول', 'Checked in'), g['check_in_time']),
                    (tr('خروج', 'Checked out'), g['check_out_time']),
                    (tr('اعتمده', 'Approved by'), g['approved_by']),
                    (tr('سبب الرفض', 'Rejection reason'), g['rejection_reason']),
                  ]),
                  const SizedBox(height: 20),
                ]),
                if (_busy) const Positioned.fill(child: ColoredBox(color: Color(0x66000000), child: Center(child: CircularProgressIndicator()))),
              ]),
      ),
    );
  }

  Widget _b(String label, Color c, VoidCallback onTap, {bool outline = false}) => outline
      ? OutlinedButton(onPressed: _busy ? null : onTap, style: OutlinedButton.styleFrom(foregroundColor: c, side: BorderSide(color: c)),
          child: Text(label, style: const TextStyle(fontWeight: FontWeight.w800)))
      : FilledButton(onPressed: _busy ? null : onTap, style: FilledButton.styleFrom(backgroundColor: c),
          child: Text(label, style: const TextStyle(fontWeight: FontWeight.w800)));

  Widget _info(String title, List<(String, dynamic)> rows, {String phone = ''}) {
    final present = rows.where((r) => r.$2 != null && '${r.$2}'.trim().isNotEmpty).toList();
    if (present.isEmpty) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 12),
      decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(14)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 12.5))),
          if (phone.isNotEmpty) IconButton(padding: EdgeInsets.zero, constraints: const BoxConstraints(),
              icon: const Icon(Icons.call_rounded, color: Color(0xFF37C98A), size: 18), onPressed: () => launchUrl(Uri.parse('tel:$phone'))),
        ]),
        const SizedBox(height: 8),
        for (final r in present) Padding(padding: const EdgeInsets.symmetric(vertical: 4), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 110, child: Text(r.$1, style: const TextStyle(color: _muted, fontSize: 12, fontWeight: FontWeight.w700))),
          Expanded(child: Text('${r.$2}', style: const TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w600))),
        ])),
      ]),
    );
  }
}
