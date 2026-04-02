import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/job_result.dart';
import '../models/processing_config.dart';
import '../models/result_version.dart';
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
      final response = await http
          .get(uri, headers: headers)
          .timeout(const Duration(seconds: 10));

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
          _errorMessage =
              _currentJob!.errorMessage ?? 'Verarbeitung fehlgeschlagen';
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

  /// Fetch full job details from the server.
  Future<JobResult?> fetchJob({
    required String serverUrl,
    required String jobId,
  }) async {
    try {
      final headers = await _authService.getAuthHeaders();
      final uri = Uri.parse('$serverUrl/v1/jobs/$jobId');
      final response = await http
          .get(uri, headers: headers)
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final body = jsonDecode(response.body) as Map<String, dynamic>;
        return JobResult.fromJson(body);
      }
    } catch (e) {
      debugPrint('Fetch job error: $e');
    }
    return null;
  }

  /// Correct job result fields via PATCH /v1/jobs/{id}/correct.
  Future<JobResult?> correctJob({
    required String serverUrl,
    required String jobId,
    required Map<String, String> fields,
  }) async {
    try {
      final headers = await _authService.getAuthHeaders();
      headers['Content-Type'] = 'application/json';
      final uri = Uri.parse('$serverUrl/v1/jobs/$jobId/correct');
      final response = await http
          .patch(uri, headers: headers, body: jsonEncode(fields))
          .timeout(const Duration(seconds: 30));

      if (response.statusCode == 200) {
        final body = jsonDecode(response.body) as Map<String, dynamic>;
        return JobResult.fromJson(body);
      }
    } catch (e) {
      debugPrint('Correct job error: $e');
    }
    return null;
  }

  /// Re-run pipeline steps via POST /v1/jobs/{id}/reprocess.
  Future<JobResult?> reprocessJob({
    required String serverUrl,
    required String jobId,
    required List<String> steps,
  }) async {
    try {
      final headers = await _authService.getAuthHeaders();
      headers['Content-Type'] = 'application/json';
      final uri = Uri.parse('$serverUrl/v1/jobs/$jobId/reprocess');
      final response = await http
          .post(uri, headers: headers, body: jsonEncode({'steps': steps}))
          .timeout(const Duration(seconds: 120));

      if (response.statusCode == 200) {
        final body = jsonDecode(response.body) as Map<String, dynamic>;
        return JobResult.fromJson(body);
      }
    } catch (e) {
      debugPrint('Reprocess job error: $e');
    }
    return null;
  }

  /// Fetch version history via GET /v1/jobs/{id}/versions.
  Future<List<ResultVersion>> fetchVersions({
    required String serverUrl,
    required String jobId,
  }) async {
    try {
      final headers = await _authService.getAuthHeaders();
      final uri = Uri.parse('$serverUrl/v1/jobs/$jobId/versions');
      final response = await http
          .get(uri, headers: headers)
          .timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final body = jsonDecode(response.body) as List<dynamic>;
        return ResultVersion.fromJsonList(body);
      }
    } catch (e) {
      debugPrint('Fetch versions error: $e');
    }
    return [];
  }

  void reset() {
    _pollTimer?.cancel();
    _status = UploadStatus.idle;
    _progress = 0.0;
    _currentJob = null;
    _errorMessage = null;
    notifyListeners();
  }

  /// Only for integration / widget tests.
  @visibleForTesting
  void setTestStatus(UploadStatus status, {String? error}) {
    _status = status;
    _errorMessage = error;
    notifyListeners();
  }

  @override
  void dispose() {
    _pollTimer?.cancel();
    super.dispose();
  }
}
