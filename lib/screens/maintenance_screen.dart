import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'searchable_picker.dart';

/// The client's professional Maintenance console — dashboard KPIs, fault/breakdown
/// reports (raise → convert to work order), periodic inspections with checklists,
/// and the spare-parts store. Scoped to the client's own facilities.
class MaintenanceScreen extends StatefulWidget {
  const MaintenanceScreen({super.key});
  @override
  State<MaintenanceScreen> createState() => _MaintenanceScreenState();
}

// Amber read as a warning on every screen it touched — a maintenance service
// is not a permanent alert. Steel blue carries the engineering feel and
// leaves amber free to mean what it means everywhere else: attention needed.
const _accent = Color(0xFF1E5F8C);
const _accentDark = Color(0xFF12405F);
const _navy = Color(0xFF0E3A5F);

const _sevColors = {
  'low': Color(0xFF64748B), 'medium': Color(0xFF0891B2),
  'high': Color(0xFFF59E0B), 'critical': Color(0xFFE5484D),
};
const _stateColors = {
  'reported': Color(0xFF0891B2), 'diagnosed': Color(0xFF7C3AED),
  'in_progress': Color(0xFFF7A23B), 'resolved': Color(0xFF16A34A),
  'closed': Color(0xFF64748B), 'cancelled': Color(0xFF94A3B8),
};

class _MaintenanceScreenState extends State<MaintenanceScreen> {
  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 4,
      child: Scaffold(
        backgroundColor: const Color(0xFFF4F6FA),
        appBar: AppBar(
          backgroundColor: _accent,
          title: Text(tr('الصيانة', 'Maintenance'), style: const TextStyle(fontWeight: FontWeight.w900)),
          bottom: TabBar(
            isScrollable: true,
            indicatorColor: Colors.white,
            indicatorWeight: 3,
            labelColor: Colors.white,
            unselectedLabelColor: Colors.white70,
            labelStyle: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5),
            tabs: [
              Tab(text: tr('لوحة', 'Dashboard')),
              Tab(text: tr('الأعطال', 'Faults')),
              Tab(text: tr('الفحوصات', 'Inspections')),
              Tab(text: tr('المخزن', 'Parts')),
            ],
          ),
        ),
        body: const TabBarView(children: [
          _DashboardTab(), _FaultsTab(), _InspectionsTab(), _PartsTab(),
        ]),
      ),
    );
  }
}

// ============================================================ dashboard =====
class _DashboardTab extends StatefulWidget {
  const _DashboardTab();
  @override
  State<_DashboardTab> createState() => _DashboardTabState();
}

class _DashboardTabState extends State<_DashboardTab> with AutomaticKeepAliveClientMixin {
  Map<String, dynamic>? _s;
  String? _err;
  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final s = await context.read<AuthProvider>().api.maintSummary();
      if (mounted) setState(() => _s = s);
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    if (_err != null) return Center(child: Text(_err!, style: const TextStyle(color: Colors.grey)));
    if (_s == null) return const Center(child: CircularProgressIndicator(color: _accent));
    if (_s!['available'] == false) {
      return Center(child: Text(tr('خدمة الصيانة غير مفعّلة', 'Maintenance service not enabled'),
          style: const TextStyle(color: Colors.grey)));
    }
    final s = _s!;
    final byDep = (s['by_department'] as List?) ?? const [];
    return RefreshIndicator(
      color: _accent,
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.all(14), children: [
        _heroBanner(s),
        const SizedBox(height: 14),
        GridView.count(
          crossAxisCount: 3, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
          mainAxisSpacing: 10, crossAxisSpacing: 10, childAspectRatio: 0.95,
          children: [
            StatCard(label: tr('أعطال مفتوحة', 'Open faults'), value: _i(s['faults_open']), color: const Color(0xFF0891B2), icon: Icons.report_problem_rounded, onTap: () => _openFaults('open')),
            StatCard(label: tr('حرجة', 'Critical'), value: _i(s['faults_critical']), color: const Color(0xFFE5484D), icon: Icons.priority_high_rounded, onTap: () => _openFaults('open')),
            StatCard(label: tr('تم الإصلاح', 'Resolved'), value: _i(s['faults_resolved']), color: const Color(0xFF16A34A), icon: Icons.check_circle_rounded, onTap: () => _openFaults('resolved')),
            StatCard(label: tr('فحوصات مستحقة', 'Due checks'), value: _i(s['inspections_due']), color: const Color(0xFFF59E0B), icon: Icons.event_available_rounded, onTap: () => DefaultTabController.of(context).animateTo(2)),
            StatCard(label: tr('قطع منخفضة', 'Low parts'), value: _i(s['parts_low']), color: const Color(0xFF7C3AED), icon: Icons.inventory_2_rounded, onTap: () => DefaultTabController.of(context).animateTo(3)),
            StatCard(label: tr('إجمالي الأعطال', 'Total faults'), value: _i(s['faults_total']), color: _navy, icon: Icons.build_circle_rounded, onTap: () => _openFaults('all')),
          ],
        ),
        const SizedBox(height: 8),
        _infoRow(Icons.timelapse_rounded, tr('ساعات التعطّل', 'Downtime hours'), '${s['downtime_hours'] ?? 0}', const Color(0xFFE5484D)),
        _infoRow(Icons.payments_rounded, tr('قيمة مخزون القطع', 'Parts stock value'), '${s['parts_value'] ?? 0} ${tr('د.ك', 'KWD')}', const Color(0xFF16A34A)),
        const SizedBox(height: 16),
        if (byDep.isNotEmpty) ...[
          _sectionTitle(Icons.account_tree_rounded, tr('حسب القسم', 'By department')),
          const SizedBox(height: 8),
          for (final d in byDep) _depBar(d),
        ],
        const SizedBox(height: 16),
        FilledButton.icon(
          style: FilledButton.styleFrom(backgroundColor: _accent, minimumSize: const Size.fromHeight(52)),
          onPressed: _newFault,
          icon: const Icon(Icons.add_alert_rounded),
          label: Text(tr('بلاغ عطل جديد', 'Report a fault'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
        ),
        const SizedBox(height: 30),
      ]),
    );
  }

  void _openFaults(String state) {
    DefaultTabController.of(context).animateTo(1);
  }

  Future<void> _newFault() async {
    final ok = await MaintFaultCreateSheet.open(context);
    if (ok == true) _load();
  }

