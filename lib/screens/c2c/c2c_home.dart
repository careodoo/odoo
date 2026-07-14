import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'c2c_shell.dart';
import 'c2c_service.dart';

/// CARE 2 CARE storefront home: hero, search, categories, popular services.
class C2CHomeScreen extends StatefulWidget {
  const C2CHomeScreen({super.key, this.canSwitchCafm = false, this.guest = false});
  final bool canSwitchCafm;
  final bool guest;
  @override
  State<C2CHomeScreen> createState() => _C2CHomeScreenState();
}

class _C2CHomeScreenState extends State<C2CHomeScreen> {
  Future<Map<String, dynamic>>? _home;

  @override
  void initState() {
    super.initState();
    _home = context.read<AuthProvider>().api.c2cHome();
  }

  Color _hex(String? s, Color fb) {
    if (s == null || !s.startsWith('#')) return fb;
    return Color(int.parse('FF${s.substring(1)}', radix: 16));
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: () async => setState(() => _home = context.read<AuthProvider>().api.c2cHome()),
      child: FutureBuilder<Map<String, dynamic>>(
        future: _home,
        builder: (_, snap) {
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final d = snap.data!;
          final cats = (d['categories'] as List?) ?? [];
          final popular = (d['popular'] as List?) ?? [];
          final name = context.read<AuthProvider>().profile?.name ?? '';
          final offers = (d['offers'] as List?) ?? [];
          final subs = (d['subscriptions'] as List?) ?? [];
          final reviews = (d['reviews'] as List?) ?? [];
          return CustomScrollView(slivers: [
            SliverToBoxAdapter(child: _hero(context, name)),
            SliverToBoxAdapter(child: _promoCarousel(offers)),
            SliverToBoxAdapter(child: _trustBadges()),
            if (cats.isNotEmpty) _sectionTitle(tr('خدماتنا', 'Our services')),
            SliverToBoxAdapter(child: _catGrid(cats)),
            if (popular.isNotEmpty) _sectionTitle(tr('الأكثر طلبًا', 'Most popular'), action: tr('عرض الكل', 'See all'), onAction: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const C2CServiceListScreen(title: 'كل الخدمات')))),
            SliverList.list(children: [for (final s in popular) _svcCard(s as Map)]),
            if (subs.isNotEmpty) _sectionTitle(tr('الاشتراكات الشهرية', 'Monthly subscriptions')),
            if (subs.isNotEmpty) SliverToBoxAdapter(child: _subscriptions(subs)),
            SliverToBoxAdapter(child: _contractCta()),
            _sectionTitle(tr('كيف يعمل', 'How it works')),
            SliverToBoxAdapter(child: _howItWorks()),
            SliverToBoxAdapter(child: _socialProof()),
            _sectionTitle(tr('آراء عملائنا', 'What clients say')),
            SliverToBoxAdapter(child: _testimonials(reviews)),
            const SliverToBoxAdapter(child: SizedBox(height: 28)),
          ]);
        },
      ),
    );
  }

  Widget _hero(BuildContext context, String name) => Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(colors: [C2C.navy, C2C.navy2], begin: Alignment.topLeft, end: Alignment.bottomRight),
          borderRadius: BorderRadius.vertical(bottom: Radius.circular(26)),
        ),
        padding: const EdgeInsets.fromLTRB(18, 0, 18, 20),
        child: SafeArea(
          bottom: false,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Container(
                padding: const EdgeInsets.all(7),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12)),
                child: const Text('C2', style: TextStyle(color: C2C.navy, fontWeight: FontWeight.w900, fontSize: 18)),
              ),
              const SizedBox(width: 10),
              const Text('CARE 2 CARE', style: TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18, letterSpacing: 0.5)),
              const Spacer(),
              if (widget.guest)
                TextButton.icon(
                  onPressed: () => promptLogin(context),
                  icon: const Icon(Icons.login_rounded, color: Colors.white, size: 18),
                  label: Text(tr('دخول', 'Sign in'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 12)),
                  style: TextButton.styleFrom(backgroundColor: Colors.white.withValues(alpha: 0.15), padding: const EdgeInsets.symmetric(horizontal: 10)),
                )
              else if (widget.canSwitchCafm)
                TextButton.icon(
                  onPressed: () => openCafm(context),
                  icon: const Icon(Icons.apartment_rounded, color: Colors.white, size: 18),
                  label: Text(tr('إدارة المرافق', 'CAFM'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 12)),
                  style: TextButton.styleFrom(backgroundColor: Colors.white.withValues(alpha: 0.15), padding: const EdgeInsets.symmetric(horizontal: 10)),
                ),
            ]),
            const SizedBox(height: 12),
            Text('${tr('أهلًا', 'Hello')}${name.isNotEmpty ? '، ${name.split(' ').first}' : ''} 👋',
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 22)),
            Text(tr('خدمات منزلية موثوقة عند بابك', 'Trusted home services at your door'),
                style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 13)),
            const SizedBox(height: 16),
            InkWell(
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const C2CServiceListScreen(title: 'كل الخدمات'))),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 13),
                decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
                child: Row(children: [
                  const Icon(Icons.search_rounded, color: Colors.grey),
                  const SizedBox(width: 10),
                  Text(tr('ابحث عن خدمة…', 'Search a service…'), style: const TextStyle(color: Colors.grey, fontSize: 14)),
                ]),
              ),
            ),
          ]),
        ),
      );

  Widget _sectionTitle(String t, {String? action, VoidCallback? onAction}) => SliverToBoxAdapter(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(18, 20, 18, 8),
          child: Row(children: [
            Text(t, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900, color: C2C.navy)),
            const Spacer(),
            if (action != null) TextButton(onPressed: onAction, child: Text(action, style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w700))),
          ]),
        ),
      );

  // ---- promo carousel -----------------------------------------------------
  final _promoCtrl = PageController(viewportFraction: 0.92);
  static const _promos = [
    ['🎉', 'خصم 20% على أول حجز', 'استخدم الكود WELCOME20', 0xFF0E3A5F, 0xFF17547F],
    ['🧹', 'باقات التنظيف الشهرية', 'وفّر حتى 30% باشتراك دوري', 0xFF0891B2, 0xFF0E7490],
    ['❄️', 'صيانة المكيّفات قبل الصيف', 'احجز الآن وتجنّب الأعطال', 0xFFC0392B, 0xFF8E2A20],
  ];

  Widget _promoCarousel(List offers) {
    // real offers from the API, falling back to the static promos
    final items = offers.isNotEmpty
        ? offers.map((o) => [o['icon'] ?? '🎉', o['title'] ?? '', o['subtitle'] ?? (o['code'] != null ? 'كود: ${o['code']}' : ''), _hex(o['color'] as String?, C2C.navy).value, _hex(o['color2'] as String?, C2C.navy2).value]).toList()
        : _promos;
    return Column(children: [
      const SizedBox(height: 14),
      SizedBox(
        height: 128,
        child: PageView.builder(
          controller: _promoCtrl,
          itemCount: items.length,
          itemBuilder: (_, i) {
            final p = items[i];
            return Container(
              margin: const EdgeInsets.symmetric(horizontal: 6),
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: [Color(p[3] as int), Color(p[4] as int)], begin: Alignment.topLeft, end: Alignment.bottomRight),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Row(children: [
                Expanded(
                  child: Column(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${p[1]}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 17), maxLines: 2, overflow: TextOverflow.ellipsis),
                    const SizedBox(height: 6),
                    Text('${p[2]}', style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 12.5), maxLines: 2, overflow: TextOverflow.ellipsis),
                  ]),
                ),
                Text('${p[0]}', style: const TextStyle(fontSize: 44)),
              ]),
            );
          },
        ),
      ),
    ]);
  }

  // ---- monthly subscriptions ----
  Widget _subscriptions(List subs) => SizedBox(
        height: 210,
        child: ListView.builder(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          itemCount: subs.length,
          itemBuilder: (_, i) {
            final s = subs[i] as Map;
            final col = _hex(s['color'] as String?, C2C.navy);
            final feats = (s['features'] as List?) ?? [];
            return Container(
              width: 230,
              margin: const EdgeInsets.symmetric(horizontal: 6, vertical: 6),
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: [col, Color.lerp(col, Colors.black, 0.4)!], begin: Alignment.topLeft, end: Alignment.bottomRight),
                borderRadius: BorderRadius.circular(18),
                boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 6, offset: Offset(0, 3))],
              ),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${s['name']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15), maxLines: 2, overflow: TextOverflow.ellipsis)),
                  if (s['popular'] == true) Container(padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)), child: Text(tr('الأفضل', 'Best'), style: TextStyle(color: col, fontSize: 9, fontWeight: FontWeight.w900))),
                ]),
                const SizedBox(height: 8),
                Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                  Text('${s['price']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 26)),
                  const SizedBox(width: 4),
                  Padding(padding: const EdgeInsets.only(bottom: 4), child: Text('KWD/${s['period'] == 'yearly' ? tr('سنة', 'yr') : tr('شهر', 'mo')}', style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 11))),
                  if ((s['save_pct'] ?? 0) > 0) ...[
                    const SizedBox(width: 6),
                    Padding(padding: const EdgeInsets.only(bottom: 4), child: Text('-${s['save_pct']}%', style: const TextStyle(color: Color(0xFFFFD54F), fontWeight: FontWeight.w900, fontSize: 12))),
                  ],
                ]),
                const SizedBox(height: 8),
                for (final f in feats.take(3)) Padding(padding: const EdgeInsets.only(bottom: 3), child: Row(children: [const Icon(Icons.check_circle, color: Colors.white70, size: 14), const SizedBox(width: 5), Expanded(child: Text('$f', style: const TextStyle(color: Colors.white, fontSize: 11), maxLines: 1, overflow: TextOverflow.ellipsis))])),
              ]),
            );
          },
        ),
      );

  // ---- long-term / contract CTA ----
  Widget _contractCta() => Container(
        margin: const EdgeInsets.fromLTRB(14, 20, 14, 0),
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          gradient: const LinearGradient(colors: [Color(0xFF17547F), Color(0xFF0E3A5F)]),
          borderRadius: BorderRadius.circular(18),
        ),
        child: Row(children: [
          const Text('🏢', style: TextStyle(fontSize: 38)),
          const SizedBox(width: 14),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(tr('خدمات طويلة الأمد للشركات والمنشآت', 'Long-term contracts for businesses'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14)),
            const SizedBox(height: 4),
            Text(tr('اطلب عرض سعر — ونحوّلك لعميل إدارة مرافق', 'Request a quote — become a facilities client'), style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 11.5)),
            const SizedBox(height: 10),
            ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: Colors.white, foregroundColor: C2C.navy, visualDensity: VisualDensity.compact),
              onPressed: () => _contractSheet(),
              child: Text(tr('اطلب عرض سعر', 'Request a quote'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 12)),
            ),
          ])),
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
          Text(tr('طلب تعاقد / خدمة طويلة الأمد', 'Long-term / contract request'), style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900, color: C2C.navy)),
          const SizedBox(height: 14),
          _f(title, tr('عنوان الطلب', 'Request title'), Icons.title),
          const SizedBox(height: 10),
          _f(name, tr('الاسم', 'Name'), Icons.person_outline),
          const SizedBox(height: 10),
          _f(phone, tr('الهاتف', 'Phone'), Icons.phone_outlined, phone: true),
          const SizedBox(height: 10),
          _f(desc, tr('وصف الاحتياج', 'Describe your needs'), Icons.notes, lines: 3),
          const SizedBox(height: 16),
          SizedBox(width: double.infinity, height: 50, child: ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: C2C.red, foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
            onPressed: () async {
              if (title.text.isEmpty || name.text.isEmpty || phone.text.isEmpty) return;
              try {
                await context.read<AuthProvider>().api.c2cContractCreate({'title': title.text, 'customer_name': name.text, 'phone': phone.text, 'description': desc.text, 'audience': 'company'});
                if (ctx.mounted) Navigator.pop(ctx);
                if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تم استلام طلبك، سنرسل لك عرض السعر قريبًا', 'Request received — we will send you a quote soon')), backgroundColor: const Color(0xFF16A34A)));
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
        decoration: InputDecoration(hintText: hint, prefixIcon: Icon(ic), filled: true, fillColor: C2C.bg, border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)),
      );

  // ---- trust badges -------------------------------------------------------
  Widget _trustBadges() {
    const items = [
      ['✅', 'فنّيون معتمدون', 'Vetted pros'],
      ['⏱️', 'في الموعد', 'On time'],
      ['💳', 'دفع آمن', 'Secure pay'],
      ['🛡️', 'ضمان الجودة', 'Quality guarantee'],
    ];
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 16, 12, 0),
      child: Row(children: [
        for (final b in items)
          Expanded(
            child: Column(children: [
              Text(b[0], style: const TextStyle(fontSize: 22)),
              const SizedBox(height: 4),
              Text(gLang == 'en' ? b[2] : b[1], textAlign: TextAlign.center, style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w700, color: C2C.navy)),
            ]),
          ),
      ]),
    );
  }

  // ---- how it works -------------------------------------------------------
  Widget _howItWorks() {
    const steps = [
      ['1', '🧭', 'اختر الخدمة', 'Pick a service'],
      ['2', '📅', 'حدّد الموعد', 'Set the time'],
      ['3', '😌', 'استرخِ ودعنا نعمل', 'Relax, we handle it'],
    ];
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 14),
      child: Row(children: [
        for (int i = 0; i < steps.length; i++) ...[
          Expanded(
            child: Column(children: [
              CircleAvatar(radius: 26, backgroundColor: C2C.navy.withValues(alpha: 0.08), child: Text(steps[i][1], style: const TextStyle(fontSize: 24))),
              const SizedBox(height: 6),
              Text(gLang == 'en' ? steps[i][3] : steps[i][2], textAlign: TextAlign.center, style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700)),
            ]),
          ),
          if (i < steps.length - 1) const Padding(padding: EdgeInsets.only(bottom: 20), child: Icon(Icons.arrow_forward_rounded, color: Colors.grey, size: 18)),
        ],
      ]),
    );
  }

  // ---- social proof -------------------------------------------------------
  Widget _socialProof() => Container(
        margin: const EdgeInsets.fromLTRB(14, 20, 14, 0),
        padding: const EdgeInsets.symmetric(vertical: 16),
        decoration: BoxDecoration(color: C2C.navy, borderRadius: BorderRadius.circular(18)),
        child: Row(mainAxisAlignment: MainAxisAlignment.spaceAround, children: const [
          _Metric('12K+', 'عميل سعيد', 'Happy clients'),
          _Metric('48K+', 'خدمة منجزة', 'Jobs done'),
          _Metric('4.9★', 'متوسط التقييم', 'Avg rating'),
        ]),
      );

  // ---- testimonials -------------------------------------------------------
  static const _reviews = [
    ['نورة . ك', 'خدمة تنظيف ممتازة، الفريق محترف ودقيق في المواعيد.', 5],
    ['Abdullah S.', 'Booked AC maintenance, technician arrived on time. Great app!', 5],
    ['مشاري . ع', 'سهولة في الحجز والدفع، وأسعار مناسبة. أنصح به.', 4],
  ];

  Widget _testimonials(List reviews) {
    // real featured reviews from the API, falling back to static samples
    final items = reviews.isNotEmpty
        ? reviews.map((r) => [r['author'] ?? '', r['comment'] ?? '', r['rating'] ?? 5]).toList()
        : _reviews;
    return SizedBox(
      height: 140,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        itemCount: items.length,
        itemBuilder: (_, i) {
          final r = items[i];
          final stars = r[2] as int;
          return Container(
            width: 260,
            margin: const EdgeInsets.symmetric(horizontal: 5, vertical: 6),
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 5, offset: Offset(0, 2))]),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('★' * stars + '☆' * (5 - stars), style: const TextStyle(color: Color(0xFFF5A623), fontSize: 15)),
              const SizedBox(height: 8),
              Expanded(child: Text('${r[1]}', style: const TextStyle(fontSize: 12.5, height: 1.5), maxLines: 4, overflow: TextOverflow.ellipsis)),
              const SizedBox(height: 6),
              Text('${r[0]}', style: const TextStyle(fontWeight: FontWeight.w800, color: C2C.navy, fontSize: 12)),
            ]),
          );
        },
      ),
    );
  }

  Widget _catGrid(List cats) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12),
        child: GridView.builder(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          gridDelegate: const SliverGridDelegateWithMaxCrossAxisExtent(maxCrossAxisExtent: 110, childAspectRatio: 0.82, crossAxisSpacing: 6, mainAxisSpacing: 6),
          itemCount: cats.length,
          itemBuilder: (_, i) {
            final c = cats[i] as Map;
            final col = _hex(c['color'] as String?, C2C.navy);
            return InkWell(
              onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => C2CServiceListScreen(title: '${c['name']}', categoryId: c['id'] as int))),
              borderRadius: BorderRadius.circular(16),
              child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                Container(
                  width: 58, height: 58,
                  decoration: BoxDecoration(color: col.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(18)),
                  alignment: Alignment.center,
                  child: Text('${c['icon'] ?? '🧩'}', style: const TextStyle(fontSize: 28)),
                ),
                const SizedBox(height: 6),
                Text('${c['name']}', textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700)),
              ]),
            );
          },
        ),
      );

  Widget _svcCard(Map s) => Padding(
        padding: const EdgeInsets.fromLTRB(14, 5, 14, 5),
        child: Material(
          color: Colors.white,
          borderRadius: BorderRadius.circular(18),
          elevation: 1.5,
          shadowColor: Colors.black12,
          child: InkWell(
            borderRadius: BorderRadius.circular(18),
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => C2CServiceScreen(serviceId: s['id'] as int))),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Row(children: [
                Container(
                  width: 62, height: 62,
                  decoration: BoxDecoration(color: C2C.navy.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(16)),
                  alignment: Alignment.center,
                  child: s['image'] != null
                      ? ClipRRect(borderRadius: BorderRadius.circular(16), child: Image.network('${s['image']}', width: 62, height: 62, fit: BoxFit.cover))
                      : Text('${s['category_icon'] ?? '🧩'}', style: const TextStyle(fontSize: 30)),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${s['name']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14.5)),
                    const SizedBox(height: 3),
                    Text('${s['category'] ?? ''}', style: const TextStyle(color: Colors.grey, fontSize: 12)),
                    const SizedBox(height: 6),
                    Row(children: [
                      if ((s['rating'] ?? 0) > 0) ...[
                        const Icon(Icons.star_rounded, color: Color(0xFFF5A623), size: 16),
                        Text(' ${s['rating']}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12)),
                        const SizedBox(width: 8),
                      ],
                      Text('${s['duration_min']} ${tr('د', 'min')}', style: const TextStyle(color: Colors.grey, fontSize: 11.5)),
                    ]),
                  ]),
                ),
                Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                  Text('${s['price']}', style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w900, fontSize: 17)),
                  Text('${s['currency'] ?? ''} / ${s['price_unit'] ?? ''}', style: const TextStyle(color: Colors.grey, fontSize: 10)),
                ]),
              ]),
            ),
          ),
        ),
      );
}

/// A single social-proof metric (number + label).
class _Metric extends StatelessWidget {
  const _Metric(this.value, this.ar, this.en);
  final String value, ar, en;
  @override
  Widget build(BuildContext context) => Column(mainAxisSize: MainAxisSize.min, children: [
        Text(value, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 20)),
        const SizedBox(height: 2),
        Text(gLang == 'en' ? en : ar, style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 11)),
      ]);
}
