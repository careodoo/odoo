import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:image_picker/image_picker.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import 'media_viewer_screen.dart';

class WorkOrderDetailScreen extends StatefulWidget {
  const WorkOrderDetailScreen({super.key, required this.id, required this.title});
  final int id;
  final String title;
  @override
  State<WorkOrderDetailScreen> createState() => _WorkOrderDetailScreenState();
}

class _WorkOrderDetailScreenState extends State<WorkOrderDetailScreen> {
  Map<String, dynamic>? _d;
  bool _loading = true;
  Timer? _timer;
  Duration _remaining = Duration.zero;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  Future<void> _load() async {
    setState(() => _loading = true);
    try {
      final d = await context.read<AuthProvider>().api.workOrderDetail(widget.id);
      if (!mounted) return;
      setState(() { _d = d; _loading = false; });
      _setupTimer();
    } catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
      }
    }
  }

  void _setupTimer() {
    _timer?.cancel();
    if (_d?['state'] == 'in_progress' && _d?['start_datetime'] != null) {
      final start = DateTime.tryParse('${_d!['start_datetime']}Z')?.toLocal();
      final expected = (_d!['expected_minutes'] as int? ?? 0);
      if (start != null && expected > 0) {
        void tick() {
          final elapsed = DateTime.now().difference(start);
          setState(() => _remaining = Duration(minutes: expected) - elapsed);
        }
        tick();
        _timer = Timer.periodic(const Duration(seconds: 1), (_) => tick());
      }
    }
  }

  Future<void> _act(Future<dynamic> Function() f, String ok) async {
    try {
      await f();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(ok)));
        _load();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  Future<void> _openMap() async {
    final q = Uri.encodeComponent('${_d?['map_query'] ?? widget.title}');
    final uri = Uri.parse('https://www.google.com/maps/search/?api=1&query=$q');
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication) && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('تعذّر فتح الخريطة')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final api = context.read<AuthProvider>().api;
    final p = context.read<AuthProvider>().profile!;
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: Text(tr('تفاصيل المهمة', 'Task details')), actions: [
        IconButton(icon: const Icon(Icons.refresh), onPressed: _load),
      ]),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _d == null
              ? const Center(child: Text('تعذّر التحميل'))
              : ListView(padding: const EdgeInsets.all(16), children: [
                  _header(cs),
                  if (_d!['state'] == 'in_progress') _timerCard(),
                  const SizedBox(height: 12),
                  _infoCard(cs),
                  const SizedBox(height: 12),
                  _actions(api, p),
                  const SizedBox(height: 16),
                  if ((_d!['media'] as List).isNotEmpty) _mediaCard(),
                  _historyCard(cs),
                ]),
    );
  }

  Widget _header(ColorScheme cs) {
    final st = _d!['state'] as String;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(gradient: LinearGradient(colors: [cs.primary, cs.primary.withValues(alpha: 0.7)]), borderRadius: BorderRadius.circular(16)),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('${_d!['name']}', style: const TextStyle(color: Colors.white70, fontSize: 12)),
        Text('${_d!['title']}', style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900)),
        const SizedBox(height: 6),
        Wrap(spacing: 6, children: [
          _chip(woStateLabel(st), kWoStateColor[st] ?? Colors.white24),
          _chip('${_d!['service']}', Colors.white24),
        ]),
      ]),
    );
  }

  Widget _chip(String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(20)),
        child: Text(t, style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w700)),
      );

  Widget _timerCard() {
    final over = _remaining.isNegative;
    final dur = _remaining.abs();
    final t = '${dur.inHours.toString().padLeft(2, '0')}:${(dur.inMinutes % 60).toString().padLeft(2, '0')}:${(dur.inSeconds % 60).toString().padLeft(2, '0')}';
    final c = over ? const Color(0xFFE5484D) : const Color(0xFF16A34A);
    return Container(
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(color: c.withValues(alpha: 0.10), borderRadius: BorderRadius.circular(14), border: Border.all(color: c)),
      child: Row(children: [
        Icon(over ? Icons.timer_off : Icons.timer, color: c, size: 34),
        const SizedBox(width: 14),
        Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(over ? 'تجاوز الوقت المحدّد' : 'الوقت المتبقّي', style: TextStyle(color: c, fontWeight: FontWeight.w700)),
          Text(t, style: TextStyle(color: c, fontSize: 30, fontWeight: FontWeight.w900, fontFeatures: const [])),
        ]),
        const Spacer(),
        Text('المحدّد: ${_d!['expected_minutes']} د', style: TextStyle(color: Theme.of(context).colorScheme.outline)),
      ]),
    );
  }

  Widget _infoCard(ColorScheme cs) => Card(
        child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          _row(Icons.location_on, tr('الموقع', 'Location'),
              (_d!['location_detail'] != null && (_d!['location_detail'] as Map)['full'] != null)
                  ? '${(_d!['location_detail'] as Map)['full']}'
                  : '${_d!['facility']}${_d!['location'] != null ? ' — ${_d!['location']}' : ''}'),
          _row(Icons.person, 'المُسنَد إليه', '${_d!['assignee'] ?? '—'}'),
          _row(Icons.flag, 'الأولوية', '${_d!['priority']}'),
          _row(Icons.schedule, 'الموعد', '${_d!['deadline'] ?? '—'}'),
          if (_d!['description'] != null) ...[
            const Divider(),
            Text(tr('الوصف', 'Description'), style: TextStyle(color: cs.outline, fontSize: 12)),
            Text('${_d!['description']}'),
          ],
          const SizedBox(height: 10),
          OutlinedButton.icon(onPressed: _openMap, icon: const Icon(Icons.directions), label: Text(tr('توجّه إلى الموقع (خريطة)', 'Navigate (map)'))),
        ])),
      );

  Widget _row(IconData i, String l, String v) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(children: [
          Icon(i, size: 18, color: Theme.of(context).colorScheme.outline),
          const SizedBox(width: 8),
          Text('$l: ', style: TextStyle(color: Theme.of(context).colorScheme.outline)),
          Expanded(child: Text(v, style: const TextStyle(fontWeight: FontWeight.w600))),
        ]),
      );

  Widget _actions(dynamic api, dynamic p) {
    final st = _d!['state'] as String;
    final children = <Widget>[];
    if (st == 'new' || st == 'assigned') {
      children.add(FilledButton.icon(
        onPressed: () => _act(() => api.workOrderStart(widget.id), 'بدأ التنفيذ — العدّاد يعمل'),
        icon: const Icon(Icons.play_arrow), label: Text(tr('بدء التنفيذ', 'Start'))));
    }
    if (st == 'in_progress') {
      children.add(FilledButton.icon(
        style: FilledButton.styleFrom(backgroundColor: const Color(0xFF16A34A)),
        onPressed: () => _act(() => api.workOrderDone(widget.id), 'تم الإرسال للاعتماد'),
        icon: const Icon(Icons.check), label: Text(tr('إتمام وإرسال للاعتماد', 'Complete & submit'))));
    }
    if (st == 'done' && (p.isSupervisor || p.isAdmin)) {
      children.add(FilledButton.icon(
        style: FilledButton.styleFrom(backgroundColor: const Color(0xFF0B6EA8)),
        onPressed: () => _act(() => api.workOrderVerify(widget.id), 'تم الاعتماد والإغلاق'),
        icon: const Icon(Icons.verified), label: Text(tr('اعتماد وإغلاق', 'Approve & close'))));
    }
    children.add(Row(children: [
      Expanded(child: OutlinedButton.icon(onPressed: () => _capture(false),
          icon: const Icon(Icons.photo_camera), label: Text(tr('صورة', 'Photo')))),
      const SizedBox(width: 8),
      Expanded(child: OutlinedButton.icon(onPressed: () => _capture(true),
          icon: const Icon(Icons.videocam), label: Text(tr('فيديو', 'Video')))),
    ]));
    children.add(OutlinedButton.icon(onPressed: _addNote, icon: const Icon(Icons.add_comment), label: Text(tr('إضافة ملاحظة', 'Add note'))));
    return Column(children: [for (final c in children) Padding(padding: const EdgeInsets.only(bottom: 8), child: SizedBox(width: double.infinity, child: c))]);
  }

  Future<void> _capture(bool video) async {
    final api = context.read<AuthProvider>().api;
    try {
      final picker = ImagePicker();
      final XFile? x = video
          ? await picker.pickVideo(source: ImageSource.camera, maxDuration: const Duration(seconds: 60))
          : await picker.pickImage(source: ImageSource.camera, imageQuality: 70, maxWidth: 1600);
      if (x == null) return;
      final bytes = await x.readAsBytes();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('جارٍ الرفع…', 'Uploading…'))));
      await api.workOrderPhoto(widget.id, base64Encode(bytes), x.name, video ? 'video' : 'photo');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تم الرفع للاعتماد', 'Uploaded for approval'))));
        _load();
      }
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  Future<void> _addNote() async {
    final ctrl = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (_) => AlertDialog(
      title: Text(tr('إضافة ملاحظة', 'Add note')),
      content: TextField(controller: ctrl, maxLines: 3, decoration: const InputDecoration(hintText: 'اكتب ملاحظة...')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('إلغاء')),
        FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(tr('إرسال', 'Send'))),
      ],
    ));
    if (ok == true && ctrl.text.trim().isNotEmpty) {
      _act(() => context.read<AuthProvider>().api.workOrderNote(widget.id, ctrl.text.trim()), 'أُضيفت الملاحظة');
    }
  }

  Widget _mediaCard() => Card(child: Padding(padding: const EdgeInsets.all(12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(tr('الصور والفيديو', 'Photos & video'), style: TextStyle(fontWeight: FontWeight.w800)),
        const SizedBox(height: 8),
        SizedBox(height: 90, child: Builder(builder: (ctx) {
          final media = (_d!['media'] as List).map((e) => e as Map).toList();
          return ListView(scrollDirection: Axis.horizontal, children: [
            for (int i = 0; i < media.length; i++)
              Padding(padding: const EdgeInsets.only(left: 8), child: GestureDetector(
                onTap: () async {
                  final tok = await ctx.read<AuthProvider>().api.token;
                  if (!ctx.mounted) return;
                  Navigator.push(ctx, MaterialPageRoute(
                      builder: (_) => MediaViewerScreen(media: media, index: i, token: tok)));
                },
                child: ClipRRect(borderRadius: BorderRadius.circular(10), child: Stack(children: [
                  Image.network('${media[i]['thumb']}', width: 90, height: 90, fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => Container(width: 90, height: 90, color: const Color(0xFFEEF2F7), child: const Icon(Icons.play_circle))),
                  if ('${media[i]['type'] ?? ''}'.toLowerCase().contains('video'))
                    const Positioned.fill(child: Center(child: Icon(Icons.play_circle_fill, color: Colors.white70, size: 34))),
                ])),
              )),
          ]);
        })),
      ])));

  Widget _historyCard(ColorScheme cs) {
    final hist = (_d!['history'] as List).where((h) => (h as Map)['body'] != null && '${h['body']}'.trim().isNotEmpty).toList();
    return Card(child: Padding(padding: const EdgeInsets.all(16), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text(tr('السجل (History)', 'History'), style: TextStyle(fontWeight: FontWeight.w800)),
      const SizedBox(height: 8),
      if (hist.isEmpty) Text(tr('لا سجل بعد', 'No history yet'), style: TextStyle(color: cs.outline)),
      for (final h in hist)
        Padding(padding: const EdgeInsets.symmetric(vertical: 6), child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Icon(Icons.circle, size: 8, color: Color(0xFF0B6EA8)),
          const SizedBox(width: 10),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('${(h as Map)['body']}'),
            Text('${h['author']} · ${'${h['date'] ?? ''}'.replaceAll('T', ' ').substring(0, ('${h['date']}').length.clamp(0, 16))}', style: TextStyle(color: cs.outline, fontSize: 11)),
          ])),
        ])),
    ])));
  }
}
