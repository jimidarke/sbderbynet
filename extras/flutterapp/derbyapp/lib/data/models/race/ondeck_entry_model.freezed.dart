// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'ondeck_entry_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

OnDeckEntryModel _$OnDeckEntryModelFromJson(Map<String, dynamic> json) {
  return _OnDeckEntryModel.fromJson(json);
}

/// @nodoc
mixin _$OnDeckEntryModel {
  int get resultid => throw _privateConstructorUsedError;
  int get roundid => throw _privateConstructorUsedError;
  int get heat => throw _privateConstructorUsedError;
  int get lane => throw _privateConstructorUsedError;
  int get racerid => throw _privateConstructorUsedError;
  String get name => throw _privateConstructorUsedError;
  int get carnumber => throw _privateConstructorUsedError;
  @OnDeckResultConverter()
  double? get result => throw _privateConstructorUsedError; // z-prefix removed, null if not finished
  @JsonKey(name: 'carphoto')
  Map<String, dynamic>? get carPhoto => throw _privateConstructorUsedError;

  /// Serializes this OnDeckEntryModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of OnDeckEntryModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $OnDeckEntryModelCopyWith<OnDeckEntryModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $OnDeckEntryModelCopyWith<$Res> {
  factory $OnDeckEntryModelCopyWith(
    OnDeckEntryModel value,
    $Res Function(OnDeckEntryModel) then,
  ) = _$OnDeckEntryModelCopyWithImpl<$Res, OnDeckEntryModel>;
  @useResult
  $Res call({
    int resultid,
    int roundid,
    int heat,
    int lane,
    int racerid,
    String name,
    int carnumber,
    @OnDeckResultConverter() double? result,
    @JsonKey(name: 'carphoto') Map<String, dynamic>? carPhoto,
  });
}

