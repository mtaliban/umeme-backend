"""Seed script — run with: python -m app.seed [--reset]

Idempotent: running twice produces the same result.
--reset clears all content collections (never users).
"""
from __future__ import annotations

import asyncio
import logging
import re
import sys
from datetime import date, datetime, timezone

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ---------------------------------------------------------------------------
# Real photo catalog (Unsplash CDN, no API key)
# ---------------------------------------------------------------------------

_PHOTOS: dict[str, list[str]] = {
    "electricity": [
        "https://images.unsplash.com/photo-1473341304170-971dccb5ac1e?w=1200&h=800&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1543966888-7c1dc482a810?w=1200&h=800&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1508514177221-188b1cf16e9d?w=1200&h=800&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1497435334941-8c899a9bd204?w=1200&h=800&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1555636222-cae831e670b3?w=1200&h=800&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1610978933854-9b7f2c8c3cfc?w=1200&h=800&fit=crop&auto=format",
    ],
    "solar": [
        "https://images.unsplash.com/photo-1509391366360-2e959784a276?w=1200&h=800&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1466611653911-95081537e5b7?w=1200&h=800&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1508514177221-188b1cf16e9d?w=1200&h=800&fit=crop&auto=format",
    ],
    "water": [
        "https://images.unsplash.com/photo-1534155059661-9e43284e82f8?w=1200&h=800&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1504280395203-5a56b4d2bb9e?w=1200&h=800&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1562158074-5f1e3f63acba?w=1200&h=800&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1468476775582-b6e18c7af65a?w=1200&h=800&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1612178991541-b48cc8e92a4d?w=1200&h=800&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1536183922588-166604504d5e?w=1200&h=800&fit=crop&auto=format",
    ],
    "construction": [
        "https://images.unsplash.com/photo-1504307651254-35680f356dfd?w=1200&h=800&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1486325212027-8081e485255e?w=1200&h=800&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1541888946425-d81bb19240f5?w=1200&h=800&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1565008447742-97f6f38c985c?w=1200&h=800&fit=crop&auto=format",
    ],
    "training": [
        "https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=1200&h=800&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?w=1200&h=800&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1434030216411-0b793f4b4173?w=1200&h=800&fit=crop&auto=format",
    ],
    "office": [
        "https://images.unsplash.com/photo-1497366216548-37526070297c?w=1200&h=800&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1486325212027-8081e485255e?w=1200&h=800&fit=crop&auto=format",
    ],
    "people": [
        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=400&h=400&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=400&h=400&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1573497019940-1c28c88b4f3e?w=400&h=400&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=400&h=400&fit=crop&auto=format",
        "https://images.unsplash.com/photo-1580489944761-15a19d654956?w=400&h=400&fit=crop&auto=format",
    ],
    "logo": [
        "https://images.unsplash.com/photo-1473341304170-971dccb5ac1e?w=400&h=120&fit=crop&auto=format",
    ],
}

_photo_counters: dict[str, int] = {}


def _pick(category: str, w: int = 1200, h: int = 800) -> str:
    photos = _PHOTOS.get(category, _PHOTOS["construction"])
    idx = _photo_counters.get(category, 0)
    _photo_counters[category] = (idx + 1) % len(photos)
    url = photos[idx]
    url = re.sub(r'w=\d+', f'w={w}', url)
    url = re.sub(r'h=\d+', f'h={h}', url)
    return url


def _t(en: str, sw: str = "") -> dict:
    return {"en": en, "sw": sw or en}


def _img(category: str, alt_en: str = "", alt_sw: str = "", w: int = 1200, h: int = 800) -> dict:
    url = _pick(category, w, h)
    return {
        "url": url,
        "alt": _t(alt_en, alt_sw or alt_en),
        "width": w,
        "height": h,
        "sizes": {"sm": url, "md": url, "lg": url},
    }


def _seo(title_en: str, desc_en: str) -> dict:
    return {
        "meta_title": _t(title_en),
        "meta_description": _t(desc_en),
        "share_image": None,
    }


NOW = datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Individual collection seeders
# ---------------------------------------------------------------------------

async def seed_settings() -> None:
    from app.models.misc import SiteSettings
    if await SiteSettings.find_one():
        logger.info("Settings already seeded")
        return
    logo_url = _pick("logo", 400, 120)
    s = SiteSettings(
        company_name="Kilele Power & Water Engineering Ltd",
        slogan=_t("Electricity and Water – We Build, We Maintain", "Umeme na Maji – Tunajenga, Tunadumisha"),
        logo={"url": logo_url, "alt": _t("Kilele Power & Water Engineering"), "width": 400, "height": 120,
              "sizes": {"sm": logo_url, "md": logo_url, "lg": logo_url}},
        logo_dark={"url": logo_url, "alt": _t("Kilele Power & Water Engineering"), "width": 400, "height": 120,
                   "sizes": {"sm": logo_url, "md": logo_url, "lg": logo_url}},
        favicon={"url": logo_url, "alt": _t("Favicon"), "width": 32, "height": 32,
                 "sizes": {"sm": logo_url, "md": logo_url, "lg": logo_url}},
        phones=["+255 700 000 001"],
        emails=["info@kileleengineering.co.tz"],
        whatsapp_number="+255700000001",
        working_hours=_t("Mon–Fri 8:00am–5:00pm; Sat 8:00am–1:00pm", "Jumatatu–Ijumaa 8:00–17:00; Jumamosi 8:00–13:00"),
        address=_t("Mikocheni B, Old Bagamoyo Road, Dar es Salaam", "Mikocheni B, Barabara ya Old Bagamoyo, Dar es Salaam"),
        social={
            "facebook": "",
            "instagram": "",
            "x": "",
            "linkedin": "",
            "youtube": "",
            "tiktok": "",
        },
        footer_text=_t(
            "Kilele Power & Water Engineering Ltd – A Tanzanian engineering company for electricity and water, serving homes, businesses, industries and institutions since 2014.",
            "Kilele Power & Water Engineering Ltd – kampuni ya Kitanzania ya uhandisi wa umeme na maji, ikihudumia makazi, biashara, viwanda na taasisi tangu 2014.",
        ),
        default_seo=_seo(
            "Kilele Power & Water Engineering Ltd – Tanzania",
            "Tanzanian engineering company for electricity and water solutions.",
        ),
        notify_emails=["info@kileleengineering.co.tz"],
        home_sections=[
            {"key": "hero", "enabled": True, "sort": 1},
            {"key": "stats", "enabled": True, "sort": 2},
            {"key": "about", "enabled": True, "sort": 3},
            {"key": "services", "enabled": True, "sort": 4},
            {"key": "features", "enabled": True, "sort": 5},
            {"key": "work_steps", "enabled": True, "sort": 6},
            {"key": "projects", "enabled": True, "sort": 7},
            {"key": "training", "enabled": True, "sort": 8},
            {"key": "clients", "enabled": True, "sort": 9},
            {"key": "testimonials", "enabled": True, "sort": 10},
            {"key": "news", "enabled": True, "sort": 11},
            {"key": "cta", "enabled": True, "sort": 12},
        ],
        cta={
            "title": _t("Need Engineering Services?", "Unahitaji Huduma za Uhandisi?"),
            "text": _t("Contact us today for a free consultation and site assessment.", "Wasiliana nasi leo kwa ushauri wa bure na tathmini ya eneo."),
            "button_label": _t("Request a Service", "Omba Huduma"),
            "button_url": "/request-service",
        },
    )
    await s.insert()
    logger.info("Settings seeded")


