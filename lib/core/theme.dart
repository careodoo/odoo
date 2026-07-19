import 'package:flutter/material.dart';
import 'i18n.dart';

/// One app, a distinct visual identity per service. These accents mirror the
/// Odoo backend so the field app and the web console feel like one system.
class ServiceTheme {
  const ServiceTheme(this.labelAr, this.labelEn, this.accent, this.icon, this.dark);
  final String labelAr;
  final String labelEn;
  /// Resolved in the viewer's language. The map is const, so tr() cannot live
  /// inside it — both spellings are carried and chosen here instead.
  String get label => tr(labelAr, labelEn);
  final Color accent;
  final String icon;
  /// Security leans into a darker, high-contrast "command" look.
  final bool dark;

  static const Map<String, ServiceTheme> byType = {
    'security': ServiceTheme('الأمن والحراسة', 'Security & guarding', Color(0xFFE5484D), '🛡️', true),
    'cleaning': ServiceTheme('النظافة', 'Cleaning', Color(0xFF2F6DF6), '🧹', false),
    'agriculture': ServiceTheme('الزراعة', 'Landscaping', Color(0xFF37C98A), '🌿', false),
    'facade': ServiceTheme('الواجهات', 'Facade', Color(0xFF38BDF8), '🪟', false),
    'maintenance': ServiceTheme('الصيانة', 'Maintenance', Color(0xFFF7A23B), '❄️', false),
    'worker': ServiceTheme('العامل', 'Worker', Color(0xFFF7A23B), '👷', false),
    'client': ServiceTheme('العميل', 'Client', Color(0xFFC0392B), '🧑‍💼', false),
  };

  static ServiceTheme of(String type) =>
      byType[type] ?? byType['worker']!;
}

ThemeData buildTheme(ServiceTheme s) {
  final base = s.dark ? Brightness.dark : Brightness.light;
  final scheme = ColorScheme.fromSeed(
    seedColor: s.accent,
    brightness: base,
  );
  return ThemeData(
    useMaterial3: true,
    fontFamily: 'Tajawal',
    colorScheme: scheme,
    scaffoldBackgroundColor: s.dark ? const Color(0xFF0B1220) : const Color(0xFFF4F6FA),
    appBarTheme: AppBarTheme(
      backgroundColor: s.dark ? const Color(0xFF0F172A) : s.accent,
      foregroundColor: Colors.white,
      elevation: 0,
      centerTitle: true,
    ),
    cardTheme: CardThemeData(
      elevation: 0,
      color: s.dark ? const Color(0xFF152238) : Colors.white,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      margin: const EdgeInsets.symmetric(vertical: 6),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(
        minimumSize: const Size.fromHeight(52),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
      ),
    ),
  );
}

/// Right-to-left, Arabic-first.
const appLocale = Locale('ar');
