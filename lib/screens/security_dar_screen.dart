import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// «تقرير النشاط اليومي» (DAR) — معيار حراسة مهني: عند نهاية الوردية يرى الحارس
/// نشاط يومه مُجمَّعاً تلقائياً (دوريات/بلاغات/مهام/زوّار) ثم يكتب سرداً
/// (ملخّص الوردية + أبرز الأحداث + توصيات) ويرسله. مع أرشيف تقاريره السابقة.
class SecurityDarScreen extends StatefulWidget {
  const SecurityDarScreen({super.key});
  @override
  State<SecurityDarScreen> createState() => _SecurityDarScreenState();
}

class _SecurityDarScreenState extends State<SecurityDarScreen> {
  static const _navy = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _muted = Color(0xFF9CB2CD);
  static const _green = Color(0xFF37C98A);
  static const _amber = Color(0xFFF7A23B);
  static const _blue = Color(0xFF4AA8FF);
  static const _red = Color(0xFFE5484D);

  Map<String, dynamic>? _today;
  List _archive = const [];
  bool _loading = true, _saving = false;
  final _summary = TextEditingController();
  final _highlights = TextEditingController();
  final _notes = TextEditingController();

  @override
  void initState() { super.initState(); _load(); }
  @override
  void dispose() { _summary.dispose(); _highlights.dispose(); _notes.dispose(); super.dispose(); }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final api = context.read<AuthProvider>().api;
      final t = await api.securityDarToday();
      final a = await api.securityDars();
      if (!mounted) return;
      final today = (t['today'] as Map?)?.cast<String, dynamic>();
      if (today != null) {
        _summary.text = (today['summary'] ?? '') as String;
        _highlights.text = (today['highlights'] ?? '') as String;
        _notes.text = (today['notes'] ?? '') as String;
      }
      setState(() {
        _today = t.cast<String, dynamic>();
        _archive = (a['items'] as List?) ?? const [];
        _loading = false;
      });
    } catch (_) { if (mounted) setState(() => _loading = false); }
  }

  Future<void> _submit() async {
    setState(() => _saving = true);
    try {
      await context.read<AuthProvider>().api.securityDarSubmit({
        'summary': _summary.text.trim(),
        'highlights': _highlights.text.trim(),
        'notes': _notes.text.trim(),
      });
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          backgroundColor: _green, content: Text(tr('تم إرسال تقرير اليوم', 'Daily report submitted'))));
      await _load();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(backgroundColor: _red, content: Text('$e')));
    } finally { if (mounted) setState(() => _saving = false); }
  }

  @override
  Widget build(BuildContext context) {
    final counts = (_today?['counts'] as Map?)?.cast<String, dynamic>() ?? const {};
    final today = (_today?['today'] as Map?)?.cast<String, dynamic>();
    final premise = (_today?['premise'] as Map?)?.cast<String, dynamic>();
    final submitted = today != null && today['state'] == 'submitted';
    return Scaffold(
      backgroundColor: _navy,
      appBar: AppBar(
        title: Text(tr('تقرير النشاط اليومي', 'Daily activity report')),
        backgroundColor: _navy,
        actions: [IconButton(onPressed: _load, icon: const Icon(Icons.refresh_rounded))],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : RefreshIndicator(
              onRefresh: _load,
              child: ListView(padding: const EdgeInsets.fromLTRB(12, 12, 12, 32), children: [
                // ترويسة اليوم + الموقع
                Row(children: [
                  const Icon(Icons.today_rounded, color: _blue, size: 20),
                  const SizedBox(width: 8),
                  Expanded(child: Text(
                    premise?['name'] != null
                        ? '${tr('وردية اليوم', 'Today')} · ${premise!['name']}'
                        : tr('وردية اليوم', 'Today shift'),
                    style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 15))),
                  if (submitted) Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(color: _green.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(20)),
                    child: Text(tr('مُرسَل', 'Submitted'), style: const TextStyle(color: _green, fontWeight: FontWeight.w700, fontSize: 11.5))),
                ]),
                const SizedBox(height: 4),
                Text(tr('نشاطك اليوم — مُجمَّع تلقائياً', 'Your activity today — auto-aggregated'),
                    style: const TextStyle(color: _muted, fontSize: 12)),
                const SizedBox(height: 12),
                // بطاقات الأعداد
                GridView.count(
                  crossAxisCount: 2, shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 10, crossAxisSpacing: 10, childAspectRatio: 2.3,
                  children: [
                    _stat(Icons.directions_walk_rounded, _green, tr('دوريات مُنجَزة', 'Patrols'), counts['patrols']),
                    _stat(Icons.report_gmailerrorred_rounded, _red, tr('بلاغات', 'Incidents'), counts['incidents']),
                    _stat(Icons.task_alt_rounded, _blue, tr('مهام مُنجَزة', 'Tasks'), counts['tasks']),
                    _stat(Icons.groups_rounded, _amber, tr('زوّار', 'Visitors'), counts['visitors']),
                  ],
                ),
                const SizedBox(height: 16),
                _field(_summary, tr('ملخّص الوردية', 'Shift summary'),
                    tr('صف سير الوردية بشكل عام…', 'Describe how the shift went…'), 4, submitted),
                const SizedBox(height: 12),
                _field(_highlights, tr('أبرز الأحداث', 'Highlights'),
                    tr('أي حدث مهم يستحق الذكر…', 'Any notable event…'), 3, submitted),
                const SizedBox(height: 12),
                _field(_notes, tr('ملاحظات وتوصيات', 'Notes & recommendations'),
                    tr('توصيات للإدارة أو الوردية القادمة…', 'For management / next shift…'), 3, submitted),
                const SizedBox(height: 16),
                SizedBox(
                  height: 50,
                  child: FilledButton.icon(
                    style: FilledButton.styleFrom(backgroundColor: submitted ? _amber : _green),
                    onPressed: _saving ? null : _submit,
                    icon: _saving
                        ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                        : Icon(submitted ? Icons.edit_note_rounded : Icons.send_rounded),
                    label: Text(submitted ? tr('تحديث التقرير', 'Update report') : tr('إرسال تقرير اليوم', 'Submit report'),
                        style: const TextStyle(fontWeight: FontWeight.w800)),
                  ),
                ),
                // الأرشيف
                if (_archive.isNotEmpty) ...[
                  const SizedBox(height: 22),
                  Text(tr('تقاريري السابقة', 'My previous reports'),
                      style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 14)),
                  const SizedBox(height: 8),
                  ..._archive.where((r) => (r as Map)['id'] != today?['id']).map((r) => _archiveTile((r as Map).cast<String, dynamic>())),
                ],
              ]),
            ),
    );
  }

  Widget _stat(IconData ic, Color c, String label, dynamic v) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
        decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(14)),
        child: Row(children: [
          Container(width: 38, height: 38, decoration: BoxDecoration(color: c.withValues(alpha: 0.16), borderRadius: BorderRadius.circular(10)),
              child: Icon(ic, color: c, size: 20)),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
            Text('${v ?? 0}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 20, height: 1)),
            Text(label, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 11)),
          ])),
        ]),
      );

  Widget _field(TextEditingController c, String label, String hint, int lines, bool readOnly) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 13)),
          const SizedBox(height: 6),
          TextField(
            controller: c, maxLines: lines, readOnly: readOnly,
            style: const TextStyle(color: Colors.white, fontSize: 13.5),
            decoration: InputDecoration(
              hintText: hint, hintStyle: const TextStyle(color: _muted, fontSize: 12.5),
              filled: true, fillColor: _card,
              contentPadding: const EdgeInsets.all(12),
              border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
            ),
          ),
        ],
      );

  Widget _archiveTile(Map<String, dynamic> r) => Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(12)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            const Icon(Icons.description_rounded, color: _blue, size: 16),
            const SizedBox(width: 6),
            Text('${r['date'] ?? ''}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 13)),
            const Spacer(),
            Text('${r['name'] ?? ''}', style: const TextStyle(color: _muted, fontSize: 11)),
          ]),
          const SizedBox(height: 6),
          Row(children: [
            _chip('${r['patrols'] ?? 0} ${tr('دورية', 'patrols')}', _green),
            _chip('${r['incidents'] ?? 0} ${tr('بلاغ', 'inc.')}', _red),
            _chip('${r['tasks'] ?? 0} ${tr('مهمة', 'tasks')}', _blue),
          ]),
          if (((r['summary'] ?? '') as String).isNotEmpty) ...[
            const SizedBox(height: 6),
            Text('${r['summary']}', maxLines: 2, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _muted, fontSize: 12)),
          ],
        ]),
      );

  Widget _chip(String t, Color c) => Container(
        margin: const EdgeInsets.only(right: 6),
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: c.withValues(alpha: 0.14), borderRadius: BorderRadius.circular(8)),
        child: Text(t, style: TextStyle(color: c, fontWeight: FontWeight.w700, fontSize: 10.5)),
      );
}
