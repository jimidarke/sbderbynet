// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'timer_state_model.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

_$TimerStateModelImpl _$$TimerStateModelImplFromJson(
  Map<String, dynamic> json,
) => _$TimerStateModelImpl(
  lanes: (json['lanes'] as num).toInt(),
  lastContact: (json['last-contact'] as num).toInt(),
  state: (json['state'] as num).toInt(),
  icon: json['icon'] as String,
  remoteStart: json['remote-start'] as bool? ?? false,
  message: json['message'] as String? ?? '',
  timers:
      (json['timers'] as List<dynamic>?)
          ?.map((e) => TimerModel.fromJson(e as Map<String, dynamic>))
          .toList() ??
      const [],
  serverTime: (json['server_time'] as num?)?.toInt() ?? 0,
  timersOnline: (json['timers_online'] as num?)?.toInt() ?? 0,
  timersReady: (json['timers_ready'] as num?)?.toInt() ?? 0,
  timersRequired: (json['timers_required'] as num?)?.toInt() ?? 0,
  healthStatus: json['health_status'] as String? ?? 'unknown',
  healthMessage: json['health_message'] as String? ?? '',
);

Map<String, dynamic> _$$TimerStateModelImplToJson(
  _$TimerStateModelImpl instance,
) => <String, dynamic>{
  'lanes': instance.lanes,
  'last-contact': instance.lastContact,
  'state': instance.state,
  'icon': instance.icon,
  'remote-start': instance.remoteStart,
  'message': instance.message,
  'timers': instance.timers,
  'server_time': instance.serverTime,
  'timers_online': instance.timersOnline,
  'timers_ready': instance.timersReady,
  'timers_required': instance.timersRequired,
  'health_status': instance.healthStatus,
  'health_message': instance.healthMessage,
};

_$TimerModelImpl _$$TimerModelImplFromJson(Map<String, dynamic> json) =>
    _$TimerModelImpl(
      lane: (json['lane'] as num).toInt(),
      timerId: json['timerID'] as String,
      lastHeartbeat: (json['last_heartbeat'] as num).toInt(),
      ready: json['ready'] as bool? ?? false,
      isStarter: json['is_starter'] as bool? ?? false,
      isOnline: json['is_online'] as bool? ?? false,
      secondsAgo: (json['seconds_ago'] as num?)?.toInt() ?? 0,
    );

Map<String, dynamic> _$$TimerModelImplToJson(_$TimerModelImpl instance) =>
    <String, dynamic>{
      'lane': instance.lane,
      'timerID': instance.timerId,
      'last_heartbeat': instance.lastHeartbeat,
      'ready': instance.ready,
      'is_starter': instance.isStarter,
      'is_online': instance.isOnline,
      'seconds_ago': instance.secondsAgo,
    };
