<?php
// Standalone functional test for the ROSTER-LESS ad-hoc racing redesign.
// No running server or network needed — builds a throwaway "official" DB from
// the real schema and exercises the real inc/adhoc.inc, inc/adhoc-standings.inc
// and inc/db-marker.inc code paths.
//
//   Run:  php testing/test-adhoc-rosterless.php
//   Needs: PHP CLI with pdo_sqlite. Exits 0 on success, 1 on any failed check,
//          2 if pdo_sqlite is unavailable.
//
// What it proves (the redesign contract, see docs/ADHOC.md):
//   * adhoc_build() builds adhoc.sqlite3 FRESH from the schema — it does NOT
//     copy the live official DB and does NOT mirror the roster. The ad-hoc DB
//     has the event's age-group Classes but ZERO RegistrationInfo/Roster/RaceChart.
//   * RaceChart carries display_pinny + agegroup_classid so a run is self-
//     describing with NO racer row (racerid stays NULL).
//   * adhoc_arm_heat() validates pinny + age group and inserts roster-less rows.
//   * adhoc_leaderboard_groups() ranks best-single-time per age group, DNF out,
//     top-N, pinny + time only (no names).
//   * dn_set_active_db() writes the marker atomically (no .tmp left behind).
//   * The official DB is byte-untouched by an ad-hoc session.

error_reporting(E_ALL & ~E_DEPRECATED & ~E_NOTICE & ~E_WARNING);
$WEB = dirname(__DIR__) . '/website';
chdir($WEB);

if (!in_array('sqlite', PDO::getAvailableDrivers(), true)) {
  fwrite(STDERR, "SKIP: pdo_sqlite not available in this PHP CLI\n");
  exit(2);
}

$tmp = sys_get_temp_dir() . '/adhoc-rl-' . getmypid();
@mkdir($tmp, 0777, true);
@mkdir("$tmp/cfg", 0777, true);
$official = "$tmp/derbynet.sqlite3";

$fail = 0;
function check($cond, $label) {
  global $fail;
  echo ($cond ? "  PASS  " : "  FAIL  ") . $label . "\n";
  if (!$cond) $fail++;
}

// ---- 1. Build the official DB from the real schema -------------------------
$build = new PDO('sqlite:' . $official);
$build->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
$build->setAttribute(PDO::ATTR_CASE, PDO::CASE_LOWER);
$GLOBALS['db'] = $build; $GLOBALS['dbtype'] = 'sqlite';
require_once("$WEB/inc/schema_version.inc");
require_once("$WEB/inc/sql-script.inc");
$script = include("$WEB/sql/sqlite/schema.inc");
foreach ($script as $stmt) { $build->exec($stmt); }

