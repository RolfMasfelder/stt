import 'package:flutter_test/flutter_test.dart';
import 'package:stt_app/services/auth.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('AuthState', () {
    test('default state is not authenticated', () {
      const state = AuthState();
      expect(state.isAuthenticated, false);
      expect(state.accessToken, null);
      expect(state.refreshToken, null);
      expect(state.expiresAt, null);
    });

    test('authenticated state', () {
      final state = AuthState(
        isAuthenticated: true,
        accessToken: 'test-token',
        refreshToken: 'test-refresh',
        expiresAt: DateTime.now().add(const Duration(minutes: 15)),
      );
      expect(state.isAuthenticated, true);
      expect(state.isExpired, false);
    });

    test('expired state', () {
      final state = AuthState(
        isAuthenticated: true,
        accessToken: 'test-token',
        refreshToken: 'test-refresh',
        expiresAt: DateTime.now().subtract(const Duration(minutes: 1)),
      );
      expect(state.isExpired, true);
    });

    test('no expiry means not expired', () {
      const state = AuthState(isAuthenticated: true, accessToken: 'test-token');
      expect(state.isExpired, false);
    });
  });

  group('AuthService', () {
    test('initial state is not authenticated', () {
      final service = AuthService();
      expect(service.isAuthenticated, false);
      expect(service.accessToken, null);
    });
  });
}
