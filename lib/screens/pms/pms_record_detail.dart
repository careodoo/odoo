// شاشة «تفاصيل سجل PMS» العامة — تستهلك GET /pms/record/<code>/<id>
// (الحقول/البنود/المرفقات/السجل الزمني/المناقشة/ذات صلة) + POST .../message.
// تصلح لأي قسم: غرامات/مكافآت/بدلات/عقود/تسليمات/طلبات/عمل إضافي…
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import '../pdf_report_screen.dart';
import 'pms_shell.dart' show Pms;
import 'pms_section.dart' show PmsPhotoView, kPmsSectionColors, kPmsSectionIcons;

(Color, Color) _stateColors(String? s) {
  switch (s) {
    case 'approve':
    case 'approved':
    case 'done':
    case 'posted':
    case 'validated':
    case 'paid':
      return (Pms.green.withValues(alpha: 0.14), const Color(0xFF15803D));
    case 'reject':
    case 'rejected':
    case 'cancel':
    case 'cancelled':
    case 'canceled':
    case 'refuse':
      return (Pms.red.withValues(alpha: 0.14), const Color(0xFFB91C1C));
    case 'draft':
    case 'new':
      return (Colors.grey.withValues(alpha: 0.16), const Color(0xFF475569));
    default:
      return (Pms.amber.withValues(alpha: 0.16), const Color(0xFFB45309));
  }
}

class PmsRecordDetailScreen extends StatefulWidget {
  const PmsRecordDetailScreen({
    super.key,
    required this.code,
    required this.id,
    this.title,
    this.accent,
  });

  final String code;
  final int id;
  final String? title;
  final Color? accent;

  @override
  State<PmsRecordDetailScreen> createState() => _PmsRecordDetailScreenState();
}

class _PmsRecordDetailScreenState extends State<PmsRecordDetailScreen> {
  Future<Map<String, dynamic>>? _f;
  // Live copy of the chatter so a posted comment appears instantly.
  final List<Map<String, dynamic>> _chatter = [];
  bool _chatterSeeded = false;
  final _msgCtrl = TextEditingController();
  bool _sending = false;

  Color get _c => widget.accent ?? kPmsSectionColors[widget.code] ?? Pms.violet;

