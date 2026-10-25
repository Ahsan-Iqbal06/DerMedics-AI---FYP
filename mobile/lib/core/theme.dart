import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// DerMedics colour tokens. Read them with `context.c` so every widget follows the active theme.
@immutable
class AppColors extends ThemeExtension<AppColors> {
  const AppColors({
    required this.brand,
    required this.onBrand,
    required this.deep,
    required this.onDeep,
    required this.soft,
    required this.accent,
    required this.canvas,
    required this.surface,
    required this.surfaceAlt,
    required this.text,
    required this.muted,
    required this.border,
    required this.amberBg,
    required this.amberText,
    required this.amberDot,
    required this.dangerBg,
    required this.danger,
    required this.heroGradient,
  });

  /// Primary actions, links and selected states.
  final Color brand;
  final Color onBrand;

  /// Hero cards and banners.
  final Color deep;
  final Color onDeep;

  /// Soft lavender highlight behind chips, icons and selected cards.
  final Color soft;

  /// Lilac accent for small details (badges on hero, progress glow).
  final Color accent;
  final Color canvas;
  final Color surface;
  final Color surfaceAlt;
  final Color text;
  final Color muted;
  final Color border;
  final Color amberBg;
  final Color amberText;
  final Color amberDot;
  final Color dangerBg;
  final Color danger;
  final List<Color> heroGradient;

  /// Purple · lavender · white.
  static const light = AppColors(
    brand: Color(0xFF6D3FD1),
    onBrand: Colors.white,
    deep: Color(0xFF3A1F78),
    onDeep: Colors.white,
    soft: Color(0xFFEFE8FD),
    accent: Color(0xFFC9B3F7),
    canvas: Color(0xFFF8F6FE),
    surface: Colors.white,
    surfaceAlt: Color(0xFFF2EEFB),
    text: Color(0xFF1E1633),
    muted: Color(0xFF6F6787),
    border: Color(0xFFE6E0F3),
    amberBg: Color(0xFFFFF4DC),
    amberText: Color(0xFF8A5A00),
    amberDot: Color(0xFF9A6B1F),
    dangerBg: Color(0xFFFDE8EC),
    danger: Color(0xFFC0283F),
    heroGradient: [Color(0xFF3A1F78), Color(0xFF6D3FD1)],
  );

  /// Black purple · lilac · lavender · grey.
  static const dark = AppColors(
    brand: Color(0xFFB69CFF),
    onBrand: Color(0xFF1A1030),
    deep: Color(0xFF2A1C4E),
    onDeep: Color(0xFFF3EEFF),
    soft: Color(0xFF2B2140),
    accent: Color(0xFFD7B8F3),
    canvas: Color(0xFF0E0B15),
    surface: Color(0xFF17121F),
    surfaceAlt: Color(0xFF1F1829),
    text: Color(0xFFEDE8F7),
    muted: Color(0xFFA29BB3),
    border: Color(0xFF2C2439),
    amberBg: Color(0xFF33280F),
    amberText: Color(0xFFF2C97D),
    amberDot: Color(0xFFD9A441),
    dangerBg: Color(0xFF3A1520),
    danger: Color(0xFFFF8FA3),
    heroGradient: [Color(0xFF241640), Color(0xFF4B2F8F)],
  );

  @override
  AppColors copyWith() => this;

  @override
  AppColors lerp(ThemeExtension<AppColors>? other, double t) {
    if (other is! AppColors) return this;
    Color l(Color a, Color b) => Color.lerp(a, b, t)!;
    return AppColors(
      brand: l(brand, other.brand),
      onBrand: l(onBrand, other.onBrand),
      deep: l(deep, other.deep),
      onDeep: l(onDeep, other.onDeep),
      soft: l(soft, other.soft),
      accent: l(accent, other.accent),
      canvas: l(canvas, other.canvas),
      surface: l(surface, other.surface),
      surfaceAlt: l(surfaceAlt, other.surfaceAlt),
      text: l(text, other.text),
      muted: l(muted, other.muted),
      border: l(border, other.border),
      amberBg: l(amberBg, other.amberBg),
      amberText: l(amberText, other.amberText),
      amberDot: l(amberDot, other.amberDot),
      dangerBg: l(dangerBg, other.dangerBg),
      danger: l(danger, other.danger),
      heroGradient: [l(heroGradient[0], other.heroGradient[0]), l(heroGradient[1], other.heroGradient[1])],
    );
  }
}

