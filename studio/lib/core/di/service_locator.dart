import 'package:dio/dio.dart';
import 'package:get_it/get_it.dart';
import 'package:flagmatrix_studio/data/datasources/flagmatrix_remote_datasource.dart';
import 'package:flagmatrix_studio/data/repositories/flagmatrix_repository_impl.dart';
import 'package:flagmatrix_studio/domain/repositories/flagmatrix_repository.dart';
import 'package:flagmatrix_studio/presentation/cubit/studio_cubit.dart';

final sl = GetIt.instance;

void setupServiceLocator() {
  if (sl.isRegistered<StudioCubit>()) return;

  sl.registerLazySingleton<Dio>(
    () => Dio(
      BaseOptions(
        baseUrl: 'http://localhost:8080',
        connectTimeout: const Duration(seconds: 8),
        receiveTimeout: const Duration(seconds: 15),
      ),
    ),
  );
  sl.registerLazySingleton<FlagMatrixRemoteDataSource>(
    () => FlagMatrixRemoteDataSource(sl<Dio>()),
  );
  sl.registerLazySingleton<FlagMatrixRepository>(
    () => FlagMatrixRepositoryImpl(sl<FlagMatrixRemoteDataSource>()),
  );
  sl.registerFactory<StudioCubit>(() => StudioCubit(sl<FlagMatrixRepository>()));
}
