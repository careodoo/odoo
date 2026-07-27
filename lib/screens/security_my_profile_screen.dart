import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// «ملفي المهني» — بطاقة الحارس الاحترافية: الهوية + إحصائيات الأداء + الشهادات
/// والرخص (بحالة الانتهاء) + المهارات + المعدّات بعهدته + الرتبة والدور.
class SecurityMyProfileScreen extends StatefulWidget {
  const SecurityMyProfileScreen({super.key});
  @override
  State<SecurityMyProfileScreen> createState() => _SecurityMyProfileScreenState();
}

class _SecurityMyProfileScreenState extends State<SecurityMyProfileScreen> {
  static const _navy = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);
  static const _green = Color(0xFF37C98A);
  static const _amber = Color(0xFFF7A23B);
  static const _red = Color(0xFFE5484D);
  static const _blue = Color(0xFF4AA8FF);

  Map<String, dynamic>? _d;
  bool _loading = true;

  @override
  void initState() { super.initState(); _load(); }
  Future<void> _load() async {
    try { final d = await context.read<AuthProvider>().api.securityMyProfile();
      if (mounted) setState(() { _d = d; _loading = false; }); }
    catch (_) { if (mounted) setState(() => _loading = false); }
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    return Scaffold(
      backgroundColor: _navy,
      appBar: AppBar(title: Text(tr('ملفي المهني', 'My profile')), backgroundColor: _navy,
          actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))]),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : d == null
              ? Center(child: Text(tr('تعذّر تحميل الملف', 'Could not load profile'), style: const TextStyle(color: _muted)))
              : RefreshIndicator(onRefresh: _load, child: ListView(padding: const EdgeInsets.all(12), children: [
                  _identity(d),
                  const SizedBox(height: 12),
                  _kpis((d['stats'] as Map?) ?? const {}),
                  const SizedBox(height: 12),
                  _details(d),
                  _certifications(((d['certifications'] as List?) ?? const []).cast<Map>()),
                  _skills(((d['skills'] as List?) ?? const []).cast<Map>()),
                  _equipment(((d['equipment'] as List?) ?? const []).cast<Map>()),
                  const SizedBox(height: 20),
                ])),
    );
  }

  Widget _identity(Map d) {
    final b64 = '${d['photo_b64'] ?? ''}';
    ImageProvider? img;
    if (b64.isNotEmpty) { try { img = MemoryImage(base64Decode(b64)); } catch (_) {} }
    final onShift = ((d['stats'] as Map?)?['on_shift']) == true;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [Color(0xFF1E3A5F), _card], begin: Alignment.topRight, end: Alignment.bottomLeft),
        borderRadius: BorderRadius.circular(18), border: Border.all(color: const Color(0xFF25405F)),
      ),
      child: Row(children: [
        Stack(children: [
          CircleAvatar(radius: 38, backgroundColor: const Color(0xFF2A3B54), backgroundImage: img,
              child: img == null ? Text('${d['name'] ?? '?'}'.characters.first, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 28)) : null),
          if (onShift) Positioned(right: 0, bottom: 0, child: Container(padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              decoration: BoxDecoration(color: _green, borderRadius: BorderRadius.circular(10), border: Border.all(color: _card, width: 2)),
              child: const Text('●', style: TextStyle(color: Colors.white, fontSize: 8)))),
        ]),
        const SizedBox(width: 14),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${d['name'] ?? ''}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
          const SizedBox(height: 4),
          Wrap(spacing: 6, runSpacing: 6, children: [
            if (d['rank'] != null) _chip('${d['rank']}', _blue, Icons.military_tech_rounded),
            if (d['is_leader'] == true) _chip(tr('قائد فريق', 'Team lead'), _amber, Icons.stars_rounded),
            if (d['role'] != null) _chip('${d['role']}', _muted, Icons.badge_rounded),
            if (onShift) _chip(tr('في وردية', 'On shift'), _green, Icons.access_time_filled_rounded),
          ]),
          if (d['badge'] != null) Padding(padding: const EdgeInsets.only(top: 6),
              child: Text('${tr('الشارة', 'Badge')}: ${d['badge']}', style: const TextStyle(color: _muted, fontSize: 12))),
        ])),
      ]),
    );
  }

  Widget _chip(String s, Color c, IconData ic) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(8)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [Icon(ic, size: 12, color: c), const SizedBox(width: 4),
          Text(s, style: TextStyle(color: c, fontSize: 10.5, fontWeight: FontWeight.w800))]),
      );

  Widget _kpis(Map st) {
    final items = [
      (tr('ورديات', 'Shifts'), st['shifts'], _blue, Icons.badge_rounded),
      (tr('دوريات', 'Patrols'), st['patrols'], _amber, Icons.directions_walk_rounded),
      (tr('مهام', 'Tasks'), st['tasks'], _green, Icons.task_alt_rounded),
      (tr('بلاغات', 'Incidents'), st['incidents'], _red, Icons.report_rounded),
    ];
    return Row(children: [
      for (final it in items) Expanded(child: Container(
        margin: const EdgeInsets.symmetric(horizontal: 3), padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(14), border: Border.all(color: const Color(0xFF20344E))),
        child: Column(children: [
          Icon(it.$4, color: it.$3, size: 18), const SizedBox(height: 5),
          Text('${it.$2 ?? 0}', style: TextStyle(color: it.$3, fontWeight: FontWeight.w900, fontSize: 18)),
          const SizedBox(height: 2),
          Text(it.$1, style: const TextStyle(color: _muted, fontSize: 9.5, fontWeight: FontWeight.w600)),
        ]),
      )),
    ]);
  }

  Widget _section(String title, IconData ic, Widget child, {Widget? trailing}) => Container(
        margin: const EdgeInsets.only(top: 12),
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(16), border: Border.all(color: const Color(0xFF20344E))),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(ic, size: 17, color: _blue), const SizedBox(width: 7),
            Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14)),
            const Spacer(), if (trailing != null) trailing,
          ]),
          const SizedBox(height: 10), child,
        ]),
      );

  Widget _details(Map d) => _section(tr('البيانات الشخصية', 'Personal details'), Icons.person_rounded, Column(children: [
        _row(Icons.credit_card_rounded, tr('الرقم المدني', 'Civil ID'), d['civil_id']),
        _row(Icons.flag_outlined, tr('الجنسية', 'Nationality'), d['nationality']),
        _row(Icons.phone_outlined, tr('الهاتف', 'Phone'), d['phone'], onTap: d['phone'] != null ? () => launchUrl(Uri.parse('tel:${d['phone']}')) : null),
        _row(Icons.email_outlined, tr('البريد', 'Email'), d['email']),
        _row(Icons.workspace_premium_outlined, tr('سنوات الخبرة', 'Experience (yrs)'), d['experience']),
        _row(Icons.verified_user_outlined, tr('رقم الرخصة', 'License no.'), d['license_number']),
        _row(Icons.event_busy_outlined, tr('انتهاء الرخصة', 'License expiry'), d['license_expiry']),
        _row(Icons.groups_rounded, tr('فِرَقي', 'My teams'), ((d['teams'] as List?) ?? const []).join(' · ')),
      ]));

  Widget _row(IconData ic, String label, dynamic val, {VoidCallback? onTap}) {
    if (val == null || '$val'.isEmpty) return const SizedBox.shrink();
    return InkWell(onTap: onTap, child: Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(children: [
        Icon(ic, size: 16, color: _muted), const SizedBox(width: 10),
        Text(label, style: const TextStyle(color: _muted, fontSize: 12.5)),
        const Spacer(),
        Flexible(child: Text('$val', textAlign: TextAlign.end, maxLines: 2, overflow: TextOverflow.ellipsis,
            style: TextStyle(color: onTap != null ? _blue : Colors.white, fontSize: 12.5, fontWeight: FontWeight.w600))),
      ]),
    ));
  }

  Color _certColor(String? s) => s == 'valid' ? _green : s == 'expiring' ? _amber : s == 'expired' ? _red : _muted;
  String _certLabel(String? s) => s == 'valid' ? tr('سارية', 'Valid') : s == 'expiring' ? tr('قرب الانتهاء', 'Expiring') : s == 'expired' ? tr('منتهية', 'Expired') : (s ?? '');

  Widget _certifications(List<Map> certs) {
    if (certs.isEmpty) return const SizedBox.shrink();
    final alert = certs.where((c) => c['state'] == 'expiring' || c['state'] == 'expired').length;
    return _section(tr('الشهادات والرخص', 'Certifications & licenses'), Icons.card_membership_rounded,
      Column(children: [for (final c in certs) _certCard(c)]),
      trailing: alert > 0 ? Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
          decoration: BoxDecoration(color: _red.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(8)),
          child: Text('$alert ${tr('تنبيه', 'alert')}', style: const TextStyle(color: _red, fontSize: 10, fontWeight: FontWeight.w800))) : null);
  }

  Widget _certCard(Map c) {
    final col = _certColor('${c['state']}');
    return Container(
      margin: const EdgeInsets.only(bottom: 8), padding: const EdgeInsets.all(11),
      decoration: BoxDecoration(color: const Color(0xFF0F1B2E), borderRadius: BorderRadius.circular(12),
          border: Border.all(color: col.withValues(alpha: 0.3))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Container(width: 4, height: 34, margin: const EdgeInsetsDirectional.only(end: 10),
              decoration: BoxDecoration(color: col, borderRadius: BorderRadius.circular(3))),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${c['name'] ?? ''}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 13)),
            if (c['type'] != null || c['authority'] != null)
              Text([c['type'], c['authority']].where((x) => x != null).join(' · '),
                  maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 10.5)),
          ])),
          Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(color: col.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(8)),
              child: Text(_certLabel('${c['state']}'), style: TextStyle(color: col, fontSize: 9.5, fontWeight: FontWeight.w800))),
        ]),
        const SizedBox(height: 6),
        Row(children: [
          if (c['number'] != null) Text('#${c['number']}', style: const TextStyle(color: Color(0xFF6B7F9A), fontSize: 10.5)),
          const Spacer(),
          if (c['expiry'] != null) Text('${tr('ينتهي', 'Exp')}: ${c['expiry']}', style: TextStyle(color: col, fontSize: 10.5, fontWeight: FontWeight.w700)),
        ]),
      ]),
    );
  }

  Widget _skills(List<Map> skills) {
    if (skills.isEmpty) return const SizedBox.shrink();
    return _section(tr('المهارات', 'Skills'), Icons.psychology_rounded,
      Wrap(spacing: 8, runSpacing: 8, children: [
        for (final s in skills) Container(
          padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 7),
          decoration: BoxDecoration(color: _blue.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20), border: Border.all(color: _blue.withValues(alpha: 0.3))),
          child: Text('${s['name'] ?? ''}', style: const TextStyle(color: _blue, fontSize: 12, fontWeight: FontWeight.w700)),
        ),
      ]));
  }

  Widget _equipment(List<Map> equip) {
    if (equip.isEmpty) return const SizedBox.shrink();
    return _section(tr('المعدّات بعهدتي', 'Equipment custody'), Icons.inventory_2_rounded,
      Column(children: [for (final e in equip) Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(children: [
          Container(width: 34, height: 34, decoration: BoxDecoration(color: const Color(0xFF223349), borderRadius: BorderRadius.circular(9)),
              child: const Icon(Icons.radar_rounded, color: _muted, size: 17)),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${e['name'] ?? ''}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 12.5)),
            Text([e['category'], if (e['serial'] != null) '#${e['serial']}'].where((x) => x != null).join(' · '),
                style: const TextStyle(color: _muted, fontSize: 10.5)),
          ])),
          if (e['expiry'] != null) Text('${e['expiry']}', style: const TextStyle(color: Color(0xFF6B7F9A), fontSize: 10)),
        ]),
      )]));
  }
}
