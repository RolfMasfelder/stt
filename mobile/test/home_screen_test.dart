import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:stt_app/screens/home_screen.dart';
import 'package:stt_app/services/auth.dart';
import 'package:stt_app/services/audio_recording.dart';
import 'package:stt_app/services/processing_config.dart';
import 'package:stt_app/services/recording_history.dart';
import 'package:stt_app/services/server_connection.dart';
import 'package:stt_app/services/upload.dart';

Widget createTestApp() {
  return MultiProvider(
    providers: [
      ChangeNotifierProvider(create: (_) => ServerConnectionService()),
      ChangeNotifierProvider(create: (_) => AudioRecordingService()),
      ChangeNotifierProvider(create: (_) => ProcessingConfigService()),
      ChangeNotifierProvider(create: (_) => AuthService()),
      ChangeNotifierProvider(create: (_) => RecordingHistoryService()),
      ChangeNotifierProxyProvider<AuthService, UploadService>(
        create: (ctx) =>
            UploadService(authService: ctx.read<AuthService>()),
        update: (_, auth, previous) =>
            previous ?? UploadService(authService: auth),
      ),
    ],
    child: MaterialApp(
      home: const HomeScreen(),
      routes: {
        '/settings': (context) => const Scaffold(body: Text('Settings')),
      },
    ),
  );
}

void main() {
  group('HomeScreen', () {
    testWidgets('shows disconnected state initially', (tester) async {
      await tester.pumpWidget(createTestApp());
      await tester.pump();

      expect(find.text('STT'), findsOneWidget);
      expect(find.text('Nicht verbunden'), findsOneWidget);
      expect(find.byIcon(Icons.settings), findsOneWidget);
    });

    testWidgets('navigates to settings', (tester) async {
      await tester.pumpWidget(createTestApp());
      await tester.pump();

      await tester.tap(find.byIcon(Icons.settings));
      await tester.pumpAndSettle();

      expect(find.text('Settings'), findsOneWidget);
    });

    testWidgets('shows snackbar when tapping eye while disconnected',
        (tester) async {
      await tester.pumpWidget(createTestApp());
      await tester.pump();

      // Tap the GestureDetector wrapping HalEye
      await tester.tap(find.byType(GestureDetector).first);
      await tester.pump();

      expect(
        find.text('Bitte zuerst Server-Verbindung einrichten'),
        findsOneWidget,
      );
    });

    testWidgets('does not show recording controls in idle state',
        (tester) async {
      await tester.pumpWidget(createTestApp());
      await tester.pump();

      expect(find.byIcon(Icons.stop), findsNothing);
      expect(find.byIcon(Icons.pause), findsNothing);
    });
  });
}
