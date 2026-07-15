import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../main_shell.dart';
import '../odoo_backend_screen.dart';
import 'c2c_shell.dart';
import 'mode_switch.dart';

/// Routes the logged-in user to their chosen interface:
///   • one interface → straight in
///   • many interfaces, none chosen yet → the mode chooser (a full switch;
///     changeable again only from the account page)
///   • chosen mode → that interface (c2c / cafm / pms / management)
class RootShell extends StatefulWidget {
  const RootShell({super.key});
  @override
  State<RootShell> createState() => _RootShellState();
}

class _RootShellState extends State<RootShell> {
  Future<void>? _init;

  @override
  void initState() {
    super.initState();
    _init = _load();
  }

  Future<void> _load() async {
    final auth = context.read<AuthProvider>();
    if (auth.interfaces == null) {
      try {
        final w = await auth.api.whoami();
        auth.interfaces = (w['interfaces'] as Map?)?.cast<String, dynamic>() ?? {};
      } catch (_) {
        auth.interfaces = {'c2c': true};
      }
    }
    await auth.loadAppMode();
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    return FutureBuilder(
      future: _init,
      builder: (_, snap) {
        if (snap.connectionState != ConnectionState.done) {
          return const Scaffold(body: Center(child: CircularProgressIndicator()));
        }
        final modes = availableModes(auth.interfaces);
        final cafmSwitch = auth.interfaces?['cafm'] == true;
        // single interface → storefront
        if (modes.length <= 1) return C2CShell(canSwitchCafm: cafmSwitch);
        // not chosen yet → chooser
        if (auth.appMode == null) return ModeChooserScreen(modes: modes);
        // route to chosen mode
        switch (auth.appMode) {
          case 'cafm':
            return const _ModeScaffold(child: MainShell());
          case 'pms':
            return const OdooBackendScreen(path: '/my/pm', title: 'إدارة المشاريع', showSwitch: true);
          case 'management':
            return const ManagementLauncherScreen();
          default:
            return C2CShell(canSwitchCafm: cafmSwitch, showModeSwitch: true);
        }
      },
    );
  }
}

/// Wraps a non-C2C native shell (CAFM) with a floating "switch mode" affordance.
class _ModeScaffold extends StatelessWidget {
  const _ModeScaffold({required this.child});
  final Widget child;
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: child,
      floatingActionButton: FloatingActionButton.small(
        heroTag: 'modeSwitch',
        backgroundColor: const Color(0xFF7C3AED),
        tooltip: 'تبديل الوضع',
        onPressed: () => context.read<AuthProvider>().setAppMode(null),
        child: const Icon(Icons.swap_horiz_rounded),
      ),
    );
  }
}
