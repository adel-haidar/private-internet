import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/core_providers.dart';
import 'messages.g.dart';

/// Lightweight, dependency-free i18n — the Flutter mirror of the web's
/// `frontend/src/i18n` singleton. Same locales, same keys (`kMessages` is
/// generated from the web locale files), same English fallback + `{param}`
/// interpolation, and the same RTL handling for Arabic.
///
/// Usage in a ConsumerWidget: `ref.t('nav.dashboard')`. Reading the locale via
/// `ref.watch` inside `t()` makes widgets rebuild on language change.

/// One selectable language. `label` is the endonym shown in the picker.
class LocaleMeta {
  const LocaleMeta(this.code, this.label, {this.rtl = false});
  final String code;
  final String label;
  final bool rtl;
}

/// Order shown in the language picker (matches the web).
const List<LocaleMeta> kLocales = [
  LocaleMeta('en', 'English'),
  LocaleMeta('de', 'Deutsch'),
  LocaleMeta('es', 'Español'),
  LocaleMeta('fr', 'Français'),
  LocaleMeta('ru', 'Русский'),
  LocaleMeta('zh', '中文'),
  LocaleMeta('ar', 'العربية', rtl: true),
];

const Set<String> _rtlCodes = {'ar'};
const String _storageKey = 'pi-locale'; // same key intent as the web

bool isSupportedLocale(String code) => kMessages.containsKey(code);
bool isRtlLocale(String code) => _rtlCodes.contains(code);

/// Persists and exposes the active [Locale]. Mirrors `ThemeController`.
class LocaleController extends Notifier<Locale> {
  @override
  Locale build() {
    final prefs = ref.watch(sharedPreferencesProvider);
    final saved = prefs.getString(_storageKey);
    if (saved != null && isSupportedLocale(saved)) return Locale(saved);
    // Fall back to the device language if we support it, else English.
    final sys = WidgetsBinding.instance.platformDispatcher.locale.languageCode;
    return Locale(isSupportedLocale(sys) ? sys : 'en');
  }

  /// Sets and persists the language. No-op for unsupported codes.
  Future<void> set(String code) async {
    if (!isSupportedLocale(code)) return;
    state = Locale(code);
    await ref.read(sharedPreferencesProvider).setString(_storageKey, code);
  }
}

/// The active locale.
final localeControllerProvider =
    NotifierProvider<LocaleController, Locale>(LocaleController.new);

Object? _lookup(Map<String, dynamic>? messages, String key) {
  Object? current = messages;
  for (final part in key.split('.')) {
    if (current is Map && current.containsKey(part)) {
      current = current[part] as Object?;
    } else {
      return null;
    }
  }
  return current;
}

/// dot-path lookup with English fallback, raw-key fallback, and `{param}`
/// interpolation — never blank, never throws.
String translate(String code, String key, [Map<String, Object?>? params]) {
  final raw = _lookup(kMessages[code], key) ??
      _lookup(kMessages['en'], key) ??
      key;
  if (raw is! String) return key;
  if (params == null || params.isEmpty) return raw;
  return raw.replaceAllMapped(RegExp(r'\{(\w+)\}'), (m) {
    final name = m.group(1)!;
    return params.containsKey(name) ? '${params[name]}' : '{$name}';
  });
}

/// Ergonomic `ref.t('key')` that also subscribes the widget to locale changes.
extension I18nRef on WidgetRef {
  String t(String key, [Map<String, Object?>? params]) =>
      translate(watch(localeControllerProvider).languageCode, key, params);
}
