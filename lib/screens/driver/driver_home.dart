import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/api_client.dart';
import '../../core/i18n.dart';

const kDrNavy = Color(0xFF0A1F44);
const kDrNavy2 = Color(0xFF14306B);
const kDrGold = Color(0xFFC9A227);
const kDrBg = Color(0xFFEDF1F7);
const kDrInk = Color(0xFF1F2A37);
const kDrMuted = Color(0xFF64748B);
const kDrCrit = Color(0xFFDC2626);
const kDrOk = Color(0xFF16A34A);
const kDrWarn = Color(0xFFE08A00);

Color payColor(String s) =>
    s == 'paid' ? kDrOk : (s == 'pending' ? kDrWarn : kDrCrit);

/// تطبيق السائق — رئيسية: سيارته مختصرة + ملخّص المخالفات. معزول: بياناته فقط.
class DriverHome extends StatefulWidget {
  const DriverHome({super.key});
  @override
  State<DriverHome> createState() => _DriverHomeState();
}

class _DriverHomeState extends State<DriverHome> {
  int _tab = 0;

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    final pages = [const _HomeTab(), const DriverViolationsScreen(embedded: true), const _NotifTab(), const _ProfileTab()];
    return Scaffold(
      backgroundColor: kDrBg,
      body: SafeArea(child: pages[_tab]),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _tab,
        onDestinationSelected: (i) => setState(() => _tab = i),
        backgroundColor: Colors.white,
        destinations: [
          NavigationDestination(icon: const Icon(Icons.home_rounded), label: tr('الرئيسية', 'Home')),
          NavigationDestination(icon: const Icon(Icons.traffic_rounded), label: tr('مخالفاتي', 'Violations')),
          NavigationDestination(icon: const Icon(Icons.notifications_rounded), label: tr('الإشعارات', 'Alerts')),
          NavigationDestination(icon: const Icon(Icons.person_rounded), label: tr('ملفّي', 'Profile')),
        ],
      ),
    );
  }
}

class _HomeTab extends StatefulWidget {
  const _HomeTab();
  @override
  State<_HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends State<_HomeTab> {
  ApiClient get _api => context.read<AuthProvider>().api;
  Map? _me;
  List _vehicles = const [];
  Map? _vioSummary;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final me = await _api.driverMe();
      final vs = await _api.driverVehicles();
      final vio = await _api.driverViolations();
      if (mounted) setState(() {
        _me = me;
        _vehicles = vs;
        _vioSummary = vio;
      });
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    if (_loading) return const Center(child: CircularProgressIndicator());
    final me = _me ?? {};
    final data = (_vioSummary?['data'] as List?) ?? [];
    final unpaid = data.where((v) => (v as Map)['pay_status'] != 'paid').toList();
    final paid = data.where((v) => (v as Map)['pay_status'] == 'paid').toList();
    final unpaidTotal = _vioSummary?['unpaid_total'] ?? 0;
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.fromLTRB(14, 14, 14, 24), children: [
        Row(children: [
          Expanded(child: Text('${tr('مرحبًا', 'Hi')}، ${me['name'] ?? ''} 👋',
              style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900, color: kDrNavy))),
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded, color: kDrNavy)),
        ]),
        const SizedBox(height: 6),
        if (unpaid.isNotEmpty) _alert(unpaid.length, unpaidTotal),
        ..._vehicles.map((v) => _vehicleCard(v as Map)),
        if (_vehicles.isEmpty)
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
            child: Center(child: Text(tr('لا توجد سيارة مُسنَدة', 'No assigned vehicle'), style: const TextStyle(color: kDrMuted))),
          ),
        const SizedBox(height: 12),
        Row(children: [
          Expanded(child: _stat(tr('غير مدفوعة', 'Unpaid'), '${unpaid.length}', kDrCrit)),
          const SizedBox(width: 10),
          Expanded(child: _stat(tr('مدفوعة أونلاين', 'Paid'), '${paid.length}', kDrOk)),
          const SizedBox(width: 10),
          Expanded(child: _stat(tr('الإجمالي المستحقّ', 'Due'), '$unpaidTotal', kDrNavy)),
        ]),
      ]),
    );
  }

  Widget _alert(int n, dynamic total) => Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(
            color: kDrCrit.withValues(alpha: 0.09),
            border: Border.all(color: kDrCrit.withValues(alpha: 0.35)),
            borderRadius: BorderRadius.circular(13)),
        child: Row(children: [
          const Text('⚠️', style: TextStyle(fontSize: 22)),
          const SizedBox(width: 10),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${tr('لديك', 'You have')} $n ${tr('مخالفة غير مدفوعة', 'unpaid violations')}',
                  style: const TextStyle(fontWeight: FontWeight.w900, color: kDrCrit)),
              Text('${tr('الإجمالي', 'Total')}: $total ${tr('د.ك', 'KWD')}', style: const TextStyle(color: kDrMuted, fontSize: 12)),
            ]),
          ),
        ]),
      );

  Widget _vehicleCard(Map v) => Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
            gradient: const LinearGradient(colors: [kDrNavy, kDrNavy2]), borderRadius: BorderRadius.circular(16)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Text('🚗', style: TextStyle(fontSize: 26)),
            const SizedBox(width: 8),
            Expanded(child: Text('${v['brand'] ?? ''} ${v['model'] ?? ''}',
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16))),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(5), border: Border.all(color: kDrOk, width: 2)),
              child: Text('${v['plate'] ?? ''}', style: const TextStyle(color: Colors.black, fontWeight: FontWeight.w900, fontSize: 12)),
            ),
          ]),
          const SizedBox(height: 10),
          Row(children: [
            _vb('${v['odometer'] ?? 0}', tr('العدّاد كم', 'Odometer')),
            _vb('${v['fuel'] ?? ''}', tr('الوقود', 'Fuel')),
            _vb('${v['year'] ?? ''}', tr('الموديل', 'Year')),
          ]),
        ]),
      );

  Widget _vb(String v, String l) => Expanded(
        child: Container(
          margin: const EdgeInsets.only(left: 6),
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)),
          child: Column(children: [
            Text(v, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14)),
            Text(l, style: const TextStyle(color: Color(0xFFC7D2E8), fontSize: 9.5)),
          ]),
        ),
      );

  Widget _stat(String l, String v, Color c) => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(13)),
        child: Column(children: [
          Text(v, style: TextStyle(color: c, fontWeight: FontWeight.w900, fontSize: 19)),
          Text(l, style: const TextStyle(color: kDrMuted, fontSize: 10.5, fontWeight: FontWeight.w700), textAlign: TextAlign.center),
        ]),
      );
}

