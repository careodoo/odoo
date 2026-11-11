// «طلبات العمل الإضافي» (overtime.request) — نظير /my/pm/p/<id>/overtime في البوابة.
// قائمة الطلبات + إنشاء طلب (حقول رأسية + مصفوفة عمّال: أيام/ساعات/سعر/قيمة/سبب) + تفصيل + إرسال + طباعة.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import '../pdf_report_screen.dart';
import 'pms_shell.dart' show Pms;

Color _stateColor(String s) {
  switch (s) {
    case 'approve':
      return Pms.green;
    case 'reject':
    case 'cancel':
      return Pms.red;
    case 'draft':
      return Pms.slate;
    default:
      return Pms.amber; // submit / waiting
  }
}

// ======================= القائمة =======================
class OvertimeScreen extends StatefulWidget {
  const OvertimeScreen({super.key, required this.projectId, required this.label});
  final int projectId;
  final String label;

  @override
  State<OvertimeScreen> createState() => _OvertimeScreenState();
}

class _OvertimeScreenState extends State<OvertimeScreen> {
  Future<Map<String, dynamic>>? _f;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _f = context.read<AuthProvider>().api.pmsOvertimeList(widget.projectId);
  }

  Future<void> _refresh() async {
    setState(_load);
    await _f;
  }

  Future<void> _openNew() async {
    final created = await Navigator.push<bool>(context, MaterialPageRoute(
        builder: (_) => _OvertimeNew(projectId: widget.projectId)));
    if (created == true) await _refresh();
  }

  Future<void> _openDetail(int oid) async {
    await Navigator.push(context, MaterialPageRoute(
        builder: (_) => _OvertimeDetail(projectId: widget.projectId, oid: oid)));
    await _refresh();
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
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: Pms.violet,
        foregroundColor: Colors.white,
        onPressed: _openNew,
        icon: const Icon(Icons.add_rounded),
        label: Text(tr('طلب جديد', 'New request')),
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
                  Icon(Icons.schedule_rounded, size: 54, color: Pms.slate.withValues(alpha: 0.5)),
                  const SizedBox(height: 12),
                  Text(tr('لا توجد طلبات عمل إضافي لهذا المشروع.', 'No overtime requests for this project.'),
                      textAlign: TextAlign.center, style: const TextStyle(color: Pms.slate)),
                ]))]);
            }
            return ListView.separated(
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 90),
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
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => _openDetail(r['id'] as int),
        child: Container(
          decoration: BoxDecoration(
            color: Colors.white, borderRadius: BorderRadius.circular(16),
            boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 10, offset: const Offset(0, 3))],
          ),
          padding: const EdgeInsets.all(14),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text('${r['name']}',
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: Pms.ink))),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(color: sc.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
                child: Text('${r['state_label']}', style: TextStyle(color: sc, fontWeight: FontWeight.w800, fontSize: 11.5)),
              ),
            ]),
            const SizedBox(height: 8),
            Wrap(spacing: 14, runSpacing: 4, children: [
              _chip(Icons.event_rounded, '${r['request_date']}'),
              _chip(Icons.groups_rounded, '${r['worker_count']} ${tr('عامل', 'workers')}'),
              _chip(Icons.timer_rounded, '${(r['total_hours'] as num?)?.toStringAsFixed(1) ?? '0'} ${tr('ساعة', 'h')}'),
              _chip(Icons.payments_rounded, '${(r['total_amount'] as num?)?.toStringAsFixed(1) ?? '0'}'),
            ]),
          ]),
        ),
      ),
    );
  }

  Widget _chip(IconData ic, String t) => Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(ic, size: 14, color: Pms.slate),
        const SizedBox(width: 4),
        Text(t, style: const TextStyle(fontSize: 12, color: Pms.ink, fontWeight: FontWeight.w700)),
      ]);
}

// ======================= نموذج طلب جديد =======================
class _WLine {
  bool selected = false;
  final days = TextEditingController(text: '1');
  final hours = TextEditingController();
  final rate = TextEditingController();
  final value = TextEditingController();
  final reason = TextEditingController();
  void dispose() {
    days.dispose(); hours.dispose(); rate.dispose(); value.dispose(); reason.dispose();
  }
}

