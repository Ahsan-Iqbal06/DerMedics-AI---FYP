import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/theme.dart';
import 'auth_controller.dart';
import 'auth_widgets.dart';

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _confirm = TextEditingController();
  final _country = TextEditingController(text: 'Pakistan');
  final _city = TextEditingController();
  bool _acceptTerms = false;
  bool _termsError = false;
  bool _loading = false;
  String? _error;
  late final _termsTap = TapGestureRecognizer()..onTap = _showTerms;

  @override
  void dispose() {
    _termsTap.dispose();
    for (final c in [_name, _email, _password, _confirm, _country, _city]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() {
      _error = null;
      _termsError = !_acceptTerms;
    });
    final valid = _form.currentState!.validate();
    if (!valid || !_acceptTerms) return;
    setState(() => _loading = true);
    try {
      await ref.read(authControllerProvider.notifier).register(
            fullName: _name.text,
            email: _email.text,
            password: _password.text,
            confirmPassword: _confirm.text,
            country: _country.text,
            city: _city.text,
            acceptTerms: _acceptTerms,
          );
    } on ApiException catch (e) {
      setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  void _showTerms() {
    showModalBottomSheet<void>(
      context: context,
      showDragHandle: true,
      builder: (_) => Padding(
        padding: EdgeInsets.fromLTRB(22, 0, 22, 28),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Terms & privacy', style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
            SizedBox(height: 12),
            Text(
              '• DerMedics AI gives informational skin-health support. It is not a diagnosis or prescription.\n'
              '• Photos and reports are stored under your account and are visible only to you.\n'
              '• Your region is used only to localise information and nearby care.\n'
              '• Location is requested only when you tap "Use my device location".\n'
              '• Seek urgent care for severe or rapidly spreading symptoms.',
              style: TextStyle(height: 1.6, fontSize: 13.5),
            ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AuthLayout(
      title: 'Create your account.',
      subtitle: 'Save analyses and reports securely, for yourself or your family.',
      children: [
        Form(
          key: _form,
          autovalidateMode: AutovalidateMode.onUnfocus,
          child: AutofillGroup(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (_error != null) ErrorBanner(_error!),
                FieldLabel('FULL NAME *'),
                TextFormField(
                  controller: _name,
                  textCapitalization: TextCapitalization.words,
                  textInputAction: TextInputAction.next,
                  autofillHints: [AutofillHints.name],
                  validator: Validators.name,
                  decoration: InputDecoration(
                    hintText: 'Enter your full name',
                    prefixIcon: Icon(Icons.person_outline_rounded, color: context.c.muted, size: 20),
                  ),
                ),
                SizedBox(height: 14),
                FieldLabel('EMAIL *'),
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
                SizedBox(height: 14),
                FieldLabel('PASSWORD *'),
                PasswordField(
                  controller: _password,
                  hint: 'Create a strong password',
                  autofillHints: [AutofillHints.newPassword],
                  validator: Validators.strongPassword,
                  onChanged: (_) => setState(() {}),
                ),
                PasswordChecklist(Validators.passwordChecks(_password.text)),
                SizedBox(height: 14),
                FieldLabel('CONFIRM PASSWORD *'),
                PasswordField(
                  controller: _confirm,
                  hint: 'Re-enter password',
                  autofillHints: [AutofillHints.newPassword],
                  validator: (v) => v != _password.text ? 'Passwords do not match' : null,
                ),
                SizedBox(height: 14),
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          FieldLabel('COUNTRY'),
                          TextFormField(
                            controller: _country,
                            textInputAction: TextInputAction.next,
                            autofillHints: [AutofillHints.countryName],
                            decoration: InputDecoration(hintText: 'Country'),
                          ),
                        ],
                      ),
                    ),
                    SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          FieldLabel('CITY / AREA'),
                          TextFormField(
                            controller: _city,
                            textInputAction: TextInputAction.done,
                            autofillHints: [AutofillHints.addressCity],
                            decoration: InputDecoration(hintText: 'e.g. Abbottabad'),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
                SizedBox(height: 14),
                Container(
                  padding: EdgeInsets.fromLTRB(4, 4, 12, 4),
                  decoration: BoxDecoration(
                    color: context.c.surface,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: _termsError ? context.c.danger : context.c.border),
                  ),
                  child: Row(
                    children: [
                      Checkbox(
                        value: _acceptTerms,
                        onChanged: (v) => setState(() {
                          _acceptTerms = v ?? false;
                          if (_acceptTerms) _termsError = false;
                        }),
                      ),
                      Expanded(
                        child: Text.rich(
                          TextSpan(
                            style: TextStyle(fontSize: 12.5, color: context.c.text, height: 1.4),
                            children: [
                              TextSpan(text: 'I agree to the '),
                              TextSpan(
                                text: 'terms & privacy notice',
                                style: TextStyle(color: context.c.brand, fontWeight: FontWeight.w600),
                                recognizer: _termsTap,
                              ),
                              TextSpan(text: ' and understand this app is informational, not a diagnosis.'),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                if (_termsError)
                  Padding(
                    padding: EdgeInsets.only(top: 6, left: 4),
                    child: Text('Please accept to continue',
                        style: TextStyle(color: context.c.danger, fontSize: 12)),
                  ),
                SizedBox(height: 22),
                FilledButton(
                  onPressed: _loading ? null : _submit,
                  child: _loading
                      ? SizedBox(
                          width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.4, color: context.c.onBrand))
                      : Text('Create account'),
                ),
                SizedBox(height: 14),
                Wrap(
                  alignment: WrapAlignment.center,
                  crossAxisAlignment: WrapCrossAlignment.center,
                  children: [
                    Text('Already have an account?', style: TextStyle(color: context.c.muted)),
                    TextButton(onPressed: () => context.go('/login'), child: Text('Sign in')),
                  ],
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
