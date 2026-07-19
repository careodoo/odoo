import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';

const _navy = Color(0xFF0E3A5F);
const _accent = Color(0xFF0891B2);

/// الدعم الفني — the app's support desk, backed by Odoo Helpdesk: raise a
/// ticket, watch its status, and reply on its thread. Phone/email/web stay one
/// tap away for anything urgent.
class SupportScreen extends StatefulWidget {
  const SupportScreen({super.key});
  @override
  State<SupportScreen> createState() => _SupportScreenState();
}

class _SupportScreenState extends State<SupportScreen> {
  Map<String, dynamic>? _d;
  String _filter = 'all';

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.supportTickets();
      if (mounted) setState(() => _d = d);
    } catch (e) {
      if (mounted) _snack('$e');
    }
  }

  void _snack(String m, {Color? c}) => ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(m), backgroundColor: c ?? _accent, behavior: SnackBarBehavior.floating));

  Future<void> _open(String url) async {
    final u = Uri.parse(url);
    if (!await launchUrl(u, mode: LaunchMode.externalApplication) && mounted) {
      _snack(tr('تعذّر فتح الرابط', 'Could not open link'));
    }
  }

  @override
  Widget build(BuildContext context) {
    final d = _d;
    final counts = (d?['counts'] as Map?) ?? const {};
    var tickets = ((d?['tickets'] as List?) ?? const []).cast<Map>();
    if (_filter == 'open') tickets = tickets.where((t) => t['closed'] != true).toList();
    if (_filter == 'closed') tickets = tickets.where((t) => t['closed'] == true).toList();
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6FA),
      appBar: AppBar(
        backgroundColor: _accent, foregroundColor: Colors.white,
        title: Text(tr('الدعم الفني', 'Support'), style: const TextStyle(fontWeight: FontWeight.w900)),
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: _accent,
        onPressed: () => _newTicket(((d?['teams'] as List?) ?? const []).cast<Map>()),
        icon: const Icon(Icons.add_comment_rounded),
        label: Text(tr('طلب دعم', 'New ticket'), style: const TextStyle(fontWeight: FontWeight.w900)),
      ),
      body: d == null
          ? const Center(child: CircularProgressIndicator(color: _accent))
          : RefreshIndicator(
              color: _accent,
              onRefresh: _load,
              child: ListView(padding: EdgeInsets.zero, children: [
                _header(counts),
                _channels(),
                if (d['available'] == false)
                  _empty(tr('خدمة التذاكر غير مفعّلة', 'Ticketing is not enabled'))
                else ...[
                  _chips(),
                  if (tickets.isEmpty)
                    _empty(tr('لا طلبات دعم — أنشئ طلباً', 'No tickets — raise one'))
                  else
                    for (final t in tickets) _card(t),
                ],
                const SizedBox(height: 90),
              ]),
            ),
    );
  }

  Widget _header(Map counts) => CustomPaint(
        painter: const BrandPattern(opacity: 0.07),
        child: Container(
          width: double.infinity,
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 16),
          decoration: const BoxDecoration(
            gradient: LinearGradient(colors: [_accent, _navy], begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.vertical(bottom: Radius.circular(20)),
          ),
          child: Row(children: [
            _hs('${counts['open'] ?? 0}', tr('مفتوحة', 'Open')),
            _hd(),
            _hs('${counts['closed'] ?? 0}', tr('مغلقة', 'Closed')),
            _hd(),
            _hs('${counts['total'] ?? 0}', tr('الإجمالي', 'Total')),
          ]),
        ),
      );

  Widget _hs(String v, String l) => Expanded(child: Column(children: [
        Text(v, style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900)),
        Text(l, style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 10.5, fontWeight: FontWeight.w600)),
      ]));

  Widget _hd() => Container(width: 1, height: 30, color: Colors.white.withValues(alpha: 0.2));

  Widget _channels() => Padding(
        padding: const EdgeInsets.fromLTRB(12, 12, 12, 4),
        child: Row(children: [
          _ch(Icons.phone_rounded, tr('اتصال', 'Call'), const Color(0xFF16A34A), () => _open('tel:+9651880011')),
          const SizedBox(width: 8),
          _ch(Icons.email_rounded, tr('بريد', 'Email'), const Color(0xFFC0392B), () => _open('mailto:info@care-kw.com')),
          const SizedBox(width: 8),
          _ch(Icons.language_rounded, tr('الموقع', 'Website'), _accent, () => _open('https://care-kw.com')),
        ]),
      );

  Widget _ch(IconData ic, String l, Color c, VoidCallback onTap) => Expanded(
        child: Material(
          color: Colors.white, borderRadius: BorderRadius.circular(13),
          child: InkWell(
            borderRadius: BorderRadius.circular(13), onTap: onTap,
            child: Container(
              padding: const EdgeInsets.symmetric(vertical: 11),
              decoration: BoxDecoration(borderRadius: BorderRadius.circular(13), border: Border.all(color: Colors.grey.shade200)),
              child: Column(children: [
                Icon(ic, color: c, size: 20),
                const SizedBox(height: 5),
                Text(l, style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: _navy)),
              ]),
            ),
          ),
        ),
      );

  Widget _chips() => SizedBox(
        height: 42,
        child: ListView(scrollDirection: Axis.horizontal, padding: const EdgeInsets.symmetric(horizontal: 8), children: [
          for (final f in const [('all', 'الكل', 'All'), ('open', 'مفتوحة', 'Open'), ('closed', 'مغلقة', 'Closed')])
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
              child: ChoiceChip(
                selected: _filter == f.$1,
                label: Text(tr(f.$2, f.$3), style: TextStyle(fontWeight: FontWeight.w800, fontSize: 12.5, color: _filter == f.$1 ? Colors.white : _navy)),
                selectedColor: _accent, backgroundColor: Colors.white,
                side: BorderSide(color: _filter == f.$1 ? _accent : Colors.grey.shade300),
                onSelected: (_) => setState(() => _filter = f.$1),
              ),
            ),
        ]),
      );

  Widget _card(Map t) {
    final closed = t['closed'] == true;
    final c = closed ? const Color(0xFF16A34A) : const Color(0xFFF59E0B);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      child: Material(
        color: Colors.white, borderRadius: BorderRadius.circular(15),
        child: InkWell(
          borderRadius: BorderRadius.circular(15),
          onTap: () => _openTicket((t['id'] as num).toInt()),
          child: Container(
            decoration: BoxDecoration(borderRadius: BorderRadius.circular(15), border: Border.all(color: Colors.grey.shade200)),
            padding: const EdgeInsets.all(12),
            child: Row(children: [
              Container(width: 5, height: 46, decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(4))),
              const SizedBox(width: 11),
              Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text('${t['name']}', maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13.5, color: _navy)),
                const SizedBox(height: 4),
                Text('${t['ref']} · ${t['created'] ?? ''}', style: TextStyle(fontSize: 11, color: Colors.grey.shade600)),
                const SizedBox(height: 6),
                Wrap(spacing: 6, runSpacing: 5, children: [
                  _tag('${t['stage'] ?? ''}', c),
                  if (t['team'] != null) _tag('${t['team']}', const Color(0xFF6366F1)),
                  if (t['assignee'] != null) _tag('👤 ${t['assignee']}', const Color(0xFF0E7490)),
                ]),
              ])),
              const Icon(Icons.chevron_left_rounded, color: Colors.grey, size: 20),
            ]),
          ),
        ),
      ),
    );
  }

  /// The ticket with its full conversation, and a reply box.
  void _openTicket(int id) {
    showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (_) => _TicketSheet(id: id, onChanged: _load));
  }

  Future<void> _newTicket(List<Map> teams) async {
    final subject = TextEditingController();
    final desc = TextEditingController();
    String priority = '1';
    int? teamId;
    String? photo;
    final saved = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.transparent,
      builder: (ctx) => StatefulBuilder(builder: (ctx, setSt) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(ctx).viewInsets.bottom),
        child: Container(
          decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
          clipBehavior: Clip.antiAlias,
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Container(
              width: double.infinity, padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
              decoration: const BoxDecoration(gradient: LinearGradient(colors: [_accent, _navy], begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Column(children: [
                Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12), decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
                Row(children: [
                  const Icon(Icons.support_agent_rounded, color: Colors.white),
                  const SizedBox(width: 10),
                  Expanded(child: Text(tr('طلب دعم جديد', 'New support ticket'),
                      style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900))),
                ]),
              ]),
            ),
            Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              _field(subject, tr('موضوع الطلب', 'Subject')),
              const SizedBox(height: 10),
              _field(desc, tr('اشرح المشكلة…', 'Describe the problem…'), lines: 4),
              const SizedBox(height: 12),
              Text(tr('الأهمية', 'Priority'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 13, color: _navy)),
              const SizedBox(height: 7),
              Row(children: [
                for (final p in const [('0', 'منخفضة', 'Low'), ('1', 'عادية', 'Normal'), ('2', 'عالية', 'High'), ('3', 'عاجلة', 'Urgent')])
                  Expanded(child: GestureDetector(
                    onTap: () => setSt(() => priority = p.$1),
                    child: Container(
                      margin: const EdgeInsets.symmetric(horizontal: 3),
                      padding: const EdgeInsets.symmetric(vertical: 9),
                      decoration: BoxDecoration(
                        color: priority == p.$1 ? _accent : Colors.white,
                        borderRadius: BorderRadius.circular(11),
                        border: Border.all(color: priority == p.$1 ? _accent : Colors.grey.shade300)),
                      child: Text(tr(p.$2, p.$3), textAlign: TextAlign.center,
                          style: TextStyle(fontSize: 11, fontWeight: FontWeight.w800, color: priority == p.$1 ? Colors.white : _navy)),
                    ),
                  )),
              ]),
              if (teams.length > 1) ...[
                const SizedBox(height: 12),
                Wrap(spacing: 7, children: [
                  for (final t in teams)
                    ChoiceChip(
                      selected: teamId == t['id'],
                      label: Text('${t['name']}', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w800, color: teamId == t['id'] ? Colors.white : _navy)),
                      selectedColor: _accent, backgroundColor: Colors.white,
                      side: BorderSide(color: teamId == t['id'] ? _accent : Colors.grey.shade300),
                      onSelected: (_) => setSt(() => teamId = t['id'] as int),
                    ),
                ]),
              ],
              const SizedBox(height: 12),
              GestureDetector(
                onTap: () async {
                  final x = await ImagePicker().pickImage(source: ImageSource.camera, imageQuality: 65, maxWidth: 1600);
                  if (x == null) return;
                  final bytes = await x.readAsBytes();
                  setSt(() => photo = base64Encode(bytes));
                },
                child: Container(
                  height: 74, width: double.infinity, clipBehavior: Clip.antiAlias,
                  decoration: BoxDecoration(color: _accent.withValues(alpha: 0.07), borderRadius: BorderRadius.circular(12), border: Border.all(color: _accent.withValues(alpha: 0.3))),
                  child: photo == null
                      ? Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                          const Icon(Icons.add_a_photo_rounded, color: _accent, size: 24),
                          const SizedBox(height: 4),
                          Text(tr('أرفق صورة (اختياري)', 'Attach a photo (optional)'),
                              style: const TextStyle(color: _accent, fontWeight: FontWeight.w800, fontSize: 11.5)),
                        ])
                      : Image.memory(base64Decode(photo!), fit: BoxFit.cover, width: double.infinity),
                ),
              ),
              const SizedBox(height: 14),
              FilledButton.icon(
                style: FilledButton.styleFrom(backgroundColor: _accent, minimumSize: const Size.fromHeight(50)),
                onPressed: () {
                  if (subject.text.trim().isEmpty) {
                    ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(content: Text(tr('اكتب موضوع الطلب', 'Enter a subject'))));
                    return;
                  }
                  Navigator.pop(ctx, true);
                },
                icon: const Icon(Icons.send_rounded),
                label: Text(tr('إرسال الطلب', 'Send ticket'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
              ),
              const SizedBox(height: 8),
            ])),
          ]),
        ),
      )),
    );
    if (saved != true) return;
    try {
      await context.read<AuthProvider>().api.supportCreate({
        'subject': subject.text.trim(),
        'description': desc.text.trim(),
        'priority': priority,
        if (teamId != null) 'team_id': teamId,
        if (photo != null) 'media': [{'name': 'support.jpg', 'mimetype': 'image/jpeg', 'data': photo}],
      });
      await _load();
      if (mounted) _snack(tr('✅ أُرسل طلب الدعم', '✅ Ticket sent'), c: const Color(0xFF16A34A));
    } catch (e) {
      if (mounted) _snack('$e');
    }
  }

  Widget _field(TextEditingController c, String hint, {int lines = 1}) => TextField(
        controller: c, maxLines: lines,
        decoration: InputDecoration(
          hintText: hint, filled: true, fillColor: Colors.white, isDense: true,
          hintStyle: TextStyle(fontSize: 13, color: Colors.grey.shade400),
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
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 30),
        child: Column(children: [
          Icon(Icons.support_agent_outlined, size: 54, color: Colors.grey.shade300),
          const SizedBox(height: 10),
          Text(t, textAlign: TextAlign.center, style: TextStyle(color: Colors.grey.shade500, fontWeight: FontWeight.w600)),
        ]),
      );
}

