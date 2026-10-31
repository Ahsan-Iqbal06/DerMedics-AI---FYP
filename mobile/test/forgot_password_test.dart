import 'package:dermedics_ai/features/auth/forgot_password_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('forgot password starts on the email step and validates it', (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.5;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(const ProviderScope(child: MaterialApp(home: ForgotPasswordScreen())));
    expect(find.text('Forgot password?'), findsOneWidget);
    expect(find.text('Send code'), findsOneWidget);

    await tester.tap(find.text('Send code'));
    await tester.pump();
    expect(find.text('Enter your email'), findsOneWidget);

    await tester.enterText(find.byType(TextFormField).first, 'not-an-email');
    await tester.tap(find.text('Send code'));
    await tester.pump();
    expect(find.text('Enter a valid email address'), findsOneWidget);
  });

  testWidgets('email passed from the sign-in screen is pre-filled', (tester) async {
    tester.view.physicalSize = const Size(1080, 2400);
    tester.view.devicePixelRatio = 2.5;
    addTearDown(tester.view.reset);

    await tester.pumpWidget(
      const ProviderScope(child: MaterialApp(home: ForgotPasswordScreen(initialEmail: 'hasnain@example.com'))),
    );
    expect(find.text('hasnain@example.com'), findsOneWidget);
  });
}
