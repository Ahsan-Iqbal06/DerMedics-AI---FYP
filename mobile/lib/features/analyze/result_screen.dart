import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/models.dart';
import '../../core/repository.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../care/care_screen.dart';

final analysisProvider =
    FutureProvider.autoDispose.family<Analysis, int>((ref, id) => ref.watch(repositoryProvider).analysis(id));

/// Loads an analysis by id (or uses the one passed from the upload screen) and shows the matching screen.
class AnalysisResultScreen extends ConsumerWidget {
  const AnalysisResultScreen({super.key, required this.id, this.initial});
  final int id;
  final Analysis? initial;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (initial != null) return _body(initial!);
    return ref.watch(analysisProvider(id)).when(
          loading: () => PageScaffold(showBack: true, children: [LoadingView()]),
          error: (e, _) => PageScaffold(
            showBack: true,
            children: [ErrorView(message: e.toString(), onRetry: () => ref.invalidate(analysisProvider(id)))],
          ),
          data: _body,
        );
  }

  Widget _body(Analysis a) => a.isConclusive ? ConclusiveResult(analysis: a) : InconclusiveResult(analysis: a);
}

class ConclusiveResult extends StatelessWidget {
  const ConclusiveResult({super.key, required this.analysis});
  final Analysis analysis;

  @override
  Widget build(BuildContext context) {
    final a = analysis;
    final d = a.description;
    return PageScaffold(
      showBack: true,
      children: [
        PageTitle('Your skin analysis'),
        Align(alignment: Alignment.centerLeft, child: StatusBadge('AI ANALYSIS')),
        SizedBox(height: 12),
        AppCard(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (a.imageUrl.isNotEmpty)
                    ClipRRect(
                      borderRadius: BorderRadius.circular(12),
                      child: AuthImage(
                        a.imageUrl,
                        width: 64,
                        height: 64,
                        fallback: IconBubble(Icons.image_outlined, size: 64),
                      ),
                    ),
                  SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(a.displayName ?? 'Unknown',
                            style: TextStyle(fontSize: 22, fontWeight: FontWeight.w800)),
                        SizedBox(height: 4),
                        Text(
                          '${a.isDemo ? 'Illustrative match' : 'Likely match'} • ${a.confidencePercent}%',
                          style: TextStyle(color: context.c.brand, fontWeight: FontWeight.w600, fontSize: 13),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              if (a.isDemo) ...[
                SizedBox(height: 12),
                Text(
                  'Example output only. A trained model is not yet connected, so this is not a real model '
                  'prediction or a diagnosis.',
                  style: TextStyle(color: context.c.muted, fontSize: 12, height: 1.4),
                ),
              ],
            ],
          ),
        ),
        SizedBox(height: 18),
        Row(
          children: [
            Expanded(
                child: Text('AI model confidence score', style: TextStyle(color: context.c.muted, fontSize: 12.5))),
            Text('${a.confidencePercent}%', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 12.5)),
          ],
        ),
        SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: LinearProgressIndicator(
            value: a.confidence,
            minHeight: 8,
            color: context.c.brand,
            backgroundColor: context.c.soft,
          ),
        ),
        if (a.topPredictions.length > 1) ...[
          SizedBox(height: 8),
          Text(
            'Other possibilities: ${a.topPredictions.skip(1).map((p) => '${p.displayName} ${(p.confidence * 100).round()}%').join(', ')}',
            style: TextStyle(color: context.c.muted, fontSize: 11.5),
          ),
        ],
        SectionHeader('About the detected condition',
            subtitle: 'AI-generated description and relevant care information'),
        if (d != null) ...[
          _InfoCard(icon: Icons.info_outline_rounded, title: 'About ${d.name.toLowerCase()}', body: d.overview),
          SizedBox(height: 10),
          _InfoCard(
            icon: Icons.check_rounded,
            title: 'Symptoms & precautions',
            bullets: [...d.symptoms, ...d.precautions.map((p) => 'Precaution: $p')],
            body: d.whenToSeeDoctor,
          ),
        ],
        SizedBox(height: 16),
        AppCard(
          color: context.c.soft.withValues(alpha: 0.6),
          borderColor: Colors.transparent,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('AI medicine suggestions',
                  style: TextStyle(color: context.c.brand, fontWeight: FontWeight.w700, fontSize: 13.5)),
              SizedBox(height: 4),
              Text(
                'Generated using the detected condition, its description and your region. Review with a clinician.',
                style: TextStyle(fontSize: 12.5, height: 1.4),
              ),
              SizedBox(height: 12),
              FilledButton(
                onPressed: () => context.push('/analyze/result/${a.id}/medicines', extra: a),
                child: Text('Review AI medicine suggestions'),
              ),
            ],
          ),
        ),
        if (a.dermatologists.isNotEmpty) ...[
          SectionHeader('Recommended dermatologists', subtitle: 'Matched to your region and this condition'),
          for (final doc in a.dermatologists.take(3)) ...[
            ProviderCard(doc, highlightCondition: a.predictedLabel),
            SizedBox(height: 10),
          ],
          TextButton(onPressed: () => context.go('/care'), child: Text('See all care options')),
        ],
        FootNote('For informational guidance only — not a medical diagnosis.'),
      ],
    );
  }
}

