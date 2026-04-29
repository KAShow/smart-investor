"""Curated reference catalogs surfaced via /api/companies and /api/solutions.

Kept in Python (rather than JSON) so it loads with the module and avoids extra
file I/O on every request. If this list grows large or becomes editable from
the admin UI, migrate to a database table.
"""

BAHRAIN_COMPANIES = {
    "b2b_marketplace": [
        {"name": "Tradeling", "sector": "متعدد", "desc": "منصة B2B للتجارة الإلكترونية تربط الموردين بالشركات في المنطقة", "website": "tradeling.com"},
        {"name": "Sary", "sector": "تجارة جملة", "desc": "منصة لتجار الجملة والمتاجر الصغيرة", "website": "sary.com"},
    ],
    "logistics": [
        {"name": "Fetchr", "sector": "نقل ولوجستيات", "desc": "شركة لوجستيات تقنية متخصصة في الشحن والتوصيل", "website": "fetchr.us"},
        {"name": "Aramex Bahrain", "sector": "نقل ولوجستيات", "desc": "شركة شحن ولوجستيات عالمية لها فرع في البحرين", "website": "aramex.com"},
        {"name": "DHL Bahrain", "sector": "نقل ولوجستيات", "desc": "خدمات شحن سريع دولي", "website": "dhl.com"},
    ],
    "real_estate": [
        {"name": "Property Finder Bahrain", "sector": "عقارات", "desc": "منصة للبحث عن العقارات للبيع والإيجار", "website": "propertyfinder.bh"},
        {"name": "Eskan Bank", "sector": "عقارات وتمويل", "desc": "بنك متخصص في التمويل العقاري", "website": "eskanbank.com.bh"},
    ],
    "delivery": [
        {"name": "Talabat", "sector": "توصيل طعام", "desc": "منصة طلب وتوصيل الطعام", "website": "talabat.com"},
        {"name": "Carriage", "sector": "توصيل طعام", "desc": "خدمة توصيل الطعام", "website": "carriage.com"},
        {"name": "HungerStation", "sector": "توصيل طعام", "desc": "منصة طلب وتوصيل الطعام", "website": "hungerstation.com"},
    ],
    "insurance": [
        {"name": "Bahrain Insurance", "sector": "تأمين", "desc": "شركة تأمين بحرينية", "website": "bahraininsurance.com"},
        {"name": "Takaful International", "sector": "تأمين تكافلي", "desc": "شركة تأمين تكافلي", "website": "takaful.com.bh"},
    ],
    "recruitment": [
        {"name": "Bayt", "sector": "توظيف", "desc": "منصة توظيف إقليمية", "website": "bayt.com"},
        {"name": "Naukrigulf", "sector": "توظيف", "desc": "منصة توظيف للخليج", "website": "naukrigulf.com"},
    ],
    "automotive": [
        {"name": "OpenSooq", "sector": "سيارات", "desc": "منصة لبيع وشراء السيارات", "website": "opensooq.com"},
        {"name": "YallaMotor", "sector": "سيارات", "desc": "منصة للسيارات الجديدة والمستعملة", "website": "yallamotor.com"},
    ],
    "business_services": [
        {"name": "Tamkeen", "sector": "دعم الأعمال", "desc": "صندوق دعم وتطوير المشاريع", "website": "tamkeen.bh"},
        {"name": "Bahrain BIC", "sector": "حاضنات أعمال", "desc": "مركز البحرين للمشاريع الناشئة", "website": "bic.com.bh"},
    ],
    "education": [
        {"name": "Naseej", "sector": "تعليم", "desc": "منصة للتعليم والتدريب", "website": "naseej.com"},
    ],
    "health": [
        {"name": "DoctorUna", "sector": "صحة", "desc": "منصة لحجز المواعيد الطبية", "website": "doctoruna.com"},
        {"name": "HealthFactory", "sector": "صحة", "desc": "منصة للخدمات الصحية", "website": "healthfactory.com"},
    ],
    "travel": [
        {"name": "Cleartrip Bahrain", "sector": "سفر", "desc": "منصة لحجز الطيران والفنادق", "website": "cleartrip.com"},
        {"name": "Booking.com", "sector": "سفر", "desc": "منصة لحجز الفنادق عالمياً", "website": "booking.com"},
    ],
    "customs": [
        {"name": "Bahrain Customs", "sector": "تخليص جمركي", "desc": "الإدارة العامة للجمارك - البحرين", "website": "customs.gov.bh"},
    ],
    "auction": [
        {"name": "Mazad", "sector": "مزادات", "desc": "منصة المزادات الإلكترونية", "website": "mazad.qa"},
    ],
    "ecommerce": [
        {"name": "OpenSooq", "sector": "تجارة إلكترونية", "desc": "منصة للبيع والشراء", "website": "opensooq.com"},
        {"name": "Dubizzle Bahrain", "sector": "إعلانات", "desc": "منصة إعلانات مبوبة", "website": "dubizzle.com.bh"},
    ],
    "ai_services": [
        {"name": "STC Bahrain", "sector": "تقنية", "desc": "شركة اتصالات تقدم خدمات رقمية متطورة", "website": "stc.com.bh"},
        {"name": "Bahrain FinTech Bay", "sector": "تقنية مالية", "desc": "مركز للابتكار في التكنولوجيا المالية", "website": "bahrainfintechbay.com"},
    ],
}

