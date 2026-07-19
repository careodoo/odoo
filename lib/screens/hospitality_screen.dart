import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';

const _brown = Color(0xFF8A6D3B);
const _navy = Color(0xFF0E3A5F);

const _stateColors = {
  'await_approval': Color(0xFFA78BFA), 'placed': Color(0xFF4AA8FF),
  'accepted': Color(0xFFF5B638), 'preparing': Color(0xFFF59E0B),
  'ready': Color(0xFF16A34A), 'delivered': Color(0xFF64748B),
  'rejected': Color(0xFFE11D48), 'cancelled': Color(0xFF94A3B8),
};

/// خدمة الضيافة — order a drink the way you actually take it, watch it being
/// made, and (if you run a station) work the queue. Three tabs because these
/// are three different jobs, not three views of one.
class HospitalityScreen extends StatefulWidget {
  const HospitalityScreen({super.key});
  @override
  State<HospitalityScreen> createState() => _HospitalityScreenState();
}

class _HospitalityScreenState extends State<HospitalityScreen> with SingleTickerProviderStateMixin {
  late TabController _tabs;
  Map<String, dynamic>? _menu;
  Map<String, dynamic>? _orders;
  Map<String, dynamic>? _kitchen;
  int? _cat;
  bool _busy = false;

  /// The cart lives here until it is placed — one round trip, so a flaky
  /// connection can never leave a half-built order on the server.
  final List<Map<String, dynamic>> _cart = [];
  final _room = TextEditingController();

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this);
    _load();
  }

  @override
  void dispose() {
    _tabs.dispose();
    _room.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final api = context.read<AuthProvider>().api;
    try {
      final m = await api.hospMenu();
      final o = await api.hospMyOrders();
      Map<String, dynamic>? k;
      try {
        k = await api.hospKitchen();
      } catch (_) {/* not kitchen staff — the tab simply stays empty */}
      if (mounted) setState(() { _menu = m; _orders = o; _kitchen = k; });
    } catch (e) {
      if (mounted) _snack('$e');
    }
  }

  void _snack(String m, {Color? c}) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: c ?? _brown, behavior: SnackBarBehavior.floating));

  int get _liveCount => ((_orders?['live'] as List?) ?? const []).length;
  int get _queueCount => (((_kitchen?['stats'] as Map?) ?? const {})['queue'] as int?) ?? 0;

  @override
  Widget build(BuildContext context) {
    final showKitchen = _kitchen != null && (_kitchen!['available'] == true);
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      appBar: AppBar(
        backgroundColor: _brown, foregroundColor: Colors.white,
        title: Text(tr('الضيافة', 'Hospitality'),
            style: const TextStyle(fontWeight: FontWeight.w900)),
        bottom: TabBar(
          controller: _tabs, indicatorColor: Colors.white,
          labelColor: Colors.white, unselectedLabelColor: Colors.white70,
          labelStyle: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13),
          tabs: [
            Tab(text: tr('القائمة', 'Menu')),
            Tab(text: '${tr('طلباتي', 'My orders')}${_liveCount > 0 ? ' ($_liveCount)' : ''}'),
            Tab(text: '${tr('المطبخ', 'Kitchen')}${_queueCount > 0 ? ' ($_queueCount)' : ''}'),
          ],
        ),
      ),
      floatingActionButton: _cart.isEmpty
          ? null
          : FloatingActionButton.extended(
              backgroundColor: _brown,
              onPressed: _cartSheet,
              icon: const Icon(Icons.shopping_cart_rounded),
              label: Text('${tr('السلّة', 'Cart')} (${_cart.length})',
                  style: const TextStyle(fontWeight: FontWeight.w900)),
            ),
      body: _menu == null
          ? const Center(child: CircularProgressIndicator(color: _brown))
          : TabBarView(controller: _tabs, children: [
              _menuTab(),
              _ordersTab(),
              showKitchen ? _kitchenTab() : _emptyTab(tr('لست ضمن طاقم المطبخ', 'Not kitchen staff')),
            ]),
    );
  }

  // ---------------------------------------------------------------- menu tab
  Widget _menuTab() {
    final cats = ((_menu!['categories'] as List?) ?? const []).cast<Map>();
    var items = ((_menu!['items'] as List?) ?? const []).cast<Map>();
    if (_cat != null) items = items.where((i) => i['category_id'] == _cat).toList();
    final favs = ((_menu!['favorites'] as List?) ?? const []).cast<Map>();

    return RefreshIndicator(
      color: _brown,
      onRefresh: _load,
      child: ListView(padding: EdgeInsets.zero, children: [
        _limitsStrip(),
        if (favs.isNotEmpty) _favourites(favs),
        SizedBox(
          height: 44,
          child: ListView(scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4), children: [
            _catChip(null, tr('الكل', 'All'), '🍽️', _brown),
            for (final c in cats)
              _catChip(c['id'] as int, '${c['name']}', '${c['icon'] ?? '☕'}',
                  _hex('${c['color'] ?? '#8a6d3b'}')),
          ]),
        ),
        if (items.isEmpty) _empty(tr('لا أصناف متاحة', 'Nothing available')),
        for (final i in items) _itemCard(i),
        const SizedBox(height: 90),
      ]),
    );
  }

  Color _hex(String h) {
    final v = h.replaceAll('#', '');
    return Color(int.parse('FF$v', radix: 16));
  }

  Widget _catChip(int? id, String label, String icon, Color c) {
    final on = _cat == id;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: ChoiceChip(
        selected: on,
        label: Text('$icon $label',
            style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5,
                color: on ? Colors.white : _navy)),
        selectedColor: c, backgroundColor: Colors.white,
        side: BorderSide(color: on ? c : Colors.grey.shade300),
        onSelected: (_) => setState(() => _cat = id),
      ),
    );
  }

  /// Show the allowance before ordering, not as a refusal at the end.
  Widget _limitsStrip() {
    final limits = ((_menu!['limits'] as List?) ?? const [])
        .cast<Map>()
        .where((l) => ((l['max_items'] as num?) ?? 0) > 0 || ((l['max_cost'] as num?) ?? 0) > 0)
        .toList();
    if (limits.isEmpty) return const SizedBox.shrink();
    return Column(children: [
      for (final l in limits.take(2)) _limitBar(l),
    ]);
  }

  Widget _limitBar(Map l) {
    final maxI = (l['max_items'] as num?) ?? 0;
    final usedI = (l['used_items'] as num?) ?? 0;
    final maxC = (l['max_cost'] as num?) ?? 0;
    final usedC = (l['used_cost'] as num?) ?? 0;
    final pct = maxI > 0 ? usedI / maxI : (maxC > 0 ? usedC / maxC : 0.0);
    final label = maxI > 0
        ? '${l['policy']} — ${tr('المتبقّي لك', 'Left')} ${(maxI - usedI).clamp(0, maxI).toInt()} ${tr('من', 'of')} ${maxI.toInt()}'
        : '${l['policy']} — ${usedC.toStringAsFixed(2)} / $maxC ${tr('د.ك', 'KWD')}';
    final c = pct >= 1 ? const Color(0xFFE11D48) : (pct >= 0.7 ? const Color(0xFFF59E0B) : const Color(0xFF16A34A));
    return Container(
      margin: const EdgeInsets.fromLTRB(12, 10, 12, 0),
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(13),
          border: Border.all(color: Colors.grey.shade200)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label, style: TextStyle(fontSize: 11.5, color: Colors.grey.shade700, fontWeight: FontWeight.w700)),
        const SizedBox(height: 6),
        ClipRRect(
          borderRadius: BorderRadius.circular(5),
          child: LinearProgressIndicator(value: pct.clamp(0.0, 1.0).toDouble(), minHeight: 6,
              backgroundColor: Colors.grey.shade200, valueColor: AlwaysStoppedAnimation(c)),
        ),
      ]),
    );
  }

  Widget _favourites(List<Map> favs) => Padding(
        padding: const EdgeInsets.fromLTRB(12, 14, 12, 0),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('⭐ ${tr('طلبي المعتاد — بنقرة واحدة', 'The usual — one tap')}',
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: _navy)),
          const SizedBox(height: 8),
          SizedBox(
            height: 66,
            child: ListView(scrollDirection: Axis.horizontal, children: [
              for (final f in favs)
                InkWell(
                  onTap: _busy ? null : () => _orderFav(f),
                  borderRadius: BorderRadius.circular(13),
                  child: Container(
                    width: 172, margin: const EdgeInsets.only(left: 8),
                    padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 9),
                    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(13),
                        border: Border.all(color: _brown.withValues(alpha: 0.4))),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${f['icon'] ?? '☕'} ${f['item']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: _navy)),
                      const SizedBox(height: 3),
                      Text('${f['options'] ?? '—'}', maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: TextStyle(fontSize: 10.5, color: Colors.grey.shade600)),
                    ]),
                  ),
                ),
            ]),
          ),
        ]),
      );

  Widget _itemCard(Map i) {
    final servable = i['servable'] == true;
    final sub = servable
        ? '${i['prep_minutes']} ${tr('دقيقة', 'min')} · ${i['cost']} ${tr('د.ك', 'KWD')}'
        : '${tr('خارج وقت التقديم', 'Outside serving hours')} '
            '(${_hhmm(i['serve_from'])}–${_hhmm(i['serve_to'])})';
    return Opacity(
      opacity: servable ? 1 : 0.5,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
        child: Material(
          color: Colors.white, borderRadius: BorderRadius.circular(14),
          child: InkWell(
            borderRadius: BorderRadius.circular(14),
            onTap: servable ? () => _configure(i) : null,
            child: Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: Colors.grey.shade200)),
              child: Row(children: [
                Container(
                  width: 46, height: 46, alignment: Alignment.center,
                  decoration: BoxDecoration(color: _brown.withValues(alpha: 0.1),
                      borderRadius: BorderRadius.circular(13)),
                  child: Text('${i['icon'] ?? '☕'}', style: const TextStyle(fontSize: 22)),
                ),
                const SizedBox(width: 11),
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${i['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: _navy)),
                  const SizedBox(height: 2),
                  Text(sub, style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600)),
                  if (i['description'] != null) ...[
                    const SizedBox(height: 3),
                    Text('${i['description']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 11, color: Colors.grey.shade500)),
                  ],
                ])),
                if (servable) const Icon(Icons.add_circle_rounded, color: _brown),
              ]),
            ),
          ),
        ),
      ),
    );
  }

  String _hhmm(dynamic v) {
    final d = (v as num?)?.toDouble() ?? 0;
    return '${d.floor().toString().padLeft(2, '0')}:${((d - d.floor()) * 60).round().toString().padLeft(2, '0')}';
  }

  // ------------------------------------------------------------- customise
  Future<void> _configure(Map item) async {
    final groups = ((item['option_groups'] as List?) ?? const []).cast<Map>();
    final chosen = <int, Set<int>>{};
    for (final g in groups) {
      final def = ((g['options'] as List?) ?? const [])
          .cast<Map>()
          .where((o) => o['is_default'] == true)
          .map((o) => o['id'] as int);
      chosen[g['id'] as int] = g['multi'] == true ? <int>{} : def.take(1).toSet();
    }
    int qty = 1;
    final note = TextEditingController();
    bool saveFav = false;

    final ok = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSt) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
        child: DraggableScrollableSheet(
          expand: false, initialChildSize: 0.85, minChildSize: 0.5, maxChildSize: 0.95,
          builder: (_, sc) => Container(
            decoration: const BoxDecoration(color: Color(0xFFF6F7F9),
                borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
            clipBehavior: Clip.antiAlias,
            child: Column(children: [
              Container(
                width: double.infinity, padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
                decoration: const BoxDecoration(
                    gradient: LinearGradient(colors: [_brown, _navy],
                        begin: Alignment.topRight, end: Alignment.bottomLeft)),
                child: Column(children: [
                  Center(child: Container(width: 40, height: 4,
                      margin: const EdgeInsets.only(bottom: 12),
                      decoration: BoxDecoration(color: Colors.white54,
                          borderRadius: BorderRadius.circular(3)))),
                  Text('${item['icon'] ?? '☕'}', style: const TextStyle(fontSize: 34)),
                  const SizedBox(height: 4),
                  Text('${item['name']}',
                      style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
                  Text('${item['prep_minutes']} ${tr('دقيقة', 'min')} · ${item['cost']} ${tr('د.ك', 'KWD')}',
                      style: const TextStyle(color: Colors.white70, fontSize: 11.5)),
                ]),
              ),
              Expanded(child: ListView(controller: sc, padding: const EdgeInsets.all(14), children: [
                for (final g in groups) _group(g, chosen, setSt),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(13)),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Row(children: [
                      Text(tr('الكمية', 'Quantity'),
                          style: const TextStyle(fontWeight: FontWeight.w900, color: _navy)),
                      const Spacer(),
                      IconButton(onPressed: qty > 1 ? () => setSt(() => qty--) : null,
                          icon: const Icon(Icons.remove_circle_outline_rounded, color: _brown)),
                      Text('$qty', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17)),
                      IconButton(onPressed: qty < 20 ? () => setSt(() => qty++) : null,
                          icon: const Icon(Icons.add_circle_rounded, color: _brown)),
                    ]),
                    TextField(
                      controller: note,
                      decoration: InputDecoration(
                        hintText: tr('ملاحظة للمُحضِّر (كوب ورقي، بدون رغوة…)',
                            'Note for the barista'),
                        hintStyle: TextStyle(fontSize: 12.5, color: Colors.grey.shade400),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(11)),
                        isDense: true,
                      ),
                    ),
                    const SizedBox(height: 4),
                    CheckboxListTile(
                      value: saveFav, activeColor: _brown, contentPadding: EdgeInsets.zero,
                      controlAffinity: ListTileControlAffinity.leading, dense: true,
                      title: Text(tr('احفظه في «طلبي المعتاد»', 'Save as my usual'),
                          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w700)),
                      onChanged: (v) => setSt(() => saveFav = v ?? false),
                    ),
                  ]),
                ),
                const SizedBox(height: 14),
                FilledButton.icon(
                  style: FilledButton.styleFrom(backgroundColor: _brown,
                      minimumSize: const Size.fromHeight(52)),
                  onPressed: () {
                    for (final g in groups) {
                      if (g['required'] == true && (chosen[g['id']]?.isEmpty ?? true)) {
                        ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(
                            content: Text('${tr('اختر', 'Choose')} ${g['name']}')));
                        return;
                      }
                    }
                    Navigator.pop(ctx, true);
                  },
                  icon: const Icon(Icons.add_shopping_cart_rounded),
                  label: Text(tr('أضف إلى السلّة', 'Add to cart'),
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
                ),
                const SizedBox(height: 10),
              ])),
            ]),
          ),
        ),
      )),
    );
    if (ok != true) return;
    final opts = chosen.values.expand((s) => s).toList();
    final names = <String>[];
    for (final g in groups) {
      for (final o in ((g['options'] as List?) ?? const []).cast<Map>()) {
        if (chosen[g['id']]?.contains(o['id']) ?? false) names.add('${o['name']}');
      }
    }
    setState(() => _cart.add({
          'item_id': item['id'], 'qty': qty, 'options': opts,
          'note': note.text.trim().isEmpty ? null : note.text.trim(),
          '_name': item['name'], '_icon': item['icon'] ?? '☕',
          '_label': names.join(' · '), '_save_fav': saveFav,
        }));
    _snack('${item['name']} ${tr('أُضيف للسلّة', 'added')}', c: const Color(0xFF16A34A));
  }

  Widget _group(Map g, Map<int, Set<int>> chosen, void Function(void Function()) setSt) {
    final id = g['id'] as int;
    final multi = g['multi'] == true;
    final opts = ((g['options'] as List?) ?? const []).cast<Map>();
    return Container(
      margin: const EdgeInsets.only(bottom: 11),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(13)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Text('${g['name']}', style: const TextStyle(fontWeight: FontWeight.w900, color: _navy)),
          const SizedBox(width: 7),
          if (g['required'] == true)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
              decoration: BoxDecoration(color: const Color(0xFFE11D48).withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(7)),
              child: Text(tr('إلزامي', 'Required'),
                  style: const TextStyle(color: Color(0xFFE11D48), fontSize: 10, fontWeight: FontWeight.w900)),
            ),
        ]),
        const SizedBox(height: 4),
        for (final o in opts)
          InkWell(
            onTap: () => setSt(() {
              final set = chosen[id]!;
              if (multi) {
                if (set.contains(o['id'])) {
                  set.remove(o['id']);
                } else if (set.length < ((g['max_select'] as int?) ?? 99)) {
                  set.add(o['id'] as int);
                }
              } else {
                chosen[id] = {o['id'] as int};
              }
            }),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(children: [
                Icon(
                  multi
                      ? (chosen[id]!.contains(o['id'])
                          ? Icons.check_box_rounded : Icons.check_box_outline_blank_rounded)
                      : (chosen[id]!.contains(o['id'])
                          ? Icons.radio_button_checked_rounded : Icons.radio_button_unchecked_rounded),
                  color: chosen[id]!.contains(o['id']) ? _brown : Colors.grey.shade400, size: 21,
                ),
                const SizedBox(width: 9),
                Expanded(child: Text('${o['name']}',
                    style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w600))),
                if (((o['extra_cost'] as num?) ?? 0) > 0)
                  Text('+${o['extra_cost']}',
                      style: const TextStyle(color: _brown, fontWeight: FontWeight.w800, fontSize: 12)),
              ]),
            ),
          ),
      ]),
    );
  }

  // ------------------------------------------------------------------- cart
  Future<void> _cartSheet() async {
    await showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSt) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
        child: Container(
          decoration: const BoxDecoration(color: Colors.white,
              borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
          padding: const EdgeInsets.fromLTRB(18, 14, 18, 22),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 14),
                decoration: BoxDecoration(color: Colors.grey.shade300,
                    borderRadius: BorderRadius.circular(3))),
            Row(children: [
              const Icon(Icons.shopping_cart_rounded, color: _brown),
              const SizedBox(width: 8),
              Text('${tr('سلّتك', 'Your cart')} (${_cart.length})',
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: _navy)),
            ]),
            const SizedBox(height: 8),
            ConstrainedBox(
              constraints: const BoxConstraints(maxHeight: 240),
              child: ListView(shrinkWrap: true, children: [
                for (var idx = 0; idx < _cart.length; idx++)
                  ListTile(
                    dense: true, contentPadding: EdgeInsets.zero,
                    leading: Text('${_cart[idx]['_icon']}', style: const TextStyle(fontSize: 20)),
                    title: Text('${_cart[idx]['_name']} × ${_cart[idx]['qty']}',
                        style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5)),
                    subtitle: Text(
                        [_cart[idx]['_label'], _cart[idx]['note']].where((x) =>
                            x != null && '$x'.isNotEmpty).join(' · '),
                        style: const TextStyle(fontSize: 11.5)),
                    trailing: IconButton(
                      icon: const Icon(Icons.delete_outline_rounded, color: Color(0xFFE11D48)),
                      onPressed: () => setSt(() { _cart.removeAt(idx); setState(() {}); }),
                    ),
                  ),
              ]),
            ),
            const SizedBox(height: 6),
            TextField(
              controller: _room,
              decoration: InputDecoration(
                labelText: tr('المكتب / القاعة', 'Office / room'),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                isDense: true,
              ),
            ),
            const SizedBox(height: 12),
            SizedBox(width: double.infinity, child: FilledButton.icon(
              style: FilledButton.styleFrom(backgroundColor: _brown,
                  minimumSize: const Size.fromHeight(52)),
              onPressed: _cart.isEmpty || _busy ? null : () { Navigator.pop(ctx); _place(); },
              icon: const Icon(Icons.send_rounded),
              label: Text(tr('إرسال الطلب للمطبخ', 'Send to the kitchen'),
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
            )),
          ]),
        ),
      )),
    );
  }

  Future<void> _place() async {
    setState(() => _busy = true);
    try {
      final saveFav = _cart.any((l) => l['_save_fav'] == true);
      final r = await context.read<AuthProvider>().api.hospCreate({
        'room': _room.text.trim(),
        'save_favorite': saveFav,
        'lines': _cart.map((l) => {
              'item_id': l['item_id'], 'qty': l['qty'],
              'options': l['options'], 'note': l['note'],
            }).toList(),
      });
      _cart.clear();
      await _load();
      if (!mounted) return;
      final st = '${r['state']}';
      _snack(
          st == 'await_approval'
              ? tr('أُرسل — بانتظار موافقة المسؤول', 'Sent — awaiting approval')
              : '${tr('أُرسل للمطبخ', 'Sent')} ${r['name']}',
          c: const Color(0xFF16A34A));
      _tabs.animateTo(1);
    } catch (e) {
      if (mounted) _snack('$e'.replaceFirst('Exception: ', ''), c: const Color(0xFFE11D48));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _orderFav(Map f) async {
    setState(() => _busy = true);
    try {
      final r = await context.read<AuthProvider>().api
          .hospFavOrder((f['id'] as num).toInt(), room: _room.text.trim());
      await _load();
      if (!mounted) return;
      _snack('${tr('أُرسل', 'Sent')} ${r['name']}', c: const Color(0xFF16A34A));
      _tabs.animateTo(1);
    } catch (e) {
      if (mounted) _snack('$e'.replaceFirst('Exception: ', ''), c: const Color(0xFFE11D48));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  // ------------------------------------------------------------- my orders
  Widget _ordersTab() {
    final live = ((_orders?['live'] as List?) ?? const []).cast<Map>();
    final past = ((_orders?['past'] as List?) ?? const []).cast<Map>();
    if (live.isEmpty && past.isEmpty) {
      return _emptyTab(tr('لا طلبات بعد', 'No orders yet'));
    }
    return RefreshIndicator(
      color: _brown,
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.only(top: 10, bottom: 90), children: [
        if (live.isNotEmpty) _sectionTitle(tr('الجاري الآن', 'In progress')),
        for (final o in live) _orderCard(o, true),
        if (past.isNotEmpty) _sectionTitle(tr('السجل', 'History')),
        for (final o in past) _orderCard(o, false),
      ]),
    );
  }

  Widget _sectionTitle(String t) => Padding(
        padding: const EdgeInsets.fromLTRB(14, 12, 14, 8),
        child: Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
      );

  Widget _orderCard(Map o, bool live) {
    final c = _stateColors['${o['state']}'] ?? Colors.grey;
    final items = ((o['lines'] as List?) ?? const [])
        .cast<Map>()
        .map((l) => '${l['item']}×${(l['qty'] as num).toInt()}'
            '${l['options'] != null ? ' (${l['options']})' : ''}')
        .join(' · ');
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
            border: Border.all(color: c.withValues(alpha: 0.35))),
        child: Column(children: [
          Row(children: [
            Container(width: 5, height: 42,
                decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(4))),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                Expanded(child: Text('${o['name']}',
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy))),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                  decoration: BoxDecoration(color: c.withValues(alpha: 0.12),
                      borderRadius: BorderRadius.circular(20)),
                  child: Text('${o['state_label']}',
                      style: TextStyle(color: c, fontSize: 10, fontWeight: FontWeight.w900)),
                ),
              ]),
              const SizedBox(height: 3),
              Text(items, maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 12, color: Colors.grey.shade700)),
              const SizedBox(height: 3),
              Text([o['room'], o['placed_at']].where((x) => x != null).join(' · '),
                  style: TextStyle(fontSize: 10.5, color: Colors.grey.shade500)),
            ])),
          ]),
          const SizedBox(height: 8),
          Row(children: [
            if (o['state'] == 'ready')
              _tag('🔔 ${tr('جاهز للاستلام', 'Ready')}', const Color(0xFF16A34A))
            else if (o['state'] == 'await_approval')
              _tag('🔐 ${tr('بانتظار الموافقة', 'Awaiting approval')}', const Color(0xFFA78BFA))
            else if (live && o['is_late'] == true)
              _tag('⏱ ${tr('متأخر', 'Late')} ${((o['wait_minutes'] as num?) ?? 0).toInt()} ${tr('د', 'm')}',
                  const Color(0xFFE11D48))
            else if (live)
              _tag('⏱ ~${(((o['prep_target'] as num?) ?? 5) - ((o['wait_minutes'] as num?) ?? 0)).clamp(0, 99).toInt()} ${tr('د', 'm')}',
                  const Color(0xFFF59E0B)),
            const Spacer(),
            // Odoo sends an unset number as `false`, not null — and in Dart
            // `false != null` is true, so the old guard let int.parse('false')
            // run and threw inside build. That is the grey screen.
            if (((o['rating'] as num?) ?? 0) > 0)
              Text('★' * ((o['rating'] as num).toInt().clamp(0, 5)),
                  style: const TextStyle(color: Color(0xFFF59E0B), fontWeight: FontWeight.w900))
            else if (o['state'] == 'delivered')
              TextButton(
                onPressed: () => _rate(o),
                child: Text(tr('قيّم الطلب', 'Rate'),
                    style: const TextStyle(color: _brown, fontWeight: FontWeight.w900, fontSize: 12.5)),
              ),
            if (live && (o['state'] == 'placed' || o['state'] == 'await_approval'))
              TextButton(
                onPressed: () => _cancel(o),
                child: Text(tr('إلغاء', 'Cancel'),
                    style: const TextStyle(color: Color(0xFFE11D48), fontWeight: FontWeight.w900, fontSize: 12.5)),
              ),
          ]),
        ]),
      ),
    );
  }

  Future<void> _rate(Map o) async {
    final r = await showDialog<int>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text(tr('كيف كان طلبك؟', 'How was it?')),
        content: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          for (var n = 1; n <= 5; n++)
            IconButton(
              onPressed: () => Navigator.pop(c, n),
              icon: const Icon(Icons.star_rounded, color: Color(0xFFF59E0B), size: 30),
            ),
        ]),
      ),
    );
    if (r == null) return;
    try {
      await context.read<AuthProvider>().api.hospRate((o['id'] as num).toInt(), r);
      await _load();
    } catch (e) {
      if (mounted) _snack('$e');
    }
  }

  Future<void> _cancel(Map o) async {
    try {
      await context.read<AuthProvider>().api.hospCancel((o['id'] as num).toInt());
      await _load();
      if (mounted) _snack(tr('أُلغي الطلب', 'Cancelled'));
    } catch (e) {
      if (mounted) _snack('$e');
    }
  }

  // --------------------------------------------------------------- kitchen
  Widget _kitchenTab() {
    final stats = (_kitchen!['stats'] as Map?) ?? const {};
    final orders = ((_kitchen!['orders'] as List?) ?? const []).cast<Map>();
    final approvals = ((_kitchen!['approvals'] as List?) ?? const []).cast<Map>();
    return RefreshIndicator(
      color: _brown,
      onRefresh: _load,
      child: ListView(padding: const EdgeInsets.only(bottom: 90), children: [
        CustomPaint(
          painter: const BrandPattern(opacity: 0.07),
          child: Container(
            padding: const EdgeInsets.fromLTRB(16, 14, 16, 16),
            decoration: const BoxDecoration(
                gradient: LinearGradient(colors: [Color(0xFFE5484D), Color(0xFF8A6D3B), _navy],
                    begin: Alignment.topRight, end: Alignment.bottomLeft)),
            child: Row(children: [
              _ks('${stats['queue'] ?? 0}', tr('في الطابور', 'Queue')),
              _kd(),
              _ks('${stats['late'] ?? 0}', tr('متأخرة', 'Late')),
              _kd(),
              _ks('${stats['ready'] ?? 0}', tr('جاهزة', 'Ready')),
              _kd(),
              _ks('${stats['delivered_today'] ?? 0}', tr('قُدِّمت اليوم', 'Served')),
            ]),
          ),
        ),
        if (approvals.isNotEmpty) ...[
          _sectionTitle('🔐 ${tr('بانتظار الاعتماد', 'Awaiting approval')}'),
          for (final o in approvals) _kdsCard(o, approval: true),
        ],
        if (orders.isEmpty && approvals.isEmpty)
          _empty(tr('لا طلبات في الطابور', 'Nothing in the queue')),
        for (final o in orders) _kdsCard(o),
      ]),
    );
  }

  Widget _ks(String v, String l) => Expanded(child: Column(children: [
        Text(v, style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900)),
        Text(l, textAlign: TextAlign.center,
            style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 9.5, fontWeight: FontWeight.w600)),
      ]));

  Widget _kd() => Container(width: 1, height: 30, color: Colors.white.withValues(alpha: 0.2));

  /// One ticket. Colour comes from how long it has waited against its own
  /// target, so urgency reads without reading numbers.
  Widget _kdsCard(Map o, {bool approval = false}) {
    final waited = ((o['wait_minutes'] as num?) ?? 0).toDouble();
    final target = ((o['prep_target'] as num?) ?? 5).toDouble();
    final ratio = target > 0 ? waited / target : 0;
    Color edge;
    if (approval) {
      edge = const Color(0xFFA78BFA);
    } else if (o['state'] == 'ready') {
      edge = const Color(0xFF16A34A);
    } else if (ratio >= 1) {
      edge = const Color(0xFFE11D48);
    } else if (ratio >= 0.7) {
      edge = const Color(0xFFF59E0B);
    } else {
      edge = const Color(0xFF4AA8FF);
    }
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Container(
        padding: const EdgeInsets.all(12),
        // A borderRadius may only be given on a *uniform* Border — pairing it
        // with a thick left edge asserts at paint time, which a release build
        // shows as a grey rectangle. The urgency edge is its own bar instead.
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.grey.shade200),
        ),
        child: Row(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Container(width: 6,
              decoration: BoxDecoration(color: edge,
                  borderRadius: BorderRadius.circular(3))),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: Text('${o['name']}',
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15.5, color: _navy))),
            _tag('${waited.toInt()} ${tr('د', 'm')}', edge),
          ]),
          Text([o['requester'], o['room']].where((x) => x != null).join(' · '),
              style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600)),
          if (o['is_vip'] == true || o['order_type'] != 'self') ...[
            const SizedBox(height: 5),
            Wrap(spacing: 6, children: [
              if (o['is_vip'] == true) _tag('VIP', const Color(0xFFE11D48)),
              if (o['order_type'] != 'self')
                _tag('${o['guest_count']} ${tr('ضيوف', 'guests')}', const Color(0xFF4AA8FF)),
            ]),
          ],
          const Divider(height: 16),
          for (final l in ((o['lines'] as List?) ?? const []).cast<Map>())
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${l['item']} × ${(l['qty'] as num).toInt()}',
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
                if (l['options'] != null)
                  Text('${l['options']}',
                      style: const TextStyle(color: _brown, fontWeight: FontWeight.w700, fontSize: 12.5)),
                if (l['note'] != null)
                  Text('📝 ${l['note']}', style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600)),
              ]),
            ),
          const SizedBox(height: 6),
          if (approval)
            Row(children: [
              Expanded(child: _kbtn(o, 'approve', tr('اعتماد', 'Approve'), const Color(0xFF16A34A))),
              const SizedBox(width: 8),
              Expanded(child: _kbtn(o, 'reject', tr('رفض', 'Reject'), const Color(0xFFE11D48))),
            ])
          else
            Row(children: [
              if (o['state'] == 'placed')
                Expanded(child: _kbtn(o, 'accept', tr('قبول', 'Accept'), const Color(0xFF4AA8FF))),
              if (o['state'] == 'placed' || o['state'] == 'accepted') ...[
                const SizedBox(width: 8),
                Expanded(child: _kbtn(o, 'ready', tr('جاهز', 'Ready'), const Color(0xFF16A34A))),
              ],
              if (o['state'] == 'ready' || o['state'] == 'preparing') ...[
                const SizedBox(width: 8),
                Expanded(child: _kbtn(o, 'deliver', tr('تم التقديم', 'Served'), _brown)),
              ],
            ]),
          ])),
        ]),
      ),
    );
  }

  Widget _kbtn(Map o, String act, String label, Color c) => OutlinedButton(
        style: OutlinedButton.styleFrom(foregroundColor: c, side: BorderSide(color: c),
            minimumSize: const Size(0, 40)),
        onPressed: _busy ? null : () => _kitchenAct(o, act),
        child: Text(label, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5)),
      );

  Future<void> _kitchenAct(Map o, String act) async {
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.hospKitchenAct((o['id'] as num).toInt(), act);
      await _load();
    } catch (e) {
      if (mounted) _snack('$e'.replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _tag(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(8)),
        child: Text(t, style: TextStyle(color: c, fontSize: 10.5, fontWeight: FontWeight.w900)),
      );

  /// Plain content — never a scrollable. It is dropped inside ListViews, and a
  /// vertical scrollable nested in another has unbounded height and throws.
  Widget _empty(String t) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 70, horizontal: 20),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.local_cafe_outlined, size: 56, color: Colors.grey.shade300),
          const SizedBox(height: 10),
          Text(t, textAlign: TextAlign.center,
              style: TextStyle(color: Colors.grey.shade500, fontWeight: FontWeight.w600)),
        ]),
      );

  /// The same message when it is a whole tab, which does need to scroll so
  /// pull-to-refresh keeps working.
  Widget _emptyTab(String t) => ListView(children: [_empty(t)]);
}
