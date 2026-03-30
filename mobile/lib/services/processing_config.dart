import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/processing_config.dart';

class ProcessingConfigService extends ChangeNotifier {
  ProcessingConfig _config = const ProcessingConfig();

  ProcessingConfig get config => _config;

  ProcessingConfigService() {
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final json = prefs.getString('processing_config');
    if (json != null) {
      _config = ProcessingConfig.fromJson(
        jsonDecode(json) as Map<String, dynamic>,
      );
      notifyListeners();
    }
  }

  Future<void> update(ProcessingConfig config) async {
    _config = config;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('processing_config', jsonEncode(config.toJson()));
    notifyListeners();
  }
}
