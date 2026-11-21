import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import '../pdf_report_screen.dart';
import 'management_home.dart' show Mgmt;

/// مركز الموافقات على التطبيق — بيانات حقيقية بالحالة من `care.approval.center`.
///
/// يستبدل لوحة الأرقام الوهمية القديمة: كل الطلبات المعلّقة فعليًا لهذا المستخدم،
/// مجمّعة حسب النوع، مع: موافقة/رفض فوري، عرض النموذج (PDF)، تفاصيل كاملة،
/// و«الاعتماد السريع» لمراجعة الطلبات واحدًا تلو الآخر.
class ApprovalCenterScreen extends StatefulWidget {
  const ApprovalCenterScreen({super.key});
  @override
  State<ApprovalCenterScreen> createState() => _ApprovalCenterScreenState();
}

class _ApprovalCenterScreenState extends State<ApprovalCenterScreen> {
  Map<String, dynamic>? _data;
  bool _loading = true;
  String? _err;
  String? _filter; // group key, null = all

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _err = null; });
    try {
      final d = await context.read<AuthProvider>().api.approvalsData();
      if (mounted) setState(() { _data = d; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _err = '$e'; _loading = false; });
    }
  }

  List<Map> get _groups => ((_data?['groups'] as List?) ?? const []).cast<Map>();
  int get _total => (_data?['count'] ?? 0) as int;

  Color _groupColor(Map g) {
    final hex = '${g['color'] ?? ''}'.replaceAll('#', '');
    if (hex.length == 6) {
      final v = int.tryParse('FF$hex', radix: 16);
      if (v != null) return Color(v);
    }
    return Mgmt.red;
  }

  // ------- actions -------
  void _snack(String msg, {bool bad = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg), backgroundColor: bad ? const Color(0xFFB91C1C) : const Color(0xFF15803D),
      behavior: SnackBarBehavior.floating, duration: const Duration(milliseconds: 1800)));
  }

  /// يُزيل سجلًّا من البيانات المحلية بعد القرار (تحديث فوري بلا إعادة تحميل كامل).
  void _removeLocal(String model, int id) {
    for (final g in _groups) {
      final recs = (g['records'] as List?)?.cast<Map>() ?? [];
      recs.removeWhere((r) => '${r['model']}' == model && (r['id'] as int) == id);
      g['records'] = recs;
      g['count'] = recs.length;
    }
    _data!['groups'] = _groups.where((g) => (g['count'] as int) > 0).toList();
    _data!['count'] = _groups.fold<int>(0, (a, g) => a + (g['count'] as int));
    if (mounted) setState(() {});
  }

  Future<bool> _decide(String model, int id, bool approve, {String reason = ''}) async {
    try {
      await context.read<AuthProvider>().api.approvalDecide(model, id, approve, reason: reason);
      _removeLocal(model, id);
      _snack(approve ? tr('✅ تمّت الموافقة وخُتم التوقيع', '✅ Approved & signed')
                     : tr('✖ تم الرفض وأُشعِر مُقدّم الطلب', '✖ Rejected, requester notified'),
             bad: !approve);
      return true;
    } catch (e) {
      _snack(tr('تعذّر التنفيذ: $e', 'Failed: $e'), bad: true);
      return false;
    }
  }

  Future<String?> _askReason() async {
    final ctrl = TextEditingController();
    return showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(tr('سبب الرفض', 'Rejection reason')),
        content: TextField(
          controller: ctrl, autofocus: true, maxLines: 3,
          decoration: InputDecoration(
            hintText: tr('اكتب سبب الرفض — سيصل لمُقدّم الطلب', 'Reason — sent to the requester'),
            border: const OutlineInputBorder()),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: Text(tr('إلغاء', 'Cancel'))),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: const Color(0xFFB91C1C)),
            onPressed: () => Navigator.pop(ctx, ctrl.text.trim()),
            child: Text(tr('رفض', 'Reject'))),
        ],
      ),
    );
  }

  Future<void> _reject(String model, int id) async {
    final reason = await _askReason();
    if (reason == null) return; // cancelled
    await _decide(model, id, false, reason: reason);
  }

  void _openForm(Map rec) {
    Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
      path: '/api/v1/approvals/report?model=${Uri.encodeQueryComponent('${rec['model']}')}&res_id=${rec['id']}',
      title: '${rec['title'] ?? rec['ref'] ?? ''}',
      fileName: 'request-${rec['id']}.pdf',
    )));
  }

  Future<void> _openDetail(Map rec, Color color) async {
    await showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => _DetailSheet(
        model: '${rec['model']}', resId: rec['id'] as int, color: color,
        onApprove: () async { final ok = await _decide('${rec['model']}', rec['id'] as int, true); if (ok && mounted) Navigator.pop(context); },
        onReject: () async { Navigator.pop(context); await _reject('${rec['model']}', rec['id'] as int); },
        onForm: () => _openForm(rec),
      ),
    );
  }

  Future<void> _startQuick() async {
    final queue = <Map>[];
    for (final g in _groups) {
      for (final r in (g['records'] as List).cast<Map>()) {
        queue.add({...r, '_color': _groupColor(g).toARGB32()});
      }
    }
    if (queue.isEmpty) { _snack(tr('لا طلبات للمراجعة', 'Nothing to review')); return; }
    await Navigator.push(context, MaterialPageRoute(builder: (_) => _QuickReviewScreen(
      queue: queue,
      onDecide: (model, id, approve, reason) => _decide(model, id, approve, reason: reason),
    )));
    _load();
  }

  @override
  Widget build(BuildContext context) {
    final groups = _filter == null ? _groups : _groups.where((g) => '${g['key']}' == _filter).toList();
    return Scaffold(
      backgroundColor: Mgmt.bg,
      appBar: AppBar(
        backgroundColor: Mgmt.deep, foregroundColor: Colors.white, elevation: 0,
        title: Row(children: [
          Text(tr('مركز الموافقات', 'Approval Center'),
              style: const TextStyle(fontWeight: FontWeight.w900)),
          const SizedBox(width: 8),
          if (_total > 0) Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 2),
            decoration: BoxDecoration(color: const Color(0xFFDC2626), borderRadius: BorderRadius.circular(12)),
            child: Text('$_total', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5))),
        ]),
        actions: [IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: _load)],
      ),
      floatingActionButton: _total > 0 ? FloatingActionButton.extended(
        backgroundColor: const Color(0xFF15803D),
        icon: const Icon(Icons.bolt_rounded), onPressed: _startQuick,
        label: Text(tr('الاعتماد السريع', 'Quick review'),
            style: const TextStyle(fontWeight: FontWeight.w900))) : null,
      body: _loading ? const Center(child: CircularProgressIndicator())
        : _err != null ? _errorView()
        : _total == 0 ? _emptyView()
        : RefreshIndicator(onRefresh: _load, child: CustomScrollView(slivers: [
            SliverToBoxAdapter(child: _chips()),
            ...groups.map((g) => _groupSliver(g)),
            const SliverToBoxAdapter(child: SizedBox(height: 90)),
          ])),
    );
  }

  Widget _errorView() => Center(child: Padding(padding: const EdgeInsets.all(28), child: Column(
    mainAxisSize: MainAxisSize.min, children: [
      const Icon(Icons.cloud_off_rounded, size: 48, color: Mgmt.slate),
      const SizedBox(height: 12),
      Text(tr('تعذّر التحميل', 'Could not load'), style: const TextStyle(fontWeight: FontWeight.w900)),
      const SizedBox(height: 6), Text('$_err', textAlign: TextAlign.center, style: const TextStyle(color: Mgmt.slate, fontSize: 12)),
      const SizedBox(height: 16), FilledButton(onPressed: _load, child: Text(tr('إعادة', 'Retry'))),
    ])));

  Widget _emptyView() => Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
    const Text('✅', style: TextStyle(fontSize: 54)),
    const SizedBox(height: 10),
    Text(tr('لا طلبات معلّقة — كل شيء مُعتمَد', 'No pending requests — all clear'),
        style: const TextStyle(fontWeight: FontWeight.w800, color: Mgmt.ink)),
  ]));

  Widget _chips() {
    return SizedBox(height: 46, child: ListView(
      scrollDirection: Axis.horizontal, padding: const EdgeInsets.fromLTRB(12, 8, 12, 4),
      children: [
        _chip(tr('الكل', 'All'), null, _total),
        ..._groups.map((g) => _chip('${g['icon']} ${g['module']}', '${g['key']}', g['count'] as int)),
      ]));
  }

  Widget _chip(String label, String? key, int count) {
    final on = _filter == key;
    return Padding(padding: const EdgeInsets.only(left: 7), child: ChoiceChip(
      label: Text('$label ($count)', style: TextStyle(
        fontWeight: FontWeight.w800, fontSize: 12, color: on ? Colors.white : Mgmt.ink)),
      selected: on, selectedColor: Mgmt.deep, backgroundColor: Colors.white,
      shape: StadiumBorder(side: BorderSide(color: on ? Mgmt.deep : const Color(0xFFE2E8F0))),
      onSelected: (_) => setState(() => _filter = on ? null : key),
    ));
  }

  Widget _groupSliver(Map g) {
    final recs = (g['records'] as List).cast<Map>();
    final color = _groupColor(g);
    return SliverList(delegate: SliverChildListDelegate([
      Padding(padding: const EdgeInsets.fromLTRB(14, 14, 14, 6), child: Row(children: [
        Text('${g['icon']}', style: const TextStyle(fontSize: 17)),
        const SizedBox(width: 7),
        Text('${g['module']}', style: const TextStyle(fontWeight: FontWeight.w900, color: Mgmt.ink, fontSize: 14.5)),
        const SizedBox(width: 7),
        Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 1),
          decoration: BoxDecoration(color: color.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(10)),
          child: Text('${recs.length}', style: TextStyle(color: color, fontWeight: FontWeight.w900, fontSize: 11.5))),
        const Spacer(),
        TextButton.icon(
          onPressed: () => _bulkApprove(g),
          style: TextButton.styleFrom(foregroundColor: const Color(0xFF15803D),
            padding: const EdgeInsets.symmetric(horizontal: 8), visualDensity: VisualDensity.compact),
          icon: const Icon(Icons.done_all_rounded, size: 17),
          label: Text(tr('اعتماد الكل', 'Approve all'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12))),
      ])),
      ...recs.map((r) => _recCard(r, color)),
    ]));
  }

  Future<void> _bulkApprove(Map g) async {
    final recs = (g['records'] as List).cast<Map>();
    if (recs.isEmpty) return;
    final api = context.read<AuthProvider>().api;
    final model = '${recs.first['model']}';
    final ids = recs.map((r) => r['id'] as int).toList();
    final ok = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(
      title: Text(tr('اعتماد جماعي', 'Bulk approve')),
      content: Text(tr('اعتماد ${ids.length} طلبًا من «${g['module']}»؟ لا يمكن التراجع.',
                       'Approve ${ids.length} requests in "${g['module']}"? This cannot be undone.')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFF15803D)),
          onPressed: () => Navigator.pop(ctx, true), child: Text(tr('اعتماد الكل', 'Approve all'))),
      ]));
    if (ok != true) return;
    try {
      final r = await api.approvalDecideBulk(model, ids, true);
      final done = (r['done'] ?? 0) as int;
      final failed = ((r['failed'] as List?) ?? const []).length;
      final failedIds = {for (final f in ((r['failed'] as List?) ?? const [])) (f as Map)['id']};
      for (final id in ids) { if (!failedIds.contains(id)) _removeLocal(model, id); }
      _snack('✅ ${tr('اعتُمد', 'Approved')} $done${failed > 0 ? ' · ${tr('فشل', 'failed')} $failed' : ''}');
    } catch (e) {
      _snack(tr('تعذّر: $e', 'Failed: $e'), bad: true);
    }
  }

  Widget _recCard(Map r, Color color) {
    final fields = ((r['fields'] as List?) ?? const []).cast<List>();
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 0, 12, 9),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
        boxShadow: const [BoxShadow(color: Color(0x0F000000), blurRadius: 10, offset: Offset(0, 3))]),
      child: Material(color: Colors.transparent, child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => _openDetail(r, color),
        child: Padding(padding: const EdgeInsets.fromLTRB(13, 12, 13, 10), child: Column(
          crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(width: 40, height: 40, alignment: Alignment.center,
              decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(11)),
              child: Text('${r['initials'] ?? '؟'}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900))),
            const SizedBox(width: 11),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${r['title'] ?? r['ref'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5, color: Mgmt.ink)),
              const SizedBox(height: 2),
              Row(children: [
                Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                  decoration: BoxDecoration(color: const Color(0xFFF1F5F9), borderRadius: BorderRadius.circular(5)),
                  child: Text('${r['ref'] ?? ''}', style: const TextStyle(fontSize: 10.5, color: Mgmt.slate))),
                if ('${r['by'] ?? ''}'.isNotEmpty) ...[
                  const SizedBox(width: 6),
                  Flexible(child: Text('👤 ${r['by']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 10.5, color: Mgmt.slate))),
                ],
              ]),
            ])),
          ]),
          if (fields.isNotEmpty) ...[
            const SizedBox(height: 9),
            Wrap(spacing: 6, runSpacing: 5, children: fields.take(3).map((f) => Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(color: const Color(0xFFF8FAFC), borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFFEEF2F7))),
              child: Text('${f[0]}: ${f[1]}', style: const TextStyle(fontSize: 10.5, color: Mgmt.ink)))).toList()),
          ],
          const SizedBox(height: 10),
          Row(children: [
            Expanded(child: _actBtn(tr('موافقة', 'Approve'), Icons.check_rounded, const Color(0xFF15803D),
              () => _decide('${r['model']}', r['id'] as int, true))),
            const SizedBox(width: 8),
            Expanded(child: _actBtn(tr('رفض', 'Reject'), Icons.close_rounded, const Color(0xFFB91C1C),
              () => _reject('${r['model']}', r['id'] as int))),
            const SizedBox(width: 8),
            _actBtn(tr('عرض', 'Open'), Icons.open_in_full_rounded, Mgmt.deep,
              () => _openDetail(r, color), outline: true),
          ]),
        ])),
      )),
    );
  }

  Widget _actBtn(String label, IconData icon, Color color, VoidCallback onTap, {bool outline = false}) {
    return SizedBox(height: 38, child: outline
      ? OutlinedButton.icon(onPressed: onTap, icon: Icon(icon, size: 16, color: color),
          style: OutlinedButton.styleFrom(foregroundColor: color, side: BorderSide(color: color.withValues(alpha: 0.5)),
            padding: const EdgeInsets.symmetric(horizontal: 12), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
          label: Text(label, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)))
      : FilledButton.icon(onPressed: onTap, icon: Icon(icon, size: 17),
          style: FilledButton.styleFrom(backgroundColor: color,
            padding: const EdgeInsets.symmetric(horizontal: 4), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
          label: Text(label, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5))));
  }
}

