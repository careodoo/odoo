import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import '../../core/widgets.dart';
import '../../core/app_version.dart';
import '../main_shell.dart';
import '../login_screen.dart';
import 'c2c_home.dart';
import 'c2c_services_tab.dart';
import 'c2c_bookings.dart';
import 'c2c_account.dart';
import 'c2c_shop.dart';

/// Brand palette for CARE 2 CARE.
class C2C {
  // Brand: red in its shades, with navy as the complementary deep tone.
  static const red = Color(0xFFC0392B);       // primary
  static const redDeep = Color(0xFF8E241B);   // pressed / gradients
  static const redBright = Color(0xFFE24A3B); // highlights
  static const redSoft = Color(0xFFFDECEA);   // tinted surfaces
  static const navy = Color(0xFF0E3A5F);       // complementary deep (text, secondary)
  static const navy2 = Color(0xFF17547F);
  static const deep = Color(0xFF08243B);
  static const amber = Color(0xFFF5A623);      // warm accent that pairs with red
  static const bg = Color(0xFFF6F7FB);
  static const ink = Color(0xFF1E293B);
  static const slate = Color(0xFF64748B);

  // ---- shared visual language for categories & services ----
  // A coordinated set of gradients that all sit next to the brand red.
  static const catGrads = <List<Color>>[
    [Color(0xFFE24A3B), Color(0xFFC0392B)],
    [Color(0xFFF39C4B), Color(0xFFE67E22)],
    [Color(0xFF20BFA9), Color(0xFF16A085)],
    [Color(0xFF4A90D9), Color(0xFF2980B9)],
    [Color(0xFFB06AB3), Color(0xFF8E44AD)],
    [Color(0xFFFF7B54), Color(0xFFE24A3B)],
    [Color(0xFF52C77E), Color(0xFF27AE60)],
    [Color(0xFFEC5F8E), Color(0xFFC2185B)],
  ];

  static List<Color> gradFor(int i) => catGrads[i % catGrads.length];

  /// A clean Material icon per category/service, chosen by keyword — used as a
  /// faint watermark so cards read as designed, not as pasted emoji.
  static IconData iconFor(String name) {
    bool has(List<String> ks) => ks.any(name.contains);
    if (has(['تكييف', 'تبريد'])) return Icons.ac_unit_rounded;
    if (has(['سباك'])) return Icons.plumbing_rounded;
    if (has(['كهرب'])) return Icons.electrical_services_rounded;
    if (has(['تنظيف', 'منازل'])) return Icons.cleaning_services_rounded;
    if (has(['سجاد', 'كنب'])) return Icons.weekend_rounded;
    if (has(['مغسلة', 'غسيل ملابس'])) return Icons.local_laundry_service_rounded;
    if (has(['حديقة', 'حدائق', 'تنسيق'])) return Icons.grass_rounded;
    if (has(['مسبح', 'سباحة', 'حمامات'])) return Icons.pool_rounded;
    if (has(['نقل', 'عفش', 'تغليف'])) return Icons.local_shipping_rounded;
    if (has(['معدّات', 'معدات', 'سيارات', 'تأجير'])) return Icons.agriculture_rounded;
    if (has(['حشرات', 'مكافحة'])) return Icons.pest_control_rounded;
    if (has(['صيانة', 'ترميم'])) return Icons.handyman_rounded;
    if (has(['دهان', 'صبغ'])) return Icons.format_paint_rounded;
    if (has(['نجار'])) return Icons.carpenter_rounded;
    if (has(['أمن', 'حراسة'])) return Icons.shield_rounded;
    return Icons.home_repair_service_rounded;
  }
}

/// The CARE 2 CARE customer storefront shell (Home · Bookings · Account).
/// Shown as the app's default face; CAFM clients get a switch into the CAFM app.
class C2CShell extends StatefulWidget {
  const C2CShell({super.key, this.canSwitchCafm = false, this.guest = false, this.showModeSwitch = false});
  final bool canSwitchCafm;
  final bool guest;
  final bool showModeSwitch;
  @override
  State<C2CShell> createState() => _C2CShellState();
}

class _C2CShellState extends State<C2CShell> {
  int _idx = 0;

