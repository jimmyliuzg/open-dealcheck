# OpenDealCheck — Implementation Plan

> Open-source alternative to dealcheck.io: real estate investment property analysis software.

**Goal:** Build a self-hosted, open-source platform that replicates dealcheck.io's core property analysis, projections, comps, and reporting capabilities — starting with a focused CLI/web MVP and expanding to full feature parity.

**Architecture:** Next.js (React) web app + Python FastAPI backend. PostgreSQL for data persistence. RentCast API for US property data (140M+ records). Local-first option with SQLite for offline use.

**Tech Stack:**
- Frontend: Next.js 14+ (App Router), TypeScript, Tailwind CSS, shadcn/ui
- Backend: Python 3.12+ FastAPI, SQLAlchemy, Alembic
- Database: PostgreSQL (production) / SQLite (local-first mode)
- Data: RentCast API (property records, AVM, comps, listings, market data)
- Auth: NextAuth.js (email/password, Google, GitHub OAuth)
- PDF: React-PDF or Puppeteer for report generation
- Mobile: React Native (Phase 5+)

---

## Scope Summary (from dealcheck.io analysis)

### Property Types Supported
1. Rental Properties (buy & hold, rehab & hold, house hacks)
2. BRRRR (Buy, Rehab, Rent, Refinance, Repeat)
3. Flips & Rehab Projects
4. Multi-Family & Commercial (5+ units, mixed-use)
5. Airbnb / Short-Term Rentals
6. Wholesale Deals

### Core Feature Matrix

| Feature | dealcheck.io | OpenDealCheck Target |
|---------|-------------|---------------------|
| Property data import (public records) | ✅ RentCast | ✅ RentCast API |
| Deal customization (financing, costs, rehab) | ✅ | ✅ |
| Cash flow analysis | ✅ | ✅ |
| Cap rate, COC, ROI, IRR, DCR, etc. | ✅ 15+ metrics | ✅ |
| Long-term cash flow projections | ✅ | ✅ |
| Flip profit projections | ✅ | ✅ |
| BRRRR analysis (refi modeling) | ✅ | ✅ |
| Multi-unit rent roll + per-unit metrics | ✅ | ✅ |
| Short-term rental (Airbnb) analysis | ✅ | ✅ |
| Wholesale deal analysis | ✅ | ✅ |
| Sales comps (ARV estimation) | ✅ | ✅ |
| Rental comps (rent estimation) | ✅ | ✅ |
| Purchase criteria screening | ✅ | ✅ Phase 3 |
| Max Allowable Offer calculator | ✅ | ✅ Phase 3 |
| Property owner lookup | ✅ | ✅ Phase 4 |
| PDF/online reports with branding | ✅ | ✅ Phase 3 |
| Side-by-side property comparison | ✅ | ✅ Phase 3 |
| Creative financing scenarios | ✅ | ✅ Phase 2 |
| CSV/Excel export | ✅ | ✅ Phase 2 |
| Lender directory | ✅ | ✅ Phase 4 |
| Real estate glossary | ✅ | ✅ Phase 4 |
| Cloud sync / multi-device | ✅ | ✅ Phase 4 |
| Mobile apps (iOS/Android) | ✅ | ❌ Phase 6 (stretch) |

### Pricing Model (dealcheck.io)
- Free: 15 properties, 5 photos, 5 comps, 5 templates
- Plus ($10/mo): 50 properties, 15 photos, 10 comps, 10 templates
- Pro ($20/mo): Unlimited everything

**OpenDealCheck advantage:** Self-hosted, no property limits, no subscription. Users bring their own RentCast API key (free tier: 50 calls/mo).

---

## Data Model

### Core Entities