  Widget _heroBanner(Map s) => CustomPaint(
        painter: const BrandPattern(opacity: 0.06),
        child: Container(
          padding: const EdgeInsets.fromLTRB(18, 18, 18, 18),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(18),
            gradient: LinearGradient(colors: [_accent, Color.lerp(_accent, Colors.black, 0.4)!],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
          ),
          child: Row(children: [
            Container(width: 52, height: 52, alignment: Alignment.center,
                decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(14)),
                child: const Text('🛠️', style: TextStyle(fontSize: 26))),
            const SizedBox(width: 14),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(tr('إدارة الصيانة', 'Maintenance management'),
                  style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
              const SizedBox(height: 4),
              Text(tr('${s['faults_open'] ?? 0} عطل مفتوح · ${s['inspections_due'] ?? 0} فحص مستحق',
                      '${s['faults_open'] ?? 0} open · ${s['inspections_due'] ?? 0} checks due'),
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.92), fontSize: 12.5)),
            ])),
          ]),
        ),
      );

  Widget _depBar(Map d) {
    final total = _i(d['total']), open = _i(d['open']);
    final frac = total == 0 ? 0.0 : open / total;
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.grey.shade200)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('${d['name']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5, color: _navy))),
          Text(tr('$open مفتوح / $total', '$open open / $total'),
              style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600, fontWeight: FontWeight.w700)),
        ]),
        const SizedBox(height: 8),
        ClipRRect(borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(value: frac, minHeight: 7,
                backgroundColor: Colors.grey.shade200,
                valueColor: AlwaysStoppedAnimation(open > 0 ? _accent : const Color(0xFF16A34A)))),
      ]),
    );
  }

  Widget _infoRow(IconData ic, String label, String val, Color c) => Container(
        margin: const EdgeInsets.only(top: 8),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
            border: Border.all(color: Colors.grey.shade200)),
        child: Row(children: [
          Icon(ic, size: 20, color: c), const SizedBox(width: 10),
          Expanded(child: Text(label, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: _navy))),
          Text(val, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: c)),
        ]),
      );
}

// ============================================================ faults ========
class _FaultsTab extends StatefulWidget {
  const _FaultsTab();
  @override
  State<_FaultsTab> createState() => _FaultsTabState();
}

class _FaultsTabState extends State<_FaultsTab> with AutomaticKeepAliveClientMixin {
  Future<List<dynamic>>? _future;
  String _state = 'open';
  String _q = '';
  @override
  bool get wantKeepAlive => true;

  static const _filters = [
    ('open', 'مفتوحة', 'Open'), ('all', 'الكل', 'All'),
    ('reported', 'مُبلَّغة', 'Reported'), ('in_progress', 'قيد الإصلاح', 'In progress'),
    ('resolved', 'تم الإصلاح', 'Resolved'), ('closed', 'مغلقة', 'Closed'),
  ];

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    setState(() => _future = context.read<AuthProvider>().api.maintFaults(state: _state, q: _q));
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: _accent,
        onPressed: () async {
          final ok = await MaintFaultCreateSheet.open(context);
          if (ok == true) _load();
        },
        icon: const Icon(Icons.add_alert_rounded),
        label: Text(tr('بلاغ', 'Report'), style: const TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(12, 12, 12, 6),
          child: TextField(
            onChanged: (v) => _q = v,
            onSubmitted: (_) => _load(),
            decoration: InputDecoration(
              hintText: tr('بحث بالعنوان أو الرقم أو الأصل…', 'Search title, ref or asset…'),
              prefixIcon: const Icon(Icons.search_rounded, size: 20),
              suffixIcon: IconButton(icon: const Icon(Icons.tune_rounded, size: 20), onPressed: _load),
              filled: true, fillColor: Colors.white, isDense: true,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
              enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
            ),
          ),
        ),
        SizedBox(height: 40, child: ListView(
          scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 10),
          children: [for (final f in _filters) _chip(f)],
        )),
        Expanded(child: FutureBuilder<List<dynamic>>(
          future: _future,
          builder: (c, snap) {
            if (snap.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator(color: _accent));
            if (snap.hasError) return Center(child: Text('${snap.error}', style: const TextStyle(color: Colors.grey)));
            final list = snap.data ?? const [];
            if (list.isEmpty) return _empty(tr('لا توجد بلاغات', 'No faults'));
            return RefreshIndicator(
              color: _accent,
              onRefresh: () async => _load(),
              child: ListView.builder(
                padding: const EdgeInsets.fromLTRB(12, 4, 12, 90),
                itemCount: list.length,
                itemBuilder: (c, i) => _faultCard(list[i] as Map),
              ),
            );
          },
        )),
      ]),
    );
  }

  Widget _chip((String, String, String) f) {
    final on = _state == f.$1;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
      child: ChoiceChip(
        selected: on,
        label: Text(tr(f.$2, f.$3), style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: on ? Colors.white : _navy)),
        selectedColor: _accent,
        backgroundColor: Colors.white,
        side: BorderSide(color: on ? _accent : Colors.grey.shade300),
        onSelected: (_) { setState(() => _state = f.$1); _load(); },
      ),
    );
  }

  Widget _faultCard(Map f) {
    final sev = '${f['severity']}';
    final sc = _sevColors[sev] ?? Colors.grey;
    final st = '${f['state']}';
    final stc = _stateColors[st] ?? Colors.grey;
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 5),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () async {
          final changed = await MaintFaultDetailSheet.open(context, _i(f['id']));
          if (changed == true) _load();
        },
        child: Padding(
          padding: const EdgeInsets.all(13),
          child: Row(children: [
            Container(width: 5, height: 52, decoration: BoxDecoration(color: sc, borderRadius: BorderRadius.circular(4))),
            const SizedBox(width: 12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text('${f['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy))),
                _pill('${f['state_label']}', stc),
              ]),
              const SizedBox(height: 5),
              Row(children: [
                Icon(Icons.apartment_rounded, size: 13, color: Colors.grey.shade500),
                const SizedBox(width: 4),
                Expanded(child: Text('${f['facility'] ?? '—'}${f['asset'] != null ? ' · ${f['asset']}' : ''}',
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600))),
              ]),
              const SizedBox(height: 6),
              Row(children: [
                _tag('${f['name']}', const Color(0xFF64748B)),
                const SizedBox(width: 6),
                _tag('${f['severity_label']}', sc),
                if (f['department'] != null) ...[const SizedBox(width: 6), Flexible(child: _tag('${f['department']}', _navy))],
              ]),
            ])),
          ]),
        ),
      ),
    );
  }
}