  @override
  Widget build(BuildContext context) {
    final pages = [
      C2CHomeScreen(canSwitchCafm: widget.canSwitchCafm, guest: widget.guest),
      const C2CServicesTab(),
      const C2CShopScreen(),
      widget.guest ? const _GuestGate() : const C2CBookingsScreen(),
      widget.guest ? const _GuestAccountScreen() : C2CAccountScreen(canSwitchCafm: widget.canSwitchCafm, showModeSwitch: widget.showModeSwitch),
    ];
    return Scaffold(
      backgroundColor: C2C.bg,
      body: pages[_idx],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _idx,
        onDestinationSelected: (i) => setState(() => _idx = i),
        indicatorColor: C2C.red.withValues(alpha: 0.14),
        destinations: [
          NavigationDestination(icon: const Icon(Icons.home_outlined), selectedIcon: const Icon(Icons.home_rounded, color: C2C.red), label: tr('الرئيسية', 'Home')),
          NavigationDestination(icon: const Icon(Icons.grid_view_outlined), selectedIcon: const Icon(Icons.grid_view_rounded, color: C2C.red), label: tr('الخدمات', 'Services')),
          NavigationDestination(icon: const Icon(Icons.storefront_outlined), selectedIcon: const Icon(Icons.storefront_rounded, color: C2C.red), label: tr('المتجر', 'Shop')),
          NavigationDestination(icon: const Icon(Icons.event_note_outlined), selectedIcon: const Icon(Icons.event_note_rounded, color: C2C.red), label: tr('حجوزاتي', 'Bookings')),
          NavigationDestination(icon: const Icon(Icons.person_outline_rounded), selectedIcon: const Icon(Icons.person_rounded, color: C2C.red), label: tr('حسابي', 'Account')),
        ],
      ),
    );
  }
}

/// Switch from the C2C storefront into the CAFM facilities app.
void openCafm(BuildContext context) {
  Navigator.of(context, rootNavigator: true).push(
    MaterialPageRoute(builder: (_) => const _CafmWrapper()),
  );
}

class _CafmWrapper extends StatelessWidget {
  const _CafmWrapper();
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: C2C.navy,
        foregroundColor: Colors.white,
        title: Text(tr('إدارة المرافق CAFM', 'CAFM')),
        leading: IconButton(icon: const Icon(Icons.arrow_back), onPressed: () => Navigator.pop(context)),
      ),
      body: const MainShell(),
    );
  }
}

/// A small helper: does the logged-in user have the CAFM interface?
Future<bool> hasCafm(BuildContext context) async {
  try {
    final w = await context.read<AuthProvider>().api.whoami();
    return (w['interfaces']?['cafm'] ?? false) == true;
  } catch (_) {
    return false;
  }
}

/// Open the login screen on demand (from guest mode). Returns true if the user
/// signed in (the widget tree rebuilds into the signed-in shell).
Future<void> promptLogin(BuildContext context) =>
    Navigator.of(context, rootNavigator: true).push(MaterialPageRoute(builder: (_) => const LoginScreen()));

/// Shown on the Bookings/Account tabs while browsing as a guest.
class _GuestGate extends StatelessWidget {
  const _GuestGate();
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: C2C.bg,
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(mainAxisSize: MainAxisSize.min, children: [
            Container(
              width: 96, height: 96,
              decoration: BoxDecoration(color: C2C.navy.withValues(alpha: 0.08), borderRadius: BorderRadius.circular(28)),
              child: const Icon(Icons.lock_person_rounded, size: 48, color: C2C.navy),
            ),
            const SizedBox(height: 18),
            Text(tr('سجّل الدخول للمتابعة', 'Sign in to continue'), style: const TextStyle(fontSize: 19, fontWeight: FontWeight.w900, color: C2C.navy)),
            const SizedBox(height: 8),
            Text(tr('لعرض حجوزاتك وحسابك، سجّل الدخول أو أنشئ حسابًا.', 'Sign in to view your bookings and account.'),
                textAlign: TextAlign.center, style: const TextStyle(color: Colors.grey, fontSize: 14, height: 1.5)),
            const SizedBox(height: 22),
            SizedBox(
              width: double.infinity, height: 52,
              child: ElevatedButton.icon(
                style: ElevatedButton.styleFrom(backgroundColor: C2C.red, foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
                onPressed: () => promptLogin(context),
                icon: const Icon(Icons.login_rounded),
                label: Text(tr('تسجيل الدخول', 'Sign in'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 16)),
              ),
            ),
          ]),
        ),
      ),
    );
  }
}

/// The Account tab for guests: everything that does NOT require a login —
/// language, theme, privacy/terms, about, contact — plus a prominent sign-in CTA.
class _GuestAccountScreen extends StatelessWidget {
  const _GuestAccountScreen();

