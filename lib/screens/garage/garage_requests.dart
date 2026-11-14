import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/api_client.dart';
import '../../core/i18n.dart';
import 'garage_home.dart' show kGrgNavy, kGrgBg, kGrgInk, kGrgGrey, kGrgGold, grgNum;

Color _stColor(String s) {
  switch (s) {
    case 'draft':
      return const Color(0xFF94A3B8);
    case 'requested':
    case 'tech_approved':
      return const Color(0xFFE08A00);
    case 'mgr_approved':
    case 'fleet_approved':
      return const Color(0xFF2563EB);
    case 'in_progress':
      return const Color(0xFF0E8A8A);
    case 'done':
    case 'closed':
      return const Color(0xFF16A34A);
    case 'cancelled':
      return const Color(0xFFDC3030);
    default:
      return kGrgGrey;
  }
}

/// قائمة طلبات الصيانة — بحث + فلترة + إنشاء.
class GarageRequestsScreen extends StatefulWidget {
  const GarageRequestsScreen({super.key});
  @override
  State<GarageRequestsScreen> createState() => _GarageRequestsScreenState();
}

class _GarageRequestsScreenState extends State<GarageRequestsScreen> {
  ApiClient get _api => context.read<AuthProvider>().api;
  List _rows = const [];
  bool _loading = true;
  String _state = 'open';
  String _q = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final r = await _api.grgRequests(state: _state == 'all' ? null : _state, q: _q.isEmpty ? null : _q);
      if (mounted) setState(() => _rows = r);
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    return Scaffold(
      backgroundColor: kGrgBg,
      appBar: AppBar(
        backgroundColor: kGrgNavy,
        foregroundColor: Colors.white,
        title: Text(tr('طلبات الصيانة', 'Maintenance requests')),
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))],
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: kGrgGold,
        foregroundColor: Colors.white,
        onPressed: () async {
          final ok = await Navigator.push<bool>(context, MaterialPageRoute(builder: (_) => const GarageRequestCreate()));
          if (ok == true) _load();
        },
        icon: const Icon(Icons.add_rounded),
        label: Text(tr('طلب جديد', 'New')),
      ),
      body: Column(children: [
        Container(
          color: Colors.white,
          padding: const EdgeInsets.fromLTRB(12, 8, 12, 8),
          child: Column(children: [
            TextField(
              onSubmitted: (v) {
                _q = v;
                _load();
              },
              style: const TextStyle(fontSize: 13),
              decoration: InputDecoration(
                  hintText: tr('بحث باسم المركبة…', 'Search by vehicle…'),
                  prefixIcon: const Icon(Icons.search_rounded, size: 19),
                  isDense: true,
                  filled: true,
                  fillColor: const Color(0xFFF1F4F8),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)),
            ),
            const SizedBox(height: 8),
            Row(children: [
              _chip('open', tr('مفتوحة', 'Open')),
              const SizedBox(width: 8),
              _chip('all', tr('الكل', 'All')),
            ]),
          ]),
        ),
        Expanded(
          child: _loading
              ? const Center(child: CircularProgressIndicator(color: kGrgNavy))
              : _rows.isEmpty
                  ? Center(child: Text(tr('لا طلبات', 'No requests'), style: const TextStyle(color: kGrgGrey)))
                  : RefreshIndicator(
                      onRefresh: _load,
                      child: ListView.builder(
                        padding: const EdgeInsets.fromLTRB(12, 10, 12, 90),
                        itemCount: _rows.length,
                        itemBuilder: (_, i) => _card(Map<String, dynamic>.from(_rows[i] as Map)),
                      ),
                    ),
        ),
      ]),
    );
  }

  Widget _chip(String v, String label) {
    final on = _state == v;
    return GestureDetector(
      onTap: () {
        setState(() => _state = v);
        _load();
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 7),
        decoration: BoxDecoration(
            color: on ? kGrgNavy : const Color(0xFFEDF1F7),
            borderRadius: BorderRadius.circular(20)),
        child: Text(label, style: TextStyle(color: on ? Colors.white : kGrgGrey, fontWeight: FontWeight.w700, fontSize: 12.5)),
      ),
    );
  }

  Widget _card(Map<String, dynamic> r) {
    final st = '${r['state']}';
    final c = _stColor(st);
    return Padding(
      padding: const EdgeInsets.only(bottom: 9),
      child: Material(
        color: Colors.white,
        borderRadius: BorderRadius.circular(13),
        child: InkWell(
          borderRadius: BorderRadius.circular(13),
          onTap: () async {
            final ch = await Navigator.push<bool>(
                context, MaterialPageRoute(builder: (_) => GarageRequestDetail(id: r['id'] as int)));
            if (ch == true) _load();
          },
          child: Padding(
            padding: const EdgeInsets.all(13),
            child: Row(children: [
              Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${r['vehicle']}', style: const TextStyle(fontWeight: FontWeight.w800, color: kGrgInk, fontSize: 13.5)),
                const SizedBox(height: 3),
                Text('${(r['desc'] as String?)?.isNotEmpty == true ? r['desc'] : (r['type'] ?? '—')}',
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: kGrgGrey, fontSize: 11.5)),
                const SizedBox(height: 3),
                Text('${r['date']}', style: const TextStyle(color: Color(0xFF9AA6B8), fontSize: 10.5)),
              ])),
              Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                  decoration: BoxDecoration(color: c.withValues(alpha: 0.13), borderRadius: BorderRadius.circular(9)),
                  child: Text('${r['state_label']}', style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 10.5)),
                ),
                const SizedBox(height: 7),
                if (((r['cost'] as num?)?.toDouble() ?? 0) > 0)
                  Text(grgNum(r['cost']), style: const TextStyle(fontWeight: FontWeight.w800, color: kGrgInk, fontSize: 12.5)),
              ]),
            ]),
          ),
        ),
      ),
    );
  }
}

