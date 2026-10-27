import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'collections_home.dart';

/// ====== قائمة عملاء التحصيل وأرصدتهم ======
class CollectionsCustomers extends StatefulWidget {
  const CollectionsCustomers({super.key});
  @override
  State<CollectionsCustomers> createState() => _CollectionsCustomersState();
}

class _CollectionsCustomersState extends State<CollectionsCustomers> {
  final _rows = <dynamic>[];
  final _search = TextEditingController();
  bool _loading = true;
  String _q = '';
  num _totalResidual = 0;
  String _sym = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final d = await context.read<AuthProvider>().api.collectionsCustomers(q: _q);
      if (mounted) {
        setState(() {
          _rows..clear()..addAll((d['customers'] as List?) ?? []);
          _totalResidual = numOf(d['total_residual']);
          _sym = '${d['currency'] ?? ''}';
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: gLang == 'en' ? TextDirection.ltr : TextDirection.rtl,
      child: Scaffold(
        backgroundColor: Coll.bg,
        appBar: AppBar(backgroundColor: Coll.green, foregroundColor: Colors.white, elevation: 0,
          title: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Text(tr('العملاء', 'Customers'), style: const TextStyle(fontSize: 17)),
            if (!_loading) Text('${_rows.length} ${tr('عميل', 'customers')} · ${money(_totalResidual, _sym)}',
                style: TextStyle(fontSize: 12, color: Colors.white.withValues(alpha: 0.85), fontWeight: FontWeight.w400)),
          ])),
        body: Column(children: [
          Padding(padding: const EdgeInsets.fromLTRB(12, 10, 12, 6),
            child: TextField(controller: _search, textInputAction: TextInputAction.search,
              onSubmitted: (v) { _q = v.trim(); _load(); },
              decoration: InputDecoration(hintText: tr('بحث عن عميل', 'Search customer'),
                prefixIcon: const Icon(Icons.search_rounded),
                suffixIcon: _q.isEmpty ? null : IconButton(icon: const Icon(Icons.close_rounded),
                    onPressed: () { _search.clear(); _q = ''; _load(); }),
                filled: true, fillColor: Colors.white, isDense: true,
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)))),
          Expanded(child: _loading
              ? const Center(child: CircularProgressIndicator())
              : _rows.isEmpty
                  ? Center(child: Text(tr('لا يوجد عملاء', 'No customers'), style: const TextStyle(color: Coll.slate)))
                  : RefreshIndicator(onRefresh: _load, child: ListView.builder(
                      padding: const EdgeInsets.fromLTRB(12, 4, 12, 20),
                      itemCount: _rows.length,
                      itemBuilder: (_, i) => _row(_rows[i] as Map)))),
        ]),
      ),
    );
  }

  Widget _row(Map r) {
    final sc = '${r['state_code'] ?? ''}';
    final c = Coll.state(sc);
    final open = numOf(r['open_count']).toInt();
    return Card(margin: const EdgeInsets.only(bottom: 10), elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14),
          side: BorderSide(color: Colors.black.withValues(alpha: 0.06))),
      child: InkWell(borderRadius: BorderRadius.circular(14),
        onTap: () => Navigator.push(context, MaterialPageRoute(
            builder: (_) => CustomerProfile(partnerId: r['id'] as int))).then((_) => _load()),
        child: Padding(padding: const EdgeInsets.all(13),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              CircleAvatar(radius: 16, backgroundColor: c.withValues(alpha: 0.14),
                child: Text('${r['name'] ?? ''}'.characters.take(1).toString(),
                    style: TextStyle(color: c, fontWeight: FontWeight.w900))),
              const SizedBox(width: 10),
              Expanded(child: Text('${r['name'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w800, color: Coll.ink, fontSize: 14))),
              if (sc.isNotEmpty)
                Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                  decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
                  child: Text('${r['state'] ?? ''}', style: TextStyle(color: c, fontWeight: FontWeight.w700, fontSize: 11))),
            ]),
            const SizedBox(height: 10),
            Row(children: [
              _m(tr('المتبقّي', 'Outstanding'), money(numOf(r['residual']), _sym), Coll.green),
              const SizedBox(width: 14),
              _m(tr('فواتير', 'Invoices'), '${numOf(r['count']).toInt()}', Coll.slate),
              const Spacer(),
              if (numOf(r['overdue']) > 0)
                Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                  decoration: BoxDecoration(color: const Color(0xFFDC2626).withValues(alpha: 0.1), borderRadius: BorderRadius.circular(8)),
                  child: Text('${tr('متأخّر', 'Overdue')} ${money(numOf(r['overdue']), _sym)}',
                      style: const TextStyle(color: Color(0xFFDC2626), fontWeight: FontWeight.w700, fontSize: 10.5))),
            ]),
            if ('${r['last_activity'] ?? ''}'.isNotEmpty || open > 0) ...[
              const SizedBox(height: 8),
              Row(children: [
                if (open > 0) ...[
                  const Icon(Icons.pending_actions_rounded, size: 13, color: Color(0xFFD97706)),
                  const SizedBox(width: 3),
                  Text('$open ${tr('غير محصّلة', 'open')}', style: const TextStyle(color: Color(0xFFD97706), fontSize: 11, fontWeight: FontWeight.w700)),
                  const SizedBox(width: 12),
                ],
                if ('${r['last_activity'] ?? ''}'.isNotEmpty) ...[
                  const Icon(Icons.history_rounded, size: 13, color: Color(0xFF2563EB)),
                  const SizedBox(width: 3),
                  Expanded(child: Text('${r['last_activity']} · ${(r['last_activity_date'] ?? '').toString().split(' ').first}',
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Color(0xFF2563EB), fontSize: 11, fontWeight: FontWeight.w600))),
                ],
              ]),
            ],
          ]))));
  }

  Widget _m(String l, String v, Color c) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(l, style: const TextStyle(fontSize: 10, color: Coll.slate)),
        Text(v, style: TextStyle(fontWeight: FontWeight.w900, color: c, fontSize: 13)),
      ]);
}

