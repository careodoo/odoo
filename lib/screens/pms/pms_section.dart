import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'pms_shell.dart';
import 'pms_employee_file.dart';
import 'pms_vehicle_file.dart';

/// Icons for the section codes the API advertises. Kept here rather than sent
/// from the server: the server names the section, the app decides how it looks.
const Map<String, IconData> kPmsSectionIcons = {
  'materials': Icons.inventory_2_rounded,
  'deliveries': Icons.receipt_long_rounded,
  'supplies': Icons.local_shipping_rounded,
  'petty': Icons.payments_rounded,
  'requests': Icons.description_rounded,
  'team': Icons.groups_rounded,
  'attendance': Icons.schedule_rounded,
  'timesheet': Icons.timer_rounded,
  'assets': Icons.precision_manufacturing_rounded,
  'fuel': Icons.local_gas_station_rounded,
  'compliance': Icons.verified_user_rounded,
  'finance': Icons.account_balance_rounded,
  'contracts': Icons.assignment_rounded,
  'performance': Icons.trending_up_rounded,
};

const Map<String, Color> kPmsSectionColors = {
  'materials': Color(0xFF0891B2),
  'deliveries': Color(0xFF6366F1),
  'supplies': Color(0xFF0EA5E9),
  'petty': Color(0xFF16A34A),
  'requests': Color(0xFF8B5CF6),
  'team': Color(0xFF0D9488),
  'attendance': Color(0xFF2F6DF6),
  'timesheet': Color(0xFF7C3AED),
  'assets': Color(0xFF64748B),
  'fuel': Color(0xFFF7A23B),
  'compliance': Color(0xFFE5484D),
  'finance': Color(0xFF15803D),
  'contracts': Color(0xFF9333EA),
  'performance': Color(0xFF0891B2),
};

/// One project section — the same shape the portal shows, rendered natively.
/// Every section returns {stats, rows}, so one screen serves all fourteen.
class PmsSectionScreen extends StatefulWidget {
  const PmsSectionScreen({
    super.key,
    required this.projectId,
    required this.code,
    required this.label,
  });

  final int projectId;
  final String code;
  final String label;

  @override
  State<PmsSectionScreen> createState() => _PmsSectionScreenState();
}

class _PmsSectionScreenState extends State<PmsSectionScreen> {
  Future<Map<String, dynamic>>? _f;
  String _q = '';

  Color get _c => kPmsSectionColors[widget.code] ?? Pms.violet;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _f = context.read<AuthProvider>().api.pmsSection(widget.projectId, widget.code);

