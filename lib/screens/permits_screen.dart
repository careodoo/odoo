import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'pdf_report_screen.dart';

/// «التصاريح» — شاشة تكيّفية: المُصدِر (عميل/مدير مشروع/مشرف) يُنشئ تصاريح (فردية
/// أو متعددة الدخول) ويتابعها؛ والحارس يُدخل/يُخرج الأشخاص على كل تصريح. ترويسة
/// إحصائيات (إجمالي/سارية/بالداخل الآن) + فلترة بالحالة.
class PermitsScreen extends StatefulWidget {
  const PermitsScreen({super.key});
  @override
  State<PermitsScreen> createState() => _PermitsScreenState();
}

class _PermitsScreenState extends State<PermitsScreen> {
  static const _navy = Color(0xFF0E3A5F);
  static const _teal = Color(0xFF0D9488);
  Map<String, dynamic>? _data;
  bool _loading = true;
  String _state = 'all';

  @override
  void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    setState(() => _loading = true);
    try { final d = await context.read<AuthProvider>().api.permitsMine(state: _state);
      if (mounted) setState(() { _data = d; _loading = false; }); }
    catch (_) { if (mounted) setState(() => _loading = false); }
  }

  bool get _canIssue => _data?['can_issue'] == true;
  bool get _isGuard => _data?['is_guard'] == true;

  @override
  Widget build(BuildContext context) {
    final items = ((_data?['items'] as List?) ?? const []).cast<Map>();
    final st = (_data?['stats'] as Map?) ?? const {};
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      appBar: AppBar(title: Text(tr('التصاريح', 'Permits')), backgroundColor: _navy, foregroundColor: Colors.white,
          actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))]),
      floatingActionButton: _canIssue
          ? FloatingActionButton.extended(backgroundColor: _teal,
              onPressed: _openCreate, icon: const Icon(Icons.add), label: Text(tr('تصريح جديد', 'New permit')))
          : null,
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : Column(children: [
              _statsHeader(st),
              _stateBar(),
              Expanded(child: items.isEmpty
                  ? _empty()
                  : RefreshIndicator(onRefresh: _load,
                      child: ListView(padding: const EdgeInsets.fromLTRB(12, 4, 12, 90),
                          children: [for (final p in items) _card(p)]))),
            ]),
    );
  }

  Widget _statsHeader(Map st) => Container(
        margin: const EdgeInsets.fromLTRB(12, 10, 12, 6),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [_teal, _navy], begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.circular(16)),
        child: Row(children: [
          _s('${st['total'] ?? 0}', tr('الإجمالي', 'Total'), Colors.white),
          _sep(), _s('${st['active'] ?? 0}', tr('سارية', 'Active'), const Color(0xFFB9F6CA)),
          _sep(), _s('${st['inside'] ?? 0}', tr('بالداخل الآن', 'Inside now'), const Color(0xFFFFE082)),
          _sep(), _s('${st['expired'] ?? 0}', tr('منتهية', 'Expired'), const Color(0xFFFFCDD2)),
        ]));
  Widget _sep() => Container(width: 1, height: 30, color: Colors.white24);
  Widget _s(String v, String l, Color c) => Expanded(child: Column(children: [
        Text(v, style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 19)),
        const SizedBox(height: 2),
        Text(l, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white70, fontSize: 10, fontWeight: FontWeight.w600)),
      ]));

  Widget _stateBar() {
    const states = [('all', 'الكل', 'All'), ('approved', 'معتمدة', 'Approved'), ('valid', 'سارية', 'Valid'), ('expired', 'منتهية', 'Expired'), ('cancelled', 'ملغاة', 'Cancelled')];
    return SizedBox(height: 42, child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 10), children: [
      for (final s in states) Padding(padding: const EdgeInsets.only(left: 7, top: 5, bottom: 5),
        child: ChoiceChip(label: Text(tr(s.$2, s.$3)), selected: _state == s.$1,
          selectedColor: _teal, labelStyle: TextStyle(color: _state == s.$1 ? Colors.white : _navy, fontWeight: FontWeight.w700, fontSize: 12),
          onSelected: (_) => setState(() { _state = s.$1; _load(); }))),
    ]));
  }

  Widget _empty() => ListView(children: [
        const SizedBox(height: 100),
        const Icon(Icons.badge_rounded, size: 74, color: Color(0xFFB6C2D2)),
        const SizedBox(height: 12),
        Center(child: Text(tr('لا تصاريح.', 'No permits.'), style: const TextStyle(color: Color(0xFF64748B)))),
      ]);

  Color _stateColor(String? s) => s == 'valid' || s == 'approved' ? const Color(0xFF16A34A)
      : s == 'expired' ? const Color(0xFF9CA3AF) : s == 'cancelled' ? const Color(0xFFDC2626) : const Color(0xFFF59E0B);

  Widget _card(Map p) {
    final multi = p['is_multi_entry'] == true;
    final inside = (p['current_inside'] ?? 0) as int;
    return InkWell(
      onTap: () => _openDetail(p['id'] as int),
      child: Container(
        margin: const EdgeInsets.only(bottom: 10), padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
            boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 8, offset: const Offset(0, 2))]),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(width: 40, height: 40, decoration: BoxDecoration(color: _navy.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(11)),
                child: Icon(p['pass_type'] == 'vehicle' ? Icons.directions_car_rounded : Icons.person_rounded, color: _navy)),
            const SizedBox(width: 11),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${p['visitor'] ?? '—'}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: Color(0xFF1E293B))),
              const SizedBox(height: 2),
              Text([p['premise'], p['name']].where((x) => x != null).join(' · '),
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Color(0xFF64748B), fontSize: 11)),
            ])),
            Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(color: _stateColor('${p['state']}').withValues(alpha: 0.14), borderRadius: BorderRadius.circular(8)),
                child: Text('${p['state_label'] ?? ''}', style: TextStyle(color: _stateColor('${p['state']}'), fontSize: 10, fontWeight: FontWeight.w800))),
          ]),
          const SizedBox(height: 9),
          Wrap(spacing: 7, runSpacing: 6, children: [
            _tag(multi ? tr('متعدد الدخول', 'Multi-entry') : tr('فردي', 'Single'), multi ? const Color(0xFF7C3AED) : const Color(0xFF0891B2), multi ? Icons.repeat_rounded : Icons.looks_one_rounded),
            if (inside > 0) _tag('${tr('بالداخل', 'Inside')}: $inside', const Color(0xFFF59E0B), Icons.login_rounded),
            if (p['valid_until'] != null) _tag('${tr('حتى', 'Until')} ${p['valid_until']}', const Color(0xFF475569), Icons.schedule_rounded),
          ]),
        ]),
      ),
    );
  }

  Widget _tag(String s, Color c, IconData ic) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(8)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [Icon(ic, size: 12, color: c), const SizedBox(width: 4),
          Text(s, style: TextStyle(color: c, fontSize: 10, fontWeight: FontWeight.w800))]),
      );

  // ============ إنشاء تصريح ============
  void _openCreate() async {
    final created = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => const _CreatePermitSheet());
    if (created == true) _load();
  }

  // ============ تفاصيل + دخول/خروج ============
  void _openDetail(int id) {
    showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _PermitDetailSheet(id: id, isGuard: _isGuard, onChanged: _load));
  }
}

