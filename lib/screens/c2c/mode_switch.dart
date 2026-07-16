import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'c2c_shell.dart';

/// One selectable interface/mode.
class AppMode {
  const AppMode(this.key, this.icon, this.ar, this.en, this.desc, this.colors);
  final String key;
  final IconData icon;
  final String ar, en, desc;
  final List<Color> colors;
}

const _allModes = [
  AppMode('c2c', Icons.storefront_rounded, 'CARE 2 CARE', 'CARE 2 CARE', 'الخدمات المنزلية والمتجر', [Color(0xFF17547F), C2C.navy]),
  AppMode('c2c_staff', Icons.badge_rounded, 'فريق العمل', 'Crew workspace', 'مهامك الميدانية وفريقك', [Color(0xFF0D9488), Color(0xFF115E59)]),
  AppMode('waste_ops', Icons.recycling_rounded, 'عمليات النفايات', 'Waste operations', 'طلبات النقل وإسناد السائقين والاستلام', [Color(0xFF16A34A), Color(0xFF14532D)]),
  AppMode('cafm', Icons.apartment_rounded, 'إدارة المرافق', 'Facilities (CAFM)', 'المرافق والمباني وأوامر العمل', [Color(0xFF0891B2), Color(0xFF0E7490)]),
  AppMode('pms', Icons.account_tree_rounded, 'إدارة المشاريع', 'Projects (PMS)', 'المشاريع والمهام', [Color(0xFF7C3AED), Color(0xFF5B21B6)]),
  AppMode('management', Icons.dashboard_customize_rounded, 'الإدارة', 'Management', 'كل أنظمة الشركة (أودو)', [Color(0xFFC0392B), Color(0xFF8E2A20)]),
];

List<AppMode> availableModes(Map<String, dynamic>? itf) {
  final i = itf ?? {};
  return _allModes.where((m) {
    switch (m.key) {
      case 'c2c':
        return true;
      case 'c2c_staff':
        return i['c2c_staff'] == true;
      case 'waste_ops':
        return i['waste_ops'] == true;
      case 'cafm':
        return i['cafm'] == true;
      case 'pms':
        return i['pms'] == true;
      case 'management':
        return i['staff'] == true || i['admin'] == true;
    }
    return false;
  }).toList();
}

/// Shown after login when the user has more than one interface — a full switch
/// they can only change again from their account page.
class ModeChooserScreen extends StatelessWidget {
  const ModeChooserScreen({super.key, required this.modes});
  final List<AppMode> modes;

  @override
  Widget build(BuildContext context) {
    final name = context.read<AuthProvider>().profile?.name ?? '';
    return Scaffold(
      backgroundColor: C2C.bg,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const SizedBox(height: 12),
            Text('${tr('أهلًا', 'Welcome')}${name.isNotEmpty ? '، ${name.split(' ').first}' : ''} 👋', style: const TextStyle(fontSize: 24, fontWeight: FontWeight.w900, color: C2C.navy)),
            const SizedBox(height: 6),
            Text(tr('لديك صلاحية على أكثر من نظام. اختر الوضع الذي تريد الدخول إليه:', 'You have access to more than one system. Choose your mode:'), style: const TextStyle(color: Colors.grey, fontSize: 14, height: 1.5)),
            const SizedBox(height: 20),
            Expanded(child: ListView.separated(
              itemCount: modes.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (_, i) => _card(context, modes[i]),
            )),
            Center(child: Text(tr('يمكنك تبديل الوضع لاحقًا من صفحة حسابك', 'You can switch mode later from your account'), style: TextStyle(color: Colors.grey.shade500, fontSize: 12))),
          ]),
        ),
      ),
    );
  }

  Widget _card(BuildContext context, AppMode m) => GestureDetector(
        onTap: () => context.read<AuthProvider>().setAppMode(m.key),
        child: Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            gradient: LinearGradient(colors: m.colors, begin: Alignment.topRight, end: Alignment.bottomLeft),
            borderRadius: BorderRadius.circular(18),
            boxShadow: [BoxShadow(color: m.colors[0].withValues(alpha: 0.35), blurRadius: 10, offset: const Offset(0, 4))],
          ),
          child: Row(children: [
            Container(width: 54, height: 54, decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.2), borderRadius: BorderRadius.circular(15)), child: Icon(m.icon, color: Colors.white, size: 28)),
            const SizedBox(width: 14),
            Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Text(gLang == 'en' ? m.en : m.ar, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w900, fontSize: 18)),
              const SizedBox(height: 2),
              Text(m.desc, style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 12.5)),
            ])),
            const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 18),
          ]),
        ),
      );
}

/// Management mode — a launcher of every Odoo app the user is permitted to use,
/// each opening the real backend (SSO) exactly as on the web.