async def seed_hero_slides() -> None:
    from app.models.content import HeroSlide
    if await HeroSlide.count() > 0:
        logger.info("HeroSlides already seeded")
        return
    slides = [
        HeroSlide(
            image=_img("electricity", "Electricity Solutions", "Suluhisho za Umeme", 1600, 900),
            headline=_t("Reliable Electricity & Water Solutions", "Suluhisho za Uhakika za Umeme na Maji"),
            text=_t(
                "We design, build and maintain electrical and water systems for homes, businesses, industries and institutions across Tanzania.",
                "Tunasanifu, kujenga na kutunza mifumo ya umeme na maji kwa nyumba, biashara, viwanda na taasisi kote Tanzania.",
            ),
            button1_label=_t("Our Services", "Huduma Zetu"),
            button1_url="/services",
            button2_label=_t("Contact Us", "Wasiliana Nasi"),
            button2_url="/contact",
            sort=1, is_active=True,
        ),
        HeroSlide(
            image=_img("electricity", "Safe Electricity", "Umeme Salama", 1600, 900),
            headline=_t("Safe Electricity, Expert Work", "Umeme Salama, Kazi ya Kitaalamu"),
            text=_t(
                "From building wiring to power lines and transformers – work carried out by registered technicians and engineers.",
                "Kuanzia wiring ya jengo hadi njia za umeme na transfoma – kazi inayofanywa na mafundi na wahandisi waliosajiliwa.",
            ),
            button1_label=_t("Electrical Services", "Huduma za Umeme"),
            button1_url="/services",
            button2_label=_t("Request Service", "Omba Huduma"),
            button2_url="/request-service",
            sort=2, is_active=True,
        ),
        HeroSlide(
            image=_img("water", "Clean Water Systems", "Mifumo ya Maji Safi", 1600, 900),
            headline=_t("Clean Water, Lasting Systems", "Maji Safi, Mifumo Inayodumu"),
            text=_t(
                "Borehole drilling, pump installation, water tanks and pipe networks for communities, institutions and private clients.",
                "Uchimbaji wa visima, ufungaji wa pampu, matenki na mitandao ya mabomba kwa jamii, taasisi na wateja binafsi.",
            ),
            button1_label=_t("Water Services", "Huduma za Maji"),
            button1_url="/services",
            button2_label=_t("Request Service", "Omba Huduma"),
            button2_url="/request-service",
            sort=3, is_active=True,
        ),
    ]
    for s in slides:
        await s.insert()
    logger.info("HeroSlides seeded (%d)", len(slides))


async def seed_stats() -> None:
    from app.models.content import Stat
    if await Stat.count() > 0:
        logger.info("Stats already seeded")
        return
    stats = [
        Stat(label=_t("Completed Projects", "Miradi Iliyokamilika"), number=120, suffix="+", icon="folder-check", sort=1),
        Stat(label=_t("Clients Served", "Wateja Tuliowahudumia"), number=85, suffix="+", icon="users", sort=2),
        Stat(label=_t("Years of Experience", "Miaka ya Uzoefu"), number=12, suffix="", icon="calendar", sort=3),
        Stat(label=_t("Regions Covered", "Mikoa Tuliyofanya Kazi"), number=14, suffix="", icon="map-pin", sort=4),
    ]
    for s in stats:
        await s.insert()
    logger.info("Stats seeded")


async def seed_features() -> None:
    from app.models.content import Feature
    if await Feature.count() > 0:
        logger.info("Features already seeded")
        return
    features = [
        Feature(
            title=_t("Registered Professionals", "Wataalamu Waliosajiliwa"),
            text=_t(
                "All work is supervised by registered engineers.",
                "Kazi zote zinasimamiwa na wahandisi waliosajiliwa.",
            ),
            icon="shield-check", sort=1,
        ),
        Feature(
            title=_t("On-Time Delivery", "Kazi kwa Wakati"),
            text=_t(
                "We plan carefully and deliver on the agreed schedule.",
                "Tunapanga kwa umakini na kukabidhi kwa muda uliokubaliwa.",
            ),
            icon="clock", sort=2,
        ),
        Feature(
            title=_t("Safety First", "Usalama Kwanza"),
            text=_t(
                "We follow workplace safety procedures in every project.",
                "Tunafuata taratibu za usalama kazini katika kila mradi.",
            ),
            icon="hard-hat", sort=3,
        ),
        Feature(
            title=_t("One-Stop Contractor", "Umeme na Maji Pamoja"),
            text=_t(
                "One contractor for all your electrical and water needs.",
                "Mkandarasi mmoja kwa mahitaji yako yote ya umeme na maji.",
            ),
            icon="layers", sort=4,
        ),
    ]
    for f in features:
        await f.insert()
    logger.info("Features seeded")


async def seed_work_steps() -> None:
    from app.models.content import WorkStep
    if await WorkStep.count() > 0:
        logger.info("WorkSteps already seeded")
        return
    steps = [
        WorkStep(
            title=_t("Initial Consultation", "Mawasiliano ya Awali"),
            text=_t(
                "We listen to your needs and budget.",
                "Tunasikiliza mahitaji yako na bajeti yako.",
            ),
            icon="message-circle", sort=1,
        ),
        WorkStep(
            title=_t("Site Survey & Design", "Ukaguzi wa Eneo na Usanifu"),
            text=_t(
                "Engineers inspect the site and prepare drawings and BOQ.",
                "Wahandisi wanakagua eneo na kuandaa michoro na gharama (BOQ).",
            ),
            icon="drafting-compass", sort=2,
        ),
        WorkStep(
            title=_t("Execution", "Utekelezaji"),
            text=_t(
                "Our technicians carry out the work safely and on schedule.",
                "Mafundi wetu wanatekeleza kazi kwa usalama na kwa ratiba.",
            ),
            icon="hard-hat", sort=3,
        ),
        WorkStep(
            title=_t("Testing", "Upimaji"),
            text=_t(
                "Every system is tested before handover.",
                "Kila mfumo unapimwa kabla ya kukabidhiwa.",
            ),
            icon="check-circle", sort=4,
        ),
        WorkStep(
            title=_t("Handover & Aftercare", "Makabidhiano na Huduma Baadaye"),
            text=_t(
                "We hand over with full documentation and continue to provide maintenance services.",
                "Tunakabidhi pamoja na nyaraka na kuendelea kutoa huduma ya matengenezo.",
            ),
            icon="package", sort=5,
        ),
    ]
    for s in steps:
        await s.insert()
    logger.info("WorkSteps seeded")


