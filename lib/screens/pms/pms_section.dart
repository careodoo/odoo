import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:http/http.dart' as http;
import 'package:share_plus/share_plus.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'pms_shell.dart';
import 'pms_employee_file.dart';
import 'pms_vehicle_file.dart';
import 'pms_attendance_advanced.dart';
import 'pms_performance.dart';
import '../pdf_report_screen.dart';

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
  'invoices': Icons.receipt_long_rounded,
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
  'invoices': Color(0xFF9D174D),
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
  int _attTab = 0; // attendance: 0 = present records, 1 = absentees

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
      'deliveries': 'delivery', 'petty': 'pettycash',
      'timesheet': 'timesheet', 'requests': 'docrequest',
      'assets': 'custody', 'fuel': 'fuel', 'materials': 'material',
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
            // Two-tab sections: attendance (present/absent) OR requests
            // (outgoing/incoming). Both expose a second list + tab labels.
            final incoming = d['incoming'] as List?;
            final absentees = d['absentees'] as List?;
            final secondList = incoming ?? absentees;
            final hasTabs = secondList != null;
            final isReqTabs = incoming != null;
            final all = (hasTabs && _attTab == 1)
                ? secondList
                : ((d['rows'] as List?) ?? const []);
            final rows = _q.isEmpty
                ? all
                : all.where((r) {
                    final m = r as Map;
                    final hay = '${m['title'] ?? ''} ${m['subtitle'] ?? ''} '
                        '${(m['badges'] as List?)?.join(' ') ?? ''} ${m['search'] ?? ''}'.toLowerCase();
                    // Odoo-style multi-search: comma separates OR alternatives;
                    // spaces within an alternative are AND. So "أحمد, civ 123"
                    // matches «أحمد» OR (a row with both «civ» and «123»).
                    return _q.toLowerCase().split(',').map((g) => g.trim()).where((g) => g.isNotEmpty)
                        .any((group) => group.split(RegExp(r'\s+')).every((w) => hay.contains(w)));
                  }).toList();
            return ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
              if (stats.isNotEmpty) _statsBand(stats),
              if (hasTabs) ...[
                const SizedBox(height: 12),
                Container(
                  padding: const EdgeInsets.all(4),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
                  child: Row(children: [
                    _attSeg(
                        isReqTabs ? '${d['tab_out'] ?? tr('الصادرة', 'Outgoing')}' : tr('الحضور', 'Present'),
                        0, isReqTabs ? Icons.outbox_rounded : Icons.how_to_reg_rounded,
                        ((d['rows'] as List?) ?? const []).length),
                    _attSeg(
                        isReqTabs ? '${d['tab_in'] ?? tr('الواردة', 'Incoming')}' : tr('الغياب', 'Absent'),
                        1, isReqTabs ? Icons.inbox_rounded : Icons.person_off_rounded,
                        secondList.length),
                  ]),
                ),
              ],
              if (widget.code == 'attendance') ...[
                const SizedBox(height: 10),
                SizedBox(width: double.infinity, height: 46, child: FilledButton.icon(
                  style: FilledButton.styleFrom(backgroundColor: const Color(0xFF0E3A5F),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                  onPressed: () => Navigator.push(context, MaterialPageRoute(
                      builder: (_) => AttendanceAdvancedScreen(projectId: widget.projectId))),
                  icon: const Icon(Icons.tune_rounded, size: 19),
                  label: Text(tr('فلاتر متقدّمة + تقرير PDF', 'Advanced filters + PDF report'),
                      style: const TextStyle(fontWeight: FontWeight.w900)),
                )),
              ],
              if (widget.code == 'performance') ...[
                const SizedBox(height: 10),
                SizedBox(width: double.infinity, height: 46, child: FilledButton.icon(
                  style: FilledButton.styleFrom(backgroundColor: Pms.violet,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                  onPressed: () => Navigator.push(context, MaterialPageRoute(
                      builder: (_) => PerformanceScreen(projectId: widget.projectId))),
                  icon: const Icon(Icons.insights_rounded, size: 19),
                  label: Text(tr('لوحة الأداء الكاملة (KPIs)', 'Full performance dashboard'),
                      style: const TextStyle(fontWeight: FontWeight.w900)),
                )),
              ],
              if (all.length > 4 || widget.code == 'team') ...[
                const SizedBox(height: 10),
                TextField(
                  onChanged: (v) => setState(() => _q = v),
                  decoration: InputDecoration(
                    hintText: widget.code == 'team'
                        ? tr('اسم / بادج / مدني / جواز — وأكثر من اسم بفاصلة',
                            'Name / badge / civil ID / passport — several by comma')
                        : tr('ابحث…', 'Search…'),
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
      case 'on_site':                       // worker on site now
        return (const Color(0xFF16A34A), Colors.white);
      case 'attended':                      // attended today, not on site
        return (const Color(0xFF0891B2), Colors.white);
      case 'off':                           // not in today
        return (Colors.grey.shade400, Colors.white);
      case 'draft':
        return (Colors.grey.shade300, Colors.black87);
      default:
        return (_c.withValues(alpha: 0.12), _c);
    }
  }

  String _createLabel() => {
        'deliveries': tr('تسليم جديد', 'New delivery'),
        'timesheet': tr('كشف جديد', 'New sheet'),
        'requests': tr('طلب مستند', 'Doc request'),
        'assets': tr('طلب عهدة', 'Request custody'),
        'petty': tr('طلب عهدة نقدية', 'Request cash custody'),
        'fuel': tr('تسجيل تعبئة', 'Add fuel'),
        'materials': tr('إضافة مادة', 'Add material'),
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

  Widget _attSeg(String label, int idx, IconData ic, int count) {
    final on = _attTab == idx;
    final c = idx == 1 ? const Color(0xFFE11D48) : _c;
    return Expanded(
      child: GestureDetector(
        onTap: () => setState(() { _attTab = idx; _q = ''; }),
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 9),
          decoration: BoxDecoration(color: on ? c : Colors.transparent, borderRadius: BorderRadius.circular(9)),
          child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            Icon(ic, size: 15, color: on ? Colors.white : c),
            const SizedBox(width: 6),
            Text('$label ($count)',
                style: TextStyle(color: on ? Colors.white : Pms.ink, fontWeight: FontWeight.w800, fontSize: 12)),
          ]),
        ),
      ),
    );
  }

  static IconData _markIcon(String k) => switch (k) {
        'flight' => Icons.flight_rounded,
        'badge' => Icons.badge_rounded,
        'gavel' => Icons.gavel_rounded,
        'block' => Icons.block_rounded,
        _ => Icons.circle,
      };
  static Color _hexColor(String h) {
    h = h.replaceAll('#', '');
    if (h.length == 6) h = 'FF$h';
    return Color(int.tryParse(h, radix: 16) ?? 0xFF6B7280);
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
            Row(children: [
              Flexible(child: Text('${r['title']}',
                  maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13))),
              // status marks (airplane if on leave, worker status)
              for (final mk in ((r['marks'] as List?) ?? const [])) Padding(
                padding: const EdgeInsets.only(right: 4),
                child: Icon(_markIcon('${(mk as Map)['icon']}'), size: 14,
                    color: _hexColor('${mk['color'] ?? '#6B7280'}')),
              ),
            ]),
            Row(children: [
              if (r['badge'] != null) Padding(
                padding: const EdgeInsets.only(top: 3, bottom: 1),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                  decoration: BoxDecoration(color: _c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(5)),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Icon(Icons.badge_rounded, size: 10, color: _c),
                    const SizedBox(width: 3),
                    Text('${r['badge']}', style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, color: _c, letterSpacing: 0.3)),
                  ]),
                ),
              ),
              if (r['badge'] != null && r['subtitle'] != null) const SizedBox(width: 6),
              if (r['subtitle'] != null)
                Flexible(child: Padding(
                  padding: const EdgeInsets.only(top: 2),
                  child: Text('${r['subtitle']}',
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: TextStyle(fontSize: 10.5, color: Colors.grey.shade600)),
                )),
            ]),
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
        } else if (opens == 'pettycash') {
          _openPetty(r['id'] as int);
        } else if (opens == 'timesheet') {
          _openTimesheet(r['id'] as int);
        } else if (opens == 'supply') {
          _openSupply(r['id'] as int);
        } else if (opens == 'invoice') {
          _openInvoice(r['id'] as int);
        }
      },
      child: inner,
    );
  }

  Future<void> _openInvoice(int id) async {
    await showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _InvoiceDetailSheet(invoiceId: id),
    );
  }

  Future<void> _openSupply(int id) async {
    await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _SupplyDetailSheet(supplyId: id, color: _c),
    );
    if (mounted) setState(_load);
  }

  Future<void> _openTimesheet(int id) async {
    await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _TimesheetSheet(timesheetId: id, color: _c),
    );
    if (mounted) setState(_load);
  }

  Future<void> _openPetty(int cid) async {
    await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _PettyDetailSheet(cashId: cid, color: _c),
    );
    // Refresh the list in case a workflow action changed a record's state.
    if (mounted) setState(_load);
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
  void initState() {
    super.initState();
    // Some forms gate Save on a text/amount field — rebuild as they change.
    _a.addListener(() => setState(() {}));
    _b.addListener(() => setState(() {}));
  }

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

  /// Searchable employee picker (by name + badge) — a dropdown is unusable for
  /// hundreds of workers.
  Widget _empPicker(String label, List emps) {
    Map? sel;
    for (final e in emps) {
      if ((e as Map)['id'] == _pick1) { sel = e; break; }
    }
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: InkWell(
        onTap: () async {
          final picked = await showModalBottomSheet<int>(
            context: context, isScrollControlled: true, backgroundColor: Colors.white,
            shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
            builder: (_) => _EmpSearchSheet(emps: emps),
          );
          if (picked != null) setState(() => _pick1 = picked);
        },
        child: InputDecorator(
          decoration: InputDecoration(labelText: label, border: const OutlineInputBorder(), isDense: true,
              prefixIcon: const Icon(Icons.person_search_rounded, size: 20)),
          child: Text(
            sel != null
                ? '${sel['name']}${sel['badge'] != null ? ' · ${sel['badge']}' : ''}'
                : tr('اختر الموظف (بحث بالاسم/البادج)', 'Pick employee (search name/badge)'),
            maxLines: 1, overflow: TextOverflow.ellipsis,
            style: TextStyle(color: sel == null ? Colors.grey : null, fontWeight: sel != null ? FontWeight.w700 : null),
          ),
        ),
      ),
    );
  }

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
      case 'materials':
        return [
          _title(tr('إضافة مادة', 'Add material')),
          _text(_a, tr('اسم المادة *', 'Material name *')),
          _submit(_a.text.trim().isNotEmpty, () => {'name': _a.text.trim()}),
        ];
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
        // A professional cash-custody REQUEST (طلب عهدة نقدية); expenses and
        // settlement are handled from the custody's own detail sheet.
        const benTypes = [
          {'value': 'project', 'label': 'مشروع'},
          {'value': 'department', 'label': 'إدارة'},
          {'value': 'person', 'label': 'شخص'},
        ];
        return [
          _title(tr('طلب عهدة نقدية', 'Request cash custody')),
          _text(_b, tr('مبلغ العهدة *', 'Custody amount *'),
              type: const TextInputType.numberWithOptions(decimal: true)),
          _dropStr(tr('صرف إلى', 'Disbursed to'), benTypes),
          _text(_a, tr('سبب العهدة', 'Reason'), lines: 2),
          _submit((double.tryParse(_b.text.trim()) ?? 0) > 0, () => {
            'amount': double.tryParse(_b.text.trim()) ?? 0,
            'beneficiary_type': _pick2 ?? 'project',
            'reason': _a.text.trim(),
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
            _empPicker(tr('الموظف', 'Employee'), emps),
          if (types.isNotEmpty) _dropStr(tr('نوع المستند', 'Document type'), types),
          _text(_a, tr('ملاحظات (اختياري)', 'Notes (optional)'), lines: 2),
          _submit(_pick1 != null, () => {
            'employee_id': _pick1, if (_pick2 != null) 'doc_type': _pick2,
            'description': _a.text.trim(),
          }),
        ];
      case 'assets':
        final emps = (widget.options['employees'] as List?) ?? const [];
        final types = (widget.options['item_types'] as List?) ?? const [];
        return [
          _title(tr('طلب عهدة', 'Request custody')),
          _text(_a, tr('اسم العهدة *', 'Custody item *')),
          if (types.isNotEmpty) _dropStr(tr('نوع العهدة', 'Type'), types),
          if (emps.isEmpty)
            Padding(padding: const EdgeInsets.only(bottom: 10),
                child: Text(tr('لا موظفين في قسم هذا المشروع.', 'No employees in this project department.'),
                    style: TextStyle(color: Colors.grey.shade600, fontSize: 12.5)))
          else
            _empPicker(tr('الموظف المستلم *', 'Assigned to *'), emps),
          _text(_b, tr('القيمة (اختياري)', 'Value (optional)'),
              type: const TextInputType.numberWithOptions(decimal: true)),
          _text(_c, tr('الوصف / ملاحظات', 'Description / notes'), lines: 2),
          _submit(_a.text.trim().isNotEmpty && _pick1 != null, () => {
            'name': _a.text.trim(),
            if (_pick2 != null) 'item_type': _pick2,
            if (_pick1 != null) 'employee_id': _pick1,
            if (_b.text.trim().isNotEmpty) 'value': _b.text.trim(),
            if (_c.text.trim().isNotEmpty) 'description': _c.text.trim(),
          }),
        ];
      case 'fuel':
        final vehicles = (widget.options['vehicles'] as List?) ?? const [];
        return [
          _title(tr('تسجيل تعبئة وقود', 'Add fuel record')),
          if (vehicles.isEmpty)
            Padding(padding: const EdgeInsets.only(bottom: 10),
                child: Text(tr('لا سيارات في قسم هذا المشروع.', 'No vehicles in this project department.'),
                    style: TextStyle(color: Colors.grey.shade600, fontSize: 12.5)))
          else
            _dropInt(tr('السيارة', 'Vehicle'), vehicles, 'id', 'name'),
          _text(_b, tr('اللترات', 'Litres'), type: const TextInputType.numberWithOptions(decimal: true)),
          _text(_a, tr('قراءة العدّاد (اختياري)', 'Odometer (optional)'), type: TextInputType.number),
          _submit(_pick1 != null && (double.tryParse(_b.text.trim()) ?? 0) > 0, () => {
            'vehicle_id': _pick1,
            'liters': double.tryParse(_b.text.trim()) ?? 0,
            if (_a.text.trim().isNotEmpty) 'odometer': double.tryParse(_a.text.trim()),
          }),
        ];
      default:
        return [const SizedBox.shrink()];
    }
  }
}

