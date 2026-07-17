import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'product_detail_screen.dart';

/// Client shop: products at the client's pricelist → categories, favorites,
/// add to cart, checkout (creates a sale order). Mirrors the portal shop.
class ShopScreen extends StatefulWidget {
  const ShopScreen({super.key});
  @override
  State<ShopScreen> createState() => _ShopScreenState();
}

class _ShopScreenState extends State<ShopScreen> {
  bool _loading = true;
  String? _error;
  List<dynamic> _products = [];
  List<dynamic> _categories = [];
  int? _catFilter;
  bool _favOnly = false;
  String _q = '';
  final Map<int, Map<String, dynamic>> _cart = {};

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final d = await context.read<AuthProvider>().api.clientProducts(q: _q);
      _products = d['products'] as List? ?? [];
      _categories = d['categories'] as List? ?? [];

      if (_favOnly && !_products.any((p) => p['favorite'] == true)) _favOnly = false;
      _error = null;
    } catch (e) {
      _error = '$e';
    }
    if (mounted) setState(() => _loading = false);
  }

  List<dynamic> get _shown {
    var r = _products;
    if (_favOnly) r = r.where((p) => p['favorite'] == true).toList();
    if (_catFilter != null) r = r.where((p) => p['category_id'] == _catFilter).toList();
    return r;
  }

  int get _cartCount => _cart.values.fold(0, (a, b) => a + (b['qty'] as int));
  double get _cartTotal =>
      _cart.values.fold(0.0, (a, b) => a + (b['qty'] as int) * (b['price'] as num).toDouble());

  void _add(Map p) => setState(() {
        final id = p['id'] as int;
        if (_cart.containsKey(id)) {
          _cart[id]!['qty'] = (_cart[id]!['qty'] as int) + 1;
        } else {
          _cart[id] = {'name': p['name'], 'price': p['price'], 'qty': 1, 'image': p['image']};
        }
      });

  Future<void> _toggleFav(Map p) async {
    try {
      final r = await context.read<AuthProvider>().api.favoriteToggle(p['id'] as int);
      setState(() => p['favorite'] = r['favorite']);
    } catch (_) {}
  }

  /// Checkout details the client chooses: where it goes and when.
  int? _addressId;
  DateTime? _deliveryDate;
  List<dynamic> _addresses = const [];
  final _noteCtl = TextEditingController();
  bool _busyCheckout = false;

  Future<void> _loadAddresses() async {
    try {
      final a = await context.read<AuthProvider>().api.clientAddresses();
      if (mounted) {
        setState(() {
          _addresses = a;
          // Default to the client's main address so checkout is one tap.
          _addressId ??= a.isNotEmpty ? a.first['id'] as int : null;
        });
      }
    } catch (_) {/* checkout still works; the server uses the account default */}
  }

  String _addrKind(String k) => {
        'main': tr('العنوان الرئيسي', 'Main'),
        'delivery': tr('عنوان تسليم', 'Delivery'),
        'facility': tr('مرفق', 'Facility'),
      }[k] ?? k;

  String _fmt(DateTime d) => '${d.year}-${d.month.toString().padLeft(2, '0')}-'
      '${d.day.toString().padLeft(2, '0')} ${d.hour.toString().padLeft(2, '0')}:'
      '${d.minute.toString().padLeft(2, '0')}';

  Future<void> _checkout() async {
    if (_cart.isEmpty) return;
    setState(() => _busyCheckout = true);
    final lines = _cart.entries
        .map((e) => {'product_id': e.key, 'qty': e.value['qty']})
        .toList();
    try {
      final r = await context.read<AuthProvider>().api.orderCreate(
        lines.cast<Map<String, dynamic>>(),
        addressId: _addressId,
        deliveryDate: _deliveryDate == null ? null : _fmt(_deliveryDate!),
        note: _noteCtl.text,
      );
      if (!mounted) return;
      Navigator.pop(context);
      setState(() {
        _cart.clear();
        _deliveryDate = null;
        _noteCtl.clear();
      });
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('${tr('تم إنشاء الطلب', 'Order created')} ${r['name']}'),
        backgroundColor: const Color(0xFF16A34A),
      ));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text('$e'), backgroundColor: const Color(0xFFE5484D)));
      }
    } finally {
      if (mounted) setState(() => _busyCheckout = false);
    }
  }

  void _openCart() {
    if (_addresses.isEmpty) _loadAddresses();
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => StatefulBuilder(builder: (ctx, setSheet) {
        void sync(VoidCallback fn) { setState(fn); setSheet(() {}); }
        return Padding(
          padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
          child: DraggableScrollableSheet(
            expand: false,
            initialChildSize: _cart.isEmpty ? 0.4 : 0.8,
            maxChildSize: 0.95,
            builder: (_, sc) => Container(
              decoration: BoxDecoration(
                color: Theme.of(ctx).scaffoldBackgroundColor,
                borderRadius: const BorderRadius.vertical(top: Radius.circular(22)),
              ),
              child: Column(children: [
                const SizedBox(height: 9),
                Container(width: 42, height: 4,
                    decoration: BoxDecoration(color: Colors.black12, borderRadius: BorderRadius.circular(4))),
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 10, 8, 4),
                  child: Row(children: [
                    const Icon(Icons.shopping_cart_rounded, color: Color(0xFF0E3A5F), size: 19),
                    const SizedBox(width: 8),
                    Text(tr('سلة الشراء', 'Cart'),
                        style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900, color: Color(0xFF0E3A5F))),
                    const SizedBox(width: 7),
                    if (_cart.isNotEmpty)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                        decoration: BoxDecoration(
                            color: const Color(0xFF0E3A5F), borderRadius: BorderRadius.circular(20)),
                        child: Text(tr('${_cart.length} صنف', '${_cart.length} items'),
                            style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w900)),
                      ),
                    const Spacer(),
                    if (_cart.isNotEmpty)
                      TextButton.icon(
                        onPressed: () => sync(() => _cart.clear()),
                        icon: const Icon(Icons.delete_outline_rounded, size: 16),
                        label: Text(tr('إفراغ', 'Clear'), style: const TextStyle(fontSize: 11.5)),
                        style: TextButton.styleFrom(foregroundColor: const Color(0xFFE5484D)),
                      ),
                    IconButton(icon: const Icon(Icons.close), onPressed: () => Navigator.pop(ctx)),
                  ]),
                ),
                if (_cart.isEmpty)
                  Expanded(child: Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
                    Icon(Icons.remove_shopping_cart_rounded, size: 44, color: Colors.grey.shade300),
                    const SizedBox(height: 10),
                    Text(tr('السلة فارغة', 'Your cart is empty'),
                        style: TextStyle(color: Colors.grey.shade500, fontWeight: FontWeight.w700)),
                  ])))
                else
                  Expanded(child: ListView(controller: sc, padding: const EdgeInsets.fromLTRB(14, 4, 14, 10), children: [
                    for (final e in _cart.entries.toList()) _cartLine(e, sync),
                    const SizedBox(height: 12),
                    _deliverySection(ctx, setSheet),
                    const SizedBox(height: 12),
                    _totalsBox(),
                  ])),
                if (_cart.isNotEmpty)
                  Container(
                    padding: const EdgeInsets.fromLTRB(14, 10, 14, 16),
                    decoration: BoxDecoration(
                      color: Theme.of(ctx).cardColor,
                      boxShadow: [BoxShadow(
                          color: Colors.black.withValues(alpha: 0.08), blurRadius: 12, offset: const Offset(0, -3))],
                    ),
                    child: SizedBox(
                      height: 50, width: double.infinity,
                      child: ElevatedButton.icon(
                        style: ElevatedButton.styleFrom(
                          backgroundColor: const Color(0xFF16A34A), foregroundColor: Colors.white,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                        ),
                        onPressed: _busyCheckout ? null : _checkout,
                        icon: _busyCheckout
                            ? const SizedBox(width: 17, height: 17,
                                child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                            : const Icon(Icons.check_circle_rounded),
                        label: Text(
                            tr('إتمام الطلب · ${_cartTotal.toStringAsFixed(3)}',
                               'Place order · ${_cartTotal.toStringAsFixed(3)}'),
                            style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5)),
                      ),
                    ),
                  ),
              ]),
            ),
          ),
        );
      }),
    );
  }

  Widget _cartLine(MapEntry<int, Map<String, dynamic>> e, void Function(VoidCallback) sync) {
    final v = e.value;
    final qty = v['qty'] as int;
    final price = (v['price'] as num).toDouble();
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.all(9),
      decoration: BoxDecoration(
        color: Theme.of(context).cardColor,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
      ),
      child: Row(children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(10),
          child: Container(
            width: 52, height: 52, color: Colors.white,
            child: v['image'] != null
                ? Image.network('${v['image']}', fit: BoxFit.contain,
                    errorBuilder: (_, __, ___) => _fallback())
                : _fallback(),
          ),
        ),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${v['name']}', maxLines: 2, overflow: TextOverflow.ellipsis,
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
          const SizedBox(height: 2),
          Text([
            if (v['code'] != null) '${v['code']}',
            '$price${v['uom'] != null ? ' / ${v['uom']}' : ''}',
          ].join(' · '),
              maxLines: 1, overflow: TextOverflow.ellipsis,
              style: TextStyle(fontSize: 10, color: Colors.grey.shade600)),
          const SizedBox(height: 4),
          Text((price * qty).toStringAsFixed(3),
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: Color(0xFFC0392B))),
        ])),
        Container(
          decoration: BoxDecoration(
            color: const Color(0xFF0E3A5F).withValues(alpha: 0.05),
            borderRadius: BorderRadius.circular(10),
          ),
          child: Row(mainAxisSize: MainAxisSize.min, children: [
            IconButton(
              iconSize: 17,
              constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
              padding: EdgeInsets.zero,
              icon: Icon(qty == 1 ? Icons.delete_outline_rounded : Icons.remove_rounded,
                  color: qty == 1 ? const Color(0xFFE5484D) : null),
              onPressed: () => sync(() {
                if (qty <= 1) {
                  _cart.remove(e.key);
                } else {
                  v['qty'] = qty - 1;
                }
              }),
            ),
            Text('$qty', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13)),
            IconButton(
              iconSize: 17,
              constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
              padding: EdgeInsets.zero,
              icon: const Icon(Icons.add_rounded),
              onPressed: () => sync(() => v['qty'] = qty + 1),
            ),
          ]),
        ),
      ]),
    );
  }

  /// Where and when — chosen by the client from the addresses already on their
  /// account, so nothing has to be retyped.
  Widget _deliverySection(BuildContext ctx, StateSetter setSheet) => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Theme.of(context).cardColor,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.local_shipping_rounded, size: 15, color: Color(0xFF16A34A)),
            const SizedBox(width: 6),
            Text(tr('التسليم', 'Delivery'),
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: Color(0xFF16A34A))),
          ]),
          const SizedBox(height: 10),
          Text(tr('عنوان التسليم', 'Delivery address'),
              style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: Colors.grey.shade600)),
          const SizedBox(height: 5),
          if (_addresses.isEmpty)
            Text(tr('يُستخدم العنوان الافتراضي لحسابك', 'Your default account address will be used'),
                style: TextStyle(fontSize: 11, color: Colors.grey.shade500))
          else
            for (final a in _addresses)
              InkWell(
                borderRadius: BorderRadius.circular(10),
                onTap: () { setState(() => _addressId = a['id'] as int); setSheet(() {}); },
                child: Container(
                  margin: const EdgeInsets.only(bottom: 6),
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 7),
                  decoration: BoxDecoration(
                    color: _addressId == a['id']
                        ? const Color(0xFF16A34A).withValues(alpha: 0.07)
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                        color: _addressId == a['id']
                            ? const Color(0xFF16A34A)
                            : Colors.grey.withValues(alpha: 0.25)),
                  ),
                  child: Row(children: [
                    Icon(
                        _addressId == a['id']
                            ? Icons.radio_button_checked_rounded
                            : Icons.radio_button_unchecked_rounded,
                        size: 16,
                        color: _addressId == a['id'] ? const Color(0xFF16A34A) : Colors.grey),
                    const SizedBox(width: 8),
                    Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Row(children: [
                        Flexible(child: Text('${a['name']}',
                            maxLines: 1, overflow: TextOverflow.ellipsis,
                            style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800))),
                        const SizedBox(width: 5),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                          decoration: BoxDecoration(
                              color: Colors.grey.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(4)),
                          child: Text(_addrKind('${a['kind']}'),
                              style: const TextStyle(fontSize: 7.5, fontWeight: FontWeight.w800)),
                        ),
                      ]),
                      if (a['address'] != null)
                        Text('${a['address']}',
                            maxLines: 2, overflow: TextOverflow.ellipsis,
                            style: TextStyle(fontSize: 9.5, color: Colors.grey.shade600)),
                    ])),
                  ]),
                ),
              ),
          const SizedBox(height: 8),
          Text(tr('موعد التسليم المطلوب', 'Requested delivery date'),
              style: TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: Colors.grey.shade600)),
          const SizedBox(height: 5),
          InkWell(
            borderRadius: BorderRadius.circular(10),
            onTap: () async {
              final now = DateTime.now();
              final d = await showDatePicker(
                context: ctx,
                initialDate: _deliveryDate ?? now.add(const Duration(days: 1)),
                // Asking for a delivery in the past is never meaningful.
                firstDate: now,
                lastDate: now.add(const Duration(days: 365)),
              );
              if (d == null) return;
              if (!ctx.mounted) return;
              final t = await showTimePicker(
                context: ctx, initialTime: const TimeOfDay(hour: 9, minute: 0));
              setState(() => _deliveryDate =
                  DateTime(d.year, d.month, d.day, t?.hour ?? 9, t?.minute ?? 0));
              setSheet(() {});
            },
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 9),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: Colors.grey.withValues(alpha: 0.25)),
              ),
              child: Row(children: [
                const Icon(Icons.event_rounded, size: 15, color: Color(0xFF0E3A5F)),
                const SizedBox(width: 8),
                Text(
                    _deliveryDate == null
                        ? tr('اختر التاريخ والوقت (اختياري)', 'Pick date & time (optional)')
                        : _fmt(_deliveryDate!),
                    style: TextStyle(
                        fontSize: 11.5,
                        fontWeight: _deliveryDate == null ? FontWeight.w600 : FontWeight.w900,
                        color: _deliveryDate == null ? Colors.grey.shade500 : null)),
                const Spacer(),
                if (_deliveryDate != null)
                  InkWell(
                    onTap: () { setState(() => _deliveryDate = null); setSheet(() {}); },
                    child: const Icon(Icons.clear_rounded, size: 15, color: Colors.grey),
                  ),
              ]),
            ),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: _noteCtl,
            maxLines: 2,
            style: const TextStyle(fontSize: 12),
            decoration: InputDecoration(
              hintText: tr('ملاحظات للطلب (اختياري)', 'Order notes (optional)'),
              hintStyle: TextStyle(fontSize: 11, color: Colors.grey.shade400),
              isDense: true,
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(10)),
            ),
          ),
        ]),
      );

  Widget _totalsBox() => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: const Color(0xFF0E3A5F).withValues(alpha: 0.04),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Column(children: [
          Row(children: [
            Text(tr('عدد الأصناف', 'Items'),
                style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600, fontWeight: FontWeight.w600)),
            const Spacer(),
            Text('${_cart.length}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
          ]),
          const SizedBox(height: 4),
          Row(children: [
            Text(tr('إجمالي الكميات', 'Total qty'),
                style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600, fontWeight: FontWeight.w600)),
            const Spacer(),
            Text('${_cart.values.fold<int>(0, (a, v) => a + (v['qty'] as int))}',
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5)),
          ]),
          const Divider(height: 16),
          Row(children: [
            Text(tr('الإجمالي', 'Total'),
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: Color(0xFF0E3A5F))),
            const Spacer(),
            Text(_cartTotal.toStringAsFixed(3),
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: Color(0xFFC0392B))),
          ]),
          Align(
            alignment: Alignment.centerLeft,
            child: Text(
                tr('لا يشمل الضريبة — تُحتسب على عرض السعر',
                   'Excludes tax — added on the quotation'),
                style: TextStyle(fontSize: 9, color: Colors.grey.shade500)),
          ),
        ]),
      );

  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(tr('المتجر', 'Shop')),
        actions: [
          Stack(alignment: Alignment.center, children: [
            IconButton(icon: const Icon(Icons.shopping_cart), onPressed: _openCart),
            if (_cartCount > 0)
              Positioned(
                right: 6,
                top: 6,
                child: Container(
                  padding: const EdgeInsets.all(4),
                  decoration: const BoxDecoration(color: Colors.red, shape: BoxShape.circle),
                  child: Text('$_cartCount', style: const TextStyle(color: Colors.white, fontSize: 10)),
                ),
              ),
          ]),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!))
              : Column(children: [
                  Padding(
                    padding: const EdgeInsets.all(10),
                    child: TextField(
                      decoration: InputDecoration(
                        hintText: tr('بحث عن منتج…', 'Search products…'),
                        prefixIcon: const Icon(Icons.search),
                        border: const OutlineInputBorder(),
                        isDense: true,
                      ),
                      onSubmitted: (v) {
                        _q = v;
                        _load();
                      },
                    ),
                  ),
                  SizedBox(
                    height: 42,
                    child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 8), children: [
                      _chip(tr('الكل', 'All'), _catFilter == null && !_favOnly, () => setState(() {
                            _catFilter = null;
                            _favOnly = false;
                          })),
                      _chip('♥ ${tr('المفضّلة', 'Favorites')}', _favOnly, () => setState(() {
                            _favOnly = !_favOnly;
                            _catFilter = null;
                          })),
                      ..._categories.map((c) => _chip('${c['name']} (${c['count']})',
                          _catFilter == c['id'], () => setState(() {
                                _catFilter = c['id'] as int;
                                _favOnly = false;
                              }))),
                    ]),
                  ),
                  Expanded(
                    child: _shown.isEmpty
                        ? Center(child: Text(tr('لا منتجات', 'No products')))
                        : GridView.builder(
                            padding: const EdgeInsets.all(10),
                            gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(
                                maxCrossAxisExtent: 200, childAspectRatio: 0.72, crossAxisSpacing: 10, mainAxisSpacing: 10),
                            itemCount: _shown.length,
                            itemBuilder: (_, i) {
                              final p = _shown[i] as Map;
                              return _card(p);
                            },
                          ),
                  ),
                ]),
    );
  }

  Widget _chip(String label, bool on, VoidCallback onTap) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 6),
        child: ChoiceChip(label: Text(label), selected: on, onSelected: (_) => onTap()),
      );

  Widget _card(Map p) => Card(
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          // The whole card opens the product; an info icon in a corner is a
          // target you have to hunt for.
          onTap: () => _openProduct(p),
          child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
            Expanded(
              child: Stack(children: [
                Positioned.fill(child: Container(
                  color: Colors.white,
                  child: p['image'] != null
                      ? Image.network('${p['image']}', fit: BoxFit.contain,
                          errorBuilder: (_, __, ___) => _fallback())
                      : _fallback(),
                )),
                Positioned(
                  top: 2, left: 2,
                  child: IconButton(
                    iconSize: 19,
                    icon: Icon(p['favorite'] == true ? Icons.favorite : Icons.favorite_border,
                        color: p['favorite'] == true ? Colors.red : Colors.grey),
                    onPressed: () => _toggleFav(p),
                  ),
                ),
                // How many of this product are already in the cart.
                if (((_cart[p['id']]?['qty'] ?? 0) as int) > 0)
                  Positioned(
                    top: 6, right: 6,
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                          color: const Color(0xFF16A34A), borderRadius: BorderRadius.circular(20)),
                      child: Text('${_cart[p['id']]!['qty']}',
                          style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w900)),
                    ),
                  ),
              ]),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8),
              child: Text('${p['name']}',
                  maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(8, 2, 4, 6),
              child: Row(children: [
                Expanded(child: Text('${p['price']} ${p['currency'] ?? ''}',
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12))),
                IconButton(
                  iconSize: 22,
                  icon: const Icon(Icons.add_circle, color: Color(0xFF0B6EA8)),
                  onPressed: () => _add(p),
                ),
              ]),
            ),
          ]),
        ),
      );

  Widget _fallback() => Center(
        child: Icon(Icons.inventory_2_outlined, size: 38, color: Colors.grey.shade300),
      );

  void _openProduct(Map p) => Navigator.push(context, MaterialPageRoute(
        builder: (_) => ProductDetailScreen(
          productId: p['id'] as int,
          name: '${p['name']}',
          inCart: (_cart[p['id']]?['qty'] ?? 0) as int,
          onAdd: (prod, qty) => setState(() {
            final id = p['id'] as int;
            if (_cart.containsKey(id)) {
              _cart[id]!['qty'] = (_cart[id]!['qty'] as int) + qty;
            } else {
              _cart[id] = {
                'name': prod['name'], 'price': prod['price'], 'qty': qty,
                'image': prod['image'], 'uom': prod['uom'], 'code': prod['code'],
              };
            }
          }),
        ),
      )).then((_) {
        // the favourite may have been toggled over on the detail screen
        if (mounted) setState(() {});
      });
}
