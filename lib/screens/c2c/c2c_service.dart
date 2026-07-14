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
              backgroundColor: C2C.navy, foregroundColor: Colors.white, pinned: true, expandedHeight: 190,
              flexibleSpace: FlexibleSpaceBar(
                title: Text('${s['name']}', style: const TextStyle(fontSize: 15, fontWeight: FontWeight.w800)),
                background: s['image'] != null
                    ? Image.network('${s['image']}', fit: BoxFit.cover, color: Colors.black26, colorBlendMode: BlendMode.darken)
                    : Container(
                        decoration: const BoxDecoration(gradient: LinearGradient(colors: [C2C.navy, C2C.navy2])),
                        alignment: Alignment.center,
                        child: Text('${s['category_icon'] ?? '🧩'}', style: const TextStyle(fontSize: 70)),
                      ),
              ),
            ),
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  Row(children: [
                    _chip('${s['category']}', C2C.navy),
                    const SizedBox(width: 8),
                    if ((s['rating'] ?? 0) > 0) _chip('⭐ ${s['rating']} (${s['bookings']})', const Color(0xFFF5A623)),
                    const Spacer(),
                    Text('${s['price']} ${s['currency'] ?? ''}', style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w900, fontSize: 22)),
                  ]),
                  Text('${tr('لكل', 'per')} ${s['price_unit'] ?? ''} · ${s['duration_min']} ${tr('دقيقة', 'min')}', style: const TextStyle(color: Colors.grey, fontSize: 12)),
                  if (s['description'] != null) ...[
                    const SizedBox(height: 14),
                    Text('${s['description']}', style: const TextStyle(fontSize: 14, height: 1.5)),
                  ],
                  if (packages.isNotEmpty) ...[
                    const SizedBox(height: 18),
                    Text(tr('اختر باقة', 'Choose a package'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: C2C.navy)),
                    const SizedBox(height: 8),
                    for (final p in packages) _pkgTile(p as Map),
                  ],
                  const SizedBox(height: 90),
                ]),
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
              child: SizedBox(
                width: double.infinity, height: 52,
                child: ElevatedButton.icon(
                  style: ElevatedButton.styleFrom(backgroundColor: C2C.red, foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
                  onPressed: () => _book(snap.data!),
                  icon: const Icon(Icons.event_available_rounded),
                  label: Text(tr('احجز الآن', 'Book now'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
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
  TimeOfDay _time = const TimeOfDay(hour: 10, minute: 0);
  final _addr = TextEditingController();
  final _area = TextEditingController();
  final _phone = TextEditingController();
  String _pay = 'cash';
  bool _busy = false;

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
          Text(tr('موعد الزيارة', 'Visit date & time'), style: const TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(child: _pick(Icons.calendar_today_rounded, '${_date.year}-${_date.month.toString().padLeft(2, '0')}-${_date.day.toString().padLeft(2, '0')}', () async {
              final d = await showDatePicker(context: context, initialDate: _date, firstDate: DateTime.now(), lastDate: DateTime.now().add(const Duration(days: 60)));
              if (d != null) setState(() => _date = d);
            })),
            const SizedBox(width: 10),
            Expanded(child: _pick(Icons.access_time_rounded, _time.format(context), () async {
              final t = await showTimePicker(context: context, initialTime: _time);
              if (t != null) setState(() => _time = t);
            })),
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
          const SizedBox(height: 18),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: C2C.bg, borderRadius: BorderRadius.circular(12)),
            child: Row(children: [
              Text(tr('الإجمالي', 'Total'), style: const TextStyle(fontWeight: FontWeight.w700)),
              const Spacer(),
              Text('${widget.service['price']} ${widget.service['currency'] ?? ''}', style: const TextStyle(color: C2C.red, fontWeight: FontWeight.w900, fontSize: 18)),
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
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 14),
          decoration: BoxDecoration(color: C2C.bg, borderRadius: BorderRadius.circular(12)),
          child: Row(children: [Icon(ic, size: 18, color: C2C.navy), const SizedBox(width: 8), Flexible(child: Text(label, overflow: TextOverflow.ellipsis))]),
        ),
      );

  Widget _field(TextEditingController c, String hint, IconData ic, {bool phone = false}) => TextField(
        controller: c,
        keyboardType: phone ? TextInputType.phone : TextInputType.text,
        decoration: InputDecoration(hintText: hint, prefixIcon: Icon(ic), filled: true, fillColor: C2C.bg, border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)),
      );

  Future<void> _confirm() async {
    setState(() => _busy = true);
    final dt = DateTime(_date.year, _date.month, _date.day, _time.hour, _time.minute);
    final visit = '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')} ${dt.hour.toString().padLeft(2, '0')}:${dt.minute.toString().padLeft(2, '0')}:00';
    try {
      await context.read<AuthProvider>().api.c2cBook({
        'service_id': widget.service['id'],
        if (widget.packageId != null) 'package_id': widget.packageId,
        'visit': visit,
        'address': _addr.text, 'area': _area.text, 'phone': _phone.text,
        'payment_method': _pay,
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
