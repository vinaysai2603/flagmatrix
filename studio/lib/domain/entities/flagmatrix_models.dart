import 'package:equatable/equatable.dart';

enum CompatibilityStatus {
  pass,
  conflict,
  unknown,
  skipped;

  static CompatibilityStatus fromApi(String raw) {
    switch (raw.toUpperCase()) {
      case 'PASS':
        return CompatibilityStatus.pass;
      case 'CONFLICT':
        return CompatibilityStatus.conflict;
      case 'UNKNOWN':
        return CompatibilityStatus.unknown;
      case 'SKIPPED':
      default:
        return CompatibilityStatus.skipped;
    }
  }

  String get label {
    switch (this) {
      case CompatibilityStatus.pass:
        return 'Supported (PASS)';
      case CompatibilityStatus.conflict:
        return 'Incompatible (CONFLICT)';
      case CompatibilityStatus.unknown:
        return 'Unknown (UNKNOWN)';
      case CompatibilityStatus.skipped:
        return 'Disabled (SKIPPED)';
    }
  }
}

class FlagsmithProjectInfo extends Equatable {
  final int id;
  final String name;

  const FlagsmithProjectInfo({required this.id, required this.name});

  factory FlagsmithProjectInfo.fromJson(Map<String, dynamic> json) =>
      FlagsmithProjectInfo(
        id: json['id'] as int,
        name: json['name'] as String,
      );

  @override
  List<Object?> get props => [id, name];
}

class FlagsmithEnvInfo extends Equatable {
  final int id;
  final String name;
  final int project;

  const FlagsmithEnvInfo({
    required this.id,
    required this.name,
    required this.project,
  });

  factory FlagsmithEnvInfo.fromJson(Map<String, dynamic> json) =>
      FlagsmithEnvInfo(
        id: json['id'] as int,
        name: json['name'] as String,
        project: json['project'] as int,
      );

  @override
  List<Object?> get props => [id, name, project];
}

class AppProfileEntity extends Equatable {
  final String appId;
  final String tenantId;
  final String platform;
  final String appVersion;
  final String buildFlavor;
  final String environment;
  final List<String> installedSdks;
  final Map<String, String> sdkVersions;
  final Map<String, String> backendApiVersions;
  final Map<String, dynamic> nativeResources;
  final Map<String, dynamic> deviceCapabilities;

  const AppProfileEntity({
    required this.appId,
    required this.tenantId,
    required this.platform,
    required this.appVersion,
    required this.buildFlavor,
    required this.environment,
    required this.installedSdks,
    required this.sdkVersions,
    required this.backendApiVersions,
    required this.nativeResources,
    required this.deviceCapabilities,
  });

  String get profileId => '$tenantId:$appId:$platform:$appVersion';

  factory AppProfileEntity.fromJson(Map<String, dynamic> json) =>
      AppProfileEntity(
        appId: json['app_id'] as String,
        tenantId: json['tenant_id'] as String,
        platform: json['platform'] as String,
        appVersion: json['app_version'] as String,
        buildFlavor: (json['build_flavor'] as String?) ?? 'production',
        environment: json['environment'] as String,
        installedSdks: List<String>.from(json['installed_sdks'] ?? const []),
        sdkVersions: Map<String, String>.from(json['sdk_versions'] ?? const {}),
        backendApiVersions:
            Map<String, String>.from(json['backend_api_versions'] ?? const {}),
        nativeResources:
            Map<String, dynamic>.from(json['native_resources'] ?? const {}),
        deviceCapabilities:
            Map<String, dynamic>.from(json['device_capabilities'] ?? const {}),
      );

  @override
  List<Object?> get props => [appId, tenantId, platform, appVersion];
}

class FeatureRuleEntity extends Equatable {
  final String featureName;
  final bool requireEnabled;
  final List<String>? platforms;
  final List<Map<String, dynamic>> constraints;

  const FeatureRuleEntity({
    required this.featureName,
    required this.requireEnabled,
    required this.platforms,
    required this.constraints,
  });

  factory FeatureRuleEntity.fromJson(Map<String, dynamic> json) =>
      FeatureRuleEntity(
        featureName: json['feature_name'] as String,
        requireEnabled: (json['require_enabled'] as bool?) ?? false,
        platforms: json['platforms'] != null
            ? List<String>.from(json['platforms'] as List)
            : null,
        constraints: List<Map<String, dynamic>>.from(
          (json['constraints'] as List? ?? const [])
              .map((e) => Map<String, dynamic>.from(e as Map)),
        ),
      );

