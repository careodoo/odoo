import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'management_home.dart' show Mgmt;
import 'management_list.dart' show mgmtHex, RelationSearchSheet;

/// The «السكن» hub — occupancy stats, buildings, and a beds view where a worker
/// can be assigned to or removed from a bed.
class HousingHubScreen extends StatefulWidget {
  const HousingHubScreen({super.key, this.accent = Mgmt.red});
  final Color accent;
  @override
  State<HousingHubScreen> createState() => _HousingHubScreenState();
}

class _HousingHubScreenState extends State<HousingHubScreen> {
  late Future<Map<String, dynamic>> _hub;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => setState(() => _hub = context.read<AuthProvider>().api.managementHousingHub());

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Mgmt.bg,
      appBar: AppBar(
        backgroundColor: widget.accent, foregroundColor: Colors.white, elevation: 0,
        title: Text('🏠 ${tr('السكن', 'Housing')}'),
      ),
      body: RefreshIndicator(
        onRefresh: () async => _reload(),
        child: FutureBuilder<Map<String, dynamic>>(
          future: _hub,
          builder: (_, snap) {
            if (snap.hasError) {
              return ListView(children: [Padding(padding: const EdgeInsets.all(40),
                  child: Center(child: Text('${snap.error}', textAlign: TextAlign.center, style: const TextStyle(color: Mgmt.slate))))]);
            }
            if (!snap.hasData) return const Center(child: CircularProgressIndicator());
            final d = snap.data!;
            final stats = ((d['stats'] as List?) ?? const []).cast<Map>();
            final buildings = ((d['buildings'] as List?) ?? const []).cast<Map>();
            final canWrite = d['can_write'] == true;
            return ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
              _statsGrid(stats),
              const SizedBox(height: 6),
              Padding(padding: const EdgeInsets.fromLTRB(4, 10, 4, 8),
                  child: Row(children: [
                    Text('🛏️ ${tr('الأسرّة والإشغال', 'Beds & occupancy')}',
                        style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: Mgmt.ink)),
                    const Spacer(),
                    TextButton.icon(
                      onPressed: () => _openBeds(null, canWrite),
                      icon: const Icon(Icons.grid_view_rounded, size: 18),
                      style: TextButton.styleFrom(foregroundColor: widget.accent),
                      label: Text(tr('كل الأسرّة', 'All beds'), style: const TextStyle(fontWeight: FontWeight.w800)),
                    ),
                  ])),
              Padding(padding: const EdgeInsets.fromLTRB(4, 4, 4, 8),
                  child: Text('🏢 ${tr('المباني', 'Buildings')}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: Mgmt.ink))),
              for (final b in buildings) _buildingCard(b, canWrite),
            ]);
          },
        ),
      ),
    );
  }

  Widget _statsGrid(List<Map> stats) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(18),
            boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.05), blurRadius: 12, offset: const Offset(0, 4))]),
        child: Wrap(spacing: 10, runSpacing: 12, children: [
          for (final s in stats)
            SizedBox(
              width: (MediaQuery.of(context).size.width - 24 - 28 - 20) / 3,
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${s['icon'] ?? ''} ${gLang == 'en' ? s['en'] : s['ar']}',
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Mgmt.slate, fontSize: 10, fontWeight: FontWeight.w700)),
                const SizedBox(height: 3),
                Text('${s['value']}${s['unit'] ?? ''}',
                    style: TextStyle(fontWeight: FontWeight.w900, fontSize: 18,
                        color: mgmtHex('${s['color'] ?? ''}', widget.accent))),
              ]),
            ),
        ]),
      );

  Widget _buildingCard(Map b, bool canWrite) {
    final pct = (b['pct'] as num?)?.toDouble() ?? 0;
    final bandColor = mgmtHex('${b['band_color'] ?? ''}', widget.accent);
    return Material(
      color: Colors.white,
      borderRadius: BorderRadius.circular(14),
      child: InkWell(
        borderRadius: BorderRadius.circular(14),
        onTap: () => _openBeds(b, canWrite),
        child: Container(
          margin: const EdgeInsets.only(bottom: 8),
          padding: const EdgeInsets.all(13),
          decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              const Text('🏢 ', style: TextStyle(fontSize: 16)),
              Expanded(child: Text('${b['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Mgmt.ink))),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                decoration: BoxDecoration(color: bandColor.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: bandColor.withValues(alpha: 0.34))),
                child: Text('${pct.toStringAsFixed(0)}%', style: TextStyle(color: bandColor, fontSize: 11, fontWeight: FontWeight.w900)),
              ),
            ]),
            const SizedBox(height: 9),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(value: (pct.clamp(0, 100)) / 100.0, minHeight: 8,
                  backgroundColor: const Color(0xFFF59E0B).withValues(alpha: 0.18),
                  valueColor: AlwaysStoppedAnimation(bandColor)),
            ),
            const SizedBox(height: 8),
            Row(children: [
              Text('🛏️ ${b['beds']} ${tr('سرير', 'beds')}', style: const TextStyle(color: Mgmt.slate, fontSize: 11, fontWeight: FontWeight.w700)),
              const SizedBox(width: 12),
              Text('🧑 ${b['occupied']}', style: const TextStyle(color: Color(0xFF16A34A), fontSize: 11, fontWeight: FontWeight.w800)),
              const SizedBox(width: 12),
              Text('🟢 ${b['vacant']} ${tr('شاغر', 'free')}', style: const TextStyle(color: Color(0xFFF59E0B), fontSize: 11, fontWeight: FontWeight.w800)),
            ]),
          ]),
        ),
      ),
    );
  }

  Future<void> _openBeds(Map? building, bool canWrite) async {
    await Navigator.push(context, MaterialPageRoute(
        builder: (_) => _BedsScreen(accent: widget.accent, building: building, canWrite: canWrite)));
    _reload(); // occupancy may have changed
  }
}

