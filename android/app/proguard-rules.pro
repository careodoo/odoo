# ML Kit text recognition ships one recogniser per script. We only bundle the
# Latin one, but the Flutter plugin references the Chinese, Devanagari, Japanese
# and Korean options classes, so R8 fails on classes that were never meant to be
# in the build. Nothing calls them at runtime.
-dontwarn com.google.mlkit.vision.text.chinese.**
-dontwarn com.google.mlkit.vision.text.devanagari.**
-dontwarn com.google.mlkit.vision.text.japanese.**
-dontwarn com.google.mlkit.vision.text.korean.**
-keep class com.google.mlkit.vision.text.latin.** { *; }