  @override
  List<Object?> get props => [featureName, requireEnabled, platforms, constraints];
}

class EvaluationFindingEntity extends Equatable {
  final CompatibilityStatus status;
  final String featureName;
  final String identity;
  final String profileId;
  final String ruleId;
  final String expectedRequirement;
  final String observedCapability;
  final String explanation;
  final String source;

  const EvaluationFindingEntity({
    required this.status,
    required this.featureName,
    required this.identity,
    required this.profileId,
    required this.ruleId,
    required this.expectedRequirement,
    required this.observedCapability,
    required this.explanation,
    required this.source,
  });

  factory EvaluationFindingEntity.fromJson(Map<String, dynamic> json) =>
      EvaluationFindingEntity(
        status: CompatibilityStatus.fromApi(json['status'] as String),
        featureName: json['feature_name'] as String,
        identity: json['identity'] as String,
        profileId: json['profile_id'] as String,
        ruleId: json['rule_id'] as String,
        expectedRequirement: json['expected_requirement'] as String,
        observedCapability: json['observed_capability'] as String,
        explanation: json['explanation'] as String,
        source: (json['source'] as String?) ?? 'flagsmith',
      );

  @override
  List<Object?> get props => [status, featureName, identity, profileId, ruleId];
}

class ValidationRecordEntity extends Equatable {
  final String runId;
  final String createdAt;
  final String environment;
  final bool strict;
  final int totalChecks;
  final int passed;
  final int conflicts;
  final int unknowns;
  final int skipped;
  final bool blocking;
  final List<EvaluationFindingEntity> findings;

  const ValidationRecordEntity({
    required this.runId,
    required this.createdAt,
    required this.environment,
    required this.strict,
    required this.totalChecks,
    required this.passed,
    required this.conflicts,
    required this.unknowns,
    required this.skipped,
    required this.blocking,
    required this.findings,
  });

  factory ValidationRecordEntity.fromJson(Map<String, dynamic> json) {
    final report = json['report'] as Map<String, dynamic>;
    return ValidationRecordEntity(
      runId: json['run_id'] as String,
      createdAt: (json['created_at'] as String?) ?? '',
      environment: report['environment'] as String,
      strict: (report['strict'] as bool?) ?? false,
      totalChecks: report['total_checks'] as int,
      passed: report['passed'] as int,
      conflicts: report['conflicts'] as int,
      unknowns: report['unknowns'] as int,
      skipped: report['skipped'] as int,
      blocking: report['blocking'] as bool,
      findings: (report['findings'] as List)
          .map((e) => EvaluationFindingEntity.fromJson(e as Map<String, dynamic>))
          .toList(),
    );
  }

  @override
  List<Object?> get props => [runId, environment, totalChecks, conflicts];
}

class EnvComparisonEntity extends Equatable {
  final String sourceEnvironment;
  final String targetEnvironment;
  final List<Map<String, dynamic>> flagDiffs;
  final int newConflictsInTarget;
  final int newUnknownsInTarget;

  const EnvComparisonEntity({
    required this.sourceEnvironment,
    required this.targetEnvironment,
    required this.flagDiffs,
    required this.newConflictsInTarget,
    required this.newUnknownsInTarget,
  });

  factory EnvComparisonEntity.fromJson(Map<String, dynamic> json) =>
      EnvComparisonEntity(
        sourceEnvironment: json['source_environment'] as String,
        targetEnvironment: json['target_environment'] as String,
        flagDiffs: List<Map<String, dynamic>>.from(
          (json['flag_diffs'] as List? ?? const [])
              .map((e) => Map<String, dynamic>.from(e as Map)),
        ),
        newConflictsInTarget: (json['new_conflicts_in_target'] as int?) ?? 0,
        newUnknownsInTarget: (json['new_unknowns_in_target'] as int?) ?? 0,
      );

  @override
  List<Object?> get props => [
        sourceEnvironment,
        targetEnvironment,
        flagDiffs,
        newConflictsInTarget,
        newUnknownsInTarget,
      ];
}
