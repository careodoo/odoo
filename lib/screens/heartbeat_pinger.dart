import 'dart:async';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';

/// مُرسِل نبضات حالة الحارس: يبعث نبضة دورية للخادم فتُحدَّث حالته (نشط/سكون).
/// عنصر غير مرئي يُوضع في رئيسية الأمن. القيم الفيزيائية الدقيقة (نبض القلب،
/// الحركة، النوم) ستأتي من نسخة الساعة الذكية لاحقاً — هنا نرسل الحركة المنطقية:
/// التطبيق في المقدّمة = نشاط، وفي الخلفية طويلاً = سكون.
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
