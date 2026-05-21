import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:stt_app/models/processing_config.dart';
import 'package:stt_app/services/processing_config.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('ProcessingConfigService – defaults', () {
    test('default language is auto', () {
      final svc = ProcessingConfigService();
      expect(svc.config.language, 'auto');
    });

    test('default model is small', () {
      final svc = ProcessingConfigService();
      expect(svc.config.model, 'small');
    });

    test('diarize/summarize/structure all enabled by default', () {
      final svc = ProcessingConfigService();
      expect(svc.config.diarize, isTrue);
      expect(svc.config.summarize, isTrue);
      expect(svc.config.structure, isTrue);
    });

    test('wifiOnly true, autoUpload false by default', () {
      final svc = ProcessingConfigService();
      expect(svc.config.wifiOnly, isTrue);
      expect(svc.config.autoUpload, isFalse);
    });

    test('storageDestination defaults to device', () {
      final svc = ProcessingConfigService();
      expect(svc.config.storageDestination, 'device');
    });
  });

  group('ProcessingConfigService – update', () {
    test('update() changes config immediately', () async {
      final svc = ProcessingConfigService();
      await svc.update(svc.config.copyWith(diarize: false));
      expect(svc.config.diarize, isFalse);
    });

    test('update() notifies listeners', () async {
      final svc = ProcessingConfigService();
      var notified = false;
      svc.addListener(() => notified = true);

      await svc.update(svc.config.copyWith(summarize: false));

      expect(notified, isTrue);
    });

    test('update() persists to SharedPreferences', () async {
      final svc = ProcessingConfigService();
      await svc.update(
        svc.config.copyWith(model: 'large-v3', structure: false),
      );

      // New instance loads persisted values
      final svc2 = ProcessingConfigService();
      await Future<void>.delayed(Duration.zero); // wait for async _load()
      expect(svc2.config.model, 'large-v3');
      expect(svc2.config.structure, isFalse);
    });

    test('disabling all LLM options leaves transcription intact', () async {
      final svc = ProcessingConfigService();
      await svc.update(
        svc.config.copyWith(diarize: false, summarize: false, structure: false),
      );
      expect(svc.config.diarize, isFalse);
      expect(svc.config.summarize, isFalse);
      expect(svc.config.structure, isFalse);
      // Language and model remain as configured
      expect(svc.config.language, 'auto');
      expect(svc.config.model, 'small');
    });
  });

  group('ProcessingConfig – serialisation round-trip', () {
    test('toJson / fromJson preserves all fields', () {
      const cfg = ProcessingConfig(
        language: 'de',
        model: 'medium',
        diarize: false,
        summarize: true,
        structure: false,
        audioFormat: 'wav',
        sampleRate: 16000,
        wifiOnly: false,
        autoUpload: true,
        storageDestination: 'some-uuid',
      );

      final json = cfg.toJson();
      final restored = ProcessingConfig.fromJson(json);

      expect(restored.language, cfg.language);
      expect(restored.model, cfg.model);
      expect(restored.diarize, cfg.diarize);
      expect(restored.summarize, cfg.summarize);
      expect(restored.structure, cfg.structure);
      expect(restored.audioFormat, cfg.audioFormat);
      expect(restored.sampleRate, cfg.sampleRate);
      expect(restored.wifiOnly, cfg.wifiOnly);
      expect(restored.autoUpload, cfg.autoUpload);
      expect(restored.storageDestination, cfg.storageDestination);
    });

    test('fromJson falls back to defaults for missing fields', () {
      final cfg = ProcessingConfig.fromJson({});
      expect(cfg.language, 'auto');
      expect(cfg.model, 'small');
      expect(cfg.diarize, isTrue);
      expect(cfg.wifiOnly, isTrue);
    });

    test('copyWith only changes specified fields', () {
      const orig = ProcessingConfig();
      final modified = orig.copyWith(model: 'large-v3', diarize: false);

      expect(modified.model, 'large-v3');
      expect(modified.diarize, isFalse);
      // Unchanged fields keep original values
      expect(modified.language, orig.language);
      expect(modified.summarize, orig.summarize);
      expect(modified.structure, orig.structure);
    });
  });

  group('ProcessingConfig – option combinations', () {
    // Representative combinations of the three bool flags
    final cases = <Map<String, Object>>[
      {'diarize': true, 'summarize': true, 'structure': true},
      {'diarize': false, 'summarize': false, 'structure': false},
      {'diarize': true, 'summarize': false, 'structure': false},
      {'diarize': false, 'summarize': true, 'structure': false},
      {'diarize': false, 'summarize': false, 'structure': true},
      {'diarize': true, 'summarize': true, 'structure': false},
      {'diarize': false, 'summarize': true, 'structure': true},
    ];

    for (final c in cases) {
      test('round-trip: diarize=${c['diarize']} summarize=${c['summarize']} '
          'structure=${c['structure']}', () {
        final cfg = ProcessingConfig(
          diarize: c['diarize']! as bool,
          summarize: c['summarize']! as bool,
          structure: c['structure']! as bool,
        );
        final restored = ProcessingConfig.fromJson(cfg.toJson());
        expect(restored.diarize, cfg.diarize);
        expect(restored.summarize, cfg.summarize);
        expect(restored.structure, cfg.structure);
      });
    }
  });
}
