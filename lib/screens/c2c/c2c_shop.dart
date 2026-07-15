import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'c2c_shell.dart';

/// CARE 2 CARE product shop — browse & buy materials.
class C2CShopScreen extends StatefulWidget {
  const C2CShopScreen({super.key});
  @override
  State<C2CShopScreen> createState() => _C2CShopScreenState();
}

class _C2CShopScreenState extends State<C2CShopScreen> {
  Future<Map<String, dynamic>>? _data;
  int? _cat;
  String _q = '';
  final Map<int, Map> _cart = {}; // productId -> {product, qty}

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => setState(() => _data = context.read<AuthProvider>().api.c2cProducts(categoryId: _cat, q: _q));

  int get _cartCount => _cart.values.fold(0, (a, b) => a + (b['qty'] as int));
  double get _cartTotal => _cart.values.fold(0.0, (a, b) => a + ((b['product']['price'] as num).toDouble() * (b['qty'] as int)));

  void _add(Map p) => setState(() {
        final id = p['id'] as int;
        if (_cart.containsKey(id)) {
          _cart[id]!['qty'] = (_cart[id]!['qty'] as int) + 1;
        } else {
          _cart[id] = {'product': p, 'qty': 1};
        }
      });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: C2C.bg,
      appBar: AppBar(
        backgroundColor: C2C.navy, foregroundColor: Colors.white,
        title: Text(tr('المتجر', 'Shop')),
        actions: [
          Stack(alignment: Alignment.center, children: [
            IconButton(icon: const Icon(Icons.shopping_cart_outlined), onPressed: _cartCount == 0 ? null : _openCart),
            if (_cartCount > 0) Positioned(right: 6, top: 8, child: Container(padding: const EdgeInsets.all(4), decoration: const BoxDecoration(color: C2C.red, shape: BoxShape.circle), child: Text('$_cartCount', style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w800)))),
          ]),
        ],
      ),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.all(10),
          child: TextField(
            decoration: InputDecoration(hintText: tr('ابحث عن منتج…', 'Search products…'), prefixIcon: const Icon(Icons.search), filled: true, fillColor: Colors.white, isDense: true, border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)),
            onSubmitted: (v) { _q = v; _load(); },
          ),
        ),
        Expanded(
          child: FutureBuilder<Map<String, dynamic>>(
            future: _data,
            builder: (_, snap) {
              if (!snap.hasData) return const Center(child: CircularProgressIndicator());
              final products = (snap.data!['products'] as List?) ?? [];
              final cats = (snap.data!['categories'] as List?) ?? [];
              return Column(children: [
                if (cats.isNotEmpty) SizedBox(
                  height: 42,
                  child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 8), children: [
                    Padding(padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4), child: ChoiceChip(label: Text(tr('الكل', 'All')), selected: _cat == null, onSelected: (_) { setState(() => _cat = null); _load(); })),
                    for (final c in cats)
                      Padding(padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4), child: ChoiceChip(label: Text('${c['name']} (${c['count']})'), selected: _cat == c['id'], onSelected: (_) { setState(() => _cat = c['id'] as int); _load(); })),
                  ]),
                ),
                Expanded(
                  child: products.isEmpty
                      ? Center(child: Text(tr('لا منتجات', 'No products')))
                      : GridView.builder(
                          padding: const EdgeInsets.all(10),
                          gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(maxCrossAxisExtent: 200, childAspectRatio: 0.66, crossAxisSpacing: 10, mainAxisSpacing: 10),
                          itemCount: products.length,
                          itemBuilder: (_, i) => _card(products[i] as Map),
                        ),
                ),
              ]);
            },
          ),
        ),
      ]),
      bottomSheet: _cartCount == 0 ? null : _cartBar(),
    );
  }

  Widget _card(Map p) => Container(
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 5, offset: Offset(0, 2))]),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Expanded(child: ClipRRect(
            borderRadius: const BorderRadius.vertical(top: Radius.circular(14)),
            child: p['image'] != null
                ? Image.network('${p['image']}', width: double.infinity, fit: BoxFit.cover, errorBuilder: (_, __, ___) => Container(color: C2C.bg, child: const Icon(Icons.inventory_2_outlined, color: Colors.grey, size: 40)))
                : Container(color: C2C.bg, child: const Icon(Icons.inventory_2_outlined, color: Colors.grey, size: 40)),
          )),
          Padding(
            padding: const EdgeInsets.fromLTRB(10, 8, 10, 8),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${p['name']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, height: 1.2)),
              const SizedBox(height: 4),
              Row(children: [
                Text('${p['price']}', style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w900, fontSize: 14)),
                Text(' ${p['currency'] ?? ''}', style: const TextStyle(color: Colors.grey, fontSize: 9)),
                const Spacer(),
                InkWell(onTap: () => _add(p), child: Container(padding: const EdgeInsets.all(6), decoration: const BoxDecoration(color: C2C.navy, shape: BoxShape.circle), child: const Icon(Icons.add, color: Colors.white, size: 16))),
              ]),
            ]),
          ),
        ]),
      );

  Widget _cartBar() => SafeArea(
        child: GestureDetector(
          onTap: _openCart,
          child: Container(
            margin: const EdgeInsets.all(12),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            decoration: BoxDecoration(color: C2C.navy, borderRadius: BorderRadius.circular(14)),
            child: Row(children: [
              Container(padding: const EdgeInsets.all(6), decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(8)), child: Text('$_cartCount', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900))),
              const SizedBox(width: 10),
              Text(tr('عرض السلة', 'View cart'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800)),
              const Spacer(),
              Text('${_cartTotal.toStringAsFixed(2)} KWD', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16)),
            ]),
          ),
        ),
      );

  void _openCart() {
    showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSt) {
        void tweak(int id, int delta) {
          final q = (_cart[id]!['qty'] as int) + delta;
          if (q <= 0) { _cart.remove(id); } else { _cart[id]!['qty'] = q; }
          setSt(() {}); setState(() {});
          if (_cart.isEmpty) Navigator.pop(ctx);
        }
        return Padding(
          padding: EdgeInsets.fromLTRB(16, 14, 16, MediaQuery.of(ctx).viewInsets.bottom + 16),
          child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(tr('سلة المشتريات', 'Cart'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: C2C.navy)),
            const SizedBox(height: 12),
            ...(_cart.values.map((e) {
              final p = e['product'] as Map; final id = p['id'] as int; final qty = e['qty'] as int;
              return Padding(padding: const EdgeInsets.symmetric(vertical: 6), child: Row(children: [
                Expanded(child: Text('${p['name']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13))),
                IconButton(onPressed: () => tweak(id, -1), icon: const Icon(Icons.remove_circle_outline, size: 20)),
                Text('$qty', style: const TextStyle(fontWeight: FontWeight.w800)),
                IconButton(onPressed: () => tweak(id, 1), icon: const Icon(Icons.add_circle_outline, size: 20)),
                SizedBox(width: 62, child: Text('${((p['price'] as num).toDouble() * qty).toStringAsFixed(1)}', textAlign: TextAlign.end, style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w800))),
              ]));
            })),
            const Divider(height: 22),
            Row(children: [Text(tr('الإجمالي', 'Total'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)), const Spacer(), Text('${_cartTotal.toStringAsFixed(2)} KWD', style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w900, fontSize: 18))]),
            const SizedBox(height: 14),
            SizedBox(width: double.infinity, height: 50, child: ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: C2C.red, foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
              onPressed: () { Navigator.pop(ctx); _checkout(); },
              child: Text(tr('إتمام الشراء', 'Checkout'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
            )),
          ]),
        );
      }),
    );
  }

  Future<void> _checkout() async {
    if (!context.read<AuthProvider>().isLoggedIn) {
      await promptLogin(context);
      if (!mounted || !context.read<AuthProvider>().isLoggedIn) return;
    }
    final addr = TextEditingController();
    final area = TextEditingController();
    final phone = TextEditingController();
    String pay = 'cash';
    final ok = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSt) => Padding(
        padding: EdgeInsets.fromLTRB(18, 16, 18, MediaQuery.of(ctx).viewInsets.bottom + 18),
        child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(tr('بيانات التوصيل', 'Delivery details'), style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900, color: C2C.navy)),
          const SizedBox(height: 12),
          _f(area, tr('المنطقة', 'Area'), Icons.map_outlined),
          const SizedBox(height: 9),
          _f(addr, tr('العنوان', 'Address'), Icons.home_outlined),
          const SizedBox(height: 9),
          _f(phone, tr('الهاتف', 'Phone'), Icons.phone_outlined, phone: true),
          const SizedBox(height: 12),
          Text(tr('طريقة الدفع', 'Payment'), style: const TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          Wrap(spacing: 8, children: [for (final p in const [['cash', '💵 نقدًا', 'Cash'], ['knet', '💳 كي نت', 'KNET'], ['card', '🏦 بطاقة', 'Card']]) ChoiceChip(label: Text(gLang == 'en' ? p[2] : p[1]), selected: pay == p[0], onSelected: (_) => setSt(() => pay = p[0]))]),
          const SizedBox(height: 16),
          Row(children: [Text(tr('الإجمالي', 'Total')), const Spacer(), Text('${_cartTotal.toStringAsFixed(2)} KWD', style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w900, fontSize: 18))]),
          const SizedBox(height: 12),
          SizedBox(width: double.infinity, height: 50, child: ElevatedButton(style: ElevatedButton.styleFrom(backgroundColor: C2C.red, foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))), onPressed: () => Navigator.pop(ctx, true), child: Text(tr('تأكيد الطلب', 'Place order'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)))),
        ])),
      )),
    );
    if (ok != true || !mounted) return;
    try {
      final items = _cart.values.map((e) => {'product_id': e['product']['id'], 'quantity': e['qty'], 'price': e['product']['price']}).toList();
      final res = await context.read<AuthProvider>().api.c2cShopOrderCreate({'items': items, 'address': addr.text, 'area': area.text, 'phone': phone.text, 'payment_method': pay});
      if (mounted) {
        setState(() => _cart.clear());
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('✅ ${res['name']} · ${res['amount_total']} KWD'), backgroundColor: const Color(0xFF16A34A)));
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: C2C.red));
    }
  }

  Widget _f(TextEditingController c, String hint, IconData ic, {bool phone = false}) => TextField(
        controller: c, keyboardType: phone ? TextInputType.phone : TextInputType.text,
        decoration: InputDecoration(hintText: hint, prefixIcon: Icon(ic), filled: true, fillColor: C2C.bg, isDense: true, border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)),
      );
}
