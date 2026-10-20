// شاشتا الجزاءات والمكافآت لمدير المشروع: قائمة + إنشاء + اعتماد + طباعة.
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'pms_shell.dart';

class PenaltiesScreen extends StatelessWidget {
  const PenaltiesScreen({super.key});
  @override
  Widget build(BuildContext context) => const _PbScreen(bonus: false);
}

class BonusesScreen extends StatelessWidget {
  const BonusesScreen({super.key});
  @override
  Widget build(BuildContext context) => const _PbScreen(bonus: true);
}

class _PbScreen extends StatefulWidget {
  final bool bonus;
  const _PbScreen({required this.bonus});
  @override
  State<_PbScreen> createState() => _PbScreenState();
}

class _PbScreenState extends State<_PbScreen> {
  late Future<Map<String, dynamic>> _f;

  bool get isBonus => widget.bonus;
  String get _title => isBonus ? tr('المكافآت', 'Bonuses') : tr('الجزاءات', 'Penalties');
  Color get _accent => isBonus ? Pms.green : Pms.violet;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    final api = context.read<AuthProvider>().api;
    _f = isBonus ? api.pmsBonuses() : api.pmsPenalties();
  }

  Color _stateColor(String st) {
    if (st == 'approved' || st == 'done') return Pms.green;
    if (st == 'refused' || st == 'cancelled') return Pms.red;
    return Pms.amber;
  }

  Future<void> _openReport(Map r) async {
    final api = context.read<AuthProvider>().api;
    final t = await api.token;
    final id = r['id'];
    final path = isBonus ? '/pms/bonus/$id/report' : '/pms/penalty/$id/report';
    final url = '${api.baseUrl}$path?token=${t ?? ''}';
    await launchUrl(Uri.parse(url), mode: LaunchMode.externalApplication);
  }

  Future<void> _doAction(Map r, String act) async {
    final api = context.read<AuthProvider>().api;
    try {
      if (isBonus) {
        await api.pmsBonusAction(r['id'] as int, act);
      } else {
        await api.pmsPenaltyAction(r['id'] as int, act);
      }
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(tr('تم تنفيذ الإجراء', 'Done')), backgroundColor: Pms.green));
        setState(_reload);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('$e'), backgroundColor: Pms.red));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: gIsRtl ? TextDirection.rtl : TextDirection.ltr,
      child: Scaffold(
        backgroundColor: Pms.bg,
        appBar: AppBar(title: Text(_title), backgroundColor: _accent, foregroundColor: Colors.white),
        floatingActionButton: FloatingActionButton.extended(
          backgroundColor: _accent,
          icon: const Icon(Icons.add, color: Colors.white),
          label: Text(tr('طلب جديد', 'New request'), style: const TextStyle(color: Colors.white)),
          onPressed: _openCreate,
        ),
        body: FutureBuilder<Map<String, dynamic>>(
          future: _f,
          builder: (context, snap) {
            if (snap.connectionState != ConnectionState.done) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return Center(child: Padding(padding: const EdgeInsets.all(24),
                  child: Text('${snap.error}', textAlign: TextAlign.center, style: const TextStyle(color: Pms.slate))));
            }
            final items = List<Map>.from((snap.data?['items'] as List?) ?? const []);
            if (items.isEmpty) {
              return Center(child: Text(tr('لا توجد طلبات', 'No requests'),
                  style: const TextStyle(color: Pms.slate)));
            }
            return RefreshIndicator(
              onRefresh: () async => setState(_reload),
              child: ListView.builder(
                padding: const EdgeInsets.fromLTRB(12, 12, 12, 90),
                itemCount: items.length,
                itemBuilder: (_, i) => _card(items[i]),
              ),
            );
          },
        ),
      ),
    );
  }

  Widget _card(Map r) {
    final st = (r['state'] ?? '').toString();
    final amount = dblOf(r['amount']);
    final cur = (r['currency'] ?? '').toString();
    final sub = isBonus
        ? '${r['type_label'] ?? ''} · ${r['pay_label'] ?? ''}'
        : '${r['category_label'] ?? ''} · ${r['settle_label'] ?? ''}';
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: Colors.white, borderRadius: BorderRadius.circular(14),
        border: Border.all(color: const Color(0xFFE5E7EB)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(r['employee']?.toString() ?? '—',
                  style: const TextStyle(fontWeight: FontWeight.w800, color: Pms.ink, fontSize: 15)),
              const SizedBox(height: 2),
              Text(r['name']?.toString() ?? '', style: const TextStyle(color: Pms.slate, fontSize: 12)),
            ])),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              decoration: BoxDecoration(color: _stateColor(st).withOpacity(.12), borderRadius: BorderRadius.circular(999)),
              child: Text(r['state_label']?.toString() ?? st,
                  style: TextStyle(color: _stateColor(st), fontWeight: FontWeight.w800, fontSize: 11.5)),
            ),
          ]),
          const SizedBox(height: 8),
          Row(children: [
            Text('${amount.toStringAsFixed(3)} $cur',
                style: TextStyle(fontWeight: FontWeight.w900, color: _accent, fontSize: 16)),
            const SizedBox(width: 10),
            Expanded(child: Text(sub, style: const TextStyle(color: Pms.slate, fontSize: 12), overflow: TextOverflow.ellipsis)),
          ]),
          if ((r['reason'] ?? '').toString().isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(r['reason'].toString(), style: const TextStyle(color: Pms.ink, fontSize: 12.5)),
          ],
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 6, children: [
            if (r['can_approve'] == true) _btn(tr('اعتماد', 'Approve'), Pms.green, () => _doAction(r, 'approve')),
            if (r['can_review'] == true) _btn(tr('بدء مراجعة', 'Start review'), Pms.amber, () => _doAction(r, 'review')),
            if (r['can_cash'] == true) _btn(isBonus ? tr('صرف نقدي', 'Pay cash') : tr('تحصيل نقدي', 'Collect cash'), Pms.green, () => _doAction(r, 'cash')),
            if (r['can_reject'] == true) _btn(tr('رفض', 'Reject'), Pms.red, () => _doAction(r, 'refuse')),
            _btn(tr('طباعة', 'Print'), Pms.slate, () => _openReport(r), outline: true),
          ]),
        ]),
      ),
    );
  }

  Widget _btn(String label, Color c, VoidCallback onTap, {bool outline = false}) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
        decoration: BoxDecoration(
          color: outline ? Colors.transparent : c.withOpacity(.12),
          border: Border.all(color: c.withOpacity(outline ? .5 : 0)),
          borderRadius: BorderRadius.circular(8),
        ),
        child: Text(label, style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 12.5)),
      ),
    );
  }

  // ---------- نموذج الإنشاء ----------
  Future<void> _openCreate() async {
    Map<String, dynamic> data;
    try {
      data = await _f;
    } catch (_) {
      return;
    }
    final meta = Map<String, dynamic>.from(data['meta'] ?? {});
    final workers = List<Map>.from(meta['workers'] ?? const []);
    if (workers.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(tr('لا يوجد عمّال ضمن مشاريعك', 'No workers in your projects'))));
      return;
    }
    final ok = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(18))),
      builder: (_) => _CreateSheet(bonus: isBonus, meta: meta, accent: _accent),
    );
    if (ok == true && mounted) setState(_reload);
  }
}

