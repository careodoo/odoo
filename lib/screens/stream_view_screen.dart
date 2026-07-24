import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/webrtc_stream.dart';
import 'stream_chat_layer.dart';
import 'security_broadcast_screen.dart';

/// شاشة مشاهدة البثّ الحيّ للعميل والفريق (WebRTC/WHEP داخل التطبيق).
/// تعرض الفيديو الحيّ + شارة مباشر + عدّاد المشاهدين + بطاقة بيانات كاملة
/// (اسم الحارس، الموقع، رقم البلاغ، وقت البدء). [isClient] تحدّد نقطة النهاية
/// المقيّدة بنطاق العميل.
class StreamViewScreen extends StatefulWidget {
  final int incidentId;
  final bool isClient;
  const StreamViewScreen({super.key, required this.incidentId, this.isClient = false});

  @override
  State<StreamViewScreen> createState() => _StreamViewScreenState();
}

class _StreamViewScreenState extends State<StreamViewScreen> {
  static const _bg = Color(0xFF0B1220);
  static const _red = Color(0xFFE5484D);
  static const _blue = Color(0xFF4AA8FF);
  static const _green = Color(0xFF37C98A);
  static const _muteGrey = Color(0xFF9CB2CD);

  WhepViewer? _vw;
  WhepViewer? _pip; // بثّ مشارك (co-host) يظهر كصورة سفلية
  int? _pipSession;
  Map<String, dynamic>? _info;
  Timer? _poll;
  bool _loading = true, _live = false, _hasVideo = false, _pipVideo = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _begin();
  }

  Future<void> _begin() async {
    try {
      final api = context.read<AuthProvider>().api;
      final info = widget.isClient
          ? await api.clientSecurityWatchStream(widget.incidentId)
          : await api.securityStreamWatch(widget.incidentId);
      _info = info;
      _live = info['live'] == true;
      if (!_live) {
        setState(() { _loading = false; });
        return;
      }
      final whep = '${info['whep_url'] ?? ''}';
      if (whep.isEmpty) {
        setState(() { _loading = false; _error = tr('البثّ لا يدعم المشاهدة داخل التطبيق', 'Stream not viewable in-app'); });
        return;
      }
      final vw = WhepViewer(onTrack: () { if (mounted) setState(() => _hasVideo = true); });
      await vw.start(whep);
      _vw = vw;
      _poll = Timer.periodic(const Duration(seconds: 6), (_) => _refresh());
      _refreshCohosts();
      if (mounted) setState(() => _loading = false);
    } catch (e) {
      if (mounted) setState(() { _loading = false; _error = '$e'.replaceFirst('Exception: ', ''); });
    }
  }

  Future<void> _refresh() async {
    try {
      final api = context.read<AuthProvider>().api;
      final info = await api.securityStreamInfo(widget.incidentId);
      if (!mounted) return;
      final stillLive = info['live'] == true;
      setState(() { _info = {..._info ?? {}, ...info}; _live = stillLive; });
      if (!stillLive) { _poll?.cancel(); }
      _refreshCohosts();
    } catch (_) {}
  }

  /// يجلب المشاركين (co-hosts) ويعرض أوّلهم كصورة سفلية (PiP).
  Future<void> _refreshCohosts() async {
    if (widget.isClient) return; // العميل يشاهد فقط الرئيسي حالياً
    try {
      final cos = await context.read<AuthProvider>().api.securityStreamCohosts(widget.incidentId);
      final live = cos.cast<Map>().where((c) => (c['whep_url'] ?? '').toString().isNotEmpty).toList();
      if (live.isEmpty) {
        if (_pip != null) { await _pip?.stop(); if (mounted) setState(() { _pip = null; _pipSession = null; _pipVideo = false; }); }
        return;
      }
      final first = live.first;
      final sid = first['session_id'] as int?;
      if (sid == _pipSession) return; // نفس المشارك — لا شيء
      await _pip?.stop();
      final p = WhepViewer(onTrack: () { if (mounted) setState(() => _pipVideo = true); });
      await p.start('${first['whep_url']}');
      if (mounted) setState(() { _pip = p; _pipSession = sid; _pipVideo = false; });
    } catch (_) {}
  }

  Future<void> _leave() async {
    _poll?.cancel();
    try { await _vw?.stop(); } catch (_) {}
    try { await _pip?.stop(); } catch (_) {}
    try { await context.read<AuthProvider>().api.securityStreamLeave(widget.incidentId); } catch (_) {}
    if (mounted) Navigator.pop(context);
  }

  /// عضو الفريق يشارك في البثّ (co-host) — يفتح شاشة بثّ بوضع المشاركة.
  Future<void> _joinAsCohost() async {
    Navigator.push(context, MaterialPageRoute(
        builder: (_) => SecurityBroadcastScreen(incidentId: widget.incidentId, providerId: -1, cohost: true)));
  }

  @override
  void dispose() {
    _poll?.cancel();
    _vw?.stop();
    _pip?.stop();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final s = _info ?? const {};
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) { if (!didPop) _leave(); },
      child: Scaffold(
        backgroundColor: _bg,
        body: SafeArea(child: _loading
            ? _center(const CircularProgressIndicator(color: _red), tr('جارٍ الاتصال بالبثّ…', 'Connecting to stream…'))
            : _error != null
                ? _center(const Icon(Icons.error_outline_rounded, color: _red, size: 48), _error!)
                : !_live
                    ? _center(const Icon(Icons.videocam_off_rounded, color: _muteGrey, size: 48), tr('لا يوجد بثّ مباشر حالياً', 'No live stream right now'))
                    : _player(s)),
      ),
    );
  }

  Widget _center(Widget icon, String msg) => Center(child: Padding(padding: const EdgeInsets.all(28),
      child: Column(mainAxisSize: MainAxisSize.min, children: [
        icon, const SizedBox(height: 16),
        Text(msg, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w700)),
        const SizedBox(height: 20),
        FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFF152238)),
            onPressed: () => Navigator.pop(context), child: Text(tr('رجوع', 'Back'))),
      ])));

  Widget _player(Map s) {
    final kbd = MediaQuery.of(context).viewInsets.bottom;
    return Stack(children: [
      Positioned.fill(child: _hasVideo
          ? RTCVideoView(_vw!.renderer, objectFit: RTCVideoViewObjectFit.RTCVideoViewObjectFitContain)
          : const Center(child: CircularProgressIndicator(color: _blue))),
      Positioned.fill(child: IgnorePointer(child: DecoratedBox(decoration: BoxDecoration(
          gradient: LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter,
              colors: [Colors.black.withValues(alpha: .55), Colors.transparent, Colors.transparent, Colors.black.withValues(alpha: .82)],
              stops: const [0, .16, .5, 1]))))),
      // شريط علوي
      Positioned(top: 12, left: 12, right: 12, child: Row(children: [
        Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(color: _red, borderRadius: BorderRadius.circular(20)),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              Container(width: 8, height: 8, decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle)),
              const SizedBox(width: 6), Text(tr('مباشر', 'LIVE'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 12)),
            ])),
        const SizedBox(width: 8),
        Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(color: Colors.black.withValues(alpha: .45), borderRadius: BorderRadius.circular(20)),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              const Icon(Icons.visibility_rounded, color: _blue, size: 14), const SizedBox(width: 5),
              Text('${s['viewer_count'] ?? 0}', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 12.5)),
            ])),
        const Spacer(),
        if (!widget.isClient)
          IconButton(onPressed: _joinAsCohost, tooltip: tr('شارك في البثّ', 'Join stream'),
              icon: const Icon(Icons.video_call_rounded, color: _green)),
        IconButton(onPressed: _leave, icon: const Icon(Icons.close_rounded, color: Colors.white)),
      ])),
      // بطاقة بيانات مصغّرة أعلى
      Positioned(top: 56, left: 12, right: 12, child: _headerCard(s)),
      // صورة المشارك السفلية (PiP)
      if (_pip != null)
        Positioned(right: 12, top: 118, child: _pipView()),
      // الأسفل: الدردشة الحيّة (ترتفع مع الكيبورد)
      Positioned(left: 12, right: 12, bottom: 14 + kbd,
          child: StreamChatLayer(incidentId: widget.incidentId, isClient: widget.isClient)),
    ]);
  }

  Widget _headerCard(Map s) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
        decoration: BoxDecoration(color: Colors.black.withValues(alpha: .42), borderRadius: BorderRadius.circular(14)),
        child: Row(children: [
          const CircleAvatar(radius: 16, backgroundColor: _blue, child: Icon(Icons.person, color: Colors.white, size: 18)),
          const SizedBox(width: 9),
          Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
            Text('${s['guard'] ?? tr('الحارس', 'Guard')}', maxLines: 1, overflow: TextOverflow.ellipsis,
                style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13.5)),
            Text([if ((s['premise'] ?? '').toString().isNotEmpty) '${s['premise']}',
                  '${tr('بلاغ', 'Incident')} #${widget.incidentId}'].join(' · '),
                maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Color(0xFF9CB2CD), fontSize: 11)),
          ])),
        ]),
      );

  Widget _pipView() => Container(
        width: 104, height: 150,
        clipBehavior: Clip.antiAlias,
        decoration: BoxDecoration(borderRadius: BorderRadius.circular(12),
            border: Border.all(color: _green, width: 2), color: Colors.black),
        child: Stack(children: [
          Positioned.fill(child: _pipVideo
              ? RTCVideoView(_pip!.renderer, objectFit: RTCVideoViewObjectFit.RTCVideoViewObjectFitCover)
              : const Center(child: SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: _green)))),
          Positioned(bottom: 0, left: 0, right: 0, child: Container(
            color: Colors.black.withValues(alpha: .5), padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 2),
            child: Text(tr('مشارك', 'Co-host'), style: const TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.w700)))),
        ]),
      );
}