// ================= المخالفات =================
class DriverViolationsScreen extends StatefulWidget {
  final bool embedded;
  const DriverViolationsScreen({super.key, this.embedded = false});
  @override
  State<DriverViolationsScreen> createState() => _DriverViolationsScreenState();
}

class _DriverViolationsScreenState extends State<DriverViolationsScreen> {
  ApiClient get _api => context.read<AuthProvider>().api;
  List _rows = const [];
  bool _loading = true;
  String _filter = 'all';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final r = await _api.driverViolations(status: _filter == 'all' ? null : _filter);
      if (mounted) setState(() => _rows = (r['data'] as List?) ?? []);
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    final body = Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 6),
        child: Row(children: [
          Text(tr('مخالفاتي المرورية', 'My violations'), style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900, color: kDrNavy)),
          const Spacer(),
          IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded, color: kDrNavy)),
        ]),
      ),
      SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 14),
        child: Row(children: [
          for (final e in {'all': tr('الكل', 'All'), 'unpaid': tr('غير مدفوعة', 'Unpaid'), 'paid': tr('مدفوعة', 'Paid')}.entries)
            Padding(
              padding: const EdgeInsets.only(left: 8),
              child: ChoiceChip(
                label: Text(e.value),
                selected: _filter == e.key,
                selectedColor: kDrNavy,
                labelStyle: TextStyle(color: _filter == e.key ? Colors.white : kDrInk, fontWeight: FontWeight.w700),
                onSelected: (_) {
                  setState(() => _filter = e.key);
                  _load();
                },
              ),
            ),
        ]),
      ),
      Expanded(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _rows.isEmpty
                ? Center(child: Text(tr('لا مخالفات', 'No violations'), style: const TextStyle(color: kDrMuted)))
                : RefreshIndicator(
                    onRefresh: _load,
                    child: ListView.separated(
                      padding: const EdgeInsets.fromLTRB(14, 8, 14, 20),
                      itemCount: _rows.length,
                      separatorBuilder: (_, __) => const SizedBox(height: 9),
                      itemBuilder: (_, i) => _card(_rows[i] as Map),
                    ),
                  ),
      ),
    ]);
    if (widget.embedded) return body;
    return Scaffold(backgroundColor: kDrBg, body: SafeArea(child: body));
  }

  Widget _card(Map v) {
    final st = (v['pay_status'] ?? 'unpaid').toString();
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(13),
      child: InkWell(
        borderRadius: BorderRadius.circular(13),
        onTap: () async {
          await Navigator.push(context, MaterialPageRoute(builder: (_) => DriverViolationDetail(id: (v['id'] as num).toInt())));
          _load();
        },
        child: Padding(
          padding: const EdgeInsets.all(13),
          child: Row(children: [
            Expanded(
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${v['ref']}', style: const TextStyle(fontSize: 10.5, color: kDrMuted, fontWeight: FontWeight.w700)),
                Text('${v['type']}', style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w900, color: kDrInk)),
                Text('📅 ${v['date']}', style: const TextStyle(fontSize: 11, color: kDrMuted)),
              ]),
            ),
            Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
              Text('${v['amount']} ${tr('د.ك', 'KWD')}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 2),
                decoration: BoxDecoration(color: payColor(st).withValues(alpha: 0.13), borderRadius: BorderRadius.circular(16)),
                child: Text('${v['pay_status_label']}', style: TextStyle(color: payColor(st), fontWeight: FontWeight.w800, fontSize: 10.5)),
              ),
            ]),
          ]),
        ),
      ),
    );
  }
}

