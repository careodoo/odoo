import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'c2c_shell.dart';
import 'c2c_addresses.dart';
import 'c2c_orders.dart';

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

  int get _cartCount => _cart.values.fold(0, (a, b) => a + intOf(b['qty']));
  double get _cartTotal => _cart.values.fold(0.0, (a, b) => a + (numOf(b['product']['price']).toDouble() * intOf(b['qty'])));

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
        backgroundColor: C2C.red, foregroundColor: Colors.white,
        title: Text(tr('المتجر', 'Shop')),
        actions: [
          Stack(alignment: Alignment.center, children: [
            IconButton(icon: const Icon(Icons.shopping_cart_outlined, color: Colors.white), onPressed: _cartCount == 0 ? null : _openCart),
            if (_cartCount > 0) Positioned(right: 5, top: 6, child: Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2), decoration: BoxDecoration(color: const Color(0xFFFFC107), borderRadius: BorderRadius.circular(20), border: Border.all(color: Colors.white, width: 1.5)), child: Text('$_cartCount', style: const TextStyle(color: Colors.black, fontSize: 10.5, fontWeight: FontWeight.w900)))),
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

  /// Full product detail — gallery, description, price, add-to-cart. Opens as a
  /// draggable sheet from the product image/name.
  void _openProduct(Map p) {
    final images = ((p['images'] as List?) ?? (p['image'] != null ? [p['image']] : [])).cast();
    showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.85, minChildSize: 0.5, maxChildSize: 0.95,
        builder: (ctx, scroll) => Container(
          decoration: const BoxDecoration(color: Colors.white, borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
          child: Column(children: [
            const SizedBox(height: 9),
            Center(child: Container(width: 42, height: 4, decoration: BoxDecoration(color: Colors.black12, borderRadius: BorderRadius.circular(4)))),
            Align(alignment: Alignment.centerLeft, child: IconButton(icon: const Icon(Icons.close_rounded), onPressed: () => Navigator.pop(ctx))),
            Expanded(child: ListView(controller: scroll, padding: const EdgeInsets.fromLTRB(16, 0, 16, 16), children: [
              // gallery
              if (images.isNotEmpty)
                SizedBox(height: 220, child: PageView(children: [
                  for (final img in images)
                    ClipRRect(borderRadius: BorderRadius.circular(16),
                        child: Image.network('$img', fit: BoxFit.cover,
                            errorBuilder: (_, __, ___) => Container(color: C2C.bg, child: const Icon(Icons.inventory_2_outlined, size: 60, color: Colors.grey)))),
                ]))
              else
                Container(height: 200, decoration: BoxDecoration(color: C2C.bg, borderRadius: BorderRadius.circular(16)), child: const Icon(Icons.inventory_2_outlined, size: 60, color: Colors.grey)),
              const SizedBox(height: 14),
              Text('${p['name']}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: C2C.navy)),
              if (p['category'] != null) Padding(padding: const EdgeInsets.only(top: 4), child: Text('${p['category']}', style: TextStyle(color: Colors.grey.shade600, fontSize: 12.5))),
              const SizedBox(height: 10),
              Row(children: [
                Text('${p['price']}', style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w900, fontSize: 26)),
                const SizedBox(width: 4),
                Text('${p['currency'] ?? 'KWD'}', style: TextStyle(color: Colors.grey.shade500, fontSize: 12, fontWeight: FontWeight.w700)),
                if (p['uom'] != null) Text(' / ${p['uom']}', style: TextStyle(color: Colors.grey.shade400, fontSize: 11)),
              ]),
              if ((p['description'] ?? '').toString().trim().isNotEmpty) ...[
                const SizedBox(height: 14),
                Text(tr('الوصف', 'Description'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: C2C.navy)),
                const SizedBox(height: 6),
                Text('${p['description']}', style: const TextStyle(fontSize: 13, height: 1.7, color: Color(0xFF334155))),
              ],
              if (p['code'] != null) Padding(padding: const EdgeInsets.only(top: 10), child: Text('${tr('الكود', 'Code')}: ${p['code']}', style: TextStyle(color: Colors.grey.shade500, fontSize: 11))),
            ])),
            SafeArea(top: false, child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 6, 16, 12),
              child: SizedBox(height: 50, width: double.infinity, child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(backgroundColor: C2C.red, foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
                onPressed: () { _add(p); Navigator.pop(ctx); },
                icon: const Icon(Icons.add_shopping_cart_rounded),
                label: Text(tr('أضف إلى السلة', 'Add to cart'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
              )),
            )),
          ]),
        ),
      ),
    );
  }

  Widget _card(Map p) {
    final id = p['id'] as int;
    final inCart = _cart[id]?['qty'] as int? ?? 0;
    return Container(
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18), boxShadow: [BoxShadow(color: C2C.navy.withValues(alpha: 0.07), blurRadius: 14, offset: const Offset(0, 6))]),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Expanded(child: Stack(children: [
          Positioned.fill(child: GestureDetector(
            onTap: () => _openProduct(p),
            child: ClipRRect(
            borderRadius: const BorderRadius.vertical(top: Radius.circular(18)),
            child: p['image'] != null
                ? Image.network('${p['image']}', width: double.infinity, fit: BoxFit.cover, errorBuilder: (_, __, ___) => Container(color: C2C.bg, child: const Icon(Icons.inventory_2_outlined, color: Colors.grey, size: 40)))
                : Container(color: C2C.bg, child: const Icon(Icons.inventory_2_outlined, color: Colors.grey, size: 40)),
          ))),
          if (inCart > 0) Positioned(top: 8, right: 8, child: Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3), decoration: BoxDecoration(color: C2C.navy, borderRadius: BorderRadius.circular(20)), child: Text(tr('في السلة $inCart', '$inCart in cart'), style: const TextStyle(color: Colors.white, fontSize: 9.5, fontWeight: FontWeight.w800)))),
        ])),
        Padding(
          padding: const EdgeInsets.fromLTRB(11, 9, 11, 10),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            GestureDetector(onTap: () => _openProduct(p), child: Text('${p['name']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, height: 1.2, color: C2C.ink))),
            const SizedBox(height: 8),
            Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(tr('السعر', 'Price'), style: const TextStyle(color: Colors.grey, fontSize: 8.5, fontWeight: FontWeight.w600)),
                Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                  Text('${p['price']}', style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w900, fontSize: 15.5)),
                  Padding(padding: const EdgeInsets.only(bottom: 2, left: 2), child: Text('${p['currency'] ?? 'KWD'}', style: const TextStyle(color: Colors.grey, fontSize: 8.5))),
                ]),
              ])),
              Material(
                color: C2C.navy, borderRadius: BorderRadius.circular(12),
                child: InkWell(borderRadius: BorderRadius.circular(12), onTap: () => _add(p), child: const Padding(padding: EdgeInsets.all(8), child: Icon(Icons.add_shopping_cart_rounded, color: Colors.white, size: 17))),
              ),
            ]),
          ]),
        ),
      ]),
    );
  }

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
                SizedBox(width: 62, child: Text('${(numOf(p['price']).toDouble() * qty).toStringAsFixed(1)}', textAlign: TextAlign.end, style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w800))),
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
    Map? selAddr; // a chosen saved address
    final ok = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSt) => Padding(
        padding: EdgeInsets.fromLTRB(18, 14, 18, MediaQuery.of(ctx).viewInsets.bottom + 18),
        child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Center(child: Container(width: 42, height: 4, decoration: BoxDecoration(color: Colors.black12, borderRadius: BorderRadius.circular(4)))),
          const SizedBox(height: 12),
          Text(tr('بيانات التوصيل', 'Delivery details'), style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900, color: C2C.navy)),
          const SizedBox(height: 12),
          // saved-address picker
          Material(
            color: C2C.navy.withValues(alpha: 0.06), borderRadius: BorderRadius.circular(14),
            child: InkWell(
              borderRadius: BorderRadius.circular(14),
              onTap: () async {
                final a = await Navigator.push<Map?>(context, MaterialPageRoute(builder: (_) => const C2CAddressesScreen(picking: true)));
                if (a != null) setSt(() {
                  selAddr = a;
                  area.text = a['area']?.toString() ?? '';
                  addr.text = a['full_address']?.toString() ?? '';
                  if ((a['phone']?.toString() ?? '').isNotEmpty) phone.text = a['phone'].toString();
                });
              },
              child: Padding(padding: const EdgeInsets.all(13), child: Row(children: [
                const Icon(Icons.bookmark_added_rounded, color: C2C.navy, size: 20),
                const SizedBox(width: 10),
                Expanded(child: Text(selAddr == null ? tr('اختر من عناوينك المحفوظة', 'Choose a saved address') : '${selAddr!['label']} · ${selAddr!['full_address'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13, color: C2C.navy))),
                const Icon(Icons.chevron_left_rounded, color: C2C.navy),
              ])),
            ),
          ),
          const SizedBox(height: 10),
          Row(children: [Expanded(child: Divider(color: Colors.grey.shade300)), Padding(padding: const EdgeInsets.symmetric(horizontal: 8), child: Text(tr('أو أدخل يدويًا', 'or enter manually'), style: const TextStyle(color: C2C.slate, fontSize: 11))), Expanded(child: Divider(color: Colors.grey.shade300))]),
          const SizedBox(height: 10),
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
      final body = {'items': items, 'address': addr.text, 'area': area.text, 'phone': phone.text, 'payment_method': pay};
      if (selAddr != null) body['address_id'] = selAddr!['id'];
      final res = await context.read<AuthProvider>().api.c2cShopOrderCreate(body);
      if (mounted) {
        setState(() => _cart.clear());
        await _orderConfirmed(res);
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: C2C.red));
    }
  }

  /// Professional post-order confirmation dialog with a track-order CTA.
  Future<void> _orderConfirmed(Map res) async {
    final lines = (res['lines'] as List?) ?? [];
    await showDialog(
      context: context, barrierDismissible: false,
      builder: (dctx) => Dialog(
        insetPadding: const EdgeInsets.symmetric(horizontal: 24),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(24)),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          // success header
          Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(20, 26, 20, 20),
            decoration: const BoxDecoration(gradient: LinearGradient(colors: [Color(0xFF16A34A), Color(0xFF15803D)], begin: Alignment.topLeft, end: Alignment.bottomRight), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
            child: Column(children: [
              Container(padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), shape: BoxShape.circle), child: const Icon(Icons.check_circle_rounded, color: Colors.white, size: 46)),
              const SizedBox(height: 12),
              Text(tr('تم استلام طلبك!', 'Order placed!'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 20)),
              const SizedBox(height: 4),
              Text('${res['name']}', style: const TextStyle(color: Colors.white70, fontWeight: FontWeight.w700, fontSize: 13)),
            ]),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
            child: Column(children: [
              if (lines.isNotEmpty) ...[
                ...lines.take(3).map((l) => Padding(padding: const EdgeInsets.symmetric(vertical: 3), child: Row(children: [
                  const Icon(Icons.check_rounded, size: 15, color: C2C.slate),
                  const SizedBox(width: 6),
                  Expanded(child: Text('${(l as Map)['product']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 12.5, color: C2C.ink))),
                  Text('×${numOf(l['qty']).toStringAsFixed(0)}', style: const TextStyle(color: C2C.slate, fontSize: 12, fontWeight: FontWeight.w700)),
                ]))),
                if (lines.length > 3) Align(alignment: Alignment.centerRight, child: Text(tr('+${lines.length - 3} أصناف أخرى', '+${lines.length - 3} more'), style: const TextStyle(color: C2C.slate, fontSize: 11.5))),
                const Divider(height: 20),
              ],
              Row(children: [
                Text(tr('الإجمالي', 'Total'), style: const TextStyle(fontWeight: FontWeight.w800, color: C2C.ink)),
                const Spacer(),
                Text('${numOf(res['amount_total']).toStringAsFixed(2)} ${res['currency'] ?? 'KWD'}', style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w900, fontSize: 18)),
              ]),
              const SizedBox(height: 6),
              Row(children: [
                const Icon(Icons.info_outline_rounded, size: 15, color: C2C.slate),
                const SizedBox(width: 6),
                Expanded(child: Text(tr('سنتواصل معك لتأكيد موعد التوصيل', 'We\'ll contact you to confirm delivery'), style: const TextStyle(color: C2C.slate, fontSize: 11.5))),
              ]),
            ]),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 6, 16, 16),
            child: Row(children: [
              Expanded(child: OutlinedButton(
                style: OutlinedButton.styleFrom(foregroundColor: C2C.navy, side: const BorderSide(color: C2C.navy), padding: const EdgeInsets.symmetric(vertical: 13), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
                onPressed: () => Navigator.pop(dctx),
                child: Text(tr('تم', 'Done'), style: const TextStyle(fontWeight: FontWeight.w800)),
              )),
              const SizedBox(width: 10),
              Expanded(child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(backgroundColor: C2C.red, foregroundColor: Colors.white, padding: const EdgeInsets.symmetric(vertical: 13), shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
                onPressed: () { Navigator.pop(dctx); Navigator.push(context, MaterialPageRoute(builder: (_) => const C2COrdersScreen())); },
                icon: const Icon(Icons.local_shipping_rounded, size: 18),
                label: Text(tr('تتبّع الطلب', 'Track order'), style: const TextStyle(fontWeight: FontWeight.w800)),
              )),
            ]),
          ),
        ]),
      ),
    );
  }

  Widget _f(TextEditingController c, String hint, IconData ic, {bool phone = false}) => TextField(
        controller: c, keyboardType: phone ? TextInputType.phone : TextInputType.text,
        decoration: InputDecoration(hintText: hint, prefixIcon: Icon(ic), filled: true, fillColor: C2C.bg, isDense: true, border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)),
      );
}
