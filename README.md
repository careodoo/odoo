# Care Field — تطبيق الميدان (Flutter)

تطبيق موبايل حقيقي (iOS + Android) لنظام Care CAFM والأمن، يستهلك واجهة Odoo
`/api/v1` بمصادقة **Bearer token** (لا كوكيز). تطبيق واحد بوجوه مختلفة:
حارس الأمن يفتح **مركز الأمن** (شاشة داكنة احترافية)، وعامل النظافة/الزراعة/الواجهات
يفتح شاشة **العامل** (مهام + مسح QR للحضور).

> هذا المجلد يحوي كود التطبيق (`lib/`) وإعداداته. **مجلدات المنصّات (android/ ios/)
> تُولَّد على جهازك** عبر `flutter create` (خطوة واحدة أدناه).

---

## ١) المتطلبات (على جهازك، ليس السيرفر)

- **Flutter SDK ≥ 3.19** — https://docs.flutter.dev/get-started/install
- **Android:** Android Studio + JDK (لبناء APK/AAB)
- **iOS:** **جهاز Mac** + Xcode (إلزامي — لا يمكن بناء iOS إلا على macOS)
- حسابات النشر:
  - Google Play Console (25$ مرة واحدة)
  - Apple Developer Program (99$/سنة)

## ٢) التهيئة الأولى

```bash
cd care_mobile
# يولّد android/ ios/ مع الحفاظ على lib/ الحالي
flutter create --org com.carekw --project-name care_mobile --platforms=android,ios .
flutter pub get
```

### الأذونات المطلوبة (الكاميرا لمسح QR)

- **Android** — في `android/app/src/main/AndroidManifest.xml` أضِف قبل `<application>`:
  ```xml
  <uses-permission android:name="android.permission.CAMERA"/>
  <uses-permission android:name="android.permission.INTERNET"/>
  ```
- **iOS** — في `ios/Runner/Info.plist` أضِف:
  ```xml
  <key>NSCameraUsageDescription</key>
  <string>لمسح رموز QR الخاصة بالمواقع ونقاط الدوريات</string>
  ```

## ٣) عنوان الـAPI

الافتراضي `https://ecare.care-kw.com/api/v1`. لتغييره وقت التشغيل/البناء:

```bash
flutter run --dart-define=CARE_API_BASE=https://YOUR_HOST/api/v1
```

## ٤) التشغيل للتجربة

```bash
flutter devices          # تأكّد من وجود جهاز/محاكي
flutter run              # أو flutter run --release
```

بيانات دخول للتجربة: `cafmtest` / `cafm12345`
(للتجربة الأمنية: ادخل بمستخدم مرتبط بموظف له أوامر عمل من نوع "security" ليفتح مركز الأمن).

## ٥) بناء نسخة الإصدار

```bash
# Android — App Bundle للنشر على Play
flutter build appbundle --release --dart-define=CARE_API_BASE=https://ecare.care-kw.com/api/v1
# الناتج: build/app/outputs/bundle/release/app-release.aab

# Android — APK للتجربة المباشرة
flutter build apk --release

# iOS (على Mac فقط)
flutter build ipa --release
# ثم ارفع عبر Xcode / Transporter
```

## ٦) النشر على المتاجر (خطوات مختصرة)

**Google Play:**
1. أنشئ تطبيقاً في Play Console، عبِّئ بيانات المتجر (وصف، أيقونة، لقطات).
2. ارفع `app-release.aab` في مسار Internal testing ثم Production.
3. جهّز App signing (Play App Signing تلقائي).

**App Store:**
1. أنشئ App ID و تطبيقاً في App Store Connect بنفس `com.carekw.careMobile`.
2. من Xcode: Archive → Distribute → Upload.
3. عبِّئ بيانات المتجر واطلب المراجعة.

> ملاحظة مهمة لقبول Apple: هذا تطبيق native حقيقي (ليس غلاف ويب)، ويؤدي وظائف
> ميدانية (كاميرا، مسح، مهام) — وهو ما يقبله المُراجِع عادةً دون مشاكل.

---

## البنية

```
lib/
  main.dart                 نقطة الدخول + التوجيه حسب الجلسة/الدور (RTL, عربي)
  core/
    api_client.dart         عميل /api/v1 + تخزين آمن للـtoken
    auth.dart               حالة الجلسة (Provider)
    theme.dart              هوية بصرية لكل خدمة (الأمن = مظهر قيادة داكن)
  models/models.dart        نماذج JSON (Profile, Service, WorkOrder)
  screens/
    login_screen.dart       تسجيل الدخول
    home_screen.dart        موجّه الأدوار → شاشة العامل
    security_home.dart      مركز الأمن (7 تايلات، الشاشة المميّزة)
    security_incidents_screen.dart  البلاغات: عرض + تسجيل حادث
    security_list_screen.dart       قوائم الدوريات/المفاتيح/البوابة
    workorders_screen.dart  أوامر العمل + بدء/إنهاء
    scan_screen.dart        ماسح QR حيّ + إثبات حضور
```

## نقاط الـAPI المتاحة (`/api/v1`)

| المسار | الطريقة | الوظيفة |
|--------|---------|---------|
| `/auth/login` `/auth/logout` | POST | دخول (يرجّع token) · خروج (يُلغي الرمز) |
| `/me` · `/services` | GET | الملف والدور والخدمات · قائمة الخدمات |
| `/workorders` `[/<id>][/start\|/done]` | GET/POST | مهامي · بدء (حضور) · إنهاء (عدّاد) |
| `/scan` | POST | مسح رمز موقع → الموقع + أوامر العمل عنده |
| `/security/incidents` | GET/POST | البلاغات · تسجيل حادث (Security Manager) |
| `/security/patrols` `/keys` `/gatepasses` | GET | الدوريات · المفاتيح · تصاريح البوابة |

كل المسارات (عدا الدخول) تتطلّب ترويسة `Authorization: Bearer <token>`؛ بدونها ترجّع 401.
نقاط الأمن تقرأ/تكتب مباشرة في وحدة **Security Manager** المستقلة.
