import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'core/api_client.dart';
import 'core/auth.dart';
import 'core/theme.dart';
import 'core/i18n.dart';
import 'core/app_version.dart';
import 'core/push.dart';
import 'screens/c2c/root_shell.dart';
import 'screens/c2c/c2c_shell.dart';
import 'screens/language_onboarding.dart';

void main() async {
  // PackageInfo talks over a platform channel, so the binding must exist first
  WidgetsFlutterBinding.ensureInitialized();
  await AppVersion.load(); // real version, never a hardcoded string
  await Push.init();          // FCM: permission + device token

  // In release Flutter paints a bare grey box when a widget throws, which is
  // exactly what a user reports as "the page is grey and won't open" — with
  // nothing to act on. Show the failure instead: the screen stays usable, the
  // error is readable, and a bug takes one screenshot to diagnose rather than
  // several rounds of guessing.
  ErrorWidget.builder = (FlutterErrorDetails details) => Material(
        color: const Color(0xFFF4F6FA),
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(22),
            child: Column(mainAxisSize: MainAxisSize.min, children: [
              const Icon(Icons.error_outline_rounded,
                  size: 44, color: Color(0xFFE11D48)),
              const SizedBox(height: 12),
              const Text('تعذّر عرض هذه الشاشة',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
              const SizedBox(height: 4),
              const Text('Could not render this screen',
                  textAlign: TextAlign.center,
                  style: TextStyle(fontSize: 12, color: Color(0xFF64748B))),
              const SizedBox(height: 14),
              SelectableText('${details.exception}',
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 11.5, color: Color(0xFF64748B))),
            ]),
          ),
        ),
      );
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
