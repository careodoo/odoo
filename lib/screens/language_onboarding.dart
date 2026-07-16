import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../core/auth.dart';
import '../core/i18n.dart';

/// First-launch language chooser. Shown once (LangProvider.firstRun) so a
/// worker who reads only Hindi/Urdu/etc. isn't stuck on the Arabic default.
class LanguageOnboardingScreen extends StatelessWidget {
  const LanguageOnboardingScreen({super.key});

  static const _navy = Color(0xFF0E3A5F);
  static const _navy2 = Color(0xFF17547F);

  // secondary "welcome" line per language so each option reads in its own tongue
  static const _hello = {
    'ar': 'أهلاً بك', 'en': 'Welcome', 'hi': 'स्वागत है', 'ur': 'خوش آمدید',
    'bn': 'স্বাগতম', 'ne': 'स्वागत छ', 'fil': 'Maligayang pagdating',
  };

  @override
  Widget build(BuildContext context) {
    final langs = context.read<LangProvider>().languages;
    return Scaffold(
      backgroundColor: const Color(0xFFF4F7FB),
      body: SafeArea(
        child: Column(children: [
          // brand header
          Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(24, 34, 24, 28),
            decoration: const BoxDecoration(
              gradient: LinearGradient(colors: [_navy2, _navy, Color(0xFF0A2A44)], begin: Alignment.topRight, end: Alignment.bottomLeft),
              borderRadius: BorderRadius.vertical(bottom: Radius.circular(30)),
            ),
            child: Column(children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(color: Colors.white.withValues(alpha: 0.15), shape: BoxShape.circle, border: Border.all(color: Colors.white24, width: 2)),
                child: const Icon(Icons.translate_rounded, color: Colors.white, size: 40),
              ),
              const SizedBox(height: 16),
              const Text('CARE', style: TextStyle(color: Colors.white, fontSize: 30, fontWeight: FontWeight.w900, letterSpacing: 3)),
              const SizedBox(height: 6),
              const Text('اختر لغتك · Choose your language', textAlign: TextAlign.center, style: TextStyle(color: Colors.white70, fontSize: 13.5, fontWeight: FontWeight.w600)),
            ]),
          ),
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.fromLTRB(16, 18, 16, 24),
              itemCount: langs.length,
              separatorBuilder: (_, __) => const SizedBox(height: 10),
              itemBuilder: (_, i) {
                final code = langs[i][0], name = langs[i][1];
                return Material(
                  color: Colors.white, borderRadius: BorderRadius.circular(16),
                  child: InkWell(
                    borderRadius: BorderRadius.circular(16),
                    onTap: () => context.read<LangProvider>().setLang(code),
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 15),
                      decoration: BoxDecoration(borderRadius: BorderRadius.circular(16), border: Border.all(color: Colors.black12)),
                      child: Row(children: [
                        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          Text(name, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16.5, color: _navy)),
                          const SizedBox(height: 2),
                          Text(_hello[code] ?? '', style: const TextStyle(color: Color(0xFF64748B), fontSize: 12.5, fontWeight: FontWeight.w600)),
                        ])),
                        Container(
                          padding: const EdgeInsets.all(8),
                          decoration: const BoxDecoration(color: Color(0xFFEAF1FB), shape: BoxShape.circle),
                          child: const Icon(Icons.arrow_forward_rounded, color: _navy, size: 18),
                        ),
                      ]),
                    ),
                  ),
                );
              },
            ),
          ),
        ]),
      ),
    );
  }
}
