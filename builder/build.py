#!/usr/bin/env python3
"""
Octoru builder routine.
Runs under Claude Code auto mode. Obeys build_state + token budget.
Renders pages from data + template; builds to a branch; NEVER deploys.
(Publish is hard-gated — see CLAUDE.md.)

Geo hierarchy: state > county > city > treatment, read from the OPERATOR-OWNED
config seed_scope.geo tree (builder reads, never invents, cannot edit config).
Back-compat: if config has only the flat seed_scope.neighborhoods, those are treated
as active cities in Miami-Dade, Florida.
"""
import json, sys, datetime, urllib.parse, math
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from scipy.stats import beta as scipy_beta   # exact Beta quantile for provider ranking

ROOT = Path(__file__).resolve().parent.parent
CONFIG = json.loads((ROOT / "config" / "thresholds.json").read_text())
STATE_PATH = ROOT / "state" / "build_state.json"
LEDGER_PATH = ROOT / "state" / "run_ledger.json"
GENERATED = ROOT / "generated"
SITE_URL = "https://octoru.com"  # production domain (Namecheap registrar, Cloudflare Pages host)

# Completeness thresholds are OPERATOR-OWNED (config/thresholds.json -> "completeness").
# Builder READS them; never invents them; cannot edit config (hard-gated). Absent -> DRY-RUN.
COMPLETENESS = CONFIG.get("completeness")
RECOMMENDED_COMPLETENESS = {
    "min_listing_fields": ["name", "address", "phone", "rating", "treatments"],
    "min_page_requirements": {"min_listings": 3, "require_cost_block": True, "require_guidance": True},
}

# Monetization: flat placement only. Revenue is never tied to per-patient/per-inquiry
# value. See data/monetization_policy.json for the full model.
# Slot cap: max featured listings per page (prevents all-paid pages). Operator can set
# completeness.max_featured_per_page in config; defaults to 3.
MAX_FEATURED_PER_PAGE = int((COMPLETENESS or {}).get("max_featured_per_page", 3))


# ----------------------------------------------------------------------------------
# Verticals / categories (OPERATOR-OWNED in config seed_scope.categories).
# Each category carries its own treatment slugs and may override completeness via
# completeness.by_category.<cat>. The builder READS these; never invents them; cannot
# edit config (hard-gated). A clinic's category defaults to "med-spa" when the record
# omits it (back-compat: the original prospector data predates the category field).
# ----------------------------------------------------------------------------------
DEFAULT_CATEGORY = "med-spa"

def _categories_config():
    """Map of category -> {"treatments": [...]}. Falls back to a single med-spa
    category built from the legacy flat seed_scope.treatments when no categories block."""
    cats = (CONFIG.get("seed_scope") or {}).get("categories")
    if cats:
        return cats
    return {DEFAULT_CATEGORY: {"treatments": (CONFIG.get("seed_scope") or {}).get("treatments", [])}}

def _category_treatments(category):
    return list(((_categories_config().get(category)) or {}).get("treatments", []))

def _clinic_category(clinic):
    return clinic.get("category") or DEFAULT_CATEGORY

def _category_page_reqs(spec, category):
    """Per-category page requirements: the global completeness.min_page_requirements
    with completeness.by_category.<cat>.min_page_requirements layered on top."""
    base = dict((spec or {}).get("min_page_requirements") or {})
    override = ((((spec or {}).get("by_category") or {}).get(category)) or {}).get("min_page_requirements") or {}
    base.update(override)
    return base

# Human-facing labels for each category/vertical. Drives the homepage and any other
# category-aware surface. UNKNOWN future categories degrade gracefully (name derived from
# the slug, empty tagline) so a new vertical surfaces on the homepage with zero code changes —
# add a row here only to give it a nicer label/tagline.
CATEGORY_META = {
    "med-spa": {
        "name": "Med spa",
        "tagline": "Non-surgical aesthetic & wellness treatments",
        "noun": "treatment",
    },
    "plastic-surgery": {
        "name": "Plastic surgery",
        "tagline": "Board-certified surgical procedures",
        "noun": "procedure",
    },
}

def _category_name(category):
    return (CATEGORY_META.get(category) or {}).get("name") or category.replace("-", " ").title()

def _category_tagline(category):
    return (CATEGORY_META.get(category) or {}).get("tagline") or ""

def _category_noun(category):
    return (CATEGORY_META.get(category) or {}).get("noun") or "treatment"

# Place taxonomy: loaded from data/places.json (operator-owned).
# Provides place type, parent_place for rollup, lat/lng for geolocation.
_PLACES_PATH = ROOT / "data" / "places.json"
try:
    _PLACES_RAW = [p for p in json.loads(_PLACES_PATH.read_text()) if not p.get("_comment")]
except Exception:
    _PLACES_RAW = []
PLACES_BY_SLUG = {p["slug"]: p for p in _PLACES_RAW}

def _place_type(slug):
    """Returns the type ('municipality'|'neighborhood'|'cdp') for a place slug, or None."""
    return PLACES_BY_SLUG.get(slug, {}).get("type")

def _parent_slug(slug):
    """Returns the parent_place slug for a neighborhood/CDP, or None."""
    return PLACES_BY_SLUG.get(slug, {}).get("parent_place")

# Surgeon entities (plastic-surgery vertical): data/surgeons.json (operator/prospector-owned).
# A surgeon's contact is their clinic; ranking inherits the clinic's score. Credentials are
# displayed AS-STATED with a source link — never adjudicated, never negated. Absent file -> {}.
_SURGEONS_PATH = ROOT / "data" / "surgeons.json"
try:
    _SURGEONS_RAW = [s for s in json.loads(_SURGEONS_PATH.read_text()) if not s.get("_comment")]
except Exception:
    _SURGEONS_RAW = []
SURGEONS_BY_CLINIC = {}
for _s in _SURGEONS_RAW:
    SURGEONS_BY_CLINIC.setdefault(_s.get("clinic_slug"), []).append(_s)

def _surgeons_for(clinic_slug, treatment_slug):
    """Surgeons at this clinic who perform this procedure (or list no procedures = all).
    Returns display dicts; the rating shown for the listing is the CLINIC's, never the
    surgeon's — surgeons carry only their as-stated credentials + a source link."""
    out = []
    for s in SURGEONS_BY_CLINIC.get(clinic_slug, []):
        procs = s.get("procedures") or []
        if procs and treatment_slug not in procs:
            continue
        out.append({
            "name": s.get("name"),
            "credentials_text": s.get("credentials_text") or "",
            "credentials_source": s.get("credentials_source") or "",
            "independent": bool(s.get("independent")),
        })
    return out

env = Environment(
    loader=FileSystemLoader(str(ROOT / "templates")),
    autoescape=select_autoescape(["html", "j2"]),
)

PROSPECTOR_DIR = ROOT / "data" / "prospector"

TREATMENT_NAMES = {
    "botox": "Botox",
    "lip-filler": "Lip filler",
    "coolsculpting": "CoolSculpting",
    "laser-hair-removal": "Laser hair removal",
    "microneedling": "Microneedling",
    # plastic-surgery vertical
    "bbl": "Brazilian Butt Lift (BBL)",
    "tummy-tuck": "Tummy Tuck",
    "breast-augmentation": "Breast Augmentation",
    "liposuction": "Liposuction",
    "rhinoplasty": "Rhinoplasty",
    "mommy-makeover": "Mommy Makeover",
    "facelift": "Facelift",
}
NEIGHBORHOOD_NAMES = {
    "brickell": "Brickell",
    "coral-gables": "Coral Gables",
    "south-beach": "South Beach",
    "coconut-grove": "Coconut Grove",
}

# One or two sentences of real local character per city. Used in page intros and guide pages
# to make the content feel written by someone who knows the area, not templated.
NEIGHBORHOOD_CONTEXT = {
    # Miami-Dade
    "aventura": "Aventura sits between Miami and Fort Lauderdale, built around one of Florida's largest malls and surrounded by high-rise towers of affluent residents.",
    "bal-harbour": "Bal Harbour is a small ultra-wealthy enclave anchored by its luxury shopping village. Providers here cater to a discerning, image-conscious clientele.",
    "brickell": "Brickell is Miami's financial district — a vertical neighborhood of glass towers packed with professionals who expect efficiency and quality.",
    "coconut-grove": "Coconut Grove is Miami's oldest neighborhood, with a bohemian-meets-affluent character and tree-lined streets. Practices here tend to be boutique, with loyal local followings.",
    "coral-gables": "Coral Gables is a planned Mediterranean-style city with strict architectural standards and a strong wellness culture. Some of South Florida's most established aesthetic practices are based here.",
    "doral": "Doral is a fast-growing city with a large Latin American professional community. Providers here are often bilingual and competitively priced.",
    "hialeah": "Hialeah has the highest proportion of Cuban-American residents of any major U.S. city. Spanish-speaking providers are the norm, and pricing tends to be accessible.",
    "homestead": "Homestead sits at the southern edge of Miami-Dade, near the entrance to the Keys. It has fewer providers than northern parts of the county but serves a practical, price-conscious clientele.",
    "kendall": "Kendall is a sprawling western suburb of Miami-Dade with a large middle-class and Latin American population. Providers here compete on value.",
    "key-biscayne": "Key Biscayne is an island village minutes from downtown Miami with some of Florida's highest average household incomes. It has a small but selective provider market.",
    "miami-lakes": "Miami Lakes is a master-planned community north of Hialeah with a stable, family-oriented demographic and solid mid-size med-spa coverage.",
    "miami-springs": "Miami Springs is a quiet residential suburb adjacent to Miami International Airport, with a small selection of neighbourhood providers serving a primarily local clientele.",
    "midtown": "Midtown encompasses the Wynwood and Design District area — a hub of art, hospitality, and creative industries. Practices here skew toward a younger, trend-forward demographic.",
    "north-miami": "North Miami is a diverse working-class city north of Miami proper. Providers offer accessible pricing and serve a multicultural patient base.",
    "palmetto-bay": "Palmetto Bay is an affluent suburban village in south Miami-Dade, popular with families and professionals seeking a quieter alternative to the city.",
    "pinecrest": "Pinecrest is one of Miami-Dade's wealthiest communities — tree-lined, residential, and home to many South Florida physicians who also practice aesthetic medicine.",
    "south-beach": "South Beach occupies the southern tip of Miami Beach — globally recognised, high-energy, and image-conscious. Providers serve a mix of year-round residents, seasonal tourists, and entertainment-industry clients.",
    "sunny-isles-beach": "Sunny Isles Beach is an oceanfront city sometimes called 'Little Moscow' for its large Russian-speaking population. Russian, English, and Spanish are all commonly spoken in practices here.",
    "surfside": "Surfside is a quiet oceanfront town of about 6,000 residents adjacent to Bal Harbour. It has very few providers, but those present serve a well-heeled and often seasonal clientele.",
    # Broward
    "coconut-creek": "Coconut Creek is a planned Broward suburb with a significant over-50 population and a correspondingly strong demand for anti-ageing treatments.",
    "cooper-city": "Cooper City is a small, family-oriented suburb with consistently high school ratings and a stable middle-class demographic.",
    "coral-springs": "Coral Springs is one of Broward's largest cities, widely regarded as well-run and well-planned, with a strong professional and family demographic.",
    "dania-beach": "Dania Beach is one of Broward's oldest cities, situated between Fort Lauderdale and Hollywood. It has a growing aesthetic market as the neighbourhood continues to evolve.",
    "davie": "Davie retains a ranch-town character despite its suburban density. Home to Nova Southeastern University, it serves a wide range of demographics.",
    "deerfield-beach": "Deerfield Beach sits at the northern edge of Broward with Atlantic Ocean access, mixing retirees, young professionals, and beach-lifestyle residents.",
    "fort-lauderdale": "Fort Lauderdale is Broward's largest and most cosmopolitan city, with a well-established LGBTQ+ community, international visitors, and a growing financial sector — and the county's deepest med-spa market.",
    "hallandale-beach": "Hallandale Beach lies between Miami and Fort Lauderdale, known for its casino resorts and large snowbird population. Demand for aesthetic services runs year-round.",
    "hollywood": "Hollywood, Florida has a long oceanfront boardwalk, a vibrant downtown, and a mix of long-time residents and seasonal visitors — larger and more cosmopolitan than visitors often expect.",
    "lighthouse-point": "Lighthouse Point is an affluent waterfront enclave east of Pompano Beach with some of Broward's highest income levels.",
    "margate": "Margate is an inland Broward suburb with a predominantly middle-income, older demographic and practical, accessibly priced providers.",
    "miramar": "Miramar is one of Broward's fastest-growing cities, popular with Caribbean-American and Latino families, with an expanding aesthetic services market.",
    "oakland-park": "Oakland Park borders Fort Lauderdale and has a strong arts and LGBTQ+ community. Independent boutique practices are the norm here.",
    "parkland": "Parkland is consistently ranked among Florida's best cities to live — affluent, family-focused, and with high demand for non-surgical aesthetics.",
    "pembroke-pines": "Pembroke Pines is one of Broward's largest cities with a significant Cuban-American and Caribbean population and a well-served suburban aesthetic market.",
    "plantation": "Plantation is a mid-size Broward suburb with a strong professional class, convenient I-595 access, and a mix of larger practices and boutique providers.",
    "pompano-beach": "Pompano Beach is an evolving coastal city with a strong fishing heritage and a growing arts scene, its med-spa market expanding alongside a gentrifying downtown.",
    "sunrise": "Sunrise is best known as the home of Sawgrass Mills, one of America's largest outlet malls. Its dense residential base and highway accessibility make it a practical base for aesthetic providers.",
    "weston": "Weston is consistently ranked among Florida's best places to live — a master-planned community with high household incomes and strong demand for wellness and aesthetics.",
    # Palm Beach
    "boca-raton": "Boca Raton is the cultural and commercial hub of southern Palm Beach County, with some of Florida's highest household incomes and a deeply rooted personal-wellness culture.",
    "boynton-beach": "Boynton Beach is one of Palm Beach County's largest cities, with a diverse population — retirees, families, and young professionals — served across a range of price points.",
    "delray-beach": "Delray Beach has transformed into one of Florida's most desirable small cities. Its walkable Atlantic Avenue, arts scene, and affluent demographic have attracted some of the county's most highly reviewed aesthetic providers.",
    "jupiter": "Jupiter is an upscale coastal community at the northern edge of Palm Beach County, popular with professional athletes, retirees, and health-focused families.",
    "north-palm-beach": "North Palm Beach is a waterfront village between Palm Beach Gardens and West Palm Beach, with strong boating culture and a small but well-curated selection of aesthetic providers.",
    "palm-beach-gardens": "Palm Beach Gardens is the county's commercial centre — home to PGA National and a rapidly expanding professional population with corresponding demand for aesthetic services.",
    "royal-palm-beach": "Royal Palm Beach is a large inland suburb with a young, family-oriented demographic. Providers here are practical, accessible, and competitively priced.",
    "wellington": "Wellington is a globally recognised equestrian destination with a wealthy, health-focused population. Aesthetic practices here skew toward a performance-wellness clientele.",
    "west-palm-beach": "West Palm Beach is the county seat and the most urban city in Palm Beach County, with a growing arts and wellness culture serving everyone from budget-conscious locals to Intracoastal residents.",
}

