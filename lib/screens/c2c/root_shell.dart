import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../main_shell.dart';
import '../waste_ops_shell.dart';
import '../management/management_home.dart';
import '../pms/pms_shell.dart';
import 'c2c_shell.dart';
import 'mode_switch.dart';
import '../update_gate.dart';
import 'staff/staff_shell.dart';

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
        // waste_role rides at the top level of whoami — keep it with the
        // interfaces so the shell knows which waste workspace to open.
        auth.interfaces!['waste_role'] = w['waste_role'];
        auth.defaultMode = w['default'] as String?;
      } catch (_) {
        auth.interfaces = {'c2c': true};
      }
    }
    await auth.loadAppMode();
    if (mounted) UpdateGate.check(context);
  }

  @override
  Widget build(BuildContext context) {
    // نراقب فقط ما يؤثّر في التوجيه (الوضع/الواجهات) — لا نُعيد بناء شجرة الواجهة
    // كاملةً كل 45ث عند تحديث الملف الشخصي الدوري (كان يسبب وميض ظهور/اختفاء
    // السجلات وإعادة تحميلها). التوجيه لا يتغيّر عند تحديث الإشعارات فقط.
    context.select<AuthProvider, String>((a) =>
        '${a.appMode}|${a.defaultMode}|${a.interfaces == null ? '' : (a.interfaces!.keys.toList()..sort()).join(',')}');
    final auth = context.read<AuthProvider>();
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
        // explicit request to pick a mode (the switch button) → show the chooser
        if (auth.appMode == 'choose') return ModeChooserScreen(modes: modes);
        // decide the active mode: an explicit user choice wins; otherwise a
        // client/projects user auto-enters their PRIMARY interface (whoami
        // 'default') so a waste-only client lands on their portal — not the
        // storefront. Storefront-first users (default 'c2c') still get the
        // chooser so they can opt into management. Switchable from account.
        var mode = auth.appMode;
        if (mode == null) {
          final def = auth.defaultMode;
          if (def != null && def != 'c2c' && modes.any((m) => m.key == def)) {
            mode = def;
          } else {
            return ModeChooserScreen(modes: modes);
          }
        }
        // route to chosen mode
        switch (mode) {
          case 'c2c_staff':
            return const StaffShell();
          case 'waste_ops':
            return WasteOpsShell(role: '${auth.interfaces?['waste_role'] ?? 'driver'}');
          case 'cafm':
            return const _ModeScaffold(child: MainShell());
          case 'pms':
            return const PmsShell();
          case 'management':
            return const ManagementShell();
          default:
            return C2CShell(canSwitchCafm: cafmSwitch, showModeSwitch: true);
        }
      },
    );
  }
}

/// Wraps a non-C2C native shell (CAFM). Switching systems lives in the account /
/// More page (the mode rail), not a floating button over the content.
class _ModeScaffold extends StatelessWidget {
  const _ModeScaffold({required this.child});
  final Widget child;
  @override
  Widget build(BuildContext context) => child;
}
