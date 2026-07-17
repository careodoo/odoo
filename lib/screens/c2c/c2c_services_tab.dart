import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'c2c_shell.dart';
import 'c2c_service.dart';

/// The Services tab — a bright, red-led home-services catalogue: a search hero,
/// the most-requested rail up top, colourful category tiles, and the full
/// service list. Built to feel like a consumer home-services app, in the CARE
/// red palette.
class C2CServicesTab extends StatefulWidget {
  const C2CServicesTab({super.key});
  @override
  State<C2CServicesTab> createState() => _C2CServicesTabState();
}

class _C2CServicesTabState extends State<C2CServicesTab> {
  Future<Map<String, dynamic>>? _home;
  Future<List<dynamic>>? _services;
  int? _catFilter;
  String _q = '';

  @override
  void initState() {
    super.initState();
    _home = context.read<AuthProvider>().api.c2cHome();
    _loadServices();
  }

  void _loadServices() => _services = context.read<AuthProvider>()
      .api
      .c2cServices(categoryId: _catFilter, q: _q);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: C2C.bg,
      body: RefreshIndicator(
        color: C2C.red,
        onRefresh: () async {
          setState(() {
            _home = context.read<AuthProvider>().api.c2cHome();
            _loadServices();
          });
        },
        child: FutureBuilder<Map<String, dynamic>>(
          future: _home,
          builder: (_, snap) {
            final d = snap.data ?? const {};
            final cats = (d['categories'] as List?) ?? const [];
            final popular = (d['popular'] as List?) ?? const [];
            return CustomScrollView(slivers: [
              _hero(),
              if (snap.connectionState == ConnectionState.waiting)
                const SliverToBoxAdapter(
                    child: Padding(padding: EdgeInsets.symmetric(vertical: 60),
                        child: Center(child: CircularProgressIndicator(color: C2C.red))))
              else ...[
                if (_q.isEmpty && _catFilter == null && popular.isNotEmpty) ...[
                  _sectionTitle(tr('🔥 الأكثر طلبًا', '🔥 Most requested'),
                      tr('خدماتنا الأكثر حجزًا هذا الشهر', 'Most-booked this month')),
                  SliverToBoxAdapter(child: _popularRail(popular)),
                ],
                if (_q.isEmpty && cats.isNotEmpty) ...[
                  _sectionTitle(tr('التصنيفات', 'Categories'), null),
                  SliverToBoxAdapter(child: _categoryStrip(cats)),
                ],
                _sectionTitle(
                    _catFilter != null
                        ? tr('خدمات التصنيف', 'Category services')
                        : (_q.isNotEmpty ? tr('نتائج البحث', 'Search results') : tr('كل الخدمات', 'All services')),
                    null),
                _serviceList(),
              ],
            ]);
          },
        ),
      ),
    );
  }

  // ---------------- hero + search ----------------
  Widget _hero() => SliverToBoxAdapter(
        child: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
                colors: [C2C.redBright, C2C.red, C2C.redDeep],
                begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.vertical(bottom: Radius.circular(26)),
          ),
          child: SafeArea(
            bottom: false,
            child: Padding(
              padding: const EdgeInsets.fromLTRB(18, 14, 18, 20),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  const Icon(Icons.home_repair_service_rounded, color: Colors.white, size: 22),
                  const SizedBox(width: 8),
                  Text(tr('خدمات عند بابك', 'Services at your door'),
                      style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
                ]),
                const SizedBox(height: 4),
                Text(tr('احجز محترفًا موثوقًا في دقائق', 'Book a trusted pro in minutes'),
                    style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 12.5)),
                const SizedBox(height: 14),
                // search
                Material(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  child: TextField(
                    onSubmitted: (v) => setState(() { _q = v.trim(); _catFilter = null; _loadServices(); }),
                    textInputAction: TextInputAction.search,
                    decoration: InputDecoration(
                      hintText: tr('ابحث عن خدمة… (تنظيف، صيانة، تكييف)', 'Search a service…'),
                      prefixIcon: const Icon(Icons.search_rounded, color: C2C.red),
                      suffixIcon: _q.isNotEmpty
                          ? IconButton(
                              icon: const Icon(Icons.clear_rounded, size: 19),
                              onPressed: () => setState(() { _q = ''; _loadServices(); }))
                          : null,
                      border: OutlineInputBorder(
                          borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
                      contentPadding: const EdgeInsets.symmetric(vertical: 4),
                    ),
                  ),
                ),
              ]),
            ),
          ),
        ),
      );

  Widget _sectionTitle(String t, String? sub) => SliverToBoxAdapter(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 18, 16, 6),
          child: Row(children: [
            Container(width: 4, height: 20,
                decoration: BoxDecoration(
                    gradient: const LinearGradient(colors: [C2C.red, C2C.redBright],
                        begin: Alignment.topCenter, end: Alignment.bottomCenter),
                    borderRadius: BorderRadius.circular(3))),
            const SizedBox(width: 9),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(t, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: C2C.navy)),
              if (sub != null)
                Text(sub, style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600, fontWeight: FontWeight.w600)),
            ])),
            if (_catFilter != null)
              GestureDetector(
                onTap: () => setState(() { _catFilter = null; _loadServices(); }),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(color: C2C.redSoft, borderRadius: BorderRadius.circular(20)),
                  child: Text(tr('كل الخدمات', 'All'),
                      style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w800, fontSize: 12)),
                ),
              ),
          ]),
        ),
      );

  // ---------------- most-requested rail ----------------
  Widget _popularRail(List popular) => SizedBox(
        height: 186,
        child: ListView.builder(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          itemCount: popular.length,
          itemBuilder: (_, i) {
            final s = popular[i] as Map;
            final tint = C2C.gradFor(i);
            return GestureDetector(
              onTap: () => Navigator.push(context, MaterialPageRoute(
                  builder: (_) => C2CServiceScreen(serviceId: s['id'] as int))),
              child: Container(
                width: 158,
                margin: const EdgeInsets.symmetric(horizontal: 5, vertical: 6),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(18),
                  boxShadow: [BoxShadow(color: tint[0].withValues(alpha: 0.18), blurRadius: 12, offset: const Offset(0, 5))],
                ),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Stack(children: [
                    ClipRRect(
                      borderRadius: const BorderRadius.vertical(top: Radius.circular(18)),
                      child: s['image'] != null
                          ? Image.network('${s['image']}', height: 92, width: 158, fit: BoxFit.cover,
                              errorBuilder: (_, __, ___) => _railFallback(s, tint))
                          : _railFallback(s, tint),
                    ),
                    Positioned(top: 8, right: 8, child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                      decoration: BoxDecoration(color: C2C.red, borderRadius: BorderRadius.circular(20)),
                      child: Text(tr('الأكثر طلبًا', 'Popular'),
                          style: const TextStyle(color: Colors.white, fontSize: 8, fontWeight: FontWeight.w900)),
                    )),
                  ]),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(10, 8, 10, 8),
                    child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                      Text('${s['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: C2C.navy)),
                      const SizedBox(height: 2),
                      Row(children: [
                        if ((s['rating'] ?? 0) > 0) ...[
                          const Icon(Icons.star_rounded, size: 12, color: Color(0xFFFBBF24)),
                          Text(' ${s['rating']}',
                              style: TextStyle(fontSize: 10, color: Colors.grey.shade600, fontWeight: FontWeight.w700)),
                          const SizedBox(width: 6),
                        ],
                        const Spacer(),
                        Text('${s['price']} ${s['currency'] ?? ''}',
                            style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w900, fontSize: 13)),
                      ]),
                    ]),
                  ),
                ]),
              ),
            );
          },
        ),
      );

  Widget _railFallback(Map s, List<Color> tint) => Container(
        height: 92, width: 158,
        decoration: BoxDecoration(gradient: LinearGradient(
            colors: tint, begin: Alignment.topRight, end: Alignment.bottomLeft)),
        alignment: Alignment.center,
        child: Icon(C2C.iconFor('${s['category'] ?? s['name']}'),
            color: Colors.white.withValues(alpha: 0.85), size: 40),
      );

  // ---------------- category strip ----------------
  Widget _categoryStrip(List cats) => SizedBox(
        height: 104,
        child: ListView.builder(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          itemCount: cats.length,
          itemBuilder: (_, i) {
            final c = cats[i] as Map;
            final tint = C2C.gradFor(i);
            final on = _catFilter == c['id'];
            return GestureDetector(
              onTap: () => setState(() {
                _catFilter = on ? null : c['id'] as int;
                _q = '';
                _loadServices();
              }),
              child: Container(
                width: 84,
                margin: const EdgeInsets.symmetric(horizontal: 5, vertical: 6),
                child: Column(children: [
                  Container(
                    width: 62, height: 62, alignment: Alignment.center,
                    decoration: BoxDecoration(
                      gradient: on
                          ? LinearGradient(colors: [tint[0], Color.lerp(tint[0], Colors.black, 0.25)!])
                          : null,
                      color: on ? null : tint[1],
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(color: tint[0].withValues(alpha: on ? 0 : 0.25)),
                      boxShadow: on
                          ? [BoxShadow(color: tint[0].withValues(alpha: 0.4), blurRadius: 10, offset: const Offset(0, 4))]
                          : null,
                    ),
                    child: Icon(C2C.iconFor('${c['name']}'),
                        color: on ? Colors.white : C2C.gradFor(i)[1], size: 27),
                  ),
                  const SizedBox(height: 5),
                  Text('${c['name']}', maxLines: 2, textAlign: TextAlign.center, overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                          fontSize: 10, height: 1.1,
                          fontWeight: on ? FontWeight.w900 : FontWeight.w700,
                          color: on ? tint[0] : C2C.navy)),
                ]),
              ),
            );
          },
        ),
      );

  // ---------------- full service list ----------------
  Widget _serviceList() => FutureBuilder<List<dynamic>>(
        future: _services,
        builder: (_, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const SliverToBoxAdapter(
                child: Padding(padding: EdgeInsets.symmetric(vertical: 40),
                    child: Center(child: CircularProgressIndicator(color: C2C.red))));
          }
          final rows = snap.data ?? const [];
          if (rows.isEmpty) {
            return SliverToBoxAdapter(child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 40),
              child: Center(child: Column(children: [
                Icon(Icons.search_off_rounded, size: 40, color: Colors.grey.shade300),
                const SizedBox(height: 8),
                Text(tr('لا خدمات مطابقة.', 'No matching services.'),
                    style: TextStyle(color: Colors.grey.shade500)),
              ])),
            ));
          }
          return SliverPadding(
            padding: const EdgeInsets.fromLTRB(14, 4, 14, 24),
            sliver: SliverList(delegate: SliverChildBuilderDelegate(
              (_, i) => _serviceCard(rows[i] as Map, i),
              childCount: rows.length,
            )),
          );
        },
      );

  Widget _serviceCard(Map s, int i) {
    final tint = C2C.gradFor(i);
    return GestureDetector(
      onTap: () => Navigator.push(context, MaterialPageRoute(
          builder: (_) => C2CServiceScreen(serviceId: s['id'] as int))),
      child: Container(
        margin: const EdgeInsets.only(bottom: 10),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.black.withValues(alpha: 0.05)),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.03), blurRadius: 6, offset: const Offset(0, 2))],
        ),
        clipBehavior: Clip.antiAlias,
        child: Row(children: [
          SizedBox(
            width: 92, height: 92,
            child: s['image'] != null
                ? Image.network('${s['image']}', fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => _cardFallback(s, tint))
                : _cardFallback(s, tint),
          ),
          Expanded(child: Padding(
            padding: const EdgeInsets.fromLTRB(11, 9, 11, 9),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
              Text('${s['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: C2C.navy)),
              if ((s['category'] ?? '').toString().isNotEmpty) ...[
                const SizedBox(height: 2),
                Text('${s['category']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
              ],
              const SizedBox(height: 6),
              Row(children: [
                if ((s['rating'] ?? 0) > 0) ...[
                  const Icon(Icons.star_rounded, size: 13, color: Color(0xFFFBBF24)),
                  Text(' ${s['rating']}',
                      style: TextStyle(fontSize: 11, color: Colors.grey.shade700, fontWeight: FontWeight.w700)),
                  if ((s['bookings'] ?? 0) > 0)
                    Text(' · ${s['bookings']} ${tr('حجز', 'booked')}',
                        style: TextStyle(fontSize: 10, color: Colors.grey.shade500)),
                  const Spacer(),
                ] else
                  const Spacer(),
                Text('${s['price']}',
                    style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w900, fontSize: 16)),
                const SizedBox(width: 2),
                Text('${s['currency'] ?? ''}',
                    style: TextStyle(color: Colors.grey.shade500, fontSize: 9, fontWeight: FontWeight.w700)),
              ]),
            ]),
          )),
          Container(
            margin: const EdgeInsets.only(left: 4, right: 8),
            padding: const EdgeInsets.all(8),
            decoration: const BoxDecoration(gradient: LinearGradient(colors: [C2C.red, C2C.redDeep]), shape: BoxShape.circle),
            child: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 13),
          ),
        ]),
      ),
    );
  }

  Widget _cardFallback(Map s, List<Color> tint) => Container(
        decoration: BoxDecoration(gradient: LinearGradient(
            colors: tint, begin: Alignment.topRight, end: Alignment.bottomLeft)),
        alignment: Alignment.center,
        child: Icon(C2C.iconFor('${s['category'] ?? s['name']}'),
            color: Colors.white.withValues(alpha: 0.85), size: 32),
      );
}
