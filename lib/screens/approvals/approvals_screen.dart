import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import '../pdf_report_screen.dart';

/// مركز الموافقات — شاشة قائمة بذاتها تستهلك `/approvals/*` (بيانات حقيقية بالحالة
/// من `care.approval.center`): كل الطلبات المعلّقة لهذا المستخدم مجمّعةً حسب النوع،
/// مع بحث نصّي، تفاصيل كاملة + نموذج الطلب (PDF)، موافقة/رفض فوري، و«اعتماد سريع»
/// يمرّ على الطلبات واحدًا تلو الآخر.
class ApprovalsScreen extends StatefulWidget {
  const ApprovalsScreen({super.key});
  @override
  State<ApprovalsScreen> createState() => _ApprovalsScreenState();
}

// ===== هوية التطبيق (نفس ألوان شاشات الطلبات الأخرى) =====
const _navy = Color(0xFF0E3A5F);
const _ink = Color(0xFF182131);
const _slate = Color(0xFF5B677B);
const _bg = Color(0xFFF4F7FB);
const _green = Color(0xFF15803D);
const _red = Color(0xFFB91C1C);

/// لون شارة الأولوية: عاجل=أحمر، متوسط=كهرماني، عادي=رمادي.
Color _urgencyColor(String u) => switch (u) {
      'high' => _red,
      'mid' => const Color(0xFFD97706),
      _ => const Color(0xFF94A3B8),
    };
String _urgencyLabel(String u) => switch (u) {
      'high' => tr('عاجل', 'Urgent'),
      'mid' => tr('متوسط', 'Medium'),
      _ => tr('عادي', 'Normal'),
    };

/// يحوّل لون المجموعة النصّي (#RRGGBB) إلى [Color]، وإلا الأزرق الداكن.
Color _hexColor(dynamic raw) {
  final hex = '${raw ?? ''}'.replaceAll('#', '');
  if (hex.length == 6) {
    final v = int.tryParse('FF$hex', radix: 16);
    if (v != null) return Color(v);
  }
  return _navy;
}

class _ApprovalsScreenState extends State<ApprovalsScreen> {
  Map<String, dynamic>? _data;
  bool _loading = true;
  String? _err;
  String _query = '';
  final Set<String> _collapsed = {}; // مفاتيح المجموعات المطويّة
  final _searchCtrl = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _searchCtrl.dispose();
    super.dispose();
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
  Map get _user => (_data?['user'] as Map?) ?? const {};

  /// المجموعات بعد تطبيق البحث النصّي (title/ref/subject/by).
  List<Map> get _filteredGroups {
    final q = _query.trim().toLowerCase();
    if (q.isEmpty) return _groups;
    final out = <Map>[];
    for (final g in _groups) {
      final recs = ((g['records'] as List?) ?? const []).cast<Map>().where((r) {
        final hay = [r['title'], r['ref'], r['subject'], r['by'], r['badge']]
            .map((v) => '${v ?? ''}'.toLowerCase()).join(' ');
        return hay.contains(q);
      }).toList();
      if (recs.isNotEmpty) out.add({...g, 'records': recs});
    }
    return out;
  }

