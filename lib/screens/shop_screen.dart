import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

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

  Future<void> _checkout() async {
    if (_cart.isEmpty) return;
    final lines = _cart.entries
        .map((e) => {'product_id': e.key, 'qty': e.value['qty']})
        .toList();
    try {
      final r = await context.read<AuthProvider>().api.orderCreate(lines.cast<Map<String, dynamic>>());
      if (!mounted) return;
      Navigator.pop(context);
      setState(() => _cart.clear());
      ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('${tr('تم إنشاء الطلب', 'Order created')} ${r['name']}')));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  void _openCart() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => StatefulBuilder(builder: (ctx, setSheet) {
        return Padding(
          padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
          child: Container(
            padding: const EdgeInsets.all(16),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Row(children: [
                Text(tr('سلة الشراء', 'Cart'),
                    style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                const Spacer(),
                IconButton(icon: const Icon(Icons.close), onPressed: () => Navigator.pop(ctx)),
              ]),
              if (_cart.isEmpty)
                Padding(padding: const EdgeInsets.all(24), child: Text(tr('السلة فارغة', 'Cart is empty')))
              else ...[
                ..._cart.entries.map((e) => ListTile(
                      title: Text('${e.value['name']}'),
                      subtitle: Text('${e.value['price']} × ${e.value['qty']}'),
                      trailing: Row(mainAxisSize: MainAxisSize.min, children: [
                        IconButton(
                            icon: const Icon(Icons.remove_circle_outline),
                            onPressed: () => setState(() {
                                  final q = (e.value['qty'] as int) - 1;
                                  if (q <= 0) {
                                    _cart.remove(e.key);
                                  } else {
                                    e.value['qty'] = q;
                                  }
                                  setSheet(() {});
                                })),
                        Text('${e.value['qty']}'),
                        IconButton(
                            icon: const Icon(Icons.add_circle_outline),
                            onPressed: () => setState(() {
                                  e.value['qty'] = (e.value['qty'] as int) + 1;
                                  setSheet(() {});
                                })),
                      ]),
                    )),
                const Divider(),
                Row(children: [
                  Text(tr('الإجمالي', 'Total'), style: const TextStyle(fontWeight: FontWeight.w800)),
                  const Spacer(),
                  Text(_cartTotal.toStringAsFixed(3),
                      style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
                ]),
                const SizedBox(height: 10),
                SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                        onPressed: _checkout,
                        icon: const Icon(Icons.check),
                        label: Text(tr('إتمام الطلب', 'Checkout')))),
              ],
            ]),
          ),
        );
      }),
    );
  }

  void _info(Map p) async {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      builder: (_) => FutureBuilder<Map<String, dynamic>>(
        future: context.read<AuthProvider>().api.clientProduct(p['id'] as int),
        builder: (ctx, snap) {
          if (!snap.hasData) {
            return const SizedBox(height: 200, child: Center(child: CircularProgressIndicator()));
          }
          final m = snap.data!;
          return Padding(
            padding: const EdgeInsets.all(18),
            child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
              if (m['image'] != null)
                Center(child: Image.network('${m['image']}', height: 150, errorBuilder: (_, __, ___) => const SizedBox())),
              const SizedBox(height: 10),
              Text('${m['name']}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
              Text('${m['price']} ${m['currency'] ?? ''}',
                  style: const TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: Color(0xFF0B6EA8))),
              const SizedBox(height: 8),
              if (m['code'] != null) Text('${tr('الرمز', 'Code')}: ${m['code']}'),
              if (m['category'] != null) Text('${tr('الفئة', 'Category')}: ${m['category']}'),
              if (m['uom'] != null) Text('${tr('الوحدة', 'Unit')}: ${m['uom']}'),
              if (m['qty_available'] != null) Text('${tr('المتوفر', 'In stock')}: ${m['qty_available']}'),
              if (m['description'] != null) Padding(padding: const EdgeInsets.only(top: 8), child: Text('${m['description']}')),
              const SizedBox(height: 14),
              SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                      onPressed: () {
                        _add(m);
                        Navigator.pop(ctx);
                      },
                      icon: const Icon(Icons.add_shopping_cart),
                      label: Text(tr('أضف للسلة', 'Add to cart')))),
            ]),
          );
        },
      ),
    );
  }

  @override
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
        child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
          Expanded(
            child: Stack(children: [
              Positioned.fill(
                child: p['image'] != null
                    ? Image.network('${p['image']}', fit: BoxFit.contain, errorBuilder: (_, __, ___) => const Icon(Icons.inventory_2, size: 40, color: Colors.black26))
                    : const Icon(Icons.inventory_2, size: 40, color: Colors.black26),
              ),
              Positioned(
                top: 2,
                left: 2,
                child: IconButton(
                  iconSize: 20,
                  icon: Icon(p['favorite'] == true ? Icons.favorite : Icons.favorite_border,
                      color: p['favorite'] == true ? Colors.red : Colors.grey),
                  onPressed: () => _toggleFav(p),
                ),
              ),
              Positioned(
                top: 2,
                right: 2,
                child: IconButton(iconSize: 20, icon: const Icon(Icons.info_outline, color: Colors.blue), onPressed: () => _info(p)),
              ),
            ]),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8),
            child: Text('${p['name']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(8, 2, 4, 6),
            child: Row(children: [
              Expanded(child: Text('${p['price']} ${p['currency'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12))),
              IconButton(iconSize: 22, icon: const Icon(Icons.add_circle, color: Color(0xFF0B6EA8)), onPressed: () => _add(p)),
            ]),
          ),
        ]),
      );
}
