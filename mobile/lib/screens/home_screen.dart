import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/connection_status.dart';
import '../models/recording_entry.dart';
import '../models/recording_state.dart';
import '../models/upload_status.dart';
import '../services/audio_recording.dart';
import '../services/auth.dart';
import '../services/connectivity.dart';
import '../services/processing_config.dart';
import '../services/recording_history.dart';
import '../services/server_connection.dart';
import '../services/upload.dart';
import '../widgets/hal_eye.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  String _statusText(ConnectionStatus status, RecordingState recording) {
    if (recording == RecordingState.recording) return 'Aufnahme...';
    if (recording == RecordingState.paused) return 'Pausiert';
    switch (status) {
      case ConnectionStatus.disconnected:
        return 'Nicht verbunden';
      case ConnectionStatus.connected:
        return 'Bereit';
      case ConnectionStatus.error:
        return 'Verbindungsfehler';
    }
  }

  String _formatDuration(Duration d) {
    final hours = d.inHours;
    final minutes = d.inMinutes.remainder(60).toString().padLeft(2, '0');
    final seconds = d.inSeconds.remainder(60).toString().padLeft(2, '0');
    if (hours > 0) return '$hours:$minutes:$seconds';
    return '$minutes:$seconds';
  }

  @override
  Widget build(BuildContext context) {
    final connection = context.watch<ServerConnectionService>();
    final recorder = context.watch<AudioRecordingService>();
    final upload = context.watch<UploadService>();
    final auth = context.watch<AuthService>();

    return Scaffold(
      appBar: AppBar(
        title: const Text('STT'),
        actions: [
          IconButton(
            icon: const Icon(Icons.history),
            onPressed: () => Navigator.pushNamed(context, '/history'),
          ),
          IconButton(
            icon: const Icon(Icons.settings),
            onPressed: () => Navigator.pushNamed(context, '/settings'),
          ),
        ],
      ),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            // HAL-9000 Eye — tap to toggle recording
            GestureDetector(
              onTap: () => _onEyeTap(context, connection, recorder, auth),
              child: HalEye(
                status: connection.status,
                size: 200.0,
                recording: recorder.isRecording,
              ),
            ),
            const SizedBox(height: 24),

            // Status text
            Text(
              _statusText(connection.status, recorder.state),
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: recorder.isRecording
                    ? Colors.red
                    : connection.status == ConnectionStatus.connected
                    ? Colors.green
                    : connection.status == ConnectionStatus.error
                    ? Colors.red
                    : Colors.grey,
              ),
            ),

            // Duration display during recording
            if (recorder.state != RecordingState.idle) ...[
              const SizedBox(height: 8),
              Text(
                _formatDuration(recorder.duration),
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                  color: Colors.white70,
                  fontFeatures: [const FontFeature.tabularFigures()],
                ),
              ),
              const SizedBox(height: 24),

              // Recording controls
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  // Pause/Resume
                  IconButton.filled(
                    onPressed: () {
                      if (recorder.isRecording) {
                        recorder.pause();
                      } else {
                        recorder.resume();
                      }
                    },
                    icon: Icon(
                      recorder.isPaused ? Icons.play_arrow : Icons.pause,
                    ),
                    iconSize: 32,
                  ),
                  const SizedBox(width: 24),
                  // Stop
                  IconButton.filled(
                    onPressed: () => _onStop(context, recorder),
                    icon: const Icon(Icons.stop),
                    iconSize: 32,
                    style: IconButton.styleFrom(
                      backgroundColor: Colors.red.shade800,
                    ),
                  ),
                ],
              ),
            ],

            // Server URL
            if (recorder.state == RecordingState.idle &&
                connection.config != null &&
                upload.status == UploadStatus.idle) ...[
              const SizedBox(height: 8),
              Text(
                connection.config!.serverUrl,
                style: Theme.of(
                  context,
                ).textTheme.bodySmall?.copyWith(color: Colors.grey),
              ),
            ],

            // Upload / Processing status
            if (upload.status != UploadStatus.idle &&
                recorder.state == RecordingState.idle) ...[
              const SizedBox(height: 24),
              _buildUploadStatus(context, upload),
              if (upload.status == UploadStatus.failed &&
                  upload.errorMessage == 'Nicht angemeldet') ...[
                const SizedBox(height: 8),
                TextButton.icon(
                  onPressed: () => Navigator.pushNamed(context, '/settings'),
                  icon: const Icon(Icons.login),
                  label: const Text('Einloggen'),
                ),
              ],
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _onEyeTap(
    BuildContext context,
    ServerConnectionService connection,
    AudioRecordingService recorder,
    AuthService auth,
  ) async {
    if (recorder.state != RecordingState.idle) return;

    if (!auth.isAuthenticated) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: const Text('Bitte zuerst einloggen'),
          action: SnackBarAction(
            label: 'Einstellungen',
            onPressed: () => Navigator.pushNamed(context, '/settings'),
          ),
        ),
      );
      return;
    }

    final hasPerms = await recorder.hasPermission();
    if (!hasPerms) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Mikrofon-Berechtigung wird benötigt')),
      );
      return;
    }

    // Show hint if offline but still allow recording
    if (connection.status != ConnectionStatus.connected && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Offline-Aufnahme — Upload bei Verbindung'),
          duration: Duration(seconds: 2),
        ),
      );
    }

    await recorder.start();
  }

  Future<void> _onStop(
    BuildContext context,
    AudioRecordingService recorder,
  ) async {
    final duration = recorder.duration;
    final path = await recorder.stop();
    if (path != null && context.mounted) {
      final connection = context.read<ServerConnectionService>();
      final processingConfig = context.read<ProcessingConfigService>();
      final upload = context.read<UploadService>();
      final connectivity = context.read<ConnectivityService>();
      final history = context.read<RecordingHistoryService>();

      final filename = kIsWeb ? 'recording.webm' : path.split('/').last;
      final entry = RecordingEntry(
        id: DateTime.now().millisecondsSinceEpoch.toString(),
        filePath: path,
        filename: filename,
        createdAt: DateTime.now(),
        duration: duration,
        status: 'recorded',
      );
      await history.add(entry);
      if (!context.mounted) return;

      final canUploadNow =
          connection.status == ConnectionStatus.connected &&
          connectivity.canUpload(wifiOnly: processingConfig.config.wifiOnly);

      if (processingConfig.config.autoUpload && canUploadNow) {
        upload.uploadAndProcess(
          serverUrl: connection.config!.serverUrl,
          filePath: path,
          config: processingConfig.config,
          entryId: entry.id,
        );
      } else {
        final reason = !canUploadNow
            ? 'Aufnahme gespeichert (offline — Upload später)'
            : 'Aufnahme gespeichert: $filename';
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(reason),
            action: canUploadNow
                ? SnackBarAction(
                    label: 'Hochladen',
                    onPressed: () {
                      upload.uploadAndProcess(
                        serverUrl: connection.config!.serverUrl,
                        filePath: path,
                        config: processingConfig.config,
                        entryId: entry.id,
                      );
                    },
                  )
                : null,
          ),
        );
      }
    }
  }

  Widget _buildUploadStatus(BuildContext context, UploadService upload) {
    switch (upload.status) {
      case UploadStatus.idle:
        return const SizedBox.shrink();
      case UploadStatus.uploading:
        return Column(
          children: [
            SizedBox(
              width: 40,
              height: 40,
              child: CircularProgressIndicator(
                value: upload.progress,
                strokeWidth: 3,
              ),
            ),
            const SizedBox(height: 8),
            const Text('Wird hochgeladen...'),
          ],
        );
      case UploadStatus.processing:
        return Column(
          children: [
            const SizedBox(
              width: 40,
              height: 40,
              child: CircularProgressIndicator(strokeWidth: 3),
            ),
            const SizedBox(height: 8),
            const Text('Wird verarbeitet...'),
          ],
        );
      case UploadStatus.completed:
        return Column(
          children: [
            const Icon(Icons.check_circle, size: 48, color: Colors.green),
            const SizedBox(height: 8),
            const Text('Verarbeitung abgeschlossen'),
            const SizedBox(height: 12),
            FilledButton.icon(
              onPressed: () {
                Navigator.pushNamed(context, '/result');
              },
              icon: const Icon(Icons.description),
              label: const Text('Ergebnis anzeigen'),
            ),
          ],
        );
      case UploadStatus.failed:
        return Column(
          children: [
            const Icon(Icons.error_outline, size: 48, color: Colors.red),
            const SizedBox(height: 8),
            Text(
              upload.errorMessage ?? 'Fehler',
              style: const TextStyle(color: Colors.red),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 12),
            TextButton(
              onPressed: upload.reset,
              child: const Text('Zurücksetzen'),
            ),
          ],
        );
    }
  }
}
