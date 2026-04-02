import 'package:flutter_test/flutter_test.dart';

import 'package:stt_app/models/connection_status.dart';
import 'package:stt_app/models/job_result.dart';
import 'package:stt_app/models/processing_config.dart';
import 'package:stt_app/models/recording_entry.dart';
import 'package:stt_app/models/recording_state.dart';
import 'package:stt_app/models/server_config.dart';
import 'package:stt_app/models/upload_status.dart';

void main() {
  group('ConnectionStatus', () {
    test('has three states', () {
      expect(ConnectionStatus.values.length, 3);
      expect(ConnectionStatus.values, contains(ConnectionStatus.disconnected));
      expect(ConnectionStatus.values, contains(ConnectionStatus.connected));
      expect(ConnectionStatus.values, contains(ConnectionStatus.error));
    });
  });

  group('ServerConfig', () {
    test('creates with required fields', () {
      const config = ServerConfig(serverUrl: 'https://stt.example.com');
      expect(config.serverUrl, 'https://stt.example.com');
      expect(config.verifyTls, true);
    });

    test('creates with custom verifyTls', () {
      const config = ServerConfig(
        serverUrl: 'https://local.test',
        verifyTls: false,
      );
      expect(config.verifyTls, false);
    });

    test('copyWith creates new instance', () {
      const original = ServerConfig(serverUrl: 'https://old.test');
      final updated = original.copyWith(serverUrl: 'https://new.test');
      expect(updated.serverUrl, 'https://new.test');
      expect(updated.verifyTls, true);
      expect(original.serverUrl, 'https://old.test');
    });
  });

  group('RecordingState', () {
    test('has three states', () {
      expect(RecordingState.values.length, 3);
      expect(RecordingState.values, contains(RecordingState.idle));
      expect(RecordingState.values, contains(RecordingState.recording));
      expect(RecordingState.values, contains(RecordingState.paused));
    });
  });

  group('ProcessingConfig', () {
    test('has sensible defaults', () {
      const config = ProcessingConfig();
      expect(config.language, 'auto');
      expect(config.model, 'small');
      expect(config.diarize, true);
      expect(config.summarize, true);
      expect(config.structure, true);
      expect(config.audioFormat, 'm4a');
      expect(config.sampleRate, 44100);
      expect(config.wifiOnly, true);
      expect(config.autoUpload, false);
      expect(config.storageDestination, 'device');
    });

    test('copyWith creates new instance', () {
      const original = ProcessingConfig();
      final updated = original.copyWith(model: 'large', diarize: false);
      expect(updated.model, 'large');
      expect(updated.diarize, false);
      expect(updated.language, 'auto');
      expect(original.model, 'small');
    });

    test('toJson/fromJson roundtrip', () {
      const original = ProcessingConfig(
        language: 'de',
        model: 'medium',
        diarize: false,
        summarize: false,
        structure: true,
        audioFormat: 'wav',
        sampleRate: 48000,
        wifiOnly: false,
        autoUpload: true,
        storageDestination: 'server',
      );
      final json = original.toJson();
      final restored = ProcessingConfig.fromJson(json);
      expect(restored.language, 'de');
      expect(restored.model, 'medium');
      expect(restored.diarize, false);
      expect(restored.summarize, false);
      expect(restored.structure, true);
      expect(restored.audioFormat, 'wav');
      expect(restored.sampleRate, 48000);
      expect(restored.wifiOnly, false);
      expect(restored.autoUpload, true);
      expect(restored.storageDestination, 'server');
    });

    test('fromJson with defaults for missing fields', () {
      final config = ProcessingConfig.fromJson({});
      expect(config.language, 'auto');
      expect(config.model, 'small');
      expect(config.diarize, true);
    });

    test('has language labels for all available languages', () {
      for (final lang in ProcessingConfig.availableLanguages) {
        expect(
          ProcessingConfig.languageLabels.containsKey(lang),
          true,
          reason: 'Missing label for language: $lang',
        );
      }
    });

    test('has model descriptions for all available models', () {
      for (final model in ProcessingConfig.availableModels) {
        expect(
          ProcessingConfig.modelDescriptions.containsKey(model),
          true,
          reason: 'Missing description for model: $model',
        );
      }
    });
  });

  group('UploadStatus', () {
    test('has five states', () {
      expect(UploadStatus.values.length, 5);
      expect(UploadStatus.values, contains(UploadStatus.idle));
      expect(UploadStatus.values, contains(UploadStatus.uploading));
      expect(UploadStatus.values, contains(UploadStatus.processing));
      expect(UploadStatus.values, contains(UploadStatus.completed));
      expect(UploadStatus.values, contains(UploadStatus.failed));
    });
  });

  group('JobResult', () {
    test('fromJson parses correctly', () {
      final json = {
        'id': '123e4567-e89b-12d3-a456-426614174000',
        'status': 'completed',
        'original_filename': 'test.m4a',
        'whisper_model': 'small',
        'created_at': '2025-01-01T12:00:00Z',
        'updated_at': '2025-01-01T12:05:00Z',
        'result_text': 'Hello world',
        'result_diarized_text': 'Speaker 1: Hello world',
        'result_structured_text': '## Section\nHello world',
        'result_summary': 'A greeting.',
      };
      final job = JobResult.fromJson(json);
      expect(job.id, '123e4567-e89b-12d3-a456-426614174000');
      expect(job.status, 'completed');
      expect(job.isCompleted, true);
      expect(job.isFailed, false);
      expect(job.isPending, false);
      expect(job.resultText, 'Hello world');
      expect(job.resultSummary, 'A greeting.');
    });

    test('isPending for pending and running', () {
      final pending = JobResult.fromJson({
        'id': 'abc',
        'status': 'pending',
        'created_at': '2025-01-01T12:00:00Z',
      });
      expect(pending.isPending, true);

      final running = JobResult.fromJson({
        'id': 'abc',
        'status': 'running',
        'created_at': '2025-01-01T12:00:00Z',
      });
      expect(running.isPending, true);
    });

    test('isFailed for failed status', () {
      final failed = JobResult.fromJson({
        'id': 'abc',
        'status': 'failed',
        'created_at': '2025-01-01T12:00:00Z',
        'error_message': 'Something went wrong',
      });
      expect(failed.isFailed, true);
      expect(failed.errorMessage, 'Something went wrong');
    });
  });

  group('RecordingEntry', () {
    final now = DateTime(2025, 1, 15, 10, 30);

    test('creates with required fields', () {
      final entry = RecordingEntry(
        id: 'entry-1',
        filePath: '/data/recording.m4a',
        filename: 'recording.m4a',
        createdAt: now,
        duration: const Duration(minutes: 2, seconds: 30),
      );
      expect(entry.id, 'entry-1');
      expect(entry.filename, 'recording.m4a');
      expect(entry.status, 'recorded');
      expect(entry.jobId, isNull);
      expect(entry.resultSummary, isNull);
    });

    test('copyWith updates fields', () {
      final entry = RecordingEntry(
        id: 'entry-1',
        filePath: '/data/recording.m4a',
        filename: 'recording.m4a',
        createdAt: now,
        duration: const Duration(minutes: 1),
      );
      final updated = entry.copyWith(jobId: 'job-abc', status: 'uploaded');
      expect(updated.jobId, 'job-abc');
      expect(updated.status, 'uploaded');
      expect(updated.id, 'entry-1');
      expect(updated.filename, 'recording.m4a');
    });

    test('toJson/fromJson roundtrip', () {
      final entry = RecordingEntry(
        id: 'entry-2',
        filePath: '/data/test.m4a',
        filename: 'test.m4a',
        createdAt: now,
        duration: const Duration(seconds: 90),
        jobId: 'job-xyz',
        status: 'completed',
        resultSummary: 'A test summary.',
      );
      final json = entry.toJson();
      final restored = RecordingEntry.fromJson(json);
      expect(restored.id, 'entry-2');
      expect(restored.filePath, '/data/test.m4a');
      expect(restored.filename, 'test.m4a');
      expect(restored.createdAt, now);
      expect(restored.duration.inSeconds, 90);
      expect(restored.jobId, 'job-xyz');
      expect(restored.status, 'completed');
      expect(restored.resultSummary, 'A test summary.');
    });

    test('encodeList/decodeList roundtrip', () {
      final entries = [
        RecordingEntry(
          id: 'a',
          filePath: '/a.m4a',
          filename: 'a.m4a',
          createdAt: now,
          duration: const Duration(seconds: 10),
        ),
        RecordingEntry(
          id: 'b',
          filePath: '/b.m4a',
          filename: 'b.m4a',
          createdAt: now,
          duration: const Duration(seconds: 20),
          status: 'uploaded',
        ),
      ];
      final encoded = RecordingEntry.encodeList(entries);
      final decoded = RecordingEntry.decodeList(encoded);
      expect(decoded.length, 2);
      expect(decoded[0].id, 'a');
      expect(decoded[1].status, 'uploaded');
    });
  });
}
