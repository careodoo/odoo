import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import 'notifications_screen.dart';

/// Professional account page for CAFM/waste clients — a gradient identity
/// header with account type + stats, plus change-password and account actions.
class ClientAccountScreen extends StatefulWidget {
  const ClientAccountScreen({super.key});
  @override
  State<ClientAccountScreen> createState() => _ClientAccountScreenState();
}

class _ClientAccountScreenState extends State<ClientAccountScreen> {
  static const _navy = Color(0xFF0E3A5F);
  static const _green = Color(0xFF16A34A);
  Future<Map<String, dynamic>>? _info;

  @override
  void initState() {
    super.initState();
    _info = context.read<AuthProvider>().api.accountInfo();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF1F6F5),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _info,
        builder: (_, snap) {
          final d = snap.data ?? {};
          final name = '${d['name'] ?? context.read<AuthProvider>().profile?.name ?? ''}';
          return ListView(padding: EdgeInsets.zero, children: [
            // ===== professional header =====
            Container(
              padding: const EdgeInsets.fromLTRB(20, 0, 20, 24),
              decoration: const BoxDecoration(gradient: LinearGradient(colors: [Color(0xFF1A6187), _navy, Color(0xFF08243B)], begin: Alignment.topRight, end: Alignment.bottomLeft), borderRadius: BorderRadius.vertical(bottom: Radius.circular(28))),
              child: SafeArea(bottom: false, child: Column(children: [
                const SizedBox(height: 12),
                CircleAvatar(radius: 40, backgroundColor: Colors.white, child: Text(name.isNotEmpty ? name.trim().characters.first : '?', style: const TextStyle(color: _navy, fontSize: 34, fontWeight: FontWeight.w900))),
                const SizedBox(height: 10),
                Text(name, style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900)),
                const SizedBox(height: 6),
                Row(mainAxisAlignment: MainAxisAlignment.center, children: [
                  Container(padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5), decoration: BoxDecoration(color: const Color(0xFFF5A623), borderRadius: BorderRadius.circular(20)), child: Text('${d['account_type'] ?? '—'}', style: const TextStyle(color: _navy, fontWeight: FontWeight.w900, fontSize: 12.5))),
                  if (d['company'] != null) ...[
                    const SizedBox(width: 8),
                    Flexible(child: Text('🏢 ${d['company']}', style: TextStyle(color: Colors.white.withValues(alpha: 0.9), fontSize: 12.5), overflow: TextOverflow.ellipsis)),
                  ],
                ]),
              ])),
            ),
            // ===== stat cards =====
            Padding(padding: const EdgeInsets.fromLTRB(14, 14, 14, 6), child: Row(children: [
              _stat('${d['projects'] ?? 0}', tr('المشاريع', 'Projects'), Icons.folder_rounded, _navy),
              const SizedBox(width: 10),
              _stat('${d['unread'] ?? 0}', tr('إشعارات', 'Alerts'), Icons.notifications_rounded, const Color(0xFFF59E0B)),
              const SizedBox(width: 10),
              _stat(d['email'] != null ? '✓' : '—', tr('موثّق', 'Verified'), Icons.verified_rounded, _green),
            ])),
            _sectionTitle(tr('معلومات الحساب', 'Account info')),
            _infoTile(Icons.person_outline, tr('الاسم', 'Name'), d['name']),
            _infoTile(Icons.badge_outlined, tr('اسم الدخول', 'Login'), d['login']),
            _infoTile(Icons.email_outlined, tr('البريد', 'Email'), d['email']),
            _infoTile(Icons.phone_outlined, tr('الهاتف', 'Phone'), d['phone']),
            _sectionTitle(tr('الحساب والأمان', 'Account & security')),
            _actionTile(Icons.lock_reset_rounded, tr('تغيير كلمة المرور', 'Change password'), _changePassword, const Color(0xFF0891B2)),
            _actionTile(Icons.notifications_rounded, tr('الإشعارات', 'Notifications'), () => Navigator.push(context, MaterialPageRoute(builder: (_) => const NotificationsScreen())), const Color(0xFF6366F1)),
            _actionTile(Icons.language_rounded, context.watch<LangProvider>().isArabic ? 'English' : 'العربية', () => context.read<LangProvider>().toggle(), _green),
            _actionTile(Icons.swap_horiz_rounded, tr('العودة إلى CARE 2 CARE / تبديل الوضع', 'Back to CARE 2 CARE / switch'), () => context.read<AuthProvider>().setAppMode('choose'), const Color(0xFFF5A623)),
            _sectionTitle(tr('قانوني', 'Legal')),
            _actionTile(Icons.privacy_tip_outlined, tr('سياسة الخصوصية', 'Privacy policy'), () => _url('https://ecare.care-kw.com/care_hr/static/legal/privacy.html'), const Color(0xFF64748B)),
            _actionTile(Icons.article_outlined, tr('شروط الاستخدام', 'Terms of use'), () => _url('https://ecare.care-kw.com/care_hr/static/legal/terms.html'), const Color(0xFF64748B)),
            const SizedBox(height: 10),
            _actionTile(Icons.logout_rounded, tr('تسجيل الخروج', 'Sign out'), () => context.read<AuthProvider>().logout(), const Color(0xFFC0392B)),
            _actionTile(Icons.delete_forever_outlined, tr('طلب حذف الحساب', 'Delete account'), _deleteAccount, const Color(0xFFB91C1C)),
            const SizedBox(height: 24),
          ]);
        },
      ),
    );
  }

  Widget _stat(String v, String l, IconData ic, Color c) => Expanded(child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14), decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16), boxShadow: const [BoxShadow(color: Colors.black12, blurRadius: 6, offset: Offset(0, 2))]),
        child: Column(children: [Icon(ic, color: c, size: 22), const SizedBox(height: 5), Text(v, style: TextStyle(fontWeight: FontWeight.w900, fontSize: 18, color: c)), Text(l, style: const TextStyle(fontSize: 11, color: Colors.grey))]),
      ));

  Widget _sectionTitle(String t) => Padding(padding: const EdgeInsets.fromLTRB(18, 16, 18, 6), child: Align(alignment: Alignment.centerRight, child: Text(t, style: const TextStyle(fontWeight: FontWeight.w900, color: _navy, fontSize: 14.5))));

  Widget _infoTile(IconData ic, String k, dynamic v) => Container(
        margin: const EdgeInsets.symmetric(horizontal: 14, vertical: 3),
        child: ListTile(
          tileColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          leading: Icon(ic, color: Colors.grey), title: Text(k, style: const TextStyle(fontSize: 13, color: Colors.grey)),
          trailing: Text('${v ?? '—'}', style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5)),
        ),
      );

  Widget _actionTile(IconData ic, String t, VoidCallback onTap, Color c) => Container(
        margin: const EdgeInsets.symmetric(horizontal: 14, vertical: 3),
        child: ListTile(
          tileColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          leading: Container(padding: const EdgeInsets.all(8), decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(10)), child: Icon(ic, color: c, size: 20)),
          title: Text(t, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14)),
          trailing: const Icon(Icons.chevron_left, color: Colors.grey), onTap: onTap,
        ),
      );

  Future<void> _url(String u) async {
    if (!await launchUrl(Uri.parse(u), mode: LaunchMode.externalApplication) && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تعذّر فتح الرابط', 'Could not open link'))));
    }
  }

  Future<void> _changePassword() async {
    final auth = context.read<AuthProvider>();
    final oldC = TextEditingController(), newC = TextEditingController(), confC = TextEditingController();
    final ok = await showModalBottomSheet<bool>(
      context: context, isScrollControlled: true, backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(22))),
      builder: (ctx) => Padding(
        padding: EdgeInsets.fromLTRB(18, 18, 18, MediaQuery.of(ctx).viewInsets.bottom + 18),
        child: Column(mainAxisSize: MainAxisSize.min, crossAxisAlignment: CrossAxisAlignment.start, children: [
          const Text('تغيير كلمة المرور', style: TextStyle(fontWeight: FontWeight.w900, fontSize: 17, color: _navy)),
          const SizedBox(height: 14),
          _pwField(oldC, tr('كلمة المرور الحالية', 'Current password')),
          const SizedBox(height: 10),
          _pwField(newC, tr('كلمة المرور الجديدة', 'New password')),
          const SizedBox(height: 10),
          _pwField(confC, tr('تأكيد كلمة المرور', 'Confirm password')),
          const SizedBox(height: 16),
          SizedBox(width: double.infinity, height: 50, child: ElevatedButton(
            style: ElevatedButton.styleFrom(backgroundColor: _green, foregroundColor: Colors.white, shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14))),
            onPressed: () {
              if (newC.text.length < 6) { ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(content: Text(tr('كلمة المرور 6 أحرف على الأقل', 'Min 6 characters')))); return; }
              if (newC.text != confC.text) { ScaffoldMessenger.of(ctx).showSnackBar(SnackBar(content: Text(tr('كلمتا المرور غير متطابقتين', 'Passwords do not match')))); return; }
              Navigator.pop(ctx, true);
            },
            child: Text(tr('حفظ', 'Save'), style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 15)))),
        ]),
      ),
    );
    if (ok != true) return;
    try {
      await auth.api.accountChangePassword(oldC.text, newC.text);
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تم تغيير كلمة المرور', 'Password changed')), backgroundColor: _green));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'.replaceAll('Exception: ', '')), backgroundColor: const Color(0xFFC0392B)));
    }
  }

  Widget _pwField(TextEditingController c, String hint) => TextField(controller: c, obscureText: true, decoration: InputDecoration(hintText: hint, prefixIcon: const Icon(Icons.lock_outline), filled: true, fillColor: const Color(0xFFF1F5F9), border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none)));

  Future<void> _deleteAccount() async {
    final auth = context.read<AuthProvider>();
    final ok = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(
      title: Text(tr('طلب حذف الحساب', 'Delete account')),
      content: Text(tr('سيتم حذف حسابك وبياناتك خلال 30 يومًا. لا يمكن التراجع.', 'Your account and data will be deleted within 30 days. Cannot be undone.')),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('إلغاء', 'Cancel'))),
        ElevatedButton(style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFFB91C1C)), onPressed: () => Navigator.pop(ctx, true), child: Text(tr('تأكيد', 'Confirm'), style: const TextStyle(color: Colors.white))),
      ],
    ));
    if (ok != true) return;
    try { await auth.api.accountDeleteRequest(); if (mounted) { ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('تم استلام طلبك — سيتم تسجيل خروجك', 'Request received — signing out')))); auth.logout(); } } catch (_) {}
  }
}
