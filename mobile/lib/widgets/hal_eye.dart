import 'dart:math';
import 'package:flutter/material.dart';

import '../models/connection_status.dart';

class HalEye extends StatefulWidget {
  final ConnectionStatus status;
  final double size;
  final bool recording;

  const HalEye({
    super.key,
    required this.status,
    this.size = 200.0,
    this.recording = false,
  });

  @override
  State<HalEye> createState() => _HalEyeState();
}

class _HalEyeState extends State<HalEye> with TickerProviderStateMixin {
  late AnimationController _glowController;
  late Animation<double> _glowAnimation;
  late AnimationController _colorController;
  late Animation<Color?> _colorAnimation;
  Color _currentColor = Colors.grey;

  @override
  void initState() {
    super.initState();
    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);
    _glowAnimation = Tween<double>(begin: 0.4, end: 1.0).animate(
      CurvedAnimation(parent: _glowController, curve: Curves.easeInOut),
    );

    _colorController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    _currentColor = _targetColor();
    _colorAnimation = AlwaysStoppedAnimation(_currentColor);
  }

  @override
  void didUpdateWidget(HalEye oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.status != widget.status ||
        oldWidget.recording != widget.recording) {
      final newColor = _targetColor();
      _colorAnimation = ColorTween(begin: _currentColor, end: newColor)
          .animate(CurvedAnimation(
        parent: _colorController,
        curve: Curves.easeInOut,
      ));
      _colorController.forward(from: 0.0).then((_) {
        _currentColor = newColor;
      });
    }

    // Faster pulsing when recording
    if (widget.recording && !oldWidget.recording) {
      _glowController.duration = const Duration(milliseconds: 1000);
      _glowController.repeat(reverse: true);
    } else if (!widget.recording && oldWidget.recording) {
      _glowController.duration = const Duration(milliseconds: 2000);
      _glowController.repeat(reverse: true);
    }
  }

  Color _targetColor() {
    if (widget.recording) return Colors.red;
    switch (widget.status) {
      case ConnectionStatus.disconnected:
        return Colors.grey;
      case ConnectionStatus.connected:
        return Colors.green;
      case ConnectionStatus.error:
        return Colors.red;
    }
  }

  @override
  void dispose() {
    _glowController.dispose();
    _colorController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isActive = widget.status != ConnectionStatus.disconnected ||
        widget.recording;

    return AnimatedBuilder(
      animation: Listenable.merge([_glowAnimation, _colorAnimation]),
      builder: (context, child) {
        final glowIntensity = isActive ? _glowAnimation.value : 0.3;
        final color = _colorAnimation.value ?? _currentColor;
        return CustomPaint(
          size: Size(widget.size, widget.size),
          painter: _HalEyePainter(
            color: color,
            glowIntensity: glowIntensity,
          ),
        );
      },
    );
  }
}

class _HalEyePainter extends CustomPainter {
  final Color color;
  final double glowIntensity;

  _HalEyePainter({required this.color, required this.glowIntensity});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = min(size.width, size.height) / 2;

    // Outer glow
    final glowPaint = Paint()
      ..color = color.withValues(alpha: 0.15 * glowIntensity)
      ..maskFilter = MaskFilter.blur(BlurStyle.normal, radius * 0.4);
    canvas.drawCircle(center, radius, glowPaint);

    // Dark ring (bezel)
    final bezelPaint = Paint()
      ..color = const Color(0xFF1A1A1A)
      ..style = PaintingStyle.fill;
    canvas.drawCircle(center, radius * 0.85, bezelPaint);

    // Inner glow
    final innerGlowPaint = Paint()
      ..shader = RadialGradient(
        colors: [
          color.withValues(alpha: glowIntensity),
          color.withValues(alpha: 0.6 * glowIntensity),
          color.withValues(alpha: 0.1 * glowIntensity),
          Colors.transparent,
        ],
        stops: const [0.0, 0.3, 0.7, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: radius * 0.7));
    canvas.drawCircle(center, radius * 0.7, innerGlowPaint);

    // Bright core
    final corePaint = Paint()
      ..shader = RadialGradient(
        colors: [
          Colors.white.withValues(alpha: 0.9 * glowIntensity),
          color.withValues(alpha: 0.8 * glowIntensity),
          Colors.transparent,
        ],
        stops: const [0.0, 0.4, 1.0],
      ).createShader(Rect.fromCircle(center: center, radius: radius * 0.3));
    canvas.drawCircle(center, radius * 0.3, corePaint);

    // Specular highlight
    final specularCenter = Offset(
      center.dx - radius * 0.15,
      center.dy - radius * 0.15,
    );
    final specularPaint = Paint()
      ..shader = RadialGradient(
        colors: [
          Colors.white.withValues(alpha: 0.4 * glowIntensity),
          Colors.transparent,
        ],
      ).createShader(
          Rect.fromCircle(center: specularCenter, radius: radius * 0.15));
    canvas.drawCircle(specularCenter, radius * 0.15, specularPaint);
  }

  @override
  bool shouldRepaint(_HalEyePainter oldDelegate) =>
      color != oldDelegate.color ||
      glowIntensity != oldDelegate.glowIntensity;
}