// ================= ورقة إنشاء التصريح =================
class _CreatePermitSheet extends StatefulWidget {
  const _CreatePermitSheet();
  @override
  State<_CreatePermitSheet> createState() => _CreatePermitSheetState();
}

class _CreatePermitSheetState extends State<_CreatePermitSheet> {
  static const _navy = Color(0xFF0E3A5F);
  static const _teal = Color(0xFF0D9488);
  final _name = TextEditingController();
  final _phone = TextEditingController();
  final _purpose = TextEditingController();
  List _premises = const [];
  int? _premiseId;
  String _passType = 'personal';
  bool _multi = false;
  int _days = 1;
  bool _loading = true, _saving = false;

  @override
  void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    try { final o = await context.read<AuthProvider>().api.permitsOptions();
      if (mounted) setState(() { _premises = (o['premises'] as List?) ?? const []; if (_premises.isNotEmpty) _premiseId = _premises.first['id'] as int; _loading = false; }); }
    catch (_) { if (mounted) setState(() => _loading = false); }
  }

  @override
  void dispose() { _name.dispose(); _phone.dispose(); _purpose.dispose(); super.dispose(); }

  Future<void> _save() async {
    if (_name.text.trim().isEmpty || _premiseId == null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('الاسم والموقع مطلوبان', 'Name & premise required'))));
      return;
    }
    setState(() => _saving = true);
    final now = DateTime.now();
    final until = now.add(Duration(days: _days));
    String fmt(DateTime d) => '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')} ${d.hour.toString().padLeft(2, '0')}:${d.minute.toString().padLeft(2, '0')}:00';
    try {
      await context.read<AuthProvider>().api.permitCreate({
        'visitor': _name.text.trim(), 'phone': _phone.text.trim(),
        'premise_id': _premiseId, 'purpose': _purpose.text.trim(),
        'pass_type': _passType, 'is_multi_entry': _multi,
        'valid_from': fmt(now), 'valid_until': fmt(until),
      });
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) { setState(() => _saving = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: const Color(0xFFDC2626))); }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: Container(
        decoration: const BoxDecoration(color: Colors.white, borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
        padding: const EdgeInsets.fromLTRB(18, 12, 18, 22),
        child: _loading ? const SizedBox(height: 200, child: Center(child: CircularProgressIndicator()))
            : SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
                Center(child: Container(width: 40, height: 4, decoration: BoxDecoration(color: const Color(0xFFCBD5E1), borderRadius: BorderRadius.circular(3)))),
                const SizedBox(height: 14),
                Text(tr('تصريح جديد', 'New permit'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: _navy)),
                const SizedBox(height: 14),
                _field(_name, tr('اسم الزائر', 'Visitor name'), Icons.person_outline),
                const SizedBox(height: 10),
                _field(_phone, tr('الهاتف', 'Phone'), Icons.phone_outlined, kb: TextInputType.phone),
                const SizedBox(height: 10),
                DropdownButtonFormField<int>(
                  value: _premiseId, isExpanded: true,
                  decoration: _dec(tr('الموقع', 'Premise'), Icons.location_on_outlined),
                  items: [for (final p in _premises) DropdownMenuItem(value: p['id'] as int, child: Text('${p['name']}', overflow: TextOverflow.ellipsis))],
                  onChanged: (v) => setState(() => _premiseId = v)),
                const SizedBox(height: 10),
                _field(_purpose, tr('الغرض', 'Purpose'), Icons.notes_outlined),
                const SizedBox(height: 14),
                Row(children: [
                  Expanded(child: _typeBtn('personal', tr('شخصي', 'Personal'), Icons.person_rounded)),
                  const SizedBox(width: 8),
                  Expanded(child: _typeBtn('vehicle', tr('مركبة', 'Vehicle'), Icons.directions_car_rounded)),
                ]),
                const SizedBox(height: 12),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero, activeColor: _teal,
                  title: Text(tr('متعدد الدخول', 'Multi-entry'), style: const TextStyle(fontWeight: FontWeight.w700, color: _navy)),
                  subtitle: Text(tr('يسمح بعدّة دخول/خروج خلال المدة', 'Allows multiple entries during validity'), style: const TextStyle(fontSize: 11)),
                  value: _multi, onChanged: (v) => setState(() => _multi = v)),
                Row(children: [
                  Text(tr('مدة الصلاحية (أيام)', 'Validity (days)'), style: const TextStyle(color: _navy, fontWeight: FontWeight.w700)),
                  const Spacer(),
                  IconButton(onPressed: () => setState(() => _days = _days > 1 ? _days - 1 : 1), icon: const Icon(Icons.remove_circle_outline)),
                  Text('$_days', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
                  IconButton(onPressed: () => setState(() => _days += 1), icon: const Icon(Icons.add_circle_outline)),
                ]),
                const SizedBox(height: 8),
                SizedBox(width: double.infinity, child: ElevatedButton(
                  onPressed: _saving ? null : _save,
                  style: ElevatedButton.styleFrom(backgroundColor: _teal, foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(vertical: 14), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                  child: _saving ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : Text(tr('إصدار التصريح', 'Issue permit'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)))),
              ])),
      ),
    );
  }

  Widget _typeBtn(String v, String label, IconData ic) {
    final sel = _passType == v;
    return InkWell(onTap: () => setState(() => _passType = v), borderRadius: BorderRadius.circular(12),
      child: Container(padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(color: sel ? _navy : const Color(0xFFF1F5F9), borderRadius: BorderRadius.circular(12), border: Border.all(color: sel ? _navy : const Color(0xFFE2E8F0))),
        child: Column(children: [Icon(ic, color: sel ? Colors.white : _navy, size: 20), const SizedBox(height: 4),
          Text(label, style: TextStyle(color: sel ? Colors.white : _navy, fontWeight: FontWeight.w700, fontSize: 12))])));
  }

  InputDecoration _dec(String l, IconData ic) => InputDecoration(labelText: l, prefixIcon: Icon(ic, size: 20),
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)), isDense: true);
  Widget _field(TextEditingController c, String l, IconData ic, {TextInputType? kb}) =>
      TextField(controller: c, keyboardType: kb, decoration: _dec(l, ic));
}