/// يفتح تفاصيل طلب اعتماد واحد (من إشعار tap مثلًا) مع موافقة/رفض/عرض النموذج.
Future<void> openApprovalDetail(BuildContext context,
    {required String model, required int id, String title = ''}) async {
  final api = context.read<AuthProvider>().api;
  void snack(String m, {bool bad = false}) {
    if (!context.mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(m), backgroundColor: bad ? const Color(0xFFB91C1C) : const Color(0xFF15803D),
      behavior: SnackBarBehavior.floating));
  }
  Future<String?> askReason() {
    final ctrl = TextEditingController();
    return showDialog<String>(context: context, builder: (ctx) => AlertDialog(
      title: Text(tr('سبب الرفض', 'Rejection reason')),
      content: TextField(controller: ctrl, autofocus: true, maxLines: 3,
        decoration: InputDecoration(hintText: tr('سيصل لمُقدّم الطلب', 'Sent to requester'), border: const OutlineInputBorder())),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFFB91C1C)),
          onPressed: () => Navigator.pop(ctx, ctrl.text.trim()), child: Text(tr('رفض', 'Reject'))),
      ]));
  }
  await showModalBottomSheet(
    context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
    builder: (_) => _DetailSheet(
      model: model, resId: id, color: Mgmt.deep,
      onApprove: () async {
        try { await api.approvalDecide(model, id, true);
          snack(tr('✅ تمّت الموافقة وخُتم التوقيع', '✅ Approved & signed'));
          if (context.mounted) Navigator.pop(context);
        } catch (e) { snack(tr('تعذّر التنفيذ: $e', 'Failed: $e'), bad: true); }
      },
      onReject: () async {
        if (context.mounted) Navigator.pop(context);
        final reason = await askReason();
        if (reason == null) return;
        try { await api.approvalDecide(model, id, false, reason: reason);
          snack(tr('✖ تم الرفض وأُشعِر مُقدّم الطلب', '✖ Rejected, requester notified'), bad: true);
        } catch (e) { snack(tr('تعذّر التنفيذ: $e', 'Failed: $e'), bad: true); }
      },
      onForm: () => Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
        path: '/api/v1/approvals/report?model=${Uri.encodeQueryComponent(model)}&res_id=$id',
        title: title.isEmpty ? tr('النموذج', 'Form') : title, fileName: 'request-$id.pdf'))),
    ),
  );
}

