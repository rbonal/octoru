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
    "hydrafacial": "HydraFacial",
    "chemical-peel": "Chemical peel",
    "dermal-fillers": "Dermal fillers",
    "iv-therapy": "IV therapy",
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
    "hydrafacial": [
        {
            "q": "How much does a HydraFacial cost in {city}?",
            "a_prices": "HydraFacial prices vary by tier (signature, deluxe, platinum) and any serum booster add-ons. Providers in our {city} directory list their starting prices above \u2014 a consultation will confirm which tier fits your skin goals.",
            "a_no_prices": "Published Florida med spa prices for a HydraFacial most commonly run $150\u2013$350 per session. Signature (basic) sessions are typically $150\u2013$200, deluxe versions with boosters $200\u2013$300, and platinum tiers $275\u2013$350. Packages and memberships usually reduce the per-session cost.",
        },
        {
            "q": "How often should you get a HydraFacial?",
            "a": "Every four to six weeks is the standard recommendation, matching the skin's roughly 28-day cell-turnover cycle. Acne-prone or congested skin sometimes starts with sessions every two to three weeks before stretching to monthly maintenance. Going more often than every two weeks is generally discouraged, because the built-in exfoliation can over-stress the skin barrier.",
        },
        {
            "q": "What does a HydraFacial treat?",
            "a": "It is best for surface-level concerns: dullness, dehydration, congested pores and blackheads, uneven tone and mild texture. The treatment is gentle enough for all skin types, including sensitive skin. For deeper concerns such as pitted acne scars or skin laxity, collagen-building treatments like microneedling tend to deliver better results.",
        },
        {
            "q": "Is there any downtime after a HydraFacial?",
            "a": "No \u2014 that is one of its main draws. Most people leave with an immediate glow and return to their day right away; some notice mild redness for a few hours. Makeup can usually be applied the same day, and daily sun protection helps preserve the result.",
        },
    ],
    "chemical-peel": [
        {
            "q": "How much does a chemical peel cost in {city}?",
            "a_prices": "Chemical peel prices depend on the peel depth \u2014 light, medium or deep \u2014 and how many sessions your plan includes. Providers in our {city} directory list their starting prices above; a consultation confirms which peel fits your skin and budget.",
            "a_no_prices": "Published prices for a professional chemical peel most commonly run about $150 to $800 per session, with light superficial peels at the lower end and medium-depth peels higher; deep peels cost more and are performed far less often. Clinics frequently sell light and medium peels as a series of three to six sessions, so ask about package pricing.",
        },
        {
            "q": "What does a chemical peel treat?",
            "a": "Chemical peels resurface the skin to improve dullness, uneven tone, sun spots, melasma, post-acne discoloration, rough texture and fine lines. Lighter peels handle surface concerns with little downtime; deeper peels reach further to address more stubborn pigmentation and lines. For pitted acne scars or skin laxity, collagen-building treatments like microneedling are often a better fit.",
        },
        {
            "q": "How many chemical peel sessions will I need?",
            "a": "Light and medium peels rarely reach their full result in one visit, so providers commonly recommend a series of three to six sessions spaced about four to six weeks apart, followed by occasional maintenance. Deeper peels can produce a bigger change in a single treatment but need more recovery and are done far less often. A provider tailors the number of sessions to your skin concern.",
        },
        {
            "q": "Is there downtime after a chemical peel?",
            "a": "It depends on the depth. Light peels usually involve little to no downtime \u2014 mild flaking and redness for a day or two. Medium peels can cause several days of visible peeling and redness, and deep peels may need a week or more of recovery. Diligent sun protection afterward is essential, because freshly resurfaced skin is more sensitive to the sun.",
        },
    ],
    "dermal-fillers": [
        {
            "q": "How much do dermal fillers cost in {city}?",
            "a_prices": "Dermal filler pricing is per syringe and depends on the filler type and how many syringes your treatment needs. Providers in our {city} directory list their starting prices above; a consultation confirms the right filler and syringe count for your goal.",
            "a_no_prices": "Published prices for dermal fillers most commonly run about $600 to $1,200 per syringe. Hyaluronic-acid fillers such as Juvederm and Restylane tend to sit near the middle of that range, while thicker or longer-lasting fillers cost more. Most areas need one to two syringes, so the total depends on how many areas you treat \u2014 ask for a per-syringe quote and an estimate of syringes.",
        },
        {
            "q": "What do dermal fillers treat?",
            "a": "Dermal fillers restore volume and smooth lines rather than freezing muscles. They are commonly used for cheek and midface volume, jawline and chin definition, nasolabial folds and marionette lines, lips, and under-eye hollows. For wrinkles caused by muscle movement \u2014 like forehead lines and crow's feet \u2014 a neuromodulator such as Botox is usually the better tool, and many people combine the two.",
        },
        {
            "q": "How long do dermal fillers last?",
            "a": "It depends on the product and where it is placed. Most hyaluronic-acid fillers last roughly 6 to 18 months, with thinner lip fillers on the shorter end and firmer cheek or jawline fillers lasting longer. Calcium-hydroxylapatite and poly-L-lactic-acid fillers can last a year or more. Areas with a lot of movement break filler down faster, so periodic touch-ups keep results consistent.",
        },
        {
            "q": "Is there downtime after dermal fillers?",
            "a": "Downtime is usually minimal. Most people return to normal activities the same day, though mild swelling, redness or bruising at the injection sites is common for a few days \u2014 under-eye and lip areas tend to swell most. Providers generally advise avoiding strenuous exercise, alcohol and blood-thinning medications for about 24 hours to limit bruising.",
        },
    ],
    "iv-therapy": [
        {
            "q": "How much does IV therapy cost in {city}?",
            "a_prices": "IV therapy is priced per session and varies with the formula \u2014 basic hydration drips cost less than vitamin blends or specialty infusions like NAD+. Providers in our {city} directory list their starting prices above; a consultation confirms which drip fits your goal.",
            "a_no_prices": "Published prices for a single IV therapy session most commonly run about $100 to $400. Basic hydration and simple vitamin drips sit at the lower end, classic blends like a Myers' cocktail in the middle, and specialty or high-dose infusions such as NAD+ cost more. Many clinics offer membership or package pricing that lowers the per-session cost.",
        },
        {
            "q": "What is IV therapy used for?",
            "a": "IV therapy delivers fluids, electrolytes, vitamins and minerals straight into the bloodstream, bypassing digestion. Med spas and IV lounges market it for hydration, an energy boost, immune support, recovery after exercise or travel, and hangover relief. It is worth knowing that rigorous clinical evidence for many of these specific benefits is limited, so it is best approached as a wellness service rather than a proven medical treatment. A licensed provider can advise whether it makes sense for you.",
        },
        {
            "q": "How long does an IV therapy session take, and how often can you get it?",
            "a": "A typical drip takes about 30 to 60 minutes while you sit comfortably. Frequency depends on the formula and your goal \u2014 some people get a drip occasionally for recovery or before an event, while others follow a regular schedule such as monthly. There is no universal rule; a provider will recommend a cadence based on your needs and health.",
        },
        {
            "q": "Is IV therapy safe, and are there side effects?",
            "a": "For healthy adults, IV therapy given by a licensed professional is generally considered low-risk, but it is not without side effects. The most common are discomfort, bruising or, rarely, infection at the insertion site, plus a warm or flushed sensation. People with heart, kidney or certain other conditions, and anyone on medications, should check with a doctor first, because high-dose vitamins and extra fluid are not appropriate for everyone.",
        },
    ],
}


