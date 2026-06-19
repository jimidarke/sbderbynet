<?php
// Standalone functional test for ad-hoc racing mode. No running server or
// network needed — builds a throwaway "official" DB from the real schema and
// exercises the real inc/adhoc.inc, inc/adhoc-standings.inc, and inc/db-marker.inc
// code paths.
//
//   Run:  php testing/test-adhoc-mode.php
//   Needs: PHP CLI with pdo_sqlite. Exits 0 on success, 1 on any failed check.
//
// See docs/ADHOC.md.

error_reporting(E_ALL & ~E_DEPRECATED & ~E_NOTICE & ~E_WARNING);
$WEB = dirname(__DIR__) . '/website';
chdir($WEB);

if (!in_array('sqlite', PDO::getAvailableDrivers(), true)) {
  fwrite(STDERR, "SKIP: pdo_sqlite not available in this PHP CLI\n");
  exit(2);
}

$tmp = sys_get_temp_dir() . '/adhoc-test-' . getmypid();
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
$ins = $build->prepare("INSERT INTO RegistrationInfo(racerid,carnumber,lastname,firstname,classid,rankid,partitionid,passedinspection,exclude)
                        VALUES(:id,:c,:ln,:fn,:cl,:rk,1,1,0)");
$racers = array(
  array(1, 11, $c911,  1), array(2, 12, $c911,  1), array(3, 13, $c911,  1),
  array(4, 21, $c1214, 2), array(5, 22, $c1214, 2),
);
foreach ($racers as $r) {
  $ins->execute(array(':id'=>$r[0], ':c'=>$r[1], ':ln'=>'L'.$r[1], ':fn'=>'F'.$r[1], ':cl'=>$r[2], ':rk'=>$r[3]));
}
// a NOT-checked-in racer (must be excluded from roster + resolve + leaderboard)
$ins->execute(array(':id'=>6, ':c'=>99, ':ln'=>'L99', ':fn'=>'F99', ':cl'=>$c911, ':rk'=>1));
$build->exec("UPDATE RegistrationInfo SET passedinspection=0 WHERE racerid=6");
$build->exec("INSERT INTO RaceInfo(itemkey,itemvalue) VALUES('lane_count','3')");
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

putenv("DERBYNET_ACTIVE_DB_MARKER=$tmp/active-db");
$_SERVER['DERBYNET_ACTIVE_DB_MARKER'] = "$tmp/active-db";
$_SERVER['DERBYNET_CONFIG_DIR'] = "$tmp/cfg";

require_once("$WEB/inc/data.inc");   // connects to official via the shim

echo "\n--- marker helpers ---\n";
require_once("$WEB/inc/db-marker.inc");
check(dn_resolve_active_db($official) === $official, "no marker -> official DB");
// The allowlist requires the target file to EXIST: a dangling marker fail-safes
// to official. adhoc.sqlite3 does not exist yet, so it must be rejected here.
check(!dn_db_path_allowed("$tmp/adhoc.sqlite3", $official), "non-existent sibling rejected (fail-safe)");
check(!dn_db_path_allowed("/etc/passwd", $official), "non-sqlite path rejected");
check(!dn_db_path_allowed("$tmp/../evil.sqlite3", $official), "path traversal rejected");

echo "\n--- adhoc_build() (real inc/adhoc.inc) ---\n";
require_once("$WEB/inc/adhoc.inc");
check(adhoc_official_db_path() === $official, "adhoc_official_db_path() resolves");
check(adhoc_db_path() === "$tmp/adhoc.sqlite3", "adhoc_db_path() is sibling");
$info = adhoc_build();
check(is_file($info['path']), "adhoc.sqlite3 created at {$info['path']}");
check($info['racers'] == 5, "seeded {$info['racers']} racers (expect 5, racer6 not checked in)");
check($info['roundid'] > 0, "ad-hoc round created (roundid={$info['roundid']})");

echo "\n--- marker set/resolve round-trip ---\n";
check(dn_db_path_allowed($info['path'], $official), "existing sibling adhoc.sqlite3 allowed");
check(dn_set_active_db($info['path']), "dn_set_active_db wrote marker");
check(dn_resolve_active_db($official) === $info['path'], "marker now resolves to adhoc DB");

// ---- 3. Switch global $db to the freshly built ad-hoc DB -------------------
$db = new PDO('sqlite:' . $info['path'], '', '', array());
$db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
$db->setAttribute(PDO::ATTR_CASE, PDO::CASE_LOWER);
$GLOBALS['db'] = $db;

check(adhoc_mode_active(), "adhoc_mode_active() true on built DB");
check(adhoc_roundid() == $info['roundid'], "adhoc_roundid() persisted");
check(read_raceinfo('scoring') == '2', "scoring=2 (best single time)");
check(read_single_value('SELECT COUNT(*) FROM RaceChart') == 0, "RaceChart empty after build");

echo "\n--- adhoc_resolve_pinny() (real fn) ---\n";
check(adhoc_resolve_pinny('11') == 1, "pinny 11 -> racerid 1");
check(adhoc_resolve_pinny('0011') == 1, "zero-padded 0011 -> racerid 1");
check(adhoc_resolve_pinny('999') === 0, "unknown pinny -> 0");
check(adhoc_resolve_pinny('99') === 0, "not-checked-in pinny 99 -> 0");

echo "\n--- simulate runs + adhoc_leaderboard_groups() (real fn) ---\n";
$rid = $info['roundid']; $cid = $info['classid'];
$rc = $db->prepare("INSERT INTO RaceChart(roundid,heat,lane,racerid,classid,finishtime)
                    VALUES(:r,:h,:l,:rid,:c,:t)");
$runs = array(
  array(1,1,1,12.500), array(1,2,2,13.000), array(1,3,4,14.000),
  array(2,1,1,11.800), array(2,2,3,12.200), array(2,3,5,99.999), // racer5 DNF only
  array(3,1,2,12.900), array(3,2,4,13.500),
);
foreach ($runs as $u) {
  $rc->execute(array(':r'=>$rid, ':h'=>$u[0], ':l'=>$u[1], ':rid'=>$u[2], ':c'=>$cid, ':t'=>$u[3]));
}

require_once("$WEB/inc/adhoc-standings.inc");
$groups = adhoc_leaderboard_groups(3);
$byclass = array();
foreach ($groups as $g) { $byclass[$g['class']] = $g['entries']; }

check(isset($byclass['9-11']) && isset($byclass['12-14']), "both age groups present");
check(!isset($byclass['Ad-Hoc Open']), "synthetic Ad-Hoc Open class NOT on leaderboard");
$g911 = $byclass['9-11'];
check(count($g911) == 3, "9-11 has 3 entries");
check($g911[0]['carnumber'] == 11 && abs($g911[0]['best_time']-11.8) < 0.001, "9-11 #1 = pinny 11 @ 11.8 (best-of)");
check($g911[1]['carnumber'] == 13 && abs($g911[1]['best_time']-12.2) < 0.001, "9-11 #2 = pinny 13 @ 12.2");
check($g911[2]['carnumber'] == 12 && abs($g911[2]['best_time']-12.9) < 0.001, "9-11 #3 = pinny 12 @ 12.9");
$g1214 = $byclass['12-14'];
check(count($g1214) == 1, "12-14 has 1 entry (DNF-only racer excluded)");
check($g1214[0]['carnumber'] == 21 && abs($g1214[0]['best_time']-13.5) < 0.001, "12-14 #1 = pinny 21 @ 13.5");

echo "\n--- renderer smoke (adhoc_write_leaderboard) ---\n";
ob_start(); adhoc_write_leaderboard(3); $html = ob_get_clean();
check(strpos($html, '0011') !== false, "renderer zero-pads pinny (0011)");
check(strpos($html, 'F11') === false && strpos($html, 'L11') === false, "renderer emits NO racer names (PII)");

echo "\n--- isolation: official DB untouched ---\n";
$off = new PDO('sqlite:' . $official, '', '', array());
$off->setAttribute(PDO::ATTR_CASE, PDO::CASE_LOWER);
check($off->query('SELECT COUNT(*) FROM RaceChart')->fetchColumn() == 0, "official RaceChart still empty");
check($off->query("SELECT COUNT(*) FROM RaceInfo WHERE itemkey='adhoc-mode'")->fetchColumn() == 0, "official has no adhoc-mode flag");
check($off->query("SELECT COUNT(*) FROM Classes WHERE class='Ad-Hoc Open'")->fetchColumn() == 0, "official has no Ad-Hoc Open class");
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
