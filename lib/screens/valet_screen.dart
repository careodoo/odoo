import 'dart:io';

import 'package:flutter/material.dart';
import 'package:geolocator/geolocator.dart';
import 'package:image_picker/image_picker.dart';
import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'searchable_picker.dart';
import 'pdf_report_screen.dart';

const _navy = Color(0xFF0E3A5F);
const _gold = Color(0xFFB45309);

const _stateColors = {
  'received': Color(0xFF0891B2), 'parked': Color(0xFF16A34A),
  'requested': Color(0xFFF59E0B), 'delivered': Color(0xFF64748B),
  'cancelled': Color(0xFF94A3B8),
};

/// خدمة صف السيارات — the attendant's kerbside console: take a car in, park it
/// in a numbered bay, answer retrieval requests against the SLA clock, hand it
/// back with the charge, and close the shift with its takings.
class ValetScreen extends StatefulWidget {
  const ValetScreen({super.key});
  @override
  State<ValetScreen> createState() => _ValetScreenState();
}

class _ValetScreenState extends State<ValetScreen>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulse = AnimationController(
      vsync: this, duration: const Duration(milliseconds: 900))
    ..repeat(reverse: true);
  Map<String, dynamic>? _d;
  String _filter = 'live';
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.valetBoard();
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack('$e');
    }
  }

  void _snack(String m, {Color? c}) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: c ?? _gold, behavior: SnackBarBehavior.floating));

  /// Who is on the floor right now and how many cars each is holding.
  Future<void> _driversSheet() async {
    final facId = (_d?['facility_id'] as num?)?.toInt();
    showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => DraggableScrollableSheet(
        expand: false, initialChildSize: 0.6, maxChildSize: 0.92, minChildSize: 0.4,
        builder: (c, ctrl) => FutureBuilder<List<dynamic>>(
          future: context.read<AuthProvider>().api.valetDrivers(facilityId: facId),
          builder: (c, snap) {
            if (snap.connectionState == ConnectionState.waiting) {
              return const Padding(padding: EdgeInsets.all(40),
                  child: Center(child: CircularProgressIndicator(color: _gold)));
            }
            final drivers = (snap.data ?? const []).cast<Map>();
            return ListView(controller: ctrl, padding: const EdgeInsets.fromLTRB(16, 14, 16, 24), children: [
              Center(child: Container(width: 40, height: 4, decoration: BoxDecoration(
                  color: Colors.black12, borderRadius: BorderRadius.circular(3)))),
              const SizedBox(height: 14),
              Row(children: [
                const Icon(Icons.groups_rounded, color: _gold),
                const SizedBox(width: 8),
                Text(tr('السائقون على الأرض', 'Drivers on the floor'),
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 17)),
                const Spacer(),
                Text('${drivers.where((d) => d['on_shift'] == true).length}/${drivers.length}',
                    style: const TextStyle(fontWeight: FontWeight.w900, color: _gold)),
              ]),
              const SizedBox(height: 12),
              if (drivers.isEmpty)
                Padding(padding: const EdgeInsets.all(30),
                    child: Center(child: Text(tr('لا سائقين مسجّلين', 'No drivers registered'),
                        style: const TextStyle(color: Colors.black54)))),
              for (final d in drivers) _driverTile(d),
            ]);
          },
        ),
      ),
    );
  }

  Widget _driverTile(Map d) {
    final on = d['on_shift'] == true;
    final open = (d['open'] as num?)?.toInt() ?? 0;
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: on ? const Color(0xFFF0FBF3) : const Color(0xFFF6F7F9),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: on ? const Color(0xFF16A34A) : const Color(0xFFE3E7EE)),
      ),
      child: Row(children: [
        CircleAvatar(radius: 22, backgroundColor: on ? const Color(0xFF16A34A) : Colors.black26,
            child: Text('${d['name'] ?? tr('؟', '?')}'.characters.take(1).toString().toUpperCase(),
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900))),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${d['name'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14)),
          const SizedBox(height: 2),
          Text([
            on ? tr('على الوردية', 'On shift') : tr('خارج الوردية', 'Off shift'),
            if (d['facility'] != null) '${d['facility']}',
            if ((d['zones'] as List?)?.isNotEmpty ?? false) (d['zones'] as List).join(tr('، ', ', ')),
          ].join(' · '), style: const TextStyle(fontSize: 11.5, color: Colors.black54)),
        ])),
        Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
          _dstat('${open}', tr('بحوزته', 'Holding'), open > 0 ? const Color(0xFFB45309) : Colors.black45),
          Text('${tr('اليوم', 'today')} ${d['today'] ?? 0} · ${d['avg_park'] ?? 0}${tr('د', 'm')}',
              style: const TextStyle(fontSize: 10.5, color: Colors.black45)),
        ]),
      ]),
    );
  }

  Widget _dstat(String v, String l, Color c) => Row(mainAxisSize: MainAxisSize.min, children: [
        Text(v, style: TextStyle(fontWeight: FontWeight.w900, color: c, fontSize: 15)),
        const SizedBox(width: 4),
        Text(l, style: const TextStyle(fontSize: 10.5, color: Colors.black45)),
      ]);

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final stats = (d?['stats'] as Map?) ?? const {};
    var tickets = ((d?['tickets'] as List?) ?? const []).cast<Map>();
    if (_filter != 'live') tickets = tickets.where((t) => t['state'] == _filter).toList();
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      appBar: AppBar(
        backgroundColor: _gold, foregroundColor: Colors.white,
        title: Text(tr('صف السيارات', 'Valet'), style: const TextStyle(fontWeight: FontWeight.w900)),
        actions: [
          IconButton(
            icon: const Icon(Icons.groups_rounded),
            tooltip: tr('السائقون', 'Drivers'),
            onPressed: _driversSheet,
          ),
          IconButton(
            icon: const Icon(Icons.badge_rounded),
            tooltip: tr('الوردية', 'Shift'),
            onPressed: () => _shiftSheet(d),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        // Green, not the header gold. The action that STARTS something should
        // not wear the same colour as the bar it sits against — it read as
        // part of the chrome instead of a button.
        backgroundColor: const Color(0xFF16A34A),
        onPressed: () => _newTicket(d),
        icon: const Icon(Icons.directions_car_rounded),
        label: Text(tr('استلام مركبة', 'Take a car'), style: const TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: d == null
          ? const Center(child: CircularProgressIndicator(color: _gold))
          : RefreshIndicator(
              color: _gold,
              onRefresh: _load,
              child: ListView(padding: EdgeInsets.zero, children: [
                // The header first (the professional gradient board), THEN the
                // "cars wanted now" banner tucked just under it — visible but no
                // longer crashing into the app bar.
                _header(stats, d),
                _wantedBanner(((d['tickets'] as List?) ?? const []).cast<Map>()),
                _zones(((d['zones'] as List?) ?? const []).cast<Map>()),
                _chips(stats),
                if (tickets.isEmpty)
                  _empty(tr('لا مركبات في هذه الحالة', 'Nothing in this state'))
                else
                  for (final t in tickets) _card(t, d),
                const SizedBox(height: 90),
              ]),
            ),
    );
  }

  Widget _header(Map s, Map d) {
    final shift = d['shift'] as Map?;
    return CustomPaint(
      painter: const BrandPattern(opacity: 0.07),
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
        decoration: const BoxDecoration(
          gradient: LinearGradient(colors: [_gold, Color(0xFF78350F), _navy], begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.vertical(bottom: Radius.circular(22)),
        ),
        child: Column(children: [
          Row(children: [
            _hs(Icons.download_rounded, '${s['received'] ?? 0}', tr('مُستلَمة', 'In')),
            _hd(),
            _hs(Icons.local_parking_rounded, '${s['parked'] ?? 0}', tr('مركونة', 'Parked')),
            _hd(),
            _hs(Icons.notifications_active_rounded, '${s['requested'] ?? 0}', tr('مطلوبة', 'Requested')),
            _hd(),
            _hs(Icons.check_circle_rounded, '${s['delivered_today'] ?? 0}', tr('سُلّمت اليوم', 'Out today')),
          ]),
          if (shift != null) ...[
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
              decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(13)),
              child: Row(children: [
                const Icon(Icons.badge_rounded, color: Colors.white, size: 15),
                const SizedBox(width: 7),
                Expanded(child: Text('${shift['name']} · ${shift['tickets']} ${tr('تذكرة', 'tickets')}',
                    style: const TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.w800))),
                Text('${tr('نقد', 'cash')} ${shift['cash_due']}',
                    style: const TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.w900)),
              ]),
            ),
          ],
        ]),
      ),
    );
  }

  Widget _hs(IconData ic, String v, String l) => Expanded(child: Column(children: [
        Icon(ic, color: Colors.white, size: 16),
        const SizedBox(height: 3),
        Text(v, style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
        Text(l, textAlign: TextAlign.center, style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 9, fontWeight: FontWeight.w600)),
      ]));

  Widget _hd() => Container(width: 1, height: 32, color: Colors.white.withValues(alpha: 0.2));

  /// Occupancy per zone — how much room is left on the ground.
  Widget _zones(List<Map> zones) {
    if (zones.isEmpty) return const SizedBox.shrink();
    return SizedBox(
      height: 84,
      child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.fromLTRB(12, 12, 12, 4), children: [
        for (final z in zones)
          Container(
            width: 178,
            margin: const EdgeInsets.only(left: 8),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.grey.shade200)),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [
                const Icon(Icons.local_parking_rounded, size: 15, color: _gold),
                const SizedBox(width: 5),
                Expanded(child: Text('${z['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 11.5, color: _navy))),
              ]),
              const SizedBox(height: 6),
              ClipRRect(
                borderRadius: BorderRadius.circular(5),
                child: LinearProgressIndicator(
                  value: (numOf(z['occupancy'], 0)) / 100.0, minHeight: 6,
                  backgroundColor: Colors.grey.shade200,
                  valueColor: AlwaysStoppedAnimation(
                      (numOf(z['occupancy'], 0)) > 85 ? const Color(0xFFE11D48) : const Color(0xFF16A34A)),
                ),
              ),
              const SizedBox(height: 5),
              Text('${z['free']} ${tr('متاح', 'free')} · ${z['occupied']}/${z['capacity']}',
                  style: TextStyle(fontSize: 10.5, color: Colors.grey.shade600, fontWeight: FontWeight.w700)),
            ]),
          ),
      ]),
    );
  }

  Widget _chips(Map s) => SizedBox(
        height: 42,
        child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 8), children: [
          for (final f in [
            ('live', tr('الكل الجاري', 'All live'), null),
            ('requested', tr('مطلوبة', 'Requested'), '${s['requested'] ?? 0}'),
            ('parked', tr('مركونة', 'Parked'), '${s['parked'] ?? 0}'),
            ('received', tr('بانتظار الصف', 'To park'), '${s['received'] ?? 0}'),
          ])
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
              child: ChoiceChip(
                selected: _filter == f.$1,
                label: Text(f.$3 == null ? f.$2 : '${f.$2} (${f.$3})',
                    style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: _filter == f.$1 ? Colors.white : _navy)),
                selectedColor: _gold, backgroundColor: Colors.white,
                side: BorderSide(color: _filter == f.$1 ? _gold : Colors.grey.shade300),
                onSelected: (_) => setState(() => _filter = f.$1),
              ),
            ),
        ]),
      );


  /// Cars that have been asked for, pinned to the top and pulsing.
  ///
  /// A retrieval request buried in a list of thirty parked cars is a guest
  /// standing at the door while nobody moves. This is the one thing on the
  /// screen that should be impossible to miss.
  Widget _wantedBanner(List<Map> tickets) {
    final wanted = tickets.where((t) => '${t['state']}' == 'requested').toList();
    if (wanted.isEmpty) return const SizedBox.shrink();
    return AnimatedBuilder(
      animation: _pulse,
      builder: (_, child) {
        final t = Curves.easeInOut.transform(_pulse.value);
        return Container(
          margin: const EdgeInsets.fromLTRB(12, 8, 12, 4),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(12),
            // A soft edge rather than a glowing slab: it has to be noticed,
            // not to dominate a screen the crew works in all day.
            boxShadow: [
              BoxShadow(
                color: const Color(0xFFE11D48).withValues(alpha: 0.12 + 0.16 * t),
                blurRadius: 8 + 6 * t,
              ),
            ],
          ),
          child: child,
        );
      },
      child: Container(
        padding: const EdgeInsets.fromLTRB(12, 10, 10, 10),
        decoration: BoxDecoration(
          gradient: const LinearGradient(
              colors: [Color(0xFFE11D48), Color(0xFF9F1239)],
              begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.notifications_active_rounded,
                color: Colors.white, size: 20),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                  '${tr('مركبات مطلوبة الآن', 'Cars requested now')} · ${wanted.length}',
                  style: const TextStyle(
                      color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14.5)),
            ),
          ]),
          const SizedBox(height: 9),
          for (final t in wanted.take(2))
            Padding(
              padding: const EdgeInsets.only(bottom: 7),
              child: Row(children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
                  decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(8)),
                  child: Text('${t['plate'] ?? ''}',
                      style: const TextStyle(
                          color: Colors.white,
                          fontWeight: FontWeight.w900,
                          fontSize: 13)),
                ),
                const SizedBox(width: 9),
                Expanded(
                  child: Text(
                      '${t['zone'] ?? t['spot'] ?? ''} · ${tr('منذ', 'for')} '
                      '${intOf(t['retrieval_minutes'])} ${tr('د', 'm')}',
                      maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.92), fontSize: 11.5)),
                ),
                const SizedBox(width: 8),
                FilledButton(
                  style: FilledButton.styleFrom(
                    backgroundColor: Colors.white,
                    foregroundColor: const Color(0xFFB91C3C),
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 0),
                    minimumSize: const Size(0, 34),
                    shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10)),
                  ),
                  onPressed: _busy ? null : () => _act(t, 'deliver'),
                  child: Text(tr('تسليم', 'Deliver'),
                      style: const TextStyle(
                          fontWeight: FontWeight.w900, fontSize: 12.5)),
                ),
              ]),
            ),
          if (wanted.length > 2)
            Text('+${wanted.length - 2} ${tr('أخرى', 'more')}',
                style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.85), fontSize: 11.5)),
        ]),
      ),
    );
  }

  Widget _card(Map t, Map d) {
    final st = '${t['state']}';
    final c = _stateColors[st] ?? Colors.grey;
    final late = t['is_late'] == true;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Material(
        color: Colors.white, borderRadius: BorderRadius.circular(15),
        child: Container(
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(15),
            border: Border.all(color: st == 'requested' ? const Color(0xFFF59E0B).withValues(alpha: 0.5) : Colors.grey.shade200),
          ),
          padding: const EdgeInsets.all(12),
          child: Column(children: [
            Row(children: [
              Container(width: 5, height: 48, decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(4))),
              const SizedBox(width: 11),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${t['plate']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15, color: _navy))),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                    decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20), border: Border.all(color: c.withValues(alpha: 0.4))),
                    child: Text('${t['state_label']}', style: TextStyle(color: c, fontSize: 10, fontWeight: FontWeight.w900)),
                  ),
                ]),
                const SizedBox(height: 3),
                Text([t['car'], t['guest'], t['name']].where((x) => x != null).join(' · '),
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600)),
                const SizedBox(height: 6),
                Wrap(spacing: 6, runSpacing: 5, children: [
                  if (t['spot'] != null) _tag('🅿️ ${t['spot']}', const Color(0xFF16A34A)),
                  if (t['key_tag'] != null) _tag('🔑 ${t['key_tag']}', const Color(0xFF64748B)),
                  if (t['has_damage'] == true) _tag('⚠ ${tr('ملاحظات ضرر', 'damage')}', const Color(0xFFE11D48)),
                  if (st == 'requested') _tag('⏱ ${t['retrieval_minutes']} ${tr('د', 'm')}',
                      late ? const Color(0xFFE11D48) : const Color(0xFFF59E0B)),
                  if ((t['fee'] as num? ?? 0) > 0) _tag('${t['fee']} ${tr('د.ك', 'KWD')}', _gold),
                ]),
              ])),
            ]),
            const SizedBox(height: 10),
            Row(children: [
              // the slip the guest walks away with, and scans to call the car up
              Expanded(child: _btn(tr('التذكرة', 'Ticket'), Icons.qr_code_2_rounded,
                  const Color(0xFF64748B), () => _openTicket(t))),
              const SizedBox(width: 6),
              if (st == 'received')
                Expanded(child: _btn(tr('صفّ', 'Park'), Icons.local_parking_rounded, const Color(0xFF16A34A),
                    () => _park(t, d))),
              // A parked ticket shows three actions at once — the labels are
              // kept short so all three fit rather than colliding.
              if (st == 'parked') ...[
                Expanded(child: _btn(tr('إحضار', 'Call up'), Icons.notifications_active_rounded,
                    const Color(0xFFF59E0B), () => _act(t, 'request'))),
                const SizedBox(width: 6),
                Expanded(child: _btn(tr('تسليم', 'Deliver'), Icons.check_rounded, _gold,
                    () => _deliver(t))),
              ],
              if (st == 'requested')
                Expanded(child: _btn(tr('تسليم', 'Hand over'), Icons.check_circle_rounded, const Color(0xFF16A34A),
                    () => _deliver(t))),
            ]),
          ]),
        ),
      ),
    );
  }

  /// Three of these sit side by side on a parked ticket, and at the old size
  /// the labels collided. Tighter padding, smaller type, and the label may
  /// shrink rather than overflow.
  Widget _btn(String l, IconData ic, Color c, VoidCallback onTap) => OutlinedButton(
        style: OutlinedButton.styleFrom(
          foregroundColor: c,
          side: BorderSide(color: c),
          minimumSize: const Size(0, 36),
          padding: const EdgeInsets.symmetric(horizontal: 6),
          visualDensity: VisualDensity.compact,
          tapTargetSize: MaterialTapTargetSize.shrinkWrap,
        ),
        onPressed: _busy ? null : onTap,
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(ic, size: 15),
          const SizedBox(width: 4),
          Flexible(
            child: FittedBox(
              fit: BoxFit.scaleDown,
              child: Text(l, maxLines: 1,
                  style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 11.5)),
            ),
          ),
        ]),
      );

  /// The ticket opens inside the app, where print and share already live.
  /// Bouncing out to a browser lost the session and the user's place.
  void _openTicket(Map t) {
    final id = (t['id'] as num).toInt();
    Navigator.push(context, MaterialPageRoute(
      builder: (_) => PdfReportScreen(
        path: '/valet/ticket/$id/pdf',
        title: '${tr('تذكرة', 'Ticket')} ${t['name'] ?? ''}',
        fileName: 'valet-${t['name'] ?? id}'.replaceAll('/', '-'),
      ),
    ));
  }

  Future<void> _act(Map t, String action, {Map<String, dynamic>? body}) async {
    setState(() => _busy = true);
    try {
      await context.read<AuthProvider>().api.valetAction((t['id'] as num).toInt(), action, body: body);
      await _load();
    } catch (e) {
      if (mounted) _snack('$e');
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  /// Pick a free bay from the zone grid.
  Future<void> _park(Map t, Map d) async {
    final zones = ((d['zones'] as List?) ?? const []).cast<Map>();
    final spots = <PickOption>[];
    for (final z in zones) {
      for (final s in ((z['spots'] as List?) ?? const []).cast<Map>()) {
        if (s['state'] == 'free') {
          spots.add(PickOption(value: s['id'], label: '${s['name']}', sublabel: '${z['name']}'));
        }
      }
    }
    if (spots.isEmpty) {
      _snack(tr('لا مواقف متاحة', 'No free bays'), c: const Color(0xFFE11D48));
      return;
    }
    final picked = await SearchablePicker.open(context,
        options: spots, title: tr('اختر الموقف', 'Choose a bay'), accent: _gold, allowClear: false);
    if (picked == null || !mounted) return;
    // Where exactly, and let the phone capture the coordinates so the car can
    // be found again — a bay id alone does not survive a busy basement.
    final row = TextEditingController();
    final note = TextEditingController();
    final go = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, showDragHandle: true,
      builder: (ctx) => Padding(
        padding: EdgeInsets.fromLTRB(18, 4, 18, MediaQuery.of(ctx).viewInsets.bottom + 18),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(tr('أين رُكنت المركبة؟', 'Where is it parked?'),
              style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w900, color: _navy)),
          const SizedBox(height: 12),
          TextField(controller: row, decoration: InputDecoration(
              labelText: tr('رقم الصف / الموقع', 'Row / bay label'),
              hintText: 'B2-14', border: const OutlineInputBorder())),
          const SizedBox(height: 10),
          TextField(controller: note, decoration: InputDecoration(
              labelText: tr('ملاحظة (اختياري)', 'Note (optional)'),
              hintText: tr('بجانب العمود', 'beside the pillar'), border: const OutlineInputBorder())),
          const SizedBox(height: 14),
          Row(children: [
            Expanded(child: OutlinedButton.icon(
              onPressed: () async {
                final loc = await _captureParkLocation();
                if (loc != null && mounted) {
                  _parkLat = loc.$1; _parkLng = loc.$2;
                  _snack(tr('سُجّل الموقع', 'Location captured'), c: const Color(0xFF16A34A));
                }
              },
              icon: const Icon(Icons.my_location_rounded, size: 18),
              label: Text(_parkLat != 0 ? tr('الموقع مُسجَّل ✓', 'Location set ✓') : tr('التقاط الموقع', 'Capture location')),
              style: OutlinedButton.styleFrom(padding: const EdgeInsets.symmetric(vertical: 13)),
            )),
          ]),
          const SizedBox(height: 12),
          SizedBox(width: double.infinity, height: 50, child: FilledButton(
            style: FilledButton.styleFrom(backgroundColor: const Color(0xFF16A34A)),
            onPressed: () => Navigator.pop(ctx, true),
            child: Text(tr('تأكيد الركن', 'Confirm parking'),
                style: const TextStyle(fontWeight: FontWeight.w900)),
          )),
        ]),
      ),
    );
    if (go != true || !mounted) return;
    try {
      await context.read<AuthProvider>().api.valetPark(intOf(t['id']), {
        'spot_id': picked, 'row': row.text.trim(), 'note': note.text.trim(),
        if (_parkLat != 0) 'lat': _parkLat, if (_parkLng != 0) 'lng': _parkLng,
      });
      _parkLat = 0; _parkLng = 0;
      if (mounted) { _snack(tr('رُكنت المركبة', 'Car parked'), c: const Color(0xFF16A34A)); _load(); }
    } catch (e) {
      // fall back to the generic action if the new route is unavailable
      await _act(t, 'park', body: {'spot_id': picked});
    }
  }

  double _parkLat = 0, _parkLng = 0;

  Future<(double, double)?> _captureParkLocation() async {
    try {
      final ok = await Geolocator.checkPermission();
      if (ok == LocationPermission.denied) await Geolocator.requestPermission();
      final pos = await Geolocator.getCurrentPosition();
      return (pos.latitude, pos.longitude);
    } catch (e) {
      if (mounted) _snack('$e', c: const Color(0xFFE11D48));
      return null;
    }
  }

  /// Hand the car back and settle the charge.
  Future<void> _deliver(Map t) async {
    final fee = TextEditingController(text: '${t['fee'] ?? 0}');
    final tip = TextEditingController(text: '0');
    bool paid = true;
    final ok = await showDialog<bool>(context: context, builder: (c) => StatefulBuilder(
      builder: (c, setSt) => AlertDialog(
        title: Text(tr('تسليم المركبة', 'Hand the car back')),
        content: Column(mainAxisSize: MainAxisSize.min, children: [
          Text('${t['plate']} · ${t['car'] ?? ''}', style: const TextStyle(fontWeight: FontWeight.w800)),
          const SizedBox(height: 12),
          TextField(controller: fee, keyboardType: TextInputType.number,
              decoration: InputDecoration(labelText: tr('الرسوم', 'Fee'), border: const OutlineInputBorder())),
          const SizedBox(height: 10),
          TextField(controller: tip, keyboardType: TextInputType.number,
              decoration: InputDecoration(labelText: tr('الإكرامية', 'Tip'), border: const OutlineInputBorder())),
          const SizedBox(height: 6),
          SwitchListTile(
            value: paid, activeColor: _gold, contentPadding: EdgeInsets.zero,
            title: Text(tr('تم الدفع', 'Paid'), style: const TextStyle(fontSize: 13.5, fontWeight: FontWeight.w800)),
            onChanged: (v) => setSt(() => paid = v),
          ),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: Text(tr('تراجع', 'Cancel'))),
          FilledButton(style: FilledButton.styleFrom(backgroundColor: _gold),
              onPressed: () => Navigator.pop(c, true), child: Text(tr('تسليم', 'Deliver'))),
        ],
      ),
    ));
    if (ok != true) return;
    await _act(t, 'deliver', body: {
      'fee': double.tryParse(fee.text.trim()) ?? 0,
      'tip': double.tryParse(tip.text.trim()) ?? 0,
      'paid': paid,
    });
    if (mounted) _snack(tr('✅ سُلّمت المركبة', '✅ Car handed back'), c: const Color(0xFF16A34A));
  }

  /// Read the plate off a photo of the car. An attendant holding keys in one
  /// hand should not be typing a plate with the other, and a mistyped plate is
  /// the one error this service cannot recover from.

  /// Look the plate up and fill in what the registry already holds.
  Future<void> _prefillFromPlate(String read, void Function(void Function()) setSt) async {
    Map<String, dynamic> v;
    try {
      v = await context.read<AuthProvider>().api.valetPlate(read);
    } catch (_) {
      _snack('${tr('قُرئت اللوحة', 'Plate read')}: $read', c: const Color(0xFF16A34A));
      return;
    }
    if (!mounted) return;
    if (v['known'] != true) {
      _snack('${tr('مركبة جديدة', 'New vehicle')}: $read', c: const Color(0xFF16A34A));
      return;
    }
    setSt(() {
      if ('${v['make'] ?? ''}'.isNotEmpty) _prefill['make'] = '${v['make']}';
      if ('${v['color'] ?? ''}'.isNotEmpty) _prefill['color'] = '${v['color']}';
      if ('${v['owner'] ?? ''}'.isNotEmpty) _prefill['owner'] = '${v['owner']}';
      if ('${v['phone'] ?? ''}'.isNotEmpty) _prefill['phone'] = '${v['phone']}';
    });
    // A blocked car must stop the crew before the key changes hands, and a
    // VIP must be known before the guest is halfway to the door.
    if (v['blocked'] == true) {
      await showDialog(
        context: context,
        builder: (c) => AlertDialog(
          icon: const Icon(Icons.block_rounded, size: 42, color: Color(0xFFE11D48)),
          title: Text(tr('مركبة ممنوعة', 'Blocked vehicle'), textAlign: TextAlign.center),
          content: Text('${v['plate']}\n${v['block_reason'] ?? ''}',
              textAlign: TextAlign.center),
          actions: [TextButton(onPressed: () => Navigator.pop(c), child: Text(tr('حسنًا', 'OK')))],
        ),
      );
      return;
    }
    final bits = <String>[
      if (v['vip'] == true) '⭐ VIP',
      '${tr('زيارة رقم', 'Visit')} ${intOf(v['visits']) + 1}',
      if ('${v['owner'] ?? ''}'.isNotEmpty) '${v['owner']}',
      if ('${v['notes'] ?? ''}'.isNotEmpty) '📌 ${v['notes']}',
    ];
    _snack(bits.join(' · '), c: const Color(0xFF0891B2));
  }

  final Map<String, String> _prefill = {};

  Future<String?> _scanPlate() async {
    try {
      final shot = await ImagePicker().pickImage(
          source: ImageSource.camera, imageQuality: 92, maxWidth: 1600);
      if (shot == null) return null;
      final recogniser = TextRecognizer(script: TextRecognitionScript.latin);
      final result = await recogniser.processImage(InputImage.fromFile(File(shot.path)));
      await recogniser.close();
      // Plates are short, mostly digits, and sit on their own line. Score the
      // lines and take the most plate-like rather than the longest blob of text.
      String? best;
      var bestScore = -1.0;
      for (final block in result.blocks) {
        for (final line in block.lines) {
          final raw = line.text.replaceAll(RegExp(r'[^0-9A-Za-z\u0600-\u06FF ]'), '').trim();
          if (raw.length < 3 || raw.length > 12) continue;
          final digits = RegExp(r'[0-9]').allMatches(raw).length;
          if (digits < 3) continue;
          final score = digits * 2.0 + (raw.length <= 8 ? 3 : 0) - (raw.length - digits) * 0.5;
          if (score > bestScore) { bestScore = score; best = raw; }
        }
      }
      return best;
    } catch (e) {
      if (mounted) _snack(tr('تعذّرت قراءة اللوحة — اكتبها يدويًا',
          'Could not read the plate — type it in'));
      return null;
    }
  }

  /// Take a car in — plate first, everything else optional.
  Future<void> _newTicket(Map? d) async {
    final facs = ((d?['facilities'] as List?) ?? const []).cast<Map>();
    final zones = ((d?['zones'] as List?) ?? const []).cast<Map>();
    final plate = TextEditingController();
    final make = TextEditingController();
    final model = TextEditingController();
    final color = TextEditingController();
    final guest = TextEditingController();
    final phone = TextEditingController();
    final keyTag = TextEditingController();
    final damage = TextEditingController();
    final fee = TextEditingController();
    int? facId = facs.isNotEmpty ? facs.first['id'] as int : null;
    int? zoneId = zones.isNotEmpty ? zones.first['id'] as int : null;

    final saved = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSt) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
        child: DraggableScrollableSheet(
          expand: false, initialChildSize: 0.85, minChildSize: 0.5, maxChildSize: 0.95,
          builder: (_, sc) => Container(
            decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
            clipBehavior: Clip.antiAlias,
            child: Column(children: [
              Container(
                width: double.infinity, padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
                decoration: const BoxDecoration(gradient: LinearGradient(colors: [_gold, _navy], begin: Alignment.topRight, end: Alignment.bottomLeft)),
                child: Column(children: [
                  Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12), decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
                  Row(children: [
                    const Icon(Icons.directions_car_rounded, color: Colors.white),
                    const SizedBox(width: 10),
                    Expanded(child: Text(tr('استلام مركبة', 'Take a car in'),
                        style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900))),
                  ]),
                ]),
              ),
              Expanded(child: ListView(controller: sc, padding: const EdgeInsets.all(16), children: [
                Row(crossAxisAlignment: CrossAxisAlignment.end, children: [
                  Expanded(child: _f(plate, tr('رقم اللوحة *', 'Plate *'), big: true)),
                  const SizedBox(width: 8),
                  SizedBox(
                    height: 52,
                    child: FilledButton.icon(
                      style: FilledButton.styleFrom(backgroundColor: _gold,
                          padding: const EdgeInsets.symmetric(horizontal: 14)),
                      onPressed: () async {
                        final read = await _scanPlate();
                        if (read == null || read.isEmpty) return;
                        setSt(() => plate.text = read);
                        // A plate the camera reads is only half the answer.
                        // If this car has been here before, everything we
                        // already know about it fills itself in — and a
                        // blocked or VIP car says so before the key is taken.
                        await _prefillFromPlate(read, setSt);
                      },
                      icon: const Icon(Icons.document_scanner_rounded, size: 18),
                      label: Text(tr('تصوير', 'Scan'),
                          style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5)),
                    ),
                  ),
                ]),
                const SizedBox(height: 10),
                Row(children: [
                  Expanded(child: _f(make, tr('الماركة', 'Make'))),
                  const SizedBox(width: 8),
                  Expanded(child: _f(model, tr('الموديل', 'Model'))),
                ]),
                const SizedBox(height: 10),
                Row(children: [
                  Expanded(child: _f(color, tr('اللون', 'Colour'))),
                  const SizedBox(width: 8),
                  Expanded(child: _f(keyTag, tr('رقم المفتاح', 'Key tag'))),
                ]),
                const SizedBox(height: 10),
                Row(children: [
                  Expanded(child: _f(guest, tr('اسم الضيف', 'Guest'))),
                  const SizedBox(width: 8),
                  Expanded(child: _f(phone, tr('الهاتف', 'Phone'))),
                ]),
                const SizedBox(height: 10),
                _f(fee, tr('الرسوم (اختياري)', 'Fee (optional)')),
                const SizedBox(height: 10),
                _f(damage, tr('ملاحظات حالة المركبة (خدوش…)', 'Condition notes (scratches…)'), lines: 2),
                if (facs.length > 1) ...[
                  const SizedBox(height: 10),
                  SearchableField(label: tr('المرفق', 'Facility'), value: facId, accent: _gold, allowClear: false,
                      icon: Icons.apartment_rounded,
                      options: [for (final f in facs) PickOption(value: f['id'], label: '${f['name']}')],
                      onChanged: (v) => setSt(() => facId = v as int?)),
                ],
                if (zones.isNotEmpty) ...[
                  const SizedBox(height: 10),
                  SearchableField(label: tr('المنطقة', 'Zone'), value: zoneId, accent: _gold,
                      icon: Icons.local_parking_rounded,
                      options: [for (final z in zones) PickOption(value: z['id'], label: '${z['name']}')],
                      onChanged: (v) => setSt(() => zoneId = v as int?)),
                ],
                const SizedBox(height: 16),
                FilledButton.icon(
                  style: FilledButton.styleFrom(backgroundColor: _gold, minimumSize: const Size.fromHeight(52)),
                  onPressed: () {
                    if (plate.text.trim().isEmpty) {
                      ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(content: Text(tr('أدخل رقم اللوحة', 'Enter the plate'))));
                      return;
                    }
                    Navigator.pop(ctx, true);
                  },
                  icon: const Icon(Icons.check_rounded),
                  label: Text(tr('إصدار التذكرة', 'Issue ticket'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
                ),
                const SizedBox(height: 10),
              ])),
            ]),
          ),
        ),
      )),
    );
    if (saved != true) return;
    try {
      final t = await context.read<AuthProvider>().api.valetCreate({
        'plate': plate.text.trim(),
        'car_make': make.text.trim(), 'car_model': model.text.trim(),
        'car_color': color.text.trim(), 'key_tag': keyTag.text.trim(),
        'guest': guest.text.trim(), 'phone': phone.text.trim(),
        'damage_note': damage.text.trim(),
        'fee': double.tryParse(fee.text.trim()) ?? 0,
        if (facId != null) 'facility_id': facId,
        if (zoneId != null) 'zone_id': zoneId,
      });
      await _load();
      if (mounted) _snack('${tr('صدرت التذكرة', 'Ticket issued')} ${t['name']}', c: const Color(0xFF16A34A));
    } catch (e) {
      if (mounted) _snack('$e');
    }
  }

  /// Open or close the attendant's shift and see its takings.
  Future<void> _shiftSheet(Map? d) async {
    final shift = d?['shift'] as Map?;
    final facs = ((d?['facilities'] as List?) ?? const []).cast<Map>();
    await showModalBottomSheet(context: context, backgroundColor: Colors.transparent,
      builder: (ctx) => Container(
        decoration: const BoxDecoration(color: Colors.white, borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
        padding: const EdgeInsets.fromLTRB(20, 14, 20, 24),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 14),
              decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(3))),
          Icon(Icons.badge_rounded, size: 34, color: _gold),
          const SizedBox(height: 8),
          Text(shift == null ? tr('لا توجد وردية مفتوحة', 'No open shift') : '${shift['name']}',
              style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: _navy)),
          if (shift != null) ...[
            const SizedBox(height: 12),
            Row(children: [
              _sv('${shift['tickets']}', tr('تذكرة', 'Tickets')),
              _sv('${shift['fees']}', tr('الرسوم', 'Fees')),
              _sv('${shift['tips']}', tr('الإكراميات', 'Tips')),
              _sv('${shift['cash_due']}', tr('النقد المستحق', 'Cash due')),
            ]),
          ],
          const SizedBox(height: 16),
          SizedBox(width: double.infinity, child: FilledButton.icon(
            style: FilledButton.styleFrom(
                backgroundColor: shift == null ? const Color(0xFF16A34A) : const Color(0xFFE11D48),
                minimumSize: const Size.fromHeight(50)),
            onPressed: () async {
              Navigator.pop(ctx);
              try {
                final r = await context.read<AuthProvider>().api.valetShift(
                    shift == null ? 'open' : 'close',
                    facilityId: facs.isNotEmpty ? facs.first['id'] as int : null);
                await _load();
                if (!mounted) return;
                _snack(shift == null
                        ? '${tr('فُتحت الوردية', 'Shift opened')} ${r['name']}'
                        : '${tr('أُغلقت الوردية — النقد المستحق', 'Shift closed — cash due')} ${r['cash_due'] ?? 0}',
                    c: const Color(0xFF16A34A));
              } catch (e) {
                if (mounted) _snack('$e');
              }
            },
            icon: Icon(shift == null ? Icons.play_arrow_rounded : Icons.stop_rounded),
            label: Text(shift == null ? tr('فتح وردية', 'Open shift') : tr('إغلاق الوردية', 'Close shift'),
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
          )),
        ]),
      ),
    );
  }

  Widget _sv(String v, String l) => Expanded(child: Column(children: [
        Text(v, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16, color: _gold)),
        Text(l, textAlign: TextAlign.center, style: TextStyle(fontSize: 10, color: Colors.grey.shade600, fontWeight: FontWeight.w700)),
      ]));

  Widget _f(TextEditingController c, String hint, {int lines = 1, bool big = false}) => TextField(
        controller: c, maxLines: lines,
        style: big ? const TextStyle(fontSize: 17, fontWeight: FontWeight.w900) : null,
        decoration: InputDecoration(
          hintText: hint, filled: true, fillColor: Colors.white, isDense: true,
          hintStyle: TextStyle(fontSize: 13, color: Colors.grey.shade400, fontWeight: FontWeight.normal),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
          enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
        ),
      );

  Widget _tag(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(7)),
        child: Text(t, style: TextStyle(color: c, fontSize: 10, fontWeight: FontWeight.w800)),
      );

  Widget _empty(String t) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 40),
        child: Column(children: [
          Icon(Icons.directions_car_outlined, size: 54, color: Colors.grey.shade300),
          const SizedBox(height: 10),
          Text(t, style: TextStyle(color: Colors.grey.shade500, fontWeight: FontWeight.w600)),
        ]),
      );
}