```
User
├── id, email, name, password_hash, avatar_url
├── settings: { default_vacancy_rate, default_mgmt_fee, ... }
└── subscription_tier: free | plus | pro (for hosted version)

Property
├── id, user_id, address, city, state, zip, county
├── property_type: single_family | multi_family | condo | commercial | land
├── bedrooms, bathrooms, square_footage, lot_size, year_built
├── zoning, parking, hoa_fee, features (JSON)
├── rentcast_id (FK to cached RentCast data)
├── photos: [{ url, caption, order }]
├── created_at, updated_at

PropertyAnalysis
├── id, property_id, user_id, analysis_type
│   (rental | brrrr | flip | multifamily | airbnb | wholesale)
├── purchase_price, arv, rehab_cost
├── financing: { loan_type, rate, term, down_payment_pct, ... }
├── closing_costs: { items: [{ name, amount, is_financed }] }
├── rehab_budget: { items: [{ category, description, cost }] }
├── operating_expenses: { tax, insurance, mgmt, maintenance, reserves, ... }
├── rental_income: { monthly_rent, other_income, vacancy_rate }
├── airbnb_settings: { nightly_rate, occupancy, cleaning_fee, ... }
├── projections_config: { appreciation_rate, income_growth, expense_growth, hold_years }
├── created_at, updated_at

PropertyAnalysisMetric (computed, cached)
├── id, analysis_id
├── noi, cash_flow_monthly, cash_flow_annual
├── cap_rate, coc_return, roi, roe, irr
├── grm, ber, dcr, debt_yield, equity_multiple
├── rent_to_value, price_per_sqft, arv_per_sqft
├── total_cash_needed, loan_amount, ltv, ltc
├── break_even_ratio
├── computed_at

Projection (year-by-year)
├── id, analysis_id, year
├── property_value, loan_balance, equity
├── gross_rent, vacancy, operating_income
├── operating_expenses, noi, loan_payment, cash_flow
├── tax_benefits, depreciation, cumulative_cash_flow
├── total_profit, sale_proceeds

Comp
├── id, subject_property_id, analysis_id
├── comp_type: sale | rental
├── address, city, state, zip
├── property_type, bedrooms, bathrooms, sqft
├── sale_price_or_rent, sale_date_or_listed_date
├── distance_miles, similarity_score
├── price_per_sqft, rent_per_sqft
├── rentcast_id

PurchaseCriteria
├── id, user_id, name
├── max_price, min_cap_rate, min_coc, min_roi
├── min_rent_to_value, max_vacancy, property_types
├── min_bedrooms, max_bedrooms, min_sqft, max_sqft
├── states, cities, zip_codes
├── custom_rules (JSON)

Report
├── id, analysis_id, user_id
├── report_type: interactive | pdf
├── branding: { logo_url, company_name, contact_info, website }
├── shared_url (slug for public sharing)
├── generated_at

Template
├── id, user_id, name, analysis_type
├── defaults: (JSON blob of pre-filled analysis fields)
├── is_public
```

---

## Phased Implementation

### Phase 1: Foundation (Weeks 1-3)
**Goal:** Working MVP — search a property, run basic rental analysis, see results.

#### Task 1.1: Project Scaffolding
- Next.js 14 app with App Router, TypeScript, Tailwind, shadcn/ui
- Python FastAPI backend with SQLAlchemy + Alembic
- Docker Compose for local dev (postgres, backend, frontend)
- CI: GitHub Actions (lint, type-check, test)

**Files:**
- `docker-compose.yml`
- `frontend/` (Next.js)
- `backend/` (FastAPI)
- `Makefile` (dev commands)

#### Task 1.2: Database Schema + Migrations
- Users table (NextAuth.js adapter pattern)
- Properties table
- PropertyAnalyses table
- PropertyAnalysisMetrics table
- Initial Alembic migration

**Files:**
- `backend/models/` (SQLAlchemy models)
- `backend/alembic/versions/001_initial.py`

#### Task 1.3: RentCast API Integration
- Backend service wrapping RentCast API calls
- Property search by address
- Property record retrieval
- Value estimate (AVM) + sales comps
- Rent estimate + rental comps
- Response caching (PostgreSQL, 24h TTL)
- Rate limiting (respect free tier: 50 calls/mo)

**Files:**
- `backend/services/rentcast.py`
- `backend/api/properties.py`
- `backend/api/comps.py`
- `backend/models/rentcast_cache.py`

#### Task 1.4: Auth System
- NextAuth.js with email/password + Google OAuth
- Session management (JWT)
- Protected API routes
- User settings endpoint

