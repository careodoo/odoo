import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/api_client.dart';
import '../../core/i18n.dart';

const _navy = Color(0xFF0A1F44);
const _sub = Color(0xFF4F46E5);
const _muted = Color(0xFF64748B);
const _bg = Color(0xFFEDF1F7);
const _ok = Color(0xFF16A34A);
const _crit = Color(0xFFDC2626);

Color _stC(String s) => s == 'applied'
    ? _ok
    : s == 'submitted'
        ? const Color(0xFF2563EB)
        : s == 'rejected'
            ? _crit
            : _muted;

/// 🔄 الإحلال (البديل عن الغائب) — قائمة + إنشاء + اعتماد.
class SubstitutionScreen extends StatefulWidget {
  const SubstitutionScreen({super.key});
  @override
  State<SubstitutionScreen> createState() => _SubstitutionScreenState();
}

class _SubstitutionScreenState extends State<SubstitutionScreen> {
  ApiClient get _api => context.read<AuthProvider>().api;
  List _projects = const [];
  int? _projectId;
  List _rows = const [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    try {
      final ps = await _api.tsProjects();
      if (mounted) {
        setState(() {
          _projects = ps;
          if (ps.isNotEmpty) _projectId = (ps.first as Map)['id'] as int;
        });
      }
      await _load();
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _load() async {
    if (_projectId == null) {
      setState(() => _loading = false);
      return;
    }
    setState(() => _loading = true);
    try {
      final r = await _api.subList(projectId: _projectId);
      if (mounted) setState(() => _rows = r);
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _navy,
        foregroundColor: Colors.white,
        title: Text(tr('الإحلال (البديل عن الغائب)', 'Substitutions')),
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))],
      ),
      floatingActionButton: _projectId == null
          ? null
          : FloatingActionButton.extended(
              backgroundColor: _sub,
              foregroundColor: Colors.white,
              icon: const Icon(Icons.swap_horiz_rounded),
              label: Text(tr('إرسال بديل', 'Send substitute')),
              onPressed: _openCreate,
            ),
      body: Column(children: [
        if (_projects.isNotEmpty)
          Padding(
            padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
            child: DropdownButtonFormField<int>(
              value: _projectId,
              isExpanded: true,
              decoration: _dec(tr('المشروع', 'Project')),
              items: _projects
                  .map((p) => DropdownMenuItem<int>(
                      value: (p as Map)['id'] as int, child: Text('${p['name']}', overflow: TextOverflow.ellipsis)))
                  .toList(),
              onChanged: (v) {
                setState(() => _projectId = v);
                _load();
              },
            ),
          ),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _rows.isEmpty
                  ? Center(child: Text(tr('لا طلبات إحلال', 'No substitutions'), style: const TextStyle(color: _muted)))
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.separated(
                        padding: const EdgeInsets.fromLTRB(12, 8, 12, 90),
                        itemCount: _rows.length,
                        separatorBuilder: (_, __) => const SizedBox(height: 8),
                        itemBuilder: (_, i) => _card(_rows[i] as Map),
                      ),
                    ),
        ),
      ]),
    );
  }

  Widget _card(Map s) {
    final st = (s['state'] ?? '').toString();
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(13),
      child: Padding(
        padding: const EdgeInsets.all(13),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${s['name']}', style: const TextStyle(fontSize: 10.5, color: _muted, fontWeight: FontWeight.w700)),
                Text('${s['substitute']}  ←  ${s['absent']}',
                    style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w900, color: _sub)),
                Text([
                  if ('${s['month'] ?? ''}'.isNotEmpty) '🗓 ${s['month']}',
                  '${s['days']} ${tr('يوم', 'd')}',
                  '${s['price_rule_label']}',
                  if ('${s['timesheet'] ?? ''}'.isNotEmpty) '${s['timesheet']}',
                ].join(' · '), style: const TextStyle(fontSize: 11, color: _muted)),
              ]),
            ),
            Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                decoration: BoxDecoration(color: _stC(st).withValues(alpha: 0.13), borderRadius: BorderRadius.circular(16)),
                child: Text('${s['state_label']}', style: TextStyle(color: _stC(st), fontWeight: FontWeight.w800, fontSize: 10.5)),
              ),
              const SizedBox(height: 4),
              Text('${s['total_cost']} ${tr('د.ك', 'KWD')}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13)),
            ]),
          ]),
          if (st == 'submitted')
            Padding(
              padding: const EdgeInsets.only(top: 9),
              child: Row(children: [
                Expanded(
                  child: FilledButton(
                    style: FilledButton.styleFrom(backgroundColor: _ok, padding: const EdgeInsets.symmetric(vertical: 8)),
                    onPressed: () => _act((s['id'] as num).toInt(), 'approve'),
                    child: Text(tr('✅ اعتماد وتطبيق', 'Approve')),
                  ),
                ),
                const SizedBox(width: 8),
                OutlinedButton(onPressed: () => _act((s['id'] as num).toInt(), 'reject'), child: Text(tr('رفض', 'Reject'))),
              ]),
            ),
        ]),
      ),
    );
  }

  Future<void> _act(int id, String action) async {
    try {
      await _api.subAction(id, action);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تمّ', 'Done'))));
        await _load();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: _crit));
    }
  }

  Future<void> _openCreate() async {
    final ok = await Navigator.push<bool>(
        context, MaterialPageRoute(builder: (_) => _SubCreate(projectId: _projectId!)));
    if (ok == true) _load();
  }

  InputDecoration _dec(String h) => InputDecoration(
      labelText: h, filled: true, fillColor: Colors.white, isDense: true,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(11)));
}

