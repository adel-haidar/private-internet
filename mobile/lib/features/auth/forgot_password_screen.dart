import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api/api_endpoints.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_dimens.dart';
import '../../core/theme/app_text_styles.dart';
import '../../core/widgets/app_button.dart';
import '../../core/widgets/app_input.dart';
import '../../core/widgets/brain_pulse.dart';
import '../../providers/core_providers.dart';

/// Request a password-reset link (`POST /api/auth/forgot-password`).
///
/// Always shows the same confirmation regardless of whether the email exists,
/// so it never leaks which addresses have accounts. The reset link itself is
/// completed on the web (the email contains a web URL).
class ForgotPasswordScreen extends ConsumerStatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  ConsumerState<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends ConsumerState<ForgotPasswordScreen> {
  final _email = TextEditingController();
  bool _loading = false;
  bool _sent = false;

  @override
  void dispose() {
    _email.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final email = _email.text.trim();
    if (email.isEmpty) return;
    setState(() => _loading = true);
    try {
      await ref.read(apiClientProvider).post(ApiEndpoints.forgotPassword, body: {'email': email});
    } catch (_) {
      // Swallow errors: we show the same neutral confirmation either way so we
      // never reveal whether an account exists.
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
          _sent = true;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final c = context.c;
    return Scaffold(
      appBar: AppBar(),
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(AppDimens.space6),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Center(child: BrainPulse(size: 56)),
                  const SizedBox(height: AppDimens.space5),
                  Text('Reset your password',
                      textAlign: TextAlign.center, style: AppText.lg.copyWith(color: c.textPrimary)),
                  const SizedBox(height: AppDimens.space2),
                  if (_sent) ...[
                    Text(
                      'If an account exists for that email, a reset link is on its way. '
                      'Open it on the web to choose a new password.',
                      textAlign: TextAlign.center,
                      style: AppText.sm.copyWith(color: c.textSecondary),
                    ),
                    const SizedBox(height: AppDimens.space6),
                    AppButton(label: 'Back to sign in', onPressed: () => context.pop(), expand: true),
                  ] else ...[
                    Text('Enter your email and we’ll send you a reset link.',
                        textAlign: TextAlign.center, style: AppText.sm.copyWith(color: c.textSecondary)),
                    const SizedBox(height: AppDimens.space6),
                    AppInput(
                      label: 'Email',
                      hint: 'you@example.com',
                      controller: _email,
                      keyboardType: TextInputType.emailAddress,
                      textInputAction: TextInputAction.done,
                      onSubmitted: (_) => _submit(),
                    ),
                    const SizedBox(height: AppDimens.space6),
                    AppButton(label: 'Send reset link', onPressed: _submit, loading: _loading, expand: true),
                  ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
