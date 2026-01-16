// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'coordinator_poll_response.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

CoordinatorPollResponse _$CoordinatorPollResponseFromJson(
  Map<String, dynamic> json,
) {
  return _CoordinatorPollResponse.fromJson(json);
}

/// @nodoc
mixin _$CoordinatorPollResponse {
  @JsonKey(name: 'current-heat')
  CurrentHeatModel get currentHeat => throw _privateConstructorUsedError;
  List<RacerModel> get racers => throw _privateConstructorUsedError;
  @JsonKey(name: 'timer-state')
  TimerStateModel get timerState => throw _privateConstructorUsedError;
  @JsonKey(name: 'race-integrity')
  RaceIntegrityModel get raceIntegrity => throw _privateConstructorUsedError;
  List<RoundModel> get rounds => throw _privateConstructorUsedError;
  @JsonKey(name: 'heat-results')
  List<Map<String, dynamic>> get heatResults =>
      throw _privateConstructorUsedError;
  @JsonKey(name: 'last-heat')
  String get lastHeat => throw _privateConstructorUsedError;
  @JsonKey(name: 'refused-results')
  int get refusedResults => throw _privateConstructorUsedError;
  @JsonKey(name: 'current-scene')
  String get currentScene => throw _privateConstructorUsedError;

  /// Serializes this CoordinatorPollResponse to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of CoordinatorPollResponse
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $CoordinatorPollResponseCopyWith<CoordinatorPollResponse> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $CoordinatorPollResponseCopyWith<$Res> {
  factory $CoordinatorPollResponseCopyWith(
    CoordinatorPollResponse value,
    $Res Function(CoordinatorPollResponse) then,
  ) = _$CoordinatorPollResponseCopyWithImpl<$Res, CoordinatorPollResponse>;
  @useResult
  $Res call({
    @JsonKey(name: 'current-heat') CurrentHeatModel currentHeat,
    List<RacerModel> racers,
    @JsonKey(name: 'timer-state') TimerStateModel timerState,
    @JsonKey(name: 'race-integrity') RaceIntegrityModel raceIntegrity,
    List<RoundModel> rounds,
    @JsonKey(name: 'heat-results') List<Map<String, dynamic>> heatResults,
    @JsonKey(name: 'last-heat') String lastHeat,
    @JsonKey(name: 'refused-results') int refusedResults,
    @JsonKey(name: 'current-scene') String currentScene,
  });

  $CurrentHeatModelCopyWith<$Res> get currentHeat;
  $TimerStateModelCopyWith<$Res> get timerState;
  $RaceIntegrityModelCopyWith<$Res> get raceIntegrity;
}

/// @nodoc
class _$CoordinatorPollResponseCopyWithImpl<
  $Res,
  $Val extends CoordinatorPollResponse
>
    implements $CoordinatorPollResponseCopyWith<$Res> {
  _$CoordinatorPollResponseCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of CoordinatorPollResponse
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? currentHeat = null,
    Object? racers = null,
    Object? timerState = null,
    Object? raceIntegrity = null,
    Object? rounds = null,
    Object? heatResults = null,
    Object? lastHeat = null,
    Object? refusedResults = null,
    Object? currentScene = null,
  }) {
    return _then(
      _value.copyWith(
            currentHeat: null == currentHeat
                ? _value.currentHeat
                : currentHeat // ignore: cast_nullable_to_non_nullable
                      as CurrentHeatModel,
            racers: null == racers
                ? _value.racers
                : racers // ignore: cast_nullable_to_non_nullable
                      as List<RacerModel>,
            timerState: null == timerState
                ? _value.timerState
                : timerState // ignore: cast_nullable_to_non_nullable
                      as TimerStateModel,
            raceIntegrity: null == raceIntegrity
                ? _value.raceIntegrity
                : raceIntegrity // ignore: cast_nullable_to_non_nullable
                      as RaceIntegrityModel,
            rounds: null == rounds
                ? _value.rounds
                : rounds // ignore: cast_nullable_to_non_nullable
                      as List<RoundModel>,
            heatResults: null == heatResults
                ? _value.heatResults
                : heatResults // ignore: cast_nullable_to_non_nullable
                      as List<Map<String, dynamic>>,
            lastHeat: null == lastHeat
                ? _value.lastHeat
                : lastHeat // ignore: cast_nullable_to_non_nullable
                      as String,
            refusedResults: null == refusedResults
                ? _value.refusedResults
                : refusedResults // ignore: cast_nullable_to_non_nullable
                      as int,
            currentScene: null == currentScene
                ? _value.currentScene
                : currentScene // ignore: cast_nullable_to_non_nullable
                      as String,
          )
          as $Val,
    );
  }

  /// Create a copy of CoordinatorPollResponse
  /// with the given fields replaced by the non-null parameter values.
  @override
  @pragma('vm:prefer-inline')
  $CurrentHeatModelCopyWith<$Res> get currentHeat {
    return $CurrentHeatModelCopyWith<$Res>(_value.currentHeat, (value) {
      return _then(_value.copyWith(currentHeat: value) as $Val);
    });
  }

  /// Create a copy of CoordinatorPollResponse
  /// with the given fields replaced by the non-null parameter values.
  @override
  @pragma('vm:prefer-inline')
  $TimerStateModelCopyWith<$Res> get timerState {
    return $TimerStateModelCopyWith<$Res>(_value.timerState, (value) {
      return _then(_value.copyWith(timerState: value) as $Val);
    });
  }

  /// Create a copy of CoordinatorPollResponse
  /// with the given fields replaced by the non-null parameter values.
  @override
  @pragma('vm:prefer-inline')
  $RaceIntegrityModelCopyWith<$Res> get raceIntegrity {
    return $RaceIntegrityModelCopyWith<$Res>(_value.raceIntegrity, (value) {
      return _then(_value.copyWith(raceIntegrity: value) as $Val);
    });
  }
}

