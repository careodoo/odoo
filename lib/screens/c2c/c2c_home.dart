import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'c2c_shell.dart';
import 'c2c_service.dart';

/// CARE 2 CARE storefront home — professional, tight, image-led.
class C2CHomeScreen extends StatefulWidget {
  const C2CHomeScreen({super.key, this.canSwitchCafm = false, this.guest = false});
  final bool canSwitchCafm;
  final bool guest;
  @override
  State<C2CHomeScreen> createState() => _C2CHomeScreenState();
}

class _C2CHomeScreenState extends State<C2CHomeScreen> {
  Future<Map<String, dynamic>>? _home;
  final _promoCtrl = PageController(viewportFraction: 0.9);
  int _promoPage = 0;

  @override
  void initState() {
    super.initState();
    _home = context.read<AuthProvider>().api.c2cHome();
    _promoCtrl.addListener(() {
      final p = _promoCtrl.page?.round() ?? 0;
      if (p != _promoPage) setState(() => _promoPage = p);
    });
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

  // ============ HEADER (compact, professional) ============
  Widget _header(BuildContext context) {
    final name = context.read<AuthProvider>().profile?.name ?? '';
    final first = name.isNotEmpty ? name.split(' ').first : '';
    return SliverAppBar(
      pinned: true,
      expandedHeight: 148,
      backgroundColor: C2C.navy,
      elevation: 0,
      automaticallyImplyLeading: false,
      flexibleSpace: FlexibleSpaceBar(
        background: Container(
          decoration: const BoxDecoration(gradient: LinearGradient(colors: [Color(0xFF17547F), C2C.navy, Color(0xFF0A2A44)], begin: Alignment.topRight, end: Alignment.bottomLeft)),
          child: Stack(children: [
            Positioned(top: -30, left: -20, child: _blob(120, Colors.white.withValues(alpha: 0.06))),
            Positioned(bottom: -40, right: -10, child: _blob(140, C2C.red.withValues(alpha: 0.10))),
            Positioned(top: 30, right: 60, child: _blob(50, Colors.white.withValues(alpha: 0.05))),
            SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Container(padding: const EdgeInsets.all(6), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(9)), child: const Text('C2', style: TextStyle(color: C2C.navy, fontWeight: FontWeight.w900, fontSize: 15))),
                  const SizedBox(width: 8),
                  Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
                    const Text('CARE 2 CARE', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15, letterSpacing: 0.5, height: 1)),
                    Row(children: [
                      const Icon(Icons.location_on, color: Colors.white70, size: 12),
                      Text(tr('الكويت', 'Kuwait'), style: const TextStyle(color: Colors.white70, fontSize: 11)),
                    ]),
                  ]),
                  const Spacer(),
                  if (widget.guest)
                    _iconBtn(Icons.login_rounded, () => promptLogin(context))
                  else ...[
                    if (widget.canSwitchCafm) _iconBtn(Icons.apartment_rounded, () => openCafm(context)),
                    const SizedBox(width: 6),
                    _iconBtn(Icons.notifications_none_rounded, () {}),
                  ],
                ]),
                const SizedBox(height: 10),
                Text(first.isNotEmpty ? '${tr('مرحبًا', 'Hi')} $first 👋' : tr('خدمات منزلية عند بابك', 'Home services at your door'),
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 18)),
              ]),
            ),
          ),
          ]),
        ),
      ),
      bottom: PreferredSize(
        preferredSize: const Size.fromHeight(56),
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 12),
          child: InkWell(
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const C2CServiceListScreen(title: 'كل الخدمات'))),
            child: Container(
              height: 44,
              padding: const EdgeInsets.symmetric(horizontal: 14),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 8, offset: Offset(0, 2))]),
              child: Row(children: [
                const Icon(Icons.search_rounded, color: Colors.grey, size: 20),
                const SizedBox(width: 8),
                Text(tr('ابحث عن خدمة…', 'Search a service…'), style: const TextStyle(color: Colors.grey, fontSize: 13.5)),
              ]),
            ),
          ),
        ),
      ),
    );
  }

  Widget _blob(double size, Color color) => Container(width: size, height: size, decoration: BoxDecoration(color: color, shape: BoxShape.circle));

  Widget _iconBtn(IconData i, VoidCallback onTap) => InkWell(
        onTap: onTap, borderRadius: BorderRadius.circular(20),
        child: Container(padding: const EdgeInsets.all(7), decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(10)), child: Icon(i, color: Colors.white, size: 19)),
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

  // vibrant palette rotation for category tiles
  static const _catGrads = [
    [Color(0xFF0EA5E9), Color(0xFF0369A1)], [Color(0xFF8B5CF6), Color(0xFF6D28D9)],
    [Color(0xFF16A34A), Color(0xFF15803D)], [Color(0xFFF59E0B), Color(0xFFB45309)],
    [Color(0xFFEC4899), Color(0xFFBE185D)], [Color(0xFF0891B2), Color(0xFF0E7490)],
    [Color(0xFFEF4444), Color(0xFFB91C1C)], [Color(0xFF6366F1), Color(0xFF4338CA)],
  ];

  // ============ PROMO CAROUSEL ============
  Widget _promoCarousel(List offers) {
    final items = offers.isNotEmpty
        ? offers.map((o) => {'ic': o['icon'] ?? '🎉', 't': o['title'] ?? '', 's': o['subtitle'] ?? (o['code'] != null ? 'كود: ${o['code']}' : ''), 'c1': _hex(o['color'] as String?, C2C.navy), 'c2': _hex(o['color2'] as String?, C2C.navy2)}).toList()
        : [
            {'ic': '🎉', 't': 'خصم 20% على أول حجز', 's': 'كود: WELCOME20', 'c1': C2C.navy, 'c2': C2C.navy2},
          ];
    return Column(children: [
      const SizedBox(height: 12),
      SizedBox(
        height: 116,
        child: PageView.builder(
          controller: _promoCtrl,
          itemCount: items.length,
          itemBuilder: (_, i) {
            final p = items[i];
            return Container(
              margin: const EdgeInsets.symmetric(horizontal: 5),
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 14),
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: [p['c1'] as Color, p['c2'] as Color], begin: Alignment.topRight, end: Alignment.bottomLeft),
                borderRadius: BorderRadius.circular(18),
                boxShadow: [BoxShadow(color: (p['c1'] as Color).withValues(alpha: 0.3), blurRadius: 10, offset: const Offset(0, 4))],
              ),
              child: Row(children: [
                Expanded(child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Text('${p['t']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16), maxLines: 2, overflow: TextOverflow.ellipsis),
                  const SizedBox(height: 4),
                  Text('${p['s']}', style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 12), maxLines: 1, overflow: TextOverflow.ellipsis),
                ])),
                Text('${p['ic']}', style: const TextStyle(fontSize: 40)),
              ]),
            );
          },
        ),
      ),
      if (items.length > 1) Padding(
        padding: const EdgeInsets.only(top: 8),
        child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          for (int i = 0; i < items.length; i++)
            AnimatedContainer(duration: const Duration(milliseconds: 200), width: _promoPage == i ? 18 : 6, height: 6, margin: const EdgeInsets.symmetric(horizontal: 2), decoration: BoxDecoration(color: _promoPage == i ? C2C.navy : Colors.black26, borderRadius: BorderRadius.circular(3))),
        ]),
      ),
    ]);
  }

  // ============ CATEGORIES (tight grid) ============
  Widget _catGrid(List cats) => Padding(
        padding: const EdgeInsets.fromLTRB(12, 4, 12, 0),
        child: GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount: 4, childAspectRatio: 0.80, crossAxisSpacing: 8, mainAxisSpacing: 10),
          itemCount: cats.length,
          itemBuilder: (_, i) {
            final c = cats[i] as Map;
            final g = _catGrads[i % _catGrads.length];
            return GestureDetector(
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => C2CServiceListScreen(title: '${c['name']}', categoryId: c['id'] as int))),
              child: Column(children: [
                Container(
                  width: 58, height: 58,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(colors: g, begin: Alignment.topLeft, end: Alignment.bottomRight),
                    borderRadius: BorderRadius.circular(18),
                    boxShadow: [BoxShadow(color: g[0].withValues(alpha: 0.4), blurRadius: 8, offset: const Offset(0, 4))],
                  ),
                  alignment: Alignment.center,
                  child: Text('${c['icon'] ?? '🧩'}', style: const TextStyle(fontSize: 27)),
                ),
                const SizedBox(height: 6),
                Text('${c['name']}', textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, height: 1.12, color: Color(0xFF334155))),
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
