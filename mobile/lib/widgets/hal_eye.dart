import 'dart:math';
import 'package:flutter/material.dart';

import '../models/connection_status.dart';

class HalEye extends StatefulWidget {
  final ConnectionStatus status;
  final double size;

  const HalEye({
    super.key,
    required this.status,
    this.size = 200.0,
  });

  @override
  State<HalEye> createState() => _HalEyeState();
}

class _HalEyeState extends State<HalEye> with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _glowAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);
    _glowAnimation = Tween<double>(begin: 0.4, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Color _getColor() {
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
  Widget build(BuildContext context) {
    final color = _getColor();
    final isActive = widget.status != ConnectionStatus.disconnected;

    return AnimatedBuilder(
      animation: _glowAnimation,
      builder: (context, child) {
        final glowIntensity = isActive ? _glowAnimation.value : 0.3;
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
