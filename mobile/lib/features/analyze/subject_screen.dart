import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/models.dart';
import '../../core/repository.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../auth/auth_widgets.dart';
import '../home/home_screen.dart';
import '../reports/reports_screen.dart';

const relationships = ['Sibling', 'Parent', 'Child', 'Spouse', 'Friend', 'Relative', 'Other'];

/// "Who is this scan for?" — labels the analysis and saves it as a report.
class SubjectScreen extends ConsumerStatefulWidget {
  const SubjectScreen({super.key, required this.analysis});
  final Analysis analysis;

  @override
  ConsumerState<SubjectScreen> createState() => _SubjectScreenState();
}

class _SubjectScreenState extends ConsumerState<SubjectScreen> {
  final _form = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _age = TextEditingController();
  final _notes = TextEditingController();
  bool _myself = true;
  String _relationship = relationships.first;
  bool _loading = false;

  @override
  void dispose() {
    _name.dispose();
    _age.dispose();
    _notes.dispose();
    super.dispose();
  }

  Future<void> _generate() async {
    if (!_form.currentState!.validate()) return;
    setState(() => _loading = true);
    try {
      final report = await ref.read(repositoryProvider).createReport(
            analysisId: widget.analysis.id,
            myself: _myself,
            name: _name.text.trim(),
            age: int.tryParse(_age.text.trim()),
            relationship: _relationship,
            notes: _notes.text.trim(),
          );
      ref.invalidate(dashboardProvider);
      ref.invalidate(reportsProvider);
      if (!mounted) return;
      showSnack(context, 'Report saved');
      context.go('/reports');
      context.push('/reports/${report.id}');
    } on ApiException catch (e) {
      if (mounted) showSnack(context, e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return PageScaffold(
      showBack: true,
      children: [
        PageTitle('Who is this scan for?',
            subtitle: 'Choose the person in the photo. You can edit their details before saving the report.'),
        _ChoiceCard(
          title: 'Myself',
          body: 'Use my patient profile for this report.',
          selected: _myself,
          onTap: () => setState(() => _myself = true),
        ),
        SizedBox(height: 10),
        _ChoiceCard(
          title: 'Someone else',
          body: 'Sibling, parent, friend or another person.',
          selected: !_myself,
          onTap: () => setState(() => _myself = false),
        ),
        Form(
          key: _form,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (!_myself) ...[
                SectionHeader("Person's details", subtitle: 'These details label this report only.'),
                FieldLabel('FULL NAME *'),
                TextFormField(
                  controller: _name,
                  textCapitalization: TextCapitalization.words,
                  decoration: InputDecoration(hintText: "Enter person's full name"),
                  validator: (v) => (v == null || v.trim().length < 2) ? "Enter the person's full name" : null,
                ),
                SizedBox(height: 12),
                FieldLabel('RELATIONSHIP *'),
                DropdownButtonFormField<String>(
                  initialValue: _relationship,
                  items: [for (final r in relationships) DropdownMenuItem(value: r, child: Text(r))],
                  onChanged: (v) => setState(() => _relationship = v ?? _relationship),
                ),
                SizedBox(height: 12),
              ] else
                SizedBox(height: 18),
              FieldLabel('AGE (OPTIONAL)'),
              TextFormField(
                controller: _age,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(hintText: 'Enter age'),
                validator: (v) {
                  if (v == null || v.trim().isEmpty) return null;
                  final n = int.tryParse(v.trim());
                  return (n == null || n < 0 || n > 130) ? 'Enter a valid age' : null;
                },
              ),
              SizedBox(height: 12),
              FieldLabel('RELEVANT HEALTH NOTES (OPTIONAL)'),
              TextFormField(
                controller: _notes,
                maxLines: 2,
                maxLength: 1000,
                decoration: InputDecoration(hintText: 'Allergies or current skin treatments'),
              ),
            ],
          ),
        ),
        NoticeBox(
          tone: BadgeTone.mint,
          title: 'Your account stays yours',
          body: "This report is saved under your account and labeled with the person's details above.",
        ),
        SizedBox(height: 16),
        FilledButton(
          onPressed: _loading ? null : _generate,
          child: _loading
              ? SizedBox(width: 22, height: 22, child: CircularProgressIndicator(strokeWidth: 2.4, color: context.c.onBrand))
              : Text('Generate report'),
        ),
        FootNote('AI findings are informational. Consult a clinician before treatment.'),
      ],
    );
  }
}

class _ChoiceCard extends StatelessWidget {
  const _ChoiceCard({required this.title, required this.body, required this.selected, required this.onTap});
  final String title;
  final String body;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      selected: selected,
      button: true,
      child: AppCard(
        onTap: onTap,
        color: selected ? context.c.soft.withValues(alpha: 0.6) : context.c.surface,
        borderColor: selected ? context.c.brand : context.c.border,
        child: Row(
          children: [
            Icon(selected ? Icons.radio_button_checked : Icons.radio_button_off,
                color: selected ? context.c.brand : context.c.muted),
            SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: TextStyle(fontWeight: FontWeight.w700)),
                  SizedBox(height: 2),
                  Text(body, style: TextStyle(color: context.c.muted, fontSize: 12.5)),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
