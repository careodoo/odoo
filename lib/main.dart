import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/api_client.dart';
import 'core/auth.dart';
import 'core/theme.dart';
import 'core/i18n.dart';
import 'core/app_version.dart';
import 'screens/c2c/root_shell.dart';
import 'screens/c2c/c2c_shell.dart';
import 'screens/language_onboarding.dart';

void main() async {
  // PackageInfo talks over a platform channel, so the binding must exist first
  WidgetsFlutterBinding.ensureInitialized();
  await AppVersion.load(); // real version, never a hardcoded string
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
    final lang = context.watch<LangProvider>(); // rebuild on language change
    final theme = ServiceTheme.of(auth.profile?.role ?? 'worker');
    return MaterialApp(
      title: 'CARE',
      debugShowCheckedModeBanner: false,
      locale: Locale(gLang),
      theme: buildTheme(theme),
      builder: (ctx, child) => Directionality(
        textDirection: gIsRtl ? TextDirection.rtl : TextDirection.ltr,
        child: child!,
      ),
      home: auth.loading
          ? const _Splash()
          : lang.firstRun
              // first launch → let the user pick a language before anything else
              ? const LanguageOnboardingScreen()
              // Public app: guests land on the CARE 2 CARE storefront; login is
              // only prompted on demand (booking / my account).
              : (auth.isLoggedIn ? const RootShell() : const C2CShell(guest: true)),
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
