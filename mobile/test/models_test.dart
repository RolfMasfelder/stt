import 'package:flutter_test/flutter_test.dart';

import 'package:stt_app/models/connection_status.dart';
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
}
