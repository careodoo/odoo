import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'driver_waste_trips.dart';
import 'receiver_waste.dart';
import 'notifications_screen.dart';
import '../core/widgets.dart';

/// Palette for the waste-operations workspace.
class WOps {
  static const green = Color(0xFF16A34A);
  static const deep = Color(0xFF14532D);
  static const mid = Color(0xFF15803D);
  static const bg = Color(0xFFF3F7F4);
  static const ink = Color(0xFF14231A);
  static const slate = Color(0xFF64748B);
  static const amber = Color(0xFFF59E0B);
}

/// Native workspace for CAFM waste staff — role-adaptive:
/// ops_manager → order inbox + driver assignment (+ trips + intake)
/// driver      → my trips
/// receiver    → center intake
class WasteOpsShell extends StatefulWidget {
  const WasteOpsShell({super.key, required this.role});
  final String role; // ops_manager | driver | receiver

  @override
  State<WasteOpsShell> createState() => _WasteOpsShellState();
}

class _WasteOpsShellState extends State<WasteOpsShell> {
  int _tab = 0;

  @override
  Widget build(BuildContext context) {
    final isOps = widget.role == 'ops_manager';
    final isDriver = widget.role == 'driver';
    final isReceiver = widget.role == 'receiver';

    final tabs = <_OpsTab>[
      if (isOps) _OpsTab(Icons.assignment_rounded, tr('الطلبات', 'Orders'), const WasteOpsInbox()),
      if (isOps || isDriver)
        _OpsTab(Icons.local_shipping_rounded, tr('الرحلات', 'Trips'), const DriverWasteTripsScreen()),
      if (isOps || isReceiver)
        _OpsTab(Icons.factory_rounded, tr('الاستلام', 'Intake'), const ReceiverWasteScreen()),
      _OpsTab(Icons.notifications_rounded, tr('الإشعارات', 'Alerts'), const NotificationsScreen()),
      _OpsTab(Icons.person_rounded, tr('حسابي', 'Me'), _MeTab(role: widget.role)),
    ];
    final idx = _tab.clamp(0, tabs.length - 1);

    return Scaffold(
      backgroundColor: WOps.bg,
      body: IndexedStack(index: idx, children: [for (final t in tabs) t.body]),
      bottomNavigationBar: NavigationBarTheme(
        data: NavigationBarThemeData(
          backgroundColor: Colors.white,
          indicatorColor: WOps.green.withValues(alpha: 0.14),
          labelTextStyle: WidgetStateProperty.all(
              const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
        ),
        child: NavigationBar(
          height: 62,
          selectedIndex: idx,
          onDestinationSelected: (i) => setState(() => _tab = i),
          destinations: [
            for (final t in tabs)
              NavigationDestination(icon: Icon(t.icon), selectedIcon: Icon(t.icon, color: WOps.green), label: t.label),
          ],
        ),
      ),
    );
  }
}

class _OpsTab {
  const _OpsTab(this.icon, this.label, this.body);
  final IconData icon;
  final String label;
  final Widget body;
}

/// ===================== OPS MANAGER: order inbox =====================
class WasteOpsInbox extends StatefulWidget {
  const WasteOpsInbox({super.key});
  @override
  State<WasteOpsInbox> createState() => _WasteOpsInboxState();
}

class _WasteOpsInboxState extends State<WasteOpsInbox> {
  String _filter = 'unassigned';
  late Future<List<dynamic>> _f;

  static const _filters = [
    ['unassigned', 'بانتظار إسناد', 'To assign'],
    ['open', 'جارية', 'Open'],
    ['done', 'منتهية', 'Done'],
  ];

