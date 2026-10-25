import 'package:flutter/material.dart';

import '../../core/config.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import 'server_settings.dart';

/// Shared layout for the login and registration screens.
class AuthLayout extends StatelessWidget {
  const AuthLayout({super.key, required this.title, required this.subtitle, required this.children});
  final String title;
  final String subtitle;
  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: BoxConstraints(maxWidth: 460),
            child: ListView(
              padding: EdgeInsets.fromLTRB(22, 20, 22, 28),
              children: [
                Row(
                  children: [
                    LogoMark(size: 38),
                    SizedBox(width: 10),
                    GlassWordmark(),
                    Spacer(),
                    ThemeToggleButton(),
                  ],
                ),
                SizedBox(height: 28),
                Container(
                  padding: EdgeInsets.all(20),
                  decoration: heroDecoration(context),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: EdgeInsets.symmetric(horizontal: 10, vertical: 5),
                        decoration: BoxDecoration(
                          color: context.c.onDeep.withValues(alpha: 0.14),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text('YOUR SKIN, UNDERSTOOD',
                            style: TextStyle(
                                color: context.c.accent, fontSize: 10.5, fontWeight: FontWeight.w700, letterSpacing: 0.6)),
                      ),
                      SizedBox(height: 12),
                      Text(title,
                          style: TextStyle(color: context.c.onDeep, fontSize: 26, fontWeight: FontWeight.w800, height: 1.15)),
                      SizedBox(height: 6),
                      Text(subtitle, style: TextStyle(color: context.c.onDeep.withValues(alpha: 0.8), fontSize: 13.5, height: 1.4)),
                    ],
                  ),
                ),
                SizedBox(height: 22),
                ...children,
                const SizedBox(height: 6),
                // Rebuilds itself after the sheet closes so the label shows the new address.
                StatefulBuilder(
                  builder: (context, setState) => Center(
                    child: TextButton.icon(
                      style: TextButton.styleFrom(foregroundColor: context.c.muted),
                      onPressed: () async {
                        await showServerSettings(context);
                        setState(() {});
                      },
                      icon: const Icon(Icons.dns_outlined, size: 16),
                      label: Text('Server: ${AppConfig.baseUrl.replaceFirst(RegExp(r'^https?://'), '')}',
                          style: const TextStyle(fontSize: 12)),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class FieldLabel extends StatelessWidget {
  const FieldLabel(this.text, {super.key});
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: EdgeInsets.only(bottom: 6, left: 2),
        child: Text(text,
            style: TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: context.c.muted, letterSpacing: 0.6)),
      );
}

class PasswordField extends StatefulWidget {
  const PasswordField({
    super.key,
    required this.controller,
    this.hint = 'Enter password',
    this.validator,
    this.onChanged,
    this.textInputAction = TextInputAction.next,
    this.onSubmitted,
    this.autofillHints,
  });

  final TextEditingController controller;
  final String hint;
  final FormFieldValidator<String>? validator;
  final ValueChanged<String>? onChanged;
  final TextInputAction textInputAction;
  final ValueChanged<String>? onSubmitted;
  final Iterable<String>? autofillHints;

  @override
  State<PasswordField> createState() => _PasswordFieldState();
}

class _PasswordFieldState extends State<PasswordField> {
  bool _obscure = true;

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: widget.controller,
      obscureText: _obscure,
      validator: widget.validator,
      onChanged: widget.onChanged,
      textInputAction: widget.textInputAction,
      onFieldSubmitted: widget.onSubmitted,
      autofillHints: widget.autofillHints,
      autocorrect: false,
      enableSuggestions: false,
      decoration: InputDecoration(
        hintText: widget.hint,
        prefixIcon: Icon(Icons.lock_outline_rounded, color: context.c.muted, size: 20),
        suffixIcon: IconButton(
          tooltip: _obscure ? 'Show password' : 'Hide password',
          icon: Icon(_obscure ? Icons.visibility_outlined : Icons.visibility_off_outlined, color: context.c.muted, size: 20),
          onPressed: () => setState(() => _obscure = !_obscure),
        ),
      ),
    );
  }
}

class PasswordChecklist extends StatelessWidget {
  const PasswordChecklist(this.checks, {super.key});
  final List<(String, bool)> checks;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(top: 8),
      child: Wrap(
        spacing: 6,
        runSpacing: 6,
        children: [
          for (final (label, ok) in checks)
            Container(
              padding: EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: ok ? context.c.soft : context.c.canvas,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: ok ? context.c.soft : context.c.border),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(ok ? Icons.check_rounded : Icons.circle_outlined, size: 12, color: ok ? context.c.brand : context.c.muted),
                  SizedBox(width: 4),
                  Text(label, style: TextStyle(fontSize: 11, color: ok ? context.c.brand : context.c.muted)),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

class ErrorBanner extends StatelessWidget {
  const ErrorBanner(this.message, {super.key});
  final String message;

  @override
  Widget build(BuildContext context) => Container(
        margin: EdgeInsets.only(bottom: 14),
        padding: EdgeInsets.all(12),
        decoration: BoxDecoration(color: context.c.dangerBg, borderRadius: BorderRadius.circular(12)),
        child: Row(
          children: [
            Icon(Icons.error_outline_rounded, color: context.c.danger, size: 18),
            SizedBox(width: 8),
            Expanded(child: Text(message, style: TextStyle(color: context.c.danger, fontSize: 13))),
          ],
        ),
      );
}
