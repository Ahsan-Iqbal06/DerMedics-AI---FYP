import 'package:dermedics_ai/core/models.dart';
import 'package:dermedics_ai/core/theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('light and dark themes carry their palettes', () {
    final light = AppTheme.light();
    final dark = AppTheme.dark();
    expect(light.brightness, Brightness.light);
    expect(dark.brightness, Brightness.dark);
    expect(light.extension<AppColors>()!.brand, AppColors.light.brand);
    expect(dark.extension<AppColors>()!.canvas, AppColors.dark.canvas);
  });

  test('palette lerp blends colours for the theme switch animation', () {
    final mid = AppColors.light.lerp(AppColors.dark, 0.5);
    expect(mid.canvas, Color.lerp(AppColors.light.canvas, AppColors.dark.canvas, 0.5));
    expect(AppColors.light.lerp(AppColors.dark, 1).brand, AppColors.dark.brand);
  });

  test('user avatar url parses', () {
    final u = AppUser.fromJson({
      'id': 1,
      'full_name': 'Hasnain Iqbal',
      'email': 'h@example.com',
      'country': 'Pakistan',
      'city': 'Abbottabad',
      'avatar_url': '/uploads/avatars/a.jpg',
    });
    expect(u.avatarUrl, '/uploads/avatars/a.jpg');
    expect(u.initial, 'H');
  });
}
