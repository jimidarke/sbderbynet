// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'racer_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

RacerModel _$RacerModelFromJson(Map<String, dynamic> json) {
  return _RacerModel.fromJson(json);
}

/// @nodoc
mixin _$RacerModel {
  int get lane => throw _privateConstructorUsedError;
  int get racerid => throw _privateConstructorUsedError;
  String get name => throw _privateConstructorUsedError;
  String get carname => throw _privateConstructorUsedError;
  int? get carnumber => throw _privateConstructorUsedError;
  String get note => throw _privateConstructorUsedError;
  String get photo => throw _privateConstructorUsedError;
  @EmptyStringToDoubleConverter()
  double? get finishtime => throw _privateConstructorUsedError;
  @EmptyStringToIntConverter()
  int? get finishplace => throw _privateConstructorUsedError;
  String? get subgroup => throw _privateConstructorUsedError;

  /// Serializes this RacerModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of RacerModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $RacerModelCopyWith<RacerModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $RacerModelCopyWith<$Res> {
  factory $RacerModelCopyWith(
    RacerModel value,
    $Res Function(RacerModel) then,
  ) = _$RacerModelCopyWithImpl<$Res, RacerModel>;
  @useResult
  $Res call({
    int lane,
    int racerid,
    String name,
    String carname,
    int? carnumber,
    String note,
    String photo,
    @EmptyStringToDoubleConverter() double? finishtime,
    @EmptyStringToIntConverter() int? finishplace,
    String? subgroup,
  });
}