  static const _stateColor = {
    'draft': WOps.amber, 'scheduled': Color(0xFF2563EB), 'pickuped': Color(0xFF7C3AED),
    'arrived': Color(0xFF0891B2), 'processing': Color(0xFFD97706),
    'delivered': WOps.mid, 'completed': WOps.green, 'cancelled': Color(0xFFB91C1C),
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => setState(() => _f = context.read<AuthProvider>().api.wasteOpsOrders(filter: _filter));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: WOps.bg,
      body: RefreshIndicator(
        onRefresh: () async => _load(),
        child: CustomScrollView(slivers: [
          SliverAppBar(
            pinned: true,
            expandedHeight: 96,
            backgroundColor: WOps.deep,
            foregroundColor: Colors.white,
            automaticallyImplyLeading: false,
            flexibleSpace: FlexibleSpaceBar(
              background: const DecoratedBox(
                decoration: BoxDecoration(gradient: LinearGradient(
                  colors: [WOps.mid, WOps.deep], begin: Alignment.topRight, end: Alignment.bottomLeft)),
              ),
              titlePadding: const EdgeInsetsDirectional.only(start: 16, bottom: 12),
              title: Row(mainAxisSize: MainAxisSize.min, children: [
                const Icon(Icons.recycling_rounded, size: 18),
                const SizedBox(width: 6),
                Text(tr('عمليات النفايات', 'Waste operations'),
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
              ]),
            ),
          ),
          SliverToBoxAdapter(child: _filterBar()),
          FutureBuilder<List<dynamic>>(
            future: _f,
            builder: (_, snap) {
              if (!snap.hasData) {
                return const SliverFillRemaining(child: Center(child: CircularProgressIndicator()));
              }
              final rows = snap.data!;
              if (rows.isEmpty) return SliverFillRemaining(hasScrollBody: false, child: _empty());
              return SliverPadding(
                padding: const EdgeInsets.fromLTRB(12, 4, 12, 20),
                sliver: SliverList.separated(
                  itemCount: rows.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 10),
                  itemBuilder: (_, i) => _card(rows[i] as Map),
                ),
              );
            },
          ),
        ]),
      ),
    );
  }

