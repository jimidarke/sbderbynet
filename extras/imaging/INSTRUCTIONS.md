# SBDerbyNet — SD Card Recovery (1-page operator sheet)

**Use this when a Pi has died and you need a replacement card.**  Time budget: ~30 minutes per card.

---

## What you need on hand

1. The race-day USB stick (labeled **USB-DERBYNET**)
2. A Windows laptop with a microSD slot (or USB SD reader)
3. A fresh microSD card — **SanDisk Industrial or Samsung PRO Endurance recommended**
4. Phone in your pocket in case something goes wrong (number on the back of this sheet)

## 1 — Pick the right image (look at the dead Pi)

| If the dead Pi is… | Flash this image | Card label |
|--------------------|------------------|------------|
| The **central server** (one box, ethernet, RTC chip) | `sbderbynet-derbypi-…img.xz` | RED |
| A **finish-line timer** (one per lane, has DIP switches) | `sbderbynet-finishtimer-…img.xz` | YELLOW |
| A **kiosk / TV display** | `sbderbynet-derbydisplay-…img.xz` | GREEN |

## 2 — Flash with Pi Imager (Windows)

1. Plug USB stick into laptop.
2. Open `tools\pi-imager-installer.exe`. Install if needed.
3. Open **Raspberry Pi Imager**.
4. **Choose Device → No filtering**.
5. **Choose OS → Use custom → Browse** to `USB:\images\sbderbynet-<role>-<sha>.img.xz`.
6. **Choose Storage** → pick the microSD.
7. Click **Next**. **When asked "Apply OS customisation settings?" click NO** (the image is already customized).
8. **Yes, erase the SD card** → Write. Wait ~5 minutes.

## 3 — Set the device ID (Notepad, ~30 seconds)

After Pi Imager finishes verifying:

1. In Windows Explorer, open the drive labeled **bootfs**.
2. Right-click **`derbyid.txt`** → **Open with → Notepad**.
3. Replace `CHANGE-ME` with the correct ID:
   - **DerbyPi:** type `derbypi` (or just leave `CHANGE-ME` — the image is fine without an edit for the central server).
   - **Finishtimer:** the DIP switches set the lane automatically, so this is just the hardware ID — type `FT001` for lane 1, `FT002` for lane 2, etc. (Or leave `CHANGE-ME` and the firstboot script will auto-fill `FT00<lane>` from the DIP switches.)
   - **Derbydisplay:** type `DD01`, `DD02`, … based on which TV it's going to.
4. Save (Ctrl+S). Close Notepad.
5. (DerbyPi only, optional) If recovering from a saved race day: copy the most recent `.sqlite3.gz` from `USB:\backups\` into a new folder `bootfs:\restore\`. Also copy the matching `.sha256` file.

## 4 — Eject + boot

1. Click the USB icon in the Windows tray → **Eject** the SD card.
2. Take the SD card out, plug it into the target Pi, power on.
3. Wait **3 minutes**. The Pi will reboot itself once during first-boot setup — this is normal.

## 5 — Verify (no SSH needed)

| Pi role | What you'll see when it worked |
|---------|--------------------------------|
| **DerbyPi** | From the laptop, browse to `http://192.168.100.10/derbynet/` — the DerbyNet UI loads. |
| **Finishtimer** | The 7-segment display shows the lane number, then `----`, then the green LED pulses. |
| **Derbydisplay** | The TV shows the kiosk page within 60 seconds (after a brief "loading" splash). |

If you don't see those signs after 5 minutes total, **see `TROUBLESHOOTING.pdf`** on the USB stick, or call the number on the back of this sheet.

---

## Fallback: Rufus (if Pi Imager won't work)

1. In `USB:\tools\7zPortable\` run `7zG.exe`. Open the `.img.xz` file. Click "Extract" → save the `.img` next to it.
2. Open `tools\rufus-portable.exe`. Pick the SD card, pick the extracted `.img`, click **Start**. If Windows says "format drive?" after — click **Cancel**.
3. Continue with step 3 above (edit `derbyid.txt`).

---

*Version stamp: replace this line with the workflow's build SHA when the PDF is regenerated.*
