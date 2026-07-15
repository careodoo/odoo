import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'c2c_shell.dart';

/// A filtered list of services (by category or search).
class C2CServiceListScreen extends StatefulWidget {
  const C2CServiceListScreen({super.key, required this.title, this.categoryId});
  final String title;
  final int? categoryId;
  @override
  State<C2CServiceListScreen> createState() => _C2CServiceListScreenState();
}

class _C2CServiceListScreenState extends State<C2CServiceListScreen> {
  Future<List<dynamic>>? _list;
  String _q = '';

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => setState(() => _list = context.read<AuthProvider>().api.c2cServices(categoryId: widget.categoryId, q: _q));

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: C2C.bg,
      appBar: AppBar(backgroundColor: C2C.navy, foregroundColor: Colors.white, title: Text(widget.title)),
      body: Column(children: [
        Padding(
          padding: const EdgeInsets.all(12),
          child: TextField(
            decoration: InputDecoration(
              hintText: tr('ابحث…', 'Search…'), prefixIcon: const Icon(Icons.search),
              filled: true, fillColor: Colors.white, border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
            ),
            onSubmitted: (v) { _q = v; _load(); },
          ),
        ),
        Expanded(
          child: FutureBuilder<List<dynamic>>(
            future: _list,
            builder: (_, snap) {
              if (!snap.hasData) return const Center(child: CircularProgressIndicator());
              final rows = snap.data!;
              if (rows.isEmpty) return Center(child: Text(tr('لا خدمات', 'No services')));
              return ListView(padding: const EdgeInsets.symmetric(horizontal: 12), children: [for (final s in rows) _tile(s as Map)]);
            },
          ),
        ),
      ]),
    );
  }

  Widget _tile(Map s) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Material(
          color: Colors.white, borderRadius: BorderRadius.circular(16), elevation: 1, shadowColor: Colors.black12,
          child: ListTile(
            contentPadding: const EdgeInsets.all(10),
            leading: Container(
              width: 56, height: 56,
              decoration: BoxDecoration(color: C2C.navy.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(14)),
              alignment: Alignment.center,
              child: s['image'] != null
                  ? ClipRRect(borderRadius: BorderRadius.circular(14), child: Image.network('${s['image']}', width: 56, height: 56, fit: BoxFit.cover))
                  : Text('${s['category_icon'] ?? '🧩'}', style: const TextStyle(fontSize: 26)),
            ),
            title: Text('${s['name']}', style: const TextStyle(fontWeight: FontWeight.w800)),
            subtitle: Text('${s['category'] ?? ''} · ${s['duration_min']} ${tr('د', 'min')}${(s['rating'] ?? 0) > 0 ? ' · ⭐ ${s['rating']}' : ''}', style: const TextStyle(fontSize: 12)),
            trailing: Text('${s['price']} ${s['currency'] ?? ''}', style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w900)),
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => C2CServiceScreen(serviceId: s['id'] as int))),
          ),
        ),
      );
}

/// Service detail with packages and a booking CTA.
class C2CServiceScreen extends StatefulWidget {
  const C2CServiceScreen({super.key, required this.serviceId});
  final int serviceId;
  @override
  State<C2CServiceScreen> createState() => _C2CServiceScreenState();
}

class _C2CServiceScreenState extends State<C2CServiceScreen> {
  Future<Map<String, dynamic>>? _svc;
  int? _pkgId;

