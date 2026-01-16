// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'round_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

RoundModel _$RoundModelFromJson(Map<String, dynamic> json) {
  return _RoundModel.fromJson(json);
}

/// @nodoc
mixin _$RoundModel {
  int get roundid => throw _privateConstructorUsedError;
  int get classid => throw _privateConstructorUsedError;
  String get class_ => throw _privateConstructorUsedError;
  String get round => throw _privateConstructorUsedError;
  String get name => throw _privateConstructorUsedError;
  String get roundname => throw _privateConstructorUsedError;
  bool get aggregate => throw _privateConstructorUsedError;
  @JsonKey(name: 'roster_size')
  int get rosterSize => throw _privateConstructorUsedError;
  int get passed => throw _privateConstructorUsedError;
  int get registered => throw _privateConstructorUsedError;
  int get unscheduled => throw _privateConstructorUsedError;
  @JsonKey(name: 'heats_scheduled')
  int get heatsScheduled => throw _privateConstructorUsedError;
  @JsonKey(name: 'heats_run')
  int get heatsRun => throw _privateConstructorUsedError;

  /// Serializes this RoundModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of RoundModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $RoundModelCopyWith<RoundModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $RoundModelCopyWith<$Res> {
  factory $RoundModelCopyWith(
    RoundModel value,
    $Res Function(RoundModel) then,
  ) = _$RoundModelCopyWithImpl<$Res, RoundModel>;
  @useResult
  $Res call({
    int roundid,
    int classid,
    String class_,
    String round,
    String name,
    String roundname,
    bool aggregate,
    @JsonKey(name: 'roster_size') int rosterSize,
    int passed,
    int registered,
    int unscheduled,
    @JsonKey(name: 'heats_scheduled') int heatsScheduled,
    @JsonKey(name: 'heats_run') int heatsRun,
  });
}