async def seed_pages() -> None:
    from app.models.pages import Page
    pages_data = [
        {
            "key": "about",
            "title": _t("About Us", "Kuhusu Sisi"),
            "intro": _t(
                "Kilele Power & Water Engineering Ltd has been providing electricity and water solutions across Tanzania since 2014.",
                "Kilele Power & Water Engineering Ltd imekuwa ikitoa suluhisho za umeme na maji kote Tanzania tangu 2014.",
            ),
            "body": _t(
                "<p>Founded in 2014, Kilele Power & Water Engineering Ltd has grown to become a trusted electrical and water engineering company in Tanzania. We combine technical expertise with a genuine commitment to quality, safety and timely delivery.</p>"
                "<p>Our team of engineers, technicians and support staff works across Tanzania, delivering solutions for homes, businesses, industries and institutions.</p>"
                "<p>We are registered with the Engineers Registration Board (ERB), hold a CRB contractor licence, an EWURA electrical installation licence and are registered with BRELA.</p>",
                "<p>Ilianzishwa mwaka 2014, Kilele Power & Water Engineering Ltd imekua kuwa kampuni ya uhandisi wa umeme na maji inayoaminika Tanzania. Tunachanganya utaalamu wa kiufundi na dhamira ya kweli ya ubora, usalama na uwasilishaji kwa wakati.</p>"
                "<p>Timu yetu ya wahandisi, mafundi na wafanyakazi wa msaada inafanya kazi Tanzania, ikitoa suluhisho kwa nyumba, biashara, viwanda na taasisi.</p>",
            ),
            "banner": _img("construction", "About Us", "Kuhusu Sisi", 1600, 700),
            "seo": _seo("About Us | Kilele Power & Water Engineering", "Learn about Kilele Power & Water Engineering Ltd — Tanzania's trusted electrical and water engineering company."),
            "vision": _t(
                "To be the most trusted engineering company for electricity and water in Tanzania.",
                "Kuwa kampuni ya uhandisi inayoaminika zaidi kwa umeme na maji Tanzania.",
            ),
            "mission": _t(
                "To deliver safe, reliable and affordable electrical and water engineering solutions that improve the quality of life for Tanzanians.",
                "Kutoa suluhisho la uhandisi wa umeme na maji salama, ya kuaminika na ya bei nafuu ambayo yanaboresha ubora wa maisha ya Watanzania.",
            ),
            "values": [
                {"title": _t("Integrity", "Uadilifu"), "text": _t("We act with honesty and transparency in everything we do.", "Tunafanya kwa uaminifu na uwazi katika kila tunachofanya."), "icon": "shield"},
                {"title": _t("Excellence", "Ubora"), "text": _t("We hold ourselves to the highest professional and technical standards.", "Tunajiweka katika viwango vya juu zaidi vya kitaalamu na kiufundi."), "icon": "star"},
                {"title": _t("Safety First", "Usalama Kwanza"), "text": _t("No project is so urgent that we cannot take time to do it safely.", "Hakuna mradi wa haraka kiasi kwamba hatuwezi kuchukua muda wa kuufanya kwa usalama."), "icon": "shield-check"},
                {"title": _t("Community Impact", "Athari kwa Jamii"), "text": _t("We measure our success by the positive impact we create in the communities we serve.", "Tunapima mafanikio yetu kwa athari nzuri tunayoiunda katika jamii tunazohudumia."), "icon": "users"},
            ],
            "hse_statement": _t(
                "Health, Safety and Environment (HSE) is at the core of every project we undertake. We comply with all OSHA regulations and maintain a zero-tolerance policy for unsafe work practices.",
                "Afya, Usalama na Mazingira (HSE) ni msingi wa kila mradi tunaoufanya. Tunafuata kanuni zote za OSHA na kudumisha sera ya kutovumilia kwa mazoea ya kazi yasiyo salama.",
            ),
            "story_image": _img("construction", "Our Story", "Historia Yetu", 900, 700),
            "profile_pdf": "",
        },
        {
            "key": "privacy",
            "title": _t("Privacy Policy", "Sera ya Faragha"),
            "intro": _t(
                "Your privacy is important to us. This policy explains how Kilele Power & Water Engineering Ltd collects, uses and protects your personal information.",
                "Faragha yako ni muhimu kwetu. Sera hii inaeleza jinsi Kilele Power & Water Engineering Ltd inavyokusanya, kutumia na kulinda taarifa zako binafsi.",
            ),
            "body": _t(
                "<h2>Information We Collect</h2>"
                "<p>We collect personal information that you voluntarily provide through our contact forms, service request forms and training application forms. This includes your name, email address, phone number and the nature of your enquiry.</p>"
                "<h2>How We Use Your Information</h2>"
                "<p>We use the information you provide solely to respond to your enquiry, process your service request or training application, and to improve our services. We do not sell, trade or transfer your personal information to third parties.</p>"
                "<h2>Data Security</h2>"
                "<p>We implement appropriate technical and organisational measures to protect your personal information against unauthorised access, alteration, disclosure or destruction.</p>"
                "<h2>Contact Us</h2>"
                "<p>If you have any questions about this privacy policy, please contact us at <a href='mailto:info@kileleengineering.co.tz'>info@kileleengineering.co.tz</a>.</p>",
                "<h2>Taarifa Tunazokusanya</h2>"
                "<p>Tunakusanya taarifa binafsi unazotoa kwa hiari kupitia fomu zetu za mawasiliano, fomu za maombi ya huduma na fomu za maombi ya mafunzo.</p>"
                "<h2>Jinsi Tunavyotumia Taarifa Zako</h2>"
                "<p>Tunatumia taarifa unazotoa tu kujibu maswali yako, kushughulikia ombi lako la huduma au mafunzo, na kuboresha huduma zetu.</p>"
                "<h2>Usalama wa Data</h2>"
                "<p>Tunatekeleza hatua zinazofaa za kiufundi na za kiutaratibu kulinda taarifa zako binafsi dhidi ya ufikiaji usioidhinishwa.</p>",
            ),
            "banner": _img("office", "Privacy Policy", "Sera ya Faragha", 1600, 500),
            "seo": _seo("Privacy Policy | Kilele Power & Water Engineering", "Privacy policy for Kilele Power & Water Engineering Ltd."),
        },
    ]
    for pd in pages_data:
        key = pd["key"]
        existing = await Page.find_one(Page.key == key)
        if existing:
            logger.info("Page '%s' already seeded", key)
            continue
        page = Page(**pd)
        await page.insert()
        logger.info("Page '%s' seeded", key)


async def seed_service_categories() -> None:
    from app.models.services import ServiceCategory
    if await ServiceCategory.count() > 0:
        logger.info("ServiceCategories already seeded")
        return
    cats = [
        ServiceCategory(name=_t("Electricity", "Umeme"),
                        slug="electricity", icon="bolt", colour="#F59E0B", sort=1,
                        created_at=NOW, updated_at=NOW),
        ServiceCategory(name=_t("Water", "Maji"),
                        slug="water", icon="droplet", colour="#0EA5E9", sort=2,
                        created_at=NOW, updated_at=NOW),
    ]
    for c in cats:
        await c.insert()
    logger.info("ServiceCategories seeded")


