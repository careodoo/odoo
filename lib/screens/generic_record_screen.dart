import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'pdf_report_screen.dart';

/// A read-only viewer for ANY record — grouped fields + a printable report if
/// one exists. Powers "tap a notification → open its record" for records that
/// have no dedicated screen (waste orders, service records, …).
class GenericRecordScreen extends StatefulWidget {
  final String model;
  final int recordId;
  final String? title;
  const GenericRecordScreen({super.key, required this.model, required this.recordId, this.title});
  @override
  State<GenericRecordScreen> createState() => _GenericRecordScreenState();
}

class _GenericRecordScreenState extends State<GenericRecordScreen> {
  late Future<Map<String, dynamic>> _f;
  static const _accent = Color(0xFF0E3A5F);

  @override
  void initState() {
    super.initState();
    _f = context.read<AuthProvider>().api.pmsGenericRecord(widget.model, widget.recordId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF3F4F6),
      appBar: AppBar(
        backgroundColor: _accent, foregroundColor: Colors.white, elevation: 0,
        title: Text(widget.title ?? tr('السجل', 'Record'), overflow: TextOverflow.ellipsis),
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _f,
        builder: (_, snap) {
          if (snap.hasError) {
            return Center(child: Padding(padding: const EdgeInsets.all(30),
                child: Text('${snap.error}', textAlign: TextAlign.center, style: const TextStyle(color: Color(0xFF64748B)))));
          }
          if (!snap.hasData) return const Center(child: CircularProgressIndicator());
          final d = snap.data!;
          final sections = (d['sections'] as List?) ?? const [];
          final report = d['report'];
          return ListView(padding: const EdgeInsets.fromLTRB(14, 14, 14, 28), children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                gradient: LinearGradient(colors: [_accent, Color.lerp(_accent, Colors.black, 0.3)!],
                    begin: Alignment.topRight, end: Alignment.bottomLeft),
                borderRadius: BorderRadius.circular(16)),
              child: Text('${d['title'] ?? ''}',
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16)),
            ),
            const SizedBox(height: 12),
            for (final s in sections.cast<Map>()) _sectionCard(s),
            if (report != null) Padding(
              padding: const EdgeInsets.only(top: 8),
              child: SizedBox(width: double.infinity, child: OutlinedButton.icon(
                style: OutlinedButton.styleFrom(foregroundColor: _accent,
                    side: BorderSide(color: _accent.withValues(alpha: 0.5)), padding: const EdgeInsets.symmetric(vertical: 12)),
                onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
                    path: '$report', title: tr('تقرير', 'Report'), fileName: 'record-${widget.recordId}.pdf'))),
                icon: const Icon(Icons.print_rounded, size: 18),
                label: Text(tr('طباعة / مشاركة التقرير', 'Print / share report'), style: const TextStyle(fontWeight: FontWeight.w800)),
              )),
            ),
          ]);
        },
      ),
    );
  }

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
          child: Text('${s['title']}', style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: _accent)),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(13, 4, 13, 10),
          child: Column(children: [
            for (final f in fields.cast<Map>())
              Padding(padding: const EdgeInsets.symmetric(vertical: 6.5),
                child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  SizedBox(width: 130, child: Text('${f['label']}', style: const TextStyle(color: Color(0xFF64748B), fontSize: 12))),
                  const SizedBox(width: 8),
                  Expanded(child: Text('${f['value']}', textAlign: TextAlign.end,
                      style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5, color: Color(0xFF1E293B)))),
                ])),
          ]),
        ),
      ]),
    );
  }
}