def _build_intro(treatment_slug, market, clinics, prices, all_clinics_for_county=None):
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
        parts.append(price_full[0].upper() + price_full[1:])

    if lang_str:
        parts.append(lang_str)

    parts.append(f"Each listing below shows the clinic's address, phone, treatments, and verified Google rating so you can compare before booking a consultation.")

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
    "hydrafacial": "per session",
    "chemical-peel": "per session",
    "dermal-fillers": "per syringe",
    "iv-therapy": "per session",
}
TREATMENT_GUIDANCE = {
    "botox": "Botox is a neuromodulator injected to soften dynamic wrinkles; it is usually priced per unit, and the number of units depends on the treatment area. Effects typically last a few months. Ask each provider who performs the injections and how units are counted.",
    "lip-filler": "Lip filler uses hyaluronic-acid dermal fillers to add volume and shape; it is usually priced per syringe. Results are not permanent and vary by product. Ask which filler is used and about reversibility.",
    "coolsculpting": "CoolSculpting is a non-surgical fat-reduction treatment that cools targeted areas; it is typically priced per session or per area, and several sessions may be suggested. Ask how many cycles a provider recommends for your goal.",
    "laser-hair-removal": "Laser hair removal reduces unwanted hair over a course of sessions; pricing is usually per session or per package and depends on the body area. Ask how many sessions are typical and which laser suits your skin type.",
    "microneedling": "Microneedling stimulates collagen to refine skin texture; it is usually priced per session, sometimes with radiofrequency or PRP add-ons. Ask what device is used and how many sessions are suggested.",
    "hydrafacial": "A HydraFacial is a non-invasive hydradermabrasion treatment that cleanses, exfoliates, extracts and hydrates the skin with serums in one visit; it is usually priced per session, with tiered versions (signature, deluxe, platinum) and booster add-ons raising the price. There is no downtime. Ask which tier and boosters a provider recommends for your skin.",
    "chemical-peel": "A chemical peel applies an acid solution \u2014 light peels use alpha- or beta-hydroxy acids like glycolic or salicylic, medium peels use TCA \u2014 to exfoliate the skin and improve tone, texture and mild discoloration; it is usually priced per session, and deeper peels or a series of sessions cost more. Downtime rises with the depth of the peel, from little to none for light peels to a week or more for deep ones. Ask which peel depth and how many sessions a provider recommends for your skin.",
    "dermal-fillers": "Dermal fillers are injectable gels \u2014 most commonly hyaluronic acid (Juvederm, Restylane), sometimes calcium hydroxylapatite (Radiesse) or poly-L-lactic acid (Sculptra) \u2014 used to restore volume and smooth folds in the cheeks, jawline, chin, lips and under-eye area; they are usually priced per syringe, and the number of syringes depends on the area and goal. Most results are immediate and last from several months to over a year depending on the product and placement. Ask which filler and how many syringes a provider recommends for your goal.",
    "iv-therapy": "IV therapy delivers fluids, electrolytes, vitamins and minerals directly into the bloodstream through a drip, usually over 30 to 60 minutes; it is priced per session, with specialty formulas such as NAD+ or higher-dose blends costing more. Providers market it for hydration, energy, immune support and hangover recovery, though robust clinical evidence for many of these specific benefits is limited. It should be given by a licensed medical professional \u2014 ask which formula fits your goal and whether it is appropriate for you.",
}