class _SubCreate extends StatefulWidget {
  final int projectId;
  const _SubCreate({required this.projectId});
  @override
  State<_SubCreate> createState() => _SubCreateState();
}

class _SubCreateState extends State<_SubCreate> {
  ApiClient get _api => context.read<AuthProvider>().api;
  Map? _meta;
  int? _absent, _substitute;
  String? _subName;
  String _rule = 'substitute';
  DateTime _from = DateTime.now();
  DateTime _to = DateTime.now();
  final _reason = TextEditingController();
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final m = await _api.subMeta(widget.projectId);
      if (mounted) setState(() => _meta = m);
    } catch (_) {}
  }

  Future<void> _save() async {
    if (_absent == null || _substitute == null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('اختر الغائب والبديل', 'Select both workers'))));
      return;
    }
    setState(() => _busy = true);
    try {
      String d(DateTime x) => '${x.year}-${x.month.toString().padLeft(2, '0')}-${x.day.toString().padLeft(2, '0')}';
      await _api.subCreate({
        'project_id': widget.projectId,
        'absent_employee_id': _absent,
        'substitute_employee_id': _substitute,
        'date_from': d(_from), 'date_to': d(_to),
        'reason': _reason.text, 'price_rule': _rule, 'submit': true,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('قُدّم طلب الإحلال', 'Submitted'))));
        Navigator.pop(context, true);
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: _crit));
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    final m = _meta;
    final absentW = (m?['absent_workers'] as List?) ?? [];
    final subs = (m?['substitutes'] as List?) ?? [];
    final rules = (m?['price_rules'] as List?) ?? [];
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(backgroundColor: _navy, foregroundColor: Colors.white, title: Text(tr('إرسال بديل', 'Send substitute'))),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: FilledButton.icon(
            style: FilledButton.styleFrom(backgroundColor: _sub, minimumSize: const Size.fromHeight(50)),
            onPressed: _busy ? null : _save,
            icon: const Icon(Icons.send_rounded),
            label: Text(tr('تقديم للاعتماد', 'Submit')),
          ),
        ),
      ),
      body: m == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(14), children: [
              Text('${m['project']?['name'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w900, color: _navy, fontSize: 15)),
              const SizedBox(height: 12),
              _dd(tr('العامل الغائب (X)', 'Absent (X)'), absentW, _absent, (v) => setState(() => _absent = v)),
              const SizedBox(height: 12),
              // العامل البديل: منتقي بحث في كل موظّفي الشركة (اسم ع/EN + بادج)
              InkWell(
                onTap: () => _pickSubstitute(subs),
                child: InputDecorator(
                  decoration: _dec(tr('العامل البديل (Y)', 'Substitute (Y)')).copyWith(
                      enabledBorder: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(11),
                          borderSide: const BorderSide(color: _sub, width: 1.5)),
                      suffixIcon: const Icon(Icons.search_rounded, color: _sub)),
                  child: Text(
                    _substitute == null ? tr('اضغط للبحث واختيار البديل', 'Tap to search') : (_subName ?? '#$_substitute'),
                    style: TextStyle(
                        fontWeight: FontWeight.w800,
                        color: _substitute == null ? _muted : _navy),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ),
              const SizedBox(height: 12),
              Row(children: [
                Expanded(child: _dateField(tr('من', 'From'), _from, (x) => setState(() => _from = x))),
                const SizedBox(width: 10),
                Expanded(child: _dateField(tr('إلى', 'To'), _to, (x) => setState(() => _to = x))),
              ]),
              const SizedBox(height: 12),
              DropdownButtonFormField<String>(
                value: _rule,
                decoration: _dec(tr('قاعدة التسعير', 'Price rule')),
                items: rules
                    .map((r) => DropdownMenuItem<String>(value: (r as Map)['id'] as String, child: Text('${r['name']}')))
                    .toList(),
                onChanged: (v) => setState(() => _rule = v ?? 'substitute'),
              ),
              const SizedBox(height: 12),
              TextField(controller: _reason, decoration: _dec(tr('سبب الغياب', 'Reason')), maxLines: 2),
            ]),
    );
  }

  Future<void> _pickSubstitute(List subs) async {
    final picked = await showModalBottomSheet<Map>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(18))),
      builder: (ctx) => _SubPicker(subs: subs),
    );
    if (picked != null && mounted) {
      setState(() {
        _substitute = (picked['id'] as num).toInt();
        _subName = '${picked['name']}';
      });
    }
  }

  Widget _dd(String label, List opts, int? val, ValueChanged<int?> onCh, {bool accent = false}) =>
      DropdownButtonFormField<int>(
        value: val,
        isExpanded: true,
        decoration: _dec(label).copyWith(
            enabledBorder: accent
                ? OutlineInputBorder(borderRadius: BorderRadius.circular(11), borderSide: const BorderSide(color: _sub, width: 1.5))
                : null),
        items: opts
            .map((o) => DropdownMenuItem<int>(
                value: (o as Map)['id'] as int, child: Text('${o['name']}', overflow: TextOverflow.ellipsis)))
            .toList(),
        onChanged: onCh,
      );

  Widget _dateField(String label, DateTime val, ValueChanged<DateTime> onCh) => InkWell(
        onTap: () async {
          final d = await showDatePicker(
              context: context, initialDate: val, firstDate: DateTime(2024), lastDate: DateTime(2030));
          if (d != null) onCh(d);
        },
        child: InputDecorator(
          decoration: _dec(label),
          child: Text('${val.year}-${val.month.toString().padLeft(2, '0')}-${val.day.toString().padLeft(2, '0')}',
              style: const TextStyle(fontWeight: FontWeight.w700)),
        ),
      );

  InputDecoration _dec(String h) => InputDecoration(
      labelText: h, filled: true, fillColor: Colors.white, isDense: true,
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(11)));
}

