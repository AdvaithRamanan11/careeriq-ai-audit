/**
 * Step 4: get CareerIQ's estimate for every profile.
 *
 * This runs CareerIQ's real code (src/lib/calculations.js) from a checkout pinned
 * at the baseline commit. It does not re-implement the formula, so what gets scored
 * is exactly what the live site computed at that commit.
 *
 * Settings (fixed by the PRD):
 *   calculateSalary: experience "Entry", area "Suburban", region "National"
 *   calculateLoan:   incomeKey "mid2" (family income $48,001-$75,000)
 *
 * Usage (Node 20.10+):
 *   node runners/run_careeriq.mjs [profiles.csv]
 * Env:
 *   CAREERIQ_DIR  path to the CareerIQ checkout (default ../careeriq-baseline)
 */

import { execSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const BASELINE_COMMIT = 'ba51be37645409c929167b56d311d10902cbce98'
const REPO = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const CAREERIQ_DIR = path.resolve(process.env.CAREERIQ_DIR ?? path.join(REPO, '..', 'careeriq-baseline'))

const SETTINGS = { experience: 'Entry', area: 'Suburban', region: 'National', incomeKey: 'mid2' }

// ── Refuse to run against anything but the pinned commit ──────────────────────
const head = execSync(`git -C "${CAREERIQ_DIR}" rev-parse HEAD`).toString().trim()
if (head !== BASELINE_COMMIT) {
  console.error(`CareerIQ checkout is at ${head.slice(0, 7)}, but the study pins ${BASELINE_COMMIT.slice(0, 7)}.`)
  process.exit(1)
}
const dirty = execSync(`git -C "${CAREERIQ_DIR}" status --porcelain`).toString().trim()
if (dirty) {
  console.error('CareerIQ checkout has local changes. Use a clean checkout of the baseline.')
  process.exit(1)
}

const calc = await import(pathToFileURL(path.join(CAREERIQ_DIR, 'src/lib/calculations.js')))
const { MAJORS, EXPERIENCE_MULTIPLIERS } = await import(pathToFileURL(path.join(CAREERIQ_DIR, 'src/data/salaries.js')))
const { colleges } = JSON.parse(fs.readFileSync(path.join(CAREERIQ_DIR, 'src/data/colleges.json'), 'utf8'))

const collegeById = new Map(colleges.map(c => [String(c.id), c]))
const jobById = new Map(MAJORS.flatMap(m => m.jobs.map(j => [j.id, { ...j, majorId: m.id }])))

// ── Minimal CSV reader/writer (RFC 4180 quoting) so no npm packages are needed ─
function parseCsv(text) {
  const rows = []
  let row = [], field = '', i = 0, quoted = false
  while (i < text.length) {
    const ch = text[i]
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { field += '"'; i += 2; continue }
      if (ch === '"') { quoted = false; i++; continue }
      field += ch; i++; continue
    }
    if (ch === '"') { quoted = true; i++; continue }
    if (ch === ',') { row.push(field); field = ''; i++; continue }
    if (ch === '\r') { i++; continue }
    if (ch === '\n') { row.push(field); rows.push(row); row = []; field = ''; i++; continue }
    field += ch; i++
  }
  if (field !== '' || row.length) { row.push(field); rows.push(row) }
  const [header, ...body] = rows
  return body.map(r => Object.fromEntries(header.map((h, k) => [h, r[k]])))
}
const csvCell = v => {
  const s = v == null ? '' : String(v)
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

// ── Run ───────────────────────────────────────────────────────────────────────
const processed = path.join(REPO, 'data', 'processed')
let input = process.argv[2]
if (!input) {
  input = fs.existsSync(path.join(processed, 'profiles.csv'))
    ? path.join(processed, 'profiles.csv')
    : path.join(processed, 'profiles_DRAFT.csv')
}
const isDraft = path.basename(input).includes('DRAFT')
const profiles = parseCsv(fs.readFileSync(input, 'utf8'))

const out = []
for (const p of profiles) {
  const college = collegeById.get(p.UNITID)
  const job = jobById.get(p.job_id)
  if (!college) throw new Error(`${p.profile_id}: UNITID ${p.UNITID} not in colleges.json`)
  if (!job) throw new Error(`${p.profile_id}: job ${p.job_id} not in MAJORS`)

  const salary = calc.calculateSalary({ college, job, area: SETTINGS.area, experience: SETTINGS.experience, region: SETTINGS.region })
  const loan = calc.calculateLoan({ college, incomeKey: SETTINGS.incomeKey })

  out.push({
    profile_id: p.profile_id,
    UNITID: p.UNITID,
    job_id: p.job_id,
    ciq_salary: salary,
    ciq_debt: loan.totalLoan4Year,          // full net price x program years (assumes every dollar is borrowed)
    ciq_monthly_payment: loan.monthlyPayment,
    // components, so every estimate can be checked by hand
    bls_base: job.blsBase,
    earnings_multiplier: college.earningsMultiplier,
    area_multiplier: calc.resolveAreaMultiplier(SETTINGS.area, SETTINGS.region),
    experience_multiplier: EXPERIENCE_MULTIPLIERS[SETTINGS.experience],
    net_price_per_year: loan.netPricePerYear,
    program_years: loan.programYears,
    careeriq_commit: BASELINE_COMMIT.slice(0, 7),
    settings: `${SETTINGS.experience}/${SETTINGS.area}/${SETTINGS.region}/${SETTINGS.incomeKey}`,
  })
}

const outPath = path.join(processed, isDraft ? 'careeriq_estimates_DRAFT.csv' : 'careeriq_estimates.csv')
const header = Object.keys(out[0])
fs.writeFileSync(outPath, [header.join(','), ...out.map(r => header.map(h => csvCell(r[h])).join(','))].join('\n') + '\n')
console.log(`Node ${process.version}. CareerIQ at ${head.slice(0, 7)}.`)
console.log(`Scored ${out.length} profiles from ${path.basename(input)} -> ${path.relative(REPO, outPath)}`)
