import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import '../main_shell.dart';
import '../login_screen.dart';
import 'c2c_home.dart';
import 'c2c_bookings.dart';
import 'c2c_account.dart';
import 'c2c_shop.dart';

/// Brand palette for CARE 2 CARE.
class C2C {
  static const navy = Color(0xFF0E3A5F);
  static const navy2 = Color(0xFF17547F);
  static const red = Color(0xFFC0392B);
  static const bg = Color(0xFFF4F7FB);
}

/// The CARE 2 CARE customer storefront shell (Home · Bookings · Account).
/// Shown as the app's default face; CAFM clients get a switch into the CAFM app.
class C2CShell extends StatefulWidget {
  const C2CShell({super.key, this.canSwitchCafm = false, this.guest = false});
  final bool canSwitchCafm;
  final bool guest;
  @override
  State<C2CShell> createState() => _C2CShellState();
}

class _C2CShellState extends State<C2CShell> {
  int _idx = 0;

  @override
  Widget build(BuildContext context) {
    final pages = [
      C2CHomeScreen(canSwitchCafm: widget.canSwitchCafm, guest: widget.guest),
      const C2CShopScreen(),
      widget.guest ? const _GuestGate() : const C2CBookingsScreen(),
      widget.guest ? const _GuestGate() : C2CAccountScreen(canSwitchCafm: widget.canSwitchCafm),
    ];
    return Scaffold(
      backgroundColor: C2C.bg,
      body: pages[_idx],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _idx,
        onDestinationSelected: (i) => setState(() => _idx = i),
        indicatorColor: C2C.navy.withValues(alpha: 0.12),
        destinations: [
          NavigationDestination(icon: const Icon(Icons.home_outlined), selectedIcon: const Icon(Icons.home_rounded, color: C2C.navy), label: tr('الرئيسية', 'Home')),
          NavigationDestination(icon: const Icon(Icons.storefront_outlined), selectedIcon: const Icon(Icons.storefront_rounded, color: C2C.navy), label: tr('المتجر', 'Shop')),
          NavigationDestination(icon: const Icon(Icons.event_note_outlined), selectedIcon: const Icon(Icons.event_note_rounded, color: C2C.navy), label: tr('حجوزاتي', 'Bookings')),
          NavigationDestination(icon: const Icon(Icons.person_outline_rounded), selectedIcon: const Icon(Icons.person_rounded, color: C2C.navy), label: tr('حسابي', 'Account')),
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
