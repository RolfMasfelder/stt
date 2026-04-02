import 'dart:async';

import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';

class ConnectivityService extends ChangeNotifier {
  final Connectivity _connectivity = Connectivity();
  StreamSubscription<List<ConnectivityResult>>? _subscription;
  List<ConnectivityResult> _results = [];

  bool get isOnline => _results.any((r) => r != ConnectivityResult.none);
  bool get isOnWifi => _results.contains(ConnectivityResult.wifi);
  bool get isOnMobile => _results.contains(ConnectivityResult.mobile);

  ConnectivityService() {
    _init();
  }

  Future<void> _init() async {
    _results = await _connectivity.checkConnectivity();
    notifyListeners();
    _subscription = _connectivity.onConnectivityChanged.listen((results) {
      _results = results;
      notifyListeners();
    });
  }

  /// Check if upload is allowed given the wifiOnly preference.
  bool canUpload({required bool wifiOnly}) {
    if (!isOnline) return false;
    if (wifiOnly && !isOnWifi) return false;
    return true;
  }

  @override
  void dispose() {
    _subscription?.cancel();
    super.dispose();
  }
}
