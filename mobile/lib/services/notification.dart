import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

class NotificationService {
  static final NotificationService _instance = NotificationService._();
  factory NotificationService() => _instance;
  NotificationService._();

  final FlutterLocalNotificationsPlugin _plugin =
      FlutterLocalNotificationsPlugin();
  bool _initialized = false;

  Future<void> init() async {
    if (_initialized) return;
    // Notifications are not supported in the web build.
    if (kIsWeb) return;

    const androidSettings = AndroidInitializationSettings(
      '@mipmap/ic_launcher',
    );
    const darwinSettings = DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );
    const settings = InitializationSettings(
      android: androidSettings,
      iOS: darwinSettings,
    );

    await _plugin.initialize(settings: settings);
    _initialized = true;
  }

  Future<void> showProcessingComplete({
    required String filename,
    String? summary,
  }) async {
    if (!_initialized) return;

    const androidDetails = AndroidNotificationDetails(
      'stt_processing',
      'Verarbeitung',
      channelDescription: 'Benachrichtigungen über abgeschlossene Verarbeitung',
      importance: Importance.high,
      priority: Priority.high,
    );
    const darwinDetails = DarwinNotificationDetails();
    const details = NotificationDetails(
      android: androidDetails,
      iOS: darwinDetails,
    );

    await _plugin.show(
      id: filename.hashCode,
      title: 'Transkription abgeschlossen',
      body: summary ?? '$filename wurde verarbeitet',
      notificationDetails: details,
    );
  }

  Future<void> showProcessingFailed({
    required String filename,
    String? error,
  }) async {
    if (!_initialized) return;

    const androidDetails = AndroidNotificationDetails(
      'stt_processing',
      'Verarbeitung',
      channelDescription: 'Benachrichtigungen über abgeschlossene Verarbeitung',
      importance: Importance.high,
      priority: Priority.high,
    );
    const details = NotificationDetails(android: androidDetails);

    await _plugin.show(
      id: filename.hashCode,
      title: 'Verarbeitung fehlgeschlagen',
      body: error ?? '$filename konnte nicht verarbeitet werden',
      notificationDetails: details,
    );
  }
}