  @override
  Widget build(BuildContext context) {
    // Sections that accept a new record → an action label for the FAB.
    final createAction = const {
      'deliveries': 'delivery', 'petty': 'expense',
      'timesheet': 'timesheet', 'requests': 'docrequest',
    }[widget.code];
    return Scaffold(
      backgroundColor: Pms.bg,
      appBar: AppBar(
        backgroundColor: _c, foregroundColor: Colors.white, elevation: 0,
        title: Text(widget.label, overflow: TextOverflow.ellipsis),
      ),
      floatingActionButton: createAction == null
          ? null
          : FloatingActionButton.extended(
              backgroundColor: _c, foregroundColor: Colors.white,
              icon: const Icon(Icons.add_rounded),
              label: Text(_createLabel(), style: const TextStyle(fontWeight: FontWeight.w800)),
              onPressed: () => _create(createAction),
            ),
      body: RefreshIndicator(
        onRefresh: () async => setState(_load),
        child: FutureBuilder<Map<String, dynamic>>(
          future: _f,
          builder: (_, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snap.hasError) {
              return ListView(children: [
                const SizedBox(height: 100),
                Center(child: Padding(
                  padding: const EdgeInsets.all(30),
                  child: Text('${snap.error}', textAlign: TextAlign.center,
                      style: const TextStyle(color: Colors.grey)),
                )),
              ]);
            }
            final d = snap.data ?? const {};
            final stats = (d['stats'] as Map?) ?? const {};
            final all = (d['rows'] as List?) ?? const [];
            final rows = _q.isEmpty
                ? all
                : all.where((r) {
                    final m = r as Map;
                    final hay = '${m['title'] ?? ''} ${m['subtitle'] ?? ''} '
                        '${(m['badges'] as List?)?.join(' ') ?? ''}'.toLowerCase();
                    return hay.contains(_q.toLowerCase());
                  }).toList();
            return ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
              if (stats.isNotEmpty) _statsBand(stats),
              if (all.length > 8) ...[
                const SizedBox(height: 10),
                TextField(
                  onChanged: (v) => setState(() => _q = v),
                  decoration: InputDecoration(
                    hintText: tr('ابحث…', 'Search…'),
                    prefixIcon: const Icon(Icons.search_rounded, size: 19),
                    isDense: true, filled: true, fillColor: Colors.white,
                    border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                  ),
                ),
              ],
              const SizedBox(height: 10),
              if (d['empty'] != null && all.isEmpty)
                _empty('${d['empty']}')
              else if (all.isEmpty)
                _empty(tr('لا سجلات في هذا القسم.', 'Nothing in this section yet.'))
              else if (rows.isEmpty)
                _empty(tr('لا نتائج للبحث.', 'No matches.'))
              else ...[
                Padding(
                  padding: const EdgeInsets.only(bottom: 6, right: 2),
                  child: Text(
                      _q.isEmpty
                          ? tr('${all.length} سجل', '${all.length} records')
                          : tr('${rows.length} من ${all.length}', '${rows.length} of ${all.length}'),
                      style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: Colors.grey.shade500)),
                ),
                for (final r in rows) _row(r as Map),
              ],
            ]);
          },
        ),
      ),
    );
  }

  Widget _statsBand(Map stats) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: [_c, Color.lerp(_c, Colors.black, 0.3)!],
              begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.circular(16),
          boxShadow: [BoxShadow(color: _c.withValues(alpha: 0.3), blurRadius: 10, offset: const Offset(0, 4))],
        ),
        child: Row(children: [
          for (final e in stats.entries) ...[
            Expanded(child: Column(children: [
              Text('${e.value}',
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
              Text('${e.key}',
                  maxLines: 2, textAlign: TextAlign.center, overflow: TextOverflow.ellipsis,
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.75),
                      fontSize: 8.5, fontWeight: FontWeight.w700, height: 1.2)),
            ])),
            if (e.key != stats.keys.last)
              Container(width: 1, height: 24, color: Colors.white.withValues(alpha: 0.15)),
          ],
        ]),
      );

  Widget _empty(String t) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 60),
        child: Center(child: Column(children: [
          Icon(kPmsSectionIcons[widget.code] ?? Icons.inbox_rounded,
              size: 40, color: Colors.grey.shade300),
          const SizedBox(height: 10),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 30),
            child: Text(t, textAlign: TextAlign.center,
                style: TextStyle(color: Colors.grey.shade500, fontSize: 12.5, height: 1.6)),
          ),
        ])),
      );

  /// Row state colours. 'expired'/'soon' come from the compliance section and
  /// must read as alarming; everything else is neutral.
  (Color, Color) _stateColors(String? state) {
    switch (state) {
      case 'expired':
        return (const Color(0xFFE5484D), Colors.white);
      case 'soon':
        return (const Color(0xFFF7A23B), Colors.white);
      case 'ok':
      case 'done':
      case 'received':
      case 'closed':
        return (const Color(0xFF16A34A), Colors.white);
      case 'open':
        return (const Color(0xFF16A34A), Colors.white);
      case 'draft':
        return (Colors.grey.shade300, Colors.black87);
      default:
        return (_c.withValues(alpha: 0.12), _c);
    }
  }

  String _createLabel() => {
        'deliveries': tr('تسليم جديد', 'New delivery'),
        'petty': tr('مصروف جديد', 'New expense'),
        'timesheet': tr('كشف جديد', 'New sheet'),
        'requests': tr('طلب مستند', 'Doc request'),
      }[widget.code] ?? tr('إضافة', 'Add');

  /// The create sheet, built per-section from its options endpoint.
  Future<void> _create(String action) async {
    Map<String, dynamic> opts = const {};
    try {
      opts = await context.read<AuthProvider>().api.pmsSectionOptions(widget.projectId, widget.code);
    } catch (_) {/* petty/timesheet need no options */}
    if (!mounted) return;
    final result = await showModalBottomSheet<Map<String, dynamic>>(
      context: context, isScrollControlled: true, showDragHandle: true,
      builder: (ctx) => _CreateSheet(code: widget.code, color: _c, options: opts),
    );
    if (result == null) return;
    try {
      await context.read<AuthProvider>().api.pmsSectionCreate(widget.projectId, action, result);
      if (!mounted) return;
      setState(_load);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('تم الحفظ', 'Saved')), backgroundColor: const Color(0xFF16A34A)));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text('$e'), backgroundColor: const Color(0xFFE5484D)));
      }
    }
  }

  Future<void> _receiveSupply(Map r) async {
    final ok = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(
      title: Text(tr('تأكيد الاستلام', 'Confirm receipt')),
      content: Text(tr('تأكيد استلام «${r['title']}»؟', 'Confirm receiving "${r['title']}"?')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('إلغاء', 'Cancel'))),
        FilledButton(
          style: FilledButton.styleFrom(backgroundColor: const Color(0xFF16A34A)),
          onPressed: () => Navigator.pop(ctx, true), child: Text(tr('استلام', 'Receive'))),
      ],
    ));
    if (ok != true) return;
    try {
      await context.read<AuthProvider>().api.pmsSupplyReceive(r['id'] as int);
      if (!mounted) return;
      setState(_load);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('تم الاستلام', 'Received')), backgroundColor: const Color(0xFF16A34A)));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text('$e'), backgroundColor: const Color(0xFFE5484D)));
      }
    }
  }

  Widget _row(Map r) {
    final badges = (r['badges'] as List?) ?? const [];
    final sc = _stateColors(r['state'] as String?);
    // team rows open an employee file; fuel rows open a vehicle file.
    final opens = '${r['open'] ?? ''}';
    final inner = Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (r['image'] != null) ...[
            CircleAvatar(
              radius: 18,
              backgroundColor: _c.withValues(alpha: 0.1),
              backgroundImage: NetworkImage('${r['image']}'),
              onBackgroundImageError: (_, __) {},
              child: null,
            ),
            const SizedBox(width: 9),
          ] else ...[
            Container(
              width: 36, height: 36, alignment: Alignment.center,
              decoration: BoxDecoration(
                  color: _c.withValues(alpha: 0.09), borderRadius: BorderRadius.circular(11)),
              child: Icon(kPmsSectionIcons[widget.code] ?? Icons.circle, size: 17, color: _c),
            ),
            const SizedBox(width: 9),
          ],
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${r['title']}',
                maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
            if (r['subtitle'] != null)
              Padding(
                padding: const EdgeInsets.only(top: 2),
                child: Text('${r['subtitle']}',
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 10.5, color: Colors.grey.shade600)),
              ),
          ])),
          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
            if (r['value'] != null)
              Row(crossAxisAlignment: CrossAxisAlignment.baseline,
                  textBaseline: TextBaseline.alphabetic, children: [
                Text('${r['value']}',
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _c)),
                if (r['value_label'] != null) ...[
                  const SizedBox(width: 2),
                  Text('${r['value_label']}',
                      style: TextStyle(fontSize: 8, color: Colors.grey.shade500, fontWeight: FontWeight.w700)),
                ],
              ]),
            if (r['state_label'] != null) ...[
              const SizedBox(height: 3),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(color: sc.$1, borderRadius: BorderRadius.circular(6)),
                child: Text('${r['state_label']}',
                    style: TextStyle(fontSize: 8.5, fontWeight: FontWeight.w900, color: sc.$2)),
              ),
            ],
          ]),
        ]),
        if (r['can_receive'] == true) ...[
          const SizedBox(height: 8),
          SizedBox(
            width: double.infinity,
            child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: const Color(0xFF16A34A),
                side: const BorderSide(color: Color(0xFF16A34A)),
                padding: const EdgeInsets.symmetric(vertical: 8),
              ),
              icon: const Icon(Icons.inventory_rounded, size: 16),
              label: Text(tr('تأكيد الاستلام', 'Confirm receipt'),
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12)),
              onPressed: () => _receiveSupply(r),
            ),
          ),
        ],
        if (badges.isNotEmpty) ...[
          const SizedBox(height: 8),
          Wrap(spacing: 5, runSpacing: 5, children: [
            for (final b in badges)
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                decoration: BoxDecoration(
                    color: Colors.grey.withValues(alpha: 0.09),
                    borderRadius: BorderRadius.circular(7)),
                child: Text('$b',
                    style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w600, color: Colors.grey.shade700)),
              ),
          ]),
        ],
      ]),
    );
    if (opens.isEmpty) return inner;
    // Give a tappable row an affordance and open the right file.
    return InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: () {
        if (opens == 'employee') {
          Navigator.push(context, MaterialPageRoute(
              builder: (_) => PmsEmployeeFileScreen(employeeId: r['id'] as int, name: '${r['title']}')));
        } else if (opens == 'vehicle' && r['vehicle_id'] != null) {
          Navigator.push(context, MaterialPageRoute(
              builder: (_) => PmsVehicleFileScreen(vehicleId: r['vehicle_id'] as int, name: '${r['title']}')));
        }
      },
      child: inner,
    );
  }
}

