class ProcessingConfig {
  final String language;
  final String model;
  final bool diarize;
  final bool summarize;
  final bool structure;
  final String audioFormat;
  final int sampleRate;
  final bool wifiOnly;
  final bool autoUpload;

  const ProcessingConfig({
    this.language = 'auto',
    this.model = 'small',
    this.diarize = true,
    this.summarize = true,
    this.structure = true,
    this.audioFormat = 'm4a',
    this.sampleRate = 44100,
    this.wifiOnly = true,
    this.autoUpload = false,
  });

  ProcessingConfig copyWith({
    String? language,
    String? model,
    bool? diarize,
    bool? summarize,
    bool? structure,
    String? audioFormat,
    int? sampleRate,
    bool? wifiOnly,
    bool? autoUpload,
  }) {
    return ProcessingConfig(
      language: language ?? this.language,
      model: model ?? this.model,
      diarize: diarize ?? this.diarize,
      summarize: summarize ?? this.summarize,
      structure: structure ?? this.structure,
      audioFormat: audioFormat ?? this.audioFormat,
      sampleRate: sampleRate ?? this.sampleRate,
      wifiOnly: wifiOnly ?? this.wifiOnly,
      autoUpload: autoUpload ?? this.autoUpload,
    );
  }

  Map<String, dynamic> toJson() => {
        'language': language,
        'model': model,
        'diarize': diarize,
        'summarize': summarize,
        'structure': structure,
        'audioFormat': audioFormat,
        'sampleRate': sampleRate,
        'wifiOnly': wifiOnly,
        'autoUpload': autoUpload,
      };

  factory ProcessingConfig.fromJson(Map<String, dynamic> json) {
    return ProcessingConfig(
      language: json['language'] as String? ?? 'auto',
      model: json['model'] as String? ?? 'small',
      diarize: json['diarize'] as bool? ?? true,
      summarize: json['summarize'] as bool? ?? true,
      structure: json['structure'] as bool? ?? true,
      audioFormat: json['audioFormat'] as String? ?? 'm4a',
      sampleRate: json['sampleRate'] as int? ?? 44100,
      wifiOnly: json['wifiOnly'] as bool? ?? true,
      autoUpload: json['autoUpload'] as bool? ?? false,
    );
  }

  static const List<String> availableLanguages = [
    'auto',
    'de',
    'en',
    'fr',
    'es',
    'it',
    'pt',
    'nl',
    'pl',
    'ru',
    'zh',
    'ja',
    'ko',
  ];

  static const Map<String, String> languageLabels = {
    'auto': 'Automatisch',
    'de': 'Deutsch',
    'en': 'English',
    'fr': 'Français',
    'es': 'Español',
    'it': 'Italiano',
    'pt': 'Português',
    'nl': 'Nederlands',
    'pl': 'Polski',
    'ru': 'Русский',
    'zh': '中文',
    'ja': '日本語',
    'ko': '한국어',
  };

  static const List<String> availableModels = [
    'tiny',
    'base',
    'small',
    'medium',
    'large',
  ];

  static const Map<String, String> modelDescriptions = {
    'tiny': 'Schnell, geringere Genauigkeit',
    'base': 'Schnell, akzeptable Genauigkeit',
    'small': 'Ausgewogen (empfohlen)',
    'medium': 'Langsamer, hohe Genauigkeit',
    'large': 'Langsam, höchste Genauigkeit',
  };

  static const List<String> availableAudioFormats = ['m4a', 'wav', 'ogg'];

  static const Map<String, String> audioFormatLabels = {
    'm4a': 'AAC (.m4a) — kompakt',
    'wav': 'WAV — unkomprimiert',
    'ogg': 'OGG Vorbis — kompakt',
  };

  static const List<int> availableSampleRates = [16000, 44100, 48000];

  static const Map<int, String> sampleRateLabels = {
    16000: '16 kHz — Sprache (Standard)',
    44100: '44.1 kHz — CD-Qualität',
    48000: '48 kHz — Studio',
  };
}