$build->exec("INSERT INTO Classes(class, sortorder) VALUES('9-11', 1), ('12-14', 2)");
$c911  = $build->query("SELECT classid FROM Classes WHERE class='9-11'")->fetchColumn();
$c1214 = $build->query("SELECT classid FROM Classes WHERE class='12-14'")->fetchColumn();
$build->exec("INSERT INTO Ranks(rankid, rank, classid) VALUES(1,'R1',$c911),(2,'R2',$c1214)");
// A roster exists in OFFICIAL — the redesign must NOT copy it into ad-hoc.
$ins = $build->prepare("INSERT INTO RegistrationInfo(racerid,carnumber,lastname,firstname,classid,rankid,partitionid,passedinspection,exclude)
                        VALUES(:id,:c,:ln,:fn,:cl,:rk,1,1,0)");
foreach (array(array(1,11,$c911,1), array(2,12,$c911,1), array(3,13,$c911,1),
               array(4,21,$c1214,2), array(5,22,$c1214,2)) as $r) {
  $ins->execute(array(':id'=>$r[0], ':c'=>$r[1], ':ln'=>'L'.$r[1], ':fn'=>'F'.$r[1], ':cl'=>$r[2], ':rk'=>$r[3]));
}
$build->exec("INSERT INTO RaceInfo(itemkey,itemvalue) VALUES('lane_count','3')");
$official_reg_count = (int)$build->query('SELECT COUNT(*) FROM RegistrationInfo')->fetchColumn();
$build = null; $GLOBALS['db'] = null;

// ---- 2. Boot DerbyNet pointed at the temp DB via a temp config shim --------
file_put_contents("$tmp/cfg/config-database.inc",
  "<?php\n" .
  "\$official_db_path = " . var_export($official, true) . ";\n" .
  "\$GLOBALS['official_db_path'] = \$official_db_path;\n" .
  "\$db_path = \$official_db_path;\n" .
  "\$mi = " . var_export("$WEB/inc/db-marker.inc", true) . ";\n" .
  "if (@is_file(\$mi)) { require_once(\$mi); if (function_exists('dn_resolve_active_db')) \$db_path = dn_resolve_active_db(\$official_db_path); }\n" .
  "\$homedir = dirname(\$db_path);\n" .
  "\$db = new PDO('sqlite:'.\$db_path, '', '', array());\n" .
  "\$db->setAttribute(PDO::ATTR_CASE, PDO::CASE_LOWER);\n");

$marker = "$tmp/active-db";
putenv("DERBYNET_ACTIVE_DB_MARKER=$marker");
$_SERVER['DERBYNET_ACTIVE_DB_MARKER'] = $marker;
$_SERVER['DERBYNET_CONFIG_DIR'] = "$tmp/cfg";

require_once("$WEB/inc/data.inc");   // connects to official via the shim

echo "\n--- marker helpers (fail-safe allowlist) ---\n";
require_once("$WEB/inc/db-marker.inc");
check(dn_resolve_active_db($official) === $official, "no marker -> official DB");
check(!dn_db_path_allowed("$tmp/adhoc.sqlite3", $official), "non-existent sibling rejected (fail-safe)");
check(!dn_db_path_allowed("/etc/passwd", $official), "non-sqlite path rejected");
check(!dn_db_path_allowed("$tmp/../evil.sqlite3", $official), "path traversal rejected");

echo "\n--- adhoc_build(): FRESH, roster-less ---\n";
require_once("$WEB/inc/adhoc.inc");
check(adhoc_official_db_path() === $official, "adhoc_official_db_path() resolves");
check(adhoc_db_path() === "$tmp/adhoc.sqlite3", "adhoc_db_path() is sibling");
$info = adhoc_build();
check(is_file($info['path']), "adhoc.sqlite3 created at {$info['path']}");
check($GLOBALS['db'] !== null, "live \$db restored after build (not left on adhoc)");

// Open the freshly built ad-hoc DB directly and inspect it.
$a = new PDO('sqlite:' . $info['path'], '', '', array());
$a->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
$a->setAttribute(PDO::ATTR_CASE, PDO::CASE_LOWER);

check((int)$a->query('SELECT COUNT(*) FROM RegistrationInfo')->fetchColumn() === 0,
      "ad-hoc DB has ZERO RegistrationInfo rows (roster NOT copied)");
check((int)$a->query('SELECT COUNT(*) FROM Roster')->fetchColumn() === 0,
      "ad-hoc DB has ZERO Roster rows");
check((int)$a->query('SELECT COUNT(*) FROM RaceChart')->fetchColumn() === 0,
      "ad-hoc DB has ZERO RaceChart rows");
check((int)$a->query("SELECT COUNT(*) FROM Classes WHERE class='9-11'")->fetchColumn() === 1
   && (int)$a->query("SELECT COUNT(*) FROM Classes WHERE class='12-14'")->fetchColumn() === 1,
      "event age-group Classes seeded into ad-hoc DB");
check((int)$a->query("SELECT COUNT(*) FROM Classes WHERE class='Ad-Hoc Open'")->fetchColumn() === 1,
      "synthetic Ad-Hoc Open class present");
check((string)$a->query("SELECT itemvalue FROM RaceInfo WHERE itemkey='adhoc-mode'")->fetchColumn() === '1',
      "adhoc-mode=1 stamped");
check((string)$a->query("SELECT itemvalue FROM RaceInfo WHERE itemkey='scoring'")->fetchColumn() === '2',
      "scoring=2 (best single time)");
check((string)$a->query("SELECT itemvalue FROM RaceInfo WHERE itemkey='lane_count'")->fetchColumn() === '3',
      "lane_count carried from official (=3)");

// new self-describing columns must exist
$cols = array();
foreach ($a->query("PRAGMA table_info(RaceChart)") as $ci) { $cols[strtolower($ci['name'])] = true; }
check(isset($cols['display_pinny']), "RaceChart.display_pinny column exists");
check(isset($cols['agegroup_classid']), "RaceChart.agegroup_classid column exists");
$a = null;

echo "\n--- marker set/resolve + ATOMIC write ---\n";
check(dn_db_path_allowed($info['path'], $official), "existing sibling adhoc.sqlite3 allowed");
check(dn_set_active_db($info['path']), "dn_set_active_db wrote marker");
check(!is_file($marker . '.tmp'), "no marker .tmp left behind (atomic rename)");
check(dn_resolve_active_db($official) === $info['path'], "marker now resolves to adhoc DB");

// ---- 3. Switch live $db to the ad-hoc DB -----------------------------------
$db = new PDO('sqlite:' . $info['path'], '', '', array());
$db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
$db->setAttribute(PDO::ATTR_CASE, PDO::CASE_LOWER);
$GLOBALS['db'] = $db;

check(adhoc_mode_active(), "adhoc_mode_active() true on built DB");
check(adhoc_roundid() == $info['roundid'], "adhoc_roundid() persisted");

echo "\n--- adhoc_age_groups(): real groups only ---\n";
$ag = adhoc_age_groups();
$agnames = array_map(function($g){ return $g['class']; }, $ag);
check(in_array('9-11', $agnames) && in_array('12-14', $agnames), "age groups include 9-11 and 12-14");
check(!in_array('Ad-Hoc Open', $agnames), "synthetic Ad-Hoc Open NOT offered as an age group");
$g911id = null; $g1214id = null;
foreach ($ag as $g) { if ($g['class']==='9-11') $g911id=$g['classid']; if ($g['class']==='12-14') $g1214id=$g['classid']; }

echo "\n--- adhoc_arm_heat(): roster-less inserts + validation ---\n";
$h1 = adhoc_arm_heat(array(
  array('pinny' => '0042', 'agegroup_classid' => $g911id),   // pinny not in any roster
  array('pinny' => '7',    'agegroup_classid' => $g1214id),
  array('pinny' => '13',   'agegroup_classid' => $g911id),
));
check($h1['heat'] == 1, "first arm mints heat 1");
check($h1['lanes'] == 3, "3 lanes armed");
$rows = $db->query("SELECT lane, racerid, display_pinny, agegroup_classid FROM RaceChart WHERE heat=1 ORDER BY lane")->fetchAll(PDO::FETCH_ASSOC);
check(count($rows) == 3, "3 RaceChart rows for heat 1");
check($rows[0]['racerid'] === null, "racerid is NULL (roster-less)");
check($rows[0]['display_pinny'] === '42', "display_pinny normalized to '42'");
check((int)$rows[0]['agegroup_classid'] === (int)$g911id, "agegroup_classid stored");

$h2 = adhoc_arm_heat(array(array('pinny' => '42', 'agegroup_classid' => $g911id)));
check($h2['heat'] == 2, "second arm mints heat 2 (same pinny may run again)");

// validation: all-or-nothing
$threw = false; try { adhoc_arm_heat(array(array('pinny'=>'5','agegroup_classid'=>99999))); } catch (Exception $e) { $threw = true; }
check($threw, "unknown age group rejected");
$threw = false; try { adhoc_arm_heat(array(array('pinny'=>'8','agegroup_classid'=>$g911id), array('pinny'=>'8','agegroup_classid'=>$g911id))); } catch (Exception $e) { $threw = true; }
check($threw, "duplicate pinny in one heat rejected");
$threw = false; try { adhoc_arm_heat(array()); } catch (Exception $e) { $threw = true; }
check($threw, "empty heat rejected");
$threw = false; try { adhoc_arm_heat(array(array('pinny'=>'0','agegroup_classid'=>$g911id))); } catch (Exception $e) { $threw = true; }
check($threw, "non-positive pinny rejected");

echo "\n--- bye lane in the middle preserves physical lane ---\n";
// Real finish timers report by PHYSICAL lane, so an empty middle lane must keep
// lanes 1 and 3 (NOT compact to 1,2). Pinnies 50/51 get no time -> never reach
// the leaderboard, so this does not perturb the standings assertions below.
$hbye = adhoc_arm_heat(array(
  array('pinny' => '50', 'agegroup_classid' => $g911id),
  array('pinny' => '',   'agegroup_classid' => 0),       // empty middle lane = bye
  array('pinny' => '51', 'agegroup_classid' => $g1214id),
));
check($hbye['lanes'] == 2, "bye heat has 2 cars");
$byerows = $db->query("SELECT lane, display_pinny FROM RaceChart WHERE heat={$hbye['heat']} ORDER BY lane")->fetchAll(PDO::FETCH_ASSOC);
check(count($byerows) == 2 && $byerows[0]['lane'] == 1 && $byerows[1]['lane'] == 3,
      "physical lanes preserved (1 and 3, not compacted to 1,2)");

echo "\n--- simulate FINISHED times (lane-keyed, racerid-independent) ---\n";
// heat1: 42=12.5, 7=13.5, 13=12.2 ; heat2: 42=11.8 (best)
$set = $db->prepare("UPDATE RaceChart SET finishtime=:t WHERE heat=:h AND lane=:l");
$set->execute(array(':t'=>12.500, ':h'=>1, ':l'=>1));
$set->execute(array(':t'=>13.500, ':h'=>1, ':l'=>2));
$set->execute(array(':t'=>12.200, ':h'=>1, ':l'=>3));
$set->execute(array(':t'=>11.800, ':h'=>2, ':l'=>1));
// a DNF-only pinny (99) in 12-14 — must be excluded from the board
$h3 = adhoc_arm_heat(array(array('pinny'=>'99','agegroup_classid'=>$g1214id)));
$db->prepare("UPDATE RaceChart SET finishtime=99.999 WHERE heat=:h AND lane=1")->execute(array(':h'=>$h3['heat']));

echo "\n--- adhoc_leaderboard_groups(): best-of, per age group ---\n";
require_once("$WEB/inc/adhoc-standings.inc");
$groups = adhoc_leaderboard_groups(3);
$byclass = array();
foreach ($groups as $g) { $byclass[$g['class']] = $g['entries']; }
check(isset($byclass['9-11']) && isset($byclass['12-14']), "both age groups present");
check(!isset($byclass['Ad-Hoc Open']), "synthetic Ad-Hoc Open NOT on leaderboard");
$g911 = $byclass['9-11'];
check(count($g911) == 2, "9-11 has 2 entries");
check($g911[0]['carnumber'] == 42 && abs($g911[0]['best_time']-11.8) < 0.001, "9-11 #1 = pinny 42 @ 11.8 (best-of two runs)");
check($g911[1]['carnumber'] == 13 && abs($g911[1]['best_time']-12.2) < 0.001, "9-11 #2 = pinny 13 @ 12.2");
$g1214 = $byclass['12-14'];
check(count($g1214) == 1, "12-14 has 1 entry (DNF-only pinny 99 excluded)");
check($g1214[0]['carnumber'] == 7 && abs($g1214[0]['best_time']-13.5) < 0.001, "12-14 #1 = pinny 7 @ 13.5");

echo "\n--- renderer smoke (adhoc_write_leaderboard) ---\n";
ob_start(); adhoc_write_leaderboard(3); $html = ob_get_clean();
check(strpos($html, '0042') !== false, "renderer zero-pads pinny (0042)");
check(strpos($html, '9-11') !== false, "renderer shows age-group label");

echo "\n--- isolation: official DB untouched ---\n";
$off = new PDO('sqlite:' . $official, '', '', array());
$off->setAttribute(PDO::ATTR_CASE, PDO::CASE_LOWER);
check((int)$off->query('SELECT COUNT(*) FROM RegistrationInfo')->fetchColumn() === $official_reg_count, "official roster unchanged ($official_reg_count rows)");
check((int)$off->query('SELECT COUNT(*) FROM RaceChart')->fetchColumn() === 0, "official RaceChart still empty");
check((int)$off->query("SELECT COUNT(*) FROM RaceInfo WHERE itemkey='adhoc-mode'")->fetchColumn() === 0, "official has no adhoc-mode flag");
check((int)$off->query("SELECT COUNT(*) FROM Classes WHERE class='Ad-Hoc Open'")->fetchColumn() === 0, "official has no Ad-Hoc Open class");
$off = null;

echo "\n--- mode off clears marker ---\n";
check(dn_set_active_db(''), "dn_set_active_db('') cleared marker");
check(dn_resolve_active_db($official) === $official, "resolves back to official after clear");

echo "\n" . ($fail == 0 ? "ALL CHECKS PASSED" : "$fail CHECK(S) FAILED") . "\n";

$db = null;
array_map('unlink', glob("$tmp/*") ?: array());
array_map('unlink', glob("$tmp/cfg/*") ?: array());
@rmdir("$tmp/cfg"); @rmdir($tmp);
exit($fail == 0 ? 0 : 1);
