// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'timer_state_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

TimerStateModel _$TimerStateModelFromJson(Map<String, dynamic> json) {
  return _TimerStateModel.fromJson(json);
}

/// @nodoc
mixin _$TimerStateModel {
  int get lanes => throw _privateConstructorUsedError;
  @JsonKey(name: 'last-contact')
  int get lastContact => throw _privateConstructorUsedError;
  int get state => throw _privateConstructorUsedError;
  String get icon => throw _privateConstructorUsedError;
  @JsonKey(name: 'remote-start')
  bool get remoteStart => throw _privateConstructorUsedError;
  String get message => throw _privateConstructorUsedError;
  List<TimerModel> get timers => throw _privateConstructorUsedError;
  @JsonKey(name: 'server_time')
  int get serverTime => throw _privateConstructorUsedError;
  @JsonKey(name: 'timers_online')
  int get timersOnline => throw _privateConstructorUsedError;
  @JsonKey(name: 'timers_ready')
  int get timersReady => throw _privateConstructorUsedError;
  @JsonKey(name: 'timers_required')
  int get timersRequired => throw _privateConstructorUsedError;
  @JsonKey(name: 'health_status')
  String get healthStatus => throw _privateConstructorUsedError;
  @JsonKey(name: 'health_message')
  String get healthMessage => throw _privateConstructorUsedError;

  /// Serializes this TimerStateModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of TimerStateModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $TimerStateModelCopyWith<TimerStateModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $TimerStateModelCopyWith<$Res> {
  factory $TimerStateModelCopyWith(
    TimerStateModel value,
    $Res Function(TimerStateModel) then,
  ) = _$TimerStateModelCopyWithImpl<$Res, TimerStateModel>;
  @useResult
  $Res call({
    int lanes,
    @JsonKey(name: 'last-contact') int lastContact,
    int state,
    String icon,
    @JsonKey(name: 'remote-start') bool remoteStart,
    String message,
    List<TimerModel> timers,
    @JsonKey(name: 'server_time') int serverTime,
    @JsonKey(name: 'timers_online') int timersOnline,
    @JsonKey(name: 'timers_ready') int timersReady,
    @JsonKey(name: 'timers_required') int timersRequired,
    @JsonKey(name: 'health_status') String healthStatus,
    @JsonKey(name: 'health_message') String healthMessage,
  });
}