// ======================= تفاصيل الطلب (bottom sheet) =======================
class _DetailSheet extends StatefulWidget {
  const _DetailSheet({required this.model, required this.resId, required this.color,
    required this.onApprove, required this.onReject, required this.onForm});
  final String model;
  final int resId;
  final Color color;
  final Future<void> Function() onApprove;
  final Future<void> Function() onReject;
  final VoidCallback onForm;
  @override
  State<_DetailSheet> createState() => _DetailSheetState();
}

class _DetailSheetState extends State<_DetailSheet> {
  Map<String, dynamic>? _d;
  String? _err;
  bool _busy = false;

  @override
  void initState() { super.initState(); _load(); }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.approvalDetail(widget.model, widget.resId);
      if (mounted) setState(() => _d = d);
    } catch (e) { if (mounted) setState(() => _err = '$e'); }
  }

  Future<void> _runAction(String method) async {
    setState(() => _busy = true);
    try {
      final r = await context.read<AuthProvider>().api.approvalRunAction(widget.model, widget.resId, method);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('✓ ${tr('تمّ التنفيذ', 'Done')}${r['opened_action'] == true ? tr(' (يفتح نموذجًا في النظام)', ' (opens a form in backend)') : ''}'),
        backgroundColor: const Color(0xFF15803D), behavior: SnackBarBehavior.floating));
      await _load();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(tr('تعذّر: $e', 'Failed: $e')), backgroundColor: const Color(0xFFB91C1C), behavior: SnackBarBehavior.floating));
    } finally { if (mounted) setState(() => _busy = false); }
  }

  /// شبكة مؤشّرات القرار + صفّ الأزرار الأخرى (كلٌّ حسب نوع الموديل).
  List<Widget> _decisionWidgets(Map d) {
    final out = <Widget>[];
    final metrics = ((d['metrics'] as List?) ?? const []).cast<Map>();
    if (metrics.isNotEmpty) {
      out.add(Wrap(spacing: 8, runSpacing: 8, children: metrics.map((m) {
        final big = m['big'] == true;
        final good = m['good'];
        final vc = good == false ? const Color(0xFFB91C1C) : (good == true ? const Color(0xFF15803D) : Mgmt.ink);
        return Container(
          width: big ? double.infinity : null,
          constraints: big ? null : const BoxConstraints(minWidth: 150),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
          decoration: BoxDecoration(
            color: big ? const Color(0xFFEEF2FF) : Colors.white,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: big ? const Color(0xFFC7D2FE) : const Color(0xFFEEF2F7))),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Text('${m['label']}', style: const TextStyle(color: Mgmt.slate, fontWeight: FontWeight.w700, fontSize: 11)),
            const SizedBox(height: 2),
            Text('${m['value']}', style: TextStyle(color: vc, fontWeight: FontWeight.w900, fontSize: big ? 18 : 15)),
          ]));
      }).toList()));
      out.add(const SizedBox(height: 12));
    }
    final actions = ((d['actions'] as List?) ?? const []).cast<Map>();
    if (actions.isNotEmpty) {
      out.add(Container(
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(color: const Color(0xFFF8FAFC), borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0xFFE2E8F0), style: BorderStyle.solid)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(tr('إجراءات أخرى', 'Other actions'), style: const TextStyle(color: Mgmt.slate, fontWeight: FontWeight.w800, fontSize: 12)),
          const SizedBox(height: 8),
          Wrap(spacing: 7, runSpacing: 7, children: actions.map((a) => OutlinedButton(
            onPressed: _busy ? null : () => _runAction('${a['name']}'),
            style: OutlinedButton.styleFrom(
              foregroundColor: a['primary'] == true ? Mgmt.deep : Mgmt.ink,
              side: BorderSide(color: a['primary'] == true ? Mgmt.deep : const Color(0xFFD9DEE7)),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              visualDensity: VisualDensity.compact),
            child: Text('${a['string']}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5)))).toList()),
        ])));
      out.add(const SizedBox(height: 12));
    }
    return out;
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final fields = ((d?['all_fields'] as List?) ?? (d?['fields'] as List?) ?? const []).cast<List>();
    final canAct = (d?['can_act'] ?? true) != false;
    return DraggableScrollableSheet(
      initialChildSize: 0.8, minChildSize: 0.5, maxChildSize: 0.96, expand: false,
      builder: (_, ctrl) => Container(
        decoration: const BoxDecoration(color: Mgmt.bg,
          borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
        child: Column(children: [
          Container(
            padding: const EdgeInsets.fromLTRB(18, 10, 10, 14),
            decoration: BoxDecoration(color: widget.color,
              borderRadius: const BorderRadius.vertical(top: Radius.circular(22))),
            child: Column(children: [
              Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 10),
                decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3))),
              Row(children: [
                Expanded(child: Text('${d?['icon'] ?? ''} ${d?['title'] ?? d?['ref'] ?? tr('تفاصيل', 'Details')}',
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16))),
                IconButton(icon: const Icon(Icons.close_rounded, color: Colors.white),
                  onPressed: () => Navigator.pop(context)),
              ]),
              if (d != null) Align(alignment: AlignmentDirectional.centerStart, child: Text(
                '${d['module'] ?? ''} · ${d['ref'] ?? ''} · ${d['state_label'] ?? ''}',
                style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 11.5))),
            ]),
          ),
          Expanded(child: d == null && _err == null
            ? const Center(child: CircularProgressIndicator())
            : _err != null ? Center(child: Text('$_err', style: const TextStyle(color: Mgmt.slate)))
            : ListView(controller: ctrl, padding: const EdgeInsets.fromLTRB(14, 14, 14, 14), children: [
                OutlinedButton.icon(onPressed: widget.onForm,
                  icon: const Icon(Icons.picture_as_pdf_outlined, size: 18),
                  style: OutlinedButton.styleFrom(foregroundColor: Mgmt.deep,
                    minimumSize: const Size.fromHeight(44)),
                  label: Text(tr('عرض النموذج (PDF)', 'View form (PDF)'),
                    style: const TextStyle(fontWeight: FontWeight.w800))),
                const SizedBox(height: 12),
                ..._decisionWidgets(d!),
                Container(
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
                  child: Column(children: [
                    for (int i = 0; i < fields.length; i++)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 10),
                        decoration: BoxDecoration(border: Border(
                          bottom: BorderSide(color: i == fields.length - 1 ? Colors.transparent : const Color(0xFFEEF2F7)))),
                        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          SizedBox(width: 120, child: Text('${fields[i][0]}',
                            style: const TextStyle(color: Mgmt.slate, fontWeight: FontWeight.w700, fontSize: 12))),
                          const SizedBox(width: 8),
                          Expanded(child: Text('${fields[i][1]}',
                            style: const TextStyle(color: Mgmt.ink, fontWeight: FontWeight.w700, fontSize: 12.5))),
                        ]),
                      ),
                  ]),
                ),
              ])),
          SafeArea(top: false, child: Padding(
            padding: const EdgeInsets.fromLTRB(14, 8, 14, 10),
            child: canAct ? Row(children: [
              Expanded(child: FilledButton.icon(
                onPressed: _busy ? null : () async { setState(() => _busy = true); await widget.onApprove(); },
                icon: const Icon(Icons.check_rounded),
                style: FilledButton.styleFrom(backgroundColor: const Color(0xFF15803D), minimumSize: const Size.fromHeight(48)),
                label: Text(tr('موافقة', 'Approve'), style: const TextStyle(fontWeight: FontWeight.w900)))),
              const SizedBox(width: 10),
              Expanded(child: OutlinedButton.icon(
                onPressed: _busy ? null : widget.onReject,
                icon: const Icon(Icons.close_rounded, color: Color(0xFFB91C1C)),
                style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFB91C1C),
                  side: const BorderSide(color: Color(0xFFB91C1C)), minimumSize: const Size.fromHeight(48)),
                label: Text(tr('رفض', 'Reject'), style: const TextStyle(fontWeight: FontWeight.w900)))),
            ]) : Container(
              alignment: Alignment.center, height: 44,
              decoration: BoxDecoration(color: const Color(0xFFF1F5F9), borderRadius: BorderRadius.circular(12)),
              child: Text(tr('لا تملك صلاحية الاعتماد على هذا الطلب', 'You cannot act on this request'),
                style: const TextStyle(color: Mgmt.slate, fontWeight: FontWeight.w700, fontSize: 12.5))),
          )),
        ]),
      ),
    );
  }
}