/// تفاصيل الطلب + أزرار الإجراء حسب الحالة.
class GarageRequestDetail extends StatefulWidget {
  const GarageRequestDetail({super.key, required this.id});
  final int id;
  @override
  State<GarageRequestDetail> createState() => _GarageRequestDetailState();
}

class _GarageRequestDetailState extends State<GarageRequestDetail> {
  ApiClient get _api => context.read<AuthProvider>().api;
  Map<String, dynamic>? _d;
  bool _loading = true;
  bool _changed = false;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final d = await _api.grgRequest(widget.id);
      if (mounted) setState(() => _d = d);
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  // الإجراء التالي حسب الحالة: (action, label, color)
  List<(String, String, Color)> _actionsFor(String s) {
    switch (s) {
      case 'draft':
        return [('submit', tr('تقديم للاعتماد', 'Submit'), const Color(0xFF2563EB))];
      case 'requested':
        return [('tech_approve', tr('اعتماد فني', 'Tech approve'), const Color(0xFFE08A00))];
      case 'tech_approved':
        return [('mgr_approve', tr('اعتماد مدير الكراج', 'Manager approve'), const Color(0xFF2563EB))];
      case 'mgr_approved':
        return [('fleet_approve', tr('اعتماد مدير الفليت', 'Fleet approve'), const Color(0xFF7C3AED))];
      case 'fleet_approved':
        return [('start', tr('بدء التنفيذ', 'Start'), const Color(0xFF0E8A8A))];
      case 'in_progress':
        return [('done', tr('إنهاء التنفيذ', 'Mark done'), const Color(0xFF16A34A))];
      case 'done':
        return [('close', tr('إقفال الطلب', 'Close'), const Color(0xFF334155))];
      case 'cancelled':
        return [('reset', tr('إعادة لمسودّة', 'Reset to draft'), const Color(0xFF64748B))];
      default:
        return const [];
    }
  }

