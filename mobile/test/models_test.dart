import 'package:flutter_test/flutter_test.dart';

import 'package:stt_app/models/connection_status.dart';
import 'package:stt_app/models/processing_config.dart';
import 'package:stt_app/models/recording_state.dart';
import 'package:stt_app/models/server_config.dart';

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
    });

    test('fromJson with defaults for missing fields', () {
      final config = ProcessingConfig.fromJson({});
      expect(config.language, 'auto');
      expect(config.model, 'small');
      expect(config.diarize, true);
    });

    test('has language labels for all available languages', () {
      for (final lang in ProcessingConfig.availableLanguages) {
        expect(ProcessingConfig.languageLabels.containsKey(lang), true,
            reason: 'Missing label for language: $lang');
      }
    });

    test('has model descriptions for all available models', () {
      for (final model in ProcessingConfig.availableModels) {
        expect(ProcessingConfig.modelDescriptions.containsKey(model), true,
            reason: 'Missing description for model: $model');
      }
    });
  });
}
