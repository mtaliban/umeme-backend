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
        company_name="Volt & Water Engineering Ltd",
        slogan=_t("Powering Lives, Sustaining Water", "Kuendesha Maisha, Kudumisha Maji"),
        logo={"url": logo_url, "alt": _t("Volt & Water Engineering"), "width": 400, "height": 120,
              "sizes": {"sm": logo_url, "md": logo_url, "lg": logo_url}},
        logo_dark={"url": logo_url, "alt": _t("Volt & Water Engineering"), "width": 400, "height": 120,
                   "sizes": {"sm": logo_url, "md": logo_url, "lg": logo_url}},
        favicon={"url": logo_url, "alt": _t("Favicon"), "width": 32, "height": 32,
                 "sizes": {"sm": logo_url, "md": logo_url, "lg": logo_url}},
        phones=["+255 222 123 456", "+255 754 123 456"],
        emails=["info@voltwater.co.tz", "support@voltwater.co.tz"],
        whatsapp_number="+255754123456",
        working_hours=_t("Mon–Fri 08:00–17:00", "Jumatatu–Ijumaa 08:00–17:00"),
        address=_t("Plot 45, Kinondoni Road, Dar es Salaam", "Kiwanja Na. 45, Barabara ya Kinondoni, Dar es Salaam"),
        social={
            "facebook": "https://facebook.com/voltwater",
            "instagram": "https://instagram.com/voltwater",
            "x": "",
            "linkedin": "https://linkedin.com/company/voltwater",
            "youtube": "",
            "tiktok": "",
        },
        footer_text=_t(
            "Volt & Water Engineering Ltd is a leading provider of electrical and water engineering services across Tanzania.",
            "Volt & Water Engineering Ltd ni kampuni inayoongoza katika kutoa huduma za uhandisi wa umeme na maji kote Tanzania.",
        ),
        default_seo=_seo(
            "Volt & Water Engineering Ltd – Tanzania",
            "Leading electrical and water engineering company in Tanzania.",
        ),
        notify_emails=["info@voltwater.co.tz"],
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
            image=_img("water", "Water Engineering", "Uhandisi wa Maji", 1600, 900),
            headline=_t("Clean Water for Every Community", "Maji Safi kwa Kila Jamii"),
            text=_t(
                "Designing and building water supply and sanitation systems that last for generations.",
                "Kubuni na kujenga mifumo ya maji na usafi inayodumu kwa vizazi.",
            ),
            button1_label=_t("View Projects", "Angalia Miradi"),
            button1_url="/projects",
            button2_label=_t("Request a Service", "Omba Huduma"),
            button2_url="/request-service",
            sort=1, is_active=True,
        ),
        HeroSlide(
            image=_img("electricity", "Electrical Engineering", "Uhandisi wa Umeme", 1600, 900),
            headline=_t("Reliable Electrical Engineering Solutions", "Suluhisho la Kuaminika la Uhandisi wa Umeme"),
            text=_t(
                "From grid connections to industrial installations — serving all 26 regions of Tanzania.",
                "Kutoka muunganiko wa gridi hadi ufungaji wa viwanda — tunahudumia mikoa yote 26 ya Tanzania.",
            ),
            button1_label=_t("Our Services", "Huduma Zetu"),
            button1_url="/services",
            button2_label=_t("Contact Us", "Wasiliana Nasi"),
            button2_url="/contact",
            sort=2, is_active=True,
        ),
        HeroSlide(
            image=_img("solar", "Solar Power", "Nishati ya Jua", 1600, 900),
            headline=_t("Powering Tanzania with Solar Energy", "Kulisha Tanzania kwa Nishati ya Jua"),
            text=_t(
                "Grid-tied and off-grid solar installations for homes, businesses and public facilities.",
                "Ufungaji wa jua uliounganishwa na gridi na uliojitegemea kwa nyumba, biashara na huduma za umma.",
            ),
            button1_label=_t("Solar Services", "Huduma za Jua"),
            button1_url="/services",
            button2_label=_t("Get a Quote", "Pata Bei"),
            button2_url="/request-service",
            sort=3, is_active=True,
        ),
        HeroSlide(
            image=_img("training", "Engineering Training", "Mafunzo ya Uhandisi", 1600, 900),
            headline=_t("Building Engineering Capacity", "Kujenga Uwezo wa Uhandisi"),
            text=_t(
                "Professional training programmes for the next generation of Tanzanian engineers.",
                "Mipango ya mafunzo ya kitaalamu kwa kizazi kipya cha wahandisi wa Tanzania.",
            ),
            button1_label=_t("Our Training", "Mafunzo Yetu"),
            button1_url="/training",
            button2_label=_t("Apply Now", "Omba Sasa"),
            button2_url="/training",
            sort=4, is_active=True,
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
        Stat(label=_t("Projects Completed", "Miradi Iliyokamilika"), number=400, suffix="+", icon="briefcase", sort=1),
        Stat(label=_t("Years of Experience", "Miaka ya Uzoefu"), number=15, suffix="+", icon="clock", sort=2),
        Stat(label=_t("Satisfied Clients", "Wateja Walioridhika"), number=200, suffix="+", icon="users", sort=3),
        Stat(label=_t("Regions Served", "Mikoa Inayohudumiwa"), number=26, suffix="", icon="map-pin", sort=4),
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
            title=_t("ERB Certified Engineers", "Wahandisi Wenye Cheti cha ERB"),
            text=_t(
                "All our engineers are registered with the Engineers Registration Board (ERB) and hold international qualifications.",
                "Wahandisi wetu wote wamesajiliwa na Bodi ya Usajili wa Wahandisi (ERB) na wana sifa za kimataifa.",
            ),
            icon="award", sort=1,
        ),
        Feature(
            title=_t("ISO 9001:2015 Certified", "Cheti cha ISO 9001:2015"),
            text=_t(
                "Our quality management system is ISO 9001:2015 certified, ensuring every project meets international standards.",
                "Mfumo wetu wa usimamizi wa ubora una cheti cha ISO 9001:2015, kuhakikisha kila mradi unakidhi viwango vya kimataifa.",
            ),
            icon="shield-check", sort=2,
        ),
        Feature(
            title=_t("On-Time Delivery", "Uwasilishaji kwa Wakati"),
            text=_t(
                "We have a track record of completing 95% of projects on schedule and within the agreed budget.",
                "Tuna rekodi ya kukamilisha 95% ya miradi kwa wakati na ndani ya bajeti iliyokubaliana.",
            ),
            icon="clock", sort=3,
        ),
        Feature(
            title=_t("Nationwide Coverage", "Huduma Kote Tanzania"),
            text=_t(
                "With offices in Dar es Salaam and Arusha, we operate across all 26 regions of mainland Tanzania.",
                "Tuna ofisi Dar es Salaam na Arusha, tunafanya kazi katika mikoa yote 26 ya Tanzania Bara.",
            ),
            icon="map-pin", sort=4,
        ),
        Feature(
            title=_t("Turnkey Solutions", "Suluhisho Kamili"),
            text=_t(
                "From survey and design through to construction, testing and handover — we handle the entire project lifecycle.",
                "Kutoka upembuzi na usanifu hadi ujenzi, majaribio na ukabidhi — tunashughulikia mzunguko wote wa mradi.",
            ),
            icon="layers", sort=5,
        ),
        Feature(
            title=_t("24/7 Support", "Msaada Saa 24/7"),
            text=_t(
                "Our emergency response team is available around the clock to handle critical electrical and water system faults.",
                "Timu yetu ya kukabiliana na dharura inapatikana saa nne na saa nne kushughulikia hitilafu muhimu za mifumo ya umeme na maji.",
            ),
            icon="headphones", sort=6,
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
            title=_t("Initial Consultation", "Ushauri wa Awali"),
            text=_t(
                "We meet with you to understand your project requirements, site conditions and budget constraints.",
                "Tunakutana nawe kuelewa mahitaji ya mradi wako, hali ya eneo na vikwazo vya bajeti.",
            ),
            icon="message-circle", sort=1,
        ),
        WorkStep(
            title=_t("Site Survey & Design", "Upembuzi wa Eneo na Usanifu"),
            text=_t(
                "Our engineers conduct a detailed site survey and produce comprehensive engineering designs and BOQs.",
                "Wahandisi wetu wanafanya upembuzi wa kina wa eneo na kutoa michoro ya kina ya uhandisi na BOQ.",
            ),
            icon="drafting-compass", sort=2,
        ),
        WorkStep(
            title=_t("Procurement", "Ununuzi wa Vifaa"),
            text=_t(
                "We source and procure all materials and equipment from approved suppliers to meet project specifications.",
                "Tunanunua vifaa na vifaa vyote kutoka kwa wasambazaji walioidhinishwa kulingana na maelezo ya mradi.",
            ),
            icon="shopping-cart", sort=3,
        ),
        WorkStep(
            title=_t("Construction & Installation", "Ujenzi na Ufungaji"),
            text=_t(
                "Our skilled teams execute the work safely, to spec and on the agreed schedule.",
                "Timu zetu stadi zinatekeleza kazi kwa usalama, kulingana na maelezo na ratiba iliyokubaliana.",
            ),
            icon="hard-hat", sort=4,
        ),
        WorkStep(
            title=_t("Testing & Commissioning", "Majaribio na Uzinduzi"),
            text=_t(
                "Every system is rigorously tested and commissioned before handover to ensure it performs as designed.",
                "Kila mfumo unajaribiwa kwa kina na kuzinduliwa kabla ya ukabidhi kuhakikisha inafanya kazi kama ilivyobuniwa.",
            ),
            icon="check-circle", sort=5,
        ),
        WorkStep(
            title=_t("Handover & After-Sales", "Ukabidhi na Huduma Baada ya Mauzo"),
            text=_t(
                "We hand over a fully tested system with all documentation and provide ongoing maintenance and support.",
                "Tunakabidhia mfumo uliojaribiwa kikamilifu na nyaraka zote na kutoa matengenezo na msaada unaoendelea.",
            ),
            icon="package", sort=6,
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
                "Volt & Water Engineering Ltd has been powering homes, businesses and communities across Tanzania since 2009.",
                "Volt & Water Engineering Ltd imekuwa ikiendesha nyumba, biashara na jamii kote Tanzania tangu 2009.",
            ),
            "body": _t(
                "<p>Founded in 2009, Volt & Water Engineering Ltd has grown to become one of Tanzania's most trusted electrical and water engineering firms. We combine deep technical expertise with a genuine commitment to quality, safety and timely delivery.</p>"
                "<p>Our team of over 80 engineers, technicians and support staff works across all 26 regions of Tanzania, delivering solutions that range from small residential installations to large-scale national infrastructure projects.</p>"
                "<p>We are registered with the Engineers Registration Board (ERB), accredited to ISO 9001:2015, and hold approvals from TANESCO, EWURA, REA and OSHA Tanzania.</p>",
                "<p>Ilianzishwa mwaka 2009, Volt & Water Engineering Ltd imekua kuwa moja ya makampuni ya uhandisi wa umeme na maji yanayoaminika zaidi Tanzania. Tunachanganya utaalamu wa kina wa kiufundi na dhamira ya kweli ya ubora, usalama na uwasilishaji kwa wakati.</p>"
                "<p>Timu yetu ya wahandisi, mafundi na wafanyakazi wa msaada zaidi ya 80 inafanya kazi katika mikoa yote 26 ya Tanzania, ikitoa suluhisho kuanzia ufungaji mdogo wa nyumba hadi miradi mikubwa ya miundombinu ya kitaifa.</p>",
            ),
            "banner": _img("construction", "About Us", "Kuhusu Sisi", 1600, 700),
            "seo": _seo("About Us | Volt & Water Engineering", "Learn about Volt & Water Engineering Ltd — Tanzania's trusted electrical and water engineering firm."),
            "vision": _t(
                "To be the most trusted and innovative engineering company in East and Central Africa.",
                "Kuwa kampuni ya uhandisi inayoaminika na yenye ubunifu zaidi Afrika Mashariki na Kati.",
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
                "Your privacy is important to us. This policy explains how Volt & Water Engineering Ltd collects, uses and protects your personal information.",
                "Faragha yako ni muhimu kwetu. Sera hii inaeleza jinsi Volt & Water Engineering Ltd inavyokusanya, kutumia na kulinda taarifa zako binafsi.",
            ),
            "body": _t(
                "<h2>Information We Collect</h2>"
                "<p>We collect personal information that you voluntarily provide through our contact forms, service request forms and training application forms. This includes your name, email address, phone number and the nature of your enquiry.</p>"
                "<h2>How We Use Your Information</h2>"
                "<p>We use the information you provide solely to respond to your enquiry, process your service request or training application, and to improve our services. We do not sell, trade or transfer your personal information to third parties.</p>"
                "<h2>Data Security</h2>"
                "<p>We implement appropriate technical and organisational measures to protect your personal information against unauthorised access, alteration, disclosure or destruction.</p>"
                "<h2>Contact Us</h2>"
                "<p>If you have any questions about this privacy policy, please contact us at <a href='mailto:info@voltwater.co.tz'>info@voltwater.co.tz</a>.</p>",
                "<h2>Taarifa Tunazokusanya</h2>"
                "<p>Tunakusanya taarifa binafsi unazotoa kwa hiari kupitia fomu zetu za mawasiliano, fomu za maombi ya huduma na fomu za maombi ya mafunzo.</p>"
                "<h2>Jinsi Tunavyotumia Taarifa Zako</h2>"
                "<p>Tunatumia taarifa unazotoa tu kujibu maswali yako, kushughulikia ombi lako la huduma au mafunzo, na kuboresha huduma zetu.</p>"
                "<h2>Usalama wa Data</h2>"
                "<p>Tunatekeleza hatua zinazofaa za kiufundi na za kiutaratibu kulinda taarifa zako binafsi dhidi ya ufikiaji usioidhinishwa.</p>",
            ),
            "banner": _img("office", "Privacy Policy", "Sera ya Faragha", 1600, 500),
            "seo": _seo("Privacy Policy | Volt & Water", "Privacy policy for Volt & Water Engineering Ltd."),
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
        ServiceCategory(name=_t("Electrical Engineering", "Uhandisi wa Umeme"),
                        slug="electrical", icon="zap", colour="#F59E0B", sort=1,
                        created_at=NOW, updated_at=NOW),
        ServiceCategory(name=_t("Water Engineering", "Uhandisi wa Maji"),
                        slug="water", icon="droplets", colour="#0EA5E9", sort=2,
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

    elec = await ServiceCategory.find_one({"slug": "electrical"})
    water = await ServiceCategory.find_one({"slug": "water"})
    elec_id = str(elec.id) if elec else ""
    water_id = str(water.id) if water else ""

    # (slug, title_en, title_sw, cat_id, is_featured, photo_category, body_en)
    services_data = [
        (
            "grid-connection", "Grid Connection Services", "Huduma za Muunganiko wa Gridi",
            elec_id, True, "electricity",
            "<p>We handle the full process of connecting homes, commercial premises and industrial facilities to the national grid. Our team coordinates with TANESCO at every stage to ensure a smooth, compliant and timely connection.</p>"
            "<ul><li>Low voltage (LV) residential and commercial connections</li><li>Medium voltage (MV) industrial connections</li><li>Load assessments and power quality studies</li><li>Metering installation and inspection</li></ul>",
        ),
        (
            "solar-installation", "Solar Power Installation", "Ufungaji wa Nishati ya Jua",
            elec_id, True, "solar",
            "<p>We design and install grid-tied, off-grid and hybrid solar photovoltaic systems for residential, commercial and institutional clients. All installations comply with REA guidelines and use tier-1 solar components.</p>"
            "<ul><li>Rooftop and ground-mounted PV systems</li><li>Battery storage systems</li><li>Solar water pumping</li><li>System monitoring and maintenance</li></ul>",
        ),
        (
            "industrial-wiring", "Industrial Wiring & Installations", "Uwezeshaji wa Viwanda",
            elec_id, False, "electricity",
            "<p>From small factories to large industrial plants, we design and install complete electrical wiring systems that are safe, efficient and built to last.</p>"
            "<ul><li>HV/MV/LV wiring and cable management</li><li>Motor control centres (MCC)</li><li>Distribution boards and switchgear</li><li>Earthing and lightning protection</li></ul>",
        ),
        (
            "transformer-installation", "Transformer Installation & Maintenance", "Ufungaji na Matengenezo ya Transfoma",
            elec_id, False, "electricity",
            "<p>We supply, install, test and maintain distribution transformers for TANESCO, municipalities, industries and large commercial facilities.</p>"
            "<ul><li>11kV/415V distribution transformers</li><li>Transformer testing and commissioning</li><li>Oil sampling and analysis</li><li>Preventive maintenance programmes</li></ul>",
        ),
        (
            "street-lighting", "Street & Area Lighting", "Taa za Barabarani na Maeneo",
            elec_id, False, "electricity",
            "<p>We design, supply and install street lighting systems for municipalities, roads, industrial estates and public spaces across Tanzania.</p>"
            "<ul><li>LED street light design and supply</li><li>Pole installation and cabling</li><li>Solar-powered street lighting</li><li>Smart lighting control systems</li></ul>",
        ),
        (
            "electrical-inspection", "Electrical Inspection & Testing", "Ukaguzi na Majaribio ya Umeme",
            elec_id, False, "electricity",
            "<p>Our accredited inspection team carries out thorough electrical testing and certification services for new installations, existing systems and insurance purposes.</p>"
            "<ul><li>Installation condition reports (EICR)</li><li>Insulation resistance testing</li><li>Earth fault loop impedance testing</li><li>Thermographic surveys</li></ul>",
        ),
        (
            "water-supply-design", "Water Supply System Design", "Usanifu wa Mfumo wa Maji",
            water_id, True, "water",
            "<p>We provide end-to-end water supply system design services — from hydrological studies and demand analysis through to detailed engineering drawings and construction supervision.</p>"
            "<ul><li>Water demand forecasting</li><li>Pipe network hydraulic modelling</li><li>Pumping station design</li><li>Reservoir and elevated tank design</li></ul>",
        ),
        (
            "borehole-drilling", "Borehole Drilling & Equipping", "Uchimbaji na Uwezeshaji wa Visima",
            water_id, True, "water",
            "<p>We drill, case, develop, test and equip boreholes for rural communities, urban areas, agriculture and industry across Tanzania.</p>"
            "<ul><li>Hydrogeological surveys</li><li>Rotary and DTH borehole drilling</li><li>Pump installation and testing</li><li>Water quality analysis</li></ul>",
        ),
        (
            "water-treatment", "Water Treatment Plants", "Vinu vya Kutibu Maji",
            water_id, False, "water",
            "<p>We design, construct and commission water treatment plants for municipal water utilities, industries and rural water supply schemes.</p>"
            "<ul><li>Conventional and compact treatment plants</li><li>Chemical dosing systems</li><li>Filtration and disinfection</li><li>Sludge management systems</li></ul>",
        ),
        (
            "irrigation-systems", "Irrigation Systems", "Mifumo ya Umwagiliaji",
            water_id, False, "water",
            "<p>We design and install drip, sprinkler and furrow irrigation systems for smallholder farmers, large-scale farms and irrigation schemes funded by government and development partners.</p>"
            "<ul><li>Irrigation scheme master planning</li><li>Pumping and conveyance systems</li><li>Drip and micro-irrigation</li><li>Farmer training and capacity building</li></ul>",
        ),
        (
            "sewerage-systems", "Sewerage & Sanitation Systems", "Mifumo ya Maji Taka na Usafi",
            water_id, False, "water",
            "<p>We design and construct sewerage networks, wastewater treatment plants and on-site sanitation facilities for municipalities, institutions and industries.</p>"
            "<ul><li>Gravity sewer network design</li><li>Wastewater treatment plants</li><li>Septic tanks and soak pits</li><li>Faecal sludge management</li></ul>",
        ),
        (
            "rainwater-harvesting", "Rainwater Harvesting Systems", "Mifumo ya Uvunaji wa Maji ya Mvua",
            water_id, False, "water",
            "<p>We design and install rainwater harvesting systems for schools, clinics, households and community centres — a sustainable solution for water-scarce areas.</p>"
            "<ul><li>Roof catchment assessment</li><li>Storage tank sizing and installation</li><li>First-flush diverters and filtration</li><li>Community maintenance training</li></ul>",
        ),
    ]

    for slug, title_en, title_sw, cat_id, is_featured, photo_cat, body_en in services_data:
        summary_en = f"Professional {title_en.lower()} services delivered across Tanzania by ERB-certified engineers."
        summary_sw = f"Huduma za kitaalamu za {title_sw.lower()} zinazotolewa kote Tanzania na wahandisi wenye cheti cha ERB."
        s = Service(
            status="published",
            slug=slug,
            slug_sw=slug,
            category_id=cat_id,
            title=_t(title_en, title_sw),
            icon="wrench",
            cover=_img(photo_cat, title_en, title_sw, 900, 600),
            summary=_t(summary_en, summary_sw),
            body=_t(body_en, f"<p>{summary_sw}</p>"),
            included=[
                _t("Site survey and assessment", "Upembuzi na tathmini ya eneo"),
                _t("Detailed engineering design", "Usanifu wa kina wa uhandisi"),
                _t("Material procurement and supply", "Ununuzi na usambazaji wa vifaa"),
                _t("Construction and installation", "Ujenzi na ufungaji"),
                _t("Testing and commissioning", "Majaribio na uzinduzi"),
                _t("As-built drawings and documentation", "Michoro na nyaraka za mwisho"),
            ],
            is_featured=is_featured,
            seo=_seo(f"{title_en} | Volt & Water Engineering", summary_en),
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

    elec = await ServiceCategory.find_one({"slug": "electrical"})
    water = await ServiceCategory.find_one({"slug": "water"})
    elec_id = str(elec.id) if elec else ""
    water_id = str(water.id) if water else ""

    # (slug, title_en, title_sw, cat_id, client, loc, region, start, end, value, is_featured, proj_status, photo_cat)
    projects = [
        (
            "dar-es-salaam-grid-upgrade",
            "Dar es Salaam Grid Upgrade Phase II",
            "Uboreshaji wa Gridi ya Dar es Salaam Awamu ya II",
            elec_id, "TANESCO", "Kinondoni & Ilala, Dar es Salaam", "Dar es Salaam",
            date(2022, 1, 15), date(2023, 6, 30), 850_000_000, True, "completed", "electricity",
            "Upgrading 42km of overhead MV lines from 11kV to 33kV across two districts to reduce system losses and improve reliability for 35,000 customers.",
        ),
        (
            "dodoma-rural-water-supply",
            "Dodoma Rural Water Supply Scheme",
            "Skimu ya Maji ya Vijijini Dodoma",
            water_id, "DAWASA / World Bank", "Chamwino & Kondoa Districts, Dodoma", "Dodoma",
            date(2021, 3, 1), date(2022, 9, 30), 1_200_000_000, True, "completed", "water",
            "Designing and constructing a piped water supply scheme serving 18 villages with a combined population of 42,000 people, including borehole drilling, pumping stations and 85km of distribution piping.",
        ),
        (
            "arusha-solar-farm",
            "Arusha 2MW Solar Farm",
            "Shamba la Jua la 2MW Arusha",
            elec_id, "REA Tanzania / AfDB", "Monduli District, Arusha", "Arusha",
            date(2023, 7, 1), None, 2_500_000_000, False, "ongoing", "solar",
            "EPC contract for a 2MW ground-mounted solar photovoltaic farm to supply clean electricity to rural communities in three wards currently off-grid.",
        ),
        (
            "mwanza-borehole-network",
            "Mwanza Peri-Urban Borehole Network",
            "Mtandao wa Visima vya Mwanza",
            water_id, "Mwanza City Council / UNICEF", "Ilemela District, Mwanza", "Mwanza",
            date(2022, 10, 1), date(2023, 12, 31), 450_000_000, False, "completed", "water",
            "Drilling and equipping 12 production boreholes with solar-powered pumps and constructing 3,200m of distribution pipework to serve 15,000 peri-urban residents.",
        ),
        (
            "mbeya-street-lighting",
            "Mbeya City Street Lighting Upgrade",
            "Uboreshaji wa Taa za Barabarani Mbeya",
            elec_id, "Mbeya City Council", "Mbeya City, Mbeya", "Mbeya",
            date(2023, 1, 10), date(2023, 8, 31), 320_000_000, False, "completed", "electricity",
            "Supply and installation of 1,200 LED street lights along 48km of urban roads, replacing old sodium vapour fittings and reducing the council's electricity consumption by 65%.",
        ),
        (
            "morogoro-irrigation-scheme",
            "Morogoro Lower Valley Irrigation Scheme",
            "Skimu ya Umwagiliaji ya Bonde la Chini Morogoro",
            water_id, "Ministry of Agriculture / IFAD", "Kilosa District, Morogoro", "Morogoro",
            date(2024, 2, 1), None, 980_000_000, False, "ongoing", "water",
            "Design and construction of a 450-hectare gravity-fed irrigation scheme serving 850 smallholder farming households with reliable water access year-round.",
        ),
        (
            "zanzibar-solar-street-lights",
            "Zanzibar Solar Street Lighting",
            "Taa za Barabarani za Jua Zanzibar",
            elec_id, "ZEC / JICA", "Stone Town & North A, Zanzibar", "Zanzibar",
            date(2023, 9, 1), date(2024, 3, 31), 580_000_000, False, "completed", "solar",
            "Supply and installation of 800 solar-powered street lights across 30km of roads in Zanzibar Stone Town and surrounding areas, improving public safety and reducing municipal energy costs.",
        ),
        (
            "tabora-water-treatment-plant",
            "Tabora Water Treatment Plant Rehabilitation",
            "Ukarabati wa Kinu cha Kutibu Maji Tabora",
            water_id, "DAWASCO / IsDB", "Tabora Municipality, Tabora", "Tabora",
            date(2022, 6, 1), date(2023, 5, 31), 760_000_000, False, "completed", "water",
            "Full rehabilitation of a 10,000m³/day water treatment plant including rapid sand filters, chemical dosing systems, disinfection and SCADA installation.",
        ),
    ]

    for idx, row in enumerate(projects):
        (slug, title_en, title_sw, cat_id, client, loc, region,
         start, end, value, is_featured, proj_status, photo_cat, scope_text) = row
        p = Project(
            status="published",
            slug=slug,
            slug_sw=slug,
            sort=idx + 1,
            category_id=cat_id,
            title=_t(title_en, title_sw),
            client_name=client,
            location=loc,
            region=region,
            start_date=start,
            end_date=end,
            value_tzs=value,
            hide_value=False,
            project_status=proj_status,
            summary=_t(scope_text, scope_text),
            scope=_t(f"<p>{scope_text}</p>", f"<p>{scope_text}</p>"),
            outcome=_t(
                "<p>Project completed successfully within the agreed timeline and budget. All systems tested, commissioned and handed over to the client with full documentation.</p>",
                "<p>Mradi ulikamilika kwa mafanikio ndani ya muda na bajeti iliyokubaliana. Mifumo yote ilijaribiwa, kuzinduliwa na kukabidhiwa kwa mteja na nyaraka kamili.</p>",
            ) if end else _t("<p>Project currently under construction and on schedule.</p>", "<p>Mradi uko katika ujenzi na uko kwenye ratiba.</p>"),
            cover=_img(photo_cat, title_en, title_sw, 900, 600),
            is_featured=is_featured,
            seo=_seo(f"{title_en} | Volt & Water Engineering", scope_text[:160]),
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
            slug="electrical-installation-wiring",
            slug_sw="ufungaji-na-uwezeshaji-wa-umeme",
            sort=1,
            title=_t("Electrical Installation & Wiring", "Ufungaji na Uwezeshaji wa Umeme"),
            cover=_img("electricity", "Electrical Installation Training", "Mafunzo ya Ufungaji wa Umeme", 900, 600),
            summary=_t(
                "A comprehensive, hands-on training programme covering electrical installation, wiring regulations, safety and testing. Ideal for technicians seeking ERB registration.",
                "Programu ya mafunzo ya kina na ya vitendo inayoshughulikia ufungaji wa umeme, kanuni za wiring, usalama na majaribio. Nzuri kwa mafundi wanaotafuta usajili wa ERB.",
            ),
            audience=_t(
                "Electrical technicians, artisans and engineers with at least 1 year of practical experience.",
                "Mafundi wa umeme, mafundi na wahandisi wenye angalau mwaka 1 wa uzoefu wa vitendo.",
            ),
            requirements=_t(
                "Form IV certificate or VETA Level II electrical qualification. Candidates must bring proof of practical experience.",
                "Cheti cha Kidato cha Nne au sifa ya VETA Level II ya umeme. Wagombea lazima walете uthibitisho wa uzoefu wa vitendo.",
            ),
            outline=_t(
                "<p><strong>Module 1 (3 days):</strong> Electrical theory, circuit analysis and wiring regulations<br>"
                "<strong>Module 2 (5 days):</strong> Installation practices — conduit, trunking and cable management<br>"
                "<strong>Module 3 (4 days):</strong> Distribution boards, switchgear and protection devices<br>"
                "<strong>Module 4 (3 days):</strong> Testing, inspection and commissioning<br>"
                "<strong>Module 5 (2 days):</strong> Electrical safety, HSE and emergency procedures<br>"
                "<strong>Module 6 (3 days):</strong> Practical project and assessment</p>",
                "<p><strong>Moduli 1 (Siku 3):</strong> Nadharia ya umeme, uchanganuzi wa mzunguko na kanuni za wiring<br>"
                "<strong>Moduli 2 (Siku 5):</strong> Mazoea ya ufungaji — conduit, trunking na usimamizi wa kebo<br>"
                "<strong>Moduli 3 (Siku 4):</strong> Ubao wa usambazaji, switchgear na vifaa vya ulinzi<br>"
                "<strong>Moduli 4 (Siku 3):</strong> Majaribio, ukaguzi na uzinduzi<br>"
                "<strong>Moduli 5 (Siku 2):</strong> Usalama wa umeme, HSE na taratibu za dharura<br>"
                "<strong>Moduli 6 (Siku 3):</strong> Mradi wa vitendo na tathmini</p>",
            ),
            duration=_t("4 weeks (20 training days)", "Wiki 4 (Siku 20 za mafunzo)"),
            mode="classroom",
            fee_tzs=350_000,
            certificate=_t(
                "Certificate in Electrical Installation & Wiring (recognised by ERB)",
                "Cheti cha Ufungaji na Uwezeshaji wa Umeme (kinatambuliwa na ERB)",
            ),
            venue=_t(
                "Volt & Water Engineering Training Centre, Kinondoni, Dar es Salaam",
                "Kituo cha Mafunzo cha Volt & Water Engineering, Kinondoni, Dar es Salaam",
            ),
            is_open=True,
            seo=_seo(
                "Electrical Installation & Wiring Training | Volt & Water",
                "Hands-on electrical installation and wiring training in Tanzania — recognised by ERB.",
            ),
            created_at=NOW, updated_at=NOW,
        ),
        TrainingProgramme(
            status="published",
            slug="water-system-design-management",
            slug_sw="usanifu-na-usimamizi-wa-mfumo-wa-maji",
            sort=2,
            title=_t("Water System Design & Management", "Usanifu na Usimamizi wa Mfumo wa Maji"),
            cover=_img("water", "Water System Training", "Mafunzo ya Mfumo wa Maji", 900, 600),
            summary=_t(
                "Learn to design, install, operate and maintain rural and urban water supply systems. Covers hydraulic modelling, borehole development and O&M best practices.",
                "Jifunza kubuni, kufunga, kuendesha na kudumisha mifumo ya maji ya vijijini na mijini. Inashughulikia mfano wa hydraulic, maendeleo ya visima na mazoea bora ya O&M.",
            ),
            audience=_t(
                "Civil engineers, water utility operators, NGO staff and government water department technicians.",
                "Wahandisi wa ujenzi, waendeshaji wa maji, wafanyakazi wa NGO na mafundi wa idara ya maji ya serikali.",
            ),
            requirements=_t(
                "Diploma in Civil Engineering, Water Engineering or equivalent. Basic computer skills required.",
                "Stashahada ya Uhandisi wa Ujenzi, Uhandisi wa Maji au sawa. Ujuzi wa msingi wa kompyuta unahitajika.",
            ),
            outline=_t(
                "<p><strong>Module 1 (3 days):</strong> Hydrology and water resources assessment<br>"
                "<strong>Module 2 (4 days):</strong> Water system design — pipes, pumps and storage<br>"
                "<strong>Module 3 (3 days):</strong> Borehole development and water quality<br>"
                "<strong>Module 4 (3 days):</strong> Operation and maintenance of water systems<br>"
                "<strong>Module 5 (2 days):</strong> Community engagement and tariff setting</p>",
                "<p><strong>Moduli 1 (Siku 3):</strong> Haidrolojia na tathmini ya rasilimali za maji<br>"
                "<strong>Moduli 2 (Siku 4):</strong> Usanifu wa mfumo wa maji — mabomba, pampu na uhifadhi<br>"
                "<strong>Moduli 3 (Siku 3):</strong> Maendeleo ya visima na ubora wa maji<br>"
                "<strong>Moduli 4 (Siku 3):</strong> Uendeshaji na matengenezo ya mifumo ya maji<br>"
                "<strong>Moduli 5 (Siku 2):</strong> Ushirikishwaji wa jamii na uwekaji wa ada</p>",
            ),
            duration=_t("3 weeks (15 training days)", "Wiki 3 (Siku 15 za mafunzo)"),
            mode="blended",
            fee_tzs=400_000,
            certificate=_t(
                "Certificate in Water System Design & Management (endorsed by EWURA)",
                "Cheti cha Usanifu na Usimamizi wa Mfumo wa Maji (kinaidhinishwa na EWURA)",
            ),
            venue=_t(
                "Volt & Water Engineering Training Centre, Kinondoni, Dar es Salaam",
                "Kituo cha Mafunzo cha Volt & Water Engineering, Kinondoni, Dar es Salaam",
            ),
            is_open=True,
            seo=_seo(
                "Water System Design & Management Training | Volt & Water",
                "Professional water system design and management training endorsed by EWURA.",
            ),
            created_at=NOW, updated_at=NOW,
        ),
        TrainingProgramme(
            status="published",
            slug="solar-pv-installation",
            slug_sw="ufungaji-wa-nishati-ya-jua",
            sort=3,
            title=_t("Solar PV Installation & Maintenance", "Ufungaji na Matengenezo ya Paneli za Jua"),
            cover=_img("solar", "Solar PV Training", "Mafunzo ya Paneli za Jua", 900, 600),
            summary=_t(
                "A practical training course on the design, installation, commissioning and maintenance of solar PV systems — grid-tied, off-grid and hybrid.",
                "Kozi ya mafunzo ya vitendo kuhusu usanifu, ufungaji, uzinduzi na matengenezo ya mifumo ya PV ya jua — iliyounganishwa na gridi, inayojitegemea na mseto.",
            ),
            audience=_t(
                "Electricians, electrical engineers and technicians wishing to specialise in solar energy.",
                "Mafundi wa umeme, wahandisi wa umeme na mafundi wanaotaka kutaalamu katika nishati ya jua.",
            ),
            requirements=_t(
                "Basic electrical knowledge equivalent to Form IV or VETA Level I.",
                "Maarifa ya msingi ya umeme sawa na Kidato cha Nne au VETA Level I.",
            ),
            outline=_t(
                "<p><strong>Module 1 (2 days):</strong> Solar energy fundamentals and system sizing<br>"
                "<strong>Module 2 (3 days):</strong> PV panel, inverter and battery installation<br>"
                "<strong>Module 3 (2 days):</strong> Grid-tied system installation and anti-islanding<br>"
                "<strong>Module 4 (2 days):</strong> System testing, commissioning and monitoring<br>"
                "<strong>Module 5 (1 day):</strong> Fault diagnosis and preventive maintenance</p>",
                "<p><strong>Moduli 1 (Siku 2):</strong> Misingi ya nishati ya jua na upangaji wa ukubwa wa mfumo<br>"
                "<strong>Moduli 2 (Siku 3):</strong> Ufungaji wa paneli za PV, inverter na betri<br>"
                "<strong>Moduli 3 (Siku 2):</strong> Ufungaji wa mfumo ulioratibishwa na gridi<br>"
                "<strong>Moduli 4 (Siku 2):</strong> Majaribio, uzinduzi na ufuatiliaji wa mfumo<br>"
                "<strong>Moduli 5 (Siku 1):</strong> Utambuzi wa hitilafu na matengenezo ya kuzuia</p>",
            ),
            duration=_t("2 weeks (10 training days)", "Wiki 2 (Siku 10 za mafunzo)"),
            mode="classroom",
            fee_tzs=300_000,
            certificate=_t(
                "Certificate in Solar PV Installation & Maintenance (REA approved)",
                "Cheti cha Ufungaji na Matengenezo ya Paneli za Jua (imeidhinishwa na REA)",
            ),
            venue=_t(
                "Volt & Water Engineering Training Centre, Kinondoni, Dar es Salaam",
                "Kituo cha Mafunzo cha Volt & Water Engineering, Kinondoni, Dar es Salaam",
            ),
            is_open=True,
            seo=_seo(
                "Solar PV Installation Training | Volt & Water",
                "Hands-on solar PV installation and maintenance training — REA approved.",
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
        TrainingStep(number=1, title=_t("Apply Online", "Omba Mtandaoni"),
                     text=_t("Complete the application form on our website with your personal details, qualifications and work experience.", "Jaza fomu ya maombi kwenye tovuti yetu na maelezo yako binafsi, sifa na uzoefu wa kazi."),
                     icon="file-text"),
        TrainingStep(number=2, title=_t("Application Review", "Mapitio ya Maombi"),
                     text=_t("Our admissions team reviews your application and notifies you of the outcome within 3 working days.", "Timu yetu ya uandikishaji inaangalia maombi yako na kukujulisha matokeo ndani ya siku 3 za kazi."),
                     icon="search"),
        TrainingStep(number=3, title=_t("Fee Payment", "Malipo ya Ada"),
                     text=_t("Upon acceptance, pay the registration fee via bank transfer or mobile money (M-Pesa / Tigo Pesa).", "Baada ya kukubaliwa, lipa ada ya usajili kupitia uhamisho wa benki au pesa za rununu (M-Pesa / Tigo Pesa)."),
                     icon="credit-card"),
        TrainingStep(number=4, title=_t("Attend Training", "Hudhuria Mafunzo"),
                     text=_t("Attend all scheduled classroom and practical sessions. Training materials are provided at no extra cost.", "Hudhuria vikao vyote vilivyopangwa vya darasani na vitendo. Vifaa vya mafunzo vinatolewa bila gharama ya ziada."),
                     icon="calendar"),
        TrainingStep(number=5, title=_t("Assessment", "Tathmini"),
                     text=_t("Complete written and practical assessments at the end of the programme. A minimum pass mark of 60% is required.", "Kamilisha tathmini za maandishi na vitendo mwishoni mwa programu. Alama ya chini ya kufaulu ya 60% inahitajika."),
                     icon="clipboard-check"),
        TrainingStep(number=6, title=_t("Graduation", "Kuhitimu"),
                     text=_t("Successful candidates receive their certificates at a graduation ceremony held at our training centre.", "Wagombea waliofaulu wanapokea vyeti vyao katika sherehe ya kuhitimu inayofanyika katika kituo chetu cha mafunzo."),
                     icon="graduation-cap"),
        TrainingStep(number=7, title=_t("Alumni Network", "Mtandao wa Wahitimu"),
                     text=_t("Join our growing alumni network and access career support, job alerts and continuing professional development resources.", "Jiunge na mtandao wetu unaokua wa wahitimu na upate msaada wa kazi, arifa za kazi na rasilimali za maendeleo ya kitaalamu inayoendelea."),
                     icon="users"),
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
        Certification(name=_t("ERB Registration", "Usajili wa ERB"),
                      issuer="Engineers Registration Board of Tanzania", number="ERB/2009/0045",
                      logo=_img("office", "ERB", "ERB", 300, 150), sort=1),
        Certification(name=_t("ISO 9001:2015", "ISO 9001:2015"),
                      issuer="Bureau Veritas Certification", number="BV-ISO-9001-TZ-2019",
                      logo=_img("office", "ISO 9001", "ISO 9001", 300, 150), sort=2),
        Certification(name=_t("TANESCO Approved Contractor", "Mkandarasi Aliyeidhinishwa TANESCO"),
                      issuer="Tanzania Electric Supply Company (TANESCO)", number="TANESCO/AC/2015/112",
                      logo=_img("electricity", "TANESCO", "TANESCO", 300, 150), sort=3),
        Certification(name=_t("EWURA Licensed Operator", "Opereta Mwenye Leseni ya EWURA"),
                      issuer="Energy and Water Utilities Regulatory Authority (EWURA)", number="EWURA/WO/2016/078",
                      logo=_img("water", "EWURA", "EWURA", 300, 150), sort=4),
        Certification(name=_t("OSHA Safety Certification", "Cheti cha Usalama cha OSHA"),
                      issuer="Occupational Safety and Health Authority (OSHA) Tanzania", number="OSHA-TZ/2020/1234",
                      logo=_img("construction", "OSHA", "OSHA", 300, 150), sort=5),
        Certification(name=_t("REA Approved Solar Installer", "Mfungaji wa Jua Aliyeidhinishwa REA"),
                      issuer="Rural Energy Agency (REA)", number="REA/SI/2018/045",
                      logo=_img("solar", "REA", "REA", 300, 150), sort=6),
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
            name="Eng. Ali Hassan",
            position=_t("Projects Manager, TANESCO", "Meneja wa Miradi, TANESCO"),
            organisation="TANESCO",
            photo=_img("people", "Ali Hassan", "Ali Hassan", 300, 300),
            quote=_t(
                "Volt & Water delivered our Dar es Salaam grid upgrade on time and within budget. Their engineers are professional and their project management is first class.",
                "Volt & Water waliwasilisha uboreshaji wetu wa gridi ya Dar es Salaam kwa wakati na ndani ya bajeti. Wahandisi wao ni wataalamu na usimamizi wao wa miradi ni wa daraja la kwanza.",
            ),
            rating=5, sort=1, is_active=True,
        ),
        Testimonial(
            name="Ms. Sarah Kimani",
            position=_t("Group CEO, Azam Group", "Mkurugenzi Mtendaji, Azam Group"),
            organisation="Azam Group",
            photo=_img("people", "Sarah Kimani", "Sarah Kimani", 300, 300),
            quote=_t(
                "The solar installation at our Mbeya factory has reduced our electricity bills by over 60%. The Volt & Water team was professional from start to finish.",
                "Ufungaji wa jua katika kiwanda chetu cha Mbeya umepunguza bili zetu za umeme kwa zaidi ya 60%. Timu ya Volt & Water ilikuwa kitaalamu tangu mwanzo hadi mwisho.",
            ),
            rating=5, sort=2, is_active=True,
        ),
        Testimonial(
            name="Mr. John Mlay",
            position=_t("Country Director, WaterAid Tanzania", "Mkurugenzi wa Nchi, WaterAid Tanzania"),
            organisation="WaterAid Tanzania",
            photo=_img("people", "John Mlay", "John Mlay", 300, 300),
            quote=_t(
                "The borehole network Volt & Water installed in Mwanza now provides clean water to over 15,000 people daily. We are very pleased with the quality of their work.",
                "Mtandao wa visima ambao Volt & Water uliofunga Mwanza sasa unatoa maji safi kwa zaidi ya watu 15,000 kila siku. Tunafurahi sana na ubora wa kazi yao.",
            ),
            rating=5, sort=3, is_active=True,
        ),
        Testimonial(
            name="Eng. David Rutabanzibwa",
            position=_t("Director of Infrastructure, Mbeya City Council", "Mkurugenzi wa Miundombinu, Halmashauri ya Jiji la Mbeya"),
            organisation="Mbeya City Council",
            photo=_img("people", "David Rutabanzibwa", "", 300, 300),
            quote=_t(
                "Our street lighting project was completed on schedule and the LED lights are performing exactly as specified. We would not hesitate to work with Volt & Water again.",
                "Mradi wetu wa taa za barabarani ulikamilika kwa wakati na taa za LED zinaonyesha utendaji kama ilivyoainishwa. Hatusiti kufanya kazi na Volt & Water tena.",
            ),
            rating=5, sort=4, is_active=True,
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
            "rea-rural-electrification-contract-2025",
            "Volt & Water Wins Major REA Rural Electrification Contract",
            "Volt & Water Inashinda Mkataba Mkubwa wa REA wa Usambazaji wa Umeme Vijijini",
            "news", True, "electricity",
            "We are proud to announce that Volt & Water Engineering has been awarded a TZS 4.2 billion contract by the Rural Energy Agency (REA) to extend the national grid to 32 villages in Mbeya and Iringa regions.",
            "Tunafurahi kutangaza kwamba Volt & Water Engineering imepewa mkataba wa TZS bilioni 4.2 na Wakala wa Nishati Vijijini (REA) ili kupanua gridi ya taifa hadi vijiji 32 katika mikoa ya Mbeya na Iringa.",
        ),
        (
            "solar-energy-expo-tanzania-2026",
            "Volt & Water at Solar Energy Expo Tanzania 2026",
            "Volt & Water Kwenye Maonyesho ya Nishati ya Jua Tanzania 2026",
            "event", True, "solar",
            "Join us at Solar Energy Expo Tanzania 2026, where we will be showcasing our latest solar PV installation capabilities and off-grid energy solutions. Visit us at Stand B-14.",
            "Jiunge nasi kwenye Maonyesho ya Nishati ya Jua Tanzania 2026, ambapo tutaonyesha uwezo wetu wa hivi karibuni wa ufungaji wa PV ya jua na suluhisho za nishati ya off-grid.",
        ),
        (
            "water-safety-training-programme-2026",
            "New Water Safety & Quality Training Programme Launched",
            "Programu Mpya ya Mafunzo ya Usalama na Ubora wa Maji Imezinduliwa",
            "announcement", False, "water",
            "We have launched a new short course on water safety and quality management, designed for water utility operators and municipal water department staff. Applications are now open.",
            "Tumezindua kozi mpya ya muda mfupi kuhusu usalama wa maji na usimamizi wa ubora, iliyoundwa kwa waendeshaji wa maji na wafanyakazi wa idara ya maji ya manispaa.",
        ),
        (
            "mwanza-borehole-project-completion",
            "Mwanza Borehole Network — Project Completion Report",
            "Mtandao wa Visima Mwanza — Ripoti ya Kukamilika kwa Mradi",
            "news", False, "water",
            "We are pleased to report the successful completion of the Mwanza peri-urban borehole network project. The 12 solar-powered boreholes now supply clean water to over 15,000 residents in Ilemela District.",
            "Tunafurahi kutoa taarifa ya kukamilika kwa mafanikio kwa mradi wa mtandao wa visima wa miji ya Mwanza. Visima 12 vinavyotumia nishati ya jua sasa vinatoa maji safi kwa wakazi zaidi ya 15,000 katika Wilaya ya Ilemela.",
        ),
        (
            "tender-electrical-dodoma-university",
            "Tender Notice: Electrical Works — Dodoma University Phase III",
            "Tangazo la Zabuni: Kazi za Umeme — Chuo Kikuu cha Dodoma Awamu ya III",
            "tender", False, "electricity",
            "Volt & Water Engineering invites qualified electrical contractors to submit tenders for the supply and installation of electrical systems for the Phase III expansion of a major university in Dodoma.",
            "Volt & Water Engineering inaalika makandarasi wa umeme waliohitimu kuwasilisha zabuni kwa usambazaji na ufungaji wa mifumo ya umeme kwa upanuzi wa Awamu ya III wa chuo kikuu kikubwa Dodoma.",
        ),
        (
            "iso-9001-2015-recertification",
            "Volt & Water Achieves ISO 9001:2015 Recertification",
            "Volt & Water Inapata Uthibitisho Upya wa ISO 9001:2015",
            "news", True, "construction",
            "We are delighted to announce that Volt & Water Engineering has successfully achieved recertification to ISO 9001:2015 by Bureau Veritas. This recertification confirms our ongoing commitment to quality management excellence.",
            "Tunafurahi kutangaza kwamba Volt & Water Engineering imefanikisha kupata uthibitisho upya wa ISO 9001:2015 na Bureau Veritas. Uthibitisho huu unathibitisha dhamira yetu inayoendelea ya ubora wa usimamizi.",
        ),
        (
            "arusha-solar-farm-groundbreaking",
            "Groundbreaking Ceremony — Arusha 2MW Solar Farm",
            "Sherehe ya Kuanzisha — Shamba la Jua la 2MW Arusha",
            "news", False, "solar",
            "We marked the official start of construction of the Arusha 2MW Solar Farm with a groundbreaking ceremony attended by the Regional Commissioner of Arusha and representatives of REA and AfDB.",
            "Tuliashiria mwanzo rasmi wa ujenzi wa Shamba la Jua la 2MW la Arusha kwa sherehe ya kuanzisha iliyohudhuria na Mkuu wa Mkoa wa Arusha na wawakilishi wa REA na AfDB.",
        ),
        (
            "dar-es-salaam-grid-upgrade-completion",
            "Dar es Salaam Grid Upgrade Phase II — Successfully Completed",
            "Uboreshaji wa Gridi ya Dar es Salaam Awamu ya II — Umekamilika kwa Mafanikio",
            "news", False, "electricity",
            "We are proud to announce the successful completion of the Dar es Salaam Grid Upgrade Phase II project for TANESCO. The 42km of upgraded MV lines will improve electricity reliability for 35,000 customers.",
            "Tunafurahi kutangaza kukamilika kwa mafanikio kwa mradi wa Uboreshaji wa Gridi ya Dar es Salaam Awamu ya II kwa TANESCO. Mistari ya 42km ya MV iliyoboreshwa itaboresha kuaminika kwa umeme kwa wateja 35,000.",
        ),
    ]
    for slug, title_en, title_sw, cat, is_featured, photo_cat, excerpt_en, excerpt_sw in posts:
        body_en = (
            f"<p>{excerpt_en}</p>"
            "<p>For more information about this project or to request a similar service, please <a href='/contact'>contact us</a> or submit a <a href='/request-service'>service request</a>.</p>"
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
            seo=_seo(f"{title_en} | Volt & Water Engineering", excerpt_en[:160]),
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
        ("general", "What areas of Tanzania do you serve?", "Mnafanya kazi katika maeneo gani ya Tanzania?",
         "We operate in all 26 regions of mainland Tanzania. We have permanent offices in Dar es Salaam and Arusha, and we mobilise site teams to any region.",
         "Tunafanya kazi katika mikoa yote 26 ya Tanzania Bara. Tuna ofisi za kudumu Dar es Salaam na Arusha, na tunahamisha timu za eneo kwenda mkoa wowote.", 1),
        ("general", "How do I request a quotation?", "Ninawezaje kuomba bei?",
         "You can submit a service request through our website, email us at info@voltwater.co.tz or call +255 222 123 456. We respond within 1 working day.",
         "Unaweza kuwasilisha ombi la huduma kupitia tovuti yetu, utumie barua pepe kwa info@voltwater.co.tz au piga simu +255 222 123 456. Tunajibu ndani ya siku 1 ya kazi.", 2),
        ("general", "Are your engineers registered with ERB?", "Je, wahandisi wenu wamesajiliwa na ERB?",
         "Yes. All our engineers are registered with the Engineers Registration Board (ERB) of Tanzania and are covered by professional indemnity insurance.",
         "Ndiyo. Wahandisi wetu wote wamesajiliwa na Bodi ya Usajili wa Wahandisi (ERB) ya Tanzania na wana bima ya uwajibikaji wa kitaalamu.", 3),
        ("general", "Do you offer warranties on your work?", "Je, mnatoa dhamana kwa kazi yenu?",
         "Yes. We provide a 12-month workmanship warranty on all installations and projects. Manufacturers' warranties on equipment are passed through to the client.",
         "Ndiyo. Tunatoa dhamana ya utengenezaji wa miezi 12 kwa ufungaji wote na miradi. Dhamana za watengenezaji kwa vifaa zinapitishwa kwa mteja.", 4),
        ("general", "Are you ISO certified?", "Je, mna cheti cha ISO?",
         "Yes. We are accredited to ISO 9001:2015 by Bureau Veritas, covering all our electrical and water engineering services.",
         "Ndiyo. Tuna ithibati ya ISO 9001:2015 na Bureau Veritas, inayoshughulikia huduma zetu zote za uhandisi wa umeme na maji.", 5),
        ("electricity", "Do you install solar power systems?", "Je, mnafunga mifumo ya nishati ya jua?",
         "Yes. We design and install grid-tied, off-grid and hybrid solar PV systems for residential, commercial and institutional clients. We use tier-1 panels and inverters.",
         "Ndiyo. Tunabuni na kufunga mifumo ya PV ya jua iliyounganishwa na gridi, inayojitegemea na mseto kwa wateja wa nyumba, biashara na taasisi. Tunatumia paneli na inverters za daraja la kwanza.", 1),
        ("electricity", "Can you upgrade an old electrical installation?", "Je, mnaweza kuboresha ufungaji wa zamani wa umeme?",
         "Yes. We carry out full electrical condition surveys and can design and implement upgrades to bring installations up to current wiring regulations.",
         "Ndiyo. Tunafanya upembuzi kamili wa hali ya umeme na tunaweza kubuni na kutekeleza uboreshaji ili kuleta ufungaji kwa kanuni za sasa za wiring.", 2),
        ("electricity", "Do you work with TANESCO on grid connections?", "Je, mnafanya kazi na TANESCO kwa muunganiko wa gridi?",
         "Yes. We are a TANESCO-approved contractor and handle the entire grid connection process — from application through to energisation.",
         "Ndiyo. Sisi ni mkandarasi aliyeidhinishwa na TANESCO na tunashughulikia mchakato wote wa muunganiko wa gridi — kutoka ombi hadi kupewa nguvu.", 3),
        ("electricity", "Do you install transformer substations?", "Je, mnafunga vituo vidogo vya transfoma?",
         "Yes. We supply, install, test and commission distribution transformers (11kV/415V and 33kV/415V) for TANESCO, municipalities and industrial clients.",
         "Ndiyo. Tunatoa, kufunga, kujaribu na kuzindua transfoma za usambazaji (11kV/415V na 33kV/415V) kwa TANESCO, manispaa na wateja wa viwanda.", 4),
        ("water", "Do you drill boreholes?", "Je, mnachimba visima?",
         "Yes. We drill, case, develop, test and equip boreholes using modern rotary and DTH drilling rigs. We also carry out hydrogeological surveys.",
         "Ndiyo. Tunachimba, kutubia, kukuza, kujaribu na kuweka vifaa kwenye visima kwa kutumia vifaa vya kisasa vya kuchimba vya rotary na DTH. Pia tunafanya upembuzi wa hydrogeolojia.", 1),
        ("water", "What water treatment services do you offer?", "Mnatoa huduma gani za kutibu maji?",
         "We design and construct water treatment plants for municipalities and industries, including sedimentation, filtration and chlorination systems.",
         "Tunabuni na kujenga vinu vya kutibu maji kwa manispaa na viwanda, ikiwa ni pamoja na mifumo ya utulivu, uchujaji na uklorineshaji.", 2),
        ("water", "Can you design a water supply system for a rural community?", "Je, mnaweza kubuni mfumo wa maji kwa jamii ya vijijini?",
         "Yes. We have extensive experience designing and constructing piped water supply schemes for rural communities, including borehole sources, pumping systems and distribution networks.",
         "Ndiyo. Tuna uzoefu mkubwa wa kubuni na kujenga skimu za maji za bomba kwa jamii za vijijini, ikiwa ni pamoja na visima, mifumo ya pampu na mitandao ya usambazaji.", 3),
        ("training", "Who can attend your training programmes?", "Nani anaweza kuhudhuria mipango yenu ya mafunzo?",
         "Our training is open to engineers, technicians, artisans and students. Each programme has its own entry requirements — please check the specific programme page.",
         "Mafunzo yetu yako wazi kwa wahandisi, mafundi, mafundi na wanafunzi. Kila programu ina mahitaji yake ya kuingia — tafadhali angalia ukurasa wa programu maalum.", 1),
        ("training", "Are your training certificates recognised?", "Je, vyeti vyenu vya mafunzo vinatambuliwa?",
         "Our certificates are recognised by the Engineers Registration Board (ERB), EWURA and other professional bodies in Tanzania. The Solar PV course is approved by REA.",
         "Vyeti vyetu vinatambuliwa na Bodi ya Usajili wa Wahandisi (ERB), EWURA na vyombo vingine vya kitaalamu Tanzania. Kozi ya Solar PV imeidhinishwa na REA.", 2),
        ("training", "Can training be delivered at our premises?", "Je, mafunzo yanaweza kutolewa kwenye majengo yetu?",
         "Yes. We offer on-site and in-company training for organisations wishing to train groups of 10 or more staff. Contact us for a customised training proposal.",
         "Ndiyo. Tunatoa mafunzo ya mahali pa kazi na ndani ya kampuni kwa mashirika yanayotaka kufundisha vikundi vya wafanyakazi 10 au zaidi. Wasiliana nasi kwa pendekezo la mafunzo la kibinafsi.", 3),
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
                "Plot 45, Kinondoni Road, Kinondoni District, Dar es Salaam",
                "Kiwanja Na. 45, Barabara ya Kinondoni, Wilaya ya Kinondoni, Dar es Salaam",
            ),
            phone="+255 222 123 456",
            email="dar@voltwater.co.tz",
            hours=_t("Mon–Fri 08:00–17:00 | Sat 08:00–13:00", "Jumatatu–Ijumaa 08:00–17:00 | Jumamosi 08:00–13:00"),
            lat=-6.7924,
            lng=39.2083,
            is_head_office=True,
            sort=1,
        ),
        Office(
            name=_t("Arusha Branch Office", "Ofisi ya Tawi la Arusha"),
            address=_t(
                "Plot 12, Sokoine Road, Arusha Central Business District, Arusha",
                "Kiwanja Na. 12, Barabara ya Sokoine, Kituo cha Biashara cha Arusha, Arusha",
            ),
            phone="+255 272 345 678",
            email="arusha@voltwater.co.tz",
            hours=_t("Mon–Fri 08:00–17:00", "Jumatatu–Ijumaa 08:00–17:00"),
            lat=-3.3869,
            lng=36.6830,
            is_head_office=False,
            sort=2,
        ),
        Office(
            name=_t("Mwanza Liaison Office", "Ofisi ya Ufuatiliaji Mwanza"),
            address=_t(
                "2nd Floor, Sukuma House, Kenyatta Road, Mwanza",
                "Ghorofa ya 2, Sukuma House, Barabara ya Kenyatta, Mwanza",
            ),
            phone="+255 282 456 789",
            email="mwanza@voltwater.co.tz",
            hours=_t("Mon–Fri 08:30–17:00", "Jumatatu–Ijumaa 08:30–17:00"),
            lat=-2.5164,
            lng=32.9175,
            is_head_office=False,
            sort=3,
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