/// @nodoc
class _$OnDeckEntryModelCopyWithImpl<$Res, $Val extends OnDeckEntryModel>
    implements $OnDeckEntryModelCopyWith<$Res> {
  _$OnDeckEntryModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of OnDeckEntryModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? resultid = null,
    Object? roundid = null,
    Object? heat = null,
    Object? lane = null,
    Object? racerid = null,
    Object? name = null,
    Object? carnumber = null,
    Object? result = freezed,
    Object? carPhoto = freezed,
  }) {
    return _then(
      _value.copyWith(
            resultid: null == resultid
                ? _value.resultid
                : resultid // ignore: cast_nullable_to_non_nullable
                      as int,
            roundid: null == roundid
                ? _value.roundid
                : roundid // ignore: cast_nullable_to_non_nullable
                      as int,
            heat: null == heat
                ? _value.heat
                : heat // ignore: cast_nullable_to_non_nullable
                      as int,
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
            carnumber: null == carnumber
                ? _value.carnumber
                : carnumber // ignore: cast_nullable_to_non_nullable
                      as int,
            result: freezed == result
                ? _value.result
                : result // ignore: cast_nullable_to_non_nullable
                      as double?,
            carPhoto: freezed == carPhoto
                ? _value.carPhoto
                : carPhoto // ignore: cast_nullable_to_non_nullable
                      as Map<String, dynamic>?,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$OnDeckEntryModelImplCopyWith<$Res>
    implements $OnDeckEntryModelCopyWith<$Res> {
  factory _$$OnDeckEntryModelImplCopyWith(
    _$OnDeckEntryModelImpl value,
    $Res Function(_$OnDeckEntryModelImpl) then,
  ) = __$$OnDeckEntryModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({
    int resultid,
    int roundid,
    int heat,
    int lane,
    int racerid,
    String name,
    int carnumber,
    @OnDeckResultConverter() double? result,
    @JsonKey(name: 'carphoto') Map<String, dynamic>? carPhoto,
  });
}

/// @nodoc
class __$$OnDeckEntryModelImplCopyWithImpl<$Res>
    extends _$OnDeckEntryModelCopyWithImpl<$Res, _$OnDeckEntryModelImpl>
    implements _$$OnDeckEntryModelImplCopyWith<$Res> {
  __$$OnDeckEntryModelImplCopyWithImpl(
    _$OnDeckEntryModelImpl _value,
    $Res Function(_$OnDeckEntryModelImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of OnDeckEntryModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? resultid = null,
    Object? roundid = null,
    Object? heat = null,
    Object? lane = null,
    Object? racerid = null,
    Object? name = null,
    Object? carnumber = null,
    Object? result = freezed,
    Object? carPhoto = freezed,
  }) {
    return _then(
      _$OnDeckEntryModelImpl(
        resultid: null == resultid
            ? _value.resultid
            : resultid // ignore: cast_nullable_to_non_nullable
                  as int,
        roundid: null == roundid
            ? _value.roundid
            : roundid // ignore: cast_nullable_to_non_nullable
                  as int,
        heat: null == heat
            ? _value.heat
            : heat // ignore: cast_nullable_to_non_nullable
                  as int,
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
        carnumber: null == carnumber
            ? _value.carnumber
            : carnumber // ignore: cast_nullable_to_non_nullable
                  as int,
        result: freezed == result
            ? _value.result
            : result // ignore: cast_nullable_to_non_nullable
                  as double?,
        carPhoto: freezed == carPhoto
            ? _value._carPhoto
            : carPhoto // ignore: cast_nullable_to_non_nullable
                  as Map<String, dynamic>?,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$OnDeckEntryModelImpl implements _OnDeckEntryModel {
  const _$OnDeckEntryModelImpl({
    required this.resultid,
    required this.roundid,
    required this.heat,
    required this.lane,
    required this.racerid,
    this.name = '',
    this.carnumber = 0,
    @OnDeckResultConverter() this.result,
    @JsonKey(name: 'carphoto') final Map<String, dynamic>? carPhoto,
  }) : _carPhoto = carPhoto;

  factory _$OnDeckEntryModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$OnDeckEntryModelImplFromJson(json);

  @override
  final int resultid;
  @override
  final int roundid;
  @override
  final int heat;
  @override
  final int lane;
  @override
  final int racerid;
  @override
  @JsonKey()
  final String name;
  @override
  @JsonKey()
  final int carnumber;
  @override
  @OnDeckResultConverter()
  final double? result;
  // z-prefix removed, null if not finished
  final Map<String, dynamic>? _carPhoto;
  // z-prefix removed, null if not finished
  @override
  @JsonKey(name: 'carphoto')
  Map<String, dynamic>? get carPhoto {
    final value = _carPhoto;
    if (value == null) return null;
    if (_carPhoto is EqualUnmodifiableMapView) return _carPhoto;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableMapView(value);
  }

  @override
  String toString() {
    return 'OnDeckEntryModel(resultid: $resultid, roundid: $roundid, heat: $heat, lane: $lane, racerid: $racerid, name: $name, carnumber: $carnumber, result: $result, carPhoto: $carPhoto)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$OnDeckEntryModelImpl &&
            (identical(other.resultid, resultid) ||
                other.resultid == resultid) &&
            (identical(other.roundid, roundid) || other.roundid == roundid) &&
            (identical(other.heat, heat) || other.heat == heat) &&
            (identical(other.lane, lane) || other.lane == lane) &&
            (identical(other.racerid, racerid) || other.racerid == racerid) &&
            (identical(other.name, name) || other.name == name) &&
            (identical(other.carnumber, carnumber) ||
                other.carnumber == carnumber) &&
            (identical(other.result, result) || other.result == result) &&
            const DeepCollectionEquality().equals(other._carPhoto, _carPhoto));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(
    runtimeType,
    resultid,
    roundid,
    heat,
    lane,
    racerid,
    name,
    carnumber,
    result,
    const DeepCollectionEquality().hash(_carPhoto),
  );

  /// Create a copy of OnDeckEntryModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$OnDeckEntryModelImplCopyWith<_$OnDeckEntryModelImpl> get copyWith =>
      __$$OnDeckEntryModelImplCopyWithImpl<_$OnDeckEntryModelImpl>(
        this,
        _$identity,
      );

  @override
  Map<String, dynamic> toJson() {
    return _$$OnDeckEntryModelImplToJson(this);
  }
}

abstract class _OnDeckEntryModel implements OnDeckEntryModel {
  const factory _OnDeckEntryModel({
    required final int resultid,
    required final int roundid,
    required final int heat,
    required final int lane,
    required final int racerid,
    final String name,
    final int carnumber,
    @OnDeckResultConverter() final double? result,
    @JsonKey(name: 'carphoto') final Map<String, dynamic>? carPhoto,
  }) = _$OnDeckEntryModelImpl;

  factory _OnDeckEntryModel.fromJson(Map<String, dynamic> json) =
      _$OnDeckEntryModelImpl.fromJson;

  @override
  int get resultid;
  @override
  int get roundid;
  @override
  int get heat;
  @override
  int get lane;
  @override
  int get racerid;
  @override
  String get name;
  @override
  int get carnumber;
  @override
  @OnDeckResultConverter()
  double? get result; // z-prefix removed, null if not finished
  @override
  @JsonKey(name: 'carphoto')
  Map<String, dynamic>? get carPhoto;

  /// Create a copy of OnDeckEntryModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$OnDeckEntryModelImplCopyWith<_$OnDeckEntryModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
mixin _$OnDeckResponse {
  List<OnDeckEntryModel> get chart => throw _privateConstructorUsedError;

  /// Create a copy of OnDeckResponse
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $OnDeckResponseCopyWith<OnDeckResponse> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $OnDeckResponseCopyWith<$Res> {
  factory $OnDeckResponseCopyWith(
    OnDeckResponse value,
    $Res Function(OnDeckResponse) then,
  ) = _$OnDeckResponseCopyWithImpl<$Res, OnDeckResponse>;
  @useResult
  $Res call({List<OnDeckEntryModel> chart});
}

/// @nodoc
class _$OnDeckResponseCopyWithImpl<$Res, $Val extends OnDeckResponse>
    implements $OnDeckResponseCopyWith<$Res> {
  _$OnDeckResponseCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of OnDeckResponse
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({Object? chart = null}) {
    return _then(
      _value.copyWith(
            chart: null == chart
                ? _value.chart
                : chart // ignore: cast_nullable_to_non_nullable
                      as List<OnDeckEntryModel>,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$OnDeckResponseImplCopyWith<$Res>
    implements $OnDeckResponseCopyWith<$Res> {
  factory _$$OnDeckResponseImplCopyWith(
    _$OnDeckResponseImpl value,
    $Res Function(_$OnDeckResponseImpl) then,
  ) = __$$OnDeckResponseImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({List<OnDeckEntryModel> chart});
}

/// @nodoc
class __$$OnDeckResponseImplCopyWithImpl<$Res>
    extends _$OnDeckResponseCopyWithImpl<$Res, _$OnDeckResponseImpl>
    implements _$$OnDeckResponseImplCopyWith<$Res> {
  __$$OnDeckResponseImplCopyWithImpl(
    _$OnDeckResponseImpl _value,
    $Res Function(_$OnDeckResponseImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of OnDeckResponse
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({Object? chart = null}) {
    return _then(
      _$OnDeckResponseImpl(
        chart: null == chart
            ? _value._chart
            : chart // ignore: cast_nullable_to_non_nullable
                  as List<OnDeckEntryModel>,
      ),
    );
  }
}

/// @nodoc

class _$OnDeckResponseImpl implements _OnDeckResponse {
  const _$OnDeckResponseImpl({final List<OnDeckEntryModel> chart = const []})
    : _chart = chart;

  final List<OnDeckEntryModel> _chart;
  @override
  @JsonKey()
  List<OnDeckEntryModel> get chart {
    if (_chart is EqualUnmodifiableListView) return _chart;
    // ignore: implicit_dynamic_type
    return EqualUnmodifiableListView(_chart);
  }

  @override
  String toString() {
    return 'OnDeckResponse(chart: $chart)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$OnDeckResponseImpl &&
            const DeepCollectionEquality().equals(other._chart, _chart));
  }

  @override
  int get hashCode =>
      Object.hash(runtimeType, const DeepCollectionEquality().hash(_chart));

  /// Create a copy of OnDeckResponse
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$OnDeckResponseImplCopyWith<_$OnDeckResponseImpl> get copyWith =>
      __$$OnDeckResponseImplCopyWithImpl<_$OnDeckResponseImpl>(
        this,
        _$identity,
      );
}

abstract class _OnDeckResponse implements OnDeckResponse {
  const factory _OnDeckResponse({final List<OnDeckEntryModel> chart}) =
      _$OnDeckResponseImpl;

  @override
  List<OnDeckEntryModel> get chart;

  /// Create a copy of OnDeckResponse
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$OnDeckResponseImplCopyWith<_$OnDeckResponseImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