# Short factual treatment blurbs for the homepage cards (not pricing — pricing is real-data only).
TREATMENT_DESC = {
    "botox": "Wrinkle-relaxing injections, priced per unit.",
    "lip-filler": "Hyaluronic-acid lip enhancement, priced per syringe.",
    "coolsculpting": "Non-invasive fat reduction, priced per area.",
    "laser-hair-removal": "Multi-session hair reduction, priced by area.",
    "microneedling": "Collagen-induction skin treatment, per session.",
    "hydrafacial": "Hydradermabrasion facial with serum infusion, per session.",
    "chemical-peel": "Acid-based skin resurfacing peel, priced per session.",
    "dermal-fillers": "Hyaluronic-acid facial volume restoration, priced per syringe.",
    "iv-therapy": "IV vitamin and hydration drip therapy, priced per session.",
}

# City centroids for geolocation — sourced from data/places.json (operator-owned taxonomy).
# Falls back to empty if places.json is absent; the build never invents clinic data from these.
CITY_LATLNG = {
    p["slug"]: (p["lat"], p["lng"])
    for p in _PLACES_RAW
    if p.get("lat") and p.get("lng")
}


def treatment_cards(all_clinics):
    """Homepage treatment cards. 'Typical from' price is computed from REAL listing prices;
    treatments without enough real data get the honest empty state (no placeholder $)."""
    cards = []
    for t in CONFIG["seed_scope"]["treatments"]:
        vals = sorted({p for c in all_clinics if (p := _starting_price(c, t)) is not None})
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