// ================= ورقة تفاصيل التصريح + دخول/خروج =================
class _PermitDetailSheet extends StatefulWidget {
  final int id; final bool isGuard; final VoidCallback onChanged;
  const _PermitDetailSheet({required this.id, required this.isGuard, required this.onChanged});
  @override
  State<_PermitDetailSheet> createState() => _PermitDetailSheetState();
}

class _PermitDetailSheetState extends State<_PermitDetailSheet> {
  static const _navy = Color(0xFF0E3A5F);
  Map<String, dynamic>? _d;
  bool _busy = false;

  @override
  void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    try { final d = await context.read<AuthProvider>().api.permitDetail(widget.id); if (mounted) setState(() => _d = d); }
    catch (_) { if (mounted) setState(() => _d = {}); }
  }

  Future<void> _visit(String dir) async {
    final person = await showDialog<String>(context: context, builder: (_) => const _PersonDialog());
    if (person == null) return;
    setState(() => _busy = true);
    try {
      final d = await context.read<AuthProvider>().api.permitVisit(widget.id, dir, {'person': person});
      if (mounted) { setState(() { _d = d; _busy = false; }); widget.onChanged();
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(backgroundColor: const Color(0xFF16A34A),
          content: Text(dir == 'in' ? tr('تم تسجيل الدخول', 'Entry recorded') : tr('تم تسجيل الخروج', 'Exit recorded')))); }
    } catch (e) {
      if (mounted) { setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(backgroundColor: const Color(0xFFDC2626), content: Text('$e'))); }
    }
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    if (d == null) return const SizedBox(height: 220, child: Center(child: CircularProgressIndicator()));
    final logs = ((d['logs'] as List?) ?? const []).cast<Map>();
    final active = d['state'] == 'approved' || d['state'] == 'valid';
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
        const SizedBox(height: 10),
        Center(child: Container(width: 40, height: 4, decoration: BoxDecoration(color: const Color(0xFFCBD5E1), borderRadius: BorderRadius.circular(3)))),
        const SizedBox(height: 14),
        Padding(padding: const EdgeInsets.fromLTRB(18, 0, 6, 0), child: Row(children: [
          Expanded(child: Text('${d['visitor'] ?? '—'}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 18, color: _navy))),
          IconButton(
            tooltip: tr('طباعة PDF', 'Print PDF'),
            icon: const Icon(Icons.print_rounded, color: _navy),
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
                path: '/cafm/permit/${widget.id}/card.pdf',
                title: tr('بطاقة التصريح', 'Permit card'), fileName: 'permit-${widget.id}.pdf'))),
          ),
          Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
            decoration: BoxDecoration(color: (d['is_multi_entry'] == true ? const Color(0xFF7C3AED) : const Color(0xFF0891B2)).withValues(alpha: 0.14), borderRadius: BorderRadius.circular(8)),
            child: Text(d['is_multi_entry'] == true ? tr('متعدد الدخول', 'Multi-entry') : tr('فردي', 'Single'),
              style: TextStyle(color: d['is_multi_entry'] == true ? const Color(0xFF7C3AED) : const Color(0xFF0891B2), fontWeight: FontWeight.w800, fontSize: 11))),
        ])),
        const SizedBox(height: 10),
        _row(tr('الرقم', 'No.'), d['name']),
        _row(tr('الموقع', 'Premise'), d['premise']),
        _row(tr('العميل', 'Client'), d['client']),
        _row(tr('الهاتف', 'Phone'), d['phone']),
        _row(tr('الغرض', 'Purpose'), d['purpose']),
        _row(tr('من', 'From'), d['valid_from']),
        _row(tr('حتى', 'Until'), d['valid_until']),
        _row(tr('الحالة', 'State'), d['state_label']),
        _row(tr('بالداخل الآن', 'Inside now'), '${d['current_inside'] ?? 0}'),
        _row(tr('مرّات الدخول', 'Entries'), '${d['entries_count'] ?? 0}'),
        // أزرار الحارس: دخول/خروج
        if (active) Padding(padding: const EdgeInsets.fromLTRB(16, 14, 16, 6), child: Row(children: [
          Expanded(child: ElevatedButton.icon(onPressed: _busy ? null : () => _visit('in'),
            icon: const Icon(Icons.login_rounded), label: Text(tr('تسجيل دخول', 'Check in')),
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF16A34A), foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(vertical: 13), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))))),
          const SizedBox(width: 10),
          Expanded(child: ElevatedButton.icon(onPressed: _busy ? null : () => _visit('out'),
            icon: const Icon(Icons.logout_rounded), label: Text(tr('تسجيل خروج', 'Check out')),
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFEA580C), foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(vertical: 13), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))))),
        ])),
        if (logs.isNotEmpty) ...[
          Padding(padding: const EdgeInsets.fromLTRB(18, 14, 18, 6), child: Text(tr('سجلّ الدخول/الخروج', 'Entry / exit log'), style: const TextStyle(color: Color(0xFF64748B), fontWeight: FontWeight.w700, fontSize: 12))),
          for (final l in logs) Padding(padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 4), child: Row(children: [
            Icon(l['type'] == 'check_in' ? Icons.login_rounded : Icons.logout_rounded, size: 16,
              color: l['type'] == 'check_in' ? const Color(0xFF16A34A) : const Color(0xFFEA580C)),
            const SizedBox(width: 8),
            Expanded(child: Text([l['type_label'], l['note']].where((x) => x != null && '$x'.isNotEmpty).join(' — '), style: const TextStyle(fontSize: 12.5, color: Color(0xFF1E293B)))),
            Text('${l['at'] ?? ''}', style: const TextStyle(fontSize: 10, color: Color(0xFF94A3B8))),
          ])),
        ],
        const SizedBox(height: 20),
      ])),
    );
  }

  Widget _row(String l, dynamic v) {
    if (v == null || '$v'.isEmpty) return const SizedBox.shrink();
    return Padding(padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 5), child: Row(children: [
      Text(l, style: const TextStyle(color: Color(0xFF64748B), fontSize: 12.5)),
      const Spacer(),
      Flexible(child: Text('$v', textAlign: TextAlign.end, style: const TextStyle(color: Color(0xFF1E293B), fontSize: 12.5, fontWeight: FontWeight.w600))),
    ]));
  }
}

// حوار إدخال اسم الشخص الداخل/الخارج
class _PersonDialog extends StatefulWidget {
  const _PersonDialog();
  @override
  State<_PersonDialog> createState() => _PersonDialogState();
}

class _PersonDialogState extends State<_PersonDialog> {
  final _c = TextEditingController();
  @override
  void dispose() { _c.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) => AlertDialog(
        title: Text(tr('اسم الشخص', 'Person name')),
        content: TextField(controller: _c, autofocus: true,
            decoration: InputDecoration(hintText: tr('الاسم / رقم الهوية', 'Name / ID'), border: const OutlineInputBorder())),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: Text(tr('إلغاء', 'Cancel'))),
          ElevatedButton(onPressed: () => Navigator.pop(context, _c.text.trim().isEmpty ? '—' : _c.text.trim()), child: Text(tr('تأكيد', 'Confirm'))),
        ],
      );
}
