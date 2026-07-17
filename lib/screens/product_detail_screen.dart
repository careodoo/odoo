import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// One product, in full: gallery, price, stock, specs and description — with
/// add-to-cart. Reached by tapping any product in the shop.
class ProductDetailScreen extends StatefulWidget {
  const ProductDetailScreen({
    super.key,
    required this.productId,
    required this.name,
    this.onAdd,
    this.inCart = 0,
  });

  final int productId;
  final String name;

  /// Adds [qty] of this product to the shop's cart. Null when the screen is
  /// opened somewhere without a cart (e.g. from an order).
  final void Function(Map product, int qty)? onAdd;
  final int inCart;

  @override
  State<ProductDetailScreen> createState() => _ProductDetailScreenState();
}

class _ProductDetailScreenState extends State<ProductDetailScreen> {
  Future<Map<String, dynamic>>? _future;
  final _page = PageController();
  int _img = 0;
  int _qty = 1;
  bool? _fav;

  static const _navy = Color(0xFF0E3A5F);

  @override
  void initState() {
    super.initState();
    _future = context.read<AuthProvider>().api.clientProduct(widget.productId);
  }

  @override
  void dispose() {
    _page.dispose();
    super.dispose();
  }

  Future<void> _toggleFav(Map p) async {
    try {
      final r = await context.read<AuthProvider>().api.favoriteToggle(widget.productId);
      if (mounted) setState(() => _fav = r['favorite'] as bool);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      body: FutureBuilder<Map<String, dynamic>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Scaffold(
              appBar: AppBar(title: Text(widget.name)),
              body: Center(child: Text('${snap.error}', style: TextStyle(color: cs.outline))),
            );
          }
          final p = snap.data!;
          final images = (p['images'] as List?) ?? const [];
          final fav = _fav ?? (p['favorite'] == true);
          return CustomScrollView(slivers: [
            SliverAppBar(
              expandedHeight: 300,
              pinned: true,
              backgroundColor: _navy,
              foregroundColor: Colors.white,
              // The gallery background is white, so a plain white arrow would
              // vanish — give the back button its own dark scrim so it always
              // reads against any image.
              leading: Padding(
                padding: const EdgeInsets.all(6),
                child: CircleAvatar(
                  backgroundColor: Colors.black.withValues(alpha: 0.35),
                  child: IconButton(
                    icon: const Icon(Icons.arrow_back_rounded, color: Colors.white, size: 20),
                    tooltip: tr('رجوع', 'Back'),
                    onPressed: () => Navigator.maybePop(context),
                  ),
                ),
              ),
              actions: [
                Padding(
                  padding: const EdgeInsets.all(6),
                  child: CircleAvatar(
                    backgroundColor: Colors.black.withValues(alpha: 0.35),
                    child: IconButton(
                      icon: Icon(fav ? Icons.favorite_rounded : Icons.favorite_border_rounded,
                          color: fav ? const Color(0xFFE5484D) : Colors.white, size: 20),
                      tooltip: tr('المفضلة', 'Favourite'),
                      onPressed: () => _toggleFav(p),
                    ),
                  ),
                ),
              ],
              flexibleSpace: FlexibleSpaceBar(background: _gallery(images)),
            ),
            SliverToBoxAdapter(child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 14, 16, 110),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                if (p['category'] != null)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                    decoration: BoxDecoration(
                        color: _navy.withValues(alpha: 0.07), borderRadius: BorderRadius.circular(7)),
                    child: Text('${p['category']}',
                        style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: _navy)),
                  ),
                const SizedBox(height: 8),
                Text('${p['name']}',
                    style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900, height: 1.35)),
                const SizedBox(height: 10),
                Row(crossAxisAlignment: CrossAxisAlignment.baseline, textBaseline: TextBaseline.alphabetic, children: [
                  Text('${p['price']}',
                      style: const TextStyle(fontSize: 26, fontWeight: FontWeight.w900, color: Color(0xFFC0392B))),
                  const SizedBox(width: 5),
                  Text('${p['currency'] ?? ''}',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Colors.grey.shade600)),
                  const SizedBox(width: 8),
                  // Only call it a discount when the client's pricelist really
                  // is below the list price.
                  if (((p['list_price'] ?? 0) as num) > ((p['price'] ?? 0) as num)) ...[
                    Text('${p['list_price']}',
                        style: TextStyle(
                            fontSize: 13, color: Colors.grey.shade500,
                            decoration: TextDecoration.lineThrough)),
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                          color: const Color(0xFF16A34A), borderRadius: BorderRadius.circular(6)),
                      child: Text(
                          '-${(100 - ((p['price'] as num) * 100 / (p['list_price'] as num))).round()}%',
                          style: const TextStyle(
                              fontSize: 9.5, fontWeight: FontWeight.w900, color: Colors.white)),
                    ),
                  ],
                  const Spacer(),
                  _stockPill(p),
                ]),
                const SizedBox(height: 14),
                _specs(p),
                if ((p['description'] ?? '').toString().trim().isNotEmpty) ...[
                  const SizedBox(height: 14),
                  Text(tr('الوصف', 'Description'),
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
                  const SizedBox(height: 6),
                  Text('${p['description']}',
                      style: const TextStyle(fontSize: 13, height: 1.7, color: Color(0xFF334155))),
                ],
                if (((p['attributes'] as List?) ?? const []).isNotEmpty) ...[
                  const SizedBox(height: 14),
                  Text(tr('الخصائص', 'Attributes'),
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
                  const SizedBox(height: 6),
                  Wrap(spacing: 7, runSpacing: 7, children: [
                    for (final a in (p['attributes'] as List))
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
                        decoration: BoxDecoration(
                            color: _navy.withValues(alpha: 0.05),
                            borderRadius: BorderRadius.circular(8),
                            border: Border.all(color: _navy.withValues(alpha: 0.14))),
                        child: Text('${a['name']}: ${a['value']}',
                            style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
                      ),
                  ]),
                ],
              ]),
            )),
          ]);
        },
      ),
      bottomSheet: widget.onAdd == null ? null : _addBar(),
    );
  }

  Widget _gallery(List images) {
    if (images.isEmpty) {
      // The API sends no URL when the product has no image, so this is a real
      // "no picture" state rather than a blank download.
      return Container(
        color: _navy,
        alignment: Alignment.center,
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(Icons.inventory_2_outlined, size: 62, color: Colors.white.withValues(alpha: 0.25)),
          const SizedBox(height: 8),
          Text(tr('لا توجد صورة لهذا المنتج', 'No image for this product'),
              style: TextStyle(color: Colors.white.withValues(alpha: 0.4), fontSize: 11)),
        ]),
      );
    }
    return Stack(children: [
      Container(color: Colors.white),
      PageView.builder(
        controller: _page,
        itemCount: images.length,
        onPageChanged: (i) => setState(() => _img = i),
        itemBuilder: (_, i) => InteractiveViewer(
          maxScale: 4,
          child: Image.network('${images[i]}', fit: BoxFit.contain,
              errorBuilder: (_, __, ___) =>
                  Icon(Icons.broken_image_outlined, size: 50, color: Colors.grey.shade300)),
        ),
      ),
      if (images.length > 1)
        Positioned(bottom: 10, left: 0, right: 0, child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            for (var i = 0; i < images.length; i++)
              AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                margin: const EdgeInsets.symmetric(horizontal: 3),
                width: i == _img ? 18 : 6, height: 6,
                decoration: BoxDecoration(
                  color: i == _img ? _navy : Colors.black26,
                  borderRadius: BorderRadius.circular(3),
                ),
              ),
          ],
        )),
    ]);
  }

  Widget _stockPill(Map p) {
    // Services and consumables have no on-hand figure — saying "0 in stock"
    // for them would be false.
    final qty = p['qty_available'];
    if (qty == null) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
            color: const Color(0xFF0891B2).withValues(alpha: 0.1), borderRadius: BorderRadius.circular(8)),
        child: Text(tr('متاح للطلب', 'Available'),
            style: const TextStyle(fontSize: 10, fontWeight: FontWeight.w900, color: Color(0xFF0891B2))),
      );
    }
    final n = (qty as num).toDouble();
    final c = n > 0 ? const Color(0xFF16A34A) : const Color(0xFFE5484D);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(8)),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(n > 0 ? Icons.check_circle_rounded : Icons.remove_circle_rounded, size: 11, color: c),
        const SizedBox(width: 4),
        Text(n > 0 ? tr('متوفر: ${n.toStringAsFixed(0)}', 'In stock: ${n.toStringAsFixed(0)}')
                   : tr('غير متوفر حاليًا', 'Out of stock'),
            style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, color: c)),
      ]),
    );
  }

  Widget _specs(Map p) {
    final rows = <(String, String, IconData)>[
      if (p['code'] != null) (tr('الكود', 'Code'), '${p['code']}', Icons.tag_rounded),
      if (p['barcode'] != null) (tr('الباركود', 'Barcode'), '${p['barcode']}', Icons.qr_code_rounded),
      if (p['uom'] != null) (tr('الوحدة', 'Unit'), '${p['uom']}', Icons.straighten_rounded),
      if (p['type'] != null) (tr('النوع', 'Type'), '${p['type']}', Icons.category_rounded),
      if (p['weight'] != null) (tr('الوزن', 'Weight'), '${p['weight']} kg', Icons.scale_rounded),
      if (p['volume'] != null) (tr('الحجم', 'Volume'), '${p['volume']} m³', Icons.view_in_ar_rounded),
    ];
    if (rows.isEmpty) return const SizedBox.shrink();
    return Container(
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(
        color: _navy.withValues(alpha: 0.03),
        borderRadius: BorderRadius.circular(13),
        border: Border.all(color: _navy.withValues(alpha: 0.08)),
      ),
      child: Column(children: [
        for (final r in rows) Padding(
          padding: const EdgeInsets.symmetric(vertical: 4),
          child: Row(children: [
            Icon(r.$3, size: 13, color: Colors.grey.shade500),
            const SizedBox(width: 7),
            Text(r.$1, style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600, fontWeight: FontWeight.w600)),
            const Spacer(),
            Text(r.$2, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w800)),
          ]),
        ),
      ]),
    );
  }

  Widget _addBar() => Container(
        padding: const EdgeInsets.fromLTRB(14, 10, 14, 16),
        decoration: BoxDecoration(
          color: Theme.of(context).cardColor,
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.10), blurRadius: 14, offset: const Offset(0, -3))],
        ),
        child: Row(children: [
          Container(
            decoration: BoxDecoration(
              color: _navy.withValues(alpha: 0.06),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(children: [
              IconButton(
                icon: const Icon(Icons.remove_rounded, size: 18),
                onPressed: _qty > 1 ? () => setState(() => _qty--) : null,
              ),
              Text('$_qty', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
              IconButton(
                icon: const Icon(Icons.add_rounded, size: 18),
                onPressed: () => setState(() => _qty++),
              ),
            ]),
          ),
          const SizedBox(width: 10),
          Expanded(child: SizedBox(
            height: 48,
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(
                backgroundColor: _navy, foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13)),
              ),
              icon: const Icon(Icons.add_shopping_cart_rounded, size: 18),
              label: Text(
                  widget.inCart > 0
                      ? tr('أضف للسلة (بها ${widget.inCart})', 'Add to cart (${widget.inCart} in)')
                      : tr('أضف إلى السلة', 'Add to cart'),
                  style: const TextStyle(fontWeight: FontWeight.w900)),
              onPressed: () async {
                final p = await _future;
                if (p == null || !mounted) return;
                widget.onAdd!(p, _qty);
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(SnackBar(
                  content: Text(tr('أُضيف $_qty إلى السلة', 'Added $_qty to cart')),
                  backgroundColor: const Color(0xFF16A34A),
                  duration: const Duration(seconds: 1),
                ));
                Navigator.pop(context);
              },
            ),
          )),
        ]),
      );
}
