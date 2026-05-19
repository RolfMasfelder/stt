import 'dart:convert';
import 'dart:io';

import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:stt_app/models/job_result.dart';
import 'package:stt_app/models/processing_config.dart';
import 'package:stt_app/models/upload_status.dart';
import 'package:stt_app/services/auth.dart';
import 'package:stt_app/services/upload.dart';

/// Returns a fixed bearer token without touching platform channels.
class _FakeAuthService extends AuthService {
  @override
  Future<Map<String, String>> getAuthHeaders() async {
    return {'Authorization': 'Bearer test-token'};
  }
}

/// Simulates not being authenticated.
class _UnauthedAuthService extends AuthService {
  @override
  Future<Map<String, String>> getAuthHeaders() async => {};
}

Map<String, dynamic> _jobJson(String id, {String status = 'pending'}) => {
  'id': id,
  'status': status,
  'original_filename': 'test.m4a',
  'whisper_model': 'small',
  'created_at': '2024-01-01T00:00:00Z',
};

JobResult _makeJob({
  String id = 'test-job-id',
  String status = 'completed',
  String? resultText,
  String? resultSummary,
  String? resultDiarizedText,
  String? resultStructuredText,
}) {
  return JobResult(
    id: id,
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

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late Directory tmpDir;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    FlutterSecureStorage.setMockInitialValues({});
    tmpDir = await Directory.systemTemp.createTemp('stt_test_');
  });

  tearDown(() async {
    await tmpDir.delete(recursive: true);
  });

  group('UploadService.uploadAndProcess', () {
    test('status becomes processing when server returns 202', () async {
      final mockClient = MockClient((request) async {
        if (request.url.path == '/v1/jobs') {
          return http.Response(
            jsonEncode(_jobJson('job-1')),
            202,
            headers: {'content-type': 'application/json'},
          );
        }
        return http.Response('', 404);
      });

      final audioFile = File('${tmpDir.path}/test.m4a');
      await audioFile.create();

      final svc = UploadService(
        authService: _FakeAuthService(),
        httpClient: mockClient,
      );
      addTearDown(svc.dispose);

      await svc.uploadAndProcess(
        serverUrl: 'http://localhost:8090',
        filePath: audioFile.path,
        config: const ProcessingConfig(),
      );

      expect(svc.status, UploadStatus.processing);
      expect(svc.currentJob?.id, 'job-1');
      svc.reset();
    });

    test('status becomes failed when server returns non-202', () async {
      final mockClient = MockClient(
        (_) async => http.Response('Server Error', 500),
      );

      final audioFile = File('${tmpDir.path}/test.m4a');
      await audioFile.create();

      final svc = UploadService(
        authService: _FakeAuthService(),
        httpClient: mockClient,
      );
      addTearDown(svc.dispose);

      await svc.uploadAndProcess(
        serverUrl: 'http://localhost:8090',
        filePath: audioFile.path,
        config: const ProcessingConfig(),
      );

      expect(svc.status, UploadStatus.failed);
      expect(svc.errorMessage, contains('500'));
    });

    test('status is failed with auth message when not authenticated', () async {
      final svc = UploadService(
        authService: _UnauthedAuthService(),
        httpClient: MockClient((_) async => http.Response('', 500)),
      );
      addTearDown(svc.dispose);

      await svc.uploadAndProcess(
        serverUrl: 'http://localhost:8090',
        filePath: '${tmpDir.path}/test.m4a',
        config: const ProcessingConfig(),
      );

      expect(svc.status, UploadStatus.failed);
      expect(svc.errorMessage, 'Nicht angemeldet');
    });

    test('second call while uploading is ignored', () async {
      var callCount = 0;
      final mockClient = MockClient((request) async {
        callCount++;
        return http.Response(
          jsonEncode(_jobJson('job-1')),
          202,
          headers: {'content-type': 'application/json'},
        );
      });

      final svc = UploadService(
        authService: _FakeAuthService(),
        httpClient: mockClient,
      );
      addTearDown(svc.dispose);

      svc.setTestStatus(UploadStatus.uploading);

      await svc.uploadAndProcess(
        serverUrl: 'http://localhost:8090',
        filePath: '${tmpDir.path}/test.m4a',
        config: const ProcessingConfig(),
      );

      expect(callCount, 0);
    });

    test('request includes multipart content-type', () async {
      String? receivedContentType;
      final mockClient = MockClient((request) async {
        receivedContentType = request.headers['content-type'];
        return http.Response(
          jsonEncode(_jobJson('job-1')),
          202,
          headers: {'content-type': 'application/json'},
        );
      });

      final audioFile = File('${tmpDir.path}/lang_test.m4a');
      await audioFile.create();

      final svc = UploadService(
        authService: _FakeAuthService(),
        httpClient: mockClient,
      );
      addTearDown(svc.dispose);

      await svc.uploadAndProcess(
        serverUrl: 'http://localhost:8090',
        filePath: audioFile.path,
        config: const ProcessingConfig(language: 'fr'),
      );

      expect(receivedContentType, contains('multipart/form-data'));
      svc.reset();
    });
  });

  group('UploadService.setTestStatus', () {
    test('updates status and errorMessage', () {
      final svc = UploadService(authService: _FakeAuthService());
      addTearDown(svc.dispose);

      svc.setTestStatus(UploadStatus.failed, error: 'boom');
      expect(svc.status, UploadStatus.failed);
      expect(svc.errorMessage, 'boom');
    });

    test('updates currentJob', () {
      final svc = UploadService(authService: _FakeAuthService());
      addTearDown(svc.dispose);

      final job = _makeJob(id: 'j1');
      svc.setTestStatus(UploadStatus.completed, job: job);
      expect(svc.status, UploadStatus.completed);
      expect(svc.currentJob?.id, 'j1');
    });
  });

  group('UploadService.reset', () {
    test('returns to idle and clears job and error', () {
      final svc = UploadService(authService: _FakeAuthService());
      addTearDown(svc.dispose);

      svc.setTestStatus(UploadStatus.failed, error: 'err', job: _makeJob());
      svc.reset();

      expect(svc.status, UploadStatus.idle);
      expect(svc.errorMessage, isNull);
      expect(svc.currentJob, isNull);
    });
  });
}
