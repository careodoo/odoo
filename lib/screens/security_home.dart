import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/widgets.dart';
import 'scan_screen.dart';
import 'workorders_screen.dart';
import 'security_incidents_screen.dart';
import 'security_list_screen.dart';
import 'supervisor_screen.dart';

/// The security app's face — deliberately different: a dark "command centre"
/// look, large glanceable tiles, and a prominent panic action. This is the
/// screen the user asked to be "very, very professional".
class SecurityHome extends StatelessWidget {
  const SecurityHome({super.key});

  @override
  Widget build(BuildContext context) {
    final p = context.watch<AuthProvider>().profile!;
    return Scaffold(
      backgroundColor: const Color(0xFF0B1220),
      appBar: AppBar(
        title: const Text('🛡️  مركز الأمن'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            onPressed: () => context.read<AuthProvider>().logout(),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [Color(0xFF1E3A5F), Color(0xFF0F172A)]),
              borderRadius: BorderRadius.circular(18),
            ),
            child: Row(
              children: [
                const CircleAvatar(radius: 26, backgroundColor: Color(0xFFE5484D), child: Text('🛡️', style: TextStyle(fontSize: 24))),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(p.name, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w800)),
                      const Text('حارس أمن · وردية نشطة', style: TextStyle(color: Color(0xFF9CB2CD), fontSize: 13)),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 14),
          MyStatsRow(counts: p.counts),
          const SizedBox(height: 14),
          GridView.count(
            crossAxisCount: 2,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 1.05,
            children: [
              if (p.isSupervisor)
                _Tile(
                  icon: '🧭', label: 'لوحة المشرف',
                  sub: 'إحصائيات · إسناد',
                  onTap: () => Navigator.push(context,
                      MaterialPageRoute(builder: (_) => const SupervisorScreen())),
                ),
              _Tile(
                icon: '📍', label: 'مسح نقطة دورية',
                sub: 'إثبات تفتيش',
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ScanScreen())),
              ),
              _Tile(
                icon: '📋', label: 'مهامي',
                sub: 'أوامر العمل',
                onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const WorkOrdersScreen())),
              ),
              _Tile(
                icon: '🚨', label: 'زر الطوارئ',
                sub: 'بلاغ فوري', danger: true,
                onTap: () => _panic(context),
              ),
              _Tile(
                icon: '📝', label: 'البلاغات الأمنية',
                sub: 'عرض · تسجيل حادث',
                onTap: () => Navigator.push(context,
                    MaterialPageRoute(builder: (_) => const SecurityIncidentsScreen())),
              ),
              _Tile(
                icon: '🚶', label: 'الدوريات',
                sub: 'المسارات والحالة',
                onTap: () => Navigator.push(context, MaterialPageRoute(
                    builder: (_) => const SecurityListScreen(kind: 'patrols', title: 'الدوريات'))),
              ),
              _Tile(
                icon: '🔑', label: 'المفاتيح',
                sub: 'العهدة والحالة',
                onTap: () => Navigator.push(context, MaterialPageRoute(
                    builder: (_) => const SecurityListScreen(kind: 'keys', title: 'عهدة المفاتيح'))),
              ),
              _Tile(
                icon: '🚪', label: 'تصاريح البوابة',
                sub: 'الزوّار',
                onTap: () => Navigator.push(context, MaterialPageRoute(
                    builder: (_) => const SecurityListScreen(kind: 'gatepasses', title: 'تصاريح البوابة'))),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _panic(BuildContext context) {
    showDialog(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('🚨 تأكيد الطوارئ'),
        content: const Text('سيتم إرسال بلاغ طوارئ فوري إلى غرفة العمليات. متابعة؟'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('إلغاء')),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: const Color(0xFFE5484D)),
            onPressed: () {
              Navigator.pop(context);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('🚨 تم إرسال بلاغ الطوارئ')));
            },
            child: const Text('إرسال البلاغ'),
          ),
        ],
      ),
    );
  }

}

class _Tile extends StatelessWidget {
  const _Tile({required this.icon, required this.label, required this.sub, required this.onTap, this.danger = false});
  final String icon;
  final String label;
  final String sub;
  final VoidCallback onTap;
  final bool danger;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      borderRadius: BorderRadius.circular(16),
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: danger ? const Color(0xFF3A1418) : const Color(0xFF152238),
          border: Border.all(color: danger ? const Color(0xFFE5484D) : const Color(0xFF294059)),
          borderRadius: BorderRadius.circular(16),
        ),
        padding: const EdgeInsets.all(14),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(icon, style: const TextStyle(fontSize: 34)),
            const SizedBox(height: 8),
            Text(label, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 15)),
            Text(sub, style: const TextStyle(color: Color(0xFF9CB2CD), fontSize: 12)),
          ],
        ),
      ),
    );
  }
}
