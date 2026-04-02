import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../models/connection_status.dart';
import '../models/server_config.dart';

class ServerConnectionService extends ChangeNotifier {
  ServerConfig? _config;
  ConnectionStatus _status = ConnectionStatus.disconnected;
  Timer? _healthTimer;
  // ignore: unused_field
  Map<String, String> Function()? _authHeadersProvider;

  ServerConfig? get config => _config;
  ConnectionStatus get status => _status;

  ServerConnectionService() {
    _loadConfig();
  }

  /// Set a callback providing auth headers for authenticated health checks.
  void setAuthHeadersProvider(Map<String, String> Function() provider) {
    _authHeadersProvider = provider;
  }

  Future<void> _loadConfig() async {
    final prefs = await SharedPreferences.getInstance();
    final url = prefs.getString('server_url');
    final verifyTls = prefs.getBool('verify_tls') ?? true;
    if (url != null && url.isNotEmpty) {
      _config = ServerConfig(serverUrl: url, verifyTls: verifyTls);
      _startHealthCheck();
      notifyListeners();
    }
  }

  Future<void> updateConfig(ServerConfig config) async {
    _config = config;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('server_url', config.serverUrl);
    await prefs.setBool('verify_tls', config.verifyTls);
    _startHealthCheck();
    notifyListeners();
  }

  void _startHealthCheck() {
    _healthTimer?.cancel();
    _checkHealth();
    _healthTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => _checkHealth(),
    );
  }

  Future<void> _checkHealth() async {
    if (_config == null) {
      _status = ConnectionStatus.disconnected;
      notifyListeners();
      return;
    }

    try {
      final uri = Uri.parse('${_config!.serverUrl}/health');
      final response = await http.get(uri).timeout(const Duration(seconds: 5));
      if (response.statusCode == 200) {
        final body = jsonDecode(response.body);
        _status = body['status'] == 'healthy'
            ? ConnectionStatus.connected
            : ConnectionStatus.error;
      } else {
        _status = ConnectionStatus.error;
      }
    } catch (_) {
      _status = ConnectionStatus.error;
    }
    notifyListeners();
  }

  Future<void> testConnection() async {
    await _checkHealth();
  }

  @override
  void dispose() {
    _healthTimer?.cancel();
    super.dispose();
  }
}
