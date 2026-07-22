import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/widgets.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'pms_shell.dart';
import 'pms_section.dart' show PmsPhotoView;

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
          return ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 24), children: [
            _identity(e),
            const SizedBox(height: 14),
            if (compliance.isNotEmpty) ...[_compliance(compliance), const SizedBox(height: 14)],
            // professional sections hub — each opens its own detail
            _sectionsHub(d),
            const SizedBox(height: 14),
            if (((d['details'] as List?) ?? const []).isNotEmpty) ...[
              _miniHead(tr('كل بيانات العامل', 'All employee data'), Icons.badge_rounded),
              const SizedBox(height: 8),
              _detailsSection(d['details'] as List)],
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
          // status marks (worker status / on-leave airplane) + tags
          if (((e['marks'] as List?) ?? const []).isNotEmpty || ((e['tags'] as List?) ?? const []).isNotEmpty) ...[
            Wrap(spacing: 6, runSpacing: 6, children: [
              for (final m in (e['marks'] as List? ?? const [])) _markChip(m as Map),
              for (final t in (e['tags'] as List? ?? const [])) _tagChip('${(t as Map)['name']}'),
            ]),
            const SizedBox(height: 10),
          ],
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

  static const _markIcons = {
    'flight': Icons.flight_rounded, 'badge': Icons.badge_rounded,
    'gavel': Icons.gavel_rounded, 'block': Icons.block_rounded,
  };

  Widget _markChip(Map m) {
    final c = _hex('${m['color'] ?? '#6B7280'}');
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20),
          boxShadow: [BoxShadow(color: Colors.black.withValues(alpha: 0.12), blurRadius: 3)]),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(_markIcons['${m['icon']}'] ?? Icons.circle, size: 13, color: c),
        const SizedBox(width: 4),
        Text('${m['label']}', style: TextStyle(color: c, fontSize: 10.5, fontWeight: FontWeight.w900)),
      ]),
    );
  }

  Widget _tagChip(String t) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
        decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.18),
            borderRadius: BorderRadius.circular(20), border: Border.all(color: Colors.white38)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          const Icon(Icons.sell_rounded, size: 11, color: Colors.white70),
          const SizedBox(width: 4),
          Text(t, style: const TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.w700)),
        ]),
      );

  static Color _hex(String h) {
    h = h.replaceAll('#', '');
    if (h.length == 6) h = 'FF$h';
    return Color(int.tryParse(h, radix: 16) ?? 0xFF6B7280);
  }

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

  Widget _miniHead(String t, IconData ic) => Row(children: [
        Icon(ic, size: 17, color: _c),
        const SizedBox(width: 7),
        Text(t, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14.5, color: Pms.ink)),
      ]);

  // (key, label, icon, color, type)
  static const List<(String, String, IconData, Color, String)> _secDefs = [
    ('attendance', 'الحضور والانصراف', Icons.schedule_rounded, Color(0xFF2563EB), 'attendance'),
    ('leaves', 'الإجازات', Icons.beach_access_rounded, Color(0xFF0891B2), 'leaves'),
    ('transfers', 'الانتقالات', Icons.swap_horiz_rounded, Color(0xFF7C3AED), 'transfers'),
    ('documents', 'المستندات والصور', Icons.folder_shared_rounded, Color(0xFFB45309), 'documents'),
    ('docs', 'طلبات المستندات', Icons.description_rounded, Color(0xFF8B5CF6), 'docs'),
    ('payslips', 'كشوف الرواتب', Icons.receipt_long_rounded, Color(0xFF16A34A), 'payslips'),
    ('loans', 'السُّلف', Icons.savings_rounded, Color(0xFF0D9488), 'loans'),
    ('penalties', 'الجزاءات', Icons.gavel_rounded, Color(0xFFE5484D), 'money'),
    ('bonuses', 'المكافآت', Icons.emoji_events_rounded, Color(0xFFF59E0B), 'money'),
    ('appraisals', 'التقييمات', Icons.star_rounded, Color(0xFFEA580C), 'appraisals'),
    ('skills', 'المهارات', Icons.psychology_rounded, Color(0xFF6366F1), 'skills'),
    ('uniform', 'اليونيفورم', Icons.checkroom_rounded, Color(0xFF0EA5E9), 'uniform'),
    ('vehicles', 'السيارات', Icons.directions_car_rounded, Color(0xFF334155), 'vehicles'),
    ('violations', 'المخالفات المرورية', Icons.report_rounded, Color(0xFFDC2626), 'violations'),
    ('devices', 'أجهزة البصمة', Icons.fingerprint_rounded, Color(0xFF475569), 'devices'),
  ];

  Widget _sectionsHub(Map d) {
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      _miniHead(tr('سجلات العامل', 'Employee records'), Icons.dashboard_rounded),
      const SizedBox(height: 8),
      GridView.count(
        crossAxisCount: 3, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
        mainAxisSpacing: 9, crossAxisSpacing: 9, childAspectRatio: 0.95,
        children: [
          for (final s in _secDefs)
            _hubTile(s.$2, s.$3, s.$4, s.$5, ((d[s.$1] as List?) ?? const []).length,
                (d[s.$1] as List?) ?? const []),
        ],
      ),
    ]);
  }

  Widget _hubTile(String label, IconData ic, Color c, String type, int count, List items) {
    final empty = count == 0;
    return Material(
      color: Colors.white, borderRadius: BorderRadius.circular(15),
      child: InkWell(
        borderRadius: BorderRadius.circular(15),
        onTap: () => _openSection(label, type, items, c),
        child: Container(
          padding: const EdgeInsets.all(9),
          decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(15),
              border: Border.all(color: c.withValues(alpha: 0.16)),
              boxShadow: [BoxShadow(color: c.withValues(alpha: 0.07), blurRadius: 7, offset: const Offset(0, 3))]),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(children: [
                Container(width: 30, height: 30, alignment: Alignment.center,
                  decoration: BoxDecoration(
                      gradient: LinearGradient(colors: [c, Color.lerp(c, Colors.black, 0.22)!]),
                      borderRadius: BorderRadius.circular(9)),
                  child: Icon(ic, size: 16, color: Colors.white)),
                const Spacer(),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                  decoration: BoxDecoration(
                      color: empty ? const Color(0xFFF1F5F9) : c.withValues(alpha: 0.13),
                      borderRadius: BorderRadius.circular(10)),
                  child: Text('$count', style: TextStyle(
                      color: empty ? Pms.slate : c, fontWeight: FontWeight.w900, fontSize: 12)),
                ),
              ]),
              Text(label, maxLines: 2, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w800, color: Pms.ink, height: 1.2)),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _openSection(String title, String type, List items, Color c) async {
    await showModalBottomSheet(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (_) => _EmpSectionSheet(title: title, type: type, items: items, color: c,
          employeeId: widget.employeeId),
    );
  }

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

}