UNIVERSAL_SOLUTIONS = [
    {
        "icon": "🤖",
        "title": "منصة الوساطة الذكية بالذكاء الاصطناعي",
        "description": "منصة رقمية تستخدم AI لمطابقة البائعين مع المشترين تلقائياً بناءً على احتياجاتهم وتاريخهم. تقلل الوقت وتزيد معدل نجاح الصفقات.",
        "features": ["مطابقة ذكية", "تقييم آلي للثقة", "تقارير تنبؤية"],
        "success_rate": "85%",
        "implementation": "2-3 أشهر",
        "cost": "متوسط",
    },
    {
        "icon": "📱",
        "title": "تطبيق الجوال للوساطة الفورية",
        "description": "تطبيق يربط العملاء بالوسطاء المعتمدين في الوقت الفعلي مع نظام تقييم وشفافية كامل في العمولات والإجراءات.",
        "features": ["إشعارات فورية", "تتبع المعاملات", "دفع إلكتروني"],
        "success_rate": "78%",
        "implementation": "1-2 شهر",
        "cost": "منخفض",
    },
    {
        "icon": "🌐",
        "title": "شبكة الوسطاء المتعاونين",
        "description": "شبكة تربط بين شركات الوساطة الصغيرة والمتوسطة لتبادل الفرص والعملاء، مما يزيد من تغطية السوق والكفاءة.",
        "features": ["تبادل العملاء", "عمولات مشتركة", "دعم فني موحد"],
        "success_rate": "72%",
        "implementation": "3-4 أشهر",
        "cost": "عالي",
    },
]

