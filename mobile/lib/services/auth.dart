import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter_appauth/flutter_appauth.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class AuthState {
  final bool isAuthenticated;
  final String? accessToken;
  final String? refreshToken;
  final DateTime? expiresAt;

  const AuthState({
    this.isAuthenticated = false,
    this.accessToken,
    this.refreshToken,
    this.expiresAt,
  });

  bool get isExpired =>
      expiresAt != null && DateTime.now().isAfter(expiresAt!);
}

class AuthService extends ChangeNotifier {
  static const _redirectUri = 'stt.app://callback';
  static const _scopes = ['read', 'write'];

  static const _keyAccessToken = 'auth_access_token';
  static const _keyRefreshToken = 'auth_refresh_token';
  static const _keyExpiresAt = 'auth_expires_at';
  static const _keyClientId = 'auth_client_id';
  static const _keyIssuer = 'auth_issuer';

  final FlutterAppAuth _appAuth = const FlutterAppAuth();
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  AuthState _state = const AuthState();
  Timer? _refreshTimer;

  AuthState get state => _state;
  bool get isAuthenticated => _state.isAuthenticated && !_state.isExpired;
  String? get accessToken => _state.accessToken;

  AuthService() {
    _loadStoredTokens();
  }

  Future<void> _loadStoredTokens() async {
    final accessToken = await _storage.read(key: _keyAccessToken);
    final refreshToken = await _storage.read(key: _keyRefreshToken);
    final expiresAtStr = await _storage.read(key: _keyExpiresAt);

    if (accessToken != null && refreshToken != null) {
      final expiresAt = expiresAtStr != null
          ? DateTime.tryParse(expiresAtStr)
          : null;

      _state = AuthState(
        isAuthenticated: true,
        accessToken: accessToken,
        refreshToken: refreshToken,
        expiresAt: expiresAt,
      );

      if (_state.isExpired) {
        await _refreshAccessToken();
      } else {
        _scheduleRefresh();
      }
      notifyListeners();
    }
  }

  Future<bool> login({
    required String serverUrl,
    required String clientId,
  }) async {
    try {
      final issuer = serverUrl.endsWith('/') ? '${serverUrl}o' : '$serverUrl/o';

      final result = await _appAuth.authorizeAndExchangeCode(
        AuthorizationTokenRequest(
          clientId,
          _redirectUri,
          serviceConfiguration: AuthorizationServiceConfiguration(
            authorizationEndpoint: '$issuer/authorize/',
            tokenEndpoint: '$issuer/token/',
          ),
          scopes: _scopes,
        ),
      );

      await _storeTokens(
        accessToken: result.accessToken!,
        refreshToken: result.refreshToken!,
        expiresAt: result.accessTokenExpirationDateTime,
        clientId: clientId,
        issuer: issuer,
      );

      _state = AuthState(
        isAuthenticated: true,
        accessToken: result.accessToken,
        refreshToken: result.refreshToken,
        expiresAt: result.accessTokenExpirationDateTime,
      );

      _scheduleRefresh();
      notifyListeners();
      return true;
    } catch (e) {
      debugPrint('OAuth2 login failed: $e');
      return false;
    }
  }

  Future<void> _refreshAccessToken() async {
    final refreshToken = await _storage.read(key: _keyRefreshToken);
    final clientId = await _storage.read(key: _keyClientId);
    final issuer = await _storage.read(key: _keyIssuer);

    if (refreshToken == null || clientId == null || issuer == null) {
      await logout();
      return;
    }

    try {
      final result = await _appAuth.token(
        TokenRequest(
          clientId,
          _redirectUri,
          serviceConfiguration: AuthorizationServiceConfiguration(
            authorizationEndpoint: '$issuer/authorize/',
            tokenEndpoint: '$issuer/token/',
          ),
          refreshToken: refreshToken,
          scopes: _scopes,
        ),
      );

      await _storeTokens(
        accessToken: result.accessToken!,
        refreshToken: result.refreshToken!,
        expiresAt: result.accessTokenExpirationDateTime,
        clientId: clientId,
        issuer: issuer,
      );

      _state = AuthState(
        isAuthenticated: true,
        accessToken: result.accessToken,
        refreshToken: result.refreshToken,
        expiresAt: result.accessTokenExpirationDateTime,
      );

      _scheduleRefresh();
      notifyListeners();
    } catch (e) {
      debugPrint('Token refresh failed: $e');
      await logout();
    }
  }

  Future<void> logout() async {
    _refreshTimer?.cancel();
    await _storage.deleteAll();
    _state = const AuthState();
    notifyListeners();
  }

  void _scheduleRefresh() {
    _refreshTimer?.cancel();
    if (_state.expiresAt == null) return;

    // Refresh 60 seconds before expiry
    final refreshAt = _state.expiresAt!.subtract(const Duration(seconds: 60));
    final delay = refreshAt.difference(DateTime.now());

    if (delay.isNegative) {
      _refreshAccessToken();
    } else {
      _refreshTimer = Timer(delay, _refreshAccessToken);
    }
  }

  Future<void> _storeTokens({
    required String accessToken,
    required String refreshToken,
    DateTime? expiresAt,
    required String clientId,
    required String issuer,
  }) async {
    await _storage.write(key: _keyAccessToken, value: accessToken);
    await _storage.write(key: _keyRefreshToken, value: refreshToken);
    if (expiresAt != null) {
      await _storage.write(
        key: _keyExpiresAt,
        value: expiresAt.toIso8601String(),
      );
    }
    await _storage.write(key: _keyClientId, value: clientId);
    await _storage.write(key: _keyIssuer, value: issuer);
  }

  /// Returns auth headers for API requests. Auto-refreshes if expired.
  Future<Map<String, String>> getAuthHeaders() async {
    if (!_state.isAuthenticated) return {};
    if (_state.isExpired) {
      await _refreshAccessToken();
    }
    if (_state.accessToken == null) return {};
    return {'Authorization': 'Bearer ${_state.accessToken}'};
  }

  @override
  void dispose() {
    _refreshTimer?.cancel();
    super.dispose();
  }
}
