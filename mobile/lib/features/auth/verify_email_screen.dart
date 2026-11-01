import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/repository.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import 'auth_controller.dart';
import 'auth_widgets.dart';

/// What the verify screen needs, passed in memory (never in the URL, since it holds the password).
typedef VerifyEmailArgs = ({String email, String password});

/// After sign-up (or signing in to an unconfirmed account): enter the 6-digit code emailed to the new address.
/// The password typed a moment ago is sent with the code, so only the person who chose it can activate the account.
class VerifyEmailScreen extends ConsumerStatefulWidget {
  const VerifyEmailScreen({super.key, required this.args});
  final VerifyEmailArgs args;

  @override
  ConsumerState<VerifyEmailScreen> createState() => _VerifyEmailScreenState();
}

class _VerifyEmailScreenState extends ConsumerState<VerifyEmailScreen> {
  final _code = TextEditingController();
  bool _loading = false;
  String? _error;
  int _resendIn = 60; // a code was just sent by sign-up or sign-in
  Timer? _timer;

  @override
  void initState() {
    super.initState();
    _startResendTimer();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _code.dispose();
    super.dispose();
  }

  void _startResendTimer() {
    _timer?.cancel();
    _resendIn = 60;
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (!mounted) return t.cancel();
      setState(() => _resendIn = (_resendIn - 1).clamp(0, 60));
      if (_resendIn == 0) t.cancel();
    });
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await action();
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _verify() async {
    if (_code.text.trim().length != 6) {
      setState(() => _error = 'Enter the 6-digit code from your email');
      return;
    }
    // On success the router sees the signed-in state and opens Home.
    await _run(() => ref
        .read(authControllerProvider.notifier)
        .verifyEmail(widget.args.email, widget.args.password, _code.text.trim()));
  }

  Future<void> _resend() => _run(() async {
        await ref.read(repositoryProvider).resendVerification(widget.args.email);
        setState(_startResendTimer);
        if (mounted) showSnack(context, 'A new code has been sent');
      });

  @override
  Widget build(BuildContext context) {
    return AuthLayout(
      title: 'Confirm your email',
      subtitle: 'We sent a 6-digit code to ${widget.args.email}. Enter it to activate your account.',
      children: [
        if (_error != null) ErrorBanner(_error!),
        const FieldLabel('6-DIGIT CODE'),
        TextField(
          controller: _code,
          autofocus: true,
          keyboardType: TextInputType.number,
          textAlign: TextAlign.center,
          maxLength: 6,
          autofillHints: const [AutofillHints.oneTimeCode],
          inputFormatters: [FilteringTextInputFormatter.digitsOnly],
          style: const TextStyle(fontSize: 26, letterSpacing: 12, fontWeight: FontWeight.w700),
          decoration: const InputDecoration(hintText: '••••••', counterText: ''),
          onChanged: (v) {
            if (v.length == 6) _verify();
          },
        ),
        const SizedBox(height: 22),
        FilledButton(
          onPressed: _loading ? null : _verify,
          child: _loading
              ? SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.4, color: context.c.onBrand))
              : const Text('Verify and continue'),
        ),
        const SizedBox(height: 6),
        Center(
          child: TextButton(
            onPressed: _resendIn > 0 || _loading ? null : _resend,
            child: Text(_resendIn > 0 ? 'Resend code in ${_resendIn}s' : 'Resend code'),
          ),
        ),
        Text(
          "Didn't get it? Check spam or junk. Wrong address? Go back and sign up again with the right email.",
          textAlign: TextAlign.center,
          style: TextStyle(color: context.c.muted, fontSize: 12),
        ),
        const SizedBox(height: 10),
        Center(
          child: TextButton(
            onPressed: () => context.go(Uri(path: '/login', queryParameters: {'email': widget.args.email}).toString()),
            child: const Text('Back to sign in'),
          ),
        ),
      ],
    );
  }
}