// ================= تفاصيل + دفع =================
class DriverViolationDetail extends StatefulWidget {
  final int id;
  const DriverViolationDetail({super.key, required this.id});
  @override
  State<DriverViolationDetail> createState() => _DriverViolationDetailState();
}

class _DriverViolationDetailState extends State<DriverViolationDetail> {
  ApiClient get _api => context.read<AuthProvider>().api;
  Map? _d;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await _api.driverViolation(widget.id);
      if (mounted) setState(() => _d = d);
    } catch (_) {}
  }

  Future<void> _pay() async {
    setState(() => _busy = true);
    try {
      await _api.driverPay(widget.id);
      // محاكاة عودة البوّابة بنجاح مع مرجع (يُستبدل بتدفّق UPayments الفعلي)
      final ref = 'UPAY-${DateTime.now().millisecondsSinceEpoch.toString().substring(5)}';
      await _api.driverConfirmPayment(widget.id, ref, method: 'KNET');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تمّ الدفع بنجاح', 'Paid'))));
        await _load();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: kDrCrit));
    }
    if (mounted) setState(() => _busy = false);
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    final d = _d;
    final paid = d != null && d['pay_status'] == 'paid';
    return Scaffold(
      backgroundColor: kDrBg,
      appBar: AppBar(backgroundColor: kDrNavy, foregroundColor: Colors.white, title: Text(tr('تفاصيل المخالفة', 'Violation'))),
      bottomNavigationBar: (d != null && !paid)
          ? SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: FilledButton.icon(
                  style: FilledButton.styleFrom(backgroundColor: kDrGold, foregroundColor: kDrNavy, minimumSize: const Size.fromHeight(50)),
                  onPressed: _busy ? null : _pay,
                  icon: const Icon(Icons.credit_card_rounded),
                  label: Text(tr('💳 ادفع أونلاين الآن', 'Pay online now')),
                ),
              ),
            )
          : null,
      body: d == null
          ? const Center(child: CircularProgressIndicator())
          : ListView(padding: const EdgeInsets.all(16), children: [
              Center(
                child: Column(children: [
                  Text('${d['type']}', style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900, color: kDrInk)),
                  const SizedBox(height: 4),
                  Text('${d['amount']} ${tr('د.ك', 'KWD')}', style: TextStyle(fontSize: 30, fontWeight: FontWeight.w900, color: paid ? kDrOk : kDrCrit)),
                  const SizedBox(height: 4),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    decoration: BoxDecoration(color: payColor(d['pay_status']).withValues(alpha: 0.13), borderRadius: BorderRadius.circular(20)),
                    child: Text('${d['pay_status_label']}', style: TextStyle(color: payColor(d['pay_status']), fontWeight: FontWeight.w900)),
                  ),
                ]),
              ),
              const SizedBox(height: 18),
              _kv(tr('المرجع', 'Ref'), d['ref']),
              _kv(tr('التاريخ', 'Date'), d['date']),
              _kv(tr('المركبة', 'Vehicle'), d['vehicle']),
              _kv(tr('المسؤولية', 'Responsibility'), d['responsible']),
              if (paid) ...[
                const Divider(height: 28),
                Text(tr('بيانات الدفع', 'Payment'), style: const TextStyle(fontWeight: FontWeight.w900, color: kDrOk)),
                _kv(tr('مرجع العملية', 'Txn ref'), d['payment_ref']),
                _kv(tr('طريقة الدفع', 'Method'), d['payment_method']),
                _kv(tr('تاريخ الدفع', 'Paid at'), d['payment_date']),
              ],
            ]),
    );
  }

  Widget _kv(String k, dynamic v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Row(children: [
          Expanded(flex: 2, child: Text(k, style: const TextStyle(color: kDrMuted))),
          Expanded(flex: 3, child: Text('${v ?? '—'}', style: const TextStyle(fontWeight: FontWeight.w800, color: kDrInk))),
        ]),
      );
}

