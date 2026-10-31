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

enum _Step { email, code, password, done }

/// Forgot password: email -> 6-digit code from the inbox -> new password.
class ForgotPasswordScreen extends ConsumerStatefulWidget {
  const ForgotPasswordScreen({super.key, this.initialEmail});
  final String? initialEmail;

  @override
  ConsumerState<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends ConsumerState<ForgotPasswordScreen> {
  final _emailForm = GlobalKey<FormState>();
  final _passwordForm = GlobalKey<FormState>();
  late final _email = TextEditingController(text: widget.initialEmail ?? '');
  final _code = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();

  _Step _step = _Step.email;
  bool _loading = false;
  String? _error;
  String? _resetToken;
  int _resendIn = 0;
  Timer? _timer;

  @override
  void dispose() {
    _timer?.cancel();
    for (final c in [_email, _code, _password, _confirm]) {
      c.dispose();
    }
    super.dispose();
  }

  void _startResendTimer() {
    _timer?.cancel();
    setState(() => _resendIn = 60);
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

  Future<void> _sendCode({bool resend = false}) async {
    if (!resend && !_emailForm.currentState!.validate()) return;
    await _run(() async {
      await ref.read(repositoryProvider).forgotPassword(_email.text.trim());
      _startResendTimer();
      setState(() => _step = _Step.code);
      if (resend && mounted) showSnack(context, 'A new code has been sent');
    });
  }

  Future<void> _verifyCode() async {
    if (_code.text.trim().length != 6) {
      setState(() => _error = 'Enter the 6-digit code from your email');
      return;
    }
    await _run(() async {
      _resetToken = await ref.read(repositoryProvider).verifyResetCode(_email.text.trim(), _code.text.trim());
      setState(() => _step = _Step.password);
    });
  }

  Future<void> _setPassword() async {
    if (!_passwordForm.currentState!.validate()) return;
    await _run(() async {
      await ref.read(repositoryProvider).resetPassword(_resetToken!, _password.text, _confirm.text);
      setState(() => _step = _Step.done);
    });
  }

  Widget _button(String label, VoidCallback onPressed) => FilledButton(
        onPressed: _loading ? null : onPressed,
        child: _loading
            ? SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.4, color: context.c.onBrand))
            : Text(label),
      );

  @override
  Widget build(BuildContext context) {
    final (title, subtitle) = switch (_step) {
      _Step.email => ('Forgot password?', "Enter your account email and we'll send you a 6-digit code."),
      _Step.code => ('Check your email', 'We sent a 6-digit code to ${_email.text.trim()}. It expires in 15 minutes.'),
      _Step.password => ('Set a new password', 'Choose a strong password you haven\'t used here before.'),
      _Step.done => ('Password updated', 'You can now sign in with your new password.'),
    };
    return AuthLayout(
      title: title,
      subtitle: subtitle,
      children: [
        _Steps(current: _step.index.clamp(0, 2), done: _step == _Step.done),
        const SizedBox(height: 18),
        if (_error != null) ErrorBanner(_error!),
        ...switch (_step) {
          _Step.email => _emailStep(),
          _Step.code => _codeStep(),
          _Step.password => _passwordStep(),
          _Step.done => _doneStep(),
        },
        const SizedBox(height: 10),
        if (_step != _Step.done)
          Center(
            child: TextButton(onPressed: () => context.go('/login'), child: const Text('Back to sign in')),
          ),
      ],
    );
  }

  List<Widget> _emailStep() => [
        Form(
          key: _emailForm,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const FieldLabel('EMAIL'),
              TextFormField(
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                autofillHints: const [AutofillHints.email],
                autocorrect: false,
                textInputAction: TextInputAction.send,
                onFieldSubmitted: (_) => _sendCode(),
                validator: Validators.email,
                decoration: const InputDecoration(
                  hintText: 'you@example.com',
                  prefixIcon: Icon(Icons.mail_outline_rounded, size: 20),
                ),
              ),
              const SizedBox(height: 22),
              _button('Send code', _sendCode),
            ],
          ),
        ),
      ];

  List<Widget> _codeStep() => [
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
            if (v.length == 6) _verifyCode();
          },
        ),
        const SizedBox(height: 22),
        _button('Verify code', _verifyCode),
        const SizedBox(height: 6),
        Center(
          child: TextButton(
            onPressed: _resendIn > 0 || _loading ? null : () => _sendCode(resend: true),
            child: Text(_resendIn > 0 ? 'Resend code in ${_resendIn}s' : 'Resend code'),
          ),
        ),
        Text(
          "Didn't get it? Check spam or junk, and make sure the email is the one you registered with.",
          textAlign: TextAlign.center,
          style: TextStyle(color: context.c.muted, fontSize: 12),
        ),
      ];

  List<Widget> _passwordStep() => [
        Form(
          key: _passwordForm,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const FieldLabel('NEW PASSWORD'),
              PasswordField(
                controller: _password,
                hint: 'Create a strong password',
                autofillHints: const [AutofillHints.newPassword],
                validator: Validators.strongPassword,
                onChanged: (_) => setState(() {}),
              ),
              PasswordChecklist(Validators.passwordChecks(_password.text)),
              const SizedBox(height: 14),
              const FieldLabel('CONFIRM NEW PASSWORD'),
              PasswordField(
                controller: _confirm,
                hint: 'Re-enter password',
                textInputAction: TextInputAction.done,
                autofillHints: const [AutofillHints.newPassword],
                onSubmitted: (_) => _setPassword(),
                validator: (v) => v != _password.text ? 'Passwords do not match' : null,
              ),
              const SizedBox(height: 22),
              _button('Update password', _setPassword),
              const SizedBox(height: 8),
              Text(
                'For your security, this signs you out on all your devices.',
                textAlign: TextAlign.center,
                style: TextStyle(color: context.c.muted, fontSize: 12),
              ),
            ],
          ),
        ),
      ];

  List<Widget> _doneStep() => [
        Center(child: IconBubble(Icons.verified_rounded, size: 72, color: context.c.soft, iconColor: context.c.brand)),
        const SizedBox(height: 20),
        FilledButton(
          onPressed: () => context.go(Uri(path: '/login', queryParameters: {'email': _email.text.trim()}).toString()),
          child: const Text('Back to sign in'),
        ),
      ];
}

/// Three-dot progress indicator: Email · Code · New password.
class _Steps extends StatelessWidget {
  const _Steps({required this.current, required this.done});
  final int current;
  final bool done;

  @override
  Widget build(BuildContext context) {
    const labels = ['Email', 'Code', 'New password'];
    final c = context.c;
    return Row(
      children: [
        for (var i = 0; i < labels.length; i++) ...[
          if (i > 0)
            Expanded(
              child: Container(
                height: 2,
                margin: const EdgeInsets.only(bottom: 18),
                color: (done || i <= current) ? c.brand : c.border,
              ),
            ),
          Column(
            children: [
              CircleAvatar(
                radius: 13,
                backgroundColor: (done || i < current)
                    ? c.brand
                    : i == current
                        ? c.soft
                        : c.surfaceAlt,
                child: (done || i < current)
                    ? Icon(Icons.check_rounded, size: 15, color: c.onBrand)
                    : Text('${i + 1}',
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w700,
                          color: i == current ? c.brand : c.muted,
                        )),
              ),
              const SizedBox(height: 4),
              Text(labels[i], style: TextStyle(fontSize: 11, color: i == current && !done ? c.brand : c.muted)),
            ],
          ),
        ],
      ],
    );
  }
}
