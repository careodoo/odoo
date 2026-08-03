import 'dart:async';
import 'dart:io';
import 'dart:typed_data';
import 'package:flutter_webrtc/flutter_webrtc.dart';
import 'package:http/http.dart' as http;
import 'i18n.dart';
import 'package:path_provider/path_provider.dart';

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

  // تسجيل ذاتيّ على الجهاز (Cloudflare لا يسجّل بثّ WebRTC) → يُرفَع بعد التوقّف
  MediaRecorder? _recorder;
  String? recordedPath;
  bool get hasRecording => recordedPath != null && File(recordedPath!).existsSync();

  /// التقاط لقطة (JPEG) من الكاميرا لتكون الصورة المصغّرة للبثّ.
  Future<Uint8List?> captureFrame() async {
    try {
      final track = _local?.getVideoTracks().firstOrNull;
      if (track == null) return null;
      final buf = await track.captureFrame();
      return buf.asUint8List();
    } catch (_) {
      return null;
    }
  }

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
      throw Exception(tr('WHIP فشل (${res.statusCode})', 'WHIP failed (${res.statusCode})'));
    }
    _resourceUrl = res.headers['location'];
    await _pc!.setRemoteDescription(RTCSessionDescription(res.body, 'answer'));

    // 5) بدء التسجيل الذاتيّ على الجهاز (يُتجاهَل الفشل حتى لا يُعطّل البثّ)
    await _startRecording();
  }

  Future<void> _startRecording() async {
    try {
      final vt = _local?.getVideoTracks().firstOrNull;
      if (vt == null) return;
      final dir = await getTemporaryDirectory();
      final path = '${dir.path}/care_broadcast_${DateTime.now().millisecondsSinceEpoch}.mp4';
      final rec = MediaRecorder();
      await rec.start(path, videoTrack: vt, audioChannel: RecorderAudioChannel.INPUT);
      _recorder = rec;
      recordedPath = path;
    } catch (_) {
      _recorder = null;
      recordedPath = null;
    }
  }

  Future<void> _stopRecording() async {
    try {
      await _recorder?.stop();
    } catch (_) {} finally {
      _recorder = null;
    }
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
    // نوقف التسجيل أولاً (قبل إيقاف المسارات) حتى يُغلَق ملف mp4 سليماً
    await _stopRecording();
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
  MediaStream? _remote; // stream مُجمّع (صوت + فيديو) نضمن به عرض الفيديو
  String? _resourceUrl;
  final RTCVideoRenderer renderer = RTCVideoRenderer();
  final void Function()? onTrack; // يُستدعى عند وصول أول فيديو

  WhepViewer({this.onTrack});

  Future<void> start(String whepUrl) async {
    await renderer.initialize();
    _pc = await createPeerConnection(_kIce);

    // نجمع كل المسارات الواردة في stream واحد ونعرضه — لتفادي «صوت بلا صورة»
    // الناتج عن ضبط srcObject على مسار الصوت قبل وصول الفيديو.
    _remote = await createLocalMediaStream('whep_remote');
    renderer.srcObject = _remote;

    // مستقبِل فقط (فيديو + صوت)
    await _pc!.addTransceiver(
        kind: RTCRtpMediaType.RTCRtpMediaTypeVideo,
        init: RTCRtpTransceiverInit(direction: TransceiverDirection.RecvOnly));
    await _pc!.addTransceiver(
        kind: RTCRtpMediaType.RTCRtpMediaTypeAudio,
        init: RTCRtpTransceiverInit(direction: TransceiverDirection.RecvOnly));

    _pc!.onTrack = (RTCTrackEvent e) async {
      try {
        await _remote?.addTrack(e.track);
      } catch (_) {}
      // نُعيد ربط العرض عند وصول الفيديو (يجبر إعادة الرسم)
      if (e.track.kind == 'video') {
        renderer.srcObject = _remote;
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
      throw Exception(tr('WHEP فشل (${res.statusCode})', 'WHEP failed (${res.statusCode})'));
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
      await _remote?.dispose();
    } catch (_) {}
    _pc = null;
    _remote = null;
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
