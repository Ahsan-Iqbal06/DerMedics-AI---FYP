DateTime? _date(dynamic v) => v == null ? null : DateTime.tryParse(v as String)?.toLocal();
List<String> _strings(dynamic v) => (v as List? ?? const []).map((e) => e.toString()).toList();

class AppUser {
  AppUser({
    required this.id,
    required this.fullName,
    required this.email,
    required this.phone,
    required this.country,
    required this.city,
    this.avatarUrl,
  });

  final int id;
  final String fullName;
  final String email;
  final String phone;
  final String country;
  final String city;

  /// Server path such as /uploads/avatars/abc.jpg, or null when no photo is set.
  final String? avatarUrl;

  String get firstName => fullName.split(' ').first;
  String get initial => fullName.isEmpty ? '?' : fullName[0].toUpperCase();

  factory AppUser.fromJson(Map<String, dynamic> j) => AppUser(
        id: j['id'] as int,
        fullName: j['full_name'] as String,
        email: j['email'] as String,
        phone: j['phone'] as String? ?? '',
        country: j['country'] as String? ?? '',
        city: j['city'] as String? ?? '',
        avatarUrl: j['avatar_url'] as String?,
      );
}

class ConditionInfo {
  ConditionInfo({
    required this.name,
    required this.overview,
    required this.symptoms,
    required this.precautions,
    required this.whenToSeeDoctor,
    this.causes = const [],
    this.riskFactors = const [],
    this.dermatologistCare = const [],
    this.outlook = '',
  });

  final String name;
  final String overview;
  final List<String> symptoms;
  final List<String> precautions;
  final String whenToSeeDoctor;
  final List<String> causes;
  final List<String> riskFactors;

  /// What a dermatologist typically examines, tests or follows up for this condition.
  final List<String> dermatologistCare;
  final String outlook;

  factory ConditionInfo.fromJson(Map<String, dynamic> j) => ConditionInfo(
        name: j['name'] as String? ?? '',
        overview: j['overview'] as String? ?? '',
        symptoms: _strings(j['symptoms']),
        precautions: _strings(j['precautions']),
        whenToSeeDoctor: j['when_to_see_doctor'] as String? ?? '',
        causes: _strings(j['causes']),
        riskFactors: _strings(j['risk_factors']),
        dermatologistCare: _strings(j['dermatologist_care']),
        outlook: j['outlook'] as String? ?? '',
      );
}

class Medicine {
  Medicine({
    required this.name,
    required this.type,
    required this.usageNote,
    required this.prescriptionRequired,
    required this.caution,
  });

  final String name;
  final String type;
  final String usageNote;
  final bool prescriptionRequired;
  final String caution;

  factory Medicine.fromJson(Map<String, dynamic> j) => Medicine(
        name: j['name'] as String,
        type: j['type'] as String? ?? '',
        usageNote: j['usage_note'] as String? ?? '',
        prescriptionRequired: j['prescription_required'] as bool? ?? false,
        caution: j['caution'] as String? ?? '',
      );
}

class Dermatologist {
  Dermatologist({
    required this.name,
    required this.kind,
    required this.clinic,
    required this.qualification,
    required this.city,
    required this.country,
    required this.address,
    required this.phone,
    required this.latitude,
    required this.longitude,
    required this.conditions,
    required this.isSample,
    required this.source,
    required this.distanceKm,
    required this.rating,
  });

  final String name;
  final String kind;
  final String clinic;
  final String qualification;
  final String city;
  final String country;
  final String address;
  final String phone;
  final double? latitude;
  final double? longitude;
  final List<String> conditions;
  final bool isSample;
  final String source;
  final double? distanceKm;
  final double? rating;

  bool get isClinic => kind == 'clinic';

  factory Dermatologist.fromJson(Map<String, dynamic> j) => Dermatologist(
        name: j['name'] as String,
        kind: j['kind'] as String? ?? 'doctor',
        clinic: j['clinic'] as String? ?? '',
        qualification: j['qualification'] as String? ?? '',
        city: j['city'] as String? ?? '',
        country: j['country'] as String? ?? '',
        address: j['address'] as String? ?? '',
        phone: j['phone'] as String? ?? '',
        latitude: (j['latitude'] as num?)?.toDouble(),
        longitude: (j['longitude'] as num?)?.toDouble(),
        conditions: _strings(j['conditions']),
        isSample: j['is_sample'] as bool? ?? true,
        source: j['source'] as String? ?? 'database',
        distanceKm: (j['distance_km'] as num?)?.toDouble(),
        rating: (j['rating'] as num?)?.toDouble(),
      );
}

class Prediction {
  Prediction(this.label, this.displayName, this.confidence);
  final String label;
  final String displayName;
  final double confidence;

  factory Prediction.fromJson(Map<String, dynamic> j) =>
      Prediction(j['label'] as String, j['display_name'] as String, (j['confidence'] as num).toDouble());
}

