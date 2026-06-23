# Rich Menu — Update Guide

The rich menu image is bundled in `app/assets/rich-menu.jpg` and auto-created at startup.

---

## How to update the image

### Step 1 — Replace the image locally

Replace `app/assets/rich-menu.jpg` with the new image.

Requirements (LINE limits):
- Format: **JPEG** (not PNG — PNG often exceeds 1 MB limit)
- Size: **under 1 MB**
- Dimensions: **2500 × 843 px**

To convert a PNG on macOS:
```bash
sips -s format jpeg -s formatOptions 85 /path/to/new-image.png --out app/assets/rich-menu.jpg
```

### Step 2 — Push to GitHub

```bash
git add app/assets/rich-menu.jpg
git commit -m "update rich menu image"
git push origin master
```

Wait for Railway to finish deploying (the new image is now in the container).

### Step 3 — Recreate the rich menu via Railway Console

Go to Railway → **nail-bot** → **Console** tab and run:

```
python3 -c "import os,httpx;from pathlib import Path;token=os.environ['LINE_CHANNEL_ACCESS_TOKEN'];liff=os.environ['LIFF_ID'];h={'Authorization':'Bearer '+token};[httpx.delete(f'https://api.line.me/v2/bot/richmenu/{m[\"richMenuId\"]}',headers=h) for m in httpx.get('https://api.line.me/v2/bot/richmenu/list',headers=h).json().get('richmenus',[]) if m.get('name')=='Hualienvibe Main Menu'];body={'size':{'width':2500,'height':843},'selected':True,'name':'Hualienvibe Main Menu','chatBarText':'選單','areas':[{'bounds':{'x':0,'y':0,'width':833,'height':843},'action':{'type':'uri','label':'預約','uri':'https://liff.line.me/'+liff}},{'bounds':{'x':833,'y':0,'width':834,'height':843},'action':{'type':'message','label':'作品集','text':'作品集'}},{'bounds':{'x':1667,'y':0,'width':833,'height':843},'action':{'type':'message','label':'聯絡我們','text':'聯絡我們'}}]};rid=httpx.post('https://api.line.me/v2/bot/richmenu',json=body,headers=h).json()['richMenuId'];httpx.post(f'https://api-data.line.me/v2/bot/richmenu/{rid}/content',content=Path('/app/app/assets/rich-menu.jpg').read_bytes(),headers={**h,'Content-Type':'image/jpeg'});httpx.post(f'https://api.line.me/v2/bot/user/all/richmenu/{rid}',headers=h);print('New RICH_MENU_ID:',rid)"
```

This will:
- Delete the old "Hualienvibe Main Menu" from LINE
- Create a new menu with the new image
- Set it as default for all users
- Print the new `richMenuId`

### Step 4 — Update Railway variable

Copy the printed `richmenu-XXXXXXXX` value and update `RICH_MENU_ID` in Railway → **Variables**.

---

## How it works at startup

On every deploy, `_ensure_rich_menu()` in `app/main.py` runs:

1. If `RICH_MENU_ID` env var is set and valid → calls `set_default_rich_menu` (fast path, no image upload)
2. If `RICH_MENU_ID` is invalid (400) → falls through
3. Looks for existing menu named "Hualienvibe Main Menu" → reuses it if image is uploaded
4. If existing menu has no image → deletes it and creates fresh from `app/assets/rich-menu.jpg`
5. Logs the new ID: `INFO:root:rich menu created: richmenu-XXXX — set RICH_MENU_ID=...`

New followers also get the menu linked automatically via the follow-event handler in `app/event_router.py`.