class _CreateSheet extends StatefulWidget {
  final bool bonus;
  final Map<String, dynamic> meta;
  final Color accent;
  const _CreateSheet({required this.bonus, required this.meta, required this.accent});
  @override
  State<_CreateSheet> createState() => _CreateSheetState();
}

class _CreateSheetState extends State<_CreateSheet> {
  int? _emp;
  String? _s1; // category (penalty) / type (bonus)
  String? _s2; // level (penalty) / recurrence (bonus)
  String? _s3; // settle_mode (penalty) / payment_method (bonus)
  final _amount = TextEditingController();
  final _reason = TextEditingController();
  bool _busy = false;

  bool get isBonus => widget.bonus;
  List<Map> get _workers => List<Map>.from(widget.meta['workers'] ?? const []);
  List<Map> get _list1 => List<Map>.from(widget.meta[isBonus ? 'types' : 'categories'] ?? const []);
  List<Map> get _list2 => List<Map>.from(widget.meta[isBonus ? 'recurrences' : 'levels'] ?? const []);
  List<Map> get _list3 => List<Map>.from(widget.meta[isBonus ? 'pays' : 'settle_modes'] ?? const []);

  @override
  void initState() {
    super.initState();
    if (_list1.isNotEmpty) _s1 = _list1.first['value']?.toString();
    if (_list3.isNotEmpty) _s3 = _list3.first['value']?.toString();
    if (isBonus && _list2.isNotEmpty) _s2 = _list2.first['value']?.toString();
  }