/// @nodoc
class _$TimerStateModelCopyWithImpl<$Res, $Val extends TimerStateModel>
    implements $TimerStateModelCopyWith<$Res> {
  _$TimerStateModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of TimerStateModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? lanes = null,
    Object? lastContact = null,
    Object? state = null,
    Object? icon = null,
    Object? remoteStart = null,
    Object? message = null,
    Object? timers = null,
    Object? serverTime = null,
    Object? timersOnline = null,
    Object? timersReady = null,
    Object? timersRequired = null,
    Object? healthStatus = null,
    Object? healthMessage = null,
  }) {
    return _then(
      _value.copyWith(
            lanes: null == lanes
                ? _value.lanes
                : lanes // ignore: cast_nullable_to_non_nullable
                      as int,
            lastContact: null == lastContact
                ? _value.lastContact
                : lastContact // ignore: cast_nullable_to_non_nullable
                      as int,
            state: null == state
                ? _value.state
                : state // ignore: cast_nullable_to_non_nullable
                      as int,
            icon: null == icon
                ? _value.icon
                : icon // ignore: cast_nullable_to_non_nullable
                      as String,
            remoteStart: null == remoteStart
                ? _value.remoteStart
                : remoteStart // ignore: cast_nullable_to_non_nullable
                      as bool,
            message: null == message
                ? _value.message
                : message // ignore: cast_nullable_to_non_nullable
                      as String,
            timers: null == timers
                ? _value.timers
                : timers // ignore: cast_nullable_to_non_nullable
                      as List<TimerModel>,
            serverTime: null == serverTime
                ? _value.serverTime
                : serverTime // ignore: cast_nullable_to_non_nullable
                      as int,
            timersOnline: null == timersOnline
                ? _value.timersOnline
                : timersOnline // ignore: cast_nullable_to_non_nullable
                      as int,
            timersReady: null == timersReady
                ? _value.timersReady
                : timersReady // ignore: cast_nullable_to_non_nullable
                      as int,
            timersRequired: null == timersRequired
                ? _value.timersRequired
                : timersRequired // ignore: cast_nullable_to_non_nullable
                      as int,
            healthStatus: null == healthStatus
                ? _value.healthStatus
                : healthStatus // ignore: cast_nullable_to_non_nullable
                      as String,
            healthMessage: null == healthMessage
                ? _value.healthMessage
                : healthMessage // ignore: cast_nullable_to_non_nullable
                      as String,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$TimerStateModelImplCopyWith<$Res>
    implements $TimerStateModelCopyWith<$Res> {
  factory _$$TimerStateModelImplCopyWith(
    _$TimerStateModelImpl value,
    $Res Function(_$TimerStateModelImpl) then,
  ) = __$$TimerStateModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    int lanes,
    @JsonKey(name: 'last-contact') int lastContact,
    int state,
    String icon,
    @JsonKey(name: 'remote-start') bool remoteStart,
    String message,
    List<TimerModel> timers,
    @JsonKey(name: 'server_time') int serverTime,
    @JsonKey(name: 'timers_online') int timersOnline,
    @JsonKey(name: 'timers_ready') int timersReady,
    @JsonKey(name: 'timers_required') int timersRequired,
    @JsonKey(name: 'health_status') String healthStatus,
    @JsonKey(name: 'health_message') String healthMessage,
  });
}

/// @nodoc
class __$$TimerStateModelImplCopyWithImpl<$Res>
    extends _$TimerStateModelCopyWithImpl<$Res, _$TimerStateModelImpl>
    implements _$$TimerStateModelImplCopyWith<$Res> {
  __$$TimerStateModelImplCopyWithImpl(
    _$TimerStateModelImpl _value,
    $Res Function(_$TimerStateModelImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of TimerStateModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? lanes = null,
    Object? lastContact = null,
    Object? state = null,
    Object? icon = null,
    Object? remoteStart = null,
    Object? message = null,
    Object? timers = null,
    Object? serverTime = null,
    Object? timersOnline = null,
    Object? timersReady = null,
    Object? timersRequired = null,
    Object? healthStatus = null,
    Object? healthMessage = null,
  }) {
    return _then(
      _$TimerStateModelImpl(
        lanes: null == lanes
            ? _value.lanes
            : lanes // ignore: cast_nullable_to_non_nullable
                  as int,
        lastContact: null == lastContact
            ? _value.lastContact
            : lastContact // ignore: cast_nullable_to_non_nullable
                  as int,
        state: null == state
            ? _value.state
            : state // ignore: cast_nullable_to_non_nullable
                  as int,
        icon: null == icon
            ? _value.icon
            : icon // ignore: cast_nullable_to_non_nullable
                  as String,
        remoteStart: null == remoteStart
            ? _value.remoteStart
            : remoteStart // ignore: cast_nullable_to_non_nullable
                  as bool,
        message: null == message
            ? _value.message
            : message // ignore: cast_nullable_to_non_nullable
                  as String,
        timers: null == timers
            ? _value._timers
            : timers // ignore: cast_nullable_to_non_nullable
                  as List<TimerModel>,
        serverTime: null == serverTime
            ? _value.serverTime
            : serverTime // ignore: cast_nullable_to_non_nullable
                  as int,
        timersOnline: null == timersOnline
            ? _value.timersOnline
            : timersOnline // ignore: cast_nullable_to_non_nullable
                  as int,
        timersReady: null == timersReady
            ? _value.timersReady
            : timersReady // ignore: cast_nullable_to_non_nullable
                  as int,
        timersRequired: null == timersRequired
            ? _value.timersRequired
            : timersRequired // ignore: cast_nullable_to_non_nullable
                  as int,
        healthStatus: null == healthStatus
            ? _value.healthStatus
            : healthStatus // ignore: cast_nullable_to_non_nullable
                  as String,
        healthMessage: null == healthMessage
            ? _value.healthMessage
            : healthMessage // ignore: cast_nullable_to_non_nullable
                  as String,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$TimerStateModelImpl implements _TimerStateModel {
  const _$TimerStateModelImpl({
    required this.lanes,
    @JsonKey(name: 'last-contact') required this.lastContact,
    required this.state,
    required this.icon,
    @JsonKey(name: 'remote-start') this.remoteStart = false,
    this.message = '',
    final List<TimerModel> timers = const [],
    @JsonKey(name: 'server_time') this.serverTime = 0,
    @JsonKey(name: 'timers_online') this.timersOnline = 0,
    @JsonKey(name: 'timers_ready') this.timersReady = 0,
    @JsonKey(name: 'timers_required') this.timersRequired = 0,
    @JsonKey(name: 'health_status') this.healthStatus = 'unknown',
    @JsonKey(name: 'health_message') this.healthMessage = '',
  }) : _timers = timers;

  factory _$TimerStateModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$TimerStateModelImplFromJson(json);

  @override
  final int lanes;
  @override
  @JsonKey(name: 'last-contact')
  final int lastContact;
  @override
  final int state;
  @override
  final String icon;
  @override
  @JsonKey(name: 'remote-start')
  final bool remoteStart;
  @override
  @JsonKey()
  final String message;
  final List<TimerModel> _timers;
  @override
  @JsonKey()
  List<TimerModel> get timers {
    if (_timers is EqualUnmodifiableListView) return _timers;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_timers);
  }

  @override
  @JsonKey(name: 'server_time')
  final int serverTime;
  @override
  @JsonKey(name: 'timers_online')
  final int timersOnline;
  @override
  @JsonKey(name: 'timers_ready')
  final int timersReady;
  @override
  @JsonKey(name: 'timers_required')
  final int timersRequired;
  @override
  @JsonKey(name: 'health_status')
  final String healthStatus;
  @override
  @JsonKey(name: 'health_message')
  final String healthMessage;

  @override
  String toString() {
    return 'TimerStateModel(lanes: $lanes, lastContact: $lastContact, state: $state, icon: $icon, remoteStart: $remoteStart, message: $message, timers: $timers, serverTime: $serverTime, timersOnline: $timersOnline, timersReady: $timersReady, timersRequired: $timersRequired, healthStatus: $healthStatus, healthMessage: $healthMessage)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$TimerStateModelImpl &&
            (identical(other.lanes, lanes) || other.lanes == lanes) &&
            (identical(other.lastContact, lastContact) ||
                other.lastContact == lastContact) &&
            (identical(other.state, state) || other.state == state) &&
            (identical(other.icon, icon) || other.icon == icon) &&
            (identical(other.remoteStart, remoteStart) ||
                other.remoteStart == remoteStart) &&
            (identical(other.message, message) || other.message == message) &&
            const DeepCollectionEquality().equals(other._timers, _timers) &&
            (identical(other.serverTime, serverTime) ||
                other.serverTime == serverTime) &&
            (identical(other.timersOnline, timersOnline) ||
                other.timersOnline == timersOnline) &&
            (identical(other.timersReady, timersReady) ||
                other.timersReady == timersReady) &&
            (identical(other.timersRequired, timersRequired) ||
                other.timersRequired == timersRequired) &&
            (identical(other.healthStatus, healthStatus) ||
                other.healthStatus == healthStatus) &&
            (identical(other.healthMessage, healthMessage) ||
                other.healthMessage == healthMessage));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    lanes,
    lastContact,
    state,
    icon,
    remoteStart,
    message,
    const DeepCollectionEquality().hash(_timers),
    serverTime,
    timersOnline,
    timersReady,
    timersRequired,
    healthStatus,
    healthMessage,
  );

  /// Create a copy of TimerStateModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$TimerStateModelImplCopyWith<_$TimerStateModelImpl> get copyWith =>
      __$$TimerStateModelImplCopyWithImpl<_$TimerStateModelImpl>(
        this,
        _$identity,
      );

  @override
  Map<String, dynamic> toJson() {
    return _$$TimerStateModelImplToJson(this);
  }
}

abstract class _TimerStateModel implements TimerStateModel {
  const factory _TimerStateModel({
    required final int lanes,
    @JsonKey(name: 'last-contact') required final int lastContact,
    required final int state,
    required final String icon,
    @JsonKey(name: 'remote-start') final bool remoteStart,
    final String message,
    final List<TimerModel> timers,
    @JsonKey(name: 'server_time') final int serverTime,
    @JsonKey(name: 'timers_online') final int timersOnline,
    @JsonKey(name: 'timers_ready') final int timersReady,
    @JsonKey(name: 'timers_required') final int timersRequired,
    @JsonKey(name: 'health_status') final String healthStatus,
    @JsonKey(name: 'health_message') final String healthMessage,
  }) = _$TimerStateModelImpl;

  factory _TimerStateModel.fromJson(Map<String, dynamic> json) =
      _$TimerStateModelImpl.fromJson;

  @override
  int get lanes;
  @override
  @JsonKey(name: 'last-contact')
  int get lastContact;
  @override
  int get state;
  @override
  String get icon;
  @override
  @JsonKey(name: 'remote-start')
  bool get remoteStart;
  @override
  String get message;
  @override
  List<TimerModel> get timers;
  @override
  @JsonKey(name: 'server_time')
  int get serverTime;
  @override
  @JsonKey(name: 'timers_online')
  int get timersOnline;
  @override
  @JsonKey(name: 'timers_ready')
  int get timersReady;
  @override
  @JsonKey(name: 'timers_required')
  int get timersRequired;
  @override
  @JsonKey(name: 'health_status')
  String get healthStatus;
  @override
  @JsonKey(name: 'health_message')
  String get healthMessage;

  /// Create a copy of TimerStateModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$TimerStateModelImplCopyWith<_$TimerStateModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

TimerModel _$TimerModelFromJson(Map<String, dynamic> json) {
  return _TimerModel.fromJson(json);
}

/// @nodoc
mixin _$TimerModel {
  int get lane => throw _privateConstructorUsedError;
  @JsonKey(name: 'timerID')
  String get timerId => throw _privateConstructorUsedError;
  @JsonKey(name: 'last_heartbeat')
  int get lastHeartbeat => throw _privateConstructorUsedError;
  bool get ready => throw _privateConstructorUsedError;
  @JsonKey(name: 'is_starter')
  bool get isStarter => throw _privateConstructorUsedError;
  @JsonKey(name: 'is_online')
  bool get isOnline => throw _privateConstructorUsedError;
  @JsonKey(name: 'seconds_ago')
  int get secondsAgo => throw _privateConstructorUsedError;

  /// Serializes this TimerModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of TimerModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $TimerModelCopyWith<TimerModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $TimerModelCopyWith<$Res> {
  factory $TimerModelCopyWith(
    TimerModel value,
    $Res Function(TimerModel) then,
  ) = _$TimerModelCopyWithImpl<$Res, TimerModel>;
  @useResult
  $Res call({
    int lane,
    @JsonKey(name: 'timerID') String timerId,
    @JsonKey(name: 'last_heartbeat') int lastHeartbeat,
    bool ready,
    @JsonKey(name: 'is_starter') bool isStarter,
    @JsonKey(name: 'is_online') bool isOnline,
    @JsonKey(name: 'seconds_ago') int secondsAgo,
  });
}

/// @nodoc
class _$TimerModelCopyWithImpl<$Res, $Val extends TimerModel>
    implements $TimerModelCopyWith<$Res> {
  _$TimerModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of TimerModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? lane = null,
    Object? timerId = null,
    Object? lastHeartbeat = null,
    Object? ready = null,
    Object? isStarter = null,
    Object? isOnline = null,
    Object? secondsAgo = null,
  }) {
    return _then(
      _value.copyWith(
            lane: null == lane
                ? _value.lane
                : lane // ignore: cast_nullable_to_non_nullable
                      as int,
            timerId: null == timerId
                ? _value.timerId
                : timerId // ignore: cast_nullable_to_non_nullable
                      as String,
            lastHeartbeat: null == lastHeartbeat
                ? _value.lastHeartbeat
                : lastHeartbeat // ignore: cast_nullable_to_non_nullable
                      as int,
            ready: null == ready
                ? _value.ready
                : ready // ignore: cast_nullable_to_non_nullable
                      as bool,
            isStarter: null == isStarter
                ? _value.isStarter
                : isStarter // ignore: cast_nullable_to_non_nullable
                      as bool,
            isOnline: null == isOnline
                ? _value.isOnline
                : isOnline // ignore: cast_nullable_to_non_nullable
                      as bool,
            secondsAgo: null == secondsAgo
                ? _value.secondsAgo
                : secondsAgo // ignore: cast_nullable_to_non_nullable
                      as int,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$TimerModelImplCopyWith<$Res>
    implements $TimerModelCopyWith<$Res> {
  factory _$$TimerModelImplCopyWith(
    _$TimerModelImpl value,
    $Res Function(_$TimerModelImpl) then,
  ) = __$$TimerModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    int lane,
    @JsonKey(name: 'timerID') String timerId,
    @JsonKey(name: 'last_heartbeat') int lastHeartbeat,
    bool ready,
    @JsonKey(name: 'is_starter') bool isStarter,
    @JsonKey(name: 'is_online') bool isOnline,
    @JsonKey(name: 'seconds_ago') int secondsAgo,
  });
}

/// @nodoc
class __$$TimerModelImplCopyWithImpl<$Res>
    extends _$TimerModelCopyWithImpl<$Res, _$TimerModelImpl>
    implements _$$TimerModelImplCopyWith<$Res> {
  __$$TimerModelImplCopyWithImpl(
    _$TimerModelImpl _value,
    $Res Function(_$TimerModelImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of TimerModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? lane = null,
    Object? timerId = null,
    Object? lastHeartbeat = null,
    Object? ready = null,
    Object? isStarter = null,
    Object? isOnline = null,
    Object? secondsAgo = null,
  }) {
    return _then(
      _$TimerModelImpl(
        lane: null == lane
            ? _value.lane
            : lane // ignore: cast_nullable_to_non_nullable
                  as int,
        timerId: null == timerId
            ? _value.timerId
            : timerId // ignore: cast_nullable_to_non_nullable
                  as String,
        lastHeartbeat: null == lastHeartbeat
            ? _value.lastHeartbeat
            : lastHeartbeat // ignore: cast_nullable_to_non_nullable
                  as int,
        ready: null == ready
            ? _value.ready
            : ready // ignore: cast_nullable_to_non_nullable
                  as bool,
        isStarter: null == isStarter
            ? _value.isStarter
            : isStarter // ignore: cast_nullable_to_non_nullable
                  as bool,
        isOnline: null == isOnline
            ? _value.isOnline
            : isOnline // ignore: cast_nullable_to_non_nullable
                  as bool,
        secondsAgo: null == secondsAgo
            ? _value.secondsAgo
            : secondsAgo // ignore: cast_nullable_to_non_nullable
                  as int,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$TimerModelImpl implements _TimerModel {
  const _$TimerModelImpl({
    required this.lane,
    @JsonKey(name: 'timerID') required this.timerId,
    @JsonKey(name: 'last_heartbeat') required this.lastHeartbeat,
    this.ready = false,
    @JsonKey(name: 'is_starter') this.isStarter = false,
    @JsonKey(name: 'is_online') this.isOnline = false,
    @JsonKey(name: 'seconds_ago') this.secondsAgo = 0,
  });

  factory _$TimerModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$TimerModelImplFromJson(json);

  @override
  final int lane;
  @override
  @JsonKey(name: 'timerID')
  final String timerId;
  @override
  @JsonKey(name: 'last_heartbeat')
  final int lastHeartbeat;
  @override
  @JsonKey()
  final bool ready;
  @override
  @JsonKey(name: 'is_starter')
  final bool isStarter;
  @override
  @JsonKey(name: 'is_online')
  final bool isOnline;
  @override
  @JsonKey(name: 'seconds_ago')
  final int secondsAgo;

  @override
  String toString() {
    return 'TimerModel(lane: $lane, timerId: $timerId, lastHeartbeat: $lastHeartbeat, ready: $ready, isStarter: $isStarter, isOnline: $isOnline, secondsAgo: $secondsAgo)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$TimerModelImpl &&
            (identical(other.lane, lane) || other.lane == lane) &&
            (identical(other.timerId, timerId) || other.timerId == timerId) &&
            (identical(other.lastHeartbeat, lastHeartbeat) ||
                other.lastHeartbeat == lastHeartbeat) &&
            (identical(other.ready, ready) || other.ready == ready) &&
            (identical(other.isStarter, isStarter) ||
                other.isStarter == isStarter) &&
            (identical(other.isOnline, isOnline) ||
                other.isOnline == isOnline) &&
            (identical(other.secondsAgo, secondsAgo) ||
                other.secondsAgo == secondsAgo));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    lane,
    timerId,
    lastHeartbeat,
    ready,
    isStarter,
    isOnline,
    secondsAgo,
  );

  /// Create a copy of TimerModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$TimerModelImplCopyWith<_$TimerModelImpl> get copyWith =>
      __$$TimerModelImplCopyWithImpl<_$TimerModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$TimerModelImplToJson(this);
  }
}

abstract class _TimerModel implements TimerModel {
  const factory _TimerModel({
    required final int lane,
    @JsonKey(name: 'timerID') required final String timerId,
    @JsonKey(name: 'last_heartbeat') required final int lastHeartbeat,
    final bool ready,
    @JsonKey(name: 'is_starter') final bool isStarter,
    @JsonKey(name: 'is_online') final bool isOnline,
    @JsonKey(name: 'seconds_ago') final int secondsAgo,
  }) = _$TimerModelImpl;

  factory _TimerModel.fromJson(Map<String, dynamic> json) =
      _$TimerModelImpl.fromJson;

  @override
  int get lane;
  @override
  @JsonKey(name: 'timerID')
  String get timerId;
  @override
  @JsonKey(name: 'last_heartbeat')
  int get lastHeartbeat;
  @override
  bool get ready;
  @override
  @JsonKey(name: 'is_starter')
  bool get isStarter;
  @override
  @JsonKey(name: 'is_online')
  bool get isOnline;
  @override
  @JsonKey(name: 'seconds_ago')
  int get secondsAgo;

  /// Create a copy of TimerModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$TimerModelImplCopyWith<_$TimerModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