class _OvertimeNew extends StatefulWidget {
  const _OvertimeNew({required this.projectId});
  final int projectId;

  @override
  State<_OvertimeNew> createState() => _OvertimeNewState();
}

class _OvertimeNewState extends State<_OvertimeNew> {
  Future<Map<String, dynamic>>? _opts;
  final Map<int, _WLine> _lines = {};
  bool _saving = false;
  String _search = '';

  // header values
  DateTime _date = DateTime.now();
  String? _compType, _calcMode, _rateBasis, _compMonth, _disbMethod, _pmSource;
  int? _compYear, _benefDept, _benefPm;
  final _bankRef = TextEditingController();
  final _note = TextEditingController();

  @override
  void initState() {
    super.initState();
    _opts = context.read<AuthProvider>().api.pmsOvertimeOptions(widget.projectId).then((d) {
      // قيم افتراضية
      _compYear = (d['cur_year'] as num?)?.toInt();
      _compMonth = d['cur_month']?.toString();
      final cm = (d['calc_modes'] as List?) ?? const [];
      if (cm.isNotEmpty) _calcMode = '${(cm.first as Map)['value']}';
      return d;
    });
  }

  @override
  void dispose() {
    for (final l in _lines.values) {
      l.dispose();
    }
    _bankRef.dispose();
    _note.dispose();
    super.dispose();
  }

  _WLine _line(int id) => _lines.putIfAbsent(id, () => _WLine());

  List<Map<String, dynamic>> _collectLines() {
    final out = <Map<String, dynamic>>[];
    _lines.forEach((eid, l) {
      if (!l.selected) return;
      out.add({
        'employee_id': eid,
        'num_days': double.tryParse(l.days.text.trim()) ?? 1.0,
        'num_hours': double.tryParse(l.hours.text.trim()) ?? 0.0,
        'hourly_rate': double.tryParse(l.rate.text.trim()) ?? 0.0,
        'compensation_value': double.tryParse(l.value.text.trim()) ?? 0.0,
        'overtime_reason': l.reason.text.trim(),
      });
    });
    return out;
  }

