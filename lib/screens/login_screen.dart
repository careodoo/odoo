import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';
import '../core/widgets.dart';
import '../core/app_version.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _login = TextEditingController();
  final _pass = TextEditingController();
  bool _busy = false;
  bool _obscure = true;
  Map<String, dynamic>? _brand;

  @override
  void initState() {
    super.initState();
    _loadBrand();
  }

  Future<void> _loadBrand() async {
    try {
      final b = await context.read<AuthProvider>().api.branding();
      if (mounted) setState(() => _brand = b);
    } catch (_) {/* offline: fall back to the wordmark */}
  }

  @override
  void dispose() {
    _login.dispose();
    _pass.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (_login.text.isEmpty || _pass.text.isEmpty) return;
    setState(() => _busy = true);
    final ok = await context.read<AuthProvider>().login(_login.text.trim(), _pass.text);
    if (mounted) setState(() => _busy = false);
    if (ok && mounted && Navigator.canPop(context)) {
      // opened on-demand from guest mode → close and reveal the signed-in tree
      Navigator.pop(context);
    } else if (!ok && mounted) {
      final err = context.read<AuthProvider>().error ?? tr('فشل الدخول', 'Login failed');
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err)));
    }
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    return Scaffold(
      body: Stack(
        children: [
          // 1) brand gradient ground
          const _Backdrop(),
          // 2) content
          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(24, 12, 24, 24),
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // language switcher — top-right, understated
                    Align(
                      alignment: Alignment.centerLeft,
                      child: InkWell(
                        borderRadius: BorderRadius.circular(20),
                        onTap: () => showLanguagePicker(context),
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
                          decoration: BoxDecoration(
                            color: Colors.white.withValues(alpha: 0.12),
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(color: Colors.white.withValues(alpha: 0.2)),
                          ),
                          child: Row(mainAxisSize: MainAxisSize.min, children: [
                            const Icon(Icons.language_rounded, size: 15, color: Colors.white),
                            const SizedBox(width: 6),
                            Text(tr('العربية', 'English'),
                                style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w700)),
                          ]),
                        ),
                      ),
                    ),
                    const SizedBox(height: 28),
                    _hero(),
                    const SizedBox(height: 26),
                    _card(context),
                    const SizedBox(height: 20),
                    Text('v${AppVersion.value}',
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.35), fontSize: 11)),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// The brand opening. The logo already says CARE, so repeating it as a
  /// wordmark, then again as two chips and two taglines, was four introductions
  /// where one will do.
  Widget _hero() => Column(mainAxisSize: MainAxisSize.min, children: [
        _logo(),
        const SizedBox(height: 18),
        Text(tr('منصّة إدارة المرافق والخدمات', 'Facilities and services platform'),
            textAlign: TextAlign.center,
            style: TextStyle(
                color: Colors.white.withValues(alpha: 0.82),
                fontSize: 13.5, height: 1.4, fontWeight: FontWeight.w600, letterSpacing: 0.3)),
      ]);

  Widget _logo() {
    final logo = _brand?['logo'] as String?;
    if (logo != null && logo.startsWith('data:image')) {
      try {
        final bytes = base64Decode(logo.split(',').last);
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 22, vertical: 18),
          constraints: const BoxConstraints(maxWidth: 260),
          decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(20),
            boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 20, offset: Offset(0, 8))],
          ),
          child: Image.memory(bytes, height: 66, fit: BoxFit.contain),
        );
      } catch (_) {}
    }
    // fallback emblem
    return Container(
      height: 100, width: 100,
      alignment: Alignment.center,
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(28),
        boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 20, offset: Offset(0, 8))],
      ),
      child: const Text('🏢', style: TextStyle(fontSize: 50)),
    );
  }

  Widget _card(BuildContext context) {
    const ink = Color(0xFF14202B);
    const red = Color(0xFFC0392B);
    return Container(
      constraints: const BoxConstraints(maxWidth: 420),
      padding: const EdgeInsets.fromLTRB(22, 26, 22, 20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: const [BoxShadow(color: Color(0x40000000), blurRadius: 38, offset: Offset(0, 18))],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(tr('تسجيل الدخول', 'Sign in'),
              style: const TextStyle(fontSize: 21, fontWeight: FontWeight.w900, color: ink)),
          const SizedBox(height: 3),
          Text(tr('مرحباً بعودتك', 'Welcome back'),
              style: TextStyle(fontSize: 13, color: Colors.grey.shade500)),
          const SizedBox(height: 22),
          _field(_login, tr('اسم المستخدم', 'Username'), Icons.person_outline_rounded, next: true),
          const SizedBox(height: 13),
          _field(_pass, tr('كلمة المرور', 'Password'), Icons.lock_outline_rounded,
            obscure: _obscure, onSubmit: _submit,
            suffix: IconButton(
              icon: Icon(_obscure ? Icons.visibility_rounded : Icons.visibility_off_rounded,
                  color: Colors.grey.shade500, size: 20),
              onPressed: () => setState(() => _obscure = !_obscure),
            ),
          ),
          const SizedBox(height: 22),
          Material(
            color: Colors.transparent,
            child: Ink(
              decoration: BoxDecoration(
                gradient: const LinearGradient(colors: [Color(0xFFE24A3B), red]),
                borderRadius: BorderRadius.circular(15),
                boxShadow: [BoxShadow(color: red.withValues(alpha: 0.32),
                    blurRadius: 14, offset: const Offset(0, 7))],
              ),
              child: InkWell(
                borderRadius: BorderRadius.circular(15),
                onTap: _busy ? null : _submit,
                child: SizedBox(
                  height: 54,
                  child: Center(child: _busy
                      ? const SizedBox(height: 22, width: 22,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : Text(tr('دخول', 'Log in'),
                          style: const TextStyle(color: Colors.white, fontSize: 16,
                              fontWeight: FontWeight.w900, letterSpacing: 0.5))),
                ),
              ),
            ),
          ),
          const SizedBox(height: 16),
          // Creating an account is the rarer path, so it reads as a link rather
          // than a second button competing with the one people came to press —
          // and it is no longer green, which fought the brand.
          Center(
            child: TextButton(
              onPressed: _busy ? null : () => Navigator.push(context,
                  MaterialPageRoute(builder: (_) => const SignupScreen())),
              child: RichText(
                text: TextSpan(
                  style: TextStyle(fontSize: 13, color: Colors.grey.shade600),
                  children: [
                    TextSpan(text: '${tr('جديد على كير؟', 'New to CARE?')} '),
                    TextSpan(text: tr('أنشئ عضوية', 'Create an account'),
                        style: const TextStyle(color: red, fontWeight: FontWeight.w900)),
                  ],
                ),
              ),
            ),
          ),
          const SizedBox(height: 2),
          Row(mainAxisAlignment: MainAxisAlignment.center, children: [
            Icon(Icons.lock_rounded, size: 11, color: Colors.grey.shade400),
            const SizedBox(width: 5),
            Text(tr('اتصال آمن ومشفّر', 'Secure encrypted connection'),
                style: TextStyle(color: Colors.grey.shade400, fontSize: 10.5, fontWeight: FontWeight.w600)),
          ]),
        ],
      ),
    );
  }

  Widget _field(TextEditingController c, String label, IconData ic,
      {bool obscure = false, bool next = false, Widget? suffix, VoidCallback? onSubmit}) {
    const navy = Color(0xFF0E3A5F);
    return TextField(
      controller: c,
      obscureText: obscure,
      textInputAction: next ? TextInputAction.next : TextInputAction.done,
      onSubmitted: onSubmit == null ? null : (_) => onSubmit(),
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(ic, size: 21),
        suffixIcon: suffix,
        filled: true,
        fillColor: const Color(0xFFF4F6F8),
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: BorderSide(color: Colors.grey.shade200)),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(14), borderSide: const BorderSide(color: navy, width: 1.6)),
      ),
    );
  }
}

