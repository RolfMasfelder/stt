import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/recording_entry.dart';

class RecordingHistoryService extends ChangeNotifier {
  static const _storageKey = 'recording_history';
  List<RecordingEntry> _entries = [];

  List<RecordingEntry> get entries => List.unmodifiable(_entries);
  int get count => _entries.length;

  RecordingHistoryService() {
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    final json = prefs.getString(_storageKey);
    if (json != null) {
      _entries = RecordingEntry.decodeList(json);
      notifyListeners();
    }
  }

  Future<void> add(RecordingEntry entry) async {
    _entries.insert(0, entry);
    await _save();
    notifyListeners();
  }

  Future<void> updateEntry(String id, RecordingEntry updated) async {
    final index = _entries.indexWhere((e) => e.id == id);
    if (index >= 0) {
      _entries[index] = updated;
      await _save();
      notifyListeners();
    }
  }

  Future<void> remove(String id) async {
    _entries.removeWhere((e) => e.id == id);
    await _save();
    notifyListeners();
  }

  RecordingEntry? findByJobId(String jobId) {
    try {
      return _entries.firstWhere((e) => e.jobId == jobId);
    } catch (_) {
      return null;
    }
  }

  RecordingEntry? findById(String id) {
    try {
      return _entries.firstWhere((e) => e.id == id);
    } catch (_) {
      return null;
    }
  }

  Future<void> _save() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_storageKey, RecordingEntry.encodeList(_entries));
  }
}