  Future<void> _act(String action) async {
    setState(() => _busy = true);
    try {
      final d = await _api.grgRequestAction(widget.id, action);
      _changed = true;
      if (mounted) setState(() => _d = d);
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تعذّر تنفيذ الإجراء', 'Action failed'))));
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    final d = _d;
    final st = d == null ? '' : '${d['state']}';
    return PopScope(
      canPop: true,
      onPopInvokedWithResult: (didPop, _) {},
      child: Scaffold(
        backgroundColor: kGrgBg,
        appBar: AppBar(
          backgroundColor: kGrgNavy,
          foregroundColor: Colors.white,
          title: Text(tr('طلب صيانة', 'Request')),
          leading: IconButton(icon: const Icon(Icons.arrow_back), onPressed: () => Navigator.pop(context, _changed)),
        ),
        body: _loading
            ? const Center(child: CircularProgressIndicator(color: kGrgNavy))
            : d == null
                ? Center(child: Text(tr('تعذّر التحميل', 'Load failed'), style: const TextStyle(color: kGrgGrey)))
                : ListView(padding: const EdgeInsets.fromLTRB(14, 16, 14, 28), children: [
                    _headerCard(d, st),
                    const SizedBox(height: 14),
                    _section(tr('البيانات', 'Details'), [
                      _kv(tr('المركبة', 'Vehicle'), '${d['vehicle']}'),
                      _kv(tr('النوع', 'Type'), '${d['type'] ?? '—'}'),
                      _kv(tr('الفنّي', 'Technician'), '${(d['technician'] as String?)?.isNotEmpty == true ? d['technician'] : '—'}'),
                      _kv(tr('ساعات العمل', 'Labor hrs'), '${d['labor_hours'] ?? 0}'),
                      _kv(tr('العهدة', 'Custody'), '${(d['custody'] as String?)?.isNotEmpty == true ? d['custody'] : '—'}'),
                      _kv(tr('التكلفة', 'Cost'), grgNum(d['cost'])),
                      if ((d['desc'] as String?)?.isNotEmpty == true) _kv(tr('الوصف', 'Description'), '${d['desc']}'),
                    ]),
                    if ((d['damages'] as List?)?.isNotEmpty == true) ...[
                      const SizedBox(height: 14),
                      _damages(List.from(d['damages'] as List)),
                    ],
                    const SizedBox(height: 14),
                    _signatures(Map<String, dynamic>.from(d['signatures'] as Map? ?? {})),
                  ]),
        bottomNavigationBar: (d == null || _actionsFor(st).isEmpty)
            ? null
            : SafeArea(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Row(children: [
                    for (final a in _actionsFor(st))
                      Expanded(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 4),
                          child: ElevatedButton(
                            onPressed: _busy ? null : () => _act(a.$1),
                            style: ElevatedButton.styleFrom(backgroundColor: a.$3, foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(vertical: 13)),
                            child: _busy ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : Text(a.$2, style: const TextStyle(fontWeight: FontWeight.w800)),
                          ),
                        ),
                      ),
                    if (st != 'cancelled' && st != 'closed' && st != 'done')
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 4),
                        child: OutlinedButton(
                          onPressed: _busy ? null : () => _act('cancel'),
                          style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFDC3030), padding: const EdgeInsets.symmetric(vertical: 13, horizontal: 12)),
                          child: Text(tr('إلغاء', 'Cancel'), style: const TextStyle(fontWeight: FontWeight.w800)),
                        ),
                      ),
                  ]),
                ),
              ),
      ),
    );
  }

  Widget _headerCard(Map<String, dynamic> d, String st) {
    final c = _stColor(st);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(15), border: Border.all(color: const Color(0xFFE2E8F0))),
      child: Row(children: [
        Container(width: 46, height: 46, decoration: BoxDecoration(color: c.withValues(alpha: 0.13), borderRadius: BorderRadius.circular(12)), child: Icon(Icons.build_rounded, color: c)),
        const SizedBox(width: 12),
        Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${d['vehicle']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: kGrgInk)),
          const SizedBox(height: 4),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(color: c.withValues(alpha: 0.13), borderRadius: BorderRadius.circular(9)),
            child: Text('${d['state_label']}', style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 11.5)),
          ),
        ])),
      ]),
    );
  }

  Widget _section(String title, List<Widget> rows) => Container(
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: const Color(0xFFE2E8F0))),
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Padding(padding: const EdgeInsets.fromLTRB(14, 12, 14, 6), child: Text(title, style: const TextStyle(fontWeight: FontWeight.w900, color: kGrgNavy, fontSize: 13.5))),
          ...rows,
          const SizedBox(height: 6),
        ]),
      );

  Widget _kv(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 6),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 110, child: Text(k, style: const TextStyle(color: kGrgGrey, fontSize: 12))),
          Expanded(child: Text(v, style: const TextStyle(color: kGrgInk, fontWeight: FontWeight.w700, fontSize: 12.5))),
        ]),
      );

  Widget _damages(List dm) => _section(tr('الأعطال', 'Damages'),
      dm.map((x) {
        final m = Map<String, dynamic>.from(x as Map);
        return _kv('${m['name']}', '${grgNum(m['cost'])}${(m['how'] as String?)?.isNotEmpty == true ? ' · ${m['how']}' : ''}');
      }).toList());

  Widget _signatures(Map<String, dynamic> s) => _section(tr('التواقيع', 'Signatures'), [
        _kv(tr('مقدّم الطلب', 'Requested'), '${(s['req'] as String?)?.isNotEmpty == true ? s['req'] : '—'}'),
        _kv(tr('اعتماد فني', 'Tech'), '${(s['tech'] as String?)?.isNotEmpty == true ? s['tech'] : '—'}'),
        _kv(tr('مدير الكراج', 'Manager'), '${(s['mgr'] as String?)?.isNotEmpty == true ? s['mgr'] : '—'}'),
        _kv(tr('مدير الفليت', 'Fleet'), '${(s['fleet'] as String?)?.isNotEmpty == true ? s['fleet'] : '—'}'),
      ]);
}