  @override
  void initState() {
    super.initState();
    _svc = context.read<AuthProvider>().api.c2cService(widget.serviceId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: C2C.bg,
      body: FutureBuilder<Map<String, dynamic>>(
        future: _svc,
        builder: (_, snap) {
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final s = snap.data!;
          final packages = (s['packages'] as List?) ?? [];
          return CustomScrollView(slivers: [
            SliverAppBar(
              backgroundColor: C2C.navy, foregroundColor: Colors.white, pinned: true, expandedHeight: 230,
              flexibleSpace: FlexibleSpaceBar(
                titlePadding: const EdgeInsets.only(right: 16, bottom: 46, left: 16),
                title: Text('${s['name']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900, shadows: [Shadow(color: Colors.black54, blurRadius: 6)])),
                background: Stack(fit: StackFit.expand, children: [
                  s['image'] != null
                      ? Image.network('${s['image']}', fit: BoxFit.cover)
                      : Container(decoration: const BoxDecoration(gradient: LinearGradient(colors: [C2C.navy, C2C.navy2])), alignment: Alignment.center, child: Text('${s['category_icon'] ?? '🧩'}', style: const TextStyle(fontSize: 80))),
                  const DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: [Colors.transparent, Colors.transparent, Color(0xCC0E3A5F)]))),
                ]),
              ),
            ),
            SliverToBoxAdapter(
              child: Transform.translate(
                offset: const Offset(0, -20),
                child: Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 0),
                  child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    // floating info card
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18), boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 12, offset: Offset(0, 4))]),
                      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                        Row(children: [
                          _chip('${s['category']}', C2C.navy),
                          const SizedBox(width: 6),
                          if ((s['rating'] ?? 0) > 0) _chip('⭐ ${s['rating']} (${s['bookings']})', const Color(0xFFF5A623)),
                          const Spacer(),
                          Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
                            Text('${s['price']} ${s['currency'] ?? ''}', style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w900, fontSize: 22)),
                            Text('${tr('لكل', 'per')} ${s['price_unit'] ?? ''}', style: const TextStyle(color: Colors.grey, fontSize: 10)),
                          ]),
                        ]),
                        const SizedBox(height: 12),
                        Row(children: [
                          _pillIcon(Icons.schedule_rounded, '${s['duration_min']} ${tr('دقيقة', 'min')}', const Color(0xFF0891B2)),
                          const SizedBox(width: 8),
                          _pillIcon(Icons.verified_rounded, tr('فنّي معتمد', 'Vetted pro'), const Color(0xFF16A34A)),
                          const SizedBox(width: 8),
                          _pillIcon(Icons.shield_rounded, tr('ضمان', 'Warranty'), const Color(0xFF8B5CF6)),
                        ]),
                      ]),
                    ),
                    if (s['description'] != null) ...[
                      _secTitle(tr('عن الخدمة', 'About the service')),
                      Text('${s['description']}', style: const TextStyle(fontSize: 14, height: 1.6, color: Color(0xFF475569))),
                    ],
                    if (packages.isNotEmpty) ...[
                      _secTitle(tr('اختر باقة', 'Choose a package')),
                      for (final p in packages) _pkgTile(p as Map),
                    ],
                    _gallery((s['work_samples'] as List?) ?? []),
                    _team((s['team'] as List?) ?? []),
                    _reviews((s['reviews'] as List?) ?? [], s),
                    const SizedBox(height: 90),
                  ]),
                ),
              ),
            ),
          ]);
        },
      ),
      bottomSheet: FutureBuilder<Map<String, dynamic>>(
        future: _svc,
        builder: (_, snap) {
          if (!snap.hasData) return const SizedBox.shrink();
          return SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: GestureDetector(
                onTap: () => _book(snap.data!),
                child: Container(
                  height: 54,
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(colors: [Color(0xFFE05545), C2C.red], begin: Alignment.topLeft, end: Alignment.bottomRight),
                    borderRadius: BorderRadius.circular(15),
                    boxShadow: [BoxShadow(color: C2C.red.withValues(alpha: 0.4), blurRadius: 12, offset: const Offset(0, 4))],
                  ),
                  child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                    const Icon(Icons.event_available_rounded, color: Colors.white),
                    const SizedBox(width: 8),
                    Text('${tr('احجز الآن', 'Book now')} · ${snap.data!['price']} ${snap.data!['currency'] ?? ''}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16)),
                  ]),
                ),
              ),
            ),
          );
        },
      ),
    );
  }

  Widget _chip(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
        child: Text(t, style: TextStyle(color: c, fontWeight: FontWeight.w800, fontSize: 12)),
      );

  Widget _secTitle(String t) => Padding(
        padding: const EdgeInsets.only(top: 20, bottom: 10),
        child: Row(children: [
          Container(width: 4, height: 18, decoration: BoxDecoration(gradient: const LinearGradient(colors: [C2C.red, Color(0xFFE05545)], begin: Alignment.topCenter, end: Alignment.bottomCenter), borderRadius: BorderRadius.circular(3))),
          const SizedBox(width: 8),
          Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: C2C.navy)),
        ]),
      );

  Widget _pillIcon(IconData ic, String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 6),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(10)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [Icon(ic, size: 14, color: c), const SizedBox(width: 4), Text(t, style: TextStyle(color: c, fontWeight: FontWeight.w700, fontSize: 11))]),
      );

  // ---- before / after gallery ----
  Widget _gallery(List samples) {
    if (samples.isEmpty) return const SizedBox.shrink();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _secTitle(tr('أعمال سابقة (قبل / بعد)', 'Past work (before / after)')),
      SizedBox(
        height: 150,
        child: ListView.builder(
          scrollDirection: Axis.horizontal,
          itemCount: samples.length,
          itemBuilder: (_, i) {
            final w = samples[i] as Map;
            return GestureDetector(
              onTap: () => _showBeforeAfter(w),
              child: Container(
                width: 210,
                margin: const EdgeInsets.only(left: 10),
                decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 4)]),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(14),
                  child: Row(children: [
                    if (w['before'] != null) Expanded(child: _tagImg('${w['before']}', tr('قبل', 'Before'))),
                    if (w['after'] != null) Expanded(child: _tagImg('${w['after']}', tr('بعد', 'After'))),
                  ]),
                ),
              ),
            );
          },
        ),
      ),
    ]);
  }

  Widget _tagImg(String url, String tag) => Stack(fit: StackFit.expand, children: [
        Image.network(url, fit: BoxFit.cover),
        Positioned(left: 0, right: 0, bottom: 0, child: Container(
          color: Colors.black54, padding: const EdgeInsets.symmetric(vertical: 3),
          child: Text(tag, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w800)),
        )),
      ]);

  void _showBeforeAfter(Map w) => showDialog(context: context, builder: (_) => Dialog(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Padding(padding: const EdgeInsets.all(12), child: Text('${w['title'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w800))),
          Row(children: [
            if (w['before'] != null) Expanded(child: _tagImg('${w['before']}', tr('قبل', 'Before'))),
            if (w['after'] != null) Expanded(child: _tagImg('${w['after']}', tr('بعد', 'After'))),
          ]),
          if (w['note'] != null) Padding(padding: const EdgeInsets.all(12), child: Text('${w['note']}', style: const TextStyle(color: Colors.grey))),
        ]),
      ));

  // ---- team ----
  Widget _team(List team) {
    if (team.isEmpty) return const SizedBox.shrink();
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _secTitle(tr('فريق العمل', 'Our team')),
      SizedBox(
        height: 132,
        child: ListView.builder(
          scrollDirection: Axis.horizontal,
          itemCount: team.length,
          itemBuilder: (_, i) {
            final t = team[i] as Map;
            return Container(
              width: 110,
              margin: const EdgeInsets.only(left: 10),
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 4)]),
              child: Column(children: [
                CircleAvatar(radius: 26, backgroundColor: C2C.navy.withValues(alpha: 0.1), backgroundImage: t['image'] != null ? NetworkImage('${t['image']}') : null, child: t['image'] == null ? const Icon(Icons.person, color: C2C.navy) : null),
                const SizedBox(height: 6),
                Text('${t['name']}', maxLines: 2, textAlign: TextAlign.center, overflow: TextOverflow.ellipsis, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
                if ((t['rating'] ?? 0) > 0) Text('⭐ ${t['rating']}', style: const TextStyle(fontSize: 11, color: Color(0xFFF5A623), fontWeight: FontWeight.w800)),
              ]),
            );
          },
        ),
      ),
    ]);
  }

  // ---- reviews ----
  Widget _reviews(List reviews, Map s) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [
        _secTitle(tr('تقييمات العملاء', 'Customer reviews')),
        const Spacer(),
        if ((s['rating'] ?? 0) > 0) Padding(padding: const EdgeInsets.only(top: 14), child: Text('⭐ ${s['rating']} (${s['rating_count'] ?? reviews.length})', style: const TextStyle(fontWeight: FontWeight.w800, color: C2C.navy))),
      ]),
      if (reviews.isEmpty)
        Text(tr('لا تقييمات بعد', 'No reviews yet'), style: const TextStyle(color: Colors.grey))
      else
        for (final r in reviews) _reviewTile(r as Map),
    ]);
  }

  Widget _reviewTile(Map r) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14)),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          CircleAvatar(radius: 20, backgroundColor: C2C.navy.withValues(alpha: 0.1), backgroundImage: r['avatar'] != null ? NetworkImage('${r['avatar']}') : null, child: r['avatar'] == null ? Text('${r['author']}'.characters.first, style: const TextStyle(color: C2C.navy, fontWeight: FontWeight.w800)) : null),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Expanded(child: Text('${r['author']}', style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13))),
              Text('★' * (r['rating'] as int? ?? 0), style: const TextStyle(color: Color(0xFFF5A623), fontSize: 13)),
            ]),
            if (r['comment'] != null) Padding(padding: const EdgeInsets.only(top: 3), child: Text('${r['comment']}', style: const TextStyle(fontSize: 12.5, height: 1.4))),
          ])),
        ]),
      );

  Widget _pkgTile(Map p) {
    final sel = _pkgId == p['id'];
    return InkWell(
      onTap: () => setState(() => _pkgId = p['id'] as int),
      borderRadius: BorderRadius.circular(14),
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: Colors.white, borderRadius: BorderRadius.circular(14),
          border: Border.all(color: sel ? C2C.red : Colors.black12, width: sel ? 2 : 1),
        ),
        child: Row(children: [
          Icon(sel ? Icons.radio_button_checked : Icons.radio_button_off, color: sel ? C2C.red : Colors.grey),
          const SizedBox(width: 12),
          Expanded(
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${p['name']}', style: const TextStyle(fontWeight: FontWeight.w800)),
              if (p['description'] != null) Text('${p['description']}', style: const TextStyle(color: Colors.grey, fontSize: 12)),
            ]),
          ),
          Text('${p['price']}', style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w900, fontSize: 16)),
        ]),
      ),
    );
  }

  Future<void> _book(Map s) async {
    // guests must sign in before booking
    if (!context.read<AuthProvider>().isLoggedIn) {
      await promptLogin(context);
      if (!mounted || !context.read<AuthProvider>().isLoggedIn) return;
    }
    final ok = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => C2CBookingSheet(service: s, packageId: _pkgId),
    );
    if (ok == true && mounted) Navigator.pop(context);
  }
}