  Future<void> _save(bool submit) async {
    final lines = _collectLines();
    if (lines.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('اختر عاملاً واحداً على الأقل', 'Select at least one worker')),
          backgroundColor: Pms.red));
      return;
    }
    setState(() => _saving = true);
    final body = <String, dynamic>{
      'request_date': '${_date.year.toString().padLeft(4, '0')}-${_date.month.toString().padLeft(2, '0')}-${_date.day.toString().padLeft(2, '0')}',
      if (_compType != null) 'compensation_type': _compType,
      if (_calcMode != null) 'calc_mode': _calcMode,
      if (_rateBasis != null) 'rate_basis': _rateBasis,
      if (_compMonth != null) 'comp_month': _compMonth,
      if (_compYear != null) 'comp_year': _compYear,
      if (_disbMethod != null) 'disbursement_method': _disbMethod,
      if (_pmSource != null) 'pm_approval_source': _pmSource,
      if (_bankRef.text.trim().isNotEmpty) 'bank_ref': _bankRef.text.trim(),
      if (_note.text.trim().isNotEmpty) 'note': _note.text.trim(),
      if (_benefDept != null) 'beneficiary_department_id': _benefDept,
      if (_benefPm != null) 'beneficiary_pm_id': _benefPm,
      'lines': lines,
      'do': submit ? 'submit' : '',
    };
    try {
      final res = await context.read<AuthProvider>().api.pmsOvertimeCreate(widget.projectId, body);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('${res['message'] ?? tr('تم', 'Done')}'), backgroundColor: Pms.green));
      Navigator.pop(context, true);
    } catch (e) {
      if (!mounted) return;
      setState(() => _saving = false);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('تعذّر: $e', 'Failed: $e')), backgroundColor: Pms.red));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Pms.bg,
      appBar: AppBar(
        backgroundColor: Pms.violet, foregroundColor: Colors.white,
        title: Text(tr('طلب عمل إضافي جديد', 'New overtime request'),
            style: const TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _opts,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Padding(padding: const EdgeInsets.all(28),
                child: Text(tr('تعذّر التحميل: ${snap.error}', 'Load failed: ${snap.error}'),
                    textAlign: TextAlign.center, style: const TextStyle(color: Pms.red)));
          }
          final d = snap.data ?? const {};
          final proj = (d['project'] as Map?) ?? const {};
          if (proj['has_dept'] == false) {
            return Padding(padding: const EdgeInsets.all(28),
                child: Text(tr('المشروع غير مرتبط بإدارة — لا يمكن إنشاء طلب.',
                    'Project has no department — cannot create a request.'),
                    textAlign: TextAlign.center, style: const TextStyle(color: Pms.red)));
          }
          final workers = ((d['workers'] as List?) ?? const [])
              .where((w) => _search.isEmpty ||
                  '${(w as Map)['name']}'.toLowerCase().contains(_search.toLowerCase()) ||
                  '${w['no']}'.contains(_search))
              .toList();
          final selCount = _lines.values.where((l) => l.selected).length;
          return Column(children: [
            Expanded(child: ListView(padding: const EdgeInsets.all(12), children: [
              _headerCard(d),
              const SizedBox(height: 12),
              _sectionTitle('${tr('العمّال', 'Workers')} (${proj['department'] ?? ''})',
                  trailing: selCount > 0 ? '$selCount ${tr('محدَّد', 'selected')}' : null),
              const SizedBox(height: 6),
              TextField(
                onChanged: (v) => setState(() => _search = v),
                decoration: InputDecoration(
                  hintText: tr('بحث عن عامل…', 'Search worker…'),
                  prefixIcon: const Icon(Icons.search_rounded, size: 20),
                  filled: true, fillColor: Colors.white, isDense: true,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                ),
              ),
              const SizedBox(height: 8),
              for (final w in workers) _workerTile(w as Map),
              if (workers.isEmpty) Padding(padding: const EdgeInsets.all(20),
                  child: Text(tr('لا يوجد عمّال في هذه الإدارة.', 'No workers in this department.'),
                      textAlign: TextAlign.center, style: const TextStyle(color: Pms.slate))),
            ])),
            _bottomBar(),
          ]);
        },
      ),
    );
  }

  Widget _sectionTitle(String t, {String? trailing}) => Row(children: [
        Text(t, style: const TextStyle(fontWeight: FontWeight.w900, color: Pms.ink, fontSize: 14)),
        const Spacer(),
        if (trailing != null)
          Text(trailing, style: const TextStyle(color: Pms.violet, fontWeight: FontWeight.w800, fontSize: 12)),
      ]);

  Widget _headerCard(Map d) {
    List<Map> _opt(String k) => ((d[k] as List?) ?? const []).cast<Map>();
    final years = ((d['years'] as List?) ?? const []).map((y) => (y as num).toInt()).toList();
    return Container(
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
      padding: const EdgeInsets.all(14),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        _sectionTitle(tr('بيانات الطلب', 'Request details')),
        const SizedBox(height: 10),
        _dateField(),
        const SizedBox(height: 10),
        _dd(tr('نوع التعويض', 'Compensation type'), _opt('comp_types'), _compType, (v) => setState(() => _compType = v)),
        const SizedBox(height: 10),
        _dd(tr('طريقة الحساب', 'Calc mode'), _opt('calc_modes'), _calcMode, (v) => setState(() => _calcMode = v)),
        const SizedBox(height: 10),
        _dd(tr('أساس السعر', 'Rate basis'), _opt('rate_bases'), _rateBasis, (v) => setState(() => _rateBasis = v)),
        const SizedBox(height: 10),
        Row(children: [
          Expanded(child: _dd(tr('شهر الاستحقاق', 'Month'), _opt('comp_months'), _compMonth, (v) => setState(() => _compMonth = v))),
          const SizedBox(width: 8),
          Expanded(child: _ddInt(tr('السنة', 'Year'), years, _compYear, (v) => setState(() => _compYear = v))),
        ]),
        const SizedBox(height: 10),
        _dd(tr('طريقة الصرف', 'Disbursement'), _opt('disb_methods'), _disbMethod, (v) => setState(() => _disbMethod = v)),
        const SizedBox(height: 10),
        _dd(tr('مصدر اعتماد المدير', 'PM approval source'), _opt('pm_sources'), _pmSource, (v) => setState(() => _pmSource = v)),
        const SizedBox(height: 10),
        _ddIntMap(tr('الإدارة المستفيدة', 'Beneficiary dept'), _opt('depts'), _benefDept, (v) => setState(() => _benefDept = v)),
        const SizedBox(height: 10),
        _ddIntMap(tr('مدير الإدارة المستفيدة', 'Beneficiary PM'), _opt('pm_users'), _benefPm, (v) => setState(() => _benefPm = v)),
        const SizedBox(height: 10),
        _txt(_bankRef, tr('مرجع التحويل/الحساب', 'Transfer / account ref.')),
        const SizedBox(height: 10),
        _txt(_note, tr('ملاحظة', 'Note'), lines: 2),
      ]),
    );
  }

  Widget _workerTile(Map w) {
    final id = w['id'] as int;
    final l = _line(id);
    final status = '${w['worker_status_label'] ?? ''}';
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: Colors.white, borderRadius: BorderRadius.circular(14),
        border: Border.all(color: l.selected ? Pms.violet.withValues(alpha: 0.5) : const Color(0xFFEDEFF3)),
      ),
      child: Column(children: [
        CheckboxListTile(
          value: l.selected,
          activeColor: Pms.violet,
          controlAffinity: ListTileControlAffinity.leading,
          onChanged: (v) => setState(() => l.selected = v ?? false),
          title: Text('${w['name']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5, color: Pms.ink)),
          subtitle: Text([
            if ('${w['no']}'.isNotEmpty) '#${w['no']}',
            if ('${w['job_title']}'.isNotEmpty) '${w['job_title']}',
            if (status.isNotEmpty) '• $status',
          ].join('  '), style: const TextStyle(fontSize: 11.5, color: Pms.slate)),
        ),
        if (l.selected)
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
            child: Column(children: [
              Row(children: [
                Expanded(child: _num(l.days, tr('أيام', 'Days'))),
                const SizedBox(width: 8),
                Expanded(child: _num(l.hours, tr('ساعات', 'Hours'))),
              ]),
              const SizedBox(height: 8),
              Row(children: [
                Expanded(child: _num(l.rate, tr('السعر/ساعة', 'Rate/h'))),
                const SizedBox(width: 8),
                Expanded(child: _num(l.value, tr('القيمة', 'Value'))),
              ]),
              const SizedBox(height: 8),
              _txt(l.reason, tr('سبب العمل الإضافي', 'Overtime reason')),
            ]),
          ),
      ]),
    );
  }

  Widget _bottomBar() {
    return Container(
      padding: EdgeInsets.fromLTRB(12, 10, 12, 10 + MediaQuery.of(context).padding.bottom),
      decoration: BoxDecoration(color: Colors.white, boxShadow: [
        BoxShadow(color: Colors.black.withValues(alpha: 0.06), blurRadius: 12, offset: const Offset(0, -2)),
      ]),
      child: Row(children: [
        Expanded(child: OutlinedButton(
          onPressed: _saving ? null : () => _save(false),
          child: Text(tr('حفظ كمسودّة', 'Save draft')))),
        const SizedBox(width: 10),
        Expanded(child: ElevatedButton.icon(
          style: ElevatedButton.styleFrom(backgroundColor: Pms.violet, foregroundColor: Colors.white),
          onPressed: _saving ? null : () => _save(true),
          icon: _saving
              ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
              : const Icon(Icons.send_rounded, size: 18),
          label: Text(tr('حفظ وإرسال', 'Save & submit')))),
      ]),
    );
  }

  // ---- field helpers ----
  Widget _dateField() => InkWell(
        onTap: () async {
          final picked = await showDatePicker(
              context: context, initialDate: _date,
              firstDate: DateTime(2020), lastDate: DateTime(2031));
          if (picked != null) setState(() => _date = picked);
        },
        child: InputDecorator(
          decoration: _dec(tr('تاريخ الطلب', 'Request date')),
          child: Text('${_date.year}-${_date.month.toString().padLeft(2, '0')}-${_date.day.toString().padLeft(2, '0')}',
              style: const TextStyle(fontSize: 13.5, color: Pms.ink)),
        ),
      );

  Widget _dd(String label, List<Map> opts, String? val, ValueChanged<String?> on) =>
      DropdownButtonFormField<String>(
        value: val, isExpanded: true, decoration: _dec(label),
        items: [for (final o in opts) DropdownMenuItem(value: '${o['value']}', child: Text('${o['label']}', overflow: TextOverflow.ellipsis))],
        onChanged: on,
      );

  Widget _ddInt(String label, List<int> opts, int? val, ValueChanged<int?> on) =>
      DropdownButtonFormField<int>(
        value: val, isExpanded: true, decoration: _dec(label),
        items: [for (final o in opts) DropdownMenuItem(value: o, child: Text('$o'))],
        onChanged: on,
      );

  Widget _ddIntMap(String label, List<Map> opts, int? val, ValueChanged<int?> on) =>
      DropdownButtonFormField<int>(
        value: val, isExpanded: true, decoration: _dec(label),
        items: [for (final o in opts) DropdownMenuItem(value: o['id'] as int, child: Text('${o['name']}', overflow: TextOverflow.ellipsis))],
        onChanged: on,
      );

  Widget _txt(TextEditingController c, String label, {int lines = 1}) =>
      TextField(controller: c, maxLines: lines, decoration: _dec(label));

  Widget _num(TextEditingController c, String label) => TextField(
        controller: c,
        keyboardType: const TextInputType.numberWithOptions(decimal: true),
        decoration: _dec(label),
      );

  InputDecoration _dec(String label) => InputDecoration(
        labelText: label, isDense: true,
        filled: true, fillColor: Pms.bg,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
      );
}

