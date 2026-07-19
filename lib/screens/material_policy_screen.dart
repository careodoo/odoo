import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';

const _navy = Color(0xFF0E3A5F);
const _accent = Color(0xFF0E7490);

/// سياسة صرف المواد — the client's (or admin's) control over what the crew may
/// draw from each store: which items are self-issuable, for which services, and
/// the per-issue cap. Stores can also be closed to direct issue entirely.
class MaterialPolicyScreen extends StatefulWidget {
  const MaterialPolicyScreen({super.key});
  @override
  State<MaterialPolicyScreen> createState() => _MaterialPolicyScreenState();
}

class _MaterialPolicyScreenState extends State<MaterialPolicyScreen> {
  Map<String, dynamic>? _d;
  int? _storeId;
  String _q = '';
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.invPolicy(storeId: _storeId);
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack('$e');
    }
  }

  void _snack(String m, {Color? c}) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: c ?? _accent, behavior: SnackBarBehavior.floating));

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final canManage = d?['can_manage'] == true;
    final stores = ((d?['stores'] as List?) ?? const []).cast<Map>();
    final services = ((d?['services'] as List?) ?? const []).cast<Map>();
    var items = ((d?['items'] as List?) ?? const []).cast<Map>();
    if (_q.isNotEmpty) {
      final q = _q.toLowerCase();
      items = items.where((i) => '${i['product']} ${i['store']}'.toLowerCase().contains(q)).toList();
    }
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      appBar: AppBar(
        backgroundColor: _accent, foregroundColor: Colors.white,
        title: Text(tr('سياسة صرف المواد', 'Material policy'), style: const TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: d == null
          ? const Center(child: CircularProgressIndicator(color: _accent))
          : RefreshIndicator(
              color: _accent,
              onRefresh: _load,
              child: Column(children: [
                _header(items, canManage),
                _storeBar(stores),
                _search(),
                Expanded(child: items.isEmpty
                    ? _empty()
                    : ListView.builder(
                        padding: const EdgeInsets.fromLTRB(12, 4, 12, 20),
                        itemCount: items.length,
                        itemBuilder: (_, i) => _itemCard(items[i], services, canManage),
                      )),
              ]),
            ),
    );
  }

  Widget _header(List<Map> items, bool canManage) {
    final allowed = items.where((i) => i['allow_worker_issue'] == true).length;
    final blocked = items.length - allowed;
    return CustomPaint(
      painter: const BrandPattern(opacity: 0.07),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
        decoration: const BoxDecoration(
          gradient: LinearGradient(colors: [_accent, _navy], begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.vertical(bottom: Radius.circular(20)),
        ),
        child: Column(children: [
          Row(children: [
            _hs('${items.length}', tr('صنف', 'Items')),
            _hd(),
            _hs('$allowed', tr('مسموح للعمّال', 'Self-issue')),
            _hd(),
            _hs('$blocked', tr('محظور', 'Blocked')),
          ]),
          if (!canManage) ...[
            const SizedBox(height: 10),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(12)),
              child: Text(tr('عرض فقط — الضبط للعميل أو المدير',
                             'View only — configuring is for the client or an admin'),
                  textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.w700)),
            ),
          ],
        ]),
      ),
    );
  }

  Widget _hs(String v, String l) => Expanded(child: Column(children: [
        Text(v, style: const TextStyle(color: Colors.white, fontSize: 19, fontWeight: FontWeight.w900)),
        Text(l, textAlign: TextAlign.center, style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 10, fontWeight: FontWeight.w600)),
      ]));

  Widget _hd() => Container(width: 1, height: 30, color: Colors.white.withValues(alpha: 0.2));

  /// Stores, showing the main → sub structure and each store's issue switch.
  Widget _storeBar(List<Map> stores) => SizedBox(
        height: 78,
        child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.fromLTRB(10, 10, 10, 4), children: [
          _storeChip(null, tr('كل المخازن', 'All stores'), null, null),
          for (final s in stores)
            _storeChip(s['id'] as int, '${s['name']}',
                s['is_sub'] == true ? '${s['service'] ?? ''} · ${tr('فرعي', 'sub')}' : tr('رئيسي', 'main'),
                s),
        ]),
      );

  Widget _storeChip(int? id, String label, String? sub, Map? store) {
    final on = _storeId == id;
    final closed = store != null && store['worker_issue_allowed'] == false;
    return GestureDetector(
      onTap: () { setState(() => _storeId = id); _load(); },
      onLongPress: store == null ? null : () => _toggleStore(store),
      child: Container(
        width: 150,
        margin: const EdgeInsets.only(left: 8),
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(
          color: on ? _accent : Colors.white,
          borderRadius: BorderRadius.circular(13),
          border: Border.all(color: on ? _accent : Colors.grey.shade300),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
          Row(children: [
            Icon(store != null && store['is_sub'] == true ? Icons.subdirectory_arrow_left_rounded : Icons.warehouse_rounded,
                size: 14, color: on ? Colors.white : _navy),
            const SizedBox(width: 5),
            Expanded(child: Text(label, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: TextStyle(fontWeight: FontWeight.w900, fontSize: 11.5, color: on ? Colors.white : _navy))),
          ]),
          if (sub != null) ...[
            const SizedBox(height: 3),
            Text(sub, maxLines: 1, overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 9.5, color: on ? Colors.white70 : Colors.grey.shade600, fontWeight: FontWeight.w700)),
          ],
          if (closed) ...[
            const SizedBox(height: 3),
            Text(tr('مغلق للصرف', 'issue closed'),
                style: TextStyle(fontSize: 9, color: on ? Colors.white : const Color(0xFFE11D48), fontWeight: FontWeight.w900)),
          ],
        ]),
      ),
    );
  }

  Future<void> _toggleStore(Map s) async {
    if (_d?['can_manage'] != true) return;
    final now = s['worker_issue_allowed'] == true;
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      title: Text('${s['name']}'),
      content: Text(now
          ? tr('إغلاق الصرف المباشر من هذا المخزن؟', 'Close direct issue from this store?')
          : tr('السماح بالصرف المباشر من هذا المخزن؟', 'Allow direct issue from this store?')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('تراجع', 'Cancel'))),
        FilledButton(style: FilledButton.styleFrom(backgroundColor: _accent),
            onPressed: () => Navigator.pop(c, true), child: Text(tr('تأكيد', 'Confirm'))),
      ],
    ));
    if (ok != true) return;
    try {
      await context.read<AuthProvider>().api.invPolicySetStore(s['id'] as int, !now);
      await _load();
      if (mounted) _snack(tr('تم تحديث المخزن', 'Store updated'), c: const Color(0xFF16A34A));
    } catch (e) {
      if (mounted) _snack('$e');
    }
  }

  Widget _search() => Padding(
        padding: const EdgeInsets.fromLTRB(12, 6, 12, 4),
        child: TextField(
          onChanged: (v) => setState(() => _q = v),
          decoration: InputDecoration(
            hintText: tr('بحث عن صنف…', 'Search item…'),
            prefixIcon: const Icon(Icons.search_rounded, size: 20),
            filled: true, fillColor: Colors.white, isDense: true,
            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
            enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          ),
        ),
      );

  Widget _itemCard(Map it, List<Map> services, bool canManage) {
    final allow = it['allow_worker_issue'] == true;
    final cap = (it['max_issue_qty'] as num?)?.toDouble() ?? 0;
    final svcs = ((it['allowed_services'] as List?) ?? const []).cast<String>();
    return Card(
      margin: const EdgeInsets.symmetric(vertical: 4),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(children: [
          Row(children: [
            Container(width: 40, height: 40, alignment: Alignment.center,
                decoration: BoxDecoration(
                    color: (allow ? const Color(0xFF16A34A) : const Color(0xFFE11D48)).withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(11)),
                child: Icon(allow ? Icons.check_circle_rounded : Icons.block_rounded,
                    color: allow ? const Color(0xFF16A34A) : const Color(0xFFE11D48), size: 20)),
            const SizedBox(width: 11),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${it['product']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: _navy)),
              const SizedBox(height: 3),
              Text('${it['store']} · ${tr('الرصيد', 'on hand')} ${it['on_hand']} ${it['uom'] ?? ''}',
                  style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
            ])),
            Switch(
              value: allow,
              activeColor: const Color(0xFF16A34A),
              onChanged: !canManage || _busy ? null : (v) => _setAllow(it, v),
            ),
          ]),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: Wrap(spacing: 6, runSpacing: 5, children: [
              if (svcs.isEmpty) _tag(tr('كل الخدمات', 'All services'), const Color(0xFF64748B))
              else for (final s in svcs) _tag(s, const Color(0xFF6366F1)),
              if (cap > 0) _tag('${tr('حد', 'cap')} ${cap.toStringAsFixed(0)}', const Color(0xFFF59E0B))
              else _tag(tr('بلا حد', 'no cap'), const Color(0xFF94A3B8)),
            ])),
            if (canManage)
              TextButton.icon(
                onPressed: _busy ? null : () => _editRules(it, services),
                icon: const Icon(Icons.tune_rounded, size: 17, color: _accent),
                label: Text(tr('ضبط', 'Rules'), style: const TextStyle(color: _accent, fontWeight: FontWeight.w900, fontSize: 12)),
              ),
          ]),
        ]),
      ),
    );
  }

  Future<void> _setAllow(Map it, bool v) async {
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.invPolicySetItem(it['id'] as int, allow: v);
      await _load();
    } catch (e) {
      if (mounted) _snack('$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Which services may draw this item, and the per-issue cap.
  Future<void> _editRules(Map it, List<Map> services) async {
    final selected = Set<int>.from(((it['allowed_service_ids'] as List?) ?? const []).cast<int>());
    final capCtrl = TextEditingController(
        text: ((it['max_issue_qty'] as num?)?.toDouble() ?? 0) == 0 ? '' : '${it['max_issue_qty']}');
    final saved = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSt) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
        child: Container(
          decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
          clipBehavior: Clip.antiAlias,
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Container(
              width: double.infinity, padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
              decoration: const BoxDecoration(gradient: LinearGradient(colors: [_accent, _navy], begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Column(children: [
                Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12), decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
                Text('${it['product']}', textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Colors.white, fontSize: 14.5, fontWeight: FontWeight.w900)),
              ]),
            ),
            Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(tr('الخدمات المسموح لها بالصرف', 'Services allowed to draw it'),
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: _navy)),
              const SizedBox(height: 4),
              Text(tr('اتركها فارغة ليكون متاحاً لكل الخدمات', 'Leave empty to allow every service'),
                  style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
              const SizedBox(height: 10),
              Wrap(spacing: 7, runSpacing: 7, children: [
                for (final s in services)
                  FilterChip(
                    selected: selected.contains(s['id']),
                    label: Text('${s['name']}', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800,
                        color: selected.contains(s['id']) ? Colors.white : _navy)),
                    selectedColor: _accent, backgroundColor: Colors.white,
                    checkmarkColor: Colors.white,
                    side: BorderSide(color: selected.contains(s['id']) ? _accent : Colors.grey.shade300),
                    onSelected: (v) => setSt(() => v ? selected.add(s['id'] as int) : selected.remove(s['id'])),
                  ),
              ]),
              const SizedBox(height: 16),
              Text(tr('حد الصرف للمرة الواحدة', 'Per-issue cap'),
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: _navy)),
              const SizedBox(height: 8),
              TextField(
                controller: capCtrl, keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  hintText: tr('اتركه فارغاً = بلا حد', 'Leave empty = no cap'),
                  filled: true, fillColor: Colors.white, isDense: true,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
                  enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
                ),
              ),
              const SizedBox(height: 16),
              FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: _accent, minimumSize: const Size.fromHeight(50)),
                onPressed: () => Navigator.pop(ctx, true),
                icon: const Icon(Icons.check_rounded),
                label: Text(tr('حفظ السياسة', 'Save policy'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
              ),
              const SizedBox(height: 8),
            ])),
          ]),
        ),
      )),
    );
    if (saved != true) return;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.invPolicySetItem(
        it['id'] as int,
        maxQty: double.tryParse(capCtrl.text.trim()) ?? 0,
        serviceIds: selected.toList(),
      );
      await _load();
      if (mounted) _snack(tr('حُفظت السياسة', 'Policy saved'), c: const Color(0xFF16A34A));
    } catch (e) {
      if (mounted) _snack('$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _tag(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(7)),
        child: Text(t, style: TextStyle(color: c, fontSize: 10, fontWeight: FontWeight.w800)),
      );

  Widget _empty() => ListView(children: [
        const SizedBox(height: 80),
        Icon(Icons.inventory_2_outlined, size: 56, color: Colors.grey.shade300),
        const SizedBox(height: 12),
        Center(child: Text(tr('لا أصناف', 'No items'), style: TextStyle(color: Colors.grey.shade500, fontWeight: FontWeight.w600))),
      ]);
}