  String _initial(String s) {
    final t = s.trim();
    return t.isEmpty ? '?' : t.substring(0, 1);
  }

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _msgCtrl.dispose();
    super.dispose();
  }

  void _load() => _f = context.read<AuthProvider>().api.pmsRecordDetail(widget.code, widget.id);

  Future<void> _refresh() async {
    setState(() {
      _chatterSeeded = false;
      _chatter.clear();
      _load();
    });
    await _f;
  }

  Future<void> _send() async {
    final body = _msgCtrl.text.trim();
    if (body.isEmpty || _sending) return;
    FocusScope.of(context).unfocus();
    setState(() => _sending = true);
    try {
      final res = await context.read<AuthProvider>().api.pmsRecordMessage(widget.code, widget.id, body);
      if (!mounted) return;
      setState(() {
        _chatter.insert(0, {
          'author': res['author'] ?? tr('أنا', 'Me'),
          'date': res['date'] ?? '',
          'body': body,
        });
        _msgCtrl.clear();
        _sending = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _sending = false);
      ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(tr('تعذّر الإرسال: $e', 'Send failed: $e')), backgroundColor: Pms.red));
    }
  }

  void _print(Map<String, dynamic> d) {
    // The backend resolves the right report (and falls back to the origin
    // record for stop/resume), so use report_model/report_id/report as-is —
    // the origin may differ from this record (suspension/resume).
    final report = '${d['report'] ?? ''}';
    final model = '${d['report_model'] ?? d['model'] ?? ''}';
    final rid = (d['report_id'] as num?)?.toInt() ?? widget.id;
    if (report.isEmpty || model.isEmpty) return;
    final api = context.read<AuthProvider>().api;
    Navigator.push(context, MaterialPageRoute(builder: (_) => PdfReportScreen(
        path: api.pmsRecordReportPath(model, rid, report),
        title: '${d['name'] ?? tr('التقرير', 'Report')}',
        fileName: 'record-$rid.pdf')));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Pms.bg,
      appBar: AppBar(
        backgroundColor: _c, foregroundColor: Colors.white, elevation: 0,
        title: Text(widget.title ?? tr('تفاصيل السجل', 'Record detail'), overflow: TextOverflow.ellipsis),
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _f,
        builder: (_, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return ListView(children: [
              const SizedBox(height: 90),
              Center(child: Padding(
                padding: const EdgeInsets.all(28),
                child: Text(tr('تعذّر التحميل: ${snap.error}', 'Load failed: ${snap.error}'),
                    textAlign: TextAlign.center, style: const TextStyle(color: Pms.red)),
              )),
            ]);
          }
          final d = snap.data ?? const {};
          if (!_chatterSeeded) {
            _chatter
              ..clear()
              ..addAll(((d['chatter'] as List?) ?? const [])
                  .map((e) => Map<String, dynamic>.from(e as Map)));
            _chatterSeeded = true;
          }
          final fields = ((d['fields'] as List?) ?? const []).cast<dynamic>();
          final lines = (d['lines'] as Map?) ?? const {};
          final cols = ((lines['cols'] as List?) ?? const []);
          final lineRows = ((lines['rows'] as List?) ?? const []);
          final files = ((d['files'] as List?) ?? const []);
          final timeline = ((d['timeline'] as List?) ?? const []);
          final related = ((d['related'] as List?) ?? const []);
          final canPrint = d['report'] != null && '${d['report']}'.isNotEmpty;

          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView(
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 24),
              children: [
                _header(d),
                if (canPrint) ...[
                  const SizedBox(height: 10),
                  SizedBox(
                    width: double.infinity, height: 46,
                    child: FilledButton.icon(
                      style: FilledButton.styleFrom(
                          backgroundColor: _c,
                          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                      onPressed: () => _print(d),
                      icon: const Icon(Icons.print_rounded, size: 19),
                      label: Text(tr('طباعة التقرير', 'Print report'),
                          style: const TextStyle(fontWeight: FontWeight.w900)),
                    ),
                  ),
                ],
                if (fields.isNotEmpty) _fieldsCard(fields),
                if (cols.isNotEmpty && lineRows.isNotEmpty) _linesCard(cols, lineRows),
                if (files.isNotEmpty) _filesCard(files),
                if (timeline.isNotEmpty) _timelineCard(timeline),
                if (related.isNotEmpty) _relatedCard(related),
                _chatterCard(),
              ],
            ),
          );
        },
      ),
    );
  }

  // ---------- header ----------
  Widget _header(Map d) {
    final sc = _stateColors(d['state'] as String?);
    final stateLabel = _fieldValue(d, 'state') ?? '${d['state'] ?? ''}';
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        gradient: LinearGradient(colors: [_c, Color.lerp(_c, Colors.black, 0.22)!],
            begin: Alignment.topLeft, end: Alignment.bottomRight),
        borderRadius: BorderRadius.circular(16),
      ),
      child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Container(
          width: 42, height: 42, alignment: Alignment.center,
          decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.18), borderRadius: BorderRadius.circular(12)),
          child: Icon(kPmsSectionIcons[widget.code] ?? Icons.description_rounded, color: Colors.white, size: 21),
        ),
        const SizedBox(width: 11),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${d['name'] ?? '—'}',
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16)),
          if (d['state'] != null && stateLabel.isNotEmpty) ...[
            const SizedBox(height: 7),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
              decoration: BoxDecoration(color: sc.$1, borderRadius: BorderRadius.circular(7)),
              child: Text(stateLabel,
                  style: TextStyle(fontSize: 11, fontWeight: FontWeight.w900, color: sc.$2)),
            ),
          ],
        ])),
      ]),
    );
  }

  // Find a field's displayed value by matching the raw state against fields.
  String? _fieldValue(Map d, String key) {
    // The 'state' field appears in `fields` translated; show that label.
    for (final f in ((d['fields'] as List?) ?? const [])) {
      final m = f as Map;
      if ('${m['label']}'.toLowerCase() == key || '${m['label']}' == 'الحالة') {
        return '${m['value']}';
      }
    }
    return null;
  }

  Widget _sectionCard({required String title, required IconData icon, required Widget child}) => Container(
        margin: const EdgeInsets.only(top: 12),
        padding: const EdgeInsets.all(13),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.black.withValues(alpha: 0.06)),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(icon, size: 17, color: _c),
            const SizedBox(width: 7),
            Text(title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5)),
          ]),
          const SizedBox(height: 10),
          child,
        ]),
      );

  // ---------- fields ----------
  Widget _fieldsCard(List fields) => _sectionCard(
        title: tr('التفاصيل', 'Details'),
        icon: Icons.list_alt_rounded,
        child: Column(children: [
          for (var i = 0; i < fields.length; i++) ...[
            if (i > 0) Divider(height: 1, color: Colors.grey.withValues(alpha: 0.18)),
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                SizedBox(
                  width: 120,
                  child: Text('${(fields[i] as Map)['label'] ?? ''}',
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Colors.grey.shade600)),
                ),
                const SizedBox(width: 10),
                Expanded(child: Text('${(fields[i] as Map)['value'] ?? ''}',
                    style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700, color: Pms.ink))),
              ]),
            ),
          ],
        ]),
      );

  // ---------- lines table ----------
  Widget _linesCard(List cols, List rows) => _sectionCard(
        title: tr('البنود', 'Items'),
        icon: Icons.table_rows_rounded,
        child: SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: DataTable(
            headingRowHeight: 38,
            dataRowMinHeight: 34,
            dataRowMaxHeight: 52,
            columnSpacing: 22,
            horizontalMargin: 0,
            headingTextStyle: TextStyle(fontSize: 11.5, fontWeight: FontWeight.w900, color: _c),
            dataTextStyle: const TextStyle(fontSize: 12, color: Pms.ink),
            columns: [for (final cObj in cols) DataColumn(label: Text('$cObj'))],
            rows: [
              for (final r in rows)
                DataRow(cells: [
                  for (var ci = 0; ci < cols.length; ci++)
                    DataCell(Text(ci < (r as List).length ? '${r[ci] ?? ''}' : '')),
                ]),
            ],
          ),
        ),
      );

  // ---------- files ----------
  Widget _filesCard(List files) => _sectionCard(
        title: tr('المرفقات', 'Attachments'),
        icon: Icons.attach_file_rounded,
        child: Column(children: [
          for (final fObj in files) _fileRow(fObj as Map),
        ]),
      );

  Widget _fileRow(Map f) {
    final url = f['url'] as String?;
    final isImage = url != null && url.isNotEmpty;
    return InkWell(
      borderRadius: BorderRadius.circular(10),
      onTap: isImage
          ? () => Navigator.push(context, MaterialPageRoute(
              builder: (_) => PmsPhotoView(url: url, title: '${f['name']}')))
          : null,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Row(children: [
          Container(
            width: 34, height: 34, alignment: Alignment.center,
            decoration: BoxDecoration(
                color: _c.withValues(alpha: 0.09), borderRadius: BorderRadius.circular(9)),
            child: Icon(isImage ? Icons.image_rounded : Icons.insert_drive_file_rounded, size: 17, color: _c),
          ),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${f['name'] ?? '—'}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700)),
            if (f['info'] != null && '${f['info']}'.isNotEmpty)
              Text('${f['info']}', style: TextStyle(fontSize: 10.5, color: Colors.grey.shade500)),
          ])),
          if (isImage) Icon(Icons.chevron_left_rounded, color: Colors.grey.shade400),
        ]),
      ),
    );
  }

  // ---------- timeline ----------
  Widget _timelineCard(List timeline) => _sectionCard(
        title: tr('السجل الزمني', 'Timeline'),
        icon: Icons.history_rounded,
        child: Column(children: [
          for (final tObj in timeline) _timelineRow(tObj as Map),
        ]),
      );

  Widget _timelineRow(Map t) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Container(width: 8, height: 8,
                decoration: BoxDecoration(color: _c, shape: BoxShape.circle)),
          ),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${t['title'] ?? ''}', style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700)),
            const SizedBox(height: 2),
            Text([t['author'], t['date']].where((e) => e != null && '$e'.isNotEmpty).join(' · '),
                style: TextStyle(fontSize: 10.5, color: Colors.grey.shade500)),
          ])),
        ]),
      );

  // ---------- related ----------
  Widget _relatedCard(List related) => _sectionCard(
        title: tr('سجلات ذات صلة', 'Related'),
        icon: Icons.link_rounded,
        child: Column(children: [
          for (final rObj in related)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 6),
              child: Row(children: [
                Icon(Icons.subdirectory_arrow_left_rounded, size: 16, color: Colors.grey.shade400),
                const SizedBox(width: 8),
                Expanded(child: Text('${(rObj as Map)['name'] ?? '—'}',
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontSize: 12.5, fontWeight: FontWeight.w700))),
                if ((rObj)['info'] != null && '${(rObj)['info']}'.isNotEmpty)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                    decoration: BoxDecoration(
                        color: Colors.grey.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(6)),
                    child: Text('${(rObj)['info']}',
                        style: TextStyle(fontSize: 10, fontWeight: FontWeight.w800, color: Colors.grey.shade700)),
                  ),
              ]),
            ),
        ]),
      );

  // ---------- chatter ----------
  Widget _chatterCard() => _sectionCard(
        title: tr('المناقشة', 'Discussion'),
        icon: Icons.forum_rounded,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Expanded(child: TextField(
              controller: _msgCtrl,
              minLines: 1, maxLines: 4,
              textInputAction: TextInputAction.newline,
              decoration: InputDecoration(
                hintText: tr('أضف تعليقاً…', 'Add a comment…'),
                isDense: true, filled: true, fillColor: Pms.bg,
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
              ),
            )),
            const SizedBox(width: 8),
            SizedBox(
              height: 44, width: 44,
              child: FilledButton(
                style: FilledButton.styleFrom(
                    backgroundColor: _c, padding: EdgeInsets.zero,
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12))),
                onPressed: _sending ? null : _send,
                child: _sending
                    ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                    : const Icon(Icons.send_rounded, size: 19),
              ),
            ),
          ]),
          const SizedBox(height: 12),
          if (_chatter.isEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 8),
              child: Text(tr('لا توجد تعليقات بعد.', 'No comments yet.'),
                  style: TextStyle(fontSize: 12, color: Colors.grey.shade500)),
            )
          else
            for (final m in _chatter) _chatterRow(m),
        ]),
      );

  Widget _chatterRow(Map m) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
            color: Pms.bg, borderRadius: BorderRadius.circular(11)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            CircleAvatar(radius: 11, backgroundColor: _c.withValues(alpha: 0.15),
                child: Text(_initial('${m['author'] ?? '?'}'),
                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.w900, color: _c))),
            const SizedBox(width: 7),
            Expanded(child: Text('${m['author'] ?? ''}',
                style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w900))),
            Text('${m['date'] ?? ''}', style: TextStyle(fontSize: 10, color: Colors.grey.shade500)),
          ]),
          if (m['body'] != null && '${m['body']}'.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text('${m['body']}', style: const TextStyle(fontSize: 12.5, color: Pms.ink, height: 1.35)),
          ],
        ]),
      );
}