  Widget _empty() => Center(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(padding: const EdgeInsets.all(22),
              decoration: BoxDecoration(color: WOps.green.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(26)),
              child: const Icon(Icons.inbox_rounded, size: 44, color: WOps.green)),
          const SizedBox(height: 14),
          Text(_filter == 'unassigned' ? tr('لا طلبات بانتظار الإسناد', 'Nothing to assign') : tr('لا طلبات', 'No orders'),
              style: const TextStyle(fontWeight: FontWeight.w800, color: WOps.deep, fontSize: 15)),
          const SizedBox(height: 4),
          Text(tr('كل شيء تحت السيطرة 👌', 'All clear 👌'), style: const TextStyle(color: WOps.slate, fontSize: 12.5)),
        ]),
      );

  Widget _filterBar() => Container(
        color: Colors.white,
        padding: const EdgeInsets.fromLTRB(12, 10, 12, 10),
        child: Row(children: [
          for (final f in _filters) ...[
            Expanded(child: GestureDetector(
              onTap: () { setState(() => _filter = f[0]); _load(); },
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 160),
                padding: const EdgeInsets.symmetric(vertical: 9),
                decoration: BoxDecoration(
                  gradient: _filter == f[0] ? const LinearGradient(colors: [WOps.mid, WOps.deep]) : null,
                  color: _filter == f[0] ? null : WOps.bg,
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(color: _filter == f[0] ? Colors.transparent : Colors.black12),
                ),
                alignment: Alignment.center,
                child: Text(gLang == 'en' ? f[2] : f[1],
                    style: TextStyle(color: _filter == f[0] ? Colors.white : WOps.slate,
                        fontWeight: FontWeight.w800, fontSize: 12.5)),
              ),
            )),
            if (f != _filters.last) const SizedBox(width: 8),
          ],
        ]),
      );

  Widget _card(Map o) {
    final st = '${o['state']}';
    final col = _stateColor[st] ?? WOps.slate;
    final unassigned = o['driver_id'] == null;
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(16),
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: () => _openDetail(o),
        child: Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: unassigned ? WOps.amber.withValues(alpha: 0.55) : Colors.black12,
                width: unassigned ? 1.4 : 1),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Container(padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(color: col.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)),
                  child: Icon(Icons.recycling_rounded, color: col, size: 20)),
              const SizedBox(width: 10),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${o['serial']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: WOps.ink)),
                Text('${o['project'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: WOps.slate, fontSize: 11.5)),
              ])),
              Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                  decoration: BoxDecoration(color: col.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
                  child: Text('${o['state_label']}', style: TextStyle(color: col, fontWeight: FontWeight.w800, fontSize: 10.5))),
            ]),
            const Divider(height: 18),
            _kv(Icons.location_on_outlined, '${o['pickup'] ?? '—'}'),
            _kv(Icons.inventory_2_outlined,
                tr('${o['items_count']} صنف · ${o['qty_total']} قطعة · ${o['weight_total']} كجم',
                   '${o['items_count']} items · ${o['qty_total']} pcs · ${o['weight_total']} kg')),
            const SizedBox(height: 10),
            if (unassigned)
              SizedBox(width: double.infinity, height: 42, child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(backgroundColor: WOps.green, foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                onPressed: () => _assign(o),
                icon: const Icon(Icons.person_add_alt_1_rounded, size: 18),
                label: Text(tr('إسناد سائق', 'Assign driver'), style: const TextStyle(fontWeight: FontWeight.w800)),
              ))
            else
              Row(children: [
                const Icon(Icons.local_shipping_rounded, size: 16, color: WOps.green),
                const SizedBox(width: 6),
                Expanded(child: Text('${o['driver']}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: WOps.ink))),
                TextButton(onPressed: () => _assign(o), child: Text(tr('تغيير', 'Change'), style: const TextStyle(fontSize: 12))),
              ]),
          ]),
        ),
      ),
    );
  }

  Widget _kv(IconData ic, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(children: [
          Icon(ic, size: 15, color: WOps.slate),
          const SizedBox(width: 6),
          Expanded(child: Text(v, style: const TextStyle(fontSize: 12.5, color: WOps.ink))),
        ]),
      );

  void _openDetail(Map o) => showModalBottomSheet(
        context: context, isScrollControlled: true, backgroundColor: Colors.white,
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        builder: (_) => _OrderSheet(order: o, onAssign: () { Navigator.pop(context); _assign(o); }),
      );

  /// Native driver-assignment sheet (no web page).
  Future<void> _assign(Map o) async {
    final api = context.read<AuthProvider>().api;
    final picked = await showModalBottomSheet<int>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
      builder: (_) => _DriverPicker(orderId: o['id'] as int, currentId: o['driver_id'] as int?),
    );
    if (picked == null || !mounted) return;
    try {
      final res = await api.wasteOpsAssign(o['id'] as int, picked);
      if (!mounted) return;
      _load();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(tr('✅ تم الإسناد إلى ${res['driver']} وبدأت العملية',
                         '✅ Assigned to ${res['driver']} — operation started')),
        backgroundColor: WOps.green));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('$e'), backgroundColor: const Color(0xFFB91C1C)));
      }
    }
  }
}

/// Native driver picker — shows the project's registered drivers + their load.
class _DriverPicker extends StatefulWidget {
  const _DriverPicker({required this.orderId, this.currentId});
  final int orderId;
  final int? currentId;
  @override
  State<_DriverPicker> createState() => _DriverPickerState();
}

class _DriverPickerState extends State<_DriverPicker> {
  late Future<List<dynamic>> _f;

