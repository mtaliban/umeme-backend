"""One-time script to update About page with rich content."""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import os, sys

sys.path.insert(0, "/app")

MONGO_URL = "mongodb://mongoadmin:devpassword123@mongo:27017/company_website?authSource=admin"

BODY_EN = """<p>Founded in 2009, Volt &amp; Water Engineering Ltd has grown from a small electrical contractor into one of Tanzania's most respected multi-disciplinary engineering firms. With headquarters in Dar es Salaam and project offices across the country, we serve government agencies, development organisations, and private-sector clients who demand quality, reliability, and value.</p>

<p>Over the past 15 years we have designed, installed, and commissioned more than <strong>400 projects</strong> spanning rural electrification, solar energy, water supply, borehole drilling, and industrial installations. Our reach extends from the bustling commercial districts of Dar es Salaam and Arusha to remote communities in Mtwara, Kigoma, and the Southern Highlands.</p>

<p>We hold full registration with the Engineers Registration Board of Tanzania (ERB), certification under ISO 9001:2015 for quality management, and accreditation with EWURA, TANESCO, and REA. This regulatory standing enables us to pursue a wide range of public and private contracts with confidence.</p>

<p>Our in-house team of over <strong>120 engineers, technicians, and support staff</strong> is our greatest asset. We invest heavily in continuous professional development, ensuring every project benefits from the latest technical know-how and best practices. Safety, environmental stewardship, and community engagement are embedded into every phase of our work.</p>"""

BODY_SW = """<p>Ilianzishwa mwaka 2009, Volt &amp; Water Engineering Ltd imekua kutoka kwa mkandarasi mdogo wa umeme hadi kuwa moja ya makampuni ya uhandisi yenye heshima zaidi Tanzania. Makao makuu yetu yako Dar es Salaam na tuna ofisi za mradi katika maeneo mbalimbali ya nchi, tukihudumia serikali, mashirika ya maendeleo, na wateja wa sekta binafsi wanaohitaji ubora, uaminifu, na thamani.</p>

<p>Katika miaka 15 iliyopita tumebuni, kufunga, na kuzindua zaidi ya <strong>miradi 400</strong> inayohusisha umeme vijijini, nguvu ya jua, usambazaji wa maji, uchimbaji wa visima, na ufungaji wa viwanda. Huduma zetu zinaenea kutoka maeneo ya biashara ya Dar es Salaam na Arusha hadi jamii za mbali Mtwara, Kigoma, na Nyanda za Juu Kusini.</p>

<p>Tuna usajili kamili na Bodi ya Usajili wa Wahandisi Tanzania (ERB), uthibitisho wa ISO 9001:2015 kwa usimamizi wa ubora, na idhini kutoka EWURA, TANESCO, na REA. Hali hii ya kisheria inatuwezesha kushiriki katika aina mbalimbali za zabuni za umma na binafsi kwa ujasiri.</p>

<p>Timu yetu ya ndani ya zaidi ya <strong>wahandisi, mafundi, na wafanyakazi wa msaada 120</strong> ndiyo rasilimali yetu kubwa zaidi. Tunawekeza sana katika maendeleo ya kitaalamu yanayoendelea, kuhakikisha kila mradi unafaidika na ujuzi wa hivi karibuni na mbinu bora. Usalama, utunzaji wa mazingira, na ushirikiano wa jamii vimeingizwa katika kila hatua ya kazi yetu.</p>"""

VALUES = [
    {"title": {"en": "Integrity", "sw": "Uadilifu"},
     "text": {"en": "We hold ourselves to the highest ethical standards — transparent in our dealings, honest in our reporting, and accountable for every outcome.", "sw": "Tunazingatia viwango vya juu zaidi vya kimaadili — uwazi katika miamala yetu, uaminifu katika ripoti zetu, na uwajibikaji kwa kila matokeo."}, "icon": "shield"},
    {"title": {"en": "Excellence", "sw": "Ubora"},
     "text": {"en": "We pursue technical perfection on every project, applying rigorous quality-control processes from design through commissioning to handover.", "sw": "Tunafuata ukamilifu wa kiufundi katika kila mradi, tukitumia michakato madhubuti ya udhibiti wa ubora kutoka muundo hadi uzinduzi hadi ukabidhiaji."}, "icon": "star"},
    {"title": {"en": "Innovation", "sw": "Ubunifu"},
     "text": {"en": "We continuously adopt emerging technologies — from smart metering and solar-storage hybrids to IoT-enabled water monitoring — to deliver future-proof solutions.", "sw": "Tunaendelea kupitisha teknolojia mpya — kutoka kupima kwa akili na mseto wa jua na hifadhi hadi ufuatiliaji wa maji kwa IoT — kutoa suluhisho zinazodumu."}, "icon": "lightbulb"},
    {"title": {"en": "Community", "sw": "Jamii"},
     "text": {"en": "Every project we deliver improves lives. We prioritise local employment, skills transfer, and social investment in the communities where we operate.", "sw": "Kila mradi tunaowasilisha unaboresha maisha. Tunaitanguliza ajira ya wenyeji, uhamishaji wa ujuzi, na uwekezaji wa kijamii katika jamii tunapoendeshea kazi."}, "icon": "users"},
]

