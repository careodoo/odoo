import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'work_order_detail_screen.dart';
import 'employee_profile_screen.dart';

/// Everything happening on the client's sites in one timeline: QR check-ins,
/// shift punches and work-order milestones — plus who is on site right now.
class ClientActivityScreen extends StatefulWidget {
  const ClientActivityScreen({super.key});
  @override
  State<ClientActivityScreen> createState() => _ClientActivityScreenState();
}

class _ClientActivityScreenState extends State<ClientActivityScreen> {
  Future<Map<String, dynamic>>? _future;
  String _period = 'all';
  String _kind = 'all';
  int? _employeeId;
  int? _facilityId;
  int _tab = 0;

  static const _navy = Color(0xFF0E3A5F);

  static const _periods = [
    ('all', 'الكل', 'All'), ('day', 'اليوم', 'Today'),
    ('week', 'الأسبوع', 'Week'), ('month', 'الشهر', 'Month'),
  ];

  /// Each event kind gets its own colour and icon, so the timeline can be read
  /// by shape instead of by reading every line.
  static const _kinds = <String, (String, String, IconData, Color)>{
    'scan': ('مسح موقع', 'Scan', Icons.qr_code_scanner_rounded, Color(0xFF6366F1)),
    'shift_in': ('بداية وردية', 'Clock in', Icons.login_rounded, Color(0xFF16A34A)),
    'shift_out': ('نهاية وردية', 'Clock out', Icons.logout_rounded, Color(0xFF94A3B8)),
    'wo_new': ('أمر عمل جديد', 'New order', Icons.add_task_rounded, Color(0xFF0EA5E9)),
    'wo_start': ('بدء التنفيذ', 'Started', Icons.play_circle_rounded, Color(0xFFF7A23B)),
    'wo_done': ('إنجاز', 'Done', Icons.task_alt_rounded, Color(0xFF16A34A)),
  };

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() => _future = context.read<AuthProvider>().api.clientActivity(
      period: _period, kind: _kind, employeeId: _employeeId, facilityId: _facilityId);

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(
        title: Text(tr('النشاط المباشر', 'Live activity')),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded),
            tooltip: tr('تحديث', 'Refresh'),
            onPressed: () => setState(_load),
          ),
        ],
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Center(child: Text('${snap.error}', style: TextStyle(color: cs.outline)));
          }
          final d = snap.data ?? const {};
          final feed = (d['feed'] as List?) ?? const [];
          final live = (d['live'] as List?) ?? const [];
          final st = (d['stats'] as Map?) ?? const {};
          final facets = (d['facets'] as Map?) ?? const {};
          return RefreshIndicator(
            onRefresh: () async => setState(_load),
            child: ListView(padding: const EdgeInsets.fromLTRB(12, 10, 12, 24), children: [
              _pulse(st),
              const SizedBox(height: 11),
              _filters(facets),
              const SizedBox(height: 11),
              _tabs(live.length, feed.length),
              const SizedBox(height: 10),
              if (_tab == 0) ...[
                if (live.isEmpty)
                  _empty(tr('لا حركة مسجّلة.', 'No movement recorded.'), cs)
                else
                  for (final w in live) _liveCard(w as Map),
              ] else ...[
                if (feed.isEmpty)
                  _empty(tr('لا أحداث مطابقة.', 'No matching events.'), cs)
                else
                  ..._timeline(feed),
              ],
            ]),
          );
        },
      ),
    );
  }

  Widget _empty(String t, ColorScheme cs) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 44),
        child: Center(child: Column(children: [
          Icon(Icons.sensors_off_rounded, size: 38, color: cs.outline.withValues(alpha: 0.4)),
          const SizedBox(height: 8),
          Text(t, style: TextStyle(color: cs.outline, fontSize: 12.5)),
        ])),
      );

  /// The "right now" band — what a client checks before anything else.
  Widget _pulse(Map st) {
    final byHour = (st['by_hour'] as Map?) ?? const {};
    final maxH = byHour.values.fold<int>(1, (a, v) => (v as int) > a ? v : a);
    return Container(
      padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [Color(0xFF17547F), _navy],
            begin: Alignment.topRight, end: Alignment.bottomLeft),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(children: [
        Row(children: [
          _live('${st['live_now'] ?? 0}', tr('نشط الآن', 'Live now'), const Color(0xFF4ADE80)),
          _sep(),
          _t('${st['on_task_now'] ?? 0}', tr('ينفّذ مهمة', 'On task')),
          _sep(),
          _t('${st['on_shift_now'] ?? 0}', tr('بالوردية', 'On shift')),
          _sep(),
          _t('${st['workers'] ?? 0}', tr('عامل', 'Workers')),
        ]),
        const SizedBox(height: 10),
        Wrap(spacing: 6, runSpacing: 6, children: [
          _chip(Icons.timeline_rounded, tr('${st['total'] ?? 0} حدث', '${st['total'] ?? 0} events')),
          _chip(Icons.today_rounded, tr('${st['today'] ?? 0} اليوم', '${st['today'] ?? 0} today')),
          _chip(Icons.add_task_rounded, tr('${st['wo_new'] ?? 0} أمر جديد', '${st['wo_new'] ?? 0} new')),
          _chip(Icons.task_alt_rounded, tr('${st['wo_done'] ?? 0} إنجاز', '${st['wo_done'] ?? 0} done')),
          _chip(Icons.qr_code_scanner_rounded, tr('${st['scans'] ?? 0} مسح', '${st['scans'] ?? 0} scans')),
        ]),
        // When the site is actually worked, today, hour by hour.
        if (((st['today'] ?? 0) as int) > 0) ...[
          const SizedBox(height: 12),
          SizedBox(
            height: 34,
            child: Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
              for (var h = 0; h < 24; h++)
                Expanded(child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 0.6),
                  child: Container(
                    height: 4 + 28 * (((byHour['$h'] ?? 0) as int) / maxH),
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: ((byHour['$h'] ?? 0) as int) > 0 ? 0.85 : 0.15),
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                )),
            ]),
          ),
          Padding(
            padding: const EdgeInsets.only(top: 3),
            child: Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
              for (final l in ['00', '06', '12', '18', '23'])
                Text(l, style: TextStyle(color: Colors.white.withValues(alpha: 0.4),
                    fontSize: 7.5, fontWeight: FontWeight.w700)),
            ]),
          ),
          Text(tr('نشاط اليوم حسب الساعة', "Today's activity by hour"),
              style: TextStyle(color: Colors.white.withValues(alpha: 0.5),
                  fontSize: 8.5, fontWeight: FontWeight.w700)),
        ],
      ]),
    );
  }

  Widget _live(String v, String l, Color dot) => Expanded(child: Column(children: [
        Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          Container(width: 7, height: 7, decoration: BoxDecoration(color: dot, shape: BoxShape.circle)),
          const SizedBox(width: 4),
          Text(v, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
        ]),
        Text(l, maxLines: 1, overflow: TextOverflow.ellipsis,
            style: TextStyle(color: Colors.white.withValues(alpha: 0.7), fontSize: 9, fontWeight: FontWeight.w700)),
      ]));

  Widget _t(String v, String l) => Expanded(child: Column(children: [
        Text(v, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
        Text(l, maxLines: 1, overflow: TextOverflow.ellipsis,
            style: TextStyle(color: Colors.white.withValues(alpha: 0.7), fontSize: 9, fontWeight: FontWeight.w700)),
      ]));

  Widget _sep() => Container(width: 1, height: 24, color: Colors.white.withValues(alpha: 0.15));

  Widget _chip(IconData ic, String t) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
        decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.13), borderRadius: BorderRadius.circular(8)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(ic, size: 11, color: Colors.white),
          const SizedBox(width: 4),
          Text(t, style: const TextStyle(color: Colors.white, fontSize: 9.5, fontWeight: FontWeight.w800)),
        ]),
      );

  Widget _filters(Map facets) {
    final emps = (facets['employees'] as List?) ?? const [];
    final facs = (facets['facilities'] as List?) ?? const [];
    return Column(children: [
      SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(children: [
          for (final p in _periods)
            Padding(padding: const EdgeInsets.only(left: 6), child: ChoiceChip(
              label: Text(tr(p.$2, p.$3), style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
              selected: _period == p.$1,
              onSelected: (_) => setState(() { _period = p.$1; _load(); }),
            )),
        ]),
      ),
      const SizedBox(height: 6),
      SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(children: [
          Padding(padding: const EdgeInsets.only(left: 6), child: ChoiceChip(
            label: Text(tr('كل الأحداث', 'All events'),
                style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
            selected: _kind == 'all',
            onSelected: (_) => setState(() { _kind = 'all'; _load(); }),
          )),
          for (final e in _kinds.entries)
            Padding(padding: const EdgeInsets.only(left: 6), child: ChoiceChip(
              avatar: Icon(e.value.$3, size: 13, color: _kind == e.key ? Colors.white : e.value.$4),
              label: Text(tr(e.value.$1, e.value.$2),
                  style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700)),
              selected: _kind == e.key,
              selectedColor: e.value.$4,
              labelStyle: TextStyle(color: _kind == e.key ? Colors.white : null),
              onSelected: (_) => setState(() { _kind = e.key; _load(); }),
            )),
        ]),
      ),
      if (emps.isNotEmpty || facs.isNotEmpty) ...[
        const SizedBox(height: 7),
        Row(children: [
          if (facs.isNotEmpty)
            Expanded(child: _drop(tr('المرفق', 'Facility'), _facilityId?.toString() ?? 'all',
                [('all', tr('كل المرافق', 'All sites')), for (final f in facs) ('${f['value']}', '${f['label']}')],
                (v) => setState(() { _facilityId = v == 'all' ? null : int.parse(v); _load(); }))),
          if (facs.isNotEmpty && emps.isNotEmpty) const SizedBox(width: 7),
          if (emps.isNotEmpty)
            Expanded(child: _drop(tr('العامل', 'Worker'), _employeeId?.toString() ?? 'all',
                [('all', tr('كل العاملين', 'All workers')), for (final e in emps) ('${e['value']}', '${e['label']}')],
                (v) => setState(() { _employeeId = v == 'all' ? null : int.parse(v); _load(); }))),
        ]),
      ],
    ]);
  }

  Widget _drop(String label, String value, List<(String, String)> opts, ValueChanged<String> onChanged) {
    // A stale id (e.g. a worker who dropped out of the facet list after another
    // filter narrowed it) would throw inside DropdownButton.
    final safe = opts.any((o) => o.$1 == value) ? value : opts.first.$1;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9),
      decoration: BoxDecoration(
          color: _navy.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(10),
          border: Border.all(color: _navy.withValues(alpha: 0.14))),
      child: DropdownButtonHideUnderline(child: DropdownButton<String>(
        value: safe, isDense: true, isExpanded: true,
        hint: Text(label, style: const TextStyle(fontSize: 11)),
        style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: Colors.black87),
        items: [for (final o in opts) DropdownMenuItem(value: o.$1,
            child: Text(o.$2, maxLines: 1, overflow: TextOverflow.ellipsis))],
        onChanged: (v) { if (v != null) onChanged(v); },
      )),
    );
  }

  Widget _tabs(int live, int feed) => Row(children: [
        for (final t in [
          (0, tr('بالموقع الآن', 'On site now'), live, Icons.person_pin_circle_rounded),
          (1, tr('سجل الأحداث', 'Timeline'), feed, Icons.timeline_rounded),
        ]) ...[
          Expanded(child: InkWell(
            borderRadius: BorderRadius.circular(11),
            onTap: () => setState(() => _tab = t.$1),
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 8),
              decoration: BoxDecoration(
                color: _tab == t.$1 ? _navy : _navy.withValues(alpha: 0.06),
                borderRadius: BorderRadius.circular(11),
              ),
              child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                Icon(t.$4, size: 14, color: _tab == t.$1 ? Colors.white : _navy),
                const SizedBox(width: 5),
                Text('${t.$2} (${t.$3})',
                    style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800,
                        color: _tab == t.$1 ? Colors.white : _navy)),
              ]),
            ),
          )),
          if (t.$1 == 0) const SizedBox(width: 7),
        ],
      ]);

  Widget _liveCard(Map w) {
    final onTask = w['on_task'] == true;
    final fresh = w['fresh'] == true;
    final c = onTask ? const Color(0xFF16A34A) : (fresh ? const Color(0xFF2F6DF6) : const Color(0xFF94A3B8));
    return Card(
      margin: const EdgeInsets.only(bottom: 7),
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: w['employee_id'] == null ? null : () => Navigator.push(context, MaterialPageRoute(
            builder: (_) => EmployeeProfileScreen(
                employeeId: w['employee_id'] as int, name: '${w['employee']}'))),
        child: Padding(
          padding: const EdgeInsets.all(10),
          child: Row(children: [
            Stack(children: [
              _avatar(w, r: 21),
              Positioned(bottom: 0, left: 0, child: Container(
                width: 12, height: 12,
                decoration: BoxDecoration(color: c, shape: BoxShape.circle,
                    border: Border.all(color: Theme.of(context).cardColor, width: 2)),
              )),
            ]),
            const SizedBox(width: 10),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${w['employee']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13)),
              if (w['job'] != null)
                Text('${w['job']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 9.5, color: Colors.grey.shade500)),
              const SizedBox(height: 3),
              Row(children: [
                Icon(Icons.place_rounded, size: 11, color: Colors.grey.shade500),
                const SizedBox(width: 2),
                Flexible(child: Text(
                    '${w['location'] ?? '—'}${w['building'] != null ? ' · ${w['building']}' : ''}',
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 10.5, color: Colors.grey.shade600, fontWeight: FontWeight.w600))),
              ]),
              if (onTask && w['task'] != null) ...[
                const SizedBox(height: 4),
                InkWell(
                  onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) =>
                      WorkOrderDetailScreen(id: w['task_id'] as int, title: '${w['task']}'))),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                    decoration: BoxDecoration(
                        color: const Color(0xFF16A34A).withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(7)),
                    child: Row(mainAxisSize: MainAxisSize.min, children: [
                      const Icon(Icons.play_circle_rounded, size: 10, color: Color(0xFF16A34A)),
                      const SizedBox(width: 4),
                      Flexible(child: Text('${w['task']}',
                          maxLines: 1, overflow: TextOverflow.ellipsis,
                          style: const TextStyle(
                              fontSize: 9.5, fontWeight: FontWeight.w800, color: Color(0xFF16A34A)))),
                    ]),
                  ),
                ),
              ],
            ])),
            Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 3),
                decoration: BoxDecoration(
                    color: c.withValues(alpha: 0.13), borderRadius: BorderRadius.circular(11)),
                child: Text(onTask ? tr('ينفّذ', 'On task') : (fresh ? tr('نشط', 'Live') : tr('سابق', 'Past')),
                    style: TextStyle(color: c, fontSize: 9, fontWeight: FontWeight.w900)),
              ),
              const SizedBox(height: 3),
              Text(_ago(w['last_seen']),
                  style: TextStyle(fontSize: 8.5, color: Colors.grey.shade500, fontWeight: FontWeight.w600)),
            ]),
          ]),
        ),
      ),
    );
  }

  /// The feed, grouped by day — a flat run of 150 timestamps is unreadable.
  List<Widget> _timeline(List feed) {
    final out = <Widget>[];
    String? day;
    for (final e in feed) {
      final m = e as Map;
      final d = '${m['when']}'.split(' ').first.split('T').first;
      if (d != day) {
        day = d;
        out.add(Padding(
          padding: const EdgeInsets.fromLTRB(2, 10, 2, 6),
          child: Row(children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
              decoration: BoxDecoration(
                  color: _navy.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(8)),
              child: Text(d, style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w900, color: _navy)),
            ),
            const SizedBox(width: 8),
            Expanded(child: Container(height: 1, color: Colors.grey.withValues(alpha: 0.2))),
          ]),
        ));
      }
      out.add(_eventRow(m));
    }
    return out;
  }

  Widget _eventRow(Map e) {
    final k = _kinds['${e['kind']}'] ?? (tr('حدث', 'Event'), 'Event', Icons.circle, const Color(0xFF64748B));
    final hasWo = e['wo_id'] != null;
    return InkWell(
      borderRadius: BorderRadius.circular(10),
      onTap: hasWo
          ? () => Navigator.push(context, MaterialPageRoute(builder: (_) =>
              WorkOrderDetailScreen(id: e['wo_id'] as int, title: '${e['wo_title']}')))
          : (e['employee_id'] != null
              ? () => Navigator.push(context, MaterialPageRoute(builder: (_) =>
                  EmployeeProfileScreen(employeeId: e['employee_id'] as int, name: '${e['employee']}')))
              : null),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 5, horizontal: 2),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Column(children: [
            Container(
              width: 28, height: 28, alignment: Alignment.center,
              decoration: BoxDecoration(
                  color: k.$4.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(9)),
              child: Icon(k.$3, size: 14, color: k.$4),
            ),
            Container(width: 1.5, height: 14, color: Colors.grey.withValues(alpha: 0.15)),
          ]),
          const SizedBox(width: 9),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Text(tr(k.$1, k.$2),
                  style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w900, color: k.$4)),
              const Spacer(),
              Text('${e['when']}'.length >= 16 ? '${e['when']}'.substring(11, 16) : '',
                  style: TextStyle(fontSize: 9.5, color: Colors.grey.shade500, fontWeight: FontWeight.w700)),
            ]),
            if (e['employee'] != null)
              Text('${e['employee']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700)),
            if (hasWo)
              Text('${e['wo_name']} · ${e['wo_title']}',
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 10, color: Colors.grey.shade600)),
            if (e['location'] != null || e['facility'] != null)
              Text([
                if (e['location'] != null) '📍 ${e['location']}',
                if (e['building'] != null) '${e['building']}',
                if (e['facility'] != null) '${e['facility']}',
              ].join(' · '),
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: TextStyle(fontSize: 9.5, color: Colors.grey.shade500)),
            if (e['hours'] != null)
              Text(tr('المدة: ${e['hours']} ساعة', 'Duration: ${e['hours']}h'),
                  style: const TextStyle(fontSize: 9.5, fontWeight: FontWeight.w700, color: Color(0xFF0891B2))),
          ])),
        ]),
      ),
    );
  }

  String _ago(dynamic when) {
    final s = '${when ?? ''}';
    if (s.length < 16) return '';
    // Odoo stamps are UTC without a zone marker; compare like for like.
    final t = DateTime.tryParse('${s.replaceFirst(' ', 'T')}Z');
    if (t == null) return '';
    final diff = DateTime.now().difference(t);
    if (diff.inMinutes < 1) return tr('الآن', 'now');
    if (diff.inMinutes < 60) return tr('${diff.inMinutes} د', '${diff.inMinutes}m');
    if (diff.inHours < 24) return tr('${diff.inHours} س', '${diff.inHours}h');
    return tr('${diff.inDays} يوم', '${diff.inDays}d');
  }

  Widget _avatar(Map m, {double r = 22}) {
    final photo = m['photo'] as String?;
    if (photo != null && photo.startsWith('data:image')) {
      try {
        return CircleAvatar(radius: r, backgroundImage: MemoryImage(base64Decode(photo.split(',').last)));
      } catch (_) {/* fall through to the initial */}
    }
    if (photo != null && photo.startsWith('http')) {
      return CircleAvatar(radius: r, backgroundImage: NetworkImage(photo));
    }
    return CircleAvatar(radius: r, child: Text('${m['employee'] ?? '?'}'.characters.first));
  }
}
