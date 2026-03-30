import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

import '../models/recording_state.dart';

class AudioRecordingService extends ChangeNotifier {
  final AudioRecorder _recorder = AudioRecorder();
  RecordingState _state = RecordingState.idle;
  Duration _duration = Duration.zero;
  double _amplitude = 0.0;
  String? _filePath;
  Timer? _durationTimer;
  Timer? _amplitudeTimer;

  RecordingState get state => _state;
  Duration get duration => _duration;
  double get amplitude => _amplitude;
  String? get filePath => _filePath;
  bool get isRecording => _state == RecordingState.recording;
  bool get isPaused => _state == RecordingState.paused;

  Future<bool> hasPermission() async {
    return await _recorder.hasPermission();
  }

  Future<void> start() async {
    if (_state != RecordingState.idle) return;

    final hasPerms = await _recorder.hasPermission();
    if (!hasPerms) return;

    final dir = await getApplicationDocumentsDirectory();
    final timestamp = DateTime.now().millisecondsSinceEpoch;
    _filePath = '${dir.path}/recording_$timestamp.m4a';

    await _recorder.start(
      const RecordConfig(
        encoder: AudioEncoder.aacLc,
        sampleRate: 44100,
        bitRate: 128000,
        numChannels: 1,
      ),
      path: _filePath!,
    );

    _state = RecordingState.recording;
    _duration = Duration.zero;
    _startTimers();
    notifyListeners();
  }

  Future<void> pause() async {
    if (_state != RecordingState.recording) return;
    await _recorder.pause();
    _state = RecordingState.paused;
    _stopTimers();
    notifyListeners();
  }

  Future<void> resume() async {
    if (_state != RecordingState.paused) return;
    await _recorder.resume();
    _state = RecordingState.recording;
    _startTimers();
    notifyListeners();
  }

  Future<String?> stop() async {
    if (_state == RecordingState.idle) return null;
    final path = await _recorder.stop();
    _state = RecordingState.idle;
    _stopTimers();
    _amplitude = 0.0;
    notifyListeners();
    return path;
  }

  Future<void> cancel() async {
    final path = await stop();
    if (path != null) {
      // File cleanup handled by caller if needed
      _filePath = null;
    }
  }

  void _startTimers() {
    _durationTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      _duration += const Duration(seconds: 1);
      notifyListeners();
    });

    _amplitudeTimer = Timer.periodic(
      const Duration(milliseconds: 200),
      (_) async {
        final amp = await _recorder.getAmplitude();
        // Normalize from dB (-160..0) to 0..1
        _amplitude = ((amp.current + 60) / 60).clamp(0.0, 1.0);
        notifyListeners();
      },
    );
  }

  void _stopTimers() {
    _durationTimer?.cancel();
    _amplitudeTimer?.cancel();
  }

  @override
  void dispose() {
    _stopTimers();
    _recorder.dispose();
    super.dispose();
  }
}
