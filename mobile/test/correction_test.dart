import 'package:flutter_test/flutter_test.dart';

import 'package:stt_app/models/job_result.dart';
import 'package:stt_app/models/result_version.dart';
import 'package:stt_app/screens/job_detail_screen.dart';

void main() {
  group('ResultVersion', () {
    test('fromJson parses correctly', () {
      final json = {
        'id': 'v-001',
        'version': 0,
        'result_text': 'Hello',
        'result_diarized_text': '[S1] Hello',
        'result_structured_text': '# Hello',
        'result_summary': 'A greeting',
        'source': 'pipeline',
        'created_at': '2025-06-15T10:00:00Z',
      };
      final v = ResultVersion.fromJson(json);
      expect(v.id, 'v-001');
      expect(v.version, 0);
      expect(v.resultText, 'Hello');
      expect(v.resultDiarizedText, '[S1] Hello');
      expect(v.resultStructuredText, '# Hello');
      expect(v.resultSummary, 'A greeting');
      expect(v.source, 'pipeline');
    });

    test('fromJson with null optional fields', () {
      final json = {
        'id': 'v-002',
        'version': 1,
        'source': 'correction',
        'created_at': '2025-06-15T11:00:00Z',
      };
      final v = ResultVersion.fromJson(json);
      expect(v.version, 1);
      expect(v.resultText, isNull);
      expect(v.resultSummary, isNull);
      expect(v.source, 'correction');
    });

    test('fromJsonList parses a list', () {
      final jsonList = [
        {
          'id': 'v-001',
          'version': 0,
          'source': 'pipeline',
          'created_at': '2025-06-15T10:00:00Z',
        },
        {
          'id': 'v-002',
          'version': 1,
          'source': 'correction',
          'created_at': '2025-06-15T11:00:00Z',
        },
      ];
      final versions = ResultVersion.fromJsonList(jsonList);
      expect(versions.length, 2);
      expect(versions[0].version, 0);
      expect(versions[1].version, 1);
    });

    test('fromJsonList with empty list', () {
      final versions = ResultVersion.fromJsonList([]);
      expect(versions, isEmpty);
    });

    test('default source is pipeline', () {
      final json = {
        'id': 'v-003',
        'version': 0,
        'created_at': '2025-06-15T10:00:00Z',
      };
      final v = ResultVersion.fromJson(json);
      expect(v.source, 'pipeline');
    });
  });

  group('JobDetailArgs', () {
    test('holds jobId', () {
      const args = JobDetailArgs(jobId: 'abc-123');
      expect(args.jobId, 'abc-123');
    });
  });

  group('JobResult correction fields', () {
    test('completed job has all result fields', () {
      final json = {
        'id': 'job-1',
        'status': 'completed',
        'original_filename': 'test.m4a',
        'whisper_model': 'small',
        'created_at': '2025-01-01T12:00:00Z',
        'result_text': 'Transcript text',
        'result_diarized_text': '[S1] Transcript text',
        'result_structured_text': '# Structure',
        'result_summary': 'Summary of content',
      };
      final job = JobResult.fromJson(json);
      expect(job.isCompleted, true);
      expect(job.resultText, 'Transcript text');
      expect(job.resultDiarizedText, '[S1] Transcript text');
      expect(job.resultStructuredText, '# Structure');
      expect(job.resultSummary, 'Summary of content');
    });

    test('empty strings treated as non-null', () {
      final json = {
        'id': 'job-2',
        'status': 'completed',
        'created_at': '2025-01-01T12:00:00Z',
        'result_text': '',
        'result_summary': '',
      };
      final job = JobResult.fromJson(json);
      expect(job.resultText, '');
      expect(job.resultSummary, '');
    });
  });
}