/// منتقي بحث لكل موظّفي الشركة — بالاسم العربي/الإنجليزي أو رقم البادج.
class _SubPicker extends StatefulWidget {
  final List subs;
  const _SubPicker({required this.subs});
  @override
  State<_SubPicker> createState() => _SubPickerState();
}

class _SubPickerState extends State<_SubPicker> {
  String _q = '';

  @override
  Widget build(BuildContext context) {
    final q = _q.trim().toLowerCase();
    final list = q.isEmpty
        ? widget.subs.take(60).toList()
        : widget.subs.where((e) {
            final m = e as Map;
            final n = '${m['name'] ?? ''}'.toLowerCase();
            final en = '${m['en'] ?? ''}'.toLowerCase();
            final b = '${m['badge'] ?? ''}'.toLowerCase();
            return n.contains(q) || en.contains(q) || b.contains(q);
          }).take(60).toList();
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: SizedBox(
        height: MediaQuery.of(context).size.height * 0.78,
        child: Column(children: [
          const SizedBox(height: 10),
          Container(width: 44, height: 4, decoration: BoxDecoration(color: const Color(0xFFCBD5E1), borderRadius: BorderRadius.circular(3))),
          Padding(
            padding: const EdgeInsets.fromLTRB(14, 12, 14, 8),
            child: TextField(
              autofocus: true,
              onChanged: (v) => setState(() => _q = v),
              decoration: InputDecoration(
                hintText: tr('🔍 ابحث بالاسم ع/EN أو رقم البادج…', '🔍 Search name or badge…'),
                filled: true, fillColor: const Color(0xFFF1F5F9), isDense: true,
                prefixIcon: const Icon(Icons.search_rounded, color: _sub),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
              ),
            ),
          ),
          Expanded(
            child: list.isEmpty
                ? Center(child: Text(tr('لا نتائج', 'No results'), style: const TextStyle(color: _muted)))
                : ListView.separated(
                    padding: const EdgeInsets.fromLTRB(10, 0, 10, 14),
                    itemCount: list.length,
                    separatorBuilder: (_, __) => const Divider(height: 1),
                    itemBuilder: (_, i) {
                      final m = list[i] as Map;
                      final badge = '${m['badge'] ?? ''}';
                      return ListTile(
                        dense: true,
                        title: Text('${m['name']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5)),
                        subtitle: Text('${badge.isNotEmpty ? '#$badge  ' : ''}${m['en'] ?? ''}',
                            style: const TextStyle(fontSize: 11, color: _muted)),
                        trailing: const Icon(Icons.chevron_left_rounded, color: _sub),
                        onTap: () => Navigator.pop(context, m),
                      );
                    },
                  ),
          ),
        ]),
      ),
    );
  }
}
