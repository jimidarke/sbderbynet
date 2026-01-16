// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'current_heat_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

CurrentHeatModel _$CurrentHeatModelFromJson(Map<String, dynamic> json) {
  return _CurrentHeatModel.fromJson(json);
}

/// @nodoc
mixin _$CurrentHeatModel {
  @JsonKey(name: 'now_racing')
  bool get nowRacing => throw _privateConstructorUsedError;
  @JsonKey(name: 'use_master_sched')
  bool get useMasterSched => throw _privateConstructorUsedError;
  @JsonKey(name: 'use_points')
  bool get usePoints => throw _privateConstructorUsedError;
  int? get classid => throw _privateConstructorUsedError;
  int? get roundid => throw _privateConstructorUsedError;
  int? get round => throw _privateConstructorUsedError;
  @JsonKey(name: 'tbodyid')
  int? get tbodyId => throw _privateConstructorUsedError;
  int? get heat => throw _privateConstructorUsedError;
  @JsonKey(name: 'number-of-heats')
  int get numberOfHeats => throw _privateConstructorUsedError;
  @JsonKey(name: 'class')
  String? get className => throw _privateConstructorUsedError;
  int? get masterheat => throw _privateConstructorUsedError;
  @JsonKey(name: 'max_masterheat')
  int? get maxMasterheat => throw _privateConstructorUsedError;

  /// Serializes this CurrentHeatModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of CurrentHeatModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $CurrentHeatModelCopyWith<CurrentHeatModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $CurrentHeatModelCopyWith<$Res> {
  factory $CurrentHeatModelCopyWith(
    CurrentHeatModel value,
    $Res Function(CurrentHeatModel) then,
  ) = _$CurrentHeatModelCopyWithImpl<$Res, CurrentHeatModel>;
  @useResult
  $Res call({
    @JsonKey(name: 'now_racing') bool nowRacing,
    @JsonKey(name: 'use_master_sched') bool useMasterSched,
    @JsonKey(name: 'use_points') bool usePoints,
    int? classid,
    int? roundid,
    int? round,
    @JsonKey(name: 'tbodyid') int? tbodyId,
    int? heat,
    @JsonKey(name: 'number-of-heats') int numberOfHeats,
    @JsonKey(name: 'class') String? className,
    int? masterheat,
    @JsonKey(name: 'max_masterheat') int? maxMasterheat,
  });
}