  // ------------------------- actions -------------------------
  void _snack(String msg, {bool bad = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(
      content: Text(msg), backgroundColor: bad ? _red : _green,
      behavior: SnackBarBehavior.floating, duration: const Duration(milliseconds: 1900)));
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
            style: FilledButton.styleFrom(backgroundColor: _red),
            onPressed: () => Navigator.pop(ctx, ctrl.text.trim()),
            child: Text(tr('رفض', 'Reject'))),
        ],
      ),
    );
  }

  Future<void> _reject(String model, int id) async {
    final reason = await _askReason();
    if (reason == null) return; // أُلغي
    await _decide(model, id, false, reason: reason);
  }

  Future<void> _openForm(Map rec) async {
    final api = context.read<AuthProvider>().api;
    final url = await api.approvalsReportUrl('${rec['model']}', rec['id'] as int);
    if (!mounted) return;
    Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
      url: url,
      title: '${rec['title'] ?? rec['ref'] ?? tr('النموذج', 'Form')}',
      fileName: 'request-${rec['id']}.pdf',
    )));
  }

  Future<void> _openDetail(Map rec, Color color) async {
    await showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => _DetailSheet(
        model: '${rec['model']}', resId: rec['id'] as int, color: color,
        onApprove: () async {
          final ok = await _decide('${rec['model']}', rec['id'] as int, true);
          if (ok && mounted) Navigator.pop(context);
        },
        onReject: () async {
          Navigator.pop(context);
          await _reject('${rec['model']}', rec['id'] as int);
        },
        onForm: () => _openForm(rec),
      ),
    );
  }

  Future<void> _startQuick() async {
    final queue = <Map>[];
    for (final g in _groups) {
      final color = _hexColor(g['color']);
      for (final r in ((g['records'] as List?) ?? const []).cast<Map>()) {
        queue.add({...r, '_color': color.toARGB32()});
      }
    }
    if (queue.isEmpty) { _snack(tr('لا طلبات للمراجعة', 'Nothing to review')); return; }
    await Navigator.push(context, MaterialPageRoute(builder: (_) => _QuickReviewScreen(
      queue: queue,
      onDecide: (model, id, approve, reason) => _decide(model, id, approve, reason: reason),
    )));
    _load(); // إعادة المزامنة بعد الطابور
  }

  // ------------------------- build -------------------------
  @override
  Widget build(BuildContext context) {
    final groups = _filteredGroups;
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _navy, foregroundColor: Colors.white, elevation: 0,
        title: Row(children: [
          Text(tr('مركز الموافقات', 'Approval Center'),
              style: const TextStyle(fontWeight: FontWeight.w900)),
          const SizedBox(width: 8),
          if (_total > 0) Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 2),
            decoration: BoxDecoration(color: _red, borderRadius: BorderRadius.circular(12)),
            child: Text('$_total', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5))),
        ]),
        actions: [IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: _load)],
      ),
      floatingActionButton: (!_loading && _err == null && _total > 0)
          ? FloatingActionButton.extended(
              backgroundColor: _green,
              icon: const Icon(Icons.bolt_rounded),
              onPressed: _startQuick,
              label: Text(tr('اعتماد سريع', 'Quick review'),
                  style: const TextStyle(fontWeight: FontWeight.w900)))
          : null,
      body: _loading ? const Center(child: CircularProgressIndicator())
          : _err != null ? _errorView()
          : _total == 0 ? _emptyView()
          : Column(children: [
              _userStrip(),
              _searchBar(),
              Expanded(child: RefreshIndicator(
                onRefresh: _load,
                child: groups.isEmpty
                    ? ListView(children: [const SizedBox(height: 120), _noMatch()])
                    : ListView(
                        padding: const EdgeInsets.fromLTRB(0, 4, 0, 96),
                        children: [for (final g in groups) _group(g)],
                      ),
              )),
            ]),
    );
  }

  Widget _userStrip() {
    final name = '${_user['name'] ?? ''}';
    final initials = '${_user['initials'] ?? '؟'}';
    return Container(
      color: _navy,
      padding: const EdgeInsets.fromLTRB(16, 0, 16, 14),
      child: Row(children: [
        CircleAvatar(radius: 18, backgroundColor: Colors.white,
            child: Text(initials, style: const TextStyle(color: _navy, fontWeight: FontWeight.w900, fontSize: 14))),
        const SizedBox(width: 11),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(name, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14.5)),
          Text(tr('لديك $_total طلبًا بانتظار اعتمادك', 'You have $_total requests awaiting you'),
              style: TextStyle(color: Colors.white.withValues(alpha: 0.82), fontSize: 11.5)),
        ])),
      ]),
    );
  }

  Widget _searchBar() => Container(
        color: Colors.white,
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        child: TextField(
          controller: _searchCtrl,
          onChanged: (v) => setState(() => _query = v),
          textInputAction: TextInputAction.search,
          decoration: InputDecoration(
            isDense: true,
            hintText: tr('ابحث بالعنوان أو الرقم أو البادج أو مقدّم الطلب…', 'Search title, ref, badge or requester…'),
            prefixIcon: const Icon(Icons.search_rounded, size: 20),
            suffixIcon: _query.isEmpty ? null : IconButton(
              icon: const Icon(Icons.close_rounded, size: 18),
              onPressed: () { _searchCtrl.clear(); setState(() => _query = ''); }),
            filled: true, fillColor: _bg,
            contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
          ),
        ),
      );

  Widget _group(Map g) {
    final key = '${g['key']}';
    final color = _hexColor(g['color']);
    final recs = ((g['records'] as List?) ?? const []).cast<Map>();
    // عند البحث تبقى كل المجموعات مفتوحة؛ وإلا نحترم الطيّ اليدوي.
    final open = _query.trim().isNotEmpty || !_collapsed.contains(key);
    return Column(children: [
      // رأس المجموعة (قابل للطيّ/التوسعة)
      Material(color: Colors.transparent, child: InkWell(
        onTap: () => setState(() {
          if (_collapsed.contains(key)) { _collapsed.remove(key); } else { _collapsed.add(key); }
        }),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(14, 14, 14, 6),
          child: Row(children: [
            Text('${g['icon']}', style: const TextStyle(fontSize: 17)),
            const SizedBox(width: 8),
            Expanded(child: Text('${g['module']}',
                maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w900, color: _ink, fontSize: 14.5))),
            Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 1),
              decoration: BoxDecoration(color: color.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(10)),
              child: Text('${recs.length}', style: TextStyle(color: color, fontWeight: FontWeight.w900, fontSize: 11.5))),
            const SizedBox(width: 4),
            Icon(open ? Icons.keyboard_arrow_up_rounded : Icons.keyboard_arrow_down_rounded,
                color: _slate),
          ]),
        ),
      )),
      if (open) ...recs.map((r) => _card(r, color)),
    ]);
  }

  Widget _card(Map r, Color color) {
    final fields = ((r['fields'] as List?) ?? const []).cast<List>();
    final u = '${r['urgency'] ?? 'low'}';
    final uc = _urgencyColor(u);
    final by = '${r['by'] ?? ''}';
    final byRole = '${r['by_role'] ?? ''}';
    final subject = '${r['subject'] ?? ''}';
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 0, 12, 9),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
        boxShadow: const [BoxShadow(color: Color(0x0F000000), blurRadius: 10, offset: Offset(0, 3))]),
      child: Material(color: Colors.transparent, child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => _openDetail(r, color),
        child: Padding(padding: const EdgeInsets.fromLTRB(13, 12, 13, 10),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(width: 40, height: 40, alignment: Alignment.center,
              decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(11)),
              child: Text('${r['initials'] ?? '؟'}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900))),
            const SizedBox(width: 11),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${r['title'] ?? r['ref'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5, color: _ink)),
              const SizedBox(height: 3),
              Wrap(spacing: 6, runSpacing: 3, crossAxisAlignment: WrapCrossAlignment.center, children: [
                Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                  decoration: BoxDecoration(color: const Color(0xFFF1F5F9), borderRadius: BorderRadius.circular(5)),
                  child: Text('${r['ref'] ?? ''}', style: const TextStyle(fontSize: 10.5, color: _slate))),
                // شارة الأولوية
                Container(padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 1),
                  decoration: BoxDecoration(color: uc.withValues(alpha: 0.13), borderRadius: BorderRadius.circular(5)),
                  child: Text(_urgencyLabel(u), style: TextStyle(fontSize: 10, color: uc, fontWeight: FontWeight.w800))),
              ]),
            ])),
            if ('${r['date'] ?? ''}'.isNotEmpty)
              Text('${r['date']}', style: const TextStyle(fontSize: 10.5, color: _slate)),
          ]),
          if (by.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 8),
            child: Text('👤 $by${byRole.isNotEmpty ? ' ($byRole)' : ''}',
              maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 11.5, color: _slate, fontWeight: FontWeight.w600))),
          if (subject.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 3),
            child: Text(subject, maxLines: 2, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontSize: 12, color: _ink))),
          if (fields.isNotEmpty) ...[
            const SizedBox(height: 9),
            Wrap(spacing: 6, runSpacing: 5, children: fields.take(2).map((f) => Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(color: _bg, borderRadius: BorderRadius.circular(8),
                border: Border.all(color: const Color(0xFFEEF2F7))),
              child: Text('${f[0]}: ${f[1]}', style: const TextStyle(fontSize: 10.5, color: _ink)))).toList()),
          ],
          const SizedBox(height: 10),
          Row(children: [
            Expanded(child: _actBtn(tr('اعتماد', 'Approve'), Icons.check_rounded, _green,
              () => _decide('${r['model']}', r['id'] as int, true))),
            const SizedBox(width: 8),
            Expanded(child: _actBtn(tr('رفض', 'Reject'), Icons.close_rounded, _red,
              () => _reject('${r['model']}', r['id'] as int))),
            const SizedBox(width: 8),
            _actBtn(tr('عرض', 'Open'), Icons.open_in_full_rounded, _navy,
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

  Widget _errorView() => Center(child: Padding(padding: const EdgeInsets.all(28), child: Column(
    mainAxisSize: MainAxisSize.min, children: [
      const Icon(Icons.cloud_off_rounded, size: 48, color: _slate),
      const SizedBox(height: 12),
      Text(tr('تعذّر التحميل', 'Could not load'), style: const TextStyle(fontWeight: FontWeight.w900)),
      const SizedBox(height: 6),
      Text('$_err', textAlign: TextAlign.center, style: const TextStyle(color: _slate, fontSize: 12)),
      const SizedBox(height: 16),
      FilledButton.icon(onPressed: _load, icon: const Icon(Icons.refresh_rounded), label: Text(tr('إعادة المحاولة', 'Retry'))),
    ])));

  Widget _emptyView() => Center(child: Padding(padding: const EdgeInsets.all(28), child: Column(
    mainAxisSize: MainAxisSize.min, children: [
      const Text('✅', style: TextStyle(fontSize: 54)),
      const SizedBox(height: 10),
      Text(tr('لا طلبات بانتظار اعتمادك', 'No requests awaiting you'),
          style: const TextStyle(fontWeight: FontWeight.w800, color: _ink)),
      const SizedBox(height: 4),
      Text(tr('كل شيء مُعتمَد — راجع لاحقًا', 'All clear — check back later'),
          style: const TextStyle(color: _slate, fontSize: 12.5)),
    ])));

  Widget _noMatch() => Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
    const Icon(Icons.search_off_rounded, size: 48, color: _slate),
    const SizedBox(height: 10),
    Text(tr('لا نتائج مطابقة للبحث', 'No matching results'),
        style: const TextStyle(fontWeight: FontWeight.w800, color: _ink)),
  ]));
}

