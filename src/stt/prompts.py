"""System prompts for LLM-based text processing."""

DEFAULT_SYSTEM_PROMPT = "Fasse Texte zusammen."

STRUCTURE_SYSTEM_PROMPT = (
    "Du erhältst ein Transkript einer Audio-Aufnahme. "
    "Gliedere den VOLLSTÄNDIGEN Inhalt in thematische Abschnitte. "
    "Gib jedem Abschnitt eine kurze, aussagekräftige Überschrift (## Markdown). "
    "Antworte ausschließlich mit dem gegliederten Text. "
    "Keine Erklärungen, keine Analyse, kein Kommentar."
)

SUMMARY_SYSTEM_PROMPT = (
    "Du erhältst einen bereits in Abschnitte gegliederten Text im markdown Format. "
    "Jeder Abschnitt wird mit einem ## Überschrift markiert. "
    "Erstelle eine KURZE Zusammenfassung: maximal 2-3 Sätze pro Abschnitt. "
    "Ziel ist eine kompakte Übersicht, NICHT eine Wiederholung des vollen Textes. "
    "Behalte die Überschriften bei, aber kürze den Inhalt radikal auf das Wesentliche. "
    "Antworte ausschließlich mit der Zusammenfassung im Markdown-Format."
)

DIARIZE_SYSTEM_PROMPT = (
    "Du erhältst ein Transkript einer Audio-Aufnahme mit mehreren Sprechern. "
    "Deine Aufgabe: Weise jedem Textabschnitt ein konsistentes Speaker-Label zu.\n\n"
    "VORGEHEN:\n"
    "1. Schätze zuerst die Anzahl der Sprecher anhand des gesamten Textes.\n"
    "2. Vergib feste Labels: **Sprecher 1:**, **Sprecher 2:**, etc.\n"
    "3. Behalte die Zuordnung im gesamten Text konsistent bei — "
    "derselbe Sprecher behält immer dasselbe Label.\n\n"
    "ERKENNUNGSMERKMALE für Sprecherwechsel:\n"
    "- Direkte Anreden oder Begrüßungen (z.B. 'Hallo', 'Jan, ...', 'Moin')\n"
    "- Frage-Antwort-Muster\n"
    "- Themenwechsel oder Perspektivwechsel\n"
    "- Unterschiedlicher Sprachstil, Wortwahl oder Fachkenntnis\n"
    "- Zustimmung/Widerspruch zu vorherigem Beitrag\n\n"
    "REGELN:\n"
    "- Gib den VOLLSTÄNDIGEN Text zurück — kürze oder fasse NICHTS zusammen.\n"
    "- Setze das Speaker-Label als eigene Zeile vor den jeweiligen Abschnitt.\n"
    "- Fasse aufeinanderfolgende Sätze desselben Sprechers unter einem Label zusammen.\n"
    "- Antworte ausschließlich mit dem zugeordneten Text.\n"
    "- Keine Erklärungen, keine Analyse, keine Einleitung."
)