/// Bottom sheet listing one section's records, formatted per type.
class _EmpSectionSheet extends StatelessWidget {
  final String title, type;
  final List items;
  final Color color;
  final int employeeId;
  const _EmpSectionSheet({required this.title, required this.type, required this.items,
      required this.color, required this.employeeId});

  Color _stateColor(String s) {
    final l = s.toLowerCase();
    if (l.contains('done') || l.contains('approve') || l.contains('valid') || l.contains('paid') || l.contains('confirm')) return Pms.green;
    if (l.contains('reject') || l.contains('cancel') || l.contains('refuse')) return Pms.red;
    if (l.contains('draft') || l.contains('submit') || l.contains('pending') || l.contains('wait')) return Pms.amber;
    return Pms.slate;
  }

  @override
  Widget build(BuildContext context) {
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.75, maxChildSize: 0.95, minChildSize: 0.4,
      builder: (_, sc) => Column(children: [
        Container(width: 40, height: 4, margin: const EdgeInsets.symmetric(vertical: 11),
            decoration: BoxDecoration(color: Colors.grey.shade300, borderRadius: BorderRadius.circular(4))),
        Padding(
          padding: const EdgeInsets.fromLTRB(18, 0, 18, 10),
          child: Row(children: [
            Icon(Icons.folder_open_rounded, color: color),
            const SizedBox(width: 8),
            Text(title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
            const Spacer(),
            Text('${items.length}', style: TextStyle(fontWeight: FontWeight.w900, color: color, fontSize: 15)),
          ]),
        ),
        Expanded(child: items.isEmpty
            ? Center(child: Padding(padding: const EdgeInsets.all(30),
                child: Text(tr('لا سجلات في هذا القسم', 'No records'), style: const TextStyle(color: Pms.slate))))
            : ListView.builder(controller: sc, padding: const EdgeInsets.fromLTRB(14, 0, 14, 24),
                itemCount: items.length,
                itemBuilder: (_, i) => _card(context, items[i] as Map))),
      ]),
    );
  }

