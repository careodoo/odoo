import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'package:provider/provider.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:geolocator/geolocator.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/webrtc_stream.dart';
import '../core/live_broadcast.dart';
import 'stream_chat_layer.dart';

/// شاشة بثّ الحارس الاحترافية: معاينة الكاميرا الحيّة داخل التطبيق (WebRTC/WHIP)،
/// شارة مباشر + مؤقّت، عدّاد وقائمة المشاهدين لحظياً، وبطاقة بيانات كاملة
/// (اسم الحارس، الموقع، رقم البلاغ، المزوّد). إن كان المزوّد لا يدعم WebRTC،
/// تتحوّل تلقائياً لوضع رابط RTMP (Larix) دون أن يفشل شيء.
class SecurityBroadcastScreen extends StatefulWidget {
  final int? incidentId;
  final int providerId;
  final List<int>? viewerIds;
  final bool cohost; // وضع المشاركة: يبثّ كـ co-host داخل بثّ قائم
  final String? audience; // 'all' | 'client' | 'team'
  const SecurityBroadcastScreen(
      {super.key, this.incidentId, required this.providerId, this.viewerIds, this.cohost = false, this.audience});

  @override
  State<SecurityBroadcastScreen> createState() => _SecurityBroadcastScreenState();
}

class _SecurityBroadcastScreenState extends State<SecurityBroadcastScreen> {
  static const _bg = Color(0xFF0B1220);
  static const _red = Color(0xFFE5484D);
  static const _blue = Color(0xFF4AA8FF);
  static const _green = Color(0xFF37C98A);
  static const _muteGrey = Color(0xFF9CB2CD);

  // الناشر يعيش في الخدمة العامّة ليستمرّ عند التصغير
  WhipBroadcaster? get _bc => LiveBroadcast.instance.bc;
  Map<String, dynamic>? _session;
  Timer? _elapsed, _pollViewers;
  int _seconds = 0, _viewers = 0;
  List<Map> _viewerList = const [];
  bool _muted = false, _starting = true, _webrtc = false;
  String? _error, _ingestUrl;

  int get _iid => (_session?['incident_id'] as int?) ?? widget.incidentId ?? 0;

  @override
  void initState() {
    super.initState();
    WidgetsFlutterBinding.ensureInitialized();
    _begin();
  }

  Future<void> _begin() async {
    try {
      // استئناف بثّ مصغّر قائم لنفس البلاغ (بدل بدء جديد)
      final svc = LiveBroadcast.instance;
      if (svc.isLive && svc.incidentId == (widget.incidentId ?? 0)) {
        _session = svc.session;
        _webrtc = true;
        _seconds = svc.elapsedSeconds;
        _startTimers();
        if (mounted) setState(() => _starting = false);
        return;
      }
      // 1) الأذونات
      final cam = await Permission.camera.request();
      final mic = await Permission.microphone.request();
      if (!cam.isGranted || !mic.isGranted) {
        setState(() { _starting = false; _error = tr('يجب السماح بالكاميرا والميكروفون للبثّ', 'Camera & microphone permission required'); });
        return;
      }
      // 2) الموقع (اختياري)
      double? lat, lng;
      try {
        final p = await Geolocator.getCurrentPosition(
            desiredAccuracy: LocationAccuracy.medium,
            timeLimit: const Duration(seconds: 6));
        lat = p.latitude; lng = p.longitude;
      } catch (_) {}
      // 3) إنشاء الجلسة في الباك ايند (بثّ رئيسي أو مشاركة co-host)
      final api = context.read<AuthProvider>().api;
      final s = widget.cohost
          ? await api.securityStreamCohostStart(widget.incidentId ?? 0, latitude: lat, longitude: lng)
          : await api.securityStreamStart(
              incidentId: widget.incidentId, providerId: widget.providerId,
              viewerIds: (widget.viewerIds?.isNotEmpty ?? false) ? widget.viewerIds : null,
              latitude: lat, longitude: lng, audience: widget.audience);
      _session = s;
      final whip = '${s['whip_url'] ?? ''}';
      if (whip.isNotEmpty) {
        // 4) بثّ WebRTC حقيقي داخل التطبيق
        _webrtc = true;
        final bc = WhipBroadcaster();
        await bc.start(whip);
        LiveBroadcast.instance.begin(bc, s, _iid, widget.cohost);
        _startTimers();
      } else {
        // رجوع لوضع RTMP (Larix)
        _webrtc = false;
        _ingestUrl = '${s['ingest_url'] ?? ''}';
        _startTimers(pollOnly: true);
      }
      if (mounted) setState(() => _starting = false);
    } catch (e) {
      if (mounted) setState(() { _starting = false; _error = '$e'.replaceFirst('Exception: ', ''); });
    }
  }