/// @nodoc
class _$CurrentHeatModelCopyWithImpl<$Res, $Val extends CurrentHeatModel>
    implements $CurrentHeatModelCopyWith<$Res> {
  _$CurrentHeatModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of CurrentHeatModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? nowRacing = null,
    Object? useMasterSched = null,
    Object? usePoints = null,
    Object? classid = freezed,
    Object? roundid = freezed,
    Object? round = freezed,
    Object? tbodyId = freezed,
    Object? heat = freezed,
    Object? numberOfHeats = null,
    Object? className = freezed,
    Object? masterheat = freezed,
    Object? maxMasterheat = freezed,
  }) {
    return _then(
      _value.copyWith(
            nowRacing: null == nowRacing
                ? _value.nowRacing
                : nowRacing // ignore: cast_nullable_to_non_nullable
                      as bool,
            useMasterSched: null == useMasterSched
                ? _value.useMasterSched
                : useMasterSched // ignore: cast_nullable_to_non_nullable
                      as bool,
            usePoints: null == usePoints
                ? _value.usePoints
                : usePoints // ignore: cast_nullable_to_non_nullable
                      as bool,
            classid: freezed == classid
                ? _value.classid
                : classid // ignore: cast_nullable_to_non_nullable
                      as int?,
            roundid: freezed == roundid
                ? _value.roundid
                : roundid // ignore: cast_nullable_to_non_nullable
                      as int?,
            round: freezed == round
                ? _value.round
                : round // ignore: cast_nullable_to_non_nullable
                      as int?,
            tbodyId: freezed == tbodyId
                ? _value.tbodyId
                : tbodyId // ignore: cast_nullable_to_non_nullable
                      as int?,
            heat: freezed == heat
                ? _value.heat
                : heat // ignore: cast_nullable_to_non_nullable
                      as int?,
            numberOfHeats: null == numberOfHeats
                ? _value.numberOfHeats
                : numberOfHeats // ignore: cast_nullable_to_non_nullable
                      as int,
            className: freezed == className
                ? _value.className
                : className // ignore: cast_nullable_to_non_nullable
                      as String?,
            masterheat: freezed == masterheat
                ? _value.masterheat
                : masterheat // ignore: cast_nullable_to_non_nullable
                      as int?,
            maxMasterheat: freezed == maxMasterheat
                ? _value.maxMasterheat
                : maxMasterheat // ignore: cast_nullable_to_non_nullable
                      as int?,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$CurrentHeatModelImplCopyWith<$Res>
    implements $CurrentHeatModelCopyWith<$Res> {
  factory _$$CurrentHeatModelImplCopyWith(
    _$CurrentHeatModelImpl value,
    $Res Function(_$CurrentHeatModelImpl) then,
  ) = __$$CurrentHeatModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    @JsonKey(name: 'now_racing') bool nowRacing,
    @JsonKey(name: 'use_master_sched') bool useMasterSched,
    @JsonKey(name: 'use_points') bool usePoints,
    int? classid,
    int? roundid,
    int? round,
    @JsonKey(name: 'tbodyid') int? tbodyId,
    int? heat,
    @JsonKey(name: 'number-of-heats') int numberOfHeats,
    @JsonKey(name: 'class') String? className,
    int? masterheat,
    @JsonKey(name: 'max_masterheat') int? maxMasterheat,
  });
}

/// @nodoc
class __$$CurrentHeatModelImplCopyWithImpl<$Res>
    extends _$CurrentHeatModelCopyWithImpl<$Res, _$CurrentHeatModelImpl>
    implements _$$CurrentHeatModelImplCopyWith<$Res> {
  __$$CurrentHeatModelImplCopyWithImpl(
    _$CurrentHeatModelImpl _value,
    $Res Function(_$CurrentHeatModelImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of CurrentHeatModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? nowRacing = null,
    Object? useMasterSched = null,
    Object? usePoints = null,
    Object? classid = freezed,
    Object? roundid = freezed,
    Object? round = freezed,
    Object? tbodyId = freezed,
    Object? heat = freezed,
    Object? numberOfHeats = null,
    Object? className = freezed,
    Object? masterheat = freezed,
    Object? maxMasterheat = freezed,
  }) {
    return _then(
      _$CurrentHeatModelImpl(
        nowRacing: null == nowRacing
            ? _value.nowRacing
            : nowRacing // ignore: cast_nullable_to_non_nullable
                  as bool,
        useMasterSched: null == useMasterSched
            ? _value.useMasterSched
            : useMasterSched // ignore: cast_nullable_to_non_nullable
                  as bool,
        usePoints: null == usePoints
            ? _value.usePoints
            : usePoints // ignore: cast_nullable_to_non_nullable
                  as bool,
        classid: freezed == classid
            ? _value.classid
            : classid // ignore: cast_nullable_to_non_nullable
                  as int?,
        roundid: freezed == roundid
            ? _value.roundid
            : roundid // ignore: cast_nullable_to_non_nullable
                  as int?,
        round: freezed == round
            ? _value.round
            : round // ignore: cast_nullable_to_non_nullable
                  as int?,
        tbodyId: freezed == tbodyId
            ? _value.tbodyId
            : tbodyId // ignore: cast_nullable_to_non_nullable
                  as int?,
        heat: freezed == heat
            ? _value.heat
            : heat // ignore: cast_nullable_to_non_nullable
                  as int?,
        numberOfHeats: null == numberOfHeats
            ? _value.numberOfHeats
            : numberOfHeats // ignore: cast_nullable_to_non_nullable
                  as int,
        className: freezed == className
            ? _value.className
            : className // ignore: cast_nullable_to_non_nullable
                  as String?,
        masterheat: freezed == masterheat
            ? _value.masterheat
            : masterheat // ignore: cast_nullable_to_non_nullable
                  as int?,
        maxMasterheat: freezed == maxMasterheat
            ? _value.maxMasterheat
            : maxMasterheat // ignore: cast_nullable_to_non_nullable
                  as int?,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$CurrentHeatModelImpl implements _CurrentHeatModel {
  const _$CurrentHeatModelImpl({
    @JsonKey(name: 'now_racing') required this.nowRacing,
    @JsonKey(name: 'use_master_sched') this.useMasterSched = false,
    @JsonKey(name: 'use_points') this.usePoints = false,
    this.classid,
    this.roundid,
    this.round,
    @JsonKey(name: 'tbodyid') this.tbodyId,
    this.heat,
    @JsonKey(name: 'number-of-heats') this.numberOfHeats = 0,
    @JsonKey(name: 'class') this.className,
    this.masterheat,
    @JsonKey(name: 'max_masterheat') this.maxMasterheat,
  });

  factory _$CurrentHeatModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$CurrentHeatModelImplFromJson(json);

  @override
  @JsonKey(name: 'now_racing')
  final bool nowRacing;
  @override
  @JsonKey(name: 'use_master_sched')
  final bool useMasterSched;
  @override
  @JsonKey(name: 'use_points')
  final bool usePoints;
  @override
  final int? classid;
  @override
  final int? roundid;
  @override
  final int? round;
  @override
  @JsonKey(name: 'tbodyid')
  final int? tbodyId;
  @override
  final int? heat;
  @override
  @JsonKey(name: 'number-of-heats')
  final int numberOfHeats;
  @override
  @JsonKey(name: 'class')
  final String? className;
  @override
  final int? masterheat;
  @override
  @JsonKey(name: 'max_masterheat')
  final int? maxMasterheat;

  @override
  String toString() {
    return 'CurrentHeatModel(nowRacing: $nowRacing, useMasterSched: $useMasterSched, usePoints: $usePoints, classid: $classid, roundid: $roundid, round: $round, tbodyId: $tbodyId, heat: $heat, numberOfHeats: $numberOfHeats, className: $className, masterheat: $masterheat, maxMasterheat: $maxMasterheat)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$CurrentHeatModelImpl &&
            (identical(other.nowRacing, nowRacing) ||
                other.nowRacing == nowRacing) &&
            (identical(other.useMasterSched, useMasterSched) ||
                other.useMasterSched == useMasterSched) &&
            (identical(other.usePoints, usePoints) ||
                other.usePoints == usePoints) &&
            (identical(other.classid, classid) || other.classid == classid) &&
            (identical(other.roundid, roundid) || other.roundid == roundid) &&
            (identical(other.round, round) || other.round == round) &&
            (identical(other.tbodyId, tbodyId) || other.tbodyId == tbodyId) &&
            (identical(other.heat, heat) || other.heat == heat) &&
            (identical(other.numberOfHeats, numberOfHeats) ||
                other.numberOfHeats == numberOfHeats) &&
            (identical(other.className, className) ||
                other.className == className) &&
            (identical(other.masterheat, masterheat) ||
                other.masterheat == masterheat) &&
            (identical(other.maxMasterheat, maxMasterheat) ||
                other.maxMasterheat == maxMasterheat));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    nowRacing,
    useMasterSched,
    usePoints,
    classid,
    roundid,
    round,
    tbodyId,
    heat,
    numberOfHeats,
    className,
    masterheat,
    maxMasterheat,
  );

  /// Create a copy of CurrentHeatModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$CurrentHeatModelImplCopyWith<_$CurrentHeatModelImpl> get copyWith =>
      __$$CurrentHeatModelImplCopyWithImpl<_$CurrentHeatModelImpl>(
        this,
        _$identity,
      );

  @override
  Map<String, dynamic> toJson() {
    return _$$CurrentHeatModelImplToJson(this);
  }
}

abstract class _CurrentHeatModel implements CurrentHeatModel {
  const factory _CurrentHeatModel({
    @JsonKey(name: 'now_racing') required final bool nowRacing,
    @JsonKey(name: 'use_master_sched') final bool useMasterSched,
    @JsonKey(name: 'use_points') final bool usePoints,
    final int? classid,
    final int? roundid,
    final int? round,
    @JsonKey(name: 'tbodyid') final int? tbodyId,
    final int? heat,
    @JsonKey(name: 'number-of-heats') final int numberOfHeats,
    @JsonKey(name: 'class') final String? className,
    final int? masterheat,
    @JsonKey(name: 'max_masterheat') final int? maxMasterheat,
  }) = _$CurrentHeatModelImpl;

  factory _CurrentHeatModel.fromJson(Map<String, dynamic> json) =
      _$CurrentHeatModelImpl.fromJson;

  @override
  @JsonKey(name: 'now_racing')
  bool get nowRacing;
  @override
  @JsonKey(name: 'use_master_sched')
  bool get useMasterSched;
  @override
  @JsonKey(name: 'use_points')
  bool get usePoints;
  @override
  int? get classid;
  @override
  int? get roundid;
  @override
  int? get round;
  @override
  @JsonKey(name: 'tbodyid')
  int? get tbodyId;
  @override
  int? get heat;
  @override
  @JsonKey(name: 'number-of-heats')
  int get numberOfHeats;
  @override
  @JsonKey(name: 'class')
  String? get className;
  @override
  int? get masterheat;
  @override
  @JsonKey(name: 'max_masterheat')
  int? get maxMasterheat;

  /// Create a copy of CurrentHeatModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$CurrentHeatModelImplCopyWith<_$CurrentHeatModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
