import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';

/// Interactive 2.5D building — floors stacked in isometric perspective, each
/// showing live occupancy; tap a floor to see who's there and their status.
class OccupancyScreen extends StatefulWidget {
  const OccupancyScreen({super.key});
  @override
  State<OccupancyScreen> createState() => _OccupancyScreenState();
}

class _OccupancyScreenState extends State<OccupancyScreen> {
  List<dynamic> _facs = [];
  int? _fid;
  Map<String, dynamic>? _data;
  bool _loading = true;
  Map? _selFloor;

  static const _status = {
    'on_task': ('ينفّذ مهمة', 'On task', Color(0xFF16A34A)),
    'available': ('متاح', 'Available', Color(0xFF2F6DF6)),
    'recent': ('نشاط حديث', 'Recent', Color(0xFFF59E0B)),
    'off': ('خارج الوردية', 'Off shift', Color(0xFF94A3B8)),
  };

  @override
  void initState() {
    super.initState();
    _boot();
  }

  Future<void> _boot() async {
    try {
      final api = context.read<AuthProvider>().api;
      _facs = await api.facilities();
      if (_facs.isNotEmpty) {
        _fid = _facs.first['id'] as int;
        await _load();
      } else {
        setState(() => _loading = false);
      }
    } catch (e) {
      setState(() => _loading = false);
    }
  }

  Future<void> _load() async {
    setState(() { _loading = true; _selFloor = null; });
    try {
      _data = await context.read<AuthProvider>().api.facilityOccupancy(_fid!);
    } catch (_) {}
    if (mounted) setState(() => _loading = false);
  }

  List<Map> _floors() {
    final out = <Map>[];
    for (final b in (_data?['buildings'] as List? ?? [])) {
      for (final f in ((b as Map)['floors'] as List)) {
        out.add({...(f as Map), 'building': b['name']});
      }
    }
    final ground = (_data?['ground'] as List? ?? []);
    if (ground.isNotEmpty) {
      out.add({'id': 0, 'name': tr('الأرضي/الخارجي', 'Ground/Outdoor'), 'workers': ground,
        'total': ground.length, 'on_task': ground.where((w) => w['status'] == 'on_task').length});
    }
    return out;
  }

