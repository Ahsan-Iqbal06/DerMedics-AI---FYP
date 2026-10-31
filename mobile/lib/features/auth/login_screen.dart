import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/theme.dart';
import 'auth_controller.dart';
import 'auth_widgets.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key, this.initialEmail});

  /// Pre-filled after a password reset.
  final String? initialEmail;

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _form = GlobalKey<FormState>();
  late final _email = TextEditingController(text: widget.initialEmail ?? '');
  final _password = TextEditingController();
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _error = null);
    if (!_form.currentState!.validate()) return;
    setState(() => _loading = true);
    try {
      await ref.read(authControllerProvider.notifier).login(_email.text, _password.text);
      // Router redirect takes the user to Home.
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AuthLayout(
      title: 'Welcome back.',
      subtitle: 'Sign in to continue your skin-health journey.',
      children: [
        Form(
          key: _form,
          child: AutofillGroup(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (_error != null) ErrorBanner(_error!),
                FieldLabel('EMAIL'),
                TextFormField(
                  controller: _email,
                  keyboardType: TextInputType.emailAddress,
                  textInputAction: TextInputAction.next,
                  autofillHints: [AutofillHints.email],
                  autocorrect: false,
                  validator: Validators.email,
                  decoration: InputDecoration(
                    hintText: 'you@example.com',
                    prefixIcon: Icon(Icons.mail_outline_rounded, color: context.c.muted, size: 20),
                  ),
                ),
                SizedBox(height: 16),
                FieldLabel('PASSWORD'),
                PasswordField(
                  controller: _password,
                  textInputAction: TextInputAction.done,
                  autofillHints: [AutofillHints.password],
                  onSubmitted: (_) => _submit(),
                  validator: (v) => (v == null || v.isEmpty) ? 'Enter your password' : null,
                ),
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton(
                    onPressed: () => context.go(
                      Uri(path: '/forgot-password', queryParameters: {
                        if (_email.text.trim().isNotEmpty) 'email': _email.text.trim(),
                      }).toString(),
                    ),
                    child: Text('Forgot password?'),
                  ),
                ),
                SizedBox(height: 8),
                FilledButton(
                  onPressed: _loading ? null : _submit,
                  child: _loading
                      ? SizedBox(
                          width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.4, color: context.c.onBrand))
                      : Text('Sign in'),
                ),
                SizedBox(height: 18),
                Wrap(
                  alignment: WrapAlignment.center,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text("Don't have an account?", style: TextStyle(color: context.c.muted)),
                    TextButton(onPressed: () => context.go('/register'), child: Text('Create account')),
                  ],
                ),
                SizedBox(height: 8),
                Text(
                  'DerMedics AI provides informational skin-health support, not a diagnosis.',
                  textAlign: TextAlign.center,
                  style: TextStyle(color: context.c.muted, fontSize: 11.5),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
