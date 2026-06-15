import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:video_player/video_player.dart';

import '../i18n/i18n.dart';
import '../theme/app_colors.dart';
import 'brain_pulse.dart';

/// The localized onboarding / intro film — the Flutter mirror of the web's
/// `IntroVideo.vue` + `config/introVideo.ts`.
///
/// Picks the video version matching the active locale (English fallback for
/// locales we have not produced a film for) and re-resolves when the language
/// changes. Until the base URL is configured / reachable, shows a calm
/// Brain-Pulse placeholder instead of a broken player.

/// Languages an intro film exists for (mirrors web INTRO_VIDEO_LANGS).
const Set<String> _introVideoLangs = {'en', 'de', 'fr', 'ru', 'ar'};

/// Content CloudFront distribution, `/intro` prefix (mirrors the web default).
const String _introVideoBase = 'https://d20aaqlrgvxz3g.cloudfront.net/intro';

String _introLang(String code) => _introVideoLangs.contains(code) ? code : 'en';

/// Full URL of the intro video for a locale, or null if no base is configured.
String? introVideoUrl(String code) => _introVideoBase.isEmpty
    ? null
    : '$_introVideoBase/private_internet_intro_${_introLang(code)}.mp4';

/// A 16:9 localized intro video with tap-to-play and a graceful placeholder.
class IntroVideo extends ConsumerStatefulWidget {
  const IntroVideo({super.key, this.autoplay = false, this.loop = false, this.muted = false});

  final bool autoplay;
  final bool loop;
  final bool muted;

  @override
  ConsumerState<IntroVideo> createState() => _IntroVideoState();
}

class _IntroVideoState extends ConsumerState<IntroVideo> {
  VideoPlayerController? _controller;
  String? _lang;
  bool _ready = false;
  bool _failed = false;

  void _initFor(String localeCode) {
    final lang = _introLang(localeCode);
    if (lang == _lang) return; // already on this language
    _lang = lang;
    _controller?.dispose();
    _ready = false;
    _failed = false;

    final url = introVideoUrl(localeCode);
    if (url == null) {
      _controller = null;
      if (mounted) setState(() {});
      return;
    }
    final ctrl = VideoPlayerController.networkUrl(Uri.parse(url));
    _controller = ctrl;
    ctrl.initialize().then((_) {
      if (!mounted || _controller != ctrl) return;
      ctrl
        ..setLooping(widget.loop)
        ..setVolume(widget.muted ? 0 : 1);
      if (widget.autoplay) ctrl.play();
      setState(() => _ready = true);
    }).catchError((Object _) {
      if (mounted && _controller == ctrl) setState(() => _failed = true);
    });
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  void _toggle() {
    final ctrl = _controller;
    if (ctrl == null || !_ready) return;
    setState(() => ctrl.value.isPlaying ? ctrl.pause() : ctrl.play());
  }

  @override
  Widget build(BuildContext context) {
    // Re-resolve when the language changes. The controller swap is a side effect,
    // so defer it past this frame to avoid setState-during-build.
    final code = ref.watch(localeControllerProvider).languageCode;
    if (_introLang(code) != _lang) {
      WidgetsBinding.instance.addPostFrameCallback((_) => _initFor(code));
    }

    final ctrl = _controller;
    Widget inner;
    if (ctrl != null && _ready) {
      inner = GestureDetector(
        onTap: _toggle,
        child: Stack(
          alignment: Alignment.center,
          children: [
            VideoPlayer(ctrl),
            if (!ctrl.value.isPlaying)
              const DecoratedBox(
                decoration: BoxDecoration(color: Colors.black26),
                child: Center(child: Icon(Icons.play_arrow_rounded, size: 56, color: Colors.white)),
              ),
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: VideoProgressIndicator(ctrl, allowScrubbing: true),
            ),
          ],
        ),
      );
    } else if (ctrl != null && !_failed) {
      inner = const Center(child: CircularProgressIndicator(strokeWidth: 2));
    } else {
      inner = _Placeholder(failed: _failed);
    }

    return ClipRRect(
      borderRadius: BorderRadius.circular(12),
      child: AspectRatio(
        aspectRatio: 16 / 9,
        child: ColoredBox(color: const Color(0xFF0C0C14), child: inner),
      ),
    );
  }
}

class _Placeholder extends StatelessWidget {
  const _Placeholder({required this.failed});
  final bool failed;

  @override
  Widget build(BuildContext context) {
    final c = context.c;
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const BrainPulse(size: 48, slow: true),
        const SizedBox(height: 12),
        Text(
          failed ? 'Intro video unavailable' : 'Intro video coming soon',
          style: TextStyle(fontSize: 13, color: c.textSecondary),
        ),
      ],
    );
  }
}