async def seed_services() -> None:
    from app.models.services import Service, ServiceCategory
    if await Service.count() > 0:
        logger.info("Services already seeded")
        return

    elec = await ServiceCategory.find_one({"slug": "electricity"})
    water = await ServiceCategory.find_one({"slug": "water"})
    elec_id = str(elec.id) if elec else ""
    water_id = str(water.id) if water else ""

    # (slug, title_en, title_sw, desc_en, desc_sw, cat_id, is_featured, photo_category)
    services_data = [
        (
            "building-wiring", "Building Wiring", "Wiring wa Majengo",
            "New wiring and electrical renovation for homes, offices, shops and industries to safety standards.",
            "Wiring mpya na ukarabati wa umeme kwa nyumba, ofisi, maduka na viwanda kwa viwango vya usalama.",
            elec_id, True, "electricity",
        ),
        (
            "power-lines", "Power Line Construction", "Ujenzi wa Njia za Umeme",
            "Construction of low and medium voltage (LV/MV) lines including pole installation.",
            "Ujenzi wa njia za msongo mdogo na wa kati (LV/MV), pamoja na usimikaji wa nguzo.",
            elec_id, True, "electricity",
        ),
        (
            "transformer-installation", "Transformer Installation", "Ufungaji wa Transfoma",
            "Installation, testing and maintenance of transformers for industries and residential areas.",
            "Ufungaji, upimaji na matengenezo ya transfoma kwa viwanda na makazi.",
            elec_id, False, "electricity",
        ),
        (
            "solar-systems", "Solar Power Systems", "Mifumo ya Umeme wa Jua",
            "Design and installation of solar systems for homes, schools, clinics and businesses.",
            "Kusanifu na kufunga mifumo ya solar kwa nyumba, shule, zahanati na biashara.",
            elec_id, False, "electricity",
        ),
        (
            "street-lighting", "Street & Security Lighting", "Taa za Barabarani na Ulinzi",
            "Installation of street lights, parking areas and security lighting.",
            "Ufungaji wa taa za barabarani, maeneo ya maegesho na taa za ulinzi.",
            elec_id, False, "electricity",
        ),
        (
            "electrical-inspection", "Inspection & Maintenance", "Ukaguzi na Matengenezo",
            "Electrical system inspection, testing and regular maintenance.",
            "Ukaguzi wa mifumo ya umeme, upimaji (testing) na matengenezo ya mara kwa mara.",
            elec_id, False, "electricity",
        ),
        (
            "borehole-drilling", "Borehole Drilling", "Uchimbaji wa Visima",
            "Groundwater research, borehole drilling and completion.",
            "Utafiti wa maji chini ya ardhi, uchimbaji na ukamilishaji wa visima virefu.",
            water_id, True, "water",
        ),
        (
            "pump-installation", "Pump Installation", "Ufungaji wa Pampu",
            "Installation of electric and solar pumps for boreholes and water tanks.",
            "Ufungaji wa pampu za umeme na za nishati ya jua kwa visima na matenki.",
            water_id, True, "water",
        ),
        (
            "water-distribution", "Water Distribution Systems", "Mifumo ya Usambazaji Maji",
            "Design and construction of water distribution networks for villages, institutions and housing.",
            "Kusanifu na kujenga mitandao ya usambazaji maji kwa vijiji, taasisi na makazi.",
            water_id, False, "water",
        ),
        (
            "pipe-laying", "Pipe Laying", "Ulazaji wa Mabomba",
            "Installation of main and distribution pipes including network extensions.",
            "Ulazaji wa mabomba makuu na ya kusambaza, pamoja na upanuzi wa mtandao.",
            water_id, False, "water",
        ),
        (
            "water-tanks", "Water Tanks & Towers", "Matenki na Minara ya Maji",
            "Construction and installation of underground and elevated water tanks.",
            "Ujenzi na ufungaji wa matenki ya ardhini na ya juu.",
            water_id, False, "water",
        ),
        (
            "water-maintenance", "Water System Maintenance", "Matengenezo ya Mifumo ya Maji",
            "Fixing leaks, replacing pumps and maintaining existing water systems.",
            "Kurekebisha uvujaji, kubadilisha pampu na kutunza mifumo iliyopo.",
            water_id, False, "water",
        ),
    ]

    for slug, title_en, title_sw, desc_en, desc_sw, cat_id, is_featured, photo_cat in services_data:
        s = Service(
            status="published",
            slug=slug,
            slug_sw=slug,
            category_id=cat_id,
            title=_t(title_en, title_sw),
            icon="wrench",
            cover=_img(photo_cat, title_en, title_sw, 900, 600),
            summary=_t(desc_en, desc_sw),
            body=_t(f"<p>{desc_en}</p>", f"<p>{desc_sw}</p>"),
            included=[
                _t("Site survey and assessment", "Ukaguzi wa eneo"),
                _t("Engineering design", "Usanifu wa uhandisi"),
                _t("Material procurement", "Ununuzi wa vifaa"),
                _t("Construction and installation", "Ujenzi na ufungaji"),
                _t("Testing and handover", "Upimaji na makabidhiano"),
            ],
            is_featured=is_featured,
            seo=_seo(f"{title_en} | Kilele Power & Water Engineering", desc_en),
            created_at=NOW, updated_at=NOW,
        )
        await s.insert()
    logger.info("Services seeded (%d)", len(services_data))


async def seed_projects() -> None:
    from app.models.projects import Project
    from app.models.services import ServiceCategory
    if await Project.count() > 0:
        logger.info("Projects already seeded")
        return

    elec = await ServiceCategory.find_one({"slug": "electricity"})
    water = await ServiceCategory.find_one({"slug": "water"})
    elec_id = str(elec.id) if elec else ""
    water_id = str(water.id) if water else ""

    # (slug, title_en, title_sw, cat_id, loc, year, proj_status, photo_cat, desc_en, desc_sw)
    projects = [
        (
            "grain-mill-electrical",
            "Grain Mill Electrical Installation",
            "Umeme kwa Kiwanda cha Kusindika Nafaka",
            elec_id, "Mbezi, Dar es Salaam", 2024, "completed", "electricity",
            "Installation of a 315kVA transformer and complete factory wiring.",
            "Ufungaji wa transfoma ya 315kVA na wiring kamili wa kiwanda.",
        ),
        (
            "mvumi-village-water",
            "Mvumi Village Water System",
            "Mfumo wa Maji Kijiji cha Mvumi",
            water_id, "Chamwino, Dodoma", 2023, "completed", "water",
            "Borehole drilling, solar pump, 50,000-litre tank and 6 water collection points.",
            "Uchimbaji wa kisima, pampu ya solar, tenki la lita 50,000 na vituo 6 vya kuchotea maji.",
        ),
        (
            "clinic-solar-4",
            "Solar for 4 Health Clinics",
            "Solar kwa Zahanati 4",
            elec_id, "Kongwa, Dodoma", 2024, "completed", "electricity",
            "Battery-backed solar systems for night services and vaccine refrigerators.",
            "Mifumo ya solar yenye betri kwa huduma za usiku na majokofu ya chanjo.",
        ),
        (
            "kibaha-pipe-network",
            "Kibaha Pipe Network Extension",
            "Upanuzi wa Mtandao wa Mabomba",
            water_id, "Kibaha, Pwani", 2025, "ongoing", "water",
            "8km pipe laying to reach 1,200 households.",
            "Ulazaji wa mabomba km 8 kufikisha maji kwa kaya 1,200.",
        ),
        (
            "morogoro-street-lights",
            "Town Street Lighting",
            "Taa za Barabarani Mji Mdogo",
            elec_id, "Morogoro", 2023, "completed", "electricity",
            "Installation of 150 solar street lights.",
            "Ufungaji wa taa 150 za solar za barabarani.",
        ),
        (
            "singida-school-boreholes",
            "Boreholes for 5 Secondary Schools",
            "Visima kwa Shule 5 za Sekondari",
            water_id, "Singida", 2025, "ongoing", "water",
            "Borehole drilling and tank systems for 5 schools.",
            "Uchimbaji wa visima na mifumo ya matenki kwa shule 5.",
        ),
    ]

    for idx, row in enumerate(projects):
        (slug, title_en, title_sw, cat_id, loc, year,
         proj_status, photo_cat, desc_en, desc_sw) = row
        end_date = date(year, 12, 31) if proj_status == "completed" else None
        start_date = date(year, 1, 1)
        p = Project(
            status="published",
            slug=slug,
            slug_sw=slug,
            sort=idx + 1,
            category_id=cat_id,
            title=_t(title_en, title_sw),
            client_name="",
            location=loc,
            region=loc.split(",")[-1].strip(),
            start_date=start_date,
            end_date=end_date,
            value_tzs=0,
            hide_value=True,
            project_status=proj_status,
            summary=_t(desc_en, desc_sw),
            scope=_t(f"<p>{desc_en}</p>", f"<p>{desc_sw}</p>"),
            outcome=_t(
                "<p>Project completed successfully. All systems tested and handed over with full documentation.</p>",
                "<p>Mradi ulikamilika kwa mafanikio. Mifumo yote ilijaribiwa na kukabidhiwa na nyaraka kamili.</p>",
            ) if end_date else _t("<p>Project currently underway and on schedule.</p>", "<p>Mradi unaendelea na uko kwenye ratiba.</p>"),
            cover=_img(photo_cat, title_en, title_sw, 900, 600),
            is_featured=idx < 2,
            seo=_seo(f"{title_en} | Kilele Power & Water Engineering", desc_en),
            created_at=NOW, updated_at=NOW,
        )
        await p.insert()
    logger.info("Projects seeded (%d)", len(projects))