// ======================= الاعتماد السريع (طابور مراجعة) =======================
class _QuickReviewScreen extends StatefulWidget {
  const _QuickReviewScreen({required this.queue, required this.onDecide});
  final List<Map> queue;
  final Future<bool> Function(String model, int id, bool approve, String reason) onDecide;
  @override
  State<_QuickReviewScreen> createState() => _QuickReviewScreenState();
}

class _QuickReviewScreenState extends State<_QuickReviewScreen> {
  late final PageController _pc = PageController();
  int _i = 0;
  final Set<int> _done = {}; // indices decided

  Color _color(Map r) {
    final v = r['_color'];
    return v is int ? Color(v) : Mgmt.red;
  }

  Future<void> _act(int index, bool approve) async {
    final r = widget.queue[index];
    String reason = '';
    if (!approve) {
      final ctrl = TextEditingController();
      final res = await showDialog<String>(context: context, builder: (ctx) => AlertDialog(
        title: Text(tr('سبب الرفض', 'Rejection reason')),
        content: TextField(controller: ctrl, autofocus: true, maxLines: 3,
          decoration: InputDecoration(hintText: tr('سيصل لمُقدّم الطلب', 'Sent to requester'), border: const OutlineInputBorder())),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: Text(tr('إلغاء', 'Cancel'))),
          FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFFB91C1C)),
            onPressed: () => Navigator.pop(ctx, ctrl.text.trim()), child: Text(tr('رفض', 'Reject'))),
        ]));
      if (res == null) return;
      reason = res;
    }
    final ok = await widget.onDecide('${r['model']}', r['id'] as int, approve, reason);
    if (ok) {
      setState(() => _done.add(index));
      await Future.delayed(const Duration(milliseconds: 350));
      _next();
    }
  }

  void _next() {
    if (_i < widget.queue.length - 1) {
      _pc.nextPage(duration: const Duration(milliseconds: 280), curve: Curves.easeOut);
    } else if (_done.length >= widget.queue.length) {
      if (mounted) Navigator.pop(context);
    }
  }

  @override
  Widget build(BuildContext context) {
    final total = widget.queue.length;
    return Scaffold(
      backgroundColor: Mgmt.bg,
      appBar: AppBar(
        backgroundColor: Mgmt.deep, foregroundColor: Colors.white,
        title: Text(tr('الاعتماد السريع', 'Quick review'), style: const TextStyle(fontWeight: FontWeight.w900)),
        actions: [Padding(padding: const EdgeInsets.only(left: 14), child: Center(child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 4),
          decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(12)),
          child: Text('${_i + 1} / $total', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5)))))],
      ),
      body: Column(children: [
        LinearProgressIndicator(value: (_done.length) / total, minHeight: 4,
          backgroundColor: const Color(0xFFE2E8F0), color: const Color(0xFF15803D)),
        Expanded(child: PageView.builder(
          controller: _pc, itemCount: total,
          onPageChanged: (i) => setState(() => _i = i),
          itemBuilder: (_, i) => _QuickCard(
            rec: widget.queue[i], color: _color(widget.queue[i]), decided: _done.contains(i)),
        )),
        SafeArea(top: false, child: Padding(padding: const EdgeInsets.fromLTRB(14, 8, 14, 10), child: Row(children: [
          Expanded(child: FilledButton.icon(
            onPressed: _done.contains(_i) ? null : () => _act(_i, true),
            icon: const Icon(Icons.check_rounded),
            style: FilledButton.styleFrom(backgroundColor: const Color(0xFF15803D), minimumSize: const Size.fromHeight(50)),
            label: Text(tr('موافقة', 'Approve'), style: const TextStyle(fontWeight: FontWeight.w900)))),
          const SizedBox(width: 10),
          Expanded(child: OutlinedButton.icon(
            onPressed: _done.contains(_i) ? null : () => _act(_i, false),
            icon: const Icon(Icons.close_rounded, color: Color(0xFFB91C1C)),
            style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFB91C1C),
              side: const BorderSide(color: Color(0xFFB91C1C)), minimumSize: const Size.fromHeight(50)),
            label: Text(tr('رفض', 'Reject'), style: const TextStyle(fontWeight: FontWeight.w900)))),
          const SizedBox(width: 10),
          IconButton.filledTonal(onPressed: _next, icon: const Icon(Icons.skip_next_rounded),
            tooltip: tr('تخطٍّ', 'Skip')),
        ]))),
      ]),
    );
  }
}