  @override
  void initState() {
    super.initState();
    _f = context.read<AuthProvider>().api.wasteOpsDrivers(widget.orderId);
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 14, 16, 20),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        Container(width: 42, height: 4, decoration: BoxDecoration(color: Colors.black12, borderRadius: BorderRadius.circular(4))),
        const SizedBox(height: 14),
        Row(children: [
          const Icon(Icons.local_shipping_rounded, color: WOps.green),
          const SizedBox(width: 8),
          Text(tr('اختر السائق', 'Choose a driver'),
              style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900, color: WOps.deep)),
        ]),
        const SizedBox(height: 12),
        FutureBuilder<List<dynamic>>(
          future: _f,
          builder: (_, snap) {
            if (!snap.hasData) return const Padding(padding: EdgeInsets.all(30), child: CircularProgressIndicator());
            final ds = snap.data!;
            if (ds.isEmpty) {
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 26),
                child: Column(children: [
                  const Icon(Icons.person_off_rounded, size: 40, color: WOps.slate),
                  const SizedBox(height: 10),
                  Text(tr('لا سائقين مسجّلين في هذا المشروع', 'No drivers registered on this project'),
                      textAlign: TextAlign.center, style: const TextStyle(fontWeight: FontWeight.w700, color: WOps.ink)),
                  const SizedBox(height: 4),
                  Text(tr('أضِفهم من تبويب «فريق نقل النفايات» في المشروع',
                          'Add them in the project\'s waste-team tab'),
                      textAlign: TextAlign.center, style: const TextStyle(color: WOps.slate, fontSize: 12)),
                ]),
              );
            }
            return ConstrainedBox(
              constraints: BoxConstraints(maxHeight: MediaQuery.of(context).size.height * 0.5),
              child: ListView.separated(
                shrinkWrap: true,
                itemCount: ds.length,
                separatorBuilder: (_, __) => const SizedBox(height: 8),
                itemBuilder: (_, i) {
                  final d = ds[i] as Map;
                  final sel = d['id'] == widget.currentId;
                  final busy = (d['busy'] as num?)?.toInt() ?? 0;
                  return Material(
                    color: sel ? WOps.green.withValues(alpha: 0.08) : WOps.bg,
                    borderRadius: BorderRadius.circular(14),
                    child: InkWell(
                      borderRadius: BorderRadius.circular(14),
                      onTap: () => Navigator.pop(context, d['id'] as int),
                      child: Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: sel ? WOps.green : Colors.transparent),
                        ),
                        child: Row(children: [
                          CircleAvatar(radius: 20, backgroundColor: WOps.green.withValues(alpha: 0.15),
                              child: Text('${d['name']}'.characters.first,
                                  style: const TextStyle(color: WOps.deep, fontWeight: FontWeight.w900))),
                          const SizedBox(width: 12),
                          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                            Text('${d['name']}', style: const TextStyle(fontWeight: FontWeight.w800, color: WOps.ink)),
                            Text(busy == 0 ? tr('متاح', 'Available') : tr('$busy رحلة جارية', '$busy active trips'),
                                style: TextStyle(fontSize: 11.5, color: busy == 0 ? WOps.green : WOps.amber, fontWeight: FontWeight.w700)),
                          ])),
                          if (sel) const Icon(Icons.check_circle_rounded, color: WOps.green),
                        ]),
                      ),
                    ),
                  );
                },
              ),
            );
          },
        ),
      ]),
    );
  }
}

/// Order detail sheet for the ops manager.
class _OrderSheet extends StatelessWidget {
  const _OrderSheet({required this.order, required this.onAssign});
  final Map order;
  final VoidCallback onAssign;

