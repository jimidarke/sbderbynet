import 'package:freezed_annotation/freezed_annotation.dart';

part 'current_heat_model.freezed.dart';
part 'current_heat_model.g.dart';

@freezed
class CurrentHeatModel with _$CurrentHeatModel {
  const factory CurrentHeatModel({
    @JsonKey(name: 'now_racing') required bool nowRacing,
    @JsonKey(name: 'use_master_sched') @Default(false) bool useMasterSched,
    @JsonKey(name: 'use_points') @Default(false) bool usePoints,
    int? classid,
    int? roundid,
    int? round,
    @JsonKey(name: 'tbodyid') int? tbodyId,
    int? heat,
    @JsonKey(name: 'number-of-heats') @Default(0) int numberOfHeats,
    @JsonKey(name: 'class') String? className,
    int? masterheat,
    @JsonKey(name: 'max_masterheat') int? maxMasterheat,
  }) = _CurrentHeatModel;

  factory CurrentHeatModel.fromJson(Map<String, dynamic> json) =>
      _$CurrentHeatModelFromJson(json);
}