/// @nodoc
class _$RacerModelCopyWithImpl<$Res, $Val extends RacerModel>
    implements $RacerModelCopyWith<$Res> {
  _$RacerModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of RacerModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? lane = null,
    Object? racerid = null,
    Object? name = null,
    Object? carname = null,
    Object? carnumber = freezed,
    Object? note = null,
    Object? photo = null,
    Object? finishtime = freezed,
    Object? finishplace = freezed,
    Object? subgroup = freezed,
  }) {
    return _then(
      _value.copyWith(
            lane: null == lane
                ? _value.lane
                : lane // ignore: cast_nullable_to_non_nullable
                      as int,
            racerid: null == racerid
                ? _value.racerid
                : racerid // ignore: cast_nullable_to_non_nullable
                      as int,
            name: null == name
                ? _value.name
                : name // ignore: cast_nullable_to_non_nullable
                      as String,
            carname: null == carname
                ? _value.carname
                : carname // ignore: cast_nullable_to_non_nullable
                      as String,
            carnumber: freezed == carnumber
                ? _value.carnumber
                : carnumber // ignore: cast_nullable_to_non_nullable
                      as int?,
            note: null == note
                ? _value.note
                : note // ignore: cast_nullable_to_non_nullable
                      as String,
            photo: null == photo
                ? _value.photo
                : photo // ignore: cast_nullable_to_non_nullable
                      as String,
            finishtime: freezed == finishtime
                ? _value.finishtime
                : finishtime // ignore: cast_nullable_to_non_nullable
                      as double?,
            finishplace: freezed == finishplace
                ? _value.finishplace
                : finishplace // ignore: cast_nullable_to_non_nullable
                      as int?,
            subgroup: freezed == subgroup
                ? _value.subgroup
                : subgroup // ignore: cast_nullable_to_non_nullable
                      as String?,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$RacerModelImplCopyWith<$Res>
    implements $RacerModelCopyWith<$Res> {
  factory _$$RacerModelImplCopyWith(
    _$RacerModelImpl value,
    $Res Function(_$RacerModelImpl) then,
  ) = __$$RacerModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    int lane,
    int racerid,
    String name,
    String carname,
    int? carnumber,
    String note,
    String photo,
    @EmptyStringToDoubleConverter() double? finishtime,
    @EmptyStringToIntConverter() int? finishplace,
    String? subgroup,
  });
}

/// @nodoc
class __$$RacerModelImplCopyWithImpl<$Res>
    extends _$RacerModelCopyWithImpl<$Res, _$RacerModelImpl>
    implements _$$RacerModelImplCopyWith<$Res> {
  __$$RacerModelImplCopyWithImpl(
    _$RacerModelImpl _value,
    $Res Function(_$RacerModelImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of RacerModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? lane = null,
    Object? racerid = null,
    Object? name = null,
    Object? carname = null,
    Object? carnumber = freezed,
    Object? note = null,
    Object? photo = null,
    Object? finishtime = freezed,
    Object? finishplace = freezed,
    Object? subgroup = freezed,
  }) {
    return _then(
      _$RacerModelImpl(
        lane: null == lane
            ? _value.lane
            : lane // ignore: cast_nullable_to_non_nullable
                  as int,
        racerid: null == racerid
            ? _value.racerid
            : racerid // ignore: cast_nullable_to_non_nullable
                  as int,
        name: null == name
            ? _value.name
            : name // ignore: cast_nullable_to_non_nullable
                  as String,
        carname: null == carname
            ? _value.carname
            : carname // ignore: cast_nullable_to_non_nullable
                  as String,
        carnumber: freezed == carnumber
            ? _value.carnumber
            : carnumber // ignore: cast_nullable_to_non_nullable
                  as int?,
        note: null == note
            ? _value.note
            : note // ignore: cast_nullable_to_non_nullable
                  as String,
        photo: null == photo
            ? _value.photo
            : photo // ignore: cast_nullable_to_non_nullable
                  as String,
        finishtime: freezed == finishtime
            ? _value.finishtime
            : finishtime // ignore: cast_nullable_to_non_nullable
                  as double?,
        finishplace: freezed == finishplace
            ? _value.finishplace
            : finishplace // ignore: cast_nullable_to_non_nullable
                  as int?,
        subgroup: freezed == subgroup
            ? _value.subgroup
            : subgroup // ignore: cast_nullable_to_non_nullable
                  as String?,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$RacerModelImpl implements _RacerModel {
  const _$RacerModelImpl({
    required this.lane,
    required this.racerid,
    this.name = '',
    this.carname = '',
    this.carnumber,
    this.note = '',
    this.photo = '',
    @EmptyStringToDoubleConverter() this.finishtime,
    @EmptyStringToIntConverter() this.finishplace,
    this.subgroup,
  });

  factory _$RacerModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$RacerModelImplFromJson(json);

  @override
  final int lane;
  @override
  final int racerid;
  @override
  @JsonKey()
  final String name;
  @override
  @JsonKey()
  final String carname;
  @override
  final int? carnumber;
  @override
  @JsonKey()
  final String note;
  @override
  @JsonKey()
  final String photo;
  @override
  @EmptyStringToDoubleConverter()
  final double? finishtime;
  @override
  @EmptyStringToIntConverter()
  final int? finishplace;
  @override
  final String? subgroup;

  @override
  String toString() {
    return 'RacerModel(lane: $lane, racerid: $racerid, name: $name, carname: $carname, carnumber: $carnumber, note: $note, photo: $photo, finishtime: $finishtime, finishplace: $finishplace, subgroup: $subgroup)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$RacerModelImpl &&
            (identical(other.lane, lane) || other.lane == lane) &&
            (identical(other.racerid, racerid) || other.racerid == racerid) &&
            (identical(other.name, name) || other.name == name) &&
            (identical(other.carname, carname) || other.carname == carname) &&
            (identical(other.carnumber, carnumber) ||
                other.carnumber == carnumber) &&
            (identical(other.note, note) || other.note == note) &&
            (identical(other.photo, photo) || other.photo == photo) &&
            (identical(other.finishtime, finishtime) ||
                other.finishtime == finishtime) &&
            (identical(other.finishplace, finishplace) ||
                other.finishplace == finishplace) &&
            (identical(other.subgroup, subgroup) ||
                other.subgroup == subgroup));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    lane,
    racerid,
    name,
    carname,
    carnumber,
    note,
    photo,
    finishtime,
    finishplace,
    subgroup,
  );

  /// Create a copy of RacerModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$RacerModelImplCopyWith<_$RacerModelImpl> get copyWith =>
      __$$RacerModelImplCopyWithImpl<_$RacerModelImpl>(this, _$identity);

  @override
  Map<String, dynamic> toJson() {
    return _$$RacerModelImplToJson(this);
  }
}

abstract class _RacerModel implements RacerModel {
  const factory _RacerModel({
    required final int lane,
    required final int racerid,
    final String name,
    final String carname,
    final int? carnumber,
    final String note,
    final String photo,
    @EmptyStringToDoubleConverter() final double? finishtime,
    @EmptyStringToIntConverter() final int? finishplace,
    final String? subgroup,
  }) = _$RacerModelImpl;

  factory _RacerModel.fromJson(Map<String, dynamic> json) =
      _$RacerModelImpl.fromJson;

  @override
  int get lane;
  @override
  int get racerid;
  @override
  String get name;
  @override
  String get carname;
  @override
  int? get carnumber;
  @override
  String get note;
  @override
  String get photo;
  @override
  @EmptyStringToDoubleConverter()
  double? get finishtime;
  @override
  @EmptyStringToIntConverter()
  int? get finishplace;
  @override
  String? get subgroup;

  /// Create a copy of RacerModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$RacerModelImplCopyWith<_$RacerModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