/// Cash-custody detail — the money at a glance (amount / spent / remaining),
/// the expenses behind it, and the workflow buttons to move it forward
/// (request → approve → disburse → settle → close).
class _PettyDetailSheet extends StatefulWidget {
  final int cashId;
  final Color color;
  const _PettyDetailSheet({required this.cashId, required this.color});
  @override
  State<_PettyDetailSheet> createState() => _PettyDetailSheetState();
}

class _PettyDetailSheetState extends State<_PettyDetailSheet> {
  Map<String, dynamic>? _d;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.pmsPettyDetail(widget.cashId);
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  Future<void> _run(String action) async {
    // «تقديم التسوية» opens a real settlement record to fill + attach, not a
    // one-tap state change.
    if (action == 'settle') {
      final done = await showModalBottomSheet<bool>(
        context: context, isScrollControlled: true, backgroundColor: Colors.white,
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
        builder: (_) => _SettlementSheet(cashId: widget.cashId, color: widget.color,
            remaining: numOf((_d ?? const {})['remaining'], 0).toDouble()),
      );
      if (done == true) await _load();
      return;
    }
    setState(() => _busy = true);
    try {
      final res = await context.read<AuthProvider>().api.pmsPettyAction(widget.cashId, action);
      if (mounted) setState(() { _d = {...?_d, 'state': res['state'], 'actions': res['actions']}; _busy = false; });
      await _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(tr('تم تنفيذ الإجراء', 'Done')), backgroundColor: Pms.green));
      }
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Pms.red));
      }
    }
  }

  Widget _money(String label, num? v, Color c) => Expanded(
        child: Column(children: [
          Text('${v ?? 0}', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: c)),
          const SizedBox(height: 2),
          Text(label, style: const TextStyle(fontSize: 10.5, color: Pms.slate, fontWeight: FontWeight.w700)),
        ]),
      );

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.62, maxChildSize: 0.95, minChildSize: 0.4,
      builder: (_, sc) {
        if (_error != null) {
          return Center(child: Padding(padding: const EdgeInsets.all(24), child: Text('$_error')));
        }
        if (_d == null) return const SizedBox(height: 220, child: Center(child: CircularProgressIndicator()));
        final d = _d!;
        final actions = (d['actions'] as List?) ?? const [];
        final expenses = (d['expenses'] as List?) ?? const [];
        return Stack(children: [
          ListView(controller: sc, padding: EdgeInsets.zero, children: [
            // header
            Container(
              padding: const EdgeInsets.fromLTRB(20, 14, 20, 18),
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: [widget.color, widget.color.withValues(alpha: 0.75)],
                    begin: Alignment.topRight, end: Alignment.bottomLeft),
                borderRadius: const BorderRadius.vertical(top: Radius.circular(22))),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Center(child: Container(width: 42, height: 4,
                    decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(4)))),
                const SizedBox(height: 12),
                Row(children: [
                  const Icon(Icons.payments_rounded, color: Colors.white),
                  const SizedBox(width: 8),
                  Expanded(child: Text('${d['name'] ?? ''}',
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16))),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.22), borderRadius: BorderRadius.circular(20)),
                    child: Text('${d['state_label'] ?? ''}',
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 11)),
                  ),
                ]),
                const SizedBox(height: 14),
                Container(
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(14)),
                  child: Row(children: [
                    _money(tr('العهدة', 'Custody'), d['amount'] as num?, Colors.white),
                    Container(width: 1, height: 30, color: Colors.white24),
                    _money(tr('المصروف', 'Spent'), d['spent'] as num?, Colors.white),
                    Container(width: 1, height: 30, color: Colors.white24),
                    _money(tr('المتبقّي', 'Remaining'), d['remaining'] as num?, Colors.white),
                  ]),
                ),
              ]),
            ),
            // workflow actions
            if (actions.isNotEmpty) Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 2),
              child: Wrap(spacing: 8, runSpacing: 8, children: [
                for (final a in actions)
                  SizedBox(height: 42, child: (a as Map)['style'] == 'primary'
                    ? ElevatedButton(
                        style: ElevatedButton.styleFrom(backgroundColor: widget.color, foregroundColor: Colors.white,
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                        onPressed: _busy ? null : () => _run('${a['key']}'),
                        child: Text('${a['ar']}', style: const TextStyle(fontWeight: FontWeight.w800)))
                    : OutlinedButton(
                        style: OutlinedButton.styleFrom(
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                        onPressed: _busy ? null : () => _run('${a['key']}'),
                        child: Text('${a['ar']}', style: const TextStyle(fontWeight: FontWeight.w800)))),
              ]),
            ),
            // meta
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 14, 18, 0),
              child: Column(children: [
                if (d['reason'] != null) _kvp(tr('السبب', 'Reason'), '${d['reason']}'),
                if (d['custodian'] != null) _kvp(tr('المسؤول', 'Custodian'), '${d['custodian']}'),
                if (d['request_date'] != null) _kvp(tr('تاريخ الطلب', 'Requested'), '${d['request_date']}'),
                if (d['disbursed_date'] != null) _kvp(tr('تاريخ الصرف', 'Disbursed'), '${d['disbursed_date']}'),
              ]),
            ),
            // settlements — with a printable report each
            if (((d['settlement_list'] as List?) ?? const []).isNotEmpty) ...[
              Padding(
                padding: const EdgeInsets.fromLTRB(18, 14, 18, 6),
                child: Text(tr('التسويات', 'Settlements'),
                    style: const TextStyle(fontWeight: FontWeight.w900, color: Pms.ink, fontSize: 14)),
              ),
              for (final s in (d['settlement_list'] as List).cast<Map>())
                Container(
                  margin: const EdgeInsets.fromLTRB(16, 0, 16, 6),
                  padding: const EdgeInsets.fromLTRB(12, 8, 8, 8),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.black12)),
                  child: Row(children: [
                    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${s['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
                      Row(children: [
                        if (s['date'] != null) Text('${s['date']}', style: const TextStyle(fontSize: 10.5, color: Pms.slate)),
                        if (s['amount'] != null) ...[
                          const SizedBox(width: 8),
                          Text('${s['amount']}', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: widget.color)),
                        ],
                        if (s['state_label'] != null) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                            decoration: BoxDecoration(color: widget.color.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(6)),
                            child: Text('${s['state_label']}', style: TextStyle(fontSize: 9, fontWeight: FontWeight.w800, color: widget.color)),
                          ),
                        ],
                      ]),
                    ])),
                    OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(foregroundColor: widget.color,
                          side: BorderSide(color: widget.color.withValues(alpha: 0.5)),
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
                      onPressed: () => Navigator.push(context, MaterialPageRoute(
                          builder: (_) => PdfReportScreen(
                              path: '/api/v1/pms/settlement/${s['id']}/report',
                              title: tr('تقرير التسوية', 'Settlement report'),
                              fileName: 'settlement-${s['id']}.pdf'))),
                      icon: const Icon(Icons.print_rounded, size: 16),
                      label: Text(tr('طباعة', 'Print'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 11.5)),
                    ),
                  ]),
                ),
            ],
            // expenses
            if (expenses.isNotEmpty) ...[
              Padding(
                padding: const EdgeInsets.fromLTRB(18, 14, 18, 6),
                child: Text(tr('المصروفات (${expenses.length})', 'Expenses (${expenses.length})'),
                    style: const TextStyle(fontWeight: FontWeight.w900, color: Pms.ink, fontSize: 14)),
              ),
              for (final e in expenses)
                Container(
                  margin: const EdgeInsets.fromLTRB(16, 0, 16, 6),
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.black12)),
                  child: Row(children: [
                    Expanded(child: Text('${(e as Map)['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5))),
                    Text('${e['amount'] ?? ''}', style: TextStyle(fontWeight: FontWeight.w900, color: widget.color)),
                  ]),
                ),
            ],
            const SizedBox(height: 24),
          ]),
          if (_busy) const Positioned.fill(child: ColoredBox(color: Color(0x11000000),
              child: Center(child: CircularProgressIndicator()))),
        ]);
      },
    );
  }

  Widget _kvp(String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 100, child: Text(k, style: const TextStyle(color: Pms.slate, fontSize: 12))),
          Expanded(child: Text(v, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: Pms.ink))),
        ]),
      );
}