/// ====== ملف العميل الغنيّ ======
class CustomerProfile extends StatefulWidget {
  const CustomerProfile({super.key, required this.partnerId});
  final int partnerId;
  @override
  State<CustomerProfile> createState() => _CustomerProfileState();
}

class _CustomerProfileState extends State<CustomerProfile> {
  Map _d = {};
  bool _loading = true;
  String get _sym => '${_d['currency'] ?? ''}';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final d = await context.read<AuthProvider>().api.collectionsCustomer(widget.partnerId);
      if (mounted) setState(() { _d = d; _loading = false; });
    } catch (e) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _setState(String code) async {
    try {
      await context.read<AuthProvider>().api.collectionsSetCustomerState(widget.partnerId, code);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('تم تحديث حالة العميل وكل فواتيره', 'Customer & invoices updated')), backgroundColor: Coll.green));
      _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final sc = '${_d['state_code'] ?? ''}';
    final c = Coll.state(sc);
    return Directionality(
      textDirection: gLang == 'en' ? TextDirection.ltr : TextDirection.rtl,
      child: Scaffold(
        backgroundColor: Coll.bg,
        appBar: AppBar(backgroundColor: Coll.green, foregroundColor: Colors.white, elevation: 0,
            title: Text(tr('ملف العميل', 'Customer file'), style: const TextStyle(fontSize: 17))),
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _d.isEmpty
                ? Center(child: Text(tr('تعذّر التحميل', 'Load failed'), style: const TextStyle(color: Coll.slate)))
                : RefreshIndicator(onRefresh: _load, child: ListView(
                    padding: const EdgeInsets.fromLTRB(12, 12, 12, 28), children: [
                      _header(c, sc),
                      const SizedBox(height: 12),
                      _kpiGrid(),
                      const SizedBox(height: 12),
                      _aging(),
                      const SizedBox(height: 12),
                      if (_d['can_set_state'] == true) _stateSetter(sc),
                      const SizedBox(height: 12),
                      _section(tr('الفواتير', 'Invoices'), (_d['invoices'] as List?) ?? [], _invTile),
                      _section(tr('سجلّ الأنشطة', 'Activity log'), (_d['activities'] as List?) ?? [], _actTile),
                      _section(tr('الدفعات', 'Payments'), (_d['payments'] as List?) ?? [], _payTile),
                    ])),
      ),
    );
  }

  Widget _header(Color c, String sc) => Container(padding: const EdgeInsets.all(16),
    decoration: BoxDecoration(gradient: const LinearGradient(colors: [Coll.green, Coll.greenD]),
        borderRadius: BorderRadius.circular(18)),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        CircleAvatar(radius: 22, backgroundColor: Colors.white.withValues(alpha: 0.2),
            child: Text('${_d['partner'] ?? ''}'.characters.take(1).toString(),
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18))),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${_d['partner'] ?? ''}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16)),
          if ('${_d['phone'] ?? ''}'.isNotEmpty || '${_d['city'] ?? ''}'.isNotEmpty)
            Text([_d['phone'], _d['city']].where((e) => '${e ?? ''}'.isNotEmpty).join(' · '),
                style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12)),
        ])),
        if (sc.isNotEmpty)
          Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
            child: Text('${_d['state'] ?? ''}', style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 11.5))),
      ]),
      const SizedBox(height: 14),
      Row(children: [
        _hv(tr('المتبقّي', 'Outstanding'), money(numOf(_d['residual']), _sym)),
        _hv(tr('المحصّل', 'Collected'), money(numOf(_d['collected']), _sym)),
        _hv(tr('نسبة التحصيل', 'Rate'), '${numOf(_d['collect_rate']).toStringAsFixed(1)}%'),
      ]),
    ]));

  Widget _hv(String l, String v) => Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        FittedBox(fit: BoxFit.scaleDown, alignment: AlignmentDirectional.centerStart,
          child: Text(v, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16))),
        Text(l, style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 11)),
      ]));

  Widget _kpiGrid() => GridView.count(crossAxisCount: 2, shrinkWrap: true,
    physics: const NeverScrollableScrollPhysics(), mainAxisSpacing: 10, crossAxisSpacing: 10, childAspectRatio: 1.6,
    children: [
      _kpi('🧾', tr('إجمالي الفواتير', 'Total'), money(numOf(_d['total']), _sym), Coll.green,
          '${numOf(_d['invoice_count']).toInt()} ${tr('فاتورة', 'inv')}'),
      _kpi('⏳', tr('غير محصّلة', 'Open'), '${numOf(_d['open_count']).toInt()}', const Color(0xFFD97706),
          '${numOf(_d['paid_count']).toInt()} ${tr('محصّلة', 'paid')}'),
      _kpi('⚠️', tr('المتأخّرات', 'Overdue'), money(numOf(_d['overdue_amount']), _sym), const Color(0xFFDC2626), ''),
      _kpi('💵', tr('المحصّل', 'Collected'), money(numOf(_d['collected']), _sym), Coll.gold, ''),
    ]);

  Widget _kpi(String ic, String l, String v, Color c, String sub) => Container(padding: const EdgeInsets.all(12),
    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.black.withValues(alpha: 0.05))),
    child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
      Container(width: 30, height: 30, alignment: Alignment.center,
        decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(9)),
        child: Text(ic, style: const TextStyle(fontSize: 15))),
      SizedBox(width: double.infinity, child: FittedBox(fit: BoxFit.scaleDown, alignment: AlignmentDirectional.centerStart,
        child: Text(v, maxLines: 1, style: TextStyle(fontWeight: FontWeight.w900, color: c, fontSize: 20)))),
      Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(l, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700, color: Coll.ink, fontSize: 12)),
        if (sub.isNotEmpty) Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Coll.slate, fontSize: 10)),
      ]),
    ]));

  Widget _aging() {
    final a = (_d['aging'] as Map?) ?? {};
    final items = [
      ['0-30', numOf(a['d0_30']), const Color(0xFF16A34A)],
      ['31-60', numOf(a['d31_60']), const Color(0xFFD97706)],
      ['61-90', numOf(a['d61_90']), const Color(0xFFEA580C)],
      ['90+', numOf(a['d90p']), const Color(0xFFDC2626)],
    ];
    final maxV = items.map((e) => e[1] as num).fold<num>(1, (p, e) => e > p ? e : p);
    return Container(padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.black.withValues(alpha: 0.05))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(tr('أعمار الديون', 'Aging'), style: const TextStyle(fontWeight: FontWeight.w800, color: Coll.ink, fontSize: 13.5)),
        const SizedBox(height: 10),
        ...items.map((e) => Padding(padding: const EdgeInsets.symmetric(vertical: 4), child: Row(children: [
          SizedBox(width: 48, child: Text('${e[0]} ${tr('ي', 'd')}', style: const TextStyle(fontSize: 11.5, color: Coll.slate))),
          Expanded(child: ClipRRect(borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(value: ((e[1] as num) / maxV).clamp(0.0, 1.0).toDouble(),
                minHeight: 10, backgroundColor: const Color(0xFFF1F3F4), color: e[2] as Color))),
          const SizedBox(width: 8),
          SizedBox(width: 92, child: Text(money(e[1] as num, _sym), textAlign: TextAlign.end,
              style: TextStyle(fontWeight: FontWeight.w800, fontSize: 11.5, color: e[2] as Color))),
        ]))),
      ]));
  }

  Widget _stateSetter(String sc) {
    final opts = [
      ['ok', tr('ملتزم', 'OK')], ['late', tr('متأخّر', 'Late')],
      ['no_response', tr('لا يتجاوب', 'No reply')], ['refuses', tr('يرفض', 'Refuses')], ['legal', tr('قانوني', 'Legal')],
    ];
    return Container(padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.black.withValues(alpha: 0.05))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(tr('حالة العميل (تُطبَّق على كل فواتيره)', 'Customer status (applies to all invoices)'),
            style: const TextStyle(fontWeight: FontWeight.w800, color: Coll.ink, fontSize: 13)),
        const SizedBox(height: 10),
        Wrap(spacing: 8, runSpacing: 8, children: opts.map((e) {
          final sel = sc == e[0];
          final c = Coll.state(e[0]);
          return ChoiceChip(label: Text(e[1]), selected: sel,
            selectedColor: c, backgroundColor: c.withValues(alpha: 0.10),
            labelStyle: TextStyle(color: sel ? Colors.white : c, fontWeight: FontWeight.w700, fontSize: 12),
            onSelected: (_) => _setState(e[0]));
        }).toList()),
      ]));
  }

  Widget _section(String title, List rows, Widget Function(Map) tile) {
    if (rows.isEmpty) return const SizedBox.shrink();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Padding(padding: const EdgeInsets.fromLTRB(4, 14, 4, 8),
        child: Text('$title (${rows.length})', style: const TextStyle(fontWeight: FontWeight.w800, color: Coll.ink, fontSize: 14))),
      ...rows.map((e) => tile(e as Map)),
    ]);
  }

  Widget _invTile(Map r) {
    final sc = '${r['state_code'] ?? ''}';
    final c = Coll.state(sc);
    return Card(margin: const EdgeInsets.only(bottom: 8), elevation: 0,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: BorderSide(color: Colors.black.withValues(alpha: 0.06))),
      child: ListTile(
        onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => CollectionsDetail(id: r['id'] as int))).then((_) => _load()),
        title: Text('${r['name'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13)),
        subtitle: Text('${r['invoice_date'] ?? ''} · ${r['payment_state'] == 'paid' ? tr('محصّلة', 'paid') : tr('غير محصّلة', 'open')}'
            '${r['delivered'] == true ? tr(' · مُسلّمة', ' · delivered') : ''}', style: const TextStyle(fontSize: 11.5)),
        trailing: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.end, children: [
          Text(money(numOf(r['amount_residual']), _sym), style: const TextStyle(fontWeight: FontWeight.w900, color: Coll.green, fontSize: 12.5)),
          if (sc.isNotEmpty) Text('${r['state'] ?? ''}', style: TextStyle(color: c, fontSize: 10.5, fontWeight: FontWeight.w700)),
        ])));
  }

  Widget _actTile(Map a) => Card(margin: const EdgeInsets.only(bottom: 8), elevation: 0,
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: BorderSide(color: Colors.black.withValues(alpha: 0.06))),
    child: ListTile(dense: true,
      leading: const Icon(Icons.event_note_rounded, color: Color(0xFF2563EB)),
      title: Text('${a['kind_label'] ?? ''}${a['outcome_label'] != null && '${a['outcome_label']}'.isNotEmpty ? ' · ${a['outcome_label']}' : ''}',
          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5)),
      subtitle: Text('${(a['date'] ?? '').toString()}${'${a['comment'] ?? ''}'.isNotEmpty ? '\n${a['comment']}' : ''}', style: const TextStyle(fontSize: 11)),
      isThreeLine: '${a['comment'] ?? ''}'.isNotEmpty));

  Widget _payTile(Map p) => Card(margin: const EdgeInsets.only(bottom: 8), elevation: 0,
    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12), side: BorderSide(color: Colors.black.withValues(alpha: 0.06))),
    child: ListTile(dense: true,
      leading: const Icon(Icons.payments_rounded, color: Coll.gold),
      title: Text('${money(numOf(p['amount']), _sym)} · ${p['method_label'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5)),
      subtitle: Text('${p['date'] ?? ''}${'${p['recipient'] ?? ''}'.isNotEmpty ? ' · ${p['recipient']}' : ''}', style: const TextStyle(fontSize: 11))));
}