# Per-treatment FAQ templates. {city}, {n}, {price_range}, {county} are filled at build time.
# Answers are written to sound human — no robotic patterns, varied sentence structures.
TREATMENT_FAQS = {
    "botox": [
        {
            "q": "How much does Botox cost in {city}?",
            "a_prices": "Based on the {n} providers listed in our {city} directory, Botox starts around {price_range}. Most practices price by the unit, so the total depends on the treatment area — forehead lines typically need 10–20 units, crow's feet 10–15 units per side, and a full upper-face treatment 20–40 units. First-time patients are often advised to start conservatively and add units at a follow-up.",
            "a_no_prices": "Botox in {city} is priced per unit at most practices. A typical forehead treatment runs $200–$400 depending on unit count and injector experience. Request a consultation to get a quote tailored to your specific goals — a reputable provider will assess what you need rather than upselling maximum units.",
        },
        {
            "q": "How long does Botox last?",
            "a": "Most patients enjoy results for three to four months, though this varies with your metabolism, the treatment area, and how regularly you have the treatment done. Muscles in heavily used areas — like the forehead — tend to bounce back faster. With consistent treatments over time, many patients find they need top-ups less frequently as the targeted muscles gradually weaken.",
        },
        {
            "q": "What should I look for when choosing a Botox provider in {city}?",
            "a": "Your injector's credentials and experience matter more than the price. Look for a licensed medical professional — physician, nurse practitioner, or physician assistant — who can show you a portfolio of natural-looking results. Ask whether a physician is supervising or performing the treatment, confirm they use FDA-approved product from an authorised distributor, and be wary of unusually low pricing, which can indicate diluted product or under-trained staff.",
        },
        {
            "q": "What is the difference between Botox and Dysport?",
            "a": "Both are botulinum toxin type A neurotoxins approved to soften dynamic wrinkles — Botox has been FDA-cleared since 2002, Dysport since 2009. Dysport tends to spread slightly more, which some injectors prefer for broader areas like the forehead. The units are not equivalent; roughly 2.5 Dysport units equal one Botox unit, so comparing prices requires knowing which product is being quoted. Results and safety profiles are comparable.",
        },
        {
            "q": "Is Botox safe?",
            "a": "Botox has one of the longest safety records of any cosmetic procedure. Side effects are typically minor — bruising at the injection site, a brief headache, or slight asymmetry — and resolve on their own within days. Serious complications are rare when the treatment is performed by a qualified injector using authentic product sourced from a licensed distributor. If a price seems too good to be true, ask where the product comes from.",
        },
    ],
    "lip-filler": [
        {
            "q": "How much does lip filler cost in {city}?",
            "a_prices": "{n} providers in our {city} directory offer lip filler. Most practices charge per syringe of hyaluronic acid filler — a single syringe is usually sufficient for a first treatment, with touch-ups possible at a follow-up. Ask whether the quoted price includes a complimentary two-week review, which many quality practices offer.",
            "a_no_prices": "Lip filler in South Florida typically costs $500–$900 per syringe for hyaluronic acid products like Juvederm Volbella, Restylane Kysse, or RHA. Price reflects the specific product used, the injector's experience, and the clinic's location. Get a consultation before committing — a good injector will advise on how much filler actually serves your goals.",
        },
        {
            "q": "How long does lip filler last?",
            "a": "Results typically last six to twelve months, though the lips break down filler faster than less-mobile areas because of how frequently they move. The specific product, the amount placed, and your individual metabolism all play a role. Many patients schedule a top-up at around six months to maintain their result rather than waiting for it to fully fade.",
        },
        {
            "q": "Is lip filler reversible?",
            "a": "Yes — hyaluronic acid filler can be fully dissolved using hyaluronidase, an enzyme that is injected into the treated area. The effect is rapid, usually within hours. It is a useful safety net if results are uneven, overfilled, or simply not what you wanted. Ask your provider whether they stock hyaluronidase on-site; the answer tells you something important about how seriously they take patient safety.",
        },
        {
            "q": "What should I look for when choosing a lip filler provider in {city}?",
            "a": "Lips are technically demanding — they require a light hand and good aesthetic judgement, not just injection technique. Look for a provider who consistently shows natural-looking results in their portfolio and who recommends starting conservatively. You can always add more at a follow-up; overcorrection means dissolving the filler and starting over. Confirm that they stock hyaluronidase and that product is properly refrigerated.",
        },
        {
            "q": "Does lip filler hurt?",
            "a": "Most providers apply topical numbing cream before the treatment, and many fillers contain lidocaine which provides additional comfort during the injection itself. Patients typically describe it as mild pressure or a brief sting. Some swelling and tenderness for 24–48 hours afterward is completely normal — lips are highly vascular and swell readily. Results settle into their final shape within a week.",
        },
    ],
    "coolsculpting": [
        {
            "q": "How much does CoolSculpting cost in {city}?",
            "a_prices": "CoolSculpting is priced per treatment cycle, and total cost depends on how many areas you want to treat and which applicator sizes are used. Providers in {city} offer free consultations where they will map out a treatment plan and give you a personalised quote.",
            "a_no_prices": "CoolSculpting is quoted per treatment cycle, and most patients treat more than one area. A single-area session typically runs $700–$1,500; treating both flanks or the abdomen plus flanks in one session commonly costs $2,000–$4,000. Providers regularly offer package pricing that reduces the per-session cost. A free consultation will get you an accurate number for your specific goals.",
        },
        {
            "q": "How many CoolSculpting sessions will I need?",
            "a": "Most patients see meaningful improvement after a single session per area. Those wanting more dramatic results typically schedule a second round six to twelve weeks after the first, once the body has finished processing the initial treatment. CoolSculpting permanently destroys fat cells, which do not regenerate — but weight gain can expand the remaining cells in surrounding areas, so maintaining results requires stable weight.",
        },
        {
            "q": "When will I see CoolSculpting results?",
            "a": "The body processes destroyed fat cells gradually through the lymphatic system, so results appear slowly. Most patients notice visible changes at four to six weeks, with the full outcome visible at two to three months. The gradual timeline is actually an advantage — results look natural rather than sudden.",
        },
        {
            "q": "Is CoolSculpting safe?",
            "a": "CoolSculpting received FDA clearance in 2010 and has a well-established safety record for non-surgical fat reduction. Common side effects — temporary numbness, redness, bruising, and sensitivity in the treated area — resolve on their own. Ask your provider about paradoxical adipose hyperplasia (PAH), a rare side effect in which the treated area enlarges rather than reduces. A qualified provider will explain the risk and discuss whether it applies to your treatment plan.",
        },
    ],
    "laser-hair-removal": [
        {
            "q": "How much does laser hair removal cost in {city}?",
            "a_prices": "Laser hair removal pricing varies by treatment area and session count. Providers in {city} often offer package pricing across multiple sessions, which is the most cost-effective approach since permanent reduction requires a course of treatments.",
            "a_no_prices": "Pricing depends on the area being treated and whether you purchase individual sessions or a package. Small areas like the upper lip or underarms run roughly $75–$150 per session; larger areas like legs or the back cost $200–$400. Clinics typically offer six to eight-session packages that reduce the per-visit price considerably.",
        },
        {
            "q": "How many sessions do I need for laser hair removal?",
            "a": "Most patients need six to eight sessions spaced four to eight weeks apart to achieve significant permanent reduction. Laser targets follicles only in the active growth phase — hair grows in cycles, so multiple sessions are required to catch every follicle at the right stage. After the initial course, occasional maintenance sessions once or twice a year handle any regrowth.",
        },
        {
            "q": "Does laser hair removal work on darker skin tones?",
            "a": "Yes — technology has improved significantly over the years. The Nd:YAG laser (1064nm wavelength) is both safe and effective across Fitzpatrick skin types IV through VI, which covers most of South Florida's patient population. Older systems like some Alexandrite or Diode lasers are better suited to lighter skin. Ask your provider which laser they use and confirm it is appropriate for your skin tone before your first appointment.",
        },
        {
            "q": "Is laser hair removal permanent?",
            "a": "The FDA classifies it as 'permanent hair reduction' rather than complete removal, because a small percentage of follicles can regenerate over time — particularly with hormonal shifts. In practice, most patients experience 70–90% permanent reduction after a full treatment course and require minimal maintenance afterward. The results are dramatically better than waxing, shaving, or threading over any multi-year period.",
        },
    ],
    "microneedling": [
        {
            "q": "How much does microneedling cost in {city}?",
            "a_prices": "Microneedling prices vary by device, any add-ons (PRP, radiofrequency), and the provider's experience level. Standard sessions and more advanced RF microneedling treatments are both available from providers in our {city} directory — a consultation will clarify which approach suits your skin goals.",
            "a_no_prices": "A standard microneedling session typically costs $200–$400. Advanced treatments — RF microneedling (Morpheus8, Scarlet SRF, Vivace) or sessions with PRP — run $400–$800 per visit due to equipment and add-on costs. Package pricing for multiple sessions is common and reduces the per-session cost meaningfully.",
        },
        {
            "q": "How many microneedling sessions do I need?",
            "a": "For texture improvement and mild scarring, most practitioners recommend three to six sessions spaced four to six weeks apart. More significant concerns — deep acne scars, pronounced laxity — may benefit from a longer course or from RF microneedling rather than standard needling. Results continue improving for months after the final session, because the collagen remodelling process unfolds gradually.",
        },
        {
            "q": "What skin concerns does microneedling treat?",
            "a": "Microneedling is most effective for improving skin texture, minimising enlarged pores, reducing acne and surgical scarring, and softening fine lines. RF microneedling adds a skin-tightening dimension that works well for mild laxity. It is generally less effective for deep static wrinkles or significant volume loss, where injectable treatments tend to deliver better results.",
        },
        {
            "q": "What is the downtime after microneedling?",
            "a": "Standard microneedling causes redness and mild sensitivity for 24–48 hours — similar to a sunburn. Most patients return to work the next day with light-coverage makeup. RF microneedling may involve two to three days of more noticeable redness and some swelling. Either way, sun protection is essential for at least two weeks following treatment.",
        },
    ],
    # ---------- plastic-surgery vertical FAQs ----------
    "bbl": [
        {
            "q": "How much does a BBL cost in {city}?",
            "a_prices": "Among the {n} providers in our {city} directory, Brazilian Butt Lift pricing starts around {price_range}. A BBL fee usually bundles the liposuction needed to harvest the fat plus the fat transfer itself; anesthesia and accredited-facility costs are typically quoted separately. Book a consultation for a quote based on your anatomy and goals.",
            "a_no_prices": "A Brazilian Butt Lift in South Florida commonly runs $4,000–$12,000+ depending on the surgeon, how much liposuction is involved, and anesthesia and facility fees. Because BBL safety depends heavily on technique, prioritize a board-certified plastic surgeon over the lowest price — request a personalized quote at a consultation.",
        },
        {
            "q": "Is a BBL safe?",
            "a": "A BBL carries higher risk than most cosmetic procedures because fat injected too deeply can enter large veins. Modern safety guidelines — injecting only above the muscle, often with ultrasound guidance — have substantially reduced that risk. Choose a board-certified plastic surgeon operating in an accredited facility, and ask specifically how they avoid deep fat injection.",
        },
        {
            "q": "What is BBL recovery like?",
            "a": "Most patients avoid sitting directly on the buttocks for about two to three weeks, using a special pillow when seated, and wear a compression garment. Swelling settles over several weeks, and results refine over a few months as some transferred fat is reabsorbed. Your surgeon will give you a specific aftercare and activity timeline.",
        },
    ],
    "tummy-tuck": [
        {
            "q": "How much does a tummy tuck cost in {city}?",
            "a_prices": "Among the {n} providers in our {city} directory, tummy tuck pricing starts around {price_range}. The fee usually reflects the surgeon's fee, with anesthesia and accredited-facility costs quoted separately, and varies between a full and a mini procedure. A consultation will give you an accurate number for your goals.",
            "a_no_prices": "A tummy tuck in South Florida typically runs $6,000–$12,000+ depending on whether it is a full or mini abdominoplasty and on anesthesia and facility fees. Request a quote at a consultation with a board-certified plastic surgeon.",
        },
        {
            "q": "Full or mini tummy tuck — which do I need?",
            "a": "A full tummy tuck addresses loose skin and muscle separation above and below the navel and is common after pregnancy or major weight loss; a mini tuck targets only the area below the navel for smaller concerns. A board-certified plastic surgeon will assess your skin, muscle separation, and goals to recommend the right option.",
        },
        {
            "q": "What is tummy tuck recovery like?",
            "a": "Expect roughly two weeks before returning to desk work and about six weeks before resuming vigorous exercise. You will wear a compression garment, and many patients have temporary drains. The final contour appears over several months as swelling resolves.",
        },
    ],
    "breast-augmentation": [
        {
            "q": "How much does breast augmentation cost in {city}?",
            "a_prices": "Among the {n} providers in our {city} directory, breast augmentation starts around {price_range}. The price usually reflects the surgeon's fee plus implants, anesthesia, and facility costs. A consultation will clarify your implant options and a personalized quote.",
            "a_no_prices": "Breast augmentation in South Florida commonly runs $5,000–$10,000+ depending on implant type, the surgeon, and anesthesia and facility fees. Request a quote at a consultation with a board-certified plastic surgeon.",
        },
        {
            "q": "Saline or silicone implants — what's the difference?",
            "a": "Silicone implants tend to feel more like natural breast tissue and are popular, while saline implants are filled after placement and can require a smaller incision. Each has trade-offs in feel, rupture detection, and follow-up. Discuss implant type, size, and placement (over or under the muscle) with a board-certified plastic surgeon.",
        },
        {
            "q": "How long do breast implants last?",
            "a": "Implants are not necessarily lifetime devices; many people eventually have them replaced or removed, often after 10 or more years, due to changes, rupture, or preference. Routine follow-up — and, for silicone, periodic imaging — is recommended. Your surgeon will outline a monitoring plan.",
        },
    ],
    "liposuction": [
        {
            "q": "How much does liposuction cost in {city}?",
            "a_prices": "Among the {n} providers in our {city} directory, liposuction starts around {price_range}. Cost depends on the number and size of areas treated, plus anesthesia and facility fees. A consultation will give you a quote for your specific areas.",
            "a_no_prices": "Liposuction in South Florida typically runs $3,000–$8,000+ depending on the number of areas treated and on anesthesia and facility fees. Request a quote at a consultation with a board-certified plastic surgeon.",
        },
        {
            "q": "Is liposuction a weight-loss procedure?",
            "a": "No. Liposuction contours specific areas of stubborn fat — it is not a treatment for obesity or a substitute for diet and exercise. The best candidates are near their goal weight with localized fat that resists lifestyle changes.",
        },
        {
            "q": "What is liposuction recovery like?",
            "a": "Most people return to desk work within a few days to a week and wear a compression garment for several weeks to manage swelling. Bruising and firmness are normal early on, and the final contour emerges over one to three months. Your surgeon will give you an activity timeline.",
        },
    ],
    "rhinoplasty": [
        {
            "q": "How much does rhinoplasty cost in {city}?",
            "a_prices": "Among the {n} providers in our {city} directory, rhinoplasty starts around {price_range}. The fee reflects the surgeon's experience plus anesthesia and facility costs, and revision cases can differ. A consultation will give you a tailored quote.",
            "a_no_prices": "Rhinoplasty in South Florida commonly runs $7,000–$15,000+ depending heavily on the surgeon's experience and on anesthesia and facility fees. Because results depend on surgical skill, prioritize an experienced board-certified surgeon — request a quote at a consultation.",
        },
        {
            "q": "How do I choose a rhinoplasty surgeon?",
            "a": "Rhinoplasty is one of the most technically demanding cosmetic surgeries, so the surgeon's experience matters more than price. Look for a board-certified plastic or facial plastic surgeon with a large portfolio of natural-looking noses similar to your goals, and confirm they operate in an accredited facility.",
        },
        {
            "q": "What is rhinoplasty recovery like?",
            "a": "An external splint is usually worn for about a week, with bruising and swelling around the eyes fading over two to three weeks. Subtle swelling at the tip can take up to a year to fully resolve, so the final result appears gradually. Your surgeon will guide you on aftercare.",
        },
    ],
    "mommy-makeover": [
        {
            "q": "How much does a mommy makeover cost in {city}?",
            "a_prices": "Among the {n} providers in our {city} directory, mommy makeover pricing starts around {price_range}. Because it combines procedures — often a tummy tuck, breast surgery, and liposuction — the total is customized to your plan, with anesthesia and facility costs included. A consultation will produce a personalized quote.",
            "a_no_prices": "A mommy makeover in South Florida commonly runs $10,000–$20,000+ because it bundles several procedures in one surgery. The exact figure depends on which procedures you combine plus anesthesia and facility fees — request a personalized quote at a consultation.",
        },
        {
            "q": "What procedures are included in a mommy makeover?",
            "a": "It is a customizable combination, most often a tummy tuck plus breast augmentation or lift, frequently with liposuction. The plan is tailored to the changes you want to address after pregnancy. A board-certified plastic surgeon will help you decide which procedures to combine safely in one operation.",
        },
        {
            "q": "What is mommy makeover recovery like?",
            "a": "Because it bundles multiple procedures, recovery is more involved than any single surgery — typically two to three weeks before returning to light work and about six weeks before vigorous activity. Planning help with childcare and household tasks is strongly advised. Your surgeon will provide a staged recovery plan.",
        },
    ],
    "facelift": [
        {
            "q": "How much does a facelift cost in {city}?",
            "a_prices": "Among the {n} providers in our {city} directory, facelift pricing starts around {price_range}. The fee reflects the technique and the surgeon's experience plus anesthesia and facility costs. A consultation will clarify which approach suits you and a personalized quote.",
            "a_no_prices": "A facelift in South Florida commonly runs $8,000–$18,000+ depending on the technique (mini vs. deep-plane), the surgeon, and anesthesia and facility fees. Request a quote at a consultation with a board-certified surgeon.",
        },
        {
            "q": "How long does a facelift last?",
            "a": "A facelift turns the clock back rather than stopping it; results commonly last roughly 8 to 12 years, though aging continues naturally afterward. Skin quality, technique, and lifestyle all affect longevity. Many patients maintain results with non-surgical treatments over time.",
        },
        {
            "q": "What is the difference between a mini and a deep-plane facelift?",
            "a": "A mini facelift addresses early jowling with shorter incisions and a quicker recovery, while a deep-plane facelift repositions deeper tissue layers for more comprehensive, longer-lasting rejuvenation. The right choice depends on your anatomy and goals — a board-certified surgeon will recommend the appropriate technique at your consultation.",
        },
    ],
}