/// A timesheet: its lines with the editable «actual» days (draft only), plus
/// submit-for-approval and delete-draft — the module's policy, on a phone.
class _TimesheetSheet extends StatefulWidget {
  final int timesheetId;
  final Color color;
  const _TimesheetSheet({required this.timesheetId, required this.color});
  @override
  State<_TimesheetSheet> createState() => _TimesheetSheetState();
}

class _TimesheetSheetState extends State<_TimesheetSheet> {
  Map<String, dynamic>? _d;
  String? _error;
  bool _busy = false;
  String _q = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.pmsTimesheetDetail(widget.timesheetId);
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  Future<void> _editLine(Map line) async {
    final ctrl = TextEditingController(text: '${line['actual'] ?? 0}');
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text('${line['employee']}', style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w900)),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          Text(tr('المتوقّع: ${line['count'] ?? 0} يوم', 'Expected: ${line['count'] ?? 0}'),
              style: const TextStyle(color: Pms.slate, fontSize: 12)),
          const SizedBox(height: 12),
          TextField(
            controller: ctrl, keyboardType: TextInputType.number, autofocus: true,
            decoration: InputDecoration(labelText: tr('الأيام الفعلية', 'Actual days'),
                border: const OutlineInputBorder()),
          ),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
          FilledButton(
              style: FilledButton.styleFrom(backgroundColor: widget.color),
              onPressed: () => Navigator.pop(c, true), child: Text(tr('حفظ', 'Save'))),
        ],
      ),
    );
    if (ok != true) return;
    final v = int.tryParse(ctrl.text.trim());
    if (v == null) return;
    try {
      final res = await context.read<AuthProvider>().api.pmsTimesheetLineWrite(line['id'] as int, v);
      setState(() { line['actual'] = res['actual']; line['diff'] = res['diff']; });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Pms.red));
      }
    }
  }

  Future<void> _run(String action, {bool confirm = false}) async {
    if (confirm) {
      final ok = await showDialog<bool>(
        context: context,
        builder: (c) => AlertDialog(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
          title: Text(tr('حذف المسودة', 'Delete draft'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
          content: Text(tr('سيُحذف الكشف نهائيًّا. متابعة؟', 'The sheet will be permanently deleted. Continue?')),
          actions: [
            TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('تراجع', 'Back'))),
            FilledButton(style: FilledButton.styleFrom(backgroundColor: Pms.red),
                onPressed: () => Navigator.pop(c, true), child: Text(tr('حذف', 'Delete'))),
          ],
        ),
      );
      if (ok != true) return;
    }
    setState(() => _busy = true);
    try {
      final res = await context.read<AuthProvider>().api.pmsTimesheetAction(widget.timesheetId, action);
      if (!mounted) return;
      if (res['deleted'] != null || action == 'delete') {
        Navigator.pop(context, true);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(tr('تم حذف المسودة', 'Draft deleted')), backgroundColor: Pms.green));
        return;
      }
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('تم تقديم الكشف للاعتماد', 'Timesheet submitted')), backgroundColor: Pms.green));
      await _load();
      setState(() => _busy = false);
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Pms.red));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.85, maxChildSize: 0.96, minChildSize: 0.5,
      builder: (_, sc) {
        if (_error != null) return Center(child: Padding(padding: const EdgeInsets.all(24), child: Text('$_error')));
        if (_d == null) return const SizedBox(height: 240, child: Center(child: CircularProgressIndicator()));
        final d = _d!;
        final canEdit = d['can_edit'] == true;
        final actions = (d['actions'] as List?) ?? const [];
        final allLines = (d['lines'] as List?) ?? const [];
        final lines = _q.isEmpty ? allLines
            : allLines.where((l) => '${(l as Map)['search'] ?? ''}'.contains(_q.toLowerCase())).toList();
        return Stack(children: [
          Column(children: [
            // header
            Container(
              padding: const EdgeInsets.fromLTRB(18, 14, 18, 16),
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: [widget.color, Color.lerp(widget.color, Colors.black, 0.3)!],
                    begin: Alignment.topRight, end: Alignment.bottomLeft),
                borderRadius: const BorderRadius.vertical(top: Radius.circular(22))),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Center(child: Container(width: 40, height: 4,
                    decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(4)))),
                const SizedBox(height: 12),
                Row(children: [
                  const Icon(Icons.timer_rounded, color: Colors.white),
                  const SizedBox(width: 8),
                  Expanded(child: Text('${d['name'] ?? ''}',
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15))),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.22), borderRadius: BorderRadius.circular(20)),
                    child: Text('${d['state_label'] ?? ''}',
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 11)),
                  ),
                ]),
                const SizedBox(height: 6),
                Text('${d['date_from'] ?? ''} → ${d['date_to'] ?? ''}${d['department'] != null ? ' · ${d['department']}' : ''}',
                    style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 11.5)),
                if (canEdit) Padding(
                  padding: const EdgeInsets.only(top: 6),
                  child: Text(tr('اضغط على أي سطر لتعديل الأيام الفعلية', 'Tap a row to edit actual days'),
                      style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 10.5)),
                ),
              ]),
            ),
            // search
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 10, 12, 6),
              child: TextField(
                onChanged: (v) => setState(() => _q = v),
                decoration: InputDecoration(
                  hintText: tr('ابحث بالاسم أو البادج…', 'Search by name or badge…'),
                  prefixIcon: const Icon(Icons.search_rounded, size: 19),
                  isDense: true, filled: true, fillColor: Pms.bg,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                ),
              ),
            ),
            // lines
            Expanded(child: ListView.builder(
              controller: sc,
              padding: const EdgeInsets.fromLTRB(12, 4, 12, 90),
              itemCount: lines.length,
              itemBuilder: (_, i) {
                final l = lines[i] as Map;
                final diff = l['diff'];
                final dc = (diff is num && diff < 0) ? Pms.red : (diff is num && diff > 0 ? Pms.amber : Pms.green);
                return Container(
                  margin: const EdgeInsets.only(bottom: 6),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12),
                      border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
                  clipBehavior: Clip.antiAlias,
                  child: Material(color: Colors.transparent, child: InkWell(
                    onTap: canEdit ? () => _editLine(l) : null,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                      child: Row(children: [
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text('${l['employee']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5)),
                          if (l['badge'] != null) Text('${tr('بادج', 'Badge')} ${l['badge']}',
                              style: const TextStyle(fontSize: 9.5, color: Pms.slate)),
                        ])),
                        _tsNum(tr('متوقّع', 'Exp'), '${l['count'] ?? 0}', Pms.slate),
                        _tsNum(tr('فعلي', 'Act'), '${l['actual'] ?? 0}', widget.color),
                        _tsNum(tr('فرق', 'Diff'), '${l['diff'] ?? 0}', dc),
                        if (canEdit) Material(
                          color: widget.color.withValues(alpha: 0.12),
                          borderRadius: BorderRadius.circular(9),
                          child: InkWell(
                            borderRadius: BorderRadius.circular(9),
                            onTap: () => _editLine(l),
                            child: Padding(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
                              child: Row(mainAxisSize: MainAxisSize.min, children: [
                                Icon(Icons.edit_rounded, size: 13, color: widget.color),
                                const SizedBox(width: 3),
                                Text(tr('تعديل', 'Edit'),
                                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: widget.color)),
                              ]),
                            ),
                          ),
                        ),
                      ]),
                    ),
                  )),
                );
              },
            )),
          ]),
          // actions bar
          if (actions.isNotEmpty) Positioned(left: 0, right: 0, bottom: 0, child: Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: Colors.white, boxShadow: [
              BoxShadow(color: Colors.black.withValues(alpha: 0.08), blurRadius: 10, offset: const Offset(0, -3))]),
            child: Row(children: [
              for (final a in actions) Expanded(child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 4),
                child: SizedBox(height: 46, child: (a as Map)['style'] == 'primary'
                  ? ElevatedButton.icon(
                      style: ElevatedButton.styleFrom(backgroundColor: widget.color, foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                      onPressed: _busy ? null : () => _run('${a['key']}'),
                      icon: const Icon(Icons.send_rounded, size: 18),
                      label: Text('${a['ar']}', style: const TextStyle(fontWeight: FontWeight.w800)))
                  : OutlinedButton.icon(
                      style: OutlinedButton.styleFrom(foregroundColor: Pms.red,
                          side: const BorderSide(color: Pms.red),
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                      onPressed: _busy ? null : () => _run('${a['key']}', confirm: a['confirm'] == true),
                      icon: const Icon(Icons.delete_outline_rounded, size: 18),
                      label: Text('${a['ar']}', style: const TextStyle(fontWeight: FontWeight.w800)))),
              )),
            ]),
          )),
        ]);
      },
    );
  }

  Widget _tsNum(String label, String v, Color c) => Container(
        width: 48,
        margin: const EdgeInsets.only(right: 4),
        child: Column(children: [
          Text(v, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: c)),
          Text(label, style: const TextStyle(fontSize: 8.5, color: Pms.slate)),
        ]),
      );
}

