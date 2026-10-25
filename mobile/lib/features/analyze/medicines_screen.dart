import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/models.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';

class MedicinesScreen extends StatelessWidget {
  const MedicinesScreen({super.key, required this.analysis});
  final Analysis analysis;

  @override
  Widget build(BuildContext context) {
    final a = analysis;
    final verified = !a.isDemo && a.llmSource == 'llm';
    return PageScaffold(
      showBack: true,
      children: [
        PageTitle('AI medicine suggestions',
            subtitle: 'Condition-specific information based on your analysis and region.'),
        AppCard(
          color: context.c.soft.withValues(alpha: 0.6),
          borderColor: Colors.transparent,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('Based on your AI analysis: ${a.displayName}',
                  style: TextStyle(color: context.c.brand, fontWeight: FontWeight.w700, fontSize: 13.5)),
              SizedBox(height: 4),
              Text(
                'Suggestions use the detected condition and generated description, with regional context. '
                'Live results should use validated medical sources.',
                style: TextStyle(fontSize: 12.5, height: 1.4),
              ),
            ],
          ),
        ),
        SizedBox(height: 12),
        Align(
          alignment: Alignment.centerLeft,
          child: StatusBadge('REGION: ${a.region.toUpperCase()} • VERIFY LOCAL AVAILABILITY', tone: BadgeTone.amber),
        ),
        SectionHeader('Suggestions for the detected condition'),
        if (a.medicines.isEmpty)
          AppCard(
            child: Text('No medicine suggestions are available for this result.',
                style: TextStyle(color: context.c.muted)),
          ),
        for (final m in a.medicines) ...[
          AppCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('＋ ', style: TextStyle(color: context.c.brand, fontWeight: FontWeight.w700)),
                    Expanded(child: Text(m.name, style: TextStyle(fontWeight: FontWeight.w700))),
                  ],
                ),
                SizedBox(height: 6),
                if (m.usageNote.isNotEmpty)
                  Text(m.usageNote, style: TextStyle(color: context.c.muted, fontSize: 12.5, height: 1.4)),
                if (m.caution.isNotEmpty)
                  Padding(
                    padding: EdgeInsets.only(top: 4),
                    child: Text('Caution: ${m.caution}',
                        style: TextStyle(color: context.c.muted, fontSize: 12.5, height: 1.4)),
                  ),
                SizedBox(height: 10),
                Wrap(
                  spacing: 6,
                  runSpacing: 6,
                  children: [
                    if (m.type.isNotEmpty) StatusBadge(m.type.toUpperCase(), tone: BadgeTone.neutral),
                    if (m.prescriptionRequired) StatusBadge('PRESCRIPTION ONLY', tone: BadgeTone.danger),
                    StatusBadge(verified ? 'AI GENERATED • CONFIRM WITH CLINICIAN' : 'REFERENCE • NOT VERIFIED'),
                  ],
                ),
              ],
            ),
          ),
          SizedBox(height: 10),
        ],
        SizedBox(height: 6),
        NoticeBox(
          title: 'Safety first — no prescriptions',
          body: 'Confirm suitability, side effects and local availability with a pharmacist or dermatologist.',
        ),
        SizedBox(height: 16),
        FilledButton(
          onPressed: a.hasReport
              ? () => context.go('/reports')
              : () => context.push('/analyze/result/${a.id}/subject', extra: a),
          child: Text(a.hasReport ? 'View saved reports' : 'Continue to report details'),
        ),
      ],
    );
  }
}