  @override
  Widget build(BuildContext context) {
    final t = _data?['totals'] as Map? ?? {};
    return Scaffold(
      appBar: AppBar(title: Text(tr('المبنى ثلاثي الأبعاد', '3D building'))),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _facs.isEmpty
              ? Center(child: Text(tr('لا مرافق.', 'No facilities.')))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(padding: const EdgeInsets.all(16), children: [
                    if (_facs.length > 1)
                      DropdownButtonFormField<int>(
                        value: _fid,
                        decoration: const InputDecoration(border: OutlineInputBorder(), isDense: true),
                        items: [for (final f in _facs) DropdownMenuItem(value: f['id'] as int, child: Text('${f['name']}'))],
                        onChanged: (v) { setState(() => _fid = v); _load(); },
                      ),
                    const SizedBox(height: 12),
                    Row(children: [
                      Expanded(child: StatCard(label: tr('عاملون', 'Workers'), value: t['workers'] ?? 0, color: const Color(0xFF2F6DF6), icon: Icons.groups)),
                      const SizedBox(width: 8),
                      Expanded(child: StatCard(label: tr('على مهام', 'On task'), value: t['on_task'] ?? 0, color: const Color(0xFF16A34A), icon: Icons.build)),
                      const SizedBox(width: 8),
                      Expanded(child: StatCard(label: tr('متاحون', 'Available'), value: t['available'] ?? 0, color: const Color(0xFF0EA5E9), icon: Icons.check_circle)),
                    ]),
                    const SizedBox(height: 20),
                    _building(),
                    const SizedBox(height: 16),
                    _legend(),
                    const SizedBox(height: 16),
                    if (_selFloor != null) _workerPanel(),
                  ]),
                ),
    );
  }

  Widget _building() {
    final floors = _floors();
    if (floors.isEmpty) return Center(child: Text(tr('لا أدوار مُعرّفة', 'No floors defined'), style: TextStyle(color: Theme.of(context).colorScheme.outline)));
    return Center(
      child: Column(mainAxisSize: MainAxisSize.min, children: [for (final f in floors) _floorBlock(f)]),
    );
  }

  Widget _floorBlock(Map f) {
    final total = f['total'] as int? ?? 0;
    final onTask = f['on_task'] as int? ?? 0;
    final sel = identical(_selFloor, f);
    final base = total == 0 ? const Color(0xFFE8EEF6) : Color.lerp(const Color(0xFFDCEBFF), const Color(0xFF9AC2FF), (total / 6).clamp(0, 1))!;
    return GestureDetector(
      onTap: () => setState(() => _selFloor = f),
      child: Transform(
        alignment: Alignment.center,
        transform: Matrix4.skewX(-0.5),
        child: Container(
          width: 230,
          height: 58,
          margin: const EdgeInsets.only(bottom: 4),
          decoration: BoxDecoration(
            color: sel ? const Color(0xFF2F6DF6) : base,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(color: sel ? const Color(0xFF124E7C) : const Color(0xFFB7C7DC), width: 2),
            boxShadow: const [BoxShadow(color: Color(0x33152438), blurRadius: 10, offset: Offset(6, 8))],
          ),
          child: Transform(
            alignment: Alignment.center,
            transform: Matrix4.skewX(0.5), // un-skew content
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(children: [
                Expanded(child: Text('${f['name']}',
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontWeight: FontWeight.w800, fontSize: 13,
                        color: sel ? Colors.white : const Color(0xFF1E3A5F)))),
                if (total > 0) _badge('$total', sel ? Colors.white24 : const Color(0xFF2F6DF6), Colors.white),
                if (onTask > 0) ...[const SizedBox(width: 4), _badge('🛠️$onTask', const Color(0xFF16A34A), Colors.white)],
              ]),
            ),
          ),
        ),
      ),
    );
  }

  Widget _badge(String t, Color bg, Color fg) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(20)),
        child: Text(t, style: TextStyle(color: fg, fontSize: 11, fontWeight: FontWeight.w800)),
      );

  Widget _legend() => Wrap(spacing: 14, runSpacing: 6, alignment: WrapAlignment.center, children: [
        for (final e in _status.entries)
          Row(mainAxisSize: MainAxisSize.min, children: [
            Container(width: 10, height: 10, decoration: BoxDecoration(color: e.value.$3, shape: BoxShape.circle)),
            const SizedBox(width: 5),
            Text(tr(e.value.$1, e.value.$2), style: const TextStyle(fontSize: 12.5)),
          ]),
      ]);

  Widget _workerPanel() {
    final workers = (_selFloor!['workers'] as List? ?? []);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${tr('العاملون في', 'Workers on')} ${_selFloor!['name']}',
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
          const SizedBox(height: 8),
          if (workers.isEmpty) Text(tr('لا عاملين هنا', 'No workers here'), style: TextStyle(color: Theme.of(context).colorScheme.outline)),
          for (final w in workers) _workerRow(w as Map),
        ]),
      ),
    );
  }

  Widget _workerRow(Map w) {
    final st = _status[w['status']] ?? _status['off']!;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(children: [
        Container(width: 11, height: 11, decoration: BoxDecoration(color: st.$3, shape: BoxShape.circle)),
        const SizedBox(width: 10),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${w['employee']}', style: const TextStyle(fontWeight: FontWeight.w700)),
          if (w['task'] != null) Text('🛠️ ${w['task']}', style: TextStyle(color: Theme.of(context).colorScheme.outline, fontSize: 12)),
          if (w['location'] != null) Text('📍 ${w['location']} · ${'${w['last_seen'] ?? ''}'.replaceAll('T', ' ')}',
              style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11)),
        ])),
        Text(tr(st.$1, st.$2), style: TextStyle(color: st.$3, fontWeight: FontWeight.w700, fontSize: 12)),
      ]),
    );
  }
}