/// The cash-custody settlement record: enter the settlement data, list the
/// expenses being settled, attach receipts, then submit for approval.
class _SettlementSheet extends StatefulWidget {
  final int cashId;
  final Color color;
  final double remaining;
  const _SettlementSheet({required this.cashId, required this.color, required this.remaining});
  @override
  State<_SettlementSheet> createState() => _SettlementSheetState();
}

class _SettlementSheetState extends State<_SettlementSheet> {
  final _note = TextEditingController();
  DateTime _date = DateTime.now();
  final List<Map<String, dynamic>> _expenses = [];
  final List<String> _images = [];
  bool _busy = false;

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  double get _total => _expenses.fold(0.0, (a, e) => a + ((e['amount'] as num?)?.toDouble() ?? 0));

  Future<void> _addExpense() async {
    final name = TextEditingController();
    final amount = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text(tr('بند مصروف', 'Expense line'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          TextField(controller: name, autofocus: true,
              decoration: InputDecoration(labelText: tr('البيان', 'Description'), border: const OutlineInputBorder())),
          const SizedBox(height: 10),
          TextField(controller: amount, keyboardType: const TextInputType.numberWithOptions(decimal: true),
              decoration: InputDecoration(labelText: tr('المبلغ', 'Amount'), border: const OutlineInputBorder())),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('إلغاء', 'Cancel'))),
          FilledButton(style: FilledButton.styleFrom(backgroundColor: widget.color),
              onPressed: () => Navigator.pop(c, true), child: Text(tr('إضافة', 'Add'))),
        ],
      ),
    );
    if (ok != true) return;
    final amt = double.tryParse(amount.text.trim()) ?? 0;
    if (name.text.trim().isEmpty || amt <= 0) return;
    setState(() => _expenses.add({'name': name.text.trim(), 'amount': amt}));
  }

  Future<void> _pickImage(ImageSource src) async {
    try {
      final x = await ImagePicker().pickImage(source: src, maxWidth: 1600, imageQuality: 70);
      if (x == null) return;
      final bytes = await x.readAsBytes();
      setState(() => _images.add(base64Encode(bytes)));
    } catch (_) {}
  }

  Future<void> _submit() async {
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.pmsPettySettlement(widget.cashId, {
        'note': _note.text.trim(),
        'date': _date.toIso8601String().substring(0, 10),
        'expenses': _expenses,
        'images': _images,
        'submit': true,
      });
      if (!mounted) return;
      Navigator.pop(context, true);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('تم تقديم التسوية للاعتماد', 'Settlement submitted')), backgroundColor: Pms.green));
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Pms.red));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: DraggableScrollableSheet(
        expand: false, initialChildSize: 0.75, maxChildSize: 0.95,
        builder: (_, sc) => ListView(controller: sc, padding: const EdgeInsets.fromLTRB(18, 12, 18, 20), children: [
          Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 14),
              decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(4)))),
          Row(children: [
            Icon(Icons.fact_check_rounded, color: widget.color),
            const SizedBox(width: 8),
            Text(tr('تقديم تسوية العهدة', 'Custody settlement'),
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16.5)),
          ]),
          const SizedBox(height: 4),
          Text(tr('المتبقّي من العهدة: ${widget.remaining}', 'Remaining: ${widget.remaining}'),
              style: const TextStyle(color: Pms.slate, fontSize: 12)),
          const SizedBox(height: 14),
          // date
          InkWell(
            onTap: () async {
              final d = await showDatePicker(context: context, initialDate: _date,
                  firstDate: DateTime(2020), lastDate: DateTime(2100));
              if (d != null) setState(() => _date = d);
            },
            child: InputDecorator(
              decoration: InputDecoration(labelText: tr('تاريخ التسوية', 'Settlement date'),
                  prefixIcon: const Icon(Icons.event_rounded),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12))),
              child: Text(_date.toIso8601String().substring(0, 10), style: const TextStyle(fontWeight: FontWeight.w700)),
            ),
          ),
          const SizedBox(height: 12),
          TextField(controller: _note, maxLines: 2,
              decoration: InputDecoration(labelText: tr('ملاحظات التسوية', 'Notes'),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)))),
          const SizedBox(height: 16),
          // expenses
          Row(children: [
            Text(tr('بنود المصروفات', 'Expense lines'),
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: Pms.ink)),
            const Spacer(),
            TextButton.icon(onPressed: _addExpense, icon: const Icon(Icons.add_rounded, size: 18),
                label: Text(tr('إضافة بند', 'Add'))),
          ]),
          if (_expenses.isEmpty)
            Text(tr('لا بنود بعد', 'No lines yet'), style: const TextStyle(color: Pms.slate, fontSize: 12))
          else
            for (var i = 0; i < _expenses.length; i++) Container(
              margin: const EdgeInsets.only(bottom: 6),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
              decoration: BoxDecoration(color: Pms.bg, borderRadius: BorderRadius.circular(10)),
              child: Row(children: [
                Expanded(child: Text('${_expenses[i]['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5))),
                Text('${_expenses[i]['amount']}', style: TextStyle(fontWeight: FontWeight.w900, color: widget.color)),
                IconButton(icon: const Icon(Icons.close_rounded, size: 17, color: Pms.red),
                    onPressed: () => setState(() => _expenses.removeAt(i))),
              ]),
            ),
          if (_expenses.isNotEmpty) Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Row(children: [
              const Spacer(),
              Text(tr('الإجمالي: ${_total.toStringAsFixed(2)}', 'Total: ${_total.toStringAsFixed(2)}'),
                  style: TextStyle(fontWeight: FontWeight.w900, color: widget.color, fontSize: 13)),
            ]),
          ),
          const SizedBox(height: 16),
          // attachments
          Text(tr('المرفقات (إيصالات)', 'Attachments (receipts)'),
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: Pms.ink)),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (var i = 0; i < _images.length; i++)
              Stack(children: [
                ClipRRect(borderRadius: BorderRadius.circular(10),
                    child: Image.memory(base64Decode(_images[i]), width: 62, height: 62, fit: BoxFit.cover)),
                Positioned(right: 0, top: 0, child: GestureDetector(
                  onTap: () => setState(() => _images.removeAt(i)),
                  child: Container(decoration: const BoxDecoration(color: Pms.red, shape: BoxShape.circle),
                      child: const Icon(Icons.close, size: 15, color: Colors.white)),
                )),
              ]),
            OutlinedButton.icon(onPressed: () => _pickImage(ImageSource.camera),
                icon: const Icon(Icons.photo_camera_rounded, size: 18), label: Text(tr('كاميرا', 'Camera'))),
            OutlinedButton.icon(onPressed: () => _pickImage(ImageSource.gallery),
                icon: const Icon(Icons.attach_file_rounded, size: 18), label: Text(tr('ملف', 'File'))),
          ]),
          const SizedBox(height: 22),
          SizedBox(height: 50, child: FilledButton.icon(
            style: FilledButton.styleFrom(backgroundColor: widget.color,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
            onPressed: _busy ? null : _submit,
            icon: _busy
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : const Icon(Icons.send_rounded),
            label: Text(tr('تقديم التسوية للاعتماد', 'Submit for approval'),
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
          )),
        ]),
      ),
    );
  }
}

