import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'i18n_dict.dart';

/// Lightweight multilingual layer. Strings are supplied inline as
/// `tr('عربي','EN')` so the Arabic source stays readable and English is added
/// alongside — no separate key files to keep in sync for those two. For any
/// other language, the English string is looked up in [kDict] (see i18n_dict.dart)
/// and falls back to English when a key is missing.
String gLang = 'ar';

String tr(String ar, String en) {
  if (gLang == 'ar') return ar;
  if (gLang == 'en') return en;
  return kDict[gLang]?[en] ?? en;
}

/// Whether the current language is right-to-left.
bool get gIsRtl => kRtlLangs.contains(gLang);

class LangProvider extends ChangeNotifier {
  final _st = const FlutterSecureStorage();

  /// True until the user has explicitly picked a language once (first launch).
  bool firstRun = false;

  Future<void> load() async {
    final stored = await _st.read(key: 'care_lang');
    firstRun = stored == null;
    gLang = stored ?? 'ar';
    notifyListeners();
  }

  String get lang => gLang;
  bool get isArabic => gLang == 'ar';
  bool get isRtl => gIsRtl;

  /// All supported languages as [code, nativeName] pairs.
  List<List<String>> get languages => kLanguages;

  Future<void> setLang(String l) async {
    gLang = l;
    firstRun = false;
    await _st.write(key: 'care_lang', value: l);
    notifyListeners();
  }

  Future<void> toggle() => setLang(gLang == 'ar' ? 'en' : 'ar');
}

/// Odoo sends an unset number as `false`, never null. `x as num?` accepts a
/// num or null and throws on anything else, so every `numOf(m['f'], 0)`
/// across the app was one empty field away from crashing the screen it was on.
/// This narrows by type instead of casting.
num numOf(dynamic v, [num fallback = 0]) => v is num ? v : fallback;

/// The same, for the common `.toDouble()` / `.toInt()` follow-ups.
double dblOf(dynamic v, [double fallback = 0]) => v is num ? v.toDouble() : fallback;
int intOf(dynamic v, [int fallback = 0]) => v is num ? v.toInt() : fallback;