async def seed_training() -> None:
    from app.models.training import TrainingProgramme, TrainingIntake, TrainingStep
    if await TrainingProgramme.count() > 0:
        logger.info("Training already seeded")
        return

    programmes = [
        TrainingProgramme(
            status="published",
            slug="electrical-wiring",
            slug_sw="wiring-na-ufungaji-wa-umeme",
            sort=1,
            title=_t("Building Wiring & Electrical Installation", "Wiring na Ufungaji wa Umeme"),
            cover=_img("electricity", "Building Wiring Training", "Mafunzo ya Wiring", 900, 600),
            summary=_t(
                "Hands-on training covering building wiring, electrical installation and safety standards.",
                "Mafunzo ya vitendo yanayoshughulikia wiring ya majengo, ufungaji wa umeme na viwango vya usalama.",
            ),
            audience=_t(
                "Form four graduates and beginner technicians.",
                "Wahitimu wa kidato cha nne na mafundi wanaoanza.",
            ),
            requirements=_t(
                "Form IV certificate.",
                "Cheti cha Kidato cha Nne.",
            ),
            outline=_t(
                "<p><strong>Week 1–2:</strong> Electrical theory and wiring regulations<br>"
                "<strong>Week 3–4:</strong> Practical installation and testing<br>"
                "<strong>Week 5–6:</strong> Safety, assessment and certification</p>",
                "<p><strong>Wiki 1–2:</strong> Nadharia ya umeme na kanuni za wiring<br>"
                "<strong>Wiki 3–4:</strong> Ufungaji wa vitendo na majaribio<br>"
                "<strong>Wiki 5–6:</strong> Usalama, tathmini na utoaji wa cheti</p>",
            ),
            duration=_t("6 weeks", "Wiki 6"),
            mode="classroom",
            fee_tzs=350_000,
            certificate=_t(
                "Certificate in Building Wiring & Electrical Installation",
                "Cheti cha Wiring na Ufungaji wa Umeme",
            ),
            venue=_t(
                "Kilele Power & Water Engineering Training Centre, Dar es Salaam",
                "Kituo cha Mafunzo cha Kilele Power & Water Engineering, Dar es Salaam",
            ),
            is_open=True,
            seo=_seo(
                "Building Wiring & Electrical Installation Training | Kilele",
                "Hands-on building wiring and electrical installation training in Tanzania.",
            ),
            created_at=NOW, updated_at=NOW,
        ),
        TrainingProgramme(
            status="published",
            slug="solar-installation",
            slug_sw="ufungaji-wa-mifumo-ya-solar",
            sort=2,
            title=_t("Solar System Installation", "Ufungaji wa Mifumo ya Solar"),
            cover=_img("electricity", "Solar Installation Training", "Mafunzo ya Solar", 900, 600),
            summary=_t(
                "Practical training on the installation and maintenance of solar power systems.",
                "Mafunzo ya vitendo ya ufungaji na matengenezo ya mifumo ya nishati ya jua.",
            ),
            audience=_t(
                "Electrical technicians.",
                "Mafundi wa umeme.",
            ),
            requirements=_t(
                "Basic electrical knowledge or Form IV certificate.",
                "Ujuzi wa msingi wa umeme au cheti cha Kidato cha Nne.",
            ),
            outline=_t(
                "<p><strong>Week 1:</strong> Solar fundamentals and system sizing<br>"
                "<strong>Week 2:</strong> Panel, inverter and battery installation<br>"
                "<strong>Week 3:</strong> Testing, commissioning and maintenance</p>",
                "<p><strong>Wiki 1:</strong> Misingi ya solar na upangaji wa mfumo<br>"
                "<strong>Wiki 2:</strong> Ufungaji wa paneli, inverter na betri<br>"
                "<strong>Wiki 3:</strong> Upimaji, uzinduzi na matengenezo</p>",
            ),
            duration=_t("3 weeks", "Wiki 3"),
            mode="classroom",
            fee_tzs=250_000,
            certificate=_t(
                "Certificate in Solar System Installation",
                "Cheti cha Ufungaji wa Mifumo ya Solar",
            ),
            venue=_t(
                "Kilele Power & Water Engineering Training Centre, Dar es Salaam",
                "Kituo cha Mafunzo cha Kilele Power & Water Engineering, Dar es Salaam",
            ),
            is_open=True,
            seo=_seo(
                "Solar System Installation Training | Kilele",
                "Practical solar system installation training for electrical technicians.",
            ),
            created_at=NOW, updated_at=NOW,
        ),
        TrainingProgramme(
            status="published",
            slug="plumbing-water",
            slug_sw="ufundi-bomba-na-mifumo-ya-maji",
            sort=3,
            title=_t("Plumbing & Water Systems", "Ufundi Bomba na Mifumo ya Maji"),
            cover=_img("water", "Plumbing Training", "Mafunzo ya Ufundi Bomba", 900, 600),
            summary=_t(
                "Training on plumbing and water system installation and maintenance.",
                "Mafunzo ya ufundi bomba na ufungaji na matengenezo ya mifumo ya maji.",
            ),
            audience=_t(
                "Form four graduates and beginner technicians.",
                "Wahitimu wa kidato cha nne na mafundi wanaoanza.",
            ),
            requirements=_t(
                "Form IV certificate.",
                "Cheti cha Kidato cha Nne.",
            ),
            outline=_t(
                "<p><strong>Week 1:</strong> Plumbing fundamentals and pipe materials<br>"
                "<strong>Week 2–3:</strong> Pipe laying and fitting installation<br>"
                "<strong>Week 4:</strong> Pump systems, testing and assessment</p>",
                "<p><strong>Wiki 1:</strong> Misingi ya ufundi bomba na vifaa vya mabomba<br>"
                "<strong>Wiki 2–3:</strong> Ulazaji wa mabomba na ufungaji wa vifaa<br>"
                "<strong>Wiki 4:</strong> Mifumo ya pampu, majaribio na tathmini</p>",
            ),
            duration=_t("4 weeks", "Wiki 4"),
            mode="classroom",
            fee_tzs=280_000,
            certificate=_t(
                "Certificate in Plumbing & Water Systems",
                "Cheti cha Ufundi Bomba na Mifumo ya Maji",
            ),
            venue=_t(
                "Kilele Power & Water Engineering Training Centre, Dar es Salaam",
                "Kituo cha Mafunzo cha Kilele Power & Water Engineering, Dar es Salaam",
            ),
            is_open=True,
            seo=_seo(
                "Plumbing & Water Systems Training | Kilele",
                "Practical plumbing and water systems training in Tanzania.",
            ),
            created_at=NOW, updated_at=NOW,
        ),
    ]

    inserted_programmes = []
    for p in programmes:
        await p.insert()
        inserted_programmes.append(p)
    logger.info("Training programmes seeded (%d)", len(programmes))

    # Intakes
    for prog in inserted_programmes[:2]:
        prog_id = str(prog.id)
        await TrainingIntake(
            programme_id=prog_id,
            start_date=date(2026, 1, 13),
            end_date=date(2026, 2, 7),
            venue=_t("Dar es Salaam", "Dar es Salaam"),
            seats=25,
            status="open",
            created_at=NOW, updated_at=NOW,
        ).insert()
        await TrainingIntake(
            programme_id=prog_id,
            start_date=date(2026, 4, 7),
            end_date=date(2026, 5, 2),
            venue=_t("Arusha", "Arusha"),
            seats=20,
            status="open",
            created_at=NOW, updated_at=NOW,
        ).insert()
    logger.info("Training intakes seeded")

    if await TrainingStep.count() > 0:
        logger.info("TrainingSteps already seeded")
        return
    steps = [
        TrainingStep(number=1, title=_t("Apply Online", "Jaza Fomu Mtandaoni"),
                     text=_t("Fill in the online application form.", "Jaza fomu ya maombi mtandaoni."),
                     icon="file-text"),
        TrainingStep(number=2, title=_t("Application Review", "Ukaguzi wa Maombi"),
                     text=_t("Applications are reviewed.", "Maombi yanakaguliwa."),
                     icon="search"),
        TrainingStep(number=3, title=_t("Notification", "Taarifa"),
                     text=_t("Selected candidates are notified by phone or SMS.", "Waliochaguliwa wanajulishwa kwa simu au SMS."),
                     icon="bell"),
        TrainingStep(number=4, title=_t("Fee Payment", "Kulipa Ada"),
                     text=_t("Pay fees and confirm your place.", "Kulipa ada na kuthibitisha nafasi."),
                     icon="credit-card"),
        TrainingStep(number=5, title=_t("Training", "Mafunzo"),
                     text=_t("Classroom and hands-on practical training.", "Mafunzo ya darasani na ya vitendo kazini."),
                     icon="book-open"),
        TrainingStep(number=6, title=_t("Assessment", "Tathmini"),
                     text=_t("Final assessment.", "Tathmini ya mwisho."),
                     icon="clipboard-check"),
        TrainingStep(number=7, title=_t("Certificate Award", "Kutunukiwa Cheti"),
                     text=_t("Certificate award.", "Kutunukiwa cheti."),
                     icon="award"),
    ]
    for step in steps:
        await step.insert()
    logger.info("TrainingSteps seeded")


