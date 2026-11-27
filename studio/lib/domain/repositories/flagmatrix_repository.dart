import 'package:flagmatrix_studio/domain/entities/flagmatrix_models.dart';

abstract class FlagMatrixRepository {
  void setApiBaseUrl(String baseUrl);
  Future<Map<String, dynamic>> checkHealth();
  Future<Map<String, dynamic>> updateFlagsmithConnection({
    required String url,
    String? apiKey,
  });
  Future<List<FlagsmithProjectInfo>> getProjects();
  Future<List<FlagsmithEnvInfo>> getEnvironments(int projectId);
  Future<List<AppProfileEntity>> getProfiles();
  Future<List<FeatureRuleEntity>> getRules();
  Future<ValidationRecordEntity> runValidation({
    required int projectId,
    required String environment,
    required bool strict,
  });
  Future<List<ValidationRecordEntity>> getHistory();
  Future<EnvComparisonEntity> compareEnvironments({
    required int projectId,
    required String sourceEnvironment,
    required String targetEnvironment,
    required bool strict,
  });
  Future<String> exportReport({
    required String runId,
    required String format,
  });
}