/// Full-screen, pinch-to-zoom image viewer — used by the supply voucher and any
/// tappable photo across the PMS app.
class PmsPhotoView extends StatefulWidget {
  final String url;
  final String? title;
  const PmsPhotoView({super.key, required this.url, this.title});
  @override
  State<PmsPhotoView> createState() => _PmsPhotoViewState();
}

class _PmsPhotoViewState extends State<PmsPhotoView> {
  bool _sharing = false;

  Future<void> _share() async {
    setState(() => _sharing = true);
    try {
      final res = await http.get(Uri.parse(widget.url));
      final ct = res.headers['content-type'] ?? 'image/jpeg';
      final ext = ct.contains('png') ? 'png' : ct.contains('pdf') ? 'pdf' : 'jpg';
      await Share.shareXFiles(
          [XFile.fromData(res.bodyBytes, mimeType: ct, name: 'CARE-image.$ext')],
          text: widget.title);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(tr('تعذّرت المشاركة', 'Could not share'))));
    } finally {
      if (mounted) setState(() => _sharing = false);
    }
  }

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: Colors.black,
        appBar: AppBar(
          backgroundColor: Colors.black, foregroundColor: Colors.white, elevation: 0,
          title: Text(widget.title ?? tr('عرض الصورة', 'Photo'), overflow: TextOverflow.ellipsis),
          actions: [
            IconButton(
              tooltip: tr('مشاركة / طباعة', 'Share / print'),
              onPressed: _sharing ? null : _share,
              icon: _sharing
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(Icons.ios_share_rounded),
            ),
          ],
        ),
        body: Center(
          child: InteractiveViewer(
            minScale: 0.8, maxScale: 5,
            child: Image.network(widget.url,
                loadingBuilder: (c, w, p) => p == null ? w
                    : const CircularProgressIndicator(color: Colors.white),
                errorBuilder: (c, e, s) => const Icon(Icons.broken_image_rounded,
                    color: Colors.white54, size: 60)),
          ),
        ),
      );
}

