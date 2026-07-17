import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

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
    return Scaffold(
      body: Stack(
        children: [
          // 1) brand gradient ground
          const _Backdrop(),
          // 2) content
          SafeArea(
            child: SingleChildScrollView(
              padding: const EdgeInsets.fromLTRB(24, 48, 24, 24),
              child: Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    _hero(),
                    const SizedBox(height: 26),
                    _card(context),
                    const SizedBox(height: 20),
                    const Text('نظام إدارة المرافق المتكامل',
                        style: TextStyle(color: Colors.white54, fontSize: 12)),
                    const SizedBox(height: 4),
                    const Text('build ${String.fromEnvironment('BUILD_NUMBER', defaultValue: 'dev')}',
                        style: TextStyle(color: Colors.white38, fontSize: 11)),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  /// The brand opening. The wordmark carries a red keystone and the promise is
  /// split into the two halves of the business — services and management —
  /// rather than one grey line of text under a logo.
  Widget _hero() => Column(mainAxisSize: MainAxisSize.min, children: [
        _logo(),
        const SizedBox(height: 20),
        Row(mainAxisAlignment: MainAxisAlignment.center, crossAxisAlignment: CrossAxisAlignment.center, children: [
          const Text('CARE',
              style: TextStyle(color: Colors.white, fontSize: 40, fontWeight: FontWeight.w900, letterSpacing: 5)),
          const SizedBox(width: 7),
          // the keystone: the one spot of brand red on the screen
          Container(
            margin: const EdgeInsets.only(bottom: 5),
            width: 9, height: 9,
            decoration: BoxDecoration(
              color: const Color(0xFFC0392B),
              shape: BoxShape.circle,
              boxShadow: [BoxShadow(color: const Color(0xFFC0392B).withValues(alpha: 0.7), blurRadius: 10)],
            ),
          ),
        ]),
        const SizedBox(height: 12),
        // the promise, as the two halves of what CARE actually does
        Row(mainAxisAlignment: MainAxisAlignment.center, children: [
          _promise(Icons.home_repair_service_rounded, tr('خدمات', 'Services')),
          Container(
            width: 4, height: 4,
            margin: const EdgeInsets.symmetric(horizontal: 9),
            decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.35), shape: BoxShape.circle),
          ),
          _promise(Icons.dashboard_customize_rounded, tr('إدارة', 'Management')),
        ]),
        const SizedBox(height: 10),
        Text(tr('منصّتك المتكاملة', 'Your all-in-one platform'),
            textAlign: TextAlign.center,
            style: TextStyle(
                color: Colors.white.withValues(alpha: 0.55),
                fontSize: 12, letterSpacing: 1.5, fontWeight: FontWeight.w600)),
      ]);

  Widget _promise(IconData ic, String label) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 13, vertical: 6),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: Colors.white.withValues(alpha: 0.18)),
        ),
        child: Row(mainAxisSize: MainAxisSize.min, children: [
          Icon(ic, size: 13, color: Colors.white.withValues(alpha: 0.85)),
          const SizedBox(width: 6),
          Text(label,
              style: const TextStyle(color: Colors.white, fontSize: 12, fontWeight: FontWeight.w800)),
        ]),
      );

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
    return Container(
      constraints: const BoxConstraints(maxWidth: 420),
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(22),
        boxShadow: const [BoxShadow(color: Colors.black26, blurRadius: 30, offset: Offset(0, 12))],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(tr('تسجيل الدخول', 'Sign in'), style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w800)),
          const SizedBox(height: 18),
          TextField(
            controller: _login,
            textInputAction: TextInputAction.next,
            decoration: InputDecoration(
              labelText: tr('اسم المستخدم', 'Username'),
              prefixIcon: const Icon(Icons.person_outline),
              border: const OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 14),
          TextField(
            controller: _pass,
            obscureText: _obscure,
            onSubmitted: (_) => _submit(),
            decoration: InputDecoration(
              labelText: tr('كلمة المرور', 'Password'),
              prefixIcon: const Icon(Icons.lock_outline),
              suffixIcon: IconButton(
                icon: Icon(_obscure ? Icons.visibility : Icons.visibility_off),
                onPressed: () => setState(() => _obscure = !_obscure),
              ),
              border: const OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 22),
          FilledButton(
            onPressed: _busy ? null : _submit,
            child: _busy
                ? const SizedBox(height: 22, width: 22, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                : Text(tr('دخول', 'Log in')),
          ),
          const SizedBox(height: 14),
          Row(children: [
            const Expanded(child: Divider()),
            Padding(padding: const EdgeInsets.symmetric(horizontal: 10), child: Text(tr('جديد على كير؟', 'New to CARE?'), style: const TextStyle(color: Colors.grey, fontSize: 12))),
            const Expanded(child: Divider()),
          ]),
          const SizedBox(height: 12),
          OutlinedButton.icon(
            onPressed: _busy ? null : () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SignupScreen())),
            icon: const Icon(Icons.person_add_alt_1_rounded, color: Color(0xFF16A34A)),
            label: Text(tr('إنشاء عضوية جديدة', 'Create a new account'), style: const TextStyle(color: Color(0xFF16A34A), fontWeight: FontWeight.w800)),
            style: OutlinedButton.styleFrom(minimumSize: const Size.fromHeight(48), side: const BorderSide(color: Color(0xFF16A34A))),
          ),
        ],
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
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFF0E3A5F), Color(0xFF124E7C), Color(0xFF0B6EA8)],
        ),
      ),
      child: Stack(
        children: [
          _blob(-60, -40, 200, const Color(0x3338BDF8)),
          _blob(260, 120, 160, const Color(0x2637C98A)),
          _blob(-40, 520, 220, const Color(0x22F7A23B)),
          Positioned.fill(child: CustomPaint(painter: _GridPainter())),
        ],
      ),
    );
  }

  Widget _blob(double left, double top, double size, Color color) => Positioned(
        left: left, top: top,
        child: Container(
          width: size, height: size,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: RadialGradient(colors: [color, color.withValues(alpha: 0)]),
          ),
        ),
      );
}

class _GridPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = const Color(0x0DFFFFFF)
      ..strokeWidth = 1;
    const step = 32.0;
    for (double x = 0; x < size.width; x += step) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }
    for (double y = 0; y < size.height; y += step) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