// =========================== تفاصيل الطلب (bottom sheet) ===========================
class _DetailSheet extends StatefulWidget {
  const _DetailSheet({required this.model, required this.resId, required this.color,
    required this.onApprove, required this.onReject, required this.onForm});
  final String model;
  final int resId;
  final Color color;
  final Future<void> Function() onApprove;
  final Future<void> Function() onReject;
  final Future<void> Function() onForm;
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

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final fields = ((d?['all_fields'] as List?) ?? const []).cast<List>();
    final canAct = (d?['can_act'] ?? false) == true;
    return DraggableScrollableSheet(
      initialChildSize: 0.8, minChildSize: 0.5, maxChildSize: 0.96, expand: false,
      builder: (_, ctrl) => Container(
        decoration: const BoxDecoration(color: _bg, borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
        child: Column(children: [
          // رأس الورقة
          Container(
            padding: const EdgeInsets.fromLTRB(18, 10, 10, 14),
            decoration: BoxDecoration(color: widget.color, borderRadius: const BorderRadius.vertical(top: Radius.circular(22))),
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
            : _err != null ? Center(child: Padding(padding: const EdgeInsets.all(24),
                child: Text('$_err', textAlign: TextAlign.center, style: const TextStyle(color: _slate))))
            : ListView(controller: ctrl, padding: const EdgeInsets.fromLTRB(14, 14, 14, 14), children: [
                OutlinedButton.icon(onPressed: widget.onForm,
                  icon: const Icon(Icons.picture_as_pdf_outlined, size: 18),
                  style: OutlinedButton.styleFrom(foregroundColor: _navy, minimumSize: const Size.fromHeight(44)),
                  label: Text(tr('عرض النموذج (PDF)', 'View form (PDF)'),
                    style: const TextStyle(fontWeight: FontWeight.w800))),
                const SizedBox(height: 12),
                Container(
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
                  child: Column(children: [
                    for (int i = 0; i < fields.length; i++)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 10),
                        decoration: BoxDecoration(border: Border(bottom: BorderSide(
                          color: i == fields.length - 1 ? Colors.transparent : const Color(0xFFEEF2F7)))),
                        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          SizedBox(width: 120, child: Text('${fields[i][0]}',
                            style: const TextStyle(color: _slate, fontWeight: FontWeight.w700, fontSize: 12))),
                          const SizedBox(width: 8),
                          Expanded(child: Text('${fields[i][1]}',
                            style: const TextStyle(color: _ink, fontWeight: FontWeight.w700, fontSize: 12.5))),
                        ]),
                      ),
                  ]),
                ),
              ])),
          // شريط الإجراء
          SafeArea(top: false, child: Padding(
            padding: const EdgeInsets.fromLTRB(14, 8, 14, 10),
            child: canAct ? Row(children: [
              Expanded(child: FilledButton.icon(
                onPressed: _busy ? null : () async { setState(() => _busy = true); await widget.onApprove(); },
                icon: const Icon(Icons.check_rounded),
                style: FilledButton.styleFrom(backgroundColor: _green, minimumSize: const Size.fromHeight(48)),
                label: Text(tr('اعتماد', 'Approve'), style: const TextStyle(fontWeight: FontWeight.w900)))),
              const SizedBox(width: 10),
              Expanded(child: OutlinedButton.icon(
                onPressed: _busy ? null : widget.onReject,
                icon: const Icon(Icons.close_rounded, color: _red),
                style: OutlinedButton.styleFrom(foregroundColor: _red,
                  side: const BorderSide(color: _red), minimumSize: const Size.fromHeight(48)),
                label: Text(tr('رفض', 'Reject'), style: const TextStyle(fontWeight: FontWeight.w900)))),
            ]) : Container(
              alignment: Alignment.center, height: 44,
              decoration: BoxDecoration(color: const Color(0xFFF1F5F9), borderRadius: BorderRadius.circular(12)),
              child: Text(tr('لا تملك صلاحية الاعتماد على هذا الطلب', 'You cannot act on this request'),
                style: const TextStyle(color: _slate, fontWeight: FontWeight.w700, fontSize: 12.5))),
          )),
        ]),
      ),
    );
  }
}

