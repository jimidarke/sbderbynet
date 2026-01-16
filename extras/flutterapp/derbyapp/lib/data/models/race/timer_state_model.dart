import 'package:freezed_annotation/freezed_annotation.dart';

part 'timer_state_model.freezed.dart';
part 'timer_state_model.g.dart';

@freezed
class TimerStateModel with _$TimerStateModel {
  const factory TimerStateModel({
    required int lanes,
    @JsonKey(name: 'last-contact') required int lastContact,
    required int state,
    required String icon,
    @JsonKey(name: 'remote-start') @Default(false) bool remoteStart,
    @Default('') String message,
    @Default([]) List<TimerModel> timers,
    @JsonKey(name: 'server_time') @Default(0) int serverTime,
    @JsonKey(name: 'timers_online') @Default(0) int timersOnline,
    @JsonKey(name: 'timers_ready') @Default(0) int timersReady,
    @JsonKey(name: 'timers_required') @Default(0) int timersRequired,
    @JsonKey(name: 'health_status') @Default('unknown') String healthStatus,
    @JsonKey(name: 'health_message') @Default('') String healthMessage,
  }) = _TimerStateModel;

  factory TimerStateModel.fromJson(Map<String, dynamic> json) =>
      _$TimerStateModelFromJson(json);
}

@freezed
class TimerModel with _$TimerModel {
  const factory TimerModel({
    required int lane,
    @JsonKey(name: 'timerID') required String timerId,
    @JsonKey(name: 'last_heartbeat') required int lastHeartbeat,
    @Default(false) bool ready,
    @JsonKey(name: 'is_starter') @Default(false) bool isStarter,
    @JsonKey(name: 'is_online') @Default(false) bool isOnline,
    @JsonKey(name: 'seconds_ago') @Default(0) int secondsAgo,
  }) = _TimerModel;

  factory TimerModel.fromJson(Map<String, dynamic> json) =>
      _$TimerModelFromJson(json);
}
