// «Incoming extra work» screen — a project-internal icon: workers from other projects
// working extra on the manager's project, with a stop/end request (approved by HR)
// and form printing. Exactly the counterpart of /my/pm/p/<id>/extra-work in the portal.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import '../pdf_report_screen.dart';
import 'pms_shell.dart' show Pms;

class ExtraWorkScreen extends StatefulWidget {
  const ExtraWorkScreen({super.key, required this.projectId, required this.label});
  final int projectId;
  final String label;

  @override
  State<ExtraWorkScreen> createState() => _ExtraWorkScreenState();
}

class _ExtraWorkScreenState extends State<ExtraWorkScreen> {
  Future<Map<String, dynamic>>? _f;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _f = context.read<AuthProvider>().api.pmsExtraWork(widget.projectId);
  }

  Future<void> _refresh() async {
    setState(_load);
    await _f;
  }

  Color _stateColor(String s) {
    switch (s) {
      case 'active':
        return Pms.green;
      case 'ended':
        return Pms.red;
      default:
        return Pms.amber; // paused / pause_requested / end_requested
    }
  }

  // Stop/end request with an optional reason, then HR approval
  Future<void> _stop(Map r, String kind) async {
    final reasonCtl = TextEditingController();
    final isPause = kind == 'pause';
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => Padding(
        padding: EdgeInsets.only(
            left: 16, right: 16, top: 18,
            bottom: 18 + MediaQuery.of(ctx).viewInsets.bottom),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Text(isPause ? tr('طلب إيقاف التكليف', 'Request pause') : tr('طلب إنهاء التكليف', 'Request end'),
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: Pms.ink)),
          const SizedBox(height: 4),
          Text('${r['employee']} · ${r['name']}', style: const TextStyle(color: Pms.slate, fontSize: 13)),
          const SizedBox(height: 14),
          TextField(
            controller: reasonCtl,
            maxLines: 2,
            decoration: InputDecoration(
              hintText: tr('السبب (اختياري)…', 'Reason (optional)…'),
              filled: true, fillColor: Pms.bg,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            ),
          ),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(color: Pms.amber.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(10)),
            child: Row(children: [
              const Icon(Icons.info_outline_rounded, size: 18, color: Pms.amber),
              const SizedBox(width: 8),
              Expanded(child: Text(
                tr('يُرسَل الطلب لاعتماد الموارد البشرية قبل تطبيقه.',
                   'Sent to HR for approval before it takes effect.'),
                style: const TextStyle(fontSize: 12.5, color: Pms.ink))),
            ]),
          ),
          const SizedBox(height: 14),
          Row(children: [
            Expanded(child: OutlinedButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: Text(tr('إلغاء', 'Cancel')))),
            const SizedBox(width: 10),
            Expanded(child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                    backgroundColor: isPause ? Pms.amber : Pms.red, foregroundColor: Colors.white),
                onPressed: () => Navigator.pop(ctx, true),
                child: Text(isPause ? tr('إرسال طلب الإيقاف', 'Send pause request')
                                    : tr('إرسال طلب الإنهاء', 'Send end request')))),
          ]),
        ]),
      ),
    );
    if (ok != true || !mounted) return;
    try {
      final res = await context.read<AuthProvider>().api
          .pmsExtraWorkStop(r['id'] as int, kind, reason: reasonCtl.text.trim());
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('${res['message'] ?? tr('تم إرسال الطلب', 'Request sent')}'),
          backgroundColor: Pms.green));
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('تعذّر: $e', 'Failed: $e')), backgroundColor: Pms.red));
    }
  }

  Future<void> _print(Map r) async {
    final api = context.read<AuthProvider>().api;
    final token = await api.token;
    final url = '${api.pmsExtraWorkPrintUrl(r['id'] as int)}?token=${Uri.encodeQueryComponent(token ?? '')}';
    if (!mounted) return;
    Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
        url: url, title: tr('أمر عمل إضافي', 'Extra work order'),
        fileName: '${r['name'] ?? 'extra'}.pdf')));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Pms.bg,
      appBar: AppBar(
        backgroundColor: Pms.violet,
        foregroundColor: Colors.white,
        title: Text(widget.label, style: const TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<Map<String, dynamic>>(
          future: _f,
          builder: (context, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: Padding(padding: EdgeInsets.all(40), child: CircularProgressIndicator()));
            }
            if (snap.hasError) {
              return ListView(children: [Padding(
                padding: const EdgeInsets.all(28),
                child: Text(tr('تعذّر التحميل: ${snap.error}', 'Load failed: ${snap.error}'),
                    textAlign: TextAlign.center, style: const TextStyle(color: Pms.red)))]);
            }
            final rows = (snap.data?['rows'] as List?) ?? const [];
            if (rows.isEmpty) {
              return ListView(children: [Padding(
                padding: const EdgeInsets.only(top: 80),
                child: Column(children: [
                  Icon(Icons.group_off_rounded, size: 54, color: Pms.slate.withValues(alpha: 0.5)),
                  const SizedBox(height: 12),
                  Text(tr('لا يوجد عمّال واردون من مشاريع أخرى على هذا المشروع.',
                         'No incoming extra-work on this project.'),
                      textAlign: TextAlign.center, style: const TextStyle(color: Pms.slate)),
                ]))]);
            }
            return ListView.separated(
              padding: const EdgeInsets.all(12),
              itemCount: rows.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (_, i) => _card(rows[i] as Map),
            );
          },
        ),
      ),
    );
  }

  Widget _card(Map r) {
    final sc = _stateColor('${r['state']}');
    final pending = r['pending'] == true;
    final canPause = r['can_pause'] == true;
    final canEnd = r['can_end'] == true;
    return Container(
      decoration: BoxDecoration(
        color: Colors.white, borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 10, offset: const Offset(0, 3))],
      ),
      padding: const EdgeInsets.all(14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${r['employee']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: Pms.ink)),
            const SizedBox(height: 2),
            Text('${r['name']}${(r['employee_no'] ?? '').toString().isNotEmpty ? ' · #${r['employee_no']}' : ''}',
                style: const TextStyle(color: Pms.slate, fontSize: 12)),
          ])),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
            decoration: BoxDecoration(color: sc.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
            child: Text('${r['state_label']}', style: TextStyle(color: sc, fontWeight: FontWeight.w800, fontSize: 11.5)),
          ),
        ]),
        const Divider(height: 18),
        _kv(Icons.home_work_rounded, tr('المشروع الأساسي', 'Home project'), '${r['home_project']}'),
        _kv(Icons.event_rounded, tr('الفترة', 'Period'),
            '${r['date_from']}${(r['date_to'] ?? '').toString().isNotEmpty ? ' → ${r['date_to']}' : ''}'),
        _kv(Icons.payments_rounded, tr('التعويض', 'Compensation'),
            '${r['comp']} · ${(r['cost'] as num?)?.toStringAsFixed(1) ?? ''} ${r['currency'] ?? ''}'),
        if (pending)
          Container(
            margin: const EdgeInsets.only(top: 8),
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(color: Pms.amber.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(8)),
            child: Row(children: [
              const Icon(Icons.hourglass_top_rounded, size: 16, color: Pms.amber),
              const SizedBox(width: 6),
              Expanded(child: Text(
                tr('طلب ${r['stop_type'] == 'pause' ? 'إيقاف' : 'إنهاء'} بانتظار اعتماد الموارد البشرية',
                   'A ${r['stop_type']} request is pending HR approval'),
                style: const TextStyle(fontSize: 12, color: Pms.ink, fontWeight: FontWeight.w700))),
            ]),
          ),
        const SizedBox(height: 10),
        Row(children: [
          if (canPause)
            Expanded(child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(foregroundColor: Pms.amber, side: const BorderSide(color: Pms.amber)),
              onPressed: () => _stop(r, 'pause'),
              icon: const Icon(Icons.pause_circle_outline_rounded, size: 18),
              label: Text(tr('إيقاف', 'Pause')))),
          if (canPause && canEnd) const SizedBox(width: 8),
          if (canEnd)
            Expanded(child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(foregroundColor: Pms.red, side: const BorderSide(color: Pms.red)),
              onPressed: () => _stop(r, 'end'),
              icon: const Icon(Icons.stop_circle_outlined, size: 18),
              label: Text(tr('إنهاء', 'End')))),
          if (canPause || canEnd) const SizedBox(width: 8),
          Expanded(child: OutlinedButton.icon(
            style: OutlinedButton.styleFrom(foregroundColor: Pms.ink, side: BorderSide(color: Pms.slate.withValues(alpha: 0.4))),
            onPressed: () => _print(r),
            icon: const Icon(Icons.print_rounded, size: 18),
            label: Text(tr('طباعة', 'Print')))),
        ]),
      ]),
    );
  }

  Widget _kv(IconData ic, String k, String v) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 3),
    child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Icon(ic, size: 16, color: Pms.slate),
      const SizedBox(width: 8),
      Text('$k: ', style: const TextStyle(color: Pms.slate, fontSize: 12.5)),
      Expanded(child: Text(v, style: const TextStyle(color: Pms.ink, fontSize: 12.5, fontWeight: FontWeight.w700))),
    ]),
  );
}
