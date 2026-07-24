import 'dart:async';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'package:http/http.dart' as http;

/// عميل WHIP/WHEP للبثّ المباشر داخل التطبيق عبر WebRTC (يتوافق مع Cloudflare
/// Stream وغيره). لا يعتمد على أي SDK خاص — مجرد تبادل SDP عبر HTTP:
///   • WHIP: الحارس ينشر الكاميرا/الميكروفون (POST offer → answer).
///   • WHEP: العميل/الفريق يستقبل الفيديو (POST offer recvonly → answer).
/// مبنيّ على المعيار المفتوح، فيبقى الكود ثابتاً مهما تغيّر المزوّد.

const Map<String, dynamic> _kIce = {
  'iceServers': [
    {'urls': 'stun:stun.cloudflare.com:3478'},
    {'urls': 'stun:stun.l.google.com:19302'},
  ],
  'sdpSemantics': 'unified-plan',
};

/// ناشر WHIP — يفتح الكاميرا والميكروفون ويبثّهما إلى رابط النشر.
class WhipBroadcaster {
  RTCPeerConnection? _pc;
  MediaStream? _local;
  String? _resourceUrl; // رابط المورد لإنهاء البثّ (DELETE)
  final RTCVideoRenderer renderer = RTCVideoRenderer();

  bool _frontCamera = true;
  bool get isFront => _frontCamera;

  /// يهيّئ العرض المحلي ويبدأ النشر إلى [whipUrl]. يرمي استثناءً عند الفشل.
  Future<void> start(String whipUrl) async {
    await renderer.initialize();
    // 1) الوسائط المحلية (كاميرا أمامية + صوت)
    _local = await navigator.mediaDevices.getUserMedia({
      'audio': true,
      'video': {
        'facingMode': _frontCamera ? 'user' : 'environment',
        'width': {'ideal': 1280},
        'height': {'ideal': 720},
        'frameRate': {'ideal': 30},
      },
    });
    renderer.srcObject = _local;

    // 2) اتصال الأقران، أضف المسارات للإرسال
    _pc = await createPeerConnection(_kIce);
    for (final track in _local!.getTracks()) {
      await _pc!.addTrack(track, _local!);
    }

    // 3) عرض → وصف محلي
    final offer = await _pc!.createOffer();
    await _pc!.setLocalDescription(offer);
    await _waitIce(_pc!);

    // 4) POST الـ SDP إلى رابط WHIP، استقبل الإجابة
    final local = await _pc!.getLocalDescription();
    final res = await http.post(
      Uri.parse(whipUrl),
      headers: {'Content-Type': 'application/sdp'},
      body: local!.sdp,
    );
    if (res.statusCode != 201 && res.statusCode != 200) {
      throw Exception('WHIP فشل (${res.statusCode})');
    }
    _resourceUrl = res.headers['location'];
    await _pc!.setRemoteDescription(RTCSessionDescription(res.body, 'answer'));
  }

  /// تبديل الكاميرا الأمامية/الخلفية أثناء البثّ.
  Future<void> switchCamera() async {
    final track = _local?.getVideoTracks().firstOrNull;
    if (track != null) {
      await Helper.switchCamera(track);
      _frontCamera = !_frontCamera;
    }
  }

  /// كتم/إلغاء كتم الميكروفون.
  void setMuted(bool muted) {
    for (final t in _local?.getAudioTracks() ?? const <MediaStreamTrack>[]) {
      t.enabled = !muted;
    }
  }

  Future<void> stop() async {
    try {
      if (_resourceUrl != null && _resourceUrl!.startsWith('http')) {
        await http.delete(Uri.parse(_resourceUrl!)).timeout(
            const Duration(seconds: 4), onTimeout: () => http.Response('', 200));
      }
    } catch (_) {}
    await _dispose();
  }

  Future<void> _dispose() async {
    try {
      for (final t in _local?.getTracks() ?? const <MediaStreamTrack>[]) {
        await t.stop();
      }
      await _local?.dispose();
      await _pc?.close();
    } catch (_) {}
    _local = null;
    _pc = null;
    renderer.srcObject = null;
    await renderer.dispose();
  }
}

/// مشاهد WHEP — يستقبل الفيديو الحيّ من رابط المشاهدة ويعرضه.
class WhepViewer {
  RTCPeerConnection? _pc;
  String? _resourceUrl;
  final RTCVideoRenderer renderer = RTCVideoRenderer();
  final void Function()? onTrack; // يُستدعى عند وصول أول فيديو

  WhepViewer({this.onTrack});

  Future<void> start(String whepUrl) async {
    await renderer.initialize();
    _pc = await createPeerConnection(_kIce);

    // مستقبِل فقط (فيديو + صوت)
    await _pc!.addTransceiver(
        kind: RTCRtpMediaType.RTCRtpMediaTypeVideo,
        init: RTCRtpTransceiverInit(direction: TransceiverDirection.RecvOnly));
    await _pc!.addTransceiver(
        kind: RTCRtpMediaType.RTCRtpMediaTypeAudio,
        init: RTCRtpTransceiverInit(direction: TransceiverDirection.RecvOnly));

    _pc!.onTrack = (RTCTrackEvent e) {
      if (e.streams.isNotEmpty) {
        renderer.srcObject = e.streams.first;
        onTrack?.call();
      }
    };

    final offer = await _pc!.createOffer();
    await _pc!.setLocalDescription(offer);
    await _waitIce(_pc!);

    final local = await _pc!.getLocalDescription();
    final res = await http.post(
      Uri.parse(whepUrl),
      headers: {'Content-Type': 'application/sdp'},
      body: local!.sdp,
    );
    if (res.statusCode != 201 && res.statusCode != 200) {
      throw Exception('WHEP فشل (${res.statusCode})');
    }
    _resourceUrl = res.headers['location'];
    await _pc!.setRemoteDescription(RTCSessionDescription(res.body, 'answer'));
  }

  Future<void> stop() async {
    try {
      if (_resourceUrl != null && _resourceUrl!.startsWith('http')) {
        await http.delete(Uri.parse(_resourceUrl!)).timeout(
            const Duration(seconds: 4), onTimeout: () => http.Response('', 200));
      }
    } catch (_) {}
    try {
      await _pc?.close();
    } catch (_) {}
    _pc = null;
    renderer.srcObject = null;
    await renderer.dispose();
  }
}

/// ينتظر تجميع مرشّحات ICE (حتى الاكتمال أو مهلة قصيرة) قبل إرسال العرض —
/// يجعل الاتصال أسرع وأكثر موثوقية مع خوادم WHIP/WHEP.
Future<void> _waitIce(RTCPeerConnection pc) async {
  final done = Completer<void>();
  Timer? t;
  void finish() {
    if (!done.isCompleted) {
      t?.cancel();
      done.complete();
    }
  }

  pc.onIceGatheringState = (state) {
    if (state == RTCIceGatheringState.RTCIceGatheringStateComplete) finish();
  };
  t = Timer(const Duration(seconds: 3), finish); // لا ننتظر أكثر من 3 ثوانٍ
  await done.future;
}

extension _FirstOrNull<E> on List<E> {
  E? get firstOrNull => isEmpty ? null : first;
}