// ================= الإشعارات =================
class _NotifTab extends StatefulWidget {
  const _NotifTab();
  @override
  State<_NotifTab> createState() => _NotifTabState();
}

class _NotifTabState extends State<_NotifTab> {
  ApiClient get _api => context.read<AuthProvider>().api;
  List _rows = const [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final r = await _api.driverNotifications();
      if (mounted) setState(() => _rows = r);
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    return Column(children: [
      Padding(
        padding: const EdgeInsets.fromLTRB(14, 14, 14, 6),
        child: Row(children: [
          Text(tr('الإشعارات', 'Alerts'), style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900, color: kDrNavy)),
          const Spacer(),
          Text(tr('مخالفات فقط', 'Violations only'), style: const TextStyle(fontSize: 11, color: kDrMuted)),
        ]),
      ),
      Expanded(
        child: _loading
            ? const Center(child: CircularProgressIndicator())
            : _rows.isEmpty
                ? Center(child: Text(tr('لا إشعارات', 'No alerts'), style: const TextStyle(color: kDrMuted)))
                : ListView.builder(
                    padding: const EdgeInsets.fromLTRB(14, 6, 14, 20),
                    itemCount: _rows.length,
                    itemBuilder: (_, i) {
                      final n = _rows[i] as Map;
                      return Container(
                        margin: const EdgeInsets.only(bottom: 9),
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
                        child: Row(children: [
                          Container(
                            width: 38, height: 38,
                            decoration: BoxDecoration(color: kDrCrit.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)),
                            child: const Icon(Icons.traffic_rounded, color: kDrCrit, size: 19),
                          ),
                          const SizedBox(width: 11),
                          Expanded(
                            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                              Text('${n['title']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
                              Text('${n['body']}', style: const TextStyle(fontSize: 11.5, color: kDrMuted)),
                              Text('${n['date']}', style: const TextStyle(fontSize: 10, color: kDrMuted)),
                            ]),
                          ),
                        ]),
                      );
                    },
                  ),
      ),
    ]);
  }
}

// ================= الملف الشخصي =================
class _ProfileTab extends StatefulWidget {
  const _ProfileTab();
  @override
  State<_ProfileTab> createState() => _ProfileTabState();
}

class _ProfileTabState extends State<_ProfileTab> {
  ApiClient get _api => context.read<AuthProvider>().api;
  Map? _me;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final me = await _api.driverMe();
      if (mounted) setState(() => _me = me);
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    final me = _me;
    return me == null
        ? const Center(child: CircularProgressIndicator())
        : ListView(padding: const EdgeInsets.all(16), children: [
            Center(
              child: Column(children: [
                Container(
                  width: 76, height: 76,
                  decoration: const BoxDecoration(gradient: LinearGradient(colors: [kDrNavy, kDrNavy2]), shape: BoxShape.circle),
                  child: const Icon(Icons.person_rounded, color: kDrGold, size: 36),
                ),
                const SizedBox(height: 10),
                Text('${me['name']}', style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900)),
                Text('${me['job']} · ${me['nationality']}', style: const TextStyle(color: kDrMuted, fontSize: 12)),
              ]),
            ),
            const SizedBox(height: 18),
            _kv(tr('الرقم المدني', 'Civil ID'), me['civil_id']),
            _kv(tr('الرقم الوظيفي', 'Emp No'), me['emp_no']),
            _kv(tr('الهاتف', 'Phone'), me['phone']),
            _kv(tr('المشروع', 'Project'), me['project']),
          ]);
  }

  Widget _kv(String k, dynamic v) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
        child: Row(children: [
          Expanded(flex: 2, child: Text(k, style: const TextStyle(color: kDrMuted))),
          Expanded(flex: 3, child: Text('${v ?? '—'}', style: const TextStyle(fontWeight: FontWeight.w800, color: kDrInk))),
        ]),
      );
}