  void _startTimers({bool pollOnly = false}) {
    if (!pollOnly) {
      _elapsed = Timer.periodic(const Duration(seconds: 1), (_) {
        if (mounted) setState(() => _seconds++);
      });
    }
    _pollViewers = Timer.periodic(const Duration(seconds: 5), (_) => _refreshViewers());
    _refreshViewers();
  }

  Future<void> _refreshViewers() async {
    try {
      final v = await context.read<AuthProvider>().api.securityStreamViewers(_iid);
      if (!mounted) return;
      setState(() {
        _viewers = (v['count'] as int?) ?? 0;
        _viewerList = ((v['viewers'] as List?) ?? const []).cast<Map>();
      });
    } catch (_) {}
  }

  String get _clock {
    final m = (_seconds ~/ 60).toString().padLeft(2, '0');
    final s = (_seconds % 60).toString().padLeft(2, '0');
    return '$m:$s';
  }

  Future<void> _stop() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (d) => AlertDialog(
        backgroundColor: const Color(0xFF152238),
        title: Text(tr('إيقاف البثّ؟', 'Stop stream?'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900)),
        content: Text(tr('سينتهي البثّ المباشر للجميع.', 'The live stream will end for everyone.'), style: const TextStyle(color: _muteGrey)),
        actions: [
          TextButton(onPressed: () => Navigator.pop(d, false), child: Text(tr('متابعة البثّ', 'Keep streaming'))),
          FilledButton(style: FilledButton.styleFrom(backgroundColor: _red), onPressed: () => Navigator.pop(d, true), child: Text(tr('إيقاف', 'Stop'))),
        ],
      ),
    );
    if (ok != true) return;
    final iid = _iid;
    _elapsed?.cancel(); _pollViewers?.cancel();
    try { await LiveBroadcast.instance.end(); } catch (_) {}
    try {
      final api = context.read<AuthProvider>().api;
      if (widget.cohost) { await api.securityStreamCohostStop(iid); }
      else { await api.securityStreamStop(iid); }
    } catch (_) {}
    if (mounted) Navigator.pop(context);
  }

  /// تصغير: نغلق الشاشة ويستمرّ البثّ في الخدمة (يظهر المؤشّر العائم).
  void _minimize() {
    _elapsed?.cancel(); _pollViewers?.cancel();
    Navigator.pop(context);
  }

  void _showViewers() {
    showModalBottomSheet(context: context, backgroundColor: const Color(0xFF152238),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => SafeArea(child: Column(mainAxisSize: MainAxisSize.min, children: [
        Padding(padding: const EdgeInsets.all(16),
            child: Row(children: [
              const Icon(Icons.visibility_rounded, color: _blue, size: 20), const SizedBox(width: 8),
              Text(tr('المشاهدون الآن', 'Watching now') + ' ($_viewers)', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 16)),
            ])),
        if (_viewerList.isEmpty)
          Padding(padding: const EdgeInsets.all(24), child: Text(tr('لا مشاهدين بعد', 'No viewers yet'), style: const TextStyle(color: _muteGrey)))
        else Flexible(child: ListView(shrinkWrap: true, children: [
          for (final v in _viewerList) ListTile(
            leading: const CircleAvatar(backgroundColor: _blue, child: Icon(Icons.person, color: Colors.white, size: 18)),
            title: Text('${v['name'] ?? 'مشاهد'}', style: const TextStyle(color: Colors.white, fontSize: 14)),
            trailing: Text('${v['since'] ?? ''}', style: const TextStyle(color: _muteGrey, fontSize: 12)),
          ),
        ])),
        const SizedBox(height: 8),
      ])));
  }

  /// دردشة البثّ للحارس (لوحة سفلية فوق المعاينة).
  void _showChat() {
    showModalBottomSheet(context: context, isScrollControlled: true, backgroundColor: const Color(0xFF0B1220),
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(20))),
      builder: (_) => Padding(
        padding: EdgeInsets.only(left: 14, right: 14, top: 14, bottom: MediaQuery.of(context).viewInsets.bottom + 14),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          Row(children: [
            const Icon(Icons.forum_rounded, color: _blue, size: 18), const SizedBox(width: 8),
            Text(tr('دردشة البثّ', 'Live chat'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 15)),
          ]),
          const SizedBox(height: 10),
          StreamChatLayer(incidentId: _iid),
        ]),
      ));
  }

  @override
  void dispose() {
    // لا نوقف الناشر هنا — الخدمة تملكه ليستمرّ البثّ عند التصغير
    _elapsed?.cancel(); _pollViewers?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: false,
      onPopInvokedWithResult: (didPop, _) { if (!didPop) _minimize(); },
      child: Scaffold(
        backgroundColor: _bg,
        body: SafeArea(
          child: _starting
              ? _center(const CircularProgressIndicator(color: _red), tr('جارٍ بدء البثّ…', 'Starting stream…'))
              : _error != null
                  ? _center(const Icon(Icons.error_outline_rounded, color: _red, size: 48), _error!)
                  : _webrtc ? _liveView() : _rtmpFallback(),
        ),
      ),
    );
  }

  Widget _center(Widget icon, String msg) => Center(child: Padding(
        padding: const EdgeInsets.all(28),
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          icon, const SizedBox(height: 16),
          Text(msg, textAlign: TextAlign.center, style: const TextStyle(color: Colors.white, fontSize: 15, fontWeight: FontWeight.w700)),
          if (_error != null) ...[
            const SizedBox(height: 20),
            FilledButton(style: FilledButton.styleFrom(backgroundColor: const Color(0xFF152238)),
                onPressed: () => Navigator.pop(context), child: Text(tr('رجوع', 'Back'))),
          ],
        ]),
      ));

  // ---- عرض البثّ الحيّ (WebRTC) ----
  Widget _liveView() {
    final s = _session ?? const {};
    return Stack(children: [
      // الفيديو ملء الشاشة
      Positioned.fill(child: RTCVideoView(_bc!.renderer,
          objectFit: RTCVideoViewObjectFit.RTCVideoViewObjectFitCover, mirror: _bc!.isFront)),
      // تدرّج علوي/سفلي لقراءة النصوص
      Positioned.fill(child: IgnorePointer(child: DecoratedBox(decoration: BoxDecoration(
          gradient: LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter,
              colors: [Colors.black.withValues(alpha: .55), Colors.transparent, Colors.transparent, Colors.black.withValues(alpha: .75)],
              stops: const [0, .2, .6, 1]))))),
      // الشريط العلوي: مباشر + مؤقّت + مشاهدون
      Positioned(top: 12, left: 12, right: 12, child: Row(children: [
        Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(color: _red, borderRadius: BorderRadius.circular(20)),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              const _Pulse(), const SizedBox(width: 6),
              Text(tr('مباشر', 'LIVE'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 12)),
            ])),
        const SizedBox(width: 8),
        Container(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
            decoration: BoxDecoration(color: Colors.black.withValues(alpha: .45), borderRadius: BorderRadius.circular(20)),
            child: Row(mainAxisSize: MainAxisSize.min, children: [
              const Icon(Icons.schedule_rounded, color: Colors.white, size: 14), const SizedBox(width: 5),
              Text(_clock, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 12.5, fontFeatures: [FontFeature.tabularFigures()])),
            ])),
        const Spacer(),
        InkWell(onTap: _minimize, borderRadius: BorderRadius.circular(20),
            child: Container(padding: const EdgeInsets.all(8), margin: const EdgeInsets.only(left: 8),
                decoration: BoxDecoration(color: Colors.black.withValues(alpha: .45), shape: BoxShape.circle),
                child: const Icon(Icons.picture_in_picture_alt_rounded, color: Colors.white, size: 17))),
        InkWell(onTap: _showChat, borderRadius: BorderRadius.circular(20),
            child: Container(padding: const EdgeInsets.all(8), margin: const EdgeInsets.only(left: 8),
                decoration: BoxDecoration(color: Colors.black.withValues(alpha: .45), shape: BoxShape.circle),
                child: const Icon(Icons.forum_rounded, color: Colors.white, size: 17))),
        InkWell(onTap: _showViewers, borderRadius: BorderRadius.circular(20),
            child: Container(padding: const EdgeInsets.symmetric(horizontal: 11, vertical: 6),
                decoration: BoxDecoration(color: Colors.black.withValues(alpha: .45), borderRadius: BorderRadius.circular(20)),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  const Icon(Icons.visibility_rounded, color: _blue, size: 15), const SizedBox(width: 5),
                  Text('$_viewers', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 13)),
                ]))),
      ])),
      // بطاقة البيانات السفلية
      Positioned(left: 12, right: 12, bottom: 92, child: _infoCard(s)),
      // أزرار التحكّم
      Positioned(left: 0, right: 0, bottom: 18, child: Row(mainAxisAlignment: MainAxisAlignment.center, children: [
        _ctrl(Icons.cameraswitch_rounded, tr('تبديل', 'Flip'), _blue, () async { await _bc?.switchCamera(); if (mounted) setState(() {}); }),
        const SizedBox(width: 22),
        _ctrl(_muted ? Icons.mic_off_rounded : Icons.mic_rounded, _muted ? tr('مكتوم', 'Muted') : tr('صوت', 'Mic'),
            _muted ? _muteGrey : _green, () { _bc?.setMuted(!_muted); setState(() => _muted = !_muted); }),
        const SizedBox(width: 22),
        _ctrl(Icons.stop_rounded, tr('إيقاف', 'Stop'), _red, _stop, big: true),
      ])),
    ]);
  }

  Widget _infoCard(Map s) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(color: Colors.black.withValues(alpha: .5), borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.white.withValues(alpha: .12))),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisSize: MainAxisSize.min, children: [
          _line(Icons.person_rounded, '${s['guard'] ?? tr('الحارس', 'Guard')}'),
          if ((s['premise'] ?? '').toString().isNotEmpty) _line(Icons.place_rounded, '${s['premise']}'),
          if ((s['client'] ?? '').toString().isNotEmpty) _line(Icons.business_rounded, '${s['client']}'),
          Row(children: [
            if (_iid > 0) _chip('${tr('بلاغ', 'Incident')} #$_iid'),
            if ((s['provider'] ?? '').toString().isNotEmpty) ...[const SizedBox(width: 6), _chip('${s['provider']}')],
          ]),
        ]),
      );

  Widget _line(IconData i, String t) => Padding(padding: const EdgeInsets.only(bottom: 4),
      child: Row(children: [Icon(i, color: _blue, size: 15), const SizedBox(width: 7),
        Expanded(child: Text(t, maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 13)))]));

  Widget _chip(String t) => Container(margin: const EdgeInsets.only(top: 6),
      padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 3),
      decoration: BoxDecoration(color: Colors.white.withValues(alpha: .12), borderRadius: BorderRadius.circular(7)),
      child: Text(t, style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700)));

  Widget _ctrl(IconData i, String label, Color c, VoidCallback onTap, {bool big = false}) => Column(mainAxisSize: MainAxisSize.min, children: [
        Material(color: big ? c : Colors.black.withValues(alpha: .5), shape: const CircleBorder(),
            child: InkWell(customBorder: const CircleBorder(), onTap: onTap,
                child: Padding(padding: EdgeInsets.all(big ? 18 : 14), child: Icon(i, color: big ? Colors.white : c, size: big ? 30 : 24)))),
        const SizedBox(height: 5),
        Text(label, style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700)),
      ]);

  // ---- رجوع لوضع RTMP (Larix) عندما لا يدعم المزوّد WebRTC ----
  Widget _rtmpFallback() {
    final s = _session ?? const {};
    final ingest = _ingestUrl ?? '';
    return SingleChildScrollView(padding: const EdgeInsets.all(20), child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
      const SizedBox(height: 10),
      Row(children: [const _Pulse(), const SizedBox(width: 8),
        Text(tr('جاهز للبثّ عبر RTMP', 'Ready to stream via RTMP'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 17))]),
      const SizedBox(height: 6),
      Text(tr('هذا المزوّد لا يدعم البثّ داخل التطبيق. الصق الرابط في تطبيق Larix Broadcaster للبثّ.',
          'This provider does not support in-app streaming. Paste the URL into Larix Broadcaster.'),
          style: const TextStyle(color: _muteGrey, fontSize: 12.5, height: 1.5)),
      const SizedBox(height: 16),
      _infoCard(s),
      const SizedBox(height: 16),
      if (ingest.isNotEmpty) Container(padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(color: const Color(0xFF152238), borderRadius: BorderRadius.circular(12)),
          child: Row(children: [
            Expanded(child: SelectableText(ingest, style: const TextStyle(color: _blue, fontSize: 11.5))),
            IconButton(icon: const Icon(Icons.copy_rounded, color: Colors.white, size: 18),
                onPressed: () { Clipboard.setData(ClipboardData(text: ingest));
                  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('نُسخ', 'Copied')), backgroundColor: _green)); }),
          ])),
      const SizedBox(height: 12),
      OutlinedButton.icon(onPressed: () => launchUrl(Uri.parse('https://softvelum.com/larix/'), mode: LaunchMode.externalApplication),
          icon: const Icon(Icons.open_in_new_rounded, color: _blue), label: Text(tr('تحميل Larix', 'Get Larix')),
          style: OutlinedButton.styleFrom(foregroundColor: _blue, side: const BorderSide(color: _blue))),
      const SizedBox(height: 8),
      FilledButton.icon(onPressed: _stop, icon: const Icon(Icons.stop_rounded),
          style: FilledButton.styleFrom(backgroundColor: _red), label: Text(tr('إنهاء البثّ', 'End stream'))),
    ]));
  }
}

/// نقطة نابضة حمراء لشارة «مباشر».
class _Pulse extends StatefulWidget {
  const _Pulse();
  @override
  State<_Pulse> createState() => _PulseState();
}

class _PulseState extends State<_Pulse> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 900))..repeat(reverse: true);
  @override
  void dispose() { _c.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) => FadeTransition(opacity: Tween(begin: .35, end: 1.0).animate(_c),
      child: Container(width: 9, height: 9, decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle)));
}