/// Public self-registration → a CARE 2 CARE customer account.
class SignupScreen extends StatefulWidget {
  const SignupScreen({super.key});
  @override
  State<SignupScreen> createState() => _SignupScreenState();
}

class _SignupScreenState extends State<SignupScreen> {
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _phone = TextEditingController();
  final _pass = TextEditingController();
  bool _busy = false, _obscure = true;

  Future<void> _submit() async {
    if (_name.text.trim().isEmpty || (_email.text.trim().isEmpty && _phone.text.trim().isEmpty) || _pass.text.length < 6) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(tr('أكمل البيانات (كلمة مرور ٦ أحرف على الأقل)', 'Complete the fields (min 6-char password)'))));
      return;
    }
    setState(() => _busy = true);
    final ok = await context.read<AuthProvider>().signup(name: _name.text.trim(), email: _email.text.trim(), phone: _phone.text.trim(), password: _pass.text);
    if (mounted) setState(() => _busy = false);
    if (ok && mounted) {
      Navigator.of(context)..pop()..maybePop();
    } else if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(context.read<AuthProvider>().error ?? tr('تعذّر إنشاء الحساب', 'Signup failed'))));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Stack(children: [
        const _Backdrop(),
        SafeArea(child: SingleChildScrollView(
          padding: const EdgeInsets.fromLTRB(24, 20, 24, 24),
          child: Column(children: [
            Align(alignment: Alignment.centerLeft, child: IconButton(icon: const Icon(Icons.arrow_back, color: Colors.white), onPressed: () => Navigator.pop(context))),
            const SizedBox(height: 8),
            const Text('CARE 2 CARE', style: TextStyle(color: Colors.white, fontSize: 26, fontWeight: FontWeight.w900, letterSpacing: 2)),
            const SizedBox(height: 4),
            Text(tr('أنشئ عضويتك واحجز خدماتك المنزلية', 'Create your account & book home services'), style: const TextStyle(color: Colors.white70, fontSize: 13)),
            const SizedBox(height: 24),
            Container(
              constraints: const BoxConstraints(maxWidth: 420),
              padding: const EdgeInsets.all(22),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(22), boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 30, offset: Offset(0, 12))]),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Text(tr('عضوية جديدة', 'New account'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
                const SizedBox(height: 16),
                _f(_name, tr('الاسم الكامل', 'Full name'), Icons.person_outline),
                const SizedBox(height: 12),
                _f(_email, tr('البريد الإلكتروني', 'Email'), Icons.email_outlined, keyboard: TextInputType.emailAddress),
                const SizedBox(height: 12),
                _f(_phone, tr('رقم الهاتف', 'Phone'), Icons.phone_outlined, keyboard: TextInputType.phone),
                const SizedBox(height: 12),
                TextField(controller: _pass, obscureText: _obscure, decoration: InputDecoration(
                  labelText: tr('كلمة المرور', 'Password'), prefixIcon: const Icon(Icons.lock_outline),
                  suffixIcon: IconButton(icon: Icon(_obscure ? Icons.visibility : Icons.visibility_off), onPressed: () => setState(() => _obscure = !_obscure)),
                  border: const OutlineInputBorder())),
                const SizedBox(height: 20),
                FilledButton(
                  style: FilledButton.styleFrom(backgroundColor: const Color(0xFF16A34A), minimumSize: const Size.fromHeight(50)),
                  onPressed: _busy ? null : _submit,
                  child: _busy ? const SizedBox(height: 22, width: 22, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white)) : Text(tr('إنشاء الحساب', 'Create account'), style: const TextStyle(fontWeight: FontWeight.w800))),
                const SizedBox(height: 10),
                Text(tr('بإنشائك الحساب فأنت توافق على الشروط وسياسة الخصوصية.', 'By signing up you agree to the Terms & Privacy Policy.'), textAlign: TextAlign.center, style: const TextStyle(color: Colors.grey, fontSize: 11)),
              ]),
            ),
          ]),
        )),
      ]),
    );
  }

  Widget _f(TextEditingController c, String label, IconData ic, {TextInputType? keyboard}) => TextField(
        controller: c, keyboardType: keyboard,
        decoration: InputDecoration(labelText: label, prefixIcon: Icon(ic), border: const OutlineInputBorder()),
      );
}

