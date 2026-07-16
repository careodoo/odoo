import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import '../notifications_screen.dart';
import 'c2c_shell.dart';
import 'c2c_contracts.dart';
import 'c2c_bookings.dart';
import 'c2c_orders.dart';
import 'c2c_addresses.dart';

class C2CAccountScreen extends StatefulWidget {
  const C2CAccountScreen({super.key, this.canSwitchCafm = false, this.showModeSwitch = false});
  final bool canSwitchCafm;
  final bool showModeSwitch;
  @override
  State<C2CAccountScreen> createState() => _C2CAccountScreenState();
}

class _C2CAccountScreenState extends State<C2CAccountScreen> {
  Future<Map<String, dynamic>>? _acc;

  @override
  void initState() {
    super.initState();
    _acc = context.read<AuthProvider>().api.c2cAccount();
  }

  @override
  Widget build(BuildContext context) {
    final name = context.read<AuthProvider>().profile?.name ?? '';
    return Scaffold(
      backgroundColor: C2C.bg,
      body: FutureBuilder<Map<String, dynamic>>(
        future: _acc,
        builder: (_, snap) {
          final d = snap.data ?? {};
          return ListView(padding: EdgeInsets.zero, children: [
            // ===== vibrant header =====
            SizedBox(
              height: 210,
              child: Stack(children: [
                Container(
                  height: 190,
                  decoration: const BoxDecoration(gradient: LinearGradient(colors: [Color(0xFF17547F), C2C.navy, Color(0xFF0A2A44)], begin: Alignment.topRight, end: Alignment.bottomLeft), borderRadius: BorderRadius.vertical(bottom: Radius.circular(30))),
                ),
                Positioned(top: -20, right: -20, child: _blob(120, Colors.white.withValues(alpha: 0.06))),
                Positioned(top: 60, left: -30, child: _blob(110, C2C.red.withValues(alpha: 0.10))),
                Positioned(top: 0, left: 0, right: 0, child: SafeArea(bottom: false, child: Padding(
                  padding: const EdgeInsets.only(top: 18),
                  child: Column(children: [
                    Container(
                      padding: const EdgeInsets.all(3),
                      decoration: BoxDecoration(shape: BoxShape.circle, border: Border.all(color: Colors.white.withValues(alpha: 0.4), width: 2)),
                      child: CircleAvatar(radius: 36, backgroundColor: Colors.white, child: Text(name.isNotEmpty ? name.trim().characters.first : '?', style: const TextStyle(color: C2C.navy, fontSize: 30, fontWeight: FontWeight.w900))),
                    ),
                    const SizedBox(height: 8),
                    Text(name, style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w900)),
                    if (d['phone'] != null) Text('${d['phone']}', style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 13)),
                  ]),
                ))),
              ]),
            ),
            // ===== gradient stat cards =====
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 4, 14, 8),
              child: Row(children: [
                _stat('${d['total_bookings'] ?? 0}', tr('الحجوزات', 'Bookings'), Icons.event_note_rounded, const [Color(0xFF17547F), C2C.navy]),
                const SizedBox(width: 10),
                _stat('${d['upcoming'] ?? 0}', tr('قادمة', 'Upcoming'), Icons.upcoming_rounded, const [Color(0xFFF59E0B), Color(0xFFB45309)]),
                const SizedBox(width: 10),
                _stat('${d['total_spent'] ?? 0}', tr('أنفقت', 'Spent'), Icons.payments_rounded, const [Color(0xFF16A34A), Color(0xFF15803D)]),
              ]),
            ),
            const Padding(padding: EdgeInsets.fromLTRB(18, 8, 18, 4), child: Align(alignment: Alignment.centerRight, child: Text('الحساب', style: TextStyle(fontWeight: FontWeight.w900, color: C2C.navy, fontSize: 15)))),
            _tile(Icons.notifications_rounded, tr('الإشعارات', 'Notifications'), () => Navigator.push(context, MaterialPageRoute(builder: (_) => const NotificationsScreen())), ic: const Color(0xFF6366F1)),
            _tile(Icons.event_note_rounded, tr('حجوزاتي', 'My bookings'), () => Navigator.push(context, MaterialPageRoute(builder: (_) => const C2CBookingsScreen())), ic: const Color(0xFF0EA5E9)),
            _tile(Icons.receipt_long_rounded, tr('طلباتي (المتجر)', 'My orders (shop)'), () => Navigator.push(context, MaterialPageRoute(builder: (_) => const C2COrdersScreen())), ic: const Color(0xFFF59E0B)),
            _tile(Icons.location_on_outlined, tr('عناوين التوصيل', 'Delivery addresses'), () => Navigator.push(context, MaterialPageRoute(builder: (_) => const C2CAddressesScreen())), ic: const Color(0xFF16A34A)),
            _tile(Icons.description_outlined, tr('طلبات التعاقد وعروض الأسعار', 'Contracts & quotes'), () => Navigator.push(context, MaterialPageRoute(builder: (_) => const C2CContractsScreen())), ic: const Color(0xFF8B5CF6)),
            if (widget.showModeSwitch)
              _tile(Icons.swap_horiz_rounded, tr('تبديل الوضع (الأنظمة الأخرى)', 'Switch mode (other systems)'), () => context.read<AuthProvider>().setAppMode('choose'), ic: const Color(0xFF7C3AED))
            else if (widget.canSwitchCafm)
              _tile(Icons.apartment_rounded, tr('التحويل إلى إدارة المرافق (CAFM)', 'Switch to CAFM'), () => openCafm(context), ic: C2C.navy),
            _tile(Icons.language_rounded, tr('اللغة', 'Language'), _langSheet, ic: const Color(0xFF16A34A)),
            _tile(Icons.privacy_tip_outlined, tr('سياسة الخصوصية', 'Privacy policy'), () => _openUrl('https://ecare.care-kw.com/care_hr/static/legal/privacy.html'), ic: const Color(0xFF0891B2)),
            _tile(Icons.article_outlined, tr('شروط الاستخدام', 'Terms of use'), () => _openUrl('https://ecare.care-kw.com/care_hr/static/legal/terms.html'), ic: const Color(0xFF64748B)),
            _tile(Icons.logout_rounded, tr('تسجيل الخروج', 'Sign out'), () => context.read<AuthProvider>().logout(), ic: C2C.red, danger: true),
            _tile(Icons.delete_forever_outlined, tr('طلب حذف الحساب', 'Delete account'), _deleteAccount, ic: const Color(0xFFB91C1C), danger: true),
            const SizedBox(height: 20),
            Center(child: Text('CARE 2 CARE', style: TextStyle(color: Colors.grey.shade400, fontWeight: FontWeight.w900, letterSpacing: 1))),
            const SizedBox(height: 30),
          ]);
        },
      ),
    );
  }

  Future<void> _openUrl(String url) async {
    final u = Uri.parse(url);
    if (!await launchUrl(u, mode: LaunchMode.externalApplication)) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تعذّر فتح الرابط', 'Could not open link'))));
    }
  }

  Future<void> _deleteAccount() async {
    final auth = context.read<AuthProvider>();
    final reason = TextEditingController();
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(tr('طلب حذف الحساب', 'Delete account')),
        content: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(tr('سيتم حذف حسابك وبياناتك نهائيًا خلال 30 يومًا. لا يمكن التراجع.',
              'Your account and data will be permanently deleted within 30 days. This cannot be undone.'),
              style: const TextStyle(fontSize: 13.5)),
          const SizedBox(height: 12),
          TextField(controller: reason, maxLines: 2, decoration: InputDecoration(
              hintText: tr('السبب (اختياري)', 'Reason (optional)'), border: const OutlineInputBorder())),
        ]),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('إلغاء', 'Cancel'))),
          ElevatedButton(style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFB91C1C)),
              onPressed: () => Navigator.pop(ctx, true),
              child: Text(tr('تأكيد الحذف', 'Confirm'), style: const TextStyle(color: Colors.white))),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await auth.api.accountDeleteRequest(reason: reason.text);
      if (!mounted) return;
      await showDialog(context: context, builder: (ctx) => AlertDialog(
        title: Text(tr('تم استلام طلبك', 'Request received')),
        content: Text(tr('سنحذف حسابك وبياناتك خلال 30 يومًا. سيتم تسجيل خروجك الآن.',
            'We will delete your account and data within 30 days. You will be signed out now.')),
        actions: [TextButton(onPressed: () => Navigator.pop(ctx), child: Text(tr('حسنًا', 'OK')))],
      ));
      auth.logout();
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e')));
    }
  }

  Widget _blob(double size, Color color) => Container(width: size, height: size, decoration: BoxDecoration(color: color, shape: BoxShape.circle));

  Widget _stat(String v, String l, IconData ic, List<Color> g) => Expanded(
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 8),
          decoration: BoxDecoration(
            gradient: LinearGradient(colors: g, begin: Alignment.topLeft, end: Alignment.bottomRight),
            borderRadius: BorderRadius.circular(16),
            boxShadow: [BoxShadow(color: g[0].withValues(alpha: 0.35), blurRadius: 8, offset: const Offset(0, 4))],
          ),
          child: Column(children: [
            Icon(ic, color: Colors.white, size: 22),
            const SizedBox(height: 6),
            Text(v, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 18, color: Colors.white)),
            Text(l, style: TextStyle(fontSize: 10.5, color: Colors.white.withValues(alpha: 0.9)), textAlign: TextAlign.center, maxLines: 1, overflow: TextOverflow.ellipsis),
          ]),
        ),
      );

  Widget _tile(IconData icon, String t, VoidCallback onTap, {Color ic = C2C.navy, bool danger = false}) => Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
        child: Material(
          color: Colors.white, borderRadius: BorderRadius.circular(14),
          child: ListTile(
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
            leading: Container(width: 38, height: 38, decoration: BoxDecoration(color: ic.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(11)), child: Icon(icon, color: ic, size: 20)),
            title: Text(t, style: TextStyle(fontWeight: FontWeight.w700, color: danger ? C2C.red : null)),
            trailing: const Icon(Icons.chevron_left_rounded, color: Colors.grey),
            onTap: onTap,
          ),
        ),
      );

  void _langSheet() => showModalBottomSheet(context: context, backgroundColor: Colors.white, shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))), builder: (_) => SafeArea(
        child: Column(mainAxisSize: MainAxisSize.min, children: [
          const SizedBox(height: 10),
          Container(width: 42, height: 4, decoration: BoxDecoration(color: Colors.black12, borderRadius: BorderRadius.circular(4))),
          Padding(padding: const EdgeInsets.all(14), child: Text(tr('اختر اللغة', 'Choose language'), style: const TextStyle(fontWeight: FontWeight.w900, color: C2C.navy, fontSize: 16))),
          for (final l in context.read<LangProvider>().languages)
            ListTile(title: Text(l[1], style: const TextStyle(fontWeight: FontWeight.w600)), trailing: gLang == l[0] ? const Icon(Icons.check_circle_rounded, color: C2C.navy) : null, onTap: () { context.read<LangProvider>().setLang(l[0]); Navigator.pop(context); setState(() {}); }),
          const SizedBox(height: 8),
        ]),
      ));
}
