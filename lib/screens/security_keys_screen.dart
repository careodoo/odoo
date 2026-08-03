import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'scan_screen.dart';

/// «عهدة المفاتيح» — a guard scans a key (QR/NFC/barcode) or browses the board
/// by state, checks it out to a recipient, returns it to a hub, or marks it
/// lost. Each key keeps a full in/out log.
class SecurityKeysScreen extends StatefulWidget {
  const SecurityKeysScreen({super.key});
  @override
  State<SecurityKeysScreen> createState() => _SecurityKeysScreenState();
}

class _SecurityKeysScreenState extends State<SecurityKeysScreen> {
  static const _navy = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);
  static const _amber = Color(0xFFF59E0B);

  Map<String, dynamic>? _data;
  bool _loading = true;
  String _tab = '', _q = '';
  Timer? _debounce;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _debounce?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final d = await context.read<AuthProvider>().api.securityKeysBoard(tab: _tab, q: _q);
      if (mounted) setState(() { _data = d; _loading = false; });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _onSearch(String v) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 400), () { _q = v.trim(); _load(); });
  }

  Future<void> _scan() async {
    final code = await Navigator.push<String>(context,
        MaterialPageRoute(builder: (_) => const ScanScreen(returnCode: true)));
    if (code == null || !mounted) return;
    try {
      final key = await context.read<AuthProvider>().api.securityKeyScan(code);
      if (mounted) _openKey(key['id'] as int);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('$e'.replaceFirst('Exception: ', '')), backgroundColor: const Color(0xFFE11D48)));
    }
  }

  void _openKey(int id) {
    showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
        builder: (_) => _KeySheet(id: id)).then((_) => _load());
  }

  @override
  Widget build(BuildContext context) {
    final items = ((_data?['items'] as List?) ?? const []).cast<Map>();
    final st = (_data?['stats'] as Map?) ?? const {};
    return Scaffold(
      backgroundColor: _navy,
      appBar: AppBar(title: Text(tr('عهدة المفاتيح', 'Key custody')), backgroundColor: _navy),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: _amber, foregroundColor: Colors.black,
        onPressed: _scan, icon: const Icon(Icons.qr_code_scanner_rounded),
        label: Text(tr('مسح مفتاح', 'Scan key'), style: const TextStyle(fontWeight: FontWeight.w900))),
      body: Column(children: [
        Padding(padding: const EdgeInsets.fromLTRB(12, 8, 12, 4), child: Row(children: [
          _stat('${st['total'] ?? 0}', tr('الكل', 'Total'), _muted, ''),
          _stat('${st['available'] ?? 0}', tr('متاحة', 'Available'), const Color(0xFF37C98A), 'available'),
          _stat('${st['checked_out'] ?? 0}', tr('مصروفة', 'Out'), const Color(0xFF4AA8FF), 'checked_out'),
          _stat('${st['lost'] ?? 0}', tr('مفقودة', 'Lost'), const Color(0xFFE5484D), 'lost'),
        ])),
        Padding(padding: const EdgeInsets.fromLTRB(12, 4, 12, 8), child: TextField(
          style: const TextStyle(color: Colors.white), onChanged: _onSearch,
          decoration: InputDecoration(
            hintText: tr('بحث بالاسم/الرقم/الحامل…', 'Search key / holder…'), hintStyle: const TextStyle(color: _muted),
            prefixIcon: const Icon(Icons.search_rounded, color: _muted),
            filled: true, fillColor: _card, isDense: true,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)))),
        Expanded(child: _loading
            ? const Center(child: CircularProgressIndicator())
            : items.isEmpty
                ? Center(child: Text(tr('لا مفاتيح.', 'No keys.'), style: const TextStyle(color: _muted)))
                : RefreshIndicator(onRefresh: _load, child: ListView.builder(
                    padding: const EdgeInsets.all(12), itemCount: items.length,
                    itemBuilder: (_, i) => _keyCard(items[i])))),
      ]),
    );
  }

  Widget _stat(String v, String l, Color c, String tab) => Expanded(child: GestureDetector(
        onTap: () { setState(() => _tab = _tab == tab ? '' : tab); _load(); },
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 3),
          padding: const EdgeInsets.symmetric(vertical: 9),
          decoration: BoxDecoration(color: _tab == tab && tab.isNotEmpty ? c.withValues(alpha: 0.2) : _card,
              borderRadius: BorderRadius.circular(12),
              border: _tab == tab && tab.isNotEmpty ? Border.all(color: c) : null),
          child: Column(children: [
            Text(v, style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 17)),
            Text(l, style: const TextStyle(color: _muted, fontSize: 9.5, fontWeight: FontWeight.w600)),
          ]))));

  Color _stColor(String s) => switch (s) {
        'available' => const Color(0xFF37C98A),
        'checked_out' => const Color(0xFF4AA8FF),
        'lost' => const Color(0xFFE5484D),
        _ => _amber,
      };

  Widget _keyCard(Map k) {
    final c = _stColor('${k['state']}');
    return Card(color: _card, child: InkWell(
      borderRadius: BorderRadius.circular(12),
      onTap: () => _openKey(k['id'] as int),
      child: Padding(padding: const EdgeInsets.all(12), child: Row(children: [
        Container(width: 42, height: 42, alignment: Alignment.center,
            decoration: BoxDecoration(color: c.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(11)),
            child: Icon(Icons.vpn_key_rounded, color: c, size: 20)),
        const SizedBox(width: 11),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${k['name'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13.5)),
          Text([if (k['key_number'] != null) '#${k['key_number']}', if (k['hub'] != null) k['hub'], if (k['unit'] != null) k['unit']].where((x) => x != null).join(' · '),
              maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 11)),
          if (k['holder'] != null) Padding(padding: const EdgeInsets.only(top: 2),
              child: Text('🧑 ${k['holder']}${k['expected_return'] != null ? ' · ⏰ ${k['expected_return']}' : ''}',
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Color(0xFF4AA8FF), fontSize: 10.5))),
        ])),
        Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(color: c.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(20)),
              child: Text('${k['state_label'] ?? k['state']}', style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 9.5))),
          if ((k['overdue'] as num?) != null && (k['overdue'] as num) > 0) Padding(padding: const EdgeInsets.only(top: 3),
              child: Text('${tr('متأخر', 'overdue')} ${k['overdue']}${tr('ي', 'd')}', style: const TextStyle(color: Color(0xFFE5484D), fontSize: 9.5, fontWeight: FontWeight.w700))),
          Row(mainAxisSize: MainAxisSize.min, children: [
            if (k['has_qr'] == true) const Text('▪', style: TextStyle(color: _muted)),
            if (k['has_nfc'] == true) const Padding(padding: EdgeInsets.only(left: 2), child: Icon(Icons.nfc_rounded, size: 12, color: _muted)),
          ]),
        ]),
      ]))));
  }
}

