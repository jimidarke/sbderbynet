import 'package:connectivity_plus/connectivity_plus.dart';

/// Utility class to check network connectivity status
class NetworkInfo {
  final Connectivity _connectivity;

  NetworkInfo(this._connectivity);

  /// Check if device is connected to internet
  Future<bool> get isConnected async {
    final result = await _connectivity.checkConnectivity();

    // Returns true if connected to WiFi, mobile data, or ethernet
    // Returns false if no connection
    return result.contains(ConnectivityResult.wifi) ||
        result.contains(ConnectivityResult.mobile) ||
        result.contains(ConnectivityResult.ethernet);
  }

  /// Stream of connectivity changes
  Stream<bool> get onConnectivityChanged {
    return _connectivity.onConnectivityChanged.map((results) {
      return results.contains(ConnectivityResult.wifi) ||
          results.contains(ConnectivityResult.mobile) ||
          results.contains(ConnectivityResult.ethernet);
    });
  }

  /// Check if connected to WiFi specifically
  Future<bool> get isConnectedToWifi async {
    final result = await _connectivity.checkConnectivity();
    return result.contains(ConnectivityResult.wifi);
  }
}
