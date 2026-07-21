import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/widgets.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import '../../core/service_ui.dart';
import 'pms_shell.dart';

/// The employee file a project manager sees: identity, wage, compliance dates,
/// docs, loans, penalties, bonuses and recent attendance. Server-scoped to the
/// manager's own project departments.
class PmsEmployeeFileScreen extends StatefulWidget {
  const PmsEmployeeFileScreen({super.key, required this.employeeId, required this.name});
  final int employeeId;
  final String name;
  @override
  State<PmsEmployeeFileScreen> createState() => _PmsEmployeeFileScreenState();
}

class _PmsEmployeeFileScreenState extends State<PmsEmployeeFileScreen> {
  Future<Map<String, dynamic>>? _f;
  static const _c = Color(0xFF0D9488);

  @override
  void initState() {
    super.initState();
    _f = context.read<AuthProvider>().api.pmsEmployeeFile(widget.employeeId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Pms.bg,
      appBar: AppBar(
        backgroundColor: _c, foregroundColor: Colors.white, elevation: 0,
        title: Text(widget.name, overflow: TextOverflow.ellipsis),
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _f,
        builder: (_, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return Center(child: Padding(
              padding: const EdgeInsets.all(30),
              child: Text('${snap.error}', textAlign: TextAlign.center,
                  style: const TextStyle(color: Colors.grey)),
            ));
          }
          final d = snap.data ?? const {};
          final e = (d['employee'] as Map?) ?? const {};
          final compliance = (d['compliance'] as List?) ?? const [];
          final docs = (d['docs'] as List?) ?? const [];
          final loans = (d['loans'] as List?) ?? const [];
          final penalties = (d['penalties'] as List?) ?? const [];
          final bonuses = (d['bonuses'] as List?) ?? const [];
          final att = (d['attendance'] as List?) ?? const [];
          return ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
            _identity(e),
            const SizedBox(height: 12),
            if (((d['details'] as List?) ?? const []).isNotEmpty) ...[
              _detailsSection(d['details'] as List), const SizedBox(height: 0)],
            if (compliance.isNotEmpty) ...[_compliance(compliance), const SizedBox(height: 12)],
            _recordBlock(tr('طلبات المستندات', 'Document requests'), Icons.description_rounded,
                const Color(0xFF8B5CF6), docs, showState: true),
            _recordBlock(tr('السُّلف', 'Loans'), Icons.savings_rounded,
                const Color(0xFF0891B2), loans, amountKey: 'amount'),
            _recordBlock(tr('الجزاءات', 'Penalties'), Icons.gavel_rounded,
                const Color(0xFFE5484D), penalties, amountKey: 'amount', showState: true),
            _recordBlock(tr('المكافآت', 'Bonuses'), Icons.emoji_events_rounded,
                const Color(0xFF16A34A), bonuses, amountKey: 'amount', showState: true),
            if (att.isNotEmpty) ...[const SizedBox(height: 4), _attendance(att)],
          ]);
        },
      ),
    );
  }

  Widget _identity(Map e) => Container(
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: [_c, Color.lerp(_c, Colors.black, 0.3)!],
              begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.circular(18),
        ),
        child: Column(children: [
          Row(children: [
            CircleAvatar(
              radius: 30, backgroundColor: Colors.white.withValues(alpha: 0.18),
              backgroundImage: avatarImage(e['photo'] as String?),
              child: e['photo'] == null
                  ? Text('${e['name']}'.characters.first,
                      style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w900))
                  : null,
            ),
            const SizedBox(width: 13),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${e['name']}', style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
              if (e['job'] != null)
                Text('${e['job']}', style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12.5, fontWeight: FontWeight.w600)),
              if (e['department'] != null)
                Text('${e['department']}', style: TextStyle(color: Colors.white.withValues(alpha: 0.65), fontSize: 10.5)),
              if (e['duty_label'] != null) Padding(
                padding: const EdgeInsets.only(top: 6),
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
                  decoration: BoxDecoration(
                      color: e['duty'] == 'on_site' ? const Color(0xFF16A34A)
                          : e['duty'] == 'attended' ? const Color(0xFF0891B2) : Colors.white24,
                      borderRadius: BorderRadius.circular(20)),
                  child: Row(mainAxisSize: MainAxisSize.min, children: [
                    Icon(e['duty'] == 'off' ? Icons.person_off_rounded : Icons.fmd_good_rounded,
                        size: 11, color: Colors.white),
                    const SizedBox(width: 4),
                    Text('${e['duty_label']}',
                        style: const TextStyle(color: Colors.white, fontSize: 10, fontWeight: FontWeight.w800)),
                  ]),
                ),
              ),
            ])),
          ]),
          const SizedBox(height: 12),
          // contact quick-actions
          Row(children: [
            if (e['phone'] != null || e['mobile'] != null) ...[
              _quickBtn(Icons.call_rounded, tr('اتصال', 'Call'),
                  () => _launch('tel:${e['mobile'] ?? e['phone']}')),
              const SizedBox(width: 8),
              _quickBtn(Icons.chat_rounded, 'واتساب',
                  () => _launch('https://wa.me/${'${e['mobile'] ?? e['phone']}'.replaceAll(RegExp(r'[^0-9]'), '')}')),
            ],
            if (e['email'] != null) ...[
              const SizedBox(width: 8),
              _quickBtn(Icons.email_rounded, tr('بريد', 'Email'), () => _launch('mailto:${e['email']}')),
            ],
          ]),
          const SizedBox(height: 12),
          // Important data — badge highlighted, no manager.
          Wrap(spacing: 8, runSpacing: 8, children: [
            if (e['badge'] != null) _badgeChip('${e['badge']}'),
            if (e['civil'] != null) _chip(Icons.credit_card_rounded, tr('مدني: ${e['civil']}', 'Civil: ${e['civil']}')),
            if (e['nationality'] != null) _chip(Icons.public_rounded, '${e['nationality']}'),
            if (e['residency_end'] != null) _chip(Icons.event_busy_rounded, tr('الإقامة: ${e['residency_end']}', 'Residency: ${e['residency_end']}')),
            if (e['wage'] != null) _chip(Icons.payments_rounded, tr('الأجر: ${e['wage']}', 'Wage: ${e['wage']}')),
          ]),
        ]),
      );

  /// The Badge ID — the worker's key identifier, given a distinct, prominent pill.
  Widget _badgeChip(String badge) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
        decoration: BoxDecoration(
            color: Colors.white, borderRadius: BorderRadius.circular(10),
            boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.12), blurRadius: 4, offset: const Offset(0, 2))]),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(Icons.badge_rounded, size: 14, color: _c),
          const SizedBox(width: 5),
          Text(tr('بادج', 'Badge'), style: TextStyle(color: _c.withValues(alpha: 0.7), fontSize: 9.5, fontWeight: FontWeight.w700)),
          const SizedBox(width: 4),
          Text(badge, style: TextStyle(color: _c, fontSize: 13, fontWeight: FontWeight.w900, letterSpacing: 0.5)),
        ]),
      );

  Widget _detailsSection(List sections) => Column(children: [
        for (final s in sections.cast<Map>()) Container(
          margin: const EdgeInsets.only(bottom: 12),
          decoration: BoxDecoration(
              color: Colors.white, borderRadius: BorderRadius.circular(14),
              border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
          clipBehavior: Clip.antiAlias,
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              width: double.infinity,
              padding: const EdgeInsets.fromLTRB(13, 10, 13, 9),
              decoration: BoxDecoration(border: Border(bottom: BorderSide(color: Colors.grey.shade100))),
              child: Text('${s['title']}',
                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: _c)),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(13, 4, 13, 10),
              child: Column(children: [
                for (final f in ((s['fields'] as List?) ?? const []).cast<Map>())
                  _detailRow('${f['label']}', '${f['value']}',
                      highlight: '${f['label']}'.contains('بادج')),
              ]),
            ),
          ]),
        ),
      ]);

  Widget _detailRow(String label, String value, {bool highlight = false}) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6.5),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 118, child: Text(label,
              style: const TextStyle(color: Pms.slate, fontSize: 12))),
          const SizedBox(width: 8),
          Expanded(child: highlight
              ? Align(alignment: AlignmentDirectional.centerStart, child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(color: _c.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(7)),
                  child: Text(value, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: _c, letterSpacing: 0.5))))
              : Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: Pms.ink))),
        ]),
      );

  Future<void> _launch(String uri) async {
    try {
      await launchUrl(Uri.parse(uri), mode: LaunchMode.externalApplication);
    } catch (_) {}
  }

  Widget _quickBtn(IconData ic, String label, VoidCallback onTap) => Expanded(
        child: Material(
          color: Colors.white.withValues(alpha: 0.18),
          borderRadius: BorderRadius.circular(11),
          child: InkWell(
            borderRadius: BorderRadius.circular(11),
            onTap: onTap,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 9),
              child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                Icon(ic, size: 15, color: Colors.white),
                const SizedBox(width: 6),
                Text(label, style: const TextStyle(color: Colors.white, fontSize: 11.5, fontWeight: FontWeight.w800)),
              ]),
            ),
          ),
        ),
      );

  Widget _chip(IconData ic, String t) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
        decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(9)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(ic, size: 12, color: Colors.white),
          const SizedBox(width: 5),
          Text(t, style: const TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.w700)),
        ]),
      );

  Widget _compliance(List items) => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.white, borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(Icons.verified_user_rounded, size: 15, color: Color(0xFFE5484D)),
            SizedBox(width: 6),
            Text(tr('الوثائق والامتثال', 'Documents & compliance'), style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: Pms.ink)),
          ]),
          const SizedBox(height: 10),
          for (final i in items) Builder(builder: (_) {
            final days = (i['days'] ?? 0) as int;
            final c = days < 0 ? const Color(0xFFE5484D)
                : days <= 60 ? const Color(0xFFF7A23B) : const Color(0xFF16A34A);
            return Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(children: [
                Container(width: 8, height: 8, decoration: BoxDecoration(color: c, shape: BoxShape.circle)),
                const SizedBox(width: 8),
                Expanded(child: Text('${i['label']}',
                    style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700))),
                Text('${i['date']}', style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                  decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(7)),
                  child: Text(
                      days < 0 ? tr('منتهية ${-days} يوم', '${-days}d ago')
                               : tr('$days يوم', '${days}d'),
                      style: TextStyle(fontSize: 9.5, fontWeight: FontWeight.w900, color: c)),
                ),
              ]),
            );
          }),
        ]),
      );

  Widget _recordBlock(String title, IconData ic, Color c, List rows,
      {String? amountKey, bool showState = false}) {
    if (rows.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.white, borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(ic, size: 15, color: c),
            const SizedBox(width: 6),
            Text(title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: Pms.ink)),
            const SizedBox(width: 6),
            Text('${rows.length}', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: c)),
          ]),
          const SizedBox(height: 8),
          for (final r in rows) Padding(
            padding: const EdgeInsets.symmetric(vertical: 4),
            child: Row(children: [
              Expanded(child: Text('${r['name']}',
                  maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700))),
              if (amountKey != null && r[amountKey] != null)
                Text('${r[amountKey]}',
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w900, color: c)),
              if (showState && r['state_label'] != null) ...[
                const SizedBox(width: 6),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                  decoration: BoxDecoration(color: c.withValues(alpha: 0.1), borderRadius: BorderRadius.circular(6)),
                  child: Text('${r['state_label']}',
                      style: TextStyle(fontSize: 8.5, fontWeight: FontWeight.w800, color: c)),
                ),
              ],
            ]),
          ),
        ]),
      ),
    );
  }

  Widget _attendance(List att) => Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: Colors.white, borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(Icons.schedule_rounded, size: 15, color: Color(0xFF2F6DF6)),
            SizedBox(width: 6),
            Text(tr('آخر الحضور', 'Recent attendance'), style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: Pms.ink)),
          ]),
          const SizedBox(height: 4),
          // The file lists the last 30 punches; paging keeps it readable.
          MoreList(
            items: att,
            color: const Color(0xFF2F6DF6),
            pageSize: 7,
            itemBuilder: (_, r, __) {
              final m = r as Map;
              return Padding(
                padding: const EdgeInsets.symmetric(vertical: 4),
                child: Row(children: [
                  Container(width: 7, height: 7,
                      decoration: BoxDecoration(
                          color: m['open'] == true ? const Color(0xFF16A34A) : Colors.grey.shade400,
                          shape: BoxShape.circle)),
                  const SizedBox(width: 8),
                  Expanded(child: Text('${m['date'] ?? '—'}',
                      style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700))),
                  Text('${_hm(m['check_in'])} → ${_hm(m['check_out'])}',
                      style: TextStyle(fontSize: 10.5, color: Colors.grey.shade600)),
                  const SizedBox(width: 8),
                  Text(tr('${m['hours']} س', '${m['hours']}h'),
                      style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: Color(0xFF0891B2))),
                ]),
              );
            },
          ),
        ]),
      );

  String _hm(dynamic v) {
    final s = '${v ?? ''}';
    return s.length >= 16 ? s.substring(11, 16) : '—';
  }
}