async def seed_team() -> None:
    from app.models.team import TeamMember, Certification
    if await TeamMember.count() > 0:
        logger.info("Team already seeded")
        return
    members = [
        TeamMember(
            name="Eng. James Mwangi",
            position=_t("Managing Director & CEO", "Mkurugenzi Mtendaji"),
            bio=_t(
                "James founded Volt & Water Engineering in 2009 and has over 20 years of experience in power systems and project management. He holds a BSc in Electrical Engineering from UDSM and an MBA from the University of Cape Town.",
                "James alianzisha Volt & Water Engineering mwaka 2009 na ana uzoefu wa zaidi ya miaka 20 katika mifumo ya nguvu na usimamizi wa miradi.",
            ),
            photo=_img("people", "James Mwangi", "James Mwangi", 400, 400),
            sort=1, is_active=True,
        ),
        TeamMember(
            name="Eng. Fatuma Rashid",
            position=_t("Head of Water Engineering", "Mkuu wa Uhandisi wa Maji"),
            bio=_t(
                "Fatuma specialises in rural water supply and sanitation. She has led water projects in 14 regions of Tanzania and holds an MSc in Water Engineering from IHE Delft, Netherlands.",
                "Fatuma ni mtaalamu wa maji ya vijijini na usafi wa mazingira. Ameongoza miradi ya maji katika mikoa 14 ya Tanzania.",
            ),
            photo=_img("people", "Fatuma Rashid", "Fatuma Rashid", 400, 400),
            sort=2, is_active=True,
        ),
        TeamMember(
            name="Eng. Peter Kimaro",
            position=_t("Senior Electrical Engineer", "Mhandisi Mkuu wa Umeme"),
            bio=_t(
                "Peter leads our grid connection and solar installation divisions. He has 12 years of experience with TANESCO grid projects and renewable energy systems across East Africa.",
                "Peter anaongoza vitengo vyetu vya muunganiko wa gridi na ufungaji wa jua. Ana uzoefu wa miaka 12 na miradi ya gridi ya TANESCO.",
            ),
            photo=_img("people", "Peter Kimaro", "Peter Kimaro", 400, 400),
            sort=3, is_active=True,
        ),
        TeamMember(
            name="Ms. Grace Msigwa",
            position=_t("Training & HR Manager", "Meneja wa Mafunzo na Rasilimali Watu"),
            bio=_t(
                "Grace manages our professional training programmes and human resources. She has trained over 500 engineers and technicians since joining Volt & Water in 2015.",
                "Grace anasimamia mipango yetu ya mafunzo ya kitaalamu na rasilimali watu. Amefundisha wahandisi na mafundi zaidi ya 500 tangu kujiunga na Volt & Water mwaka 2015.",
            ),
            photo=_img("people", "Grace Msigwa", "Grace Msigwa", 400, 400),
            sort=4, is_active=True,
        ),
        TeamMember(
            name="Eng. Mohamed Juma",
            position=_t("Projects Manager", "Meneja wa Miradi"),
            bio=_t(
                "Mohamed oversees all ongoing construction projects, ensuring they are delivered on time and to specification. He holds a BSc in Civil Engineering and a PMP certification.",
                "Mohamed anasimamia miradi yote ya ujenzi inayoendelea, kuhakikisha imetolewa kwa wakati na kulingana na maelezo.",
            ),
            photo=_img("people", "Mohamed Juma", "Mohamed Juma", 400, 400),
            sort=5, is_active=True,
        ),
        TeamMember(
            name="Ms. Amina Saleh",
            position=_t("Finance & Contracts Manager", "Meneja wa Fedha na Mikataba"),
            bio=_t(
                "Amina manages the company's finances, procurement and contract administration. She is a Certified Public Accountant (CPA-T) with 10 years of experience in infrastructure finance.",
                "Amina anasimamia fedha za kampuni, ununuzi na usimamizi wa mikataba. Yeye ni Mhasibu wa Umma Aliyeidhinishwa (CPA-T) mwenye uzoefu wa miaka 10.",
            ),
            photo=_img("people", "Amina Saleh", "Amina Saleh", 400, 400),
            sort=6, is_active=True,
        ),
    ]
    for m in members:
        await m.insert()
    logger.info("Team members seeded")

    if await Certification.count() > 0:
        logger.info("Certifications already seeded")
        return
    certs = [
        Certification(name=_t("Engineers Registration Board (ERB)", "Bodi ya Usajili wa Wahandisi (ERB)"),
                      issuer="ERB Tanzania", number="",
                      logo=_img("office", "ERB", "ERB", 300, 150), sort=1),
        Certification(name=_t("Contractors Registration Board (CRB)", "Bodi ya Wakandarasi (CRB)"),
                      issuer="CRB Tanzania", number="",
                      logo=_img("office", "CRB", "CRB", 300, 150), sort=2),
        Certification(name=_t("EWURA Electrical Installation Licence", "Leseni ya EWURA ya Ufungaji wa Umeme"),
                      issuer="EWURA", number="",
                      logo=_img("electricity", "EWURA", "EWURA", 300, 150), sort=3),
        Certification(name=_t("BRELA Business Registration", "Usajili wa BRELA"),
                      issuer="BRELA Tanzania", number="",
                      logo=_img("office", "BRELA", "BRELA", 300, 150), sort=4),
    ]
    for c in certs:
        await c.insert()
    logger.info("Certifications seeded")


