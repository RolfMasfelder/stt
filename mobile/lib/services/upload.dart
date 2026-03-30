import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/job_result.dart';
import '../models/processing_config.dart';
import '../models/upload_status.dart';
import '../services/auth.dart';
import '../services/notification.dart';

class UploadService extends ChangeNotifier {
  final AuthService _authService;

  UploadStatus _status = UploadStatus.idle;
  double _progress = 0.0;
  JobResult? _currentJob;
  String? _errorMessage;
  Timer? _pollTimer;

  UploadStatus get status => _status;
  double get progress => _progress;
  JobResult? get currentJob => _currentJob;
  String? get errorMessage => _errorMessage;

  UploadService({required AuthService authService})
      : _authService = authService;

  /// Upload audio file and start async processing job.
  Future<void> uploadAndProcess({
    required String serverUrl,
    required String filePath,
    required ProcessingConfig config,
  }) async {
    if (_status == UploadStatus.uploading ||
        _status == UploadStatus.processing) {
      return;
    }

    _status = UploadStatus.uploading;
    _progress = 0.0;
    _errorMessage = null;
    _currentJob = null;
    notifyListeners();

    try {
      final headers = await _authService.getAuthHeaders();
      final uri = Uri.parse('$serverUrl/v1/jobs');

      final request = http.MultipartRequest('POST', uri)
        ..headers.addAll(headers)
        ..fields['model'] = config.model
        ..fields['diarize'] = config.diarize.toString()
        ..files.add(await http.MultipartFile.fromPath('file', filePath));

      final streamedResponse = await request.send();
      _progress = 1.0;
      notifyListeners();

      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 202) {
        final body = jsonDecode(response.body) as Map<String, dynamic>;
        _currentJob = JobResult.fromJson(body);
        _status = UploadStatus.processing;
        notifyListeners();
        _startPolling(serverUrl);
      } else {
        _status = UploadStatus.failed;
        _errorMessage = 'Upload fehlgeschlagen (${response.statusCode})';
        notifyListeners();
      }
    } catch (e) {
      _status = UploadStatus.failed;
      _errorMessage = 'Verbindungsfehler: $e';
      notifyListeners();
    }
  }

  void _startPolling(String serverUrl) {
    _pollTimer?.cancel();
    _pollTimer = Timer.periodic(const Duration(seconds: 3), (_) async {
      await _pollJobStatus(serverUrl);
    });
  }

  Future<void> _pollJobStatus(String serverUrl) async {
    if (_currentJob == null) return;

    try {
      final headers = await _authService.getAuthHeaders();
      final uri = Uri.parse('$serverUrl/v1/jobs/${_currentJob!.id}');
      final response = await http.get(uri, headers: headers).timeout(
        const Duration(seconds: 10),
      );

      if (response.statusCode == 200) {
        final body = jsonDecode(response.body) as Map<String, dynamic>;
        _currentJob = JobResult.fromJson(body);

        if (_currentJob!.isCompleted) {
          _status = UploadStatus.completed;
          _pollTimer?.cancel();
          NotificationService().showProcessingComplete(
            filename: _currentJob!.originalFilename,
            summary: _currentJob!.resultSummary,
          );
        } else if (_currentJob!.isFailed) {
          _status = UploadStatus.failed;
          _errorMessage = _currentJob!.errorMessage ?? 'Verarbeitung fehlgeschlagen';
          _pollTimer?.cancel();
          NotificationService().showProcessingFailed(
            filename: _currentJob!.originalFilename,
            error: _errorMessage,
          );
        }
        notifyListeners();
      }
    } catch (e) {
      debugPrint('Job polling error: $e');
    }
  }

  /// Save result text to a local file.
  Future<String?> saveResultToFile(String outputPath, String content) async {
    try {
      final file = File(outputPath);
      await file.writeAsString(content);
      return outputPath;
    } catch (e) {
      debugPrint('Save failed: $e');
      return null;
    }
  }

  void reset() {
    _pollTimer?.cancel();
    _status = UploadStatus.idle;
    _progress = 0.0;
    _currentJob = null;
    _errorMessage = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }
}
