import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/api_client.dart';
import '../core/i18n.dart';
import 'excel_export.dart';

/// موديول البترول/خزّانات الوقود بالكامل: هيدر بإحصائيات غنية + أقسام لكل
/// المداولات الداخلية (الخزّانات · الشحن Charges · الاستهلاك Uses · التحويل
/// Transfers) بفلاتر متعدّدة ونماذج إضافة مطابقة تماماً لحقول الباك ايند.
class PetrolScreen extends StatefulWidget {
  const PetrolScreen({super.key});
  @override
  State<PetrolScreen> createState() => _PetrolScreenState();
}

class _PetrolScreenState extends State<PetrolScreen> with SingleTickerProviderStateMixin {
  static const _amber = Color(0xFFE8873B);
  static const _dark = Color(0xFF243447);
  static const _ink = Color(0xFF1F2A37);
  static const _grey = Color(0xFF6B7A8D);

  late TabController _tabs;
  Map<String, dynamic>? _ov;
  Map<String, dynamic>? _opts;
  bool _loading = true;

  // بيانات الأقسام + الفلاتر
  List _tanks = const [], _charges = const [], _uses = const [], _transfers = const [];
  Map _cTotals = const {}, _uTotals = const {}, _xTotals = const {};
  int? _fTank, _fVehicle, _fStage;
  String? _fState;
  bool _fLow = false;
  String _q = '';

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 4, vsync: this)..addListener(_onTab);
    _load();
  }

  @override
  void dispose() { _tabs.dispose(); super.dispose(); }

  void _onTab() { if (!_tabs.indexIsChanging) _loadSection(); }

  ApiClient get _api => context.read<AuthProvider>().api;

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final ov = await _api.petrolOverview();
      Map<String, dynamic>? opts;
      try { opts = await _api.petrolOptions(); } catch (_) {}
      if (mounted) setState(() { _ov = ov; _opts = opts; });
      await _loadSection();
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  Future<void> _loadSection() async {
    try {
      switch (_tabs.index) {
        case 0:
          final d = await _api.petrolTanks(stage: _fStage, low: _fLow, q: _q.isEmpty ? null : _q);
          _tanks = (d['items'] as List?) ?? const [];
          break;
        case 1:
          final d = await _api.petrolCharges(tank: _fTank);
          _charges = (d['items'] as List?) ?? const [];
          _cTotals = {'qty': d['total_qty'], 'cost': d['total_cost']};
          break;
        case 2:
          final d = await _api.petrolUses(tank: _fTank, vehicle: _fVehicle);
          _uses = (d['items'] as List?) ?? const [];
          _uTotals = {'qty': d['total_qty']};
          break;
        case 3:
          final d = await _api.petrolTransfers(tank: _fTank, state: _fState);
          _transfers = (d['items'] as List?) ?? const [];
          _xTotals = {'qty': d['total_qty']};
          break;
      }
      if (mounted) setState(() {});
    } catch (_) {}
  }

  List get _tankOpts => ((_opts?['tanks'] as List?) ?? const []).cast();
  List get _stageOpts => ((_opts?['stages'] as List?) ?? const []).cast();
  List get _vehicleOpts => ((_opts?['vehicles'] as List?) ?? const []).cast();

  @override
  Widget build(BuildContext context) {
    final avail = _ov?['available'] != false;
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6F9),
      appBar: AppBar(
        backgroundColor: _dark, foregroundColor: Colors.white,
        title: Text(tr('إدارة الوقود', 'Fuel management')),
        actions: [
          IconButton(
            tooltip: tr('تصدير Excel', 'Export Excel'),
            icon: const Icon(Icons.grid_on_rounded),
            onPressed: () {
              final kind = ['tanks', 'charges', 'uses', 'transfers'][_tabs.index];
              exportExcelFile(context, path: '/cafm/petrol/export?kind=$kind',
                  fileName: 'petrol-$kind.xlsx', shareText: tr('بيانات الوقود', 'Fuel data'));
            }),
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded)),
        ],
        bottom: TabBar(
          controller: _tabs, isScrollable: true,
          indicatorColor: _amber, labelColor: Colors.white, unselectedLabelColor: Colors.white70,
          tabs: [
            Tab(text: tr('الخزّانات', 'Tanks')),
            Tab(text: tr('الشحن', 'Charges')),
            Tab(text: tr('الاستهلاك', 'Uses')),
            Tab(text: tr('التحويلات', 'Transfers')),
          ],
        ),
      ),
      floatingActionButton: avail ? FloatingActionButton.extended(
        backgroundColor: _amber, foregroundColor: Colors.white,
        onPressed: _createForCurrentTab,
        icon: const Icon(Icons.add_rounded),
        label: Text(_createLabel(), style: const TextStyle(fontWeight: FontWeight.w900)),
      ) : null,
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: _amber))
          : !avail
              ? Center(child: Text(tr('موديول البترول غير مثبّت', 'Petrol module not installed'), style: const TextStyle(color: _grey)))
              : Column(children: [
                  _statsHeader(),
                  Expanded(child: TabBarView(controller: _tabs, children: [
                    _tanksTab(), _chargesTab(), _usesTab(), _transfersTab(),
                  ])),
                ]),
    );
  }

  String _createLabel() => [tr('خزّان', 'Tank'), tr('شحن', 'Charge'), tr('استهلاك', 'Use'), tr('تحويل', 'Transfer')][_tabs.index];
  void _createForCurrentTab() => [_tankForm, _chargeForm, _useForm, _transferForm][_tabs.index]();

  // ---- هيدر الإحصائيات (كثيرة) -----------------------------------------
  Widget _statsHeader() {
    final s = (_ov?['stats'] as Map?) ?? const {};
    final chips = <(String, String, IconData, Color)>[
      (tr('الخزّانات', 'Tanks'), '${s['tanks'] ?? 0}', Icons.propane_tank_rounded, _amber),
      (tr('السعة', 'Capacity'), _n(s['capacity']), Icons.straighten_rounded, const Color(0xFF3B82F6)),
      (tr('الرصيد', 'Balance'), _n(s['balance']), Icons.water_drop_rounded, const Color(0xFF10B981)),
      (tr('متوسط الامتلاء', 'Avg fill'), '${_n(s['avg_fill'])}%', Icons.speed_rounded, const Color(0xFF8B5CF6)),
      (tr('المشحون', 'Charged'), _n(s['charged']), Icons.local_gas_station_rounded, const Color(0xFF0EA5A4)),
      (tr('المستهلك', 'Used'), _n(s['used']), Icons.local_fire_department_rounded, const Color(0xFFEF4444)),
      (tr('وارد', 'Incoming'), _n(s['incoming']), Icons.call_received_rounded, const Color(0xFF22C55E)),
      (tr('صادر', 'Outgoing'), _n(s['outgoing']), Icons.call_made_rounded, const Color(0xFFF59E0B)),
      (tr('خزّانات منخفضة', 'Low tanks'), '${s['low_tanks'] ?? 0}', Icons.warning_amber_rounded, const Color(0xFFDC2626)),
      (tr('تحويلات معلّقة', 'Pending'), '${s['pending_transfers'] ?? 0}', Icons.hourglass_bottom_rounded, const Color(0xFFF97316)),
      (tr('عمليات شحن', 'Charges'), '${s['charges'] ?? 0}', Icons.add_circle_outline_rounded, const Color(0xFF6366F1)),
      (tr('عمليات استهلاك', 'Uses'), '${s['uses'] ?? 0}', Icons.remove_circle_outline_rounded, const Color(0xFF64748B)),
    ];
    return Container(
      color: _dark, padding: const EdgeInsets.fromLTRB(10, 8, 10, 12),
      child: SizedBox(height: 74, child: ListView.separated(
        scrollDirection: Axis.horizontal,
        itemCount: chips.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8),
        itemBuilder: (_, i) {
          final c = chips[i];
          return Container(
            width: 108, padding: const EdgeInsets.all(9),
            decoration: BoxDecoration(color: Colors.white.withValues(alpha: .06), borderRadius: BorderRadius.circular(12),
                border: Border.all(color: c.$4.withValues(alpha: .4))),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
              Row(children: [Icon(c.$3, color: c.$4, size: 15), const SizedBox(width: 4),
                Expanded(child: Text(c.$1, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.white70, fontSize: 10.5)))]),
              const SizedBox(height: 4),
              Text(c.$2, maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(color: c.$4, fontWeight: FontWeight.w900, fontSize: 16)),
            ]),
          );
        },
      )),
    );
  }

  String _n(dynamic v) {
    final d = (v as num?)?.toDouble() ?? 0;
    if (d >= 1000000) return '${(d / 1000000).toStringAsFixed(1)}M';
    if (d >= 1000) return '${(d / 1000).toStringAsFixed(1)}K';
    return d % 1 == 0 ? d.toInt().toString() : d.toStringAsFixed(1);
  }

  // ---- تبويب الخزّانات --------------------------------------------------
  Widget _tanksTab() {
    return Column(children: [
      _filterBar([
        _searchField(),
        _chipFilter(tr('منخفض فقط', 'Low only'), _fLow, () { setState(() => _fLow = !_fLow); _loadSection(); }),
        _dropFilter<int>(tr('المرحلة', 'Stage'), _fStage, [for (final s in _stageOpts) (s['id'] as int, '${s['name']}')], (v) { setState(() => _fStage = v); _loadSection(); }),
      ]),
      Expanded(child: _list(_tanks, (t) => _tankCard(t as Map))),
    ]);
  }

  Widget _tankCard(Map t) {
    final fill = ((t['fill_pct'] as num?)?.toDouble() ?? 0) / 100;
    final low = t['low'] == true;
    return _card(onTap: () => _tankDetail(t), children: [
      Row(children: [
        Container(width: 42, height: 42, decoration: BoxDecoration(color: _amber.withValues(alpha: .12), borderRadius: BorderRadius.circular(11)),
            child: const Icon(Icons.propane_tank_rounded, color: _amber)),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${t['name']}', style: const TextStyle(fontWeight: FontWeight.w800, color: _ink, fontSize: 15)),
          if ((t['stage'] ?? '').toString().isNotEmpty) Text('${t['stage']}', style: const TextStyle(color: _grey, fontSize: 12)),
        ])),
        if (low) _tag(tr('منخفض', 'Low'), const Color(0xFFDC2626)),
      ]),
      const SizedBox(height: 10),
      Row(children: [
        Expanded(child: ClipRRect(borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(value: fill.clamp(0, 1), minHeight: 8, backgroundColor: const Color(0xFFE9EDF2),
                color: low ? const Color(0xFFDC2626) : _amber))),
        const SizedBox(width: 8),
        Text('${t['fill_pct']}%', style: const TextStyle(color: _grey, fontWeight: FontWeight.w700, fontSize: 12)),
      ]),
      const SizedBox(height: 8),
      Wrap(spacing: 14, runSpacing: 4, children: [
        _kv(tr('الرصيد', 'Balance'), _n(t['balance'])),
        _kv(tr('السعة', 'Capacity'), _n(t['capacity'])),
        _kv(tr('مشحون', 'Charged'), _n(t['charged'])),
        _kv(tr('مستهلك', 'Used'), _n(t['used'])),
        if ((t['last_charge'] ?? '').toString().isNotEmpty) _kv(tr('آخر شحن', 'Last charge'), '${t['last_charge']}'),
      ]),
    ]);
  }

  // ---- تبويب الشحن ------------------------------------------------------
  Widget _chargesTab() {
    return Column(children: [
      _filterBar([
        _tankFilter(),
        _totalTag('${tr('الكمية', 'Qty')}: ${_n(_cTotals['qty'])}'),
        _totalTag('${tr('التكلفة', 'Cost')}: ${_n(_cTotals['cost'])}'),
      ]),
      Expanded(child: _list(_charges, (c) => _rowCard(
        icon: Icons.add_circle_rounded, color: const Color(0xFF10B981),
        title: '${(c as Map)['name']}',
        sub: [c['tank'], c['charge_date']].where((x) => (x ?? '').toString().isNotEmpty).join(' · '),
        pills: [('${tr('كمية', 'Qty')} ${_n(c['quantity'])}', _amber), ('${tr('تكلفة', 'Cost')} ${_n(c['cost'])}', const Color(0xFF3B82F6))],
      ))),
    ]);
  }

  // ---- تبويب الاستهلاك --------------------------------------------------
  Widget _usesTab() {
    return Column(children: [
      _filterBar([
        _tankFilter(),
        _dropFilter<int>(tr('المركبة', 'Vehicle'), _fVehicle, [for (final v in _vehicleOpts) (v['id'] as int, '${v['name']}')], (v) { setState(() => _fVehicle = v); _loadSection(); }),
        _totalTag('${tr('الكمية', 'Qty')}: ${_n(_uTotals['qty'])}'),
      ]),
      Expanded(child: _list(_uses, (u) => _rowCard(
        icon: Icons.local_fire_department_rounded, color: const Color(0xFFEF4444),
        title: '${(u as Map)['name']}',
        sub: [u['vehicle'], u['tank'], u['datetime']].where((x) => (x ?? '').toString().isNotEmpty).join(' · '),
        pills: [
          ('${tr('كمية', 'Qty')} ${_n(u['quantity'])}', _amber),
          ('${tr('عدّاد', 'Odo')} ${_n(u['odometer_value'])}', const Color(0xFF64748B)),
          if (((u['liter_per_km_rate'] as num?) ?? 0) > 0) ('${_n(u['liter_per_km_rate'])} ${tr('ل/كم', 'L/km')}', const Color(0xFF8B5CF6)),
        ],
      ))),
    ]);
  }

  // ---- تبويب التحويلات --------------------------------------------------
  Widget _transfersTab() {
    return Column(children: [
      _filterBar([
        _tankFilter(),
        _dropFilter<String>(tr('الحالة', 'State'), _fState, [('draft', tr('مسودّة', 'Draft')), ('done', tr('منجَز', 'Done'))], (v) { setState(() => _fState = v); _loadSection(); }),
        _totalTag('${tr('الكمية', 'Qty')}: ${_n(_xTotals['qty'])}'),
      ]),
      Expanded(child: _list(_transfers, (x) => _transferCard(x as Map))),
    ]);
  }

  Widget _transferCard(Map x) {
    final done = x['state'] == 'done';
    return _card(children: [
      Row(children: [
        Icon(Icons.swap_horiz_rounded, color: done ? const Color(0xFF10B981) : const Color(0xFFF59E0B)),
        const SizedBox(width: 8),
        Expanded(child: Text('${x['from_tank'] ?? '—'}  →  ${x['to_tank'] ?? '—'}',
            style: const TextStyle(fontWeight: FontWeight.w800, color: _ink, fontSize: 14))),
        _tag('${x['state_label']}', done ? const Color(0xFF10B981) : const Color(0xFFF59E0B)),
      ]),
      const SizedBox(height: 8),
      Row(children: [
        _kv(tr('الكمية', 'Quantity'), _n(x['quantity'])),
        const SizedBox(width: 16),
        if ((x['date'] ?? '').toString().isNotEmpty) _kv(tr('التاريخ', 'Date'), '${x['date']}'),
        const Spacer(),
        if (!done) TextButton.icon(
          onPressed: () => _confirmTransfer(x['id'] as int),
          icon: const Icon(Icons.check_circle_rounded, size: 18, color: _amber),
          label: Text(tr('تأكيد', 'Confirm'), style: const TextStyle(color: _amber, fontWeight: FontWeight.w800))),
      ]),
    ]);
  }

  Future<void> _confirmTransfer(int id) async {
    try {
      await _api.petrolTransferConfirm(id);
      _ok(tr('تمّ التحويل', 'Transfer done'));
      _load();
    } catch (e) { _err('$e'.replaceFirst('Exception: ', '')); }
  }

  // ---- تفاصيل الخزّان ---------------------------------------------------
  Future<void> _tankDetail(Map t) async {
    showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: .7, maxChildSize: .95,
        builder: (_, sc) => FutureBuilder<Map<String, dynamic>>(
          future: _api.petrolTank(t['id'] as int),
          builder: (_, snap) {
            if (!snap.hasData) return const Center(child: Padding(padding: EdgeInsets.all(40), child: CircularProgressIndicator(color: _amber)));
            final d = snap.data!;
            final charges = (d['charges'] as List?) ?? const [];
            final uses = (d['uses'] as List?) ?? const [];
            final transfers = (d['transfers'] as List?) ?? const [];
            return ListView(controller: sc, padding: const EdgeInsets.all(16), children: [
              Center(child: Container(width: 40, height: 4, decoration: BoxDecoration(color: const Color(0xFFE0E5EB), borderRadius: BorderRadius.circular(4)))),
              const SizedBox(height: 12),
              Text('${d['name']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 20, color: _ink)),
              const SizedBox(height: 12),
              Wrap(spacing: 10, runSpacing: 10, children: [
                for (final e in [
                  (tr('السعة', 'Capacity'), _n(d['capacity'])), (tr('الرصيد', 'Balance'), _n(d['balance'])),
                  (tr('المشحون', 'Charged'), _n(d['charged'])), (tr('المستهلك', 'Used'), _n(d['used'])),
                  (tr('وارد', 'Incoming'), _n(d['incoming_transfer'])), (tr('صادر', 'Outgoing'), _n(d['outgoing_transfer'])),
                  (tr('نسبة الرصيد', 'Balance %'), '${d['balance_progress']}%'), (tr('آخر شحن', 'Last charge'), '${d['last_charge'] ?? '—'}'),
                ]) _statBox(e.$1, e.$2),
              ]),
              const SizedBox(height: 16),
              _detailSection(tr('الشحن', 'Charges'), charges.length, [for (final c in charges) '${(c as Map)['name']} · ${_n(c['quantity'])} · ${c['charge_date'] ?? ''}']),
              _detailSection(tr('الاستهلاك', 'Uses'), uses.length, [for (final u in uses.take(30)) '${(u as Map)['vehicle'] ?? ''} · ${_n(u['quantity'])} · ${u['datetime'] ?? ''}']),
              _detailSection(tr('التحويلات', 'Transfers'), transfers.length, [for (final x in transfers) '${(x as Map)['from_tank'] ?? ''}→${x['to_tank'] ?? ''} · ${_n(x['quantity'])} · ${x['state_label'] ?? ''}']),
            ]);
          },
        ),
      ),
    );
  }

  Widget _detailSection(String title, int n, List<String> lines) => Padding(
    padding: const EdgeInsets.only(bottom: 14),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [Text(title, style: const TextStyle(fontWeight: FontWeight.w800, color: _ink, fontSize: 15)),
        const SizedBox(width: 6), _tag('$n', _amber)]),
      const SizedBox(height: 6),
      if (lines.isEmpty) Text(tr('لا سجلات', 'No records'), style: const TextStyle(color: _grey, fontSize: 12))
      else ...lines.map((l) => Padding(padding: const EdgeInsets.symmetric(vertical: 3),
          child: Row(children: [const Icon(Icons.chevron_left_rounded, size: 16, color: _grey),
            Expanded(child: Text(l, style: const TextStyle(color: _ink, fontSize: 12.5)))]))),
    ]),
  );

  // ================= نماذج الإضافة (مطابقة للباك ايند) =================
  void _tankForm() {
    final name = TextEditingController(); final cap = TextEditingController();
    int? stage;
    _sheet(tr('خزّان جديد', 'New tank'), (set) => [
      _tf(name, tr('اسم الخزّان *', 'Tank name *')),
      _tf(cap, tr('السعة', 'Capacity'), kb: const TextInputType.numberWithOptions(decimal: true)),
      _drop<int>(tr('المرحلة', 'Stage'), stage, [for (final s in _stageOpts) (s['id'] as int, '${s['name']}')], (v) => set(() => stage = v)),
    ], () async {
      if (name.text.trim().isEmpty) throw Exception(tr('الاسم مطلوب', 'Name required'));
      await _api.petrolCreate('tank', {'name': name.text.trim(), 'capacity': cap.text.trim(), if (stage != null) 'stage_id': stage});
    });
  }

  void _chargeForm() {
    final qty = TextEditingController(); final cost = TextEditingController();
    int? tank; DateTime? date;
    _sheet(tr('شحن جديد', 'New charge'), (set) => [
      _drop<int>(tr('الخزّان *', 'Tank *'), tank, [for (final t in _tankOpts) (t['id'] as int, '${t['name']}')], (v) => set(() => tank = v)),
      _dateField(tr('تاريخ الشحن', 'Charge date'), date, (d) => set(() => date = d)),
      _tf(qty, tr('الكمية', 'Quantity'), kb: const TextInputType.numberWithOptions(decimal: true)),
      _tf(cost, tr('التكلفة', 'Cost'), kb: const TextInputType.numberWithOptions(decimal: true)),
    ], () async {
      if (tank == null) throw Exception(tr('اختر الخزّان', 'Select tank'));
      await _api.petrolCreate('charge', {'tank_id': tank, 'quantity': qty.text.trim(), 'cost': cost.text.trim(), if (date != null) 'charge_date': _fmtD(date!)});
    });
  }

  void _useForm() {
    final odo = TextEditingController(); final cur = TextEditingController(); final qty = TextEditingController();
    int? vehicle; int? tank; DateTime? dt;
    _sheet(tr('استهلاك جديد', 'New use'), (set) => [
      _drop<int>(tr('المركبة *', 'Vehicle *'), vehicle, [for (final v in _vehicleOpts) (v['id'] as int, '${v['name']}')], (v) => set(() => vehicle = v)),
      _drop<int>(tr('مصدر السجل (الخزّان)', 'Source tank'), tank, [for (final t in _tankOpts) (t['id'] as int, '${t['name']}')], (v) => set(() => tank = v)),
      _tf(odo, tr('قراءة العدّاد الحالية', 'Current odometer'), kb: const TextInputType.numberWithOptions(decimal: true)),
      _tf(cur, tr('الكمية الحالية', 'Current quantity'), kb: const TextInputType.numberWithOptions(decimal: true)),
      _tf(qty, tr('الكمية', 'Quantity'), kb: const TextInputType.numberWithOptions(decimal: true)),
      _dateField(tr('التاريخ والوقت', 'Date & time'), dt, (d) => set(() => dt = d), withTime: true),
    ], () async {
      if (vehicle == null) throw Exception(tr('اختر المركبة', 'Select vehicle'));
      await _api.petrolCreate('use', {'vehicle_id': vehicle, if (tank != null) 'tank_id': tank,
        'odometer_value': odo.text.trim(), 'current_quantity': cur.text.trim(), 'quantity': qty.text.trim(),
        if (dt != null) 'datetime': _fmtDT(dt!)});
    });
  }

  void _transferForm() {
    final qty = TextEditingController();
    int? from; int? to; DateTime? date; bool confirm = true;
    _sheet(tr('تحويل جديد', 'New transfer'), (set) => [
      _drop<int>(tr('من خزّان *', 'From tank *'), from, [for (final t in _tankOpts) (t['id'] as int, '${t['name']} (${_n(t['balance'])})')], (v) => set(() => from = v)),
      _drop<int>(tr('إلى خزّان *', 'To tank *'), to, [for (final t in _tankOpts) (t['id'] as int, '${t['name']}')], (v) => set(() => to = v)),
      _tf(qty, tr('الكمية', 'Quantity'), kb: const TextInputType.numberWithOptions(decimal: true)),
      _dateField(tr('تاريخ التحويل', 'Transfer date'), date, (d) => set(() => date = d)),
      SwitchListTile(contentPadding: EdgeInsets.zero, activeThumbColor: _amber,
        title: Text(tr('تأكيد فوري', 'Confirm immediately'), style: const TextStyle(color: _ink, fontSize: 13.5)),
        value: confirm, onChanged: (v) => set(() => confirm = v)),
    ], () async {
      if (from == null || to == null) throw Exception(tr('اختر الخزّانين', 'Select both tanks'));
      if (from == to) throw Exception(tr('يجب أن يختلف الخزّانان', 'Tanks must differ'));
      await _api.petrolCreate('transfer', {'tank_id': from, 'to_tank_id': to, 'quantity': qty.text.trim(),
        if (date != null) 'date': _fmtD(date!), 'confirm': confirm});
    });
  }

  // ================= أدوات واجهة مشتركة =================
  Widget _list(List items, Widget Function(dynamic) builder) {
    if (items.isEmpty) return Center(child: Text(tr('لا سجلات', 'No records'), style: const TextStyle(color: _grey)));
    return RefreshIndicator(onRefresh: _loadSection, color: _amber,
      child: ListView.builder(padding: const EdgeInsets.all(12), itemCount: items.length, itemBuilder: (_, i) => builder(items[i])));
  }

  Widget _card({required List<Widget> children, VoidCallback? onTap}) => Container(
    margin: const EdgeInsets.only(bottom: 10),
    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: .04), blurRadius: 8, offset: const Offset(0, 2))]),
    clipBehavior: Clip.antiAlias,
    child: InkWell(onTap: onTap, child: Padding(padding: const EdgeInsets.all(12),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: children))),
  );

  Widget _rowCard({required IconData icon, required Color color, required String title, required String sub, required List<(String, Color)> pills}) =>
    _card(children: [
      Row(children: [
        Container(width: 40, height: 40, decoration: BoxDecoration(color: color.withValues(alpha: .12), borderRadius: BorderRadius.circular(10)),
            child: Icon(icon, color: color, size: 20)),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(title, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800, color: _ink, fontSize: 13.5)),
          if (sub.isNotEmpty) Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _grey, fontSize: 11.5)),
        ])),
      ]),
      if (pills.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 8),
        child: Wrap(spacing: 6, runSpacing: 6, children: [for (final p in pills) _tag(p.$1, p.$2)])),
    ]);

  Widget _filterBar(List<Widget> children) => Container(
    color: Colors.white, padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
    child: SizedBox(height: 38, child: ListView.separated(scrollDirection: Axis.horizontal, itemCount: children.length,
        separatorBuilder: (_, __) => const SizedBox(width: 8), itemBuilder: (_, i) => children[i])),
  );

  Widget _searchField() => SizedBox(width: 180, child: TextField(
    onChanged: (v) { _q = v; _loadSection(); },
    style: const TextStyle(fontSize: 13),
    decoration: InputDecoration(hintText: tr('بحث…', 'Search…'), prefixIcon: const Icon(Icons.search_rounded, size: 18),
        isDense: true, contentPadding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
        filled: true, fillColor: const Color(0xFFF1F4F8), border: OutlineInputBorder(borderRadius: BorderRadius.circular(10), borderSide: BorderSide.none)),
  ));

  Widget _tankFilter() => _dropFilter<int>(tr('الخزّان', 'Tank'), _fTank, [for (final t in _tankOpts) (t['id'] as int, '${t['name']}')], (v) { setState(() => _fTank = v); _loadSection(); });

  Widget _chipFilter(String label, bool active, VoidCallback onTap) => GestureDetector(onTap: onTap,
    child: Container(alignment: Alignment.center, padding: const EdgeInsets.symmetric(horizontal: 14),
      decoration: BoxDecoration(color: active ? _amber : const Color(0xFFF1F4F8), borderRadius: BorderRadius.circular(10)),
      child: Text(label, style: TextStyle(color: active ? Colors.white : _grey, fontWeight: FontWeight.w700, fontSize: 12.5))));

  Widget _dropFilter<T>(String hint, T? value, List<(T, String)> items, ValueChanged<T?> onCh) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 12), alignment: Alignment.center,
    decoration: BoxDecoration(color: const Color(0xFFF1F4F8), borderRadius: BorderRadius.circular(10)),
    child: DropdownButton<T>(value: value, isDense: true, underline: const SizedBox(), hint: Text(hint, style: const TextStyle(fontSize: 12.5, color: _grey)),
        style: const TextStyle(fontSize: 12.5, color: _ink),
        items: [DropdownMenuItem<T>(value: null, child: Text(tr('الكل', 'All'), style: const TextStyle(fontSize: 12.5))),
          for (final it in items) DropdownMenuItem<T>(value: it.$1, child: Text(it.$2, style: const TextStyle(fontSize: 12.5)))],
        onChanged: onCh),
  );

  Widget _totalTag(String t) => Container(alignment: Alignment.center, padding: const EdgeInsets.symmetric(horizontal: 12),
    decoration: BoxDecoration(color: _amber.withValues(alpha: .12), borderRadius: BorderRadius.circular(10)),
    child: Text(t, style: const TextStyle(color: _amber, fontWeight: FontWeight.w800, fontSize: 12)));

  Widget _tag(String t, Color c) => Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
    decoration: BoxDecoration(color: c.withValues(alpha: .14), borderRadius: BorderRadius.circular(20)),
    child: Text(t, style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 11)));

  Widget _kv(String k, String v) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
    Text(k, style: const TextStyle(color: _grey, fontSize: 10.5)),
    Text(v, style: const TextStyle(color: _ink, fontWeight: FontWeight.w800, fontSize: 13)),
  ]);

  Widget _statBox(String k, String v) => Container(width: 150, padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(color: const Color(0xFFF6F8FB), borderRadius: BorderRadius.circular(12)),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(k, style: const TextStyle(color: _grey, fontSize: 11.5)),
      const SizedBox(height: 3),
      Text(v, style: const TextStyle(color: _ink, fontWeight: FontWeight.w900, fontSize: 17)),
    ]));

  // نماذج: ورقة سفلية + حقول
  void _sheet(String title, List<Widget> Function(StateSetter) fields, Future<void> Function() onSubmit) {
    showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (ctx) => StatefulBuilder(builder: (ctx, set) => Padding(
        padding: EdgeInsets.only(left: 16, right: 16, top: 16, bottom: MediaQuery.of(ctx).viewInsets.bottom + 20),
        child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Center(child: Container(width: 40, height: 4, decoration: BoxDecoration(color: const Color(0xFFE0E5EB), borderRadius: BorderRadius.circular(4)))),
          const SizedBox(height: 12),
          Text(title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 18, color: _ink)),
          const SizedBox(height: 14),
          ...fields(set),
          const SizedBox(height: 16),
          FilledButton(style: FilledButton.styleFrom(backgroundColor: _amber, padding: const EdgeInsets.symmetric(vertical: 14)),
            onPressed: () async {
              try { await onSubmit(); if (ctx.mounted) Navigator.pop(ctx); _ok(tr('تمّ الحفظ', 'Saved')); _load(); }
              catch (e) { _err('$e'.replaceFirst('Exception: ', '')); }
            },
            child: Text(tr('حفظ', 'Save'), style: const TextStyle(fontWeight: FontWeight.w900))),
        ])),
      )),
    );
  }

  Widget _tf(TextEditingController c, String hint, {TextInputType? kb}) => Padding(padding: const EdgeInsets.only(bottom: 10),
    child: TextField(controller: c, keyboardType: kb,
      decoration: InputDecoration(labelText: hint, filled: true, fillColor: const Color(0xFFF6F8FB),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
          contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14))));

  Widget _drop<T>(String hint, T? value, List<(T, String)> items, ValueChanged<T?> onCh) => Padding(padding: const EdgeInsets.only(bottom: 10),
    child: Container(padding: const EdgeInsets.symmetric(horizontal: 14), decoration: BoxDecoration(color: const Color(0xFFF6F8FB), borderRadius: BorderRadius.circular(12)),
      child: DropdownButton<T>(value: value, isExpanded: true, underline: const SizedBox(), hint: Text(hint, style: const TextStyle(color: _grey)),
          items: [for (final it in items) DropdownMenuItem<T>(value: it.$1, child: Text(it.$2))], onChanged: onCh)));

  Widget _dateField(String label, DateTime? value, ValueChanged<DateTime> onPick, {bool withTime = false}) => Padding(padding: const EdgeInsets.only(bottom: 10),
    child: InkWell(borderRadius: BorderRadius.circular(12),
      onTap: () async {
        final now = DateTime.now();
        final d = await showDatePicker(context: context, initialDate: value ?? now, firstDate: DateTime(now.year - 2), lastDate: DateTime(now.year + 2));
        if (d == null || !mounted) return;
        TimeOfDay? t;
        if (withTime) t = await showTimePicker(context: context, initialTime: TimeOfDay.fromDateTime(value ?? now));
        onPick(DateTime(d.year, d.month, d.day, t?.hour ?? 0, t?.minute ?? 0));
      },
      child: Container(padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 15),
        decoration: BoxDecoration(color: const Color(0xFFF6F8FB), borderRadius: BorderRadius.circular(12)),
        child: Row(children: [Icon(withTime ? Icons.event_note_rounded : Icons.event_rounded, color: _amber, size: 18), const SizedBox(width: 10),
          Text(value == null ? label : (withTime ? _fmtDT(value) : _fmtD(value)), style: TextStyle(color: value == null ? _grey : _ink, fontWeight: value == null ? FontWeight.normal : FontWeight.w700))]))),
  );

  String _fmtD(DateTime d) { String two(int n) => n.toString().padLeft(2, '0'); return '${d.year}-${two(d.month)}-${two(d.day)}'; }
  String _fmtDT(DateTime d) { String two(int n) => n.toString().padLeft(2, '0'); return '${_fmtD(d)} ${two(d.hour)}:${two(d.minute)}:00'; }

  void _ok(String m) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m), backgroundColor: const Color(0xFF10B981)));
  void _err(String m) => ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m), backgroundColor: const Color(0xFFDC2626)));
}
