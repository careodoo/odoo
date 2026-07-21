import 'hosp_suppliers_screen.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/auth.dart';
import '../core/i18n.dart';

/// The pantry behind the menu.
///
/// A storekeeper does not think in grams — they think in cups and in days.
/// So every supply leads with how many servings are left and how long that
/// lasts at the current rate, with the weight as the supporting detail rather
/// than the headline.
class HospStockScreen extends StatefulWidget {
  const HospStockScreen({super.key});

  @override
  State<HospStockScreen> createState() => _HospStockScreenState();
}

class _HospStockScreenState extends State<HospStockScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs = TabController(length: 2, vsync: this);
  Map<String, dynamic>? _d;
  String? _error;
  bool _busy = false;
  String? _supCat;      // supplies category filter (null = all)
  bool _supLowOnly = false;

  static const _brown = Color(0xFF8A6D3B);
  static const _navy = Color(0xFF0E3A5F);

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _tabs.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.hospStock();
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) setState(() => _error = '$e');
    }
  }

  List<Map> get _supplies =>
      ((_d?['supplies'] as List?) ?? const []).cast<Map>();

  /// Distinct categories present in the supplies, as (code, label).
  List<(String, String)> get _supCategories {
    final seen = <String, String>{};
    for (final s in _supplies) {
      final c = '${s['category'] ?? ''}';
      if (c.isNotEmpty) seen[c] = '${s['category_label'] ?? c}';
    }
    final out = seen.entries.map((e) => (e.key, e.value)).toList();
    out.sort((a, b) => a.$2.compareTo(b.$2));
    return out;
  }

  List<Map> get _filteredSupplies => _supplies.where((s) {
        if (_supCat != null && '${s['category'] ?? ''}' != _supCat) return false;
        if (_supLowOnly && s['low'] != true) return false;
        return true;
      }).toList();

  Widget _supplyFilters() => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(children: [
            _supChip(null, tr('الكل', 'All'), _supCat == null && !_supLowOnly),
            _supChipLow(),
            for (final c in _supCategories) _supChip(c.$1, c.$2, _supCat == c.$1),
          ]),
        ),
      );

  Widget _supChip(String? code, String label, bool on) => Padding(
        padding: const EdgeInsets.only(left: 6),
        child: ChoiceChip(
          label: Text(label, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
          selected: on,
          selectedColor: _brown.withValues(alpha: 0.16),
          onSelected: (_) => setState(() { _supCat = code; if (code != null) _supLowOnly = false; }),
        ),
      );

  Widget _supChipLow() => Padding(
        padding: const EdgeInsets.only(left: 6),
        child: FilterChip(
          label: Text(tr('تحت الحد', 'Low'), style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
          selected: _supLowOnly,
          selectedColor: const Color(0xFFE11D48).withValues(alpha: 0.14),
          onSelected: (v) => setState(() { _supLowOnly = v; if (v) _supCat = null; }),
        ),
      );
  List<Map> get _purchases =>
      ((_d?['purchases'] as List?) ?? const []).cast<Map>();

  @override
  Widget build(BuildContext context) {
    final t = (_d?['totals'] as Map?) ?? const {};
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      appBar: AppBar(
        backgroundColor: _brown,
        foregroundColor: Colors.white,
        title: Text(tr('مخزون الضيافة', 'Hospitality pantry'),
            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
        actions: [
          IconButton(
            icon: const Icon(Icons.storefront_rounded),
            tooltip: tr('الموردون والمواد', 'Suppliers & materials'),
            onPressed: () async {
              await Navigator.push(context, MaterialPageRoute(builder: (_) => const HospSuppliersScreen()));
              if (mounted) _load();
            },
          ),
          IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
        ],
        bottom: TabBar(
          controller: _tabs,
          indicatorColor: Colors.white,
          labelColor: Colors.white,
          unselectedLabelColor: Colors.white70,
          labelStyle: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13),
          tabs: [
            Tab(text: tr('المستهلكات', 'Supplies')),
            Tab(text: tr('المشتريات', 'Purchases')),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: _brown,
        onPressed: _busy ? null : _orderSheet,
        icon: const Icon(Icons.add_shopping_cart_rounded),
        label: Text(tr('طلب شراء', 'Order supplies'),
            style: const TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: _d == null
          ? Center(
              child: _error != null
                  ? Padding(
                      padding: const EdgeInsets.all(24),
                      child: Text(_error!, textAlign: TextAlign.center))
                  : const CircularProgressIndicator(color: _brown))
          : TabBarView(controller: _tabs, children: [
              RefreshIndicator(
                color: _brown,
                onRefresh: _load,
                child: ListView(
                  padding: const EdgeInsets.fromLTRB(12, 12, 12, 90),
                  children: [
                    _summary(t),
                    _supplyFilters(),
                    for (final s in _filteredSupplies) _supplyCard(s),
                    if (_filteredSupplies.isEmpty)
                      Padding(padding: const EdgeInsets.all(28),
                          child: Center(child: Text(tr('لا مستهلكات بهذا الفلتر', 'Nothing matches this filter'),
                              style: const TextStyle(color: Colors.black45)))),
                  ],
                ),
              ),
              RefreshIndicator(
                color: _brown,
                onRefresh: _load,
                child: _purchases.isEmpty
                    ? ListView(children: [
                        const SizedBox(height: 110),
                        Center(
                            child: Text(
                                tr('لا مشتريات بعد', 'No purchases yet'),
                                style: TextStyle(color: Colors.grey.shade600))),
                      ])
                    : ListView(
                        padding: const EdgeInsets.fromLTRB(12, 12, 12, 90),
                        children: [for (final p in _purchases) _purchaseCard(p)],
                      ),
              ),
            ]),
    );
  }

  Widget _summary(Map t) => Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
              colors: [_brown, Color(0xFF5C4526)],
              begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.circular(16),
        ),
        child: Row(children: [
          _stat('${numOf(t['value']).toStringAsFixed(2)}',
              tr('قيمة المخزون', 'Stock value')),
          _stat('${intOf(t['low'])}', tr('تحت الحد', 'Below minimum')),
          _stat('${intOf(t['urgent'])}', tr('تنفد خلال أسبوع', 'Out within a week')),
        ]),
      );

  Widget _stat(String v, String l) => Expanded(
        child: Column(children: [
          Text(v,
              style: const TextStyle(
                  color: Colors.white, fontSize: 19, fontWeight: FontWeight.w900)),
          const SizedBox(height: 2),
          Text(l,
              textAlign: TextAlign.center,
              style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.88), fontSize: 10.5)),
        ]),
      );

  Widget _supplyCard(Map s) {
    final days = numOf(s['days_cover']);
    final low = s['low'] == true;
    // Under a week is where a storekeeper should already be ordering.
    final urgent = low || (days > 0 && days < 7);
    final c = urgent ? const Color(0xFFE11D48) : const Color(0xFF16A34A);
    return InkWell(
      onTap: () => _supplySheet(s),
      borderRadius: BorderRadius.circular(14),
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: urgent ? c.withValues(alpha: 0.4) : Colors.grey.shade200),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(
              child: Text('${s['name']}',
                  style: const TextStyle(
                      fontWeight: FontWeight.w900, fontSize: 14.5, color: _navy)),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                  color: c.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(20)),
              // Servings first: this is the number the decision hangs on.
              child: Text('${intOf(s['servings_left'])} ${tr('حصة', 'servings')}',
                  style: TextStyle(
                      fontSize: 11.5, fontWeight: FontWeight.w900, color: c)),
            ),
          ]),
          const SizedBox(height: 6),
          Text(
              '${numOf(s['on_hand']).toStringAsFixed(0)} ${s['uom_label']} '
              '· ${numOf(s['packs']).toStringAsFixed(1)} ${s['pack_name']}'
              '${'${s['per_serving']}'.isNotEmpty ? ' · ${s['per_serving']}' : ''}',
              style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600)),
          if (days > 0) ...[
            const SizedBox(height: 8),
            Row(children: [
              Icon(urgent ? Icons.warning_amber_rounded : Icons.schedule_rounded,
                  size: 14, color: c),
              const SizedBox(width: 5),
              Text(
                  '${tr('تكفي', 'Lasts')} ${days.toStringAsFixed(days < 10 ? 1 : 0)} '
                  '${tr('يوم', 'days')}',
                  style: TextStyle(
                      fontSize: 11.5, fontWeight: FontWeight.w800, color: c)),
            ]),
          ],
        ]),
      ),
    );
  }

  /// What this supply is actually used by — the formula, in plain terms.
  void _supplySheet(Map s) {
    final used = ((s['used_in'] as List?) ?? const []).cast<Map>();
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (c) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(18, 14, 18, 20),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Container(
                width: 40, height: 4, margin: const EdgeInsets.only(bottom: 14),
                decoration: BoxDecoration(
                    color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(3))),
            Align(
              alignment: AlignmentDirectional.centerStart,
              child: Text('${s['name']}',
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17)),
            ),
            const SizedBox(height: 4),
            Align(
              alignment: AlignmentDirectional.centerStart,
              child: Text(
                  '${s['category_label']} · ${tr('العبوة', 'Pack')} '
                  '${numOf(s['pack_size']).toStringAsFixed(0)} ${s['uom_label']}',
                  style: TextStyle(fontSize: 12, color: Colors.grey.shade600)),
            ),
            const SizedBox(height: 14),
            if (used.isEmpty)
              Text(tr('لا يدخل في أي صنف بعد', 'Not used by any item yet'),
                  style: TextStyle(color: Colors.grey.shade600))
            else
              ...used.map((u) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Row(children: [
                      Expanded(
                        child: Text(
                            '${u['item']}'
                            '${u['option'] != null ? ' · ${u['option']}' : ''}',
                            style: const TextStyle(
                                fontWeight: FontWeight.w700, fontSize: 13)),
                      ),
                      Text(
                          '${numOf(u['qty'])} ${s['uom_label']} '
                          '→ ${intOf(u['per_pack'])} ${tr('حصة/عبوة', 'per pack')}',
                          style: TextStyle(
                              fontSize: 11.5,
                              fontWeight: FontWeight.w800,
                              color: Colors.grey.shade700)),
                    ]),
                  )),
          ]),
        ),
      ),
    );
  }

  Widget _purchaseCard(Map p) {
    const stateColors = {
      'draft': Color(0xFF64748B), 'submitted': Color(0xFF3B82F6),
      'approved': Color(0xFFF59E0B), 'received': Color(0xFF16A34A),
      'cancelled': Color(0xFFE11D48),
    };
    final st = '${p['state']}';
    final c = stateColors[st] ?? const Color(0xFF64748B);
    final labels = {
      'draft': tr('مسودة', 'Draft'), 'submitted': tr('مُرسَل', 'Submitted'),
      'approved': tr('معتمد', 'Approved'), 'received': tr('تم الاستلام', 'Received'),
      'cancelled': tr('ملغى', 'Cancelled'),
    };
    final next = {'draft': 'submit', 'submitted': 'approve', 'approved': 'receive'}[st];
    final nextLabel = {
      'draft': tr('إرسال', 'Submit'), 'submitted': tr('اعتماد', 'Approve'),
      'approved': tr('استلام', 'Receive'),
    }[st];
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.grey.shade200),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(
            child: Text('${p['name']}',
                style: const TextStyle(
                    fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
          ),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
            decoration: BoxDecoration(
                color: c.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(20)),
            child: Text(labels[st] ?? st,
                style: TextStyle(
                    fontSize: 11, fontWeight: FontWeight.w800, color: c)),
          ),
        ]),
        const SizedBox(height: 5),
        Text(
            '${p['supplier']} · ${p['date']} · ${intOf(p['lines'])} '
            '${tr('صنف', 'items')} · ${numOf(p['total']).toStringAsFixed(3)}',
            style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600)),
        if (next != null) ...[
          const SizedBox(height: 10),
          SizedBox(
            width: double.infinity,
            child: FilledButton(
              style: FilledButton.styleFrom(
                  backgroundColor: c,
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(11))),
              onPressed: _busy ? null : () => _act(intOf(p['id']), next),
              child: Text(nextLabel ?? '',
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13)),
            ),
          ),
        ],
      ]),
    );
  }

  Future<void> _act(int id, String act) async {
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.hospPurchaseAct(id, act);
      // Receiving is what moves the balance, so the whole page is reloaded.
      await _load();
      if (mounted) _snack(tr('تم', 'Done'), const Color(0xFF16A34A));
    } catch (e) {
      if (mounted) _snack('$e', const Color(0xFFE11D48));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Ordering is by pack, because that is how supplies are bought.
  Future<void> _orderSheet() async {
    final picked = <int, double>{};
    var source = 'care';
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (c) => StatefulBuilder(
        builder: (c, setSt) => DraggableScrollableSheet(
          expand: false,
          initialChildSize: 0.85,
          builder: (_, sc) => Container(
            decoration: const BoxDecoration(
                color: Color(0xFFF6F7F9),
                borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
            clipBehavior: Clip.antiAlias,
            child: Column(children: [
              Container(
                width: double.infinity,
                color: _brown,
                padding: const EdgeInsets.fromLTRB(18, 14, 18, 14),
                child: Text(tr('طلب شراء مستهلكات', 'Order supplies'),
                    style: const TextStyle(
                        color: Colors.white,
                        fontSize: 16.5,
                        fontWeight: FontWeight.w900)),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(14, 12, 14, 6),
                child: SegmentedButton<String>(
                  segments: [
                    ButtonSegment(
                        value: 'care', label: Text(tr('من CARE', 'From CARE'))),
                    ButtonSegment(
                        value: 'external',
                        label: Text(tr('مورّد خارجي', 'External'))),
                  ],
                  selected: {source},
                  showSelectedIcon: false,
                  onSelectionChanged: (v) => setSt(() => source = v.first),
                ),
              ),
              Expanded(
                child: ListView(
                  controller: sc,
                  padding: const EdgeInsets.fromLTRB(14, 6, 14, 14),
                  children: [
                    for (final s in _supplies)
                      Card(
                        elevation: 0,
                        margin: const EdgeInsets.only(bottom: 8),
                        shape: RoundedRectangleBorder(
                            side: BorderSide(color: Colors.grey.shade300),
                            borderRadius: BorderRadius.circular(12)),
                        child: ListTile(
                          dense: true,
                          title: Text('${s['name']}',
                              style: const TextStyle(
                                  fontWeight: FontWeight.w800, fontSize: 13.5)),
                          subtitle: Text(
                              '${s['pack_name']} · ${numOf(s['pack_size']).toStringAsFixed(0)} ${s['uom_label']}',
                              style: const TextStyle(fontSize: 11.5)),
                          trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                            IconButton(
                              icon: const Icon(Icons.remove_circle_outline, size: 20),
                              onPressed: () => setSt(() {
                                final q = (picked[intOf(s['id'])] ?? 0) - 1;
                                if (q <= 0) {
                                  picked.remove(intOf(s['id']));
                                } else {
                                  picked[intOf(s['id'])] = q;
                                }
                              }),
                            ),
                            Text('${(picked[intOf(s['id'])] ?? 0).toStringAsFixed(0)}',
                                style: const TextStyle(
                                    fontWeight: FontWeight.w900, fontSize: 14)),
                            IconButton(
                              icon: const Icon(Icons.add_circle, size: 20, color: _brown),
                              onPressed: () => setSt(() => picked[intOf(s['id'])] =
                                  (picked[intOf(s['id'])] ?? 0) + 1),
                            ),
                          ]),
                        ),
                      ),
                  ],
                ),
              ),
              SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(14, 6, 14, 12),
                  child: SizedBox(
                    height: 50,
                    width: double.infinity,
                    child: FilledButton(
                      style: FilledButton.styleFrom(
                          backgroundColor: _brown,
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(14))),
                      onPressed: picked.isEmpty ? null : () => Navigator.pop(c, true),
                      child: Text(
                          '${tr('إنشاء الطلب', 'Create order')}'
                          '${picked.isEmpty ? '' : ' (${picked.length})'}',
                          style: const TextStyle(
                              fontWeight: FontWeight.w900, fontSize: 15)),
                    ),
                  ),
                ),
              ),
            ]),
          ),
        ),
      ),
    );
    if (ok != true || picked.isEmpty || !mounted) return;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.hospPurchaseCreate({
        'source': source,
        'lines': [
          for (final e in picked.entries)
            {'supply_id': e.key, 'quantity': e.value, 'by_pack': true},
        ],
      });
      await _load();
      if (mounted) {
        _tabs.animateTo(1);
        _snack(tr('أُنشئ طلب الشراء', 'Purchase order created'),
            const Color(0xFF16A34A));
      }
    } catch (e) {
      if (mounted) _snack('$e', const Color(0xFFE11D48));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _snack(String m, Color c) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: c, behavior: SnackBarBehavior.floating));
}
