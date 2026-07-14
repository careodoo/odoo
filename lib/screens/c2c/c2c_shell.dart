import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import '../main_shell.dart';
import 'c2c_home.dart';
import 'c2c_bookings.dart';
import 'c2c_account.dart';

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
  const C2CShell({super.key, this.canSwitchCafm = false});
  final bool canSwitchCafm;
  @override
  State<C2CShell> createState() => _C2CShellState();
}

class _C2CShellState extends State<C2CShell> {
  int _idx = 0;

  @override
  Widget build(BuildContext context) {
    final pages = [
      C2CHomeScreen(canSwitchCafm: widget.canSwitchCafm),
      const C2CBookingsScreen(),
      C2CAccountScreen(canSwitchCafm: widget.canSwitchCafm),
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