// ==================================================== fault detail sheet =====
class MaintFaultDetailSheet extends StatefulWidget {
  const MaintFaultDetailSheet(this.id, {super.key});
  final int id;
  static Future<bool?> open(BuildContext c, int id) => showModalBottomSheet<bool>(
        context: c, isScrollControlled: true, backgroundColor: Colors.transparent,
        builder: (_) => MaintFaultDetailSheet(id),
      );
  @override
  State<MaintFaultDetailSheet> createState() => _MaintFaultDetailSheetState();
}

class _MaintFaultDetailSheetState extends State<MaintFaultDetailSheet> {
  Map<String, dynamic>? _f;
  bool _busy = false;
  bool _changed = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final f = await context.read<AuthProvider>().api.maintFault(widget.id);
      if (mounted) setState(() => _f = f);
    } catch (e) {
      if (mounted) _snack('$e');
    }
  }

  Future<void> _act(String action, String confirmMsg) async {
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      title: Text(tr('تأكيد', 'Confirm')),
      content: Text(confirmMsg),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('تراجع', 'Cancel'))),
        FilledButton(style: FilledButton.styleFrom(backgroundColor: _accent), onPressed: () => Navigator.pop(c, true), child: Text(tr('تأكيد', 'Confirm'))),
      ],
    ));
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.maintFaultAction(widget.id, action);
      _changed = true;
      await _load();
      if (mounted) setState(() => _busy = false);
    } catch (e) {
      if (mounted) { setState(() => _busy = false); _snack('$e'); }
    }
  }

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: _accent, behavior: SnackBarBehavior.floating));

  @override
  Widget build(BuildContext context) {
    final f = _f;
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.9, minChildSize: 0.5, maxChildSize: 0.96,
      builder: (_, sc) => Container(
        decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        clipBehavior: Clip.antiAlias,
        child: Column(children: [
          _header(f),
          Expanded(child: f == null
              ? const Center(child: CircularProgressIndicator(color: _accent))
              : ListView(controller: sc, padding: const EdgeInsets.all(16), children: _body(f))),
          if (f != null) _actions(f),
        ]),
      ),
    );
  }

  Widget _header(Map? f) {
    final sc = _sevColors['${f?['severity']}'] ?? _accent;
    return CustomPaint(
      painter: const BrandPattern(opacity: 0.06),
      child: Container(
        padding: const EdgeInsets.fromLTRB(20, 12, 12, 16),
        decoration: BoxDecoration(gradient: LinearGradient(
            colors: [sc, Color.lerp(sc, Colors.black, 0.4)!], begin: Alignment.topRight, end: Alignment.bottomLeft)),
        child: Column(children: [
          Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12),
              decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
          Row(children: [
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${f?['name'] ?? ''}', style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12, fontWeight: FontWeight.w700)),
              const SizedBox(height: 2),
              Text('${f?['title'] ?? tr('تفاصيل البلاغ', 'Fault details')}',
                  style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
            ])),
            IconButton(icon: const Icon(Icons.close_rounded, color: Colors.white), onPressed: () => Navigator.pop(context, _changed)),
          ]),
          if (f != null) Padding(padding: const EdgeInsets.only(top: 8), child: Row(children: [
            _hpill('${f['state_label']}', Colors.white),
            const SizedBox(width: 8),
            _hpill('${f['severity_label']}', Colors.white),
            if (f['workorder'] != null) ...[const SizedBox(width: 8), _hpill('${f['workorder']}', Colors.white)],
          ])),
        ]),
      ),
    );
  }

  List<Widget> _body(Map f) {
    return [
      _kv(Icons.apartment_rounded, tr('المرفق', 'Facility'), '${f['facility'] ?? '—'}'),
      if (f['location'] != null) _kv(Icons.pin_drop_rounded, tr('الموقع', 'Location'), '${f['location']}'),
      if (f['asset'] != null) _kv(Icons.precision_manufacturing_rounded, tr('الأصل', 'Asset'), '${f['asset']}'),
      if (f['department'] != null) _kv(Icons.account_tree_rounded, tr('القسم', 'Department'), '${f['department']}'),
      if (f['trade'] != null) _kv(Icons.engineering_rounded, tr('التخصص', 'Trade'), '${f['trade']}'),
      if (f['assignee'] != null) _kv(Icons.person_rounded, tr('الفني', 'Technician'), '${f['assignee']}'),
      _kv(Icons.schedule_rounded, tr('وقت البلاغ', 'Reported'), '${f['reported'] ?? '—'}'),
      if (_num(f['downtime_hours']) > 0) _kv(Icons.timelapse_rounded, tr('مدة التعطّل', 'Downtime'), '${f['downtime_hours']} ${tr('ساعة', 'h')}'),
      const SizedBox(height: 12),
      if (f['description'] != null) _para(tr('وصف العطل', 'Description'), '${f['description']}'),
      if (f['diagnosis'] != null) _para(tr('التشخيص', 'Diagnosis'), '${f['diagnosis']}'),
      if (f['resolution'] != null) _para(tr('الإجراء التصحيحي', 'Resolution'), '${f['resolution']}'),
      if ((f['parts'] as List?)?.isNotEmpty ?? false) ...[
        const SizedBox(height: 8),
        _sectionTitle(Icons.inventory_2_rounded, tr('قطع الغيار المستخدمة', 'Parts used')),
        const SizedBox(height: 6),
        for (final p in (f['parts'] as List)) _partLine(p as Map),
        Align(alignment: Alignment.centerLeft, child: Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Text('${tr('الإجمالي', 'Total')}: ${f['parts_cost'] ?? 0} ${tr('د.ك', 'KWD')}',
              style: const TextStyle(fontWeight: FontWeight.w900, color: Color(0xFF16A34A))),
        )),
      ],
      const SizedBox(height: 20),
    ];
  }

  Widget _actions(Map f) {
    final canConvert = f['can_convert'] == true;
    final canCancel = f['can_cancel'] == true;
    final canResolve = !['resolved', 'closed', 'cancelled'].contains('${f['state']}');
    return SafeArea(top: false, child: Padding(
      padding: const EdgeInsets.fromLTRB(14, 8, 14, 12),
      child: _busy
          ? const Center(child: Padding(padding: EdgeInsets.all(8), child: CircularProgressIndicator(color: _accent)))
          : Row(children: [
              if (canCancel) Expanded(child: OutlinedButton.icon(
                style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFFE5484D), minimumSize: const Size.fromHeight(50),
                    side: const BorderSide(color: Color(0xFFE5484D))),
                onPressed: () => _act('cancel', tr('إلغاء هذا البلاغ؟', 'Cancel this fault?')),
                icon: const Icon(Icons.block_rounded, size: 19),
                label: Text(tr('إلغاء', 'Cancel'), style: const TextStyle(fontWeight: FontWeight.w900)),
              )),
              if (canCancel && (canResolve || canConvert)) const SizedBox(width: 10),
              if (canResolve && !canConvert) Expanded(child: OutlinedButton.icon(
                style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFF16A34A), minimumSize: const Size.fromHeight(50),
                    side: const BorderSide(color: Color(0xFF16A34A))),
                onPressed: () => _act('resolve', tr('تعليم البلاغ كمُصلَح؟', 'Mark as resolved?')),
                icon: const Icon(Icons.check_rounded, size: 19),
                label: Text(tr('تم الإصلاح', 'Resolve'), style: const TextStyle(fontWeight: FontWeight.w900)),
              )),
              if (canConvert) Expanded(flex: 2, child: FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: _accent, minimumSize: const Size.fromHeight(50)),
                onPressed: () => _act('convert', tr('تحويل البلاغ إلى أمر عمل؟', 'Convert to work order?')),
                icon: const Icon(Icons.build_rounded, size: 19),
                label: Text(tr('تحويل لأمر عمل', 'To work order'), style: const TextStyle(fontWeight: FontWeight.w900)),
              )),
              if (!canConvert && !canResolve && !canCancel) Expanded(child: Center(
                child: Text(tr('لا إجراءات متاحة', 'No actions available'), style: TextStyle(color: Colors.grey.shade500)))),
            ]),
    ));
  }

  Widget _partLine(Map p) => Container(
        margin: const EdgeInsets.only(bottom: 6),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(10), border: Border.all(color: Colors.grey.shade200)),
        child: Row(children: [
          Expanded(child: Text('${p['name']}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13))),
          Text('×${p['qty']}', style: TextStyle(color: Colors.grey.shade600, fontWeight: FontWeight.w800)),
          const SizedBox(width: 10),
          Text('${p['subtotal']}', style: const TextStyle(fontWeight: FontWeight.w900, color: Color(0xFF16A34A))),
        ]),
      );

  Widget _kv(IconData ic, String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(ic, size: 17, color: _accent), const SizedBox(width: 10),
          SizedBox(width: 92, child: Text(k, style: TextStyle(color: Colors.grey.shade600, fontSize: 12.5, fontWeight: FontWeight.w700))),
          Expanded(child: Text(v, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: _navy))),
        ]),
      );

  Widget _para(String t, String v) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        width: double.infinity,
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.grey.shade200)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: _accent)),
          const SizedBox(height: 4),
          Text(v, style: const TextStyle(fontSize: 13, height: 1.4, color: _navy)),
        ]),
      );

  Widget _hpill(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(20), border: Border.all(color: c.withValues(alpha: 0.5))),
        child: Text(t, style: TextStyle(color: c, fontSize: 11, fontWeight: FontWeight.w800)),
      );
}

