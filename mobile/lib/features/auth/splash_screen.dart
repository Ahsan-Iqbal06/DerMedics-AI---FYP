import 'package:flutter/material.dart';

import '../../core/theme.dart';
import '../../core/widgets.dart';

class SplashScreen extends StatelessWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: DecoratedBox(
        // Theme background with a soft lavender glow, so the transparent purple logo stays clear.
        decoration: BoxDecoration(
          gradient: RadialGradient(radius: 0.9, colors: [context.c.soft, context.c.canvas]),
        ),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const LogoMark(size: 120),
              const SizedBox(height: 22),
              const GlassWordmark(fontSize: 26),
              const SizedBox(height: 32),
              SizedBox(
                width: 24,
                height: 24,
                child: CircularProgressIndicator(strokeWidth: 2.4, color: context.c.brand),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
