import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'collections_home.dart' show Coll, money;

/// شاشة أهداف التحصيل (التارجت) + العمولات داخل التطبيق.
/// يرى المحصّل هدفه النشط (نسبة الإنجاز + العمولة المتوقّعة) وسجلّ أهدافه.
class CollectionsTargets extends StatefulWidget {
  const CollectionsTargets({super.key});
  @override
  State<CollectionsTargets> createState() => _CollectionsTargetsState();
}

class _CollectionsTargetsState extends State<CollectionsTargets> {
  Map<String, dynamic>? _d;
  bool _loading = true;
  String? _err;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _err = null; });
    try {
      final d = await context.read<AuthProvider>().api.collectionsTargets();
      if (mounted) setState(() { _d = d; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _err = '$e'; _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Directionality(
      textDirection: gLang == 'en' ? TextDirection.ltr : TextDirection.rtl,
      child: Scaffold(
        backgroundColor: Coll.bg,
        body: _loading
            ? const Center(child: CircularProgressIndicator())
            : _d == null
                ? _errView()
                : RefreshIndicator(onRefresh: _load, child: _body()),
      ),
    );
  }

  Widget _errView() => Center(child: Padding(padding: const EdgeInsets.all(24),
    child: Column(mainAxisSize: MainAxisSize.min, children: [
      const Icon(Icons.error_outline_rounded, color: Coll.red, size: 40),
      const SizedBox(height: 10),
      Text(tr('تعذّر تحميل الأهداف', 'Could not load targets'),
          style: const TextStyle(fontWeight: FontWeight.w800, color: Coll.ink)),
      if ((_err ?? '').isNotEmpty) ...[
        const SizedBox(height: 8),
        Text(_err!, textAlign: TextAlign.center, style: const TextStyle(color: Coll.slate, fontSize: 12.5)),
      ],
      const SizedBox(height: 16),
      FilledButton.icon(onPressed: _load,
          style: FilledButton.styleFrom(backgroundColor: Coll.green),
          icon: const Icon(Icons.refresh_rounded, size: 18),
          label: Text(tr('إعادة المحاولة', 'Retry'))),
    ])));

  Widget _body() {
    final d = _d!;
    final active = (d['active'] as List?) ?? const [];
    final history = (d['history'] as List?) ?? const [];
    final sym = '${d['currency'] ?? ''}';
    final isMgr = d['is_manager'] == true;
    final due = numOf(d['commission_due_total']);
    return CustomScrollView(slivers: [
      SliverToBoxAdapter(child: _hero(due, sym)),
      SliverPadding(
        padding: const EdgeInsets.fromLTRB(14, 14, 14, 28),
        sliver: SliverList(delegate: SliverChildListDelegate([
          if (active.isEmpty && history.isEmpty)
            _empty()
          else ...[
            if (active.isNotEmpty) ...[
              _sectionTitle(tr('الهدف النشط', 'Active target')),
              const SizedBox(height: 10),
              ...active.map((t) => _activeCard(t as Map, isMgr)),
            ],
            if (history.isNotEmpty) ...[
              const SizedBox(height: 18),
              _sectionTitle(tr('سجلّ الأهداف', 'History')),
              const SizedBox(height: 10),
              ...history.map((t) => _historyCard(t as Map)),
            ],
          ],
        ])),
      ),
    ]);
  }

  Widget _hero(num due, String sym) => Container(
        padding: EdgeInsets.fromLTRB(18, MediaQuery.of(context).padding.top + 16, 18, 20),
        decoration: const BoxDecoration(
          gradient: LinearGradient(colors: [Coll.greenD, Coll.green],
              begin: Alignment.topLeft, end: Alignment.bottomRight),
          borderRadius: BorderRadius.vertical(bottom: Radius.circular(26)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            IconButton(onPressed: () => Navigator.maybePop(context),
                icon: const Icon(Icons.arrow_back_rounded, color: Colors.white)),
            const Text('🎯', style: TextStyle(fontSize: 22)),
            const SizedBox(width: 8),
            Expanded(child: Text(tr('أهداف التحصيل', 'Collection targets'),
                style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900))),
          ]),
          const SizedBox(height: 10),
          Text(tr('إجمالي العمولة المستحقّة (غير مصروفة)', 'Total commission due'),
              style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 13)),
          const SizedBox(height: 4),
          Text(money(due, sym),
              style: const TextStyle(color: Colors.white, fontSize: 28, fontWeight: FontWeight.w900)),
        ]),
      );

  Widget _empty() => Container(
      margin: const EdgeInsets.only(top: 40), alignment: Alignment.center,
      child: Column(children: [
        const Icon(Icons.flag_outlined, size: 54, color: Coll.slate),
        const SizedBox(height: 12),
        Text(tr('لا توجد أهداف محدّدة بعد', 'No targets set yet'),
            style: const TextStyle(color: Coll.slate, fontWeight: FontWeight.w700)),
      ]));

  Widget _sectionTitle(String t) => Text(t,
      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: Coll.ink));

  Color _achColor(num pct) {
    if (pct >= 100) return const Color(0xFF16A34A);
    if (pct >= 50) return const Color(0xFFD97706);
    return const Color(0xFFDC2626);
  }

  Widget _activeCard(Map t, bool isMgr) {
    final sym = '${t['currency'] ?? ''}';
    final pct = numOf(t['achievement_pct']).toDouble();
    final c = _achColor(pct);
    final paid = t['commission_paid'] == true;
    return Container(margin: const EdgeInsets.only(bottom: 14), padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 12, offset: const Offset(0, 5))]),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Expanded(child: Text('${t['name'] ?? ''}',
              style: const TextStyle(fontWeight: FontWeight.w900, color: Coll.ink, fontSize: 14.5))),
          Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
            decoration: BoxDecoration(color: Coll.green.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
            child: Text('${t['state_label'] ?? ''}',
                style: const TextStyle(color: Coll.green, fontWeight: FontWeight.w700, fontSize: 11))),
        ]),
        Text('${t['date_from'] ?? ''} → ${t['date_to'] ?? ''}',
            style: const TextStyle(color: Coll.slate, fontSize: 11.5)),
        if (isMgr) Padding(padding: const EdgeInsets.only(top: 2),
          child: Text('${tr('المحصّل', 'Collector')}: ${t['collector'] ?? ''}',
              style: const TextStyle(color: Coll.slate, fontSize: 11.5))),
        const SizedBox(height: 14),
        // حلقة الإنجاز + المبالغ
        Row(children: [
          _ring(pct, c),
          const SizedBox(width: 16),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            _amtLine(tr('المستهدف', 'Target'), money(numOf(t['target_amount']), sym), Coll.ink),
            const SizedBox(height: 6),
            _amtLine(tr('المُحصّل', 'Collected'), money(numOf(t['collected_amount']), sym), Coll.green),
            const SizedBox(height: 6),
            _amtLine(tr('المتبقّي', 'Remaining'), money(numOf(t['remaining_amount']), sym), const Color(0xFFDC2626)),
          ])),
        ]),
        const SizedBox(height: 14),
        const Divider(height: 1),
        const SizedBox(height: 12),
        // بطاقة العمولة
        _commissionBox(t, sym, paid),
      ]));
  }

  Widget _ring(double pct, Color c) {
    final v = (pct / 100.0).clamp(0.0, 1.0);
    return SizedBox(width: 92, height: 92, child: Stack(alignment: Alignment.center, children: [
      SizedBox(width: 92, height: 92, child: CircularProgressIndicator(
          value: v, strokeWidth: 9, backgroundColor: const Color(0xFFEEF2F1),
          valueColor: AlwaysStoppedAnimation(c))),
      Column(mainAxisSize: MainAxisSize.min, children: [
        Text('${pct.toStringAsFixed(0)}%',
            style: TextStyle(fontWeight: FontWeight.w900, fontSize: 19, color: c)),
        Text(tr('إنجاز', 'done'), style: const TextStyle(fontSize: 10, color: Coll.slate)),
      ]),
    ]));
  }

  Widget _amtLine(String l, String v, Color c) => Row(children: [
        Expanded(child: Text(l, style: const TextStyle(color: Coll.slate, fontSize: 12.5))),
        Text(v, style: TextStyle(fontWeight: FontWeight.w900, color: c, fontSize: 13.5)),
      ]);

  Widget _commissionBox(Map t, String sym, bool paid) {
    return Container(padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: [Coll.gold.withValues(alpha: 0.13), Colors.white]),
        borderRadius: BorderRadius.circular(14), border: Border.all(color: Coll.gold.withValues(alpha: 0.3))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          const Icon(Icons.savings_rounded, color: Coll.gold, size: 20),
          const SizedBox(width: 8),
          Expanded(child: Text(tr('العمولة المستحقّة', 'Commission due'),
              style: const TextStyle(fontWeight: FontWeight.w800, color: Coll.ink, fontSize: 13))),
          Text(money(numOf(t['commission_amount']), sym),
              style: const TextStyle(fontWeight: FontWeight.w900, color: Coll.gold, fontSize: 17)),
        ]),
        const SizedBox(height: 8),
        Wrap(spacing: 6, runSpacing: 6, children: [
          _chip(Icons.tune_rounded, '${t['commission_type_label'] ?? ''}'),
          ..._rule(t, sym),
          if (paid) _chip(Icons.check_circle_rounded, tr('مصروفة', 'Paid'), green: true)
          else _chip(Icons.hourglass_bottom_rounded, tr('غير مصروفة', 'Unpaid')),
        ]),
      ]));
  }

  // وصف قاعدة العمولة المختارة كشرائح صغيرة
  List<Widget> _rule(Map t, String sym) {
    final type = '${t['commission_type']}';
    final out = <Widget>[];
    if (type == 'pct') {
      out.add(_chip(Icons.percent_rounded, '${numOf(t['commission_pct'])}% ${tr('من المُحصّل', 'of collected')}'));
    } else if (type == 'per_invoice') {
      out.add(_chip(Icons.receipt_long_rounded,
          '${money(numOf(t['commission_per_invoice']), sym)} × ${numOf(t['invoices_collected']).toInt()} ${tr('فاتورة', 'inv')}'));
    } else if (type == 'lump') {
      out.add(_chip(Icons.card_giftcard_rounded,
          '${money(numOf(t['commission_lump']), sym)} ${tr('عند 100%', 'at 100%')}'));
    } else if (type == 'tiered') {
      final tiers = (t['tiers'] as List?) ?? const [];
      for (final tr0 in tiers) {
        final m = tr0 as Map;
        out.add(_chip(Icons.stairs_rounded,
            '${numOf(m['from']).toInt()}–${numOf(m['to']).toInt()}% → ${numOf(m['rate'])}%'));
      }
    }
    if (numOf(t['min_achieve_pct']) > 0) {
      out.add(_chip(Icons.flag_rounded, '${tr('حد أدنى', 'min')} ${numOf(t['min_achieve_pct'])}%'));
    }
    if (numOf(t['overdue_bonus_pct']) > 0) {
      out.add(_chip(Icons.trending_up_rounded, '+${numOf(t['overdue_bonus_pct'])}% ${tr('متعثّرات', 'overdue')}'));
    }
    if (numOf(t['commission_cap']) > 0) {
      out.add(_chip(Icons.vertical_align_top_rounded, '${tr('سقف', 'cap')} ${money(numOf(t['commission_cap']), sym)}'));
    }
    return out;
  }

  Widget _chip(IconData ic, String l, {bool green = false}) {
    final c = green ? const Color(0xFF16A34A) : Coll.slate;
    return Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(color: c.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(8)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(ic, size: 12.5, color: c), const SizedBox(width: 4),
        Text(l, style: TextStyle(color: c, fontWeight: FontWeight.w700, fontSize: 10.5)),
      ]));
  }

  Widget _historyCard(Map t) {
    final sym = '${t['currency'] ?? ''}';
    final pct = numOf(t['achievement_pct']).toDouble();
    final c = _achColor(pct);
    return Container(margin: const EdgeInsets.only(bottom: 8), padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(13),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
      child: Row(children: [
        SizedBox(width: 44, height: 44, child: Stack(alignment: Alignment.center, children: [
          SizedBox(width: 44, height: 44, child: CircularProgressIndicator(
              value: (pct / 100).clamp(0.0, 1.0), strokeWidth: 5,
              backgroundColor: const Color(0xFFEEF2F1), valueColor: AlwaysStoppedAnimation(c))),
          Text('${pct.toStringAsFixed(0)}', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: c)),
        ])),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${t['name'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w800, color: Coll.ink, fontSize: 13)),
          Text('${money(numOf(t['collected_amount']), sym)} / ${money(numOf(t['target_amount']), sym)}',
              style: const TextStyle(color: Coll.slate, fontSize: 11.5)),
        ])),
        Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Text(money(numOf(t['commission_amount']), sym),
              style: const TextStyle(fontWeight: FontWeight.w900, color: Coll.gold, fontSize: 13)),
          Text('${t['state_label'] ?? ''}', style: const TextStyle(color: Coll.slate, fontSize: 10.5)),
        ]),
      ]));
  }
}