// ==================================================== fault create sheet =====
class _Media {
  _Media(this.name, this.mimetype, this.b64, this.isVideo);
  final String name, mimetype, b64;
  final bool isVideo;
}

class MaintFaultCreateSheet extends StatefulWidget {
  const MaintFaultCreateSheet({super.key});
  static Future<bool?> open(BuildContext c) => showModalBottomSheet<bool>(
        context: c, isScrollControlled: true, backgroundColor: Colors.transparent,
        builder: (_) => const MaintFaultCreateSheet(),
      );
  @override
  State<MaintFaultCreateSheet> createState() => _MaintFaultCreateSheetState();
}

class _MaintFaultCreateSheetState extends State<MaintFaultCreateSheet> {
  Map<String, dynamic>? _opt;
  String? _err;
  final _title = TextEditingController();
  final _desc = TextEditingController();
  int? _facId, _locId, _assetId, _depId, _techId;
  String? _trade, _sev = 'medium';
  final List<_Media> _media = [];
  bool _busy = false;
  final _picker = ImagePicker();

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _title.dispose();
    _desc.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final o = await context.read<AuthProvider>().api.maintOptions();
      if (!mounted) return;
      setState(() {
        _opt = o;
        final facs = (o['facilities'] as List?) ?? const [];
        if (facs.isNotEmpty) _facId = facs.first['id'] as int;
      });
    } catch (e) {
      if (mounted) setState(() => _err = '$e');
    }
  }

  Map? get _fac {
    final facs = (_opt?['facilities'] as List?) ?? const [];
    return facs.cast<Map>().where((f) => f['id'] == _facId).cast<Map?>().firstWhere((_) => true, orElse: () => null);
  }

  Future<void> _addPhoto(ImageSource src) async {
    final x = await _picker.pickImage(source: src, imageQuality: 60, maxWidth: 1600);
    if (x == null) return;
    final b = await x.readAsBytes();
    setState(() => _media.add(_Media(x.name, 'image/jpeg', base64Encode(b), false)));
  }

  Future<void> _addVideo(ImageSource src) async {
    final x = await _picker.pickVideo(source: src, maxDuration: const Duration(seconds: 30));
    if (x == null) return;
    final b = await x.readAsBytes();
    if (b.length > 12 * 1024 * 1024) { _snack(tr('الفيديو كبير جداً (الحد 12 ميجا)', 'Video too large (max 12 MB)')); return; }
    setState(() => _media.add(_Media(x.name, 'video/mp4', base64Encode(b), true)));
  }

  void _mediaMenu() => showModalBottomSheet(context: context, builder: (_) => SafeArea(child: Wrap(children: [
        ListTile(leading: const Icon(Icons.photo_camera_rounded, color: _accent), title: Text(tr('التقاط صورة', 'Take photo')),
            onTap: () { Navigator.pop(context); _addPhoto(ImageSource.camera); }),
        ListTile(leading: const Icon(Icons.videocam_rounded, color: Color(0xFFE5484D)), title: Text(tr('تسجيل فيديو', 'Record video')),
            onTap: () { Navigator.pop(context); _addVideo(ImageSource.camera); }),
        ListTile(leading: const Icon(Icons.photo_library_rounded, color: Color(0xFF7C3AED)), title: Text(tr('صورة من المعرض', 'Photo from gallery')),
            onTap: () { Navigator.pop(context); _addPhoto(ImageSource.gallery); }),
        ListTile(leading: const Icon(Icons.video_library_rounded, color: Color(0xFF0891B2)), title: Text(tr('فيديو من المعرض', 'Video from gallery')),
            onTap: () { Navigator.pop(context); _addVideo(ImageSource.gallery); }),
      ])));

  Future<void> _submit() async {
    if (_title.text.trim().isEmpty) { _snack(tr('أدخل عنوان العطل', 'Enter fault title')); return; }
    if (_facId == null) { _snack(tr('اختر المرفق', 'Choose facility')); return; }
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.maintFaultCreate({
        'title': _title.text.trim(), 'facility_id': _facId, 'location_id': _locId,
        'asset_id': _assetId, 'department_id': _depId, 'trade': _trade, 'severity': _sev,
        'assignee_id': _techId, 'description': _desc.text.trim(),
        'media': [for (final m in _media) {'name': m.name, 'mimetype': m.mimetype, 'data': m.b64}],
      });
      if (!mounted) return;
      Navigator.pop(context, true);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(tr('تم تسجيل البلاغ', 'Fault reported')),
        backgroundColor: const Color(0xFF16A34A), behavior: SnackBarBehavior.floating));
    } catch (e) {
      if (mounted) { setState(() => _busy = false); _snack('$e'); }
    }
  }

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: _accent, behavior: SnackBarBehavior.floating));

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.94, minChildSize: 0.5, maxChildSize: 0.97,
      builder: (_, sc) => Container(
        decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        clipBehavior: Clip.antiAlias,
        child: Column(children: [
          CustomPaint(painter: const BrandPattern(opacity: 0.07), child: Container(
            padding: const EdgeInsets.fromLTRB(20, 12, 12, 16),
            decoration: BoxDecoration(gradient: LinearGradient(
                colors: [_accent, Color.lerp(_accent, Colors.black, 0.35)!], begin: Alignment.topRight, end: Alignment.bottomLeft)),
            child: Column(children: [
              Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12),
                  decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
              Row(children: [
                Container(width: 42, height: 42, alignment: Alignment.center,
                    decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(12)),
                    child: const Icon(Icons.add_alert_rounded, color: Colors.white, size: 22)),
                const SizedBox(width: 12),
                Expanded(child: Text(tr('بلاغ عطل جديد', 'Report a fault'),
                    style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900))),
                IconButton(icon: const Icon(Icons.close_rounded, color: Colors.white), onPressed: () => Navigator.pop(context)),
              ]),
            ]),
          )),
          Expanded(child: _opt == null
              ? Center(child: _err != null ? Text(_err!, style: const TextStyle(color: Colors.grey)) : const CircularProgressIndicator(color: _accent))
              : ListView(controller: sc, padding: const EdgeInsets.all(16), children: _form())),
          if (_opt != null) SafeArea(top: false, child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
            child: FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: _accent, minimumSize: const Size.fromHeight(52)),
              onPressed: _busy ? null : _submit,
              icon: _busy ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Icon(Icons.check_rounded),
              label: Text(tr('تسجيل البلاغ', 'Submit fault'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
            ),
          )),
        ]),
      ),
    );
  }

  List<Widget> _form() {
    final facs = (_opt!['facilities'] as List?) ?? const [];
    final locs = (_fac?['locations'] as List?) ?? const [];
    final assets = (_fac?['assets'] as List?) ?? const [];
    final deps = (_opt!['departments'] as List?) ?? const [];
    final trades = (_opt!['trades'] as List?) ?? const [];
    final techs = (_opt!['technicians'] as List?) ?? const [];
    final sevs = (_opt!['severities'] as List?) ?? const [];
    return [
      _lbl(Icons.edit_rounded, tr('العطل', 'Fault')),
      const SizedBox(height: 8),
      _field(_title, tr('مثال: انقطاع التيار بالدور الثاني', 'e.g. Power outage on 2nd floor')),
      const SizedBox(height: 16),
      _lbl(Icons.apartment_rounded, tr('المرفق والموقع', 'Facility & location')),
      const SizedBox(height: 8),
      SearchableField(label: tr('المرفق', 'Facility'), icon: Icons.apartment_rounded, value: _facId, accent: _accent, allowClear: false,
          options: [for (final f in facs) PickOption(value: f['id'], label: '${f['name']}')],
          onChanged: (v) => setState(() { _facId = v as int?; _locId = null; _assetId = null; })),
      const SizedBox(height: 10),
      SearchableField(label: tr('الموقع (اختياري)', 'Location (optional)'), icon: Icons.pin_drop_rounded, value: _locId, accent: _accent,
          options: [for (final l in locs) PickOption(value: l['id'], label: '${l['name']}')],
          onChanged: (v) => setState(() => _locId = v as int?)),
      const SizedBox(height: 10),
      SearchableField(label: tr('الأصل/المعدّة (اختياري)', 'Asset (optional)'), icon: Icons.precision_manufacturing_rounded, value: _assetId, accent: _accent,
          options: [for (final a in assets) PickOption(value: a['id'], label: '${a['name']}', sublabel: a['code'] == null ? null : '${a['code']}')],
          onChanged: (v) => setState(() => _assetId = v as int?)),
      const SizedBox(height: 16),
      _lbl(Icons.account_tree_rounded, tr('القسم والتخصص', 'Department & trade')),
      const SizedBox(height: 8),
      SearchableField(label: tr('القسم', 'Department'), icon: Icons.account_tree_rounded, value: _depId, accent: _accent,
          options: [for (final d in deps) PickOption(value: d['id'], label: '${d['name']}')],
          onChanged: (v) => setState(() => _depId = v as int?)),
      const SizedBox(height: 10),
      SearchableField(label: tr('التخصص المطلوب', 'Required trade'), icon: Icons.engineering_rounded, value: _trade, accent: _accent,
          options: [for (final t in trades) PickOption(value: t['v'], label: '${t['l']}')],
          onChanged: (v) => setState(() => _trade = v as String?)),
      const SizedBox(height: 10),
      SearchableField(label: tr('الفني المُسنَد (اختياري)', 'Assign technician (optional)'), icon: Icons.person_rounded, value: _techId, accent: _accent,
          options: [for (final t in techs) PickOption(value: t['id'], label: '${t['name']}', sublabel: t['trade'] == null ? null : '${t['trade']}')],
          onChanged: (v) => setState(() => _techId = v as int?)),
      const SizedBox(height: 16),
      _lbl(Icons.flag_rounded, tr('الخطورة', 'Severity')),
      const SizedBox(height: 8),
      Row(children: [for (final s in sevs) Expanded(child: _sevChip('${s['v']}', '${s['l']}'))]),
      const SizedBox(height: 16),
      _lbl(Icons.perm_media_rounded, tr('صور وفيديو', 'Photos & video')),
      const SizedBox(height: 8),
      _mediaStrip(),
      const SizedBox(height: 16),
      _lbl(Icons.notes_rounded, tr('الوصف', 'Description')),
      const SizedBox(height: 8),
      _field(_desc, tr('تفاصيل إضافية…', 'Extra details…'), lines: 3),
      const SizedBox(height: 8),
    ];
  }

  Widget _mediaStrip() => SizedBox(height: 84, child: ListView(scrollDirection: Axis.horizontal, children: [
        InkWell(onTap: _mediaMenu, borderRadius: BorderRadius.circular(12), child: Container(
          width: 84, height: 84,
          decoration: BoxDecoration(color: _accent.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(12), border: Border.all(color: _accent.withValues(alpha: 0.3))),
          child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            const Icon(Icons.add_a_photo_rounded, color: _accent, size: 24),
            const SizedBox(height: 4),
            Text(tr('إضافة', 'Add'), style: const TextStyle(color: _accent, fontSize: 11, fontWeight: FontWeight.w800)),
          ]),
        )),
        for (var i = 0; i < _media.length; i++) Padding(padding: const EdgeInsets.only(right: 8), child: Stack(children: [
          Container(width: 84, height: 84, clipBehavior: Clip.antiAlias,
              decoration: BoxDecoration(borderRadius: BorderRadius.circular(12), color: Colors.black12),
              child: _media[i].isVideo
                  ? const Center(child: Icon(Icons.play_circle_fill_rounded, color: Color(0xFFE5484D), size: 34))
                  : Image.memory(base64Decode(_media[i].b64), fit: BoxFit.cover)),
          Positioned(top: 2, right: 2, child: GestureDetector(onTap: () => setState(() => _media.removeAt(i)),
              child: Container(decoration: const BoxDecoration(color: Colors.black54, shape: BoxShape.circle),
                  child: const Icon(Icons.close_rounded, color: Colors.white, size: 16)))),
        ])),
      ]));

  Widget _sevChip(String v, String label) {
    final on = _sev == v;
    final c = _sevColors[v] ?? _accent;
    return GestureDetector(onTap: () => setState(() => _sev = v), child: AnimatedContainer(
      duration: const Duration(milliseconds: 150),
      margin: const EdgeInsets.symmetric(horizontal: 3),
      padding: const EdgeInsets.symmetric(vertical: 10),
      decoration: BoxDecoration(color: on ? c : Colors.white, borderRadius: BorderRadius.circular(11), border: Border.all(color: on ? c : Colors.grey.shade300)),
      child: Text(label, textAlign: TextAlign.center, style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: on ? Colors.white : _navy)),
    ));
  }

  Widget _lbl(IconData ic, String t) => Row(children: [
        Icon(ic, size: 16, color: _accent), const SizedBox(width: 7),
        Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
      ]);

  Widget _field(TextEditingController c, String hint, {int lines = 1}) => TextField(
        controller: c, maxLines: lines,
        decoration: InputDecoration(hintText: hint, filled: true, fillColor: Colors.white,
          hintStyle: TextStyle(fontSize: 13, color: Colors.grey.shade400),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: const BorderSide(color: _accent, width: 1.5))),
      );
}

