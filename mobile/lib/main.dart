import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'services/auth.dart';
import 'services/audio_recording.dart';
import 'services/processing_config.dart';
import 'services/recording_history.dart';
import 'services/server_connection.dart';
import 'services/upload.dart';
import 'screens/history_screen.dart';
import 'screens/home_screen.dart';
import 'screens/result_screen.dart';
import 'screens/settings_screen.dart';

void main() {
  runApp(const STTApp());
}

class STTApp extends StatelessWidget {
  const STTApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => ServerConnectionService()),
        ChangeNotifierProvider(create: (_) => AudioRecordingService()),
        ChangeNotifierProvider(create: (_) => ProcessingConfigService()),
        ChangeNotifierProvider(create: (_) => AuthService()),
        ChangeNotifierProvider(create: (_) => RecordingHistoryService()),
        ChangeNotifierProxyProvider<AuthService, UploadService>(
          create: (ctx) => UploadService(
            authService: ctx.read<AuthService>(),
          ),
          update: (_, auth, previous) =>
              previous ?? UploadService(authService: auth),
        ),
      ],
      child: MaterialApp(
        title: 'STT',
        debugShowCheckedModeBanner: false,
        theme: ThemeData(
          colorScheme: ColorScheme.fromSeed(
            seedColor: Colors.red,
            brightness: Brightness.dark,
          ),
          useMaterial3: true,
          scaffoldBackgroundColor: const Color(0xFF121212),
        ),
        initialRoute: '/',
        routes: {
          '/': (context) => const HomeScreen(),
          '/settings': (context) => const SettingsScreen(),
          '/result': (context) => const ResultScreen(),
          '/history': (context) => const HistoryScreen(),
        },
      ),
    );
  }
}