/// @nodoc
class _$RoundModelCopyWithImpl<$Res, $Val extends RoundModel>
    implements $RoundModelCopyWith<$Res> {
  _$RoundModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of RoundModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? roundid = null,
    Object? classid = null,
    Object? class_ = null,
    Object? round = null,
    Object? name = null,
    Object? roundname = null,
    Object? aggregate = null,
    Object? rosterSize = null,
    Object? passed = null,
    Object? registered = null,
    Object? unscheduled = null,
    Object? heatsScheduled = null,
    Object? heatsRun = null,
  }) {
    return _then(
      _value.copyWith(
            roundid: null == roundid
                ? _value.roundid
                : roundid // ignore: cast_nullable_to_non_nullable
                      as int,
            classid: null == classid
                ? _value.classid
                : classid // ignore: cast_nullable_to_non_nullable
                      as int,
            class_: null == class_
                ? _value.class_
                : class_ // ignore: cast_nullable_to_non_nullable
                      as String,
            round: null == round
                ? _value.round
                : round // ignore: cast_nullable_to_non_nullable
                      as String,
            name: null == name
                ? _value.name
                : name // ignore: cast_nullable_to_non_nullable
                      as String,
            roundname: null == roundname
                ? _value.roundname
                : roundname // ignore: cast_nullable_to_non_nullable
                      as String,
            aggregate: null == aggregate
                ? _value.aggregate
                : aggregate // ignore: cast_nullable_to_non_nullable
                      as bool,
            rosterSize: null == rosterSize
                ? _value.rosterSize
                : rosterSize // ignore: cast_nullable_to_non_nullable
                      as int,
            passed: null == passed
                ? _value.passed
                : passed // ignore: cast_nullable_to_non_nullable
                      as int,
            registered: null == registered
                ? _value.registered
                : registered // ignore: cast_nullable_to_non_nullable
                      as int,
            unscheduled: null == unscheduled
                ? _value.unscheduled
                : unscheduled // ignore: cast_nullable_to_non_nullable
                      as int,
            heatsScheduled: null == heatsScheduled
                ? _value.heatsScheduled
                : heatsScheduled // ignore: cast_nullable_to_non_nullable
                      as int,
            heatsRun: null == heatsRun
                ? _value.heatsRun
                : heatsRun // ignore: cast_nullable_to_non_nullable
                      as int,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$RoundModelImplCopyWith<$Res>
    implements $RoundModelCopyWith<$Res> {
  factory _$$RoundModelImplCopyWith(
    _$RoundModelImpl value,
    $Res Function(_$RoundModelImpl) then,
  ) = __$$RoundModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    int roundid,
    int classid,
    String class_,
    String round,
    String name,
    String roundname,
    bool aggregate,
    @JsonKey(name: 'roster_size') int rosterSize,
    int passed,
    int registered,
    int unscheduled,
    @JsonKey(name: 'heats_scheduled') int heatsScheduled,
    @JsonKey(name: 'heats_run') int heatsRun,
  });
}

/// @nodoc
class __$$RoundModelImplCopyWithImpl<$Res>
    extends _$RoundModelCopyWithImpl<$Res, _$RoundModelImpl>
    implements _$$RoundModelImplCopyWith<$Res> {
  __$$RoundModelImplCopyWithImpl(
    _$RoundModelImpl _value,
    $Res Function(_$RoundModelImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of RoundModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? roundid = null,
    Object? classid = null,
    Object? class_ = null,
    Object? round = null,
    Object? name = null,
    Object? roundname = null,
    Object? aggregate = null,
    Object? rosterSize = null,
    Object? passed = null,
    Object? registered = null,
    Object? unscheduled = null,
    Object? heatsScheduled = null,
    Object? heatsRun = null,
  }) {
    return _then(
      _$RoundModelImpl(
        roundid: null == roundid
            ? _value.roundid
            : roundid // ignore: cast_nullable_to_non_nullable
                  as int,
        classid: null == classid
            ? _value.classid
            : classid // ignore: cast_nullable_to_non_nullable
                  as int,
        class_: null == class_
            ? _value.class_
            : class_ // ignore: cast_nullable_to_non_nullable
                  as String,
        round: null == round
            ? _value.round
            : round // ignore: cast_nullable_to_non_nullable
                  as String,
        name: null == name
            ? _value.name
            : name // ignore: cast_nullable_to_non_nullable
                  as String,
        roundname: null == roundname
            ? _value.roundname
            : roundname // ignore: cast_nullable_to_non_nullable
                  as String,
        aggregate: null == aggregate
            ? _value.aggregate
            : aggregate // ignore: cast_nullable_to_non_nullable
                  as bool,
        rosterSize: null == rosterSize
            ? _value.rosterSize
            : rosterSize // ignore: cast_nullable_to_non_nullable
                  as int,
        passed: null == passed
            ? _value.passed
            : passed // ignore: cast_nullable_to_non_nullable
                  as int,
        registered: null == registered
            ? _value.registered
            : registered // ignore: cast_nullable_to_non_nullable
                  as int,
        unscheduled: null == unscheduled
            ? _value.unscheduled
            : unscheduled // ignore: cast_nullable_to_non_nullable
                  as int,
        heatsScheduled: null == heatsScheduled
            ? _value.heatsScheduled
            : heatsScheduled // ignore: cast_nullable_to_non_nullable
                  as int,
        heatsRun: null == heatsRun
            ? _value.heatsRun
            : heatsRun // ignore: cast_nullable_to_non_nullable
                  as int,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$RoundModelImpl implements _RoundModel {
  const _$RoundModelImpl({
    required this.roundid,
    required this.classid,
    this.class_ = '',
    this.round = '',
    this.name = '',
    this.roundname = '',
    this.aggregate = false,
    @JsonKey(name: 'roster_size') this.rosterSize = 0,
    this.passed = 0,
    this.registered = 0,
    this.unscheduled = 0,
    @JsonKey(name: 'heats_scheduled') this.heatsScheduled = 0,
    @JsonKey(name: 'heats_run') this.heatsRun = 0,
  });

  factory _$RoundModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$RoundModelImplFromJson(json);

  @override
  final int roundid;
  @override
  final int classid;
  @override
  @JsonKey()
  final String class_;
  @override
  @JsonKey()
  final String round;
  @override
  @JsonKey()
  final String name;
  @override
  @JsonKey()
  final String roundname;
  @override
  @JsonKey()
  final bool aggregate;
  @override
  @JsonKey(name: 'roster_size')
  final int rosterSize;
  @override
  @JsonKey()
  final int passed;
  @override
  @JsonKey()
  final int registered;
  @override
  @JsonKey()
  final int unscheduled;
  @override
  @JsonKey(name: 'heats_scheduled')
  final int heatsScheduled;
  @override
  @JsonKey(name: 'heats_run')
  final int heatsRun;

  @override
  String toString() {
    return 'RoundModel(roundid: $roundid, classid: $classid, class_: $class_, round: $round, name: $name, roundname: $roundname, aggregate: $aggregate, rosterSize: $rosterSize, passed: $passed, registered: $registered, unscheduled: $unscheduled, heatsScheduled: $heatsScheduled, heatsRun: $heatsRun)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$RoundModelImpl &&
            (identical(other.roundid, roundid) || other.roundid == roundid) &&
            (identical(other.classid, classid) || other.classid == classid) &&
            (identical(other.class_, class_) || other.class_ == class_) &&
            (identical(other.round, round) || other.round == round) &&
            (identical(other.name, name) || other.name == name) &&
            (identical(other.roundname, roundname) ||
                other.roundname == roundname) &&
            (identical(other.aggregate, aggregate) ||
                other.aggregate == aggregate) &&
            (identical(other.rosterSize, rosterSize) ||
                other.rosterSize == rosterSize) &&
            (identical(other.passed, passed) || other.passed == passed) &&
            (identical(other.registered, registered) ||
                other.registered == registered) &&
            (identical(other.unscheduled, unscheduled) ||
                other.unscheduled == unscheduled) &&
            (identical(other.heatsScheduled, heatsScheduled) ||
                other.heatsScheduled == heatsScheduled) &&
            (identical(other.heatsRun, heatsRun) ||
                other.heatsRun == heatsRun));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    roundid,
    classid,
    class_,
    round,
    name,
    roundname,
    aggregate,
    rosterSize,
    passed,
    registered,
    unscheduled,
    heatsScheduled,
    heatsRun,
  );

  /// Create a copy of RoundModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$RoundModelImplCopyWith<_$RoundModelImpl> get copyWith =>
      __$$RoundModelImplCopyWithImpl<_$RoundModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$RoundModelImplToJson(this);
  }
}

abstract class _RoundModel implements RoundModel {
  const factory _RoundModel({
    required final int roundid,
    required final int classid,
    final String class_,
    final String round,
    final String name,
    final String roundname,
    final bool aggregate,
    @JsonKey(name: 'roster_size') final int rosterSize,
    final int passed,
    final int registered,
    final int unscheduled,
    @JsonKey(name: 'heats_scheduled') final int heatsScheduled,
    @JsonKey(name: 'heats_run') final int heatsRun,
  }) = _$RoundModelImpl;

  factory _RoundModel.fromJson(Map<String, dynamic> json) =
      _$RoundModelImpl.fromJson;

  @override
  int get roundid;
  @override
  int get classid;
  @override
  String get class_;
  @override
  String get round;
  @override
  String get name;
  @override
  String get roundname;
  @override
  bool get aggregate;
  @override
  @JsonKey(name: 'roster_size')
  int get rosterSize;
  @override
  int get passed;
  @override
  int get registered;
  @override
  int get unscheduled;
  @override
  @JsonKey(name: 'heats_scheduled')
  int get heatsScheduled;
  @override
  @JsonKey(name: 'heats_run')
  int get heatsRun;

  /// Create a copy of RoundModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$RoundModelImplCopyWith<_$RoundModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
