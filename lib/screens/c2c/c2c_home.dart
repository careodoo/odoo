import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'c2c_shell.dart';
import 'c2c_service.dart';

/// CARE 2 CARE storefront home: hero, search, categories, popular services.
class C2CHomeScreen extends StatefulWidget {
  const C2CHomeScreen({super.key, this.canSwitchCafm = false});
  final bool canSwitchCafm;
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
          return CustomScrollView(slivers: [
            SliverToBoxAdapter(child: _hero(context, name)),
            if (cats.isNotEmpty) _sectionTitle(tr('خدماتنا', 'Our services')),
            SliverToBoxAdapter(child: _catGrid(cats)),
            if (popular.isNotEmpty) _sectionTitle(tr('الأكثر طلبًا', 'Most popular')),
            SliverList.list(children: [for (final s in popular) _svcCard(s as Map)]),
            const SliverToBoxAdapter(child: SizedBox(height: 24)),
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
              if (widget.canSwitchCafm)
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

  Widget _sectionTitle(String t) => SliverToBoxAdapter(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(18, 20, 18, 8),
          child: Text(t, style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w900, color: C2C.navy)),
        ),
      );

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