def _assemble_page(treatment_slug, market, clinics, all_county_clinics=None):
    """Group real clinics into one treatment x city page. Differentiation comes from
    the real clinics + market-specific context, not boilerplate."""
    t_name = TREATMENT_NAMES.get(treatment_slug, treatment_slug.replace("-", " ").title())
    city_name = market["city_name"]

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
    top_ranked_id = None
    if organic_ranked:
        top = organic_ranked[0]
        if (top.get("review_count") or 0) >= MIN_REVIEWS_FOR_BADGE:
            top_ranked_id = top.get("slug") or top.get("name")

    n = len(clinics)
    unit = TREATMENT_UNITS.get(treatment_slug, "")
    prices = sorted({p for c in clinics if (p := _starting_price(c, treatment_slug)) is not None})

    # Rich human-sounding intro with neighbourhood context and real data
    intro = _build_intro(treatment_slug, market, clinics, prices, all_county_clinics)

    # Meta description optimised for SERP click-through
    provider_word = "provider" if n == 1 else "providers"
    price_hint = f" Botox from ${prices[0]}/{unit}" if treatment_slug == "botox" and prices else ""
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
        "treatment": {"slug": treatment_slug, "name": t_name},
        "neighborhood": {"slug": market["city"], "name": city_name},
        "city": market["state_abbr"],
        "geo": market,
        "path": page_path(market, treatment_slug),
        "page_flags": {"has_consent_form": True, "has_schema_markup": True},
        "meta_description": meta,
        "canonical_url": SITE_URL + page_url(market, treatment_slug),
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


def fetch_pages(spec=None, enforce=False):
    """Build treatment x place pages, applying completeness thresholds and place-taxonomy
    rollup. Returns (pages, report).

    Place taxonomy (data/places.json):
    - A clinic appears at its MOST SPECIFIC qualifying place (neighborhood > CDP > municipality).
    - De-duplication: once a clinic is assigned to a neighborhood/CDP page, it is NOT included
      on the parent municipality page (prevents the same clinic appearing on both Brickell and
      Miami pages).
    - Rollup: if a neighborhood/CDP treatment page is below min_page_requirements AND the place
      has a parent_place, its qualifying clinics are rolled up to the parent place. The thin
      neighborhood page is NOT built; the parent page gains those clinics.

    Listing below min_listing_fields is excluded; page below min_page_requirements is HELD
    (unless rollup to parent is possible). Dry-run (enforce=False) reports only."""
    clinics = load_clinics()
    report = {
        "excluded_listings": [], "held_pages": [],
        "rolled_up": [],   # {clinic, from_place, to_place, treatment}
        "deduped": [],     # {clinic, kept_at, not_shown_at}
    }
    if not clinics:
        print(f"[builder] no prospector data in {PROSPECTOR_DIR} — nothing to build.")
        return [], report

    req_fields = (spec or {}).get("min_listing_fields") or []
    page_reqs = (spec or {}).get("min_page_requirements") or {}
    min_listings = page_reqs.get("min_listings", 0)
    treatments = CONFIG["seed_scope"]["treatments"]

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
    for market in markets:
        city = market["city"]
        place_type = _place_type(city)
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
            page = _assemble_page(t, market, use, all_county_clinics=county_clinics)
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
            page = _assemble_page(t, market, use, all_county_clinics=county_clinics)
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

    return pages, report


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
    for tr in CONFIG["seed_scope"]["treatments"]:
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
        rel_path=rel_path, site_url=SITE_URL, last_updated=datetime.date.today().isoformat())
    return _write(f"{rel_path}/index.html" if rel_path else "index_hub.html", html)