/// Key detail + check-out / check-in / lost, with the full operation log.
class _KeySheet extends StatefulWidget {
  const _KeySheet({required this.id});
  final int id;
  @override
  State<_KeySheet> createState() => _KeySheetState();
}

class _KeySheetState extends State<_KeySheet> {
  static const _navy = Color(0xFF0F1B2E);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);

  Map<String, dynamic>? _k;
  bool _busy = false;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try {
      final k = await context.read<AuthProvider>().api.securityKeyDetail(widget.id);
      if (mounted) setState(() => _k = k);
    } catch (_) {}
  }

  void _snack(String m, [Color? c]) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: c, behavior: SnackBarBehavior.floating));

  Future<void> _act(String act, Map<String, dynamic> body) async {
    setState(() => _busy = true);
    try {
      final k = await context.read<AuthProvider>().api.securityKeyAction(widget.id, act, body);
      if (mounted) setState(() { _k = k; _busy = false; });
      _snack(tr('تم', 'Done'), const Color(0xFF16A34A));
    } catch (e) {
      if (mounted) { setState(() => _busy = false); _snack('$e'.replaceFirst('Exception: ', ''), const Color(0xFFE11D48)); }
    }
  }

  Future<void> _checkout() async {
    final meta = await context.read<AuthProvider>().api.securityKeyMeta();
    final guards = ((meta['guards'] as List?) ?? const []).cast<Map>();
    Map? recipient = meta['me'] as Map?;
    final reason = TextEditingController();
    int hours = 8;
    if (!mounted) return;
    final ok = await showModalBottomSheet<bool>(context: context, isScrollControlled: true, backgroundColor: _navy,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (c) => StatefulBuilder(builder: (c, setD) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(c).viewInsets.bottom, left: 16, right: 16, top: 16),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text(tr('صرف المفتاح', 'Check out key'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16)),
          const SizedBox(height: 14),
          InkWell(
            onTap: () async {
              final g = await showModalBottomSheet<Map>(context: c, backgroundColor: _card, isScrollControlled: true,
                builder: (_) => ListView(shrinkWrap: true, children: [
                  for (final gg in guards) ListTile(
                    title: Text('${gg['l']}', style: const TextStyle(color: Colors.white)),
                    subtitle: gg['badge'] != '' ? Text('#${gg['badge']}', style: const TextStyle(color: _muted)) : null,
                    onTap: () => Navigator.pop(_, gg))]));
              if (g != null) setD(() => recipient = g);
            },
            child: InputDecorator(
              decoration: InputDecoration(labelText: tr('المستلم', 'Recipient'), labelStyle: const TextStyle(color: _muted),
                  filled: true, fillColor: _card, border: const OutlineInputBorder(borderSide: BorderSide.none)),
              child: Text(recipient == null ? tr('اختر…', 'Select…') : '${recipient!['l']}', style: const TextStyle(color: Colors.white)))),
          const SizedBox(height: 12),
          TextField(controller: reason, style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(labelText: tr('السبب/الغرض', 'Purpose'), labelStyle: const TextStyle(color: _muted),
                  filled: true, fillColor: _card, border: const OutlineInputBorder(borderSide: BorderSide.none))),
          const SizedBox(height: 12),
          Row(children: [
            const Text('⏱️', style: TextStyle(fontSize: 16)), const SizedBox(width: 8),
            Text(tr('مدة الإرجاع', 'Return in'), style: const TextStyle(color: _muted)),
            const Spacer(),
            for (final h in [4, 8, 12, 24]) Padding(padding: const EdgeInsets.only(left: 6),
                child: ChoiceChip(label: Text(tr('${h}س', '${h}h')), selected: hours == h,
                    onSelected: (_) => setD(() => hours = h))),
          ]),
          const SizedBox(height: 16),
          FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFF4AA8FF), minimumSize: const Size(0, 48)),
              onPressed: () => Navigator.pop(c, true), child: Text(tr('صرف المفتاح', 'Check out'))),
          const SizedBox(height: 12),
        ]))));
    if (ok != true || recipient == null) return;
    await _act('checkout', {'employee_id': recipient!['v'], 'reason': reason.text.trim(), 'expected_hours': hours});
  }

  Future<void> _checkin() async {
    final meta = await context.read<AuthProvider>().api.securityKeyMeta();
    final hubs = ((meta['hubs'] as List?) ?? const []).cast<Map>();
    Map? hub = hubs.isNotEmpty ? hubs.firstWhere((h) => h['v'] == _k?['hub_id'], orElse: () => hubs.first) : null;
    final notes = TextEditingController();
    if (!mounted) return;
    final ok = await showModalBottomSheet<bool>(context: context, isScrollControlled: true, backgroundColor: _navy,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (c) => StatefulBuilder(builder: (c, setD) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(c).viewInsets.bottom, left: 16, right: 16, top: 16),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text(tr('إرجاع المفتاح', 'Return key'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16)),
          const SizedBox(height: 14),
          if (hubs.isNotEmpty) InkWell(
            onTap: () async {
              final h = await showModalBottomSheet<Map>(context: c, backgroundColor: _card,
                builder: (_) => ListView(shrinkWrap: true, children: [
                  for (final hh in hubs) ListTile(title: Text('${hh['l']}', style: const TextStyle(color: Colors.white)),
                      onTap: () => Navigator.pop(_, hh))]));
              if (h != null) setD(() => hub = h);
            },
            child: InputDecorator(
              decoration: InputDecoration(labelText: tr('إرجاع إلى الخزنة', 'Return to hub'), labelStyle: const TextStyle(color: _muted),
                  filled: true, fillColor: _card, border: const OutlineInputBorder(borderSide: BorderSide.none)),
              child: Text(hub == null ? tr('اختر…', 'Select…') : '${hub!['l']}', style: const TextStyle(color: Colors.white)))),
          const SizedBox(height: 12),
          TextField(controller: notes, style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(labelText: tr('ملاحظات', 'Notes'), labelStyle: const TextStyle(color: _muted),
                  filled: true, fillColor: _card, border: const OutlineInputBorder(borderSide: BorderSide.none))),
          const SizedBox(height: 16),
          FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFF37C98A), minimumSize: const Size(0, 48)),
              onPressed: () => Navigator.pop(c, true), child: Text(tr('إرجاع', 'Return'))),
          const SizedBox(height: 12),
        ]))));
    if (ok != true) return;
    await _act('checkin', {if (hub != null) 'hub_id': hub!['v'], 'notes': notes.text.trim()});
  }

  Future<void> _lost() async {
    final reason = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      title: Text(tr('الإبلاغ عن فقدان', 'Report lost')),
      content: TextField(controller: reason, autofocus: true, decoration: InputDecoration(labelText: tr('السبب', 'Reason'), border: const OutlineInputBorder())),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE5484D)),
            onPressed: () => Navigator.pop(c, true), child: Text(tr('فُقد', 'Lost'))),
      ]));
    if (ok != true) return;
    await _act('lost', {'reason': reason.text.trim()});
  }

  @override
  Widget build(BuildContext context) {
    final k = _k;
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.75, maxChildSize: 0.95, minChildSize: 0.4,
      builder: (_, sc) => Container(
        decoration: const BoxDecoration(color: _navy, borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        clipBehavior: Clip.antiAlias,
        child: k == null
            ? const SizedBox(height: 260, child: Center(child: CircularProgressIndicator()))
            : Stack(children: [
                ListView(controller: sc, padding: const EdgeInsets.all(18), children: [
                  Center(child: Container(width: 42, height: 4, margin: const EdgeInsets.only(bottom: 14),
                      decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(3)))),
                  Row(children: [
                    const Icon(Icons.vpn_key_rounded, color: Color(0xFFF59E0B), size: 26),
                    const SizedBox(width: 10),
                    Expanded(child: Text('${k['name'] ?? ''}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 17))),
                    Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(color: Colors.white12, borderRadius: BorderRadius.circular(20)),
                        child: Text('${k['state_label'] ?? k['state']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 11))),
                  ]),
                  const SizedBox(height: 14),
                  // action buttons by state
                  if (k['state'] == 'available')
                    _bigBtn(Icons.logout_rounded, tr('صرف المفتاح', 'Check out'), const Color(0xFF4AA8FF), _checkout),
                  if (k['state'] == 'checked_out') ...[
                    _bigBtn(Icons.login_rounded, tr('إرجاع المفتاح', 'Check in'), const Color(0xFF37C98A), _checkin),
                    const SizedBox(height: 8),
                  ],
                  if (k['state'] != 'lost')
                    _bigBtn(Icons.report_gmailerrorred_rounded, tr('الإبلاغ عن فقدان', 'Report lost'), const Color(0xFFE5484D), _lost, outline: true),
                  const SizedBox(height: 16),
                  _info(tr('بيانات المفتاح', 'Key details'), [
                    (tr('رقم المفتاح', 'Key number'), k['key_number']),
                    (tr('رقم الباب', 'Door number'), k['door_number']),
                    (tr('الخزنة', 'Hub'), k['hub']),
                    (tr('الوحدة', 'Unit'), k['unit']),
                    (tr('الموقع', 'Premise'), k['premise']),
                    (tr('الحامل الحالي', 'Current holder'), k['holder']),
                    (tr('وقت الصرف', 'Checked out'), k['checkout_time']),
                    (tr('الإرجاع المتوقع', 'Expected return'), k['expected_return']),
                  ]),
                  const SizedBox(height: 14),
                  Text(tr('سجل الدخول والخروج', 'In / out log'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13.5)),
                  const SizedBox(height: 8),
                  for (final l in ((k['log'] as List?) ?? const []).cast<Map>()) _logRow(l),
                  const SizedBox(height: 20),
                ]),
                if (_busy) const Positioned.fill(child: ColoredBox(color: Color(0x66000000), child: Center(child: CircularProgressIndicator()))),
              ]),
      ),
    );
  }

  Widget _bigBtn(IconData ic, String label, Color c, VoidCallback onTap, {bool outline = false}) => SizedBox(
        width: double.infinity, height: 48,
        child: outline
            ? OutlinedButton.icon(onPressed: _busy ? null : onTap, icon: Icon(ic, size: 18, color: c),
                style: OutlinedButton.styleFrom(foregroundColor: c, side: BorderSide(color: c)),
                label: Text(label, style: const TextStyle(fontWeight: FontWeight.w900)))
            : FilledButton.icon(onPressed: _busy ? null : onTap, icon: Icon(ic, size: 18),
                style: FilledButton.styleFrom(backgroundColor: c),
                label: Text(label, style: const TextStyle(fontWeight: FontWeight.w900))));

  Widget _info(String title, List<(String, dynamic)> rows) {
    final present = rows.where((r) => r.$2 != null && '${r.$2}'.trim().isNotEmpty).toList();
    if (present.isEmpty) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 10, 14, 12),
      decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(14)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 12.5)),
        const SizedBox(height: 8),
        for (final r in present) Padding(padding: const EdgeInsets.symmetric(vertical: 4), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 120, child: Text(r.$1, style: const TextStyle(color: _muted, fontSize: 12, fontWeight: FontWeight.w700))),
          Expanded(child: Text('${r.$2}', style: const TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w600))),
        ])),
      ]),
    );
  }

  Widget _logRow(Map l) {
    final op = '${l['operation']}';
    final c = op == 'check_out' ? const Color(0xFF4AA8FF) : op == 'check_in' ? const Color(0xFF37C98A) : const Color(0xFFE5484D);
    final ic = op == 'check_out' ? Icons.logout_rounded : op == 'check_in' ? Icons.login_rounded : Icons.error_outline_rounded;
    return Padding(padding: const EdgeInsets.symmetric(vertical: 5), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Icon(ic, size: 16, color: c), const SizedBox(width: 10),
      Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Text('${l['operation_label'] ?? op}', style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 12.5)),
          const Spacer(),
          Text('${l['at'] ?? ''}', style: const TextStyle(color: _muted, fontSize: 10.5)),
        ]),
        if (l['by'] != null) Text('👤 ${l['by']}', style: const TextStyle(color: _muted, fontSize: 11)),
        if (l['reason'] != null) Text('${l['reason']}', style: const TextStyle(color: _muted, fontSize: 11)),
      ])),
    ]));
  }
}
