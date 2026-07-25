import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:webview_flutter/webview_flutter.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// سجل كل عمليات البثّ المؤرشفة بتفاصيلها + إعادة تشغيل التسجيلات داخل التطبيق
/// (مشغّل Cloudflare عبر WebView). يعمل للفريق والعميل (isClient يقيّده بمواقعه).
class StreamArchiveScreen extends StatefulWidget {
  final bool isClient;
  const StreamArchiveScreen({super.key, this.isClient = false});
  @override
  State<StreamArchiveScreen> createState() => _StreamArchiveScreenState();
}

class _StreamArchiveScreenState extends State<StreamArchiveScreen> {
  static const _bg = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _blue = Color(0xFF4AA8FF);
  static const _green = Color(0xFF37C98A);
  static const _grey = Color(0xFF9CB2CD);

  List<Map> _items = const [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final l = await context.read<AuthProvider>().api.securityStreamArchive(isClient: widget.isClient);
      if (mounted) setState(() { _items = l.cast<Map>(); _loading = false; });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  String _dur(int s) {
    if (s <= 0) return '—';
    final h = s ~/ 3600, m = (s % 3600) ~/ 60, sec = s % 60;
    return h > 0 ? '$h:${m.toString().padLeft(2, '0')}:${sec.toString().padLeft(2, '0')}'
                 : '$m:${sec.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(backgroundColor: const Color(0xFF1E3A5F), foregroundColor: Colors.white,
          title: Text(tr('سجل البثّ', 'Broadcasts archive')),
          actions: [IconButton(onPressed: () { setState(() => _loading = true); _load(); }, icon: const Icon(Icons.refresh_rounded))]),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: _blue))
          : _items.isEmpty
              ? _empty()
              : RefreshIndicator(
                  onRefresh: _load, color: _blue,
                  child: ListView.builder(
                    padding: const EdgeInsets.all(12),
                    itemCount: _items.length,
                    itemBuilder: (_, i) => _card_(_items[i]),
                  )),
    );
  }

  Widget _empty() => Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
        const Icon(Icons.movie_creation_outlined, size: 64, color: _grey),
        const SizedBox(height: 12),
        Text(tr('لا بثوث مؤرشفة بعد', 'No archived broadcasts yet'), style: const TextStyle(color: _grey, fontWeight: FontWeight.w700)),
      ]));

  Widget _card_(Map b) {
    final rec = b['has_recording'] == true;
    final thumb = '${b['thumbnail'] ?? ''}';
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.white.withValues(alpha: .06))),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: () => _open(b),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          // الصورة المصغّرة + شارة التسجيل/المدة
          Stack(children: [
            AspectRatio(aspectRatio: 16 / 8, child: thumb.isNotEmpty
                ? Image.network(thumb, fit: BoxFit.cover, errorBuilder: (_, __, ___) => _thumbPlaceholder())
                : _thumbPlaceholder()),
            if (rec) Positioned(right: 8, top: 8, child: _pill(Icons.play_circle_fill_rounded, tr('تسجيل', 'Recording'), _green)),
            Positioned(left: 8, bottom: 8, child: _pill(Icons.schedule_rounded, _dur((b['duration'] as int?) ?? 0), Colors.black.withValues(alpha: .6))),
            Positioned(right: 8, bottom: 8, child: _pill(Icons.visibility_rounded, '${b['peak_viewers'] ?? 0}', Colors.black.withValues(alpha: .6))),
          ]),
          Padding(padding: const EdgeInsets.all(12), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              const Icon(Icons.person_rounded, color: _blue, size: 15), const SizedBox(width: 6),
              Expanded(child: Text('${b['guard'] ?? tr('حارس', 'Guard')}', maxLines: 1, overflow: TextOverflow.ellipsis,
                  style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 14))),
            ]),
            const SizedBox(height: 4),
            if ((b['premise'] ?? '').toString().isNotEmpty)
              Row(children: [const Icon(Icons.place_rounded, color: _grey, size: 13), const SizedBox(width: 5),
                Expanded(child: Text('${b['premise']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: _grey, fontSize: 12)))]),
            const SizedBox(height: 4),
            Row(children: [
              const Icon(Icons.event_rounded, color: _grey, size: 12), const SizedBox(width: 5),
              Text('${b['started_at'] ?? ''}'.replaceFirst('T', ' '), style: const TextStyle(color: _grey, fontSize: 11)),
              const Spacer(),
              if (rec) Row(children: [const Icon(Icons.play_arrow_rounded, color: _green, size: 16),
                Text(tr('تشغيل', 'Play'), style: const TextStyle(color: _green, fontSize: 12, fontWeight: FontWeight.w800))])
              else Text(tr('قيد المعالجة', 'Processing'), style: const TextStyle(color: _grey, fontSize: 11)),
            ]),
          ])),
        ]),
      ),
    );
  }

  Widget _thumbPlaceholder() => Container(color: const Color(0xFF0E1A2E),
      child: const Center(child: Icon(Icons.videocam_off_rounded, color: _grey, size: 34)));

  Widget _pill(IconData i, String t, Color c) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(color: c, borderRadius: BorderRadius.circular(20)),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(i, color: Colors.white, size: 12), const SizedBox(width: 3),
          Text(t, style: const TextStyle(color: Colors.white, fontSize: 10.5, fontWeight: FontWeight.w800)),
        ]),
      );

  void _open(Map b) {
    // فتح شاشة التفاصيل الكاملة (تسجيل + معلومات + دردشة + مشاهدون)
    Navigator.push(context, MaterialPageRoute(
        builder: (_) => _DetailScreen(sid: (b['session_id'] as num).toInt(), isClient: widget.isClient, brief: b)));
  }
}