  Future<void> _url(BuildContext c, String u) async {
    if (!await launchUrl(Uri.parse(u), mode: LaunchMode.externalApplication) && c.mounted) {
      ScaffoldMessenger.of(c).showSnackBar(SnackBar(content: Text(tr('تعذّر فتح الرابط', 'Could not open link'))));
    }
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    Widget tile(IconData i, String t, VoidCallback onTap, {Color c = C2C.navy}) => Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
          child: Material(
            color: Colors.white, borderRadius: BorderRadius.circular(14),
            child: ListTile(
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
              leading: Container(width: 38, height: 38,
                  decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)),
                  child: Icon(i, color: c, size: 20)),
              title: Text(t, style: const TextStyle(fontWeight: FontWeight.w700)),
              trailing: const Icon(Icons.chevron_left_rounded, color: Colors.grey),
              onTap: onTap,
            ),
          ),
        );
    return Scaffold(
      backgroundColor: C2C.bg,
      body: ListView(padding: EdgeInsets.zero, children: [
        // header
        Container(
          height: 168,
          decoration: const BoxDecoration(
            gradient: LinearGradient(colors: [C2C.redBright, C2C.red, C2C.redDeep], begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.vertical(bottom: Radius.circular(28)),
          ),
          child: SafeArea(bottom: false, child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
            const CircleAvatar(radius: 32, backgroundColor: Colors.white,
                child: Icon(Icons.person_outline_rounded, color: C2C.navy, size: 34)),
            const SizedBox(height: 8),
            Text(tr('زائر', 'Guest'), style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
            Text(tr('سجّل الدخول لحفظ حجوزاتك وطلباتك', 'Sign in to save your bookings & orders'),
                style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 12)),
          ])),
        ),
        // sign-in CTA
        Padding(
          padding: const EdgeInsets.fromLTRB(14, 14, 14, 6),
          child: SizedBox(height: 50, child: ElevatedButton.icon(
            style: ElevatedButton.styleFrom(backgroundColor: C2C.red, foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
            onPressed: () => promptLogin(context),
            icon: const Icon(Icons.login_rounded),
            label: Text(tr('تسجيل الدخول / إنشاء حساب', 'Sign in / Create account'), style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 15)),
          )),
        ),
        const Padding(padding: EdgeInsets.fromLTRB(18, 10, 18, 4), child: Align(alignment: Alignment.centerRight,
            child: Text('التفضيلات', style: TextStyle(fontWeight: FontWeight.w900, color: C2C.navy, fontSize: 15)))),
        tile(Icons.language_rounded, tr('اللغة', 'Language'), () => showLanguagePicker(context), c: const Color(0xFF16A34A)),
        const Padding(padding: EdgeInsets.fromLTRB(18, 12, 18, 4), child: Align(alignment: Alignment.centerRight,
            child: Text('عن التطبيق', style: TextStyle(fontWeight: FontWeight.w900, color: C2C.navy, fontSize: 15)))),
        tile(Icons.support_agent_rounded, tr('تواصل معنا', 'Contact us'), () => _url(context, 'https://care-kw.com'), c: const Color(0xFF0891B2)),
        tile(Icons.privacy_tip_outlined, tr('سياسة الخصوصية', 'Privacy policy'), () => _url(context, 'https://ecare.care-kw.com/care_hr/static/legal/privacy.html'), c: const Color(0xFF16A34A)),
        tile(Icons.article_outlined, tr('شروط الاستخدام', 'Terms of use'), () => _url(context, 'https://ecare.care-kw.com/care_hr/static/legal/terms.html'), c: const Color(0xFF64748B)),
        tile(Icons.info_outline_rounded, tr('عن التطبيق', 'About'), () => showAboutDialog(context: context,
            applicationName: 'CARE 2 CARE', applicationVersion: 'v${AppVersion.value}', applicationLegalese: '© CARE — care-kw.com'), c: C2C.navy),
        const SizedBox(height: 24),
        Center(child: Text('CARE 2 CARE', style: TextStyle(color: Colors.grey.shade400, fontWeight: FontWeight.w900, letterSpacing: 1))),
        Center(child: Text('v${AppVersion.value}', style: TextStyle(color: Colors.grey.shade400, fontSize: 11))),
        const SizedBox(height: 24),
      ]),
    );
  }
}
