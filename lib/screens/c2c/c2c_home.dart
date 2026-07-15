import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'c2c_shell.dart';
import 'c2c_service.dart';

/// CARE 2 CARE storefront home — premium, image-led, animated header.
class C2CHomeScreen extends StatefulWidget {
  const C2CHomeScreen({super.key, this.canSwitchCafm = false, this.guest = false});
  final bool canSwitchCafm;
  final bool guest;
  @override
  State<C2CHomeScreen> createState() => _C2CHomeScreenState();
}

class _C2CHomeScreenState extends State<C2CHomeScreen> with SingleTickerProviderStateMixin {
  Future<Map<String, dynamic>>? _home;
  final _promoCtrl = PageController(viewportFraction: 0.88);
  int _promoPage = 0;
  late final AnimationController _anim;
  Timer? _promoTimer;
  int _promoCount = 1;

  @override
  void initState() {
    super.initState();
    _home = context.read<AuthProvider>().api.c2cHome();
    _anim = AnimationController(vsync: this, duration: const Duration(seconds: 16))..repeat();
    _promoCtrl.addListener(() {
      final p = _promoCtrl.page?.round() ?? 0;
      if (p != _promoPage) setState(() => _promoPage = p);
    });
    _promoTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      if (!mounted || !_promoCtrl.hasClients || _promoCount <= 1) return;
      final next = (_promoPage + 1) % _promoCount;
      _promoCtrl.animateToPage(next, duration: const Duration(milliseconds: 550), curve: Curves.easeInOutCubic);
    });
  }

  @override
  void dispose() {
    _anim.dispose();
    _promoTimer?.cancel();
    _promoCtrl.dispose();
    super.dispose();
  }

  Color _hex(String? s, Color fb) {
    if (s == null || !s.startsWith('#')) return fb;
    return Color(int.parse('FF${s.substring(1)}', radix: 16));
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      color: C2C.bg,
      child: RefreshIndicator(
        onRefresh: () async => setState(() => _home = context.read<AuthProvider>().api.c2cHome()),
        child: FutureBuilder<Map<String, dynamic>>(
          future: _home,
          builder: (_, snap) {
            if (!snap.hasData) return const Center(child: CircularProgressIndicator());
            final d = snap.data!;
            final cats = (d['categories'] as List?) ?? [];
            final popular = (d['popular'] as List?) ?? [];
            final offers = (d['offers'] as List?) ?? [];
            final subs = (d['subscriptions'] as List?) ?? [];
            final reviews = (d['reviews'] as List?) ?? [];
            return CustomScrollView(slivers: [
              _header(context),
              SliverToBoxAdapter(child: _promoCarousel(offers)),
              _rowTitle(tr('الخدمات', 'Services'), tr('عرض الكل', 'All'), () => Navigator.push(context, MaterialPageRoute(builder: (_) => const C2CServiceListScreen(title: 'كل الخدمات')))),
              SliverToBoxAdapter(child: _catGrid(cats)),
              SliverToBoxAdapter(child: _trustStrip()),
              if (popular.isNotEmpty) _rowTitle(tr('الأكثر طلبًا', 'Most popular'), null, null),
              if (popular.isNotEmpty) SliverToBoxAdapter(child: _popularRail(popular)),
              if (subs.isNotEmpty) _rowTitle(tr('الاشتراكات الشهرية', 'Monthly plans'), null, null),
              if (subs.isNotEmpty) SliverToBoxAdapter(child: _subscriptions(subs)),
              SliverToBoxAdapter(child: _contractCta()),
              _rowTitle(tr('كيف يعمل', 'How it works'), null, null),
              SliverToBoxAdapter(child: _howItWorks()),
              SliverToBoxAdapter(child: _socialProof()),
              if (reviews.isNotEmpty) _rowTitle(tr('آراء عملائنا', 'Reviews'), null, null),
              if (reviews.isNotEmpty) SliverToBoxAdapter(child: _testimonials(reviews)),
              const SliverToBoxAdapter(child: SizedBox(height: 20)),
            ]);
          },
        ),
      ),
    );
  }

  // ============ HEADER (animated aurora, glass search) ============
  Widget _header(BuildContext context) {
    final name = context.read<AuthProvider>().profile?.name ?? '';
    final first = name.isNotEmpty ? name.split(' ').first : '';
    return SliverAppBar(
      pinned: true,
      expandedHeight: 164,
      backgroundColor: C2C.deep,
      elevation: 0,
      automaticallyImplyLeading: false,
      flexibleSpace: FlexibleSpaceBar(
        background: Stack(fit: StackFit.expand, children: [
          // base brand gradient (harmonised navy→teal-navy)
          const DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(
            colors: [Color(0xFF1A6187), C2C.navy, Color(0xFF08243B)],
            stops: [0.0, 0.55, 1.0], begin: Alignment.topRight, end: Alignment.bottomLeft))),
          // animated aurora pattern
          AnimatedBuilder(
            animation: _anim,
            builder: (_, __) => CustomPaint(painter: _AuroraPainter(_anim.value)),
          ),
          // gentle bottom fade for legibility of the search bar
          const DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(
            colors: [Colors.transparent, Color(0x2200243B)], begin: Alignment.topCenter, end: Alignment.bottomCenter))),
          SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Container(
                    padding: const EdgeInsets.all(7),
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(colors: [Colors.white, Color(0xFFEAF2F8)]),
                      borderRadius: BorderRadius.circular(11),
                      boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.18), blurRadius: 8, offset: const Offset(0, 3))]),
                    child: const Text('C2', style: TextStyle(color: C2C.navy, fontWeight: FontWeight.w900, fontSize: 15, height: 1)),
                  ),
                  const SizedBox(width: 9),
                  Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                    const Text('CARE 2 CARE', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15.5, letterSpacing: 1.2, height: 1)),
                    const SizedBox(height: 2),
                    Row(children: [
                      const Icon(Icons.location_on, color: Color(0xFF7FD4E8), size: 12),
                      const SizedBox(width: 2),
                      Text(tr('الكويت', 'Kuwait'), style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 11, fontWeight: FontWeight.w600)),
                    ]),
                  ]),
                  const Spacer(),
                  if (widget.guest)
                    _iconBtn(Icons.login_rounded, () => promptLogin(context))
                  else ...[
                    if (widget.canSwitchCafm) _iconBtn(Icons.apartment_rounded, () => openCafm(context)),
                    const SizedBox(width: 6),
                    _iconBtn(Icons.notifications_none_rounded, () {}, dot: true),
                  ],
                ]),
                const SizedBox(height: 12),
                Text(first.isNotEmpty ? '${tr('مرحبًا', 'Hi')} $first 👋' : tr('خدمات منزلية عند بابك', 'Home services at your door'),
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 19, letterSpacing: 0.2, shadows: [Shadow(color: Colors.black26, blurRadius: 6)])),
              ]),
            ),
          ),
        ]),
      ),
      bottom: PreferredSize(
        preferredSize: const Size.fromHeight(58),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
          child: InkWell(
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const C2CServiceListScreen(title: 'كل الخدمات'))),
            child: Container(
              height: 46,
              padding: const EdgeInsets.symmetric(horizontal: 6),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.22), blurRadius: 12, offset: const Offset(0, 4))]),
              child: Row(children: [
                Container(
                  width: 34, height: 34, margin: const EdgeInsets.symmetric(horizontal: 4),
                  decoration: BoxDecoration(color: C2C.navy.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(10)),
                  child: const Icon(Icons.search_rounded, color: C2C.navy, size: 20)),
                const SizedBox(width: 6),
                Text(tr('ابحث عن خدمة…', 'Search a service…'), style: TextStyle(color: Colors.grey.shade500, fontSize: 13.5, fontWeight: FontWeight.w500)),
                const Spacer(),
                Container(
                  margin: const EdgeInsets.symmetric(horizontal: 4),
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
                  decoration: BoxDecoration(gradient: const LinearGradient(colors: [C2C.red, Color(0xFFE05545)]), borderRadius: BorderRadius.circular(10)),
                  child: const Icon(Icons.tune_rounded, color: Colors.white, size: 17)),
              ]),
            ),
          ),
        ),
      ),
    );
  }

  Widget _iconBtn(IconData i, VoidCallback onTap, {bool dot = false}) => InkWell(
        onTap: onTap, borderRadius: BorderRadius.circular(12),
        child: Stack(clipBehavior: Clip.none, children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.18),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: Colors.white.withValues(alpha: 0.22))),
            child: Icon(i, color: Colors.white, size: 19)),
          if (dot) Positioned(top: 4, right: 4, child: Container(width: 8, height: 8, decoration: BoxDecoration(color: const Color(0xFFFF5A4D), shape: BoxShape.circle, border: Border.all(color: C2C.navy, width: 1.4)))),
        ]),
      );

  Widget _rowTitle(String t, String? action, VoidCallback? onAction) => SliverToBoxAdapter(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 2),
          child: Row(children: [
            Container(width: 4, height: 18, decoration: BoxDecoration(gradient: const LinearGradient(colors: [C2C.red, Color(0xFFE05545)], begin: Alignment.topCenter, end: Alignment.bottomCenter), borderRadius: BorderRadius.circular(3))),
            const SizedBox(width: 8),
            Text(t, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900, color: C2C.navy)),
            const Spacer(),
            if (action != null) GestureDetector(onTap: onAction, child: Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4), decoration: BoxDecoration(color: C2C.red.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(20)), child: Text(action, style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w800, fontSize: 12)))),
          ]),
        ),
      );

  // curated, harmonious tints for category tiles (soft, not garish)
  // each: [accent icon-ring color, soft tile background]
  static const _catTints = [
    [Color(0xFF2563EB), Color(0xFFEAF1FE)], // blue
    [Color(0xFF0D9488), Color(0xFFE4F5F2)], // teal
    [Color(0xFF7C3AED), Color(0xFFF1EBFD)], // violet
    [Color(0xFFD97706), Color(0xFFFDF2E2)], // amber
    [Color(0xFFDB2777), Color(0xFFFCE9F2)], // rose
    [Color(0xFF0891B2), Color(0xFFE3F5FA)], // cyan
    [Color(0xFF16A34A), Color(0xFFE7F6EC)], // green
    [Color(0xFF4F46E5), Color(0xFFEBEBFC)], // indigo
  ];

  // ============ PROMO CAROUSEL (image-capable) ============
  Widget _promoCarousel(List offers) {
    final items = offers.isNotEmpty
        ? offers.map<Map<String, dynamic>>((o) => {'ic': o['icon'] ?? '🎉', 't': o['title'] ?? '', 's': o['subtitle'] ?? (o['code'] != null ? 'كود: ${o['code']}' : ''), 'img': o['image'], 'code': o['code'], 'c1': _hex(o['color'] as String?, C2C.navy), 'c2': _hex(o['color2'] as String?, C2C.navy2)}).toList()
        : [
            {'ic': '🎉', 't': 'خصم 20% على أول حجز', 's': 'كود: WELCOME20', 'code': 'WELCOME20', 'c1': const Color(0xFF17547F), 'c2': const Color(0xFF0A2A44)},
          ];
    _promoCount = items.length;
    return Column(children: [
      const SizedBox(height: 14),
      SizedBox(
        height: 138,
        child: PageView.builder(
          controller: _promoCtrl,
          itemCount: items.length,
          itemBuilder: (_, i) {
            final p = items[i];
            final c1 = p['c1'] as Color, c2 = p['c2'] as Color;
            final hasImg = p['img'] != null;
            return Container(
              margin: const EdgeInsets.symmetric(horizontal: 6),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(20),
                boxShadow: [BoxShadow(color: c1.withValues(alpha: 0.35), blurRadius: 16, offset: const Offset(0, 7))],
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(20),
                child: Stack(fit: StackFit.expand, children: [
                  if (hasImg)
                    Image.network('${p['img']}', fit: BoxFit.cover, errorBuilder: (_, __, ___) => DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(colors: [c1, c2], begin: Alignment.topRight, end: Alignment.bottomLeft))))
                  else
                    DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(colors: [c1, c2], begin: Alignment.topRight, end: Alignment.bottomLeft))),
                  // subtle sheen
                  Positioned(top: -30, right: -20, child: Container(width: 120, height: 120, decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.08), shape: BoxShape.circle))),
                  // readability scrim
                  DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(colors: [Colors.black.withValues(alpha: hasImg ? 0.55 : 0.15), Colors.transparent], begin: Alignment.centerLeft, end: Alignment.centerRight))),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(18, 14, 14, 14),
                    child: Row(children: [
                      Expanded(child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                          decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.22), borderRadius: BorderRadius.circular(20), border: Border.all(color: Colors.white.withValues(alpha: 0.35))),
                          child: Text(tr('عرض خاص', 'Special offer'), style: const TextStyle(color: Colors.white, fontSize: 9.5, fontWeight: FontWeight.w800, letterSpacing: 0.5))),
                        const SizedBox(height: 8),
                        Text('${p['t']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 17, height: 1.15, shadows: [Shadow(color: Colors.black38, blurRadius: 4)]), maxLines: 2, overflow: TextOverflow.ellipsis),
                        const SizedBox(height: 5),
                        if ('${p['s']}'.isNotEmpty)
                          Text('${p['s']}', style: TextStyle(color: Colors.white.withValues(alpha: 0.92), fontSize: 11.5, fontWeight: FontWeight.w600), maxLines: 1, overflow: TextOverflow.ellipsis),
                      ])),
                      if (!hasImg) Text('${p['ic']}', style: const TextStyle(fontSize: 44)),
                    ]),
                  ),
                ]),
              ),
            );
          },
        ),
      ),
      if (items.length > 1) Padding(
        padding: const EdgeInsets.only(top: 10),
        child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          for (int i = 0; i < items.length; i++)
            AnimatedContainer(duration: const Duration(milliseconds: 250), width: _promoPage == i ? 20 : 6, height: 6, margin: const EdgeInsets.symmetric(horizontal: 2.5), decoration: BoxDecoration(color: _promoPage == i ? C2C.red : Colors.black.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(3))),
        ]),
      ),
    ]);
  }

  // ============ CATEGORIES (calm, organised soft-tint grid) ============
  Widget _catGrid(List cats) => Padding(
        padding: const EdgeInsets.fromLTRB(14, 6, 14, 0),
        child: GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 4, childAspectRatio: 0.78, crossAxisSpacing: 10, mainAxisSpacing: 14),
          itemCount: cats.length,
          itemBuilder: (_, i) {
            final c = cats[i] as Map;
            final t = _catTints[i % _catTints.length];
            final accent = t[0], soft = t[1];
            return GestureDetector(
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => C2CServiceListScreen(title: '${c['name']}', categoryId: c['id'] as int))),
              child: Column(children: [
                Container(
                  width: 60, height: 60,
                  decoration: BoxDecoration(
                    color: soft,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: accent.withValues(alpha: 0.18)),
                    boxShadow: [BoxShadow(color: accent.withValues(alpha: 0.12), blurRadius: 10, offset: const Offset(0, 5))],
                  ),
                  alignment: Alignment.center,
                  child: Text('${c['icon'] ?? '🧩'}', style: const TextStyle(fontSize: 26)),
                ),
                const SizedBox(height: 7),
                Text('${c['name']}', textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, height: 1.15, color: C2C.ink)),
              ]),
            );
          },
        ),
      );

  Widget _trustStrip() => Container(
        margin: const EdgeInsets.fromLTRB(16, 12, 16, 0),
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 5, offset: Offset(0, 2))]),
        child: Row(mainAxisAlignment: MainAxisAlignment.spaceAround, children: const [
          _Trust('✅', 'معتمدون', 'Vetted'),
          _Trust('⏱️', 'في الموعد', 'On time'),
          _Trust('💳', 'دفع آمن', 'Secure'),
          _Trust('🛡️', 'ضمان', 'Warranty'),
        ]),
      );

  // ============ POPULAR (image rail) ============
  Widget _popularRail(List popular) => SizedBox(
        height: 196,
        child: ListView.builder(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 11),
          itemCount: popular.length,
          itemBuilder: (_, i) {
            final s = popular[i] as Map;
            return GestureDetector(
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => C2CServiceScreen(serviceId: s['id'] as int))),
              child: Container(
                width: 168,
                margin: const EdgeInsets.symmetric(horizontal: 5, vertical: 4),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 3))]),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Stack(children: [
                    ClipRRect(
                      borderRadius: const BorderRadius.vertical(top: Radius.circular(16)),
                      child: s['image'] != null
                          ? Image.network('${s['image']}', height: 104, width: 168, fit: BoxFit.cover)
                          : Container(height: 104, width: 168, color: C2C.navy.withValues(alpha: 0.08), alignment: Alignment.center, child: Text('${s['category_icon'] ?? '🧩'}', style: const TextStyle(fontSize: 40))),
                    ),
                    if ((s['rating'] ?? 0) > 0) Positioned(top: 8, left: 8, child: Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2), decoration: BoxDecoration(color: Colors.black.withValues(alpha: 0.6), borderRadius: BorderRadius.circular(20)), child: Text('⭐ ${s['rating']}', style: const TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.w700)))),
                  ]),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(10, 8, 10, 8),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${s['name']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
                      const SizedBox(height: 2),
                      Text('${s['category'] ?? ''}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.grey, fontSize: 11)),
                      const SizedBox(height: 6),
                      Row(children: [
                        Text('${s['price']}', style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w900, fontSize: 15)),
                        const SizedBox(width: 2),
                        Text('${s['currency'] ?? ''}', style: const TextStyle(color: Colors.grey, fontSize: 9)),
                        const Spacer(),
                        Container(padding: const EdgeInsets.all(5), decoration: const BoxDecoration(color: C2C.navy, shape: BoxShape.circle), child: const Icon(Icons.add, color: Colors.white, size: 14)),
                      ]),
                    ]),
                  ),
                ]),
              ),
            );
          },
        ),
      );

  // ============ SUBSCRIPTIONS ============
  Widget _subscriptions(List subs) => SizedBox(
        height: 194,
        child: ListView.builder(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 11),
          itemCount: subs.length,
          itemBuilder: (_, i) {
            final s = subs[i] as Map;
            final col = _hex(s['color'] as String?, C2C.navy);
            final feats = (s['features'] as List?) ?? [];
            return Container(
              width: 218,
              margin: const EdgeInsets.symmetric(horizontal: 5, vertical: 4),
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: [col, Color.lerp(col, Colors.black, 0.4)!], begin: Alignment.topRight, end: Alignment.bottomLeft),
                borderRadius: BorderRadius.circular(16),
                boxShadow: [BoxShadow(color: col.withValues(alpha: 0.35), blurRadius: 8, offset: const Offset(0, 3))],
              ),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${s['name']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14), maxLines: 2, overflow: TextOverflow.ellipsis)),
                  if (s['popular'] == true) Container(padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)), child: Text(tr('الأفضل', 'Best'), style: TextStyle(color: col, fontSize: 9, fontWeight: FontWeight.w900))),
                ]),
                const SizedBox(height: 8),
                Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                  Text('${s['price']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 24)),
                  const SizedBox(width: 3),
                  Padding(padding: const EdgeInsets.only(bottom: 3), child: Text('KWD/${s['period'] == 'yearly' ? tr('سنة', 'yr') : tr('شهر', 'mo')}', style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 10))),
                  if ((s['save_pct'] ?? 0) > 0) ...[const SizedBox(width: 5), Padding(padding: const EdgeInsets.only(bottom: 3), child: Text('-${s['save_pct']}%', style: const TextStyle(color: Color(0xFFFFD54F), fontWeight: FontWeight.w900, fontSize: 11)))],
                ]),
                const SizedBox(height: 8),
                for (final f in feats.take(3)) Padding(padding: const EdgeInsets.only(bottom: 3), child: Row(children: [const Icon(Icons.check_circle, color: Colors.white70, size: 13), const SizedBox(width: 5), Expanded(child: Text('$f', style: const TextStyle(color: Colors.white, fontSize: 10.5), maxLines: 1, overflow: TextOverflow.ellipsis))])),
              ]),
            );
          },
        ),
      );

  // ============ CONTRACT CTA ============
  Widget _contractCta() => Container(
        margin: const EdgeInsets.fromLTRB(16, 16, 16, 0),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(gradient: const LinearGradient(colors: [Color(0xFF17547F), Color(0xFF0E3A5F)]), borderRadius: BorderRadius.circular(16)),
        child: Row(children: [
          const Text('🏢', style: TextStyle(fontSize: 34)),
          const SizedBox(width: 12),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(tr('عقود طويلة الأمد للشركات', 'Long-term contracts'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13.5)),
            const SizedBox(height: 3),
            Text(tr('اطلب عرض سعر ونحوّلك لعميل إدارة مرافق', 'Request a quote → become a facilities client'), style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 11)),
          ])),
          const SizedBox(width: 8),
          ElevatedButton(style: ElevatedButton.styleFrom(backgroundColor: Colors.white, foregroundColor: C2C.navy, visualDensity: VisualDensity.compact, padding: const EdgeInsets.symmetric(horizontal: 12)), onPressed: _contractSheet, child: Text(tr('عرض سعر', 'Quote'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12))),
        ]),
      );

  void _contractSheet() {
    final title = TextEditingController();
    final name = TextEditingController(text: context.read<AuthProvider>().profile?.name ?? '');
    final phone = TextEditingController();
    final desc = TextEditingController();
    showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (ctx) => Padding(
        padding: EdgeInsets.fromLTRB(18, 16, 18, MediaQuery.of(ctx).viewInsets.bottom + 18),
        child: SingleChildScrollView(child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(tr('طلب تعاقد / خدمة طويلة الأمد', 'Long-term / contract request'), style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: C2C.navy)),
          const SizedBox(height: 12),
          _f(title, tr('عنوان الطلب', 'Request title'), Icons.title),
          const SizedBox(height: 9),
          _f(name, tr('الاسم', 'Name'), Icons.person_outline),
          const SizedBox(height: 9),
          _f(phone, tr('الهاتف', 'Phone'), Icons.phone_outlined, phone: true),
          const SizedBox(height: 9),
          _f(desc, tr('وصف الاحتياج', 'Describe your needs'), Icons.notes, lines: 3),
          const SizedBox(height: 14),
          SizedBox(width: double.infinity, height: 48, child: ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: C2C.red, foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
            onPressed: () async {
              if (title.text.isEmpty || name.text.isEmpty || phone.text.isEmpty) return;
              try {
                await context.read<AuthProvider>().api.c2cContractCreate({'title': title.text, 'customer_name': name.text, 'phone': phone.text, 'description': desc.text, 'audience': 'company'});
                if (ctx.mounted) Navigator.pop(ctx);
                if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تم استلام طلبك، سنرسل عرض السعر قريبًا', 'Received — we will send a quote soon')), backgroundColor: const Color(0xFF16A34A)));
              } catch (e) {
                if (ctx.mounted) ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(content: Text('$e')));
              }
            },
            child: Text(tr('إرسال الطلب', 'Submit request'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)),
          )),
        ])),
      ),
    );
  }

  Widget _f(TextEditingController c, String hint, IconData ic, {bool phone = false, int lines = 1}) => TextField(
        controller: c, keyboardType: phone ? TextInputType.phone : TextInputType.text, maxLines: lines,
        decoration: InputDecoration(hintText: hint, prefixIcon: Icon(ic), filled: true, fillColor: C2C.bg, isDense: true, border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)),
      );

  // ============ HOW IT WORKS ============
  Widget _howItWorks() {
    const steps = [['🧭', 'اختر الخدمة', 'Pick'], ['📅', 'حدّد الموعد', 'Schedule'], ['😌', 'استرخِ', 'Relax']];
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(children: [
        for (int i = 0; i < steps.length; i++) ...[
          Expanded(child: Column(children: [
            CircleAvatar(radius: 24, backgroundColor: C2C.navy.withValues(alpha: 0.08), child: Text(steps[i][0], style: const TextStyle(fontSize: 22))),
            const SizedBox(height: 5),
            Text(gLang == 'en' ? steps[i][2] : steps[i][1], textAlign: TextAlign.center, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
          ])),
          if (i < steps.length - 1) const Padding(padding: EdgeInsets.only(bottom: 18), child: Icon(Icons.arrow_forward_rounded, color: Colors.grey, size: 16)),
        ],
      ]),
    );
  }

  // ============ SOCIAL PROOF ============
  Widget _socialProof() => Container(
        margin: const EdgeInsets.fromLTRB(16, 16, 16, 0),
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(gradient: const LinearGradient(colors: [C2C.navy, C2C.navy2]), borderRadius: BorderRadius.circular(16)),
        child: Row(mainAxisAlignment: MainAxisAlignment.spaceAround, children: const [
          _Metric('12K+', 'عميل سعيد', 'Clients'),
          _Metric('48K+', 'خدمة منجزة', 'Jobs'),
          _Metric('4.9★', 'التقييم', 'Rating'),
        ]),
      );

  // ============ TESTIMONIALS ============
  Widget _testimonials(List reviews) => SizedBox(
        height: 132,
        child: ListView.builder(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 11),
          itemCount: reviews.length,
          itemBuilder: (_, i) {
            final r = reviews[i] as Map;
            final stars = (r['rating'] as int?) ?? 5;
            return Container(
              width: 250,
              margin: const EdgeInsets.symmetric(horizontal: 5, vertical: 4),
              padding: const EdgeInsets.all(13),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 5, offset: Offset(0, 2))]),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('★' * stars + '☆' * (5 - stars), style: const TextStyle(color: Color(0xFFF5A623), fontSize: 14)),
                const SizedBox(height: 7),
                Expanded(child: Text('${r['comment'] ?? ''}', style: const TextStyle(fontSize: 12, height: 1.45), maxLines: 3, overflow: TextOverflow.ellipsis)),
                const SizedBox(height: 5),
                Text('${r['author'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w800, color: C2C.navy, fontSize: 11.5)),
              ]),
            );
          },
        ),
      );
}