def _build_intro(treatment_slug, market, clinics, prices, all_clinics_for_county=None,
                 category=DEFAULT_CATEGORY, fallback=False):
    """Build a rich, human-sounding page intro from real data. Each city reads as if
    written by someone who knows the area — not a template with a city name swapped in."""
    t_name = TREATMENT_NAMES.get(treatment_slug, treatment_slug.replace("-", " ").title())
    city = market["city"]
    city_name = market["city_name"]
    county_name = market["county_name"]
    state_abbr = market["state_abbr"]
    n = len(clinics)
    unit = TREATMENT_UNITS.get(treatment_slug, "")
    langs = sorted({l for c in clinics for l in (c.get("languages") or [])})

    # Nearest-provider fallback page: be honest that there are NO local providers, then
    # point to the nearest ones. Never claim these providers are located in this city.
    if fallback:
        near_cities = []
        for c in clinics:
            nm = c.get("_nearby_city_name") or c.get("neighborhood_name")
            if nm and nm not in near_cities:
                near_cities.append(nm)
        if len(near_cities) > 1:
            where = ", ".join(near_cities[:-1]) + f" and {near_cities[-1]}"
        else:
            where = near_cities[0] if near_cities else "nearby cities"
        return (
            f"There are no {t_name.lower()} providers listed in {city_name} yet. "
            f"Below are the nearest board-certified options — in {where} — ordered by distance, "
            f"so you can still compare and book a consultation. Each listing shows the practice's "
            f"location, contact details, and verified Google rating; the rating shown is for the "
            f"practice, not an individual surgeon."
        )

    # Neighbourhood character sentence (if we have one)
    ctx = NEIGHBORHOOD_CONTEXT.get(city, "")

    # Price sentence — reference real data only
    if prices:
        rng = f"${prices[0]}" if prices[0] == prices[-1] else f"${prices[0]}–${prices[-1]}"
        price_str = f"{t_name} starts at {rng} {unit} among listed providers".rstrip()
    else:
        price_str = None

    # County comparison — compute county average price for this treatment from all clinics
    county_prices = []
    if all_clinics_for_county:
        for c in all_clinics_for_county:
            p = _starting_price(c, treatment_slug)
            if p:
                county_prices.append(p)
    if county_prices and prices:
        county_avg = sum(county_prices) / len(county_prices)
        city_avg = sum(prices) / len(prices)
        if city_avg < county_avg * 0.95:
            comparison = f", which is below the {county_name} County average"
        elif city_avg > county_avg * 1.05:
            comparison = f", which is above the {county_name} County average"
        else:
            comparison = ", in line with the broader {county_name} market".format(county_name=county_name)
    else:
        comparison = ""

    # Language sentence
    if langs and len(langs) >= 2:
        lang_str = f"Several listed providers offer consultations in {' and '.join(langs[:3])}."
    elif langs and langs[0] != "English":
        lang_str = f"A number of providers here offer consultations in {langs[0]}."
    else:
        lang_str = ""

    # Assemble — aim for natural, flowing prose
    provider_word = "provider" if n == 1 else "providers"
    parts = []
    if ctx:
        parts.append(ctx)

    if n == 1:
        provider_sent = f"Octoru has one verified {t_name.lower()} provider in {city_name}."
    else:
        provider_sent = f"Octoru has {n} verified {t_name.lower()} {provider_word} in {city_name}."
    parts.append(provider_sent)

    if price_str:
        price_full = f"{price_str}{comparison}." if comparison else f"{price_str}."
        parts.append(price_full.capitalize())

    if lang_str:
        parts.append(lang_str)

    if category == "plastic-surgery":
        parts.append("Each listing below shows the practice's location, contact details, the "
                     "procedures it offers, and its verified Google rating, plus the surgeons who "
                     "perform this procedure with their credentials as stated on the provider's "
                     "website. The rating shown is for the practice, not an individual surgeon — "
                     "always confirm a surgeon's credentials and facility accreditation at your consultation.")
    else:
        parts.append("Each listing below shows the clinic's address, phone, treatments, and verified Google rating so you can compare before booking a consultation.")

    return " ".join(parts)


def _generate_faqs(treatment_slug, market, clinics, prices):
    """Return a list of {{q, a}} dicts with real data filled in. Safe for FAQPage schema."""
    templates = TREATMENT_FAQS.get(treatment_slug, [])
    city_name = market["city_name"]
    n = len(clinics)
    unit = TREATMENT_UNITS.get(treatment_slug, "")
    price_range = (
        f"${prices[0]}–${prices[-1]} {unit}".strip()
        if len(prices) >= 2
        else (f"${prices[0]} {unit}".strip() if prices else None)
    )

    result = []
    for tpl in templates:
        q = tpl["q"].format(city=city_name, n=n, county=market["county_name"])
        if "a_prices" in tpl and "a_no_prices" in tpl:
            a_tpl = tpl["a_prices"] if price_range else tpl["a_no_prices"]
        else:
            a_tpl = tpl["a"]
        a = a_tpl.format(
            city=city_name, n=n,
            price_range=price_range or "varies by provider",
            county=market["county_name"]
        )
        result.append({"q": q, "a": a})
    return result
