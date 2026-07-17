import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/auth.dart';
import '../../core/i18n.dart';
import 'c2c_shell.dart';

/// Manage my account — name, email, phone and password in one place.
/// The server only ever writes the caller's own user.
class C2CProfileEditScreen extends StatefulWidget {
  const C2CProfileEditScreen({super.key});
  @override
  State<C2CProfileEditScreen> createState() => _C2CProfileEditScreenState();
}

class _C2CProfileEditScreenState extends State<C2CProfileEditScreen> {
  late final TextEditingController _name;
  late final TextEditingController _email;
  late final TextEditingController _phone;
  bool _busy = false;
  bool _dirty = false;

  @override
  void initState() {
    super.initState();
    final p = context.read<AuthProvider>().profile;
    _name = TextEditingController(text: p?.name ?? '');
    _email = TextEditingController(text: '');
    _phone = TextEditingController(text: '');
    _load();
    for (final c in [_name, _email, _phone]) {
      c.addListener(() { if (!_dirty && mounted) setState(() => _dirty = true); });
    }
  }

  Future<void> _load() async {
    try {
      final d = await context.read<AuthProvider>().api.c2cAccount();
      if (!mounted) return;
      setState(() {
        if ((d['name'] ?? '').toString().isNotEmpty) _name.text = '${d['name']}';
        _email.text = '${d['email'] ?? ''}';
        _phone.text = '${d['phone'] ?? ''}';
        _dirty = false;
      });
    } catch (_) {}
  }

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _phone.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: C2C.bg,
      appBar: AppBar(
        backgroundColor: C2C.navy, foregroundColor: Colors.white, elevation: 0,
        flexibleSpace: const DecoratedBox(decoration: BoxDecoration(gradient: LinearGradient(
            colors: [Color(0xFF17547F), C2C.navy], begin: Alignment.topRight, end: Alignment.bottomLeft))),
        title: Text(tr('إدارة الحساب', 'Manage account')),
      ),
      body: ListView(padding: const EdgeInsets.fromLTRB(14, 14, 14, 30), children: [
        _card(tr('بياناتي', 'My details'), Icons.person_rounded, C2C.navy, [
          _f(_name, tr('الاسم', 'Full name'), Icons.badge_outlined),
          const SizedBox(height: 10),
          _f(_email, tr('البريد الإلكتروني', 'Email'), Icons.mail_outline_rounded,
              type: TextInputType.emailAddress),
          Padding(
            padding: const EdgeInsets.only(top: 4, right: 4),
            child: Text(tr('البريد هو اسم الدخول — تغييره يغيّر طريقة تسجيل دخولك',
                           'Your email is your login — changing it changes how you sign in'),
                style: const TextStyle(fontSize: 10.5, color: Colors.grey)),
          ),
          const SizedBox(height: 10),
          _f(_phone, tr('رقم الهاتف', 'Phone'), Icons.phone_outlined, type: TextInputType.phone),
          const SizedBox(height: 14),
          SizedBox(width: double.infinity, height: 48, child: ElevatedButton.icon(
            style: ElevatedButton.styleFrom(
              backgroundColor: _dirty ? C2C.red : Colors.grey.shade300,
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(13))),
            onPressed: (_busy || !_dirty) ? null : _save,
            icon: _busy
                ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : const Icon(Icons.check_rounded),
            label: Text(tr('حفظ التغييرات', 'Save changes'), style: const TextStyle(fontWeight: FontWeight.w800)),
          )),
        ]),
        const SizedBox(height: 12),
        _card(tr('الأمان', 'Security'), Icons.lock_rounded, const Color(0xFF0891B2), [
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: Container(padding: const EdgeInsets.all(9),
                decoration: BoxDecoration(color: const Color(0xFF0891B2).withValues(alpha: 0.1), borderRadius: BorderRadius.circular(11)),
                child: const Icon(Icons.password_rounded, color: Color(0xFF0891B2), size: 20)),
            title: Text(tr('تغيير كلمة المرور', 'Change password'),
                style: const TextStyle(fontWeight: FontWeight.w800, fontSize: 14)),
            subtitle: Text(tr('يتطلب كلمة المرور الحالية', 'Requires your current password'),
                style: const TextStyle(fontSize: 11.5)),
            trailing: const Icon(Icons.chevron_left_rounded),
            onTap: _changePassword,
          ),
        ]),
      ]),
    );
  }

  Widget _card(String title, IconData ic, Color c, List<Widget> children) => Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.black12)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(children: [
            Icon(ic, color: c, size: 18),
            const SizedBox(width: 7),
            Text(title, style: TextStyle(fontWeight: FontWeight.w900, color: c, fontSize: 14.5)),
          ]),
          const SizedBox(height: 12),
          ...children,
        ]),
      );

  Widget _f(TextEditingController c, String label, IconData ic, {TextInputType? type}) => TextField(
        controller: c,
        keyboardType: type,
        decoration: InputDecoration(
          labelText: label,
          prefixIcon: Icon(ic, size: 20),
          filled: true, fillColor: C2C.bg, isDense: true,
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
        ),
      );

  Future<void> _save() async {
    setState(() => _busy = true);
    try {
      final d = await context.read<AuthProvider>().api.accountUpdate({
        'name': _name.text.trim(),
        'email': _email.text.trim(),
        'phone': _phone.text.trim(),
      });
      if (!mounted) return;
      // keep the header/profile in step with what was just saved
      await context.read<AuthProvider>().refreshProfile();
      if (!mounted) return;
      setState(() => _dirty = false);
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('✅ حُفظت بياناتك', '✅ Saved')), backgroundColor: const Color(0xFF16A34A)));
      Navigator.pop(context, d);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: C2C.red));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _changePassword() async {
    final oldPw = TextEditingController();
    final newPw = TextEditingController();
    final confirm = TextEditingController();
    final ok = await showDialog<bool>(context: context, builder: (ctx) => AlertDialog(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
      title: Text(tr('تغيير كلمة المرور', 'Change password'),
          style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)),
      content: Column(mainAxisSize: MainAxisSize.min, children: [
        TextField(controller: oldPw, obscureText: true,
            decoration: InputDecoration(labelText: tr('كلمة المرور الحالية', 'Current password'))),
        const SizedBox(height: 8),
        TextField(controller: newPw, obscureText: true,
            decoration: InputDecoration(labelText: tr('الجديدة (6 أحرف فأكثر)', 'New (6+ chars)'))),
        const SizedBox(height: 8),
        TextField(controller: confirm, obscureText: true,
            decoration: InputDecoration(labelText: tr('تأكيد الجديدة', 'Confirm new'))),
      ]),
      actions: [
        TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text(tr('إلغاء', 'Cancel'))),
        ElevatedButton(
          style: ElevatedButton.styleFrom(backgroundColor: C2C.navy, foregroundColor: Colors.white),
          onPressed: () => Navigator.pop(ctx, true), child: Text(tr('تغيير', 'Change'))),
      ],
    ));
    if (ok != true || !mounted) return;
    if (newPw.text.length < 6) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('كلمة المرور قصيرة', 'Password too short')), backgroundColor: C2C.red));
      return;
    }
    if (newPw.text != confirm.text) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(tr('التأكيد لا يطابق', 'Confirmation does not match')), backgroundColor: C2C.red));
      return;
    }
    try {
      await context.read<AuthProvider>().api.accountChangePassword(oldPw.text, newPw.text);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
            content: Text(tr('✅ تم تغيير كلمة المرور', '✅ Password changed')),
            backgroundColor: const Color(0xFF16A34A)));
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('$e'), backgroundColor: C2C.red));
      }
    }
  }
}