/// Supply document detail: product lines with images/quantities, per-product
/// Receive (with quantity) / Reject (with reason), and the delivery voucher.
class _SupplyDetailSheet extends StatefulWidget {
  final int supplyId;
  final Color color;
  const _SupplyDetailSheet({required this.supplyId, required this.color});
  @override
  State<_SupplyDetailSheet> createState() => _SupplyDetailSheetState();
}

class _SupplyDetailSheetState extends State<_SupplyDetailSheet> {
  Map<String, dynamic>? _d;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.pmsSupplyDetail(widget.supplyId);
      if (mounted) setState(() { _d = d; _error = null; });
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  Color _stateColor(String s) => switch (s) {
        'received' => Pms.green,
        'partial' => Pms.amber,
        'rejected' => Pms.red,
        'sent' => const Color(0xFF2563EB),
        _ => Pms.slate,
      };

  Future<void> _receiveLine(Map line) async {
    final ctrl = TextEditingController(text: '${numOf(line['qty'], 0)}');
    final ok = await showDialog<bool>(
      context: context,
      builder: (dc) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text(tr('استلام المنتج', 'Receive item'),
            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          Text('${line['name']}', style: const TextStyle(fontSize: 12.5, color: Pms.slate)),
          const SizedBox(height: 12),
          TextField(controller: ctrl, keyboardType: const TextInputType.numberWithOptions(decimal: true),
              autofocus: true,
              decoration: InputDecoration(
                  labelText: tr('الكمية المستلمة', 'Received quantity'),
                  suffixText: '${line['uom'] ?? ''}',
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)))),
          const SizedBox(height: 4),
          Align(alignment: AlignmentDirectional.centerStart,
              child: Text(tr('المطلوب: ${numOf(line['qty'], 0)}', 'Ordered: ${numOf(line['qty'], 0)}'),
                  style: const TextStyle(fontSize: 11, color: Pms.slate))),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dc, false), child: Text(tr('إلغاء', 'Cancel'))),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Pms.green),
            onPressed: () => Navigator.pop(dc, true),
            child: Text(tr('تأكيد الاستلام', 'Receive')),
          ),
        ],
      ),
    );
    if (ok != true) return;
    final qty = double.tryParse(ctrl.text.trim().replaceAll(',', '.')) ?? numOf(line['qty'], 0).toDouble();
    if (qty <= 0) return;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.pmsSupplyLineReceive(line['id'] as int, qty);
      await _load();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('تم استلام المنتج', 'Item received')), backgroundColor: Pms.green));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e'), backgroundColor: Pms.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _rejectLine(Map line) async {
    final ctrl = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (dc) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Text(tr('رفض الاستلام', 'Reject receipt'),
            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
        content: TextField(controller: ctrl, maxLines: 2, autofocus: true,
            decoration: InputDecoration(
                labelText: tr('سبب الرفض', 'Reason'),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)))),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dc, false), child: Text(tr('إلغاء', 'Cancel'))),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: Pms.red),
            onPressed: () => Navigator.pop(dc, true),
            child: Text(tr('رفض', 'Reject')),
          ),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.pmsSupplyLineReject(line['id'] as int, ctrl.text.trim());
      await _load();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('تم رفض المنتج', 'Item rejected')), backgroundColor: Pms.red));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e'), backgroundColor: Pms.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _attachVoucher() async {
    final src = await showModalBottomSheet<ImageSource>(
      context: context,
      builder: (bc) => SafeArea(child: Wrap(children: [
        ListTile(leading: const Icon(Icons.photo_camera_rounded), title: Text(tr('كاميرا', 'Camera')),
            onTap: () => Navigator.pop(bc, ImageSource.camera)),
        ListTile(leading: const Icon(Icons.photo_library_rounded), title: Text(tr('المعرض', 'Gallery')),
            onTap: () => Navigator.pop(bc, ImageSource.gallery)),
      ])),
    );
    if (src == null) return;
    try {
      final x = await ImagePicker().pickImage(source: src, maxWidth: 1800, imageQuality: 72);
      if (x == null) return;
      setState(() => _busy = true);
      final b64 = base64Encode(await x.readAsBytes());
      await context.read<AuthProvider>().api.pmsSupplyVoucher(widget.supplyId, b64, 'delivery_voucher.jpg');
      await _load();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('تم إرفاق سند التسليم', 'Delivery voucher attached')), backgroundColor: Pms.green));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e'), backgroundColor: Pms.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _openVoucher(Map voucher) async {
    final api = context.read<AuthProvider>().api;
    final path = '${voucher['path']}';
    if (voucher['is_pdf'] == true) {
      if (!mounted) return;
      Navigator.push(context, MaterialPageRoute(
          builder: (_) => PdfReportScreen(path: path, title: '${voucher['name']}')));
      return;
    }
    final token = await api.token;
    final origin = api.baseUrl.replaceFirst(RegExp(r'/api/v\d+/?$'), '');
    final url = '$origin$path?token=${Uri.encodeQueryComponent(token ?? '')}';
    if (!mounted) return;
    Navigator.push(context, MaterialPageRoute(
        builder: (_) => PmsPhotoView(url: url, title: '${voucher['name']}')));
  }

  Future<void> _receiveAll() async {
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.pmsSupplyReceive(widget.supplyId);
      await _load();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('تم استلام كل البنود', 'All items received')), backgroundColor: Pms.green));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('$e'), backgroundColor: Pms.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.9, maxChildSize: 0.96, minChildSize: 0.5,
      builder: (_, sc) {
        if (_error != null) {
          return Center(child: Padding(padding: const EdgeInsets.all(24),
              child: Text('$_error', style: const TextStyle(color: Pms.red))));
        }
        if (_d == null) return const Center(child: CircularProgressIndicator());
        final d = _d!;
        final lines = (d['lines'] as List?) ?? const [];
        final sm = (d['summary'] as Map?) ?? const {};
        final voucher = d['voucher'] as Map?;
        final st = '${d['state']}';
        final pending = numOf(sm['pending'], 0);
        return ListView(controller: sc, padding: const EdgeInsets.fromLTRB(16, 12, 16, 24), children: [
          Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 14),
              decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(4)))),
          // header
          Row(children: [
            Container(width: 44, height: 44,
                decoration: BoxDecoration(color: widget.color.withValues(alpha: .12),
                    borderRadius: BorderRadius.circular(12)),
                child: Icon(Icons.local_shipping_rounded, color: widget.color)),
            const SizedBox(width: 12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${d['name']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
              if (d['source'] != null)
                Text('${tr('المصدر', 'Source')}: ${d['source']}',
                    style: const TextStyle(fontSize: 11.5, color: Pms.slate)),
            ])),
            Container(padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
                decoration: BoxDecoration(color: _stateColor(st).withValues(alpha: .13),
                    borderRadius: BorderRadius.circular(20)),
                child: Text('${d['state_label']}',
                    style: TextStyle(color: _stateColor(st), fontWeight: FontWeight.w900, fontSize: 11.5))),
          ]),
          const SizedBox(height: 14),
          // summary chips
          Row(children: [
            _sum(tr('البنود', 'Items'), sm['total'], Pms.ink),
            _sum(tr('مستلم', 'Received'), sm['received'], Pms.green),
            _sum(tr('مرفوض', 'Rejected'), sm['rejected'], Pms.red),
            _sum(tr('منتظر', 'Pending'), sm['pending'], Pms.amber),
          ]),
          const SizedBox(height: 16),
          // delivery voucher
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: Pms.bg, borderRadius: BorderRadius.circular(14)),
            child: Row(children: [
              const Icon(Icons.description_rounded, color: Pms.slate),
              const SizedBox(width: 10),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(tr('سند التسليم', 'Delivery voucher'),
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
                Text(voucher != null ? '${voucher['name']}' : tr('غير مرفق', 'Not attached'),
                    style: const TextStyle(fontSize: 11.5, color: Pms.slate)),
              ])),
              if (voucher != null)
                IconButton(onPressed: () => _openVoucher(voucher),
                    icon: const Icon(Icons.visibility_rounded), color: widget.color),
              IconButton(onPressed: _busy ? null : _attachVoucher,
                  icon: Icon(voucher != null ? Icons.autorenew_rounded : Icons.upload_rounded),
                  color: Pms.slate),
            ]),
          ),
          const SizedBox(height: 16),
          Text(tr('المنتجات', 'Products'),
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: Pms.ink)),
          const SizedBox(height: 8),
          for (final l in lines) _lineCard(l as Map),
          if (pending > 0) ...[
            const SizedBox(height: 14),
            SizedBox(width: double.infinity, height: 48, child: FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: Pms.green,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
              onPressed: _busy ? null : _receiveAll,
              icon: const Icon(Icons.done_all_rounded),
              label: Text(tr('استلام كل البنود المتبقية ($pending)', 'Receive all pending ($pending)'),
                  style: const TextStyle(fontWeight: FontWeight.w900)),
            )),
          ],
        ]);
      },
    );
  }

  Widget _sum(String label, dynamic v, Color c) => Expanded(
        child: Container(
          margin: const EdgeInsets.symmetric(horizontal: 3),
          padding: const EdgeInsets.symmetric(vertical: 10),
          decoration: BoxDecoration(color: c.withValues(alpha: .09), borderRadius: BorderRadius.circular(12)),
          child: Column(children: [
            Text('${v ?? 0}', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: c)),
            const SizedBox(height: 2),
            Text(label, style: const TextStyle(fontSize: 10.5, color: Pms.slate, fontWeight: FontWeight.w700)),
          ]),
        ),
      );

  Widget _lineCard(Map l) {
    final ls = '${l['line_state']}';
    final img = l['image'];
    final done = ls == 'received';
    final rejected = ls == 'rejected';
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFFE5E7EB))),
      child: Column(children: [
        Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(10),
            child: img != null
                ? Image.network('$img', width: 52, height: 52, fit: BoxFit.cover,
                    errorBuilder: (c, e, s) => _imgPlaceholder())
                : _imgPlaceholder(),
          ),
          const SizedBox(width: 11),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${l['name']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
            const SizedBox(height: 3),
            Text('${tr('الكمية', 'Qty')}: ${numOf(l['qty'], 0)} ${l['uom'] ?? ''}'
                '${done ? '  •  ${tr('مستلم', 'received')}: ${numOf(l['received_qty'], 0)}' : ''}',
                style: const TextStyle(fontSize: 12, color: Pms.slate, fontWeight: FontWeight.w600)),
            if (rejected && l['reject_reason'] != null)
              Padding(padding: const EdgeInsets.only(top: 3),
                  child: Text('${tr('السبب', 'Reason')}: ${l['reject_reason']}',
                      style: const TextStyle(fontSize: 11.5, color: Pms.red))),
          ])),
          Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
              decoration: BoxDecoration(color: _stateColor(ls).withValues(alpha: .13),
                  borderRadius: BorderRadius.circular(16)),
              child: Text('${l['line_state_label']}',
                  style: TextStyle(color: _stateColor(ls), fontWeight: FontWeight.w800, fontSize: 10.5))),
        ]),
        if (ls == 'pending') ...[
          const SizedBox(height: 9),
          Row(children: [
            Expanded(child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(foregroundColor: Pms.red,
                  side: const BorderSide(color: Pms.red),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
              onPressed: _busy ? null : () => _rejectLine(l),
              icon: const Icon(Icons.close_rounded, size: 17),
              label: Text(tr('رفض', 'Reject'), style: const TextStyle(fontWeight: FontWeight.w800)),
            )),
            const SizedBox(width: 8),
            Expanded(child: FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: Pms.green,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10))),
              onPressed: _busy ? null : () => _receiveLine(l),
              icon: const Icon(Icons.check_rounded, size: 18),
              label: Text(tr('استلام', 'Receive'), style: const TextStyle(fontWeight: FontWeight.w800)),
            )),
          ]),
        ],
      ]),
    );
  }

  Widget _imgPlaceholder() => Container(width: 52, height: 52,
      color: Pms.bg, child: const Icon(Icons.inventory_2_rounded, color: Pms.slate, size: 24));
}