  @override
  Widget build(BuildContext context) {
    final o = order;
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.7, maxChildSize: 0.95, minChildSize: 0.4,
      builder: (_, sc) => ListView(controller: sc, padding: EdgeInsets.zero, children: [
        Container(
          padding: const EdgeInsets.fromLTRB(20, 14, 20, 20),
          decoration: const BoxDecoration(
            gradient: LinearGradient(colors: [WOps.mid, WOps.deep], begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Center(child: Container(width: 42, height: 4, decoration: BoxDecoration(color: Colors.white24, borderRadius: BorderRadius.circular(4)))),
            const SizedBox(height: 14),
            Row(children: [
              const Icon(Icons.recycling_rounded, color: Colors.white70, size: 20),
              const SizedBox(width: 8),
              Text('${o['serial']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
              const Spacer(),
              Container(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                  decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(20)),
                  child: Text('${o['state_label']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 12))),
            ]),
            const SizedBox(height: 4),
            Text('${o['project'] ?? ''}', style: const TextStyle(color: Colors.white70, fontSize: 12.5)),
          ]),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(18, 16, 18, 8),
          child: Column(children: [
            _row(Icons.business_rounded, tr('العميل', 'Client'), '${o['client'] ?? '—'}'),
            _row(Icons.location_on_outlined, tr('الالتقاط', 'Pickup'), '${o['pickup'] ?? '—'}'),
            _row(Icons.category_outlined, tr('النوع', 'Type'), '${o['type'] ?? '—'}'),
            _row(Icons.schedule_rounded, tr('وقت الطلب', 'Requested'), '${o['date'] ?? '—'}'),
            _row(Icons.inventory_2_outlined, tr('الأصناف', 'Items'),
                tr('${o['items_count']} صنف · ${o['qty_total']} قطعة · ${o['weight_total']} كجم',
                   '${o['items_count']} items · ${o['qty_total']} pcs · ${o['weight_total']} kg')),
            _row(Icons.local_shipping_rounded, tr('السائق', 'Driver'), '${o['driver'] ?? tr('لم يُسنَد بعد', 'Not assigned')}'),
            _row(Icons.factory_rounded, tr('المستلم', 'Receiver'), '${o['receiver'] ?? '—'}'),
            if (o['trip'] != null) _row(Icons.route_rounded, tr('الرحلة', 'Trip'), '${o['trip']}'),
          ]),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
          child: SizedBox(width: double.infinity, height: 48, child: ElevatedButton.icon(
            style: ElevatedButton.styleFrom(backgroundColor: WOps.green, foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
            onPressed: onAssign,
            icon: const Icon(Icons.person_add_alt_1_rounded, size: 18),
            label: Text(o['driver_id'] == null ? tr('إسناد سائق وبدء العملية', 'Assign driver & start')
                                               : tr('تغيير السائق', 'Change driver'),
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
          )),
        ),
      ]),
    );
  }

  Widget _row(IconData ic, String k, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Icon(ic, size: 18, color: WOps.slate),
          const SizedBox(width: 10),
          SizedBox(width: 78, child: Text(k, style: const TextStyle(color: WOps.slate, fontSize: 12.5))),
          Expanded(child: Text(v, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: WOps.ink))),
        ]),
      );
}

/// Account tab for waste staff.
class _MeTab extends StatelessWidget {
  const _MeTab({required this.role});
  final String role;

  static const _roleLabel = {
    'ops_manager': ['مسؤول العمليات', 'Operations manager'],
    'driver': ['سائق', 'Driver'],
    'receiver': ['مستلم الكميات', 'Center receiver'],
  };

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final name = auth.profile?.name ?? '';
    final lbl = _roleLabel[role] ?? [role, role];
    return Scaffold(
      backgroundColor: WOps.bg,
      body: ListView(padding: EdgeInsets.zero, children: [
        Container(
          padding: const EdgeInsets.fromLTRB(20, 50, 20, 24),
          decoration: const BoxDecoration(
            gradient: LinearGradient(colors: [WOps.mid, WOps.deep], begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.vertical(bottom: Radius.circular(28))),
          child: Column(children: [
            CircleAvatar(radius: 34, backgroundColor: Colors.white,
                child: Text(name.isNotEmpty ? name.trim().characters.first : '?',
                    style: const TextStyle(color: WOps.deep, fontSize: 28, fontWeight: FontWeight.w900))),
            const SizedBox(height: 10),
            Text(name, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
            const SizedBox(height: 6),
            Container(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(20)),
                child: Text(gLang == 'en' ? lbl[1] : lbl[0],
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 12))),
          ]),
        ),
        const SizedBox(height: 10),
        _tile(context, Icons.swap_horiz_rounded, tr('تبديل الوضع', 'Switch mode'),
            () => context.read<AuthProvider>().setAppMode('choose'), const Color(0xFF7C3AED)),
        _tile(context, Icons.language_rounded, tr('اللغة', 'Language'),
            () => showLanguagePicker(context), WOps.green),
        _tile(context, Icons.logout_rounded, tr('تسجيل الخروج', 'Sign out'),
            () => context.read<AuthProvider>().logout(), const Color(0xFFB91C1C)),
      ]),
    );
  }

  Widget _tile(BuildContext c, IconData i, String t, VoidCallback onTap, Color col) => Container(
        margin: const EdgeInsets.fromLTRB(14, 0, 14, 9),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
        child: ListTile(
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
          leading: Container(padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(color: col.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(10)),
              child: Icon(i, color: col, size: 20)),
          title: Text(t, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
          trailing: const Icon(Icons.chevron_left_rounded, color: WOps.slate),
          onTap: onTap,
        ),
      );
}
