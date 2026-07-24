import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'management_home.dart' show Mgmt;
import 'management_list.dart' show openManagementRecord;

/// «الاعتمادات» — the unified approvals inbox: every record awaiting THIS
/// user's action, grouped by the workflow (system) it came from. Tapping a
/// record opens its detail sheet where the user takes the action.
class ManagementInboxScreen extends StatefulWidget {
  const ManagementInboxScreen({super.key});
  @override
  State<ManagementInboxScreen> createState() => _ManagementInboxScreenState();
}

class _ManagementInboxScreenState extends State<ManagementInboxScreen> {
  Map<String, dynamic>? _data;
  bool _loading = true;
  String? _err;
  String? _filter; // selected source key, null = all

  static const _tint = {
    'purchases': Color(0xFF2563EB), 'sales': Color(0xFF16A34A), 'tenders': Color(0xFF7C3AED),
    'proposals': Color(0xFF0891B2), 'leaves': Color(0xFF0EA5E9), 'expenses': Color(0xFFEA580C),
    'purchase_requests': Color(0xFF2563EB), 'approvals': Color(0xFFDB2777),
    'invoice_requests': Color(0xFF9333EA), 'experience': Color(0xFF059669),
    'payslips': Color(0xFF7C3AED), 'payroll': Color(0xFF7C3AED),
  };
  Color _c(String k) => _tint[k] ?? Mgmt.red;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() { _loading = true; _err = null; });
    try {
      final d = await context.read<AuthProvider>().api.managementInbox();
      if (mounted) setState(() { _data = d; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _err = '$e'; _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    final sources = ((_data?['sources'] as List?) ?? const []).cast<Map>();
    var items = ((_data?['items'] as List?) ?? const []).cast<Map>();
    if (_filter != null) items = items.where((i) => '${i['key']}' == _filter).toList();
    final total = (_data?['total'] ?? 0) as int;

    return Scaffold(
      backgroundColor: Mgmt.bg,
      appBar: AppBar(
        backgroundColor: Mgmt.deep, foregroundColor: Colors.white, elevation: 0,
        title: Text('✅ ${tr('الاعتمادات', 'Approvals inbox')}'),
        actions: [IconButton(icon: const Icon(Icons.refresh_rounded), onPressed: _load)],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _err != null
              ? Center(child: Padding(padding: const EdgeInsets.all(30),
                  child: Text(_err!, textAlign: TextAlign.center, style: const TextStyle(color: Mgmt.slate))))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: CustomScrollView(slivers: [
                    SliverToBoxAdapter(child: _header(total, sources)),
                    if (items.isEmpty)
                      SliverFillRemaining(hasScrollBody: false, child: _empty())
                    else
                      SliverPadding(
                        padding: const EdgeInsets.fromLTRB(12, 4, 12, 24),
                        sliver: SliverList(delegate: SliverChildBuilderDelegate(
                          (_, i) => _itemCard(items[i]),
                          childCount: items.length,
                        )),
                      ),
                  ]),
                ),
    );
  }

  Widget _header(int total, List<Map> sources) => Container(
        margin: const EdgeInsets.fromLTRB(12, 14, 12, 8),
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [Mgmt.red, Mgmt.deep],
              begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.circular(20),
          boxShadow: [BoxShadow(color: Mgmt.red.withValues(alpha: 0.25), blurRadius: 16, offset: const Offset(0, 6))],
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.assignment_turned_in_rounded, color: Colors.white, size: 30),
            const SizedBox(width: 12),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(tr('بانتظار اعتمادك', 'Awaiting your action'),
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12.5, fontWeight: FontWeight.w600)),
              Text('$total', style: const TextStyle(color: Colors.white, fontSize: 30, fontWeight: FontWeight.w900, height: 1.1)),
            ])),
            Text(tr('طلب', 'requests'), style: TextStyle(color: Colors.white.withValues(alpha: 0.7), fontSize: 12)),
          ]),
          if (sources.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(tr('المداولات', 'Workflows'),
                style: TextStyle(color: Colors.white.withValues(alpha: 0.7), fontSize: 11, fontWeight: FontWeight.w700)),
            const SizedBox(height: 8),
            SizedBox(height: 78, child: ListView(
              scrollDirection: Axis.horizontal,
              children: [
                _srcChip(null, '🗂️', tr('الكل', 'All'), total),
                for (final s in sources)
                  _srcChip('${s['key']}', '${s['icon']}',
                      gLang == 'en' ? '${s['en']}' : '${s['ar']}', (s['count'] ?? 0) as int),
              ],
            )),
          ],
        ]),
      );

  Widget _srcChip(String? key, String icon, String label, int count) {
    final selected = _filter == key;
    return GestureDetector(
      onTap: () => setState(() => _filter = key),
      child: Container(
        width: 76,
        margin: const EdgeInsets.only(left: 8),
        padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
        decoration: BoxDecoration(
          color: selected ? Colors.white : Colors.white.withValues(alpha: 0.14),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.white.withValues(alpha: selected ? 1 : 0.25)),
        ),
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          Stack(clipBehavior: Clip.none, children: [
            Text(icon, style: const TextStyle(fontSize: 22)),
            if (count > 0) Positioned(
              right: -10, top: -6,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                constraints: const BoxConstraints(minWidth: 16),
                decoration: BoxDecoration(color: const Color(0xFFDC2626), borderRadius: BorderRadius.circular(9),
                    border: Border.all(color: Colors.white, width: 1.2)),
                child: Text('$count', textAlign: TextAlign.center,
                    style: const TextStyle(color: Colors.white, fontSize: 9.5, fontWeight: FontWeight.w900)),
              ),
            ),
          ]),
          const SizedBox(height: 5),
          Text(label, maxLines: 1, overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800,
                  color: selected ? Mgmt.ink : Colors.white)),
        ]),
      ),
    );
  }

  Widget _itemCard(Map it) {
    final key = '${it['key']}';
    final c = _c(key);
    final amount = it['amount'];
    final date = it['date'];
    final subtitle = it['subtitle'];
    return Container(
      margin: const EdgeInsets.only(bottom: 9),
      decoration: BoxDecoration(
        color: Colors.white, borderRadius: BorderRadius.circular(14),
        boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.04), blurRadius: 8, offset: const Offset(0, 2))],
      ),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: () async {
            await openManagementRecord(context, key, it['id'] as int, title: '${it['title']}', accent: c);
            _load(); // refresh counts after acting
          },
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Row(children: [
              Container(
                width: 46, height: 46,
                decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(12)),
                alignment: Alignment.center,
                child: Text('${it['icon'] ?? '📄'}', style: const TextStyle(fontSize: 22)),
              ),
              const SizedBox(width: 12),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                    decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(6)),
                    child: Text(gLang == 'en' ? '${it['system_en']}' : '${it['system_ar']}',
                        style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w800, color: c)),
                  ),
                  const Spacer(),
                  if (date != null) Text('$date', style: const TextStyle(fontSize: 10.5, color: Mgmt.slate)),
                ]),
                const SizedBox(height: 5),
                Text('${it['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5, color: Mgmt.ink)),
                if (subtitle != null && '$subtitle'.isNotEmpty)
                  Padding(padding: const EdgeInsets.only(top: 2),
                      child: Text('$subtitle', maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontSize: 11.5, color: Mgmt.slate))),
                if (amount != null)
                  Padding(padding: const EdgeInsets.only(top: 3),
                      child: Text(_money(amount),
                          style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w900, color: c))),
              ])),
              const Icon(Icons.chevron_left_rounded, color: Mgmt.slate),
            ]),
          ),
        ),
      ),
    );
  }

  String _money(dynamic v) {
    final n = v is num ? v : double.tryParse('$v') ?? 0;
    return '${n.toStringAsFixed(n == n.roundToDouble() ? 0 : 2)} ${tr('د.ك', 'KWD')}';
  }

  Widget _empty() => Center(child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
        const Icon(Icons.check_circle_outline_rounded, size: 84, color: Color(0xFF86EFAC)),
        const SizedBox(height: 14),
        Text(tr('لا يوجد ما ينتظر اعتمادك', 'Nothing awaiting your action'),
            style: const TextStyle(fontWeight: FontWeight.w800, color: Mgmt.ink, fontSize: 15)),
        const SizedBox(height: 6),
        Text(tr('كل الطلبات محدثة 🎉', 'You\'re all caught up 🎉'),
            style: const TextStyle(color: Mgmt.slate, fontSize: 12.5)),
      ]));
}