// ============================================================ inspections ===
class _InspectionsTab extends StatefulWidget {
  const _InspectionsTab();
  @override
  State<_InspectionsTab> createState() => _InspectionsTabState();
}

class _InspectionsTabState extends State<_InspectionsTab> with AutomaticKeepAliveClientMixin {
  Future<List<dynamic>>? _future;
  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => setState(() => _future = context.read<AuthProvider>().api.maintInspections());

  Future<void> _done(int id) async {
    final res = await showModalBottomSheet<String>(context: context, builder: (_) => SafeArea(child: Wrap(children: [
      ListTile(leading: const Icon(Icons.check_circle_rounded, color: Color(0xFF16A34A)), title: Text(tr('مطابق', 'Pass')), onTap: () => Navigator.pop(context, 'pass')),
      ListTile(leading: const Icon(Icons.info_rounded, color: Color(0xFFF59E0B)), title: Text(tr('ملاحظات بسيطة', 'Minor notes')), onTap: () => Navigator.pop(context, 'minor')),
      ListTile(leading: const Icon(Icons.cancel_rounded, color: Color(0xFFE5484D)), title: Text(tr('فشل', 'Fail')), onTap: () => Navigator.pop(context, 'fail')),
    ])));
    if (res == null) return;
    try {
      await context.read<AuthProvider>().api.maintInspectionDone(id, res);
      _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: _accent,
        onPressed: () async {
          final ok = await MaintInspectionCreateSheet.open(context);
          if (ok == true) _load();
        },
        icon: const Icon(Icons.event_note_rounded),
        label: Text(tr('جدولة فحص', 'Schedule'), style: const TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: FutureBuilder<List<dynamic>>(
        future: _future,
        builder: (c, snap) {
          if (snap.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator(color: _accent));
          if (snap.hasError) return Center(child: Text('${snap.error}', style: const TextStyle(color: Colors.grey)));
          final list = snap.data ?? const [];
          if (list.isEmpty) return _empty(tr('لا فحوصات مجدولة', 'No inspections scheduled'));
          return RefreshIndicator(color: _accent, onRefresh: () async => _load(),
            child: ListView.builder(padding: const EdgeInsets.fromLTRB(12, 10, 12, 90), itemCount: list.length,
              itemBuilder: (c, i) => _card(list[i] as Map)));
        },
      ),
    );
  }

  Widget _card(Map r) {
    final due = r['is_due'] == true;
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 5),
      child: Padding(padding: const EdgeInsets.all(13), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Icon(Icons.fact_check_rounded, size: 18, color: due ? const Color(0xFFE5484D) : _accent),
          const SizedBox(width: 8),
          Expanded(child: Text('${r['name']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy))),
          if (due) _pill(tr('مستحق', 'Due'), const Color(0xFFE5484D)),
        ]),
        const SizedBox(height: 8),
        Wrap(spacing: 6, runSpacing: 6, children: [
          _tag('${r['facility'] ?? '—'}', const Color(0xFF64748B)),
          _tag('${r['frequency']}', _navy),
          if (r['department'] != null) _tag('${r['department']}', const Color(0xFF7C3AED)),
          if (r['last_result'] != null) _tag('${r['last_result']}', const Color(0xFF16A34A)),
        ]),
        const SizedBox(height: 8),
        Row(children: [
          Icon(Icons.event_rounded, size: 13, color: Colors.grey.shade500), const SizedBox(width: 4),
          Text(tr('القادم: ${r['next_date'] ?? '—'}', 'Next: ${r['next_date'] ?? '—'}'), style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600)),
          const Spacer(),
          TextButton.icon(
            onPressed: () => _done(_i(r['id'])),
            icon: const Icon(Icons.done_all_rounded, size: 17, color: _accent),
            label: Text(tr('تم الفحص', 'Mark done'), style: const TextStyle(color: _accent, fontWeight: FontWeight.w900, fontSize: 12.5)),
          ),
        ]),
      ])),
    );
  }
}

