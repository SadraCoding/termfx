# termfx

هدر انیمیشنی ASCII + ظاهر مدرن شل، برای هر توزیع لینوکس. / Animated ASCII terminal header + modern shell UI for any Linux distro.

## Features

| Category | Count | Examples |
|----------|-------|----------|
| **Effects** | 57 | aurora, fire, matrix, spiral, vortex, dna, tunnel, hologram, galaxy, metaballs, lissajous, circuit, sonar, phosphor, pixelrain… |
| **Palettes** | 66 | catppuccin, tokyonight, dracula, nord, gruvbox, neon, vaporwave, cyberpunk, synthwave, toxic, sakura, nebula, spectrum, cosmic… |
| **Shell Themes** | 8 | catppuccin, tokyonight, dracula, nord, gruvbox, rosepine, onedark, mono + custom |
| **Prompt Styles** | 6 | pills, blocks, sharp, slant, minimal, plain |
| **Info Panel** | 11 presets | classic, compact, minimal, clean, full, gamer, server, developer, aesthetic, hybridfetch, ultra |
| **Info Colours** | 66+ | auto (match header), rainbow, any palette name, or off |
| **Extras** | — | sparkle, vignette, glitch (optional), sweep, stars, auto-rotate, profiles, randomize |

## نصب (برای کاربر مبتدی)

فایل `dist/termfx-install.sh` رو دانلود کن و اجرا کن:

```sh
sh termfx-install.sh
```

(اول فایل رو ذخیره کن؛ `curl ... | sh` کار نمی‌کنه.)

نصب‌کننده خودش:
1. چیزهای لازم (python3، git، curl، fastfetch، starship، eza، bat، fzf، فونت) رو نصب می‌کنه؛
2. تنظیمات قبلی ترمینالت (oh-my-zsh، p10k، starship، ghostty، kitty و...) رو **به `~/.termfx-backup` منتقل می‌کنه** (چیزی پاک نمی‌شه) و ترمینال رو به حالت پیش‌فرض برمی‌گردونه؛
3. فونت رو فعال و termfx رو نصب می‌کنه.

بعدش یه ترمینال جدید باز کن (حداقل ۸۰×۲۴).

| کار | دستور |
|---|---|
| برگردوندن تنظیمات قبلی | `termfx restore` |
| حذف termfx | `termfx uninstall` |
| انتخاب ظاهر Fastfetch | `termfx fastfetch` (یا `termfx fastfetch list`) |
| بدون سؤال | `sh termfx-install.sh -y` |
| انتخاب تم Starship هنگام نصب | `sh termfx-install.sh --starship-theme cloud-ops` |
| ریست نکن، تنظیمات قبلی بمونه | `--keep-old` |
| کنترل ظاهر | `termfx --help` |

## تنظیم Starship

برای تغییرات مستقیم پرامپت:

```sh
termfx starship list
termfx starship theme list
termfx starship theme developer-forge
termfx starship set right_prompt true
termfx starship set time_format '%H:%M:%S'
termfx starship module on battery
termfx starship preset cloud
```

بیش از ۲۵ کنترل برای چینش، زمان، مسیر، شاخه و وضعیت Git و نمادها وجود دارد. از `termfx starship module list` برای دیدن ماژول‌های زبان‌ها، ابزارها، کانتینرها و سرویس‌های ابری استفاده کن؛ presetهای `minimal`، `developer`، `cloud` و `full` هم مجموعه‌های آماده‌اند. تنظیمات به‌صورت TOML سازگار با گزینه‌های رسمی Starship تولید می‌شوند.

نصب‌کننده هم می‌تواند تم را تعاملی بپرسد یا با `--starship-theme NAME` مستقیم انتخابش کنی. ۱۵ تم با اسم‌هایی مثل `nord-frost`، `rose-pine`، `cloud-ops` و `plain-clean` ساخته می‌شوند؛ فایل‌هایشان در `~/.config/termfx/starship-themes/` قرار می‌گیرد و انتخاب هر کدام، پرامپت فعال را دوباره می‌سازد.

انتخاب یک تم نام‌دار، فایل فعال را حتی اگر قبلاً `prompt_style=custom` بوده بازسازی می‌کند؛ `terminal-match` فایل دستی را حفظ می‌کند. هنگام فعال بودن TermFX، مسیر `STARSHIP_CONFIG` به فایل مدیریت‌شدهٔ TermFX تنظیم می‌شود (نسخهٔ بدون آیکون هم فرم تم را نگه می‌دارد). اگر عمداً `--keep-old` انتخاب شود و p10k یا oh-my-posh باقی بماند، باید فقط یکی از آن پرامپت‌ها را فعال نگه داشت.

## For developers

```
install.sh        thin installer (sources lib/, reads src/)
lib/              ui, packages (distro detect + user-space fallbacks), steps, reset/restore, font
src/              modular engine and CLI launchers, init.zsh/bash, config.default, art/
src/termfx_engine/ system/config, colour, art, info, layout, effects, rendering, command handlers
src/termfx.d/      CLI settings, art and status commands
gen/themes.py     generates starship / fastfetch / ghostty / kitty themes
build.sh          compresses the engine package and builds dist/termfx-install.sh
tests/smoke.sh    installs into a throw-away HOME, checks reset -> restore -> uninstall
```

`make test` builds and runs the smoke test on both forms. Run it inside containers (Ubuntu, Fedora, Arch, Alpine) before releasing; the smoke test uses `--no-packages`, so package installs per distro are **not** covered by it.
