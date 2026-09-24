# 🌿 Sera — Photo Card Generator for Dar Al-Nasaem

A lightweight Flask web app that drops a user's photo into a beautifully designed template alongside custom Arabic (or English) text — perfect for producing branded photo cards quickly and consistently.

This project was built for **Dar Al-Nasaem for Publishing and Distribution (دار النسائم للنشر والتوزيع)** to make it easy to generate polished, on-brand photo cards without touching Photoshop — one at a time, or hundreds at once.

---

## ✨ What it does

Upload a photo and a line (or a few lines) of text, and the app places your photo neatly inside a rounded frame on one side of the template, and renders your text — properly shaped and right-to-left for Arabic — on the other side. The output is a clean, transparent-background PNG ready to use.

**Key features:**

- 🖼️ **Simple mode** — upload one photo + text, get one card instantly.
- ⚙️ **Admin/settings panel** — visually fine-tune the photo box and text box (position, size, colors, fonts, alignment) with a live preview, no code required.
- 📦 **Batch mode** — upload a whole folder of photos plus an Excel/CSV file mapping filenames to text, and generate the entire batch in one click.
- 🔤 **Arabic-aware text engine** — correct Arabic letter shaping/joining and right-to-left rendering (via `arabic-reshaper` + `python-bidi`), with automatic font fallback so no character ever renders as a blank box.
- 📐 **Auto-fit text** — text automatically shrinks to fit its box if it's too long, and wraps intelligently across multiple lines.
- 🎨 **Multiple font choices** — several Arabic and Latin fonts bundled in, switchable from the settings panel.

---

## 📁 Project structure

```
SeraAppProgram/
├── app.py                 # Flask routes (web server + API)
├── imaging.py              # Core image-generation engine
├── batch.py                 # Batch processing + Excel template builder
├── config.py                # Loads/saves settings to config.json
├── config.json              # Your saved default layout settings
├── requirements.txt          # Python dependencies
├── static/
│   ├── template/            # The base design template (photo frame + card art)
│   ├── fonts/                # Bundled font files
│   ├── outputs/               # (working folder)
│   └── style.css
└── templates/
    ├── simple.html           # The main "quick generate" page
    ├── admin.html             # The visual settings/admin page
    └── batch.html             # The batch-upload page
```

---

## 🚀 Getting started

### 1. Requirements

- Python 3.9 or newer
- The packages listed in `requirements.txt`: `flask`, `pillow`, `arabic-reshaper`, `python-bidi`, `fonttools`, `openpyxl`

### 2. Install

Open a terminal in the project folder and run:

```bash
pip install -r requirements.txt
```

*(Tip: it's good practice to do this inside a virtual environment — `python -m venv venv` then activate it — but it's not required.)*

### 3. Run the app

```bash
python app.py
```

Then open your browser to:

```
http://127.0.0.1:5000
```

That's it — the app is running locally on your own computer.

---

## 🧭 How to use it

### Quick generate (`/`)

This is the home page. Just:

1. Choose a photo from your device.
2. Type your text in the box (Arabic or English both work).
3. Click **Generate** — a finished PNG card is created and ready to download.

This page always uses whatever settings are currently saved (see the Admin panel below) — so once you've dialed in the perfect layout, every quick card automatically follows it.

### Admin panel — customizing the layout (`/admin`)

This is where you control *exactly* how the photo and text are placed on the card, with a live preview so you can see your changes before saving them. You can adjust:

**Photo box settings:**
| Setting | What it controls |
|---|---|
| X / Y | Position of the photo box on the canvas |
| Width / Height | Size of the photo box |
| Border width | Thickness of the colored border around the photo |
| Border color | Color of that border (hex color, e.g. `#8FA28A`) |
| Corner radius | How rounded the photo's corners are |
| Fit mode | `cover` (fills the box, cropping overflow) or `contain` (fits the whole photo inside, padding empty space with the background color) |
| Background color | Fill color used behind the photo in `contain` mode |

**Text box settings:**
| Setting | What it controls |
|---|---|
| X / Y | Position of the text area |
| Width / Height | Size of the text area (text wraps and shrinks to stay inside this box) |
| Font | Choose from the bundled font list |
| Font size | Starting font size (it will automatically shrink if the text is too long to fit) |
| Color | Text color (hex color, e.g. `#17433F`) |
| Align | Horizontal alignment: left / center / right |
| V-align | Vertical alignment: top / middle / bottom |
| Line spacing | Space between lines, as a multiplier (e.g. `1.25`) |

**Workflow:**
1. Adjust any settings you like.
2. Upload a sample photo and type sample text.
3. Click **Preview** to see the result instantly, without saving anything.
4. Happy with it? Click **Save** — from now on, every card generated anywhere in the app (quick mode *and* batch mode) will use this layout.
5. Want to start over? Click **Reset to defaults** to restore the original layout.

> 💡 All coordinates are in pixels, based on a canvas size of **1024 × 512 px** — the same size as the template artwork.

### Batch mode — generating many cards at once (`/batch`)

Perfect for producing a large set of cards in one go — for example, an entire course or collection of names.

**Step by step:**

1. Go to the **Batch** page and click **Download template** to get a starter Excel file (`نموذج_الكلمات.xlsx`).
2. Fill it in with two columns:
   - **Column A** — the *filename* of each photo (without needing the extension, e.g. `Q004S002`).
   - **Column B** — the *text* that should appear on that photo's card.
3. Save the file (Excel `.xlsx` or `.csv` both work).
4. On the Batch page, upload:
   - Your filled-in Excel/CSV file.
   - All the corresponding photo files (select multiple at once).
5. Click **Run batch**.

The app matches each photo to its row in the spreadsheet by filename, generates every card using your currently saved Admin settings, and saves the finished PNGs into a new, timestamped folder inside your **Downloads** folder (e.g. `نتائج_المجموعة_20260925_143000`).

You'll get a summary report showing:
- ✅ How many cards were generated successfully.
- ⚠️ Any photos that had no matching text row.
- ⚠️ Any text rows that had no matching photo.

---

## 🎨 Fonts included

The app ships with several fonts you can pick from in the Admin panel, including:

- Calibri (Regular & Bold) — default
- Tahoma (Regular & Bold)
- Cairo (Regular & Bold) — modern Arabic
- Almarai (Regular & Bold) — modern Arabic
- Amiri (Regular & Bold) — classic Arabic
- Arial (Regular & Bold)
- Dubai & Baloo Bhaijaan 2 — best for English/Latin text

If a chosen font is missing a particular character, the app automatically fills the gap using a fallback font so nothing ever appears as a broken/empty box.

---

## 🛠️ Troubleshooting

- **"File too large" error** — uploads are capped at 500 MB total per request. Split a very large batch into smaller groups if you hit this.
- **Text looks cut off or too small** — increase the text box's width/height in the Admin panel, or check that "Font size" isn't set too conservatively.
- **A photo isn't matched in batch mode** — make sure the photo's filename (minus extension) matches Column A in your spreadsheet *exactly* (matching ignores capitalization but not spelling).
- **App won't start** — double check you ran `pip install -r requirements.txt` and that you're using Python 3.9+.

---

## 📌 Notes

- All generated images are exported as PNG with a transparent background outside the card artwork, so they drop cleanly onto any background.
- Settings are saved to `config.json` in the project folder — back this file up if you want to preserve a custom layout.
- This tool runs entirely locally; no images or text are sent anywhere outside your own machine.

---

*Built for Dar Al-Nasaem for Publishing and Distribution (دار النسائم للنشر والتوزيع) 🌿*