import 'package:dermedics_ai/core/models.dart';
import 'package:dermedics_ai/features/auth/auth_controller.dart';
import 'package:dermedics_ai/features/auth/login_screen.dart';
import 'package:dermedics_ai/features/home/home_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('Validators', () {
    test('email', () {
      expect(Validators.email(''), isNotNull);
      expect(Validators.email('not-an-email'), isNotNull);
      expect(Validators.email('a@b.co'), isNull);
    });

    test('strong password mirrors backend rules', () {
      expect(Validators.strongPassword('password'), contains('uppercase'));
      expect(Validators.strongPassword('Passw0rd'), contains('symbol'));
      expect(Validators.strongPassword('Str0ng!Pass'), isNull);
    });

    test('name', () {
      expect(Validators.name(' '), isNotNull);
      expect(Validators.name('12'), isNotNull);
      expect(Validators.name('Hasnain Iqbal'), isNull);
    });
  });

  test('greeting follows time of day', () {
    expect(greeting(DateTime(2026, 1, 1, 8)), 'Good morning');
    expect(greeting(DateTime(2026, 1, 1, 14)), 'Good afternoon');
    expect(greeting(DateTime(2026, 1, 1, 20)), 'Good evening');
  });

  test('analysis JSON parsing', () {
    final a = Analysis.fromJson({
      'id': 3,
      'status': 'ai',
      'predicted_label': 'acne',
      'display_name': 'Acne',
      'confidence': 0.823,
      'top_predictions': [
        {'label': 'acne', 'display_name': 'Acne', 'confidence': 0.823},
      ],
      'description': {'name': 'Acne', 'overview': 'x', 'symptoms': ['a'], 'precautions': [], 'when_to_see_doctor': ''},
      'medicines': [
        {'name': 'Benzoyl peroxide', 'type': 'Topical', 'prescription_required': false},
      ],
      'region': 'Abbottabad, Pakistan',
      'body_area': 'Face / neck',
      'symptoms': '',
      'is_demo': true,
      'image_url': '/uploads/x.jpg',
      'created_at': '2026-10-24T10:00:00Z',
      'dermatologists': [
        {'name': 'Dr. Sana Malik', 'city': 'Abbottabad', 'conditions': ['acne']},
      ],
    });
    expect(a.isConclusive, isTrue);
    expect(a.confidencePercent, 82);
    expect(a.medicines.single.name, 'Benzoyl peroxide');
    expect(a.dermatologists.single.conditions, ['acne']);
  });

  testWidgets('login form shows validation errors', (tester) async {
    await tester.pumpWidget(const ProviderScope(child: MaterialApp(home: LoginScreen())));
    await tester.tap(find.text('Sign in'));
    await tester.pump();
    expect(find.text('Enter your email'), findsOneWidget);
    expect(find.text('Enter your password'), findsOneWidget);

    await tester.enterText(find.byType(TextFormField).first, 'bad');
    await tester.tap(find.text('Sign in'));
    await tester.pump();
    expect(find.text('Enter a valid email address'), findsOneWidget);
  });
}
