import 'package:dio/dio.dart';

class FlagMatrixRemoteDataSource {
  final Dio dio;

  FlagMatrixRemoteDataSource(this.dio);

  void setBaseUrl(String baseUrl) {
    dio.options.baseUrl = baseUrl.replaceAll(RegExp(r'/+$'), '');
  }

  Future<Map<String, dynamic>> getHealth() async {
    final resp = await dio.get<Map<String, dynamic>>('/health');
    return resp.data ?? {};
  }

  Future<Map<String, dynamic>> updateConnection(String url, String? apiKey) async {
    final resp = await dio.post<Map<String, dynamic>>(
      '/api/v1/connection',
      data: {
        'url': url,
        if (apiKey != null && apiKey.isNotEmpty) 'api_key': apiKey,
      },
    );
    return resp.data ?? {};
  }

  Future<List<dynamic>> getProjects() async {
    final resp = await dio.get<List<dynamic>>('/api/v1/projects');
    return resp.data ?? [];
  }

  Future<List<dynamic>> getEnvironments(int projectId) async {
    final resp = await dio.get<List<dynamic>>(
      '/api/v1/environments',
      queryParameters: {'project_id': projectId},
    );
    return resp.data ?? [];
  }

  Future<List<dynamic>> getProfiles() async {
    final resp = await dio.get<List<dynamic>>('/api/v1/profiles');
    return resp.data ?? [];
  }

  Future<Map<String, dynamic>> getRules() async {
    final resp = await dio.get<Map<String, dynamic>>('/api/v1/rules');
    return resp.data ?? {};
  }

  Future<Map<String, dynamic>> runValidation({
    required int projectId,
    required String environment,
    required bool strict,
  }) async {
    final resp = await dio.post<Map<String, dynamic>>(
      '/api/v1/validation/run',
      data: {
        'project_id': projectId,
        'environment': environment,
        'strict': strict,
      },
    );
    return resp.data ?? {};
  }

  Future<List<dynamic>> getHistory() async {
    final resp = await dio.get<List<dynamic>>('/api/v1/validation');
    return resp.data ?? [];
  }

  Future<Map<String, dynamic>> compareEnvironments({
    required int projectId,
    required String sourceEnvironment,
    required String targetEnvironment,
    required bool strict,
  }) async {
    final resp = await dio.post<Map<String, dynamic>>(
      '/api/v1/environments/compare',
      data: {
        'project_id': projectId,
        'source_environment': sourceEnvironment,
        'target_environment': targetEnvironment,
        'strict': strict,
      },
    );
    return resp.data ?? {};
  }

  Future<String> exportReport(String runId, String format) async {
    final resp = await dio.get<dynamic>(
      '/api/v1/reports/$runId',
      queryParameters: {'format': format},
      options: Options(responseType: ResponseType.plain),
    );
    return resp.data?.toString() ?? '';
  }
}
