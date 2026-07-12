import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/api_client.dart';
import 'core/auth.dart';
import 'core/theme.dart';
import 'screens/login_screen.dart';
import 'screens/home_screen.dart';

void main() {
  final api = ApiClient();
  runApp(
    ChangeNotifierProvider(
      create: (_) => AuthProvider(api)..bootstrap(),
      child: const CareApp(),
    ),
  );
}

class CareApp extends StatelessWidget {
  const CareApp({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    // Theme follows the logged-in user's primary service (security → command look).
    final theme = ServiceTheme.of(auth.profile?.role ?? 'worker');
    return MaterialApp(
      title: 'CARE FM',
      debugShowCheckedModeBanner: false,
      locale: appLocale,
      theme: buildTheme(theme),
      builder: (ctx, child) => Directionality(
        textDirection: TextDirection.rtl,
        child: child!,
      ),
      home: auth.loading
          ? const _Splash()
          : (auth.isLoggedIn ? const HomeScreen() : const LoginScreen()),
    );
  }
}

class _Splash extends StatelessWidget {
  const _Splash();
  @override
  Widget build(BuildContext context) => const Scaffold(
        body: Center(child: CircularProgressIndicator()),
      );
}