class _Trust extends StatelessWidget {
  const _Trust(this.ic, this.ar, this.en);
  final String ic, ar, en;
  @override
  Widget build(BuildContext context) => Column(mainAxisSize: MainAxisSize.min, children: [
        Text(ic, style: const TextStyle(fontSize: 18)),
        const SizedBox(height: 2),
        Text(gLang == 'en' ? en : ar, style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700, color: C2C.navy)),
      ]);
}

class _Metric extends StatelessWidget {
  const _Metric(this.value, this.ar, this.en);
  final String value, ar, en;
  @override
  Widget build(BuildContext context) => Column(mainAxisSize: MainAxisSize.min, children: [
        Text(value, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 19)),
        const SizedBox(height: 1),
        Text(gLang == 'en' ? en : ar, style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 10.5)),
      ]);
}

/// Animated, softly-glowing aurora pattern for the header. Floating light orbs
/// drift on sine paths and a faint diagonal sheen sweeps across — subtle, premium.
class _AuroraPainter extends CustomPainter {
  _AuroraPainter(this.t);
  final double t; // 0..1 loop

  // orb: base x%, base y%, radius, color, drift x, drift y, phase
  static const _orbs = [
    [0.20, 0.35, 90.0, 0xFF2E86B0, 0.06, 0.05, 0.0],
    [0.82, 0.22, 70.0, 0x30FFFFFF, 0.05, 0.07, 1.8],
    [0.68, 0.72, 100.0, 0xFF14808F, 0.07, 0.04, 3.1],
    [0.10, 0.85, 60.0, 0x33C0392B, 0.05, 0.06, 4.6],
  ];

