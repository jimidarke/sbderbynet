import 'package:freezed_annotation/freezed_annotation.dart';

part 'round_model.freezed.dart';
part 'round_model.g.dart';

@freezed
class RoundModel with _$RoundModel {
  const factory RoundModel({
    required int roundid,
    required int classid,
    @Default('') String class_,
    @Default('') String round,
    @Default('') String name,
    @Default('') String roundname,
    @Default(false) bool aggregate,
    @JsonKey(name: 'roster_size') @Default(0) int rosterSize,
    @Default(0) int passed,
    @Default(0) int registered,
    @Default(0) int unscheduled,
    @JsonKey(name: 'heats_scheduled') @Default(0) int heatsScheduled,
    @JsonKey(name: 'heats_run') @Default(0) int heatsRun,
  }) = _RoundModel;

  factory RoundModel.fromJson(Map<String, dynamic> json) =>
      _$RoundModelFromJson(json);
}
