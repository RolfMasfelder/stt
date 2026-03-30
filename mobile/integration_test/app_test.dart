import 'package:integration_test/integration_test.dart';

// Integration tests require a connected device (emulator/physical).
// Run with: flutter test integration_test/ -d <device_id>
//
// For headless CI, the same test scenarios are available as widget tests
// in test/e2e_test.dart and run via: flutter test test/e2e_test.dart

import '../test/e2e_test.dart' as e2e;

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  e2e.main();
}
