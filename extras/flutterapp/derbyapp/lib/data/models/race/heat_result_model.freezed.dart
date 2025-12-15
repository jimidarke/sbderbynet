// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'heat_result_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

HeatResultModel _$HeatResultModelFromJson(Map<String, dynamic> json) {
  return _HeatResultModel.fromJson(json);
}

/// @nodoc
mixin _$HeatResultModel {
  int get lane => throw _privateConstructorUsedError;
  double get time => throw _privateConstructorUsedError;
  int get place => throw _privateConstructorUsedError;
  double get speed => throw _privateConstructorUsedError;

  /// Serializes this HeatResultModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of HeatResultModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $HeatResultModelCopyWith<HeatResultModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $HeatResultModelCopyWith<$Res> {
  factory $HeatResultModelCopyWith(
    HeatResultModel value,
    $Res Function(HeatResultModel) then,
  ) = _$HeatResultModelCopyWithImpl<$Res, HeatResultModel>;
  @useResult
  $Res call({int lane, double time, int place, double speed});
}

/// @nodoc
class _$HeatResultModelCopyWithImpl<$Res, $Val extends HeatResultModel>
    implements $HeatResultModelCopyWith<$Res> {
  _$HeatResultModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of HeatResultModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? lane = null,
    Object? time = null,
    Object? place = null,
    Object? speed = null,
  }) {
    return _then(
      _value.copyWith(
            lane: null == lane
                ? _value.lane
                : lane // ignore: cast_nullable_to_non_nullable
                      as int,
            time: null == time
                ? _value.time
                : time // ignore: cast_nullable_to_non_nullable
                      as double,
            place: null == place
                ? _value.place
                : place // ignore: cast_nullable_to_non_nullable
                      as int,
            speed: null == speed
                ? _value.speed
                : speed // ignore: cast_nullable_to_non_nullable
                      as double,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$HeatResultModelImplCopyWith<$Res>
    implements $HeatResultModelCopyWith<$Res> {
  factory _$$HeatResultModelImplCopyWith(
    _$HeatResultModelImpl value,
    $Res Function(_$HeatResultModelImpl) then,
  ) = __$$HeatResultModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({int lane, double time, int place, double speed});
}

/// @nodoc
class __$$HeatResultModelImplCopyWithImpl<$Res>
    extends _$HeatResultModelCopyWithImpl<$Res, _$HeatResultModelImpl>
    implements _$$HeatResultModelImplCopyWith<$Res> {
  __$$HeatResultModelImplCopyWithImpl(
    _$HeatResultModelImpl _value,
    $Res Function(_$HeatResultModelImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of HeatResultModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? lane = null,
    Object? time = null,
    Object? place = null,
    Object? speed = null,
  }) {
    return _then(
      _$HeatResultModelImpl(
        lane: null == lane
            ? _value.lane
            : lane // ignore: cast_nullable_to_non_nullable
                  as int,
        time: null == time
            ? _value.time
            : time // ignore: cast_nullable_to_non_nullable
                  as double,
        place: null == place
            ? _value.place
            : place // ignore: cast_nullable_to_non_nullable
                  as int,
        speed: null == speed
            ? _value.speed
            : speed // ignore: cast_nullable_to_non_nullable
                  as double,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$HeatResultModelImpl implements _HeatResultModel {
  const _$HeatResultModelImpl({
    required this.lane,
    required this.time,
    required this.place,
    this.speed = 0.0,
  });

  factory _$HeatResultModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$HeatResultModelImplFromJson(json);

  @override
  final int lane;
  @override
  final double time;
  @override
  final int place;
  @override
  @JsonKey()
  final double speed;

  @override
  String toString() {
    return 'HeatResultModel(lane: $lane, time: $time, place: $place, speed: $speed)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$HeatResultModelImpl &&
            (identical(other.lane, lane) || other.lane == lane) &&
            (identical(other.time, time) || other.time == time) &&
            (identical(other.place, place) || other.place == place) &&
            (identical(other.speed, speed) || other.speed == speed));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, lane, time, place, speed);

  /// Create a copy of HeatResultModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$HeatResultModelImplCopyWith<_$HeatResultModelImpl> get copyWith =>
      __$$HeatResultModelImplCopyWithImpl<_$HeatResultModelImpl>(
        this,
        _$identity,
      );

  @override
  Map<String, dynamic> toJson() {
    return _$$HeatResultModelImplToJson(this);
  }
}

abstract class _HeatResultModel implements HeatResultModel {
  const factory _HeatResultModel({
    required final int lane,
    required final double time,
    required final int place,
    final double speed,
  }) = _$HeatResultModelImpl;

  factory _HeatResultModel.fromJson(Map<String, dynamic> json) =
      _$HeatResultModelImpl.fromJson;

  @override
  int get lane;
  @override
  double get time;
  @override
  int get place;
  @override
  double get speed;

  /// Create a copy of HeatResultModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$HeatResultModelImplCopyWith<_$HeatResultModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