/// @nodoc
abstract class _$$CoordinatorPollResponseImplCopyWith<$Res>
    implements $CoordinatorPollResponseCopyWith<$Res> {
  factory _$$CoordinatorPollResponseImplCopyWith(
    _$CoordinatorPollResponseImpl value,
    $Res Function(_$CoordinatorPollResponseImpl) then,
  ) = __$$CoordinatorPollResponseImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    @JsonKey(name: 'current-heat') CurrentHeatModel currentHeat,
    List<RacerModel> racers,
    @JsonKey(name: 'timer-state') TimerStateModel timerState,
    @JsonKey(name: 'race-integrity') RaceIntegrityModel raceIntegrity,
    List<RoundModel> rounds,
    @JsonKey(name: 'heat-results') List<Map<String, dynamic>> heatResults,
    @JsonKey(name: 'last-heat') String lastHeat,
    @JsonKey(name: 'refused-results') int refusedResults,
    @JsonKey(name: 'current-scene') String currentScene,
  });

  @override
  $CurrentHeatModelCopyWith<$Res> get currentHeat;
  @override
  $TimerStateModelCopyWith<$Res> get timerState;
  @override
  $RaceIntegrityModelCopyWith<$Res> get raceIntegrity;
}

/// @nodoc
class __$$CoordinatorPollResponseImplCopyWithImpl<$Res>
    extends
        _$CoordinatorPollResponseCopyWithImpl<
          $Res,
          _$CoordinatorPollResponseImpl
        >
    implements _$$CoordinatorPollResponseImplCopyWith<$Res> {
  __$$CoordinatorPollResponseImplCopyWithImpl(
    _$CoordinatorPollResponseImpl _value,
    $Res Function(_$CoordinatorPollResponseImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of CoordinatorPollResponse
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? currentHeat = null,
    Object? racers = null,
    Object? timerState = null,
    Object? raceIntegrity = null,
    Object? rounds = null,
    Object? heatResults = null,
    Object? lastHeat = null,
    Object? refusedResults = null,
    Object? currentScene = null,
  }) {
    return _then(
      _$CoordinatorPollResponseImpl(
        currentHeat: null == currentHeat
            ? _value.currentHeat
            : currentHeat // ignore: cast_nullable_to_non_nullable
                  as CurrentHeatModel,
        racers: null == racers
            ? _value._racers
            : racers // ignore: cast_nullable_to_non_nullable
                  as List<RacerModel>,
        timerState: null == timerState
            ? _value.timerState
            : timerState // ignore: cast_nullable_to_non_nullable
                  as TimerStateModel,
        raceIntegrity: null == raceIntegrity
            ? _value.raceIntegrity
            : raceIntegrity // ignore: cast_nullable_to_non_nullable
                  as RaceIntegrityModel,
        rounds: null == rounds
            ? _value._rounds
            : rounds // ignore: cast_nullable_to_non_nullable
                  as List<RoundModel>,
        heatResults: null == heatResults
            ? _value._heatResults
            : heatResults // ignore: cast_nullable_to_non_nullable
                  as List<Map<String, dynamic>>,
        lastHeat: null == lastHeat
            ? _value.lastHeat
            : lastHeat // ignore: cast_nullable_to_non_nullable
                  as String,
        refusedResults: null == refusedResults
            ? _value.refusedResults
            : refusedResults // ignore: cast_nullable_to_non_nullable
                  as int,
        currentScene: null == currentScene
            ? _value.currentScene
            : currentScene // ignore: cast_nullable_to_non_nullable
                  as String,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$CoordinatorPollResponseImpl implements _CoordinatorPollResponse {
  const _$CoordinatorPollResponseImpl({
    @JsonKey(name: 'current-heat') required this.currentHeat,
    final List<RacerModel> racers = const [],
    @JsonKey(name: 'timer-state') required this.timerState,
    @JsonKey(name: 'race-integrity') required this.raceIntegrity,
    final List<RoundModel> rounds = const [],
    @JsonKey(name: 'heat-results')
    final List<Map<String, dynamic>> heatResults = const [],
    @JsonKey(name: 'last-heat') this.lastHeat = 'none',
    @JsonKey(name: 'refused-results') this.refusedResults = 0,
    @JsonKey(name: 'current-scene') this.currentScene = '',
  }) : _racers = racers,
       _rounds = rounds,
       _heatResults = heatResults;

  factory _$CoordinatorPollResponseImpl.fromJson(Map<String, dynamic> json) =>
      _$$CoordinatorPollResponseImplFromJson(json);

  @override
  @JsonKey(name: 'current-heat')
  final CurrentHeatModel currentHeat;
  final List<RacerModel> _racers;
  @override
  @JsonKey()
  List<RacerModel> get racers {
    if (_racers is EqualUnmodifiableListView) return _racers;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_racers);
  }

  @override
  @JsonKey(name: 'timer-state')
  final TimerStateModel timerState;
  @override
  @JsonKey(name: 'race-integrity')
  final RaceIntegrityModel raceIntegrity;
  final List<RoundModel> _rounds;
  @override
  @JsonKey()
  List<RoundModel> get rounds {
    if (_rounds is EqualUnmodifiableListView) return _rounds;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_rounds);
  }

  final List<Map<String, dynamic>> _heatResults;
  @override
  @JsonKey(name: 'heat-results')
  List<Map<String, dynamic>> get heatResults {
    if (_heatResults is EqualUnmodifiableListView) return _heatResults;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_heatResults);
  }

  @override
  @JsonKey(name: 'last-heat')
  final String lastHeat;
  @override
  @JsonKey(name: 'refused-results')
  final int refusedResults;
  @override
  @JsonKey(name: 'current-scene')
  final String currentScene;

  @override
  String toString() {
    return 'CoordinatorPollResponse(currentHeat: $currentHeat, racers: $racers, timerState: $timerState, raceIntegrity: $raceIntegrity, rounds: $rounds, heatResults: $heatResults, lastHeat: $lastHeat, refusedResults: $refusedResults, currentScene: $currentScene)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$CoordinatorPollResponseImpl &&
            (identical(other.currentHeat, currentHeat) ||
                other.currentHeat == currentHeat) &&
            const DeepCollectionEquality().equals(other._racers, _racers) &&
            (identical(other.timerState, timerState) ||
                other.timerState == timerState) &&
            (identical(other.raceIntegrity, raceIntegrity) ||
                other.raceIntegrity == raceIntegrity) &&
            const DeepCollectionEquality().equals(other._rounds, _rounds) &&
            const DeepCollectionEquality().equals(
              other._heatResults,
              _heatResults,
            ) &&
            (identical(other.lastHeat, lastHeat) ||
                other.lastHeat == lastHeat) &&
            (identical(other.refusedResults, refusedResults) ||
                other.refusedResults == refusedResults) &&
            (identical(other.currentScene, currentScene) ||
                other.currentScene == currentScene));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    currentHeat,
    const DeepCollectionEquality().hash(_racers),
    timerState,
    raceIntegrity,
    const DeepCollectionEquality().hash(_rounds),
    const DeepCollectionEquality().hash(_heatResults),
    lastHeat,
    refusedResults,
    currentScene,
  );

  /// Create a copy of CoordinatorPollResponse
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$CoordinatorPollResponseImplCopyWith<_$CoordinatorPollResponseImpl>
  get copyWith =>
      __$$CoordinatorPollResponseImplCopyWithImpl<
        _$CoordinatorPollResponseImpl
      >(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$CoordinatorPollResponseImplToJson(this);
  }
}