TREATMENT_UNITS = {
    "botox": "per unit",
    "lip-filler": "per syringe",
    "coolsculpting": "per session",
    "laser-hair-removal": "per session",
    "microneedling": "per session",
    # plastic surgery is quoted as a single surgical fee, not per-unit — no unit suffix.
    "bbl": "",
    "tummy-tuck": "",
    "breast-augmentation": "",
    "liposuction": "",
    "rhinoplasty": "",
    "mommy-makeover": "",
    "facelift": "",
}
TREATMENT_GUIDANCE = {
    "botox": "Botox is a neuromodulator injected to soften dynamic wrinkles; it is usually priced per unit, and the number of units depends on the treatment area. Effects typically last a few months. Ask each provider who performs the injections and how units are counted.",
    "lip-filler": "Lip filler uses hyaluronic-acid dermal fillers to add volume and shape; it is usually priced per syringe. Results are not permanent and vary by product. Ask which filler is used and about reversibility.",
    "coolsculpting": "CoolSculpting is a non-surgical fat-reduction treatment that cools targeted areas; it is typically priced per session or per area, and several sessions may be suggested. Ask how many cycles a provider recommends for your goal.",
    "laser-hair-removal": "Laser hair removal reduces unwanted hair over a course of sessions; pricing is usually per session or per package and depends on the body area. Ask how many sessions are typical and which laser suits your skin type.",
    "microneedling": "Microneedling stimulates collagen to refine skin texture; it is usually priced per session, sometimes with radiofrequency or PRP add-ons. Ask what device is used and how many sessions are suggested.",
    # plastic-surgery vertical — surgical procedures. Safety-forward, board-certification-aware.
    "bbl": "A Brazilian Butt Lift (BBL) transfers your own fat — harvested by liposuction — to reshape and add volume to the buttocks. It is a surgical procedure performed under anesthesia and is among the higher-risk cosmetic surgeries, so it should be done only by a board-certified plastic surgeon in an accredited surgical facility. Pricing is usually a single surgical fee plus anesthesia and facility costs. Ask about the surgeon's fat-transfer technique, safety protocols, and recovery during your consultation.",
    "tummy-tuck": "A tummy tuck (abdominoplasty) removes excess skin and fat from the lower abdomen and tightens the underlying muscles, often after pregnancy or major weight loss. It is performed surgically under anesthesia, with several weeks of recovery. Choose a board-certified plastic surgeon operating in an accredited facility, and ask whether a full or mini tummy tuck suits you. Pricing is typically a single surgical fee plus anesthesia and facility costs.",
    "breast-augmentation": "Breast augmentation increases breast size or restores volume using saline or silicone implants, or in some cases fat transfer. It is a surgical procedure performed under anesthesia. Implant type, size, and placement are decisions to make with a board-certified plastic surgeon at a consultation. Pricing usually reflects a surgical fee plus implants, anesthesia, and facility costs. Ask about implant options, longevity, and follow-up care.",
    "liposuction": "Liposuction removes localized fat through small cannulas to contour areas such as the abdomen, flanks, thighs, or chin. It is a surgical contouring procedure, not a weight-loss method, and works best for stubborn fat in people near their goal weight. Have it performed by a board-certified plastic surgeon in an accredited facility. Pricing depends on the number and size of areas; ask for a quote and recovery plan at your consultation.",
    "rhinoplasty": "Rhinoplasty (a 'nose job') reshapes the nose for cosmetic balance or to improve breathing. It is technically demanding and results depend heavily on the surgeon's experience, so look for a board-certified plastic or facial plastic surgeon with a strong rhinoplasty portfolio. Pricing reflects a surgical fee plus anesthesia and facility costs, and may differ for revision cases. Discuss your goals and open vs. closed technique at your consultation.",
    "mommy-makeover": "A mommy makeover combines procedures — commonly a tummy tuck, breast surgery, and liposuction — into one surgical plan addressing changes after pregnancy. Because it bundles multiple surgeries, it should be performed by a board-certified plastic surgeon in an accredited facility, with recovery planned accordingly. Pricing is customized to the combination chosen; request a personalized quote and staged recovery guidance at your consultation.",
    "facelift": "A facelift (rhytidectomy) tightens and repositions facial and neck tissues to soften deep folds and jowls. It is a surgical procedure under anesthesia, and results look most natural with an experienced board-certified surgeon. Techniques range from mini to deep-plane lifts. Pricing reflects a surgical fee plus anesthesia and facility costs. Ask which technique suits your anatomy and what recovery to expect at your consultation.",
}

# Short factual treatment blurbs for the homepage cards (not pricing — pricing is real-data only).
TREATMENT_DESC = {
    "botox": "Wrinkle-relaxing injections, priced per unit.",
    "lip-filler": "Hyaluronic-acid lip enhancement, priced per syringe.",
    "coolsculpting": "Non-invasive fat reduction, priced per area.",
    "laser-hair-removal": "Multi-session hair reduction, priced by area.",
    "microneedling": "Collagen-induction skin treatment, per session.",
    # plastic-surgery vertical
    "bbl": "Fat-transfer buttock reshaping — surgical.",
    "tummy-tuck": "Abdominal skin and muscle tightening — surgical.",
    "breast-augmentation": "Implant or fat breast enhancement — surgical.",
    "liposuction": "Targeted surgical fat removal and contouring.",
    "rhinoplasty": "Surgical reshaping of the nose.",
    "mommy-makeover": "Combined post-pregnancy surgical procedures.",
    "facelift": "Surgical facial and neck rejuvenation.",
}

# City centroids for geolocation — sourced from data/places.json (operator-owned taxonomy).
# Falls back to empty if places.json is absent; the build never invents clinic data from these.
CITY_LATLNG = {
    p["slug"]: (p["lat"], p["lng"])
    for p in _PLACES_RAW
    if p.get("lat") and p.get("lng")
}


def treatment_cards(clinics, treatments):
    """Homepage treatment cards for a given treatment list. 'Typical from' price is
    computed from REAL listing prices in `clinics`; treatments without enough real data
    get the honest empty state (no placeholder $)."""
    cards = []
    for t in treatments:
        vals = sorted({p for c in clinics if (p := _starting_price(c, t)) is not None})
        unit = TREATMENT_UNITS.get(t, "")
        if len(vals) >= 2:
            disp = f"${vals[0]}–${vals[-1]} {unit}".strip()
        elif len(vals) == 1:
            disp = f"from ${vals[0]} {unit}".strip()
        else:
            disp = None   # honest empty state -> template renders "Varies"
        cards.append({"slug": t, "name": TREATMENT_NAMES.get(t, t),
                      "desc": TREATMENT_DESC.get(t, ""), "from_display": disp})
    return cards


# ----------------------------------------------------------------------------------
# Geographic hierarchy: state > county > city (OPERATOR-OWNED in config seed_scope.geo)
# ----------------------------------------------------------------------------------
# City -> county map (so a flat seed_scope.neighborhoods list still gets correct counties
# when the operator hasn't supplied a full seed_scope.geo tree). Florida only for now.
CITY_COUNTY = {
    # Miami-Dade
    "aventura": "miami-dade", "bal-harbour": "miami-dade", "brickell": "miami-dade",
    "coconut-grove": "miami-dade", "coral-gables": "miami-dade", "doral": "miami-dade",
    "hialeah": "miami-dade", "homestead": "miami-dade", "kendall": "miami-dade",
    "key-biscayne": "miami-dade", "miami-lakes": "miami-dade", "miami-springs": "miami-dade",
    "midtown": "miami-dade", "north-miami": "miami-dade", "palmetto-bay": "miami-dade",
    "pinecrest": "miami-dade", "south-beach": "miami-dade", "sunny-isles-beach": "miami-dade",
    "surfside": "miami-dade",
    # Broward
    "coconut-creek": "broward", "cooper-city": "broward", "coral-springs": "broward",
    "dania-beach": "broward", "davie": "broward", "deerfield-beach": "broward",
    "fort-lauderdale": "broward", "hallandale-beach": "broward", "hollywood": "broward",
    "lighthouse-point": "broward", "margate": "broward", "miramar": "broward",
    "oakland-park": "broward", "parkland": "broward", "pembroke-pines": "broward",
    "plantation": "broward", "pompano-beach": "broward", "sunrise": "broward", "weston": "broward",
    # Palm Beach
    "boca-raton": "palm-beach", "west-palm-beach": "palm-beach",
    "delray-beach": "palm-beach", "palm-beach-gardens": "palm-beach",
    "jupiter": "palm-beach", "wellington": "palm-beach", "boynton-beach": "palm-beach",
    "north-palm-beach": "palm-beach", "royal-palm-beach": "palm-beach",
    "lake-worth-beach": "palm-beach", "greenacres": "palm-beach", "palm-beach": "palm-beach",
}
COUNTY_NAMES = {"miami-dade": "Miami-Dade", "broward": "Broward", "palm-beach": "Palm Beach"}


def _legacy_geo():
    """No seed_scope.geo -> derive a CORRECT state/county/city tree from the flat
    'neighborhoods' list using CITY_COUNTY (unknown cities default to Miami-Dade)."""
    geo = {"fl": {"name": "Florida", "abbr": "FL", "status": "active", "counties": {}}}
    for c in CONFIG["seed_scope"].get("neighborhoods", []):
        county = CITY_COUNTY.get(c, "miami-dade")
        cc = geo["fl"]["counties"].setdefault(
            county, {"name": COUNTY_NAMES.get(county, county.replace("-", " ").title()),
                     "status": "active", "cities": {}})
        cc["cities"][c] = {"name": NEIGHBORHOOD_NAMES.get(c, c.replace("-", " ").title()), "status": "active"}
    return geo


GEO = CONFIG["seed_scope"].get("geo") or _legacy_geo()


def _is_active(node):
    return (node or {}).get("status", "active") == "active"


def active_markets():
    """Every fully-active state > county > city chain, as flat market dicts."""
    out = []
    for s_slug, s in GEO.items():
        if not _is_active(s):
            continue
        for c_slug, c in (s.get("counties") or {}).items():
            if not _is_active(c):
                continue
            for city_slug, city in (c.get("cities") or {}).items():
                if not _is_active(city):
                    continue
                out.append({
                    "state": s_slug, "state_name": s.get("name", s_slug),
                    "state_abbr": s.get("abbr", s_slug.upper()),
                    "county": c_slug, "county_name": c.get("name", c_slug),
                    "city": city_slug, "city_name": city.get("name", city_slug),
                })
    return out


def page_path(market, treatment_slug):
    return f"{market['state']}/{market['county']}/{market['city']}/{treatment_slug}"


def page_url(market, treatment_slug):
    return f"/{page_path(market, treatment_slug)}/"


def load_state():
    try:                                            # fail safe: any problem => paused
        return json.loads(STATE_PATH.read_text()).get("state", "paused")
    except Exception:
        return "paused"


def month_tokens_used():
    try:
        ledger = json.loads(LEDGER_PATH.read_text())
        return ledger.get(datetime.date.today().strftime("%Y-%m"), {}).get("tokens", 0)
    except Exception:
        return 0


def stop(reason):
    print(f"[builder] STOP: {reason}")
    sys.exit(0)


def quality_gate(page) -> bool:
    """ALL must hold or the page is skipped. Never lower the gate to hit a count."""
    flags = page.get("page_flags", {})
    if not (flags.get("has_consent_form") and flags.get("has_schema_markup")):
        return False
    for c in page.get("clinics", []):
        if not c.get("has_real_clinic_data"):
            return False
        if c.get("uses_scraped_review_text"):
            return False
        if c.get("has_before_after") and not c.get("before_after_consent"):
            return False
    return True


def _field_present(raw_clinic, field):
    if field == "treatments":
        return bool(raw_clinic.get("treatments"))
    if field == "rating":
        return raw_clinic.get("rating") is not None
    if field == "price":
        return bool(raw_clinic.get("starting_prices_usd") or raw_clinic.get("starting_price_usd"))
    return bool(raw_clinic.get(field))


def listing_missing_fields(raw_clinic, required_fields):
    """Required fields this listing is missing (empty/None). No imputation."""
    return [f for f in (required_fields or []) if not _field_present(raw_clinic, f)]


def load_clinics():
    """Read the flat clinic list the prospector writes into data/prospector/*.json.
    Real records only; nothing fabricated. Returns [] if absent/empty."""
    clinics = []
    if not PROSPECTOR_DIR.exists():
        return clinics
    for f in sorted(PROSPECTOR_DIR.glob("*.json")):
        try:
            data = json.loads(f.read_text())
        except Exception as e:
            print(f"[builder] WARN: could not parse {f.name}: {e}")
            continue
        clinics.extend(data if isinstance(data, list) else [data])
    return clinics


