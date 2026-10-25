import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/models.dart';
import '../../core/repository.dart';
import '../../core/theme.dart';
import '../../core/widgets.dart';
import '../auth/auth_controller.dart';

final dashboardProvider = FutureProvider.autoDispose<Dashboard>((ref) => ref.watch(repositoryProvider).dashboard());

String greeting([DateTime? now]) {
  final h = (now ?? DateTime.now()).hour;
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authControllerProvider).user;
    final dash = ref.watch(dashboardProvider);
    String two(int n) => n.toString().padLeft(2, '0');

    return PageScaffold(
      onRefresh: () => ref.refresh(dashboardProvider.future),
      children: [
        PageTitle('${greeting()}, ${user?.firstName ?? ''}', subtitle: 'Your skin health, one small step at a time.'),
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
                    style: TextStyle(color: context.c.accent, fontSize: 10.5, fontWeight: FontWeight.w700, letterSpacing: 0.6)),
              ),
              SizedBox(height: 14),
              Text('Know your skin.\nFind your next step.',
                  style: TextStyle(color: context.c.onDeep, fontSize: 25, fontWeight: FontWeight.w800, height: 1.2)),
              SizedBox(height: 8),
              Text('Learn about skin conditions and find professional care with confidence.',
                  style: TextStyle(color: context.c.onDeep.withValues(alpha: 0.82), fontSize: 13.5, height: 1.4)),
              SizedBox(height: 18),
              FilledButton(
                style: FilledButton.styleFrom(backgroundColor: context.c.onDeep, foregroundColor: context.c.deep),
                onPressed: () => context.go('/analyze'),
                child: Text('Start skin analysis'),
              ),
            ],
          ),
        ),
        SizedBox(height: 14),
        Row(
          children: [
            _StatTile(
              value: dash.whenOrNull(data: (d) => two(d.analysesCount)) ?? '--',
              label: 'Analyses',
              onTap: () => context.go('/reports'),
            ),
            SizedBox(width: 10),
            _StatTile(
              value: dash.whenOrNull(data: (d) => two(d.reportsCount)) ?? '--',
              label: 'Reports',
              onTap: () => context.go('/reports'),
            ),
            SizedBox(width: 10),
            _StatTile(value: 'Nearby', label: 'Care options', onTap: () => context.go('/care')),
          ],
        ),
        SectionHeader(
          'Recent activity',
          trailing: TextButton(onPressed: () => context.go('/reports'), child: Text('View all')),
        ),
        dash.when(
          loading: () => LoadingView(),
          error: (e, _) => ErrorView(message: e.toString(), onRetry: () => ref.invalidate(dashboardProvider)),
          data: (d) => d.recentActivity.isEmpty
              ? AppCard(
                  child: Text('No activity yet. Start your first skin analysis to see it here.',
                      style: TextStyle(color: context.c.muted, fontSize: 13)),
                )
              : AppCard(
                  padding: EdgeInsets.symmetric(vertical: 4),
                  child: Column(
                    children: [
                      for (final (i, a) in d.recentActivity.indexed) ...[
                        if (i > 0) Divider(indent: 16, endIndent: 16),
                        ListTile(
                          leading: IconBubble(
                            a.kind == 'report' ? Icons.picture_as_pdf_outlined : Icons.center_focus_strong_outlined,
                            size: 36,
                          ),
                          title: Text(a.title, style: TextStyle(fontSize: 14, fontWeight: FontWeight.w600)),
                          trailing: Text(relativeDay(a.createdAt),
                              style: TextStyle(color: context.c.muted, fontSize: 12)),
                          onTap: () => a.kind == 'report'
                              ? context.push('/reports/${a.refId}')
                              : context.push('/analyze/result/${a.refId}'),
                        ),
                      ],
                    ],
                  ),
                ),
        ),
        SizedBox(height: 16),
        NoticeBox(
          title: 'A gentle reminder',
          body: 'This app provides informational skin-health support, not a diagnosis. '
              'Seek urgent care for severe or rapidly spreading symptoms.',
        ),
      ],
    );
  }
}

class _StatTile extends StatelessWidget {
  const _StatTile({required this.value, required this.label, this.onTap});
  final String value;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: AppCard(
        onTap: onTap,
        padding: EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(value, style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800, color: context.c.brand)),
            SizedBox(height: 2),
            Text(label, style: TextStyle(color: context.c.muted, fontSize: 12)),
          ],
        ),
      ),
    );
  }
}
