import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:stt_app/services/connectivity.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  setUp(() {
    // Mock the connectivity plugin method channel
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('dev.fluttercommunity.plus/connectivity'),
      (methodCall) async {
        if (methodCall.method == 'check') {
          return ['none'];
        }
        return null;
      },
    );
  });

  tearDown(() {
    TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
        .setMockMethodCallHandler(
      const MethodChannel('dev.fluttercommunity.plus/connectivity'),
      null,
    );
  });

  group('ConnectivityService', () {
    test('initial state before async init', () {
      final service = ConnectivityService();
      // Before async init completes, results are empty
      expect(service.isOnWifi, false);
      expect(service.isOnMobile, false);
    });

    test('canUpload returns false when offline', () {
      final service = ConnectivityService();
      // Empty results = offline
      expect(service.canUpload(wifiOnly: false), false);
      expect(service.canUpload(wifiOnly: true), false);
    });
  });
}
