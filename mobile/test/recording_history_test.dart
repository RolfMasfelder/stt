import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:stt_app/models/recording_entry.dart';
import 'package:stt_app/services/recording_history.dart';

RecordingEntry _entry({
  String id = '1',
  String? jobId,
  String status = 'recorded',
}) {
  return RecordingEntry(
    id: id,
    filePath: '/tmp/$id.m4a',
    filename: '$id.m4a',
    createdAt: DateTime(2024, 1, 1),
    duration: const Duration(seconds: 10),
    jobId: jobId,
    status: status,
  );
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('RecordingHistoryService', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    test('starts empty', () async {
      final svc = RecordingHistoryService();
      await Future<void>.delayed(Duration.zero);
      expect(svc.entries, isEmpty);
      expect(svc.count, 0);
    });

    test('add() inserts entry and increases count', () async {
      final svc = RecordingHistoryService();
      await Future<void>.delayed(Duration.zero);

      await svc.add(_entry(id: 'a'));
      expect(svc.count, 1);
      expect(svc.entries.first.id, 'a');
    });

    test('add() inserts at the front (newest first)', () async {
      final svc = RecordingHistoryService();
      await Future<void>.delayed(Duration.zero);

      await svc.add(_entry(id: '1'));
      await svc.add(_entry(id: '2'));
      expect(svc.entries.first.id, '2');
    });

    test('remove() decreases count', () async {
      final svc = RecordingHistoryService();
      await Future<void>.delayed(Duration.zero);

      await svc.add(_entry(id: 'x'));
      await svc.remove('x');
      expect(svc.count, 0);
    });

    test('remove() ignores unknown id', () async {
      final svc = RecordingHistoryService();
      await Future<void>.delayed(Duration.zero);

      await svc.add(_entry(id: 'x'));
      await svc.remove('unknown');
      expect(svc.count, 1);
    });

    test('updateEntry() modifies matching entry', () async {
      final svc = RecordingHistoryService();
      await Future<void>.delayed(Duration.zero);

      await svc.add(_entry(id: 'u', status: 'recorded'));
      await svc.updateEntry('u', _entry(id: 'u', status: 'completed'));
      expect(svc.findById('u')?.status, 'completed');
    });

    test('findById() returns correct entry', () async {
      final svc = RecordingHistoryService();
      await Future<void>.delayed(Duration.zero);

      await svc.add(_entry(id: 'find-me'));
      expect(svc.findById('find-me')?.id, 'find-me');
      expect(svc.findById('missing'), isNull);
    });

    test('findByJobId() returns correct entry', () async {
      final svc = RecordingHistoryService();
      await Future<void>.delayed(Duration.zero);

      await svc.add(_entry(id: '1', jobId: 'job-abc'));
      expect(svc.findByJobId('job-abc')?.id, '1');
      expect(svc.findByJobId('job-xyz'), isNull);
    });

    test('entries are persisted and reloaded', () async {
      final svc1 = RecordingHistoryService();
      await Future<void>.delayed(Duration.zero);
      await svc1.add(_entry(id: 'persist-me'));

      // A second instance reads from the same SharedPreferences mock.
      final svc2 = RecordingHistoryService();
      await Future<void>.delayed(Duration.zero);
      expect(svc2.count, 1);
      expect(svc2.entries.first.id, 'persist-me');
    });

    test('entries returns unmodifiable list', () async {
      final svc = RecordingHistoryService();
      await Future<void>.delayed(Duration.zero);

      await svc.add(_entry(id: '1'));
      expect(() => svc.entries.add(_entry(id: '2')), throwsUnsupportedError);
      expect(svc.count, 1);
    });
  });
}
