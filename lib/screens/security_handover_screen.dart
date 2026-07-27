import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// «تسليم الوردية» — عند تغيّر الوردية يسلّم الحارس المنصرف تقريراً للمستلِم:
/// الوضع العام + المهام المعلّقة + العهدة/المفاتيح + الملاحظات، ويُقرّ المستلِم.
class SecurityHandoverScreen extends StatefulWidget {
  const SecurityHandoverScreen({super.key});
  @override
  State<SecurityHandoverScreen> createState() => _SecurityHandoverScreenState();
}

class _SecurityHandoverScreenState extends State<SecurityHandoverScreen> {
  static const _navy = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);
  static const _green = Color(0xFF37C98A);
  static const _amber = Color(0xFFF7A23B);
  static const _blue = Color(0xFF4AA8FF);
  static const _red = Color(0xFFE5484D);

  Map<String, dynamic>? _d;
  bool _loading = true;

  @override
  void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    setState(() => _loading = true);
    try { final d = await context.read<AuthProvider>().api.securityHandovers();
      if (mounted) setState(() { _d = d; _loading = false; }); }
    catch (_) { if (mounted) setState(() => _loading = false); }
  }

  Future<void> _ack(int id) async {
    try { await context.read<AuthProvider>().api.securityHandoverAck(id);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(backgroundColor: _green, content: Text(tr('تم استلام الوردية', 'Handover acknowledged'))));
      await _load();
    } catch (e) { if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(backgroundColor: _red, content: Text('$e'))); }
  }

  @override
  Widget build(BuildContext context) {
    final items = ((_d?['items'] as List?) ?? const []).cast<Map>();
    final pending = (_d?['pending_ack'] ?? 0) as int;
    return Scaffold(
      backgroundColor: _navy,
      appBar: AppBar(title: Text(tr('تسليم الوردية', 'Shift handover')), backgroundColor: _navy,
          actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))]),
      floatingActionButton: FloatingActionButton.extended(backgroundColor: _blue,
          onPressed: _openCreate, icon: const Icon(Icons.swap_horiz_rounded), label: Text(tr('تسليم جديد', 'New handover'))),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Column(children: [
              if (pending > 0) Container(
                margin: const EdgeInsets.fromLTRB(12, 10, 12, 0), padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(color: _amber.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(12), border: Border.all(color: _amber.withValues(alpha: 0.4))),
                child: Row(children: [const Icon(Icons.notifications_active_rounded, color: _amber, size: 20), const SizedBox(width: 8),
                  Expanded(child: Text('$pending ${tr('تسليم بانتظار استلامك', 'handover(s) awaiting your acknowledgement')}', style: const TextStyle(color: _amber, fontWeight: FontWeight.w700, fontSize: 12.5)))])),
              Expanded(child: items.isEmpty
                  ? _empty()
                  : RefreshIndicator(onRefresh: _load, child: ListView(padding: const EdgeInsets.fromLTRB(12, 8, 12, 90), children: [for (final h in items) _hCard(h)]))),
            ]),
    );
  }

  Widget _empty() => ListView(children: [
        const SizedBox(height: 100), const Icon(Icons.swap_horizontal_circle_outlined, size: 74, color: Color(0xFF2A3B54)),
        const SizedBox(height: 12), Center(child: Text(tr('لا عمليات تسليم بعد.', 'No handovers yet.'), style: const TextStyle(color: _muted)))]);

  Widget _hCard(Map h) {
    final acked = h['state'] == 'acknowledged';
    final sent = h['mine_sent'] == true;
    final col = acked ? _green : _amber;
    return InkWell(onTap: () => _detail(h), child: Container(
      margin: const EdgeInsets.only(bottom: 10), padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(14), border: Border.all(color: const Color(0xFF20344E))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(width: 38, height: 38, decoration: BoxDecoration(color: (sent ? _blue : _amber).withValues(alpha: 0.15), borderRadius: BorderRadius.circular(11)),
              child: Icon(sent ? Icons.upload_rounded : Icons.download_rounded, color: sent ? _blue : _amber, size: 19)),
          const SizedBox(width: 11),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(sent ? '${tr('إلى', 'To')}: ${h['to'] ?? '—'}' : '${tr('من', 'From')}: ${h['from'] ?? '—'}',
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13.5)),
            const SizedBox(height: 2),
            Text([h['premise'], h['date']].where((x) => x != null).join(' · '), maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 11)),
          ])),
          Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3), decoration: BoxDecoration(color: col.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(8)),
              child: Text(acked ? tr('مُستلَم', 'Acked') : tr('مُرسَل', 'Sent'), style: TextStyle(color: col, fontSize: 10, fontWeight: FontWeight.w800))),
        ]),
        if (h['situation'] != null) Padding(padding: const EdgeInsets.only(top: 8),
            child: Text('${h['situation']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Color(0xFFCBD6E6), fontSize: 12))),
        if (!sent && !acked) Padding(padding: const EdgeInsets.only(top: 10), child: Align(alignment: Alignment.centerLeft,
            child: ElevatedButton.icon(onPressed: () => _ack(h['id'] as int), icon: const Icon(Icons.check_rounded, size: 16),
                label: Text(tr('استلام الوردية', 'Acknowledge'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12)),
                style: ElevatedButton.styleFrom(backgroundColor: _green, foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)))))),
      ]),
    ));
  }

  void _detail(Map h) => showModalBottomSheet(context: context, backgroundColor: _card, isScrollControlled: true,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => Padding(padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
        child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          const SizedBox(height: 10), Center(child: Container(width: 40, height: 4, decoration: BoxDecoration(color: const Color(0xFF34506F), borderRadius: BorderRadius.circular(3)))),
          const SizedBox(height: 14),
          Padding(padding: const EdgeInsets.symmetric(horizontal: 18), child: Text('${h['name'] ?? tr('تسليم وردية', 'Handover')}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16))),
          _row(tr('من', 'From'), h['from']), _row(tr('إلى', 'To'), h['to']), _row(tr('الموقع', 'Premise'), h['premise']), _row(tr('الوقت', 'Time'), h['date']),
          _blk(tr('الوضع العام', 'Situation'), h['situation']), _blk(tr('مهام معلّقة', 'Pending'), h['pending']),
          _row(tr('العهدة/المفاتيح', 'Keys/custody'), h['keys_note']), _blk(tr('ملاحظات وبلاغات', 'Notes'), h['incidents_note']),
          const SizedBox(height: 20),
        ]))));

  Widget _row(String l, dynamic v) { if (v == null || '$v'.isEmpty) return const SizedBox.shrink();
    return Padding(padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 5), child: Row(children: [
      Text(l, style: const TextStyle(color: _muted, fontSize: 12.5)), const Spacer(),
      Flexible(child: Text('$v', textAlign: TextAlign.end, style: const TextStyle(color: Colors.white, fontSize: 12.5, fontWeight: FontWeight.w600)))])); }
  Widget _blk(String l, dynamic v) { if (v == null || '$v'.isEmpty) return const SizedBox.shrink();
    return Padding(padding: const EdgeInsets.fromLTRB(18, 8, 18, 2), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(l, style: const TextStyle(color: _muted, fontSize: 12, fontWeight: FontWeight.w700)), const SizedBox(height: 3),
      Text('$v', style: const TextStyle(color: Colors.white, fontSize: 12.5, height: 1.4))])); }

  void _openCreate() async {
    final ok = await showModalBottomSheet<bool>(context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
        builder: (_) => const _HandoverCreateSheet());
    if (ok == true) _load();
  }
}