/// Searchable employee picker sheet — filters by name AND badge as you type.
/// A consistent, professional employee row for ANY employee picker:
/// photo, name, badge, worker status, and a ✈ mark if on leave.
Widget empPickTile(Map e, VoidCallback onTap, {bool selected = false}) {
  final onLeave = e['on_leave'] == true;
  return ListTile(
    onTap: onTap,
    selected: selected, selectedTileColor: Pms.violet.withValues(alpha: 0.06),
    leading: CircleAvatar(radius: 22, backgroundColor: Pms.bg,
        backgroundImage: e['avatar'] != null ? NetworkImage('${e['avatar']}') : null,
        child: e['avatar'] == null ? const Icon(Icons.person, color: Pms.slate) : null),
    title: Text('${e['name']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14)),
    subtitle: Padding(
      padding: const EdgeInsets.only(top: 3),
      child: Wrap(spacing: 6, runSpacing: 4, children: [
        if (e['badge'] != null) Container(
          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
          decoration: BoxDecoration(color: Pms.violet.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(6)),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            const Icon(Icons.badge_rounded, size: 11, color: Pms.violet),
            const SizedBox(width: 3),
            Text('${e['badge']}', style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w900, color: Pms.violet)),
          ]),
        ),
        if (onLeave) const _MiniTag(icon: Icons.flight_rounded, label: 'إجازة', color: Color(0xFF2563EB)),
        if (e['status'] != null) _MiniTag(icon: Icons.circle, label: '${e['status']}', color: Pms.slate),
      ]),
    ),
    trailing: selected ? const Icon(Icons.check_circle_rounded, color: Pms.violet) : null,
  );
}

class _MiniTag extends StatelessWidget {
  final IconData icon;
  final String label;
  final Color color;
  const _MiniTag({required this.icon, required this.label, required this.color});
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
        decoration: BoxDecoration(color: color.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(6)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(icon, size: 10, color: color),
          const SizedBox(width: 3),
          Text(label, style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, color: color)),
        ]),
      );
}

class _EmpSearchSheet extends StatefulWidget {
  final List emps;
  const _EmpSearchSheet({required this.emps});
  @override
  State<_EmpSearchSheet> createState() => _EmpSearchSheetState();
}

class _EmpSearchSheetState extends State<_EmpSearchSheet> {
  String _q = '';
  @override
  Widget build(BuildContext context) {
    final q = _q.trim().toLowerCase();
    final list = q.isEmpty
        ? widget.emps
        : widget.emps.where((e) {
            final m = e as Map;
            final hay = '${m['search'] ?? '${m['name'] ?? ''} ${m['badge'] ?? ''}'}'.toLowerCase();
            // comma = OR, spaces = AND (same idiom as the section search)
            return q.split(',').map((g) => g.trim()).where((g) => g.isNotEmpty)
                .any((group) => group.split(RegExp(r'\s+')).every((w) => hay.contains(w)));
          }).toList();
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
      child: DraggableScrollableSheet(
        expand: false, initialChildSize: 0.8, maxChildSize: 0.95, minChildSize: 0.5,
        builder: (_, sc) => Column(children: [
          Container(width: 40, height: 4, margin: const EdgeInsets.symmetric(vertical: 10),
              decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(4))),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 10),
            child: TextField(
              autofocus: true,
              onChanged: (v) => setState(() => _q = v),
              decoration: InputDecoration(
                hintText: tr('ابحث بالاسم أو البادج… (فاصلة = أو)', 'Search name or badge… (comma = OR)'),
                prefixIcon: const Icon(Icons.search_rounded),
                isDense: true, filled: true, fillColor: Pms.bg,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
              ),
            ),
          ),
          Expanded(child: list.isEmpty
              ? Center(child: Text(tr('لا نتائج', 'No matches'), style: const TextStyle(color: Pms.slate)))
              : ListView.builder(
                  controller: sc, itemCount: list.length,
                  itemBuilder: (_, i) => empPickTile(list[i] as Map, () => Navigator.pop(context, (list[i] as Map)['id'] as int)),
                )),
        ]),
      ),
    );
  }
}