def _starting_price(clinic, treatment_slug):
    prices = clinic.get("starting_prices_usd")
    if isinstance(prices, dict):
        return prices.get(treatment_slug)
    return clinic.get("starting_price_usd")


def _format_phone(phone):
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[0:3]}) {digits[3:6]}-{digits[6:]}"
    return phone


def _google_listing_url(clinic):
    explicit = clinic.get("google_listing_url")
    if explicit:
        return explicit
    query = " ".join(p for p in (clinic.get("name"), clinic.get("address")) if p)
    if not query:
        return None
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(query)


def _clinic_for_page(clinic, treatment_slug):
    """Shape one clinic for the template + quality gate. Gate flags ride through verbatim."""
    return {
        "slug": clinic.get("slug"),
        "name": clinic.get("name"),
        "neighborhood": clinic.get("neighborhood_name")
            or NEIGHBORHOOD_NAMES.get(clinic.get("neighborhood"), clinic.get("neighborhood")),
        "address": clinic.get("address"),
        "phone": clinic.get("phone"),
        "phone_display": _format_phone(clinic.get("phone")),
        "email": clinic.get("email"),
        "booking_url": clinic.get("booking_url"),
        "google_listing_url": _google_listing_url(clinic),
        "treatments_offered": [
            TREATMENT_NAMES.get(t, t.replace("-", " ").title())
            for t in (clinic.get("treatments") or [])
        ],
        "rating": clinic.get("rating"),
        "review_count": clinic.get("review_count"),
        "rating_source": clinic.get("rating_source"),
        "starting_price_usd": _starting_price(clinic, treatment_slug),
        "price_unit": TREATMENT_UNITS.get(treatment_slug) if _starting_price(clinic, treatment_slug) is not None else None,
        "languages": clinic.get("languages", []),
        # Flat-placement monetization fields (all operator-set, never builder-inferred).
        # featured_tier > 0 = paid flat placement; never tied to per-patient value.
        "featured_tier": clinic.get("featured_tier", 0),
        # campaigns_prospect: flag routes to Bonalta Campaigns CRM pipeline (stub).
        # Triggered by placement purchase, NOT lead count.
        "campaigns_prospect": bool(clinic.get("campaigns_prospect", False)),
        # placement_tier: null=organic; "standard"|"premium"=flat placement subscriber.
        "placement_tier": clinic.get("placement_tier"),
        # sponsored: True means all outbound links from this clinic must carry rel="sponsored".
        "sponsored": bool(clinic.get("featured_tier", 0) or clinic.get("placement_tier")),
        # Free inquiry routing: booking_url and phone are always free for patients.
        # The lead form forwards inquiries to the clinic at no charge — see monetization_policy.json.
        "last_verified": clinic.get("last_verified"),
        "sources": clinic.get("sources"),
        "has_real_clinic_data": clinic.get("has_real_clinic_data", False),
        "uses_scraped_review_text": clinic.get("uses_scraped_review_text", False),
        "has_before_after": clinic.get("has_before_after", False),
        "before_after_consent": clinic.get("before_after_consent", False),
        # Plastic-surgery vertical: surgeons performing THIS procedure at this practice.
        # The rating shown above is the CLINIC's; surgeons carry only as-stated credentials.
        "surgeons": _surgeons_for(clinic.get("slug"), treatment_slug),
        # Nearest-provider fallback (empty-city pages): the clinic's real home city + distance.
        "nearby_city_name": clinic.get("_nearby_city_name"),
        "nearby_distance_mi": clinic.get("_nearby_distance_mi"),
    }


# ============================================================================
# Provider ranking — Bayesian Beta-posterior lower bound (exact Beta quantile).
#
# We model each provider's "true quality" as a Beta posterior over p = rating/5,
# with a skeptical prior, then rank by the lower bound of that posterior. This does
# NOT collapse at perfect ratings the way a frequentist proportion does — a thin 5.0
# is pulled toward the prior and loses to a proven 4.9. The prior is an EDITORIAL
# skepticism dial; it is a fixed constant and is NEVER derived from the listing data
# (which is 5.0-inflated — deriving the prior from it would defeat the purpose).
# ----------------------------------------------------------------------------
PRIOR_MEAN = 0.90              # = 4.5 stars. Skepticism dial. FIXED — never auto-computed.
PRIOR_STRENGTH = 50           # prior pseudo-reviews
CONF_LEVEL = 0.05             # lower-bound quantile (5th percentile of the posterior)
MIN_REVIEWS_FOR_BADGE = 25    # "Top Rated" badge requires at least this many reviews
a0 = PRIOR_STRENGTH * PRIOR_MEAN          # = 45
b0 = PRIOR_STRENGTH * (1 - PRIOR_MEAN)    # = 5


def _provider_score(c):
    """Bayesian Beta-posterior lower bound for a provider. Computed once and memoized
    on the record (the score is intrinsic to rating+count, identical on every page).

    Unrated / missing -> -1.0 (sorts to the BOTTOM; never inherits the prior)."""
    if "_rank_score" in c:
        return c["_rank_score"]
    r = c.get("rating")
    n = c.get("review_count")
    if n in (None, 0) or r is None:
        c["_rank_score"] = -1.0
        return -1.0
    p = r / 5.0
    a = a0 + n * p
    b = b0 + n * (1.0 - p)
    score = float(scipy_beta.ppf(CONF_LEVEL, a, b))   # exact Beta quantile — NOT a normal approx
    c["_rank_score"] = score
    return score


def rank_providers(providers):
    """THE canonical ordering for EVERY ORGANIC provider list in Octoru.

    Orders the ORGANIC list only. It neither overrides nor is overridden by paid
    placement — Featured/paid listings are pinned + labeled separately by the caller.
    Never re-sort a provider list elsewhere; always order through this function.

    Deterministic for SEO stability (pages must not reshuffle across rebuilds):
      sort key = (score DESC, review_count DESC, slug/place-id ASC)
    """
    return sorted(
        providers,
        key=lambda c: (
            -_provider_score(c),
            -(c.get("review_count") or 0),
            (c.get("slug") or c.get("name") or "").lower(),
        ),
    )


def _assemble_page(treatment_slug, market, clinics, all_county_clinics=None,
                   category=DEFAULT_CATEGORY, fallback=False):
    """Group real clinics into one treatment x city page. Differentiation comes from
    the real clinics + market-specific context, not boilerplate.

    fallback=True builds a nearest-provider page for a city with NO local providers:
    the caller's distance order is preserved (no Beta ranking, no Featured pinning, no
    Top Rated badge — these providers are not located in this city)."""
    t_name = TREATMENT_NAMES.get(treatment_slug, treatment_slug.replace("-", " ").title())
    city_name = market["city_name"]

    top_ranked_id = None
    if not fallback:
        # Placement is handled SEPARATELY from organic ranking. Paid Featured listings are
        # pinned on top (slot-capped, labeled "Featured"); overflow beyond the cap is demoted
        # to organic. rank_providers() then orders the organic list by the Beta-posterior
        # lower bound — it neither overrides nor is overridden by placement.
        featured = [c for c in clinics if c.get("featured_tier", 0) > 0]
        organic = [c for c in clinics if c.get("featured_tier", 0) == 0]
        featured_pinned = featured[:MAX_FEATURED_PER_PAGE]
        overflow = [{**c, "featured_tier": 0, "sponsored": bool(c.get("placement_tier"))}
                    for c in featured[MAX_FEATURED_PER_PAGE:]]
        featured_pinned = rank_providers(featured_pinned)          # stable order among Featured
        organic_ranked = rank_providers(organic + overflow)        # the canonical organic order
        clinics = featured_pinned + organic_ranked

        # "Top Rated" badge — the #1 ORGANIC provider ONLY, and only if it has at least
        # MIN_REVIEWS_FOR_BADGE reviews. Earned by the formula; NEVER assigned to a paid
        # listing. If the #1 organic has too few reviews, no badge is shown at all.
        if organic_ranked:
            top = organic_ranked[0]
            if (top.get("review_count") or 0) >= MIN_REVIEWS_FOR_BADGE:
                top_ranked_id = top.get("slug") or top.get("name")

    n = len(clinics)
    unit = TREATMENT_UNITS.get(treatment_slug, "")
    prices = sorted({p for c in clinics if (p := _starting_price(c, treatment_slug)) is not None})

    # Rich human-sounding intro with neighbourhood context and real data
    intro = _build_intro(treatment_slug, market, clinics, prices, all_county_clinics,
                         category=category, fallback=fallback)

    # Meta description optimised for SERP click-through
    provider_word = "provider" if n == 1 else "providers"
    price_hint = f" Botox from ${prices[0]}/{unit}" if treatment_slug == "botox" and prices else ""
    if fallback:
        meta = (f"No {t_name.lower()} providers in {city_name}, FL yet — compare the nearest "
                f"board-certified options nearby by rating and distance, and book a consultation.")
    else:
        meta = (
            f"{n} verified {t_name.lower()} {provider_word} in {city_name}, FL.{price_hint} "
            f"Compare addresses, real prices and Google ratings — and book direct."
        )

    priced_clinics = [c for c in clinics if _starting_price(c, treatment_slug) is not None]
    cost = {
        "has_prices": bool(priced_clinics),
        "low": prices[0] if prices else None,
        "high": prices[-1] if prices else None,
        "unit": unit,
        "count_priced": len(priced_clinics),
        "count_total": len(clinics),
        "coverage_label": f"{len(priced_clinics)} of {len(clinics)} {'provider lists' if len(priced_clinics)==1 else 'providers list'} pricing",
    }
    verified_dates = [c.get("last_verified") for c in clinics if c.get("last_verified")]
    updated = max(verified_dates) if verified_dates else datetime.date.today().isoformat()

    # FAQs — generated from real data, safe for FAQPage schema
    faqs = _generate_faqs(treatment_slug, market, clinics, prices)

    return {
        "category": category,
        "fallback": fallback,
        "treatment": {"slug": treatment_slug, "name": t_name},
        "neighborhood": {"slug": market["city"], "name": city_name},
        "city": market["state_abbr"],
        "geo": market,
        "path": page_path(market, treatment_slug),
        "page_flags": {"has_consent_form": True, "has_schema_markup": True},
        "meta_description": meta,
        "intro": intro,
        "cost": cost,
        "guidance": TREATMENT_GUIDANCE.get(treatment_slug),
        "faqs": faqs,
        "updated": updated,
        "clinics": [
            {**_clinic_for_page(c, treatment_slug),
             "top_ranked": (c.get("slug") or c.get("name")) == top_ranked_id}
            for c in clinics
        ],
    }


def _clinic_in_market(clinic, market):
    """A clinic belongs to a market if its city slug matches; county/state, if the record
    carries them, must also match (future-proof disambiguation for national data)."""
    if clinic.get("neighborhood") != market["city"]:
        return False
    if clinic.get("county") and clinic["county"] != market["county"]:
        return False
    if clinic.get("state") and clinic["state"] != market["state"]:
        return False
    return True


def page_hold_reason(page, page_reqs):
    if not page_reqs:
        return None
    min_listings = page_reqs.get("min_listings", 0)
    if len(page.get("clinics", [])) < min_listings:
        return f"only {len(page['clinics'])} qualifying listing(s) (< {min_listings})"
    if page_reqs.get("require_cost_block") and not page.get("cost"):
        return "missing cost block"
    if page_reqs.get("require_guidance") and not page.get("guidance"):
        return "missing treatment guidance"
    return None