**Files:**
- `frontend/lib/auth.ts`
- `backend/api/auth.py`
- `backend/models/user.py`

#### Task 1.5: Property Search UI
- Address autocomplete (debounced RentCast search)
- Property card with key details (type, beds, baths, sqft, price)
- "Add Property" flow → creates Property + opens analysis wizard

**Files:**
- `frontend/app/page.tsx` (dashboard/search)
- `frontend/components/PropertySearch.tsx`
- `frontend/components/PropertyCard.tsx`

#### Task 1.6: Rental Analysis Engine (Core Math)
This is the heart of the app. Implement ALL calculation logic as pure functions (no UI dependency) with comprehensive tests.

**Calculations:**
- Purchase analysis: total cash needed, loan amount, LTV, LTC
- Operating expenses breakdown (tax, insurance, mgmt, maintenance, reserves, HOA)
- Cash flow: gross rent → vacancy → operating income → NOI → cash flow
- Return metrics: cap rate, COC, ROI, ROE, IRR, GRM, BER, DCR, debt yield, equity multiple
- Rent-to-value ratio, price per sqft

**Files:**
- `backend/services/calculations/rental.py`
- `backend/services/calculations/metrics.py`
- `backend/services/calculations/utils.py`
- `backend/tests/test_rental_calculations.py`

#### Task 1.7: Cash Flow Projections Engine
Year-by-year projections for buy & hold:
- Property value appreciation
- Rent income growth
- Expense growth
- Loan amortization schedule
- Equity accumulation
- Tax benefits (depreciation, interest deductions)
- Sale analysis (selling costs, net proceeds)
- Cumulative returns at each year (1, 2, 3, 5, 10, 20, 30)

**Files:**
- `backend/services/calculations/projections.py`
- `backend/tests/test_projections.py`

#### Task 1.8: Analysis Input Wizard UI
Step-by-step wizard:
1. Property overview (pre-filled from RentCast)
2. Purchase & rehab costs
3. Financing structure
4. Operating expenses
5. Rental income assumptions
6. View results

**Files:**
- `frontend/app/properties/[id]/analysis/new/page.tsx`
- `frontend/components/AnalysisWizard.tsx`
- `frontend/components/wizard/` (step components)

#### Task 1.9: Results Dashboard UI
- Summary cards (cap rate, COC, cash flow, etc.)
- Cash flow breakdown table
- Year-by-year projections table
- Chart.js visualizations (cash flow over time, equity growth)

**Files:**
- `frontend/app/properties/[id]/analysis/[analysisId]/page.tsx`
- `frontend/components/AnalysisResults.tsx`
- `frontend/components/charts/` (chart components)

#### Task 1.10: Property Management
- List saved properties (dashboard)
- Property detail page
- Multiple analyses per property
- Delete property/analysis

**Files:**
- `frontend/app/properties/page.tsx`
- `frontend/app/properties/[id]/page.tsx`

---

### Phase 2: Analysis Depth (Weeks 4-6)
**Goal:** Support all analysis types (BRRRR, flip, multifamily, Airbnb, wholesale) + export.

#### Task 2.1: Flip Analysis Engine
- Buy → rehab → sell model
- Rehab cost tracking (line items by category)
- Holding costs (loan payments during rehab period)
- Profit calculation: ARV - purchase - rehab - holding - selling costs
- ROI for flips (different formula than rental)
- Flip projections (timeline-based, not year-based)

**Files:**
- `backend/services/calculations/flip.py`
- `backend/tests/test_flip_calculations.py`

#### Task 2.2: BRRRR Analysis Engine
- Buy → rehab → rent → refinance → repeat model
- Refinance modeling (new loan based on ARV)
- "BRRRR score" (actual cash left in deal after refi)
- Repeat cycle visualization
- Comparison: BRRRR vs. standard rental

**Files:**
- `backend/services/calculations/brrrr.py`
- `backend/tests/test_brrrr_calculations.py`

#### Task 2.3: Multi-Family Analysis Engine
- Rent roll management (per-unit rent entry)
- Per-unit analysis metrics
- Vacancy by unit
- Commercial loan modeling
- Cap rate emphasis (primary metric for commercial)