/// تفاصيل بثّ مؤرشف: مشغّل التسجيل + بطاقة معلومات + دردشة البثّ + قائمة المشاهدين.
class _DetailScreen extends StatefulWidget {
  final int sid;
  final bool isClient;
  final Map brief;
  const _DetailScreen({required this.sid, required this.isClient, required this.brief});
  @override
  State<_DetailScreen> createState() => _DetailScreenState();
}

class _DetailScreenState extends State<_DetailScreen> {
  static const _bg = Color(0xFF0B1220);
  static const _card = Color(0xFF152238);
  static const _blue = Color(0xFF4AA8FF);
  static const _green = Color(0xFF37C98A);
  static const _grey = Color(0xFF9CB2CD);

  Map _d = const {};
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _d = widget.brief;
    _load();
  }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.securityStreamArchiveDetail(widget.sid, isClient: widget.isClient);
      if (mounted) setState(() { _d = d; _loading = false; });
    } catch (_) {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final rec = _d['has_recording'] == true && '${_d['recording_url'] ?? ''}'.isNotEmpty;
    final msgs = (_d['messages'] as List?) ?? const [];
    final viewers = (_d['viewers_list'] as List?) ?? const [];
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(backgroundColor: const Color(0xFF1E3A5F), foregroundColor: Colors.white,
          title: Text(tr('تفاصيل البثّ', 'Broadcast details'))),
      body: ListView(padding: const EdgeInsets.all(12), children: [
        // المشغّل أو لوحة «قيد المعالجة»
        ClipRRect(borderRadius: BorderRadius.circular(16),
          child: AspectRatio(aspectRatio: 16 / 9, child: rec
              ? _PlayerInline(url: '${_d['recording_url']}'.replaceFirst('/manifest/video.m3u8', '/iframe'))
              : Container(color: Colors.black, child: Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.hourglass_bottom_rounded, color: _grey, size: 40), const SizedBox(height: 8),
                  Text(tr('التسجيل قيد المعالجة', 'Recording processing'), style: const TextStyle(color: _grey)),
                ]))))),
        const SizedBox(height: 14),
        // بطاقة المعلومات
        Container(padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.white.withValues(alpha: .06))),
          child: Column(children: [
            _info(Icons.person_rounded, tr('الحارس', 'Guard'), '${_d['guard'] ?? '—'}'),
            _info(Icons.place_rounded, tr('الموقع', 'Premise'), '${_d['premise'] ?? '—'}'),
            if ((_d['client'] ?? '').toString().isNotEmpty)
              _info(Icons.apartment_rounded, tr('العميل', 'Client'), '${_d['client']}'),
            _info(Icons.event_rounded, tr('البداية', 'Started'), '${_d['started_at'] ?? '—'}'),
            _info(Icons.event_available_rounded, tr('النهاية', 'Ended'), '${_d['ended_at'] ?? '—'}'),
            _info(Icons.visibility_rounded, tr('ذروة المشاهدين', 'Peak viewers'), '${_d['peak_viewers'] ?? 0}'),
            _info(Icons.groups_rounded, tr('إجمالي المشاهدين', 'Total viewers'), '${_d['total_viewers'] ?? 0}'),
            _info(Icons.campaign_rounded, tr('الجمهور', 'Audience'),
                _d['audience'] == 'client' ? tr('العميل فقط', 'Client only') : tr('الفريق والعميل', 'Team & client')),
          ])),
        const SizedBox(height: 14),
        // دردشة البثّ (إعادة عرض)
        _section(Icons.chat_rounded, tr('دردشة البثّ', 'Broadcast chat'), msgs.length),
        if (msgs.isEmpty) _muted(tr('لا رسائل في هذا البثّ', 'No messages in this broadcast'))
        else ...msgs.map((m) => _msg(m as Map)),
        const SizedBox(height: 14),
        // المشاهدون
        _section(Icons.people_rounded, tr('المشاهدون', 'Viewers'), viewers.length),
        if (viewers.isEmpty) _muted(tr('لا مشاهدين مسجّلين', 'No recorded viewers'))
        else ...viewers.map((v) => _viewer(v as Map)),
        if (_loading) const Padding(padding: EdgeInsets.all(16), child: Center(child: CircularProgressIndicator(color: _blue))),
      ]),
    );
  }

  Widget _info(IconData i, String k, String v) => Padding(padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(children: [
        Icon(i, color: _blue, size: 16), const SizedBox(width: 8),
        Text(k, style: const TextStyle(color: _grey, fontSize: 13)),
        const Spacer(),
        Flexible(child: Text(v, textAlign: TextAlign.end, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 13))),
      ]));

  Widget _section(IconData i, String t, int n) => Padding(padding: const EdgeInsets.only(bottom: 8, top: 2),
      child: Row(children: [
        Icon(i, color: _green, size: 18), const SizedBox(width: 8),
        Text(t, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 15)),
        const SizedBox(width: 6),
        Container(padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 1),
            decoration: BoxDecoration(color: _blue.withValues(alpha: .2), borderRadius: BorderRadius.circular(20)),
            child: Text('$n', style: const TextStyle(color: _blue, fontSize: 12, fontWeight: FontWeight.w800))),
      ]));

  Widget _muted(String t) => Padding(padding: const EdgeInsets.symmetric(vertical: 8),
      child: Text(t, style: const TextStyle(color: _grey, fontSize: 13)));

  Widget _msg(Map m) {
    final isClient = m['is_client'] == true;
    return Container(margin: const EdgeInsets.only(bottom: 6), padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(color: _card, borderRadius: BorderRadius.circular(12),
          border: Border(right: BorderSide(color: isClient ? _green : _blue, width: 3))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Row(children: [
          Text('${m['name'] ?? ''}', style: TextStyle(color: isClient ? _green : _blue, fontWeight: FontWeight.w800, fontSize: 12.5)),
          const Spacer(),
          Text('${m['at'] ?? ''}', style: const TextStyle(color: _grey, fontSize: 11)),
        ]),
        const SizedBox(height: 3),
        Text('${m['body'] ?? ''}', style: const TextStyle(color: Colors.white, fontSize: 13.5)),
      ]));
  }

  Widget _viewer(Map v) => Padding(padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(children: [
        const CircleAvatar(radius: 12, backgroundColor: Color(0xFF294059), child: Icon(Icons.person_rounded, size: 14, color: Colors.white)),
        const SizedBox(width: 8),
        Text('${v['name'] ?? ''}', style: const TextStyle(color: Colors.white, fontSize: 13)),
        const Spacer(),
        if ((v['joined'] ?? '').toString().isNotEmpty)
          Text(tr('انضم ${v['joined']}', 'joined ${v['joined']}'), style: const TextStyle(color: _grey, fontSize: 11)),
      ]));
}

/// مشغّل مضمّن (WebView) داخل بطاقة التفاصيل.
class _PlayerInline extends StatefulWidget {
  final String url;
  const _PlayerInline({required this.url});
  @override
  State<_PlayerInline> createState() => _PlayerInlineState();
}

class _PlayerInlineState extends State<_PlayerInline> {
  late final WebViewController _c;
  @override
  void initState() {
    super.initState();
    _c = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(const Color(0xFF000000))
      ..loadRequest(Uri.parse(widget.url));
  }

  @override
  Widget build(BuildContext context) => WebViewWidget(controller: _c);
}
