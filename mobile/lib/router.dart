import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import 'core/models.dart';
import 'core/theme.dart';
import 'features/analyze/medicines_screen.dart';
import 'features/analyze/result_screen.dart';
import 'features/analyze/subject_screen.dart';
import 'features/analyze/upload_screen.dart';
import 'features/auth/auth_controller.dart';
import 'features/auth/login_screen.dart';
import 'features/auth/register_screen.dart';
import 'features/auth/splash_screen.dart';
import 'features/care/care_screen.dart';
import 'features/home/home_screen.dart';
import 'features/profile/profile_screen.dart';
import 'features/reports/report_detail_screen.dart';
import 'features/reports/reports_screen.dart';

final _rootKey = GlobalKey<NavigatorState>();

final routerProvider = Provider<GoRouter>((ref) {
  final authChanges = ValueNotifier(ref.read(authControllerProvider).status);
  ref.listen(authControllerProvider, (_, next) => authChanges.value = next.status);
  ref.onDispose(authChanges.dispose);

  return GoRouter(
    navigatorKey: _rootKey,
    initialLocation: '/home',
    refreshListenable: authChanges,
    redirect: (context, state) {
      final status = ref.read(authControllerProvider).status;
      final loc = state.matchedLocation;
      final onAuthPage = loc == '/login' || loc == '/register';
      // Remember where the user was heading so a deep link survives the splash/login check.
      final from = state.uri.queryParameters['from'];
      switch (status) {
        case AuthStatus.unknown:
          return loc == '/splash' ? null : Uri(path: '/splash', queryParameters: {'from': state.uri.toString()}).toString();
        case AuthStatus.unauthenticated:
          if (onAuthPage) return null;
          return Uri(path: '/login', queryParameters: {'from': ?from}).toString();
        case AuthStatus.authenticated:
          if (onAuthPage || loc == '/splash') return (from != null && from.startsWith('/') && !from.startsWith('/splash')) ? from : '/home';
          return null;
      }
    },
    routes: [
      GoRoute(path: '/splash', builder: (_, _) => SplashScreen()),
      GoRoute(path: '/login', builder: (_, _) => LoginScreen()),
      GoRoute(path: '/register', builder: (_, _) => RegisterScreen()),
      GoRoute(path: '/profile', parentNavigatorKey: _rootKey, builder: (_, _) => ProfileScreen()),
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => _NavShell(shell: shell),
        branches: [
          StatefulShellBranch(routes: [GoRoute(path: '/home', builder: (_, _) => HomeScreen())]),
          StatefulShellBranch(routes: [
            GoRoute(
              path: '/analyze',
              builder: (_, _) => UploadScreen(),
              routes: [
                GoRoute(
                  path: 'result/:id',
                  builder: (_, s) => AnalysisResultScreen(id: _id(s), initial: s.extra as Analysis?),
                  routes: [
                    GoRoute(
                      path: 'medicines',
                      builder: (_, s) => _withAnalysis(s, (a) => MedicinesScreen(analysis: a)),
                    ),
                    GoRoute(
                      path: 'subject',
                      builder: (_, s) => _withAnalysis(s, (a) => SubjectScreen(analysis: a)),
                    ),
                  ],
                ),
              ],
            ),
          ]),
          StatefulShellBranch(routes: [
            GoRoute(
              path: '/reports',
              builder: (_, _) => ReportsScreen(),
              routes: [GoRoute(path: ':id', builder: (_, s) => ReportDetailScreen(id: _id(s)))],
            ),
          ]),
          StatefulShellBranch(routes: [GoRoute(path: '/care', builder: (_, _) => CareScreen())]),
        ],
      ),
    ],
  );
});

int _id(GoRouterState s) => int.tryParse(s.pathParameters['id'] ?? '') ?? 0;

/// Uses the analysis passed via `extra`, or loads it by id (e.g. after a browser refresh).
Widget _withAnalysis(GoRouterState s, Widget Function(Analysis) builder) {
  final extra = s.extra;
  if (extra is Analysis) return builder(extra);
  return _AnalysisLoader(id: _id(s), builder: builder);
}

class _AnalysisLoader extends ConsumerWidget {
  const _AnalysisLoader({required this.id, required this.builder});
  final int id;
  final Widget Function(Analysis) builder;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ref.watch(analysisProvider(id)).when(
          data: builder,
          loading: () => Scaffold(body: Center(child: CircularProgressIndicator(color: context.c.brand))),
          error: (e, _) => Scaffold(body: Center(child: Text(e.toString()))),
        );
  }
}

class _NavShell extends StatelessWidget {
  const _NavShell({required this.shell});
  final StatefulNavigationShell shell;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: shell,
      bottomNavigationBar: NavigationBarTheme(
        data: NavigationBarThemeData(
          backgroundColor: context.c.surface,
          indicatorColor: context.c.soft,
          labelTextStyle: WidgetStateProperty.resolveWith(
            (s) => TextStyle(
              fontSize: 11.5,
              fontWeight: s.contains(WidgetState.selected) ? FontWeight.w700 : FontWeight.w500,
              color: s.contains(WidgetState.selected) ? context.c.brand : context.c.muted,
            ),
          ),
          iconTheme: WidgetStateProperty.resolveWith(
            (s) => IconThemeData(color: s.contains(WidgetState.selected) ? context.c.brand : context.c.muted),
          ),
        ),
        child: NavigationBar(
          height: 66,
          selectedIndex: shell.currentIndex,
          // Re-tapping the active tab returns to its first screen.
          onDestinationSelected: (i) => shell.goBranch(i, initialLocation: i == shell.currentIndex),
          destinations: [
            NavigationDestination(icon: Icon(Icons.home_outlined), selectedIcon: Icon(Icons.home_rounded), label: 'Home'),
            NavigationDestination(
                icon: Icon(Icons.radio_button_unchecked), selectedIcon: Icon(Icons.adjust_rounded), label: 'Analyze'),
            NavigationDestination(
                icon: Icon(Icons.description_outlined), selectedIcon: Icon(Icons.description_rounded), label: 'Reports'),
            NavigationDestination(
                icon: Icon(Icons.location_on_outlined), selectedIcon: Icon(Icons.location_on_rounded), label: 'Care'),
          ],
        ),
      ),
    );
  }
}