extension AppColorsX on BuildContext {
  AppColors get c {
    final theme = Theme.of(this);
    // Fall back to the matching palette when a plain ThemeData is in use (e.g. widget tests).
    return theme.extension<AppColors>() ??
        (theme.brightness == Brightness.dark ? AppColors.dark : AppColors.light);
  }
  bool get isDark => Theme.of(this).brightness == Brightness.dark;
}

class AppTheme {
  static ThemeData light() => _build(AppColors.light, Brightness.light);
  static ThemeData dark() => _build(AppColors.dark, Brightness.dark);

  static ThemeData _build(AppColors c, Brightness brightness) {
    final base = ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: ColorScheme.fromSeed(
        seedColor: c.brand,
        brightness: brightness,
        primary: c.brand,
        onPrimary: c.onBrand,
        surface: c.surface,
        onSurface: c.text,
        error: c.danger,
      ),
      scaffoldBackgroundColor: c.canvas,
      extensions: [c],
    );
    final text = GoogleFonts.interTextTheme(base.textTheme).apply(bodyColor: c.text, displayColor: c.text);
    final radius = BorderRadius.circular(14);
    OutlineInputBorder outline(Color color, [double width = 1]) =>
        OutlineInputBorder(borderRadius: radius, borderSide: BorderSide(color: color, width: width));

    return base.copyWith(
      textTheme: text,
      appBarTheme: AppBarTheme(backgroundColor: c.canvas, foregroundColor: c.text, elevation: 0, scrolledUnderElevation: 0),
      iconTheme: IconThemeData(color: c.text),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: c.surface,
        contentPadding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
        labelStyle: TextStyle(color: c.muted, fontSize: 13),
        floatingLabelStyle: TextStyle(color: c.brand, fontWeight: FontWeight.w600),
        hintStyle: TextStyle(color: c.muted, fontSize: 14),
        prefixIconColor: c.muted,
        suffixIconColor: c.muted,
        border: outline(c.border),
        enabledBorder: outline(c.border),
        focusedBorder: outline(c.brand, 1.6),
        errorBorder: outline(c.danger),
        focusedErrorBorder: outline(c.danger, 1.6),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: c.brand,
          foregroundColor: c.onBrand,
          disabledBackgroundColor: c.brand.withValues(alpha: 0.35),
          disabledForegroundColor: c.onBrand.withValues(alpha: 0.8),
          minimumSize: const Size.fromHeight(52),
          shape: RoundedRectangleBorder(borderRadius: radius),
          textStyle: GoogleFonts.inter(fontSize: 15, fontWeight: FontWeight.w600),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: c.brand,
          backgroundColor: c.surface,
          side: BorderSide(color: c.border),
          shape: RoundedRectangleBorder(borderRadius: radius),
          textStyle: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: c.brand,
          textStyle: GoogleFonts.inter(fontSize: 14, fontWeight: FontWeight.w600),
        ),
      ),
      checkboxTheme: CheckboxThemeData(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(4)),
        side: BorderSide(color: c.muted, width: 1.6),
        checkColor: WidgetStatePropertyAll(c.onBrand),
        fillColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? c.brand : Colors.transparent),
      ),
      switchTheme: SwitchThemeData(
        thumbColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? c.onBrand : c.muted),
        trackColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? c.brand : c.surfaceAlt),
        trackOutlineColor: WidgetStateProperty.resolveWith((s) => s.contains(WidgetState.selected) ? c.brand : c.border),
      ),
      progressIndicatorTheme: ProgressIndicatorThemeData(color: c.brand, linearTrackColor: c.soft),
      dialogTheme: DialogThemeData(backgroundColor: c.surface),
      bottomSheetTheme: BottomSheetThemeData(backgroundColor: c.surface, dragHandleColor: c.border),
      popupMenuTheme: PopupMenuThemeData(color: c.surface),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: c.deep,
        contentTextStyle: TextStyle(color: c.onDeep),
      ),
      dividerTheme: DividerThemeData(color: c.border, space: 1),
      listTileTheme: ListTileThemeData(iconColor: c.brand, textColor: c.text),
    );
  }
}
