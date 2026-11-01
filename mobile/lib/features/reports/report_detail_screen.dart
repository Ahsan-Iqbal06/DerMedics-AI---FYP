import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../core/api_client.dart';
import '../../core/models.dart';
import '../../core/repository.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../home/home_screen.dart';
import 'reports_screen.dart';

final reportProvider =
    FutureProvider.autoDispose.family<Report, int>((ref, id) => ref.watch(repositoryProvider).report(id));

class ReportDetailScreen extends ConsumerWidget {
  const ReportDetailScreen({super.key, required this.id});
  final int id;

  Future<void> _delete(BuildContext context, WidgetRef ref) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text('Delete report?'),
        content: Text('This permanently removes the report and its analysis from your account.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: Text('Cancel')),
          TextButton(
            style: TextButton.styleFrom(foregroundColor: context.c.danger),
            onPressed: () => Navigator.pop(ctx, true),
            child: Text('Delete'),
          ),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await ref.read(repositoryProvider).deleteReport(id);
      ref.invalidate(reportsProvider);
      ref.invalidate(dashboardProvider);
      if (context.mounted) {
        showSnack(context, 'Report deleted');
        context.pop();
      }
    } on ApiException catch (e) {
      if (context.mounted) showSnack(context, e.message);
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ref.watch(reportProvider(id)).when(
          loading: () => PageScaffold(showBack: true, children: [LoadingView()]),
          error: (e, _) => PageScaffold(
            showBack: true,
            children: [ErrorView(message: e.toString(), onRetry: () => ref.invalidate(reportProvider(id)))],
          ),
          data: (r) {
            final a = r.analysis;
            final created = r.createdAt == null ? '' : DateFormat('d MMM yyyy, h:mm a').format(r.createdAt!);
            return PageScaffold(
              showBack: true,
              children: [
                PageTitle(a.isConclusive ? a.displayName ?? 'Report' : 'Inconclusive result', subtitle: 'Report #${r.id} • $created'),
                AppCard(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(12),
                        child: AuthImage(
                          a.imageUrl,
                          width: 86,
                          height: 86,
                          fallback: IconBubble(Icons.image_outlined, size: 86),
                        ),
                      ),
                      SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            _kv(context, 'Person', r.subjectName),
                            _kv(context, 'Relationship', r.relationship),
                            if (r.subjectAge != null) _kv(context, 'Age', '${r.subjectAge}'),
                            _kv(context, 'Body area', a.bodyArea),
                            if (a.symptoms.isNotEmpty) _kv(context, 'Noticed', a.symptoms),
                            if (r.healthNotes.isNotEmpty) _kv(context, 'Notes', r.healthNotes),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                SizedBox(height: 12),
                if (a.isConclusive) ...[
                  AppCard(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [
                          StatusBadge('AI ANALYSIS'),
                          Spacer(),
                          Text('${a.confidencePercent}% confidence',
                              style: TextStyle(color: context.c.brand, fontWeight: FontWeight.w600, fontSize: 12.5)),
                        ]),
                        if (a.isDemo)
                          Padding(
                            padding: EdgeInsets.only(top: 8),
                            child: Text('Demo model output — illustrative only.',
                                style: TextStyle(color: context.c.amberText, fontSize: 12)),
                          ),
                        if (a.description != null) ...[
                          SizedBox(height: 10),
                          Text(a.description!.overview, style: TextStyle(fontSize: 13, height: 1.45)),
                        ],
                      ],
                    ),
                  ),
                  SizedBox(height: 10),
                  AppCard(
                    onTap: () => context.push('/analyze/result/${a.id}/medicines', extra: a),
                    child: Row(children: [
                      IconBubble(Icons.medication_outlined, size: 36),
                      SizedBox(width: 12),
                      Expanded(
                        child: Text('${a.medicines.length} medicine suggestions',
                            style: TextStyle(fontWeight: FontWeight.w600)),
                      ),
                      Icon(Icons.chevron_right_rounded, color: context.c.muted),
                    ]),
                  ),
                  SizedBox(height: 10),
                  AppCard(
                    onTap: () => context.push('/analyze/result/${a.id}', extra: a),
                    child: Row(children: [
                      IconBubble(Icons.article_outlined, size: 36),
                      SizedBox(width: 12),
                      Expanded(child: Text('Full analysis & dermatologists', style: TextStyle(fontWeight: FontWeight.w600))),
                      Icon(Icons.chevron_right_rounded, color: context.c.muted),
                    ]),
                  ),
                ] else
                  NoticeBox(
                    title: 'No reliable prediction',
                    body: 'No medicine suggestions are shown for uncertain results. '
                        'Try a clearer photo or speak with a dermatologist.',
                  ),
                SizedBox(height: 18),
                FilledButton.icon(
                  onPressed: () => downloadReportPdf(context, ref, r.id),
                  icon: Icon(Icons.download_rounded),
                  label: Text('Download PDF'),
                ),
                SizedBox(height: 8),
                TextButton.icon(
                  style: TextButton.styleFrom(foregroundColor: context.c.danger),
                  onPressed: () => _delete(context, ref),
                  icon: Icon(Icons.delete_outline_rounded),
                  label: Text('Delete report'),
                ),
                FootNote('AI findings are informational. Consult a clinician before treatment.'),
              ],
            );
          },
        );
  }

  Widget _kv(BuildContext context, String k, String v) => Padding(
        padding: EdgeInsets.only(bottom: 4),
        child: Text.rich(TextSpan(children: [
          TextSpan(text: '$k: ', style: TextStyle(color: context.c.muted, fontSize: 12.5)),
          TextSpan(text: v, style: TextStyle(fontSize: 12.5, fontWeight: FontWeight.w600)),
        ])),
      );
}
