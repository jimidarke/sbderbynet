// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'heat_detail_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

HeatDetailModel _$HeatDetailModelFromJson(Map<String, dynamic> json) {
  return _HeatDetailModel.fromJson(json);
}

/// @nodoc
mixin _$HeatDetailModel {
  int get roundId => throw _privateConstructorUsedError;
  int get heat => throw _privateConstructorUsedError;
  String get roundName => throw _privateConstructorUsedError;
  String get className => throw _privateConstructorUsedError;
  List<RacerModel> get racers => throw _privateConstructorUsedError;
  List<HeatResultModel> get results => throw _privateConstructorUsedError;
  bool get isComplete => throw _privateConstructorUsedError;
  DateTime? get completedAt => throw _privateConstructorUsedError;

  /// Serializes this HeatDetailModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of HeatDetailModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $HeatDetailModelCopyWith<HeatDetailModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $HeatDetailModelCopyWith<$Res> {
  factory $HeatDetailModelCopyWith(
    HeatDetailModel value,
    $Res Function(HeatDetailModel) then,
  ) = _$HeatDetailModelCopyWithImpl<$Res, HeatDetailModel>;
  @useResult
  $Res call({
    int roundId,
    int heat,
    String roundName,
    String className,
    List<RacerModel> racers,
    List<HeatResultModel> results,
    bool isComplete,
    DateTime? completedAt,
  });
}