def _haversine_mi(a, b):
    """Great-circle distance in miles between two (lat, lng) pairs."""
    lat1, lng1 = a
    lat2, lng2 = b
    R = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def _nearest_fallback_pages(category, treatments, clinics, req_fields, page_reqs,
                            built_keys, max_nearby=5, max_distance_mi=40):
    """Demand-capture pages for cities with NO local provider for a procedure.

    For each active city x treatment that did NOT build a real page AND has zero
    qualifying LOCAL providers, build a page showing the nearest qualifying providers
    from OTHER cities (ordered by distance, then Beta score), with an honest empty-state
    note. Requires city centroids (data/places.json); cities without a centroid are
    skipped. These nearby providers also appear on their own home-city pages — that's
    intended (a referral), so they are NOT de-duplicated or claimed.

    A distance cap (max_distance_mi) keeps these pages useful and limits near-duplication:
    if the nearest qualifying provider is farther than the cap, no fallback page is built
    (a provider an hour+ away is not a real local option, and a city pointed only at
    far providers would just near-duplicate closer cities' pages)."""
    pages = []
    # Pre-qualify candidates once per treatment: real, rated, has a centroid.
    cands_by_t = {}
    for t in treatments:
        cs = []
        for c in clinics:
            if t not in (c.get("treatments") or []):
                continue
            if listing_missing_fields(c, req_fields):
                continue
            nb = c.get("neighborhood")
            if nb not in CITY_LATLNG:
                continue
            cs.append(c)
        cands_by_t[t] = cs

    for market in active_markets():
        city = market["city"]
        if city not in CITY_LATLNG:
            continue
        origin = CITY_LATLNG[city]
        for t in treatments:
            key = (market["state"], market["county"], city, t)
            if key in built_keys:
                continue
            # Only fall back when there are ZERO qualifying LOCAL providers.
            local = [c for c in clinics
                     if _clinic_in_market(c, market) and t in (c.get("treatments") or [])
                     and not listing_missing_fields(c, req_fields)]
            if local:
                continue
            scored = []
            for c in cands_by_t.get(t, []):
                if c.get("neighborhood") == city:
                    continue
                d = _haversine_mi(origin, CITY_LATLNG[c["neighborhood"]])
                if d > max_distance_mi:
                    continue
                scored.append((d, c))
            if not scored:
                continue
            scored.sort(key=lambda dc: (dc[0], -_provider_score(dc[1])))
            chosen = []
            for d, c in scored[:max_nearby]:
                cc = dict(c)
                cc["_nearby_distance_mi"] = round(d)
                cc["_nearby_city_name"] = c.get("neighborhood_name") \
                    or NEIGHBORHOOD_NAMES.get(c.get("neighborhood"), (c.get("neighborhood") or "").replace("-", " ").title())
                chosen.append(cc)
            page = _assemble_page(t, market, chosen, all_county_clinics=None,
                                  category=category, fallback=True)
            if page_hold_reason(page, page_reqs):
                continue
            pages.append(page)
    return pages


def fetch_pages(spec=None, enforce=False):
    """Build pages for EVERY category in seed_scope.categories across the shared
    neighborhood scope, applying per-category completeness overrides. Returns
    (pages, report). Each category is independent (disjoint treatment slugs + clinic
    sets), so categories are processed separately and their pages concatenated.

    A category with no qualifying clinics builds nothing and is recorded in
    report["empty_categories"] (surfaced to needs_human.json by main()). The builder
    NEVER fabricates providers to fill an empty category."""
    all_clinics = load_clinics()
    report = {
        "excluded_listings": [], "held_pages": [],
        "rolled_up": [],   # {clinic, from_place, to_place, treatment}
        "deduped": [],     # {clinic, kept_at, not_shown_at}
        "empty_categories": [],
        "categories_built": [],
    }
    if not all_clinics:
        print(f"[builder] no prospector data in {PROSPECTOR_DIR} — nothing to build.")
        return [], report

    req_fields = (spec or {}).get("min_listing_fields") or []
    pages = []
    for category in _categories_config():
        treatments = _category_treatments(category)
        page_reqs = _category_page_reqs(spec, category)
        cat_clinics = [c for c in all_clinics if _clinic_category(c) == category]
        has_match = any(t in (c.get("treatments") or []) for c in cat_clinics for t in treatments)
        if not treatments or not cat_clinics or not has_match:
            report["empty_categories"].append(category)
            print(f"[builder] category '{category}': no qualifying clinics in data/prospector "
                  f"(clinics={len(cat_clinics)}, treatments={len(treatments)}) — building nothing, "
                  f"surfacing to needs_human.")
            continue
        cat_pages = _fetch_category_pages(category, treatments, req_fields, page_reqs,
                                          enforce, cat_clinics, report)
        # Nearest-provider fallback (plastic-surgery only): under-served cities with NO local
        # provider still get a page showing the nearest board-certified options + honest note.
        fb_pages = []
        if category == "plastic-surgery" and enforce:
            built_keys = {(p["geo"]["state"], p["geo"]["county"], p["geo"]["city"], p["treatment"]["slug"])
                          for p in cat_pages}
            fb_pages = _nearest_fallback_pages(category, treatments, cat_clinics, req_fields,
                                               page_reqs, built_keys)
            report.setdefault("nearest_fallback_pages", 0)
            report["nearest_fallback_pages"] += len(fb_pages)
        report["categories_built"].append({"category": category, "pages": len(cat_pages),
                                           "fallback_pages": len(fb_pages), "clinics": len(cat_clinics)})
        print(f"[builder] category '{category}': {len(cat_pages)} page(s) from "
              f"{len(cat_clinics)} clinic(s), min_listings={page_reqs.get('min_listings', 0)}"
              + (f" (+{len(fb_pages)} nearest-provider fallback page(s))" if fb_pages else ""))
        pages.extend(cat_pages)
        pages.extend(fb_pages)
    return pages, report


def _fetch_category_pages(category, treatments, req_fields, page_reqs, enforce, clinics, report):
    """Core builder for ONE category: treatment x place pages with completeness gating
    and place-taxonomy rollup/de-dup.

    Place taxonomy (data/places.json):
    - A clinic appears at its MOST SPECIFIC qualifying place (neighborhood > CDP > municipality).
    - De-duplication: once a clinic is assigned to a neighborhood/CDP page, it is NOT included
      on the parent municipality page (prevents the same clinic appearing on both Brickell and
      Miami pages).
    - Rollup: if a neighborhood/CDP treatment page is below min_page_requirements AND the place
      has a parent_place, its qualifying clinics are rolled up to the parent place. The thin
      neighborhood page is NOT built; the parent page gains those clinics.

    Listing below min_listing_fields is excluded; page below min_page_requirements is HELD
    (unless rollup to parent is possible). Dry-run (enforce=False) reports only.
    rollup_pool/claimed are category-local (clinic sets are disjoint across categories)."""
    min_listings = page_reqs.get("min_listings", 0)

    # Step 1: qualify clinics per market (apply field exclusions).
    def _qualify(matched, label):
        ok, excl = [], []
        for c in matched:
            miss = listing_missing_fields(c, req_fields)
            if miss:
                report["excluded_listings"].append({"clinic": c.get("name"), "page": label, "missing": miss})
                print(f"[builder] listing {'excluded' if enforce else 'would-exclude (dry-run)'} "
                      f"(missing {miss}): {c.get('name')} on {label}")
                excl.append(c)
            else:
                ok.append(c)
        return ok if enforce else matched  # dry-run: use all

    # Step 2: collect rollup pools keyed by (parent_slug, county, state, treatment).
    rollup_pool = {}   # (parent_city, county, state, treatment) -> [clinics]
    # Track which clinic slugs have been "claimed" by a specific place (for de-dup).
    claimed = {}       # clinic_slug -> city_slug (the place that will show this clinic)

    pages = []
    markets = list(active_markets())

    # First pass: process neighborhoods/CDPs to see what rolls up.
    # Municipalities are owned exclusively by the second pass — skip them here, or
    # they would be appended twice (duplicate sitemap URLs, double-counted hubs).
    for market in markets:
        city = market["city"]
        place_type = _place_type(city)
        if place_type == "municipality":
            continue
        parent = _parent_slug(city)
        is_child = place_type in ("neighborhood", "cdp") and parent

        for t in treatments:
            matched = [c for c in clinics if _clinic_in_market(c, market) and t in (c.get("treatments") or [])]
            if not matched:
                continue
            label = f"{t}@{market['state']}/{market['county']}/{city}"
            use = _qualify(matched, label)
            if not use:
                continue
            county_clinics = [c for c in clinics if (c.get("county") or "miami-dade") == market["county"]]
            page = _assemble_page(t, market, use, all_county_clinics=county_clinics, category=category)
            reason = page_hold_reason(page, page_reqs) if enforce else None
            # For dry-run without enforce, only roll up if the page would be GENUINELY thin.
            would_be_thin = len(use) < min_listings if min_listings else False

            if is_child and (reason or would_be_thin):
                # Roll up to parent instead of shipping a thin neighborhood page.
                key = (parent, market["county"], market["state"], t)
                rollup_pool.setdefault(key, []).extend(use)
                for c in use:
                    slug = c.get("slug") or c.get("name")
                    report["rolled_up"].append({
                        "clinic": c.get("name"), "from_place": city,
                        "to_place": parent, "treatment": t
                    })
                    claimed[slug] = parent  # will appear on parent, not on city page
                reason_str = reason or f"thin ({len(use)} < {min_listings})"
                report["held_pages"].append({"page": label, "reason": f"rolled up to {parent}: {reason_str}"})
                print(f"[builder] {'HOLD→rollup' if enforce else 'would-HOLD→rollup (dry-run)'} {label}: rolled to {parent}")
            else:
                if reason:
                    report["held_pages"].append({"page": label, "reason": reason})
                    print(f"[builder] {'HELD' if enforce else 'would-HOLD (dry-run)'} {label}: {reason}")
                    if enforce:
                        continue
                # Claim these clinics at this specific place.
                for c in use:
                    slug = c.get("slug") or c.get("name")
                    if slug not in claimed:
                        claimed[slug] = city
                pages.append(page)

    # Ensure every parent place that received rolled-up clinics exists as a market.
    # Parent places (e.g. "miami", "miami-beach") may not be in the config's neighborhoods
    # list; we synthesise a market entry for them from places.json so rollup pages build.
    existing_cities = {m["city"] for m in markets}
    for (parent_city, county, state, _t) in rollup_pool:
        if parent_city not in existing_cities:
            p_data = PLACES_BY_SLUG.get(parent_city, {})
            markets.append({
                "state": state, "state_name": "Florida",
                "state_abbr": state.upper() if len(state) <= 3 else "FL",
                "county": county,
                "county_name": COUNTY_NAMES.get(county, county.replace("-", " ").title()),
                "city": parent_city,
                "city_name": p_data.get("name", parent_city.replace("-", " ").title()),
            })
            existing_cities.add(parent_city)
            print(f"[builder] activated rollup target: {parent_city} (received clinics from children)")

    # Second pass: municipality pages. Only include clinics NOT already claimed by a child place.
    for market in markets:
        city = market["city"]
        place_type = _place_type(city)
        is_parent = place_type == "municipality"
        if not is_parent:
            continue

        for t in treatments:
            # Base clinics: directly assigned to this municipality.
            direct = [c for c in clinics if _clinic_in_market(c, market) and t in (c.get("treatments") or [])]
            # Add any rolled-up clinics from child places.
            rolled = rollup_pool.get((city, market["county"], market["state"], t), [])
            for c in rolled:
                slug = c.get("slug") or c.get("name")
                report["rolled_up"]  # already recorded above

            # De-dup: exclude direct clinics already claimed by a child place.
            deduped_direct = []
            for c in direct:
                slug = c.get("slug") or c.get("name")
                if claimed.get(slug, city) != city:
                    # Claimed by a child neighborhood — skip from municipality page.
                    report["deduped"].append({
                        "clinic": c.get("name"), "kept_at": claimed[slug], "not_shown_at": city
                    })
                    print(f"[builder] dedup: {c.get('name')} kept at {claimed[slug]}, not shown at {city}")
                else:
                    deduped_direct.append(c)

            all_clinics = deduped_direct + rolled
            if not all_clinics:
                continue
            label = f"{t}@{market['state']}/{market['county']}/{city}"
            use = _qualify(all_clinics, label)
            if not use:
                continue
            county_clinics = [c for c in clinics if (c.get("county") or "miami-dade") == market["county"]]
            page = _assemble_page(t, market, use, all_county_clinics=county_clinics, category=category)
            reason = page_hold_reason(page, page_reqs) if enforce else None
            if reason:
                report["held_pages"].append({"page": label, "reason": reason})
                print(f"[builder] {'HELD' if enforce else 'would-HOLD (dry-run)'} {label}: {reason}")
                if enforce:
                    continue
            for c in use:
                slug = c.get("slug") or c.get("name")
                if slug not in claimed:
                    claimed[slug] = city
            pages.append(page)

    return pages


def compute_empty_fields(pages):
    seen, price_missing, price_total = {}, 0, 0
    for p in pages:
        for c in p["clinics"]:
            seen[c.get("name")] = c
            price_total += 1
            if not c.get("starting_price_usd"):
                price_missing += 1
    cl = list(seen.values())
    return {
        "unique_clinics": len(cl),
        "missing_phone": sum(1 for c in cl if not c.get("phone")),
        "missing_email": sum(1 for c in cl if not c.get("email")),
        "missing_address": sum(1 for c in cl if not c.get("address")),
        "missing_booking_url": sum(1 for c in cl if not c.get("booking_url")),
        "price_empty_state_listings": price_missing,
        "price_total_listings": price_total,
    }


def page_summary(page):
    m = page["geo"]
    t = page["treatment"]["slug"]
    prices = [c["starting_price_usd"] for c in page.get("clinics", []) if c.get("starting_price_usd")]
    return {
        "treatment_slug": t, "treatment_name": page["treatment"]["name"],
        "state": m["state"], "state_name": m["state_name"], "state_abbr": m["state_abbr"],
        "county": m["county"], "county_name": m["county_name"],
        "city": m["city"], "city_name": m["city_name"],
        "url": page_url(m, t),
        "category": page.get("category", DEFAULT_CATEGORY),
        "fallback": bool(page.get("fallback")),
        "n_clinics": len(page.get("clinics", [])),
        "from_price": min(prices) if prices else None,
        "price_unit": TREATMENT_UNITS.get(t) if prices else None,
    }