abstract class _CoordinatorPollResponse implements CoordinatorPollResponse {
  const factory _CoordinatorPollResponse({
    @JsonKey(name: 'current-heat') required final CurrentHeatModel currentHeat,
    final List<RacerModel> racers,
    @JsonKey(name: 'timer-state') required final TimerStateModel timerState,
    @JsonKey(name: 'race-integrity')
    required final RaceIntegrityModel raceIntegrity,
    final List<RoundModel> rounds,
    @JsonKey(name: 'heat-results') final List<Map<String, dynamic>> heatResults,
    @JsonKey(name: 'last-heat') final String lastHeat,
    @JsonKey(name: 'refused-results') final int refusedResults,
    @JsonKey(name: 'current-scene') final String currentScene,
  }) = _$CoordinatorPollResponseImpl;

  factory _CoordinatorPollResponse.fromJson(Map<String, dynamic> json) =
      _$CoordinatorPollResponseImpl.fromJson;

  @override
  @JsonKey(name: 'current-heat')
  CurrentHeatModel get currentHeat;
  @override
  List<RacerModel> get racers;
  @override
  @JsonKey(name: 'timer-state')
  TimerStateModel get timerState;
  @override
  @JsonKey(name: 'race-integrity')
  RaceIntegrityModel get raceIntegrity;
  @override
  List<RoundModel> get rounds;
  @override
  @JsonKey(name: 'heat-results')
  List<Map<String, dynamic>> get heatResults;
  @override
  @JsonKey(name: 'last-heat')
  String get lastHeat;
  @override
  @JsonKey(name: 'refused-results')
  int get refusedResults;
  @override
  @JsonKey(name: 'current-scene')
  String get currentScene;

  /// Create a copy of CoordinatorPollResponse
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$CoordinatorPollResponseImplCopyWith<_$CoordinatorPollResponseImpl>
  get copyWith => throw _privateConstructorUsedError;
}