/// Professional project-invoice detail — mirrors the CAFM client invoice view
/// (paid-status header, tabular lines, totals, payment records, PDF).
class _InvoiceDetailSheet extends StatefulWidget {
  final int invoiceId;
  const _InvoiceDetailSheet({required this.invoiceId});
  @override
  State<_InvoiceDetailSheet> createState() => _InvoiceDetailSheetState();
}

class _InvoiceDetailSheetState extends State<_InvoiceDetailSheet> {
  Map<String, dynamic>? _m;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final m = await context.read<AuthProvider>().api.pmsInvoice(widget.invoiceId);
      if (mounted) setState(() => _m = m);
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.85, maxChildSize: 0.96, minChildSize: 0.5,
      builder: (_, sc) {
        if (_error != null) {
          return Center(child: Padding(padding: const EdgeInsets.all(24),
              child: Text('$_error', style: const TextStyle(color: Pms.red))));
        }
        if (_m == null) return const Center(child: CircularProgressIndicator());
        final m = _m!;
        final residual = numOf(m['amount_residual']);
        final total = numOf(m['amount_total']);
        final paid = numOf(m['amount_paid']);
        final done = residual <= 0.001 && total > 0;
        final part = paid > 0 && residual > 0.001;
        final c = done ? const Color(0xFF16A34A) : (part ? const Color(0xFFF59E0B) : const Color(0xFF7A1340));
        final label = done ? tr('مدفوعة بالكامل', 'Paid in full')
            : (part ? tr('مدفوعة جزئيًا', 'Partly paid') : tr('غير مدفوعة', 'Unpaid'));
        final payments = (m['payments'] as List?) ?? const [];
        return ListView(controller: sc, padding: EdgeInsets.zero, children: [
          Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(top: 10, bottom: 4),
              decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(4)))),
          // status header
          Container(
            margin: const EdgeInsets.fromLTRB(12, 6, 12, 0),
            padding: const EdgeInsets.fromLTRB(18, 16, 18, 15),
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(16),
                gradient: LinearGradient(colors: [c, Color.lerp(c, Colors.black, 0.28)!],
                    begin: Alignment.topRight, end: Alignment.bottomLeft)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text('${m['name']}', style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900))),
                Container(padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 5),
                    decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.22), borderRadius: BorderRadius.circular(20)),
                    child: Text(label, style: const TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.w900))),
              ]),
              if (m['project'] != null) Padding(padding: const EdgeInsets.only(top: 3),
                  child: Text('${m['project']}', style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 11.5))),
              const SizedBox(height: 10),
              Text('${m['amount_total']} ${m['currency'] ?? ''}',
                  style: const TextStyle(color: Colors.white, fontSize: 27, fontWeight: FontWeight.w900)),
              if (residual > 0.001) Padding(padding: const EdgeInsets.only(top: 4),
                  child: Text('${tr('المتبقّي', 'Outstanding')}: ${m['amount_residual']} ${m['currency'] ?? ''}',
                      style: TextStyle(color: Colors.white.withValues(alpha: 0.92), fontSize: 12.5, fontWeight: FontWeight.w700))),
              if (total > 0) Padding(padding: const EdgeInsets.only(top: 10),
                  child: ClipRRect(borderRadius: BorderRadius.circular(6),
                      child: LinearProgressIndicator(value: (paid / total).clamp(0.0, 1.0), minHeight: 7,
                          color: Colors.white, backgroundColor: Colors.white.withValues(alpha: 0.25)))),
              if (m['invoice_date'] != null || m['due_date'] != null) Padding(padding: const EdgeInsets.only(top: 10),
                  child: Text([
                    if (m['invoice_date'] != null) '${tr('التاريخ', 'Date')}: ${m['invoice_date']}',
                    if (m['due_date'] != null) '${tr('الاستحقاق', 'Due')}: ${m['due_date']}',
                  ].join('   ·   '), style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 11.5))),
            ]),
          ),
          if (m['pdf_url'] != null) Padding(padding: const EdgeInsets.fromLTRB(12, 10, 12, 0),
            child: SizedBox(width: double.infinity, height: 44, child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(foregroundColor: const Color(0xFF7A1340),
                  side: const BorderSide(color: Color(0xFF7A1340)),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
              onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
                  url: '${m['pdf_url']}', title: tr('فاتورة ${m['name'] ?? ''}', 'Invoice ${m['name'] ?? ''}'),
                  fileName: 'invoice-${m['name'] ?? ''}.pdf'))),
              icon: const Icon(Icons.picture_as_pdf_rounded, size: 18),
              label: Text(tr('عرض / طباعة PDF', 'View / print PDF'), style: const TextStyle(fontWeight: FontWeight.w800)),
            ))),
          const SizedBox(height: 12),
          // lines table
          Padding(padding: const EdgeInsets.symmetric(horizontal: 14), child: Column(children: [
            _lineRow(tr('البند', 'Item'), tr('كمية', 'Qty'), tr('السعر', 'Price'), tr('الإجمالي', 'Total'), header: true),
            for (final l in ((m['lines'] as List?) ?? const []))
              _lineRow('${(l as Map)['name'] ?? ''}', '${l['qty'] ?? ''}', '${l['price'] ?? ''}', '${l['subtotal'] ?? ''}'),
          ])),
          const SizedBox(height: 12),
          Padding(padding: const EdgeInsets.symmetric(horizontal: 18), child: Column(children: [
            _tot(tr('قبل الضريبة', 'Untaxed'), '${m['amount_untaxed']}'),
            _tot(tr('الضريبة', 'Tax'), '${m['amount_tax']}'),
            _tot(tr('الإجمالي', 'Total'), '${m['amount_total']} ${m['currency'] ?? ''}', bold: true),
            _tot(tr('المدفوع', 'Paid'), '${m['amount_paid']}', color: const Color(0xFF16A34A)),
            _tot(tr('المتبقّي', 'Residual'), '${m['amount_residual']}', color: const Color(0xFFE11D48)),
          ])),
          if (payments.isNotEmpty) ...[
            const SizedBox(height: 12),
            Padding(padding: const EdgeInsets.symmetric(horizontal: 18),
                child: Text(tr('سجلّات الدفع', 'Payment records'), style: const TextStyle(fontWeight: FontWeight.w800))),
            for (final p in payments) ListTile(dense: true,
                leading: const Icon(Icons.payments_rounded, color: Color(0xFF16A34A)),
                title: Text('${(p as Map)['name'] ?? ''}'),
                subtitle: Text('${p['method'] ?? ''} · ${p['date'] ?? ''}'),
                trailing: Text('${p['amount']}', style: const TextStyle(fontWeight: FontWeight.w700))),
          ],
          const SizedBox(height: 24),
        ]);
      },
    );
  }

  Widget _lineRow(String a, String b, String cc, String d, {bool header = false}) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
        decoration: BoxDecoration(
            color: header ? Pms.bg : Colors.white,
            border: Border(bottom: BorderSide(color: Colors.black.withValues(alpha: 0.06)))),
        child: Row(children: [
          Expanded(flex: 4, child: Text(a, style: TextStyle(fontSize: 12, fontWeight: header ? FontWeight.w800 : FontWeight.w600))),
          Expanded(flex: 1, child: Text(b, textAlign: TextAlign.center, style: TextStyle(fontSize: 11.5, fontWeight: header ? FontWeight.w800 : FontWeight.w600))),
          Expanded(flex: 2, child: Text(cc, textAlign: TextAlign.center, style: TextStyle(fontSize: 11.5, fontWeight: header ? FontWeight.w800 : FontWeight.w600))),
          Expanded(flex: 2, child: Text(d, textAlign: TextAlign.end, style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: header ? Pms.ink : Pms.violet))),
        ]),
      );

  Widget _tot(String k, String v, {bool bold = false, Color? color}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(children: [
          Text(k, style: TextStyle(fontSize: 12.5, color: Pms.slate, fontWeight: bold ? FontWeight.w900 : FontWeight.w600)),
          const Spacer(),
          Text(v, style: TextStyle(fontSize: bold ? 15 : 12.5, fontWeight: FontWeight.w900, color: color ?? Pms.ink)),
        ]),
      );
}