/// Booking sheet: pick date/time, address, payment → confirm.
class C2CBookingSheet extends StatefulWidget {
  const C2CBookingSheet({super.key, required this.service, this.packageId});
  final Map service;
  final int? packageId;
  @override
  State<C2CBookingSheet> createState() => _C2CBookingSheetState();
}

class _C2CBookingSheetState extends State<C2CBookingSheet> {
  DateTime _date = DateTime.now().add(const Duration(days: 1));
  String? _slot; // selected 'HH:MM'
  List<dynamic> _slots = [];
  List<int> _openWeekdays = const [0, 1, 2, 3, 4, 5, 6];
  int _horizon = 30;
  bool _loadingSlots = false;
  final _addr = TextEditingController();
  final _area = TextEditingController();
  final _phone = TextEditingController();
  final _coupon = TextEditingController();
  int _discountPct = 0;
  String? _couponMsg;
  String _pay = 'cash';
  bool _busy = false;

  double get _basePrice => (widget.service['price'] is num) ? (widget.service['price'] as num).toDouble() : 0.0;
  double get _total => _basePrice * (1 - _discountPct / 100);

  Future<void> _applyCoupon() async {
    final c = _coupon.text.trim();
    if (c.isEmpty) return;
    try {
      final r = await context.read<AuthProvider>().api.c2cCoupon(c);
      if (!mounted) return;
      setState(() {
        if (r['valid'] == true) { _discountPct = (r['discount_pct'] as int?) ?? 0; _couponMsg = '✅ ${r['title'] ?? ''} · -$_discountPct%'; }
        else { _discountPct = 0; _couponMsg = tr('كود غير صالح', 'Invalid code'); }
      });
    } catch (_) {}
  }

