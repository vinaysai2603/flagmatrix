import 'package:flagmatrix_studio/data/datasources/flagmatrix_remote_datasource.dart';
import 'package:flagmatrix_studio/domain/entities/flagmatrix_models.dart';
import 'package:flagmatrix_studio/domain/repositories/flagmatrix_repository.dart';

class FlagMatrixRepositoryImpl implements FlagMatrixRepository {
  final FlagMatrixRemoteDataSource remote;

  FlagMatrixRepositoryImpl(this.remote);

  @override
  void setApiBaseUrl(String baseUrl) => remote.setBaseUrl(baseUrl);

  @override
  Future<Map<String, dynamic>> checkHealth() => remote.getHealth();

  @override
  Future<Map<String, dynamic>> updateFlagsmithConnection({
    required String url,
    String? apiKey,
  }) =>
      remote.updateConnection(url, apiKey);

  @override
  Future<List<FlagsmithProjectInfo>> getProjects() async {
    final raw = await remote.getProjects();
    return raw
        .map((e) => FlagsmithProjectInfo.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<List<FlagsmithEnvInfo>> getEnvironments(int projectId) async {
    final raw = await remote.getEnvironments(projectId);
    return raw
        .map((e) => FlagsmithEnvInfo.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<List<AppProfileEntity>> getProfiles() async {
    final raw = await remote.getProfiles();
    return raw
        .map((e) => AppProfileEntity.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<List<FeatureRuleEntity>> getRules() async {
    final raw = await remote.getRules();
    final rules = raw['rules'] as List? ?? const [];
    return rules
        .map((e) => FeatureRuleEntity.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<ValidationRecordEntity> runValidation({
    required int projectId,
    required String environment,
    required bool strict,
  }) async {
    final raw = await remote.runValidation(
      projectId: projectId,
      environment: environment,
      strict: strict,
    );
    return ValidationRecordEntity.fromJson(raw);
  }

  @override
  Future<List<ValidationRecordEntity>> getHistory() async {
    final raw = await remote.getHistory();
    return raw
        .map((e) => ValidationRecordEntity.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<EnvComparisonEntity> compareEnvironments({
    required int projectId,
    required String sourceEnvironment,
    required String targetEnvironment,
    required bool strict,
  }) async {
    final raw = await remote.compareEnvironments(
      projectId: projectId,
      sourceEnvironment: sourceEnvironment,
      targetEnvironment: targetEnvironment,
      strict: strict,
    );
    return EnvComparisonEntity.fromJson(raw);
  }

  @override
  Future<String> exportReport({
    required String runId,
    required String format,
  }) =>
      remote.exportReport(runId, format);
}