async def seed_clients() -> None:
    from app.models.clients import Client, Testimonial
    if await Client.count() > 0:
        logger.info("Clients already seeded")
        return
    clients_data = [
        ("TANESCO", "government", True),
        ("DAWASA", "government", True),
        ("REA Tanzania", "government", True),
        ("EWURA", "government", True),
        ("Ministry of Water", "government", False),
        ("Mbeya City Council", "government", False),
        ("Vodacom Tanzania", "private", True),
        ("Azam Group", "private", True),
        ("Twiga Cement", "private", False),
        ("Precision Air", "private", False),
        ("WaterAid Tanzania", "ngo", True),
        ("UNICEF Tanzania", "ngo", True),
        ("Concern Worldwide", "ngo", False),
        ("World Vision Tanzania", "ngo", False),
    ]
    for idx, (name, ctype, is_featured) in enumerate(clients_data):
        await Client(
            name=name,
            logo=_img("office", name, name, 300, 150),
            type=ctype, url="", is_featured=is_featured, sort=idx + 1,
        ).insert()
    logger.info("Clients seeded (%d)", len(clients_data))

    if await Testimonial.count() > 0:
        logger.info("Testimonials already seeded")
        return
    testimonials = [
        Testimonial(
            name="Village Chairman",
            position=_t("Village Chairman, Chamwino", "Mwenyekiti wa Kijiji, Chamwino"),
            organisation="Chamwino",
            photo=_img("people", "Village Chairman", "Mwenyekiti", 300, 300),
            quote=_t(
                "They installed the water system in our village on time. Mothers no longer walk long distances to fetch water.",
                "Walitufungia mfumo wa maji kijijini kwetu kwa muda waliouahidi. Sasa akina mama hawatembei tena umbali mrefu kutafuta maji.",
            ),
            rating=5, sort=1, is_active=True,
        ),
        Testimonial(
            name="Factory Manager",
            position=_t("Factory Manager, Dar es Salaam", "Meneja wa Kiwanda, Dar es Salaam"),
            organisation="Dar es Salaam",
            photo=_img("people", "Factory Manager", "Meneja wa Kiwanda", 300, 300),
            quote=_t(
                "The electrical work at our factory was done with great care and safety. We have had no problems since.",
                "Kazi ya umeme kiwandani kwetu ilifanywa kwa umakini na usalama mkubwa. Tangu hapo hatujapata tatizo.",
            ),
            rating=5, sort=2, is_active=True,
        ),
        Testimonial(
            name="Clinic Medical Officer",
            position=_t("Clinic Medical Officer, Kongwa", "Daktari Mkuu wa Zahanati, Kongwa"),
            organisation="Kongwa",
            photo=_img("people", "Medical Officer", "Daktari", 300, 300),
            quote=_t(
                "The solar they installed allows us to treat patients at night without worry.",
                "Solar waliyotufungia inatuwezesha kuhudumia wagonjwa usiku bila wasiwasi.",
            ),
            rating=5, sort=3, is_active=True,
        ),
    ]
    for t in testimonials:
        await t.insert()
    logger.info("Testimonials seeded")


async def seed_posts() -> None:
    from app.models.posts import Post
    if await Post.count() > 0:
        logger.info("Posts already seeded")
        return
    posts = [
        (
            "mvumi-water-project-complete",
            "Mvumi Village Water Project Complete",
            "Tumekamilisha Mradi wa Maji Kijiji cha Mvumi",
            "news", True, "water",
            "More than 3,000 residents now have clean water close to their homes. The project included borehole drilling, solar pump installation and 6 collection points.",
            "Wakazi zaidi ya 3,000 sasa wanapata maji safi karibu na makazi yao. Mradi ulijumuisha uchimbaji wa kisima, ufungaji wa pampu ya solar na vituo 6 vya kuchotea.",
        ),
        (
            "solar-training-intake-open",
            "Solar Training Intake Now Open",
            "Usajili wa Mafunzo ya Solar Umefunguliwa",
            "announcement", True, "electricity",
            "25 places available for the intake starting next month. Apply online now.",
            "Nafasi 25 kwa awamu inayoanza mwezi ujao. Omba sasa mtandaoni.",
        ),
        (
            "sabasaba-exhibition",
            "Visit Us at Sabasaba Exhibition",
            "Tutakuwepo Maonesho ya Sabasaba",
            "event", False, "electricity",
            "Visit our stand to learn about our electrical and water services. Free consultations available.",
            "Tembelea banda letu kujifunza kuhusu huduma zetu za umeme na maji. Ushauri bila malipo.",
        ),
    ]
    for slug, title_en, title_sw, cat, is_featured, photo_cat, excerpt_en, excerpt_sw in posts:
        body_en = (
            f"<p>{excerpt_en}</p>"
            "<p>For more information, please <a href='/contact'>contact us</a> or submit a <a href='/request-service'>service request</a>.</p>"
        )
        await Post(
            status="published",
            slug=slug,
            slug_sw=slug,
            sort=0,
            category=cat,
            title=_t(title_en, title_sw),
            cover=_img(photo_cat, title_en, title_sw, 900, 600),
            excerpt=_t(excerpt_en, excerpt_sw),
            body=_t(body_en, f"<p>{excerpt_sw}</p>"),
            published_at=NOW,
            is_featured=is_featured,
            seo=_seo(f"{title_en} | Kilele Power & Water Engineering", excerpt_en[:160]),
            created_at=NOW, updated_at=NOW,
        ).insert()
    logger.info("Posts seeded (%d)", len(posts))


async def seed_gallery() -> None:
    from app.models.gallery import GalleryAlbum
    if await GalleryAlbum.count() > 0:
        logger.info("Gallery already seeded")
        return
    albums = [
        GalleryAlbum(
            status="published",
            slug="dar-es-salaam-grid-upgrade-gallery",
            slug_sw="gallery-ya-uboreshaji-wa-gridi-dar",
            sort=1,
            title=_t("Dar es Salaam Grid Upgrade — Project Gallery", "Picha za Mradi wa Uboreshaji wa Gridi Dar es Salaam"),
            category="projects",
            cover=_img("electricity", "Grid Upgrade", "Uboreshaji wa Gridi", 900, 600),
            items=[
                {"type": "photo", "image": _img("electricity", "MV line upgrade", "Uboreshaji wa mstari wa MV", 900, 600), "video_url": "", "caption": _t("MV line stringing in Kinondoni", "Kupiga waya wa MV Kinondoni")},
                {"type": "photo", "image": _img("electricity", "Transformer installation", "Ufungaji wa transfoma", 900, 600), "video_url": "", "caption": _t("Distribution transformer installation", "Ufungaji wa transfoma ya usambazaji")},
                {"type": "photo", "image": _img("construction", "Site work", "Kazi ya eneo", 900, 600), "video_url": "", "caption": _t("Cable laying and jointing", "Uwekaji na uunganishaji wa kebo")},
                {"type": "photo", "image": _img("electricity", "Completed installation", "Ufungaji uliokamilika", 900, 600), "video_url": "", "caption": _t("Completed substation at Ilala", "Kituo kidogo kilichokamilika Ilala")},
            ],
            seo=_seo("Dar es Salaam Grid Upgrade Gallery | Volt & Water", "Photos from the TANESCO Dar es Salaam grid upgrade project."),
            created_at=NOW, updated_at=NOW,
        ),
        GalleryAlbum(
            status="published",
            slug="dodoma-water-supply-gallery",
            slug_sw="gallery-ya-maji-dodoma",
            sort=2,
            title=_t("Dodoma Rural Water Supply — Project Gallery", "Picha za Mradi wa Maji Vijijini Dodoma"),
            category="projects",
            cover=_img("water", "Water Supply Project", "Mradi wa Maji", 900, 600),
            items=[
                {"type": "photo", "image": _img("water", "Borehole drilling", "Uchimbaji wa kisima", 900, 600), "video_url": "", "caption": _t("Borehole drilling in Chamwino", "Uchimbaji wa kisima Chamwino")},
                {"type": "photo", "image": _img("water", "Pipe laying", "Uwekaji wa bomba", 900, 600), "video_url": "", "caption": _t("Distribution pipe laying", "Uwekaji wa bomba la usambazaji")},
                {"type": "photo", "image": _img("construction", "Pump installation", "Ufungaji wa pampu", 900, 600), "video_url": "", "caption": _t("Solar pump installation", "Ufungaji wa pampu ya jua")},
                {"type": "photo", "image": _img("water", "Water point", "Kisima cha maji", 900, 600), "video_url": "", "caption": _t("Community water point, Kondoa", "Kisima cha jamii, Kondoa")},
            ],
            seo=_seo("Dodoma Water Supply Gallery | Volt & Water", "Photos from the Dodoma rural water supply project."),
            created_at=NOW, updated_at=NOW,
        ),
        GalleryAlbum(
            status="published",
            slug="solar-installations-gallery",
            slug_sw="gallery-ya-ufungaji-wa-jua",
            sort=3,
            title=_t("Solar Power Installations Gallery", "Picha za Ufungaji wa Nishati ya Jua"),
            category="projects",
            cover=_img("solar", "Solar Installation", "Ufungaji wa Jua", 900, 600),
            items=[
                {"type": "photo", "image": _img("solar", "Rooftop solar", "Jua la juu ya paa", 900, 600), "video_url": "", "caption": _t("5kW rooftop installation, Dar es Salaam", "Ufungaji wa 5kW juu ya paa, Dar es Salaam")},
                {"type": "photo", "image": _img("solar", "Solar farm", "Shamba la jua", 900, 600), "video_url": "", "caption": _t("Arusha solar farm groundwork", "Kazi za ujenzi wa shamba la jua Arusha")},
                {"type": "photo", "image": _img("solar", "Battery storage", "Hifadhi ya betri", 900, 600), "video_url": "", "caption": _t("Battery bank installation", "Ufungaji wa betri")},
            ],
            seo=_seo("Solar Installations Gallery | Volt & Water", "Photos of solar power installations by Volt & Water Engineering."),
            created_at=NOW, updated_at=NOW,
        ),
        GalleryAlbum(
            status="published",
            slug="training-graduation-2025",
            slug_sw="kuhitimu-mafunzo-2025",
            sort=4,
            title=_t("Training Graduation Ceremony 2025", "Sherehe ya Kuhitimu Mafunzo 2025"),
            category="training",
            cover=_img("training", "Training Graduation", "Kuhitimu Mafunzo", 900, 600),
            items=[
                {"type": "photo", "image": _img("training", "Certificate presentation", "Usambazaji wa vyeti", 900, 600), "video_url": "", "caption": _t("Certificate presentation ceremony", "Sherehe ya usambazaji wa vyeti")},
                {"type": "photo", "image": _img("training", "Practical training", "Mafunzo ya vitendo", 900, 600), "video_url": "", "caption": _t("Practical electrical wiring session", "Kipindi cha wiring ya umeme cha vitendo")},
                {"type": "photo", "image": _img("people", "Class photo", "Picha ya darasa", 900, 600), "video_url": "", "caption": _t("Graduates — Electrical Installation cohort", "Wahitimu — kikundi cha Ufungaji wa Umeme")},
            ],
            seo=_seo("Training Graduation 2025 | Volt & Water", "Photos from our 2025 training graduation ceremony."),
            created_at=NOW, updated_at=NOW,
        ),
    ]
    for a in albums:
        await a.insert()
    logger.info("Gallery albums seeded (%d)", len(albums))