// ======================= تفصيل =======================
class _OvertimeDetail extends StatefulWidget {
  const _OvertimeDetail({required this.projectId, required this.oid});
  final int projectId;
  final int oid;

  @override
  State<_OvertimeDetail> createState() => _OvertimeDetailState();
}

class _OvertimeDetailState extends State<_OvertimeDetail> {
  Future<Map<String, dynamic>>? _f;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _f = context.read<AuthProvider>().api.pmsOvertime(widget.oid);
  }

  Future<void> _refresh() async {
    setState(_load);
    await _f;
  }

  Future<void> _submit() async {
    setState(() => _busy = true);
    try {
      final res = await context.read<AuthProvider>().api.pmsOvertimeSubmit(widget.oid);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text('${res['message'] ?? tr('تم', 'Done')}'), backgroundColor: Pms.green));
      await _refresh();
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('تعذّر: $e', 'Failed: $e')), backgroundColor: Pms.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _print(String name) async {
    final api = context.read<AuthProvider>().api;
    final token = await api.token;
    final url = '${api.pmsOvertimePrintUrl(widget.oid)}?token=${Uri.encodeQueryComponent(token ?? '')}';
    if (!mounted) return;
    Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
        url: url, title: tr('طلب عمل إضافي', 'Overtime request'), fileName: '$name.pdf')));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Pms.bg,
      appBar: AppBar(
        backgroundColor: Pms.violet, foregroundColor: Colors.white,
        title: Text(tr('طلب عمل إضافي', 'Overtime request'), style: const TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _f,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Padding(padding: const EdgeInsets.all(28),
                child: Text(tr('تعذّر التحميل: ${snap.error}', 'Load failed: ${snap.error}'),
                    textAlign: TextAlign.center, style: const TextStyle(color: Pms.red)));
          }
          final d = snap.data ?? const {};
          final sc = _stateColor('${d['state']}');
          final lines = (d['lines'] as List?) ?? const [];
          final canSubmit = d['can_submit'] == true;
          return ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
            Container(
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
              padding: const EdgeInsets.all(14),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${d['name']}',
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: Pms.ink))),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                    decoration: BoxDecoration(color: sc.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
                    child: Text('${d['state_label']}', style: TextStyle(color: sc, fontWeight: FontWeight.w800, fontSize: 11.5)),
                  ),
                ]),
                const Divider(height: 18),
                _kv(tr('التاريخ', 'Date'), '${d['request_date']}'),
                _kv(tr('الإدارة', 'Department'), '${d['department']}'),
                if ('${d['beneficiary_department']}'.isNotEmpty) _kv(tr('الإدارة المستفيدة', 'Beneficiary'), '${d['beneficiary_department']}'),
                _kv(tr('نوع التعويض', 'Comp. type'), '${d['compensation_type']}'),
                _kv(tr('طريقة الحساب', 'Calc mode'), '${d['calc_mode']}'),
                _kv(tr('شهر/سنة', 'Month/Year'), '${d['comp_month']} ${d['comp_year']}'),
                _kv(tr('طريقة الصرف', 'Disbursement'), '${d['disbursement_method']}'),
                const Divider(height: 18),
                Row(children: [
                  _stat(tr('العمّال', 'Workers'), '${d['worker_count']}'),
                  _stat(tr('الساعات', 'Hours'), '${(d['total_hours'] as num?)?.toStringAsFixed(1) ?? '0'}'),
                  _stat(tr('الإجمالي', 'Total'), '${(d['total_amount'] as num?)?.toStringAsFixed(1) ?? '0'}'),
                ]),
              ]),
            ),
            const SizedBox(height: 12),
            Text(tr('العمّال', 'Workers'), style: const TextStyle(fontWeight: FontWeight.w900, color: Pms.ink, fontSize: 14)),
            const SizedBox(height: 6),
            for (final ln in lines) _lineCard(ln as Map),
            const SizedBox(height: 14),
            Row(children: [
              if (canSubmit)
                Expanded(child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(backgroundColor: Pms.violet, foregroundColor: Colors.white),
                  onPressed: _busy ? null : _submit,
                  icon: const Icon(Icons.send_rounded, size: 18),
                  label: Text(tr('إرسال للاعتماد', 'Submit')))),
              if (canSubmit) const SizedBox(width: 10),
              Expanded(child: OutlinedButton.icon(
                style: OutlinedButton.styleFrom(foregroundColor: Pms.ink, side: BorderSide(color: Pms.slate.withValues(alpha: 0.4))),
                onPressed: () => _print('${d['name']}'),
                icon: const Icon(Icons.print_rounded, size: 18),
                label: Text(tr('طباعة', 'Print')))),
            ]),
          ]);
        },
      ),
    );
  }

  Widget _lineCard(Map ln) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${ln['employee']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5, color: Pms.ink)),
          if ('${ln['job_title']}'.isNotEmpty)
            Text('${ln['job_title']}', style: const TextStyle(fontSize: 11.5, color: Pms.slate)),
          const SizedBox(height: 8),
          Wrap(spacing: 14, runSpacing: 4, children: [
            _chip(tr('أيام', 'Days'), '${(ln['num_days'] as num?)?.toStringAsFixed(1) ?? ''}'),
            _chip(tr('ساعات', 'Hours'), '${(ln['num_hours'] as num?)?.toStringAsFixed(1) ?? ''}'),
            _chip(tr('السعر', 'Rate'), '${(ln['hourly_rate'] as num?)?.toStringAsFixed(3) ?? ''}'),
            _chip(tr('القيمة', 'Value'), '${(ln['compensation_value'] as num?)?.toStringAsFixed(1) ?? ''}'),
          ]),
          if ('${ln['reason']}'.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text('${ln['reason']}', style: const TextStyle(fontSize: 12, color: Pms.slate)),
          ],
        ]),
      );

  Widget _chip(String k, String v) => Row(mainAxisSize: MainAxisSize.min, children: [
        Text('$k: ', style: const TextStyle(fontSize: 11.5, color: Pms.slate)),
        Text(v, style: const TextStyle(fontSize: 12.5, color: Pms.ink, fontWeight: FontWeight.w800)),
      ]);

  Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 120, child: Text(k, style: const TextStyle(color: Pms.slate, fontSize: 12.5))),
          Expanded(child: Text(v, style: const TextStyle(color: Pms.ink, fontSize: 12.5, fontWeight: FontWeight.w700))),
        ]),
      );

  Widget _stat(String k, String v) => Expanded(
        child: Column(children: [
          Text(v, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: Pms.violet)),
          const SizedBox(height: 2),
          Text(k, style: const TextStyle(fontSize: 11, color: Pms.slate)),
        ]),
      );
}
