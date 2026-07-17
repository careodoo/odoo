import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/i18n.dart';

/// First-launch language chooser — the very first screen anyone sees, so it
/// carries the brand rather than looking like a settings list. Shown once
/// (LangProvider.firstRun) so a worker who reads only Hindi/Urdu/etc. isn't
/// stranded on the Arabic default.
class LanguageOnboardingScreen extends StatefulWidget {
  const LanguageOnboardingScreen({super.key});

  @override
  State<LanguageOnboardingScreen> createState() => _LanguageOnboardingScreenState();
}

class _LanguageOnboardingScreenState extends State<LanguageOnboardingScreen>
    with SingleTickerProviderStateMixin {
  static const _navy = Color(0xFFC0392B);       // brand red (used as the accent)
  static const _navy2 = Color(0xFFE24A3B);      // bright red
  static const _deep = Color(0xFF7A1C14);       // deep red ground
  static const _red = Color(0xFFF5A623);        // warm amber pop
  // a cheerful coordinated glyph gradient per language
  static const _glyphGrads = [
    [Color(0xFFE24A3B), Color(0xFFC0392B)], [Color(0xFFF39C4B), Color(0xFFE67E22)],
    [Color(0xFF20BFA9), Color(0xFF16A085)], [Color(0xFF4A90D9), Color(0xFF2980B9)],
    [Color(0xFFB06AB3), Color(0xFF8E44AD)], [Color(0xFF52C77E), Color(0xFF27AE60)],
    [Color(0xFFEC5F8E), Color(0xFFC2185B)],
  ];

  /// A greeting in each language's own tongue — the point of the screen is that
  /// you can find yours without reading any of the others.
  static const _hello = {
    'ar': 'أهلاً بك', 'en': 'Welcome', 'hi': 'स्वागत है', 'ur': 'خوش آمدید',
    'bn': 'স্বাগতম', 'ne': 'स्वागत छ', 'fil': 'Maligayang pagdating',
  };

  /// A letter from each script, so the tile is recognisable at a glance even to
  /// someone who is scanning rather than reading.
  static const _glyph = {
    'ar': 'ع', 'en': 'A', 'hi': 'अ', 'ur': 'ا', 'bn': 'অ', 'ne': 'न', 'fil': 'F',
  };

  String? _picked;
  late final AnimationController _in = AnimationController(
      vsync: this, duration: const Duration(milliseconds: 520))
    ..forward();

  @override
  void dispose() {
    _in.dispose();
    super.dispose();
  }

  Future<void> _choose(String code) async {
    setState(() => _picked = code);
    // let the tick land before the app rebuilds under us
    await Future.delayed(const Duration(milliseconds: 220));
    if (mounted) context.read<LangProvider>().setLang(code);
  }

  @override
  Widget build(BuildContext context) {
    final langs = context.read<LangProvider>().languages;
    return Scaffold(
      backgroundColor: _deep,
      body: Stack(children: [
        // ambient brand wash
        const Positioned.fill(child: DecoratedBox(decoration: BoxDecoration(
          gradient: LinearGradient(colors: [_navy2, _navy, _deep],
              begin: Alignment.topRight, end: Alignment.bottomLeft),
        ))),
        Positioned(top: -70, right: -60, child: _blob(220, Colors.white.withValues(alpha: 0.05))),
        Positioned(top: 130, left: -70, child: _blob(180, _red.withValues(alpha: 0.16))),
        Positioned(bottom: -60, right: -40, child: _blob(200, Colors.white.withValues(alpha: 0.04))),
        SafeArea(
          child: FadeTransition(
            opacity: _in,
            child: Column(children: [
              const SizedBox(height: 26),
              // ---- brand ----
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(24),
                  border: Border.all(color: Colors.white.withValues(alpha: 0.22), width: 1.5),
                ),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(14),
                  child: Image.asset('assets/app_icon.png', width: 54, height: 54,
                      errorBuilder: (_, __, ___) =>
                          const Icon(Icons.translate_rounded, color: Colors.white, size: 44)),
                ),
              ),
              const SizedBox(height: 16),
              const Text('CARE',
                  style: TextStyle(color: Colors.white, fontSize: 32, fontWeight: FontWeight.w900, letterSpacing: 6)),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 5),
                decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: Colors.white.withValues(alpha: 0.16))),
                child: const Text('اختر لغتك · Choose your language',
                    style: TextStyle(color: Colors.white70, fontSize: 12.5, fontWeight: FontWeight.w700)),
              ),
              const SizedBox(height: 22),
              // ---- languages ----
              Expanded(
                child: GridView.builder(
                  padding: const EdgeInsets.fromLTRB(16, 2, 16, 18),
                  gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                    crossAxisCount: 2, crossAxisSpacing: 11, mainAxisSpacing: 11, childAspectRatio: 1.52,
                  ),
                  itemCount: langs.length,
                  itemBuilder: (_, i) => _tile(langs[i][0], langs[i][1], i),
                ),
              ),
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text('يمكنك تغييرها لاحقًا من حسابك · You can change this later',
                    style: TextStyle(color: Colors.white.withValues(alpha: 0.45), fontSize: 10.5, fontWeight: FontWeight.w600)),
              ),
            ]),
          ),
        ),
      ]),
    );
  }

  Widget _tile(String code, String name, int i) {
    final on = _picked == code;
    // stagger the entrance so the grid assembles instead of snapping in
    final t = CurvedAnimation(
        parent: _in,
        curve: Interval((i * 0.07).clamp(0.0, 0.6), 1, curve: Curves.easeOutCubic));
    return FadeTransition(
      opacity: t,
      child: SlideTransition(
        position: Tween(begin: const Offset(0, 0.16), end: Offset.zero).animate(t),
        child: Material(
          color: Colors.transparent,
          child: InkWell(
            borderRadius: BorderRadius.circular(18),
            onTap: () => _choose(code),
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 180),
              padding: const EdgeInsets.fromLTRB(13, 11, 13, 11),
              decoration: BoxDecoration(
                color: on ? Colors.white : Colors.white.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(
                    color: on ? Colors.white : Colors.white.withValues(alpha: 0.18),
                    width: on ? 2 : 1),
                boxShadow: on
                    ? [BoxShadow(color: Colors.black.withValues(alpha: 0.25), blurRadius: 14, offset: const Offset(0, 5))]
                    : null,
              ),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(children: [
                  Container(
                    width: 34, height: 34, alignment: Alignment.center,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(colors: _glyphGrads[i % _glyphGrads.length],
                          begin: Alignment.topRight, end: Alignment.bottomLeft),
                      borderRadius: BorderRadius.circular(11),
                      boxShadow: on ? [BoxShadow(color: _glyphGrads[i % _glyphGrads.length][1].withValues(alpha: 0.4), blurRadius: 8, offset: const Offset(0, 3))] : null,
                    ),
                    child: Text(_glyph[code] ?? '•',
                        style: const TextStyle(color: Colors.white, fontSize: 16, fontWeight: FontWeight.w900)),
                  ),
                  const Spacer(),
                  AnimatedScale(
                    duration: const Duration(milliseconds: 180),
                    scale: on ? 1 : 0,
                    child: const Icon(Icons.check_circle_rounded, color: Color(0xFF16A34A), size: 20),
                  ),
                ]),
                const Spacer(),
                Text(name,
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                        color: on ? const Color(0xFF1E293B) : Colors.white,
                        fontSize: 15.5, fontWeight: FontWeight.w900)),
                const SizedBox(height: 2),
                Text(_hello[code] ?? '',
                    maxLines: 1, overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                        color: on ? const Color(0xFF64748B) : Colors.white.withValues(alpha: 0.6),
                        fontSize: 11.5, fontWeight: FontWeight.w600)),
              ]),
            ),
          ),
        ),
      ),
    );
  }

  Widget _blob(double s, Color c) =>
      Container(width: s, height: s, decoration: BoxDecoration(color: c, shape: BoxShape.circle));
}