  @override
  void paint(Canvas canvas, Size size) {
    final tau = 2 * math.pi;
    for (final o in _orbs) {
      final phase = o[6] as double;
      final dx = math.sin(tau * t + phase) * (o[4] as double) * size.width;
      final dy = math.cos(tau * t + phase) * (o[5] as double) * size.height;
      final cx = (o[0] as double) * size.width + dx;
      final cy = (o[1] as double) * size.height + dy;
      final r = o[2] as double;
      final base = Color(o[3] as int);
      // orbs with full alpha in hex get a soft opacity here
      final col = base.a == 1.0 ? base.withValues(alpha: 0.16) : base;
      final paint = Paint()
        ..color = col
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 34);
      canvas.drawCircle(Offset(cx, cy), r, paint);
    }
    // faint diagonal sheen sweeping left→right
    final sweep = (t * 1.6 - 0.3) * size.width;
    final sheen = Paint()
      ..shader = LinearGradient(
        colors: [Colors.transparent, Colors.white.withValues(alpha: 0.07), Colors.transparent],
        stops: const [0.0, 0.5, 1.0],
      ).createShader(Rect.fromLTWH(sweep - 80, 0, 160, size.height));
    canvas.save();
    canvas.translate(0, 0);
    canvas.drawRect(Rect.fromLTWH(sweep - 80, -20, 160, size.height + 40), sheen);
    canvas.restore();
  }

  @override
  bool shouldRepaint(_AuroraPainter old) => old.t != t;
}