class MaintInspectionCreateSheet extends StatefulWidget {
  const MaintInspectionCreateSheet({super.key});
  static Future<bool?> open(BuildContext c) => showModalBottomSheet<bool>(
        context: c, isScrollControlled: true, backgroundColor: Colors.transparent,
        builder: (_) => const MaintInspectionCreateSheet());
  @override
  State<MaintInspectionCreateSheet> createState() => _MaintInspectionCreateSheetState();
}

class _MaintInspectionCreateSheetState extends State<MaintInspectionCreateSheet> {
  Map<String, dynamic>? _opt;
  final _name = TextEditingController();
  final _check = TextEditingController();
  int? _facId, _depId;
  String? _freq = 'monthly';
  final List<String> _items = [];
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final o = await context.read<AuthProvider>().api.maintOptions();
    if (!mounted) return;
    setState(() {
      _opt = o;
      final facs = (o['facilities'] as List?) ?? const [];
      if (facs.isNotEmpty) _facId = facs.first['id'] as int;
    });
  }

  Future<void> _submit() async {
    if (_name.text.trim().isEmpty) { _snack(tr('أدخل اسم الفحص', 'Enter inspection name')); return; }
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.maintInspectionCreate({
        'name': _name.text.trim(), 'facility_id': _facId, 'department_id': _depId,
        'frequency': _freq, 'checklist': _items,
      });
      if (!mounted) return;
      Navigator.pop(context, true);
    } catch (e) {
      if (mounted) { setState(() => _busy = false); _snack('$e'); }
    }
  }

  void _snack(String m) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: _accent, behavior: SnackBarBehavior.floating));

  @override
  Widget build(BuildContext context) {
    final facs = (_opt?['facilities'] as List?) ?? const [];
    final deps = (_opt?['departments'] as List?) ?? const [];
    final freqs = (_opt?['frequencies'] as List?) ?? const [];
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.9, minChildSize: 0.5, maxChildSize: 0.96,
      builder: (_, sc) => Container(
        decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        clipBehavior: Clip.antiAlias,
        child: Column(children: [
          Container(
            padding: const EdgeInsets.fromLTRB(20, 14, 12, 16),
            decoration: BoxDecoration(gradient: LinearGradient(colors: [_accent, Color.lerp(_accent, Colors.black, 0.35)!],
                begin: Alignment.topRight, end: Alignment.bottomLeft)),
            child: Row(children: [
              const Icon(Icons.event_note_rounded, color: Colors.white),
              const SizedBox(width: 10),
              Expanded(child: Text(tr('جدولة فحص دوري', 'Schedule inspection'),
                  style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900))),
              IconButton(icon: const Icon(Icons.close_rounded, color: Colors.white), onPressed: () => Navigator.pop(context)),
            ]),
          ),
          Expanded(child: _opt == null ? const Center(child: CircularProgressIndicator(color: _accent))
              : ListView(controller: sc, padding: const EdgeInsets.all(16), children: [
            _field(_name, tr('اسم الفحص (مثال: فحص لوحة الكهرباء)', 'Inspection name')),
            const SizedBox(height: 12),
            SearchableField(label: tr('المرفق', 'Facility'), value: _facId, accent: _accent, allowClear: false, icon: Icons.apartment_rounded,
                options: [for (final f in facs) PickOption(value: f['id'], label: '${f['name']}')],
                onChanged: (v) => setState(() => _facId = v as int?)),
            const SizedBox(height: 10),
            SearchableField(label: tr('القسم', 'Department'), value: _depId, accent: _accent, icon: Icons.account_tree_rounded,
                options: [for (final d in deps) PickOption(value: d['id'], label: '${d['name']}')],
                onChanged: (v) => setState(() => _depId = v as int?)),
            const SizedBox(height: 10),
            SearchableField(label: tr('التردّد', 'Frequency'), value: _freq, accent: _accent, allowClear: false, icon: Icons.repeat_rounded,
                options: [for (final f in freqs) PickOption(value: f['v'], label: '${f['l']}')],
                onChanged: (v) => setState(() => _freq = v as String?)),
            const SizedBox(height: 16),
            Text(tr('بنود قائمة الفحص', 'Checklist items'), style: const TextStyle(fontWeight: FontWeight.w900, color: _navy)),
            const SizedBox(height: 8),
            Row(children: [
              Expanded(child: _field(_check, tr('أضف بنداً…', 'Add item…'))),
              const SizedBox(width: 8),
              IconButton.filled(style: IconButton.styleFrom(backgroundColor: _accent), onPressed: () {
                if (_check.text.trim().isEmpty) return;
                setState(() { _items.add(_check.text.trim()); _check.clear(); });
              }, icon: const Icon(Icons.add_rounded)),
            ]),
            const SizedBox(height: 8),
            for (var i = 0; i < _items.length; i++) ListTile(
              dense: true,
              leading: CircleAvatar(radius: 12, backgroundColor: _accent.withValues(alpha: 0.15), child: Text('${i + 1}', style: const TextStyle(color: _accent, fontSize: 11, fontWeight: FontWeight.w900))),
              title: Text(_items[i], style: const TextStyle(fontSize: 13)),
              trailing: IconButton(icon: const Icon(Icons.close_rounded, size: 18), onPressed: () => setState(() => _items.removeAt(i))),
            ),
          ])),
          if (_opt != null) SafeArea(top: false, child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 12),
            child: FilledButton.icon(style: FilledButton.styleFrom(backgroundColor: _accent, minimumSize: const Size.fromHeight(52)),
              onPressed: _busy ? null : _submit,
              icon: _busy ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : const Icon(Icons.check_rounded),
              label: Text(tr('حفظ الجدولة', 'Save schedule'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15))),
          )),
        ]),
      ),
    );
  }

  Widget _field(TextEditingController c, String hint) => TextField(
        controller: c,
        decoration: InputDecoration(hintText: hint, filled: true, fillColor: Colors.white, isDense: true,
          hintStyle: TextStyle(fontSize: 13, color: Colors.grey.shade400),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300))),
      );
}

