import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/api_client.dart';
import 'core/auth.dart';
import 'core/theme.dart';
import 'core/i18n.dart';
import 'screens/login_screen.dart';
import 'screens/main_shell.dart';

void main() {
  final api = ApiClient();
  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => AuthProvider(api)..bootstrap()),
        ChangeNotifierProvider(create: (_) => LangProvider()..load()),
      ],
      child: const CareApp(),
    ),
  );
}

class CareApp extends StatelessWidget {
  const CareApp({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    context.watch<LangProvider>(); // rebuild on language change
    final theme = ServiceTheme.of(auth.profile?.role ?? 'worker');
    return MaterialApp(
      title: 'CARE FM',
      debugShowCheckedModeBanner: false,
      locale: Locale(gLang),
      theme: buildTheme(theme),
      builder: (ctx, child) => Directionality(
        textDirection: gLang == 'ar' ? TextDirection.rtl : TextDirection.ltr,
        child: child!,
      ),
      home: auth.loading
          ? const _Splash()
          : (auth.isLoggedIn ? const MainShell() : const LoginScreen()),
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
