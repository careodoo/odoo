import 'dart:async';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import '../notifications_screen.dart';
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
    _loadUnread();
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

  // real unread count drives the header bell dot (guests have none)
  int _unread = 0;

  Future<void> _loadUnread() async {
    if (widget.guest) return;
    try {
      final (_, n) = await context.read<AuthProvider>().api.notifications();
      if (mounted) setState(() => _unread = n);
    } catch (_) {}
  }

  Future<void> _openNotifications() async {
    await Navigator.push(context, MaterialPageRoute(builder: (_) => const NotificationsScreen()));
    _loadUnread(); // refresh the dot after the user reads them
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
            final subsDesign = (d['subs_design'] as Map?) ?? const {};
            final reviews = (d['reviews'] as List?) ?? [];
            return CustomScrollView(slivers: [
              _header(context),
              SliverToBoxAdapter(child: _promoCarousel(offers)),
              // trust strip sits directly under the slider, no gap
              SliverToBoxAdapter(child: _trustStrip()),
              _servicesHeader(),
              SliverToBoxAdapter(child: _catGrid(cats)),
              if (popular.isNotEmpty) _rowTitle(tr('الأكثر طلبًا', 'Most popular'), null, null),
              if (popular.isNotEmpty) SliverToBoxAdapter(child: _popularRail(popular)),
              if (subs.isNotEmpty)
                _rowTitle('${subsDesign['title'] ?? tr('الاشتراكات الشهرية', 'Monthly plans')}', null, null),
              if (subs.isNotEmpty && subsDesign['subtitle'] != null)
                SliverToBoxAdapter(child: Padding(
                  padding: const EdgeInsets.fromLTRB(28, 0, 16, 2),
                  child: Text('${subsDesign['subtitle']}',
                      style: TextStyle(color: Colors.grey.shade600, fontSize: 12, fontWeight: FontWeight.w600)),
                )),
              if (subs.isNotEmpty) SliverToBoxAdapter(child: _subscriptions(subs, subsDesign)),
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
                    child: const Text('C2C', style: TextStyle(color: C2C.navy, fontWeight: FontWeight.w900, fontSize: 13.5, height: 1)),
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
                    _iconBtn(Icons.notifications_none_rounded, _openNotifications, dot: _unread > 0),
                  ],
                ]),
                const SizedBox(height: 12),
                Text(first.isNotEmpty ? '${tr('مرحبًا', 'Hi')} $first 👋' : tr('كير تو كير … لأننا نهتم', 'CARE 2 CARE … because we care'),
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


  /// A deliberately distinctive band for the services section — it is the
  /// heart of the storefront, so it should not look like every other row title.
  Widget _servicesHeader() => SliverToBoxAdapter(
        child: Container(
          margin: const EdgeInsets.fromLTRB(14, 10, 14, 0),
          padding: const EdgeInsets.fromLTRB(14, 11, 10, 11),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [C2C.navy, Color(0xFF17547F)],
              begin: Alignment.centerRight, end: Alignment.centerLeft),
            borderRadius: BorderRadius.circular(14),
            boxShadow: [BoxShadow(color: C2C.navy.withValues(alpha: 0.25), blurRadius: 10, offset: const Offset(0, 4))],
          ),
          child: Row(children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(color: C2C.red, borderRadius: BorderRadius.circular(9)),
              child: const Icon(Icons.grid_view_rounded, color: Colors.white, size: 15),
            ),
            const SizedBox(width: 9),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              Text(tr('خدماتنا', 'Our services'),
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15.5, height: 1.1)),
              Text(tr('اختر ما تحتاجه واحجز في دقيقة', 'Pick what you need — book in a minute'),
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.75), fontSize: 10.5)),
            ])),
            GestureDetector(
              onTap: () => Navigator.push(context, MaterialPageRoute(
                  builder: (_) => const C2CServiceListScreen(title: 'كل الخدمات'))),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(20)),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  Text(tr('عرض الكل', 'All'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 11.5)),
                  const Icon(Icons.chevron_left_rounded, color: Colors.white, size: 16),
                ]),
              ),
            ),
          ]),
        ),
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
        padding: const EdgeInsets.fromLTRB(14, 10, 14, 0),
        child: GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 4, childAspectRatio: 0.78, crossAxisSpacing: 10, mainAxisSpacing: 14),
          itemCount: cats.length,
          itemBuilder: (_, i) {
            final c = cats[i] as Map;
            return GestureDetector(
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => C2CServiceListScreen(title: '${c['name']}', categoryId: c['id'] as int))),
              child: Column(children: [
                // icon shown directly — no frame/box
                SizedBox(
                  width: 62, height: 62,
                  child: c['image'] != null
                      ? ClipRRect(borderRadius: BorderRadius.circular(16), child: Image.network('${c['image']}', fit: BoxFit.cover, errorBuilder: (_, __, ___) => Center(child: Text('${c['icon'] ?? '🧩'}', style: const TextStyle(fontSize: 42)))))
                      : Center(child: Text('${c['icon'] ?? '🧩'}', style: const TextStyle(fontSize: 42))),
                ),
                const SizedBox(height: 6),
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
        height: 268,
        child: ListView.builder(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          itemCount: popular.length,
          itemBuilder: (_, i) => _popularCard(popular[i] as Map),
        ),
      );

  /// A popular service. Everything on it is real: the rating and the booking
  /// count come from the service's own bookings, so nothing here is decoration
  /// pretending to be data.
  Widget _popularCard(Map s) {
    final rating = (s['rating'] ?? 0) is num ? (s['rating'] as num).toDouble() : 0.0;
    final bookings = (s['bookings'] ?? 0) is num ? (s['bookings'] as num).toInt() : 0;
    final mins = (s['duration_min'] ?? 0) is num ? (s['duration_min'] as num).toInt() : 0;
    return GestureDetector(
      onTap: () => Navigator.push(context, MaterialPageRoute(
          builder: (_) => C2CServiceScreen(serviceId: s['id'] as int))),
      child: Container(
        width: 204,
        margin: const EdgeInsets.symmetric(horizontal: 6, vertical: 6),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.black.withValues(alpha: 0.05)),
          boxShadow: [BoxShadow(color: C2C.navy.withValues(alpha: 0.10), blurRadius: 14, offset: const Offset(0, 5))],
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          // ---- image + scrim ----
          Stack(children: [
            ClipRRect(
              borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
              child: s['image'] != null
                  ? Image.network('${s['image']}', height: 126, width: 204, fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => _popularFallback(s))
                  : _popularFallback(s),
            ),
            Positioned(bottom: 0, left: 0, right: 0, child: Container(
              height: 54,
              decoration: BoxDecoration(gradient: LinearGradient(
                  begin: Alignment.bottomCenter, end: Alignment.topCenter,
                  colors: [Colors.black.withValues(alpha: 0.55), Colors.transparent])),
            )),
            if (rating > 0)
              Positioned(top: 9, left: 9, child: _glassPill(
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    const Icon(Icons.star_rounded, size: 12, color: Color(0xFFFBBF24)),
                    const SizedBox(width: 2),
                    Text(rating.toStringAsFixed(1),
                        style: const TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.w900)),
                  ]))),
            if ((s['category'] ?? '').toString().isNotEmpty)
              Positioned(bottom: 8, right: 9, child: Row(children: [
                Text('${s['category_icon'] ?? ''}', style: const TextStyle(fontSize: 11)),
                const SizedBox(width: 3),
                Text('${s['category']}',
                    style: const TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.w700)),
              ])),
          ]),
          // ---- body ----
          Expanded(child: Padding(
            padding: const EdgeInsets.fromLTRB(11, 9, 11, 9),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${s['name']}',
                  maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, height: 1.3, color: C2C.navy)),
              const SizedBox(height: 5),
              Row(children: [
                if (bookings > 0) ...[
                  _meta(Icons.people_alt_rounded, tr('$bookings حجز', '$bookings booked')),
                  if (mins > 0) _metaDot(),
                ],
                if (mins > 0) _meta(Icons.schedule_rounded, _dur(mins)),
              ]),
              const Spacer(),
              Divider(height: 1, color: Colors.grey.shade200),
              const SizedBox(height: 8),
              Row(children: [
                Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                  Row(crossAxisAlignment: CrossAxisAlignment.baseline, textBaseline: TextBaseline.alphabetic, children: [
                    Text('${s['price']}',
                        style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w900, fontSize: 17)),
                    const SizedBox(width: 3),
                    Text('${s['currency'] ?? ''}',
                        style: TextStyle(color: Colors.grey.shade500, fontSize: 9.5, fontWeight: FontWeight.w700)),
                  ]),
                  if ((s['price_unit'] ?? '').toString().isNotEmpty)
                    Text('${s['price_unit']}',
                        style: TextStyle(color: Colors.grey.shade400, fontSize: 8.5, fontWeight: FontWeight.w600)),
                ]),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(colors: [Color(0xFF17547F), C2C.navy]),
                    borderRadius: BorderRadius.circular(11),
                  ),
                  child: Text(tr('احجز', 'Book'),
                      style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w900)),
                ),
              ]),
            ]),
          )),
        ]),
      ),
    );
  }

  Widget _popularFallback(Map s) => Container(
        height: 126, width: 204,
        decoration: BoxDecoration(gradient: LinearGradient(
            colors: [C2C.navy.withValues(alpha: 0.10), C2C.navy.withValues(alpha: 0.20)],
            begin: Alignment.topRight, end: Alignment.bottomLeft)),
        alignment: Alignment.center,
        child: Text('${s['category_icon'] ?? '🧩'}', style: const TextStyle(fontSize: 44)),
      );

  Widget _glassPill({required Widget child}) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
        decoration: BoxDecoration(
            color: Colors.black.withValues(alpha: 0.55), borderRadius: BorderRadius.circular(20)),
        child: child,
      );

  Widget _meta(IconData ic, String t) => Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(ic, size: 11, color: Colors.grey.shade500),
        const SizedBox(width: 3),
        Text(t, style: TextStyle(fontSize: 10, color: Colors.grey.shade600, fontWeight: FontWeight.w600)),
      ]);

  Widget _metaDot() => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 5),
        child: Container(width: 2.5, height: 2.5,
            decoration: BoxDecoration(color: Colors.grey.shade400, shape: BoxShape.circle)),
      );

  String _dur(int mins) {
    if (mins < 60) return tr('$mins د', '$mins min');
    final h = mins ~/ 60, m = mins % 60;
    final hs = tr('$h س', '${h}h');
    return m == 0 ? hs : '$hs ${tr('$m د', '${m}m')}';
  }

  Widget _subscriptions(List subs, Map design) {
    final showSave = design['show_save'] != false;
    // layout: 'grid' stacks them vertically; anything else is the horizontal rail.
    if (design['layout'] == 'grid') {
      return Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14),
        child: Column(children: [for (final s in subs) _planCard(s as Map, showSave, full: true)]),
      );
    }
    return SizedBox(
      height: 232,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 11),
        itemCount: subs.length,
        itemBuilder: (_, i) => _planCard(subs[i] as Map, showSave),
      ),
    );
  }

  Widget _planCard(Map s, bool showSave, {bool full = false}) {
    final col = _hex(s['color'] as String?, C2C.navy);
    final feats = (s['features'] as List?) ?? [];
    return Container(
      width: full ? double.infinity : 224,
      margin: EdgeInsets.symmetric(horizontal: full ? 0 : 5, vertical: full ? 5 : 4),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: [col, Color.lerp(col, Colors.black, 0.4)!],
            begin: Alignment.topRight, end: Alignment.bottomLeft),
        borderRadius: BorderRadius.circular(16),
        boxShadow: [BoxShadow(color: col.withValues(alpha: 0.35), blurRadius: 8, offset: const Offset(0, 3))],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
        Row(children: [
          Expanded(child: Text('${s['name']}',
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14),
              maxLines: 2, overflow: TextOverflow.ellipsis)),
          if (s['popular'] == true)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
              child: Text(tr('الأفضل', 'Best'),
                  style: TextStyle(color: col, fontSize: 9, fontWeight: FontWeight.w900))),
        ]),
        const SizedBox(height: 8),
        Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
          Text('${s['price']}',
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 24)),
          const SizedBox(width: 3),
          Padding(padding: const EdgeInsets.only(bottom: 3),
              child: Text('KWD/${s['period'] == 'yearly' ? tr('سنة', 'yr') : (s['period'] == 'quarterly' ? tr('ربع', 'qtr') : tr('شهر', 'mo'))}',
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 10))),
          if (showSave && (s['save_pct'] ?? 0) > 0) ...[
            const SizedBox(width: 5),
            Padding(padding: const EdgeInsets.only(bottom: 3),
                child: Text('-${s['save_pct']}%',
                    style: const TextStyle(color: Color(0xFFFFD54F), fontWeight: FontWeight.w900, fontSize: 11))),
          ],
        ]),
        if ((s['visits'] ?? 0) > 0)
          Text(tr('${s['visits']} زيارة', '${s['visits']} visits'),
              style: TextStyle(color: Colors.white.withValues(alpha: 0.7), fontSize: 10)),
        const SizedBox(height: 8),
        for (final f in feats.take(full ? 6 : 3))
          Padding(padding: const EdgeInsets.only(bottom: 3),
              child: Row(children: [
                const Icon(Icons.check_circle, color: Colors.white70, size: 13),
                const SizedBox(width: 5),
                Expanded(child: Text('$f',
                    style: const TextStyle(color: Colors.white, fontSize: 10.5),
                    maxLines: 1, overflow: TextOverflow.ellipsis)),
              ])),
        const SizedBox(height: 9),
        SizedBox(
          width: double.infinity, height: 36,
          child: ElevatedButton(
            style: ElevatedButton.styleFrom(
              backgroundColor: Colors.white, foregroundColor: col,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(11)),
              padding: EdgeInsets.zero,
            ),
            onPressed: () => _subscribe(s, col),
            child: Text(tr('اشترك الآن', 'Subscribe'),
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5)),
          ),
        ),
      ]),
    );
  }

  Future<void> _subscribe(Map plan, Color col) async {
    final auth = context.read<AuthProvider>();
    // Subscribing needs an identified customer.
    if (auth.profile == null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('سجّل الدخول للاشتراك', 'Sign in to subscribe'))));
      return;
    }
    final note = TextEditingController();
    final ok = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (ctx) => Padding(
        padding: EdgeInsets.fromLTRB(18, 16, 18, MediaQuery.of(ctx).viewInsets.bottom + 18),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(width: 42, height: 4, margin: const EdgeInsets.only(bottom: 14),
              decoration: BoxDecoration(color: Colors.black12, borderRadius: BorderRadius.circular(4))),
          Text(tr('تأكيد الاشتراك', 'Confirm subscription'),
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: C2C.navy)),
          const SizedBox(height: 12),
          Container(
            padding: const EdgeInsets.all(13),
            decoration: BoxDecoration(color: col.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(13), border: Border.all(color: col.withValues(alpha: 0.25))),
            child: Row(children: [
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${plan['name']}', style: TextStyle(fontWeight: FontWeight.w900, color: col, fontSize: 14)),
                Text(tr('${plan['visits']} زيارة · ${plan['period'] == 'yearly' ? 'سنوي' : (plan['period'] == 'quarterly' ? 'ربع سنوي' : 'شهري')}',
                        '${plan['visits']} visits'),
                    style: TextStyle(color: Colors.grey.shade600, fontSize: 11)),
              ])),
              Text('${plan['price']} KWD',
                  style: TextStyle(fontWeight: FontWeight.w900, color: col, fontSize: 16)),
            ]),
          ),
          const SizedBox(height: 12),
          TextField(controller: note, maxLines: 2,
              decoration: InputDecoration(
                  hintText: tr('ملاحظات (اختياري)', 'Notes (optional)'),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(11)), isDense: true)),
          const SizedBox(height: 8),
          Text(tr('سيتواصل معك فريقنا لتأكيد المواعيد وبدء الاشتراك.',
                  'Our team will contact you to schedule and start your subscription.'),
              style: TextStyle(color: Colors.grey.shade500, fontSize: 10.5, height: 1.5)),
          const SizedBox(height: 14),
          SizedBox(width: double.infinity, height: 48,
            child: ElevatedButton.icon(
              style: ElevatedButton.styleFrom(backgroundColor: col, foregroundColor: Colors.white,
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
              onPressed: () => Navigator.pop(ctx, true),
              icon: const Icon(Icons.check_circle_rounded),
              label: Text(tr('تأكيد الاشتراك', 'Confirm'),
                  style: const TextStyle(fontWeight: FontWeight.w900)),
            )),
        ]),
      ),
    );
    if (ok != true) return;
    try {
      await auth.api.c2cSubscribe(plan['id'] as int, note: note.text);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('✅ تم استلام طلب اشتراكك', '✅ Subscription requested')),
          backgroundColor: const Color(0xFF16A34A)));
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: C2C.red));
      }
    }
  }

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
