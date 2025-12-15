import '../../../core/constants/api_endpoints.dart';
import '../../../core/network/dio_client.dart';
import '../../../core/errors/exceptions.dart';
import '../../models/race/coordinator_poll_response.dart';
import '../../models/race/ondeck_entry_model.dart';
import '../../models/race/heat_detail_model.dart';
import '../../models/race/heat_result_model.dart';

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

  /// Get ondeck chart with heat history and results
  Future<OnDeckResponse> getOnDeckChart() async {
    try {
      final response = await _dioClient.get(ApiEndpoints.pollOnDeck);

      if (response.data == null) {
        throw const ServerException('Empty response from server');
      }

      return OnDeckResponse.fromJson(
        response.data as Map<String, dynamic>,
      );
    } catch (e) {
      if (e is ServerException || e is NetworkException) {
        rethrow;
      }
      throw ServerException('Failed to fetch ondeck data: ${e.toString()}');
    }
  }

  /// Get specific heat detail by polling coordinator with roundid+heat
  Future<HeatDetailModel> getHeatDetail({
    required int roundId,
    required int heat,
  }) async {
    try {
      // Use existing pollCoordinator with specific heat
      final response = await pollCoordinator(roundId: roundId, heat: heat);

      // Extract round name from rounds array
      final round = response.rounds.firstWhere(
        (r) => r.roundid == roundId,
        orElse: () => throw const ServerException('Round not found'),
      );

      // Parse heat results
      final results = response.heatResults
          .map((json) => HeatResultModel.fromJson(json))
          .toList();

      // Check if results are available
      final hasResults = results.isNotEmpty;

      return HeatDetailModel(
        roundId: roundId,
        heat: heat,
        roundName: round.roundname,
        className: round.class_,
        racers: response.racers,
        results: results,
        isComplete: hasResults,
        completedAt: hasResults ? DateTime.now() : null,
      );
    } catch (e) {
      if (e is ServerException || e is NetworkException) {
        rethrow;
      }
      throw ServerException('Failed to fetch heat detail: ${e.toString()}');
    }
  }
}