**Files:**
- `backend/services/calculations/multifamily.py`
- `backend/tests/test_multifamily_calculations.py`

#### Task 2.4: Short-Term Rental (Airbnb) Analysis
- Nightly rate + dynamic occupancy modeling
- Cleaning fees, management fees (higher % for STR)
- Seasonal income variation
- Platform fees (Airbnb/VRBO host fees)
- Comparison: STR vs. long-term rental

**Files:**
- `backend/services/calculations/airbnb.py`
- `backend/tests/test_airbnb_calculations.py`

#### Task 2.5: Wholesale Deal Analysis
- Assignment fee modeling
- End buyer MAO calculation
- Marketing cost tracking
- Quick-pass/fail screening

**Files:**
- `backend/services/calculations/wholesale.py`
- `backend/tests/test_wholesale_calculations.py`

#### Task 2.6: Creative Financing Scenarios
- Owner financing (seller carry)
- Lease options
- Subject-to existing financing
- Hard money / private money
- Portfolio / DSCR loans
- Interest-only periods
- balloon payments

**Files:**
- `backend/services/calculations/financing.py`
- `backend/tests/test_financing.py`

#### Task 2.7: Analysis Type Selector UI
- Updated wizard that branches by analysis type
- Type-specific input forms
- Type-specific results views

**Files:**
- `frontend/components/AnalysisTypeSelector.tsx`
- `frontend/components/wizard/FlipSteps.tsx`
- `frontend/components/wizard/BrrrrSteps.tsx`
- `frontend/components/wizard/MultifamilySteps.tsx`
- `frontend/components/wizard/AirbnbSteps.tsx`

#### Task 2.8: CSV/Excel Export
- Export property data
- Export analysis results
- Export projections table
- Export comps data
- Use openpyxl for Excel, standard CSV otherwise

**Files:**
- `backend/api/export.py`
- `backend/services/export.py`

#### Task 2.9: Property Templates
- Save analysis as template
- Apply template to new property
- Pre-filled defaults (vacancy rate, expense ratios, etc.)
- Community templates (shared)

**Files:**
- `backend/api/templates.py`
- `frontend/components/TemplateManager.tsx`

---

### Phase 3: Power Features (Weeks 7-10)
**Goal:** Comps viewer, reports, screening, comparison — the features that make it a "platform."

#### Task 3.1: Sales Comps Viewer
- Display sales comps from RentCast AVM
- Similarity scoring visualization
- Price/sqft comparison
- ARV estimation from comps
- Map view (Leaflet/Mapbox)

**Files:**
- `frontend/components/CompsViewer.tsx`
- `frontend/components/CompsMap.tsx`
- `backend/api/comps.py` (enhanced)

#### Task 3.2: Rental Comps Viewer
- Display rental comps from RentCast
- Rent/sqft analysis
- Rent estimation from comps
- Market rent range visualization

**Files:**
- `frontend/components/RentalCompsViewer.tsx`

#### Task 3.3: Purchase Criteria Screening
- Define investment criteria (min cap rate, max price, etc.)
- Bulk screen properties against criteria
- Pass/fail/warning indicators
- Filter and sort by metrics

**Files:**
- `backend/api/criteria.py`
- `backend/services/screening.py`
- `frontend/components/CriteriaBuilder.tsx`
- `frontend/components/ScreeningResults.tsx`

#### Task 3.4: Max Allowable Offer (MAO) Calculator
- Reverse valuation from desired returns
- 70% rule calculator
- Custom MAO rules (12+ criteria)
- Quick calculator sidebar

**Files:**
- `backend/services/calculations/mao.py`
- `frontend/components/MaoCalculator.tsx`

#### Task 3.5: Side-by-Side Property Comparison
- Select 2-4 properties
- Comparison table (all metrics)
- Radar chart visualization
- Highlight best-in-class per metric

**Files:**
- `frontend/app/compare/page.tsx`
- `frontend/components/ComparisonTable.tsx`
- `frontend/components/ComparisonChart.tsx`