class Analysis {
  Analysis({
    required this.id,
    required this.status,
    required this.predictedLabel,
    required this.displayName,
    required this.confidence,
    required this.topPredictions,
    required this.description,
    required this.medicines,
    required this.region,
    required this.bodyArea,
    required this.symptoms,
    required this.isDemo,
    required this.modelVersion,
    required this.llmSource,
    required this.imageUrl,
    required this.createdAt,
    required this.dermatologists,
    required this.hasReport,
  });

  final int id;
  final String status;
  final String? predictedLabel;
  final String? displayName;
  final double confidence;
  final List<Prediction> topPredictions;
  final ConditionInfo? description;
  final List<Medicine> medicines;
  final String region;
  final String bodyArea;
  final String symptoms;
  final bool isDemo;
  final String modelVersion;
  final String llmSource;
  final String imageUrl;
  final DateTime? createdAt;
  final List<Dermatologist> dermatologists;
  final bool hasReport;

  bool get isConclusive => status == 'ai';
  int get confidencePercent => (confidence * 100).round();

  factory Analysis.fromJson(Map<String, dynamic> j) => Analysis(
        id: j['id'] as int,
        status: j['status'] as String,
        predictedLabel: j['predicted_label'] as String?,
        displayName: j['display_name'] as String?,
        confidence: (j['confidence'] as num).toDouble(),
        topPredictions:
            (j['top_predictions'] as List? ?? const []).map((e) => Prediction.fromJson(e as Map<String, dynamic>)).toList(),
        description: j['description'] == null ? null : ConditionInfo.fromJson(j['description'] as Map<String, dynamic>),
        medicines: (j['medicines'] as List? ?? const []).map((e) => Medicine.fromJson(e as Map<String, dynamic>)).toList(),
        region: j['region'] as String? ?? '',
        bodyArea: j['body_area'] as String? ?? '',
        symptoms: j['symptoms'] as String? ?? '',
        isDemo: j['is_demo'] as bool? ?? false,
        modelVersion: j['model_version'] as String? ?? '',
        llmSource: j['llm_source'] as String? ?? '',
        imageUrl: j['image_url'] as String? ?? '',
        createdAt: _date(j['created_at']),
        dermatologists: (j['dermatologists'] as List? ?? const [])
            .map((e) => Dermatologist.fromJson(e as Map<String, dynamic>))
            .toList(),
        hasReport: j['has_report'] as bool? ?? false,
      );
}

class ReportSummary {
  ReportSummary({
    required this.id,
    required this.analysisId,
    required this.title,
    required this.subtitle,
    required this.status,
    required this.subjectName,
    required this.createdAt,
  });

  final int id;
  final int analysisId;
  final String title;
  final String subtitle;
  final String status;
  final String subjectName;
  final DateTime? createdAt;

  factory ReportSummary.fromJson(Map<String, dynamic> j) => ReportSummary(
        id: j['id'] as int,
        analysisId: j['analysis_id'] as int,
        title: j['title'] as String,
        subtitle: j['subtitle'] as String,
        status: j['status'] as String,
        subjectName: j['subject_name'] as String,
        createdAt: _date(j['created_at']),
      );
}

class Report {
  Report({
    required this.id,
    required this.subjectType,
    required this.subjectName,
    required this.subjectAge,
    required this.relationship,
    required this.healthNotes,
    required this.createdAt,
    required this.analysis,
  });

  final int id;
  final String subjectType;
  final String subjectName;
  final int? subjectAge;
  final String relationship;
  final String healthNotes;
  final DateTime? createdAt;
  final Analysis analysis;

  factory Report.fromJson(Map<String, dynamic> j) => Report(
        id: j['id'] as int,
        subjectType: j['subject_type'] as String,
        subjectName: j['subject_name'] as String,
        subjectAge: j['subject_age'] as int?,
        relationship: j['relationship'] as String? ?? '',
        healthNotes: j['health_notes'] as String? ?? '',
        createdAt: _date(j['created_at']),
        analysis: Analysis.fromJson(j['analysis'] as Map<String, dynamic>),
      );
}

class ActivityItem {
  ActivityItem(this.kind, this.title, this.refId, this.createdAt);
  final String kind;
  final String title;
  final int refId;
  final DateTime? createdAt;

  factory ActivityItem.fromJson(Map<String, dynamic> j) =>
      ActivityItem(j['kind'] as String, j['title'] as String, j['ref_id'] as int, _date(j['created_at']));
}

class Dashboard {
  Dashboard(this.analysesCount, this.reportsCount, this.nearbyCount, this.recentActivity);
  final int analysesCount;
  final int reportsCount;
  final int nearbyCount;
  final List<ActivityItem> recentActivity;

  factory Dashboard.fromJson(Map<String, dynamic> j) => Dashboard(
        j['analyses_count'] as int,
        j['reports_count'] as int,
        j['nearby_count'] as int,
        (j['recent_activity'] as List).map((e) => ActivityItem.fromJson(e as Map<String, dynamic>)).toList(),
      );
}
