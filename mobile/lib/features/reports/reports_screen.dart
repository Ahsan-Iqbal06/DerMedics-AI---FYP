import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/api_client.dart';
import '../../core/download/save_file.dart';
import '../../core/models.dart';
import '../../core/repository.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';

typedef ReportQuery = ({String filter, String q});

final reportsProvider = FutureProvider.autoDispose.family<List<ReportSummary>, ReportQuery>(
  (ref, query) => ref.watch(repositoryProvider).reports(filter: query.filter, query: query.q),
);

Future<void> downloadReportPdf(BuildContext context, WidgetRef ref, int reportId) async {
  showSnack(context, 'Preparing PDF…');
  try {
    final bytes = await ref.read(repositoryProvider).reportPdf(reportId);
    final savedTo = await saveAndOpenFile(bytes, 'DerMedics-Report-DM-${reportId.toString().padLeft(6, '0')}.pdf');
    if (context.mounted) showSnack(context, 'PDF saved to $savedTo');
  } on ApiException catch (e) {
    if (context.mounted) showSnack(context, e.message);
  } catch (_) {
    if (context.mounted) showSnack(context, 'Could not save the PDF on this device.');
  }
}

class ReportsScreen extends ConsumerStatefulWidget {
  const ReportsScreen({super.key});

  @override
  ConsumerState<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportsScreenState extends ConsumerState<ReportsScreen> {
  final _search = TextEditingController();
  Timer? _debounce;
  String _filter = 'all';
  String _q = '';

  @override
  void dispose() {
    _debounce?.cancel();
    _search.dispose();
    super.dispose();
  }

  void _onSearch(String v) {
    _debounce?.cancel();
    _debounce = Timer(Duration(milliseconds: 350), () => setState(() => _q = v.trim()));
  }

  @override
  Widget build(BuildContext context) {
    final query = (filter: _filter, q: _q);
    final reports = ref.watch(reportsProvider(query));
    final count = reports.whenOrNull(data: (r) => r.length);

    return PageScaffold(
      onRefresh: () => ref.refresh(reportsProvider(query).future),
      children: [
        PageTitle('Your reports', subtitle: 'Review saved skin analyses and reports for yourself or others.'),
        Container(
          padding: EdgeInsets.all(18),
          decoration: heroDecoration(context, radius: 18),
          child: Row(
            children: [
              Text(count == null ? '--' : count.toString().padLeft(2, '0'),
                  style: TextStyle(color: context.c.onDeep, fontSize: 28, fontWeight: FontWeight.w800)),
              SizedBox(width: 12),
              Expanded(
                child: Text('Reports saved', style: TextStyle(color: context.c.onDeep, fontWeight: FontWeight.w600)),
              ),
              Text('Patient-owned report history',
                  style: TextStyle(color: context.c.onDeep.withValues(alpha: 0.75), fontSize: 11.5)),
            ],
          ),
        ),
        SizedBox(height: 14),
        TextField(
          controller: _search,
          onChanged: _onSearch,
          textInputAction: TextInputAction.search,
          decoration: InputDecoration(
            hintText: 'Search reports',
            prefixIcon: Icon(Icons.search_rounded, color: context.c.muted),
          ),
        ),
        SizedBox(height: 12),
        Align(
          alignment: Alignment.centerLeft,
          child: Segmented<String>(
            options: {'all': 'All', 'ai': 'AI', 'inconclusive': 'Inconclusive'},
            value: _filter,
            onChanged: (v) => setState(() => _filter = v),
          ),
        ),
        SectionHeader('RECENT'),
        reports.when(
          loading: () => LoadingView(),
          error: (e, _) => ErrorView(message: e.toString(), onRetry: () => ref.invalidate(reportsProvider(query))),
          data: (items) => items.isEmpty
              ? AppCard(
                  child: Column(
                    children: [
                      IconBubble(Icons.description_outlined),
                      SizedBox(height: 10),
                      Text(_q.isEmpty && _filter == 'all' ? 'No reports yet' : 'No reports match',
                          style: TextStyle(fontWeight: FontWeight.w700)),
                      SizedBox(height: 4),
                      Text('Analyze a skin photo and generate a report to see it here.',
                          textAlign: TextAlign.center, style: TextStyle(color: context.c.muted, fontSize: 12.5)),
                      SizedBox(height: 10),
                      TextButton(onPressed: () => context.go('/analyze'), child: Text('Start skin analysis')),
                    ],
                  ),
                )
              : Column(
                  children: [
                    for (final r in items) ...[
                      _ReportCard(report: r),
                      SizedBox(height: 10),
                    ],
                  ],
                ),
        ),
        SizedBox(height: 6),
        NoticeBox(
          tone: BadgeTone.neutral,
          title: 'Your privacy matters',
          body: 'Reports are stored under your account on the DerMedics server and are visible only to you.',
        ),
      ],
    );
  }
}

class _ReportCard extends ConsumerWidget {
  const _ReportCard({required this.report});
  final ReportSummary report;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final conclusive = report.status == 'ai';
    return AppCard(
      onTap: () => context.push('/reports/${report.id}'),
      child: Column(
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              IconBubble(
                conclusive ? Icons.center_focus_strong_outlined : Icons.help_outline_rounded,
                color: conclusive ? context.c.soft : context.c.amberBg,
                iconColor: conclusive ? context.c.brand : context.c.amberText,
              ),
              SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(report.title, style: TextStyle(fontWeight: FontWeight.w700)),
                    SizedBox(height: 3),
                    Text('${report.subjectName} • ${report.subtitle}',
                        style: TextStyle(color: context.c.muted, fontSize: 12)),
                  ],
                ),
              ),
              Text(relativeDay(report.createdAt), style: TextStyle(color: context.c.muted, fontSize: 12)),
            ],
          ),
          SizedBox(height: 10),
          Row(
            children: [
              TextButton(onPressed: () => context.push('/reports/${report.id}'), child: Text('Open report')),
              Spacer(),
              TextButton.icon(
                onPressed: () => downloadReportPdf(context, ref, report.id),
                icon: Icon(Icons.download_rounded, size: 18),
                label: Text('Download PDF'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