  @override
  void initState() {
    super.initState();
    _loadSlots();
  }

  Future<void> _loadSlots() async {
    setState(() { _loadingSlots = true; _slot = null; });
    final ds = '${_date.year}-${_date.month.toString().padLeft(2, '0')}-${_date.day.toString().padLeft(2, '0')}';
    try {
      final r = await context.read<AuthProvider>().api.c2cSlots(widget.service['id'] as int, ds);
      if (!mounted) return;
      setState(() {
        _slots = (r['slots'] as List?) ?? [];
        _openWeekdays = ((r['open_weekdays'] as List?) ?? const [0, 1, 2, 3, 4, 5, 6]).map((e) => e as int).toList();
        _horizon = (r['horizon_days'] as int?) ?? 30;
        final firstAvail = _slots.firstWhere((s) => s['available'] == true, orElse: () => null);
        _slot = firstAvail != null ? firstAvail['time'] as String : null;
        _loadingSlots = false;
      });
    } catch (_) {
      if (mounted) setState(() { _slots = []; _loadingSlots = false; });
    }
  }

  Future<void> _pickDate() async {
    final d = await showDatePicker(
      context: context, initialDate: _date, firstDate: DateTime.now(),
      lastDate: DateTime.now().add(Duration(days: _horizon)),
      selectableDayPredicate: (day) => _openWeekdays.contains(day.weekday - 1), // Mon=1→0
    );
    if (d != null) { setState(() => _date = d); _loadSlots(); }
  }

