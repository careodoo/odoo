import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// طلبات الفواتير: رفعها (مدير المشروع)، اعتماد المدير، ثم اعتماد الإدارة المالية
/// وتوليد الفاتورة — مرآةً لمسار الباك ايند.
class InvoiceRequestsScreen extends StatefulWidget {
  const InvoiceRequestsScreen({super.key});
  @override
  State<InvoiceRequestsScreen> createState() => _InvoiceRequestsScreenState();
}

class _InvoiceRequestsScreenState extends State<InvoiceRequestsScreen> {
  static const _navy = Color(0xFF123A6B);
  static const _gold = Color(0xFFC19A3E);
  static const _green = Color(0xFF2E7D5B);

  String _filter = 'all';
  Map<String, dynamic> _counts = {};
  Future<Map<String, dynamic>>? _future;

  static const _tabs = [
    ['all', 'الكل', 'All'],
    ['draft', 'مسودّة', 'Draft'],
    ['manager', 'اعتماد المدير', 'Manager'],
    ['finance', 'المالية', 'Finance'],
    ['invoiced', 'مُفوتر', 'Invoiced'],
  ];
  static const _stateColor = {
    'draft': Color(0xFF8A95A6), 'manager': Color(0xFF2B5E9E),
    'finance': _gold, 'invoiced': _green,
    'rejected': Color(0xFFC0392B), 'cancel': Color(0xFFC0392B),
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => setState(() =>
      _future = context.read<AuthProvider>().api.invoiceRequests(filter: _filter));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF1F4F8),
      appBar: AppBar(
        backgroundColor: _navy, foregroundColor: Colors.white,
        title: Text(tr('طلبات الفواتير', 'Invoice requests')),
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh))],
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: _gold, foregroundColor: Colors.white,
        onPressed: _raise, icon: const Icon(Icons.add),
        label: Text(tr('رفع طلب', 'Raise'), style: const TextStyle(fontWeight: FontWeight.w800)),
      ),
      body: Column(children: [
        _tabsBar(),
        Expanded(child: RefreshIndicator(
          onRefresh: () async => _load(),
          child: FutureBuilder<Map<String, dynamic>>(
            future: _future,
            builder: (_, snap) {
              if (snap.connectionState == ConnectionState.waiting) {
                return const Center(child: CircularProgressIndicator());
              }
              if (snap.hasError) {
                return ListView(children: [const SizedBox(height: 120), Center(child: Text('${snap.error}'))]);
              }
              _counts = (snap.data?['counts'] as Map?)?.cast<String, dynamic>() ?? _counts;
              final rows = ((snap.data?['data'] as List?) ?? const []).cast<Map>();
              if (rows.isEmpty) {
                return ListView(children: [
                  const SizedBox(height: 120),
                  Center(child: Column(children: [
                    const Icon(Icons.receipt_long_outlined, size: 56, color: Colors.grey),
                    const SizedBox(height: 8),
                    Text(tr('لا طلبات', 'No requests'), style: const TextStyle(color: Colors.grey)),
                  ])),
                ]);
              }
              return ListView.builder(
                padding: const EdgeInsets.all(12),
                itemCount: rows.length,
                itemBuilder: (_, i) => _card(rows[i]),
              );
            },
          ),
        )),
      ]),
    );
  }

  Widget _tabsBar() => Container(
        color: Colors.white,
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 10),
          child: Row(children: [
            for (final t in _tabs) ...[
              Builder(builder: (_) {
                final on = _filter == t[0];
                final c = _counts[t[0]];
                return GestureDetector(
                  onTap: () { setState(() => _filter = t[0]); _load(); },
                  child: Container(
                    margin: const EdgeInsets.symmetric(horizontal: 4),
                    padding: const EdgeInsets.symmetric(horizontal: 15, vertical: 8),
                    decoration: BoxDecoration(
                      color: on ? _navy : const Color(0xFFEEF1F5),
                      borderRadius: BorderRadius.circular(20)),
                    child: Text(
                      '${gLang == 'en' ? t[2] : t[1]}${c != null && t[0] != 'all' ? ' ($c)' : ''}',
                      style: TextStyle(color: on ? Colors.white : const Color(0xFF5B677B),
                          fontWeight: FontWeight.w800, fontSize: 12.5)),
                  ),
                );
              }),
            ],
          ]),
        ),
      );

  Widget _card(Map o) {
    final col = _stateColor['${o['state']}'] ?? Colors.grey;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
          boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 2))]),
      child: ListTile(
        onTap: () => _detail(o['id'] as int),
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
        leading: Container(width: 42, height: 42,
          decoration: BoxDecoration(color: col.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)),
          child: Icon(Icons.receipt_long_rounded, color: col)),
        title: Text('${o['name']} · ${o['partner'] ?? ''}',
            maxLines: 1, overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14, color: _navy)),
        subtitle: Text('${o['department'] ?? o['contract'] ?? ''} · ${o['date'] ?? ''}',
            maxLines: 1, overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 12, color: Color(0xFF5B677B))),
        trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
          Text('${o['amount']} ${o['currency'] ?? ''}',
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: _navy)),
          const SizedBox(height: 4),
          Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(color: col.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(20)),
            child: Text('${o['state_label']}', style: TextStyle(color: col, fontWeight: FontWeight.w800, fontSize: 10.5))),
        ]),
      ),
    );
  }

  // ---------- detail sheet ----------
  void _detail(int id) async {
    await showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (ctx) => _DetailSheet(id: id, onChanged: _load),
    );
  }

  // ---------- raise ----------
  void _raise() async {
    final api = context.read<AuthProvider>().api;
    List<dynamic> contracts;
    try {
      contracts = await api.invoiceRequestContracts();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      return;
    }
    if (!mounted) return;
    if (contracts.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('لا عقود متاحة للرفع', 'No contracts available'))));
      return;
    }
    int? contractId;
    DateTime date = DateTime.now();
    await showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => StatefulBuilder(builder: (ctx, setS) {
        return Padding(
          padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom + 16, left: 16, right: 16, top: 16),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Center(child: Container(width: 40, height: 4, decoration: BoxDecoration(color: Colors.black26, borderRadius: BorderRadius.circular(3)))),
            const SizedBox(height: 14),
            Text(tr('رفع طلب فاتورة', 'Raise invoice request'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: _navy)),
            const SizedBox(height: 4),
            Text(tr('يُنسخ آخر طلب لهذا العقد كأساس، ثم يمكنك تعديله.', 'Copies the contract\'s last request as a base.'),
                style: const TextStyle(fontSize: 12, color: Color(0xFF5B677B))),
            const SizedBox(height: 16),
            Text(tr('العقد', 'Contract'), style: const TextStyle(fontWeight: FontWeight.w700)),
            const SizedBox(height: 6),
            DropdownButtonFormField<int>(
              value: contractId, isExpanded: true,
              decoration: const InputDecoration(border: OutlineInputBorder(), isDense: true),
              items: [for (final c in contracts)
                DropdownMenuItem(value: c['id'] as int, child: Text('${c['name']}', overflow: TextOverflow.ellipsis))],
              onChanged: (v) => setS(() => contractId = v),
            ),
            const SizedBox(height: 14),
            Row(children: [
              Text(tr('تاريخ الفاتورة:', 'Invoice date:'), style: const TextStyle(fontWeight: FontWeight.w700)),
              const Spacer(),
              TextButton.icon(
                onPressed: () async {
                  final p = await showDatePicker(context: ctx, initialDate: date,
                      firstDate: DateTime(2023), lastDate: DateTime(2030));
                  if (p != null) setS(() => date = p);
                },
                icon: const Icon(Icons.calendar_month, size: 18),
                label: Text('${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}'),
              ),
            ]),
            const SizedBox(height: 16),
            SizedBox(width: double.infinity, height: 48, child: ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: _gold, foregroundColor: Colors.white),
              onPressed: contractId == null ? null : () async {
                try {
                  final d = '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
                  await api.invoiceRequestRaise(contractId!, d);
                  if (ctx.mounted) Navigator.pop(ctx);
                  if (mounted) { _load(); ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                      content: Text(tr('تم رفع الطلب كمسودّة', 'Draft raised')), backgroundColor: _green)); }
                } catch (e) {
                  if (ctx.mounted) ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(content: Text('$e')));
                }
              },
              child: Text(tr('رفع', 'Raise'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
            )),
          ]),
        );
      }),
    );
  }
}

