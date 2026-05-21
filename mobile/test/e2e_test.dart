import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:stt_app/main.dart';
import 'package:stt_app/services/upload.dart';
import 'package:stt_app/models/upload_status.dart';

/// Pumps the full app and waits for layout + providers to initialise.
/// Uses pump(duration) instead of pumpAndSettle because HalEye has
/// a continuous glow animation that would cause pumpAndSettle to time out.
Future<void> pumpApp(WidgetTester tester) async {
  await tester.pumpWidget(const STTApp());
  await tester.pump(const Duration(milliseconds: 500));
}

/// Pump after an interaction (tap, enterText, etc.)
/// Route transitions need ~300ms, so we pump 1s to be safe.
Future<void> settle(WidgetTester tester) async {
  await tester.pump(const Duration(seconds: 1));
  await tester.pump(const Duration(milliseconds: 100));
}

void main() {
  group('App-Start', () {
    testWidgets('HomeScreen wird beim Start angezeigt', (tester) async {
      await pumpApp(tester);

      expect(find.text('STT'), findsOneWidget);
      expect(find.text('Nicht verbunden'), findsOneWidget);
      expect(find.byIcon(Icons.history), findsOneWidget);
      expect(find.byIcon(Icons.settings), findsOneWidget);
    });

    testWidgets('HAL-Eye Widget wird angezeigt', (tester) async {
      await pumpApp(tester);

      expect(find.byType(GestureDetector), findsWidgets);
    });
  });

  group('Navigation', () {
    testWidgets('HomeScreen → Einstellungen → zurück', (tester) async {
      await pumpApp(tester);

      await tester.tap(find.byIcon(Icons.settings));
      await settle(tester);

      expect(find.text('Einstellungen'), findsOneWidget);
      expect(find.text('Server-Verbindung'), findsOneWidget);
      expect(find.text('Authentifizierung'), findsOneWidget);

      await tester.tap(find.byType(BackButton));
      await settle(tester);

      expect(find.text('Nicht verbunden'), findsOneWidget);
    });

    testWidgets('HomeScreen → Historie → zurück', (tester) async {
      await pumpApp(tester);

      await tester.tap(find.byIcon(Icons.history));
      await settle(tester);

      expect(find.text('Aufnahmen'), findsOneWidget);
      expect(find.text('Noch keine Aufnahmen'), findsOneWidget);

      await tester.tap(find.byType(BackButton));
      await settle(tester);

      expect(find.text('Nicht verbunden'), findsOneWidget);
    });
  });

  group('Einstellungen', () {
    testWidgets('Server-URL Feld und Buttons vorhanden', (tester) async {
      await pumpApp(tester);

      await tester.tap(find.byIcon(Icons.settings));
      await settle(tester);

      final urlField = find.widgetWithText(TextField, 'Server-URL');
      expect(urlField, findsOneWidget);

      await tester.enterText(urlField, 'https://stt.example.com');
      await settle(tester);

      expect(find.text('TLS-Zertifikat prüfen'), findsOneWidget);
      expect(find.text('Speichern & Testen'), findsOneWidget);
    });

    testWidgets('Leere URL wird nicht gespeichert', (tester) async {
      await pumpApp(tester);

      await tester.tap(find.byIcon(Icons.settings));
      await settle(tester);

      final urlField = find.widgetWithText(TextField, 'Server-URL');
      await tester.enterText(urlField, '');
      await settle(tester);

      await tester.tap(find.text('Speichern & Testen'));
      await settle(tester);

      expect(find.text('Verbindung erfolgreich'), findsNothing);
    });

    testWidgets('Verarbeitungs-Optionen sichtbar', (tester) async {
      await pumpApp(tester);

      await tester.tap(find.byIcon(Icons.settings));
      await settle(tester);

      expect(find.text('Transkription'), findsOneWidget);

      await tester.scrollUntilVisible(
        find.text('Verarbeitung'),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      await settle(tester);
      expect(find.text('Verarbeitung'), findsOneWidget);
      expect(find.text('Sprechererkennung'), findsOneWidget);
    });

    testWidgets('Audio- und Netzwerk-Sektionen sichtbar', (tester) async {
      await pumpApp(tester);

      await tester.tap(find.byIcon(Icons.settings));
      await settle(tester);

      await tester.scrollUntilVisible(
        find.text('Audio-Aufnahme'),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      await settle(tester);
      expect(find.text('Audio-Aufnahme'), findsOneWidget);

      await tester.scrollUntilVisible(
        find.text('Netzwerk'),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      await settle(tester);
      expect(find.text('Netzwerk'), findsOneWidget);
      expect(find.text('Nur über WLAN'), findsOneWidget);
    });
  });

  group('Upload-Status', () {
    testWidgets('Completed-Status zeigt Ergebnis-Button', (tester) async {
      await pumpApp(tester);

      final context = tester.element(find.byType(Scaffold).first);
      final upload = Provider.of<UploadService>(context, listen: false);
      upload.setTestStatus(UploadStatus.completed);
      await settle(tester);

      expect(find.text('Verarbeitung abgeschlossen'), findsOneWidget);
      expect(find.text('Ergebnis anzeigen'), findsOneWidget);
    });

    testWidgets('Ergebnis-Button navigiert zu ResultScreen', (tester) async {
      await pumpApp(tester);

      final context = tester.element(find.byType(Scaffold).first);
      final upload = Provider.of<UploadService>(context, listen: false);
      upload.setTestStatus(UploadStatus.completed);
      await settle(tester);

      await tester.tap(find.text('Ergebnis anzeigen'));
      await settle(tester);

      // ResultScreen AppBar title
      expect(find.text('Ergebnis'), findsOneWidget);
    });

    testWidgets('Failed-Status zeigt Fehler und Reset', (tester) async {
      await pumpApp(tester);

      final context = tester.element(find.byType(Scaffold).first);
      final upload = Provider.of<UploadService>(context, listen: false);
      upload.setTestStatus(UploadStatus.failed, error: 'Netzwerkfehler');
      await settle(tester);

      expect(find.text('Netzwerkfehler'), findsOneWidget);
      expect(find.text('Zurücksetzen'), findsOneWidget);

      await tester.tap(find.text('Zurücksetzen'));
      await settle(tester);

      expect(find.text('Netzwerkfehler'), findsNothing);
    });

    testWidgets('Uploading-Status zeigt Fortschritt', (tester) async {
      await pumpApp(tester);

      final context = tester.element(find.byType(Scaffold).first);
      final upload = Provider.of<UploadService>(context, listen: false);
      upload.setTestStatus(UploadStatus.uploading);
      await settle(tester);

      expect(find.text('Wird hochgeladen...'), findsOneWidget);
      expect(find.byType(CircularProgressIndicator), findsOneWidget);
    });

    testWidgets('Processing-Status zeigt Verarbeitung', (tester) async {
      await pumpApp(tester);

      final context = tester.element(find.byType(Scaffold).first);
      final upload = Provider.of<UploadService>(context, listen: false);
      upload.setTestStatus(UploadStatus.processing);
      await settle(tester);

      expect(find.text('Wird verarbeitet...'), findsOneWidget);
    });
  });

  group('Einstellungen Navigation-Flow', () {
    testWidgets('Einstellungen → URL eingeben → zurück → HomeScreen', (
      tester,
    ) async {
      await pumpApp(tester);

      await tester.tap(find.byIcon(Icons.settings));
      await settle(tester);

      final urlField = find.widgetWithText(TextField, 'Server-URL');
      await tester.enterText(urlField, 'https://stt.test.local');
      await settle(tester);

      await tester.tap(find.byType(BackButton));
      await settle(tester);

      expect(find.text('STT'), findsOneWidget);
    });

    testWidgets('TLS-Switch kann umgeschaltet werden', (tester) async {
      await pumpApp(tester);

      await tester.tap(find.byIcon(Icons.settings));
      await settle(tester);

      final tlsSwitch = find.widgetWithText(
        SwitchListTile,
        'TLS-Zertifikat prüfen',
      );
      expect(tlsSwitch, findsOneWidget);

      await tester.tap(tlsSwitch);
      await settle(tester);

      final switchWidget = tester.widget<SwitchListTile>(tlsSwitch);
      expect(switchWidget.value, isFalse);
    });
  });

  group('Verarbeitungsoptionen', () {
    testWidgets('Sprechererkennung kann deaktiviert werden', (tester) async {
      await pumpApp(tester);

      await tester.tap(find.byIcon(Icons.settings));
      await settle(tester);

      await tester.scrollUntilVisible(
        find.widgetWithText(SwitchListTile, 'Sprechererkennung'),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      await settle(tester);

      final diarizeTile = find.widgetWithText(
        SwitchListTile,
        'Sprechererkennung',
      );
      final before = tester.widget<SwitchListTile>(diarizeTile).value;
      await tester.tap(diarizeTile);
      await settle(tester);

      expect(tester.widget<SwitchListTile>(diarizeTile).value, isNot(before));
    });

    testWidgets(
      'Zusammenfassung und Strukturierung können deaktiviert werden',
      (tester) async {
        await pumpApp(tester);

        await tester.tap(find.byIcon(Icons.settings));
        await settle(tester);

        // Scroll to and toggle Strukturierung
        await tester.scrollUntilVisible(
          find.widgetWithText(SwitchListTile, 'Strukturierung'),
          200,
          scrollable: find.byType(Scrollable).first,
        );
        await settle(tester);

        final structureTile = find.widgetWithText(
          SwitchListTile,
          'Strukturierung',
        );
        if (tester.widget<SwitchListTile>(structureTile).value) {
          await tester.tap(structureTile);
          await settle(tester);
        }
        expect(tester.widget<SwitchListTile>(structureTile).value, isFalse);

        // Scroll to and toggle Zusammenfassung
        await tester.scrollUntilVisible(
          find.widgetWithText(SwitchListTile, 'Zusammenfassung'),
          200,
          scrollable: find.byType(Scrollable).first,
        );
        await settle(tester);

        final summaryTile = find.widgetWithText(
          SwitchListTile,
          'Zusammenfassung',
        );
        if (tester.widget<SwitchListTile>(summaryTile).value) {
          await tester.tap(summaryTile);
          await settle(tester);
        }
        expect(tester.widget<SwitchListTile>(summaryTile).value, isFalse);
      },
    );

    testWidgets('Optionsänderung bleibt nach Navigation erhalten', (
      tester,
    ) async {
      await pumpApp(tester);

      // Open settings and disable diarize
      await tester.tap(find.byIcon(Icons.settings));
      await settle(tester);

      await tester.scrollUntilVisible(
        find.widgetWithText(SwitchListTile, 'Sprechererkennung'),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      await settle(tester);

      final tile = find.widgetWithText(SwitchListTile, 'Sprechererkennung');
      if (tester.widget<SwitchListTile>(tile).value) {
        await tester.tap(tile);
        await settle(tester);
      }
      final savedValue = tester.widget<SwitchListTile>(tile).value;

      // Navigate away and back
      await tester.tap(find.byType(BackButton));
      await settle(tester);
      await tester.tap(find.byIcon(Icons.settings));
      await settle(tester);

      await tester.scrollUntilVisible(
        find.widgetWithText(SwitchListTile, 'Sprechererkennung'),
        200,
        scrollable: find.byType(Scrollable).first,
      );
      await settle(tester);

      expect(
        tester
            .widget<SwitchListTile>(
              find.widgetWithText(SwitchListTile, 'Sprechererkennung'),
            )
            .value,
        savedValue,
      );
    });
  });
}