def page_links(page, all_pages):
    """Breadcrumb (Home > State > County > City > Treatment) + cross-links to related
    canonical pages (same treatment in sibling cities; other treatments in this city)."""
    m = page["geo"]
    t = page["treatment"]["slug"]
    t_name = page["treatment"]["name"]
    exists = {(p["geo"]["state"], p["geo"]["county"], p["geo"]["city"], p["treatment"]["slug"]) for p in all_pages}
    tnames = {p["treatment"]["slug"]: p["treatment"]["name"] for p in all_pages}
    cnames = {(p["geo"]["state"], p["geo"]["county"], p["geo"]["city"]): p["geo"]["city_name"] for p in all_pages}

    same_treatment = []
    for (st, co, ci, tr) in sorted(exists):
        if tr == t and co == m["county"] and ci != m["city"]:
            same_treatment.append({"name": cnames[(st, co, ci)], "url": f"/{st}/{co}/{ci}/{tr}/"})
    other_treatments = []
    # Cross-link only within the same vertical (a surgery page links other surgery
    # procedures in this city; a med-spa page links other med-spa treatments).
    for tr in _category_treatments(page.get("category", DEFAULT_CATEGORY)):
        if tr != t and (m["state"], m["county"], m["city"], tr) in exists:
            other_treatments.append({"name": tnames[tr], "url": f"/{m['state']}/{m['county']}/{m['city']}/{tr}/"})

    breadcrumb = [
        {"name": "Home", "url": "/"},
        {"name": m["state_name"], "url": f"/{m['state']}/"},
        {"name": m["county_name"], "url": f"/{m['state']}/{m['county']}/"},
        {"name": m["city_name"], "url": f"/{m['state']}/{m['county']}/{m['city']}/"},
        {"name": f"{t_name} in {m['city_name']}", "url": page_url(m, t)},
    ]
    return {"same_treatment": same_treatment, "other_treatments": other_treatments,
            "breadcrumb": breadcrumb, "site_url": SITE_URL,
            "city_label": f"{m['city_name']}, {m['state_abbr']}"}


def _write(path_rel, html):
    out = GENERATED / path_rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    return out


def render(page, links=None):
    ctx = dict(page)
    if links:
        ctx.update(links)
    ctx.setdefault("last_updated", datetime.date.today().isoformat())
    ctx.setdefault("site_url", SITE_URL)
    html = env.get_template("treatment-page.html.j2").render(**ctx)
    return _write(f"{page['path']}/index.html", html)


def render_hub(title, subtitle, breadcrumb, cards, rel_path, intro=None):
    html = env.get_template("hub.html.j2").render(
        title=title, subtitle=subtitle, breadcrumb=breadcrumb, cards=cards, intro=intro,
        site_url=SITE_URL, last_updated=datetime.date.today().isoformat())
    return _write(f"{rel_path}/index.html" if rel_path else "index_hub.html", html)


def render_hubs(summaries):
    """State, county, and city hub pages from the built listing summaries."""
    states = {}
    for s in summaries:
        states.setdefault(s["state"], {"name": s["state_name"], "counties": {}})
        co = states[s["state"]]["counties"].setdefault(s["county"], {"name": s["county_name"], "cities": {}})
        ci = co["cities"].setdefault(s["city"], {"name": s["city_name"], "pages": []})
        ci["pages"].append(s)

    for st, sdata in states.items():
        # city hubs
        for co, cdata in sdata["counties"].items():
            for ci, cidata in cdata["cities"].items():
                cards = [{"title": p["treatment_name"], "sub": f"{p['n_clinics']} provider" + ("" if p["n_clinics"] == 1 else "s"),
                          "url": p["url"],
                          "chip": (f"from ${p['from_price']} {p['price_unit']}" if p["from_price"] else None)}
                         for p in sorted(cidata["pages"], key=lambda x: x["treatment_name"])]
                bc = [{"name": "Home", "url": "/"}, {"name": sdata["name"], "url": f"/{st}/"},
                      {"name": cdata["name"], "url": f"/{st}/{co}/"},
                      {"name": cidata["name"], "url": f"/{st}/{co}/{ci}/"}]
                render_hub(f"Health & wellness in {cidata['name']}, {sdata['name']}",
                           f"{len(cidata['pages'])} treatment guides for {cidata['name']}", bc, cards, f"{st}/{co}/{ci}")
            # county hub
            ccards = [{"title": cidata["name"], "sub": f"{len(cidata['pages'])} treatment" + ("" if len(cidata['pages']) == 1 else "s"),
                       "url": f"/{st}/{co}/{ci}/", "chip": None}
                      for ci, cidata in sorted(cdata["cities"].items(), key=lambda kv: kv[1]["name"])]
            bc = [{"name": "Home", "url": "/"}, {"name": sdata["name"], "url": f"/{st}/"}, {"name": cdata["name"], "url": f"/{st}/{co}/"}]
            render_hub(f"Health & wellness in {cdata['name']} County, {sdata['name']}",
                       f"{len(cdata['cities'])} cities", bc, ccards, f"{st}/{co}")
        # state hub
        scards = [{"title": cdata["name"] + " County", "sub": f"{len(cdata['cities'])} cities",
                   "url": f"/{st}/{co}/", "chip": None}
                  for co, cdata in sorted(sdata["counties"].items(), key=lambda kv: kv[1]["name"])]
        bc = [{"name": "Home", "url": "/"}, {"name": sdata["name"], "url": f"/{st}/"}]
        render_hub(f"Health & wellness directory — {sdata['name']}", f"{len(sdata['counties'])} counties", bc, scards, st)
    return states


COUNTY_ORDER = ["miami-dade", "broward", "palm-beach"]


def render_index(summaries):
    """Homepage (design/landing): real stats, real county->city grid (with real treatment
    counts), real treatment cards (real prices or honest 'varies'), and the geolocation
    nearest-city set built from real covered cities. Renders templates/home.html.j2."""
    if not summaries:
        return None
    # Homepage aggregates use REAL coverage only (exclude nearest-provider fallback pages):
    # fallback pages repeat the same nearby providers across many empty cities, so counting
    # them would inflate "listings" and make every city look identical. Fallback pages still
    # ship (sitemap, direct nav, city hubs) — they just don't drive the homepage grid/stats.
    real = [s for s in summaries if not s.get("fallback")] or summaries
    counties = {}  # (state, county) -> {name, state_name, cities}
    for s in real:
        key = (s["state"], s["county"])
        c = counties.setdefault(key, {"name": s["county_name"], "state_name": s["state_name"], "cities": {}})
        ci = c["cities"].setdefault(s["city"], {
            "name": s["city_name"], "url": f'/{s["state"]}/{s["county"]}/{s["city"]}/',
            "treats": set(), "cats": set()})
        ci["treats"].add(s["treatment_slug"])
        ci["cats"].add(s.get("category", DEFAULT_CATEGORY))

    order = sorted(counties, key=lambda k: (COUNTY_ORDER.index(k[1]) if k[1] in COUNTY_ORDER else 99, k[1]))
    groups = []
    for key in order:
        c = counties[key]
        cities = [{"name": v["name"], "url": v["url"], "n_treatments": len(v["treats"]),
                   "data_treatments": " ".join(sorted(v["treats"])),
                   "data_cats": " ".join(sorted(v["cats"]))}
                  for _, v in sorted(c["cities"].items(), key=lambda kv: kv[1]["name"])]
        groups.append({"slug": key[1], "short_name": c["name"],
                       "name": f'{c["name"]}, {c["state_name"]}', "n_cities": len(cities), "cities": cities})

    stats = {
        "listings": sum(s["n_clinics"] for s in real),
        "cities": len({(s["state"], s["county"], s["city"]) for s in real}),
        "counties": len(counties),
    }

    # geolocation nearest-city set: covered cities that have a known centroid
    city_url = {s["city"]: f'/{s["state"]}/{s["county"]}/{s["city"]}/' for s in real}
    city_name = {s["city"]: s["city_name"] for s in real}
    geo_cities = [{"name": city_name[c], "slug": c, "lat": lat, "lng": lng, "url": city_url[c]}
                  for c, (lat, lng) in CITY_LATLNG.items() if c in city_url]

    # Top searches: real treatment x city combos ranked by clinic count.
    # Always resolve county via CITY_COUNTY (authoritative) before falling back to
    # the clinic record — clinics.json may omit county for older records.
    all_clinics = load_clinics()
    from collections import defaultdict as _dd
    combos = _dd(list)
    for c in all_clinics:
        nb = c.get("neighborhood","")
        # Authoritative county lookup: CITY_COUNTY > record field > "miami-dade"
        co = CITY_COUNTY.get(nb) or c.get("county") or "miami-dade"
        st = c.get("state","fl") or "fl"
        for t in (c.get("treatments") or []):
            combos[(st, co, nb, t)].append(1)
    top_searches = []
    for (st, co, nb, t), hits in sorted(combos.items(), key=lambda x: -len(x[1])):
        if len(top_searches) >= 8: break
        city_name = NEIGHBORHOOD_NAMES.get(nb, nb.replace("-"," ").title())
        treat_name = TREATMENT_NAMES.get(t, t)
        top_searches.append({"label": f"{treat_name} in {city_name}",
                              "url": f"/{st}/{co}/{nb}/{t}/"})

    # Category-driven treatment cards. Every config category with REAL built coverage gets
    # an equal section; treatment cards link to #areas and filter the city grid (see home JS).
    # New verticals added to config + data surface here automatically — no template change.
    built_by_cat = {}
    for s in real:
        built_by_cat.setdefault(s.get("category", DEFAULT_CATEGORY), set()).add(s["treatment_slug"])
    categories = []
    for cat in _categories_config():
        built = built_by_cat.get(cat, set())
        treats = [t for t in _category_treatments(cat) if t in built]
        if not treats:
            continue
        cat_clinics = [c for c in all_clinics if _clinic_category(c) == cat]
        cat_real = [s for s in real if s.get("category", DEFAULT_CATEGORY) == cat]
        categories.append({
            "slug": cat,
            "name": _category_name(cat),
            "tagline": _category_tagline(cat),
            "noun": _category_noun(cat),
            "cards": treatment_cards(cat_clinics, treats),
            "n_cities": len({(s["state"], s["county"], s["city"]) for s in cat_real}),
            "n_listings": sum(s["n_clinics"] for s in cat_real),
        })
    category_names = [c["name"] for c in categories]

    # Avg rating for social proof
    ratings = [c["rating"] for c in all_clinics if c.get("rating")]
    avg_rating = round(sum(ratings)/len(ratings), 1) if ratings else None

    html = env.get_template("home.html.j2").render(
        groups=groups, stats=stats, categories=categories, category_names=category_names,
        top_searches=top_searches, avg_rating=avg_rating,
        geo_cities_json=json.dumps(geo_cities),
        last_updated=datetime.date.today().isoformat(), site_url=SITE_URL)
    return _write("index.html", html)


def render_claim():
    html = env.get_template("claim.html.j2").render(
        site_url=SITE_URL, lead_routing_target="crm:octoru-listing-claims",
        last_updated=datetime.date.today().isoformat())
    return _write("claim.html", html)


def render_advertise(summaries=None):
    """Placement / advertise page. Intake only — no card data on site.
    Checkout is Bonalta Payments hosted (gated). Routes interest to Campaigns CRM."""
    policy = {}
    try:
        policy = json.loads((ROOT / "data" / "monetization_policy.json").read_text())
    except Exception:
        pass
    sub = policy.get("placement_subscription") or {}
    clinics = load_clinics()
    ratings = [c["rating"] for c in clinics if c.get("rating")]
    avg_rating = round(sum(ratings)/len(ratings), 1) if ratings else None
    html = env.get_template("advertise.html.j2").render(
        site_url=SITE_URL,
        slot_cap=sub.get("slot_cap_per_page", 3),
        price_display=sub.get("price_display", "from $299 / month"),
        price_cancel=sub.get("price_cancel", "cancel anytime"),
        crm_pipeline=(policy.get("campaigns_upsell") or {}).get("crm_pipeline", "crm:octoru-campaigns-prospect"),
        total_clinics=len(clinics),
        total_pages=len(summaries) if summaries else 0,
        avg_rating=avg_rating,
        last_updated=datetime.date.today().isoformat())
    return _write("advertise.html", html)


