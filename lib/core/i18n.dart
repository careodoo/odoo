import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Lightweight bilingual layer. Strings are supplied inline as `tr('عربي','EN')`
/// so the Arabic source stays readable and English is added alongside — no
/// separate key files to keep in sync.
String gLang = 'ar';

String tr(String ar, String en) => gLang == 'en' ? en : ar;

class LangProvider extends ChangeNotifier {
  final _st = const FlutterSecureStorage();

  Future<void> load() async {
    gLang = (await _st.read(key: 'care_lang')) ?? 'ar';
    notifyListeners();
  }

  String get lang => gLang;
  bool get isArabic => gLang == 'ar';

  Future<void> setLang(String l) async {
    gLang = l;
    await _st.write(key: 'care_lang', value: l);
    notifyListeners();
  }

  Future<void> toggle() => setLang(gLang == 'ar' ? 'en' : 'ar');
}