/// The per-section create form. Each section needs different fields, so this
/// picks the right ones from the section code and returns the values map the
/// create endpoint expects (or null on cancel).
class _CreateSheet extends StatefulWidget {
  const _CreateSheet({required this.code, required this.color, required this.options});
  final String code;
  final Color color;
  final Map<String, dynamic> options;
  @override
  State<_CreateSheet> createState() => _CreateSheetState();
}

class _CreateSheetState extends State<_CreateSheet> {
  final _a = TextEditingController();
  final _b = TextEditingController();
  final _c = TextEditingController();
  int? _pick1;
  String? _pick2;
  DateTime? _from, _to;

  @override
  void dispose() {
    _a.dispose(); _b.dispose(); _c.dispose();
    super.dispose();
  }

  String _fmtDate(DateTime d) =>
      '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 0, 16, MediaQuery.of(context).viewInsets.bottom + 16),
      child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start,
          children: _fields()),
    );
  }

  Widget _title(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: Text(t, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: widget.color)),
      );

  Widget _text(TextEditingController c, String label, {int lines = 1, TextInputType? type}) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: TextField(
          controller: c, maxLines: lines, keyboardType: type,
          decoration: InputDecoration(labelText: label, border: const OutlineInputBorder(), isDense: true),
        ),
      );

  Widget _dropInt(String label, List opts, String idKey, String labelKey) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: DropdownButtonFormField<int>(
          initialValue: _pick1,
          decoration: InputDecoration(labelText: label, border: const OutlineInputBorder(), isDense: true),
          isExpanded: true,
          items: [for (final o in opts) DropdownMenuItem(value: o[idKey] as int,
              child: Text('${o[labelKey]}', maxLines: 1, overflow: TextOverflow.ellipsis))],
          onChanged: (v) => setState(() => _pick1 = v),
        ),
      );

  Widget _dropStr(String label, List opts) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: DropdownButtonFormField<String>(
          initialValue: _pick2,
          decoration: InputDecoration(labelText: label, border: const OutlineInputBorder(), isDense: true),
          isExpanded: true,
          items: [for (final o in opts) DropdownMenuItem(value: '${o['value']}',
              child: Text('${o['label']}'))],
          onChanged: (v) => setState(() => _pick2 = v),
        ),
      );

  Widget _dateField(String label, DateTime? value, ValueChanged<DateTime> onPick) => Padding(
        padding: const EdgeInsets.only(bottom: 10),
        child: InkWell(
          onTap: () async {
            final now = DateTime.now();
            final d = await showDatePicker(
              context: context, initialDate: value ?? now,
              firstDate: DateTime(now.year - 2), lastDate: DateTime(now.year + 1));
            if (d != null) onPick(d);
          },
          child: InputDecorator(
            decoration: InputDecoration(labelText: label, border: const OutlineInputBorder(), isDense: true),
            child: Text(value == null ? tr('اختر', 'Pick') : _fmtDate(value),
                style: TextStyle(color: value == null ? Colors.grey : null)),
          ),
        ),
      );

  Widget _submit(bool enabled, Map<String, dynamic> Function() build) => SizedBox(
        width: double.infinity,
        child: FilledButton.icon(
          style: FilledButton.styleFrom(backgroundColor: widget.color),
          onPressed: enabled ? () => Navigator.pop(context, build()) : null,
          icon: const Icon(Icons.check_rounded),
          label: Text(tr('حفظ', 'Save')),
        ),
      );

  List<Widget> _fields() {
    switch (widget.code) {
      case 'deliveries':
        final materials = (widget.options['materials'] as List?) ?? const [];
        return [
          _title(tr('تسليم مواد جديد', 'New material delivery')),
          if (materials.isEmpty)
            Padding(padding: const EdgeInsets.only(bottom: 10),
                child: Text(tr('لا مواد مسجّلة في هذا المشروع.', 'No materials registered on this project.'),
                    style: TextStyle(color: Colors.grey.shade600, fontSize: 12.5)))
          else
            _dropInt(tr('المادة', 'Material'), materials, 'id', 'name'),
          _text(_a, tr('الكمية', 'Quantity'), type: TextInputType.number),
          _text(_b, tr('الموقع', 'Location')),
          _text(_c, tr('اسم المستلم', 'Receiver name')),
          _submit(_pick1 != null && _a.text.trim().isNotEmpty, () => {
            'material_id': _pick1, 'qty': double.tryParse(_a.text.trim()) ?? 0,
            'location': _b.text.trim(), 'receiver_name': _c.text.trim(),
          }),
        ];
      case 'petty':
        final cats = (widget.options['categories'] as List?) ?? const [];
        final cash = (widget.options['cash'] as List?) ?? const [];
        return [
          _title(tr('مصروف نقدي جديد', 'New petty-cash expense')),
          _text(_a, tr('البيان', 'Description')),
          _text(_b, tr('المبلغ', 'Amount'), type: TextInputType.number),
          if (cats.isNotEmpty) _dropStr(tr('التصنيف', 'Category'), cats),
          if (cash.isNotEmpty)
            _dropInt(tr('من عهدة (اختياري)', 'From cash (optional)'), cash, 'id', 'name')
          else
            _text(_c, tr('قيمة العهدة الجديدة', 'New cash amount'), type: TextInputType.number),
          _submit((double.tryParse(_b.text.trim()) ?? 0) > 0, () => {
            'name': _a.text.trim(), 'amount': double.tryParse(_b.text.trim()) ?? 0,
            if (_pick2 != null) 'category': _pick2,
            if (_pick1 != null) 'cash_id': _pick1
            else if (_c.text.trim().isNotEmpty) 'cash_amount': double.tryParse(_c.text.trim()),
          }),
        ];
      case 'timesheet':
        return [
          _title(tr('كشف ساعات جديد', 'New timesheet')),
          Padding(padding: const EdgeInsets.only(bottom: 10),
              child: Text(tr('يُولَّد آليًا من حضور البصمة للفترة المحددة ثم يُرسَل للاعتماد.',
                  'Generated from biometric attendance for the period, then submitted for approval.'),
                  style: TextStyle(color: Colors.grey.shade600, fontSize: 11.5, height: 1.5))),
          _dateField(tr('من', 'From'), _from, (d) => setState(() => _from = d)),
          _dateField(tr('إلى', 'To'), _to, (d) => setState(() => _to = d)),
          _submit(_from != null && _to != null, () => {
            'date_from': _fmtDate(_from!), 'date_to': _fmtDate(_to!),
          }),
        ];
      case 'requests':
        final emps = (widget.options['employees'] as List?) ?? const [];
        final types = (widget.options['doc_types'] as List?) ?? const [];
        return [
          _title(tr('طلب مستند', 'Document request')),
          if (emps.isEmpty)
            Padding(padding: const EdgeInsets.only(bottom: 10),
                child: Text(tr('لا موظفين في قسم هذا المشروع.', 'No employees in this project department.'),
                    style: TextStyle(color: Colors.grey.shade600, fontSize: 12.5)))
          else
            _dropInt(tr('الموظف', 'Employee'), emps, 'id', 'name'),
          if (types.isNotEmpty) _dropStr(tr('نوع المستند', 'Document type'), types),
          _text(_a, tr('ملاحظات (اختياري)', 'Notes (optional)'), lines: 2),
          _submit(_pick1 != null, () => {
            'employee_id': _pick1, if (_pick2 != null) 'doc_type': _pick2,
            'description': _a.text.trim(),
          }),
        ];
      default:
        return [const SizedBox.shrink()];
    }
  }
}