/// One ticket: status, description and the whole conversation, with a reply box.
class _TicketSheet extends StatefulWidget {
  const _TicketSheet({required this.id, required this.onChanged});
  final int id;
  final VoidCallback onChanged;
  @override
  State<_TicketSheet> createState() => _TicketSheetState();
}

class _TicketSheetState extends State<_TicketSheet> {
  Map<String, dynamic>? _t;
  final _reply = TextEditingController();
  bool _sending = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final t = await context.read<AuthProvider>().api.supportTicket(widget.id);
      if (mounted) setState(() => _t = t);
    } catch (_) {}
  }

  Future<void> _send() async {
    final body = _reply.text.trim();
    if (body.isEmpty) return;
    setState(() => _sending = true);
    _reply.clear();
    try {
      await context.read<AuthProvider>().api.supportReply(widget.id, body);
      await _load();
      widget.onChanged();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    } finally {
      if (mounted) setState(() => _sending = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = _t;
    final closed = t?['closed'] == true;
    final c = closed ? const Color(0xFF16A34A) : const Color(0xFFF59E0B);
    final msgs = ((t?['messages'] as List?) ?? const []).cast<Map>();
    return DraggableScrollableSheet(
      expand: false, initialChildSize: 0.9, minChildSize: 0.5, maxChildSize: 0.96,
      builder: (_, sc) => Padding(
        padding: EdgeInsets.only(bottom: MediaQuery.of(context).viewInsets.bottom),
        child: Container(
          decoration: const BoxDecoration(color: Color(0xFFF6F7F9), borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
          clipBehavior: Clip.antiAlias,
          child: Column(children: [
            Container(
              width: double.infinity, padding: const EdgeInsets.fromLTRB(20, 12, 20, 16),
              decoration: BoxDecoration(gradient: LinearGradient(colors: [c, Color.lerp(c, Colors.black, 0.42)!], begin: Alignment.topRight, end: Alignment.bottomLeft)),
              child: Column(children: [
                Center(child: Container(width: 40, height: 4, margin: const EdgeInsets.only(bottom: 12), decoration: BoxDecoration(color: Colors.white54, borderRadius: BorderRadius.circular(3)))),
                Row(children: [
                  Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Text('${t?['ref'] ?? ''}', style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 11.5, fontWeight: FontWeight.w700)),
                    const SizedBox(height: 2),
                    Text('${t?['name'] ?? tr('طلب دعم', 'Ticket')}', maxLines: 2, overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900)),
                  ])),
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.22), borderRadius: BorderRadius.circular(20)),
                    child: Text('${t?['stage'] ?? ''}', style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w900)),
                  ),
                ]),
              ]),
            ),
            Expanded(child: t == null
                ? const Center(child: CircularProgressIndicator(color: _accent))
                : ListView(controller: sc, padding: const EdgeInsets.all(16), children: [
                    if (t['description'] != null)
                      Container(
                        width: double.infinity, padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(12), border: Border.all(color: Colors.grey.shade200)),
                        child: Text('${t['description']}', style: const TextStyle(fontSize: 13, height: 1.4, color: _navy)),
                      ),
                    const SizedBox(height: 14),
                    Row(children: [
                      const Icon(Icons.forum_rounded, size: 17, color: _navy), const SizedBox(width: 7),
                      Text(tr('المحادثة', 'Conversation'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 14, color: _navy)),
                    ]),
                    const SizedBox(height: 8),
                    if (msgs.isEmpty)
                      Padding(padding: const EdgeInsets.all(14),
                          child: Text(tr('لا رسائل بعد', 'No messages yet'), style: TextStyle(color: Colors.grey.shade500))),
                    for (final m in msgs) _bubble(m),
                  ])),
            SafeArea(top: false, child: Container(
              padding: const EdgeInsets.fromLTRB(10, 6, 10, 8),
              color: Colors.white,
              child: Row(children: [
                Expanded(child: TextField(
                  controller: _reply, minLines: 1, maxLines: 3,
                  decoration: InputDecoration(
                    hintText: tr('اكتب ردك…', 'Write a reply…'), filled: true, fillColor: const Color(0xFFF1F3F6), isDense: true,
                    border: OutlineInputBorder(borderRadius: BorderRadius.circular(22), borderSide: BorderSide.none),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                  ),
                )),
                const SizedBox(width: 8),
                Material(color: _accent, shape: const CircleBorder(), child: InkWell(
                  customBorder: const CircleBorder(),
                  onTap: _sending ? null : _send,
                  child: Padding(padding: const EdgeInsets.all(11),
                      child: _sending
                          ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                          : const Icon(Icons.send_rounded, color: Colors.white, size: 20)),
                )),
              ]),
            )),
          ]),
        ),
      ),
    );
  }

  Widget _bubble(Map m) {
    final mine = m['mine'] == true;
    return Align(
      alignment: mine ? Alignment.centerLeft : Alignment.centerRight,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 3),
        padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 9),
        constraints: BoxConstraints(maxWidth: MediaQuery.of(context).size.width * 0.78),
        decoration: BoxDecoration(
          color: mine ? _accent : Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: mine ? null : Border.all(color: Colors.grey.shade200),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          if (!mine && m['author'] != null)
            Text('${m['author']}', style: const TextStyle(fontSize: 10.5, fontWeight: FontWeight.w900, color: _accent)),
          Text('${m['body']}', style: TextStyle(color: mine ? Colors.white : _navy, fontSize: 13, height: 1.35)),
          const SizedBox(height: 2),
          Text('${m['at'] ?? ''}', style: TextStyle(color: mine ? Colors.white70 : Colors.grey.shade500, fontSize: 9.5)),
        ]),
      ),
    );
  }
}
