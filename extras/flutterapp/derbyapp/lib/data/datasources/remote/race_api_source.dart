import '../../../core/constants/api_endpoints.dart';
import '../../../core/network/dio_client.dart';
import '../../../core/errors/exceptions.dart';
import '../../models/race/coordinator_poll_response.dart';

/// Remote data source for race data API calls to DerbyNet server
class RaceApiSource {
  final DioClient _dioClient;

  RaceApiSource(this._dioClient);

  /// Poll coordinator endpoint for race status
  /// This is the main endpoint for getting real-time race information
  Future<CoordinatorPollResponse> pollCoordinator({
    int? roundId,
    int? heat,
  }) async {
    try {
      final queryParams = <String, dynamic>{};
      if (roundId != null) queryParams['roundid'] = roundId;
      if (heat != null) queryParams['heat'] = heat;

      final response = await _dioClient.get(
        ApiEndpoints.pollCoordinator,
        queryParameters: queryParams.isNotEmpty ? queryParams : null,
      );

      if (response.data == null) {
        throw const ServerException('Empty response from server');
      }

      return CoordinatorPollResponse.fromJson(
        response.data as Map<String, dynamic>,
      );
    } catch (e) {
      if (e is ServerException || e is NetworkException) {
        rethrow;
      }
      throw ServerException('Failed to fetch race data: ${e.toString()}');
    }
  }

  /// Get racer list (for future use)
  Future<List<Map<String, dynamic>>> getRacerList() async {
    try {
      final response = await _dioClient.get(ApiEndpoints.racerList);

      if (response.data == null) {
        throw const ServerException('Empty response from server');
      }

      final data = response.data as Map<String, dynamic>;
      return List<Map<String, dynamic>>.from(data['racers'] ?? []);
    } catch (e) {
      if (e is ServerException || e is NetworkException) {
        rethrow;
      }
      throw ServerException('Failed to fetch racer list: ${e.toString()}');
    }
  }

  /// Get class list (for future use)
  Future<List<Map<String, dynamic>>> getClassList() async {
    try {
      final response = await _dioClient.get(ApiEndpoints.classList);

      if (response.data == null) {
        throw const ServerException('Empty response from server');
      }

      final data = response.data as Map<String, dynamic>;
      return List<Map<String, dynamic>>.from(data['classes'] ?? []);
    } catch (e) {
      if (e is ServerException || e is NetworkException) {
        rethrow;
      }
      throw ServerException('Failed to fetch class list: ${e.toString()}');
    }
  }
}
