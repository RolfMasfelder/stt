import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:stt_app/models/job_result.dart';
import 'package:stt_app/models/upload_status.dart';
import 'package:stt_app/screens/result_screen.dart';
import 'package:stt_app/services/auth.dart';
import 'package:stt_app/services/upload.dart';

class _FakeAuthService extends AuthService {
  @override
  Future<Map<String, String>> getAuthHeaders() async => {};
}

JobResult _makeJob({
  String status = 'completed',
  String? resultText,
  String? resultSummary,
  String? resultDiarizedText,
  String? resultStructuredText,
}) {
  return JobResult(
    id: 'job-1',
    status: status,
    originalFilename: 'test.m4a',
    whisperModel: 'small',
    createdAt: DateTime(2024, 1, 1),
    resultText: resultText,
    resultSummary: resultSummary,
    resultDiarizedText: resultDiarizedText,
    resultStructuredText: resultStructuredText,
  );
}

Widget _buildApp(UploadService upload) {
  return ChangeNotifierProvider<UploadService>.value(
    value: upload,
    child: const MaterialApp(home: ResultScreen()),
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
  });

  group('ResultScreen', () {
    testWidgets('shows idle text when status is idle', (tester) async {
      final svc = UploadService(authService: _FakeAuthService());
      addTearDown(svc.dispose);

      await tester.pumpWidget(_buildApp(svc));
      await tester.pump();

      expect(find.text('Kein aktiver Auftrag'), findsOneWidget);
    });

    testWidgets('shows upload progress when uploading', (tester) async {
      final svc = UploadService(authService: _FakeAuthService());
      addTearDown(svc.dispose);
      svc.setTestStatus(UploadStatus.uploading);

      await tester.pumpWidget(_buildApp(svc));
      await tester.pump();

      expect(find.text('Wird hochgeladen...'), findsOneWidget);
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('shows spinner when processing', (tester) async {
      final svc = UploadService(authService: _FakeAuthService());
      addTearDown(svc.dispose);
      svc.setTestStatus(
        UploadStatus.processing,
        job: _makeJob(status: 'running'),
      );

      await tester.pumpWidget(_buildApp(svc));
      await tester.pump();

      expect(find.byType(CircularProgressIndicator), findsOneWidget);
      expect(find.textContaining('Verarbeitung läuft'), findsOneWidget);
    });

    testWidgets('shows error message when failed', (tester) async {
      final svc = UploadService(authService: _FakeAuthService());
      addTearDown(svc.dispose);
      svc.setTestStatus(UploadStatus.failed, error: 'Verbindungsfehler');

      await tester.pumpWidget(_buildApp(svc));
      await tester.pump();

      expect(find.text('Verbindungsfehler'), findsOneWidget);
      expect(find.byIcon(Icons.error_outline), findsOneWidget);
    });

    testWidgets('shows all 4 tabs when all result fields are set', (
      tester,
    ) async {
      final svc = UploadService(authService: _FakeAuthService());
      addTearDown(svc.dispose);
      svc.setTestStatus(
        UploadStatus.completed,
        job: _makeJob(
          resultText: 'Roher Transkripttext',
          resultSummary: 'Kurzfassung des Inhalts',
          resultDiarizedText: 'Sprecherzuordnung',
          resultStructuredText: 'Strukturierter Text',
        ),
      );

      await tester.pumpWidget(_buildApp(svc));
      await tester.pump();

      expect(find.text('Zusammenfassung'), findsOneWidget);
      expect(find.text('Struktur'), findsOneWidget);
      expect(find.text('Sprecher'), findsOneWidget);
      expect(find.text('Transkript'), findsOneWidget);
    });

    testWidgets('shows only transcript tab when only resultText is set', (
      tester,
    ) async {
      final svc = UploadService(authService: _FakeAuthService());
      addTearDown(svc.dispose);
      svc.setTestStatus(
        UploadStatus.completed,
        job: _makeJob(resultText: 'Nur Transkript'),
      );

      await tester.pumpWidget(_buildApp(svc));
      await tester.pump();

      expect(find.text('Transkript'), findsOneWidget);
      expect(find.text('Zusammenfassung'), findsNothing);
      expect(find.text('Struktur'), findsNothing);
      expect(find.text('Sprecher'), findsNothing);
    });

    testWidgets('shows 2 tabs for text + summary', (tester) async {
      final svc = UploadService(authService: _FakeAuthService());
      addTearDown(svc.dispose);
      svc.setTestStatus(
        UploadStatus.completed,
        job: _makeJob(resultText: 'T', resultSummary: 'Z'),
      );

      await tester.pumpWidget(_buildApp(svc));
      await tester.pump();

      expect(find.text('Transkript'), findsOneWidget);
      expect(find.text('Zusammenfassung'), findsOneWidget);
      expect(find.text('Struktur'), findsNothing);
      expect(find.text('Sprecher'), findsNothing);
    });

    testWidgets('tab content is scrollable', (tester) async {
      final svc = UploadService(authService: _FakeAuthService());
      addTearDown(svc.dispose);
      svc.setTestStatus(
        UploadStatus.completed,
        job: _makeJob(resultText: 'Inhalt des Transkripts'),
      );

      await tester.pumpWidget(_buildApp(svc));
      await tester.pump();

      expect(find.byType(SingleChildScrollView), findsAtLeastNWidgets(1));
    });

    testWidgets('copy-all button visible when job is completed', (
      tester,
    ) async {
      final svc = UploadService(authService: _FakeAuthService());
      addTearDown(svc.dispose);
      svc.setTestStatus(
        UploadStatus.completed,
        job: _makeJob(resultText: 'text'),
      );

      await tester.pumpWidget(_buildApp(svc));
      await tester.pump();

      // The AppBar shows a copy-all icon button when the job is completed.
      expect(
        find.descendant(
          of: find.byType(AppBar),
          matching: find.byIcon(Icons.copy),
        ),
        findsOneWidget,
      );
    });

    testWidgets('copy-all button not shown when idle', (tester) async {
      final svc = UploadService(authService: _FakeAuthService());
      addTearDown(svc.dispose);

      await tester.pumpWidget(_buildApp(svc));
      await tester.pump();

      expect(
        find.descendant(
          of: find.byType(AppBar),
          matching: find.byIcon(Icons.copy),
        ),
        findsNothing,
      );
    });
  });
}