/// @nodoc
class _$HeatDetailModelCopyWithImpl<$Res, $Val extends HeatDetailModel>
    implements $HeatDetailModelCopyWith<$Res> {
  _$HeatDetailModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of HeatDetailModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? roundId = null,
    Object? heat = null,
    Object? roundName = null,
    Object? className = null,
    Object? racers = null,
    Object? results = null,
    Object? isComplete = null,
    Object? completedAt = freezed,
  }) {
    return _then(
      _value.copyWith(
            roundId: null == roundId
                ? _value.roundId
                : roundId // ignore: cast_nullable_to_non_nullable
                      as int,
            heat: null == heat
                ? _value.heat
                : heat // ignore: cast_nullable_to_non_nullable
                      as int,
            roundName: null == roundName
                ? _value.roundName
                : roundName // ignore: cast_nullable_to_non_nullable
                      as String,
            className: null == className
                ? _value.className
                : className // ignore: cast_nullable_to_non_nullable
                      as String,
            racers: null == racers
                ? _value.racers
                : racers // ignore: cast_nullable_to_non_nullable
                      as List<RacerModel>,
            results: null == results
                ? _value.results
                : results // ignore: cast_nullable_to_non_nullable
                      as List<HeatResultModel>,
            isComplete: null == isComplete
                ? _value.isComplete
                : isComplete // ignore: cast_nullable_to_non_nullable
                      as bool,
            completedAt: freezed == completedAt
                ? _value.completedAt
                : completedAt // ignore: cast_nullable_to_non_nullable
                      as DateTime?,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$HeatDetailModelImplCopyWith<$Res>
    implements $HeatDetailModelCopyWith<$Res> {
  factory _$$HeatDetailModelImplCopyWith(
    _$HeatDetailModelImpl value,
    $Res Function(_$HeatDetailModelImpl) then,
  ) = __$$HeatDetailModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    int roundId,
    int heat,
    String roundName,
    String className,
    List<RacerModel> racers,
    List<HeatResultModel> results,
    bool isComplete,
    DateTime? completedAt,
  });
}

/// @nodoc
class __$$HeatDetailModelImplCopyWithImpl<$Res>
    extends _$HeatDetailModelCopyWithImpl<$Res, _$HeatDetailModelImpl>
    implements _$$HeatDetailModelImplCopyWith<$Res> {
  __$$HeatDetailModelImplCopyWithImpl(
    _$HeatDetailModelImpl _value,
    $Res Function(_$HeatDetailModelImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of HeatDetailModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? roundId = null,
    Object? heat = null,
    Object? roundName = null,
    Object? className = null,
    Object? racers = null,
    Object? results = null,
    Object? isComplete = null,
    Object? completedAt = freezed,
  }) {
    return _then(
      _$HeatDetailModelImpl(
        roundId: null == roundId
            ? _value.roundId
            : roundId // ignore: cast_nullable_to_non_nullable
                  as int,
        heat: null == heat
            ? _value.heat
            : heat // ignore: cast_nullable_to_non_nullable
                  as int,
        roundName: null == roundName
            ? _value.roundName
            : roundName // ignore: cast_nullable_to_non_nullable
                  as String,
        className: null == className
            ? _value.className
            : className // ignore: cast_nullable_to_non_nullable
                  as String,
        racers: null == racers
            ? _value._racers
            : racers // ignore: cast_nullable_to_non_nullable
                  as List<RacerModel>,
        results: null == results
            ? _value._results
            : results // ignore: cast_nullable_to_non_nullable
                  as List<HeatResultModel>,
        isComplete: null == isComplete
            ? _value.isComplete
            : isComplete // ignore: cast_nullable_to_non_nullable
                  as bool,
        completedAt: freezed == completedAt
            ? _value.completedAt
            : completedAt // ignore: cast_nullable_to_non_nullable
                  as DateTime?,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$HeatDetailModelImpl extends _HeatDetailModel {
  const _$HeatDetailModelImpl({
    required this.roundId,
    required this.heat,
    required this.roundName,
    required this.className,
    required final List<RacerModel> racers,
    required final List<HeatResultModel> results,
    required this.isComplete,
    this.completedAt,
  }) : _racers = racers,
       _results = results,
       super._();

  factory _$HeatDetailModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$HeatDetailModelImplFromJson(json);

  @override
  final int roundId;
  @override
  final int heat;
  @override
  final String roundName;
  @override
  final String className;
  final List<RacerModel> _racers;
  @override
  List<RacerModel> get racers {
    if (_racers is EqualUnmodifiableListView) return _racers;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_racers);
  }

  final List<HeatResultModel> _results;
  @override
  List<HeatResultModel> get results {
    if (_results is EqualUnmodifiableListView) return _results;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_results);
  }

  @override
  final bool isComplete;
  @override
  final DateTime? completedAt;

  @override
  String toString() {
    return 'HeatDetailModel(roundId: $roundId, heat: $heat, roundName: $roundName, className: $className, racers: $racers, results: $results, isComplete: $isComplete, completedAt: $completedAt)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$HeatDetailModelImpl &&
            (identical(other.roundId, roundId) || other.roundId == roundId) &&
            (identical(other.heat, heat) || other.heat == heat) &&
            (identical(other.roundName, roundName) ||
                other.roundName == roundName) &&
            (identical(other.className, className) ||
                other.className == className) &&
            const DeepCollectionEquality().equals(other._racers, _racers) &&
            const DeepCollectionEquality().equals(other._results, _results) &&
            (identical(other.isComplete, isComplete) ||
                other.isComplete == isComplete) &&
            (identical(other.completedAt, completedAt) ||
                other.completedAt == completedAt));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    roundId,
    heat,
    roundName,
    className,
    const DeepCollectionEquality().hash(_racers),
    const DeepCollectionEquality().hash(_results),
    isComplete,
    completedAt,
  );

  /// Create a copy of HeatDetailModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$HeatDetailModelImplCopyWith<_$HeatDetailModelImpl> get copyWith =>
      __$$HeatDetailModelImplCopyWithImpl<_$HeatDetailModelImpl>(
        this,
        _$identity,
      );

  @override
  Map<String, dynamic> toJson() {
    return _$$HeatDetailModelImplToJson(this);
  }
}

abstract class _HeatDetailModel extends HeatDetailModel {
  const factory _HeatDetailModel({
    required final int roundId,
    required final int heat,
    required final String roundName,
    required final String className,
    required final List<RacerModel> racers,
    required final List<HeatResultModel> results,
    required final bool isComplete,
    final DateTime? completedAt,
  }) = _$HeatDetailModelImpl;
  const _HeatDetailModel._() : super._();

  factory _HeatDetailModel.fromJson(Map<String, dynamic> json) =
      _$HeatDetailModelImpl.fromJson;

  @override
  int get roundId;
  @override
  int get heat;
  @override
  String get roundName;
  @override
  String get className;
  @override
  List<RacerModel> get racers;
  @override
  List<HeatResultModel> get results;
  @override
  bool get isComplete;
  @override
  DateTime? get completedAt;

  /// Create a copy of HeatDetailModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$HeatDetailModelImplCopyWith<_$HeatDetailModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