  Widget _wrap(List<Widget> children) => Container(
        margin: const EdgeInsets.only(bottom: 9),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(13),
            border: Border.all(color: const Color(0xFFE5E7EB))),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: children),
      );

  Widget _titleRow(String t, {String? trailing, Color? tc}) => Row(children: [
        Expanded(child: Text(t, style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13.5))),
        if (trailing != null)
          Container(padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
              decoration: BoxDecoration(color: (tc ?? Pms.slate).withValues(alpha: 0.13), borderRadius: BorderRadius.circular(14)),
              child: Text(trailing, style: TextStyle(color: tc ?? Pms.slate, fontWeight: FontWeight.w800, fontSize: 11))),
      ]);

  Widget _kv(String k, String v, {Color? vc}) => Padding(
        padding: const EdgeInsets.only(top: 4),
        child: Row(children: [
          Text('$k: ', style: const TextStyle(fontSize: 11.5, color: Pms.slate, fontWeight: FontWeight.w600)),
          Expanded(child: Text(v, style: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w700, color: vc ?? Pms.ink))),
        ]),
      );

  Widget _card(BuildContext context, Map m) {
    switch (type) {
      case 'leaves':
        final ret = m['returned'];
        return _wrap([
          _titleRow('${m['type'] ?? tr('إجازة', 'Leave')}',
              trailing: '${m['state_label'] ?? ''}', tc: _stateColor('${m['state']}')),
          _kv(tr('من', 'From'), '${m['from'] ?? '—'}'),
          _kv(tr('إلى', 'To'), '${m['to'] ?? '—'}'),
          _kv(tr('الأيام', 'Days'), '${m['days']}'),
          _kv(tr('العودة', 'Returned'), ret != null ? '$ret' : tr('لم يُسجّل', 'not recorded'),
              vc: ret != null ? Pms.green : Pms.amber),
        ]);
      case 'transfers':
        return _wrap([
          _titleRow(tr('نقل', 'Transfer'), trailing: '${m['state_label'] ?? ''}', tc: _stateColor('${m['state']}')),
          _kv(tr('من قسم', 'From'), '${m['from'] ?? '—'}'),
          _kv(tr('إلى قسم', 'To'), '${m['to'] ?? '—'}'),
          _kv(tr('التاريخ', 'Date'), '${m['date'] ?? '—'}'),
        ]);
      case 'documents':
        final imgs = (m['images'] as List?) ?? const [];
        final days = m['days'];
        final expColor = days == null ? Pms.slate : (days < 0 ? Pms.red : days < 30 ? Pms.amber : Pms.green);
        return _wrap([
          _titleRow('${m['type'] ?? tr('مستند', 'Document')}'),
          if (m['number'] != null) _kv(tr('الرقم', 'No.'), '${m['number']}'),
          if (m['issue'] != null) _kv(tr('الإصدار', 'Issued'), '${m['issue']}'),
          if (m['expiry'] != null) _kv(tr('الانتهاء', 'Expiry'),
              '${m['expiry']}${days != null ? '  (${days < 0 ? tr('منتهٍ', 'expired') : '$days ${tr('يوم', 'd')}'})' : ''}', vc: expColor),
          if (imgs.isNotEmpty) Padding(padding: const EdgeInsets.only(top: 8), child: Wrap(spacing: 8, runSpacing: 8, children: [
            for (final im in imgs) GestureDetector(
              onTap: () => Navigator.push(context, MaterialPageRoute(
                  builder: (_) => PmsPhotoView(url: '$im', title: '${m['type'] ?? ''}'))),
              child: ClipRRect(borderRadius: BorderRadius.circular(9),
                  child: Image.network('$im', width: 78, height: 78, fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => Container(width: 78, height: 78, color: Pms.bg,
                          child: const Icon(Icons.insert_drive_file_rounded, color: Pms.slate)))),
            ),
          ])),
        ]);
      case 'payslips':
        return _wrap([
          _titleRow('${m['name'] ?? tr('كشف راتب', 'Payslip')}',
              trailing: '${m['state_label'] ?? ''}', tc: _stateColor('${m['state']}')),
          _kv(tr('الفترة', 'Period'), '${m['from'] ?? ''} → ${m['to'] ?? ''}'),
          if (m['net'] != null) _kv(tr('الصافي', 'Net'), '${m['net']}', vc: Pms.green),
        ]);
      case 'appraisals':
        return _wrap([
          _titleRow(tr('تقييم', 'Appraisal'), trailing: '${m['state_label'] ?? ''}', tc: _stateColor('${m['state']}')),
          if (m['date'] != null) _kv(tr('التاريخ', 'Date'), '${m['date']}'),
          if (m['score'] != null) _kv(tr('النتيجة', 'Score'), '${m['score']}', vc: color),
        ]);
      case 'skills':
        final p = (m['progress'] is num) ? (m['progress'] as num).toDouble() : null;
        return _wrap([
          _titleRow('${m['name'] ?? ''}', trailing: m['level'] != null ? '${m['level']}' : null, tc: color),
          if (p != null) Padding(padding: const EdgeInsets.only(top: 8),
              child: ClipRRect(borderRadius: BorderRadius.circular(4),
                  child: LinearProgressIndicator(value: (p / 100).clamp(0, 1), minHeight: 7,
                      backgroundColor: Pms.bg, valueColor: AlwaysStoppedAnimation(color)))),
        ]);
      case 'uniform':
        return _wrap([
          _titleRow('${m['type'] ?? tr('يونيفورم', 'Uniform')}',
              trailing: m['signed'] == true ? tr('موقّع', 'signed') : null, tc: Pms.green),
          if (m['date'] != null) _kv(tr('التاريخ', 'Date'), '${m['date']}'),
        ]);
      case 'vehicles':
        return _wrap([
          _titleRow('${m['plate'] ?? m['model'] ?? tr('مركبة', 'Vehicle')}'),
          if (m['model'] != null) _kv(tr('الطراز', 'Model'), '${m['model']}'),
        ]);
      case 'violations':
        return _wrap([
          _titleRow('${m['type'] ?? tr('مخالفة', 'Violation')}',
              trailing: '${m['state_label'] ?? ''}', tc: _stateColor('${m['state']}')),
          if (m['date'] != null) _kv(tr('التاريخ', 'Date'), '${m['date']}'),
          if (m['vehicle'] != null) _kv(tr('المركبة', 'Vehicle'), '${m['vehicle']}'),
          if (m['amount'] != null) _kv(tr('المبلغ', 'Amount'), '${m['amount']}', vc: Pms.red),
        ]);
      case 'devices':
        return _wrap([
          _titleRow('${m['device'] ?? tr('جهاز بصمة', 'Device')}'),
          if (m['uid'] != null) _kv(tr('معرّف المستخدم', 'UID'), '${m['uid']}'),
          if (m['templates'] != null) _kv(tr('البصمات', 'Templates'), '${m['templates']}'),
        ]);
      case 'attendance':
        return _wrap([
          _titleRow('${m['date'] ?? ''}',
              trailing: m['open'] == true ? tr('بالموقع', 'on site') : '${m['hours']} ${tr('س', 'h')}',
              tc: m['open'] == true ? Pms.green : color),
          _kv(tr('دخول', 'In'), '${m['check_in'] ?? '—'}'),
          _kv(tr('خروج', 'Out'), '${m['check_out'] ?? '—'}'),
        ]);
      default: // money (loans/penalties/bonuses), docs
        return _wrap([
          _titleRow('${m['name'] ?? ''}',
              trailing: m['state_label'] != null ? '${m['state_label']}' : null, tc: _stateColor('${m['state']}')),
          for (final k in ['amount', 'loan_amount', 'balance_amount', 'total_amount'])
            if (m[k] != null) _kv(k == 'balance_amount' ? tr('المتبقّي', 'Balance') : tr('المبلغ', 'Amount'), '${m[k]}',
                vc: k == 'balance_amount' ? Pms.red : Pms.ink),
        ]);
    }
  }
}
