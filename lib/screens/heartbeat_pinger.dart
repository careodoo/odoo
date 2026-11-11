import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';

/// Guard status heartbeat sender: emits a periodic heartbeat to the server so their status is updated (active/idle).
/// An invisible widget placed on the security home. The precise physical values (heart rate,
/// movement, sleep) will come from the smartwatch version later — here we send the logical activity:
/// app in the foreground = active, long in the background = idle.
class HeartbeatPinger extends StatefulWidget {
  const HeartbeatPinger({super.key});
  @override
  State<HeartbeatPinger> createState() => _HeartbeatPingerState();
}

class _HeartbeatPingerState extends State<HeartbeatPinger> with WidgetsBindingObserver {
  Timer? _t;
  bool _foreground = true;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _ping();
    _t = Timer.periodic(const Duration(seconds: 60), (_) => _ping());
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    _foreground = state == AppLifecycleState.resumed;
    _ping(); // نبضة فورية عند تغيّر الحالة
  }

  Future<void> _ping() async {
    try {
      await context.read<AuthProvider>().api.securityGuardHeartbeat(moving: _foreground);
    } catch (_) {}
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _t?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => const SizedBox.shrink();
}