def render_hubs(summaries):
    """State, county, and city hub pages from the built listing summaries."""
    states = {}
    for s in summaries:
        states.setdefault(s["state"], {"name": s["state_name"], "counties": {}})
        co = states[s["state"]]["counties"].setdefault(s["county"], {"name": s["county_name"], "cities": {}})
        ci = co["cities"].setdefault(s["city"], {"name": s["city_name"], "pages": []})
        if not any(p["url"] == s["url"] for p in ci["pages"]):
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
                render_hub(f"Best Med Spas in {cidata['name']}, {sdata['name']}",
                           f"Compare {len(cidata['pages'])} treatments and top-rated providers in {cidata['name']} — Botox, lip filler, laser hair removal & microneedling.", bc, cards, f"{st}/{co}/{ci}")
            # county hub
            ccards = [{"title": cidata["name"], "sub": f"{len(cidata['pages'])} treatment" + ("" if len(cidata['pages']) == 1 else "s"),
                       "url": f"/{st}/{co}/{ci}/", "chip": None}
                      for ci, cidata in sorted(cdata["cities"].items(), key=lambda kv: kv[1]["name"])]
            bc = [{"name": "Home", "url": "/"}, {"name": sdata["name"], "url": f"/{st}/"}, {"name": cdata["name"], "url": f"/{st}/{co}/"}]
            render_hub(f"Best Med Spas in {cdata['name']} County, {sdata['name']} — Botox, Filler & Laser",
                       f"{len(cdata['cities'])} cities", bc, ccards, f"{st}/{co}")
        # state hub
        scards = [{"title": cdata["name"] + " County", "sub": f"{len(cdata['cities'])} cities",
                   "url": f"/{st}/{co}/", "chip": None}
                  for co, cdata in sorted(sdata["counties"].items(), key=lambda kv: kv[1]["name"])]
        bc = [{"name": "Home", "url": "/"}, {"name": sdata["name"], "url": f"/{st}/"}]
        render_hub(f"Med Spas in {sdata['name']} — Botox, Filler & Laser by City", f"{len(sdata['counties'])} counties", bc, scards, st)
    return states


COUNTY_ORDER = ["miami-dade", "broward", "palm-beach"]


