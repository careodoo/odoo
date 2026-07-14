import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../main_shell.dart';
import 'c2c_shell.dart';

/// Decides the app's landing face from /whoami:
///   • internal staff / admin  → the operational CAFM app (MainShell)
///   • everyone else (customers, incl. CAFM clients) → the CARE 2 CARE
///     storefront, with a switch into CAFM when they also own facilities.
class RootShell extends StatefulWidget {
  const RootShell({super.key});
  @override
  State<RootShell> createState() => _RootShellState();
}

class _RootShellState extends State<RootShell> {
  Future<Map<String, dynamic>>? _who;

  @override
  void initState() {
    super.initState();
    _who = context.read<AuthProvider>().api.whoami().catchError((_) => <String, dynamic>{});
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Map<String, dynamic>>(
      future: _who,
      builder: (_, snap) {
        if (!snap.hasData) {
          return const Scaffold(body: Center(child: CircularProgressIndicator()));
        }
        final itf = (snap.data!['interfaces'] as Map?) ?? {};
        final staff = itf['staff'] == true || itf['admin'] == true;
        // Internal staff run the operational app; customers get the storefront.
        if (staff) return const MainShell();
        return C2CShell(canSwitchCafm: itf['cafm'] == true);
      },
    );
  }
}
