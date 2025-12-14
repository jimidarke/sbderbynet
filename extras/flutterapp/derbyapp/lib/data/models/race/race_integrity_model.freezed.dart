// coverage:ignore-file
// GENERATED CODE - DO NOT MODIFY BY HAND
// ignore_for_file: type=lint
// ignore_for_file: unused_element, deprecated_member_use, deprecated_member_use_from_same_package, use_function_type_syntax_for_parameters, unnecessary_const, avoid_init_to_null, invalid_override_different_default_values_named, prefer_expression_function_bodies, annotate_overrides, invalid_annotation_target, unnecessary_question_mark

part of 'race_integrity_model.dart';

// **************************************************************************
// FreezedGenerator
// **************************************************************************

T _$identity<T>(T value) => value;

final _privateConstructorUsedError = UnsupportedError(
  'It seems like you constructed your class using `MyClass._()`. This constructor is only meant to be used by freezed and you are not supposed to need it nor use it.\nPlease check the documentation here for more information: https://github.com/rrousselGit/freezed#adding-getters-and-methods-to-our-models',
);

RaceIntegrityModel _$RaceIntegrityModelFromJson(Map<String, dynamic> json) {
  return _RaceIntegrityModel.fromJson(json);
}

/// @nodoc
mixin _$RaceIntegrityModel {
  String get status => throw _privateConstructorUsedError;
  String get code => throw _privateConstructorUsedError;
  String get message => throw _privateConstructorUsedError;

  /// Serializes this RaceIntegrityModel to a JSON map.
  Map<String, dynamic> toJson() => throw _privateConstructorUsedError;

  /// Create a copy of RaceIntegrityModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  $RaceIntegrityModelCopyWith<RaceIntegrityModel> get copyWith =>
      throw _privateConstructorUsedError;
}

/// @nodoc
abstract class $RaceIntegrityModelCopyWith<$Res> {
  factory $RaceIntegrityModelCopyWith(
    RaceIntegrityModel value,
    $Res Function(RaceIntegrityModel) then,
  ) = _$RaceIntegrityModelCopyWithImpl<$Res, RaceIntegrityModel>;
  @useResult
  $Res call({String status, String code, String message});
}

/// @nodoc
class _$RaceIntegrityModelCopyWithImpl<$Res, $Val extends RaceIntegrityModel>
    implements $RaceIntegrityModelCopyWith<$Res> {
  _$RaceIntegrityModelCopyWithImpl(this._value, this._then);

  // ignore: unused_field
  final $Val _value;
  // ignore: unused_field
  final $Res Function($Val) _then;

  /// Create a copy of RaceIntegrityModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? status = null,
    Object? code = null,
    Object? message = null,
  }) {
    return _then(
      _value.copyWith(
            status: null == status
                ? _value.status
                : status // ignore: cast_nullable_to_non_nullable
                      as String,
            code: null == code
                ? _value.code
                : code // ignore: cast_nullable_to_non_nullable
                      as String,
            message: null == message
                ? _value.message
                : message // ignore: cast_nullable_to_non_nullable
                      as String,
          )
          as $Val,
    );
  }
}

/// @nodoc
abstract class _$$RaceIntegrityModelImplCopyWith<$Res>
    implements $RaceIntegrityModelCopyWith<$Res> {
  factory _$$RaceIntegrityModelImplCopyWith(
    _$RaceIntegrityModelImpl value,
    $Res Function(_$RaceIntegrityModelImpl) then,
  ) = __$$RaceIntegrityModelImplCopyWithImpl<$Res>;
  @override
  @useResult
  $Res call({String status, String code, String message});
}

/// @nodoc
class __$$RaceIntegrityModelImplCopyWithImpl<$Res>
    extends _$RaceIntegrityModelCopyWithImpl<$Res, _$RaceIntegrityModelImpl>
    implements _$$RaceIntegrityModelImplCopyWith<$Res> {
  __$$RaceIntegrityModelImplCopyWithImpl(
    _$RaceIntegrityModelImpl _value,
    $Res Function(_$RaceIntegrityModelImpl) _then,
  ) : super(_value, _then);

  /// Create a copy of RaceIntegrityModel
  /// with the given fields replaced by the non-null parameter values.
  @pragma('vm:prefer-inline')
  @override
  $Res call({
    Object? status = null,
    Object? code = null,
    Object? message = null,
  }) {
    return _then(
      _$RaceIntegrityModelImpl(
        status: null == status
            ? _value.status
            : status // ignore: cast_nullable_to_non_nullable
                  as String,
        code: null == code
            ? _value.code
            : code // ignore: cast_nullable_to_non_nullable
                  as String,
        message: null == message
            ? _value.message
            : message // ignore: cast_nullable_to_non_nullable
                  as String,
      ),
    );
  }
}

/// @nodoc
@JsonSerializable()
class _$RaceIntegrityModelImpl implements _RaceIntegrityModel {
  const _$RaceIntegrityModelImpl({
    this.status = 'ok',
    this.code = 'ok',
    this.message = '',
  });

  factory _$RaceIntegrityModelImpl.fromJson(Map<String, dynamic> json) =>
      _$$RaceIntegrityModelImplFromJson(json);

  @override
  @JsonKey()
  final String status;
  @override
  @JsonKey()
  final String code;
  @override
  @JsonKey()
  final String message;

  @override
  String toString() {
    return 'RaceIntegrityModel(status: $status, code: $code, message: $message)';
  }

  @override
  bool operator ==(Object other) {
    return identical(this, other) ||
        (other.runtimeType == runtimeType &&
            other is _$RaceIntegrityModelImpl &&
            (identical(other.status, status) || other.status == status) &&
            (identical(other.code, code) || other.code == code) &&
            (identical(other.message, message) || other.message == message));
  }

  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  int get hashCode => Object.hash(runtimeType, status, code, message);

  /// Create a copy of RaceIntegrityModel
  /// with the given fields replaced by the non-null parameter values.
  @JsonKey(includeFromJson: false, includeToJson: false)
  @override
  @pragma('vm:prefer-inline')
  _$$RaceIntegrityModelImplCopyWith<_$RaceIntegrityModelImpl> get copyWith =>
      __$$RaceIntegrityModelImplCopyWithImpl<_$RaceIntegrityModelImpl>(
        this,
        _$identity,
      );

  @override
  Map<String, dynamic> toJson() {
    return _$$RaceIntegrityModelImplToJson(this);
  }
}

abstract class _RaceIntegrityModel implements RaceIntegrityModel {
  const factory _RaceIntegrityModel({
    final String status,
    final String code,
    final String message,
  }) = _$RaceIntegrityModelImpl;

  factory _RaceIntegrityModel.fromJson(Map<String, dynamic> json) =
      _$RaceIntegrityModelImpl.fromJson;

  @override
  String get status;
  @override
  String get code;
  @override
  String get message;

  /// Create a copy of RaceIntegrityModel
  /// with the given fields replaced by the non-null parameter values.
  @override
  @JsonKey(includeFromJson: false, includeToJson: false)
  _$$RaceIntegrityModelImplCopyWith<_$RaceIntegrityModelImpl> get copyWith =>
      throw _privateConstructorUsedError;
}
