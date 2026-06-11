// Pinny (car number) display form. carnumber is an INTEGER column in the
// database, so a pinny printed "0004" on the physical bib arrives here as 4;
// restore the 4-digit zero padding whenever a carnumber is shown to a human.
// Mirror of pinny_display() in inc/data.inc.
function pinnyDisplay(carnumber) {
  var s = String(carnumber);
  if (!/^\d+$/.test(s)) {
    return s;
  }
  while (s.length < 4) {
    s = '0' + s;
  }
  return s;
}
