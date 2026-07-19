import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'observation_create.dart';
import 'observation_detail.dart';
import 'quality_screen.dart';
import 'service_screen.dart';
import 'workorders_screen.dart';
import 'scan_screen.dart';
import 'chat_screen.dart';
import 'my_profile_screen.dart';
import 'notifications_screen.dart';
import 'searchable_picker.dart';

const _navy = Color(0xFF0E3A5F);
const _teal = Color(0xFF0EA5A4);
const _sevColors = {
  'low': Color(0xFF64748B), 'medium': Color(0xFF3B82F6),
  'high': Color(0xFFF59E0B), 'critical': Color(0xFFE11D48),
};

/// The quality inspector's console: what they inspect (team / service / facility
/// / client), live observation stats, a severity breakdown, their recent notes —
/// and a two-tap quick note so logging a finding on the round is instant.
class QualityHome extends StatefulWidget {
  const QualityHome({super.key});
  @override
  State<QualityHome> createState() => _QualityHomeState();
}

class _QualityHomeState extends State<QualityHome> {
  Map<String, dynamic>? _d;
  String _period = 'month';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.meQuality(period: _period);
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  void _go(Widget s) => Navigator.push(context, MaterialPageRoute(builder: (_) => s));

  @override
  Widget build(BuildContext context) {
    final p = context.watch<AuthProvider>().profile!;
    final d = _d;
    final stats = (d?['stats'] as Map?) ?? const {};
    final recent = ((d?['recent'] as List?) ?? const []).cast<Map>();
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: _teal,
        onPressed: () => _quickNote(d),
        icon: const Icon(Icons.add_a_photo_rounded),
        label: Text(tr('ملاحظة سريعة', 'Quick note'), style: const TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: RefreshIndicator(
        color: _teal,
        onRefresh: _load,
        child: ListView(padding: EdgeInsets.zero, children: [
          _header(p, d, stats),
          _actions(),
          if (d == null)
            const Padding(padding: EdgeInsets.all(40), child: Center(child: CircularProgressIndicator(color: _teal)))
          else ...[
            if (((d['by_severity'] as List?) ?? const []).isNotEmpty) _severityBar(d['by_severity'] as List),
            _sectionTitle(Icons.fact_check_rounded, tr('أحدث الملاحظات', 'Recent observations'), recent.length),
            if (recent.isEmpty)
              _empty(tr('لا ملاحظات — سجّل أول ملاحظة', 'No observations yet — log your first'))
            else
              for (final o in recent.take(15)) _obsCard(o),
          ],
          const SizedBox(height: 90),
        ]),
      ),
    );
  }

