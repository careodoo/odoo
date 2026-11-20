import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// Second step of two-factor login. Reached only when /auth/login answered with
/// `need_otp` — the account has app 2FA on, a 6-digit code was e-mailed, and no
/// session exists yet. On a correct code the server issues the real token and
/// [AuthProvider.verifyOtp] brings the session up exactly like a normal login;
/// this screen then pops with `true` so the login screen can finish.
class OtpScreen extends StatefulWidget {
  const OtpScreen({super.key, required this.challenge, this.maskedEmail});

  /// The pending challenge from /auth/login (rotated by each resend).
  final String challenge;

  /// Masked destination address (e.g. `a***@care-kw.com`) for the hint, if the
  /// server provided one.
  final String? maskedEmail;

  @override
  State<OtpScreen> createState() => _OtpScreenState();
}

class _OtpScreenState extends State<OtpScreen> {
  final _code = TextEditingController();
  late String _challenge = widget.challenge;
  bool _busy = false;
  bool _resending = false;
  int _cooldown = 0;
  Timer? _timer;

  static const _red = Color(0xFFC0392B);
  static const _ink = Color(0xFF14202B);

  @override
  void initState() {
    super.initState();
    _startCooldown();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _code.dispose();
    super.dispose();
  }

  /// A 30s window before the code can be re-sent — long enough that the e-mail
  /// has a chance to arrive, short enough not to strand a user whose code went
  /// astray.
  void _startCooldown() {
    _timer?.cancel();
    setState(() => _cooldown = 30);
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (!mounted) return;
      if (_cooldown <= 1) {
        t.cancel();
        setState(() => _cooldown = 0);
      } else {
        setState(() => _cooldown--);
      }
    });
  }

  Future<void> _verify() async {
    final code = _code.text.trim();
    if (code.length < 4 || _busy) return;
    FocusScope.of(context).unfocus();
    setState(() => _busy = true);
    final ok = await context.read<AuthProvider>().verifyOtp(_challenge, code);
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

  Future<void> _resend() async {
    if (_cooldown > 0 || _resending) return;
    setState(() => _resending = true);
    final data = await context.read<AuthProvider>().resendOtp(_challenge);
    if (!mounted) return;
    setState(() => _resending = false);
    if (data != null) {
      // The server rotates the challenge on resend — adopt the new one, or the
      // next verify would be checked against the now-invalid old session.
      final ch = '${data['challenge'] ?? ''}';
      if (ch.isNotEmpty) _challenge = ch;
      _code.clear();
      _startCooldown();
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text(tr('أُرسِل رمز جديد', 'A new code has been sent')),
        backgroundColor: const Color(0xFF16A34A),
      ));
    } else {
      final err = context.read<AuthProvider>().error ??
          tr('تعذّر إعادة الإرسال', 'Could not resend the code');
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err)));
    }
  }

  @override
  Widget build(BuildContext context) {
    context.watch<LangProvider>();
    return Scaffold(
      body: Stack(children: [
        const _OtpBackdrop(),
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
              const Icon(Icons.verified_user_rounded, color: Colors.white, size: 54),
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
        RichText(
          text: TextSpan(
            style: TextStyle(fontSize: 13, color: Colors.grey.shade600, height: 1.4),
            children: [
              TextSpan(text: tr('أرسلنا رمزاً مكوّناً من 6 أرقام إلى ',
                  'We sent a 6-digit code to ')),
              TextSpan(
                text: (widget.maskedEmail != null && widget.maskedEmail!.isNotEmpty)
                    ? widget.maskedEmail!
                    : tr('بريدك المسجّل', 'your registered e-mail'),
                style: const TextStyle(fontWeight: FontWeight.w900, color: _ink),
              ),
            ],
          ),
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
        const SizedBox(height: 14),
        Center(
          child: _resending
              ? const SizedBox(height: 18, width: 18,
                  child: CircularProgressIndicator(strokeWidth: 2))
              : _cooldown > 0
                  ? Text(
                      tr('يمكنك إعادة الإرسال خلال $_cooldown ثانية',
                          'You can resend in ${_cooldown}s'),
                      style: TextStyle(fontSize: 13, color: Colors.grey.shade500))
                  : TextButton(
                      onPressed: _resend,
                      child: Text(tr('لم يصلك الرمز؟ إعادة الإرسال',
                          "Didn't get it? Resend code"),
                          style: const TextStyle(
                              fontSize: 13, color: _red, fontWeight: FontWeight.w900)),
                    ),
        ),
      ]),
    );
  }
}

/// Brand gradient background — matches the login screen so the two-factor step
/// reads as one continuous flow.
class _OtpBackdrop extends StatelessWidget {
  const _OtpBackdrop();
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
