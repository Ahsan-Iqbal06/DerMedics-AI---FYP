import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../features/auth/auth_controller.dart';
import 'config.dart';
import 'models.dart';
import 'theme.dart';
import 'theme_mode.dart';

/// "D DerMedics AI .... (H)" header used at the top of every main screen.
class AppHeader extends ConsumerWidget {
  const AppHeader({super.key, this.showBack = false});
  final bool showBack;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authControllerProvider).user;
    return Padding(
      padding: EdgeInsets.fromLTRB(20, 12, 20, 8),
      child: Row(
        children: [
          if (showBack && context.canPop())
            Padding(
              padding: EdgeInsets.only(right: 8),
              child: InkWell(
                borderRadius: BorderRadius.circular(20),
                onTap: () => context.pop(),
                child: Padding(
                  padding: EdgeInsets.all(4),
                  child: Icon(Icons.arrow_back_rounded, color: context.c.text),
                ),
              ),
            ),
          LogoMark(),
          SizedBox(width: 10),
          const Expanded(
            child: Align(
              alignment: Alignment.centerLeft,
              child: FittedBox(fit: BoxFit.scaleDown, child: GlassWordmark()),
            ),
          ),
          const ThemeToggleButton(),
          const SizedBox(width: 6),
          Semantics(
            button: true,
            label: 'Profile and settings',
            child: InkWell(
              customBorder: const CircleBorder(),
              onTap: () => context.push('/profile'),
              child: UserAvatar(user: user, radius: 17),
            ),
          ),
        ],
      ),
    );
  }
}

/// Profile photo if the user uploaded one, otherwise their initial on lavender.
class UserAvatar extends StatelessWidget {
  const UserAvatar({super.key, required this.user, this.radius = 17});
  final AppUser? user;
  final double radius;

  @override
  Widget build(BuildContext context) {
    final url = user?.avatarUrl;
    final initial = Text(
      user?.initial ?? '?',
      style: TextStyle(color: context.c.brand, fontWeight: FontWeight.w700, fontSize: radius * 0.8),
    );
    return Container(
      padding: const EdgeInsets.all(1.5),
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: LinearGradient(colors: [context.c.brand, context.c.accent]),
      ),
      child: CircleAvatar(
        radius: radius,
        backgroundColor: context.c.soft,
        child: url == null
            ? initial
            : ClipOval(
                child: Image.network(
                  '${AppConfig.baseUrl}$url',
                  key: ValueKey(url),
                  width: radius * 2,
                  height: radius * 2,
                  fit: BoxFit.cover,
                  errorBuilder: (_, _, _) => initial,
                ),
              ),
      ),
    );
  }
}

/// Sun/moon button that flips between light and dark mode with a small spin.
class ThemeToggleButton extends ConsumerWidget {
  const ThemeToggleButton({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dark = context.isDark;
    return Tooltip(
      message: dark ? 'Switch to light mode' : 'Switch to dark mode',
      child: InkWell(
        customBorder: const CircleBorder(),
        onTap: () => ref.read(themeModeProvider.notifier).toggle(Theme.of(context).brightness),
        child: Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(color: context.c.surface, shape: BoxShape.circle, border: Border.all(color: context.c.border)),
          child: AnimatedSwitcher(
            duration: const Duration(milliseconds: 350),
            transitionBuilder: (child, anim) => RotationTransition(
              turns: Tween(begin: 0.6, end: 1.0).animate(anim),
              child: FadeTransition(opacity: anim, child: child),
            ),
            child: Icon(
              dark ? Icons.light_mode_rounded : Icons.dark_mode_rounded,
              key: ValueKey(dark),
              size: 18,
              color: dark ? context.c.accent : context.c.brand,
            ),
          ),
        ),
      ),
    );
  }
}

/// Purple gradient used by hero cards (home, auth, reports).
BoxDecoration heroDecoration(BuildContext context, {double radius = 20}) => BoxDecoration(
      gradient: LinearGradient(
        colors: context.c.heroGradient,
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      ),
      borderRadius: BorderRadius.circular(radius),
      boxShadow: [
        BoxShadow(
          color: context.c.brand.withValues(alpha: context.isDark ? 0.18 : 0.28),
          blurRadius: 24,
          offset: const Offset(0, 10),
        ),
      ],
    );

/// The DerMedics logo on a transparent background, with a soft lavender glow behind it.
class LogoMark extends StatelessWidget {
  const LogoMark({super.key, this.size = 36});
  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        boxShadow: [
          BoxShadow(
            color: context.c.brand.withValues(alpha: context.isDark ? 0.30 : 0.14),
            blurRadius: size * 0.45,
            spreadRadius: -size * 0.12,
          ),
        ],
      ),
      child: Image.asset('assets/images/logo.png', fit: BoxFit.contain, filterQuality: FilterQuality.medium),
    );
  }
}

/// "DerMedics AI" in a frosted-glass pill with gradient, glossy lettering that follows the theme.
class GlassWordmark extends StatelessWidget {
  const GlassWordmark({super.key, this.fontSize = 17, this.onHero = false});
  final double fontSize;