def render_guides(pages):
    """Render a treatment cost guide page for every built listing page.
    URL: /{state}/{county}/{city}/{treatment}/guide/
    These pages target informational 'how much does X cost in Y' queries.
    They link back to the listing page for provider browsing."""
    guide_urls = []
    for page in pages:
        m = page["geo"]
        t = page["treatment"]["slug"]
        t_name = page["treatment"]["name"]
        city_name = page["neighborhood"]["name"]
        state_abbr = page["city"]
        prices = []
        if page.get("cost", {}).get("low") is not None:
            prices = list({page["cost"]["low"], page["cost"]["high"]} - {None})
            prices = sorted(set(prices))
        unit = TREATMENT_UNITS.get(t, "")
        price_display = (
            f"${prices[0]}–${prices[-1]} {unit}".strip() if len(prices) >= 2
            else (f"${prices[0]} {unit}".strip() if prices else None)
        )
        guide_path = f"{page['path']}/guide"
        listing_url = page_url(m, t)
        guide_url = f"/{guide_path}/"

        faqs = page.get("faqs", _generate_faqs(t, m, [], prices))
        ctx = NEIGHBORHOOD_CONTEXT.get(m["city"], "")

        html = env.get_template("guide.html.j2").render(
            treatment=page["treatment"],
            neighborhood=page["neighborhood"],
            city=state_abbr,
            geo=m,
            cost=page.get("cost", {}),
            price_display=price_display,
            unit=unit,
            faqs=faqs,
            guidance=TREATMENT_GUIDANCE.get(t, ""),
            neighborhood_context=ctx,
            listing_url=listing_url,
            guide_url=guide_url,
            n_clinics=len(page.get("clinics", [])),
            site_url=SITE_URL,
            last_updated=datetime.date.today().isoformat(),
            year=datetime.date.today().year,
        )
        _write(f"{guide_path}/index.html", html)
        guide_urls.append(guide_url)
    print(f"[builder] built {len(guide_urls)} guide pages")
    return guide_urls


def render_sitemap(summaries, guide_urls=None):
    urls = ["/", "/claim.html", "/advertise.html"]
    seen_hubs = set()
    for s in summaries:
        for hub in (f"/{s['state']}/", f"/{s['state']}/{s['county']}/", f"/{s['state']}/{s['county']}/{s['city']}/"):
            if hub not in seen_hubs:
                seen_hubs.add(hub); urls.append(hub)
        urls.append(s["url"])
    for gu in (guide_urls or []):
        urls.append(gu)
    today = datetime.date.today().isoformat()
    body = "\n".join(
        f"  <url><loc>{SITE_URL}{u}</loc><lastmod>{today}</lastmod></url>" for u in urls)
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "\n</urlset>\n"
    return _write("sitemap.xml", xml)


def integrity_scan():
    """Rating-integrity guards tied to the #1 risk (inflated / synthetic ratings).

    Per-row : any provider with rating >= 4.95 AND n >= 100 is flagged to
              needs_human.json ("implausibly perfect at volume — verify source").
    Corpus  : if the share of providers with rating >= 4.95 AND n >= 50 exceeds 20%,
              write a HALT-level flag ("ratings distribution implausible — likely
              synthetic, do not publish"). Uses >= 4.95 (never == 5.0) to avoid float misses.

    Writes results into state/needs_human.json idempotently (replaces the prior
    auto-generated integrity items). Returns (row_flags, corpus_share, halt)."""
    providers = [c for c in load_clinics() if c.get("rating") is not None]
    row_flags = [c for c in providers
                 if (c.get("rating") or 0) >= 4.95 and (c.get("review_count") or 0) >= 100]
    perfect_at_volume = [c for c in providers
                         if (c.get("rating") or 0) >= 4.95 and (c.get("review_count") or 0) >= 50]
    share = (len(perfect_at_volume) / len(providers)) if providers else 0.0
    halt = share > 0.20

    nh_path = ROOT / "state" / "needs_human.json"
    try:
        nh = json.loads(nh_path.read_text())
    except Exception:
        nh = {"items": [], "_resolved": []}
    managed = {"integrity-implausible-perfect-providers", "integrity-corpus-perfect-share"}
    # Preserve a human override across rebuilds. integrity_scan regenerates the corpus
    # item every run; without this, an operator's recorded decision to ship despite the
    # halt would be silently overwritten back to blocking on the next build.
    prior_override = next(
        (it.get("human_override") for it in nh.get("items", [])
         if it.get("id") == "integrity-corpus-perfect-share" and it.get("human_override")),
        None,
    )
    nh["items"] = [it for it in nh.get("items", []) if it.get("id") not in managed]

    if row_flags:
        nh["items"].insert(0, {
            "id": "integrity-implausible-perfect-providers",
            "opened_at": datetime.date.today().isoformat(), "opened_by": "builder",
            "blocking": False, "severity": "verify",
            "summary": f"{len(row_flags)} provider(s) rated >= 4.95 with >= 100 reviews — "
                       f"implausibly perfect at volume. Verify the source data.",
            "providers": [f"{c.get('name')} — {c.get('rating')} ({c.get('review_count')}) "
                          f"in {c.get('neighborhood')}" for c in row_flags],
        })
    if halt:
        item = {
            "id": "integrity-corpus-perfect-share",
            "opened_at": datetime.date.today().isoformat(), "opened_by": "builder",
            "blocking": True, "severity": "halt",
            "summary": "ratings distribution implausible — likely synthetic, do not publish.",
            "detail": f"{share:.1%} of providers are rated >= 4.95 with >= 50 reviews "
                      f"(threshold 20%). Investigate the ratings source before any deploy.",
        }
        if prior_override:
            # A human explicitly accepted this risk. Keep the flag visible for the audit
            # trail but stop it blocking, and carry the override forward verbatim.
            item["blocking"] = False
            item["summary"] = ("ratings distribution implausible — HUMAN OVERRIDE on file: "
                               "operator chose to ship anyway (see human_override).")
            item["human_override"] = prior_override
        nh["items"].insert(0, item)
    nh_path.write_text(json.dumps(nh, indent=2))
    return row_flags, share, halt, bool(prior_override)


def surface_category_gaps(empty_categories):
    """Record categories that are armed in config (seed_scope.categories) but have no
    qualifying clinics in data/prospector, so the operator knows the builder built
    nothing for them. Idempotent: manages 'vertical-empty-<cat>' items, clearing any
    that now have data. The builder NEVER fabricates providers to fill a gap."""
    nh_path = ROOT / "state" / "needs_human.json"
    try:
        nh = json.loads(nh_path.read_text())
    except Exception:
        nh = {"items": [], "_resolved": []}
    nh["items"] = [it for it in nh.get("items", [])
                   if not str(it.get("id", "")).startswith("vertical-empty-")]
    for cat in empty_categories:
        nh["items"].append({
            "id": f"vertical-empty-{cat}",
            "opened_at": datetime.date.today().isoformat(), "opened_by": "builder",
            "blocking": False, "severity": "operator-action-to-activate",
            "summary": f"Category '{cat}' is armed in config (seed_scope.categories.{cat}) "
                       f"but data/prospector has 0 qualifying '{cat}' clinics — the builder "
                       f"built nothing for it. Other categories built normally.",
            "operator_action": f"Add real '{cat}' provider data to data/prospector/ "
                               f"(records with category=\"{cat}\" and matching treatment slugs), "
                               f"then re-run the build. Do NOT fabricate providers.",
        })
    nh_path.write_text(json.dumps(nh, indent=2))
    return empty_categories


def main():
    state = load_state()
    if state in ("paused", "halted", "halted_technical"):
        stop(f"build_state is '{state}' — not building.")
    if month_tokens_used() >= CONFIG["monthly_token_cap"]:
        stop(f"monthly token cap reached ({CONFIG['monthly_token_cap']}).")

    throttle = (state == "throttled")
    spec = COMPLETENESS or RECOMMENDED_COMPLETENESS
    enforce = COMPLETENESS is not None
    print(f"[builder] geo: {len(active_markets())} active market(s); completeness "
          f"{'ENFORCED from config' if enforce else 'DRY-RUN (config completeness absent; cannot edit config)'}")

    fetched, report = fetch_pages(spec, enforce)
    # Surface any armed-but-empty category (e.g. plastic-surgery with no prospector data)
    # to needs_human.json. Building proceeds for categories that DO have data.
    empty_cats = report.get("empty_categories", [])
    surface_category_gaps(empty_cats)
    if empty_cats:
        print(f"[builder] empty categories surfaced to needs_human: {empty_cats}")

    passed, skipped = [], 0
    for page in fetched:
        if quality_gate(page):
            passed.append(page)
        else:
            skipped += 1
            print(f"[builder] skipped (failed quality gate): {page['path']}")
    if throttle:
        passed = passed[:10]

    summaries = []
    for page in passed:
        out = render(page, page_links(page, passed))
        summaries.append(page_summary(page))
        print(f"[builder] built {out.relative_to(GENERATED)}")
    built = len(summaries)

    render_hubs(summaries)
    render_index(summaries)
    render_claim()
    render_advertise(summaries)
    guide_urls = render_guides(passed)
    render_sitemap(summaries, guide_urls)
    # Octoru favicon — inline vector octagon mark (NOT a bitmap). Served at site root /favicon.svg.
    _write("favicon.svg",
           '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 72 72">'
           '<polygon points="62,47 47,62 25,62 10,47 10,25 25,10 47,10 62,25" fill="#1447E6"/>'
           '<path d="M27,33 H33 V27 H39 V33 H45 V39 H39 V45 H33 V39 H27 Z" fill="#fff"/></svg>\n')
    print(f"[builder] built hubs + homepage + claim + advertise + {len(guide_urls)} guides + favicon + sitemap.xml")

    report["empty_fields"] = compute_empty_fields(passed)
    report["mode"] = "enforced" if enforce else "dry-run (config 'completeness' absent)"
    report["thresholds_used"] = spec
    print(f"[builder] completeness: mode={report['mode']} | listings_excluded={len(report['excluded_listings'])} | "
          f"pages_held={len(report['held_pages'])} | empty_fields={report['empty_fields']}")
    (GENERATED / "_completeness_report.json").write_text(json.dumps(report, indent=2))

    # Copy static assets (CSS, images, favicons) into generated/ so deploys serve them.
    # Without this, pages reference /assets/styles.css but the file isn't shipped.
    _assets_src = ROOT / "assets"
    if _assets_src.is_dir():
        import shutil as _shutil
        _assets_dst = GENERATED / "assets"
        if _assets_dst.exists():
            _shutil.rmtree(_assets_dst)
        _shutil.copytree(_assets_src, _assets_dst)
        print(f"[builder] copied assets/ -> generated/assets/ ({sum(1 for _ in _assets_dst.rglob('*') if _.is_file())} files)")

    # Link validation — catch wrong-county and dead internal links before commit.
    import re as _re
    _link_re = _re.compile(r'href="(/fl/[^"#?]+)"')
    _built_paths = set()
    for _f in GENERATED.rglob("index.html"):
        _rel = "/" + str(_f.relative_to(GENERATED).parent).replace("\\","/") + "/"
        _built_paths.add(_rel)
    _broken, _wrong = [], []
    for _f in GENERATED.rglob("index.html"):
        _src = "/" + str(_f.relative_to(GENERATED).parent).replace("\\","/") + "/"
        for _href in _link_re.findall(_f.read_text()):
            _tgt = _href if _href.endswith("/") else _href + "/"
            _parts = _tgt.strip("/").split("/")
            if len(_parts) >= 3 and _parts[0] == "fl":
                _exp_co = CITY_COUNTY.get(_parts[2])
                if _exp_co and _parts[1] != _exp_co:
                    _wrong.append(f"{_tgt} (from {_src})")
            if _tgt not in _built_paths and not _tgt.startswith("/fl/") is False:
                pass  # non-fl links are external
            if _tgt.startswith("/fl/") and _tgt not in _built_paths:
                _broken.append(f"{_tgt} (from {_src})")
    if _wrong:
        print(f"[builder] WARN: {len(_wrong)} wrong-county link(s): {_wrong[:5]}")
    if _broken:
        print(f"[builder] WARN: {len(_broken)} broken internal link(s): {_broken[:5]}")
    if not _wrong and not _broken:
        print(f"[builder] link check: all internal links valid")

    # Rating-integrity guards (inflated / synthetic ratings)
    _row_flags, _share, _halt, _overridden = integrity_scan()
    print(f"[builder] integrity: perfect-at-volume(>=4.95 & n>=50) share = {_share:.1%} "
          f"(halt>20%: {'YES' if _halt else 'no'}) | row flags(>=4.95 & n>=100) = {len(_row_flags)}")
    if _halt and not _overridden:
        print("[builder] *** HALT FLAG written to needs_human.json: ratings distribution "
              "implausible — likely synthetic, DO NOT PUBLISH. ***")
    elif _halt and _overridden:
        print("[builder] integrity halt is on file but a HUMAN OVERRIDE is recorded "
              "(operator chose to ship Google data as-is); flag is non-blocking. "
              "Publish remains a separate human-gated step.")

    # DO NOT merge to main. DO NOT deploy. (hard-gated in CLAUDE.md)
    print(f"[builder] done. built={built} skipped={skipped} state={state}")


if __name__ == "__main__":
    main()
