# Quantum and AI Briefing

Every morning at 6:00 AM Eastern, this repository gathers the day's quantum and AI news,
writes a plain-language summary of each item with why it matters for leaders, picks the
most attractive items, and writes a ready-to-post Substack Note for each one, ending with
the citation and link. Every other Friday it also runs a research roundup of new papers.
The results appear on a web page you can open in any browser.

## One-time setup, about 30 minutes

### 1. Create the repository
1. Sign in at github.com (create a free account if needed).
2. Click **New repository**. Name it `quantum-briefing`. Choose **Public**.
   GitHub Pages is free for public repositories.
3. Click **Create repository**.

### 2. Upload the files
1. On the new repository page, click **uploading an existing file**.
2. Drag in the `docs` and `scripts` folders and this README. Click **Commit changes**.
3. The `.github` folder is hidden on most computers, so create the workflow by hand:
   click **Add file**, then **Create new file**, type the name
   `.github/workflows/briefing.yml`, paste the contents of that file from this folder,
   and click **Commit changes**.

### 3. Add your Claude API key
1. Go to console.anthropic.com, sign in, add a payment method and a small credit
   balance, then create an API key under **API keys**. Copy it.
2. In the repository: **Settings**, then **Secrets and variables**, then **Actions**,
   then **New repository secret**. Name: `ANTHROPIC_API_KEY`. Value: the key. Save.

### 4. Let the job save its results
**Settings**, then **Actions**, then **General**. Under **Workflow permissions**,
choose **Read and write permissions**. Save.

### 5. Turn on the web page
**Settings**, then **Pages**. Under **Build and deployment**, choose
**Deploy from a branch**, branch `main`, folder `/docs`. Save.
After a minute the page is live at:
`https://YOUR-GITHUB-USERNAME.github.io/quantum-briefing/`

### 6. Run it once to test
**Actions** tab, then **Daily briefing**, then **Run workflow**. Tick
**Also run the research roundup now** if you want both. It takes 2 to 5 minutes.
Refresh the web page afterwards.

### 7. Open it at startup
In Chrome: **Settings**, **On startup**, **Open a specific page or set of pages**,
add the page address from step 5.

## Optional: keep the Notion database in sync
If you also want new findings added to the Notion database used by the Claude desk:
1. Go to notion.so/profile/integrations, create an internal integration, copy its token.
2. Open the **Quantum and AI Daily Findings** database in Notion, click the menu,
   **Connections**, and add the integration.
3. Add two more repository secrets: `NOTION_TOKEN` (the token) and
   `NOTION_DATABASE_ID` with the value `c11a5b9a5b634a64aed744c1b0f98c97`.

## Good to know
- **Cost:** Claude API usage is billed to your Anthropic account, separate from a
  Claude subscription. At one run a day with up to 15 web searches, expect a few
  dollars to the low teens per month. Set a monthly spend limit in the console.
- **The page is public.** Anyone with the address can see it, including the draft
  Notes before they are posted. Nothing else about you is on it.
- **Timing:** GitHub runs scheduled jobs close to, not exactly at, the set time.
  In winter the 10:00 UTC schedule lands at 5:00 AM Eastern.
- **Changing things:** the search areas, rules, and Note style live near the top of
  `scripts/run.py`. The research schedule anchor is `ROUNDUP_ANCHOR`.
