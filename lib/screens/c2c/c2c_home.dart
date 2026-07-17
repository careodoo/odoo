import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import '../notifications_screen.dart';
import 'c2c_shell.dart';
import 'c2c_service.dart';
import 'c2c_orders.dart';
import 'c2c_bookings.dart';
import 'c2c_subscriptions.dart';
import 'c2c_contracts.dart';
import 'c2c_rfq_dialog.dart';
import 'c2c_video.dart';

/// CARE 2 CARE storefront home — premium, image-led, animated header.
class C2CHomeScreen extends StatefulWidget {
  const C2CHomeScreen({super.key, this.canSwitchCafm = false, this.guest = false});
  final bool canSwitchCafm;
  final bool guest;
  @override
  State<C2CHomeScreen> createState() => _C2CHomeScreenState();
}

class _C2CHomeScreenState extends State<C2CHomeScreen> {
  Future<Map<String, dynamic>>? _home;
  final _promoCtrl = PageController(viewportFraction: 0.88);
  int _promoPage = 0;
  Timer? _promoTimer;
  int _promoCount = 1;

  @override
  void initState() {
    super.initState();
    _home = context.read<AuthProvider>().api.c2cHome();
    _loadUnread();
    _loadVideos();
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
  List<dynamic> _videos = const [];

  Future<void> _loadVideos() async {
    try {
      final v = await context.read<AuthProvider>().api.c2cVideos();
      if (mounted) setState(() => _videos = v);
    } catch (_) {}
  }

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
              SliverToBoxAdapter(child: _premiumHeader(context, offers)),
              SliverToBoxAdapter(child: _trustStrip()),
              SliverToBoxAdapter(child: _quickActions()),
              _sectionRow(tr('التصنيفات', 'Categories'),
                  () => Navigator.push(context, MaterialPageRoute(
                      builder: (_) => const C2CServiceListScreen(title: 'كل الخدمات')))),
              SliverToBoxAdapter(child: _categoryCards(cats)),
              if (popular.isNotEmpty)
                _sectionRow(tr('موصى به لك', 'Recommended for you'),
                    () => Navigator.push(context, MaterialPageRoute(
                        builder: (_) => const C2CServiceListScreen(title: 'كل الخدمات')))),
              if (popular.isNotEmpty) SliverToBoxAdapter(child: _popularRail(popular)),
              if (_videos.isNotEmpty)
                _sectionRow(tr('شاهد خدماتنا', 'Watch our services'), () {}),
              if (_videos.isNotEmpty) SliverToBoxAdapter(child: _videoRail()),
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
  // ============ PREMIUM HEADER (red panel + promo + floating search) ============
  Widget _premiumHeader(BuildContext context, List offers) {
    final name = context.read<AuthProvider>().profile?.name ?? '';
    final first = name.isNotEmpty ? name.split(' ').first : '';
    return Stack(clipBehavior: Clip.none, children: [
      // rounded red panel
      Container(
        padding: EdgeInsets.only(top: MediaQuery.of(context).padding.top),
        decoration: const BoxDecoration(
          gradient: LinearGradient(
              colors: [C2C.redBright, C2C.red, C2C.redDeep],
              stops: [0.0, 0.5, 1.0], begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.vertical(bottom: Radius.circular(30)),
        ),
        child: Stack(children: [
          // soft light bloom for depth
          Positioned(top: -30, left: -20, child: _bloom(150, 0.10)),
          Positioned(top: 40, right: -30, child: _bloom(120, 0.08)),
          Padding(
            padding: const EdgeInsets.fromLTRB(18, 10, 18, 34),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              // ---- top row: greeting + location + bell ----
              Row(children: [
                Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text(
                      first.isNotEmpty
                          ? '${_greeting()}، $first 👋'
                          : tr('كير تو كير 👋', 'CARE 2 CARE 👋'),
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
                  const SizedBox(height: 3),
                  Row(children: [
                    const Icon(Icons.location_on_rounded, color: Colors.white70, size: 13),
                    const SizedBox(width: 3),
                    Text(tr('توصيل إلى الكويت', 'Deliver to Kuwait'),
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 11.5, fontWeight: FontWeight.w600)),
                    const Icon(Icons.keyboard_arrow_down_rounded, color: Colors.white70, size: 15),
                  ]),
                ])),
                if (widget.guest)
                  _iconBtn(Icons.login_rounded, () => promptLogin(context))
                else ...[
                  if (widget.canSwitchCafm) _iconBtn(Icons.apartment_rounded, () => openCafm(context)),
                  const SizedBox(width: 8),
                  _iconBtn(Icons.notifications_none_rounded, _openNotifications, dot: _unread > 0),
                ],
              ]),
              const SizedBox(height: 16),
              // ---- promo banner carousel ----
              _promoCarousel(offers),
            ]),
          ),
        ]),
      ),
      // ---- floating search + filter, overlapping the panel edge ----
      Positioned(left: 16, right: 16, bottom: -26, child: _searchBar()),
    ]);
  }

  Widget _searchBar() => Material(
        color: Colors.white,
        elevation: 8,
        shadowColor: Colors.black.withValues(alpha: 0.25),
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(6),
          child: Row(children: [
            Expanded(child: InkWell(
              onTap: () => Navigator.push(context, MaterialPageRoute(
                  builder: (_) => const C2CServiceListScreen(title: 'كل الخدمات'))),
              borderRadius: BorderRadius.circular(12),
              child: Padding(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 11),
                child: Row(children: [
                  const Icon(Icons.search_rounded, color: C2C.red, size: 22),
                  const SizedBox(width: 8),
                  Text(tr('ابحث عن خدمة منزلية…', 'Search a home service…'),
                      style: TextStyle(color: Colors.grey.shade500, fontSize: 13.5, fontWeight: FontWeight.w500)),
                ]),
              ),
            )),
            // filter pill, like the reference
            InkWell(
              onTap: () => Navigator.push(context, MaterialPageRoute(
                  builder: (_) => const C2CServiceListScreen(title: 'كل الخدمات'))),
              borderRadius: BorderRadius.circular(12),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
                decoration: BoxDecoration(
                    gradient: const LinearGradient(colors: [C2C.red, C2C.redDeep]),
                    borderRadius: BorderRadius.circular(12)),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.tune_rounded, color: Colors.white, size: 16),
                  const SizedBox(width: 5),
                  Text(tr('تصفية', 'Filter'),
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 12.5)),
                ]),
              ),
            ),
          ]),
        ),
      );

  Widget _bloom(double size, double a) => Container(
        width: size, height: size,
        decoration: BoxDecoration(color: Colors.white.withValues(alpha: a), shape: BoxShape.circle),
      );

  String _greeting() {
    // A time-aware greeting — small touch that reads as considered.
    final h = DateTime.now().hour;
    if (h < 12) return tr('صباح الخير', 'Good morning');
    if (h < 17) return tr('طاب يومك', 'Good afternoon');
    return tr('مساء الخير', 'Good evening');
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
          if (dot) Positioned(top: 4, right: 4, child: Container(width: 8, height: 8, decoration: BoxDecoration(color: const Color(0xFFFF5A4D), shape: BoxShape.circle, border: Border.all(color: C2C.red, width: 1.4)))),
        ]),
      );


  /// A deliberately distinctive band for the services section — it is the
  /// heart of the storefront, so it should not look like every other row title.
  /// A clean "Title  ·  عرض الكل" row, like the reference. Extra top space on
  /// the first one leaves room for the floating search bar to overlap.
  Widget _sectionRow(String title, VoidCallback onAll, {double top = 16}) => SliverToBoxAdapter(
        child: Padding(
          padding: EdgeInsets.fromLTRB(18, top, 18, 4),
          child: Row(children: [
            Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: C2C.ink, letterSpacing: -0.3)),
            const Spacer(),
            GestureDetector(
              onTap: onAll,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
                decoration: BoxDecoration(color: C2C.redSoft, borderRadius: BorderRadius.circular(20)),
                child: Text(tr('عرض الكل', 'View All'),
                    style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w800, fontSize: 12)),
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
    /// Categories as bold gradient cards — white title top-start, a faint icon
  /// watermark bottom-end, exactly the reference's language but in our palette.
  Widget _categoryCards(List cats) => SizedBox(
        height: 128,
        child: ListView.builder(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.fromLTRB(14, 8, 14, 4),
          itemCount: cats.length,
          itemBuilder: (_, i) {
            final c = cats[i] as Map;
            final g = C2C.gradFor(i);
            return GestureDetector(
              onTap: () => Navigator.push(context, MaterialPageRoute(
                  builder: (_) => C2CServiceListScreen(title: '${c['name']}', categoryId: c['id'] as int, gradIndex: i))),
              child: Container(
                width: 150,
                margin: const EdgeInsets.symmetric(horizontal: 5),
                decoration: BoxDecoration(
                  gradient: LinearGradient(colors: g, begin: Alignment.topRight, end: Alignment.bottomLeft),
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [BoxShadow(color: g[1].withValues(alpha: 0.4), blurRadius: 14, offset: const Offset(0, 7))],
                ),
                child: Stack(clipBehavior: Clip.antiAlias, children: [
                  // clean, transparent icon watermark bottom-start
                  Positioned(
                    bottom: -12, left: -8,
                    child: Icon(C2C.iconFor('${c['name']}'), size: 84,
                        color: Colors.white.withValues(alpha: 0.20)),
                  ),
                  // a soft sheen circle top-end
                  Positioned(top: -18, right: -14, child: _bloom(70, 0.14)),
                  // title
                  Padding(
                    padding: const EdgeInsets.all(13),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${c['name']}',
                          maxLines: 3, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14.5, height: 1.2, shadows: [Shadow(color: Colors.black26, blurRadius: 4)])),
                      const SizedBox(height: 4),
                      if ((c['service_count'] ?? 0) > 0)
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                          decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.24), borderRadius: BorderRadius.circular(20)),
                          child: Text(tr('${c['service_count']} خدمة', '${c['service_count']} services'),
                              style: const TextStyle(color: Colors.white, fontSize: 9.5, fontWeight: FontWeight.w800)),
                        ),
                    ]),
                  ),
                ]),
              ),
            );
          },
        ),
      );

  /// Fast lanes to the things a returning customer opens most.
  Widget _quickActions() {
    final items = <(IconData, String, String, List<Color>, Widget)>[
      (Icons.event_available_rounded, 'احجز خدمة', 'Book', C2C.gradFor(0), const C2CServiceListScreen(title: 'كل الخدمات')),
      (Icons.card_membership_rounded, 'باقة اشتراك', 'Plans', C2C.gradFor(4), const C2CSubscriptionsScreen()),
      (Icons.receipt_long_rounded, 'طلباتي', 'Orders', C2C.gradFor(1), const C2COrdersScreen()),
      (Icons.description_rounded, 'عرض سعر', 'Quote', C2C.gradFor(3), const C2CContractsScreen()),
    ];
    return Padding(
      padding: const EdgeInsets.fromLTRB(14, 14, 14, 0),
      child: Row(children: [
        for (final it in items) ...[
          Expanded(child: GestureDetector(
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => it.$5)),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              // A softly tinted square with a small coloured icon badge —
              // balanced proportions rather than a tall capsule.
              AspectRatio(
                aspectRatio: 1,
                child: Container(
                  decoration: BoxDecoration(
                    color: it.$4[1].withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(color: it.$4[1].withValues(alpha: 0.18)),
                  ),
                  child: Center(child: Container(
                    width: 40, height: 40,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(colors: it.$4, begin: Alignment.topRight, end: Alignment.bottomLeft),
                      borderRadius: BorderRadius.circular(13),
                      boxShadow: [BoxShadow(color: it.$4[1].withValues(alpha: 0.35), blurRadius: 7, offset: const Offset(0, 3))],
                    ),
                    child: Icon(it.$1, color: Colors.white, size: 21),
                  )),
                ),
              ),
              const SizedBox(height: 6),
              Text(tr(it.$2, it.$3), maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: C2C.ink)),
            ]),
          )),
          if (it != items.last) const SizedBox(width: 10),
        ],
      ]),
    );
  }

  Widget _videoRail() => SizedBox(
        height: 160,
        child: ListView.builder(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          itemCount: _videos.length,
          itemBuilder: (_, i) {
            final v = _videos[i] as Map;
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 5),
              child: C2CVideoThumb(
                url: '${v['video_url']}',
                poster: v['poster'] as String?,
                title: v['name'] as String?,
                subtitle: v['service'] as String?,
              ),
            );
          },
        ),
      );

    Widget _trustStrip() => Container(
        margin: const EdgeInsets.fromLTRB(16, 42, 16, 0),
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
          itemBuilder: (_, i) => _popularCard(popular[i] as Map, i),
        ),
      );

  /// A popular service. Everything on it is real: the rating and the booking
  /// count come from the service's own bookings, so nothing here is decoration
  /// pretending to be data.
  Widget _popularCard(Map s, int idx) {
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
          // ---- gradient header + clean icon watermark (matches categories) ----
          Builder(builder: (_) {
            final g = C2C.gradFor(idx);
            return ClipRRect(
              borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
              child: Container(
                height: 116, width: 204,
                decoration: BoxDecoration(gradient: LinearGradient(
                    colors: g, begin: Alignment.topRight, end: Alignment.bottomLeft)),
                child: Stack(clipBehavior: Clip.antiAlias, children: [
                  Positioned(bottom: -14, left: -10, child: Icon(
                      C2C.iconFor('${s['category'] ?? s['name']}'), size: 92,
                      color: Colors.white.withValues(alpha: 0.22))),
                  Positioned(top: -16, right: -12, child: _bloom(64, 0.14)),
                  if (rating > 0)
                    Positioned(top: 9, left: 9, child: _glassPill(
                        child: Row(mainAxisSize: MainAxisSize.min, children: [
                          const Icon(Icons.star_rounded, size: 12, color: Color(0xFFFBBF24)),
                          const SizedBox(width: 2),
                          Text(rating.toStringAsFixed(1),
                              style: const TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.w900)),
                        ]))),
                  if ((s['category'] ?? '').toString().isNotEmpty)
                    Positioned(top: 9, right: 9, child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                      decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.22),
                          borderRadius: BorderRadius.circular(20)),
                      child: Text('${s['category']}',
                          style: const TextStyle(color: Colors.white, fontSize: 9.5, fontWeight: FontWeight.w800)),
                    )),
                ]),
              ),
            );
          }),
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
                    gradient: const LinearGradient(colors: [C2C.red, C2C.redDeep]),
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
    return GestureDetector(
      onTap: () => _planDetails(s, col),
      child: Container(
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
    ),
    );
  }

  void _planDetails(Map plan, Color col) {
    final feats = (plan['features'] as List?) ?? [];
    showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (ctx) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.8, minChildSize: 0.5, maxChildSize: 0.95,
        builder: (_, scroll) => Container(
          decoration: const BoxDecoration(color: Colors.white, borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
          child: Column(children: [
            // gradient header
            Container(
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: [col, Color.lerp(col, Colors.black, 0.4)!],
                    begin: Alignment.topRight, end: Alignment.bottomLeft),
                borderRadius: const BorderRadius.vertical(top: Radius.circular(22)),
              ),
              child: SafeArea(bottom: false, child: Padding(
                padding: const EdgeInsets.fromLTRB(18, 10, 8, 16),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Align(alignment: Alignment.centerLeft,
                      child: IconButton(icon: const Icon(Icons.close_rounded, color: Colors.white),
                          onPressed: () => Navigator.pop(ctx))),
                  Row(children: [
                    Expanded(child: Text('${plan['name']}',
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 20))),
                    if (plan['popular'] == true)
                      Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
                          child: Text(tr('الأفضل قيمة', 'Best value'),
                              style: TextStyle(color: col, fontSize: 10, fontWeight: FontWeight.w900))),
                  ]),
                  const SizedBox(height: 8),
                  Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                    Text('${plan['price']}',
                        style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 34)),
                    const SizedBox(width: 4),
                    Padding(padding: const EdgeInsets.only(bottom: 6), child: Text(
                        'KWD/${plan['period'] == 'yearly' ? tr('سنة', 'yr') : (plan['period'] == 'quarterly' ? tr('ربع', 'qtr') : tr('شهر', 'mo'))}',
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12))),
                    if ((plan['save_pct'] ?? 0) > 0) ...[
                      const SizedBox(width: 8),
                      Padding(padding: const EdgeInsets.only(bottom: 6), child: Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                        decoration: BoxDecoration(color: const Color(0xFFFFC107), borderRadius: BorderRadius.circular(20)),
                        child: Text('-${plan['save_pct']}%',
                            style: const TextStyle(color: Colors.black, fontWeight: FontWeight.w900, fontSize: 11)))),
                    ],
                  ]),
                  if ((plan['visits'] ?? 0) > 0)
                    Text(tr('${plan['visits']} زيارة ضمن الباقة', '${plan['visits']} visits included'),
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.8), fontSize: 12)),
                ]),
              )),
            ),
            Expanded(child: ListView(controller: scroll, padding: const EdgeInsets.fromLTRB(18, 16, 18, 16), children: [
              Text(tr('ماذا تشمل الباقة', "What's included"),
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: C2C.navy)),
              const SizedBox(height: 10),
              for (final f in feats)
                Padding(padding: const EdgeInsets.only(bottom: 8), child: Row(children: [
                  Icon(Icons.check_circle_rounded, color: col, size: 18),
                  const SizedBox(width: 8),
                  Expanded(child: Text('$f', style: const TextStyle(fontSize: 13.5, height: 1.4))),
                ])),
              const SizedBox(height: 14),
              // cancellation terms
              Container(
                padding: const EdgeInsets.all(13),
                decoration: BoxDecoration(color: C2C.bg, borderRadius: BorderRadius.circular(14)),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: const [
                    Icon(Icons.gavel_rounded, size: 15, color: C2C.slate),
                    SizedBox(width: 6),
                    Text('شروط الإلغاء', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: C2C.ink)),
                  ]),
                  const SizedBox(height: 8),
                  for (final t in const [
                    'يمكن إلغاء الاشتراك في أي وقت من صفحة «اشتراكاتي».',
                    'الإلغاء قبل بدء أول زيارة: استرداد كامل.',
                    'بعد بدء الخدمة: تُحتسب الزيارات المنفّذة ويُسترد الباقي.',
                    'لا رسوم إلغاء خفية — الشفافية أساس تعاملنا.',
                  ])
                    Padding(padding: const EdgeInsets.only(bottom: 5), child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start, children: [
                        const Text('• ', style: TextStyle(color: C2C.slate, fontWeight: FontWeight.w900)),
                        Expanded(child: Text(t, style: TextStyle(fontSize: 11.5, height: 1.5, color: Colors.grey.shade700))),
                      ])),
                ]),
              ),
            ])),
            SafeArea(top: false, child: Padding(
              padding: const EdgeInsets.fromLTRB(18, 6, 18, 12),
              child: SizedBox(height: 52, width: double.infinity, child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(backgroundColor: col, foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
                onPressed: () { Navigator.pop(ctx); _subscribe(plan, col); },
                icon: const Icon(Icons.card_membership_rounded),
                label: Text(tr('اشترك الآن', 'Subscribe'),
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
              )),
            )),
          ]),
        ),
      ),
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
          ElevatedButton(style: ElevatedButton.styleFrom(backgroundColor: Colors.white, foregroundColor: C2C.navy, visualDensity: VisualDensity.compact, padding: const EdgeInsets.symmetric(horizontal: 12)), onPressed: () => openRfqSheet(context), child: Text(tr('عرض سعر', 'Quote'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12))),
        ]),
      );

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
