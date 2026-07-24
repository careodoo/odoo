import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/live_broadcast.dart';
import 'security_broadcast_screen.dart';

/// مؤشّر عائم يظهر فوق كل شاشات التطبيق طالما هناك بثّ نشط مُصغّر — يذكّر الحارس
/// أنه «على الهواء» (نبضة حمراء + مؤقّت)، يعيد فتح شاشة البثّ عند الضغط، ويتيح
/// الإيقاف السريع. يحقّق «البثّ بسرية»: الحارس يكمل عمله والبثّ مستمرّ.
class LiveBroadcastPill extends StatelessWidget {
  const LiveBroadcastPill({super.key});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<bool>(
      valueListenable: LiveBroadcast.instance.live,
      builder: (_, live, __) => live ? const _Pill() : const SizedBox.shrink(),
    );
  }
}

class _Pill extends StatefulWidget {
  const _Pill();
  @override
  State<_Pill> createState() => _PillState();
}

class _PillState extends State<_Pill> with SingleTickerProviderStateMixin {
  Timer? _t;
  late final AnimationController _pulse =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 850))..repeat(reverse: true);

  @override
  void initState() {
    super.initState();
    _t = Timer.periodic(const Duration(seconds: 1), (_) { if (mounted) setState(() {}); });
  }

  @override
  void dispose() {
    _t?.cancel();
    _pulse.dispose();
    super.dispose();
  }

  String get _clock {
    final s = LiveBroadcast.instance.elapsedSeconds;
    return '${(s ~/ 60).toString().padLeft(2, '0')}:${(s % 60).toString().padLeft(2, '0')}';
  }

  void _open() {
    final svc = LiveBroadcast.instance;
    Navigator.of(context).push(MaterialPageRoute(builder: (_) => SecurityBroadcastScreen(
        incidentId: svc.incidentId, providerId: -1, cohost: svc.cohost)));
  }

  Future<void> _stop() async {
    final svc = LiveBroadcast.instance;
    final iid = svc.incidentId, co = svc.cohost;
    final api = context.read<AuthProvider>().api;
    await svc.end();
    try {
      if (co) { await api.securityStreamCohostStop(iid); } else { await api.securityStreamStop(iid); }
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    final top = MediaQuery.of(context).padding.top + 6;
    return Positioned(
      top: top, left: 12, right: 12,
      child: Directionality(
        textDirection: gIsRtl ? TextDirection.rtl : TextDirection.ltr,
        child: Align(
          alignment: Alignment.topCenter,
          child: Material(
            color: Colors.transparent,
            child: InkWell(
              borderRadius: BorderRadius.circular(24),
              onTap: _open,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                decoration: BoxDecoration(
                  color: const Color(0xFFE5484D),
                  borderRadius: BorderRadius.circular(24),
                  boxShadow: [BoxShadow(color: const Color(0xFFE5484D).withValues(alpha: .5), blurRadius: 12, offset: const Offset(0, 3))],
                ),
                child: Row(mainAxisSize: MainAxisSize.min, children: [
                  FadeTransition(opacity: Tween(begin: .4, end: 1.0).animate(_pulse),
                      child: Container(width: 9, height: 9, decoration: const BoxDecoration(color: Colors.white, shape: BoxShape.circle))),
                  const SizedBox(width: 7),
                  Text(tr('أنت تبثّ الآن', 'You are live'), style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 12.5)),
                  const SizedBox(width: 7),
                  Text(_clock, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w700, fontSize: 12, fontFeatures: [FontFeature.tabularFigures()])),
                  const SizedBox(width: 10),
                  GestureDetector(
                    onTap: _stop,
                    child: Container(padding: const EdgeInsets.all(3),
                        decoration: BoxDecoration(color: Colors.white.withValues(alpha: .25), shape: BoxShape.circle),
                        child: const Icon(Icons.stop_rounded, color: Colors.white, size: 15)),
                  ),
                ]),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
