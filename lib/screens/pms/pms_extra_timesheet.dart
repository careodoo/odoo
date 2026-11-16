// شاشة «التايم شيت الإضافي» (care.extra.timesheet) — نظير قسم xts في بوابة /my/pm/x:
// كشوف العمل الإضافي الواردة للمشروع، تعبئة تلقائية من تكليفات العمل الإضافي، تعديل ساعات
// كل عامل، احتساب المستحقّ، ثم إرسال/اعتماد وطباعة التقرير المعتمد.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import '../pdf_report_screen.dart';
import 'pms_shell.dart' show Pms;

class ExtraTimesheetScreen extends StatefulWidget {
  const ExtraTimesheetScreen({super.key, required this.projectId, required this.label});
  final int projectId;
  final String label;

  @override
  State<ExtraTimesheetScreen> createState() => _ExtraTimesheetScreenState();
}

class _ExtraTimesheetScreenState extends State<ExtraTimesheetScreen> {
  Future<Map<String, dynamic>>? _f;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _f = context.read<AuthProvider>().api.pmsExtraTimesheets(widget.projectId);
  }

  Future<void> _refresh() async {
    setState(_load);
    await _f;
  }

  Color _stateColor(String s) {
    switch (s) {
      case 'approved':
        return Pms.green;
      case 'submitted':
        return Pms.amber;
      case 'cancelled':
        return Pms.red;
      default:
        return Pms.slate;
    }
  }

  Future<void> _create() async {
    final now = DateTime.now();
    int m = now.month, y = now.year;
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => StatefulBuilder(
        builder: (ctx, setD) => AlertDialog(
          title: Text(tr('إنشاء كشف عمل إضافي', 'New extra timesheet')),
          content: Column(mainAxisSize: MainAxisSize.min, children: [
            Text(tr('يُنشأ للمشروع الحالي ويُعبّأ تلقائيًّا بالعمّال الواردين في الفترة.',
                'Created for the current project, auto-filled with incoming workers.'),
                style: const TextStyle(fontSize: 12.5, color: Pms.slate)),
            const SizedBox(height: 14),
            Row(children: [
              Expanded(
                child: DropdownButtonFormField<int>(
                  value: m,
                  decoration: InputDecoration(labelText: tr('الشهر', 'Month'), border: const OutlineInputBorder()),
                  items: List.generate(12, (i) => DropdownMenuItem(value: i + 1, child: Text(_MONTHS[i]))),
                  onChanged: (v) => setD(() => m = v ?? m),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: DropdownButtonFormField<int>(
                  value: y,
                  decoration: InputDecoration(labelText: tr('السنة', 'Year'), border: const OutlineInputBorder()),
                  items: [now.year - 1, now.year, now.year + 1]
                      .map((e) => DropdownMenuItem(value: e, child: Text('$e'))).toList(),
                  onChanged: (v) => setD(() => y = v ?? y),
                ),
              ),
            ]),
          ]),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('إلغاء', 'Cancel'))),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(tr('إنشاء', 'Create'))),
          ],
        ),
      ),
    );
    if (ok != true || !mounted) return;
    final from = '$y-${m.toString().padLeft(2, '0')}-01';
    final lastDay = DateTime(y, m + 1, 0).day;
    final to = '$y-${m.toString().padLeft(2, '0')}-${lastDay.toString().padLeft(2, '0')}';
    try {
      final r = await context.read<AuthProvider>().api.pmsExtraTimesheetNew(widget.projectId, from, to);
      if (!mounted) return;
      final tid = r['id'] as int?;
      if (tid != null) {
        await Navigator.push(context,
            MaterialPageRoute(builder: (_) => ExtraTimesheetSheetScreen(tid: tid, projectId: widget.projectId)));
        _refresh();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Pms.bg,
      appBar: AppBar(title: Text(tr('التايم شيت الإضافي', 'Extra timesheet'))),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _create,
        backgroundColor: Pms.ink,
        icon: const Icon(Icons.add),
        label: Text(tr('كشف جديد', 'New sheet')),
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<Map<String, dynamic>>(
          future: _f,
          builder: (_, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: Padding(padding: EdgeInsets.all(40), child: CircularProgressIndicator()));
            }
            if (snap.hasError) {
              return ListView(children: [Padding(padding: const EdgeInsets.all(30), child: Text('${snap.error}', textAlign: TextAlign.center, style: const TextStyle(color: Pms.slate)))]);
            }
            final rows = (snap.data?['rows'] as List?) ?? const [];
            if (rows.isEmpty) {
              return ListView(children: [Padding(padding: const EdgeInsets.all(50), child: Center(child: Text(tr('لا كشوف بعد — أنشئ كشفًا جديدًا.', 'No sheets yet — create one.'), style: const TextStyle(color: Pms.slate))))]);
            }
            return ListView.builder(
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 90),
              itemCount: rows.length,
              itemBuilder: (_, i) => _card(rows[i] as Map),
            );
          },
        ),
      ),
    );
  }

  Widget _card(Map r) {
    final sc = _stateColor('${r['state']}');
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: () async {
          await Navigator.push(context,
              MaterialPageRoute(builder: (_) => ExtraTimesheetSheetScreen(tid: r['id'] as int, projectId: widget.projectId)));
          _refresh();
        },
        child: Padding(
          padding: const EdgeInsets.all(13),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text('${r['name']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: Pms.ink))),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                decoration: BoxDecoration(color: sc.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
                child: Text('${r['state_label']}', style: TextStyle(color: sc, fontWeight: FontWeight.w800, fontSize: 11.5)),
              ),
            ]),
            const SizedBox(height: 7),
            Text('${r['period']}', style: const TextStyle(fontWeight: FontWeight.w700, color: Pms.ink)),
            const SizedBox(height: 9),
            Row(children: [
              _pill(Icons.groups_rounded, '${r['workers']} ${tr('عامل', 'workers')}'),
              const SizedBox(width: 8),
              _pill(Icons.schedule_rounded, '${r['total_hours']} ${tr('ساعة', 'h')}'),
              const SizedBox(width: 8),
              _pill(Icons.payments_rounded, '${r['total_amount']} ${r['currency']}'),
            ]),
          ]),
        ),
      ),
    );
  }

  Widget _pill(IconData ic, String t) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
        decoration: BoxDecoration(color: Pms.bg, borderRadius: BorderRadius.circular(8)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(ic, size: 14, color: Pms.slate),
          const SizedBox(width: 5),
          Text(t, style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: Pms.ink)),
        ]),
      );
}