// =========================== الاعتماد السريع (طابور مراجعة) ===========================
class _QuickReviewScreen extends StatefulWidget {
  const _QuickReviewScreen({required this.queue, required this.onDecide});
  final List<Map> queue;
  final Future<bool> Function(String model, int id, bool approve, String reason) onDecide;
  @override
  State<_QuickReviewScreen> createState() => _QuickReviewScreenState();
}

class _QuickReviewScreenState extends State<_QuickReviewScreen> {
  final PageController _pc = PageController();
  int _i = 0;
  final Set<int> _done = {}; // الفهارس التي اتُّخذ فيها قرار

  @override
  void dispose() { _pc.dispose(); super.dispose(); }

  Color _color(Map r) {
    final v = r['_color'];
    return v is int ? Color(v) : _navy;
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
          FilledButton(style: FilledButton.styleFrom(backgroundColor: _red),
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

  void _prev() {
    if (_i > 0) _pc.previousPage(duration: const Duration(milliseconds: 280), curve: Curves.easeOut);
  }

  @override
  Widget build(BuildContext context) {
    final total = widget.queue.length;
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _navy, foregroundColor: Colors.white,
        title: Text(tr('الاعتماد السريع', 'Quick review'), style: const TextStyle(fontWeight: FontWeight.w900)),
        actions: [Padding(padding: const EdgeInsets.symmetric(horizontal: 14), child: Center(child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 4),
          decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(12)),
          child: Text('${_i + 1} / $total', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5)))))],
      ),
      body: Column(children: [
        LinearProgressIndicator(value: _done.length / total, minHeight: 4,
          backgroundColor: const Color(0xFFE2E8F0), color: _green),
        Expanded(child: PageView.builder(
          controller: _pc, itemCount: total,
          onPageChanged: (i) => setState(() => _i = i),
          itemBuilder: (_, i) => _QuickCard(
            rec: widget.queue[i], color: _color(widget.queue[i]), decided: _done.contains(i)),
        )),
        SafeArea(top: false, child: Padding(padding: const EdgeInsets.fromLTRB(14, 8, 14, 10), child: Row(children: [
          IconButton.filledTonal(onPressed: _i == 0 ? null : _prev, icon: const Icon(Icons.skip_previous_rounded),
            tooltip: tr('السابق', 'Previous')),
          const SizedBox(width: 6),
          Expanded(child: FilledButton.icon(
            onPressed: _done.contains(_i) ? null : () => _act(_i, true),
            icon: const Icon(Icons.check_rounded),
            style: FilledButton.styleFrom(backgroundColor: _green, minimumSize: const Size.fromHeight(50)),
            label: Text(tr('اعتماد', 'Approve'), style: const TextStyle(fontWeight: FontWeight.w900)))),
          const SizedBox(width: 8),
          Expanded(child: OutlinedButton.icon(
            onPressed: _done.contains(_i) ? null : () => _act(_i, false),
            icon: const Icon(Icons.close_rounded, color: _red),
            style: OutlinedButton.styleFrom(foregroundColor: _red,
              side: const BorderSide(color: _red), minimumSize: const Size.fromHeight(50)),
            label: Text(tr('رفض', 'Reject'), style: const TextStyle(fontWeight: FontWeight.w900)))),
          const SizedBox(width: 6),
          IconButton.filledTonal(onPressed: _next, icon: const Icon(Icons.skip_next_rounded),
            tooltip: tr('التالي', 'Next')),
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

  Future<void> _form() async {
    final r = widget.rec;
    final url = await context.read<AuthProvider>().api
      .approvalsReportUrl('${r['model']}', r['id'] as int);
    if (!mounted) return;
    Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
      url: url, title: '${r['title'] ?? r['ref'] ?? ''}', fileName: 'request-${r['id']}.pdf')));
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final d = _d;
    final fields = ((d?['all_fields'] as List?) ?? (widget.rec['fields'] as List?) ?? const []).cast<List>();
    final u = '${widget.rec['urgency'] ?? 'low'}';
    return ListView(padding: const EdgeInsets.all(14), children: [
      Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: widget.color, borderRadius: BorderRadius.circular(18)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('${widget.rec['title'] ?? widget.rec['ref'] ?? ''}',
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 17))),
            Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
              decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(20)),
              child: Text(_urgencyLabel(u), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 11))),
          ]),
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
        style: OutlinedButton.styleFrom(foregroundColor: _navy, minimumSize: const Size.fromHeight(46)),
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
                  style: const TextStyle(color: _slate, fontWeight: FontWeight.w700, fontSize: 12))),
                const SizedBox(width: 8),
                Expanded(child: Text('${fields[i][1]}',
                  style: const TextStyle(color: _ink, fontWeight: FontWeight.w700, fontSize: 12.5))),
              ]),
            ),
        ])),
    ]);
  }
}
