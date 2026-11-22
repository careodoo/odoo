// شاشة «الشكاوى التأديبية» — أيقونة داخل المشروع: مدير المشروع يقدّم شكوى ضد
// أحد عمّال مشروعه ويتابع مسارها. مرآة لبوابة /my/pm/p/<id>/discipline.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'pms_shell.dart' show Pms;

class DisciplineScreen extends StatefulWidget {
  const DisciplineScreen({super.key, required this.projectId, required this.label});
  final int projectId;
  final String label;

  @override
  State<DisciplineScreen> createState() => _DisciplineScreenState();
}

class _DisciplineScreenState extends State<DisciplineScreen> {
  Future<Map<String, dynamic>>? _f;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _f = context.read<AuthProvider>().api.pmComplaints(widget.projectId);
  }

  Future<void> _refresh() async {
    setState(_load);
    await _f;
  }

  Color _sevColor(String k) =>
      k == 'high' ? Pms.red : (k == 'low' ? Pms.green : Pms.amber);

  Color _stateColor(String s) {
    if (s == 'applied') return Pms.green;
    if (s == 'rejected' || s == 'closed' || s == 'cancelled') return Pms.slate;
    return const Color(0xFF2563EB);
  }

  // نموذج تقديم شكوى جديدة
  Future<void> _fileSheet(Map data) async {
    final workers = (data['workers'] as List?) ?? [];
    final cats = (data['categories'] as List?) ?? [];
    int? empId;
    int? catId;
    String severity = 'medium';
    bool ack = false;
    final descCtl = TextEditingController();
    bool busy = false;

    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => StatefulBuilder(builder: (ctx, setM) {
        return Padding(
          padding: EdgeInsets.only(
              left: 16, right: 16, top: 14,
              bottom: MediaQuery.of(ctx).viewInsets.bottom + 16),
          child: SingleChildScrollView(
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
              Row(children: [
                const Icon(Icons.gavel_rounded, color: Pms.red, size: 20),
                const SizedBox(width: 8),
                Text(tr('تقديم شكوى تأديبية', 'File a disciplinary complaint'),
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: Pms.ink)),
              ]),
              const SizedBox(height: 14),
              _lbl(tr('العامل المُشتكى عليه', 'Worker')),
              DropdownButtonFormField<int>(
                value: empId, isExpanded: true,
                decoration: _dec(tr('اختر العامل', 'Choose worker')),
                items: [
                  for (final w in workers)
                    DropdownMenuItem<int>(
                        value: (w as Map)['id'] as int,
                        child: Text('${w['name']}${(w['badge'] ?? '').toString().isNotEmpty ? ' (${w['badge']})' : ''}',
                            overflow: TextOverflow.ellipsis)),
                ],
                onChanged: (v) => setM(() => empId = v),
              ),
              const SizedBox(height: 10),
              _lbl(tr('نوع المخالفة', 'Category')),
              DropdownButtonFormField<int>(
                value: catId, isExpanded: true,
                decoration: _dec(tr('اختر النوع', 'Choose category')),
                items: [
                  for (final c in cats)
                    DropdownMenuItem<int>(
                        value: (c as Map)['id'] as int,
                        child: Text('${c['name']}', overflow: TextOverflow.ellipsis)),
                ],
                onChanged: (v) => setM(() => catId = v),
              ),
              const SizedBox(height: 10),
              _lbl(tr('درجة الخطورة', 'Severity')),
              Row(children: [
                _segBtn(tr('بسيطة', 'Low'), severity == 'low', Pms.green, () => setM(() => severity = 'low')),
                _segBtn(tr('متوسّطة', 'Medium'), severity == 'medium', Pms.amber, () => setM(() => severity = 'medium')),
                _segBtn(tr('جسيمة', 'High'), severity == 'high', Pms.red, () => setM(() => severity = 'high')),
              ]),
              const SizedBox(height: 10),
              _lbl(tr('وصف الواقعة', 'Incident description')),
              TextField(
                controller: descCtl, maxLines: 3,
                decoration: _dec(tr('اكتب تفاصيل الواقعة...', 'Describe what happened...')),
              ),
              const SizedBox(height: 8),
              CheckboxListTile(
                value: ack, dense: true, contentPadding: EdgeInsets.zero,
                controlAffinity: ListTileControlAffinity.leading,
                activeColor: Pms.red,
                onChanged: (v) => setM(() => ack = v ?? false),
                title: Text(tr('أُقرّ بصحّة البيانات المذكورة', 'I confirm the information is accurate'),
                    style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: Pms.ink)),
              ),
              const SizedBox(height: 6),
              SizedBox(
                height: 46,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(
                      backgroundColor: Pms.red, foregroundColor: Colors.white,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                  icon: busy
                      ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : const Icon(Icons.send_rounded, size: 18),
                  label: Text(tr('تقديم الشكوى', 'Submit complaint'),
                      style: const TextStyle(fontWeight: FontWeight.w900)),
                  onPressed: busy
                      ? null
                      : () async {
                          if (empId == null || catId == null || descCtl.text.trim().isEmpty) {
                            _toast(tr('أكمل العامل والنوع والوصف', 'Fill worker, category and description'));
                            return;
                          }
                          setM(() => busy = true);
                          try {
                            await context.read<AuthProvider>().api.pmFileComplaint(widget.projectId, {
                              'employee_id': empId,
                              'category_id': catId,
                              'severity': severity,
                              'description': descCtl.text.trim(),
                              'ack': ack,
                            });
                            if (ctx.mounted) Navigator.pop(ctx, true);
                          } catch (e) {
                            setM(() => busy = false);
                            _toast('$e'.replaceFirst('Exception: ', ''));
                          }
                        },
                ),
              ),
            ]),
          ),
        );
      }),
    );
    if (ok == true) {
      _toast(tr('قُدّمت الشكوى وأُحيلت لاعتماد المدير المباشر', 'Submitted for direct manager approval'));
      await _refresh();
    }
  }

  // تفاصيل الشكوى + المسار
  void _detailSheet(Map r) {
    const steps = [
      ['submitted', 'بانتظار المدير المباشر', 'Pending direct manager'],
      ['manager_approved', 'بانتظار الموارد البشرية', 'Pending HR'],
      ['hr_review', 'تحقيق الموارد البشرية', 'HR investigation'],
      ['legal_review', 'بانتظار الإدارة القانونية', 'Pending Legal'],
      ['penalty_decided', 'بانتظار تطبيق الجزاء', 'Pending penalty'],
      ['applied', 'طُبّق الجزاء', 'Penalty applied'],
    ];
    final order = [for (final s in steps) s[0]];
    final st = '${r['state']}';
    final curIdx = order.contains(st) ? order.indexOf(st) : (st == 'closed' ? order.length : -1);
    showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 14, 16, 24),
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Text('${r['name']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: Pms.ink)),
              const Spacer(),
              _badge('${r['state_label']}', _stateColor(st)),
            ]),
            const SizedBox(height: 4),
            Text('${r['employee']}', style: const TextStyle(color: Pms.slate, fontWeight: FontWeight.w700)),
            const SizedBox(height: 14),
            if (st == 'rejected')
              Container(
                width: double.infinity, padding: const EdgeInsets.all(10), margin: const EdgeInsets.only(bottom: 10),
                decoration: BoxDecoration(color: const Color(0xFFFDECEA), borderRadius: BorderRadius.circular(10)),
                child: Text('🚫 ${tr('مرفوضة', 'Rejected')}', style: const TextStyle(color: Pms.red, fontWeight: FontWeight.w800)),
              )
            else
              Column(children: [
                for (int i = 0; i < steps.length; i++)
                  _timelineRow(tr(steps[i][1], steps[i][2]), i < curIdx, i == curIdx),
              ]),
            const SizedBox(height: 10),
            _kv(tr('نوع المخالفة', 'Category'), '${r['category']}'),
            _kv(tr('الخطورة', 'Severity'), '${r['severity']}'),
            _kv(tr('التاريخ', 'Date'), '${r['incident_date']}'),
            if ('${r['penalty']}'.isNotEmpty) _kv(tr('الجزاء المُقرَّر', 'Penalty'), '${r['penalty']}'),
            if ('${r['law_article']}'.isNotEmpty) _kv(tr('السند القانوني', 'Legal article'), '${r['law_article']}'),
            const SizedBox(height: 8),
            Text(tr('وصف الواقعة', 'Description'), style: const TextStyle(color: Pms.slate, fontWeight: FontWeight.w700, fontSize: 12)),
            const SizedBox(height: 3),
            Container(
              width: double.infinity, padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(border: Border.all(color: const Color(0xFFE6EAF3)), borderRadius: BorderRadius.circular(8)),
              child: Text('${r['description']}', style: const TextStyle(fontSize: 13, color: Pms.ink)),
            ),
            // سحب/إلغاء الشكوى (لمُقدّمها، قبل التطبيق/الإغلاق) → الحالة «ملغاة»
            if (!['applied', 'closed', 'rejected', 'cancelled'].contains(st)) ...[
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: OutlinedButton.icon(
                  style: OutlinedButton.styleFrom(
                      foregroundColor: Pms.red, side: const BorderSide(color: Pms.red),
                      padding: const EdgeInsets.symmetric(vertical: 12)),
                  icon: const Icon(Icons.block_rounded),
                  label: Text(tr('سحب / إلغاء الشكوى', 'Withdraw / cancel')),
                  onPressed: () async {
                    try {
                      await context.read<AuthProvider>().api.pmCancelComplaint(r['id'] as int);
                      if (ctx.mounted) Navigator.pop(ctx);
                      if (mounted) {
                        setState(() => _f = context.read<AuthProvider>().api.pmComplaints(widget.projectId));
                        ScaffoldMessenger.of(context).showSnackBar(
                            SnackBar(content: Text(tr('أُلغيت الشكوى (ملغاة)', 'Complaint cancelled'))));
                      }
                    } catch (e) {
                      if (ctx.mounted) ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(content: Text('$e')));
                    }
                  },
                ),
              ),
            ],
          ]),
        ),
      ),
    );
  }

  Widget _timelineRow(String label, bool done, bool cur) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(children: [
          Container(
            width: 24, height: 24, alignment: Alignment.center,
            decoration: BoxDecoration(
                color: done ? Pms.green : (cur ? const Color(0xFF2563EB) : const Color(0xFFC7CCD8)),
                shape: BoxShape.circle),
            child: done
                ? const Icon(Icons.check_rounded, size: 14, color: Colors.white)
                : Icon(cur ? Icons.radio_button_checked : Icons.circle, size: cur ? 12 : 8, color: Colors.white),
          ),
          const SizedBox(width: 10),
          Expanded(child: Text(label,
              style: TextStyle(
                  fontSize: 12.5, fontWeight: done || cur ? FontWeight.w800 : FontWeight.w600,
                  color: done || cur ? Pms.ink : Pms.slate))),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FB),
      appBar: AppBar(
        title: Text(widget.label, style: const TextStyle(fontWeight: FontWeight.w900)),
        backgroundColor: Pms.red, foregroundColor: Colors.white,
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _f,
        builder: (ctx, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return _errView('${snap.error}'.replaceFirst('Exception: ', ''));
          }
          final data = snap.data ?? {};
          final rows = (data['rows'] as List?) ?? [];
          return RefreshIndicator(
            onRefresh: _refresh,
            child: rows.isEmpty
                ? ListView(children: [
                    const SizedBox(height: 120),
                    Icon(Icons.gavel_rounded, size: 52, color: Pms.slate.withValues(alpha: 0.4)),
                    const SizedBox(height: 10),
                    Center(child: Text(tr('لا توجد شكاوى', 'No complaints'),
                        style: const TextStyle(color: Pms.slate, fontWeight: FontWeight.w700))),
                  ])
                : ListView.builder(
                    padding: const EdgeInsets.all(12),
                    itemCount: rows.length,
                    itemBuilder: (ctx, i) {
                      final r = rows[i] as Map;
                      return Card(
                        elevation: 0,
                        margin: const EdgeInsets.only(bottom: 10),
                        shape: RoundedRectangleBorder(
                            side: const BorderSide(color: Color(0xFFE6EAF3)),
                            borderRadius: BorderRadius.circular(14)),
                        child: InkWell(
                          borderRadius: BorderRadius.circular(14),
                          onTap: () => _detailSheet(r),
                          child: Padding(
                            padding: const EdgeInsets.all(12),
                            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              Row(children: [
                                Text('${r['name']}', style: const TextStyle(fontWeight: FontWeight.w900, color: Pms.ink)),
                                const Spacer(),
                                _badge('${r['severity']}', _sevColor('${r['severity_key']}')),
                              ]),
                              const SizedBox(height: 4),
                              Text('${r['employee']}', style: const TextStyle(fontWeight: FontWeight.w700, color: Pms.ink, fontSize: 13.5)),
                              const SizedBox(height: 2),
                              Text('${r['category']}', style: const TextStyle(color: Pms.slate, fontSize: 12.5)),
                              const SizedBox(height: 8),
                              Row(children: [
                                _badge('${r['state_label']}', _stateColor('${r['state']}')),
                                const Spacer(),
                                if ('${r['penalty']}'.isNotEmpty)
                                  Text('${r['penalty']}', style: const TextStyle(color: Pms.red, fontWeight: FontWeight.w800, fontSize: 12)),
                                const SizedBox(width: 6),
                                Text('${r['incident_date']}', style: const TextStyle(color: Pms.slate, fontSize: 11.5)),
                              ]),
                            ]),
                          ),
                        ),
                      );
                    },
                  ),
          );
        },
      ),
      floatingActionButton: FutureBuilder<Map<String, dynamic>>(
        future: _f,
        builder: (ctx, snap) {
          final data = snap.data ?? {};
          return FloatingActionButton.extended(
            backgroundColor: Pms.red,
            icon: const Icon(Icons.add_rounded),
            label: Text(tr('شكوى جديدة', 'New complaint'), style: const TextStyle(fontWeight: FontWeight.w900)),
            onPressed: snap.hasData ? () => _fileSheet(data) : null,
          );
        },
      ),
    );
  }

  // ---- helpers ----
  Widget _errView(String msg) => ListView(children: [
        const SizedBox(height: 120),
        const Icon(Icons.error_outline_rounded, size: 48, color: Pms.red),
        const SizedBox(height: 10),
        Center(child: Padding(padding: const EdgeInsets.symmetric(horizontal: 30),
            child: Text(msg, textAlign: TextAlign.center, style: const TextStyle(color: Pms.slate)))),
      ]);

  Widget _lbl(String t) => Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Text(t, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12, color: Pms.ink)));

  InputDecoration _dec(String hint) => InputDecoration(
        hintText: hint, isDense: true,
        contentPadding: const EdgeInsets.symmetric(horizontal: 10, vertical: 10),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
      );

  Widget _segBtn(String t, bool on, Color c, VoidCallback tap) => Expanded(
        child: Padding(
          padding: const EdgeInsets.only(right: 6),
          child: InkWell(
            onTap: tap,
            borderRadius: BorderRadius.circular(10),
            child: Container(
              height: 38, alignment: Alignment.center,
              decoration: BoxDecoration(
                  color: on ? c.withValues(alpha: 0.14) : const Color(0xFFF1F3F8),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: on ? c : const Color(0xFFE6EAF3), width: on ? 1.4 : 1)),
              child: Text(t, style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: on ? c : Pms.slate)),
            ),
          ),
        ),
      );

  Widget _badge(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(999)),
        child: Text(t, style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 11)),
      );

  Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 120, child: Text(k, style: const TextStyle(color: Pms.slate, fontWeight: FontWeight.w700, fontSize: 12.5))),
          Expanded(child: Text(v, style: const TextStyle(color: Pms.ink, fontWeight: FontWeight.w700, fontSize: 12.5))),
        ]),
      );

  void _toast(String m) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }
}