SECTOR_SOLUTIONS = {
    "food_hospitality": [
        {"icon": "🍽️", "title": "منصة ربط المطاعم بالموردين", "description": "منصة رقمية تربط المطاعم والكافيهات بموردي المواد الغذائية والخضروات مباشرة، مع نظام طلبات وتتبع. نجحت في تقليل التكاليف 25%.", "company": "FoodLink Bahrain", "result": "250+ مطعم مشترك", "year": "2022"},
        {"icon": "🚚", "title": "وساطة خدمات التموين المركزي", "description": "خدمة وساطة متخصصة في ربط شركات التموين بالمؤسسات (مدارس، مستشفيات، شركات) مع إدارة العقود والجودة.", "company": "Catering Connect", "result": "50+ عقد سنوي", "year": "2021"},
        {"icon": "🥬", "title": "سوق الجملة الإلكتروني للخضروات", "description": "منصة B2B تربط مزارعي البحرين بالتجار والمطاعم مباشرة دون وسطاء تقليديين، مع توصيل مباشر.", "company": "Bahrain Fresh Market", "result": "100+ مزارع", "year": "2023"},
    ],
    "real_estate": [
        {"icon": "🏢", "title": "منصة العقارات الذكية للإيجار", "description": "منصة رقمية متخصصة في تأجير العقارات السكنية والتجارية مع زيارات افتراضية وعقود إلكترونية. حققت نمو 300% في سنة.", "company": "SmartRent Bahrain", "result": "500+ عقد إيجار شهرياً", "year": "2022"},
        {"icon": "🏗️", "title": "وساطة المقاولات والمشاريع", "description": "خدمة تربط أصحاب المشاريع بالمقاولين المعتمدين مع ضمان جودة ونظام مراحل دفع آمن.", "company": "BuildConnect", "result": "120+ مشروع منجز", "year": "2021"},
        {"icon": "📊", "title": "تقييم العقارات الآلي", "description": "نظام وساطة يقدم تقييمات فورية للعقارات بناءً على بيانات السوق والموقع والمقارنات.", "company": "PropValuator", "result": "10,000+ تقييم", "year": "2023"},
    ],
    "technology": [
        {"icon": "💻", "title": "سوق البرمجيات والتطبيقات", "description": "منصة تربط شركات البرمجة بالعملاء المحتاجين حلول تقنية، مع نظام مراحل ومتابعة المشاريع.", "company": "TechHub Bahrain", "result": "300+ مشروع تقني", "year": "2022"},
        {"icon": "☁️", "title": "وساطة خدمات الحوسبة السحابية", "description": "خدمة تساعد الشركات في اختيار ومقارنة مزودي الخدمات السحابية مع دعم فني متخصص.", "company": "CloudBroker BH", "result": "150+ شركة مشتركة", "year": "2021"},
        {"icon": "🔒", "title": "وساطة الأمن السيبراني", "description": "منصة تربط الشركات بخبراء الأمن السيبراني وشركات الحماية مع تقييم مخاطر مجاني.", "company": "SecureLink", "result": "80+ تقييم أمني", "year": "2023"},
    ],
    "finance": [
        {"icon": "🏦", "title": "منصة مقارنة منتجات التمويل", "description": "منصة تتيح للأفراد والشركات مقارنة قروض البنوك والتمويلات مع وساطة في إتمام الإجراءات.", "company": "FinanceCompare BH", "result": "200+ تمويل منجز", "year": "2022"},
        {"icon": "🛡️", "title": "وساطة التأمين الذكية", "description": "منصة رقمية لمقارنة وشراء وثائق التأمين مع استشارات مخصصة وادعاءات إلكترونية.", "company": "InsureTech Bahrain", "result": "5,000+ وثيقة تأمين", "year": "2021"},
        {"icon": "💰", "title": "وساطة الاستثمار للشركات الناشئة", "description": "منصة تربط المستثمرين بالشركات الناشئة مع تقييم جدوى وإدارة استثمارات.", "company": "StartupInvest BH", "result": "45+ صفقة استثمار", "year": "2023"},
    ],
    "manufacturing": [
        {"icon": "🏭", "title": "منصة توريد المواد الخام", "description": "منصة B2B تربط المصانع بموردي المواد الخام المحليين والدوليين مع إدارة مخزون ذكية.", "company": "SupplyChain BH", "result": "80+ مصنع مشترك", "year": "2022"},
        {"icon": "📦", "title": "وساطة التصنيع حسب الطلب", "description": "خدمة تربط العملاء بمصانع للتصنيع OEM حسب الطلب مع مراقبة جودة وشحن.", "company": "MakeIt Bahrain", "result": "150+ طلب تصنيع", "year": "2021"},
        {"icon": "🔄", "title": "سوق المعدات الصناعية المستعملة", "description": "منصة متخصصة في بيع وشراء المعدات الصناعية المستعملة مع تقييم وفحص فني.", "company": "IndustrialExchange", "result": "300+ آلة مباعة", "year": "2023"},
    ],
    "health": [
        {"icon": "🏥", "title": "منصة حجز المواعيد الطبية", "description": "منصة شاملة لحجز مواعيد في العيادات والمستشفيات مع ملف طبي إلكتروني ومتابعة.", "company": "HealthBook Bahrain", "result": "50,000+ حجز شهرياً", "year": "2022"},
        {"icon": "💊", "title": "وساطة الأدوية والمستلزمات", "description": "منصة تربط الصيدليات والمستشفيات بموردي الأدوية مع إدارة مخزون وطلبات دورية.", "company": "PharmaLink BH", "result": "200+ صيدلية", "year": "2021"},
        {"icon": "🏠", "title": "وساطة الرعاية الصحية المنزلية", "description": "خدمة تربط المرضى بمقدمي الرعاية المنزلية والتمريض مع متابعة ومتابعة صحية.", "company": "HomeCare Bahrain", "result": "1,000+ مريض شهرياً", "year": "2023"},
    ],
    "education": [
        {"icon": "🎓", "title": "منصة التدريب المهني للشركات", "description": "منصة تربط الشركات بمراكز التدريب والمدربين المعتمدين لبرامج تطوير الموظفين.", "company": "CorpTrain Bahrain", "result": "100+ شركة مشتركة", "year": "2022"},
        {"icon": "📚", "title": "سوق المحتوى التعليمي الرقمي", "description": "منصة تربط المعلمين والمدربين بالطلاب لبيع وشراء المحتوى التعليمي والدورات.", "company": "EduContent BH", "result": "5,000+ طالب", "year": "2021"},
        {"icon": "🌍", "title": "وساطة الدراسة في الخارج", "description": "خدمة متكاملة لمساعدة الطلاب في اختيار الجامعات والقبول والإقامة في الخارج.", "company": "StudyAbroad BH", "result": "300+ طالب سنوياً", "year": "2023"},
    ],
    "transport": [
        {"icon": "🚛", "title": "منصة الشحن اللوجستي الذكي", "description": "منصة رقمية تربط أصحاب البضائع بشركات النقل والشحن مع تتبع مباشر وأسعار تنافسية.", "company": "LogiConnect Bahrain", "result": "10,000+ شحنة شهرياً", "year": "2022"},
        {"icon": "🚗", "title": "وساطة تأجير المركبات للشركات", "description": "خدمة تربط الشركات بمكاتب تأجير السيارات والشاحنات مع عقود سنوية مخفضة.", "company": "FleetLease BH", "result": "500+ مركبة مستأجرة", "year": "2021"},
        {"icon": "📦", "title": "وساطة التخزين والمستودعات", "description": "منصة تربط التجار بأصحاب المستودعات الفارغة للتخزين المؤقت أو الطويل الأمد.", "company": "StorageHub Bahrain", "result": "50+ مستودع مشترك", "year": "2023"},
    ],
    "retail": [
        {"icon": "🛒", "title": "منصة الجملة للتجار الإلكترونيين", "description": "منصة B2B تربط تجار الجملة بأصحاب المتاجر الإلكترونية مع دروبشيبينغ ومخزون مشترك.", "company": "WholesaleEcom BH", "result": "400+ تاجر إلكتروني", "year": "2022"},
        {"icon": "🏪", "title": "وساطة امتياز العلامات التجارية", "description": "خدمة تربط العلامات التجارية العالمية بالمستثمرين المحليين لفتح امتيازات في البحرين.", "company": "FranchiseLink BH", "result": "30+ علامة تجارية", "year": "2021"},
        {"icon": "🎁", "title": "منصة الهدايا والتغليف المخصص", "description": "منصة تربط الشركات بموردي الهدايا والتغليف للمناسبات والمؤتمرات مع تخصيح كامل.", "company": "GiftPro Bahrain", "result": "200+ شركة عميلة", "year": "2023"},
    ],
    "ai_applications": [
        {"icon": "🤖", "title": "منصة تخصيص نماذج الذكاء الاصطناعي", "description": "منصة تربط الشركات بمطوري AI لتخصيص نماذج ChatGPT وغيرها لاحتياجات الأعمال الخاصة.", "company": "AICustom Bahrain", "result": "100+ نموذج مخصص", "year": "2023"},
        {"icon": "📞", "title": "وساطة خدمة العملاء بالذكاء الاصطناعي", "description": "خدمة تربط الشركات بمزودي حلول chatbot وخدمة العملاء الآلية مع تدريب وتخصيص.", "company": "AI Support BH", "result": "80+ شركة مشتركة", "year": "2023"},
        {"icon": "📊", "title": "وساطة تحليل البيانات بالذكاء الاصطناعي", "description": "منصة تربط الشركات بخبراء تحليل البيانات وAI لاستخراج رؤى من بياناتهم.", "company": "DataAI Bahrain", "result": "150+ مشروع تحليل", "year": "2023"},
    ],
}