class _HandoverCreateSheet extends StatefulWidget {
  const _HandoverCreateSheet();
  @override
  State<_HandoverCreateSheet> createState() => _HandoverCreateSheetState();
}

class _HandoverCreateSheetState extends State<_HandoverCreateSheet> {
  static const _navy = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _blue = Color(0xFF4AA8FF);
  final _situation = TextEditingController(), _pending = TextEditingController(), _keys = TextEditingController(), _incidents = TextEditingController();
  List _recips = const [], _prems = const [];
  int? _toUid, _premiseId;
  bool _loading = true, _saving = false;

  @override
  void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    try { final o = await context.read<AuthProvider>().api.securityHandoverOptions();
      if (mounted) setState(() { _recips = (o['recipients'] as List?) ?? const []; _prems = (o['premises'] as List?) ?? const [];
        if (_recips.isNotEmpty) _toUid = _recips.first['uid'] as int; if (_prems.isNotEmpty) _premiseId = _prems.first['id'] as int; _loading = false; }); }
    catch (_) { if (mounted) setState(() => _loading = false); }
  }
  @override
  void dispose() { _situation.dispose(); _pending.dispose(); _keys.dispose(); _incidents.dispose(); super.dispose(); }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      await context.read<AuthProvider>().api.securityHandoverCreate({
        if (_toUid != null) 'to_uid': _toUid, if (_premiseId != null) 'premise_id': _premiseId,
        'situation': _situation.text.trim(), 'pending': _pending.text.trim(),
        'keys_note': _keys.text.trim(), 'incidents_note': _incidents.text.trim(),
      });
      if (mounted) Navigator.pop(context, true);
    } catch (e) { if (mounted) { setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(backgroundColor: const Color(0xFFE5484D), content: Text('$e'))); } }
  }

  @override
  Widget build(BuildContext context) => Padding(padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
    child: Container(decoration: const BoxDecoration(color: _card, borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      padding: const EdgeInsets.fromLTRB(18, 12, 18, 22),
      child: _loading ? const SizedBox(height: 180, child: Center(child: CircularProgressIndicator()))
        : SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Center(child: Container(width: 40, height: 4, decoration: BoxDecoration(color: const Color(0xFF34506F), borderRadius: BorderRadius.circular(3)))),
            const SizedBox(height: 14), Text(tr('تسليم وردية', 'New handover'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16)),
            const SizedBox(height: 14),
            _lbl(tr('المستلِم', 'Recipient')),
            DropdownButtonFormField<int>(value: _toUid, isExpanded: true, dropdownColor: _card, style: const TextStyle(color: Colors.white),
                decoration: _dec(), items: [for (final r in _recips) DropdownMenuItem(value: r['uid'] as int, child: Text('${r['name']}', overflow: TextOverflow.ellipsis))],
                onChanged: (v) => setState(() => _toUid = v)),
            const SizedBox(height: 10), _lbl(tr('الموقع', 'Premise')),
            DropdownButtonFormField<int>(value: _premiseId, isExpanded: true, dropdownColor: _card, style: const TextStyle(color: Colors.white),
                decoration: _dec(), items: [for (final p in _prems) DropdownMenuItem(value: p['id'] as int, child: Text('${p['name']}', overflow: TextOverflow.ellipsis))],
                onChanged: (v) => setState(() => _premiseId = v)),
            _field(_situation, tr('الوضع العام', 'Situation'), 2), _field(_pending, tr('مهام معلّقة', 'Pending tasks'), 2),
            _field(_keys, tr('العهدة/المفاتيح', 'Keys/custody'), 1), _field(_incidents, tr('ملاحظات وبلاغات', 'Notes'), 2),
            const SizedBox(height: 14),
            SizedBox(width: double.infinity, child: ElevatedButton(onPressed: _saving ? null : _save,
                style: ElevatedButton.styleFrom(backgroundColor: _blue, foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(vertical: 14), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                child: _saving ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : Text(tr('تسليم', 'Hand over'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)))),
          ]))));

  Widget _lbl(String s) => Padding(padding: const EdgeInsets.only(bottom: 4), child: Text(s, style: const TextStyle(color: Color(0xFF9CB2CD), fontSize: 12.5, fontWeight: FontWeight.w700)));
  InputDecoration _dec() => InputDecoration(isDense: true, filled: true, fillColor: const Color(0xFF0F1B2E),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Color(0xFF2A3B54))),
      enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: Color(0xFF2A3B54))));
  Widget _field(TextEditingController c, String l, int lines) => Padding(padding: const EdgeInsets.only(top: 10), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    _lbl(l), TextField(controller: c, maxLines: lines, style: const TextStyle(color: Colors.white), decoration: _dec())]));
}