/// إنشاء طلب صيانة — منتقي مركبة/فنّي typeahead + وصف.
class GarageRequestCreate extends StatefulWidget {
  const GarageRequestCreate({super.key});
  @override
  State<GarageRequestCreate> createState() => _GarageRequestCreateState();
}

class _GarageRequestCreateState extends State<GarageRequestCreate> {
  ApiClient get _api => context.read<AuthProvider>().api;
  List _vehicles = const [];
  List _techs = const [];
  bool _loading = true;
  bool _busy = false;
  int? _vehicleId;
  int? _techId;
  final _desc = TextEditingController();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final m = await _api.grgRequestMeta();
      if (mounted) {
        setState(() {
          _vehicles = (m['vehicles'] as List?) ?? const [];
          _techs = (m['technicians'] as List?) ?? const [];
        });
      }
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override
  void dispose() {
    _desc.dispose();
    super.dispose();
  }

  Future<void> _save(bool submit) async {
    if (_vehicleId == null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('اختر المركبة', 'Select a vehicle'))));
      return;
    }
    setState(() => _busy = true);
    try {
      await _api.grgCreateRequest({
        'vehicle_id': _vehicleId,
        'description': _desc.text.trim(),
        if (_techId != null) 'technician_id': _techId,
        'submit': submit,
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(submit ? tr('تم الإنشاء والتقديم', 'Created & submitted') : tr('حُفظت كمسودّة', 'Saved as draft'))));
        Navigator.pop(context, true);
      }
    } on ApiException catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.message)));
    } catch (_) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تعذّر الحفظ', 'Save failed'))));
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    return Scaffold(
      backgroundColor: kGrgBg,
      appBar: AppBar(backgroundColor: kGrgNavy, foregroundColor: Colors.white, title: Text(tr('طلب صيانة جديد', 'New request'))),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: kGrgNavy))
          : ListView(padding: const EdgeInsets.all(16), children: [
              _label(tr('المركبة', 'Vehicle')),
              _typeahead(_vehicles, (id) => _vehicleId = id, tr('اكتب اسم/لوحة المركبة…', 'Type vehicle name/plate…')),
              const SizedBox(height: 16),
              _label(tr('الفنّي (اختياري)', 'Technician (optional)')),
              _typeahead(_techs, (id) => _techId = id, tr('اكتب اسم الفنّي…', 'Type technician…')),
              const SizedBox(height: 16),
              _label(tr('الوصف', 'Description')),
              TextField(
                controller: _desc,
                maxLines: 3,
                decoration: InputDecoration(
                    hintText: tr('وصف العطل/الصيانة…', 'Describe the issue…'),
                    filled: true,
                    fillColor: Colors.white,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12))),
              ),
              const SizedBox(height: 24),
              Row(children: [
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _busy ? null : () => _save(false),
                    style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF0E7490), foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(vertical: 14)),
                    icon: const Icon(Icons.save_rounded, size: 18),
                    label: Text(tr('حفظ كمسودّة', 'Save draft')),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: ElevatedButton.icon(
                    onPressed: _busy ? null : () => _save(true),
                    style: ElevatedButton.styleFrom(backgroundColor: kGrgGold, foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(vertical: 14)),
                    icon: const Icon(Icons.send_rounded, size: 18),
                    label: Text(tr('حفظ وتقديم', 'Submit')),
                  ),
                ),
              ]),
            ]),
    );
  }

  Widget _label(String t) => Padding(padding: const EdgeInsets.only(bottom: 6), child: Align(alignment: Alignment.centerRight, child: Text(t, style: const TextStyle(fontWeight: FontWeight.w800, color: kGrgInk, fontSize: 13))));

  Widget _typeahead(List opts, void Function(int?) onPick, String hint) {
    return Autocomplete<Map>(
      displayStringForOption: (o) => '${o['name']}',
      optionsBuilder: (v) {
        final q = v.text.trim().toLowerCase();
        if (q.isEmpty) return opts.map((e) => Map.from(e as Map)).take(40);
        return opts
            .map((e) => Map.from(e as Map))
            .where((e) => '${e['name']}'.toLowerCase().contains(q))
            .take(40);
      },
      onSelected: (o) => onPick(o['id'] as int?),
      fieldViewBuilder: (ctx, ctrl, focus, onSubmit) => TextField(
        controller: ctrl,
        focusNode: focus,
        onChanged: (_) => onPick(null),
        decoration: InputDecoration(
            hintText: hint,
            prefixIcon: const Icon(Icons.search_rounded, size: 19),
            filled: true,
            fillColor: Colors.white,
            isDense: true,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12))),
      ),
    );
  }
}