  /// Use the bright variant on purple hero/gradient backgrounds (e.g. splash).
  final bool onHero;

  @override
  Widget build(BuildContext context) {
    final c = context.c;
    final dark = context.isDark;
    final ink = onHero
        ? [Colors.white, c.accent, Colors.white]
        : dark
            ? [const Color(0xFFF6F1FF), c.accent, c.brand]
            : [c.deep, c.brand, const Color(0xFF9B6BFF)];
    final glassTop = Colors.white.withValues(alpha: onHero ? 0.20 : (dark ? 0.10 : 0.70));
    final glassBottom = Colors.white.withValues(alpha: onHero ? 0.06 : (dark ? 0.03 : 0.30));
    final rim = onHero || dark ? Colors.white.withValues(alpha: 0.16) : Colors.white.withValues(alpha: 0.95);

    final style = TextStyle(fontSize: fontSize, fontWeight: FontWeight.w800, letterSpacing: 0.2, height: 1.1);
    final label = Text.rich(
      TextSpan(children: [
        const TextSpan(text: 'DerMedics'),
        TextSpan(text: ' AI', style: TextStyle(fontWeight: FontWeight.w600, letterSpacing: 0.6)),
      ]),
      style: style,
    );

    return ClipRRect(
      borderRadius: BorderRadius.circular(fontSize),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
        child: Container(
          padding: EdgeInsets.symmetric(horizontal: fontSize * 0.7, vertical: fontSize * 0.32),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(fontSize),
            gradient: LinearGradient(begin: Alignment.topCenter, end: Alignment.bottomCenter, colors: [glassTop, glassBottom]),
            border: Border.all(color: rim, width: 1),
            boxShadow: [
              BoxShadow(color: c.brand.withValues(alpha: dark || onHero ? 0.18 : 0.10), blurRadius: 16, offset: const Offset(0, 4)),
            ],
          ),
          child: Stack(
            children: [
              // Gradient lettering.
              ShaderMask(
                blendMode: BlendMode.srcIn,
                shaderCallback: (r) => LinearGradient(colors: ink, stops: const [0, 0.6, 1]).createShader(r),
                child: label,
              ),
              // Glossy highlight across the top half of the letters.
              ShaderMask(
                blendMode: BlendMode.srcIn,
                shaderCallback: (r) => LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [Colors.white.withValues(alpha: dark || onHero ? 0.45 : 0.55), Colors.white.withValues(alpha: 0)],
                  stops: const [0, 0.55],
                ).createShader(r),
                child: label,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Scrollable page body with the app header and consistent gutters.
class PageScaffold extends StatelessWidget {
  const PageScaffold({super.key, required this.children, this.showBack = false, this.onRefresh, this.bottom});
  final List<Widget> children;
  final bool showBack;
  final Future<void> Function()? onRefresh;
  final Widget? bottom;

  @override
  Widget build(BuildContext context) {
    Widget list = ListView(
      padding: EdgeInsets.fromLTRB(20, 4, 20, 28),
      physics: AlwaysScrollableScrollPhysics(),
      children: children,
    );
    if (onRefresh != null) list = RefreshIndicator(color: context.c.brand, onRefresh: onRefresh!, child: list);
    return Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            AppHeader(showBack: showBack),
            Expanded(child: list),
            ?bottom,
          ],
        ),
      ),
    );
  }
}

class PageTitle extends StatelessWidget {
  const PageTitle(this.title, {super.key, this.subtitle});
  final String title;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(top: 8, bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: TextStyle(fontSize: 26, fontWeight: FontWeight.w800, height: 1.15)),
          if (subtitle != null) ...[
            SizedBox(height: 6),
            Text(subtitle!, style: TextStyle(color: context.c.muted, fontSize: 14, height: 1.4)),
          ],
        ],
      ),
    );
  }
}

class SectionHeader extends StatelessWidget {
  const SectionHeader(this.title, {super.key, this.subtitle, this.trailing});
  final String title;
  final String? subtitle;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(top: 18, bottom: 10),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
                if (subtitle != null)
                  Padding(
                    padding: EdgeInsets.only(top: 3),
                    child: Text(subtitle!, style: TextStyle(color: context.c.muted, fontSize: 12.5)),
                  ),
              ],
            ),
          ),
          ?trailing,
        ],
      ),
    );
  }
}

class AppCard extends StatelessWidget {
  const AppCard({super.key, required this.child, this.padding = const EdgeInsets.all(16), this.color, this.onTap, this.borderColor});
  final Widget child;
  final EdgeInsets padding;
  final Color? color;
  final Color? borderColor;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: color ?? context.c.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: BorderSide(color: borderColor ?? context.c.border),
      ),
      clipBehavior: Clip.antiAlias,
      child: InkWell(onTap: onTap, child: Padding(padding: padding, child: child)),
    );
  }
}

enum BadgeTone { mint, amber, danger, neutral }