  Future<void> _submit() async {
    if (_emp == null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('اختر العامل', 'Choose a worker'))));
      return;
    }
    final amt = double.tryParse(_amount.text.trim()) ?? 0;
    if (amt <= 0) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('أدخل قيمة صحيحة', 'Enter a valid amount'))));
      return;
    }
    setState(() => _busy = true);
    final api = context.read<AuthProvider>().api;
    final vals = <String, dynamic>{'amount': amt, 'reason': _reason.text.trim(), 'submit': true};
    if (isBonus) {
      vals['bonus_type'] = _s1;
      vals['recurrence'] = _s2;
      vals['payment_method'] = _s3;
    } else {
      vals['violation_category'] = _s1;
      if (_s2 != null) vals['escalation_level'] = _s2;
      vals['settle_mode'] = _s3;
    }
    try {
      if (isBonus) {
        await api.pmsBonusCreate(_emp!, vals);
      } else {
        await api.pmsPenaltyCreate(_emp!, vals);
      }
      if (mounted) Navigator.pop(context, true);
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Pms.red));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: gIsRtl ? TextDirection.rtl : TextDirection.ltr,
      child: Padding(
        padding: EdgeInsets.only(
            left: 16, right: 16, top: 16,
            bottom: MediaQuery.of(context).viewInsets.bottom + 16),
        child: SingleChildScrollView(
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Center(child: Text(isBonus ? tr('طلب مكافأة جديد', 'New bonus request') : tr('طلب جزاء جديد', 'New penalty request'),
                style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: widget.accent))),
            const SizedBox(height: 14),
            _dropdownInt(tr('العامل', 'Worker'), _emp,
                _workers.map((w) => DropdownMenuItem<int>(value: w['id'] as int,
                    child: Text('${w['name']}${(w['dept'] ?? '').toString().isNotEmpty ? ' · ${w['dept']}' : ''}',
                        overflow: TextOverflow.ellipsis))).toList(),
                (v) => setState(() => _emp = v)),
            const SizedBox(height: 10),
            _dropdownStr(isBonus ? tr('نوع المكافأة', 'Bonus type') : tr('تصنيف المخالفة', 'Violation category'), _s1, _list1, (v) => setState(() => _s1 = v)),
            const SizedBox(height: 10),
            _dropdownStr(isBonus ? tr('التكرار', 'Recurrence') : tr('درجة الجزاء', 'Penalty degree'), _s2, _list2, (v) => setState(() => _s2 = v)),
            const SizedBox(height: 10),
            _dropdownStr(isBonus ? tr('طريقة الصرف', 'Payment method') : tr('طريقة التسوية', 'Settlement'), _s3, _list3, (v) => setState(() => _s3 = v)),
            const SizedBox(height: 10),
            TextField(controller: _amount, keyboardType: const TextInputType.numberWithOptions(decimal: true),
                decoration: _dec(isBonus ? tr('قيمة المكافأة', 'Bonus amount') : tr('قيمة الجزاء', 'Penalty amount'))),
            const SizedBox(height: 10),
            TextField(controller: _reason, maxLines: 2, decoration: _dec(tr('السبب / المبرّر', 'Reason'))),
            const SizedBox(height: 16),
            SizedBox(height: 48, child: ElevatedButton(
              onPressed: _busy ? null : _submit,
              style: ElevatedButton.styleFrom(backgroundColor: widget.accent, foregroundColor: Colors.white),
              child: _busy
                  ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : Text(tr('تقديم الطلب', 'Submit'), style: const TextStyle(fontWeight: FontWeight.w800)),
            )),
          ]),
        ),
      ),
    );
  }

  InputDecoration _dec(String label) => InputDecoration(
        labelText: label, filled: true, fillColor: Pms.bg,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none),
      );

  Widget _dropdownInt(String label, int? val, List<DropdownMenuItem<int>> items, ValueChanged<int?> onCh) =>
      DropdownButtonFormField<int>(value: val, isExpanded: true, items: items, onChanged: onCh, decoration: _dec(label));

  Widget _dropdownStr(String label, String? val, List<Map> opts, ValueChanged<String?> onCh) {
    if (opts.isEmpty) return const SizedBox.shrink();
    return DropdownButtonFormField<String>(
      value: val, isExpanded: true, decoration: _dec(label),
      items: opts.map((o) => DropdownMenuItem<String>(value: o['value']?.toString(),
          child: Text(o['label']?.toString() ?? '', overflow: TextOverflow.ellipsis))).toList(),
      onChanged: onCh,
    );
  }
}