#### Task 3.6: Professional Reports
- Interactive online reports (shareable URL)
- PDF export (React-PDF or Puppeteer)
- Custom branding (logo, company name, contact info)
- Report sections: overview, analysis, projections, comps, photos
- Public sharing via slug URL

**Files:**
- `backend/api/reports.py`
- `backend/services/report_generator.py`
- `frontend/app/reports/[slug]/page.tsx`
- `frontend/components/ReportBranding.tsx`
- `frontend/lib/pdf-generator.ts`

#### Task 3.7: Property Photo Management
- Upload photos (local storage or S3-compatible)
- Photo gallery on property detail
- Include in reports

**Files:**
- `backend/api/photos.py`
- `frontend/components/PhotoGallery.tsx`

---

### Phase 4: Polish & Ecosystem (Weeks 11-14)
**Goal:** Owner lookup, lender directory, glossary, cloud sync, UX polish.

#### Task 4.1: Property Owner Lookup
- Use RentCast owner data endpoint
- Display owner name, mailing address
- Owner-occupied indicator
- Export for direct mail campaigns

**Files:**
- `frontend/components/OwnerInfo.tsx`
- `backend/services/rentcast.py` (owner endpoint)

#### Task 4.2: Lender Directory
- Curated list of investor-friendly lenders
- Filter by type (conventional, hard money, private, commercial)
- Filter by state/region
- Community-contributed entries

**Files:**
- `backend/api/lenders.py`
- `backend/models/lender.py`
- `frontend/app/lenders/page.tsx`

#### Task 4.3: Real Estate Glossary
- Interactive glossary with definitions
- Formula explanations for each metric
- Searchable, categorized
- Linked from metric tooltips in analysis results

**Files:**
- `backend/api/glossary.py`
- `backend/data/glossary.json`
- `frontend/app/glossary/page.tsx`
- `frontend/components/MetricTooltip.tsx`

#### Task 4.4: Data Sync & Import/Export
- JSON export/import of all user data
- Backup/restore functionality
- Optional cloud sync (for hosted version)

**Files:**
- `backend/api/sync.py`
- `frontend/components/Settings/DataManagement.tsx`

#### Task 4.5: Dashboard & UX Polish
- Dashboard with portfolio overview
- Total portfolio value, cash flow, equity
- Recent activity feed
- Quick-analyze from dashboard
- Responsive design (mobile-friendly)
- Dark mode

**Files:**
- `frontend/app/dashboard/page.tsx`
- `frontend/components/PortfolioSummary.tsx`
- `frontend/components/ActivityFeed.tsx`

#### Task 4.6: Settings & Preferences
- Default analysis parameters
- Currency/locale settings
- Notification preferences
- Account management

**Files:**
- `frontend/app/settings/page.tsx`
- `backend/api/user-settings.py`

#### Task 4.7: Documentation
- README with setup instructions
- API documentation (FastAPI auto-generated)
- User guide (how to analyze properties)
- Contributing guide
- License selection (MIT or AGPL)

**Files:**
- `README.md`
- `docs/`
- `CONTRIBUTING.md`
- `LICENSE`

---

### Phase 5: Advanced (Weeks 15-20, stretch goals)
- Market data dashboards (zip code trends)
- Portfolio analytics (aggregate returns)
- Automated deal alerts (criteria-based notifications)
- API for third-party integrations
- Webhook support
- Multi-currency support

### Phase 6: Mobile (Month 6+, major stretch)
- React Native app
- Camera integration for property photos
- Offline analysis capability
- Push notifications for deal alerts

---

## Open-Source Strategy

### Name: OpenDealCheck
### License: AGPL-3.0 (prevents SaaS competitors from forking without contributing back)
### Repo: github.com/open-dealcheck/open-dealcheck

### Differentiators from dealcheck.io:
1. **Self-hosted** — no subscription, no data sharing
2. **Open source** — inspect, modify, contribute
3. **Unlimited properties** — no artificial limits
4. **Own your data** — export everything, no vendor lock-in
5. **Community-driven** — shared templates, lender directory, glossary
6. **API-first** — programmatic access to all features
7. **Multi-data-source** — not locked to RentCast (extensible)