const _MONTHS = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو', 'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر'];

// ============ شاشة تفصيل الكشف ============
class ExtraTimesheetSheetScreen extends StatefulWidget {
  const ExtraTimesheetSheetScreen({super.key, required this.tid, required this.projectId});
  final int tid;
  final int projectId;

  @override
  State<ExtraTimesheetSheetScreen> createState() => _ExtraTimesheetSheetScreenState();
}

class _ExtraTimesheetSheetScreenState extends State<ExtraTimesheetSheetScreen> {
  Future<Map<String, dynamic>>? _f;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _f = context.read<AuthProvider>().api.pmsExtraTimesheet(widget.tid);
  }

  Future<void> _reload() async {
    setState(_load);
    await _f;
  }

  Future<void> _act(String act, String confirm) async {
    if (confirm.isNotEmpty) {
      final ok = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          content: Text(confirm),
          actions: [
            TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('إلغاء', 'Cancel'))),
            FilledButton(onPressed: () => Navigator.pop(ctx, true), child: Text(tr('متابعة', 'Continue'))),
          ],
        ),
      );
      if (ok != true) return;
    }
    setState(() => _busy = true);
    try {
      if (act == 'refresh') {
        await context.read<AuthProvider>().api.pmsExtraTimesheetRefresh(widget.tid);
      } else {
        await context.read<AuthProvider>().api.pmsExtraTimesheetAction(widget.tid, act);
      }
      await _reload();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _editHours(Map l) async {
    final ctl = TextEditingController(text: '${l['hours']}');
    final v = await showDialog<double>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('${l['name']}'),
        content: TextField(
          controller: ctl,
          keyboardType: const TextInputType.numberWithOptions(decimal: true),
          decoration: InputDecoration(labelText: tr('عدد الساعات', 'Hours'), border: const OutlineInputBorder()),
          autofocus: true,
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx), child: Text(tr('إلغاء', 'Cancel'))),
          FilledButton(
              onPressed: () => Navigator.pop(ctx, double.tryParse(ctl.text.trim()) ?? 0.0),
              child: Text(tr('حفظ', 'Save'))),
        ],
      ),
    );
    if (v == null || !mounted) return;
    try {
      await context.read<AuthProvider>().api.pmsExtraTimesheetHours(widget.tid, l['lid'] as int, v);
      await _reload();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Pms.bg,
      appBar: AppBar(title: Text(tr('كشف عمل إضافي', 'Extra sheet'))),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _f,
        builder: (_, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Center(child: Padding(padding: const EdgeInsets.all(30), child: Text('${snap.error}', textAlign: TextAlign.center, style: const TextStyle(color: Pms.slate))));
          }
          final d = snap.data ?? const {};
          final lines = (d['lines'] as List?) ?? const [];
          final canEdit = d['can_edit'] == true;
          final cur = '${d['currency'] ?? 'KWD'}';
          return ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
            // الترويسة
            Card(
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    Expanded(child: Text('${d['name']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: Pms.ink))),
                    Text('${d['state_label']}', style: const TextStyle(fontWeight: FontWeight.w800, color: Pms.ink)),
                  ]),
                  const SizedBox(height: 4),
                  Text('${d['period']} · ${d['project']}', style: const TextStyle(color: Pms.slate, fontSize: 12.5)),
                  const SizedBox(height: 12),
                  Row(children: [
                    _stat('${d['workers'] ?? 0}', tr('عامل', 'Workers')),
                    _stat('${d['total_hours'] ?? 0}', tr('ساعات', 'Hours')),
                    _stat('${d['total_amount'] ?? 0} $cur', tr('المستحق', 'Due')),
                  ]),
                ]),
              ),
            ),
            const SizedBox(height: 10),
            // الأزرار
            Wrap(spacing: 8, runSpacing: 8, children: [
              if (canEdit) OutlinedButton.icon(onPressed: _busy ? null : () => _act('refresh', ''), icon: const Icon(Icons.refresh, size: 18), label: Text(tr('تحديث العمّال', 'Refresh'))),
              if (d['can_submit'] == true) FilledButton.icon(onPressed: _busy ? null : () => _act('submit', ''), icon: const Icon(Icons.send, size: 18), label: Text(tr('إرسال للاعتماد', 'Submit'))),
              if (d['can_approve'] == true) FilledButton.icon(style: FilledButton.styleFrom(backgroundColor: Pms.green), onPressed: _busy ? null : () => _act('approve', tr('اعتماد الكشف؟ لا يُعدَّل بعد الاعتماد.', 'Approve? Cannot edit after.')), icon: const Icon(Icons.check, size: 18), label: Text(tr('اعتماد', 'Approve'))),
              OutlinedButton.icon(
                onPressed: () async {
                  final api = context.read<AuthProvider>().api;
                  final token = await api.token;
                  final url = '${api.pmsExtraTimesheetPrintUrl(widget.tid)}?token=${Uri.encodeQueryComponent(token ?? '')}';
                  if (!mounted) return;
                  Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(url: url, title: tr('كشف العمل الإضافي', 'Extra timesheet'))));
                },
                icon: const Icon(Icons.print, size: 18),
                label: Text(tr('طباعة', 'Print')),
              ),
            ]),
            const SizedBox(height: 12),
            Text(tr('العمّال', 'Workers'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: Pms.ink)),
            const SizedBox(height: 6),
            if (lines.isEmpty)
              Padding(padding: const EdgeInsets.all(20), child: Center(child: Text(tr('لا عمّال عمل إضافي واردون.', 'No incoming extra-work workers.'), style: const TextStyle(color: Pms.slate)))),
            ...lines.map((e) => _lineCard(e as Map, canEdit, cur)),
          ]);
        },
      ),
    );
  }

  Widget _stat(String v, String l) => Expanded(
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(v, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: Pms.ink)),
          Text(l, style: const TextStyle(fontSize: 11, color: Pms.slate, fontWeight: FontWeight.w600)),
        ]),
      );

  Widget _lineCard(Map l, bool canEdit, String cur) {
    final hourly = '${l['comp_type']}' == 'hourly';
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: Padding(
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        child: Row(children: [
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${l['name']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Pms.ink)),
              Text('#${l['badge']} · ${l['home_dept']}', style: const TextStyle(fontSize: 10.5, color: Pms.slate)),
              const SizedBox(height: 2),
              Row(children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                  decoration: BoxDecoration(color: (hourly ? Pms.ink : Pms.slate).withValues(alpha: 0.12), borderRadius: BorderRadius.circular(10)),
                  child: Text('${l['comp_label']}', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: hourly ? Pms.ink : Pms.slate)),
                ),
                if (hourly) ...[
                  const SizedBox(width: 6),
                  Text('${l['rate']} $cur/${tr('س', 'h')}', style: const TextStyle(fontSize: 10.5, color: Pms.slate)),
                ],
              ]),
            ]),
          ),
          const SizedBox(width: 8),
          // الساعات (قابلة للتعديل للكشف غير المعتمد وللنوع بالساعة)
          InkWell(
            onTap: (canEdit && hourly) ? () => _editHours(l) : null,
            borderRadius: BorderRadius.circular(8),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                border: Border.all(color: (canEdit && hourly) ? Pms.ink : const Color(0xFFE5E7EB)),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Column(children: [
                Text(hourly ? '${l['hours']}' : '—', style: const TextStyle(fontWeight: FontWeight.w900, color: Pms.ink)),
                Text(tr('ساعة', 'hrs'), style: const TextStyle(fontSize: 9, color: Pms.slate)),
              ]),
            ),
          ),
          const SizedBox(width: 10),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            Text('${l['amount']}', style: const TextStyle(fontWeight: FontWeight.w900, color: Pms.green, fontSize: 14)),
            Text(cur, style: const TextStyle(fontSize: 9, color: Pms.slate)),
          ]),
        ]),
      ),
    );
  }
}