/// A layered gradient + soft floating shapes — brand-forward, no assets needed.
class _Backdrop extends StatelessWidget {
  const _Backdrop();
  @override
  Widget build(BuildContext context) {
    return Container(
      // CARE is a red brand. This screen was the one place it read as a blue
      // one, so the first impression contradicted every other surface.
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topRight,
          end: Alignment.bottomLeft,
          colors: [Color(0xFFE24A3B), Color(0xFFC0392B), Color(0xFF7A1B14)],
        ),
      ),
      child: Stack(children: const [
        // a single soft light source rather than three coloured blobs fighting
        Positioned(top: -120, right: -90, child: _Glow(size: 320, opacity: 0.16)),
        Positioned(bottom: -140, left: -110, child: _Glow(size: 300, opacity: 0.10)),
        Positioned.fill(child: CustomPaint(painter: BrandPattern(opacity: 0.055, gap: 30))),
      ]),
    );
  }
}


class _Glow extends StatelessWidget {
  const _Glow({required this.size, required this.opacity});
  final double size;
  final double opacity;
  @override
  Widget build(BuildContext context) => Container(
        width: size, height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          gradient: RadialGradient(colors: [
            Colors.white.withValues(alpha: opacity),
            Colors.white.withValues(alpha: 0),
          ]),
        ),
      );
}