/// The beds/occupancy list for a building (or all), with assign/vacate.
class _BedsScreen extends StatefulWidget {
  const _BedsScreen({required this.accent, this.building, required this.canWrite});
  final Color accent;
  final Map? building;
  final bool canWrite;
  @override
  State<_BedsScreen> createState() => _BedsScreenState();
}

class _BedsScreenState extends State<_BedsScreen> {
  late Future<Map<String, dynamic>> _f;
  final _search = TextEditingController();
  Timer? _deb;
  String _q = '';
  String? _status; // null=all / occupied / vacant
  bool _busy = false;

  int? get _hostelId => widget.building?['id'] as int?;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  @override
  void dispose() {
    _deb?.cancel();
    _search.dispose();
    super.dispose();
  }

  void _reload() => setState(() => _f = context.read<AuthProvider>().api
      .managementHousingBeds(hostel: _hostelId, status: _status, q: _q));

  void _onSearch(String v) {
    _deb?.cancel();
    _deb = Timer(const Duration(milliseconds: 400), () { _q = v.trim(); _reload(); });
  }

  Future<void> _assign(Map bed) async {
    final picked = await showModalBottomSheet<Map>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => RelationSearchSheet(model: 'hr.employee', title: tr('اختر العامل', 'Select worker'), accent: widget.accent),
    );
    if (picked == null || !mounted) return;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.managementHousingAssign(bed['id'] as int, picked['v'] as int);
      if (!mounted) return;
      _reload();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('✅ تم تسكين ${picked['l']}', '✅ Assigned ${picked['l']}')), backgroundColor: const Color(0xFF16A34A)));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _vacate(Map bed) async {
    final ok = await showDialog<bool>(context: context, builder: (c) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      title: Text(tr('إخلاء السرير', 'Vacate bed'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
      content: Text(tr('إخراج ${bed['employee']} من السرير ${bed['name']}؟', 'Remove ${bed['employee']} from bed ${bed['name']}?')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('تراجع', 'Back'))),
        ElevatedButton(style: ElevatedButton.styleFrom(backgroundColor: Mgmt.red, foregroundColor: Colors.white),
            onPressed: () => Navigator.pop(c, true), child: Text(tr('إخلاء', 'Vacate'))),
      ],
    ));
    if (ok != true || !mounted) return;
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.managementHousingVacate(bed['id'] as int);
      if (!mounted) return;
      _reload();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('✅ تم الإخلاء', '✅ Vacated')), backgroundColor: const Color(0xFF16A34A)));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: Mgmt.red));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Widget _chip(String label, bool active, VoidCallback onTap) => Padding(
        padding: const EdgeInsets.only(right: 6),
        child: ChoiceChip(
          label: Text(label, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
          selected: active,
          selectedColor: widget.accent.withValues(alpha: 0.15),
          onSelected: (_) => onTap(),
        ),
      );

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Mgmt.bg,
      appBar: AppBar(
        backgroundColor: widget.accent, foregroundColor: Colors.white, elevation: 0,
        title: Text('🛏️ ${widget.building?['name'] ?? tr('كل الأسرّة', 'All beds')}', overflow: TextOverflow.ellipsis),
      ),
      body: Stack(children: [
        Column(children: [
          Container(
            color: Colors.white,
            padding: const EdgeInsets.fromLTRB(12, 10, 12, 8),
            child: Column(children: [
              TextField(
                controller: _search, onChanged: _onSearch,
                decoration: InputDecoration(
                  hintText: tr('ابحث بالسرير/الغرفة/العامل…', 'Search bed / room / worker…'),
                  prefixIcon: const Icon(Icons.search_rounded, size: 20),
                  filled: true, fillColor: Mgmt.bg, isDense: true,
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
                ),
              ),
              const SizedBox(height: 8),
              Row(children: [
                _chip(tr('الكل', 'All'), _status == null, () { setState(() => _status = null); _reload(); }),
                _chip('🧑 ${tr('مشغولة', 'Occupied')}', _status == 'occupied', () { setState(() => _status = 'occupied'); _reload(); }),
                _chip('🟢 ${tr('شاغرة', 'Vacant')}', _status == 'vacant', () { setState(() => _status = 'vacant'); _reload(); }),
              ]),
            ]),
          ),
          Expanded(
            child: FutureBuilder<Map<String, dynamic>>(
              future: _f,
              builder: (_, snap) {
                if (snap.hasError) return Center(child: Padding(padding: const EdgeInsets.all(30), child: Text('${snap.error}', textAlign: TextAlign.center, style: const TextStyle(color: Mgmt.slate))));
                if (!snap.hasData) return const Center(child: CircularProgressIndicator());
                final beds = (snap.data!['beds'] as List?) ?? const [];
                final total = snap.data!['count'] ?? beds.length;
                if (beds.isEmpty) return Center(child: Text(tr('لا أسرّة', 'No beds'), style: const TextStyle(color: Mgmt.slate, fontWeight: FontWeight.w700)));
                return ListView.separated(
                  padding: const EdgeInsets.fromLTRB(12, 10, 12, 24),
                  itemCount: beds.length + 1,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (_, i) {
                    if (i == 0) {
                      return Padding(padding: const EdgeInsets.only(bottom: 4),
                          child: Text(tr('عرض ${beds.length} من $total', 'Showing ${beds.length} of $total'),
                              style: const TextStyle(color: Mgmt.slate, fontSize: 11.5, fontWeight: FontWeight.w700)));
                    }
                    return _bedCard(beds[i - 1] as Map);
                  },
                );
              },
            ),
          ),
        ]),
        if (_busy) const Positioned.fill(child: ColoredBox(color: Color(0x11000000), child: Center(child: CircularProgressIndicator()))),
      ]),
    );
  }

  Widget _bedCard(Map b) {
    final occupied = b['occupied'] == true;
    final photo = '${b['photo_b64'] ?? ''}';
    return Container(
      padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.black12)),
      child: Row(children: [
        // bed badge
        Container(
          width: 46, height: 46, alignment: Alignment.center,
          decoration: BoxDecoration(
              color: (occupied ? const Color(0xFF16A34A) : const Color(0xFFF59E0B)).withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(11)),
          child: Text(occupied ? '🧑' : '🛏️', style: const TextStyle(fontSize: 20)),
        ),
        const SizedBox(width: 11),
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(color: Mgmt.ink, borderRadius: BorderRadius.circular(5)),
                child: Text('${b['name']}', style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w900)),
              ),
              const SizedBox(width: 6),
              if (b['room'] != null)
                Expanded(child: Text('${b['room']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Mgmt.slate, fontSize: 11))),
            ]),
            const SizedBox(height: 4),
            if (occupied)
              Row(children: [
                if (photo.isNotEmpty) ...[
                  ClipRRect(borderRadius: BorderRadius.circular(9), child: Image.memory(base64Decode(photo), width: 18, height: 18, fit: BoxFit.cover, gaplessPlayback: true)),
                  const SizedBox(width: 5),
                ],
                Expanded(child: Text('${b['employee']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(color: Mgmt.ink, fontSize: 12, fontWeight: FontWeight.w700))),
              ])
            else
              Text(tr('شاغر', 'Vacant'), style: const TextStyle(color: Color(0xFFF59E0B), fontSize: 12, fontWeight: FontWeight.w800)),
          ]),
        ),
        if (widget.canWrite)
          occupied
              ? IconButton(onPressed: _busy ? null : () => _vacate(b), icon: const Icon(Icons.logout_rounded, color: Mgmt.red), tooltip: tr('إخلاء', 'Vacate'))
              : IconButton(onPressed: _busy ? null : () => _assign(b), icon: Icon(Icons.person_add_rounded, color: widget.accent), tooltip: tr('تسكين', 'Assign')),
      ]),
    );
  }
}
