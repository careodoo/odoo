import 'dart:async';
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/live_broadcast.dart';
import 'stream_view_screen.dart';
import 'security_broadcast_screen.dart';

/// بانر البثوث الحيّة في رئيسية تطبيق حارس الأمن: يظهر تلقائياً عند وجود بثّ،
/// بأيقونة حمراء نابضة + اسم وصورة الباثّ + الموقع + عدّاد المشاهدين، مع
/// «مشاهدة» و«مشاركة». يستطلع الحالة دورياً ويختفي عند انتهاء كل البثوث.
class LiveStreamBanner extends StatefulWidget {
  /// isClient: بانر هيدر تطبيق العميل (بثوث مواقعه، مشاهدة فقط بلا «مشاركة»).
  final bool isClient;
  const LiveStreamBanner({super.key, this.isClient = false});
  @override
  State<LiveStreamBanner> createState() => _LiveStreamBannerState();
}

class _LiveStreamBannerState extends State<LiveStreamBanner> with WidgetsBindingObserver {
  static const _red = Color(0xFFE5484D);
  static const _green = Color(0xFF37C98A);
  List<Map> _items = const [];
  Timer? _poll;
  StreamSubscription? _fcmSub;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _tick();
    // استطلاع سريع (شبه فوري) — يظهر البثّ خلال ثوانٍ دون رفرش يدوي
    _poll = Timer.periodic(const Duration(seconds: 4), (_) => _tick());
    // ظهور فوري عند وصول إشعار البثّ (push)
    _fcmSub = FirebaseMessaging.onMessage.listen((_) => _tick());
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) _tick(); // تحديث عند فتح التطبيق
  }

  Future<void> _tick() async {
    try {
      final api = context.read<AuthProvider>().api;
      final items = widget.isClient ? await api.clientSecurityStreamActive() : await api.securityStreamActive();
      // لا نمسح البانر عند خطأ شبكة عابر — فقط عند استجابة ناجحة فارغة
      if (mounted) setState(() => _items = items.cast<Map>());
    } catch (_) {}
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _fcmSub?.cancel();
    _poll?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_items.isEmpty) return const SizedBox.shrink();
    return Column(children: [
      for (final s in _items) Padding(padding: const EdgeInsets.only(bottom: 10), child: _card(s)),
    ]);
  }

  Widget _card(Map s) {
    final photo = _decode('${s['guard_photo'] ?? ''}');
    final mine = s['is_mine'] == true;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [Color(0xFF3A0E12), Color(0xFF1A1013)], begin: Alignment.topRight, end: Alignment.bottomLeft),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: _red.withValues(alpha: .5)),
      ),
      child: Row(children: [
        // صورة الباثّ + نبض
        Stack(clipBehavior: Clip.none, children: [
          CircleAvatar(radius: 24, backgroundColor: const Color(0xFF152238),
              backgroundImage: photo,
              child: photo == null ? const Icon(Icons.person, color: Colors.white, size: 22) : null),
          Positioned(right: -2, bottom: -2, child: Container(
              padding: const EdgeInsets.all(2), decoration: const BoxDecoration(color: Color(0xFF1A1013), shape: BoxShape.circle),
              child: const _PulseDot())),
        ]),
        const SizedBox(width: 12),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Container(padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(color: _red, borderRadius: BorderRadius.circular(6)),
                child: Text(tr('مباشر', 'LIVE'), style: const TextStyle(color: Colors.white, fontSize: 9.5, fontWeight: FontWeight.w900))),
            const SizedBox(width: 6),
            Icon(Icons.visibility_rounded, color: Colors.white.withValues(alpha: .7), size: 12),
            const SizedBox(width: 3),
            Text('${s['viewer_count'] ?? 0}', style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700)),
            if ((s['cohosts'] ?? 0) as int > 0) ...[
              const SizedBox(width: 8), const Icon(Icons.groups_rounded, color: _green, size: 13), const SizedBox(width: 2),
              Text('${s['cohosts']}', style: const TextStyle(color: _green, fontSize: 11, fontWeight: FontWeight.w700)),
            ],
          ]),
          const SizedBox(height: 3),
          Text('${s['guard'] ?? tr('حارس', 'Guard')}', maxLines: 1, overflow: TextOverflow.ellipsis,
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 14)),
          if ((s['premise'] ?? '').toString().isNotEmpty)
            Text('${s['premise']}', maxLines: 1, overflow: TextOverflow.ellipsis, style: const TextStyle(color: Color(0xFFCBA6A8), fontSize: 11)),
        ])),
        const SizedBox(width: 8),
        // أزرار: الباثّ نفسه (عودة/إيقاف)، وإلا مشاهدة (+ مشاركة للفريق)
        Column(mainAxisSize: MainAxisSize.min, children: [
          if (mine && !widget.isClient) ...[
            _btn(Icons.videocam_rounded, tr('العودة للبثّ', 'Resume'), _red, () => _resume(s)),
            const SizedBox(height: 6),
            _btn(Icons.stop_rounded, tr('إيقاف', 'Stop'), const Color(0xFF64748B), () => _stopMine(s)),
          ] else ...[
            _btn(Icons.play_arrow_rounded, tr('مشاهدة', 'Watch'), _red,
                () => Navigator.push(context, MaterialPageRoute(builder: (_) =>
                    StreamViewScreen(incidentId: s['incident_id'] as int, isClient: widget.isClient)))),
            if (!widget.isClient) ...[
              const SizedBox(height: 6),
              _btn(Icons.video_call_rounded, tr('مشاركة', 'Join'), _green,
                  () => Navigator.push(context, MaterialPageRoute(builder: (_) =>
                      SecurityBroadcastScreen(incidentId: s['incident_id'] as int, providerId: -1, cohost: true)))),
            ],
          ],
        ]),
      ]),
    );
  }

  Widget _btn(IconData i, String label, Color c, VoidCallback onTap) => SizedBox(
        height: 30,
        child: FilledButton.icon(
          onPressed: onTap,
          style: FilledButton.styleFrom(backgroundColor: c, padding: const EdgeInsets.symmetric(horizontal: 10),
              minimumSize: const Size(0, 30), tapTargetSize: MaterialTapTargetSize.shrinkWrap),
          icon: Icon(i, size: 15), label: Text(label, style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w800)),
        ),
      );

  /// الباثّ يعود لشاشة بثّه الكاملة (تستأنف الجلسة الحيّة).
  void _resume(Map s) {
    Navigator.push(context, MaterialPageRoute(builder: (_) =>
        SecurityBroadcastScreen(incidentId: s['incident_id'] as int, providerId: -1)));
  }

  /// الباثّ يوقف بثّه من البانر مباشرة.
  Future<void> _stopMine(Map s) async {
    final iid = s['incident_id'] as int;
    final api = context.read<AuthProvider>().api;
    try { await LiveBroadcast.instance.end(); } catch (_) {}
    try { await api.securityStreamStop(iid); } catch (_) {}
    _tick();
  }

  MemoryImage? _decode(String b64) {
    if (b64.isEmpty) return null;
    try { return MemoryImage(base64Decode(b64)); } catch (_) { return null; }
  }
}

class _PulseDot extends StatefulWidget {
  const _PulseDot();
  @override
  State<_PulseDot> createState() => _PulseDotState();
}

class _PulseDotState extends State<_PulseDot> with SingleTickerProviderStateMixin {
  late final AnimationController _c = AnimationController(vsync: this, duration: const Duration(milliseconds: 850))..repeat(reverse: true);
  @override
  void dispose() { _c.dispose(); super.dispose(); }
  @override
  Widget build(BuildContext context) => ScaleTransition(scale: Tween(begin: .7, end: 1.15).animate(_c),
      child: Container(width: 11, height: 11, decoration: const BoxDecoration(color: Color(0xFFE5484D), shape: BoxShape.circle)));
}