  static const _pays = [
    ['cash', '💵', 'نقدًا', 'Cash'],
    ['knet', '💳', 'كي نت', 'KNET'],
    ['card', '🏦', 'بطاقة', 'Card'],
    ['wallet', '👛', 'المحفظة', 'Wallet'],
  ];

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(18, 14, 18, MediaQuery.of(context).viewInsets.bottom + 18),
      child: SingleChildScrollView(
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Center(child: Container(width: 42, height: 4, decoration: BoxDecoration(color: Colors.black12, borderRadius: BorderRadius.circular(4)))),
          const SizedBox(height: 14),
          Text('${tr('حجز', 'Book')}: ${widget.service['name']}', style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: C2C.navy)),
          const SizedBox(height: 16),
          Text(tr('اختر اليوم', 'Choose the day'), style: const TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          _pick(Icons.calendar_today_rounded, '${_date.year}-${_date.month.toString().padLeft(2, '0')}-${_date.day.toString().padLeft(2, '0')} · ${_weekdayName(_date.weekday)}', _pickDate),
          const SizedBox(height: 14),
          Row(children: [
            Text(tr('المواعيد المتاحة', 'Available times'), style: const TextStyle(fontWeight: FontWeight.w800)),
            const Spacer(),
            if (_loadingSlots) const SizedBox(width: 14, height: 14, child: CircularProgressIndicator(strokeWidth: 2)),
          ]),
          const SizedBox(height: 8),
          if (!_loadingSlots && _slots.isEmpty)
            Container(width: double.infinity, padding: const EdgeInsets.all(14), decoration: BoxDecoration(color: C2C.bg, borderRadius: BorderRadius.circular(12)), child: Text(tr('لا مواعيد متاحة في هذا اليوم، اختر يومًا آخر.', 'No slots this day — pick another day.'), style: const TextStyle(color: Colors.grey)))
          else
            Wrap(spacing: 8, runSpacing: 8, children: [
              for (final s in _slots)
                _slotChip(s as Map),
            ]),
          const SizedBox(height: 14),
          _field(_area, tr('المنطقة', 'Area'), Icons.map_outlined),
          const SizedBox(height: 10),
          _field(_addr, tr('العنوان بالتفصيل', 'Full address'), Icons.home_outlined),
          const SizedBox(height: 10),
          _field(_phone, tr('رقم الهاتف', 'Phone'), Icons.phone_outlined, phone: true),
          const SizedBox(height: 16),
          Text(tr('طريقة الدفع', 'Payment method'), style: const TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            for (final p in _pays)
              ChoiceChip(
                label: Text('${p[1]} ${gLang == 'en' ? p[3] : p[2]}'),
                selected: _pay == p[0],
                selectedColor: C2C.navy.withValues(alpha: 0.15),
                onSelected: (_) => setState(() => _pay = p[0]),
              ),
          ]),
          const SizedBox(height: 16),
          Text(tr('كود الخصم', 'Promo code'), style: const TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: TextField(controller: _coupon, textCapitalization: TextCapitalization.characters, decoration: InputDecoration(hintText: 'WELCOME20', prefixIcon: const Icon(Icons.local_offer_outlined), filled: true, fillColor: C2C.bg, isDense: true, border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)))),
            const SizedBox(width: 8),
            SizedBox(height: 46, child: ElevatedButton(style: ElevatedButton.styleFrom(backgroundColor: C2C.navy, foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))), onPressed: _applyCoupon, child: Text(tr('تطبيق', 'Apply')))),
          ]),
          if (_couponMsg != null) Padding(padding: const EdgeInsets.only(top: 6), child: Text(_couponMsg!, style: TextStyle(color: _discountPct > 0 ? const Color(0xFF16A34A) : C2C.red, fontSize: 12, fontWeight: FontWeight.w700))),
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: C2C.bg, borderRadius: BorderRadius.circular(12)),
            child: Column(children: [
              if (_discountPct > 0) ...[
                Row(children: [Text(tr('السعر', 'Price'), style: const TextStyle(color: Colors.grey)), const Spacer(), Text('$_basePrice ${widget.service['currency'] ?? ''}', style: const TextStyle(color: Colors.grey, decoration: TextDecoration.lineThrough))]),
                const SizedBox(height: 4),
                Row(children: [Text(tr('الخصم', 'Discount'), style: const TextStyle(color: Color(0xFF16A34A))), const Spacer(), Text('-$_discountPct%', style: const TextStyle(color: Color(0xFF16A34A), fontWeight: FontWeight.w700))]),
                const Divider(height: 14),
              ],
              Row(children: [
                Text(tr('الإجمالي', 'Total'), style: const TextStyle(fontWeight: FontWeight.w800)),
                const Spacer(),
                Text('${_total.toStringAsFixed(_total.truncateToDouble() == _total ? 0 : 2)} ${widget.service['currency'] ?? ''}', style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w900, fontSize: 19)),
              ]),
            ]),
          ),
          const SizedBox(height: 14),
          SizedBox(
            width: double.infinity, height: 52,
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(backgroundColor: C2C.red, foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
              onPressed: _busy ? null : _confirm,
              child: _busy ? const SizedBox(width: 22, height: 22, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2)) : Text(tr('تأكيد الحجز', 'Confirm booking'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
            ),
          ),
        ]),
      ),
    );
  }

  Widget _pick(IconData ic, String label, VoidCallback onTap) => InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
          decoration: BoxDecoration(color: C2C.bg, borderRadius: BorderRadius.circular(12)),
          child: Row(children: [Icon(ic, size: 18, color: C2C.navy), const SizedBox(width: 8), Flexible(child: Text(label, overflow: TextOverflow.ellipsis)), const Spacer(), const Icon(Icons.expand_more, size: 18, color: Colors.grey)]),
        ),
      );

  Widget _slotChip(Map s) {
    final available = s['available'] == true;
    final sel = _slot == s['time'];
    return GestureDetector(
      onTap: available ? () => setState(() => _slot = s['time'] as String) : null,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        decoration: BoxDecoration(
          color: !available ? Colors.grey.shade200 : sel ? C2C.navy : Colors.white,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: sel ? C2C.navy : Colors.black12),
        ),
        child: Text('${s['time']}', style: TextStyle(
          fontWeight: FontWeight.w700, fontSize: 13,
          color: !available ? Colors.grey : sel ? Colors.white : C2C.navy,
          decoration: available ? null : TextDecoration.lineThrough,
        )),
      ),
    );
  }

  String _weekdayName(int wd) {
    const ar = ['الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد'];
    const en = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    return gLang == 'en' ? en[wd - 1] : ar[wd - 1];
  }

  Widget _field(TextEditingController c, String hint, IconData ic, {bool phone = false}) => TextField(
        controller: c,
        keyboardType: phone ? TextInputType.phone : TextInputType.text,
        decoration: InputDecoration(hintText: hint, prefixIcon: Icon(ic), filled: true, fillColor: C2C.bg, border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)),
      );

  Future<void> _confirm() async {
    if (_slot == null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('اختر موعدًا متاحًا أولاً', 'Pick an available time first'))));
      return;
    }
    setState(() => _busy = true);
    final parts = _slot!.split(':');
    final visit = '${_date.year}-${_date.month.toString().padLeft(2, '0')}-${_date.day.toString().padLeft(2, '0')} ${parts[0].padLeft(2, '0')}:${parts[1].padLeft(2, '0')}:00';
    try {
      await context.read<AuthProvider>().api.c2cBook({
        'service_id': widget.service['id'],
        if (widget.packageId != null) 'package_id': widget.packageId,
        'visit': visit,
        'address': _addr.text, 'area': _area.text, 'phone': _phone.text,
        'payment_method': _pay,
        if (_coupon.text.trim().isNotEmpty) 'code': _coupon.text.trim(),
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('✅ ${tr('تم تأكيد حجزك', 'Booking confirmed')}'), backgroundColor: const Color(0xFF16A34A)));
        Navigator.pop(context, true);
      }
    } catch (e) {
      if (mounted) {
        setState(() => _busy = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: C2C.red));
      }
    }
  }
}