class InconclusiveResult extends StatelessWidget {
  const InconclusiveResult({super.key, required this.analysis});
  final Analysis analysis;

  String get _reason => switch (analysis.llmSource) {
        'too_dark' => 'The photo looks too dark.',
        'overexposed' => 'The photo looks overexposed.',
        'blurry' => 'The photo looks blurry or out of focus.',
        'unsupported_condition' => 'This looks like a condition the app does not cover yet.',
        _ => 'An image may be unclear, or a condition may not be supported.',
      };

  @override
  Widget build(BuildContext context) {
    return PageScaffold(
      showBack: true,
      children: [
        PageTitle("We couldn't find a\nreliable match", subtitle: _reason),
        Container(
          padding: EdgeInsets.all(18),
          decoration: BoxDecoration(color: context.c.amberBg, borderRadius: BorderRadius.circular(18)),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              CircleAvatar(
                radius: 18,
                backgroundColor: context.c.amberDot,
                child: Icon(Icons.priority_high_rounded, color: Colors.white, size: 20),
              ),
              SizedBox(height: 14),
              Text('No reliable prediction',
                  style: TextStyle(color: context.c.amberText, fontWeight: FontWeight.w700, fontSize: 15)),
              SizedBox(height: 4),
              Text("We won't show disease-specific medicine information for an uncertain result.",
                  style: TextStyle(fontSize: 12.5, height: 1.4)),
            ],
          ),
        ),
        SizedBox(height: 12),
        Align(alignment: Alignment.centerLeft, child: StatusBadge('NO MEDICINE SUGGESTIONS', tone: BadgeTone.amber)),
        SectionHeader('What to do next', subtitle: 'Prioritize your wellbeing'),
        AppCard(
          onTap: () => context.go('/analyze'),
          child: _NextStep(
            icon: Icons.center_focus_weak_rounded,
            title: 'Try a clearer photo',
            body: 'Use even lighting, focus on the affected area, and avoid filters.',
          ),
        ),
        SizedBox(height: 10),
        AppCard(
          child: _NextStep(
            icon: Icons.favorite_border_rounded,
            title: 'Speak with a dermatologist',
            body: 'A clinician can examine your skin and ask about symptoms and history.',
          ),
        ),
        SizedBox(height: 16),
        FilledButton(onPressed: () => context.go('/care'), child: Text('Find a dermatologist')),
        SizedBox(height: 8),
        if (!analysis.hasReport)
          OutlinedButton(
            style: OutlinedButton.styleFrom(minimumSize: Size.fromHeight(48)),
            onPressed: () => context.push('/analyze/result/${analysis.id}/subject', extra: analysis),
            child: Text('Save as report'),
          ),
        FootNote('For information only. Seek urgent care for severe symptoms.'),
      ],
    );
  }
}

class _NextStep extends StatelessWidget {
  const _NextStep({required this.icon, required this.title, required this.body});
  final IconData icon;
  final String title;
  final String body;

  @override
  Widget build(BuildContext context) => Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Icon(icon, color: context.c.brand, size: 18),
            SizedBox(width: 8),
            Text(title, style: TextStyle(fontWeight: FontWeight.w700)),
          ]),
          SizedBox(height: 6),
          Text(body, style: TextStyle(color: context.c.muted, fontSize: 12.5, height: 1.4)),
        ],
      );
}

class _InfoCard extends StatelessWidget {
  const _InfoCard({required this.icon, required this.title, required this.body, this.bullets = const []});
  final IconData icon;
  final String title;
  final String body;
  final List<String> bullets;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Icon(icon, size: 18, color: context.c.brand),
            SizedBox(width: 8),
            Expanded(child: Text(title, style: TextStyle(fontWeight: FontWeight.w700))),
          ]),
          SizedBox(height: 8),
          for (final b in bullets)
            Padding(
              padding: EdgeInsets.only(bottom: 4),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('•  ', style: TextStyle(color: context.c.brand)),
                  Expanded(child: Text(b, style: TextStyle(fontSize: 13, height: 1.4))),
                ],
              ),
            ),
          if (body.isNotEmpty)
            Padding(
              padding: EdgeInsets.only(top: bullets.isEmpty ? 0 : 6),
              child: Text(body, style: TextStyle(color: context.c.muted, fontSize: 13, height: 1.45)),
            ),
        ],
      ),
    );
  }
}