HSE_EN = ("At Volt & Water Engineering Ltd, Health, Safety and Environment (HSE) is not a "
          "compliance checkbox — it is a core value. We operate under a certified HSE Management "
          "System aligned with ISO 45001 and OSHA regulations. Zero Lost-Time Incidents is our "
          "standing target, and our teams receive rigorous safety induction, PPE, and regular "
          "toolbox-talk training on every site.")

HSE_SW = ("Katika Volt & Water Engineering Ltd, Afya, Usalama na Mazingira (HSE) si tu kukagua "
          "uzingatiaji — ni thamani ya msingi. Tunafanya kazi chini ya Mfumo wa Usimamizi wa HSE "
          "ulioidhinishwa sambamba na ISO 45001 na kanuni za OSHA. Kutokuwa na Ajali za Muda "
          "Kupotea ni lengo letu la kudumu, na timu zetu zinapata mafunzo makali ya usalama, "
          "vifaa vya kujikinga, na mafunzo ya mazungumzo ya zana kwenye kila tovuti.")


async def main():
    from app.models.pages import Page
    from app.models.team import TeamMember, Certification
    from app.models.content import Stat
    from beanie import init_beanie

    client = AsyncIOMotorClient(MONGO_URL)
    db = client.get_default_database()

    all_models = [Page, TeamMember, Certification, Stat]
    await init_beanie(database=db, document_models=all_models)

    # --- Update About page ---
    about = await Page.find_one(Page.key == "about")
    if about:
        about.intro = {"en": "Founded in 2009, Volt & Water Engineering Ltd has grown into Tanzania's trusted partner for electrical and water engineering — delivering over 400 projects across the country and empowering communities from Dar es Salaam to the most remote regions.",
                       "sw": "Ilianzishwa mwaka 2009, Volt & Water Engineering Ltd imekua kuwa mshirika wa kuaminiwa wa Tanzania kwa uhandisi wa umeme na maji — ikiwasilisha miradi zaidi ya 400 nchini kote na kuwezesha jamii kutoka Dar es Salaam hadi maeneo ya mbali zaidi."}
        about.body = {"en": BODY_EN, "sw": BODY_SW}
        about.vision = {"en": "To be East Africa's leading integrated engineering company, known for technical excellence, sustainable impact, and unwavering commitment to our clients and communities.",
                        "sw": "Kuwa kampuni inayoongoza ya uhandisi jumuishi Afrika Mashariki, inayojulikana kwa ubora wa kiufundi, athari endelevu, na kujitolea bila kuyumba kwa wateja na jamii zetu."}
        about.mission = {"en": "To design, build, and maintain world-class electrical and water infrastructure that improves livelihoods, drives economic growth, and safeguards Tanzania's natural resources for future generations.",
                         "sw": "Kubuni, kujenga, na kudumisha miundombinu ya daraja la dunia ya umeme na maji inayoboresha maisha, kukuza ukuaji wa uchumi, na kulinda rasilimali asili za Tanzania kwa vizazi vijavyo."}
        about.values = VALUES
        about.hse_statement = {"en": HSE_EN, "sw": HSE_SW}
        await about.save()
        print("✅ About page updated with rich content")
    else:
        print("❌ About page not found — run seed first")

    # --- Update Stats to be richer ---
    stats = await Stat.find_all().to_list()
    rich_stats = [
        {"label_en": "Projects Completed", "label_sw": "Miradi Iliyokamilika", "number": 400, "suffix": "+"},
        {"label_en": "Years of Experience", "label_sw": "Miaka ya Uzoefu", "number": 15, "suffix": "+"},
        {"label_en": "Engineers & Technicians", "label_sw": "Wahandisi & Mafundi", "number": 120, "suffix": "+"},
        {"label_en": "Regions Served", "label_sw": "Mikoa Inayohudumiwa", "number": 26, "suffix": ""},
    ]
    for stat, rich in zip(stats, rich_stats):
        stat.label = {"en": rich["label_en"], "sw": rich["label_sw"]}
        stat.number = rich["number"]
        stat.suffix = rich["suffix"]
        await stat.save()
    print(f"✅ Updated {len(stats)} stats")

    # --- Update Team members with richer bios ---
    team = await TeamMember.find_all().to_list()
    rich_team = [
        {"name": "Eng. James Mwangi", "pos_en": "Managing Director & CEO", "pos_sw": "Mkurugenzi Mtendaji & CEO",
         "bio_en": "James founded Volt & Water in 2009 with a vision to transform engineering service delivery in Tanzania. A registered electrical engineer with an MSc from UDSM, he has led the company from a 3-person startup to a 120+ strong team delivering landmark infrastructure projects across East Africa.",
         "bio_sw": "James alianzisha Volt & Water mwaka 2009 na maono ya kubadilisha utoaji wa huduma za uhandisi Tanzania. Mhandisi wa umeme aliyesajiliwa na MSc kutoka UDSM, ameongoza kampuni kutoka timu ya watu 3 hadi timu ya watu 120+ inayotekeleza miradi mikubwa ya miundombinu Afrika Mashariki."},
        {"name": "Eng. Fatuma Rashid", "pos_en": "Head of Water Engineering", "pos_sw": "Mkuu wa Uhandisi wa Maji",
         "bio_en": "Fatuma brings 14 years of expertise in water supply, borehole drilling, and sanitation systems. She has overseen the design and delivery of over 80 water infrastructure projects, including REA-funded rural water schemes benefiting more than 200,000 people.",
         "bio_sw": "Fatuma analeta uzoefu wa miaka 14 katika usambazaji wa maji, uchimbaji wa visima, na mifumo ya usafi. Amesimamia muundo na uwasilishaji wa miradi zaidi ya 80 ya miundombinu ya maji, ikiwemo mipango ya maji vijijini inayofadhiliwa na REA inayonufaisha zaidi ya watu 200,000."},
        {"name": "Eng. Peter Kimaro", "pos_en": "Head of Electrical Projects", "pos_sw": "Mkuu wa Miradi ya Umeme",
         "bio_en": "Peter specialises in high-voltage grid connections, solar-storage systems, and industrial electrical installations. With an MEng from NIT Arusha, he has supervised TANESCO grid extensions covering over 350 villages across Tanzania.",
         "bio_sw": "Peter ni mtaalamu katika uunganishaji wa gridi ya voltage ya juu, mifumo ya jua na hifadhi, na ufungaji wa umeme wa viwanda. Na MEng kutoka NIT Arusha, amesimamia upanuzi wa gridi ya TANESCO unaofunika vijiji zaidi ya 350 Tanzania."},
        {"name": "Grace Minja", "pos_en": "Finance & Administration Director", "pos_sw": "Mkurugenzi wa Fedha & Utawala",
         "bio_en": "Grace oversees all financial planning, compliance, and corporate governance for Volt & Water. A CPA (T) and holder of an MBA from the University of Dar es Salaam, she ensures the company maintains the financial discipline needed to deliver large infrastructure contracts on time and on budget.",
         "bio_sw": "Grace anasimamia mipango yote ya fedha, uzingatiaji, na utawala wa kampuni kwa Volt & Water. CPA (T) na mwenye MBA kutoka Chuo Kikuu cha Dar es Salaam, anahakikisha kampuni inadumisha nidhamu ya fedha inayohitajika kutoa mikataba mikubwa ya miundombinu kwa wakati na bajeti."},
    ]
    for member in team:
        for rich in rich_team:
            if rich["name"] in member.name:
                member.position = {"en": rich["pos_en"], "sw": rich["pos_sw"]}
                member.bio = {"en": rich["bio_en"], "sw": rich["bio_sw"]}
                await member.save()
                print(f"  ✅ Updated team member: {member.name}")
                break

    client.close()
    print("\nDone.")

asyncio.run(main())