async def seed_faqs() -> None:
    from app.models.misc import FAQ
    if await FAQ.count() > 0:
        logger.info("FAQs already seeded")
        return
    faqs = [
        ("general", "Which regions do you work in?", "Mnafanya kazi mikoa gani?",
         "We work across all of Tanzania Mainland; our offices are in Dar es Salaam and Dodoma.",
         "Tunafanya kazi Tanzania Bara yote; ofisi zetu ziko Dar es Salaam na Dodoma.", 1),
        ("general", "Is the site survey free?", "Ukaguzi wa eneo una gharama?",
         "The initial survey within Dar es Salaam and Dodoma is free.",
         "Ukaguzi wa awali ndani ya Dar es Salaam na Dodoma ni bure.", 2),
        ("general", "How long does a quotation take?", "Inachukua muda gani kupata bei (quotation)?",
         "2 to 5 days after the site survey.",
         "Siku 2 hadi 5 baada ya ukaguzi wa eneo.", 3),
        ("general", "Do you offer a work guarantee?", "Mnatoa dhamana ya kazi?",
         "Yes, all our work carries a 12-month guarantee.",
         "Ndiyo, kazi zetu zina dhamana ya miezi 12.", 4),
        ("general", "Do you take small jobs like single-house wiring?", "Mnafanya kazi ndogo kama wiring wa nyumba moja?",
         "Yes, we serve both small and large projects.",
         "Ndiyo, tunahudumia kazi ndogo na kubwa.", 5),
        ("training", "Where is the training centre?", "Mafunzo yanatolewa wapi?",
         "At our training centre in Dar es Salaam, with practical sessions on real project sites.",
         "Kwenye kituo chetu cha mafunzo Dar es Salaam, pamoja na mazoezi kwenye miradi halisi.", 1),
    ]
    for cat, q_en, q_sw, a_en, a_sw, sort in faqs:
        await FAQ(
            category=cat,
            question=_t(q_en, q_sw),
            answer=_t(a_en, a_sw),
            sort=sort,
            is_active=True,
        ).insert()
    logger.info("FAQs seeded (%d)", len(faqs))


async def seed_offices() -> None:
    from app.models.misc import Office
    if await Office.count() > 0:
        logger.info("Offices already seeded")
        return
    offices = [
        Office(
            name=_t("Head Office – Dar es Salaam", "Makao Makuu – Dar es Salaam"),
            address=_t(
                "Mikocheni B, Old Bagamoyo Road, Dar es Salaam",
                "Mikocheni B, Barabara ya Old Bagamoyo, Dar es Salaam",
            ),
            phone="+255 700 000 001",
            email="info@kileleengineering.co.tz",
            hours=_t("Mon–Fri 8:00am–5:00pm; Sat 8:00am–1:00pm", "Jumatatu–Ijumaa 8:00–17:00; Jumamosi 8:00–13:00"),
            lat=-6.7924,
            lng=39.2083,
            is_head_office=True,
            sort=1,
        ),
        Office(
            name=_t("Branch – Dodoma", "Tawi – Dodoma"),
            address=_t(
                "Area D, Dodoma",
                "Area D, Dodoma",
            ),
            phone="+255 700 000 002",
            email="dodoma@kileleengineering.co.tz",
            hours=_t("Mon–Fri 8:00am–5:00pm", "Jumatatu–Ijumaa 8:00–17:00"),
            lat=-6.1722,
            lng=35.7395,
            is_head_office=False,
            sort=2,
        ),
    ]
    for o in offices:
        await o.insert()
    logger.info("Offices seeded (%d)", len(offices))


# ---------------------------------------------------------------------------
# Reset helper
# ---------------------------------------------------------------------------

async def reset_content() -> None:
    from app.models.content import HeroSlide, Stat, Feature, WorkStep
    from app.models.pages import Page
    from app.models.team import TeamMember, Certification
    from app.models.services import ServiceCategory, Service
    from app.models.projects import Project
    from app.models.training import TrainingProgramme, TrainingIntake, TrainingStep
    from app.models.clients import Client, Testimonial
    from app.models.posts import Post
    from app.models.gallery import GalleryAlbum
    from app.models.misc import FAQ, Office, Download, SiteSettings
    from app.models.inbox import ServiceRequest, TrainingApplication, ContactMessage

    for model in [HeroSlide, Stat, Feature, WorkStep, Page, TeamMember, Certification,
                  ServiceCategory, Service, Project, TrainingProgramme, TrainingIntake,
                  TrainingStep, Client, Testimonial, Post, GalleryAlbum, FAQ, Office,
                  Download, SiteSettings]:
        await model.delete_all()
    logger.info("Content collections cleared (users preserved)")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def main(reset: bool = False) -> None:
    from app.db import init_db
    await init_db()

    if reset:
        await reset_content()

    await seed_settings()
    await seed_hero_slides()
    await seed_stats()
    await seed_features()
    await seed_work_steps()
    await seed_pages()
    await seed_service_categories()
    await seed_services()
    await seed_projects()
    await seed_training()
    await seed_team()
    await seed_clients()
    await seed_posts()
    await seed_gallery()
    await seed_faqs()
    await seed_offices()

    logger.info("Seeding complete!")


if __name__ == "__main__":
    reset_flag = "--reset" in sys.argv
    asyncio.run(main(reset=reset_flag))
