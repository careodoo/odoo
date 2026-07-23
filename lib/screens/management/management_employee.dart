import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'management_home.dart' show Mgmt;

/// The rich employee file for the Management back-office: every readable field
/// grouped into professional sections, and every related sub-module (contracts,
/// allowances, work-commencement, end-of-service, leaves, payslips, penalties…)
/// as an expandable card. Mirrors the depth of the PMS employee file.
class ManagementEmployeeScreen extends StatefulWidget {
  final int employeeId;
  final String name;
  final Color accent;
  const ManagementEmployeeScreen({super.key, required this.employeeId, required this.name, required this.accent});
  @override
  State<ManagementEmployeeScreen> createState() => _ManagementEmployeeScreenState();
}

class _ManagementEmployeeScreenState extends State<ManagementEmployeeScreen> {
  late Future<Map<String, dynamic>> _f;

  @override
  void initState() {
    super.initState();
    _f = context.read<AuthProvider>().api.managementEmployeeFull(widget.employeeId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Mgmt.bg,
      appBar: AppBar(
        backgroundColor: widget.accent, foregroundColor: Colors.white, elevation: 0,
        title: Text(widget.name, overflow: TextOverflow.ellipsis),
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _f,
        builder: (_, snap) {
          if (snap.hasError) {
            return Center(child: Padding(padding: const EdgeInsets.all(30),
                child: Text('${snap.error}', textAlign: TextAlign.center, style: const TextStyle(color: Mgmt.slate))));
          }
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final d = snap.data!;
          final sections = (d['sections'] as List?) ?? const [];
          final related = (d['related'] as List?) ?? const [];
          return ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 28), children: [
            _identity(d),
            const SizedBox(height: 14),
            if (related.isNotEmpty) ...[
              _miniHead(tr('السجلات والمديولات', 'Records & modules'), Icons.widgets_rounded),
              const SizedBox(height: 8),
              for (final r in related.cast<Map>()) _relatedCard(r),
              const SizedBox(height: 6),
            ],
            _miniHead(tr('كل بيانات العامل', 'All employee data'), Icons.badge_rounded),
            const SizedBox(height: 8),
            for (final s in sections.cast<Map>()) _sectionCard(s),
          ]);
        },
      ),
    );
  }

  Widget _identity(Map d) => Container(
        padding: const EdgeInsets.all(15),
        decoration: BoxDecoration(
          gradient: LinearGradient(colors: [widget.accent, Color.lerp(widget.accent, Colors.black, 0.3)!],
              begin: Alignment.topRight, end: Alignment.bottomLeft),
          borderRadius: BorderRadius.circular(18),
        ),
        child: Column(children: [
          Row(children: [
            CircleAvatar(
              radius: 30, backgroundColor: Colors.white24,
              backgroundImage: d['avatar'] != null ? NetworkImage('${d['avatar']}') : null,
              onBackgroundImageError: (_, __) {},
              child: d['avatar'] == null
                  ? Text('${d['name']}'.characters.first, style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.w900))
                  : null,
            ),
            const SizedBox(width: 13),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text('${d['name']}', style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w900)),
              if (d['job'] != null) Text('${d['job']}', style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12.5, fontWeight: FontWeight.w600)),
              if (d['department'] != null) Text('${d['department']}', style: TextStyle(color: Colors.white.withValues(alpha: 0.65), fontSize: 10.5)),
            ])),
          ]),
          const SizedBox(height: 12),
          Row(children: [
            if (d['work_phone'] != null) ...[
              _quick(Icons.call_rounded, tr('اتصال', 'Call'), () => _launch('tel:${d['work_phone']}')),
              const SizedBox(width: 8),
              _quick(Icons.chat_rounded, 'واتساب', () => _launch('https://wa.me/${'${d['work_phone']}'.replaceAll(RegExp(r'[^0-9]'), '')}')),
            ],
            if (d['work_email'] != null) ...[
              const SizedBox(width: 8),
              _quick(Icons.email_rounded, tr('بريد', 'Email'), () => _launch('mailto:${d['work_email']}')),
            ],
          ]),
          if (d['badge'] != null) Padding(padding: const EdgeInsets.only(top: 12),
            child: Align(alignment: AlignmentDirectional.centerStart, child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(10)),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                const Icon(Icons.badge_rounded, size: 13, color: Colors.white),
                const SizedBox(width: 5),
                Text('${d['badge']}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, letterSpacing: 0.4)),
              ]),
            )),
          ),
        ]),
      );

  Widget _quick(IconData ic, String t, VoidCallback onTap) => Expanded(
        child: Material(color: Colors.white.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(11),
          child: InkWell(borderRadius: BorderRadius.circular(11), onTap: onTap,
            child: Padding(padding: const EdgeInsets.symmetric(vertical: 8),
              child: Column(children: [Icon(ic, color: Colors.white, size: 18),
                Text(t, style: const TextStyle(color: Colors.white, fontSize: 9.5, fontWeight: FontWeight.w700))]))),
        ),
      );

  Widget _miniHead(String t, IconData ic) => Row(children: [
        Icon(ic, size: 17, color: widget.accent),
        const SizedBox(width: 7),
        Text(t, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: widget.accent)),
      ]);

  Widget _relatedCard(Map r) {
    final rows = (r['rows'] as List?) ?? const [];
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
      clipBehavior: Clip.antiAlias,
      child: Theme(
        data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
        child: ExpansionTile(
          tilePadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 2),
          childrenPadding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
          leading: Text('${r['icon'] ?? '📋'}', style: const TextStyle(fontSize: 20)),
          title: Text(gLang == 'en' ? '${r['en']}' : '${r['ar']}',
              style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 13, color: Mgmt.ink)),
          trailing: Container(
            padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
            decoration: BoxDecoration(color: widget.accent.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(20)),
            child: Text('${r['count']}', style: TextStyle(color: widget.accent, fontWeight: FontWeight.w900, fontSize: 12)),
          ),
          children: [for (final row in rows.cast<Map>()) _relRow(row)],
        ),
      ),
    );
  }

  Widget _relRow(Map row) => Container(
        margin: const EdgeInsets.only(bottom: 6),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(color: Mgmt.bg, borderRadius: BorderRadius.circular(10)),
        child: Row(children: [
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${row['title']}', maxLines: 2, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: Mgmt.ink)),
            if (row['subtitle'] != null || row['date'] != null)
              Padding(padding: const EdgeInsets.only(top: 2),
                child: Text([if (row['subtitle'] != null) '${row['subtitle']}', if (row['date'] != null) '${row['date']}'].join('  ·  '),
                    style: const TextStyle(color: Mgmt.slate, fontSize: 10.5))),
          ])),
          if (row['amount'] != null) Padding(padding: const EdgeInsets.only(left: 8),
            child: Text('${row['amount']}', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 12.5, color: widget.accent))),
          if (row['state'] != null) Container(
            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
            decoration: BoxDecoration(color: widget.accent.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(7)),
            child: Text('${row['state']}', style: TextStyle(color: widget.accent, fontSize: 9, fontWeight: FontWeight.w800)),
          ),
        ]),
      );

  Widget _sectionCard(Map s) {
    final fields = (s['fields'] as List?) ?? const [];
    if (fields.isEmpty) return const SizedBox.shrink();
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          width: double.infinity,
          padding: const EdgeInsets.fromLTRB(13, 10, 13, 9),
          decoration: BoxDecoration(border: Border(bottom: BorderSide(color: Colors.grey.shade100))),
          child: Text(gLang == 'en' ? '${s['title_en'] ?? s['title']}' : '${s['title']}',
              style: TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: widget.accent)),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(13, 4, 13, 10),
          child: Column(children: [for (final f in fields.cast<Map>()) _fieldRow(f)]),
        ),
      ]),
    );
  }

  Widget _fieldRow(Map f) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6.5),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          SizedBox(width: 130, child: Text('${f['label']}', style: const TextStyle(color: Mgmt.slate, fontSize: 12))),
          const SizedBox(width: 8),
          Expanded(child: Text('${f['value']}', textAlign: TextAlign.end,
              style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: Mgmt.ink))),
        ]),
      );

  Future<void> _launch(String url) async {
    final u = Uri.parse(url);
    if (!await launchUrl(u, mode: LaunchMode.externalApplication) && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تعذّر الفتح', 'Could not open'))));
    }
  }
}