class StatusBadge extends StatelessWidget {
  const StatusBadge(this.label, {super.key, this.tone = BadgeTone.mint});
  final String label;
  final BadgeTone tone;

  @override
  Widget build(BuildContext context) {
    final (bg, fg) = switch (tone) {
      BadgeTone.mint => (context.c.soft, context.c.brand),
      BadgeTone.amber => (context.c.amberBg, context.c.amberText),
      BadgeTone.danger => (context.c.dangerBg, context.c.danger),
      BadgeTone.neutral => (context.c.canvas, context.c.muted),
    };
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(20)),
      child: Text(label,
          style: TextStyle(color: fg, fontSize: 10.5, fontWeight: FontWeight.w700, letterSpacing: 0.4)),
    );
  }
}

/// Amber "Safety first" / "A gentle reminder" notice.
class NoticeBox extends StatelessWidget {
  const NoticeBox({super.key, required this.title, required this.body, this.tone = BadgeTone.amber, this.icon});
  final String title;
  final String body;
  final BadgeTone tone;
  final IconData? icon;

  @override
  Widget build(BuildContext context) {
    final (bg, fg) = switch (tone) {
      BadgeTone.mint => (context.c.soft, context.c.brand),
      BadgeTone.danger => (context.c.dangerBg, context.c.danger),
      BadgeTone.neutral => (context.c.surfaceAlt, context.c.text),
      BadgeTone.amber => (context.c.amberBg, context.c.amberText),
    };
    return Container(
      width: double.infinity,
      padding: EdgeInsets.all(14),
      decoration: BoxDecoration(color: bg, borderRadius: BorderRadius.circular(14)),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (icon != null) ...[Icon(icon, size: 18, color: fg), SizedBox(width: 10)],
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: TextStyle(color: fg, fontWeight: FontWeight.w700, fontSize: 13.5)),
                SizedBox(height: 4),
                Text(body, style: TextStyle(color: context.c.text, fontSize: 12.5, height: 1.4)),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class FootNote extends StatelessWidget {
  const FootNote(this.text, {super.key});
  final String text;

  @override
  Widget build(BuildContext context) => Padding(
        padding: EdgeInsets.only(top: 10),
        child: Text(text,
            textAlign: TextAlign.center, style: TextStyle(color: context.c.muted, fontSize: 11.5, height: 1.4)),
      );
}

class IconBubble extends StatelessWidget {
  const IconBubble(this.icon, {super.key, this.color, this.iconColor, this.size = 40});
  final IconData icon;
  final Color? color;
  final Color? iconColor;
  final double size;

  @override
  Widget build(BuildContext context) => Container(
        width: size,
        height: size,
        decoration: BoxDecoration(color: color ?? context.c.soft, shape: BoxShape.circle),
        child: Icon(icon, color: iconColor ?? context.c.brand, size: size * 0.5),
      );
}

/// Pill-style segmented control used for List/Map and report filters.
class Segmented<T> extends StatelessWidget {
  const Segmented({super.key, required this.options, required this.value, required this.onChanged});
  final Map<T, String> options;
  final T value;
  final ValueChanged<T> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.all(4),
      decoration: BoxDecoration(color: context.c.surfaceAlt, borderRadius: BorderRadius.circular(12)),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (final e in options.entries)
            GestureDetector(
              onTap: () => onChanged(e.key),
              child: AnimatedContainer(
                duration: Duration(milliseconds: 180),
                padding: EdgeInsets.symmetric(horizontal: 18, vertical: 8),
                decoration: BoxDecoration(
                  color: e.key == value ? context.c.brand : Colors.transparent,
                  borderRadius: BorderRadius.circular(9),
                ),
                child: Text(
                  e.value,
                  style: TextStyle(
                    color: e.key == value ? context.c.onBrand : context.c.muted,
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

class ErrorView extends StatelessWidget {
  const ErrorView({super.key, required this.message, this.onRetry});
  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => Padding(
        padding: EdgeInsets.symmetric(vertical: 32),
        child: Column(
          children: [
            Icon(Icons.cloud_off_rounded, color: context.c.muted, size: 36),
            SizedBox(height: 10),
            Text(message, textAlign: TextAlign.center, style: TextStyle(color: context.c.muted)),
            if (onRetry != null) TextButton(onPressed: onRetry, child: Text('Try again')),
          ],
        ),
      );
}

class LoadingView extends StatelessWidget {
  const LoadingView({super.key});
  @override
  Widget build(BuildContext context) => Padding(
        padding: EdgeInsets.symmetric(vertical: 48),
        child: Center(child: CircularProgressIndicator(color: context.c.brand)),
      );
}

String relativeDay(DateTime? d) {
  if (d == null) return '';
  final now = DateTime.now();
  final days = DateTime(now.year, now.month, now.day).difference(DateTime(d.year, d.month, d.day)).inDays;
  if (days == 0) return 'Today';
  if (days == 1) return 'Yesterday';
  if (days < 7) return DateFormat('EEEE').format(d);
  return DateFormat('d MMM yyyy').format(d);
}

void showSnack(BuildContext context, String message) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(message)));
}