class _QuickCard extends StatefulWidget {
  const _QuickCard({required this.rec, required this.color, required this.decided});
  final Map rec;
  final Color color;
  final bool decided;
  @override
  State<_QuickCard> createState() => _QuickCardState();
}

class _QuickCardState extends State<_QuickCard> with AutomaticKeepAliveClientMixin {
  Map<String, dynamic>? _d;
  @override
  bool get wantKeepAlive => true;
  @override
  void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api
        .approvalDetail('${widget.rec['model']}', widget.rec['id'] as int);
      if (mounted) setState(() => _d = d);
    } catch (_) {}
  }

  void _form() {
    final r = widget.rec;
    Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
      path: '/api/v1/approvals/report?model=${Uri.encodeQueryComponent('${r['model']}')}&res_id=${r['id']}',
      title: '${r['title'] ?? r['ref'] ?? ''}', fileName: 'request-${r['id']}.pdf')));
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final d = _d;
    final fields = ((d?['all_fields'] as List?) ?? (widget.rec['fields'] as List?) ?? const []).cast<List>();
    return ListView(padding: const EdgeInsets.all(14), children: [
      Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: widget.color, borderRadius: BorderRadius.circular(18)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${widget.rec['title'] ?? widget.rec['ref'] ?? ''}',
            style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 17)),
          const SizedBox(height: 4),
          Text('${widget.rec['ref'] ?? ''}${widget.rec['by'] != null && '${widget.rec['by']}'.isNotEmpty ? ' · 👤 ${widget.rec['by']}' : ''}',
            style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 12)),
          if (widget.decided) ...[
            const SizedBox(height: 10),
            Container(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
              child: Text('✓ ${tr('تمّت المعالجة', 'Processed')}',
                style: TextStyle(color: widget.color, fontWeight: FontWeight.w900, fontSize: 12.5))),
          ],
        ])),
      const SizedBox(height: 12),
      OutlinedButton.icon(onPressed: _form,
        icon: const Icon(Icons.picture_as_pdf_outlined, size: 18),
        style: OutlinedButton.styleFrom(foregroundColor: Mgmt.deep, minimumSize: const Size.fromHeight(46)),
        label: Text(tr('عرض النموذج (PDF)', 'View form (PDF)'), style: const TextStyle(fontWeight: FontWeight.w800))),
      const SizedBox(height: 12),
      if (d == null) const Padding(padding: EdgeInsets.all(20), child: Center(child: CircularProgressIndicator()))
      else Container(
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
        child: Column(children: [
          for (int i = 0; i < fields.length; i++)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 10),
              decoration: BoxDecoration(border: Border(bottom: BorderSide(
                color: i == fields.length - 1 ? Colors.transparent : const Color(0xFFEEF2F7)))),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                SizedBox(width: 120, child: Text('${fields[i][0]}',
                  style: const TextStyle(color: Mgmt.slate, fontWeight: FontWeight.w700, fontSize: 12))),
                const SizedBox(width: 8),
                Expanded(child: Text('${fields[i][1]}',
                  style: const TextStyle(color: Mgmt.ink, fontWeight: FontWeight.w700, fontSize: 12.5))),
              ]),
            ),
        ])),
    ]);
  }
}