### Revenue Model (if hosted version is offered):
- Free: self-hosted (unlimited)
- Hosted Free: 15 properties (RentCast free tier)
- Hosted Pro: $8/mo (unlimited + priority support)
- This undercuts dealcheck.io significantly

---

## Dependency Graph

```
Phase 1 (Foundation)
├── 1.1 Scaffolding ─────────────────────────────┐
├── 1.2 Database Schema ──────────────────────────┤
├── 1.3 RentCast API ─────────────────────────────┤
├── 1.4 Auth System ──────────────────────────────┤
├── 1.5 Property Search UI ───────────────────────┤
├── 1.6 Rental Analysis Engine ───────────────────┤
├── 1.7 Cash Flow Projections ────────────────────┤
├── 1.8 Analysis Wizard UI ───────────────────────┤
├── 1.9 Results Dashboard UI ─────────────────────┤
└── 1.10 Property Management ─────────────────────┘
                                                      │
Phase 2 (Analysis Depth) ◄────────────────────────────┘
├── 2.1 Flip Analysis ─────────────────────────────┐
├── 2.2 BRRRR Analysis ────────────────────────────┤
├── 2.3 Multi-Family Analysis ─────────────────────┤
├── 2.4 Airbnb/STR Analysis ───────────────────────┤
├── 2.5 Wholesale Analysis ────────────────────────┤
├── 2.6 Creative Financing ────────────────────────┤
├── 2.7 Analysis Type Selector UI ─────────────────┤
├── 2.8 CSV/Excel Export ──────────────────────────┤
└── 2.9 Property Templates ────────────────────────┘
                                                      │
Phase 3 (Power Features) ◄───────────────────────────┘
├── 3.1 Sales Comps Viewer ────────────────────────┐
├── 3.2 Rental Comps Viewer ───────────────────────┤
├── 3.3 Purchase Criteria Screening ───────────────┤
├── 3.4 MAO Calculator ────────────────────────────┤
├── 3.5 Side-by-Side Comparison ───────────────────┤
├── 3.6 Professional Reports ──────────────────────┤
└── 3.7 Photo Management ──────────────────────────┘
                                                      │
Phase 4 (Polish) ◄───────────────────────────────────┘
├── 4.1 Owner Lookup
├── 4.2 Lender Directory
├── 4.3 Glossary
├── 4.4 Data Sync
├── 4.5 Dashboard & UX Polish
├── 4.6 Settings
└── 4.7 Documentation
```

---

## Effort Estimates

| Phase | Weeks | Key Risk |
|-------|-------|----------|
| Phase 1: Foundation | 3 | Calculation accuracy — must match dealcheck.io exactly |
| Phase 2: Analysis Depth | 3 | BRRRR refinance modeling complexity |
| Phase 3: Power Features | 4 | Report generation quality, comps map rendering |
| Phase 4: Polish | 4 | Owner lookup data quality, glossary completeness |
| Phase 5: Advanced | 6 | Market data aggregation, alert infrastructure |
| Phase 6: Mobile | 8+ | React Native learning curve, offline sync |

**Total to functional MVP (Phase 1-2):** ~6 weeks
**Total to dealcheck.io feature parity (Phase 1-4):** ~14 weeks
**Solo developer pace:** Double the estimates above

---

## Testing Strategy

| Layer | What | Framework |
|-------|------|-----------|
| Unit | All calculation functions | pytest |
| Unit | API endpoint logic | pytest + httpx |
| Integration | RentCast API wrapper | pytest + responses (mocked) |
| Integration | Database operations | pytest + testcontainers |
| E2E | Full analysis flow | Playwright |
| E2E | Auth + property CRUD | Playwright |
| Visual | Report rendering | Percy or Chromatic |

**Critical:** Every financial calculation must have hand-verified test cases matching dealcheck.io output. Use the sample report PDF as ground truth.

---

## Out of Scope (for now)
- Non-US property data (UK, Canada, Australia)
- AI-powered deal recommendations
- CRM integration
- Accounting/bookkeeping integration
- Property management features (tenant tracking, rent collection)
- Real-time listing alerts from MLS