// ============================ detail sheet ============================
class _DetailSheet extends StatefulWidget {
  const _DetailSheet({required this.id, required this.onChanged});
  final int id;
  final VoidCallback onChanged;
  @override
  State<_DetailSheet> createState() => _DetailSheetState();
}

class _DetailSheetState extends State<_DetailSheet> {
  static const _navy = Color(0xFF123A6B);
  static const _gold = Color(0xFFC19A3E);
  static const _green = Color(0xFF2E7D5B);
  Map<String, dynamic>? _d;
  bool _busy = false;

  @override
  void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    final d = await context.read<AuthProvider>().api.invoiceRequestDetail(widget.id);
    if (mounted) setState(() => _d = d);
  }

  Future<void> _action(String action, {String? reason}) async {
    setState(() => _busy = true);
    try {
      final api = context.read<AuthProvider>().api;
      final d = reason != null
          ? await api.invoiceRequestReject(widget.id, reason)
          : await api.invoiceRequestAction(widget.id, action);
      if (mounted) { setState(() { _d = d; _busy = false; }); widget.onChanged(); }
    } catch (e) {
      if (mounted) { setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'))); }
    }
  }

  Future<void> _rejectDialog() async {
    final ctrl = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      title: Text(tr('سبب الرفض', 'Rejection reason')),
      content: TextField(controller: ctrl, maxLines: 3, decoration: const InputDecoration(border: OutlineInputBorder())),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFFC0392B)),
            onPressed: () => Navigator.pop(c, true), child: Text(tr('رفض', 'Reject'))),
      ],
    ));
    if (ok == true) _action('reject', reason: ctrl.text.trim());
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.85, maxChildSize: 0.96, minChildSize: 0.5,
      builder: (_, sc) => Container(
        decoration: const BoxDecoration(color: Color(0xFFF4F7FB), borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
        child: _d == null
            ? const Center(child: Padding(padding: EdgeInsets.all(40), child: CircularProgressIndicator()))
            : Column(children: [
                _header(),
                Expanded(child: ListView(controller: sc, padding: const EdgeInsets.all(16), children: _bodyChildren())),
                _actionBar(),
              ]),
      ),
    );
  }

  Widget _header() {
    final d = _d!;
    return Container(
      width: double.infinity, padding: const EdgeInsets.fromLTRB(18, 14, 18, 16),
      decoration: const BoxDecoration(color: _navy, borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12),
            decoration: BoxDecoration(color: Colors.white38, borderRadius: BorderRadius.circular(3)))),
        Row(children: [
          Expanded(child: Text('${d['name']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18))),
          Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(20)),
            child: Text('${d['state_label']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 11))),
        ]),
        const SizedBox(height: 4),
        Text('${d['partner'] ?? ''}', style: const TextStyle(color: Colors.white70, fontSize: 12.5)),
      ]),
    );
  }

  List<Widget> _bodyChildren() {
    final d = _d!;
    final lines = (d['lines'] as List?)?.cast<Map>() ?? const [];
    final terms = (d['terms'] as List?)?.cast<String>() ?? const [];
    return [
      _infoCard(),
      if (d['over_budget'] == true) _alert(tr('⚠️ يتجاوز قيمة العقد المتبقية', '⚠️ Exceeds remaining contract value'), const Color(0xFFC0392B)),
      if (d['timesheet_match'] == 'mismatch') _alert(tr('🕒 عدد العمالة لا يطابق التايم شيت', '🕒 Labor count mismatches timesheet'), _gold),
      const SizedBox(height: 12),
      Text(tr('البنود', 'Lines'), style: const TextStyle(fontWeight: FontWeight.w900, color: _navy)),
      const SizedBox(height: 6),
      for (final l in lines) Container(
        margin: const EdgeInsets.only(bottom: 6), padding: const EdgeInsets.all(11),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(10)),
        child: Row(children: [
          Expanded(child: Text('${l['product']}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13))),
          Text('${l['qty']}×${l['days']} · ${l['subtotal']}', style: const TextStyle(color: Color(0xFF5B677B), fontSize: 12)),
        ]),
      ),
      if (terms.isNotEmpty) ...[
        const SizedBox(height: 12),
        Text(tr('الشروط', 'Terms'), style: const TextStyle(fontWeight: FontWeight.w900, color: _navy)),
        const SizedBox(height: 6),
        for (final t in terms) Padding(padding: const EdgeInsets.only(bottom: 4),
            child: Text('• $t', style: const TextStyle(fontSize: 12.5, color: Color(0xFF31404F)))),
      ],
      const SizedBox(height: 16),
    ];
  }

  Widget _infoCard() {
    final d = _d!;
    Widget row(String k, String v, {Color? c}) => Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(children: [
        Text(k, style: const TextStyle(color: Color(0xFF5B677B), fontSize: 12.5)),
        const Spacer(),
        Text(v, style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: c ?? const Color(0xFF182131))),
      ]),
    );
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
      child: Column(children: [
        row(tr('الإجمالي', 'Total'), '${d['amount']} ${d['currency'] ?? ''}', c: _navy),
        row(tr('العقد', 'Contract'), '${d['contract'] ?? '—'}'),
        row(tr('قيمة العقد', 'Contract value'), '${d['contract_amount'] ?? 0}'),
        row(tr('متبقٍ من العقد', 'Remaining'), '${d['contract_remaining'] ?? 0}',
            c: d['over_budget'] == true ? const Color(0xFFC0392B) : _green),
        row(tr('عمالة (تايم شيت/مفوتر)', 'Labor (ts/billed)'),
            '${d['timesheet_worker_count'] ?? 0} / ${d['billed_worker_count'] ?? 0}',
            c: d['timesheet_match'] == 'match' ? _green : (d['timesheet_match'] == 'mismatch' ? _gold : null)),
        row(tr('التاريخ', 'Date'), '${d['date'] ?? '—'}'),
      ]),
    );
  }

  Widget _alert(String text, Color c) => Container(
        margin: const EdgeInsets.only(top: 10), padding: const EdgeInsets.all(11),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(10)),
        child: Text(text, style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 12.5)),
      );

  Widget _actionBar() {
    final d = _d!;
    final btns = <Widget>[];
    Widget b(String label, String action, Color color, {String? reason}) => Expanded(
      child: Padding(padding: const EdgeInsets.symmetric(horizontal: 4),
        child: SizedBox(height: 46, child: ElevatedButton(
          style: ElevatedButton.styleFrom(backgroundColor: color, foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
          onPressed: _busy ? null : (action == 'reject' ? _rejectDialog : () => _action(action)),
          child: Text(label, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
        )),
      ),
    );
    if (d['can_submit'] == true) btns.add(b(tr('إرسال للاعتماد', 'Submit'), 'submit', _navy));
    if (d['can_send_direct'] == true) btns.add(b(tr('مباشر للمالية', 'To finance'), 'send-direct', _gold));
    if (d['can_manager_approve'] == true) btns.add(b(tr('اعتماد المدير', 'Approve'), 'manager-approve', _green));
    if (d['can_finance_generate'] == true) btns.add(b(tr('اعتماد وتوليد', 'Generate'), 'finance-generate', _green));
    if (d['can_reject'] == true) btns.add(b(tr('رفض', 'Reject'), 'reject', const Color(0xFFC0392B)));
    if (btns.isEmpty) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.fromLTRB(12, 10, 12, 16),
      decoration: const BoxDecoration(color: Colors.white, boxShadow: [BoxShadow(color: Colors.black12, blurRadius: 8, offset: Offset(0, -2))]),
      child: _busy
          ? const Center(child: Padding(padding: EdgeInsets.all(8), child: CircularProgressIndicator()))
          : Row(children: btns),
    );
  }
}