// ============================================================ parts store ===
class _PartsTab extends StatefulWidget {
  const _PartsTab();
  @override
  State<_PartsTab> createState() => _PartsTabState();
}

class _PartsTabState extends State<_PartsTab> with AutomaticKeepAliveClientMixin {
  Future<List<dynamic>>? _future;
  String _q = '';
  bool _lowOnly = false;
  @override
  bool get wantKeepAlive => true;

  @override
  void initState() {
    super.initState();
    _future = context.read<AuthProvider>().api.maintParts();
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    return Column(children: [
      Padding(padding: const EdgeInsets.fromLTRB(12, 12, 12, 6), child: Row(children: [
        Expanded(child: TextField(onChanged: (v) => setState(() => _q = v),
          decoration: InputDecoration(hintText: tr('بحث عن قطعة…', 'Search part…'), prefixIcon: const Icon(Icons.search_rounded, size: 20),
            filled: true, fillColor: Colors.white, isDense: true,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300))))),
        const SizedBox(width: 8),
        FilterChip(selected: _lowOnly, label: Text(tr('منخفض', 'Low')),
          selectedColor: const Color(0xFFE5484D).withValues(alpha: 0.15),
          onSelected: (v) => setState(() => _lowOnly = v)),
      ])),
      Expanded(child: FutureBuilder<List<dynamic>>(future: _future, builder: (c, snap) {
        if (snap.connectionState == ConnectionState.waiting) return const Center(child: CircularProgressIndicator(color: _accent));
        var list = (snap.data ?? const []).cast<Map>();
        if (_q.isNotEmpty) list = list.where((p) => '${p['name']} ${p['code'] ?? ''} ${p['category'] ?? ''}'.toLowerCase().contains(_q.toLowerCase())).toList();
        if (_lowOnly) list = list.where((p) => p['low_stock'] == true).toList();
        if (list.isEmpty) return _empty(tr('لا قطع', 'No parts'));
        return ListView.builder(padding: const EdgeInsets.fromLTRB(12, 4, 12, 20), itemCount: list.length,
          itemBuilder: (c, i) => _partCard(list[i]));
      })),
    ]);
  }

  Widget _partCard(Map p) {
    final low = p['low_stock'] == true;
    return Card(margin: const EdgeInsets.symmetric(vertical: 4), child: Padding(
      padding: const EdgeInsets.all(12),
      child: Row(children: [
        Container(width: 44, height: 44, alignment: Alignment.center,
          decoration: BoxDecoration(color: (low ? const Color(0xFFE5484D) : _accent).withValues(alpha: 0.12), borderRadius: BorderRadius.circular(12)),
          child: Icon(low ? Icons.warning_amber_rounded : Icons.widgets_rounded, color: low ? const Color(0xFFE5484D) : _accent, size: 22)),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${p['name']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: _navy)),
          const SizedBox(height: 3),
          Wrap(spacing: 6, children: [
            if (p['code'] != null) _tag('${p['code']}', const Color(0xFF64748B)),
            _tag('${p['category']}', const Color(0xFF7C3AED)),
            if (p['location'] != null) _tag('${p['location']}', const Color(0xFF0891B2)),
          ]),
        ])),
        const SizedBox(width: 8),
        Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Text('${p['on_hand']}', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: low ? const Color(0xFFE5484D) : const Color(0xFF16A34A))),
          Text('${p['uom'] ?? ''} · ${tr('حد', 'min')} ${p['min_qty']}', style: TextStyle(fontSize: 10.5, color: Colors.grey.shade500)),
        ]),
      ]),
    ));
  }
}

// ============================================================ shared bits ===
int _i(dynamic v) => v is int ? v : (v is num ? v.toInt() : int.tryParse('$v') ?? 0);
double _num(dynamic v) => v is num ? v.toDouble() : double.tryParse('$v') ?? 0;

Widget _pill(String t, Color c) => Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
      decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20), border: Border.all(color: c.withValues(alpha: 0.4))),
      child: Text(t, style: TextStyle(color: c, fontSize: 10.5, fontWeight: FontWeight.w900)),
    );

Widget _tag(String t, Color c) => Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(7)),
      child: Text(t, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: c, fontSize: 10.5, fontWeight: FontWeight.w800)),
    );

Widget _sectionTitle(IconData ic, String t) => Row(children: [
      Icon(ic, size: 17, color: _accent), const SizedBox(width: 7),
      Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: _navy)),
    ]);

Widget _empty(String t) => Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
      Icon(Icons.inbox_rounded, size: 54, color: Colors.grey.shade300),
      const SizedBox(height: 10),
      Text(t, style: TextStyle(color: Colors.grey.shade500, fontSize: 14, fontWeight: FontWeight.w700)),
    ]));