  Widget _header(dynamic p, Map? d, Map stats) {
    final teams = ((d?['teams'] as List?) ?? const []).cast<Map>();
    return CustomPaint(
      painter: const BrandPattern(opacity: 0.07),
      child: Container(
        padding: const EdgeInsets.fromLTRB(18, 0, 10, 18),
        decoration: const BoxDecoration(
          gradient: LinearGradient(colors: [_teal, Color(0xFF0F766E), _navy], begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.vertical(bottom: Radius.circular(26)),
        ),
        child: SafeArea(bottom: false, child: Column(children: [
          Row(children: [
            const Text('✅', style: TextStyle(fontSize: 20)),
            const SizedBox(width: 8),
            Expanded(child: Text(tr('مراقبة الجودة', 'Quality control'),
                style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900))),
            IconButton(icon: const Icon(Icons.notifications_rounded, color: Colors.white),
                onPressed: () => _go(const NotificationsScreen())),
            IconButton(icon: const Icon(Icons.workspace_premium_rounded, color: Colors.white),
                onPressed: () => _go(const MyProfileScreen())),
            IconButton(icon: const Icon(Icons.logout_rounded, color: Colors.white),
                onPressed: () => context.read<AuthProvider>().logout()),
          ]),
          Row(children: [
            Container(
              padding: const EdgeInsets.all(3),
              decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: Colors.white.withValues(alpha: 0.4), width: 2)),
              child: MeAvatar(name: p.name, radius: 26, fallbackColor: _teal),
            ),
            const SizedBox(width: 13),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(p.name, maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
              const SizedBox(height: 3),
              Text(tr('مراقب جودة · جولات وتفتيش', 'Quality inspector · rounds & audits'),
                  style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 11.5)),
            ])),
          ]),
          // what exactly they inspect
          if (teams.isNotEmpty) ...[
            const SizedBox(height: 12),
            for (final t in teams) Container(
              width: double.infinity,
              margin: const EdgeInsets.only(bottom: 6),
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.13), borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.white.withValues(alpha: 0.18))),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  const Icon(Icons.verified_rounded, color: Colors.white, size: 15),
                  const SizedBox(width: 6),
                  Expanded(child: Text('${t['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13))),
                ]),
                const SizedBox(height: 7),
                Wrap(spacing: 6, runSpacing: 6, children: [
                  if (t['service'] != null) _ctx(Icons.design_services_rounded, '${t['service']}'),
                  if (t['facility'] != null) _ctx(Icons.apartment_rounded, '${t['facility']}'),
                  if (t['client'] != null) _ctx(Icons.badge_rounded, '${t['client']}'),
                  if (t['supervisor'] != null) _ctx(Icons.supervisor_account_rounded, '${t['supervisor']}'),
                ]),
              ]),
            ),
          ],
          const SizedBox(height: 6),
          // period filter
          SizedBox(height: 34, child: ListView(scrollDirection: Axis.horizontal, children: [
            for (final pr in const [('today', 'اليوم', 'Today'), ('week', 'الأسبوع', 'Week'), ('month', 'الشهر', 'Month'), ('all', 'الكل', 'All')])
              Padding(padding: const EdgeInsets.only(left: 6), child: GestureDetector(
                onTap: () { setState(() => _period = pr.$1); _load(); },
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 7),
                  decoration: BoxDecoration(color: _period == pr.$1 ? Colors.white : Colors.white.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(20)),
                  child: Text(tr(pr.$2, pr.$3), style: TextStyle(color: _period == pr.$1 ? _teal : Colors.white, fontSize: 11.5, fontWeight: FontWeight.w900)),
                ),
              )),
          ])),
          const SizedBox(height: 12),
          // live stats
          Container(
            padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 6),
            decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.white.withValues(alpha: 0.18))),
            child: Row(children: [
              _hs(Icons.pending_actions_rounded, '${stats['open'] ?? 0}', tr('مفتوحة', 'Open')),
              _hd(),
              _hs(Icons.priority_high_rounded, '${stats['critical'] ?? 0}', tr('حرجة', 'Critical')),
              _hd(),
              _hs(Icons.edit_note_rounded, '${stats['mine'] ?? 0}', tr('سجّلتها', 'Mine')),
              _hd(),
              _hs(Icons.build_rounded, '${stats['converted'] ?? 0}', tr('حُوّلت', 'Converted')),
              _hd(),
              _hs(Icons.check_circle_rounded, '${stats['closed'] ?? 0}', tr('أُغلقت', 'Closed')),
            ]),
          ),
        ])),
      ),
    );
  }

  Widget _hs(IconData ic, String v, String l) => Expanded(child: Column(children: [
        Icon(ic, color: Colors.white, size: 16),
        const SizedBox(height: 3),
        Text(v, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900)),
        Text(l, textAlign: TextAlign.center, style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 9, fontWeight: FontWeight.w600)),
      ]));

  Widget _hd() => Container(width: 1, height: 32, color: Colors.white.withValues(alpha: 0.18));

  Widget _ctx(IconData ic, String t) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 4),
        decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(8)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(ic, color: Colors.white, size: 12), const SizedBox(width: 5),
          Text(t, style: const TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.w800)),
        ]),
      );

  Widget _actions() {
    final items = <(IconData, String, String, Color, VoidCallback)>[
      (Icons.note_add_rounded, 'ملاحظة كاملة', 'Full note', _teal, () async {
        final ok = await ObservationCreateSheet.open(context);
        if (ok == true) _load();
      }),
      (Icons.fact_check_rounded, 'كل الملاحظات', 'All notes', const Color(0xFF0891B2), () => _go(const QualityScreen())),
      (Icons.cleaning_services_rounded, 'تدقيق النظافة', 'Cleaning audit', const Color(0xFF0EA5E9),
          () => _go(const ServiceScreen(kind: 'cleaning', title: 'تدقيق النظافة'))),
      (Icons.assignment_rounded, 'أوامر العمل', 'Work orders', _navy, () => _go(const WorkOrdersScreen())),
      (Icons.qr_code_scanner_rounded, 'مسح موقع', 'Scan', const Color(0xFF0D9488), () => _go(const ScanScreen())),
      (Icons.forum_rounded, 'التواصل', 'Messages', const Color(0xFF0E7490), () => _go(const ChatHubScreen())),
    ];
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 14, 12, 4),
      child: GridView.count(
        crossAxisCount: 3, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
        mainAxisSpacing: 10, crossAxisSpacing: 10, childAspectRatio: 1.0,
        children: [
          for (final a in items)
            Material(
              color: Colors.white, borderRadius: BorderRadius.circular(15),
              child: InkWell(
                borderRadius: BorderRadius.circular(15), onTap: a.$5,
                child: Container(
                  decoration: BoxDecoration(borderRadius: BorderRadius.circular(15), border: Border.all(color: Colors.grey.shade200)),
                  padding: const EdgeInsets.symmetric(vertical: 11, horizontal: 6),
                  child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                    Container(width: 42, height: 42, alignment: Alignment.center,
                        decoration: BoxDecoration(color: a.$4.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(12)),
                        child: Icon(a.$1, color: a.$4, size: 21)),
                    const SizedBox(height: 7),
                    Text(tr(a.$2, a.$3), textAlign: TextAlign.center, maxLines: 2, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 11, color: _navy)),
                  ]),
                ),
              ),
            ),
        ],
      ),
    );
  }

  Widget _severityBar(List bySev) {
    final total = bySev.fold<int>(0, (s, g) => s + ((g as Map)['count'] as num).toInt());
    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 12, 12, 0),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.grey.shade200)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.flag_rounded, size: 17, color: _teal), const SizedBox(width: 7),
            Text(tr('المفتوحة حسب الخطورة', 'Open by severity'),
                style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
          ]),
          const SizedBox(height: 10),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: Row(children: [
              for (final g in bySev)
                Expanded(
                  flex: ((g as Map)['count'] as num).toInt().clamp(1, 999),
                  child: Container(height: 10, color: _sevColors['${g['key']}'] ?? Colors.grey),
                ),
            ]),
          ),
          const SizedBox(height: 10),
          Wrap(spacing: 10, runSpacing: 6, children: [
            for (final g in bySev)
              Row(mainAxisSize: MainAxisSize.min, children: [
                Container(width: 9, height: 9, decoration: BoxDecoration(color: _sevColors['${(g as Map)['key']}'] ?? Colors.grey, shape: BoxShape.circle)),
                const SizedBox(width: 5),
                Text('${g['label']} · ${g['count']}', style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w800, color: _navy)),
              ]),
            Text('${tr('الإجمالي', 'Total')} $total', style: TextStyle(fontSize: 11.5, color: Colors.grey.shade600, fontWeight: FontWeight.w700)),
          ]),
        ]),
      ),
    );
  }

  Widget _obsCard(Map o) {
    final c = _sevColors['${o['severity']}'] ?? Colors.grey;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Material(
        color: Colors.white, borderRadius: BorderRadius.circular(14),
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: () async {
            final changed = await ObservationDetailSheet.open(context, (o['id'] as num).toInt());
            if (changed == true) _load();
          },
          child: Container(
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.grey.shade200)),
            padding: const EdgeInsets.all(11),
            child: Row(children: [
              Container(width: 5, height: 46, decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(4))),
              const SizedBox(width: 11),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Expanded(child: Text('${o['title']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: _navy))),
                  if (o['mine'] == true)
                    Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(color: _teal.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(6)),
                        child: Text(tr('لي', 'mine'), style: const TextStyle(color: _teal, fontSize: 9.5, fontWeight: FontWeight.w900))),
                ]),
                const SizedBox(height: 3),
                Text([o['facility'], o['location'], o['at']].where((x) => x != null).join(' · '),
                    maxLines: 1, overflow: TextOverflow.ellipsis, style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
                const SizedBox(height: 5),
                Wrap(spacing: 6, children: [
                  _tag('${o['severity_label']}', c),
                  _tag('${o['state_label']}', const Color(0xFF64748B)),
                  if (o['workorder'] != null) _tag('🛠️ ${o['workorder']}', const Color(0xFF16A34A)),
                ]),
              ])),
            ]),
          ),
        ),
      ),
    );
  }

  Widget _tag(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(7)),
        child: Text(t, style: TextStyle(color: c, fontSize: 10, fontWeight: FontWeight.w800)),
      );

  Widget _sectionTitle(IconData ic, String t, int n) => Padding(
        padding: const EdgeInsets.fromLTRB(14, 18, 14, 8),
        child: Row(children: [
          Icon(ic, size: 17, color: _navy), const SizedBox(width: 7),
          Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: _navy)),
          const SizedBox(width: 8),
          Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(color: _teal.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
              child: Text('$n', style: const TextStyle(color: _teal, fontWeight: FontWeight.w900, fontSize: 11.5))),
        ]),
      );

  Widget _empty(String t) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Container(
          width: double.infinity, padding: const EdgeInsets.all(22), alignment: Alignment.center,
          decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14), border: Border.all(color: Colors.grey.shade200)),
          child: Text(t, style: TextStyle(color: Colors.grey.shade500, fontWeight: FontWeight.w600)),
        ),
      );

  // ------------------------------------------------------------ quick note --
  /// Two taps to a logged finding: snap the photo, pick severity, done. Facility
  /// and location default to the last used, and everything else is optional.
  Future<void> _quickNote(Map? d) async {
    final facs = ((d?['facilities'] as List?) ?? const []).cast<Map>();
    if (facs.isEmpty) {
      final ok = await ObservationCreateSheet.open(context);
      if (ok == true) _load();
      return;
    }
    int facId = facs.first['id'] as int;
    int? locId;
    String sev = 'medium';
    final title = TextEditingController();
    String? photo;
    final picker = ImagePicker();

    final saved = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSt) {
        final locs = ((facs.firstWhere((f) => f['id'] == facId, orElse: () => const {})['locations'] as List?) ?? const []).cast<Map>();
        return Padding(
          padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
          child: Container(
            decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
            clipBehavior: Clip.antiAlias,
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              Container(
                width: double.infinity, padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
                decoration: const BoxDecoration(gradient: LinearGradient(colors: [_teal, _navy], begin: Alignment.topRight, end: Alignment.bottomLeft)),
                child: Column(children: [
                  Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12), decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
                  Row(children: [
                    const Icon(Icons.bolt_rounded, color: Colors.white),
                    const SizedBox(width: 8),
                    Expanded(child: Text(tr('ملاحظة سريعة', 'Quick note'),
                        style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900))),
                  ]),
                ]),
              ),
              Padding(padding: const EdgeInsets.all(16), child: Column(children: [
                // 1) the photo — the fastest way to say what is wrong
                GestureDetector(
                  onTap: () async {
                    final x = await picker.pickImage(source: ImageSource.camera, imageQuality: 65, maxWidth: 1600);
                    if (x == null) return;
                    final b = await x.readAsBytes();
                    setSt(() => photo = base64Encode(b));
                  },
                  child: Container(
                    height: 110, width: double.infinity, clipBehavior: Clip.antiAlias,
                    decoration: BoxDecoration(color: _teal.withValues(alpha: 0.07), borderRadius: BorderRadius.circular(14), border: Border.all(color: _teal.withValues(alpha: 0.35))),
                    child: photo == null
                        ? Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                            const Icon(Icons.photo_camera_rounded, color: _teal, size: 30),
                            const SizedBox(height: 6),
                            Text(tr('التقط صورة الملاحظة', 'Snap the finding'),
                                style: const TextStyle(color: _teal, fontWeight: FontWeight.w900, fontSize: 12.5)),
                          ])
                        : Image.memory(base64Decode(photo!), fit: BoxFit.cover, width: double.infinity),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: title, autofocus: false,
                  decoration: InputDecoration(
                    hintText: tr('الملاحظة… مثال: أرضية غير نظيفة', 'The finding… e.g. dirty floor'),
                    filled: true, fillColor: Colors.white, isDense: true,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
                    enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide(color: Colors.grey.shade300)),
                  ),
                ),
                const SizedBox(height: 10),
                // 2) severity — one tap
                Row(children: [
                  for (final s in const [('low', 'منخفضة', 'Low'), ('medium', 'متوسطة', 'Medium'), ('high', 'عالية', 'High'), ('critical', 'حرجة', 'Critical')])
                    Expanded(child: GestureDetector(
                      onTap: () => setSt(() => sev = s.$1),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 140),
                        margin: const EdgeInsets.symmetric(horizontal: 3),
                        padding: const EdgeInsets.symmetric(vertical: 9),
                        decoration: BoxDecoration(
                          color: sev == s.$1 ? (_sevColors[s.$1] ?? _teal) : Colors.white,
                          borderRadius: BorderRadius.circular(11),
                          border: Border.all(color: sev == s.$1 ? (_sevColors[s.$1] ?? _teal) : Colors.grey.shade300)),
                        child: Text(tr(s.$2, s.$3), textAlign: TextAlign.center,
                            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: sev == s.$1 ? Colors.white : _navy)),
                      ),
                    )),
                ]),
                const SizedBox(height: 12),
                if (facs.length > 1)
                  SearchableField(
                    label: tr('المرفق', 'Facility'), icon: Icons.apartment_rounded, value: facId, accent: _teal, allowClear: false,
                    options: [for (final f in facs) PickOption(value: f['id'], label: '${f['name']}')],
                    onChanged: (v) => setSt(() { facId = v as int; locId = null; }),
                  ),
                if (locs.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  SearchableField(
                    label: tr('الموقع (اختياري)', 'Location (optional)'), icon: Icons.pin_drop_rounded, value: locId, accent: _teal,
                    options: [for (final l in locs) PickOption(value: l['id'], label: '${l['name']}', sublabel: l['code'] == null ? null : '${l['code']}')],
                    onChanged: (v) => setSt(() => locId = v as int?),
                  ),
                ],
                const SizedBox(height: 14),
                FilledButton.icon(
                  style: FilledButton.styleFrom(backgroundColor: _teal, minimumSize: const Size.fromHeight(50)),
                  onPressed: () async {
                    if (title.text.trim().isEmpty && photo == null) {
                      ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(content: Text(tr('أضف صورة أو نص الملاحظة', 'Add a photo or the finding text'))));
                      return;
                    }
                    try {
                      await context.read<AuthProvider>().api.createObservation({
                        'title': title.text.trim().isEmpty ? tr('ملاحظة من الجولة', 'Round finding') : title.text.trim(),
                        'facility_id': facId, 'location_id': locId, 'severity': sev,
                        if (photo != null) 'media': [{'name': 'quick.jpg', 'mimetype': 'image/jpeg', 'data': photo}],
                      });
                      if (ctx.mounted) Navigator.pop(ctx, true);
                    } catch (e) {
                      if (ctx.mounted) ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(content: Text('$e')));
                    }
                  },
                  icon: const Icon(Icons.check_rounded),
                  label: Text(tr('حفظ الملاحظة', 'Save note'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
                ),
                const SizedBox(height: 8),
              ])),
            ]),
          ),
        );
      }),
    );
    if (saved == true) {
      _load();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('✅ سُجّلت الملاحظة', '✅ Observation logged')),
          backgroundColor: const Color(0xFF16A34A), behavior: SnackBarBehavior.floating));
      }
    }
  }
}