def render_index(summaries):
    """Homepage (design/landing): real stats, real county->city grid (with real treatment
    counts), real treatment cards (real prices or honest 'varies'), and the geolocation
    nearest-city set built from real covered cities. Renders templates/home.html.j2."""
    if not summaries:
        return None
    counties = {}  # (state, county) -> {name, state_name, cities}
    for s in summaries:
        key = (s["state"], s["county"])
        c = counties.setdefault(key, {"name": s["county_name"], "state_name": s["state_name"], "cities": {}})
        ci = c["cities"].setdefault(s["city"], {
            "name": s["city_name"], "url": f'/{s["state"]}/{s["county"]}/{s["city"]}/', "treats": set()})
        ci["treats"].add(s["treatment_slug"])

    order = sorted(counties, key=lambda k: (COUNTY_ORDER.index(k[1]) if k[1] in COUNTY_ORDER else 99, k[1]))
    groups = []
    for key in order:
        c = counties[key]
        cities = [{"name": v["name"], "url": v["url"], "n_treatments": len(v["treats"]),
                   "data_treatments": " ".join(sorted(v["treats"]))}
                  for _, v in sorted(c["cities"].items(), key=lambda kv: kv[1]["name"])]
        groups.append({"slug": key[1], "short_name": c["name"],
                       "name": f'{c["name"]}, {c["state_name"]}', "n_cities": len(cities), "cities": cities})

    stats = {
        "listings": sum(s["n_clinics"] for s in summaries),
        "cities": len({(s["state"], s["county"], s["city"]) for s in summaries}),
        "counties": len(counties),
    }

    # geolocation nearest-city set: covered cities that have a known centroid
    city_url = {s["city"]: f'/{s["state"]}/{s["county"]}/{s["city"]}/' for s in summaries}
    city_name = {s["city"]: s["city_name"] for s in summaries}
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

    # Treatment cards no longer hard-link to a single "densest" city — clicking a card
    # filters the city grid to the cities that offer that treatment (see home.html.j2 JS).
    tcard_list = treatment_cards(all_clinics)

    # Avg rating for social proof
    ratings = [c["rating"] for c in all_clinics if c.get("rating")]
    avg_rating = round(sum(ratings)/len(ratings), 1) if ratings else None

    html = env.get_template("home.html.j2").render(
        groups=groups, stats=stats, treatments=tcard_list,
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


def render_learn():
    urls = []
    for t in json.loads((ROOT / "data" / "learn_topics.json").read_text()):
        _write(f"learn/{t['slug']}/index.html", env.get_template("learn.html.j2").render(topic=t, site_url=SITE_URL, last_updated=datetime.date.today().isoformat(), year=datetime.date.today().year))
        urls.append(f"/learn/{t['slug']}/")
    return urls


def render_metros(summaries):
    metros = [{"slug": "miami", "name": "Miami", "county": "miami-dade"}, {"slug": "fort-lauderdale", "name": "Fort Lauderdale", "county": "broward"}, {"slug": "boca-raton", "name": "Boca Raton", "county": "palm-beach"}]
    names = {}
    for s in summaries:
        names.setdefault(s["treatment_slug"], s["treatment_name"])
    urls = []
    for metro in metros:
        for t_slug in sorted(names):
            rows = sorted([s for s in summaries if s["county"] == metro["county"] and s["treatment_slug"] == t_slug], key=lambda r: (r["from_price"] is None, r["from_price"] or 0, r["city_name"]))
            _seen = set()
            rows = [r for r in rows if not (r["url"] in _seen or _seen.add(r["url"]))]
            providers = sum(r["n_clinics"] for r in rows)
            if len(rows) < 2 or providers < 3:
                continue
            priced = [r["from_price"] for r in rows if r["from_price"]]
            html = env.get_template("metro.html.j2").render(ref_price=(sorted(priced)[len(priced)//2] if priced else None), has_es=t_slug in ("botox", "lip-filler", "laser-hair-removal", "microneedling", "coolsculpting"), metro=metro, treatment_slug=t_slug, treatment_name=names[t_slug], rows=rows, unit=rows[0]["price_unit"], low=(min(priced) if priced else None), high=(max(priced) if priced else None), n_areas=len(rows), providers=providers, priced_count=len(priced), site_url=SITE_URL, year=datetime.date.today().year, last_updated=datetime.date.today().isoformat())
            _write(f"fl/{metro['slug']}/{t_slug}/guide/index.html", html)
            urls.append(f"/fl/{metro['slug']}/{t_slug}/guide/")
            if t_slug in ("botox", "lip-filler", "laser-hair-removal", "microneedling", "coolsculpting"):
                es_names = {"botox": "Botox", "lip-filler": "Relleno de labios", "laser-hair-removal": "Depilación láser", "microneedling": "Microneedling", "coolsculpting": "CoolSculpting"}
                es_units = {"per unit": "por unidad", "per syringe": "por jeringa", "per session": "por sesión"}
                es_html = env.get_template("metro-es.html.j2").render(ref_price=(sorted(priced)[len(priced)//2] if priced else None), metro=metro, treatment_slug=t_slug, treatment_name=es_names[t_slug], art=("la" if t_slug == "laser-hair-removal" else "el"), contr=("de la" if t_slug == "laser-hair-removal" else "del"), rows=rows, unit=es_units.get(rows[0]["price_unit"], ""), low=(min(priced) if priced else None), high=(max(priced) if priced else None), n_areas=len(rows), providers=providers, priced_count=len(priced), site_url=SITE_URL, year=datetime.date.today().year, last_updated=datetime.date.today().isoformat())
                _write(f"es/fl/{metro['slug']}/{t_slug}/guide/index.html", es_html)
                urls.append(f"/es/fl/{metro['slug']}/{t_slug}/guide/")
    print(f"[builder] built {len(urls)} metro pages")
    return urls


def render_metro_hubs(summaries):
    metros = [{"slug": "miami", "name": "Miami", "county": "miami-dade"}, {"slug": "fort-lauderdale", "name": "Fort Lauderdale", "county": "broward"}, {"slug": "boca-raton", "name": "Boca Raton", "county": "palm-beach"}]
    names = {}
    for s in summaries:
        names.setdefault(s["treatment_slug"], s["treatment_name"])
    urls = []
    for metro in metros:
        items = []
        for t_slug in sorted(names):
            rows = [s for s in summaries if s["county"] == metro["county"] and s["treatment_slug"] == t_slug]
            seen = set()
            rows = [r for r in rows if not (r["url"] in seen or seen.add(r["url"]))]
            providers = sum(r["n_clinics"] for r in rows)
            if len(rows) < 2 or providers < 3:
                continue
            priced = [r["from_price"] for r in rows if r["from_price"]]
            items.append({"treatment_slug": t_slug, "treatment_name": names[t_slug], "n_areas": len(rows), "providers": providers, "low": (min(priced) if priced else None), "unit": next((r["price_unit"] for r in rows if r.get("price_unit")), "")})
        if not items:
            continue
        html = env.get_template("metro-hub.html.j2").render(metro=metro, items=items, site_url=SITE_URL, year=datetime.date.today().year, last_updated=datetime.date.today().isoformat())
        _write(f"fl/{metro['slug']}/index.html", html)
        urls.append(f"/fl/{metro['slug']}/")
    print(f"[builder] built {len(urls)} metro hubs")
    return urls


def render_sitemap(summaries, guide_urls=None):
    urls = ["/", "/claim.html", "/advertise.html"]
    seen_hubs = set()
    seen_pages = set()
    for s in summaries:
        for hub in (f"/{s['state']}/", f"/{s['state']}/{s['county']}/", f"/{s['state']}/{s['county']}/{s['city']}/"):
            if hub not in seen_hubs:
                seen_hubs.add(hub); urls.append(hub)
        if s["url"] not in seen_pages:
            seen_pages.add(s["url"]); urls.append(s["url"])
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
        nh["items"].insert(0, {
            "id": "integrity-corpus-perfect-share",
            "opened_at": datetime.date.today().isoformat(), "opened_by": "builder",
            "blocking": True, "severity": "halt",
            "summary": "ratings distribution implausible — likely synthetic, do not publish.",
            "detail": f"{share:.1%} of providers are rated >= 4.95 with >= 50 reviews "
                      f"(threshold 20%). Investigate the ratings source before any deploy.",
        })
    nh_path.write_text(json.dumps(nh, indent=2))
    return row_flags, share, halt


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
    learn_urls = render_learn()
    metro_urls = render_metros(summaries)
    metro_hub_urls = render_metro_hubs(summaries)
    render_sitemap(summaries, learn_urls + metro_urls + metro_hub_urls)  # guides are noindexed -> keep out of sitemap
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
    _row_flags, _share, _halt = integrity_scan()
    print(f"[builder] integrity: perfect-at-volume(>=4.95 & n>=50) share = {_share:.1%} "
          f"(halt>20%: {'YES' if _halt else 'no'}) | row flags(>=4.95 & n>=100) = {len(_row_flags)}")
    if _halt:
        print("[builder] *** HALT FLAG written to needs_human.json: ratings distribution "
              "implausible — likely synthetic, DO NOT PUBLISH. ***")

    # DO NOT merge to main. DO NOT deploy. (hard-gated in CLAUDE.md)
    print(f"[builder] done. built={built} skipped={skipped} state={state}")


if __name__ == "__main__":
    main()
