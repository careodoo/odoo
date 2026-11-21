import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Second step of two-factor login for accounts secured with an authenticator
/// app (TOTP). Reached only when /auth/login answered with `need_totp` — the
/// account has app-based 2FA on and no session exists yet. There is no code to
/// e-mail or resend: the user reads a 6-digit code from Google Authenticator /
/// Microsoft Authenticator. On a correct code the server issues the real token
/// and [AuthProvider.verifyTotp] brings the session up exactly like a normal
/// login; this screen then pops with `true` so the login screen can finish.
class TotpScreen extends StatefulWidget {
  const TotpScreen({super.key, required this.challenge});

  /// The pending challenge from /auth/login.
  final String challenge;

  @override
  State<TotpScreen> createState() => _TotpScreenState();
}

class _TotpScreenState extends State<TotpScreen> {
  final _code = TextEditingController();
  late final String _challenge = widget.challenge;
  bool _busy = false;

  static const _red = Color(0xFFC0392B);
  static const _ink = Color(0xFF14202B);

  @override
  void dispose() {
    _code.dispose();
    super.dispose();
  }

  Future<void> _verify() async {
    final code = _code.text.trim();
    if (code.length < 6 || _busy) return;
    FocusScope.of(context).unfocus();
    setState(() => _busy = true);
    final ok = await context.read<AuthProvider>().verifyTotp(_challenge, code);
    if (!mounted) return;
    setState(() => _busy = false);
    if (ok) {
      Navigator.of(context).pop(true);
    } else {
      _code.clear();
      final err = context.read<AuthProvider>().error ??
          tr('الرمز غير صحيح', 'Incorrect code');
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err)));
    }
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    return Scaffold(
      body: Stack(children: [
        const _TotpBackdrop(),
        SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.fromLTRB(24, 12, 24, 24),
            child: Column(children: [
              Align(
                alignment: Alignment.centerLeft,
                child: IconButton(
                  icon: const Icon(Icons.arrow_back, color: Colors.white),
                  onPressed: _busy ? null : () => Navigator.pop(context, false),
                ),
              ),
              const SizedBox(height: 10),
              const Icon(Icons.security_rounded, color: Colors.white, size: 54),
              const SizedBox(height: 14),
              Text(tr('التحقّق بخطوتين', 'Two-step verification'),
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                      color: Colors.white, fontSize: 20, fontWeight: FontWeight.w900)),
              const SizedBox(height: 26),
              _card(context),
            ]),
          ),
        ),
      ]),
    );
  }

  Widget _card(BuildContext context) {
    return Container(
      constraints: const BoxConstraints(maxWidth: 420),
      padding: const EdgeInsets.fromLTRB(22, 26, 22, 22),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(24),
        boxShadow: const [
          BoxShadow(color: Color(0x40000000), blurRadius: 38, offset: Offset(0, 18)),
        ],
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
        Text(tr('أدخل رمز التحقّق', 'Enter the verification code'),
            style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w900, color: _ink)),
        const SizedBox(height: 6),
        Text(
          tr('أدخل الرمز المكوّن من 6 أرقام من تطبيق المصادقة '
              '(Google Authenticator أو Microsoft Authenticator).',
              'Enter the 6-digit code from your authenticator app '
              '(Google Authenticator or Microsoft Authenticator).'),
          style: TextStyle(fontSize: 13, color: Colors.grey.shade600, height: 1.4),
        ),
        const SizedBox(height: 20),
        TextField(
          controller: _code,
          autofocus: true,
          keyboardType: TextInputType.number,
          textAlign: TextAlign.center,
          maxLength: 6,
          enabled: !_busy,
          onSubmitted: (_) => _verify(),
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          style: const TextStyle(
              fontSize: 28, fontWeight: FontWeight.w900, letterSpacing: 12, color: _ink),
          decoration: InputDecoration(
            counterText: '',
            hintText: '••••••',
            hintStyle: TextStyle(letterSpacing: 12, color: Colors.grey.shade300),
            filled: true,
            fillColor: const Color(0xFFF4F6F8),
            contentPadding: const EdgeInsets.symmetric(vertical: 16),
            border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14), borderSide: BorderSide.none),
            enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: BorderSide(color: Colors.grey.shade200)),
            focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(14),
                borderSide: const BorderSide(color: Color(0xFF0E3A5F), width: 1.6)),
          ),
        ),
        const SizedBox(height: 14),
        Material(
          color: Colors.transparent,
          child: Ink(
            decoration: BoxDecoration(
              gradient: const LinearGradient(colors: [Color(0xFFE24A3B), _red]),
              borderRadius: BorderRadius.circular(15),
              boxShadow: [
                BoxShadow(color: _red.withValues(alpha: 0.32),
                    blurRadius: 14, offset: const Offset(0, 7)),
              ],
            ),
            child: InkWell(
              borderRadius: BorderRadius.circular(15),
              onTap: _busy ? null : _verify,
              child: SizedBox(
                height: 54,
                child: Center(
                  child: _busy
                      ? const SizedBox(height: 22, width: 22,
                          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                      : Text(tr('تحقّق ودخول', 'Verify & sign in'),
                          style: const TextStyle(color: Colors.white, fontSize: 16,
                              fontWeight: FontWeight.w900, letterSpacing: 0.5)),
                ),
              ),
            ),
          ),
        ),
      ]),
    );
  }
}

/// Brand gradient background — matches the login screen so the two-factor step
/// reads as one continuous flow.
class _TotpBackdrop extends StatelessWidget {
  const _TotpBackdrop();
  @override
  Widget build(BuildContext context) => Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topRight,
            end: Alignment.bottomLeft,
            colors: [Color(0xFFE24A3B), Color(0xFFC0392B), Color(0xFF7A1B14)],
          ),
        ),
      );
}
